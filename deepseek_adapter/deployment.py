"""Logging and singleton endpoint reconciliation for the DeepSeek boundary."""

from __future__ import annotations

from datetime import timedelta
from os import chdir, getcwd
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from pydantic import BaseModel, Field, model_validator

SECRET_REFERENCE = "{{secrets/API_KEY/DEEPSEEK_API_KEY}}"
ENDPOINT_NAME = "deepseek-v4-streaming-agent-lab"


class AiGatewayDeploymentConfig(BaseModel):
    """Explicit governance inputs for the existing DeepSeek singleton.

    There are intentionally no production defaults for payload retention or
    QPM. Those values are business/governance choices and must be supplied by
    the deployment caller after approving the target UC schema.
    """

    enable_inference_table: bool = True
    catalog_name: str | None = None
    schema_name: str | None = None
    table_name_prefix: str | None = None
    endpoint_qpm: int = Field(ge=1)
    enable_usage_tracking: bool = False

    @model_validator(mode="after")
    def require_table_location_when_enabled(self) -> "AiGatewayDeploymentConfig":
        if self.enable_inference_table and not all(
            (self.catalog_name, self.schema_name, self.table_name_prefix)
        ):
            raise ValueError(
                "catalog_name, schema_name, and table_name_prefix are required "
                "when inference tables are enabled"
            )
        return self


def responses_agent_signature_with_runtime_tools() -> Any:
    """Widen only the MLflow Responses `tools` input to accept full schemas."""
    from mlflow.models import ModelSignature
    from mlflow.types.responses import (
        RESPONSES_AGENT_INPUT_SCHEMA,
        RESPONSES_AGENT_OUTPUT_SCHEMA,
    )
    from mlflow.types.schema import AnyType, Array, ColSpec, Schema

    return ModelSignature(
        inputs=Schema(
            [
                ColSpec(Array(AnyType()), name="tools", required=False)
                if column.name == "tools"
                else column
                for column in RESPONSES_AGENT_INPUT_SCHEMA.inputs
            ]
        ),
        outputs=RESPONSES_AGENT_OUTPUT_SCHEMA,
    )


def log_and_register(*, model_name: str, deepseek_model: str) -> str:
    """Log the isolated adapter and return a registered UC model version.

    MLflow always calls a ``ResponsesAgent`` during logging to validate its
    example. Provider credentials intentionally exist only in the serving
    endpoint secret reference, not on the deployment client, so stub that
    one local validation call. The logged source remains the real adapter and
    is verified after deployment through ``ChatDatabricks``.
    """
    import mlflow
    from mlflow.types.responses import ResponsesAgentResponse

    from deepseek_adapter.adapter import DeepSeekResponsesAgent

    def validation_predict(
        _self: DeepSeekResponsesAgent, _request: Any
    ) -> ResponsesAgentResponse:
        return ResponsesAgentResponse(id="logging-validation", output=[])

    source_root = Path(__file__).parent
    with TemporaryDirectory() as temp_dir:
        entrypoint = Path(temp_dir) / "model.py"
        entrypoint.write_text(
            "from mlflow.models import set_model\n"
            "from deepseek_adapter.adapter import DeepSeekResponsesAgent\n"
            f"set_model(DeepSeekResponsesAgent({deepseek_model!r}))\n",
            encoding="utf-8",
        )
        original_directory = getcwd()
        try:
            # MLflow otherwise detects the repository uv.lock, which deliberately
            # omits the provider-only package and overrides pip_requirements.
            # Keep ``python_model`` relative to this directory: Model Serving
            # cannot resolve an absolute Windows source path from the deployer.
            chdir(temp_dir)
            with patch.object(DeepSeekResponsesAgent, "predict", validation_predict):
                with mlflow.start_run(run_name="deepseek-responses-adapter"):
                    logged = mlflow.pyfunc.log_model(
                        name="deepseek_responses_agent",
                        python_model="model.py",
                        code_paths=[str(source_root)],
                        pip_requirements=[
                            "mlflow==3.14.0",
                            "langchain==1.3.13",
                            "langchain-deepseek==1.1.0",
                            "pydantic==2.13.4",
                        ],
                    )
        finally:
            chdir(original_directory)
        mlflow.models.set_signature(
            logged.model_uri, responses_agent_signature_with_runtime_tools()
        )
        registered = mlflow.register_model(
            model_uri=logged.model_uri, name=model_name, await_registration_for=600
        )
    return str(registered.version)


def reconcile_singleton_endpoint(
    *,
    client: Any,
    model_name: str,
    model_version: str,
    endpoint_name: str = ENDPOINT_NAME,
) -> Any:
    """In-place update only; the two-endpoint quota forbids endpoint creation."""
    from databricks.sdk.service.serving import ServedEntityInput

    existing = client.serving_endpoints.get(name=endpoint_name)
    update_state = str(existing.state.config_update)
    if not update_state.endswith(("NOT_UPDATING", "UPDATE_FAILED", "UPDATE_CANCELED")):
        client.serving_endpoints.wait_get_serving_endpoint_not_updating(
            name=endpoint_name, timeout=timedelta(minutes=30)
        )
    endpoint = client.serving_endpoints.update_config(
        name=endpoint_name,
        served_entities=[
            ServedEntityInput(
                entity_name=model_name,
                entity_version=model_version,
                workload_size="Small",
                scale_to_zero_enabled=True,
                environment_vars={"DEEPSEEK_API_KEY": SECRET_REFERENCE},
            )
        ],
    ).result(timeout=timedelta(minutes=30))
    assert str(endpoint.state.ready).endswith("READY"), endpoint.state
    assert str(endpoint.state.config_update).endswith("NOT_UPDATING"), endpoint.state
    active = next(
        item
        for item in endpoint.config.served_entities
        if item.entity_name == model_name and str(item.entity_version) == model_version
    )
    assert "DEEPSEEK_API_KEY" in (active.environment_vars or {})
    return endpoint


def configure_ai_gateway(
    *,
    client: Any,
    config: AiGatewayDeploymentConfig,
    endpoint_name: str = ENDPOINT_NAME,
) -> Any:
    """Apply approved inference-table and QPM controls to the singleton only.

    This operation updates AI Gateway separately from a served-entity update,
    so it cannot create a third endpoint or alter the DeepSeek model, traffic,
    secret reference, or scale-to-zero setting.
    """
    from databricks.sdk.service.serving import (
        AiGatewayInferenceTableConfig,
        AiGatewayRateLimit,
        AiGatewayRateLimitKey,
        AiGatewayRateLimitRenewalPeriod,
        AiGatewayUsageTrackingConfig,
    )

    existing = client.serving_endpoints.get(name=endpoint_name)
    update_state = str(existing.state.config_update)
    if not update_state.endswith(("NOT_UPDATING", "UPDATE_FAILED", "UPDATE_CANCELED")):
        client.serving_endpoints.wait_get_serving_endpoint_not_updating(
            name=endpoint_name, timeout=timedelta(minutes=30)
        )

    request: dict[str, Any] = {
        "name": endpoint_name,
        "rate_limits": [
            AiGatewayRateLimit(
                key=AiGatewayRateLimitKey.ENDPOINT,
                renewal_period=AiGatewayRateLimitRenewalPeriod.MINUTE,
                calls=config.endpoint_qpm,
            )
        ],
        "usage_tracking_config": AiGatewayUsageTrackingConfig(
            enabled=config.enable_usage_tracking
        ),
    }
    if config.enable_inference_table:
        request["inference_table_config"] = AiGatewayInferenceTableConfig(
            enabled=True,
            catalog_name=config.catalog_name,
            schema_name=config.schema_name,
            table_name_prefix=config.table_name_prefix,
        )

    return client.serving_endpoints.put_ai_gateway(
        **request,
    )

from types import SimpleNamespace
from pathlib import Path

from deepseek_adapter.deployment import (
    SECRET_REFERENCE,
    AiGatewayDeploymentConfig,
    configure_ai_gateway,
    reconcile_singleton_endpoint,
)


def test_reconcile_updates_existing_singleton_without_create():
    active = SimpleNamespace(
        entity_name="ecommerce_agent.gold_layer.deepseek_v4_streaming_agent",
        entity_version="4",
        environment_vars={"DEEPSEEK_API_KEY": SECRET_REFERENCE},
    )
    ready = SimpleNamespace(
        state=SimpleNamespace(ready="READY", config_update="NOT_UPDATING"),
        config=SimpleNamespace(served_entities=[active]),
    )
    calls = []

    class Endpoints:
        def get(self, **kwargs):
            calls.append(("get", kwargs))
            return SimpleNamespace(state=SimpleNamespace(config_update="NOT_UPDATING"))

        def update_config(self, **kwargs):
            calls.append(("update", kwargs))
            return SimpleNamespace(result=lambda **_: ready)

    result = reconcile_singleton_endpoint(
        client=SimpleNamespace(serving_endpoints=Endpoints()),
        model_name="ecommerce_agent.gold_layer.deepseek_v4_streaming_agent",
        model_version="4",
    )
    assert result is ready
    assert [name for name, _ in calls] == ["get", "update"]
    assert calls[1][1]["served_entities"][0].environment_vars == {
        "DEEPSEEK_API_KEY": SECRET_REFERENCE
    }


def test_ai_gateway_reconciliation_uses_explicit_inference_table_and_qpm():
    calls = []

    class Endpoints:
        def get(self, *, name):
            return SimpleNamespace(state=SimpleNamespace(config_update="NOT_UPDATING"))

        def put_ai_gateway(self, **kwargs):
            calls.append(kwargs)
            return "configured"

    result = configure_ai_gateway(
        client=SimpleNamespace(serving_endpoints=Endpoints()),
        config=AiGatewayDeploymentConfig(
            catalog_name="ecommerce_agent",
            schema_name="agent_layer",
            table_name_prefix="deepseek_gateway",
            endpoint_qpm=12,
            enable_usage_tracking=True,
        ),
    )

    assert result == "configured"
    assert calls[0]["name"] == "deepseek-v4-streaming-agent-lab"
    assert calls[0]["inference_table_config"].catalog_name == "ecommerce_agent"
    assert calls[0]["rate_limits"][0].calls == 12
    assert calls[0]["rate_limits"][0].tokens is None


def test_ai_gateway_can_apply_qpm_when_inference_tables_are_unsupported():
    calls = []

    class Endpoints:
        def get(self, *, name):
            return SimpleNamespace(state=SimpleNamespace(config_update="NOT_UPDATING"))

        def put_ai_gateway(self, **kwargs):
            calls.append(kwargs)
            return "configured"

    result = configure_ai_gateway(
        client=SimpleNamespace(serving_endpoints=Endpoints()),
        config=AiGatewayDeploymentConfig(
            enable_inference_table=False,
            endpoint_qpm=15,
            enable_usage_tracking=True,
        ),
    )

    assert result == "configured"
    assert "inference_table_config" not in calls[0]
    assert calls[0]["rate_limits"][0].calls == 15


def test_logging_uses_a_relative_model_entrypoint_and_adapter_only_code_path():
    source = (
        Path(__file__).resolve().parents[2] / "deepseek_adapter" / "deployment.py"
    ).read_text(encoding="utf-8")

    assert 'python_model="model.py"' in source
    assert "code_paths=[str(source_root)]" in source
    assert "python_model=str(entrypoint)" not in source

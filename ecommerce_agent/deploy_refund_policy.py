"""Deploy the approved synthetic refund policy as a governed UC Python UDF."""

from __future__ import annotations

from typing import Any

from ecommerce_agent.policies import check_refund_eligibility

CATALOG = "ecommerce_agent"
SCHEMA = "agent_layer"
FUNCTION_NAME = "check_refund_eligibility"
FULL_FUNCTION_NAME = f"{CATALOG}.{SCHEMA}.{FUNCTION_NAME}"


def deploy_refund_policy_function(*, client: Any | None = None) -> Any:
    """Create or replace the governed refund-policy Python function.

    The Unity Catalog client is imported lazily so importing the agent package
    never initializes workspace authentication or serverless Spark Connect.
    """
    if client is None:
        from unitycatalog.ai.core.databricks import DatabricksFunctionClient

        try:
            client = DatabricksFunctionClient()
        except Exception as exc:
            raise RuntimeError(
                "DatabricksFunctionClient could not initialize local serverless "
                "Spark Connect. Run this adapter in a compatible Databricks "
                "environment or submit the generated current Python UDF DDL "
                "through a Pro/serverless SQL warehouse."
            ) from exc

    return client.create_python_function(
        func=check_refund_eligibility,
        catalog=CATALOG,
        schema=SCHEMA,
        replace=True,
    )

# Databricks notebook source
# MAGIC %md
# MAGIC ## Driver — Databricks setup
# MAGIC
# MAGIC This notebook handles Databricks workspace setup tasks:
# MAGIC - AI Gateway configuration on the configured LLM endpoint.
# MAGIC
# MAGIC Skills are loaded from the application source tree
# MAGIC (``ecommerce_agent/skills/``) and ship with the App. A UC Volume provider
# MAGIC is intentionally not part of the current config schema; adding one later
# MAGIC requires an explicit publishing/versioning contract and read-only App
# MAGIC resource rather than an ad-hoc sync cell.

# COMMAND ----------

import yaml
from databricks.sdk import WorkspaceClient

with open("config.yaml") as f:
    raw_config = yaml.safe_load(f)

CATALOG, SCHEMA = "ecommerce_agent", "agent_layer"
w = WorkspaceClient()

# COMMAND ----------
# MAGIC %md
# MAGIC ### AI Gateway on the configured LLM endpoint
# MAGIC
# MAGIC This is an explicit capability probe for the endpoint in
# MAGIC ``config.yaml -> llm.endpoint_name``. Official Databricks documentation
# MAGIC supports QPM for custom endpoints, but the current Free Edition workspace
# MAGIC rejects AI Gateway controls for this endpoint type. Production deployment
# MAGIC records that workspace-specific result and relies on the application
# MAGIC safety envelope; it must not claim the controls below are active until a
# MAGIC read-back exposes an ``ai_gateway`` configuration.

# COMMAND ----------

from databricks.sdk.service.serving import (
    AiGatewayInferenceTableConfig,
    AiGatewayRateLimit,
    AiGatewayRateLimitKey,
    AiGatewayRateLimitRenewalPeriod,
)

LLM_ENDPOINT_NAME = raw_config["llm"]["endpoint_name"]

w.serving_endpoints.put_ai_gateway(
    name=LLM_ENDPOINT_NAME,
    inference_table_config=AiGatewayInferenceTableConfig(
        enabled=True,
        catalog_name=CATALOG,
        schema_name=SCHEMA,
        table_name_prefix="ecommerce_support_llm",
    ),
    rate_limits=[
        AiGatewayRateLimit(
            key=AiGatewayRateLimitKey.ENDPOINT,
            renewal_period=AiGatewayRateLimitRenewalPeriod.MINUTE,
            calls=15,
        )
    ],
)

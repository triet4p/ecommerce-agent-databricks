# Databricks notebook source
# MAGIC %md
# MAGIC ## Driver — setup cho agent (đã đổi theo current state 2026-07)
# MAGIC Trước đây file này log model qua `mlflow.pyfunc.log_model` + deploy lên Model
# MAGIC Serving bằng `agents.deploy()`. Sau khi rà lại, Databricks docs hiện tại gọi hướng
# MAGIC đó là "legacy" cho agent MỚI, khuyến nghị host agent trực tiếp trên Databricks Apps
# MAGIC (xem `agent_app/server.py`) — file này giờ chỉ còn phần KHÔNG phụ thuộc hosting
# MAGIC target: sync skills lên UC Volume, và bật AI Gateway trên endpoint LLM nền tảng
# MAGIC (không phải trên 1 "agent endpoint" nữa, vì agent không còn là Model Serving
# MAGIC endpoint riêng). Phần Model Serving cũ được giữ lại phía dưới, comment rõ, phòng
# MAGIC trường hợp workspace chưa bật Databricks Apps.

# COMMAND ----------

import pathlib

import yaml
from databricks.sdk import WorkspaceClient

with open("config.yaml") as f:
    raw_config = yaml.safe_load(f)

CATALOG, SCHEMA = "ecommerce_demo", "agent"
w = WorkspaceClient()

# COMMAND ----------
# Sync skills/*.md lên UC Volume — SkillLibrary (agent_core/skill_interface.py) đọc
# trực tiếp từ đây lúc runtime, dù agent chạy trên Databricks App hay Model Serving.
# Chạy độc lập với hosting target — sửa skill không cần re-deploy gì cả.

skills_volume_path = raw_config.get("skills", {}).get("volume_path")
if skills_volume_path:
    for skill_file in pathlib.Path("skills").glob("*.md"):
        with open(skill_file, "rb") as f:
            w.files.upload(f"{skills_volume_path}/{skill_file.name}", f, overwrite=True)

# COMMAND ----------
# AI Gateway trên endpoint LLM nền tảng (config.yaml -> llm.endpoint_name, thường là
# 1 pay-per-token Foundation Model endpoint) — inference table + rate limit.
# LƯU Ý (đã rà lại 2026-07): SDK ghi rõ endpoint loại "agent" (tạo qua agents.deploy)
# chỉ hỗ trợ inference_table_config, KHÔNG hỗ trợ rate_limits. Endpoint pay-per-token/
# external model như databricks-meta-llama-3-3-70b-instruct thì "fully supported" —
# nên rate_limits chuyển xuống áp ở ĐÂY thay vì ở 1 agent endpoint không còn tồn tại
# trong kiến trúc mới (agent giờ host trên Databricks App, không phải Model Serving).

from databricks.sdk.service.serving import (
    AiGatewayConfig,
    AiGatewayInferenceTableConfig,
    AiGatewayRateLimit,
    AiGatewayRateLimitKey,
    AiGatewayRateLimitRenewalPeriod,
)

LLM_ENDPOINT_NAME = raw_config["llm"]["endpoint_name"]

w.serving_endpoints.put_ai_gateway(
    name=LLM_ENDPOINT_NAME,
    ai_gateway=AiGatewayConfig(
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
                calls=100,
            )
        ],
    ),
)

# COMMAND ----------
# MAGIC %md
# MAGIC ### (LEGACY, không chạy mặc định) Deploy agent lên Model Serving
# MAGIC Chỉ dùng nếu workspace chưa bật Databricks Apps. Đường chính hiện tại là
# MAGIC `databricks bundle deploy` + `databricks bundle run` cho resource App
# MAGIC `ecommerce_support_agent_app` (xem `resources/ecommerce_support_agent.app.yml`).

# COMMAND ----------
# MAGIC %md
# MAGIC ```python
# MAGIC import mlflow
# MAGIC from mlflow.models.resources import DatabricksFunction, DatabricksServingEndpoint
# MAGIC from databricks import agents
# MAGIC
# MAGIC UC_FUNCTION_NAMES = [t["full_name"] for t in raw_config["tools"] if t["kind"] == "uc_function"]
# MAGIC SERVING_ENDPOINT_NAMES = [t["endpoint_name"] for t in raw_config["tools"] if t["kind"] == "serving_endpoint"]
# MAGIC UC_MODEL_NAME = f"{CATALOG}.{SCHEMA}.ecommerce_support_agent"
# MAGIC
# MAGIC resources = [DatabricksFunction(function_name=n) for n in UC_FUNCTION_NAMES]
# MAGIC resources += [DatabricksServingEndpoint(endpoint_name=n) for n in SERVING_ENDPOINT_NAMES]
# MAGIC
# MAGIC mlflow.set_registry_uri("databricks-uc")
# MAGIC logged_model = mlflow.pyfunc.log_model(
# MAGIC     python_model="agent.py", name="agent", resources=resources, pip_requirements="requirements.txt",
# MAGIC )
# MAGIC registered_model = mlflow.register_model(model_uri=logged_model.model_uri, name=UC_MODEL_NAME)
# MAGIC deployment = agents.deploy(
# MAGIC     model_name=UC_MODEL_NAME, model_version=registered_model.version, scale_to_zero_enabled=True,
# MAGIC )
# MAGIC # Agent-type endpoint: AiGatewayConfig chỉ hỗ trợ inference_table_config, không rate_limits.
# MAGIC ```

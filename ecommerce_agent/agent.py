# Databricks notebook source
# MAGIC %md
# MAGIC ## Agent entrypoint — ecommerce_support (Models-from-Code, path LEGACY)
# MAGIC File này dùng để log agent qua `mlflow.pyfunc.log_model(python_model="agent.py")`
# MAGIC cho hướng Model Serving cũ (xem driver.py phần legacy). **Path chính hiện tại là
# MAGIC `agent_app/server.py`** — host agent trực tiếp trên Databricks Apps, không cần file
# MAGIC này. Vẫn giữ lại vì hữu ích để test agent offline / log 1 bản snapshot cho MLflow
# MAGIC Agent Evaluation mà không cần chạy cả FastAPI server.

# COMMAND ----------

import mlflow
import yaml

from agent_core import AgentConfig, build_agent
from agent_core.tool_interface import register_custom_tool_factory
from agent_core.retriever_interface import Retriever

from projects.ecommerce_support.tools.search_policy_docs_tool import make_search_policy_docs_tool

# COMMAND ----------

mlflow.langchain.autolog()
mlflow.set_registry_uri("databricks-uc")  # cần cho load_prompt() nếu system_prompt_registry_uri có set

with open("config.yaml") as f:
    raw_config = yaml.safe_load(f)
config = AgentConfig.model_validate(raw_config)

# COMMAND ----------
# Đăng ký tool "nặng" — retriever qua Model Serving endpoint, KHÔNG thể là UC Function
# vì UC Python Function chạy sandbox không có network egress.

if config.retriever is not None:
    retriever = Retriever(config.retriever)
    register_custom_tool_factory(
        "search_policy_docs",
        lambda tool_config: make_search_policy_docs_tool(retriever, tool_config),
    )

# COMMAND ----------

AGENT = build_agent(config)
mlflow.models.set_model(AGENT)

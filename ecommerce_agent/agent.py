# Databricks notebook source
# MAGIC %md
# MAGIC ## Agent entrypoint — offline snapshot / MLflow Agent Evaluation
# MAGIC This file builds the agent for offline testing and MLflow Agent Evaluation.
# MAGIC It logs the agent via ``mlflow.pyfunc.log_model(python_model="agent.py")``
# MAGIC so it can be evaluated without deploying the full Databricks App.
# MAGIC
# MAGIC **The production hosting path is ``agent_app/server.py``** — host the agent
# MAGIC directly on Databricks Apps with MLflow ``AgentServer``.
# MAGIC
# MAGIC NOTE: The config file path resolution assumes this file runs from the
# MAGIC ``ecommerce_agent`` directory or via Databricks Repos root.

# COMMAND ----------

import mlflow

from agent_core import Retriever, ToolRegistry, build_agent, load_config

from ecommerce_agent.tools.search_policy_docs_tool import make_search_policy_docs_tool

# COMMAND ----------

mlflow.langchain.autolog()
mlflow.set_registry_uri(
    "databricks-uc"
)  # required for load_prompt() when system_prompt_registry_uri is set

config = load_config("config.yaml")

# COMMAND ----------
# Register the serving-endpoint tool factory.

_registry = ToolRegistry()
if config.retriever is not None:
    retriever = Retriever(config.retriever)
    _registry.register_serving_factory(
        "search_policy_docs",
        lambda tool_config: make_search_policy_docs_tool(retriever, tool_config),
    )

# Build agent for legacy logging use case.
# Note: UC function tools require managed MCP or explicit UCFunctionToolkit adapter.
# In this legacy snapshot path, UC functions are resolved via the configured MCP servers.
AGENT = build_agent(config, registry=_registry)
mlflow.models.set_model(AGENT)

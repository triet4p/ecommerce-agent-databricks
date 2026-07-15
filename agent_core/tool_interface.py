"""
agent_core.tool_interface
--------------------------
Turns a `ToolConfig` (from config_schema) into a LangChain-compatible tool object,
without the orchestrator needing to know whether the tool is a UC Function or a
Serving Endpoint wrapper. This is the single seam between Agent Core and Fat Module.

Fat Modules that need a custom SERVING_ENDPOINT tool (e.g. search_policy_docs) provide
their own callable and register it via `register_custom_tool_factory` below — Agent Core
still owns the resolution logic, the Fat Module only owns the implementation.
"""

from __future__ import annotations

from typing import Callable

from agent_core.config_schema import (
    AgentConfig,
    ServingEndpointToolConfig,
    ToolConfig,
    ToolKind,
    UCFunctionToolConfig,
)

# name -> factory(config: ServingEndpointToolConfig) -> BaseTool
_CUSTOM_TOOL_FACTORIES: dict[str, Callable] = {}


def register_custom_tool_factory(name: str, factory: Callable) -> None:
    """Fat Module calls this once at import time, e.g. in projects/<uc>/agent.py."""
    _CUSTOM_TOOL_FACTORIES[name] = factory


def _build_uc_function_tools(configs: list[UCFunctionToolConfig],
                             execution_mode: str) -> list:
    """UC Functions are governed natively by Unity Catalog (EXECUTE grant = access control).
    Uses the Databricks UC Function client so Agent Core never hand-rolls auth/signature parsing.
    """
    from databricks_langchain.uc_ai import DatabricksFunctionClient, UCFunctionToolkit

    client = DatabricksFunctionClient(execution_mode=execution_mode)
    full_names = [c.full_name for c in configs]
    toolkit = UCFunctionToolkit(function_names=full_names, client=client)
    return toolkit.tools


def _build_serving_endpoint_tool(config: ServingEndpointToolConfig):
    factory = _CUSTOM_TOOL_FACTORIES.get(config.name)
    if factory is None:
        raise ValueError(
            f"No custom tool factory registered for '{config.name}'. "
            "Fat Module must call register_custom_tool_factory(...) before building the agent."
        )
    return factory(config)


def build_tools(config: AgentConfig) -> list:
    """Resolve every ToolConfig entry into an actual callable tool object."""
    uc_configs = [t for t in config.tools if t.kind == ToolKind.UC_FUNCTION]
    serving_configs = [t for t in config.tools if t.kind == ToolKind.SERVING_ENDPOINT]

    tools = []
    if uc_configs:
        tools.extend(_build_uc_function_tools(uc_configs, execution_mode=config.compute_type))
    for sc in serving_configs:
        tools.append(_build_serving_endpoint_tool(sc))
    return tools

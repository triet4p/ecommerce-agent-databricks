"""
agent_core.tool_interface
--------------------------
Resolves a `ToolConfig` (from config_schema) into a LangChain-compatible tool object,
without the orchestrator needing to know whether the tool is a UC Function, a local
function, or a Serving Endpoint wrapper.

This module provides:
- Instance-scoped `ToolRegistry` that replaces the process-global factory dict.
- Resolution for UC functions (via managed MCP or an explicit compatibility adapter).
- Resolution for local functions (imported by dotted path and wrapped as @tool).
- Resolution for serving endpoint tools (delegated to registered factories).

UC function resolution in the production path goes through managed MCP (see
mcp_lifecycle.py). Direct `UCFunctionToolkit` is available only through an explicit
compatibility adapter (see uc_toolkit_adapter.py) and is never a silent fallback.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Callable

from langchain_core.tools import tool as lc_tool, BaseTool

from agent_core.config_schema import (
    AgentConfig,
    LocalFunctionToolConfig,
    ServingEndpointToolConfig,
    ToolKind,
    UCFunctionTransport,
)

# ---------------------------------------------------------------------------
# Instance-scoped tool registry
# ---------------------------------------------------------------------------


@dataclass
class ToolRegistry:
    """Instance-scoped registry for custom tool factories.

    Each agent build gets its own registry so that tests and multiple agent
    builds cannot leak factories between each other.
    """

    _serving_factories: dict[str, Callable] = field(default_factory=dict)

    def register_serving_factory(self, name: str, factory: Callable) -> None:
        """Register a factory for a serving-endpoint tool.

        The factory receives the `ServingEndpointToolConfig` and must return a
        LangChain `BaseTool` or callable.
        """
        self._serving_factories[name] = factory

    def get_serving_factory(self, name: str) -> Callable | None:
        return self._serving_factories.get(name)


# ---------------------------------------------------------------------------
# Tool builders
# ---------------------------------------------------------------------------


def _build_local_function_tool(config: LocalFunctionToolConfig) -> BaseTool:
    """Wrap a deterministic local function as a LangChain tool.

    Imports the callable by dotted ``function_ref`` at build time so the
    function definition stays in the Fat Module.
    """
    module_path, _, func_name = config.function_ref.rpartition(".")
    mod = importlib.import_module(module_path)
    fn = getattr(mod, func_name)

    tool = lc_tool(config.name, description=config.description)(fn)
    return tool


def _build_serving_endpoint_tool(
    config: ServingEndpointToolConfig,
    registry: ToolRegistry,
) -> BaseTool:
    factory = registry.get_serving_factory(config.name)
    if factory is None:
        raise ValueError(
            f"No custom tool factory registered for '{config.name}'. "
            "The Fat Module must register a factory before building the agent."
        )
    result = factory(config)
    if isinstance(result, BaseTool):
        return result
    # If the factory returned a plain callable, wrap it
    return lc_tool(config.name, description=config.description)(result)


def resolve_uc_function_tools(
    config: AgentConfig,
    *,
    client: Any | None = None,
) -> list[BaseTool]:
    """Resolve UC functions through the explicitly selected transport.

    Both managed MCP and the top-level ``UCFunctionToolkit`` are supported.
    Selection is explicit in ``AgentConfig.uc_function_transport``; failures
    never trigger an automatic fallback to the other transport.
    """
    configs = [
        tool_config
        for tool_config in config.tools
        if tool_config.kind == ToolKind.UC_FUNCTION
    ]
    if not configs:
        return []

    if config.uc_function_transport == UCFunctionTransport.MANAGED_MCP:
        from agent_core.mcp_lifecycle import resolve_mcp_uc_tools

        return resolve_mcp_uc_tools(config)

    if config.uc_function_transport == UCFunctionTransport.UC_TOOLKIT:
        from agent_core.uc_toolkit_adapter import build_uc_toolkit_tools

        return build_uc_toolkit_tools(configs, client=client)

    raise ValueError(
        f"Unsupported UC function transport: {config.uc_function_transport!r}"
    )


def build_tools(
    config: AgentConfig,
    registry: ToolRegistry | None = None,
    *,
    uc_function_client: Any | None = None,
) -> list[BaseTool]:
    """Resolve every ToolConfig entry into an actual callable tool object.

    Uses the provided ``registry`` (or a fresh one) to look up serving-endpoint
    factories. This keeps resolution deterministic and testable without
    process-global state.
    """
    if registry is None:
        registry = ToolRegistry()

    tools: list[BaseTool] = []

    for tc in config.tools:
        if tc.kind == ToolKind.LOCAL_FUNCTION:
            tools.append(_build_local_function_tool(tc))
        elif tc.kind == ToolKind.SERVING_ENDPOINT:
            tools.append(_build_serving_endpoint_tool(tc, registry))
        elif tc.kind == ToolKind.UC_FUNCTION:
            # Resolved once below through the explicitly selected transport.
            continue

    tools.extend(resolve_uc_function_tools(config, client=uc_function_client))

    return tools

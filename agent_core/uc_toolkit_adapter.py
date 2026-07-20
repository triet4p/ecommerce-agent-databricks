"""
agent_core.uc_toolkit_adapter
--------------------------------
Explicit compatibility adapter for the top-level ``UCFunctionToolkit``.

This adapter is for:
1. Explicitly selected compatibility deployment targets where managed MCP
   is unavailable.
2. Certification labs that teach the UC function toolkit concept.

It is NEVER a silent fallback from managed MCP failures.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from databricks_langchain import UCFunctionToolkit
from unitycatalog.ai.core.databricks import DatabricksFunctionClient

from agent_core.config_schema import UCFunctionToolConfig

if TYPE_CHECKING:
    from unitycatalog.ai.core.base import BaseFunctionClient

logger = logging.getLogger(__name__)


def build_uc_toolkit_tools(
    configs: list[UCFunctionToolConfig],
    *,
    client: BaseFunctionClient | None = None,
) -> list:
    """Build tools using the top-level ``UCFunctionToolkit``.

    This is a direct, non-MCP path for Unity Catalog function discovery.
    It requires the caller to have appropriate UC permissions (``EXECUTE``,
    ``USE CATALOG``, ``USE SCHEMA``).

    Args:
        configs: UC function tool configs.
        client: Explicit Unity Catalog function client. When omitted, construct
            the current Databricks client using unified authentication.

    Returns:
        A list of LangChain-compatible tool objects.
    """
    if not configs:
        return []

    function_client = client if client is not None else DatabricksFunctionClient()
    full_names = [c.full_name for c in configs]
    toolkit = UCFunctionToolkit(function_names=full_names, client=function_client)
    logger.info(
        "Built %d UC toolkit tools (non-MCP compatibility path): %s",
        len(toolkit.tools),
        full_names,
    )
    return toolkit.tools

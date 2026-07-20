"""
agent_core.mcp_lifecycle
--------------------------
Lifecycle management for ``DatabricksMultiServerMCPClient`` and
exposure of its discovered tools to ``create_agent``.

This module owns:
- Construction of ``DatabricksMCPServer`` configs from the typed schema.
- Tool discovery and UC function allowlisting against the config schema.
- Cleanup and error handling.

The managed MCP feature is Public Preview as of 2026-07-16. Production
deployment must verify workspace enablement.

API notes (``databricks-langchain==0.20.0``):
- ``DatabricksMCPServer`` requires ``name`` and ``url`` (the managed MCP
  server endpoint URL). Optional: ``headers``, ``timeout``, ``handle_tool_error``.
- ``DatabricksMultiServerMCPClient(servers=[...])`` accepts a list of servers.
- ``client.get_tools()`` is **async** — returns a flat list of LangChain tools.
- ``client.session(name)`` is an async context manager for session lifecycle.
- There is no ``connect()`` or ``close()`` — the client handles connections.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from databricks_langchain import DatabricksMCPServer, DatabricksMultiServerMCPClient

from agent_core.config_schema import AgentConfig

logger = logging.getLogger(__name__)


def build_mcp_server_configs(
    config: AgentConfig,
) -> list[tuple[DatabricksMCPServer, set[str] | None]]:
    """Build ``DatabricksMCPServer`` entries with per-server UC function allowlists.

    Each managed MCP server requires a ``url`` pointing to the Databricks
    managed MCP endpoint for the workspace. The per-server ``uc_function_names``
    allowlist is returned alongside the server config for downstream filtering.

    Args:
        config: Agent config with ``mcp_servers`` entries.

    Returns:
        A list of ``(DatabricksMCPServer, allowlist_set_or_None)`` tuples.
    """
    servers: list[tuple[DatabricksMCPServer, set[str] | None]] = []
    for mcp_cfg in config.mcp_servers:
        if not mcp_cfg.url:
            logger.warning(
                "MCP server '%s' has no url configured; skipping.",
                mcp_cfg.name,
            )
            continue
        server = DatabricksMCPServer(
            name=mcp_cfg.name,
            url=mcp_cfg.url,
            headers=mcp_cfg.headers,
        )
        allowlist = (
            set(mcp_cfg.uc_function_names) if mcp_cfg.uc_function_names else None
        )
        servers.append((server, allowlist))
    return servers


def resolve_mcp_uc_tools(config: AgentConfig) -> list[Any]:
    """Resolve UC function tools through managed MCP.

    Uses ``DatabricksMultiServerMCPClient`` to discover tools from the
    configured MCP servers. Only UC functions whose full names appear in
    the config's ``tools`` list are returned (allowlisting).

    Because ``get_tools()`` is async, this function runs it in a fresh
    event loop if no running loop exists.

    Returns:
        A list of LangChain-compatible tool objects.

    Raises:
        RuntimeError: If MCP connection or tool discovery fails.
    """
    uc_function_full_names = {
        t.full_name
        for t in config.tools
        if hasattr(t, "kind") and t.kind == "uc_function"
    }

    if not uc_function_full_names:
        return []

    mcp_server_tuples = build_mcp_server_configs(config)
    if not mcp_server_tuples:
        # The current Databricks managed-MCP contract has a stable UC-function
        # route.  Build one server per configured function through the locked
        # client's helper, which derives the workspace host and OAuth transport
        # from WorkspaceClient rather than storing an environment-specific URL.
        mcp_server_tuples = _build_default_uc_function_servers(uc_function_full_names)
    if not mcp_server_tuples:
        raise RuntimeError(
            "No valid managed MCP configuration could be built for the configured "
            "UC functions. Check workspace authentication and managed MCP enablement."
        )

    discovered: list[Any] = []
    for server, allowlist in mcp_server_tuples:
        # Discovery must stay server-scoped. Flattening all discovered tools and
        # applying a union allowlist afterwards lets one server expose a function
        # authorized only for a different server.
        client = DatabricksMultiServerMCPClient(servers=[server])
        try:
            server_tools: list[Any] = _run_async(client.get_tools())
        except Exception as exc:
            logger.error(
                "MCP tool discovery failed for server '%s': %s", server.name, exc
            )
            raise RuntimeError(
                f"MCP tool discovery failed for server '{server.name}': {exc}. "
                "Ensure the workspace has managed MCP enabled and the configured "
                "server URL and authentication are correct."
            ) from exc

        effective_allowlist = allowlist or uc_function_full_names
        discovered.extend(
            _filter_by_uc_function_names(server_tools, effective_allowlist)
        )

    _assert_unique_tool_names(discovered)
    return discovered


def _build_default_uc_function_servers(
    function_names: set[str],
) -> list[tuple[DatabricksMCPServer, set[str]]]:
    """Construct current managed-MCP UC-function servers without fixed URLs.

    ``DatabricksMCPServer.from_uc_function`` is the current SDK-supported
    constructor. It produces ``/api/2.0/mcp/functions/<catalog>/<schema>/<fn>``
    and obtains OAuth from the running user or App identity.
    """
    servers: list[tuple[DatabricksMCPServer, set[str]]] = []
    for full_name in sorted(function_names):
        catalog, schema, function_name = full_name.split(".", maxsplit=2)
        server = DatabricksMCPServer.from_uc_function(
            catalog=catalog,
            schema=schema,
            function_name=function_name,
            name=f"uc-function-{function_name}",
        )
        servers.append((server, {full_name}))
    return servers


def _run_async(coro):
    """Run an async coroutine synchronously."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — create one.
        return asyncio.run(coro)
    else:
        # Already in an event loop — use run_coroutine_threadsafe or
        # create a task. For simplicity, create a new loop in a thread.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()


def _filter_by_uc_function_names(
    tools: list[Any],
    allowlisted_names: set[str],
) -> list[Any]:
    """Filter discovered tools to only those whose UC function name is allowlisted.

    Databricks managed MCP tools expose their UC function name through the
    tool metadata (commonly via ``tool.name`` matching a function's last segment,
    or via a custom attribute). We match against the full ``catalog.schema.function``
    format by checking the tool name against each allowlisted name's last segment
    and by checking any ``function_name`` attribute.
    """
    # Managed MCP currently exposes a UC function as a LangChain tool named
    # ``catalog__schema__function`` and puts catalog/schema in metadata. Keep
    # compatibility with full and short names too, because the client contract
    # can evolve independently of the governed function contract.
    short_names = {name.rpartition(".")[2] for name in allowlisted_names}
    encoded_full_names = {name.replace(".", "__") for name in allowlisted_names}

    filtered = []
    for tool in tools:
        tool_id = (
            getattr(tool, "function_name", None) or getattr(tool, "name", None) or ""
        )
        metadata = getattr(tool, "metadata", None) or {}
        metadata_full_name = ".".join(
            part
            for part in (
                metadata.get("catalog"),
                metadata.get("schema"),
                str(tool_id).rpartition("__")[2],
            )
            if part
        )
        if (
            tool_id in allowlisted_names
            or tool_id in short_names
            or tool_id in encoded_full_names
            or metadata_full_name in allowlisted_names
        ):
            filtered.append(tool)
        else:
            logger.debug(
                "Filtered out non-allowlisted tool: %s (id=%s)",
                getattr(tool, "name", "?"),
                tool_id,
            )
    logger.info(
        "MCP allowlisting: %d/%d tools passed filter",
        len(filtered),
        len(tools),
    )
    return filtered


def _assert_unique_tool_names(tools: list[Any]) -> None:
    """Reject ambiguous tool dispatch caused by duplicate MCP tool names."""
    names = [getattr(tool, "name", "") for tool in tools]
    duplicates = sorted({name for name in names if name and names.count(name) > 1})
    if duplicates:
        raise RuntimeError(
            "Managed MCP discovery returned duplicate tool name(s): "
            f"{', '.join(duplicates)}. Configure unique function names or "
            "separate the conflicting server exposure."
        )

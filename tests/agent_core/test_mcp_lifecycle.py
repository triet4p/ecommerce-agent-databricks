"""Network-free contract tests for managed MCP discovery (Sprint C8)."""

from types import SimpleNamespace

import pytest

from agent_core.config_schema import AgentConfig
from agent_core import mcp_lifecycle


def _config() -> AgentConfig:
    return AgentConfig.model_validate(
        {
            "use_case": "test",
            "system_prompt": "test",
            "llm": {"endpoint_name": "model"},
            "tools": [
                {
                    "kind": "uc_function",
                    "full_name": "ecommerce_agent.agent_layer.alpha",
                },
                {
                    "kind": "uc_function",
                    "full_name": "ecommerce_agent.agent_layer.beta",
                },
            ],
            "mcp_servers": [
                {
                    "name": "server-a",
                    "url": "https://a",
                    "uc_function_names": ["ecommerce_agent.agent_layer.alpha"],
                },
                {
                    "name": "server-b",
                    "url": "https://b",
                    "uc_function_names": ["ecommerce_agent.agent_layer.beta"],
                },
            ],
        }
    )


def test_allowlists_are_isolated_per_server(monkeypatch):
    monkeypatch.setattr(
        mcp_lifecycle,
        "DatabricksMCPServer",
        lambda name, url, headers=None: SimpleNamespace(name=name, url=url),
    )

    class FakeClient:
        def __init__(self, servers):
            self.server = servers[0].name

        async def get_tools(self):
            return [
                SimpleNamespace(
                    name="alpha", function_name="ecommerce_agent.agent_layer.alpha"
                ),
                SimpleNamespace(
                    name="beta", function_name="ecommerce_agent.agent_layer.beta"
                ),
            ]

    monkeypatch.setattr(mcp_lifecycle, "DatabricksMultiServerMCPClient", FakeClient)
    tools = mcp_lifecycle.resolve_mcp_uc_tools(_config())
    assert [tool.name for tool in tools] == ["alpha", "beta"]


def test_authentication_failure_identifies_server(monkeypatch):
    monkeypatch.setattr(
        mcp_lifecycle,
        "DatabricksMCPServer",
        lambda name, url, headers=None: SimpleNamespace(name=name, url=url),
    )

    class FailingClient:
        def __init__(self, servers):
            pass

        async def get_tools(self):
            raise PermissionError("401")

    monkeypatch.setattr(mcp_lifecycle, "DatabricksMultiServerMCPClient", FailingClient)
    with pytest.raises(RuntimeError, match="server 'server-a'.*401"):
        mcp_lifecycle.resolve_mcp_uc_tools(_config())


def test_duplicate_tool_names_are_rejected():
    with pytest.raises(RuntimeError, match="duplicate tool name.*alpha"):
        mcp_lifecycle._assert_unique_tool_names(
            [SimpleNamespace(name="alpha"), SimpleNamespace(name="alpha")]
        )


def test_discovery_delegates_session_cleanup_to_get_tools(monkeypatch):
    """The locked MCP client creates ephemeral sessions inside ``get_tools``."""
    monkeypatch.setattr(
        mcp_lifecycle,
        "DatabricksMCPServer",
        lambda name, url, headers=None: SimpleNamespace(name=name, url=url),
    )

    class CleanupManagedClient:
        session_called = False

        def __init__(self, servers):
            self.server = servers[0]

        async def get_tools(self):
            return [
                SimpleNamespace(
                    name="alpha", function_name="ecommerce_agent.agent_layer.alpha"
                )
            ]

        def session(self, *_args, **_kwargs):
            self.session_called = True
            raise AssertionError("discovery must not retain direct MCP sessions")

    monkeypatch.setattr(
        mcp_lifecycle, "DatabricksMultiServerMCPClient", CleanupManagedClient
    )
    tools = mcp_lifecycle.resolve_mcp_uc_tools(_config())
    assert [tool.name for tool in tools] == ["alpha"]
    assert not CleanupManagedClient.session_called


def test_current_uc_function_route_is_derived_without_workspace_url(monkeypatch):
    config = AgentConfig.model_validate(
        {
            "use_case": "test",
            "system_prompt": "test",
            "llm": {"endpoint_name": "model"},
            "tools": [
                {
                    "kind": "uc_function",
                    "full_name": "ecommerce_agent.agent_layer.get_order_status",
                }
            ],
        }
    )

    class CurrentServer:
        @classmethod
        def from_uc_function(cls, **kwargs):
            return SimpleNamespace(
                name=kwargs["name"], function_name=kwargs["function_name"]
            )

    class FakeClient:
        def __init__(self, servers):
            assert servers[0].function_name == "get_order_status"

        async def get_tools(self):
            return [
                SimpleNamespace(
                    name="get_order_status",
                    function_name="ecommerce_agent.agent_layer.get_order_status",
                )
            ]

    monkeypatch.setattr(mcp_lifecycle, "DatabricksMCPServer", CurrentServer)
    monkeypatch.setattr(mcp_lifecycle, "DatabricksMultiServerMCPClient", FakeClient)

    tools = mcp_lifecycle.resolve_mcp_uc_tools(config)
    assert [tool.name for tool in tools] == ["get_order_status"]


def test_allowlist_accepts_current_managed_mcp_encoded_tool_name():
    tools = mcp_lifecycle._filter_by_uc_function_names(
        [
            SimpleNamespace(
                name="ecommerce_agent__agent_layer__get_order_status",
                metadata={"catalog": "ecommerce_agent", "schema": "agent_layer"},
            )
        ],
        {"ecommerce_agent.agent_layer.get_order_status"},
    )
    assert [tool.name for tool in tools] == [
        "ecommerce_agent__agent_layer__get_order_status"
    ]

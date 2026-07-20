"""Contract tests for explicit Unity Catalog function transports."""

from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from agent_core.config_schema import AgentConfig, UCFunctionTransport
from agent_core.orchestrator import build_agent
from agent_core.tool_interface import resolve_uc_function_tools
from agent_core.uc_toolkit_adapter import build_uc_toolkit_tools


def _config(transport: str) -> AgentConfig:
    return AgentConfig.model_validate(
        {
            "use_case": "test",
            "system_prompt": "test",
            "llm": {"endpoint_name": "test-endpoint"},
            "uc_function_transport": transport,
            "tools": [
                {
                    "kind": "uc_function",
                    "full_name": "ecommerce_agent.agent_layer.get_order_status",
                }
            ],
        }
    )


def test_managed_mcp_transport_is_selected_explicitly():
    config = _config(UCFunctionTransport.MANAGED_MCP.value)
    expected = [Mock(name="mcp_tool")]

    with patch(
        "agent_core.mcp_lifecycle.resolve_mcp_uc_tools",
        return_value=expected,
    ) as resolve_mcp:
        assert resolve_uc_function_tools(config) == expected

    resolve_mcp.assert_called_once_with(config)


def test_uc_toolkit_transport_receives_explicit_client():
    config = _config(UCFunctionTransport.UC_TOOLKIT.value)
    client = Mock(name="uc_function_client")
    expected = [Mock(name="uc_tool")]

    with patch(
        "agent_core.uc_toolkit_adapter.build_uc_toolkit_tools",
        return_value=expected,
    ) as build_toolkit:
        assert resolve_uc_function_tools(config, client=client) == expected

    build_toolkit.assert_called_once_with(
        [config.tools[0]],
        client=client,
    )


def test_managed_mcp_failure_does_not_fallback_to_toolkit():
    config = _config(UCFunctionTransport.MANAGED_MCP.value)

    with (
        patch(
            "agent_core.mcp_lifecycle.resolve_mcp_uc_tools",
            side_effect=RuntimeError("MCP unavailable"),
        ),
        patch("agent_core.uc_toolkit_adapter.build_uc_toolkit_tools") as build_toolkit,
        pytest.raises(RuntimeError, match="MCP unavailable"),
    ):
        resolve_uc_function_tools(config)

    build_toolkit.assert_not_called()


def test_invalid_transport_is_rejected_by_config():
    with pytest.raises(ValidationError, match="uc_function_transport"):
        _config("automatic_fallback")


def test_toolkit_adapter_passes_injected_client_to_public_toolkit():
    config = _config(UCFunctionTransport.UC_TOOLKIT.value)
    client = Mock(name="uc_function_client")
    expected_tools = [Mock(name="uc_tool")]

    class FakeToolkit:
        def __init__(self, *, function_names, client):
            self.function_names = function_names
            self.client = client
            self.tools = expected_tools

    with patch(
        "agent_core.uc_toolkit_adapter.UCFunctionToolkit",
        FakeToolkit,
    ):
        tools = build_uc_toolkit_tools([config.tools[0]], client=client)

    assert tools == expected_tools


def test_toolkit_adapter_constructs_current_databricks_client_when_omitted():
    config = _config(UCFunctionTransport.UC_TOOLKIT.value)
    default_client = Mock(name="default_databricks_function_client")

    class FakeToolkit:
        def __init__(self, *, function_names, client):
            self.tools = [client]

    with (
        patch(
            "agent_core.uc_toolkit_adapter.DatabricksFunctionClient",
            return_value=default_client,
        ) as client_factory,
        patch("agent_core.uc_toolkit_adapter.UCFunctionToolkit", FakeToolkit),
    ):
        tools = build_uc_toolkit_tools([config.tools[0]])

    client_factory.assert_called_once_with()
    assert tools == [default_client]


def test_build_agent_passes_client_through_selected_toolkit_transport():
    from langchain_core.tools import tool

    config = _config(UCFunctionTransport.UC_TOOLKIT.value)
    client = Mock(name="uc_function_client")

    @tool
    def get_order_status(order_id: str) -> str:
        """Return a test order status."""
        return order_id

    with (
        patch(
            "agent_core.uc_toolkit_adapter.build_uc_toolkit_tools",
            return_value=[get_order_status],
        ) as build_toolkit,
        patch("agent_core.orchestrator.ChatDatabricks", return_value=object()),
        patch(
            "agent_core.orchestrator.create_agent",
            side_effect=lambda **kwargs: kwargs,
        ),
    ):
        agent = build_agent(config, uc_function_client=client)

    build_toolkit.assert_called_once_with(
        [config.tools[0]],
        client=client,
    )
    assert [tool.name for tool in agent.graph["tools"]] == ["get_order_status"]

"""
Tests for local function tool building (Sprint 1 tasks C3, C4).

Verifies that local_function tool configs are correctly resolved from
dotted function_ref paths and produce callable LangChain tools.
"""

import pytest

from agent_core.config_schema import LocalFunctionToolConfig
from agent_core.tool_interface import _build_local_function_tool


class TestBuildLocalFunctionTool:
    def test_import_local_function_by_ref(self):
        """Build a local_function tool from a dotted import path."""
        config = LocalFunctionToolConfig(
            name="compute_delay_severity",
            description="Classify delivery delay severity",
            function_ref="ecommerce_agent.tools.python_tools.compute_delay_severity",
        )
        tool = _build_local_function_tool(config)
        assert tool.name == "compute_delay_severity"
        assert hasattr(tool, "invoke")
        assert hasattr(tool, "func")

    def test_local_tool_executes_correctly(self):
        """The wrapped tool should produce the expected output."""
        config = LocalFunctionToolConfig(
            name="compute_delay_severity",
            description="Classify delivery delay severity",
            function_ref="ecommerce_agent.tools.python_tools.compute_delay_severity",
        )
        tool = _build_local_function_tool(config)
        from datetime import date

        result = tool.invoke(
            {
                "estimated_delivery_date": date(2024, 1, 10),
                "actual_delivery_date": date(2024, 1, 5),
            }
        )
        assert result == "none"

    def test_customer_value_score_tool(self):
        """Build and invoke the customer_value_score tool."""
        config = LocalFunctionToolConfig(
            name="customer_value_score",
            description="Calculate customer value score",
            function_ref="ecommerce_agent.tools.python_tools.customer_value_score",
        )
        tool = _build_local_function_tool(config)
        result = tool.invoke(
            {
                "total_orders": 10,
                "total_spent": 500.0,
                "avg_review_score": 4.5,
            }
        )
        assert 0 <= result <= 100

    def test_non_existent_function_ref_fails(self):
        """A non-existent function_ref should raise ImportError."""
        config = LocalFunctionToolConfig(
            name="bad_tool",
            description="This tool should fail to build",
            function_ref="non_existent_module.function_does_not_exist",
        )
        with pytest.raises((ImportError, ModuleNotFoundError, AttributeError)):
            _build_local_function_tool(config)

    def test_tool_has_description(self):
        """The built tool should have the configured description."""
        config = LocalFunctionToolConfig(
            name="test_tool",
            description="A test tool description",
            function_ref="ecommerce_agent.tools.python_tools.compute_delay_severity",
        )
        tool = _build_local_function_tool(config)
        assert tool.description == config.description

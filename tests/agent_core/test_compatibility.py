"""
Compatibility tests for Sprint 1 (task A3).

Verifies that every public ``agent_core`` API and the ``ecommerce_agent``
entrypoint can be imported on the locked dependency environment.
"""


class TestAgentCoreCompatibility:
    """Verify all public agent_core APIs import correctly."""

    def test_import_agent_core(self):
        from agent_core import AgentConfig, UCFunctionTransport

        assert AgentConfig is not None
        assert UCFunctionTransport is not None

    def test_import_config_loader(self):
        from agent_core.config_loader import load_config

        assert load_config is not None

    def test_import_orchestrator(self):
        from agent_core.orchestrator import CoreAgent

        assert CoreAgent is not None

    def test_import_tool_interface(self):
        from agent_core.tool_interface import ToolRegistry

        assert ToolRegistry is not None

    def test_import_tool_policy(self):
        from agent_core.tool_policy import OperationGate

        assert OperationGate is not None

    def test_import_mcp_lifecycle(self):
        from agent_core.mcp_lifecycle import build_mcp_server_configs

        assert build_mcp_server_configs is not None

    def test_import_prompt_registry(self):
        from agent_core.prompt_registry import resolve_system_prompt

        assert resolve_system_prompt is not None

    def test_import_retriever_interface(self):
        from agent_core.retriever_interface import Retriever

        assert Retriever is not None

    def test_import_skill_interface(self):
        from agent_core.skill_interface import SkillLibrary

        assert SkillLibrary is not None

    def test_import_uc_toolkit_adapter(self):
        from agent_core.uc_toolkit_adapter import build_uc_toolkit_tools

        assert build_uc_toolkit_tools is not None


class TestEcommerceAgentCompatibility:
    """Verify ecommerce_agent entrypoint imports."""

    def test_import_config(self):
        """Config should be loadable and valid."""
        import yaml
        from pathlib import Path

        config_path = (
            Path(__file__).resolve().parents[2] / "ecommerce_agent" / "config.yaml"
        )
        assert config_path.is_file()

        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert raw is not None
        assert raw["use_case"] == "ecommerce_support"
        assert "llm" in raw
        assert "endpoint_name" in raw["llm"]

    def test_import_tools(self):
        from ecommerce_agent.tools.python_tools import compute_delay_severity

        assert compute_delay_severity is not None

    def test_import_search_tool(self):
        from ecommerce_agent.tools.search_policy_docs_tool import (
            make_search_policy_docs_tool,
        )

        assert make_search_policy_docs_tool is not None

    def test_sql_ddl_importable(self):
        from ecommerce_agent.tools.sql_tools import ALL_DDL

        assert len(ALL_DDL) == 4

    def test_config_loads_with_agent_core(self):
        """Validate that config.yaml can be loaded through agent_core's public API."""
        from pathlib import Path

        from agent_core import load_config

        config_path = (
            Path(__file__).resolve().parents[2] / "ecommerce_agent" / "config.yaml"
        )
        config = load_config(str(config_path))
        assert config.use_case == "ecommerce_support"
        assert config.llm.endpoint_name == "deepseek-v4-streaming-agent-lab"
        assert len(config.tools) > 0

    def test_agent_builds_with_registry(self):
        """Verify agent can be built with ToolRegistry via public API."""
        from pathlib import Path

        from agent_core import ToolRegistry, build_agent, load_config

        config_path = (
            Path(__file__).resolve().parents[2] / "ecommerce_agent" / "config.yaml"
        )
        config = load_config(str(config_path))
        # Managed MCP is credentialed integration behavior. This public-core
        # compatibility test intentionally builds only the locally resolvable
        # tool set; live MCP discovery has its own gated contracts.
        config = config.model_copy(
            update={
                "tools": [
                    tool_config
                    for tool_config in config.tools
                    if tool_config.kind.value != "uc_function"
                ]
            }
        )

        # Register a mock factory for the serving endpoint tool so the build
        # completes without needing a real WorkspaceClient.
        from langchain_core.tools import tool as lc_tool

        registry = ToolRegistry()

        @lc_tool
        def mock_search(query: str) -> str:
            """Mock search tool."""
            return f"mock result for: {query}"

        # The factory receives a config and returns a callable
        registry.register_serving_factory("search_policy_docs", lambda tc: mock_search)

        # Build agent — tests that the full pipeline works.
        agent = build_agent(config, registry=registry)
        assert agent is not None
        # CoreAgent should have an OperationGate
        assert hasattr(agent, "operation_gate")

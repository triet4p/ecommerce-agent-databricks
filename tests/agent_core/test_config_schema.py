"""
Config schema validation tests (Sprint 1 tasks B3, C3).

Tests for:
- Valid input with all tool kinds
- Missing required keys
- Invalid tool unions
- Working-directory-independent path resolution
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_core.config_schema import (
    AgentConfig,
    LLMConfig,
    ToolKind,
    UCFunctionTransport,
    UCFunctionToolConfig,
    LocalFunctionToolConfig,
    ServingEndpointToolConfig,
    ManagedMCPServerConfig,
)


class TestLLMConfig:
    def test_valid_llm_config(self):
        cfg = LLMConfig(endpoint_name="test-endpoint", temperature=0.5, max_tokens=2000)
        assert cfg.endpoint_name == "test-endpoint"
        assert cfg.temperature == 0.5
        assert cfg.max_tokens == 2000

    def test_default_temperature_and_tokens(self):
        cfg = LLMConfig(endpoint_name="test-endpoint")
        assert cfg.temperature == 0.0
        assert cfg.max_tokens == 1500

    def test_missing_endpoint_name_fails(self):
        with pytest.raises(ValidationError):
            LLMConfig()

    def test_no_provider_field(self):
        """LLMConfig should not have a provider field (removed in Sprint 1)."""
        cfg = LLMConfig(endpoint_name="test-endpoint")
        assert not hasattr(cfg, "provider")

    def test_no_model_name_field(self):
        """LLMConfig should use endpoint_name, not model_name."""
        cfg = LLMConfig(endpoint_name="test-endpoint")
        assert not hasattr(cfg, "model_name")


class TestToolConfigUnion:
    def test_uc_function_config(self):
        cfg = UCFunctionToolConfig(full_name="catalog.schema.function_name")
        assert cfg.kind == ToolKind.UC_FUNCTION
        assert cfg.full_name == "catalog.schema.function_name"

    def test_local_function_config(self):
        cfg = LocalFunctionToolConfig(
            name="my_tool",
            description="A local deterministic tool",
            function_ref="ecommerce_agent.tools.python_tools.compute_delay_severity",
        )
        assert cfg.kind == ToolKind.LOCAL_FUNCTION
        assert cfg.name == "my_tool"

    def test_serving_endpoint_config(self):
        cfg = ServingEndpointToolConfig(
            name="search_tool",
            endpoint_name="search-endpoint",
            description="Searches documents",
        )
        assert cfg.kind == ToolKind.SERVING_ENDPOINT
        assert cfg.endpoint_name == "search-endpoint"

    def test_invalid_tool_kind_fails(self):
        with pytest.raises(ValidationError):
            UCFunctionToolConfig(kind="invalid_kind", full_name="c.s.f")

    def test_discriminated_union_roundtrip(self):
        """AgentConfig should correctly parse all three tool kinds from YAML."""
        raw = {
            "use_case": "test",
            "system_prompt": "You are a test agent.",
            "llm": {"endpoint_name": "test-llm"},
            "tools": [
                {"kind": "uc_function", "full_name": "catalog.schema.func1"},
                {
                    "kind": "local_function",
                    "name": "local1",
                    "description": "A local tool",
                    "function_ref": "mod.fn",
                },
                {
                    "kind": "serving_endpoint",
                    "name": "serving1",
                    "endpoint_name": "ep1",
                    "description": "A serving tool",
                },
            ],
        }
        config = AgentConfig.model_validate(raw)
        assert len(config.tools) == 3
        assert isinstance(config.tools[0], UCFunctionToolConfig)
        assert isinstance(config.tools[1], LocalFunctionToolConfig)
        assert isinstance(config.tools[2], ServingEndpointToolConfig)

    def test_empty_tools_list(self):
        raw = {
            "use_case": "test",
            "system_prompt": "You are a test agent.",
            "llm": {"endpoint_name": "test-llm"},
        }
        config = AgentConfig.model_validate(raw)
        assert config.tools == []


class TestManagedMCPServerConfig:
    MCP_URL = "https://test.workspace.databricks.com/api/2.0/mcp/functions/ecommerce_agent/agent_layer/get_order_status"

    def test_valid_mcp_config(self):
        cfg = ManagedMCPServerConfig(
            name="my_mcp",
            url=self.MCP_URL,
            uc_function_names=["catalog.schema.func1", "catalog.schema.func2"],
        )
        assert cfg.name == "my_mcp"
        assert cfg.url == self.MCP_URL
        assert len(cfg.uc_function_names) == 2

    def test_missing_url_fails(self):
        with pytest.raises(ValidationError, match="url"):
            ManagedMCPServerConfig(name="my_mcp")

    def test_with_description(self):
        cfg = ManagedMCPServerConfig(
            name="my_mcp",
            url=self.MCP_URL,
            uc_function_names=["c.s.f"],
            description="My MCP server",
        )
        assert cfg.description == "My MCP server"


class TestAgentConfigFull:
    def test_minimal_config(self):
        raw = {
            "use_case": "test",
            "system_prompt": "You are a test agent.",
            "llm": {"endpoint_name": "test-llm"},
        }
        config = AgentConfig.model_validate(raw)
        assert config.use_case == "test"
        assert config.llm.endpoint_name == "test-llm"
        assert config.uc_function_transport == UCFunctionTransport.MANAGED_MCP

    def test_uc_toolkit_transport(self):
        raw = {
            "use_case": "test",
            "system_prompt": "test",
            "llm": {"endpoint_name": "test-llm"},
            "uc_function_transport": "uc_toolkit",
        }
        config = AgentConfig.model_validate(raw)
        assert config.uc_function_transport == UCFunctionTransport.UC_TOOLKIT

    def test_full_config_with_yaml(self):
        """Parse a realistic full config."""
        raw = {
            "use_case": "ecommerce_support",
            "system_prompt": "You are an e-commerce support agent.",
            "llm": {
                "endpoint_name": "test-llm",
                "temperature": 0.1,
                "max_tokens": 2000,
            },
            "tools": [
                {"kind": "uc_function", "full_name": "catalog.schema.get_order_status"},
                {
                    "kind": "local_function",
                    "name": "compute_score",
                    "description": "Score",
                    "function_ref": "mod.fn",
                },
            ],
            "rules": {"paths": ["rules/rule1.md", "rules/rule2.md"]},
            "skills": {"source_dir": "skills"},
            "mcp_servers": [
                {
                    "name": "uc_mcp",
                    "url": "https://test.databricks.com/api/2.0/mcp/functions/ecommerce_agent/agent_layer/get_order_status",
                    "uc_function_names": ["catalog.schema.get_order_status"],
                },
            ],
            "retriever": {"endpoint_name": "rerank-ep", "top_k": 5},
        }
        config = AgentConfig.model_validate(raw)
        assert len(config.tools) == 2
        assert len(config.mcp_servers) == 1
        assert config.retriever is not None
        assert config.retriever.endpoint_name == "rerank-ep"

    def test_missing_use_case_fails(self):
        with pytest.raises(ValidationError):
            AgentConfig.model_validate(
                {
                    "system_prompt": "test",
                    "llm": {"endpoint_name": "test-llm"},
                }
            )

    def test_missing_llm_fails(self):
        with pytest.raises(ValidationError):
            AgentConfig.model_validate(
                {
                    "use_case": "test",
                    "system_prompt": "test",
                }
            )

    def test_no_compute_type_field(self):
        """AgentConfig should not have a compute_type field (removed in Sprint 1)."""
        raw = {
            "use_case": "test",
            "system_prompt": "test",
            "llm": {"endpoint_name": "test-llm"},
        }
        config = AgentConfig.model_validate(raw)
        assert not hasattr(config, "compute_type")


class TestConfigPathResolution:
    def test_config_loader_resolves_paths(self):
        """Verify that load_config resolves relative paths."""
        from agent_core.config_loader import load_config

        config_path = (
            Path(__file__).resolve().parents[2] / "ecommerce_agent" / "config.yaml"
        )
        assert config_path.is_file()

        config = load_config(str(config_path))
        assert config.rules is not None
        assert len(config.rules.paths) > 0

        # Paths should now be absolute
        for p in config.rules.paths:
            assert Path(p).is_absolute(), f"Path {p} should be absolute"

        # Skills source_dir should be absolute
        if config.skills:
            assert Path(config.skills.source_dir).is_absolute(), (
                "Skills source_dir should be absolute"
            )

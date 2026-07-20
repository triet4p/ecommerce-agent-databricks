"""
agent_core.config_schema
-------------------------
Project-agnostic config contract. Every Fat Module (config.yaml)
must validate against this schema. The Agent Core NEVER imports anything from a
specific project — it only ever sees a `AgentConfig` instance.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum


class ToolKind(str, Enum):
    """How a tool is executed. Determines which adapter agent_core.tool_interface uses."""

    UC_FUNCTION = "uc_function"  # SQL or Python, governed by Unity Catalog
    SERVING_ENDPOINT = "serving_endpoint"  # heavy tool (network egress / model load), wrapped as a @tool
    LOCAL_FUNCTION = (
        "local_function"  # deterministic local calculation, no external resource needed
    )


class UCFunctionTransport(str, Enum):
    """Explicit transport used to expose configured Unity Catalog functions."""

    MANAGED_MCP = "managed_mcp"
    UC_TOOLKIT = "uc_toolkit"


class UCFunctionToolConfig(BaseModel):
    kind: Literal[ToolKind.UC_FUNCTION] = ToolKind.UC_FUNCTION
    full_name: str = Field(
        ...,
        description="catalog.schema.function_name, e.g. ecommerce_agent.agent_layer.get_order_status",
    )


class LocalFunctionToolConfig(BaseModel):
    kind: Literal[ToolKind.LOCAL_FUNCTION] = ToolKind.LOCAL_FUNCTION
    name: str = Field(
        ...,
        description="Logical tool name exposed to the LLM, e.g. compute_delay_severity",
    )
    description: str = Field(
        ..., description="Tool description shown to the LLM for tool selection"
    )
    function_ref: str = Field(
        ...,
        description="Dotted import path to the implementation function, e.g. ecommerce_agent.tools.python_tools.compute_delay_severity",
    )


class ServingEndpointToolConfig(BaseModel):
    kind: Literal[ToolKind.SERVING_ENDPOINT] = ToolKind.SERVING_ENDPOINT
    name: str = Field(
        ..., description="Logical tool name exposed to the LLM, e.g. search_policy_docs"
    )
    endpoint_name: str = Field(
        ..., description="Databricks Model Serving endpoint name"
    )
    description: str = Field(
        ..., description="Tool description shown to the LLM for tool selection"
    )


ToolConfig = UCFunctionToolConfig | LocalFunctionToolConfig | ServingEndpointToolConfig


class RetrieverConfig(BaseModel):
    """Only populated if the Fat Module has a RAG component."""

    endpoint_name: str
    over_fetch_k: int = 20
    top_k: int = 5
    timeout_seconds: float = Field(default=60.0, gt=0)
    cold_start_retry_attempts: int = Field(default=1, ge=0, le=3)


class LLMConfig(BaseModel):
    endpoint_name: str = Field(
        ...,
        description="Databricks Model Serving endpoint name, e.g. databricks-meta-llama-3-3-70b-instruct",
    )
    temperature: float = 0.0
    max_tokens: int = 1500


class RulesConfig(BaseModel):
    """Always-loaded instructions — concatenated into the system prompt once at build time.
    Keep this list short; every path here is paid for on every single request."""

    paths: list[str] = Field(
        default_factory=list,
        description="Repository-relative paths to small .md rule files, resolved by the config loader against the config file directory",
    )


class SkillMeta(BaseModel):
    name: str
    description: str
    path: str


class SkillsConfig(BaseModel):
    """Progressive-disclosure skill library — agent sees only name+description by default,
    pulls full content on demand via the load_skill tool. Scales to a large library
    without inflating the system prompt.

    Skills are loaded from the application source tree by default.
    A Unity Catalog Volume can be configured as a separate opt-in provider
    (see the project documentation for the Volume provider pattern)."""

    source_dir: str = Field(
        default="skills",
        description="Directory path (relative to config file or absolute) containing skill .md files",
    )


class ManagedMCPServerConfig(BaseModel):
    """Typed config for a single managed MCP server that proxies Unity Catalog functions."""

    name: str = Field(..., description="Logical name for this MCP server connection")
    url: str = Field(
        ...,
        description=(
            "Managed MCP endpoint URL. For Unity Catalog functions prefer "
            "DatabricksMCPServer.from_uc_function(), which derives "
            "/api/2.0/mcp/functions/<catalog>/<schema>/<function> "
            "without checking in a workspace hostname."
        ),
    )
    uc_function_names: list[str] | None = Field(
        default=None,
        description="Optional allowlist of full catalog.schema.function names to expose from this server. If None, all available functions are exposed.",
    )
    headers: dict[str, str] | None = Field(
        default=None, description="Optional HTTP headers for MCP server authentication"
    )
    description: str | None = Field(
        default=None, description="Optional description visible to the agent"
    )


class AgentConfig(BaseModel):
    """Root config loaded from ecommerce_agent/config.yaml."""

    use_case: str
    system_prompt: str
    llm: LLMConfig
    tools: list[ToolConfig] = Field(default_factory=list)
    uc_function_transport: UCFunctionTransport = Field(
        default=UCFunctionTransport.MANAGED_MCP,
        description=(
            "Explicit UC function transport. Both managed_mcp and uc_toolkit are "
            "supported; the selected transport is used without automatic fallback."
        ),
    )
    retriever: RetrieverConfig | None = None
    rules: RulesConfig | None = None
    skills: SkillsConfig | None = None
    mcp_servers: list[ManagedMCPServerConfig] = Field(
        default_factory=list,
        description="Managed MCP server configurations for UC function discovery",
    )
    system_prompt_registry_uri: str | None = Field(
        default=None,
        description=(
            "Optional MLflow Prompt Registry URI, e.g. "
            "'prompts:/ecommerce_agent.agent_layer.ecommerce_support_system_prompt@production' "
            "(Databricks-UC registry requires the full catalog.schema.name form, and '@alias' "
            "not '/alias'). When set, this WINS over `system_prompt` at build time — "
            "`system_prompt` stays as the local dev fallback / the value used to seed the "
            "registry the first time. See agent_core.prompt_registry."
        ),
    )

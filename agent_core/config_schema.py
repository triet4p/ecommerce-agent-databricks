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

    UC_FUNCTION = "uc_function"      # SQL or lightweight Python, governed by Unity Catalog
    SERVING_ENDPOINT = "serving_endpoint"  # heavy tool (network egress / model load), wrapped as a thin @tool


class UCFunctionToolConfig(BaseModel):
    kind: Literal[ToolKind.UC_FUNCTION] = ToolKind.UC_FUNCTION
    full_name: str = Field(..., description="catalog.schema.function_name, e.g. ecommerce_demo.agent.get_order_status")


class ServingEndpointToolConfig(BaseModel):
    kind: Literal[ToolKind.SERVING_ENDPOINT] = ToolKind.SERVING_ENDPOINT
    name: str = Field(..., description="Logical tool name exposed to the LLM, e.g. search_policy_docs")
    endpoint_name: str = Field(..., description="Databricks Model Serving endpoint name")
    description: str = Field(..., description="Tool description shown to the LLM for tool selection")


ToolConfig = UCFunctionToolConfig | ServingEndpointToolConfig


class RetrieverConfig(BaseModel):
    """Only populated if the Fat Module has a RAG component."""

    endpoint_name: str
    over_fetch_k: int = 20
    top_k: int = 5


class LLMConfig(BaseModel):
    model_name: str = Field(..., description="Databricks Foundation Model / external model serving endpoint")
    provider: str = Field(..., description="Databricks Foundation Model provider, e.g. 'databricks' or 'openai'")
    temperature: float = 0.0
    max_tokens: int = 1500


class RulesConfig(BaseModel):
    """Always-loaded instructions — concatenated into the system prompt once at build time.
    Keep this list short; every path here is paid for on every single request."""

    paths: list[str] = Field(default_factory=list, description="Paths to small .md rule files")

class SkillMeta(BaseModel):
    name: str
    description: str
    path: str

class SkillsConfig(BaseModel):
    """Progressive-disclosure skill library — agent sees only name+description by default,
    pulls full content on demand via the load_skill tool. Scales to a large library
    without inflating the system prompt."""

    volume_path: str = Field(..., description="UC Volume path holding skill .md files, e.g. /Volumes/catalog/schema/skills")


class AgentConfig(BaseModel):
    """Root config loaded from projects/<use_case>/config.yaml."""

    use_case: str
    system_prompt: str
    llm: LLMConfig
    tools: list[ToolConfig] = Field(default_factory=list)
    retriever: RetrieverConfig | None = None
    rules: RulesConfig | None = None
    skills: SkillsConfig | None = None
    compute_type: str | None = Field(default="serverless", description="Optional Databricks cluster compute type for LLM inference")
    system_prompt_registry_uri: str | None = Field(
        default=None,
        description=(
            "Optional MLflow Prompt Registry URI, e.g. "
            "'prompts:/ecommerce_demo.agent.ecommerce_support_system_prompt@production' "
            "(Databricks-UC registry requires the full catalog.schema.name form, and '@alias' "
            "not '/alias'). When set, this WINS over `system_prompt` at build time — "
            "`system_prompt` stays as the local dev fallback / the value used to seed the "
            "registry the first time. See agent_core.prompt_registry."
        ),
    )
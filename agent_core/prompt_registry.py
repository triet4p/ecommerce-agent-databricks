"""
agent_core.prompt_registry
------------------------------
Additive: nếu `system_prompt_registry_uri` KHÔNG được set trong config.yaml, mọi thứ
hoạt động y hệt trước đây (dùng thẳng `system_prompt` string). Chỉ khi Fat Module chủ
động điền URI thì mới chuyển sang load version từ MLflow Prompt Registry — đúng
objective "prompt version control" (MLflow 3) trong exam guide, không đổi code cũ.
"""

from __future__ import annotations

from agent_core.config_schema import AgentConfig


def resolve_system_prompt(config: AgentConfig) -> str:
    """Prompt Registry version thắng khi có set; fallback về `system_prompt` inline."""
    if config.system_prompt_registry_uri:
        import mlflow

        prompt = mlflow.genai.load_prompt(config.system_prompt_registry_uri)
        return prompt.template
    return config.system_prompt

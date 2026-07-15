"""
projects.ecommerce_support.tools.search_policy_docs_tool
-----------------------------------------------------------
Fat Module implementation của tool "nặng" `search_policy_docs`. Không load model gì
ở đây — chỉ gọi HTTP tới Model Serving endpoint qua `agent_core.retriever_interface.Retriever`.
"""

from __future__ import annotations

from langchain_core.tools import tool

from agent_core.config_schema import ServingEndpointToolConfig
from agent_core.retriever_interface import Retriever


def make_search_policy_docs_tool(retriever: Retriever, config: ServingEndpointToolConfig):
    @tool(config.name)
    def search_policy_docs(query: str) -> str:
        """Tìm trong tài liệu chính sách (return, shipping, LGPD, seller conduct) đoạn
        văn bản liên quan nhất tới câu hỏi của khách hàng, kèm nguồn tài liệu."""
        results = retriever.search(query)
        return "\n\n".join(
            f"[{r['source_file']}] {r['content']}" for r in results
        )

    search_policy_docs.description = config.description
    return search_policy_docs

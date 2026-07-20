"""
ecommerce_agent.tools.search_policy_docs_tool
-----------------------------------------------
Fat Module implementation of the ``search_policy_docs`` serving-endpoint tool.
Does not load any model — only calls the Model Serving endpoint via
``agent_core.retriever_interface.Retriever``.
"""

from __future__ import annotations

from langchain_core.tools import tool

from agent_core import Retriever, ServingEndpointToolConfig


def _format_retrieval_result(source_file: str, content: str) -> str:
    """Render source-provided text as content, never as executable markup."""
    safe_source = source_file.replace("[", "(").replace("]", ")").replace("\n", " ")
    return f"[{safe_source}] {content}"


def make_search_policy_docs_tool(
    retriever: Retriever, config: ServingEndpointToolConfig
):
    @tool(config.name)
    def search_policy_docs(query: str) -> str:
        """Search policy documents (return, shipping, LGPD, seller conduct) for
        the most relevant excerpts matching the customer's question, with source attribution."""
        results = retriever.search(query)
        if not results:
            return "No relevant policy documents found."
        return "\n\n".join(
            _format_retrieval_result(r.source_file, r.content) for r in results
        )

    search_policy_docs.description = config.description
    return search_policy_docs

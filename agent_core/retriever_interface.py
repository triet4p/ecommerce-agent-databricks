"""
agent_core.retriever_interface
--------------------------------
Thin, project-agnostic wrapper around a `search-and-rerank` Model Serving endpoint.
Agent Core only knows "give me top_k chunks for this query" — it has no knowledge of
Vector Search, the cross-encoder, or how the pyfunc was packaged.

If a Fat Module has no RAG component, it simply omits `retriever` in config.yaml and
never calls this module.
"""

from __future__ import annotations

from agent_core.config_schema import RetrieverConfig


class Retriever:
    def __init__(self, config: RetrieverConfig):
        self._config = config
        # Lazy import: keeps agent_core importable outside a Databricks runtime (e.g. unit tests)
        from databricks.sdk import WorkspaceClient

        self._client = WorkspaceClient()

    def search(self, query: str, *, top_k: int | None = None) -> list[dict]:
        """Returns a list of {"content": str, "source_file": str, "score": float} dicts."""
        from databricks.sdk.service.serving import DataframeSplitInput

        payload = DataframeSplitInput(
            columns=["query_text", "top_k", "over_fetch_k"],
            data=[[query, top_k or self._config.top_k, self._config.over_fetch_k]],
        )
        response = self._client.serving_endpoints.query(
            name=self._config.endpoint_name,
            dataframe_split=payload,
        )
        return response.predictions

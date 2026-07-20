"""
agent_core.retriever_interface
--------------------------------
Thin, project-agnostic wrapper around a ``search-and-rerank`` Model Serving endpoint.
Agent Core only knows "give me top_k chunks for this query" — it has no knowledge of
Vector Search, the cross-encoder, or how the pyfunc was packaged.

If a Fat Module has no RAG component, it simply omits ``retriever`` in config.yaml and
never calls this module.
"""

from __future__ import annotations

import logging
import json
import math
import time
from typing import Any

from pydantic import BaseModel, Field

from agent_core.config_schema import RetrieverConfig

logger = logging.getLogger(__name__)

# Default timeout in seconds for serving endpoint calls.
_DEFAULT_TIMEOUT_SECONDS = 60.0


class RetrievalRequest(BaseModel):
    """Validated payload sent to the custom search-and-rerank endpoint."""

    query_text: str = Field(min_length=1)
    top_k: int = Field(ge=1)
    over_fetch_k: int = Field(ge=1)


class RetrievalResult(BaseModel):
    """Typed result from a single retrieved document.

    Attributes:
        content: The text content of the retrieved chunk.
        source_file: The source document identifier.
        score: The relevance score from the reranker.
    """

    content: str
    source_file: str
    score: float

    @classmethod
    def from_prediction(cls, pred: dict[str, Any]) -> RetrievalResult:
        """Construct from a raw prediction dict, handling malformed data."""
        content = pred.get("content") or pred.get("text") or ""
        source_file = pred.get("source_file") or pred.get("source") or "unknown"
        try:
            score = float(pred.get("score", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        return cls(content=str(content), source_file=str(source_file), score=score)


def _expand_prediction(prediction: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize direct chunks and the deployed model's ``results_json`` envelope."""
    results_json = prediction.get("results_json")
    if results_json is None:
        return [prediction]
    if not isinstance(results_json, str):
        raise ValueError("results_json must be a JSON string")
    decoded = json.loads(results_json)
    if not isinstance(decoded, list) or not all(
        isinstance(item, dict) for item in decoded
    ):
        raise ValueError("results_json must decode to a list of objects")
    return decoded


class Retriever:
    """Wrapper around a search-and-rerank Model Serving endpoint.

    Args:
        config: Retriever configuration with endpoint name and fetch parameters.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        config: RetrieverConfig,
        timeout: float | None = None,
        *,
        client: Any | None = None,
    ):
        self._config = config
        self._timeout = timeout if timeout is not None else config.timeout_seconds
        if self._timeout <= 0:
            raise ValueError("Retriever timeout must be greater than zero")
        if client is None:
            # Lazy imports keep agent_core importable outside a Databricks runtime.
            # ``serving_endpoints.query`` has no supported per-call timeout in SDK
            # 0.120.0.  Configure the transport instead so a timed-out HTTP call is
            # actually terminated rather than left running in a worker thread.
            from databricks.sdk import WorkspaceClient
            from databricks.sdk.config import Config

            client = WorkspaceClient(
                config=Config(
                    http_timeout_seconds=self._timeout,
                    retry_timeout_seconds=math.ceil(self._timeout),
                )
            )
        self._client = client

    def search(self, query: str, *, top_k: int | None = None) -> list[RetrievalResult]:
        """Search and rerank for the given query.

        Args:
            query: The search query string.
            top_k: Override for the default top_k from config.

        Returns:
            A list of ``RetrievalResult`` instances, ordered by score descending.

        Raises:
            RuntimeError: If the endpoint call fails or returns malformed data.
        """
        request = RetrievalRequest(
            query_text=query,
            top_k=top_k or self._config.top_k,
            over_fetch_k=self._config.over_fetch_k,
        )

        from databricks.sdk.service.serving import DataframeSplitInput

        payload = DataframeSplitInput(
            columns=["query_text", "top_k", "over_fetch_k"],
            data=[[request.query_text, request.top_k, request.over_fetch_k]],
        )

        try:
            response = self._query_with_cold_start_retry(payload)
        except TimeoutError as exc:
            raise TimeoutError(
                f"Retriever endpoint '{self._config.endpoint_name}' timed out after "
                f"{self._timeout:g}s"
            ) from exc
        except Exception as e:
            raise RuntimeError(
                f"Retriever endpoint '{self._config.endpoint_name}' failed: {e}"
            ) from e

        predictions = getattr(response, "predictions", None) or []
        if not predictions:
            logger.info("Retriever returned empty results for query '%s'", query[:50])
            return []

        results = []
        for pred in predictions:
            if not isinstance(pred, dict):
                raise RuntimeError(
                    "Retriever endpoint returned a malformed prediction: "
                    f"expected object, got {type(pred).__name__}"
                )
            try:
                for chunk in _expand_prediction(pred):
                    normalized = dict(chunk)
                    if "score" not in normalized and "rerank_score" in normalized:
                        normalized["score"] = normalized["rerank_score"]
                    results.append(RetrievalResult.from_prediction(normalized))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    "Retriever endpoint returned a malformed prediction envelope"
                ) from exc

        # Sort by score descending.
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _query(self, payload: Any) -> Any:
        """Call the endpoint using the configured SDK transport timeout.

        Callers that inject a client own that client's transport configuration;
        the default client is constructed with ``self._timeout`` above.
        """
        return self._client.serving_endpoints.query(
            name=self._config.endpoint_name,
            dataframe_split=payload,
        )

    def _query_with_cold_start_retry(self, payload: Any) -> Any:
        """Retry bounded timeout failures once the endpoint has had time to warm."""
        for attempt in range(self._config.cold_start_retry_attempts + 1):
            try:
                return self._query(payload)
            except TimeoutError:
                if attempt >= self._config.cold_start_retry_attempts:
                    raise
                # Bounded, short pause avoids an immediate retry while a
                # scale-to-zero endpoint is still becoming queryable.
                time.sleep(min(1.0, 0.25 * (attempt + 1)))
        raise AssertionError("unreachable")

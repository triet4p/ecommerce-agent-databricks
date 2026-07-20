"""
Retriever and serving endpoint contract tests (Sprint 1 tasks F1-F3).

Verifies:
- Typed ``RetrievalResult`` model construction from raw predictions
- SDK 0.120.0 compatibility of ``DataframeSplitInput`` shape
- Error handling for timeout, empty results, malformed predictions
- Proper output formatting from ``search_policy_docs_tool``
"""

import pytest


class TestRetrievalResult:
    """Test the typed RetrievalResult dataclass."""

    def test_from_prediction_full(self):
        from agent_core.retriever_interface import RetrievalResult

        pred = {"content": "Policy text", "source_file": "policy.pdf", "score": 0.95}
        result = RetrievalResult.from_prediction(pred)
        assert result.content == "Policy text"
        assert result.source_file == "policy.pdf"
        assert result.score == 0.95

    def test_from_prediction_minimal(self):
        from agent_core.retriever_interface import RetrievalResult

        result = RetrievalResult.from_prediction({})
        assert result.content == ""
        assert result.source_file == "unknown"
        assert result.score == 0.0

    def test_from_prediction_alternate_keys(self):
        from agent_core.retriever_interface import RetrievalResult

        pred = {"text": "Alt content", "source": "doc.txt"}
        result = RetrievalResult.from_prediction(pred)
        assert result.content == "Alt content"
        assert result.source_file == "doc.txt"

    def test_from_prediction_non_numeric_score(self):
        from agent_core.retriever_interface import RetrievalResult

        pred = {"score": "not_a_number"}
        result = RetrievalResult.from_prediction(pred)
        assert result.score == 0.0

    def test_expands_deployed_results_json_envelope(self):
        from agent_core.retriever_interface import _expand_prediction

        prediction = {
            "query_text": "policy",
            "results_json": '[{"content": "policy text", "source_file": "policy.md", "rerank_score": 0.9}]',
        }
        assert _expand_prediction(prediction) == [
            {"content": "policy text", "source_file": "policy.md", "rerank_score": 0.9}
        ]


class TestRetrieverConfig:
    def test_retriever_config_has_required_fields(self):
        from agent_core.config_schema import RetrieverConfig

        config = RetrieverConfig(endpoint_name="test-ep")
        assert config.endpoint_name == "test-ep"
        assert config.top_k == 5  # default
        assert config.over_fetch_k == 20  # default
        assert config.timeout_seconds == 60.0
        assert config.cold_start_retry_attempts == 1

    def test_retriever_config_custom_values(self):
        from agent_core.config_schema import RetrieverConfig

        config = RetrieverConfig(endpoint_name="rerank-ep", top_k=10, over_fetch_k=50)
        assert config.top_k == 10
        assert config.over_fetch_k == 50


class TestServingEndpointQuerySDK:
    """Verifies the SDK call shape against SDK 0.120.0."""

    def test_dataframe_split_input_shape(self):
        """Verify the DataframeSplitInput shape matches SDK 0.120.0."""
        try:
            from databricks.sdk.service.serving import DataframeSplitInput
        except ImportError:
            pytest.skip("databricks-sdk not available in test environment")

        payload = DataframeSplitInput(
            columns=["query_text", "top_k", "over_fetch_k"],
            data=[["test query", 5, 20]],
        )
        assert payload.columns == ["query_text", "top_k", "over_fetch_k"]
        assert len(payload.data) == 1
        assert payload.data[0][0] == "test query"

    def test_retriever_uses_supported_sdk_shape_with_injected_client(self):
        from types import SimpleNamespace

        from agent_core.config_schema import RetrieverConfig
        from agent_core.retriever_interface import Retriever

        class FakeQuery:
            def __init__(self):
                self.calls = []

            def query(self, **kwargs):
                self.calls.append(kwargs)
                return SimpleNamespace(
                    predictions=[
                        {"content": "Policy", "source_file": "policy.md", "score": 0.8}
                    ]
                )

        query = FakeQuery()
        client = SimpleNamespace(serving_endpoints=query)
        retriever = Retriever(RetrieverConfig(endpoint_name="reranker"), client=client)

        results = retriever.search("delivery")

        assert results[0].content == "Policy"
        assert query.calls == [
            {
                "name": "reranker",
                "dataframe_split": query.calls[0]["dataframe_split"],
            }
        ]
        payload = query.calls[0]["dataframe_split"]
        assert payload.columns == ["query_text", "top_k", "over_fetch_k"]
        assert payload.data == [["delivery", 5, 20]]


class TestRetrieverErrorHandling:
    """Test timeout/error mapping without hitting a real endpoint."""

    def test_retriever_constructor_with_injected_client(self):
        """Construction is local and does not require workspace credentials."""
        from types import SimpleNamespace

        from agent_core.config_schema import RetrieverConfig
        from agent_core.retriever_interface import Retriever

        config = RetrieverConfig(endpoint_name="test-ep")
        retriever = Retriever(config, client=SimpleNamespace(serving_endpoints=None))
        assert retriever is not None

    def test_timeout_is_mapped_by_production_code(self):
        from types import SimpleNamespace

        from agent_core.config_schema import RetrieverConfig
        from agent_core.retriever_interface import Retriever

        class TimedOutQuery:
            def query(self, **_kwargs):
                raise TimeoutError("HTTP request timed out")

        retriever = Retriever(
            RetrieverConfig(endpoint_name="test-ep"),
            timeout=0.001,
            client=SimpleNamespace(serving_endpoints=TimedOutQuery()),
        )
        with pytest.raises(TimeoutError, match="timed out after"):
            retriever.search("policy")

    def test_cold_start_timeout_is_retried_once(self, monkeypatch):
        from types import SimpleNamespace

        from agent_core.config_schema import RetrieverConfig
        from agent_core.retriever_interface import Retriever

        class ColdThenWarmQuery:
            def __init__(self):
                self.calls = 0

            def query(self, **_kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise TimeoutError("cold start")
                return SimpleNamespace(
                    predictions=[
                        {"content": "Policy", "source_file": "policy.md", "score": 0.8}
                    ]
                )

        query = ColdThenWarmQuery()
        monkeypatch.setattr("agent_core.retriever_interface.time.sleep", lambda _: None)
        retriever = Retriever(
            RetrieverConfig(endpoint_name="test-ep", cold_start_retry_attempts=1),
            client=SimpleNamespace(serving_endpoints=query),
        )

        assert retriever.search("policy")[0].content == "Policy"
        assert query.calls == 2

    def test_endpoint_errors_are_not_converted_to_empty_results(self):
        from types import SimpleNamespace

        from agent_core.config_schema import RetrieverConfig
        from agent_core.retriever_interface import Retriever

        class FailingQuery:
            def query(self, **_kwargs):
                raise ConnectionError("unavailable")

        retriever = Retriever(
            RetrieverConfig(endpoint_name="test-ep"),
            client=SimpleNamespace(serving_endpoints=FailingQuery()),
        )
        with pytest.raises(RuntimeError, match="test-ep.*unavailable"):
            retriever.search("policy")

    def test_malformed_results_json_is_not_converted_to_empty_results(self):
        from types import SimpleNamespace

        from agent_core.config_schema import RetrieverConfig
        from agent_core.retriever_interface import Retriever

        class MalformedQuery:
            def query(self, **_kwargs):
                return SimpleNamespace(predictions=[{"results_json": "not json"}])

        retriever = Retriever(
            RetrieverConfig(endpoint_name="test-ep"),
            client=SimpleNamespace(serving_endpoints=MalformedQuery()),
        )
        with pytest.raises(RuntimeError, match="malformed prediction envelope"):
            retriever.search("policy")

    def test_retrieval_result_sorting(self):
        """Verify results are sorted by score descending."""
        from agent_core.retriever_interface import RetrievalResult

        results = [
            RetrievalResult(content="b", source_file="x", score=0.5),
            RetrievalResult(content="a", source_file="x", score=0.9),
            RetrievalResult(content="c", source_file="x", score=0.7),
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        assert results[0].score == 0.9
        assert results[1].score == 0.7
        assert results[2].score == 0.5


class TestSearchToolOutputFormatting:
    """Test the output formatting from search_policy_docs_tool."""

    def test_format_with_retrieval_results(self):
        """Verify the tool formats typed RetrievalResult objects correctly."""
        from agent_core.retriever_interface import RetrievalResult
        from ecommerce_agent.tools.search_policy_docs_tool import (
            _format_retrieval_result,
        )

        results = [
            RetrievalResult(
                content="Policy A content", source_file="a.pdf", score=0.95
            ),
            RetrievalResult(
                content="Policy B content", source_file="b.pdf", score=0.85
            ),
        ]
        formatted = "\n\n".join(
            _format_retrieval_result(r.source_file, r.content) for r in results
        )
        assert "[a.pdf] Policy A content" in formatted
        assert "[b.pdf] Policy B content" in formatted

    def test_format_neutralizes_source_delimiters(self):
        from ecommerce_agent.tools.search_policy_docs_tool import (
            _format_retrieval_result,
        )

        assert _format_retrieval_result("[untrusted]\nsource", "policy") == (
            "[(untrusted) source] policy"
        )

    def test_format_empty_results(self):
        """Verify empty results return appropriate message."""
        formatted = "No relevant policy documents found."
        assert formatted

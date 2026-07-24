"""Tests for the Agent App retriever keep-warm worker."""

from ecommerce_agent.apps.agent_app.retriever_warmup import RetrieverWarmup


def test_warm_once_uses_a_bounded_governed_lookup() -> None:
    calls: list[tuple[str, int]] = []

    def search(query: str, *, top_k: int) -> list[object]:
        calls.append((query, top_k))
        return []

    warmup = RetrieverWarmup(search)

    assert warmup.warm_once() is True
    assert calls == [("order shipping return policy", 1)]


def test_warm_once_contains_endpoint_failures() -> None:
    def failing_search(query: str, *, top_k: int) -> list[object]:
        raise TimeoutError(f"{query}:{top_k}")

    warmup = RetrieverWarmup(failing_search)

    assert warmup.warm_once() is False

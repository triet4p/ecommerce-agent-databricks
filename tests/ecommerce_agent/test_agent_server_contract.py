"""Local contracts for the MLflow AgentServer invoke and SSE adapters."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from mlflow.types.responses import ResponsesAgentRequest

from ecommerce_agent.agent_app.handlers import invoke_agent, stream_agent


def _request() -> dict:
    return {
        "input": [{"role": "user", "content": "Where is my order?"}],
        "metadata": {"trace_id": "trace-123"},
        "custom_inputs": {"tenant": "test", "request_mode": "contract"},
    }


class _FakeAgent:
    def __init__(self) -> None:
        self.requests = []

    def predict(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            model_dump=lambda: {
                "object": "response",
                "output": [],
                "custom_outputs": request.custom_inputs,
            }
        )

    def predict_stream(self, request):
        self.requests.append(request)
        yield SimpleNamespace(
            model_dump=lambda: {
                "type": "response.output_text.delta",
                "delta": "Order is in transit.",
                "custom_outputs": request.custom_inputs,
            }
        )
        yield SimpleNamespace(
            model_dump=lambda: {
                "type": "response.completed",
                "custom_outputs": request.custom_inputs,
            }
        )


def test_invoke_validates_request_and_preserves_trace_and_custom_inputs():
    agent = _FakeAgent()

    response = invoke_agent(agent, _request())

    assert response["object"] == "response"
    assert response["custom_outputs"] == {"tenant": "test", "request_mode": "contract"}
    assert agent.requests[0].metadata == {"trace_id": "trace-123"}
    assert agent.requests[0].custom_inputs == {
        "tenant": "test",
        "request_mode": "contract",
    }


def test_stream_serializes_ordered_sse_events_and_propagates_custom_inputs():
    agent = _FakeAgent()

    events = list(stream_agent(agent, _request()))

    assert [event["type"] for event in events] == [
        "response.output_text.delta",
        "response.completed",
    ]
    assert events[0]["delta"] == "Order is in transit."
    assert all(event["custom_outputs"]["tenant"] == "test" for event in events)


def test_stream_accepts_request_already_validated_by_agent_server():
    agent = _FakeAgent()

    events = list(stream_agent(agent, ResponsesAgentRequest(**_request())))

    assert len(events) == 2
    assert agent.requests[0].custom_inputs["tenant"] == "test"


def test_invoke_propagates_agent_errors_without_converting_them_to_success():
    class FailingAgent:
        def predict(self, _request):
            raise RuntimeError("configured endpoint unavailable")

    with pytest.raises(RuntimeError, match="configured endpoint unavailable"):
        invoke_agent(FailingAgent(), _request())


def test_stream_propagates_agent_errors_without_emitting_a_completion():
    class FailingAgent:
        def predict_stream(self, _request):
            raise RuntimeError("stream failed")
            yield  # pragma: no cover

    with pytest.raises(RuntimeError, match="stream failed"):
        list(stream_agent(FailingAgent(), _request()))


def test_invalid_agent_server_request_is_rejected_before_agent_execution():
    agent = _FakeAgent()

    with pytest.raises(Exception):
        invoke_agent(agent, {"input": "not an input-item list"})

    assert agent.requests == []

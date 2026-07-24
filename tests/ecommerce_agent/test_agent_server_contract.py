"""Local contracts for the MLflow AgentServer invoke and SSE adapters."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from mlflow.types.responses import ResponsesAgentRequest

from ecommerce_agent.apps.agent_app.handlers import invoke_agent, stream_agent


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


# ---------------------------------------------------------------------------
# Sprint 2 — D4: Multiple text deltas
# ---------------------------------------------------------------------------


def test_stream_produces_multiple_real_text_deltas_for_deterministic_response():
    """More than one real text delta is emitted for a multi-chunk response."""

    class MultiDeltaAgent:
        def __init__(self) -> None:
            self.requests = []

        def predict_stream(self, request):
            self.requests.append(request)
            for chunk in ["Your ", "order ", "is ", "being ", "processed."]:
                yield SimpleNamespace(
                    model_dump=lambda c=chunk: {
                        "type": "response.output_text.delta",
                        "item_id": "msg_d4_1",
                        "delta": c,
                        "content_index": 0,
                        "output_index": 0,
                    }
                )
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "message",
                        "id": "msg_d4_1",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "Your order is being processed.",
                            }
                        ],
                    },
                }
            )
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.completed",
                    "response": {"status": "completed"},
                }
            )

    agent = MultiDeltaAgent()
    events = list(stream_agent(agent, _request()))

    delta_events = [e for e in events if e["type"] == "response.output_text.delta"]
    done_events = [e for e in events if e["type"] == "response.output_item.done"]

    assert len(delta_events) >= 2, (
        f"Expected at least 2 text deltas, got {len(delta_events)}"
    )
    # Verify the deltas aggregate to the full text
    full_text = "".join(e["delta"] for e in delta_events)
    assert full_text == "Your order is being processed."

    # Done event must carry the aggregated text
    assert len(done_events) == 1
    assert done_events[0]["item"]["content"][0]["text"] == full_text


def test_delta_and_done_share_item_id():
    """Text deltas and the final done event share the same item_id."""

    class CorrelatedDeltaAgent:
        def predict_stream(self, request):
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_text.delta",
                    "item_id": "msg_corr_1",
                    "delta": "Hello ",
                }
            )
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_text.delta",
                    "item_id": "msg_corr_1",
                    "delta": "world",
                }
            )
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "message",
                        "id": "msg_corr_1",
                        "content": [{"type": "output_text", "text": "Hello world"}],
                    },
                }
            )

    events = list(stream_agent(CorrelatedDeltaAgent(), _request()))
    done_events = [e for e in events if e["type"] == "response.output_item.done"]
    assert done_events[0]["item"]["id"] == "msg_corr_1"


# ---------------------------------------------------------------------------
# Sprint 2 — D5: Tool-loop event ordering and correlation
# ---------------------------------------------------------------------------


def test_tool_loop_events_are_ordered_call_before_result():
    """For a tool-assisted turn, function_call must precede
    function_call_output with the same call_id."""

    class ToolLoopAgent:
        def predict_stream(self, request):
            # Text delta before tool
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_text.delta",
                    "item_id": "msg_d5",
                    "delta": "Let me check...",
                }
            )
            # Tool call
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "function_call",
                        "id": "fc_d5_1",
                        "call_id": "call_d5",
                        "name": "get_order_status",
                        "arguments": '{"order_id": "o-1"}',
                    },
                }
            )
            # Tool result
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "function_call_output",
                        "call_id": "call_d5",
                        "output": '{"status": "shipped"}',
                    },
                }
            )
            # Final assistant text
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "message",
                        "id": "msg_d5",
                        "content": [
                            {"type": "output_text", "text": "Your order is shipped!"}
                        ],
                    },
                }
            )

    # Route through stream_agent() like the handler does.
    events = list(stream_agent(ToolLoopAgent(), _request()))
    done_items = [e for e in events if e["type"] == "response.output_item.done"]

    # Check ordering: call before result
    call_indices = [
        i for i, e in enumerate(done_items) if e["item"].get("type") == "function_call"
    ]
    result_indices = [
        i
        for i, e in enumerate(done_items)
        if e["item"].get("type") == "function_call_output"
    ]

    assert len(call_indices) == 1
    assert len(result_indices) == 1
    assert call_indices[0] < result_indices[0], (
        "function_call must precede function_call_output"
    )

    # Check correlation: same call_id
    call = done_items[call_indices[0]]["item"]
    result = done_items[result_indices[0]]["item"]
    assert call["call_id"] == result["call_id"] == "call_d5"


def test_multiple_tool_calls_maintain_individual_correlation():
    """Each tool call/result pair is independently correlated by call_id."""

    class MultiToolAgent:
        def predict_stream(self, request):
            # Tool 1 call
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "function_call",
                        "id": "fc_1",
                        "call_id": "call_1",
                        "name": "get_order",
                        "arguments": "{}",
                    },
                }
            )
            # Tool 2 call
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "function_call",
                        "id": "fc_2",
                        "call_id": "call_2",
                        "name": "get_shipping",
                        "arguments": "{}",
                    },
                }
            )
            # Tool 1 result
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "function_call_output",
                        "call_id": "call_1",
                        "output": "order found",
                    },
                }
            )
            # Tool 2 result
            yield SimpleNamespace(
                model_dump=lambda: {
                    "type": "response.output_item.done",
                    "item": {
                        "type": "function_call_output",
                        "call_id": "call_2",
                        "output": "shipped",
                    },
                }
            )

    events = list(stream_agent(MultiToolAgent(), _request()))
    done_items = [e for e in events if e["type"] == "response.output_item.done"]

    # Group by call_id
    calls = {}
    for i, e in enumerate(done_items):
        item = e["item"]
        if item.get("type") == "function_call":
            calls[item["call_id"]] = {"call_idx": i}
        elif item.get("type") == "function_call_output":
            cid = item["call_id"]
            if cid in calls:
                calls[cid]["result_idx"] = i

    for cid, indices in calls.items():
        assert "call_idx" in indices, f"Missing call for call_id {cid}"
        assert "result_idx" in indices, f"Missing result for call_id {cid}"
        assert indices["call_idx"] < indices["result_idx"], (
            f"Result before call for call_id {cid}"
        )

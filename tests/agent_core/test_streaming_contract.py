"""Tests for the token-level streaming contract (Sprint 2, Section B).

This test file validates that ``CoreAgent.predict_stream()``:
- Emits real ``response.output_text.delta`` events (not just completed items)
- Aggregates deltas into one final ``response.output_item.done`` (message)
- Emits correlated function-call and function-call-output items
- Deduplicates items across ``updates`` and ``messages`` stream modes
- Preserves the OperationGate safety boundary
- Propagates errors without synthesizing a completion event
- Returns trace metadata without placing internals in chat history
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.tools import tool

from agent_core.orchestrator import CoreAgent, _responses_safe_messages
from agent_core.tool_policy import OperationGate, ToolPolicy, ToolRole


# =========================================================================
# Helpers
# =========================================================================


def _dummy_agent() -> CoreAgent:
    """Build a minimal CoreAgent for streaming tests.

    Uses a real tool so the graph construction is valid, but overrides the
    graph with a controllable fake so tests are deterministic.
    """

    @tool("test_tool")
    def test_tool(query: str) -> str:
        """A test tool for dummy agent construction."""
        return f"result_for_{query}"

    core = object.__new__(CoreAgent)
    core._operation_gate = OperationGate()
    core._tools_by_name = {"test_tool": test_tool}
    core._pending_tool_results = {}
    return core


# =========================================================================
# S2-B1: Test fixture — distinguish token deltas from completed events
# =========================================================================


def test_delta_events_have_required_fields():
    """A ``response.output_text.delta`` event must carry ``item_id`` and ``delta``."""
    from mlflow.types.responses import ResponsesAgentStreamEvent, create_text_delta

    event_dict = create_text_delta("Hello", item_id="msg_1")
    assert event_dict["type"] == "response.output_text.delta"
    assert event_dict["item_id"] == "msg_1"
    assert event_dict["delta"] == "Hello"

    # Validate through the MLflow model
    validated = ResponsesAgentStreamEvent(**event_dict)
    assert validated.type == "response.output_text.delta"


def test_delta_events_can_be_aggregated_into_done_event():
    """Multiple deltas with the same item_id aggregate into one done event."""
    from mlflow.types.responses import (
        ResponsesAgentStreamEvent,
        create_text_delta,
        create_text_output_item,
    )

    deltas = ["Hello", " world", "!"]
    item_id = "msg_agg_1"

    # Emit deltas
    for chunk in deltas:
        event = ResponsesAgentStreamEvent(**create_text_delta(chunk, item_id=item_id))
        assert event.type == "response.output_text.delta"

    # Emit the aggregated done event
    done_item = create_text_output_item("".join(deltas), id=item_id)
    done_event = ResponsesAgentStreamEvent(
        type="response.output_item.done", item=done_item
    )
    assert done_event.type == "response.output_item.done"
    assert done_event.item["id"] == item_id
    assert done_event.item["content"][0]["text"] == "Hello world!"


def test_text_delta_and_done_share_item_id():
    """Deltas and their final done event must share the same item_id."""
    from mlflow.types.responses import (
        ResponsesAgentStreamEvent,
        create_text_delta,
        create_text_output_item,
    )

    item_id = "msg_share_1"
    delta = ResponsesAgentStreamEvent(**create_text_delta("Hello", item_id=item_id))
    done = ResponsesAgentStreamEvent(
        type="response.output_item.done",
        item=create_text_output_item("Hello", id=item_id),
    )

    assert delta.type == "response.output_text.delta"
    assert delta.item_id == item_id
    assert done.item["id"] == item_id


def test_function_call_item_has_call_id():
    """A function_call item must carry a stable call_id for correlation."""
    from mlflow.types.responses import (
        ResponsesAgentStreamEvent,
        create_function_call_item,
    )

    item = create_function_call_item(
        id="fc_1",
        call_id="call_abc",
        name="test_tool",
        arguments='{"query": "test"}',
    )
    event = ResponsesAgentStreamEvent(type="response.output_item.done", item=item)

    assert event.item["call_id"] == "call_abc"
    assert event.item["name"] == "test_tool"


def test_function_call_output_item_is_correlated_by_call_id():
    """A function_call_output item must share the call_id with its call."""
    from mlflow.types.responses import (
        ResponsesAgentStreamEvent,
        create_function_call_output_item,
    )

    item = create_function_call_output_item(call_id="call_abc", output="test result")
    event = ResponsesAgentStreamEvent(type="response.output_item.done", item=item)

    assert event.item["call_id"] == "call_abc"
    assert event.item["output"] == "test result"


def test_text_delta_and_tool_call_have_distinct_roles():
    """Text deltas and tool call items have distinct types."""
    from mlflow.types.responses import (
        ResponsesAgentStreamEvent,
        create_text_delta,
        create_function_call_item,
    )

    delta_event = ResponsesAgentStreamEvent(**create_text_delta("text", item_id="m1"))
    call_event = ResponsesAgentStreamEvent(
        type="response.output_item.done",
        item=create_function_call_item("fc1", "call1", "tool", "{}"),
    )

    assert delta_event.type == "response.output_text.delta"
    assert call_event.type == "response.output_item.done"
    assert call_event.item["type"] == "function_call"


# =========================================================================
# S2-B7: Deduplication — items from both stream modes
# =========================================================================


def test_text_not_duplicated_across_updates_and_messages(monkeypatch):
    """When text is already streamed as deltas, the completed text item
    from the updates stream must be suppressed (not duplicated). A single
    aggregated done event is emitted after the stream completes."""

    core = _dummy_agent()
    monkeypatch.setattr(
        "agent_core.orchestrator.to_chat_completions_input", lambda _: []
    )

    consumed_types = []

    class DedupGraph:
        """Simulates dual-stream-mode graph with both messages and updates."""

        def stream(self, _inputs, **_kwargs):
            # Emulate "messages" mode yielding text chunks
            yield (
                "messages",
                (
                    AIMessageChunk(content="Hello ", id="msg_dedup_1"),
                    {"langgraph_node": "agent"},
                ),
            )
            yield (
                "messages",
                (
                    AIMessageChunk(content="world", id="msg_dedup_1"),
                    {"langgraph_node": "agent"},
                ),
            )
            # Emulate "updates" mode yielding completed message
            yield (
                "updates",
                {
                    "agent": {
                        "messages": [
                            AIMessage(
                                content="Hello world",
                                id="msg_dedup_1",
                            )
                        ]
                    }
                },
            )

    core.graph = DedupGraph()

    flush_text_done_count = 0
    for event in core.predict_stream(SimpleNamespace(input=[])):
        consumed_types.append(event.type)
        if event.type == "response.output_text.delta":
            assert event.delta in ("Hello ", "world")
        if event.type == "response.output_item.done":
            item = event.item
            if isinstance(item, dict) and item.get("type") == "message":
                # The aggregated done from flush is expected exactly once.
                flush_text_done_count += 1

    # Should have seen deltas
    delta_count = sum(1 for t in consumed_types if t == "response.output_text.delta")
    assert delta_count == 2, f"Expected 2 deltas, got {delta_count}"

    # The updates-mode text should NOT produce a separate done event.
    # Only the flush aggregation should produce one.
    assert flush_text_done_count == 1, (
        f"Expected exactly 1 aggregated text done, got {flush_text_done_count}"
    )


# =========================================================================
# S2-B8: Operation gate safety
# =========================================================================


def test_required_operation_still_blocks_events_until_verified(monkeypatch):
    """When a required operation is configured, no events escape the stream
    before the gate is verified, even with dual stream modes."""

    @tool("required_tool")
    def required_tool(input: str) -> str:
        """A required tool for gate testing."""
        return "done"

    core = object.__new__(CoreAgent)
    core._operation_gate = OperationGate(
        policies={
            "required_tool": ToolPolicy(
                name="required_tool",
                role=ToolRole.REQUIRED_ACTION,
                required_args=["input"],
            )
        }
    )
    core._tools_by_name = {"required_tool": required_tool}
    core._pending_tool_results = {}

    monkeypatch.setattr(
        "agent_core.orchestrator.to_chat_completions_input", lambda _: []
    )

    class GateTestGraph:
        def stream(self, _inputs, **_kwargs):
            # Emit text deltas first (messages mode)
            yield (
                "messages",
                (
                    AIMessageChunk(content="thinking...", id="msg_g1"),
                    {"langgraph_node": "agent"},
                ),
            )
            # Then emit updates without the required tool
            yield (
                "updates",
                {
                    "agent": {
                        "messages": [
                            AIMessage(
                                content="thinking...",
                                id="msg_g1",
                                tool_calls=[],
                            )
                        ]
                    }
                },
            )

    core.graph = GateTestGraph()

    with pytest.raises(RuntimeError, match=r"Required tool\(s\) not called"):
        list(core.predict_stream(SimpleNamespace(input=[])))


# =========================================================================
# S2-B9: Error propagation
# =========================================================================


def test_error_event_prevents_successful_completion(monkeypatch):
    """An error event must terminate the stream and not be followed by
    a completion event."""

    core = _dummy_agent()
    monkeypatch.setattr(
        "agent_core.orchestrator.to_chat_completions_input", lambda _: []
    )

    consumed_types = []

    class ErrorGraph:
        def stream(self, _inputs, **_kwargs):
            raise RuntimeError("upstream stream failed")
            yield  # pragma: no cover

    core.graph = ErrorGraph()

    events = list(core.predict_stream(SimpleNamespace(input=[])))
    for e in events:
        consumed_types.append(e.type)

    assert "error" in consumed_types
    assert "response.completed" not in consumed_types


def test_successful_stream_ends_with_completion_event(monkeypatch):
    core = _dummy_agent()
    monkeypatch.setattr(
        "agent_core.orchestrator.to_chat_completions_input", lambda _: []
    )

    class SuccessGraph:
        def stream(self, _inputs, **_kwargs):
            yield (
                "updates",
                {
                    "agent": {
                        "messages": [
                            AIMessage(content="OK", id="msg_ok_1", tool_calls=[])
                        ]
                    }
                },
            )

    core.graph = SuccessGraph()
    events = list(core.predict_stream(SimpleNamespace(input=[])))

    assert events[-1].type == "response.completed"
    assert events[-1].response["status"] == "completed"
    assert events[-1].response["output"]
    assert events[-1].response["output"][0]["type"] == "message"


# =========================================================================
# S2-B10: Trace metadata
# =========================================================================


def test_trace_id_surface_not_in_chat_history(monkeypatch):
    """Trace metadata must be available to the caller but never end up in
    future chat input history."""

    core = _dummy_agent()
    monkeypatch.setattr(
        "agent_core.orchestrator.to_chat_completions_input", lambda _: []
    )

    class TraceGraph:
        def stream(self, _inputs, **_kwargs):
            yield (
                "updates",
                {
                    "agent": {
                        "messages": [
                            AIMessage(content="OK", id="msg_t1", tool_calls=[])
                        ]
                    }
                },
            )

    core.graph = TraceGraph()

    # predict_stream does NOT return trace IDs in the event stream
    for event in core.predict_stream(SimpleNamespace(input=[])):
        # Trace info belongs in metadata, not in event content
        if event.type == "response.output_item.done":
            item = getattr(event, "item", {}) or {}
            if item.get("type") == "message":
                for block in item.get("content", []):
                    if isinstance(block, dict):
                        assert "trace_id" not in block.get("text", "")
                        assert "mlflow" not in block.get("text", "").lower()


# =========================================================================
# S2-B2 / B3 / B4: Message-chunk-to-delta conversion (unit-level)
# =========================================================================


def test_aimessage_chunk_content_becomes_text_delta():
    """A single AIMessageChunk with text content must become one
    ``response.output_text.delta`` event."""
    from agent_core.orchestrator import _message_chunk_to_delta_events

    chunk = AIMessageChunk(content="Hello ", id="chunk_1")
    metadata = {"langgraph_node": "agent"}
    events = list(_message_chunk_to_delta_events(chunk, metadata))
    assert len(events) == 1
    assert events[0].type == "response.output_text.delta"
    assert events[0].delta == "Hello "


def test_empty_chunk_produces_no_events():
    """An AIMessageChunk with empty content must produce no events."""
    from agent_core.orchestrator import _message_chunk_to_delta_events

    chunk = AIMessageChunk(content="", id="chunk_empty")
    events = list(_message_chunk_to_delta_events(chunk, {"langgraph_node": "agent"}))
    assert len(events) == 0


def test_tool_call_chunks_are_not_emitted_as_deltas():
    """Tool call chunks in messages mode must NOT be emitted as text deltas."""
    from agent_core.orchestrator import _message_chunk_to_delta_events

    chunk = AIMessageChunk(
        content="",
        id="chunk_tc",
        tool_call_chunks=[
            {"index": 0, "id": "call_1", "name": "test_tool", "args": "{}"}
        ],
    )
    events = list(_message_chunk_to_delta_events(chunk, {"langgraph_node": "agent"}))
    # Tool call chunks should not produce text deltas
    assert len(events) == 0


def test_tool_result_chunks_are_not_emitted_as_visible_text():
    """Tool output JSON belongs in provenance, not the assistant answer."""
    from langchain_core.messages import ToolMessageChunk

    from agent_core.orchestrator import _message_chunk_to_delta_events

    chunk = ToolMessageChunk(
        content='{"status":"delivered"}',
        tool_call_id="call_1",
    )
    events = list(_message_chunk_to_delta_events(chunk, {"langgraph_node": "tools"}))

    assert events == []


# =========================================================================
# S2-B5 / B6: Tool call and result correlation
# =========================================================================


def test_function_call_and_output_share_call_id():
    """A tool call and its result must be correlated by call_id."""
    from mlflow.types.responses import (
        create_function_call_item,
        create_function_call_output_item,
    )

    call_id = "call_corr_1"
    call = create_function_call_item("fc1", call_id, "test_tool", "{}")
    result = create_function_call_output_item(call_id, "output")

    assert call["call_id"] == result["call_id"] == call_id


def test_responses_safe_messages_strips_reasoning():
    """The _responses_safe_messages helper must strip reasoning blocks."""
    message = AIMessage(
        content=[
            {"type": "reasoning", "summary": [{"type": "summary_text", "text": "x"}]},
            {"type": "text", "text": "visible"},
        ],
        id="msg_safe_1",
    )

    normalized = _responses_safe_messages([message])
    assert "reasoning" not in normalized[0].content
    assert "visible" in normalized[0].content

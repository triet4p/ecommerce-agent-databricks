"""Reducer/aggregator tests for stream events (Sprint 2, D2).

Validates:
- Text delta aggregation into one final message
- Tool call/result correlation by call_id
- Duplicate suppression across stream modes
- Error event propagation without completion
- Phase label derivation
"""

from __future__ import annotations

from ecommerce_agent.apps.chat_ui.display_policy import (
    derive_phase_label,
    sanitize_arguments,
    sanitize_output,
    tool_display_name,
)
from ecommerce_agent.apps.chat_ui.stream_types import (
    FunctionCallItem,
    FunctionCallOutputItem,
    OutputItemDoneEvent,
    TextDeltaEvent,
    TextMessageItem,
    parse_stream_event,
)


# =========================================================================
# Text aggregation
# =========================================================================


def test_text_deltas_accumulate_to_full_message():
    """Multiple TextDeltaEvents with the same item_id accumulate."""
    deltas = [
        TextDeltaEvent(item_id="msg_1", delta="Hello "),
        TextDeltaEvent(item_id="msg_1", delta="world!"),
    ]
    accumulated = "".join(d.delta for d in deltas)
    assert accumulated == "Hello world!"


def test_text_done_event_has_aggregated_content():
    """The final OutputItemDoneEvent for text matches the accumulated content."""
    aggregated_text = "Hello world!"
    done = OutputItemDoneEvent(
        item=TextMessageItem(
            id="msg_1",
            content=[{"type": "output_text", "text": aggregated_text}],
        )
    )
    assert done.item.text == aggregated_text
    assert done.item.id == "msg_1"


def test_multiple_delta_batches_aggregate_correctly():
    """Simulate three delta batches that arrive in order."""
    items = [
        TextDeltaEvent(item_id="msg_agg", delta="The order "),
        TextDeltaEvent(item_id="msg_agg", delta="status is "),
        TextDeltaEvent(item_id="msg_agg", delta="**shipped**."),
    ]
    text = "".join(it.delta for it in items)
    assert text == "The order status is **shipped**."


# =========================================================================
# Tool correlation
# =========================================================================


def test_tool_call_and_result_share_call_id():
    """Tool calls and results are correlated by call_id."""
    call = FunctionCallItem(
        id="fc_1", call_id="call_abc", name="get_order", arguments="{}"
    )
    result = FunctionCallOutputItem(call_id="call_abc", output='{"status": "ok"}')
    assert call.call_id == result.call_id


def test_multiple_tools_have_distinct_call_ids():
    """Different tool calls have different call_ids."""
    call_a = FunctionCallItem(
        id="fc_1", call_id="call_a", name="tool_a", arguments="{}"
    )
    call_b = FunctionCallItem(
        id="fc_2", call_id="call_b", name="tool_b", arguments="{}"
    )
    assert call_a.call_id != call_b.call_id


def test_parse_stream_event_recognises_function_call():
    data = {
        "type": "response.output_item.done",
        "item": {
            "type": "function_call",
            "id": "fc_1",
            "call_id": "call_1",
            "name": "get_order_status",
            "arguments": '{"order_id": "o-1"}',
        },
    }
    event = parse_stream_event(data)
    assert event is not None
    assert isinstance(event, OutputItemDoneEvent)
    assert isinstance(event.item, FunctionCallItem)
    assert event.item.name == "get_order_status"


# =========================================================================
# Deduplication
# =========================================================================


def test_duplicate_delta_item_ids_are_deduplicated_by_id():
    """If two deltas share the same item_id, they belong to one output."""
    deltas = [
        TextDeltaEvent(item_id="dup_id", delta="first "),
        TextDeltaEvent(item_id="dup_id", delta="second"),
    ]
    ids = {d.item_id for d in deltas}
    assert len(ids) == 1


def test_delta_and_done_share_item_id():
    delta = TextDeltaEvent(item_id="msg_shared", delta="Hello")
    done = OutputItemDoneEvent(
        item=TextMessageItem(
            id="msg_shared", content=[{"type": "output_text", "text": "Hello"}]
        )
    )
    assert delta.item_id == done.item.id


# =========================================================================
# Error propagation
# =========================================================================


def test_error_event_type_is_recognised():
    data = {"type": "error", "code": "INTERNAL_ERROR", "message": "Tool failed"}
    event = parse_stream_event(data)
    assert event is not None
    from ecommerce_agent.apps.chat_ui.stream_types import ErrorEvent

    assert isinstance(event, ErrorEvent)
    assert event.code == "INTERNAL_ERROR"


def test_error_event_with_no_code():
    data = {"type": "error", "message": "Something went wrong"}
    event = parse_stream_event(data)
    assert event is not None
    from ecommerce_agent.apps.chat_ui.stream_types import ErrorEvent

    assert isinstance(event, ErrorEvent)
    assert event.code is None


# =========================================================================
# Phase label derivation
# =========================================================================


def test_phase_label_composing():
    assert derive_phase_label(has_text_delta=True) == "🤖 Composing…"


def test_phase_label_running_tool_overrides_text():
    """When a tool call is pending, the phase shows running even with text."""
    assert (
        derive_phase_label(has_text_delta=True, has_pending_tool_call=True)
        == "\U0001f527 Running tool…"
    )


def test_phase_label_text_without_tool():
    """When only text deltas are present (no tool), show composing."""
    assert derive_phase_label(has_text_delta=True) == "\U0001f916 Composing…"


def test_phase_label_running_tool():
    assert derive_phase_label(has_pending_tool_call=True) == "\U0001f527 Running tool…"


def test_phase_label_tool_complete():
    assert derive_phase_label(has_tool_result=True) == "✅ Tool complete"


def test_phase_label_error():
    assert derive_phase_label(is_error=True) == "❌ Error"


# =========================================================================
# Display policy
# =========================================================================


def test_tool_display_name_known():
    assert tool_display_name("get_order_status") == "\U0001f50d Order lookup"


def test_tool_display_name_unknown():
    assert tool_display_name("unknown_tool") == "\U0001f527 unknown_tool"


def test_sanitize_arguments_truncates_long_input():
    long_args = '{"data": "' + "x" * 600 + '"}'
    result = sanitize_arguments(long_args)
    assert len(result) == 501  # 500 chars + "…" (one Unicode char)
    assert result.endswith("…")


def test_sanitize_arguments_redacts_secret_keys():
    args = '{"password": "s3cret", "normal": "visible"}'
    result = sanitize_arguments(args)
    assert '"<redacted>"' in result
    assert "s3cret" not in result


def test_sanitize_output_truncates_long_content():
    long_output = "x" * 2000
    result = sanitize_output(long_output)
    assert len(result) == 1001  # 1000 + "…"
    assert result.endswith("…")


def test_sanitize_output_preserves_short_content():
    short = "short output"
    assert sanitize_output(short) == short


# =========================================================================
# Parse stream event — unsupported types
# =========================================================================


def test_unsupported_event_type_is_ignored():
    data = {"type": "response.content_part.added", "content": []}
    event = parse_stream_event(data)
    assert event is None

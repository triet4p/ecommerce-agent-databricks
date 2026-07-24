"""Tests for history replay pipeline (S3-D1 through S3-D6)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ecommerce_agent.conversation.models import ConversationItem, ItemPayload
from ecommerce_agent.conversation.replay import (
    accumulate_output_items,
    append_user_message,
    build_replay_request,
    check_request_budget,
    compute_request_size,
    convert_items_to_input_history,
)

_NOW = datetime.now(timezone.utc)
_CONV_ID = uuid.uuid4()
_TURN_ID = uuid.uuid4()


def _make_item(
    item_type: str,
    payload_dict: dict,
    sequence: int = 1,
    role: str | None = None,
) -> ConversationItem:
    return ConversationItem(
        id=uuid.uuid4(),
        conversation_id=_CONV_ID,
        turn_id=_TURN_ID,
        sequence=sequence,
        item_type=item_type,  # type: ignore
        role=role,
        payload=ItemPayload(**payload_dict),
        created_at=_NOW,
    )


class TestConvertItemsToInputHistory:
    """S3-D1: Convert persisted items to Responses API input."""

    def test_convert_user_message(self):
        item = _make_item(
            "message",
            {
                "type": "message",
                "id": "msg_1",
                "role": "user",
                "content": [{"type": "input_text", "text": "Hello"}],
            },
            role="user",
        )
        result = convert_items_to_input_history([item])
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"][0]["type"] == "input_text"
        assert result[0]["content"][0]["text"] == "Hello"

    def test_convert_assistant_message(self):
        item = _make_item(
            "message",
            {
                "type": "message",
                "id": "msg_2",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "I can help!"}],
            },
            role="assistant",
        )
        result = convert_items_to_input_history([item])
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["content"][0]["type"] == "input_text"
        assert result[0]["content"][0]["text"] == "I can help!"

    def test_convert_function_call(self):
        """function_call items are filtered out during replay."""
        item = _make_item(
            "function_call",
            {
                "type": "function_call",
                "id": "fc_1",
                "call_id": "call_abc",
                "name": "get_order_status",
                "arguments": '{"order_id": "123"}',
            },
        )
        result = convert_items_to_input_history([item])
        assert len(result) == 0  # filtered out

    def test_convert_function_call_output(self):
        """function_call_output items are filtered out during replay
        (the ResponsesAgent rejects replayed tool results)."""
        item = _make_item(
            "function_call_output",
            {
                "type": "function_call_output",
                "call_id": "call_abc",
                "output": '{"status": "shipped"}',
            },
        )
        result = convert_items_to_input_history([item])
        assert len(result) == 0  # filtered out

    def test_skip_malformed_items(self):
        """Items with no extractable content are skipped."""
        item = _make_item(
            "message",
            {"type": "message", "id": "empty", "content": []},
        )
        result = convert_items_to_input_history([item])
        assert len(result) == 0

    def test_full_sequence(self):
        """A realistic sequence of items converts correctly."""
        items = [
            _make_item(
                "message",
                {
                    "type": "message",
                    "id": "u1",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Where is my order?"}],
                },
                sequence=1,
                role="user",
            ),
            _make_item(
                "function_call",
                {
                    "type": "function_call",
                    "id": "fc1",
                    "call_id": "c1",
                    "name": "get_order_status",
                    "arguments": '{"order_id": "42"}',
                },
                sequence=2,
            ),
            _make_item(
                "function_call_output",
                {
                    "type": "function_call_output",
                    "call_id": "c1",
                    "output": '{"status": "delivered"}',
                },
                sequence=3,
            ),
            _make_item(
                "message",
                {
                    "type": "message",
                    "id": "tool-echo",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": '{"status": "delivered"}'}
                    ],
                },
                sequence=4,
                role="assistant",
            ),
            _make_item(
                "message",
                {
                    "type": "message",
                    "id": "a1",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "Your order was delivered."}
                    ],
                },
                sequence=5,
                role="assistant",
            ),
        ]
        result = convert_items_to_input_history(items)
        # function_call and function_call_output are filtered out during replay
        assert len(result) == 2  # user + assistant only
        assert result[0]["role"] == "user"
        assert result[0]["content"] is not None
        assert result[1]["role"] == "assistant"


class TestAppendUserMessage:
    """S3-D2: Append new user item after prior history."""

    def test_append_to_empty(self):
        history = []
        result = append_user_message(history, "Hello")
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_append_after_history(self):
        history = [
            {"role": "assistant", "content": [{"type": "input_text", "text": "Hi"}]}
        ]
        result = append_user_message(history, "How are you?")
        assert len(result) == 2
        assert result[1]["role"] == "user"


class TestRequestBudget:
    """S3-D3 and S3-D4: Size computation and budget checking."""

    def test_compute_request_size(self):
        items = [{"role": "user", "content": [{"type": "input_text", "text": "Hello"}]}]
        size = compute_request_size(items)
        assert isinstance(size, int)
        assert size > 0

    def test_within_budget(self):
        items = [{"role": "user", "content": [{"type": "input_text", "text": "Hi"}]}]
        ok, size = check_request_budget(items)
        assert ok is True
        assert size > 0

    def test_over_budget(self):
        huge_text = "x" * 200_000
        items = [
            {"role": "user", "content": [{"type": "input_text", "text": huge_text}]}
        ]
        ok, size = check_request_budget(items, max_chars=100_000)
        assert ok is False
        assert size > 100_000


class TestAccumulateOutputItems:
    """S3-D5: Accumulate stream events and commit only on terminal success."""

    def test_accumulates_output_items(self):
        events = [
            {
                "type": "response.output_item.done",
                "item": {
                    "type": "message",
                    "id": "m1",
                    "content": [{"type": "output_text", "text": "Hello"}],
                },
                "output_index": 0,
            },
            {
                "type": "response.output_item.done",
                "item": {
                    "type": "function_call",
                    "id": "fc1",
                    "call_id": "c1",
                    "name": "get_status",
                    "arguments": "{}",
                },
                "output_index": 1,
            },
            {"type": "response.completed", "response": {}},
        ]
        items = accumulate_output_items(events)
        assert len(items) == 2
        assert items[0]["type"] == "message"
        assert items[1]["type"] == "function_call"

    def test_empty_on_error(self):
        events = [
            {
                "type": "response.output_item.done",
                "item": {"type": "message", "id": "m1"},
            },
            {"type": "error", "code": "ERROR", "message": "Something broke"},
        ]
        items = accumulate_output_items(events)
        assert items == []

    def test_empty_on_empty(self):
        items = accumulate_output_items([])
        assert items == []

    def test_empty_without_terminal_completion(self):
        items = accumulate_output_items(
            [
                {
                    "type": "response.output_item.done",
                    "item": {"type": "message", "id": "m1"},
                },
                {"type": "done"},
            ]
        )
        assert items == []

    def test_stops_at_completed(self):
        """Should stop collecting items after response.completed."""
        events = [
            {
                "type": "response.output_item.done",
                "item": {"type": "message", "id": "m1"},
            },
            {"type": "response.completed", "response": {}},
            {
                "type": "response.output_item.done",
                "item": {"type": "message", "id": "m2"},
            },
        ]
        items = accumulate_output_items(events)
        assert len(items) == 1


class TestBuildReplayRequest:
    """Full replay pipeline integration (D1-D4 combined)."""

    def test_build_replay_request(self):
        items = [
            _make_item(
                "message",
                {
                    "type": "message",
                    "id": "m1",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Hello!"}],
                },
                sequence=1,
                role="assistant",
            ),
        ]
        input_items, size = build_replay_request(items, "Hi again")
        assert input_items is not None
        assert len(input_items) == 2  # history + new user message
        assert input_items[0]["role"] == "assistant"
        assert input_items[1]["role"] == "user"

    def test_build_replay_over_budget(self):
        huge = _make_item(
            "message",
            {
                "type": "message",
                "id": "m1",
                "role": "user",
                "content": [{"type": "input_text", "text": "x" * 200_000}],
            },
        )
        input_items, size = build_replay_request([huge], "Hi", max_chars=100_000)
        assert input_items is None
        assert size > 100_000

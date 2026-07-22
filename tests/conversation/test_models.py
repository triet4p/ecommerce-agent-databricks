"""Tests for conversation models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ecommerce_agent.conversation.models import (
    Conversation,
    ConversationItem,
    ConversationSummary,
    ItemPayload,
    Turn,
)


class TestConversation:
    def test_create(self):
        conv = Conversation(
            id=uuid.uuid4(),
            owner="user@example.com",
            title="My conversation",
        )
        assert conv.owner == "user@example.com"
        assert conv.title == "My conversation"
        assert conv.deleted_at is None

    def test_default_title(self):
        conv = Conversation(id=uuid.uuid4(), owner="user@example.com")
        assert conv.title == "New conversation"


class TestConversationSummary:
    def test_create(self):
        now = datetime.now(timezone.utc)
        summary = ConversationSummary(
            id=uuid.uuid4(),
            title="Test",
            created_at=now,
            updated_at=now,
        )
        assert summary.title == "Test"


class TestTurn:
    def test_create_active(self):
        turn = Turn(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            client_request_id="req-123",
            sequence=1,
        )
        assert turn.status == "active"
        assert turn.mlflow_trace_id is None

    def test_completed(self):
        turn = Turn(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            client_request_id="req-456",
            sequence=2,
            status="completed",
        )
        assert turn.status == "completed"


class TestConversationItem:
    def test_create_message(self):
        item = ConversationItem(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            turn_id=uuid.uuid4(),
            sequence=1,
            item_type="message",
            payload=ItemPayload(
                type="message",
                id="msg_1",
                role="user",
                content=[{"type": "input_text", "text": "Hello"}],
            ),
        )
        assert item.item_type == "message"

    def test_create_function_call(self):
        item = ConversationItem(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            turn_id=uuid.uuid4(),
            sequence=2,
            item_type="function_call",
            payload=ItemPayload(
                type="function_call",
                id="fc_1",
                call_id="call_abc",
                name="get_order_status",
                arguments='{"order_id": "42"}',
            ),
        )
        assert item.item_type == "function_call"
        assert item.payload.name == "get_order_status"

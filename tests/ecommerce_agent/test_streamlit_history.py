from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ecommerce_agent.apps.streamlit_chat_ui.history import hydrate_messages
from ecommerce_agent.conversation.models import ConversationItem, ItemPayload


def _item(
    *,
    item_type: str = "message",
    role: str | None,
    content: list[dict],
) -> ConversationItem:
    return ConversationItem(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        turn_id=uuid.uuid4(),
        sequence=1,
        item_type=item_type,
        role=role,
        payload=ItemPayload(type=item_type, role=role, content=content),
        item_key="history-test",
        created_at=datetime.now(timezone.utc),
    )


def test_hydrate_messages_restores_only_visible_user_and_assistant_text() -> None:
    items = [
        _item(
            role="user",
            content=[{"type": "input_text", "text": "Where is my order?"}],
        ),
        _item(
            role="assistant",
            content=[
                {"type": "output_text", "text": "It is "},
                {"type": "output_text", "text": "in transit."},
            ],
        ),
        _item(
            item_type="function_call",
            role=None,
            content=[],
        ),
    ]

    assert hydrate_messages(items) == [
        {"role": "user", "content": "Where is my order?"},
        {"role": "assistant", "content": "It is in transit."},
    ]


def test_hydrate_messages_skips_empty_or_non_chat_roles() -> None:
    items = [
        _item(role="assistant", content=[{"type": "output_text", "text": "  "}]),
        _item(role=None, content=[{"type": "output_text", "text": "hidden"}]),
    ]

    assert hydrate_messages(items) == []

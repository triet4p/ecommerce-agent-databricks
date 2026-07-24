"""Streamlit-only adapters for rendering persisted conversation history."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conversation.models import ConversationItem


def hydrate_messages(items: Iterable["ConversationItem"]) -> list[dict[str, str]]:
    """Convert persisted message items into Streamlit chat message dictionaries."""

    messages: list[dict[str, str]] = []
    for item in items:
        if item.item_type != "message" or item.role not in {"user", "assistant"}:
            continue

        text_parts = [
            part.get("text", "")
            for part in item.payload.content
            if part.get("type") in {"input_text", "output_text", "text"}
            and isinstance(part.get("text"), str)
        ]
        text = "".join(text_parts).strip()
        if text:
            messages.append({"role": item.role, "content": text})
    return messages

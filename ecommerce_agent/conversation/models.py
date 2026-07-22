"""Pydantic models for the conversation persistence layer.

These models define the shape of data returned by the conversation repository.
They are used internally by the Chat UI App — never sent directly to the
Agent App.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------


class Conversation(BaseModel):
    """A persisted conversation owned by a single end user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner: str
    title: str = "New conversation"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None


class ConversationSummary(BaseModel):
    """Lightweight representation used for conversation list display."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Turns
# ---------------------------------------------------------------------------


TurnStatus = Literal["active", "completed", "failed", "cancelled"]


class Turn(BaseModel):
    """A single turn within a conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    client_request_id: str
    sequence: int
    status: TurnStatus = "active"
    mlflow_trace_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Conversation items
# ---------------------------------------------------------------------------


ItemType = Literal["message", "function_call", "function_call_output"]


class ItemPayload(BaseModel):
    """The canonical payload body stored for a conversation item.

    This mirrors the Sprint 2 Responses API output item structure.
    """

    model_config = ConfigDict(extra="allow")

    type: str
    id: str | None = None
    role: str | None = None
    content: list[dict[str, Any]] = Field(default_factory=list)
    call_id: str | None = None
    name: str | None = None
    arguments: str | None = None
    output: str | None = None


class ConversationItem(BaseModel):
    """A single canonical item within a turn."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    turn_id: uuid.UUID
    sequence: int
    item_type: ItemType
    role: str | None = None
    payload: ItemPayload
    item_key: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

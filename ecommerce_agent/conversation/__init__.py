"""Conversation persistence and history replay for Sprint 3.

This package provides:
- A Lakebase-backed conversation repository for durable per-user session storage
- Canonical item persistence based on the Sprint 2 Responses API event schema
- Bounded history replay for stateless Agent App invocation
- Idempotent turn management with monotonic sequencing
- Soft deletion and retention semantics

Usage:
    repo = ConversationRepository(pool)
    conv = await repo.create_conv("user@example.com")
    turn = await repo.create_turn(conv.id, "req-uuid-42")
"""

from .repository import ConversationRepository
from .models import (
    Conversation,
    ConversationSummary,
    Turn,
    ConversationItem,
    ItemPayload,
)
from .schema import SCHEMA_VERSION

__all__ = [
    "ConversationRepository",
    "Conversation",
    "ConversationSummary",
    "Turn",
    "ConversationItem",
    "ItemPayload",
    "SCHEMA_VERSION",
]

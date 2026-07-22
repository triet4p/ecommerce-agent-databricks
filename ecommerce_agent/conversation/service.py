"""UI-neutral conversation service that the Streamlit and Sprint 4 React
clients can both use.

This is the public-facing API for conversation management. It wraps the
repository and replay logic into a single interface.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from psycopg_pool import AsyncConnectionPool

from .models import (
    Conversation,
    ConversationItem,
    ConversationSummary,
    Turn,
)
from .repository import (
    ConversationRepository,
    ConversationNotFoundError,
)
from .replay import (
    accumulate_output_items,
    build_replay_request,
)
from .schema import check_schema_version, migrate

# ---------------------------------------------------------------------------
# Public exceptions (re-exported)
# ---------------------------------------------------------------------------

ConversationNotFound = ConversationNotFoundError


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ReplayResult:
    """The result of building a replay request."""

    input_items: list[dict[str, Any]] | None
    character_count: int
    within_budget: bool


@dataclass
class StreamCommitResult:
    """Result of committing stream events to a turn."""

    turn: Turn
    output_items: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ConversationService:
    """High-level conversation service for UI clients.

    Provides both sync-style (Streamlit-compatible) and async interfaces.

    Usage:
        service = ConversationService(pool)
        conv = await service.create_conversation("user@example.com")
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool
        self._repo = ConversationRepository(pool)

    # ------------------------------------------------------------------
    # Schema management
    # ------------------------------------------------------------------

    async def ensure_schema(self) -> dict[str, Any]:
        """Ensure the database schema is up-to-date.

        Returns the migration report. Call this at startup.
        """
        return await migrate(self._pool)

    async def health(self) -> dict[str, Any]:
        """Run a health check that includes schema version verification."""
        db_ok = False
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    row = await cur.fetchone()
                    db_ok = row is not None and row[0] == 1
        except Exception as exc:
            return {"healthy": False, "database": False, "error": str(exc)}

        schema_info = await check_schema_version(self._pool)
        return {
            "healthy": db_ok and schema_info["ok"],
            "database": db_ok,
            "schema": schema_info,
        }

    # ------------------------------------------------------------------
    # Conversation CRUD
    # ------------------------------------------------------------------

    async def create_conversation(
        self, owner: str, title: str = "New conversation"
    ) -> Conversation:
        """Create a new conversation."""
        return await self._repo.create_conversation(owner, title)

    async def list_conversations(
        self,
        owner: str,
        include_deleted: bool = False,
        limit: int = 50,
    ) -> list[ConversationSummary]:
        """List conversations for the given user."""
        return await self._repo.list_conversations(
            owner, include_deleted=include_deleted, limit=limit
        )

    async def get_conversation(
        self, conversation_id: uuid.UUID, owner: str
    ) -> Conversation:
        """Get a single conversation by ID and owner."""
        return await self._repo.get_conversation(conversation_id, owner)

    async def update_title(
        self, conversation_id: uuid.UUID, owner: str, title: str
    ) -> Conversation:
        """Update the title of a conversation."""
        return await self._repo.update_title(conversation_id, owner, title)

    async def delete_conversation(
        self, conversation_id: uuid.UUID, owner: str
    ) -> None:
        """Soft-delete a conversation."""
        return await self._repo.soft_delete_conversation(conversation_id, owner)

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------

    async def create_turn(
        self,
        conversation_id: uuid.UUID,
        owner: str,
        client_request_id: str,
    ) -> Turn:
        """Create a new turn with idempotency via client_request_id."""
        return await self._repo.create_turn(
            conversation_id, owner, client_request_id
        )

    async def complete_turn(
        self,
        turn_id: uuid.UUID,
        conversation_id: uuid.UUID,
        owner: str,
        stream_events: list[dict[str, Any]],
        mlflow_trace_id: str | None = None,
        user_message: str | None = None,
    ) -> StreamCommitResult:
        """Commit stream events to a completed turn.

        Accumulates canonical output items from the stream events and
        persists them. If the stream contained an error, no items are
        persisted and the turn is NOT completed — use ``fail_turn()``
        instead.

        Args:
            user_message: Optional user prompt to persist as the first item.

        Returns:
            A ``StreamCommitResult`` with the completed turn and accumulated
            output items.
        """
        output_items = accumulate_output_items(stream_events)

        turn = await self._repo.complete_turn(
            turn_id=turn_id,
            conversation_id=conversation_id,
            owner=owner,
            items=output_items,
            mlflow_trace_id=mlflow_trace_id,
            user_message=user_message,
        )

        return StreamCommitResult(turn=turn, output_items=output_items)

    async def fail_turn(
        self,
        turn_id: uuid.UUID,
        conversation_id: uuid.UUID,
        owner: str,
    ) -> Turn:
        """Mark a turn as failed (no output persisted)."""
        return await self._repo.fail_turn(turn_id, conversation_id, owner)

    # ------------------------------------------------------------------
    # History replay
    # ------------------------------------------------------------------

    async def build_replay(
        self,
        conversation_id: uuid.UUID,
        owner: str,
        user_message: str,
    ) -> ReplayResult:
        """Build a complete bounded history for an agent turn.

        Loads all completed items, converts them to Responses API input
        format, appends the new user message, and checks the character
        budget.

        Returns:
            A ``ReplayResult``. When ``within_budget`` is False,
            ``input_items`` is ``None`` and the caller should inform the
            user instead of calling the agent.
        """
        items = await self._repo.get_replay_items(conversation_id, owner)
        input_items, char_count = build_replay_request(items, user_message)

        return ReplayResult(
            input_items=input_items,
            character_count=char_count,
            within_budget=input_items is not None,
        )

    async def set_mlflow_trace_id(
        self,
        turn_id: uuid.UUID,
        conversation_id: uuid.UUID,
        mlflow_trace_id: str,
    ) -> None:
        """Set the MLflow trace ID on a turn."""
        await self._repo.set_mlflow_trace_id(
            turn_id, conversation_id, mlflow_trace_id
        )

    async def get_conversation_with_items(
        self,
        conversation_id: uuid.UUID,
        owner: str,
    ) -> tuple[Conversation, list[ConversationItem]]:
        """Load conversation with all persisted items for UI restoration."""
        return await self._repo.get_conversation_with_items(
            conversation_id, owner
        )

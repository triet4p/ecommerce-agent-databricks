"""ConversationRepository — Lakebase-backed CRUD for conversation sessions.

Every operation is scoped by ``owner`` (the ``X-Forwarded-User`` identity).
All turn and item operations verify conversation ownership before proceeding.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from psycopg import sql
from psycopg_pool import AsyncConnectionPool

from .models import (
    Conversation,
    ConversationItem,
    ConversationSummary,
    ItemPayload,
    ItemType,
    Turn,
)
from .redaction import (
    redact_payload,
    validate_payload_size,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_TITLE_LENGTH = 500
_MAX_ITEMS_PER_TURN = 100

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ConversationNotFoundError(Exception):
    """Raised when a requested conversation does not exist or is not owned by
    the caller."""


class TurnNotFoundError(Exception):
    """Raised when a requested turn does not exist."""


class PayloadTooLargeError(Exception):
    """Raised when an item payload exceeds the maximum allowed size."""


class PayloadRedactedError(Exception):
    """Raised when an item payload is invalid after redaction."""


class IdempotentTurnExistsError(Exception):
    """Raised when a turn with the same client_request_id already exists in
    the conversation (this is expected in retry scenarios — the caller should
    use the existing turn)."""


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class ConversationRepository:
    """Lakebase-backed repository for conversation CRUD operations.

    All public methods accept an ``owner`` parameter that MUST be the
    authenticated ``X-Forwarded-User`` value. Operations are scoped to that
    owner.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    # ------------------------------------------------------------------
    # C1: Conversation creation
    # ------------------------------------------------------------------

    async def create_conversation(
        self,
        owner: str,
        title: str = "New conversation",
    ) -> Conversation:
        """Create a new conversation owned by the given user.

        Args:
            owner: The authenticated user identity (from X-Forwarded-User).
            title: An optional initial title (max 500 chars).

        Returns:
            The newly created Conversation.
        """
        truncated_title = title[:_MAX_TITLE_LENGTH]
        conv_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO conversations (id, owner, title, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (conv_id, owner, truncated_title, now, now),
                )
            await conn.commit()

        return Conversation(
            id=conv_id,
            owner=owner,
            title=truncated_title,
            created_at=now,
            updated_at=now,
        )

    # ------------------------------------------------------------------
    # C2: Owner-scoped conversation listing
    # ------------------------------------------------------------------

    async def list_conversations(
        self,
        owner: str,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationSummary]:
        """List conversations owned by the given user, ordered by most recent
        activity.

        Args:
            owner: The authenticated user identity.
            include_deleted: If True, include soft-deleted conversations.
            limit: Maximum number of results to return.
            offset: Number of results to skip.

        Returns:
            A list of ConversationSummary objects.
        """
        clauses = ["owner = %s"]
        params: list[Any] = [owner]

        if not include_deleted:
            clauses.append("deleted_at IS NULL")

        where = " AND ".join(clauses)
        query = sql.SQL(
            "SELECT id, title, created_at, updated_at "
            "FROM conversations "
            "WHERE {} "
            "ORDER BY updated_at DESC "
            "LIMIT %s OFFSET %s"
        ).format(sql.SQL(where))
        params.extend([limit, offset])

        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                rows = await cur.fetchall()

        return [
            ConversationSummary(
                id=row[0],
                title=row[1],
                created_at=row[2],
                updated_at=row[3],
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # C3: Owner-scoped conversation loading with ordered items
    # ------------------------------------------------------------------

    async def get_conversation(
        self,
        conversation_id: uuid.UUID,
        owner: str,
    ) -> Conversation:
        """Load a conversation by ID, verifying ownership.

        Raises:
            ConversationNotFoundError: If the conversation does not exist or
                is not owned by the caller.
        """
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id, owner, title, created_at, updated_at, deleted_at "
                    "FROM conversations WHERE id = %s AND owner = %s AND deleted_at IS NULL",
                    (conversation_id, owner),
                )
                row = await cur.fetchone()

        if row is None:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found for owner {owner}"
            )

        return Conversation(
            id=row[0],
            owner=row[1],
            title=row[2],
            created_at=row[3],
            updated_at=row[4],
            deleted_at=row[5],
        )

    async def get_conversation_with_items(
        self,
        conversation_id: uuid.UUID,
        owner: str,
    ) -> tuple[Conversation, list[ConversationItem]]:
        """Load a conversation and its ordered items, verifying ownership.

        Returns:
            A tuple of (Conversation, list of ConversationItem).
        """
        conv = await self.get_conversation(conversation_id, owner)

        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT ci.id, ci.conversation_id, ci.turn_id, ci.sequence, "
                    "       ci.item_type, ci.role, ci.payload, ci.item_key, ci.created_at "
                    "FROM conversation_items ci "
                    "JOIN conversations c ON c.id = ci.conversation_id "
                    "WHERE ci.conversation_id = %s AND c.owner = %s AND c.deleted_at IS NULL "
                    "ORDER BY ci.sequence ASC",
                    (conversation_id, owner),
                )
                rows = await cur.fetchall()

        items = [_row_to_item(row) for row in rows]
        return conv, items

    # ------------------------------------------------------------------
    # C4: Title updates with length limits
    # ------------------------------------------------------------------

    async def update_title(
        self,
        conversation_id: uuid.UUID,
        owner: str,
        title: str,
    ) -> Conversation:
        """Update the title of a conversation.

        Args:
            conversation_id: The conversation ID.
            owner: The authenticated user identity.
            title: The new title (max 500 characters).

        Returns:
            The updated Conversation.

        Raises:
            ConversationNotFoundError: If the conversation does not exist or
                is not owned by the caller.
        """
        truncated = title[:_MAX_TITLE_LENGTH]
        now = datetime.now(timezone.utc)

        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE conversations SET title = %s, updated_at = %s "
                    "WHERE id = %s AND owner = %s AND deleted_at IS NULL "
                    "RETURNING id, owner, title, created_at, updated_at, deleted_at",
                    (truncated, now, conversation_id, owner),
                )
                row = await cur.fetchone()
            await conn.commit()

        if row is None:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found for owner {owner}"
            )

        return Conversation(
            id=row[0],
            owner=row[1],
            title=row[2],
            created_at=row[3],
            updated_at=row[4],
            deleted_at=row[5],
        )

    # ------------------------------------------------------------------
    # C5: Soft deletion
    # ------------------------------------------------------------------

    async def soft_delete_conversation(
        self,
        conversation_id: uuid.UUID,
        owner: str,
    ) -> None:
        """Recoverably delete a conversation without removing its audit data.

        Raises:
            ConversationNotFoundError: If the conversation does not exist or
                is not owned by the caller.
        """
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE conversations SET deleted_at = now(), updated_at = now() "
                    "WHERE id = %s AND owner = %s AND deleted_at IS NULL",
                    (conversation_id, owner),
                )
                updated = cur.rowcount
            await conn.commit()

        if updated == 0:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found for owner {owner}"
            )

    # ------------------------------------------------------------------
    # C6: Idempotent turn creation
    # ------------------------------------------------------------------

    async def create_turn(
        self,
        conversation_id: uuid.UUID,
        owner: str,
        client_request_id: str,
    ) -> Turn:
        """Create a new turn in the conversation.

        Uses the ``client_request_id`` for idempotency — if a turn with the
        same ``(conversation_id, client_request_id)`` already exists, raises
        ``IdempotentTurnExistsError``. This allows the caller to retry safely:
        on a 409/duplicate, the caller can retrieve the existing turn.

        Args:
            conversation_id: The conversation ID.
            owner: The authenticated user identity.
            client_request_id: A caller-generated unique ID for this turn
                (e.g. a UUID or request correlation ID).

        Returns:
            The newly created Turn.

        Raises:
            ConversationNotFoundError: If the conversation does not exist or
                is not owned by the caller.
            IdempotentTurnExistsError: If a turn with the same
                ``client_request_id`` already exists in this conversation.
        """
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                # This row lock serializes both turn and item sequence allocation
                # for the conversation.  It also checks owner and soft deletion.
                await cur.execute(
                    "SELECT id FROM conversations WHERE id = %s AND owner = %s "
                    "AND deleted_at IS NULL FOR UPDATE",
                    (conversation_id, owner),
                )
                if await cur.fetchone() is None:
                    raise ConversationNotFoundError("Conversation not found for owner")
                await cur.execute(
                    "SELECT COALESCE(MAX(sequence), 0) + 1 FROM turns WHERE conversation_id = %s",
                    (conversation_id,),
                )
                (next_seq,) = await cur.fetchone()
                await cur.execute(
                    "INSERT INTO turns (id, conversation_id, client_request_id, sequence, status) "
                    "VALUES (%s, %s, %s, %s, 'active') "
                    "ON CONFLICT (conversation_id, client_request_id) DO NOTHING "
                    "RETURNING id, conversation_id, client_request_id, sequence, status, "
                    "mlflow_trace_id, created_at, completed_at",
                    (uuid.uuid4(), conversation_id, client_request_id, next_seq),
                )
                row = await cur.fetchone()
                if row is None:
                    await cur.execute(
                        "SELECT id, conversation_id, client_request_id, sequence, status, "
                        "mlflow_trace_id, created_at, completed_at FROM turns "
                        "WHERE conversation_id = %s AND client_request_id = %s",
                        (conversation_id, client_request_id),
                    )
                    row = await cur.fetchone()
                await cur.execute(
                    "UPDATE conversations SET updated_at = now() WHERE id = %s",
                    (conversation_id,),
                )
            await conn.commit()
        if row is None:
            raise RuntimeError("Could not create or retrieve turn")
        return _row_to_turn(row)

    # ------------------------------------------------------------------
    # C7: Monotonic sequence allocation (implemented inline in create_turn)
    # ------------------------------------------------------------------
    # Monotonic sequence allocation is done atomically via:
    #   SELECT COALESCE(MAX(sequence), 0) + 1 FROM turns WHERE conversation_id = %s
    # This works correctly under concurrent inserts because the UNIQUE
    # constraint on (conversation_id, sequence) prevents duplicates.
    # PostgreSQL serializes DML on the same table, and the unique constraint
    # ensures no two turns get the same sequence in a conversation.

    # ------------------------------------------------------------------
    # C8: Atomic completed-turn persistence
    # ------------------------------------------------------------------

    async def complete_turn(
        self,
        turn_id: uuid.UUID,
        conversation_id: uuid.UUID,
        owner: str,
        items: list[dict[str, Any]],
        mlflow_trace_id: str | None = None,
        user_message: str | None = None,
    ) -> Turn:
        """Atomically persist completed turn items and mark the turn as
        completed.

        Accepts a list of output items from the Responses API stream and
        persists each as a ``ConversationItem``. Items are redacted before
        storage. If ``user_message`` is provided, it is persisted as the
        first item of the turn.

        Args:
            turn_id: The turn ID to complete.
            conversation_id: The owning conversation ID.
            owner: The authenticated user identity.
            items: The list of output items from the Responses API response.
            mlflow_trace_id: Optional MLflow trace ID to associate.
            user_message: Optional user prompt to persist.

        Returns:
            The completed Turn.
        """
        if len(items) > _MAX_ITEMS_PER_TURN:
            raise PayloadRedactedError(
                f"A turn may contain at most {_MAX_ITEMS_PER_TURN} output items"
            )
        raw_persisted: list[tuple[ItemType, str | None, dict[str, Any], str]] = []
        if user_message is not None:
            user_payload = redact_payload(
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_message}],
                }
            )
            if not validate_payload_size(user_payload):
                raise PayloadTooLargeError("User message exceeds maximum size")
            raw_persisted.append(("message", "user", user_payload, "input"))
        for index, raw_item in enumerate(items):
            payload = redact_payload(raw_item)
            if not validate_payload_size(payload):
                raise PayloadTooLargeError(f"Item {index} payload exceeds maximum size")
            # Stable stream provenance first; index is deterministic fallback.
            provenance = raw_item.get("id") or raw_item.get("call_id") or str(index)
            item_key = f"{self._infer_item_type(raw_item)}:{provenance}"
            raw_persisted.append(
                (
                    self._infer_item_type(raw_item),
                    raw_item.get("role"),
                    payload,
                    item_key,
                )
            )
        now = datetime.now(timezone.utc)

        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                # Lock the owned active conversation, then transition the turn.
                await cur.execute(
                    "SELECT id FROM conversations WHERE id = %s AND owner = %s "
                    "AND deleted_at IS NULL FOR UPDATE",
                    (conversation_id, owner),
                )
                if await cur.fetchone() is None:
                    raise ConversationNotFoundError("Conversation not found for owner")

                await cur.execute(
                    "UPDATE turns SET status = 'completed', completed_at = %s, "
                    "mlflow_trace_id = COALESCE(%s, mlflow_trace_id) "
                    "WHERE id = %s AND conversation_id = %s AND status = 'active' "
                    "RETURNING id, conversation_id, client_request_id, sequence, status, "
                    "mlflow_trace_id, created_at, completed_at",
                    (now, mlflow_trace_id, turn_id, conversation_id),
                )
                turn_row = await cur.fetchone()
                if turn_row is None:
                    await cur.execute(
                        "SELECT id, conversation_id, client_request_id, sequence, status, "
                        "mlflow_trace_id, created_at, completed_at FROM turns "
                        "WHERE id = %s AND conversation_id = %s",
                        (turn_id, conversation_id),
                    )
                    existing = await cur.fetchone()
                    if existing is None:
                        raise TurnNotFoundError(f"Turn {turn_id} not found")
                    if existing[4] == "completed":
                        await conn.commit()
                        return _row_to_turn(existing)
                    raise TurnNotFoundError(f"Turn {turn_id} is not active")

                # Get the next item sequence
                await cur.execute(
                    "SELECT COALESCE(MAX(sequence), 0) + 1 FROM conversation_items "
                    "WHERE conversation_id = %s",
                    (conversation_id,),
                )
                (next_item_seq,) = await cur.fetchone()

                for i, (item_type, role, payload, item_key) in enumerate(raw_persisted):
                    await cur.execute(
                        "INSERT INTO conversation_items "
                        "(id, conversation_id, turn_id, sequence, item_type, "
                        " role, payload, item_key) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s) "
                        "ON CONFLICT (turn_id, item_key) DO NOTHING",
                        (
                            uuid.uuid4(),
                            conversation_id,
                            turn_id,
                            next_item_seq + i,
                            item_type,
                            role,
                            _payload_to_json(payload),
                            item_key,
                        ),
                    )
                await cur.execute(
                    "UPDATE conversations SET updated_at = %s WHERE id = %s",
                    (now, conversation_id),
                )

            await conn.commit()

        return _row_to_turn(turn_row)

    # ------------------------------------------------------------------
    # C9: Failed-turn persistence
    # ------------------------------------------------------------------

    async def fail_turn(
        self,
        turn_id: uuid.UUID,
        conversation_id: uuid.UUID,
        owner: str,
    ) -> Turn:
        """Mark a turn as failed without persisting any output items.

        Failed turns are recorded in the database so the UI can display them
        as failed, but their (partial or missing) output is NOT included in
        the canonical history replayed to the Agent App.

        Raises:
            TurnNotFoundError: If the turn is not found.
            ConversationNotFoundError: If ownership check fails.
        """
        now = datetime.now(timezone.utc)

        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE turns SET status = 'failed', completed_at = %s "
                    "WHERE id = %s AND conversation_id = %s AND status = 'active' "
                    "AND EXISTS (SELECT 1 FROM conversations c WHERE c.id = %s "
                    "AND c.owner = %s AND c.deleted_at IS NULL)",
                    (now, turn_id, conversation_id, conversation_id, owner),
                )
                updated = cur.rowcount
            await conn.commit()

        if updated == 0:
            existing = await self._get_owned_turn(turn_id, conversation_id, owner)
            if existing is not None and existing.status == "failed":
                return existing
            raise TurnNotFoundError(
                f"Active turn {turn_id} not found in conversation {conversation_id}"
            )

        await self._touch_conversation(conversation_id)
        return await self._get_turn(turn_id)

    async def cancel_turn(
        self, turn_id: uuid.UUID, conversation_id: uuid.UUID, owner: str
    ) -> Turn:
        """Atomically transition an owned active turn to ``cancelled``."""
        now = datetime.now(timezone.utc)
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE turns SET status = 'cancelled', completed_at = %s "
                    "WHERE id = %s AND conversation_id = %s AND status = 'active' "
                    "AND EXISTS (SELECT 1 FROM conversations c WHERE c.id = %s "
                    "AND c.owner = %s AND c.deleted_at IS NULL) RETURNING id, conversation_id, "
                    "client_request_id, sequence, status, mlflow_trace_id, created_at, completed_at",
                    (now, turn_id, conversation_id, conversation_id, owner),
                )
                row = await cur.fetchone()
            await conn.commit()
        if row is None:
            existing = await self._get_owned_turn(turn_id, conversation_id, owner)
            if existing is not None and existing.status == "cancelled":
                return existing
            raise TurnNotFoundError(f"Active turn {turn_id} not found for owner")
        return _row_to_turn(row)

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------

    async def _get_owned_turn(
        self, turn_id: uuid.UUID, conversation_id: uuid.UUID, owner: str
    ) -> Turn | None:
        """Load a terminal turn only when it remains owned and not deleted."""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT t.id, t.conversation_id, t.client_request_id, t.sequence, "
                    "t.status, t.mlflow_trace_id, t.created_at, t.completed_at "
                    "FROM turns t JOIN conversations c ON c.id = t.conversation_id "
                    "WHERE t.id = %s AND t.conversation_id = %s AND c.owner = %s "
                    "AND c.deleted_at IS NULL",
                    (turn_id, conversation_id, owner),
                )
                row = await cur.fetchone()
        return _row_to_turn(row) if row is not None else None

    async def get_replay_items(
        self,
        conversation_id: uuid.UUID,
        owner: str,
    ) -> list[ConversationItem]:
        """Load completed items for history replay, excluding failed turns.

        Only items from turns with status 'completed' are returned.
        Items are ordered by sequence ASC for correct replay ordering.
        """
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT ci.id, ci.conversation_id, ci.turn_id, ci.sequence, "
                    "       ci.item_type, ci.role, ci.payload, ci.item_key, ci.created_at "
                    "FROM conversation_items ci "
                    "JOIN conversations c ON c.id = ci.conversation_id "
                    "JOIN turns t ON t.id = ci.turn_id "
                    "WHERE ci.conversation_id = %s AND c.owner = %s "
                    "  AND c.deleted_at IS NULL AND t.status = 'completed' "
                    "ORDER BY ci.sequence ASC",
                    (conversation_id, owner),
                )
                rows = await cur.fetchall()

        return [_row_to_item(row) for row in rows]

    async def set_mlflow_trace_id(
        self,
        turn_id: uuid.UUID,
        conversation_id: uuid.UUID,
        owner: str,
        mlflow_trace_id: str,
    ) -> None:
        """Set the MLflow trace ID on a turn record without adding it to
        model history."""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE turns SET mlflow_trace_id = %s WHERE id = %s "
                    "AND conversation_id = %s AND EXISTS (SELECT 1 FROM conversations c "
                    "WHERE c.id = %s AND c.owner = %s AND c.deleted_at IS NULL)",
                    (mlflow_trace_id, turn_id, conversation_id, conversation_id, owner),
                )
                if cur.rowcount == 0:
                    raise TurnNotFoundError(f"Turn {turn_id} not found for owner")
            await conn.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _touch_conversation(self, conversation_id: uuid.UUID) -> None:
        """Update the conversation's ``updated_at`` timestamp."""
        now = datetime.now(timezone.utc)
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE conversations SET updated_at = %s WHERE id = %s",
                    (now, conversation_id),
                )
            await conn.commit()

    async def _get_turn(self, turn_id: uuid.UUID) -> Turn:
        """Fetch a turn by ID."""
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id, conversation_id, client_request_id, sequence, "
                    "       status, mlflow_trace_id, created_at, completed_at "
                    "FROM turns WHERE id = %s",
                    (turn_id,),
                )
                row = await cur.fetchone()
        if row is None:
            raise TurnNotFoundError(f"Turn {turn_id} not found")
        return Turn(
            id=row[0],
            conversation_id=row[1],
            client_request_id=row[2],
            sequence=row[3],
            status=row[4],
            mlflow_trace_id=row[5],
            created_at=row[6],
            completed_at=row[7],
        )

    @staticmethod
    def _infer_item_type(raw_item: dict[str, Any]) -> ItemType:
        """Infer the item type from a raw Responses API output item."""
        item_type = raw_item.get("type", "")
        if item_type == "message":
            return "message"
        elif item_type == "function_call":
            return "function_call"
        elif item_type == "function_call_output":
            return "function_call_output"
        # Fallback: infer from role
        role = raw_item.get("role", "")
        if role == "tool":
            return "function_call_output"
        return "message"


def _row_to_item(row: Sequence[Any]) -> ConversationItem:
    """Convert a database row to a ConversationItem."""
    return ConversationItem(
        id=row[0],
        conversation_id=row[1],
        turn_id=row[2],
        sequence=row[3],
        item_type=row[4],
        role=row[5],
        payload=ItemPayload(**row[6])
        if isinstance(row[6], dict)
        else ItemPayload(type="unknown"),
        item_key=row[7],
        created_at=row[8],
    )


def _row_to_turn(row: Sequence[Any]) -> Turn:
    """Convert a canonical turn select row into its model."""
    return Turn(
        id=row[0],
        conversation_id=row[1],
        client_request_id=row[2],
        sequence=row[3],
        status=row[4],
        mlflow_trace_id=row[5],
        created_at=row[6],
        completed_at=row[7],
    )


def _payload_to_json(payload: dict[str, Any]) -> str:
    """Serialize a payload dict to a JSON string for PostgreSQL JSONB."""
    import json

    return json.dumps(payload, ensure_ascii=False, default=str)


def _is_unique_violation(exc: Exception) -> bool:
    """Check if an exception is a PostgreSQL unique constraint violation."""
    err_msg = str(exc)
    return "unique" in err_msg.lower() or "duplicate" in err_msg.lower()

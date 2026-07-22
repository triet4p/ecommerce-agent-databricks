"""Database schema migrations for the conversation persistence layer.

Uses a version-based migration system with an advisory lock to prevent
concurrent App instances from applying the same migration twice.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema version — bump when adding new migrations below
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Migration definitions: ordered list of (version, description, SQL)
# ---------------------------------------------------------------------------

MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (
        1,
        "Create conversations, turns, and conversation_items tables",
        [
            # Ensure the schema exists
            "CREATE SCHEMA IF NOT EXISTS conversations",
            # --- conversations ---
            """
            CREATE TABLE IF NOT EXISTS conversations.conversations (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                owner           VARCHAR(255) NOT NULL,
                title           VARCHAR(500) NOT NULL DEFAULT 'New conversation',
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                deleted_at      TIMESTAMPTZ
            )
            """,
            # --- turns ---
            """
            CREATE TABLE IF NOT EXISTS conversations.turns (
                id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                conversation_id   UUID NOT NULL REFERENCES conversations.conversations(id)
                                  ON DELETE CASCADE,
                client_request_id VARCHAR(255) NOT NULL,
                sequence          INTEGER NOT NULL,
                status            VARCHAR(32) NOT NULL DEFAULT 'active',
                mlflow_trace_id   VARCHAR(255),
                created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
                completed_at      TIMESTAMPTZ,
                UNIQUE (conversation_id, client_request_id),
                UNIQUE (conversation_id, sequence)
            )
            """,
            # --- conversation_items ---
            """
            CREATE TABLE IF NOT EXISTS conversations.conversation_items (
                id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                conversation_id   UUID NOT NULL REFERENCES conversations.conversations(id)
                                  ON DELETE CASCADE,
                turn_id           UUID NOT NULL REFERENCES conversations.turns(id)
                                  ON DELETE CASCADE,
                sequence          INTEGER NOT NULL,
                item_type         VARCHAR(64) NOT NULL,
                role              VARCHAR(32),
                payload           JSONB NOT NULL,
                item_key          VARCHAR(255),
                created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (conversation_id, turn_id, sequence)
            )
            """,
            # --- indexes for owner listing ---
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_owner
            ON conversations.conversations(owner, updated_at DESC)
            """,
            # --- indexes for session loading ---
            """
            CREATE INDEX IF NOT EXISTS idx_items_conversation
            ON conversations.conversation_items(conversation_id, sequence ASC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_items_turn
            ON conversations.conversation_items(turn_id, sequence ASC)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_turns_conversation
            ON conversations.turns(conversation_id, sequence ASC)
            """,
            # --- schema version tracking ---
            """
            CREATE TABLE IF NOT EXISTS conversations._schema_version (
                version   INTEGER NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                applied_by VARCHAR(255) NOT NULL DEFAULT 'app'
            )
            """,
        ],
    ),
]


# ---------------------------------------------------------------------------
# Migration lock (advisory)
# ---------------------------------------------------------------------------

# pg_try_advisory_lock requires a bigint (64-bit signed). UUID.int is 128-bit,
# so we take the lower 63 bits (positive signed int64 range) to avoid overflow.
_LOCK_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "ecommerce-agent-databricks-schema-migration").int & ((1 << 63) - 1)


async def _acquire_migration_lock(pool: AsyncConnectionPool) -> bool:
    """Try to acquire a Postgres advisory lock for migrations.

    Returns:
        ``True`` if the lock was acquired, ``False`` if another session holds it.
    """
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT pg_try_advisory_lock(%s::bigint)", (_LOCK_ID,))
            row = await cur.fetchone()
            acquired = row[0] if row else False
            if acquired:
                logger.info("Acquired schema migration advisory lock")
            else:
                logger.warning("Could not acquire migration advisory lock — another instance may be migrating")
            return acquired


async def _release_migration_lock(pool: AsyncConnectionPool) -> None:
    """Release the advisory migration lock."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT pg_advisory_unlock(%s::bigint)", (_LOCK_ID,))


# ---------------------------------------------------------------------------
# Current version reader
# ---------------------------------------------------------------------------


async def _get_current_version(pool: AsyncConnectionPool) -> int:
    """Read the currently applied schema version from the database.

    Returns ``0`` if the ``_schema_version`` table does not exist yet.
    """
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.tables "
                "  WHERE table_schema = 'conversations'"
                "    AND table_name = '_schema_version'"
                ")"
            )
            exists = (await cur.fetchone())[0]
            if not exists:
                return 0
            await cur.execute("SELECT MAX(version) FROM conversations._schema_version")
            row = await cur.fetchone()
            return row[0] if row and row[0] else 0


async def _record_version(pool: AsyncConnectionPool, version: int) -> None:
    """Record that a migration version has been applied."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO conversations._schema_version (version) VALUES (%s)",
                (version,),
            )
        await conn.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def migrate(pool: AsyncConnectionPool) -> dict[str, Any]:
    """Apply all pending schema migrations.

    Uses an advisory lock to ensure only one App instance applies migrations
    at a time. If the lock cannot be acquired (another instance is migrating),
    this call waits briefly and returns a report indicating no migrations were
    applied.

    Args:
        pool: An open connection pool to the Lakebase database.

    Returns:
        A dict with keys:
        - ``success``: bool
        - ``applied``: list of version numbers that were applied
        - ``current_version``: int
        - ``skipped_due_to_lock``: bool
    """
    applied: list[int] = []
    acquired = await _acquire_migration_lock(pool)
    if not acquired:
        current = await _get_current_version(pool)
        return {
            "success": True,
            "applied": applied,
            "current_version": current,
            "skipped_due_to_lock": True,
        }

    try:
        current_version = await _get_current_version(pool)
        pending = [m for m in MIGRATIONS if m[0] > current_version]

        if not pending:
            logger.info("Schema is up-to-date at version %s", current_version)
            return {
                "success": True,
                "applied": applied,
                "current_version": current_version,
                "skipped_due_to_lock": False,
            }

        for version, description, statements in pending:
            logger.info("Applying migration v%s: %s", version, description)
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    for sql in statements:
                        await cur.execute(sql)
                await conn.commit()
            await _record_version(pool, version)
            applied.append(version)
            logger.info("Applied migration v%s", version)

        current_version = await _get_current_version(pool)
        return {
            "success": True,
            "applied": applied,
            "current_version": current_version,
            "skipped_due_to_lock": False,
        }
    finally:
        await _release_migration_lock(pool)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def check_schema_version(pool: AsyncConnectionPool) -> dict[str, Any]:
    """Verify that the schema is at the expected version.

    Returns a dict with ``expected``, ``actual``, and ``ok`` keys.
    """
    actual = await _get_current_version(pool)
    return {
        "expected": SCHEMA_VERSION,
        "actual": actual,
        "ok": actual >= SCHEMA_VERSION,
    }

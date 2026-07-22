"""Tests for ConversationRepository (S3-C1 through S3-C9, S3-F1-F3).

Uses mocked async pg connections for unit test isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from ecommerce_agent.conversation.repository import (
    ConversationNotFoundError,
    ConversationRepository,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_pool():
    """Create a mock AsyncConnectionPool.

    Uses MagicMock for connection() because AsyncMock makes connection()
    return a coroutine, which then fails in ``async with pool.connection()``
    since bare coroutines lack ``__aenter__``.
    """
    pool = MagicMock()
    pool.connection = MagicMock()
    return pool


@pytest.fixture
def repo(mock_pool):
    return ConversationRepository(mock_pool)


def _fake_cursor(fetch_result=None, rowcount=1):
    """Create a mock cursor that returns a given result.

    All database methods (execute, fetchone, fetchall) are AsyncMock so the
    repository can ``await`` them.
    """
    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=fetch_result)
    cursor.fetchall = AsyncMock(return_value=fetch_result or [])
    cursor.rowcount = rowcount
    cursor.__aenter__ = AsyncMock(return_value=cursor)
    cursor.__aexit__ = AsyncMock(return_value=None)
    return cursor


def _make_connection(mock_pool, conn, cursor):
    """Wire up mock pool so that ``async with pool.connection() as c:``
    yields ``conn``, and ``conn.cursor()`` returns ``cursor``."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool.connection.return_value = ctx
    conn.cursor = MagicMock(return_value=cursor)
    conn.commit = AsyncMock()
    conn.rollback = AsyncMock()


_NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateConversation:
    """S3-C1: Conversation creation."""

    async def test_creates_conversation(self, repo, mock_pool):
        cursor = _fake_cursor()
        conn = MagicMock()
        _make_connection(mock_pool, conn, cursor)

        conv = await repo.create_conversation("user@test.com", "My title")

        assert conv.owner == "user@test.com"
        assert conv.title == "My title"
        assert conv.deleted_at is None
        cursor.execute.assert_called_once()

    async def test_truncates_long_title(self, repo, mock_pool):
        conn = MagicMock()
        _make_connection(mock_pool, conn, _fake_cursor())

        long_title = "x" * 1000
        conv = await repo.create_conversation("user@test.com", long_title)
        assert len(conv.title) <= 500


class TestListConversations:
    """S3-C2: Owner-scoped conversation listing."""

    async def test_lists_conversations(self, repo, mock_pool):
        fake_rows = [
            (uuid.uuid4(), "Conv 1", _NOW, _NOW),
            (uuid.uuid4(), "Conv 2", _NOW, _NOW),
        ]
        cursor = _fake_cursor(fetch_result=fake_rows)
        conn = MagicMock()
        _make_connection(mock_pool, conn, cursor)

        result = await repo.list_conversations("user@test.com")
        assert len(result) == 2
        assert result[0].title == "Conv 1"

    async def test_empty_list(self, repo, mock_pool):
        conn = MagicMock()
        _make_connection(mock_pool, conn, _fake_cursor(fetch_result=[]))

        result = await repo.list_conversations("user@test.com")
        assert result == []


class TestGetConversation:
    """S3-C3: Conversation loading with ownership check."""

    async def test_get_conversation_found(self, repo, mock_pool):
        conv_id = uuid.uuid4()
        fake_row = (conv_id, "user@test.com", "Test", _NOW, _NOW, None)
        cursor = _fake_cursor(fetch_result=fake_row)
        conn = MagicMock()
        _make_connection(mock_pool, conn, cursor)

        conv = await repo.get_conversation(conv_id, "user@test.com")
        assert conv.id == conv_id
        assert conv.owner == "user@test.com"

    async def test_get_conversation_not_found(self, repo, mock_pool):
        conn = MagicMock()
        _make_connection(mock_pool, conn, _fake_cursor(fetch_result=None))

        with pytest.raises(ConversationNotFoundError):
            await repo.get_conversation(uuid.uuid4(), "other@test.com")


class TestUpdateTitle:
    """S3-C4: Title updates with length limits."""

    async def test_updates_title(self, repo, mock_pool):
        conv_id = uuid.uuid4()
        fake_row = (conv_id, "user@test.com", "New Title", _NOW, _NOW, None)
        cursor = _fake_cursor(fetch_result=fake_row)
        conn = MagicMock()
        _make_connection(mock_pool, conn, cursor)

        conv = await repo.update_title(conv_id, "user@test.com", "New Title")
        assert conv.title == "New Title"

    async def test_update_not_found(self, repo, mock_pool):
        conn = MagicMock()
        _make_connection(mock_pool, conn, _fake_cursor(fetch_result=None))

        with pytest.raises(ConversationNotFoundError):
            await repo.update_title(uuid.uuid4(), "user@test.com", "Title")


class TestSoftDelete:
    """S3-C5: Recoverable soft deletion."""

    async def test_soft_delete(self, repo, mock_pool):
        cursor = _fake_cursor(rowcount=1)
        conn = MagicMock()
        _make_connection(mock_pool, conn, cursor)

        # Should not raise
        await repo.soft_delete_conversation(uuid.uuid4(), "user@test.com")
        assert "UPDATE conversations SET deleted_at" in cursor.execute.call_args.args[0]

    async def test_soft_delete_not_found(self, repo, mock_pool):
        conn = MagicMock()
        _make_connection(mock_pool, conn, _fake_cursor(rowcount=0))

        with pytest.raises(ConversationNotFoundError):
            await repo.soft_delete_conversation(uuid.uuid4(), "user@test.com")


class TestCreateTurn:
    """S3-C6 and S3-C7: Idempotent turn creation with monotonic sequence."""

    async def test_creates_turn(self, repo, mock_pool):
        conv_row = (uuid.uuid4(), "user@test.com", "Test", _NOW, _NOW, None)

        conn = MagicMock()
        _make_connection(mock_pool, conn, None)

        turn_row = (
            uuid.uuid4(),
            conv_row[0],
            "client-req-123",
            1,
            "active",
            None,
            _NOW,
            None,
        )
        cursor = _fake_cursor()
        cursor.fetchone = AsyncMock(side_effect=[(conv_row[0],), (1,), turn_row])
        conn.cursor = MagicMock(return_value=cursor)

        result = await repo.create_turn(uuid.uuid4(), "user@test.com", "client-req-123")
        assert result.client_request_id == "client-req-123"
        assert result.sequence == 1


class TestFailTurn:
    """S3-C9: Failed-turn persistence."""

    async def test_fail_turn(self, repo, mock_pool):
        turn_row = (
            uuid.uuid4(),
            uuid.uuid4(),
            "client-req",
            1,
            "failed",
            None,
            _NOW,
            _NOW,
        )

        update_cursor = _fake_cursor(fetch_result=None, rowcount=1)
        # _touch_conversation needs a cursor (UPDATE conversations SET updated_at)
        touch_cursor = _fake_cursor(fetch_result=None, rowcount=1)
        # _get_turn needs a cursor (SELECT from turns)
        fetch_cursor = _fake_cursor(fetch_result=turn_row)

        conn = MagicMock()
        _make_connection(mock_pool, conn, None)
        conn.cursor = MagicMock(side_effect=[update_cursor, touch_cursor, fetch_cursor])

        turn = await repo.fail_turn(uuid.uuid4(), uuid.uuid4(), "user@test.com")
        assert turn.status == "failed"


class TestGetReplayItems:
    """Items from completed turns load correctly."""

    async def test_get_replay_items(self, repo, mock_pool):
        fake_items = [
            (
                uuid.uuid4(),
                uuid.uuid4(),
                uuid.uuid4(),
                1,
                "message",
                "user",
                {
                    "type": "message",
                    "content": [{"type": "input_text", "text": "Hello"}],
                },
                None,
                _NOW,
            ),
        ]

        cursor = _fake_cursor(fetch_result=fake_items)
        conn = MagicMock()
        _make_connection(mock_pool, conn, cursor)

        items = await repo.get_replay_items(uuid.uuid4(), "user@test.com")
        assert len(items) == 1
        assert items[0].item_type == "message"

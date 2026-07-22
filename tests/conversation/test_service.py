"""Tests for ConversationService (S3-E6 boundary, S3-F2 isolation, S3-F5 budget)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from ecommerce_agent.conversation.service import ConversationService


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    pool.connection = MagicMock()
    return pool


@pytest.fixture
def svc(mock_pool):
    return ConversationService(mock_pool)


def _make_connection(mock_pool, conn, cursor):
    """Wire up mock pool's async context manager."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool.connection.return_value = ctx
    conn.cursor = MagicMock(return_value=cursor)
    conn.commit = AsyncMock()


class TestService:
    """S3-E6: UI-neutral conversation service boundary."""

    async def test_build_replay_empty(self, svc, mock_pool):
        """Building replay for an empty conversation returns budget info."""
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.__aenter__ = AsyncMock(return_value=cursor)
        cursor.__aexit__ = AsyncMock(return_value=None)
        cursor.fetchone = AsyncMock(return_value=None)
        cursor.fetchall = AsyncMock(return_value=[])

        conn = MagicMock()
        _make_connection(mock_pool, conn, cursor)

        # Also need to mock get_replay_items which does a join query
        # The build_replay_request -> convert_items_to_input_history will
        # produce an empty input, then append_user_message adds the prompt
        # This should always pass budget check for empty history

        result = await svc.build_replay(uuid.uuid4(), "user@test.com", "Hello")
        assert result.within_budget is True
        assert result.character_count > 0
        assert result.input_items is not None
        # Should have the new user message
        assert len(result.input_items) >= 1
        assert result.input_items[-1]["role"] == "user"

    async def test_health_check(self, svc, mock_pool):
        """Health check returns expected keys."""
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.__aenter__ = AsyncMock(return_value=cursor)
        cursor.__aexit__ = AsyncMock(return_value=None)
        cursor.fetchone = AsyncMock(return_value=(1,))
        cursor.fetchall = AsyncMock(return_value=[(1,)])

        conn = MagicMock()
        _make_connection(mock_pool, conn, cursor)

        health = await svc.health()
        assert "healthy" in health
        assert "database" in health
        assert "schema" in health

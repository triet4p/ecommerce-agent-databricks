"""Credentialed Sprint 4b persistence verification on an isolated Lakebase branch."""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

import pytest
from psycopg_pool import AsyncConnectionPool

from ecommerce_agent.conversation.repository import (
    ConversationNotFoundError,
    ConversationRepository,
    PayloadRedactedError,
)
from ecommerce_agent.conversation.schema import migrate

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


_REQUIRED_ENV = (
    "S4B_PGHOST",
    "S4B_PGDATABASE",
    "S4B_PGUSER",
    "S4B_PGPASSWORD",
    "S4B_LAKEBASE_ENDPOINT",
)


def _configured() -> bool:
    return all(os.environ.get(name) for name in _REQUIRED_ENV)


@pytest.mark.databricks
@pytest.mark.skipif(
    not _configured(), reason="isolated Lakebase credentials unavailable"
)
async def test_isolated_postgres_migration_and_repository_contract() -> None:
    endpoint = os.environ["S4B_LAKEBASE_ENDPOINT"]
    assert "/branches/s4b-integration-" in endpoint, (
        "Refusing to reset a non-integration Lakebase branch"
    )
    assert os.environ.get("S4B_ALLOW_SCHEMA_RESET") == "1", (
        "Explicit schema-reset guard is required"
    )

    pool = AsyncConnectionPool(
        conninfo=(
            f"host={os.environ['S4B_PGHOST']} "
            f"dbname={os.environ['S4B_PGDATABASE']} "
            f"user={os.environ['S4B_PGUSER']}"
        ),
        kwargs={
            "password": os.environ["S4B_PGPASSWORD"],
            "sslmode": "require",
            "options": "-c search_path=conversations,$user,public",
        },
        min_size=1,
        max_size=12,
        open=False,
    )
    await pool.open()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DROP SCHEMA IF EXISTS conversations CASCADE")
            await conn.commit()

        migration = await migrate(pool)
        assert migration["success"] is True
        assert migration["applied"] == [1, 2]
        assert migration["current_version"] == 2

        repo = ConversationRepository(pool)
        owner = f"s4b-{uuid.uuid4()}@example.com"
        other_owner = f"other-{uuid.uuid4()}@example.com"
        conversation = await repo.create_conversation(owner, "S4B integration")

        turns = await asyncio.gather(
            *[
                repo.create_turn(conversation.id, owner, f"concurrent-{index}")
                for index in range(8)
            ]
        )
        assert sorted(turn.sequence for turn in turns) == list(range(1, 9))

        first = await repo.create_turn(conversation.id, owner, "idempotent")
        repeated = await repo.create_turn(conversation.id, owner, "idempotent")
        assert repeated.id == first.id
        assert repeated.sequence == first.sequence

        completed = await repo.complete_turn(
            first.id,
            conversation.id,
            owner,
            [
                {
                    "type": "function_call",
                    "id": "fc-1",
                    "call_id": "call-1",
                    "name": "get_order_status",
                    "arguments": '{"order_id":"1","access_token":"secret"}',
                    "reasoning_content": "private",
                },
                {
                    "type": "function_call_output",
                    "call_id": "call-1",
                    "output": '{"status":"shipped","api_key":"secret"}',
                },
                {
                    "type": "message",
                    "id": "message-1",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "It shipped."}],
                },
            ],
            mlflow_trace_id="trace-s4b",
            user_message="Where is order 1?",
        )
        repeated_completion = await repo.complete_turn(
            first.id,
            conversation.id,
            owner,
            [],
            mlflow_trace_id="trace-s4b",
        )
        assert completed.status == repeated_completion.status == "completed"

        failed = turns[0]
        assert (
            await repo.fail_turn(failed.id, conversation.id, owner)
        ).status == "failed"
        assert (
            await repo.fail_turn(failed.id, conversation.id, owner)
        ).status == "failed"

        cancelled = turns[1]
        assert (
            await repo.cancel_turn(cancelled.id, conversation.id, owner)
        ).status == "cancelled"
        assert (
            await repo.cancel_turn(cancelled.id, conversation.id, owner)
        ).status == "cancelled"

        with pytest.raises(ConversationNotFoundError):
            await repo.get_conversation(conversation.id, other_owner)

        replay = await repo.get_replay_items(conversation.id, owner)
        assert [item.item_type for item in replay] == [
            "message",
            "function_call",
            "function_call_output",
            "message",
        ]
        serialized = " ".join(str(item.payload.model_dump()) for item in replay)
        assert "secret" not in serialized
        assert "<redacted>" in serialized

        overflow_turn = turns[2]
        with pytest.raises(PayloadRedactedError, match="at most 100"):
            await repo.complete_turn(
                overflow_turn.id,
                conversation.id,
                owner,
                [{"type": "message", "id": str(index)} for index in range(101)],
            )

        await repo.soft_delete_conversation(conversation.id, owner)
        with pytest.raises(ConversationNotFoundError):
            await repo.get_conversation(conversation.id, owner)
        with pytest.raises(ConversationNotFoundError):
            await repo.create_turn(conversation.id, owner, "after-delete")
    finally:
        await pool.close()

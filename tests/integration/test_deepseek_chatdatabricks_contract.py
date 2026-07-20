"""Credentialed contract for the existing DeepSeek singleton endpoint.

This test intentionally calls only through ChatDatabricks. It never creates,
updates, or substitutes a serving endpoint.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest


pytestmark = pytest.mark.databricks


@pytest.mark.skipif(
    os.getenv("RUN_DATABRICKS_TESTS") != "1",
    reason="set RUN_DATABRICKS_TESTS=1 to run credentialed Databricks tests",
)
def test_deepseek_chatdatabricks_streams_tool_reasoning_round_trip() -> None:
    """Verify two tool turns without forcing unsupported ``tool_choice``."""
    from databricks_langchain import ChatDatabricks
    from langchain_core.messages import (
        HumanMessage,
        ToolMessage,
        message_chunk_to_message,
    )
    from langchain_core.tools import tool

    @tool
    def lookup_order_total(order_id: str) -> dict[str, Any]:
        """Look up a deterministic total and status for a lab order ID."""
        return {
            "ORDER-1001": {"total_usd": 125.50, "status": "delivered"},
            "ORDER-1002": {"total_usd": 79.99, "status": "shipped"},
        }.get(order_id, {"error": "order_not_found"})

    model = ChatDatabricks(
        endpoint="deepseek-v4-streaming-agent-lab",
        use_responses_api=True,
        timeout=180,
        max_retries=3,
        stream_usage=True,
    ).bind_tools([lookup_order_total])

    def visible_text(message: Any) -> str:
        if isinstance(message.content, str):
            return message.content
        if not isinstance(message.content, list):
            return ""
        return "".join(
            block.get("text", "")
            for block in message.content
            if isinstance(block, dict)
            and block.get("type") in {"text", "output_text"}
            and isinstance(block.get("text"), str)
        )

    def stream_message(history: list[Any]) -> tuple[Any, int, int]:
        accumulated = None
        chunks = 0
        visible_deltas = 0
        for chunk in model.stream(history):
            chunks += 1
            accumulated = chunk if accumulated is None else accumulated + chunk
            visible_deltas += bool(visible_text(chunk))
        assert accumulated is not None, "ChatDatabricks returned no stream chunks"
        return message_chunk_to_message(accumulated), chunks, visible_deltas

    def run_turn(history: list[Any], question: str) -> dict[str, int]:
        history.append(HumanMessage(content=question))
        tool_calls = reasoning_rounds = chunks = visible_deltas = 0
        for _ in range(6):
            answer, new_chunks, new_visible_deltas = stream_message(history)
            history.append(answer)
            chunks += new_chunks
            visible_deltas += new_visible_deltas
            if answer.tool_calls:
                tool_calls += len(answer.tool_calls)
                if isinstance(answer.content, list):
                    reasoning_rounds += sum(
                        1
                        for block in answer.content
                        if isinstance(block, dict) and block.get("type") == "reasoning"
                    )
                for call in answer.tool_calls:
                    history.append(
                        ToolMessage(
                            content=json.dumps(lookup_order_total.invoke(call["args"])),
                            tool_call_id=call["id"],
                        )
                    )
                continue
            assert visible_text(answer).strip(), "tool loop ended without visible text"
            assert tool_calls > 0, "DeepSeek did not select the requested tool"
            assert reasoning_rounds > 0, "tool call had no reasoning item to replay"
            return {"chunks": chunks, "visible_deltas": visible_deltas}
        raise AssertionError("DeepSeek exceeded six model calls in one tool turn")

    conversation: list[Any] = []
    first = run_turn(
        conversation,
        "Use lookup_order_total for ORDER-1001, then report its total and status.",
    )
    second = run_turn(
        conversation,
        "Use lookup_order_total for ORDER-1002 and compare it to the previous order.",
    )
    assert first["visible_deltas"] > 0
    assert second["visible_deltas"] > 0

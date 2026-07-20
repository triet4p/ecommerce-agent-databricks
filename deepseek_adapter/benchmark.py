"""Latency measurement for the existing DeepSeek singleton endpoint."""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StreamingBenchmark:
    elapsed_seconds: float
    time_to_first_text_seconds: float | None
    chunks: int
    visible_characters: int


def visible_text(content: Any) -> str:
    """Extract only output text blocks; reasoning blocks are intentionally ignored."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict)
        and block.get("type") in {"text", "output_text"}
        and isinstance(block.get("text"), str)
    )


def measure_stream(chunks: Iterable[Any]) -> StreamingBenchmark:
    """Measure a stream supplied by `ChatDatabricks.stream` without logging content."""
    started = time.perf_counter()
    first_text: float | None = None
    chunk_count = 0
    characters = 0
    for chunk in chunks:
        chunk_count += 1
        text = visible_text(chunk.content)
        if text:
            first_text = first_text or time.perf_counter()
            characters += len(text)
    finished = time.perf_counter()
    return StreamingBenchmark(
        elapsed_seconds=finished - started,
        time_to_first_text_seconds=(first_text - started) if first_text else None,
        chunks=chunk_count,
        visible_characters=characters,
    )

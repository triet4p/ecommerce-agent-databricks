"""Incremental SSE (Server-Sent Events) parser for the Streamlit Chat UI.

Handles fragmented SSE boundaries, multiple events in one network chunk,
comments, blank lines, JSON events, ``[DONE]``, and malformed data.

Usage::

    parser = SSESparser()
    for chunk in response.iter_content(chunk_size=None):
        for event in parser.feed(chunk):
            if event.type == "response.output_text.delta":
                ...
            elif event == "[DONE]":
                break
"""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any


class SSESparser:
    """Incremental SSE parser that handles fragmented stream boundaries.

    Maintains a buffer across ``feed()`` calls so events split across network
    chunks are reassembled correctly.
    """

    def __init__(self) -> None:
        self._buffer = ""

    def feed(self, chunk: str | bytes) -> Generator[str, None, None]:
        """Feed a network chunk into the parser.

        Args:
            chunk: Raw string or bytes from the streaming response.

        Yields:
            Parsed ``data:`` line values as strings. For ``data: [DONE]``,
            yields the literal string ``"[DONE]"``. For JSON events, yields
            the parsed JSON string without the ``data: `` prefix.
        """
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8", errors="replace")

        self._buffer += chunk

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()

            # Skip blank lines and comments
            if not line or line.startswith(":"):
                continue

            # Check for stream termination
            if line == "data: [DONE]":
                yield "[DONE]"
                continue

            # Extract data: prefix
            if line.startswith("data: "):
                yield line[len("data: ") :]
            elif line.startswith("data:"):
                yield line[len("data:") :]

    def feed_all(self, chunk: str | bytes) -> list[str]:
        """Convenience wrapper: feed a chunk and collect all events."""
        return list(self.feed(chunk))

    @property
    def has_pending(self) -> bool:
        """Whether the buffer contains an incomplete event fragment."""
        return bool(self._buffer.strip())


class JSONEventParser:
    """Wrapper around :class:`SSESparser` that deserialises JSON events.

    Yields parsed ``dict`` objects for JSON ``data:`` lines and the
    string ``"[DONE]"`` for stream termination.
    """

    def __init__(self) -> None:
        self._sse = SSESparser()

    def feed(self, chunk: str | bytes) -> Generator[dict[str, Any] | str, None, None]:
        """Feed a chunk and yield parsed events.

        Yields:
            - ``dict`` for parsed JSON ``data:`` lines.
            - ``"[DONE]"`` for the stream-termination signal.
        """
        for data in self._sse.feed(chunk):
            if data == "[DONE]":
                yield "[DONE]"
            else:
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    # Malformed JSON — yield the raw string so callers can
                    # decide how to handle it.
                    yield data

    def feed_all(self, chunk: str | bytes) -> list[dict[str, Any] | str]:
        """Convenience wrapper: feed a chunk and collect all parsed events."""
        return list(self.feed(chunk))

    @property
    def has_pending(self) -> bool:
        return self._sse.has_pending

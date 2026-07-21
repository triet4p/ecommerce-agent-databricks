"""Tests for the incremental SSE parser (Sprint 2, D1).

Validates:
- Standard ``data:`` JSON lines
- ``data: [DONE]`` termination
- Multiple events in one network chunk
- Fragmented SSE boundaries (events split across chunks)
- Comments (``: ...``) and blank lines
- Malformed JSON
- Bytes vs string input
"""

from __future__ import annotations

import json


from ecommerce_agent.apps.chat_ui.sse_parser import JSONEventParser, SSESparser


# =========================================================================
# Basic parsing
# =========================================================================


def test_single_json_event():
    parser = SSESparser()
    result = parser.feed_all('data: {"type": "delta", "text": "Hello"}\n\n')
    assert result == ['{"type": "delta", "text": "Hello"}']


def test_done_termination():
    parser = SSESparser()
    result = parser.feed_all("data: [DONE]\n\n")
    assert result == ["[DONE]"]


def test_multiple_events_in_one_chunk():
    parser = SSESparser()
    chunk = (
        'data: {"type": "delta", "text": "Hello"}\n\n'
        'data: {"type": "delta", "text": " world"}\n\n'
        "data: [DONE]\n\n"
    )
    result = parser.feed_all(chunk)
    assert len(result) == 3
    assert result[0] == '{"type": "delta", "text": "Hello"}'
    assert result[1] == '{"type": "delta", "text": " world"}'
    assert result[2] == "[DONE]"


def test_blank_lines_are_skipped():
    parser = SSESparser()
    chunk = "\n\n\ndata: x\n\n\n\n"
    assert parser.feed_all(chunk) == ["x"]


# =========================================================================
# Fragmented SSE boundaries
# =========================================================================


def test_event_split_across_two_chunks():
    parser = SSESparser()
    results = []
    results.extend(parser.feed('data: {"type":'))
    results.extend(parser.feed(' "text": "split"}\n\n'))
    assert results == ['{"type": "text": "split"}']


def test_done_split_across_chunks():
    parser = SSESparser()
    results = []
    results.extend(parser.feed("data: [D"))
    results.extend(parser.feed("ONE]\n\n"))
    assert results == ["[DONE]"]


def test_newline_split_across_chunks():
    """The newline that terminates an event is in a separate chunk."""
    parser = SSESparser()
    results = []
    results.extend(parser.feed('data: {"type": "a"}'))
    results.extend(parser.feed("\n"))
    results.extend(parser.feed('data: {"type": "b"}\n'))
    results.extend(parser.feed("\n"))
    assert results == [
        '{"type": "a"}',
        '{"type": "b"}',
    ]


# =========================================================================
# Comments
# =========================================================================


def test_comment_lines_are_skipped():
    parser = SSESparser()
    chunk = ": this is a comment\ndata: value\n\n"
    assert parser.feed_all(chunk) == ["value"]


def test_mixed_comments_and_data():
    parser = SSESparser()
    chunk = (
        ": streaming session start\n\n"
        'data: {"event": "first"}\n\n'
        ": mid-stream comment\n\n"
        'data: {"event": "second"}\n\n'
        "data: [DONE]\n\n"
    )
    result = parser.feed_all(chunk)
    assert len(result) == 3
    assert json.loads(result[0])["event"] == "first"
    assert json.loads(result[1])["event"] == "second"
    assert result[2] == "[DONE]"


# =========================================================================
# JSONEventParser
# =========================================================================


def test_json_parser_returns_dicts():
    parser = JSONEventParser()
    results = parser.feed_all('data: {"a": 1}\n\ndata: [DONE]\n\n')
    assert results[0] == {"a": 1}
    assert results[1] == "[DONE]"


def test_json_parser_malformed_data():
    parser = JSONEventParser()
    results = parser.feed_all("data: not-json\n\n")
    # Malformed JSON should yield the raw string, not raise
    assert results[0] == "not-json"


# =========================================================================
# Bytes input
# =========================================================================


def test_bytes_input():
    parser = SSESparser()
    result = parser.feed_all(b'data: {"bytes": true}\n\n')
    assert result == ['{"bytes": true}']


def test_utf8_fragmented_bytes():
    parser = SSESparser()
    results = []
    results.extend(parser.feed(b'data: {"type":'))
    results.extend(parser.feed(b' "text": "unicode"}\n\n'))
    assert results == ['{"type": "text": "unicode"}']

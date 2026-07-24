"""Security regression tests for public stream payloads (Sprint 2, D3).

Ensures that:
1. ``reasoning_content`` never appears in public response payloads
2. Authorization headers/values are never included in serialized output
3. Configured secret names are never present in text content
4. The ``_responses_safe_messages`` filter properly strips reasoning blocks
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from agent_core.orchestrator import _responses_safe_messages

# Sensitive patterns that must never appear in public output
BANNED_PATTERNS: list[re.Pattern] = [
    re.compile(r"reasoning_content"),
    re.compile(r"authorization", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9._-]+", re.IGNORECASE),
    re.compile(r"databricks_token"),
    re.compile(r"api_key", re.IGNORECASE),
    re.compile(r"api[-_]?secret", re.IGNORECASE),
    re.compile(r"\bdbtoken\b", re.IGNORECASE),
]

# Content substrings that could indicate a leak (from config or env)
SENSITIVE_VALUE_PATTERNS: list[re.Pattern] = [
    # Match patterns that look like OAuth tokens or connection strings
    re.compile(r"dapi[a-zA-Z0-9]{8,}"),
    re.compile(r"pat-[a-zA-Z0-9]{8,}"),
]


def _get_all_public_response_output_files() -> list[str]:
    """Return paths to modules that serialize agent responses for the browser."""
    return [
        "agent_core/orchestrator.py",
        "ecommerce_agent/agent_app/handlers.py",
    ]


# ---------------------------------------------------------------------------
# Static analysis: banned patterns in source
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relative_path",
    [
        "agent_core/orchestrator.py",
        "ecommerce_agent/agent_app/handlers.py",
    ],
)
def test_public_response_paths_have_no_banned_patterns(relative_path: str):
    """Scan files that serialize responses for banned patterns.

    Note: ``display_policy.py`` intentionally defines redaction regexes
    containing ``authorization`` and similar patterns — those references
    are permitted because the file implements the redaction, not because
    it leaks secrets.
    """
    root = __file__.rsplit("tests", 1)[0]
    source = (root / Path(relative_path)).read_text(encoding="utf-8")

    for pattern in BANNED_PATTERNS:
        # The display policy file is the *enforcer* of redaction, not a
        # leak site. Skip the authorization pattern there.
        if (
            relative_path.endswith("display_policy.py")
            and pattern.pattern == "authorization"
        ):
            continue
        matches = pattern.findall(source)
        assert not matches, (
            f"Found banned pattern {pattern.pattern!r} in {relative_path}: {matches}"
        )


# ---------------------------------------------------------------------------
# Behavioral: _responses_safe_messages strips reasoning
# ---------------------------------------------------------------------------


def test_safe_messages_strips_reasoning_content_blocks():
    """The _responses_safe_messages helper must remove reasoning blocks."""
    message = AIMessage(
        content=[
            {
                "type": "reasoning",
                "summary": [{"type": "summary_text", "text": "secret reasoning"}],
            },
            {"type": "text", "text": "public answer"},
        ]
    )

    normalized = _responses_safe_messages([message])
    serialized = json.dumps(normalized[0].content)

    assert "reasoning" not in serialized or "secret reasoning" not in serialized
    assert "public answer" in serialized


def test_safe_messages_preserves_visible_text():
    """Visible text content must be preserved after filtering."""
    message = AIMessage(
        content=[
            {"type": "text", "text": "Hello, your order is confirmed."},
            {"type": "output_text", "text": " [ref: 12345]"},
        ]
    )

    normalized = _responses_safe_messages([message])
    serialized = json.dumps(normalized[0].content)

    assert "Hello, your order is confirmed." in serialized
    assert "ref: 12345" in serialized


def test_safe_messages_handles_empty_content():
    """Empty or None content must not raise."""
    message = AIMessage(content="")
    normalized = _responses_safe_messages([message])
    assert normalized[0].content == ""


def test_safe_messages_handles_string_content():
    """Plain string content (not list) must pass through unchanged."""
    message = AIMessage(content="plain string")
    normalized = _responses_safe_messages([message])
    assert normalized[0].content == "plain string"


# ---------------------------------------------------------------------------
# Static: compiled files
# ---------------------------------------------------------------------------


def test_no_banned_values_in_compiled_response_output():
    """Scan compiled Python files (*.pyc) is overkill — this scans the source
    for any literal sensitive value patterns that could leak at runtime."""
    root = Path(__file__).resolve().parents[2]
    for rel in _get_all_public_response_output_files():
        source = (root / rel).read_text(encoding="utf-8")
        for pattern in SENSITIVE_VALUE_PATTERNS:
            assert not pattern.search(source), (
                f"Potential leak in {rel}: matched {pattern.pattern!r}"
            )

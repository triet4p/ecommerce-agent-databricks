"""Payload redaction and size validation for conversation item persistence.

Enforces the "never store" policy defined in S3-A7 before every insert.
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# Keys that MUST be redacted from payloads before persistence
# ---------------------------------------------------------------------------

_EXACT_REDACTED_KEYS = {
    "authorization",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "private_key",
}
_SENSITIVE_KEY_SUFFIXES = (
    "_token",
    "_secret",
    "_password",
    "_api_key",
    "_credential",
    "_key",
)
_JSON_STRING_FIELDS = {"arguments", "output"}

_FORBIDDEN_TOP_LEVEL_FIELDS = {
    "reasoning_content",
    "reasoning",
    "authorization",
    "x-forwarded-user",
    "cookie",
    "mlflow_trace_id",
}

_MAX_PAYLOAD_BYTES = 50_000  # Max serialized payload size in bytes

# ---------------------------------------------------------------------------
# Payload redaction
# ---------------------------------------------------------------------------


def redact_payload(payload: dict[str, Any] | str) -> dict[str, Any]:
    """Remove forbidden fields from a payload dict before persistence.

    Strips:
    - Top-level fields matching ``_FORBIDDEN_TOP_LEVEL_FIELDS``
    - Nested keys matching ``_REDACTED_KEYS_PATTERN``

    Args:
        payload: The raw payload dict, or a JSON string to parse.

    Returns:
        A new dict with forbidden content removed.
    """
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return {"redacted": True, "original_type": "unparseable_string"}

    if not isinstance(payload, dict):
        return {"redacted": True, "original_type": type(payload).__name__}

    return _redact_dict(payload)


def _redact_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact forbidden keys from a dict."""
    result: dict[str, Any] = {}
    for key, value in d.items():
        # Remove forbidden top-level fields
        if key.lower() in _FORBIDDEN_TOP_LEVEL_FIELDS:
            result[key] = "<redacted>"
            continue
        normalized_key = key.casefold()
        # Match explicit credential field names, not arbitrary substrings
        # (for example, ``monkey_type`` is legitimate data).
        if normalized_key in _EXACT_REDACTED_KEYS or normalized_key.endswith(
            _SENSITIVE_KEY_SUFFIXES
        ):
            result[key] = "<redacted>"
            continue
        # Recurse into nested dicts
        if isinstance(value, dict):
            result[key] = _redact_dict(value)
        # Recurse into lists of dicts
        elif isinstance(value, list):
            result[key] = [
                _redact_dict(item) if isinstance(item, dict) else item for item in value
            ]
        elif isinstance(value, str) and normalized_key in _JSON_STRING_FIELDS:
            result[key] = _redact_json_string(value)
        else:
            result[key] = value
    return result


def _redact_json_string(value: str) -> str:
    """Redact a known structured string while preserving the wire shape."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    if isinstance(parsed, dict):
        return json.dumps(
            _redact_dict(parsed), ensure_ascii=False, separators=(",", ":")
        )
    if isinstance(parsed, list):
        return json.dumps(
            [_redact_dict(item) if isinstance(item, dict) else item for item in parsed],
            ensure_ascii=False,
            separators=(",", ":"),
        )
    return value


# ---------------------------------------------------------------------------
# Size validation
# ---------------------------------------------------------------------------


def validate_payload_size(payload: dict[str, Any]) -> bool:
    """Check that the serialized payload does not exceed the maximum size.

    Args:
        payload: The payload dict (already redacted).

    Returns:
        ``True`` if the payload is within limits, ``False`` otherwise.
    """
    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    return len(serialized.encode("utf-8")) <= _MAX_PAYLOAD_BYTES


def compute_payload_size(payload: dict[str, Any]) -> int:
    """Return the UTF-8 byte length of the serialized payload."""
    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    return len(serialized.encode("utf-8"))

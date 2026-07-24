"""Browser-safe tool display policy and thinking-visualization policy.

Every tool call and result that reaches the browser must pass through the
safety layers defined here before rendering.

See Also:
    - ``docs/contracts/chat-ui-event-contract.md`` §4 (Browser-Safe Tool Display Policy)
    - ``docs/contracts/chat-ui-event-contract.md`` §5 (Thinking-Visualization Policy)
"""

from __future__ import annotations

import json
import re

# ---------------------------------------------------------------------------
# Friendly labels for known tools
# ---------------------------------------------------------------------------

_TOOL_LABELS: dict[str, str] = {
    "get_order_status": "\U0001f50d Order lookup",
    "get_customer_order_history": "\U0001f4cb Order history",
    "search_policy_docs": "\U0001f4c4 Policy search",
    "check_refund_eligibility": "\U0001f4b3 Refund check",
    "get_seller_performance": "\U0001f4ca Seller rating",
    "get_shipping_delay_stats": "\U0001f69a Shipping status",
    "compute_delay_severity": "⏱ Delay analysis",
    "customer_value_score": "⭐ Customer value",
    "list_skills": "\U0001f4da Available guides",
    "load_skill": "\U0001f4d6 Load guide",
}

# ---------------------------------------------------------------------------
# Arguments/patterns that MUST be redacted before rendering
# ---------------------------------------------------------------------------

_REDACTED_KEYS_PATTERN = re.compile(
    r"token|secret|password|key|authorization|credential",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Size limits
# ---------------------------------------------------------------------------

_MAX_ARGUMENT_LENGTH = 500
_MAX_OUTPUT_LENGTH = 1000
_MAX_REDACTED_VALUE_LENGTH = 2000

_UNKNOWN_TOOL_LABEL = "\U0001f527 Unknown tool"

# ---------------------------------------------------------------------------
# Phase labels derived from event sequences
# ---------------------------------------------------------------------------


def tool_display_name(name: str) -> str:
    """Return the human-readable label for a tool.

    Falls back to ``\U0001f527 <name>`` for unknown tools.
    """
    return _TOOL_LABELS.get(name, f"\U0001f527 {name}")


def sanitize_arguments(arguments: str) -> str:
    """Truncate and redact tool arguments before browser display.

    Steps:
    1. Truncate to ``_MAX_ARGUMENT_LENGTH`` characters.
    2. Redact keys matching ``_REDACTED_KEYS_PATTERN``.
    3. Redact values exceeding ``_MAX_REDACTED_VALUE_LENGTH``.
    """
    if len(arguments) > _MAX_ARGUMENT_LENGTH:
        arguments = arguments[:_MAX_ARGUMENT_LENGTH] + "…"

    try:
        parsed = json.loads(arguments)
    except (json.JSONDecodeError, TypeError):
        return arguments

    if not isinstance(parsed, dict):
        return arguments

    redacted = {}
    for key, value in parsed.items():
        if _REDACTED_KEYS_PATTERN.search(key):
            redacted[key] = "<redacted>"
        elif isinstance(value, str) and len(value) > _MAX_REDACTED_VALUE_LENGTH:
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value

    return json.dumps(redacted, ensure_ascii=False)


def sanitize_output(output: str) -> str:
    """Truncate tool output before browser display."""
    if len(output) > _MAX_OUTPUT_LENGTH:
        return output[:_MAX_OUTPUT_LENGTH] + "…"
    return output


# ---------------------------------------------------------------------------
# Phase label derivation from event type
# ---------------------------------------------------------------------------

# Phase labels — derived from event type, never from raw model output.
_PHASE_LABELS: dict[str, str] = {
    "text_delta_no_tool": "\U0001f916 Composing…",
    "text_delta_before_tool": "\U0001f50d Analyzing…",
    "function_call_emitted": "\U0001f527 Running tool…",
    "function_call_output": "✅ Tool complete",
    "multi_step": "\U0001f504 Multi-step…",
    "error": "❌ Error",
    "idle": "⏳ Still working…",
}


def derive_phase_label(
    *,
    has_text_delta: bool = False,
    has_pending_tool_call: bool = False,
    has_tool_result: bool = False,
    is_multi_step: bool = False,
    is_error: bool = False,
) -> str:
    """Derive a safe display label from observed event types.

    Args:
        has_text_delta: Whether text deltas have been observed in this turn.
        has_pending_tool_call: Whether an unmatched tool call is pending.
        has_tool_result: Whether a tool result has been received.
        is_multi_step: Whether multiple tool calls have been observed.
        is_error: Whether an error event terminated the stream.

    Returns:
        A safe display label (never raw reasoning text).
    """
    if is_error:
        return _PHASE_LABELS["error"]
    if is_multi_step:
        return _PHASE_LABELS["multi_step"]
    if has_pending_tool_call:
        return _PHASE_LABELS["function_call_emitted"]
    if has_tool_result:
        return _PHASE_LABELS["function_call_output"]
    if has_text_delta:
        return _PHASE_LABELS["text_delta_no_tool"]
    return _PHASE_LABELS["text_delta_before_tool"]

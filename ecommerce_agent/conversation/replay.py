"""History replay — convert persisted canonical items into Responses API input.

This module reconstructs the complete bounded history from stored items
and appends the new user message for the next agent invocation.
"""

from __future__ import annotations

import json
from typing import Any

from .models import ConversationItem

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_REQUEST_CHARACTERS = 100_000  # Agent App safety limit

# ---------------------------------------------------------------------------
# Item conversion
# ---------------------------------------------------------------------------


def _convert_message_item(item: ConversationItem) -> dict[str, Any] | None:
    """Convert a stored ``message`` item to a Responses API input item.

    Returns ``None`` if the payload cannot be converted.
    The Responses Agent expects ``content`` as a list of content blocks
    with ``type`` and ``text`` fields — identical format to the initial
    (non-replay) request sent by the Chat UI.
    """
    payload = item.payload
    role = payload.role or item.role or "assistant"
    content = payload.content or []

    # Extract text from content blocks
    texts: list[str] = []
    for block in content:
        if isinstance(block, dict):
            block_type = block.get("type", "")
            if block_type in ("output_text", "input_text", "text"):
                t = block.get("text", "")
                if t:
                    texts.append(t)

    # Fallback: try to extract text directly from payload
    if not texts:
        t = getattr(payload, "text", None)
        if t:
            texts.append(t)

    if not texts:
        return None

    combined = "\n".join(texts)

    # Skip messages that are raw JSON echoes of tool results (starts with
    # `{` or `[`).  The agent emits these as a separate response.output_item
    # before the natural-language answer, and replaying them would break the
    # Responses API's role-alternation requirement.
    stripped = combined.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return None

    return {
        "role": role,
        "content": [{"type": "input_text", "text": combined}],
    }


def _convert_function_call_item(item: ConversationItem) -> dict[str, Any] | None:
    """Convert a stored ``function_call`` item to a tool call input block."""
    payload = item.payload
    call_id = payload.call_id or item.id
    name = payload.name or "unknown_tool"
    arguments = payload.arguments or "{}"

    return {
        "type": "function_call",
        "role": "assistant",
        "content": "",  # required by ResponsesAgentRequest schema
        "tool_calls": [
            {
                "id": str(call_id),
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": arguments,
                },
            }
        ],
    }


def _convert_function_call_output_item(item: ConversationItem) -> dict[str, Any] | None:
    """Convert a stored ``function_call_output`` item to a tool result block."""
    payload = item.payload
    call_id = payload.call_id or item.item_key or ""
    output = payload.output or ""

    return {
        "type": "function_call_output",
        "role": "assistant",
        "call_id": str(call_id),
        "content": output,
    }


# ---------------------------------------------------------------------------
# D1: Convert persisted items to Responses API input
# ---------------------------------------------------------------------------


def convert_items_to_input_history(
    items: list[ConversationItem],
) -> list[dict[str, Any]]:
    """Convert a list of stored ``ConversationItem``s into Responses API input
    items.

    Only items from completed turns should be passed here (see
    ``ConversationRepository.get_replay_items()``).

    Args:
        items: Ordered list of ConversationItems to convert.

    Returns:
        A list of input dicts suitable for the Responses API ``input`` field.
    """
    input_history: list[dict[str, Any]] = []

    for item in items:
        converted: dict[str, Any] | None = None

        if item.item_type == "message":
            converted = _convert_message_item(item)
        # Skip function_call and function_call_output items — the
        # ResponsesAgent may reject replayed tool results because it
        # cannot find the corresponding pending function call.  The
        # assistant message already contains the tool output in text
        # form, so the agent has enough context from messages alone.
        # elif item.item_type == "function_call":
        #     converted = _convert_function_call_item(item)
        # elif item.item_type == "function_call_output":
        #     converted = _convert_function_call_output_item(item)

        if converted is not None:
            input_history.append(converted)

    return input_history


# ---------------------------------------------------------------------------
# D2: Append the new user item after prior history
# ---------------------------------------------------------------------------


def append_user_message(
    input_history: list[dict[str, Any]],
    user_message: str,
) -> list[dict[str, Any]]:
    """Append the new user message after the prior completed history.

    Args:
        input_history: The converted history from prior turns.
        user_message: The new user message text.

    Returns:
        The complete input list with the new user message appended.
    """
    input_history.append({
        "role": "user",
        "content": [{"type": "input_text", "text": user_message}],
    })
    return input_history


# ---------------------------------------------------------------------------
# D3: Compute serialized request size
# ---------------------------------------------------------------------------


def compute_request_size(input_items: list[dict[str, Any]]) -> int:
    """Compute the character length of the serialized request.

    Uses the same semantics as the Agent App's 100,000-character safety
    check: the JSON-serialized ``input`` list length in characters.
    """
    serialized = json.dumps(input_items, ensure_ascii=False, default=str)
    return len(serialized)


# ---------------------------------------------------------------------------
# D4: Reject over-budget requests
# ---------------------------------------------------------------------------


def check_request_budget(
    input_items: list[dict[str, Any]],
    max_chars: int = _MAX_REQUEST_CHARACTERS,
) -> tuple[bool, int]:
    """Check whether the serialized request fits within the character budget.

    Args:
        input_items: The Responses API input items.
        max_chars: Maximum allowed characters (default 100,000).

    Returns:
        A tuple of ``(within_budget, character_count)``.
    """
    size = compute_request_size(input_items)
    return size <= max_chars, size


# ---------------------------------------------------------------------------
# D5: Accumulate stream events and build completed output
# ---------------------------------------------------------------------------
# This is used by the Chat UI to collect Sprint 2 stream events and commit
# only canonical completed output items after terminal success.

# Event type markers from the Sprint 2 contract
_OUTPUT_ITEM_DONE = "response.output_item.done"
_RESPONSE_COMPLETED = "response.completed"
_ERROR = "error"


def accumulate_output_items(
    stream_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Accumulate canonical output items from a stream of SSE events.

    Collects the ``item`` from every ``response.output_item.done`` event
    and groups them into a response output list.

    Args:
        stream_events: The full list of parsed SSE events from the Agent App
            stream.

    Returns:
        A list of output item dicts suitable for persisting via
        ``ConversationRepository.complete_turn()``. Returns an empty list
        if the stream contained an ``error`` event before any
        ``response.completed`` event.
    """
    output_items: list[dict[str, Any]] = []
    had_error = False

    for event in stream_events:
        event_type = event.get("type", "")

        if event_type == _ERROR:
            had_error = True
            break

        if event_type == _OUTPUT_ITEM_DONE:
            item = event.get("item")
            if isinstance(item, dict):
                output_items.append(item)

        # Stop collecting at response.completed
        if event_type == _RESPONSE_COMPLETED:
            break

    if had_error:
        return []

    return output_items


# ---------------------------------------------------------------------------
# Public convenience: full replay pipeline
# ---------------------------------------------------------------------------


def build_replay_request(
    history_items: list[ConversationItem],
    user_message: str,
    max_chars: int = _MAX_REQUEST_CHARACTERS,
) -> tuple[list[dict[str, Any]] | None, int]:
    """Build a complete bounded history request for the Agent App.

    Args:
        history_items: Completed items from ``get_replay_items()``.
        user_message: The new user message.
        max_chars: Maximum allowed character budget.

    Returns:
        A tuple of ``(input_items, character_count)`` where ``input_items``
        is ``None`` if the request exceeds the budget.
    """
    input_history = convert_items_to_input_history(history_items)
    full_input = append_user_message(input_history, user_message)
    within_budget, size = check_request_budget(full_input, max_chars)

    if not within_budget:
        return None, size

    return full_input, size

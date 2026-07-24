"""Typed internal representation for Chat UI stream events.

This module defines Pydantic models for every SSE event type that the Chat UI
can receive from the Agent App. These models are the single source of truth for
stream parsing — every SSE ``data:`` line is validated against one of these
types before being passed to the UI rendering layer.

See Also:
    - ``docs/contracts/chat-ui-event-contract.md`` for the full wire specification.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Text delta — incremental assistant text chunk
# ---------------------------------------------------------------------------


class TextDeltaEvent(BaseModel):
    """One chunk of incremental assistant text."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["response.output_text.delta"] = "response.output_text.delta"
    item_id: str
    delta: str
    content_index: int = 0
    output_index: int = 0


# ---------------------------------------------------------------------------
# Output items carried by ``response.output_item.done``
# ---------------------------------------------------------------------------


class TextMessageItem(BaseModel):
    """A completed assistant text output item."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["message"] = "message"
    id: str
    role: str = "assistant"
    status: str = "completed"
    content: list[dict[str, Any]] = []

    @property
    def text(self) -> str:
        """Aggregate all ``output_text`` blocks into a single string."""
        return "".join(
            block.get("text", "")
            for block in self.content
            if isinstance(block, dict) and block.get("type") == "output_text"
        )


class FunctionCallItem(BaseModel):
    """A completed function/tool call output item."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["function_call"] = "function_call"
    id: str
    call_id: str
    name: str
    arguments: str


class FunctionCallOutputItem(BaseModel):
    """A completed function/tool result output item."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["function_call_output"] = "function_call_output"
    call_id: str
    output: str


# ---------------------------------------------------------------------------
# ``response.output_item.done`` — discriminated union over item types
# ---------------------------------------------------------------------------


class OutputItemDoneEvent(BaseModel):
    """Signals completion of a single output item (text, tool call, or result)."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["response.output_item.done"] = "response.output_item.done"
    item: TextMessageItem | FunctionCallItem | FunctionCallOutputItem
    output_index: int = 0


# ---------------------------------------------------------------------------
# Error event
# ---------------------------------------------------------------------------


class ErrorEvent(BaseModel):
    """Terminal error that ended the stream."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["error"] = "error"
    code: str | None = None
    message: str = ""


# ---------------------------------------------------------------------------
# Response completed event
# ---------------------------------------------------------------------------


class ResponseCompletedEvent(BaseModel):
    """Signals the response completed successfully."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["response.completed"] = "response.completed"
    response: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Union of all supported events
# ---------------------------------------------------------------------------

ChatUIStreamEvent = (
    TextDeltaEvent | OutputItemDoneEvent | ErrorEvent | ResponseCompletedEvent
)


def parse_stream_event(data: dict[str, Any]) -> ChatUIStreamEvent | None:
    """Parse a single SSE ``data:`` JSON object into a typed event.

    Args:
        data: The parsed JSON object from an SSE ``data:`` line.

    Returns:
        A typed event model, or ``None`` if the event type is not recognised
        (unsupported types are silently ignored per contract).

    Raises:
        ValueError: If the payload declares a recognised type but fails
            validation.
    """
    event_type = data.get("type")
    if event_type == "response.output_text.delta":
        return TextDeltaEvent(**data)
    elif event_type == "response.output_item.done":
        return OutputItemDoneEvent(**data)
    elif event_type == "error":
        return ErrorEvent(**data)
    elif event_type == "response.completed":
        return ResponseCompletedEvent(**data)
    # Unrecognised types are silently ignored (contract §2 preamble).
    return None

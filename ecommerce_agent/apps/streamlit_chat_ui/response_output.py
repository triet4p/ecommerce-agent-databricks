"""Extract visible assistant text from an MLflow Responses API response."""

from typing import Any


def extract_response_text(payload: dict[str, Any]) -> str:
    """Return the final assistant message, not an intermediate function call."""
    output = payload.get("output")
    if not isinstance(output, list):
        raise ValueError("Agent response is missing an output list")

    for item in reversed(output):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        texts: list[str] = []
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                texts.append(content["text"])
        if texts:
            return "\n".join(texts)
    raise ValueError("Agent response contained no final assistant message")

"""MLflow Responses API adapter for the isolated DeepSeek serving boundary."""

from __future__ import annotations

import json
from typing import Any, Generator
from uuid import uuid4

from langchain.chat_models import init_chat_model
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)

DEFAULT_MAX_OUTPUT_TOKENS = 1500


def _text(content: Any) -> str:
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


def responses_to_deepseek_messages(items: list[Any]) -> list[dict[str, Any]]:
    """Reconstruct provider messages, preserving reasoning and tool-call order."""
    messages: list[dict[str, Any]] = []
    reasoning: list[str] = []
    calls: dict[str, dict[str, Any]] = {}

    def flush_calls() -> None:
        if not calls:
            return
        message: dict[str, Any] = {
            "role": "assistant",
            "content": None,
            "tool_calls": list(calls.values()),
        }
        if reasoning:
            message["reasoning_content"] = "".join(reasoning)
        messages.append(message)
        reasoning.clear()
        calls.clear()

    for item in items:
        data = (
            item.model_dump(exclude_none=True)
            if hasattr(item, "model_dump")
            else dict(item)
        )
        kind = data.get("type")
        if kind == "reasoning":
            reasoning.extend(
                part.get("text", "")
                for part in data.get("summary", [])
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            )
        elif kind == "function_call":
            call_id = data["call_id"]
            calls[call_id] = {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": data["name"],
                    "arguments": data.get("arguments") or "{}",
                },
            }
        elif kind == "function_call_output":
            flush_calls()
            output = data.get("output", "")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": data["call_id"],
                    "content": output
                    if isinstance(output, str)
                    else json.dumps(output),
                }
            )
        elif kind == "message":
            flush_calls()
            message = {"role": data["role"], "content": _text(data.get("content"))}
            if data["role"] == "assistant" and reasoning:
                message["reasoning_content"] = "".join(reasoning)
                reasoning.clear()
            messages.append(message)
    flush_calls()
    return messages


def normalize_function_tools(tools: list[Any] | None) -> list[dict[str, Any]]:
    """Convert Responses function tools to the provider's OpenAI-compatible form."""
    converted = []
    for tool in tools or []:
        data = (
            tool.model_dump(exclude_none=True)
            if hasattr(tool, "model_dump")
            else dict(tool)
        )
        if data.get("type") != "function":
            raise ValueError(f"Unsupported tool type: {data.get('type')!r}")
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": data["name"],
                    "description": data.get("description", ""),
                    "parameters": data.get("parameters", {"type": "object"}),
                },
            }
        )
    return converted


class DeepSeekResponsesAgent(ResponsesAgent):
    """Thinking-mode adapter. `tool_choice` is rejected by provider contract."""

    def __init__(
        self, model_name: str, *, max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    ) -> None:
        self.model_name = model_name
        if max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        self.max_output_tokens = max_output_tokens
        self._chat_model = None

    def _model(self):
        if self._chat_model is None:
            self._chat_model = init_chat_model(
                model=self.model_name,
                model_provider="deepseek",
                max_retries=6,
                timeout=120,
                max_tokens=self.max_output_tokens,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}},
            )
        return self._chat_model

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        return ResponsesAgentResponse(
            output=[
                event.item
                for event in self.predict_stream(request)
                if event.type == "response.output_item.done"
            ],
            custom_outputs=request.custom_inputs,
        )

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        tools = normalize_function_tools(request.tools)
        if tools and request.tool_choice is not None:
            raise ValueError(
                "DeepSeek V4 thinking mode rejects tool_choice; bind tools without it."
            )
        model = self._model()
        if tools:
            model = model.bind_tools(
                tools,
                **(
                    {"parallel_tool_calls": request.parallel_tool_calls}
                    if request.parallel_tool_calls is not None
                    else {}
                ),
            )
        item_id, full, text_parts, reasoning = f"msg_{uuid4().hex}", None, [], []
        for chunk in model.stream(responses_to_deepseek_messages(request.input)):
            full = chunk if full is None else full + chunk
            if isinstance(chunk.additional_kwargs.get("reasoning_content"), str):
                reasoning.append(chunk.additional_kwargs["reasoning_content"])
            text = _text(chunk.content)
            if text:
                text_parts.append(text)
                yield ResponsesAgentStreamEvent(
                    **self.create_text_delta(delta=text, item_id=item_id)
                )
        if full is None:
            raise RuntimeError("DeepSeek returned no stream chunks.")
        if reasoning:
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=self.create_reasoning_item(
                    id=f"rs_{uuid4().hex}", reasoning_text="".join(reasoning)
                ),
            )
        if text_parts:
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=self.create_text_output_item(text="".join(text_parts), id=item_id),
            )
        for call in full.tool_calls:
            call_id = call.get("id") or f"call_{uuid4().hex}"
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=self.create_function_call_item(
                    id=f"fc_{call_id}"[:64],
                    call_id=call_id,
                    name=call["name"],
                    arguments=json.dumps(call["args"]),
                ),
            )
        if not text_parts and not full.tool_calls:
            raise RuntimeError("DeepSeek returned neither answer text nor tool calls.")

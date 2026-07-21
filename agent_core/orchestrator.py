"""
agent_core.orchestrator
-------------------------
Project-agnostic agent builder that constructs a LangChain ``create_agent`` with
``ChatDatabricks``, resolves tools from config, and wraps everything in an
MLflow ``ResponsesAgent`` for deployment on Databricks Apps.

Usage::

    config = load_config("config.yaml")
    agent = build_agent(config, registry=my_registry)
    response = agent.predict(request)
"""

from __future__ import annotations

import logging
import json
import asyncio
import concurrent.futures
from typing import Any, Generator
from uuid import uuid4

from databricks_langchain import ChatDatabricks
from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk
from langchain_core.tools import StructuredTool
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    output_to_responses_items_stream,
    to_chat_completions_input,
)

from agent_core.config_schema import AgentConfig
from agent_core.config_loader import resolve_paths
from agent_core.prompt_registry import resolve_system_prompt
from agent_core.skill_interface import SkillLibrary, build_skill_tools, render_rules
from agent_core.tool_interface import ToolRegistry, build_tools
from agent_core.tool_policy import (
    OperationGate,
    build_default_policy,
    validate_required_arguments,
)

logger = logging.getLogger(__name__)

# Application-level safety envelope used when an endpoint cannot enable AI
# Gateway rate or token controls. The character cap bounds caller-supplied
# history, while the graph limit bounds repeated model/tool turns. Model output
# is independently bounded by ``LLMConfig.max_tokens``.
MAX_REQUEST_INPUT_CHARACTERS = 100_000
MAX_AGENT_GRAPH_STEPS = 12


def _await_tool_invocation(awaitable: Any) -> Any:
    """Resolve an async tool invocation from the synchronous LangGraph path."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    # ``predict_stream`` is normally synchronous, but an embedding host may
    # already own an event loop. Avoid nesting ``asyncio.run`` in that loop.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, awaitable).result()


def _make_sync_tool_adapters(tools: list[Any]) -> list[Any]:
    """Adapt async-only managed-MCP tools for LangGraph's sync stream API."""
    adapted: list[Any] = []
    for tool in tools:
        if getattr(tool, "func", object()) is not None or not callable(
            getattr(tool, "ainvoke", None)
        ):
            adapted.append(tool)
            continue

        def invoke_async_tool(*, _tool: Any = tool, **kwargs: Any) -> Any:
            return _await_tool_invocation(_tool.ainvoke(kwargs))

        adapted.append(
            StructuredTool.from_function(
                func=invoke_async_tool,
                name=tool.name,
                description=tool.description,
                args_schema=tool.args_schema,
            )
        )
    return adapted


def _safe_string(value: Any) -> str:
    """Convert an arbitrary value to a string for safe concatenation.

    The DeepSeek Responses API may return ``text`` fields as strings or as
    lists (e.g. ``["Hello"]``).  Normalise to a string regardless.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(str(v) for v in value)
    return str(value)


def _responses_safe_messages(messages: list[Any]) -> list[Any]:
    """Adapt Responses-style LangChain content blocks for MLflow 3.14 output.

    ``output_to_responses_items_stream`` accepts LangChain messages but assumes
    AI content is a string. ChatDatabricks Responses API instead returns a list
    containing reasoning and text blocks. Normalize only the copy serialized to
    the client: the original graph message, including reasoning/tool calls,
    remains intact for provider round-trips.
    """
    normalized: list[Any] = []
    for message in messages:
        content = getattr(message, "content", None)
        if not isinstance(content, list) or not hasattr(message, "model_copy"):
            normalized.append(message)
            continue
        visible_text = "".join(
            _safe_string(block.get("text"))
            for block in content
            if isinstance(block, dict) and block.get("type") in {"text", "output_text"}
        )
        normalized.append(message.model_copy(update={"content": visible_text}))
    return normalized


# ---------------------------------------------------------------------------
# Text streaming helpers (Sprint 2 — dual stream-mode support)
# ---------------------------------------------------------------------------


class _TextAggregator:
    """Track text chunks from ``messages`` stream mode for deduplication.

    When dual stream mode is active, text content arrives both as incremental
    chunks (``messages`` mode → ``AIMessageChunk``) and as completed messages
    (``updates`` mode → ``AIMessage``). This class tracks which message IDs
    have been streamed as deltas so the completed item from the updates path
    can be suppressed and replaced with a single aggregated done event.
    """

    def __init__(self) -> None:
        self._buffers: dict[str, str] = {}
        self._streamed_ids: set[str] = set()

    def record_chunk(self, chunk: AIMessageChunk) -> str | None:
        """Accumulate text content from a message chunk.

        Returns:
            The item_id for the chunk, or ``None`` if the chunk had no text.
        """
        msg_id = getattr(chunk, "id", None) or str(uuid4())
        content = getattr(chunk, "content", None)
        if not content:
            return None
        # The Responses API may return content as a list of blocks.
        # Extract only visible text to avoid accumulating reasoning content.
        if isinstance(content, list):
            text_parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") in {
                    "text",
                    "output_text",
                }:
                    text_parts.append(_safe_string(block.get("text", "")))
            safe_text = "".join(text_parts) if text_parts else ""
        else:
            safe_text = _safe_string(content)
        if not safe_text:
            return None
        self._buffers.setdefault(msg_id, "")
        self._buffers[msg_id] += safe_text
        return msg_id

    def mark_streamed(self, msg_id: str) -> None:
        """Record that this message ID was fully streamed as text deltas."""
        self._streamed_ids.add(msg_id)

    def was_streamed(self, msg_id: str) -> bool:
        """Return ``True`` if this message ID was already streamed as deltas."""
        return msg_id in self._streamed_ids

    def flush_done_events(
        self,
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """Yield ``response.output_item.done`` events for accumulated text."""
        from mlflow.types.responses import (
            ResponsesAgentStreamEvent,
            create_text_output_item,
        )

        for msg_id, text in self._buffers.items():
            if msg_id not in self._streamed_ids:
                continue
            item = create_text_output_item(text, id=msg_id)
            yield ResponsesAgentStreamEvent(type="response.output_item.done", item=item)


def _message_chunk_to_delta_events(
    chunk: AIMessageChunk,
    metadata: dict[str, Any],  # noqa: ARG001  — kept for future extensibility
    aggregator: _TextAggregator | None = None,
) -> Generator[ResponsesAgentStreamEvent, None, None]:
    """Convert an ``AIMessageChunk`` into ``response.output_text.delta`` events.

    Args:
        chunk: Message chunk from LangGraph's ``messages`` stream mode.
        metadata: Metadata dict (``langgraph_node``, ``langgraph_step``, …).
        aggregator: Optional aggregator for deduplication tracking.

    Yields:
        ``ResponsesAgentStreamEvent`` objects of type ``response.output_text.delta``.
    """
    from mlflow.types.responses import (
        ResponsesAgentStreamEvent,
        create_text_delta,
    )

    content = getattr(chunk, "content", None)
    if not content:
        return

    # Responses API may return content as a list of blocks (text, reasoning, …).
    # Extract only visible text blocks to avoid leaking reasoning content.
    if isinstance(content, list):
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") in {"text", "output_text"}:
                text_parts.append(_safe_string(block.get("text", "")))
        if not text_parts:
            return  # Nothing visible — skip this chunk entirely.
        visible = "".join(text_parts)
    else:
        visible = _safe_string(content)

    msg_id = getattr(chunk, "id", None) or str(uuid4())

    if aggregator is not None:
        aggregator.record_chunk(chunk)
        aggregator.mark_streamed(msg_id)

    if visible:
        yield ResponsesAgentStreamEvent(**create_text_delta(visible, item_id=msg_id))


def _deduplicate_stream_events(
    stream_events: Generator[ResponsesAgentStreamEvent, None, None],
    aggregator: _TextAggregator,
) -> Generator[ResponsesAgentStreamEvent, None, None]:
    """Suppress completed text items that were already streamed as deltas.

    Passes through non-message events and raw strings (used by test stubs)
    without filtering.
    """
    for event in stream_events:
        # Test stubs may inject raw strings instead of stream events.
        if isinstance(event, str):
            yield event
            continue
        if getattr(event, "type", None) == "response.output_item.done":
            item = getattr(event, "item", None) or {}
            if isinstance(item, dict) and item.get("type") == "message":
                item_id = item.get("id", "")
                if aggregator.was_streamed(item_id):
                    continue  # Already emitted as text deltas
        yield event


def _build_graph(
    config: AgentConfig,
    registry: ToolRegistry | None = None,
    tools: list | None = None,
    uc_function_client: Any | None = None,
):
    """Construct the LangChain agent graph from config.

    * Creates ``ChatDatabricks(use_responses_api=True)`` as the model.
    * Resolves local, serving-endpoint, and MCP-discovered tools.
    * Loads rules and skills from the configured paths.

    Args:
        config: Agent config.
        registry: Optional tool registry.
        tools: Optional pre-built tool list. If provided, skips
            ``build_tools`` and uses these directly.
    """
    if registry is None:
        registry = ToolRegistry()

    # --- Model ---
    llm = ChatDatabricks(
        endpoint=config.llm.endpoint_name,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
        use_responses_api=True,
    )

    # --- Tools ---
    if tools is not None:
        # Pre-built tools provided (e.g. from CoreAgent).
        all_tools = list(tools)
    else:
        all_tools = build_tools(
            config,
            registry,
            uc_function_client=uc_function_client,
        )

    # --- System prompt with rules ---
    system_prompt = resolve_system_prompt(config)
    if config.rules is not None and config.rules.paths:
        resolved_paths = resolve_paths(config.rules.paths, config)
        rules_text = render_rules(resolved_paths)
        if rules_text:
            system_prompt = f"{system_prompt}\n\n{rules_text}"

    # --- Skill tools (progressive disclosure) ---
    if config.skills is not None:
        library = SkillLibrary(config.skills)
        all_tools = all_tools + build_skill_tools(library)

    return create_agent(model=llm, tools=all_tools, system_prompt=system_prompt)


class CoreAgent(ResponsesAgent):
    """MLflow ResponsesAgent wrapping the LangChain agent.

    This is the production contract used by MLflow ``AgentServer`` on
    Databricks Apps.

    Supports tool-selection policy enforcement via ``OperationGate``:
    before prediction, required tools are identified; after prediction,
    the gate verifies that all required tools were invoked.
    """

    def __init__(
        self,
        config: AgentConfig,
        registry: ToolRegistry | None = None,
        *,
        uc_function_client: Any | None = None,
    ):
        self.config = config
        self.registry = registry
        # Build tools once: store for the OperationGate and pass to the graph.
        if registry is None:
            registry = ToolRegistry()
        self._tools = _make_sync_tool_adapters(
            build_tools(
                config,
                registry,
                uc_function_client=uc_function_client,
            )
        )

        self.graph = _build_graph(
            config,
            registry=registry,
            tools=self._tools,
            uc_function_client=uc_function_client,
        )
        # The policy marks known required business operations explicitly; a Fat
        # Module may replace individual policies for its own domain.
        self._operation_gate = build_default_policy(self._tools)
        self._tools_by_name = {tool.name: tool for tool in self._tools}
        # Track pending tool results for OperationGate (call_id -> tool_name).
        self._pending_tool_results: dict[str, str] = {}

    @property
    def operation_gate(self) -> OperationGate:
        """Access the agent's OperationGate for tool-selection policy."""
        return self._operation_gate

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        # Built from predict_stream to guarantee identical behavior.
        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(
            id=str(uuid4()),
            output=outputs,
            custom_outputs=request.custom_inputs,
        )

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        thread_id = str(uuid4())

        input_items = [item.model_dump() for item in request.input]
        input_characters = len(json.dumps(input_items, ensure_ascii=False, default=str))
        if input_characters > MAX_REQUEST_INPUT_CHARACTERS:
            raise ValueError(
                "Agent input exceeds the application safety limit of "
                f"{MAX_REQUEST_INPUT_CHARACTERS} characters"
            )

        # Request-local state is essential: this singleton is shared by every
        # concurrent App request. The instance gate is a policy template only.
        operation_gate = OperationGate(policies=dict(self._operation_gate.policies))
        pending_tool_results: dict[str, str] = {}
        workflow_context = self._run_required_workflow(request, gate=operation_gate)
        cc_msgs = to_chat_completions_input(input_items)
        if workflow_context is not None:
            cc_msgs.append({"role": "system", "content": workflow_context})

        # Until C11 adds intent-to-workflow routing, only deployments that
        # actually configure a required operation need completion buffering.
        # Optional/read-only tool requests must preserve real-time SSE output.
        buffer_until_verified = bool(operation_gate.report_unsatisfied())
        buffered_events: list[ResponsesAgentStreamEvent] = []

        # Sprint 2: dual stream-mode — "messages" for token-level text deltas,
        # "updates" for node-level completed items (tool calls, results).
        text_aggregator = _TextAggregator()

        # Track whether an error was emitted to prevent synthesizing a
        # completion event after it (S2-B9).
        _error_emitted = False

        try:
            for mode, data in self.graph.stream(
                {"messages": cc_msgs},
                config={
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": MAX_AGENT_GRAPH_STEPS,
                },
                stream_mode=["updates", "messages"],
            ):
                if mode == "messages":
                    # Token-level chunks from the streaming LLM.
                    msg_chunk, metadata = data
                    for event in _message_chunk_to_delta_events(
                        msg_chunk,
                        metadata,
                        aggregator=text_aggregator,
                    ):
                        if buffer_until_verified:
                            buffered_events.append(event)
                        else:
                            yield event

                elif mode == "updates":
                    # Node-level completed items.
                    for node_data in data.values():
                        messages = node_data.get("messages", [])
                        for msg in messages:
                            # Track tool calls for OperationGate
                            self._track_tool_calls(
                                msg,
                                gate=operation_gate,
                                pending_tool_results=pending_tool_results,
                            )
                        stream_events = output_to_responses_items_stream(
                            _responses_safe_messages(messages)
                        )
                        # Deduplicate text items already streamed as deltas.
                        deduped = _deduplicate_stream_events(
                            stream_events, text_aggregator
                        )
                        if buffer_until_verified:
                            buffered_events.extend(deduped)
                        else:
                            yield from deduped

        except Exception as exc:
            # S2-B9: Catch upstream errors and yield an error event instead of
            # synthesizing a completion.
            logger.warning("Streaming error: %s", exc)
            error_event = ResponsesAgentStreamEvent(
                type="error",
                code="INTERNAL_ERROR",
                message=str(exc),
            )
            if buffer_until_verified:
                buffered_events.append(error_event)
            else:
                yield error_event
            _error_emitted = True

        # S2-B9: Do not emit aggregated events or gate verification after an
        # error. The client receives the error and must not see a completion.
        if not _error_emitted:
            # Emit aggregated text-output done events for streamed content.
            for event in text_aggregator.flush_done_events():
                if buffer_until_verified:
                    buffered_events.append(event)
                else:
                    yield event

            # Verify required tools after streaming completes.
            self._verify_required_operations(gate=operation_gate)

        if buffer_until_verified:
            yield from buffered_events

    def _run_required_workflow(
        self,
        request: ResponsesAgentRequest,
        *,
        gate: OperationGate | None = None,
    ) -> str | None:
        """Execute an explicitly routed required operation before model generation.

        Callers opt in through ``custom_inputs.required_operation`` with a
        mapping containing ``tool_name`` and ``arguments``. This contract is
        deterministic: the model cannot omit, rename, or alter the operation.
        """
        custom_inputs = getattr(request, "custom_inputs", None) or {}
        operation = custom_inputs.get("required_operation")
        if operation is None:
            return None
        if not isinstance(operation, dict):
            raise ValueError("custom_inputs.required_operation must be an object")

        tool_name = operation.get("tool_name")
        arguments = operation.get("arguments")
        if not isinstance(tool_name, str) or not tool_name:
            raise ValueError("required_operation.tool_name must be a non-empty string")
        if not isinstance(arguments, dict):
            raise ValueError("required_operation.arguments must be an object")

        tool = self._tools_by_name.get(tool_name)
        if tool is None:
            raise ValueError(
                f"Required workflow references unavailable tool '{tool_name}'"
            )

        gate = gate or self._operation_gate
        gate.require_tool(tool_name)
        validate_required_arguments(tool, arguments)
        call_id = f"workflow-{uuid4()}"
        gate.validate_and_track(tool_name, arguments, call_id=call_id)
        result = self._invoke_required_tool(tool, arguments)
        gate.validate_and_track(
            tool_name,
            {},
            tool_result=result,
            call_id=call_id,
        )
        return (
            "A deterministic required workflow has already run. Use this typed "
            f"result when responding; do not claim a different outcome. Tool: {tool_name}. "
            f"Result: {json.dumps(result, ensure_ascii=False, default=str)}"
        )

    def _invoke_required_tool(self, tool: Any, arguments: dict[str, Any]) -> Any:
        """Run a required workflow through sync or async LangChain tool contracts.

        Managed MCP discovery returns async-only ``StructuredTool`` instances.
        The deterministic gate remains synchronous at its public boundary, so
        bridge only that async invocation instead of treating the tool as
        unavailable or silently skipping the required operation.
        """
        try:
            return tool.invoke(arguments)
        except NotImplementedError:
            async_invoke = getattr(tool, "ainvoke", None)
            if async_invoke is None:
                raise
            return _await_tool_invocation(async_invoke(arguments))

    def _track_tool_calls(
        self,
        msg: Any,
        *,
        gate: OperationGate | None = None,
        pending_tool_results: dict[str, str] | None = None,
    ) -> None:
        """Track tool calls and results in the OperationGate.

        Reads from LangChain standard ``AIMessage.tool_calls`` (List[ToolCall])
        and ``ToolMessage`` (which carries tool results by ``tool_call_id``).

        A required tool is only marked satisfied when both:
        1. The tool call was observed (via AIMessage.tool_calls).
        2. The tool result was observed (via ToolMessage with matching id).
        """
        gate = gate or self._operation_gate
        pending_tool_results = (
            self._pending_tool_results
            if pending_tool_results is None
            else pending_tool_results
        )
        # Track tool CALLS from AIMessage.tool_calls (standard attribute).
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                tool_name = tc.get("name", "") if isinstance(tc, dict) else tc.name
                args = tc.get("args", {}) if isinstance(tc, dict) else tc.args
                call_id = tc.get("id", "") if isinstance(tc, dict) else tc.id
                tool = self._tools_by_name.get(tool_name)
                if tool is not None:
                    validate_required_arguments(tool, dict(args))
                # Validate the call but do not satisfy it until its correlated
                # ToolMessage is observed.
                gate.validate_and_track(
                    tool_name, dict(args), tool_result=None, call_id=call_id
                )
                pending_tool_results[call_id] = tool_name

        # Track tool RESULTS from ToolMessage.
        if hasattr(msg, "tool_call_id") and msg.tool_call_id:
            call_id = msg.tool_call_id
            if call_id in pending_tool_results:
                tool_name = pending_tool_results.pop(call_id)
                # Now mark satisfied with the actual result.
                gate.validate_and_track(
                    tool_name,
                    {},
                    tool_result=msg.content,
                    call_id=call_id,
                )

    def _verify_required_operations(self, *, gate: OperationGate | None = None) -> None:
        """Verify all required operations were performed.

        Raises:
            RuntimeError: If any required tool was not called.
        """
        unsatisfied = (gate or self._operation_gate).report_unsatisfied()
        if unsatisfied:
            msg = (
                f"Required tool(s) not called: {', '.join(unsatisfied)}. "
                "The agent response should not report success for this operation."
            )
            logger.warning(msg)
            raise RuntimeError(msg)


def build_agent(
    config: AgentConfig,
    registry: ToolRegistry | None = None,
    *,
    uc_function_client: Any | None = None,
) -> CoreAgent:
    """Single entrypoint every Fat Module's agent.py should call.

    Args:
        config: Validated ``AgentConfig`` instance.
        registry: Optional instance-scoped ``ToolRegistry``. A fresh one is
            created if not provided.

    Returns:
        A ``CoreAgent`` ready for ``predict`` / ``predict_stream``.
    """
    return CoreAgent(
        config,
        registry=registry,
        uc_function_client=uc_function_client,
    )

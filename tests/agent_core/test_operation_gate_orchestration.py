"""CoreAgent boundary tests for the deterministic required-operation gate."""

from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool, tool

from agent_core.orchestrator import (
    MAX_AGENT_GRAPH_STEPS,
    MAX_REQUEST_INPUT_CHARACTERS,
    CoreAgent,
    _make_sync_tool_adapters,
    _responses_safe_messages,
)
from agent_core.tool_policy import OperationGate, ToolPolicy, ToolRole


def _core_with_required_refund() -> CoreAgent:
    """Build the smallest CoreAgent instance needed to exercise event tracking."""

    @tool("check_refund_eligibility")
    def check_refund_eligibility(order_id: str, claim_date: str) -> dict[str, bool]:
        """Check a refund claim."""
        return {"eligible": True}

    core = object.__new__(CoreAgent)
    core._operation_gate = OperationGate(
        policies={
            "check_refund_eligibility": ToolPolicy(
                name="check_refund_eligibility",
                role=ToolRole.REQUIRED_ACTION,
                required_args=["order_id", "claim_date"],
            )
        }
    )
    core._tools_by_name = {"check_refund_eligibility": check_refund_eligibility}
    core._pending_tool_results = {}
    return core


def test_required_tool_invalid_arguments_are_rejected_before_execution():
    core = _core_with_required_refund()
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "check_refund_eligibility",
                "args": {"order_id": "o-1"},
                "id": "call-1",
            }
        ],
    )

    with pytest.raises(ValueError, match="Missing required argument.*claim_date"):
        core._track_tool_calls(message)
    assert core.operation_gate.report_unsatisfied() == ["check_refund_eligibility"]


def test_streaming_withholds_output_when_required_operation_is_missing(monkeypatch):
    """No response event can escape before post-stream gate verification."""

    core = _core_with_required_refund()

    class FakeGraph:
        def stream(self, *_args, **_kwargs):
            yield "updates", {"agent": {"messages": [object()]}}

    core.graph = FakeGraph()
    monkeypatch.setattr(
        "agent_core.orchestrator.to_chat_completions_input", lambda _: []
    )
    monkeypatch.setattr(
        "agent_core.orchestrator.output_to_responses_items_stream", lambda _: ["early"]
    )

    with pytest.raises(RuntimeError, match=r"Required tool\(s\) not called"):
        list(core.predict_stream(SimpleNamespace(input=[])))


def test_optional_streaming_yields_before_graph_completes(monkeypatch):
    core = _core_with_required_refund()
    core._operation_gate = OperationGate()  # no required workflow configured
    consumed = []

    graph_calls = []

    class FakeGraph:
        def stream(self, *_args, **kwargs):
            graph_calls.append(kwargs)
            consumed.append("first")
            yield "updates", {"agent": {"messages": [object()]}}
            consumed.append("second")
            yield "updates", {"agent": {"messages": [object()]}}

    core.graph = FakeGraph()
    monkeypatch.setattr(
        "agent_core.orchestrator.to_chat_completions_input", lambda _: []
    )
    monkeypatch.setattr(
        "agent_core.orchestrator.output_to_responses_items_stream", lambda _: ["event"]
    )

    stream = core.predict_stream(SimpleNamespace(input=[]))
    assert next(stream) == "event"
    assert consumed == ["first"]
    assert graph_calls[0]["config"]["recursion_limit"] == MAX_AGENT_GRAPH_STEPS


def test_request_input_over_safety_limit_is_rejected_before_graph_execution():
    core = _core_with_required_refund()

    class InputItem:
        def model_dump(self):
            return {"role": "user", "content": "x" * MAX_REQUEST_INPUT_CHARACTERS}

    with pytest.raises(ValueError, match="application safety limit"):
        list(core.predict_stream(SimpleNamespace(input=[InputItem()])))


def test_explicit_required_workflow_executes_before_model_generation():
    core = _core_with_required_refund()
    request = SimpleNamespace(
        custom_inputs={
            "required_operation": {
                "tool_name": "check_refund_eligibility",
                "arguments": {"order_id": "o-1", "claim_date": "2026-07-17"},
            }
        }
    )

    context = core._run_required_workflow(request)

    assert context is not None
    assert "check_refund_eligibility" in context
    assert core.operation_gate.all_required_satisfied()


def test_explicit_required_workflow_rejects_unavailable_tool():
    core = _core_with_required_refund()
    request = SimpleNamespace(
        custom_inputs={"required_operation": {"tool_name": "missing", "arguments": {}}}
    )

    with pytest.raises(ValueError, match="unavailable tool"):
        core._run_required_workflow(request)


def test_explicit_required_workflow_supports_async_only_tool():
    core = _core_with_required_refund()
    sync_tool = core._tools_by_name["check_refund_eligibility"]

    class AsyncOnlyTool:
        name = sync_tool.name
        args_schema = sync_tool.args_schema

        def invoke(self, _arguments):
            raise NotImplementedError("StructuredTool does not support sync invocation")

        async def ainvoke(self, _arguments):
            return {"eligible": True}

    core._tools_by_name["check_refund_eligibility"] = AsyncOnlyTool()
    request = SimpleNamespace(
        custom_inputs={
            "required_operation": {
                "tool_name": "check_refund_eligibility",
                "arguments": {"order_id": "o-1", "claim_date": "2026-07-17"},
            }
        }
    )

    context = core._run_required_workflow(request)

    assert context is not None
    assert core.operation_gate.all_required_satisfied()


def test_responses_output_normalizes_block_content_without_mutating_message():
    message = AIMessage(
        content=[
            {"type": "reasoning", "summary": [{"type": "summary_text", "text": "x"}]},
            {"type": "text", "text": "visible "},
            {"type": "output_text", "text": "answer"},
        ]
    )

    normalized = _responses_safe_messages([message])

    assert normalized[0].content == "visible answer"
    assert isinstance(message.content, list)


def test_async_only_mcp_tool_is_adapted_for_sync_graph_execution():
    async def lookup_order(order_id: str) -> dict[str, str]:
        return {"order_id": order_id, "status": "missing"}

    async_only = StructuredTool.from_function(
        coroutine=lookup_order,
        name="ecommerce_agent__agent_layer__get_order_status",
        description="Lookup an order.",
    )

    adapted = _make_sync_tool_adapters([async_only])

    assert adapted[0].invoke({"order_id": "o-1"}) == {
        "order_id": "o-1",
        "status": "missing",
    }


def test_request_local_operation_gates_do_not_leak_requirements_between_requests():
    core = _core_with_required_refund()
    request_a = SimpleNamespace(custom_inputs={})
    request_b = SimpleNamespace(
        custom_inputs={
            "required_operation": {
                "tool_name": "check_refund_eligibility",
                "arguments": {"order_id": "o-b", "claim_date": "2026-07-20"},
            }
        }
    )
    policies = {
        "check_refund_eligibility": ToolPolicy(
            name="check_refund_eligibility", role=ToolRole.OPTIONAL_READ
        )
    }
    gate_a = OperationGate(policies=dict(policies))
    gate_b = OperationGate(policies=dict(policies))

    assert core._run_required_workflow(request_a, gate=gate_a) is None
    assert core._run_required_workflow(request_b, gate=gate_b) is not None

    # This models request A resuming after request B has completed. A must not
    # inherit B's activated requirement or completion state from the singleton.
    assert gate_a.report_unsatisfied() == []
    assert gate_b.all_required_satisfied()

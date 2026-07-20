"""
Tests for tool-selection policy and operation gate (Sprint 1 tasks C10-C14).

Verifies:
- Tool classification (optional vs required)
- Deterministic operation gate that tracks required calls
- Argument validation against declared schemas
- Blocking success when required tools are not called
- Handling of invalid arguments
"""

import pytest

from agent_core.tool_policy import (
    OperationGate,
    ToolPolicy,
    ToolRole,
    build_default_policy,
    validate_required_arguments,
    assert_required_tool_invocation,
)


class TestToolPolicyRoles:
    def test_default_role_is_optional_read(self):
        policy = ToolPolicy(name="test_tool")
        assert policy.role == ToolRole.OPTIONAL_READ

    def test_required_action_role(self):
        policy = ToolPolicy(name="refund_tool", role=ToolRole.REQUIRED_ACTION)
        assert policy.role == ToolRole.REQUIRED_ACTION

    def test_required_args(self):
        policy = ToolPolicy(name="test", required_args=["order_id", "amount"])
        assert "order_id" in policy.required_args


class TestOperationGate:
    def test_no_policies_all_valid(self):
        gate = OperationGate()
        assert gate.validate_and_track("any_tool", {"arg": 1}) is True

    def test_track_required_tool(self):
        gate = OperationGate(
            policies={
                "mandatory_tool": ToolPolicy(
                    name="mandatory_tool", role=ToolRole.REQUIRED_ACTION
                ),
            }
        )
        gate.validate_and_track("mandatory_tool", {"arg": 1}, call_id="call-1")
        gate.validate_and_track(
            "mandatory_tool", {}, tool_result={"status": "ok"}, call_id="call-1"
        )
        assert gate.all_required_satisfied()

    def test_required_tool_not_called(self):
        gate = OperationGate(
            policies={
                "mandatory_tool": ToolPolicy(
                    name="mandatory_tool", role=ToolRole.REQUIRED_ACTION
                ),
            }
        )
        assert not gate.all_required_satisfied()
        assert "mandatory_tool" in gate.report_unsatisfied()

    def test_optional_tool_does_not_block(self):
        gate = OperationGate(
            policies={
                "optional_tool": ToolPolicy(
                    name="optional_tool", role=ToolRole.OPTIONAL_READ
                ),
            }
        )
        assert gate.all_required_satisfied()  # no required tools

    def test_missing_required_arg_raises(self):
        gate = OperationGate(
            policies={
                "strict_tool": ToolPolicy(
                    name="strict_tool",
                    role=ToolRole.REQUIRED_ACTION,
                    required_args=["order_id"],
                ),
            }
        )
        with pytest.raises(ValueError, match="Required argument.*order_id.*missing"):
            gate.validate_and_track("strict_tool", {})

    def test_report_unsatisfied_multiple(self):
        gate = OperationGate(
            policies={
                "tool_a": ToolPolicy(name="tool_a", role=ToolRole.REQUIRED_ACTION),
                "tool_b": ToolPolicy(name="tool_b", role=ToolRole.REQUIRED_ACTION),
                "tool_c": ToolPolicy(name="tool_c", role=ToolRole.OPTIONAL_READ),
            }
        )
        gate.validate_and_track("tool_a", {"x": 1}, call_id="call-a")
        unsatisfied = gate.report_unsatisfied()
        assert "tool_a" in unsatisfied  # call alone is not completion
        assert "tool_b" in unsatisfied
        assert "tool_c" not in unsatisfied  # optional


class TestAssertRequiredToolInvocation:
    def test_passes_when_called(self):
        gate = OperationGate(
            policies={
                "required_tool": ToolPolicy(
                    name="required_tool", role=ToolRole.REQUIRED_ACTION
                ),
            }
        )
        gate.validate_and_track("required_tool", {}, call_id="call-1")
        gate.validate_and_track(
            "required_tool", {}, tool_result="done", call_id="call-1"
        )
        assert_required_tool_invocation(gate, "required_tool")  # should not raise

    def test_raises_when_not_called(self):
        gate = OperationGate(
            policies={
                "required_tool": ToolPolicy(
                    name="required_tool", role=ToolRole.REQUIRED_ACTION
                ),
            }
        )
        with pytest.raises(RuntimeError, match="not called"):
            assert_required_tool_invocation(gate, "required_tool")

    def test_optional_tool_no_assertion(self):
        gate = OperationGate()
        assert_required_tool_invocation(gate, "optional_tool")  # should not raise


class TestValidateRequiredArguments:
    def test_missing_required_argument(self):
        """Depends on tool having actual args schema."""
        # Using a simple check via the function

        # The local function tool wraps python functions
        # For the validate function, test basic behavior
        from langchain_core.tools import tool as lc_tool

        @lc_tool
        def sample_tool(x: int, y: str) -> str:
            """A sample tool with required args."""
            return f"{x}:{y}"

        with pytest.raises(ValueError, match="Missing required argument"):
            validate_required_arguments(sample_tool, {"y": "test"})

    def test_invalid_argument_type(self):
        from langchain_core.tools import tool as lc_tool

        @lc_tool
        def sample_tool(count: int) -> str:
            """A sample tool with a typed argument."""
            return str(count)

        with pytest.raises(ValueError, match="Invalid arguments"):
            validate_required_arguments(sample_tool, {"count": {"bad": "type"}})


class TestBuildDefaultPolicy:
    def test_builds_all_optional(self):
        from langchain_core.tools import tool as lc_tool

        @lc_tool
        def tool_a(x: int) -> int:
            """Tool A."""
            return x

        @lc_tool
        def tool_b(y: str) -> str:
            """Tool B."""
            return y

        gate = build_default_policy([tool_a, tool_b])
        assert gate.all_required_satisfied()  # all optional
        assert len(gate.policies) == 2


class TestRequiredOperationCompletion:
    def test_call_without_result_does_not_satisfy_required_operation(self):
        gate = OperationGate(
            policies={
                "refund": ToolPolicy(name="refund", role=ToolRole.REQUIRED_ACTION)
            }
        )
        gate.validate_and_track("refund", {"order_id": "o-1"}, call_id="call-1")
        assert gate.report_unsatisfied() == ["refund"]

    def test_result_without_validated_call_is_rejected(self):
        gate = OperationGate(
            policies={
                "refund": ToolPolicy(name="refund", role=ToolRole.REQUIRED_ACTION)
            }
        )
        with pytest.raises(ValueError, match="not correlated"):
            gate.validate_and_track(
                "refund", {}, tool_result={"eligible": True}, call_id="call-1"
            )

    def test_empty_result_does_not_satisfy_required_operation(self):
        gate = OperationGate(
            policies={
                "refund": ToolPolicy(name="refund", role=ToolRole.REQUIRED_ACTION)
            }
        )
        gate.validate_and_track("refund", {}, call_id="call-1")
        with pytest.raises(ValueError, match="invalid or empty"):
            gate.validate_and_track("refund", {}, tool_result="", call_id="call-1")
        assert gate.report_unsatisfied() == ["refund"]

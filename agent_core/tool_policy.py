"""
agent_core.tool_policy
-------------------------
Tool-selection policy for models that cannot accept protocol-level
``tool_choice`` (e.g. DeepSeek V4 thinking mode).

Provides:
- Classification of tools as optional/read-only vs required/state-changing.
- Deterministic operation gate that routes required intents to an explicit
  workflow rather than relying on the model to choose a tool.
- Argument validation against declared schemas before execution.
- Completion verification: blocks success response until the required
  tool call and typed result are observed.

This is an application-level safety layer, not a model protocol feature.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class ToolRole:
    """Classification constants for tool roles."""

    OPTIONAL_READ = "optional_read"
    """Read-only tools that are safe to skip; the model may or may not call them."""

    REQUIRED_ACTION = "required_action"
    """State-changing or information-required operations that MUST be executed
    before a success response can be returned."""


@dataclass
class ToolPolicy:
    """Policy for one tool: its role and optional argument schema."""

    name: str
    role: str = ToolRole.OPTIONAL_READ
    required_args: list[str] = field(default_factory=list)
    """Argument names that must be present and non-empty for a valid call."""


@dataclass
class OperationGate:
    """Deterministic gate that validates and tracks required operations.

    The gate ensures:
    1. Required tools are actually called before reporting success.
    2. Arguments to required tools are valid against declared schemas.
    3. The typed tool result is observed before unblocking success.
    """

    policies: dict[str, ToolPolicy] = field(default_factory=dict)

    required_satisfied: set[str] = field(default_factory=set)
    """Names of required tools with a validated call and correlated result."""

    pending_calls: dict[str, str] = field(default_factory=dict)
    """Validated required calls, keyed by provider tool-call id."""

    activated_required: set[str] = field(default_factory=set)
    """Operations explicitly routed as required for the current request."""

    def validate_and_track(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tool_result: Any | None = None,
        *,
        call_id: str | None = None,
    ) -> bool:
        """Validate a tool call and track it as satisfied if required.

        Args:
            tool_name: The tool that was called.
            arguments: The arguments supplied to the tool.
            tool_result: The result from executing the tool. If None, the
                tool is tracked as called but with an unknown result.

        Returns:
            True if the call is valid (all required args present).

        Raises:
            ValueError: If required arguments are missing or invalid.
        """
        policy = self.policies.get(tool_name)
        if policy is None:
            return True  # no policy for this tool — always valid

        if (
            policy.role != ToolRole.REQUIRED_ACTION
            and tool_name not in self.activated_required
        ):
            return True

        if tool_result is None:
            # Validate required arguments only on the call. A ToolMessage does
            # not repeat them, so validating them again on the result would
            # incorrectly reject a valid correlated completion.
            for arg_name in policy.required_args:
                value = arguments.get(arg_name)
                if value is None or (isinstance(value, str) and not value.strip()):
                    raise ValueError(
                        f"Required argument '{arg_name}' missing for tool '{tool_name}'"
                    )
            if not call_id:
                raise ValueError(
                    f"Required tool '{tool_name}' call is missing a tool-call id"
                )
            self.pending_calls[call_id] = tool_name
            logger.info("Required tool '%s' call validated", tool_name)
            return True

        if not call_id or self.pending_calls.get(call_id) != tool_name:
            raise ValueError(
                f"Tool result for required tool '{tool_name}' is not correlated "
                "with a validated tool call"
            )
        if not _is_typed_tool_result(tool_result):
            raise ValueError(
                f"Required tool '{tool_name}' returned an invalid or empty result"
            )

        self.pending_calls.pop(call_id)
        self.required_satisfied.add(tool_name)
        logger.info("Required tool '%s' result satisfied", tool_name)

        return True

    def all_required_satisfied(self) -> bool:
        """Check whether every required tool has been called."""
        required_names = self._required_names()
        return required_names.issubset(self.required_satisfied)

    def _required_names(self) -> set[str]:
        return {
            name
            for name, policy in self.policies.items()
            if policy.role == ToolRole.REQUIRED_ACTION
        } | self.activated_required

    def report_unsatisfied(self) -> list[str]:
        """Return the names of required tools that have NOT been satisfied."""
        return sorted(self._required_names() - self.required_satisfied)

    def reset(self) -> None:
        """Clear per-request completion state."""
        self.required_satisfied.clear()
        self.pending_calls.clear()
        self.activated_required.clear()

    def require_tool(self, tool_name: str) -> None:
        """Activate a required workflow for this request explicitly."""
        if tool_name not in self.policies:
            raise ValueError(f"Required workflow references unknown tool '{tool_name}'")
        self.activated_required.add(tool_name)


def _is_typed_tool_result(result: Any) -> bool:
    """Reject absent/empty results without interpreting business success.

    A tool result may be a Pydantic model, mapping, or scalar content. The
    operation itself owns its business-level success/failure semantics; the
    gate only requires a real result correlated to the validated invocation.
    """
    if result is None:
        return False
    if isinstance(result, str):
        return bool(result.strip())
    if isinstance(result, (dict, list, tuple, set)):
        return bool(result)
    return True


def build_default_policy(tools: list[BaseTool]) -> OperationGate:
    """Build an OperationGate with defaults for the given tools.

    By default, read-only tools are optional. Known state-changing and
    eligibility tools are required actions; a Fat Module can replace this
    mapping with its own policy before handling a request.
    """
    policies: dict[str, ToolPolicy] = {}
    for t in tools:
        policies[t.name] = ToolPolicy(name=t.name, role=ToolRole.OPTIONAL_READ)
    return OperationGate(policies=policies)


def validate_required_arguments(
    tool: BaseTool,
    arguments: dict[str, Any],
) -> bool:
    """Validate that a tool call has all required arguments per its schema.

    Checks the tool args schema's model fields for required markers.

    Args:
        tool: The LangChain tool.
        arguments: Arguments supplied to the tool.

    Returns:
        True if valid.

    Raises:
        ValueError: With details on missing/invalid arguments.
    """
    # LangChain tools store their args_schema as a Pydantic model.
    # Check its model_fields for required ones.
    if not hasattr(tool, "args_schema") or tool.args_schema is None:
        return True

    try:
        model_fields = tool.args_schema.model_fields
    except AttributeError:
        return True

    for field_name, field_info in model_fields.items():
        # In Pydantic v2, a field is required if it has no default
        is_required = field_info.is_required()
        if is_required and field_name not in arguments:
            raise ValueError(
                f"Missing required argument '{field_name}' for tool '{tool.name}'"
            )

    try:
        tool.args_schema.model_validate(arguments)
    except Exception as exc:
        raise ValueError(f"Invalid arguments for tool '{tool.name}': {exc}") from exc

    return True


def assert_required_tool_invocation(
    gate: OperationGate,
    tool_name: str,
) -> None:
    """Assert that a required tool has been invoked.

    This is used AFTER the agent response to verify mandatory calls.

    Raises:
        RuntimeError: If the required tool was not called.
    """
    if tool_name not in gate.required_satisfied:
        policy = gate.policies.get(tool_name)
        role = policy.role if policy else ToolRole.OPTIONAL_READ
        if role == ToolRole.REQUIRED_ACTION:
            raise RuntimeError(
                f"Required tool '{tool_name}' was not called. "
                "The model did not invoke this mandatory operation. "
                "The response should not report success for this operation."
            )

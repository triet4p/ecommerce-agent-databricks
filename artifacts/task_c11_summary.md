# Task Summary: C11 Deterministic required-operation workflow

**Sprint:** Sprint 1
**Task:** C11

## Summary of Work

Added the explicit `custom_inputs.required_operation` contract. It validates the
selected configured tool and arguments, executes the tool before model
generation, correlates its typed result through `OperationGate`, and injects a
non-forgeable workflow-result context for the final response. Requests without
this contract retain normal streaming behavior.

## Files Modified

* `agent_core/orchestrator.py` - Deterministic pre-model workflow execution.
* `agent_core/tool_policy.py` - Per-request activation of required tools.
* `tests/agent_core/test_operation_gate_orchestration.py` - Explicit workflow boundary tests.

## Testing

* **Test File:** `tests/agent_core/test_tool_policy.py`, `tests/agent_core/test_operation_gate_orchestration.py`
* **Status:** Passed (23 tests)
* **Execution Command:** `.\\.venv\\Scripts\\python.exe -m pytest tests/agent_core/test_tool_policy.py tests/agent_core/test_operation_gate_orchestration.py -q`

## Additional Notes

Callers must deliberately provide the required-operation object. This avoids
keyword/model-output intent guessing and keeps optional requests real-time.

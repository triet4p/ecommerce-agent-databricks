# Task Summary: S4 runtime hardening

**Sprint:** Sprint 4
**Task:** Completion event, context budget, and production runtime hardening

## Summary of Work

The Agent completion event now includes the output items emitted during the
stream. The Chat UI server rejects oversized replay contexts with the typed
`CONTEXT_BUDGET_EXCEEDED` error before calling the Agent. The Chat UI production
command now runs compiled JavaScript artifacts, and its Lakebase endpoint is
resolved through the managed `conversation-store` resource rather than a
hard-coded deployment value.

## Files Modified

* `agent_core/orchestrator.py` - records completed output items for the terminal event.
* `chat_ui/server/src/routes/turns.ts` - enforces the replay context safety budget.
* `chat_ui/package.json` - builds core, client, and server artifacts in production order.
* `chat_ui/server/package.json` - starts compiled JavaScript instead of `tsx`.
* `chat_ui/app.yaml` - resolves the Lakebase endpoint from `conversation-store`.

## Testing

* **Test File:** `tests/agent_core/test_streaming_contract.py`
* **Status:** Passed
* **Execution Command:** `uv run pytest tests/agent_core/test_streaming_contract.py -q`
* **Additional gates:** `npm run build`, `npm run typecheck`, `npm run lint`, and `npm test` passed.

## Additional Notes

The corrected Chat UI production artifact snapshot and the Agent completion
contract snapshot were both deployed and reached `RUNNING` using the
`Ecommerce-Agent` profile. Browser-authenticated feature-parity smokes remain
unverified because no in-app browser session is available in this environment.

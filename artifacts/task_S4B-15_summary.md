# Task Summary: Differentiate the React chat experience

**Sprint:** Sprint 4b
**Task:** S4B-15

## Summary of Work

Replaced the Streamlit-equivalent React shell with a responsive governed
commerce assistant experience. The deployed UI now has a useful starter state,
mobile-safe navigation, automatic stream following, explicit active/error
phases, polished Markdown, expandable tool provenance, an ergonomic sticky
composer, authenticated identity disclosure, and accessible conversation
actions. Live testing also removed raw tool JSON from answers/history and fixed
failed-response and non-current-delete lifecycle defects.

## Files Modified

- `chat_ui/client/src/components/ConversationWelcome.tsx` — starter experience.
- `chat_ui/client/src/components/Composer.tsx` — sticky, trust-aware composer.
- `chat_ui/client/src/components/Message.tsx` — response hierarchy and stream states.
- `chat_ui/client/src/components/ToolCard.tsx` — governed arguments/result provenance.
- `chat_ui/client/src/components/Sidebar.tsx` — responsive accessible navigation.
- `chat_ui/client/src/pages/ChatPage.tsx` — identity, hydration, and auto-follow shell.
- `chat_ui/client/src/hooks/useChat.ts` — clean failure/history lifecycle.
- `agent_core/orchestrator.py` — prevent tool-result chunks entering visible text.
- `ecommerce_agent/conversation/replay.py` — filter legacy JSON tool echoes.

## Testing

- **Test Files:** `chat_ui/tests/components/*`,
  `tests/agent_core/test_streaming_contract.py`,
  `tests/conversation/test_replay.py`
- **Status:** Passed
- **Execution Commands:** `npm test`, `npm run lint`, `npm run typecheck`,
  `npm run build`, and focused `uv run pytest`/Ruff gates.
- **Live Evidence:** React snapshot `01f186c191531985adc2bf25817f2782`
  completed order and policy tool streams, rendered Markdown tables/lists,
  expanded safe arguments/results, restored clean history, and passed
  rename/delete.

## Additional Notes

- The workspace requires the custom retriever endpoint to scale to zero. Agent
  snapshot `01f186c3cd021563a82d3023c3a833fb` therefore warms it at startup and
  every 15 minutes; this can increase serving cost.
- Cross-user browser isolation is owner-deferred. Rollback S4B-12 remains the
  final gate before removing Streamlit.

# S4B-11 Authenticated Browser E2E — Completed Evidence

Date: 2026-07-24

## Candidate

- Databricks App: `ecommerce-agent-chat-ui`
- Snapshot: `01f186c191531985adc2bf25817f2782`
- Runtime: compiled Node server serving the React build

## Passed with a real logged-in user

- React shell, assets, sidebar, conversation route, and composer.
- Idle → streaming → terminal lifecycle without reload.
- Incremental Markdown response and two-turn completed-history replay.
- Reload restoration of persisted messages.
- Conversation switching between populated and empty histories without stale
  messages or tool state.
- Governed `get_order_status` tool execution and final answer.
- Stop/cancel followed by reload with no cancelled prompt or partial output.
- Real HTTP 400 error rendering and Retry without a duplicate user message.
- Production debug/trace control absent.
- Responsive React experience, starter actions, sticky composer, streaming
  skeleton/phase state, and authenticated identity disclosure.
- Expanded tool cards with formatted arguments, result, and provenance.
- Markdown tables and lists with no raw tool JSON in visible assistant text.
- Rename and delete, including deletion of a non-current conversation without
  changing the active route.
- Policy retrieval after Agent warm-up, completing below the Chat UI timeout.

## Defects fixed during the pass

1. Idle conversations initialized with `isStreaming=true`.
2. Completed text responses retained the active “Composing…” phase label.
3. Pre-stream `createTurn` errors had no assistant node to render the error.
4. The Chat UI proxy now suppresses upstream `[DONE]` and emits one
   downstream sentinel only after terminal persistence.
5. Raw `ToolMessageChunk` JSON was emitted and persisted as assistant text.
6. Failed partial output became a normal-looking answer after a later send.
7. Deleting a non-current conversation navigated away from the active route.
8. Scale-to-zero retriever cold start exceeded the Apps request budget.

## Verification

- Component tests: 14 passed.
- Deterministic/server tests: 36 passed, 1 credential-gated PostgreSQL test
  skipped.
- Focused Python streaming/replay/warm-up tests: 41 passed.
- Biome, TypeScript typecheck, and production build passed.

## Deferred and remaining gates

- Cross-user isolation is deferred by the repository owner and is no longer a
  Sprint 4b completion gate.
- Rollback certification remains S4B-12 and is the only gate before Streamlit
  removal.

S4B-11 is complete. S4B-12 rollback certification may proceed; Streamlit
removal must still wait until rollback passes.

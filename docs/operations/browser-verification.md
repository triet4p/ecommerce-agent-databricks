# Browser Verification and UI Cutover Checklist

Use a real authenticated Databricks browser session after deploying the Chat UI.
Deterministic tests remain necessary but do not replace ingress identity, OAuth,
streaming, persistence, and static-asset verification in the deployed App.

## React parity

- [ ] Open the active React App and confirm shell, sidebar, composer, and assets
  render without a redirect loop or console error.
- [ ] Confirm the trusted user identity and healthy Agent/conversation-store
  status.
- [ ] Start a turn and observe preparing, tool, and text progress without a page
  reload.
- [ ] Run a tool-backed request; expand the card and verify sanitized arguments,
  result, progress, and final answer.
- [ ] Verify Markdown headings, lists, tables, links, and code formatting.
- [ ] Send a second turn and confirm completed message history reaches the Agent.
- [ ] Reload and verify messages, correlated tool cards, terminal state, and
  trace provenance hydrate correctly.
- [ ] Switch rapidly between conversations and confirm stale history never
  appears in the selected thread.
- [ ] Retry an error and verify no duplicate user message or turn is created.
- [ ] Stop an active response and verify reload shows `cancelled`, never
  completed partial output.
- [ ] Verify timeout, Agent unavailable, Lakebase unavailable, invalid request,
  and unauthorized states remain actionable without resource-detail leakage.
- [ ] Rename and delete a temporary conversation.
- [ ] Check desktop and narrow mobile layouts for horizontal overflow.

## Streamlit switch

Follow the commands in [redeploy.md](redeploy.md), then verify:

- [ ] the same trusted owner identity is active;
- [ ] an existing React-created conversation is listed and hydrated;
- [ ] one new turn reaches terminal completion and persists;
- [ ] no raw reasoning, credential, or unsafe tool payload is displayed.

Record the Streamlit deployment ID before restoring React.

## React restoration

- [ ] Redeploy without `chat_ui_source`; the default must resolve to
  `.build/apps/chat_ui`.
- [ ] Confirm the production command is the built Node server.
- [ ] Confirm React lists and hydrates the Streamlit-created conversation.
- [ ] Delete only the temporary verification conversation.
- [ ] Confirm the final Chat UI deployment is `RUNNING / ACTIVE / SUCCEEDED`.

## Cross-user isolation

Cross-user browser isolation requires a second authenticated user session. It
remains owner-deferred. Until that manual gate is run, retain deterministic
owner-scoped service, repository, and PostgreSQL integration coverage.

## Latest certified evidence

The Sprint 5 authenticated pass on 2026-07-24 verified:

- React incremental streaming, tool details, Markdown, two-turn replay, reload,
  retry, Stop, error, rename, delete, desktop, and mobile behavior;
- Streamlit loading existing current-owner history and persisting a new
  completed turn;
- React restoration loading the Streamlit-created history;
- Agent snapshot `01f18727edd312acbb5389602bdf1467`;
- Streamlit snapshot `01f18729fcae105bbd4fb503b7a47165`;
- final React snapshot `01f1872a4a8c15808ec6454f77068bb4`.

Detailed evidence is stored in
`artifacts/s5-manual-verification-2026-07-24.md`.


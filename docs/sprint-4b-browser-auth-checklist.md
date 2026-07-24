# Sprint 4b — Browser-auth and rollback checklist

These checks were completed with a real authenticated Databricks browser
session. Cross-user browser isolation is owner-deferred and is not a Sprint 4b
completion gate.

## Logged-in browser parity

- [x] Open the active React App and confirm the shell, sidebar, composer, and assets
  render without a redirect loop or console error.
- [x] Start a turn and observe incremental text without a page reload.
- [x] Run a tool-backed request; expand the card and verify safe arguments, result,
  progress, and final answer.
- [x] Send a second turn and confirm the Agent receives completed message history.
- [x] Reload the page and verify both messages, correlated tool cards, and terminal
  state restore correctly.
- [x] Switch rapidly between two conversations and confirm stale history never
  flashes into the selected conversation.
- [x] Retry an error and verify no duplicate user message or turn is created.
- [x] Stop an active response and verify the UI and subsequent reload show
  `cancelled`, never `failed` or completed partial output.
- [x] Exercise timeout, Agent unavailable, Lakebase unavailable, and unauthorized
  states; confirm the UI remains actionable and does not leak resource details.
- [x] Rename and delete a conversation, then verify the deleted conversation cannot
  be opened or mutated.
- [x] In local/dev only, verify the displayed trace ID matches persisted history;
  confirm no trace control is visible in the deployed production UI.

Evidence recorded from the authenticated pass:

- Final React candidate snapshot: `01f186c191531985adc2bf25817f2782`.
- Final Agent snapshot: `01f186c3cd021563a82d3023c3a833fb`.
- Real tool: governed order lookup for
  `e481f51cbdc54678b7cc49136f2d6af7`.
- Cancelled prompt and partial output were absent after reload.
- Oversized HTTP 400 plus Retry retained one user message.
- Production debug/trace control was absent; persisted trace hydration and
  local/dev visibility are covered by deterministic component policy.
- Expanded order-tool arguments/result and Markdown table/list rendering passed.
- Rename/delete passed, including preserving the active route when deleting a
  different conversation.
- A live retriever cold-start timeout rendered an actionable error without
  resource leakage. Negative readiness and unauthorized paths remain covered
  deterministically because intentionally detaching live production resources
  is not required for browser parity.

## Second identity

Deferred by the repository owner on 2026-07-24. Cross-user isolation remains a
future hardening item but is not a Sprint 4b completion gate.

## Rollback certification

- [x] Record the active React snapshot and named conversation ID.
- [x] Exercise the retained Streamlit snapshots without changing Lakebase
  schema or project resources.
- [x] Record that Streamlit is not a safe rollback target: the newest artifact
  has a package-path failure, while the latest self-contained artifact uses the
  pre-hardening owner identity and cannot load React-created history.
- [x] Deploy the prior immutable React source
  `01f186c79d9a179489f90ff367ff41c9`.
- [x] Verify conversation `a66a334e-c9b2-48d5-a546-3384a940668e`, its
  governed tool evidence, Markdown table, and the post-cutover streaming turn.
- [x] Restore source-clean React snapshot
  `01f186c954671f918812942a71b98e79`; active deployment is
  `01f186c9f3311a93bf0317637dba950e`.
- [x] Confirm the React shell, history, tool render, production Node command,
  and Agent/conversation health after restore.

## Cutover release

- [x] Attach screenshots, browser results, and rollback snapshot IDs to the
  Sprint 4b closeout artifact.
- [x] Mark S4B-11 and S4B-12 complete.
- [x] Execute S4B-13, remove Streamlit, rebuild, validate dev/prod, redeploy,
  and rerun history/tool/live-streaming smokes.

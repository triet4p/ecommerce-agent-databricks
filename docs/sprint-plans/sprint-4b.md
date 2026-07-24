# Sprint 4b Plan — React Cutover Hardening

## Sprint Goal

Turn the deployed Sprint 4 Node/React implementation into a production-ready
Chat UI by fixing the live runtime, readiness, persistence, streaming, and
shutdown defects; completing real PostgreSQL and authenticated browser
verification; proving rollback; and removing Streamlit only after every cutover
gate passes.

## Starting Point

- Chat UI snapshot `01f18684be3f16c0be09fb35a0e13bd8` is active and runs
  compiled Node code, but the live root route returns `404` because the server
  starts with `NODE_ENV=development` and does not serve the React build.
- Live health currently reports `healthy: true` while `agent: false`; the Agent
  App is running but does not expose the `/api/health` route probed by Chat UI.
- Local Python verification passes with 392 tests, 4 skips, and 37 subtests.
- Local Node build, typecheck, lint, and 24 deterministic tests pass, but the
  default Node test command excludes server and authenticated browser suites.
- Sprint 3b remains open until isolated PostgreSQL integration and real
  React-server-to-Agent verification pass.

## Definition of Done

- The deployed Chat UI root and static assets return successfully and render
  React in production mode.
- Readiness accurately represents both Lakebase and Agent availability.
- Owner-scoped persistence and terminal turn transitions pass isolated
  PostgreSQL integration tests with a real database principal.
- Streaming honors backpressure, cancellation has one deterministic terminal
  outcome, and shutdown completes within the Databricks 15-second SIGTERM
  window.
- Component, server, and authenticated browser E2E suites cover the Sprint 4
  parity contract and failure paths. Owner/database isolation remains proven
  deterministically; the second browser identity check is owner-deferred.
- Rollback is exercised without data or schema loss.
- Streamlit is removed only after feature-parity and rollback gates pass.
- Plans, artifacts, lessons, and Git history accurately represent the released
  implementation.

## Atomic Tasks

Status legend: `[ ]` pending / `[~]` in progress / `[x]` done.

### P0 — Cutover blockers

- [x] **S4B-01 — Serve React in the live production runtime:** Configure the
  Databricks Chat UI App to start with `NODE_ENV=production` or an equivalent
  explicit runtime signal; keep the compiled `node dist/index.js` command;
  deploy a new snapshot; and verify `/`, the SPA fallback, JavaScript, and CSS
  assets return `200` instead of `404`.

- [x] **S4B-02 — Make readiness reflect the real Agent dependency:** Add a
  supported authenticated Agent health endpoint or change Chat UI to a valid
  Agent probe; compute readiness from both Lakebase and Agent health; return
  `503` when either required dependency is unavailable; and add positive and
  negative readiness tests. Keep Sprint 4 task S4-C7 in progress until this
  passes live.

- [x] **S4B-03 — Fix and prove idempotent Node turn completion:** Qualify the
  ambiguous columns in the joined terminal-state query, audit related terminal
  SQL, and verify repeated owner-scoped complete/fail/cancel operations against
  PostgreSQL. Reconcile Sprint 3b S3B-05 and Sprint 4 S4-C2 status with the
  resulting evidence.

- [x] **S4B-04 — Implement streaming backpressure:** Respect the boolean result
  of downstream `res.write`, pause upstream reads while the response buffer is
  full, resume on `drain`, and clean up readers and abort signals on timeout,
  downstream disconnect, and upstream failure. Add a deterministic slow-client
  test before marking Sprint 4 S4-C4 complete.

- [x] **S4B-05 — Eliminate the Stop/cancel terminal-state race:** Define one
  cancellation owner across browser abort, the cancel lifecycle endpoint, and
  server disconnect handling so a user Stop always persists `cancelled` rather
  than racing to `failed`; keep repeated cancellation idempotent; and test the
  final database state for Stop, disconnect, and upstream error paths.

### P1 — Integration, test, and production hardening

- [x] **S4B-06 — Complete isolated PostgreSQL integration coverage:** Run
  migrations and repository tests with a real database principal in an
  isolated database or schema, covering v1-to-v2 migration and rollback,
  constraints, concurrent sequencing, retries, owner isolation, soft deletion,
  redaction, 50 KB payload and 100-item limits, terminal idempotency, and
  completed-message-only replay. Use this evidence to close Sprint 3b S3B-11.

- [x] **S4B-07 — Complete the Node verification matrix:** Add real React
  component tests for streamed Markdown, tool cards, progress, errors, and
  navigation; strengthen server tests for trusted identity, OAuth proxying,
  authorization, cancellation, and terminal error propagation; add duplicate
  event/idempotency suppression coverage; remove assertions that accept server
  `500` as success; and provide an explicit command that runs all deterministic,
  component, and server suites.

- [x] **S4B-08 — Complete persisted history and developer trace UX:** Restore
  correlated persisted tool calls and results after reload, prevent stale
  history while switching conversations, expose an actual trace ID or
  developer-only trace link, keep trace controls unavailable to normal deployed
  users, and test timeout, unauthorized, and unavailable-dependency UI states.
  Reopen Sprint 4 S4-D10 until trace evidence is displayed.

- [x] **S4B-09 — Meet the Databricks graceful-shutdown contract:** Retain the
  HTTP server handle, stop accepting new requests, abort or drain active
  streams, close the HTTP server and Lakebase pool in a bounded order, and add
  a force-exit deadline below 15 seconds. Verify local SIGTERM and Databricks
  redeploy/rollback logs contain no shutdown-timeout error.

- [x] **S4B-10 — Remove deploy-artifact configuration leakage and noise:** Remove
  the Python Lakebase deployment-specific endpoint fallback or require a bound
  resource/environment value, set production environment explicitly, exclude
  `chat_ui/debug.log` and other local outputs, and inspect the packaged Agent
  and Chat UI snapshots for unnecessary local files or deployment-specific
  values.

### P2 — Verification, rollback, and closeout

- [x] **S4B-11 — Run authenticated browser feature-parity E2E:** With a real
  logged-in Databricks user, verify React and assets, incremental streaming,
  tool arguments/results, terminal completion and persistence, two-turn replay,
  reload restoration, retry without duplicate messages or turns, deterministic
  Stop/cancel, failed-stream non-persistence, rename/delete, health/error UI,
  and OAuth. Cross-user isolation is deferred by the repository owner and is no
  longer a Sprint 4b completion gate. Use the evidence to close Sprint 3b
  S3B-12 and Sprint 4 S4-E4, S4-E5, and S4-E9.

- [x] **S4B-12 — Exercise and document rollback:** Record the React and rollback
  snapshot IDs, exercise the retained Streamlit artifacts, and reject them as
  production rollback targets when browser evidence proves package-path or
  identity incompatibility. Roll back to the prior immutable React snapshot,
  verify pre- and post-cutover Lakebase data, then restore the exact current
  React source. Use the evidence to close Sprint 4 S4-E10.

- [x] **S4B-13 — Remove Streamlit only after cutover gates pass:** After
  S4B-11 and S4B-12 are complete, remove the Streamlit Chat UI source,
  requirements, bundle references, and obsolete documentation without changing
  the Agent App or MCP facade. Rebuild, validate both bundle targets, redeploy,
  and rerun the critical React smokes before closing Sprint 4 S4-E11.

- [x] **S4B-14 — Reconcile plans, evidence, lessons, and Git history:** Update
  Sprint 3b, Sprint 4, and global milestone statuses from verified evidence;
  correct stale closeout artifacts; record durable lessons for production mode,
  health contracts, cancellation, backpressure, and SIGTERM; remove local-only
  artifacts; and commit the complete Sprint 3b/4/4b implementation with focused
  Conventional Commits. Close Sprint 3b and Sprint 4b only after their
  completion gates pass.

- [x] **S4B-15 — Differentiate the React chat experience:** Replace the
  Streamlit-equivalent shell with a responsive, product-grade assistant
  experience: mobile-safe navigation, useful empty conversation state,
  auto-following incremental output, clear active/terminal phases, polished
  Markdown and governed tool provenance, an ergonomic composer, authenticated
  identity/execution disclosure, and accessible conversation actions. Add
  component/browser evidence and redeploy before closing S4B-11.

## Execution Order and Completion Gates

1. Complete S4B-01 through S4B-05 before treating any deployed React snapshot as
   a cutover candidate.
2. Complete S4B-03 and S4B-06 before closing Sprint 3b persistence hardening.
3. Complete S4B-06 through S4B-10 before running the final authenticated parity
   suite.
4. Complete S4B-11 before rollback certification.
5. Complete S4B-11 and S4B-12 before any Streamlit removal in S4B-13.
6. Complete S4B-14 only after code, deployment, E2E, and rollback evidence are
   final and reproducible.

## Notes / Blockers

- Browser E2E requires a real logged-in Databricks Apps session. Cross-user
  isolation has been explicitly deferred by the repository owner.
- One authenticated in-app Browser identity completed the required parity path.
  Cross-user browser isolation remains explicitly deferred by the owner.
- PostgreSQL integration must use an isolated database/schema and must not
  delete or mutate unrelated Lakebase data.
- Deployment and rollback must preserve the canonical `ecommerce_agent`
  catalog, Agent App, MCP facade, existing serving endpoints, and conversation
  data.
- A Databricks App reporting `RUNNING` is not sufficient evidence of a usable
  React cutover; root/static asset, health, streaming, persistence, and browser
  checks must all pass.

## Verified Evidence — 2026-07-23

- Agent snapshot `01f186ac0eaa16639aa4f0724a4b5aee` succeeded and exposes
  authenticated `/api/health`.
- Active React snapshot `01f186ae3e851a9080a3f9b67e7df4d0` serves `/`, SPA
  fallback, JavaScript, and CSS with HTTP 200.
- Chat readiness returns HTTP 200 with `database: true` and `agent: true`.
- Authenticated API smoke completed a real Agent stream, observed
  `response.completed` and `[DONE]`, restored two persisted items with a real
  MLflow trace ID, and soft-deleted its temporary conversation.
- A second deployment of the direct Node command logged SIGTERM receipt and
  `Shutdown complete` in the same second; no later system timeout was emitted.
- Isolated real-PostgreSQL suites passed in a four-hour TTL branch: Python
  `1 passed` and Node `1 passed`; the temporary branch was deleted.
- Local gates: Python `395 passed, 5 skipped, 37 subtests`; Node component
  `8 passed`; deterministic/server `34 passed, 1 skipped`; production build,
  typecheck, Biome, Ruff, compileall, npm audit, and strict dev/prod Bundle
  validation passed.
- Historical note: S4B-11 through S4B-13 were still gated at this checkpoint.
  The final 2026-07-24 evidence below supersedes this status.

## Additional Browser Evidence — 2026-07-23

- Active React candidate snapshot:
  `01f186b93f961f48a1a73de80a655de2`.
- A real logged-in Databricks user verified React shell/assets, idle composer,
  incremental streaming, terminal completion, two-turn replay, and reload
  restoration.
- A real governed order lookup for
  `e481f51cbdc54678b7cc49136f2d6af7` rendered tool progress and returned
  `delivered`, eight days early.
- A live Stop removed the active stream immediately; reload proved the
  cancelled prompt and partial assistant output were not persisted.
- Switching between the populated tool conversation and a new empty
  conversation restored the correct history in each direction without leaking
  the prior messages or tool card.
- An oversized request exercised the real HTTP 400 path. The assistant error
  and Retry rendered, and retry retained exactly one user message.
- Production exposed no debug/trace control.
- Browser execution found and fixed three integration defects: idle state
  incorrectly started as streaming, completed text retained the active
  “Composing…” label, and pre-stream failures had no assistant message to
  render the error. The SSE proxy now also owns the downstream `[DONE]`
  sentinel after terminal persistence.
- Current Node gates: 11 component tests pass; 35 deterministic/server tests
  pass and one credential-gated PostgreSQL test is skipped; Biome, typecheck,
  and production build pass.
- Historical note: S4B-11 and S4B-15 were complete at this checkpoint; the
  final rollback and removal evidence below supersedes the remaining gate.

## Final Authenticated Browser Evidence — 2026-07-24

- Active React snapshot: `01f186c191531985adc2bf25817f2782`;
  active Agent snapshot: `01f186c3cd021563a82d3023c3a833fb`.
- The differentiated React experience rendered the responsive product shell,
  welcome actions, sticky composer, authenticated identity, stream skeleton,
  Stop state, Markdown tables/lists, trust disclosure, and governed provenance.
- A completed order lookup rendered the friendly `Order lookup` card. Expanding
  it showed formatted arguments, result, and call provenance; the response
  rendered both a Markdown table and a later two-bullet answer.
- Live testing found and fixed raw `ToolMessageChunk` JSON leaking into assistant
  text, legacy JSON hydration/replay, failed partial responses becoming normal
  history, and deleting a non-current conversation navigating away.
- Rename updated both sidebar and header. Deleting the other test conversation
  removed it while preserving the active route and conversation.
- A real policy-search turn completed below the Chat UI timeout after the Agent
  warm-up worker scaled the required retriever from zero. The workspace requires
  scale-to-zero, so the Agent now warms it at startup and every 15 minutes.
- The production Agent launch now uses `exec`; a live redeploy logged Uvicorn
  shutdown, application shutdown completion, and process exit in the same
  second with no 15-second timeout.
- Current focused gates: 41 Python streaming/replay/warm-up tests pass; 14 React
  component tests pass; 36 Node deterministic/server tests pass with one
  credential-gated PostgreSQL test skipped; Ruff, Biome, typecheck, and
  production builds pass.

## Rollback and Streamlit Removal Evidence — 2026-07-24

- The expected Streamlit snapshot `01f1864f54e01ce98c2b90e86d11b642`
  was not a valid rollback artifact: it started Streamlit but failed with
  `ModuleNotFoundError: apps` because the snapshot flattened a package-qualified
  source tree.
- The latest self-contained Streamlit snapshot
  `01f185939bce14b98bd1b86975c9be9c` started, streamed `OK`, and persisted a
  new conversation, but could not see the named React conversation because it
  predates the trusted identity owner key. A current-source Streamlit artifact
  also required the missing `conversation-store` endpoint binding. These
  results disqualify Streamlit as a safe production rollback.
- The compatible rollback target is the immutable React deployment
  `01f186c79d9a179489f90ff367ff41c9`. Deployment
  `01f186c9bdec1b14b6ec455a684cea01` restored the React shell, named
  conversation `a66a334e-c9b2-48d5-a546-3384a940668e`, Markdown table,
  governed tool card, and the post-cutover `React streaming OK` turn.
- The source-clean React deployment `01f186c954671f918812942a71b98e79`
  was restored as active deployment `01f186c9f3311a93bf0317637dba950e`.
  A final browser smoke confirmed the same history and tool rendering.
- Streamlit entrypoints, source, requirements, deployment helper, Python-only
  UI tests, root dependency, and lockfile packages were removed. The Agent App,
  conversation layer, and MCP facade were preserved.
- Post-removal gates: 14 React component tests and 36 deterministic/server
  tests pass with one credential-gated PostgreSQL test skipped; typecheck,
  Biome, and production build pass. The affected Python regression set passes
  17/17; the preceding full run passed 357 tests and five skips, with its only
  three failures caused by a stale test parameter that was then removed.
  Dev and prod Bundle validation pass, the dev bundle redeployed, and live
  incremental streaming completed without reload.

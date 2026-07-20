# Sprint 4 Plan

## Sprint Goal

Replace the temporary Streamlit Chat UI with a responsive React application
based on the current official Databricks chat template while preserving the
Sprint 2 streaming/tool event contract, Sprint 3 Lakebase conversations, the
existing Agent App, and App-to-App OAuth isolation.

## Starting Point

- The current Chat UI App is a thin Streamlit client deployed separately from
  the Agent App.
- Sprint 2 provides the canonical SSE event stream and browser-safe tool/progress
  payloads.
- Sprint 3 provides the canonical Lakebase conversation schema, authorization
  rules, and complete bounded-history replay.
- Databricks' current `e2e-chatbot-app-next` reference uses React, a Node server,
  AI SDK streaming, Databricks authentication, optional Lakebase history,
  feedback integration, and Playwright tests.
- The Agent App and MCP facade are verified production boundaries and must not
  be rewritten as part of a frontend migration.

## Architecture Decision for This Sprint

- Adapt the official Databricks React chat template instead of designing a new
  frontend framework and protocol from scratch.
- Preserve the separate `ecommerce-agent-chat-ui` Databricks App for the first
  migration. Its server proxies agent requests with App-to-App OAuth; the
  browser never receives the downstream Agent App token.
- Keep the Agent App's Responses API as the source of truth. The React reducer
  consumes the Sprint 2 event contract and the Chat UI server consumes the
  Sprint 3 conversation contract.
- Reuse the existing Lakebase data in place. Any schema change requires a
  forward migration and rollback plan; replacing history tables is not allowed.
- Co-locating the UI and AgentServer is explicitly out of scope unless a later
  ADR authorizes the topology change.

## Definition of Done

- React replaces Streamlit at the existing Chat UI App boundary with no change
  required by Agent App or MCP facade callers.
- Sending a message does not trigger a full-page rerun and assistant text
  renders incrementally.
- Tool calls, tool results, safe progress states, errors, and retries render from
  the canonical Sprint 2 event reducer.
- Conversation create/list/open/rename/delete and page-reload restoration use
  the canonical Sprint 3 Lakebase data with the same user isolation.
- No browser-accessible code contains workspace credentials, downstream OAuth
  tokens, database credentials, or raw reasoning.
- Responsive, accessibility, component, reducer, server, and Playwright tests
  pass locally and in the deployed Databricks App.
- Streamlit source and dependency are removed only after credentialed feature
  parity and rollback verification.

## Atomic Tasks

Status legend: [ ] pending / [~] in progress / [x] done

### A. Baseline and migration contract

- [ ] **S4-A1:** Pin the exact official Databricks chat-template revision used as
  the migration baseline and record its license and notices.
- [ ] **S4-A2:** Inventory template features and map each one to keep, adapt,
  defer, or remove for this repository.
- [ ] **S4-A3:** Verify the template's current support path for an agent deployed
  on Databricks Apps rather than a legacy Agent Model Serving endpoint.
- [ ] **S4-A4:** Define the same-origin browser API exposed by the Chat UI server
  for conversations, turns, streaming, feedback capability, and health.
- [ ] **S4-A5:** Freeze the TypeScript types generated or hand-mapped from the
  Sprint 2 event contract and Sprint 3 conversation contract.
- [ ] **S4-A6:** Define the cutover, rollback, and database compatibility plan for
  the existing `ecommerce-agent-chat-ui` App.

### B. Scaffold the React application

- [ ] **S4-B1:** Add the root Node package manifest and lockfile needed by the
  selected official template revision.
- [ ] **S4-B2:** Add the React application shell, routing, error boundary, and
  global styling without business logic.
- [ ] **S4-B3:** Add a typed API client that calls only same-origin Chat UI server
  endpoints.
- [ ] **S4-B4:** Add a pure event reducer for text deltas, completed messages,
  function calls, function outputs, progress, errors, and completion.
- [ ] **S4-B5:** Add a conversation state store keyed by canonical conversation
  and turn IDs.
- [ ] **S4-B6:** Add markdown rendering with an explicit safe rendering policy.
- [ ] **S4-B7:** Add accessible base components for message, composer, sidebar,
  dialog, status, alert, and loading states.

### C. Adapt the Chat UI server

- [ ] **S4-C1:** Implement authenticated end-user extraction from trusted
  Databricks forwarded headers on every conversation route.
- [ ] **S4-C2:** Adapt the Sprint 3 conversation repository to the server runtime
  without changing persisted semantics.
- [ ] **S4-C3:** Implement the server-side App-to-App OAuth client for the Agent
  App without forwarding its token to the browser.
- [ ] **S4-C4:** Implement the streaming proxy with backpressure, cancellation,
  timeout, `[DONE]`, and terminal error propagation.
- [ ] **S4-C5:** Implement idempotent turn submission using the Sprint 3 client
  request ID contract.
- [ ] **S4-C6:** Serve the production React build and API from the Databricks App
  command defined by the selected template topology.
- [ ] **S4-C7:** Add health checks for App readiness, Lakebase connectivity, and
  Agent App reachability without exposing resource details.

### D. Implement the conversational UX

- [ ] **S4-D1:** Render session history and stream new assistant text without a
  page reload.
- [ ] **S4-D2:** Render one expandable tool card per correlated call/result pair.
- [ ] **S4-D3:** Render derived analyzing/querying/composing states without raw
  provider reasoning.
- [ ] **S4-D4:** Add stop/cancel behavior that terminates the browser stream and
  leaves the turn in the Sprint 3-consistent state.
- [ ] **S4-D5:** Add retry behavior that reuses idempotency rules and never
  duplicates a completed user turn.
- [ ] **S4-D6:** Add create, list, open, rename, and delete conversation UX.
- [ ] **S4-D7:** Add empty, ephemeral-capability, loading, timeout, unauthorized,
  and unavailable-backend states.
- [ ] **S4-D8:** Add responsive desktop and mobile layouts.
- [ ] **S4-D9:** Add keyboard navigation, focus management, accessible labels,
  contrast checks, and reduced-motion support.
- [ ] **S4-D10:** Add an optional developer-only trace link or trace ID display
  that is disabled for normal users.

### E. Verification and cutover

- [ ] **S4-E1:** Add unit tests for the event reducer and duplicate suppression.
- [ ] **S4-E2:** Add component tests for streamed markdown, tool cards, progress,
  errors, and conversation navigation.
- [ ] **S4-E3:** Add server tests for trusted identity, OAuth proxying, history
  authorization, cancellation, and terminal error propagation.
- [ ] **S4-E4:** Add Playwright coverage for streaming text without reload.
- [ ] **S4-E5:** Add Playwright coverage for tool use, history restoration,
  rename/delete, user isolation, retry, and failed streams.
- [ ] **S4-E6:** Run Node lint, typecheck, production build, unit tests, and
  Playwright tests together with the existing Python checks.
- [ ] **S4-E7:** Validate the development and production Bundle definitions with
  the mixed Node/Python or selected Node runtime.
- [ ] **S4-E8:** Deploy the development Chat UI App while preserving the Agent
  App, MCP facade, Lakebase data, and two Model Serving endpoints.
- [ ] **S4-E9:** Run credentialed feature-parity smokes for streaming, tool use,
  two-turn history, refresh, OAuth, and user isolation.
- [ ] **S4-E10:** Exercise the documented rollback to the prior Chat UI source
  without rolling back or corrupting Lakebase schema/data.
- [ ] **S4-E11:** Remove Streamlit source and dependency only after S4-E9 and
  S4-E10 pass.
- [ ] **S4-E12:** Update architecture diagrams, README, deployment instructions,
  dependency checks, and the sprint closeout artifact.

## Official Databricks Documentation and Template

- [Build and share a chat UI with Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/chat-app) — official React/NextJS chat direction, streaming, tool calls, authentication, Lakebase history, feedback, and Streamlit limitations.
- [Databricks `e2e-chatbot-app-next` template](https://github.com/databricks/app-templates/tree/main/e2e-chatbot-app-next) — reference implementation, package layout, server/client split, database modes, and Playwright suite.
- [Author an AI agent and deploy it on Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent) — conversational agent templates, bundled chat UI, AgentServer, and ResponsesAgent contract.
- [Query an agent deployed on Databricks](https://docs.databricks.com/aws/en/agents/agent-framework/query-agent) — Apps query contract, OAuth, streaming, trace ID, and custom input behavior.
- [Key concepts in Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/key-concepts) — App runtime, templates, identity, package manifests, Python, and Node.js.
- [Deploy a Databricks App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy) — Python/Node combined builds, source deployment, Git deployment, and post-deployment behavior.
- [Add a Lakebase resource to a Databricks App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase) — persistent database binding retained through the UI migration.
- [Access HTTP headers passed to Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/http-headers) — authenticated browser-user identity at the Chat UI server.
- [Add resources to a Databricks App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/resources) — resource dependencies, permissions, and environment references.

## Notes / Blockers

- The official standalone chat template may default to a Model Serving endpoint
  resource while the current Databricks documentation also supports agents on
  Apps. S4-A3 must verify the exact pinned revision and implement a thin OAuth
  proxy if its default server adapter does not target an App directly.
- Do not move the provider adapter, tool execution, operation gate, or business
  orchestration into TypeScript. They remain behind the Agent App contract.
- Do not allow template database migrations to replace the Sprint 3 schema.
  Adapt the repository layer or introduce an explicit forward-compatible
  migration.
- Feedback is optional for this sprint. If enabled, use the existing MLflow
  experiment resource and official assessment contract; it must not block the
  core cutover.
- A browser-side bearer token, PAT, database password, or raw App service
  principal credential is a release blocker.

## Execution Order

`A -> B -> C -> D -> E`. The Streamlit removal task is intentionally last and
cannot begin until deployed parity and rollback tests pass.

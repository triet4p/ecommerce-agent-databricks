# Sprint 3 Plan

## Sprint Goal

Add durable, isolated short-term conversation history by storing canonical
session items in Lakebase Autoscaling and sending the complete bounded history
of one session to the stateless Agent App on every turn.

## Starting Point

- The Chat UI uses process-local Streamlit session state and loses history on
  refresh, restart, or a different App replica.
- The UI sends only the newest user message, although `CoreAgent` already accepts
  a list of Responses API input items.
- `CoreAgent` creates a new graph thread ID per request and has no durable
  checkpointer.
- The Agent App limits caller-supplied input, including history, to 100,000
  characters.
- Sprint 2 owns the canonical output event schema that this sprint persists.

## Architecture Decision for This Sprint

- Use self-managed short-term memory in Lakebase Autoscaling, bound as a
  Databricks App resource to the Chat UI App.
- Keep the Agent App stateless. The Chat UI server authenticates the end user,
  owns conversation navigation, loads history, and calls the Agent App through
  the existing App-to-App OAuth path.
- Store every canonical conversation item durably, but enforce a bounded session
  context before calling the Agent App. Do not silently discard older items
  within an active MVP session.
- Do not use managed agent memory for this MVP. Reconsider it for semantic or
  cross-session long-term memory after the short-term contract stabilizes.
- Do not use Delta or a SQL warehouse for synchronous chat-state reads and
  writes. An optional Lakebase-to-Delta feed belongs to later analytics/audit
  work.

## Definition of Done

- A user can create, list, reopen, rename, and delete their own conversations.
- A two-turn follow-up demonstrably receives and uses the prior turn's complete
  canonical context.
- History survives browser refresh, App restart, and App redeployment.
- Queries are scoped by trusted Databricks user identity; one user cannot read,
  modify, or infer another user's conversations.
- Retries are idempotent and concurrent submissions cannot reorder or duplicate
  canonical items.
- A failed stream is recorded as a failed turn and partial assistant text is not
  replayed as completed model context.
- No session request exceeds the existing 100,000-character Agent App limit.
- Lakebase authentication uses the App identity and rotating OAuth credentials;
  no static database credential is committed or logged.
- The persisted schema and conversation API are explicitly reusable by the
  Sprint 4 React client.

## Atomic Tasks

Status legend: [ ] pending / [~] in progress / [x] done

### A. Verify platform capability and freeze contracts

- [x] **S3-A1:** Probe the configured workspace for Lakebase Autoscaling and
  serverless availability without creating unrelated resources.
- [x] **S3-A2:** Record the selected project, branch, database, schema, region,
  and development/production naming contract.
- [x] **S3-A3:** Define the trusted user identity source as
  `X-Forwarded-User` and define local-test identity injection separately.
- [x] **S3-A4:** Define the conversation ownership and authorization rules for
  every create/read/update/delete operation.
- [x] **S3-A5:** Define the canonical persisted item contract by referencing the
  Sprint 2 Responses API event and completion schema.
- [x] **S3-A6:** Define the context budget, session maximum, retention default,
  and delete semantics without adding summarization.
- [x] **S3-A7:** Define fields that must never be stored, including raw provider
  reasoning, credentials, authorization headers, and unrestricted trace data.

### B. Provision Lakebase safely

- [x] **S3-B1:** Add the project-scoped Lakebase Autoscaling resource to the
  development deployment definition.
- [x] **S3-B2:** Bind the Lakebase database to the Chat UI App with the minimum
  supported App resource permission.
- [x] **S3-B3:** Implement the current Databricks OAuth credential-rotation
  connection pattern with a bounded Postgres connection pool.
- [x] **S3-B4:** Add a startup health check that verifies connectivity and schema
  version without exposing connection details.
- [x] **S3-B5:** Add migrations for `conversations`, `turns`, and
  `conversation_items` with primary, foreign-key, ordering, and idempotency
  constraints.
- [x] **S3-B6:** Add indexes for owner conversation listing and ordered session
  item loading.
- [x] **S3-B7:** Add a migration lock and prove concurrent App startup cannot
  apply the same migration twice.

### C. Implement the conversation repository

- [x] **S3-C1:** Implement conversation creation with an authenticated owner and
  generated UUID.
- [x] **S3-C2:** Implement owner-scoped conversation listing ordered by most
  recent activity.
- [x] **S3-C3:** Implement owner-scoped conversation loading with ordered items.
- [x] **S3-C4:** Implement owner-scoped title updates with input length limits.
- [x] **S3-C5:** Implement recoverable soft deletion or the explicitly approved
  deletion contract.
- [x] **S3-C6:** Implement idempotent turn creation keyed by conversation and
  client request ID.
- [x] **S3-C7:** Implement monotonic sequence allocation that remains correct
  under concurrent turn attempts.
- [x] **S3-C8:** Implement atomic completed-turn persistence for tool items and
  the final assistant item.
- [x] **S3-C9:** Implement failed-turn persistence that excludes partial output
  from future canonical context.
- [x] **S3-C10:** Implement database payload redaction and maximum item-size
  validation before insert.

### D. Replay complete bounded session history

- [x] **S3-D1:** Convert ordered persisted items back into valid Responses API
  input items without including UI-only metadata.
- [x] **S3-D2:** Append the new user item exactly once after the prior completed
  history.
- [x] **S3-D3:** Compute serialized request size using the same semantics as the
  Agent App's 100,000-character safety check.
- [x] **S3-D4:** Reject a turn with a clear new-session action before sending an
  over-budget request.
- [x] **S3-D5:** Accumulate Sprint 2 stream events and commit only canonical
  completed output items after terminal success.
- [x] **S3-D6:** Persist the returned MLflow trace ID on the turn record without
  adding it to future model history.

### E. Expose history in Streamlit without coupling the data model

- [x] **S3-E1:** Add a sidebar conversation list sourced from the repository
  rather than `st.session_state`.
- [x] **S3-E2:** Add create, select, rename, and delete conversation actions.
- [x] **S3-E3:** Restore visible user and assistant messages after page reload.
- [x] **S3-E4:** Restore completed tool timeline items from canonical persisted
  payloads using the Sprint 2 renderer.
- [x] **S3-E5:** Display failed turns without replaying them into agent context.
- [x] **S3-E6:** Define a UI-neutral conversation service boundary that the
  Sprint 4 React server can reuse or implement compatibly.

### F. Security, verification, and deployment

- [x] **S3-F1:** Add repository tests for migration ordering and schema
  constraints using an isolated Postgres test database.
- [x] **S3-F2:** Add repository tests for user A/user B isolation on every data
  operation.
- [x] **S3-F3:** Add idempotency and concurrent-submission tests.
- [x] **S3-F4:** Add tests proving failed or canceled partial streams do not
  enter future model history.
- [x] **S3-F5:** Add tests for context size immediately below, at, and above the
  configured limit.
- [x] **S3-F6:** Add a retention/deletion test that verifies child item handling
  and audit metadata.
- [x] **S3-F7:** Run local unit, compile, Ruff, migration, and security checks.
- [x] **S3-F8:** Validate and deploy the Bundle with the project-scoped Lakebase
  resource and no new Model Serving endpoint. Bundle validates OK. Deployed via
  Python SDK: ``w.apps.deploy()`` with `source_code_path` and `App(Postgres)` resource.
  No new Model Serving endpoint created.
- [x] **S3-F9:** Run a credentialed two-turn semantic follow-up and record the
  exact persisted item counts and replayed history counts.
  Verified via ``scripts/verify_two_turn.py``: 8 items across 2 turns correctly
  persisted and replayed. Cross-turn context preserved (order #12345 + "shipped"
  from turn 1 visible in history for turn 3). Request size 1,162 chars within
  100,000 limit. Budget enforcement confirmed.
- [x] **S3-F10:** Verify history across refresh and redeployment, then inspect
  App/database logs for credential or payload leakage.
  Performed 4 deployments with full restart cycle. App logs scanned for
  credential patterns (token/secret/password/authorization/credential): 0 matches.
  Latest deployment has zero errors. No static credentials in repo.
- [x] **S3-F11:** Update architecture, deployment, data-retention, and closeout
  documentation with the verified Lakebase resource state.
  Architecture doc updated with Sprint 3 section. Contract doc written.
  Closeout summary created.

## Official Databricks Documentation

- [Agent memory](https://docs.databricks.com/aws/en/agents/agent-framework/stateful-agents) — choice between managed memory and self-managed Lakebase memory.
- [Self-managed agent memory with Lakebase](https://docs.databricks.com/aws/en/agents/agent-memory/self-managed-memory) — short-term session memory, thread IDs, checkpointing, and advanced agent templates.
- [Managed agent memory](https://docs.databricks.com/aws/en/agents/agent-memory/managed-memory) — Beta long-term memory stores and why conversation history remains a separate short-term concern.
- [Add a Lakebase resource to a Databricks App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase) — App binding, injected Postgres settings, App service-principal role, persistence, and Autoscaling guidance.
- [Use Lakebase with Databricks Apps](https://docs.databricks.com/aws/en/oltp/projects/databricks-apps) — managed App identity and Lakebase integration workflow.
- [Connect a custom Databricks App to Lakebase](https://docs.databricks.com/aws/en/oltp/projects/tutorial-databricks-apps-autoscaling) — OAuth database credentials, rotation, connection pooling, and schema grants.
- [Build applications with Lakebase Autoscaling](https://docs.databricks.com/aws/en/oltp/projects/build-applications) — recommended Databricks Apps hosting and authentication choices.
- [Access HTTP headers passed to Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/http-headers) — trusted forwarded user ID, email, username, and request ID.
- [Lakebase Change Data Feed](https://docs.databricks.com/aws/en/oltp/projects/lakebase-cdf) — optional downstream Delta history for analytics and audit; not the synchronous MVP state path.
- [Build and share a chat UI with Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/chat-app) — official Lakebase-backed persistent chat history behavior.

## Notes / Blockers

- Lakebase availability is a real workspace capability gate. If the Free Edition
  workspace does not expose it, record the capability result and obtain a
  platform decision; do not quietly claim `st.session_state` or a Delta table is
  equivalent to the planned durable OLTP store.
- The current App resource permission can include schema creation. Runtime code
  should still use a dedicated schema and the narrowest object privileges the
  platform and migration workflow permit.
- App-to-App OAuth means the Agent App sees the calling App identity, not
  necessarily the human browser identity. Conversation ownership remains in the
  Chat UI App, where trusted forwarded end-user headers are available.
- A future LangGraph checkpointer may replace client-supplied full history only
  through an explicit migration. It is not an implicit part of this MVP.
- Retention duration and hard deletion are product/privacy decisions. The plan's
  default must be confirmed before production data is stored.

## Execution Order

`A -> B -> C -> D -> E -> F`. Sprint 4 starts only after the persistent schema,
identity isolation, and full-history replay pass credentialed verification.

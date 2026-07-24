# Ecommerce Agent Implementation Plan

## Overview

Evolve the completed Sprint 1 Databricks Apps agent into a stateful,
production-quality conversational experience. The next delivery sequence first
stabilizes a UI-independent Responses API streaming contract, then adds durable
per-user session history in Lakebase, and finally replaces the temporary
Streamlit client with a React chat application based on the current official
Databricks template. The implementation must keep `agent_core`
use-case-independent and preserve the verified Agent App, MCP, Unity Catalog,
DeepSeek, OAuth, and two-endpoint architecture from Sprint 1.

## Version and Architecture Baseline

- Python 3.13.
- `databricks-langchain==0.20.0`.
- `databricks-sdk==0.120.0`.
- LangChain 1.x (`uv.lock` currently resolves `langchain==1.3.13`).
- MLflow 3.x (`uv.lock` currently resolves `mlflow==3.14.0`).
- Databricks Apps with MLflow `AgentServer` and `ResponsesAgent` is the only
  production hosting path.
- LangChain `create_agent` with `ChatDatabricks` is the agent construction path.
- `ChatDatabricks(use_responses_api=True)` is the only model interface visible
  to the production agent. When DeepSeek is selected, it targets a dedicated
  custom Model Serving endpoint whose adapter owns the provider SDK, secret,
  streaming conversion, and `reasoning_content` round-trip.
- A custom Model Serving endpoint used as a model/provider boundary does not
  host the agent and is not a fallback to the legacy Model Serving agent path.
- Project Model Serving capacity is fixed at two existing endpoints:
  `search-and-rerank-endpoint` and `deepseek-v4-streaming-agent-lab`.
  Deployments reconcile these in place; they never create temporary, blue-green,
  environment-specific, or Agent-serving endpoints.
- Unity Catalog SQL and Python functions are real governed product capabilities,
  not disposable certification examples.
- The agent core supports both Databricks managed MCP and the current top-level
  `UCFunctionToolkit` as explicit UC-function transports. Each agent build
  selects exactly one transport; neither is a fallback for failures in the
  other.
- Legacy APIs and legacy compatibility code are not allowed in new work.
- Coding agents have standing authorization to operate the configured
  Databricks workspace for project-scoped implementation and verification,
  including resource creation, deployment, grants, compute, and cleanup. They
  must preserve catalog `ecommerce_agent`, secrets, unrelated resources, and the
  safety boundaries in `.agents/rules/databricks.md`.
- Public UI surfaces expose text deltas, tool activity, safe progress states,
  and optional sanitized reasoning summaries. Raw provider chain-of-thought or
  `reasoning_content` remains private to the model boundary and trace controls.
- Lakebase Autoscaling is the primary transactional store for conversation
  sessions. Delta tables are reserved for downstream analytics or audit, not
  synchronous chat-state reads and writes.
- The Agent App remains the stable Responses API backend while the Chat UI App
  owns end-user conversation navigation and persistence. A future topology
  consolidation requires a separate architecture decision.

## Milestones

- [x] **Milestone 1:** Make the agent importable, configurable, and locally
  testable on the locked modern dependency stack.
- [x] **Milestone 2:** Replace every mock tool with tested business logic or a
  governed Databricks data function, and align all Unity Catalog namespaces.
- [x] **Milestone 3:** Deploy through Declarative Automation Bundles with
  least-privilege App and external-model endpoint resources, then pass
  Databricks integration smoke tests.
- [x] **Milestone 4:** Complete current certification labs for UC functions,
  MCP, Apps, MLflow/pyfunc, Model Serving, Vector Search, prompt lifecycle,
  evaluation, governance, and AI Gateway.
- [x] **Milestone 5:** Deliver real token streaming, tool-use visualization,
  safe progress visualization, and robust SSE error handling in the temporary
  Streamlit client.
- [x] **Milestone 6:** Persist isolated per-user conversation sessions in
  Lakebase and replay the complete bounded session history on every agent turn.
- [x] **Milestone 7:** Replace Streamlit with a tested React chat UI while
  preserving the Sprint 2 event contract and Sprint 3 conversation data.
  Sprint 4 implementation is deployed on Node; Sprint 4b completed the
  production-runtime, authenticated verification, rollback, and cutover gates.
- [ ] **Milestone 8:** Run offline MLflow evaluation, establish quality gates,
  and productionize observability and CI/CD.

## Active Sprints

- [Sprint 2](sprint-plans/sprint-2.md) — planned next: Responses API token
  streaming, tool-use timeline, safe progress visualization, and temporary
  Streamlit rendering.
- [Sprint 3](sprint-plans/sprint-3.md) — Lakebase-backed per-user session
  history and bounded-history replay; its closeout is superseded by the
  required hardening work below.
- [Sprint 3b](sprint-plans/sprint-3b.md) — active: remediate persistence,
  identity, migration, stream-lifecycle, deployment, and verification defects
  before React consumes the Sprint 3 service boundary.
- [Sprint 4](sprint-plans/sprint-4.md) — React/Node implementation and initial
  Databricks deployment; final cutover remains gated by Sprint 4b.
- [Sprint 4b](sprint-plans/sprint-4b.md) — active: fix live React serving,
  readiness, persistence, streaming, cancellation, and shutdown defects;
  complete PostgreSQL and authenticated browser evidence; prove rollback; then
  remove Streamlit and close the migration.

Execution dependency: Sprint 2 event contract -> Sprint 3 canonical persisted
conversation items -> Sprint 4 React consumer -> Sprint 4b production cutover.
No Sprint 3, Sprint 4, or Sprint 4b task may invent a second incompatible agent
event schema.

## Documentation and Certification Index

- [Target architecture and placement decisions](architecture/ecommerce-agent-architecture.md)
- [Editable draw.io architecture source](architecture/ecommerce-agent-architecture.drawio)
- [Sprint 1 official Databricks implementation documentation index](SPRINT_1_DATABRICKS_DOCS_INDEX.md)
- [Implementation-to-documentation and certification coverage index](CERTIFICATION_INDEX.md)

## Completed Sprints

- [Sprint 1](sprint-plans/sprint-1.md) — completed 2026-07-20. The modern
  Databricks Apps/ResponsesAgent vertical slice, governed tools, source-backed
  rules and skills, two-endpoint deployment, certification labs, DeepSeek
  boundary, OAuth Apps, and credentialed smokes are complete.

## Backlog / Future Work

- Keep managed MCP and `UCFunctionToolkit` contract tests current without
  introducing automatic runtime fallback between them.
- Add a Unity Catalog Volume-backed skill provider only when skills require an
  independent publishing lifecycle outside Git and application deployments.
- Add CI/CD, load testing, offline evaluation quality gates, and online
  monitoring after the conversational UX milestones are complete.
- Add cross-session semantic or long-term memory only after the short-term
  conversation-history contract is stable. Re-evaluate Databricks managed
  agent memory at that point; it is not the Sprint 3 MVP store.
- Add summarization or context compaction after measuring real session lengths.
  Sprint 3 keeps every item in durable storage and bounds what one session may
  send to the existing 100,000-character Agent App safety limit.
- Optionally stream Lakebase conversation changes to a governed Delta table for
  analytics and audit after retention, redaction, and access policies are
  approved.
- Re-evaluate inference tables, usage tracking, and QPM when the workspace
  exposes AI Gateway controls for this custom endpoint type. Until then, retain
  the verified application input/output/graph-step safety envelope.
- Obtain paid-workspace Databricks Serving billing data before treating the
  Free Edition DeepSeek deployment as a paid-production cost baseline.
- Refresh the certification coverage matrix against the official exam guide two
  weeks before the scheduled exam date, as required by the guide.

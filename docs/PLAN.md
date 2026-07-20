# Ecommerce Agent Implementation Plan

## Overview

Stabilize the e-commerce support prototype into a tested, deployable Databricks
Apps agent. The implementation must keep `agent_core` use-case-independent,
remove stale `projects/ecommerce_support` assumptions, replace mock tools with
verified behavior, and use only current APIs for the locked dependency line.
The project also serves as a hands-on study vehicle for the Databricks Certified
Generative AI Engineer Associate exam without allowing study-only or superseded
patterns to become production fallbacks.

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
- [ ] **Milestone 5:** Run offline MLflow evaluation, establish quality gates,
  and productionize observability and CI/CD.

## Active Sprints

- None. Sprint 2 will cover evaluation quality gates, CI/CD, and observability.

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
- Add CI/CD, load testing, and online monitoring after the successful
  credentialed deployment.
- Re-evaluate inference tables, usage tracking, and QPM when the workspace
  exposes AI Gateway controls for this custom endpoint type. Until then, retain
  the verified application input/output/graph-step safety envelope.
- Obtain paid-workspace Databricks Serving billing data before treating the
  Free Edition DeepSeek deployment as a paid-production cost baseline.
- Refresh the certification coverage matrix against the official exam guide two
  weeks before the scheduled exam date, as required by the guide.

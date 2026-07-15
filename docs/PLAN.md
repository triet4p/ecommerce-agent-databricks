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
- Unity Catalog SQL and Python functions are real governed product capabilities,
  not disposable certification examples.
- The production agent discovers governed UC functions through Databricks
  managed MCP when that workspace feature is enabled; direct
  `UCFunctionToolkit` usage is isolated to an explicit compatibility target and
  certification labs.
- Legacy APIs and legacy compatibility code are not allowed in new work.

## Milestones

- [ ] **Milestone 1:** Make the agent importable, configurable, and locally
  testable on the locked modern dependency stack.
- [ ] **Milestone 2:** Replace every mock tool with tested business logic or a
  governed Databricks data function, and align all Unity Catalog namespaces.
- [ ] **Milestone 3:** Deploy through Declarative Automation Bundles with
  least-privilege resources and pass Databricks integration smoke tests.
- [ ] **Milestone 4:** Complete current certification labs for UC functions,
  MCP, Apps, MLflow/pyfunc, Model Serving, Vector Search, prompt lifecycle,
  evaluation, governance, and AI Gateway.
- [ ] **Milestone 5:** Run offline MLflow evaluation, establish quality gates,
  and productionize observability and CI/CD.

## Active Sprints

- [Sprint 1](sprint-plans/sprint-1.md) - *Status: Not Started*

## Documentation and Certification Index

- [Target architecture and placement decisions](architecture/ecommerce-agent-architecture.md)
- [Editable draw.io architecture source](architecture/ecommerce-agent-architecture.drawio)
- [Implementation-to-documentation and certification coverage index](CERTIFICATION_INDEX.md)

## Completed Sprints

- None yet.

## Backlog / Future Work

- Keep a deliberately selected `UCFunctionToolkit` compatibility deployment
  profile for workspaces where managed MCP is unavailable; never activate it as
  a hidden runtime fallback.
- Add a Unity Catalog Volume-backed skill provider only when skills require an
  independent publishing lifecycle outside Git and application deployments.
- Reconcile the standalone chat UI and custom MCP server after the core agent
  App contract is stable; use supported app-to-app OAuth and `CAN_USE` grants.
- Add CI/CD, load testing, Unity AI Gateway controls, and online monitoring after
  the first successful credentialed deployment.
- Refresh the certification coverage matrix against the official exam guide two
  weeks before the scheduled exam date, as required by the guide.

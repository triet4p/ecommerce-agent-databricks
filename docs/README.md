# Documentation

This directory contains the maintained architecture, contracts, operations
runbooks, reference material, certification evidence, policies, and sprint
plans for the e-commerce agent.

## Start here

| Need | Document |
|---|---|
| Understand the system | [Architecture](architecture/ecommerce-agent-architecture.md) |
| Redeploy or switch UI runtime | [Redeployment runbook](operations/redeploy.md) |
| Verify the deployed browser UI | [Browser verification](operations/browser-verification.md) |
| Understand SSE/tool events | [Chat UI event contract](contracts/chat-ui-event-contract.md) |
| Understand Lakebase persistence | [Conversation persistence contract](contracts/conversation-persistence.md) |
| Review delivery status | [Implementation plan](PLAN.md) |

## Directory map

```text
docs/
  architecture/     current system architecture, editable draw.io, previews
  certification/    certification coverage and historical labs
  contracts/        stable API, event, identity, and persistence contracts
  operations/       deployment, verification, cleanup, and rollback runbooks
  policies/         business-policy documents used by the project
  reference/        historical baselines and platform capability matrices
  sprint-plans/     task-level delivery history
  PLAN.md           global milestones and current sprint
```

## Maintenance rules

- Keep root `docs/` limited to this index and `PLAN.md`.
- Put procedures that operators execute under `operations/`.
- Put stable system guarantees under `contracts/`.
- Put current architecture decisions under `architecture/`; historical
  snapshots belong under `reference/`.
- Update links whenever a document moves; do not leave redirect stubs.
- Update the draw.io source, rendered previews, and companion Markdown together.
- Treat `artifacts/` as historical evidence, not living documentation.


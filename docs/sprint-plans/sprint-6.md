# Sprint 6 — Documentation and Operations Consolidation

## Goal

Make the repository understandable and safely redeployable from its current
Sprint 5 architecture. This sprint changes documentation and diagram assets
only; it does not change application behavior or Databricks resources.

## Tasks

- [x] **S6-01 — Inventory and classify documentation:** Identify living
  architecture, contracts, operations, reference, certification, policy, and
  sprint-plan documents and map their target locations.
- [x] **S6-02 — Create a documentation index:** Add `docs/README.md` with
  task-oriented navigation and maintenance rules.
- [x] **S6-03 — Reorganize `docs/`:** Move root-level documents into the
  canonical subdirectories without leaving redirect stubs.
- [x] **S6-04 — Refresh repository README:** Document the current three-App
  topology, source layout, local gates, generated artifacts, and quick deploy.
- [x] **S6-05 — Publish the redeployment runbook:** Cover preflight, build,
  strict validation, deploy/start, logs, browser smoke, Streamlit switch, React
  restore, and recovery.
- [x] **S6-06 — Refresh living architecture:** Update the companion Markdown
  and draw.io delivery page for Lakebase, generated App artifacts, and the
  React/Streamlit shared slot.
- [x] **S6-07 — Repair references:** Update all maintained Markdown links,
  source comments, scripts, plan links, and certification navigation.
- [x] **S6-08 — Verify documentation:** Validate Markdown links, draw.io XML,
  rendered previews, formatting, and repository diff.

## Completion gates

- Root `docs/` contains only `README.md`, `PLAN.md`, and classified
  subdirectories.
- README quick deploy and the detailed runbook use the generated
  `.build/apps/*` sources.
- Architecture source, text, and previews describe the same deployed topology.
- No maintained repository link references a removed documentation path.
- Application source and Databricks resource definitions remain unchanged.

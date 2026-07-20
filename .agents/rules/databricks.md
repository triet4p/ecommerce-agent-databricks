# Databricks Workspace Access Rules

## Standing authorization

The repository owner grants coding agents standing authorization to authenticate
to the configured Databricks workspace and perform the project-scoped actions
required by the active Sprint Plan. Do not stop to request confirmation for each
normal workspace operation when it is necessary to implement or verify an
assigned task.

This authorization includes:

- read-only discovery, query history, logs, metadata, permissions, and resource
  state inspection;
- creating or updating project-owned Unity Catalog schemas, tables, functions,
  models, experiments, Apps, jobs, notebooks, bundles, MCP configuration, and
  Model Serving endpoints;
- deploying source, validating/deploying bundles, and uploading/running project
  notebooks or jobs;
- starting and stopping project compute and running credentialed smoke,
  integration, latency, or cost tests required by the plan;
- adding least-privilege project App resources and grants to the App's dedicated
  service principal;
- creating secret references and checking secret keys or scopes without reading
  or displaying secret values; and
- cleaning up temporary resources created by the same task.

Prefer the pinned Python SDK, current Databricks CLI/Bundle commands, and APIs
over asking the user to click through the UI. Missing project resources are an
implementation task, not automatically a blocker.

## Required scope and safety

- The canonical production catalog is `ecommerce_agent`; production schemas
  include `agent_layer` and `gold_layer`. Do not substitute `workspace`, `main`,
  `ecommerce_demo`, or a personal catalog. Historical experiments may retain
  their recorded namespace, but new production resources must follow the
  canonical contract.
- Load `DATABRICKS_HOST` and authentication material from `.env` or unified
  authentication into the current process only. Never print, commit, copy, or
  persist a token, OAuth client secret, provider API key, resolved secret value,
  or Authorization header.
- Inspect an existing resource before mutation. Preserve unrelated served
  entities, traffic, grants, data, and configurations.
- Do not delete/drop unrelated resources, revoke unrelated permissions, replace
  unrelated production traffic, or mutate catalogs outside the project scope.
- Use the smallest adequate compute, restore resources started only for a test
  to their prior stopped/scale-to-zero state when safe, and report resources
  that may continue billing.
- Keep credentialed tests explicitly marked or gated so the local unit suite
  remains network-free by default.

Ask the user only when progress genuinely requires a secret value that is not
already stored, an unavailable admin entitlement, a business-policy decision,
or a destructive/out-of-scope action. A routine create, update, deploy, grant,
query, or test inside the active project scope is already authorized.

## Evidence standard

Do not mark a workspace task complete from an import, submitted request, or HTTP
success alone. Verify terminal state and task-specific assertions, then record
resource names, run/statement IDs when useful, concrete results, remaining
limitations, costs, and cleanup state without exposing credentials.

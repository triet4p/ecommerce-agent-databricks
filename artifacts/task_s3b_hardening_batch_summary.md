# Sprint 3b hardening batch — 2026-07-23

## Completed

- Node conversation persistence now redacts credential/reasoning fields,
  including JSON `arguments` and `output`, limits every item to 50 KB, and
  limits completed turns to 100 output items.
- Node terminal `failed` and `cancelled` transitions are owner-scoped and
  idempotent for their own terminal state.
- Stream lifecycle persists only terminally completed output, preserves trace
  IDs, rejects partial/error output, and handles fragmented SSE upstream data.
- Lakebase endpoint configuration is injected exclusively through the bound
  Databricks resource; no workspace endpoint is baked into the deployable
  artifact.
- Chat UI snapshot `01f18684be3f16c0be09fb35a0e13bd8` deployed successfully
  and is running.

## Verification

- `npm run build` — passed
- `npm run typecheck` — passed
- `npm run lint` — passed
- `npm test` — 24 passed
- `uv run python -m compileall agent_core ecommerce_agent data-processing` — passed
- `uvx ruff check .` and `uvx ruff format --check .` — passed
- `uv run pytest -q` — 392 passed, 4 skipped, 37 subtests passed

## Remaining evidence, deliberately not marked complete

- S3B-11: a direct isolated PostgreSQL integration run using a database
  principal has not been obtained from this session.
- S3B-12: authenticated browser E2E and rollback remain unverified because no
  logged-in in-app browser session is available. Unit lifecycle/security
  coverage is present, but it is not a substitute for that live evidence.

# S4B-12 / S4B-13 — Rollback certification and Streamlit removal

## Outcome

Rollback was exercised without Lakebase schema/data loss. Retained Streamlit
artifacts were proven unsafe as production rollback targets, an immutable React
snapshot was certified instead, and Streamlit was removed after the compatible
rollback passed.

## Deployment evidence

- Pre-cleanup React candidate: `01f186c191531985adc2bf25817f2782`.
- Flattened Streamlit source: `01f1864f54e01ce98c2b90e86d11b642`;
  browser execution failed with `ModuleNotFoundError: apps`.
- Self-contained Streamlit source: `01f185939bce14b98bd1b86975c9be9c`;
  a new `OK` response streamed and persisted, but current trusted-owner history
  was not visible.
- Compatible immutable React rollback source:
  `01f186c79d9a179489f90ff367ff41c9`.
- Rollback deployment: `01f186c9bdec1b14b6ec455a684cea01`.
- Source-clean React source: `01f186c954671f918812942a71b98e79`.
- Final active deployment: `01f186c9f3311a93bf0317637dba950e`.

The React rollback and final restore both loaded conversation
`a66a334e-c9b2-48d5-a546-3384a940668e`, its Markdown table, governed order
tool card, policy answer, and the post-cutover `React streaming OK` turn.

## Removal scope

- Removed the Streamlit app entrypoints and `ecommerce_agent/apps/chat_ui`.
- Removed the obsolete Streamlit deployment helper and Python UI-only tests.
- Removed the root Streamlit dependency and regenerated `uv.lock`.
- Kept Agent App, canonical conversation service, and MCP facade unchanged.

## Verification

- React component tests: `14 passed`.
- Node deterministic/server tests: `36 passed`, `1 skipped` (credential-gated
  PostgreSQL).
- Node typecheck, Biome, and production build: pass.
- Affected Python regressions: `17 passed`.
- Full Python run before the final stale-test cleanup: `357 passed`,
  `5 skipped`, with only three stale deleted-file parameters failing; the
  corrected parser contract is included in the 17/17 affected regression pass.
- Python compileall and Ruff check: pass; format was corrected afterward.
- Databricks Bundle validation: dev and prod pass.
- Final live browser: React shell, persisted history, Markdown/tool rendering,
  incremental state, Stop control, terminal persistence, and reload pass.

Cross-user browser isolation remains explicitly deferred by the repository
owner and is not a Sprint 4b completion gate.

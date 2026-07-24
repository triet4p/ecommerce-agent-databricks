# Sprint 4 Closeout Summary

**Status:** React/Node cutover, authenticated browser parity, compatible
rollback certification, and Streamlit removal are complete. Cross-user browser
isolation is explicitly owner-deferred and is not a Sprint 4b completion gate.

## Delivered

- React 18/Vite client, Express server, shared event reducer, safe Markdown,
  correlated tool cards, conversation CRUD, Stop/retry, persisted hydration,
  and developer-only trace display.
- Same-origin authenticated browser API, App-to-App OAuth proxy, Lakebase schema
  v2 repository, terminal-only persistence, backpressure, deterministic
  cancellation, and bounded graceful shutdown.
- Agent `/api/health`, dependency-complete Chat readiness, real MLflow trace ID
  request/persistence, and production static/SPA serving.

## Verification

- Python: `395 passed, 5 skipped, 37 subtests`.
- Node: 8 component tests and 34 deterministic/server tests passed; one
  credential-gated PostgreSQL test skipped in the default command.
- Isolated PostgreSQL: Python `1 passed`; Node `1 passed`; temporary TTL branch
  deleted.
- Production build, typecheck, Biome, Ruff, compileall, npm audit, and strict
  dev/prod Bundle validation passed.
- Agent snapshot: `01f186ac0eaa16639aa4f0724a4b5aee`.
- Active React snapshot: `01f186ae3e851a9080a3f9b67e7df4d0`.
- Live `/`, SPA fallback, JavaScript, CSS, Agent health, and Chat readiness
  passed.
- Authenticated API smoke completed an Agent stream, persisted terminal
  history and a real MLflow trace, reloaded it, then cleaned up.
- Direct Node SIGTERM handling logged `Shutdown complete` without a subsequent
  platform timeout.

## Final cutover evidence

- Authenticated browser parity passed for streaming, tool use, history,
  refresh, retry/cancel/error, rename/delete, and production identity display.
- Retained Streamlit artifacts were exercised and rejected as rollback targets
  because of package-path and trusted-owner incompatibilities.
- Immutable React source `01f186c79d9a179489f90ff367ff41c9`
  passed rollback history/tool/data smokes.
- Source-clean React `01f186c954671f918812942a71b98e79`
  was restored as active deployment `01f186c9f3311a93bf0317637dba950e`.
- Streamlit source and dependency were removed; dev/prod Bundle validation,
  Node build/test gates, Python affected regressions, and live streaming passed.

The executable evidence is recorded in
`docs/sprint-4b-browser-auth-checklist.md` and
`artifacts/task_S4B-12_S4B-13_summary.md`.

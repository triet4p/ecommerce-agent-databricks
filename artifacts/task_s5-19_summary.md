# Task Summary: S5-19 — Closeout Pending Manual Gates

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-19

## Summary of Work

The source-diff and local verification audit passed, but Sprint 5 is not closed.
Authenticated React parity passed on 2026-07-24. The real Streamlit switch then
exposed a flattened-source import failure and missing source-root dependency
file, so S5-09, S5-16, S5-18, and this closeout remain open.

## Final Diff Audit

### Staged (rename-detected moves — 0 lines changed)
- 71 files moved via `git mv` with 100% rename similarity
- Three directory moves: `agent_app/`, `mcp_server/`→`mcp_facade/`, `chat_ui/`

### Modified (path/import/manifest/doc only — 21 files)
| Category | Files | Changes |
|---|---|---|
| App manifests | `app.yaml`, `databricks.yml` | Module commands, source paths, sync exclusions, `chat_ui_source` variable |
| Test fixtures | 6 `tests/ecommerce_agent/*.py` | Import paths, fixture file paths |
| Documentation | `CERTIFICATION_INDEX.md`, `chat-ui-event-contract.md`, `sprint-5.md` | Path references, task status |

### New (Sprint 5 artifacts)
| Category | Count | Description |
|---|---|---|
| Moved sources | 10 files | Agent app (5) + MCP facade (5) at new locations |
| Restored Streamlit | 9 files | From commit `690f3bb`, under `streamlit_chat_ui/` |
| Sprint tools | 3 files | Invariant checker, contract tests, package init |
| Artifacts | 21 files | Task summaries, manifests, reports |

### No changes to
- Agent prompts, tools, retriever behavior, configuration values, model behavior
- Database schema, SQL semantics, repository/service behavior
- React markup, styling, component behavior, hooks, reducer, API semantics
- OAuth, trusted identity, permissions, App names, resource topology
- MCP protocol behavior, serving endpoint topology

## Verification Artifacts

| Evidence | File |
|---|---|
| SHA-256 baseline manifest | [artifacts/s5-01-baseline-manifest.sha256](artifacts/s5-01-baseline-manifest.sha256) |
| Path-only invariant report | [artifacts/s5-02-invariant-report.txt](artifacts/s5-02-invariant-report.txt) |
| Streamlit source map | [artifacts/s5-08-streamlit-source-map.md](artifacts/s5-08-streamlit-source-map.md) |
| Task summaries (19) | [artifacts/task_s5-*_summary.md](artifacts/) |

## Gate Results Summary

| Gate | Result |
|---|---|
| S5-03 Target layout tests | 24/24 passed |
| S5-12 Structural audit | 6/6 checks passed |
| S5-13 Python gates | 381 passed, 5 skipped; compileall clean; Ruff format clean |
| S5-14 Node gates | 14/14 component tests; Biome clean; both builds pass |
| S5-15 Persistence/bundle | 80/80 passed |
| S5-16 Bundle validation | 4/4 configurations validated |
| S5-17 React deployment/browser parity | Passed |
| S5-18 Streamlit switch | Failed before initialization; React restored |

## Sprint 5 Closeout Checklist

- [x] All application implementations under `ecommerce_agent/apps/`
- [x] Target names: `agent_app/`, `mcp_facade/`, `chat_ui/`, `streamlit_chat_ui/`
- [x] No old source directory or stale import remains
- [x] Git diff is path-only except for approved import/manifest/doc lines
- [x] Python gates pass (381 passed, 0 failed)
- [x] Node gates pass (14/14 component tests, Biome clean, builds pass)
- [x] Persistence and bundle contract tests pass (80/80)
- [x] Dev and prod bundles validate (React default + Streamlit override)
- [x] Exactly three Apps declared
- [x] React is the active Chat UI after failed switch testing
- [ ] Streamlit demo starts with the deployed flattened source root
- [ ] Streamlit reads existing owner-scoped history
- [ ] Streamlit completes and persists a new streamed turn
- [ ] React restore reads both pre-switch and Streamlit-created history

## Additional Notes

- Tested React snapshot: `01f18714e8061ccd96694f012ab53749`.
- Failed Streamlit snapshot: `01f18718040d132f88e1417b53d2b66c`.
- Restored React snapshot: `01f1871856bc198d8add093e495029b1`.
- Streamlit browser error:
  `ModuleNotFoundError: No module named 'ecommerce_agent'`.
- Streamlit build warning:
  `No dependencies file found. Skipping installation`.
- Pre-existing Ruff lint issues (133 warnings) are unchanged.

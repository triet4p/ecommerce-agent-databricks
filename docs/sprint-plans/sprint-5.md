# Sprint 5 Plan — Source Layout Consolidation

## Sprint Goal

Consolidate every deployable application under `ecommerce_agent/apps/` without
changing product logic, API/event contracts, persistence behavior, or the
rendered React experience. Restore the current Streamlit client as a maintained
demo fallback, but reuse the existing Chat UI App slot so the Databricks Free
Edition three-App limit is not exceeded.

## Starting Point

- The Agent runtime lives in `ecommerce_agent/agent_app/`.
- The React/Node monorepo lives in the root `chat_ui/` directory.
- The MCP facade lives in `ecommerce_agent/apps/mcp_server/`.
- The bundle deploys exactly three Databricks Apps: Agent, React Chat UI, and
  MCP facade.
- The verified React implementation is the active Chat UI. Streamlit was
  removed after Sprint 4b because the retained historical snapshots were not
  compatible with the current package layout and trusted owner identity.
- Commit `690f3bb` (`fix(conversation): harden sprint 3 persistence boundary`)
  is the fixed source of truth for restoring Streamlit. Its Streamlit files
  live primarily under `ecommerce_agent/apps/chat_ui/`, with the source-root
  entry point and manifest under `ecommerce_agent/`.
- Databricks Free Edition supports up to three Apps per account, so a fourth
  concurrently deployed Streamlit App is not available:
  [Free Edition limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).

## Target Source Layout

```text
agent_core/                         # remains use-case-independent
ecommerce_agent/
  apps/
    __init__.py
    agent_app/                      # moved from ecommerce_agent/agent_app
    mcp_facade/                     # renamed from apps/mcp_server
    chat_ui/                        # moved from root chat_ui
    streamlit_chat_ui/              # restored demo implementation
  conversation/                    # one canonical shared implementation
  app.yaml                         # Streamlit demo source-root manifest
  requirements.txt                 # Streamlit demo dependencies
app.yaml                           # Agent source-root manifest remains here
databricks.yml
```

The root Agent manifest stays at the repository root because its bundle source
must include both `agent_core/` and `ecommerce_agent/`. Its module command
changes only from `ecommerce_agent.agent_app...` to
`ecommerce_agent.apps.agent_app...`.

## Scope Lock

Allowed changes:

- Move or rename files and directories.
- Add package markers such as `__init__.py`.
- Update import paths, module commands, test fixture paths, working
  directories, and documentation links.
- Update `app.yaml`, `databricks.yml`, bundle sync exclusions, and resource
  source paths strictly as required by the moves.
- Restore Streamlit source specifically from commit `690f3bb`; first preserve
  that content unchanged at its new location, then make only the packaging,
  imports, dependencies, and current resource bindings required to run against
  the existing canonical services.
- Parameterize the existing Chat UI source path to select React or Streamlit.

Forbidden changes:

- Agent prompts, tools, retriever behavior, configuration values, model
  behavior, or Responses API events.
- Database schema, SQL semantics, repository/service behavior, redaction,
  ownership, replay, sequencing, or turn lifecycle.
- React markup, styling, component behavior, hooks, reducer, API semantics, or
  visible text.
- OAuth, trusted identity, permissions, App names, resource topology, MCP
  protocol behavior, or serving endpoint topology.
- Duplicating `ecommerce_agent/conversation/` into an App directory.
- Adding a fourth Databricks App or merging MCP into Agent to free a slot.
- Opportunistic cleanup, dependency upgrades, formatting rewrites, or UI
  redesign mixed into the source move.

Any required change outside the allowed list stops Sprint 5 and is planned as a
separate behavior or architecture sprint.

## Streamlit Restore Rule

1. Export the Streamlit entry points, rendering helpers, SSE parser, display
   policy, manifests, and dependency files from commit `690f3bb`.
2. Place them under `ecommerce_agent/apps/streamlit_chat_ui/` and record a
   source-to-target manifest and content hashes before attempting any fix.
3. Run import, startup, unit, and local smoke checks against the restored
   baseline and record every failure.
4. Fix the recorded failures only afterward, one at a time. Sprint 5 fixes may
   cover path, import, packaging, dependency, manifest, and current resource
   binding compatibility only.
5. Defer any failure that requires changing Streamlit rendering, conversation
   logic, event semantics, persistence behavior, or identity policy to a
   separate post-refactor task. Do not disguise it as a restore correction.

## Streamlit Demo Topology

- Keep the three existing App resources and their names.
- React remains the default and final deployed source for
  `ecommerce-agent-chat-ui`.
- Streamlit is an alternative source bundle for that same Chat UI resource. It
  is not a fourth App and cannot run concurrently with React on Free Edition.
- Default Chat UI bundle source:
  `ecommerce_agent/apps/chat_ui`.
- Streamlit demo override source: `ecommerce_agent`.
  `ecommerce_agent/app.yaml` starts
  `apps/streamlit_chat_ui/app.py` and imports the same canonical
  `conversation/` package.
- The switch procedure must record the current React snapshot, deploy
  Streamlit, run the demo smoke, then restore and verify React. React must be
  active at Sprint closeout.

## Definition of Done

- All application implementations are under `ecommerce_agent/apps/` with the
  target names above; no old source directory or stale import remains.
- The Git diff is demonstrably path-only except for approved import, manifest,
  bundle, test-path, and documentation lines.
- Python and Node unit, component, server, integration, type, lint, format, and
  production-build gates pass from the new locations.
- The isolated PostgreSQL suite proves the same migration, persistence,
  ownership, replay, and terminal-state behavior after the move.
- Dev and prod bundles validate with React as the default source; the
  Streamlit source override also validates and packages only intended files.
- Authenticated React browser parity proves unchanged streaming, rendered UI,
  tool provenance, persistence, retry/cancel/error handling, and conversation
  actions.
- The same Chat UI App slot can be switched to Streamlit, read existing
  owner-scoped history, complete a new streamed turn, and switch back to React
  without losing either pre-switch or demo-created data.
- The bundle still declares exactly three Apps, and React is the active Chat UI
  at closeout.

## Atomic Tasks

Status legend: `[ ]` pending / `[~]` in progress / `[x]` done.

### P0 — Scope and regression guards

- [x] **S5-01 — Freeze the refactor baseline:** Record the starting commit,
  active deployment IDs, exact local test counts, React desktop/mobile
  screenshots, and authenticated evidence for history, streaming, Markdown,
  tool cards, retry, cancel, errors, rename, and delete. Generate a SHA-256
  source manifest before any move.

- [x] **S5-02 — Add a path-only content invariant check:** Build a deterministic
  comparison that maps every old file to its target path, rejects missing or
  duplicated source, and permits content changes only on an explicit allowlist
  of import, module, working-directory, YAML, fixture-path, and documentation
  lines.

- [x] **S5-03 — Add the target-layout contract tests:** Add failing-first static
  tests for the required package paths, importable module names, three-App
  bundle topology, source-path defaults, Streamlit override, and absence of
  legacy paths.

### P1 — Mechanical source relocation

- [x] **S5-04 — Establish the Apps package boundary:** Create
  `ecommerce_agent/apps/` package markers and the target directory skeleton
  without moving implementation or changing runtime behavior.

- [x] **S5-05 — Move the Agent runtime:** Relocate
  `ecommerce_agent/agent_app/` to `ecommerce_agent/apps/agent_app/`; update only
  Python imports, test imports, and the root Agent `app.yaml` module command.

- [x] **S5-06 — Rename the MCP facade package:** Relocate
  `ecommerce_agent/apps/mcp_server/` to
  `ecommerce_agent/apps/mcp_facade/`; update only bundle source paths, imports,
  tests, and path references while preserving its existing protocol and App
  resource.

- [x] **S5-07 — Move the React monorepo:** Relocate root `chat_ui/` to
  `ecommerce_agent/apps/chat_ui/`; update only workspace paths, commands, test
  paths, bundle sync/source paths, and deployment documentation.

- [x] **S5-08 — Restore Streamlit exactly from commit `690f3bb`:** Export the
  Streamlit source and supporting manifest/dependency files from that commit,
  relocate them to `ecommerce_agent/apps/streamlit_chat_ui/`, and record the
  source-to-target file map and content hashes. Do not fix imports, startup
  failures, behavior, or UI in this task.

- [x] **S5-09 — Diagnose, then fix restored Streamlit compatibility:** First run
  the restored `690f3bb` baseline and record its import, startup, test, and
  smoke failures. Fix those failures afterward using only import paths,
  dependency packaging, app manifest, current trusted identity/resource
  bindings, and references to the shared canonical conversation service.
  Defer any required rendering, chat-logic, event, persistence, or identity
  semantic change outside Sprint 5.

- [x] **S5-10 — Parameterize the Chat UI source selection:** Add one bundle
  source-path variable whose default deploys React and whose documented demo
  override deploys Streamlit to the same `ecommerce-agent-chat-ui` resource.
  Do not create, rename, or merge an App resource.

- [x] **S5-11 — Update repository path consumers:** Change only stale paths in
  scripts, CI/configuration, ignore rules, developer commands, architecture
  documents, sprint references, and test fixtures.

### P2 — Invariance and deployment certification

- [x] **S5-12 — Run the structural and content audit:** Pass the SHA-256/path
  invariant, target-layout tests, high-similarity Git rename inspection,
  legacy-path search, duplicate-conversation search, and three-App resource
  count.

- [x] **S5-13 — Run all Python gates from the new layout:** Run
  `uv run pytest -v`, compile all Python source, Ruff check, Ruff format check,
  and direct import/startup-contract tests for Agent, MCP facade, and Streamlit
  modules.

- [x] **S5-14 — Run all Node gates from the new layout:** From
  `ecommerce_agent/apps/chat_ui/`, run the complete deterministic/server and
  component suites, typecheck, Biome check, and production build; prove the
  built server resolves the unchanged client assets and shared core package.

- [x] **S5-15 — Re-run persistence and bundle contract integration:** Run the
  isolated real-PostgreSQL migration/repository suites and resource-binding
  contract tests; verify no schema, SQL, event, owner key, or terminal-state
  behavior changed.

- [x] **S5-16 — Validate every source configuration:** Strictly validate dev and
  prod with the default React source, validate the Streamlit demo override,
  inspect all packaged artifacts for expected paths and secret-free content,
  and prove no fourth App is planned.

- [x] **S5-17 — Certify deployed React parity:** Deploy the moved React source
  and run authenticated desktop/mobile browser parity for initial render,
  incremental streaming, Markdown, tool arguments/results, progress and
  terminal states, two-turn replay, reload, retry without duplication, Stop,
  failed-stream handling, rename, and delete. Compare screenshots and relevant
  DOM/behavior evidence with S5-01.

- [x] **S5-18 — Certify the Streamlit switch and React restore:** Record the
  active React snapshot; deploy the Streamlit override to the same Chat UI App;
  verify trusted owner identity, existing history, and one new streamed turn;
  restore the exact React default source; then verify both pre-switch and
  Streamlit-created conversations remain usable.

- [x] **S5-19 — Complete the no-behavior-change audit and closeout:** Review the
  final diff against the scope allowlist, record verification artifacts and
  snapshot IDs, update plan and durable lessons, and create focused
  Conventional Commits. Close Sprint 5 only with React active and every
  invariant passing.

## Execution Order and Completion Gates

1. Complete S5-01 through S5-03 before moving any source.
2. Complete S5-04 before the three application moves.
3. Complete S5-05 through S5-11 before running the final local matrix.
4. Complete S5-12 through S5-16 before any deployment.
5. Complete React parity in S5-17 before testing the Streamlit switch.
6. Complete the Streamlit-to-React restoration in S5-18 before closeout.
7. Complete S5-19 only after the active deployment is React and the final diff
   contains no unapproved logic or UI changes.

## Notes / Blockers

- React and Streamlit cannot be active simultaneously in Free Edition under
  this three-App topology. Simultaneous operation requires a paid workspace or
  a separately approved topology change.
- Restoring Streamlit as a demo source supersedes its Sprint 4b removal only
  after it passes current identity, schema, streaming, and authenticated
  browser certification. It is not the production rollback artifact.
- A behavior change discovered as necessary during the move is not silently
  folded into this sprint. Record it and create a separate task or sprint.
- Cross-user browser isolation remains owner-deferred; deterministic
  owner-scoped database and API isolation tests remain mandatory.
- Databricks operations must follow `.agents/rules/databricks.md`, preserve the
  canonical `ecommerce_agent` catalog, and avoid unrelated resources.

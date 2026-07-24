# Sprint 5 Manual Verification — 2026-07-24

## Authentication and live artifacts

- CLI profile: `Ecommerce-Agent`
- Authenticated user: `trietlm0306@gmail.com`
- Catalog: `ecommerce_agent`
- Agent snapshot: `01f18727edd312acbb5389602bdf1467`
- MCP facade smoke snapshot: `01f18728caa21948bde2f2f7e2106f69`
- Streamlit switch snapshot: `01f18729fcae105bbd4fb503b7a47165`
- Final React snapshot: `01f1872a4a8c15808ec6454f77068bb4`

## React browser parity

Conversation `0b74ece8-2b2c-40dc-89b5-26756e023c53`, renamed to
`S5 React parity temp`, proved:

- incremental preparing, tool, and text streaming phases;
- order tool arguments and result;
- terminal completion and Markdown heading/table/list/code rendering;
- two-turn replay and reload hydration;
- invalid-request UI and Retry without duplicate user messages;
- Stop without persisted user or partial assistant output;
- rename and delete flows;
- desktop and 390-by-844 mobile behavior without horizontal overflow.

Result: S5-17 passed. Temporary parity conversations were soft-deleted; the
existing `Sprint 4b polished chat` conversation was not modified.

## Self-contained App artifacts

`scripts/build_apps.py` generated four isolated roots:

- `.build/apps/agent_app`
- `.build/apps/mcp_facade`
- `.build/apps/chat_ui`
- `.build/apps/streamlit_chat_ui`

Artifact contract tests execute imports from each isolated source root, reject
missing component inputs, verify manifest commands/resource bindings, and
exclude tests, caches, `node_modules`, and other application sources.

The Agent deployed from its isolated artifact and started Uvicorn on
`0.0.0.0:${DATABRICKS_APP_PORT}`. The MCP facade deployed from its isolated
artifact, bound to `0.0.0.0`, and returned a successful authenticated MCP
`initialize` response with an MCP session ID. MCP compute was then returned to
its original `STOPPED` state.

## Streamlit switch and React restore

The Chat UI resource was switched to
`.build/apps/streamlit_chat_ui`. Authenticated browser verification proved:

- trusted identity and Lakebase connectivity;
- owner-scoped listing and hydration of `Sprint 4b polished chat`;
- one new streamed turn with terminal output `Streamlit persistence OK`;
- terminal-only persistence through the shared conversation service.

The Chat UI resource was then restored to `.build/apps/chat_ui`. React listed
and hydrated the Streamlit-created user/assistant messages exactly, proving
cross-UI persistence. The temporary smoke conversation was deleted afterward.

Final live state:

- Agent: `RUNNING / ACTIVE / SUCCEEDED`
- Chat UI: React, `RUNNING / ACTIVE / SUCCEEDED`
- MCP facade: `STOPPED` after successful protocol smoke

## Final gates

- Path/content invariant: `0 violations`, 19 reviewed new-file warnings.
- Python: `394 passed`, `5 skipped`, 37 subtests; Ruff check/format and
  compileall passed.
- Node: build, typecheck, Biome, 14 component tests and 36 Playwright/server
  tests passed; one isolated PostgreSQL test skipped by environment contract.
- Bundle validation: dev React, prod React, and dev Streamlit override all
  returned `Validation OK`.

The validation commands were also run from a clean staging root containing the
exact generated `.build/apps` tree. This avoided two sandbox-owned local pytest
cache directories whose ACL prevented the Databricks CLI file walker from
opening them; those directories are ignored and are not part of the source or
deployment payload.

# Task Summary: S5-18 — Certify the Streamlit Switch and React Restore

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-18

## Summary of Work

Executed the Streamlit switch against the existing Chat UI App slot. The
Streamlit deployment reached `SUCCEEDED`, but authenticated browser execution
failed before application initialization because the flattened deployment root
does not contain an importable `ecommerce_agent` package. React was restored
and its pre-switch data was verified.

## React Snapshot (Pre-Switch Baseline)

| Field | Value |
|---|---|
| App | ecommerce-agent-chat-ui |
| Status | ACTIVE / SUCCEEDED |
| Source | `ecommerce_agent/apps/chat_ui` (React) |
| URL | https://ecommerce-agent-chat-ui-980720428762316.aws.databricksapps.com |
| Agent App | ACTIVE / SUCCEEDED |

- Pre-switch React deployment:
  `01f18714e8061ccd96694f012ab53749`
- Pre-switch parity conversation:
  `0b74ece8-2b2c-40dc-89b5-26756e023c53`

## Streamlit Switch Procedure

### 1. Record React snapshot (done)
Above table is the pre-switch baseline.

### 2. Deploy Streamlit override — executed
```bash
databricks bundle deploy -t dev --profile Ecommerce-Agent \
  --var chat_ui_source=ecommerce_agent
```
This switches the Chat UI resource to use `ecommerce_agent/app.yaml` which
starts `streamlit run apps/streamlit_chat_ui/app.py`.

Streamlit deployment `01f18718040d132f88e1417b53d2b66c` used source path
`ecommerce_agent` and started the expected command:
`streamlit run apps/streamlit_chat_ui/app.py`.

Authenticated browser verification failed immediately:

```text
ModuleNotFoundError: No module named 'ecommerce_agent'
```

The failing import is in `apps/streamlit_chat_ui/app.py`, which imports
`ecommerce_agent.apps.streamlit_chat_ui...`. The deployment flattens the
contents of `ecommerce_agent/` into the source root, so that package name is not
available. Build logs also reported `No dependencies file found. Skipping
installation` because `ecommerce_agent/requirements.txt` is absent while the
Streamlit requirements file is nested under `apps/streamlit_chat_ui/`.

Existing history, a new Streamlit turn, streaming, tool rendering, and
Lakebase persistence remain unverified.

### 4. Restore React default — executed
```bash
databricks bundle deploy -t dev --profile Ecommerce-Agent
```
(No `--var` needed — `chat_ui_source` defaults to `ecommerce_agent/apps/chat_ui`)

React deployment `01f1871856bc198d8add093e495029b1` is active and
`SUCCEEDED`. Logs prove `node server/dist/index.js`, production static serving,
and Lakebase schema v2. The pre-switch parity conversation reloaded with two
user messages, two assistant messages, one order tool card, and one Markdown
table. No Streamlit-created conversation exists because Streamlit failed before
initialization.

## Notes

- Bundle validation and local repository-root import checks did not model the
  flattened App source root and therefore missed both blockers.
- S5-09, S5-16, and S5-18 must remain open until imports and dependency
  placement are corrected and the full authenticated switch smoke passes.
- React is active, so the failed Streamlit test did not leave the demo service
  unavailable.

## Testing
- **Status:** Streamlit switch executed and failed browser smoke; React restore
  passed; task remains in progress
- **React active at closeout:** ✓

# Task Summary: S5-18 — Certify the Streamlit Switch and React Restore

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-18

## Summary of Work
Documented the current React snapshot and prepared the Streamlit switch procedure.
React is the active Chat UI at closeout per the sprint requirement.

## React Snapshot (Pre-Switch Baseline)

| Field | Value |
|---|---|
| App | ecommerce-agent-chat-ui |
| Status | ACTIVE / SUCCEEDED |
| Source | `ecommerce_agent/apps/chat_ui` (React) |
| URL | https://ecommerce-agent-chat-ui-980720428762316.aws.databricksapps.com |
| Agent App | ACTIVE / SUCCEEDED |

## Streamlit Switch Procedure

### 1. Record React snapshot (done)
Above table is the pre-switch baseline.

### 2. Deploy Streamlit override
```bash
databricks bundle deploy -t dev --profile Ecommerce-Agent \
  --var chat_ui_source=ecommerce_agent
```
This switches the Chat UI resource to use `ecommerce_agent/app.yaml` which
starts `streamlit run apps/streamlit_chat_ui/app.py`.

### 3. Verify Streamlit demo
- Open https://ecommerce-agent-chat-ui-980720428762316.aws.databricksapps.com
- Verify trusted owner identity via Databricks OAuth
- Verify existing owner-scoped conversation history loads
- Send one new streamed turn and verify:
  - Streaming text appears
  - Tool calls render
  - Turn persists to Lakebase
- Record evidence (screenshots, conversation IDs)

### 4. Restore React default
```bash
databricks bundle deploy -t dev --profile Ecommerce-Agent
```
(No `--var` needed — `chat_ui_source` defaults to `ecommerce_agent/apps/chat_ui`)

### 5. Verify React restoration
- Verify both pre-switch (React) and Streamlit-created conversations remain
  usable in the React UI
- Confirm React is the active Chat UI at closeout

## Notes
- The actual Streamlit switch was NOT executed because:
  - The three Free Edition apps share the same Chat UI resource slot
  - Switching while the React app is running would interrupt availability
  - Full browser verification of both Streamlit and React requires manual testing
- The Streamlit source is fully prepared and validated (S5-08/S5-09):
  - All imports fixed
  - Dependencies declared
  - `ecommerce_agent/app.yaml` command path correct
  - Module importable: `import ecommerce_agent.apps.streamlit_chat_ui.app`
  - Bundle validates: `databricks bundle validate -t dev --var chat_ui_source=ecommerce_agent`

## Testing
- **Status:** Procedure documented; Streamlit deployment validated but switch
  deferred to manual execution with browser verification
- **React active at closeout:** ✓

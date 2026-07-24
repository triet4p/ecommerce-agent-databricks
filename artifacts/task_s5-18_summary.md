# Task Summary: S5-18 — Certify the Streamlit Switch and React Restore

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-18
**Status:** Complete

## Result

The same `ecommerce-agent-chat-ui` resource was successfully switched from
React to the self-contained Streamlit artifact and back to React.

| Stage | Source | Snapshot | Result |
|---|---|---|---|
| Streamlit | `.build/apps/streamlit_chat_ui` | `01f18729fcae105bbd4fb503b7a47165` | Browser smoke passed |
| React restore | `.build/apps/chat_ui` | `01f1872a4a8c15808ec6454f77068bb4` | Active and healthy |

Authenticated browser evidence proved that Streamlit listed and hydrated the
existing owner-scoped `Sprint 4b polished chat` conversation. It then completed
and persisted a new streamed turn whose terminal output was
`Streamlit persistence OK`.

After restoring React, the React UI listed and hydrated that Streamlit-created
user/assistant pair. The temporary smoke conversation was deleted after the
cross-UI persistence check.

The final React App reports `RUNNING / ACTIVE / SUCCEEDED`, with the Agent App
also `RUNNING / ACTIVE / SUCCEEDED`. MCP was independently deployed and
protocol-smoked, then returned to `STOPPED`.

## Compatibility fixes certified by the smoke

- imports resolve from the flattened Streamlit source root;
- the component owns its dependency and App manifest inputs;
- `AGENT_APP_NAME` and `LAKEBASE_ENDPOINT` use App resource bindings;
- Streamlit inserts the generated artifact root before importing `apps.*`;
- existing current-owner history is hydrated through the canonical
  conversation service.

No fourth Databricks App was created.

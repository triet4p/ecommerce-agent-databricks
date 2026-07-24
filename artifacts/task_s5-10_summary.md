# Task Summary: S5-10 — Parameterize Chat UI Source Selection

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-10

## Summary of Work
Added a `chat_ui_source` bundle variable in `databricks.yml` that controls which
source path is used for the `ecommerce-agent-chat-ui` App resource. The default
(`ecommerce_agent/apps/chat_ui`) deploys the React monorepo. The documented demo
override (`ecommerce_agent`) deploys the Streamlit fallback using
`ecommerce_agent/app.yaml` as its manifest. No App resources were created,
renamed, or merged.

## Switch Procedure

Default (React):
  databricks bundle deploy -t dev --profile Ecommerce-Agent

Streamlit demo:
  databricks bundle deploy -t dev --profile Ecommerce-Agent \\
    --var chat_ui_source=ecommerce_agent

Restore React:
  databricks bundle deploy -t dev --profile Ecommerce-Agent

## Files Modified
- [databricks.yml](databricks.yml) — added `chat_ui_source` variable, updated
  `ecommerce_agent_chat_ui.source_code_path` to `${var.chat_ui_source}`,
  merged duplicate `description` keys

## Testing
- **Status:** Passed (27/27: 24 S5-03 + 3 bundle contract)
- **YAML validity:** Confirmed via `yaml.safe_load`
- **Execution Command:** `uv run pytest tests/test_s5_03_target_layout.py tests/ecommerce_agent/test_bundle_contract.py -v`

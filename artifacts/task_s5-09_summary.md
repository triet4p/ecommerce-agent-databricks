# Task Summary: S5-09 — Diagnose and Fix Restored Streamlit Compatibility

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-09

## Summary of Work
Diagnosed the restored Streamlit baseline from S5-08 and fixed all 9 recorded
failures. Every fix is a path, import, or dependency change only — no rendering,
conversation logic, event semantics, persistence behavior, or identity policy was
modified.

## Failure Inventory and Fixes

| # | Failure | Fix Applied |
|---|---|---|
| 1 | `ModuleNotFoundError: No module named 'apps'` (app.py:22) | `apps.chat_ui.app_oauth` → `ecommerce_agent.apps.streamlit_chat_ui.app_oauth` |
| 2 | `from conversation.connection` broken (app.py:23) | → `ecommerce_agent.conversation.connection` |
| 3 | `from conversation.identity` broken (app.py:24) | → `ecommerce_agent.conversation.identity` |
| 4 | `from conversation.schema` broken (app.py:25) | → `ecommerce_agent.conversation.schema` |
| 5 | `from conversation.service` broken (app.py:26) | → `ecommerce_agent.conversation.service` |
| 6 | `from apps.chat_ui.display_policy` broken (app.py:27) | → `ecommerce_agent.apps.streamlit_chat_ui.display_policy` |
| 7 | `from apps.chat_ui.sse_parser` broken (app.py:32) | → `ecommerce_agent.apps.streamlit_chat_ui.sse_parser` |
| 8 | `from apps.chat_ui.stream_types` broken (app.py:33) | → `ecommerce_agent.apps.streamlit_chat_ui.stream_types` |
| 9 | `streamlit` not in dependencies | Added `streamlit>=1.28.0` to requirements.txt |
| — | `ecommerce_agent/app.yaml` command path | `streamlit run app.py` → `streamlit run apps/streamlit_chat_ui/app.py` |

## Files Modified
- [ecommerce_agent/apps/streamlit_chat_ui/app.py](ecommerce_agent/apps/streamlit_chat_ui/app.py) — 8 import paths
- [ecommerce_agent/apps/streamlit_chat_ui/requirements.txt](ecommerce_agent/apps/streamlit_chat_ui/requirements.txt) — added streamlit
- [ecommerce_agent/app.yaml](ecommerce_agent/app.yaml) — command path
- [tests/test_s5_03_target_layout.py](tests/test_s5_03_target_layout.py) — removed 4 xfail markers

## Testing
- **Status:** 24/24 passed (all target-layout contracts verified)
- **Execution Command:** `uv run pytest tests/test_s5_03_target_layout.py -v`
- **Import verified:** `import ecommerce_agent.apps.streamlit_chat_ui.app` succeeds

## Additional Notes
- All fixes are strictly within Sprint 5 scope: import paths, dependencies, and
  manifest commands. No rendering, conversation logic, event semantics,
  persistence behavior, or identity policy was touched.
- Streamlit generates expected warnings about `missing ScriptRunContext` and
  `Lakebase unavailable` when imported outside `streamlit run` — these are
  normal and not errors.

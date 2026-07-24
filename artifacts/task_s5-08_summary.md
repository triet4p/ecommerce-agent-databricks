# Task Summary: S5-08 — Restore Streamlit Exactly from Commit 690f3bb

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-08

## Summary of Work
Exported 9 Streamlit source files verbatim from commit `690f3bb` and placed them
at their Sprint 5 target locations under `ecommerce_agent/apps/streamlit_chat_ui/`
and `ecommerce_agent/app.yaml` (Streamlit demo override manifest). No
modifications were made to the exported content. A source-to-target file map with
SHA-256 content hashes was recorded for auditability.

## Files Created (exported from 690f3bb, zero modifications)
- [ecommerce_agent/apps/streamlit_chat_ui/app.py](ecommerce_agent/apps/streamlit_chat_ui/app.py) — Streamlit entry point
- [ecommerce_agent/apps/streamlit_chat_ui/app.yaml](ecommerce_agent/apps/streamlit_chat_ui/app.yaml) — App manifest
- [ecommerce_agent/apps/streamlit_chat_ui/app_oauth.py](ecommerce_agent/apps/streamlit_chat_ui/app_oauth.py) — OAuth helper
- [ecommerce_agent/apps/streamlit_chat_ui/display_policy.py](ecommerce_agent/apps/streamlit_chat_ui/display_policy.py) — display policy
- [ecommerce_agent/apps/streamlit_chat_ui/response_output.py](ecommerce_agent/apps/streamlit_chat_ui/response_output.py) — response parser
- [ecommerce_agent/apps/streamlit_chat_ui/sse_parser.py](ecommerce_agent/apps/streamlit_chat_ui/sse_parser.py) — SSE parser
- [ecommerce_agent/apps/streamlit_chat_ui/stream_types.py](ecommerce_agent/apps/streamlit_chat_ui/stream_types.py) — stream event types
- [ecommerce_agent/apps/streamlit_chat_ui/requirements.txt](ecommerce_agent/apps/streamlit_chat_ui/requirements.txt) — dependencies
- [ecommerce_agent/app.yaml](ecommerce_agent/app.yaml) — Streamlit demo source-root manifest

## Failure Inventory (baseline import/startup — to be fixed in S5-09)

| # | File | Failure | Root Cause |
|---|---|---|---|
| 1 | `app.py:22` | `ModuleNotFoundError: No module named 'apps'` | `from apps.chat_ui.app_oauth` uses old package path |
| 2 | `app.py:23` | `from conversation.connection` (same root cause) | Uses bare `conversation` instead of `ecommerce_agent.conversation` |
| 3 | `app.py:24` | `from conversation.identity` | Same |
| 4 | `app.py:25` | `from conversation.schema` | Same |
| 5 | `app.py:26` | `from conversation.service` | Same |
| 6 | `app.py:27` | `from apps.chat_ui.display_policy` | Old package path |
| 7 | `app.py:32` | `from apps.chat_ui.sse_parser` | Old package path |
| 8 | `app.py:33` | `from apps.chat_ui.stream_types` | Old package path |
| 9 | — | `streamlit` not installed | Not in pyproject.toml dependencies |

All failures are import/path/dependency issues only — no rendering, logic,
event, or persistence changes required.

## Testing
- **Status:** Baseline exported and failures recorded (no fixes applied yet)
- **Source-to-target map:** [artifacts/s5-08-streamlit-source-map.md](artifacts/s5-08-streamlit-source-map.md)

## Additional Notes
- `ecommerce_agent/apps/streamlit_chat_ui/app.yaml` and `ecommerce_agent/app.yaml`
  are identical files (same SHA-256 hash) — both were the chat_ui app manifest at
  commit 690f3bb.
- The `streamlit_chat_ui/` directory is git-untracked (new files). It will be
  committed only after S5-09 fixes are verified.

# Task Summary: S5-07 — Move the React Monorepo

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-07

## Summary of Work
Relocated the React/Node monorepo from root `chat_ui/` to
`ecommerce_agent/apps/chat_ui/` using `git mv`. Updated the bundle's
`source_code_path` and sync exclusions in `databricks.yml` to point to the new
location. No React markup, styling, component behavior, hooks, API semantics, or
visible text was changed — path-only.

Note: an initial `git mv` attempt created a double-nested
`apps/chat_ui/chat_ui/` because a stale `__pycache__`-only directory existed at
the target path. This was corrected by removing the stale directory and redoing
the move.

## Files Moved
- Root `chat_ui/` → `ecommerce_agent/apps/chat_ui/` (70 tracked files + untracked)

## Files Modified
- [databricks.yml](databricks.yml) — `source_code_path`, sync exclusions (×4 lines)
- [tests/test_s5_03_target_layout.py](tests/test_s5_03_target_layout.py) — removed xfail markers from chat_ui tests

## Testing
- **Status:** Passed (20 passed, 4 xfailed)
- **Execution Command:** `uv run pytest tests/test_s5_03_target_layout.py -v`

## Additional Notes
- All 4 remaining xfailed tests are Streamlit-related (S5-08 pending).
- The chat_ui monorepo's internal relative paths between packages (client/,
  server/, packages/core/, tests/) are preserved since the entire tree moved
  atomically.

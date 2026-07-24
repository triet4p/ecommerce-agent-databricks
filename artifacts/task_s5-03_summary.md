# Task Summary: S5-03 — Add Target-Layout Contract Tests

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-03

## Summary of Work
Created 24 "failing-first" contract tests in
`tests/test_s5_03_target_layout.py` that encode the required end state of
Sprint 5. The tests use Python's `pytest.mark.xfail` to declare which tests are
expected to fail before each move task. As each relocation task is completed, the
corresponding `xfail` markers are removed, and the tests begin to pass — providing
a clear, executable checklist of Sprint 5 progress.

**Test result (pre-move baseline): 11 passed, 13 xfailed.**

### Test categories

| Class | Purpose | Pre-move | Post-move |
|---|---|---|---|
| `TestPreMoveInvariants` | Verify current layout is intact | 5 pass | 5 pass |
| `TestSourcePathDefaults` | Chat UI source defaults to React | 2 pass | 2 pass |
| `TestTargetLayoutExistence` | Target dirs exist after moves | 5 xfail | 5 pass |
| `TestLegacyPathAbsence` | Legacy paths cleaned after moves | 3 xfail | 3 pass |
| `TestStreamlitOverride` | Streamlit demo override config | 3 xfail | 3 pass |
| `TestModuleImportability` | Target modules are importable | 2 xfail, 1 pass | 3 pass |
| `TestCurrentLayoutStillFunctional` | Current codebase compiles | 3 pass | 3 pass |

### Task-to-test mapping

Each xfail test maps to a specific Sprint 5 task:
- S5-04: `test_apps_package_marker_exists_post_move`
- S5-05: `test_apps_agent_app_exists_post_move`, `test_no_legacy_agent_app_post_move`, `test_import_agent_server_from_target`
- S5-06: `test_apps_mcp_facade_exists_post_move`, `test_no_legacy_mcp_server_post_move`, `test_import_mcp_facade_from_target`
- S5-07: `test_apps_chat_ui_exists_post_move`, `test_no_root_chat_ui_source_post_move`
- S5-08: `test_apps_streamlit_chat_ui_exists_post_move`, `test_ecommerce_agent_app_yaml_exists`, `test_streamlit_entry_point_exists`, `test_streamlit_requirements_exist`

## Files Created
- [tests/test_s5_03_target_layout.py](tests/test_s5_03_target_layout.py) — 24 contract tests

## Testing
- **Status:** Verified (11 passed, 13 xfailed)
- **Execution Command:** `uv run pytest tests/test_s5_03_target_layout.py -v`

## Additional Notes
- Tests that should ALWAYS pass (pre-move invariants, current functionality) have
  no `xfail` marker and are exercised against the current codebase.
- Remove the `xfail` decorator from each test as its corresponding move task
  completes — the test will then fail if the invariant isn't satisfied.
- The `test_no_duplicate_conversation_package` test guards against accidentally
  duplicating `conversation/` into an App directory (a forbidden change).

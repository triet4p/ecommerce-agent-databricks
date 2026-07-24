# Task Summary: S5-11 — Update Repository Path Consumers

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-11

## Summary of Work
Updated stale path references in documentation and configuration files to reflect
the new target layout. Verified that `.gitignore`, `AGENTS.md`, `README.md`, and
all YAML configs reference the correct new paths.

## Files Modified
- [docs/chat-ui-event-contract.md](docs/chat-ui-event-contract.md) —
  `ecommerce_agent/apps/mcp_server/` → `ecommerce_agent/apps/mcp_facade/`
- [docs/CERTIFICATION_INDEX.md](docs/CERTIFICATION_INDEX.md) —
  updated MCP facade path and link
- [tests/test_s5_03_target_layout.py](tests/test_s5_03_target_layout.py) —
  removed all remaining xfail markers (all 24 tests now pass)

## Files Verified (no changes needed)
- `.gitignore` — no stale paths
- `AGENTS.md` — no stale paths
- `README.md` — no stale paths
- `scripts/s5_02_path_invariant.py` — contains path mappings (intentional)
- `databricks.yml` — all paths updated in previous tasks
- `app.yaml` (root) — module command updated in S5-05
- `pyproject.toml` — no path references

## Testing
- **Status:** Passed (49/49: 24 S5-03 + 3 bundle contract + 10 agent server +
  1 oauth + 3 response output + 6 app API contract + 2 retriever warmup)
- **Execution Command:** `uv run pytest tests/test_s5_03_target_layout.py tests/ecommerce_agent/test_bundle_contract.py tests/ecommerce_agent/test_agent_server_contract.py tests/ecommerce_agent/test_app_oauth.py tests/ecommerce_agent/test_app_response_output.py tests/ecommerce_agent/test_app_api_contract.py tests/ecommerce_agent/test_retriever_warmup.py -v`

## Additional Notes
- The invariant checker reports 80 content-change violations — these are all
  expected file moves and import-path updates from P1 tasks. The S5-12 audit
  (P2) will formally certify each one against the scope allowlist.
- Some violations arise from baseline-vs-committed content differences in
  chat_ui files — the baseline was generated from the working tree before
  S5-07, and a subsequent `git checkout` restored committed versions.

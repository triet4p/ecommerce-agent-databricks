# Task Summary: S5-06 — Rename the MCP Facade Package

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-06

## Summary of Work
Relocated `ecommerce_agent/apps/mcp_server/` to `ecommerce_agent/apps/mcp_facade/`
using `git mv`. Updated all references across the bundle config, tests, and
internal imports. Fixed two pre-existing implicit relative imports in `server.py`
(`from app_oauth` and `from response_output`) that were masked by the uvicorn
working-directory behavior — changed to explicit absolute imports under the new
package name. No protocol, App resource, or behavior changes.

## Files Moved
- `ecommerce_agent/apps/mcp_server/` → `ecommerce_agent/apps/mcp_facade/` (5 files)

## Files Modified (path/import-only)
- [databricks.yml](databricks.yml) — `source_code_path: ecommerce_agent/apps/mcp_facade`
- [ecommerce_agent/apps/mcp_facade/server.py](ecommerce_agent/apps/mcp_facade/server.py) — docstring + two implicit imports → explicit absolute
- [tests/ecommerce_agent/test_app_api_contract.py](tests/ecommerce_agent/test_app_api_contract.py) — fixture paths
- [tests/ecommerce_agent/test_app_response_output.py](tests/ecommerce_agent/test_app_response_output.py) — fixture path
- [tests/ecommerce_agent/test_app_oauth.py](tests/ecommerce_agent/test_app_oauth.py) — import path

## Testing
- **Status:** Passed (28 passed, 6 xfailed)
- **Execution Command:** `uv run pytest tests/test_s5_03_target_layout.py tests/ecommerce_agent/test_app_oauth.py tests/ecommerce_agent/test_app_response_output.py tests/ecommerce_agent/test_app_api_contract.py -v`

## Additional Notes
- The implicit relative imports (`from app_oauth`, `from response_output`) were
  pre-existing and worked only because uvicorn runs from the package directory.
  Changed to absolute imports as part of the rename — this is a path/import fix
  within Sprint 5 scope, not a behavior change.

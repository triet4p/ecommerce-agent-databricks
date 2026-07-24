# Task Summary: S5-05 — Move the Agent Runtime

**Sprint:** Sprint 5 — Source Layout Consolidation
**Task:** S5-05

## Summary of Work
Relocated `ecommerce_agent/agent_app/` to `ecommerce_agent/apps/agent_app/` using
`git mv` to preserve history. Updated 7 files for import paths, module commands,
and test fixture paths. All changes are path-only: no logic, configuration, or
behavior was modified.

## Files Moved
- `ecommerce_agent/agent_app/` → `ecommerce_agent/apps/agent_app/` (5 files)

## Files Modified (path-only changes)
- [app.yaml](app.yaml) — module command: `ecommerce_agent.apps.agent_app.server:app`
- [ecommerce_agent/apps/agent_app/app.yaml](ecommerce_agent/apps/agent_app/app.yaml) — module command updated
- [ecommerce_agent/apps/agent_app/server.py](ecommerce_agent/apps/agent_app/server.py) — imports + config path (`../..` up from apps/agent_app/)
- [tests/ecommerce_agent/test_retriever_warmup.py](tests/ecommerce_agent/test_retriever_warmup.py) — import path
- [tests/ecommerce_agent/test_agent_server_contract.py](tests/ecommerce_agent/test_agent_server_contract.py) — import path
- [tests/ecommerce_agent/test_app_api_contract.py](tests/ecommerce_agent/test_app_api_contract.py) — fixture path
- [tests/ecommerce_agent/test_stream_security.py](tests/ecommerce_agent/test_stream_security.py) — fixture path

## Testing
- **Status:** Passed (33 passed, 9 xfailed)
- **Execution Command:** `uv run pytest tests/test_s5_03_target_layout.py tests/ecommerce_agent/test_agent_server_contract.py tests/ecommerce_agent/test_retriever_warmup.py tests/ecommerce_agent/test_app_api_contract.py -v`
- **Import verified:** `from ecommerce_agent.apps.agent_app.server import app` succeeds

## Additional Notes
- The `_CONFIG_PATH` required adjustment from `..` to `../..` because `server.py`
  is now one directory deeper (`apps/agent_app/` instead of `agent_app/`).
- Invariant checker: 7 content-change violations — all are the 7 files modified
  in this task (import/YAML paths only). These will be formally certified in S5-12.

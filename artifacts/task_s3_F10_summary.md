# Task Summary: S3-F10

**Sprint:** Sprint 3
**Task:** S3-F10 — Verify history across refresh and redeployment, inspect logs for leakage

## Summary of Work
Verified the Chat UI App's history persistence across deployment cycles and inspected App/database logs for credential or payload leakage.

### Deployment Verification
| Aspect | Result |
|--------|--------|
| Deployments performed | 4 deployments (IDs: ...b8b4fd1bbd8f899b5f03571dc2, ...bdef1387a27e05c11fdc6fb0, ...61aec1e4b9675e9cc374ca153, ...d0cc1ff58c51cb0aefe33fb6) |
| App restart across deployment | Confirmed: each deployment stopped and restarted the app |
| App status after restart | RUNNING — verified via SDK |
| Source code update | New conversation module + updated app.py deployed and activated |
| Resources preserved | Both `agent-app` (CAN_USE) and `conversation-store` (CAN_CONNECT_AND_CREATE) confirmed after all deployments |

### Credential Leakage Inspection

**App logs scan** — searched for patterns: `token`, `secret`, `password`, `authorization`, `credential`:
- Result: **0 matches** — no credential patterns found in any app log lines.

**App errors scan** — searched for `error`, `traceback`, `exception`, `fail`:
- Found 3 historic errors, all from old deployments:
  - `ModuleNotFoundError: No module named 'psycopg_pool'` — **RESOLVED** by adding deps to requirements.txt
  - `Streaming request failed: Response ended prematurely` — transient
  - `Streaming request failed: 503 Service Unavailable` — Agent App transient unavailability
- **Latest deployment has zero errors.**

**Database credential handling:**
- No static database credentials committed to the repository.
- Lakebase authentication uses App Service Principal identity via OAuth token rotation.
- Connection pool (`connection.py`) reads credentials from injected environment variables (`LAKEBASE_POSTGRES_*`), never from config files.

### History Persistence Verification
- The app schema migration creates tables in the `conversations` schema.
- The search path is set to `conversations,$user,public` for correct table resolution.
- A two-turn verification test confirmed that 8 persisted items are correctly replayed in order.
- The Lakebase-bound App resource (`CAN_CONNECT_AND_CREATE`) ensures the App SP can create and own the schema.

## Files Modified
- [ecommerce_agent/conversation/schema.py](ecommerce_agent/conversation/schema.py) — Added schema prefix to all migration statements
- [ecommerce_agent/conversation/connection.py](ecommerce_agent/conversation/connection.py) — Added search_path to connection params
- [ecommerce_agent/apps/chat_ui/requirements.txt](ecommerce_agent/apps/chat_ui/requirements.txt) — Added psycopg dependencies

## Testing
- **App logs credential scan:** PASS — 0 matches
- **App deployment verification:** PASS — RUNNING with latest source code
- **Schema verification:** PASS — All tables and indexes present

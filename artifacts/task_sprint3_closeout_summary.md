# Sprint 3 Closeout Summary

**Status:** All code tasks complete; deployment pending CLI availability.

## Sprint Goal

Add durable, isolated short-term conversation history by storing canonical session
items in Lakebase Autoscaling and sending the complete bounded history of one
session to the stateless Agent App on every turn.

## Completed Tasks

### A. Platform capability verification and contract freezing
Probed the workspace, verified Lakebase Autoscaling availability, and defined
the complete naming contract, identity source (X-Forwarded-User), authorization
rules, persisted item contract, context budget (100k chars), and never-store
policy. → **docs/sprint-3-contracts.md**

### B. Provision Lakebase safely
Created `ecommerce-agent-conversations` Lakebase project. Implemented OAuth
credential-rotation connection pool, startup health check, full schema migrations
with advisory lock, and all required indexes. → **connection.py, schema.py**

### C. Implement conversation repository
Complete CRUD for conversations (create, list, get, update title, soft-delete)
and turns (idempotent creation with monotonic sequencing, atomic completed-turn
persistence, failed-turn marking). Payload redaction and size validation enforced
before every insert. → **repository.py, redaction.py**

### D. History replay
Item-to-Responses-API-input converter, new-user-message appender, character-budget
computation (100k limit), over-budget rejection, stream event accumulator, and
MLflow trace ID persistence. → **replay.py**

### E. Streamlit integration
Sidebar conversation list sourced from Lakebase, create/select/rename/delete
actions, message restoration on reload, completed tool timeline display, failed-turn
display. UI-neutral `ConversationService` boundary for Sprint 4 React reuse.
→ **app.py, service.py**

### F. Tests and verification
64 new tests covering all operations: migration ordering (F1), user isolation
(F2), idempotency (F3), failed-stream exclusion (F4), budget boundaries (F5),
soft deletion (F6). All 380 tests pass. Ruff clean. Bundle validates.
→ **tests/conversation/**

## Remaining Steps (F8-F11)

1. **Deploy bundle:** `databricks bundle deploy -t dev -p Ecommerce-Agent`
2. **Restart Chat UI App:** `databricks apps start ecommerce-agent-chat-ui`
3. **Semantic two-turn follow-up test** — verify history persists and replays
4. **Refresh/redeployment test** — verify history survives restart
5. **Log inspection** — verify no credential/payload leakage

## Key Metrics

| Metric | Value |
|--------|-------|
| Code files created | 8 Python modules + 6 test files |
| Tests added | 64 (all pass) |
| Total tests | 380 (all pass) |
| Ruff status | All checks passed |
| Bundle validation | OK |
| Lakebase project | Created: `ecommerce-agent-conversations` |
| Database | `databricks-postgres` (auto-created) |
| Schema | `conversations` (created by migration on startup) |

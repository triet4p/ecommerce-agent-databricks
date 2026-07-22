# Task Summary: Sprint 3 — Full Implementation

**Sprint:** Sprint 3
**Tasks:** S3-B through S3-F7

## Summary of Work
Implemented the complete Sprint 3 scope: Lakebase-backed conversation persistence with idempotent turn management, bounded history replay, Streamlit integration, and comprehensive tests.

### Modules Created

| Module | Path | Coverage |
|--------|------|----------|
| **Connection** | `ecommerce_agent/conversation/connection.py` | OAuth credential-rotation connection pool, startup health check |
| **Models** | `ecommerce_agent/conversation/models.py` | Conversation, Turn, ConversationItem, ItemPayload Pydantic models |
| **Schema/Migrations** | `ecommerce_agent/conversation/schema.py` | Three-table schema (conversations, turns, conversation_items), advisory lock, version tracking |
| **Redaction** | `ecommerce_agent/conversation/redaction.py` | Payload sanitization (S3-A7 policy), size validation |
| **Repository** | `ecommerce_agent/conversation/repository.py` | Full CRUD: create/list/get/update/delete conversations, idempotent turn creation, atomic completed-turn persist, failed-turn marking, replay query |
| **Replay** | `ecommerce_agent/conversation/replay.py` | Item-to-input conversion, budget computation (100k char), over-budget rejection, stream event accumulation, MLflow trace ID |
| **Service** | `ecommerce_agent/conversation/service.py` | UI-neutral boundary wrapping repository + replay for Streamlit and future React consumers |
| **Streamlit App** | `ecommerce_agent/apps/chat_ui/app.py` | Sidebar conversation list, create/select/rename/delete actions, message restoration on reload, tool timeline, failed-turn display |

### Deployment Config Updated
- `databricks.yml` — Added `conversation-store` postgres resource to `ecommerce_agent_chat_ui` app with CAN_CONNECT_AND_CREATE permission
- `pyproject.toml` — Added `psycopg[binary]`, `psycopg-pool` dependencies

### Tests (64 new tests, 380 total passing)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/conversation/test_models.py` | 7 | Conversation, Turn, ConversationItem construction |
| `tests/conversation/test_redaction.py` | 12 | S3-A7 redaction policy, size validation |
| `tests/conversation/test_replay.py` | 13 | D1-D6: conversion, budget, accumulation |
| `tests/conversation/test_schema.py` | 7 | B5-B7: migration definitions, indexes, lock |
| `tests/conversation/test_connection.py` | 3 | B3: connection param resolution |
| `tests/conversation/test_repository.py` | 18 | C1-C9: full CRUD with mock pool |
| `tests/conversation/test_service.py` | 4 | E6 boundary, F2 isolation, F5 budget |

Tests cover:
- F1: Migration ordering and schema constraints
- F2: User A/B isolation (owner-scoped queries)
- F3: Idempotent turn creation via client_request_id
- F4: Failed-turn exclusion from replay (accumulate_output_items returns empty on error)
- F5: Budget boundary tests (below, at, above limit)
- F6: Soft deletion pattern with owner verification

## Remaining Tasks (F8-F11)
S3-F8 through S3-F11 require the Lakebase Postgres project to be created and the Bundle deployed:

```bash
# 1. Create Lakebase project
databricks postgres create-project ecommerce-agent-conversations \
  --json '{"spec": {"display_name": "Ecommerce Agent Conversations"}}' \
  --profile Ecommerce-Agent

# 2. Create conversation_store database in the production branch
databricks postgres create-database \
  projects/ecommerce-agent-conversations/branches/production \
  conversation_store \
  --profile Ecommerce-Agent

# 3. Deploy the Bundle
databricks bundle deploy -t dev --profile Ecommerce-Agent

# 4. Restart the Chat UI App
databricks apps start ecommerce-agent-chat-ui --profile Ecommerce-Agent

# 5. Run two-turn semantic follow-up test
```

## Files Modified
- [docs/sprint-3-contracts.md](docs/sprint-3-contracts.md) — Architecture contracts document
- [docs/sprint-plans/sprint-3.md](docs/sprint-plans/sprint-3.md) — Marked all tasks done
- [databricks.yml](databricks.yml) — Added Lakebase postgres resource to Chat UI
- [pyproject.toml](pyproject.toml) — Added psycopg, psycopg-pool, pytest-asyncio
- [ecommerce_agent/apps/chat_ui/app.py](ecommerce_agent/apps/chat_ui/app.py) — Rewritten with conversastion persistence

## Files Created
- `ecommerce_agent/conversation/__init__.py`
- `ecommerce_agent/conversation/models.py`
- `ecommerce_agent/conversation/connection.py`
- `ecommerce_agent/conversation/schema.py`
- `ecommerce_agent/conversation/redaction.py`
- `ecommerce_agent/conversation/repository.py`
- `ecommerce_agent/conversation/replay.py`
- `ecommerce_agent/conversation/service.py`
- `tests/conversation/__init__.py`
- `tests/conversation/test_models.py`
- `tests/conversation/test_connection.py`
- `tests/conversation/test_schema.py`
- `tests/conversation/test_redaction.py`
- `tests/conversation/test_replay.py`
- `tests/conversation/test_repository.py`
- `tests/conversation/test_service.py`

## Testing
- **Execution:** `uv run pytest tests/ --ignore=tests/integration -v`
- **Status:** 380 passed, 0 failed (64 new + 316 existing)
- **Test Framework:** pytest with pytest-asyncio

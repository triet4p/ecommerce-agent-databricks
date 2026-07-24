# Conversation Persistence Contract

## S3-A1: Lakebase Autoscaling Availability

- **Workspace:** `dbc-5d26f2a2-84ca.cloud.databricks.com` (AWS us-east-2)
- **CLI:** Databricks CLI v1.8.0 with `postgres` commands available (Beta)
- **Lakebase Autoscaling:** Available — `databricks postgres list-projects` returns an
  empty list (no existing projects), confirming the API surface is accessible.
- **No existing Lakebase resources** — a new project will be created for this sprint.

## S3-A2: Naming Contract

| Aspect | Value |
|--------|-------|
| Project name | `ecommerce-agent-conversations` |
| Display name | `Ecommerce Agent Conversations` |
| Branch | `production` (auto-created with project) |
| Database | `conversation_store` (new, within production branch) |
| Schema | `conversations` (created by app service principal on startup) |
| Region | AWS us-east-2 |
| Catalog (UC) | `ecommerce_agent` (existing, for optional audit feed) |
| Dev workspace root | `/Workspace/Users/${user}/.bundle/ecommerce-agent/dev` |
| Prod workspace root | `/Workspace/Users/${user}/.bundle/ecommerce-agent/prod` |

## S3-A3: Trusted User Identity Source

- **Production:** `X-Forwarded-User` header passed by Databricks Apps to the Chat UI
  App. Databricks Apps injects this as a trusted header containing the authenticated
  end-user email.
- **Local development:** `DATABRICKS_USERNAME` environment variable. When
  `X-Forwarded-User` is absent and the app runs outside Databricks Apps, fall back
  to the workspace user from the SDK (`current_user.me().userName`).
- The Agent App receives the calling **App identity** (OAuth app-to-app), not the
  end-user identity. Conversation ownership is handled entirely in the Chat UI App.
- **Storage:** The `conversations.owner` column stores the normalized email from
  `X-Forwarded-User`. All queries filter by this column.

## S3-A4: Conversation Ownership and Authorization Rules

| Operation | Authorization |
|-----------|---------------|
| Create conversation | `owner = X-Forwarded-User`; always creates as self |
| List conversations | `WHERE owner = X-Forwarded-User` |
| Get conversation | `WHERE id = :id AND owner = :user` |
| Update title | `WHERE id = :id AND owner = :user` |
| Soft-delete conversation | `WHERE id = :id AND owner = :user` |
| Hard-delete conversation | Admin only (not exposed to end-user API) |
| Read turns/items | `WHERE conversation_id IN (SELECT id FROM conversations WHERE owner = :user)` |
| Create turn | Verified via conversation ownership before insert |

- One user **cannot** read, modify, or infer another user's conversations.
- No admin bypass endpoints exist in the Chat UI App.
- The Agent App never sees or stores user identity; all requests pass through
  the Chat UI App.

## S3-A5: Canonical Persisted Item Contract

Persisted items mirror the Sprint 2 Responses API event types with minimal
additions for sequencing and ownership metadata.

**`conversation_items` table** stores individual canonical items:

```yaml
columns:
  - id: UUID (PK, gen_random_uuid())
  - conversation_id: UUID (FK → conversations.id, NOT NULL)
  - turn_id: UUID (FK → turns.id, NOT NULL)
  - sequence: INTEGER (monotonic per conversation, NOT NULL)
  - item_type: VARCHAR(64) (NOT NULL) — one of:
      "message", "function_call", "function_call_output"
  - role: VARCHAR(32) — "user" | "assistant" | "tool"
  - payload: JSONB (NOT NULL) — the canonical item body
  - item_key: VARCHAR(255) — idempotency key for items
  - created_at: TIMESTAMPTZ (default NOW())

constraints:
  - PK: id
  - FK: conversation_id → conversations.id ON DELETE CASCADE
  - FK: turn_id → turns.id ON DELETE CASCADE
  - UNIQUE: (conversation_id, turn_id, sequence)
```

**Payload structure** per `item_type`:

| `item_type` | `payload` fields |
|---|---|
| `message` | `{type: "message", id, role, content: [{type: "output_text", text, annotations?}]}` |
| `function_call` | `{type: "function_call", id, call_id, name, arguments}` |
| `function_call_output` | `{type: "function_call_output", call_id, output}` |

## S3-A6: Context Budget, Session Maximum, Retention

- **Context budget:** 100,000 characters (Agent App safety limit).
- **Session maximum:** No hard item count limit — items are bounded by the
  character budget applied at serialization time.
- **Retention default:** 30 days from last activity (`conversations.updated_at`).
  Items older than this are eligible for hard deletion by a background sweep
  (not part of MVP, but the column exists).
- **Delete semantics:** Soft-delete (`conversations.deleted_at`). Hard deletion
  is deferred to an operational script. Soft-deleted conversations are excluded
  from listing and loading but remain in the database for a retention window.
- **No summarization:** All items are kept in full; no compaction is applied.
  The budget limits what is sent to the Agent App, not what is stored.

## S3-A7: Fields That Must Never Be Stored

The following fields MUST be stripped from payloads before persisting:

1. Raw provider reasoning content (`reasoning_content`, `reasoning` fields)
2. OAuth credentials, tokens, or passwords
3. `Authorization` / `X-Forwarded-User` / `Cookie` headers
4. Raw HTTP request bodies beyond the canonical input
5. `mlflow_trace_id` — stored on the `turn` record, NOT in item payloads
6. Internal deployment environment variables
7. App service principal credentials
8. Any field matching `token|secret|password|key|authorization|credential`
   (case-insensitive regex)

A `payload_redactor` function enforces this before every insert.

---

## Schema Definitions

### `conversations` table

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner           VARCHAR(255) NOT NULL,
    title           VARCHAR(500) NOT NULL DEFAULT 'New conversation',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_conversations_owner ON conversations(owner, updated_at DESC);
```

### `turns` table

```sql
CREATE TABLE IF NOT EXISTS turns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    client_request_id VARCHAR(255) NOT NULL,
    sequence        INTEGER NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'active',
        -- 'active' | 'completed' | 'failed' | 'cancelled'
    mlflow_trace_id VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    UNIQUE (conversation_id, client_request_id),
    UNIQUE (conversation_id, sequence)
);

CREATE INDEX idx_turns_conversation ON turns(conversation_id, sequence ASC);
```

### `conversation_items` table

```sql
CREATE TABLE IF NOT EXISTS conversation_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    turn_id         UUID NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
    sequence        INTEGER NOT NULL,
    item_type       VARCHAR(64) NOT NULL,
    role            VARCHAR(32),
    payload         JSONB NOT NULL,
    item_key        VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (conversation_id, turn_id, sequence)
);

CREATE INDEX idx_items_conversation ON conversation_items(conversation_id, sequence ASC);
CREATE INDEX idx_items_turn ON conversation_items(turn_id, sequence ASC);
```

---

## History Replay Contract

The replay pipeline converts stored items back into Responses API input format:

```
1. SELECT items FROM conversation_items
   WHERE conversation_id = :id
   ORDER BY sequence ASC

2. Convert each item:
   - message/assistant → {"role": "assistant", "content": [...]}
   - function_call → {"role": "assistant", "tool_calls": [...]}
   - function_call_output → {"role": "tool", "content": "...", "tool_call_id": "..."}

3. Append new user message:
   {"role": "user", "content": "new message"}

4. Serialize to JSON and check length ≤ 100,000 chars.
   If exceeded, return "new-session" action to user instead.
```

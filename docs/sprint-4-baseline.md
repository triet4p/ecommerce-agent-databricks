# Sprint 4 — Baseline and Migration Contract

## S4-A1: Pinned Template Revision

| Field | Value |
|-------|-------|
| Template repository | `databricks/app-templates` |
| Template directory | `e2e-chatbot-app-next` |
| Pinned commit | `2a4c79296aae89c8a05e7825c61e0d94ad34c944` |
| Date | 2026-07-01 |
| Message | "Remove outdated note about postgres resource not being supported as a dependency for autoscaling Lakebase instances" |
| License | Apache 2.0 (full text at `docs/sprint-4-template-license.md`) |

### Adaptation Note

The pinned template is a *reference implementation* for a general-purpose Databricks
chat application. Every file is adapted to this repository's architecture: the
existing Agent App, MCP facade, Sprint 2 event contract, Sprint 3 Lakebase schema,
and separate `ecommerce-agent-chat-ui` App boundary are never replaced by a
template file. Where the template's design conflicts with this repository's
architecture, the repository's existing contract wins.

### Template License

The template is published under the Apache 2.0 license by Databricks, Inc. See
`docs/sprint-4-template-license.md` for the full license text.

---

## S4-A2: Template Feature Inventory

| # | Feature | Decision | Rationale |
|---|---------|----------|-----------|
| 1 | Vite + React 18 SPA | **Keep** | Modern build tooling; replaces Streamlit rerun model |
| 2 | Express 5 server | **Keep** | Required for API proxy and static file serving |
| 3 | AI SDK (`ai`, `@ai-sdk/react`) | **Adapt** | Replace `useChat` with custom React hook consuming the Sprint 2 event contract. The template's AI SDK assumes direct Model Serving endpoint access; our proxy layer matches the Sprint 2 protocol |
| 4 | Radix UI primitives | **Keep** | Accessible component foundation (Dialog, Collapsible, Alert, etc.) |
| 5 | Tailwind CSS v4 | **Keep** | Standard styling approach; replace template tokens with project palette |
| 6 | Server-side App-to-App OAuth | **Adapt** | Our Agent App is at the chat UI server, not a Model Serving endpoint. The OAuth proxy layer reuses the template pattern but targets App-to-App |
| 7 | Drizzle ORM | **Adapt** | Replace with direct `psycopg`-style SQL calls from Node to preserve Sprint 3 schema exactly. Drizzle migrations must never alter the Sprint 3 tables |
| 8 | Lakebase conversation history | **Adapt** | Our schema is Sprint 3's. The template's DB schema is not used. The Node server adapts the same SQL operations |
| 9 | Streaming response handling | **Adapt** | Template uses AI SDK streaming; we use raw SSE parsing matching the Sprint 2 contract |
| 10 | Feedback UI (thumbs up/down) | **Defer** | Optional per Sprint 4 plan; not blocking the cutover |
| 11 | Playwright test suite | **Keep** | Essential for verification across streaming, history, and tool UX |
| 12 | Biometric linting | **Keep** | Replace ESLint with Biome per template convention |
| 13 | `framer-motion` animations | **Keep** | Subtle message entry and tool card animations |
| 14 | `lucide-react` icons | **Keep** | Standard icon set for sidebar, buttons, tool cards |
| 15 | `react-router-dom` routing | **Keep** | Required for conversation views and settings |
| 16 | `@chat-template/auth` package | **Adapt** | Replace with our X-Forwarded-User identity logic |
| 17 | `@chat-template/core` package | **Adapt** | Replace with Sprint 2/3 type definitions |
| 18 | `@chat-template/db` package | **Adapt** | Replace with Node-based repository matching Sprint 3 SQL |
| 19 | `@chat-template/utils` package | **Keep** | General utilities (formatting, validation) |
| 20 | `@chat-template/ai-sdk-providers` | **Remove** | Our proxy server handles all AI SDK interaction; the client never calls provider SDKs directly |

---

## S4-A3: Databricks Apps Support Path

### Current Topology (unchanged)

```
Browser → Chat UI App (Node/Express) → [App-to-App OAuth] → Agent App (Python)
                ↓
          Lakebase (Sprint 3)
```

### Key Findings

1. **Agent on Apps, not Model Serving.** The Agent App is a Databricks App
   (`ecommerce-agent-app`), not a Model Serving endpoint. The Chat UI App
   (`ecommerce-agent-chat-ui`) uses App-to-App OAuth to call it. This is
   supported by Databricks Apps — one App can grant `CAN_USE` permission to
   another App.

2. **The template default adapter targets Model Serving endpoints.** The
   `@databricks/ai-sdk-provider` package is designed for Model Serving
   endpoints. We **replace** this with a custom proxy server that:
   - Uses `WorkspaceClient` (Python) or Databricks SDK for Node to authenticate
   - Calls the Agent App's `/api/responses` endpoint
   - Streams the Sprint 2 event contract back to the browser

3. **X-Forwarded-User identity.** The Chat UI server receives the trusted
   end-user identity via the `X-Forwarded-User` header injected by Databricks
   Apps. This is used for conversation ownership — the same mechanism as
   Sprint 3.

4. **App-to-App OAuth.** The relationship is:
   - Chat UI App (Node) ↔ Agent App (Python): App-to-App OAuth via
     Databricks SDK `config.authenticate()`
   - Browser ↔ Chat UI App: Same-origin API calls (no token exposed to browser)

### Permission Model

| Direction | Auth Mechanism | Scope |
|-----------|---------------|-------|
| Browser → Chat UI | Databricks Apps session cookie | User authentication (handled by Databricks) |
| Chat UI → Agent App | App-to-App OAuth (SDK) | Agent App `CAN_USE` permission |

**Critical:** The browser must never receive the Agent App's OAuth token, the
Lakebase credential, or any service principal secret.

---

## S4-A4: Same-Origin Browser API Contract

The Chat UI server exposes the following endpoints on the same origin.
All are prefixed with `/api/` and return JSON unless otherwise specified.

### Conversations

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/conversations` | List conversations for the authenticated user |
| `POST` | `/api/conversations` | Create a new conversation |
| `GET` | `/api/conversations/:id` | Get conversation with all items |
| `PATCH` | `/api/conversations/:id` | Update conversation title |
| `DELETE` | `/api/conversations/:id` | Soft-delete a conversation |

### Turns / Streaming

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/conversations/:id/turns` | Create a new turn (idempotent via `clientRequestId`) |
| `POST` | `/api/conversations/:id/turns/:turnId/stream` | SSE stream: send user message, receive event stream |
| `POST` | `/api/conversations/:id/turns/:turnId/cancel` | Cancel an active turn |
| `POST` | `/api/conversations/:id/turns/:turnId/retry` | Retry a failed turn |

### Streaming Event Contract (SSE)

The SSE stream uses the **identical** Sprint 2 event contract. Every event
is a `data:` line with JSON, terminated by `data: [DONE]`.

See [docs/chat-ui-event-contract.md](./chat-ui-event-contract.md) for the full
event type definitions: `response.output_text.delta`, `response.output_item.done`,
`error`, `response.completed`.

### Feedback (deferred)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/conversations/:id/turns/:turnId/feedback` | Submit feedback (thumbs up/down) |

**Note:** Feedback is deferred from Sprint 4 but the endpoint slot is reserved.

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check (App, Lakebase, Agent App reachability) |

### Error Responses

All errors follow a consistent shape:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Human-readable description"
  }
}
```

Standard codes: `NOT_FOUND`, `UNAUTHORIZED`, `BAD_REQUEST`, `CONFLICT`,
`INTERNAL_ERROR`, `TIMEOUT`.

---

## S4-A5: Frozen TypeScript Types

TypeScript types are generated in `chat_ui/packages/core/src/` and mirror
the Sprint 2 event contract and Sprint 3 data models.

### Sprint 2 Event Types

```typescript
// Event type discriminators
type SSEEventType =
  | 'response.output_text.delta'
  | 'response.output_item.done'
  | 'response.completed'
  | 'error';

// SSE event base
interface SSEEvent {
  type: SSEEventType;
}

// Text delta
interface TextDeltaEvent extends SSEEvent {
  type: 'response.output_text.delta';
  item_id: string;
  delta: string;
  content_index: number;
  output_index: number;
}

// Output item done
interface OutputItemDoneEvent extends SSEEvent {
  type: 'response.output_item.done';
  item: OutputItem;
  output_index: number;
}

type OutputItem =
  | TextMessageOutput
  | FunctionCallOutput
  | FunctionCallResultOutput;

interface TextMessageOutput {
  type: 'message';
  id: string;
  role: 'assistant';
  content: Array<{ type: 'output_text'; text: string; annotations: unknown[] }>;
}

interface FunctionCallOutput {
  type: 'function_call';
  id: string;
  call_id: string;
  name: string;
  arguments: string;
}

interface FunctionCallResultOutput {
  type: 'function_call_output';
  call_id: string;
  output: string;
}

// Error
interface ErrorEvent extends SSEEvent {
  type: 'error';
  code: string;
  message: string;
}

// Response completed
interface ResponseCompletedEvent extends SSEEvent {
  type: 'response.completed';
  response: {
    id: string;
    status: 'completed';
    output: OutputItem[];
  };
}
```

### Sprint 3 Data Model Types

```typescript
// Conversation
interface Conversation {
  id: string;           // UUID
  owner: string;
  title: string;
  created_at: string;   // ISO 8601
  updated_at: string;   // ISO 8601
  deleted_at?: string;  // ISO 8601, null if not deleted
}

interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

// Turn
type TurnStatus = 'active' | 'completed' | 'failed' | 'cancelled';

interface Turn {
  id: string;
  conversation_id: string;
  client_request_id: string;
  sequence: number;
  status: TurnStatus;
  mlflow_trace_id?: string;
  created_at: string;
  completed_at?: string;
}

// Item
type ItemType = 'message' | 'function_call' | 'function_call_output';

interface ConversationItem {
  id: string;
  conversation_id: string;
  turn_id: string;
  sequence: number;
  item_type: ItemType;
  role?: string;
  payload: Record<string, unknown>;
  item_key?: string;
  created_at: string;
}
```

---

## S4-A6: Cutover, Rollback, and Database Compatibility Plan

### Cutover Sequence

```
Phase 1: Deploy new Chat UI alongside Streamlit (S4-E8)
  - New Node app deployed to `ecommerce-agent-chat-ui` App
  - Streamlit app still available at a different route or preserved artifact
  - Both apps share the same Lakebase schema (read-compatible)

Phase 2: Credentialed feature parity (S4-E9)
  - Verify streaming, tool use, two-turn history, refresh, OAuth, user isolation
  - Compare results between React and Streamlit implementations

Phase 3: Streamlit removal (S4-E11)
  - Only after Phase 2 passes
  - Remove `ecommerce_agent/apps/chat_ui/app.py` and Streamlit dependency

Phase 4: Documentation update (S4-E12)
  - Update architecture diagrams, README, deployment instructions
```

### Rollback Plan

**Rollback trigger:** Any release-blocking defect in the React UI that cannot be
fixed within 2 hours.

**Rollback steps:**
1. Redeploy the previous Streamlit source to the `ecommerce-agent-chat-ui` App:
   `databricks bundle deploy -t dev --resource ecommerce_agent_chat_ui`
2. Verify Streamlit starts and serves requests
3. The React build artifact is replaced; no database rollback needed
4. Lakebase schema and data are unchanged — rollback only affects the UI layer

### Database Compatibility

The Node server accesses the **exact same** Sprint 3 Lakebase schema:

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL DEFAULT 'New conversation',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    client_request_id VARCHAR(255) NOT NULL,
    sequence INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    mlflow_trace_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    UNIQUE (conversation_id, client_request_id),
    UNIQUE (conversation_id, sequence)
);

CREATE TABLE IF NOT EXISTS conversation_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    turn_id UUID NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    item_type VARCHAR(64) NOT NULL,
    role VARCHAR(32),
    payload JSONB NOT NULL,
    item_key VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (conversation_id, turn_id, sequence)
);
```

**Rules:**
- No ALTER TABLE or DROP TABLE on Sprint 3 tables
- No new tables that duplicate Sprint 3 data
- All new Node code accesses existing tables with SELECT/INSERT/UPDATE only
- The Streamlit app continues to work with the same schema during cutover

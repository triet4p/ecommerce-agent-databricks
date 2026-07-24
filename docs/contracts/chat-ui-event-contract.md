# Chat UI App Event Contract

> Canonical wire and display contract shared by React and Streamlit clients.

## Status

**Frozen as of Sprint 2.** Any change to public event semantics after this
sprint requires coordinated migration through Sprint 3 (persistence) and
Sprint 4 (React reducer).

## Purpose

This document defines the wire contract between the Agent App (producer) and
the Chat UI App (consumer). Both sides must adhere to this contract
independently: the Agent App emits events in this format and the Chat UI
parses only these fields.

---

## 1. Inbound Request Fields

The Chat UI App sends `POST <agent_app_url>/api/responses` with the following
JSON body. Fields not listed below are silently ignored by the Agent App.

| Field | Type | Required | Description |
|---|---|---|---|
| `input` | `list[message]` | **yes** | Ordered chat history. Each entry has `role` (`"user"`, `"assistant"`, `"system"`, `"developer"`) and `content` (string or list of content blocks). The last entry is the current user turn. |
| `stream` | `bool` | no | When `true`, the response is an SSE stream. Default `false`. |
| `custom_inputs` | `dict` | no | Arbitrary JSON-serializable context. Used for `required_operation` routing. |
| `context` | `object` | no | `{ "conversation_id": "…", "user_id": "…" }` — set by the App, not by the Chat UI. |

### Example (streaming request)

```json
{
  "input": [
    {"role": "system", "content": "You are a support agent."},
    {"role": "user", "content": "What is my order status?"}
  ],
  "stream": true
}
```

---

## 2. Outbound SSE Event Types

When `stream: true` is set, the response is a Server-Sent Events (SSE) stream.
Each event is a `data:` line containing a JSON object, terminated by
`data: [DONE]`.

The following event types are **supported** by the Chat UI. Events of any
other type are silently ignored by the parser.

### 2.1 `response.output_text.delta`

Emitted for each incremental text chunk during assistant generation.

```json
{
  "type": "response.output_text.delta",
  "item_id": "msg_<uuid>",
  "delta": "Hello",
  "content_index": 0,
  "output_index": 0
}
```

| Field | Type | Description |
|---|---|---|
| `type` | `string` | Always `"response.output_text.delta"` |
| `item_id` | `string` | Stable ID shared across all deltas of the same output item |
| `delta` | `string` | The incremental text chunk (may be empty for non-text events) |
| `content_index` | `int` | Index within the content array (always 0 for single-content items) |
| `output_index` | `int` | Index within the overall output array |

Multiple deltas with the same `item_id` are aggregated into one assistant
message on the client.

### 2.2 `response.output_item.done`

Emitted when an output item (text message, function call, or function call
result) is complete. The `item` field carries the completed payload.

#### 2.2.1 Text message item

```json
{
  "type": "response.output_item.done",
  "item": {
    "type": "message",
    "id": "msg_<uuid>",
    "role": "assistant",
    "status": "completed",
    "content": [
      {"type": "output_text", "text": "Hello world!", "annotations": []}
    ]
  },
  "output_index": 0
}
```

#### 2.2.2 Function call item

```json
{
  "type": "response.output_item.done",
  "item": {
    "type": "function_call",
    "id": "fc_<uuid>",
    "call_id": "call_<uuid>",
    "name": "get_order_status",
    "arguments": "{\"order_id\": \"o-123\"}"
  },
  "output_index": 1
}
```

#### 2.2.3 Function call output item (tool result)

```json
{
  "type": "response.output_item.done",
  "item": {
    "type": "function_call_output",
    "call_id": "call_<uuid>",
    "output": "{\"status\": \"shipped\"}"
  },
  "output_index": 2
}
```

### 2.3 `error`

Emitted when the stream terminates due to an error.

```json
{
  "type": "error",
  "code": "INTERNAL_ERROR",
  "message": "Tool execution failed: TimeoutException"
}
```

| Field | Type | Description |
|---|---|---|
| `code` | `string` | Machine-readable error code (`"INTERNAL_ERROR"`, `"BAD_REQUEST"`, `"TIMEOUT"`) |
| `message` | `string` | Human-readable error description |

### 2.4 `response.completed`

Emitted at the very end of a successful stream, before `[DONE]`.

```json
{
  "type": "response.completed",
  "response": {
    "id": "resp_<uuid>",
    "object": "response",
    "status": "completed",
    "output": [...]
  }
}
```

### 2.5 Stream termination

All streams end with a line containing exactly:

```
data: [DONE]
```

This is NOT a JSON line. The SSE parser must recognise `[DONE]` as the
stream-termination signal.

---

## 3. Correlation Rules

### 3.1 Response ID

- Every stream corresponds to one logical response.
- The response ID (`resp_<uuid>`) is created by the Agent App for each
  `predict_stream` call.
- The Chat UI does not need to persist the response ID, but the Agent App
  includes it in the `response.completed` event for traceability.

### 3.2 Item ID

- `item_id` in `response.output_text.delta` events links text deltas to
  their eventual `response.output_item.done` event.
- All deltas with the same `item_id` belong to the same assistant text output.
- The `item` payload in `response.output_item.done` contains the aggregated
  content under the same `id`.

### 3.3 Tool Call ID

- `call_id` in `function_call` items and `function_call_output` items links
  a tool result to its originating tool call.
- The Chat UI groups tool calls and results into one timeline card when their
  `call_id` values match.

### 3.4 Request ID (Databricks Apps)

- `X-Request-Id` header from the Databricks Apps reverse proxy provides a
  UUID for the HTTP request.
- Used for log correlation and debugging, not for business logic.

---

## 4. Browser-Safe Tool Display Policy

Every tool call and result that reaches the browser must pass through the
following safety layers before rendering.

### 4.1 Allowlisting

Only tool names matching an allowlist are displayed. The allowlist is derived
from the agent's configured tool set at deployment time. Unknown tool names are
displayed as `"Unknown tool"`.

### 4.2 Argument truncation

Tool arguments exceeding **500 characters** are truncated to 500 characters
with `…` appended. The full arguments remain in the backend trace but never
reach the browser.

### 4.3 Argument redaction

Arguments whose keys match the following patterns are **redacted before
rendering**:

- Any key containing `token`, `secret`, `password`, `key`, `authorization`,
  `credential` (case-insensitive)
- Any key whose value exceeds **2000 characters**

Redacted values are replaced with `"<redacted>"`.

### 4.4 Output truncation

Tool output (function_call_output) exceeding **1000 characters** is truncated
to 1000 characters with `…` appended.

### 4.5 Friendly labels

Tool names are mapped to human-readable labels:

| Tool name (internal) | Display label |
|---|---|
| `get_order_status` | 🔍 Order lookup |
| `get_customer_order_history` | 📋 Order history |
| `search_policy_docs` | 📄 Policy search |
| `check_refund_eligibility` | 💳 Refund check |
| `get_seller_performance` | 📊 Seller rating |
| `get_shipping_delay_stats` | 🚚 Shipping status |
| `compute_delay_severity` | ⏱ Delay analysis |
| `customer_value_score` | ⭐ Customer value |
| `list_skills` | 📚 Available guides |
| `load_skill` | 📖 Load guide |

Any unmapped tool name is displayed as `🔧 <name>`.

---

## 5. Thinking-Visualization Policy

### 5.1 Public vs. Private

| Category | Content | Visibility |
|---|---|---|
| **Private** | Raw `reasoning_content` from DeepSeek provider | Never leaves the Agent App |
| **Public** | `response.output_text.delta` deltas | Streamed to the browser |
| **Public** | Tool call/result items | Streamed to the browser |
| **Public** | Error events | Streamed to the browser |

### 5.2 Phase labels

The Chat UI derives safe display labels from the event type sequence, not from
raw model output:

| Observed event pattern | Display label |
|---|---|
| `response.output_text.delta` (no tool calls) | 🤖 Composing… |
| `response.output_text.delta` → `function_call` | 🔍 Analyzing… |
| `function_call` emitted | 🔧 Running tool… |
| `function_call_output` received | ✅ Tool complete |
| Multiple tool calls in sequence | 🔄 Multi-step… |
| `error` received | ❌ Error |
| Stream idle > 30s | ⏳ Still working… |

### 5.3 Enforcement

The Agent App **must never** include `reasoning_content`, `reasoning` blocks,
or any raw provider chain-of-thought in the public SSE stream. This is
enforced by:

1. The `_responses_safe_messages()` filter in `agent_core/orchestrator.py`
   strips reasoning content blocks from messages serialized to the client.
2. A repository-level test (`test_banned_symbols.py` and S2-D3) scans for
   `reasoning_content` in public response payloads.
3. The DeepSeek adapter contract (`deepseek_adapter/tests/test_adapter_contract.py`)
   verifies that reasoning is never leaked at the provider boundary.

---

## 6. Error Propagation

### 6.1 SSE-level errors

Errors encountered during streaming are propagated as `error` SSE events
(see §2.3). The Chat UI must:

- Detect the `error` event type and display a terminal error state.
- NOT render any partial output as a completed answer.
- Offer a retry action that re-sends the original user message.

### 6.2 HTTP-level errors

- 4xx/5xx HTTP status codes from `POST /api/responses` indicate a non-streaming
  error. The response body may contain error details.
- The Chat UI must catch HTTP errors with `response.raise_for_status()`.
- 401/403 errors indicate an authentication problem and should display a
  "Re-authenticate" action.

### 6.3 Disconnect handling

- If the SSE stream disconnects before `[DONE]`, the Chat UI must display
  "Connection lost — your message may not have been answered" and offer retry.
- Partial output that was received before the disconnect must be discarded
  (not retained as a completed answer).

### 6.4 Timeout handling

- The Chat UI enforces a 180-second outer timeout on the HTTP request.
- If the timeout expires before `[DONE]`, the request is cancelled and the
  user sees a timeout error with retry.

---

## 7. Non-Streaming Compatibility

The MCP facade (`ecommerce_agent/apps/mcp_facade/`) and all non-streaming
clients use `stream: false`. Their contract remains:

- Response is a single JSON object conforming to `ResponsesAgentResponse`.
- Extract the terminal assistant message via `extract_response_text()`.
- No SSE parsing needed.

# Sprint 2 Closeout Summary

**Completed:** 2026-07-21
**Event contract:** Frozen as of Sprint 2 — changes require coordinated migration through Sprint 3 (persistence) and Sprint 4 (React reducer).

## Summary

Delivered a stable, UI-independent streaming contract that emits real assistant
text deltas, complete tool-call and tool-result events, safe progress states,
and terminal errors, then visualized that contract in the existing Streamlit
Chat UI without exposing raw provider reasoning.

## Deliverables

### A. Public event contract (frozen)

| Artifact | Description |
|---|---|
| `docs/chat-ui-event-contract.md` | Complete wire contract: inbound request fields, outbound SSE event types (text deltas, done events, errors, completion), correlation rules, tool display policy, thinking-visualization policy, error propagation, non-streaming compatibility |
| `ecommerce_agent/apps/chat_ui/stream_types.py` | Typed Pydantic models for all supported SSE events (`TextDeltaEvent`, `OutputItemDoneEvent`, `ErrorEvent`, `ResponseCompletedEvent`) with a `parse_stream_event()` dispatcher |
| `ecommerce_agent/apps/chat_ui/display_policy.py` | Browser-safe tool display policy: friendly labels, argument allowlisting/truncation/redaction, output truncation, and safe phase-label derivation from event types |

### B. Real token and agent-event streaming

| Change | Files |
|---|---|
| Dual stream-mode support | `agent_core/orchestrator.py` — `predict_stream()` now uses `stream_mode=["updates", "messages"]` |
| Text delta emission | `_message_chunk_to_delta_events()` converts `AIMessageChunk` → `response.output_text.delta` events |
| Text aggregation | `_TextAggregator` tracks item_id → accumulated text; `flush_done_events()` emits aggregated `response.output_item.done` |
| Deduplication | `_deduplicate_stream_events()` suppresses completed text messages from updates mode when already streamed as deltas |
| Error propagation | Stream errors caught and yielded as `error` events; no completion event follows an error |
| Operation gate preserved | `buffer_until_verified` still blocks events until required tool verification; dual-mode events are buffered consistently |

### C. Streamlit streaming UI

| Change | Files |
|---|---|
| Streaming request | `app.py` sends `stream: True` with `requests.post(..., stream=True)` |
| Incremental SSE parser | `sse_parser.py` — `SSESparser` handles fragmented boundaries, comments, [DONE]; `JSONEventParser` deserializes JSON |
| Text delta rendering | `text_placeholder.markdown()` updated incrementally with cursor indicator |
| Tool status cards | `st.status()` with running/complete states for correlated tool call/result pairs |
| Phase labels | `phase_placeholder.caption()` shows safe labels (Composing… / Running tool… / ✅ Tool complete / ❌ Error) |
| Error & retry | Timeout, connection errors, and error events displayed with retry button |
| Non-streaming compatibility | `response_output.py` unchanged for MCP facade and non-streaming tests |

### D. Verification and deployment

| Test | Count | Status |
|---|---|---|
| SSE parser tests (D1) | 11 tests | ✅ All pass |
| Stream reducer tests (D2) | 20 tests | ✅ All pass |
| Security/repository tests (D3) | 8 tests | ✅ All pass |
| Agent App contract tests (D4) | 2 tests | ✅ All pass |
| Tool-loop contract tests (D5) | 2 tests | ✅ All pass |
| Unit test suite | 309 tests | ✅ All pass (11 Databricks-credentialed skipped) |
| Ruff check | — | ✅ 0 errors |
| Ruff format | 71 files | ✅ All formatted |

## Files created

```
ecommerce_agent/apps/chat_ui/stream_types.py      # Typed event models
ecommerce_agent/apps/chat_ui/sse_parser.py         # Incremental SSE parser
ecommerce_agent/apps/chat_ui/display_policy.py     # Tool display & thinking policy
tests/agent_core/test_streaming_contract.py         # Streaming contract tests
tests/ecommerce_agent/test_sse_parser.py            # SSE parser tests
tests/ecommerce_agent/test_stream_reducers.py       # Reducer/aggregator tests
tests/ecommerce_agent/test_stream_security.py       # Security regression tests
docs/chat-ui-event-contract.md                     # Frozen event contract
```

## Files modified

```
agent_core/orchestrator.py          # Dual stream-mode, dedup, error handling
ecommerce_agent/apps/chat_ui/app.py # Streaming Streamlit UI
tests/ecommerce_agent/test_agent_server_contract.py  # D4/D5 contract tests
tests/agent_core/test_operation_gate_orchestration.py # Updated FakeGraph format
```

## Deferred to Sprint 3

- Chat history persistence (Lakebase)
- Session replay from persisted history
- Intent-to-workflow routing (C11)

## Deferred to Sprint 4

- React UI replacement
- Styling and component investment
- Production tool card UX

## Metrics

- **Text delta count:** Verified ≥2 real deltas for deterministic multi-chunk response
- **Tool call/result correlation:** Each function_call paired with function_call_output by matching call_id
- **Dedup:** Zero duplicate text items when both stream modes active
- **Error isolation:** Errors never followed by completion events
- **Security:** Zero reasoning_content, authorization values, or secret patterns in public payloads

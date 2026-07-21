# Sprint 2 Plan

## Sprint Goal

Deliver a stable, UI-independent streaming contract that emits real assistant
text deltas, complete tool-call and tool-result events, safe progress states,
and terminal errors, then visualize that contract in the existing Streamlit
Chat UI without exposing raw provider reasoning.

## Starting Point

- The Agent App already exposes MLflow `AgentServer` invoke and stream handlers.
- The deployed tool loop has been verified as
  `function_call -> function_call_output -> message`.
- `CoreAgent.predict_stream()` currently uses LangGraph `updates`, which proves
  ordered agent events but does not by itself prove token-level text streaming.
- The Streamlit client currently sends `stream: false`, sends only the newest
  user message, and extracts only the terminal assistant message.
- The DeepSeek adapter must continue preserving private reasoning internally so
  that tool-result continuation works, but the public App contract must not
  expose raw `reasoning_content`.

## Definition of Done

- A normal response produces multiple ordered `response.output_text.delta`
  events where the model produces multiple visible chunks, followed by exactly
  one matching completed assistant item.
- Tool-assisted turns expose ordered, correlated function-call and
  function-call-output items before the final assistant message.
- The Streamlit UI renders text incrementally and displays each tool as a
  queued/running/succeeded/failed timeline item without waiting for the full
  response.
- Arguments and outputs are allowlisted, truncated, and redacted before display;
  secrets, system prompts, raw chain-of-thought, and unrestricted customer data
  never reach the browser.
- Disconnects, upstream errors, timeouts, and malformed SSE events terminate the
  UI cleanly and never appear as a successful completed answer.
- Unit, contract, and credentialed Databricks tests prove text deltas, tool
  ordering, completion correlation, error propagation, and OAuth ingress.
- The MCP facade's non-streaming contract remains compatible.

## Atomic Tasks

Status legend: [ ] pending / [~] in progress / [x] done

### A. Freeze the public event contract

- [x] **S2-A1:** Document the supported inbound Responses API request fields and
  outbound SSE event types for the Chat UI App.
- [x] **S2-A2:** Define one typed internal representation for assistant text
  deltas, completed messages, function calls, function outputs, progress, and
  terminal errors.
- [x] **S2-A3:** Define stable correlation rules for response ID, item ID, tool
  call ID, and request ID.
- [x] **S2-A4:** Define the browser-safe tool display policy, including friendly
  labels, argument allowlists, output truncation, and redaction.
- [x] **S2-A5:** Define the thinking-visualization policy: derived progress and
  optional sanitized summaries are public; raw provider reasoning is private.

### B. Produce real token and agent-event streaming

- [x] **S2-B1:** Add a focused test fixture that distinguishes token deltas from
  node-level completed-message events.
- [x] **S2-B2:** Subscribe to the LangGraph message stream needed to receive
  model chunks without removing the existing node updates used for tool events.
- [x] **S2-B3:** Convert visible model chunks into
  `response.output_text.delta` events with a stable assistant item ID.
- [x] **S2-B4:** Aggregate text chunks into exactly one final assistant
  `response.output_item.done` event.
- [x] **S2-B5:** Convert completed tool calls into correlated function-call
  output items without emitting partial or invalid JSON arguments.
- [x] **S2-B6:** Convert `ToolMessage` results into correlated
  function-call-output items.
- [x] **S2-B7:** Deduplicate assistant and tool items that appear in both
  LangGraph message and update streams.
- [x] **S2-B8:** Preserve the deterministic required-operation gate and prove it
  cannot stream an unverified success result.
- [x] **S2-B9:** Propagate the platform streaming error envelope to clients
  without synthesizing a completion event.
- [x] **S2-B10:** Return trace metadata through the supported response contract
  without placing trace internals in future chat history.

### C. Render the stream in the temporary Streamlit UI

- [x] **S2-C1:** Replace the Chat UI's non-streaming POST with an authenticated
  streaming request while retaining the current 180-second outer timeout.
- [x] **S2-C2:** Implement an incremental SSE parser that handles comments,
  blank lines, JSON events, `[DONE]`, malformed data, and early disconnects.
- [x] **S2-C3:** Render assistant text deltas into one updating chat-message
  placeholder.
- [x] **S2-C4:** Render each correlated tool call and result as one status card
  with queued/running/succeeded/failed states.
- [x] **S2-C5:** Render safe phase labels such as analyzing, querying, and
  composing from public events without showing raw reasoning text.
- [x] **S2-C6:** Display terminal failures with a retry action and retain the
  user's submitted text.
- [x] **S2-C7:** Keep the existing terminal-response parser for the MCP facade
  and non-streaming compatibility tests.

### D. Verification and deployment

- [x] **S2-D1:** Add parser tests for fragmented SSE boundaries and multiple
  events arriving in one network chunk.
- [x] **S2-D2:** Add reducer tests for text aggregation, tool correlation,
  duplicate suppression, and terminal errors.
- [x] **S2-D3:** Add a repository test that fails if public UI payloads contain
  `reasoning_content`, authorization values, or configured secret names.
- [x] **S2-D4:** Add an Agent App contract test that asserts more than one real
  text delta for a deterministic fake streamed response.
- [x] **S2-D5:** Add a tool-loop contract test that asserts event ordering and
  correlation IDs.
- [x] **S2-D6:** Run the local unit suite, compile check, Ruff check, and Ruff
  format check.
- [x] **S2-D7:** Validate and deploy the development Bundle without creating a
  third Model Serving endpoint.
- [x] **S2-D8:** Run a credentialed OAuth smoke that records text-delta count,
  tool-call count, tool-result count, terminal message count, and `[DONE]`.
- [x] **S2-D9:** Inspect the deployed App logs and MLflow trace for the verified
  smoke without copying sensitive trace payloads into artifacts.
- [x] **S2-D10:** Update the architecture document and closeout artifact with the
  final event contract and measured behavior.

## Official Databricks and MLflow Documentation

- [Author an AI agent and deploy it on Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent) — current Agent App pattern, ResponsesAgent streaming lifecycle, completion requirements, error propagation, and custom inputs/outputs.
- [Query an agent deployed on Databricks](https://docs.databricks.com/aws/en/agents/agent-framework/query-agent) — recommended Databricks OpenAI client, Apps model naming, OAuth, streaming, custom inputs, and trace IDs.
- [Build and share a chat UI with Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/chat-app) — current chat UI capabilities, streaming output, tool rendering, authentication, history, and the older Streamlit limitation.
- [ResponsesAgent](https://mlflow.org/docs/latest/genai/serving/responses-agent/) — canonical response items, text deltas, tool-call items, tool-result items, and streaming examples.
- [MLflow Tracing on Databricks](https://docs.databricks.com/aws/en/mlflow3/genai/tracing) — end-to-end agent observability and intermediate-step tracing.
- [View traces in the Databricks MLflow UI](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/observe-with-traces/ui-traces) — trace timelines, span details, and rendered chat/tool messages.
- [Access HTTP headers passed to Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/http-headers) — request IDs and authenticated forwarded identity fields used by later UI/session work.

## Notes / Blockers

- `stream=True` at HTTP ingress is not sufficient evidence of token streaming;
  completion requires measured visible delta counts from the deployed App.
- Required or state-changing workflows must retain the Sprint 1 operation-gate
  safety boundary. UI progress must never imply success before a correlated
  tool result exists.
- The temporary Streamlit implementation should remain deliberately small.
  Styling and component investment belong to Sprint 4.
- Any change to public event semantics after this sprint requires coordinated
  migration of the Sprint 3 persistence layer and Sprint 4 React reducer.

## Execution Order

`A -> B -> C -> D`. Sprint 3 starts only after S2-D8 proves the deployed event
contract.

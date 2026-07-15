# Lessons Learned

A log of past bugs, edge cases, and environment-specific quirks discovered during development.

**Purpose:** Prevents the agent from repeating the same mistakes. Before implementing anything non-trivial, scan this file for related gotchas. When a new bug or unexpected behavior is resolved, record it here immediately.

**Format for each entry:**

```
## [YYYY-MM-DD] <Short title of the issue>

**Symptom:** What went wrong or behaved unexpectedly.
**Root cause:** Why it happened.
**Fix / workaround:** What resolved it.
**Watch out for:** Conditions that would trigger this again.
```

---

## [2026-07-15] Model Serving endpoint waiters expire before custom images are ready

**Symptom:** `serving_endpoints.create_and_wait()` timed out at five minutes, a
bare create/update was followed by a query race, and a concurrent update failed
with `ResourceConflict` even though endpoint creation through the UI eventually
worked.
**Root cause:** Custom model images took more than five minutes to build. SDK
`create()` and `update_config()` return long-running-operation waiters; submitting
the request does not make the endpoint queryable. A second update cannot be
submitted while `state.config_update` is still in progress.
**Fix / workaround:** Use a 30-minute waiter with a status callback, recover from a
client timeout by checking whether the endpoint now exists, wait for
`NOT_UPDATING` before submitting another update, and assert both `READY` and the
active served-entity configuration before querying.
**Watch out for:** Every new registered model version can trigger another image
build. Do not infer failure from a five-minute client timeout, and do not run the
next notebook cell immediately after a bare `create()` or `update_config()`.

## [2026-07-15] ResponsesAgent runtime function tools fail standard signature enforcement

**Symptom:** `ChatDatabricks.bind_tools()` reached a ready ResponsesAgent endpoint
but Model Serving returned HTTP 400 because tool properties `name`, `description`,
and `parameters` were not defined in the schema.
**Root cause:** In MLflow 3.14.0 the standard `ResponsesAgent` model signature
serializes `tools` as `Array({type: string})`, although the runtime Pydantic `Tool`
model permits the full function-tool payload. Databricks enforces the serialized
signature before invoking the Python adapter.
**Fix / workaround:** After `mlflow.pyfunc.log_model()`, replace only the `tools`
column with optional `Array(Any)` via `mlflow.models.set_signature()`, retain the
standard ResponsesAgent output schema, and verify the widened signature before UC
registration.
**Watch out for:** Any custom ResponsesAgent endpoint that accepts tools supplied
at request time, including `ChatDatabricks.bind_tools()`, can hit this before the
agent code runs. A tool-free input example does not prove runtime tools are valid.

## [2026-07-15] DeepSeek V4 thinking mode rejects tool_choice

**Symptom:** Tool schemas passed Model Serving validation, but DeepSeek V4 returned
HTTP 400: `Thinking mode does not support this tool_choice`.
**Root cause:** DeepSeek V4 thinking mode supports tool calls but rejects the
OpenAI `tool_choice` parameter. Its thinking-mode tool loop also requires the
assistant `reasoning_content` to be replayed after a tool call.
**Fix / workaround:** Bind tools without `required`, `auto`, or a named
`tool_choice`; express the tool requirement in the prompt and assert that the tool
was actually called. The ResponsesAgent adapter must emit a reasoning item and
reconstruct it as `reasoning_content` before forwarding the next tool-result turn.
**Watch out for:** The generic Chat Completions API documents `tool_choice`, but
DeepSeek V4 thinking-mode compatibility is narrower. Do not force a tool at the
protocol level on this route.

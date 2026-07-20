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

## [2026-07-17] Required tool calls were treated as completed before their result

**Symptom:** A required tool became satisfied as soon as its call was observed;
later result handling validated empty arguments again and could raise
`ValueError`. Streaming output could already have been yielded before that
failure was discovered.
**Root cause:** Completion state was keyed only by tool name and did not retain
the validated arguments or correlate a `ToolMessage` to its tool-call ID.
**Fix / workaround:** Validate arguments once at call time, retain pending
required calls by call ID, accept completion only for a non-empty correlated
result, and buffer stream events until verification succeeds.
**Watch out for:** Tool-result messages do not repeat tool arguments. Never
re-run required-argument validation with the result message's empty payload.

## [2026-07-17] UC SQL table functions do not allow parameterized LIMIT

**Symptom:** Deploying `get_customer_order_history(customer_id, limit_n)` failed
with `INVALID_LIMIT_LIKE_EXPRESSION.IS_UNFOLDABLE` when using `LIMIT limit_n`.
**Root cause:** Databricks requires the `LIMIT` expression in a Unity Catalog SQL
table function to be constant; a function parameter is not folded there.
**Fix / workaround:** Rank customer orders with `ROW_NUMBER() OVER (ORDER BY
order_purchase_timestamp DESC)` and filter on `row_num <= limit_n` in the outer
query.
**Watch out for:** Validate DDL against a live SQL warehouse before considering
parameterized table-function SQL complete; static string tests cannot detect
this analyzer rule.

## [2026-07-17] Search-and-rerank endpoint wraps chunks in `results_json`

**Symptom:** The production retriever received one prediction with a source but
empty content and zero score even though endpoint invocation succeeded.
**Root cause:** Model version 4 returns one row per query with a JSON-string
`results_json` array, while the retriever treated the outer prediction as a
single chunk with direct `content` and `score` fields.
**Fix / workaround:** Decode and expand `results_json` into chunk dictionaries,
then map `rerank_score` to the retriever's typed `score` field.
**Watch out for:** A successful endpoint HTTP response does not prove the client
contract. Smoke test that returned chunks have non-empty content/source and
parsed scores after every model-version deployment.

## [2026-07-17] Optional SSE requests were buffered behind required-operation checks

**Symptom:** An optional/read-only streaming request consumed all graph events
before its first SSE event was yielded.
**Root cause:** The required-operation gate buffered every request, even when no
required operation was configured for that deployment.
**Fix / workaround:** Stream immediately when the gate has no required policies;
retain buffering only where a required workflow is configured until C11 adds
intent-level routing.
**Watch out for:** C13 protects required-operation completion, but it must not
silently turn ordinary optional tool requests into non-streaming responses.

## [2026-07-17] Local Function Client startup can fail before workspace access

**Symptom:** Constructing `DatabricksFunctionClient()` failed locally before any
workspace call with a protobuf gencode/runtime version error.
**Root cause:** The locked `databricks-connect==17.0.10` package contains Spark
Connect protobuf code generated with 6.33.0, while the resolved shared protobuf
runtime is 5.29.6 through the current Databricks/MLflow dependency graph.
**Fix / workaround:** Generate the current UC Python function DDL from the same
callable and submit it through the SQL Statement Execution API on a Pro or
serverless SQL warehouse; keep Function Client execution for a compatible
Databricks/serverless environment.
**Watch out for:** A valid `create_python_function` callable contract does not
prove that local Spark Connect can initialize. Test client construction before
using it as a deployment path, and do not change the shared protobuf version
without resolving the full locked dependency graph.

## [2026-07-20] Retriever caller timeout left the SDK HTTP request running

**Symptom:** A timed-out retriever call returned control to the caller while the
Model Serving SDK request continued in a background thread.
**Root cause:** `serving_endpoints.query` in SDK 0.120.0 has no per-call timeout;
wrapping it in `Future.result(timeout=...)` only cancels queued work, not an
already-running HTTP request.
**Fix / workaround:** Construct the default `WorkspaceClient` with
`Config(http_timeout_seconds=timeout, retry_timeout_seconds=ceil(timeout))` and
invoke the query directly so the SDK transport terminates it. Injected clients
must provide their own transport timeout.
**Watch out for:** Do not reintroduce a thread-wrapper timeout around SDK calls
unless its worker can be actively cancelled; it creates leaked in-flight calls
under endpoint degradation.

## [2026-07-20] Bundle MLflow experiment creation does not create parent folders

**Symptom:** Deploying the App bundle failed with `Parent directory does not
exist: /Shared/ecommerce_agent` while creating its MLflow experiment.
**Root cause:** The MLflow experiment API used by Declarative Automation Bundles
creates the experiment but does not recursively create workspace directories.
**Fix / workaround:** Use the existing `/Shared` directory directly for the
project experiment (`/Shared/ecommerce-agent-app`), or create a parent directory
explicitly before using a nested experiment path.
**Watch out for:** Validate Bundle schema alone cannot catch workspace-path
existence; inspect the target workspace or keep deployment-owned experiment
paths directly under a known existing directory.

## [2026-07-20] Managed MCP UC tools use encoded LangChain names

**Symptom:** Live Managed MCP discovery succeeded, but the production allowlist
filtered every discovered tool and produced an empty tool set.
**Root cause:** The current managed UC-function server exposes tools as
`catalog__schema__function` and puts catalog/schema in metadata, rather than
using the full dot-qualified UC function name or a `function_name` attribute.
**Fix / workaround:** Build current routes with
`DatabricksMCPServer.from_uc_function` and accept encoded names plus metadata
when applying each server's allowlist; retain exact/full/short-name matching for
client compatibility.
**Watch out for:** Do not infer a failed allowlist from discovery success alone.
Run live discovery and at least one asynchronous `ainvoke`; these MCP tools are
`StructuredTool` instances that do not support synchronous `invoke`.

## [2026-07-20] Managed MCP tool calls failed inside the synchronous Agent graph

**Symptom:** The deployed App emitted a `function_call`, then its LangGraph tool
node failed with `StructuredTool does not support sync invocation.` and no
tool-result continuation reached the client.
**Root cause:** Managed UC MCP discovery returns async-only `StructuredTool`
instances, whereas the MLflow `ResponsesAgent` implementation consumes the
LangGraph graph through synchronous `stream`.
**Fix / workaround:** Adapt only async-only tools into a `StructuredTool` with
the original name, description, and args schema whose sync function resolves
the original `ainvoke` coroutine; preserve the explicit managed-MCP transport.
**Watch out for:** A deterministic pre-model workflow may work through
`ainvoke` while model-selected tool calls still fail in the graph. Exercise a
real `function_call -> function_call_output -> message` App smoke after any
MCP or LangGraph upgrade.

## [2026-07-20] Bundle resource deployment does not refresh an App source snapshot

**Symptom:** `databricks bundle deploy` completed after an App source change,
but the running App still showed stack-trace line numbers from the old source.
**Root cause:** The Bundle update reconciled the App resource and uploaded its
workspace files, but did not create a new Databricks Apps source deployment.
**Fix / workaround:** After uploading with `databricks bundle deploy -t dev`,
run `databricks apps deploy ecommerce-agent-app --source-code-path` against the
Bundle workspace path and wait for `SUCCEEDED`.
**Watch out for:** A `RUNNING` App only proves its current snapshot started.
Check the active deployment ID or execute a behavior-specific smoke before
claiming a source patch is live.

## [2026-07-20] Outer App timeout canceled the retriever cold-start retry budget

**Symptom:** The retriever allowed two 60-second endpoint attempts, while the
Chat UI and MCP façade canceled their Agent App request after 60 seconds.
**Root cause:** Retry policy and outer App-to-App HTTP timeout were configured in
different packages without a shared end-to-end latency budget.
**Fix / workaround:** Keep the retriever attempts bounded and set both App
callers to 180 seconds, leaving room for two attempts, backoff, and model/tool
overhead. Add a repository contract test for the relationship.
**Watch out for:** Adding a retry can make reliability worse when an upstream
caller times out before the retry can finish. Review nested timeout budgets from
the innermost transport outward.

## [2026-07-20] AI Gateway SDK success criteria require endpoint read-back

**Symptom:** Deployment code contained a valid SDK 0.120.0 QPM configuration,
but the live endpoint had no `ai_gateway` field and therefore no active limit.
**Root cause:** The current workspace rejects even a QPM-only request for this
custom endpoint type with `Rate limits is not currently supported for this
endpoint type in this workspace.` Official product documentation describing QPM
support does not override a workspace capability result.
**Fix / workaround:** Treat `put_ai_gateway` as active only after successful
endpoint read-back. Record the exact workspace error and enforce application
input, output, and graph-step limits when Gateway controls are unavailable.
**Watch out for:** A correct request shape or passing mock test proves only the
client contract. Never document QPM, inference tables, or usage tracking as
enabled until the live endpoint exposes the resulting configuration.

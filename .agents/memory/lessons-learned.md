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

## [2026-07-21] Databricks Apps runtime uses `pip install -r requirements.txt`, not pyproject.toml

**Symptom:** `ModuleNotFoundError: No module named 'psycopg_pool'` at app startup even though psycopg-pool was listed in pyproject.toml.
**Root cause:** The Databricks Apps build system runs `pip install -r requirements.txt` inside the app's source directory. It does not read pyproject.toml or uv.lock. The Chat UI's requirements.txt only contained a comment.
**Fix / workaround:** List every runtime dependency (psycopg, psycopg-pool, databricks-sdk) explicitly in requirements.txt with version bounds.
**Watch out for:** Requirements.txt is the SOLE dependency source for the App runtime. Adding a dependency to pyproject.toml does NOT deploy it. After changing requirements.txt, the build will detect the change and reinstall.

**Databricks evidence:** [Add a Lakebase resource to a Databricks App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase) — the build logs show `pip install -r requirements.txt`.

## [2026-07-21] Databricks Apps only downloads the source_code_path directory

**Symptom:** `ModuleNotFoundError: No module named 'ecommerce_agent'` even though the conversation package exists at `ecommerce_agent/conversation/`.
**Root cause:** The App's `source_code_path` was set to `ecommerce_agent/apps/chat_ui/`. The runtime ONLY downloads files under that path. The `ecommerce_agent/conversation/` directory (one level up) was excluded.
**Fix / workaround:** Copy the conversation package as a sibling directory inside `chat_ui/` during deployment, and update imports from `from ecommerce_agent.conversation...` to `from conversation...`. Change internal conversation module imports to relative imports (`.models`, `.repository`, etc.).
**Watch out for:** `source_code_path` determines what files the app runtime receives. Any module outside that path won't be available at import time. Either flatten the structure or set source_code_path to a common parent.

## [2026-07-21] Streamlit script thread has no asyncio event loop — use background thread

**Symptom:** `RuntimeError: no running event loop` when calling `asyncio.run()` from within a Streamlit app callback.
**Root cause:** Streamlit executes user scripts in a plain Python thread without an asyncio event loop. `asyncio.run()` cannot be called from a thread that already has or doesn't have a running loop correctly.
**Fix / workaround:** Create a dedicated background daemon thread with its own event loop (`asyncio.new_event_loop()` + `loop.run_forever()`), then submit async tasks via `asyncio.run_coroutine_threadsafe(coro, loop).result()`.
**Watch out for:** Any `asyncio.run()` call inside a Streamlit app's synchronous context will fail. Always route async calls through a persistent background event loop.

## [2026-07-21] Uploading pyproject.toml to the app source directory breaks deployments

**Symptom:** `AppDeploymentState.FAILED: Unexpected error. Please contact Databricks support` — deployments ending in <2 seconds with no pip output.
**Root cause:** The Databricks Apps build system detected `pyproject.toml` alongside `requirements.txt` in the app source directory and attempted to build the project as a Python package (editable install) instead of just running `pip install -r requirements.txt`.
**Fix / workaround:** Never upload `pyproject.toml` to the app's source directory. Only include `requirements.txt` and the actual Python source files needed by the app.
**Watch out for:** Deployments that fail instantly (1-2 seconds) indicate a build system issue, not a pip install failure. Check if `pyproject.toml` or other build configuration files are present in the source directory.

## [2026-07-21] Databricks Apps injects PG* env vars, not LAKEBASE_POSTGRES_*

**Symptom:** `Missing Lakebase connection parameters: host, dbname, user, password` even though the postgres resource was bound to the app.
**Root cause:** The Databricks Apps runtime injects standard PostgreSQL environment variables (`PGHOST`, `PGDATABASE`, `PGUSER`, `PGPORT`, `PGSSLMODE`) — not `LAKEBASE_POSTGRES_HOST` as the code expected.
**Fix / workaround:** Read `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPORT` from the environment. Keep `LAKEBASE_LOCAL_*` as a fallback for local development.
**Watch out for:** Different Databricks documentation pages use different naming conventions. The `apps init --features lakebase` scaffolding uses `LAKEBASE_*` prefixed vars, but the actual runtime injection uses `PG*` vars. Verify against a deployed app.

**Databricks evidence:** [Add a Lakebase resource to a Databricks App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase) — documents that `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPORT`, `PGSSLMODE` are injected.

## [2026-07-21] Databricks Apps does not inject a PGPASSWORD — must generate OAuth token

**Symptom:** Connection timeout after 120s — `couldn't get a connection` with no specific error.
**Root cause:** The Databricks Apps runtime injects `PGHOST`, `PGDATABASE`, `PGUSER`, `PGPORT`, but does NOT inject `PGPASSWORD` or any token. The app must programmatically call `WorkspaceClient().postgres.generate_database_credential(endpoint=...)` to obtain a short-lived OAuth token to use as the connection password.
**Fix / workaround:** In the connection pool, override `_resolve_kwargs` to call `generate_database_credential()` before each new connection and pass the returned `cred.token` as the `password` kwarg. Use `loop.run_in_executor()` to run the synchronous SDK call without blocking the async event loop.
**Watch out for:** Tokens expire after 1 hour. The pool's `max_lifetime` should be set to 1800s (30 min) so connections are recycled well before token expiry. Always use a subclass of `AsyncConnectionPool` that overrides `_resolve_kwargs` or `_resolve_conninfo`, never monkey-patch `_connect`.

**Databricks evidence:** [Connect a custom Databricks App to Lakebase](https://docs.databricks.com/aws/en/oltp/projects/tutorial-databricks-apps-autoscaling) — step-by-step tutorial showing token generation.

## [2026-07-21] App runtime may have an older databricks-sdk without postgres API

**Symptom:** `'WorkspaceClient' object has no attribute 'postgres'` at runtime, even though the local SDK has it.
**Root cause:** The Databricks Apps runtime includes a pre-installed `databricks-sdk` but at an older version that doesn't have the `postgres` sub-module (added in SDK 0.28+). The local pyproject.toml pins `databricks-sdk==0.120.0` but the App runtime doesn't read pyproject.toml.
**Fix / workaround:** Add `databricks-sdk>=0.120.0` to `requirements.txt` so pip upgrades the SDK to a version with the `postgres` API.
**Watch out for:** The App runtime's pre-installed packages can be older than what the project uses locally. Always pin required SDK features explicitly in requirements.txt. The SDK import succeeds (module found) but attributes may be missing.

## [2026-07-21] psycopg_pool._connect() override must set _created_at and _expire_at

**Symptom:** `'AsyncConnection' object has no attribute '_created_at'` or `'_expire_at'` when the pool tries to manage connection lifetimes.
**Root cause:** The base `AsyncConnectionPool._connect()` method sets `_created_at` and `_expire_at` on the connection after calling `_connect_gen()`. Monkey-patching or overriding `_connect()` directly bypasses this bookkeeping.
**Fix / workaround:** Override `_resolve_conninfo()` and `_resolve_kwargs()` instead of `_connect()`. These methods are called by the base `_connect()` which then handles all bookkeeping (`_pool`, `_created_at`, `_expire_at`, stats, configure hook) automatically.
**Watch out for:** If you must override `_connect()` (e.g., for a completely custom connection flow), replicate `conn._created_at = time.time()` and `conn._expire_at = now + max_lifetime`. Prefer overriding `_resolve_*` hooks — they're the designed extension points.

## [2026-07-21] PostgreSQL pg_try_advisory_lock requires bigint, not numeric

**Symptom:** `function pg_try_advisory_lock(numeric) does not exist` during schema migration.
**Root cause:** `uuid.uuid5(...).int` returns a 128-bit integer. PostgreSQL's `pg_try_advisory_lock()` accepts `bigint` (64-bit signed). The Python driver sends the 128-bit value as `numeric`, which has no matching function overload.
**Fix / workaround:** Mask the lock ID to 63 bits: `uuid.uuid5(...).int & ((1 << 63) - 1)`. Also add an explicit `::bigint` cast in the SQL query: `SELECT pg_try_advisory_lock(%s::bigint)`.
**Watch out for:** Any `pg_try_advisory_lock` / `pg_advisory_lock` call with a Python `int` value > 2^63-1 will fail with the same error. Always ensure the lock key fits in a signed 64-bit integer.

## [2026-07-21] App SP cannot access pre-existing schemas created by a different user

**Symptom:** `permission denied for schema conversations` when the app tries to create tables, even though the schema exists.
**Root cause:** The App's Service Principal has `CAN_CONNECT_AND_CREATE` on the database, but the `conversations` schema was previously created by the developer's username (`trietlm0306@gmail.com`). The SP can create new objects but cannot access existing schemas owned by other users. A schema created by someone else is invisible to the SP at the DDL level.
**Fix / workaround:** Drop the schema using the original creator's credentials: `DROP SCHEMA IF EXISTS conversations CASCADE`. Then let the App SP create it on next startup (`CREATE SCHEMA IF NOT EXISTS conversations`) — the SP becomes the owner and can create tables inside it.
**Watch out for:** Never create the app's schema manually before the first deployment. Always deploy the app first so the SP creates and owns the schema. If you ran migration scripts locally first and hit this error, drop the user-owned schema and let the SP recreate it (data loss — back up first).

**Databricks evidence:** [Add a Lakebase resource to a Databricks App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/lakebase) — "The app's Service Principal has CAN_CONNECT_AND_CREATE — it can create new objects but cannot access existing schemas. The SP must create the schema to become its owner."

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

## [2026-07-21] MLflow ResponsesAgent input rejects `role: "tool"` and missing `type`/`content` fields

**Symptom:** HTTP 400 on second+ turn when replaying conversation history that includes tool calls. First turn (no history) works. Error from MLflow ResponsesAgent: "Invalid role: tool. Must be 'user', 'assistant', 'system', or 'developer'" and "Field required" for `type` and `content`.

**Root cause:** The MLflow `ResponsesAgentRequest` uses a stricter input schema than the OpenAI Responses API:
- Every input item must have a `type` field (`"message"`, `"function_call"`, or `"function_call_output"`).
- The `role` field only accepts `"user"`, `"assistant"`, `"system"`, or `"developer"` — `"tool"` is invalid.
- For `function_call` items, `content` must be present (can be empty string `""`).
- For `function_call_output` items, use `output` field (not `content`) and `role: "assistant"`.

The initial "no history" request works because it only contains user messages.

**Fix / workaround:** In `replay.py`, convert function calls with `{"type": "function_call", "role": "assistant", "content": "", "tool_calls": [...]}` and function results with `{"type": "function_call_output", "role": "assistant", "tool_call_id": "...", "output": "..."}`. Never use `role: "tool"`.

**Watch out for:** Every request that includes tool-call history will 400 if the MLflow-specific `type` field is missing. Testing a single-turn request (no history) does not catch this. The OpenAI-standard format (`role: "tool"`, no `type` field) is NOT compatible with MLflow ResponsesAgent.

## [2026-07-21] Agent emits duplicate `response.output_item.done` messages for tool output

**Symptom:** The replayed history contained two consecutive `assistant` messages for a single turn — one carrying raw JSON tool output and one carrying natural-language answer. The ResponsesAgent does not allow consecutive same-role messages.

**Root cause:** The MLflow ResponsesAgent produces two `response.output_item.done` events with `type: "message"` after a function call — the first echoes the raw tool result as an assistant message, the second gives the natural-language response. Both get persisted by `complete_turn()`.

**Fix / workaround:** In `_convert_message_item()` in `replay.py`, skip assistant messages whose text starts with `{` or `[` (likely JSON echoes). This prevents the duplicate assistant message from being included in the replayed history.

**Watch out for:** The number of persisted items per turn may exceed the expected count (user + function_call + function_call_output + assistant could become 5+ items). Verify replay correctness by checking the actual items stored in Lakebase.

## [2026-07-21] Streamlit UI fails to rerender after long-running streaming callback

**Symptom:** After a streaming agent response completes and messages are appended to `st.session_state.messages`, the new messages do not appear until a manual page refresh. Data is correctly persisted to Lakebase but not displayed.

**Root cause:** Streamlit does not automatically rerun the script after a long-running callback (the streaming HTTP request blocks the script). Although `st.session_state` updates are preserved, the UI is not re-rendered until the next user interaction triggers a rerun.

**Fix / workaround:** Call `st.rerun()` after all messages are appended to session state. However, be careful not to restructure the code in ways that break the linear execution flow — keep the handler inline (not a separate function) so Streamlit's execution context is preserved.

**Watch out for:** Do NOT move the streaming logic into a separate function callback — Streamlit's `st.chat_input` handler must remain in the main script body for correct state management. Adding `st.rerun()` inside a deeply nested callback can cause infinite recursion.

## [2026-07-22] psycopg_pool requires persistent asyncio event loop — temporary loops cause "Event loop is closed"

**Symptom:** After a successful pool open + migration at startup, subsequent async pool operations fail with "Event loop is closed" or "couldn't get a connection after N sec".

**Root cause:** `asyncio.new_event_loop()` + `loop.run_until_complete()` + `loop.close()` creates a temporary event loop. The `AsyncConnectionPool` internally associates connections and scheduling with the loop on which it was opened. When a subsequent operation runs on a *different* event loop (or a closed one), the pool's internal tasks fail because they reference the original loop.

Specifically, the Chat UI's session state init opened the pool on loop A, then closed it. Later, `_run_async()` created loop B for DB operations. The pool tried to use loop B, but its internal connections were associated with loop A → "Event loop is closed".

**Fix / workaround:** Use a SINGLE persistent background event loop that lives for the entire app session:
1. Create a daemon thread running `loop.run_forever()`.
2. Store the loop in `st.session_state` so it persists across Streamlit reruns.
3. Submit all async operations via `asyncio.run_coroutine_threadsafe(coro, loop).result()`.
4. Create the loop BEFORE initializing any pool/async resources that depend on it.

**Watch out for:** Streamlit reruns the entire script on each interaction, but session state persists. Initialize the background loop only once (`if "bg_loop" not in st.session_state`) and ensure it's created before any code that depends on it. The pool must also be opened on the same persistent loop, not a temporary one.

## [2026-07-22] Streamlit session state initialization order matters for cross-referencing objects

**Symptom:** `st.session_state has no attribute "bg_loop"` even though the `if "bg_loop" not in st.session_state` check exists in the same file.

**Root cause:** Streamlit executes the script top-to-bottom on every rerun. The session state initialization block that created `bg_loop` was positioned AFTER the block that tried to read it (inside the conversation service init). Since the script hadn't reached the `bg_loop` creation code yet, the attribute didn't exist.

**Fix / workaround:** Always declare session state initializers in dependency order. Any object created in one `if "key" not in st.session_state` block that is consumed by another block must appear first in the source file. Move prerequisite initializers before dependents.

**Watch out for:** This is easy to miss when modules grow large and initializer blocks are separated by comments or functions. Group related session state keys together, or extract initialization into a dedicated function with explicit ordering.

## [2026-07-22] MLflow ResponsesAgent stream rejects replayed `function_call_output` items with `'call_id'` error

**Symptom:** On the second turn of a conversation, the Agent App returns HTTP 200 but the stream immediately contains `{"error": "'call_id'"}` followed by `[DONE]`. No output items or text deltas are produced. The first turn works fine.

**Root cause:** The MLflow ResponsesAgent maintains internal state for pending function calls. When a `function_call_output` item is replayed from a previous turn's history, the agent cannot find a corresponding pending `function_call` (it was already completed in the previous turn), and raises an internal `'call_id'` key error. This error is serialized as an SSE event, not an HTTP error, making it invisible to standard error handling.

**Fix / workaround:** Filter out `function_call` and `function_call_output` items during history replay. Only replay `user` and `assistant` messages. The assistant message already contains the tool output in natural language form, so the agent has enough context from messages alone.

**Watch out for:** The tool-call pattern from previous turns is lost from the replayed context. If the agent needs to reference which tools were called or what arguments were passed, that information must be conveyed in the assistant's natural-language response text.

## [2026-07-22] Streamlit app logs require explicit logger configuration to appear in Databricks Apps logs

**Symptom:** `logger.info()` calls produce no output in `databricks apps logs`, even though the code executes correctly. Only BUILD-level logs appear.

**Root cause:** `logger = logging.getLogger(__name__)` creates a logger with default level WARNING and no handler. Messages at INFO or lower are silently dropped. The Databricks Apps runtime captures stdout/stderr but does not configure Python logging handlers.

**Fix / workaround:** After creating the logger:
```python
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.INFO)
    _h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(_h)
```

**Watch out for:** Every new Python module that uses `logger.info()` in a Databricks App must repeat this configuration. Simply calling `logging.getLogger(__name__)` is insufficient.

## [2026-07-23] Bundle deployment leaves a Databricks App on its previous runtime snapshot

**Symptom:** `databricks bundle deploy` validated and uploaded a new Node source tree, but the live App continued to start with `streamlit run app.py`.
**Root cause:** Bundle deployment synchronizes source and resource configuration; it does not create a new App deployment snapshot. `databricks apps start` also starts the existing active snapshot.
**Fix / workaround:** After `databricks bundle deploy`, run `databricks bundle run <app-resource-key> -t <target>`. Verify `active_deployment.source_code_path` and the startup command in App logs.
**Watch out for:** A Bundle "Deployment complete" message is not evidence that an App is running the newly synchronized source.

## [2026-07-23] Databricks Node Apps require explicit OAuth and Lakebase credential handling

**Symptom:** The React server started but could neither authenticate to the Agent App nor connect to Lakebase.
**Root cause:** The runtime injects `DATABRICKS_CLIENT_ID`/`DATABRICKS_CLIENT_SECRET`, not a ready `DATABRICKS_TOKEN`; it may inject `DATABRICKS_HOST` without an URL scheme. Lakebase supplies `PG*` connection fields but no password.
**Fix / workaround:** Normalize the workspace host to HTTPS, obtain and cache an OAuth M2M token from `/oidc/v1/token`, generate a short-lived database credential from `/api/2.0/postgres/credentials`, and use an async `pg` password callback with bounded connection lifetime.
**Watch out for:** A successful static React response proves neither App-to-App OAuth nor Lakebase connectivity. Run authenticated `/api/health` and CRUD smokes.

## [2026-07-23] Conversation schema code at v2 does not mean the live Lakebase schema migrated

**Symptom:** Completed Node turns rolled back with `there is no unique or exclusion constraint matching the ON CONFLICT specification`.
**Root cause:** The repository contained migration v2, but live `_schema_version` was still 1 and lacked `items_turn_key_unique`; 91 legacy items still had null keys.
**Fix / workaround:** Inspect `_schema_version` and live constraints before cutover. Run the exact v2 migration transactionally under an advisory lock using the Chat UI App service principal that owns the schema, then verify the version and constraints.
**Watch out for:** Unit migration tests and checked-in DDL are not deployment evidence. A replacement runtime must still execute forward migrations.

## [2026-07-23] Production agent stream omitted the documented terminal completion event

**Symptom:** Live streams returned text delta, output item, then `[DONE]`; every otherwise successful turn was marked failed and history was not persisted.
**Root cause:** `CoreAgent.predict_stream()` never emitted `response.completed`. Handler tests used fake agents that emitted it themselves, so the production omission was not covered.
**Fix / workaround:** Emit a valid `ResponsesAgentStreamEvent(type="response.completed", response={id, status, output})` only after successful stream flushing and operation-gate verification, and add a test against the real `CoreAgent.predict_stream()` path.
**Watch out for:** Mock adapter tests can validate serialization while missing terminal events in the production generator. Verify live event type order.

## [2026-07-23] Databricks SDK deployment waiter requires a timedelta timeout

**Symptom:** A Chat UI snapshot upload succeeded and the deployment was created, but waiting for it raised `AttributeError: 'int' object has no attribute 'total_seconds'`.
**Root cause:** This SDK version accepts a `datetime.timedelta` timeout for the deployment waiter, not a raw integer, even though the surrounding deployment request is valid.
**Fix / workaround:** Pass `timedelta(minutes=12)` to `.result(timeout=...)`, or poll `apps.get_deployment` after submission. Verify the new deployment becomes `SUCCEEDED` and active before reporting it.
**Watch out for:** The local waiter exception can occur after the remote deployment has already started; inspect `list_deployments` before submitting another snapshot.

## [2026-07-23] A RUNNING Node Databricks App can still return 404 at the root

**Symptom:** The Chat UI deployment reported `RUNNING`, and Node started successfully, but `/` returned 404.
**Root cause:** Static client serving was conditional on `NODE_ENV=production`; Databricks Apps did not infer that value from the production start command.
**Fix / workaround:** Use an app-specific `APP_RUNTIME=production` signal for static serving, build the client into the expected `dist` path, and verify the authenticated root URL rather than relying on control-plane status.
**Watch out for:** Setting `NODE_ENV=production` in `app.yaml` also affects the Databricks build phase, causing npm to omit TypeScript/Vite development dependencies and fail with `tsc: not found`.

## [2026-07-23] Psycopg async integration tests on Windows need the selector event loop

**Symptom:** Real PostgreSQL integration tests timed out while opening the async connection pool and emitted Proactor transport warnings.
**Root cause:** Psycopg's async transport is incompatible with the default Windows Proactor event loop in this test path.
**Fix / workaround:** Apply `asyncio.WindowsSelectorEventLoopPolicy()` only in the credential-gated PostgreSQL integration test process.
**Watch out for:** Do not change the application's global event-loop policy merely to accommodate a Windows test runner.

## [2026-07-23] A cloned Lakebase branch preserves database ownership

**Symptom:** The integration principal could connect to a temporary cloned branch but could not drop or recreate the application-owned schema.
**Root cause:** Branch cloning preserved the schema owner from production; the developer principal was not the owner.
**Fix / workaround:** Create an empty, short-lived database in the TTL branch owned by the test principal, run migrations and destructive isolation checks there, then delete the branch.
**Watch out for:** Never change production-like schema ownership or grants just to make an integration test pass.

## [2026-07-23] An npm start wrapper can swallow Databricks Apps SIGTERM

**Symptom:** The Express server implemented bounded shutdown and `process.exit`, but every redeploy still logged `App did not respect SIGTERM timeout of 15 seconds`.
**Root cause:** `app.yaml` launched `npm run start`; the Databricks signal reached the npm parent process rather than the Node child that owned the shutdown handlers.
**Fix / workaround:** Start the compiled server directly with `node server/dist/index.js` so Node is the app process and receives SIGTERM.
**Watch out for:** A correct application-level shutdown handler cannot help when a process wrapper does not forward the platform signal.

## [2026-07-23] A new conversation opened in a permanent streaming state

**Symptom:** A freshly created React conversation showed only the Stop button; Enter left the message in the composer and could not start a turn.
**Root cause:** `createInitialStreamState()` correctly defaults to an active stream for reducer processing, but `useChat` also used that default for its idle initial and conversation-reset states.
**Fix / workaround:** Let `createInitialStreamState(isStreaming)` accept an explicit lifecycle value and initialize/reset `useChat` with `false`; keep active send/reducer paths at the default `true`.
**Watch out for:** Reducer initial state and UI idle state are different lifecycle states. Browser-test the composer before assuming a component test with a manually supplied `isStreaming={false}` covers hook integration.

## [2026-07-23] The Chat UI proxy must own the downstream DONE sentinel

**Symptom:** A blindly proxied upstream sentinel could let the browser terminate before the server had made its terminal persistence decision.
**Root cause:** The proxy forwarded upstream chunks, including `[DONE]`, before parsing all events and persisting the completed turn.
**Fix / workaround:** Make the Chat UI proxy consume and suppress upstream sentinels, keep reading terminal metadata, persist the turn, then emit exactly one downstream `[DONE]`. The browser safely finishes on that proxy-owned sentinel and surfaces an incomplete-stream error if it arrives without completion.
**Watch out for:** Do not blindly forward an upstream `[DONE]`; termination ordering is part of the proxy contract.

## [2026-07-23] A terminal text response retained the active composing label

**Symptom:** A completed live response had already switched from Stop to Send and was persisted, but still displayed “🤖 Composing…”.
**Root cause:** The `response.completed` reducer recomputed the phase label with `hasTextDelta=true`; the display policy correctly interpreted that as an active composing phase even though `isStreaming=false`.
**Fix / workaround:** Terminal completion must derive its phase with no active text delta. Preserve “✅ Tool complete” only when completed tool results exist; otherwise clear the phase label.
**Watch out for:** Test terminal visual state independently from lifecycle booleans; a correct `isStreaming=false` can still expose a misleading active phase label.

## [2026-07-23] Create-turn failures had no assistant message to render the error

**Symptom:** An oversized live request correctly produced a failed stream state and Retry button, but the conversation showed only the user message and no explanation.
**Root cause:** `useChat` appended the assistant placeholder only after `createTurn()` succeeded. Its catch path updated stream state, while `ChatPage` attaches that state only to the last assistant message.
**Fix / workaround:** On a pre-stream failure, append an assistant error message; if an assistant placeholder already exists, update it instead. Retry removes that error assistant and reuses the existing user message.
**Watch out for:** Exercise failures before and after assistant-placeholder creation; a global error flag is not visible unless the component tree has a node that renders it.

## [2026-07-24] LangGraph messages mode streamed tool-result JSON as assistant text

**Symptom:** A governed tool card rendered correctly, but the final assistant
answer began with the raw JSON tool result; after reload, the JSON could appear
as a separate assistant bubble and enter replay history.
**Root cause:** LangGraph `stream_mode="messages"` emits `ToolMessageChunk`
objects as well as `AIMessageChunk` objects. The Agent converted every chunk
with content into `response.output_text.delta`, and the resulting aggregated
message was persisted.
**Fix / workaround:** Emit visible deltas only for `AIMessageChunk`. Keep tool
results in `function_call_output` items, and filter legacy JSON-only assistant
echoes from replay and React history hydration when the same turn has tool
provenance.
**Watch out for:** A correct tool card does not prove the assistant text is
clean. Verify live output, persisted items, reload hydration, and the next-turn
replay after every LangGraph/MLflow streaming change.

## [2026-07-24] Scale-to-zero retriever cold starts can consume the Apps request budget

**Symptom:** The React UI showed tool progress, then failed with `Stream read
error`; Chat UI aborted near 110 seconds and Agent logs later reported
`search-and-rerank-endpoint timed out after 60s`.
**Root cause:** Databricks Apps enforces a 120-second request limit, the workspace
requires custom serving endpoints to enable scale-to-zero, and the former
two-attempt 60-second retriever policy could not fit alongside model/tool-loop
latency.
**Fix / workaround:** Use a single 45-second retrieval attempt and start a
bounded Agent App daemon worker that performs a harmless top-1 lookup at startup
and every 15 minutes. The worker stops within the App shutdown budget and
contains warm-up failures without crashing readiness.
**Watch out for:** Keeping the endpoint warm can increase serving cost. If the
interval changes, prove a policy-search turn still finishes below the proxy
limit after an idle period and document the ongoing compute tradeoff.

## [2026-07-24] Current Agent runtime lifecycle and signal APIs differ from older examples

**Symptom:** A deployed Agent crashed because `FastAPI.add_event_handler` did
not exist, and an earlier redeploy logged `App did not respect SIGTERM timeout
of 15 seconds`.
**Root cause:** The locked FastAPI runtime exposes startup/shutdown handler lists
on `app.router`, while the App command used `sh -c uv run ...` without replacing
the shell process.
**Fix / workaround:** Register lifecycle callbacks with
`app.router.on_startup/on_shutdown.append(...)` and launch with
`sh -c "exec uv run ..."` so Uvicorn receives SIGTERM. A live redeploy then
logged shutdown start, completion, and process exit in the same second.
**Watch out for:** Static FastAPI examples and a successful startup do not prove
the deployed version's lifecycle API or signal delivery. Verify both by
redeploying the exact command twice and inspecting runtime logs.

## [2026-07-24] A RUNNING Streamlit snapshot can still be an invalid rollback

**Symptom:** Databricks reported successful Streamlit deployments, but one
failed on first browser execution with `ModuleNotFoundError: apps`; another
streamed a new response yet could not list the existing React conversation.
**Root cause:** The newer artifact flattened files that still used
package-qualified imports. The older self-contained artifact used the
pre-hardening owner identity, so its Lakebase view did not match current
trusted-owner records.
**Fix / workaround:** Exercise rollback through the authenticated browser, not
only deployment status. Disqualify both Streamlit artifacts and certify the
previous immutable React snapshot against pre- and post-cutover history before
restoring the current React snapshot.
**Watch out for:** Process startup, a successful new turn, and schema migration
are separate from identity-compatible history. A rollback is valid only when
the same user can read existing conversations and newly persisted data.

---
name: databricks-workspace-operator
description: Safely connect to and operate a Databricks workspace with the current Python SDK, including PAT/OAuth authentication, Unity Catalog checks, serverless notebook or job execution, Model Serving endpoint lifecycle, logs, secrets, MLflow models, and ChatDatabricks smoke tests. Use this skill whenever a user asks to connect to Databricks, run something on serverless, upload or execute a notebook, inspect or deploy an endpoint, debug a Databricks timeout or serving error, or verify a workspace result—even if they only say “run it on Databricks.”
compatibility: Repository uses PowerShell, uv, databricks-sdk 0.120.0, databricks-langchain 0.20.0, LangChain 1.x, and MLflow 3.x.
---

# Databricks Workspace Operator

Use evidence from the live workspace to connect, diagnose, mutate, and verify
Databricks resources without exposing credentials or silently changing the
user's namespace.

## Before taking action

1. Read the repository instructions, relevant plan, and
   `.agents/memory/lessons-learned.md`.
2. Inspect the locked dependency versions before writing API calls. Do not copy
   legacy examples for older LangChain, MLflow, or Databricks SDK versions.
3. Browse current official Databricks documentation when an API, feature status,
   serverless behavior, or serving contract might have changed. For provider
   quirks, use that provider's official documentation as well.
4. Classify the requested operation:
   - Read-only discovery and diagnostics are safe to perform.
   - Uploading the user's file, running their notebook, and updating a resource
     explicitly placed in scope are normal implementation actions.
   - Creating paid compute, replacing traffic, deleting resources, changing
     permissions, or touching an unrelated endpoint requires explicit authority.
5. Identify invariants before running anything. In this repository, preserve
   catalog `workspace` unless the user explicitly changes it. Never silently
   substitute `main`, a personal catalog, or a new schema.

## Credential safety

- Prefer `DATABRICKS_HOST` and `DATABRICKS_TOKEN` from `.env` or an existing
  authenticated profile. Never print `.env`, a token, an Authorization header,
  a secret value, or a complete SDK config object.
- Check only whether required variable names exist. If a token must be classified
  for debugging, output only a coarse kind and length—not any substring.
- Load credentials into the current process only. Do not write a
  `.databrickscfg` or copy credentials into notebooks unless the user explicitly
  requests persistent configuration.
- Confirm `.env` is ignored before any Git operation.
- A Model Serving secret reference such as
  `{{secrets/SCOPE/KEY}}` is safe to display; the resolved value is not.

Read [references/runtime-playbook.md](references/runtime-playbook.md) before
working with serverless Jobs, Model Serving, ResponsesAgent, or DeepSeek.

## Connection workflow

### 1. Discover configuration without leaking it

Check for the two required names:

```text
DATABRICKS_HOST
DATABRICKS_TOKEN
```

If the host is missing, explain that it is the workspace root URL, not a notebook
URL. VS Code extension installation alone does not guarantee that the CLI has an
auth profile. The extension may bundle a CLI, but prefer the repository's pinned
Python SDK for programmatic work.

### 2. Run a minimal authenticated preflight

Create `WorkspaceClient()` from the process environment and verify:

1. `current_user.me()` succeeds.
2. The required catalog exists and its returned name exactly matches the
   requested catalog.
3. Only the permissions/resources needed by the task are queried.

Print identity and resource names only when useful. Never print the client or its
configuration representation.

### 3. Inspect live state before mutation

For every resource that may already exist, call `get` first and record:

- canonical name and namespace;
- active version or config version;
- readiness and update state;
- pending configuration;
- only environment-variable keys, never resolved values.

This prevents accidental replacement and distinguishes “the request timed out”
from “the server never accepted the request.”

## Running notebooks on serverless compute

1. Upload a Databricks source notebook to a user-owned workspace path with
   `workspace.upload(..., format=SOURCE, language=PYTHON, overwrite=True)`.
2. Use a saved Lakeflow Job with a notebook task and no cluster definition when
   serverless Jobs is enabled. A saved job gives better run history than an
   opaque local execution.
3. Pass catalog/schema/deploy switches as notebook task parameters rather than
   editing the uploaded source.
4. Poll `jobs.get_run()` in short intervals. Send the user an update at least once
   per minute during a long run.
5. On failure, obtain output from the task run ID, not just the parent run ID.
   Capture the exception class, message, and the smallest useful traceback.
6. For machine-verifiable evidence, end a smoke notebook with
   `dbutils.notebook.exit(json.dumps(result))`; otherwise Jobs API may report
   success but return no notebook output.
7. Treat a serverless run as proven only when lifecycle/result states are
   terminal/successful and task output satisfies the task's assertions.

## Model Serving lifecycle

- `create()` and `update_config()` return long-running-operation waiters.
  Submission is not readiness.
- Custom image creation can exceed five minutes. Use a task-appropriate timeout
  (30 minutes for this repository's custom model lab) and a status callback.
- Before `update_config()`, wait until the current endpoint state is
  `NOT_UPDATING`; otherwise Databricks returns `ResourceConflict`.
- If a create call times out, call `get(name)` before retrying. The control plane
  may have created the endpoint successfully.
- Query only after checking `READY`, `NOT_UPDATING`, active entity/version, and
  required secret environment-variable keys.
- Preserve existing endpoint traffic and unrelated served entities unless the
  user explicitly authorized replacement.
- Remind the user that scale-to-zero custom Model Serving still incurs compute
  cost while active and can have cold-start latency.

## Layered serving diagnosis

Test the narrowest layer that can falsify the current hypothesis:

1. Provider client directly, if provider credentials and scope allow it.
2. Endpoint without tools: confirm auth, secret injection, image health, and
   basic streaming.
3. Endpoint with one runtime function schema: confirm request signature and tool
   call serialization.
4. Tool-result continuation: confirm the assistant/tool history contract.
5. Two user turns: confirm state survives a realistic agent loop.

Do not jump directly to a large agent trace when a simple endpoint stream already
fails. Conversely, do not claim tool-use compatibility from a tool-free response.

## ChatDatabricks and provider adapters

- Application code should depend on `ChatDatabricks` when Databricks Model
  Serving is the selected model boundary. Provider-specific packages, API keys,
  and message repair belong inside the custom served model.
- Use the current Responses API contract (`use_responses_api=True`) for an MLflow
  `ResponsesAgent`; do not introduce legacy `ChatModel` or `ChatAgent` fallbacks.
- Tools are executed by the caller/agent. The model endpoint produces function
  calls; it does not execute the local Python function.
- For DeepSeek V4 thinking mode, omit `tool_choice`, preserve tool-call reasoning
  across the tool result, and assert that a required business tool was actually
  selected. Prompt-only enforcement is not sufficient for high-stakes actions;
  add deterministic routing or post-validation in application code.
- Verify the deployed model signature accepts full runtime function tools before
  attributing an HTTP 400 to LangChain or the provider.

## Evidence and handoff

Report the outcome before implementation details. Include:

```text
Authentication: success/failure without credentials
Catalog: exact verified name
Compute/run: serverless or other explicit target, run ID, terminal state
Resource: endpoint/model/config version and readiness
Test: layer exercised and concrete counts/assertions
Result: what is proven, what remains unproven
Costs/cleanup: active resources that may continue billing
```

Do not say “works” based only on a successful import, endpoint creation request,
or HTTP 200. Match evidence to the requested behavior: streaming requires
multiple deltas, tool use requires a function call, and reasoning round-trip
requires a successful continuation after a tool result.

## Common traps

- Printing `.env` while trying to discover the host.
- Assuming a VS Code extension created `.databrickscfg`.
- Treating a five-minute waiter timeout as proof that creation failed.
- Querying immediately after a bare `create()` or `update_config()`.
- Updating an endpoint while another config is pending.
- Assuming an endpoint created in the UI contains notebook-defined secret vars.
- Testing only the first tool call and missing the failing continuation.
- Using Playground `Auto`/`Required` when a provider rejects `tool_choice`.
- Letting a certification or compatibility experiment leak into the production
  serving architecture.


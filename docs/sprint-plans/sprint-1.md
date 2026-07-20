# Sprint 1 Plan

## Sprint Goal

Deliver one modern, non-legacy vertical slice that validates configuration,
builds the LangChain 1.x agent, loads versioned rules and skills, exposes it via
Databricks Apps, and executes real, tested Unity Catalog and local tools while
creating isolated hands-on certification labs for adjacent platform concepts.

## Definition of Done

- The repository has no runtime import or command containing
  `projects.ecommerce_support`.
- `ecommerce_agent/config.yaml` validates and all file paths resolve independent
  of the current working directory.
- The agent uses `ChatDatabricks`, LangChain `create_agent`, MLflow
  `ResponsesAgent`, and MLflow `AgentServer` on Databricks Apps.
- When DeepSeek is configured, the App reaches it only through
  `ChatDatabricks(use_responses_api=True)` and a dedicated custom Model Serving
  endpoint; the provider secret and provider-specific reasoning protocol never
  enter the App or `agent_core`.
- No configured tool raises `NotImplementedError`, returns placeholder data, or
  references a Unity Catalog function/table that is not provisioned by the
  project.
- Governed order, seller, shipping, and policy operations are implemented as
  real UC SQL/Python functions and exposed through the explicitly selected
  managed MCP or `UCFunctionToolkit` transport.
- Managed MCP and the top-level `UCFunctionToolkit` are both supported as
  explicit UC-function transports; each agent build selects exactly one and
  never falls back silently to the other.
- Rules and skills are loaded from version-controlled application source.
- The root `uv` lock is the runtime dependency source of truth; the SDK is pinned
  to 0.120.0 and LangChain stays on 1.x.
- Unit tests, syntax checks, Ruff checks, bundle validation, and credentialed
  Databricks smoke tests pass at the appropriate test layer.

## Non-Legacy Guardrails

Do not introduce or preserve these in the production path:

- `databricks.agents.deploy` or a Model Serving deployment fallback.
- Direct `ChatDeepSeek`, `init_chat_model(provider="deepseek")`, provider API
  keys, or imports from `experiments/` in the App or `agent_core` production
  import graph.
- Hand-written FastAPI emulation of the Responses API.
- LangChain `AgentExecutor`, `create_tool_calling_agent`, or LangGraph
  `create_react_agent`.
- `databricks_langchain.uc_ai` imports or a manually constructed internal
  `DatabricksFunctionClient` execution mode.
- `projects.ecommerce_support` imports, paths, commands, or documentation.
- DBFS paths for rules, skills, configuration, or application support files.
- Unbounded per-App `requirements.txt` files that can resolve differently from
  `uv.lock`.

The supported stabilization path is:

- `databricks_langchain.ChatDatabricks` for the model.
- A dedicated custom Model Serving adapter is allowed solely as the external
  model/provider boundary. It must not contain agent business orchestration or
  become a legacy Model Serving deployment of the agent itself.
- `langchain.agents.create_agent` for orchestration.
- Databricks managed MCP or the top-level
  `databricks_langchain.UCFunctionToolkit` for governed UC functions, selected
  explicitly per deployment with least-privilege grants and no automatic
  fallback.
- Local LangChain tools for deterministic calculations that need no external
  resource.
- The existing serving endpoint adapter only for the custom search-and-rerank
  contract that cannot be replaced by a plain AI Search call without a quality
  comparison.
- MLflow `ResponsesAgent` hosted by MLflow `AgentServer` on Databricks Apps.
- Project Model Serving capacity is exactly two endpoints:
  `search-and-rerank-endpoint` and `deepseek-v4-streaming-agent-lab`. Bundle,
  benchmark, and deployment code must reconcile these in place; temporary,
  blue-green, environment-specific, and Agent-serving endpoints are prohibited.

## Atomic Tasks

Status legend: [ ] pending / [~] in progress / [x] done

Before implementing a task, use the
[Sprint 1 Databricks implementation documentation index](../SPRINT_1_DATABRICKS_DOCS_INDEX.md)
to verify the current official platform guidance, release stage, locked API
surface, and task-specific non-legacy constraints.

### Workspace execution authorization

The repository owner grants implementation agents standing authorization to
access the configured Databricks workspace and perform all project-scoped
create, update, deploy, grant, query, compute, test, and cleanup operations
needed by this Sprint Plan. Agents must not pause for per-operation approval or
treat a missing project resource as a manual-UI blocker; use the pinned SDK,
current CLI/Bundle commands, or APIs to provision and verify it.

This authorization is bounded by `.agents/rules/databricks.md`: production
resources use catalog `ecommerce_agent`, credentials and resolved secrets are
never displayed or persisted, existing resources are inspected before mutation,
unrelated resources are preserved, credentialed tests remain gated, and compute
started for validation is stopped or returned to scale-to-zero when safe. Ask
the user only for a missing secret value, unavailable admin entitlement,
business-policy decision, or destructive/out-of-scope action.

### A. Lock the runtime contract

- [x] **A1:** Pin `databricks-sdk==0.120.0` and declare the supported LangChain
  1.x and MLflow 3.x ranges in the root `pyproject.toml`.
- [x] **A2:** Make the root `pyproject.toml` plus `uv.lock` the dependency source
  for the agent App and remove unbounded duplicate runtime manifests.
- [x] **A3:** Add a compatibility test that imports every public `agent_core` API
  and the `ecommerce_agent` entrypoint on the locked environment.
- [x] **A4:** Add a repository check that fails on the banned legacy symbols and
  paths listed above.

### B. Repair configuration and imports

- [x] **B1:** Change `LLMConfig` to the `ChatDatabricks` contract used by the
  YAML (`endpoint_name`, temperature, and token limit) and remove unused provider
  and compute-mode fields.
- [x] **B2:** Add one config loader that validates YAML and records the config
  file's directory as the base for relative resources.
- [x] **B3:** Add config tests for valid input, missing required keys, invalid tool
  unions, and working-directory-independent path resolution.
- [x] **B4:** Replace Python imports from `projects.ecommerce_support` with the
  installed `ecommerce_agent` package path.
- [x] **B5:** Replace App commands and developer instructions that still launch a
  `projects.ecommerce_support` module.
- [x] **B6:** Export the intended stable construction APIs from `agent_core` and
  make `ecommerce_agent` consume only those public exports.

### C. Modernize agent and tool construction

- [x] **C1:** Replace generic `init_chat_model` construction with
  `ChatDatabricks(endpoint=..., use_responses_api=True)` while retaining
  LangChain `create_agent` and keeping endpoint selection environment-driven.
- [x] **C2:** Remove `databricks_langchain.uc_ai` imports and unsupported
  execution-mode plumbing from the production adapter.
- [x] **C3:** Extend the tool config union with a local-function kind so pure
  calculations do not need Unity Catalog registration.
- [x] **C4:** Add unit tests that build mixed local, UC function, and serving
  endpoint tool sets without workspace network calls.
- [x] **C5:** Make the custom tool registry instance-scoped or immutable so tests
  and multiple agent builds cannot leak process-global factories.
- [x] **C6:** Add a typed managed-MCP server config for allowlisted Unity Catalog
  functions without embedding workspace hostnames or credentials.
- [x] **C7:** Implement async lifecycle management for
  `DatabricksMultiServerMCPClient` and expose its discovered tools to
  `create_agent`.
- [x] **C8:** Add contract tests for MCP tool discovery, function allowlisting,
  authentication failure, session cleanup, and duplicate tool names.
- [x] **C9:** Support both managed MCP and the top-level `UCFunctionToolkit` as
  explicitly selected UC-function transports, inject the current UC client into
  the toolkit path, and never automatically fallback between transports.
- [x] **C10:** Define a tool-selection policy that distinguishes optional
  read-only tools from required or state-changing business operations when the
  selected model cannot accept protocol-level `tool_choice`.
- [x] **C11:** Implement a deterministic operation gate that routes required or
  state-changing intents to an explicit workflow instead of relying on the model
  to choose a tool.
- [x] **C12:** Validate required-tool arguments against their declared schemas
  before execution.
- [x] **C13:** Block a required-operation success response until the workflow has
  observed the expected typed tool result.
- [x] **C14:** Add tests proving a required operation cannot report success when
  the model omits its mandatory tool call or supplies invalid arguments.

### D. Make rules and skills reproducible

- [x] **D1:** Change rule paths in `config.yaml` to package-relative
  `rules/*.md` paths resolved by the central config loader.
- [x] **D2:** Replace `SkillsConfig.volume_path` with a source directory contract
  for `ecommerce_agent/skills`.
- [x] **D3:** Update `SkillLibrary` to use `pathlib`, deterministic ordering, and
  validated frontmatter names without assuming `/Volumes`.
- [x] **D4:** Add tests for rule ordering, empty libraries, duplicate skill names,
  malformed frontmatter, unknown skill names, and path traversal attempts.
- [x] **D5:** Remove the default skill-sync step from `driver.py` and document UC
  Volume as an opt-in provider requiring an App volume resource with read-only
  access.
- [x] **E1-E14:** See below for individual status.
- [x] **F1-F3:** See below for individual status.
- [x] **G1-G3:** See below for individual status; request-concurrency and
  streaming regression coverage is complete.

### E. Remove mock tools and align data contracts

- [x] **E1:** Define one environment-aware Unity Catalog namespace contract and
  eliminate the current `ecommerce_agent.gold_layer` versus
  `ecommerce_demo.gold`/`ecommerce_demo.agent` mismatch.
- [x] **E2:** Update the Olist transformation to build the seller aggregates
  required by seller-performance and shipping-delay tools.
- [x] **E3:** Complete the two unfinished SQL table functions against the agreed
  gold schema and remove commented placeholder DDL.
- [x] **E4:** Provision `EXECUTE`, `USE CATALOG`, and `USE SCHEMA` grants for the
  App service principal through the deployment workflow.
- [x] **E5:** Add SQL contract tests for function names, parameters, return
  columns, qualification, and empty-result behavior.
- [x] **E6:** Extract an auditable refund-policy matrix from the canonical policy
  documents; record policy identifiers, conditions, and effective dates rather
  than inventing thresholds in code.
- [x] **E7:** Redesign `check_refund_eligibility` inputs to include an explicit
  claim/reference date and every policy discriminator needed by the matrix.
- [x] **E8:** Implement `check_refund_eligibility` as a governed UC Python
  function from the policy matrix and make
  unsupported or ambiguous claims return a typed explanation instead of a false
  boolean certainty.
- [x] **E9:** Add boundary tests for every refund window, claim type, missing
  condition, future date, and non-delivered order state.
- [x] **E10:** Define and document the delay-severity thresholds from the shipping
  policy, then implement `compute_delay_severity` as a deterministic local tool.
- [x] **E11:** Add tests for early, on-time, undelivered, and every delay boundary
  handled by `compute_delay_severity`.
- [x] **E12:** Define a documented, bounded customer-value formula and implement
  `customer_value_score` as a deterministic local tool without using it to deny
  service eligibility.
- [x] **E13:** Add tests for negative inputs, zero history, score bounds, and
  monotonicity of `customer_value_score`.
- [x] **E14:** Remove every tool from `config.yaml` until its implementation and
  backing resource are complete; add it back only with a passing contract test.

### F. Verify the retriever and serving contract

- [x] **F1:** Define typed request and response models for the custom
  search-and-rerank endpoint, including malformed and empty prediction handling.
- [x] **F2:** Verify the `WorkspaceClient.serving_endpoints.query` call shape
  against SDK 0.120.0 and cover it with a fake-client contract test.
- [x] **F3:** Add timeout/error mapping and source-safe output formatting to
  `search_policy_docs` without hiding endpoint failures as empty search results.

### G. Replace the hand-written App server

- [x] **G1:** Adapt `CoreAgent` request and streaming output to the MLflow 3.14
  `ResponsesAgent` contract, preserving tool-call and tool-result events.
- [x] **G2:** Replace the custom FastAPI `/responses` route with MLflow
  `AgentServer` invoke/stream registration.
- [x] **G3:** Add local contract tests for non-streaming responses, SSE streaming,
  custom inputs, trace metadata, and propagated errors.
- [x] **G4:** Create a Declarative Automation Bundle for the agent App with its
  command, environment variables, source path, and development/production
  targets; reconcile the two existing Model Serving endpoints without creating
  environment-specific endpoints.
- [x] **G5:** Declare least-privilege App resources for the LLM endpoint, custom
  reranker endpoint, MLflow experiment, each enabled UC function, and the
  resources behind each managed MCP server; the App receives `CAN_QUERY` on the
  configured LLM endpoint but no provider-secret access.
- [x] **G6:** Update the standalone chat UI and custom MCP server to use the
  documented app-to-app OAuth path and apply `CAN_USE` to the target App service
  principal client ID.

### H. Verification and handoff

- [x] **H1:** Run `uv run python -m compileall agent_core ecommerce_agent
  data-processing`.
- [x] **H2:** Run the full unit suite with `uv run pytest -v` and keep
  credentialed tests isolated behind a marker.
- [x] **H3:** Run `uvx ruff check .` and `uvx ruff format --check .`.
- [x] **H4:** Run `databricks bundle validate` for development and production
  targets without provisioning additional Model Serving endpoints.
- [x] **H5:** Run credentialed smoke tests that discover the allowlisted UC
  functions through managed MCP, execute one function, query the reranker
  endpoint, load rules and skills, and complete streamed multi-turn tool calls
  through the deployed App and configured `ChatDatabricks` endpoint, reusing
  the two existing project endpoints.
- [x] **H6:** Update README setup, architecture, deployment, and verification
  instructions only after the tested commands are final.

### I. Build certification learning artifacts

- [x] **I1:** Create a coverage matrix mapping every objective in the exam guide
  effective from 2026-03-18 to product code, a hands-on lab, or study notes.
- [x] **I2:** Create a current-API lab that defines, registers, grants, describes,
  and directly executes one UC SQL function and one UC Python function.
- [x] **I3:** Create a compatibility lab that wraps the same functions with the
  documented top-level `UCFunctionToolkit` and compares its tool schema with the
  managed MCP schema.
- [x] **I4:** Create a managed-MCP lab that discovers and calls allowlisted UC
  functions, then documents authentication and permission failure modes.
- [x] **I5:** Create a current exam lab for MLflow pyfunc, model signature,
  Unity Catalog model registration, and Model Serving without importing it from
  the Databricks Apps production path.
- [x] **I6:** Create a retrieval lab covering chunking, Delta tables, AI Search,
  metadata filtering, reranking, and retrieval evaluation on the policy corpus.
- [x] **I7:** Create an evaluation/governance lab covering Prompt Registry aliases,
  MLflow tracing and scorers, SME rubrics, inference tables, rate limits, and AI
  Gateway cost controls; distinguish controls supported by custom model endpoints
  from those limited to other endpoint types.
- [x] **I8:** Add a concise current-versus-superseded API matrix; superseded APIs
  may be explained but must not be executable dependencies of production code.

### J. Verify the DeepSeek/ChatDatabricks serving experiment

- [x] **J1:** Authenticate from the local workspace, verify serverless execution,
  and confirm the experiment uses the fixed Unity Catalog catalog `workspace`
  without exposing credentials.
- [x] **J2:** Reproduce and classify the five-minute SDK endpoint-creation timeout
  using control-plane status and debug evidence.
- [x] **J3:** Reproduce the final-cell failure against a ready endpoint and capture
  both client traceback and served-model logs.
- [x] **J4:** Fix the endpoint lifecycle and Responses/DeepSeek reasoning adapter,
  then extend local contract tests for the discovered causes.
- [x] **J5:** Deploy the corrected model version, run the two-turn
  `ChatDatabricks` tool-call stream on serverless compute, and record whether
  streaming and `reasoning_content` round-trip succeed.

### K. Productionize the verified DeepSeek model boundary

- [x] **K1:** Define a typed Responses API contract for the DeepSeek provider
  adapter, including tool schemas, streaming events, reasoning items, provider
  errors, and unsupported request fields.
- [x] **K2:** Extract the verified adapter into a deployable package outside
  `experiments/` without importing it from the App or `agent_core`.
- [x] **K3:** Add adapter contract tests for tool-schema normalization,
  `reasoning_content` replay, streaming reconstruction, provider error mapping,
  and explicit rejection of `tool_choice` in DeepSeek V4 thinking mode.
- [x] **K4:** Add a parameterized model logging and Unity Catalog registration
  workflow for the extracted adapter.
- [x] **K5:** Add an endpoint reconciliation workflow that updates the singleton
  `deepseek-v4-streaming-agent-lab` in place, resolving its model version from
  deployment configuration rather than application source.
- [x] **K6:** Configure the endpoint's `DEEPSEEK_API_KEY` through a secret-scope
  reference and grant secret `READ` only to the identity that creates or updates
  the served model configuration.
- [x] **K7:** Implement singleton endpoint reconciliation with a deployment timeout of at
  least 30 minutes, `NOT_UPDATING` verification, served-entity config checks, and
  actionable status/log diagnostics instead of relying on the five-minute SDK
  waiter default.
- [x] **K8:** Benchmark scale-to-zero cold start, warm streaming latency, and the
  combined Databricks Serving plus DeepSeek provider cost before selecting the
  endpoint as a production default, reusing the singleton endpoint without a
  temporary benchmark endpoint.
- [x] **K9:** Add a credentialed end-to-end test that reaches the adapter only
  through `ChatDatabricks`, completes a multi-turn tool loop, and verifies that
  streaming text, tool calls, tool results, and reasoning round-trip survive the
  App boundary.
- [x] **K10:** Record the verified AI Gateway capability matrix for this custom
  endpoint, including inference tables, QPM, unavailable TPM limiting, and the
  absence of output guardrails for streaming responses.
- [x] **K11:** Configure the inference table and QPM controls supported by the
  custom endpoint through the deployment workflow.
- [x] **K12:** Define the application streaming-safety behavior and provider-cost
  limit used where AI Gateway cannot supply output guardrails or TPM enforcement.

## Implementation Handoff — Re-audit 2026-07-17

Assign one workstream at a time. An implementation agent must read the linked
official-document index before coding, change only files named by its assigned
tasks, and must not edit `data-processing` notebooks unless its assignment is
workstream 1 or 5.

| Priority | Workstream | Sprint tasks | Status | Exit criteria |
|---:|---|---|---|---|
| 1 | Public core contract and canonical UC namespace | B6, E1, E3, E5 | [x] | `ecommerce_agent` consumes only public `agent_core` exports; every production identifier defaults to catalog `ecommerce_agent`; schema names are decided once, config-driven, and covered by qualification tests. |
| 2 | Deterministic required-operation gate | C10-C14 | [x] | A required tool is satisfied only after validated arguments and its correlated typed result; non-streaming and streaming success cannot escape early. |
| 3 | Managed MCP contracts | C6-C8 | [x] | Per-server allowlists, duplicate names, auth failures, discovery, and session behavior have network-free contract tests using the locked API. |
| 4 | Retriever serving contract | F1-F3 | [x] | Typed request/response models, an injectable fake SDK client, supported timeout behavior, error mapping, malformed predictions, and source-safe formatting are tested through production code. |
| 5 | Governed UC business functions | E2-E5, E14, H5 | [x] | Order, customer, seller, and shipping functions exist under the canonical namespace, have grants, and pass credentialed transport and App smokes. |
| 6 | Refund policy implementation | E6-E9 | [x] | Approved synthetic policy `SYNTH-REFUND-2026-01` drives the governed Python function and complete local/live decision-state tests; it is explicitly not an Olist policy. |
| 7 | App contracts and deployment | G3-G6 | [x] | AgentServer invoke/SSE tests pass; a dev/prod Declarative Automation Bundle declares commands, resources, permissions, and app-to-app OAuth. |
| 8 | Workspace verification and handoff | H4-H6 | [x] | Both bundle targets validate; credentialed end-to-end smoke tests pass; README and architecture match the tested commands. |
| 9 | Certification labs | I2-I4, I6-I8 | [x] | UC function, toolkit-versus-MCP, retrieval, evaluation/governance, and current-versus-superseded labs are runnable and isolated from production imports; the managed-MCP lab uses the current per-function route. |
| 10 | DeepSeek production boundary | K1-K12 | [x] | The canonical adapter is packaged and served by the singleton endpoint; credentialed `ChatDatabricks`, OAuth App, MCP tool-loop, latency, capability, and safety-envelope checks pass. |

Implementation order is 1 → 2 → 3 → 4 → 5 → 7 → 8. Workstream 6 is complete.
Workstreams 9 and 10 may provision their project-scoped workspace resources
under the standing authorization, but must not change contracts owned by
workstreams 1–5.

## Notes / Blockers

- Managed MCP is explicitly covered by the exam guide effective from 2026-03-18
  and was Public Preview in the documentation reviewed on 2026-07-15.
  Production deployment must check workspace enablement. Both managed MCP and
  `UCFunctionToolkit` remain explicit supported transports; failure in one must
  never activate the other automatically.
- The current exam guide does not name `UCFunctionToolkit` as a standalone
  objective. UC Functions remain valuable hands-on coverage for governed tools,
  while certification preparation must also cover MCP, Apps, MLflow, Model
  Serving, Vector Search, evaluation, monitoring, governance, and AI Gateway.
- The custom search-and-rerank endpoint includes behavior beyond a plain managed
  AI Search MCP call. Do not replace it until retrieval quality and latency are
  compared on the existing evaluation dataset.
- The workspace quota permits exactly two project Model Serving endpoints:
  `search-and-rerank-endpoint` and `deepseek-v4-streaming-agent-lab`. Reconcile
  them in place and do not create temporary, per-environment, blue-green, or
  Agent-serving endpoints.
- Refund tasks E6-E9 are complete using the explicitly approved synthetic policy
  `SYNTH-REFUND-2026-01`; it is not an Olist policy and semantic changes require
  a new version and tests.
- Databricks integration tests require workspace authentication and real
  resources; agents are authorized to provision and exercise project-scoped
  resources programmatically. Local import success is not an integration test.
- DeepSeek serving verification completed on 2026-07-15 using catalog `workspace`,
  registered model version 4, and endpoint config 5. Serverless run
  `843390409034780` succeeded with 33/28 stream chunks/text deltas on turn 1 and
  140/135 on turn 2; both turns contained one tool call and one reasoning
  round-trip.
- The successful lab promotes the DeepSeek adapter to the configured model
  boundary for this Free Edition learning deployment. It is not a paid-production
  cost baseline: exact Databricks Serving billing data is unavailable here, and
  direct provider access from the App is never an automatic fallback.
- DeepSeek V4 thinking mode accepted tool use only when `tool_choice` was omitted
  in the verified route. Prompt wording may encourage a tool call but is not an
  enforcement mechanism for required or state-changing operations; C10-C14 own
  that product-level safety requirement.
- The current Agent App, Chat UI, and MCP façade run with OAuth-safe App
  invocation. The façade was recreated after the owner authorized recovery;
  its service principal has `CAN_USE` on the Agent App. A credentialed MCP
  handshake, `tools/list`, and `ask_ecommerce_support` call completed through
  the façade on 2026-07-20. A workspace PAT remains intentionally rejected at
  Apps ingress; the authenticated `Ecommerce-Agent` profile supplies the OAuth
  token used by credentialed smoke tests.
- The credentialed singleton DeepSeek contract passed on 2026-07-20 through
  `ChatDatabricks`: two streamed tool turns, visible output deltas, and replayed
  reasoning items. The OAuth Agent App now also completed a managed-MCP
  `function_call -> function_call_output -> message` loop on 2026-07-20. MLflow's
  public App serializer intentionally does not expose provider reasoning; K9 is
  therefore verified at two observable layers rather than by leaking hidden
  reasoning through the App response.
- AI Gateway QPM-only reconciliation was retried with SDK 0.120.0 on 2026-07-20
  and returned `Rate limits is not currently supported for this endpoint type in
  this workspace.` The endpoint read-back has no `ai_gateway` config. K10-K11 are
  complete as a workspace-specific capability result, not a claim that QPM or
  inference tables are active.
- Where Gateway controls are unavailable, K12 is enforced in application code:
  caller input is capped at 100,000 characters, LangGraph execution at 12 steps,
  and model output at 1,500 tokens per call. Chat UI and MCP App-to-App calls use
  a 180-second timeout so the bounded two-attempt retriever cold-start policy can
  finish rather than being canceled by the outer caller.

## Sprint Closeout

Sprint 1 completed on 2026-07-20. All atomic tasks are `[x]`; unsupported
workspace capabilities are recorded as verified capability outcomes instead of
being represented as active controls. Final evidence is maintained in
`artifacts/task_sprint1_closeout_summary.md`.

Final App deployment IDs are `01f184166f6f1014831fc63e83f1888c` (Agent),
`01f184169b8b1af18bc776464e411b8c` (Chat UI), and
`01f184169f401ab8b7ffc9b817b4375b` (MCP façade).

## Official References Reviewed

- [Databricks Certified Generative AI Engineer Associate exam guide effective 2026-03-18](https://www.databricks.com/sites/default/files/2026-02/Databricks-Certified-Generative-AI-Engineer-Associate-Exam-Guide-Interrim-Feb26.pdf)
- [Author an AI agent and deploy it on Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent)
- [Connect agents to tools](https://docs.databricks.com/aws/en/agents/agent-framework/agent-tool)
- [Use MCP servers in agents](https://docs.databricks.com/aws/en/agents/mcp/use-mcp-in-agents)
- [Databricks managed MCP servers](https://docs.databricks.com/aws/en/agents/mcp/managed-mcp)
- [Unity Catalog tools with LangChain](https://docs.databricks.com/aws/en/agents/agent-framework/unity-catalog-tool-integration)
- [Add resources to a Databricks App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/resources)
- [Add a Unity Catalog volume resource to an App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/uc-volumes)
- [Work with files in Unity Catalog volumes](https://docs.databricks.com/aws/en/volumes/volume-files)
- [Databricks LangChain Python API](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html)
- [LangChain agents](https://docs.langchain.com/oss/python/langchain/agents)
- [LangChain ChatDatabricks integration](https://docs.langchain.com/oss/python/integrations/chat/databricks)
- [MLflow AgentServer API](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.genai.html)
- [Databricks SDK for Python workspace client](https://databricks-sdk-py.readthedocs.io/en/latest/clients/workspace.html)
- [Create and manage custom Model Serving endpoints](https://docs.databricks.com/aws/en/machine-learning/model-serving/create-manage-serving-endpoints)
- [Configure secret environment variables for Model Serving](https://docs.databricks.com/aws/en/machine-learning/model-serving/store-env-variable-model-serving)
- [Configure AI Gateway on serving endpoints](https://docs.databricks.com/aws/en/ai-gateway/configure-ai-gateway-endpoints)

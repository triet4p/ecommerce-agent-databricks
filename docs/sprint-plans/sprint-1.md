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
- No configured tool raises `NotImplementedError`, returns placeholder data, or
  references a Unity Catalog function/table that is not provisioned by the
  project.
- Governed order, seller, shipping, and policy operations are implemented as
  real UC SQL/Python functions and exposed to the production agent through the
  managed Unity Catalog functions MCP server when enabled.
- Direct `UCFunctionToolkit`, MLflow pyfunc, and Model Serving exercises are
  isolated from the production import graph and clearly labeled by current,
  compatibility, or historical status.
- Rules and skills are loaded from version-controlled application source.
- The root `uv` lock is the runtime dependency source of truth; the SDK is pinned
  to 0.120.0 and LangChain stays on 1.x.
- Unit tests, syntax checks, Ruff checks, bundle validation, and credentialed
  Databricks smoke tests pass at the appropriate test layer.

## Non-Legacy Guardrails

Do not introduce or preserve these in the production path:

- `databricks.agents.deploy` or a Model Serving deployment fallback.
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
- `langchain.agents.create_agent` for orchestration.
- Databricks managed MCP for production discovery and execution of governed UC
  functions, with explicit function allowlists and least-privilege grants.
- Top-level `databricks_langchain.UCFunctionToolkit` only in certification labs
  and an explicitly selected compatibility deployment target.
- Local LangChain tools for deterministic calculations that need no external
  resource.
- The existing serving endpoint adapter only for the custom search-and-rerank
  contract that cannot be replaced by a plain AI Search call without a quality
  comparison.
- MLflow `ResponsesAgent` hosted by MLflow `AgentServer` on Databricks Apps.

## Atomic Tasks

Status legend: [ ] pending / [~] in progress / [x] done

### A. Lock the runtime contract

- [ ] **A1:** Pin `databricks-sdk==0.120.0` and declare the supported LangChain
  1.x and MLflow 3.x ranges in the root `pyproject.toml`.
- [ ] **A2:** Make the root `pyproject.toml` plus `uv.lock` the dependency source
  for the agent App and remove unbounded duplicate runtime manifests.
- [ ] **A3:** Add a compatibility test that imports every public `agent_core` API
  and the `ecommerce_agent` entrypoint on the locked environment.
- [ ] **A4:** Add a repository check that fails on the banned legacy symbols and
  paths listed above.

### B. Repair configuration and imports

- [ ] **B1:** Change `LLMConfig` to the `ChatDatabricks` contract used by the
  YAML (`endpoint_name`, temperature, and token limit) and remove unused provider
  and compute-mode fields.
- [ ] **B2:** Add one config loader that validates YAML and records the config
  file's directory as the base for relative resources.
- [ ] **B3:** Add config tests for valid input, missing required keys, invalid tool
  unions, and working-directory-independent path resolution.
- [ ] **B4:** Replace Python imports from `projects.ecommerce_support` with the
  installed `ecommerce_agent` package path.
- [ ] **B5:** Replace App commands and developer instructions that still launch a
  `projects.ecommerce_support` module.
- [ ] **B6:** Export the intended stable construction APIs from `agent_core` and
  make `ecommerce_agent` consume only those public exports.

### C. Modernize agent and tool construction

- [ ] **C1:** Replace generic `init_chat_model` construction with
  `ChatDatabricks(endpoint=...)` while retaining LangChain `create_agent`.
- [ ] **C2:** Remove `databricks_langchain.uc_ai` imports and unsupported
  execution-mode plumbing from the production adapter.
- [ ] **C3:** Extend the tool config union with a local-function kind so pure
  calculations do not need Unity Catalog registration.
- [ ] **C4:** Add unit tests that build mixed local, UC function, and serving
  endpoint tool sets without workspace network calls.
- [ ] **C5:** Make the custom tool registry instance-scoped or immutable so tests
  and multiple agent builds cannot leak process-global factories.
- [ ] **C6:** Add a typed managed-MCP server config for allowlisted Unity Catalog
  functions without embedding workspace hostnames or credentials.
- [ ] **C7:** Implement async lifecycle management for
  `DatabricksMultiServerMCPClient` and expose its discovered tools to
  `create_agent`.
- [ ] **C8:** Add contract tests for MCP tool discovery, function allowlisting,
  authentication failure, session cleanup, and duplicate tool names.
- [ ] **C9:** Implement an explicitly selected top-level `UCFunctionToolkit`
  compatibility adapter without automatic fallback from MCP failures.

### D. Make rules and skills reproducible

- [ ] **D1:** Change rule paths in `config.yaml` to package-relative
  `rules/*.md` paths resolved by the central config loader.
- [ ] **D2:** Replace `SkillsConfig.volume_path` with a source directory contract
  for `ecommerce_agent/skills`.
- [ ] **D3:** Update `SkillLibrary` to use `pathlib`, deterministic ordering, and
  validated frontmatter names without assuming `/Volumes`.
- [ ] **D4:** Add tests for rule ordering, empty libraries, duplicate skill names,
  malformed frontmatter, unknown skill names, and path traversal attempts.
- [ ] **D5:** Remove the default skill-sync step from `driver.py` and document UC
  Volume as an opt-in provider requiring an App volume resource with read-only
  access.

### E. Remove mock tools and align data contracts

- [ ] **E1:** Define one environment-aware Unity Catalog namespace contract and
  eliminate the current `ecommerce_agent.gold_layer` versus
  `ecommerce_demo.gold`/`ecommerce_demo.agent` mismatch.
- [ ] **E2:** Update the Olist transformation to build the seller aggregates
  required by seller-performance and shipping-delay tools.
- [ ] **E3:** Complete the two unfinished SQL table functions against the agreed
  gold schema and remove commented placeholder DDL.
- [ ] **E4:** Provision `EXECUTE`, `USE CATALOG`, and `USE SCHEMA` grants for the
  App service principal through the deployment workflow.
- [ ] **E5:** Add SQL contract tests for function names, parameters, return
  columns, qualification, and empty-result behavior.
- [ ] **E6:** Extract an auditable refund-policy matrix from the canonical policy
  documents; record policy identifiers, conditions, and effective dates rather
  than inventing thresholds in code.
- [ ] **E7:** Redesign `check_refund_eligibility` inputs to include an explicit
  claim/reference date and every policy discriminator needed by the matrix.
- [ ] **E8:** Implement `check_refund_eligibility` as a governed UC Python
  function from the policy matrix and make
  unsupported or ambiguous claims return a typed explanation instead of a false
  boolean certainty.
- [ ] **E9:** Add boundary tests for every refund window, claim type, missing
  condition, future date, and non-delivered order state.
- [ ] **E10:** Define and document the delay-severity thresholds from the shipping
  policy, then implement `compute_delay_severity` as a deterministic local tool.
- [ ] **E11:** Add tests for early, on-time, undelivered, and every delay boundary
  handled by `compute_delay_severity`.
- [ ] **E12:** Define a documented, bounded customer-value formula and implement
  `customer_value_score` as a deterministic local tool without using it to deny
  service eligibility.
- [ ] **E13:** Add tests for negative inputs, zero history, score bounds, and
  monotonicity of `customer_value_score`.
- [ ] **E14:** Remove every tool from `config.yaml` until its implementation and
  backing resource are complete; add it back only with a passing contract test.

### F. Verify the retriever and serving contract

- [ ] **F1:** Define typed request and response models for the custom
  search-and-rerank endpoint, including malformed and empty prediction handling.
- [ ] **F2:** Verify the `WorkspaceClient.serving_endpoints.query` call shape
  against SDK 0.120.0 and cover it with a fake-client contract test.
- [ ] **F3:** Add timeout/error mapping and source-safe output formatting to
  `search_policy_docs` without hiding endpoint failures as empty search results.

### G. Replace the hand-written App server

- [ ] **G1:** Adapt `CoreAgent` request and streaming output to the MLflow 3.14
  `ResponsesAgent` contract, preserving tool-call and tool-result events.
- [ ] **G2:** Replace the custom FastAPI `/responses` route with MLflow
  `AgentServer` invoke/stream registration.
- [ ] **G3:** Add local contract tests for non-streaming responses, SSE streaming,
  custom inputs, trace metadata, and propagated errors.
- [ ] **G4:** Create a Declarative Automation Bundle for the agent App with its
  command, environment variables, source path, and development/production
  targets.
- [ ] **G5:** Declare least-privilege App resources for the LLM endpoint, custom
  reranker endpoint, MLflow experiment, each enabled UC function, and the
  resources behind each managed MCP server.
- [ ] **G6:** Update the standalone chat UI and custom MCP server to use the
  documented app-to-app OAuth path and apply `CAN_USE` to the target App service
  principal client ID.

### H. Verification and handoff

- [ ] **H1:** Run `uv run python -m compileall agent_core ecommerce_agent
  data-processing`.
- [ ] **H2:** Run the full unit suite with `uv run pytest -v` and keep
  credentialed tests isolated behind a marker.
- [ ] **H3:** Run `uvx ruff check .` and `uvx ruff format --check .`.
- [ ] **H4:** Run `databricks bundle validate` for development and production
  targets.
- [ ] **H5:** Run credentialed smoke tests that discover the allowlisted UC
  functions through managed MCP, execute one function, query the reranker
  endpoint, load rules and skills, and complete one `/responses` request through
  the deployed App.
- [ ] **H6:** Update README setup, architecture, deployment, and verification
  instructions only after the tested commands are final.

### I. Build certification learning artifacts

- [x] **I1:** Create a coverage matrix mapping every objective in the exam guide
  effective from 2026-03-18 to product code, a hands-on lab, or study notes.
- [ ] **I2:** Create a current-API lab that defines, registers, grants, describes,
  and directly executes one UC SQL function and one UC Python function.
- [ ] **I3:** Create a compatibility lab that wraps the same functions with the
  documented top-level `UCFunctionToolkit` and compares its tool schema with the
  managed MCP schema.
- [ ] **I4:** Create a managed-MCP lab that discovers and calls allowlisted UC
  functions, then documents authentication and permission failure modes.
- [x] **I5:** Create a current exam lab for MLflow pyfunc, model signature,
  Unity Catalog model registration, and Model Serving without importing it from
  the Databricks Apps production path.
- [ ] **I6:** Create a retrieval lab covering chunking, Delta tables, AI Search,
  metadata filtering, reranking, and retrieval evaluation on the policy corpus.
- [ ] **I7:** Create an evaluation/governance lab covering Prompt Registry aliases,
  MLflow tracing and scorers, SME rubrics, inference tables, rate limits, and AI
  Gateway cost controls.
- [ ] **I8:** Add a concise current-versus-superseded API matrix; superseded APIs
  may be explained but must not be executable dependencies of production code.

## Notes / Blockers

- Managed MCP is the current Databricks recommendation and is explicitly covered
  by the exam guide effective from 2026-03-18, but it is Public Preview as of the
  documentation reviewed on 2026-07-15. Production deployment must check that
  the workspace feature is enabled. A workspace without it must select the
  compatibility target deliberately; MCP failure must never trigger a silent
  transport fallback.
- The current exam guide does not name `UCFunctionToolkit` as a standalone
  objective. UC Functions remain valuable hands-on coverage for governed tools,
  while certification preparation must also cover MCP, Apps, MLflow, Model
  Serving, Vector Search, evaluation, monitoring, governance, and AI Gateway.
- The custom search-and-rerank endpoint includes behavior beyond a plain managed
  AI Search MCP call. Do not replace it until retrieval quality and latency are
  compared on the existing evaluation dataset.
- Refund logic is blocked until canonical policy documents are available to the
  implementation environment. Evaluation notes are evidence, not a sufficient
  source of truth for every policy condition.
- Databricks integration tests require workspace authentication and provisioned
  resources; local import success is not an integration test.

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

# Architecture Decision Records (ADR)

A chronological log of *why* key choices were made in this project.

**Purpose:** Prevents re-litigating settled decisions. Before refactoring, replacing a library, or changing an architectural pattern, the agent must check this file first. If a decision already has a recorded rationale, do not reverse it without explicit user instruction.

**Format for each entry:**

```
## [YYYY-MM-DD] <Short title of the decision>

**Decision:** What was decided.
**Alternatives considered:** What else was on the table.
**Reason:** Why this option was chosen over the alternatives.
**Consequences:** What this decision constrains or enables going forward.
```

---

<!-- Add new entries below, newest at the bottom -->

## [2026-07-15] Use the current Databricks Apps and LangChain 1.x agent stack

**Decision:** Build the production agent with Databricks Apps, MLflow `AgentServer` and `ResponsesAgent`, LangChain `create_agent`, `ChatDatabricks`, and the documented top-level `UCFunctionToolkit`; do not keep Model Serving agent deployment or pre-LangChain-1 agent APIs as fallbacks.
**Alternatives considered:** Keep the hand-written FastAPI Responses route, retain `databricks.agents.deploy` as a fallback, use `AgentExecutor`/`create_react_agent`, or immediately migrate all Databricks tools to managed MCP.
**Reason:** Current Databricks documentation recommends Apps plus MLflow's server contract for new custom agents, while current LangChain documentation identifies `create_agent` as its production agent API. Managed MCP is promising but remains Public Preview, so the stabilization sprint uses the current supported Unity Catalog toolkit surface without importing its former internal module.
**Consequences:** Production code cannot rely on legacy hosting or agent constructors; managed MCP adoption requires a later explicit preview decision and compatibility work.

## [2026-07-15] Keep rules and skills source-controlled by default

**Decision:** Store and load the e-commerce agent's rules and skills from the deployed `ecommerce_agent` source tree; treat Unity Catalog Volume storage as an optional provider for a future independent content-publishing lifecycle.
**Alternatives considered:** Load both rules and skills only from a UC Volume, keep rules in source and skills only in a Volume, or duplicate canonical copies in Git and a Volume.
**Reason:** The current library has only two rules and two skills, and these files change agent behavior. Keeping their canonical runtime copies with code gives atomic review, testing, deployment, and rollback while removing the current unsound relative-path sync step. Databricks Apps can add a read-only Volume resource later when content must change independently of application releases.
**Consequences:** Skill changes currently require an App deployment; a future Volume provider must define publishing, version pinning, cache invalidation, permissions, and rollback before it can become a production source.

## [2026-07-15] Use UC Functions in production and teach both MCP and toolkit transports

**Decision:** Implement governed order, seller, shipping, and policy capabilities as real Unity Catalog SQL/Python functions; expose them to the production agent through managed MCP when enabled, and isolate direct top-level `UCFunctionToolkit` usage to an explicit compatibility target and certification labs.
**Alternatives considered:** Remove UC Functions in favor of local tools, use `UCFunctionToolkit` as the only production transport, keep both transports behind an automatic fallback, or use UC Functions only in throwaway study notebooks.
**Reason:** The product benefits from Unity Catalog discovery, permissions, reuse, and auditable business logic, while the certification goal benefits from hands-on UC function creation and execution. The exam guide effective from 2026-03-18 explicitly covers managed/external/custom MCP, Apps, MLflow/Agent Framework, Model Serving, Vector Search, governance, evaluation, and AI Gateway, so production should teach the current MCP path without losing the supported toolkit concepts. Automatic fallback would hide permission and transport failures and create two unobservable production behaviors.
**Consequences:** Managed MCP capability and permissions become deployment prerequisites for the default target; non-MCP workspaces must choose a separate compatibility target explicitly. Certification artifacts may demonstrate current alternative transports and explain superseded APIs, but they cannot be imported by or silently alter the production runtime. This entry supersedes only the UC-function transport portion of the earlier Databricks Apps stack decision; Apps, `AgentServer`, `ResponsesAgent`, `create_agent`, and `ChatDatabricks` remain unchanged.

## [2026-07-16] Use ChatDatabricks behind a dedicated DeepSeek model boundary

**Decision:** Keep the agent on Databricks Apps and access DeepSeek only through `ChatDatabricks(use_responses_api=True)` targeting a dedicated custom Model Serving endpoint whose adapter owns the DeepSeek client, secret, streaming conversion, and reasoning round-trip.
**Alternatives considered:** Call DeepSeek directly from the App with `ChatDeepSeek` or `init_chat_model`, host the whole agent on Model Serving, use only a Databricks-hosted foundation model, or keep the verified DeepSeek route as a certification-only experiment.
**Reason:** The project cannot assume budget for a Databricks-hosted model, while the serverless lab verified multi-turn tool calls, streaming, and `reasoning_content` preservation through the exact `ChatDatabricks` boundary intended by the App. The endpoint keeps provider-specific behavior and the API key outside reusable agent code while retaining centralized Databricks permissions, logging, and the AI Gateway controls that custom endpoints actually support.
**Consequences:** The adapter must be productionized outside `experiments/` and cannot leak `ChatDeepSeek` or provider credentials into the App or `agent_core`. Endpoint selection remains environment-configurable and must pass a cold-start, latency, and combined-cost gate. DeepSeek V4's lack of `tool_choice` in thinking mode requires deterministic application enforcement for mandatory tools. AI Gateway assumptions must be endpoint-type-specific. This refines, but does not reverse, the ban on hosting the production agent through the legacy Model Serving agent path.

## [2026-07-16] Use `ecommerce_agent` as the canonical Unity Catalog catalog

**Decision:** Use `ecommerce_agent` as the canonical Unity Catalog catalog for this project; do not use `ecommerce_demo` as a production or default catalog name.
**Alternatives considered:** Keep `ecommerce_demo`, allow each notebook to choose an unrelated default catalog, or parameterize the catalog while retaining a different hard-coded fallback.
**Reason:** The project's existing Unity Catalog resources and Volume paths belong to `ecommerce_agent`; mixing in `ecommerce_demo` creates function, table, index, prompt, and deployment references that point at a different namespace.
**Consequences:** Defaults, examples, tests, prompt registry URIs, UC function names, data pipelines, Vector Search resources, and deployment configuration must resolve to `ecommerce_agent`. Environment overrides may parameterize the catalog but must default to `ecommerce_agent`. This decision does not by itself choose schema names such as `gold` versus `gold_layer`; schema naming must be aligned separately.

## [2026-07-16] Support both explicit UC function transports

**Decision:** Support both Databricks managed MCP and the current top-level `UCFunctionToolkit` in `agent_core`, with exactly one transport selected explicitly for each agent build and no automatic fallback.
**Alternatives considered:** Make managed MCP the only core transport, keep `UCFunctionToolkit` only in certification notebooks, run both transports simultaneously, or silently fallback from MCP to the toolkit.
**Reason:** The product needs the current governed MCP integration while the same reusable core must support direct UC function access and certification practice; explicit selection preserves both without duplicate tool names or hidden changes in authentication and failure behavior.
**Consequences:** `AgentConfig` owns the transport choice. The toolkit path receives an injectable current `DatabricksFunctionClient`; the MCP path retains its own typed server configuration. A failure in either path is surfaced directly, and switching transports is a deliberate configuration/deployment action. This supersedes the earlier decision that restricted `UCFunctionToolkit` to compatibility targets, but retains its ban on silent fallback.

## [2026-07-17] Use a versioned synthetic refund policy for the demo

**Decision:** Use `SYNTH-REFUND-2026-01` version `1.0.0`, effective `2026-07-17`, as the canonical refund-policy source for the learning project and label every representation of it as synthetic rather than an Olist policy.
**Alternatives considered:** Keep E6-E9 blocked until a real merchant policy is supplied, infer refund thresholds from general marketplace expectations, or implement unversioned thresholds directly in code.
**Reason:** The user explicitly approved a synthetic policy so the project can exercise auditable policy extraction, governed Unity Catalog functions, boundary testing, and agent safety without making unsupported claims about a real company.
**Consequences:** The implementation must preserve the policy ID, version, effective date, explicit evaluation date, three-state decision contract, and documented matrix. Any semantic policy change requires a new version and tests; production or real-customer use requires replacing this synthetic source with approved legal/business policy.

## [2026-07-17] Grant coding agents standing Databricks workspace authorization

**Decision:** Coding agents may autonomously inspect, create, update, deploy, grant, run, verify, and clean up project-scoped Databricks resources required by the active Sprint Plan without requesting approval for each routine workspace operation.
**Alternatives considered:** Require manual UI operations from the user, request approval before every workspace mutation, or permit unrestricted changes across the whole workspace.
**Reason:** The remaining Sprint 1 work is dominated by credentialed App, MCP, Unity Catalog, Bundle, serving, and certification validation; repeated approval and manual UI handoffs would prevent end-to-end verification even though the user explicitly authorized agents to provision everything needed for the project.
**Consequences:** Missing project resources are implementation work rather than automatic blockers. Agents must still preserve the canonical `ecommerce_agent` catalog, credentials, unrelated resources and traffic, use least privilege, gate credentialed tests, restore test compute when safe, and request direction for missing secret values, unavailable admin entitlement, business-policy decisions, or destructive/out-of-scope actions.

## [2026-07-20] Reconcile the two existing Model Serving endpoints within the workspace quota

**Decision:** Maintain exactly two project-owned Model Serving endpoints: `search-and-rerank-endpoint` for retrieval and `deepseek-v4-streaming-agent-lab` for the DeepSeek boundary; reconcile both in place and create no temporary, environment-specific, blue-green, or Agent-serving endpoint.
**Alternatives considered:** Create separate development/staging/production or temporary benchmark endpoints, blue-green deploy DeepSeek with two endpoints, combine reranker and DeepSeek as served entities in one endpoint, or host the agent itself on Model Serving.
**Reason:** The workspace currently enforces a two-active-endpoint project quota. The endpoints have incompatible request/response contracts, while the agent architecture intentionally runs on Databricks Apps rather than Model Serving.
**Consequences:** Bundles and deployment workflows must inspect then reconcile existing endpoint names. DeepSeek upgrades use rolling in-place updates after `NOT_UPDATING` and verify `READY`; benchmarks reuse the existing endpoint. The reranker may be replaced only after an equivalent-quality comparison with direct AI Search or managed MCP.

## [2026-07-20] Route required operations through an explicit request workflow

**Decision:** Required operations are supplied as `custom_inputs.required_operation` with a configured tool name and typed arguments, then executed by `CoreAgent` before model generation.
**Alternatives considered:** Depend on prompt wording, infer intent from keywords, force model-level `tool_choice`, or require the model to produce the tool call before a post-hoc gate.
**Reason:** The DeepSeek thinking route rejects `tool_choice`, while keyword/model inference is not a deterministic safety boundary for governed operations.
**Consequences:** Callers that need a mandatory operation must deliberately select the workflow contract. Optional requests retain real-time streaming; a validated, correlated result is included as model context before any final answer.

## [2026-07-20] Isolate DeepSeek provider code in the served adapter package

**Decision:** Keep DeepSeek-specific Responses API normalization in `deepseek_adapter`, a deployable Model Serving-only package that App and `agent_core` never import.
**Alternatives considered:** Leave the adapter embedded in the experiment notebook, call the provider from the App/core, or host the full agent through Model Serving.
**Reason:** The verified provider protocol needs reasoning replay and rejects `tool_choice`, but those quirks and credentials must not cross the `ChatDatabricks` model boundary used by the App.
**Consequences:** The package is the sole allowed exception to the repository's direct-provider banned-symbol check. K4 logging/reconciliation packages this source into the existing singleton endpoint; app/tool safety remains owned by `CoreAgent`.

## [2026-07-20] Use the DeepSeek singleton as the AgentServer model boundary

**Decision:** Configure the production Agent App's `ChatDatabricks` endpoint as `deepseek-v4-streaming-agent-lab` and grant it `CAN_QUERY` through the existing Bundle resource.
**Alternatives considered:** Keep `databricks-meta-llama-3-3-70b-instruct` as the App model, choose an unverified preconfigured Foundation Model endpoint, or create another Agent Model Serving endpoint.
**Reason:** The deployed Foundation endpoint returned a deterministic `400` that Responses API passthrough is unsupported, while the existing DeepSeek singleton has passed streaming, tool-call, reasoning replay, and two-turn `ChatDatabricks` contracts. The user approved using the existing quota-bound resources and accepts the cost envelope.
**Consequences:** No third endpoint is created and the App remains on Databricks Apps. The DeepSeek adapter remains isolated from App/core imports, but every App smoke now exercises the actual Responses-compatible model boundary; endpoint feature limitations for AI Gateway remain documented separately.

## [2026-07-23] Readiness requires both Lakebase and Agent availability

**Decision:** The Chat UI readiness endpoint returns healthy only when it can query Lakebase and the configured Agent App health endpoint succeeds.
**Alternatives considered:** Report healthy when Lakebase alone succeeds, or only resolve the Agent URL without probing its runtime.
**Reason:** The Chat UI cannot serve a complete chat turn without both dependencies, and control-plane URL resolution does not prove the Agent process is responsive.
**Consequences:** The Agent App exposes a lightweight `/api/health` route, Chat UI readiness returns HTTP 503 for either dependency failure, and deployments must verify both dependency fields.

## [2026-07-23] Cancellation owns the terminal state of an active turn

**Decision:** Browser Stop, the cancel endpoint, and client disconnect share one cancellation promise and abort controller; once cancellation wins, the stream must not race into a failed terminal state.
**Alternatives considered:** Let every path independently update the turn, or treat a disconnected client as an upstream failure.
**Reason:** Independent lifecycle writers produced duplicate cancellation calls and nondeterministic `failed` versus `cancelled` results.
**Consequences:** Active streams are registered by turn, cancellation is idempotent, disconnects request cancellation, upstream aborts are coordinated, and failure persistence is skipped after cancellation.

## [2026-07-24] Use an immutable React snapshot for Chat UI rollback

**Decision:** Roll back the production Chat UI only to a verified immutable React snapshot that uses the current trusted identity and Lakebase schema; retained Streamlit artifacts are evidence only, not rollback candidates.
**Alternatives considered:** Roll back to the latest flattened Streamlit snapshot, use the latest self-contained Streamlit snapshot, or reconstruct and retain a current-source Streamlit deployment.
**Reason:** Live rollback testing proved the flattened snapshot fails its package imports, while the self-contained snapshot predates the trusted owner key and cannot read React-created conversations. Maintaining a second Streamlit runtime would also restore the dependency and operational surface removed at cutover.
**Consequences:** Release evidence must record a compatible React deployment ID and verify existing/post-cutover history before restore. Reintroducing Streamlit as a production rollback path requires an explicit new migration decision and full identity/schema/browser certification.

## [2026-07-24] Reuse the Chat UI App slot for Streamlit demos

**Decision:** Keep exactly the three existing Databricks App resources. React remains the default Chat UI source, while a maintained Streamlit client under `ecommerce_agent/apps/streamlit_chat_ui/` may be deployed temporarily to the same `ecommerce-agent-chat-ui` resource for demos and must then be switched back to React.
**Alternatives considered:** Create a fourth independent Streamlit App, merge the MCP facade into the Agent App to free a slot, remove Streamlit permanently, or run React and Streamlit concurrently.
**Reason:** Databricks Free Edition supports up to three Apps per account and the project already uses all three for Agent, Chat UI, and MCP facade. A fourth App is unavailable, while merging services changes runtime topology and violates Sprint 5's path-only refactor constraint. Restoring Streamlit satisfies the requested demo fallback only if it is certified against the current trusted identity, Lakebase schema, and streaming contract.
**Consequences:** React and Streamlit cannot run concurrently on Free Edition. The switch workflow must record the React snapshot, reuse the same resource and bindings, verify owner-scoped history and streaming in Streamlit, restore React, and verify data continuity. Streamlit is a demo source rather than the production rollback artifact; a paid workspace may reconsider a separate App in a future architecture sprint.

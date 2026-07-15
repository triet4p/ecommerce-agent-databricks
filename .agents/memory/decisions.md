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

# Databricks Implementation and Certification Index

Last reviewed: 2026-07-20

The runnable Sprint 1 lab procedures are collected in
[SPRINT_1_LABS.md](certification-labs/SPRINT_1_LABS.md).

Exam baseline: [Databricks Certified Generative AI Engineer Associate exam guide,
effective 2026-03-18](https://www.databricks.com/sites/default/files/2026-02/Databricks-Certified-Generative-AI-Engineer-Associate-Exam-Guide-Interrim-Feb26.pdf).
Recheck the guide two weeks before the scheduled exam date.

## How to Use This Index

Use this file in both directions:

- Before implementing a task, open the linked official Databricks documentation
  and verify that the planned API is still current.
- While studying, follow the implementation anchor to find the corresponding
  production code, test, or isolated certification lab.

Status legend:

- **Prototype:** An artifact exists, but it may still need sprint fixes.
- **Planned:** Covered by a pending Sprint 1 implementation task.
- **Lab:** Deliberately isolated certification exercise, not production runtime.
- **Gap:** No end-to-end exercise is currently planned.

## Implementation-to-Documentation Map

### Agent architecture and application lifecycle

| Knowledge implemented | Repository anchor | Official Databricks documentation | Exam objectives covered | Status |
|---|---|---|---|---|
| Business inputs, outputs, and typed agent configuration | [`agent_core/config_schema.py`](../agent_core/config_schema.py), Sprint B1-B3 | [Author an AI agent and deploy it on Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent) | Design chain components; translate a business use case into pipeline inputs and outputs; code a simple chain | Prototype + Planned |
| LangChain 1.x agent construction with `ChatDatabricks` and `create_agent` | [`agent_core/orchestrator.py`](../agent_core/orchestrator.py), Sprint C1 | [Author an AI agent](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent), [Databricks LangChain integration](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html) | Select LangChain tools; use MLflow and Agent Framework; select chain components | Prototype + Planned |
| MLflow `ResponsesAgent` and `AgentServer` on Databricks Apps | [`agent_core/orchestrator.py`](../agent_core/orchestrator.py), Sprint G1-G3 | [Author an AI agent](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent), [Productionize a Databricks Apps agent](https://docs.databricks.com/aws/en/agents/agent-framework/productionize-agent) | Use Agent Framework; serve an LLM application; develop an interactive interface | Implemented + Live verified |
| Prompt instructions, always-on rules, and progressive-disclosure skills | [`ecommerce_agent/rules`](../ecommerce_agent/rules), [`ecommerce_agent/skills`](../ecommerce_agent/skills), Sprint D1-D5 | [Use prompts in deployed applications](https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry/use-prompts-in-deployed-apps), [MLflow 3 for GenAI](https://docs.databricks.com/aws/en/mlflow3/genai/) | Design prompts; adjust responses from a baseline; implement guardrails; manage prompt lifecycle | Prototype + Planned |
| App identity, OAuth, least-privilege resources, and app-to-app access | [`ecommerce_agent/apps`](../ecommerce_agent/apps), Sprint G5-G6 | [Add resources to a Databricks App](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/resources), [Author an AI agent: authentication](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent) | Control access to serving resources; develop an authenticated user interface | Prototype + Planned |
| Declarative Automation Bundles and deployment targets | Sprint G4-G5 and H4 | [What are Declarative Automation Bundles?](https://docs.databricks.com/aws/en/dev-tools/bundles/), [Bundle authentication](https://docs.databricks.com/aws/en/dev-tools/bundles/authentication) | Apply CI/CD practices; promote and test agent components across environments | Implemented + Validated |

### Governed tools and MCP

| Knowledge implemented | Repository anchor | Official Databricks documentation | Exam objectives covered | Status |
|---|---|---|---|---|
| Unity Catalog SQL functions for governed order, seller, and shipping lookup | [`ecommerce_agent/tools/sql_tools.py`](../ecommerce_agent/tools/sql_tools.py), Sprint E1-E5 | [Unity Catalog UDFs](https://docs.databricks.com/aws/en/udf/unity-catalog), [Unity Catalog tools with LangChain](https://docs.databricks.com/aws/en/agents/agent-framework/unity-catalog-tool-integration) | Define and order tools; create tools for structured retrieval; apply Unity Catalog governance | Prototype + Planned |
| Unity Catalog Python function for governed refund-policy logic | [`ecommerce_agent/policies/refund_policy.py`](../ecommerce_agent/policies/refund_policy.py), [`docs/policies/synthetic-refund-policy.md`](policies/synthetic-refund-policy.md), Sprint E6-E9 | [Unity Catalog UDFs](https://docs.databricks.com/aws/en/udf/unity-catalog), [What are UDFs?](https://docs.databricks.com/aws/en/udf) | Define action tools; govern and reuse business logic | Implemented + workspace verified |
| Managed MCP discovery and execution of allowlisted UC functions | Sprint C6-C8 and I4 | [Databricks managed MCP servers](https://docs.databricks.com/aws/en/agents/mcp/managed-mcp), [Use MCP servers in agents](https://docs.databricks.com/aws/en/agents/mcp/use-mcp-in-agents) | Integrate managed MCP servers; control tool access and authentication | Planned + Lab |
| Direct top-level `UCFunctionToolkit` integration and schema comparison | Sprint C9 and I3 | [Unity Catalog tools with LangChain](https://docs.databricks.com/aws/en/agents/agent-framework/unity-catalog-tool-integration), [Databricks LangChain API](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html) | Select LangChain tools; understand governed function tool schemas | Lab |
| Deterministic local tools for calculations that need no external resource | [`ecommerce_agent/tools/python_tools.py`](../ecommerce_agent/tools/python_tools.py), Sprint C3 and E10-E13 | [Define local Python function tools](https://docs.databricks.com/aws/en/agents/agent-framework/author-agent) | Define and order tools that gather knowledge or take actions | Prototype + Planned |
| Custom MCP server and app-to-app agent invocation | [`ecommerce_agent/apps/mcp_facade`](../ecommerce_agent/apps/mcp_facade), Sprint G6 | [Use MCP servers in agents](https://docs.databricks.com/aws/en/agents/mcp/use-mcp-in-agents), [Build a multi-agent system on Databricks Apps](https://docs.databricks.com/aws/en/agents/agent-framework/multi-agent-apps) | Integrate custom MCP; build an appropriate agent-facing interface | Implemented + Live verified |
| MCP tool allowlists, policies, audit, and rate controls | Sprint C8, G5, and I7 | [Govern an MCP service](https://docs.databricks.com/aws/en/ai-gateway/govern-mcp-service), [AI governance guide](https://docs.databricks.com/aws/en/ai-gateway/ai-governance) | MCP governance; malicious-input guardrails; usage and cost controls | Planned |

### Data preparation and retrieval

| Knowledge implemented | Repository anchor | Official Databricks documentation | Exam objectives covered | Status |
|---|---|---|---|---|
| UC Volumes for raw non-tabular input data | [`data-processing/TransformDocumentsData.py`](../data-processing/TransformDocumentsData.py), [`data-processing/TransformOlistData.py`](../data-processing/TransformOlistData.py) | [Work with files in Unity Catalog volumes](https://docs.databricks.com/aws/en/volumes/volume-files) | Identify and ingest required source documents | Prototype |
| Bronze, Silver, and Gold Delta tables | [`data-processing/TransformOlistData.py`](../data-processing/TransformOlistData.py) | [Medallion lakehouse architecture](https://docs.databricks.com/aws/en/lakehouse/medallion) | Define the sequence for writing prepared data into Delta tables in Unity Catalog | Prototype + Planned |
| Document cleaning and chunking | [`data-processing/TransformDocumentsData.py`](../data-processing/TransformDocumentsData.py), Sprint I6 | [Build an unstructured data pipeline for RAG](https://docs.databricks.com/aws/en/agents/tutorials/ai-cookbook/quality-data-pipeline-rag) | Choose chunking; filter extraneous content; design advanced chunking | Prototype + Planned |
| Delta-backed AI Search index creation and synchronization | [`data-processing/TransformDocumentsData.py`](../data-processing/TransformDocumentsData.py) | [Create AI Search endpoints and indexes](https://docs.databricks.com/aws/en/ai-search/create-ai-search) | Create an AI Search index; explain AI Search components; configure index type and sync | Prototype + Planned |
| ANN, hybrid search, metadata filtering, and reranking | [`agent_core/retriever_interface.py`](../agent_core/retriever_interface.py), Sprint F1-F3 and I6 | [Query an AI Search index](https://docs.databricks.com/aws/en/ai-search/query-ai-search) | Explain reranking; configure retrieval for quality, latency, and cost | Prototype + Planned |
| Retrieval evaluation dataset, recall/rank/latency, and relevance judges | [`data-processing/CreateDocumentEvalDataset.py`](../data-processing/CreateDocumentEvalDataset.py), [`ecommerce_agent/eval`](../ecommerce_agent/eval), Sprint I6-I7 | [Evaluation dataset reference](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/eval-datasets), [Retrieval relevance judges](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/judges/is_context_relevant) | Evaluate retrieval performance; select chunking based on retrieval evaluation | Prototype + Planned |

### MLflow, deployment, evaluation, and monitoring

| Knowledge implemented | Repository anchor | Official Databricks documentation | Exam objectives covered | Status |
|---|---|---|---|---|
| Prompt Registry versions and environment aliases | [`ecommerce_agent/register_prompt.py`](../ecommerce_agent/register_prompt.py), [`agent_core/prompt_registry.py`](../agent_core/prompt_registry.py) | [Use prompts in deployed applications](https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry/use-prompts-in-deployed-apps) | Apply prompt version control, promotion, and rollback | Prototype + Planned |
| MLflow tracing of prompts, retrieval, tool calls, latency, and outputs | [`agent_core/orchestrator.py`](../agent_core/orchestrator.py), Sprint G1-G3 and I7 | [MLflow 3 for GenAI](https://docs.databricks.com/aws/en/mlflow3/genai/) | Use MLflow and Agent Framework; evaluate agents with tracing | Prototype + Planned |
| Evaluation datasets, built-in judges, custom scorers, and SME feedback | [`ecommerce_agent/eval`](../ecommerce_agent/eval), Sprint I7 | [Evaluate and monitor AI agents](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor), [Built-in LLM judges](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/judges/) | Select judges requiring ground truth; use custom scorers; incorporate SME feedback | Planned + Lab |
| MLflow pyfunc, model signature, UC model registration, secret injection, and `ChatDatabricks` streaming/reasoning round-trip through Model Serving | [`experiments/DeepSeekServingEndpointStreaming.py`](../experiments/DeepSeekServingEndpointStreaming.py), Sprint I5/J1-J5 | [Deploy custom Python code](https://docs.databricks.com/aws/en/machine-learning/model-serving/deploy-custom-python-code), [Configure secret environment variables](https://docs.databricks.com/aws/en/machine-learning/model-serving/store-env-variable-model-serving), [Databricks LangChain API](https://api-docs.databricks.com/python/databricks-ai-bridge/latest/databricks_langchain.html) | Code a pyfunc chain; inspect its signature; register a model in UC; control and query a serving endpoint through the application model adapter | Lab — runtime verified 2026-07-15 |
| Unity AI Gateway permissions, inference tables, usage, costs, and rate limits | [`ecommerce_agent/driver.py`](../ecommerce_agent/driver.py), Sprint I7 | [Unity AI Gateway](https://docs.databricks.com/aws/en/ai-gateway), [Configure AI Gateway on serving endpoints](https://docs.databricks.com/aws/en/ai-gateway/configure-ai-gateway-endpoints) | Inference logging; cost controls; inference tables; rate limiting; agent monitoring | Lab + Workspace capability verified |
| Batch inference with `ai_query` | No implementation anchor | [Use `ai_query`](https://docs.databricks.com/aws/en/large-language-models/ai-query), [Deploy batch inference pipelines](https://docs.databricks.com/aws/en/large-language-models/batch-inference-pipelines) | Identify batch inference and apply `ai_query` appropriately | Gap |

## Certification Coverage Estimate

The current guide contains 56 individually listed objectives across six
sections. It does not publish a weight for each objective, so this index uses an
objective-count estimate:

- Full hands-on coverage = `1`.
- Partial or adjacent coverage = `0.5`.
- No planned exercise = `0`.

| Exam section | Objectives | Full | Partial | Gap | Adjusted coverage | Section estimate |
|---|---:|---:|---:|---:|---:|---:|
| 1. Design Applications | 6 | 3 | 1 | 2 | 3.5 | 58% |
| 2. Data Preparation | 8 | 6 | 1 | 1 | 6.5 | 81% |
| 3. Application Development | 13 | 7 | 2 | 4 | 8.0 | 62% |
| 4. Assembling and Deploying Applications | 15 | 10 | 3 | 2 | 11.5 | 77% |
| 5. Governance | 4 | 0 | 1 | 3 | 0.5 | 13% |
| 6. Evaluation and Monitoring | 10 | 9 | 0 | 1 | 9.0 | 90% |
| **Total** | **56** | **35** | **8** | **13** | **39.0** | **69.6%** |

Interpretation:

- Completed Sprint 1 plus labs I2-I8 gives approximately **70% syllabus
  coverage** using the adjusted method.
- Counting only full end-to-end objectives gives a stricter floor of
  `35 / 56 = 62.5%`.
- These numbers measure topic coverage, not expected exam score. Question
  distribution and difficulty are not guaranteed to be uniform.

## Known Gaps

The 13 uncovered objectives are concentrated in:

- Agent Bricks selection and use cases.
- Model task selection, model cards/Marketplace, and quantitative model
  comparison experiments.
- OCR or image-document extraction package selection.
- Multi-agent use of Genie Spaces or the conversational API.
- Batch inference with `ai_query`.
- Persistent agent memory or structured intermediate storage.
- Governance topics: masking, legal/licensing risk, and mitigation of problematic
  source text.
- Quantitative LLM selection using evaluation metrics.

Closing the first six technical gaps with focused labs would move planned
coverage into roughly the **80–85%** range. Legal/licensing and governance still
require dedicated study even when they do not naturally belong in the product
runtime.

## Maintenance Rule

When adding or completing an implementation task:

1. Add or update its row in the implementation map.
2. Link only current official Databricks or MLflow documentation.
3. Mark the corresponding objective as full, partial, or gap.
4. Recalculate the section and total coverage.
5. Do not upgrade a partial objective to full until a testable code path or
   reproducible lab exists.

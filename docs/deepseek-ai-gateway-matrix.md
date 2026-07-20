# DeepSeek custom endpoint: AI Gateway capability matrix

Endpoint: `deepseek-v4-streaming-agent-lab` (custom MLflow model, singleton).
Reviewed 2026-07-20 against Databricks AI Gateway documentation.

| Control | Custom endpoint status | Sprint action |
|---|---|---|
| Usage tracking | The current workspace API rejected the requested configuration on 2026-07-20; this is a workspace/endpoint-capability result, not a general custom-model limitation. | Recheck after edition/capability changes. Do not represent usage tracking as active until endpoint read-back exposes it. |
| AI Gateway inference tables | The current workspace API rejected the requested configuration on 2026-07-20. Official documentation supports payload logging for custom endpoints subject to UC permissions and endpoint capability. | Keep `ecommerce_agent.agent_layer` as the approved target and reattempt only after workspace capabilities change. |
| QPM | A QPM-only SDK 0.120.0 request with endpoint limit 15 returned `Rate limits is not currently supported for this endpoint type in this workspace.` Endpoint read-back still has no `ai_gateway` config. Official documentation supports QPM generally; TPM remains unsupported for custom models/agents. | Keep the tested reconciliation code, but rely on application limits in this workspace and never claim QPM 15 is active. |
| TPM | Unsupported for custom models/agents | Enforce bounded output and tool-loop work in application/provider code. |
| Input guardrails | Capability must be confirmed in endpoint UI/API before enablement | Treat as optional; do not claim it protects provider-side behavior until verified. |
| Output guardrails | Unsupported for streaming | Preserve no reasoning text, cap output tokens, and keep deterministic operation checks outside the model. |
| Traffic split/fallback | Not used | Prohibited by the two-endpoint quota and incompatible model contracts. |

References: [configure AI Gateway](https://docs.databricks.com/aws/en/ai-gateway/configure-ai-gateway-endpoints),
[legacy inference-table migration](https://docs.databricks.com/aws/en/machine-learning/model-serving/enable-model-serving-inference-tables).

## Approved deployment inputs and fallback

The learning deployment uses these approved values when the workspace exposes
the capability:

1. Inference table target: `ecommerce_agent.agent_layer`.
2. Endpoint QPM: 15.
3. Payload logging remains disabled until a retention/access policy is approved.

The endpoint is already constrained to a single served entity.
When supported, call `deepseek_adapter.deployment.configure_ai_gateway()` with
an `AiGatewayDeploymentConfig`; it uses the pinned SDK's `put_ai_gateway` API,
updates only `deepseek-v4-streaming-agent-lab`, and does not alter the served
entity, traffic, secret reference, or scale-to-zero setting. Set
`enable_inference_table=False` only after recording an API capability failure;
retry QPM and usage tracking only when the workspace capability allows them.
Until then, `CoreAgent` caps caller input at 100,000 characters and graph
execution at 12 steps, while the configured model output cap is 1,500 tokens per
call.

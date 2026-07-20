# K8 DeepSeek singleton benchmark — 2026-07-20

Endpoint: `deepseek-v4-streaming-agent-lab`
Configuration observed: `Small`, `scale_to_zero=True`, `READY`, `NOT_UPDATING`.

| Run | Request | Elapsed | TTFT | Chunks | Visible characters |
|---|---|---:|---:|---:|---:|
| First observed | short no-tool stream | 35.630s | parser not yet block-aware | 5 | not measured |
| Warm observed | short no-tool stream | 3.904s | parser not yet block-aware | 5 | not measured |
| Verified streaming | `Reply with exactly: benchmark ok` | 8.913s | 8.673s | 5 | 12 |

The verified run used `ChatDatabricks(use_responses_api=True)` and the
block-aware parser in `deepseek_adapter.benchmark`; it did not create or update
an endpoint. The first 35.630s response may represent cold-start/provider
latency, but control-plane state alone cannot prove cold start.

## Cost envelope

The canonical model is `deepseek-v4-flash`. The official DeepSeek price reviewed
2026-07-20 is USD 0.14 per 1M cache-miss input tokens, USD 0.0028 per 1M
cache-hit input tokens, and USD 0.28 per 1M output tokens:
https://api-docs.deepseek.com/quick_start/pricing

The adapter caps output at 1,500 tokens per model call. `CoreAgent` additionally
caps caller input at 100,000 characters and LangGraph execution at 12 steps. A
conservative upper bound that assumes every graph step invokes the provider is
18,000 output tokens, or USD 0.00504 of provider output charges per App request;
real graph runs use fewer model calls. Input charges depend on provider token
count and cache hits, so character limits are a safety envelope rather than an
exact dollar assertion.

Free Edition does not expose usable Databricks Serving billing data for this
endpoint, so an exact combined Databricks-plus-provider amount cannot be derived.
K8 is complete for the learning deployment: latency is measured, provider price
and formula are recorded, and application limits are enforced. A paid production
promotion requires a new billing-data measurement rather than reusing this
Free Edition estimate.

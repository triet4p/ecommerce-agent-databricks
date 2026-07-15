# Architecture Icon Attribution

**Last verified:** 2026-07-15

The architecture diagram embeds the following unmodified source assets as
base64 data URIs. They are embedded for offline rendering; this directory is the
provenance manifest rather than a second copy of the binaries.

| Mark | Primary source | Repository/license or terms | SHA-256 |
|---|---|---|---|
| Databricks favicon, 48×48 PNG | [Databricks brand portal CDN](https://cdn.bfldr.com/9AYANS2F/at/tcrz8bc986mhsq69gn9x2cvn/databricks-favicon-48x48-orange.png?auto=webp&format=png) | [Databricks brand guidelines](https://brand.databricks.com/iconography); trademark asset, used unmodified | `3983414caf2537ac59d2ee2852f00389a4ed4c03619c78561ff40613a42da49d` |
| Delta Lake favicon SVG | [`delta-io/website`](https://github.com/delta-io/website/blob/main/public/favicon.svg) | Official Delta Lake website repository, Apache-2.0; project marks may have additional trademark protections | `461df4bd0f6832924b6ab5e7f191ce9580b1d10e9f79659b3b833c81defc9983` |
| MLflow icon SVG | [`mlflow/mlflow`](https://github.com/mlflow/mlflow/blob/master/assets/icon.svg) | Official MLflow repository, Apache-2.0; project marks may have additional trademark protections | `b54d9e0cef3459854666eb7be0f3bb0662ac4ed69674c0af64abe6157438197f` |
| MCP favicon SVG | [`modelcontextprotocol/modelcontextprotocol`](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/favicon.svg) | Official MCP specification/documentation repository, MIT | `f6f33e24e95846f9ae2582ab72c4eae7beec5ec52c13d767d9f342bf639dd3e6` |

## Usage Rules

- Keep every mark unmodified: do not recolor, stretch, crop, rotate, or combine
  it with a new logo.
- Use marks as small product-identification aids next to explicit text labels;
  never rely on the icon alone to define a service or architecture boundary.
- Do not infer that a generic Databricks favicon is a dedicated product icon for
  Apps, DAB, Unity Catalog, AI Search, or Model Serving.
- Do not source replacement assets from blogs, icon aggregators, Wikimedia, or
  search-result thumbnails when a primary source exists.
- When replacing an asset, update its primary URL, retrieval date, SHA-256, and
  every embedded data URI in the same change.
- Render all three pages after any icon update. SVG payloads are treated as
  untrusted until source, content, checksum, and rendered output are verified.

## Embedded Instances

- Databricks: `p1-app-glyph`, `p2-dab-glyph`
- Delta Lake: `p1-delta-glyph`, `p2-delta-glyph`
- MLflow: `p1-mlflow-glyph`
- MCP: `p1-mcp-glyph`, `p2-mcp-glyph`, `p3-mcp-glyph`

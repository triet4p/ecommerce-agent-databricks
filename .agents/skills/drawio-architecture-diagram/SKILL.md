---
name: drawio-architecture-diagram
description: Create, redesign, and maintain polished editable draw.io architecture diagrams with clear page structure, orthogonal connector routing, non-overlapping labels and icons, official product assets, attribution, rendered previews, and visual QA. Use this skill whenever the user asks for a .drawio file, diagrams.net architecture, a system/data/deployment flow, standard Databricks or technology icons, or says arrows, icons, text, spacing, or an existing diagram look messy—even if they only ask to “make the architecture diagram nicer.”
compatibility: Requires editable draw.io XML; draw.io Desktop is recommended for PNG/PDF rendering. Validation scripts use Python 3 and PowerShell.
---

# Draw.io Architecture Diagram

Produce an editable architecture source that communicates one coherent story per
page and remains attractive after real draw.io rendering—not merely XML that
parses.

## Definition of done

A diagram change is complete only when all of these are true:

1. The `.drawio` source is valid, editable, and uncompressed for useful diffs.
2. Page boundaries and visual hierarchy match the architecture's actual
   boundaries.
3. Connectors do not cross node bodies or text, and unrelated connectors do not
   share the same visual segment.
4. Icons have dedicated space and do not cover labels.
5. Product marks come from primary sources, remain unmodified, and have an
   attribution/checksum record.
6. Every affected page has been rendered and inspected at original resolution.
7. The companion architecture document and previews are updated when applicable.

Read [references/visual-quality-checklist.md](references/visual-quality-checklist.md)
before editing a complex or multi-page diagram.

## 1. Understand the story before drawing

Inspect the existing `.drawio`, its companion Markdown, preview images, and icon
attribution manifest. Confirm:

- intended readers and decision the diagram should support;
- system boundary, trust/permission boundaries, and ownership;
- production path versus optional, compatibility, or certification paths;
- request direction, data direction, and deployment direction;
- pages that already own parts of the story.

Do not begin by placing every component on one canvas. Split the content when
one page would need multiple unrelated reading orders. Common architecture pages
are:

1. Production runtime and request/tool flow.
2. Data, retrieval, and observability flow.
3. Delivery/deployment or placement decisions.

## 2. Establish a visual grammar

Choose a small consistent system before editing XML:

- one primary reading direction, usually left to right;
- swimlanes or containers for ownership and platform boundaries;
- one fill/stroke family per semantic category, not per individual service;
- solid connectors for runtime/data flow and dashed connectors for optional or
  control-plane relationships;
- consistent node widths, corner radii, typography, and internal padding;
- a restrained legend only when styles cannot be understood from labels.

Text remains the source of truth. An icon is a product-identification aid, not a
replacement for an explicit service name.

## 3. Lay out nodes before connectors

1. Place page title, subtitle, and legend zones.
2. Place large boundaries/swimlanes.
3. Arrange primary-flow nodes on a shared grid.
4. Reserve horizontal or vertical connector corridors between groups.
5. Place secondary/optional nodes away from the production path.
6. Allocate a dedicated icon badge or icon column before writing the label.

Keep at least 12–16 px between an icon and text. Prefer a separate icon cell near
a node corner or an internal two-column layout. If a badge overlaps the node
outline, reserve that corner by shortening or offsetting the label; never place a
badge over text and hope rendering will fit.

## 4. Route connectors deliberately

Use `orthogonalEdgeStyle` by default. For each edge:

- choose explicit source/target sides that match the reading direction;
- use `exitX`, `exitY`, `entryX`, and `entryY` to spread multiple connections;
- add waypoints when the automatic route would cross another node or label;
- give parallel flows separate corridors rather than stacking them;
- keep arrowheads clear of labels and container headers;
- place edge labels on quiet segments with an opaque or page-colored background;
- avoid long backtracking arrows—move the node or split the page instead.

Connectors that represent the same bus may share a segment deliberately. Other
shared segments make the flow ambiguous and must be separated.

## 5. Use real icons safely

Search official brand portals, product documentation, or the project's official
repository before using favicons or SVGs. Avoid blogs, icon aggregators,
search-result thumbnails, and community redraws when a primary source exists.

For every external asset:

1. Record the primary URL, license/brand terms, retrieval date, and SHA-256.
2. Inspect SVG/XML as untrusted text before embedding it.
3. Keep the mark unmodified: do not recolor, crop, stretch, rotate, or combine it
   into a new logo.
4. Embed it as a base64 data URI when offline rendering and repository portability
   matter.
5. Use `imageAspect=0;aspect=fixed` and a square geometry where appropriate.
6. Update the attribution manifest in the same change.

Do not imply that a generic company favicon is an official icon for every product
from that company. Label the actual product explicitly.

## 6. Edit source for maintainability

- Keep `<mxfile compressed="false">` in source-controlled diagrams.
- Give cells stable, descriptive IDs such as `p1-agent-runtime` or
  `p2-vector-index-edge`; do not regenerate unrelated IDs.
- Keep one `<diagram>` per page with a descriptive name.
- Use a 10 px grid and integer geometry where practical.
- Preserve unaffected pages and existing user changes.
- Escape HTML/XML content correctly and keep styling in predictable key order.
- Change the architecture version/date when the repository's maintenance policy
  requires it.

Run the structural validator:

```powershell
python .agents/skills/drawio-architecture-diagram/scripts/validate_drawio.py `
  docs/architecture/ecommerce-agent-architecture.drawio
```

Errors block completion. Warnings identify items that require visual inspection;
do not suppress them merely to make the command green.

## 7. Render every affected page

Use the bundled renderer on Windows:

```powershell
.agents/skills/drawio-architecture-diagram/scripts/render_drawio.ps1 `
  -InputFile docs/architecture/ecommerce-agent-architecture.drawio `
  -OutputDirectory docs/architecture/previews
```

If draw.io Desktop is unavailable, locate an existing installation first. Ask
before installing software or launching a GUI. CLI export is preferred for
repeatable QA.

After rendering, inspect each PNG with an image viewer at original resolution.
Do not rely on a scaled IDE thumbnail. Check title/header clipping, node text,
icon/text clearance, arrowheads, connector crossings, edge-label placement,
balanced whitespace, and visual reading order. Iterate until the rendered output
passes—not just until the XML validator passes.

## 8. Update living documentation

When the diagram documents a maintained architecture:

- update the companion Markdown explanation and preview links;
- update the icon attribution manifest and checksums;
- record durable architecture decisions in project memory;
- refresh certification/documentation mappings if the architecture coverage
  changed;
- mention the draw.io Desktop version used for the final render.

## Visual failure patterns

- Icons placed on top of long centered labels.
- Orthogonal edges sharing a trunk accidentally, making arrow ownership unclear.
- Multiple arrows entering the same node at exactly the same point.
- Connectors crossing swimlane titles or node bodies.
- Tiny nodes with five lines of text and no internal padding.
- One page mixing runtime, ingestion, deployment, and decision rationale.
- Every Databricks product represented by the same favicon without labels.
- Remote image URLs that render only while online.
- Updating the `.drawio` source without regenerating previews.
- Declaring success without opening the rendered pages.

## Handoff format

Lead with what changed and where. Include:

```text
Source: editable .drawio path
Pages: created/changed page names
Previews: rendered output paths
Validation: errors/warnings and how warnings were reviewed
Assets: new/changed icons and attribution path
Visual QA: pages inspected and notable routing/layout decisions
```


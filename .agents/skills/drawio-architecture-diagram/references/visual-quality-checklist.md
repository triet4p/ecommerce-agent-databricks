# Draw.io Visual Quality Checklist

Use this as a design and review aid, not as a substitute for judgment. Large
architecture diagrams need generous whitespace and intentional routing more than
they need decorative detail.

## Canvas and hierarchy

- Use a page size suited to the content; 1600–2200 px wide is a practical range
  for detailed landscape architecture pages.
- Keep at least 40 px outer margin and 20–30 px between the title area and the
  architecture content.
- Use a 10 px grid and align related node edges.
- Keep the page title dominant, the subtitle secondary, group headers distinct,
  and node text readable at the final rendered scale.
- Give each page one obvious starting point and one primary reading direction.

## Nodes and groups

- Typical service node: 180–320 px wide and 70–130 px high.
- Horizontal sibling gap: 30–60 px; vertical group gap: 40–80 px.
- Use 12–18 px internal text padding.
- Keep a node to roughly one bold title plus two or three short supporting lines.
  Move detailed explanation into the companion document.
- Use swimlane header sizes around 40–64 px and keep connectors out of headers.
- Do not use color alone to encode meaning; combine it with labels, line style, or
  containment.

## Icons

- Typical product icon: 28–44 px.
- Keep aspect ratio fixed and avoid upscaling low-resolution favicons.
- Reserve 12–16 px clearance from label text.
- Prefer a dedicated left icon column or a corner badge with reserved label space.
- Inspect the real bitmap/SVG render; geometry boxes alone do not reveal opaque
  padding within an asset.
- Use explicit service labels even when the icon is widely recognized.

## Connectors

- Use orthogonal connectors for architecture flows unless a curved relationship
  is intentionally clearer.
- Route primary flow through the visual center; route secondary/control flows
  through outer corridors.
- Spread exits and entries across node sides using explicit anchor fractions.
- Keep at least 10–20 px between parallel connector segments.
- Avoid more than one bend near an edge label.
- Do not place labels on crossings, corners, arrowheads, or swimlane borders.
- Use dashed strokes consistently for optional, async, or control-plane links and
  explain the convention once.

## Product assets and provenance

For each asset, record:

```markdown
| Mark | Primary source | License/terms | Retrieved | SHA-256 |
|---|---|---|---|---|
| Product icon | https://official.example/icon.svg | Official terms | YYYY-MM-DD | `...` |
```

- Inspect SVGs for scripts, external references, and unexpected embedded data.
- Prefer embedded base64 data URIs for offline rendering.
- Never alter a trademark to match the diagram palette.
- Do not call a generic vendor logo a product-specific icon.

## Original-resolution review

For every affected page, answer yes to all:

- Is every label fully visible and readable?
- Does every icon have clear separation from text?
- Can each connector be traced from source to target without ambiguity?
- Are arrowheads visible and attached to the intended node?
- Do any connectors cross text, node bodies, or group headers?
- Are optional and production paths visually distinct?
- Is whitespace balanced rather than concentrated in one corner?
- Does the page still make sense without relying on icon recognition?
- Do preview and source show the same architecture version?

## When to split a page

Split when any two of these are true:

- The page needs more than one reading direction.
- A connector crosses two or more major boundaries only to explain a secondary
  relationship.
- Runtime and deployment flows compete for the same visual corridor.
- Node text must be reduced below the document's normal font size.
- A legend grows because the page uses too many semantic styles.
- Reviewers need different explanations for different parts of the canvas.


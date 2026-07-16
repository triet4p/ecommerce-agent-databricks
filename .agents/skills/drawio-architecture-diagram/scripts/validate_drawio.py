"""Validate editable, uncompressed draw.io architecture sources."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class Issue:
    severity: str
    page: str
    cell_id: str | None
    message: str


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    def intersects(self, other: "Rect") -> bool:
        return not (
            self.x + self.width <= other.x
            or other.x + other.width <= self.x
            or self.y + self.height <= other.y
            or other.y + other.height <= self.y
        )


def parse_style(style: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in style.split(";"):
        if not item:
            continue
        key, separator, value = item.partition("=")
        result[key] = value if separator else ""
    return result


def geometry(cell: ET.Element) -> Rect | None:
    item = cell.find("mxGeometry")
    if item is None:
        return None
    try:
        return Rect(
            x=float(item.get("x", "0")),
            y=float(item.get("y", "0")),
            width=float(item.get("width", "0")),
            height=float(item.get("height", "0")),
        )
    except ValueError:
        return None


def validate(path: Path) -> tuple[list[Issue], dict[str, int]]:
    issues: list[Issue] = []
    stats = {"pages": 0, "vertices": 0, "edges": 0, "images": 0}

    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        return [Issue("error", "<file>", None, str(exc))], stats

    mxfile = tree.getroot()
    if mxfile.tag != "mxfile":
        return [Issue("error", "<file>", None, "Root element must be <mxfile>." )], stats

    if mxfile.get("compressed", "true").lower() != "false":
        issues.append(
            Issue(
                "error",
                "<file>",
                None,
                "Source-controlled diagram must set compressed=\"false\".",
            )
        )

    diagrams = mxfile.findall("diagram")
    stats["pages"] = len(diagrams)
    if not diagrams:
        issues.append(Issue("error", "<file>", None, "No <diagram> pages found."))

    for page_index, diagram in enumerate(diagrams, start=1):
        page_name = diagram.get("name") or f"page-{page_index}"
        graph = diagram.find("mxGraphModel")
        if graph is None:
            issues.append(
                Issue(
                    "error",
                    page_name,
                    None,
                    "Page has no editable mxGraphModel; it may be compressed.",
                )
            )
            continue

        root = graph.find("root")
        if root is None:
            issues.append(Issue("error", page_name, None, "Page has no graph root."))
            continue

        cells = root.findall("mxCell")
        cell_by_id: dict[str, ET.Element] = {}
        for cell in cells:
            cell_id = cell.get("id")
            if not cell_id:
                issues.append(Issue("error", page_name, None, "mxCell is missing id."))
                continue
            if cell_id in cell_by_id:
                issues.append(
                    Issue("error", page_name, cell_id, "Duplicate cell id on page.")
                )
            cell_by_id[cell_id] = cell

        image_cells: list[tuple[ET.Element, Rect]] = []
        text_cells: list[tuple[ET.Element, Rect]] = []

        for cell in cells:
            cell_id = cell.get("id")
            is_vertex = cell.get("vertex") == "1"
            is_edge = cell.get("edge") == "1"
            style = parse_style(cell.get("style", ""))
            rect = geometry(cell)

            if is_vertex:
                stats["vertices"] += 1
                if rect is None or rect.width <= 0 or rect.height <= 0:
                    issues.append(
                        Issue(
                            "error",
                            page_name,
                            cell_id,
                            "Vertex needs positive numeric geometry.",
                        )
                    )
                elif style.get("shape") == "image":
                    stats["images"] += 1
                    image_cells.append((cell, rect))
                    image_value = style.get("image", "")
                    if not image_value:
                        issues.append(
                            Issue("error", page_name, cell_id, "Image cell has no image value.")
                        )
                    elif not image_value.startswith("data:image/"):
                        issues.append(
                            Issue(
                                "warning",
                                page_name,
                                cell_id,
                                "Image is not an embedded data URI; offline rendering may fail.",
                            )
                        )
                    if rect.width > 64 or rect.height > 64:
                        issues.append(
                            Issue(
                                "warning",
                                page_name,
                                cell_id,
                                "Product icon exceeds 64 px; inspect scaling and label clearance.",
                            )
                        )
                elif cell.get("value") and "swimlane" not in style:
                    text_cells.append((cell, rect))

            if is_edge:
                stats["edges"] += 1
                if cell.find("mxGeometry") is None:
                    issues.append(
                        Issue("error", page_name, cell_id, "Edge is missing mxGeometry.")
                    )
                for endpoint in ("source", "target"):
                    endpoint_id = cell.get(endpoint)
                    if endpoint_id and endpoint_id not in cell_by_id:
                        issues.append(
                            Issue(
                                "error",
                                page_name,
                                cell_id,
                                f"Edge {endpoint} references unknown cell {endpoint_id!r}.",
                            )
                        )
                if style.get("edgeStyle") != "orthogonalEdgeStyle":
                    issues.append(
                        Issue(
                            "warning",
                            page_name,
                            cell_id,
                            "Edge is not orthogonal; confirm this is an intentional exception.",
                        )
                    )

        for image_cell, image_rect in image_cells:
            for text_cell, text_rect in text_cells:
                if image_rect.intersects(text_rect):
                    issues.append(
                        Issue(
                            "warning",
                            page_name,
                            image_cell.get("id"),
                            "Image geometry overlaps a labeled node "
                            f"({text_cell.get('id')}); inspect the rendered page for covered text.",
                        )
                    )

    return issues, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("drawio_file", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures after they are reviewed.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output.")
    args = parser.parse_args()

    issues, stats = validate(args.drawio_file)
    if args.json:
        print(json.dumps({"stats": stats, "issues": [asdict(i) for i in issues]}, indent=2))
    else:
        print(
            f"pages={stats['pages']} vertices={stats['vertices']} "
            f"edges={stats['edges']} images={stats['images']}"
        )
        for issue in issues:
            location = issue.page
            if issue.cell_id:
                location += f"/{issue.cell_id}"
            print(f"{issue.severity.upper()}: {location}: {issue.message}")

    has_errors = any(issue.severity == "error" for issue in issues)
    has_warnings = any(issue.severity == "warning" for issue in issues)
    return 1 if has_errors or (args.strict and has_warnings) else 0


if __name__ == "__main__":
    sys.exit(main())


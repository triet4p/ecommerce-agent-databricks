#!/usr/bin/env python3
"""S5-02 — Path-only content invariant checker for Sprint 5 source relocation.

Reads the baseline SHA-256 manifest and a current manifest, maps every old
file to its expected target path per the Sprint 5 plan, and flags any
content change that is not covered by the explicit allowlist.  Returns
exit code 0 when every change is permitted; non-zero otherwise.

Usage:
  uv run python scripts/s5_02_path_invariant.py                       \\
      --baseline artifacts/s5-01-baseline-manifest.sha256              \\
      --current  .                                                     \\
      [--allowlist artifacts/s5-02-content-allowlist.txt]              \\
      [--output   artifacts/s5-02-invariant-report.txt]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Sprint 5 path mapping — every path that will be moved or renamed.
# Keys are directory prefixes; values are the replacement prefixes.
# ---------------------------------------------------------------------------
DIRECTORY_MOVES: dict[str, str] = {
    "ecommerce_agent/agent_app/": "ecommerce_agent/apps/agent_app/",
    "ecommerce_agent/apps/mcp_server/": "ecommerce_agent/apps/mcp_facade/",
    "chat_ui/": "ecommerce_agent/apps/chat_ui/",
}

# Files that will be *added* (no baseline hash) — new package markers,
# restored Streamlit sources (from commit 690f3bb), etc.
NEW_FILES: set[str] = {
    "ecommerce_agent/apps/__init__.py",
    # Streamlit restoration paths (S5-08) — exact set TBD after export.
    "ecommerce_agent/apps/streamlit_chat_ui/app.py",
    "ecommerce_agent/apps/streamlit_chat_ui/requirements.txt",
}

# ---------------------------------------------------------------------------
# Content-change allowlist: patterns that may differ between old and new
# without triggering a violation.
# ---------------------------------------------------------------------------
ALLOWED_CHANGE_PATTERNS = [
    # Import-path updates
    "ecommerce_agent.agent_app",
    "ecommerce_agent.apps.agent_app",
    "ecommerce_agent.apps.mcp_server",
    "ecommerce_agent.apps.mcp_facade",
    # Module commands in YAML
    "uvicorn ecommerce_agent.agent_app",
    "uvicorn ecommerce_agent.apps.agent_app",
    # source_code_path keys in databricks.yml / app.yaml
    "source_code_path",
    # Working-directory references in scripts / docs
    "ecommerce_agent/agent_app",
    "ecommerce_agent/apps/mcp_server",
    "ecommerce_agent/apps/mcp_facade",
    "chat_ui",
    "ecommerce_agent/apps/chat_ui",
    # Test fixture paths
    "tests/",
    # Documentation links (handled by the category-based skip below)
]

# Files where ANY content change is permitted (manifests, docs, configs
# that must reference new paths).
UNCONDITIONAL_ALLOW: set[str] = {
    "databricks.yml",
    "app.yaml",
    "ecommerce_agent/agent_app/app.yaml",
    "ecommerce_agent/apps/mcp_server/app.yaml",
    "chat_ui/app.yaml",
    "pyproject.toml",
}

# File suffixes whose content changes are unconditionally permitted.
UNCONDITIONAL_SUFFIXES: set[str] = {".md", ".txt"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_manifest(path: str | Path) -> dict[str, str]:
    """Parse a sha256sum-format manifest into {relpath: hexdigest}."""
    entries: dict[str, str] = {}
    raw = Path(path).read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Format: "<hash> *./rel/path" or "<hash>  ./rel/path"
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        digest, filepath = parts
        # Strip leading "./" prefix
        filepath = filepath.removeprefix("*").removeprefix("./")
        entries[filepath] = digest
    return entries


def _generate_manifest(root: Path) -> dict[str, str]:
    """Walk *root* and return {relpath: sha256hex} for all source files."""
    EXCLUDE_DIRS = {
        ".venv",
        ".git",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "mlruns",
        ".databricks",
        "artifacts",
        "playwright-report",
        "test-results",
        "dist",
        ".agents",
        ".vscode",
        ".claude",  # tooling, not deployable source
    }
    EXCLUDE_FILES = {"uv.lock", "mlflow.db", "package-lock.json"}

    entries: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        # Skip hidden directories not in the explicit set
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""

        for fname in filenames:
            if fname in EXCLUDE_FILES:
                continue
            # Skip binary / generated files
            if fname.endswith((".db", ".pyc", ".lock")):
                continue

            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root).replace("\\", "/")

            try:
                content = Path(fpath).read_bytes()
                digest = hashlib.sha256(content).hexdigest()
                entries[rel] = digest
            except (OSError, PermissionError):
                continue

    return entries


def _map_old_to_target(old_path: str) -> str:
    """Map a baseline path to its expected target path after Sprint 5."""
    for old_prefix, new_prefix in DIRECTORY_MOVES.items():
        if old_path.startswith(old_prefix):
            return new_prefix + old_path[len(old_prefix) :]
    return old_path  # unmoved


def _changed_lines_are_allowlisted(old_text: str, new_text: str, filepath: str) -> bool:
    """Return True if every changed line in *filepath* matches the allowlist."""
    if not old_text and not new_text:
        return True
    if not old_text or not new_text:
        return False  # file was created or deleted entirely

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    if len(old_lines) != len(new_lines):
        # Line-count change — only permitted in unconditional-allow or docs
        suffix = Path(filepath).suffix
        return suffix in UNCONDITIONAL_SUFFIXES

    # Check each differing line against allowlist patterns
    for i, (old_line, new_line) in enumerate(zip(old_lines, new_lines)):
        if old_line == new_line:
            continue
        # The line changed — is it on the allowlist?
        if not _line_in_allowlist(old_line, new_line):
            return False
    return True


def _line_in_allowlist(old_line: str, new_line: str) -> bool:
    """Check if a line change is permitted by the allowlist."""
    for pattern in ALLOWED_CHANGE_PATTERNS:
        if pattern in old_line or pattern in new_line:
            return True
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="S5-02 path-only invariant check")
    parser.add_argument(
        "--baseline",
        required=True,
        help="Path to the baseline SHA-256 manifest (from S5-01)",
    )
    parser.add_argument(
        "--current",
        required=True,
        help="Root directory to generate the current manifest from",
    )
    parser.add_argument(
        "--output", help="Write the report to this file instead of stdout"
    )
    args = parser.parse_args()

    baseline = _parse_manifest(args.baseline)
    current = _generate_manifest(Path(args.current))

    violations: list[str] = []
    warnings: list[str] = []

    # --- Check 1: Every baseline file maps to exactly one target ---
    old_to_new: dict[str, str] = {}
    for old_path in baseline:
        new_path = _map_old_to_target(old_path)
        old_to_new[old_path] = new_path

    # Check for target-path collisions (two old files → same new path)
    seen_targets: dict[str, list[str]] = {}
    for old, new in old_to_new.items():
        seen_targets.setdefault(new, []).append(old)
    for target, sources in seen_targets.items():
        if len(sources) > 1:
            violations.append(
                f"COLLISION: {len(sources)} old files map to '{target}':\n  "
                + "\n  ".join(sources)
            )

    # --- Check 2: Baseline files that would be missing ---
    # Directories whose contents are generated/build artifacts — not source.
    BUILD_PREFIXES = (
        "chat_ui/client/dist/",
        "chat_ui/server/dist/",
        "chat_ui/packages/core/dist/",
        "chat_ui/server/node_modules/",
        "chat_ui/client/node_modules/",
        "chat_ui/playwright-report/",
        "chat_ui/test-results/",
        "chat_ui/package-lock.json",
        ".agents/",
        ".vscode/",
        ".claude/",
    )

    def _is_build_artifact(path: str) -> bool:
        return any(path.startswith(p) for p in BUILD_PREFIXES)

    for old_path, new_path in old_to_new.items():
        if _is_build_artifact(old_path):
            continue  # generated files are not source — skip
        if new_path not in current and old_path not in current:
            violations.append(
                f"MISSING: '{old_path}' -> '{new_path}' (neither old "
                f"nor new path exists in current tree)"
            )

    # --- Check 3: Content-change scope violations ---
    for old_path, baseline_hash in baseline.items():
        new_path = old_to_new[old_path]
        target_hash = current.get(new_path)
        old_hash = current.get(old_path)

        # File still at old location (move not done yet)
        if old_hash is not None:
            if old_hash != baseline_hash:
                # Content changed at old location — check allowlist
                path = Path(args.current) / old_path
                if path.suffix not in UNCONDITIONAL_SUFFIXES:
                    _check_content_violation(
                        path, old_path, baseline_hash, old_hash, violations, args
                    )
            continue

        # File moved to new location
        if (
            target_hash is not None
            and target_hash != baseline_hash
            and new_path not in UNCONDITIONAL_ALLOW
            and Path(new_path).suffix not in UNCONDITIONAL_SUFFIXES
        ):
            path = Path(args.current) / new_path
            _check_content_violation(
                path, new_path, baseline_hash, target_hash, violations, args
            )

    # --- Check 4: Unexpected new files ---
    for new_path in current:
        if new_path in NEW_FILES:
            continue
        # Check if it's at a new location that maps back to a baseline file
        reverse_map: dict[str, str] = {}
        for old, new in old_to_new.items():
            reverse_map[new] = old

        if new_path in reverse_map:
            continue  # it's a moved file — checked above
        if new_path in baseline:
            continue  # unmoved, unchanged file
        # File exists now but wasn't in baseline and isn't a planned new file
        warnings.append(
            f"UNEXPECTED: '{new_path}' is new since baseline "
            f"(not in the planned NEW_FILES set)"
        )

    # --- Report ---
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("S5-02 Path-Only Content Invariant Report")
    lines.append("=" * 72)
    lines.append(f"Baseline entries:  {len(baseline)}")
    lines.append(f"Current entries:   {len(current)}")
    lines.append(f"Planned moves:     {len(DIRECTORY_MOVES)}")
    lines.append(f"Violations:        {len(violations)}")
    lines.append(f"Warnings:          {len(warnings)}")
    lines.append("=" * 72)

    if violations:
        lines.append("\n--- VIOLATIONS ---")
        for v in violations:
            lines.append(f"  {v}")

    if warnings:
        lines.append("\n--- WARNINGS ---")
        for w in warnings:
            lines.append(f"  {w}")

    if not violations:
        lines.append("\n[PASS] All content changes are within the approved allowlist.")

    report = "\n".join(lines)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        sys.stderr.write(f"Report written to {args.output}\n")

    # Write summary to stderr (avoids cp1252 encoding issues on Windows)
    sys.stderr.write(f"Violations: {len(violations)}  Warnings: {len(warnings)}\n")
    return 1 if violations else 0


def _check_content_violation(
    path: Path,
    rel_path: str,
    baseline_hash: str,
    current_hash: str,
    violations: list[str],
    args: argparse.Namespace,
) -> None:
    """Check if a content change in *path* is permitted."""
    # Try to read the file for detailed line-level analysis
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        violations.append(
            f"CONTENT: '{rel_path}' hash changed ({baseline_hash[:8]} -> "
            f"{current_hash[:8]}) but file is binary/unreadable"
        )
        return

    # For Python files: check if only import lines changed
    suffix = path.suffix
    if suffix == ".py":
        _check_python_import_only(content, rel_path, violations)
    elif suffix in (".yaml", ".yml"):
        _check_yaml_path_only(content, rel_path, violations)
    else:
        violations.append(
            f"CONTENT: '{rel_path}' hash changed "
            f"({baseline_hash[:8]} -> {current_hash[:8]}) -- "
            f"file type '{suffix}' is not in the unconditional-allow set"
        )


def _check_python_import_only(
    content: str, rel_path: str, violations: list[str]
) -> None:
    """Verify Python file changes are limited to import-path updates."""
    # This is a structural check — full line-level analysis requires
    # comparing old and new files, which is done after moves.
    # For now, flag the violation for manual review during S5-12.
    violations.append(
        f"CONTENT: '{rel_path}' — Python file content changed. "
        f"Manual review required during S5-12 audit to confirm "
        f"only import paths were updated."
    )


def _check_yaml_path_only(content: str, rel_path: str, violations: list[str]) -> None:
    """Verify YAML changes are limited to path/manifest fields."""
    violations.append(
        f"CONTENT: '{rel_path}' — YAML file content changed. "
        f"Manual review required during S5-12 audit to confirm "
        f"only source_code_path, module commands, and bundle paths changed."
    )


if __name__ == "__main__":
    sys.exit(main())

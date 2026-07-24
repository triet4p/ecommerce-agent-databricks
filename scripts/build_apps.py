#!/usr/bin/env python3
"""Build self-contained deployment artifacts under .build/apps/.

Each Databricks App source root must be self-contained: the runtime
flattens source_code_path into the working directory, so every import
must resolve relative to that root.  This script copies each app's own
sources together with the shared packages it needs.

Usage:
  uv run python scripts/build_apps.py              # build all
  uv run python scripts/build_apps.py --app agent   # build one
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / ".build" / "apps"

# =====================================================================
# App manifest
#
# Each key under "apps" names a deployment directory under .build/apps/.
#   copy:   list of "src_rel [-> dst_name]" entries (trees or files).
#           If dst_name is "." the contents of src are flattened into
#           the app root.
#   exclude: set of path prefixes to skip during tree copies (relative
#            to the source root being copied).
#   app_yaml:    path to the app.yaml to place at the deployment root.
#   requirements: path to requirements.txt (None for Node apps).
# =====================================================================

APPS: dict[str, dict] = {
    "agent_app": {
        "copy": [
            "agent_core",
            "ecommerce_agent",
        ],
        "exclude": {
            "ecommerce_agent/apps/chat_ui",
            "ecommerce_agent/apps/mcp_facade",
            "ecommerce_agent/apps/streamlit_chat_ui",
        },
        "app_yaml": "ecommerce_agent/apps/agent_app/app.yaml",
        "requirements": "ecommerce_agent/apps/agent_app/requirements.txt",
    },
    "mcp_facade": {
        "copy": [
            "ecommerce_agent/apps/mcp_facade/app_oauth.py -> app_oauth.py",
            "ecommerce_agent/apps/mcp_facade/response_output.py -> response_output.py",
            "ecommerce_agent/apps/mcp_facade/server.py -> server.py",
        ],
        "app_yaml": "ecommerce_agent/apps/mcp_facade/app.yaml",
        "requirements": "ecommerce_agent/apps/mcp_facade/requirements.txt",
    },
    "streamlit_chat_ui": {
        "copy": [
            "ecommerce_agent/conversation -> conversation",
            "ecommerce_agent/apps/streamlit_chat_ui -> apps/streamlit_chat_ui",
        ],
        "app_yaml": "ecommerce_agent/apps/streamlit_chat_ui/app.yaml",
        "requirements": "ecommerce_agent/requirements.txt",
    },
    "chat_ui": {
        "copy": [
            "ecommerce_agent/apps/chat_ui -> .",
        ],
        "exclude": {
            "node_modules",
            "playwright-report",
            "test-results",
            "tests",
            "dist",
        },
        "app_yaml": "ecommerce_agent/apps/chat_ui/app.yaml",
        "requirements": None,  # Node project — package.json drives install
    },
}

# =====================================================================
def _ensure(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _rm(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _build_exclude_filter(src_root: Path, excludes: set[str]):
    """Return an ignore function for shutil.copytree."""

    def _ignore(directory: str, files: list[str]) -> list[str]:
        # directory is the *current* absolute path being walked
        d = Path(directory)
        ignored: set[str] = set()
        for exc in excludes:
            # Check if the excluded path is inside or matches this directory
            exc_path = src_root / exc
            try:
                # Is this directory an ancestor of the excluded path?
                d.relative_to(exc_path)
                # d is inside an excluded path — ignore everything
                return set(files)
            except ValueError:
                pass
            try:
                # Is the excluded path inside this directory?
                exc_path.relative_to(d)
                # Yes — ignore the top-level name under this directory
                rel = exc_path.relative_to(d)
                first = str(rel).replace("\\", "/").split("/")[0]
                if first in files:
                    ignored.add(first)
            except ValueError:
                pass
        return list(ignored)

    return _ignore


def build_app(name: str, cfg: dict) -> bool:
    """Build one app's deployment directory."""
    app_dir = BUILD / name
    print(f"--- {name} ---")

    _rm(app_dir)
    _ensure(app_dir)

    # 1. Copy source items
    excludes: set[str] = cfg.get("exclude", set())
    for entry in cfg["copy"]:
        parts = entry.split("->")
        src_rel = parts[0].strip()
        dst_rel = parts[1].strip() if len(parts) > 1 else src_rel

        src_path = ROOT / src_rel

        if not src_path.exists():
            print(f"  SKIP missing: {src_rel}")
            continue

        if dst_rel == ".":
            # Flatten: copy each top-level item, skipping excludes
            for item in sorted(src_path.iterdir()):
                if item.name in excludes:
                    continue
                item_dst = app_dir / item.name
                _rm(item_dst)
                if item.is_dir():
                    shutil.copytree(str(item), str(item_dst))
                else:
                    shutil.copy2(str(item), str(item_dst))
            print(f"  flatten: {src_rel}/* -> {app_dir}/")
        elif src_path.is_dir():
            item_dst = app_dir / dst_rel
            _rm(item_dst)
            if excludes:
                src_root_for_excludes = ROOT
                shutil.copytree(
                    str(src_path),
                    str(item_dst),
                    ignore=_build_exclude_filter(src_root_for_excludes, excludes),
                )
            else:
                shutil.copytree(str(src_path), str(item_dst))
            print(f"  tree: {src_rel} -> {dst_rel}")
        else:
            item_dst = app_dir / dst_rel
            _ensure(item_dst.parent)
            _rm(item_dst)
            shutil.copy2(str(src_path), str(item_dst))
            print(f"  file: {src_rel} -> {dst_rel}")

    # 2. Place app.yaml at deployment root
    app_yaml_src = ROOT / cfg["app_yaml"]
    if app_yaml_src.exists():
        shutil.copy2(str(app_yaml_src), str(app_dir / "app.yaml"))
        print(f"  app.yaml <- {cfg['app_yaml']}")

    # 3. Place requirements.txt at deployment root
    req = cfg.get("requirements")
    if req:
        req_src = ROOT / req
        if req_src.exists():
            shutil.copy2(str(req_src), str(app_dir / "requirements.txt"))
            print(f"  requirements.txt <- {req}")

    # Sanity
    if not (app_dir / "app.yaml").exists():
        print(f"  ERROR: no app.yaml in {app_dir}")
        return False

    print(f"  OK -> {app_dir}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build self-contained Databricks App deployment dirs"
    )
    parser.add_argument(
        "--app",
        choices=list(APPS) + ["all"],
        default="all",
        help="Which app to build (default: all)",
    )
    args = parser.parse_args()

    _ensure(BUILD)
    names = list(APPS) if args.app == "all" else [args.app]

    ok = True
    for name in names:
        if not build_app(name, APPS[name]):
            ok = False

    if ok:
        print(f"\nDone — apps under {BUILD}/")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

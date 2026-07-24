"""Shared pytest setup for generated deployment artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def build_deployment_artifacts() -> None:
    """Always test freshly generated artifacts instead of stale local output."""

    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "build_apps.py")],
        cwd=REPO_ROOT,
        check=True,
    )

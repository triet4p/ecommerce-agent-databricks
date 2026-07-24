"""Deployment artifact contracts for the four self-contained app sources."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_ROOT = REPO_ROOT / ".build" / "apps"


def _assert_module_resolves(artifact: str, module: str) -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            (
                "import importlib.util,sys;"
                f"sys.exit(0 if importlib.util.find_spec({module!r}) else 1)"
            ),
        ],
        cwd=BUILD_ROOT / artifact,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _assert_streamlit_entrypoint_imports_from_script_directory() -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", "-c", "import app"],
        cwd=BUILD_ROOT / "streamlit_chat_ui" / "apps" / "streamlit_chat_ui",
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "build_apps_under_test", REPO_ROOT / "scripts" / "build_apps.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_contains_exactly_four_app_roots() -> None:
    assert {path.name for path in BUILD_ROOT.iterdir()} == {
        "agent_app",
        "chat_ui",
        "mcp_facade",
        "streamlit_chat_ui",
    }


def test_agent_artifact_contains_and_resolves_runtime_module() -> None:
    assert (
        BUILD_ROOT
        / "agent_app"
        / "ecommerce_agent"
        / "apps"
        / "agent_app"
        / "server.py"
    ).is_file()
    assert (BUILD_ROOT / "agent_app" / "pyproject.toml").is_file()
    assert (BUILD_ROOT / "agent_app" / "uv.lock").is_file()
    _assert_module_resolves("agent_app", "ecommerce_agent.apps.agent_app.server")


def test_mcp_artifact_resolves_flat_runtime_module() -> None:
    assert (BUILD_ROOT / "mcp_facade" / "server.py").is_file()
    _assert_module_resolves("mcp_facade", "server")


def test_streamlit_manifest_targets_existing_nested_entrypoint() -> None:
    artifact = BUILD_ROOT / "streamlit_chat_ui"
    config = yaml.safe_load((artifact / "app.yaml").read_text(encoding="utf-8"))
    command = " ".join(config["command"])

    assert "apps/streamlit_chat_ui/app.py" in command
    assert (artifact / "apps" / "streamlit_chat_ui" / "app.py").is_file()
    assert "DATABRICKS_APP_PORT" in command
    assert {"name": "LAKEBASE_ENDPOINT", "valueFrom": "conversation-store"} in config[
        "env"
    ]
    _assert_module_resolves("streamlit_chat_ui", "apps.streamlit_chat_ui.app")
    _assert_streamlit_entrypoint_imports_from_script_directory()


def test_python_artifacts_have_component_owned_runtime_dependencies() -> None:
    for app in ("mcp_facade", "streamlit_chat_ui"):
        requirements = BUILD_ROOT / app / "requirements.txt"
        active_lines = [
            line.strip()
            for line in requirements.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        assert active_lines, f"{app} has no runtime dependencies"

    agent = BUILD_ROOT / "agent_app"
    assert not (agent / "requirements.txt").exists()
    assert (
        agent / "ecommerce_agent" / "apps" / "agent_app" / "requirements.txt"
    ).is_file()
    assert (agent / "pyproject.toml").is_file()
    assert (agent / "uv.lock").is_file()
    assert not (REPO_ROOT / "ecommerce_agent" / "requirements.txt").exists()


def test_artifacts_exclude_local_caches_tests_and_dependencies() -> None:
    banned_names = {
        ".databricks",
        ".env",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
        "playwright-report",
        "test-results",
        "tests",
    }
    offenders = [
        path.relative_to(BUILD_ROOT).as_posix()
        for path in BUILD_ROOT.rglob("*")
        if path.name in banned_names or path.suffix in {".pyc", ".pyo"}
    ]
    assert offenders == []


def test_bundle_explicitly_includes_gitignored_build_artifacts() -> None:
    bundle = yaml.safe_load((REPO_ROOT / "databricks.yml").read_text(encoding="utf-8"))
    includes = bundle.get("sync", {}).get("include", [])
    assert ".build/apps/**" in includes


def test_missing_source_fails_the_build(tmp_path, monkeypatch) -> None:
    build_apps = _load_build_module()
    monkeypatch.setattr(build_apps, "ROOT", tmp_path)
    monkeypatch.setattr(build_apps, "BUILD", tmp_path / ".build" / "apps")

    assert not build_apps.build_app(
        "broken",
        {
            "copy": ["missing-source"],
            "app_yaml": "missing-app.yaml",
            "requirements": None,
        },
    )

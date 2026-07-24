"""S5-03 — Target-layout contract tests.

These are *failing-first* tests: they describe the required end state of
Sprint 5, so many will FAIL now (before the moves) and only PASS after
the corresponding source relocation is complete.

The test functions use markers in their names to indicate when they are
expected to start passing:

  _post_move  — should pass only after the mechanical moves (S5-05…S5-08)
  _pre_move   — should pass both before and after (invariants)
  _post_clean — should pass only after legacy paths are removed
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
ECOMMERCE_AGENT = REPO_ROOT / "ecommerce_agent"
APPS_DIR = ECOMMERCE_AGENT / "apps"


def _read_databricks_yml() -> dict:
    """Parse databricks.yml at the repo root."""
    path = REPO_ROOT / "databricks.yml"
    if not path.exists():
        pytest.skip("databricks.yml not found")
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Pre-move invariants — must pass before AND after the relocation
# ---------------------------------------------------------------------------
class TestPreMoveInvariants:
    """Tests that verify the CURRENT layout is intact (baseline checks)."""

    def test_agent_core_package_exists(self):
        """agent_core/ remains use-case-independent throughout."""
        assert (REPO_ROOT / "agent_core" / "__init__.py").is_file()

    def test_conversation_package_exists(self):
        """ecommerce_agent/conversation/ is the canonical persistence layer."""
        assert (ECOMMERCE_AGENT / "conversation" / "__init__.py").is_file()

    def test_databricks_yml_has_three_apps(self):
        """The bundle declares exactly three App resources."""
        bundle = _read_databricks_yml()
        apps = bundle.get("resources", {}).get("apps", {})
        assert len(apps) == 3, (
            f"Expected exactly 3 App resources, found {len(apps)}: {list(apps.keys())}"
        )

    def test_databricks_yml_app_names(self):
        """Verify the three canonical App resource keys exist."""
        bundle = _read_databricks_yml()
        apps = bundle.get("resources", {}).get("apps", {})
        expected = {
            "ecommerce_agent",
            "ecommerce_agent_chat_ui",
            "ecommerce_agent_mcp_facade",
        }
        actual = set(apps.keys())
        missing = expected - actual
        assert not missing, f"Missing App resources: {missing}"

    def test_required_app_resource_keys(self):
        """Each App resource uses the canonical public name."""
        bundle = _read_databricks_yml()
        apps = bundle.get("resources", {}).get("apps", {})

        agent = apps.get("ecommerce_agent", {})
        assert agent.get("name") == "${var.app_name}"

        chat_ui = apps.get("ecommerce_agent_chat_ui", {})
        assert chat_ui.get("name") == "ecommerce-agent-chat-ui"

        mcp = apps.get("ecommerce_agent_mcp_facade", {})
        assert mcp.get("name") == "ecommerce-agent-mcp-facade"


# ---------------------------------------------------------------------------
# Source-path default tests
# ---------------------------------------------------------------------------
class TestSourcePathDefaults:
    """Verify Chat UI source defaults to React per the Sprint 5 plan."""

    def test_chat_ui_source_default_is_react(self):
        """The default Chat UI source_code_path points to the React build artifact."""
        bundle = _read_databricks_yml()
        apps = bundle.get("resources", {}).get("apps", {})
        chat_ui = apps.get("ecommerce_agent_chat_ui", {})
        source = chat_ui.get("source_code_path", "")
        assert "chat_ui" in source and "streamlit" not in source, (
            f"Default source should reference chat_ui (not streamlit), got '{source}'"
        )

    def test_chat_ui_is_not_streamlit_by_default(self):
        """The default source_code_path must NOT point to streamlit_chat_ui."""
        bundle = _read_databricks_yml()
        apps = bundle.get("resources", {}).get("apps", {})
        chat_ui = apps.get("ecommerce_agent_chat_ui", {})
        source = chat_ui.get("source_code_path", "")
        assert "streamlit" not in source.lower(), (
            f"Default Chat UI source must not be Streamlit, got '{source}'"
        )


# ---------------------------------------------------------------------------
# Target-layout existence tests — FAIL now, PASS after moves
# ---------------------------------------------------------------------------
class TestTargetLayoutExistence:
    """Tests that verify the target directory structure after moves."""

    def test_apps_agent_app_exists_post_move(self):
        """ecommerce_agent/apps/agent_app/server.py exists after S5-05."""
        assert (APPS_DIR / "agent_app" / "server.py").is_file()

    def test_apps_mcp_facade_exists_post_move(self):
        """ecommerce_agent/apps/mcp_facade/server.py exists after S5-06."""
        assert (APPS_DIR / "mcp_facade" / "server.py").is_file()

    def test_apps_chat_ui_exists_post_move(self):
        """ecommerce_agent/apps/chat_ui/package.json exists after S5-07."""
        assert (APPS_DIR / "chat_ui" / "package.json").is_file()

    def test_apps_streamlit_chat_ui_exists_post_move(self):
        """ecommerce_agent/apps/streamlit_chat_ui/ exists after S5-08."""
        assert (APPS_DIR / "streamlit_chat_ui").is_dir()

    def test_apps_package_marker_exists_post_move(self):
        """ecommerce_agent/apps/__init__.py exists (package boundary)."""
        # S5-04 creates this — may pass now if already created
        apps_init = APPS_DIR / "__init__.py"
        if not apps_init.exists():
            pytest.xfail("apps/__init__.py not yet created (S5-04 pending)")
        assert apps_init.is_file()


# ---------------------------------------------------------------------------
# Legacy-path ABSENCE tests — PASS now (legacy paths still exist),
# expected to PASS after cleanup, FAIL if cleanup incomplete
# ---------------------------------------------------------------------------
class TestLegacyPathAbsence:
    """Tests that legacy paths are removed after the moves complete.

    These use xfail because legacy paths CURRENTLY exist — they should
    be gone only after the final cleanup (S5-11).
    """

    def test_no_legacy_agent_app_post_move(self):
        """ecommerce_agent/agent_app/ must NOT exist after S5-05."""
        legacy = ECOMMERCE_AGENT / "agent_app"
        assert not legacy.exists(), (
            f"Legacy path {legacy} still exists after Agent move"
        )

    def test_no_legacy_mcp_server_post_move(self):
        """ecommerce_agent/apps/mcp_server/ must NOT exist after S5-06."""
        legacy = ECOMMERCE_AGENT / "apps" / "mcp_server"
        assert not legacy.exists(), (
            f"Legacy path {legacy} still exists after MCP rename"
        )

    def test_no_root_chat_ui_source_post_move(self):
        """Chat UI source_code_path uses the chat_ui_source variable."""
        bundle = _read_databricks_yml()
        apps = bundle.get("resources", {}).get("apps", {})
        chat_ui = apps.get("ecommerce_agent_chat_ui", {})
        source = chat_ui.get("source_code_path", "")
        # Must use the parameterized variable — not a hardcoded legacy path
        assert "chat_ui_source" in source, (
            f"source_code_path should use var.chat_ui_source, got '{source}'"
        )
        # Variable default must point to the build artifact
        variables = bundle.get("variables", {})
        cs_var = variables.get("chat_ui_source", {})
        default = cs_var.get("default", "")
        assert ".build" in default, (
            f"chat_ui_source default should use .build/, got '{default}'"
        )


# ---------------------------------------------------------------------------
# Streamlit override configuration tests
# ---------------------------------------------------------------------------
class TestStreamlitOverride:
    """Verify the Streamlit demo override configuration."""

    def test_streamlit_build_artifact_exists(self):
        """Streamlit build artifact has app.yaml at root."""
        path = REPO_ROOT / ".build" / "apps" / "streamlit_chat_ui" / "app.yaml"
        if not path.exists():
            pytest.skip("Run scripts/build_apps.py first")
        assert path.is_file()

    def test_streamlit_entry_point_exists(self):
        """apps/streamlit_chat_ui/app.py is the Streamlit demo entry point (source)."""
        path = APPS_DIR / "streamlit_chat_ui" / "app.py"
        assert path.is_file()

    def test_streamlit_build_has_conversation(self):
        """Streamlit build artifact includes conversation/ package."""
        path = REPO_ROOT / ".build" / "apps" / "streamlit_chat_ui" / "conversation" / "__init__.py"
        if not path.exists():
            pytest.skip("Run scripts/build_apps.py first")
        assert path.is_file()


# ---------------------------------------------------------------------------
# Module importability tests — FAIL now, PASS after moves
# ---------------------------------------------------------------------------
class TestModuleImportability:
    """Verify key modules are importable from their target locations."""

    def test_import_agent_server_from_target(self):
        """Can import from ecommerce_agent.apps.agent_app.server."""
        import importlib

        try:
            importlib.import_module("ecommerce_agent.apps.agent_app.server")
        except ImportError as exc:
            pytest.fail(f"Import failed: {exc}")

    def test_import_mcp_facade_from_build_artifact(self):
        """MCP facade imports resolve from the flat build artifact root.

        The deployment flattens .build/apps/mcp_facade/ to the runtime root,
        so imports must be local (``from app_oauth import ...``).
        """
        import importlib
        import sys

        build_root = str(REPO_ROOT / ".build" / "apps" / "mcp_facade")
        if build_root not in sys.path:
            sys.path.insert(0, build_root)
        try:
            importlib.import_module("server")
        except ImportError as exc:
            pytest.fail(
                f"MCP import failed from build artifact ({build_root}): {exc}"
            )
        finally:
            if sys.path[0] == build_root:
                sys.path.pop(0)

    def test_import_conversation_still_works(self):
        """Canonical conversation package is importable (should always pass)."""
        import importlib

        try:
            importlib.import_module("ecommerce_agent.conversation")
        except ImportError as exc:
            pytest.fail(f"Conversation import failed: {exc}")


# ---------------------------------------------------------------------------
# Integration: existing tests still pass against old layout
# ---------------------------------------------------------------------------
class TestCurrentLayoutStillFunctional:
    """Smoke test: the pre-move codebase still passes basic checks."""

    def test_streamlit_imports_from_build_artifact(self):
        """Streamlit imports resolve from the build artifact source root.

        Databricks flattens .build/apps/streamlit_chat_ui/ to the runtime
        root, so imports must use flat paths
        (``apps.streamlit_chat_ui...``, ``conversation...``).
        """
        import importlib
        import sys

        build_root = str(REPO_ROOT / ".build" / "apps" / "streamlit_chat_ui")
        if build_root not in sys.path:
            sys.path.insert(0, build_root)
        try:
            importlib.import_module("apps.streamlit_chat_ui.app")
        except ImportError as exc:
            pytest.fail(
                f"Streamlit import failed from build artifact "
                f"({build_root}): {exc}"
            )
        finally:
            if sys.path[0] == build_root:
                sys.path.pop(0)

    def test_mcp_facade_imports_from_build_artifact(self):
        """MCP facade imports resolve from the flat build artifact root."""
        import importlib
        import sys

        build_root = str(REPO_ROOT / ".build" / "apps" / "mcp_facade")
        if build_root not in sys.path:
            sys.path.insert(0, build_root)
        try:
            importlib.import_module("server")
        except ImportError as exc:
            pytest.fail(
                f"MCP import failed from build artifact "
                f"({build_root}): {exc}"
            )
        finally:
            if sys.path[0] == build_root:
                sys.path.pop(0)

    def test_agent_core_compiles(self):
        """All Python source in agent_core/ compiles."""
        import compileall

        result = compileall.compile_dir(
            str(REPO_ROOT / "agent_core"),
            force=True,
            quiet=1,
        )
        assert result, "agent_core/ compilation failed"

    def test_ecommerce_agent_compiles(self):
        """All Python source in ecommerce_agent/ compiles."""
        import compileall

        result = compileall.compile_dir(
            str(ECOMMERCE_AGENT),
            force=True,
            quiet=1,
        )
        assert result, "ecommerce_agent/ compilation failed"

    def test_no_duplicate_conversation_package(self):
        """conversation/ only exists once under ecommerce_agent/ (not in apps/)."""
        conversation_dirs = list(ECOMMERCE_AGENT.rglob("conversation/__init__.py"))
        # There should be exactly one conversation package
        assert len(conversation_dirs) == 1, (
            f"Expected 1 conversation package, found {len(conversation_dirs)}: "
            f"{[str(d) for d in conversation_dirs]}"
        )
        assert (
            str(conversation_dirs[0])
            .replace("\\", "/")
            .endswith("ecommerce_agent/conversation/__init__.py")
        )

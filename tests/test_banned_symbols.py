"""
Banned-legacy-symbol repository check (Sprint 1 task A4).

Ensures that no production source file contains banned legacy imports,
paths, or commands that the Sprint 1 non-legacy guardrails explicitly
forbid.
"""

import ast
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BANNED_PATTERNS: list[tuple[str, str]] = [
    # Legacy deployment path
    (r"databricks\.agents\.deploy", "Legacy Model Serving agent deployment"),
    # Direct DeepSeek provider initialization
    (r"ChatDeepSeek", "Direct DeepSeek chat model import not allowed in production"),
    (
        r"init_chat_model\(.*provider.*deepseek",
        "Provider-specific init_chat_model with DeepSeek not allowed",
    ),
    # LangChain legacy agent constructors
    (
        r"from langchain\.agents import AgentExecutor",
        "Use create_agent, not AgentExecutor",
    ),
    (
        r"from langchain\.agents import create_tool_calling_agent",
        "Use create_agent, not create_tool_calling_agent",
    ),
    (
        r"from langgraph\.prebuilt import create_react_agent",
        "Use create_agent, not create_react_agent",
    ),
    # Internal uc_ai module
    (r"databricks_langchain\.uc_ai", "Do not import uc_ai internal module"),
    # Legacy project path
    (r"projects\.ecommerce_support", "Legacy projects.ecommerce_support path"),
    # DBFS paths
    (r"/dbfs/", "DBFS paths are not allowed for rules/skills/config"),
    (r"dbfs:", "DBFS paths are not allowed"),
    # Legacy agent API
    (r"from databricks\.agents import", "databricks.agents is legacy for new agents"),
]

# Files to exempt from the check (test files, experiments, legacy notebooks kept for reference)
EXEMPT_DIRS = {
    ".venv",
    "__pycache__",
    ".git",
    ".agents",
    "experiments",
    "deepseek_adapter",
}
EXEMPT_FILES = {
    "tests/experiments/test_deepseek_serving_notebook.py",
    # This test file itself contains banned pattern strings in test parametrize.
    "tests/test_banned_symbols.py",
}


def _is_exempt(filepath: Path) -> bool:
    rel = filepath.relative_to(PROJECT_ROOT).as_posix()
    if rel in EXEMPT_FILES:
        return True
    for part in filepath.parts:
        if part in EXEMPT_DIRS:
            return True
    return False


def _get_python_files() -> list[Path]:
    files = []
    for path in PROJECT_ROOT.rglob("*.py"):
        if not _is_exempt(path):
            files.append(path)
    return sorted(files)


class TestBannedSymbols:
    """Check that no production source file contains banned legacy patterns."""

    @pytest.mark.parametrize("pattern,reason", BANNED_PATTERNS)
    def test_no_banned_patterns_in_source(self, pattern: str, reason: str):
        """Verify banned regex patterns are absent from all production Python files."""
        files = _get_python_files()
        violations = []
        for fpath in files:
            try:
                content = fpath.read_text(encoding="utf-8")
            except Exception:
                continue
            for match in re.finditer(pattern, content):
                lineno = content[: match.start()].count("\n") + 1
                violations.append(f"  {fpath.relative_to(PROJECT_ROOT)}:{lineno}")
        assert not violations, (
            f"Banned pattern found: {pattern!r} ({reason})\n" + "\n".join(violations)
        )

    def test_no_import_of_projects_ecommerce_support(self):
        """Verify ast-level check that no production file imports projects.ecommerce_support."""
        files = _get_python_files()
        violations = []
        for fpath in files:
            try:
                tree = ast.parse(fpath.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "projects.ecommerce_support" in alias.name:
                            violations.append(str(fpath.relative_to(PROJECT_ROOT)))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and "projects.ecommerce_support" in node.module:
                        violations.append(str(fpath.relative_to(PROJECT_ROOT)))
        assert not violations, (
            "Files still import projects.ecommerce_support:\n" + "\n".join(violations)
        )

    def test_no_chatdeepseek_import(self):
        """Verify no production file imports ChatDeepSeek."""
        files = _get_python_files()
        violations = []
        for fpath in files:
            try:
                tree = ast.parse(fpath.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "ChatDeepSeek" in alias.name:
                            violations.append(str(fpath.relative_to(PROJECT_ROOT)))
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if "ChatDeepSeek" in alias.name:
                            violations.append(str(fpath.relative_to(PROJECT_ROOT)))
        assert not violations, "Files still import ChatDeepSeek:\n" + "\n".join(
            violations
        )

    def test_no_experiments_import_in_production(self):
        """Verify no production file imports from experiments/."""
        files = _get_python_files()
        violations = []
        for fpath in files:
            try:
                content = fpath.read_text(encoding="utf-8")
            except Exception:
                continue
            # Check for actual import statements, not just string matches
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith(("from experiments", "import experiments")):
                    violations.append(
                        f"{fpath.relative_to(PROJECT_ROOT)}:{content[: content.index(line)].count(chr(10)) + 1}"
                    )
        assert not violations, "Files still import from experiments/:\n" + "\n".join(
            violations
        )

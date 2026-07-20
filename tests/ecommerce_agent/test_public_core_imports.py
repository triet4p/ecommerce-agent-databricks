"""Concrete use case code depends on the published agent_core surface only."""

from pathlib import Path


def test_ecommerce_agent_has_no_private_agent_core_imports():
    root = Path(__file__).parents[2] / "ecommerce_agent"
    violations = []
    for source in root.rglob("*.py"):
        for line_number, line in enumerate(
            source.read_text(encoding="utf-8").splitlines(), 1
        ):
            if line.strip().startswith(("from agent_core.", "import agent_core.")):
                violations.append(f"{source.relative_to(root)}:{line_number}")
    assert not violations, "Private agent_core imports:\n" + "\n".join(violations)

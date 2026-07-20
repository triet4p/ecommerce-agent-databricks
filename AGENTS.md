# Repository Guidelines

## Project Structure & Module Organization

- `agent_core/` contains reusable orchestration, configuration schemas, prompt resolution, retrieval, and tool/skill interfaces. Keep this package independent of any specific commerce use case.
- `ecommerce_agent/` is the concrete implementation: configuration, agent assembly, tools, rules, skills, evaluation notes, and Databricks App entry points.
- `data-processing/` contains Databricks notebook-style ingestion and transformation scripts.
- `.agents/` stores contributor rules, reusable skills, and project memory. Consult it before changing conventions or architecture.

There is currently no checked-in `tests/` directory or static asset tree. Add tests under `tests/`, mirroring package paths (for example, `tests/agent_core/test_config_schema.py`).

## Build, Test, and Development Commands

Use `uv`; do not manage the root environment with `pip`, Poetry, or Conda.

- `uv sync --all-groups` installs locked runtime and data-processing dependencies.
- `uv run python -m compileall agent_core ecommerce_agent data-processing` performs a fast syntax check.
- `uv run pytest -v` runs the test suite once tests and the `pytest` development dependency are present.
- `uvx ruff check .` checks Python style; `uvx ruff format --check .` verifies formatting without rewriting files.

Databricks-facing modules require workspace authentication and configured resources; do not treat a successful import as an integration test.

## Coding Style & Naming Conventions

Target Python 3.13 and use four-space indentation. Follow standard Python naming: `snake_case` for modules and functions, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants. Fully annotate function signatures and use Pydantic v2 for configuration models. Keep core abstractions in `agent_core/`; use-case imports belong in `ecommerce_agent/`. Format with Ruff and keep Markdown concise.

## Testing Guidelines

Use `pytest`; name files `test_<module>.py` and tests `test_<behavior>`. Cover schema validation and orchestration logic with unit tests. Mark or isolate tests requiring Databricks credentials, endpoints, Unity Catalog, or network access. No coverage threshold is configured, so prioritize meaningful coverage of changed behavior.

## Commit & Pull Request Guidelines

History follows Conventional Commits, such as `feat(core): implement core agent logic`. Use `<type>(<scope>): <imperative summary>`, with focused commits. Pull requests should explain intent, list verification commands, link relevant issues, and call out configuration or deployment impacts. Include screenshots only for UI changes.

## Security & Agent Notes

Never commit Databricks tokens, `.env` files, customer data, or generated credentials. Keep deploy-specific values configurable. Record durable technical decisions and resolved environment quirks in `.agents/memory/decisions.md` and `.agents/memory/lessons-learned.md`, respectively.

## Databricks Workspace Autonomy

Before Databricks work, read `.agents/rules/databricks.md` and use the
`databricks-workspace-operator` skill. The repository owner has granted standing
authorization for coding agents to inspect, create, update, deploy, grant, run,
and verify project-scoped Databricks resources required by the active Sprint
Plan without requesting confirmation for each routine operation. Preserve the
canonical `ecommerce_agent` catalog, never expose secrets, and do not mutate or
delete unrelated resources.

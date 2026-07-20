"""
agent_core.config_loader
--------------------------
Central configuration loading with working-directory-independent path resolution.

Usage::

    config = load_config("path/to/config.yaml")
    # config.rules.paths are now absolute, resolved against config.yaml's directory.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from agent_core.config_schema import AgentConfig


def load_config(path: str | Path) -> AgentConfig:
    """Load, validate, and resolve a YAML config file.

    The config file's parent directory is recorded and used to resolve
    all relative paths in ``rules.paths``, ``skills.source_dir``, etc.
    This makes the agent work correctly regardless of the current working
    directory.

    Returns:
        An ``AgentConfig`` with all relative paths resolved to absolute paths.
    """
    path = Path(path).resolve()
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    config = AgentConfig.model_validate(raw)

    return resolve_config_paths(config, config_dir=path.parent)


def resolve_config_paths(
    config: AgentConfig,
    config_dir: Path | None = None,
) -> AgentConfig:
    """Resolve relative paths in config against the config file directory.

    If ``config_dir`` is None, uses the current working directory.
    """
    if config_dir is None:
        config_dir = Path.cwd()

    # ---- Resolve rules paths ----
    if config.rules and config.rules.paths:
        config.rules.paths = resolve_paths_list(config.rules.paths, config_dir)

    # ---- Resolve skills source dir ----
    if config.skills and config.skills.source_dir:
        sd = Path(config.skills.source_dir)
        if not sd.is_absolute():
            sd = config_dir / sd
        config.skills.source_dir = str(sd.resolve())

    return config


def resolve_paths_list(
    paths: list[str],
    config_dir: Path | None = None,
) -> list[str]:
    """Resolve a list of paths against a base directory.

    Args:
        paths: List of relative or absolute paths.
        config_dir: Base directory for relative paths. Defaults to CWD.

    Returns:
        List of resolved absolute paths.
    """
    if config_dir is None:
        config_dir = Path.cwd()
    resolved = []
    for p in paths:
        rp = Path(p)
        if not rp.is_absolute():
            rp = config_dir / rp
        resolved.append(str(rp.resolve()))
    return resolved


def resolve_paths(
    paths: list[str],
    config: AgentConfig,
) -> list[str]:
    """Resolve a list of paths against config.

    Convenience wrapper that uses the config's stored config_dir if available
    (via resolve_config_paths), falling back to CWD.

    Note: This variant preserves backward compatibility. Prefer
    ``resolve_paths_list(paths, config_dir)`` for standalone use.
    """
    # The config has already been through resolve_config_paths if loaded
    # via load_config(), so relative paths are already resolved.
    # For paths that need resolution, use CWD as fallback.
    return resolve_paths_list(paths)

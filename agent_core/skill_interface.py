"""
agent_core.skill_interface
-----------------------------
Two independent mechanisms, analogous to Claude Code's approach:

- **Rules**: always loaded into the system prompt at build time (``render_rules``).
  Used for mandatory, short instructions — small enough that the token cost
  is paid once per request.

- **Skills**: progressive disclosure. The agent only sees name + short description
  via the ``list_skills()`` tool; full content is loaded only when the agent
  explicitly calls ``load_skill(name)``. This keeps the system prompt small
  regardless of the library size.

Both load from the application source tree by default (``ecommerce_agent/skills/``
for skills, ``ecommerce_agent/rules/`` for rules). A Unity Catalog Volume can
be configured as an opt-in provider for an independent content-publishing lifecycle.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Sequence

import yaml
from langchain_core.tools import tool

from agent_core.config_schema import SkillsConfig, SkillMeta

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a skill .md file.

    Returns:
        (meta_dict, body_text)

    Raises:
        ValueError: If the file does not contain valid frontmatter.
    """
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        raise ValueError(
            "Skill file missing YAML frontmatter (expected ---\\nname: ...\\n---)"
        )
    meta = yaml.safe_load(match.group(1))
    if not isinstance(meta, dict):
        raise ValueError("Skill frontmatter must be a YAML mapping")
    body = match.group(2).strip()
    return meta, body


def _validate_skill_meta(meta: dict, path: Path) -> None:
    """Validate that a skill's frontmatter has the required fields."""
    if "name" not in meta or not isinstance(meta["name"], str):
        raise ValueError(
            f"Skill at {path} is missing required string field 'name' in frontmatter"
        )
    if "description" not in meta or not isinstance(meta["description"], str):
        raise ValueError(
            f"Skill at {path} is missing required string field 'description' in frontmatter"
        )


class SkillLibrary:
    """Loads skill ``.md`` files from a directory.

    One file = one skill. The index is built lazily and cached — it only
    reads directory entries and frontmatter (not full content) when building
    the index. Full content is loaded on demand via ``load_skill(name)``.

    Args:
        config: ``SkillsConfig`` with the ``source_dir`` (or optional
            ``volume_path``) pointing to the directory containing skill files.
    """

    def __init__(self, config: SkillsConfig):
        self._source_dir = Path(config.source_dir)
        self._index: dict[str, SkillMeta] | None = None

    def _list_files(self) -> list[Path]:
        """Return skill .md files sorted for deterministic ordering."""
        if not self._source_dir.is_dir():
            logger.warning("Skill directory '%s' does not exist", self._source_dir)
            return []
        files = sorted(self._source_dir.glob("*.md"))
        return files

    def _build_index(self) -> dict[str, SkillMeta]:
        """Build a name -> SkillMeta index from all .md files."""
        index: dict[str, SkillMeta] = {}
        for fpath in self._list_files():
            raw = fpath.read_text(encoding="utf-8")
            try:
                meta, _ = _parse_frontmatter(raw)
                _validate_skill_meta(meta, fpath)
            except ValueError as e:
                logger.warning("Skipping skill file %s: %s", fpath, e)
                continue

            skill_name = meta["name"]
            if skill_name in index:
                logger.warning(
                    "Duplicate skill name '%s' in files %s and %s; keeping first",
                    skill_name,
                    index[skill_name].path,
                    str(fpath),
                )
                continue
            index[skill_name] = SkillMeta(
                name=skill_name,
                description=meta["description"],
                path=str(fpath),
            )
        return index

    @property
    def index(self) -> dict[str, SkillMeta]:
        if self._index is None:
            self._index = self._build_index()
        return self._index

    def list_skills(self) -> list[dict]:
        """Return name + description for every skill."""
        return [
            {"name": s.name, "description": s.description} for s in self.index.values()
        ]

    def load_skill(self, name: str) -> str:
        """Load the full body content of a skill by name.

        Raises:
            ValueError: If the skill name is not found.
        """
        meta = self.index.get(name)
        if meta is None:
            available = ", ".join(self.index.keys())
            raise ValueError(
                f"Unknown skill '{name}'. Available skills: {available or '(none)'}"
            )
        raw = Path(meta.path).read_text(encoding="utf-8")
        _, body = _parse_frontmatter(raw)
        return body


def build_skill_tools(library: SkillLibrary) -> list:
    """Create the two progressive-disclosure skill tools.

    Returns:
        ``[list_skills, load_skill]`` — the exact lifecycle: list first,
        then load.
    """

    @tool
    def list_skills() -> str:
        """List all available skills with their names and short descriptions.
        Call this tool first to know which skills are available before loading one."""
        items = library.list_skills()
        if not items:
            return "No skills available."
        return "\n".join(f"- {s['name']}: {s['description']}" for s in items)

    @tool
    def load_skill(name: str) -> str:
        """Load the full content of a skill by name (get the name from list_skills())."""
        return library.load_skill(name)

    return [list_skills, load_skill]


def render_rules(paths: Sequence[str]) -> str:
    """Render all rules into a single string for inclusion in the system prompt.

    Args:
        paths: Absolute paths to rule ``.md`` files.

    Returns:
        Concatenated rule content, separated by double newlines.
    """
    parts = []
    for str_path in paths:
        p = Path(str_path)
        if not p.is_file():
            logger.warning("Rule file '%s' not found; skipping", p)
            continue
        parts.append(p.read_text(encoding="utf-8").strip())
    return "\n\n".join(parts)

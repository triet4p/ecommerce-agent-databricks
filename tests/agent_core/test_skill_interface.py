"""
Tests for skill interface (Sprint 1 tasks D3, D4).

Verifies:
- Rule rendering with valid/missing paths
- SkillLibrary with source directory
- Empty libraries
- Duplicate skill names
- Malformed frontmatter
- Unknown skill names
"""

import tempfile
from pathlib import Path

import pytest

from agent_core.skill_interface import (
    SkillLibrary,
    build_skill_tools,
    render_rules,
    _parse_frontmatter,
)
from agent_core.config_schema import SkillsConfig


@pytest.fixture
def temp_skills_dir():
    """Create a temporary directory with sample skill files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)

        # Valid skill
        skill1 = d / "skill-one.md"
        skill1.write_text(
            "---\nname: skill_one\ndescription: First test skill\n---\n\n# Skill One\n\nContent here."
        )

        # Another valid skill
        skill2 = d / "skill-two.md"
        skill2.write_text(
            "---\nname: skill_two\ndescription: Second test skill\n---\n\n# Skill Two\n\nMore content."
        )

        yield d


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        raw = "---\nname: test\ndescription: A test\n---\nBody content here"
        meta, body = _parse_frontmatter(raw)
        assert meta["name"] == "test"
        assert body == "Body content here"

    def test_missing_frontmatter_fails(self):
        raw = "Just body text without frontmatter"
        with pytest.raises(ValueError, match="missing YAML frontmatter"):
            _parse_frontmatter(raw)

    def test_empty_string_fails(self):
        with pytest.raises(ValueError, match="missing YAML frontmatter"):
            _parse_frontmatter("")

    def test_multiline_body(self):
        raw = "---\nname: test\ndescription: desc\n---\nLine 1\nLine 2\nLine 3"
        _, body = _parse_frontmatter(raw)
        assert "Line 1" in body
        assert "Line 3" in body


class TestRenderRules:
    def test_render_single_rule(self, tmp_path):
        rule_file = tmp_path / "rule.md"
        rule_file.write_text("## Rule one\n\nBe concise.")
        result = render_rules([str(rule_file)])
        assert "Rule one" in result
        assert "Be concise" in result

    def test_render_multiple_rules(self, tmp_path):
        r1 = tmp_path / "rule1.md"
        r1.write_text("Rule A")
        r2 = tmp_path / "rule2.md"
        r2.write_text("Rule B")
        result = render_rules([str(r1), str(r2)])
        assert "Rule A" in result
        assert "Rule B" in result

    def test_missing_rule_is_skipped(self):
        result = render_rules(["/nonexistent/rule.md"])
        assert result == ""

    def test_empty_paths_list(self):
        result = render_rules([])
        assert result == ""


class TestSkillLibrary:
    def test_list_skills(self, temp_skills_dir):
        config = SkillsConfig(source_dir=str(temp_skills_dir))
        lib = SkillLibrary(config)
        skills = lib.list_skills()
        names = {s["name"] for s in skills}
        assert "skill_one" in names
        assert "skill_two" in names

    def test_load_skill(self, temp_skills_dir):
        config = SkillsConfig(source_dir=str(temp_skills_dir))
        lib = SkillLibrary(config)
        body = lib.load_skill("skill_one")
        assert "Skill One" in body
        assert "Content here" in body

    def test_unknown_skill_raises(self, temp_skills_dir):
        config = SkillsConfig(source_dir=str(temp_skills_dir))
        lib = SkillLibrary(config)
        with pytest.raises(ValueError, match="Unknown skill"):
            lib.load_skill("nonexistent_skill")

    def test_empty_directory(self, tmp_path):
        config = SkillsConfig(source_dir=str(tmp_path))
        lib = SkillLibrary(config)
        assert lib.list_skills() == []

    def test_duplicate_skill_name(self, temp_skills_dir):
        """When two files have the same frontmatter name, the first one (alphabetically) wins."""
        dup_file = temp_skills_dir / "skill-one-dup.md"
        dup_file.write_text(
            "---\nname: skill_one\ndescription: Duplicate\n---\nDuplicate content"
        )
        config = SkillsConfig(source_dir=str(temp_skills_dir))
        lib = SkillLibrary(config)
        # The first file alphabetically is 'skill-one-dup.md' -> 'Duplicate content'
        body = lib.load_skill("skill_one")
        assert "Duplicate content" in body

    def test_malformed_frontmatter_skipped(self, temp_skills_dir):
        bad_file = temp_skills_dir / "bad-skill.md"
        bad_file.write_text("No frontmatter here")
        config = SkillsConfig(source_dir=str(temp_skills_dir))
        lib = SkillLibrary(config)
        # Should not raise; bad file is skipped and logged
        skills = lib.list_skills()
        names = {s["name"] for s in skills}
        assert "skill_one" in names  # valid files still present

    def test_deterministic_ordering(self, temp_skills_dir):
        config = SkillsConfig(source_dir=str(temp_skills_dir))
        lib1 = SkillLibrary(config)
        lib2 = SkillLibrary(config)
        assert lib1.list_skills() == lib2.list_skills()


class TestPathTraversal:
    """Test that SkillLibrary rejects path traversal attempts (Sprint 1 D4)."""

    def test_skill_name_with_path_traversal_raises(self, temp_skills_dir):
        """Path traversal in skill load_skill() should not read outside the skill directory."""
        config = SkillsConfig(source_dir=str(temp_skills_dir))
        lib = SkillLibrary(config)
        with pytest.raises(ValueError, match="Unknown skill"):
            lib.load_skill("../../etc/passwd")

    def test_skill_name_with_slash_raises(self, temp_skills_dir):
        """Skill name with a / should not resolve to a file path."""
        config = SkillsConfig(source_dir=str(temp_skills_dir))
        lib = SkillLibrary(config)
        skills_before = lib.list_skills()
        with pytest.raises(ValueError, match="Unknown skill"):
            lib.load_skill("../skill_one")
        # Library should be unchanged
        assert lib.list_skills() == skills_before


class TestBuildSkillTools:
    def test_list_and_load_tools(self, temp_skills_dir):
        config = SkillsConfig(source_dir=str(temp_skills_dir))
        lib = SkillLibrary(config)
        tools = build_skill_tools(lib)
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert "list_skills" in names
        assert "load_skill" in names

    def test_list_skills_executes(self, temp_skills_dir):
        config = SkillsConfig(source_dir=str(temp_skills_dir))
        lib = SkillLibrary(config)
        tools = build_skill_tools(lib)
        list_fn = next(t for t in tools if t.name == "list_skills")
        result = list_fn.invoke({})
        assert "skill_one" in result
        assert "skill_two" in result

    def test_load_skill_executes(self, temp_skills_dir):
        config = SkillsConfig(source_dir=str(temp_skills_dir))
        lib = SkillLibrary(config)
        tools = build_skill_tools(lib)
        load_fn = next(t for t in tools if t.name == "load_skill")
        result = load_fn.invoke({"name": "skill_one"})
        assert "Content here" in result

    def test_empty_library_list(self, tmp_path):
        config = SkillsConfig(source_dir=str(tmp_path))
        lib = SkillLibrary(config)
        tools = build_skill_tools(lib)
        list_fn = next(t for t in tools if t.name == "list_skills")
        result = list_fn.invoke({})
        assert result == "No skills available."

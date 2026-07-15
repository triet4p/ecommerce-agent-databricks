"""
agent_core.skill_interface
-----------------------------
Hai cơ chế tách biệt, giống Claude Code:

- **Rules**: luôn nạp vào system prompt, nạp 1 lần lúc build agent (`render_rules`).
  Dùng cho quy tắc bắt buộc, ngắn — đủ nhỏ để lúc nào cũng trả phí token.
- **Skills**: progressive disclosure. Agent chỉ thấy tên + mô tả ngắn qua tool
  `list_skills()`; nội dung đầy đủ chỉ load khi agent chủ động gọi `load_skill(name)`.
  Giữ system prompt gọn dù thư viện skill lớn tới đâu.

Cả hai đọc file `.md` từ UC Volume — không cần thêm Model Serving endpoint (đọc file
tĩnh, không phải semantic search), nên đặt cạnh `retriever_interface.py` trong
agent_core nhưng KHÔNG dùng chung cơ chế với nó.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import yaml
from langchain_core.tools import tool

from agent_core.config_schema import RulesConfig, SkillsConfig, SkillMeta

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        raise ValueError("Skill file thiếu YAML frontmatter (dạng ---\\nname: ...\\n---)")
    meta = yaml.safe_load(match.group(1))
    return meta, match.group(2).strip()


class SkillLibrary:
    """Đọc skill `.md` từ 1 UC Volume. 1 file = 1 skill. Index được build lười (lazy)
    và cache lại — chỉ list_dir + đọc frontmatter (không đọc full content) khi build index."""

    def __init__(self, config: SkillsConfig):
        self._volume_path = config.volume_path.rstrip("/")
        self._index: dict[str, SkillMeta] | None = None

    def _list_files(self) -> list[str]:
        return [f for f in os.listdir(self._volume_path) if f.endswith(".md")]

    def _build_index(self) -> dict[str, SkillMeta]:
        index: dict[str, SkillMeta] = {}
        for fname in self._list_files():
            path = f"{self._volume_path}/{fname}"
            with open(path, encoding="utf-8") as f:
                meta, _ = _parse_frontmatter(f.read())
            index[meta["name"]] = SkillMeta(name=meta["name"], description=meta["description"], path=path)
        return index

    @property
    def index(self) -> dict[str, SkillMeta]:
        if self._index is None:
            self._index = self._build_index()
        return self._index

    def list_skills(self) -> list[dict]:
        return [{"name": s.name, "description": s.description} for s in self.index.values()]

    def load_skill(self, name: str) -> str:
        meta = self.index.get(name)
        if meta is None:
            available = ", ".join(self.index.keys())
            raise ValueError(f"Không tìm thấy skill '{name}'. Skills sẵn có: {available}")
        with open(meta.path, encoding="utf-8") as f:
            _, body = _parse_frontmatter(f.read())
        return body


def build_skill_tools(library: SkillLibrary) -> list:
    """2 tool duy nhất — đúng vòng đời progressive disclosure: list rồi mới load."""

    @tool
    def list_skills() -> str:
        """Liệt kê tất cả skill sẵn có (tên + mô tả ngắn). Luôn gọi tool này trước
        khi cần load 1 skill cụ thể, để biết skill nào phù hợp với tình huống hiện tại."""
        items = library.list_skills()
        if not items:
            return "Không có skill nào."
        return "\n".join(f"- {s['name']}: {s['description']}" for s in items)

    @tool
    def load_skill(name: str) -> str:
        """Load toàn bộ nội dung của 1 skill theo tên (name lấy từ list_skills())."""
        return library.load_skill(name)

    return [list_skills, load_skill]


def render_rules(config: RulesConfig) -> str:
    """Rules luôn nạp — ghép nối 1 lần lúc build agent, KHÔNG phải tool call."""
    parts = []
    for path in config.paths:
        with open(path, encoding="utf-8") as f:
            parts.append(f.read().strip())
    return "\n\n".join(parts)

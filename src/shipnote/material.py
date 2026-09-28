"""Zenn の記事の材料集め: コミット、CHANGELOG、README、人が書いたメモ。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import gh

README_LIMIT = 6000
NOTES_FILE = "shipnote-story.md"  # なぜ作ったか・何に詰まったかを人が書いておく (任意)


@dataclass
class Material:
    tag: str
    prev_tag: str | None
    commits: str
    changelog: str
    readme: str
    notes: str


def tags(repo: Path) -> list[str]:
    """タグを古い順に。"""
    out = gh.git(repo, "tag", "--sort=creatordate")
    return [t for t in out.split() if t]


def changelog_section(repo: Path, tag: str) -> str:
    path = repo / "CHANGELOG.md"
    if not path.exists():
        return ""
    version = tag.lstrip("v")
    out, inside = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = bool(re.match(rf"^##\s+v?{re.escape(version)}\b", line))
            continue
        if inside:
            out.append(line)
    return "\n".join(out).strip()


def collect(repo: Path, tag: str, notes: Path | None = None) -> Material:
    all_tags = tags(repo)
    if tag not in all_tags:
        raise ValueError(f"タグ {tag} がありません (あるもの: {', '.join(all_tags) or 'なし'})")
    i = all_tags.index(tag)
    prev = all_tags[i - 1] if i > 0 else None
    rng = f"{prev}..{tag}" if prev else tag
    commits = gh.git(repo, "log", "--reverse", "--date=short", "--format=%ad %s", rng).strip()
    readme = ""
    for name in ("README.md", "README.ja.md", "readme.md"):
        if (repo / name).exists():
            readme = (repo / name).read_text(encoding="utf-8")[:README_LIMIT]
            break
    notes = notes or (repo / NOTES_FILE)
    note_text = notes.read_text(encoding="utf-8").strip() if notes.exists() else ""
    return Material(tag, prev, commits, changelog_section(repo, tag), readme, note_text)

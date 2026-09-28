"""Release → サイトのリポジトリ (Astro) へのデータ書き出し。

LLM は使わない。Release の本文 (CHANGELOG から人が書いたもの) をそのまま記録にするので、
書いていない機能が紛れ込む余地がない。

書き出すもの:
- ``src/content/projects/<slug>.json`` : LP (/projects/<slug>/) とトップの一覧のデータ
- ``src/content/posts/<slug>-<tag>.md`` : リリース記録 (/posts/<slug>-<tag>/)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import gh
from .config import ProjectConfig

# Release の本文から落とす節。LP に同じ情報があり、記録に毎回並べると読みにくい
DROP_SECTIONS = ("初めての方へ",)
# 見出しが記事のタイトルと重複する節 (本文は残して見出しだけ落とす)
DROP_HEADINGS = re.compile(r"^##\s+\S+\s+の変更点\s*$")


def tag_slug(tag: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")


def post_slug(project: str, tag: str) -> str:
    return f"{project}-{tag_slug(tag)}"


def clean_body(body: str) -> str:
    out: list[str] = []
    skipping = False
    for line in body.split("\n"):
        if line.startswith("## "):
            skipping = any(s in line for s in DROP_SECTIONS)
            if skipping or DROP_HEADINGS.match(line):
                continue
        if not skipping:
            out.append(line)
    text = re.sub(r"<!--.*?-->", "", "\n".join(out), flags=re.S)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def yaml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)  # JSON の文字列は YAML でもそのまま通る


def render_post(proj: ProjectConfig, rel: gh.Release) -> str:
    body = clean_body(rel.body) or "（変更点の記載なし）"
    fm = [
        "---",
        f"title: {yaml_str(rel.name)}",
        f"date: {yaml_str(rel.published_at)}",
        f"project: {yaml_str(proj.slug)}",
        f"projectName: {yaml_str(proj.name)}",
        f"tag: {yaml_str(rel.tag)}",
        f"releaseUrl: {yaml_str(rel.url)}",
        f"prerelease: {'true' if rel.prerelease else 'false'}",
        "generator: shipnote",
        "---",
    ]
    return "\n".join(fm) + "\n\n" + body + "\n"


def render_project(proj: ProjectConfig, repo: Path, info: dict, rels: list[gh.Release]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    branch = (info.get("defaultBranchRef") or {}).get("name") or "main"
    shots = []
    for s in proj.screenshots:
        if not (repo / s).exists():
            warnings.append(f"スクリーンショットが見つかりません: {s}")
        shots.append(f"https://raw.githubusercontent.com/{proj.github}/{branch}/{s.lstrip('/')}")
    latest = next((r for r in rels if not r.prerelease), rels[0] if rels else None)
    data = {
        "name": proj.name,
        "slug": proj.slug,
        "github": proj.github,
        "repoUrl": info.get("url") or f"https://github.com/{proj.github}",
        "tagline": proj.tagline,
        "description": proj.description,
        "features": proj.features,
        "platforms": proj.platforms,
        "screenshots": shots,
        "license": ((info.get("licenseInfo") or {}).get("spdxId") or ""),
        "listed": proj.listed,
        "latest": None if latest is None else {
            "tag": latest.tag,
            "name": latest.name,
            "url": latest.url,
            "date": latest.published_at,
            "assets": [{"name": a.name, "url": a.url, "size": a.size} for a in latest.assets],
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n", warnings


@dataclass
class SyncResult:
    written: list[Path] = field(default_factory=list)
    unchanged: list[Path] = field(default_factory=list)
    removed: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _write(path: Path, text: str, res: SyncResult, dry: bool) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        res.unchanged.append(path)
        return
    res.written.append(path)
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def sync(proj: ProjectConfig, repo: Path, site: Path, dry: bool = False) -> SyncResult:
    res = SyncResult()
    info = gh.repo_info(proj.github)
    if info.get("isPrivate"):
        raise ValueError(f"{proj.github} は非公開です。公開リポジトリだけを載せます")
    rels = gh.releases(proj.github)
    if not rels:
        res.warnings.append("公開済みの Release がありません (LP だけ作ります)")

    text, warns = render_project(proj, repo, info, rels)
    res.warnings += warns
    _write(site / "src/content/projects" / f"{proj.slug}.json", text, res, dry)

    posts_dir = site / "src/content/posts"
    keep = set()
    for rel in rels:
        path = posts_dir / f"{post_slug(proj.slug, rel.tag)}.md"
        keep.add(path.name)
        _write(path, render_post(proj, rel), res, dry)

    # Release を消したら記録も消す (shipnote が作ったものに限る)
    if posts_dir.exists():
        marker = f"project: {yaml_str(proj.slug)}"
        for path in posts_dir.glob(f"{proj.slug}-*.md"):
            head = path.read_text(encoding="utf-8")[:1000]
            if path.name not in keep and "generator: shipnote" in head and marker in head:
                res.removed.append(path)
                if not dry:
                    path.unlink()
    return res

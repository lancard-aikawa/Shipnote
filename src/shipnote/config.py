"""設定の読み込み。

設定は 2 種類ある。

- 全体の設定 ``~/.shipnote/config.toml`` : サイトのリポジトリと Zenn のリポジトリの場所、対象のリポジトリ一覧
- プロジェクトごとの ``shipnote.toml`` : 各リポジトリの直下。LP に出す紹介文と特徴
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_FILE = "shipnote.toml"


def home_dir() -> Path:
    return Path(os.environ.get("SHIPNOTE_HOME") or Path.home() / ".shipnote")


@dataclass
class GlobalConfig:
    site_dir: Path | None = None
    zenn_dir: Path | None = None
    repos: list[Path] = field(default_factory=list)


def load_global() -> GlobalConfig:
    path = home_dir() / "config.toml"
    if not path.exists():
        return GlobalConfig()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    opt = lambda k: Path(data[k]).expanduser() if data.get(k) else None  # noqa: E731
    return GlobalConfig(
        site_dir=opt("site_dir"),
        zenn_dir=opt("zenn_dir"),
        repos=[Path(p).expanduser() for p in data.get("repos", [])],
    )


@dataclass
class ProjectConfig:
    name: str
    slug: str
    github: str  # owner/name
    tagline: str
    description: str
    features: list[str]
    screenshots: list[str]  # リポジトリ内のパス
    platforms: str
    listed: bool
    posts: bool = True  # false なら一覧と LP だけ。リリース記録 (/posts/) は作らない
    claude: bool = False  # Claude Code 前提。「作ったもの」ではなく /claudes/ の一覧に載せる
    links: list[dict[str, str]] = field(default_factory=list)  # LP に並べるリンク [{label, url}]


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "project"


def load_project(repo: Path, github: str) -> ProjectConfig:
    """``shipnote.toml`` を読む。無ければ例外 (init で作ってもらう)。"""
    path = repo / PROJECT_FILE
    if not path.exists():
        raise FileNotFoundError(f"{path} がありません。先に `shipnote init {repo}` で作ってください")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    name = data.get("name") or repo.name
    slug = data.get("slug") or slugify(name)
    if not SLUG_RE.match(slug):
        raise ValueError(f"{path}: slug は英小文字・数字・ハイフンだけにしてください ({slug!r})")
    tagline = str(data.get("tagline", "")).strip()
    links = []
    for ln in data.get("links", []):
        label, url = str(ln.get("label", "")).strip(), str(ln.get("url", "")).strip()
        if not label or not url.startswith("https://"):
            raise ValueError(f"{path}: links は label と https:// の url を書いてください ({ln!r})")
        links.append({"label": label, "url": url})
    if not tagline:
        raise ValueError(f"{path}: tagline が空です")
    return ProjectConfig(
        name=name,
        slug=slug,
        github=data.get("github") or github,
        tagline=tagline,
        description=str(data.get("description", "")).strip(),
        features=[str(f).strip() for f in data.get("features", []) if str(f).strip()],
        screenshots=[str(s) for s in data.get("screenshots", [])],
        platforms=str(data.get("platforms", "")).strip(),
        listed=bool(data.get("listed", True)),
        posts=bool(data.get("posts", True)),
        claude=bool(data.get("claude", False)),
        links=links,
    )


def toml_str(s: str) -> str:
    """TOML の基本文字列。JSON の文字列表記は TOML でもそのまま通る。"""
    return json.dumps(s, ensure_ascii=False)


def render_project_toml(*, name: str, github: str, tagline: str, description: str,
                        features: list[str], platforms: str) -> str:
    feats = "\n".join(f"  {toml_str(f)}," for f in features)
    return f"""# Shipnote の設定。Pages の LP (/projects/<slug>/) に出す内容。
# 書き換えたら `shipnote sync` で反映する。

name = {toml_str(name)}
github = {toml_str(github)}
# slug = "{slugify(name)}"   # LP の URL。省略すると name から作る

# 一行の紹介 (トップの一覧と LP の見出し下に出る)
tagline = {toml_str(tagline)}

# 二〜四文の説明
description = {toml_str(description)}

features = [
{feats}
]

# 動く環境 (例: "Windows 10 / 11")
platforms = {toml_str(platforms)}

# リポジトリ内の画像のパス。LP に並ぶ
screenshots = []

# false にするとトップの一覧から外す (LP とリリース記録は作る)
listed = true

# false にすると一覧と LP だけ載せ、リリース記録 (/posts/) は作らない (作ってあったものは消す)
posts = true

# true にすると Claude Code 前提のものとして、「作ったもの」ではなく /claudes/ の一覧に載せる
claude = false

# LP の「GitHub で見る」の横に並べるリンク (ギャラリー、動画など)
# links = [
#   {{ label = "ギャラリー", url = "https://..." }},
# ]
"""

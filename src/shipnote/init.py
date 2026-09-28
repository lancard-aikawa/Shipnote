"""``shipnote.toml`` の下書きを作る。README から claude に紹介文を書かせ、人が直す前提。"""

from __future__ import annotations

from pathlib import Path

from . import claude, gh
from .config import PROJECT_FILE, render_project_toml

TAGLINE_MAX = 60
FEATURE_MAX = 80
PLATFORMS_MAX = 60


def draft_prompt(name: str, description: str, readme: str) -> str:
    return f"""個人開発のツール「{name}」の紹介ページに載せる文を書きます。
下の README とリポジトリの説明に書かれている事実だけを使い、無い機能を作らないでください。
日本語。宣伝の誇張 (「革新的」「最強」など) はしない。

次の JSON を 1 つだけ出力する。前後に何も書かない。
{{"tagline": "何をするツールかを一行で ({TAGLINE_MAX} 字以内)",
  "description": "誰の何を楽にするかを 2〜4 文で",
  "features": ["特徴を 3〜5 個、それぞれ {FEATURE_MAX} 字以内"],
  "platforms": "動く OS だけを短く ({PLATFORMS_MAX} 字以内。例: Windows 10 / 11。README に書いてなければ空文字)"}}

# リポジトリの説明
{description or "(なし)"}

# README
{readme[:8000] or "(なし)"}
"""


def run_init(repo: Path, use_ai: bool = True, force: bool = False) -> tuple[Path, list[str]]:
    path = repo / PROJECT_FILE
    if path.exists() and not force:
        raise FileExistsError(f"{path} はもうあります。作り直すなら --force")
    github = gh.github_of(repo)
    info = gh.repo_info(github)
    description = info.get("description") or ""
    readme_path = next((repo / n for n in ("README.md", "readme.md") if (repo / n).exists()), None)
    readme = readme_path.read_text(encoding="utf-8") if readme_path else ""

    tagline, desc, features, platforms = description, "", [], ""
    if use_ai and (readme or description):
        d = claude.ask_json(draft_prompt(repo.name, description, readme))
        tagline = str(d.get("tagline", "")).strip() or description
        desc = str(d.get("description", "")).strip()
        features = [str(f).strip() for f in d.get("features", []) if str(f).strip()][:5]
        platforms = str(d.get("platforms", "")).strip()

    # 長すぎるものは途中で切らず (文が壊れる)、直してもらう
    warnings = []
    if len(tagline) > TAGLINE_MAX:
        warnings.append(f"tagline が {len(tagline)} 字です ({TAGLINE_MAX} 字以内に)")
    for f in features:
        if len(f) > FEATURE_MAX:
            warnings.append(f"features が {len(f)} 字です ({FEATURE_MAX} 字以内に): {f[:20]}…")
    if len(platforms) > PLATFORMS_MAX:
        warnings.append(f"platforms が {len(platforms)} 字です ({PLATFORMS_MAX} 字以内に)")

    text = render_project_toml(name=repo.name, github=github, tagline=tagline or repo.name,
                               description=desc, features=features, platforms=platforms)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path, warnings

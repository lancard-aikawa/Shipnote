"""Zenn の記事の下書き (ストーリー) を作る。

公開するかどうかは人が決める。``published: false`` と、LP・GitHub へのリンクは
コードで入れる (プロンプトで頼んでも守られるとは限らないため)。
"""

from __future__ import annotations

import re
from pathlib import Path

from . import claude
from .config import ProjectConfig
from .material import Material

SITE_URL = "https://lancard-aikawa.github.io"
TOPIC_RE = re.compile(r"^[a-z0-9]{1,30}$")
MIN_BODY = 800


def build_prompt(proj: ProjectConfig, m: Material) -> str:
    first = m.prev_tag is None
    return f"""あなたは個人開発者の代わりに Zenn の記事の下書きを書きます。

# 題材
- ツール: {proj.name} — {proj.tagline}
- 版: {m.tag}{"（最初の公開）" if first else f"（前の版 {m.prev_tag} から）"}

# 書き方
- 「作った話」のストーリーにする。告知文や宣伝文にしない。
  {"なぜ作ったか → どう作ったか・どこで詰まったか → 何ができるか → これから" if first else "何に困ってこの変更をしたか → どう直したか → 使い方の変化"} の順で。
- 下の材料に書かれている事実だけを使う。材料に無い機能・数字・経緯・感想を作らない。
  材料から理由が読み取れないところは、理由を書かずに事実だけを書く。
- 日本語。です・ます調。見出しは ## から。2000〜4000 字。
- 記事の末尾にツールへのリンクを書かない (後で自動で付ける)。

# 出力
次の JSON を 1 つだけ出力する。前後に何も書かない。
{{"title": "記事のタイトル (70 字以内)", "emoji": "絵文字 1 つ", "topics": ["英小文字と数字だけ", "最大 5 個"], "body": "Markdown の本文"}}

# 材料
## 開発者のメモ
{m.notes or "(なし)"}

## CHANGELOG のこの版の節
{m.changelog or "(なし)"}

## この版のコミット
{m.commits or "(なし)"}

## README
{m.readme or "(なし)"}
"""


def article_slug(proj: ProjectConfig, tag: str) -> str:
    """Zenn の slug は a-z0-9_- の 12〜50 字。"""
    s = re.sub(r"[^a-z0-9_-]+", "-", f"{proj.slug}-{tag.lower()}").strip("-")
    if len(s) < 12:
        s = f"{s}-story"
    return s[:50].rstrip("-").ljust(12, "0")


def render(proj: ProjectConfig, data: dict) -> str:
    title = str(data.get("title", "")).strip()
    body = str(data.get("body", "")).strip()
    if not title:
        raise ValueError("claude の返答に title がありません")
    if len(body) < MIN_BODY:
        raise ValueError(f"本文が短すぎます ({len(body)} 字)。材料が足りないかもしれません")
    title = title[:70]
    emoji = str(data.get("emoji", "")).strip()
    if not emoji or len(emoji) > 4 or emoji.isascii():
        emoji = "📦"
    topics = []
    for t in data.get("topics", []):
        t = re.sub(r"[^a-z0-9]", "", str(t).lower())
        if TOPIC_RE.match(t) and t not in topics:
            topics.append(t)
    topics = topics[:5]
    j = lambda s: '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'  # noqa: E731
    footer = (
        f"\n\n---\n\n"
        f"- {proj.name} の紹介とダウンロード: {SITE_URL}/projects/{proj.slug}/\n"
        f"- ソースコード: https://github.com/{proj.github}\n"
    )
    return (
        "---\n"
        f"title: {j(title)}\n"
        f"emoji: {j(emoji)}\n"
        'type: "idea"\n'
        f"topics: [{', '.join(j(t) for t in topics)}]\n"
        "published: false\n"
        "---\n\n"
        + body + footer
    )


def write_story(proj: ProjectConfig, m: Material, zenn_dir: Path, force: bool = False) -> Path:
    path = zenn_dir / "articles" / f"{article_slug(proj, m.tag)}.md"
    if path.exists() and not force:
        raise FileExistsError(f"{path} はもうあります。作り直すなら --force")
    text = render(proj, claude.ask_json(build_prompt(proj, m)))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path

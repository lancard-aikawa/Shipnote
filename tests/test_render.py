import tomllib

import pytest

from shipnote.config import ProjectConfig, render_project_toml
from shipnote.story import article_slug, render
from shipnote.sync import clean_body, post_slug

PROJ = ProjectConfig(name="RepoTether", slug="repotether", github="o/RepoTether", tagline="t",
                     description="", features=[], screenshots=[], platforms="", listed=True)


def test_clean_body_drops_intro_and_duplicate_heading():
    body = "## 0.1.0 の変更点\n\n最初の公開版。\n\n- a\n\n## 初めての方へ\n\nインストーラー\n\n## 既知の問題\n\n- b"
    out = clean_body(body)
    assert "変更点" not in out
    assert "インストーラー" not in out
    assert out.startswith("最初の公開版。")
    assert "## 既知の問題" in out and "- b" in out


def test_post_slug():
    assert post_slug("repotether", "v0.1.0") == "repotether-v0-1-0"


def test_project_toml_roundtrip():
    text = render_project_toml(name="X", github="o/X", tagline='引用符 "と" \\ 記号',
                               description="説明", features=["a", "b"], platforms="Windows")
    d = tomllib.loads(text)
    assert d["tagline"] == '引用符 "と" \\ 記号'
    assert d["features"] == ["a", "b"]


def test_article_slug_length():
    s = article_slug(ProjectConfig(**{**PROJ.__dict__, "slug": "x"}), "v1")
    assert 12 <= len(s) <= 50


def test_story_forces_unpublished_and_links():
    text = render(PROJ, {"title": "t", "emoji": "🔗", "topics": ["Tauri", "個人開発", "svelte"],
                         "body": "あ" * 900, "published": True})
    assert "published: false" in text and "published: true" not in text
    assert 'topics: ["tauri", "svelte"]' in text
    assert "/projects/repotether/" in text and "github.com/o/RepoTether" in text


def test_story_rejects_short_body():
    with pytest.raises(ValueError):
        render(PROJ, {"title": "t", "body": "短い"})

import tomllib
from pathlib import Path

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


def test_remotes_reject_gogs_even_with_github_origin():
    from shipnote.gh import check_remotes
    ok = "origin\thttps://github.com/o/X.git (fetch)\norigin\thttps://github.com/o/X.git (push)\n"
    check_remotes(Path("X"), ok)
    with pytest.raises(ValueError, match="gogs"):
        check_remotes(Path("X"), ok + "backup\thttps://gogs.example.com/a/X.git (fetch)\n")


def test_posts_false_writes_card_only_and_removes_old_posts(tmp_path, monkeypatch):
    from shipnote import gh, sync as s
    rel = gh.Release(tag="v1.0.0", name="X 1.0.0", body="- a", url="u", published_at="2026-09-01T00:00:00Z",
                     prerelease=False, assets=[])
    monkeypatch.setattr(gh, "repo_info", lambda g: {"isPrivate": False})
    monkeypatch.setattr(gh, "releases", lambda g: [rel])
    proj = ProjectConfig(**{**PROJ.__dict__, "posts": False})
    old = tmp_path / "src/content/posts/repotether-v1-0-0.md"
    old.parent.mkdir(parents=True)
    old.write_text(s.render_post(PROJ, rel), encoding="utf-8")
    res = s.sync(proj, tmp_path, tmp_path)
    assert [p.name for p in res.written] == ["repotether.json"]
    assert res.removed == [old] and not old.exists()
    assert '"tag": "v1.0.0"' in (tmp_path / "src/content/projects/repotether.json").read_text(encoding="utf-8")


def test_claude_flag_reaches_card_and_defaults_off(tmp_path):
    import json
    from shipnote.config import load_project
    from shipnote.sync import render_project
    (tmp_path / "shipnote.toml").write_text(render_project_toml(
        name="X", github="o/X", tagline="t", description="", features=[], platforms=""), encoding="utf-8")
    assert load_project(tmp_path, "o/X").claude is False
    proj = ProjectConfig(**{**PROJ.__dict__, "claude": True})
    text, _ = render_project(proj, tmp_path, {}, [])
    assert json.loads(text)["claude"] is True


def test_links_need_label_and_https(tmp_path):
    from shipnote.config import load_project
    base = render_project_toml(name="X", github="o/X", tagline="t", description="", features=[], platforms="")
    f = tmp_path / "shipnote.toml"
    f.write_text(base + 'links = [{ label = "ギャラリー", url = "https://e.example/" }]\n', encoding="utf-8")
    assert load_project(tmp_path, "o/X").links == [{"label": "ギャラリー", "url": "https://e.example/"}]
    f.write_text(base + 'links = [{ label = "x", url = "javascript:alert(1)" }]\n', encoding="utf-8")
    with pytest.raises(ValueError, match="links"):
        load_project(tmp_path, "o/X")

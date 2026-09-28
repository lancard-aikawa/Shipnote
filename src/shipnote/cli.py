"""Shipnote のコマンド。

    shipnote init  <repo>            shipnote.toml の下書きを作る (README から)
    shipnote sync  [<repo>...]       Release → サイトのリポジトリ (LP のデータとリリース記録)
    shipnote story <repo> <tag>      Zenn の記事の下書きを作る (published: false)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, gh
from .config import load_global, load_project


def _site_dir(arg: str | None) -> Path:
    site = Path(arg) if arg else load_global().site_dir
    if not site:
        sys.exit("サイトのリポジトリが分かりません。--site か ~/.shipnote/config.toml の site_dir で指定してください")
    if not (site / "astro.config.mjs").exists():
        sys.exit(f"{site} はサイトのリポジトリ (Astro) ではないようです")
    return site


def cmd_init(a: argparse.Namespace) -> int:
    from .init import run_init
    path, warnings = run_init(Path(a.repo).resolve(), use_ai=not a.no_ai, force=a.force)
    print(f"作りました: {path}")
    for w in warnings:
        print(f"  ! {w}")
    print("中身を読んで直してから `shipnote sync` してください。")
    return 0


def cmd_sync(a: argparse.Namespace) -> int:
    from .sync import sync
    site = _site_dir(a.site)
    repos = [Path(r).resolve() for r in a.repos] or load_global().repos
    if not repos:
        sys.exit("対象のリポジトリがありません。引数か ~/.shipnote/config.toml の repos で指定してください")
    failed = 0
    names = []
    for repo in repos:
        try:
            proj = load_project(repo, gh.github_of(repo))
            res = sync(proj, repo, site, dry=a.dry_run)
        except Exception as e:  # 1 件の失敗で全体を止めない
            print(f"[失敗] {repo}: {e}", file=sys.stderr)
            failed += 1
            continue
        names.append(proj.name)
        rel = lambda p: p.relative_to(site).as_posix()  # noqa: E731
        print(f"[{proj.name}] 書き出し {len(res.written)} / 変更なし {len(res.unchanged)} / 削除 {len(res.removed)}")
        for p in res.written:
            print(f"  + {rel(p)}")
        for p in res.removed:
            print(f"  - {rel(p)}")
        for w in res.warnings:
            print(f"  ! {w}")
    if a.commit and not a.dry_run and names:
        status = gh.git(site, "status", "--porcelain", "--", "src/content").strip()
        if status:
            gh.git(site, "add", "--", "src/content")
            gh.git(site, "commit", "-m", f"Sync releases: {', '.join(names)}")
            print("サイトのリポジトリにコミットしました。")
            if a.push:
                gh.git(site, "push")
                print("push しました。Actions が Pages を作り直します。")
        else:
            print("コミットするものはありません。")
    return 1 if failed else 0


def cmd_story(a: argparse.Namespace) -> int:
    from .material import collect
    from .story import write_story
    repo = Path(a.repo).resolve()
    zenn = Path(a.zenn) if a.zenn else load_global().zenn_dir
    if not zenn:
        sys.exit("Zenn のリポジトリが分かりません。--zenn か ~/.shipnote/config.toml の zenn_dir で指定してください")
    proj = load_project(repo, gh.github_of(repo))
    m = collect(repo, a.tag, Path(a.notes) if a.notes else None)
    print(f"材料: コミット {len(m.commits.splitlines())} 件 / CHANGELOG {'あり' if m.changelog else 'なし'} / "
          f"メモ {'あり' if m.notes else 'なし'}。claude に書かせています (数分かかります)…")
    path = write_story(proj, m, zenn, force=a.force)
    print(f"下書きを作りました: {path}")
    print("published: false のままです。読んで直し、公開するときに true にして push してください。")
    return 0


def main(argv: list[str] | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="shipnote", description="Release から Pages と Zenn の下書きを作る")
    p.add_argument("--version", action="version", version=f"shipnote {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="shipnote.toml の下書きを作る")
    s.add_argument("repo")
    s.add_argument("--no-ai", action="store_true", help="claude を使わず、リポジトリの説明だけで作る")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("sync", help="Release をサイトのリポジトリに書き出す")
    s.add_argument("repos", nargs="*")
    s.add_argument("--site", help="サイトのリポジトリ (既定: config.toml の site_dir)")
    s.add_argument("--dry-run", action="store_true", help="書き出さずに差分だけ表示する")
    s.add_argument("--commit", action="store_true", help="サイトのリポジトリにコミットする")
    s.add_argument("--push", action="store_true", help="コミットのあと push する (--commit と一緒に)")
    s.set_defaults(func=cmd_sync)

    s = sub.add_parser("story", help="Zenn の記事の下書きを作る")
    s.add_argument("repo")
    s.add_argument("tag")
    s.add_argument("--zenn", help="Zenn のリポジトリ (既定: config.toml の zenn_dir)")
    s.add_argument("--notes", help="なぜ作ったか等のメモ (既定: リポジトリの shipnote-story.md)")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_story)

    a = p.parse_args(argv)
    try:
        return a.func(a)
    except (FileNotFoundError, FileExistsError, ValueError, RuntimeError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

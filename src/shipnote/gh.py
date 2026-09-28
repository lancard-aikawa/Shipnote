"""git と GitHub CLI (gh) の呼び出し。"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


def run(args: list[str], cwd: Path | None = None, check: bool = True) -> str:
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} が失敗しました ({p.returncode}):\n{p.stderr.strip()}")
    return p.stdout


def git(repo: Path, *args: str, check: bool = True) -> str:
    return run(["git", "-C", str(repo), *args], check=check)


GITHUB_RE = re.compile(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$")


def github_of(repo: Path) -> str:
    """origin の URL から owner/name を取る。"""
    url = git(repo, "remote", "get-url", "origin", check=False).strip()
    m = GITHUB_RE.search(url)
    if not m:
        raise ValueError(f"{repo} の origin が GitHub ではありません ({url or 'origin なし'})")
    return f"{m.group(1)}/{m.group(2)}"


@dataclass
class Asset:
    name: str
    url: str
    size: int


@dataclass
class Release:
    tag: str
    name: str
    body: str
    url: str
    published_at: str  # ISO 8601
    prerelease: bool
    assets: list[Asset]

    @property
    def date(self) -> str:
        return self.published_at[:10]


def releases(github: str) -> list[Release]:
    """公開済みの Release を新しい順に返す (下書きは含めない)。"""
    out = run(["gh", "api", f"repos/{github}/releases?per_page=100"])
    items = []
    for r in json.loads(out):
        if r.get("draft") or not r.get("published_at"):
            continue
        items.append(Release(
            tag=r["tag_name"],
            name=r.get("name") or r["tag_name"],
            body=(r.get("body") or "").replace("\r\n", "\n").strip(),
            url=r["html_url"],
            published_at=r["published_at"],
            prerelease=bool(r.get("prerelease")),
            assets=[Asset(a["name"], a["browser_download_url"], a["size"]) for a in r.get("assets", [])],
        ))
    items.sort(key=lambda r: r.published_at, reverse=True)
    return items


def repo_info(github: str) -> dict:
    out = run(["gh", "repo", "view", github, "--json",
               "description,licenseInfo,defaultBranchRef,isPrivate,url"])
    return json.loads(out)

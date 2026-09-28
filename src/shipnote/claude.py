"""``claude -p`` の呼び出し。

API キーが環境にあると従量課金に倒れるので、子プロセスには渡さない (サブスクの枠で動かす)。
ツールは全部外し、文章を書かせるだけにする。
"""

from __future__ import annotations

import json
import os
import re
import subprocess

TIMEOUT = 900


def ask(prompt: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    p = subprocess.run(
        ["claude", "-p", "--tools", "", "--no-session-persistence", "--output-format", "text"],
        input=prompt, capture_output=True, text=True, encoding="utf-8", env=env, timeout=TIMEOUT,
    )
    if p.returncode != 0:
        raise RuntimeError(f"claude -p が失敗しました ({p.returncode}):\n{(p.stderr or p.stdout).strip()}")
    return p.stdout.strip()


def ask_json(prompt: str) -> dict:
    """JSON を 1 つ返させる。前後に文章や ``` が付いても拾う。"""
    text = ask(prompt)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"claude の返答に JSON がありません:\n{text[:500]}")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(f"claude の返答の JSON が読めません ({e}):\n{text[:500]}") from e
    if not isinstance(data, dict):
        raise ValueError("claude の返答が JSON のオブジェクトではありません")
    return data

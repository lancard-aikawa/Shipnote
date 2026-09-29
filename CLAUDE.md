# Shipnote

使い方と役割の分け方は README.md。ここには、変えるときに守ること。

- **Pages のリリース記録に LLM を使わない。** Release の本文 (CHANGELOG から人が書いたもの) をそのまま使う。
  書いていない機能が公開ページに紛れ込まないようにするため
- **LLM の出力の制約はコードで担保する。** Zenn の `published: false`、LP・GitHub へのリンク、topics の形式、
  slug の長さは story.py が入れる/直す。プロンプトで頼むだけにしない
- **LLM の出力を文字数で切らない。** 文の途中で切れる (「デスクトップア」になった)。長すぎたら警告して人に直してもらう
- `claude -p` の子プロセスには `ANTHROPIC_API_KEY` を渡さない (従量課金に倒れる)。ツールは `--tools ""` で全部外す
- Claude Code のセッション記録 (`~/.claude/projects`) は材料にしない。読もうとしたら許可されなかった (2026-09-28)。
  「なぜ作ったか」は人が `shipnote-story.md` に書く
- **Gogs (gogs.lancard.com) のリポジトリは絶対に材料にしない。** 機密を含む。remote が 1 つでも GitHub 以外なら
  `gh.github_of` (→ `check_remotes`) で止める。この確認を外す・迂回する変更 (設定の `github` で上書きして通す等) をしない
- LP のパスは `/projects/<slug>/`。ユーザーサイトの直下にすると、各リポジトリの Pages (例: `/kokogallery/`) とぶつかる

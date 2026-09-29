# Changelog

## 0.1.0

最初の版 (未公開)。

- `shipnote init`: README から `shipnote.toml` の下書きを作る。長すぎる項目は切らずに警告する
- `shipnote sync`: 公開済みの Release から、サイトの LP のデータとリリースの記録を書き出す。`--commit` / `--push`
- `shipnote story`: コミット・CHANGELOG・README・`shipnote-story.md` から Zenn の記事の下書きを作る (`published: false`)
- `shipnote.toml` の `posts = false`: リリース記録は作らず、一覧と LP にだけ載せる
- `shipnote.toml` の `claude = true`: Claude Code 前提のものとして `/claudes/` の一覧に載せる
- remote が 1 つでも GitHub 以外 (Gogs など) のリポジトリは、どのコマンドでも止める

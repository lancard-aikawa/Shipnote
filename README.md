# Shipnote

GitHub の Release を材料に、次の 2 つを作る個人用の CLI です。

- **Pages のサイト**（[lancard-aikawa.github.io](https://github.com/lancard-aikawa/lancard-aikawa.github.io)）に載せる、各ツールの紹介ページ（LP）のデータとリリースの記録
- **Zenn の記事の下書き**（「作った話」のストーリー）。`published: false` で作るので、公開するかどうかは人が決めます

リリースの告知を自分で書かずに済ませるための道具です。

## 役割の分け方

| 出し先 | 中身 | 作り方 |
|---|---|---|
| Pages `/projects/<slug>/` | 紹介・特徴・ダウンロード | `shipnote.toml`（人が直したもの）と最新の Release |
| Pages `/claudes/` | Claude Code 前提のものの一覧 | `shipnote.toml` の `claude = true` |
| Pages `/posts/<slug>-<tag>/` | その版の変更点 | Release の本文そのまま（LLM は使わない） |
| Zenn | なぜ作ったか・どう作ったか | `claude -p` が下書きし、人が読んで公開 |

Release の本文は CHANGELOG から人が書いたものなので、Pages には書いていない機能が紛れ込みません。
LLM が書くのは `shipnote.toml` の下書きと Zenn の下書きだけで、どちらも人が読んでから使います。

## 必要なもの

- [uv](https://docs.astral.sh/uv/)、git、[GitHub CLI](https://cli.github.com/)（`gh auth login` 済み）
- `init` と `story` には [Claude Code](https://claude.com/claude-code)（`claude -p` を使います）。
  `ANTHROPIC_API_KEY` は子プロセスに渡さないので、サブスクの枠で動きます

## 使い方

```sh
# 1. リポジトリに shipnote.toml の下書きを作る (README から)。読んで直す
shipnote init C:\Repos\mywork\RepoTether

# 2. Release を公開したら、サイトに書き出す
shipnote sync C:\Repos\mywork\RepoTether --commit --push

# 3. 最初の公開や大きな版では、Zenn の下書きを作る
shipnote story C:\Repos\mywork\RepoTether v0.1.0
```

ソースから動かすときは `uv run --project C:\Repos\mywork\Shipnote shipnote ...`。

- `sync` は何度流しても同じ結果になります（変わったファイルだけ書き出す）。Release を消すと記録も消えます
- `sync --dry-run` で書き出す予定のファイルだけを表示します
- 非公開のリポジトリは載せません

### Zenn の下書きに「なぜ」を入れる

材料はコミット・CHANGELOG・README です。なぜ作ったか、何で失敗したかはここに書かれていないことが多いので、
リポジトリの直下に `shipnote-story.md` を置いてメモを書いておくと、それを軸に書きます（箇条書きで十分）。
材料に無い経緯は書かないように指示しているので、メモが無いと「何ができるか」中心の記事になります。

## 設定

### 全体 `~/.shipnote/config.toml`

```toml
site_dir = "C:/Repos/mywork/lancard-aikawa.github.io"
zenn_dir = "C:/Repos/mywork/zenn-content"
repos = [
  "C:/Repos/mywork/RepoTether",
  "C:/Repos/mywork/LPortMan",
]
```

`repos` を書いておくと `shipnote sync` を引数なしで流せます。

### プロジェクトごと `shipnote.toml`

`shipnote init` が作ります。`tagline`（一行）、`description`、`features`、`platforms`、`screenshots`（リポジトリ内の画像のパス）、`listed`（一覧に出すか）、`posts`（リリース記録を作るか）、`claude`（Claude Code 前提か）。

これまでに Release を出したプロジェクトを、記録は出さずに「作ったもの」の一覧と LP にだけ載せるときは `posts = false` にします。
LP のダウンロード欄は最新の Release のままです。作ってあった記録は次の `sync` で消えます。

Claude Code に頼んで動かす前提のもの（単体では動かないもの）は `claude = true` にします。
「作ったもの」（トップと `/projects/`）から外れて、`/claudes/` の一覧に載ります。LP は同じ `/projects/<slug>/` で、
Claude Code が必要なことを書き添えます。Release が無くても載せられます。

### 載せないもの

非公開のリポジトリと、remote が 1 つでも GitHub 以外（Gogs など）のリポジトリは、`init` / `sync` / `story` のどれもエラーで止まります。
Gogs のリポジトリは機密を含むので、origin が GitHub でも Gogs の remote が混ざっていたら材料にしません。

## 開発

```sh
uv sync
uv run pytest -q
```

## ライセンス

MIT

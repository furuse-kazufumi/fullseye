# Fullseye を AI アシスタントの RAG にする手順(Claude Code 向け)

Fullseye の推奨運用は「**AI コーディングアシスタントの知識ベース(RAG)として使う**」こと。
全 op が機械可読な Markdown ノート(`docs/ops`、単一真実源)を持つため、追加のベクタ DB や
埋め込みサービスは**不要**です。grep できる環境ならそれがそのまま RAG になります。

3 段階の導入方法を用意しています。**Tier 0/1 は外部依存ゼロ**(Fullseye リポジトリだけで完結)。

## 入口は 1 つではない(最初に読む)

文書だけを渡した Codex / Copilot は、どちらも 1 回目に **用途から引く索引を見つけられなかった**
(2026-09-15)。原因はこのガイドに導線が無かったこと。入口は 4 つある:

1. **用途から** → [`docs/CAPABILITIES.md`](CAPABILITIES.md)。課題 → **推奨パイプライン(順序つき op)/
   代替 / 限界 / 実寸校正** を 1 課題 1 ファイル(`docs/capabilities/`)で持ち、op 名の実在と
   **型(in → out)が前段から後段へ繋がる**ことを `tests/test_capabilities.py` が検査する。
2. **op 名・概念から** → [`docs/ops/INDEX.md`](ops/INDEX.md) → 族の目次 → op ノート。
3. **機械で引く** → `fs.op_find(query)`(自由語・語幹)/ `fs.op_assist(op)`(仕様・プリセット・
   次に繋げる先)/ `fs.op_path(from_sort, to_sort)`(型 A → 型 B を繋ぐ op 列)/
   `fs.op_producers(sort)`(その型を産む op)/ `fs.op_accepts(op)`(実測の受理型)、
   CLI は `fullseye has <op>`(HALCON 名でも引ける)。
4. **索引ファイル** → [`docs/OP_INDEX.json`](OP_INDEX.json)(全 op の型契約)、
   wheel 同梱の `OP_CATALOG.md`。

> **PyPI からの利用**: `pip install fullseye` した環境では console script **`fullseye-rag`** が
> 使えます。checkout(clone / `pip install -e .`)なら `docs/ops` のフルコーパスを、wheel のみ
> なら同梱の `OP_CATALOG.md`(AI 向け全 op カタログ)をスキルにピン留めします(フルの
> per-op ノートが欲しくなったら repo を clone して再実行するだけ)。更新は
> `py -3.11 tools/update_fullseye.py`(dirty ツリー拒否・--ff-only・スキルはバックアップの上
> 更新・Studio 設定には触れない=環境をつぶさない設計)。

---

## Tier 0: リポジトリを開くだけ(手順ゼロ)

Fullseye リポジトリのチェックアウトを Claude Code で開けば、`docs/ops/INDEX.md` と
per-op ノートをそのまま検索・参照できます。コーパスはリポジトリ内容(wheel には同梱しない)
なので、pip インストールのみの場合はリポジトリも clone してください。

```
docs/CAPABILITIES.md                    # 用途 → op 連鎖(推奨パイプライン / 代替 / 限界 / 実寸校正)。ここから入る
docs/ops/<family>/<category>/<op>.md    # 呼び出し形・型契約・HALCON 別名・文献・関連 op(2d / 3d / optics / piv …)
docs/ops/INDEX.md                       # フォルダ階層 walk で自動生成の全体目次(34 族)
docs/ops/<family>/guides/<name>.md      # 使い方ガイド 49 本(34 族。2-D は gallery2d_*、数式・図・正典引用)
docs/OP_INDEX.json                      # レジストリの機械可読インデックス
```

数字(族 34・ガイド 49・ノート枚数)は配布物の側から数えたもので、`tests/test_docs_index_reachable.py`
がこの行と実ファイルを突き合わせる(自己記述が中身から遅れないように)。

**Windows のシェルから読むときは UTF-8 を明示する** —— ノートは BOM 無しの UTF-8 で、既定の
コードページで開くと日本語が文字化けし、AI が「読めていない」のに「無い」と判断する(Codex で実際に
起きた)。PowerShell は `Get-Content -Encoding utf8`、`[Console]::OutputEncoding = [Text.Encoding]::UTF8`
(または `chcp 65001`)、Python は `PYTHONUTF8=1`。

## Tier 1: スキルとして常駐させる(推奨・同梱インストーラー)

自分のプロジェクト側で作業しながら Fullseye を引きたい場合は、同梱のセットアップ
スクリプトを 1 回実行します:

```bash
py -3.11 tools/setup_claude_rag.py              # インストール(再実行=更新)
py -3.11 tools/setup_claude_rag.py --uninstall  # 削除
```

同梱スキル `skills/fullseye-ops` が `~/.claude/skills/fullseye-ops` へコピーされ、
SKILL.md の `FULLSEYE_REPO =` 行が**この checkout の絶対パスに自動で固定**されます
(AI がどのプロジェクトで作業していてもコーパスの場所が分かる)。コーパス
(`docs/ops`)が見つからない checkout ではインストールを拒否します(fail-closed)。

以後、画像処理・幾何ビジョンの話題で Claude Code が自動的にこのスキルを起動し、
`docs/ops` を検索(retrieve)→ 型(sort)が繋がる op を選んで実装 → 同梱の worked example で
検証、という流れで動きます。スキル本文がそのまま「AI への使い方指示書」です。
手動で入れたい場合は `skills/fullseye-ops` を `~/.claude/skills/` へコピーするだけでも
動きます(パス固定が無い分、AI がリポジトリ位置を都度探します)。

## Tier 2(任意): クラスタ化コーパス — 外部ツールでの発展形

ノート **1,949 枚**をトピッククラスタに階層化し、各クラスタに LLM 要約を付けた
「ナビゲーション付きコーパス」も作れます。私たちは内部で
[RAPTOR](https://github.com/gadievron/raptor) フォークの `corpus2skill`
(TF-IDF + k-means + LLM 要約)を使っていますが、**これは任意の最適化であって
必須ではありません**。要件は「`docs/ops` を入力に、クラスタごとの SKILL.md 階層を
出力する」ことだけなので、同等のツールなら何でも代替できます。

再取込(ノート更新後)の例 — 内部運用そのままの honest な記録として:

```powershell
$env:RAPTOR_DIR="<path-to-raptor-checkout>"
py -3.11 raptor_corpus2skill.py --source <fullseye>/docs/ops --name fullseye_ops_corpus_v2 `
  --overwrite --max-depth 2 --max-clusters 6 --min-cluster-size 8   # 要 ANTHROPIC_API_KEY
```

注意: クラスタ化コーパスは**取込時点のスナップショット**です。`docs/ops` を更新したら
再取込しないと陳腐化します(Tier 0/1 は常に生ノートを読むため陳腐化しません)。

---

## なぜこれが機能するか(設計上の根拠)

1. **md=単一真実源**: ノートはレジストリから決定的に自動生成され、CI の drift テストで
   「commit 済みノート == 現在のコードから生成したノート」を強制。**AI が読む文書と
   実際のコードが常に同じ版**です(frontmatter の `version` + fingerprint)。
2. **型(sort)契約**: 各ノートが `in:`/`out:` と「型が繋がる関連 op」を持つので、AI は
   パイプラインを**型検査しながら**組めます。
3. **検証可能**: 全 op に ground-truth 付き worked example(`examples/` /
   `examples_3d/`)があり、AI が自分の提案を実行して確かめられます。
4. **表示まで一気通貫**: Studio(`py -3.11 studio.py`)を開けば、AI が組んだ結果を
   画像ウィンドウ・3D 表示として人間が同じ画面で検査できます(`dev_open_window` 等で
   スクリプトから複数窓の配置も可能)。

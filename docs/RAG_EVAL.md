# RAG 評価 — 他の AI に同じ質問集を投げて機械採点する

`docs/ops`(op ノート 1,942 枚)+ `docs/OP_CATALOG.md` + `docs/MCP.md` を「AI 向け RAG」として
使ったとき、**Claude Code 以外の AI がどれだけ正しく op を引けるか**を、固定の質問集と
機械採点で測る仕組み。置き場所は `tools/rag_eval/`、門は `tests/test_rag_eval.py`。

```
tools/rag_eval/
  questions.json        固定質問集 30 問(15 分野 × 2)+ 正解の判定基準
  prompt_template.txt   投げるプロンプトの雛形(文書だけで答える・op 名を作らない・根拠パスを添える)
  run.py                実行器(Codex CLI / Copilot CLI、読み取り専用、--dry-run あり)
  ingest.py             手で投げた transcript から最終回答を切り出して run dir にする
  score.py              機械採点 → score.json / score.md、複数 AI の横並び表
  common.py             op の実在確認(4 層)・文書語彙・回答からの抽出
  runs/<date>_<ai>/     qNN.md(回答)/ meta.json / score.json / score.md / feedback.md / interview.md
```

## 目的

1. **文書側の弱点を数字で見る**: どの分野で op を引けないか、実在しない op を作るか、根拠を
   挙げられるか。改善(逆引き索引・決定表・単位の明記)の前後で同じ質問集を投げて比べる。
2. **AI ごとの差を測る**: 同じ文書でも AI の道具(ファイルを開く手段・文字コード・サンドボックス)で
   結果が変わる。差は文書の問題か環境の問題かを切り分ける。
3. **外部 AI の指摘を鵜呑みにしない**: 採点は機械的に測れるものだけ。感想・限界の指摘は人が
   一次情報で検証してから採用する(下の「規律」)。

## 質問集の作り方(`questions.json`)

30 問、15 分野 × 2 問。分野: 2D 欠陥 / 計測 / 偏光 / 光学 / レンズ / 照明設計 / 3D / 1-D 信号 /
音響 / SPC / トモグラフィ / 天体スタック / 法医 / MCP の使い方 / 失敗の原因診断。
2026-09-15 に手で投げた 3 問(スクラッチ・偏光・内径)を q01〜q03 として含む。

各問が持つもの:

| 項目 | 意味 |
|---|---|
| `required_ops` | **必須 op 群**のリスト。各群は代替の集合(例: 線検出は `lines_gauss` でも `tophat` でも可)。群のどれか 1 つを実在 op 名で挙げれば充足 |
| `required_terms` | op でない鍵語の群(MCP の tool 名、環境変数、診断の語)。substring 一致 |
| `optional_ops` | 妥当な補助 op。加点はしないが表に出す |
| `expected_evidence` | 質問側が想定する根拠ノート/ガイドのパス |
| `human_check` | **検証済みの事実**(採点器は見ない。人が回答を読んで照合する) |

**門**: 正解側の op 名は全部 `tests/test_rag_eval.py` が実在確認する。`fs.find_op` は 2-D レジストリ
(+HALCON 別名)しか見ないので、それだけで「無い」と言うと台帳(`fs.ledger`、1,000 本超)の op を
見落とす。`common.op_exists` は 2-D レジストリ → 台帳 → algo 層 → ノート(CI の drift 門で
レジストリと一致が強制される)の順に全部引く。期待根拠のパスと鍵語も実在確認する
(鍵語は期待根拠ファイルに実際に書いてあること)。

質問を足すときは: 分野を 2 問ずつ保つ / `required_ops` は「これを引けなければ答えになっていない」
群だけにし、前処理(`gaussian` 等)は optional に / `human_check` にはノートで確認した事実だけを書く。

## 実行手順

各 AI の登録・ログインはそれぞれの CLI の手順に従う(ここには書かない)。実行器は **読み取り専用**
(Codex `-s read-only` / Copilot `--allow-tool read --no-ask-user`)、cwd = リポジトリ root、stdin は閉じる、
1 回の呼び出しに上限秒(既定 900)。

```powershell
# コマンド列を確かめるだけ(何も書かない)
py -3.11 tools/rag_eval/run.py --ai codex --dry-run
py -3.11 tools/rag_eval/run.py --ai copilot --ids q01,q02,q03 --dry-run

# 実行(1 問ずつ。--batch 3 で 3 問ずつ束ねる)→ tools/rag_eval/runs/<今日>_<ai>/
py -3.11 tools/rag_eval/run.py --ai codex --timeout 900
py -3.11 tools/rag_eval/run.py --ai copilot --batch 3

# 手で投げた transcript を取り込む(問 N の見出しで q01, q02, … に割る)
py -3.11 tools/rag_eval/ingest.py --ai codex --transcript <stdout を保存した file> --out tools/rag_eval/runs/<date>_codex

# 採点(複数 dir を渡すと横並び表も出る)
py -3.11 tools/rag_eval/score.py tools/rag_eval/runs/<date>_codex tools/rag_eval/runs/<date>_copilot
```

dry-run の 1 行(プロンプトは切り詰めて表示):

```
[q01] cwd=<repo>  timeout=900s  stdin=DEVNULL
  codex exec -s read-only -C <repo> 'あなたは画像処理ライブラリ fullseye(このリポジトリ、`import fullseye as fs`)を初めて使...<612 chars>'
```

失敗は消さない: timeout / 非ゼロ終了 / 見出しが無くて割れなかった回答は `meta.json` の `calls` に
status(`ok` / `error` / `timeout` / `unparsed` / `cli-not-found`)と所要秒で残り、生の stdout は
`qNN.raw.txt` に残る。

## 採点の定義(`score.py`、0〜100)

| 項目 | 配点 | 何を測るか |
|---|---|---|
| op 網羅 | 50 | 必須群(op 群 + 鍵語群)のうち、回答が**実在する** op 名 / 鍵語で満たした割合 |
| 根拠の実在 | 20 | 回答が挙げたリポジトリ相対パスのうち実在する割合(挙げていなければ 0) |
| 期待根拠 | 10 | `expected_evidence` のどれかを挙げていれば加点 |
| 実在しない op を作らない | 20 | op でも文書語彙でもない snake_case をバッククォートで書いた数 u に対し 20·max(0, 1 − u/3) |

回答からの抽出は regex だけ: バッククォート内の識別子(`fs.ledger.foo(...)` / `fullseye.apply(img, "foo")` /
`opsxxx.get("foo")` の形も)と、`docs/…`, `examples/…` などのパス。識別子は 3 段に分ける:

* **実在 op** —— 4 層のどれかにある(HALCON 別名は正規名に畳む。`fit_circle_contour_xld` → `hx_fit_circle_contour`)
* **文書語彙** —— op ではないが型名・引数名・返り値の鍵としてノートに出る(`max_violation_frac`, `params`)。減点しない
* **作った疑い** —— どちらでもない下線つきの名前。減点

**LLM で採点しない。** 「金属で信頼できないと言えたか」「px→mm の op が無いと正直に言えたか」のような
限界の指摘は `human_check` を横に置いて人が読む。実在 op の欄には、辞書の鍵と同名の op(`rms` 等)が
混じることがある —— 網羅率には効かないが、表を読むときは頭に入れておく。

## 2026-09-15 の結果(q01〜q03、3 問を 1 プロンプトで)

| 問 | 分野 | Codex | Copilot |
|---|---|---:|---:|
| q01 | 2D 欠陥(スクラッチ) | 75.0 | 93.3 |
| q02 | 偏光(拡散成分) | 100.0 | 100.0 |
| q03 | 計測(内径) | 100.0 | 93.3 |
| **平均** | | **91.7** | **95.5** |

| 計測 | Codex | Copilot |
|---|---|---|
| モデル | gpt-5.6-sol(`codex exec -s read-only`) | Copilot CLI 既定(`--allow-tool read -s`) |
| ファイルを開いた回数 | 20(自己申告)/ exec ブロック 27、方針拒否 5 | 語りの行数 21(`-s` では tool 呼び出しが出ないので近似) |
| トークン | 90,819 | 不明(出力しない) |
| 文字コード | PowerShell `Get-Content` が BOM 無し UTF-8 を文字化け → `-Encoding utf8` で再読。`[Console]::OutputEncoding` 変更は read-only 方針で拒否 | 問題なし |

点差の内訳(機械採点が拾ったもの):

* **q01 Codex 75**: 線検出(`lines_gauss`)は引けたが、**幅の計測 op(`measure_pairs`)を見落とした**
  (「幅を測る op は見つからなかった」と回答)。Copilot は `tophat → … → measure_pairs` で両群を満たした。
* **q01 / q03 Copilot 93.3**: 根拠パスを `docs/examples/poc_….py` と書いた(実在は `examples/poc_….py`)。
* 実在しない op はどちらも作らなかった(u = 0)。

人が読んで検証した所見(`human_check` との照合):

| 主張 | 出所 | 検証 |
|---|---|---|
| `lines_gauss` は幅・極性を返さない | Codex | 正(ノートに明記) |
| 傷幅を測る op は無い | Codex | **誤**。`measure_pairs`(measure1d 族)で測れる |
| `polarization_separate` は金属で信頼できない、`max_violation_frac` の推奨値が無い | 両 AI | 正(ノートに警告あり、推奨値は無い) |
| px→mm の op は無い | 両 AI | 正 |
| `gaussian` の a→σ 換算が曖昧 | Copilot | **誤**。ノートに σ = 0.3 + 2.7a |
| `AI_RAG_GUIDE.md` の「2D guides は 13 ファミリ」は古い | Codex | 正(実 16 ファイル) |
| `OP_CATALOG.md` の「204 例」は 201〜203 | Copilot | **誤**。見出し下の項目を数えると 204 |
| `measure_pairs` は対が見つからないことを区別しない | Copilot | 正(ガイドの落とし穴 2: 近接エッジでも 100 % 「見つかった」と答える) |

## AI ごとの使い道と障害(聞き取り、採点対象外)

同じ 2 AI に「fullseye を自分の日常の作業に組み込むか」を 7 項目で聞いた(共通プロンプト
`tools/rag_eval/runs/interview_prompt.txt`、回答は各 run dir の `interview.md`)。質問集の採点とは別枠で、
人が読む用。Codex は 25 回の exec のうち **18 回が方針拒否**(`--demo` 実行・複数ファイルの一括読み・
エンコーディング変更)、65,358 トークン。Copilot は 31 行で返した。

| 観点 | Codex | Copilot |
|---|---|---|
| 役に立つ場面 | 検査画像の古典処理での判定、ステレオ/点群/CT/粗さのコードのレビュー、`import fullseye as fs` の安定した入口 | 検査画像の欠陥・寸法、点群からの深度/姿勢/地形/把持、Claude Code から MCP で検索→ノート→実行 |
| 使わない場面 | 画像と無関係な依頼、学習済みモデルが要る意味認識 | 自然画像の認識・分類、画像を目視できない環境での最終判定 |
| 詰まった点 | 読み取り専用で実行・登録が不可、PowerShell の文字化け、一括読みの拒否、巨大カタログ | 巨大ファイルの一括閲覧拒否、PowerShell の permission denied、MCP 登録不可 |
| 一番使いやすい入口 | **op ノート**(部分読みできる。MCP は本来最良だがこのセッションでは使えない) | **MCP**(検索・説明・実行が連続する。登録できなければ次点は `rg` で op ノート) |
| 軽くなる課題 | 幻覚・古い知識・誤った連鎖(fingerprint / drift / GT / 型契約 / fail-closed) | 幻覚・長文の読み落とし・ツール失敗の隠蔽 |
| 悪化する課題 | 巨大文書の読み落とし、op 数の表記が不統一、文字コード・任意依存・checkout 必須 | コンテキスト量、環境差(wheel に知識層なし)、Tier 2 の陳腐化 |
| 作者への要望 1 つ | wheel に索引と最小限のノートを同梱し checkout なしで MCP を起動 | 同左(op ノートと `OP_INDEX.json` を含む MCP 対応 wheel) |

検証済みの注記(両 AI の主張を一次情報で確かめたもの):

1. 両 AI の「作者への要望」= **wheel だけで MCP を起動**は **0.2.0 で実装済み**(`docs/MCP.md`)。
   両 AI は 0.1.11 の文書(「wheel からは `CatalogError` で止まる」)を読んでいた。
2. Copilot の「`AI_RAG_GUIDE.md` が約 389 KB で一括閲覧が拒否された」は**取り違え**。実 5.6 KB。
   巨大なのは `docs/OP_CATALOG.md`(398 KB)。
3. Codex の「op 数が 918 / 1,500+ / 1,943 と不統一」は README で**確認済み**(0.2.0 で統一予定)。
4. 一番使いやすい入口は **Copilot = MCP、Codex = op ノート**で割れた。どちらも「自分の環境で使えるもの」を
   選んでいる(Codex は MCP を登録できない)。
5. どちらも**答えの正しさを自分で確かめる手段を持てなかった**(例の実行・図の目視が不可)。
   文書側で「実行できる例」を用意しても、実行できない AI には届かない —— 数値の期待値をノートに
   書いておく(読むだけで照合できる)のが次の手。

## 規律: AI の指摘は一次情報で検証してから採用

外部 AI(Codex / Copilot / Gemini)の finding は情報収集・第二意見であって、そのまま採用しない。
上の表のとおり、もっともらしい指摘の中に**誤りが混じる**(「幅を測る op は無い」「a→σ が曖昧」
「204 例は 201〜203」「AI_RAG_GUIDE が 389 KB」)。手順:

1. 採点表(`score.md`)で機械的に測れる分(op 網羅・根拠の実在・作った op)を見る。
2. 回答の主張を 1 件ずつ `human_check` とノート本文で照合し、正 / 誤 / 未確認に分ける。
3. 正しい指摘だけを文書改善に回す。誤りも捨てず、上のような表に残す(次の AI が同じ誤りをするかが
   文書側の弱点の指標になる)。

## 既知の環境差

* **Codex(Windows)**: 既定の PowerShell `Get-Content` は BOM 無し UTF-8 を文字化けさせる。
  `-Encoding utf8` を付ければ読める。`[Console]::OutputEncoding` を変えるコマンドは read-only 方針で
  拒否される。複数ファイルをカンマで一括指定する `Get-Content` も拒否されることがある(1 ファイルずつなら通る)。
  プロンプト雛形に「UTF-8 として読む(`Get-Content -Encoding utf8`)」を入れてある。
* **Copilot(Windows)**: 文字化けは出なかった。`-s`(quiet)では tool 呼び出しが出力に残らないので、
  ファイルを開いた回数は語りの行数で近似する。巨大ファイル(`docs/OP_CATALOG.md` 398 KB)は一括閲覧を拒否し、部分検索に落ちる。
* **どちらも**: サンドボックスでは例を実行できない。MCP サーバも登録できない。文書を読むだけで答えている。
* 回答に混じったローカル絶対パスは `ingest.py` がリポジトリ相対に落とす(公開物にローカルパスを残さない。
  `tests/test_rag_eval.py` が run dir を検査する)。

## 次の手

* 30 問を両 AI に 1 問ずつ投げて `runs/` を増やす(今日は 3 問だけ)。分野別の平均で文書の弱点を見る。
* 文書改善(用途→op の逆引き索引、類似 op の決定表、px→mm の書き方)の前後で同じ質問集を投げ、
  差分を CHANGELOG に残す。
* ノートに「読むだけで照合できる数値」(実行できる例の期待出力)を足し、実行できない AI にも検証手段を渡す。

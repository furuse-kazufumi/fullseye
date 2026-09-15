# Fullseye を MCP(Model Context Protocol)から使う

Claude Code / Claude Desktop などの MCP クライアントから、fullseye の op を**探し、
使い方を読み、実際に走らせる**ための stdio サーバ。0.1.11 で PoC として入った。

```
py -3.11 -m fullseye.mcp             # stdio サーバ(クライアントが起動する)
py -3.11 -m fullseye.mcp --demo      # 自分を起動して一通り叩く(下の出力が出れば動いている)
py -3.11 -m fullseye.mcp --coverage  # カタログ 5 層の被覆を JSON で
```

**前提(正直に)**: いまは**開発 checkout 前提**。カタログの正本 `docs/OP_INDEX.json` と
知識層 `docs/ops/**/*.md` は wheel に入っていないので、`pip install fullseye` した環境から
起動すると `CatalogError: docs/OP_INDEX.json が無い` で**理由つきで止まる**(黙って空の
カタログにはならない)。wheel 対応は次の版。

## Claude Code への登録

```
claude mcp add fullseye -- py -3.11 -m fullseye.mcp
```

リポジトリの外から起動するときは作業ディレクトリを checkout に向ける
(`--cwd` 相当の設定はクライアントに従う)。読み込める画像は既定で**同梱サンプルだけ**。
自分の画像を読ませるには根を足す:

```
set FULLSEYE_MCP_ROOT=C:\path\to\images;D:\more   (PowerShell: $env:FULLSEYE_MCP_ROOT = "...")
```

## tool は 8 つ(op は 1,939 あるが tool にはしない)

op はデータで、tool は「探す・読む・読み込む・走らせる・観察する」の数個だけ。
tool を 1,939 個並べると LLM の文脈を食い潰す(TheMCPCompany の実測: 18,000 tool は
retrieval 無しでは使えない)。

| tool | 何をするか |
|---|---|
| `fullseye_search_ops` | 名前・HALCON 名・カテゴリ・次元の部分一致。返り値の `sources` が出どころ(index / registry / ledger / note / facade)、`by_sources` が層別の内訳 |
| `fullseye_op_help` | op の知識層ノート(使い方・つまみ a/b の実効・HALCON 相当)+ 生成済みで実行が検証された図を `resource_link` で |
| `fullseye_catalog_coverage` | カタログ 5 層の交差。検索がどれだけの機能を見えているか |
| `fullseye_list_samples` | 同梱サンプル(来歴・ライセンスつき) |
| `fullseye_load_image` | 画像 → ハンドル。画素は返さず、数値統計 + 判定 |
| `fullseye_apply` | ハンドルに op を 1 つ。出力ハンドル + 数値統計 + 判定 + 劣化台帳 |
| `fullseye_pipeline` | op を順に。段ごとに記録、型連鎖は走らせる前に検査、strict は失敗段で停止 |
| `fullseye_inspect` | ハンドルの数値統計 + 判定(+ 小図) |

## 画像は「在らず、必要なときだけ在る」

画像は `fullseye://img/<sha16>` の**ハンドル**でやり取りし、LLM はバイト列を見ない
(画像を本文に載せると 1 枚で文脈が破裂する)。代わりに**返り値が自分の妥当性を名乗る**:

```
otsu(a=0.50, b=0.50) → fullseye://img/2c1e…
判定=ok(std=0.499 range=1)  shape=[512, 512] min=0 max=1 mean=0.46 std=0.499 nonfinite=0
```

判定は「標準偏差 0 / 値域 0.1 未満 / 空 / 非有限 / [0,1] の外」を機械的に見て
`ok / constant / flat / saturated / nonfinite / out_of_range / empty` を返す。
**判定は必ず生の数値と併記**する —— 言葉だけだと、判定器が中身を見ていなくても「健全」と
言えてしまう。免除は `ops.NONFINITE_IS_MEANINGFUL`(inf が答えの op)と
`ops.UNIT_RANGE_IS_NOT_THE_CONTRACT`(image を名乗るが物理量を運ぶ op)を正本として引く。

**判定が ok でないときだけ**、入出力を左右に並べた 96 px の小図が `resource_link` で
自動で付く(`vision="thumb"` で強制、`"none"` で抑止)。パイプラインでは**最初に割れた段**の
1 枚だけ —— 知りたいのは「どの段で壊れたか」だから。

## 黙って劣化しない(strict 既定)

fullseye には fail-soft 層があり、op が失敗しても型の合う値が返る。MCP では**既定を strict**
(`on_error="raise"`)にし、劣化したら**拒否して理由を返す**。`allow_degraded=true` を明示した
ときだけ fail-soft を許し、そのときは `degraded` に「どの op が・どの層で・なぜ」を必ず載せる
(空でも `[]`)。

## fail-closed の一覧

| 境界 | 規約 |
|---|---|
| ファイルパス | 根の下だけ。`..` もシンボリックリンクも `realpath` で潰してから比べる |
| op 名 | registry の完全一致のみ。近い名前は**提示するだけ**で、勝手に倒さない |
| 型 | ハンドルの sort ≠ op の in_sort なら拒否。パイプラインは**走らせる前に**全段を検査 |
| つまみ | `a, b ∈ [0,1]`。外は拒否(丸めない) |
| 引数 | スキーマは `additionalProperties: false`。知らないキーは拒否 |
| 結果サイズ | `structuredContent` が 512 KB を超えたら落とし、**落としたと本文と `_meta` に書く** |
| stdout | プロトコル専用。ログ・監査は stderr |

## 検証(どう確かめてあるか)

`tests/test_mcp_server.py` / `tests/test_mcp_images.py`(66 件):
subprocess で**本物の stdio を往復**させ、stdout にプロトコル以外の 1 バイトも無いことまで見る。
拒否はそれぞれ**狙った文言**で落ちることを本文で判定する。小図は実際に開いて高さと非黒を見る。
`--demo` は同じ経路を人が目で見る用。

## 設計の出どころ

RAD(agents コーパス)の 4 本 —— TheMCPCompany(18,000 tool は retrieval が要る)、
MCP-Universe(GPT-5 でも 43.7 %、ボトルネックは long-context と unknown tools)、
Self-Healing Router(失敗は必ず記録か昇格、**沈黙のスキップにしない**)、
Function Hijacking(tool 選択の乗っ取り ASR 70〜100 %)—— と、TRIZ の分離原理
(画像は「在らねばならない」かつ「在ってはならない」→ 時間で分離 + #25 セルフサービス)。
画像処理ライブラリを MCP で公開した先行例は、8 コーパスを引いて 0 件だった(2026-09-15)。

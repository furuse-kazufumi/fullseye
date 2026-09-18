# Fullseye を MCP(Model Context Protocol)から使う

Claude Code / Claude Desktop などの MCP クライアントから、fullseye の op を**探し、
使い方を読み、実際に走らせる**ための stdio サーバ。0.1.11 で PoC として入った。

```
py -3.11 -m fullseye.mcp             # stdio サーバ(クライアントが起動する)
py -3.11 -m fullseye.mcp --demo      # 自分を起動して一通り叩く(下の出力が出れば動いている)
py -3.11 -m fullseye.mcp --coverage  # カタログ 5 層の被覆を JSON で
```

**wheel から動く(0.2.0〜)**。0.1.11 はカタログの正本 `docs/OP_INDEX.json` と知識層
`docs/ops/**/*.md` をリポジトリ相対で読んでいたので、`pip install fullseye` した環境からは
`CatalogError` で止まっていた(理由つきで止まるのは正しいが、動かない)。いまは
`tools/gen_mcp_data.py` が **索引の複製**と**ノートの frontmatter だけ**(op / dim /
category / in / out / halcon + 相対パス、本文は入れない)を `fullseye/data/OP_INDEX.json` /
`fullseye/data/OP_NOTES.json` に書き、package-data として wheel に入る(約 0.8 MB)。
読む順は 索引 = パッケージ内 → リポジトリ `docs/` → **無ければ `CatalogError`**、
ノート = リポジトリ `docs/ops`(正本、本文も読める)→ パッケージ内の frontmatter → `CatalogError`。
どこから読んだかは `fullseye_catalog_coverage` の `index_source` / `notes_source` に出る。
wheel ではノート本文の代わりに同梱の Studio help HTML(`studio_assets/op_help/`)を返し、
返り値の `note_body_unavailable` にそう書く(黙って代替に落ちない)。図は「入力 → 出力」の
1 枚(`op_help/fig/`)だけになり、つまみの掃引図(`docs/ops/_fig/`)は checkout でだけ付く。

複製なので**ずれる**。`py -3.11 tools/regen_all.py --check`(CI で回る)と
`tests/test_mcp_server.py` が「複製 = 正本」を件数ごと数え、`tests/test_mcp_wheel.py`
(`FULLSEYE_WHEEL_GATE=1` で有効)が wheel を建てて別 venv に入れ、リポジトリの外の cwd から
起動して索引 1,942 / ノート 1,942 が返ることを配布物の側で数える。

## Claude Code への登録

```
claude mcp add fullseye -- py -3.11 -m fullseye.mcp
```

`pip install fullseye` した環境でも checkout でも同じ。checkout なら `docs/ops` の
ノート本文と掃引図まで届く(cwd は問わない —— パッケージの位置から解決する)。
読み込める画像は既定で**同梱サンプルだけ**。自分の画像を読ませるには根を足す:

```
set FULLSEYE_MCP_ROOT=C:\path\to\images;D:\more   (PowerShell: $env:FULLSEYE_MCP_ROOT = "...")
```

## tool は 9 つ(op は 1,942 あるが tool にはしない)

op はデータで、tool は「探す・読む・読み込む・走らせる・観察する」の数個だけ。
tool を 1,942 個並べると LLM の文脈を食い潰す(TheMCPCompany の実測: 18,000 tool は
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
| `fullseye_fix_text` | 画像の中の文字を「本当はこう書いてあるべき文字列」に合わせて直す。行ごとに `{text, bbox}`、`mode=repair_flagged`(床を超えた字だけ置換、正しい字に触らない)/ `rewrite_line`(行を丸ごと同じ書体で描き直す)。直した画像はハンドル + 全解像度 PNG、報告に `status` / `reason_code` / `mismatch`(typo か unrelated = 元の字が指示と無関係な疑い)。検証を通らない置換は元に戻す |

## 文字を直す(`fullseye_fix_text`)の呼び出し例

画像は `fullseye_load_image` を `color=true` で読んでハンドルにし、行ごとに「本当はこう
書いてあるべき文字列」と行に密着した bbox を渡す。Python の `fullseye.glyph_correct_spec`
と**同じ items**(能力ノート [`fix-text-in-images`](capabilities/fix-text-in-images.md)、
例 [`examples/fix_text_in_image.py`](../examples/fix_text_in_image.py))。

```json
{"method": "tools/call", "params": {"name": "fullseye_fix_text", "arguments": {
  "handle": "fullseye://img/2c1e7a90b3d4f5e6",
  "items": [{"text": "電気設備", "bbox": [24, 40, 384, 96]}],
  "mode": "repair_flagged"}}}
```

返り値(本文の抜粋。`structuredContent.report` に行ごと・マスごとの全記録、`fixed_png` に
**全解像度の PNG のパス**、`resource_link` にも同じファイル):

```
fix_text(mode=repair_flagged, 床=0.0505 from typeface, 書体 3 本) → fullseye://img/9f0c…
- replaced            電気設備         ・・◆・  mismatch=typo(1.90 倍)
記号: ・無事 ◆直した ×検証不通過(元に戻した) ?直せない。unrelated は「元の字が指示と無関係」の疑い
```

* `mode="rewrite_line"` は行を丸ごと同じ書体で描き直す(見逃し・字数違いも直るが書体は変わる)。
* `bbox` は省ける(全行そろえて)。暗い字の行を上から検出して items の順に当て、使った bbox と
  `layout` を返す。版面が取れなければ `isError` で断る(黙って外れた箱で直さない)。
  Python では `fullseye.glyph_make_spec(rgb, texts)` が同じ指示書を返す。
* 直せない行は `skipped` + `reason_code`(`missing_text_or_bbox / bbox_too_small / empty_text /
  no_font / no_ink / empty_cell / multimodal_colour / cannot_replace / no_lines / layout_implausible`)。縁取り・影の文字は
  `multimodal_colour` で断り、画像は触らない。
* `mismatch=unrelated`(壊れたマスの距離の中央値が床の 2 倍以上)のときは、描き直しが成功して
  いても**指示か画像のどちらかが違う**疑いなので、前後対比の小図を自動で付ける(`vision=auto`)。
* 灰色のハンドル、bbox の長さ違い、数でない要素、未知の `mode` は `-32602` で入口で拒む。

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

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

## 最小プロファイルは10道具(opはデータとして検索する)

op はデータで、tool は「探す・読む・読み込む・走らせる・観察する」の数個だけ。
tool を 1,942 個並べると LLM の文脈を食い潰す(TheMCPCompany の実測: 18,000 tool は
retrieval 無しでは使えない)。

| tool | 何をするか |
|---|---|
| `fullseye_search_ops` | 名前・HALCON 名・カテゴリ・次元の部分一致。返り値の `sources` が出どころ(index / registry / ledger / note / facade)、`by_sources` が層別の内訳 |
| `fullseye_find_ops` | やりたいことの言葉で探す。候補ごとに loader + pipeline の次呼び出し骨格を返す。直接0件なら業務表現の英語候補と型同義語で再検索し、`retry_queries` / `retry_ops` を同じ応答に載せる。`limit`(既定 7)は提案の総数: レシピは最大 `find_ops_recipe_max`(2)件で op の枠を必ず 1 つ残し、残りが op。limit を増やして op が減ることはない |
| `fullseye_plan` | have・want・goalから型付きDAGを返す。「暗い欠陥」「照明むら」「細い傷」等がop説明に一致したときは、`evidence` に一致語・op・説明・固定加点を返す |
| `fullseye_describe` | sort・op・族を1件だけ説明する |
| `fullseye_op_cards` | 候補 op の短いカードを token 予算内で返す。カードの途中では切らない |
| `fullseye_suggest_pipeline` | 検索候補が一意なときだけ、カードと検証済み一段pipeline案を一手で返す。曖昧なら`candidate_not_unique`で選ばない |
| `fullseye_validate_pipeline` | op 名、型連鎖、a/b の範囲、段数を実行せず検査し、段番号つきの理由と候補を返す |
| `fullseye_op_help` | op の知識層ノート(使い方・つまみ a/b の実効・HALCON 相当)+ 生成済みで実行が検証された図を `resource_link` で |
| `fullseye_catalog_coverage` | カタログ 5 層の交差。検索がどれだけの機能を見えているか |
| `fullseye_list_samples` | `samples` = 同梱サンプル(来歴・ライセンスつき)、`files` = 作業場所(`FULLSEYE_MCP_ROOT`)の読める画像の名前(根からの相対名、根の直下と 1 段下まで、`.` で始まる名前は出さない、最大 200 件)。どちらも `load_image` の `path` にそのまま渡せる。ホストのパスは出さない |
| `fullseye_load_image` | 画像 → ハンドル。画素は返さず、数値統計 + 判定。無い名前・読めない拡張子は、読める名前(作業場所のファイル名と同梱サンプル名)を近い順に 8 件まで添えて断る(根の外のパスには添えない) |
| `fullseye_load_template` | 位置決め用の登録見本 → ハンドル。`fullseye_pipeline.template_handle`へ明示的に渡す |
| `fullseye_load_stack` | 複数画像 → `images` / `seq<image>` / `polsweep` の束ハンドル |
| `fullseye_apply` | ハンドルに op を 1 つ。出力ハンドル + 数値統計 + 判定 + 劣化台帳 |
| `fullseye_pipeline` | op を順に。段ごとに記録、型連鎖は走らせる前に検査、strict は失敗段で停止 |
| `fullseye_inspect` | ハンドルの数値統計 + 判定(+ 小図) |
| `fullseye_fix_text` | 画像の中の文字を「本当はこう書いてあるべき文字列」に合わせて直す。行ごとに `{text, bbox}`、`mode=repair_flagged`(床を超えた字だけ置換、正しい字に触らない)/ `rewrite_line`(行を丸ごと同じ書体で描き直す)。直した画像はハンドル + 全解像度 PNG、報告に `status` / `reason_code` / `mismatch`(typo か unrelated = 元の字が指示と無関係な疑い)。検証を通らない置換は元に戻す |
| `fullseye_import_json` | 型付きの値を **JSON 封筒で引数に受け取り**、以後の op が使えるハンドルにする。`json`(文字列)か `envelope`(オブジェクト)のどちらか一方。配列 sort(image / color / region / points / matrix …)はハンドルに、feature / contour / table は値を返す。壊れた封筒・未知 sort は `-32602` |
| `fullseye_export_json` | ハンドルの中身を **JSON 封筒で持ち出す**。`structuredContent` に `fullseye.from_jsonable` で bit そのまま戻せる封筒、本文に `fullseye.to_markdown` の読める描画。`readable=true` で数をリストに。上限(512 KB)超の大きな画像は `isError` で断る(画像はハンドル/小図で扱う) |
| `fullseye_write_viewer` | PoC の結果を**自己完結した 1 枚の HTML ビューア**にして書く(タブ・正直なバッジ `passed` / `limit` / `null`・数字・3-D の点群/メッシュ・2-D 動画と時系列・前後の分割・ja/en/zh/tw/ko/de/hi/fr の切り替え)。`spec`(JSON)・`lang`(言語の配列、先頭が既定)・`name`。`spec` は信頼境界で再検証し、形違い・NaN・未知のバッジ/種類・欠けた訳は `-32602`。書き先はサンドボックスだけで、`resource_link` で返す |
| `fullseye_estimate_distortion` | 本来まっすぐな**線群の点列**(`lines`=`[[x,y],…]` を並べた配列、2 本以上・各線 3 点以上)と 3x3 内部行列 `K` から Brown–Conrady 歪み係数 `dist=[k1,k2,p1,p2,k3]` を推定(plumb-line 法、チェッカー不要)。`radial`=1/2/3、`tangential` 真偽。返す `dist` は `undistort_image` にそのまま渡せる。`lines`/`K` は信頼境界で再検証し、形が違えば `-32602`、推定不能は `isError` |
| `fullseye_make_task` | **真値付きの課題**を作る(`kind` = 族、`seed`、`params` = 族ごとの難度つまみ)。返すのは入力画像のハンドル・課題文・出力の型と単位・指標と許容範囲・`task_id`。**真値はサーバが持ち、返さない**。同じ `(kind, seed, params)` からは同じ課題・同じ `task_id`。知らない族・つまみ・範囲外は `-32602` |
| `fullseye_score_pipeline` | `task_id` と `fullseye_pipeline` と同じ形の `stages` を受け、課題の入力で走らせて**真値で採点**する。型の門を先に通し、指標ごとの誤差の大きさ・許容範囲・合否と外れ方の説明を返す(真値と誤差の符号は返さない)。例外・型の不一致・NaN / 空 / 定数の出力・知らない / 期限切れの `task_id` は合格を返さず `reason` を書く |

小さな LLM は、候補を絞ってから短い説明だけを渡す。推奨順は
`find_ops / plan → op_cards → validate_pipeline → pipeline`。

```json
{"name":"fullseye_plan","arguments":{"have":"image","want":"feature","goal":"count connected defects"}}
{"name":"fullseye_op_cards","arguments":{"names":["otsu","count_obj"]}}
{"name":"fullseye_validate_pipeline","arguments":{"start_sort":"image","stages":[{"op":"otsu"},{"op":"count_obj"}]}}
```

## 名前つき物理量・見本ハンドル・一手のpipeline案

画素単位の窓、σ、半径は `params` の名前で渡す。対象と範囲は `param_specs.py` の
op台帳 `MCP_PHYSICAL_PARAMS` から列挙され、現在は14 opである。例: `gaussian.sigma_px`
は0.3〜3.0 px、`sk_rolling_ball.radius_px`は5〜25 px、top-hat系の`window_px`は
3/5/7/9 px。範囲外や選択肢外はMCP境界で理由つき拒否し、丸めもclipもしない。

```json
{"name":"fullseye_pipeline","arguments":{"handle":"fullseye://img/<scene>","stages":[{"op":"gaussian","params":{"sigma_px":1.2}}]}}
{"name":"fullseye_suggest_pipeline","arguments":{"query":"gaussian","start_sort":"image","goal_sort":"image"}}
```

位置決めopは見本を暗黙の状態から読まない。見本を読み、返ったハンドルを同じpipeline呼び出しに渡す。
`ncc_locate` / `shape_locate`で`template_handle`を省くと`missing_template_handle`で停止する。

```json
{"name":"fullseye_load_template","arguments":{"path":"template.npy","vision":"none"}}
{"name":"fullseye_pipeline","arguments":{"handle":"fullseye://img/<scene>","template_handle":"fullseye://img/<template>","stages":[{"op":"ncc_locate"}],"vision":"none"}}
```

ローカルで実際に動かす一式は [`examples/mcp_usability.py`](../examples/mcp_usability.py)。


`find_ops` の `probe` は既定入力での試し実行結果である。
失敗は「その入力では動かなかった」という選択材料であり、op 自体の故障とは断定しない。

## 触って見るビューアを書く(`fullseye_write_viewer`)

PoC の結果を、自己完結した 1 枚の HTML(タブ・正直なバッジ・3-D の点群/メッシュ・2-D 動画・前後の分割・言語切り替え)にして書く。Python の `fullseye.write_viewer` と同じ門を通る(能力ノート [`interactive-poc-viewer`](capabilities/interactive-poc-viewer.md)、例 [`examples/interactive_poc_viewer.py`](../examples/interactive_poc_viewer.py))。

```json
{"method": "tools/call", "params": {"name": "fullseye_write_viewer", "arguments": {
  "lang": ["ja", "en"],
  "spec": {"id": "demo", "title": {"ja": "見本", "en": "Demo"}, "subtitle": {"ja": "副題", "en": "Subtitle"},
           "hint": {"ja": "操作", "en": "Hint"},
           "tabs": [{"id": "a", "kind": "points", "badge": "null",
                     "label": {"ja": "点群", "en": "Points"}, "text": {"ja": "説明", "en": "Text"},
                     "pos": [[0, 0, 0], [1, 0, 0], [0, 1, 1]], "val": [0.0, 0.5, 1.0],
                     "cbar": {"lo": 0, "hi": 1, "unit": "mm"}}]}}}}
```

* `spec` は **untrusted として信頼境界で再検証**する。形が違う・NaN・未知のバッジ(`passed` / `limit` / `null` 以外)・未知の `kind`・空の `tabs`・要求した言語の訳が 1 つでも欠ける、は `-32602`(欠けた鍵を全部並べる。他の言語で補わない)。
* 書き先は MCP のサンドボックスの作業ディレクトリだけ(`name` は英数字と `_` `-`、`..` や `/` は拒否)。返り値の `resource_link`(`text/html`)でファイルを受け取る。
* 対応言語は ja / en / zh / tw / ko / de / hi / fr。URL の `?lang=xx` と `?tab=<id>` で開く言語とタブを選べる。

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
- replaced            電気設備         ・・◆・  mismatch=typo(壊れ 25 %, 距離 0.099)
記号: ・無事 ◆直した ×検証不通過(元に戻した) ?直せない。unrelated は「元の字が指示と無関係」の疑い
```

* `mode="rewrite_line"` は行を丸ごと同じ書体で描き直す(見逃し・字数違いも直るが書体は変わる)。
* `bbox` は省ける(全行そろえて)。暗い字の行を上から検出して items の順に当て、使った bbox と
  `layout` を返す。版面が取れなければ `isError` で断る(黙って外れた箱で直さない)。
  Python では `fullseye.glyph_make_spec(rgb, texts)` が同じ指示書を返す。
* 直せない行は `skipped` + `reason_code`(`missing_text_or_bbox / bbox_too_small / empty_text /
  no_font / no_ink / empty_cell / multimodal_colour / cannot_replace / no_lines / layout_implausible`)。縁取り・影の文字は
  `multimodal_colour` で断り、画像は触らない。
* `mismatch=unrelated`(壊れたマスが 2/3 以上で、距離の中央値も 0.10 以上)のときは、描き直しが
  成功していても**指示か画像のどちらかが違う**疑いなので、前後対比の小図を自動で付ける(`vision=auto`)。
* 灰色のハンドル、bbox の長さ違い、数でない要素、未知の `mode` は `-32602` で入口で拒む。

## JSON で値を出し入れする(`fullseye_import_json` / `fullseye_export_json`)の呼び出し例

型付きの値(点群・行列・小さな画像・region …)を JSON 封筒で **MCP に注入**したり、ハンドルの中身を
**JSON で持ち出す**。封筒は `fullseye.to_json` / `fullseye.to_jsonable` が作る自己記述の形
(能力ノート [`typed-results-as-json`](capabilities/typed-results-as-json.md)、例
[`examples/typed_results_json.py`](../examples/typed_results_json.py))。

```json
{"method": "tools/call", "params": {"name": "fullseye_import_json", "arguments": {
  "envelope": {"fullseye_sort": "points", "version": 1,
               "payload": {"encoding": "list", "dtype": "float64",
                           "shape": [2, 2], "data": [[1.5, 2.0], [3.25, 4.0]]}}}}}
```

返り値の `structuredContent` に `handle` / `sort` / `shape`(配列 sort のとき)。以後は `fullseye_apply`
などにそのハンドルを渡せる。取り出しは:

```json
{"method": "tools/call", "params": {"name": "fullseye_export_json",
  "arguments": {"handle": "fullseye://img/1524e3d5c6e2dc59", "readable": true}}}
```

* 封筒は **untrusted として毎回再検証**する(`from_jsonable` が fail-closed。壊れた封筒・版違い・
  形の不一致・未知 sort は `-32602`)。`import_json` は `json` と `envelope` の両方または両方無しを断る。
* `export_json` は封筒が上限(512 KB)を超えると `isError` で断る —— 大きな画像は JSON で持ち出さず、
  ハンドルのまま `fullseye_apply` で回すか小図で見る。`sort` が JSON にできないハンドルも断る。
* Python では同じ橋を `fullseye.apply_json(image, op, a, b)`(JSON 入力 → op → JSON 出力)や
  `fullseye.as_value(x)`(値でも封筒でも受ける引数入口)で使える。

## 直線群から歪み係数を推定する(`fullseye_estimate_distortion`)の呼び出し例

本来まっすぐな線(印刷線・建物のエッジ・定規)がレンズで曲がった**点列**だけから、Brown–Conrady
歪み係数を推定する(チェッカーボードの対応点は不要。能力ノート
[`estimate-lens-distortion`](capabilities/estimate-lens-distortion.md)、例
[`examples/estimate_lens_distortion.py`](../examples/estimate_lens_distortion.py))。

```json
{"method": "tools/call", "params": {"name": "fullseye_estimate_distortion", "arguments": {
  "lines": [[[12.0, 41.3], [40.0, 40.2], [100.0, 40.0], [188.0, 41.8]],
            [[41.0, 12.4], [40.2, 100.0], [41.9, 188.0]]],
  "K": [[190.0, 0.0, 99.5], [0.0, 190.0, 99.5], [0.0, 0.0, 1.0]],
  "radial": 2, "tangential": false}}}
```

返り値の `structuredContent.dist` が `[k1, k2, p1, p2, k3]`。そのまま `undistort_image` に渡せる。

* `lines`(各線 `[[x,y],…]`)と `K` は **untrusted として信頼境界で再検証**する —— `K` が 3x3 でない、
  線が `(N,2)` でない、非有限が混ざる、線が 2 本未満は `-32602`。各線 3 点未満など道具側の拒否は `isError`。
* 主点=歪み中心は `K` 固定(1 枚では中心と `p1,p2` が縮退)。向きの違う線を混ぜ、画面いっぱいに張るほど安定。

## 真値付きの課題を作り、組んだ処理を採点する(`fullseye_make_task` / `fullseye_score_pipeline`)

> **使い方の範囲(2026-11-10、独立レビュー第 3 巡)**
>
> 1. **公開モードは、対話で処理を直させるための道具。能力の比較(LLM+Fullseye / LLM だけ / 人)には使えない。**
>    公開の生成器と返された `seed`・`params` から真値も隠れた双子の入力も計算でき、`detailed` の誤差の大きさからは
>    真値を符号の 2 択まで絞れるため。
> 2. **結果は pass@k で報告し、pass@1 は必ず添える。** 合格したかだけでなく、合格までに使った試行回数 k(監査記録の
>    `attempt`)を添え、pass@1 と pass@k を並べる。32 回まで出し直せるので、合否だけでも選び直しの経路になる。
>    直した後も残る数字(独立レビュー第 5 巡): 半分しか正しくない処理(照明むらを補正しない計数)が、32 回以内に
>    合格する課題が 20 課題中 9 課題ある。そうして合格した処理は、別の seed では 50 課題中 3〜38 課題にしか合わない。
>    pass@k だけでは「出し直せば通った」ことと「処理が正しい」ことを区別できない。
> 3. **隠れた双子の検査は、正しい処理も断ることがある。** 正しい処理を seed 50〜99 で数えると、誤って断った率は
>    計数・寸法・位相で 0/50(公開・実験の両モード)、キズ(比較実験から外した族)で公開 3/49、実験 5/42
>    (双子を試行ごとに替えた後、1 回目の試行)。実験モードの率は秘密値で変わる(課題も双子も秘密値で決まるため。
>    キズは秘密値と版によって 3/42、4/49、5/42 になった)。
> 4. **入力に依存しない op の一覧は既定のつまみだけで判定している。** つまみの端で定数になる op は一覧に載らない
>    (隠れた双子の検査で補う)。一覧に無いことは、その op が入力に依存する保証ではない。
> 5. **回数ファイル(`<AUDIT_PATH>.attempts.json`)と監査ファイルは、agent が読めず書けない場所に置く。** 回数ファイルを
>    消せば新しいセッションの回数が戻り、監査ファイルには詳しい誤差がある。
>
> **実験モードは、独立レビューで測り終えるまでは比較実験に使わない。**

「LLM が組む → 型の門 → 実行」だけでは、型は合うがもっともらしく間違った処理(照明むらを大域の
二値化で拾う、位相を展開し忘れる、しきい値の高さで端を測る)を落とせない。この 2 つの道具は、
シミュレーションで真値の決まる課題を作り、組んだ処理の**出力**を真値と比べて数値で採点する。
走る一式は [`examples/mcp_task_score.py`](../examples/mcp_task_score.py)(LLM の役を手書きの処理で演じる)。

```json
{"name":"fullseye_make_task","arguments":{"kind":"blob_count","seed":11}}
{"name":"fullseye_score_pipeline","arguments":{"task_id":"fullseye://task/<16 hex>","stages":[{"op":"gaussian"},{"op":"tophat","params":{"window_px":9}},{"op":"otsu"},{"op":"count_obj"}]}}
```

| 族 (`kind`) | 分野 | 入力 | 採点する出力 | 指標と許容範囲 |
|---|---|---|---|---|
| `blob_count` | 二値化と計数 | 照明むらのある板の粒(image 128×128) | feature(スカラー) | 数え違い = 0 |
| `edge_subpixel` | サブピクセルの寸法 | ぼけた水平の帯(image 96×64) | contour / points / matrix の `[row, col]` | 上端・下端の位置の誤差 ≤ 0.15 px |
| `defect_inspect` | キズの検出 | 加工目のある面の暗い打痕(image 128×128) | region | 重心の誤差 ≤ 1.5 px、面積の相対誤差 ≤ 0.30、1 − IoU ≤ 0.40 |
| `fringe_phase` | 3-D 計測(位相シフト) | 4 歩の縞(seq<image> 4×64×96) | image / depth(連続位相、rad) | rms(大域の 2πm は許す)≤ max(0.05, 3σ) rad |

* **許容範囲は事前登録。** 値と根拠は [`fullseye/mcp/task_tolerances.py`](../fullseye/mcp/task_tolerances.py)。
  許容・指標・根拠を変えるときは、その表だけの commit を先に作り(採点の結果・合格数はまだ含めない)、
  同じ commit で `SCORING_VERSION` を上げる。その後の commit で実装と結果を足す(比較実験の事前登録)。
  キズの族の IoU(1 − IoU ≤ 0.40)はこの作法で、IoU を 1 つも測る前に登録した。
* **段が読めるのは課題の入力と前段だけ。** 段の `inputs` と `params` の `{"ref": …}` に書けるのは
  `have:<課題の入力の型>` と `stage:N` だけで、他の `fullseye://` ハンドル(`fullseye_import_json` で取り込んだ答え、
  他の課題の入力)は `foreign_input` で断る。入力を読まない段(生成源)と、課題の入力に依存の経路で
  辿り着かない最終段も `foreign_input`。入力は課題の画像に固定で、`handle` は渡せない。
* **入力の中身を読まない処理は断る(`input_independent`)。** 生成の op(`hx_gen_checker_region` /
  `hx_gen_ellipse` など)は `have:` を形のためだけに読むので、参照を辿る門は通ってしまう(画像を見ない処理で
  計数の 50 課題中 9 課題が 3 回以内に合格した)。2 段で断る: (1) 実行できる 1 入力の op を中身の違う 7 枚に
  通して出力が同じ物を機械的に洗い出した一覧
  ([`fullseye/data/MCP_INPUT_INDEPENDENT.json`](../fullseye/data/MCP_INPUT_INDEPENDENT.json)、
  `tools/gen_mcp_input_independent.py`、既定のつまみで判定)にある op を断る。(2) 採点のたびに、同じ族・同じ
  つまみで真値の違う隠れた双子の課題で同じ処理を走らせる。最終段の出力がバイト単位で同じなら `input_independent`、
  本体が合格したのに双子の真値には合格しなければ不合格(固定の答えは真値の違う 2 つの課題の両方には合格できない)。
  双子の側の誤差は返さない。走り切らなければ `input_check_failed`。
  - **双子の決め方**: `sha256("alt|<kind>|<seed>|<k>|" + 秘密値の要約 [+ "|attempt=<n>"])` の先頭 4 バイトを seed の範囲に
    畳み、k = 1, 2, … の順に、真値が本体とどの鍵でも違う最初の seed を使う。公開モードは秘密値が空で試行の番号も
    混ぜない(公開の生成器から計算できる)。実験モードは秘密値と試行の番号を混ぜ、**試行ごとに双子を替える**。
  - **reason の出し分け**: `detailed` では双子で落ちたことを `hidden_check_failed` で返す(対話で直すため)。
    `pass_fail` / `coarse` では区別せず、許容外の不合格と同じ `out_of_tolerance` と同じ形で返す(`coarse` の段階は
    落ちた側 = 双子の指標から作る)。区別は監査記録の `hidden_seed_check` にだけ残す。区別して返すと
    「本体には合っていた」ことが分かり、本体と双子の探索を 2 回に分けられた(独立レビュー第 4 巡: 計数の
    20 課題中 13 課題が 20 回以内に合格)。試行ごとに双子を替えるのも、この分けた探索を効かなくするため。
* **params の値は 数・文字列・真偽・null と `{"ref": have|stage}` だけ**(`param_not_allowed`)。配列や入れ子の辞書で
  データを持ち込めない(`decode_fringe` の `ref_phase` に配列を書いて答えを注入できた)。
* **採点の回数は真値ごと。** 真値は `(kind, seed)` で決まり、難度のつまみ(`params`)は入力を変えても真値を変えない
  (どの族もテストで確かめている)。だから回数は `(kind, seed)` ごとに 32 回までで、課題を作り直しても・つまみを
  微小に変えても・他の課題で追い出されても・寿命(3,600 秒)が切れても戻らない。雑音 0 の「双子」の課題も
  同じ真値なので回数を共有する(易しい双子で解いた処理を難しい側に出すことは止めない —— それは同じ真値への
  正当な解答)。回数の表は、公開モードでは 1 セッション(1 つのサーバ・プロセス)の中で数え、実験モードでは
  ファイルに残してセッションをまたいで数える(下)。作れる真値は 1 セッションで 4,096 個まで。
* **返す細かさ(`feedback`)。** `detailed`(既定)は指標ごとの誤差の大きさ・許容・倍率・合否と外れ方の説明。
  `coarse` は指標ごとの合否と許容の何倍か(`<=1x` / `<=2x` / `<=5x` / `>5x`)だけ。`pass_fail` は全体の合否だけ。
  詳しい値は `FULLSEYE_TASK_AUDIT_PATH` の監査記録(JSON Lines)にだけ書く。**stderr には task_id・試行回数・合否
  だけ**を出す(MCP のクライアントは stdio サーバの stderr をファイルに残すので、ファイルを読める agent が誤差を
  読めてしまう)。サーバの上限(環境変数 `FULLSEYE_TASK_FEEDBACK`)より詳しい要求は上限まで粗くし、
  `feedback_capped: true` を付ける。
* **2 つのモード。** 公開モード(既定)は誰でも同じ課題を作り直せる —— 公開の生成器と返された `seed`・`params` から
  真値も作り直せる(再現のための性質で、採点の秘匿にはならない)。比較実験には実験モードを使う:
  環境変数 `FULLSEYE_TASK_SECRET` を設定すると、その秘密値を乱数の種と `task_id` に混ぜ、公開の生成器では
  作り直せなくなる。秘密値は返り値にも記録にも出さない。実験モードの `feedback` の上限は既定で `pass_fail`、
  `scoring_version` の末尾に `+secret` が付く。実験モードは次が揃わないと課題を作らない(fail-closed):
  秘密値が 32 文字以上、`FULLSEYE_TASK_AUDIT_PATH`(実験者だけが読む場所。MCP の根の外)がある。
  採点の回数は `<AUDIT_PATH>.attempts.json` にも残し、**セッションをまたいで**数える。読み書きは
  `<AUDIT_PATH>.attempts.json.lock` への OS のファイル lock(Windows は `msvcrt.locking`、他は `fcntl.flock`)で守る。
  持ち主のプロセスが落ちれば OS が lock を外すので、古い lock を消す判断は要らない(以前の O_EXCL + 時刻の方式は、
  古い lock を 2 つのプロセスが続けて消すと回数が 1 つ減った)。取れなければ 10 秒で `attempt_store_unavailable`。
  中身が壊れた回数ファイル(数でない・負・小数)や書けない回数ファイルも `attempt_store_unavailable` で断る
  (推測で読まない。返す文にファイルの場所は入れない)。
  **秘密値と監査記録は agent のシェルから見えない場所に置く**: 秘密値はサーバのプロセスの環境だけ
  (例: `.mcp.json` の `env`)に書き、agent が使うシェルの環境変数やファイルには置かない。
* **比較実験の報告は pass@k で。** 合否だけでも、32 回まで出し直せば選び直しの経路になる。合格したかだけでなく、
  合格までに使った試行回数 k(監査記録の `attempt`)を添え、pass@1・pass@k(k = 使った回数の上限)を並べて報告する。
* 採点の返り値は誤差の**大きさ**だけで、符号と段の出力の値・統計は載せない。ただし `detailed` では、誤差の大きさと
  自分の出力を合わせれば真値は符号の 2 択まで絞れる(計数は特に)。秘匿が要る場面では `coarse` / `pass_fail` を使う。
* 採点できた不合格は `passed: false`・`reason: out_of_tolerance`・`isError: false`。採点が成り立たない不合格は
  `isError: true` で、`reason` は `foreign_input` / `param_not_allowed` / `input_independent` / `hidden_check_failed` /
  `input_check_failed` / `attempt_store_unavailable` / `type_gate` / `output_sort_mismatch` / `pipeline_refused` /
  `exception` / `execution_failed` / `invalid_output`(NaN・Inf)/ `empty_output` / `constant_output` /
  `output_shape_mismatch` / `unscorable_output` / `unknown_task` / `task_expired` / `attempts_exhausted` のどれか。
* 実行は `fullseye_pipeline` と同じ実行器(同じ検証済みの op だけ、CPU)。
* **比較実験に使える族は `blob_count` / `edge_subpixel` / `fringe_phase` の 3 つ**(`fullseye.mcp.tasks.COMPARISON_FAMILIES`、
  課題の返り値の `comparison_ready`)。**`defect_inspect` は正誤の分け方が弱い**: 加工目を処理しない処理
  (反転 → 最大エントロピーの二値化 → 最大の領域)が seed 0〜49 で 20/50、seed 50〜249 で 78/200 合格する。
  IoU(1 − IoU ≤ 0.40、事前登録)を足しても変わらなかった。落とせる閾値を結果を見てから選ぶと門を結果に
  合わせて動かすことになるので、許容は締めずに比較実験から外した(課題の返り値の `known_weakness` にも書く)。
  族の作り直し(加工目を強くする等)は v2 として、新しい seed の範囲で事前登録してから測る。
* 正しい処理の選び方(テストと例の処理): 窓幅など(top-hat 9 px、横 7 px の平均)は **seed 0〜49 で選んだ**(調整用)。
  選んだ後に別の seed 50〜249 で数え直した合格数は、正しい処理が計数 200/200・寸法 200/200・キズ 192/200・
  位相 200/200、もっともらしく間違えた処理は 4 族とも 0/200。加工目を処理しない処理(反転 → 最大エントロピーの
  二値化 → 最大の領域)はキズの族で 78/200 が合格する(IoU を足しても変わらない。下の CHANGELOG を参照)。

## 型付き結果に JSON 封筒 + Markdown が自動で付く(`fullseye_apply` / `fullseye_pipeline` / `fullseye_inspect`)

`apply` / `pipeline` / `inspect` の結果が**小さい型付きの値**(scalar / feature / table / points / matrix /
signal / vector / keypoints / counts / contour)のとき、`structuredContent.json` に `fullseye.from_jsonable`
で **bit そのまま戻せる封筒**が、本文に `fullseye.to_markdown` の**読める描画**(表または 1 行要約)が
自動で付く。画素・場・ボリューム系(image / volume / region / color …)や上限(512 KB)超は**付けない**
—— 大きい画像はハンドル/小図で扱う(`fullseye_export_json` と同じ判断)。追加情報なので既存の返り
(`handle` / `value` / `stats` …)はそのまま。例: `count_obj` で終わるパイプラインは `structuredContent.json`
に `{"fullseye_sort":"scalar",…}` が入り、`from_jsonable` で数値を厳密に回収できる。

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

fullseye には fail-soft 層があるが、MCP pipeline は**strict固定**とし、op が失敗したら
拒否して理由を返す。途中までの段階記録は返すが、劣化値を後続段へ流さない。

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
# AI に op を選ばせる短い手順

公開する計画入口は `fullseye_plan`、`fullseye_describe`、`fullseye_choose` の3つだけである。
未計測の制約は推測で補わず、fail-closedの理由として返す。`tools/list` に
`{"profile":"minimal"}` を渡すか、`FULLSEYE_MCP_PROFILE=minimal`を設定すると実行に必要な10道具を公開する。
`docs/mcp_context_benchmark.json`を生成する実測では、全24道具が4,211トークン、最小10道具が1,498トークンである。
未検証の設計パターンと重複した計画入口はMCP一覧に出さない。

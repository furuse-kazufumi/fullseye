# Fullseye Studio 完全ガイド

**Fullseye Studio** は、HDevelop 風のビジュアル・パイプライン・ワークベンチです。オペレータを検索して並べ、2 つのつまみをスライダーで回し、途中結果をズーム/パンで見ながら 1 段ずつ実行し、組み上がったパイプラインを `--ops` 文字列 / Python / JSON として書き出せます。実体は `fullseye` API の薄い GUI フロントで、パイプラインのロジック（`PipelineModel`）・Inspector（`inspect_result`）・サンプル集（`recipes`）はいずれも Qt 非依存で単体テストされています。

このガイドは `studio.py`（`build_window`）を実コードに突き合わせて機能を列挙したものです。UX/デザインの意図は [STUDIO_UX.md](STUDIO_UX.md) に、v14 の知覚パネルの背景は [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md) にあります。

---

## 起動方法

GUI extras（PySide6）が必要です（`pip install -e ".[gui]"`）。

```powershell
py -3.11 studio.py          # リポジトリ直下から直接
fullseye-studio             # pip install -e . 済みなら、コンソールスクリプトで
```

起動すると 1320×860 のメインウィンドウが開きます（タイトル: Fullseye Studio）。`assets/fullseye.ico` があればウィンドウ/タスクバーアイコンとして付きます。初期状態では合成デモ画像（`demo_image`、エッジ・ブロブ・グラデーションを含む 256×256）が読み込まれています。

---

## 画面構成（3 パネル）

上部に **メニューバー**（File / Edit / View / Run / Help）と**ブランドツールバー**、下部に **ステータスバー**（ホバー時の座標+画素値、`flash()` の一時メッセージ）。中央は左右分割の 3 パネルです。

| パネル | セクション（QGroupBox） | 役割 |
|---|---|---|
| 左 | **SAMPLE PIPELINES** / **OPERATORS** | サンプル読み込みとオペレータ・ブラウザ |
| 中央 | **PIPELINE** / **SELECTED STAGE · KNOBS** / **EXPORT & I/O** | パイプライン構築・つまみ調整・書き出し |
| 右 | **IMAGE** / **DISPLAY & PERCEPTION (v14)** / **ANALYSIS** | 結果表示・カラーマップ/知覚・ヒストグラム/Inspector |

初期の分割幅は 340 / 360 / 640 px で、右パネルが伸縮します。

---

## 左パネル: Operators ブラウザ

### サンプルパイプライン（SAMPLE PIPELINES）
ドロップダウンから **20 個**の既製レシピ（`recipes.py`）を選ぶと、パイプラインがそのレシピに置き換わります。例: 「Edge — Sobel + Otsu」「Denoise — bilateral + unsharp」「Segment — blob / coin」「Count — blobs」「Texture — Gabor」など。まず動かして中身を見る出発点に便利です。

### オペレータ・ブラウザ（OPERATORS）
- **カテゴリ絞り込み**: 「all categories」＋ 31 カテゴリ（smoothing / edges / morphology / segmentation / features / texture / region / contour / color / frequency / restoration / 3d …）。
- **検索ボックス**: オペレータ名・HALCON エイリアス・カテゴリを部分一致でフィルタ（クリアボタン付き）。
- **一覧**: 各行に `name [in_sort → out_sort]` を表示。**ダブルクリックで挿入**。ホバーすると tooltip で「名前 / HALCON エイリアス / カテゴリ / sort 変換 / つまみ a,b の説明」が出ます。

挿入位置は「選択中の段の直後」。段を選んでいなければ末尾に追加されます。

---

## 中央パネル: パイプライン構築とステップ実行

### PIPELINE（段の一覧）
各行は `N. op (a=…, b=…) -> 結果の要約` の形で、その段まで実行した結果の状態（image/region/feature など）が右側に出ます。

- **並べ替え**: 行をドラッグ（InternalMove）で入れ替え、または **↑ Up / ↓ Down** ボタン・**Ctrl+↑ / Ctrl+↓**。
- **削除**: **Remove** ボタン・**Del**。
- **ステップ実行の 3 ボタン**:
  - **⏮ Reset（Home）** — パイプライン適用前の生画像を表示（ステップスルーの起点）。
  - **Step ▶（Ctrl+→）** — 1 段進める。
  - **Run all ▶▶（Ctrl+Enter）** — 最終結果まで一気に表示（プライマリ・アクセントボタン）。

段を選ぶと、その段までの途中結果が右の IMAGE パネルに描画され、下の ANALYSIS（ヒストグラム / Inspector）も同期します。これが「ステップスルー・デバッガ」に相当します。

### SELECTED STAGE · KNOBS（つまみ調整）
選択中の段の詳細（`op_detail`: 名前・`in → out` sort・カテゴリ・HALCON エイリアス）を表示し、**2 本のスライダー a / b（0.00〜1.00）** で調整します。値を動かすと即座に結果が再計算されます。段を選んでいないときはスライダーは無効化されます（意味のないつまみは死んだ状態にしない設計）。

つまみの意味はオペレータごとに異なります（半径 / しきい値 / σ / 方向など）。何を調整しているかは段の詳細ラベルと tooltip で確認できます。

### EXPORT & I/O
- **Export（ops string + Python）…（Ctrl+E）** — 現在のパイプラインを `--ops "…"` 文字列と、単体で動く Python 関数の両方としてダイアログに出力（コピー用）。
- **Save pipeline…（Ctrl+Shift+S）** — パイプラインを JSON 保存（`{"fullseye_pipeline": 1, "stages": [...]}`）。この JSON が `FullseyeEngine.load` / `imgevolve.py run` の入力になります。
- **Open pipeline…（Ctrl+Shift+O）** — 保存した JSON を読み込み。

---

## 右パネル: 表示・知覚・解析

### IMAGE（結果ビュー）
- **Load image…（Ctrl+O）** — 画像ファイルを基準フレームとして読み込み（png/jpg/bmp/tif）。
- **Synthetic demo（Ctrl+D）** — 合成デモ画像を読み込み。
- **Save result…（Ctrl+S）** — 表示中の結果を PNG 保存。
- **ズーム**: マウスホイールでカーソル位置ズーム、ドラッグでパン。**Zoom +（Ctrl+=）/ Zoom −（Ctrl+-）/ Fit（Ctrl+0）/ 1:1（Ctrl+1）**。
- スカラ feature 結果・contour 結果・画像未読み込みのときは、ビュー中央にメッセージを表示（空表示にしない）。
- ホバー時、ステータスバーに `x, y, value`（カラーなら RGB）を表示。

### DISPLAY & PERCEPTION (v14)
- **Display（カラーマップ）** — 2D 結果を表示用に着色: `gray` / `shaded relief` / `height (color)` / 各カラーマップ（jet, viridis, turbo, magma, plasma, inferno …）。
- **3D surface（Ctrl+3）** — 現在の結果を回転可能な 3D サーフェスで表示（`QtDataVisualization` があるときのみ／best-effort）。高さ/深度マップの確認に。
- **知覚パネル（2 フレーム）** — **Load frame B…** で 2 枚目のフレームを読み込み、モードを選んで **Run**:
  - `optical flow` — 2 フレーム間の密なオプティカルフローを色相で可視化。
  - `motion overlay` — 動いている領域を元画像に重畳。
  - `stereo depth` — ステレオ視差から深度を推定して着色。
  - `stereo terrain` — ステレオ→点群→地形ハイトマップを着色。

  フレーム B が無い/サイズ不一致のときはステータスバーにエラーを出して安全に中断します。

### ANALYSIS
- **Histogram** — 現在の 2D 結果の輝度ヒストグラム。
- **Inspector（variable / image / region）** — 結果を sort に応じて検査。image/color なら shape・min/max/mean・非有限数、region なら連結成分数・面積・最大領域、feature なら値、contour なら輪郭数。二値領域のときは各領域の特徴表（`detect.feature_table`）も併記します。

---

## Command palette（Ctrl+P）

`Ctrl+P` で、**任意のアクションや任意のオペレータを名前で実行**できるファジー検索ダイアログが開きます。先頭一致 > 単語先頭一致 > 部分一致の順にランク付け（`palette_filter`、Qt 非依存で単体テスト済み）。アクション（`▸ Open image` など）が先、続いて全オペレータ（`op: gaussian` など）が並び、Enter で実行します。キーボードだけでオペレータ挿入まで完結します。

---

## キーボードショートカット

アプリ内では **Help ▸ Keyboard shortcuts（F1）** で全一覧が表で出ます（自己文書化）。主なもの（`studio.py` の `act_*` 定義より）:

| 操作 | ショートカット | 操作 | ショートカット |
|---|---|---|---|
| Open image | `Ctrl+O` | Remove stage | `Del` |
| Synthetic demo | `Ctrl+D` | Move stage up / down | `Ctrl+↑` / `Ctrl+↓` |
| Save result | `Ctrl+S` | Clear pipeline | `Ctrl+Shift+Backspace` |
| Open pipeline | `Ctrl+Shift+O` | Zoom in / out | `Ctrl+=` / `Ctrl+-` |
| Save pipeline | `Ctrl+Shift+S` | Fit / Actual size (1:1) | `Ctrl+0` / `Ctrl+1` |
| Export | `Ctrl+E` | 3D surface | `Ctrl+3` |
| Quit | `Ctrl+Q` | Reset to start | `Home` |
| Command palette | `Ctrl+P` | Step forward | `Ctrl+→` |
| Keyboard shortcuts | `F1` | Run all | `Ctrl+Enter` |

各アクションはメニュー・ツールバー・ボタンのいずれからも同じハンドラで呼ばれます（1 動作・複数入口）。

---

## HDevelop `dev_*` 描画制御ディレクティブ

HDevelop と同様に、**描画の挙動をプログラムから制御**できます。Program ウィンドウの
スクリプトに `dev_*` 行を書くと、画像ステージではなく**表示ディレクティブ**として解釈され、
Apply 時に適用されます（`docs/HDEVELOP_DEV_OPS.md` に全 43 `dev_*` の網羅把握）。

| ディレクティブ | 効果 | 対応 UI |
|---|---|---|
| `dev_update_window ('off'|'on')` | グラフィクス窓の自動更新を切替 | View ▸ Display updates ▸ Graphics window |
| `dev_update_var ('off'|'on')` | 変数窓の自動更新を切替 | 〃 Variable window |
| `dev_update_pc ('off'|'on')` | 実行カーソルの更新を切替 | 〃 Program counter |
| `dev_update_time ('off'|'on')` | 行ごとの処理時間表示を切替 | 〃 Operator timings |
| `dev_update_off ()` / `dev_update_on ()` | 上記すべてを一括で off / on | ツールバー **Auto-update** トグル |
| `dev_set_part (Row1, Col1, Row2, Col2)` | 表示範囲（ズーム/パン）を設定・負値=全体 | マウスホイール/Fit と併用 |
| `dev_set_lut ('gray'|'jet'|'viridis'…)` | カラーマップ（LUT）を切替 | View ▸ Display mode |
| `dev_clear_window ()` | カレント窓をクリア | — |
| `set_system ('thread_num', N)` | OpenCV ワーカースレッド数（0=既定/全）を設定 | Tools ▸ System settings |
| `set_system ('operator_timeout', ms)` | ソフト operator タイムアウト（遅い段を Run status で警告） | 〃 |
| `dev_set_draw ('fill'|'margin')` | region overlay の塗り（fill）/ 輪郭（margin）切替 | View ▸ Display mode = region overlay |
| `dev_set_color ('red'|'green'…)` | region overlay の色 | 〃 |
| `dev_set_line_width (N)` | margin の輪郭幅（px） | 〃 |
| `dev_disp_text ('label', Row, Col)` | 結果の上にテキスト注釈（次の描画/`dev_clear_window` で消える） | — |

**用途**: `dev_update_off ()` を先頭に置くと、重い処理や多数の編集を**描画コストなし**で行え、
`dev_update_on ()` で現状態へ一括更新できます（HDevelop の性能テクニックと同じ）。更新が
off の間はステータスバー右に `updates off: …` が出るため、凍結状態が「壊れて見える」ことは
ありません。ツールバーの **Auto-update** トグルでも同じ切替ができます。

**注意**（honest）: `dev_*` はパイプライン段と違い `if`/`for` に従わず**無条件に適用**されます
（分岐内に置いても発火）。トップレベルに書いてください。未対応の `dev_*` はエラーになります。

**動かして見る**: **File ▸ dev_* visualization demo** で、coins 画像 + 上記 `dev_*` を実際に使う
HDevelop プログラム（区分→領域を cyan の輪郭 + ラベルで表示）が読み込まれ適用されます。作業用の
サンプル画像は **File ▸ Sample images**（8 枚・provenance は `studio_assets/sample_images/manifest.json`。
合成 = own work / `coins`・`camera` 等 = skimage.data の BSD/public-domain。`tools/gen_sample_images.py`
で再生成）。

---

## Export と Save/Open の関係

Studio で組んだパイプラインは 3 つの形で持ち出せます。

| 形式 | 出し方 | 使いどころ |
|---|---|---|
| `--ops` 文字列 | Export（Ctrl+E） | CLI の `imgevolve.py pipeline --ops "…"` / `run "…"` に貼る |
| Python 関数 | Export（Ctrl+E） | 自分のコードに `fullseye.run_pipeline(...)` として埋め込む |
| JSON | Save pipeline（Ctrl+Shift+S） | `FullseyeEngine.load(...)` / `imgevolve.py run pipeline.json` で実行 |

**設計は Studio、実行はコード/CLI** という HDevelop→HDevEngine 相当の流れは、JSON を介して行います。JSON を受け取って実行する側は [ENGINE.md](ENGINE.md) を参照してください。

---

## 関連ドキュメント

- [STUDIO_UX.md](STUDIO_UX.md) — デザインシステム・UX 改善の意図と背景（デザイン視点）
- [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md) — 知覚パネルの中身（flow / stereo / terrain）
- [ENGINE.md](ENGINE.md) — 書き出したパイプラインを実行する
- [GETTING_STARTED.md](GETTING_STARTED.md) — 5 分ではじめる

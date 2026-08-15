# Fullseye Studio — HDevelop 忠実化スペック(北極星)

> 目的 = Fullseye Studio（`studio.py`）を **MVTec HDevelop に忠実な画像処理 IDE** にする。
> 原則 = **「IDE の画面はシンプルかつ多機能」「情報密度が高い」**（ユーザー 2026-08-15、[[feedback_ide_design_simple_multifunctional]]）。
> 本ドキュメントは複数セッション横断の実装スペック。各セッションはここを読んで続きを実装する。

## 一次情報（必ずこれで裏取り）
- 公式ドキュメント: <https://docs.mvtec.com/hdevelopevo/24.11-preview/index.html>
  - UI / Rapid Prototyping: `content/ide/index.html`
  - 実行 / デバッグ: `content/ide/debugging/index.html`
  - **HALCON Script Reference（構文）**: `content/halcon_script/index.html`
  - オペレータ / リファレンス: `content/reference/index.html`
- 補助調査（Perplexity、下記に要約。**主張は公式で裏取り**）。

## HDevelop のモデル（Perplexity 調査要約・公式で要確認）
### ウィンドウ（それぞれが「一つの完結したソフト」として機能・ボタンはアイコンでコンパクト・右クリックでコンテキストメニュー）
- **Graphics Window**: iconic（image/region/XLD）の描画先。複数生成可。`dev_display`/`dev_set_color`/`dev_set_draw`/`dev_set_colored`/`dev_set_lut` が現在の active window に作用。
- **Variable Window**: 変数を **iconic（サムネイル表示で形状が分かる）** と **control（数値/文字列テキスト・編集可）** に分離。iconic を**ダブルクリック→ active Graphics Window に表示**（= `dev_display`）。control をダブルクリック→ Variable Inspection。**ステップ実行に連動して変数状態が更新**。
- **Program Window**: 1 行 = 1 オペレータ呼出 / 制御文 / 代入。行番号・実行カーソル（黄矢印）・ブレークポイント・Step Into/Over/Out/Run。
- **Operator Window**: **オペレータ選択コンボ（オートコンプリート）** + カテゴリツリー + 検索。1 パラメータ = 1 行で **名前 / 型 / 方向（iconic|control × in|out） / デフォルト / 候補値ドロップダウン / min-max / inline doc**。**引数入力までできる**。**コードへ挿入**と**単発実行（single-shot）**の両方が可能で、**結果を Graphics Window で確認**できる。

### iconic の与え方・確認
- オペレータの**出力パラメータ**が iconic を生成: `read_image`→Image、`threshold`→Region、`connection`→ConnectedRegions、`edges_sub_pix`→XLD。
- 確認 = Variable 窓サムネイル・ダブルクリック表示・`dev_display`。region は image 上に**色 overlay**（`dev_set_draw` の `margin`/`fill`、複数色 `dev_set_colored`）。

### 制御フロー / スクリプト構文（HALCON Script）
- `if / elseif / else / endif`・`for / endfor`・`while / endwhile`・`repeat / until`・`break / continue / return / stop / exit`・代入 `:=`。
- 条件 = boolean 式。比較 `< > <= >= = #`、論理 `and / or / xor / not`。タプル `[1,2,3]`。
- 挿入 = Edit▸Insert / ツールバー / operator window（キーワードを program text に挿入）。
- コメント記法・オペレータ呼出記法 `operator (Params)` は **公式 Script Reference で確定**してから実装。

### メニュー（HDevelop）
- File / Edit / Execute / Visualization / Operators / Suggestions / Assistants / Procedures / Window / Help。

## 現状 Studio → HDevelop ギャップ & ロードマップ
線形 a/b パイプライン（op,a,b の列）→ 変数 + 制御文 + 型付き引数の HDevelop 型へ段階進化。

- **P1 メニュー再構成 — 済（v18.7）**: 標準 IDE 構成、Window を Panels/Graphics/Layout の submenu 化、View に Display mode、Command palette/Language を Tools、submenu 消失バグ修正。
- **P2a オペレータ引数の可視化 — 済（v18.7）**: `op_arg_roles`/`op_impl_source`/`op_signature_detail` で knob a/b の役割 + 実装式を高密度表示（「引数が判断できない」を解消）。
- **P2b Operator ウィンドウ（HDevelop 型）— 次**: op 選択を**オートコンプリート・コンボ**化（画面有効活用）+ **引数入力ウィジェット**（名前/型/デフォルト/候補/範囲）+ **コード挿入**と**単発実行**の両方 + **結果を Graphics 窓で確認**。
- **P3 サンプル/スクリプト読込導線**: 「読み込む」一本道 + プレビュー + 説明。
- **P4 iconic 変数モデル + パネル刷新**: Variable 窓を **iconic（サムネイル）/control（編集可）分離**、**ダブルクリック→Graphics 表示**、**step 連動更新**、**Region の色 overlay 表示**。各パネルを**自己完結ソフト化**・**アイコンツールバーでコンパクト化**・**高情報密度**・**右クリック→コンテキストメニュー**（各所）。
- **P5 HDevelop script 構文 + 制御フロー**: Program 窓を HDevelop 構文対応（`op (params)`・`:=`・コメント・if/else/for/while）。実行モデル（step/breakpoint/実行カーソル）と Variable/Graphics 連動。

## 実装規律
- 変更は additive・全 op 契約を壊さない・full suite green を維持（studio テスト offscreen）。
- 各 UI 挙動は headless（`QT_QPA_PLATFORM=offscreen`）でテストする（build_window ハンドル経由）。
- submenu/QMenu は**明示親付き構築**（`QMenu(title, parent)`）で shiboken 回収を防ぐ（v18.7 で判明）。
- HDevelop 挙動は**公式ドキュメントで裏取り**してから実装（Perplexity は補助）。

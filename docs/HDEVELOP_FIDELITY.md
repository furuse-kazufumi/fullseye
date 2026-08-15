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

## 次セッション最優先(2026-08-15 実 GUI レビューで判明)
1. **★自律 UI 操作デバッグ・ハーネス**: QTest で実マウス click/press/move/release を全ボタン/ドラッグへ注入し、操作系のクラッシュ・不具合をユーザーに触らせず自動検出。手順: build_window(offscreen)→全 QPushButton/QAction を QTest.mouseClick→dock ドラッグ→各段でスクショ+状態 assert。ハンドラ直呼びでは実イベント固有のバグ(旧 GroupedDragging segfault 等)を見逃す。
2. **カレント画像表示窓モデル(HDevelop)**: 画像表示窓は最低1つ常駐(最後は閉じられない)=「カレント窓」。変数/オブジェクトのダブルクリック表示は**カレント窓へ**行う(現状は new window/main が分離)。new_graphics_window/display_variable を current-window 概念で統一。
3. **修正済(本セッション)**: ステップ実行が表示更新しないバグ(step_to 自己修復化)。既定レイアウト HDevelop 型。ボタンアイコン+ラベル。crash ログ常設。
4. **検証規律**: ユーザーに手動テストさせる前に**サンドボックス(QTest+スクショ)で私が e2e 検証**する(ユーザー明示指摘)。
   - 補足(HDevelop): 各 Graphics 窓に**ハンドル番号**(`open_window`/`dev_open_window` の WindowHandle)。`dev_*` 系オペレータ(dev_display/dev_set_color/dev_set_draw/dev_clear_window 等)は**カレント窓**へ描画。`dev_set_window(Handle)` でカレント切替。→ Studio 実装: 各 graphics 窓に handle 番号 + カレント窓ポインタ + 変数ダブルクリック=カレント窓へ描画 + カレント切替 UI(窓クリック or ハンドル指定)。

---

## 実装記録: v18.8(2026-08-15, Opus5[1m]/ultracode)= 自律 UI 操作デバッグ・ハーネス + クラッシュ級バグ 3 件修正

**★自律 UI 操作ハーネスを実装**(`tools/studio_ui_harness.py`)。offscreen subprocess で Studio を起動し、**実マウスイベント**(`QMouseEvent` 直送=drag は buttons=LeftButton 保持)を全 QPushButton / 全 QAction / **全 dock ドラッグ** / 変数リスト / 右クリックコンテキストメニューへ注入(P0–P9 の 183 ステップ)。設計:
- **crash 帰属** = 各フェーズ開始を JSONL step-log に前置記録 + `faulthandler`。硬い C++ segfault は親が exit code + step-log の最後の `phase_start` + native traceback で帰属。
- **hang 回避** = モーダル(`QDialog.exec`)は CONFIRM/ERROR stub + `QFileDialog` monkeypatch + **watchdog QTimer**(`activeModalWidget` **と** `activePopupWidget`=`QMenu.exec` も閉じる)。
- **slot 例外捕捉** = `sys.excepthook` で queued signal 内の非同期例外をフェーズ付きで記録。
- **常駐窓 probe** = 各フェーズ後に `graphics_primary` の生存 + in-MDI を記録。

**★ハーネスが実イベント注入でしか出ない 3 クラッシュを自動検出→修正**(全て `studio.py`、regression テスト付き `tests/test_studio.py`):
1. **[高] 3D surface ボタンで access violation(segfault)**。`show_3d_surface`(旧 737 行)の `Q3DSurface()` は OpenGL コンテキスト不在(offscreen / **Remote Desktop / ソフトウェア GL**)で native segfault、`try/except` は import 失敗しか捕捉せず。→ `_opengl_available()`(`QOffscreenSurface`+`QOpenGLContext` プローブ、offscreen は即 False)でゲート、`open_3d` は None 時に「3-D surface needs OpenGL」を flash。**GL があれば動く / 無ければ無害に degrade / 決してクラッシュしない**。
2. **[高] update_actions が削除済みウィジェットで RuntimeError**。`b_save`(Save result)は `image_panel`(=プライマリ Graphics 窓)内にあり、窓破棄で削除されるが queued `currentRowChanged`→`update_actions` が `setEnabled` で `RuntimeError: Internal C++ object already deleted`。→ `_enable(cond, *widgets)` ヘルパで削除済みを skip(状態同期は生存分を継続)。
3. **[高] プライマリ Graphics 窓が閉じられ、常駐 view + グローバル操作ボタンが破棄**(=下記 Codex #2「最後の窓は閉じられない常駐モデル欠如」の実クラッシュ)。MDI サブ窓の close(閉じるボタン / システムメニュー「Close」/ Ctrl+W)で `image_panel` ごと `view`/`b_save` が破棄。→ プライマリ サブ窓に **close 拒否 event filter**(`_ResidentCloseGuard`)+ `detach_graphics` はプライマリ(`objectName == "graphics_primary"`)の detach を拒否。**常駐カレント窓モデルの第一歩**。

**検証** = ハーネス再走で 183 steps 全 OK・slot 例外 0・crash 0、プライマリ窓は全 10 フェーズで alive+in-MDI 維持(修正前は P2 の MDI「Close」で in-MDI=False→P9 で削除→クラッシュ)。studio テスト 69→**72**(detach テストを常駐仕様へ更新 + resident/update_actions/3D の 3 回帰追加)。**dock ドラッグ(GroupedDragging 疑い)は全 25 パターンで crash せず**(自動プロキシは通過。実 windowing-system の native drag とは差があるため実機確認は別途)。

## 操作方法の仕様・審議(2026-08-15, 外部 AI = Codex read-only、ユーザー指示「用途を考えながら批判をさせて」)

**用途** = 「画像処理アルゴリズムを対話的に組み・パラメータを詰め・holdout 検証する」設計作業(HDevelop 経験者が同等の操作感を期待)。Codex に `studio.py` + 本 doc を読ませ、操作フローに限定して 12 件の code-backed 批判を取得(各件を私が一次コード検証。**規律=鵜呑み禁止 [[feedback_external_ai_verify]]**)。採用した論点(★=次の実装対象):

- **★[高] カレント Graphics 窓状態が無い**(`new_graphics_window` 1550– は窓を追加するだけ、`_render` は常に固定 `view` へ)= **本 doc の北極星「カレント窓モデル」と一致**。操作対象と結果表示先が乖離。→ **P4-current: カレント窓ポインタ + ハンドル番号 + `dev_set_window` 相当の切替 UI + `_render`/`display_variable`/`run_op_once` をカレント窓へ**。上記修正 3(常駐化)がその土台。
- **★[高] 変数ダブルクリックが新規窓を増殖**(`display_variable(True)`→常に新窓)。HDevelop は active 窓へ表示。→ ダブルクリック=カレント窓へ、Shift/ボタンで新窓。
- **★[高] Run once が常に新窓・入力は常に原画像**(`run_op_once` 1861–、入力 `model.image` 固定)。中間結果や選択変数を入力にできない。→ カレント窓表示 + 入力=選択ステージ/変数の結果を選べるように。
- **[高] Operator 引数 UI が汎用 a/b**(0..1, 0.5 固定、op で型/範囲/候補/既定/名前が変わらない)= 本 doc P2b の未完部分。
- **[高] 変数 iconic/control 分離が文字列判定のみ**・contour 非サムネイル(`_var_icon` は 2D/3D ndarray のみ)。
- **[高] step 実行と Variable 窓の「生存変数」非連動**(`step_to` は `refresh_variables` を呼ばない、全ステージ先行計算で未実行の後段も存在して見える)。
- **[高] Program 窓の未適用編集が確認なし消失**(`confirm_discard` は Pipeline のみ、`code_edit` の変更未追跡、`sync_program` が上書き)。
- **[中] 削除/並べ替え/Program 適用に Undo が無い** / **削除後に選択が必ず消える**(`remove` が select 指定なしで refresh)。
- **[高] holdout 検証への操作経路が Studio 内に無い**(`load_image` は単一画像のみ、`load_frame_b` は 2 フレーム perception 用)= 用途の最終工程が未完結。**要ユーザー判断(スコープ大)**。

**次の実装順(deliberated)**: (P4-current)カレント窓モデル ← 常駐化済で土台あり・最大クラスタ(Codex #1–5)を一括で筋通し → (P2b')op 別引数 UI → (step 連動)→(Program dirty 追跡)。Undo / holdout 経路はスコープ大ゆえユーザー確認後。

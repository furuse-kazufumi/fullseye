# HDevelop `dev_*` operator family — the UI/display control surface (Studio 北極星)

> ユーザー指摘(2026-08-16): 「HALCON では**描画の更新有無も** op で制御できる」「**画像の描画範囲**の設定とかも op で対応できる」→ HDevelop は **表示(グラフィクス窓・変数窓・実行カーソル・表示範囲・描画スタイル)をすべて `dev_*` operator で制御**する。Fullseye Studio(`studio.py`)はこの HDevelop モデルに忠実であるべき。
>
> 一次情報 = MVTec 公式 Operator Reference の実スクレイプ `data/halcon_operators.json`(HALCON 26.05, **43 個の `dev_*` op** / Graphics 章 174 op)。裏取り URL は各 op の `url`。

## なぜ重要か(async threading より優先すべき理由)
Studio の残件「大画像/重い op で GUI が固まる」に対し、HDevelop は **`dev_update_off`(全更新オフ)= 描画コストをループ中ゼロにする**という op レベルの解を持つ。これは共有可変モデルへの threading 変更(高リスク・回帰を harness/test で捕捉しにくい)より **低リスクかつ HDevelop 忠実**。表示範囲(`dev_set_part`)も同様に op で制御する。

## 43 `dev_*` op の分類と Studio 実装状況

凡例: ✔=実装済(等価機能あり) / △=部分/UI のみ / ★=本トラックで実装対象 / ○=将来 / —=IDE 固有でスコープ外

### A. 描画更新制御(★ユーザー指摘①・最優先)
| op | 説明 | Studio |
|---|---|---|
| `dev_update_window` | 実行中に iconic 出力をグラフィクス窓へ自動表示する on/off(既定 on) | ★ |
| `dev_update_var` | 変数窓を変数変更ごとに更新する on/off(off=停止まで更新しない) | ★ |
| `dev_update_pc` | プログラムカウンタ(実行カーソル)の更新 on/off | ★ |
| `dev_update_time` | operator の時間計測 on/off | ★ |
| (`dev_update_off`/`dev_update_on`) | 上記の一括切替(HDevelop ライブラリ手続き・性能/計時用) | ★ |

### B. 表示範囲 / 窓(★ユーザー指摘②)
| op | 説明 | Studio |
|---|---|---|
| `dev_set_part` | **表示する画像部分(ズーム/パン範囲)を変更** | ★ |
| `dev_set_window` / `dev_get_window` | アクティブ窓の切替 / ハンドル取得 | ✔ (UI カレント窓モデル + **program directive**: `dev_set_window (handle)`) |
| `dev_open_window` / `dev_close_window` | 窓の open / close | ✔ (UI + **program directive**: `dev_open_window (row, col, w, h)` が開いて配置しカレント化 / `dev_close_window` はカレントを閉じる。resident 主窓は close 保護。再 Apply は**同じ窓を再配置**(source-order slot キー)し増殖しない。上限 = `set_system('max_graphics_windows')`(既定 256、System settings で変更可・全経路 fail-closed)) |
| `dev_clear_window` | アクティブ窓のクリア | ✔ (script directive) |
| `dev_set_window_extents` | 浮動グラフィクス窓の位置・サイズ | ✔ (**program directive**: `dev_set_window_extents (row, col, w, h)`、-1 は現状維持) |

### C. iconic 表示・描画スタイル
| op | 説明 | Studio |
|---|---|---|
| `dev_display` | 現在窓へ image object を表示 | ✔ (display_variable) |
| `dev_disp_text` | テキスト表示 | ✔ (ImageView.disp_text・script directive) |
| `dev_set_lut` | ルックアップテーブル(カラーマップ) | ✔ (script + 18 display modes) |
| `dev_set_draw` | region 塗り mode(margin/fill) | ✔ (script directive・overlay_mask mode) |
| `dev_set_color` / `dev_set_colored` | 出力色 | ✔ dev_set_color(script・色名→RGB) / △ colored |
| `dev_set_line_width` | 線幅(margin 輪郭幅) | ✔ (script directive) |
| `dev_set_shape` | region 出力形状 | ○ |
| `dev_set_paint` | gray value 出力 mode | ○ |
| `dev_set_contour_style` | contour 塗りスタイル | ○ |
| `dev_clear_obj` | iconic object を DB から削除 | — |

### D. 変数 / 検査窓
| op | 説明 | Studio |
|---|---|---|
| `dev_map_var` / `dev_unmap_var` | 変数窓の表示/非表示 | ✔ (Window▸Panels) |
| `dev_inspect_ctrl` / `dev_close_inspect_ctrl` | control 変数の検査窓 | △ (Inspector) |
| `dev_map_prog` / `dev_unmap_prog` | メイン窓の表示/非表示 | — |
| `dev_map_par` / `dev_unmap_par` | 可視化パラメータダイアログ | — |

### E. ツール/ダイアログ/システム/エラー(HDevelop-IDE 固有・スコープ外)
`dev_open_tool` `dev_close_tool` `dev_show_tool` `dev_set_tool_geometry` `dev_open_dialog`
`dev_open_file_dialog` `dev_get_system` `dev_set_system` `dev_get_preferences`
`dev_set_preferences` `dev_set_check` `dev_error_var` `dev_get_exception_data` — いずれも
HDevelop IDE 内部の制御で、Fullseye Studio の設計デモ用途では不要(—)。

## 参考: dev_ が包む低レベル Graphics op(165, 非 dev_)
`set_part` / `set_lut` / `set_color` / `set_draw` / `set_paint` / `disp_obj` / `disp_image` /
`disp_region` / `disp_xld` / `get_mbutton` / `get_mposition`(マウス)等。HDevelop script は
通常 `dev_*` を使う(現在窓・エラー処理込み)ため、Studio も `dev_*` 面を優先実装する。

## 実装計画(本トラック)
1. **Phase A = `dev_update_window/var/pc/time` + `dev_update_off/on`**: `state["dev_update"]`
   (window/var/pc/time、既定 on)+ Visualization メニュー checkable トグル + ツールバー +
   Program パーサが `dev_update_*` を **directive**(画像 stage でない)として認識し run_program で
   適用。off の間は該当描画(show_result / refresh_variables / 実行カーソル)をスキップし、停止時に
   最終更新。→ 描画更新の op/UI 制御を実現(= GUI freeze 緩和の HDevelop 流の解)。
2. **Phase B = `dev_set_part(Row1,Col1,Row2,Col2)`**: ImageView に `set_part` を追加(画像座標の
   矩形へズーム/パン)、`dev_set_part(0,0,-1,-1)`=全体。Program パーサ + 適用。
3. 将来(○) = `dev_clear_window` / `dev_disp_text` / `dev_set_line_width` 等の描画スタイル op。

各段は offscreen テスト + `tools/studio_ui_harness.py`(192 steps)で回帰確認。

**実装状況(2026-08-16)**: Phase A(`dev_update_window/var/pc/time` + `dev_update_off/on`)= **済**
(`state["dev_update"]` / View▸Display updates / ツールバー Auto-update / Program directive)。
Phase B(`dev_set_part`)= **済**(`ImageView.set_part` / `win._set_part` / directive)。
Program パーサは `dev_*` を directive として認識(未対応 dev_ はエラー)、`extract_dev_directives`
で source 順収集、`apply_program` が元テキストから適用。studio 88 passed / harness 202・0 fail。
次(○)= `dev_clear_window` / `dev_disp_text` / `dev_set_lut`(display mode)/ `dev_set_draw`
(region overlay)を script directive 面へ配線(UI では既に対応済み)。

## F. System / 設定系 op(ユーザー指摘・System 章 140 op)
HALCON はグローバル設定を `set_system`/`get_system`(パラメータ名+値)で行う。HDevelop は
`dev_set_system`/`dev_get_system`(IDE 実行系)+ `dev_set_preferences`/`dev_get_preferences`
(IDE 設定)。Fullseye に直結する設定は:

| op | 設定内容 | Fullseye での対応先 |
|---|---|---|
| `set_system('thread_num', N)` / `get_system` | 並列スレッド数 | `fsruntime` の `cv2_threads` knob(N1b 裾対策)/ `scale.process_tiled_mt` |
| `set_check('on'/'off')` / `get_check` | エラーチェック制御モード(fail-closed の可否) | fail-closed 規律(既定 on を崩さない)。runtime は常に fail-closed |
| `set_operator_timeout` | operator 単位のタイムアウト | `FullseyeRuntime(deadline_ms=...)` → TIMEOUT verdict |
| `get_system_info` | ライセンス不要のシステム情報 | 環境レポート(capabilities) |
| `init_compute_device` / `set_compute_device_param` / `optimize_aop` | GPU/計算デバイス・自動並列 | 将来(GPU 化・NAS スイープ) |

**実装状況(2026-08-16)= 済**: **Tools ▸ System settings** ダイアログ + `state["system"]` +
QSettings 永続化。`thread_num`(OpenCV `cv2.setNumThreads`、対話 op 速度に直結)/ `operator_timeout`
(ソフト=遅い段を Run status で警告。native op は hard-interrupt 不可の honest 限界)/ `check`=
fail-closed 表示。**`set_system(param, value)` を Program directive 化**(HALCON 忠実、非 dev_ の
`_CONFIG_DIRECTIVES`)。`get_system` は戻り値を格納する変数モデルが flat pipeline に無いため未対応
(honest)。deadline_ms/high_priority の runtime 配布設定は fsruntime 側の既存 knob に集約(過剰な
設定面を作らない=「IDE はシンプルかつ多機能」原則)。studio 89→92 / harness 202→204。

## G. `disp_*` 表示 op(Graphics 章・2026-08-30 実装)
HALCON の Graphics 章には窓へ直接描く `disp_*` operator 群がある。Studio は表示 op を純変換の
`ops.REGISTRY` に混ぜず(副作用=UI を持つため)、`dev_*` と同じ **Program directive 層**
(`_DISP_DIRECTIVES`)+ **Python API**(`studio.disp_points3d` / `studio.disp_mesh3d`、directive の
ビューアと同一実装)の二面で提供する。全 `disp_*` は `state["disp_log"]` に記録され(headless で
テスト可能)、失敗は flash+ログで raise しない(fail-soft)。

| directive | HALCON 実 op(裏取り) | Studio 動作 |
|---|---|---|
| `disp_image (n)` | `disp_image` | stage n(1 始まり、省略=最終)の出力を**カレント graphics 窓**へ現在の display mode で描画 |
| `disp_region (n)` | `disp_region` | 同上を region overlay(dev_set_draw/color/line_width スタイル)で描画 |
| `disp_points3d ('file')` | `disp_object_model_3d` 相当(点群面) | 対話 3-D ビューア窓を開く(mesh.read_points 形式: ply/pcd/xyz/npy/npz/obj/stl/off) |
| `disp_mesh3d ('file')` | `disp_object_model_3d` 相当(メッシュ面) | 同、メッシュ(頂点+面重心のランバート splat、W=ワイヤフレーム) |
| `disp_object_model_3d ('file')` | `disp_object_model_3d` | HALCON パリティ別名: 面が有ればメッシュ、無ければ点群として dispatch |

正直な整理: HALCON の `disp_object_model_3d` は window handle + カメラパラメータ + genParam を取る
リッチな op であり、Studio 版は「ファイル→ビューア窓」の最小写像(相当・workalike)。窓管理は
`dev_open_window` と同じ handle 体系に乗り(`dev_set_window` で選択可、`max_graphics_windows` の
上限も共通)、re-Apply は source-order slot キーで**同じ窓を再利用**する。2-D の `disp_image` を
3-D ビューア窓がカレントの時に呼ぶと primary 窓へ安全に redirect(honest limit)。ビューアは
実測に基づき software rasterizer(offscreen/RDP でも同一経路)。**性能実測**(2026-08-30
再計測、size=480、定常状態 median): 200k pts ≈ 66 ms/frame(≈15 fps)、1M pts ≈ 350 ms/frame —
**1M は full resolution では対話的とは言えない**ため、drag/wheel 中は `DRAG_BUDGET`(250k)点へ
均一間引きし(HUD に "preview N pts" と正直表示)、リリース時にフル解像度で再描画する。
ワイヤフレーム overlay は **60,000 辺 cap**(`mesh_edges(cap=60000)`、超過時は overlay 自体を
スキップ)。ヘッドレスのカメラ数学(`viewer3d_camera`/`viewer3d_project`)は pytest で数値固定済み
(depth は「大きいほど遠い」— far→near の painter's algorithm で遮蔽、UV 球の可視面回帰テストあり)。
`dev_*` 同様、docs/ops の per-op ノート体系(純変換 op 用)には登録しない(体系を乱さない)。

## 出典
一次情報 = `data/halcon_operators.json`(MVTec Operator Reference 実スクレイプ, HALCON 26.05)。
個別 op 裏取り例: [dev_update_window](https://www.mvtec.com/doc/halcon/13/en/dev_update_window.html) /
[dev_set_part](https://www.mvtec.com/doc/halcon/2411/en/dev_set_part.html) /
[set_system](https://www.mvtec.com/doc/halcon/2411/en/set_system.html)。

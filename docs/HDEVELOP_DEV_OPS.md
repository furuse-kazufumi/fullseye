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
| `dev_set_window` / `dev_get_window` | アクティブ窓の切替 / ハンドル取得 | ✔ (v18.8 カレント窓モデル) |
| `dev_open_window` / `dev_close_window` | 窓の open / close | ✔ (new/close graphics window) |
| `dev_clear_window` | アクティブ窓のクリア | ○ |
| `dev_set_window_extents` | 浮動グラフィクス窓の位置・サイズ | △ (detach/float あり) |

### C. iconic 表示・描画スタイル
| op | 説明 | Studio |
|---|---|---|
| `dev_display` | 現在窓へ image object を表示 | ✔ (display_variable) |
| `dev_disp_text` | テキスト表示 | ○ |
| `dev_set_lut` | ルックアップテーブル(カラーマップ) | ✔ (18 display modes) |
| `dev_set_draw` | region 塗り mode(margin/fill) | ✔ (region overlay) |
| `dev_set_color` / `dev_set_colored` | 出力色 | △ |
| `dev_set_shape` | region 出力形状 | ○ |
| `dev_set_paint` | gray value 出力 mode | ○ |
| `dev_set_line_width` | contour 線幅 | ○ |
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

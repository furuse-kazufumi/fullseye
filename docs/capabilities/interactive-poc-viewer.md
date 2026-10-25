---
id: interactive-poc-viewer
title: 結果を、触って見られる 1 枚の HTML にする(タブ・バッジ・3-D・動画・多言語)
title_en: Turn results into one self-contained page you can touch (tabs, badges, 3-D, video, languages)
category: 見せる
ops: [write_viewer, viewer_spec, viewer_points_tab, viewer_mesh_tab, viewer_frames_tab, viewer_split_tab, viewer_anim3d_tab]
examples: [interactive_poc_viewer, interactive_anim3d_viewer]
version: 0.7.0
---

# 結果を、触って見られる 1 枚の HTML にする(タブ・バッジ・3-D・動画・多言語)

## できること

PoC や計測の結果を、**自己完結した 1 枚の HTML ビューア**にします。暗色で、素の WebGL と 2-D canvas だけ、外部ライブラリも外部 URL の読み込みも無く、`file://` でも iPhone の Safari でも動きます。同じ課題を違う方法で試した記録を**タブ**に並べ、各タブに正直な**バッジ**(門を通った / 限界を見せる / 何もしない場合)・短い説明・実測の数字を付けます。

ペイロードは 5 種です。**三角形メッシュ + 頂点ごとの値の色 + カラーバー**、**点群(点ごとの値の色か RGB、灰色の参照点群つき)**、**2-D の画像列 + 重ねる枠(真値と推定)+ しきい値つきの時系列グラフ**、**前後の画像のドラッグ分割**、**動く 3-D**(`viewer_anim3d_tab`)。3-D はドラッグで回し、ホイールとピンチで拡大し、視点ボタン・再生・時間つまみ・速度で見ます。動く 3-D の物体には `"alpha"`(0 < alpha <= 1)を付けて半透明にでき、レンズやガラス板の中・後ろを通る光線(軌跡)が透けて見えます。

**動く 3-D** は、物体ごとのメッシュを 1 回だけ持ち、コマごとには剛体の姿勢(位置 + 四元数)だけを持ちます。残像の軌跡、点群の時系列、段の区切り(ジャンプのボタン)、時系列グラフ、**同じ時間軸で並ぶ 2-D の画像列**(センサー画像・op の結果)を 1 つのタブで同期再生します。操作は再生/一時停止・コマ送り/戻し・スライダ・速度 0.25〜4 倍・ループ・段へのジャンプ・カメラの追従(平滑化して揺らさない)。2-D の画像は既定で**無損失の PNG** で埋めます(画素を変えずに小さくする。間引かない)。

言語は呼ぶ側が選びます。`write_viewer(spec, path, lang="ja")` は単言語のページ、`lang=["ja", "en", "fr"]` は切り替えつき(先頭が既定)。対応は ja / en / zh / tw / ko / de / hi / fr の 8 つで、ボタンやバッジの文字列はモジュールが 8 言語で持ちます。仕様の文字列は言語ごとの辞書で渡し、**要求した言語が欠けていれば欠けた鍵を並べて `ValueError`** —— 日本語などへ黙って補いません。URL の `?lang=xx` と `?tab=<id>` で開く言語とタブを選べます。

データは**間引かず量子化**します(位置は軸ごとに uint16、値はカラーバーの範囲の uint16、画像と索引は無損失)。同じ配列は内容のハッシュで 1 本にまとめるので、タブ間で位置を共有するビューアは小さく済みます。

## What it does

`write_viewer(spec, path, lang=...)` writes one self-contained HTML page (dark theme, plain WebGL and 2-D canvas, no libraries, no external loads; works from `file://` and on iPhone Safari). Tabs hold the same task attempted by different methods; each carries an honest badge (`passed` / `limit` / `null`), a short text and measured numbers. Payloads: a triangle mesh with per-vertex scalar colour and a colour bar; a point cloud (scalar or RGB colour, optional grey ghost cloud); a 2-D frame sequence with overlaid boxes and a thresholded time-series plot; a before/after pair with a draggable split; and moving 3-D (`viewer_anim3d_tab`): each rigid body's mesh is stored once and only its per-frame pose (position + quaternion, quantised to uint16 / int16) is stored per frame, with fading trails, point-cloud snapshots, stage markers you can jump to, time series and 2-D image panes (embedded as lossless PNG) played on the same clock, frame stepping, 0.25-4x speed, loop and a smoothed follow camera; a body may carry `"alpha"` (0 < alpha <= 1) to be drawn translucent after trails and point clouds, so rays passing through a lens or glass plate stay visible. `lang` is a code or a list (first is the default) from ja, en, zh, tw, ko, de, hi, fr; every requested language must be present for every string or `ValueError` names the missing keys (no silent fallback). Data is quantised, never decimated: positions as per-axis uint16, values as uint16 over the colour-bar range, images and indices lossless. Standard library and NumPy only. The same call is available as the MCP tool `fullseye_write_viewer`.

## 向くところ / 向かないところ

**向く**: 論文の QR コードの行き先に置く「触れる展示」、PoC の結果を同僚に配る、成功だけでなく失敗の形(限界・零点)を並べて見せる、数字をカードと HUD に出して「何を見ているか」を 1 行で添える。

**向かない**: ★**解析の道具ではありません**(色と数字を見せるだけで、計算はしない)。★**volume(ボクセル)や大きな動画**は想定外(2-D のコマは 8 bit、メッシュの頂点が 65,535 を超えるには `OES_element_index_uint` が要る)。★**数字は手で写さない** —— 実行から取ること(`tools/build_view2026_viewers.py` が 7 本の手本)。★数万〜数十万点までは軽いが、数百万点は端末による。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

pos = np.random.default_rng(0).uniform(-1, 1, (5000, 3))
val = pos[:, 2]                                           # 色にする値
tab = fs.viewer_points_tab(
    "a", fs.viewer_text("高さ", "Height", fr="Hauteur"), "passed",
    fs.viewer_text("高さで色づけ。", "Coloured by height.", fr="Coloré par la hauteur."),
    pos, val=val, cbar={"lo": -1, "hi": 1, "unit": "mm"})
spec = fs.viewer_spec("my_viewer", fs.viewer_text("見本", "Sample", fr="Exemple"),
                      fs.viewer_text("副題", "Subtitle", fr="Sous-titre"),
                      fs.viewer_text("操作", "Hint", fr="Aide"), [tab])
fs.write_viewer(spec, "out/my_viewer.html", lang=["ja", "en", "fr"])   # 先頭の ja が既定
```

## 裏づけ

- 実装: `pocviewer.py`(`write_viewer` / `viewer_spec` / `viewer_*_tab`。標準ライブラリ + numpy だけ)
- 例: [`interactive_anim3d_viewer`](../../examples/interactive_anim3d_viewer.py)(動く 3-D: 3 関節のアームが箱を運ぶ運動学 + 同じ時間軸の上から見たカメラ画像と二値化、姿勢の復元が刻みの半分以内、PNG が無損失)
- 例: [`interactive_poc_viewer`](../../examples/interactive_poc_viewer.py)(4 種のペイロード、位置の復元が量子化の刻みの半分以内、外部 URL 無し、欠けた訳の拒否)。実物は `tools/build_view2026_viewers.py`(CAD の偏差 / LiDAR の地形変化 / テンプレート追跡 / パルスサーモグラフィ / 格子干渉計 / デフレクトメトリ / 小惑星の曲率の 7 本、8 言語)
- 試験: `tests/test_pocviewer_anim3d_2026_10_24.py`(動く 3-D の姿勢の復元・四元数の符号・T の不一致や未知の色指定の拒否・PNG の往復と外部の復号器との一致)、`tests/test_gen_poc_viewer.py`(4 種のペイロード / 題が全言語で入る / 復元誤差 / 外部 URL 無し / 言語ごとに他言語の字が混ざらない / 欠けた訳を名指しで拒否 / 壊れた仕様の拒否 / MCP tool)
- MCP: `fullseye_write_viewer`(`docs/MCP.md`)

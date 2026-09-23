---
op: vol_render_transfer
dim: videocube
category: render
in: voxel
out: rgb
examples: [poc_print_layer_inspection, poc_video_cube]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# vol_render_transfer — VIDEOCUBE `render` op

- **データ種**: `voxel` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.vol_render_transfer(vol, color=None, yaw: 'float' = 35.0, pitch: 'float' = 25.0, size: 'int' = 256, alpha_gain: 'float' = 1.0, static_alpha: 'float' = 0.0, background=(0.04, 0.04, 0.06), frame: 'bool' = True, depth_samples: 'int | None' = None, static_color=None) -> 'np.ndarray'` (実装を直接呼ぶなら `import videocube; videocube.vol_render_transfer(vol, color=None, yaw: 'float' = 35.0, pitch: 'float' = 25.0, size: 'int' = 256, alpha_gain: 'float' = 1.0, static_alpha: 'float' = 0.0, background=(0.04, 0.04, 0.06), frame: 'bool' = True, depth_samples: 'int | None' = None, static_color=None) -> 'np.ndarray'`、台帳から引くなら `opsvideocube.get("vol_render_transfer")`)

## 使い方

立方体を任意の視点から**前から後ろへの α 合成**で描く ``(size, size, 3)`` float [0, 1] (``rgb``)。

``vol`` (T, H, W) は不透明度 [0, 1] (``video_spacetime_cube(mode="motion")``)。色は ``color`` を渡せば
その値(同じ形、[0, 1] に正規化される)のグレー、``(T, H, W, 3)`` の RGB 立方体([0, 1])ならその色、
渡さなければ**時刻の色**(青 = 始め → 赤 = 終わり)。``static_color``(同じ形のグレー)を渡すと
静止した背景の明るさをそれにする(2026-09-21、live4d の軌跡描画が「軌跡は時刻の色・背景は最初の
フレームの灰」を 1 回の合成で描くために)。
軌跡を時刻で塗ると「どちらへ動いたか」が 1 枚で読める。``static_alpha`` > 0 なら静止した背景(``color`` の
明るさ、無ければ灰)を薄く重ねる —— 値は**立方体の最長辺の長さを貫いたときの合計の不透明度**(0.15 なら
最長辺ぶん奥まで見て 15 %、短い辺の向きならそれより薄い)で、サンプル数には依らない(Summagator の「静的な内容」)。正射影、視線に沿って ``depth_samples`` 点
(既定 = 立方体の最大辺)を三線形補間で拾い、``C = Σ α_i c_i Π_{j<i}(1 − α_j)``。
``frame=True`` で立方体の 12 辺を薄く描く(向きの手掛かり)。

``yaw`` は時間軸と x 軸の面での回転(0 = 時間軸を奥行きに見る = 動画をそのまま見る向き)、``pitch`` は仰角。
1 枚あたりの計算量は ``size² × depth_samples``(256² × 64 で約 0.3 s)。

>>> rgb = vol_render_transfer(video_spacetime_cube(clip), yaw=40.0, pitch=20.0, static_alpha=0.02)

## 詳しい使い方ガイド

- [videocube ファミリ ガイド](../guides/videocube.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`
- [poc_video_cube](../../../../examples/poc_video_cube.py) — `py -3.11 examples/poc_video_cube.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

—

## 同カテゴリ(`render`)

[video_cube_orbit](video_cube_orbit.md)

---
*Provenance: videocube.py — VIDEOCUBE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

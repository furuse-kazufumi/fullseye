---
op: video_cube_orbit
dim: videocube
category: render
in: video
out: rgbvideo
examples: [poc_video_cube]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# video_cube_orbit — VIDEOCUBE `render` op

- **データ種**: `video` → `rgbvideo`
- **呼び出し**: `import fullseye as fs; fs.ledger.video_cube_orbit(video, n_frames: 'int' = 36, pitch: 'float' = 25.0, yaw_start: 'float' = 0.0, yaw_span: 'float' = 360.0, size: 'int' = 256, sigma: 'float' = 1.0, alpha_gain: 'float' = 1.0, static_alpha: 'float' = 0.02, color: 'str' = 'time', mode: 'str' = 'motion', depth_samples: 'int | None' = None, floor: 'float' = 0.15) -> 'np.ndarray'` (実装を直接呼ぶなら `import videocube; videocube.video_cube_orbit(video, n_frames: 'int' = 36, pitch: 'float' = 25.0, yaw_start: 'float' = 0.0, yaw_span: 'float' = 360.0, size: 'int' = 256, sigma: 'float' = 1.0, alpha_gain: 'float' = 1.0, static_alpha: 'float' = 0.02, color: 'str' = 'time', mode: 'str' = 'motion', depth_samples: 'int | None' = None, floor: 'float' = 0.15) -> 'np.ndarray'`、台帳から引くなら `opsvideocube.get("video_cube_orbit")`)

## 使い方

立方体を回す色動画 ``(n_frames, size, size, 3)`` float [0, 1] (``rgbvideo``)。

``video_spacetime_cube(mode)`` を不透明度に(``"motion"`` = 動画の軌跡、``"dark"`` / ``"bright"`` = z スタックの膜や
細胞)、``color="time"`` なら先頭軸(時刻 / 奥行き)の色、``"intensity"`` なら明るさで塗り、yaw を ``yaw_start`` から
``yaw_span`` 度ぶん等分に回す(pitch 固定)。展示と Studio の出口。``video_write_gif`` でそのまま GIF にできる。

>>> frames = video_cube_orbit(clip, n_frames=24, size=200)
>>> video_write_gif(frames, "cube.gif", fps=10)

## 詳しい使い方ガイド

- [videocube ファミリ ガイド](../guides/videocube.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_video_cube](../../../../examples/poc_video_cube.py) — `py -3.11 examples/poc_video_cube.py`

## 型が繋がる次の op(`rgbvideo` を入力に取れる)

[video_write_gif](../export/video_write_gif.md)

## 同カテゴリ(`render`)

[vol_render_transfer](vol_render_transfer.md)

---
*Provenance: videocube.py — VIDEOCUBE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

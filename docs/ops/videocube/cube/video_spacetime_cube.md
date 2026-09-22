---
op: video_spacetime_cube
dim: videocube
category: cube
in: video
out: voxel
examples: [poc_video_cube]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# video_spacetime_cube — VIDEOCUBE `cube` op

- **データ種**: `video` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.video_spacetime_cube(video, mode: 'str' = 'motion', sigma: 'float' = 1.0, percentile: 'float' = 99.5, floor: 'float' = 0.15) -> 'np.ndarray'` (実装を直接呼ぶなら `import videocube; videocube.video_spacetime_cube(video, mode: 'str' = 'motion', sigma: 'float' = 1.0, percentile: 'float' = 99.5, floor: 'float' = 0.15) -> 'np.ndarray'`、台帳から引くなら `opsvideocube.get("video_spacetime_cube")`)

## 使い方

動画 (T, H, W) を空間 × 時間の立方体 ``(T, H, W)`` float [0, 1] にする(``voxel``)。

``mode="motion"``: 隣り合うフレームの差の大きさ |I_t − I_{t−1}| を空間で σ = ``sigma`` のガウスで平滑し、
``percentile`` 分位で 1 に正規化、``floor`` 未満を 0 に落として [0, 1] に伸ばす(先頭フレームは 0。
センサ雑音の差分は床の下に沈む)。動く物体だけが立つので、``vol_render_transfer`` の**不透明度**になる ——
静止した背景は透けて、軌跡が浮かぶ(Summagator の伝達関数)。
``mode="intensity"``: 明るさを [0, 1] に正規化(色の元、または背景を薄く敷く用)。
``mode="dark"`` / ``"bright"``: 暗い / 明るい所を不透明にする(σ で平滑、``floor`` 未満は 0)。動画でなく
**z スタック**(EM の連続断面: 膜は暗い、蛍光: 細胞は明るい)を同じ立方体として見るため —— 先頭軸を
時間でなく奥行きと読むだけで、断面(``video_cube_cut``)も回転(``video_cube_orbit``)も同じ op で動く。

>>> alpha = video_spacetime_cube(clip, "motion")
>>> color = video_spacetime_cube(clip, "intensity")
>>> rgb = vol_render_transfer(alpha, color, yaw=35.0, pitch=25.0)
>>> membranes = video_spacetime_cube(em_stack, "dark", sigma=1.0)      # ハエの脳の断面を積んだ立方体

## 詳しい使い方ガイド

- [videocube ファミリ ガイド](../guides/videocube.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_video_cube](../../../../examples/poc_video_cube.py) — `py -3.11 examples/poc_video_cube.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[vol_render_transfer](../render/vol_render_transfer.md)

## 同カテゴリ(`cube`)

[video_cube_cut](video_cube_cut.md)

---
*Provenance: videocube.py — VIDEOCUBE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

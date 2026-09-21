---
op: volseq_render_orbit
dim: live4d
category: render
in: volseq
out: rgbvideo
examples: [poc_live4d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# volseq_render_orbit — LIVE4D `render` op

- **データ種**: `volseq` → `rgbvideo`
- **呼び出し**: `import fullseye as fs; fs.ledger.volseq_render_orbit(volseq, n_frames: 'int' = 36, pitch: 'float' = 25.0, yaw_start: 'float' = 0.0, yaw_span: 'float' = 360.0, size: 'int' = 256, mode: 'str' = 'intensity', loops: 'int' = 1, percentile: 'float' = 99.5, floor: 'float' = 0.0, opacity_gain: 'float' = 1.0, depth_samples: 'int | None' = None, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.volseq_render_orbit(volseq, n_frames: 'int' = 36, pitch: 'float' = 25.0, yaw_start: 'float' = 0.0, yaw_span: 'float' = 360.0, size: 'int' = 256, mode: 'str' = 'intensity', loops: 'int' = 1, percentile: 'float' = 99.5, floor: 'float' = 0.0, opacity_gain: 'float' = 1.0, depth_samples: 'int | None' = None, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("volseq_render_orbit")`)

## 使い方

体積時系列を**時間を進めながら視点を回して**描く ``(n_frames, size, size, 3)``(``rgbvideo``)。

フレーム i は時刻 ``t = (i / n_frames) · T · loops mod T``(隣り合う体積の線形補間)の体積を、
yaw ``yaw_start + yaw_span · i / n_frames`` から ``vol_render_transfer`` で合成する。不透明度は明るさ
(系列全体の ``percentile`` で正規化、``floor`` 未満は透明)。``mode="intensity"`` は灰の明るさで、
``mode="speed"`` は隣り合うフレーム間の速さ(``volseq_speed``、青 = 遅い → 赤 = 速い)で塗る。
``loops`` 周ぶん時間を回すと 1 周の軌道で拍動が何回も見える。``video_write_gif`` でそのまま GIF に。

## 詳しい使い方ガイド

- [live4d ファミリ ガイド](../guides/live4d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_live4d](../../../../examples/poc_live4d.py) — `py -3.11 examples/poc_live4d.py`

## 型が繋がる次の op(`rgbvideo` を入力に取れる)

—

## 同カテゴリ(`render`)

[focus_sweep_height_video](focus_sweep_height_video.md) · [focus_sweep_surface_video](focus_sweep_surface_video.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

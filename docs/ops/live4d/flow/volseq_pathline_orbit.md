---
op: volseq_pathline_orbit
dim: live4d
category: flow
in: volseq
out: rgbvideo
examples: [poc_live4d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# volseq_pathline_orbit — LIVE4D `flow` op

- **データ種**: `volseq` → `rgbvideo`
- **呼び出し**: `import fullseye as fs; fs.ledger.volseq_pathline_orbit(volseq, n_frames: 'int' = 36, n_seeds: 'int' = 200, pitch: 'float' = 25.0, size: 'int' = 256, yaw_start: 'float' = 0.0, yaw_span: 'float' = 360.0, static_alpha: 'float' = 0.03, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001, seed: 'int' = 0, trail_sigma: 'float' = 0.7, min_speed: 'float' = 0.1, min_intensity: 'float' = 0.3) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.volseq_pathline_orbit(volseq, n_frames: 'int' = 36, n_seeds: 'int' = 200, pitch: 'float' = 25.0, size: 'int' = 256, yaw_start: 'float' = 0.0, yaw_span: 'float' = 360.0, static_alpha: 'float' = 0.03, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001, seed: 'int' = 0, trail_sigma: 'float' = 0.7, min_speed: 'float' = 0.1, min_intensity: 'float' = 0.3) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("volseq_pathline_orbit")`)

## 使い方

``volseq_pathline_render`` の軌跡の立体を回して見る ``(n_frames, size, size, 3)``(``rgbvideo``)。

流れと軌跡は 1 回だけ計算し、視点だけを ``yaw_start`` から ``yaw_span`` 度ぶん回す。``video_write_gif`` で
そのまま GIF に書ける。

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

## 同カテゴリ(`flow`)

[vol_flow_3d](vol_flow_3d.md) · [volseq_speed](volseq_speed.md) · [volseq_pathline_render](volseq_pathline_render.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

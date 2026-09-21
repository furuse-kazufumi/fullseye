---
op: volseq_synth_dividing
dim: live4d
category: synth
in: 
out: volseq
examples: [poc_live4d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# volseq_synth_dividing — LIVE4D `synth` op

- **データ種**: `なし` → `volseq`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.volseq_synth_dividing(shape=(24, 32, 32), n_frames: 'int' = 24, split_frame: 'int' = 8, speed: 'float' = 0.5, sigma: 'float' = 2.5, axis: 'int' = 3, noise: 'float' = 0.0, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.volseq_synth_dividing(shape=(24, 32, 32), n_frames: 'int' = 24, split_frame: 'int' = 8, speed: 'float' = 0.5, sigma: 'float' = 2.5, axis: 'int' = 3, noise: 'float' = 0.0, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("volseq_synth_dividing")`)

## 使い方

既知の速さで二つに分かれる塊の体積時系列 ``(T, Z, Y, X)``(``volseq``)。

``split_frame`` までは中心に 1 つのガウス塊(標準偏差 ``sigma``)、それ以降は 2 つの塊が ``axis``
(1 = z, 2 = y, 3 = x)に沿って ``±speed · (t − split_frame)`` voxel ずつ離れる(細胞分裂の最小モデル)。
**真値 = 中心の位置**なので、流れ(``vol_flow_3d``)は ``±speed`` の並進、軌跡は直線になるはず。

>>> s = volseq_synth_dividing((16, 24, 24), n_frames=12, split_frame=4, speed=0.5)
>>> s.shape
(12, 16, 24, 24)

## 詳しい使い方ガイド

- [live4d ファミリ ガイド](../guides/live4d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_live4d](../../../../examples/poc_live4d.py) — `py -3.11 examples/poc_live4d.py`

## 型が繋がる次の op(`volseq` を入力に取れる)

[volseq_mip_video](../series/volseq_mip_video.md) · [volseq_cut_video](../series/volseq_cut_video.md) · [volseq_speed](../flow/volseq_speed.md) · [volseq_pathline_render](../flow/volseq_pathline_render.md) · [volseq_pathline_orbit](../flow/volseq_pathline_orbit.md) · [volseq_interpolate_flow](../time/volseq_interpolate_flow.md) · [volseq_magnify_motion](../time/volseq_magnify_motion.md) · [volseq_render_orbit](../render/volseq_render_orbit.md)

## 同カテゴリ(`synth`)

[volseq_synth_beating](volseq_synth_beating.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: volseq_interpolate_flow
dim: live4d
category: time
in: volseq
out: volseq
examples: [poc_live4d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# volseq_interpolate_flow — LIVE4D `time` op

- **データ種**: `volseq` → `volseq`
- **呼び出し**: `import fullseye as fs; fs.ledger.volseq_interpolate_flow(volseq, factor: 'int' = 2, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001, occlusion_tau: 'float' = 1.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.volseq_interpolate_flow(volseq, factor: 'int' = 2, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001, occlusion_tau: 'float' = 1.0) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("volseq_interpolate_flow")`)

## 使い方

体積時系列 ``(T, Z, Y, X)`` を 3 次元の流れで補間して ``(T + (T − 1)(factor − 1), Z, Y, X)`` に(``volseq``)。

``video_interpolate_flow`` と同じ手順の 3 次元版(流れは ``vol_flow_3d``)。ライトシートの z-stack は
時間方向が粗い(1 体積に秒単位)ので、ここを埋めると「回しながら動く」動画になる。

## 詳しい使い方ガイド

- [live4d ファミリ ガイド](../guides/live4d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_live4d](../../../../examples/poc_live4d.py) — `py -3.11 examples/poc_live4d.py`

## 型が繋がる次の op(`volseq` を入力に取れる)

[volseq_mip_video](../series/volseq_mip_video.md) · [volseq_cut_video](../series/volseq_cut_video.md) · [volseq_speed](../flow/volseq_speed.md) · [volseq_pathline_render](../flow/volseq_pathline_render.md) · [volseq_pathline_orbit](../flow/volseq_pathline_orbit.md) · [volseq_magnify_motion](volseq_magnify_motion.md) · [volseq_render_orbit](../render/volseq_render_orbit.md) · [focus_sweep_height_video](../render/focus_sweep_height_video.md)

## 同カテゴリ(`time`)

[video_interpolate_flow](video_interpolate_flow.md) · [volseq_magnify_motion](volseq_magnify_motion.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

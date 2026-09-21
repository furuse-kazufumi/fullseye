---
op: volseq_speed
dim: live4d
category: flow
in: volseq
out: volseq
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# volseq_speed — LIVE4D `flow` op

- **データ種**: `volseq` → `volseq`
- **呼び出し**: `import fullseye as fs; fs.ledger.volseq_speed(volseq, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.volseq_speed(volseq, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 5, reg: 'float' = 0.001) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("volseq_speed")`)

## 使い方

体積時系列の隣り合うフレーム間の**速さ** ``|d|`` [voxel/frame] を ``(T − 1, Z, Y, X)`` で返す(``volseq``)。

各フレーム対に ``vol_flow_3d`` を当てた大きさ。どこが・いつ動いたかの地図で、``volseq_render_orbit(mode="speed")``
の色もこれ。T >= 3 が要る(返りも ``volseq`` = T − 1 >= 2 枚)。

## 詳しい使い方ガイド

- [live4d ファミリ ガイド](../guides/live4d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`volseq` を入力に取れる)

[volseq_mip_video](../series/volseq_mip_video.md) · [volseq_cut_video](../series/volseq_cut_video.md) · [volseq_pathline_render](volseq_pathline_render.md) · [volseq_pathline_orbit](volseq_pathline_orbit.md) · [volseq_interpolate_flow](../time/volseq_interpolate_flow.md) · [volseq_magnify_motion](../time/volseq_magnify_motion.md) · [volseq_render_orbit](../render/volseq_render_orbit.md) · [focus_sweep_height_video](../render/focus_sweep_height_video.md)

## 同カテゴリ(`flow`)

[vol_flow_3d](vol_flow_3d.md) · [volseq_pathline_render](volseq_pathline_render.md) · [volseq_pathline_orbit](volseq_pathline_orbit.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

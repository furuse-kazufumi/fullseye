---
op: piv_replace_outliers
dim: piv
category: validate
in: flow2d × mask
out: flow2d
examples: [piv_flow_from_particles, poc_river_surface_velocity]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# piv_replace_outliers — PIV `validate` op

- **データ種**: `flow2d × mask` → `flow2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.piv_replace_outliers(flow, mask, method='median')` (実装を直接呼ぶなら `import pivops; pivops.piv_replace_outliers(flow, mask, method='median')`、台帳から引くなら `opspiv.get("piv_replace_outliers")`)

## 使い方

外れ値を近傍で埋める。``method="nan"`` なら**埋めずに欠測にする**。

埋めた場所と実測を区別できなくなるのが埋め込みの代償なので、
どこを埋めたかは呼ぶ側が ``mask`` として持っている前提にしてある
(この op は mask を返さない —— 入力として受け取ったものだから)。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_flow_from_particles](../../../../examples/piv_flow_from_particles.py) — `py -3.11 examples/piv_flow_from_particles.py`
- [poc_river_surface_velocity](../../../../examples/poc_river_surface_velocity.py) — `py -3.11 examples/poc_river_surface_velocity.py`

## 型が繋がる次の op(`flow2d` を入力に取れる)

[piv_deform_pass](../estimate/piv_deform_pass.md) · [piv_outlier_mask](piv_outlier_mask.md) · [piv_vorticity](../field/piv_vorticity.md) · [piv_divergence](../field/piv_divergence.md) · [piv_flow_magnitude](../field/piv_flow_magnitude.md) · [piv_to_velocity](../field/piv_to_velocity.md) · [piv_velocity_gradient](../field/piv_velocity_gradient.md) · [piv_q_criterion](../field/piv_q_criterion.md)

## 同カテゴリ(`validate`)

[piv_outlier_mask](piv_outlier_mask.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

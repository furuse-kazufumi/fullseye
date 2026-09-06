---
op: piv_flow_magnitude
dim: piv
category: field
in: flow2d
out: image2d
examples: [piv_field_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_flow_magnitude — PIV `field` op

- **データ種**: `flow2d` → `image2d`
- **呼び出し**: `import pivops; pivops.piv_flow_magnitude(flow)` (または `opspiv.get("piv_flow_magnitude")`)

## 使い方

``sqrt(dy^2 + dx^2)``。向きを捨てる**一方向**の変換。

``reprconv.flow_magnitude`` の 2 次元版。あちらは ``(3, D, H, W)`` 専用で、
ここへ渡すと形で弾かれる(型を分けてある理由がこれ)。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[piv_cross_correlate](../estimate/piv_cross_correlate.md) · [piv_multipass](../estimate/piv_multipass.md) · [piv_deform_pass](../estimate/piv_deform_pass.md) · [strain_from_displacement](../solid/strain_from_displacement.md) · [correlation_quality](../solid/correlation_quality.md) · [speckle_quality](../solid/speckle_quality.md)

## 同カテゴリ(`field`)

[piv_vorticity](piv_vorticity.md) · [piv_divergence](piv_divergence.md) · [piv_to_velocity](piv_to_velocity.md) · [piv_velocity_gradient](piv_velocity_gradient.md) · [piv_q_criterion](piv_q_criterion.md) · [piv_swirling_strength](piv_swirling_strength.md) · [piv_strain_rate](piv_strain_rate.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

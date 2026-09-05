---
op: piv_vorticity
dim: piv
category: field
in: flow2d
out: image2d
examples: [piv_flow_from_particles]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# piv_vorticity — PIV `field` op

- **データ種**: `flow2d` → `image2d`
- **呼び出し**: `import pivops; pivops.piv_vorticity(flow, spacing=1.0)` (または `opspiv.get("piv_vorticity")`)

## 使い方

渦度 ``d(dx)/dy - d(dy)/dx``。**反時計回りが正**(画像座標での定義)。

行が下向きに増える画像座標では、数学の xy 座標と上下が逆になる。この符号を
決めずに書くと渦の向きが黙って反転するので、定義を docstring に固定する。

Args:
    flow: ``(2, h, w)``。
    spacing: 隣り合うベクトルの間隔 [px] (``info["step"]``)。
Returns:
    ``(h, w)``。単位は 1/フレーム(``spacing`` が画素なら)。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_flow_from_particles](../../../../examples/piv_flow_from_particles.py) — `py -3.11 examples/piv_flow_from_particles.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[piv_cross_correlate](../estimate/piv_cross_correlate.md) · [piv_multipass](../estimate/piv_multipass.md) · [piv_deform_pass](../estimate/piv_deform_pass.md)

## 同カテゴリ(`field`)

[piv_divergence](piv_divergence.md) · [piv_flow_magnitude](piv_flow_magnitude.md) · [piv_to_velocity](piv_to_velocity.md) · [piv_velocity_gradient](piv_velocity_gradient.md) · [piv_q_criterion](piv_q_criterion.md) · [piv_swirling_strength](piv_swirling_strength.md) · [piv_strain_rate](piv_strain_rate.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

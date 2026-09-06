---
op: piv_velocity_gradient
dim: piv
category: field
in: flow2d
out: table
examples: [piv_field_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_velocity_gradient — PIV `field` op

- **データ種**: `flow2d` → `table`
- **呼び出し**: `import pivops; pivops.piv_velocity_gradient(flow, spacing=1.0)` (または `opspiv.get("piv_velocity_gradient")`)

## 使い方

速度勾配テンソルの成分と、そこから出る量をまとめて返す。

渦度・発散・Q 基準・渦回転強度・ひずみ速度は**すべて同じ 4 つの微分**から
出るので、勾配を 4 回計算し直さずに済むようにここへまとめる。個々の op
(:func:`piv_vorticity` など)は単独でも使えるが、複数要るならこちら。

Returns:
    dict: ``dudx`` / ``dudy`` / ``dvdx`` / ``dvdy``(各 ``(h, w)``)、
    ``vorticity`` / ``divergence`` / ``q`` / ``swirl`` / ``strain_rate``、
    ``spacing``。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`field`)

[piv_vorticity](piv_vorticity.md) · [piv_divergence](piv_divergence.md) · [piv_flow_magnitude](piv_flow_magnitude.md) · [piv_to_velocity](piv_to_velocity.md) · [piv_q_criterion](piv_q_criterion.md) · [piv_swirling_strength](piv_swirling_strength.md) · [piv_strain_rate](piv_strain_rate.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

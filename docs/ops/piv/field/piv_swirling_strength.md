---
op: piv_swirling_strength
dim: piv
category: field
in: flow2d
out: image2d
examples: [piv_field_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_swirling_strength — PIV `field` op

- **データ種**: `flow2d` → `image2d`
- **呼び出し**: `import pivops; pivops.piv_swirling_strength(flow, spacing=1.0)` (または `opspiv.get("piv_swirling_strength")`)

## 使い方

渦回転強度 λ_ci —— 速度勾配テンソルの複素固有値の虚部の大きさ。

Q 基準と同じく「せん断と渦を区別する」量だが、こちらは**回転の角速度に
等しい単位**を持つ(1/フレーム)。実測: 剛体回転 ω=0.01 で ``0.01``、
一様膨張とせん断で ``0.0``。

固有値が実数(= 回転していない)の場所は 0 を返す。各点で独立な 2x2 の
固有値なので、格子全体をベクトル化して一度に解いている。

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

[piv_vorticity](piv_vorticity.md) · [piv_divergence](piv_divergence.md) · [piv_flow_magnitude](piv_flow_magnitude.md) · [piv_to_velocity](piv_to_velocity.md) · [piv_velocity_gradient](piv_velocity_gradient.md) · [piv_q_criterion](piv_q_criterion.md) · [piv_strain_rate](piv_strain_rate.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

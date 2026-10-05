---
op: largedef_radius_ratio
dim: drive
category: tacdome
in: signal × scalar
out: signal
examples: [poc_tacdome_large_deformation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# largedef_radius_ratio — DRIVE `tacdome` op

- **データ種**: `signal × scalar` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.largedef_radius_ratio(d, p: 'float', method: 'str' = 'quadrature')` (実装を直接呼ぶなら `import tacdome; tacdome.largedef_radius_ratio(d, p: 'float', method: 'str' = 'quadrature')`、台帳から引くなら `opsdrive.get("largedef_radius_ratio")`)

## 使い方

大変形の接触半径の比 a/a_L(式 4)= (1/p)·B_d(1/p, 3/2)·d^{−1/p}/√(1 − d) = ∫₀¹ √((1 − d·uᵖ)/(1 − d)) du。

``method="quadrature"``(既定): 右の積分を 1 に寄せた複合 Gauss–Legendre で。``"beta"``: 原文の形どおり不完全ベータの
連分数で(別の経路、照合用)。p = ∞(平頭)は非圧縮の半径の伸び 1/√(1 − d)。d → 0 で 1 + d·p/(2(p+1))。
p = 1・2 の閉形式は (2/(3d))(1 − (1 − d)^{3/2})/√(1 − d) と [√(1−d)/2 + atan2(√d, √(1−d))/(2√d)]/√(1 − d)。
**Raises** ``ValueError``: d が [0, 1) の外、p が範囲外、method の綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacdome_large_deformation](../../../../examples/poc_tacdome_large_deformation.py) — `py -3.11 examples/poc_tacdome_large_deformation.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`tacdome`)

[powerlaw_linear_contact](powerlaw_linear_contact.md) · [largedef_correction](largedef_correction.md) · [largedef_universal_correction](largedef_universal_correction.md) · [large_deformation_contact](large_deformation_contact.md) · [large_deformation_inverse](large_deformation_inverse.md) · [mdr_spring_bed](mdr_spring_bed.md) · [neohookean_cylinder_exact](neohookean_cylinder_exact.md) · [hertz_small_strain_error](hertz_small_strain_error.md)

---
*Provenance: tacdome.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: largedef_universal_correction
dim: drive
category: tacdome
in: signal
out: signal
examples: [poc_tacdome_large_deformation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# largedef_universal_correction — DRIVE `tacdome` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.largedef_universal_correction(d, k: 'float' = 1.1111111111111112)` (実装を直接呼ぶなら `import tacdome; tacdome.largedef_universal_correction(d, k: 'float' = 1.1111111111111112)`、台帳から引くなら `opsdrive.get("largedef_universal_correction")`)

## 使い方

普遍形の補正 κ(d) = (1 − k·d)⁻¹(式 6、k = 10/9)。**Raises** ``ValueError``: d が [0, 1) の外、k·d ≥ 1、k ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacdome_large_deformation](../../../../examples/poc_tacdome_large_deformation.py) — `py -3.11 examples/poc_tacdome_large_deformation.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`tacdome`)

[powerlaw_linear_contact](powerlaw_linear_contact.md) · [largedef_correction](largedef_correction.md) · [largedef_radius_ratio](largedef_radius_ratio.md) · [large_deformation_contact](large_deformation_contact.md) · [large_deformation_inverse](large_deformation_inverse.md) · [mdr_spring_bed](mdr_spring_bed.md) · [neohookean_cylinder_exact](neohookean_cylinder_exact.md) · [hertz_small_strain_error](hertz_small_strain_error.md)

---
*Provenance: tacdome.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

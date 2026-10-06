---
op: neohookean_cylinder_exact
dim: drive
category: tacdome
in: signal
out: table
examples: [poc_tacdome_large_deformation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# neohookean_cylinder_exact — DRIVE `tacdome` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.neohookean_cylinder_exact(d, mu: 'float' = 1.0, area: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import tacdome; tacdome.neohookean_cylinder_exact(d, mu: 'float' = 1.0, area: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsdrive.get("neohookean_cylinder_exact")`)

## 使い方

非圧縮 neo-Hookean の円柱を摩擦なしで一軸に圧縮する厳密解(連続体の教科書の結果、模型と独立)。

伸び λ = 1 − d、横は λ^{−1/2}(体積一定)。公称応力 P = μ(λ⁻² − λ)(圧縮を正)、Cauchy 応力 σ = μ(λ⁻¹ − λ²)、力 F = P·area、
線形の力 3μ·d·area(E = 3μ)、``kappa`` = F/線形、``radius_ratio`` = λ^{−1/2}。
**Raises** ``ValueError``: d が [0, 1) の外、μ・area ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacdome_large_deformation](../../../../examples/poc_tacdome_large_deformation.py) — `py -3.11 examples/poc_tacdome_large_deformation.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacdome`)

[powerlaw_linear_contact](powerlaw_linear_contact.md) · [largedef_correction](largedef_correction.md) · [largedef_radius_ratio](largedef_radius_ratio.md) · [largedef_universal_correction](largedef_universal_correction.md) · [large_deformation_contact](large_deformation_contact.md) · [large_deformation_inverse](large_deformation_inverse.md) · [mdr_spring_bed](mdr_spring_bed.md) · [hertz_small_strain_error](hertz_small_strain_error.md)

---
*Provenance: tacdome.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

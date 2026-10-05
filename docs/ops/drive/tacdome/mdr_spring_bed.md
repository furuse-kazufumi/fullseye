---
op: mdr_spring_bed
dim: drive
category: tacdome
in: scalar × scalar × table
out: table
examples: [poc_tacdome_large_deformation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# mdr_spring_bed — DRIVE `tacdome` op

- **データ種**: `scalar × scalar × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mdr_spring_bed(delta: 'float', L: 'float', lin: 'dict', n_springs: 'int' = 4000) -> 'dict'` (実装を直接呼ぶなら `import tacdome; tacdome.mdr_spring_bed(delta: 'float', L: 'float', lin: 'dict', n_springs: 'int' = 4000) -> 'dict'`、台帳から引くなら `opsdrive.get("mdr_spring_bed")`)

## 使い方

1D の非線形ばね列を中点則で直接積分する(閉形式 :func:`largedef_correction` / :func:`largedef_radius_ratio` の第 2 実装)。

ばね x ∈ [0, a_L] (片側、力は 2 倍): MDR の断面 g = g_coef·xᵖ、長さ ℓ = L − g、伸び λ = (L − δ)/ℓ、力 E*·dx·ℓ·(λ⁻² − λ)/3
(線形の極限で E*·dx·(δ − g) = MDR)、幅は λ^{−1/2} 倍。平頭は g = 0(全部 λ = 1 − d)。返り: ``x``・``g``・``length``・
``stretch``・``width_factor``・``x_deformed``(幅の累積 = 変形後の位置)・``F``・``F_lin``・``kappa``(= F/F_lin)・``a``・
``radius_ratio``(= a/a_L)・``strain_max``・``spring_force``(dF/dx)。
**Raises** ``ValueError``: n_springs < 16、δ/L が (0, 1) の外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacdome_large_deformation](../../../../examples/poc_tacdome_large_deformation.py) — `py -3.11 examples/poc_tacdome_large_deformation.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacdome`)

[powerlaw_linear_contact](powerlaw_linear_contact.md) · [largedef_correction](largedef_correction.md) · [largedef_radius_ratio](largedef_radius_ratio.md) · [largedef_universal_correction](largedef_universal_correction.md) · [large_deformation_contact](large_deformation_contact.md) · [large_deformation_inverse](large_deformation_inverse.md) · [neohookean_cylinder_exact](neohookean_cylinder_exact.md) · [hertz_small_strain_error](hertz_small_strain_error.md)

---
*Provenance: tacdome.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

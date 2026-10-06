---
op: large_deformation_contact
dim: drive
category: tacdome
in: any × scalar × table
out: table
examples: [poc_tacdome_large_deformation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# large_deformation_contact — DRIVE `tacdome` op

- **データ種**: `any × scalar × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.large_deformation_contact(delta, L: 'float', lin: 'dict', reading: 'str' = 'derived') -> 'dict'` (実装を直接呼ぶなら `import tacdome; tacdome.large_deformation_contact(delta, L: 'float', lin: 'dict', reading: 'str' = 'derived') -> 'dict'`、台帳から引くなら `opsdrive.get("large_deformation_contact")`)

## 使い方

押し込み δ(スカラーか配列)から大変形の力と接触半径(式 2・4)と、同じ δ の線形解(Hertz)との差。

返り: ``d``・``delta``・``F_L``(線形)・``a_L``・``kappa``・``F``(= κ F_L)・``radius_ratio``・``a``・``F_universal``
(式 6、k·d ≥ 1 は inf)・``F_hertz_from_radius``(測った a を線形解で読んだ力、平頭は nan)・``err_force_from_delta_pct``
(F_L/F − 1)・``err_radius_from_delta_pct``(a_L/a − 1)・``err_force_from_radius_pct``・``beyond_validated``(d > 0.5)。
**Raises** ``ValueError``: δ ≤ 0 か δ ≥ L、L ≤ 0、lin が powerlaw_linear_contact の表でない、読みの綴り違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacdome_large_deformation](../../../../examples/poc_tacdome_large_deformation.py) — `py -3.11 examples/poc_tacdome_large_deformation.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacdome`)

[powerlaw_linear_contact](powerlaw_linear_contact.md) · [largedef_correction](largedef_correction.md) · [largedef_radius_ratio](largedef_radius_ratio.md) · [largedef_universal_correction](largedef_universal_correction.md) · [large_deformation_inverse](large_deformation_inverse.md) · [mdr_spring_bed](mdr_spring_bed.md) · [neohookean_cylinder_exact](neohookean_cylinder_exact.md) · [hertz_small_strain_error](hertz_small_strain_error.md)

---
*Provenance: tacdome.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

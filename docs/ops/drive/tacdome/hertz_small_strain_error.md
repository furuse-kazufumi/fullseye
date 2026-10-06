---
op: hertz_small_strain_error
dim: drive
category: tacdome
in: signal × scalar
out: table
examples: [poc_tacdome_large_deformation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# hertz_small_strain_error — DRIVE `tacdome` op

- **データ種**: `signal × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.hertz_small_strain_error(d, p: 'float', reading: 'str' = 'derived') -> 'dict'` (実装を直接呼ぶなら `import tacdome; tacdome.hertz_small_strain_error(d, p: 'float', reading: 'str' = 'derived') -> 'dict'`、台帳から引くなら `opsdrive.get("hertz_small_strain_error")`)

## 使い方

小変形の線形解(Hertz)を大変形に当てたときの誤差 [%] (d だけで決まり、L・寸法・弾性率に依らない)。

``force_from_delta`` = 1/κₙ − 1(押し込みから力を読む)、``radius_from_delta`` = 1/(a/a_L) − 1、``force_from_radius`` =
(a/a_L)^{p+1}/κₙ − 1(接触半径から力を読む = 視触覚センサの読み方、平頭は nan)、``force_universal`` = 普遍形 (1 − k d)⁻¹ で読んだ力の誤差
κ_universal/κₙ − 1(k·d ≥ 1 は nan)。
**Raises** ``ValueError``: d が [0, 1) の外、p が範囲外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacdome_large_deformation](../../../../examples/poc_tacdome_large_deformation.py) — `py -3.11 examples/poc_tacdome_large_deformation.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacdome`)

[powerlaw_linear_contact](powerlaw_linear_contact.md) · [largedef_correction](largedef_correction.md) · [largedef_radius_ratio](largedef_radius_ratio.md) · [largedef_universal_correction](largedef_universal_correction.md) · [large_deformation_contact](large_deformation_contact.md) · [large_deformation_inverse](large_deformation_inverse.md) · [mdr_spring_bed](mdr_spring_bed.md) · [neohookean_cylinder_exact](neohookean_cylinder_exact.md)

---
*Provenance: tacdome.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: cerruti_surface_displacement
dim: drive
category: tacslip
in: matrix × table
out: table
examples: [poc_tacsim_marker_shear]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# cerruti_surface_displacement — DRIVE `tacslip` op

- **データ種**: `matrix × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cerruti_surface_displacement(qx, kern: 'dict') -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.cerruti_surface_displacement(qx, kern: 'dict') -> 'dict'`、台帳から引くなら `opsdrive.get("cerruti_surface_displacement")`)

## 使い方

接線トラクション分布 qx (n, n) [Pa] → 表面変位 ``ux``・``uy``(核に ``Kzx`` があれば ``uz``)(n, n) [m]。零詰め 2n の線形畳み込み
(巻き込みなし)。**Raises** ValueError: qx が (n, n) でない、kern が :func:`cerruti_kernel` の表でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md) · [displace_markers](displace_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: mindlin_partial_slip
dim: drive
category: tacslip
in: scalar × table × scalar × scalar × scalar
out: table
examples: [poc_tacsim_marker_shear, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# mindlin_partial_slip — DRIVE `tacslip` op

- **データ種**: `scalar × table × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mindlin_partial_slip(Q: 'float', hz: 'dict', mu: 'float', G: 'float', nu: 'float') -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.mindlin_partial_slip(Q: 'float', hz: 'dict', mu: 'float', G: 'float', nu: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("mindlin_partial_slip")`)

## 使い方

Cattaneo–Mindlin の部分滑り(Johnson 1985 §7.2): 球を法線 P で押したまま接線 Q を掛ける。

``hz`` は :func:`tacsim.hertz_sphere` の表(a・F・p0)。返り: ``c``(固着半径 = a(1 − Q/μP)^{1/3})、``c_over_a``、``q_ratio`` = Q/μP、
``delta_x``(剛体球の接線変位 3μP(2−ν)/(16Ga)[1 − (1−Q/μP)^{2/3}])、``k_t``(初期接線剛性 8Ga/(2−ν))、``slipping``(Q ≥ μP で True =
全滑り。例外にせず印で返す: 滑りは物理的に起きる状態で入力の誤りではない)、入力の写し(``Q``・``muP``・``a``・``P``・``mu``・``G``・``nu``・``p0``)。
**Raises** ValueError: Q < 0、μ ≤ 0、G ≤ 0、ν が [0, 0.5] の外、hz に a/F/p0 が無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`
- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md) · [displace_markers](displace_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

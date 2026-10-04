---
op: fem_vs_halfspace
dim: drive
category: tacslip
in: table × table
out: table
examples: [poc_tacsim_marker_shear]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# fem_vs_halfspace — DRIVE `tacslip` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fem_vs_halfspace(fz: 'dict', fxz: 'dict') -> 'dict'` (実装を直接呼ぶなら `import tacslip; tacslip.fem_vs_halfspace(fz: 'dict', fxz: 'dict') -> 'dict'`、台帳から引くなら `opsdrive.get("fem_vs_halfspace")`)

## 使い方

同じ節点集合の法線押し込み ``fz`` と斜め押し込み ``fxz``(:func:`fem_nodes_load`)を半空間解と**形だけ**比べる(荷重の大きさは不明)。
(1) r·dz を 0.5〜0.8 mm で 1 に正規化(``mids``・``rdz_n``): 半空間 Boussinesq は r ≫ 接触で一定、有限厚は落ちる。1/r から 2 倍外れる
半径 ``r_half``(無ければ None)。(2) 斜め押し込みの dx(θ) を r = 1/1.5/2/3 mm の環で A + B cos²θ に当てる(``ang``: Cerruti なら
B/A = ν/(1−ν) → ``nu``、``ratio`` = (A+B)/A、``R2``)、dy を A + B sin2θ に(``dy_fit``)。``R_dome``(表面の r–z を球冠に当てた半径)、
``dy_over_dz0``(法線だけでも出ている接線成分 = 非対称の量)、``rdx_n``、``dz0``、``dx_min_spacing``、``r``・``th``(中心相対)も返す。
**Raises** ValueError: 2 つの表の節点数が違う、節点が 10 個未満。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

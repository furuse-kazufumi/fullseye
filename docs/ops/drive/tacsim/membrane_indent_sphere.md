---
op: membrane_indent_sphere
dim: drive
category: tacsim
in: table
out: table
examples: [poc_tacsim_elastic_membrane]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# membrane_indent_sphere — DRIVE `tacsim` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.membrane_indent_sphere(hz: 'dict', n: 'int' = 256, fov: 'float' = 0.016) -> 'dict'` (実装を直接呼ぶなら `import tacsim; tacsim.membrane_indent_sphere(hz: 'dict', n: 'int' = 256, fov: 'float' = 0.016) -> 'dict'`、台帳から引くなら `opsdrive.get("membrane_indent_sphere")`)

## 使い方

球押し込みのゲル膜の高さ場 h(x, y) = −ū_z(r)[m] (:func:`hertz_sphere` の表から)と解析的な法線。

``n`` 画素四方、視野 ``fov`` [m] (画素ピッチ fov/n)。法線は ū_z の半径微分を中心差分(刻み pitch/4)で取り
(−∂h/∂x, −∂h/∂y, 1)/|·|。返り: ``h``(n, n)、``normals``(n, n, 3)、``pitch``、``X``・``Y``・``r``(n, n)、``contact``(r < a の bool)、
``hz``。窓は接触半径の 5 倍以上ないと遠方場の裾で高さの基準が沈む(**Raises** ``ValueError``: fov < 5a、hz に a/delta/R が無い)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_elastic_membrane](../../../../examples/poc_tacsim_elastic_membrane.py) — `py -3.11 examples/poc_tacsim_elastic_membrane.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacsim`)

[combined_modulus](combined_modulus.md) · [hertz_sphere](hertz_sphere.md) · [hertz_force](hertz_force.md) · [hertz_cylinder](hertz_cylinder.md) · [hertz_surface_uz](hertz_surface_uz.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_shape](membrane_indent_shape.md) · [membrane_lights](membrane_lights.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

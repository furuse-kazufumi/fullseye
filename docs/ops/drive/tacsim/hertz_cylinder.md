---
op: hertz_cylinder
dim: drive
category: tacsim
in: scalar × scalar × scalar
out: table
examples: [poc_tacsim_elastic_membrane]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# hertz_cylinder — DRIVE `tacsim` op

- **データ種**: `scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.hertz_cylinder(F_per_L: 'float', R: 'float', Estar: 'float') -> 'dict'` (実装を直接呼ぶなら `import tacsim; tacsim.hertz_cylinder(F_per_L: 'float', R: 'float', Estar: 'float') -> 'dict'`、台帳から引くなら `opsdrive.get("hertz_cylinder")`)

## 使い方

円柱(半径 R)を弾性半空間に線荷重 F/L で押す線接触(Johnson 1985 §4.2): 接触半幅 b = √(4(F/L)R/(πE*))、p0 = 2(F/L)/(πb)。

返り: ``b``、``p0``、``pm`` = (F/L)/(2b) = (π/4)p0、入力。2-D の押し込み δ は対数的で参照点に依存するため返さない。
**Raises** ``ValueError``: ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_elastic_membrane](../../../../examples/poc_tacsim_elastic_membrane.py) — `py -3.11 examples/poc_tacsim_elastic_membrane.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`tacsim`)

[combined_modulus](combined_modulus.md) · [hertz_sphere](hertz_sphere.md) · [hertz_force](hertz_force.md) · [hertz_surface_uz](hertz_surface_uz.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_sphere](membrane_indent_sphere.md) · [membrane_indent_shape](membrane_indent_shape.md) · [membrane_lights](membrane_lights.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

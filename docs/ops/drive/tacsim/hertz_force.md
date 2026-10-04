---
op: hertz_force
dim: drive
category: tacsim
in: scalar × scalar
out: scalar
examples: [poc_tacsim_elastic_membrane]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# hertz_force — DRIVE `tacsim` op

- **データ種**: `scalar × scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.hertz_force(R: 'float', Estar: 'float', a: 'float | None' = None, delta: 'float | None' = None) -> 'float'` (実装を直接呼ぶなら `import tacsim; tacsim.hertz_force(R: 'float', Estar: 'float', a: 'float | None' = None, delta: 'float | None' = None) -> 'float'`、台帳から引くなら `opsdrive.get("hertz_force")`)

## 使い方

Hertz の逆算: 接触半径 a か押し込み δ のどちらか一方から荷重 F。F = 4E*a³/(3R) = (4/3) E* √R δ^{3/2}。

**Raises** ``ValueError``: a と δ の両方(または両方なし)、値が ≤ 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_elastic_membrane](../../../../examples/poc_tacsim_elastic_membrane.py) — `py -3.11 examples/poc_tacsim_elastic_membrane.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`tacsim`)

[combined_modulus](combined_modulus.md) · [hertz_sphere](hertz_sphere.md) · [hertz_cylinder](hertz_cylinder.md) · [hertz_surface_uz](hertz_surface_uz.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_sphere](membrane_indent_sphere.md) · [membrane_indent_shape](membrane_indent_shape.md) · [membrane_lights](membrane_lights.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

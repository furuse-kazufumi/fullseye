---
op: combined_modulus
dim: drive
category: tacsim
in: scalar × scalar
out: scalar
examples: [poc_tacsim_elastic_membrane]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# combined_modulus — DRIVE `tacsim` op

- **データ種**: `scalar × scalar` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.combined_modulus(E1: 'float', nu1: 'float', E2: 'float | None' = None, nu2: 'float' = 0.0) -> 'float'` (実装を直接呼ぶなら `import tacsim; tacsim.combined_modulus(E1: 'float', nu1: 'float', E2: 'float | None' = None, nu2: 'float' = 0.0) -> 'float'`、台帳から引くなら `opsdrive.get("combined_modulus")`)

## 使い方

複合弾性率 E*: 1/E* = (1 − ν1²)/E1 + (1 − ν2²)/E2(Johnson 1985 式 4.9)。``E2=None`` は剛体の押し込み子(第 2 項 0)。

**Raises** ``ValueError``: E ≤ 0、|ν| ≥ 1(Poisson 比は (−1, 0.5] が物理的だが上限は見ない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacsim_elastic_membrane](../../../../examples/poc_tacsim_elastic_membrane.py) — `py -3.11 examples/poc_tacsim_elastic_membrane.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`tacsim`)

[hertz_sphere](hertz_sphere.md) · [hertz_force](hertz_force.md) · [hertz_cylinder](hertz_cylinder.md) · [hertz_surface_uz](hertz_surface_uz.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_sphere](membrane_indent_sphere.md) · [membrane_indent_shape](membrane_indent_shape.md) · [membrane_lights](membrane_lights.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

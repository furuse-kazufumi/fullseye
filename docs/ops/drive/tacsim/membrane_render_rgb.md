---
op: membrane_render_rgb
dim: drive
category: tacsim
in: normalmap × matrix
out: rgb
examples: [poc_knife_tactile_toughness, poc_tacsim_elastic_membrane, poc_tacsim_marker_shear, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# membrane_render_rgb — DRIVE `tacsim` op

- **データ種**: `normalmap × matrix` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.membrane_render_rgb(normals, lights, albedo: 'float' = 1.0, ambient: 'float' = 0.03, noise: 'float' = 0.0, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import tacsim; tacsim.membrane_render_rgb(normals, lights, albedo: 'float' = 1.0, ambient: 'float' = 0.03, noise: 'float' = 0.0, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("membrane_render_rgb")`)

## 使い方

法線場 (H, W, 3) + 光源 (3, 3) → 視触覚センサ風の RGB (H, W, 3) float。チャネル k = 光源 k の Lambertian 像
albedo·(max(N·L_k, 0) + ambient)(:func:`photometric.render_lambertian` を 3 回、第 2 実装)。``noise`` > 0 なら正規乱数を足す。

**Raises** ``ValueError``: normals が (H, W, 3) でない、lights が (3, 3) でない、noise < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_knife_tactile_toughness](../../../../examples/poc_knife_tactile_toughness.py) — `py -3.11 examples/poc_knife_tactile_toughness.py`
- [poc_tacsim_elastic_membrane](../../../../examples/poc_tacsim_elastic_membrane.py) — `py -3.11 examples/poc_tacsim_elastic_membrane.py`
- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`
- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_depth_decode](../carla/carla_depth_decode.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md)

## 同カテゴリ(`tacsim`)

[combined_modulus](combined_modulus.md) · [hertz_sphere](hertz_sphere.md) · [hertz_force](hertz_force.md) · [hertz_cylinder](hertz_cylinder.md) · [hertz_surface_uz](hertz_surface_uz.md) · [hertz_pressure](hertz_pressure.md) · [membrane_indent_sphere](membrane_indent_sphere.md) · [membrane_indent_shape](membrane_indent_shape.md)

---
*Provenance: tacsim.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

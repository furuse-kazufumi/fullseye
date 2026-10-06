---
op: membrane_render_markers
dim: drive
category: tacslip
in: rgb × matrix × scalar × scalar
out: rgb
examples: [poc_knife_tactile_toughness, poc_tacsim_marker_shear, poc_tactile_dipole_torque]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# membrane_render_markers — DRIVE `tacslip` op

- **データ種**: `rgb × matrix × scalar × scalar` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.membrane_render_markers(rgb, pts, r_px: 'float', dark: 'float', sub: 'int' = 8) -> 'np.ndarray'` (実装を直接呼ぶなら `import tacslip; tacslip.membrane_render_markers(rgb, pts, r_px: 'float', dark: 'float', sub: 'int' = 8) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("membrane_render_markers")`)

## 使い方

RGB (H, W, 3) に黒い円盤のマーカー(中心 pts (N, 2) [px]、半径 r_px)を描く: 画素の被覆率で rgb *= 1 − dark·coverage。
被覆率は円盤の縁の画素だけ sub² の副標本(内側 1・外側 0)。像を補間して歪めないので真値が厳密。
**Raises** ValueError: rgb が (H, W, 3) でない、pts が (N, 2) でない、r_px ≤ 0、dark が [0, 1] の外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_knife_tactile_toughness](../../../../examples/poc_knife_tactile_toughness.py) — `py -3.11 examples/poc_knife_tactile_toughness.py`
- [poc_tacsim_marker_shear](../../../../examples/poc_tacsim_marker_shear.py) — `py -3.11 examples/poc_tacsim_marker_shear.py`
- [poc_tactile_dipole_torque](../../../../examples/poc_tactile_dipole_torque.py) — `py -3.11 examples/poc_tactile_dipole_torque.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_depth_decode](../carla/carla_depth_decode.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md)

## 同カテゴリ(`tacslip`)

[mindlin_partial_slip](mindlin_partial_slip.md) · [mindlin_traction](mindlin_traction.md) · [hertz_surface_ur](hertz_surface_ur.md) · [hertzian_tangential_inner](hertzian_tangential_inner.md) · [cerruti_kernel](cerruti_kernel.md) · [cerruti_surface_displacement](cerruti_surface_displacement.md) · [membrane_shear_field](membrane_shear_field.md) · [membrane_markers](membrane_markers.md)

---
*Provenance: tacslip.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: membrane_predict_rgb
dim: drive
category: tacscalib
in: normalmap × table
out: rgb
examples: [poc_tacscalib_sphere_lut]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# membrane_predict_rgb — DRIVE `tacscalib` op

- **データ種**: `normalmap × table` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.membrane_predict_rgb(normals, fit: 'dict') -> 'np.ndarray'` (実装を直接呼ぶなら `import tacscalib; tacscalib.membrane_predict_rgb(normals, fit: 'dict') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("membrane_predict_rgb")`)

## 使い方

法線 (H, W, 3) + :func:`lights_fit_from_sphere` の結果 → 背景差分 RGB の予測 (H, W, 3)(線形、クリップしない)。
order 2 の結果は画素ごとに a(x, y)・L(x, y) を作る(画像の大きさは較正時と同じであること)。
**Raises** ``ValueError``: 法線の形 / order 2 で画像の大きさが違う。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tacscalib_sphere_lut](../../../../examples/poc_tacscalib_sphere_lut.py) — `py -3.11 examples/poc_tacscalib_sphere_lut.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_depth_decode](../carla/carla_depth_decode.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md)

## 同カテゴリ(`tacscalib`)

[calib_pack_load](calib_pack_load.md) · [sphere_normals_known](sphere_normals_known.md) · [lights_fit_from_sphere](lights_fit_from_sphere.md) · [gradient_lut_build](gradient_lut_build.md) · [gradient_lut_invert](gradient_lut_invert.md) · [normal_error_map](normal_error_map.md) · [sphere_cap_height](sphere_cap_height.md) · [field_position_sweep](field_position_sweep.md)

---
*Provenance: tacscalib.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

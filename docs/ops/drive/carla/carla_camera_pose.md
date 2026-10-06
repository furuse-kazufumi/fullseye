---
op: carla_camera_pose
dim: drive
category: carla
in: any
out: matrix
examples: [poc_carla_bridge]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# carla_camera_pose — DRIVE `carla` op

- **データ種**: `any` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.carla_camera_pose(cam_transform6) -> 'np.ndarray'` (実装を直接呼ぶなら `import carlabridge; carlabridge.carla_camera_pose(cam_transform6) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("carla_camera_pose")`)

## 使い方

CARLA のカメラの世界姿勢 → render3d / driveworld の **world → camera** 4×4(:func:`driveworld.camera_pose` と同じ型)。
CARLA のカメラは局所 +x を見て右 = +y・上 = +z、render3d は −z を見て右 = +x・上 = +y。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_carla_bridge](../../../../examples/poc_carla_bridge.py) — `py -3.11 examples/poc_carla_bridge.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`carla`)

[carla_labels](carla_labels.md) · [carla_label_map](carla_label_map.md) · [carla_label_unmap](carla_label_unmap.md) · [carla_depth_decode](carla_depth_decode.md) · [carla_depth_encode](carla_depth_encode.md) · [carla_intrinsics](carla_intrinsics.md) · [intrinsics_to_fullseye](intrinsics_to_fullseye.md) · [intrinsics_to_carla](intrinsics_to_carla.md)

---
*Provenance: carlabridge.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

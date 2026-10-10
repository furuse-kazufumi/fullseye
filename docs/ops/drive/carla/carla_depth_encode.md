---
op: carla_depth_encode
dim: drive
category: carla
in: image2d
out: rgb
examples: [poc_carla_bridge]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# carla_depth_encode — DRIVE `carla` op

- **データ種**: `image2d` → `rgb`
- **呼び出し**: `import fullseye as fs; fs.ledger.carla_depth_encode(depth_m) -> 'np.ndarray'` (実装を直接呼ぶなら `import carlabridge; carlabridge.carla_depth_encode(depth_m) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("carla_depth_encode")`)

## 使い方

像面からの距離 [m] → CARLA の生の深度像(uint8 (H,W,3))。inf と 1000 m 超は最大値、負と NaN は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_carla_bridge](../../../../examples/poc_carla_bridge.py) — `py -3.11 examples/poc_carla_bridge.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_depth_decode](carla_depth_decode.md) · [carla_transform_matrix](carla_transform_matrix.md) · [carla_pose_to_world](carla_pose_to_world.md) · [carla_camera_pose](carla_camera_pose.md) · [carla_xy_yaw](carla_xy_yaw.md) · [carla_scene_load](carla_scene_load.md) · [town_chain](../town/town_chain.md)

## 同カテゴリ(`carla`)

[carla_labels](carla_labels.md) · [carla_label_map](carla_label_map.md) · [carla_label_unmap](carla_label_unmap.md) · [carla_depth_decode](carla_depth_decode.md) · [carla_intrinsics](carla_intrinsics.md) · [intrinsics_to_fullseye](intrinsics_to_fullseye.md) · [intrinsics_to_carla](intrinsics_to_carla.md) · [carla_rotation_matrix](carla_rotation_matrix.md)

---
*Provenance: carlabridge.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

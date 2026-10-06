---
op: intrinsics_to_fullseye
dim: drive
category: carla
in: matrix
out: matrix
examples: [poc_carla_bridge]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# intrinsics_to_fullseye — DRIVE `carla` op

- **データ種**: `matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.intrinsics_to_fullseye(K) -> 'np.ndarray'` (実装を直接呼ぶなら `import carlabridge; carlabridge.intrinsics_to_fullseye(K) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("intrinsics_to_fullseye")`)

## 使い方

CARLA の K(画素の角が整数、主点 W/2)→ Fullseye / render3d の K(画素の中心が整数、主点 (W−1)/2)。主点を 0.5 ずらすだけ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_carla_bridge](../../../../examples/poc_carla_bridge.py) — `py -3.11 examples/poc_carla_bridge.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[world_camera](../world/world_camera.md) · [lidar_scan](../lidar/lidar_scan.md) · [relative_motion](../ttc/relative_motion.md) · [foe_from_motion](../ttc/foe_from_motion.md) · [flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [world_materials](../terrain/world_materials.md) · [mesh_signed_volume](../terrain/mesh_signed_volume.md)

## 同カテゴリ(`carla`)

[carla_labels](carla_labels.md) · [carla_label_map](carla_label_map.md) · [carla_label_unmap](carla_label_unmap.md) · [carla_depth_decode](carla_depth_decode.md) · [carla_depth_encode](carla_depth_encode.md) · [carla_intrinsics](carla_intrinsics.md) · [intrinsics_to_carla](intrinsics_to_carla.md) · [carla_rotation_matrix](carla_rotation_matrix.md)

---
*Provenance: carlabridge.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

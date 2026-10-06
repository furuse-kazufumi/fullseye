---
op: camera_pose_to_carla
dim: drive
category: carla
in: matrix
out: any
examples: [poc_carla_bridge]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# camera_pose_to_carla — DRIVE `carla` op

- **データ種**: `matrix` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.camera_pose_to_carla(pose) -> 'np.ndarray'` (実装を直接呼ぶなら `import carlabridge; carlabridge.camera_pose_to_carla(pose) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("camera_pose_to_carla")`)

## 使い方

render3d の world → camera 4×4 → CARLA のカメラの [x, y, z, roll, pitch, yaw]。:func:`carla_camera_pose` の逆。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_carla_bridge](../../../../examples/poc_carla_bridge.py) — `py -3.11 examples/poc_carla_bridge.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`carla`)

[carla_labels](carla_labels.md) · [carla_label_map](carla_label_map.md) · [carla_label_unmap](carla_label_unmap.md) · [carla_depth_decode](carla_depth_decode.md) · [carla_depth_encode](carla_depth_encode.md) · [carla_intrinsics](carla_intrinsics.md) · [intrinsics_to_fullseye](intrinsics_to_fullseye.md) · [intrinsics_to_carla](intrinsics_to_carla.md)

---
*Provenance: carlabridge.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

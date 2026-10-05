---
op: lead_from_depth
dim: drive
category: carla
in: image2d × image2d × matrix
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# lead_from_depth — DRIVE `carla` op

- **データ種**: `image2d × image2d × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lead_from_depth(depth, label, K, cam_height: 'float', *, pitch: 'float' = 0.0, band: 'float' = 0.5, car_label: 'int' = 2) -> 'dict'` (実装を直接呼ぶなら `import carlabridge; carlabridge.lead_from_depth(depth, label, K, cam_height: 'float', *, pitch: 'float' = 0.0, band: 'float' = 0.5, car_label: 'int' = 2) -> 'dict'`、台帳から引くなら `opsdrive.get("lead_from_depth")`)

## 使い方

ルールベースの先行車の距離(両方の世界に同じ式):
``depth_median`` = 画像の中央の帯(幅 band × W)にある車の画素の深度の中央値(後ろ面は像面に平行なので一定)、
``row_distance`` = 車の最下行から平らな路面の式(driveenv.road_row_distance)で出した水平距離、
``bbox`` = (top, bottom, left, right)、``n_pixels``、``found``。車の画素が無ければ found = False(距離は inf)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`carla`)

[carla_labels](carla_labels.md) · [carla_label_map](carla_label_map.md) · [carla_label_unmap](carla_label_unmap.md) · [carla_depth_decode](carla_depth_decode.md) · [carla_depth_encode](carla_depth_encode.md) · [carla_intrinsics](carla_intrinsics.md) · [intrinsics_to_fullseye](intrinsics_to_fullseye.md) · [intrinsics_to_carla](intrinsics_to_carla.md)

---
*Provenance: carlabridge.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

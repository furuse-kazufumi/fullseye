---
op: scene_pair_table
dim: drive
category: carla
in: table
out: table
examples: [poc_carla_bridge]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# scene_pair_table — DRIVE `carla` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.scene_pair_table(scene, *, lead_asset: 'str' = 'sedan', asset_root=None) -> 'dict'` (実装を直接呼ぶなら `import carlabridge; carlabridge.scene_pair_table(scene, *, lead_asset: 'str' = 'sedan', asset_root=None) -> 'dict'`、台帳から引くなら `opsdrive.get("scene_pair_table")`)

## 使い方

1 つの場面記録を **CARLA の像**と**自前の世界の像**の両方で採点して並べる。
返り値 = ``{"truth", "carla": {...lead_from_depth}, "fullseye": {...}, "carla_error", "fullseye_error", "width", "height"}``
(誤差 = depth_median − 真値、真値は :func:`lead_truth_depth`)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_carla_bridge](../../../../examples/poc_carla_bridge.py) — `py -3.11 examples/poc_carla_bridge.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`carla`)

[carla_labels](carla_labels.md) · [carla_label_map](carla_label_map.md) · [carla_label_unmap](carla_label_unmap.md) · [carla_depth_decode](carla_depth_decode.md) · [carla_depth_encode](carla_depth_encode.md) · [carla_intrinsics](carla_intrinsics.md) · [intrinsics_to_fullseye](intrinsics_to_fullseye.md) · [intrinsics_to_carla](intrinsics_to_carla.md)

---
*Provenance: carlabridge.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

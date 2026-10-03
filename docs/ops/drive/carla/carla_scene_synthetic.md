---
op: carla_scene_synthetic
dim: drive
category: carla
in: 
out: table
examples: [poc_carla_bridge]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# carla_scene_synthetic — DRIVE `carla` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.carla_scene_synthetic(lead_distance_m: 'float' = 20.0, *, width: 'int' = 320, height: 'int' = 180, fov_deg: 'float' = 90.0, cam_height: 'float' = 1.6, lateral: 'float' = 0.0, lead_asset: 'str' = 'sedan', asset_root=None) -> 'dict'` (実装を直接呼ぶなら `import carlabridge; carlabridge.carla_scene_synthetic(lead_distance_m: 'float' = 20.0, *, width: 'int' = 320, height: 'int' = 180, fov_deg: 'float' = 90.0, cam_height: 'float' = 1.6, lateral: 'float' = 0.0, lead_asset: 'str' = 'sedan', asset_root=None) -> 'dict'`、台帳から引くなら `opsdrive.get("carla_scene_synthetic")`)

## 使い方

自前の世界(直線路 + 先行車)を **CARLA の規約の場面記録**にする(撮影記録と同じ鍵・型)。

自車のカメラは (x = 20, y = 0, z = cam_height) で +x を向き、先行車(``lead_asset``)の後ろ面がカメラから
``lead_distance_m`` 先(横に ``lateral`` m、Fullseye の +y = 左)に来る。``lead_distance_m <= 0`` は先行車なし。
返り値には ``depth`` [m] と ``label``(Fullseye のラベル像)と ``pose``(render3d の world → camera)も入れる
(記録の鍵ではないが門で使う)。

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

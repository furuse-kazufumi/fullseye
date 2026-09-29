---
op: flow_from_depth_motion
dim: drive
category: ttc
in: image2d × matrix × matrix
out: table
examples: [poc_ttc_rss, poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# flow_from_depth_motion — DRIVE `ttc` op

- **データ種**: `image2d × matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.flow_from_depth_motion(depth, K, T_rel) -> 'dict'` (実装を直接呼ぶなら `import drivettc; drivettc.flow_from_depth_motion(depth, K, T_rel) -> 'dict'`、台帳から引くなら `opsdrive.get("flow_from_depth_motion")`)

## 使い方

深度像と剛体運動から **真の像の流れ**: ``{"u", "v", "valid", "depth1"}``(各 (H, W))。

画素の 3-D 点を ``T_rel`` で動かして再投影し、``u = col₁ − col₀``、``v = row₁ − row₀``。動かした後に
カメラの背後へ行く点や深度の無い画素は ``valid = False``(u, v は NaN)。``depth1`` は動かした後の深度。
光学流の推定器の採点に使う真値(推定器と同じ規約: (x, y) → (x + u, y + v))。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ttc`)

[relative_motion](relative_motion.md) · [foe_from_motion](foe_from_motion.md) · [ttc_truth](ttc_truth.md) · [ttc_from_flow](ttc_from_flow.md) · [ttc_from_scale](ttc_from_scale.md) · [ttc_from_range](ttc_from_range.md) · [label_extent](label_extent.md) · [foe_from_flow](foe_from_flow.md)

---
*Provenance: drivettc.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

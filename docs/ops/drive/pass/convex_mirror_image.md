---
op: convex_mirror_image
dim: drive
category: pass
in: any
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# convex_mirror_image — DRIVE `pass` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.convex_mirror_image(object_distance, radius: 'float', *, eye_distance: 'float', object_size: 'float' = 1.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.convex_mirror_image(object_distance, radius: 'float', *, eye_distance: 'float', object_size: 'float' = 1.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("convex_mirror_image")`)

## 使い方

凸面鏡の虚像(近軸、配列可)。場面 S064・S130。

1/a + 1/b = 2/R(b は鏡の向こうの虚像)→ b = aR/(2a + R)、倍率 m = R/(2a + R)。眼が鏡から e(``eye_distance``)のとき
像の見かけの大きさ θ = 2 atan(m h /(2(e + b)))、近軸では m h/(e + b) = h/(e + k a)、k = 1 + 2e/R。
``flat_equivalent_distance`` = 同じ大きさに見える平面鏡の距離 k a(遠くに見える量)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [overtake_return_gap](overtake_return_gap.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtake_permitted](overtake_permitted.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_entry_check](roundabout_entry_check.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

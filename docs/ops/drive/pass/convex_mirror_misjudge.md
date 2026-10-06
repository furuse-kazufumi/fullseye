---
op: convex_mirror_misjudge
dim: drive
category: pass
in: any × any
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# convex_mirror_misjudge — DRIVE `pass` op

- **データ種**: `any × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.convex_mirror_misjudge(object_distance, speed, radius: 'float', *, eye_distance: 'float') -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.convex_mirror_misjudge(object_distance, speed, radius: 'float', *, eye_distance: 'float') -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("convex_mirror_misjudge")`)

## 使い方

凸面鏡に映った車の距離と速さを平面鏡のつもりで読んだときの見誤り(近軸の閉形式、配列可)。場面 S064・S130。

k = 1 + 2e/R。距離(大きさから): â = k a。速さは読み方で 3 つ:
``speed_size_consistent`` = k v(大きさの変化を、大きさから読んだ距離と矛盾なく読む → 速く見える)、
``speed_size_anchored`` = k v (e + a)²/(e + k a)²(本当の距離 a にある物の大きさの変化として読む → a > e/√k で遅い)、
``speed_lateral_anchored`` = v (e + a)/(e + k a)(横切る動きの角の速さを本当の距離で読む → 遅い)。
``tau_apparent`` = (e + k a)/(k v)(大きさとその変化率の比 = 見かけの到達時間)、``tau_true`` = a / v。
遠く見える(k > 1)は読み方によらないが、**遅く見えるのは本当の距離に錨を置いたときだけ** —— 返り値の 3 つで分かる。

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

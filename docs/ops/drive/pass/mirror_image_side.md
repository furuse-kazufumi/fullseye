---
op: mirror_image_side
dim: drive
category: pass
in: points
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# mirror_image_side — DRIVE `pass` op

- **データ種**: `points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.mirror_image_side(eye_xy, mirror_center_xy, mirror_normal_xy, points, *, heading, velocities=None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.mirror_image_side(eye_xy, mirror_center_xy, mirror_normal_xy, points, *, heading, velocities=None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("mirror_image_side")`)

## 使い方

カーブミラーに映る点が、鏡の中心より左右どちらに見えるか・どちらへ動いて見えるか(平面鏡の閉形式)。場面 S064・S130。

左右の向きは凸面鏡でも同じ(門で光線追跡と照合。凸面は角を縮めるだけ)。

上から見た 2 次元(x, y)。像 P' = P − 2((P − M)·n)n(``drivedecide.mirror_reflection_matrix`` の 2 次元版)。
``image_offset`` = 眼から鏡の中心を見る向きに対する像の向きの角(+ = 左)。``real_side`` = ``heading``(運転者の前)に
対して物が左(+1)か右(−1)か。``velocities`` を渡すと ``image_motion`` = 像の角の速さ、``direct_motion`` = 眼から物を
直接見たときの角の速さ(遮りは見ない)、``virtual_eye_motion`` = 仮想の眼 E' から見た角の速さ(= −image_motion が恒等式)、
``reversed`` = 像と直接の動きの向きが逆か。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [overtake_return_gap](overtake_return_gap.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtake_permitted](overtake_permitted.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_entry_check](roundabout_entry_check.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

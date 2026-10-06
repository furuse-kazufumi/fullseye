---
op: overtake_return_gap
dim: drive
category: pass
in: 
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# overtake_return_gap — DRIVE `pass` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.overtake_return_gap(*, lane_offset: 'float', lead_width: 'float', eye_xy=(0.0, -0.35), mirror_center_xy=(0.55, 0.0), mirror_normal_xy=None, mirror_width: 'float' = 0.25, eye_to_rear: 'float' = 2.8) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.overtake_return_gap(*, lane_offset: 'float', lead_width: 'float', eye_xy=(0.0, -0.35), mirror_center_xy=(0.55, 0.0), mirror_normal_xy=None, mirror_width: 'float' = 0.25, eye_to_rear: 'float' = 2.8) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("overtake_return_gap")`)

## 使い方

追い越した前車の **全体がルームミラーに映る** ときの車間(自車の後端と前車の前端の間)。場面 S086・S145。

教則 5-6-3(6)「追い越した車がルームミラーで見えるくらいの距離までそのまま進み」・7-2-3「追い越した車全体が
ルームミラーに映ってから」を幾何にする。座標は自車(x = 前、y = 左、原点 = 眼の真横の車の中心線)。前車は左の車線
(横の中心 = ``lane_offset``、幅 ``lead_width``)で自車の後ろ。ルームミラーは平面鏡(中心 ``mirror_center_xy``、
幅 ``mirror_width``、法線は眼の側)。法線を省くと、眼から鏡の中心への光線を真後ろ(−x)へ返す向き
(``drivedecide.mirror_aim_normal``)。

映る ⇔ 仮想の眼 E'(眼を鏡の直線で折り返した点)と点を結ぶ線分が鏡の線分を通る。道に平行な直線の上では境目は 1 次
方程式の根で、前の辺の両端(2 隅)で決まる。返り値: ``gap`` = 眼の後ろ ``eye_to_rear`` の自車の後端から、前の 2 隅が
映る前車の前端までの距離、``corner_limit_x``(各隅が映る x の上限)、``straight_back_s``(真後ろの方向が鏡のどこを通るか。
鏡の外なら真後ろが映らない = ValueError)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtake_permitted](overtake_permitted.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_entry_check](roundabout_entry_check.md) · [roundabout_signal_point](roundabout_signal_point.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

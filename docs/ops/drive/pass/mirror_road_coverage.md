---
op: mirror_road_coverage
dim: drive
category: pass
in: 
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# mirror_road_coverage — DRIVE `pass` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.mirror_road_coverage(eye_xy, mirror_center_xy, mirror_normal_xy, mirror_width: 'float', *, mirror_radius=inf, road_point, road_direction) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.mirror_road_coverage(eye_xy, mirror_center_xy, mirror_normal_xy, mirror_width: 'float', *, mirror_radius=inf, road_point, road_direction) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("mirror_road_coverage")`)

## 使い方

カーブミラー(凸面の円弧 or 平面)に映る道の範囲(上から見た 2 次元、閉形式)。場面 S064・S130。

道 = 直線 Q(λ) = road_point + λ·road_direction(単位にする。λ = 0 を交差点の衝突の点に置くと読みやすい)。鏡の両端
(円弧なら端の法線 N = cos φ n ± sin φ t、φ = asin(w/2R))で眼からの光線を反射させ、道との交点 λ₁, λ₂ を求める。
凸面では反射光線の向きが鏡の上の位置に単調なので、映る範囲 = [min λ, max λ]。光線が道に届かなければ(平行・背を向ける)
その側は ±∞(光線の向きと道の向きの内積の符号)。``blind_near`` = λ = 0 から映る範囲の手前の端までの長さ(0 より奥から
しか映らないとき、交差点の直前が映らない死角)。``drivedecide.convex_mirror_fov`` と同じ端の光線(眼が軸上なら
2 本の向きの差 = 全視野角)。

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

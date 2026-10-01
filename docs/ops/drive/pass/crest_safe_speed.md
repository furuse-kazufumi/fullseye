---
op: crest_safe_speed
dim: drive
category: pass
in: any
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# crest_safe_speed — DRIVE `pass` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.crest_safe_speed(sight, *, reaction: 'float', brake: 'float', theta: 'float' = 0.0, c_rr: 'float' = 0.0, g: 'float' = 9.80665, crawl: 'float' = 2.7777777777777777) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.crest_safe_speed(sight, *, reaction: 'float', brake: 'float', theta: 'float' = 0.0, c_rr: 'float' = 0.0, g: 'float' = 9.80665, crawl: 'float' = 2.7777777777777777) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("crest_safe_speed")`)

## 使い方

見えている距離の中で止まれる上限の速さ(停止距離の逆関数、閉形式、配列可)。場面 S065。

v ρ + v²/(2A) = S、A = brake + g sin θ + c_rr g cos θ(θ > 0 = 上り。``drivelong.stopping_distance_grade`` の空気抵抗なしの式)
を解いた v = 2S/(ρ + √(ρ² + 2S/A))。A ≤ 0 は ValueError。返り値: ``speed`` [m/s]、``speed_kmh``、
``crawl_required``(42 条 2 号は頂上付近では速さによらず徐行 = True)、``crawl_sufficient``(徐行 ``crawl``(**仮定**)で
視距の中に止まれるか)。

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

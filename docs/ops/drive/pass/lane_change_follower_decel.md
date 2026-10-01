---
op: lane_change_follower_decel
dim: drive
category: pass
in: any
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# lane_change_follower_decel — DRIVE `pass` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lane_change_follower_decel(gap, v_follow, v_ego, *, reaction: 'float', accel_ego: 'float' = 0.0, min_gap: 'float' = 0.0, sudden: 'float' = 2.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.lane_change_follower_decel(gap, v_follow, v_ego, *, reaction: 'float', accel_ego: 'float' = 0.0, min_gap: 'float' = 0.0, sudden: 'float' = 2.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("lane_change_follower_decel")`)

## 使い方

進路を変えた先の後続車が、自車に min_gap より近づかないために要る一定の減速度(閉形式、配列可)。場面 S072。

車間 ``gap`` = 後続車の前端と自車の後端の距離(変えた瞬間)、後続車 ``v_follow``、自車 ``v_ego``(``accel_ego`` ≥ 0 で
加速し続ける)。後続車は ``reaction`` の間は速さを保ち、その後一定の減速。w₀ = v_follow − v_ego。
反応の間に詰まる量 = w₀τ − a_eτ²/2(相対速度が反応の中で 0 に届けば w₀²/(2a_e))。反応の後の相対速度
w₁ = w₀ − a_eτ、残り g₁ = gap − min_gap − (詰まる量)。要る減速度 b = max(0, w₁²/(2g₁) − a_e)。
反応の間にもう min_gap を割るなら ∞。``obstructs`` = b > ``sudden``(**仮定** 2.0 m/s²、26 条の 2 第 2 項「急に」)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [overtake_return_gap](overtake_return_gap.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtake_permitted](overtake_permitted.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_entry_check](roundabout_entry_check.md) · [roundabout_signal_point](roundabout_signal_point.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

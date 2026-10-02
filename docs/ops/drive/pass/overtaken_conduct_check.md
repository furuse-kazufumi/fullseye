---
op: overtaken_conduct_check
dim: drive
category: pass
in: table
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# overtaken_conduct_check — DRIVE `pass` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.overtaken_conduct_check(trajectory, *, t_caught: 'float', t_passed: 'float', kind: 'str' = 'car', overtaker_higher_limit: 'bool' = True, continuing_slower: 'bool' = False, lanes: 'bool' = False, room: 'Optional[float]' = None, room_needed: 'Optional[float]' = None, tol: 'float' = 0.2) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivepass; drivepass.overtaken_conduct_check(trajectory, *, t_caught: 'float', t_passed: 'float', kind: 'str' = 'car', overtaker_higher_limit: 'bool' = True, continuing_slower: 'bool' = False, lanes: 'bool' = False, room: 'Optional[float]' = None, room_needed: 'Optional[float]' = None, tol: 'float' = 0.2) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("overtaken_conduct_check")`)

## 使い方

追い越される側の義務(27 条)。場面 S085。

``trajectory`` = {"t", "v"}(追い越される車の速さ)。27 条 1 項の対象 = 乗合自動車・トロリーバス(``kind`` が
"route_bus" / "trolleybus")以外で、追いついた車の最高速度が高い(``overtaker_higher_limit``)か、同じか低くても
その速さより遅く進み続ける(``continuing_slower``)とき。その間 [t_caught, t_passed] に **速度を増した量** =
max_t (v(t) − min_{s ≤ t} v(s)) が ``tol``(**仮定** 0.2 m/s)を超えると ``speed_increased``。
27 条 2 項: 車両通行帯の無い道路(``lanes`` が偽)で中央との間の余地 ``room`` < ``room_needed`` なら ``must_yield_left``。
返り値: ``applies``、``increase``、``violations``、``must_yield_left``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_requirement](overtake_requirement.md) · [overtake_return_gap](overtake_return_gap.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtake_permitted](overtake_permitted.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_entry_check](roundabout_entry_check.md) · [roundabout_signal_point](roundabout_signal_point.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

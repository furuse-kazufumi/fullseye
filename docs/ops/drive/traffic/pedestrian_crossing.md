---
op: pedestrian_crossing
dim: drive
category: traffic
in: 
out: table
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# pedestrian_crossing — DRIVE `traffic` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.pedestrian_crossing(intent: 'str', *, start_xy=(0.0, -3.0), road_width: 'float' = 7.0, speed: 'float' = 1.2, wait_time: 'float' = 3.0, curb_offset: 'float' = 0.3, along_heading: 'float' = 0.0, dt: 'float' = 0.1, t_end: 'Optional[float]' = None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.pedestrian_crossing(intent: 'str', *, start_xy=(0.0, -3.0), road_width: 'float' = 7.0, speed: 'float' = 1.2, wait_time: 'float' = 3.0, curb_offset: 'float' = 0.3, along_heading: 'float' = 0.0, dt: 'float' = 0.1, t_end: 'Optional[float]' = None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("pedestrian_crossing")`)

## 使い方

横断の意図を真値に持つ歩行者の軌跡(区分ごとの閉形式。積分しない)。

道路は x 方向、車道 0 ≤ y ≤ road_width、歩道 y < 0 から始める(``start_xy`` の y < −curb_offset)。
* ``cross``: (x0, y0) → 縁 (x0, −curb_offset) まで歩き、止まらずに向こうの縁 (x0, road_width + curb_offset)
  まで横断して止まる。向きは +π/2(車道の方)。
* ``wait_then_cross``: 縁まで歩き、**縁で車道を向いて** (+π/2) ``wait_time`` 秒止まり、それから横断する。
* ``walk_along``: 歩道を向き ``along_heading``(0 か π)で y = y0 のまま歩く(車道に入らない)。
* ``stand_no_cross``: 縁まで歩き、**縁で車道を向いて** (+π/2) 立ち止まったまま渡らない(バス待ち・連れ待ち)。見た目は
  ``wait_then_cross`` の待ちと区別がつかない —— 規則で「止まる」と判断すれば誤検出になる真値。``t_cross_start`` は None。
速さは ``speed``(既定 ``WALK_SPEED`` = 1.2 m/s、仮定)。

戻り値 dict: ``t`` (K,)、``xy`` (K, 2)、``heading`` (K,)、``phase`` (K,) の文字列
("approach" / "wait" / "cross" / "done" / "along")、``intent``(真値)、``t_cross_start``・``t_cross_end``
(横断しない意図では None)、``speed``。門: 横断にかかる時間 = (road_width + 2·curb_offset)/speed、待つ人は
待ちの間の位置が一定で向きが +π/2、沿って歩く人は全時刻で y < 0、向きは位置の差分の向きと一致。

**Raises** ``ValueError``: 未知の intent、speed ≤ 0、start が歩道上でない、along_heading が 0/π でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [occlusion_reveal_distance](occlusion_reveal_distance.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

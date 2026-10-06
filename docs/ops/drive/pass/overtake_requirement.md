---
op: overtake_requirement
dim: drive
category: pass
in: 
out: table
examples: [poc_driving_pass]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# overtake_requirement — DRIVE `pass` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.overtake_requirement(v_ego: 'float', v_lead: 'float', *, lead_length: 'float', ego_length: 'float', gap_back: 'float', gap_front: 'float', accel: 'float' = 0.0, v_max: 'Optional[float]' = None, lane_change_time: 'float' = 0.0, v_oncoming: 'float' = 0.0, pet_min: 'float' = 0.0) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivepass; drivepass.overtake_requirement(v_ego: 'float', v_lead: 'float', *, lead_length: 'float', ego_length: 'float', gap_back: 'float', gap_front: 'float', accel: 'float' = 0.0, v_max: 'Optional[float]' = None, lane_change_time: 'float' = 0.0, v_oncoming: 'float' = 0.0, pet_min: 'float' = 0.0) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("overtake_requirement")`)

## 使い方

前車を追い越すのに要る時間・道のりと、対向車が来ない境目の距離(閉形式)。場面 S079・S086・S145(28 条 4 項)。

自車の前端が前車の後端の ``gap_back`` 手前で対向車線(又は右の車線)に出てから、自車の後端が前車の前端の ``gap_front``
先に出るまで(相対の距離 D = gap_back + lead_length + ego_length + gap_front)。自車は初速 ``v_ego`` から ``accel`` で
``v_max`` まで加速(教則 5-6-3(4)「最高速度の制限内で加速しながら」)、前車は ``v_lead`` で一定。そのあと
``lane_change_time`` かけて元の車線に戻り切る。``gap_front`` に ``overtake_return_gap`` の値を入れると「ルームミラーで
見える距離」まで進んでから戻る手順(教則 5-6-3(6))になる。

返り値: ``relative_distance`` = D、``t_pass``、``t_occupy`` = t_pass + lane_change_time、``ego_distance``(占有の間に
自車が進む道のり)、``v_pass``(追い越し終えたときの速さ)、``d_required`` = ego_distance + v_oncoming (t_occupy +
pet_min)(判断の時点で対向車がこれより遠ければ、戻り切ってから pet_min 秒以上あとに対向車がその地点に着く)。
前に出られない(相対速度が正にならない)は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_pass](../../../../examples/poc_driving_pass.py) — `py -3.11 examples/poc_driving_pass.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`pass`)

[overtake_return_gap](overtake_return_gap.md) · [no_overtaking_zones](no_overtaking_zones.md) · [overtake_permitted](overtake_permitted.md) · [overtaken_conduct_check](overtaken_conduct_check.md) · [lane_change_follower_decel](lane_change_follower_decel.md) · [lane_change_permitted](lane_change_permitted.md) · [roundabout_entry_check](roundabout_entry_check.md) · [roundabout_signal_point](roundabout_signal_point.md)

---
*Provenance: drivepass.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

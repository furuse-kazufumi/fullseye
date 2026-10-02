---
op: passing_gap_required
dim: drive
category: traffic
in: 
out: table
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# passing_gap_required — DRIVE `traffic` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.passing_gap_required(parked_len: 'float', margin_front: 'float', margin_back: 'float', v_ego: 'float', v_oncoming: 'float', *, lane_change_time: 'float', ego_length: 'float' = 0.0, pet_min: 'float' = 0.0, v_obstacle: 'float' = 0.0) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.passing_gap_required(parked_len: 'float', margin_front: 'float', margin_back: 'float', v_ego: 'float', v_oncoming: 'float', *, lane_change_time: 'float', ego_length: 'float' = 0.0, pet_min: 'float' = 0.0, v_obstacle: 'float' = 0.0) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("passing_gap_required")`)

## 使い方

駐車車両を避けて対向車線にはみ出す区間を抜ける時間と、対向車がそれまでに来ない境目の距離(閉形式)。

自車は駐車車両の後端の ``margin_back`` 手前(x_in)で対向車線に出始め、前端の ``margin_front`` 先(x_out)を
過ぎてから ``lane_change_time`` かけて自車線へ戻り切る。はみ出す長さ L_occ = margin_back + parked_len +
margin_front + ego_length、はみ出している時間 t_occ = L_occ / v_ego + T_lc。戻り切った地点
P = x_in + L_occ + v_ego T_lc に対向車が着くのが戻り切った時刻より ``pet_min`` 以上後(PET ≥ pet_min)である
ための、判断時(自車が x_in)の対向車までの距離の境目:

    D* = t_occ (v_ego + v_on) + v_on · pet_min

**走っている障害物**(自転車など、同じ向きに ``v_obstacle`` で進む): はみ出す長さは障害物に対する相対の距離なので
t_occ = L_occ / (v_ego − v_obstacle) + T_lc、戻り切った地点 P = x_in + v_ego t_occ。D* の式は同じ形。
v_obstacle = 0 で止まっている車の式に戻る。

戻り値 dict: ``L_occ``, ``t_occupy``, ``d_required`` (= D*)、``clear_point``(x_in から P までの距離)。

**Raises** ``ValueError``: 負の長さ・余裕、v_ego ≤ 0、v_oncoming < 0、lane_change_time < 0、
v_obstacle < 0 か v_obstacle ≥ v_ego(追いつけない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [idm_platoon_simulate](idm_platoon_simulate.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: passing_simulate
dim: drive
category: traffic
in: 
out: table
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# passing_simulate — DRIVE `traffic` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.passing_simulate(dist_oncoming: 'float', parked_len: 'float', margin_front: 'float', margin_back: 'float', v_ego: 'float', v_oncoming: 'float', *, lane_change_time: 'float', ego_length: 'float' = 0.0, dt: 'float' = 0.01, v_obstacle: 'float' = 0.0) -> 'Dict[str, float]'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.passing_simulate(dist_oncoming: 'float', parked_len: 'float', margin_front: 'float', margin_back: 'float', v_ego: 'float', v_oncoming: 'float', *, lane_change_time: 'float', ego_length: 'float' = 0.0, dt: 'float' = 0.01, v_obstacle: 'float' = 0.0) -> 'Dict[str, float]'`、台帳から引くなら `opsdrive.get("passing_simulate")`)

## 使い方

"go" にした場合を時間を進めて走らせ、PET(自車が対向車線から戻り切った時刻と、対向車がその地点に着く時刻の差)を返す。

閉形式と独立な経路: 自車の **横位置** を、x_in〜x_out の間は対向車線(y = 1)、x_out を過ぎたら
y(τ) = 1 − smoothstep(τ / T_lc)(τ = x_out を過ぎてからの時間)で戻すとして刻み dt で進め、y が 0 になった刻みを
探して刻み内を二分法で詰めた時刻を戻り切った時刻とする(T_lc = 0 なら x_out を過ぎた時刻)。対向車は x = D から
−v_on で進め、戻り切った地点を通る刻みを探して線形補間する。v_on = 0 なら PET = inf。

``v_obstacle`` > 0: 障害物の前端の外(x_out)も v_obstacle で進む(走っている自転車の追い越し)。

戻り値 dict: ``t_clear``、``x_clear``、``t_oncoming``(対向車が x_clear に着く時刻)、``pet``。

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

---
op: curvature_speed_plan
dim: drive
category: lateral
in: any
out: table
examples: [poc_driving_lateral]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# curvature_speed_plan — DRIVE `lateral` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.curvature_speed_plan(s, kappa, *, v_max, a_lat_max: 'float', a_accel: 'float', a_decel: 'float', a_total: 'Optional[float]' = None, v_start: 'Optional[float]' = None, v_end: 'Optional[float]' = None) -> 'Dict[str, np.ndarray]'` (実装を直接呼ぶなら `import drivelateral; drivelateral.curvature_speed_plan(s, kappa, *, v_max, a_lat_max: 'float', a_accel: 'float', a_decel: 'float', a_total: 'Optional[float]' = None, v_start: 'Optional[float]' = None, v_end: 'Optional[float]' = None) -> 'Dict[str, np.ndarray]'`、台帳から引くなら `opsdrive.get("curvature_speed_plan")`)

## 使い方

曲率の列から速度の上限を作り、前向き・後ろ向きの 2 パスで加減速の上限を守る速度計画(古典的な手法)。

``s``: 弧長(増加、(N,))。``kappa``: 各点の曲率(符号は問わない)。``v_max``: 速度の上限(スカラーまたは (N,)、
法定速度・徐行の区間など)。上限 v_lim = min(v_max, √(a_lat_max/|κ|))。刻みの間は v² を s に一次(一定の加減速)。
``a_total``(摩擦円の半径、例 μg)を与えると、縦の加減速を √(a_total² − (v²κ_m)²) でも抑える(κ_m = 刻みの両端の |κ|
の大きい方、2 次方程式で解くので刻みの中の **どこでも** √(a_x² + a_y²) ≤ a_total)。a_lat_max ≤ a_total を要求。
返り値: ``v``, ``v_limit``, ``ax``(刻みごとの縦の加速度、(N−1,))、``ay_max``(刻みの中の横の加速度の最大)、
``time``(到着時刻、v² 一次の厳密な時間)。

**Raises** ``ValueError``: 形の誤り、s が増加でない、上限が正でない、a_lat_max > a_total、v_start/v_end が上限超え。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_lateral](../../../../examples/poc_driving_lateral.py) — `py -3.11 examples/poc_driving_lateral.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

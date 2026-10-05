---
op: flight_simulate
dim: drive
category: ball
in: table × table
out: table
examples: [poc_ball_bounce, poc_table_tennis_bounce, poc_table_tennis_rally_loop, poc_table_tennis_spin]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# flight_simulate — DRIVE `ball` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.flight_simulate(p0, v0, omega, bp: 'dict', ip: 'dict', t_end: 'float', dt: 'float' = 0.001, table_z: 'float' = 0.0, table_xy=None, max_bounces: 'int' = 100, v_rest: 'float' = 0.001) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.flight_simulate(p0, v0, omega, bp: 'dict', ip: 'dict', t_end: 'float', dt: 'float' = 0.001, table_z: 'float' = 0.0, table_xy=None, max_bounces: 'int' = 100, v_rest: 'float' = 0.001) -> 'dict'`、台帳から引くなら `opsdrive.get("flight_simulate")`)

## 使い方

飛翔 + 卓上(z = table_z の平面、``table_xy`` = (xmin, xmax, ymin, ymax) の範囲内だけ)での跳ねを、接触時刻を 2 分法で
区間内に求めて繋ぐ。返り値 ``{"t", "p", "v", "omega" (N, 3), "contacts": [{"t", "p", "v_in", "v_out", "omega_in",
"omega_out", "regime"}], "rest_t"}``。球は半径 r なので中心が table_z + r に達した所が接触。跳ねは無限に続く(Zeno)ので、
接触時の |v_n| < ``v_rest`` になったら卓上に置く(以後 z は固定、水平は摩擦無しで続く。``rest_t`` = その時刻、無ければ None)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ball_bounce](../../../../examples/poc_ball_bounce.py) — `py -3.11 examples/poc_ball_bounce.py`
- [poc_table_tennis_bounce](../../../../examples/poc_table_tennis_bounce.py) — `py -3.11 examples/poc_table_tennis_bounce.py`
- [poc_table_tennis_rally_loop](../../../../examples/poc_table_tennis_rally_loop.py) — `py -3.11 examples/poc_table_tennis_rally_loop.py`
- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ball`)

[ball_params](ball_params.md) · [impact_params](impact_params.md) · [flight_vacuum](flight_vacuum.md) · [flight_ode](flight_ode.md) · [flight_state_at](flight_state_at.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md) · [bounce](bounce.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

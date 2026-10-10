---
op: fit_spin
dim: drive
category: ball
in: signal × points × table
out: table
examples: [poc_table_tennis_spin]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# fit_spin — DRIVE `ball` op

- **データ種**: `signal × points × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_spin(t, p, bp: 'dict', *, omega0=None, omega_max: 'float' = 1000.0, iters: 'int' = 20, dt: 'float' = 0.001) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.fit_spin(t, p, bp: 'dict', *, omega0=None, omega_max: 'float' = 1000.0, iters: 'int' = 20, dt: 'float' = 0.001) -> 'dict'`、台帳から引くなら `opsdrive.get("fit_spin")`)

## 使い方

**曲がり方から回転を読む**: 軌跡 (t_i, p_i)(跳ねを含まない区間)に、抗力 + マグヌスの運動方程式を
(p₀, v₀, ω) の 9 パラメータで Gauss–Newton で当てる(空力係数は ``bp`` の値 = 既知とする)。

マグヌスの力は ω × v なので、**ω の v に平行な成分は力を生まず、軌跡からは決まらない**(進行方向を軸にした
回転 = 横回転の一部)。飛ぶうちに v の向きが変わるので完全に不定ではないが弱い。返り値の ``omega_perp`` =
初速に垂直な成分(読める部分)、``cond`` = ヤコビアンの条件数、``omega_axial_sensitivity`` = 平行成分を
1 rad/s 動かしたときの軌跡の変化の rms [m] (小さいほど読めない)。
返り値 ``{"p0", "v0", "omega", "omega_perp", "rms", "cond", "omega_axial_sensitivity", "iters", "t0"}``。
真値の軌跡を入れると 1e-3 rad/s で戻る(門)。模様から測った角速度(:func:`balltrack.spin_from_markers`)と
独立な第 2 の測り方になる。

``omega_max`` [rad/s] = 回転の大きさの上限(各歩の後にこの球へ射影する)。★スピン比の模型 C_L = 1/(2 + 1/S) は
回転が大きいと 0.5 で頭打ちになるので、力が足りないと見た当てはめは |ω| を際限なく大きくできる(大きさが決まらない)。
軌跡が短く雑音が勝つと 1e5 rad/s へ走った(2026-09-30)。既定 1000 rad/s ≈ 160 回転/秒(強打の上限より上)。
返り値の ``at_bound`` が True なら上限に張り付いた = 大きさは読めていない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_table_tennis_spin](../../../../examples/poc_table_tennis_spin.py) — `py -3.11 examples/poc_table_tennis_spin.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ball`)

[ball_params](ball_params.md) · [impact_params](impact_params.md) · [flight_vacuum](flight_vacuum.md) · [flight_ode](flight_ode.md) · [flight_simulate](flight_simulate.md) · [flight_state_at](flight_state_at.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

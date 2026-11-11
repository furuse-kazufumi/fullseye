---
op: fit_spin_aero
dim: drive
category: ball
in: signal × points × table
out: table
gpu: なし
examples: [poc_cd_spin_joint]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# fit_spin_aero — DRIVE `ball` op

- **データ種**: `signal × points × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fit_spin_aero(t, p, bp: 'dict', *, omega0=None, fit_cl: 'bool' = False, omega_max: 'float' = 1000.0, iters: 'int' = 25, dt: 'float' = 0.001) -> 'dict'` (実装を直接呼ぶなら `import ballistics; ballistics.fit_spin_aero(t, p, bp: 'dict', *, omega0=None, fit_cl: 'bool' = False, omega_max: 'float' = 1000.0, iters: 'int' = 25, dt: 'float' = 0.001) -> 'dict'`、台帳から引くなら `opsdrive.get("fit_spin_aero")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

**抗力と回転を同時に読む**(:func:`fit_spin` の C_d 自由版): 軌跡 (t_i, p_i)(跳ねを含まない区間)に抗力 + マグヌスの運動方程式を (p₀, v₀, ω, C_d) の 10 パラメータで Levenberg–Marquardt で当てる(``fit_cl=True`` で C_L の係数 κ も自由にして 11 パラメータ)。

当てはめの模型の C_d は定数(Re 依存を当てない)、揚力はスピン比の経験式 C_L = κ·S/(1 + 2S)(S = rω/|v|)で、係数 κ は既定で 1。
★C_L を数(定数)にした ``bp`` は受け付けない(ValueError): 定数 C_L のマグヌスの力は大きさが ω によらず、|ω| の列が 0 になって
回転の大きさが原理的に読めない(測って確かめた: ω が 0 のまま動かない)。

**読めないものを返り値に出す**: 抗力は −v、マグヌスは ω × v(v に垂直)なので力の向きは直交して分かれるが、(a) 飛行が短く速さがあまり落ちないと
C_d は v₀ と、(b) ω と C_L の係数 κ は縮退(S が小さい域で C_L ≈ κS なので力は κ·ω の積だけ)、(c) ω の v に平行な成分は力を生まない。
返り値の ``cond``(スケール後のヤコビアンの条件数)、``corr``(推定量の相関行列、``param_names`` の順)、``cov_unit``(位置雑音 1 m あたりの推定量の
共分散 = 線形化したクラメール・ラオ。雑音 σ [m] なら σ² 倍)、``corr_cd_omega``(C_d と ω⊥ の大きさの相関)、``corr_cd_v0``(C_d と初速の大きさの相関)、
``omega_axial_std_unit``(ω の平行成分の標準偏差、雑音 1 m あたり)、``omega_perp_std_unit``(ω の垂直 2 成分の 1 成分あたりの標準偏差)で判る。
返り値 ``{"p0", "v0", "omega", "omega_perp", "cd", "cl_scale", "rms", "cond", "corr", "param_names", "cov_unit", "corr_cd_omega",
"corr_cd_v0", "omega_axial_std_unit", "omega_perp_std_unit", "iters", "t0", "at_bound"}``。
同じ模型で作った軌跡なら 1e-6 で戻る(門)。★世界が別の模型(C_d が Re 依存、C_L に谷)だと、定数で当てた C_d・ω・C_L はその区間の実効値になり偏る
(偏りは PoC で測って出す)。``omega_max`` は :func:`fit_spin` と同じ(回転の大きさの上限)。収束は ``omega0`` が真値から離れる・軌跡が短い・
``fit_cl=True`` だと遅く、平らな谷で ``iters`` に届かない標本がある(返り値の ``iters`` が引数と同じなら打ち切り)。

Limits: with ``fit_cl=True`` the |ω| and κ columns are nearly parallel (``cond`` large, ``corr`` ≈ ±1) — read ω from the ball's pattern
(:func:`balltrack.spin_from_markers`) and take the lift scale from the trajectory instead (:func:`fit_aero` with ω known). A constant-C_L ``bp``
and fewer than 12 samples raise ValueError.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_cd_spin_joint](../../../../examples/poc_cd_spin_joint.py) — `py -3.11 examples/poc_cd_spin_joint.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`ball`)

[ball_params](ball_params.md) · [impact_params](impact_params.md) · [flight_vacuum](flight_vacuum.md) · [flight_ode](flight_ode.md) · [flight_simulate](flight_simulate.md) · [flight_state_at](flight_state_at.md) · [magnus_lift_coefficient](magnus_lift_coefficient.md) · [drag_coefficient_sphere](drag_coefficient_sphere.md)

---
*Provenance: ballistics.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: catch_success_rate
dim: drive
category: kendama
in: table
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# catch_success_rate — DRIVE `kendama` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.catch_success_rate(kp: 'dict', *, n: 'int' = 20, seed: 'int' = 0, noise_pos: 'float' = 0.0, noise_vel: 'float' = 0.0, jitter_pos: 'float' = 0.01, jitter_vel: 'float' = 0.05, lift: 'float' = None, T_lift: 'float' = 0.15, kind: 'str' = 'bang', t_end: 'float' = 1.5, dt: 'float' = 0.001, v_max: 'float' = 2.0, a_max: 'float' = 20.0, v_rel_max: 'float' = 1.0, v_target: 'float' = 0.5, origin=(0.0, 0.0, 0.0), perceiver_factory=None, dodge=(0.0, -0.1, 0.0), clearance: 'bool' = True, keep_runs: 'bool' = False, planner: 'str' = 'staged', contact=None, absorb: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import kendama; kendama.catch_success_rate(kp: 'dict', *, n: 'int' = 20, seed: 'int' = 0, noise_pos: 'float' = 0.0, noise_vel: 'float' = 0.0, jitter_pos: 'float' = 0.01, jitter_vel: 'float' = 0.05, lift: 'float' = None, T_lift: 'float' = 0.15, kind: 'str' = 'bang', t_end: 'float' = 1.5, dt: 'float' = 0.001, v_max: 'float' = 2.0, a_max: 'float' = 20.0, v_rel_max: 'float' = 1.0, v_target: 'float' = 0.5, origin=(0.0, 0.0, 0.0), perceiver_factory=None, dodge=(0.0, -0.1, 0.0), clearance: 'bool' = True, keep_runs: 'bool' = False, planner: 'str' = 'staged', contact=None, absorb: 'bool' = True) -> 'dict'`、台帳から引くなら `opsdrive.get("catch_success_rate")`)

## 使い方

大皿の成功率: 初期状態を散らして n 回(玉は支点(皿胴の糸穴)の L 下に吊り、横に σ = jitter_pos、速度に σ = jitter_vel
(接線成分)のガウス揺らぎ)、:func:`swing_up_plan`(手元の出発点 ``origin``)で振り上げ、:func:`catch_plan_ballistic` で皿を運ぶ。

計画: ``planner="staged"``(既定、:func:`catch_plan_staged`: hold → carry → absorb、``absorb=False`` で着地で下げない)か
"plane"(:func:`catch_plan_ballistic`、``clearance`` つき)。``lift`` 既定 None = :func:`swing_up_lift`(技ごとに頂点が皿の
h_c + 0.9 r_b 上)。``contact(hand, p) → 隙間`` を渡すとけん玉に触れた試行は "hit_ken" で失敗。
知覚: 既定は :func:`noisy_perceiver`(noise_pos [m]、noise_vel [m/s]; 0 なら真値)。``perceiver_factory(i) → perceive`` を
渡すとそれを使う(試行 i ごとに新しい知覚: :func:`kendamaworld.camera_perceiver` で画像だけから予測する閉ループ)。
初期状態の揺らぎは知覚によらず seed で決まる(同じ seed なら真値と画像の試行が対になる)。
返り値 ``{"rate", "n", "caught_list", "mean_lateral", "catch_times", "end_reasons", "laterals", "starts"}``
(mean_lateral = 捕った試行の捕球時の横ずれの平均、無ければ nan。starts = 各試行の (p0, v0))。``dodge`` / ``clearance`` は
:func:`swing_up_plan` / :func:`catch_plan_ballistic` へ(既定 = 手元を糸穴の側(−y)へ 10 cm 逃がし、玉が大皿の縁より上に出てから
皿を戻す: 玉がけん玉を突き抜けない構え。逃がさない (0, 0, 0)・False だと 20 試行すべてで玉が皿胴を突き抜けた —— 測って退けた。
+y へ逃がすとカメラ 2 から見てけんが玉の手前に来て玉を隠し、画像の予測の横ずれが 0.14 → 2.8 mm に増えた)。``keep_runs=True`` で各試行の :func:`kendama_simulate` の返り値と
知覚を ``"runs"`` / ``"perceivers"`` に残す。n ≤ 0 は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_tension_fixed](tether_tension_fixed.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_plan](swing_up_plan.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

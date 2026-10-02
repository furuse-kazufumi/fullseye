---
op: kendama_simulate
dim: drive
category: kendama
in: table
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# kendama_simulate — DRIVE `kendama` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.kendama_simulate(kp: 'dict', handle, *, p0, v0, t_end: 'float', dt: 'float' = 0.001, perceive=None, catch_plan=None, g: 'float' = None, v_max: 'float' = 2.0, a_max: 'float' = 20.0, v_rel_max: 'float' = 1.0, plan_from: 'float' = 0.0, stop_on_miss: 'bool' = True, contact=None, contact_tol: 'float' = 0.0005) -> 'dict'` (実装を直接呼ぶなら `import kendama; kendama.kendama_simulate(kp: 'dict', handle, *, p0, v0, t_end: 'float', dt: 'float' = 0.001, perceive=None, catch_plan=None, g: 'float' = None, v_max: 'float' = 2.0, a_max: 'float' = 20.0, v_rel_max: 'float' = 1.0, plan_from: 'float' = 0.0, stop_on_miss: 'bool' = True, contact=None, contact_tol: 'float' = 0.0005) -> 'dict'`、台帳から引くなら `opsdrive.get("kendama_simulate")`)

## 使い方

けん玉の 2 段シミュレーション: ひもが張っている間は支点(**皿胴の糸穴** = 手元 + kp["tie_offset"])に繋がれた玉
(射影法、:func:`ballistics.tether_simulate` と同じ: 支点固定・真空なら同じ軌跡、ひもの長さ = kp["pendulum_length"])、
弛んだら自由落下(重力 + 抗力、kp["bp"]; rho = 0 で真空)。毎 step :func:`kendama_catch_check`(大皿 = 手元 + kp["cup_offset"]、
軸 kp["cup_axis"])で捕球を判定し、捕ったら終わる。

``handle`` = 手元(皿胴の中心)の (3,) の固定点か t → (3,) の関数(開ループの振り上げ)。``catch_plan`` があれば、弛んだ後
(かつ t ≥ ``plan_from``: 振り上げが終わるまでは開ループを優先する)は毎 step ``perceive`` で知覚した (p̂, v̂) を
``catch_plan(t, p̂, v̂, cup_state) → {"target": 大皿の縁の中心の目標 (3,), …}`` に渡し、手元を速さ ≤ v_max・加速度 ≤ a_max の
bang-bang で「目標 − cup_offset」へ運ぶ(手元が動くと支点も動くので、玉が落ちてきて |p − 支点| = L になれば再び張る)。

知覚 ``perceive``:
 - None → 真値 (p, v)。
 - ``perceive(t, p, v) → (p̂, v̂)``(:func:`noisy_perceiver` など)は計画が生きている step だけ呼ぶ。
 - 属性 ``observe_all = True`` の知覚(:func:`kendamaworld.camera_perceiver`)は **毎 step** ``perceive(t, p, v, scene)`` で呼ぶ
   (scene = ``{"t", "hand", "tie", "cup", "cup_axis", "taut"}`` = 手元の自己受容で分かる量 + 世界を描くための taut
   (玉の姿勢の描画の約束: 張っている間は糸穴が結び目を向き、弛んだら最後の姿勢のまま)。p も世界を描くためだけに渡す)。
   返り値が None なら計画はそのまま(最後の目標へ運び続け、目標が無ければ手元を止める)。

**玉を動かすのは重力(+ 抗力、rho > 0 のとき)とひもの張力(≥ 0 の片側拘束)だけ**。けんは玉を押さない: ``contact(hand, p) → 隙間 [m]``
(:func:`kendamaworld.kendama_clearance` など)を渡すと、捕球の前に隙間 < −``contact_tol`` になった step で "hit_ken" として終わる
(けん先・皿の縁・皿胴に玉が触れた = 失敗)。捕球は ``kp["catch_window"]``(玉が縁に触れた高さ)で判定する。

終わり方 ``end_reason``: "caught"(捕球)、"hit_ken"(けん玉に触れた)、"missed"(弛んだ後、下向きに落ちながら大皿の面より 2 r_b 以上下に来た。
``stop_on_miss=False`` なら止めない: snap の門に使う)、"timeout"(t_end)。
返り値 ``{"t", "p", "v", "hand", "anchor" (= 支点 = 糸穴), "cup", "cup_v", "taut", "tension", "energy", "snap_times", "snap_loss",
"slack_t", "caught", "catch_t", "end_reason", "lateral", "plan_log", "n_estimates", "stage", "min_gap"}``(配列は終わった step まで。
stage = 各 step の制御の段階 ("lift" 振り上げ / "wait" 弛んだが計画前 / 計画の "stage"(hold / carry / absorb)or "plan")。slack_t = ひもが
張った後で初めて弛んだ時刻、初めから弛んでいれば 0.0、一度も弛まなければ None。energy = ½mv² + mgz。n_estimates = 計画に
渡した知覚の数)。初期状態が |p₀ − 支点(0)| > L、t_end < 0、dt ≤ 0、上限 ≤ 0 は ValueError。

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

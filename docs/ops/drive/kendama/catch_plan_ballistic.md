---
op: catch_plan_ballistic
dim: drive
category: kendama
in: table
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# catch_plan_ballistic — DRIVE `kendama` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.catch_plan_ballistic(kp: 'dict', *, v_max: 'float' = 2.0, a_max: 'float' = 20.0, g: 'float' = None, v_target: 'float' = 0.5, v_rel_max: 'float' = 1.0, n_planes: 'int' = 12, plane_step: 'float' = 0.02, clearance: 'bool' = False, margin: 'float' = 0.002)` (実装を直接呼ぶなら `import kendama; kendama.catch_plan_ballistic(kp: 'dict', *, v_max: 'float' = 2.0, a_max: 'float' = 20.0, g: 'float' = None, v_target: 'float' = 0.5, v_rel_max: 'float' = 1.0, n_planes: 'int' = 12, plane_step: 'float' = 0.02, clearance: 'bool' = False, margin: 'float' = 0.002)`、台帳から引くなら `opsdrive.get("catch_plan_ballistic")`)

## 使い方

弛んだ玉の (p, v) から放物線の閉形式で皿の到達点を出す計画。返り値は ``plan(t, p, v, cup_state) → dict``。

捕球の判定は「玉が皿の窓の上端(縁の面 + h_c + 1.5 r_b)に相対速さ ≤ v_rel_max で下向きに入る」瞬間に起きるので、
窓の上端に玉が速さ ``v_target`` で届く面を選ぶ: 頂点 z_a = z + v_z²/(2g) から z_c = z_a − (h_c + 1.5 r_b) − v_target²/(2g)。
到達時刻は z + v_z τ − ½ g τ² = z_c + h_c + 1.5 r_b の**遅い方の根**(下降)τ = (v_z + √(v_z² − 2g(z_c + h_c + 1.5 r_b − z)))/g、
目標の xy = (x + v_x τ, y + v_y τ)。皿が bang-bang で τ までに届かなければ(閉形式の移動時間: 静止から 2√(d/a) または
d/v + v/a、動いていれば現在の速さ込み)面を ``plane_step`` ずつ下げて ``n_planes`` 段まで探す(下げるほど時間は増え、
到達速さは増える)。どの面にも間に合わなければ **最上段を返し** ``feasible=False``(到達速さが最小の面に賭ける。
「最下段へ逃げる」と到達の直前に τ → 0 で必ず不可判定になり皿が 20 cm 沈んで落とす —— 測って退けた)。

返り値 ``{"target" (皿の中心), "t_hit", "z_plane", "v_ball_hit", "speed_hit", "feasible", "travel", "apex"}``。
``clearance=True``: 玉の下端が縁の面(+ ``margin``)より上に出る時刻 τ_up までは皿を**横に動かさない**(高さだけ面へ)——
大皿の縁はけん玉のいちばん高い所なので、玉が縁の面より上なら xy がどこでもぶつからない。間に合うかは τ − τ_up で判定し、
玉が縁の面を越えない面は不可。返り値に ``"landing"``(落下点 = 最終の目標)と ``"wait"``(τ_up、0 = 待たない)を足す。
制限(正直に): 皿は目標で**静止して待つ**(到達時の相対速さ = 玉の速さ)。間に合わない面での「玉に合わせて皿を下げる」
速度合わせは実装していない —— v_rel_max に頼る。抗力は無視(60 mm の玉の ≤ 0.5 s の飛翔で数 mm、毎 step 計画し直すので消える)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_tension_fixed](tether_tension_fixed.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_plan](swing_up_plan.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

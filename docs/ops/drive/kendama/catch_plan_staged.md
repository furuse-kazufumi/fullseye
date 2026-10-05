---
op: catch_plan_staged
dim: drive
category: kendama
in: table
out: any
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# catch_plan_staged — DRIVE `kendama` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.catch_plan_staged(kp: 'dict', *, v_max: 'float' = 2.0, a_max: 'float' = 20.0, g: 'float' = None, margin: 'float' = 0.005, absorb_time: 'float' = None, absorb_depth: 'float' = 0.02)` (実装を直接呼ぶなら `import kendama; kendama.catch_plan_staged(kp: 'dict', *, v_max: 'float' = 2.0, a_max: 'float' = 20.0, g: 'float' = None, margin: 'float' = 0.005, absorb_time: 'float' = None, absorb_depth: 'float' = 0.02)`、台帳から引くなら `opsdrive.get("catch_plan_staged")`)

## 使い方

段階を明示した捕球の制御(大皿・小皿・中皿・ろうそくに同じ計画を使う: 皿の向きは kp の技の姿勢から)。
返り値は ``plan(t, p, v, cup_state) → dict``(:func:`kendama_simulate` の ``catch_plan``)。

段階(人のコツ「膝で真上に引き上げ、糸が弛んでから皿を玉の真下へ水平に運び、着地で下げて衝撃を吸う(すくいに行かず待つ)」を写す):
 0. **lift / wait**(:func:`kendama_simulate` 側): 振り上げの間と、弛む前は計画を呼ばない = 弛んでから動かす。
 1. **hold**: 玉の下端がけん玉のいちばん高い所(手元 + kp["top_offset"]、+ ``margin``)より上に出るまで皿を動かさない
    (けんは玉を押せないので、昇ってくる玉にけんを寄せない。玉がそこまで昇らない軌道なら hold のまま = 捕らない)。
 2. **carry**: 皿を今の高さのまま**水平に**、玉が縁に乗る点の真下へ運ぶ: 玉の中心が「皿の中心 + h_c·軸」に下りてくる時刻 τ
    (z(τ) = 皿の高さ + h_c·a_z の遅い根 = 頂点を過ぎて下降中)の玉の xy から h_c·(a_x, a_y) を引いた点。
 3. **absorb**: 着地の ``absorb_time``(既定 √(absorb_depth / a_max) = bang-bang で下げる動きの折り返しの時間)前から、目標を
    ``absorb_depth`` 下げる: 着地の瞬間に皿が下向きに最高速 √(a_max·absorb_depth)(20 m/s²・2 cm で 0.63 m/s)で動いている
    = 相対速さを減らす。absorb_time を長く取ると皿は着地の前に下がり切って止まり、玉はその分深く落ちて速くなる(0.06 s で
    4 技とも縁で弾かれた —— 測って退けた)。
返り値 ``{"target" (皿の中心の目標), "stage", "landing" (玉が縁に乗る点の真下の皿の中心), "t_land", "wait" (hold の残り), "feasible",
"apex", "travel"}``。頂点が縁に乗る高さに届かない軌道は ``feasible=False`` で hold。
制限(正直に): 皿の姿勢は技ごとに固定(手首を回して玉を迎えない)、抗力は予測に入れない(毎回知覚からやり直す)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`kendama`)

[kendama_params](kendama_params.md) · [elliptic_k_agm](elliptic_k_agm.md) · [pendulum_period_exact](pendulum_period_exact.md) · [pendulum_launch_speed](pendulum_launch_speed.md) · [pendulum_rod_simulate](pendulum_rod_simulate.md) · [tether_tension_fixed](tether_tension_fixed.md) · [tether_slack_angle](tether_slack_angle.md) · [swing_up_plan](swing_up_plan.md)

---
*Provenance: kendama.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

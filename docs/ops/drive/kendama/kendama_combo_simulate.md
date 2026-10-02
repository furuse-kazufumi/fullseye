---
op: kendama_combo_simulate
dim: drive
category: kendama
in: table
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# kendama_combo_simulate — DRIVE `kendama` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.kendama_combo_simulate(kp: 'dict', sequence=('ozara', 'chuzara'), *, n_catch: 'int' = 10, hand0=(0.0, 0.0, 1.0), hand_v0=(0.0, 0.0, 0.0), z_home: 'float' = None, apex_above_cup: 'float' = 0.2, k_match: 'float' = 0.8, v_max: 'float' = 2.5, a_max: 'float' = 20.0, a_toss: 'float' = 20.0, omega_max: 'float' = 30.0, rot_clear: 'float' = 0.15, v_rel_max: 'float' = 1.0, dt: 'float' = 0.001, perceive=None, contact=None, contact_tol: 'float' = 0.0005, controller: 'str' = 'pos_vel', t_max: 'float' = None, g: 'float' = None) -> 'dict'` (実装を直接呼ぶなら `import kendama; kendama.kendama_combo_simulate(kp: 'dict', sequence=('ozara', 'chuzara'), *, n_catch: 'int' = 10, hand0=(0.0, 0.0, 1.0), hand_v0=(0.0, 0.0, 0.0), z_home: 'float' = None, apex_above_cup: 'float' = 0.2, k_match: 'float' = 0.8, v_max: 'float' = 2.5, a_max: 'float' = 20.0, a_toss: 'float' = 20.0, omega_max: 'float' = 30.0, rot_clear: 'float' = 0.15, v_rel_max: 'float' = 1.0, dt: 'float' = 0.001, perceive=None, contact=None, contact_tol: 'float' = 0.0005, controller: 'str' = 'pos_vel', t_max: 'float' = None, g: 'float' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("kendama_combo_simulate")`)

## 使い方

連続技: 玉が ``sequence[0]`` の皿に乗った状態から「放つ → 飛んでいる間に持ち替え → 次の皿を着地点の真下へ運び、速さを合わせて受ける」
を ``n_catch`` 回か最初の失敗まで繰り返す(もしかめ = ("ozara", "chuzara")、3 皿 = ("ozara", "kozara", "chuzara"))。
手元 ``hand0`` = 皿胴の中心(持ち替えは手首で向きを変えるだけ、握り替えない: 仮定)。最初の皿へは :func:`kendama_simulate` の
振り上げで受けて、その手元の位置・速度を ``hand0`` / ``hand_v0`` で渡す。

段階(毎回): **absorb**(受けた皿を上限つきで止める: 玉は皿と一緒)→ **toss**(皿を a_toss で上へ加速し、速さ v_toss に達したら
a_max(> g)で止める: 止め始めた歩で皿の抗力が負になり玉が離れる。離れた瞬間の玉の速度 = 皿の速度 → 頂点 = 離れた高さ + v²/2g)→
**flight**(知覚した放物線から着地の時刻 τ と点を出し、手元を「位置 = 着地点の真下(高さ z_home)、速度 = k_match × 玉の着地の速度」へ
:func:`_move_pos_vel` で運ぶ。持ち替えは玉が皿胴の中心から ``rot_clear``(0.15 m: 皿胴の中心から中皿の縁まで 0.12 m + 玉の半径)以上離れてから(知覚で。
離れないまま着地に間に合う最後の時刻が来たらそこで始める = 3 皿の大皿 → 小皿の 180° はこちらになることがある)、角速度の上限 ``omega_max`` の
三角形の角速度で次の姿勢へ回す。回し終わる前には受けない)→ 受けたら absorb に戻る。

物理: 玉は皿の上では皿と一緒に動く(皿の抗力 ∝ (a_皿 + g ẑ)·軸 ≥ 0 の間。負になったら離れる)、飛んでいる間は重力(+ 抗力)と
糸の張力(片側拘束、:func:`kendama_simulate` と同じ射影法)だけ。けんは玉を押さない(``contact(hand, p, R) → 隙間`` が −contact_tol
を下回ったら "hit_ken": :func:`kendamaworld.kendama_clearance` の ``R_ken``)。受ける判定は :func:`kendama_catch_check`(着地の窓
kp["catch_window"]、相対速さ ≤ ``v_rel_max``: 仮定 1 m/s)。窓に入ったのに速すぎたら "too_fast"。受けた瞬間に玉を縁に乗る位置へ置き、
速度を皿の速度にする(非弾性・跳ねない: 仮定。置き直す距離 ≤ 窓の 3 mm)。

放つ高さ(閉形式): 次の着地で玉の中心が乗る高さ z_r の ``apex_above_cup`` 上を頂点にする。今の玉の高さ z₀ から a_toss で加速すると
離れる高さは z₀ + v²/(2 a_toss) なので v_toss² = 2g (z_r + A − z₀) / (1 + g / a_toss)(抗力は入れない)。
``controller="position"``: 飛んでいる間の手元を旧来の :func:`_move_bounded`(位置だけを目標に止まる)で運ぶ対照。
知覚 ``perceive``: None = 真値。:func:`kendamaworld.camera_perceiver`(``flight_from="cup"``)なら毎 step
``perceive(t, p, v, scene)``(scene = 手元の自己受容で分かる量 + 描画用の姿勢 R_ken)を呼び、(p̂, v̂) か None を受ける。
受けたことは手の感覚で分かる(仮定: 触覚)として ``perceive.reset()`` があれば受けた歩で呼ぶ(前の飛翔の放物線を捨てる)。

仮定(公表値なし): 手首の角速度 ≤ 30 rad/s、手元の速さ ≤ 2.5 m/s・加速度 ≤ 20 m/s²、k_match = 0.8(人の「膝で速さを合わせる」の程度)。
返り値 ``{"count" (最初の失敗までに受けた回数), "catches" [{"t", "trick", "rel_speed", "lateral", "apex", "z_catch" (受けた瞬間の玉の中心の高さ), "z_release", "v_release",
"apex_closed", "rose_then_fell", "energy_drift"}], "end_reason" ("done" | "too_fast" | "hit_ken" | "missed" | "timeout"), "t", "p", "v",
"hand", "hand_v", "hand_a", "R", "on_cup", "taut", "stage", "min_gap", "grade" (もしかめの級相当), "max_omega"}``。

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

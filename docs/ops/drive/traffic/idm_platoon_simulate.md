---
op: idm_platoon_simulate
dim: drive
category: traffic
in: any
out: table
examples: [poc_driving_traffic]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# idm_platoon_simulate — DRIVE `traffic` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.idm_platoon_simulate(lead_v_of_t, n_followers: 'int', *, params_per_vehicle, dt: 'float', t_end: 'float', reaction_delay: 'float' = 0.0, seed: 'Optional[int]' = None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivetraffic; drivetraffic.idm_platoon_simulate(lead_v_of_t, n_followers: 'int', *, params_per_vehicle, dt: 'float', t_end: 'float', reaction_delay: 'float' = 0.0, seed: 'Optional[int]' = None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("idm_platoon_simulate")`)

## 使い方

先頭車の速度プロファイルに IDM の追従車列を積分する(車 0 = 先頭、1..n = 追従車)。

引数
----
* ``lead_v_of_t``: 先頭車の速度 [m/s]。``callable(t) -> v`` か、時刻列と同じ長さの配列。
* ``params_per_vehicle``: 追従車ごとの dict(長さ n)か、全車共通の 1 つの dict。キー ``v0, T, a, b, s0``
  (必須)、``delta``(既定 4)、``length``(前の車の車長として使う。既定 4.5 m、仮定)、``reaction_delay``
  (無ければ引数 ``reaction_delay``)、``speed_noise``(希望速度 v0 に掛ける 1 + N(0, speed_noise²) の相対むら。
  > 0 なら ``seed`` が必須 = 決定的)。先頭車の車長は ``params_per_vehicle`` の 1 台目の ``length`` を使う。
* ``reaction_delay``: 反応遅れ [s]。刻み dt の整数倍に丸める(m = round(delay/dt))。車 i は時刻 k に
  **時刻 k − m の自分の速度・車間・相対速度** を見て加速度を決める(t < 0 は初期の定常状態が続いていたとする)。

積分(ballistic update): v_{k+1} = max(0, v_k + a_k dt)、x_{k+1} = x_k + v_k dt + ½ a_k dt²
(速度が負になる刻みでは止まる位置 x_k − v_k²/(2 a_k) で止める)。先頭車の位置は速度の台形積分。
初期状態: 全車が v_lead(0) で走り、各追従車の車間はその速度の平衡車間 ``idm_equilibrium_gap``。
車間が 0 以下になったら(追突)、その車を **接触の位置(車間 0)で止め**、以後は動かさない(速度・加速度 0。前の車や
後ろの車は積分を続け、後ろの車には止まった車が先行車になる)。車を重ねない —— 重ねたまま積分すると位置に意味が無い。

戻り値 dict: ``t`` (K,)、``x``, ``v``, ``a``, ``gap`` (K, n+1)(gap[:, 0] = inf)、``params``(実際に使った
車ごとの母数。速度むら込み)、``delay_steps`` (n,)、``collision``(bool)、``collision_time``(最初の時刻 or None)、
``collisions``(追突の ``(時刻, 車番)`` の列。車番 i は前の車 i−1 に追突した車)、``crashed`` (n+1,) bool。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_traffic](../../../../examples/poc_driving_traffic.py) — `py -3.11 examples/poc_driving_traffic.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`traffic`)

[idm_accel](idm_accel.md) · [idm_equilibrium_gap](idm_equilibrium_gap.md) · [driver_style](driver_style.md) · [lateral_wobble](lateral_wobble.md) · [ou_estimate](ou_estimate.md) · [social_force_step](social_force_step.md) · [pedestrian_crossing](pedestrian_crossing.md) · [occlusion_reveal_distance](occlusion_reveal_distance.md)

---
*Provenance: drivetraffic.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

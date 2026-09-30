---
op: long_simulate
dim: drive
category: long
in: scalar × scalar × any
out: table
examples: [poc_driving_longitudinal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# long_simulate — DRIVE `long` op

- **データ種**: `scalar × scalar × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.long_simulate(s0: 'float', v0: 'float', command: 'Callable', road=None, t_end: 'float' = 30.0, dt: 'float' = 0.01, params: 'Optional[dict]' = None, t_breaks: 'Sequence[float]' = (), t0: 'float' = 0.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivelong; drivelong.long_simulate(s0: 'float', v0: 'float', command: 'Callable', road=None, t_end: 'float' = 30.0, dt: 'float' = 0.01, params: 'Optional[dict]' = None, t_breaks: 'Sequence[float]' = (), t0: 'float' = 0.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("long_simulate")`)

## 使い方

縦の運動方程式を RK4 で積分する(事象の時刻で刻みを切る。モジュールの docstring)。

Parameters
----------
s0, v0 : 初めの位置 [m] (道なりの弧長)と速度 [m/s] (負 = 後ろ向き)
command : ``command(t, s, v) -> (drive, brake)``(どちらも ≥ 0 [m/s²]。上限は μ g cos θ と a_max で頭打ち)。
          **v = 0.0 で呼ばれるのは止まっている間だけ**(動いている刻みの中間点で速度が 0 を横切っても、指令には動きの向きの
          ±1e-300 を渡す)ので、指令は ``v == 0`` / ``v <= 0`` で「止まったら保持」を書いてよい。
          指令が時刻で不連続に変わるなら、その時刻を ``t_breaks`` に入れると刻みがそこで切れる(厳密さのため)。
road : 道の縦断(:func:`road_eval` と同じ)
t_end : 終わりの時刻 [s]、dt : 刻み [s]
params : :func:`long_params` の dict(None = 既定)
t0 : 初めの時刻 [s]

Returns
-------
dict : ``t, s, v, a, drive, brake, z, W_drive, W_brake, W_rr, W_drag``(各 (n,) の配列、a = その時点の加速度)、
``stopped``(bool 配列)、``events``(``("stop"|"move", t, s, 向き)`` の列)、``saturated``(上限で頭打ちになった刻みがあったか)、
``params``。

**Raises** ``ValueError``: 引数が不正、指令が負や非有限を返した。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`long`)

[long_params](long_params.md) · [road_profile](road_profile.md) · [road_eval](road_eval.md) · [long_energy_residual](long_energy_residual.md) · [stopping_distance_grade](stopping_distance_grade.md) · [stop_line_plan](stop_line_plan.md) · [plan_command](plan_command.md) · [hill_hold_brake_min](hill_hold_brake_min.md)

---
*Provenance: drivelong.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: skill_test_score
dim: drive
category: long
in: table
out: table
examples: [poc_driving_longitudinal]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# skill_test_score — DRIVE `long` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.skill_test_score(events, venue: 'str' = '場内', thresholds: 'Optional[dict]' = None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivelong; drivelong.skill_test_score(events, venue: 'str' = '場内', thresholds: 'Optional[dict]' = None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("skill_test_score")`)

## 使い方

技能試験の減点を集計する(警察庁 丙運発第 12 号 令和 4 年の減点細目)。

events : dict の列。
  * ``{"kind": "stop", "gap": 前端から停止線 [m] (負 = 越えた), "signal": "red" など(任意)}`` →
    gap < 0 または gap > stop_gap_max で 停止位置不適。赤信号で越え幅 > signal_violation_over なら 信号無視(試験中止)。
  * ``{"kind": "brake", "stages": 段数}`` → 1 段以下で 制動操作不良(「ブレーキを数回に分けて踏まない場合」)。
  * ``{"kind": "start", "rollback": 逆行 [m] (その場所の累計), "delay": 発進の合図から動き出すまで [s] (任意)}`` →
    逆行小・中・大(大は試験中止)、delay > start_delay_max で 発進手間どり。
  * ``{"kind": "hold", "creep": 保持中に動いた距離 [m]}`` → creep > creep_eps で 制動操作不良(クリープ)。
venue : "場内" か "路上"(点数が違う細目がある)。

Returns
-------
dict : ``deductions``(``(細目, 点, 説明)`` の列。点 None = 試験中止)、``total``(減点の合計)、``score``(100 − 合計、
試験中止なら None)、``test_stopped``、``passed``(第一種 70 点以上)、``thresholds``。

**Raises** ``ValueError``: venue が不正、event の kind が不明・値が非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_longitudinal](../../../../examples/poc_driving_longitudinal.py) — `py -3.11 examples/poc_driving_longitudinal.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`long`)

[long_params](long_params.md) · [road_profile](road_profile.md) · [road_eval](road_eval.md) · [long_simulate](long_simulate.md) · [long_energy_residual](long_energy_residual.md) · [stopping_distance_grade](stopping_distance_grade.md) · [stop_line_plan](stop_line_plan.md) · [plan_command](plan_command.md)

---
*Provenance: drivelong.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

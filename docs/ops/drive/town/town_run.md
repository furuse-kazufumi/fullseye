---
op: town_run
dim: drive
category: town
in: table
out: table
examples: [poc_driving_japan_town, poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# town_run — DRIVE `town` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.town_run(layout, *, dt: 'float' = 0.05, v_max: 'float' = 8.0, a_max: 'float' = 1.5, b_max: 'float' = 3.0, stop_at: 'Optional[Sequence[str]]' = None, stop_hold: 'Optional[float]' = None, look_hold: 'Optional[float]' = None, stop_margin: 'float' = 0.5, idm_T: 'float' = 1.0, v_stop: 'Optional[float]' = None, t_max: 'Optional[float]' = None, rules: 'Optional[dict]' = None, train=None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivetown; drivetown.town_run(layout, *, dt: 'float' = 0.05, v_max: 'float' = 8.0, a_max: 'float' = 1.5, b_max: 'float' = 3.0, stop_at: 'Optional[Sequence[str]]' = None, stop_hold: 'Optional[float]' = None, look_hold: 'Optional[float]' = None, stop_margin: 'float' = 0.5, idm_T: 'float' = 1.0, v_stop: 'Optional[float]' = None, t_max: 'Optional[float]' = None, rules: 'Optional[dict]' = None, train=None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("town_run")`)

## 使い方

中心線に沿う縦だけの通し走行(ルールベース)。

各刻みで、まだ止まっていない次の **目標の停止線** を「止まっている先行車」と見なし、
``drivetraffic.idm_accel(v, gap = 停止線 − 前端, dv = v, v0 = v_max, T = idm_T, a = a_max, b = b_max, s0 = stop_margin)``
で加速度を出し ``[−b_max, a_max]`` に切る(目標が無ければ gap = ∞ = 自由走行)。v を先に更新(0 ≤ v ≤ v_max)、s は台形則。
``v ≤ v_stop`` かつ前端が停止線の 1.0 m 以内なら停止。

目標の決まり方(``rules`` = :func:`town_rules`、None = JP): 交差点は常に目標(信号は ``stop_hold`` 秒で青の規則)。踏切は
``rules["crossing_stop"]`` が "always" なら常に、"when_active" なら ``train`` の警報中(``entry_forbidden``)だけ目標。
"when_active" で警報が始まった時に b_max で止まれない(gap < v²/(2 b_max))なら進む(event "commit")。``stop_at`` を渡すと
規則より優先する(kind の列。回帰用)。停止後: 交差点は ``stop_hold``(既定 rules["hold_s"])秒保持(mode "hold")、踏切は
``rules["look_required"]`` なら左・右・左・右を各 ``look_hold``(既定 rules["look_hold_s"])秒見る(mode "look")。``train`` が
あれば、保持が明けても警報中(かん降下〜上昇中)は待つ(mode "wait")。``train`` = t_warning か (t_warning[, v_train[, length]])
か dict(時刻は解釈基準の標準値、:data:`TRAIN_DEFAULTS`)。

Returns
-------
dict : ``t, s, x, y, z, v, yaw, a`` (各 (n,))、``mode`` (n,) 文字列("cruise" / "brake" / "hold" / "look" / "wait")、
``stops`` = [(s_stop, kind, t_arrive, t_leave), ...]、``events`` = [("stop"|"go"|"look"|"wait_gate"|"commit"|"pass"|"end", t, ...)]、
``stop_lines``(目標になり得た停止線)、``targets``(停止線ごとの "static" / "dynamic")、``train``(時刻の dict か None)、
``rules``、``params``、``total_length``。

**Raises** ``ValueError``: layout が town_chain の物でも drivejapan.osm_route の "route" でもない、dt/v_max/a_max/b_max/保持時間が不正、stop_at に知らない kind、
rules/train が不正、停止線を越えてしまった(IDM の想定外)、t_max までに終点に着かない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`
- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`town`)

[town_chain](town_chain.md) · [town_layout](town_layout.md) · [town_world](town_world.md) · [town_centerline](town_centerline.md) · [town_stop_lines](town_stop_lines.md) · [town_rules](town_rules.md) · [town_crossing_state](town_crossing_state.md) · [town_checks](town_checks.md)

---
*Provenance: drivetown.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

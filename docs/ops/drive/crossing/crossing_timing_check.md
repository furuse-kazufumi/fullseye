---
op: crossing_timing_check
dim: drive
category: crossing
in: 
out: table
examples: [poc_driving_crossing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# crossing_timing_check — DRIVE `crossing` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.crossing_timing_check(t_warning, t_closed, t_arrival, *, timing: 'Optional[dict]' = None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivecrossing; drivecrossing.crossing_timing_check(t_warning, t_closed, t_arrival, *, timing: 'Optional[dict]' = None) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("crossing_timing_check")`)

## 使い方

踏切の 3 つの時刻(警報開始・遮断動作の終了・列車の到達)を解釈基準の標準と最小に照らす(配列 = 列車ごと)。

警報→到達の 30 / 20 秒は解釈基準 5(3) の**踏切警報機**(遮断機なし)の値。遮断機のある踏切では 4(3)(5) の 2 つ
(15 + 20 = 35 秒が標準)が効き、30 / 20 秒の側は自動的に満たされる。

返り値: ``warn_to_closed`` / ``closed_to_arrival`` / ``warn_to_arrival``(各 [s])、``meets_minimum``(3 つとも最小以上)、
``deviation``(標準からのずれ、3 つ)、``spread``(列車ごとの警報開始→到達の最大 − 最小。解釈基準 5(4)「速度等により
大きく異なるものでない」の量)。時刻の順が逆(遮断終了が警報より前など)は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_crossing](../../../../examples/poc_driving_crossing.py) — `py -3.11 examples/poc_driving_crossing.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`crossing`)

[crossing_gate_state](crossing_gate_state.md) · [crossing_lamp_signal](crossing_lamp_signal.md) · [lamp_pair_phase](lamp_pair_phase.md) · [crossing_clear_time](crossing_clear_time.md) · [exit_room_check](exit_room_check.md) · [crossing_stop_check](crossing_stop_check.md) · [track_sight_distance](track_sight_distance.md) · [sight_triangle_distance](sight_triangle_distance.md)

---
*Provenance: drivecrossing.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

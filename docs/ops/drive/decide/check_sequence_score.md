---
op: check_sequence_score
dim: drive
category: decide
in: table
out: table
examples: [poc_driving_decisions]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# check_sequence_score — DRIVE `decide` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.check_sequence_score(events, *, maneuver: 'str' = 'lane_change', lead_time: 'float' = 3.0, lead_tol: 'float' = 0.5, max_lead: 'Optional[float]' = None, signal_distance: 'float' = 30.0, distance_tol: 'float' = 3.0, cancel_tol: 'float' = 2.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivedecide; drivedecide.check_sequence_score(events, *, maneuver: 'str' = 'lane_change', lead_time: 'float' = 3.0, lead_tol: 'float' = 0.5, max_lead: 'Optional[float]' = None, signal_distance: 'float' = 30.0, distance_tol: 'float' = 3.0, cancel_tol: 'float' = 2.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("check_sequence_score")`)

## 使い方

進路変更・右左折の前の「安全確認 → 合図 → (約 3 秒 / 30 m)→ 行為 → 合図をやめる」を採点する。

``events``: ``{"t": 時刻, "kind": 種類, "s": 道のりの位置(任意)}`` の列。種類は
``mirror`` / ``head_check``(安全確認)、``signal_on`` / ``signal_off``(合図)、``start``(進路を変え始めた /
右左折の地点に達した)、``end``(行為が終わった)。``start`` は必須(1 回)。

規則(根拠は ``SOURCES``):

1. 合図がある(``signal_missing``)。
2. 合図より前(かつ start より前)に安全確認がある(``safety_check_missing``。教則「あらかじめバックミラーなどで
   安全を確かめてから合図」)。
3. 合図の時期(``signal_timing``): 進路変更は start − 合図 ≥ ``lead_time − lead_tol``(教則「約 3 秒前」。許容は仮定)、
   ``max_lead`` を与えれば早すぎも減点。右左折・転回は start の位置 − 合図の位置 ≥ ``signal_distance − distance_tol``
   (教則「30 メートル手前」。``s`` が必要)。
4. ``end`` より前に合図をやめていない(``signal_not_continued``、法 53 条 1 項)。
5. ``end`` の後 ``cancel_tol`` 秒以内に合図をやめた(``signal_not_cancelled``、法 53 条 4 項。許容は仮定)。
   ``end`` が無ければ 4・5 は見ない。

返り値: ``violations``(各 ``{"rule", "detail", "deduction"}``)、``deduction``、``score`` = 100 − deduction、
``ok``、``lead``(秒、進路変更)/ ``distance``(m、右左折)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`decide`)

[mirror_reflection_matrix](mirror_reflection_matrix.md) · [mirror_virtual_camera](mirror_virtual_camera.md) · [mirror_aim_normal](mirror_aim_normal.md) · [convex_mirror_fov](convex_mirror_fov.md) · [mirror_blind_zone](mirror_blind_zone.md) · [signal_phase_plan](signal_phase_plan.md) · [signal_state](signal_state.md) · [predict_amber_onset](predict_amber_onset.md)

---
*Provenance: drivedecide.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

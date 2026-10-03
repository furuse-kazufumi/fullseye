---
op: town_crossing_state
dim: drive
category: town
in: table
out: table
examples: [poc_driving_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# town_crossing_state — DRIVE `town` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.town_crossing_state(world: 'dict', t: 'float', train: 'Optional[dict]', *, exposure: 'float' = 0.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import drivetown; drivetown.town_crossing_state(world: 'dict', t: 'float', train: 'Optional[dict]', *, exposure: 'float' = 0.0) -> 'Dict[str, object]'`、台帳から引くなら `opsdrive.get("town_crossing_state")`)

## 使い方

時刻 t の踏切の設備を世界に書き込む(全部の踏切に同じ列車の時刻を使う)。

``train`` = :func:`town_run` の ``run["train"]``(None = 待機: かん上・灯消灯・列車は遠く)。状態は既存 op
:func:`drivecrossing.crossing_gate_state`(警報 → 降下 → 遮断 → 上昇、かんの角)と :func:`drivecrossing.crossing_lamp_signal`
(2 灯の交互点滅、``exposure`` > 0 でカメラの露光平均)で評価する。列車の先頭は ``t_arrival`` に道路の縁(手前 margin)に着き、
``v_train`` で +y(局所)へ進む。返り値 ``{"state", "state_name", "boom_angle", "lamps", "entry_forbidden", "train_y"}``。

**Raises** ``ValueError``: world が town_world の物でない、t が非有限、train の鍵が足りない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_town](../../../../examples/poc_driving_town.py) — `py -3.11 examples/poc_driving_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`town`)

[town_chain](town_chain.md) · [town_layout](town_layout.md) · [town_world](town_world.md) · [town_centerline](town_centerline.md) · [town_stop_lines](town_stop_lines.md) · [town_rules](town_rules.md) · [town_run](town_run.md) · [town_checks](town_checks.md)

---
*Provenance: drivetown.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

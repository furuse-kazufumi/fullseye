---
op: cr_drive_sweep
dim: drive
category: commonroad
in: table
out: table
examples: [poc_driving_commonroad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# cr_drive_sweep — DRIVE `commonroad` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cr_drive_sweep(scene, pp_index: 'int' = 0, *, grid=None, margin: 'float' = 0.15, **kwargs) -> 'dict'` (実装を直接呼ぶなら `import drivecommonroad; drivecommonroad.cr_drive_sweep(scene, pp_index: 'int' = 0, *, grid=None, margin: 'float' = 0.15, **kwargs) -> 'dict'`、台帳から引くなら `opsdrive.get("cr_drive_sweep")`)

## 使い方

ルールベースの gap acceptance: 運転手の母数の格子を穏やかな順に試し、**最初に全部の門を通った走行** を返す。

門 = ゴール到達 ∧ :func:`cr_feasible` ∧ :func:`cr_collision` で障害物なし(``margin`` だけ膨らませた判定)∧ 道路境界なし。
``grid`` は ``{"a_lat": (...), "lookahead": (...), "k_v": (...), "v_cruise": (...)}`` 形式(既定 = a_lat 2.5→10、lookahead 5/8、
k_v 0.6/1.0、v_cruise None)。他の kwargs は :func:`cr_drive` へ。

返り値 ``{"run" (通った走行 | None), "settings" (その母数 | None), "tries": [{"settings", "goal_reached", "feasible",
"obstacle_collision", "boundary_violation", "first_collision"}], "n_tries"}``。通る物が無ければ ``run`` は None(ValueError ではない)。

**Raises** ``ValueError``: grid のキーが上記以外、margin < 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_commonroad](../../../../examples/poc_driving_commonroad.py) — `py -3.11 examples/poc_driving_commonroad.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`commonroad`)

[cr_synthetic](cr_synthetic.md) · [cr_read](cr_read.md) · [cr_route](cr_route.md) · [ks_step](ks_step.md) · [cr_drive](cr_drive.md) · [cr_feasible](cr_feasible.md) · [cr_collision](cr_collision.md) · [cr_solution_xml](cr_solution_xml.md)

---
*Provenance: drivecommonroad.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

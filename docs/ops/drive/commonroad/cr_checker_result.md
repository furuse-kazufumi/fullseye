---
op: cr_checker_result
dim: drive
category: commonroad
in: any
out: table
examples: [poc_driving_commonroad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# cr_checker_result — DRIVE `commonroad` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cr_checker_result(path) -> 'dict'` (実装を直接呼ぶなら `import drivecommonroad; drivecommonroad.cr_checker_result(path) -> 'dict'`、台帳から引くなら `opsdrive.get("cr_checker_result")`)

## 使い方

WSL の公式チェッカー(tools/check_solution_json.py)が書いた JSON を読む。

必須キー :data:`CHECKER_KEYS`(``valid`` / ``goal_reached`` / ``feasible`` / ``obstacle_collision`` / ``boundary_collision``
は bool、``scenario`` / ``solution`` / ``checker_version`` は文字列)。それ以外のキー(``details`` 等)はそのまま返す。

**Raises** ``ValueError``: ファイルが無い、JSON でない、必須キーの欠落、型違い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_commonroad](../../../../examples/poc_driving_commonroad.py) — `py -3.11 examples/poc_driving_commonroad.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`commonroad`)

[cr_synthetic](cr_synthetic.md) · [cr_read](cr_read.md) · [cr_route](cr_route.md) · [ks_step](ks_step.md) · [cr_drive](cr_drive.md) · [cr_drive_sweep](cr_drive_sweep.md) · [cr_feasible](cr_feasible.md) · [cr_collision](cr_collision.md)

---
*Provenance: drivecommonroad.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

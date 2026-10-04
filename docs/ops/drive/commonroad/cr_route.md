---
op: cr_route
dim: drive
category: commonroad
in: table
out: table
examples: [poc_driving_commonroad]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# cr_route — DRIVE `commonroad` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cr_route(scene, lanelet_from, lanelet_to=None, *, goal=None, step: 'float' = 0.5) -> 'dict'` (実装を直接呼ぶなら `import drivecommonroad; drivecommonroad.cr_route(scene, lanelet_from, lanelet_to=None, *, goal=None, step: 'float' = 0.5) -> 'dict'`、台帳から引くなら `opsdrive.get("cr_route")`)

## 使い方

successor の BFS(hop 数最小)で lanelet の列を出し、中心線を継いで ``step`` m で再標本化する。

``lanelet_to`` が None なら ``goal["position_lanelets"]`` を終点にする(どちらも無ければ ValueError)。
返り値 ``{"lanelets", "polyline" (K,2), "cum" (K,), "length", "speed_limit_mps" (経路上の最小 | None),
"lanelet_s" (各 lanelet が始まる弧長), "lanelet_len", "polygons" [多角形]}``。``length`` = 継いだ中心線の折線長
(継ぎ目で重なる頂点は 1 つに潰す)。

**Raises** ``ValueError``: 未知の lanelet、到達不能、終点が無い。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_commonroad](../../../../examples/poc_driving_commonroad.py) — `py -3.11 examples/poc_driving_commonroad.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`commonroad`)

[cr_synthetic](cr_synthetic.md) · [cr_read](cr_read.md) · [ks_step](ks_step.md) · [cr_drive](cr_drive.md) · [cr_drive_sweep](cr_drive_sweep.md) · [cr_feasible](cr_feasible.md) · [cr_collision](cr_collision.md) · [cr_solution_xml](cr_solution_xml.md)

---
*Provenance: drivecommonroad.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: world_move
dim: drive
category: world
in: table
out: any
examples: [poc_driving_decisions, poc_ttc_rss, poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# world_move — DRIVE `world` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.world_move(world: 'dict', i: 'int', x: 'float', y: 'float', yaw: 'float', z: 'float' = 0.0) -> 'None'` (実装を直接呼ぶなら `import driveworld; driveworld.world_move(world: 'dict', i: 'int', x: 'float', y: 'float', yaw: 'float', z: 'float' = 0.0) -> 'None'`、台帳から引くなら `opsdrive.get("world_move")`)

## 使い方

物体 i(資産で置いたもの)を新しい姿勢 (x, y, yaw) へ動かす(頂点だけ書き換える。面・ラベル・色は不変)。

対向車を 1 コマずつ進める(15 巡目の TTC)ための op。資産でない物体(縁石・路面・信号機)は ``ValueError``。
姿勢の意味は :func:`add_asset` と同じ(資産の原点 = 箱の底面中心、yaw は +x から反時計回り)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_decisions](../../../../examples/poc_driving_decisions.py) — `py -3.11 examples/poc_driving_decisions.py`
- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`world`)

[world_build](world_build.md) · [world_camera](world_camera.md) · [load_asset](load_asset.md)

---
*Provenance: driveworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

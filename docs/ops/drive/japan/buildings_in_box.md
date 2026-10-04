---
op: buildings_in_box
dim: drive
category: japan
in: table
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# buildings_in_box — DRIVE `japan` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.buildings_in_box(parsed: 'dict[str, Any]', xmin: 'float', xmax: 'float', ymin: 'float', ymax: 'float') -> 'list[dict[str, Any]]'` (実装を直接呼ぶなら `import driveplateau; driveplateau.buildings_in_box(parsed: 'dict[str, Any]', xmin: 'float', xmax: 'float', ymin: 'float', ymax: 'float') -> 'list[dict[str, Any]]'`、台帳から引くなら `opsdrive.get("buildings_in_box")`)

## 使い方

重心(足元頂点の平均)が箱 [xmin,xmax]×[ymin,ymax] に入る建物だけを返す。

Args:
    parsed: ``plateau_parse`` の返り値。
    xmin, xmax, ymin, ymax: 局所座標の箱 [m] (両端を含む)。

Raises:
    ValueError: parsed に ``buildings`` が無い、xmin > xmax または ymin > ymax。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md)

---
*Provenance: driveplateau.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

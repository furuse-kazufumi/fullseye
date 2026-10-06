---
op: triangulate_polygon
dim: drive
category: japan
in: any
out: any
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# triangulate_polygon — DRIVE `japan` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.triangulate_polygon(poly: 'np.ndarray | Sequence[Sequence[float]]') -> 'np.ndarray'` (実装を直接呼ぶなら `import driveplateau; driveplateau.triangulate_polygon(poly: 'np.ndarray | Sequence[Sequence[float]]') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("triangulate_polygon")`)

## 使い方

単純多角形(凸・凹どちらも、自己交差なし)を耳切り法で三角形分割する。

返す三角形は入力頂点の添字 (k-2, 3) で、各三角形は反時計回り(入力が時計回りなら
内部で反転して扱い、添字は元の頂点番号で返す)。

Args:
    poly: (k,2) 頂点列。閉じていなくてよい。

Returns:
    (k-2, 3) int64 配列。

Raises:
    ValueError: 頂点が 3 未満、面積がほぼ 0、耳が見つからない(自己交差や重複点の疑い)。

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

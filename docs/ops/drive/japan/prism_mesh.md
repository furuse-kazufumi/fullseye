---
op: prism_mesh
dim: drive
category: japan
in: any
out: any
examples: [poc_print_layer_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# prism_mesh — DRIVE `japan` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.prism_mesh(footprint: 'np.ndarray | Sequence[Sequence[float]]', height: 'float', *, base_z: 'float' = 0.0) -> 'tuple[np.ndarray, np.ndarray, np.ndarray]'` (実装を直接呼ぶなら `import driveplateau; driveplateau.prism_mesh(footprint: 'np.ndarray | Sequence[Sequence[float]]', height: 'float', *, base_z: 'float' = 0.0) -> 'tuple[np.ndarray, np.ndarray, np.ndarray]'`、台帳から引くなら `opsdrive.get("prism_mesh")`)

## 使い方

足元多角形を高さ ``height`` の柱に押し出す(底面なし)。

頂点の並びは ``V[0:k]`` が底の環、``V[k:2k]`` が天井の環(同じ順)。
側面は辺ごとに四角形 2 三角形、屋根は耳切りの三角形。外向き法線になる向きで返す。

Args:
    footprint: (k,2) 局所 x,y [m]。向きは任意(内部で反時計回りに揃える)。
    height: 柱の高さ [m] > 0。
    base_z: 底の z [m]。

Returns:
    ``(V (2k,3) float64, F (m,3) int64, is_roof (m,) bool)``。

Raises:
    ValueError: height ≤ 0 / 非有限、footprint が不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_print_layer_inspection](../../../../examples/poc_print_layer_inspection.py) — `py -3.11 examples/poc_print_layer_inspection.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md)

---
*Provenance: driveplateau.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

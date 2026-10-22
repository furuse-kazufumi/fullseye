---
op: building_prisms
dim: drive
category: japan
in: any
out: any
examples: [gallery_drive_city_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# building_prisms — DRIVE `japan` op

- **データ種**: `any` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.building_prisms(buildings: 'Iterable[dict[str, Any]]', *, color_fn: 'Callable[[dict[str, Any]], Sequence[float]] | None' = None, base_z: 'float | None' = 0.0, roof_shade: 'float' = 0.92) -> 'tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]'` (実装を直接呼ぶなら `import driveplateau; driveplateau.building_prisms(buildings: 'Iterable[dict[str, Any]]', *, color_fn: 'Callable[[dict[str, Any]], Sequence[float]] | None' = None, base_z: 'float | None' = 0.0, roof_shade: 'float' = 0.92) -> 'tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]'`、台帳から引くなら `opsdrive.get("building_prisms")`)

## 使い方

建物の足跡(footprint)を高さまで押し出し、1 つの三角形メッシュにまとめる。

Args:
    buildings: ``plateau_parse`` の ``buildings``(``footprint``, ``height``, ``ground_z``)。
    color_fn: ``building -> (r,g,b)`` 0..1。None なら ``_default_building_color``。
    base_z: 全建物の底 z [m]。None なら各建物の ``ground_z`` を使う(起伏のある世界向け)。
        自前の平らな道路世界には 0.0 が合う。
    roof_shade: 屋根面の色の倍率(側面と見分けるための控えめな陰)。

Returns:
    ``(V (n,3) float64, F (m,3) int64, colors (m,3) float64 0..1, ids (m,) int64)``。
    ``ids[f]`` は面 f が属する建物の番号(入力列の添字)。建物が 0 件なら各配列は空。

Raises:
    ValueError: color_fn の返り値が RGB 3 要素 0..1 でない、建物の footprint/height が不正。

空の入力(``buildings`` が 0 件)は空を返す(理由: 建物が 0 件のタイルは実データに普通にある。空の角柱集合が正しい答え)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gallery_drive_city_terrain](../../../../examples/gallery_drive_city_terrain.py) — `py -3.11 examples/gallery_drive_city_terrain.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md)

---
*Provenance: driveplateau.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: citygml_synthetic
dim: drive
category: japan
in: 
out: any
examples: [poc_driving_japan_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# citygml_synthetic — DRIVE `japan` op

- **データ種**: `なし` → `any`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.citygml_synthetic(n: 'int' = 4, *, origin: 'tuple[float, float]' = (35.6716, 139.765), spacing: 'float' = 30.0, size: 'float' = 12.0, heights: 'Sequence[float] | None' = None, ground_z: 'float' = 0.0, omit_measured_height: 'Iterable[int]' = (), use_lod0_footprint: 'bool' = False, ns_building: 'str' = 'http://www.opengis.net/citygml/building/2.0') -> 'str'` (実装を直接呼ぶなら `import driveplateau; driveplateau.citygml_synthetic(n: 'int' = 4, *, origin: 'tuple[float, float]' = (35.6716, 139.765), spacing: 'float' = 30.0, size: 'float' = 12.0, heights: 'Sequence[float] | None' = None, ground_z: 'float' = 0.0, omit_measured_height: 'Iterable[int]' = (), use_lod0_footprint: 'bool' = False, ns_building: 'str' = 'http://www.opengis.net/citygml/building/2.0') -> 'str'`、台帳から引くなら `opsdrive.get("citygml_synthetic")`)

## 使い方

本物と同じ構造の最小 CityGML 2.0 文字列を作る(テスト・デモ用)。

建物は ``size`` [m] の正方形を ``spacing`` [m] 間隔で x 方向に並べ、各建物に
``bldg:measuredHeight`` と ``bldg:lod1Solid > gml:Solid > gml:exterior >
gml:CompositeSurface > gml:surfaceMember × 6 > gml:Polygon > gml:exterior >
gml:LinearRing > gml:posList``(底面 + 側面 4 + 天面、lat lon alt の順)を書く。
等距円筒近似は線形なので、局所座標で作った正方形は読み戻すと面積が size² に一致する。

Args:
    n: 建物数(≥ 0)。
    origin: 建物 0 の中心の (lat, lon) [deg]。
    spacing: 建物中心の間隔 [m]。
    size: 正方形の一辺 [m]。
    heights: 各建物の高さ [m]。None なら ``10 + 5*i``。
    ground_z: 底面の標高 [m]。
    omit_measured_height: この添字の建物では ``measuredHeight`` を書かない。
    use_lod0_footprint: True なら lod1Solid の前に ``lod0FootPrint``(底面のみ)も書く。
    ns_building: bldg 名前空間 URI(版違いの試験用に差し替え可)。

Returns:
    UTF-8 で書き出せる CityGML 文字列。

Raises:
    ValueError: n が負、size/spacing が非正、heights の長さ不一致や非正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md)

---
*Provenance: driveplateau.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

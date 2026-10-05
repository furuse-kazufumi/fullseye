---
op: plateau_parse
dim: drive
category: japan
in: any
out: table
examples: [poc_driving_japan_town]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# plateau_parse — DRIVE `japan` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.plateau_parse(source: 'str | Path | bytes', *, origin: 'tuple[float, float] | None' = None, max_buildings: 'int | None' = None) -> 'dict[str, Any]'` (実装を直接呼ぶなら `import driveplateau; driveplateau.plateau_parse(source: 'str | Path | bytes', *, origin: 'tuple[float, float] | None' = None, max_buildings: 'int | None' = None) -> 'dict[str, Any]'`、台帳から引くなら `opsdrive.get("plateau_parse")`)

## 使い方

PLATEAU CityGML から建物の足元多角形・高さ・底面標高をストリーム読みする。

``iterparse`` で ``Building``(ローカル名)の end イベントごとに処理し、
処理後 ``elem.clear()`` でメモリを解放する(1 ファイル数百 MB でも動く設計)。

建物ごとに:
  * ``measuredHeight`` があれば高さに使う。無ければ ``lod1Solid`` の最大標高 − 最小標高。
  * 足元: ``lod0FootPrint`` があればその posList。無ければ ``lod1Solid`` の全面のうち
    **平均標高が最も低い面**(LOD1 は押し出し柱なので底面がある)。
  * posList は EPSG:6697 の「緯度 経度 標高」3 つ組として読む。

Args:
    source: CityGML の文字列(``<`` で始まる)、bytes、またはファイルパス(str/Path)。
    origin: 局所座標の原点 ``(lat0, lon0)`` [deg]。None なら最初に採用した建物の重心。
    max_buildings: 採用する建物数の上限(None で無制限)。到達したら読み取りを止める。

Returns:
    ``{"origin": (lat0, lon0), "buildings": [...], "n_skipped": int,
    "crs": "EPSG:6697 (lat, lon, alt)"}``。各建物は
    ``{"id", "footprint" (k,2) float64(局所 x,y[m]、閉じない、反時計回り),
    "height", "ground_z", "lat", "lon"}``(lat/lon は足元頂点の平均 = 重心)。

Raises:
    ValueError: source が空/不正、posList が 3 の倍数でない、XML が壊れている、
        max_buildings が負、origin が不正。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_japan_town](../../../../examples/poc_driving_japan_town.py) — `py -3.11 examples/poc_driving_japan_town.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md)

---
*Provenance: driveplateau.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

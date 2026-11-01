---
op: plateau_lod2_mesh
dim: drive
category: japan
in: any
out: table
gpu: なし
examples: [poc_plateau_venue_lod2]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# plateau_lod2_mesh — DRIVE `japan` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.plateau_lod2_mesh(source: 'str | Path | bytes', *, origin: 'tuple[float, float, float] | None' = None, ids: 'Iterable[str] | None' = None, bbox_latlon: 'tuple[float, float, float, float] | None' = None, on_bad_polygon: 'str' = 'raise') -> 'dict[str, Any]'` (実装を直接呼ぶなら `import driveplateau; driveplateau.plateau_lod2_mesh(source: 'str | Path | bytes', *, origin: 'tuple[float, float, float] | None' = None, ids: 'Iterable[str] | None' = None, bbox_latlon: 'tuple[float, float, float, float] | None' = None, on_bad_polygon: 'str' = 'raise') -> 'dict[str, Any]'`、台帳から引くなら `opsdrive.get("plateau_lod2_mesh")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

PLATEAU の CityGML から LOD2 の建物を読み、局所メートル座標の三角形メッシュ (V, F) と建物ごとの属性を返す。

``bldg:Building`` を ``iterparse`` でストリーム読みし、本体と ``bldg:BuildingPart`` を 1 つずつ **部位**
(unit)として扱う。面は主題面(``GroundSurface`` / ``WallSurface`` / ``RoofSurface`` / ``OuterCeilingSurface``
/ ``OuterFloorSurface`` / ``ClosureSurface``)の ``lod2MultiSurface`` から取り、面種を ``face_kind`` に残す。
``lod2Solid`` が ``xlink:href`` で参照する面はすべて見つかることを確かめる。穴(``gml:interior``)は外周へ
橋を架けて耳切りで三角形にし、三角形の向きは元の環の向き(外向き法線)を保つ。

座標は EPSG:6697(JGD2011 の緯度・経度・標高)を GRS80 の地心直交座標経由で原点の接平面の
ENU(x 東, y 北, z 上, メートル)へ厳密に移す。既定の原点は **地面の重心**: ``GroundSurface`` の頂点の
緯度経度の平均と、その最低標高(地面が無ければ全頂点)。

**fail-closed**: 6697 以外の ``srsName``、``srsDimension`` が 3 以外、LOD2 の幾何に未知の gml 要素
(``Triangle``・``OrientableSurface``・``pos`` の点列など)、表に無い主題面、見つからない xlink、
m 以外の ``measuredHeight`` の単位は、読み飛ばさず ``ValueError`` にする。

Args:
    source: CityGML の文字列(``<`` で始まる)、bytes、またはファイルパス(str/Path)。
    origin: 局所座標の原点 ``(lat0 [deg], lon0 [deg], h0 [m])``。None なら地面の重心。
    ids: 読む建物の ``gml:id``(``bldg:Building`` の id)。None なら全部。
    bbox_latlon: ``(lat_min, lon_min, lat_max, lon_max)``。部位の頂点の平均がこの箱に入る部位だけ残す。
    on_bad_polygon: 三角形にできない Polygon(面積 0・自己交差)の扱い。``"raise"``(既定)か
        ``"skip"``(数えて ``n_bad_polygons`` に残す)。

Returns:
    ``{"V": (n,3) float64 [m], "F": (m,3) int64, "face_unit": (m,) int64, "face_kind": (m,) int8,
    "kinds": LOD2_KINDS, "units": [...], "origin": (lat0, lon0, h0), "crs": str,
    "n_buildings": int, "n_no_lod2": int, "n_bad_polygons": int, "max_nonplanarity_m": float}``。
    ``units[i]`` は ``{"building_id", "part", "gml_id", "measured_height", "attrs", "z_min", "z_max",
    "ground_z", "height_mesh", "extent_xy", "lat", "lon", "n_faces"}``。``height_mesh`` は
    ``z_max − ground_z``(``measuredHeight`` と比べる値)、``extent_xy`` は ENU の (x 幅, y 幅) [m]。

Raises:
    ValueError: 上の fail-closed の条件、source が空・不正、XML が壊れている、該当する部位が 0 件、
        ``on_bad_polygon`` が未知、``origin`` / ``bbox_latlon`` が不正。

Examples:
    >>> import driveplateau as PL
    >>> m = PL.plateau_lod2_mesh(PL._citygml_lod2_example())
    >>> [round(u["height_mesh"], 3) for u in m["units"]]
    [12.0, 4.0]
    >>> m["V"].shape[1], m["F"].shape[1], sorted(set(m["face_kind"].tolist()))
    (3, 3, [0, 1, 2])

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_plateau_venue_lod2](../../../../examples/poc_plateau_venue_lod2.py) — `py -3.11 examples/poc_plateau_venue_lod2.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`japan`)

[osm_synthetic](osm_synthetic.md) · [osm_parse](osm_parse.md) · [osm_road_graph](osm_road_graph.md) · [osm_road_mask](osm_road_mask.md) · [osm_road_loops](osm_road_loops.md) · [osm_route](osm_route.md) · [japan_world](japan_world.md) · [japan_stats](japan_stats.md)

---
*Provenance: driveplateau.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

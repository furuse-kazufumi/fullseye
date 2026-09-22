---
op: dem_geodetic_from_enu
dim: dem
category: geodesy
in: points
out: points
examples: [poc_geodetic_benchmarks_real, poc_geodetic_height_frames]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# dem_geodetic_from_enu — DEM `geodesy` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_geodetic_from_enu(enu, lat0_deg, lon0_deg, h0_m)` (実装を直接呼ぶなら `import demops; demops.dem_geodetic_from_enu(enu, lat0_deg, lon0_deg, h0_m)`、台帳から引くなら `opsdem.get("dem_geodetic_from_enu")`)

## 使い方

局所 ENU → 測地座標(:func:`dem_enu_from_geodetic` の逆)。``points``。

Args:
    enu: ``(n, 3)`` の ``(east, north, up)`` [m]。
    lat0_deg / lon0_deg / h0_m: 基準点の測地座標。
Returns:
    ``(n, 3)`` の ``(緯度[度], 経度[度], 楕円体高[m])``。

閉じた式で検査できること: 往復が 1e-9 m 級、``(0, 0, 0)`` は基準点そのもの。

**ValueError**: ``(n, 3)`` でない、非有限、基準点が不正。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_geodetic_benchmarks_real](../../../../examples/poc_geodetic_benchmarks_real.py) — `py -3.11 examples/poc_geodetic_benchmarks_real.py`
- [poc_geodetic_height_frames](../../../../examples/poc_geodetic_height_frames.py) — `py -3.11 examples/poc_geodetic_height_frames.py`

## 型が繋がる次の op(`points` を入力に取れる)

[dem_ecef_to_geodetic](dem_ecef_to_geodetic.md)

## 同カテゴリ(`geodesy`)

[dem_geodetic_to_ecef](dem_geodetic_to_ecef.md) · [dem_ecef_to_geodetic](dem_ecef_to_geodetic.md) · [dem_geocentric_grid](dem_geocentric_grid.md) · [dem_earth_curvature_drop](dem_earth_curvature_drop.md) · [dem_cell_size_webmercator](dem_cell_size_webmercator.md) · [dem_geodetic_slope](dem_geodetic_slope.md) · [dem_geoid_height](dem_geoid_height.md) · [dem_height_frame_convert](dem_height_frame_convert.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

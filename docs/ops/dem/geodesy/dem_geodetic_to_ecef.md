---
op: dem_geodetic_to_ecef
dim: dem
category: geodesy
in: 
out: points
examples: [dem_geodesy_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_geodetic_to_ecef — DEM `geodesy` op

- **データ種**: `なし` → `points`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_geodetic_to_ecef(lat_deg, lon_deg, height_m=0.0)` (実装を直接呼ぶなら `import demops; demops.dem_geodetic_to_ecef(lat_deg, lon_deg, height_m=0.0)`、台帳から引くなら `opsdem.get("dem_geodetic_to_ecef")`)

## 使い方

測地座標(緯度・経度・楕円体高)→ **地心直交座標 ECEF** [m]。

地球の中心を原点、赤道面の本初子午線方向を x、東経 90 度を y、北極を z と
する右手系。地形を「地球中心から見た座標」で扱いたいときの入口。

球ではなく **WGS84 楕円体**で計算する —— 球近似は緯度 45 度あたりで
最大 21 km ずれる(極半径が赤道半径より短いぶん)。

Args:
    lat_deg / lon_deg: 緯度・経度 [度]。配列可(同じ形)。
    height_m: 楕円体高 [m]。スカラでも配列でも可。
Returns:
    ``(..., 3)`` の ECEF 座標 [m]。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dem_geodesy_tour](../../../../examples/dem_geodesy_tour.py) — `py -3.11 examples/dem_geodesy_tour.py`

## 型が繋がる次の op(`points` を入力に取れる)

[dem_ecef_to_geodetic](dem_ecef_to_geodetic.md)

## 同カテゴリ(`geodesy`)

[dem_ecef_to_geodetic](dem_ecef_to_geodetic.md) · [dem_geocentric_grid](dem_geocentric_grid.md) · [dem_earth_curvature_drop](dem_earth_curvature_drop.md) · [dem_cell_size_webmercator](dem_cell_size_webmercator.md) · [dem_geodetic_slope](dem_geodetic_slope.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

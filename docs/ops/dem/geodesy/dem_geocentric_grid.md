---
op: dem_geocentric_grid
dim: dem
category: geodesy
in: depth
out: pointmap
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_geocentric_grid — DEM `geodesy` op

- **データ種**: `depth` → `pointmap`
- **呼び出し**: `import demops; demops.dem_geocentric_grid(dem, lat0_deg, lon0_deg, cell_size, spherical=False)` (または `opsdem.get("dem_geocentric_grid")`)

## 使い方

DEM の各セルを**地球中心から見た座標**にする。

``(H, W)`` の標高格子を、北西角が ``(lat0_deg, lon0_deg)`` にある局所平面と
みなし、各セルを ECEF(既定)または**地心球座標**へ写す。

Args:
    dem: ``(H, W)`` の標高 [m]。
    lat0_deg / lon0_deg: 格子の**北西角**の緯度経度 [度]。
    cell_size: セル寸法 [m]。緯度方向・経度方向とも同じとみなす
        (Web メルカトルのタイルはそうなっている。
        :func:`dem_cell_size_webmercator` を参照)。
    spherical: ``True`` なら ``(半径 r[m], 地心緯度[度], 経度[度])`` を返す。
        ``False``(既定)なら ECEF ``(x, y, z)`` [m]。
Returns:
    ``(H, W, 3)``。

★ **地心緯度は測地緯度ではありません**。``spherical=True`` の返りの緯度は
地球中心から見た角度で、地図の緯度(楕円体の法線が赤道面となす角)とは
最大 0.19 度違います。地図に戻すときは ECEF 側を
:func:`dem_ecef_to_geodetic` に渡してください。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`pointmap` を入力に取れる)

—

## 同カテゴリ(`geodesy`)

[dem_geodetic_to_ecef](dem_geodetic_to_ecef.md) · [dem_ecef_to_geodetic](dem_ecef_to_geodetic.md) · [dem_earth_curvature_drop](dem_earth_curvature_drop.md) · [dem_cell_size_webmercator](dem_cell_size_webmercator.md) · [dem_geodetic_slope](dem_geodetic_slope.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

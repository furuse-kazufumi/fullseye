---
op: dem_ecef_to_geodetic
dim: dem
category: geodesy
in: points
out: points
examples: [dem_geodesy_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_ecef_to_geodetic — DEM `geodesy` op

- **データ種**: `points` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_ecef_to_geodetic(xyz)` (実装を直接呼ぶなら `import demops; demops.dem_ecef_to_geodetic(xyz)`、台帳から引くなら `opsdem.get("dem_ecef_to_geodetic")`)

## 使い方

ECEF → 測地座標。返りは ``(..., 3)`` の ``(緯度[度], 経度[度], 高さ[m])``。

Bowring (1976) の閉形式に近い解法。往復(測地→ECEF→測地)の誤差は
実測で緯度・経度が 1e-12 度未満、高さが 1e-7 m 未満。

地心**球**座標が欲しいだけなら、``r = |xyz|`` と
``geocentric_lat = asin(z/r)`` で足りる —— ただしそれは**測地緯度ではない**
(両者は最大 0.19 度、距離にして約 21 km ずれる)。この op が返すのは
地図や GPS と同じ**測地**緯度のほう。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dem_geodesy_tour](../../../../examples/dem_geodesy_tour.py) — `py -3.11 examples/dem_geodesy_tour.py`

## 型が繋がる次の op(`points` を入力に取れる)

—

## 同カテゴリ(`geodesy`)

[dem_geodetic_to_ecef](dem_geodetic_to_ecef.md) · [dem_geocentric_grid](dem_geocentric_grid.md) · [dem_earth_curvature_drop](dem_earth_curvature_drop.md) · [dem_cell_size_webmercator](dem_cell_size_webmercator.md) · [dem_geodetic_slope](dem_geodetic_slope.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

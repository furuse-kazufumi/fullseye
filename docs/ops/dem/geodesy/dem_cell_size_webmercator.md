---
op: dem_cell_size_webmercator
dim: dem
category: geodesy
in: 
out: measurement
examples: [dem_geodesy_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# dem_cell_size_webmercator — DEM `geodesy` op

- **データ種**: `なし` → `measurement`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_cell_size_webmercator(zoom, lat_deg)` (実装を直接呼ぶなら `import demops; demops.dem_cell_size_webmercator(zoom, lat_deg)`、台帳から引くなら `opsdem.get("dem_cell_size_webmercator")`)

## 使い方

Web メルカトルのタイルの地上分解能 [m/px]。**緯度で変わる**。

``156543.03392804097 * cos(lat) / 2^zoom``(タイルが 256 px の場合)。

実測の目安: 東京(北緯 35.68 度)の z=15 で **3.880 m**、赤道では 4.777 m。
赤道の値をそのまま使うと東京で傾斜が **23 % 過小**になります —— これは
例外を出さずに全部の下流の数字を狂わせるので、この族で最も多い事故です。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dem_geodesy_tour](../../../../examples/dem_geodesy_tour.py) — `py -3.11 examples/dem_geodesy_tour.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`geodesy`)

[dem_geodetic_to_ecef](dem_geodetic_to_ecef.md) · [dem_ecef_to_geodetic](dem_ecef_to_geodetic.md) · [dem_geocentric_grid](dem_geocentric_grid.md) · [dem_earth_curvature_drop](dem_earth_curvature_drop.md) · [dem_geodetic_slope](dem_geodetic_slope.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

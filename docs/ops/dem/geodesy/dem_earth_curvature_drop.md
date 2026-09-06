---
op: dem_earth_curvature_drop
dim: dem
category: geodesy
in: 
out: measurement
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# dem_earth_curvature_drop — DEM `geodesy` op

- **データ種**: `なし` → `measurement`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import demops; demops.dem_earth_curvature_drop(distance_m, refraction=0.13)` (または `opsdem.get("dem_earth_curvature_drop")`)

## 使い方

見通し計算の**地球曲率落ち** [m]。``(1 - k) d^2 / (2 R)``。

遠くの地面は地球の丸みぶん下がって見え、大気屈折はそれを一部打ち消します。
標準大気(``k = 0.13``)での目安:

==========  ============  ============
距離        曲率のみ      屈折込み
==========  ============  ============
1 km        0.078 m       0.068 m
5 km        1.962 m       1.707 m
10 km       7.848 m       6.828 m
30 km       70.63 m       61.45 m
==========  ============  ============

30 km 先の見通しでは **60 m 以上**下がるので、平面として扱った可視領域は
その距離では意味を持ちません。``refraction`` は標準大気の慣行値であって
定数ではない —— 夜間の逆転層では負にも 0.25 にもなります。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`geodesy`)

[dem_geodetic_to_ecef](dem_geodetic_to_ecef.md) · [dem_ecef_to_geodetic](dem_ecef_to_geodetic.md) · [dem_geocentric_grid](dem_geocentric_grid.md) · [dem_cell_size_webmercator](dem_cell_size_webmercator.md) · [dem_geodetic_slope](dem_geodetic_slope.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

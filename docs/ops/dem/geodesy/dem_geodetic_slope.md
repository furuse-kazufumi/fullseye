---
op: dem_geodetic_slope
dim: dem
category: geodesy
in: depth
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# dem_geodetic_slope — DEM `geodesy` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import demops; demops.dem_geodetic_slope(dem, lat0_deg, d_lat_deg, d_lon_deg, method='horn', units='degrees')` (または `opsdem.get("dem_geodetic_slope")`)

## 使い方

**緯度経度の格子**(等角度間隔)の DEM の傾斜。セル寸法が緯度で変わる。

公開 DEM の多くは「1 秒メッシュ」のように**角度で等間隔**です。この格子を
そのまま :func:`dem_slope` に一定のセル寸法で渡すと、経度方向の実距離が
``cos(緯度)`` 倍だけ短いことが無視されます。緯度方向の寸法を両軸に使うと
**東西の傾斜が過小**になり(北緯 60 度で半分)、経度方向の寸法を両軸に使えば
今度は南北が過大になります。**どちらに転ぶかは何を定数にしたかで決まる**ので、
「過大/過小」を覚えるのではなく**緯度ごとに寸法を計算する**のが正解です。

★ 最初この docstring に「東西が過大になる」と書いたが、テストで測ったら
**半分になった**(過小)。符号や向きの主張は測ってから書くこと。

ここでは緯度ごとに東西のセル寸法を計算し、格子を等距離へ直してから測ります。

Args:
    dem: ``(H, W)``。行 0 が北。
    lat0_deg: **北西角**の緯度 [度]。
    d_lat_deg / d_lon_deg: 1 セルあたりの緯度・経度の刻み [度]。正の値。
    method / units: :func:`dem_slope` と同じ。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

—

## 同カテゴリ(`geodesy`)

[dem_geodetic_to_ecef](dem_geodetic_to_ecef.md) · [dem_ecef_to_geodetic](dem_ecef_to_geodetic.md) · [dem_geocentric_grid](dem_geocentric_grid.md) · [dem_earth_curvature_drop](dem_earth_curvature_drop.md) · [dem_cell_size_webmercator](dem_cell_size_webmercator.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: dem_ecef_to_geodetic
dim: dem
category: geodesy
in: points
out: points
examples: [dem_geodesy_tour, poc_geodetic_height_frames]
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
**どこを標本にしたかで 1 桁以上動く**ので、範囲つきで書く(2026-09-08 再測。
以前は「緯度・経度 1e-12 度未満、高さ 1e-7 m 未満」と書いていたが、
★これは緯度 ±85 度・高さ -500〜9000 m の 4000 点で既に **最大 6.4e-12 度 /
8.5e-07 m** と超えていた —— 中央値 2.6e-13 度 / 3.3e-08 m と混同していた):

* 緯度 ±85 度・高さ -500〜9000 m … 緯度 中央 2.6e-13 / 最大 6.4e-12 度、
  高さ 中央 3.3e-08 / 最大 8.5e-07 m
* 緯度 ±89.9 度・高さ -11 km〜40 km … 緯度 中央 2.9e-12 / 最大 1.3e-10 度、
  高さ 中央 3.5e-07 / 最大 1.7e-05 m(**極に寄せると 20 倍悪くなる**)

経度はどちらでも最大 2.8e-14 度。いずれも地上では µm 以下で、実用上は
「誤差の床」として扱ってよいが、**中央値を最大値として引用しないこと**。

地心**球**座標が欲しいだけなら、``r = |xyz|`` と
``geocentric_lat = asin(z/r)`` で足りる —— ただしそれは**測地緯度ではない**
(両者は最大 0.19 度、距離にして約 21 km ずれる)。この op が返すのは
地図や GPS と同じ**測地**緯度のほう。

★**地球の中心付近では fail-closed で拒否する**(2026-09-08、
`poc_geodetic_height_frames` が踏んだ)。楕円体の縮閉線(evolute)
``(a·p)^(2/3) + (b·|z|)^(2/3) < (a²-b²)^(2/3)`` の内側では、楕円体面から
立てた法線が 1 本に決まらず、**測地緯度がそもそも一意でない**。それまでは
ここで黙って ``lat = 180 度`` を返していた —— 緯度として存在しない値で、
しかも**自分の逆関数 :func:`dem_geodetic_to_ecef` が
「lat_deg must be within [-90, 90]」で拒否する**値だった。
領域は赤道面で軸から ``e²a = 42697.7 m``、極軸上で ``(a²-b²)/b = 42841.3 m``
まで(実測: 42600 m で 180 度、42700 m で 0 度 —— 閉形式の境界とちょうど一致)。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dem_geodesy_tour](../../../../examples/dem_geodesy_tour.py) — `py -3.11 examples/dem_geodesy_tour.py`
- [poc_geodetic_height_frames](../../../../examples/poc_geodetic_height_frames.py) — `py -3.11 examples/poc_geodetic_height_frames.py`

## 型が繋がる次の op(`points` を入力に取れる)

—

## 同カテゴリ(`geodesy`)

[dem_geodetic_to_ecef](dem_geodetic_to_ecef.md) · [dem_geocentric_grid](dem_geocentric_grid.md) · [dem_earth_curvature_drop](dem_earth_curvature_drop.md) · [dem_cell_size_webmercator](dem_cell_size_webmercator.md) · [dem_geodetic_slope](dem_geodetic_slope.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

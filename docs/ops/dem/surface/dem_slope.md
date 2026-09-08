---
op: dem_slope
dim: dem
category: surface
in: depth
out: image2d
examples: [dem_geodesy_tour, poc_crop_phenotyping, poc_dem_terrain, poc_geodetic_height_frames, poc_multibeam_bathymetry, poc_stockpile_volume]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_slope — DEM `surface` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_slope(dem, cell_size, method='horn', units='degrees')` (実装を直接呼ぶなら `import demops; demops.dem_slope(dem, cell_size, method='horn', units='degrees')`、台帳から引くなら `opsdem.get("dem_slope")`)

## 使い方

傾斜角。``units`` は ``"degrees"`` / ``"radians"`` / ``"percent"``。

平面なら閉形式 ``atan(|grad|)`` と一致する(実測 1e-13 以下)。

手順: 3x3 近傍から ``dz/dx``(東向き)と ``dz/dy``(北向き = 行が減る向き)を
取り、``g = hypot(dz/dx, dz/dy)``。``"degrees"`` は ``atan(g)`` を度で、
``"radians"`` はラジアン、``"percent"`` は ``100 g``(45 度 = 100 %)。
縁は端の値を複製して埋める(``pad mode="edge"``)ので、外周 1 セルは内側より
緩めに出る。

- ``dem``: ``(H, W)`` の標高 [m]、3x3 以上、実数、``inf`` 不可。欠測は ``nan`` で
  渡す ―― ``-9999`` のような番兵値がそのまま入っている(``<= -9000`` があり
  ``nan`` が無い)と拒否する。``nan`` は 3x3 の範囲に伝播する。
- ``cell_size``: セル辺長 [m]、正の有限値。bool / 文字列は拒否。緯度経度格子は
  先に ``dem_geodetic_slope`` 側を使う。
- ``method``: ``"horn"``(Horn 1981 の 3x3 重み付き差分、既定)/ ``"central"``
  (Zevenbergen–Thorne の中央差分)。
- 返り値: ``(H, W)`` float64。``degrees`` は ``[0, 90)``。
- 失敗はすべて ``ValueError``(形・番兵値・``cell_size``・選択肢)。

``dem_aspect`` と対で使う。``dem_hillshade`` はこの 2 つから陰影を作る。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dem_geodesy_tour](../../../../examples/dem_geodesy_tour.py) — `py -3.11 examples/dem_geodesy_tour.py`
- [poc_crop_phenotyping](../../../../examples/poc_crop_phenotyping.py) — `py -3.11 examples/poc_crop_phenotyping.py`
- [poc_dem_terrain](../../../../examples/poc_dem_terrain.py) — `py -3.11 examples/poc_dem_terrain.py`
- [poc_geodetic_height_frames](../../../../examples/poc_geodetic_height_frames.py) — `py -3.11 examples/poc_geodetic_height_frames.py`
- [poc_multibeam_bathymetry](../../../../examples/poc_multibeam_bathymetry.py) — `py -3.11 examples/poc_multibeam_bathymetry.py`
- [poc_stockpile_volume](../../../../examples/poc_stockpile_volume.py) — `py -3.11 examples/poc_stockpile_volume.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

—

## 同カテゴリ(`surface`)

[dem_aspect](dem_aspect.md) · [dem_curvature](dem_curvature.md) · [dem_roughness](dem_roughness.md) · [dem_tpi](dem_tpi.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

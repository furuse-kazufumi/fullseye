---
op: dem_datum_shift_3param
dim: dem
category: geodesy
in: 
out: points
examples: [poc_geodetic_benchmarks_real, poc_geodetic_height_frames]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# dem_datum_shift_3param — DEM `geodesy` op

- **データ種**: `なし` → `points`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_datum_shift_3param(lat_deg, lon_deg, h_m, dx_m, dy_m, dz_m, a_from_m, f_from, a_to_m, f_to)` (実装を直接呼ぶなら `import demops; demops.dem_datum_shift_3param(lat_deg, lon_deg, h_m, dx_m, dy_m, dz_m, a_from_m, f_from, a_to_m, f_to)`、台帳から引くなら `opsdem.get("dem_datum_shift_3param")`)

## 使い方

測地成果(datum)の乗り換え —— 地心 3 パラメータの平行移動(``points``)。

同じ「北緯 35 度 41 分」でも、旧日本測地系と世界測地系では**地上で数百メートル**
離れた点を指す。この op はその乗り換えを、地心直交座標での平行移動
(``Molodensky-Badekas`` の回転・縮尺なしの場合)として行う::

    ECEF(a_from, f_from) + (dx, dy, dz) -> 測地座標(a_to, f_to)

★**パラメータに既定値を置かない**。どの成果からどの成果へ、どの平行移動量で
移すのかは国・地域・版で違い、黙って仮定すると「例外は出ないが数百メートル
ずれた座標」が出る —— それがこの op の存在理由なので、呼び手に必ず書かせる。

Args:
    lat_deg / lon_deg: 元の成果での緯度・経度 [度]。配列可。
    h_m: 元の成果での楕円体高 [m]。
    dx_m / dy_m / dz_m: 地心の平行移動量 [m] (元 → 先)。
    a_from_m / f_from: 元の楕円体の長半径 [m] と扁平率。
    a_to_m / f_to: 先の楕円体の長半径 [m] と扁平率。
Returns:
    ``(n, 3)`` の ``(緯度[度], 経度[度], 楕円体高[m])``。

閉じた式で検査できること: 平行移動 0 かつ同じ楕円体なら**恒等変換**
(往復の床は ``dem_ecef_to_geodetic`` と同じ)。平行移動だけを与えたときの
地上の移動量は、その点の ECEF 基底で分解した成分と一致する。

**ValueError**: 非有限、緯度が ±90 を外れる、長半径が非正、扁平率が [0, 1) を外れる。

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

[dem_ecef_to_geodetic](dem_ecef_to_geodetic.md) · [dem_geodetic_from_enu](dem_geodetic_from_enu.md)

## 同カテゴリ(`geodesy`)

[dem_geodetic_to_ecef](dem_geodetic_to_ecef.md) · [dem_ecef_to_geodetic](dem_ecef_to_geodetic.md) · [dem_geocentric_grid](dem_geocentric_grid.md) · [dem_earth_curvature_drop](dem_earth_curvature_drop.md) · [dem_cell_size_webmercator](dem_cell_size_webmercator.md) · [dem_geodetic_slope](dem_geodetic_slope.md) · [dem_geoid_height](dem_geoid_height.md) · [dem_height_frame_convert](dem_height_frame_convert.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

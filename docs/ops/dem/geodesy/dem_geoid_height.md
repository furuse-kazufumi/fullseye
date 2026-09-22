---
op: dem_geoid_height
dim: dem
category: geodesy
in: depth
out: signal
examples: [poc_geodetic_benchmarks_real, poc_geodetic_height_frames]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# dem_geoid_height — DEM `geodesy` op

- **データ種**: `depth` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_geoid_height(geoid, lat_deg, lon_deg, lat0_deg, lon0_deg, d_lat_deg, d_lon_deg)` (実装を直接呼ぶなら `import demops; demops.dem_geoid_height(geoid, lat_deg, lon_deg, lat0_deg, lon0_deg, d_lat_deg, d_lon_deg)`、台帳から引くなら `opsdem.get("dem_geoid_height")`)

## 使い方

ジオイド高の格子を緯度・経度で**双一次補間**して ``N`` [m] を返す(``signal``)。

GNSS が返すのは楕円体高 ``h``、地図と設計図が使うのは標高 ``H``。その差が
ジオイド高 ``N``(``H = h - N``)で、日本付近では概ね **+30〜+40 m** ある。
この op は公開されているジオイドモデルの格子(GSIGEO / EGM 系のような
等間隔グリッド)を読む側の道具で、**モデルそのものは持たない** —— どの版を
使ったかは呼び手の責任であり、版が変われば標高は数 cm 動く。

Args:
    geoid: ``(H, W)`` のジオイド高 [m]。``geoid[0, 0]`` が
        ``(lat0_deg, lon0_deg)``、行が増えると緯度が ``d_lat_deg`` 増え、
        列が増えると経度が ``d_lon_deg`` 増える(どちらの符号でもよい)。
    lat_deg / lon_deg: 引きたい点の緯度・経度 [度]。配列可。
    lat0_deg / lon0_deg: 格子の原点 [度]。
    d_lat_deg / d_lon_deg: 格子の刻み [度]。0 は拒否する。
Returns:
    ``(n,)`` のジオイド高 [m]。

閉じた式で検査できること: ``N`` が緯度・経度の **1 次式**であるような格子に
対しては、双一次補間は**厳密**(機械精度)。2 次の項があるときの誤差は
``|∂²N| * d² / 8`` で上から押さえられる。

**ValueError**: 格子が 2-D でない / 2x2 未満 / 非有限、刻みが 0 か非有限、
緯度が ±90 を外れる、そして**格子の外の点**(海域や範囲外を黙って端の値で
埋めない —— 外挿したジオイド高は測量値ではない)。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_geodetic_benchmarks_real](../../../../examples/poc_geodetic_benchmarks_real.py) — `py -3.11 examples/poc_geodetic_benchmarks_real.py`
- [poc_geodetic_height_frames](../../../../examples/poc_geodetic_height_frames.py) — `py -3.11 examples/poc_geodetic_height_frames.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[dem_height_frame_convert](dem_height_frame_convert.md) · [dem_height_frame_residual](dem_height_frame_residual.md)

## 同カテゴリ(`geodesy`)

[dem_geodetic_to_ecef](dem_geodetic_to_ecef.md) · [dem_ecef_to_geodetic](dem_ecef_to_geodetic.md) · [dem_geocentric_grid](dem_geocentric_grid.md) · [dem_earth_curvature_drop](dem_earth_curvature_drop.md) · [dem_cell_size_webmercator](dem_cell_size_webmercator.md) · [dem_geodetic_slope](dem_geodetic_slope.md) · [dem_height_frame_convert](dem_height_frame_convert.md) · [dem_height_frame_residual](dem_height_frame_residual.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

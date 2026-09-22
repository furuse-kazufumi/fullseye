---
op: dem_height_frame_convert
dim: dem
category: geodesy
in: signal × signal
out: signal
examples: [poc_geodetic_benchmarks_real]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# dem_height_frame_convert — DEM `geodesy` op

- **データ種**: `signal × signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_height_frame_convert(height_m, geoid_height_m, frm='ellipsoidal', to='orthometric')` (実装を直接呼ぶなら `import demops; demops.dem_height_frame_convert(height_m, geoid_height_m, frm='ellipsoidal', to='orthometric')`、台帳から引くなら `opsdem.get("dem_height_frame_convert")`)

## 使い方

高さの**基準**を移す: 楕円体高 ``h`` ↔ 標高 ``H``(``H = h - N``)。``signal``。

同じ「高さ」という語で 2 つの別物が流通していて、どちらも例外を出さずに
地図に載る。この op は**どちらからどちらへ移すのかを必ず書かせる** ——
既定はあるが、``frm`` と ``to`` は docstring でなくコードに残る。

Args:
    height_m: 高さ [m]。配列可。
    geoid_height_m: 同じ点のジオイド高 ``N`` [m] —— :func:`dem_geoid_height` で引いた値。
        スカラでも配列でもよい。
    frm / to: ``"ellipsoidal"``(楕円体高)か ``"orthometric"``(標高)。
Returns:
    ``(n,)`` の変換後の高さ [m]。``frm == to`` なら値は変わらない。

閉じた式で検査できること: ``H = h - N`` は定義そのものなので真値は引き算で出る。
往復(h→H→h)の誤差は**実測で 5e-13 m 以下**(5,000 点、高さ −100〜4000 m・
``N`` ±100 m)。ビット一致ではない —— ``(h - N) + N`` は丸めで 1 ulp 動くことが
あり、実測では 5,000 点中 273 点がそうなった。**「往復で元に戻る」を等号で
書かない**のはそのため。

**ValueError**: 未知の基準名、長さの食い違い、非有限。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_geodetic_benchmarks_real](../../../../examples/poc_geodetic_benchmarks_real.py) — `py -3.11 examples/poc_geodetic_benchmarks_real.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[dem_height_frame_residual](dem_height_frame_residual.md)

## 同カテゴリ(`geodesy`)

[dem_geodetic_to_ecef](dem_geodetic_to_ecef.md) · [dem_ecef_to_geodetic](dem_ecef_to_geodetic.md) · [dem_geocentric_grid](dem_geocentric_grid.md) · [dem_earth_curvature_drop](dem_earth_curvature_drop.md) · [dem_cell_size_webmercator](dem_cell_size_webmercator.md) · [dem_geodetic_slope](dem_geodetic_slope.md) · [dem_geoid_height](dem_geoid_height.md) · [dem_height_frame_residual](dem_height_frame_residual.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

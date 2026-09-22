---
op: dem_height_frame_residual
dim: dem
category: geodesy
in: signal × signal × signal
out: table
examples: [poc_geodetic_benchmarks_real]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# dem_height_frame_residual — DEM `geodesy` op

- **データ種**: `signal × signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_height_frame_residual(h_ellipsoidal_m, h_orthometric_m, geoid_height_m, tol_m=0.1)` (実装を直接呼ぶなら `import demops; demops.dem_height_frame_residual(h_ellipsoidal_m, h_orthometric_m, geoid_height_m, tol_m=0.1)`、台帳から引くなら `opsdem.get("dem_height_frame_residual")`)

## 使い方

``h - H - N`` の残差 —— 高さの取り違えを**静かにさせない**検出器(``table``)。

楕円体高・標高・ジオイド高は 1 つの恒等式で結ばれている(``h = H + N``)。
3 つそろった点でその残差を測れば、**どれかが別の基準・別のモデル・別の版で
作られている**ことが数値で出る。測量成果どうしなら残差は cm 級に収まり、
楕円体高をそのまま標高として使っていれば残差は ``-N``(日本付近で −30〜−40 m)
に張り付く。

Args:
    h_ellipsoidal_m: 楕円体高 [m] (GNSS の返り)。配列可。
    h_orthometric_m: 同じ点の標高 [m] (地図・水準測量)。
    geoid_height_m: 同じ点のジオイド高 [m]。
    tol_m: 「合っている」とみなす閾値 [m]。既定 0.10 m。
Returns:
    ``{"residual_m": (n,), "rms_m", "max_abs_m", "median_m", "n",
    "n_over_tol", "tol_m", "fraction_over_tol"}``。

閉じた式で検査できること: 恒等式どおりに作った 3 つ組では残差は 0 になる
(実測 rms 1.2e-14 m。丸めの分だけ厳密な 0 ではない)。標高の列に楕円体高を
そのまま入れると残差は **−N** に張り付く —— 取り違えの量がそのまま出る。

**ValueError**: 長さの食い違い、非有限、負の *tol_m*。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_geodetic_benchmarks_real](../../../../examples/poc_geodetic_benchmarks_real.py) — `py -3.11 examples/poc_geodetic_benchmarks_real.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`geodesy`)

[dem_geodetic_to_ecef](dem_geodetic_to_ecef.md) · [dem_ecef_to_geodetic](dem_ecef_to_geodetic.md) · [dem_geocentric_grid](dem_geocentric_grid.md) · [dem_earth_curvature_drop](dem_earth_curvature_drop.md) · [dem_cell_size_webmercator](dem_cell_size_webmercator.md) · [dem_geodetic_slope](dem_geodetic_slope.md) · [dem_geoid_height](dem_geoid_height.md) · [dem_height_frame_convert](dem_height_frame_convert.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

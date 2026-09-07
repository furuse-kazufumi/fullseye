---
op: dem_sky_view_factor
dim: dem
category: visibility
in: depth
out: image2d
examples: [poc_dem_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_sky_view_factor — DEM `visibility` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_sky_view_factor(dem, cell_size, n_azimuth=16, max_distance_m=None)` (実装を直接呼ぶなら `import demops; demops.dem_sky_view_factor(dem, cell_size, n_azimuth=16, max_distance_m=None)`、台帳から引くなら `opsdem.get("dem_sky_view_factor")`)

## 使い方

天空率 [0,1]。空がどれだけ見えているか。

``n_azimuth`` 方位の地平線仰角から ``mean(cos^2(horizon))`` で求める
(等方輝度の空を仮定した標準的な近似)。**平坦面では厳密に 1**。
都市の暑熱や谷底の冷え込みで効く量。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dem_terrain](../../../../examples/poc_dem_terrain.py) — `py -3.11 examples/poc_dem_terrain.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

—

## 同カテゴリ(`visibility`)

[dem_horizon_angle](dem_horizon_angle.md) · [dem_viewshed](dem_viewshed.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

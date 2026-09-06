---
op: dem_roughness
dim: dem
category: surface
in: depth
out: image2d
examples: [dem_terrain_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_roughness — DEM `surface` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import demops; demops.dem_roughness(dem, cell_size=1.0)` (または `opsdem.get("dem_roughness")`)

## 使い方

地形起伏指数 TRI —— 8 近傍との標高差の二乗平均平方根 [m]。

Riley ほか (1999)。``cell_size`` は結果に影響しないが、**単位が m である
ことを呼び出し側に意識させる**ために受け取る(検証もする)。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [dem_terrain_analysis_tour](../../../../examples/dem_terrain_analysis_tour.py) — `py -3.11 examples/dem_terrain_analysis_tour.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

—

## 同カテゴリ(`surface`)

[dem_slope](dem_slope.md) · [dem_aspect](dem_aspect.md) · [dem_curvature](dem_curvature.md) · [dem_tpi](dem_tpi.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

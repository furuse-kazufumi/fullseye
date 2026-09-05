---
op: dem_curvature
dim: dem
category: surface
in: depth
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# dem_curvature — DEM `surface` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import demops; demops.dem_curvature(dem, cell_size, kind='profile')` (または `opsdem.get("dem_curvature")`)

## 使い方

曲率 [1/m]。``kind`` は ``"profile"``(断面) / ``"planform"``(平面) / ``"total"``。

Zevenbergen & Thorne (1987) の 2 次曲面当てはめ。断面曲率は流下方向の
凹凸(加速・減速)、平面曲率は等高線の曲がり(集中・発散)を表す。

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

## 同カテゴリ(`surface`)

[dem_slope](dem_slope.md) · [dem_aspect](dem_aspect.md) · [dem_roughness](dem_roughness.md) · [dem_tpi](dem_tpi.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

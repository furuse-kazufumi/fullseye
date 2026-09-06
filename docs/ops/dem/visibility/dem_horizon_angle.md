---
op: dem_horizon_angle
dim: dem
category: visibility
in: depth
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_horizon_angle — DEM `visibility` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import demops; demops.dem_horizon_angle(dem, cell_size, azimuth_deg, max_distance_m=None)` (または `opsdem.get("dem_horizon_angle")`)

## 使い方

指定方位の地平線仰角 [度]。0 は水平、90 は真上が塞がれている状態。

各セルから ``azimuth_deg`` の向きへ視線を進め、``atan((z_j - z_0)/d)`` の
最大値を返す。落ちる影・日照時間・天空率の下ごしらえになる。

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

## 同カテゴリ(`visibility`)

[dem_sky_view_factor](dem_sky_view_factor.md) · [dem_viewshed](dem_viewshed.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

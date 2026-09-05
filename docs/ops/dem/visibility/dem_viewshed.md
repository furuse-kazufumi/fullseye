---
op: dem_viewshed
dim: dem
category: visibility
in: depth
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# dem_viewshed — DEM `visibility` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import demops; demops.dem_viewshed(dem, cell_size, observer_rc, observer_height_m=1.7, target_height_m=0.0, max_distance_m=None)` (または `opsdem.get("dem_viewshed")`)

## 使い方

1 点からの可視領域(1 = 見える)。視線が地形に遮られるかを判定する。

``observer_rc`` は ``(row, col)``。観測点自身は常に可視。

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

[dem_horizon_angle](dem_horizon_angle.md) · [dem_sky_view_factor](dem_sky_view_factor.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

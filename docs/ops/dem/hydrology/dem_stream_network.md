---
op: dem_stream_network
dim: dem
category: hydrology
in: depth
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# dem_stream_network — DEM `hydrology` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import demops; demops.dem_stream_network(dem, cell_size, threshold_cells=100.0, fill=True, nodata='error')` (または `opsdem.get("dem_stream_network")`)

## 使い方

集水量が閾値を超えたセルを河道とみなす二値マスク。

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

## 同カテゴリ(`hydrology`)

[dem_fill_sinks](dem_fill_sinks.md) · [dem_flow_direction](dem_flow_direction.md) · [dem_flow_accumulation](dem_flow_accumulation.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

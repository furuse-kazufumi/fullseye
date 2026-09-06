---
op: dem_flow_direction
dim: dem
category: hydrology
in: depth
out: labels
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_flow_direction — DEM `hydrology` op

- **データ種**: `depth` → `labels`
- **呼び出し**: `import demops; demops.dem_flow_direction(dem, cell_size, nodata='error')` (または `opsdem.get("dem_flow_direction")`)

## 使い方

D8 流向。O'Callaghan & Mark (1984)。

返り値は ``(H, W)`` の整数で、0-7 が :data:`_D8` の並び、``-1`` が
「流出先なし」(周囲より低い = 窪地、または境界外へ出る)。

``nodata="outlet"`` なら、欠測セルへ向かう流れを**許す**(そこで系を出る)。
``"barrier"`` なら欠測へは流れない。欠測セル自身は常に ``-1``。

## 詳しい使い方ガイド

- [dem_terrain_analysis ファミリ ガイド](../guides/dem_terrain_analysis.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`labels` を入力に取れる)

—

## 同カテゴリ(`hydrology`)

[dem_fill_sinks](dem_fill_sinks.md) · [dem_flow_accumulation](dem_flow_accumulation.md) · [dem_stream_network](dem_stream_network.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

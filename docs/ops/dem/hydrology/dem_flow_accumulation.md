---
op: dem_flow_accumulation
dim: dem
category: hydrology
in: depth
out: image2d
examples: [poc_dem_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_flow_accumulation — DEM `hydrology` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import demops; demops.dem_flow_accumulation(dem, cell_size, fill=True, epsilon=1e-06, nodata='error')` (または `opsdem.get("dem_flow_accumulation")`)

## 使い方

集水セル数。各セルへ流れ込む上流セルの個数(自セルを 1 と数える)。

``fill=True`` なら先に窪地を埋める(埋めないと窪地で流れが止まり、
下流の集水量が**静かに小さく出る**)。欠測セルの集水量は ``nan``。

グラフの構築はベクトル化してある。ただし**効果は小さい**: 1024x1024 で
2.71 秒 -> 2.39 秒。支配しているのは構築ではなく、そのあとのトポロジカル
走査(セル数ぶんの Python ループ)のほうだった。速くしたいならそこを
書き換える必要がある —— 直したつもりで直っていない、を残さないため明記する。

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

## 同カテゴリ(`hydrology`)

[dem_fill_sinks](dem_fill_sinks.md) · [dem_flow_direction](dem_flow_direction.md) · [dem_stream_network](dem_stream_network.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

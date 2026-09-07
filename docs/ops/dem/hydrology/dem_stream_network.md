---
op: dem_stream_network
dim: dem
category: hydrology
in: depth
out: image2d
examples: [dem_terrain_analysis_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# dem_stream_network — DEM `hydrology` op

- **データ種**: `depth` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.dem_stream_network(dem, cell_size, threshold_cells=100.0, fill=True, nodata='error')` (実装を直接呼ぶなら `import demops; demops.dem_stream_network(dem, cell_size, threshold_cells=100.0, fill=True, nodata='error')`、台帳から引くなら `opsdem.get("dem_stream_network")`)

## 使い方

集水量が閾値を超えたセルを河道とみなす二値マスク。

手順: ``dem_flow_accumulation(dem, cell_size, fill, nodata)`` で各セルの集水
セル数(自セルを 1 と数える)を取り、``acc >= threshold_cells`` を 1、それ以外を 0
にする。欠測セルは ``nan`` のまま。

- ``threshold_cells``: 河道とみなす集水セル数。正の有限値(``ValueError``)。
  面積で決めたいなら ``面積 [m^2] / cell_size^2`` に換算して渡す(この op は
  セル数しか受けない)。
- ``fill=True``(既定): 先に priority-flood(``dem_fill_sinks``、``epsilon=1e-6``)で
  窪地を埋める。埋めないと窪地で流れが止まり、下流の集水量が小さく出て河道が
  途切れる。
- ``nodata``: ``"error"``(既定、``nan`` があれば拒否)/ ``"outlet"``(欠測 = 流出口、
  水域向き)/ ``"barrier"``(欠測 = 壁)。定数で穴埋めする選択肢は無い。
- ``dem`` / ``cell_size`` の契約は ``dem_slope`` と同じ(3x3 以上、番兵値拒否、[m])。
- 返り値: ``(H, W)`` float64 の 0 / 1(欠測は ``nan``)。bool ではないので
  ``blob_label`` 等に渡すなら ``== 1`` で二値化する。
- 計算量: 集水量のトポロジカル走査がセル数ぶんの Python ループ。

D8 流向(``dem_flow_direction``)に基づくので、平坦な埋立地では流れが一箇所に
集まりやすい ―― 閾値を下げすぎると格子状の偽河道が出る。

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

## 同カテゴリ(`hydrology`)

[dem_fill_sinks](dem_fill_sinks.md) · [dem_flow_direction](dem_flow_direction.md) · [dem_flow_accumulation](dem_flow_accumulation.md)

---
*Provenance: demops.py — DEM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

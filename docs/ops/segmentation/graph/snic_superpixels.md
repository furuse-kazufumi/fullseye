---
op: snic_superpixels
dim: segmentation
category: graph
in: image2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# snic_superpixels — SEGMENTATION `graph` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.snic_superpixels(image, *, n_segments: 'int' = 100, compactness: 'float' = 0.1, connectivity: 'int' = 4) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.snic_superpixels(image, *, n_segments: 'int' = 100, compactness: 'float' = 0.1, connectivity: 'int' = 4) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("snic_superpixels")`)

## 使い方

SNIC(Achanta–Süsstrunk 2017 の Algorithm 1): 格子の種から優先度つき待ち行列で育てる非反復の超画素。

距離 d² = |Δx|²/s² + |Δc|²/m²(s = √(N/K)、m = ``compactness``、c は画素の値。SLIC の正規化の形、式 (1) の表記は要確認)。
待ち行列から最小の d を取り出し、未ラベルならラベルを付け、重心(位置と値)をその場で更新し、未ラベルの近傍を今の重心との
距離で積む。同点は (距離, 積んだ順) で決める(決定的)。
返す: ``labels``(1..K)、``n_segments``、``all_connected``(全ラベルが 4-連結 = 構成上の保証を数えて確かめた印)、
``n_disconnected``、``sizes``、``seeds``((K, 2) の [row, col])、``s``。

## 詳しい使い方ガイド

- [halcon_segmentation ファミリ ガイド](../guides/halcon_segmentation.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [graph_hierarchy_and_thresholds](../guides/graph_hierarchy_and_thresholds.md) — グラフ・階層・閾値の定理でつくる分割 — 何が厳密で、どこで割れ方が倒れるか

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_graph_hierarchy_segmentation](../../../../examples/poc_graph_hierarchy_segmentation.py) — `py -3.11 examples/poc_graph_hierarchy_segmentation.py`

## 型が繋がる次の op(`table` を入力に取れる)

[class_ndim_norm](../classify/class_ndim_norm.md)

## 同カテゴリ(`graph`)

[graph_cut_binary](graph_cut_binary.md) · [alpha_expansion](alpha_expansion.md) · [statistical_region_merging](statistical_region_merging.md) · [max_tree](max_tree.md) · [area_opening_attr](area_opening_attr.md) · [quasi_flat_zones](quasi_flat_zones.md) · [alpha_tree](alpha_tree.md) · [hierarchical_watershed](hierarchical_watershed.md)

---
*Provenance: seggraph.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: ultrametric_contour_map
dim: segmentation
category: graph
in: image2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# ultrametric_contour_map — SEGMENTATION `graph` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ultrametric_contour_map(image, *, mask=None, connectivity: 'int' = 4, distance_matrix: 'bool' = False) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.ultrametric_contour_map(image, *, mask=None, connectivity: 'int' = 4, distance_matrix: 'bool' = False) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("ultrametric_contour_map")`)

## 使い方

dynamics の階層の ultrametric contour map(UCM): 隣り合う画素 p, q の値 = 「p と q が同じ領域になる最小の閾値」。

盆地の中の辺は 0、盆地の境の辺は第 2 の Kruskal(盆地の木を saliency の昇順に併合)で 2 つの盆地が出会う高さ。
返す: ``ucm_h``(H, W − 1:画素とその右)、``ucm_v``(H − 1, W:画素とその下)、``ucm``(画素ごとに右と下の大きい方 =
境界を左上の画素で代表、segeval と同じ)、``basins``、``levels``、``distance``(``distance_matrix=True`` かつ盆地が
2500 以下なら盆地の全組の ultrametric 距離の行列)。閾値 θ で ucm > θ の辺を切った成分 = hierarchical_watershed(θ)。

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

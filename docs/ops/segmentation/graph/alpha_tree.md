---
op: alpha_tree
dim: segmentation
category: graph
in: image2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# alpha_tree — SEGMENTATION `graph` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.alpha_tree(image, alphas: 'Sequence[float]' = (0.0,), *, connectivity: 'int' = 4) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.alpha_tree(image, alphas: 'Sequence[float]' = (0.0,), *, connectivity: 'int' = 4) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("alpha_tree")`)

## 使い方

α-tree: 隣の差を重みにした格子の最小全域木(scipy の Kruskal)を作り、重み ≤ α の木の辺だけで α ごとの分割を出す。

scipy は重み 0 の辺を「辺が無い」と読むので、重み 0 の辺だけを「正の重みの最小の半分」に置き換えてから木を作る
(辺の順序は変わらない = 最小全域木は同じ)。**全辺に 1 を足す手は使わない**: 0.3 の差が浮動小数で 0.29999999999999993 と
0.30000000000000004 に割れている時、+1 の丸めで 2 つが同点になり、木が重い方を選んで α = 0.3 の切断がずれた(実測、
テスト test_quasi_flat_zones_equal_mst_cut)。木の辺の重みは添字から |f_p − f_q| を計算し直す。
返す: ``labels``(α ごとの (H, W) を積んだ (A, H, W))、``n_zones``、``mst_i`` / ``mst_j`` / ``mst_w``、``merge_levels``
(木の辺の重みの昇順 = 併合の高さ)、``nested``(α の昇順で入れ子か)。

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

[graph_cut_binary](graph_cut_binary.md) · [alpha_expansion](alpha_expansion.md) · [statistical_region_merging](statistical_region_merging.md) · [max_tree](max_tree.md) · [area_opening_attr](area_opening_attr.md) · [quasi_flat_zones](quasi_flat_zones.md) · [hierarchical_watershed](hierarchical_watershed.md) · [ultrametric_contour_map](ultrametric_contour_map.md)

---
*Provenance: seggraph.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

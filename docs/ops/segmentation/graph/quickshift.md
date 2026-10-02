---
op: quickshift
dim: segmentation
category: graph
in: image2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# quickshift — SEGMENTATION `graph` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.quickshift(image, *, kernel_size: 'float' = 3.0, max_dist: 'float' = 6.0, ratio: 'float' = 1.0, search_radius: 'int' = 10) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.quickshift(image, *, kernel_size: 'float' = 3.0, max_dist: 'float' = 6.0, ratio: 'float' = 1.0, search_radius: 'int' = 10) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("quickshift")`)

## 使い方

quick shift(Vedaldi–Soatto 2008): 特徴 (y, x, ratio · I) で Parzen 密度 P_i = Σ_j exp(−D_ij²/(2σ²))(窓 3σ、σ =
``kernel_size``)を見積もり、各画素を「密度が上の点のうち最も近い点」(半径 ``search_radius`` の窓の中)に繋ぎ、
長さ > ``max_dist`` の枝を切った木の成分を領域にする。

密度の同点は画素番号で決める(乱数なし)。木は ``max_dist`` に依らない(search_radius を固定すれば)ので、
max_dist を増やした分割は入れ子になる(切る枝が減るだけ)。返す: ``labels``(1..k)、``n_segments``、``parent``
(平らな添字、根は自分)、``link``(親までの距離、根は inf)、``density``。

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

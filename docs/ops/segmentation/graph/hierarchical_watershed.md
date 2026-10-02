---
op: hierarchical_watershed
dim: segmentation
category: graph
in: image2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# hierarchical_watershed — SEGMENTATION `graph` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.hierarchical_watershed(image, *, threshold: 'float' = 0.0, n_regions: 'Optional[int]' = None, mask=None, connectivity: 'int' = 4) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.hierarchical_watershed(image, *, threshold: 'float' = 0.0, n_regions: 'Optional[int]' = None, mask=None, connectivity: 'int' = 4) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("hierarchical_watershed")`)

## 使い方

dynamics による階層分水嶺: 地形 ``image``(低い所が盆地)の最小全域森の辺に dynamics の saliency を付け、
saliency ≤ ``threshold`` の辺で結んだ成分を返す(``n_regions`` を与えたら、その数になる最小の閾値を使う)。

``mask`` を与えるとその中だけで(外は 0)。返す: ``labels``(1..k)、``n_regions``、``basins``(閾値 0 の分割 = 分水嶺の
盆地)、``n_basins``、``dynamics``(盆地ごと、各連結成分で最も深い盆地は inf)、``levels``(盆地が消える高さの昇順)、
``threshold``(実際に使った値)。盆地の数 = dynamics > 閾値 の盆地の数(この関数が数えて返す ``n_expected``)。

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

[graph_cut_binary](graph_cut_binary.md) · [alpha_expansion](alpha_expansion.md) · [statistical_region_merging](statistical_region_merging.md) · [max_tree](max_tree.md) · [area_opening_attr](area_opening_attr.md) · [quasi_flat_zones](quasi_flat_zones.md) · [alpha_tree](alpha_tree.md) · [ultrametric_contour_map](ultrametric_contour_map.md)

---
*Provenance: seggraph.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

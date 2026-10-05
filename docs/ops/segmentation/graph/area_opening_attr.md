---
op: area_opening_attr
dim: segmentation
category: graph
in: image2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# area_opening_attr — SEGMENTATION `graph` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.area_opening_attr(image, threshold: 'float' = 16.0, *, attribute: 'str' = 'area', connectivity: 'int' = 4) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.area_opening_attr(image, threshold: 'float' = 16.0, *, attribute: 'str' = 'area', connectivity: 'int' = 4) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("area_opening_attr")`)

## 使い方

属性開放(Salembier ら 1998): 成分木の節のうち属性 < ``threshold`` を消し、各画素を「属性 ≥ 閾値の最も近い祖先」の値にする。

``attribute`` = ``"area"``(画素数、skimage の area_opening と同じ「面積が閾値未満の明るい構造を消す」)か ``"diameter"``
(外接矩形の長い辺、skimage の diameter_opening)。どちらも **2 値の集合の** 増加する属性なので、結果は代数的開放 =
冪等・反拡大・増加。成分の中の最大値に依る「高さ」は集合の属性でなく(h-maxima と同じく)冪等にならないので載せない
(実測で 2 回目に値が変わった)。
返す: ``image``(開放の結果)、``n_nodes_kept`` / ``n_nodes``、``removed``(値が下がった画素の数)。

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

[graph_cut_binary](graph_cut_binary.md) · [alpha_expansion](alpha_expansion.md) · [statistical_region_merging](statistical_region_merging.md) · [max_tree](max_tree.md) · [quasi_flat_zones](quasi_flat_zones.md) · [alpha_tree](alpha_tree.md) · [hierarchical_watershed](hierarchical_watershed.md) · [ultrametric_contour_map](ultrametric_contour_map.md)

---
*Provenance: seggraph.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

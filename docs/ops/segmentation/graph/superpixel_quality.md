---
op: superpixel_quality
dim: segmentation
category: graph
in: labels2d × labels2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# superpixel_quality — SEGMENTATION `graph` op

- **データ種**: `labels2d × labels2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.superpixel_quality(labels_sp, labels_true, *, tau: 'float' = 2.0) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.superpixel_quality(labels_sp, labels_true, *, tau: 'float' = 2.0) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("superpixel_quality")`)

## 使い方

超画素の採点: 境界の再現率(``segeval.seg_boundary_f`` の recall、許容 τ)、補正つき未分割誤差 CUSE =
(1/N) Σ_k |S_k − G_max(S_k)|(Neubert–Protzel 2012、SNIC 論文の式 (2))、ASA = 1 − CUSE、Neubert–Protzel の未分割誤差
UE = (1/N) Σ_G Σ_(S∩G≠∅) min(|S∩G|, |S − G|)、超画素の数。真値の 0 も 1 つの領域として数える(背景も被覆の対象)。

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

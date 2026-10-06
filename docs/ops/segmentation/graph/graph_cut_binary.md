---
op: graph_cut_binary
dim: segmentation
category: graph
in: image2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# graph_cut_binary — SEGMENTATION `graph` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_cut_binary(image, *, lam: 'float' = 1.0, mu_bg: 'Optional[float]' = None, mu_fg: 'Optional[float]' = None, contrast_sigma: 'Optional[float]' = None, seeds=None, connectivity: 'int' = 4) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.graph_cut_binary(image, *, lam: 'float' = 1.0, mu_bg: 'Optional[float]' = None, mu_fg: 'Optional[float]' = None, contrast_sigma: 'Optional[float]' = None, seeds=None, connectivity: 'int' = 4) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("graph_cut_binary")`)

## 使い方

2 値の graph cut(Boykov–Jolly 2001): E = Σ_p D_p(x_p) + λ Σ w_pq [x_p ≠ x_q] を最大フロー / 最小カットで厳密に最小化。

データ項は D_p(0) = (I_p − μ_bg)²、D_p(1) = (I_p − μ_fg)²(μ を省くと isodata の 2 群の平均)。辺の重みは
w_pq = exp(−(I_p − I_q)²/(2σ²)) / dist(p, q)(``contrast_sigma`` = σ、省くと 1/dist = Potts)。``seeds`` は labels2d で
1 = 背景の種、2 = 物体の種(Boykov–Jolly の K = 1 + max_p Σ_q λ w_pq で硬く縛る、エネルギーには数えない)。
返す: ``mask``(物体 = True)、``energy`` = data + smooth、``cut_value`` / ``flow_value``(実数に戻した値 = 整数の値 / scale +
定数)と ``cut_value_int`` / ``flow_value_int``(最大フロー = 最小カットの門)、``quantization_bound``(整数化による実数の
最小との差の上界、整数の入力なら 0)。

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

[alpha_expansion](alpha_expansion.md) · [statistical_region_merging](statistical_region_merging.md) · [max_tree](max_tree.md) · [area_opening_attr](area_opening_attr.md) · [quasi_flat_zones](quasi_flat_zones.md) · [alpha_tree](alpha_tree.md) · [hierarchical_watershed](hierarchical_watershed.md) · [ultrametric_contour_map](ultrametric_contour_map.md)

---
*Provenance: seggraph.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

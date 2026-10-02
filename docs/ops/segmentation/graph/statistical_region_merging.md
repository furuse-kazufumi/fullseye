---
op: statistical_region_merging
dim: segmentation
category: graph
in: image2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# statistical_region_merging — SEGMENTATION `graph` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.statistical_region_merging(image, *, q: 'float' = 32.0, g: 'int' = 256, value_range=(0.0, 1.0), connectivity: 'int' = 4) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.statistical_region_merging(image, *, q: 'float' = 32.0, g: 'int' = 256, value_range=(0.0, 1.0), connectivity: 'int' = 4) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("statistical_region_merging")`)

## 使い方

統計的領域併合 SRM(Nock–Nielsen 2004): 隣の画素の組を |I_p − I_q| の昇順に処理し、述語 P(R, R') が真なら併合。

画素の値は ``value_range`` を [0, g − 1] に線形に写して使う(範囲の外の値は ValueError)。
P(R, R') ⇔ |R̄ − R̄'| ≤ √(b²(R) + b²(R'))、b(R) = g √(ln(|R_|R||/δ) / (2Q|R|))、ln|R_l| = min(l, g) ln(l + 1)、
δ = 1/(6|I|²)(述語の係数は **要確認**、モジュールの説明参照)。Q(``q``)が大きいほど b が小さく、併合を渋る(細かい)。
返す: ``labels``(1..k)、``n_regions``、``means``(領域ごとの平均、元の値の尺度)、``n_merges``、``q``。

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

[graph_cut_binary](graph_cut_binary.md) · [alpha_expansion](alpha_expansion.md) · [max_tree](max_tree.md) · [area_opening_attr](area_opening_attr.md) · [quasi_flat_zones](quasi_flat_zones.md) · [alpha_tree](alpha_tree.md) · [hierarchical_watershed](hierarchical_watershed.md) · [ultrametric_contour_map](ultrametric_contour_map.md)

---
*Provenance: seggraph.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

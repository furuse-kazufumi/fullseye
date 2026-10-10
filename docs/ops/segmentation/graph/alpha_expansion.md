---
op: alpha_expansion
dim: segmentation
category: graph
in: image2d
out: table
examples: [poc_graph_hierarchy_segmentation]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# alpha_expansion — SEGMENTATION `graph` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.alpha_expansion(image, means: 'Optional[Sequence[float]]' = None, *, lam: 'float' = 1.0, pairwise: 'str' = 'potts', truncation: 'float' = 2.0, connectivity: 'int' = 4, max_cycles: 'int' = 10, init=None) -> 'Dict[str, object]'` (実装を直接呼ぶなら `import seggraph; seggraph.alpha_expansion(image, means: 'Optional[Sequence[float]]' = None, *, lam: 'float' = 1.0, pairwise: 'str' = 'potts', truncation: 'float' = 2.0, connectivity: 'int' = 4, max_cycles: 'int' = 10, init=None) -> 'Dict[str, object]'`、台帳から引くなら `opssegmentation.get("alpha_expansion")`)

## 使い方

多ラベルの α-expansion(Boykov–Veksler–Zabih 2001): E(f) = Σ (I_p − μ_(f_p))² + λ Σ w_pq V(f_p, f_q)、V は計量。

``means`` = 各ラベルの平均 μ_1..μ_L(L ≥ 2。省くと画素の値の 1/6・1/2・5/6 分位の 3 ラベル)。V は ``"potts"``([α ≠ β]、c = 1)か ``"truncated_linear"``
(min(|α − β|, T)、T ≥ 1 なら計量、c = min(L − 1, T))。1 周 = α = 1..L の expansion を順に。各移動は 2 値の graph cut で
厳密に解き、**エネルギーが厳密に下がる時だけ** 受け入れる。1 周で 1 度も受け入れなければ止まる(論文と同じ)。
返す: ``labels``(1..L)、``energy``、``energies``(受け入れの列、単調減少)、``move_minima``(各移動の 2 値問題の最小、
今の値以下 = 門)、``c``、``bound_factor`` = 2c(Theorem 6.1: E(f̂) ≤ 2c E(f*))。

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

[graph_cut_binary](graph_cut_binary.md) · [statistical_region_merging](statistical_region_merging.md) · [max_tree](max_tree.md) · [area_opening_attr](area_opening_attr.md) · [quasi_flat_zones](quasi_flat_zones.md) · [alpha_tree](alpha_tree.md) · [hierarchical_watershed](hierarchical_watershed.md) · [ultrametric_contour_map](ultrametric_contour_map.md)

---
*Provenance: seggraph.py — SEGMENTATION operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

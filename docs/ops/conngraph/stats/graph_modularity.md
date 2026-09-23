---
op: graph_modularity
dim: conngraph
category: stats
in: conn_graph × labels
out: measurement
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# graph_modularity — CONNGRAPH `stats` op

- **データ種**: `conn_graph × labels` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_modularity(W: 'Any', labels: 'Any') -> 'float'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_modularity(W: 'Any', labels: 'Any') -> 'float'`、台帳から引くなら `opsconngraph.get("graph_modularity")`)

## 使い方

有向・重みつきモジュラリティ Q(Leicht–Newman 2008)。

Q = (1/m) Σ_ij (W_ij − k_i^out k_j^in / m) δ(c_i, c_j)、m = Σ W。全ノードが
1 つの群なら厳密に 0。対角(自己結合)は落とす。重みは非負であること。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`stats`)

[graph_degree_table](graph_degree_table.md) · [graph_clustering_coefficient](graph_clustering_coefficient.md) · [graph_betweenness](graph_betweenness.md) · [graph_laplacian_spectrum](graph_laplacian_spectrum.md) · [graph_spectral_radius](graph_spectral_radius.md) · [graph_components](graph_components.md) · [graph_rich_club](graph_rich_club.md) · [graph_motif_count](graph_motif_count.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

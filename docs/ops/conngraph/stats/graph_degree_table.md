---
op: graph_degree_table
dim: conngraph
category: stats
in: conn_graph
out: table
examples: [poc_larval_connectome_reservoir]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# graph_degree_table — CONNGRAPH `stats` op

- **データ種**: `conn_graph` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_degree_table(W: 'Any') -> 'dict[str, np.ndarray]'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_degree_table(W: 'Any') -> 'dict[str, np.ndarray]'`、台帳から引くなら `opsconngraph.get("graph_degree_table")`)

## 使い方

ノードごとの in_degree / out_degree(二値)と in_strength / out_strength(重み和)の表。

度数は ``W != 0`` の本数(対角は除く)、strength は重みの和(対角は除く)。
返りは列名 → 長さ n の配列の dict(この repo の ``table``)。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_larval_connectome_reservoir](../../../../examples/poc_larval_connectome_reservoir.py) — `py -3.11 examples/poc_larval_connectome_reservoir.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`stats`)

[graph_clustering_coefficient](graph_clustering_coefficient.md) · [graph_betweenness](graph_betweenness.md) · [graph_laplacian_spectrum](graph_laplacian_spectrum.md) · [graph_spectral_radius](graph_spectral_radius.md) · [graph_components](graph_components.md) · [graph_modularity](graph_modularity.md) · [graph_rich_club](graph_rich_club.md) · [graph_motif_count](graph_motif_count.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

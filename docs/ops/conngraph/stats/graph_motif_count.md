---
op: graph_motif_count
dim: conngraph
category: stats
in: conn_graph
out: measurement
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# graph_motif_count — CONNGRAPH `stats` op

- **データ種**: `conn_graph` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_motif_count(W: 'Any', motif: 'str' = 'ffl') -> 'float'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_motif_count(W: 'Any', motif: 'str' = 'ffl') -> 'float'`、台帳から引くなら `opsconngraph.get("graph_motif_count")`)

## 使い方

3 点モチーフの個数(二値有向、対角は除く): reciprocal / ffl / cycle3。

reciprocal = 相互結合の対の数 (Σ A∧Aᵀ)/2、ffl = Σ_ac (A²)_ac A_ac
(a→b, b→c, a→c)、cycle3 = tr(A³)/3。各インスタンスを 1 回だけ数える。

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

[graph_degree_table](graph_degree_table.md) · [graph_clustering_coefficient](graph_clustering_coefficient.md) · [graph_betweenness](graph_betweenness.md) · [graph_laplacian_spectrum](graph_laplacian_spectrum.md) · [graph_spectral_radius](graph_spectral_radius.md) · [graph_components](graph_components.md) · [graph_modularity](graph_modularity.md) · [graph_rich_club](graph_rich_club.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

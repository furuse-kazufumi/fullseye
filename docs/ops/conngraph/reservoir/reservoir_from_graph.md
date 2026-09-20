---
op: reservoir_from_graph
dim: conngraph
category: reservoir
in: conn_graph
out: conn_graph
examples: [poc_larval_connectome_reservoir]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# reservoir_from_graph — CONNGRAPH `reservoir` op

- **データ種**: `conn_graph` → `conn_graph`
- **呼び出し**: `import fullseye as fs; fs.ledger.reservoir_from_graph(W: 'Any', rho: 'float' = 0.9) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.reservoir_from_graph(W: 'Any', rho: 'float' = 0.9) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("reservoir_from_graph")`)

## 使い方

W をスペクトル半径が rho になるように定数倍した conn_graph(echo state の前処理)。半径 0 は拒否。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_larval_connectome_reservoir](../../../../examples/poc_larval_connectome_reservoir.py) — `py -3.11 examples/poc_larval_connectome_reservoir.py`

## 型が繋がる次の op(`conn_graph` を入力に取れる)

[graph_degree_preserving_shuffle](../build/graph_degree_preserving_shuffle.md) · [graph_binarize](../build/graph_binarize.md) · [graph_degree_table](../stats/graph_degree_table.md) · [graph_clustering_coefficient](../stats/graph_clustering_coefficient.md) · [graph_betweenness](../stats/graph_betweenness.md) · [graph_laplacian_spectrum](../stats/graph_laplacian_spectrum.md) · [graph_spectral_radius](../stats/graph_spectral_radius.md) · [graph_components](../stats/graph_components.md)

## 同カテゴリ(`reservoir`)

[reservoir_states](reservoir_states.md) · [reservoir_encode](reservoir_encode.md) · [ridge_readout](ridge_readout.md) · [ridge_predict](ridge_predict.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

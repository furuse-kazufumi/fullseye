---
op: graph_degree_preserving_shuffle
dim: conngraph
category: construct
in: conn_graph
out: conn_graph
examples: [poc_larval_connectome_reservoir, poc_malecns_activity_wave, poc_microns_brain_wave]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# graph_degree_preserving_shuffle — CONNGRAPH `construct` op

- **データ種**: `conn_graph` → `conn_graph`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_degree_preserving_shuffle(W: 'Any', n_swaps: 'int | None' = None, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_degree_preserving_shuffle(W: 'Any', n_swaps: 'int | None' = None, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("graph_degree_preserving_shuffle")`)

## 使い方

次数保存シャッフル(帰無モデル): 各ノードの入次数・出次数と重みの多重集合を保って辺を繋ぎ替える。

有向 double-edge swap(Maslov & Sneppen 2002): 辺 (a→b, w1) と (c→d, w2) を
(a→d, w1) と (c→b, w2) に替える。自己結合と重複辺を作る組は捨てる。
``n_swaps`` の既定は 10 × 辺数。**二値構造の次数**を保つ(重みは辺に付いて
移動するので strength は変わりうる)。対角(自己結合)は動かさずそのまま残す。
辺が 2 本未満なら複製を返す。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_larval_connectome_reservoir](../../../../examples/poc_larval_connectome_reservoir.py) — `py -3.11 examples/poc_larval_connectome_reservoir.py`
- [poc_malecns_activity_wave](../../../../examples/poc_malecns_activity_wave.py) — `py -3.11 examples/poc_malecns_activity_wave.py`
- [poc_microns_brain_wave](../../../../examples/poc_microns_brain_wave.py) — `py -3.11 examples/poc_microns_brain_wave.py`

## 型が繋がる次の op(`conn_graph` を入力に取れる)

[graph_binarize](graph_binarize.md) · [graph_degree_table](../stats/graph_degree_table.md) · [graph_clustering_coefficient](../stats/graph_clustering_coefficient.md) · [graph_betweenness](../stats/graph_betweenness.md) · [graph_laplacian_spectrum](../stats/graph_laplacian_spectrum.md) · [graph_spectral_radius](../stats/graph_spectral_radius.md) · [graph_components](../stats/graph_components.md) · [graph_modularity](../stats/graph_modularity.md)

## 同カテゴリ(`construct`)

[graph_from_synapses](graph_from_synapses.md) · [graph_binarize](graph_binarize.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

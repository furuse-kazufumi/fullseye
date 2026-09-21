---
op: graph_block_shuffle
dim: conngraph
category: dimension
in: conn_graph × labels
out: conn_graph
examples: [poc_connectome_motor_bottleneck]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# graph_block_shuffle — CONNGRAPH `dimension` op

- **データ種**: `conn_graph × labels` → `conn_graph`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_block_shuffle(W: 'Any', labels: 'Any', seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_block_shuffle(W: 'Any', labels: 'Any', seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("graph_block_shuffle")`)

## 使い方

層(ラベル)のブロックごとに**送り手を混ぜた**対照の ``conn_graph``: 各受け手が受ける重みの多重集合と
層間の総結線量は保ったまま、「誰から」だけを壊す。

``graph_degree_preserving_shuffle`` が全体の次数列を保つのに対し、こちらは**層構造を保つ**(脳 → 首 → 腹髄 →
筋 のブロックは動かさず、ブロックの中で行を並べ替える)。層の大きさと収束(fan-in)の効果を残して
「配線の特異性」だけを消した対照として使う。同じ ``seed`` で再現。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_connectome_motor_bottleneck](../../../../examples/poc_connectome_motor_bottleneck.py) — `py -3.11 examples/poc_connectome_motor_bottleneck.py`

## 型が繋がる次の op(`conn_graph` を入力に取れる)

[graph_degree_preserving_shuffle](../construct/graph_degree_preserving_shuffle.md) · [graph_binarize](../construct/graph_binarize.md) · [graph_degree_table](../stats/graph_degree_table.md) · [graph_clustering_coefficient](../stats/graph_clustering_coefficient.md) · [graph_betweenness](../stats/graph_betweenness.md) · [graph_laplacian_spectrum](../stats/graph_laplacian_spectrum.md) · [graph_spectral_radius](../stats/graph_spectral_radius.md) · [graph_components](../stats/graph_components.md)

## 同カテゴリ(`dimension`)

[graph_layer_propagate](graph_layer_propagate.md) · [states_participation_ratio](states_participation_ratio.md) · [states_layer_dimension](states_layer_dimension.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

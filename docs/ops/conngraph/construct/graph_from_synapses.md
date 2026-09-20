---
op: graph_from_synapses
dim: conngraph
category: construct
in: synapse_table
out: conn_graph
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# graph_from_synapses — CONNGRAPH `construct` op

- **データ種**: `synapse_table` → `conn_graph`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_from_synapses(syn: 'Any', n: 'int | None' = None, sign: 'float' = 1.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_from_synapses(syn: 'Any', n: 'int | None' = None, sign: 'float' = 1.0) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("graph_from_synapses")`)

## 使い方

シナプス表 (m, 3) = (pre_id, post_id, count) を n×n の重みつき有向隣接行列にする。

``W[pre, post] += count * sign``。同じ (pre, post) の行は足し合わせる。
``n`` を省くと ``max(id) + 1``。id は 0 始まりの整数値(float で持っていてよい)
で、範囲外・非整数・負の id は拒否する。``sign`` は抑制性シナプスを負で
入れたいときの係数(count 自体は符号を持たない量として扱う)。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`conn_graph` を入力に取れる)

[graph_degree_preserving_shuffle](graph_degree_preserving_shuffle.md) · [graph_binarize](graph_binarize.md) · [graph_degree_table](../stats/graph_degree_table.md) · [graph_clustering_coefficient](../stats/graph_clustering_coefficient.md) · [graph_betweenness](../stats/graph_betweenness.md) · [graph_laplacian_spectrum](../stats/graph_laplacian_spectrum.md) · [graph_spectral_radius](../stats/graph_spectral_radius.md) · [graph_components](../stats/graph_components.md)

## 同カテゴリ(`construct`)

[graph_degree_preserving_shuffle](graph_degree_preserving_shuffle.md) · [graph_binarize](graph_binarize.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

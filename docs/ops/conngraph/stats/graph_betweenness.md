---
op: graph_betweenness
dim: conngraph
category: stats
in: conn_graph
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# graph_betweenness — CONNGRAPH `stats` op

- **データ種**: `conn_graph` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_betweenness(W: 'Any') -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_betweenness(W: 'Any') -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("graph_betweenness")`)

## 使い方

媒介中心性(Brandes 2001、二値有向、正規化なし)。ノードごとの長さ n の配列。

ノード v の値 = Σ_{s≠v≠t} σ_st(v) / σ_st(最短路の本数比)。二値構造が対称
(すべての辺が相互)なら無向グラフとして (s, t) と (t, s) を 1 対と数え 2 で割る
—— 無向スター(n 個)の中心が (n−1)(n−2)/2、葉が 0 になる教科書の値。
有向(非対称)なら順序対のまま数える。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`signal` を入力に取れる)

—

## 同カテゴリ(`stats`)

[graph_degree_table](graph_degree_table.md) · [graph_clustering_coefficient](graph_clustering_coefficient.md) · [graph_laplacian_spectrum](graph_laplacian_spectrum.md) · [graph_spectral_radius](graph_spectral_radius.md) · [graph_components](graph_components.md) · [graph_modularity](graph_modularity.md) · [graph_rich_club](graph_rich_club.md) · [graph_motif_count](graph_motif_count.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

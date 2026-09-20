---
op: graph_adjacency_image
dim: conngraph
category: view
in: conn_graph
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# graph_adjacency_image — CONNGRAPH `view` op

- **データ種**: `conn_graph` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_adjacency_image(W: 'Any', order: 'str' = 'none', log: 'bool' = True) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_adjacency_image(W: 'Any', order: 'str' = 'none', log: 'bool' = True) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("graph_adjacency_image")`)

## 使い方

隣接行列を [0, 1] の画像 (n, n) にする。order = none / degree(総次数の降順)/ component(成分順)。

値は |W| を(log なら log1p してから)最大値で割る。全零なら全零の画像。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

—

## 同カテゴリ(`view`)

[graph_layout_spectral](graph_layout_spectral.md) · [graph_edges_as_lines](graph_edges_as_lines.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

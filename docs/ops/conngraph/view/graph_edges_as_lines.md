---
op: graph_edges_as_lines
dim: conngraph
category: view
in: conn_graph × points
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# graph_edges_as_lines — CONNGRAPH `view` op

- **データ種**: `conn_graph × points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_edges_as_lines(W: 'Any', P: 'Any', thresh: 'float' = 0.0) -> 'dict[str, np.ndarray]'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_edges_as_lines(W: 'Any', P: 'Any', thresh: 'float' = 0.0) -> 'dict[str, np.ndarray]'`、台帳から引くなら `opsconngraph.get("graph_edges_as_lines")`)

## 使い方

辺を線分の表にする(Studio で点群に重ねる出口): 列 pre / post / x0 y0 z0 / x1 y1 z1 / weight。

``P`` は graph_layout_spectral の (n, 3)(または (n, 2)、z = 0 を足す)。
|W| > thresh の辺だけ、対角(自己結合)は長さ 0 なので出さない。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`view`)

[graph_layout_spectral](graph_layout_spectral.md) · [graph_adjacency_image](graph_adjacency_image.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

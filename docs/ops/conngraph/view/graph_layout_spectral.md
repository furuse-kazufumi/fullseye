---
op: graph_layout_spectral
dim: conngraph
category: view
in: conn_graph
out: points
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# graph_layout_spectral — CONNGRAPH `view` op

- **データ種**: `conn_graph` → `points`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_layout_spectral(W: 'Any', dim: 'int' = 2, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_layout_spectral(W: 'Any', dim: 'int' = 2, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("graph_layout_spectral")`)

## 使い方

スペクトル配置: 向きを畳んだ Laplacian の Fiedler ベクトル(第 2..dim+1 固有ベクトル)を座標にした点群 (n, 3)、各軸 [0, 1]。

``dim`` は 2 か 3(2 なら z = 0)。連結成分ごとに配置してから格子に並べる —— 非連結の
グラフでは零固有空間が縮退して Fiedler ベクトルが成分を分けるとは限らないので、
成分は明示的に分ける(成分内は箱の 0.3 倍、成分間は 1 の間隔)。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`points` を入力に取れる)

[graph_edges_as_lines](graph_edges_as_lines.md) · [graph_activity_spread](../activity/graph_activity_spread.md) · [points_activity_video](../activity/points_activity_video.md)

## 同カテゴリ(`view`)

[graph_edges_as_lines](graph_edges_as_lines.md) · [graph_adjacency_image](graph_adjacency_image.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

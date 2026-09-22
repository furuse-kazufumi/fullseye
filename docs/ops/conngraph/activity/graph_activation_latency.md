---
op: graph_activation_latency
dim: conngraph
category: activity
in: matrix
out: labels
examples: [poc_malecns_activity_wave]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# graph_activation_latency — CONNGRAPH `activity` op

- **データ種**: `matrix` → `labels`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_activation_latency(X: 'Any', thresh: 'float' = 0.1) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_activation_latency(X: 'Any', thresh: 'float' = 0.1) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("graph_activation_latency")`)

## 使い方

各ノードが初めて「点いた」ステップ(0 始まり)の列 (n,)、整数。点かなかったノードは −1。

``X`` は reservoir_states の (T, n)。「点いた」= |x| ≥ **全体の最大値** × thresh(thresh は
(0, 1])。尺度はノードごとでなく 1 つ —— ノードごとに伸ばすと、ほとんど動かないノードの
丸め屑も「点いた」になる。全零の X はすべて −1。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_malecns_activity_wave](../../../../examples/poc_malecns_activity_wave.py) — `py -3.11 examples/poc_malecns_activity_wave.py`

## 型が繋がる次の op(`labels` を入力に取れる)

[graph_modularity](../stats/graph_modularity.md) · [graph_activity_spread](graph_activity_spread.md) · [graph_block_shuffle](../dimension/graph_block_shuffle.md) · [graph_layer_propagate](../dimension/graph_layer_propagate.md) · [states_layer_dimension](../dimension/states_layer_dimension.md)

## 同カテゴリ(`activity`)

[graph_activity_spread](graph_activity_spread.md) · [points_activity_video](points_activity_video.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

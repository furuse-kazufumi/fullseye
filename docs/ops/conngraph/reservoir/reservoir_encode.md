---
op: reservoir_encode
dim: conngraph
category: reservoir
in: conn_graph × matrix
out: matrix
examples: [poc_larval_connectome_reservoir]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# reservoir_encode — CONNGRAPH `reservoir` op

- **データ種**: `conn_graph × matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.reservoir_encode(W: 'Any', X: 'Any', steps: 'int' = 6, in_scale: 'float' = 0.1, leak: 'float' = 0.3, nonlinearity: 'str' = 'tanh', seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.reservoir_encode(W: 'Any', X: 'Any', steps: 'int' = 6, in_scale: 'float' = 0.1, leak: 'float' = 0.3, nonlinearity: 'str' = 'tanh', seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("reservoir_encode")`)

## 使い方

静的入力の一括 reservoir 符号化(分類用): X の各行を零状態から steps 回回した最終状態 (N, n)。

行 x ごとに x_{t+1} = (1−leak) x_t + leak · f(Wᵀ x_t + W_in x) を steps 回。
``W_in`` は reservoir_states と同じ seed 付き一様 (−in_scale, in_scale) の (n, d)。
行のループは書かず、1 ステップ = (N, n) @ (n, n) の行列積 1 回で全行を同時に進める。
linear・leak 1・steps 1 なら X W_inᵀ、steps 2 なら (X W_inᵀ) W + X W_inᵀ に厳密一致。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_larval_connectome_reservoir](../../../../examples/poc_larval_connectome_reservoir.py) — `py -3.11 examples/poc_larval_connectome_reservoir.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[reservoir_states](reservoir_states.md) · [ridge_readout](ridge_readout.md) · [ridge_predict](ridge_predict.md) · [graph_activation_latency](../activity/graph_activation_latency.md) · [graph_activity_spread](../activity/graph_activity_spread.md) · [points_activity_video](../activity/points_activity_video.md) · [graph_layer_propagate](../dimension/graph_layer_propagate.md) · [states_participation_ratio](../dimension/states_participation_ratio.md)

## 同カテゴリ(`reservoir`)

[reservoir_from_graph](reservoir_from_graph.md) · [reservoir_states](reservoir_states.md) · [ridge_readout](ridge_readout.md) · [ridge_predict](ridge_predict.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

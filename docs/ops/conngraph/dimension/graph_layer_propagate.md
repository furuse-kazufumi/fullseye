---
op: graph_layer_propagate
dim: conngraph
category: dimension
in: conn_graph × labels × matrix
out: matrix
examples: [poc_connectome_motor_bottleneck]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# graph_layer_propagate — CONNGRAPH `dimension` op

- **データ種**: `conn_graph × labels × matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.graph_layer_propagate(W: 'Any', labels: 'Any', U: 'Any', activation: 'str' = 'kwta', active_frac: 'float' = 0.1, gain: 'float' = 1.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.graph_layer_propagate(W: 'Any', labels: 'Any', U: 'Any', activation: 'str' = 'kwta', active_frac: 'float' = 0.1, gain: 'float' = 1.0) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("graph_layer_propagate")`)

## 使い方

層 0 の状態 ``U`` (N, n_0) を、ブロック ``W[layer a → layer a+1]`` で**前向きに一段ずつ**通した全層の状態
``(N, n)``(``matrix``、列はノード順で層 0 の列は ``U`` そのもの)。

受け手ごとに入力重みの和を 1 に正規化してから重みつき和を取り(層の大きさに依らない)、``activation`` で
活性化する: ``"linear"`` はそのまま(平均絶対値を ``gain`` に)、``"tanh"`` は飽和、``"kwta"`` は各刺激で
入力が上位 ``active_frac`` の受け手だけが(閾値上の余剰で)発火し、平均が 1 になるよう正規化する。
層をまたぐ結線(層 a → a+2)と層内の再帰は**使わない**(前向きの一段ごとの写像だけを見る道具)。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_connectome_motor_bottleneck](../../../../examples/poc_connectome_motor_bottleneck.py) — `py -3.11 examples/poc_connectome_motor_bottleneck.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[reservoir_states](../reservoir/reservoir_states.md) · [reservoir_encode](../reservoir/reservoir_encode.md) · [ridge_readout](../reservoir/ridge_readout.md) · [ridge_predict](../reservoir/ridge_predict.md) · [graph_activation_latency](../activity/graph_activation_latency.md) · [graph_activity_spread](../activity/graph_activity_spread.md) · [points_activity_video](../activity/points_activity_video.md) · [states_participation_ratio](states_participation_ratio.md)

## 同カテゴリ(`dimension`)

[graph_block_shuffle](graph_block_shuffle.md) · [states_participation_ratio](states_participation_ratio.md) · [states_layer_dimension](states_layer_dimension.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

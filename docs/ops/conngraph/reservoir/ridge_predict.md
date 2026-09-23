---
op: ridge_predict
dim: conngraph
category: reservoir
in: matrix × matrix
out: matrix
examples: [poc_larval_connectome_reservoir]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# ridge_predict — CONNGRAPH `reservoir` op

- **データ種**: `matrix × matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.ridge_predict(X: 'Any', Wout: 'Any') -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.ridge_predict(X: 'Any', Wout: 'Any') -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("ridge_predict")`)

## 使い方

読み出し重みで予測 (T, k) = [X, 1] · Wout。Wout は ridge_readout の (d+1, k)。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_larval_connectome_reservoir](../../../../examples/poc_larval_connectome_reservoir.py) — `py -3.11 examples/poc_larval_connectome_reservoir.py`

## 型が繋がる次の op(`matrix` を入力に取れる)

[reservoir_states](reservoir_states.md) · [reservoir_encode](reservoir_encode.md) · [ridge_readout](ridge_readout.md) · [graph_activation_latency](../activity/graph_activation_latency.md) · [graph_activity_spread](../activity/graph_activity_spread.md) · [points_activity_video](../activity/points_activity_video.md) · [graph_layer_propagate](../dimension/graph_layer_propagate.md) · [states_participation_ratio](../dimension/states_participation_ratio.md)

## 同カテゴリ(`reservoir`)

[reservoir_from_graph](reservoir_from_graph.md) · [reservoir_states](reservoir_states.md) · [reservoir_encode](reservoir_encode.md) · [ridge_readout](ridge_readout.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

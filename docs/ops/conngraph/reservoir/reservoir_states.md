---
op: reservoir_states
dim: conngraph
category: reservoir
in: conn_graph × matrix
out: matrix
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# reservoir_states — CONNGRAPH `reservoir` op

- **データ種**: `conn_graph × matrix` → `matrix`
- **呼び出し**: `import fullseye as fs; fs.ledger.reservoir_states(W: 'Any', U: 'Any', in_scale: 'float' = 1.0, leak: 'float' = 1.0, nonlinearity: 'str' = 'tanh', seed: 'int' = 0, washout: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import conngraph; conngraph.reservoir_states(W: 'Any', U: 'Any', in_scale: 'float' = 1.0, leak: 'float' = 1.0, nonlinearity: 'str' = 'tanh', seed: 'int' = 0, washout: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsconngraph.get("reservoir_states")`)

## 使い方

reservoir の状態列: x_{t+1} = (1−leak) x_t + leak · f(Wᵀ x_t + W_in u_t)。返りは (T − washout, n)。

``U`` は (T, d) の入力列(1-D は (T, 1))。``W_in`` は seed で決まる一様 (−in_scale, in_scale)
の (n, d) 行列。``nonlinearity`` は tanh / linear。x_0 = 0 から始め、各ステップの更新後の
状態を並べる。``washout`` 行を先頭から捨てる(T 以上は拒否)。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`matrix` を入力に取れる)

[reservoir_encode](reservoir_encode.md) · [ridge_readout](ridge_readout.md) · [ridge_predict](ridge_predict.md)

## 同カテゴリ(`reservoir`)

[reservoir_from_graph](reservoir_from_graph.md) · [reservoir_encode](reservoir_encode.md) · [ridge_readout](ridge_readout.md) · [ridge_predict](ridge_predict.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

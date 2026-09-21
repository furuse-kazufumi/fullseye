---
op: states_layer_dimension
dim: conngraph
category: dimension
in: matrix × labels
out: table
examples: [poc_connectome_motor_bottleneck]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# states_layer_dimension — CONNGRAPH `dimension` op

- **データ種**: `matrix × labels` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.states_layer_dimension(X: 'Any', labels: 'Any') -> 'dict[str, np.ndarray]'` (実装を直接呼ぶなら `import conngraph; conngraph.states_layer_dimension(X: 'Any', labels: 'Any') -> 'dict[str, np.ndarray]'`、台帳から引くなら `opsconngraph.get("states_layer_dimension")`)

## 使い方

層ごとの実効次元の表: 列 layer / n / participation_ratio / ratio(= PR / n)。

``X`` = ``graph_layer_propagate`` の返り (N, n)、``labels`` = ノードの層 id。「脳 → 首 → 腹髄 → 筋」で
次元がどこで落ちるか(動きの量子化)を 1 つの数式で読む。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_connectome_motor_bottleneck](../../../../examples/poc_connectome_motor_bottleneck.py) — `py -3.11 examples/poc_connectome_motor_bottleneck.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`dimension`)

[graph_block_shuffle](graph_block_shuffle.md) · [graph_layer_propagate](graph_layer_propagate.md) · [states_participation_ratio](states_participation_ratio.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

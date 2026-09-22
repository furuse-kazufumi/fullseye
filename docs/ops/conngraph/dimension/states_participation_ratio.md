---
op: states_participation_ratio
dim: conngraph
category: dimension
in: matrix
out: measurement
examples: [poc_connectome_motor_bottleneck]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# states_participation_ratio — CONNGRAPH `dimension` op

- **データ種**: `matrix` → `measurement`
- **呼び出し**: `import fullseye as fs; fs.ledger.states_participation_ratio(X: 'Any') -> 'float'` (実装を直接呼ぶなら `import conngraph; conngraph.states_participation_ratio(X: 'Any') -> 'float'`、台帳から引くなら `opsconngraph.get("states_participation_ratio")`)

## 使い方

状態列 ``X`` (N, n) の**実効次元** = participation ratio ``PR = (Σλ)² / Σλ²``(λ は共分散の固有値、
Gao et al. 2017)。全列が独立で同じ分散なら n、1 本の方向に乗っていれば 1。

標本数 N に依存する(N が小さいと PR ≤ N に頭打ち)ので、比べるときは N を揃える。定数(分散 0)なら 0。

## 詳しい使い方ガイド

- [conngraph ファミリ ガイド](../guides/conngraph.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_connectome_motor_bottleneck](../../../../examples/poc_connectome_motor_bottleneck.py) — `py -3.11 examples/poc_connectome_motor_bottleneck.py`

## 型が繋がる次の op(`measurement` を入力に取れる)

—

## 同カテゴリ(`dimension`)

[graph_block_shuffle](graph_block_shuffle.md) · [graph_layer_propagate](graph_layer_propagate.md) · [states_layer_dimension](states_layer_dimension.md)

---
*Provenance: conngraph.py — CONNGRAPH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

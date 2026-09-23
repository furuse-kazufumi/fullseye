---
op: perpetual_step
dim: generative
category: stream
in: table
out: table
examples: [poc_illusions_and_perpetual_drawing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# perpetual_step — GENERATIVE `stream` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.perpetual_step(state: 'dict', steps: 'int' = 1) -> 'dict'` (実装を直接呼ぶなら `import perpetual; perpetual.perpetual_step(state: 'dict', steps: 'int' = 1) -> 'dict'`、台帳から引くなら `opsgenerative.get("perpetual_step")`)

## 使い方

状態を ``steps`` だけ進める(同じ dict を返す ―― 大きな配列を複製しない)。

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_illusions_and_perpetual_drawing](../../../../examples/poc_illusions_and_perpetual_drawing.py) — `py -3.11 examples/poc_illusions_and_perpetual_drawing.py`

## 型が繋がる次の op(`table` を入力に取れる)

[perpetual_render](perpetual_render.md)

## 同カテゴリ(`stream`)

[perpetual_state](perpetual_state.md) · [perpetual_render](perpetual_render.md)

---
*Provenance: perpetual.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

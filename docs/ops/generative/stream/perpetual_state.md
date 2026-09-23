---
op: perpetual_state
dim: generative
category: stream
in: 
out: table
examples: [poc_illusions_and_perpetual_drawing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# perpetual_state — GENERATIVE `stream` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.perpetual_state(name: 'str' = 'langtons_ant', size: 'int' = 301, seed: 'int' = 0, rule: 'int' = 110) -> 'dict'` (実装を直接呼ぶなら `import perpetual; perpetual.perpetual_state(name: 'str' = 'langtons_ant', size: 'int' = 301, seed: 'int' = 0, rule: 'int' = 110) -> 'dict'`、台帳から引くなら `opsgenerative.get("perpetual_state")`)

## 使い方

無限に回せる**状態**を作る(``table``)。止めどきは呼んだ側が決める。

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_illusions_and_perpetual_drawing](../../../../examples/poc_illusions_and_perpetual_drawing.py) — `py -3.11 examples/poc_illusions_and_perpetual_drawing.py`

## 型が繋がる次の op(`table` を入力に取れる)

[perpetual_step](perpetual_step.md) · [perpetual_render](perpetual_render.md)

## 同カテゴリ(`stream`)

[perpetual_step](perpetual_step.md) · [perpetual_render](perpetual_render.md)

---
*Provenance: perpetual.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

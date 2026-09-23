---
op: perpetual_reaction_diffusion
dim: generative
category: perpetual
in: 
out: rgb
examples: [poc_illusions_and_perpetual_drawing]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# perpetual_reaction_diffusion — GENERATIVE `perpetual` op

- **データ種**: `なし` → `rgb`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.perpetual_reaction_diffusion(size: 'int' = 220, steps: 'int' = 1600, feed: 'float' = 0.037, kill: 'float' = 0.06, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import perpetual; perpetual.perpetual_reaction_diffusion(size: 'int' = 220, steps: 'int' = 1600, feed: 'float' = 0.037, kill: 'float' = 0.06, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsgenerative.get("perpetual_reaction_diffusion")`)

## 使い方

グレイ–スコット反応拡散 ―― 模様が生まれ、分裂し、増え続ける。

不変量: **餌も死も 0(``feed = kill = 0``)なら、総量は厳密に保存される**
—— 拡散は再分配であって生成ではないから。数値解法が壊れていれば、
ここが真っ先に崩れる(:func:`perpetual_identities`)。

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_illusions_and_perpetual_drawing](../../../../examples/poc_illusions_and_perpetual_drawing.py) — `py -3.11 examples/poc_illusions_and_perpetual_drawing.py`

## 型が繋がる次の op(`rgb` を入力に取れる)

—

## 同カテゴリ(`perpetual`)

[perpetual_ten_print](perpetual_ten_print.md) · [perpetual_truchet](perpetual_truchet.md) · [perpetual_elementary_ca](perpetual_elementary_ca.md) · [perpetual_langtons_ant](perpetual_langtons_ant.md) · [perpetual_chaos_game](perpetual_chaos_game.md) · [perpetual_apollonian](perpetual_apollonian.md) · [perpetual_harmonograph](perpetual_harmonograph.md) · [perpetual_ifs_attractor](perpetual_ifs_attractor.md)

---
*Provenance: perpetual.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

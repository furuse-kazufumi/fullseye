---
op: perpetual_langtons_ant
dim: generative
category: perpetual
in: 
out: rgb
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# perpetual_langtons_ant — GENERATIVE `perpetual` op

- **データ種**: `なし` → `rgb`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.perpetual_langtons_ant(steps: 'int' = 12000, size: 'int' = 301) -> 'np.ndarray'` (実装を直接呼ぶなら `import perpetual; perpetual.perpetual_langtons_ant(steps: 'int' = 12000, size: 'int' = 301) -> 'np.ndarray'`、台帳から引くなら `opsgenerative.get("perpetual_langtons_ant")`)

## 使い方

ラングトンの蟻 ―― 2 つの規則だけで、1 万歩後に「高速道路」を作り続ける。

不変量: 高速道路に入ったあとは **周期 104 で斜めに (-2,-2) 進む**。

★塗りは「そのマスが黒でいた時間」。高速道路は最後にできるので薄く、
最初の混沌は濃い —— **時間の順序が絵に出る**。

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`rgb` を入力に取れる)

—

## 同カテゴリ(`perpetual`)

[perpetual_ten_print](perpetual_ten_print.md) · [perpetual_truchet](perpetual_truchet.md) · [perpetual_elementary_ca](perpetual_elementary_ca.md) · [perpetual_chaos_game](perpetual_chaos_game.md) · [perpetual_apollonian](perpetual_apollonian.md) · [perpetual_harmonograph](perpetual_harmonograph.md) · [perpetual_ifs_attractor](perpetual_ifs_attractor.md) · [perpetual_flow_field](perpetual_flow_field.md)

---
*Provenance: perpetual.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

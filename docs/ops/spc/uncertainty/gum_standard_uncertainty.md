---
op: gum_standard_uncertainty
dim: spc
category: uncertainty
in: table
out: table
examples: [poc_measurement_system_analysis]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# gum_standard_uncertainty — SPC `uncertainty` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gum_standard_uncertainty(table, halfwidth='halfwidth', distribution='distribution')` (実装を直接呼ぶなら `import spc; spc.gum_standard_uncertainty(table, halfwidth='halfwidth', distribution='distribution')`、台帳から引くなら `opsspc.get("gum_standard_uncertainty")`)

## 使い方

不確かさの成分を**分布の形**から標準不確かさへ直す(``table``)。

校正証明書や規格が与えるのは「半幅 a」「95 % で ±U」のような形であって標準偏差
ではない。伝播則が食えるのは標準不確かさだけなので、ここで揃える:

    矩形(一様)  u = a / sqrt(3)      三角      u = a / sqrt(6)
    U 字(逆正弦) u = a / sqrt(2)      normal_95 u = a / 1.959964

★どれも分布の分散の定義から出る**厳密**な値で、モンテカルロで標本標準偏差を
取れば同じ数に収束する(``gum_monte_carlo`` が独立に確かめる)。

★★**既定の分布を置かない**。一番よく使うからといって矩形を既定にすると、
形を書き忘れた成分が黙って a/sqrt(3) になる —— 三角のつもりなら 1.41 倍、
95 % 区間のつもりなら 1.13 倍ずれた不確かさが、例外を出さずに下流へ流れる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_propagate](gum_propagate.md) · [gum_expanded](gum_expanded.md) · [gum_monte_carlo](gum_monte_carlo.md) · [gum_validate](gum_validate.md)

## 同カテゴリ(`uncertainty`)

[gum_propagate](gum_propagate.md) · [gum_expanded](gum_expanded.md) · [gum_monte_carlo](gum_monte_carlo.md) · [gum_validate](gum_validate.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

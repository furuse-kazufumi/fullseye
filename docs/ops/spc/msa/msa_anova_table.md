---
op: msa_anova_table
dim: spc
category: msa
in: table
out: table
examples: [poc_measurement_system_analysis]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# msa_anova_table — SPC `msa` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.msa_anova_table(table, part='part', operator='operator', value='value')` (実装を直接呼ぶなら `import spc; spc.msa_anova_table(table, part='part', operator='operator', value='value')`、台帳から引くなら `opsspc.get("msa_anova_table")`)

## 使い方

交差 2 元配置(部品 x 測定者 x 繰り返し)の分散分析表(``table``)。

*table* は列 *part* / *operator* / *value* を持つ表。設計は**釣り合っている**
こと(升目ごとの繰り返し数が同じ)——釣り合っていなければ拒む。

返りは source / ss / df / ms / f / p の 6 列。``f`` と ``p`` は測定者と交互作用を
交互作用平均平方で、交互作用を誤差平均平方で検定した値(規格の慣行)。

★門にできる厳密な恒等式: ``ss_total == ss_part + ss_oper + ss_inter + ss_err``。
これは代数的な分解なので、分散成分をどう出そうと必ず成り立つ —— 片方が壊れれば
一致しない。自由度も ``df_total == 和`` で閉じる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_gauge_rr](msa_gauge_rr.md) · [msa_bias_linearity](msa_bias_linearity.md) · [msa_attribute_agreement](msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md) · [gum_validate](../uncertainty/gum_validate.md)

## 同カテゴリ(`msa`)

[msa_gauge_rr](msa_gauge_rr.md) · [msa_bias_linearity](msa_bias_linearity.md) · [msa_attribute_agreement](msa_attribute_agreement.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

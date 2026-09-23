---
op: msa_bias_linearity
dim: spc
category: msa
in: table
out: table
examples: [poc_measurement_system_analysis]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# msa_bias_linearity — SPC `msa` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.msa_bias_linearity(table, reference='reference', measured='measured')` (実装を直接呼ぶなら `import spc; spc.msa_bias_linearity(table, reference='reference', measured='measured')`、台帳から引くなら `opsspc.get("msa_bias_linearity")`)

## 使い方

基準値に対する偏りと、その基準値依存(直線性)(``table``)。

偏り ``bias = measured - reference`` を基準値に回帰する
(``bias = intercept + slope * reference``)。傾きが 0 でなければ、測定系は
測定範囲の**場所によって違う量だけずれている** = 直線性の問題。

返りは基準値ごとの平均偏り(``ref`` / ``bias_mean`` / ``n``)と、回帰の
``intercept`` / ``slope`` / それぞれの標準誤差・t 値・p 値、全体平均偏り。

★門にできる厳密な性質: 雑音の無い ``bias = a + b*ref`` を渡すと最小二乗は
a と b を**厳密に**返す(残差 0)。そのとき標準誤差は 0 なので t は ``inf`` /
p は 0 —— これは欠陥ではなく完全適合の正しい報告なので、そのまま返す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](msa_anova_table.md) · [msa_gauge_rr](msa_gauge_rr.md) · [msa_attribute_agreement](msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md) · [gum_validate](../uncertainty/gum_validate.md)

## 同カテゴリ(`msa`)

[msa_anova_table](msa_anova_table.md) · [msa_gauge_rr](msa_gauge_rr.md) · [msa_attribute_agreement](msa_attribute_agreement.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

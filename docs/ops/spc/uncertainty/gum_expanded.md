---
op: gum_expanded
dim: spc
category: uncertainty
in: table
out: table
examples: [poc_measurement_system_analysis]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# gum_expanded — SPC `uncertainty` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gum_expanded(table, u='u', sensitivity='sensitivity', dof='dof', level=0.95, correlation=None, estimate=None, lower_bound=None, upper_bound=None)` (実装を直接呼ぶなら `import spc; spc.gum_expanded(table, u='u', sensitivity='sensitivity', dof='dof', level=0.95, correlation=None, estimate=None, lower_bound=None, upper_bound=None)`、台帳から引くなら `opsspc.get("gum_expanded")`)

## 使い方

Welch-Satterthwaite の有効自由度と包含係数 k、拡張不確かさ U(``table``)。

    nu_eff = u_c^4 / sum_i (c_i u_i)^4 / nu_i        U = k u_c,  k = t_{p}(nu_eff)

★門にできる厳密な性質が 3 つある:

  * 成分が 1 つだけなら ``nu_eff == nu``(厳密)。
  * ``nu_eff >= min_i nu_i`` が**常に**成り立つ。証明は
    ``sum u_i^4/nu_i <= (1/nu_min) sum u_i^4 <= (1/nu_min)(sum u_i^2)^2``。
    有効自由度が最小の成分より小さくなったら計算が壊れている。
  * すべての自由度が無限大なら ``k`` は正規分布の分位点へ収束する
    (95 % で 1.959964)。

無限自由度(既知の定数など)は ``numpy.inf`` を入れる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](gum_standard_uncertainty.md) · [gum_propagate](gum_propagate.md) · [gum_monte_carlo](gum_monte_carlo.md) · [gum_validate](gum_validate.md)

## 同カテゴリ(`uncertainty`)

[gum_standard_uncertainty](gum_standard_uncertainty.md) · [gum_propagate](gum_propagate.md) · [gum_monte_carlo](gum_monte_carlo.md) · [gum_validate](gum_validate.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

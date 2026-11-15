---
op: gum_expanded
dim: spc
category: uncertainty
in: table
out: table
gpu: なし
examples: [poc_light_section_step_weld_floor, poc_measurement_system_analysis]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# gum_expanded — SPC `uncertainty` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gum_expanded(table, u='u', sensitivity='sensitivity', dof='dof', level=0.95, correlation=None, estimate=None, lower_bound=None, upper_bound=None)` (実装を直接呼ぶなら `import spc; spc.gum_expanded(table, u='u', sensitivity='sensitivity', dof='dof', level=0.95, correlation=None, estimate=None, lower_bound=None, upper_bound=None)`、台帳から引くなら `opsspc.get("gum_expanded")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Welch-Satterthwaite の有効自由度と包含係数 k、拡張不確かさ U(``table``)。

    nu_eff = u_c^4 / sum_i (c_i u_i)^4 / nu_i        U = k u_c,  k = t_{p}(floor(nu_eff))

★門にできる厳密な性質が 3 つある:

  * 成分が 1 つだけなら ``nu_eff == nu``(厳密)。
  * ``nu_eff >= min_i nu_i`` が**常に**成り立つ。証明は
    ``sum u_i^4/nu_i <= (1/nu_min) sum u_i^4 <= (1/nu_min)(sum u_i^2)^2``。
    有効自由度が最小の成分より小さくなったら計算が壊れている。
  * すべての自由度が無限大なら ``k`` は正規分布の分位点へ収束する
    (95 % で 1.959964)。

無限自由度(既知の定数など)は ``numpy.inf`` を入れる。

★★**相関があるときの自由度**。Welch-Satterthwaite(GUM G.4.1)は入力が**独立**で
あることを前提にした式で、相関項を含む ``u_c`` にそのまま当てると自由度を水増し
する(等しい 2 成分・各 nu=4・r=+1 で nu_eff=32 —— 予算の自由度の総和 8 を超える)。
負の相関では逆に 1 未満へ潰れる。そこで *correlation* に非零の非対角があるときは、
非零の相関でつながった成分を 1 つの群にまとめ、群の分散 ``w_g' R_g w_g``
(``w = c u``)と群の自由度 ``min_{i in g} nu_i`` で Welch-Satterthwaite を組む::

    nu_eff = u_c^4 / sum_g (w_g' R_g w_g)^2 / min_{i in g} nu_i

根拠: 同じ測定から推定した相関する成分(共分散行列が Wishart、自由度 nu 共通)では、
合成分散の推定量は厳密に ``sigma^2 chi^2_nu / nu`` で、有効自由度は ``r`` に依らず
``nu`` そのもの(Willink, *Metrologia* 44:340, 2007 の一般化 Welch-Satterthwaite で
r=+1 の等しい 2 成分が nu になるのと一致)。自由度の違う成分が相関する場合は最小値を
取る —— 安全側(k を大きく)に倒す本実装の規則であって、規格の式ではない。
相関がすべて 0(または単位行列)なら群は全部 1 成分で、従来の式と同じ値になる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_light_section_step_weld_floor](../../../../examples/poc_light_section_step_weld_floor.py) — `py -3.11 examples/poc_light_section_step_weld_floor.py`
- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](gum_standard_uncertainty.md) · [gum_propagate](gum_propagate.md) · [gum_monte_carlo](gum_monte_carlo.md) · [gum_validate](gum_validate.md)

## 同カテゴリ(`uncertainty`)

[gum_standard_uncertainty](gum_standard_uncertainty.md) · [gum_propagate](gum_propagate.md) · [gum_monte_carlo](gum_monte_carlo.md) · [gum_validate](gum_validate.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

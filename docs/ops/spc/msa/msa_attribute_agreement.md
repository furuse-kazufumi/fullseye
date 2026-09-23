---
op: msa_attribute_agreement
dim: spc
category: msa
in: table
out: table
examples: [poc_measurement_system_analysis]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# msa_attribute_agreement — SPC `msa` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.msa_attribute_agreement(table, appraiser='appraiser', part='part', rating='rating')` (実装を直接呼ぶなら `import spc; spc.msa_attribute_agreement(table, appraiser='appraiser', part='part', rating='rating')`、台帳から引くなら `opsspc.get("msa_attribute_agreement")`)

## 使い方

計数値(合否)検査の一致度(``table``)。

同じ部品を複数の検査員が判定した表から、**検査員の対ごとの Cohen のカッパ**と
全体の **Fleiss のカッパ**、および素の一致率を返す。

★カッパは一致率そのものではない。``kappa = (p_o - p_e)/(1 - p_e)`` で、
**偶然でも起きる一致 p_e を割り引いた**残りを測る —— 合格率 95 % の工程では
でたらめに判を押しても素の一致率は 90 % を超えるので、一致率だけ見ると
「よく合っている」と読めてしまう。

★門にできる厳密な値: 全員が同じ判定 → ``kappa = 1``(厳密)。2 人 x 2 カテゴリの
Cohen のカッパは ``2(ad-bc)/((a+b)(b+d)+(a+c)(c+d))`` という閉形式と一致する。
独立でたらめな判定では期待値 0(こちらは標本ごとに揺れるので区間で見る)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](msa_anova_table.md) · [msa_gauge_rr](msa_gauge_rr.md) · [msa_bias_linearity](msa_bias_linearity.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md) · [gum_validate](../uncertainty/gum_validate.md)

## 同カテゴリ(`msa`)

[msa_anova_table](msa_anova_table.md) · [msa_gauge_rr](msa_gauge_rr.md) · [msa_bias_linearity](msa_bias_linearity.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

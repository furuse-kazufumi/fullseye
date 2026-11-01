---
op: proportion_interval
dim: spc
category: pod
in: 
out: table
gpu: なし
examples: [proportion_interval_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# proportion_interval — SPC `pod` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.proportion_interval(k, n, *, confidence=0.95, sides='two', method='clopper_pearson')` (実装を直接呼ぶなら `import pod; pod.proportion_interval(k, n, *, confidence=0.95, sides='two', method='clopper_pearson')`、台帳から引くなら `opsspc.get("proportion_interval")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

二項比率 ``k/n`` の点推定と信頼限界を返す(``table``)。

``sides`` は ``"two"``(両側)、``"lower"``(片側下限)、``"upper"``
(片側上限)、``method`` は ``"clopper_pearson"``、``"wilson"``、
``"jeffreys"``。返り値は ``estimate``、``lower``、``upper``、``method``、
``confidence``、``sides``、``k``、``n`` を持つ。保証・合否判定には正確で
保守的な Clopper--Pearson、推定には Wilson / Jeffreys を使い分ける。

``k=0`` / ``k=n`` も有限の限界を返す。たとえば 10/10 の 95 % 片側
下限は 0.7411、0/20 の片側上限は 0.1391 である。

空の入力(``n=0``)は ``ValueError`` を返す(理由: 比率を定義できない)。
拒否(``ValueError``): 非整数の ``k`` / ``n``、``0 <= k <= n`` 違反、
``confidence`` が (0, 1) 外、未知の ``sides`` / ``method``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [proportion_interval_audit](../../../../examples/proportion_interval_audit.py) — `py -3.11 examples/proportion_interval_audit.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`pod`)

[trials_for_all_success](trials_for_all_success.md) · [pod_ahat_fit](pod_ahat_fit.md) · [pod_from_ahat](pod_from_ahat.md) · [pod_hitmiss_fit](pod_hitmiss_fit.md) · [pod_false_call](pod_false_call.md) · [pod_decision_tradeoff](pod_decision_tradeoff.md)

---
*Provenance: pod.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

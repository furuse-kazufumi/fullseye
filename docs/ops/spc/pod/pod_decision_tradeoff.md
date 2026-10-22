---
op: pod_decision_tradeoff
dim: spc
category: pod
in: table × signal
out: table
examples: [poc_pod_lighting]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# pod_decision_tradeoff — SPC `pod` op

- **データ種**: `table × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pod_decision_tradeoff(fit, noise, a_dec_grid=None, n_grid=25, level=0.95)` (実装を直接呼ぶなら `import pod; pod.pod_decision_tradeoff(fit, noise, a_dec_grid=None, n_grid=25, level=0.95)`、台帳から引くなら `opsspc.get("pod_decision_tradeoff")`)

## 使い方

判定閾値 ``a_dec`` を振ったときの (a50, a90, a90/95, 誤検出確率) の取引表(``table``)。

MIL-HDBK-1823A G.3.6.2.4.1(図 G-28)の数表版。閾値を上げれば誤検出は減り、
同じ回帰から出る a90/95 は大きくなる —— 「どこに閾値を置くか」は統計ではなく
運用の判断で、この表はその判断の材料を並べるだけ(最適点は選ばない)。

*fit* は ``pod_ahat_fit`` の表、*noise* は無欠陥部位の応答(元の â の単位、
座標は *fit* の ``log_response`` に従う)。*a_dec_grid* を省略すると、雑音の
中央値から「雑音の平均 + 6 標準偏差」までを ``n_grid`` 点(対数座標なら等比)。
各行は ``pod_from_ahat`` と ``pod_false_call`` を同じ閾値で呼んだものと一致する。

返り: 列 ``a_dec`` ``a50`` ``a90`` ``a90_95`` ``pfp_normal`` ``pfp_empirical``
``pfp50`` ``pfp95``(すべて長さ ``n_grid`` か ``len(a_dec_grid)``)。

空の入力(``fit`` が空の dict)は ValueError。
拒否(``ValueError``): ``pod_ahat_fit`` の表でない・``β1`` が 0 と区別できない、雑音が空・定数・
非有限、閾値が非有限(対数座標で 0 以下)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pod_lighting](../../../../examples/poc_pod_lighting.py) — `py -3.11 examples/poc_pod_lighting.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`pod`)

[pod_ahat_fit](pod_ahat_fit.md) · [pod_from_ahat](pod_from_ahat.md) · [pod_hitmiss_fit](pod_hitmiss_fit.md) · [pod_false_call](pod_false_call.md)

---
*Provenance: pod.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

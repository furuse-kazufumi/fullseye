---
op: pod_false_call
dim: spc
category: pod
in: signal
out: table
examples: [poc_pod_lighting, poc_sam_hybrid_bonding_voids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# pod_false_call — SPC `pod` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pod_false_call(noise, a_dec, log_response=False)` (実装を直接呼ぶなら `import pod; pod.pod_false_call(noise, a_dec, log_response=False)`、台帳から引くなら `opsspc.get("pod_false_call")`)

## 使い方

無欠陥部位の応答 ``noise`` と判定閾値 ``a_dec`` から誤検出確率(``table``)。

判定は ``â > a_dec`` で「検出」(POD と同じ規則)。3 通りで返す:

  * ``pfp_empirical = k/n`` —— 素の比率。
  * ``pfp50`` / ``pfp90`` / ``pfp95`` —— k 回 / n 機会の**二項の片側上限**
    (Clopper–Pearson、``Beta⁻¹(c; k+1, n−k)``)。MIL-HDBK-1823A G.4.6 の
    表 G-I と同じ定義で、0 回でも 0 にはならない(150 機会で 0 回なら
    PFP50 = 0.0046)。1823A は報告とリスク計算に PFP50 を使えと言う。
  * ``pfp_normal`` —— 雑音を正規と見た ``1 − Φ((y_dec − m)/s)``(G.3.5.3、
    ``log_response`` なら対数座標で)。裾の外挿なので、分布の仮定に敏感
    (1823A G.3.4.2 が警告するとおり)。

空の入力(``noise`` が 0 要素)は ValueError。
拒否(``ValueError``): 空・非有限・2 点未満、雑音がすべて同じ値(正規の幅が 0)、
``a_dec`` が非有限(対数座標で 0 以下)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_pod_lighting](../../../../examples/poc_pod_lighting.py) — `py -3.11 examples/poc_pod_lighting.py`
- [poc_sam_hybrid_bonding_voids](../../../../examples/poc_sam_hybrid_bonding_voids.py) — `py -3.11 examples/poc_sam_hybrid_bonding_voids.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md)

## 同カテゴリ(`pod`)

[pod_ahat_fit](pod_ahat_fit.md) · [pod_from_ahat](pod_from_ahat.md) · [pod_hitmiss_fit](pod_hitmiss_fit.md) · [pod_decision_tradeoff](pod_decision_tradeoff.md)

---
*Provenance: pod.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: pod_ahat_fit
dim: spc
category: pod
in: table
out: table
gpu: なし
examples: [poc_pod_lighting, poc_sam_hybrid_bonding_voids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# pod_ahat_fit — SPC `pod` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pod_ahat_fit(table, size='a', response='ahat', log_size=False, log_response=False, censor_low=None, censor_high=None)` (実装を直接呼ぶなら `import pod; pod.pod_ahat_fit(table, size='a', response='ahat', log_size=False, log_response=False, censor_low=None, censor_high=None)`、台帳から引くなら `opsspc.get("pod_ahat_fit")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

â vs a の回帰を、左右の打ち切りつき最尤法で当てる(``table``)。

モデル(MIL-HDBK-1823A G.3.4)は ``y = β0 + β1 x + ε, ε ~ N(0, σ²)``、
``x = a`` または ``ln a``、``y = â`` または ``ln â``。応答が ``censor_low`` 以下の
行は**左打ち切り**(雑音床に埋もれて「それ以下だった」としか分からない)、
``censor_high`` 以上の行は**右打ち切り**(飽和)として、対数尤度に
``ln Φ((y_L − μ_i)/σ)`` / ``ln Φ((μ_i − y_H)/σ)`` で入る(Tobin 1958)。

最大化は Olsen(1978)の座標 ``(γ, θ) = (β/σ, 1/σ)`` でのニュートン法 ——
そこでは対数尤度が大域的に凹なので、解は一意で初期値に依らない。共分散は
観測情報行列の逆を ``(β0, β1, σ)`` へ写したもの(最尤点では勾配が 0 なので
ヤコビアンで厳密に写る)。

★打ち切りが 1 つも無ければ、最尤解は**最小二乗そのもの**: β は ``np.polyfit``
と一致し、σ は ``sqrt(RSS/n)``(n で割る最尤推定。``n − 2`` ではない)。
★比較のため、打ち切りを無視して記録値のまま最小二乗した ``ols_beta0`` /
``ols_beta1`` / ``ols_sigma`` も返す —— 打ち切りの多いデータでは傾きが寝て
σ が縮む(このモデルが要る理由)。

返り: ``beta0`` ``beta1`` ``sigma`` ``cov``(3x3、並びは ``param_names``)、
``n`` ``n_left`` ``n_right`` ``n_censored`` ``loglik`` ``iterations``、座標の印
``log_size`` ``log_response``、打ち切り閾値、大きさの範囲 ``size_min`` / ``size_max``、
当てに使った ``x`` ``y`` ``status``(-1 左 / 0 観測 / +1 右)。

空の入力(``table`` が 0 行、または空の dict)は ValueError。
拒否(``ValueError``): 空の表・列の欠け・長さ違い・非有限・文字列、観測(打ち切り
でない)が 3 点未満か大きさが 1 種類しかない、応答が定数で散らばりが 0
(POD が階段になりモデルが立たない)、``censor_low >= censor_high``、対数座標で 0 以下。

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

[proportion_interval](proportion_interval.md) · [trials_for_all_success](trials_for_all_success.md) · [pod_from_ahat](pod_from_ahat.md) · [pod_hitmiss_fit](pod_hitmiss_fit.md) · [pod_false_call](pod_false_call.md) · [pod_decision_tradeoff](pod_decision_tradeoff.md)

---
*Provenance: pod.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

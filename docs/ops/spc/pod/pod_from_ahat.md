---
op: pod_from_ahat
dim: spc
category: pod
in: table
out: table
examples: [poc_pod_lighting, poc_sam_hybrid_bonding_voids]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# pod_from_ahat — SPC `pod` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.pod_from_ahat(fit, a_dec, level=0.95, n_grid=200, a=None)` (実装を直接呼ぶなら `import pod; pod.pod_from_ahat(fit, a_dec, level=0.95, n_grid=200, a=None)`、台帳から引くなら `opsspc.get("pod_from_ahat")`)

## 使い方

â vs a の回帰と判定閾値 ``a_dec`` から POD(a) 曲線と a50 / a90 / a90/95(``table``)。

判定は ``â > a_dec`` で「検出」。回帰 ``y = β0 + β1 x + ε`` のもとで
``POD(x) = Φ((x − μ)/σ_pod)``、``μ = (y_dec − β0)/β1``、``σ_pod = σ/β1``
(MIL-HDBK-1823A G.3.4.3。``y_dec`` は ``a_dec`` を回帰の y 座標へ写したもの)。
``a50 = μ``、``a90 = μ + z_0.9 σ_pod``(``z_0.9 = 1.281552``)を元の単位へ戻す。

a90/95 はデルタ法: ``(β0, β1, σ)`` の共分散をヤコビアン
``∂(μ, σ_pod)/∂(β0, β1, σ)`` で写し、``x90 + z_level · sqrt(vμ + z_0.9² vσ + 2 z_0.9 c)``。
``level`` は片側の信頼水準(既定 0.95 → ``z = 1.644854``)。

曲線の下限 ``pod_lower`` は「各 POD 水準 p の大きさ a_p の上限」をつないだ線
(水平方向のデルタ法)。だから下限が 0.9 を横切る大きさは a90/95 と**一致する**。
``bound_monotone`` が False のとき(``σ_pod`` が自分の標準誤差の z 倍に届かない =
データが少なすぎる)下限曲線は 1 価にならず、読まないこと。

★``a90_95_beyond_data`` が True のとき、a90/95 は**試した最大の大きさより先**にある
—— 回帰の直線を試験の外へ延ばした外挿で、1823A が「データの外で POD を語るな」と
いう領域。数は返すが、その数で合否を決めてはいけないことを旗で同伴させる
(PoC の暗視野照明: 試した最大 300 µm に対し a90/95 = 5,952 µm)。

*a* を渡すとその大きさで曲線を評価する。省略時は当てに使った大きさの範囲を
少し広げた ``n_grid`` 点(対数座標なら等比)。

空の入力(``fit`` が空の dict)は ValueError。
拒否(``ValueError``): ``pod_ahat_fit`` の表でない、``β1 <= 0``(応答が大きさとともに
増えない = 検出曲線が無い)、``β1`` が自分の標準誤差の ``z_level`` 倍以下(増えると
言えない —— その傾きで割った a50 は 10^12 µm のような数になる)、``a_dec`` が
非有限(対数座標で 0 以下)、``level`` が (0.5, 1) の外。

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

[pod_ahat_fit](pod_ahat_fit.md) · [pod_hitmiss_fit](pod_hitmiss_fit.md) · [pod_false_call](pod_false_call.md) · [pod_decision_tradeoff](pod_decision_tradeoff.md)

---
*Provenance: pod.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: msa_gauge_rr
dim: spc
category: msa
in: table
out: table
examples: [poc_measurement_system_analysis]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# msa_gauge_rr — SPC `msa` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.msa_gauge_rr(table, part='part', operator='operator', value='value', tolerance=None, pool_interaction='auto', pool_alpha=0.25)` (実装を直接呼ぶなら `import spc; spc.msa_gauge_rr(table, part='part', operator='operator', value='value', tolerance=None, pool_interaction='auto', pool_alpha=0.25)`、台帳から引くなら `opsspc.get("msa_gauge_rr")`)

## 使い方

分散分析法によるゲージ R&R(``table``)。

繰り返し性 EV(同じ人が同じ物を測り直したときの散らばり)、再現性 AV(人が
変わったときの散らばり。交互作用を含む)、その合成 GRR、部品間 PV、総変動 TV、
``%GRR = 100 GRR/TV``、区別できる階級数 ``ndc = 1.41 PV/GRR``。

*tolerance* を渡すと公差に対する比 ``%tolerance = 100 GRR/tolerance`` も返す。

★分散成分は**釣り合った交差計画の期待平均平方**から出す:

    var_repeat = MS_err
    var_inter  = (MS_inter - MS_err) / r
    var_oper   = (MS_oper - MS_inter) / (p r)
    var_part   = (MS_part - MS_inter) / (o r)

★★**負の分散成分は 0 に丸めるが、丸めたことを隠さない**(``clamped`` 列)。
期待平均平方の差は推定量なので、真の成分が 0 に近いと負になりうる。黙って 0 に
すると「測定者差は無い」と読めてしまうが、正しくは「**推定できなかった**」。
しかもこれは稀な端ではない —— 部品 60 x 測定者 4 x 繰り返し 5 で測定者差を
**厳密に 0** にした合成データを種 40 本で回すと、**31 本**で再現性成分が負に出る
(実測 2026-09-23)。丸めを申告しない実装は、この 31 本すべてで「差が無い」と
言い切ってしまう。

★推定量の揺れも隠さない。同じ 60x4x5 で真値 0.4 の繰り返し性は種 40 本で
平均 0.39710・標準偏差 0.00788 に出る —— 理論の ``sigma/sqrt(2 df)``
(df = 960 で 0.00913)と同じ桁で、**1 本の種を 1 % の精度で信じてはいけない**。
再現性はもっと悪く、測定者 4 人(自由度 3)からの推定なので真値 0.5 に対して
標準偏差 0.159 —— 桁が合えば上等という量である。

★★**交互作用を残すか、誤差にプールするかで答えが変わる**。規格の手順は
「交互作用の F 検定が有意でなければ交互作用項を落として再計算する」で、
*pool_interaction* がその選択:

  * ``"auto"``(既定)—— 交互作用の p 値が *pool_alpha*(既定 0.25)を**超えたら**
    プールする。

★★**0.25 は規格が明記した数ではない**。参考マニュアル本文が言うのは
「交互作用を見落とす危険を下げるため**高い有意水準を選べ**」という定性的な指示
だけで、数値は書かれていない。0.25 はソフトウェア側の慣行の多数派で、
別の実装は 0.05 を既定にしている。α を**大きく**すると `p > alpha` が成りにくく
なる = **交互作用を残しやすい**ので、0.25 は本文の方針に忠実な(保守的な)側。
一方で規格の worked example の表は脚注に「α = 0.05 で判定」と書いてあるので、
**その表を再現すると名乗る検査は `pool_alpha=0.05` を明示して通すべき**である
(既定値の話と、公表例題の再現条件の話は別)。この例題では F = 0.434 が
どちらの α でも非有意なので結果は変わらないが、境界付近のデータでは既定の違いが
EV / AV を数 % 動かす —— 実測でモデル切替は EV を 7.3 % 動かした。
  * ``False`` —— 常に交互作用を残す。
  * ``True`` —— 常にプールする。

返りの ``interaction_pooled`` / ``interaction_p`` / ``pool_alpha`` に**どちらを
使ったかを必ず載せる**。黙って切り替えると、同じ道具が同じ工程について別の数字を
返し、その理由が出力のどこにも残らない。

★実測(規格の例題、10 部品 x 3 測定者 x 3 回の 90 点): 交互作用を残すと
EV = 0.214435、プールすると EV = 0.199933 —— **7.3 % 違う**。選択は p 値の
閾値で決まるので、データがわずかに動けばモデルが飛ぶ。この例題では
``F = 0.4337 / p = 0.9741`` と交互作用がまったく効いていないため、規格は
プールした側を公表値にしている(その値をこの実装は 3e-7 で再現する)。

★門にできる厳密な関係: ``TV^2 == GRR^2 + PV^2`` と ``GRR^2 == EV^2 + AV^2``
(定義そのもの)、寄与率の合計 100 %、そして**測定者が 1 人のときの EV は
升目ごとの標本分散の平均に厳密に一致する**(numpy が真値になる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](msa_anova_table.md) · [msa_bias_linearity](msa_bias_linearity.md) · [msa_attribute_agreement](msa_attribute_agreement.md) · [gum_standard_uncertainty](../uncertainty/gum_standard_uncertainty.md) · [gum_propagate](../uncertainty/gum_propagate.md) · [gum_expanded](../uncertainty/gum_expanded.md) · [gum_monte_carlo](../uncertainty/gum_monte_carlo.md) · [gum_validate](../uncertainty/gum_validate.md)

## 同カテゴリ(`msa`)

[msa_anova_table](msa_anova_table.md) · [msa_bias_linearity](msa_bias_linearity.md) · [msa_attribute_agreement](msa_attribute_agreement.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

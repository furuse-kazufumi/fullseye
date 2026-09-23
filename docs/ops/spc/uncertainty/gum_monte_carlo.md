---
op: gum_monte_carlo
dim: spc
category: uncertainty
in: table
out: table
examples: [poc_measurement_system_analysis]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# gum_monte_carlo — SPC `uncertainty` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gum_monte_carlo(table, u='u', sensitivity='sensitivity', n=200000, seed=0, level=0.95, correlation=None, distribution=None, value=None, power=None)` (実装を直接呼ぶなら `import spc; spc.gum_monte_carlo(table, u='u', sensitivity='sensitivity', n=200000, seed=0, level=0.95, correlation=None, distribution=None, value=None, power=None)`、台帳から引くなら `opsspc.get("gum_monte_carlo")`)

## 使い方

GUM 補遺 1(JCGM 101)のモンテカルロ伝播(``table``)。

各入力量を分布から引いて ``y = sum_i c_i x_i`` を作り、標本から標準不確かさと
最短の包含区間を返す。既定は正規分布で、*distribution* に列名を渡すと
``gum_standard_uncertainty`` と同じ形の名前(rectangular / triangular / ...)を
成分ごとに指定できる(半幅ではなく**標準不確かさ**を持つ分布を作る)。

*value* と *power* に列名を渡すと **冪モデル** を回す:

    y = sum_i c_i (x_i + e_i)^{p_i}

(``e_i`` が分布から引いた揺らぎ。既定は ``x_i = 0`` / ``p_i = 1`` = 線形。)
冪までに絞ったのは、台帳に載る op は**宣言的**でなければならず、任意の関数を
受け取れないため —— それでも規格の非線形の例(二乗の和)はこれで表現でき、
伝播則が破綻する場面を再現できる。

★これは ``gum_propagate`` の**独立な検算**である。伝播則は偏微分と分散の代数、
こちらは乱数の標本 —— 導出も実装も別なので、線形モデルでは
``u_mc -> u_c``(1/sqrt(n) の速さ)に近づくはずで、近づかなければどちらかが
壊れている。相関は Cholesky 分解で入れるので、伝播則の相関項とは別の経路を通る。

★★**非線形では両者が食い違うのが正しい**。規格の例(比較損失
``dY = X1^2 + X2^2``、各 ``u = 0.005``)を ``x1 = x2 = 0`` で回すと:

    伝播則   感度 ``c_i = 2 x_i`` が**両方 0** になるので ``u_c = 0``、区間 [0, 0]
    モンテカルロ  ``dy = 50e-6``、``u = 50e-6``、区間 ``[0, 150e-6]``

伝播則は「不確かさゼロ」と答える —— これは実装の誤りではなく、**1 次近似が
極値で情報を失う**という手法そのものの限界。こういう場面があるから補遺 1 の
モンテカルロが要る。``x1 = 0.010`` では伝播則の区間が ``[-96, +296]e-6`` と
**負の損失**を含み(物理的にありえない)、``x1 = 0.050`` まで離れると
``[1520, 3480]`` 対 ``[1590, 3543]`` と近づく。

★★**正規分布でない入力では、包含区間は ``k u_c`` と一致しない**。矩形分布を
足し合わせると中心極限定理で正規に近づくが、成分が 1 つだけなら最短 95 % 区間の
半幅は **``0.95 a``**(支持の端 ``a`` ではない —— 95 % ぶんの幅しか要らない)で、
``k u = 1.96 a/sqrt(3) = 1.1316 a`` より**狭い**。比は
``1.959964/(sqrt(3) x 0.95) = 1.1911`` という閉形式で、実測 1.1914。
これは欠陥ではなく**伝播則が分布の形を捨てている**ことの現れなので、両方返して
読み手に見せる(この 0.95 を最初 ``a`` と思い込んで門を誤らせた)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](gum_standard_uncertainty.md) · [gum_propagate](gum_propagate.md) · [gum_expanded](gum_expanded.md) · [gum_validate](gum_validate.md)

## 同カテゴリ(`uncertainty`)

[gum_standard_uncertainty](gum_standard_uncertainty.md) · [gum_propagate](gum_propagate.md) · [gum_expanded](gum_expanded.md) · [gum_validate](gum_validate.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

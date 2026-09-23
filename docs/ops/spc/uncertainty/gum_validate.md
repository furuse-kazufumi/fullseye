---
op: gum_validate
dim: spc
category: uncertainty
in: table × table
out: table
examples: [poc_measurement_system_analysis]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# gum_validate — SPC `uncertainty` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gum_validate(guf, mcm, ndig=2)` (実装を直接呼ぶなら `import spc; spc.gum_validate(guf, mcm, ndig=2)`、台帳から引くなら `opsspc.get("gum_validate")`)

## 使い方

モンテカルロの結果で伝播則の結果を**検証**する(``table``)。

*guf* は ``gum_expanded``(``estimate`` を渡して区間を出したもの)、*mcm* は
``gum_monte_carlo`` の返り。手続きは規格 8.1.3 のとおり:

  1. ``u(y)`` に対応する**数値許容差** ``delta`` を作る。``z`` を
     ``c x 10^l``(``c`` は *ndig* 桁の整数)の形に書いたとき ``delta = 0.5 x 10^l``。
  2. ``dlow = |y - U - y_low|`` と ``dhigh = |y + U - y_high|`` を求める
     —— 比べるのは**カバレッジ区間の端点**であって ``U`` そのものではない。
  3. 両方が ``delta`` 以下なら、そのインスタンスで伝播則は検証されたとする。

★**「一致した」と「一致すべきだった」を混同しない**。この op が返すのは
*ndig* 桁で見たときの一致であって、真偽ではない。*ndig* を上げれば同じ数字でも
不一致になる —— 実測(加法モデル、矩形入力、端点差 0.04):

    ndig=1 -> delta 0.5    一致
    ndig=2 -> delta 0.05   一致(きわどい)
    ndig=3 -> delta 0.005  **不一致**

つまり ndig は「どこまでの桁を主張するか」であり、**主張を強くすれば伝播則は
検証に落ちる**。既定の 2 は規格が典型と述べる値(1 か 2)の上側。

★★**出力が対称なとき**、端点で比べるのは幅で比べるより本質的に厳しい。最短区間の
幅 ``W(a) = F(a+w) - F(a)`` は対称分布の中央で ``W' = 0`` かつ曲率が小さい
**平らな谷**になるので、幅は精度よく決まるのに ``argmin``(位置)が定まらない。
4 成分の加法モデル(正規)で種 12 本ずつ測った実測:

    n           半幅の標準偏差      区間の中心の標準偏差   比
    200,000     0.0054              0.0284                 5.2
    1,000,000   0.0035              0.0146                 4.1
    5,000,000   0.0011              0.0114                10.0

★**これは対称(または近対称)の出力に限った話**である。歪んだ出力では最適点が
一意に強く決まるので位置も普通に ``1/sqrt(n)`` で収束する —— 同じ測り方で
二乗の和(強い歪み)を測ると **位置 sd / 幅 sd の比は 1.0**(n=200,000 でも
n=1,000,000 でも)。規格の比較損失の例でモンテカルロが公表値に素直に乗るのは
そのため。

したがって ``dlow`` / ``dhigh`` が大きいとき、**出力が対称なら**それは伝播則の
誤りではなくモンテカルロの位置決めの揺れであることが多い。理論上は厳密に
一致するはずの正規入力でも ``ndig=3``(``delta=0.005``)は n=5,000,000 で
5 本中 2 本しか通らない。

★区間の推定器そのものに偏りは無い。1 成分・正規の厳密解(半幅 1.959964)に対し
実測の偏りは n=50,000 で −0.0060、n=5,000,000 で **−0.000008** まで縮み、
標準偏差も ``1/sqrt(n)`` に従う(0.0086 → 0.0009)。

★検証用のモンテカルロは ``delta/5`` の精度まで回すことが規格の推奨で、試行数の
目安は ``M >= 10^4 / (1 - p)``(95 % なら 2 x 10^5)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](gum_standard_uncertainty.md) · [gum_propagate](gum_propagate.md) · [gum_expanded](gum_expanded.md) · [gum_monte_carlo](gum_monte_carlo.md)

## 同カテゴリ(`uncertainty`)

[gum_standard_uncertainty](gum_standard_uncertainty.md) · [gum_propagate](gum_propagate.md) · [gum_expanded](gum_expanded.md) · [gum_monte_carlo](gum_monte_carlo.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

---
op: gum_propagate
dim: spc
category: uncertainty
in: table
out: table
examples: [poc_measurement_system_analysis]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# gum_propagate — SPC `uncertainty` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gum_propagate(table, u='u', sensitivity='sensitivity', correlation=None)` (実装を直接呼ぶなら `import spc; spc.gum_propagate(table, u='u', sensitivity='sensitivity', correlation=None)`、台帳から引くなら `opsspc.get("gum_propagate")`)

## 使い方

不確かさの伝播則(GUM 5.2、相関つき)(``table``)。

    u_c^2 = sum_i (c_i u_i)^2 + 2 sum_{i<j} c_i c_j u_i u_j r_ij

*table* は列 *u*(標準不確かさ)と *sensitivity*(感度係数 ``c_i = df/dx_i``)を
持つ表。*correlation* に (n, n) の相関行列を渡すと相関項を含める。

★門にできる閉形式: ``f = x y`` なら ``c_x = y`` / ``c_y = x`` なので
``u_c/|f| = sqrt((u_x/x)^2 + (u_y/y)^2)`` —— 相対不確かさの二乗和。
相関 ``r = +1`` の 2 成分では ``u_c = |c1 u1 + c2 u2||`` に**厳密に**一致し、
``r = -1`` では ``|c1 u1 - c2 u2|``(打ち消し)。無相関なら寄与の合計が
``u_c^2`` にぴったり閉じる。

★★**相関を無視した誤りの向きは一定ではない**。「独立として扱うと過小評価になる」
はよく言われるが、**偽である**。規格の worked example(電圧・電流・位相差から
抵抗とリアクタンスを同時に出す例、3 量すべてに相関がある)で相関を落として測ると:

    u_c(R)  0.0702 -> 0.1945   **2.8 倍の過大**
    u_c(X)  0.2961 -> 0.2009   過小
    u_c(Z)  0.2367 -> 0.2041   過小

同じ 1 つのデータで、量によって向きが逆に出る —— 感度係数の符号と相関の符号の
積で決まるので、当たり前といえば当たり前だが、「安全側に外れる」と思って相関を
省くと **R では 3 倍近く過大な不確かさを報告**することになる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_measurement_system_analysis](../../../../examples/poc_measurement_system_analysis.py) — `py -3.11 examples/poc_measurement_system_analysis.py`

## 型が繋がる次の op(`table` を入力に取れる)

[msa_anova_table](../msa/msa_anova_table.md) · [msa_gauge_rr](../msa/msa_gauge_rr.md) · [msa_bias_linearity](../msa/msa_bias_linearity.md) · [msa_attribute_agreement](../msa/msa_attribute_agreement.md) · [gum_standard_uncertainty](gum_standard_uncertainty.md) · [gum_expanded](gum_expanded.md) · [gum_monte_carlo](gum_monte_carlo.md) · [gum_validate](gum_validate.md)

## 同カテゴリ(`uncertainty`)

[gum_standard_uncertainty](gum_standard_uncertainty.md) · [gum_expanded](gum_expanded.md) · [gum_monte_carlo](gum_monte_carlo.md) · [gum_validate](gum_validate.md)

---
*Provenance: spc.py — SPC operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.

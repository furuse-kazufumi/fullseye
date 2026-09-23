---
id: measurement-system-and-uncertainty
title: その数字のうち、いくつが測り方のものか(ゲージ R&R と測定の不確かさ)
title_en: How much of that number is your measuring, not your process (gauge R&R and measurement uncertainty)
category: 測る
ops: [msa_anova_table, msa_gauge_rr, msa_bias_linearity, msa_attribute_agreement, gum_standard_uncertainty, gum_propagate, gum_expanded, gum_monte_carlo, gum_validate, spc_capability, spc_xbar_r]
examples: [poc_measurement_system_analysis]
version: 0.2.3
---

# その数字のうち、いくつが測り方のものか(ゲージ R&R と測定の不確かさ)

## できること

工程のばらつきを見る管理図も工程能力も、**測定のばらつきを含んだままの数字**を見ています。この層はそれを分けます —— 総変動のうち何割が部品どうしの差で、何割が「測るという行為」の差なのか。そして 1 回の測定について、成分ごとの不確かさを合成して報告可能な形にします。

どれも閉形式の規格モデルで、**照合できる厳密な恒等式**を持ちます。使った式でそのまま答え合わせをする op は 1 つも入れていません。

- ★**分散分析の平方和は代数的な恒等式で閉じます** —— `SS_total = SS_部品 + SS_測定者 + SS_交互作用 + SS_誤差` が**相対差 1e-16**。分散成分をどう導こうと必ず成り立つので、推定の正しさとは別の層で実装を押さえられます。自由度も同じく閉じます。
- ★**繰り返し性は numpy が真値になります** —— 期待平均平方から導いた `var_repeat = MS_err` は、釣り合った設計では「各升目の `np.var(ddof=1)` の平均」に**代数的に等しい**。導出も実装も別なので、片方が壊れれば一致しません。
- ★★**規格の worked example(10 部品 × 3 測定者 × 3 回の 90 点)を再現します**。EV 0.199933 / AV 0.226838 / GRR 0.302372 / PV 1.042327 —— いずれも**公表値と 1.5e-06 以内**。寄与率 3.4 / 4.4 / 7.8 / 92.2 % は完全一致。これは**外の権威が出した答え**で、こちらの導出とは独立に印刷されている数字です。
- ★★**交互作用を残すかプールするかで答えが 7.3 % 動きます**。規格の手順は「交互作用の F 検定が有意でなければ交互作用項を落として再計算する」で、例題は `F = 0.434 / p = 0.9741` とまったく効いていないためプールした値を公表しています。残すと EV は 0.214435、プールすると 0.199933。**どちらを使ったかを必ず返します**(`interaction_pooled` / `interaction_p` / `pool_alpha`)—— 黙って切り替えると、同じ道具が同じ工程について別の数字を返し、理由が出力のどこにも残りません。なお閾値 0.25 は**規格が明記した数ではなく**、本文の「高い有意水準を選べ」という定性的指示に沿ったソフトウェア慣行の多数派です(例題の表は α=0.05 で判定しています)。
- ★★**負の分散成分は稀な端ではなく、普通に起きます**。測定者差を**厳密に 0** にした合成データを種 40 本で回すと、**31 本**で再現性成分が負に出ます。0 に丸めるのは妥当ですが、**丸めたことを申告しない実装は「差は無い」と言い切ります** —— 正しくは「推定できなかった」。`clamped` 列がその申告です。
- ★**推定量の揺れも隠しません**。60 × 4 × 5 で真値 0.4 の繰り返し性は種 40 本で平均 0.39710・標準偏差 0.00788(理論 `σ/√(2·df)` は df=960 で 0.00913)。再現性は測定者 4 人(自由度 3)からの推定なので真値 0.5 に対し標準偏差 0.159 —— **桁が合えば上等**という量です。
- ★**釣り合っていない表は拒みます**。分散成分は釣り合った交差計画の期待平均平方から導くので、欠測のある表を黙って受けると式は動くが**別の量**を返します。
- ★**カッパは一致率ではありません**。合格率 95 % の工程ではでたらめに判を押しても素の一致率は 9 割近くになります —— 実測で一致率 0.850 に対しカッパ 0.037。`(p_o − p_e)/(1 − p_e)` で偶然の一致を割り引いた残りを返し、2×2 の閉形式 `2(ad−bc)/((a+b)(b+d)+(a+c)(c+d))` と 1e-12 で一致します。
- ★**分布の形から標準不確かさへ直す除数は、分散の定義から出る厳密値です** —— 矩形 `a/√3`・三角 `a/√6`・U 字 `a/√2`・95 % 区間 `a/1.959964`。**既定の分布を置きません**: 一番よく使うからと矩形を既定にすると、形を書き忘れた成分が黙って `a/√3` になり、三角のつもりなら 1.41 倍ずれた不確かさが例外を出さずに下流へ流れます。
- ★★**「相関を無視すると過小評価」は偽です**。規格の worked example(電圧・電流・位相差から抵抗とリアクタンスを同時に出す例)で相関行列を落とすと、`u_c(R)` は 0.0702 → **0.1945(2.8 倍の過大)**、`u_c(X)` は 0.2961 → 0.2009(過小)。**同じ 1 つのデータで量によって向きが逆に出ます** —— 感度係数の符号と相関の符号の積で決まるからです。R / X / Z の値そのもの(127.732 / 219.847 / 254.260 Ω)と `u_c` も公表値と一致します。
- ★**有効自由度は t 表を引く直前に切り捨てます**(規格の要求)。端度器校正の例題で `ν_eff = 16.64` を切り捨てずに引くと `k = 2.1132`、切り捨てて 16 で引くと **2.1199** —— 公表値は後者。0.3 % の差ですが、拡張不確かさは報告書に載る数字です。切り捨て前の値も返します。
- ★**`ν_eff ≥ min νᵢ` は定理です**(`Σuᵢ⁴/νᵢ ≤ (1/ν_min)Σuᵢ⁴ ≤ (1/ν_min)(Σuᵢ²)²`)。破れたら計算が壊れています。全成分が無限自由度なら `k` は正規の分位点 1.959964 に収束します。
- ★★**モンテカルロは伝播則の独立な検算です**(代数 vs 標本)。線形モデルでは一致し、**非線形では食い違うのが正しい**。規格の比較損失 `δY = X₁² + X₂²` を `x₁ = x₂ = 0` で評価すると、感度 `cᵢ = 2xᵢ` が両方 0 になるので伝播則は `u_c = 0` / 区間 `[0, 0]` を返します —— 実装の誤りではなく**1 次近似が極値で情報を失う**という手法の限界で、同じ状況でモンテカルロは `δy = 50e-6` / `u = 50e-6` / `[0, 150e-6]`。`x₁ = 0.010` では伝播則の区間が `[-96, +296]e-6` と**負の損失**を含みます。
- ★★**破綻は警告でなく構造で返します**(`guf_valid` / `invalid_reasons`)。`u_c = 0` を黙って返すのが最悪で、呼んだ側は「測定が完璧だった」と読みます。検出は 2 つ —— 感度がすべて 0 の**停留点**と、区間が定義域を出る**非実現区間**。後者は**境界を渡されたときだけ**検査します(「損失だから非負」は呼ぶ側しか知らない情報で、既定で 0 を下限と仮定すると負を取れる量で誤検出します)。なお**この検出条件そのものは本実装の判断**で、規格が列挙しているのは線形 3 条件・非線形 5 条件のほうです。
- ★★**4 つの矩形分布の和には厳密解があります**。各 `u = 1` なら `a = √3` で、和はスケールした Irwin–Hall(4)。`F(s) = s⁴/24` を反転して **`y_2.5% = √3(2·0.6^(1/4) − 4) = −3.879407`** —— 乱数を 1 つも使わない真値です。伝播則は正規近似の `1.959964σ` を使うので `3.919928`、真値は `1.939703σ` で `3.879407`、差 **0.040521**。Irwin–Hall(4) の超過尖度は `−6/(5n) = −0.3` で正規より裾が薄いため、正規近似は**構造的に広く出ます**。
- ★★**「検証に落ちた」と「伝播則が誤り」は別物です**。規格の検証手続き(`u(y)` を ndig 桁で表したときの数値許容差 `δ` と**区間の端点**を比べる)で、正規入力は理論上厳密に一致するのに `ndig=3`(`δ=0.005`)では落ちます —— 最短区間は対称な分布では幅が**平らな谷**を持つので幅は精度よく決まるのに**位置が定まらない**からです。実測の位置 sd / 幅 sd は対称で 5.2〜4.1、**歪んだ出力では 1.0**(そちらでは位置も普通に収束します)。一方、矩形の例の不一致は**手法そのものの誤差**(0.040521 は `δ` の 8 倍)。**同じ「落ちた」でも原因が逆**で、厳密解が無ければ区別できませんでした。

## What it does

Separate how much of a number comes from the parts and how much from the act of measuring, then combine the components of a single measurement into a reportable uncertainty. Every operator is a closed-form standards model with an exact identity to check it against. The analysis-of-variance decomposition closes algebraically (`SS_total = SS_part + SS_operator + SS_interaction + SS_error`, relative difference 1e-16); repeatability equals the mean of the per-cell `np.var(ddof=1)` that numpy computes independently; the published worked example (10 parts x 3 operators x 3 trials) is reproduced to 1.5e-06 on EV/AV/GRR/PV with contribution percentages 3.4/4.4/7.8/92.2 exactly. Whether the interaction is kept or pooled into error moves EV by **7.3 %**, so the model actually used is reported (`interaction_pooled`, `interaction_p`), and a negative variance component — which happens in **31 of 40** synthetic runs when the true component is zero — is clamped to zero but declared rather than hidden. On the uncertainty side: the divisors that turn a distribution shape into a standard uncertainty are exact (`a/sqrt(3)`, `a/sqrt(6)`, `a/sqrt(2)`); ignoring correlation errs in **both directions on the same data** (u_c of resistance 0.0702 -> 0.1945, a 2.8x overestimate, while reactance goes the other way); the effective degrees of freedom are truncated immediately before the t lookup as the standard requires (16.64 -> 16 gives k = 2.1199, matching the published 2.12); and the propagation law's breakdown at a stationary point is returned as structure (`guf_valid`, `invalid_reasons`) rather than as a silent `u_c = 0`. A sum of four rectangular distributions has an exact coverage interval via Irwin-Hall, `sqrt(3)(2 x 0.6^(1/4) - 4) = -3.879407`, against which the propagation law is structurally 0.040521 too wide.

## 向くところ / 向かないところ

- **不釣り合いな計画・入れ子計画**は扱いません(拒みます)。分散成分は釣り合った交差計画の期待平均平方から導いています。
- **任意の関数の不確かさ伝播**はできません。伝播則は感度係数を受け取る形、モンテカルロは `y = Σ cᵢ (xᵢ + εᵢ)^{pᵢ}` の**冪モデル**までです —— 台帳に載る op は宣言的でなければならず、呼び出し可能オブジェクトを受け取れないためです(規格の非線形の例はこれで表現できます)。
- **出力どうしの相関**(同じ入力から複数の量を出したときの `r(R,X)` など)は返しません。必要なら別の op になります。
- 不確かさの**成分を洗い出すこと自体**は人の仕事です。この層は「並べた成分を正しく合成し、合成が破綻したら申告する」ところから先を引き受けます。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

# その数字のうち、いくつが測り方のものか
t = {"part":     np.repeat([f"P{i}" for i in range(6)], 9),
     "operator": np.tile(np.repeat(["A", "B", "C"], 3), 6),
     "value":    np.random.default_rng(0).normal(10.0, 1.0, 54)}
g = fs.ledger.msa_gauge_rr(t)
print("%%GRR %.1f %% / 区別できる階級数 %.1f / 交互作用を畳んだか %s"
      % (g["pct_grr"][0], g["ndc"][0], bool(g["interaction_pooled"][0])))

# 不確かさ: 分布の形 -> 合成 -> 拡張
u = fs.ledger.gum_standard_uncertainty(
    {"halfwidth": [0.5, 0.2], "distribution": ["rectangular", "triangular"]})
e = fs.ledger.gum_expanded({"u": u["u"], "sensitivity": [1.0, 1.0],
                            "dof": [np.inf, 8.0]}, estimate=10.0)
print("u_c %.4f / k %.3f(nu_eff %.1f を %.0f へ切り捨て)/ U %.4f"
      % (e["u_combined"][0], e["coverage_factor"][0],
         e["dof_effective"][0], e["dof_used"][0], e["expanded"][0]))

# 伝播則が破綻する場所は、黙って 0 を返さず申告する
b = fs.ledger.gum_propagate({"u": [0.005, 0.005], "sensitivity": [0.0, 0.0]})
print("u_c %.1f / 有効か %s / 理由 %s"
      % (b["u_combined"][0], bool(b["guf_valid"][0]), list(b["invalid_reasons"])))
```

## 裏づけ

- op: `msa_anova_table` / `msa_gauge_rr` / `msa_bias_linearity` / `msa_attribute_agreement` / `gum_standard_uncertainty` / `gum_propagate` / `gum_expanded` / `gum_monte_carlo` / `gum_validate`
- 例: [`poc_measurement_system_analysis`](../../examples/poc_measurement_system_analysis.py)
- 既存 op と組む: `spc_capability`(この層の**下流** —— 工程能力は測定のばらつきを含んだ数字を見る)・`spc_xbar_r`(基準器を時間方向に追う安定性)・`mat_eigh`(相関行列の半正定値性)
- 先行: 測定システム解析の参考マニュアル第 4 版(分散分析法のゲージ R&R と worked example); JCGM 100:2008 *Evaluation of measurement data — Guide to the expression of uncertainty in measurement*(伝播則・Welch-Satterthwaite・附属書 H.1/H.2); JCGM 101:2008 *Supplement 1 — Propagation of distributions using a Monte Carlo method*(数値許容差と検証手続き); B. L. Welch, *Biometrika* 34 (1947); F. E. Satterthwaite, *Biometrics Bulletin* 2 (1946); J. Cohen, "A coefficient of agreement for nominal scales", *Educational and Psychological Measurement* 20 (1960); J. L. Fleiss, "Measuring nominal scale agreement among many raters", *Psychological Bulletin* 76 (1971); J. O. Irwin, *Biometrika* 19 (1927) と P. Hall, *Biometrika* 19 (1927)(一様分布の和の厳密な分布)。


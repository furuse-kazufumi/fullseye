---
id: probability-of-detection
title: どの大きさなら見つかるか(検出確率 POD と a90/95、MIL-HDBK-1823A)
title_en: Which flaw size will you actually find (probability of detection and a90/95, MIL-HDBK-1823A)
category: 測る
ops: [pod_ahat_fit, pod_from_ahat, pod_hitmiss_fit, pod_false_call, pod_decision_tradeoff, light_source, detectability_limit]
examples: [poc_pod_lighting]
version: 0.6.1
---

# どの大きさなら見つかるか(検出確率 POD と a90/95、MIL-HDBK-1823A)

## できること

検査の性能を「この大きさの傷は何 % の確率で見つかるか」で言います。欠陥の大きさ `a` と検査系の応答 `â`(あるいは見つけた/見落とした)の組から、POD(a) 曲線・a50・a90・**a90/95**(90 % の確率で見つかると 95 % の信頼で言える最小の大きさ)と、無欠陥部位の応答から誤検出確率を出します。手順は非破壊検査の信頼性評価の公開ハンドブック MIL-HDBK-1823A のとおりです。

- ★**応答の打ち切りを尤度に入れます**。雑音床より下の応答は「それ以下だった」、飽和した応答は「それ以上だった」としか分かりません。これを普通の最小二乗に入れると傾きが寝て σ が縮み、POD が楽観側にずれます。打ち切りつき最尤(Tobit 型、Olsen の座標で対数尤度が凹)は、打ち切りが無ければ**最小二乗そのもの**(`np.polyfit` と 1e-10、σ は `sqrt(RSS/n)`)。68 % が打ち切られたデータでも真値を 3 標準誤差以内で取り戻し、素朴な最小二乗は傾き 0.75(真値 2)まで寝ます。
- ★★**第 2 実装と突き合わせてあります**。打ち切り回帰と 2 値の GLM(logit / probit / cloglog)を、別のパラメータ化(ln σ)と別のアルゴリズム(`scipy.optimize.minimize`)で `scipy.stats` から書き直した尤度で解き直すと、推定値の差は最大 **6.6e-08**。共分散も独立な数値ヘッセ行列と 0.2 % 以内。
- ★★**公表された表を再現します**。1823A G.4.6 の誤検出確率の表(PFP50 / 90 / 95、13 行 39 個)を二項の片側上限で出すと最大差 **7.2e-05**。35 個は 4 桁の丸めの内、4 個は最後の桁が 1 ずれ、そのうち 0 回の 2 行は閉形式 `1 − (1−c)^(1/n)` そのものなので、ずれは表の側と読んでいます(名指しで固定)。
- ★★**a90/95 の被覆率を数えてあります(定理の側から)**。大標本(n=1000、300 回)では a90/95 が真の a90 を上回る割合 **0.943**(名目 0.95、二項誤差の帯の内)。★**小標本では楽観側です**: n=60 で **0.892**。σ の最尤推定が n で割るぶん小さく、a90 が手前に出るためで、規格どおりの手順の性質です。2 値データでは n=80 で Wald **0.836**・尤度比 **0.882**(1823A が尤度比を勧める理由)、n=800 で両方 0.94〜0.96。
- ★**曲線を描けないときは数を返しません**。傾きが負、または正でも標準誤差の z 倍に届かない(応答が大きさとともに増えるとは言えない)ときは `ValueError`。その傾きで割った a50 は 10^12 µm のような数になり、それでも数としては返ってしまうからです。全部検出・全部見落とし・完全分離(最尤の傾きが無限大)も拒みます。
- ★**外挿には旗を立てます**。a90/95 が試した最大の大きさより先なら `a90_95_beyond_data`。
- ★**判定閾値の取引表**(1823A 図 G-28 の数表): 閾値を上げると誤検出は減り、a90 は厳密に増えます。最適点は選びません(運用の判断です)。

## What it does

Probability of detection per MIL-HDBK-1823A: â-vs-a regression with left and right censoring (a Tobit-type maximum likelihood, concave in Olsen's coordinates, reducing exactly to least squares when nothing is censored), the POD(a) curve with a50 / a90 / a90/95 by the delta method, the hit/miss generalised linear model with both Wald and likelihood-ratio a90/95, false-call probability from unflawed sites (binomial one-sided bounds that reproduce the handbook's PFP table to 7.2e-05), and the decision-threshold trade-off. Estimates agree with an independently written likelihood minimised by a different algorithm to 6.6e-08. The delta-method a90/95 covers the true a90 in 94.3 % of large-sample replicates but only 89.2 % at n=60 — reported, not hidden. A slope that cannot be told from zero is refused rather than turned into an absurd a90, and an a90/95 beyond the largest size tested carries a flag.

## 向くところ / 向かないところ

- **1 つの説明変数(大きさ)**のモデルです。プローブ・検査員・材質のような分類変数を入れた回帰や、同じ欠陥を何度も検査した反復測定の扱い(1823A G.3.6 / G.4.4)は入っていません。
- 散らばりは**大きさによらず一定の正規**を仮定します。散らばりが大きさとともに広がるなら対数座標(`log_size` / `log_response`)で揃えてから使ってください。
- 2 値の尤度比の上限は、a90 という 1 つの量に対する**自由度 1 のプロファイル尤度**です。1823A のソフトが描く「(μ, σ) の 2 次元信頼域の包絡線」とは定義が違います。
- 規格の例題データ(EXAMPLE 1〜6)は PDF に載っていないので、**例題の数値とは突き合わせていません**。突き合わせたのは誤検出確率の表だけです。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

# 傷の大きさ a と応答 â(雑音床 0.3 で左打ち切り)
rng = np.random.default_rng(0)
a = np.exp(rng.uniform(np.log(0.1), np.log(2.0), 80))
ahat = np.exp(1.0 + 1.5 * np.log(a) + rng.normal(0.0, 0.4, a.size))
fit = fs.ledger.pod_ahat_fit({"a": a, "ahat": ahat}, log_size=True, log_response=True,
                             censor_low=0.3)
pod = fs.ledger.pod_from_ahat(fit, 1.0)
print("打ち切り %d 点 / a50 %.3f / a90 %.3f / a90/95 %.3f"
      % (fit["n_censored"], pod["a50"], pod["a90"], pod["a90_95"]))

# 無欠陥部位の応答から誤検出確率(0 回でも 0 にはしない)
noise = np.exp(rng.normal(-1.5, 0.4, 150))
fc = fs.ledger.pod_false_call(noise, 1.0)
print("誤検出 %d / %d、PFP50 %.4f" % (fc["n_false"], fc["n"], fc["pfp50"]))
```

## 裏づけ

- op: `pod_ahat_fit` / `pod_from_ahat` / `pod_hitmiss_fit` / `pod_false_call` / `pod_decision_tradeoff`
- 例: [`poc_pod_lighting`](../../examples/poc_pod_lighting.py) —— 同じカメラ・同じ処理で照明だけを変え、ヘアライン金属の V 字の傷を物理で描いて POD を出す。リング仰角 70° の a90/95 は **8.9 µm**、ドーム **27.1 µm**、設計の式の解像度の限界は **202 µm**。当てた a90 の傷を描き直すと実測の検出率は 0.910 / 0.845(0.9 ± 0.064 の帯)。
- 既存 op と組む: `light_source` / `illumdesign`(照明の物理)・`detectability_limit`(分解できる最小の大きさ —— 検出とは別の問い)・`msa_gauge_rr`(測定のばらつき)
- 先行: MIL-HDBK-1823A, *Nondestructive Evaluation System Reliability Assessment*, 2009(Distribution A); J. Tobin, *Econometrica* 26 (1958); R. J. Olsen, *Econometrica* 46 (1978); P. McCullagh & J. A. Nelder, *Generalized Linear Models*, 2nd ed., 1989; C. J. Clopper & E. S. Pearson, *Biometrika* 26 (1934)。

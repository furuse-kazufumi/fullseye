---
id: convergent-forward-models
title: 多重反射・多重散乱・反復を収束まで回す —— 収束した証拠と残りの誤差を返し、収束しなければ値を出さない
title_en: Run inter-reflections, multiple scattering and iterations to convergence — return the evidence and the remaining error, and no value when it did not converge
category: 光と色
ops: [iterate_fixed_point, conv_observed_order, conv_gci, mc_sequential_mean, mc_photon_slab, iv_richardson_lucy_until]
examples: [converge_tour]
version: 0.6.1
inputs: []
pipeline: [iterate_fixed_point, conv_gci]
alternatives: [conv_observed_order, mc_sequential_mean, mc_photon_slab, iv_richardson_lucy_until, iv_richardson_lucy]
limits: 推定残り誤差は g が縮小写像である所でだけ意味を持つ(割線の比 L が 1 以上なら出さない)。GCI は離散化の誤差だけで、モデルの誤りは含まない。モンテカルロの区間は光子ごとの寄与の正規近似で、逐次に止めると被覆率は名目より少し下がりうる(0.95 に対し 400 回で実測、テストが両側で判定)。光子輸送は平行平板の層だけ(横方向の分布・ガラス層は無い)。Richardson-Lucy の止め方は雑音モデル(光子数か既知の σ)が正しいときだけ働く。
calibration: 単位は入力のまま(光子輸送は係数の長さの単位と厚さの単位を揃える。反射率・透過率は無次元)。画素から mm への換算は無い。
---

# 多重反射・多重散乱・反復を収束まで回す

## できること

実物に近い順方向モデルは、閉じた式ではなく**繰り返しの極限**であることが多い —— 溝の壁から壁へ跳ね返り続ける光、濁った媒質の
中で散乱を繰り返す光子、どこかで止めるべき逆畳み込み。この族(`converge`、6 op)は、どれも収束まで回し、**収束した証拠**と
**残りの誤差**を返し、収束しなければ値を返しません。

- `iterate_fixed_point`: x = g(x) を素の反復・Aitken・Anderson 加速(Walker & Ni 2011 の式 3.1、QR で解き条件数で古い列を捨てる)で。
  残差の履歴と推定残り誤差。発散・周期 2 の振動・頭打ちは `NotConvergedError`。
- `conv_observed_order` / `conv_gci`: 格子(帯の数・反射の回数・標本数)を 3 段振った解から観測収束次数と GCI(Celik ら 2008、式 1〜7)。
- `mc_sequential_mean`: 区間が許容幅に入るまで標本を足し、使った標本数を返す。
- `mc_photon_slab`: 多層の濁ったスラブの光子輸送(MCML の規則)。拡散反射・全透過・吸収を信頼区間つきで。
- `iv_richardson_lucy_until`: Richardson-Lucy を食い違い原理(ポアソン τ = 1 / Morozov)で止める。止まらなければ「モデルの値域外」。

開き角 24° の V 溝の奥は、直接光だけで計算すると相互反射込みの 1/10 の明るさです(溝全体の反射率 0.198 対 0.745)。直接光だけの
モデルを実写に合わせると、この差を係数(アルベド・照明の強さ)が吸い込んで、残差は小さいのに係数が間違います。

## What it does

Six ops (`converge`) run a forward model to convergence and return the evidence: a fixed-point driver with Aitken and Anderson
acceleration (Walker & Ni 2011 eq. 3.1; it reproduces GMRES on linear maps, checked) that refuses divergent or oscillating runs;
the observed order and grid convergence index of Celik et al. 2008 (Table 1 reproduced); sequential Monte Carlo to a tolerance;
MCML-type photon transport in layered turbid slabs with confidence intervals that contain the MCML manual's Table 6.1 / 6.2
values; and Richardson-Lucy stopped by the Poisson discrepancy principle (tau = 1) or Morozov's, refusing data outside the model's range.

## 向くところ / 向かないところ

- 向く: 相互反射・多重散乱・自己無撞着の式など、繰り返しの極限として定まる量。「何回(何本・何個)で足りるか」を数で言いたい場合。
- 向く: 回数を固定すると根拠の無い反復(逆畳み込み)を、データの雑音で止めたい場合。
- 向かない: 3-D の一般形状の光線追跡(この族は 2-D の V 溝の例と平行平板の光子輸送まで)。ガラス層・横方向の分布(MCML の格子)。

## 推奨パイプライン

`iterate_fixed_point` → `conv_gci`

順方向モデルを `iterate_fixed_point` で収束まで解き(推定残り誤差を読む)→ 格子・帯の数を 3 段振った解を `conv_gci` に渡して
離散化誤差を GCI で見積もる。確率的なモデルなら `mc_sequential_mean`、濁った媒質なら `mc_photon_slab`。

## 代替

`conv_observed_order`(次数だけ)、`mc_sequential_mean`(任意の確率的なモデル)、`mc_photon_slab`(濁った多層媒質)、
`iv_richardson_lucy_until`(逆畳み込みの止め時)、`iv_richardson_lucy`(反復回数を固定する従来版)。

## 限界

推定残り誤差 L/(1−L)·‖g(x)−x‖ は g が縮小写像である所でだけ意味を持ち、割線の比 L が 1 以上なら出しません(振動する写像の
不安定な不動点を Anderson が解いた場合など)。GCI はモデルの誤りを含みません。モンテカルロの区間は光子ごとの寄与の正規近似で、
逐次に止めると被覆率は名目より少し下がりえます(テストが 400 回で両側に判定)。光子輸送は平行平板の層だけ。Richardson-Lucy の
止め方は雑音モデルが正しいときだけ働き、仮定の PSF が広すぎるとモデルの値域外として像を返しません。

## 実寸校正

単位は入力のまま。光子輸送は吸収・散乱係数の長さの単位と厚さの単位を揃えること(MCML の表は cm⁻¹ と cm)。反射率・透過率は無次元。

## 最初の 1 本

```python
import fullseye as fs

r = fs.ledger.iterate_fixed_point("cos", method="anderson")   # x = cos x
print(round(r["x"], 10), r["n_iter"], r["n_evals"])           # 0.7390851332 6 7
g = fs.ledger.conv_gci()                                       # Celik ら 2008 Table 1 の第 1 列
print(round(g["p"], 2), round(g["gci_fine21_pct"], 1))         # 1.53 2.2
```

## 裏づけ

- op: `iterate_fixed_point` / `conv_observed_order` / `conv_gci` / `mc_sequential_mean` / `mc_photon_slab` / `iv_richardson_lucy_until`
- 例: [`converge_tour`](../../examples/converge_tour.py) —— V 溝の相互反射(素の反復 187 回対 Anderson 28 回、帯の数の GCI)、光子を
  足すと区間が van de Hulst の値に縮む様子、Richardson-Lucy の半収束と停止、収束しない写像の拒否。
- 一次資料: Walker & Ni 2011(Anderson 加速、式 3.1・定理 2.2)、Celik ら 2008(GCI の手順と Table 1)、Wang & Jacques の MCML
  マニュアル(式 3.2a〜3.31、Table 6.1 / 6.2)、Benvenuto & Piana 2012(食い違い原理の式 18・30、補題 3.2)、Bertero ら 2010。

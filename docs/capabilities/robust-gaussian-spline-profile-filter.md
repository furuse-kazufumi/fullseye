---
id: robust-gaussian-spline-profile-filter
title: 傷や突起に引きずられない平均線を引く(ロバストなガウス回帰・スプラインフィルタ、断面と面)
title_en: A mean line that deep scratches and spikes cannot drag (robust Gaussian-regression and spline filters, for profiles and surfaces)
category: 測る
ops: [robust_gaussian_profile, robust_spline_profile, robust_gaussian_surface, surface_filter]
examples: [poc_robust_profile_filter, example_robust_profile_filter]
version: 0.6.1
inputs: [signal]
pipeline: [robust_gaussian_profile, profile_params]
alternatives: [robust_spline_profile, surface_filter, robust_gaussian_surface]
limits: 傷の標本が 4 割を超えると平均線が傷側へ破綻する(合成断面の実測で 35 % までは雑音の床、40 % で 3.5 µm)。外れ値の無い断面でもロバスト版は線形と一致しない(biweight が雑音の裾を刈る)。傷が窓(既定 ±λc)より広いと外挿せず拒否する。収束しなければ値を返さない。次数 2 は出していない。真値は閉形式と合成したうねりで、実スタイラス断面での検証は未了。
calibration: 平均線の真値は測定器では得られない。標本間隔 dx(µm)とカットオフ λc(測定条件で決まる値)は呼び出し側が与え、単位を混ぜても検出できない。伝達関数は dx と λc だけで決まる閉形式なので、既知波長の正弦を通して λc で 0.5 になるかを現場の設定で確かめられる。
---

# 傷や突起に引きずられない平均線を引く(ロバストなガウス回帰・スプラインフィルタ、断面と面)

## できること

粗さは断面(または面)から平均線(うねり)を引いて残りを測ります。普通のガウスフィルタは深い傷に引かれて平均線が傷の側へ凹み、**傷の両側の健全な面が山に見えます**(PoC の実測で、傷の脇の粗さが真値の 2.5 倍)。`roughness` 族の新しい 3 本は、Tukey の biweight で傷の重みを下げながら反復し、平均線を傷から守ります。

- `robust_gaussian_profile`: ガウス重みの局所回帰(次数 0 = 重み付き平均、1 = 局所直線)。カットオフ波長 λc で透過率ちょうど 50 %(閉形式)。端を削らず全長を返す。
- `robust_spline_profile`: 2 階差分の罰則つき最小二乗(離散の三次平滑化スプライン)。端に自然境界条件が付き、遮断がガウスより鋭い。伝達関数は `1/(1+(sin(π dx/λ)/sin(π dx/λc))⁴)`。
- `robust_gaussian_surface`: 面版(核は可分、局所面の回帰)。
- `robust=False` で重み 1 の線形版になり、比較の基準に使えます。

実測(合成した断面、真のうねりは解析的): 傷の標本が 20 % までロバストの引きずりは線形の 0.06 倍、**40 % で破綻**します(理論上は 50 %。線形解から反復を始めるので手前で崩れる)。収束しなければ値を返さず拒否します。

## What it does

Three ops in the `roughness` ledger (category `prepare`). `robust_gaussian_profile` is a Gaussian-weighted local regression (order 0 or 1) iterated with Tukey's biweight at `c · median|r|`; its transmission is exactly 50 % at λc (closed form `exp(-π(αλc/λ)²)`, α² = ln2/π), measured to 3e-8. `robust_spline_profile` solves a second-difference penalised least squares (a discrete cubic smoothing spline) with the same reweighting; its transfer function `1/(1+(sin(π dx/λ)/sin(π dx/λc))⁴)` is matched to 1e-11. `robust_gaussian_surface` is the areal version. On a synthetic profile with a known waviness, scratches covering up to 20 % of the samples drag the robust mean line 0.06 times as far as the linear one; at 40 % it breaks down, and a non-converging iteration is refused rather than returned.

## 向くところ / 向かないところ

**向く**: スタイラス計・白色干渉計の断面や面で、傷・ゴミ・突起が混じるうねりの分離。平均線の引きずり量を数えたいとき(`robust=False` と並べる)。

**向かない**: ★外れ値の無いデータでも biweight は雑音の裾を刈るので線形とは一致しません(「重み 1 なら既存の `surface_filter` と 1e-12 で一致」が正しい言い方)。傷が窓(既定 ±λc)より広いと外挿せず拒否します。汚染が 4 割を超えると破綻します。次数 2 は、カットオフでの透過率が 85 % になりカットオフの意味が変わるので出していません。既存の `surface_filter` は規格の文面の打ち切り ±λc/2 のせいで λc での透過率が 0.5095 でしたが、2026-10-18 に ±0.75λc へ直して 0.5000 になりました(この族の新 op は ±λc で 0.5)。実際のスタイラス断面での検証は未了で、真値は閉形式と合成したうねりです。

## 推奨パイプライン

`robust_gaussian_profile` → `profile_params`

断面の傾きや形状を先に除き(面なら `surface_form_remove`)、`robust_gaussian_profile` の粗さを `profile_params`(Ra / Rq / Rz など)へ渡す。`info["converged"]` と `info["n_zero_weight"]`(重みを 0 にされた標本の数)を見て、傷として扱われた点の多さを確認する。端は削らず全長が返るので、端の信頼度が要るなら両端 λc/2 を捨てる。

## 代替

端の自然境界条件と鋭い遮断が欲しいときは `robust_spline_profile`、面は `robust_gaussian_surface`。外れ値が無いと分かっていて普通の線形ガウスでよいときは `surface_filter`(打ち切り ±0.75λc、λc の透過率 0.5000)か、`robust=False, order=0, truncate=0.75` の線形版(内部で 1e-12 一致)。

## 限界

- 破綻点は合成断面の実測で汚染 35 % と 40 % のあいだ。線形解から反復を始めるので理論の 50 % の手前で崩れる。
- 外れ値の無い断面でもロバスト版は線形と一致しない。傷なしの引きずりは両者とも約 0.12 µm(雑音 σ 0.3 µm)で、傷が入ると差が桁で開く。
- 傷が窓より広い、反復が収束しない、次数が 0/1 以外、のときは値を返さない。

## 実寸校正

`dx` と `lambda_c` は同じ長さの単位で渡す(混ぜても検出できない)。λc は測定条件(評価長さ・粗さの区分)で決まる値で、この op は決めない。既知波長 λc の正弦を `robust=False` で通して振幅 0.5 を確かめると、設定と単位の取り違えを現場で拾える。

## 最初の 1 本

```python
import numpy as np
import roughness

x = np.arange(2400.0)
truth = 2.0 * np.sin(2 * np.pi * x / 600.0)                  # 本当のうねり(µm)
z = truth + 0.3 * np.random.default_rng(0).standard_normal(x.size)
for s in (500, 900, 1300, 1700):
    z[s:s + 8] -= 6.0                                          # 深い傷 4 本
_, lin, _ = roughness.robust_gaussian_profile(z, 1.0, 80.0, robust=False)
rough, rob, info = roughness.robust_gaussian_profile(z, 1.0, 80.0)
inner = slice(150, -150)
print("引きずり 線形 %.2f / ロバスト %.2f µm(反復 %d 回)" % (
    np.abs(lin - truth)[inner].max(), np.abs(rob - truth)[inner].max(), info["iterations"]))
```

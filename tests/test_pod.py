# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""検出確率(POD、MIL-HDBK-1823A)の 5 op の門。

★この回の規律: **使った式で答え合わせをしない**。真値は次のどれかに限った。

1. **閉形式**: (β0, β1, σ, y_dec) を手で決めた表を渡し、a50 / a90 が代数式と 1e-12 で一致。
2. **既存実装**: 打ち切りが無ければ最尤解は最小二乗 —— ``np.polyfit`` と ``sqrt(RSS/n)``。
3. **第 2 実装**: 打ち切り回帰と 2 値 GLM を、**別のパラメータ化**(ln σ)と**別のアルゴリズム**
   (``scipy.optimize.minimize``)で書いた負の対数尤度で解き直し、推定値を突き合わせる。
   尤度の式も ``scipy.stats`` の logpdf / logcdf / logsf で独立に書いた(op は Olsen の座標で
   手書きの勾配・ヘッセ行列)。
4. **公表値**: MIL-HDBK-1823A G.4.6 の誤検出確率の表(PFP50/90/95、印刷された 13 行)。
5. **定理**: 大標本で a90/95 が真の a90 を上回る割合は 0.95(二項誤差の帯で判定)。
   ★小標本では**下回る**(楽観側)—— それも数えて門にする(隠さない)。

ゼロ点: 定数応答・全部検出・完全分離・β1 <= 0 は ``ValueError``。
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import pytest
from scipy import optimize, stats

import opsspc
import pod

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Z90 = stats.norm.ppf(0.9)
Z95 = stats.norm.ppf(0.95)


def _ahat_data(rng, n, b0=1.0, b1=2.0, s=0.4, lo=0.1, hi=1.5):
    a = np.exp(rng.uniform(np.log(lo), np.log(hi), n))
    y = b0 + b1 * np.log(a) + rng.normal(0.0, s, n)
    return a, y


# --------------------------------------------------------------------------- #
# 1. 閉形式
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("log_size,log_response", [(False, False), (True, False),
                                                   (False, True), (True, True)])
def test_a50_a90_equal_the_algebraic_formulas(log_size, log_response):
    b0, b1, s = 0.7, 1.9, 0.35
    fit = {"beta0": b0, "beta1": b1, "sigma": s, "cov": np.diag([1e-4, 2e-4, 5e-5]),
           "log_size": log_size, "log_response": log_response,
           "size_min": 0.2, "size_max": 3.0}
    a_dec = 1.3
    r = pod.pod_from_ahat(fit, a_dec)
    yd = math.log(a_dec) if log_response else a_dec
    mu = (yd - b0) / b1
    x90 = mu + Z90 * s / b1
    back = math.exp if log_size else (lambda v: v)
    assert abs(r["a50"] - back(mu)) <= 1e-12 * max(1.0, abs(back(mu)))
    assert abs(r["a90"] - back(x90)) <= 1e-12 * max(1.0, abs(back(x90)))
    # a90/95 も手で: (μ, σ_pod) のヤコビアンは書き下せる
    J = np.array([[-1 / b1, -mu / b1, 0.0], [0.0, -(s / b1) / b1, 1 / b1]])
    C = J @ fit["cov"] @ J.T
    se = math.sqrt(C[0, 0] + Z90 ** 2 * C[1, 1] + 2 * Z90 * C[0, 1])
    assert abs(r["a90_95"] - back(x90 + Z95 * se)) <= 1e-12 * max(1.0, back(x90 + Z95 * se))
    # 曲線: POD(a50) = 0.5 / 下限は a90/95 でちょうど 0.9(水平方向のデルタ法の定義)
    r2 = pod.pod_from_ahat(fit, a_dec, a=np.array([r["a50"], r["a90"], r["a90_95"]]))
    assert abs(r2["pod"][0] - 0.5) < 1e-12 and abs(r2["pod"][1] - 0.9) < 1e-12
    assert abs(r2["pod_lower"][2] - 0.9) < 1e-9, r2["pod_lower"]


# --------------------------------------------------------------------------- #
# 2. 打ち切りが無ければ最小二乗
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("log_size", [False, True])
def test_no_censoring_reduces_to_polyfit(log_size):
    rng = np.random.default_rng(1)
    a, y = _ahat_data(rng, 90)
    if not log_size:
        y = 0.5 + 3.0 * a + rng.normal(0, 0.3, a.size)
    f = pod.pod_ahat_fit({"a": a, "ahat": y}, log_size=log_size)
    x = np.log(a) if log_size else a
    b1, b0 = np.polyfit(x, y, 1)
    rss = float(np.sum((y - (b0 + b1 * x)) ** 2))
    assert abs(f["beta0"] - b0) < 1e-10 and abs(f["beta1"] - b1) < 1e-10
    assert abs(f["sigma"] - math.sqrt(rss / a.size)) < 1e-10
    assert f["n_censored"] == 0
    # 共分散も既知の閉形式: Var(β) = σ² (X'X)^-1、Var(σ_MLE) = σ²/(2n)
    X = np.column_stack([np.ones_like(x), x])
    s2 = rss / a.size
    assert np.allclose(f["cov"][:2, :2], s2 * np.linalg.inv(X.T @ X), rtol=1e-8, atol=0)
    assert abs(f["cov"][2, 2] - s2 / (2 * a.size)) < 1e-10 * s2
    assert abs(f["cov"][0, 2]) < 1e-12 and abs(f["cov"][1, 2]) < 1e-12


# --------------------------------------------------------------------------- #
# 3. 第 2 実装(別のパラメータ化・別のアルゴリズム)
# --------------------------------------------------------------------------- #
def _nll_tobit(p, x, y, st):
    """負の対数尤度。パラメータは (β0, β1, ln σ) —— op の (β/σ, 1/σ) とは別。"""
    b0, b1, ls = p
    s = math.exp(ls)
    m = b0 + b1 * x
    ll = np.where(st == 0, stats.norm.logpdf(y, m, s),
                  np.where(st < 0, stats.norm.logcdf(y, m, s), stats.norm.logsf(y, m, s)))
    return -float(ll.sum())


def _num_hess(f, p, h):
    k = len(p)
    H = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            e = np.zeros(k)
            e[i] = h[i]
            d = np.zeros(k)
            d[j] = h[j]
            H[i, j] = (f(p + e + d) - f(p + e - d) - f(p - e + d) + f(p - e - d)) / (4 * h[i] * h[j])
    return H


def test_censored_mle_matches_an_independent_minimiser():
    rng = np.random.default_rng(2)
    a, y = _ahat_data(rng, 150)
    lo, hi = -1.0, 1.3
    f = pod.pod_ahat_fit({"a": a, "ahat": y}, log_size=True, censor_low=lo, censor_high=hi)
    assert f["n_left"] > 20 and f["n_right"] > 10, (f["n_left"], f["n_right"])
    st = np.where(y <= lo, -1, np.where(y >= hi, 1, 0))
    yy = np.clip(y, lo, hi)
    x = np.log(a)
    res = optimize.minimize(_nll_tobit, x0=[0.0, 1.0, 0.0], args=(x, yy, st),
                            method="Nelder-Mead",
                            options={"xatol": 1e-10, "fatol": 1e-12, "maxiter": 20000})
    res = optimize.minimize(_nll_tobit, x0=res.x, args=(x, yy, st), method="BFGS",
                            options={"gtol": 1e-9})
    b0, b1, s = res.x[0], res.x[1], math.exp(res.x[2])
    d = max(abs(f["beta0"] - b0), abs(f["beta1"] - b1), abs(f["sigma"] - s))
    print("最大差(打ち切り回帰 vs 独立最小化) = %.2e" % d)
    assert d < 1e-5, d
    assert abs(f["loglik"] + res.fun) < 1e-7
    # 共分散: 独立な尤度の数値ヘッセ行列を (β0, β1, σ) で取って逆にしたもの
    g = lambda p: _nll_tobit([p[0], p[1], math.log(p[2])], x, yy, st)  # noqa: E731
    Hn = _num_hess(g, np.array([f["beta0"], f["beta1"], f["sigma"]]), [1e-4, 1e-4, 1e-4])
    Cn = np.linalg.inv(Hn)
    assert np.allclose(f["cov"], Cn, rtol=2e-3, atol=1e-9), (f["cov"], Cn)


def _nll_glm(p, x, h, link):
    """2 値の負の対数尤度を scipy.stats の分布で書き直したもの(op はリンクごとの手書き)。"""
    eta = p[0] + p[1] * x
    if link == "logit":
        lp, lq = stats.logistic.logcdf(eta), stats.logistic.logsf(eta)
    elif link == "probit":
        lp, lq = stats.norm.logcdf(eta), stats.norm.logsf(eta)
    else:  # cloglog = 最小値の Gumbel 分布の cdf
        lp, lq = stats.gumbel_l.logcdf(eta), stats.gumbel_l.logsf(eta)
    return -float(np.sum(np.where(h > 0, lp, lq)))


@pytest.mark.parametrize("link", ["logit", "probit", "cloglog"])
def test_hitmiss_mle_matches_an_independent_minimiser(link):
    rng = np.random.default_rng(3)
    a = np.exp(rng.uniform(np.log(0.1), np.log(2.0), 160))
    h = (rng.random(a.size) < stats.norm.cdf((np.log(a) + 0.7) / 0.3)).astype(int)
    g = pod.pod_hitmiss_fit({"a": a, "hit": h}, link=link, log_size=True)
    x = np.log(a)
    res = optimize.minimize(_nll_glm, x0=[1.0, 1.0], args=(x, h, link), method="Nelder-Mead",
                            options={"xatol": 1e-11, "fatol": 1e-13, "maxiter": 20000})
    d = max(abs(g["beta0"] - res.x[0]), abs(g["beta1"] - res.x[1]))
    print("最大差(%s vs 独立最小化) = %.2e" % (link, d))
    assert d < 1e-5, d
    assert abs(g["loglik"] + res.fun) < 1e-8
    Hn = _num_hess(lambda p: _nll_glm(p, x, h, link), np.array([g["beta0"], g["beta1"]]),
                   [1e-4, 1e-4])
    assert np.allclose(g["cov"], np.linalg.inv(Hn), rtol=2e-3), (g["cov"], np.linalg.inv(Hn))
    # リンクの逆で a50 を書き下す(logit / probit は −β0/β1)
    q50 = {"logit": 0.0, "probit": 0.0, "cloglog": math.log(math.log(2.0))}[link]
    assert abs(math.log(g["a50"]) - (q50 - g["beta0"]) / g["beta1"]) < 1e-12
    if link == "logit":
        assert abs(math.log(g["a50"]) + g["beta0"] / g["beta1"]) < 1e-12
    # 尤度比の上限は Wald と同じ桁、どちらも a90 より上
    assert g["lr_status"] == "ok"
    assert g["a90_95"] > g["a90"] and g["a90_95_lr"] > g["a90"]
    assert 0.5 < (g["a90_95_lr"] - g["a90"]) / (g["a90_95"] - g["a90"]) < 2.0


def test_the_lr_bound_sits_where_the_profile_deviance_hits_chi2():
    """尤度比の上限を、プロファイル尤度を**別に**(scipy の 1-D 最小化で)計算して確かめる。"""
    rng = np.random.default_rng(4)
    a = np.exp(rng.uniform(np.log(0.1), np.log(2.0), 120))
    h = (rng.random(a.size) < stats.norm.cdf((np.log(a) + 0.7) / 0.3)).astype(int)
    g = pod.pod_hitmiss_fit({"a": a, "hit": h}, link="probit", log_size=True)
    x = np.log(a)
    q90 = stats.norm.ppf(0.9)

    def prof(t):
        r = optimize.minimize_scalar(
            lambda b: _nll_glm([q90 - b * t, b], x, h, "probit"),
            bounds=(1e-6, 100.0), method="bounded", options={"xatol": 1e-12})
        return 2.0 * (r.fun + g["loglik"])

    t = math.log(g["a90_95_lr"])
    assert abs(prof(t) - stats.chi2.ppf(0.90, 1)) < 1e-4, prof(t)
    assert abs(prof(math.log(g["a90"]))) < 1e-8          # 最尤点では 0


# --------------------------------------------------------------------------- #
# 4. 公表値: MIL-HDBK-1823A G.4.6 の誤検出確率の表
# --------------------------------------------------------------------------- #
#: (誤検出回数, 機会数, PFP50, PFP90, PFP95)。G.4.6 本文と "Reference PFP Table" の印刷値。
_TABLE_G_PFP = [
    (0, 150, 0.0046, 0.0152, 0.0198),
    (0, 60, 0.0115, 0.0377, 0.0487), (1, 60, 0.0278, 0.0633, 0.0766),
    (2, 60, 0.0443, 0.0863, 0.1012), (3, 60, 0.0609, 0.1080, 0.1242),
    (4, 60, 0.0774, 0.1289, 0.1461), (5, 60, 0.0940, 0.1491, 0.1673),
    (0, 200, 0.0035, 0.0114, 0.0148), (1, 200, 0.0084, 0.0193, 0.0235),
    (2, 200, 0.0134, 0.0264, 0.0311), (3, 200, 0.0183, 0.0331, 0.0383),
    (4, 200, 0.0233, 0.0396, 0.0452), (5, 200, 0.0283, 0.0459, 0.0518),
]


def test_false_call_bounds_reproduce_the_published_table():
    """★印刷値は 4 桁に丸めてある。39 個中 35 個は丸めの範囲(5e-5)で一致し、
    4 個は最後の桁が 1 ずれる(最大 7.2e-5):

        0/60  PFP90  Clopper–Pearson 0.037649(閉形式 1 − 0.1^(1/60))  表 0.0377
        4/60  PFP90                  0.128828                          表 0.1289
        0/200 PFP95                  0.014867(閉形式 1 − 0.05^(1/200)) 表 0.0148
        2/200 PFP50                  0.013348                          表 0.0134

    0 回の 2 行は閉形式そのものなので、ずれは表の側(丸めか数値解法の許容差)と読む。
    ずれの向きも揃っていない。4 個を名指しで固定する —— 増えても減っても落ちる。
    """
    worst, off = 0.0, []
    for k, n, *pub in _TABLE_G_PFP:
        noise = np.r_[np.full(k, 2.0), np.linspace(-1.0, 0.0, n - k)]
        r = pod.pod_false_call(noise, 1.0)
        assert r["n"] == n and r["n_false"] == k
        for got, want, tag in zip((r["pfp50"], r["pfp90"], r["pfp95"]), pub, ("50", "90", "95")):
            d = abs(got - want)
            worst = max(worst, d)
            if d > 5e-5 + 1e-12:
                off.append((k, n, tag))
    print("公表表との最大差 = %.2e、丸めを超えたもの = %s" % (worst, off))
    assert worst <= 1.0e-4 + 1e-12
    assert off == [(0, 60, "90"), (4, 60, "90"), (0, 200, "95"), (2, 200, "50")], off
    # 0 回のときは閉形式 1 − (1 − c)^(1/n)
    r = pod.pod_false_call(np.linspace(-1, 0, 150), 1.0)
    assert abs(r["pfp95"] - (1 - 0.05 ** (1 / 150))) < 1e-12


def test_false_call_normal_fit():
    rng = np.random.default_rng(5)
    v = rng.normal(-1.0, 0.5, 400)
    r = pod.pod_false_call(v, 0.0)
    m, s = v.mean(), v.std(ddof=1)
    assert abs(r["pfp_normal"] - (1 - stats.norm.cdf((0.0 - m) / s))) < 1e-14
    assert r["n_false"] == int((v > 0).sum())


# --------------------------------------------------------------------------- #
# 5. 一致性と、打ち切りを無視した最小二乗の偏り(このモデルが要る理由)
# --------------------------------------------------------------------------- #
def test_heavy_censoring_recovers_truth_and_naive_ols_is_biased():
    rng = np.random.default_rng(6)
    b0, b1, s = 1.0, 2.0, 0.4
    a, y = _ahat_data(rng, 4000, b0, b1, s)
    f = pod.pod_ahat_fit({"a": a, "ahat": y}, log_size=True, censor_low=-0.6, censor_high=1.2)
    frac = f["n_censored"] / f["n"]
    se = np.sqrt(np.diag(f["cov"]))
    z = (np.array([f["beta0"], f["beta1"], f["sigma"]]) - [b0, b1, s]) / se
    print("打ち切り %.0f %%、真値からの z = %s" % (100 * frac, np.round(z, 2)))
    assert frac > 0.5, frac
    assert np.all(np.abs(z) < 3.0), z
    # 素朴な最小二乗(記録値のまま)は傾きが寝て σ が縮む
    zo = (f["ols_beta1"] - b1) / se[1]
    print("素朴な最小二乗の傾き %.3f(真値 2)、z = %.1f" % (f["ols_beta1"], zo))
    assert zo < -10.0 and f["ols_sigma"] < 0.95 * s


# --------------------------------------------------------------------------- #
# 6. 被覆率(定理): 大標本で a90/95 >= 真の a90 となる割合は 0.95
# --------------------------------------------------------------------------- #
def _band(r, p=0.95, k=3.0):
    h = k * math.sqrt(p * (1 - p) / r)
    return p - h, p + h


def test_ahat_a9095_coverage_is_95_percent_in_large_samples():
    """n=1000 の打ち切りつきデータ 300 回。帯は二項誤差の ±3σ(±0.038)。"""
    b0, b1, s, yd = 1.0, 2.0, 0.4, 0.0
    a90 = math.exp((yd - b0) / b1 + Z90 * s / b1)
    rng = np.random.default_rng(7)
    R, hit = 300, 0
    for _ in range(R):
        a, y = _ahat_data(rng, 1000, b0, b1, s)
        f = pod.pod_ahat_fit({"a": a, "ahat": y}, log_size=True, censor_low=-1.5, censor_high=1.8)
        hit += pod.pod_from_ahat(f, yd, n_grid=2)["a90_95"] >= a90
    lo, hi = _band(R)
    print("被覆率(â vs a, n=1000) = %.3f、帯 [%.3f, %.3f]" % (hit / R, lo, hi))
    assert lo <= hit / R <= hi


def test_ahat_a9095_is_optimistic_in_small_samples():
    """★隠さない: n=60 では被覆率が 0.95 を**有意に下回る**(σ の最尤推定が n で割る
    ぶん小さく、a90 が手前に出る)。1823A の手順どおりの実装の性質で、誤りではない。"""
    b0, b1, s, yd = 1.0, 2.0, 0.4, 0.0
    a90 = math.exp((yd - b0) / b1 + Z90 * s / b1)
    rng = np.random.default_rng(8)
    R, hit = 400, 0
    for _ in range(R):
        a, y = _ahat_data(rng, 60, b0, b1, s)
        f = pod.pod_ahat_fit({"a": a, "ahat": y}, log_size=True, censor_low=-1.5, censor_high=1.8)
        hit += pod.pod_from_ahat(f, yd, n_grid=2)["a90_95"] >= a90
    lo, _ = _band(R)
    print("被覆率(â vs a, n=60) = %.3f(名目 0.95、帯の下端 %.3f)" % (hit / R, lo))
    assert hit / R < lo


def test_hitmiss_coverage_large_sample_and_lr_beats_wald_small_sample():
    """2 値: n=800 で Wald も尤度比も 0.95 の帯に入る。n=80 では両方下回り、
    尤度比のほうが名目に近い(1823A G.4.2.2 が尤度比を勧める理由)。"""
    mu, sg = -0.5, 0.2
    a90 = math.exp(mu + Z90 * sg)

    def run(n, R, seed):
        rng = np.random.default_rng(seed)
        w = lr = m = 0
        for _ in range(R):
            a = np.exp(rng.uniform(np.log(0.1), np.log(1.5), n))
            h = rng.random(n) < stats.norm.cdf((np.log(a) - mu) / sg)
            try:
                g = pod.pod_hitmiss_fit({"a": a, "hit": h}, link="probit", log_size=True,
                                        n_grid=2)
            except ValueError:
                continue                       # 分離した標本(小標本では起きる)
            m += 1
            w += g["a90_95"] >= a90
            lr += g["a90_95_lr"] is not None and g["a90_95_lr"] >= a90
        return w / m, lr / m, m

    wb, lb, m = run(800, 200, 9)
    lo, hi = _band(m)
    print("被覆率(hit/miss, n=800, %d 回) Wald %.3f / 尤度比 %.3f、帯 [%.3f, %.3f]"
          % (m, wb, lb, lo, hi))
    assert lo <= wb <= hi and lo <= lb <= hi
    ws, ls, m = run(80, 200, 10)
    print("被覆率(hit/miss, n=80, %d 回) Wald %.3f / 尤度比 %.3f" % (m, ws, ls))
    assert ws < _band(m)[0] and ls > ws


# --------------------------------------------------------------------------- #
# 7. 取引表
# --------------------------------------------------------------------------- #
def test_tradeoff_rows_agree_with_the_single_threshold_ops():
    rng = np.random.default_rng(11)
    a, y = _ahat_data(rng, 120)
    f = pod.pod_ahat_fit({"a": a, "ahat": y}, log_size=True, censor_low=-1.2)
    noise = rng.normal(-1.0, 0.5, 300)
    T = pod.pod_decision_tradeoff(f, noise, n_grid=9)
    assert T["a_dec"].size == 9
    for i, ad in enumerate(T["a_dec"]):
        r = pod.pod_from_ahat(f, float(ad), n_grid=2)
        q = pod.pod_false_call(noise, float(ad))
        assert abs(T["a90_95"][i] - r["a90_95"]) < 1e-12
        assert abs(T["a90"][i] - r["a90"]) < 1e-12
        assert abs(T["pfp_normal"][i] - q["pfp_normal"]) < 1e-12
        assert T["pfp50"][i] == q["pfp50"]
    # 閾値を上げると a90 は厳密に増え(μ が y_dec の 1 次)、誤検出は増えない
    assert np.all(np.diff(T["a90"]) > 0)
    assert np.all(np.diff(T["pfp_normal"]) < 0) and np.all(np.diff(T["pfp_empirical"]) <= 0)


# --------------------------------------------------------------------------- #
# 8. ゼロ点と拒否(fail-closed)
# --------------------------------------------------------------------------- #
def test_constant_response_is_rejected():
    a = np.linspace(0.1, 1.0, 20)
    with pytest.raises(ValueError, match="sigma is 0"):
        pod.pod_ahat_fit({"a": a, "ahat": np.full(20, 3.0)})
    with pytest.raises(ValueError, match="sigma is 0"):
        pod.pod_ahat_fit({"a": a, "ahat": 1.0 + 2.0 * a})      # 散らばり 0 の直線も


def test_falling_response_has_no_detection_curve():
    rng = np.random.default_rng(12)
    a = np.linspace(0.1, 1.0, 40)
    f = pod.pod_ahat_fit({"a": a, "ahat": 3.0 - 2.0 * a + rng.normal(0, 0.1, 40)})
    assert f["beta1"] < 0
    with pytest.raises(ValueError, match="not positive"):
        pod.pod_from_ahat(f, 1.0)
    with pytest.raises(ValueError, match="not positive"):
        pod.pod_decision_tradeoff(f, rng.normal(0, 1, 20))


def test_a_slope_indistinguishable_from_zero_is_refused():
    """★正の傾きでも誤差の範囲で 0 なら曲線を出さない(PoC の暗視野照明で、
    β1 = 0.035 ± 0.033 から a90/95 = 7e46 µm が**数として**返ってきた)。"""
    rng = np.random.default_rng(14)
    a = np.exp(rng.uniform(np.log(0.1), np.log(1.5), 60))
    y = 1.0 + rng.normal(0, 0.4, 60)                    # 大きさに依らない応答
    f = pod.pod_ahat_fit({"a": a, "ahat": y}, log_size=True)
    se = math.sqrt(f["cov"][1, 1])
    assert abs(f["beta1"]) < 3 * se
    if f["beta1"] > 0:
        with pytest.raises(ValueError, match="not distinguishable from 0|not positive"):
            pod.pod_from_ahat(f, 1.5)
    # 同じ傾き・同じ誤差の表を手で作り、境界の両側を確かめる(z_0.95 = 1.645)
    base = {"beta0": 1.0, "sigma": 0.4, "log_size": True, "log_response": False,
            "size_min": 0.1, "size_max": 1.5}
    cov = np.diag([1e-3, 0.01, 1e-3])                   # se(β1) = 0.1
    with pytest.raises(ValueError, match="not distinguishable from 0"):
        pod.pod_from_ahat(dict(base, beta1=0.16, cov=cov), 1.5)
    assert pod.pod_from_ahat(dict(base, beta1=0.17, cov=cov), 1.5)["a50"] > 0


def test_an_a9095_beyond_the_tested_sizes_is_flagged():
    """a90/95 が試した最大の大きさより先なら旗を立てる(外挿)。旗の両側を同じ回帰で。"""
    rng = np.random.default_rng(15)
    a, y = _ahat_data(rng, 80)                     # 大きさ 0.1 .. 1.5
    f = pod.pod_ahat_fit({"a": a, "ahat": y}, log_size=True)
    lo = pod.pod_from_ahat(f, 0.0)
    hi = pod.pod_from_ahat(f, 2.5)                 # 閾値を上げると a90/95 は 1.5 を超える
    assert lo["a90_95"] < f["size_max"] and not lo["a90_95_beyond_data"]
    assert hi["a90_95"] > f["size_max"] and hi["a90_95_beyond_data"]


def test_hitmiss_rejects_all_hit_all_miss_and_separation():
    a = np.linspace(0.1, 1.0, 30)
    with pytest.raises(ValueError, match="both hits and misses"):
        pod.pod_hitmiss_fit({"a": a, "hit": np.ones(30, int)})
    with pytest.raises(ValueError, match="both hits and misses"):
        pod.pod_hitmiss_fit({"a": a, "hit": np.zeros(30, bool)})
    with pytest.raises(ValueError, match="complete separation"):
        pod.pod_hitmiss_fit({"a": a, "hit": (a > 0.5).astype(int)})
    with pytest.raises(ValueError, match="0 / 1"):
        pod.pod_hitmiss_fit({"a": a, "hit": np.full(30, 2)})
    with pytest.raises(ValueError, match="link"):
        pod.pod_hitmiss_fit({"a": a, "hit": (a > 0.5).astype(int)}, link="cauchit")


@pytest.mark.parametrize("bad", [
    {}, {"a": [1.0, 2.0]}, {"a": [], "ahat": []},
    {"a": [1.0, 2.0, 3.0], "ahat": [1.0, np.nan, 2.0]},
    {"a": ["x", "y", "z"], "ahat": [1.0, 2.0, 3.0]},
    {"a": [1.0, 2.0, 3.0], "ahat": [1.0, 2.0]},
])
def test_ahat_fit_rejects_malformed_tables(bad):
    with pytest.raises(ValueError):
        pod.pod_ahat_fit(bad)


def test_other_refusals():
    rng = np.random.default_rng(13)
    a, y = _ahat_data(rng, 50)
    with pytest.raises(ValueError, match="censor_low"):
        pod.pod_ahat_fit({"a": a, "ahat": y}, censor_low=2.0, censor_high=1.0)
    with pytest.raises(ValueError, match="uncensored"):
        pod.pod_ahat_fit({"a": a, "ahat": y}, censor_low=10.0)
    with pytest.raises(ValueError, match="log_size"):
        pod.pod_ahat_fit({"a": np.r_[0.0, a[1:]], "ahat": y}, log_size=True)
    f = pod.pod_ahat_fit({"a": a, "ahat": y}, log_size=True)
    with pytest.raises(ValueError, match="level"):
        pod.pod_from_ahat(f, 0.0, level=1.2)
    with pytest.raises(ValueError, match="a_dec"):
        pod.pod_from_ahat(f, float("nan"))
    with pytest.raises(ValueError, match="pod_ahat_fit"):
        pod.pod_from_ahat({"beta0": 1.0}, 0.0)
    with pytest.raises(ValueError, match="same"):
        pod.pod_false_call(np.zeros(10), 0.5)
    with pytest.raises(ValueError):
        pod.pod_false_call(np.array([]), 0.5)


# --------------------------------------------------------------------------- #
# 9. 台帳と公開経路
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    listed = set(opsspc.list_ops("pod"))
    assert listed == set(pod.__all__) == set(pod.POD), (listed, pod.__all__)
    assert not opsspc.missing()
    for name in listed:
        assert opsspc.info(name)["module"] == "pod"
        assert opsspc.info(name)["out"] == "table"
        assert len(opsspc.info(name)["doc"]) >= 20


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs

    for name in opsspc.list_ops("pod"):
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = {r[0]: r for r in tc.catalog() if r[0].startswith("pod_")}
    assert set(rows) == set(pod.__all__)
    assert rows["pod_false_call"][2] == ["signal"]
    assert rows["pod_decision_tradeoff"][2] == ["table", "signal"]


def test_the_fuzzer_builds_arguments_that_actually_compute():
    """★宣言型は table だが table は広い型 —— 任意の表では列が合わず**必ず拒否**され、
    探針は「走ったが計算していない」になる。引数ビルダが本物の入力を組むことを確かめる。"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz as cf

    for name in pod.__all__:
        assert name in cf.OP_ARG_BUILDERS, name
        args, kw = cf.OP_ARG_BUILDERS[name](None, np.random.default_rng(0))
        out = getattr(pod, name)(*args, **kw)
        assert cf.TYPE_CHECKS["table"](out)
    fit = pod.pod_ahat_fit(*cf.OP_ARG_BUILDERS["pod_ahat_fit"](None, np.random.default_rng(0))[0],
                           **cf.OP_ARG_BUILDERS["pod_ahat_fit"](None, np.random.default_rng(0))[1])
    assert fit["n_left"] > 0 and fit["n_right"] > 0, "打ち切りの項が探針で一度も計算されない"

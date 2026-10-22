# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""収束型の演算(opsconverge: converge.py / mcphoton.py / deconvstop.py)の門 —— 外部真値で採点し、収束しなければ値を返さないこと。

外部真値:
* Celik ら 2008(J. Fluids Eng. 130:078001)Table 1 の 3 列(p 1.53 / 0.75 / 1.51、GCI 2.2 / 1.1 / 0.5 %)。
* MCML マニュアル Table 6.1(van de Hulst: R_d 0.09739、T_t 0.66096)と Table 6.2(Giovanelli: 0.2600)。区間が値を
  含むことを、区間の下端と上端の両側で判定する。
* Anderson 加速は線形問題で GMRES と同値(Walker & Ni 2011 定理 2.2)—— 別に書いた GMRES(Krylov 基底の最小二乗)と照合。
* 整合の半無限媒質の拡散反射は Chandrasekhar の H 関数から 1 - H(1) sqrt(1 - a)(H は iterate_fixed_point で解く)。
* Richardson-Lucy の総和の保存(Benvenuto & Piana 2012 補題 3.2)。

各門には「壊して確かめる」探針を付ける(門が素通しでないこと)。
"""
from __future__ import annotations

import json
import math
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import converge as cv  # noqa: E402
import deconvstop as ds  # noqa: E402
import mcphoton as mp  # noqa: E402
from metriccontract import MetricContractError, value_or_worst  # noqa: E402


# --------------------------------------------------------------------------- #
# Celik et al. 2008 Table 1                                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("col", ["monotonic", "p_below_1", "oscillatory"])
def test_celik_table1_reproduced(col):
    ex = cv.CELIK_TABLE1[col]
    # 格子比はセル数から Celik 式 (2)(2-D: h = (A/N)^(1/2))で作る。表に印字された r は 3 桁に丸めてある
    g = cv.conv_gci(phi=ex["phi"], n_cells=ex["n_cells"], dim=2)
    assert round(g["p"], 2) == ex["p"], g["p"]
    # 百分率は「小数 2 桁に丸めてから 1 桁に」丸めると 9 個とも一致する。1 回の丸めでは 1 個だけ外れる:
    # 第 2 列の e_ext = 0.8465 % は 0.8 だが、表は 0.9(0.85 を経由した二重の丸め)。照合の作法として明記して残す
    for key, want in (("ea21_pct", "ea_pct"), ("eext21_pct", "eext_pct"), ("gci_fine21_pct", "gci_pct")):
        two = Decimal(str(round(g[key], 2)))                              # 例: 0.8465 -> 0.85
        assert float(two.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) == ex[want], (key, g[key], ex[want])
        assert abs(g[key] - ex[want]) < 0.055, (key, g[key])
    assert abs(g["phi_ext21"] - ex["phi_ext"]) <= 5e-5, g["phi_ext21"]       # 表の 4 桁で一致
    assert abs(g["r21"] - ex["r"][0]) < 5e-4 and abs(g["r32"] - ex["r"][1]) < 5e-4
    assert g["oscillatory"] == (col == "oscillatory")


def test_celik_probe_printed_rounded_ratio_gives_another_p():
    """探針: 表に印字された丸めた比(r32 = 1.333)をそのまま使うと、第 1 列の p は 1.537(→ 1.54)で表の 1.53 にならない。
    門がセル数からの比を使っていること、そして 3 桁目まで見ていることの確かめ。"""
    ex = cv.CELIK_TABLE1["monotonic"]
    g = cv.conv_gci(phi=ex["phi"], r=ex["r"])
    assert round(g["p"], 2) != ex["p"], g["p"]
    assert abs(g["phi_ext21"] - ex["phi_ext"]) > 5e-5


def test_celik_probe_constant_ratio_formula_misses_column1():
    """探針: q(p)(格子比が一定でない項)を落とすと、第 1 列(r21 = 1.5、r32 = 1.333)の p = 1.53 が出ない。"""
    ex = cv.CELIK_TABLE1["monotonic"]
    o = cv.conv_observed_order(phi=ex["phi"], n_cells=ex["n_cells"], dim=2)
    assert round(o["p"], 2) == 1.53
    assert abs(o["p_first_term"] - 1.53) > 0.5, o["p_first_term"]
    # 格子比が一定なら q = 0 で、反復せずに第 1 項で決まる
    o2 = cv.conv_observed_order(phi=(1.0, 1.1, 1.3), r=(2.0, 2.0))
    assert abs(o2["p"] - 1.0) < 1e-12 and o2["iterations"] <= 1


def test_gci_inputs_h_and_cells_agree_and_refusals():
    ex = cv.CELIK_TABLE1["p_below_1"]
    a = cv.conv_gci(phi=ex["phi"], r=ex["r"])
    b = cv.conv_gci(phi=ex["phi"], h=(1.0, 2.0, 2.0 * 2.143))
    assert abs(a["p"] - b["p"]) < 1e-12
    # 2-D の N から h(Celik 式 2): 比 r = sqrt(N1/N2)
    c = cv.conv_gci(phi=ex["phi"], n_cells=(18000, 4500, 980), dim=2)
    assert abs(c["r21"] - 2.0) < 1e-12
    with pytest.raises(MetricContractError):
        cv.conv_gci(phi=(1.0, 1.0, 1.2), r=(2.0, 2.0))          # eps21 = 0: 手順が働かない
    with pytest.raises(MetricContractError):
        cv.conv_gci(phi=(1.0, 1.1, 1.2), r=(0.5, 2.0))          # 細かい順になっていない
    with pytest.raises(MetricContractError):
        cv.conv_gci(phi=(1.0, 1.1, 1.2))                        # 格子比を推測しない


# --------------------------------------------------------------------------- #
# Anderson == GMRES on a linear map (Walker & Ni 2011, Theorem 2.2)            #
# --------------------------------------------------------------------------- #
def _gmres_iterates(A, b, x0, kmax):
    """(I - A) x = b の GMRES の k 回目の反復を、Krylov 基底上の最小二乗で直接解く(Anderson とは独立の実装)。"""
    n = A.shape[0]
    M = np.eye(n) - A
    r0 = b - M @ x0
    out = [x0.copy()]
    for k in range(1, kmax + 1):
        K = np.empty((n, k))
        v = r0.copy()
        for j in range(k):
            K[:, j] = v
            v = M @ v
        Q, _ = np.linalg.qr(K)
        y, *_ = np.linalg.lstsq(M @ Q, r0, rcond=None)
        out.append(x0 + Q @ y)
    return out


def _linear_problem(n=24, seed=4, rho=0.85):
    rng = np.random.default_rng(seed)
    A = rng.normal(size=(n, n))
    A *= rho / max(abs(np.linalg.eigvals(A)))
    b = rng.normal(size=n)
    return A, b


def test_anderson_equals_gmres_on_linear_problems():
    A, b = _linear_problem()
    g = lambda x: A @ x + b                                    # noqa: E731
    x0 = np.zeros(A.shape[0])
    rec = cv.iterate_fixed_point(g, x0, method="anderson", m=20, tol=1e-300, max_iter=8,
                                 on_fail="record", keep_iterates=True)
    assert rec["columns_dropped"] == 0                       # 定理 2.2 は切り捨て無しが前提
    it = rec["iterates"]
    gm = _gmres_iterates(A, b, x0, 7)
    for k in range(1, 8):
        want = g(gm[k])                                      # x_{k+1}^AA = g(x_k^GMRES)
        err = np.linalg.norm(it[k + 1] - want) / np.linalg.norm(want)
        assert err < 1e-9, (k, err)


def test_anderson_gmres_gate_has_power():
    """探針: 同じ比較を素の反復(plain)と、1 次元少ない GMRES に当てると外れる。"""
    A, b = _linear_problem()
    g = lambda x: A @ x + b                                    # noqa: E731
    x0 = np.zeros(A.shape[0])
    gm = _gmres_iterates(A, b, x0, 6)
    plain = cv.iterate_fixed_point(g, x0, method="plain", tol=1e-300, max_iter=7, on_fail="record",
                                   keep_iterates=True)["iterates"]
    aa = cv.iterate_fixed_point(g, x0, method="anderson", m=20, tol=1e-300, max_iter=7, on_fail="record",
                                keep_iterates=True)["iterates"]
    k = 5
    want = g(gm[k])
    assert np.linalg.norm(plain[k + 1] - want) / np.linalg.norm(want) > 1e-3
    assert np.linalg.norm(aa[k + 1] - g(gm[k - 1])) / np.linalg.norm(want) > 1e-3


# --------------------------------------------------------------------------- #
# Fixed point: convergence, error bound, refusal                              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("method", ["plain", "aitken", "anderson"])
def test_fixed_point_cos_and_honest_error_bound(method):
    rec = cv.iterate_fixed_point("cos", method=method, tol=1e-10)
    assert rec["converged"]
    err = abs(rec["x"] - cv.DOTTIE)
    assert err < 1e-9
    # 推定残り誤差は実際の誤差を下回らない(縮小写像の事後評価)
    assert rec["error_estimate"] is not None and err <= rec["error_estimate"] + 1e-15, (err, rec["error_estimate"])
    assert rec["residual_history"][-1] <= 1e-10
    assert rec["n_evals"] >= rec["n_iter"]


def test_acceleration_saves_evaluations():
    n = {m: cv.iterate_fixed_point("cos", method=m)["n_evals"] for m in ("plain", "aitken", "anderson")}
    assert n["anderson"] * 4 < n["plain"] and n["aitken"] * 4 < n["plain"], n


@pytest.mark.parametrize("g,x0,word", [
    (lambda x: x * x + 1.0, 0.0, "diverged"),                  # 実数の不動点が無く、発散する
    (lambda x: 3.2 * x * (1.0 - x), 0.3, "oscillating"),       # 周期 2 の軌道に落ちる
    (lambda x: x + 1.0, 0.0, "stagnating"),                    # 不動点が無く、残差が減らない
    (lambda x: float("nan"), 0.0, "diverged"),                 # NaN を返す写像
])
def test_fixed_point_refuses_instead_of_returning_a_value(g, x0, word):
    with pytest.raises(cv.NotConvergedError) as ei:
        cv.iterate_fixed_point(g, x0, method="plain", max_iter=300)
    assert word in str(ei.value)
    assert isinstance(ei.value, MetricContractError) and isinstance(ei.value, ValueError)
    rec = cv.iterate_fixed_point(g, x0, method="plain", max_iter=300, on_fail="record")
    assert rec["converged"] is False and rec["x"] is None and "last_iterate" in rec
    att = cv.as_attempt(rec)
    assert not att.ok and value_or_worst(att) == math.inf     # 掃引では必ず最下位


def test_anderson_finds_the_repelling_fixed_point_with_verified_residual():
    """素の反復が振動する(r = 3.2)写像でも、x = g(x) の解 1 - 1/r は在る。Anderson はそれを解き、残差で裏づける。
    推定残り誤差は出さない(g はそこで縮小写像ではない: |g'| = 1.2)。"""
    rec = cv.iterate_fixed_point(lambda x: 3.2 * x * (1.0 - x), 0.3, method="anderson")
    assert abs(rec["x"] - (1.0 - 1.0 / 3.2)) < 1e-9
    assert rec["error_estimate"] is None and rec["lipschitz_estimate"] > 1.0


def _h_equation_plane_albedo(albedo, n=200):
    """Chandrasekhar の H 関数(等方散乱)を iterate_fixed_point で解き、平面アルベド 1 - H(1) sqrt(1 - a)。"""
    x, w = np.polynomial.legendre.leggauss(n)
    mu, w = (x + 1.0) / 2.0, w / 2.0
    K = mu[:, None] / (mu[:, None] + mu[None, :]) * w[None, :]
    rec = cv.iterate_fixed_point(lambda H: 1.0 / (1.0 - 0.5 * albedo * K @ H), np.ones(n), method="anderson",
                                 tol=1e-13)
    H1 = 1.0 / (1.0 - 0.5 * albedo * np.sum(w / (1.0 + mu) * rec["x"]))
    return 1.0 - H1 * math.sqrt(1.0 - albedo), rec


def test_h_function_plane_albedo_converges_in_grid():
    r100, rec = _h_equation_plane_albedo(0.9, 100)
    r400, _ = _h_equation_plane_albedo(0.9, 400)
    assert abs(r100 - r400) < 1e-9
    assert rec["n_iter"] < 20                                  # Anderson(素の反復は 43 回)


# --------------------------------------------------------------------------- #
# Sequential Monte Carlo                                                      #
# --------------------------------------------------------------------------- #
def test_sequential_mean_meets_tolerance_and_reports_samples():
    r = cv.mc_sequential_mean("pi", tol=0.01)
    assert r["converged"] and r["half_width"] <= 0.01
    assert r["ci"][0] <= math.pi <= r["ci"][1]
    assert r["n_samples"] == r["history"][-1]["n"]
    # 必要な標本数は (z sigma / tol)^2 の桁(pi の標本の sigma = 4 sqrt(p(1-p)), p = pi/4)
    sd = 4.0 * math.sqrt(math.pi / 4 * (1 - math.pi / 4))
    need = (1.959964 * sd / 0.01) ** 2
    assert 0.8 * need < r["n_samples"] < 1.3 * need, (r["n_samples"], need)


def test_sequential_mean_coverage_both_sides():
    """区間の実際の被覆率(逐次に止めると名目より少し下がりうる)を 400 回で測る。名目 0.95 に対し両側で判定。"""
    hit = 0
    for s in range(400):
        r = cv.mc_sequential_mean(lambda rng, n: rng.random(n), tol=0.02, batch=64, seed=s)
        hit += r["ci"][0] <= 0.5 <= r["ci"][1]
    cov = hit / 400
    assert 0.90 <= cov <= 0.985, cov


def test_sequential_mean_refuses_when_budget_is_spent():
    with pytest.raises(cv.NotConvergedError):
        cv.mc_sequential_mean("pi", tol=1e-4, max_samples=20000)
    rec = cv.mc_sequential_mean("pi", tol=1e-4, max_samples=20000, on_fail="record")
    assert rec["mean"] is None and rec["ci"] is None and rec["last_mean"] is not None


# --------------------------------------------------------------------------- #
# MCML: Tables 6.1 / 6.2 (two-sided), H-function, energy, probes              #
# --------------------------------------------------------------------------- #
def _inside(ci, v):
    lo, hi = ci
    return lo <= v and v <= hi


def test_mcml_table_6_1_van_de_hulst():
    t = mp.MCML_TABLE_6_1
    r = mp.mc_photon_slab(t["layers"], n_photons=300_000, seed=11)
    assert _inside(r["Rd_ci"], t["Rd"]), (r["Rd_ci"], t["Rd"])
    assert _inside(r["Tt_ci"], t["Tt"]), (r["Tt_ci"], t["Tt"])
    # 区間が広すぎて素通しになっていないこと(半幅が値の 1.5 % 未満)
    assert r["Rd_ci"][1] - r["Rd"] < 0.015 * t["Rd"]
    assert r["Tt_ci"][1] - r["Tt"] < 0.015 * t["Tt"]
    assert abs(r["energy_balance"] - 1.0) < 1e-9             # 薄いスラブでは roulette まで行かない
    # 素通し(未散乱)の透過 exp(-(mua+mus) d) = exp(-2) は T_t の一部
    assert r["Tt"] > math.exp(-2.0)


def test_mcml_table_6_1_probe_wrong_anisotropy_is_excluded():
    """探針: g を 0.75 → 0.70 にすると、区間は van de Hulst の値を含まない(門は素通しでない)。"""
    t = mp.MCML_TABLE_6_1
    lay = [dict(t["layers"][0], g=0.70)]
    r = mp.mc_photon_slab(lay, n_photons=300_000, seed=11)
    assert not _inside(r["Rd_ci"], t["Rd"]) or not _inside(r["Tt_ci"], t["Tt"]), (r["Rd_ci"], r["Tt_ci"])


def test_mcml_table_6_2_giovanelli_total_reflectance():
    """Table 6.2 は R_sp + R_d(鏡面 0.04 + 拡散)で合う。拡散だけ(0.219)では合わない —— 解釈の根拠を門に残す。"""
    t = mp.MCML_TABLE_6_2
    r = mp.mc_photon_slab(t["layers"], n_photons=300_000, seed=12)
    assert abs(r["Rsp"] - 0.04) < 1e-15
    assert _inside(r["R_total_ci"], t["Rd"]), (r["R_total_ci"], t["Rd"])
    assert not _inside(r["Rd_ci"], t["Rd"])
    assert r["Tt"] == 0.0                                      # 半無限
    assert abs(r["energy_balance"] - 1.0) < 4.0 * r["energy_balance_se_bound"]


def test_mcml_table_6_2_probe_without_fresnel_is_excluded():
    """探針: 境界の屈折率差を消す(n = 1)と、内部反射が無くなって区間は 0.2600 から外れる。"""
    t = mp.MCML_TABLE_6_2
    r = mp.mc_photon_slab([dict(t["layers"][0], n=1.0)], n_photons=100_000, seed=12)
    assert not _inside(r["R_total_ci"], t["Rd"])


def test_mcml_matched_semi_infinite_against_h_function():
    """第 2 の実装: 整合境界の半無限・等方散乱(a = 0.9)の拡散反射 = 1 - H(1) sqrt(1 - a)(H 関数は決定論的に解く)。"""
    exact, _ = _h_equation_plane_albedo(0.9)
    r = mp.mc_photon_slab([{"n": 1.0, "mua": 10.0, "mus": 90.0, "g": 0.0, "d": math.inf}], n_photons=300_000, seed=13)
    assert _inside(r["Rd_ci"], exact), (r["Rd_ci"], exact)


def test_mcml_multilayer_identical_layers_equal_one_layer():
    """同じ物性の 2 層に割っても結果は変わらない(層の境界をまたぐ無次元の歩幅の持ち越し、式 3.30)。"""
    one = mp.mc_photon_slab(n_photons=200_000, seed=21)
    L = mp.MCML_TABLE_6_1["layers"][0]
    two = mp.mc_photon_slab([dict(L, d=0.007), dict(L, d=0.013)], n_photons=200_000, seed=22)
    for k in ("Rd", "Tt"):
        d = abs(one[k] - two[k])
        assert d < 4.0 * math.hypot(one[k + "_se"], two[k + "_se"]), (k, one[k], two[k])
    assert abs(sum(two["A_layers"]) - two["A"]) < 1e-12


def test_mcml_sequential_tolerance_and_budget_refusal():
    r = mp.mc_photon_slab(n_photons=2_000_000, tol=0.002, batch=20_000, seed=3)
    assert r["Rd_ci"][1] - r["Rd"] <= 0.002 and r["Tt_ci"][1] - r["Tt"] <= 0.002
    assert r["n_photons"] < 2_000_000
    with pytest.raises(cv.NotConvergedError):
        mp.mc_photon_slab(n_photons=4_000, tol=1e-4, batch=1_000)


# --------------------------------------------------------------------------- #
# Richardson-Lucy stopped by the discrepancy principle                        #
# --------------------------------------------------------------------------- #
def _scene(seed=3, sigma=2.0):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:64, 0:64]
    truth = np.full((64, 64), 5.0)
    for i, w in enumerate((1, 2, 3)):
        truth[8:56, 8 + i * 9:8 + i * 9 + w] += 200.0
    truth[((yy - 22) ** 2 + (xx - 46) ** 2) <= 64] += 80.0
    truth[((yy - 46) ** 2 + (xx - 46) ** 2) <= 16] += 160.0
    otf = ds._otf(ds._gauss_psf(sigma, truth.shape), truth.shape)
    blurred = np.fft.irfft2(np.fft.rfft2(truth) * otf, s=truth.shape)
    return truth, blurred, rng


def test_rl_poisson_discrepancy_stops_before_noise_amplification():
    truth, blurred, rng = _scene()
    y = rng.poisson(blurred).astype(float)
    errs = {}
    r = ds.iv_richardson_lucy_until(y, psf_sigma=2.0, callback=lambda k, x, d: errs.__setitem__(k, float(np.sqrt(((x - truth) ** 2).mean()))))
    assert r["stopped"] and r["status"] == "stopped"
    k = r["k_stop"]
    D = r["discrepancy_history"]
    assert D[k] <= 1.0 < D[k - 1]                             # 最初に tau = 1 を下回った反復で止める
    assert r["mass_rel_error_max"] < 1e-10                     # 補題 3.2: sum(Hx_k) = sum(y)
    # 回しすぎると雑音を増幅する(半収束): 止めた所の誤差は 20 倍回した所より小さい
    long = ds.iv_richardson_lucy_until(y, psf_sigma=2.0, tau=1e-12, max_iter=20 * k, plateau_rtol=1e-300)
    e_stop = math.sqrt(((r["image"] - truth) ** 2).mean())
    e_long = math.sqrt(((long["last_iterate"] - truth) ** 2).mean())
    assert e_stop < 0.8 * e_long, (e_stop, e_long)
    # 止めた所は誤差最小の近く(最小の 1.1 倍以内)
    assert e_stop <= 1.1 * min(errs.values()), (e_stop, min(errs.values()))


def test_rl_mass_conservation_holds_for_an_asymmetric_psf_and_the_probe_breaks_it():
    """補題 3.2 は H^T が本当に H の転置であるときに成り立つ。非対称な PSF でも op は保つ。
    探針: H^T の代わりに H を使う(非対称な PSF では転置にならない)と総和がずれる。"""
    truth, _b, rng = _scene()
    psf = np.zeros((7, 7))
    psf[3, 1:7] = [1, 2, 4, 2, 1, 0.5]
    psf[2, 3] = 1.0
    psf /= psf.sum()
    otf = ds._otf(psf, truth.shape)
    y = rng.poisson(np.fft.irfft2(np.fft.rfft2(truth) * otf, s=truth.shape)).astype(float)
    r = ds.iv_richardson_lucy_until(y, psf=psf, max_iter=50)
    assert r["mass_rel_error_max"] < 1e-10
    H = lambda v: np.fft.irfft2(np.fft.rfft2(v) * otf, s=truth.shape)       # noqa: E731
    x = np.full(y.shape, y.mean())
    worst = 0.0
    for _ in range(20):
        x = x * H(y / H(x))                                                   # 誤: 転置の代わりに H
        worst = max(worst, abs(H(x).sum() - y.sum()) / y.sum())
    assert worst > 1e-6, worst


def test_rl_wrong_psf_is_outside_the_model_range():
    """仮定の PSF が実際のボケより広いと、データは模型の値域に無い: 食い違いは tau の上で頭打ち → 値を返さない。"""
    truth, blurred, rng = _scene(sigma=1.0)
    y = rng.poisson(blurred).astype(float)
    r = ds.iv_richardson_lucy_until(y, psf_sigma=3.0)
    assert r["status"] == "outside_model_range" and r["image"] is None
    assert r["last_iterate"] is not None and r["discrepancy"] > 1.0
    ok = ds.iv_richardson_lucy_until(y, psf_sigma=1.0)
    assert ok["stopped"]


def test_rl_gaussian_morozov_and_refusals():
    truth, blurred, rng = _scene()
    sigma = 3.0
    y = blurred + 30.0 + rng.normal(0.0, sigma, blurred.shape)     # 既知の一様な底上げ(RL は y >= 0 を要る)
    assert y.min() > 0
    r = ds.iv_richardson_lucy_until(y, psf_sigma=2.0, noise="gaussian", sigma=sigma)
    assert r["stopped"] and r["discrepancy"] <= 1.0
    with pytest.raises(MetricContractError):
        ds.iv_richardson_lucy_until(y, psf_sigma=2.0)                         # 計数ではない
    with pytest.raises(MetricContractError):
        ds.iv_richardson_lucy_until(y, psf_sigma=2.0, noise="gaussian")       # sigma を推測しない
    with pytest.raises(MetricContractError):
        ds.iv_richardson_lucy_until(y - 60.0, psf_sigma=2.0, noise="gaussian", sigma=sigma)   # 負の値


def test_rl_empty_and_tiny_input_refused():
    with pytest.raises(ValueError):
        ds.iv_richardson_lucy_until(np.zeros((0, 0)))
    with pytest.raises(MetricContractError):
        ds.iv_richardson_lucy_until(np.zeros((16, 16)))


# --------------------------------------------------------------------------- #
# Ledger, public tier, fuzzer, summaries                                      #
# --------------------------------------------------------------------------- #
def test_ledger_public_tier_fuzzer_and_summaries():
    import fullseye as fs
    import opassist
    import opsconverge as oc
    import typed_catalog as tc
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opdocs
    names = list(cv.__all__) + list(mp.__all__) + list(ds.__all__)
    assert set(oc.list_ops()) == set(names)
    assert oc.missing() == []
    assert ("opsconverge", "OPSCONVERGE") in opassist._LEDGERS
    rows = {r[0]: r for r in tc.catalog() if r[0] in names}
    assert set(rows) == set(names)
    assert all(r[1] == "converge" and r[3] == "table" for r in rows.values())
    for op in ("iv_richardson_lucy_until", "mc_photon_slab"):
        assert op in cf.OP_ARG_BUILDERS
    d = json.loads((ROOT / "docs" / "i18n" / "op_summary.json").read_text(encoding="utf-8"))
    for name in names:
        assert hasattr(fs.ledger, name), name
        mod = {"converge": cv, "mcphoton": mp, "deconvstop": ds}[oc.info(name)["module"]]
        line = getattr(mod, name).__doc__.strip().splitlines()[0]
        e = d["summaries"]["converge/" + name]
        assert e["fp"] == opdocs.fingerprint(line), name
        for lang in ("ja", "zh", "tw", "ko", "de", "hi"):
            assert e[lang].strip(), (name, lang)

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sensorgeneral(EMVA 1288 Release 4.0 General)の門。

真値の出どころ:
* 線形なセンサでは General の数が Linear の数と一致する(式 12: SNR_p = SNR_y、R_d = Kη、σ_d[光子] = σ_d[e⁻]/η)。
* γ のセンサ μ_y = K^γ(η μ_p)^γ(式 13)では SNR_p = γ SNR_y(式 14)。理想センサ(光子雑音だけ)なら SNR_p = √μ_p(式 15)。
* 圧伸したセンサ(線形に撮ってから対数で 10 bit に詰める)では、圧伸の前の線形センサの入力 SNR を誤差の伝播で厳密に書ける
  —— それを General が取り戻すか。PRNU は圧伸しない同じセンサを Linear で測った値と比べる。
* 相対量子効率(式 73・74): 圧伸したセンサで仕込んだ η(λ) の比を取り戻し、印刷どおりの式 74 は光子数が波長で違うと外れる。
"""
import math

import numpy as np
import pytest

import sensorchar as S
import sensorgeneral as G

ETA, K, SD, OFF, MAX = 0.45, 0.25, 6.0, 64.0, 4095
C_LOG = 1000.0


def _log_comp(y):
    return np.round(1023.0 * np.log1p(y / C_LOG) / np.log1p(MAX / C_LOG))


def _log_comp_slope(y):
    return 1023.0 / np.log1p(MAX / C_LOG) / (C_LOG + y)


def _camera(rng, H, W, proc=None, eta=ETA):
    pix = 1.0 * rng.standard_normal((H, W))
    prnu = 1.0 + 0.008 * rng.standard_normal((H, W))

    def shot(mu_p, eta_=eta):
        y = np.clip(np.round(K * (rng.poisson(eta_ * mu_p * prnu) + rng.normal(0.0, SD, (H, W))) + OFF + pix), 0, MAX)
        return y if proc is None else proc(y)
    return shot


def _sweep(shot, psat):
    """付録 D.1: 線形な 50 段に、SNR ≈ 1 の近くまで下りる対数の 14 段を足す。"""
    mp = np.unique(np.concatenate([np.linspace(0.0, psat, 50), np.geomspace(3.0, 400.0, 14)]))
    st = [S.emva_pair_statistics(shot(m), shot(m)) for m in mp]
    return mp, np.array([s["mu"] for s in st]), np.array([s["var_temporal"] for s in st])


PSAT = 0.97 * (MAX - OFF) / (K * ETA)


def test_general_equals_linear_on_a_linear_sensor():
    rng = np.random.default_rng(41)
    mp, mu, var = _sweep(_camera(rng, 192, 240), PSAT)
    g = G.emva_general_sensitivity(mp[1:], mu[1:], var[1:], mu[0], var[0], PSAT)
    assert abs(g["Rd"] / (K * ETA) - 1) < 0.01                           # 式 (25) = Kη
    lin = S.emva_snr_curve(mp[1:][g["used"]], ETA, SD, K)[:, 1]
    m = lin > 1
    assert np.abs(g["snr_p"][m] / lin[m] - 1).max() < 0.03                # 入力 SNR = 式 21
    ex = mp[1:][g["used"]] > 0
    assert np.abs(g["snr_p"][ex] / g["snr_y"][ex] - 1)[lin[ex] > 1].max() < 0.03   # 式 12: SNR_p = SNR_y
    th = S.emva_sensitivity_threshold(ETA, SD, K)["mu_p_min"]
    assert abs(g["mu_p_min_local"] / th - 1) < 0.02
    assert abs(g["mu_p_min"] / th - 1) < 0.06                            # 規格の逆回帰(6.8 節)は揺れが大きい
    assert g["sigma_d_valid"] and abs(g["sigma_d_p"] / (SD / ETA) - 1) < 0.02   # General の式 50 = σ_d/η
    assert abs(g["snr_max"] / math.sqrt(ETA * PSAT) - 1) < 0.03             # 線形なら飽和の露光で最大 ≈ √μ_e.sat


def _gamma_camera(gam, c, eta, d0, sd, mp):
    """電子(暗雑音つき)を μ_y = c(η μ_p + d₀)^γ で読むカメラの平均と分散(式 9 の伝播、σ_p² = (η μ_p + σ_d²)/η²)。"""
    x = eta * mp
    mu = c * (x + d0) ** gam
    slope = c * gam * (x + d0) ** (gam - 1.0) * eta
    var = slope ** 2 * (x + sd ** 2) / eta ** 2
    var_dark = (c * gam * d0 ** (gam - 1.0)) ** 2 * sd ** 2
    return x, mu, var, c * d0 ** gam, var_dark


_MP_GAMMA = np.unique(np.concatenate([np.linspace(0, 4e4, 60), np.geomspace(0.5, 300.0, 25)]))[1:]


def test_gamma_sensor_input_snr_and_equation_14():
    """式 13・14: 入力 SNR の真値は線形センサの η μ_p/√(η μ_p + σ_d²)。出力 SNR との比は
    γ x (x + d₀)^(γ−1)/((x + d₀)^γ − d₀^γ)(x = η μ_p)—— d₀ = 0 なら式 14 の γ そのもの。"""
    gam, c, eta, d0, sd = 0.6, 30.0, 0.7, 3000.0, 5.0
    x, mu, var, mud, vd = _gamma_camera(gam, c, eta, d0, sd, _MP_GAMMA)
    g = G.emva_general_sensitivity(_MP_GAMMA, mu, var, mud, vd, 4e4, n_intervals=8)
    tru = x / np.sqrt(x + sd ** 2)
    m = tru > 1
    assert np.abs(g["snr_p"][m] / tru[m] - 1).max() < 0.015
    ratio = gam * x * (x + d0) ** (gam - 1.0) / ((x + d0) ** gam - d0 ** gam)
    assert np.abs(g["snr_p"] / g["snr_y"] / ratio - 1)[m].max() < 0.015
    assert abs(g["Rd"] / (c * gam * d0 ** (gam - 1.0) * eta) - 1) < 0.01
    th = (math.sqrt(sd ** 2 + 0.25) + 0.5) / eta                         # 式 26(量子化なし)
    assert abs(g["mu_p_min_local"] / th - 1) < 0.02
    r0 = gam * 1e9 * (1e9 + 1e-9) ** (gam - 1.0) / ((1e9 + 1e-9) ** gam - (1e-9) ** gam)
    assert abs(r0 - gam) < 1e-9                                          # d₀ → 0 の極限は γ(式 14)


def test_general_spline_cannot_follow_a_bend_much_narrower_than_an_interval():
    """★限界(正直に): 曲がりの尺度 d₀/η ≈ 57 光子が区間の幅 5000 光子(本文の 6〜8 等分)よりずっと小さいと、3 次スプラインは
    暗い側の傾きを追えず、入力 SNR が数十 % 外れる。sqrt の圧伸で R_d が −8〜−23 % になるのと同じ理由。"""
    gam, c, eta, d0, sd = 0.5, 30.0, 0.7, 40.0, 5.0
    x, mu, var, mud, vd = _gamma_camera(gam, c, eta, d0, sd, _MP_GAMMA)
    try:
        g = G.emva_general_sensitivity(_MP_GAMMA, mu, var, mud, vd, 4e4, n_intervals=8)
    except ValueError as e:                                              # 逆回帰が負の μ_p.min を返して拒むこともある
        assert "mu_p.min" in str(e)
        return
    tru = x / np.sqrt(x + sd ** 2)
    low = _MP_GAMMA < 4e4 / 8 / 20
    assert np.abs(g["snr_p"][low] / tru[low] - 1).max() > 0.3


def _truth_input_snr(mp):
    """圧伸の前は線形。入力に換算した分散 [光子²] = (K²(σ_d² + η μ_p) + 1/12 + (1/12)/f'²)/(Kη)²(生と圧伸後の量子化)。"""
    yr = OFF + K * ETA * mp
    return mp / np.sqrt((K ** 2 * (SD ** 2 + ETA * mp) + S.SIGMA_Q2 + S.SIGMA_Q2 / _log_comp_slope(yr) ** 2) / (K * ETA) ** 2)


def test_general_recovers_the_linear_sensor_behind_a_log_compander():
    rng = np.random.default_rng(42)
    mp, mu, var = _sweep(_camera(rng, 192, 240, proc=_log_comp), PSAT)
    g = G.emva_general_sensitivity(mp[1:], mu[1:], var[1:], mu[0], var[0], PSAT)
    assert abs(g["Rd"] / (_log_comp_slope(OFF) * K * ETA) - 1) < 0.02
    pu = mp[1:][g["used"]]
    tr = _truth_input_snr(pu)
    m = tr > 3
    assert np.abs(g["snr_p"][m] / tr[m] - 1).max() < 0.05
    assert abs(g["snr_max"] / tr.max() - 1) < 0.02
    pp = np.geomspace(1, 300, 20000)
    true_min = pp[np.argmin(np.abs(_truth_input_snr(pp) - 1))]
    assert abs(g["mu_p_min_local"] / true_min - 1) < 0.03
    # Linear で読むと: 式 51 が落ち、η は 1 を越える(嘘)
    ok = S.emva_ptc_linearity_check(mu[1:], var[1:], mu[0], var[0], float(mu[np.argmin(np.abs(mp - PSAT))]))
    assert not ok["linear_model_ok"]


def test_general_nonuniformity_is_an_identity_with_linear_on_a_linear_sensor():
    rng = np.random.default_rng(43)
    shot = _camera(rng, 96, 128)
    mp50 = 0.5 * PSAT
    dark = np.stack([shot(0.0) for _ in range(8)])
    bright = np.stack([shot(mp50) for _ in range(8)])
    lin = S.emva_spatial_nonuniformity(dark, bright, K, highpass="r4")
    mp50_eff = (lin["bright"]["mu"] - lin["dark"]["mu"]) / (K * ETA)      # 式 55 の μ_p.50(線形なら)
    gen = G.emva_general_nonuniformity(dark, bright, K * ETA, mp50_eff, K * ETA, highpass="r4")
    assert abs(gen["PRNU1288"] / lin["PRNU1288"] - 1) < 1e-12           # 式 59 = 式 67(線形の極限)
    assert abs(gen["DSNU1288_p"] * ETA / lin["DSNU1288_e"] - 1) < 1e-12  # 式 58 [光子] = 式 66 [e⁻] / η


def test_general_prnu_through_a_compander_matches_the_uncompanded_linear_prnu():
    rng = np.random.default_rng(44)
    seed_state = rng.bit_generator.state
    H, W, L = 128, 160, 16
    mp50 = 0.5 * PSAT
    raw = _camera(rng, H, W)
    lin = S.emva_spatial_nonuniformity(np.stack([raw(0.0) for _ in range(L)]), np.stack([raw(mp50) for _ in range(L)]), K, highpass="r4")
    rng.bit_generator.state = seed_state                                 # 同じ模様のセンサを圧伸して測る
    comp = _camera(rng, H, W, proc=_log_comp)
    dark = np.stack([comp(0.0) for _ in range(L)])
    bright = np.stack([comp(mp50) for _ in range(L)])
    y50 = OFF + K * ETA * mp50
    slope50 = _log_comp_slope(y50) * K * ETA                              # 真の傾き(このテストは式 55〜59 だけを見る)
    rd = _log_comp_slope(OFF) * K * ETA
    gen = G.emva_general_nonuniformity(dark, bright, slope50, mp50, rd, highpass="r4")
    assert abs(gen["PRNU1288"] / lin["PRNU1288"] - 1) < 0.05
    naive = S.emva_spatial_nonuniformity(dark, bright, K, highpass="r4")
    assert abs(naive["PRNU1288"] / lin["PRNU1288"] - 1) > 0.2              # Linear の式 67 は圧伸で外れる


def test_relative_qe_through_a_compander_and_the_printed_equation_74():
    rng = np.random.default_rng(45)
    comp = _camera(rng, 96, 128, proc=_log_comp)
    mp, mu, var = _sweep(comp, PSAT)
    etas = np.array([0.45, 0.30, 0.20, 0.38])                           # 走査の各波長の真の η(基準は 0 番)
    mps = np.array([8000.0, 15000.0, 21000.0, 5000.0])                   # 各波長の光子数(揃っていない)
    ys = np.array([0.5 * (comp(p, eta_=e).mean() + comp(p, eta_=e).mean()) for p, e in zip(mps, etas)])
    r = G.emva_general_relative_qe(mp[1:], mu[1:], mu[0], ys, mps, 0)
    assert np.abs(r["eta_rel"] / (etas / etas[0]) - 1).max() < 0.02
    assert np.abs(r["eq74_as_printed"] / (etas / etas[0]) - 1).max() > 0.5     # 印刷どおりは光子数の比が逆
    same = np.full(4, 9000.0)
    ys2 = np.array([0.5 * (comp(p, eta_=e).mean() + comp(p, eta_=e).mean()) for p, e in zip(same, etas)])
    r2 = G.emva_general_relative_qe(mp[1:], mu[1:], mu[0], ys2, same, 0)
    assert np.abs(r2["eq74_as_printed"] - r2["eta_rel"]).max() < 1e-12   # 光子数が揃えば両者は一致(9.1 節の推奨)
    naive = (ys - mu[0]) / mps / ((ys[0] - mu[0]) / mps[0])
    assert np.abs(naive / (etas / etas[0]) - 1).max() > 0.1              # 線形化しない比(Linear の式 82 の比)は圧伸で外れる


def test_general_refusals():
    mp = np.linspace(100, 1000, 20)
    with pytest.raises(ValueError, match="SNR_p <= 1"):
        G.emva_general_sensitivity(mp, 0.1 * mp + 10, 0.1 * mp * 0.1, 10.0, 1.0, 1000.0, n_intervals=3)
    with pytest.raises(ValueError, match="differ in length"):
        G.emva_general_sensitivity(mp, mp[:-1], mp, 0.0, 1.0, 1000.0)
    with pytest.raises(ValueError, match="mu_p_sat"):
        G.emva_general_sensitivity(mp, mp, mp, 0.0, 1.0, 0.0)
    with pytest.raises(ValueError, match="not extrapolated"):
        G.emva_general_relative_qe(mp, mp, 0.0, [5000.0], [10.0], 0)
    with pytest.raises(ValueError, match="ref_index"):
        G.emva_general_relative_qe(mp, mp, 0.0, [500.0], [10.0], 3)
    with pytest.raises(ValueError, match="Rd"):
        G.emva_general_nonuniformity(np.zeros((2, 30, 30)), np.ones((2, 30, 30)), 1.0, 1.0, 0.0)

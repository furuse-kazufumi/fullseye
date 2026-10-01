# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sensorchar(EMVA 1288 Release 4.0 Linear)の門。

★合成は**物理モデル**(光子のポアソン → 電子 → 暗雑音・暗電流 → K 倍 → 量子化)、推定は**規格の手順**(式 16・18・50・52・53…)で、
別々の式を往復させる。空間模様(DSNU・PRNU)を必ず混ぜる —— 一様な入力は丸め屑を構造に化けさせる入口で、空間分散の分解が
効いているかも見えない。
"""
import math

import numpy as np
import pytest

import sensorchar as S

ETA, K, SD, OFFSET, BITS = 0.62, 0.21, 3.4, 40.0, 12
H, W = 64, 96


def _patterns(rng):
    prnu = 1.0 + 0.02 * np.sin(np.linspace(0, 7, W))[None, :] + 0.01 * rng.standard_normal((H, W))
    dsnu = 1.5 * np.cos(np.linspace(0, 5, H))[:, None] + 0.8 * rng.standard_normal((H, W))
    return prnu, dsnu


def _shot(rng, mu_p, prnu, dsnu, *, eta=ETA, k=K, sd=SD, dark_e=0.0):
    """物理モデル(式 5・6・13 の向き): 光子 → 電子(ポアソン)→ 暗雑音(電子)→ 電圧 → DN(量子化・飽和)。"""
    e = rng.poisson(eta * mu_p * prnu) + (rng.poisson(dark_e, (H, W)) if dark_e > 0 else 0)
    y = k * (e + rng.normal(0.0, sd, (H, W))) + OFFSET + dsnu
    return np.clip(np.round(y), 0, (1 << BITS) - 1)


def _sweep(rng, k=K, sd=SD, n=24, top=None):
    prnu, dsnu = _patterns(rng)
    top = top if top is not None else 0.95 * ((1 << BITS) - 1 - OFFSET) / (k * ETA)
    mp = np.linspace(0.0, top, n)
    st = [S.emva_pair_statistics(_shot(rng, m, prnu, dsnu, k=k, sd=sd), _shot(rng, m, prnu, dsnu, k=k, sd=sd)) for m in mp]
    mu = np.array([s["mu"] for s in st])
    var = np.array([s["var_temporal"] for s in st])
    return mp, mu, var


def test_photon_transfer_recovers_K_and_the_dark_noise():
    rng = np.random.default_rng(1288)
    mp, mu, var = _sweep(rng)
    assert len(mu) == 24
    r = S.emva_photon_transfer(mu[1:], var[1:], mu[0], var[0], mu_y_sat=float(mu.max()))
    assert abs(r["K"] / K - 1) < 0.03
    assert r["sigma_d_valid"] and abs(r["sigma_d"] / SD - 1) < 0.05
    assert r["n_points"] >= 10
    q = S.emva_quantum_efficiency(mp[1:], mu[1:], mu[0], float(mu.max()), r["K"])
    assert abs(q["eta"] / ETA - 1) < 0.04


def test_the_intercept_is_not_the_dark_noise():
    """★σ_d を photon transfer の切片から出すと外れる(規格の推定は式 53 = 暗画像から直接)。"""
    rng = np.random.default_rng(7)
    mp, mu, var = _sweep(rng)
    r = S.emva_photon_transfer(mu[1:], var[1:], mu[0], var[0], mu_y_sat=float(mu.max()))
    sd_from_intercept = math.sqrt(max(var[0] + r["offset"] - S.SIGMA_Q2, 0.0)) / r["K"]
    assert abs(r["sigma_d"] / SD - 1) < abs(sd_from_intercept / SD - 1)


def test_the_standard_says_where_sigma_d_stops_being_measurable():
    """σ²_y.dark < 0.24 DN² では推定しない(式 53・54)。平らなセンサでは、規格が「有効」と言う側は 5 % 以内、「無効」側は外れる。
    ★画素ごとの暗レベルのずれ(DSNU)があると、それが量子化のディザになって「無効」側でも当たりやすくなる(K = 0.10 で、種 6 通り
    平ら 28〜33 % に対し模様あり 0.3〜3.5 %)—— 規格の境界は保守側で、模様の無いセンサで初めて本当の境界になる。"""
    rng = np.random.default_rng(5)
    flat_p, flat_d = np.ones((H, W)), np.zeros((H, W))
    pat_p, pat_d = _patterns(rng)
    rows, err_pat = [], {}
    for k in (0.05, 0.10, 0.21, 0.5, 1.0, 2.0):
        a, b = _shot(rng, 0.0, flat_p, flat_d, k=k), _shot(rng, 0.0, flat_p, flat_d, k=k)
        vd = S.emva_pair_statistics(a, b)["var_temporal"]
        rows.append((vd >= 0.24, abs(math.sqrt(max(vd - S.SIGMA_Q2, 0.0)) / k / SD - 1)))
        r = S.emva_photon_transfer(np.array([100.0, 500.0, 900.0]), np.array([1.0, 2.0, 3.0]) + vd, OFFSET, vd, 4095.0)
        assert r["sigma_d_valid"] == (vd >= 0.24)
        if not r["sigma_d_valid"]:
            assert r["sigma_d"] is None and r["sigma_d_upper"] == pytest.approx(0.40 / r["K"])
        a, b = _shot(rng, 0.0, pat_p, pat_d, k=k), _shot(rng, 0.0, pat_p, pat_d, k=k)
        vp = S.emva_pair_statistics(a, b)["var_temporal"]
        err_pat[k] = abs(math.sqrt(max(vp - S.SIGMA_Q2, 0.0)) / k / SD - 1)
    assert len(rows) == 6
    assert all(err < 0.05 for ok, err in rows if ok)
    assert all(err > 0.05 for ok, err in rows if not ok)
    assert sum(ok for ok, _ in rows) == 4
    assert err_pat[0.10] < 0.5 * rows[1][1]                       # ディザの効き(平らな側の誤差の半分未満)


def test_snr_identities():
    s = S.emva_sensitivity_threshold(ETA, SD, K)
    v = S.emva_snr_curve(np.array([s["mu_p_min"]]), ETA, SD, K)[0, 1]
    assert abs(v - 1.0) < 1e-12                                   # 恒等式 1: SNR(μ_p.min) = 1(式 26 と式 21 は独立)
    mp = np.logspace(-1, 5, 200)
    c = S.emva_snr_curve(mp, 1.0, 0.0, 1.0, sigma_q2=0.0)
    assert np.abs(c[:, 1] - np.sqrt(mp)).max() < 1e-9            # 恒等式 2: 理想センサ = √μ_p(式 23)
    assert s["mu_e_min"] > SD                                     # 量子化雑音があるかぎり μ_e.min > σ_d(式 27)
    c = S.emva_snr_curve(np.logspace(-3, 7, 400), ETA, SD, K)
    sl = np.diff(np.log(c[:, 1])) / np.diff(np.log(c[:, 0]))
    assert abs(sl[0] - 1.0) < 0.01 and abs(sl[-1] - 0.5) < 0.01   # 式 (22): 傾き 1 → 1/2


def test_dynamic_range():
    r = S.emva_dynamic_range(1.0e5, 10.0)
    assert (r["ratio"], r["dB"], r["bits"]) == pytest.approx((1.0e4, 80.0, math.log2(1.0e4)))


def test_linearity_error_matches_an_independent_weighted_fit():
    """式 (59)〜(61) の閉形式が、numpy の重みつき最小二乗(重み 1/y、残差の 2 乗に 1/y²)と一致する。"""
    Hs = np.linspace(1.0, 100.0, 12)
    y = 30.0 * Hs * (1.0 + 0.002 * Hs)                             # 既知の非線形
    r = S.emva_linearity_error(Hs, y + OFFSET, OFFSET, float(y.max()) + OFFSET)
    use = r["used"]
    assert use.sum() >= 9
    a1, a0 = np.polyfit(Hs[use], y[use], 1, w=1.0 / y[use])
    assert r["a0"] == pytest.approx(a0, rel=1e-9) and r["a1"] == pytest.approx(a1, rel=1e-9)
    straight = S.emva_linearity_error(Hs, 30.0 * Hs + OFFSET, OFFSET, 3000.0 + OFFSET)
    assert straight["LE_percent"] < 1e-9 < r["LE_percent"]


def test_dark_current_recovers_the_slope():
    rng = np.random.default_rng(3)
    prnu, dsnu = _patterns(rng)
    mu_I_e = 150.0                                                # e⁻/s
    t = np.linspace(0.0, 1.0, 8)
    stats = [S.emva_pair_statistics(_shot(rng, 0.0, prnu, dsnu, dark_e=mu_I_e * tt),
                                    _shot(rng, 0.0, prnu, dsnu, dark_e=mu_I_e * tt)) for tt in t]
    assert len(stats) == 8
    r = S.emva_dark_current(t, [s["mu"] for s in stats], K, var_y_dark=[s["var_temporal"] for s in stats])
    assert abs(r["mu_I_e"] / mu_I_e - 1) < 0.03
    assert abs(r["mu_I_e_from_var"] / mu_I_e - 1) < 0.10          # 分散からの推定は粗い(規格も平均を推す)


def test_spatial_split_and_dsnu_prnu():
    """既知の列・行・画素の模様を積み、式 (42) の分解と式 (66)(67) が元の値を返すか。"""
    rng = np.random.default_rng(11)
    L = 32
    col = 1.2 * rng.standard_normal(W)[None, :]
    row = 0.7 * rng.standard_normal(H)[:, None]
    pix = 0.9 * rng.standard_normal((H, W))
    dsnu = col + row + pix
    prnu_map = 1.0 + 0.015 * rng.standard_normal((H, W))
    dark = np.stack([_shot(rng, 0.0, prnu_map, dsnu) for _ in range(L)])
    mp50 = 0.5 * ((1 << BITS) - 1 - OFFSET) / (K * ETA)
    bright = np.stack([_shot(rng, mp50, prnu_map, dsnu) for _ in range(L)])
    r = S.emva_spatial_nonuniformity(dark, bright, K)
    d = r["dark"]
    for got, truth in ((d["s2_col"], col.var()), (d["s2_row"], row.var()), (d["s2_pixel"], pix.var())):
        assert abs(got / truth - 1) < 0.10, (got, truth)
    assert abs(r["DSNU1288_e"] / (dsnu.std() / K) - 1) < 0.05
    signal = K * ETA * mp50
    assert abs(r["PRNU1288"] / (signal * prnu_map.std() / signal) - 1) < 0.10
    # 時間雑音の残りを引かないと空間分散は過大(式 36 が効いている証拠)
    avg = dark.mean(axis=0)
    assert avg.var() > d["s2"]


def test_defect_pixels_counts_the_planted_outliers():
    rng = np.random.default_rng(2)
    L = 16
    img = OFFSET + np.round(rng.normal(0.0, 1.0, (H, W)) * L) / L
    hot = [(3, 5), (10, 40), (33, 7), (50, 90), (60, 1), (20, 20), (41, 66)]
    for (i, j) in hot:
        img[i, j] += 25.0
    r = S.emva_defect_pixels(img, L, threshold=12.0)
    assert r["n_above"] == len(hot)
    assert r["hist_counts"].sum() == H * W and len(r["hist_counts"]) <= 256
    assert r["accum_percent"][0] == pytest.approx(100.0)
    assert r["accum_percent"][-1] == pytest.approx(100.0 / (H * W))


def test_fail_closed():
    with pytest.raises(ValueError, match="shape"):
        S.emva_pair_statistics(np.zeros((4, 4)), np.zeros((4, 5)))
    with pytest.raises(ValueError, match="NaN"):
        S.emva_pair_statistics(np.full((4, 4), np.nan), np.zeros((4, 4)))
    with pytest.raises(ValueError, match="0-70"):
        S.emva_photon_transfer([3000.0, 3500.0, 3900.0], [1.0, 2.0, 3.0], 40.0, 1.0, 4000.0)
    with pytest.raises(ValueError, match="slope"):
        S.emva_photon_transfer([100.0, 200.0, 300.0], [3.0, 2.0, 1.0], 40.0, 1.0, 4000.0)
    with pytest.raises(ValueError, match="eta"):
        S.emva_snr_curve([1.0], 1.2, 1.0, 1.0)
    with pytest.raises(ValueError, match="exceed"):
        S.emva_dynamic_range(5.0, 10.0)
    with pytest.raises(ValueError, match="six"):
        S.emva_dark_current([0.0, 1.0, 2.0], [1.0, 2.0, 3.0], 1.0)
    with pytest.raises(ValueError, match="at least 2 images"):
        S.emva_spatial_nonuniformity(np.zeros((1, 4, 4)), np.ones((3, 4, 4)), 1.0)
    with pytest.raises(ValueError, match="constant"):
        S.emva_defect_pixels(np.ones((4, 4)), 4, 1.0)
    with pytest.raises(ValueError, match="positive integer"):
        S.emva_defect_pixels(np.arange(16.0).reshape(4, 4), 0, 1.0)


#: 公表値の門で食い違いが出た型番(台帳の値は直さない —— 一次情報で確かめてから)。
#: IMX287: 飽和 21.0 ke⁻・暗雑音 7 e⁻ からは DR ≈ 69 dB なのに、台帳の DR は 74 dB。暗雑音の欄か DR の欄のどちらかが
#: 別の条件の値と見られる(2026-10-01、未確認)。
_DR_UNEXPLAINED = {"IMX287"}


def test_published_datasheet_values_obey_eq_55_and_eq_28():
    """メーカーが公表した EMVA 1288 の値(optscene の台帳、38 型番、整数に丸めた値)で式を検算する。
    最大 SNR = √μ_e.sat(式 55)は全型番で丸めの幅(0.5 dB)以内。DR = μ_p.sat/μ_p.min(式 28、K は公表されないので
    量子化雑音を 0 とみなす)は暗雑音が整数に丸めてあるぶん 3 dB 以内、1 型番は説明できない(名指しで除外)。"""
    import optscene
    cat = optscene._SENSOR_CATALOG
    assert len(cat) >= 30
    bad_snr, bad_dr = [], []
    for model, v in cat.items():
        qe, sd, sat, dr_db, snr_db = v[6] / 100.0, v[7], v[8] * 1e3, v[9], v[10]
        if abs(20.0 * math.log10(math.sqrt(sat)) - snr_db) > 0.5:
            bad_snr.append(model)
        t = S.emva_sensitivity_threshold(qe, sd, 1.0, sigma_q2=0.0)
        d = S.emva_dynamic_range(sat / qe, t["mu_p_min"])["dB"]
        if abs(d - dr_db) > 3.0:
            bad_dr.append(model)
    assert bad_snr == []
    assert set(bad_dr) == _DR_UNEXPLAINED, bad_dr

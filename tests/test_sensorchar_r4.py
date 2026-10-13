# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sensorchar の 2026-10-13 追加分(EMVA 1288 Release 4.0 Linear の残りの式と、前提を確かめる道具)の門。

真値の出どころ(同じ式を往復させない):
* 高域フィルタ(8.1 節): 白い雑音の分散の利得をカーネルから数えた値 = 乱数の画像に実際にかけた分散比。伝達関数 = 正弦波に
  実際にかけた振幅比。3 % の照明のむら(規格 5 節の模擬カメラ)を入れて PRNU が仕込んだ値に戻るか。
* 付録 C.5 の式 (86)(87) の 0.92 / 0.64 は、Parseval の 0.96 / 0.80 と実測で区別できる(印刷の誤り)。
* スペクトログラム(式 70〜72): Parseval(P の平均 = 分散)、整数の升の正弦波の振幅が式 72 で厳密に戻る。
* B-スプライン(General 式 44〜49): scipy の make_lsq_spline(別実装)と一致、3 次式を厳密に再現、導関数 = 有限差分。
  印刷どおりの式 (49) の外側の枝は有限差分と合わない。
* 式 51: 線形なセンサ(十分な画素数)は通り、圧伸したセンサは落ちる。小さい画像では線形でも落ちうる(雑音)。
* 線形な前処理の閉形式(:func:`emva_filter_distortion`)= 画像に実際にかけて規格の手順で測った K・η・σ_d・相関。
"""
import math

import numpy as np
import pytest

import sensorchar as S

ETA, K, SD, OFF, BITS = 0.45, 0.25, 6.0, 64.0, 12
MAX = (1 << BITS) - 1


def _box3(y):
    return sum(np.roll(np.roll(y, i, 0), j, 1) for i in (-1, 0, 1) for j in (-1, 0, 1)) / 9.0


def _patterns(rng, H, W):
    col = 0.6 * rng.standard_normal(W)[None, :]
    pix = 1.0 * rng.standard_normal((H, W))
    prnu = 1.0 + 0.008 * rng.standard_normal((H, W))
    return col, pix, prnu


def _camera(rng, H, W, proc=None):
    col, pix, prnu = _patterns(rng, H, W)

    def shot(mu_p):
        e = rng.poisson(ETA * mu_p * prnu)
        y = np.clip(np.round(K * (e + rng.normal(0.0, SD, (H, W))) + OFF + col + pix), 0, MAX)
        return y if proc is None else proc(y)
    return shot


def _sweep(shot, n=50):
    psat = (MAX - OFF) / (K * ETA)
    mp = np.linspace(0.0, psat, n)
    st = [S.emva_pair_statistics(shot(m), shot(m)) for m in mp]
    mu = np.array([s["mu"] for s in st])
    var = np.array([s["var_temporal"] for s in st])
    return mp, mu, var, float(mu[int(np.argmax(var))])


# ───────────────────────────── 8.1 節 高域フィルタ ─────────────────────────────
@pytest.mark.parametrize("method,line,gain", [("r4", False, None), ("r3.1", False, 0.96), ("r3.1", True, 0.80)])
def test_highpass_white_gain_counted_from_the_kernel_equals_the_measured_variance(method, line, gain):
    rng = np.random.default_rng(11)
    img = rng.standard_normal((300, 360))
    h = S.emva_highpass(img, method=method, line_scan=line)
    meas = float(h["image"].var())
    sigma = math.sqrt(2.0 / h["image"].size)                            # 分散の推定の相対の揺れ(白い雑音)
    assert abs(meas / h["white_variance_gain"] - 1) < 4 * sigma
    if gain is not None:
        assert abs(h["white_variance_gain"] - gain) < 1e-12              # Parseval: 1 − 1/P²(2-D)・1 − 1/P(1-D)


def test_appendix_c5_printed_factors_are_not_what_the_filter_does():
    """付録 C.5 の式 86・87 の 0.92 / 0.64 は (1 − 1/P²)² / (1 − 1/P)²。実際の分散比は 0.96 / 0.80(実測で区別できる)。"""
    rng = np.random.default_rng(12)
    img = rng.standard_normal((400, 400))
    a = S.emva_highpass(img, method="r3.1")["image"].var()
    b = S.emva_highpass(img, method="r3.1", line_scan=True)["image"].var()
    assert abs(a - 0.96) < 0.01 and abs(a - 0.92) > 0.03
    assert abs(b - 0.80) < 0.01 and abs(b - 0.64) > 0.1


def test_highpass_transfer_matches_a_filtered_sinusoid_and_the_appendix_e3_claims():
    n = np.arange(400)
    for method in ("r4", "r3.1"):
        h = S.emva_highpass(np.zeros((40, 40)), method=method)
        for kt in (0.05, 0.1, 0.2, 0.37, 0.6, 0.9):
            img = np.repeat(np.cos(np.pi * kt * n)[None, :], 30, axis=0)
            out = S.emva_highpass(img, method=method)["image"]
            amp = np.sqrt(2.0 * (out[5] ** 2).mean())                   # 実際にかけた振幅比
            assert abs(amp - abs(np.interp(kt, h["transfer_k"], h["transfer"]))) < 0.02
    r4 = S.emva_highpass(np.zeros((40, 40)), method="r4")
    r31 = S.emva_highpass(np.zeros((40, 40)), method="r3.1")
    hi = r4["transfer_k"] >= 0.2
    assert np.abs(r4["transfer"][hi] - 1).max() < 0.05                  # E.3: 高域で 1 に近い
    hi31 = r31["transfer_k"] >= 0.4
    # E.3 は旧版が高域で「0.8〜1.2 で揺れる」と書く。厳密には 1 − (5 の箱) の最小 0.80・最大 1.25(箱の負の側葉 −0.25)
    assert abs(r31["transfer"][hi31].min() - 0.80) < 0.01 and abs(r31["transfer"][hi31].max() - 1.25) < 0.01
    t20 = lambda h: np.interp(0.1, h["transfer_k"], h["transfer"])       # 波長 20 画素(k̃ = 0.1)
    assert t20(r4) > 5 * t20(r31)                                        # E.3: 新しいフィルタは長い波長をずっと多く残す


def _standard_example_camera(rng, H=240, W=320):
    """Linear 5 節の最後の段落の模擬カメラ(DSNU 白 1.5 DN + 振幅 1.5 DN の正弦 2 本、PRNU 白 0.5 %、照明 3 % の 2 次の落ち)。"""
    n, m = np.arange(W), np.arange(H)
    dsnu = 1.5 * rng.standard_normal((H, W)) + 1.5 * np.sin(2 * np.pi * 0.04 * n + 0.7)[None, :] \
        + 1.5 * np.sin(2 * np.pi * 0.2 * m + 0.2)[:, None]
    prnu = 1.0 + 0.005 * rng.standard_normal((H, W))
    yy, xx = np.mgrid[0:H, 0:W]
    r2 = ((xx - (W - 1) / 2) ** 2 + (yy - (H - 1) / 2) ** 2) / (((W - 1) / 2) ** 2 + ((H - 1) / 2) ** 2)
    illum = 1.0 - 0.03 * r2

    def shot(mp):
        return np.clip(np.round(0.1 * (rng.poisson(0.5 * mp * prnu * illum) + rng.normal(0, 30.0, (H, W))) + 29.4 + dsnu), 0, MAX)
    return shot


def test_highpass_removes_the_illumination_falloff_from_prnu_and_dsnu_follows_the_transfer():
    rng = np.random.default_rng(13)
    shot = _standard_example_camera(rng)
    mp50 = 0.5 * (MAX - 29.4) / (0.1 * 0.5)
    dark = np.stack([shot(0.0) for _ in range(16)])
    bright = np.stack([shot(mp50) for _ in range(16)])
    raw = S.emva_spatial_nonuniformity(dark, bright, 0.1)
    hp = S.emva_spatial_nonuniformity(dark, bright, 0.1, highpass="r4")
    g2 = hp["highpass"]["white_variance_gain"]
    assert raw["PRNU1288"] > 1.4 * 0.005                                 # 照明のむらが PRNU に化ける
    assert abs(hp["PRNU1288"] / (0.005 * math.sqrt(g2)) - 1) < 0.03
    h = S.emva_highpass(np.zeros((40, 40)))
    T = lambda k: np.interp(k, h["transfer_k"], h["transfer"])
    pred = math.sqrt(g2 * 1.5 ** 2 + 1.5 ** 2 / 2 * T(0.08) ** 2 + 1.5 ** 2 / 2 * T(0.4) ** 2) / 0.1
    assert abs(hp["DSNU1288_e"] / pred - 1) < 0.02


@pytest.mark.parametrize("method", ["r4", "r3.1"])
def test_highpass_residual_temporal_noise_is_subtracted_with_the_filter_gain(method):
    """模様の無い積み重ね(時間雑音だけ)では、高域フィルタの後の空間分散は 0 に戻るべき(式 36 の引き算の不偏性)。
    平均画像の時間雑音 σ²/L もフィルタを通るので、引く量は 白い利得 × σ²/L。利得を忘れると r4 で −1.2 %・r3.1 で −4 % の偏り。"""
    rng = np.random.default_rng(16)
    L = 2
    stack = rng.standard_normal((L, 600, 600))
    st = S._nonuniformity_variances(stack, stack + 5.0 + rng.standard_normal((L, 600, 600)), method, "t")
    resid = st["var_temporal_dark"] / L
    assert abs(st["dark"]["s2"] / resid) < 0.006                         # 揺れは約 0.0024(√(2/n))


def test_highpass_refusals():
    with pytest.raises(ValueError, match="line-scan"):
        S.emva_highpass(np.zeros((50, 50)), method="r4", line_scan=True)
    with pytest.raises(ValueError, match="method"):
        S.emva_highpass(np.zeros((50, 50)), method="box")
    with pytest.raises(ValueError, match="too small"):
        S.emva_highpass(np.zeros((15, 50)))
    with pytest.raises(ValueError, match="NaN"):
        S.emva_highpass(np.full((50, 50), np.nan))
    with pytest.raises(ValueError, match="highpass"):
        S.emva_spatial_nonuniformity(np.zeros((2, 30, 30)), np.ones((2, 30, 30)), 1.0, highpass="yes")


# ───────────────────────────── 8.6 節 スペクトログラム ─────────────────────────────
def test_spectrogram_parseval_and_equation_72_amplitude():
    rng = np.random.default_rng(14)
    M, N = 64, 200
    n = np.arange(N)
    img = 0.7 * rng.standard_normal((M, N))
    sg = S.emva_spectrogram(img)
    assert abs(sg["mean_power"] - sg["variance"]) < 1e-12 * sg["variance"]   # P の平均 = 空間分散
    assert abs(sg["white_floor"] / 0.49 - 1) < 0.1
    pure = 1.3 * np.sin(2 * np.pi * 0.05 * n + 0.4)[None, :] * np.ones((M, 1))   # 0.05 × 200 = 10 升目(整数)
    a = S.emva_spectrogram(pure, band=(0.05, 0.05))
    assert abs(a["amplitude"] - 1.3) < 1e-9
    v = S.emva_spectrogram(pure.T, axis="vertical", band=(0.045, 0.055))
    assert abs(v["amplitude"] - 1.3) < 1e-9
    noisy = pure + 0.7 * rng.standard_normal((M, N))
    b = S.emva_spectrogram(noisy, band=(0.04, 0.06))
    assert b["amplitude"] > 1.3 and abs(b["amplitude_above_floor"] - 1.3) < 0.05


def test_spectrogram_refusals():
    with pytest.raises(ValueError, match="axis"):
        S.emva_spectrogram(np.zeros((8, 8)), axis="diagonal")
    with pytest.raises(ValueError, match="band"):
        S.emva_spectrogram(np.zeros((8, 8)), band=(0.3, 0.1))
    with pytest.raises(ValueError, match="no frequency"):
        S.emva_spectrogram(np.zeros((8, 8)), band=(0.13, 0.14))
    with pytest.raises(ValueError, match="at least 4"):
        S.emva_spectrogram(np.zeros((8, 3)))


# ───────────────────────────── SNR(式 21・25・26・69)と光子数(式 3・4) ─────────────────────────────
def test_total_snr_reduces_to_equation_21_and_saturates_at_one_over_prnu():
    p = np.logspace(-1, 9, 300)
    c = S.emva_total_snr(p, ETA, SD, K, 0.0, 0.0)
    assert np.allclose(c[:, 2], c[:, 1], rtol=1e-12) and np.allclose(c[:, 1], S.emva_snr_curve(p, ETA, SD, K)[:, 1], rtol=1e-12)
    t = S.emva_total_snr(p, ETA, SD, K, 10.0, 0.01)
    assert (t[:, 2] <= t[:, 1] + 1e-12).all()
    assert abs(t[-1, 2] * 0.01 - 1) < 1e-3                               # 明るい側で 1/PRNU に頭打ち
    with pytest.raises(ValueError, match="prnu"):
        S.emva_total_snr(p, ETA, SD, K, 0.0, -0.1)


def test_exposure_for_snr_inverts_equation_21_and_gives_equation_26_at_one():
    s = np.logspace(-2, 3, 200)
    mp = S.emva_exposure_for_snr(s, ETA, SD, K)
    back = S.emva_snr_curve(mp, ETA, SD, K)[:, 1]
    assert np.allclose(back, s, rtol=1e-10)
    th = S.emva_sensitivity_threshold(ETA, SD, K)["mu_p_min"]
    assert abs(S.emva_exposure_for_snr(1.0, ETA, SD, K)[0] / th - 1) < 1e-12
    with pytest.raises(ValueError, match="> 0"):
        S.emva_exposure_for_snr([0.0, 1.0], ETA, SD, K)


def test_photon_exposure_constant_is_50_34_and_matches_equation_3_in_si():
    mp = S.emva_photon_exposure(1.0, 1.0, 1.0, 1.0)[0]
    assert round(mp, 2) == 50.34                                         # 式 (4) の印刷値
    A, t, lam, E = 3.45 ** 2, 2.5, 0.53, 7.0                            # µm², ms, µm, µW/cm²
    si = (A * 1e-12) * (E * 1e-2) * (t * 1e-3) / (6.6260755e-34 * 2.99792458e8 / (lam * 1e-6))   # 式 (3)
    assert abs(S.emva_photon_exposure([E], A, t, lam)[0] / si - 1) < 1e-12
    with pytest.raises(ValueError, match=">= 0"):
        S.emva_photon_exposure([-1.0], A, t, lam)


# ───────────────────────────── B-スプライン(General 式 44〜49)と式 51 ─────────────────────────────
def test_bspline_equals_an_independent_implementation_and_reproduces_cubics():
    interpolate = pytest.importorskip("scipy.interpolate")
    rng = np.random.default_rng(15)
    x = np.sort(rng.uniform(0, 10, 70))
    y = np.sin(x) + 0.1 * rng.standard_normal(70)
    for P in (3, 6, 8):
        r = S.emva_bspline_regression(x, y, n_intervals=P, x_max=10.0)
        t = (10.0 / P) * np.arange(-3, P + 4)
        sp = interpolate.make_lsq_spline(x, y, t, k=3)
        assert np.abs(sp(x) - r["fit"]).max() < 1e-10
        assert np.abs(sp.derivative()(x) - r["slope"]).max() < 1e-10       # 連鎖律の 1/Δ を含む傾き
    c = [0.3, -1.1, 2.0, 0.7]
    yc = np.polyval(c, x)
    rc = S.emva_bspline_regression(x, yc, n_intervals=5, x_max=10.0, x_eval=[0.0, 10.0])
    assert np.abs(rc["fit"] - yc).max() < 1e-9
    assert np.abs(rc["slope_eval"] - np.polyval(np.polyder(c), [0.0, 10.0])).max() < 1e-8


def test_bspline_derivative_and_the_printed_sign_of_equation_49():
    x = np.linspace(-2.4, 2.4, 2001)
    fd = (S._beta3(x + 1e-6) - S._beta3(x - 1e-6)) / 2e-6
    assert np.abs(fd - S._beta3_prime(x)).max() < 1e-8
    a = np.abs(x)
    printed = np.where(a < 1, -2 * x * (1 - 0.75 * a), np.where(a <= 2, x / (2 * np.maximum(a, 1e-300)) * (2 - a) ** 2, 0.0))
    outer = (a > 1.05) & (a < 1.95)
    assert np.abs(fd - printed)[outer].min() > 1e-3                      # 印刷どおりの外側の枝は符号が逆
    assert np.abs(fd - printed)[a < 0.95].max() < 1e-8                   # 内側の枝は印刷どおりで正しい


def test_bspline_refusals():
    x = np.linspace(0, 1, 8)
    with pytest.raises(ValueError, match="Q > P"):
        S.emva_bspline_regression(x, x, n_intervals=6)
    with pytest.raises(ValueError, match="too few points"):
        S.emva_bspline_regression(np.r_[np.linspace(0, 0.2, 30), 1.0], np.zeros(31), n_intervals=8)
    with pytest.raises(ValueError, match="not extrapolated"):
        S.emva_bspline_regression(np.linspace(0, 1, 30), np.zeros(30), n_intervals=3, x_eval=[1.5])
    with pytest.raises(ValueError, match="x must lie"):
        S.emva_bspline_regression(np.linspace(-1, 1, 30), np.zeros(30), n_intervals=3, x_max=1.0)
    with pytest.raises(ValueError, match="positive integer"):
        S.emva_bspline_regression(x, x, n_intervals=2.0)


def test_equation_51_accepts_a_linear_sensor_and_rejects_a_companded_one():
    """★画素数が要る: 2 枚の差の分散の揺れ √(2/NM) が局所の傾きの揺れになる。乱数 12 通りの実測で、
    512 × 640 は全部 3 % 未満(最大 1.4 %)、256 × 320 は 12 中 1 が、128 × 160 は 6 中 3 が線形なのに落ちた。"""
    rng = np.random.default_rng(21)
    mp, mu, var, mus = _sweep(_camera(rng, 512, 640))
    ok = S.emva_ptc_linearity_check(mu[1:], var[1:], mu[0], var[0], mus)
    assert ok["linear_model_ok"] and ok["mean_rel_dev"] < 0.03
    assert abs(ok["sum_rel_dev"] / ok["n_points"] - ok["mean_rel_dev"]) < 1e-12
    comp = _camera(rng, 128, 160, proc=lambda y: np.round(1023.0 * np.log1p(y / 1000.0) / np.log1p(MAX / 1000.0)))
    mp2, mu2, var2, _ = _sweep(comp)
    bad = S.emva_ptc_linearity_check(mu2[1:], var2[1:], mu2[0], var2[0], float(mu2.max()))
    assert not bad["linear_model_ok"] and bad["mean_rel_dev"] > 0.5


# ───────────────────────────── 前提 3 と前処理の閉形式 ─────────────────────────────
def _blend(a):
    w = np.full((3, 3), a / 9.0)
    w[1, 1] += 1.0 - a
    return w


def test_whiteness_of_a_raw_camera_and_of_filtered_ones_matches_the_kernel_prediction():
    rng = np.random.default_rng(31)
    raw = _camera(rng, 128, 160)
    for _ in range(3):
        assert S.emva_noise_whiteness(raw(800.0), raw(800.0), raw(800.0))["white"]
    for w, sign in ((_blend(0.3), 1), (np.eye(3)[1:2, :].T @ np.eye(3)[1:2, :] * 1.5 - _blend(1.0) * 0.5, -1)):
        cam = _camera(rng, 128, 160, proc=lambda y, w=w: np.round(sum(w[i + 1, j + 1] * np.roll(np.roll(y, -i, 0), -j, 1)
                                                                           for i in (-1, 0, 1) for j in (-1, 0, 1))))
        wh = S.emva_noise_whiteness(cam(800.0), cam(800.0))
        fd = S.emva_filter_distortion(w)
        assert not wh["white"] and np.sign(wh["rho_h"]) == sign
        assert abs(wh["rho_h"] - fd["rho_h"]) < 0.02 and abs(wh["rho_v"] - fd["rho_v"]) < 0.02
        assert abs(wh["variance_ratio_2x2"] - fd["variance_ratio_2x2"]) < 0.06


def test_whiteness_sees_a_recursive_temporal_filter():
    rng = np.random.default_rng(32)
    raw = _camera(rng, 256, 320)
    alpha = 0.8
    y = raw(800.0)
    for _ in range(12):                                                 # 立ち上がりを捨てる
        y = alpha * raw(800.0) + (1 - alpha) * y
    frames = []
    for _ in range(3):
        y = alpha * raw(800.0) + (1 - alpha) * y
        frames.append(np.round(y))
    wh = S.emva_noise_whiteness(*frames)
    # 再帰の画像どうしの差は独立でないので、ρ_t の揺れは白い場合の √(3/n) より大きい(乱数 6 通りで ±0.03)
    assert not wh["white"] and abs(wh["rho_t"] - (1 - alpha)) < 0.04 and abs(wh["rho_h"]) < 0.02


def test_filter_distortion_closed_forms_match_the_standard_procedure_on_filtered_cameras():
    rng = np.random.default_rng(33)
    cases = {"gain2": np.array([[2.0]]), "denoise": _blend(0.3),
             "sharpen": np.eye(3)[1:2, :].T @ np.eye(3)[1:2, :] * 1.5 - _blend(1.0) * 0.5}
    for name, w in cases.items():
        fd = S.emva_filter_distortion(w)
        cam = _camera(rng, 192, 240, proc=lambda y, w=w: np.clip(np.round(sum(
            w[i + w.shape[0] // 2, j + w.shape[1] // 2] * np.roll(np.roll(y, -i, 0), -j, 1)
            for i in range(-(w.shape[0] // 2), w.shape[0] // 2 + 1) for j in range(-(w.shape[1] // 2), w.shape[1] // 2 + 1))), 0, MAX))
        psat = (MAX / fd["G"] - OFF - 30) / (K * ETA) if fd["G"] > 1 else (MAX - OFF - 60) / (K * ETA) / 1.3
        mp = np.linspace(0.0, psat, 40)
        st = [S.emva_pair_statistics(cam(m), cam(m)) for m in mp]
        mu = np.array([s["mu"] for s in st])
        var = np.array([s["var_temporal"] for s in st])
        ptc = S.emva_photon_transfer(mu[1:], var[1:], mu[0], var[0], float(mu[-1]))
        qe = S.emva_quantum_efficiency(mp[1:], mu[1:], mu[0], float(mu[-1]), ptc["K"])
        assert abs(ptc["K"] / (K * fd["K_factor"]) - 1) < 0.02, name
        assert abs(qe["eta"] / (ETA * fd["eta_factor"]) - 1) < 0.02, name
        # σ_d: 量子化を含めた厳密な予測(生の量子化雑音 1/12 もフィルタを通る。gain2 は整数倍なので再量子化の雑音が無い)
        requant = 0.0 if name == "gain2" else S.SIGMA_Q2
        sd_pred = math.sqrt(fd["sum_w2"] * (K ** 2 * SD ** 2 + S.SIGMA_Q2) + requant - S.SIGMA_Q2) / (K * fd["K_factor"])
        assert abs(ptc["sigma_d"] / sd_pred - 1) < 0.03, name


def test_filter_distortion_pattern_gains_by_component():
    rng = np.random.default_rng(34)
    H, W = 256, 256
    col = rng.standard_normal(40000)[None, :] * np.ones((3, 1))        # 長い列の模様(期待値の利得に近づける)
    pix = rng.standard_normal((H, W))
    w = _blend(0.5)
    f = lambda y: sum(w[i + 1, j + 1] * np.roll(np.roll(y, -i, 0), -j, 1) for i in (-1, 0, 1) for j in (-1, 0, 1))
    fd = S.emva_filter_distortion(w)
    assert abs(f(col).var() / col.var() / fd["pattern_gain"]["col"] - 1) < 0.02     # 列の模様は 1-D の利得
    assert abs(f(pix).var() / pix.var() / fd["pattern_gain"]["pixel"] - 1) < 0.03
    t = S.emva_filter_distortion([[1.0]], temporal_alpha=0.5)
    assert abs(t["S"] - 0.25 / 1.5) < 1e-15 and abs(t["eta_factor"] - 6.0) < 1e-12
    for bad in ([[1.0, -1.0]], [[0.0]]):
        with pytest.raises(ValueError, match="positive gain"):
            S.emva_filter_distortion(bad)
    with pytest.raises(ValueError, match="temporal_alpha"):
        S.emva_filter_distortion([[1.0]], temporal_alpha=1.5)


def test_defect_histogram_accumulated_bins_of_equations_78_to_81():
    rng = np.random.default_rng(35)
    L = 16
    avg = np.round(rng.normal(100.0, 2.0, (64, 80)) * L) / L
    avg.flat[:5] += 30.0
    dp = S.emva_defect_pixels(avg, L, threshold=10.0)
    Hc = dp["accum_counts"]
    assert Hc[0] == avg.size and (np.diff(Hc) <= 0).all()
    dev = np.abs(avg - avg.mean()).ravel()
    I = int(math.floor(L * dev.max() / 256.0)) + 1
    for q in (0, 3, 17, len(Hc) - 1):                                  # H[q] = 偏差が q·I/L 以上の画素の数(別の数え方)
        assert Hc[q] == int((dev >= q * I / L - 1e-9).sum())
    assert dp["n_above"] == 5

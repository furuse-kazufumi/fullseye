"""フーリエ以外の積分変換(Abel / Hankel / Laplace)と s 領域の線形系の門(2026-10-03)。

棚卸しで Laplace の系統が 0 本、Abel・Hankel も 0 本だった。門は閉じた式と定理だけで立てる
(記憶から写した公表値は使わない)。逆問題は独立な 2 経路を持ち、互いに突き合わせる。
"""
import math
import warnings

import numpy as np
import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import fullseye as fs
    import mathtransforms as M
    import opsmath

LEDGER = ["abel_transform", "abel_inverse", "abel_inverse_image", "abel_revolve", "hankel_transform", "tf_poles_zeros", "tf_freq_response",
          "tf_impulse_response", "tf_step_response", "tf_bilinear", "laplace_inverse_talbot",
          "dct_transform", "wavelet_filters", "dwt_transform", "dwt_inverse"]


# ---- 公開経路 --------------------------------------------------------------------- #
def test_every_function_is_public_and_the_ledger_is_complete():
    assert opsmath.missing() == []
    assert sorted(opsmath.list_ops("transform")) == sorted(LEDGER)
    for n in M.__all__:
        assert callable(getattr(fs, n)) and n in fs.__all__, n
        assert (getattr(M, n).__doc__ or "").strip(), n
    for n in LEDGER:
        assert callable(getattr(fs.ledger, n)), n
    assert set(M.__all__) == set(LEDGER) | {"laplace_inverse_func"}


# ---- Abel ------------------------------------------------------------------------- #
def _gauss(sigma, n):
    dr = 8 * sigma / n
    r = np.arange(n) * dr
    return dr, np.exp(-r**2 / sigma**2), math.sqrt(math.pi) * sigma * np.exp(-r**2 / sigma**2)


@pytest.mark.parametrize("sigma", [1.0, 2.5])
def test_abel_of_a_gaussian_is_the_closed_form(sigma):
    dr, f, A = _gauss(sigma, 240)
    assert np.abs(M.abel_transform(f, dr) - A).max() < 1e-6 * A.max()


@pytest.mark.parametrize("method,tol", [("derivative", 2e-5), ("onion", 5e-3)])
def test_inverse_abel_recovers_the_gaussian_by_two_independent_methods(method, tol):
    dr, f, A = _gauss(1.3, 240)
    assert np.abs(M.abel_inverse(A, dr, method=method) - f).max() < tol


def test_the_two_inverse_methods_agree_without_noise():
    dr, f, A = _gauss(1.0, 200)
    a, b = M.abel_inverse(A, dr), M.abel_inverse(A, dr, method="onion")
    assert np.abs(a - b).max() < 5e-3


def _noise_err(n, method, seeds=6):
    R = 4.0
    dr = R / n
    r = np.arange(n) * dr
    f = 0.5 * np.exp(-r**2 / 1.2**2) + 0.6 * np.exp(-((r - 1.7) / 0.25) ** 2)
    A = M.abel_transform(f, dr)
    errs = []
    for k in range(seeds):
        noisy = A + np.random.default_rng(k).normal(0, 0.01 * A.max(), n)
        errs.append(np.abs(M.abel_inverse(noisy, dr, method=method) - f).mean())
    return float(np.mean(errs))


def test_noise_amplification_scales_as_one_over_dr_for_the_derivative_and_its_square_root_for_onion():
    """docstring の主張を両向きで: 細かい格子では殻剥きが勝ち、粗い格子では微分が勝つ(片側だけの門にしない)。"""
    d80, d640 = _noise_err(80, "derivative"), _noise_err(640, "derivative")
    o80, o640 = _noise_err(80, "onion"), _noise_err(640, "onion")
    slope_d, slope_o = math.log(d640 / d80) / math.log(8), math.log(o640 / o80) / math.log(8)
    assert 0.8 < slope_d < 1.2 and 0.3 < slope_o < 0.7, (slope_d, slope_o)
    assert o640 < d640 and d80 < o80


def test_abel_rejects_bad_input():
    with pytest.raises(ValueError):
        M.abel_transform([1.0, 2.0], 1.0)
    with pytest.raises(ValueError):
        M.abel_transform(np.ones(10), 0.0)
    with pytest.raises(ValueError):
        M.abel_inverse(np.ones(10), 1.0, method="basex")


# ---- Hankel ----------------------------------------------------------------------- #
def test_exp_minus_pi_r2_is_self_dual_and_the_kernel_is_an_involution():
    h = M.hankel_transform(None, lambda r: np.exp(-math.pi * r**2), r_max=6.0, n=256)
    assert np.abs(h["F"] - np.exp(-math.pi * h["nu"]**2)).max() < 1e-12
    assert h["T_involution_error"] < 1e-9


def test_order_one_self_dual_and_sampled_input():
    h = M.hankel_transform(None, lambda r: r * np.exp(-math.pi * r**2), r_max=6.0, order=1, n=200)
    assert np.abs(h["F"] - h["nu"] * np.exp(-math.pi * h["nu"]**2)).max() < 1e-12
    r = np.linspace(0, 6, 4001)
    hs = M.hankel_transform(r, np.exp(-math.pi * r**2), n=200)
    assert np.abs(hs["F"] - np.exp(-math.pi * hs["nu"]**2)).max() < 1e-5      # 線形補間の誤差だけ


def test_hankel_equals_the_radial_slice_of_the_2d_fft():
    """軸対称な関数の 2-D フーリエ変換 = 0 次 Hankel 変換(2π 規約)。"""
    N, L = 512, 16.0
    x = (np.arange(N) - N // 2) * (L / N)
    X, Y = np.meshgrid(x, x)
    g = np.exp(-math.pi * (X**2 + Y**2) / 2.0)                 # 幅を変えて自己双対でない例にする
    G = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(g))).real * (L / N) ** 2
    k = np.fft.fftshift(np.fft.fftfreq(N, d=L / N))
    # FFT の格子(間隔 1/L)は粗いので、細かい Hankel の側を 3 次スプラインで FFT の格子点に載せて比べる
    # (線形補間で比べると、ガウスの曲率による補間誤差 ~1e-2 を op の誤差と取り違える)。
    from scipy.interpolate import CubicSpline
    h = M.hankel_transform(None, lambda r: np.exp(-math.pi * r**2 / 2.0), r_max=40.0, n=600)
    kk = k[N // 2:]
    sel = (kk > h["nu"][0]) & (kk < 1.0)                       # Hankel の標本の内側だけ(外挿しない)
    Hk = CubicSpline(h["nu"], h["F"])(kk[sel])
    assert sel.sum() >= 10 and np.abs(Hk - G[N // 2, N // 2:][sel]).max() < 1e-7


# ---- s 領域 ------------------------------------------------------------------------ #
T = np.linspace(0.01, 5, 60)


def test_step_and_impulse_responses_match_closed_forms():
    a = 1.7
    assert np.abs(M.tf_step_response([1], [1, a], T) - (1 - np.exp(-a * T)) / a).max() < 1e-12
    assert np.abs(M.tf_impulse_response([1], [1, a], T) - np.exp(-a * T)).max() < 1e-12
    w0, z = 3.0, 0.3
    wd = w0 * math.sqrt(1 - z * z)
    y = 1 - np.exp(-z * w0 * T) * (np.cos(wd * T) + z / math.sqrt(1 - z * z) * np.sin(wd * T))
    assert np.abs(M.tf_step_response([w0 * w0], [1, 2 * z * w0, w0 * w0], T) - y).max() < 1e-12
    # 原点の重根(積分器 2 段)でも分岐なしで: 1/s² のステップ応答 = t²/2
    assert np.abs(M.tf_step_response([1], [1, 0, 0], T) - T * T / 2).max() < 1e-10
    # 直達項: (s+2)/(s+1) のステップ = 2 − e^{−t}
    assert np.abs(M.tf_step_response([1, 2], [1, 1], T) - (2 - np.exp(-T))).max() < 1e-12


def test_talbot_and_the_matrix_exponential_agree_on_rational_functions():
    for num, den in [([1], [1, 1.7]), ([1], [1, 0, 0]), ([2.0], [1, 0, 4.0]), ([1, 3], [1, 2, 5])]:
        a = M.laplace_inverse_talbot(num, den, T)
        b = M.tf_impulse_response(num, den, T)
        assert np.abs(a - b).max() < 1e-8, (num, den)


def test_talbot_on_a_non_rational_pair():
    """F(s) = 1/√s ↔ f(t) = 1/√(πt)(分岐点を持つので部分分数では解けない)。"""
    assert np.abs(M.laplace_inverse_func(lambda s: 1 / np.sqrt(s), T) - 1 / np.sqrt(math.pi * T)).max() < 1e-8
    with pytest.raises(ValueError):
        M.laplace_inverse_func(lambda s: 1 / s, [0.0, 1.0])


def test_poles_zeros_and_bode():
    pz = M.tf_poles_zeros([1, 2], [1, 3, 2])
    assert sorted(pz["poles"].real) == pytest.approx([-2, -1]) and pz["stable"] and pz["dc_gain"] == 1.0
    assert not M.tf_poles_zeros([1], [1, -1])["stable"]
    w0 = 10.0
    fr = M.tf_freq_response([w0], [1, w0], [w0])                 # 1 次低域通過の折点
    assert fr["mag_db"][0] == pytest.approx(-10 * math.log10(2), abs=1e-12)
    assert fr["phase_deg"][0] == pytest.approx(-45.0, abs=1e-12)
    with pytest.raises(ValueError):
        M.tf_poles_zeros([1, 0, 0], [1, 1])                       # 非プロパー


def test_tustin_matches_scipy_and_prewarp_is_exact_at_its_frequency():
    signal = pytest.importorskip("scipy.signal")
    w0, z, fs_ = 3.0, 0.3, 20.0
    num, den = [w0 * w0], [1, 2 * z * w0, w0 * w0]
    d = M.tf_bilinear(num, den, fs_)
    bz, az = signal.bilinear(num, den, fs=fs_)
    assert np.allclose(d["num_z"], bz, atol=1e-14) and np.allclose(d["den_z"], az, atol=1e-14)
    p = M.tf_bilinear(num, den, fs_, prewarp_hz=w0 / (2 * math.pi))
    zz = np.exp(1j * w0 / fs_)
    Hd = np.polyval(p["num_z"], zz) / np.polyval(p["den_z"], zz)
    Hc = np.polyval(num, 1j * w0) / np.polyval(den, 1j * w0)
    assert abs(Hd - Hc) < 1e-12
    assert np.all(np.abs(np.roots(p["den_z"])) < 1)               # 安定 → 単位円内


# ---- 次元を上げた Abel(写真 → 断面画像 → 3-D)------------------------------------------ #
def _flame_projection(H=40, W=161, dr=0.05):
    c = (W - 1) / 2
    y = (np.arange(W) - c) * dr
    s = 0.8 + 0.6 * np.linspace(0, 1, H)
    return np.sqrt(math.pi) * s[:, None] * np.exp(-y[None, :] ** 2 / s[:, None] ** 2), s, dr, c


def test_abel_inverse_image_recovers_the_gaussian_slices():
    proj, s, dr, c = _flame_projection()
    res = M.abel_inverse_image(proj, dr)
    r = np.arange(res["slice"].shape[1]) * dr
    assert res["center"] == pytest.approx(c) and res["asymmetry"] < 1e-12
    assert np.abs(res["slice"] - np.exp(-r[None, :] ** 2 / s[:, None] ** 2)).max() < 1e-2
    lop = proj.copy()
    lop[:, : int(c)] *= 1.3                                   # 左右が非対称な写真は asymmetry に出る
    assert M.abel_inverse_image(lop, dr, center=c)["asymmetry"] > 0.05


def test_revolving_the_slice_and_projecting_returns_the_photograph():
    proj, s, dr, c = _flame_projection()
    R = 80                                                    # r の最大 3.95(裾を切らない: 60 では s=1.4 の裾が欠けて端で 0.03 ずれた)
    r = np.arange(R) * dr
    vol = M.abel_revolve(np.exp(-r[None, :] ** 2 / s[:, None] ** 2), dr)
    assert vol.shape == (40, 2 * R - 1, 2 * R - 1)
    back = vol.sum(axis=1) * dr
    i0 = int(c) - (R - 1)
    assert np.abs(back - proj[:, i0:i0 + 2 * R - 1]).max() < 2e-3


# ── 係数を返す直交変換(DCT・Daubechies DWT、N 次元)──────────────────────────────────────────── #
def test_dct_matches_definition_and_inverts_in_3d():
    """定義式の行列 C[k,n] = √(2/N)·c_k·cos(π(2n+1)k/2N) と一致し、3-D でも逆変換で戻り、エネルギーは保存。"""
    N = 12
    n = np.arange(N)
    C = np.sqrt(2 / N) * np.cos(np.pi * (2 * n + 1) * n[:, None] / (2 * N))
    C[0] /= np.sqrt(2)
    x = np.random.default_rng(0).standard_normal(N)
    assert np.abs(M.dct_transform(x)["coeffs"] - C @ x).max() < 1e-12
    vol = np.random.default_rng(1).random((16, 24, 8))
    r = M.dct_transform(vol)
    assert np.abs(M.dct_transform(r["coeffs"], inverse=True)["coeffs"] - vol).max() < 1e-12
    assert abs(r["energy"] - float((vol * vol).sum())) < 1e-9 * r["energy"]


def test_dct_compacts_smooth_images_not_noise():
    """滑らかな画像は少数の係数にエネルギーが集まる(JPEG の理由)。白色雑音は集まらない(失敗例)。"""
    yy, xx = np.mgrid[0:64, 0:64] / 64.0
    smooth = np.exp(-((xx - 0.4) ** 2 + (yy - 0.6) ** 2) / 0.05) + 0.3 * xx
    noise = np.random.default_rng(2).standard_normal((64, 64))
    k = int(0.02 * 64 * 64)
    assert M.dct_transform(smooth)["compaction"][k] > 0.999
    assert M.dct_transform(noise)["compaction"][k] < 0.15


@pytest.mark.parametrize("order", range(1, 9))
def test_daubechies_filters_are_orthonormal_with_n_vanishing_moments(order):
    """スペクトル分解で作った dbN: Σ h_i h_{i+2s} = δ_s(直交)、Σ n^m g_n = 0(m < N、消失モーメント)、Σ h = √2。"""
    f = M.wavelet_filters(order)
    h, g = f["lowpass"], f["highpass"]
    L = h.size
    assert L == 2 * order and abs(h.sum() - math.sqrt(2)) < 1e-12
    for s in range(order):
        assert abs(float(np.dot(h[:L - 2 * s], h[2 * s:])) - (1.0 if s == 0 else 0.0)) < 1e-13
    for m in range(order):
        assert abs(float(np.sum(np.arange(L) ** m * g))) < 1e-9 * max(1.0, float(np.sum(np.abs(np.arange(L) ** m * g))))


def test_db2_closed_form_and_haar():
    """db2 は閉形式 (1+√3, 3+√3, 3−√3, 1−√3)/(4√2)、db1 は Haar (1, 1)/√2。"""
    r3 = math.sqrt(3)
    ref = np.array([1 + r3, 3 + r3, 3 - r3, 1 - r3]) / (4 * math.sqrt(2))
    assert np.abs(M.wavelet_filters(2)["lowpass"] - ref).max() < 1e-14
    assert np.abs(M.wavelet_filters(1)["lowpass"] - np.array([1, 1]) / math.sqrt(2)).max() < 1e-15


@pytest.mark.parametrize("shape,levels", [((64,), 3), ((32, 48), 2), ((16, 16, 8), 2)])
def test_dwt_is_orthonormal_in_nd(shape, levels):
    """1-D・2-D・3-D で Parseval(エネルギー保存)と完全再構成。2-D の帯は 'ad'・'da'・'dd'、3-D は 7 個。"""
    X = np.random.default_rng(3).standard_normal(shape)
    c = M.dwt_transform(X, order=3, levels=levels)
    assert abs(c["energy_in"] - c["energy_out"]) < 1e-11 * c["energy_in"]
    assert np.abs(M.dwt_inverse(c) - X).max() < 1e-12
    assert len(c["details"]) == levels and len(c["details"][0]) == 2 ** len(shape) - 1


def test_dwt_vanishing_moments_kill_polynomials_below_order():
    """dbN の詳細係数は N−1 次までの多項式を消す: 2 次式は db3 で消え(1e-12)、db2 では残る(失敗例)。"""
    t = np.arange(256.0)
    p = 1 + 0.3 * t - 0.002 * t ** 2
    d3 = M.dwt_transform(p, order=3)["details"][0]["d"]
    d2 = M.dwt_transform(p, order=2)["details"][0]["d"]
    assert np.abs(d3[2:-3]).max() < 1e-11                    # 周期境界の継ぎ目だけは除く
    assert np.abs(d2[2:-2]).max() > 1e-3


def test_dwt_rejects_bad_shapes():
    with pytest.raises(ValueError):
        M.dwt_transform(np.zeros(30), levels=2)                  # 30 は 4 の倍数でない
    with pytest.raises(ValueError):
        M.wavelet_filters(11)
    with pytest.raises(ValueError):
        M.dwt_inverse({"approx": np.zeros(4)})

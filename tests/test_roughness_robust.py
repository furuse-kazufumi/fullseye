# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""roughness のロバスト・ガウシアン回帰 / ロバスト・スプライン(3 op)— 外部の真値で採点する。

真値の出どころ(どれも op と独立):
  * ガウスの伝達関数 ``exp(-π (α λc / λ)²)`` が ``λ = λc`` でちょうど 0.5(α² = ln2/π から
    閉形式で出る)。
  * 離散スプラインの伝達関数 ``1 / (1 + (sin(π dx/λ) / sin(π dx/λc))⁴)``(2 階差分の
    周波数応答 ``4 sin²(π f dx)`` から導く)。
  * 第 2 実装: **密行列・点ごとの lstsq / 密な連立一次方程式**で書いた反復(op は可分相関・
    帯行列)。反復の不動点が一致することを見る。
  * 既存の ``surface_filter``(ISO 16610-21 の別実装)— 重み 1・次数 0・打ち切り 0.75(GAUSS_TRUNCATE)で一致。
  * 外れ値: 真の平均線が分かる合成(うねり + 雑音 + 片側に寄せた傷・突起)で、
    **引きずり量**(平均線の真値からの最大ずれ)を数え、線形ガウスとの比を門にする。

しきい値は「構造の差」で立てる(線形が 10 倍以上引きずられる、など)。数 % の細い線は使わない。
探針は **壊して落ちることを確かめる**: 重み関数を 1 に固定 / α を狂わす / λc を 10 % ずらす。
"""
import math

import numpy as np
import pytest
import scipy.sparse as sp
import scipy.sparse.linalg as spla

import roughness as R

DX = 1.0
LC = 80.0
N = 3000
X = np.arange(N) * DX
TRUE = 2.0 * np.sin(2.0 * np.pi * X / 600.0)          # 本当の平均線(λ = 600 >> λc)
INNER = slice(150, N - 150)                           # 端の影響を避けた評価区間


def _profile(seed, kind="spikes", frac=0.0, depth=6.0, width=8):
    """真の平均線 + 雑音(σ 0.3)+ 片側(下向き)の外れ値。``idx`` も返す。"""
    rng = np.random.default_rng(seed)
    z = TRUE + 0.3 * rng.standard_normal(N)
    idx = np.zeros(N, bool)
    if frac > 0.0:
        if kind == "spikes":
            idx = rng.random(N) < frac
        else:
            k = int(frac * N)
            while idx.sum() < k:
                s = int(rng.integers(0, N - width))
                idx[s:s + width] = True
    z = z.copy()
    z[idx] -= depth
    return z, idx


def _drag(mean_line):
    """引きずり量: 平均線の真値からの最大ずれ(端を除く)。"""
    return float(np.max(np.abs(mean_line - TRUE)[INNER]))


def _gauss(z, **kw):
    return R.robust_gaussian_profile(z, DX, LC, **kw)


def _spline(z, **kw):
    return R.robust_spline_profile(z, DX, LC, **kw)


def _amp(m, lam, sl=slice(900, 2100)):
    """平均線の中の波長 λ の振幅(正弦 + 余弦の最小二乗射影)。"""
    x = X[sl]
    basis = np.stack([np.sin(2 * np.pi * x / lam), np.cos(2 * np.pi * x / lam)], 1)
    coef, *_ = np.linalg.lstsq(basis, m[sl], rcond=None)
    return float(np.hypot(*coef))


def _gauss_closed(lam, lc=LC):
    # ★α は op の定数を読まず、ここで ln2/π から作り直す(両辺に同じ入力を渡す門は無効)
    alpha = math.sqrt(math.log(2.0) / math.pi)
    return math.exp(-math.pi * (alpha * lc / lam) ** 2)


def _spline_closed(lam, lc=LC, dx=DX):
    return 1.0 / (1.0 + (math.sin(math.pi * dx / lam) / math.sin(math.pi * dx / lc)) ** 4)


# --------------------------------------------------------------------------- #
# 1. 伝達関数(閉形式)                                                         #
# --------------------------------------------------------------------------- #
LAMS = (40.0, 60.0, 80.0, 120.0, 150.0, 240.0)       # どれも評価区間 1200 を割り切る


def _gauss_gate(filt):
    """ガウスの伝達関数が閉形式に合う最大誤差。"""
    err = 0.0
    for lam in LAMS:
        m = filt(np.sin(2 * np.pi * X / lam))
        err = max(err, abs(_amp(m, lam) - _gauss_closed(lam)))
    return err


def _spline_gate(filt):
    err = 0.0
    for lam in LAMS:
        m = filt(np.sin(2 * np.pi * X / lam))
        err = max(err, abs(_amp(m, lam) - _spline_closed(lam)))
    return err


@pytest.mark.parametrize("order", [0, 1])
def test_gaussian_transmission_is_half_at_cutoff_and_matches_closed_form(order):
    lin = lambda s: _gauss(s, order=order, robust=False)[1]
    # カットオフ波長で 0.5(α² = ln2/π から閉形式で exactly 0.5)
    assert abs(_amp(lin(np.sin(2 * np.pi * X / LC)), LC) - 0.5) < 1e-5
    # 6 波長すべてで閉形式に合う。残る誤差は打ち切り(±λc = 5.3σ の裾 ~1e-7)と射影だけ。
    assert _gauss_gate(lin) < 1e-5


def test_spline_transmission_is_half_at_cutoff_and_matches_discrete_closed_form():
    lin = lambda s: _spline(s, robust=False)[1]
    assert abs(_amp(lin(np.sin(2 * np.pi * X / LC)), LC) - 0.5) < 1e-9
    assert _spline_gate(lin) < 1e-9          # 実測 ~1e-12(連立方程式を厳密に解くため)


def test_spline_discrete_closed_form_tends_to_the_continuous_limit():
    # dx/λ → 0 で 1/(1+(λc/λ)^4)(張力 0 の三次スプラインフィルタの形)。離散式の独立な確認。
    for lam in (60.0, 100.0, 400.0):
        assert abs(_spline_closed(lam, lc=80.0, dx=1e-3)
                   - 1.0 / (1.0 + (80.0 / lam) ** 4)) < 1e-9


def test_transfer_gates_are_sharp_enough_to_catch_a_wrong_cutoff_or_alpha(monkeypatch):
    """探針: λc を 10 % ずらす / α を狂わすと、同じ門が落ちる(門が眠っていないことの証拠)。"""
    good_g = _gauss_gate(lambda s: _gauss(s, robust=False)[1])
    bad_g = _gauss_gate(lambda s: R.robust_gaussian_profile(s, DX, LC * 1.1, robust=False)[1])
    assert good_g < 1e-5 < 1e-2 < bad_g
    good_s = _spline_gate(lambda s: _spline(s, robust=False)[1])
    bad_s = _spline_gate(lambda s: R.robust_spline_profile(s, DX, LC * 1.1, robust=False)[1])
    assert good_s < 1e-9 < 1e-2 < bad_s
    monkeypatch.setattr(R, "GAUSS_ALPHA", R.GAUSS_ALPHA * 1.05)
    assert _gauss_gate(lambda s: _gauss(s, robust=False)[1]) > 1e-3


# --------------------------------------------------------------------------- #
# 2. 既存の surface_filter(ISO 16610-21 の別実装)との一致                     #
# --------------------------------------------------------------------------- #
def test_unit_weight_order0_with_same_truncation_equals_existing_surface_filter():
    lc, n, h = 40.0, 400, 120
    rng = np.random.default_rng(7)
    p = np.cumsum(rng.standard_normal(n)) * 0.1
    z2 = np.tile(p, (h, 1))                                  # 行が全部同じ面
    _, wav = R.surface_filter(z2, 1.0, lambda_c=lc, end_effect="reject")
    rad = int(math.ceil(R.GAUSS_TRUNCATE * lc))
    mine = R.robust_gaussian_profile(p, 1.0, lc, order=0, robust=False, truncate=R.GAUSS_TRUNCATE)[1]
    ref = wav[wav.shape[0] // 2]                             # 行を 1 本取る(x の並び)
    assert ref.size == n - 2 * rad
    np.testing.assert_allclose(mine[rad:n - rad], ref, rtol=0, atol=1e-12)


def test_literal_half_lambda_truncation_is_what_moves_the_cutoff_transmission_off_half():
    """規格の文面の打ち切り ±λc/2 は λc の透過率を 0.5095 にずらす(2026-10-18 まで surface_filter がそうだった)。
    surface_filter は ±0.75λc(4σ)に直し、新 op は 5.3σ まで取る。ずれの原因が打ち切りだと門にしておく。"""
    lin_iso = _gauss(np.sin(2 * np.pi * X / LC), order=0, robust=False, truncate=0.5)[1]
    assert abs(_amp(lin_iso, LC) - 0.5) > 5e-3           # 文面どおりの打ち切り = 直す前の surface_filter のずれ
    lin_wide = _gauss(np.sin(2 * np.pi * X / LC), order=0, robust=False)[1]
    assert abs(_amp(lin_wide, LC) - 0.5) < 1e-5


def test_on_clean_data_robust_differs_from_linear_far_less_than_outliers_drag_linear():
    """外れ値の無いデータでの違いを隠さない: biweight は雑音の裾も刈るので線形とは一致しない。
    その差が、外れ値が線形を引きずる量より桁で小さいことを門にする(細い % 線は使わない)。"""
    z, _ = _profile(0)
    clean_gap = float(np.max(np.abs(_gauss(z)[1] - _gauss(z, robust=False)[1])[INNER]))
    zc, _ = _profile(0, "spikes", 0.10)
    drag_lin = _drag(_gauss(zc, robust=False)[1])
    assert clean_gap < 0.2 and drag_lin > 10 * clean_gap


# --------------------------------------------------------------------------- #
# 3. 外れ値・傷に引きずられない(破綻点つき)                                    #
# --------------------------------------------------------------------------- #
FILTERS = {"gauss": _gauss, "spline": _spline}


def _median_drags(fn, kind, frac, seeds=(0, 1, 2, 3, 4)):
    lin, rob = [], []
    for s in seeds:
        z, _ = _profile(s, kind, frac)
        lin.append(_drag(fn(z, robust=False)[1]))
        rob.append(_drag(fn(z)[1]))
    return float(np.median(lin)), float(np.median(rob))


def _robust_gate(fn, kind, fracs=(0.05, 0.10, 0.20)):
    """どの汚染率でも、ロバストの引きずりが線形の 1/4 未満(雑音だけでも引きずりは 0.14 残るので
    1/10 は要求しない)。比の最大を返す。"""
    worst = 0.0
    for f in fracs:
        lin, rob = _median_drags(fn, kind, f)
        worst = max(worst, rob / lin)
    return worst


@pytest.mark.parametrize("name", ["gauss", "spline"])
@pytest.mark.parametrize("kind", ["spikes", "scratches"])
def test_robust_mean_line_ignores_outliers_and_linear_does_not(name, kind):
    assert _robust_gate(FILTERS[name], kind) < 0.25


@pytest.mark.parametrize("name", ["gauss", "spline"])
def test_breakdown_curve_robust_wins_then_stops_winning_near_half(name):
    """破綻点を数字で出す: 汚染 20 % まで勝ち、60 % では勝てない(biweight + 中央値の限界)。"""
    fn = FILTERS[name]
    lin20, rob20 = _median_drags(fn, "spikes", 0.20)
    lin60, rob60 = _median_drags(fn, "spikes", 0.60)
    assert rob20 < 0.25 * lin20
    assert rob60 > 0.5 * lin60                 # 半数を超えれば外れ値側が「多数派」になる
    assert rob60 > 1.0                         # 引きずりが真の振幅(2.0)の半分を超えて壊れる


def test_probe_with_unit_weight_function_the_outlier_gate_fails(monkeypatch):
    """探針: 重み関数を 1 に固定すると、外れ値の門(上の ``_robust_gate``)が落ちる。"""
    ok = _robust_gate(_gauss, "spikes")
    monkeypatch.setattr(R, "_biweight", lambda r, cb: np.ones_like(r))
    broken = _robust_gate(_gauss, "spikes")
    assert ok < 0.25 <= 0.5 < broken
    broken_s = _robust_gate(_spline, "scratches")
    assert broken_s > 0.5


def test_clean_profile_survives_one_deep_scratch_exactly_like_clean_data():
    z, _ = _profile(3)
    z2 = z.copy()
    z2[1400:1412] -= 50.0                    # 12 標本・深さ 50 の溝(雑音の 160 倍)
    for fn in (_gauss, _spline):
        d_clean = _drag(fn(z)[1])
        d_dirty = _drag(fn(z2)[1])
        d_lin = _drag(fn(z2, robust=False)[1])
        assert d_dirty < 3 * d_clean + 0.05 and d_lin > 20 * d_dirty


# --------------------------------------------------------------------------- #
# 4. 第 2 実装(密行列・点ごとの lstsq / 密な連立)                              #
# --------------------------------------------------------------------------- #
def _naive_gauss(z, dx, lc, order, c=4.4, trunc=1.0, robust=True):
    """点ごとに窓を切り、sqrt(w) を掛けた lstsq で当てはめる。op の可分相関とは別経路。"""
    n = z.size
    sigma = R.GAUSS_ALPHA * lc / (math.sqrt(2 * math.pi) * dx)
    rad = int(math.ceil(trunc * lc / dx))

    def fit(delta):
        out = np.empty(n)
        for i in range(n):
            j = np.arange(max(0, i - rad), min(n, i + rad + 1))
            u = (j - i).astype(float)
            w = np.exp(-0.5 * (u / sigma) ** 2) * delta[j]
            X_ = np.stack([np.ones_like(u), u], 1) if order == 1 else np.ones((u.size, 1))
            sw = np.sqrt(w)
            coef, *_ = np.linalg.lstsq(X_ * sw[:, None], z[j] * sw, rcond=None)
            out[i] = coef[0]
        return out

    m = fit(np.ones(n))
    for _ in range(500):
        if not robust:
            return m
        r = z - m
        cb = c * np.median(np.abs(r))
        u = r / cb
        delta = np.where(np.abs(u) < 1, (1 - u * u) ** 2, 0.0)
        m2 = fit(delta)
        done = np.max(np.abs(m2 - m)) < 1e-11
        m = m2
        if done:
            return m
    raise AssertionError("naive iteration did not converge")


def _naive_spline(z, dx, lc, c=4.4, robust=True):
    n = z.size
    beta = 1.0 / (16.0 * math.sin(math.pi * dx / lc) ** 4)
    d = np.zeros((n - 2, n))
    for i in range(n - 2):
        d[i, i:i + 3] = (1.0, -2.0, 1.0)
    pen = beta * d.T @ d

    def fit(delta):
        # 疎 LU(SuperLU)で解く: op の帯行列ソルバとも BLAS の密 solve とも別経路
        return spla.spsolve(sp.csc_matrix(np.diag(delta) + pen), delta * z)

    m = fit(np.ones(n))
    for _ in range(500):
        if not robust:
            return m
        r = z - m
        u = r / (c * np.median(np.abs(r)))
        m2 = fit(np.where(np.abs(u) < 1, (1 - u * u) ** 2, 0.0))
        done = np.max(np.abs(m2 - m)) < 1e-11
        m = m2
        if done:
            return m
    raise AssertionError("naive iteration did not converge")


@pytest.mark.parametrize("order", [0, 1])
@pytest.mark.parametrize("robust", [False, True])
def test_gaussian_matches_dense_second_implementation(order, robust):
    n, lc = 240, 24.0
    rng = np.random.default_rng(11)
    z = 1.5 * np.sin(2 * np.pi * np.arange(n) / 160.0) + 0.2 * rng.standard_normal(n)
    z[100:104] -= 5.0
    z[30] += 4.0
    ref = _naive_gauss(z, 1.0, lc, order, robust=robust)
    got = R.robust_gaussian_profile(z, 1.0, lc, order=order, robust=robust, tol=1e-9, max_iter=2000)[1]
    np.testing.assert_allclose(got, ref, rtol=0, atol=1e-6)


@pytest.mark.parametrize("robust", [False, True])
def test_spline_matches_dense_second_implementation(robust):
    n, lc = 120, 16.0
    rng = np.random.default_rng(12)
    z = 1.5 * np.sin(2 * np.pi * np.arange(n) / 100.0) + 0.2 * rng.standard_normal(n)
    z[60:63] -= 5.0
    z[20] += 4.0
    ref = _naive_spline(z, 1.0, lc, robust=robust)
    got = R.robust_spline_profile(z, 1.0, lc, robust=robust, tol=1e-9, max_iter=2000)[1]
    np.testing.assert_allclose(got, ref, rtol=0, atol=1e-6)


def test_surface_matches_per_pixel_second_implementation_and_the_profile_path():
    h = w = 28
    lc = 6.0
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    z = 0.8 * np.sin(2 * np.pi * xx / 40.0) + 0.5 * np.cos(2 * np.pi * yy / 33.0) \
        + 0.1 * rng.standard_normal((h, w))
    z[10:12, 8:20] -= 4.0                                   # 傷
    sigma = R.GAUSS_ALPHA * lc / math.sqrt(2 * math.pi)
    rad = int(math.ceil(lc))

    def fit(delta):
        out = np.empty((h, w))
        for i in range(h):
            for j in range(w):
                ys = np.arange(max(0, i - rad), min(h, i + rad + 1))
                xs = np.arange(max(0, j - rad), min(w, j + rad + 1))
                v, u = np.meshgrid(ys - i, xs - j, indexing="ij")
                g = np.exp(-0.5 * (u / sigma) ** 2) * np.exp(-0.5 * (v / sigma) ** 2)
                wt = (g * delta[np.ix_(ys, xs)]).ravel()
                X_ = np.stack([np.ones(u.size), v.ravel(), u.ravel()], 1)
                sw = np.sqrt(wt)
                coef, *_ = np.linalg.lstsq(X_ * sw[:, None], z[np.ix_(ys, xs)].ravel() * sw,
                                           rcond=None)
                out[i, j] = coef[0]
        return out

    m = fit(np.ones((h, w)))
    for _ in range(500):
        r = z - m
        u = r / (4.4 * np.median(np.abs(r)))
        m2 = fit(np.where(np.abs(u) < 1, (1 - u * u) ** 2, 0.0))
        done = np.max(np.abs(m2 - m)) < 1e-11
        m = m2
        if done:
            break
    assert done
    got = R.robust_gaussian_surface(z, 1.0, lc, tol=1e-10)[1]
    np.testing.assert_allclose(got, m, rtol=0, atol=1e-7)

    # 行が全部同じ面なら 1 次元版と一致する(2 つの独立した経路)
    p = z[0]
    z2 = np.tile(p, (h, 1))
    s2 = R.robust_gaussian_surface(z2, 1.0, lc, tol=1e-9, max_iter=2000)[1]
    p2 = R.robust_gaussian_profile(p, 1.0, lc, tol=1e-9, max_iter=2000)[1]
    np.testing.assert_allclose(s2[h // 2], p2, rtol=0, atol=1e-7)


def test_surface_robust_ignores_a_scratch_and_linear_does_not():
    n, lc = 96, 12.0
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    true = 1.0 * np.sin(2 * np.pi * xx / 160.0) + 0.5 * np.cos(2 * np.pi * yy / 140.0)
    rng = np.random.default_rng(2)
    z = true + 0.1 * rng.standard_normal((n, n))
    z[40:44, 10:90] -= 6.0                                   # 幅 4・長さ 80 の溝
    inner = (slice(15, n - 15),) * 2
    d_rob = float(np.max(np.abs(R.robust_gaussian_surface(z, 1.0, lc)[1] - true)[inner]))
    d_lin = float(np.max(np.abs(
        R.robust_gaussian_surface(z, 1.0, lc, robust=False)[1] - true)[inner]))
    assert d_rob < 0.25 * d_lin


# --------------------------------------------------------------------------- #
# 5. 性質: 平行移動・スケールに共変、粗さ + 平均線 = 入力                        #
# --------------------------------------------------------------------------- #
def test_shift_scale_equivariance_and_decomposition():
    z, _ = _profile(4, "spikes", 0.05)
    for fn in (_gauss, _spline):
        r, m, info = fn(z)
        assert info["converged"] and info["iterations"] >= 1
        np.testing.assert_allclose(r + m, z, rtol=0, atol=1e-12)
        m_shift = fn(z + 123.4)[1]
        np.testing.assert_allclose(m_shift, m + 123.4, rtol=0, atol=1e-7)
        m_scale = fn(z * 7.5)[1]
        np.testing.assert_allclose(m_scale, m * 7.5, rtol=0, atol=1e-6)


def test_exactly_linear_profile_is_returned_unchanged_by_order1_and_spline():
    # 直線は局所直線回帰(ガウス次数 1)にもスプライン(2 階差分の罰則)にも罰されない。端まで。
    z = 0.37 * X[:400] + 2.0
    for fn in (lambda a: R.robust_gaussian_profile(a, DX, 30.0, robust=False),
               lambda a: R.robust_spline_profile(a, DX, 30.0, robust=False)):
        np.testing.assert_allclose(fn(z)[1], z, rtol=0, atol=1e-8)


# --------------------------------------------------------------------------- #
# 6. fail-closed                                                              #
# --------------------------------------------------------------------------- #
def test_non_convergence_is_refused_not_returned():
    z, _ = _profile(0, "spikes", 0.05)
    for fn in (_gauss, _spline):
        with pytest.raises(ValueError, match="did not converge"):
            fn(z, max_iter=1)


@pytest.mark.parametrize("fn", [_gauss, _spline])
def test_bad_arguments_are_refused(fn):
    z, _ = _profile(0)
    with pytest.raises(ValueError, match="NaN or Inf"):
        fn(np.where(np.arange(N) == 5, np.nan, z))
    with pytest.raises(ValueError, match="1-D"):
        fn(z.reshape(2, -1))
    with pytest.raises(ValueError, match="at least"):
        fn(z[:5])
    with pytest.raises(ValueError, match="Nyquist"):
        R.robust_gaussian_profile(z, DX, 1.0) if fn is _gauss else R.robust_spline_profile(z, DX, 1.0)
    with pytest.raises(ValueError, match="evaluation length"):
        R.robust_gaussian_profile(z, DX, 1e6) if fn is _gauss else R.robust_spline_profile(z, DX, 1e6)
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="c must"):
            fn(z, c=bad)
    with pytest.raises(ValueError, match="tol must"):
        fn(z, tol=0.0)
    with pytest.raises(ValueError, match="max_iter"):
        fn(z, max_iter=0)


def test_gaussian_specific_refusals():
    z, _ = _profile(0)
    with pytest.raises(ValueError, match="order must"):
        _gauss(z, order=2)
    with pytest.raises(ValueError, match="truncate"):
        _gauss(z, truncate=0.2)
    # 窓より広い溝: 窓の中に重みを持つ標本が無くなり、外挿せず拒否する
    z2 = z.copy()
    z2[1000:1300] -= 80.0
    with pytest.raises(ValueError):
        _gauss(z2, truncate=0.5)


def test_spline_with_fewer_than_two_weighted_samples_is_refused(monkeypatch):
    monkeypatch.setattr(R, "_biweight", lambda r, cb: np.zeros_like(r))
    z, _ = _profile(0)
    with pytest.raises(ValueError, match="fewer than two"):
        _spline(z)


def test_surface_refusals():
    z = np.zeros((20, 20))
    with pytest.raises(ValueError, match="2-D"):
        R.robust_gaussian_surface(np.zeros(20), 1.0, 5.0)
    with pytest.raises(ValueError, match="dy"):
        R.robust_gaussian_surface(z, 1.0, 5.0, dy=-1.0)
    with pytest.raises(ValueError, match="order must"):
        R.robust_gaussian_surface(z, 1.0, 5.0, order=2)


# --------------------------------------------------------------------------- #
# 7. 台帳                                                                     #
# --------------------------------------------------------------------------- #
def test_ops_are_registered_in_the_roughness_ledger():
    import opsroughness as O
    for name in ("robust_gaussian_profile", "robust_spline_profile", "robust_gaussian_surface"):
        assert name in O.list_ops("prepare")
        assert callable(O.get(name))
    z, _ = _profile(0)
    out = O.call("robust_gaussian_profile", z, DX, LC)
    assert out.shape == z.shape

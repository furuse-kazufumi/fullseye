"""数値計算の古典と特殊関数の門(2026-10-03、陣 2)。

閉じた式と定理だけで立て、主張は両向きで確かめる(Gauss は 2n−1 次で厳密・2n 次で非厳密、
Runge は等間隔で発散・Chebyshev で収束、エネルギーは Verlet で有界・RK4 で線形に増える)。
★低食い違い列の傾きは**非対称な被積分関数**で測る: 0.5 に対して対称な sin(πx) だと、スクランブル無しの
Sobol が対称性で打ち消し合い傾き −2.2 という「良すぎる」値が出た(2026-10-03 に踏んだ)。
"""
import math
import warnings

import numpy as np
import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import fullseye as fs
    import mathnumerics as N
    import opsmath

LEDGER = ["erf", "erfc", "bessel", "gauss_quadrature", "gauss_cubature", "low_discrepancy", "chebyshev_nodes",
          "interp_barycentric", "integrate_hamiltonian"]


def test_public_and_ledger():
    assert opsmath.missing() == []
    assert sorted(opsmath.list_ops("numerics")) == sorted(LEDGER)
    assert sorted(N.__all__) == sorted(LEDGER)
    for n in N.__all__:
        assert callable(getattr(fs, n)) and n in fs.__all__, n
        assert callable(getattr(fs.ledger, n)), n
        assert (getattr(N, n).__doc__ or "").strip(), n


# ---- 特殊関数 ---------------------------------------------------------------------- #
def test_erf_is_odd_has_the_gaussian_derivative_and_matches_quadrature():
    x = np.linspace(-3, 3, 61)
    assert np.abs(N.erf(x) + N.erf(-x)).max() == 0.0
    h = 1e-5
    d = (N.erf(x + h) - N.erf(x - h)) / (2 * h)
    assert np.abs(d - 2 / math.sqrt(math.pi) * np.exp(-x**2)).max() < 1e-9
    g = N.gauss_quadrature(40, a=0.0, b=1.7)
    assert abs(2 / math.sqrt(math.pi) * np.sum(g["weights"] * np.exp(-g["nodes"]**2)) - N.erf(1.7)) < 1e-14
    assert N.erfc(10.0) > 0 and 1 - N.erf(10.0) == 0.0          # 桁落ちを避けるために erfc を別に持つ


@pytest.mark.parametrize("nu", [0, 1, 2.5])
def test_bessel_wronskian_and_recurrence(nu):
    x = np.linspace(0.5, 20, 100)
    W = N.bessel(x, nu + 1) * N.bessel(x, nu, "y") - N.bessel(x, nu) * N.bessel(x, nu + 1, "y")
    assert np.abs(W - 2 / (math.pi * x)).max() < 1e-13
    if nu >= 1:
        lhs = N.bessel(x, nu - 1) + N.bessel(x, nu + 1)
        assert np.abs(lhs - 2 * nu / x * N.bessel(x, nu)).max() < 1e-13
    with pytest.raises(ValueError):
        N.bessel([0.0, 1.0], nu, "y")


# ---- Gauss 求積 --------------------------------------------------------------------- #
@pytest.mark.parametrize("n", [2, 3, 5, 8, 12])
def test_gauss_legendre_is_exact_to_degree_2n_minus_1_and_not_beyond(n):
    q = N.gauss_quadrature(n)
    x, w = q["nodes"], q["weights"]
    exact = lambda k: 0.0 if k % 2 else 2.0 / (k + 1)       # noqa: E731
    assert max(abs(np.sum(w * x**k) - exact(k)) for k in range(2 * n)) < 1e-13
    assert abs(np.sum(w * x**(2 * n)) - exact(2 * n)) > 1e-9                # 2n 次は厳密でない(片側の門にしない)
    assert q["exact_degree"] == 2 * n - 1


def test_weighted_rules():
    qh = N.gauss_quadrature(6, "hermite")
    assert abs(np.sum(qh["weights"] * qh["nodes"]**4) - 3 * math.sqrt(math.pi) / 4) < 1e-13
    ql = N.gauss_quadrature(6, "laguerre")
    assert abs(np.sum(ql["weights"] * ql["nodes"]**5) - 120.0) < 1e-9       # ∫ x⁵ e^{−x} = 5!
    qc = N.gauss_quadrature(6, "chebyshev")
    assert abs(np.sum(qc["weights"] * qc["nodes"]**2) - math.pi / 2) < 1e-13
    with pytest.raises(ValueError):
        N.gauss_quadrature(4, "hermite", a=0.0, b=1.0)


# ---- 低食い違い列 ------------------------------------------------------------------- #
NS = [256, 1024, 4096, 16384]


def _f(P):
    return np.prod(np.exp(P), axis=1) / (math.e - 1) ** P.shape[1]         # 非対称・積分 = 1


def _slope(errs):
    return float(np.polyfit(np.log(NS), np.log(errs), 1)[0])


def test_quasi_random_beats_random_in_the_rate_of_convergence():
    rnd = [math.sqrt(np.mean([(_f(N.low_discrepancy(n, 2, "random", seed=s)).mean() - 1) ** 2
                              for s in range(20)])) for n in NS]
    assert -0.62 < _slope(rnd) < -0.38                                         # モンテカルロの N^{−1/2}
    for kind, skip in (("halton", 1), ("sobol", 0)):
        e = [abs(_f(N.low_discrepancy(n, 2, kind, skip=skip)).mean() - 1) for n in NS]
        assert _slope(e) < -0.8, (kind, e)
        assert e[-1] < rnd[-1] / 10


def test_star_discrepancy_is_smaller_than_random():
    from scipy.stats import qmc
    d_h = qmc.discrepancy(N.low_discrepancy(1024, 2, "halton", skip=1))
    d_r = qmc.discrepancy(N.low_discrepancy(1024, 2, "random", seed=0))
    assert d_h < d_r / 10
    with pytest.raises(ValueError):
        N.low_discrepancy(10, 2, "random")


def test_halton_first_coordinates_are_van_der_corput():
    P = N.low_discrepancy(8, 2, "halton", skip=1)
    assert np.allclose(P[:, 0], [0.5, 0.25, 0.75, 0.125, 0.625, 0.375, 0.875, 0.0625])
    assert np.allclose(P[:3, 1], [1 / 3, 2 / 3, 1 / 9])


# ---- Chebyshev と Runge 現象 -------------------------------------------------------- #
def _runge(t):
    return 1 / (1 + 25 * t**2)


def test_runge_phenomenon_equispaced_diverges_chebyshev_converges():
    xe = np.linspace(-1, 1, 2001)
    eq_err, ch_err = [], []
    for n in (11, 21, 41):
        eq = np.linspace(-1, 1, n)
        ch = N.chebyshev_nodes(n)
        eq_err.append(np.abs(N.interp_barycentric(eq, _runge(eq), xe) - _runge(xe)).max())
        ch_err.append(np.abs(N.interp_barycentric(ch, _runge(ch), xe) - _runge(xe)).max())
    assert eq_err[0] < eq_err[1] < eq_err[2] and eq_err[2] > 1e3
    assert ch_err[0] > ch_err[1] > ch_err[2] and ch_err[2] < 1e-3


def test_barycentric_reproduces_polynomials_and_rejects_duplicates():
    pk = np.linspace(-1, 1, 7)
    xe = np.linspace(-1, 1, 101)
    assert np.abs(N.interp_barycentric(pk, pk**6 - pk, xe) - (xe**6 - xe)).max() < 1e-13
    assert np.allclose(N.interp_barycentric(pk, pk**2, pk), pk**2)
    with pytest.raises(ValueError):
        N.interp_barycentric([0, 0, 1], [1, 2, 3], [0.5])


# ---- ハミルトン系 ------------------------------------------------------------------- #
def test_verlet_energy_is_bounded_while_rk4_drifts_linearly_and_euler_explodes():
    # dt=0.2 だと RK4 が Verlet を追い抜くのが約 1.1 万歩目(dt=0.1 では約 18 万歩目で、門の時間に入らない)。
    v1 = N.integrate_hamiltonian([1.0], [0.0], 0.2, 4_000)["energy_drift"]
    v2 = N.integrate_hamiltonian([1.0], [0.0], 0.2, 40_000)["energy_drift"]
    r1 = N.integrate_hamiltonian([1.0], [0.0], 0.2, 4_000, method="rk4")["energy_drift"]
    r2 = N.integrate_hamiltonian([1.0], [0.0], 0.2, 40_000, method="rk4")["energy_drift"]
    assert v2 / v1 < 1.01 and 8 < r2 / r1 < 12                                # 有界 vs 線形
    assert r1 < v1 < r2                                                        # 短時間は RK4、長時間は Verlet
    e = N.integrate_hamiltonian([1.0], [0.0], 0.1, 50, method="euler")
    assert e["energy"][-1] / e["energy"][0] == pytest.approx((1 + 0.01) ** 50, rel=1e-12)


def test_verlet_is_time_reversible():
    r = N.integrate_hamiltonian([1.0], [0.0], 0.1, 1000, system="pendulum", omega=2.0)
    b = N.integrate_hamiltonian(r["q"][-1], r["p"][-1], -0.1, 1000, system="pendulum", omega=2.0)
    assert abs(b["q"][-1, 0] - 1.0) < 1e-11 and abs(b["p"][-1, 0]) < 1e-11


def test_kepler_circular_orbit_keeps_its_radius():
    k = N.integrate_hamiltonian([1.0, 0.0], [0.0, 1.0], 0.01, 20_000, system="kepler")
    rad = np.linalg.norm(k["q"], axis=1)
    assert rad.max() - rad.min() < 1e-4 and k["energy_drift"] < 1e-8
    with pytest.raises(ValueError):
        N.integrate_hamiltonian([1.0], [0.0], 0.1, 10, system="kepler")


@pytest.mark.parametrize("n", [2, 3, 5])
def test_gauss_cubature_is_exact_per_axis_to_degree_2n_minus_1(n):
    q = N.gauss_cubature(n, 2)
    X, w = q["nodes"], q["weights"]

    def exact(p, r):
        return (0 if p % 2 else 2 / (p + 1)) * (0 if r % 2 else 2 / (r + 1))
    assert max(abs(np.sum(w * X[:, 0] ** p * X[:, 1] ** r) - exact(p, r)) for p in range(2 * n) for r in range(2 * n)) < 1e-13
    assert abs(np.sum(w * X[:, 0] ** (2 * n)) - exact(2 * n, 0)) > 1e-9


def test_gauss_cubature_3d_box_volume_and_rejects_huge_grids():
    q = N.gauss_cubature(4, 3, 0, [1, 2, 3])
    assert q["weights"].sum() == pytest.approx(6.0, abs=1e-12) and q["nodes"].shape == (64, 3)
    with pytest.raises(ValueError):
        N.gauss_cubature(200, 4)

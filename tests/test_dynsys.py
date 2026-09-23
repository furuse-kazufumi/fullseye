# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""力学系 6 op の門。真値は**公表値か閉形式だけ**。

絵では何も確かめられない族なので、採点は全部絵の外から来る:

* 線形系 ``x' = A x`` は ``expm(At) x0`` が厳密解。刻みを半分にすると RK4 の
  誤差は 1/16 になる —— **次数そのもの**を測る(オイラー法が対照群)。
* ★リアプノフ指数の**和**は接流のトレースの時間平均に等しく、Lorenz では
  厳密に ``-(sigma + 1 + beta)``。指数を出す手続き(QR)とは独立な恒等式。
* ロジスティック写像の周期倍分岐は ``r = 3`` と ``r = 1 + sqrt6`` が**厳密**。
  ファイゲンバウム定数 4.6692 は 3 本目の分岐点との比で出る。
* 相関次元は 円 1・平面 2・カントール集合 ``log2/log3``。
* 場の**発散**は線形系で厳密に ``tr(A)``、**渦度**は ``A10 - A01`` ——
  それを測るのは PIV 族の既存 op(``piv_divergence`` / ``piv_vorticity``)で、
  この族の実装を何も知らない。
"""
import numpy as np
import pytest

import mathops


def _states_matrix(st):
    """表(列の辞書)を (T, n) の行列に戻す。"""
    cols = sorted((k for k in st if k.startswith("x")), key=lambda s: int(s[1:]))
    return np.stack([np.asarray(st[c], dtype=np.float64) for c in cols], axis=1)


def test_rk4_is_fourth_order_against_the_matrix_exponential():
    """刻み半分で誤差 1/16。厳密解は expm(At)x0(積分器と無関係)。"""
    A = np.array([[0.0, 1.0], [-1.0, 0.0]])
    x0 = np.array([1.0, 0.0])
    T = 4.0
    exact = np.array([np.cos(T), -np.sin(T)])      # expm(At)x0 の閉形式
    errs = []
    for dt in (0.04, 0.02, 0.01):
        st = mathops.ode_flow_states("linear", A.ravel(), x0, T, dt, "rk4")
        errs.append(float(np.linalg.norm(_states_matrix(st)[-1] - exact)))
    r1, r2 = errs[0] / errs[1], errs[1] / errs[2]
    assert 12.0 < r1 < 20.0, errs
    assert 12.0 < r2 < 20.0, errs
    # 対照群: オイラー法は 1 次なので、同じ刻みで桁が違う
    eu = mathops.ode_flow_states("linear", A.ravel(), x0, T, 0.01, "euler")
    e_eu = float(np.linalg.norm(_states_matrix(eu)[-1] - exact))
    assert e_eu > 100.0 * errs[-1], (e_eu, errs[-1])


def test_lyapunov_sum_matches_the_trace_identity_for_lorenz():
    """★sum(lambda) = <div f> = -(sigma + 1 + beta) は厳密。"""
    lam = np.asarray(mathops.dynsys_lyapunov_spectrum("lorenz", None, None,
                                                      120.0, 0.004, 20.0))
    sigma, beta, _rho = mathops.DYNSYS_SYSTEMS["lorenz"]
    want = -(sigma + 1.0 + beta)
    assert lam.shape == (3,)
    assert abs(float(lam.sum()) - want) < 1e-4, (lam, want)
    # 公表値 lambda1 ~ 0.906(Lorenz 1963 の標準パラメータ)
    assert 0.80 < float(lam[0]) < 1.00, lam
    # 中間の指数は理論上 0(流れの方向)
    assert abs(float(lam[1])) < 0.05, lam
    assert float(lam[2]) < -10.0, lam


def test_conservative_system_has_a_zero_lyapunov_sum():
    """対照群: 調和振動子は保存系なので和がちょうど 0 に寄る。"""
    lam = np.asarray(mathops.dynsys_lyapunov_spectrum("harmonic", None, None,
                                                      60.0, 0.002, 5.0))
    assert abs(float(lam.sum())) < 1e-3, lam


def _period_at(r, burn, keep=256, tol=1e-7):
    """写像を直接反復して周期を数える(分岐図の op とは独立)。"""
    x = 0.4
    for _ in range(burn):
        x = r * x * (1.0 - x)
    seen = []
    for _ in range(keep):
        x = r * x * (1.0 - x)
        if not any(abs(x - u) < tol for u in seen):
            seen.append(x)
    return len(seen)


def _bifurcation_point(lo, hi, period_below, burn):
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if _period_at(mid, burn) <= period_below:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def test_logistic_period_doubling_points_are_exact_and_give_feigenbaum():
    """r1 = 3、r2 = 1 + sqrt6 は厳密。比から delta = 4.6692 が出る。

    ★**残差を隠さない**: 分岐点での収束は幾何的でなく**代数的**なので、
    有限の burn-in では分岐点が必ず少し手前に見える(burn 2,000 で r1 の
    誤差 6.5e-3、20,000 で 6.0e-4)。delta も同じ向きに偶る(4.75 対 4.6692、
    1.7 %)。したがって門は「誤差が十分小さい」ではなく
    **「burn-in を伸ばすと誤差が置いていった分だけ縮む」**で置く ——
    残差の正体が写像でなく測り方であることの証拠はそっち。
    """
    r1 = _bifurcation_point(2.8, 3.2, 1, 20_000)
    r2 = _bifurcation_point(3.4, 3.5, 2, 20_000)
    r3 = _bifurcation_point(3.54, 3.56, 4, 20_000)
    assert abs(r1 - 3.0) < 2e-3, r1
    assert abs(r2 - (1.0 + np.sqrt(6.0))) < 1e-3, r2
    assert r1 < 3.0 and r2 < 1.0 + np.sqrt(6.0)     # 偏りは常に手前向き
    delta = (r2 - r1) / (r3 - r2)
    assert abs(delta - 4.6692) < 0.15, delta

    # ★残差の正体は burn-in 。短い burn での誤差は 3 倍以上大きい。
    coarse = _bifurcation_point(2.8, 3.2, 1, 2_000)
    assert abs(coarse - 3.0) > 3.0 * abs(r1 - 3.0), (coarse, r1)


def test_bifurcation_map_lands_on_those_same_branch_points():
    """分岐図の op が、上の反復で挟んだ分岐点と同じ所で枝を増やす。"""
    bm = np.asarray(mathops.dynsys_bifurcation_map("logistic", 2.5, 4.0, 300, 400, 80))
    assert bm.ndim == 2 and bm.shape[1] == 2
    assert 2.5 <= bm[:, 0].min() and bm[:, 0].max() <= 4.0

    # ★r の列を**1 本だけ**選ぶ。横に幅を持たせると、隣の r の不動点が
    # 別の柝に見えて r = 2.9 でも「3 本」になる(一度それで誤判定した)。
    def branches(r_target, tol=1e-5):
        v = np.sort(bm[bm[:, 0] == r_target, 1])
        return 1 + int((np.diff(v) > tol).sum()) if v.size else 0

    def nearest_r(x):
        return float(bm[:, 0][np.abs(bm[:, 0] - x).argmin()])

    r_lo, r_mid, r_hi = nearest_r(2.9), nearest_r(3.2), nearest_r(3.5)
    assert branches(r_lo) == 1, branches(r_lo)
    assert branches(r_mid) == 2, branches(r_mid)
    assert branches(r_hi) >= 4, branches(r_hi)


@pytest.mark.parametrize("name,want,tol", [("circle", 1.0, 0.1),
                                           ("plane", 2.0, 0.15),
                                           ("cantor", np.log(2) / np.log(3), 0.12)])
def test_correlation_dimension_hits_the_known_values(name, want, tol):
    """円 1・平面 2・カントール log2/log3。Grassberger-Procaccia の定義そのもの。"""
    rng = np.random.default_rng(0)
    if name == "circle":
        t = np.linspace(0.0, 2.0 * np.pi, 3000, endpoint=False)
        pts = np.stack([np.cos(t), np.sin(t), np.zeros_like(t)], axis=1)
    elif name == "plane":
        pts = np.column_stack([rng.random((3000, 2)), np.zeros(3000)])
    else:
        acc = np.zeros(4000)
        for k in range(1, 13):
            acc += rng.integers(0, 2, 4000) * 2.0 / 3.0 ** k
        pts = np.column_stack([acc, np.zeros(4000), np.zeros(4000)])
    got = float(mathops.dynsys_correlation_dimension(pts, max_points=1500))
    assert abs(got - want) < tol, (name, got, want)


def test_poincare_section_of_a_periodic_orbit_is_a_single_point():
    """周期軌道は断面で 1 点に重なる。カオスは広がる —— 同じ op で両方測る。"""
    st = mathops.ode_flow_states("harmonic", None, np.array([1.0, 0.0]), 60.0, 0.001)
    sec = np.asarray(mathops.dynsys_poincare_section(st, 0, 0.0, 1))
    assert sec.ndim == 2 and sec.shape[1] == 2 and sec.shape[0] > 5
    assert float(np.ptp(sec[:, 0])) < 1e-3, np.ptp(sec[:, 0])

    st2 = mathops.ode_flow_states("rossler", None, np.array([1.0, 1.0, 1.0]),
                                  400.0, 0.005)
    m = _states_matrix(st2)[20000:]
    sec2 = np.asarray(mathops.dynsys_poincare_section(m, 1, 0.0, 1))
    assert sec2.shape[0] > 20
    assert float(np.ptp(sec2[:, 0])) > 0.05, np.ptp(sec2[:, 0])


def test_vector_field_divergence_and_vorticity_are_read_by_the_piv_ops():
    """★場の発散は厳密に tr(A)、渦度は A10 - A01 —— 測るのは PIV 族の既存 op。

    ``ode_vector_field_grid`` は ``flow2d``((2, H, W) の (dy, dx))を返すので、
    ``piv_divergence`` / ``piv_vorticity`` がそのまま食う。あちらはこの族の
    実装を何も知らないので、「場が正しい」という主張の独立した採点者になる。
    """
    import fullseye as fs
    for A in ((0.0, 1.0, -1.0, 0.0), (-0.3, 1.0, -1.0, -0.3),
              (0.5, 2.0, 0.0, -1.5), (0.0, -1.0, 4.0, 0.0)):
        M = np.asarray(A, dtype=np.float64).reshape(2, 2)
        F = np.asarray(mathops.ode_vector_field_grid("linear", A,
                                                     (-1.0, 1.0, -1.0, 1.0),
                                                     (128, 128)))
        assert F.shape == (2, 128, 128)
        px = 2.0 / 127.0                             # 画素 → 状態空間の換算
        c = (slice(8, -8), slice(8, -8))
        div = np.asarray(fs.ledger.piv_divergence(F))[c] / px
        vor = np.asarray(fs.ledger.piv_vorticity(F))[c] / px
        assert abs(float(div.mean()) - float(np.trace(M))) < 1e-6, (A, div.mean())
        assert abs(float(vor.mean()) - float(M[1, 0] - M[0, 1])) < 1e-6, (A, vor.mean())


def test_systems_are_named_not_passed_as_callables():
    """★系は族名か係数配列で受ける。callable は型付き台帳に載らない。"""
    with pytest.raises(ValueError, match="unknown system"):
        mathops.ode_flow_states("no_such_system")
    with pytest.raises((ValueError, TypeError)):
        mathops.ode_flow_states(lambda t, x: x)

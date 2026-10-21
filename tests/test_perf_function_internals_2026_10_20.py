"""Performance slice 18 regression gates.

The small reference implementations intentionally preserve the pre-slice code.
"""
import math

import numpy as np
from scipy import linalg

import mathestimation
import mathgeometry
import mathnumerics


def _interp_old(xk, yk, x):
    xk, yk, x = np.asarray(xk), np.asarray(yk), np.asarray(x)
    d = xk[:, None] - xk[None, :]
    np.fill_diagonal(d, 1.0)
    logabs = np.sum(np.log(np.abs(d)), axis=1)
    sign = np.where(np.count_nonzero(d < 0, axis=1) % 2 == 1, -1.0, 1.0)
    w = sign * np.exp(np.min(logabs) - logabs)
    diff = x.ravel()[:, None] - xk[None, :]
    exact = diff == 0
    with np.errstate(divide="ignore", invalid="ignore"):
        c = w[None, :] / diff
        val = (c @ yk) / c.sum(axis=1)
    hit = exact.any(axis=1)
    val[hit] = yk[np.argmax(exact[hit], axis=1)]
    return val.reshape(x.shape), w


def _halton_old(n, dim, skip=0):
    i = np.arange(skip, skip + n, dtype=np.int64)
    return np.stack([mathnumerics._radical_inverse(i, mathnumerics._PRIMES[d])
                     for d in range(dim)], axis=1)


def _kalman_old(z, F, H, Q, R, x0, P0):
    z = np.atleast_2d(np.asarray(z, dtype=np.float64))
    x, P = np.asarray(x0, dtype=float).ravel(), np.atleast_2d(P0).astype(float)
    n, T = x.size, z.shape[0]
    xf, Pf, xp, Pp = (np.empty((T, n)), np.empty((T, n, n)),
                      np.empty((T, n)), np.empty((T, n, n)))
    nll = 0.0
    for k in range(T):
        if k:
            x, P = F @ x, F @ P @ F.T + Q
        xp[k], Pp[k] = x, P
        if np.all(np.isfinite(z[k])):
            S = H @ P @ H.T + R
            K = linalg.solve(S, H @ P, assume_a="pos").T
            r = z[k] - H @ x
            x = x + K @ r
            P = (np.eye(n) - K @ H) @ P
            P = 0.5 * (P + P.T)
            nll += .5 * float(r @ linalg.solve(S, r) + np.linalg.slogdet(2 * math.pi * S)[1])
        xf[k], Pf[k] = x, P
    xs, Ps = xf.copy(), Pf.copy()
    for k in range(T - 2, -1, -1):
        C = linalg.solve(Pp[k + 1], F @ Pf[k], assume_a="pos").T
        xs[k] = xf[k] + C @ (xs[k + 1] - xp[k + 1])
        Ps[k] = Pf[k] + C @ (Ps[k + 1] - Pp[k + 1]) @ C.T
    return xf, Pf, xs, Ps, nll


def test_interp_barycentric_matches_pre_slice_with_node_hits():
    xk = np.cos(np.linspace(np.pi, 0, 81))
    yk = np.sin(3 * xk)
    x = np.r_[xk[::7], np.linspace(-1, 1, 2050)]
    expected, _ = _interp_old(xk, yk, x)
    np.testing.assert_allclose(mathnumerics.interp_barycentric(xk, yk, x), expected,
                               rtol=1e-12, atol=1e-12)


def test_halton_columns_are_bit_identical_to_pre_slice():
    for dim in range(1, 9):
        assert np.array_equal(mathnumerics.low_discrepancy(257, dim, skip=11),
                              _halton_old(257, dim, 11))


def test_grid_heat_changes_preserve_distance_and_empty_rejection():
    mask = np.ones((24, 31), bool)
    mask[5:19, 11:14] = False
    got = mathgeometry.geodesic_heat_grid(mask, (2, 3))["distance"]
    assert np.isfinite(got[mask]).all()
    with np.testing.assert_raises(ValueError):
        mathgeometry.geodesic_heat_grid(np.zeros((3, 3), bool))


def test_local_bspline_support_and_surface_match_dense_reference():
    rng = np.random.default_rng(60)
    control = rng.normal(size=(8, 7, 3))
    weights = rng.uniform(.2, 2., size=(8, 7))
    Uu = mathgeometry._clamped_knots(8, 3)
    Uv = mathgeometry._clamped_knots(7, 2)
    u, v = np.linspace(0, 1, 29), np.linspace(0, 1, 31)
    Nu = mathgeometry._bspline_basis(Uu, 3, 8, u)
    Nv = mathgeometry._bspline_basis(Uv, 2, 7, v)
    iu, bu = mathgeometry._bspline_basis_local(Uu, 3, 8, u)
    rebuilt = np.zeros_like(Nu)
    np.put_along_axis(rebuilt, iu, bu, axis=1)
    np.testing.assert_allclose(rebuilt, Nu, rtol=1e-14, atol=1e-14)
    expected = np.einsum("ai,bj,ij,ijk->abk", Nu, Nv, weights, control)
    expected /= np.einsum("ai,bj,ij->ab", Nu, Nv, weights)[..., None]
    got = mathgeometry.nurbs_surface(control, weights, degree=(3, 2), n=(29, 31))["points"]
    np.testing.assert_allclose(got, expected, rtol=1e-12, atol=1e-12)


def test_kalman_cholesky_and_no_store_match_pre_slice():
    rng = np.random.default_rng(18)
    z = rng.normal(size=(80, 2)); z[7] = np.nan
    F = np.array([[1., .1], [0., 1.]])
    H = np.eye(2); Q = np.eye(2) * .01; R = np.eye(2) * .2
    old = _kalman_old(z, F, H, Q, R, np.zeros(2), np.eye(2))
    for store in (True, False):
        got = mathestimation.kalman_smooth(z, F, H, Q, R, np.zeros(2), np.eye(2),
                                           store_predictions=store)
        for key, expected in zip(("x_filt", "P_filt", "x_smooth", "P_smooth"), old[:4]):
            np.testing.assert_allclose(got[key], expected, rtol=1e-10, atol=1e-10)
        assert abs(got["nll"] - old[4]) < 1e-10
    fast = mathestimation.kalman_smooth(z, F, H, Q, R, np.zeros(2), np.eye(2),
                                        method="cholesky")
    np.testing.assert_allclose(fast["x_smooth"], old[2], rtol=1e-10, atol=1e-10)
    assert abs(fast["nll"] - old[4]) < 2e-10

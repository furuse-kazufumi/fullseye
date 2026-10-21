import tracemalloc

import numpy as np
import pytest
from scipy.linalg import expm
from scipy.spatial.distance import pdist

import mathops
import volprobe


def _old_corr(points, n_radii=24, r_lo=None, r_hi=None):
    p = np.asarray(points, dtype=np.float64)
    d = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=-1)
    dist = d[np.triu_indices(p.shape[0], 1)]
    pos = dist[dist > 0]
    lo = float(np.percentile(pos, 1)) if r_lo is None else float(r_lo)
    hi = float(np.percentile(pos, 25)) if r_hi is None else float(r_hi)
    radii = np.logspace(np.log10(lo), np.log10(hi), int(n_radii))
    counts = np.array([(dist < r).sum() for r in radii], dtype=np.int64)
    ok = counts > 0
    lr, lc = np.log(radii[ok]), np.log(counts[ok] / dist.size)
    a = int(0.2 * lr.size)
    b = max(a + 3, int(0.8 * lr.size))
    return radii, counts, float(np.polyfit(lr[a:b], lc[a:b], 1)[0])


@pytest.mark.parametrize("seed", [0, 4, 19])
def test_226_227_correlation_exact_counts_boundaries_duplicates(monkeypatch, seed):
    rng = np.random.default_rng(seed)
    p = rng.normal(size=(80, 3))
    p[5] = p[4]
    p[1] = p[0] + [1.0, 0.0, 0.0]
    radii, counts, expected = _old_corr(p, r_lo=0.25, r_hi=1.0)
    calls = 0
    original = np.searchsorted

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(np, "searchsorted", counted)
    got = mathops.dynsys_correlation_dimension(p, r_lo=0.25, r_hi=1.0)
    assert calls == 1
    sorted_dist = np.sort(pdist(p))
    assert np.array_equal(original(sorted_dist, radii, side="left"), counts)
    assert abs(got - expected) <= 1e-10


def test_226_condensed_distance_peak_is_at_most_one_quarter_of_reference():
    p = np.random.default_rng(226).normal(size=(4000, 3))
    tracemalloc.start()
    _old_corr(p)
    old_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    tracemalloc.start()
    mathops.dynsys_correlation_dimension(p)
    new_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert new_peak <= 0.25 * old_peak


def _old_newton(coeffs, centre, half_width, shape, max_iter, tol):
    c, roots = mathops._cplx_canonical_roots(coeffs, "reference")
    cur = mathops.cplx_plane_grid(centre, half_width, shape).astype(np.complex128).copy()
    alive = np.ones(cur.shape, dtype=bool)
    d = c[:-1] * np.arange(c.size - 1, 0, -1)
    for _ in range(max_iter):
        if not alive.any():
            break
        p, q = np.polyval(c, cur), np.polyval(d, cur)
        step = np.zeros_like(cur)
        ok = alive & (q != 0) & np.isfinite(q) & np.isfinite(p)
        step[ok] = p[ok] / q[ok]
        cur = np.where(ok, cur - step, cur)
        alive &= ok & np.isfinite(cur) & (np.abs(step) > tol)
    lab = np.zeros(cur.shape, np.int32)
    done = np.isfinite(cur) & ~alive
    if done.any():
        dist = np.abs(cur[done, None] - roots[None, :])
        near = np.argmin(dist, axis=1)
        good = dist[np.arange(near.size), near] <= max(1e-6, 1e3 * tol)
        lab.ravel()[np.flatnonzero(done.ravel())[good]] = near[good] + 1
    return lab


@pytest.mark.parametrize("coeffs", [[1, 0, -1], [1, 0, 0, -1], [1, -1, 0, 0, 1]])
@pytest.mark.parametrize("shape", [(31, 37), (64, 48)])
def test_228_231_newton_active_pixels_are_bit_identical(coeffs, shape):
    args = (coeffs, -0.1 + 0.2j, 1.7, shape, 40, 1e-10)
    assert np.array_equal(mathops.cplx_newton_basins(*args), _old_newton(*args))


def _old_escape(centre, half_width, shape, max_iter):
    grid = mathops.cplx_plane_grid(centre, half_width, shape)
    z = np.zeros_like(grid)
    out = np.full(grid.shape, float(max_iter))
    alive = np.ones(grid.shape, bool)
    for n in range(max_iter):
        z = np.where(alive, z * z + grid, z)
        gone = alive & ((z.real * z.real + z.imag * z.imag) > 4.0)
        out[gone] = n + 1.0
        alive &= ~gone
    return out


@pytest.mark.parametrize("shape", [(31, 39), (80, 64)])
def test_230_232_escape_active_and_interior_are_bit_identical(shape):
    got = mathops.cplx_escape_time("mandelbrot", centre=-0.4 + 0.1j,
                                   half_width=1.6, shape=shape, max_iter=50)
    assert np.array_equal(got, _old_escape(-0.4 + 0.1j, 1.6, shape, 50))


def test_233_laurent_fft_uniform_only_and_matches_direct(monkeypatch):
    n, start = 64, 0.37
    for direction in (1, -1):
        th = start + direction * 2 * np.pi * np.arange(n) / n
        z = 0.2 - 0.3j + 1.4 * np.exp(1j * th)
        f = z ** 3 + 2 / z
        exact = mathops.cplx_laurent_coeffs(z, f, -3, 5, method="exact")
        fast = mathops.cplx_laurent_coeffs(z, f, -3, 5, method="fast")
        assert np.allclose(fast["c"], exact["c"], atol=1e-12, rtol=0)
        order = np.random.default_rng(2).permutation(n)
        shuffled = mathops.cplx_laurent_coeffs(z[order], f[order], -3, 5, method="fast")
        assert np.allclose(shuffled["c"], exact["c"], atol=1e-12, rtol=0)
    z[1] *= np.exp(1j * 1e-12)
    called = False
    original = np.fft.fft
    def counted(*args, **kwargs):
        nonlocal called
        called = True
        return original(*args, **kwargs)
    monkeypatch.setattr(np.fft, "fft", counted)
    mathops.cplx_laurent_coeffs(z, f, -3, 5, method="fast")
    assert not called


def test_234_236_prepared_probe_exact_public_outputs_and_shared_coefficients():
    rng = np.random.default_rng(3)
    vol = rng.normal(size=(18, 17, 16))
    p0, p1, spacing = (1.2, 2.3, 0.7), (15.1, 13.2, 14.4), (2.0, 0.8, 1.3)
    prepared = volprobe.prepare_vol_probe(vol, spline_orders=(3,))
    assert np.shares_memory(prepared.volume, vol)
    assert not prepared.volume.flags.writeable
    for order in (1, 3):
        old = volprobe.vol_profile_line(vol, p0, p1, n=43, spacing=spacing, order=order)
        new = volprobe.vol_profile_line(prepared, p0, p1, n=43, spacing=spacing, order=order)
        assert np.allclose(new[0], old[0], atol=1e-12, rtol=0)
        assert np.allclose(new[1], old[1], atol=1e-12, rtol=0)
    assert volprobe.vol_edge_probe(prepared, p0, p1, spacing=spacing) == \
           volprobe.vol_edge_probe(vol, p0, p1, spacing=spacing)


def test_237_linear_rk4_matrix_is_not_exponential_and_nonlinear_unchanged(monkeypatch):
    a = np.array([[0.1, 2.0], [-1.5, -0.2]])
    h = 0.07
    got = mathops.ode_flow_states("linear", a.ravel(), [0.7, -0.4], h * 8, h)
    b = h * a
    rk = np.eye(2) + b + b @ b / 2 + b @ b @ b / 6 + b @ b @ b @ b / 24
    expected = np.array([np.linalg.matrix_power(rk, i) @ [0.7, -0.4] for i in range(9)])
    assert np.allclose(np.column_stack([got["x0"], got["x1"]]), expected, atol=1e-12, rtol=0)
    old = np.empty((9, 2))
    old[0] = [0.7, -0.4]
    for i in range(8):
        x = old[i]
        k1 = a @ x
        k2 = a @ (x + 0.5 * h * k1)
        k3 = a @ (x + 0.5 * h * k2)
        k4 = a @ (x + h * k3)
        old[i + 1] = x + h / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)
    assert np.allclose(expected, old, atol=1e-12, rtol=0)
    assert np.max(np.abs(rk - expm(b))) > 0
    calls = 0
    original = mathops._dyn_derivative
    def counted(*args):
        nonlocal calls
        calls += 1
        return original(*args)
    monkeypatch.setattr(mathops, "_dyn_derivative", counted)
    mathops.ode_flow_states("harmonic", [1.2], [1, 0], 0.2, 0.01)
    assert calls == 80

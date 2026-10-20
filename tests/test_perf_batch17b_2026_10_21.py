"""性能レビュー batch 17-B の同値性ゲート。"""

import numpy as np

import events
import tacslip


def _time_surface_old(frames, tau=2.0, thr=0.1, eps=events._EPS):
    f = np.asarray(frames, np.float64)
    if f.ndim != 3 or f.shape[0] < 2:
        raise ValueError("time_surface needs a (T,H,W) stack with T>=2")
    t_count, height, width = f.shape
    last = np.full((height, width), -np.inf, np.float64)
    for t in range(1, t_count):
        fired = events.simulate_events(f[t - 1], f[t], thr, eps) != 0.0
        last[fired] = float(t)
    age = float(t_count - 1) - last
    sae = np.where(np.isfinite(last), np.exp(-age / max(tau, 1e-6)), 0.0)
    return np.clip(sae, 0.0, 1.0)


def test_07_08_time_surface_matches_forward_scan_bit_for_bit():
    rng = np.random.default_rng(170708)
    cases = [
        rng.random((17, 31, 29)),
        np.repeat(rng.random((1, 31, 29)), 17, axis=0),
        rng.choice([0.0, 0.1, 1.0, np.nan, np.inf], (9, 7, 11)),
    ]
    cases[1][::5, ::7, ::9] += 0.2
    for frames in cases:
        got = events.time_surface(frames, tau=1.7, thr=0.13)
        expected = _time_surface_old(frames, tau=1.7, thr=0.13)
        assert np.array_equal(got, expected)


def _rigid_scalar_lstsq_old(fx, fy, ux, uy):
    n = len(fx)
    field = np.concatenate((fx, fy))
    obs = np.concatenate((ux, uy))
    ones_x = np.concatenate((np.ones(n), np.zeros(n)))
    ones_y = np.concatenate((np.zeros(n), np.ones(n)))
    return np.linalg.lstsq(np.column_stack((field, ones_x, ones_y)), obs, rcond=None)[0]


def test_17_rigid_mean_removal_matches_three_column_least_squares():
    rng = np.random.default_rng(1717)
    for n in (3, 97, 4096):
        fx, fy = rng.normal(size=(2, n))
        ux = 1.7 * fx + 0.03 + rng.normal(scale=1e-3, size=n)
        uy = 1.7 * fy - 0.02 + rng.normal(scale=1e-3, size=n)
        got = tacslip._rigid_scalar_lstsq(fx, fy, ux, uy)
        expected = _rigid_scalar_lstsq_old(fx, fy, ux, uy)
        assert np.allclose(got, expected, rtol=1e-10, atol=1e-13)


def test_17_rigid_mean_removal_preserves_rank_deficient_solution():
    fx = np.full(11, 2.0)
    fy = np.full(11, -0.5)
    ux = np.linspace(-1.0, 1.0, 11)
    uy = ux[::-1]
    got = tacslip._rigid_scalar_lstsq(fx, fy, ux, uy)
    expected = _rigid_scalar_lstsq_old(fx, fy, ux, uy)
    assert np.array_equal(got, expected)

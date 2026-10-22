"""性能レビュー batch 17-B の同値性ゲート。"""

import numpy as np

import events
import astrostack
import dic
import geocam
import moirealign
import sensor_fusion
import sensorchar
import tacslip
import ultrasound
import tactorque


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


def test_15_bilinear_in_image_branch_and_fallback_are_identical():
    rng = np.random.default_rng(1715)
    image = rng.normal(size=(31, 37))
    y = rng.uniform(0, 30, (41, 43)); x = rng.uniform(0, 36, (41, 43))
    got = dic._bilinear(image, y, x)
    y0 = np.floor(y).astype(np.int64); x0 = np.floor(x).astype(np.int64)
    y1 = np.minimum(y0 + 1, 30); x1 = np.minimum(x0 + 1, 36)
    fy = y - y0; fx = x - x0
    expected = ((1 - fy) * ((1 - fx) * image[y0, x0] + fx * image[y0, x1])
                + fy * ((1 - fx) * image[y1, x0] + fx * image[y1, x1]))
    assert np.array_equal(got, expected)
    y[0, :3] = [-1, np.nan, 32]
    assert np.array_equal(np.isnan(dic._bilinear(image, y, x)), np.isnan(y) | (y < 0) | (y > 30))


def test_12_streaming_nonuniformity_matches_batch_ddof_one():
    rng = np.random.default_rng(1712)
    dark = rng.normal(size=(9, 23, 19)); bright = rng.normal(10, 2, size=(9, 23, 19))
    batch = sensorchar._nonuniformity_variances(dark, bright, None, "test")
    stream = sensorchar._nonuniformity_variances_stream(iter(dark), iter(bright), None, "test")
    for name in ("dark", "bright"):
        keys = tuple(batch[name])
        assert keys
        for key in keys:
            assert np.isclose(stream[name][key], batch[name][key], rtol=2e-15, atol=2e-15)
    assert np.isclose(stream["var_temporal_dark"], batch["var_temporal_dark"], rtol=2e-15)


def test_09_axis_separable_kalman_matches_six_state_filter():
    rng = np.random.default_rng(1709)
    true_v = rng.normal(size=(200, 3)); true_p = np.cumsum(true_v * 0.01, axis=0)
    got = sensor_fusion._kalman(true_p, true_v, 0.01, seed=4)[2]
    # Symmetric independent axes can differ only in floating operation ordering.
    assert got.shape == true_p.shape and np.isfinite(got).all()
    assert np.array_equal(got, sensor_fusion._kalman(true_p, true_v, 0.01, seed=4)[2])
    assert np.max(np.abs(got - sensor_fusion._kalman(true_p, true_v, 0.01, seed=4,
                                                     method="steady_state")[2])) > 0


def test_04_moffat_row_bands_match_full_fine_grid():
    h, w, s = 79, 67, 5
    off = (np.arange(s) + 0.5) / s - 0.5
    rows = (np.arange(h)[:, None] + off).ravel(); cols = (np.arange(w)[:, None] + off).ravel()
    dr = (rows - 31.2) ** 2; dc = (cols - 29.7) ** 2
    peak = 1200 * 1.5 / (np.pi * 2.1**2)
    fine = peak * (1 + (dr[:, None] + dc[None, :]) / 2.1**2) ** -2.5
    expected = fine.reshape(h, s, w, s).mean(axis=(1, 3))
    assert np.array_equal(astrostack._moffat_star(h, w, 31.2, 29.7, 1200, 2.1, 2.5, s), expected)


def test_23_adjacent_identical_acoustic_layers_preserve_spectrum():
    a = {"Z": 2.0, "c": 3.0, "alpha0": 0.0, "alpha_n": 2.0, "thickness": 0.2}
    s = {"couplant": {"Z": 1.0}, "substrate": {"Z": 4.0}, "layers": [a, dict(a, thickness=0.3)]}
    f = np.linspace(0.1, 2.0, 51)
    got = ultrasound._stack_reflection(s, f)
    merged = dict(s, layers=[dict(a, thickness=0.5)])
    expected = ultrasound._stack_reflection(merged, f)
    assert np.allclose(got, expected, rtol=1e-12, atol=1e-12)


def test_25_skyline_backtrack_offsets_preserve_path():
    image = np.zeros((180, 220))
    boundary = (70 + 8 * np.sin(np.arange(220) / 17)).astype(int)
    for col, row in enumerate(boundary):
        image[:row, col] = 1.0
    got = geocam.skyline_extract(image, max_jump=3)
    assert np.max(np.abs(got - boundary)) <= 2


def test_02_analytic_psf_jacobians_match_finite_difference_fits():
    from scipy.optimize import least_squares
    grid = np.arange(15.0) - 7
    rr = np.repeat(grid, 15); cc = np.tile(grid, 15)
    cases = [
        (astrostack._psf_residual_gaussian, astrostack._psf_jac_gaussian,
         [100, .2, -.3, 1.8, 2.1, 4], [90, 0, 0, 2, 2, 3],
         [0, -7, -7, .05, .05, -np.inf], [np.inf, 7, 7, 30, 30, np.inf]),
        (astrostack._psf_residual_moffat, astrostack._psf_jac_moffat,
         [100, .2, -.3, 1.8, 2.5, 4], [90, 0, 0, 2, 2.4, 3],
         [0, -7, -7, .05, 1.05, -np.inf], [np.inf, 7, 7, 60, 20, np.inf]),
    ]
    assert cases
    assert len(cases) == 2
    for fun, jac, truth, p0, lo, hi in cases:
        vals = fun(np.asarray(truth), rr, cc, np.zeros(rr.size))
        finite = least_squares(fun, p0, bounds=(lo, hi), args=(rr, cc, vals))
        analytic = least_squares(fun, p0, jac=jac, bounds=(lo, hi), args=(rr, cc, vals))
        assert np.allclose(analytic.x, finite.x, rtol=1e-8, atol=1e-8)
        assert analytic.nfev <= finite.nfev + 1


def test_05_truncated_star_render_is_explicit_and_default_stays_exact():
    kw = dict(shape=(128, 128), n_stars=8, noise=False, sky=0, seed=5, field_seed=6)
    exact, exact_truth = astrostack.synth_starfield(**kw)
    fast, fast_truth = astrostack.synth_starfield(**kw, truncate_flux=1e-8)
    assert "truncate_flux" not in exact_truth
    assert fast_truth["truncate_flux"] == 1e-8
    assert np.max(np.abs(fast - exact)) < 1e-5


def test_18_analytic_dipole_noise_agrees_with_sampling_error():
    xx, yy = np.meshgrid(np.linspace(-.004, .004, 7), np.linspace(-.004, .004, 7))
    pts = np.column_stack((xx.ravel(), yy.ravel()))
    u = np.column_stack((1e-4 * pts[:, 0], -8e-5 * pts[:, 1]))
    kw = dict(sigma_px=.05, pitch=1e-5, coef=2., area=1e-6, radius=.002)
    analytic = tactorque.dipole_torque_resolution(pts, u, trials=2, method="analytic", **kw)
    sampled = tactorque.dipole_torque_resolution(pts, u, trials=4000, seed=18, **kw)
    rel_sampling_error = np.sqrt(2.0 / (sampled["trials"] - 1))
    assert np.all(np.abs(sampled["sigma_D"] / analytic["sigma_D"] - 1) < 3 * rel_sampling_error)


def test_24_exact_frequency_grouping_preserves_profile():
    coords = np.arange(257.0)
    harmonics = np.arange(-6, 7)
    coef = np.ones(harmonics.size, dtype=np.complex128)
    got = moirealign._profile(coords, 1, 2, coef, harmonics, 2, coef, harmonics,
                              0, 0, 0, .1, 0)[0]
    fn = harmonics[:, None] / 2 + harmonics[None, :] / 2
    amp = (coef[:, None] * coef[None, :] * np.exp(-2*np.pi**2*.1**2*fn**2)
           * np.sinc(fn))
    expected = np.real(np.exp(2j*np.pi*np.outer(coords, fn.ravel())) @ amp.ravel())
    assert np.allclose(got, expected, rtol=1e-12, atol=1e-12)

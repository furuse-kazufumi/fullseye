"""Truth gates for geometric-circle, subpixel-shift, and principal-axis fits."""
import builtins

import numpy as np
import pytest
from scipy.ndimage import fourier_shift

import filters_freq
import measure
import measure3d


def _noisy_arc(extent, seed=4):
    rng = np.random.default_rng(seed + extent)
    t = np.deg2rad(np.linspace(-extent / 2, extent / 2, 80))
    points = np.column_stack([7 + 50 * np.sin(t), -3 + 50 * np.cos(t)])
    return points + rng.normal(0, 0.5, points.shape)


@pytest.mark.parametrize("extent", [30, 60, 120, 360])
def test_geometric_circle_radius_beats_kasa_on_seeded_noisy_arcs(extent):
    # Thirty fixed noise realisations measure estimator bias instead of letting
    # one lucky long-arc sample decide the gate. Mean |radius error| (Kåsa ->
    # geometric) is about 22.14 -> 4.65, 2.39 -> 0.91, .270 -> .249 and
    # .0466 -> .0464 px for 30/60/120/360 degrees respectively.
    errors = []
    for seed in range(30):
        points = _noisy_arc(extent, seed)
        kasa = measure.fit_circle(points)
        geometric = measure.fit_circle_geometric(points)
        errors.append((abs(kasa["r"] - 50), abs(geometric["r"] - 50)))
        assert geometric["converged"] and geometric["rms"] < 0.7
    assert np.mean(errors, axis=0)[1] < np.mean(errors, axis=0)[0]


@pytest.mark.parametrize("bad", [np.array([[0., 0.], [1., 1.]]),
                                        np.column_stack([np.arange(5.), np.arange(5.)]),
                                        np.array([[0., 0.], [1., np.nan], [0., 1.]])])
def test_geometric_circle_rejects_ill_posed_input(bad):
    with pytest.raises(ValueError):
        measure.fit_circle_geometric(bad)


def _texture(shape=(96, 112)):
    y, x = np.mgrid[:shape[0], :shape[1]]
    return (np.exp(-((x - 43) ** 2 + (y - 51) ** 2) / 180)
            + .6 * np.exp(-((x - 73) ** 2 + (y - 27) ** 2) / 70)
            + .15 * np.sin(.19 * x + .11 * y))


@pytest.mark.parametrize("window,method,expected_error,grid_bias", [
    ("hann", "parabola", 0.1663, 0.1656),
    (None, "parabola", 0.1718, 0.1710),
    ("hann", "upsample", 0.0100, 0.0075),
    (None, "upsample", 0.0100, 0.0075),
])
def test_phase_correlation_shift_recovers_fourier_translation(
        window, method, expected_error, grid_bias):
    # Broadband texture gives an identifiable subpixel phase slope; the exact
    # Fourier shift has no interpolation error in its construction.
    a = np.random.default_rng(3).normal(size=(96, 112))
    truth = (2.35, -1.7)
    b = np.fft.ifftn(fourier_shift(np.fft.fftn(a), truth)).real
    got = filters_freq.phase_correlation_shift(
        a, b, window=window, whitening=0.5, method=method)
    estimate = np.array([got["dy"], got["dx"]])
    error = np.linalg.norm(estimate + truth)
    toward_grid = (np.linalg.norm(truth - np.rint(truth))
                   - np.linalg.norm(estimate - np.rint(estimate)))
    assert error == pytest.approx(expected_error, abs=5e-4)
    assert toward_grid == pytest.approx(grid_bias, abs=5e-4)
    assert got["peak_ratio"] > 1


def test_phase_shift_nonperiodic_crop_stays_within_measured_error():
    from scipy.ndimage import shift
    # A non-periodic spatial crop exposes the wrap boundary. On this fixed
    # broadband sample gives 0.196 px (Hann) and 0.193 px (no window) with the
    # deliberately simple parabola estimator.
    a = np.random.default_rng(1).normal(size=(96, 112))
    truth = np.array([3.65, -4.2])
    b = shift(a, truth, order=3, mode="constant", cval=0.0)
    eh = np.linalg.norm(np.array(list(filters_freq.phase_correlation_shift(a, b, "hann", .5, "parabola")[k]
                                      for k in ("dy", "dx"))) + truth)
    en = np.linalg.norm(np.array(list(filters_freq.phase_correlation_shift(a, b, None, .5, "parabola")[k]
                                      for k in ("dy", "dx"))) + truth)
    assert eh == pytest.approx(.1963, abs=5e-4)
    assert en == pytest.approx(.1927, abs=5e-4)


def test_phase_shift_rejects_textureless():
    with pytest.raises(ValueError, match="texture"):
        filters_freq.phase_correlation_shift(np.ones((16, 16)), np.ones((16, 16)))


def test_phase_shift_texture_test_is_intensity_scale_invariant():
    a = np.arange(256, dtype=float).reshape(16, 16)
    for scale in (1e-30, 1e30):
        got = filters_freq.phase_correlation_shift(scale * a, scale * np.roll(a, 2, 0),
                                                   window=None)
        assert got["dy"] == pytest.approx(-2.0)


def test_phase_shift_upsample_honours_partial_whitening():
    a = np.random.default_rng(3).normal(size=(96, 112))
    truth = (2.35, -1.7)
    b = np.fft.ifftn(fourier_shift(np.fft.fftn(a), truth)).real
    raw = filters_freq.phase_correlation_shift(a, b, None, 0.0, "upsample")
    half = filters_freq.phase_correlation_shift(a, b, None, 0.5, "upsample")
    assert raw["dy"] == pytest.approx(-2.35)
    assert half["dy"] == pytest.approx(-2.34)


@pytest.mark.parametrize("window", ["hann", None])
def test_phase_shift_upsample_is_below_two_hundredths_and_beats_parabola(window):
    a = np.random.default_rng(3).normal(size=(96, 112))
    truth = np.array([2.35, -1.7])
    b = np.fft.ifftn(fourier_shift(np.fft.fftn(a), truth)).real
    errors = {}
    for method in ("upsample", "parabola"):
        got = filters_freq.phase_correlation_shift(a, b, window, .5, method)
        errors[method] = np.linalg.norm(np.array([got["dy"], got["dx"]]) + truth)
    assert errors["upsample"] <= .02
    assert errors["upsample"] < errors["parabola"]


def test_phase_shift_default_needs_no_skimage(monkeypatch):
    original_import = builtins.__import__
    def blocked(name, *args, **kwargs):
        if name.startswith("skimage"):
            raise ImportError("blocked optional dependency")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", blocked)
    a = np.arange(256, dtype=float).reshape(16, 16)
    assert filters_freq.phase_correlation_shift(a, np.roll(a, 2, 0), window=None)["dy"] == -2
    assert filters_freq.phase_correlation_shift(a, np.roll(a, 2, 0), window=None,
                                                method="upsample")["dy"] == -2


def test_phase_shift_numpy_upsample_matches_skimage():
    registration = pytest.importorskip("skimage.registration")
    a = np.random.default_rng(3).normal(size=(96, 112))
    truth = (2.35, -1.7)
    b = np.fft.ifftn(fourier_shift(np.fft.fftn(a), truth)).real
    got = filters_freq.phase_correlation_shift(a, b, None, .5)
    fa, fb = np.fft.fftn(a), np.fft.fftn(b)
    aa = np.fft.ifftn(fa / (np.abs(fa) ** .5 + 1e-12)).real
    bb = np.fft.ifftn(fb / (np.abs(fb) ** .5 + 1e-12)).real
    expected, _, _ = registration.phase_cross_correlation(
        aa, bb, upsample_factor=100, normalization=None)
    assert np.linalg.norm(np.array([got["dy"], got["dx"]]) - expected) <= .01


def test_principal_fit_degeneracy_tests_are_coordinate_scale_invariant():
    curve = _curve(25)
    x, y = np.meshgrid(np.linspace(-3, 3, 13), np.linspace(-1, 1, 9))
    surface = np.column_stack([.2 * x.ravel() - .3 * y.ravel(), y.ravel(), x.ravel()])
    for scale in (1e-20, 1e20):
        assert measure.fit_curve_principal_axis(scale * curve, 2)["rms"] >= 0
        assert measure3d.fit_surface_principal_axes(scale * surface, 1)["rms"] >= 0


def _curve(angle):
    x = np.linspace(-20, 20, 101)
    q = np.column_stack([x, 3 * (x / 20) ** 2])
    a = np.deg2rad(angle)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    xy = q @ rot.T + [13, -8]
    return xy[:, ::-1]


@pytest.mark.parametrize("angle", [0, 45, 85])
def test_principal_curve_fit_is_rotation_invariant(angle):
    result = measure.fit_curve_principal_axis(_curve(angle), 2)
    assert result["rms"] < 0.04


def test_principal_line_matches_tls():
    p = _curve(45)
    # degree one is checked on an actual line, where PCA and TLS are identical.
    p = p.copy(); p[:, 0] = 2 * p[:, 1] + 4
    pa = measure.fit_curve_principal_axis(p, 1)
    tls = measure.fit_line(p)
    assert abs(((pa["angle_deg"] - tls["angle_deg"] + 90) % 180) - 90) < 1e-10


def test_principal_surface_plane_normal_matches_tls():
    x, y = np.meshgrid(np.linspace(-3, 3, 13), np.linspace(-1, 1, 9))
    p = np.column_stack([.2 * x.ravel() - .3 * y.ravel(), y.ravel(), x.ravel()])
    result = measure3d.fit_surface_principal_axes(p, 1)
    plane = measure3d.fit_plane3(p)
    assert abs(result["normal"] @ plane["normal"]) > 1 - 1e-12


def test_principal_fits_reject_isotropic_clouds():
    t = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    with pytest.raises(ValueError, match="isotropic"):
        measure.fit_curve_principal_axis(np.column_stack([np.sin(t), np.cos(t)]), 2)

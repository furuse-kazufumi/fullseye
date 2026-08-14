"""Measurement primitives on known inputs."""
import numpy as np
import pytest

import measure


def test_line_profile_on_ramp_is_linear():
    ramp = np.tile(np.linspace(0, 1, 100), (10, 1))       # varies along columns
    prof = measure.line_profile(ramp, (5, 0), (5, 99))
    assert len(prof) == 100
    assert np.isclose(prof[0], 0, atol=1e-6) and np.isclose(prof[-1], 1, atol=1e-6)
    assert np.all(np.diff(prof) >= -1e-9)                  # monotincreasing


def test_line_profile_finds_step_edge():
    img = np.zeros((20, 40)); img[:, 20:] = 1.0            # a vertical step at col 20
    prof = measure.line_profile(img, (10, 0), (10, 39))
    st = measure.profile_stats(prof)
    assert abs(st["edge_at"] - 20) <= 1                    # edge located at the step


def test_distance_and_angle():
    assert np.isclose(measure.distance((0, 0), (3, 4)), 5.0)
    assert np.isclose(measure.angle((0, 0), (0, 5)), 0.0)      # horizontal
    assert np.isclose(measure.angle((0, 0), (5, 0)), 90.0)     # straight down


def test_color_profile_shape():
    img = np.zeros((8, 8, 3)); img[:, :, 0] = 1.0
    prof = measure.line_profile(img, (0, 0), (7, 7))
    assert prof.ndim == 2 and prof.shape[1] == 3


# --------------------------------------------------------------------------- #
# Geometric primitive fitting (fit_line / fit_circle / fit_ellipse).          #
# Points are (row, col); a fit must recover the ground-truth parameters.      #
# --------------------------------------------------------------------------- #
TH = np.linspace(0, 2 * np.pi, 60, endpoint=False)


def test_fit_circle_recovers_exact_params():
    pts = np.column_stack([20 + 12 * np.sin(TH), 30 + 12 * np.cos(TH)])
    c = measure.fit_circle(pts)
    assert np.isclose(c["cy"], 20, atol=1e-6)
    assert np.isclose(c["cx"], 30, atol=1e-6)
    assert np.isclose(c["r"], 12, atol=1e-6)
    assert c["rms"] < 1e-6


def test_fit_circle_is_noise_robust():
    rng = np.random.default_rng(0)
    th = np.linspace(0, 2 * np.pi, 300, endpoint=False)
    pts = np.column_stack([40 + 9 * np.sin(th), 25 + 9 * np.cos(th)]) + rng.normal(0, 0.15, (300, 2))
    c = measure.fit_circle(pts)
    assert abs(c["cy"] - 40) < 0.1 and abs(c["cx"] - 25) < 0.1 and abs(c["r"] - 9) < 0.1


def test_fit_circle_rejects_collinear_and_short():
    with pytest.raises(ValueError):
        measure.fit_circle(np.column_stack([np.arange(10.0), np.arange(10.0) * 2.0]))
    with pytest.raises(ValueError):
        measure.fit_circle(np.array([[0.0, 0.0], [1.0, 1.0]]))          # < 3 points


def test_fit_ellipse_recovers_axis_aligned():
    pts = np.column_stack([40 + 6 * np.sin(TH), 50 + 15 * np.cos(TH)])   # major along cols
    e = measure.fit_ellipse(pts)
    assert np.isclose(e["cy"], 40, atol=1e-5) and np.isclose(e["cx"], 50, atol=1e-5)
    assert np.isclose(e["ra"], 15, atol=1e-5) and np.isclose(e["rb"], 6, atol=1e-5)
    assert abs(e["angle_deg"]) < 1e-3 and e["rms"] < 1e-6


def test_fit_ellipse_recovers_rotation():
    ra, rb, a0 = 15.0, 6.0, np.radians(30)
    xc, yc = 50.0, 40.0
    xx = ra * np.cos(TH); yy = rb * np.sin(TH)
    xr = xc + xx * np.cos(a0) - yy * np.sin(a0)
    yr = yc + xx * np.sin(a0) + yy * np.cos(a0)
    e = measure.fit_ellipse(np.column_stack([yr, xr]))
    assert np.isclose(e["ra"], 15, atol=1e-4) and np.isclose(e["rb"], 6, atol=1e-4)
    assert np.isclose(e["angle_deg"], 30, atol=1e-3)


def test_fit_ellipse_rejects_non_ellipse():
    with pytest.raises(ValueError):
        measure.fit_ellipse(np.column_stack([np.arange(10.0), np.arange(10.0) * 2.0]))  # collinear
    with pytest.raises(ValueError):
        measure.fit_ellipse(np.zeros((4, 2)))                          # < 5 points


def test_fit_rectangle2_recovers_oriented_box():
    cy, cx, l1, l2, a0 = 40.0, 50.0, 20.0, 8.0, np.radians(25)
    corners = np.array([[l1, l2], [l1, -l2], [-l1, -l2], [-l1, l2]])
    rot = np.array([[np.cos(a0), -np.sin(a0)], [np.sin(a0), np.cos(a0)]])
    outline = []
    for i in range(4):
        pa, pb = corners[i], corners[(i + 1) % 4]
        for t in np.linspace(0, 1, 20, endpoint=False):
            outline.append(pa + (pb - pa) * t)
    world = np.array(outline) @ rot.T + np.array([cx, cy])       # (x, y)
    r = measure.fit_rectangle2(np.column_stack([world[:, 1], world[:, 0]]))
    assert np.isclose(r["cy"], 40, atol=1e-4) and np.isclose(r["cx"], 50, atol=1e-4)
    assert np.isclose(r["l1"], 20, atol=1e-4) and np.isclose(r["l2"], 8, atol=1e-4)
    assert np.isclose(r["angle_deg"], 25, atol=1e-3) and r["rms"] < 1e-6


def test_fit_rectangle2_rejects_collinear():
    with pytest.raises(ValueError):
        measure.fit_rectangle2(np.column_stack([np.arange(6.0), np.arange(6.0) * 3.0]))


def test_fit_line_is_orthogonal_and_handles_vertical():
    x = np.linspace(0, 10, 20)
    line = measure.fit_line(np.column_stack([2 * x + 5, x]))           # row = 2*col + 5
    assert np.isclose(line["angle_deg"], np.degrees(np.arctan2(2, 1)), atol=1e-6)
    assert line["rms"] < 1e-6
    vert = measure.fit_line(np.column_stack([np.linspace(0, 10, 20), np.full(20, 7.0)]))
    assert vert["rms"] < 1e-9 and np.isclose(abs(vert["angle_deg"]), 90.0)


def test_fit_functions_reject_malformed_input():
    for fn in (measure.fit_line, measure.fit_circle, measure.fit_ellipse, measure.fit_rectangle2):
        with pytest.raises(ValueError):
            fn(np.zeros((5, 3)))                                       # not (N, 2)
        with pytest.raises(ValueError):
            fn(np.array([[0.0, np.nan], [1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]))


def test_fits_exposed_on_facade():
    import fullseye as fs
    for name in ("fit_line", "fit_circle", "fit_ellipse", "fit_rectangle2"):
        assert hasattr(fs, name)

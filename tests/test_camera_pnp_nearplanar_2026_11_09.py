"""Regression tests for camera.solve_pnp on near-planar models and outliers
(2026-11-09 op audit g2_calib_ct).

Before the fix a model whose relative thickness (smallest / largest principal
spread) sat between the exact-coplanarity gate (1e-6) and ~5e-2 went to general
DLT resection alone, which is rank-deficient there: translation was 90-100 %
wrong (30/30 poses at thickness 4e-6) while cv2.solvePnP was correct on the
same input. The planar homography was also unnormalised, so three outliers on
a 20-point board pulled the start far enough that LM never recovered."""
import numpy as np
import pytest

import camera

K = camera.intrinsic_matrix(800.0, 800.0, 320.0, 240.0)


def _pose(seed):
    r = np.random.default_rng(seed)
    R = camera.rodrigues(r.normal(size=3) * 0.6)
    t = np.array([r.normal() * 0.1, r.normal() * 0.1, 2.0 + r.random()])
    return r, R, t


def _near_planar(z_sigma):
    X = np.c_[np.random.default_rng(1).uniform(-0.3, 0.3, (20, 2)), np.zeros(20)]
    X[:, 2] = np.random.default_rng(5).normal(scale=z_sigma, size=20)
    return X


@pytest.mark.parametrize("z_sigma", [1e-6, 1e-4, 1e-3, 3e-3, 1e-2])
def test_near_planar_model_recovers_translation(z_sigma):
    X = _near_planar(z_sigma)
    assert not camera._coplanar(X)          # the exact gate does not fire here
    bad = []
    for k in range(30):
        r, R, t = _pose(100 + k)
        uv = camera.project_points(X, K, R, t)[0] + r.normal(scale=0.5, size=(20, 2))
        Ro, to, rms = camera.solve_pnp(X, uv, K)
        err = np.linalg.norm(to - t) / np.linalg.norm(t)
        if err >= 0.02 or rms >= 1.5:
            bad.append((k, round(float(err), 3), round(rms, 1)))
    assert not bad, bad


def test_near_planar_matches_cv2_solvepnp():
    cv2 = pytest.importorskip("cv2")
    X = _near_planar(1e-4)
    for k in range(10):
        r, R, t = _pose(200 + k)
        uv = camera.project_points(X, K, R, t)[0] + r.normal(scale=0.5, size=(20, 2))
        _, to, _ = camera.solve_pnp(X, uv, K)
        ok, rv, tv = cv2.solvePnP(X, uv, K, None, flags=cv2.SOLVEPNP_ITERATIVE)
        assert ok
        assert np.linalg.norm(to - tv.ravel()) / np.linalg.norm(tv) < 1e-3


def _planar_with_outliers():
    rng = np.random.default_rng(0)
    rng.uniform(-0.3, 0.3, (20, 3))         # keep the probe's stream position
    return np.c_[rng.uniform(-0.3, 0.3, (20, 2)), np.zeros(20)]


def test_planar_with_outliers_no_worse_than_twice_cv2():
    cv2 = pytest.importorskip("cv2")
    Xp = _planar_with_outliers()
    eo, ec = [], []
    for s in range(30):
        r, R, t = _pose(100 + s)
        uv = camera.project_points(Xp, K, R, t)[0] + r.normal(scale=0.5, size=(20, 2))
        ii = r.choice(20, 3, replace=False)
        uv[ii] += r.uniform(-80, 80, (3, 2))
        _, to, _ = camera.solve_pnp(Xp, uv, K)
        eo.append(np.linalg.norm(to - t) / np.linalg.norm(t))
        ok, rv, tv = cv2.solvePnP(Xp, uv, K, None, flags=cv2.SOLVEPNP_ITERATIVE)
        ec.append(np.linalg.norm(tv.ravel() - t) / np.linalg.norm(t))
    eo, ec = np.array(eo), np.array(ec)
    assert np.median(eo) <= 2.0 * np.median(ec), (np.median(eo), np.median(ec))
    # no pose may be lost outright (unnormalised init: 4 of 8 poses ~100 % off)
    assert eo.max() <= 2.0 * ec.max(), (eo.max(), ec.max())


def test_nonfinite_input_is_a_named_value_error():
    X = _near_planar(1e-2)
    _, R, t = _pose(3)
    uv = camera.project_points(X, K, R, t)[0]
    uv[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        camera.solve_pnp(X, uv, K)


def test_docstring_points_to_ransac():
    assert "pnp_ransac" in camera.solve_pnp.__doc__


# --- the thickness switch (independent review 2026-11-09) ------------------ #
# The first fix tried the planar start only below a thickness ratio of 0.1; above
# it DLT alone lost 1 of 30 poses per cell with 8 points (ratios 0.11-0.36) and,
# with 3 outliers on 20 points, the median error jumped from 0.044 to 0.48.
def _boundary_model(z_sigma, n, seed_pts):
    X = np.c_[np.random.default_rng(seed_pts).uniform(-0.3, 0.3, (n, 2)), np.zeros(n)]
    X[:, 2] = np.random.default_rng(5 + seed_pts).normal(scale=z_sigma, size=n)
    return X


@pytest.mark.parametrize("z_sigma", [0.01, 0.02, 0.03, 0.05, 0.08])
@pytest.mark.parametrize("seed_pts", [1, 2, 3])
def test_eight_points_across_the_old_switch(z_sigma, seed_pts):
    X = _boundary_model(z_sigma, 8, seed_pts)
    bad = []
    for k in range(30):
        r, R, t = _pose(100 + k)
        uv = camera.project_points(X, K, R, t)[0] + r.normal(scale=0.5, size=(8, 2))
        _, to, rms = camera.solve_pnp(X, uv, K)
        err = np.linalg.norm(to - t) / np.linalg.norm(t)
        if err > 0.05:
            bad.append((k, round(float(err), 3), round(rms, 1)))
    assert not bad, (camera._thickness_ratio(X), bad)


def test_outliers_have_no_step_at_the_old_switch():
    # medians just below and just above a thickness ratio of 0.1 stay comparable
    meds = {}
    for zs, sp in ((0.02, 2), (0.02, 1), (0.03, 2)):
        X = _boundary_model(zs, 20, sp)
        eo = []
        for k in range(30):
            r, R, t = _pose(100 + k)
            uv = camera.project_points(X, K, R, t)[0] + r.normal(scale=0.5, size=(20, 2))
            ii = r.choice(20, 3, replace=False)
            uv[ii] += r.uniform(-80, 80, (3, 2))
            _, to, _ = camera.solve_pnp(X, uv, K)
            eo.append(np.linalg.norm(to - t) / np.linalg.norm(t))
        meds[round(camera._thickness_ratio(X), 3)] = float(np.median(eo))
    assert min(meds) < 0.1 < max(meds), meds
    assert max(meds.values()) < 0.2, meds

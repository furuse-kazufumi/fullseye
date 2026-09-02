"""Ground-truth tests for fit_primitives_ext (cone / torus / ellipsoid fitting).

Every cloud is sampled from a primitive with known parameters, so the fit is
checked against the exact truth rather than for plausibility."""
import numpy as np
import pytest

import fit_primitives_ext as fpe


def _perp_basis(d):
    d = d / np.linalg.norm(d)
    a = np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(d, a); e1 /= np.linalg.norm(e1)
    e2 = np.cross(d, e1)
    return e1, e2


def _cone(apex, axis, half_angle, n=300, seed=0, a_range=(0.5, 3.0)):
    rng = np.random.default_rng(seed)
    axis = axis / np.linalg.norm(axis)
    e1, e2 = _perp_basis(axis)
    a = rng.uniform(*a_range, n)
    th = rng.uniform(0, 2 * np.pi, n)
    rad = a * np.tan(half_angle)
    return apex + np.outer(a, axis) + rad[:, None] * (np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2)


def _check(o, apex, axis, half_angle, tol_apex=1e-3, tol_axis_deg=0.1, tol_ha_deg=0.1):
    axis = axis / np.linalg.norm(axis)
    assert np.linalg.norm(o["apex"] - apex) < tol_apex, o["apex"]
    assert np.degrees(np.arccos(np.clip(o["axis"] @ axis, -1, 1))) < tol_axis_deg
    assert np.degrees(abs(o["half_angle"] - half_angle)) < tol_ha_deg


def test_fit_cone_reviewer_case_25deg_no_longer_raises():
    """Regression (2026-09-02): a clean 25 deg cone (apex (0.5,-1,2), axis ~(0.1,-0.2,1),
    axial extent 0.5..3) raised 'half-angle ~0' because the PCA axis heuristic picked a
    radial eigenvector (the axial and radial variances happen to be close), leaving
    a slope ~0 in the radius-vs-axis regression. All three PCA axes are now tried."""
    apex = np.array([0.5, -1.0, 2.0])
    axis = np.array([0.1, -0.2, 1.0])
    ha = np.deg2rad(25)
    o = fpe.fit_cone(_cone(apex, axis, ha, seed=0))
    _check(o, apex, axis, ha)
    assert o["residual"] < 1e-8
    on = fpe.fit_cone(_cone(apex, axis, ha, seed=0) + np.random.default_rng(1).normal(0, 0.01, (300, 3)))
    _check(on, apex, axis, ha, tol_apex=0.05, tol_axis_deg=1.0, tol_ha_deg=1.0)


@pytest.mark.parametrize("seed", range(40))
def test_fit_cone_clean_cones_never_raise(seed):
    """40 random clean cones (half-angle 5..70 deg, random pose, random axial extent so
    the axial/radial variance ratio sweeps through 1): zero raises, exact recovery."""
    rng = np.random.default_rng(100 + seed)
    apex = rng.normal(size=3)
    axis = rng.normal(size=3)
    ha = np.deg2rad(rng.uniform(5, 70))
    lo = rng.uniform(0.2, 1.0)
    hi = lo + rng.uniform(0.5, 3.0)
    o = fpe.fit_cone(_cone(apex, axis, ha, seed=seed, a_range=(lo, hi)))
    _check(o, apex, axis, ha)
    assert o["residual"] < 1e-8


def test_fit_cone_rejects_cylinder_like_input():
    rng = np.random.default_rng(3)
    th = rng.uniform(0, 2 * np.pi, 200)
    h = rng.uniform(-2, 2, 200)
    cyl = np.c_[np.cos(th), np.sin(th), h]                # half-angle 0 -> not a cone
    with pytest.raises(ValueError):
        fpe.fit_cone(cyl)


def test_fit_torus_and_ellipsoid_still_exact():
    rng = np.random.default_rng(4)
    ctr = np.array([1.0, 2.0, 3.0])
    tax = np.array([0.3, 0.1, 1.0]); tax /= np.linalg.norm(tax)
    e1, e2 = _perp_basis(tax)
    u = rng.uniform(0, 2 * np.pi, 500); w = rng.uniform(0, 2 * np.pi, 500)
    tor = (ctr + np.outer((2.0 + 0.5 * np.cos(w)) * np.cos(u), e1)
           + np.outer((2.0 + 0.5 * np.cos(w)) * np.sin(u), e2) + np.outer(0.5 * np.sin(w), tax))
    o = fpe.fit_torus(tor)
    assert np.linalg.norm(o["center"] - ctr) < 1e-6 and abs(o["R"] - 2.0) < 1e-6 and abs(o["r"] - 0.5) < 1e-6
    v = rng.normal(size=(400, 3)); v /= np.linalg.norm(v, axis=1, keepdims=True)
    ell = np.array([-1, 0.5, 2.0]) + v * np.array([3.0, 2.0, 1.0])
    o = fpe.fit_ellipsoid(ell)
    assert np.allclose(np.sort(o["radii"]), [1.0, 2.0, 3.0], atol=1e-6)

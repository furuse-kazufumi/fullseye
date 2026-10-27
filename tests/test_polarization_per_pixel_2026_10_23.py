# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Per-pixel polarisation (2026-10-23): Stokes/DoLP/AoLP maps, element fields, finite extinction, conventions.

A private PoC (silicon photoelasticity under SWIR polarisation) found four gaps by running:

1. no per-pixel Stokes / DoLP / AoLP op (``polarization_stokes`` is a spatial mean) →
   ``specularity.polarization_stokes_map``;
2. ``optics.mueller_element`` / ``jones_element`` refused an angle or retardance *field* →
   they now return ``(..., 4, 4)`` / ``(..., 2, 2)``; the scalar path is pinned bit-for-bit
   against a verbatim copy of the old code below;
3. the angle sense (image y points down) and the circular handedness were unwritten →
   documented, and the gates here fail if either sign flips;
4. no polariser with a finite extinction ratio → ``optics.mueller_partial_polarizer``.

Every truth here is closed form: Malus's law, Mueller calculus, the diattenuator matrix,
and an independent Jones → Mueller conversion.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

import optics
import opsoptics
import opsspecular
import sfpolar
import specularity as sp


# --------------------------------------------------------------------------- #
# verbatim copy of the scalar code as it was on master before 2026-10-23       #
# --------------------------------------------------------------------------- #
def _old_rot2(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s], [s, c]], dtype=np.float64)


def _old_jones(kind="polarizer", angle_deg=0.0, retardance_deg=90.0):
    k = kind.strip().lower()
    a = np.radians(optics._finite_scalar(angle_deg, "angle_deg"))
    if k == "rotator":
        return np.ascontiguousarray(_old_rot2(a), dtype=np.complex128)
    if k == "polarizer":
        j0 = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=np.complex128)
    else:
        d = {"quarter_wave": 90.0, "half_wave": 180.0}.get(k, None)
        if d is None:
            d = optics._finite_scalar(retardance_deg, "retardance_deg")
        d = np.radians(d)
        j0 = np.array([[np.exp(-0.5j * d), 0.0], [0.0, np.exp(0.5j * d)]],
                      dtype=np.complex128)
    r = _old_rot2(a).astype(np.complex128)
    return np.ascontiguousarray(r @ j0 @ r.T, dtype=np.complex128)


def _old_mueller(kind="polarizer", angle_deg=0.0, retardance_deg=90.0):
    k = kind.strip().lower()
    a = np.radians(optics._finite_scalar(angle_deg, "angle_deg"))
    c, s = np.cos(2.0 * a), np.sin(2.0 * a)
    if k == "depolarizer":
        m = np.diag([1.0, 0.0, 0.0, 0.0])
    elif k == "polarizer":
        m = 0.5 * np.array([[1.0, c, s, 0.0],
                            [c, c * c, c * s, 0.0],
                            [s, c * s, s * s, 0.0],
                            [0.0, 0.0, 0.0, 0.0]], dtype=np.float64)
    elif k == "rotator":
        m = np.array([[1.0, 0.0, 0.0, 0.0],
                      [0.0, c, -s, 0.0],
                      [0.0, s, c, 0.0],
                      [0.0, 0.0, 0.0, 1.0]], dtype=np.float64)
    else:
        d = {"quarter_wave": 90.0, "half_wave": 180.0}.get(k, None)
        if d is None:
            d = optics._finite_scalar(retardance_deg, "retardance_deg")
        d = np.radians(d)
        cd, sd = np.cos(d), np.sin(d)
        m = np.array([[1.0, 0.0, 0.0, 0.0],
                      [0.0, c * c + s * s * cd, c * s * (1.0 - cd), -s * sd],
                      [0.0, c * s * (1.0 - cd), s * s + c * c * cd, c * sd],
                      [0.0, s * sd, -c * sd, cd]], dtype=np.float64)
    return np.ascontiguousarray(m, dtype=np.float64)


_ANGLES = [0.0, 1e-9, 21.5, 30.0, 45.0, -45.0, 90.0, 123.456, 180.0, 359.9, 7200.25,
           np.float32(17.0), np.int64(60), np.array(33.0)]
_RETS = [0.0, 33.3, 90.0, 180.0, -12.5, 720.0]


# --------------------------------------------------------------------------- #
# 2. element fields, scalar path unchanged                                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kind", list(optics.MUELLER_KINDS))
def test_mueller_scalar_path_bit_identical_to_old_code(kind):
    for a in _ANGLES:
        for d in _RETS:
            new = optics.mueller_element(kind, a, d)
            old = _old_mueller(kind, a, d)
            assert new.shape == (4, 4) and new.dtype == np.float64
            assert new.tobytes() == old.tobytes(), (kind, a, d)


@pytest.mark.parametrize("kind", list(optics.JONES_KINDS))
def test_jones_scalar_path_bit_identical_to_old_code(kind):
    for a in _ANGLES:
        for d in _RETS:
            new = optics.jones_element(kind, a, d)
            old = _old_jones(kind, a, d)
            assert new.shape == (2, 2) and new.dtype == np.complex128
            assert new.tobytes() == old.tobytes(), (kind, a, d)


def test_fixed_kinds_still_ignore_a_retardance_array():
    # Before: quarter_wave never looked at retardance_deg, so even an array passed.
    # That stays a scalar call returning (4, 4) / (2, 2).
    r = np.array([1.0, 2.0, 3.0])
    assert optics.mueller_element("quarter_wave", 30.0, r).tobytes() == \
        _old_mueller("quarter_wave", 30.0, 0.0).tobytes()
    assert optics.jones_element("polarizer", 30.0, r).shape == (2, 2)


@pytest.mark.parametrize("kind", list(optics.MUELLER_KINDS))
def test_mueller_angle_field_matches_scalar_per_entry(kind):
    ang = np.array([[0.0, 21.5, 45.0], [90.0, 123.456, -30.0]])
    m = optics.mueller_element(kind, ang, 47.0)
    assert m.shape == (2, 3, 4, 4) and m.dtype == np.float64
    worst = max(np.abs(m[i, j] - optics.mueller_element(kind, float(ang[i, j]), 47.0)).max()
                for i in range(2) for j in range(3))
    assert worst <= 1e-15


@pytest.mark.parametrize("kind", list(optics.JONES_KINDS))
def test_jones_angle_field_matches_scalar_per_entry(kind):
    ang = np.linspace(-80.0, 170.0, 12).reshape(3, 4)
    j = optics.jones_element(kind, ang, 47.0)
    assert j.shape == (3, 4, 2, 2) and j.dtype == np.complex128
    worst = max(np.abs(j[i, k] - optics.jones_element(kind, float(ang[i, k]), 47.0)).max()
                for i in range(3) for k in range(4))
    assert worst <= 1e-15


def test_retardance_field_broadcasts_with_angle_field():
    th = np.array([[0.0], [30.0]])                    # (2, 1)
    de = np.array([10.0, 90.0, 200.0])                # (3,)
    m = optics.mueller_element("retarder", th, de)
    j = optics.jones_element("retarder", th, de)
    assert m.shape == (2, 3, 4, 4) and j.shape == (2, 3, 2, 2)
    for a in range(2):
        for b in range(3):
            assert np.abs(m[a, b] - optics.mueller_element(
                "retarder", float(th[a, 0]), float(de[b]))).max() <= 1e-15
            assert np.abs(j[a, b] - optics.jones_element(
                "retarder", float(th[a, 0]), float(de[b]))).max() <= 1e-15


def test_jones_field_and_mueller_field_give_the_same_stokes():
    # Two independent constructions must agree pixel by pixel (sign slips show here).
    th = np.linspace(0.0, 180.0, 7)
    de = np.linspace(0.0, 360.0, 7)
    J = optics.jones_element("retarder", th, de)
    M = optics.mueller_element("retarder", th, de)
    e_in = np.array([math.cos(0.3), math.sin(0.3) * 1j])
    for i in range(th.size):
        s_j = optics.stokes_from_jones(J[i] @ e_in)
        s_m = M[i] @ optics.stokes_from_jones(e_in)
        assert np.abs(s_j - s_m).max() <= 1e-14


def test_dark_field_circular_polariscope_from_fields_is_sin2_half_delta():
    # Textbook: dark-field circular polariscope I = sin^2(delta/2) of the unpolarised
    # intensity * 1/2, independent of the isoclinic angle theta.
    rng = np.random.default_rng(7)
    th = rng.uniform(0, 180, (6, 5))
    de = rng.uniform(0, 720, (6, 5))
    p0 = optics.mueller_element("polarizer", 0.0)
    q1 = optics.mueller_element("quarter_wave", 45.0)
    q2 = optics.mueller_element("quarter_wave", -45.0)
    an = optics.mueller_element("polarizer", 90.0)
    spec = optics.mueller_element("retarder", th, de)
    train = an @ q2 @ spec @ q1 @ p0
    out = optics.mueller_apply(train, np.array([1.0, 0.0, 0.0, 0.0]))
    assert out.shape == (6, 5, 4)
    want = 0.5 * np.sin(np.radians(de) / 2.0) ** 2
    assert np.abs(out[..., 0] - want).max() <= 1e-15


@pytest.mark.parametrize("bad, msg", [
    (np.array([0.0, np.nan]), "non-finite"),
    (np.array([True, False]), "bool"),
    (np.array(["10", "20"]), "numeric"),
    (np.array([1 + 1j, 2.0]), "complex"),
    (np.array([]), "empty"),
    ([[0.0, 1.0], [2.0]], "ragged"),
    (np.ma.masked_array([1.0, 2.0], mask=[0, 1]), "masked"),
])
def test_element_fields_fail_closed(bad, msg):
    for fn in (optics.mueller_element, optics.jones_element):
        with pytest.raises(ValueError, match=msg):
            fn("polarizer", bad)
        with pytest.raises(ValueError, match=msg):
            fn("retarder", 10.0, bad)


def test_element_fields_refuse_non_broadcasting_and_oversize():
    with pytest.raises(ValueError, match="broadcast"):
        optics.mueller_element("retarder", np.zeros(3), np.zeros(4))
    big = np.zeros(optics.MAX_FIELD_ELEMENTS // 16 + 1)
    with pytest.raises(ValueError, match="MAX_FIELD_ELEMENTS"):
        optics.mueller_element("polarizer", big)
    with pytest.raises(ValueError, match="unknown kind"):
        optics.mueller_element("bogus", np.zeros(3))
    with pytest.raises(ValueError, match="unknown kind"):
        optics.jones_element("depolarizer", np.zeros(3))   # Mueller-only kind


# --------------------------------------------------------------------------- #
# 4. finite extinction ratio                                                    #
# --------------------------------------------------------------------------- #
def _jones_to_mueller(J):
    """Generic coherency conversion, written independently of optics' Mueller code.

    Basis of the coherency vector (Ex Ex*, Ex Ey*, Ey Ex*, Ey Ey*); the S3 row follows
    optics.stokes_from_jones (S3 = 2 Im(Ex Ey*)).
    """
    A = np.array([[1, 0, 0, 1], [1, 0, 0, -1], [0, 1, 1, 0], [0, -1j, 1j, 0]])
    M = A @ np.kron(J, J.conj()) @ np.linalg.inv(A)
    assert np.abs(M.imag).max() <= 1e-14
    return M.real


@pytest.mark.parametrize("angle", [0.0, 21.5, 45.0, 100.0, -33.0])
@pytest.mark.parametrize("er,t1", [(1.0, 1.0), (10.0, 0.8), (1000.0, 0.92), (1e6, 0.5)])
def test_partial_polarizer_equals_jones_diattenuator(angle, er, t1):
    a = math.radians(angle)
    r = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    J = r @ np.diag([math.sqrt(t1), math.sqrt(t1 / er)]) @ r.T
    M = optics.mueller_partial_polarizer(angle, er, t1)
    assert M.shape == (4, 4)
    assert np.abs(M - _jones_to_mueller(J)).max() <= 1e-15


@pytest.mark.parametrize("er", [1.0, 2.0, 50.0, 1e3, 1e5])
def test_partial_polarizer_closed_forms(er):
    t1 = 0.9
    t2 = t1 / er
    P = optics.mueller_partial_polarizer(0.0, er, t1)
    out = P @ np.array([1.0, 0.0, 0.0, 0.0])
    assert abs(out[0] - (t1 + t2) / 2) <= 1e-16
    if er > 1.0:
        dop = optics.stokes_analyze(out)["dop"]
        assert abs(dop - (er - 1) / (er + 1)) <= 1e-15
    # parallel vs crossed pair
    par = (P @ P @ np.array([1.0, 0, 0, 0]))[0]
    crs = (optics.mueller_partial_polarizer(90.0, er, t1) @ P @ np.array([1.0, 0, 0, 0]))[0]
    assert abs(par - (t1 ** 2 + t2 ** 2) / 2) <= 1e-15
    assert abs(crs - t1 * t2) <= 1e-15
    if er > 1.0:
        assert abs(par / crs - (er ** 2 + 1) / (2 * er)) <= 1e-9 * (er ** 2 + 1) / (2 * er)
    # Malus with leakage: fully polarised input at theta to the axis
    for th in np.linspace(0, 180, 13):
        s_in = np.array([1.0, math.cos(2 * math.radians(th)), math.sin(2 * math.radians(th)), 0])
        got = (P @ s_in)[0]
        assert abs(got - (t2 + (t1 - t2) * math.cos(math.radians(th)) ** 2)) <= 1e-15


def test_partial_polarizer_limits_and_field():
    ideal = optics.mueller_element("polarizer", 30.0)
    near = optics.mueller_partial_polarizer(30.0, 1e12, 1.0)
    assert np.abs(near - ideal).max() <= 2e-6               # Q/2 = sqrt(T1 T2) = 1e-6
    nd = optics.mueller_partial_polarizer(77.0, 1.0, 0.25)
    assert np.abs(nd - 0.25 * np.eye(4)).max() <= 1e-16
    ang = np.array([[0.0, 21.5], [45.0, 90.0]])
    f = optics.mueller_partial_polarizer(ang, 100.0, 0.9)
    assert f.shape == (2, 2, 4, 4)
    for i in range(2):
        for k in range(2):
            assert np.abs(f[i, k] - optics.mueller_partial_polarizer(
                float(ang[i, k]), 100.0, 0.9)).max() <= 1e-16


@pytest.mark.parametrize("kw, msg", [
    ({"extinction_ratio": 0.5}, ">= 1"),
    ({"extinction_ratio": float("inf")}, "finite"),
    ({"extinction_ratio": "100"}, "string"),
    ({"transmission": 0.0}, r"\(0, 1\]"),
    ({"transmission": 1.5}, r"\(0, 1\]"),
    ({"angle_deg": float("nan")}, "finite"),
    ({"angle_deg": True}, "bool"),
])
def test_partial_polarizer_fail_closed(kw, msg):
    with pytest.raises(ValueError, match=msg):
        optics.mueller_partial_polarizer(**kw)


# --------------------------------------------------------------------------- #
# 1. per-pixel Stokes / DoLP / AoLP                                             #
# --------------------------------------------------------------------------- #
def _sweep_from_stokes(S, angles):
    """Analyser frames of a Stokes field ``(H, W, 4)`` through ideal polarisers (Mueller path)."""
    return np.stack([optics.mueller_apply(optics.mueller_element("polarizer", t), S)[..., 0]
                     for t in angles])


def _field_through(M, s_in=(1.0, 0.0, 0.0, 0.0)):
    return optics.mueller_apply(M, np.asarray(s_in, dtype=float))


def test_dofp_closed_form_matches_textbook_differences():
    rng = np.random.default_rng(3)
    S = np.zeros((5, 6, 4))
    S[..., 0] = rng.uniform(0.5, 2.0, (5, 6))
    lin = rng.uniform(0, 1, (5, 6)) * S[..., 0]
    ang = rng.uniform(0, np.pi, (5, 6))
    S[..., 1], S[..., 2] = lin * np.cos(2 * ang), lin * np.sin(2 * ang)
    I = _sweep_from_stokes(S, (0, 45, 90, 135))
    r = sp.polarization_stokes_map(I)
    assert np.abs(r["s0"] - I.sum(0) / 2).max() <= 1e-14
    assert np.abs(r["s1"] - (I[0] - I[2])).max() <= 1e-14
    assert np.abs(r["s2"] - (I[1] - I[3])).max() <= 1e-14
    for k, j in (("s0", 0), ("s1", 1), ("s2", 2)):
        assert np.abs(r[k] - S[..., j]).max() <= 1e-14
    assert np.abs(r["dolp"] - lin / S[..., 0]).max() <= 1e-13
    d = np.abs(r["aolp_deg"] - np.degrees(ang))
    assert np.minimum(d, 180 - d).max() <= 1e-10
    assert r["lit"].all() and r["aolp_defined"].all()


@pytest.mark.parametrize("angles", [(0.0, 60.0, 120.0),
                                    (5.0, 20.0, 47.0, 90.0, 111.0, 150.0, 171.0)])
def test_arbitrary_angles_least_squares_is_exact_on_noise_free_frames(angles):
    th = np.array([[10.0, 70.0], [130.0, 175.0]])
    S = _field_through(optics.mueller_partial_polarizer(th, 20.0, 0.8))
    I = _sweep_from_stokes(S, angles)
    r = sp.polarization_stokes_map(I, angles_deg=angles)
    assert np.abs(r["dolp"] - 19.0 / 21.0).max() <= 1e-13          # (ER-1)/(ER+1)
    d = np.abs(r["aolp_deg"] - th)
    assert np.minimum(d, 180 - d).max() <= 1e-9
    # Malus rebuild of the input frames from the returned Stokes images
    t = np.radians(np.asarray(angles))[:, None, None]
    rebuilt = 0.5 * (r["s0"] + r["s1"] * np.cos(2 * t) + r["s2"] * np.sin(2 * t))
    assert np.abs(rebuilt - I).max() <= 1e-14


def test_ideal_polariser_field_has_dolp_one_and_aolp_equal_to_its_angle():
    # A "known angle" synthetic image: a radial polariser — the axis at every pixel
    # points along atan2(row - c, col - c), measured x -> y (down the rows).
    H = W = 33
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    th = np.degrees(np.arctan2(yy - 16.0, xx - 16.0)) % 180.0
    S = _field_through(optics.mueller_element("polarizer", th))
    r = sp.polarization_stokes_map(_sweep_from_stokes(S, (0, 45, 90, 135)))
    assert np.abs(r["dolp"] - 1.0).max() <= 1e-14
    d = np.abs(r["aolp_deg"] - th)
    assert np.minimum(d, 180 - d).max() <= 1e-10


def test_spatial_mean_equals_polarization_stokes():
    rng = np.random.default_rng(11)
    th = rng.uniform(0, 180, (8, 9))
    S = _field_through(optics.mueller_partial_polarizer(th, 5.0, 0.7))
    I = _sweep_from_stokes(S, (0, 45, 90, 135)) + 0.05
    r = sp.polarization_stokes_map(I)
    whole = sp.polarization_stokes(I)
    assert abs(r["s0"].mean() - whole[0]) <= 1e-15
    assert abs(r["s1"].mean() - whole[1]) <= 1e-15
    assert abs(r["s2"].mean() - whole[2]) <= 1e-15
    assert np.abs(r["dolp"] - sp.polarization_dolp_map(I)).max() <= 1e-15


def test_dark_and_unpolarised_pixels_are_masked_never_nan():
    I = np.zeros((4, 3, 3))
    I[:, 0, 0] = 1.0                       # unpolarised: same in every frame
    I[:, 1, 1] = [1.0, 0.5, 0.0, 0.5]      # fully polarised at 0 degrees
    r = sp.polarization_stokes_map(I)
    assert len(r) == 8                     # 7 + "residual" (2026-10-24, additive)
    for v in r.values():
        assert np.isfinite(v).all() if v.dtype != bool else True
    assert not r["lit"][2, 2] and r["dolp"][2, 2] == 0.0 and r["aolp_deg"][2, 2] == 0.0
    # Lit and unpolarised: DoLP is rounding dust of the fit (0 on Windows, 5.6e-17 on the Linux CI
    # runner), never exactly-zero by contract; the angle is what must stay undefined.
    assert r["lit"][0, 0] and r["dolp"][0, 0] <= 1e-15 and not r["aolp_defined"][0, 0]
    assert r["aolp_defined"][1, 1] and r["dolp"][1, 1] == pytest.approx(1.0, abs=1e-15)
    assert min(r["aolp_deg"][1, 1], 180 - r["aolp_deg"][1, 1]) <= 1e-12


@pytest.mark.parametrize("angles", [(0, 45, 90, 135), (3, 20, 47, 90, 111, 150, 171)])
def test_uniform_unpolarised_sweep_has_no_aolp_at_any_scale(angles):
    # Rounding dust of the fit (DoLP ~3e-16) must not become an angle.
    rng = np.random.default_rng(0)
    for scale in (1e-6, 1e-3, 1.0, 7.3, 1e4, 1e9):
        one = rng.uniform(0.1, 1.0, (1, 20, 20)) * scale
        r = sp.polarization_stokes_map(np.repeat(one, len(angles), 0), angles_deg=angles)
        assert not r["aolp_defined"].any() and (r["aolp_deg"] == 0.0).all()
        assert r["dolp"].max() <= 1e-15 and r["lit"].all()


def test_clamped_pixels_come_back_physical():
    # A pixel whose modulation exceeds its mean (no analyser can produce it):
    # refused by default, clamped onto the physical cone when allowed.
    I = np.full((4, 2, 2), 1.0)
    I[:, 0, 0] = [2.0, 1.0, -0.2, 1.0]
    with pytest.raises(ValueError, match="negative"):
        sp.polarization_stokes_map(I)
    r = sp.polarization_stokes_map(I, max_violation_frac=0.5)
    lin = np.hypot(r["s1"], r["s2"])
    assert (lin <= r["s0"] * (1 + 1e-15)).all() and (r["s0"] >= 0).all()
    assert r["dolp"].max() <= 1.0
    S = np.stack([r["s0"], r["s1"], r["s2"], 0 * r["s0"]], -1)
    optics.mueller_apply(optics.mueller_element("polarizer", 0.0), S)   # accepted


@pytest.mark.parametrize("args, msg", [
    ((np.zeros((2, 3, 3)), (0, 45)), "at least 3"),
    ((np.zeros((4, 3, 3)), (0, 45, 90)), "correspond"),
    ((np.full((4, 3, 3), np.nan),), "non-finite"),
    ((np.zeros((3, 3, 3)), (0, 180, 90)), "do not determine"),
    ((np.zeros((3, 3)),), "shape"),
])
def test_stokes_map_fail_closed(args, msg):
    with pytest.raises(ValueError, match=msg):
        sp.polarization_stokes_map(*args)


# --------------------------------------------------------------------------- #
# 3. conventions: the sign gates                                               #
# --------------------------------------------------------------------------- #
def test_aolp_returns_the_known_angle_and_a_flipped_sign_is_caught():
    S = _field_through(optics.mueller_element("polarizer", np.full((3, 3), 21.5)))
    I = _sweep_from_stokes(S, (0, 45, 90, 135))
    good = sp.polarization_stokes_map(I, angles_deg=(0, 45, 90, 135))["aolp_deg"]
    assert np.abs(good - 21.5).max() <= 1e-10
    # The same frames labelled with the other sense (counter-clockwise on a y-up
    # display) mirror the axis: 21.5 -> 158.5. The gate is sensitive to the sign.
    flipped = sp.polarization_stokes_map(I, angles_deg=(0, -45, -90, -135))["aolp_deg"]
    assert np.abs(flipped - 158.5).max() <= 1e-10
    assert np.abs(flipped - 21.5).min() > 100.0


def test_angle_sense_is_tied_to_image_rows_pointing_down():
    # Geometry, not algebra: a surface normal tilted toward +column and +row (down)
    # has image azimuth atan2(ny, nx) = +30 degrees. Diffuse polarisation lies in
    # the plane of incidence, so AoLP must read 30 — not 150 — and the specular
    # model 120. sfpolar and specularity are separate code.
    phi, th = math.radians(30.0), math.radians(40.0)
    n = np.array([math.sin(th) * math.cos(phi), math.sin(th) * math.sin(phi), math.cos(th)])
    N = np.broadcast_to(n, (5, 5, 3)).copy()
    diff = sfpolar.sfp_render(N, specular_radiance=0.0, diffuse_radiance=1.0)
    spec = sfpolar.sfp_render(N)
    assert np.abs(sp.polarization_stokes_map(diff)["aolp_deg"] - 30.0).max() <= 1e-9
    assert np.abs(sp.polarization_stokes_map(spec)["aolp_deg"] - 120.0).max() <= 1e-9


def _screen_rotation_sign(jones_vec):
    """+1 if the field turns counter-clockwise on a displayed image (y down), else -1."""
    w = np.linspace(0.0, 2 * np.pi, 400, endpoint=False)
    E = np.real(np.asarray(jones_vec)[:, None] * np.exp(-1j * w))     # (2, T)
    x, y_down = E[0], E[1]
    y_up = -y_down                                                        # screen up
    area = np.sum(x * np.roll(y_up, -1) - np.roll(x, -1) * y_up)         # shoelace
    return 1 if area > 0 else -1


def test_s3_positive_is_counter_clockwise_on_the_displayed_image():
    v = np.array([1.0, -1j]) / math.sqrt(2.0)
    s = optics.stokes_from_jones(v)
    assert s[3] == pytest.approx(1.0) and _screen_rotation_sign(v) == +1
    assert optics.stokes_analyze(s)["handedness"] == "right"           # label kept
    for ang, sign in ((45.0, +1), (-45.0, -1)):
        out = optics.jones_apply(optics.jones_element("quarter_wave", ang), [1.0, 0.0])
        s3 = optics.stokes_from_jones(out)[3]
        assert np.sign(s3) == sign == _screen_rotation_sign(out)
        # the Mueller path agrees on the sign
        assert np.sign((optics.mueller_element("quarter_wave", ang) @ [1, 1, 0, 0])[3]) == sign


# --------------------------------------------------------------------------- #
# registration                                                                  #
# --------------------------------------------------------------------------- #
def test_new_ops_are_registered_and_callable_through_the_registries():
    assert opsspecular.info("polarization_stokes_map")["out"] == "table"
    assert opsoptics.info("mueller_partial_polarizer")["out"] == "matrix"
    sweep = opsspecular.call("polarization_render", np.full((4, 4), 0.4), np.full((4, 4), 0.2))
    r = opsspecular.call("polarization_stokes_map", sweep)
    assert isinstance(r, dict) and r["dolp"].shape == (4, 4)
    m = opsoptics.get("mueller_partial_polarizer")()
    assert m.shape == (4, 4)
    assert "polarization_stokes_map" in sp.__all__ and "mueller_partial_polarizer" in optics.__all__

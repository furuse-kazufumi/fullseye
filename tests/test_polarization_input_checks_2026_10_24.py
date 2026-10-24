"""Input checks of the polarisation family found by the post-merge review of PR #132.

Each test reproduces one finding as it was reported (it fails on the code
before this change) and pins the fix next to a legitimate input that must
still pass, so the fix cannot be "refuse everything".
"""
import math
import warnings

import numpy as np
import pytest

import optics as O
import specularity as S

DOFP = (0.0, 45.0, 90.0, 135.0)


def _px(frames, angles=DOFP, **kw):
    """A one-pixel sweep through polarization_stokes_map."""
    I = np.asarray(frames, dtype=np.float64).reshape(len(frames), 1, 1)
    return S.polarization_stokes_map(I, angles, **kw)


# --------------------------------------------------------------------------- #
# 3. negative frame values                                                     #
# --------------------------------------------------------------------------- #
def test_negative_frame_is_refused_even_when_the_fitted_minimum_is_positive():
    # The fitted minimum of [1, 1, 1.5, -0.1] is positive, so the old check
    # passed it and returned DoLP 0.711 / AoLP 57.2 from a negative radiance.
    with pytest.raises(ValueError, match="negative"):
        _px([1.0, 1.0, 1.5, -0.1])


@pytest.mark.parametrize("op", [S.polarization_separate, S.polarization_dolp_map,
                                S.polarization_stokes, S.polarization_analyze,
                                S.polarization_stokes_map])
def test_negative_frame_refused_by_every_entry_point(op):
    I = np.array([1.0, 1.0, 1.5, -0.1]).reshape(4, 1, 1)
    with pytest.raises(ValueError, match="negative"):
        op(I, DOFP)


def test_noise_level_negative_frames_pass_the_floor():
    # Dark-frame-subtracted data dips slightly below zero; within the floor
    # (2 % of the stack's largest magnitude) it is noise, not an error.
    # [1, 1, 1.5, -0.01] fits a positive minimum, and -0.01 is inside the
    # floor (-0.03 for a stack whose peak is 1.5).
    r = _px([1.0, 1.0, 1.5, -0.01])
    assert r["s0"][0, 0] > 0.0


def test_negative_frames_count_toward_max_violation_frac():
    rng = np.random.default_rng(0)
    I = rng.uniform(0.4, 0.6, size=(4, 10, 10))
    I[3, 0, 0] = -0.1                         # 1 of 100 pixels
    with pytest.raises(ValueError, match="1 of 100"):
        S.polarization_stokes_map(I, DOFP)
    r = S.polarization_stokes_map(I, DOFP, max_violation_frac=0.01)
    assert r["s0"].shape == (10, 10)


# --------------------------------------------------------------------------- #
# 4. conditioning of the analyser design / radians passed as degrees           #
# --------------------------------------------------------------------------- #
def test_angles_in_radians_are_refused_with_a_degrees_message():
    with pytest.raises(ValueError, match="degrees"):
        _px([1.0, 0.5, 0.0, 0.5], (0.0, math.pi / 4, math.pi / 2, 3 * math.pi / 4))


def test_radians_check_also_guards_the_forward_model():
    with pytest.raises(ValueError, match="degrees"):
        S.polarization_render(np.ones((2, 2)), np.ones((2, 2)),
                              (0.0, math.pi / 3, 2 * math.pi / 3))


def test_radians_check_catches_a_well_conditioned_radian_triple():
    # (0, pi, 2 pi) read as degrees has condition number 704 — under the cap —
    # so only the radians check stops it.
    with pytest.raises(ValueError, match="degrees"):
        _px([1.0, 0.6, 0.2], (0.0, math.pi, 2 * math.pi))


def test_ill_conditioned_design_is_refused():
    # 0/5/10 degrees: condition number 276 — allowed; 0/1/2 degrees: ~7e3.
    _px([1.0, 0.9, 0.8], (180.0, 185.0, 190.0))
    with pytest.raises(ValueError, match="condition number"):
        _px([1.0, 0.99, 0.98], (180.0, 181.0, 182.0))


@pytest.mark.parametrize("angles", [DOFP, (0.0, 60.0, 120.0), (0.0, 30.0, 90.0, 135.0),
                                    (0.0, 20.0, 45.0, 90.0, 160.0), (0.0, 10.0, 20.0),
                                    (-45.0, 0.0, 45.0), (10.0, 55.0, 100.0)])
def test_legitimate_designs_still_pass(angles):
    t = np.radians(np.asarray(angles))
    frames = 0.5 * (1.0 + 0.3 * np.cos(2 * (t - 0.4)))
    r = _px(frames, angles)
    assert r["dolp"][0, 0] == pytest.approx(0.3, abs=1e-9)


def test_tiny_sweep_escapes_the_radians_check_by_a_half_turn():
    # Angles are taken modulo 180, so a genuine few-degree sweep can be
    # written 180 + a; the docstring says so, and that is what passes.
    with pytest.raises(ValueError, match="degrees"):
        _px([1.0, 0.9, 0.8], (0.0, 5.0, 6.0))
    _px([1.0, 0.9, 0.8], (180.0, 185.0, 190.0))


# --------------------------------------------------------------------------- #
# 5. handedness / azimuth / ellipticity from rounding dust                     #
# --------------------------------------------------------------------------- #
def test_rounding_dust_s3_is_linear():
    s = O.mueller_element("half_wave", 22.5) @ np.array([1.0, 1.0, 0.0, 0.0])
    assert s[3] != 0.0                         # the dust is really there
    r = O.stokes_analyze(s)
    assert r["handedness"] == "linear"
    assert r["azimuth_deg"] == pytest.approx(45.0)


def test_rounding_dust_linear_part_has_no_azimuth():
    s = O.mueller_element("quarter_wave", 45.0) @ np.array([1.0, 1.0, 0.0, 0.0])
    assert np.hypot(s[1], s[2]) != 0.0         # dust, ~1e-16
    r = O.stokes_analyze(s)
    assert r["azimuth_deg"] is None
    assert r["handedness"] in ("right", "left")


def test_genuine_small_circular_part_keeps_its_handedness():
    r = O.stokes_analyze([1.0, 0.0, 0.0, 1e-9])
    assert r["handedness"] == "right"
    r = O.stokes_analyze([1.0, 0.0, 0.0, -1e-9])
    assert r["handedness"] == "left"


def test_floor_is_relative_to_s0():
    # The same S3 is dust at S0 = 1e6 and a real circular part at S0 = 1e-6.
    assert O.stokes_analyze([1e6, 1e6 - 1e-6, 0.0, 1e-7])["handedness"] == "linear"
    assert O.stokes_analyze([1e-6, 0.0, 0.0, 1e-7])["handedness"] == "right"


def test_azimuth_stays_below_180_for_a_tiny_negative_s2():
    # Sibling found while fixing 5: 0.5*atan2(-1e-17, 1) % 180 rounds to 180.0,
    # outside the documented [0, 180).
    assert O.stokes_analyze([1.0, 1.0, -1e-17, 0.0])["azimuth_deg"] == 0.0


def test_dust_polarised_part_has_no_ellipse():
    r = O.stokes_analyze([1.0, 1e-17, 0.0, 1e-17])
    assert r["ellipticity_deg"] is None
    assert r["azimuth_deg"] is None
    assert r["handedness"] == "linear"


# --------------------------------------------------------------------------- #
# 6. inconsistent DoFP sweeps: a residual map                                  #
# --------------------------------------------------------------------------- #
def test_review_example_1133_is_a_consistent_sweep():
    # The review cited (1, 1, 3, 3) as I0+I90 != I45+I135, but in 0/45/90/135
    # order I0+I90 = 1+3 = I45+I135 = 1+3: it is an exact Malus sweep, so its
    # residual is 0 and DoLP 0.707 is the right answer.
    r = _px([1.0, 1.0, 3.0, 3.0])
    assert r["residual"][0, 0] == pytest.approx(0.0, abs=1e-15)
    assert r["dolp"][0, 0] == pytest.approx(math.sqrt(0.5))


def test_inconsistent_dofp_sweep_shows_in_the_residual():
    # I0+I90 = 2, I45+I135 = 4: no analyser sweep produces this. For four
    # DoFP angles the RMS residual is |I0 + I90 - I45 - I135| / 4.
    r = _px([1.0, 3.0, 1.0, 1.0])
    assert r["residual"][0, 0] == pytest.approx(0.5, rel=1e-12)


def test_residual_is_zero_for_three_angles_and_keys_are_kept():
    r = _px([1.0, 0.5, 0.25], (0.0, 60.0, 120.0))
    assert r["residual"][0, 0] == pytest.approx(0.0, abs=1e-15)
    assert set(r) == {"s0", "s1", "s2", "dolp", "aolp_deg", "lit",
                      "aolp_defined", "residual"}


def test_residual_matches_a_direct_lstsq_on_a_field():
    rng = np.random.default_rng(3)
    ang = (0.0, 30.0, 70.0, 110.0, 150.0)
    I = rng.uniform(0.4, 0.6, size=(5, 6, 7))
    r = S.polarization_stokes_map(I, ang)
    t = np.radians(2 * np.asarray(ang))
    M = np.stack([np.ones_like(t), np.cos(t), np.sin(t)], 1)
    a = np.linalg.lstsq(M, I.reshape(5, -1), rcond=None)[0]
    want = np.sqrt(np.mean((M @ a - I.reshape(5, -1)) ** 2, axis=0)).reshape(6, 7)
    assert np.abs(r["residual"] - want).max() < 1e-14
    assert r["residual"].shape == (6, 7)


# --------------------------------------------------------------------------- #
# 7. empty images                                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("shape", [(4, 0, 3), (4, 3, 0), (4, 0, 0)])
def test_empty_stack_is_refused_without_a_warning(shape):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(ValueError, match="no pixels"):
            S.polarization_stokes_map(np.ones(shape), DOFP)
        with pytest.raises(ValueError, match="no pixels"):
            S.polarization_stokes(np.ones(shape), DOFP)


# --------------------------------------------------------------------------- #
# 9. error messages that round the offending value onto the boundary           #
# --------------------------------------------------------------------------- #
def test_transmission_message_shows_the_real_value():
    with pytest.raises(ValueError, match=r"got 1\.0000001"):
        O.mueller_partial_polarizer(0.0, 10.0, 1.0000001)


def test_extinction_ratio_message_shows_the_real_value():
    with pytest.raises(ValueError, match=r"got 0\.9999999"):
        O.mueller_partial_polarizer(0.0, 0.9999999)


@pytest.mark.parametrize("op", [S.polarization_separate, S.polarization_dolp_map,
                                S.polarization_stokes, S.polarization_analyze,
                                S.polarization_stokes_map])
def test_max_violation_frac_message_shows_the_real_value(op):
    with pytest.raises(ValueError, match=r"got 1\.0000001"):
        op(np.ones((4, 2, 2)), DOFP, max_violation_frac=1.0000001)


def test_unit_interval_and_roughness_messages_show_the_real_value():
    n = np.zeros((2, 2, 3)); n[..., 2] = 1.0
    with pytest.raises(ValueError, match=r"got 1\.0000001"):
        S.brdf_microfacet(n, [0, 0, 1], [0, 0, 1], roughness=1.0000001)
    with pytest.raises(ValueError, match=r"got 1\.0000001"):
        S.brdf_microfacet(n, [0, 0, 1], [0, 0, 1], roughness=0.5, f0=1.0000001)

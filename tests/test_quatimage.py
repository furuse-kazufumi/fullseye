# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Ground-truth tests for quatimage — quaternion images, Riesz/monogenic, QFT.

This subject has an unusually strong ground truth and the tests spend all of it.
Nothing here is checked against a tolerance chosen to pass:

* the Riesz transform of a grid-exact grating is known **in closed form**
  (``R1 = (u0/|w|) sin``), so it is checked as an equality;
* the quaternion Fourier transform is checked against a **brute-force O(N^2)
  quaternion DFT written straight from the definition**, for three transform
  axes and both sides — the fast symplectic path is never allowed to be its own
  reference;
* the internal ``nu`` of that decomposition must not affect the answer, and an
  independent implementation with a different ``nu`` is compared against it;
* colour rotation is checked against per-pixel ``pose_quat.quat_rotate_point_3d``
  and the projection against ``specularity.specular_free_transform``;
* the displacement estimator is compared head to head with
  ``motionmag.phase_displacement`` on the same clips — **including the case the
  Riesz route loses**, which is asserted as a loss so that a future "improvement"
  that silently removes it has to change this file.

An adversarial block then attacks the operators the way the repository's
discipline asks: not for exceptions, but for **quiet wrong numbers** — the side
of a non-commutative product, a colour quaternion read as a monogenic signal, a
zero rotor that becomes the identity, string and bool scalars, and small
arguments that ask for large allocations.
"""
import numpy as np
import pytest

import motionmag as mm
import opsquat
import pose_quat
import quatimage as qi
import specularity

# --------------------------------------------------------------------------- #
# Constructed inputs with a closed-form answer                                 #
# --------------------------------------------------------------------------- #
H = W = 64
T = 64
FPS = 32.0
FREQ = 4.0                      # bin-centred: FREQ * T / FPS == 8, an integer
BAND = (3.0, 5.0)

#: Grid-exact grating frequencies covering 0..159.4 degrees. Every one of these
#: lands on a DFT bin, so the closed forms below are exact, not approximate.
ORIENTATIONS = [(8, 0), (8, 3), (6, 6), (3, 8), (0, 8), (-3, 8), (-6, 6), (-8, 3)]


def grating(cx, cy, phase=0.0, contrast=1.0, h=H, w=W):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    return contrast * np.cos(2.0 * np.pi * (cx * xx / w + cy * yy / h) + phase)


def truth(amplitude, t=T):
    """The displacement the synthetics below apply, in closed form."""
    return amplitude * np.sin(2.0 * np.pi * FREQ * np.arange(t) / FPS)


def one_grating_clip(amplitude, cyc_x=8, cyc_y=0, direction_deg=0.0,
                     sigma=0.0, seed=1, h=H, w=W, t=T):
    """A clip carrying **one** moving component, translated by an exact Fourier
    phase ramp — so the displacement is ground truth to machine precision.

    ``motionmag.synthesize_translation`` deliberately puts *two* gratings in the
    frame (one per axis); that is the right default for a steerable bank and the
    wrong one for a radial bank, which is exactly the difference these tests
    measure. This helper isolates the single-component case."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    base = 0.5 + 0.2 * np.cos(2.0 * np.pi * (cyc_x * xx / w + cyc_y * yy / h))
    fv = np.fft.fftfreq(h)[:, None]
    fu = np.fft.fftfreq(w)[None, :]
    spec = np.fft.fft2(base)
    disp = truth(amplitude, t)
    ux, uy = np.cos(np.radians(direction_deg)), np.sin(np.radians(direction_deg))
    out = np.stack([np.real(np.fft.ifft2(spec * np.exp(
        -2j * np.pi * (fu * d * ux + fv * d * uy)))) for d in disp])
    if sigma > 0.0:
        out = out + np.random.default_rng(seed).normal(0.0, sigma, out.shape)
    return out


def gain_of(series, amplitude, ux=1.0, uy=0.0):
    """Least-squares gain of a recovered ``(T, 2)`` waveform against the truth."""
    tr = truth(amplitude)
    got = series[:, 0] * ux + series[:, 1] * uy
    return float(got @ tr / (tr @ tr))


def colour_image(seed=0, h=32, w=32):
    return np.random.default_rng(seed).random((h, w, 3))


# --------------------------------------------------------------------------- #
# Riesz transform / monogenic signal: closed form                              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("cyc", ORIENTATIONS)
def test_riesz_transform_matches_the_closed_form(cyc):
    """R1 = (u0/|w0|) sin, R2 = (v0/|w0|) sin — exactly, at every orientation."""
    cx, cy = cyc
    q = qi.riesz_transform(grating(cx, cy))
    u0, v0 = cx / W, cy / H
    r = np.hypot(u0, v0)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    s = np.sin(2.0 * np.pi * (cx * xx / W + cy * yy / H))
    assert np.abs(q[..., 1] - (u0 / r) * s).max() < 1e-14
    assert np.abs(q[..., 2] - (v0 / r) * s).max() < 1e-14
    # the scalar and k components are identically zero: this is the Riesz
    # transform, not the monogenic signal
    assert np.array_equal(q[..., 0], np.zeros((H, W)))
    assert np.array_equal(q[..., 3], np.zeros((H, W)))


def test_monogenic_amplitude_phase_orientation_are_exact():
    """A unit-contrast grating at the band centre: amplitude 1, phase and
    orientation the grating's own, all to rounding."""
    g = grating(8, 0, phase=0.7)
    q = qi.monogenic_signal(g, wavelength_px=8.0)
    amp = qi.monogenic_amplitude(q)
    assert abs(amp.mean() - 1.0) < 1e-14
    assert amp.max() - amp.min() < 1e-14
    _yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    psi = np.mod(2.0 * np.pi * (8 * xx / W) + 0.7, 2.0 * np.pi)
    folded = np.where(psi > np.pi, 2.0 * np.pi - psi, psi)   # monogenic phase in [0, pi]
    assert np.abs(qi.monogenic_phase(q) - folded).max() < 1e-13
    assert np.abs(qi.monogenic_orientation(q)).max() == 0.0


@pytest.mark.parametrize("cyc", ORIENTATIONS)
def test_monogenic_orientation_is_continuous_not_quantised(cyc):
    """Every orientation is recovered exactly, obliques included — where the
    Riesz vector is alive. Masking on the *amplitude* would not be enough; see
    the degeneracy test below."""
    cx, cy = cyc
    r = np.hypot(cx / W, cy / H)
    q = qi.monogenic_signal(grating(cx, cy), wavelength_px=1.0 / r)
    th = qi.monogenic_orientation(q)
    rmag = np.hypot(q[..., 1], q[..., 2])
    live = rmag > 0.1 * rmag.max()
    true_th = np.mod(np.arctan2(cy / H, cx / W), np.pi)
    err = np.abs(np.mod(th - true_th + 0.5 * np.pi, np.pi) - 0.5 * np.pi)
    assert err[live].max() < 1e-13


def test_monogenic_amplitude_is_isotropic():
    """The amplitude of a unit grating is 1 at every orientation — that is the
    property an oriented filter bank does not have."""
    lo, hi = np.inf, -np.inf
    for cx, cy in ORIENTATIONS:
        r = np.hypot(cx / W, cy / H)
        amp = qi.monogenic_amplitude(
            qi.monogenic_signal(grating(cx, cy), wavelength_px=1.0 / r))
        lo, hi = min(lo, amp.min()), max(hi, amp.max())
    assert hi - lo < 1e-13


def test_orientation_dies_where_the_riesz_vector_does_not_where_amplitude_does():
    """The documented trap: at an even-symmetric point the amplitude is at full
    strength and the orientation is meaningless. Masking on the amplitude is the
    wrong mask, and this test is what stops the docstring from claiming it."""
    r = np.hypot(6 / W, 6 / H)
    q = qi.monogenic_signal(grating(6, 6), wavelength_px=1.0 / r)
    th = qi.monogenic_orientation(q)
    rmag = np.hypot(q[..., 1], q[..., 2])
    amp = qi.monogenic_amplitude(q)
    true_th = np.mod(np.arctan2(6 / H, 6 / W), np.pi)
    err = np.abs(np.mod(th - true_th + 0.5 * np.pi, np.pi) - 0.5 * np.pi)
    worst = int(err.argmax())
    assert err.ravel()[worst] > 0.1                     # badly wrong ...
    assert amp.ravel()[worst] > 0.99                    # ... where amplitude is full
    assert rmag.ravel()[worst] < 1e-12                  # ... and |R| is the tell


def test_riesz_nyquist_residue_is_zero_after_band_pass():
    """``np.real`` discards a genuine residue on a broadband image (16 % on a
    random one) and exactly nothing on a band-passed one, which is why the
    monogenic signal band-passes first."""
    img = np.random.default_rng(0).random((H, W))
    H1, _H2, r = qi._riesz_kernels(H, W)
    F = np.fft.fft2(img)
    raw = np.fft.ifft2(F * H1)
    assert np.abs(np.imag(raw)).sum() / np.abs(np.real(raw)).sum() > 1e-2
    x = np.where(r > 0, np.log2(np.where(r > 0, r, 1.0) / (1.0 / 8.0)), 0.0)
    G = np.where((r > 0) & (np.abs(x) <= 1.0), np.cos(0.5 * np.pi * x), 0.0)
    banded = np.fft.ifft2(F * G * H1)
    assert np.abs(np.imag(banded)).max() < 1e-15


# --------------------------------------------------------------------------- #
# quaternion algebra                                                           #
# --------------------------------------------------------------------------- #
def test_hamilton_product_agrees_with_pose_quat():
    """The vectorised product is the same algebra pose_quat implements."""
    rng = np.random.default_rng(4)
    a, b = rng.standard_normal((5, 5, 4)), rng.standard_normal((5, 5, 4))
    ref = np.stack([[pose_quat.quat_compose(a[i, j], b[i, j]) for j in range(5)]
                    for i in range(5)])
    assert np.abs(qi._hamilton(a, b) - ref).max() == 0.0


def test_rgb_round_trip_and_conjugate_involution():
    rgb = colour_image()
    q = qi.rgb_to_quaternion(rgb)
    assert np.array_equal(q[..., 0], np.zeros(rgb.shape[:2]))
    assert np.array_equal(qi.quaternion_to_rgb(q), rgb)
    assert np.array_equal(qi.quat_conjugate_image(qi.quat_conjugate_image(q)), q)
    ref = np.stack([[pose_quat.quat_conjugate(q[i, j]) for j in range(q.shape[1])]
                    for i in range(q.shape[0])])
    assert np.array_equal(qi.quat_conjugate_image(q), ref)


def test_normalize_gives_unit_modulus():
    rng = np.random.default_rng(5)
    q = rng.standard_normal((8, 8, 4))
    n = qi.quat_norm(qi.quat_normalize_image(q))
    assert np.abs(n - 1.0).max() < 1e-15


# --------------------------------------------------------------------------- #
# colour rotation: exact, and exactly what a matrix does                       #
# --------------------------------------------------------------------------- #
def test_color_rotate_is_the_quaternion_sandwich():
    rgb = colour_image(seed=2, h=8, w=8)
    q = qi.rgb_to_quaternion(rgb)
    axis = np.array([0.3, -0.5, 0.81])
    axis /= np.linalg.norm(axis)
    ang = 0.9
    out = qi.quat_color_rotate(q, axis, ang)
    rot = pose_quat.axis_angle_to_quat(axis[0], axis[1], axis[2], ang)
    ref = np.stack([[pose_quat.quat_rotate_point_3d(rot, *rgb[i, j])
                     for j in range(8)] for i in range(8)])
    # HISTORY, kept deliberately. Until 2026-09-01 this assertion had to be
    # bracketed from *below* as well (> 1e-14), because the error had a floor at
    # 1e-12 that was not rounding: pose_quat normalised with `norm + 1e-12`, so
    # even a perfectly unit rotor came back scaled by 1/(1 + 1e-12) and the
    # matrix built from it was short of orthogonal by 1.4e-12. The effect was
    # doubled because quat_to_hom_mat3d calls quat_normalize internally, which is
    # why reproducing only the outer expression does not reproduce the number.
    # pose_quat now divides exactly and fail-closes on zero length, so the floor
    # is gone and the bound is tightened to machine precision. Measured after the
    # fix: 4.44e-16 here, 2.22e-16 for the round trip.
    assert np.abs(out[..., 1:] - ref).max() < 1e-14
    back = qi.quat_color_rotate(out, axis, -ang)
    assert np.abs(back - q).max() < 1e-14


def test_color_rotate_preserves_the_colour_magnitude():
    q = qi.rgb_to_quaternion(colour_image(seed=6, h=16, w=16))
    out = qi.quat_color_rotate(q, (0.0, 0.0, 1.0), 0.77)
    assert np.abs(qi.quat_norm(out) - qi.quat_norm(q)).max() < 1e-12


def test_color_rotate_matches_a_3x3_matrix_exactly():
    """The honest ceiling of the quaternion claim: SO(3) is SO(3)."""
    rgb = colour_image(seed=7, h=16, w=16)
    axis = np.array([0.0, 0.0, 1.0])
    ang = np.radians(30.0)
    c, s = np.cos(ang), np.sin(ang)
    R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    out = qi.quat_color_rotate(qi.rgb_to_quaternion(rgb), axis, ang)
    assert np.abs(out[..., 1:] - rgb @ R.T).max() < 1e-11


def test_a_channelwise_pipeline_cannot_rotate_colour():
    """The comparison that *is* decisive. A per-channel filter multiplies each
    channel by a number; it cannot create green out of a channel that is zero."""
    rgb = np.zeros((4, 4, 3))
    rgb[..., 0] = 1.0                                   # pure red
    out = qi.quat_color_rotate(qi.rgb_to_quaternion(rgb), (0.0, 0.0, 1.0),
                               np.radians(90.0))
    assert np.abs(out[..., 1:] - np.array([0.0, 1.0, 0.0])).max() < 1e-11
    # any per-channel gain (real or complex, any value) leaves green at zero
    for gain in (0.0, 1.0, -3.5, 1e6):
        assert (rgb[..., 1] * gain == 0.0).all()


# --------------------------------------------------------------------------- #
# colour-selective filtering                                                   #
# --------------------------------------------------------------------------- #
def test_color_filter_removes_the_direction_exactly():
    rgb = colour_image(seed=8)
    q = qi.rgb_to_quaternion(rgb)
    g = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)
    rem = qi.quat_color_filter(q, g, "remove")
    keep = qi.quat_color_filter(q, g, "keep")
    assert np.abs(rem[..., 1:] @ g).max() < 1e-14
    assert np.array_equal(rem + keep, q)                 # exact decomposition
    # by construction, not by luck: the remove branch delegates to specularity
    assert np.array_equal(rem[..., 1:],
                          specularity.specular_free_transform(rgb, g))


def test_the_grey_axis_projection_is_not_diagonal():
    """Quantifies the channelwise impossibility as a number."""
    g = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)
    P = np.eye(3) - np.outer(g, g)
    D = np.diag(np.diag(P))                              # best diagonal in Frobenius
    assert np.linalg.norm(P - D, 2) > 0.66
    red = np.array([1.0, 0.0, 0.0])
    assert np.linalg.norm(P @ red - D @ red) == pytest.approx(np.sqrt(2.0) / 3.0)


# --------------------------------------------------------------------------- #
# the quaternion Fourier transform                                             #
# --------------------------------------------------------------------------- #
def _brute_qft(q, side, mu):
    """O(N^2) quaternion DFT written straight from the definition.

    The fast path must never be its own reference. This is slow on purpose and
    is only ever called on a 4x4 image."""
    h, w, _ = q.shape
    mu = np.asarray(mu, np.float64)
    mu = mu / np.linalg.norm(mu)
    out = np.zeros((h, w, 4))
    for v in range(h):
        for u in range(w):
            acc = np.zeros(4)
            for y in range(h):
                for x in range(w):
                    th = 2.0 * np.pi * (u * x / w + v * y / h)
                    E = np.concatenate([[np.cos(-th)], np.sin(-th) * mu])
                    f = q[y, x]
                    acc += (pose_quat.quat_compose(E, f) if side == "left"
                            else pose_quat.quat_compose(f, E))
            out[v, u] = acc
    return out


@pytest.mark.parametrize("mu", [(1, 1, 1), (0, 0, 1), (1, -2, 0.5)])
@pytest.mark.parametrize("side", ["left", "right"])
def test_qft_matches_the_brute_force_definition(mu, side):
    q = np.random.default_rng(7).standard_normal((4, 4, 4))
    fast = np.fft.ifftshift(qi.qft2(q, side, mu), axes=(0, 1))
    assert np.abs(fast - _brute_qft(q, side, mu)).max() < 1e-13


@pytest.mark.parametrize("side", ["left", "right"])
def test_qft_round_trip_is_exact(side):
    q = np.random.default_rng(9).standard_normal((32, 32, 4))
    assert np.abs(qi.iqft2(qi.qft2(q, side), side) - q).max() < 1e-14


@pytest.mark.parametrize("side", ["left", "right"])
def test_qft_does_not_depend_on_the_internal_nu(side):
    """``nu`` is an implementation basis, not a parameter. Rotating it must
    cancel exactly, and an independent implementation proves it does."""
    q = np.random.default_rng(11).standard_normal((16, 16, 4))
    m = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)

    def with_nu(n):
        n = np.asarray(n, np.float64)
        n = n - (n @ m) * m
        n /= np.linalg.norm(n)
        lam = np.cross(m, n)
        v = q[..., 1:]
        A = q[..., 0] + 1j * (v @ m)
        B = (v @ n) + 1j * (v @ lam)
        FA = np.fft.fft2(A)
        FB = (np.fft.fft2(B) if side == "left"
              else np.conj(np.fft.fft2(np.conj(B))))
        return qi._from_symplectic(FA, FB, m, n, lam)

    a, b = with_nu([1.0, -1.0, 0.0]), with_nu([1.0, 0.0, -1.0])
    assert np.abs(a - b).max() < 1e-13
    assert np.abs(a - np.fft.ifftshift(qi.qft2(q, side, m), axes=(0, 1))).max() < 1e-13


def test_left_and_right_qft_are_different_answers_neither_of_which_raises():
    """The reason ``side`` has no default. Both are finite, both look right."""
    q = qi.rgb_to_quaternion(colour_image(seed=12))
    fl, fr = qi.qft2(q, "left"), qi.qft2(q, "right")
    assert np.isfinite(fl).all() and np.isfinite(fr).all()
    gap = np.abs(fl - fr).max()
    assert gap > 1.0                                    # measured 33.35
    # and mixing the sides across a round trip is a different picture entirely
    cross = qi.iqft2(qi.qft2(q, "left"), "right")
    assert np.isfinite(cross).all()
    assert np.abs(cross - q).max() > 0.5 * np.abs(q).max()


def test_qft_is_a_recombination_of_channelwise_ffts():
    """The honest accounting: the QFT contains no information three per-channel
    FFTs do not. If this ever fails, the module's central honesty claim is
    wrong and the docstring must change."""
    q = qi.rgb_to_quaternion(colour_image(seed=13))
    m, n, lam = qi._mu_basis(None, "test")
    v = q[..., 1:]
    ch = [np.fft.fft2(v[..., i]) for i in range(3)]
    FA = 1j * sum(m[i] * ch[i] for i in range(3))
    FB = sum(n[i] * ch[i] for i in range(3)) + 1j * sum(lam[i] * ch[i] for i in range(3))
    rebuilt = qi._from_symplectic(np.fft.fftshift(FA), np.fft.fftshift(FB), m, n, lam)
    assert np.abs(rebuilt - qi.qft2(q, "left")).max() < 1e-11


# --------------------------------------------------------------------------- #
# quaternion correlation                                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("deg", [0.0, 30.0, 90.0])
def test_correlation_recovers_the_colour_rotation(deg):
    """With colours in the plane orthogonal to the axis the reading is exact."""
    patch = np.random.default_rng(14).random((32, 32, 3))
    patch[..., 2] = 0.0
    a = qi.rgb_to_quaternion(patch)
    b = qi.quat_color_rotate(a, (0.0, 0.0, 1.0), np.radians(deg))
    c0 = qi.quat_correlate(a, a)[0, 0]
    c1 = qi.quat_correlate(a, b)[0, 0]
    assert c1[0] / c0[0] == pytest.approx(np.cos(np.radians(deg)), abs=1e-9)
    vec = c1[1:]
    assert np.degrees(np.arctan2(np.linalg.norm(vec), c1[0])) == pytest.approx(deg, abs=1e-6)
    if deg > 0.0:
        # the direction is the *negative* axis: the conjugate is on the left
        assert np.abs(vec / np.linalg.norm(vec) - np.array([0.0, 0.0, -1.0])).max() < 1e-9


def test_correlation_scalar_part_is_the_channelwise_sum():
    """What the channelwise baseline gets, and all it gets."""
    a = qi.rgb_to_quaternion(colour_image(seed=15))
    b = qi.rgb_to_quaternion(colour_image(seed=16))
    chan = sum(np.real(np.fft.ifft2(np.conj(np.fft.fft2(a[..., i]))
                                    * np.fft.fft2(b[..., i]))) for i in (1, 2, 3))
    assert np.abs(qi.quat_correlate(a, b)[..., 0] - chan).max() < 1e-12


def test_correlation_angle_is_biased_when_colours_leave_the_plane():
    """The precondition is real and the failure is silent — asserted so that the
    docstring's warning cannot quietly become false."""
    a = qi.rgb_to_quaternion(np.random.default_rng(17).random((32, 32, 3)))
    b = qi.quat_color_rotate(a, (0.0, 0.0, 1.0), np.radians(30.0))
    c = qi.quat_correlate(a, b)[0, 0]
    got = np.degrees(np.arctan2(np.linalg.norm(c[1:]), c[0]))
    assert abs(got - 30.0) > 5.0                        # measured 22.5 deg
    assert np.isfinite(got)                             # ... and nothing complains


# --------------------------------------------------------------------------- #
# Riesz motion: head to head with the complex steerable route                  #
# --------------------------------------------------------------------------- #
def test_alpha_one_is_the_identity():
    v = one_grating_clip(0.2)
    out = qi.riesz_motion_magnify(v, 1.0, *BAND, FPS)["video"]
    assert np.abs(out - v).max() < 1e-14


@pytest.mark.parametrize("alpha", [0.0, 2.0, 4.0, -1.0, 20.0])
def test_magnified_displacement_is_alpha_times_d(alpha):
    """Measured with the *independent* steerable estimator, so the magnifier is
    not marking its own homework."""
    v = one_grating_clip(0.1)
    out = qi.riesz_motion_magnify(v, alpha, *BAND, FPS)["video"]
    assert gain_of(mm.displacement_series(out, *BAND, FPS), 0.1) == pytest.approx(alpha, abs=1e-9)


@pytest.mark.parametrize("amp", [0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 3.0])
def test_displacement_is_exact_when_one_component_holds_the_band(amp):
    v = one_grating_clip(amp)
    assert gain_of(qi.riesz_displacement_series(v, *BAND, FPS), amp) == pytest.approx(1.0, abs=1e-12)


def test_the_cliff_is_the_bessel_zero_and_both_routes_hit_it():
    """A = 2.4048/(2*pi/8) = 3.0619 px for an 8 px grating: below it both are
    exact, above it both are broken. The Riesz route does not lift the ceiling
    because the ceiling belongs to the temporal-mean reference."""
    cliff = 2.404825557695773 / (2.0 * np.pi / 8.0)
    assert cliff == pytest.approx(3.0619, abs=1e-4)
    for amp in (3.00, 3.06):
        v = one_grating_clip(amp)
        assert gain_of(qi.riesz_displacement_series(v, *BAND, FPS), amp) == pytest.approx(1.0, abs=1e-12)
        assert gain_of(mm.displacement_series(v, *BAND, FPS), amp) == pytest.approx(1.0, abs=1e-12)
    for amp in (3.07, 4.0):
        v = one_grating_clip(amp)
        assert abs(gain_of(qi.riesz_displacement_series(v, *BAND, FPS), amp) - 1.0) > 0.5
        assert abs(gain_of(mm.displacement_series(v, *BAND, FPS), amp) - 1.0) > 0.5


@pytest.mark.parametrize("cyc", [(8, 0), (8, 3), (6, 6), (3, 8), (0, 8)])
def test_oblique_structure_costs_neither_route_anything(cyc):
    """The theoretical advantage of continuous orientation does not show up:
    the steerable bank's angular windows already interpolate exactly."""
    cx, cy = cyc
    d = np.degrees(np.arctan2(cy, cx))
    ux, uy = np.cos(np.radians(d)), np.sin(np.radians(d))
    v = one_grating_clip(0.5, cyc_x=cx, cyc_y=cy, direction_deg=d)
    assert gain_of(qi.riesz_displacement_series(v, *BAND, FPS), 0.5, ux, uy) == pytest.approx(1.0, abs=1e-12)
    assert gain_of(mm.displacement_series(v, *BAND, FPS), 0.5, ux, uy) == pytest.approx(1.0, abs=1e-12)


def test_the_riesz_route_LOSES_on_multi_orientation_texture():
    """**The loss, asserted as a loss.**

    A radial band has no orientation index, so two gratings at different
    orientations inside one octave share a band and the single-plane-wave model
    behind the monogenic signal is false. On ``synthesize_translation``'s own
    default that is a 13 % displacement error with no exception and no NaN,
    while the steerable route is exact. Separating the two components by two
    octaves restores machine precision, which identifies the cause exactly.

    This is asserted rather than merely documented so that a future change which
    silently removes the failure has to come here and say so."""
    v = mm.synthesize_translation(frames=T, amplitude_px=0.5,
                                  frequency_hz=FREQ, fps=FPS)     # lambda = (8, 16)
    riesz = gain_of(qi.riesz_displacement_series(v, *BAND, FPS), 0.5)
    steer = gain_of(mm.displacement_series(v, *BAND, FPS), 0.5)
    assert abs(steer - 1.0) < 1e-12                     # steerable: exact
    assert 0.10 < abs(riesz - 1.0) < 0.20               # Riesz: ~13 % low
    # two octaves apart -> one component per band -> both exact
    v2 = mm.synthesize_translation(frames=T, amplitude_px=0.5, frequency_hz=FREQ,
                                   fps=FPS, wavelength_px=(8.0, 32.0))
    assert gain_of(qi.riesz_displacement_series(v2, *BAND, FPS), 0.5) == pytest.approx(1.0, abs=1e-12)


def test_the_riesz_route_leaves_holes_where_the_steerable_one_does_not():
    """Second measured loss: 25 % of pixels are rank 0 because the Riesz vector
    vanishes at even-symmetric points. They are marked, not hidden."""
    v = one_grating_clip(0.5)
    r = qi.riesz_displacement(v, *BAND, FPS)["rank"]
    s = mm.phase_displacement(v, *BAND, FPS)["rank"]
    assert (r == 0).sum() > 0.2 * r.size
    assert (s == 0).sum() == 0


@pytest.mark.parametrize("sigma", [0.001, 0.01, 0.05])
def test_the_riesz_route_wins_under_noise(sigma):
    """A measured win, and the reason is structural: 4 bands admit fewer
    noise-only sub-bands to the normal equations than 19 do."""
    v = one_grating_clip(0.5, sigma=sigma)
    e_r = abs(gain_of(qi.riesz_displacement_series(v, *BAND, FPS), 0.5) - 1.0)
    e_s = abs(gain_of(mm.displacement_series(v, *BAND, FPS), 0.5) - 1.0)
    assert e_r < e_s


def test_magnification_never_improves_the_motion_snr():
    v = mm.synthesize_translation(frames=T, amplitude_px=0.2, frequency_hz=FREQ,
                                  fps=FPS, noise_sigma=0.01, seed=0)
    prev = None
    for alpha in (1.0, 2.0, 4.0, 8.0):
        r = qi.riesz_motion_magnify(v, alpha, *BAND, FPS)
        assert r["motion_snr_change_db"] <= 1e-9        # never rises
        assert r["image_snr_change_db"] <= 1e-9         # and the image pays
        if prev is not None:
            assert r["image_snr_change_db"] < prev      # monotonically
        prev = r["image_snr_change_db"]


def test_a_motion_outside_the_band_is_not_magnified():
    v = one_grating_clip(0.2)                            # 4 Hz motion
    out = qi.riesz_motion_magnify(v, 50.0, 10.0, 12.0, FPS)["video"]
    assert gain_of(mm.displacement_series(v, *BAND, FPS), 0.2) == pytest.approx(1.0, abs=1e-9)
    assert gain_of(mm.displacement_series(out, *BAND, FPS), 0.2) == pytest.approx(1.0, abs=1e-6)


# --------------------------------------------------------------------------- #
# ADVERSARIAL: not exceptions, quiet wrong numbers                             #
# --------------------------------------------------------------------------- #
def test_a_colour_quaternion_is_refused_as_a_monogenic_signal():
    """The headline confusion. Both are (H, W, 4) float64, so a shape check
    cannot separate them, and without the k-component guard a colour image
    returns a smooth, plausible orientation map of nothing."""
    colour = qi.rgb_to_quaternion(colour_image(seed=20))
    for fn in (qi.monogenic_amplitude, qi.monogenic_phase, qi.monogenic_orientation):
        with pytest.raises(ValueError, match="not a monogenic signal"):
            fn(colour)
    # what it would have returned: finite, smooth, and entirely meaningless
    bogus = np.mod(np.arctan2(colour[..., 2], colour[..., 1]), np.pi)
    assert np.isfinite(bogus).all()


def test_a_monogenic_signal_is_refused_as_a_colour_image():
    """The other direction: dropping the band-pass image into oblivion and
    calling the Riesz pair 'red and green'."""
    mono = qi.monogenic_signal(np.random.default_rng(21).random((16, 16)))
    with pytest.raises(ValueError, match="not pure"):
        qi.quaternion_to_rgb(mono)
    out = qi.quaternion_to_rgb(mono, allow_scalar=True)  # opt-in is allowed
    assert out.shape == (16, 16, 3)


@pytest.mark.parametrize("fn,args", [
    (qi.qft2, ()), (qi.iqft2, ()),
])
@pytest.mark.parametrize("bad", [None, "Left", "LEFT", "l", 0, True, b"left"])
def test_side_is_required_and_matched_exactly(fn, args, bad):
    q = qi.rgb_to_quaternion(colour_image(seed=22, h=8, w=8))
    with pytest.raises(ValueError, match="side"):
        fn(q, bad, *args)


def test_side_has_no_default_anywhere():
    """A default would be a silent choice. Verified by signature, so that adding
    one later fails this test instead of quietly changing every result."""
    import inspect
    for fn in (qi.qft2, qi.iqft2, qi.quat_image_multiply):
        p = inspect.signature(fn).parameters["side"]
        assert p.default is inspect.Parameter.empty
    p = inspect.signature(qi.quat_color_filter).parameters["mode"]
    assert p.default is inspect.Parameter.empty


def test_the_two_sides_really_do_disagree():
    """If they ever agree, the required argument is pointless and this test says
    so before the API gets simplified by mistake."""
    q = np.random.default_rng(23).standard_normal((32, 32, 4))
    rot = pose_quat.axis_angle_to_quat(0.2, 0.4, 0.9, 1.1)
    L = qi.quat_image_multiply(q, rot, "left")
    R = qi.quat_image_multiply(q, rot, "right")
    assert np.abs(L - R).max() > 1.0
    assert np.isfinite(L).all() and np.isfinite(R).all()


def test_a_zero_rotation_axis_is_refused_not_turned_into_the_identity():
    """``pose_quat.axis_angle_to_quat`` normalises with ``n/(norm+1e-12)``, so a
    zero axis silently becomes a no-op — and at angle pi it becomes the identity
    for *any* axis, because the rotor is then [0,0,0,0] whose normalisation is
    zero and whose matrix is I. Both are demonstrated here on pose_quat itself
    and then shown to be blocked by quatimage."""
    assert np.allclose(pose_quat.quat_to_hom_mat3d([0.0, 0.0, 0.0, 0.0])[:3, :3],
                       np.eye(3))                        # the trap, in pose_quat
    zero_rotor = pose_quat.axis_angle_to_quat(0.0, 0.0, 0.0, 1.0)
    assert np.linalg.norm(zero_rotor) < 0.9              # not a unit rotor
    q = qi.rgb_to_quaternion(colour_image(seed=24, h=4, w=4))
    for axis in ([0.0, 0.0, 0.0], np.zeros(3), (0, 0, 0)):
        with pytest.raises(ValueError, match="zero vector"):
            qi.quat_color_rotate(q, axis, 1.0)


def test_a_180_degree_rotation_is_a_real_rotation_not_the_identity():
    """The dangerous corner of the trap above: quatimage must still perform a
    genuine pi rotation, which pose_quat's own path would collapse if the axis
    were degenerate."""
    rgb = np.zeros((4, 4, 3))
    rgb[..., 0] = 1.0
    out = qi.quat_color_rotate(qi.rgb_to_quaternion(rgb), (0.0, 0.0, 1.0), np.pi)
    assert np.abs(out[..., 1:] - np.array([-1.0, 0.0, 0.0])).max() < 1e-11


def test_a_zero_pixel_is_refused_by_normalize_not_divided_by_epsilon():
    q = np.ones((4, 4, 4))
    q[2, 3] = 0.0
    with pytest.raises(ValueError, match="row=2, col=3"):
        qi.quat_normalize_image(q)


@pytest.mark.parametrize("bad", ["4", b"4", True, np.True_, 1 + 2j, np.nan, np.inf,
                                 None, [1.0]])
def test_scalar_arguments_refuse_the_silent_coercions(bad):
    """``float("4")`` succeeds and ``True == 1``: without these branches an
    unparsed configuration value becomes an angle and a boolean becomes a gain."""
    q = qi.rgb_to_quaternion(colour_image(seed=25, h=8, w=8))
    with pytest.raises(ValueError):
        qi.quat_color_rotate(q, (0.0, 0.0, 1.0), bad)


@pytest.mark.parametrize("bad", ["remove ", "Remove", "drop", None, 0, True])
def test_mode_is_required_and_matched_exactly(bad):
    q = qi.rgb_to_quaternion(colour_image(seed=26, h=8, w=8))
    with pytest.raises(ValueError, match="mode"):
        qi.quat_color_filter(q, (1.0, 1.0, 1.0), bad)


@pytest.mark.parametrize("fn", [qi.quat_norm, qi.quat_conjugate_image,
                                qi.monogenic_amplitude])
@pytest.mark.parametrize("bad", [
    np.zeros((8, 8, 3)),                # an rgbimage: the near-miss shape
    np.zeros((8, 8)),                   # a plain image
    np.zeros((8, 8, 4, 2)),             # 4-D
    np.zeros((4, 8, 8)),                # a video-shaped array
])
def test_shape_is_never_guessed(fn, bad):
    with pytest.raises(ValueError):
        fn(bad)


@pytest.mark.parametrize("bad", [
    np.array([["1", "2"], ["3", "4"]], dtype="U1"),
    np.zeros((4, 4), dtype=bool),
    np.zeros((4, 4), dtype=np.complex128),
    np.ma.masked_array(np.zeros((4, 4)), mask=np.eye(4, dtype=bool)),
    np.full((4, 4), np.nan),
    np.full((4, 4), np.inf),
    "not an image",
])
def test_image_dtypes_refuse_the_silent_coercions(bad):
    with pytest.raises(ValueError):
        qi.riesz_transform(bad)


def test_size_caps_fire_before_the_float64_promotion():
    """A cap checked after ``asarray(x, float64)`` has already asked for the copy
    it exists to prevent (the lesson recorded in ``specularity._precheck_size``).
    ``broadcast_to`` gives a huge *shape* with no memory, so if the cap were on
    the wrong side of the conversion this test would try to allocate ~2 GB
    instead of raising."""
    huge_q = np.broadcast_to(np.zeros((1, 1, 4), np.float32), (8192, 8192, 4))
    with pytest.raises(ValueError, match="cap"):
        qi.quat_norm(huge_q)
    huge_i = np.broadcast_to(np.zeros((1, 1), np.float32), (8192, 8192))
    with pytest.raises(ValueError, match="cap"):
        qi.riesz_transform(huge_i)
    huge_rgb = np.broadcast_to(np.zeros((1, 1, 3), np.float32), (8192, 8192, 3))
    with pytest.raises(ValueError, match="cap"):
        qi.rgb_to_quaternion(huge_rgb)


def test_scales_cap_bounds_the_filter_bank():
    v = one_grating_clip(0.1, h=16, w=16, t=8)
    with pytest.raises(ValueError, match=r"scales must be in \[1, 8\]"):
        qi.riesz_displacement(v, 3.0, 5.0, 16.0, scales=9)
    with pytest.raises(ValueError, match="scales"):
        qi.riesz_displacement(v, 3.0, 5.0, 16.0, scales=2.5)


def test_alpha_cap_refuses_a_decorative_gain():
    v = one_grating_clip(0.1)
    with pytest.raises(ValueError, match="MAX_ALPHA"):
        qi.riesz_motion_magnify(v, 1e6, *BAND, FPS)


@pytest.mark.parametrize("lo,hi,fps,msg", [
    (0.0, 5.0, FPS, "f_lo must be > 0"),          # a band touching DC
    (5.0, 3.0, FPS, "f_lo < f_hi"),               # inverted
    (3.0, 40.0, FPS, "Nyquist"),                  # above Nyquist: refuse, not fold
    (4.10, 4.11, FPS, "no DFT bin"),              # narrower than the resolution
    (3.0, 5.0, 0.0, "fps must be > 0"),
])
def test_the_temporal_band_is_validated_against_the_clips_own_sampling(lo, hi, fps, msg):
    v = one_grating_clip(0.1)
    with pytest.raises(ValueError, match=msg):
        qi.riesz_displacement(v, lo, hi, fps)


def test_a_wavelength_past_nyquist_is_refused():
    img = np.random.default_rng(27).random((32, 32))
    with pytest.raises(ValueError, match="Nyquist"):
        qi.monogenic_signal(img, wavelength_px=2.0)
    with pytest.raises(ValueError, match="contains no frequency bin"):
        qi.monogenic_signal(img, wavelength_px=4096.0, bandwidth_octaves=0.01)


def test_degenerate_shapes_are_refused_rather_than_transformed():
    with pytest.raises(ValueError):
        qi.riesz_transform(np.zeros((1, 1)))
    with pytest.raises(ValueError):
        qi.riesz_displacement(np.zeros((1, 8, 8)), *BAND, FPS)       # T = 1
    with pytest.raises(ValueError, match="at least 4x4"):
        qi.riesz_displacement(np.zeros((8, 3, 3)), *BAND, FPS)


def test_a_constant_image_produces_no_measurement_rather_than_a_wrong_one():
    """No contrast anywhere: the amplitude is zero, the orientation is undefined,
    and the displacement must come back as exact zeros with rank 0 — not as a
    number produced by dividing rounding noise by rounding noise."""
    flat = np.full((16, 16), 0.5)
    q = qi.monogenic_signal(flat)
    assert np.abs(qi.monogenic_amplitude(q)).max() < 1e-12
    field = qi.riesz_displacement(np.stack([flat] * 16), 3.0, 5.0, 16.0)
    assert (field["rank"] == 0).all()
    assert np.array_equal(field["dx"], np.zeros_like(field["dx"]))
    series = qi.riesz_displacement_series(np.stack([flat] * 16), 3.0, 5.0, 16.0)
    assert np.array_equal(series, np.zeros((16, 2)))


def test_correlation_refuses_a_mismatched_template():
    a = qi.rgb_to_quaternion(colour_image(seed=28, h=16, w=16))
    b = qi.rgb_to_quaternion(colour_image(seed=29, h=8, w=8))
    with pytest.raises(ValueError, match="same shape"):
        qi.quat_correlate(a, b)


def test_multiply_refuses_a_guessed_broadcast():
    q = qi.rgb_to_quaternion(colour_image(seed=30, h=8, w=8))
    with pytest.raises(ValueError, match="broadcast"):
        qi.quat_image_multiply(q, np.ones((8, 4)), "left")
    assert qi.quat_image_multiply(q, np.ones(4), "left").shape == q.shape


# --------------------------------------------------------------------------- #
# registry                                                                     #
# --------------------------------------------------------------------------- #
def test_the_registry_is_complete_and_its_declared_types_are_honest():
    assert opsquat.missing() == []
    assert len(opsquat.OPSQUAT) == 19
    checks = {
        "qimage": lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[2] == 4,
        "image2d": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
        "rgbimage": lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[2] == 3,
        "table": lambda v: isinstance(v, (list, dict)),
        "pairs": lambda v: True,
    }
    img = np.random.default_rng(31).random((32, 32))
    mono = qi.monogenic_signal(img)
    colour = qi.rgb_to_quaternion(colour_image(seed=32))
    vid = one_grating_clip(0.2, h=32, w=32, t=32)
    produced = {
        "rgb_to_quaternion": qi.rgb_to_quaternion(colour_image(seed=33)),
        "quaternion_to_rgb": qi.quaternion_to_rgb(colour),
        "quat_norm": qi.quat_norm(colour),
        "quat_conjugate_image": qi.quat_conjugate_image(colour),
        "quat_normalize_image": qi.quat_normalize_image(mono + 1.0),
        "quat_image_multiply": qi.quat_image_multiply(colour, mono, "left"),
        "riesz_transform": qi.riesz_transform(img),
        "monogenic_signal": mono,
        "monogenic_amplitude": qi.monogenic_amplitude(mono),
        "monogenic_phase": qi.monogenic_phase(mono),
        "monogenic_orientation": qi.monogenic_orientation(mono),
        "quat_color_rotate": qi.quat_color_rotate(colour, (0, 0, 1), 0.5),
        "quat_color_filter": qi.quat_color_filter(colour, (1, 1, 1), "remove"),
        "qft2": qi.qft2(colour, "left"),
        "iqft2": qi.iqft2(colour, "left"),
        "riesz_motion_magnify": qi.riesz_motion_magnify(vid, 2.0, 3.0, 5.0, 32.0),
        "riesz_displacement": qi.riesz_displacement(vid, 3.0, 5.0, 32.0),
        "riesz_displacement_series": qi.riesz_displacement_series(vid, 3.0, 5.0, 32.0),
        "quat_correlate": qi.quat_correlate(colour, colour),
    }
    assert set(produced) == set(opsquat.OPSQUAT)
    for name, value in produced.items():
        declared = opsquat.OPSQUAT[name]["out"]
        assert checks[declared](value), "%s declared %s but returned %r" % (
            name, declared, type(value).__name__)


def test_the_new_type_is_reachable_and_has_an_exit():
    """A type nothing produces is unreachable; a type nothing consumes is a
    dead end. Both are counted here rather than asserted in a comment."""
    entries = [n for n, m in opsquat.OPSQUAT.items()
               if m["out"] == "qimage" and "qimage" not in m["in"]]
    exits = [n for n, m in opsquat.OPSQUAT.items()
             if "qimage" in m["in"] and m["out"] != "qimage"]
    assert sorted(entries) == ["monogenic_signal", "rgb_to_quaternion", "riesz_transform"]
    assert len(exits) >= 4

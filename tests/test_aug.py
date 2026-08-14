"""Correctness anchors for the sensor / sim-to-real augmentation cluster (``aug_``).

``tests/test_op_contracts.py`` already covers the universal contracts
(no-raise, finite, deterministic, declared sort) for every registry op. These
tests check that each ``aug_`` op actually implements the sensor-degradation
model it claims: shot noise really scales with the photon count, motion blur of a
delta really spreads energy along the streak angle, vignetting really darkens the
corners, JPEG quantisation really creates 8x8 seams, and so on.
"""
from __future__ import annotations

import numpy as np
import pytest

import backends_aug as A

N = 48


# --------------------------------------------------------------------------- #
# fixtures / helpers                                                          #
# --------------------------------------------------------------------------- #
def _ramp():
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    return np.clip(0.5 + 0.4 * np.sin(xx / 3.0) * np.cos(yy / 5.0), 0.0, 1.0)


def _delta():
    d = np.zeros((N, N), np.float64)
    d[N // 2, N // 2] = 1.0
    return d


def _disk(radius=10.0):
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    c = (N - 1) / 2.0
    return (((yy - c) ** 2 + (xx - c) ** 2) < radius ** 2).astype(np.float64)


def _const(val=0.42):
    return np.full((N, N), float(val))


class _Op:
    def __init__(s, n, c, h, i, o, f):
        s.name, s.category, s.halcon, s.in_sort, s.out_sort, s.fn = n, c, h, i, o, f


def _built():
    return A.build(_Op, "image", "region", "feature", "contour",
                   lambda x: x, lambda x: (np.asarray(x) > 0.5).astype(float))


# --------------------------------------------------------------------------- #
# registry-level honesty                                                      #
# --------------------------------------------------------------------------- #
def test_build_declares_no_halcon_equivalent():
    ops = _built()
    assert len(ops) == 10
    names = [o.name for o in ops]
    assert len(set(names)) == len(names), "duplicate op name inside the cluster"
    for o in ops:
        assert o.name.startswith("aug_"), o.name
        assert o.halcon == "", f"{o.name} must claim NO HALCON equivalent"
        assert o.category == "augmentation"
        assert o.in_sort == "image" and o.out_sort == "image"


def test_build_ops_are_wrapped_and_fail_soft():
    """The _safe wrapper must swallow a bad input and still return a valid image."""
    for op in _built():
        out = op.fn(np.array([[np.nan, np.inf], [1e9, -1e9]]), 0.5, 0.5)
        assert isinstance(out, np.ndarray)
        assert np.isfinite(out).all()


# --------------------------------------------------------------------------- #
# aug_shot_noise -- Poisson photon statistics                                 #
# --------------------------------------------------------------------------- #
def test_shot_noise_variance_follows_photon_count():
    """Poisson variance ~ 1/K, and K = 5 + 250*(1-a) shrinks as a grows."""
    flat = _const(0.42)
    clean = A.aug_shot_noise(flat, 0.0, 0.0)   # K = 255
    noisy = A.aug_shot_noise(flat, 1.0, 0.0)   # K = 5
    assert noisy.var() > 10 * clean.var() > 0.0
    # near-clean case still tracks the signal level
    assert abs(clean.mean() - 0.42) < 0.02


def test_shot_noise_is_quantised_by_the_photon_scale():
    """Output must be an integer photon count divided by K (a real Poisson draw)."""
    K = 5.0 + 250.0 * (1.0 - 1.0)              # a = 1 -> K = 5
    out = A.aug_shot_noise(_const(0.6), 1.0, 0.0)
    counts = out * K
    assert np.allclose(counts, np.round(counts), atol=1e-9)
    assert counts.max() >= 1.0                  # photons were actually counted


def test_shot_noise_realisation_is_fixed_per_knob_but_varies_across_knobs():
    flat = _const(0.5)
    assert np.array_equal(A.aug_shot_noise(flat, 0.7, 0.2), A.aug_shot_noise(flat, 0.7, 0.2))
    assert not np.array_equal(A.aug_shot_noise(flat, 0.7, 0.2), A.aug_shot_noise(flat, 0.7, 0.9))


# --------------------------------------------------------------------------- #
# aug_read_noise -- Gaussian amplifier noise + row banding                     #
# --------------------------------------------------------------------------- #
def test_read_noise_sigma_scales_with_a():
    flat = _const(0.5)
    lo = A.aug_read_noise(flat, 0.1, 0.0).std()
    hi = A.aug_read_noise(flat, 1.0, 0.0).std()
    assert 0.0 < lo < hi
    assert hi == pytest.approx(0.005 + 0.15, rel=0.25)   # sigma = 0.005 + 0.15*a


def test_read_noise_b_adds_row_correlated_banding():
    """b > 0 injects a per-row bias -> the spread of ROW MEANS must increase."""
    flat = _const(0.5)
    plain = A.aug_read_noise(flat, 1.0, 0.0)
    banded = A.aug_read_noise(flat, 1.0, 1.0)
    assert banded.mean(axis=1).std() > 2.0 * plain.mean(axis=1).std()


# --------------------------------------------------------------------------- #
# aug_fixed_pattern -- static FPN / PRNU                                       #
# --------------------------------------------------------------------------- #
def test_fixed_pattern_is_the_same_offset_regardless_of_scene():
    """FPN is a *fixed* additive pattern: it must not depend on the image."""
    p1 = A.aug_fixed_pattern(_const(0.3), 0.0, 0.7) - 0.3
    p2 = A.aug_fixed_pattern(_const(0.5), 0.0, 0.7) - 0.5
    assert np.allclose(p1, p2, atol=1e-12)
    assert np.abs(p1).max() > 1e-3               # the pattern is not empty


def test_fixed_pattern_amplitude_grows_with_a_and_pattern_selected_by_b():
    base = _const(0.5)
    weak = np.abs(A.aug_fixed_pattern(base, 0.0, 0.4) - 0.5).mean()
    strong = np.abs(A.aug_fixed_pattern(base, 1.0, 0.4) - 0.5).mean()
    assert strong > 5.0 * weak > 0.0
    assert not np.array_equal(A.aug_fixed_pattern(base, 0.5, 0.1),
                              A.aug_fixed_pattern(base, 0.5, 0.9))


# --------------------------------------------------------------------------- #
# aug_motion_blur -- linear PSF                                                #
# --------------------------------------------------------------------------- #
def test_motion_blur_of_a_delta_spreads_energy_along_the_streak():
    """A delta convolved with a normalised line kernel: energy conserved, peak
    reduced, support confined to one row at angle 0 and one column at 90 deg."""
    d = _delta()
    horiz = A.aug_motion_blur(d, 1.0, 0.0)       # angle 0 deg
    vert = A.aug_motion_blur(d, 1.0, 0.5)        # angle 90 deg
    assert horiz.sum() == pytest.approx(1.0, abs=1e-9)   # energy preserving
    assert horiz.max() < 0.2                             # peak spread out
    rows = np.unique(np.argwhere(horiz > 1e-9)[:, 0])
    cols = np.unique(np.argwhere(vert > 1e-9)[:, 1])
    assert rows.tolist() == [N // 2], "angle 0 must blur horizontally only"
    assert cols.tolist() == [N // 2], "angle 90 must blur vertically only"
    assert len(np.unique(np.argwhere(horiz > 1e-9)[:, 1])) >= 15   # long streak


def test_motion_blur_preserves_a_flat_field_and_lengthens_with_a():
    flat = _const(0.7)
    assert np.allclose(A.aug_motion_blur(flat, 1.0, 0.3), flat, atol=1e-9)
    d = _delta()
    short = (A.aug_motion_blur(d, 0.1, 0.0) > 1e-9).sum()
    long_ = (A.aug_motion_blur(d, 1.0, 0.0) > 1e-9).sum()
    assert long_ > short >= 1


# --------------------------------------------------------------------------- #
# aug_vignette -- cos^4 falloff                                                #
# --------------------------------------------------------------------------- #
def test_vignette_darkens_corners_only_and_never_brightens():
    ones = np.ones((N, N))
    out = A.aug_vignette(ones, 1.0, 0.2)
    assert out[N // 2, N // 2] > 0.95            # centre stays bright
    assert out[0, 0] < 0.5                       # corner strongly attenuated
    assert (out <= ones + 1e-12).all()           # purely multiplicative darkening
    # monotone: attenuation increases with radius along the centre row
    row = out[N // 2, N // 2:]
    assert np.all(np.diff(row) <= 1e-12)


def test_vignette_a_zero_is_identity_and_strength_is_monotone():
    img = _ramp()
    assert np.allclose(A.aug_vignette(img, 0.0, 0.5), img, atol=1e-12)
    weak = A.aug_vignette(img, 0.3, 0.5).sum()
    strong = A.aug_vignette(img, 1.0, 0.5).sum()
    assert strong < weak < img.sum()


# --------------------------------------------------------------------------- #
# aug_chromatic -- lateral CA proxy                                            #
# --------------------------------------------------------------------------- #
def test_chromatic_touches_edges_only():
    """The fringe is built from the high-pass, so a flat field is untouched."""
    assert np.allclose(A.aug_chromatic(_const(0.42), 0.8, 1.0), _const(0.42), atol=1e-12)
    edge = np.zeros((N, N)); edge[:, N // 2:] = 1.0
    out = A.aug_chromatic(edge, 0.8, 1.0)
    diff = np.abs(out - edge)
    assert diff.max() > 1e-3                       # the edge fringes
    assert diff[:, :N // 2 - 8].max() < 1e-6       # far-from-edge stays clean


def test_chromatic_blend_amplitude_grows_with_b():
    img = _ramp()
    weak = np.abs(A.aug_chromatic(img, 0.5, 0.0) - img).mean()
    strong = np.abs(A.aug_chromatic(img, 0.5, 1.0) - img).mean()
    assert strong > weak > 0.0


# --------------------------------------------------------------------------- #
# aug_rolling_shutter -- per-row shear                                         #
# --------------------------------------------------------------------------- #
def test_rolling_shutter_shears_rows_in_opposite_directions():
    """A vertical bar must lean: top and bottom rows shift opposite ways, and
    the centre row (exposed at mid-frame) is unmoved."""
    bar = np.zeros((N, N)); bar[:, N // 2] = 1.0
    out = A.aug_rolling_shutter(bar, 1.0, 0.0)
    top, mid, bot = int(np.argmax(out[0])), int(np.argmax(out[N // 2])), int(np.argmax(out[-1]))
    assert mid == N // 2
    assert top < mid < bot
    flipped = A.aug_rolling_shutter(bar, 1.0, 1.0)
    assert int(np.argmax(flipped[0])) > int(np.argmax(flipped[-1]))   # direction flips


def test_rolling_shutter_a_zero_is_identity_and_skew_grows_with_a():
    bar = np.zeros((N, N)); bar[:, N // 2] = 1.0
    assert np.allclose(A.aug_rolling_shutter(bar, 0.0, 0.0), bar, atol=1e-12)
    small = int(np.argmax(A.aug_rolling_shutter(bar, 0.3, 0.0)[-1]))
    large = int(np.argmax(A.aug_rolling_shutter(bar, 1.0, 0.0)[-1]))
    assert large > small > N // 2


# --------------------------------------------------------------------------- #
# aug_jpeg_blocks -- 8x8 DCT quantisation                                      #
# --------------------------------------------------------------------------- #
def _seam_ratio(x):
    """mean |dx| across the 8x8 block seams / mean |dx| inside the blocks."""
    dx = np.abs(np.diff(x, axis=1))
    seam = dx[:, 7::8].mean()
    interior = np.delete(dx, np.arange(7, dx.shape[1], 8), axis=1).mean()
    return seam / max(interior, 1e-12)


def test_jpeg_blocks_creates_8x8_seams_at_heavy_quantisation():
    img = _ramp()
    heavy = A.aug_jpeg_blocks(img, 1.0, 0.0)
    assert _seam_ratio(heavy) > 1.25 * _seam_ratio(img), "no blocking artefact appeared"


def test_jpeg_blocks_error_grows_with_quantiser_and_is_near_lossless_at_a0():
    img = _ramp()
    fine = np.abs(A.aug_jpeg_blocks(img, 0.0, 0.0) - img).mean()
    coarse = np.abs(A.aug_jpeg_blocks(img, 1.0, 0.0) - img).mean()
    assert fine < 0.005 < coarse
    # a constant field is pure DC -> survives even the coarsest quantiser
    assert np.abs(A.aug_jpeg_blocks(_const(0.42), 1.0, 0.0) - 0.42).max() < 0.02


def test_jpeg_blocks_grid_phase_depends_on_b_and_tiny_images_work():
    img = _ramp()
    assert not np.allclose(A.aug_jpeg_blocks(img, 1.0, 0.0), A.aug_jpeg_blocks(img, 1.0, 0.6))
    tiny = (np.arange(16, dtype=np.float64) / 15.0).reshape(4, 4)   # smaller than one block
    out = A.aug_jpeg_blocks(tiny, 0.5, 0.5)
    assert out.shape == (4, 4) and np.isfinite(out).all()


# --------------------------------------------------------------------------- #
# aug_cutout -- occlusion / random erasing                                     #
# --------------------------------------------------------------------------- #
def test_cutout_erases_exactly_one_rectangle_with_the_declared_fill():
    img = _const(0.8)
    black = A.aug_cutout(img, 0.5, 0.2)          # b <= 0.5 -> fill 0.0
    gray = A.aug_cutout(img, 0.5, 0.9)           # b  > 0.5 -> fill 0.5
    side = int(round(0.5 * N))
    assert (black == 0.0).sum() == side * side
    assert (gray == 0.5).sum() == side * side
    # the erased pixels form a solid axis-aligned rectangle
    ys, xs = np.nonzero(black == 0.0)
    assert ys.max() - ys.min() + 1 == side and xs.max() - xs.min() + 1 == side
    # everything outside the patch is untouched
    keep = black != 0.0
    assert np.allclose(black[keep], img[keep])


def test_cutout_area_grows_with_a_and_stays_inside_the_frame():
    img = _const(0.8)
    small = (A.aug_cutout(img, 0.2, 0.1) == 0.0).sum()
    big = (A.aug_cutout(img, 0.9, 0.1) == 0.0).sum()
    assert 1 <= small < big <= N * N
    full = A.aug_cutout(img, 1.0, 0.1)
    assert (full == 0.0).all()                   # a=1 erases the whole frame


# --------------------------------------------------------------------------- #
# aug_barrel -- radial lens distortion                                         #
# --------------------------------------------------------------------------- #
def test_barrel_and_pincushion_scale_a_centred_disk_in_opposite_directions():
    disk = _disk(10.0)
    area0 = (disk > 0.5).sum()
    barrel = (A.aug_barrel(disk, 1.0, 0.0) > 0.5).sum()      # b < 0.5
    pincushion = (A.aug_barrel(disk, 1.0, 1.0) > 0.5).sum()  # b >= 0.5
    assert barrel < area0 < pincushion, (barrel, area0, pincushion)


def test_barrel_a_zero_is_identity_and_centre_is_a_fixed_point():
    img = _ramp()
    assert np.allclose(A.aug_barrel(img, 0.0, 0.0), img, atol=1e-12)
    out = A.aug_barrel(img, 0.8, 0.0)
    assert out.shape == img.shape
    c = N // 2
    # r=0 maps to itself, so the very centre barely moves
    assert abs(out[c, c] - img[c, c]) < 0.02
    assert not np.allclose(out, img)             # but the periphery does move

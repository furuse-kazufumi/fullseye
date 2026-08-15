"""Ground-truth + contract tests for deformreg.py (Thirion demons registration).

Nothing here is satisfied by "it ran without raising". Every anchor recomputes
the named algorithm a second, independent way and compares:

  * the warp is checked against ``np.roll`` (integer field) and against a
    hand-written bilinear blend (sub-pixel field), not against itself;
  * one demons iteration is compared to the Thirion 1998 velocity formula
    recomputed from scratch in the test (``np.gradient`` here, elementwise);
  * the step cap is checked against its own bound, the elastic regulariser
    against an independent smoothness measure;
  * convergence is checked on a *known* deformation (a blob shifted by a known
    number of pixels): the SSD must collapse and the recovered field must carry
    the right sign and roughly the right magnitude;
  * the identity case must produce an exactly zero field, and a constant fixed
    image (no gradient -> no demon force) must too.

Determinism, finiteness, shape and [0,1] range are asserted over the shared
conftest image battery, and the fail-soft contract over deliberate garbage.
"""
from __future__ import annotations

import inspect

import numpy as np
import pytest
from scipy import ndimage

import deformreg as D
from conftest import image_bank


# --------------------------------------------------------------------------- #
# helpers (independent of the module under test)                              #
# --------------------------------------------------------------------------- #
def _blob(n=64, cy=30.0, cx=28.0, s=9.0):
    """A smooth Gaussian blob in [0,1] -- differentiable everywhere, so the demon
    force is well defined over a wide basin."""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    g = np.exp(-(((yy - cy) ** 2 + (xx - cx) ** 2) / (2.0 * s * s)))
    return g / g.max()


def _ssd(a, b):
    return float(np.sum((np.asarray(a, np.float64) - np.asarray(b, np.float64)) ** 2))


def _demon_velocity(F, M, eps=1e-9):
    """Thirion 1998 demon force, recomputed independently of deformreg."""
    gy = np.gradient(F, axis=0)
    gx = np.gradient(F, axis=1)
    d = M - F
    den = gx ** 2 + gy ** 2 + d ** 2 + eps
    return d * gx / den, d * gy / den


# --------------------------------------------------------------------------- #
# structural / provenance / no-RNG                                            #
# --------------------------------------------------------------------------- #
def test_public_surface_and_provenance():
    assert D.__all__ == ["warp_by_field", "demons_register", "field_magnitude", "residual_ssd"]
    for name in D.__all__:
        fn = getattr(D, name)
        assert callable(fn) and (fn.__doc__ or "").strip(), f"{name} lacks a docstring"
    doc = D.__doc__ or ""
    assert "Thirion" in doc and "1998" in doc          # published algorithm cited
    assert "Medical Image Analysis" in doc


def test_module_contains_no_rng():
    """Determinism is structural: the source may not touch a random generator."""
    src = inspect.getsource(D)
    for forbidden in ("np.random", "numpy.random", "import random", "default_rng",
                      "RandomState", "np.shuffle", "randint"):
        assert forbidden not in src, f"RNG reference {forbidden!r} in deformreg.py"


def test_no_third_party_imports():
    src = inspect.getsource(D)
    for line in src.splitlines():
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            mod = s.split()[1].split(".")[0]
            assert mod in {"__future__", "numpy", "scipy", "backend_safe"}, f"unexpected import: {s}"


# --------------------------------------------------------------------------- #
# (iv) warp_by_field ground truth                                             #
# --------------------------------------------------------------------------- #
def test_warp_zero_field_is_identity():
    img = image_bank(32)["normal"]
    out = D.warp_by_field(img, np.zeros_like(img), np.zeros_like(img))
    assert out.shape == img.shape and out.dtype == np.float64
    assert np.array_equal(out, img)                     # bit-identical, not merely close
    # scalar-zero field takes the same broadcast path
    assert np.array_equal(D.warp_by_field(img, 0.0, 0.0), img)


def test_warp_constant_field_is_a_global_shift():
    """A constant field must reproduce np.roll exactly on the interior.

    Convention: out[y, x] = img[y - fy, x - fx].  With fy = -2, fx = +3 that is
    img[y + 2, x - 3], i.e. np.roll(img, shift=(-2, +3)).
    """
    img = image_bank(32)["normal"]
    fy, fx = -2.0, 3.0
    out = D.warp_by_field(img, np.full(img.shape, fx), np.full(img.shape, fy))
    ref = np.roll(img, shift=(-2, 3), axis=(0, 1))
    inner = (slice(0, 30), slice(3, 32))                # away from the clamped border
    assert np.allclose(out[inner], ref[inner], atol=1e-12)
    # a known single pixel, spelled out
    assert out[10, 20] == pytest.approx(img[12, 17], abs=1e-12)
    # and the border is edge-clamped, not wrapped
    assert out[31, 0] == pytest.approx(img[31, 0], abs=1e-12)


def test_warp_subpixel_field_is_exact_bilinear():
    """Half-pixel shift = average of the two neighbours (bilinear by hand)."""
    img = image_bank(24)["normal"]
    out = D.warp_by_field(img, 0.5, 0.0)                # out[y,x] = img[y, x-0.5]
    ref = 0.5 * img[:, :-1] + 0.5 * img[:, 1:]          # value midway between x-1 and x
    assert np.allclose(out[:, 1:], ref, atol=1e-12)
    # a 2-D sub-pixel offset, recomputed from the four corners
    out2 = D.warp_by_field(img, 0.25, 0.75)             # fx=0.25, fy=0.75
    y, x = 10, 12
    fx, fy = 0.25, 0.75                                  # samples (y-0.75, x-0.25)
    y0, x0 = y - 1, x - 1                                # floor(y-0.75)=y-1, floor(x-0.25)=x-1
    wy, wx = (y - fy) - y0, (x - fx) - x0
    exp = ((1 - wy) * (1 - wx) * img[y0, x0] + (1 - wy) * wx * img[y0, x0 + 1]
           + wy * (1 - wx) * img[y0 + 1, x0] + wy * wx * img[y0 + 1, x0 + 1])
    assert out2[y, x] == pytest.approx(exp, abs=1e-12)


def test_warp_preserves_shape_range_and_colour():
    img = image_bank(16)["normal"]
    col = np.stack([img, 1 - img, 0.5 * img], axis=-1)
    out = D.warp_by_field(col, 1.0, -1.0)
    assert out.shape == col.shape
    assert np.all(np.isfinite(out)) and out.min() >= 0.0 and out.max() <= 1.0
    # each channel warps like the 2-D warp of that channel
    for c in range(3):
        assert np.allclose(out[..., c], D.warp_by_field(col[..., c], 1.0, -1.0), atol=1e-12)


def test_warp_never_invents_values_outside_the_input_range():
    img = image_bank(24)["normal"]
    out = D.warp_by_field(img, 1.3, -0.7)
    assert out.min() >= img.min() - 1e-12 and out.max() <= img.max() + 1e-12


# --------------------------------------------------------------------------- #
# demons: exact one-iteration ground truth (the Thirion formula itself)       #
# --------------------------------------------------------------------------- #
def test_one_iteration_equals_the_thirion_velocity_formula():
    F = _blob()
    M = ndimage.shift(F, (0.0, 2.0), order=1, mode="nearest")
    # sigma=0 (no regulariser) and an effectively infinite cap -> the field after
    # one iteration IS the raw demon velocity.
    _, fx, fy = D.demons_register(F, M, iters=1, sigma=0.0, max_step=1e9)
    vx, vy = _demon_velocity(F, M)
    assert np.allclose(fx, vx, atol=1e-12), float(np.max(np.abs(fx - vx)))
    assert np.allclose(fy, vy, atol=1e-12), float(np.max(np.abs(fy - vy)))


def test_thirion_stabiliser_bounds_one_step_at_half_a_pixel():
    """|v| = |d||g|/(|g|^2 + d^2 + eps) <= 1/2 by AM-GM -- the whole point of the
    ``d^2`` stabiliser. Asserted on the module AND on the independent formula."""
    F = _blob()
    M = ndimage.shift(F, (1.0, 2.0), order=1, mode="nearest")
    _, fx, fy = D.demons_register(F, M, iters=1, sigma=0.0, max_step=1e9)
    mag = np.hypot(fx, fy)
    assert mag.max() <= 0.5 + 1e-12, mag.max()
    assert mag.max() > 1e-3, "test is vacuous unless the demons actually moved"
    vx, vy = _demon_velocity(F, M)
    assert np.hypot(vx, vy).max() <= 0.5 + 1e-12
    # unregularised optical flow (no d^2 term) is NOT bounded -- that is what the
    # stabiliser buys, so show the difference is real.
    gy, gx = np.gradient(F, axis=0), np.gradient(F, axis=1)
    raw = np.abs((M - F) * gx) / (gx ** 2 + gy ** 2 + 1e-9)
    assert raw.max() > 4.0 * mag.max(), (raw.max(), mag.max())


def test_step_cap_rescales_without_turning():
    """A tighter ITK-style MaximumUpdateStepLength clips the length, not the
    direction."""
    F = _blob()
    M = ndimage.shift(F, (1.0, 2.0), order=1, mode="nearest")
    cap = 0.05
    _, fx, fy = D.demons_register(F, M, iters=1, sigma=0.0, max_step=cap)
    assert np.max(np.hypot(fx, fy)) <= cap + 1e-12
    vx, vy = _demon_velocity(F, M)
    mag = np.hypot(vx, vy)
    hit = mag > cap
    assert hit.any(), "test is vacuous unless the cap actually engages"
    assert np.allclose(fx[hit], vx[hit] * cap / mag[hit], atol=1e-12)
    assert np.allclose(fy[hit], vy[hit] * cap / mag[hit], atol=1e-12)


def test_elastic_regulariser_smooths_the_field():
    """Larger sigma => a smoother (lower curvature energy) displacement field."""
    F = _blob()
    M = ndimage.shift(F, (0.0, 3.0), order=1, mode="nearest")
    _, fx0, fy0 = D.demons_register(F, M, iters=10, sigma=0.0)
    _, fx3, fy3 = D.demons_register(F, M, iters=10, sigma=3.0)

    def rough(a):                                        # independent smoothness metric
        return float(np.mean(np.abs(ndimage.laplace(a))))

    assert rough(fx3) < rough(fx0) and rough(fy3) < rough(fy0)


# --------------------------------------------------------------------------- #
# (i) identity                                                                #
# --------------------------------------------------------------------------- #
def test_identity_registration_returns_zero_field():
    F = _blob()
    warped, fx, fy = D.demons_register(F, F, iters=50, sigma=1.5)
    assert np.array_equal(fx, np.zeros_like(F))          # diff == 0 => v == 0, exactly
    assert np.array_equal(fy, np.zeros_like(F))
    assert np.allclose(warped, F, atol=1e-12)
    assert _ssd(warped, F) < 1e-20                       # residual stays at (near) zero


def test_identity_on_a_textured_bank_image():
    F = image_bank(48)["normal"]
    warped, fx, fy = D.demons_register(F, F, iters=20)
    assert np.max(np.abs(fx)) == 0.0 and np.max(np.abs(fy)) == 0.0
    assert np.allclose(warped, F, atol=1e-12)


# --------------------------------------------------------------------------- #
# (ii) convergence on a known deformation                                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("sy,sx", [(0.0, 3.0), (2.0, -3.0), (1.5, 2.5), (-2.5, 0.0)])
def test_registration_substantially_reduces_ssd(sy, sx):
    F = _blob()
    M = ndimage.shift(F, (sy, sx), order=1, mode="nearest")
    before = _ssd(M, F)
    warped, fx, fy = D.demons_register(F, M, iters=50, sigma=1.5)
    after = _ssd(warped, F)
    assert before > 1.0, "the test deformation must be a real one"
    assert after < 0.6 * before, f"SSD {before:.4f} -> {after:.4f} is not a 40% reduction"
    assert after < 0.05 * before                         # in practice it collapses
    assert np.all(np.isfinite(fx)) and np.all(np.isfinite(fy))


def test_integer_roll_deformation_also_converges():
    F = _blob()
    M = np.roll(F, 3, axis=1)                            # pure integer shift, no resample
    before = _ssd(M, F)
    warped, _, _ = D.demons_register(F, M, iters=50, sigma=1.5)
    after = _ssd(warped, F)
    assert after < 0.6 * before


def test_recovered_field_has_the_right_sign_and_scale():
    """Ground truth on the field itself, not just the residual.

    moving(x) = fixed(x - s)  (content shifted right by s).  warp_by_field samples
    at x - fx, so the field that undoes it is fx = -s.
    """
    F = _blob()
    s = 3.0
    M = ndimage.shift(F, (0.0, s), order=1, mode="nearest")
    _, fx, fy = D.demons_register(F, M, iters=60, sigma=1.5)
    core = F > 0.5                                       # where the demon force exists
    fx_core = float(fx[core].mean())
    fy_core = float(fy[core].mean())
    assert fx_core < 0.0, "field must point opposite to the applied shift"
    assert abs(fx_core - (-s)) < 1.2, f"recovered {fx_core:.3f} vs true {-s}"
    assert abs(fy_core) < 0.3, "no vertical shift was applied"
    # a vertical deformation must show up in fy and (almost) not in fx
    M2 = ndimage.shift(F, (-2.0, 0.0), order=1, mode="nearest")
    _, fx2, fy2 = D.demons_register(F, M2, iters=60, sigma=1.5)
    assert float(fy2[core].mean()) > 1.0 and abs(float(fx2[core].mean())) < 0.3


def test_registration_beats_the_null_transform_on_a_bank_image():
    """Non-synthetic check: a textured bank image, deformed by a smooth non-rigid
    (sinusoidal) field, is brought back closer than doing nothing."""
    F = image_bank(48)["normal"]
    yy, xx = np.mgrid[0:48, 0:48].astype(np.float64)
    gx = 2.0 * np.sin(2 * np.pi * yy / 48.0)
    gy = 1.5 * np.cos(2 * np.pi * xx / 48.0)
    M = D.warp_by_field(F, gx, gy)
    before = _ssd(M, F)
    warped, _, _ = D.demons_register(F, M, iters=60, sigma=1.5)
    after = _ssd(warped, F)
    assert after < 0.6 * before, f"{before:.4f} -> {after:.4f}"


# --------------------------------------------------------------------------- #
# (iii) determinism                                                           #
# --------------------------------------------------------------------------- #
def test_determinism_bit_identical_across_runs():
    F = _blob()
    M = ndimage.shift(F, (1.0, -2.0), order=1, mode="nearest")
    w1, fx1, fy1 = D.demons_register(F, M, iters=25, sigma=1.5)
    w2, fx2, fy2 = D.demons_register(F, M, iters=25, sigma=1.5)
    assert np.array_equal(w1, w2)
    assert np.array_equal(fx1, fx2) and np.array_equal(fy1, fy2)
    # ... and the inputs were not mutated in place
    assert np.array_equal(M, ndimage.shift(F, (1.0, -2.0), order=1, mode="nearest"))


def test_warp_is_deterministic_and_self_consistent():
    F = _blob()
    M = ndimage.shift(F, (0.0, 2.0), order=1, mode="nearest")
    warped, fx, fy = D.demons_register(F, M, iters=15, sigma=1.5)
    # the returned image is exactly the moving image under the returned field
    assert np.array_equal(warped, D.warp_by_field(M, fx, fy))
    assert np.array_equal(D.warp_by_field(M, fx, fy), D.warp_by_field(M, fx, fy))


# --------------------------------------------------------------------------- #
# contract over the shared battery: shape / finite / range / dtype            #
# --------------------------------------------------------------------------- #
def test_contract_over_image_bank_pairs():
    bank = image_bank(24)
    for fname, F in bank.items():
        for mname, M in bank.items():
            warped, fx, fy = D.demons_register(F, M, iters=6, sigma=1.5)
            tag = f"{fname}->{mname}"
            assert warped.shape == F.shape, tag
            assert warped.dtype == np.float64, tag
            assert np.all(np.isfinite(warped)), tag
            assert warped.min() >= 0.0 and warped.max() <= 1.0, tag
            assert fx.shape == F.shape and fy.shape == F.shape, tag
            assert np.all(np.isfinite(fx)) and np.all(np.isfinite(fy)), tag


def test_constant_fixed_image_yields_no_deformation():
    """No gradient => no demon force. Documented behaviour, asserted."""
    F = np.full((32, 32), 0.42)
    M = _blob(32)
    warped, fx, fy = D.demons_register(F, M, iters=30)
    assert np.array_equal(fx, np.zeros_like(F)) and np.array_equal(fy, np.zeros_like(F))
    assert np.allclose(warped, M, atol=1e-12)            # moving passed through unchanged


def test_zero_iterations_is_the_null_transform():
    F = _blob(32)
    M = np.roll(F, 2, axis=0)
    warped, fx, fy = D.demons_register(F, M, iters=0)
    assert np.array_equal(fx, np.zeros_like(F)) and np.array_equal(fy, np.zeros_like(F))
    assert np.allclose(warped, M, atol=1e-12)


def test_mismatched_shapes_are_resampled_onto_the_fixed_grid():
    F = _blob(32)
    M = _blob(16)
    warped, fx, fy = D.demons_register(F, M, iters=5)
    assert warped.shape == F.shape and fx.shape == F.shape and fy.shape == F.shape
    assert np.all(np.isfinite(warped))


# --------------------------------------------------------------------------- #
# fail-soft on garbage                                                        #
# --------------------------------------------------------------------------- #
GARBAGE = [
    None,
    "not an image",
    np.array([]),
    np.zeros((0, 5)),
    np.full((16, 16), np.nan),
    np.full((16, 16), np.inf),
    np.array(0.5),
    np.arange(9.0),
    np.ones((4, 4, 3)),
    [[1, 2], [3, 4]],
    np.full((8, 8), 1e12),
]


@pytest.mark.parametrize("bad", GARBAGE)
def test_demons_is_fail_soft_on_garbage_moving(bad):
    F = _blob(16)
    warped, fx, fy = D.demons_register(F, bad, iters=5)
    assert warped.shape == F.shape and fx.shape == F.shape and fy.shape == F.shape
    assert np.all(np.isfinite(warped)) and np.all(np.isfinite(fx)) and np.all(np.isfinite(fy))
    assert warped.min() >= 0.0 and warped.max() <= 1.0


@pytest.mark.parametrize("bad", GARBAGE)
def test_demons_is_fail_soft_on_garbage_fixed(bad):
    M = _blob(16)
    warped, fx, fy = D.demons_register(bad, M, iters=5)
    assert warped.shape == fx.shape == fy.shape
    assert warped.ndim == 2 and warped.size >= 1
    assert np.all(np.isfinite(warped)) and np.all(np.isfinite(fx)) and np.all(np.isfinite(fy))
    assert warped.min() >= 0.0 and warped.max() <= 1.0


@pytest.mark.parametrize("bad", GARBAGE)
def test_warp_is_fail_soft_on_garbage(bad):
    out = D.warp_by_field(bad, 1.0, 2.0)
    assert isinstance(out, np.ndarray) and out.size >= 1
    assert np.all(np.isfinite(out)) and out.min() >= 0.0 and out.max() <= 1.0


def test_garbage_parameters_are_clamped_not_fatal():
    F = _blob(16)
    M = np.roll(F, 2, axis=1)
    for kw in ({"iters": -5}, {"iters": float("nan")}, {"sigma": -3.0},
               {"sigma": float("inf")}, {"max_step": 0.0}, {"eps": -1.0},
               {"iters": "x"}, {"sigma": None}):
        warped, fx, fy = D.demons_register(F, M, **kw)
        assert np.all(np.isfinite(warped)) and np.all(np.isfinite(fx)) and np.all(np.isfinite(fy))
        assert warped.shape == F.shape


def test_field_of_wrong_shape_is_ignored_not_fatal():
    img = _blob(16)
    out = D.warp_by_field(img, np.zeros((5, 7)), np.zeros((5, 7)))
    assert out.shape == img.shape
    assert np.array_equal(out, img)                      # unusable field -> no displacement


# --------------------------------------------------------------------------- #
# the small utilities, against independent references                         #
# --------------------------------------------------------------------------- #
def test_field_magnitude_matches_pythagoras():
    fx = np.array([[3.0, -4.0], [0.0, 1.0]])
    fy = np.array([[4.0, 3.0], [0.0, -1.0]])
    m = D.field_magnitude(fx, fy)
    assert np.allclose(m, [[5.0, 5.0], [0.0, np.sqrt(2.0)]], atol=1e-12)
    assert np.all(np.isfinite(D.field_magnitude([np.nan, np.inf], [1.0, 2.0])))


def test_residual_ssd_matches_a_hand_sum():
    a = np.array([[0.0, 0.5], [1.0, 0.25]])
    b = np.array([[0.5, 0.5], [0.0, 0.25]])
    expect = 0.5 ** 2 + 0.0 + 1.0 ** 2 + 0.0
    assert D.residual_ssd(a, b) == pytest.approx(expect, abs=1e-12)
    assert D.residual_ssd(a, a) == 0.0


def test_residual_ssd_tracks_the_registration():
    F = _blob()
    M = ndimage.shift(F, (0.0, 3.0), order=1, mode="nearest")
    warped, _, _ = D.demons_register(F, M, iters=50)
    assert D.residual_ssd(warped, F) < D.residual_ssd(M, F)
    assert D.residual_ssd(M, F) == pytest.approx(_ssd(M, F), rel=1e-12)

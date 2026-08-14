"""Correctness anchors for the tactile / contact-from-shading cluster (``tac_``).

The universal contracts (finite, deterministic, declared sort, unit range) are
covered for the whole registry by ``test_op_contracts.py``. These tests check
that each tactile op computes the *physically meaningful* thing it claims:

  * a flat (uncontacted) gel frame must produce no contact, no pressure, no
    shear, and a perfectly flat normal map;
  * an indentation must be localised by the contact mask and pressure proxy;
  * Poisson integration must turn shading into a relief that follows the bump;
  * the normal-z map must fall below 1 on slopes and fall further as the
    gradient gain rises;
  * the structure-tensor shear proxy must rank a stretched (uni-directional)
    texture above an isotropic one.
"""
from __future__ import annotations

import numpy as np
import pytest

import backends_tactile as T

N = 48


def _gel_with_bump(amp: float = 0.35, sig: float = 6.0) -> np.ndarray:
    """A GelSight-like frame: uniform gel with one Gaussian indentation."""
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    bump = np.exp(-(((yy - N / 2) ** 2 + (xx - N / 2) ** 2) / (2.0 * sig**2)))
    return np.clip(0.5 + amp * bump, 0.0, 1.0)


FLAT = np.full((N, N), 0.42)


# --------------------------------------------------------------------------- #
# tac_contact_mask                                                            #
# --------------------------------------------------------------------------- #
def test_contact_mask_is_binary_and_same_shape():
    m = T.tac_contact_mask(_gel_with_bump(), 0.2, 0.3)
    assert m.shape == (N, N) and m.dtype == np.float64
    assert set(np.unique(m).tolist()) <= {0.0, 1.0}


def test_contact_mask_empty_on_flat_gel():
    """No deformation -> no deviation from the pseudo-reference -> no contact."""
    for a in (0.0, 0.5, 1.0):
        assert T.tac_contact_mask(FLAT, a, 0.0).sum() == 0.0
        assert T.tac_contact_mask(np.zeros((N, N)), a, 0.5).sum() == 0.0
        assert T.tac_contact_mask(np.ones((N, N)), a, 0.5).sum() == 0.0


def test_contact_mask_finds_and_localises_the_indentation():
    img = _gel_with_bump()
    m = T.tac_contact_mask(img, 0.15, 0.0)
    assert m.sum() > 0, "the indentation must be detected as contact"
    assert m.sum() < m.size * 0.6, "contact must stay local, not flood the frame"
    assert m[N // 2, N // 2] == 1.0, "the bump centre must be inside the contact"
    assert m[0, 0] == 0.0 and m[-1, -1] == 0.0, "far corners must stay uncontacted"


def test_contact_mask_threshold_knob_is_monotone():
    """Higher a = stricter deviation threshold -> never more contact pixels."""
    img = _gel_with_bump()
    areas = [T.tac_contact_mask(img, a, 0.0).sum() for a in (0.0, 0.25, 0.5, 1.0)]
    assert all(x >= y for x, y in zip(areas, areas[1:])), areas
    assert areas[0] > areas[-1], "the threshold knob must actually do something"


# --------------------------------------------------------------------------- #
# tac_height_from_shading                                                     #
# --------------------------------------------------------------------------- #
def test_height_flat_on_constant_input():
    """div(grad const) = 0 -> the Poisson solve returns a flat relief."""
    h = T.tac_height_from_shading(FLAT, 0.5, 0.3)
    assert h.shape == (N, N)
    assert np.allclose(h, h.flat[0]), "a constant frame cannot have relief"


def test_height_is_normalised_and_non_trivial_on_a_bump():
    h = T.tac_height_from_shading(_gel_with_bump(), 0.5, 0.2)
    assert h.min() >= 0.0 and h.max() <= 1.0
    assert h.max() - h.min() > 0.5, "min-max normalisation must span the range"
    assert h.std() > 1e-3, "the recovered relief must not be flat"


def test_height_reconstructs_the_bump_shape():
    """Poisson integration of the bump's own gradients must peak at the bump."""
    img = _gel_with_bump()
    h = T.tac_height_from_shading(img, 0.5, 0.2)
    centre = h[N // 2 - 3:N // 2 + 4, N // 2 - 3:N // 2 + 4].mean()
    border = np.concatenate([h[0, :], h[-1, :], h[:, 0], h[:, -1]]).mean()
    assert centre > border + 0.2, (centre, border)
    # the peak of the reconstruction must sit near the peak of the indentation
    py, px = np.unravel_index(int(np.argmax(h)), h.shape)
    assert abs(py - N // 2) <= 3 and abs(px - N // 2) <= 3, (py, px)


def test_height_gain_knob_changes_nothing_but_scale_is_renormalised():
    """The gain scales p,q linearly; after min-max normalisation the relief is
    the same map, which is an honest property of a linear Poisson solve."""
    img = _gel_with_bump()
    h1 = T.tac_height_from_shading(img, 0.2, 0.0)
    h2 = T.tac_height_from_shading(img, 0.9, 0.0)
    assert np.allclose(h1, h2, atol=1e-8)
    # smoothing, in contrast, genuinely changes the result
    h3 = T.tac_height_from_shading(img, 0.2, 0.9)
    assert not np.allclose(h1, h3, atol=1e-6)


# --------------------------------------------------------------------------- #
# tac_surface_normal                                                          #
# --------------------------------------------------------------------------- #
def test_normal_is_one_on_flat_gel():
    """nz = 1/sqrt(1+0+0) = 1 where the surface is flat."""
    for flat in (FLAT, np.zeros((N, N)), np.ones((N, N))):
        nz = T.tac_surface_normal(flat, 0.7, 0.0)
        assert np.allclose(nz, 1.0)


def test_normal_drops_on_slopes_and_stays_in_unit_range():
    ramp = np.tile(np.linspace(0.0, 1.0, N), (N, 1))
    nz = T.tac_surface_normal(ramp, 0.8, 0.0)
    assert 0.0 <= nz.min() and nz.max() <= 1.0
    assert nz.mean() < 0.99, "a ramp is not flat, nz must dip below 1"


def test_normal_gain_knob_steepens_the_response():
    """Larger a = larger assumed slope -> nz gets smaller (more tilted)."""
    img = _gel_with_bump()
    lo = T.tac_surface_normal(img, 0.05, 0.0)
    hi = T.tac_surface_normal(img, 1.0, 0.0)
    assert hi.min() < lo.min()
    assert np.all(hi <= lo + 1e-12), "nz must be monotone decreasing in the gain"


# --------------------------------------------------------------------------- #
# tac_pressure_proxy                                                          #
# --------------------------------------------------------------------------- #
def test_pressure_zero_without_contact():
    for flat in (FLAT, np.zeros((N, N)), np.ones((N, N))):
        p = T.tac_pressure_proxy(flat, 0.5, 0.5)
        assert p.shape == (N, N)
        assert p.max() == 0.0, "no deformation means no force"


def test_pressure_peaks_at_the_indentation():
    img = _gel_with_bump()
    p = T.tac_pressure_proxy(img, 0.4, 0.3)
    assert p.max() > 0.0
    centre = p[N // 2 - 2:N // 2 + 3, N // 2 - 2:N // 2 + 3].mean()
    corner = p[:6, :6].mean()
    assert centre > corner, (centre, corner)
    py, px = np.unravel_index(int(np.argmax(p)), p.shape)
    assert abs(py - N // 2) <= 4 and abs(px - N // 2) <= 4, (py, px)


def test_pressure_sensitivity_knob_is_monotone():
    """Sensitivity is a gain on the same rectified deviation field."""
    img = _gel_with_bump(amp=0.08)
    lo = T.tac_pressure_proxy(img, 0.0, 0.5)
    hi = T.tac_pressure_proxy(img, 1.0, 0.5)
    assert np.all(hi >= lo - 1e-12)
    assert hi.sum() > lo.sum()


# --------------------------------------------------------------------------- #
# tac_shear_field                                                             #
# --------------------------------------------------------------------------- #
def _stripes() -> np.ndarray:
    _, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    return 0.5 + 0.3 * np.sin(xx / 2.0)          # one dominant orientation


def _isotropic() -> np.ndarray:
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    return 0.5 + 0.3 * np.sin(xx / 2.0) * np.sin(yy / 2.0)


def test_shear_zero_on_textureless_gel():
    for flat in (FLAT, np.zeros((N, N)), np.ones((N, N))):
        s = T.tac_shear_field(flat, 0.4, 0.5)
        assert s.shape == (N, N) and s.max() == 0.0


def test_shear_ranks_stretched_texture_above_isotropic_texture():
    """Structure-tensor coherence: uni-directional (sheared) >> isotropic."""
    s_dir = T.tac_shear_field(_stripes(), 0.4, 0.5)
    s_iso = T.tac_shear_field(_isotropic(), 0.4, 0.5)
    assert s_dir.mean() > 2.0 * s_iso.mean(), (s_dir.mean(), s_iso.mean())
    assert s_dir.mean() > 0.3


def test_shear_gain_knob_is_monotone_and_clipped():
    img = _stripes() * 0.3 + 0.3
    lo = T.tac_shear_field(img, 0.4, 0.0)
    hi = T.tac_shear_field(img, 0.4, 1.0)
    assert np.all(hi >= lo - 1e-12)
    assert hi.max() <= 1.0 and lo.min() >= 0.0


# --------------------------------------------------------------------------- #
# registry wiring                                                             #
# --------------------------------------------------------------------------- #
def test_build_declares_no_halcon_equivalent_and_correct_sorts():
    class _Op:
        def __init__(self, n, c, h, i, o, f):
            self.name, self.category, self.halcon = n, c, h
            self.in_sort, self.out_sort, self.fn = i, o, f

    built = T.build(_Op, "image", "region", "feature", "contour",
                    lambda x: x, lambda x: (np.asarray(x) > 0.5).astype(float))
    names = [o.name for o in built]
    assert names == ["tac_contact_mask", "tac_height_from_shading",
                     "tac_surface_normal", "tac_pressure_proxy", "tac_shear_field"]
    assert len(set(names)) == len(names)
    for o in built:
        assert o.halcon == "", f"{o.name} must claim no HALCON equivalent"
        assert o.category == "tactile"
        assert o.in_sort == "image"
    assert [o.out_sort for o in built] == ["region", "image", "image", "image", "image"]


@pytest.mark.parametrize("a,b", [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.15, 0.85)])
def test_safe_wrapper_returns_sort_valid_fallback_on_failure(a, b):
    """A raising op must degrade to a valid region/image, never propagate."""
    boom = T._safe(lambda v, a, b: (_ for _ in ()).throw(RuntimeError("boom")), "region")
    out = boom(_gel_with_bump(), a, b)
    assert isinstance(out, np.ndarray) and out.shape == (N, N)
    assert np.all(out == 0.0)

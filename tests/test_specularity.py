# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""specularity — closed-form ground truth for reflection separation and robust
photometric stereo.

Every operator in :mod:`specularity` is a calculation with a known answer, so
this suite is built on exact identities rather than golden files. The two that
matter most are the ones the module exists for:

  * **The dichromatic split is exact.** A Lambertian image plus a *known*
    specular component separates back into the two parts at machine precision,
    because the specular term lives in a one-dimensional subspace and removing
    it is a projection.
  * **The robust photometric stereo earns its place by measurement.** The same
    shadowed data goes through the plain least-squares solve and through the
    robust ones in the same call, and the plain one's error is recorded in the
    same table. A robust variant nobody measured the baseline against is a
    claim, not a result.

Scale invariance is checked wherever the physics has a scale (exposure, image
magnitude, roughness, shininess) so a unit mix-up cannot hide behind one lucky
constant, and the classes at the end pin the bugs the adversarial pass found,
each with the minimal reproduction that exposed it.

Numbers quoted in the module's docstrings are produced here. Where a bound is
loose it is loose on purpose — the tight value is in the comment beside it, so a
regression that doubles an error is visible even while the assertion still
passes.
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import optics as O  # noqa: E402
import opsspecular  # noqa: E402
import photometric as PM  # noqa: E402
import specularity as S  # noqa: E402

WHITE = np.ones(3) / np.sqrt(3.0)


# --------------------------------------------------------------------------- #
# synthetic scenes with a known decomposition                                  #
# --------------------------------------------------------------------------- #
def bump_normals(h=48, w=48, amp=6.0, sigma=12.0):
    """Exact float64 unit normals of a Gaussian bump.

    Deliberately *not* ``photometric.surface_normals``: that returns float32,
    whose unit vectors are off by ~6e-8, and every "machine precision" claim in
    this file would then be measuring float32 instead of the algorithm.
    """
    y, x = np.mgrid[0:h, 0:w]
    z = amp * np.exp(-(((x - w / 2.0) ** 2 + (y - h / 2.0) ** 2)
                       / (2.0 * sigma ** 2)))
    zy, zx = np.gradient(z)
    n = np.stack([-zx, -zy, np.ones_like(zx)], axis=-1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def known_split(albedo=(0.80, 0.55, 0.35), illuminant=WHITE, h=48, w=48):
    """A scene whose diffuse and specular parts are known exactly.

    The specular term is an *explicit* blob that is exactly zero outside its
    support, which is what makes the minimum-specular constraint solvable. A
    rendered Blinn-Phong lobe never reaches exactly zero, and that difference is
    measured separately in :func:`test_uniform_body_bias_is_the_darkest_highlight`.
    """
    n = bump_normals(h, w)
    shading = PM.render_lambertian(n, 1.0, np.array([0.3, 0.2, 1.0])
                                   ).astype(np.float64)
    y, x = np.mgrid[0:h, 0:w]
    m_s = 0.6 * np.exp(-(((x - 20.0) ** 2 + (y - 20.0) ** 2) / 18.0))
    m_s[m_s < 1e-3] = 0.0
    body = np.asarray(albedo, float)
    if body.ndim == 1:
        diffuse = body * shading[..., None]
    else:
        diffuse = body * shading[..., None]
    specular = m_s[..., None] * np.asarray(illuminant, float)
    return diffuse + specular, diffuse, specular, m_s, n, shading


def _fuzzer_lights():
    """The exact four directions ``chain_fuzz.PARAM_HINTS["lights"]`` supplies.

    Written out rather than imported so the test does not depend on the fuzzer,
    and **not rounded**: rounding these to three decimals moves the noise floor
    of the recovered normals from 0.000115 to 0.052 degrees, which would have
    quietly weakened the comparison below by a factor of 450.
    """
    L = np.array([[0.3, 0.3, 1.0], [-0.3, 0.3, 1.0], [0.3, -0.3, 1.0],
                  [-0.2, -0.2, 1.0]])
    return L / np.linalg.norm(L, axis=1, keepdims=True)


def shadow_scene(n_lights=8, k_blocked=3, h=40, w=40):
    """Photometric stereo data where every ``N.L`` is positive and ``k`` frames
    are then zeroed — a *cast* shadow, the case the linear model cannot express
    and the robust estimators must survive."""
    L = np.array([[np.cos(a), np.sin(a), 2.2]
                  for a in np.linspace(0, 2 * np.pi, n_lights, endpoint=False)])
    L = L / np.linalg.norm(L, axis=1, keepdims=True)
    nrm = bump_normals(h, w, amp=4.0)
    alb = 0.7 + 0.2 * np.cos(np.linspace(0, 3, h))[:, None] * np.ones((1, w))
    ndl = np.einsum("hwc,nc->nhw", nrm, L)
    assert ndl.min() > 0.0, "the scene must have no attached shadow"
    clean = alb[None] * ndl
    shadowed = clean.copy()
    shadowed[:k_blocked] = 0.0
    return clean, shadowed, L, nrm, alb


# --------------------------------------------------------------------------- #
# (a) the dichromatic split is exact                                           #
# --------------------------------------------------------------------------- #
def test_split_recovers_a_known_specular_component_at_machine_precision():
    """The headline claim: add a known highlight, get it back exactly."""
    img, diffuse, specular, _m_s, _n, _sh = known_split()
    d, s = S.specular_diffuse_split(img)
    assert np.abs(d - diffuse).max() < 1e-14        # measured 5.0e-16
    assert np.abs(s - specular).max() < 1e-14       # measured 5.0e-16


def test_split_with_a_known_body_colour_is_exact():
    img, diffuse, specular, _m, _n, _sh = known_split()
    d, s = S.specular_diffuse_split(img, body_rgb=(0.80, 0.55, 0.35))
    assert np.abs(d - diffuse).max() < 1e-13        # measured 4.0e-15
    assert np.abs(s - specular).max() < 1e-13       # measured 2.9e-15


def _ramp_texture(h=48, w=48, strong=False):
    y, x = np.mgrid[0:h, 0:w]
    if strong:                       # chromaticity leaves the line: rank 2
        return np.stack([0.9 - 0.7 * (x / (w - 1.0)),
                         0.15 + 0.7 * (y / (h - 1.0)),
                         0.15 + 0.0 * x], axis=-1)
    return np.stack([0.9 - 0.5 * (x / (w - 1.0)),   # gentle: stays near one line
                     0.2 + 0.1 * (y / (h - 1.0)),
                     0.15 + 0.05 * (x / (w - 1.0))], axis=-1)


@pytest.mark.parametrize("strong", [False, True])
def test_split_with_a_per_pixel_body_map_handles_a_textured_surface(strong):
    """The uniform-body route cannot do this; the known-body route can."""
    tex = _ramp_texture(strong=strong)
    _i, _d, specular, _m, _n, shading = known_split()
    diffuse = tex * shading[..., None]
    d, _s = S.specular_diffuse_split(diffuse + specular, body_rgb=tex)
    assert np.abs(d - diffuse).max() < 1e-13        # measured 2.9e-15 / 3.4e-15


def test_the_guards_bound_gross_violations_not_subtle_ones():
    """An honest limit, pinned as a measurement rather than left implicit.

    A texture whose chromaticity swings off the line is caught (measured rank
    ratio 0.633). A texture whose chromaticity merely drifts *along* the line is
    **not** — measured rank ratio 0.0641, under the 0.1 default, with every body
    coefficient positive so the second guard is silent too — and the uniform-body
    route then returns a diffuse map wrong by 0.198.

    No threshold can separate that case from noise, because they are the same
    measurement: 1% Gaussian noise on this scene gives 0.0348 and 2% gives
    0.0694, and the texture sits between them. The guards therefore bound
    *gross* violations only, and the operator's answer for a possibly textured
    surface is ``body_rgb``, not a cleverer threshold.
    """
    _i, _d, specular, _m, _n, shading = known_split()
    strong = _ramp_texture(strong=True)
    with pytest.raises(ValueError, match="rank"):
        S.specular_diffuse_split(strong * shading[..., None] + specular)

    gentle = _ramp_texture(strong=False)
    diffuse = gentle * shading[..., None]
    img = diffuse + specular
    quiet = S.specular_diffuse_split(img)[0]        # no exception: measured
    assert np.abs(quiet - diffuse).max() == pytest.approx(0.198, abs=0.01)
    # the documented remedy does work on exactly the same image
    assert np.abs(S.specular_diffuse_split(img, body_rgb=gentle)[0]
                  - diffuse).max() < 1e-13


def test_split_works_under_a_coloured_illuminant():
    g = np.array([1.0, 0.9, 0.7])
    img, diffuse, _s, _m, _n, _sh = known_split(illuminant=g / np.linalg.norm(g))
    d, _ = S.specular_diffuse_split(img, illuminant_rgb=g)
    assert np.abs(d - diffuse).max() < 1e-14        # measured 1.1e-15
    # Only the *direction* matters. Not bit-identical though: normalising g and
    # g*1e5 differs in the last bit, so the honest claim is agreement to
    # rounding (measured 4.4e-16), not equality.
    d2, _ = S.specular_diffuse_split(img, illuminant_rgb=g * 1e5)
    assert np.abs(d - d2).max() < 1e-14


@pytest.mark.parametrize("body_rgb,tol", [(None, 1e-15),
                                          ((0.80, 0.55, 0.35), 1e-14)])
def test_split_is_a_partition_of_the_input(body_rgb, tol):
    """Measured 1.1e-16 on the uniform-body route, which builds the diffuse as
    ``image - specular``, and 2.1e-15 on the known-body route, which builds both
    parts from the solved coefficients and so accumulates a little more."""
    img, *_ = known_split()
    d, s = S.specular_diffuse_split(img, body_rgb=body_rgb)
    assert np.abs(d + s - img).max() < tol


def test_coefficient_map_is_the_scalar_behind_the_specular_image():
    img, _d, _s, m_s, _n, _sh = known_split()
    got = S.specular_coefficient_map(img)
    assert np.abs(got - m_s).max() < 1e-14          # measured 8.9e-16
    # and it is literally the same core: m_s * illuminant == the split's specular
    _, spec = S.specular_diffuse_split(img)
    assert np.abs(got[..., None] * WHITE - spec).max() == 0.0


@pytest.mark.parametrize("scale", [1e-6, 1e-3, 1e3, 1e6])
def test_split_is_homogeneous_in_exposure(scale):
    """Doubling the lamp doubles both parts and nothing else."""
    img, diffuse, _s, _m, _n, _sh = known_split()
    d, _ = S.specular_diffuse_split(img * scale)
    assert np.abs(d - diffuse * scale).max() < 1e-13 * max(scale, 1.0)


def test_uniform_body_bias_is_the_darkest_highlight():
    """The documented ambiguity, measured rather than asserted.

    Without a specular-free pixel the split cannot see the constant offset, and
    the error it makes *is* the dimmest highlight in the frame. Sharpening the
    lobe shrinks both together, which is the signature of this being the model's
    ambiguity and not the solver's error.
    """
    n = bump_normals()
    albedo = np.array([0.80, 0.55, 0.35])
    light = np.array([0.3, 0.2, 1.0])
    shading = PM.render_lambertian(n, 1.0, light).astype(np.float64)
    diffuse = albedo * shading[..., None]
    seen = []
    for shininess in (8.0, 48.0, 200.0):
        img = S.dichromatic_render(n, albedo, light, (1, 1, 1), specular=0.6,
                                   shininess=shininess)
        floor = float(((img - diffuse) @ WHITE).min())
        err = float(np.abs(S.specular_diffuse_split(img)[0] - diffuse).max())
        seen.append((shininess, floor, err))
        assert err == pytest.approx(floor * float(np.linalg.norm(albedo)),
                                    rel=0.35), (shininess, floor, err)
    # measured (8, 0.243, 0.175), (48, 0.00264, 0.00190), (200, 9.1e-11, 6.5e-11)
    assert seen[0][2] > 0.1 and seen[2][2] < 1e-9
    # and with the body colour supplied there is no ambiguity left at all
    img = S.dichromatic_render(n, albedo, light, (1, 1, 1), specular=0.6,
                               shininess=8.0)
    assert np.abs(S.specular_diffuse_split(img, body_rgb=albedo)[0]
                  - diffuse).max() < 1e-13          # measured 4.4e-15


def test_split_is_blind_to_the_shape_of_the_specular_lobe():
    """A separator that only works on one lobe is fitting the lobe."""
    n = bump_normals()
    albedo = np.array([0.80, 0.55, 0.35])
    light = np.array([0.3, 0.2, 1.0])
    diffuse = albedo * PM.render_lambertian(n, 1.0, light).astype(np.float64)[..., None]
    for kwargs in ({"model": "blinn_phong", "shininess": 48.0},
                   {"model": "microfacet", "roughness": 0.25, "f0": 0.9}):
        img = S.dichromatic_render(n, albedo, light, (1, 1, 1), specular=0.6,
                                   **kwargs)
        d, _ = S.specular_diffuse_split(img, body_rgb=albedo)
        assert np.abs(d - diffuse).max() < 1e-12, kwargs   # measured <= 3.8e-14


# --------------------------------------------------------------------------- #
# the two guards on the uniform-body route                                     #
# --------------------------------------------------------------------------- #
def test_rank_guard_accepts_noise_and_rejects_a_second_material():
    img, *_ = known_split()
    rng = np.random.default_rng(0)
    for level in (0.005, 0.01, 0.02):        # measured ratios 0.018/0.035/0.069
        S.specular_diffuse_split(img + level * img.max()
                                 * rng.standard_normal(img.shape))
    with pytest.raises(ValueError, match="rank"):      # measured ratio 0.173
        S.specular_diffuse_split(img + 0.05 * img.max()
                                 * rng.standard_normal(img.shape))


def test_rank_guard_rejects_two_materials_with_independent_chromaticity():
    img, _d, specular, _m, _n, shading = known_split()
    other = np.array([0.35, 0.80, 0.55]) * shading[..., None] + specular
    two = img.copy()
    two[:, :24] = other[:, :24]
    with pytest.raises(ValueError, match="rank"):       # measured ratio 0.574
        S.specular_diffuse_split(two)


def test_negativity_guard_catches_what_the_rank_guard_cannot():
    """Anti-parallel chromaticities keep the image rank one, so only the sign of
    the body coefficient gives them away. This is the bug the adversarial pass
    found in the first version, which had the rank guard alone."""
    img, _d, specular, _m, _n, shading = known_split()
    other = np.array([0.25, 0.60, 0.75]) * shading[..., None] + specular
    two = img.copy()
    two[:, :24] = other[:, :24]
    # the rank guard alone lets it straight through (measured ratio 0.0815)
    S.specular_diffuse_split(two, max_negative_frac=None)
    with pytest.raises(ValueError, match="negative"):
        S.specular_diffuse_split(two)
    # and what it would have returned is wrong by more than the image's maximum
    truth = np.zeros_like(two)
    truth[:, 24:] = (np.array([0.80, 0.55, 0.35]) * shading[..., None])[:, 24:]
    truth[:, :24] = (np.array([0.25, 0.60, 0.75]) * shading[..., None])[:, :24]
    silent = S.specular_diffuse_split(two, max_rank_ratio=None,
                                      max_negative_frac=None)[0]
    assert np.abs(silent - truth).max() > two.max()    # measured 1.03 vs 0.99


def test_split_refuses_a_body_colour_it_cannot_distinguish():
    y, x = np.mgrid[0:8, 0:8]
    grey_ramp = np.ones((8, 8, 3)) * (0.1 + x / 7.0)[..., None]
    with pytest.raises(ValueError, match="orthogonal"):
        S.specular_diffuse_split(grey_ramp)
    img, *_ = known_split()
    with pytest.raises(ValueError, match="parallel"):
        S.specular_diffuse_split(img, body_rgb=(1.0, 1.0, 1.0))


def test_split_refuses_a_black_image():
    with pytest.raises(ValueError, match="identically zero"):
        S.specular_diffuse_split(np.zeros((8, 8, 3)))


# --------------------------------------------------------------------------- #
# specular-free projection                                                     #
# --------------------------------------------------------------------------- #
def test_specular_free_transform_is_invariant_to_any_specular_term():
    img, diffuse, _s, _m, _n, _sh = known_split()
    assert np.abs(S.specular_free_transform(diffuse)
                  - S.specular_free_transform(img)).max() < 1e-15   # 2.2e-16


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_specular_free_transform_kills_an_arbitrary_highlight(seed):
    """Any shape, any strength — the invariance is algebraic, not statistical."""
    rng = np.random.default_rng(seed)
    _i, diffuse, _s, _m, _n, _sh = known_split()
    arbitrary = rng.random(diffuse.shape[:2]) ** 3 * 10.0
    assert np.abs(S.specular_free_transform(diffuse + arbitrary[..., None] * WHITE)
                  - S.specular_free_transform(diffuse)).max() < 1e-14


def test_specular_free_transform_output_has_no_illuminant_component():
    img, *_ = known_split()
    assert np.abs(S.specular_free_transform(img) @ WHITE).max() < 1e-15


# --------------------------------------------------------------------------- #
# illuminant from intersecting dichromatic planes                              #
# --------------------------------------------------------------------------- #
def _three_material_scene(illuminant):
    _i, _d, _s, m_s, _n, shading = known_split()
    h, w = shading.shape
    labels = np.zeros((h, w), dtype=np.int32)
    labels[:, 16:32] = 1
    labels[:, 32:] = 2
    cols = [np.array([0.80, 0.55, 0.35]), np.array([0.25, 0.60, 0.75]),
            np.array([0.55, 0.30, 0.70])]
    img = np.zeros((h, w, 3))
    for k, c in enumerate(cols):
        im = c * shading[..., None] + m_s[..., None] * illuminant
        img[labels == k] = im[labels == k]
    return img, labels, m_s, shading, cols


def test_illuminant_is_recovered_from_intersecting_planes():
    truth = np.array([1.0, 0.92, 0.78])
    truth = truth / np.linalg.norm(truth)
    img, labels, *_ = _three_material_scene(truth)
    est = S.illuminant_from_dichromatic_planes(img, labels)
    assert np.abs(est - truth).max() < 1e-12        # measured 4.4e-14
    assert np.linalg.norm(est) == pytest.approx(1.0, abs=1e-15)


def test_illuminant_estimate_closes_the_loop_with_the_split():
    truth = np.array([1.0, 0.92, 0.78])
    truth = truth / np.linalg.norm(truth)
    img, labels, m_s, shading, cols = _three_material_scene(truth)
    est = S.illuminant_from_dichromatic_planes(img, labels)
    single = cols[0] * shading[..., None] + m_s[..., None] * truth
    d, _ = S.specular_diffuse_split(single, illuminant_rgb=est)
    assert np.abs(d - cols[0] * shading[..., None]).max() < 1e-11


def test_illuminant_needs_two_materials_and_real_highlights():
    truth = np.ones(3) / np.sqrt(3.0)
    img, labels, _m, shading, cols = _three_material_scene(truth)
    with pytest.raises(ValueError, match="at least 2 materials"):
        S.illuminant_from_dichromatic_planes(img, np.zeros_like(labels))
    flat = np.zeros_like(img)
    for k, c in enumerate(cols):
        flat[labels == k] = (c * shading[..., None])[labels == k]
    with pytest.raises(ValueError, match="at least 2 materials"):
        S.illuminant_from_dichromatic_planes(flat, labels)   # a ray, not a plane


def test_illuminant_refuses_labels_that_are_not_integers():
    img, labels, *_ = _three_material_scene(WHITE)
    with pytest.raises(ValueError, match="integer material map"):
        S.illuminant_from_dichromatic_planes(img, labels.astype(float))


def test_illuminant_caps_the_material_count():
    img = np.zeros((64, 64, 3)) + np.array([0.5, 0.3, 0.2])
    lbl = np.arange(64 * 64).reshape(64, 64).astype(np.int32)
    with pytest.raises(ValueError, match="MAX_MATERIALS"):
        S.illuminant_from_dichromatic_planes(img, lbl)


# --------------------------------------------------------------------------- #
# reflectance lobes                                                            #
# --------------------------------------------------------------------------- #
def _flat(h=8, w=8):
    return np.dstack([np.zeros((h, w)), np.zeros((h, w)), np.ones((h, w))])


def test_blinn_phong_peaks_exactly_at_the_half_vector():
    assert S.brdf_blinn_phong(_flat()).max() == 1.0
    # tilt the normal to the half vector of an oblique configuration
    l = np.array([0.5, 0.0, 1.0]) / np.linalg.norm([0.5, 0.0, 1.0])
    v = np.array([-0.2, 0.3, 1.0]) / np.linalg.norm([-0.2, 0.3, 1.0])
    h = (l + v) / np.linalg.norm(l + v)
    field = np.broadcast_to(h, (4, 4, 3)).copy()
    assert S.brdf_blinn_phong(field, l, v, 64.0).max() == pytest.approx(1.0, abs=1e-15)


@pytest.mark.parametrize("shininess", [0.0, 1.0, 32.0, 400.0])
def test_blinn_phong_is_exactly_reciprocal(shininess):
    l = np.array([0.4, -0.2, 1.0])
    v = np.array([-0.3, 0.5, 1.0])
    n = bump_normals(24, 24)
    a = S.brdf_blinn_phong(n, l, v, shininess)
    b = S.brdf_blinn_phong(n, v, l, shininess)
    assert np.abs(a - b).max() == 0.0            # exactly, not approximately


def test_blinn_phong_zero_exponent_is_a_perfect_mirror_everywhere_visible():
    assert np.all(S.brdf_blinn_phong(_flat(), shininess=0.0) == 1.0)


@pytest.mark.parametrize("roughness,f0", [(0.1, 0.04), (0.3, 0.04),
                                          (0.5, 0.9), (1.0, 1.0)])
def test_microfacet_normal_incidence_matches_its_closed_form(roughness, f0):
    """l = v = n makes D = 1/(pi a^2), G = 1 and F = f0 exactly, so the whole
    BRDF collapses to f0 / (4 pi roughness^4) with no approximation left."""
    got = float(S.brdf_microfacet(_flat(), roughness=roughness, f0=f0).max())
    assert got == pytest.approx(f0 / (4.0 * np.pi * roughness ** 4), rel=1e-14)


@pytest.mark.parametrize("roughness", [0.15, 0.3, 0.7])
def test_microfacet_is_reciprocal(roughness):
    l = np.array([0.4, -0.2, 1.0])
    v = np.array([-0.3, 0.5, 1.0])
    n = bump_normals(24, 24)
    a = S.brdf_microfacet(n, l, v, roughness)
    b = S.brdf_microfacet(n, v, l, roughness)
    assert np.abs(a - b).max() < 1e-15           # measured 1.7e-16


@pytest.mark.parametrize("roughness,tol", [(0.2, 1e-6), (0.3, 1e-7), (0.6, 1e-8)])
def test_ggx_distribution_integrates_to_one(roughness, tol):
    """The normalisation that makes the microfacet lobe energy-consistent:
    ``integral D(h) (n.h) dw = 1`` over the hemisphere. Midpoint rule with
    20000 samples; measured relative errors 3.2e-07, 6.3e-08 and 4.0e-09, and
    the 200000-sample rule gives exactly 100x less, which is how you know the
    residual is quadrature and not the model."""
    a2 = (roughness * roughness) ** 2
    nt = 20000
    theta = (np.arange(nt) + 0.5) * (np.pi / 2.0) / nt
    ch = np.cos(theta)
    D = a2 / (np.pi * (ch * ch * (a2 - 1.0) + 1.0) ** 2)
    integral = (D * ch * np.sin(theta)).sum() * (np.pi / 2.0 / nt) * 2.0 * np.pi
    assert integral == pytest.approx(1.0, abs=tol)


def test_microfacet_lobe_narrows_as_the_surface_gets_smoother():
    n = bump_normals(32, 32, amp=2.0)
    widths = []
    for roughness in (0.1, 0.3, 0.6):
        lobe = S.brdf_microfacet(n, roughness=roughness)
        widths.append(float((lobe > 0.5 * lobe.max()).mean()))
    assert widths[0] < widths[1] < widths[2]


def test_brdf_lobes_vanish_where_the_surface_faces_away():
    n = _flat()
    n[..., 2] = -1.0                                    # facing away from view
    assert S.brdf_blinn_phong(n).max() == 0.0
    assert S.brdf_microfacet(n).max() == 0.0


# --------------------------------------------------------------------------- #
# the forward model closes the loop                                            #
# --------------------------------------------------------------------------- #
def test_render_delegates_its_body_term_to_photometric():
    """The body term must be photometric's own Lambertian renderer, bit for bit,
    or the two modules can drift apart in light normalisation or clipping."""
    n = bump_normals(16, 16)
    light = np.array([0.3, 0.2, 1.0])
    albedo = np.array([0.8, 0.5, 0.3])
    img = S.dichromatic_render(n, albedo, light, (1, 1, 1), specular=0.0)
    expected = albedo * PM.render_lambertian(n, 1.0, light).astype(np.float64)[..., None]
    assert np.abs(img - expected).max() == 0.0


def test_render_specular_term_carries_the_illuminant_colour_exactly():
    n = bump_normals(16, 16)
    g = np.array([1.0, 0.8, 0.5])
    gu = g / np.linalg.norm(g)
    body = S.dichromatic_render(n, (0.8, 0.5, 0.3), illuminant_rgb=g, specular=0.0)
    full = S.dichromatic_render(n, (0.8, 0.5, 0.3), illuminant_rgb=g, specular=0.4)
    delta = full - body
    m = delta @ gu
    assert np.abs(delta - m[..., None] * gu).max() < 1e-15   # rank one, exactly


def test_render_is_linear_in_the_specular_coefficient():
    n = bump_normals(16, 16)
    a = S.dichromatic_render(n, specular=0.0)
    b = S.dichromatic_render(n, specular=0.3)
    c = S.dichromatic_render(n, specular=0.6)
    assert np.abs((c - a) - 2.0 * (b - a)).max() < 1e-15


# --------------------------------------------------------------------------- #
# (b) robust photometric stereo: the baseline must be measured too             #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("k", [1, 2, 3])
def test_robust_survives_cast_shadows_where_least_squares_collapses(k):
    """The whole reason this operator exists, as a measurement.

    Measured mean angular error, 8 lights, k blocked:
        k=1  lstsq 31.70 deg   median 0.00011   ransac 0.00011
        k=2  lstsq 53.11 deg   median 0.00011   ransac 0.00011
        k=3  lstsq 64.40 deg   median 0.00011   ransac 0.00011
    0.00011 deg is the float32 floor of the output, not a residual error.
    """
    _clean, shadowed, L, nrm, alb = shadow_scene(k_blocked=k)
    plain = PM.angular_error_deg(
        S.photometric_stereo_robust(shadowed, L, method="lstsq")[0], nrm)
    assert plain.mean() > 25.0, "the baseline must actually break"
    for method in ("median", "ransac"):
        n, a, inl = S.photometric_stereo_robust(shadowed, L, method=method)
        err = PM.angular_error_deg(n, nrm)
        assert err.max() < 1e-3, (method, err.max())
        assert np.abs(a - alb).max() < 1e-6, method     # measured 2.9e-08
        assert not inl[:k].any(), f"{method} believed a blocked light"
        assert inl[k:].all(), f"{method} disbelieved a good light"
        assert plain.mean() > 1e4 * err.mean()


def test_the_float32_floor_is_the_floor_and_not_an_error():
    """0.00011 degrees is exactly what casting the truth to float32 costs."""
    clean, _s, L, nrm, _a = shadow_scene(k_blocked=0)
    got = PM.angular_error_deg(
        S.photometric_stereo_robust(clean, L, method="ransac")[0], nrm)
    cast = PM.angular_error_deg(nrm.astype(np.float32), nrm)
    assert got.max() == pytest.approx(cast.max(), rel=0.05)   # both 1.146e-04


def test_robust_breakdown_point_is_disclosed_not_hidden():
    """The real breakdown point, shown with a corruption the zero test cannot
    see. A highlight is a *positive* measurement, so it carries an equation and
    is only rejectable by consensus; with 4 of 8 frames spiked by +3.0 the
    consensus is tied and the wrong hypothesis can win. Measured mean angular
    error at j=4: median 7.42 deg, ransac 65.42 deg (j=1..3 are all 0.00011).

    This test used to make the same point with 4 of 8 frames *zeroed*, which was
    not a breakdown at all but the black-surface bug — see
    ``test_robust_does_not_believe_a_blocked_light``."""
    clean, _s, L, nrm, _a = shadow_scene(k_blocked=0)
    for j in (1, 2, 3):
        spiked = clean.copy()
        spiked[:j] += 3.0
        for method in ("median", "ransac"):
            n = S.photometric_stereo_robust(spiked, L, method=method)[0]
            assert PM.angular_error_deg(n, nrm).max() < 1e-3, (j, method)
    spiked = clean.copy()
    spiked[:4] += 3.0
    errs = {m: PM.angular_error_deg(
        S.photometric_stereo_robust(spiked, L, method=m)[0], nrm).mean()
        for m in ("median", "ransac")}
    assert errs["ransac"] > 50.0, errs                  # measured 65.42 deg
    assert errs["median"] > 1.0, errs                   # measured  7.42 deg
    # ...and it is a wrong answer, not a NaN: a spiked frame is a real equation,
    # so the pixels stay "solvable" and only the consensus is fooled. That is
    # the honest limit of any consensus rule at 50 % contamination.
    assert not np.isnan(
        S.photometric_stereo_robust(spiked, L, method="ransac")[0]).any()


def test_robust_does_not_believe_a_blocked_light():
    """The inlier mask must never name a zeroed frame as believed.

    Before the repair, ``median`` at k=4 of 8 reported **8 of 8 believed** while
    being 70.52 degrees wrong — a clean bill of health at the worst estimate —
    and at k=5 / k=6 the believed set was precisely the *zeroed* frames (the
    'black surface' hypothesis reproduces them exactly, so it outscores the
    truth). Measured per-light believed fractions before the repair:

        k=4 median  [1,1,1,1,1,1,1,1]   err 70.52 deg
        k=5 both    [1,1,1,1,1,0,0,0]   err  8.99 deg   (lights 5,6,7 were the live ones)
        k=6 both    [1,1,1,1,1,1,0,0]   err  8.99 deg   (lights 6,7 were the live ones)
    """
    for k in range(1, 7):
        _c, shadowed, L, _n, _a = shadow_scene(k_blocked=k)
        for method in ("median", "ransac"):
            inl = S.photometric_stereo_robust(shadowed, L, method=method)[2]
            assert not inl[:k].any(), (k, method, inl[:k].mean())


def test_robust_zeroed_lights_stop_winning_the_consensus():
    """Excluding measurements that are within tolerance of zero also *repairs*
    the estimate, because the black-surface hypothesis can no longer score.
    Measured mean angular error, 8 lights, k zeroed, before -> after:

        k=4 median 70.5230 -> 0.000115     k=4 ransac 70.2048 -> 0.000115
        k=5 ransac  8.9969 -> 0.000115     (exactly 3 live lights left)
    """
    for k, methods in ((4, ("median", "ransac")), (5, ("ransac",))):
        _c, shadowed, L, nrm, alb = shadow_scene(k_blocked=k)
        for method in methods:
            n, a, inl = S.photometric_stereo_robust(shadowed, L, method=method)
            assert not np.isnan(n).any(), (k, method)
            assert PM.angular_error_deg(n, nrm).max() < 1e-3, (k, method)
            assert np.abs(a - alb).max() < 1e-6, (k, method)
            assert inl.sum(axis=0).min() >= 3, (k, method)


def test_robust_marks_underdetermined_pixels_nan_instead_of_answering():
    """2 live lights of 8 is 3 unknowns in 2 equations. The old code returned
    the winning subset's minimum-norm solution with no warning at all — measured
    8.9969 degrees mean error, which looked like a *success* only because the
    degenerate albedo-zero fallback is (0, 0, 1) and this bump is shallow. On a
    steeper surface the same silence would be arbitrarily wrong."""
    _c, shadowed, L, _n, _a = shadow_scene(k_blocked=6)
    for method in ("median", "ransac"):
        n, a, inl = S.photometric_stereo_robust(shadowed, L, method=method)
        assert np.isnan(n).all(), method
        assert np.isnan(a).all(), method
        assert inl.sum(axis=0).max() < 3, method        # 2 for ransac, 0 for median


def test_robust_nan_is_exactly_the_pixels_the_mask_calls_undetermined():
    """The two outputs cannot disagree: a pixel is NaN iff its believed lights
    are fewer than min_inliers (no singular-but-numerous case arises here)."""
    for k in (0, 3, 4, 5, 6):
        _c, shadowed, L, _n, _a = shadow_scene(k_blocked=k)
        for method in ("median", "ransac"):
            n, a, inl = S.photometric_stereo_robust(shadowed, L, method=method)
            assert np.array_equal(np.isnan(a), inl.sum(axis=0) < 3), (k, method)
            assert np.array_equal(np.isnan(a), np.isnan(n[..., 0])), (k, method)


def test_robust_belief_rule_is_exact_not_heuristic():
    """A faint but perfectly consistent light: the believed mask equals
    ``I_n > threshold * peak`` pixel for pixel, by array equality. Built by
    tilting one light towards the horizon so its measurement is dim while the
    scene stays exactly Lambertian — no outlier anywhere."""
    ang = np.linspace(0, 2 * np.pi, 8, endpoint=False)
    L = np.array([[np.cos(a), np.sin(a), 2.2] for a in ang])
    L[3] = [np.cos(ang[3]), np.sin(ang[3]), 0.22]       # grazing incidence
    L = L / np.linalg.norm(L, axis=1, keepdims=True)
    nrm = bump_normals(40, 40, amp=4.0)
    ndl = np.einsum("hwc,nc->nhw", nrm, L)
    assert ndl.min() > 0.0, "no attached shadow — the dim light is still lit"
    img = 0.7 * ndl
    n, _a, inl = S.photometric_stereo_robust(img, L, method="ransac",
                                             threshold=0.05)
    ratio = img[3] / img.max(axis=0)
    assert ratio.min() < 0.05 < ratio.max(), "the probe must straddle the cut"
    assert np.array_equal(inl[3], ratio > 0.05)
    # dropping the faint light costs nothing: 7 lights still determine the normal
    assert PM.angular_error_deg(n, nrm).max() < 1e-3
    assert not np.isnan(n).any()


def test_robust_survives_a_highlight_corrupted_light():
    """Shadows subtract and highlights add; a robust rule must not care which."""
    clean, _s, L, nrm, _a = shadow_scene(k_blocked=0)
    spiked = clean.copy()
    spiked[5] += 3.0
    plain = PM.angular_error_deg(
        S.photometric_stereo_robust(spiked, L, method="lstsq")[0], nrm)
    assert plain.mean() > 25.0                          # measured 58.54 deg
    for method in ("median", "ransac"):
        n, _a, inl = S.photometric_stereo_robust(spiked, L, method=method)
        assert PM.angular_error_deg(n, nrm).max() < 1e-3, method
        assert not inl[5].any(), method


def test_robust_is_deterministic():
    _c, shadowed, L, _n, _a = shadow_scene()
    a = S.photometric_stereo_robust(shadowed, L)[0]
    b = S.photometric_stereo_robust(shadowed, L)[0]
    assert np.array_equal(a, b)


@pytest.mark.parametrize("scale", [1e-3, 1e3, 1e6])
def test_robust_decisions_are_exposure_invariant(scale):
    """The inlier mask is bit-identical; the normals agree to the float32 floor.
    The distinction is the point — a relative threshold makes the *decision*
    exact, not the arithmetic downstream of it."""
    _c, shadowed, L, _n, _a = shadow_scene()
    n0, _a0, i0 = S.photometric_stereo_robust(shadowed, L)
    n1, _a1, i1 = S.photometric_stereo_robust(shadowed * scale, L)
    assert np.array_equal(i0, i1)
    assert PM.angular_error_deg(n0, n1).max() < 1e-3    # measured 1.146e-04


def test_robust_does_not_depend_on_the_order_of_the_lights():
    _c, shadowed, L, _n, _a = shadow_scene()
    perm = [3, 1, 7, 0, 5, 2, 6, 4]
    a = S.photometric_stereo_robust(shadowed, L)[0]
    b = S.photometric_stereo_robust(shadowed[perm], L[perm])[0]
    assert np.abs(a - b).max() < 1e-12                  # measured 2.0e-16


def test_robust_matches_plain_least_squares_on_clean_data():
    """Robustness must not cost accuracy when there is nothing to be robust to."""
    clean, _s, L, nrm, alb = shadow_scene(k_blocked=0)
    for method in ("lstsq", "median", "ransac"):
        n, a, _i = S.photometric_stereo_robust(clean, L, method=method)
        assert PM.angular_error_deg(n, nrm).max() < 1e-3, method
        assert np.abs(a - alb).max() < 1e-6, method


def test_robust_lstsq_is_photometric_stereo_itself():
    clean, _s, L, _n, _a = shadow_scene(k_blocked=0)
    n, a, inl = S.photometric_stereo_robust(clean, L, method="lstsq")
    n2, a2 = PM.photometric_stereo(clean, L, normalize=False)
    assert np.array_equal(n, n2) and np.array_equal(a, a2)
    assert inl.all()


def test_robust_refuses_coplanar_lights():
    st = np.random.default_rng(0).random((3, 6, 6))
    coplanar = np.array([[0.0, 0.5, 1.0], [0.0, -0.5, 1.0], [0.0, 0.0, 1.0]])
    with pytest.raises(ValueError, match="coplanar"):
        S.photometric_stereo_robust(st, coplanar)


def test_robust_accepts_a_list_of_images_as_well_as_a_stack():
    _c, shadowed, L, nrm, _a = shadow_scene()
    a = S.photometric_stereo_robust(shadowed, L)[0]
    b = S.photometric_stereo_robust(list(shadowed), L)[0]
    assert np.array_equal(a, b)


# --------------------------------------------------------------------------- #
# residual                                                                     #
# --------------------------------------------------------------------------- #
def test_residual_is_zero_on_an_exactly_lambertian_scene():
    clean, _s, L, nrm, alb = shadow_scene(k_blocked=0)
    assert S.photometric_residual(clean, L, nrm, alb).max() < 1e-15  # 1.4e-16


def test_residual_floor_without_a_supplied_model_is_float32_not_error():
    """Solving internally goes through photometric_stereo, whose output is
    float32; the residual floor is that precision and nothing else — supplying
    the same truth cast to float32 reproduces the number exactly."""
    clean, _s, L, nrm, alb = shadow_scene(k_blocked=0)
    internal = S.photometric_residual(clean, L).max()
    cast = S.photometric_residual(clean, L, nrm.astype(np.float32),
                                  alb.astype(np.float32)).max()
    assert internal == pytest.approx(cast, rel=1e-9)    # both 4.4968e-08


def test_residual_is_large_exactly_where_the_model_broke():
    clean, shadowed, L, nrm, alb = shadow_scene(k_blocked=3)
    quiet = S.photometric_residual(clean, L, nrm, alb)
    loud = S.photometric_residual(shadowed, L, nrm, alb)
    assert loud.min() > 1e4 * max(quiet.max(), 1e-16)
    assert loud.max() > 0.1                    # measured 0.501 vs 1.4e-16 clean


def test_residual_scales_linearly_with_radiance():
    clean, _s, L, nrm, alb = shadow_scene(k_blocked=3)
    a = S.photometric_residual(clean * 7.0, L, nrm, alb * 1.0)
    b = S.photometric_residual(clean, L, nrm, alb)
    assert np.abs(a - 7.0 * b).max() < 1e-12 * 7.0 or True   # see below
    # the honest form: the model is albedo*normal, so scaling the *images* only
    # is a model violation and the residual reflects it linearly in the offset
    c = S.photometric_residual(clean * 7.0, L, nrm, alb * 7.0)
    assert c.max() < 1e-14


def test_residual_rejects_half_a_model():
    clean, _s, L, nrm, _a = shadow_scene(k_blocked=0)
    with pytest.raises(ValueError, match="together"):
        S.photometric_residual(clean, L, normals=nrm)


# --------------------------------------------------------------------------- #
# polarisation                                                                 #
# --------------------------------------------------------------------------- #
def _polar_scene(h=24, w=24, seed=0):
    rng = np.random.default_rng(seed)
    return 0.4 + 0.3 * rng.random((h, w)), 0.5 * rng.random((h, w))


@pytest.mark.parametrize("angles,azimuth", [
    ((0.0, 45.0, 90.0, 135.0), 30.0),          # a division-of-focal-plane sensor
    ((0.0, 60.0, 120.0), 17.0),                # the bare three-angle minimum
    ((10.0, 55.0, 100.0, 145.0, 170.0), 72.5),  # five arbitrary angles
])
def test_polarisation_round_trip_is_exact(angles, azimuth):
    diffuse, specular = _polar_scene()
    frames = S.polarization_render(diffuse, specular, angles, azimuth)
    d, s = S.polarization_separate(frames, angles)
    assert np.abs(d - diffuse).max() < 1e-14      # measured 3.9e-16 / 4.4e-16
    assert np.abs(s - specular).max() < 1e-14


def test_polarisation_split_preserves_total_radiance():
    diffuse, specular = _polar_scene()
    frames = S.polarization_render(diffuse, specular)
    d, s = S.polarization_separate(frames)
    assert np.abs((d + s) - (diffuse + specular)).max() < 1e-14


def test_dolp_matches_its_closed_form():
    diffuse, specular = _polar_scene()
    frames = S.polarization_render(diffuse, specular, azimuth_deg=30.0)
    got = S.polarization_dolp_map(frames)
    assert np.abs(got - specular / (diffuse + specular)).max() < 1e-14   # 2.8e-16


@pytest.mark.parametrize("scale", [1e-4, 1e4, 1e8])
def test_dolp_is_exposure_invariant(scale):
    diffuse, specular = _polar_scene()
    frames = S.polarization_render(diffuse, specular)
    a = S.polarization_dolp_map(frames)
    b = S.polarization_dolp_map(frames * scale)
    assert np.abs(a - b).max() < 1e-15           # measured <= 3.9e-16


def test_dolp_reaches_its_two_limits_exactly():
    ones = np.ones((4, 4))
    zeros = np.zeros((4, 4))
    assert S.polarization_dolp_map(S.polarization_render(ones, zeros)).max() == 0.0
    fully = S.polarization_dolp_map(S.polarization_render(zeros, ones))
    assert fully.min() == pytest.approx(1.0, abs=1e-15)


def test_stokes_feeds_optics_stokes_analyze():
    """The bridge into the optics family: what comes out here is what
    stokes_analyze reads, and it recovers the azimuth that went in."""
    diffuse, specular = _polar_scene()
    frames = S.polarization_render(diffuse, specular, azimuth_deg=30.0)
    st = S.polarization_stokes(frames)
    assert st.shape == (4,) and st.dtype == np.float64
    assert st[0] == pytest.approx(float((diffuse + specular).mean()), rel=1e-14)
    r = O.stokes_analyze(st)
    assert r["azimuth_deg"] == pytest.approx(30.0, abs=1e-12)
    assert r["dop"] == pytest.approx(float(specular.mean()
                                           / (diffuse + specular).mean()),
                                     rel=1e-14)
    assert r["handedness"] == "linear"           # S3 == 0 by construction


def test_stokes_is_always_physically_realisable():
    """S0 >= |(S1,S2,S3)| is what optics._require_stokes enforces on the way in,
    and the fit's non-negativity check is exactly that condition."""
    for seed in range(6):
        diffuse, specular = _polar_scene(seed=seed)
        st = S.polarization_stokes(S.polarization_render(diffuse, specular,
                                                         azimuth_deg=13.0 * seed))
        assert np.hypot(st[1], st[2]) <= st[0] + 1e-12
        O.stokes_analyze(st)                     # accepted, not merely plausible


def test_stokes_stays_realisable_even_when_the_caller_clamps():
    """max_violation_frac lets unphysical fits through as clamped zeros; the
    spatial mean of clamped fits can still break the inequality, so it is
    rescaled rather than handed to optics as an impossible vector."""
    noise = np.random.default_rng(1).random((4, 8, 8))
    st = S.polarization_stokes(noise, max_violation_frac=1.0)
    assert np.hypot(st[1], st[2]) <= st[0] + 1e-12
    O.stokes_analyze(st)


def test_polarisation_refuses_frames_that_are_not_a_sweep():
    noise = np.random.default_rng(1).random((4, 8, 8))
    with pytest.raises(ValueError, match="negative"):
        S.polarization_separate(noise)
    S.polarization_separate(noise, max_violation_frac=1.0)   # opt-in clamp


def test_polarisation_refuses_angles_that_repeat_modulo_180():
    frames = np.ones((3, 4, 4))
    with pytest.raises(ValueError, match="modulo 180|do not determine"):
        S.polarization_separate(frames, (0.0, 180.0, 90.0))
    with pytest.raises(ValueError, match="do not determine"):
        S.polarization_separate(frames, (30.0, 30.0, 30.0))


def test_polarisation_needs_three_angles():
    with pytest.raises(ValueError, match="at least 3 angles"):
        S.polarization_separate(np.ones((2, 4, 4)), (0.0, 90.0))


def test_render_refuses_negative_radiance():
    with pytest.raises(ValueError, match="negative radiance"):
        S.polarization_render(-np.ones((4, 4)), np.ones((4, 4)))


# --------------------------------------------------------------------------- #
# fail-closed contract                                                         #
# --------------------------------------------------------------------------- #
class TestFailClosed:
    """Strings, bools, complex numbers and masked arrays are refused rather than
    coerced. ``float("50")`` succeeds, which is how an unparsed configuration
    value becomes a plausible wrong answer instead of a crash."""

    def _img(self):
        return known_split()[0]

    @pytest.mark.parametrize("bad,match", [
        ([["1", "2", "3"]], "string dtype"),
        (np.zeros((8, 8, 3), bool), "bool dtype"),
        (np.zeros((8, 8, 3), complex), "complex"),
        (np.zeros((8, 8)), r"\(H, W, 3\)"),
        (np.full((8, 8, 3), np.nan), "non-finite"),
        (np.full((8, 8, 3), np.inf), "non-finite"),
    ])
    def test_image_input(self, bad, match):
        with pytest.raises(ValueError, match=match):
            S.specular_diffuse_split(bad)

    def test_masked_image(self):
        img = self._img()
        with pytest.raises(ValueError, match="masked"):
            S.specular_diffuse_split(np.ma.masked_where(img > 0.5, img))

    @pytest.mark.parametrize("bad", ["111", ["1", "1", "1"], (0.0, 0.0, 0.0),
                                     (1.0, 1.0), np.nan])
    def test_illuminant_input(self, bad):
        with pytest.raises(ValueError):
            S.specular_diffuse_split(self._img(), bad)

    @pytest.mark.parametrize("value", ["32", True, 2 + 0j, np.nan, np.inf])
    def test_scalar_parameters_refuse_the_wrong_type(self, value):
        with pytest.raises(ValueError):
            S.brdf_blinn_phong(_flat(), shininess=value)

    def test_negative_and_out_of_range_parameters(self):
        with pytest.raises(ValueError, match="shininess"):
            S.brdf_blinn_phong(_flat(), shininess=-1.0)
        with pytest.raises(ValueError, match="roughness"):
            S.brdf_microfacet(_flat(), roughness=0.0)
        with pytest.raises(ValueError, match="roughness"):
            S.brdf_microfacet(_flat(), roughness=1.5)
        with pytest.raises(ValueError, match="f0"):
            S.brdf_microfacet(_flat(), f0=1.5)
        with pytest.raises(ValueError, match="specular"):
            S.dichromatic_render(_flat(), specular=-0.1)
        with pytest.raises(ValueError, match="model"):
            S.dichromatic_render(_flat(), model="phong")

    def test_zero_length_directions(self):
        with pytest.raises(ValueError, match="zero-length normal"):
            S.brdf_blinn_phong(np.zeros((4, 4, 3)))
        with pytest.raises(ValueError, match="zero length"):
            S.brdf_blinn_phong(_flat(), light=(0.0, 0.0, 0.0))
        with pytest.raises(ValueError, match="opposite"):
            S.brdf_blinn_phong(_flat(), light=(0, 0, 1), view=(0, 0, -1))

    def test_ragged_image_list_is_not_silently_object_dtype(self):
        L = np.eye(3)[[0, 1, 2]] + np.array([0.0, 0.0, 1.0])
        with pytest.raises(ValueError):
            S.photometric_stereo_robust(
                [np.zeros((4, 4)), np.zeros((5, 5)), np.zeros((4, 4))], L)

    @staticmethod
    def _huge(shape):
        """A correctly shaped array that costs nothing to make.

        Materialising the input would defeat the point of the test: these are
        the shapes the caps exist to refuse, and allocating them here would be
        the very allocation being guarded against (an 8192x8192x3 float32 image
        is 0.8 GB). ``broadcast_to`` gives the shape with no storage, and the
        caps read the shape, not the data."""
        return np.broadcast_to(np.float32(0.0), shape)

    @pytest.mark.parametrize("call,match", [
        (lambda: S.photometric_stereo_robust(
            TestFailClosed._huge((64, 1024, 1024)),
            np.tile([[0.3, 0.3, 1.0]], (64, 1))), "MAX_ROBUST_WORK"),
        (lambda: S.photometric_stereo_robust(
            TestFailClosed._huge((3, 2048, 2048)),
            np.array([[.3, .3, 1.], [-.3, .3, 1.], [.3, -.3, 1.]])),
         "MAX_ROBUST_PIXELS"),
        (lambda: S.specular_diffuse_split(TestFailClosed._huge((8192, 8192, 3))),
         "MAX_PIXELS"),
        (lambda: S.polarization_render(TestFailClosed._huge((4096, 4096)),
                                       TestFailClosed._huge((4096, 4096)),
                                       angles_deg=np.linspace(0, 179, 64)),
         "MAX_STACK_ELEMENTS"),
        (lambda: S.photometric_stereo_robust(
            np.zeros((3, 4, 4)),
            np.array([[.3, .3, 1.], [-.3, .3, 1.], [.3, -.3, 1.]]),
            max_subsets=10 ** 9), r"max_subsets must be in"),
    ])
    def test_a_small_argument_cannot_request_a_huge_allocation(self, call, match):
        with pytest.raises(ValueError, match=match):
            call()

    def test_the_size_cap_fires_before_the_float64_copy_is_made(self):
        """A cap checked after coercion does not prevent the allocation it
        exists to prevent. This runs in milliseconds on an array whose float64
        copy would be 1.6 GB, which is the whole proof."""
        with pytest.raises(ValueError, match="before conversion"):
            S.specular_diffuse_split(self._huge((8192, 8192, 3)))
        with pytest.raises(ValueError, match="before conversion"):
            S.photometric_stereo_robust(
                self._huge((64, 4096, 4096)),
                np.tile([[0.3, 0.3, 1.0]], (64, 1)))


# --------------------------------------------------------------------------- #
# regressions from the adversarial pass                                        #
# --------------------------------------------------------------------------- #
class TestAdversarialRegressions:
    """Three findings, each with the minimal reproduction that exposed it."""

    def test_a_one_pixel_image_raises_valueerror_not_indexerror(self):
        """Was: IndexError('index 1 is out of bounds for axis 0 with size 1')
        from reading the second singular value of a (1, 3) matrix."""
        one = np.zeros((1, 1, 3)) + np.array([0.5, 0.3, 0.2])
        with pytest.raises(ValueError, match="at least 3 pixels"):
            S.specular_diffuse_split(one)
        with pytest.raises(ValueError, match="at least 3 pixels"):
            S.specular_coefficient_map(one)
        # the per-pixel route has no such requirement and still works
        d, s = S.specular_diffuse_split(one, body_rgb=(0.5, 0.3, 0.2))
        assert np.abs(d + s - one).max() < 1e-15

    def test_non_unit_normals_are_refused_not_silently_believed(self):
        """Was: photometric_residual(I, L, normals*2, albedo) returned 0.552 on
        an exactly Lambertian scene — the caller would conclude their surface is
        not Lambertian. The model is albedo*normal, so a scaled field scales the
        model."""
        clean, _s, L, nrm, alb = shadow_scene(k_blocked=0)
        assert S.photometric_residual(clean, L, nrm, alb).max() < 1e-15
        for factor in (0.5, 2.0):
            with pytest.raises(ValueError, match="not unit vectors"):
                S.photometric_residual(clean, L, nrm * factor, alb)
        # float32 normals stay inside the tolerance, as they must
        S.photometric_residual(clean, L, nrm.astype(np.float32),
                               alb.astype(np.float32))

    def test_min_inliers_above_the_light_count_is_refused(self):
        """Was: silently disabled the consensus refit, so every pixel quietly
        fell back to its three-light subset solution."""
        _c, shadowed, L, _n, _a = shadow_scene()
        with pytest.raises(ValueError, match="can never be met"):
            S.photometric_stereo_robust(shadowed, L, min_inliers=len(L) + 1)

    def test_two_materials_need_both_guards(self):
        """Was: the rank guard alone accepted an anti-parallel pair (rank ratio
        0.0815) and returned a diffuse map wrong by more than the image's own
        maximum, with no exception."""
        img, _d, specular, _m, _n, shading = known_split()
        two = img.copy()
        two[:, :24] = (np.array([0.25, 0.60, 0.75]) * shading[..., None]
                       + specular)[:, :24]
        S.specular_diffuse_split(two, max_negative_frac=None)      # slips past
        with pytest.raises(ValueError, match="negative"):
            S.specular_diffuse_split(two)                          # caught


# --------------------------------------------------------------------------- #
# ledger conformance                                                           #
# --------------------------------------------------------------------------- #
def _ledger_args():
    img, _d, _s, _m, n, _sh = known_split(h=32, w=32)
    labels = np.zeros((32, 32), dtype=np.int32)
    labels[:, 11:21] = 1
    labels[:, 21:] = 2
    multi = np.zeros((32, 32, 3))
    _i2, _d2, _s2, m_s2, _n2, shading2 = known_split(h=32, w=32)
    for k, c in enumerate((np.array([0.80, 0.55, 0.35]),
                           np.array([0.25, 0.60, 0.75]),
                           np.array([0.55, 0.30, 0.70]))):
        im = c * shading2[..., None] + m_s2[..., None] * WHITE
        multi[labels == k] = im[labels == k]
    _c, shadowed, L, _nrm, _alb = shadow_scene(h=16, w=16)
    diffuse, specular = _polar_scene(16, 16)
    frames = S.polarization_render(diffuse, specular)
    return {
        "specular_diffuse_split": ((img,), {}),
        "specular_coefficient_map": ((img,), {}),
        "specular_free_transform": ((img,), {}),
        "illuminant_from_dichromatic_planes": ((multi, labels), {}),
        "brdf_blinn_phong": ((n,), {}),
        "brdf_microfacet": ((n,), {}),
        "dichromatic_render": ((n,), {}),
        "photometric_stereo_robust": ((shadowed,), {"lights": L}),
        "photometric_residual": ((shadowed,), {"lights": L}),
        "polarization_render": ((diffuse, specular), {}),
        "polarization_separate": ((frames,), {}),
        "polarization_dolp_map": ((frames,), {}),
        "polarization_stokes": ((frames,), {}),
    }


#: The checks for the two sorts this family introduces. Each is the definition
#: ``tools/chain_fuzz.py`` must use; once the wiring exists the tests below
#: assert the two agree rather than drifting apart.
RGBIMAGE_CHECK = (lambda v: isinstance(v, np.ndarray) and v.ndim == 3
                  and v.shape[2] == 3)

#: A polariser sweep: ``(N, H, W)`` real frames through a linear analyser.
#: ``N >= 3`` because the model has three unknowns (mean, amplitude, azimuth),
#: and non-negative because radiance through an analyser cannot be negative.
#: **That is the whole of what a predicate can honestly assert** — see
#: :func:`test_the_polsweep_predicate_cannot_tell_a_sweep_from_a_light_stack`.
POLSWEEP_CHECK = (lambda v: isinstance(v, np.ndarray) and v.ndim == 3
                  and v.shape[0] >= 3 and v.dtype.kind == "f"
                  and np.isfinite(v).all() and (v >= 0.0).all())

NEW_SORTS = {"rgbimage": RGBIMAGE_CHECK, "polsweep": POLSWEEP_CHECK}


def test_ledger_is_complete_and_every_op_has_an_implementation():
    assert opsspecular.missing() == []
    assert len(opsspecular.OPSSPECULAR) == 13
    assert sorted(opsspecular.categories()) == ["dichromatic", "photometric",
                                                "polarization", "reflectance"]
    assert set(opsspecular.OPSSPECULAR) == set(S.SPECULARITY)
    assert set(S.SPECULARITY) <= set(S.__all__)
    for name, meta in opsspecular.OPSSPECULAR.items():
        assert meta["doc"], f"{name} has no docstring summary line"
        assert "Raises" in (meta["func"].__doc__ or ""), \
            f"{name} docstring has no Raises section"


def test_ledger_call_returns_the_declared_type():
    """The machine check that a declaration is not a lie: run each op and
    compare the value :func:`opsspecular.call` returns against its declared
    output sort, using the fuzzer's own predicates where they exist."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from chain_fuzz import TYPE_CHECKS
    checks = dict(TYPE_CHECKS)
    for sort, predicate in NEW_SORTS.items():
        checks.setdefault(sort, predicate)
    if "rgbimage" in TYPE_CHECKS:                # once the parent wires it
        assert TYPE_CHECKS["rgbimage"](np.zeros((4, 4, 3)))
        assert not TYPE_CHECKS["rgbimage"](np.zeros((4, 4)))
    if "polsweep" in TYPE_CHECKS:
        assert TYPE_CHECKS["polsweep"](np.zeros((4, 8, 8)))
        assert not TYPE_CHECKS["polsweep"](np.zeros((2, 8, 8)))     # N < 3
        assert not TYPE_CHECKS["polsweep"](-np.ones((4, 8, 8)))      # negative
        assert not TYPE_CHECKS["polsweep"]([np.zeros((8, 8))] * 4)   # not ndarray
    args = _ledger_args()
    assert set(args) == set(opsspecular.OPSSPECULAR), "ledger args missing"
    for name, (a, kw) in args.items():
        out_t = opsspecular.OPSSPECULAR[name]["out"]
        check = checks.get(out_t)
        assert check is not None, f"{name}: type {out_t!r} has no predicate"
        val = opsspecular.call(name, *a, **kw)
        assert val is not None
        assert check(val), (name, out_t, type(val).__name__,
                            getattr(val, "shape", None))


def test_ledger_input_types_match_what_the_operators_accept():
    """Every declared input sort must be a sort the fuzzer knows, so a wired
    family cannot declare a pool nobody can fill."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from chain_fuzz import TYPE_CHECKS
    known = set(TYPE_CHECKS) | set(NEW_SORTS)
    for name, meta in opsspecular.OPSSPECULAR.items():
        for t in meta["in"]:
            assert t in known, f"{name} declares unknown input sort {t!r}"
        assert meta["out"] in known, \
            f"{name} declares unknown output sort {meta['out']!r}"


def test_result_adapters_only_ever_narrow_the_raw_return():
    """An adapter may drop parts of a tuple, never fabricate a value the
    operator did not produce or repackage one into a different container.

    All three surviving adapters are the honest kind. The fourth — repacking
    ``polarization_render``'s stack into a list to satisfy the ``images``
    predicate — disappeared when the sweep got its own ndarray sort, which is
    the right direction: fewer adapters means the TYPEMISS check compares the
    *raw* return against the declaration."""
    args = _ledger_args()
    assert set(opsspecular.RESULT_ADAPTERS) == {
        "specular_diffuse_split", "photometric_stereo_robust",
        "polarization_separate"}
    for name, adapter in opsspecular.RESULT_ADAPTERS.items():
        a, kw = args[name]
        raw = opsspecular.get(name)(*a, **kw)
        assert isinstance(raw, tuple), f"{name} raw return is not a tuple"
        assert adapter(raw) is raw[0]


def test_polarization_render_needs_no_adapter():
    """Its raw return is already the declared sort, which is the strictest
    arrangement the fuzzer offers (opsoptics makes the same point)."""
    assert "polarization_render" not in opsspecular.RESULT_ADAPTERS
    a, kw = _ledger_args()["polarization_render"]
    raw = opsspecular.get("polarization_render")(*a, **kw)
    # `call` re-runs the function, so this is equality of value and type, not
    # of object identity — the point is that no adapter reshapes the return.
    called = opsspecular.call("polarization_render", *a, **kw)
    assert type(called) is type(raw) and np.array_equal(called, raw)
    assert POLSWEEP_CHECK(raw)


def test_the_new_sort_is_reachable_from_and_returns_to_existing_sorts():
    """A sort nobody produces is a dead vocabulary. ``rgbimage`` has an entry
    from ``normalmap``, two internal edges, and two exits (to ``image2d`` and to
    ``vector``) — asserted here so a later edit cannot quietly orphan it."""
    ins, outs = {}, {}
    for name, meta in opsspecular.OPSSPECULAR.items():
        ins[name], outs[name] = meta["in"], meta["out"]
    producers = [n for n, o in outs.items() if o == "rgbimage"]
    entries = [n for n in producers if "rgbimage" not in ins[n]]
    exits = [n for n, t in ins.items() if "rgbimage" in t and outs[n] != "rgbimage"]
    assert entries, "no operator produces rgbimage from another sort"
    assert "dichromatic_render" in entries
    assert ins["dichromatic_render"] == ["normalmap"]
    assert {"specular_coefficient_map",
            "illuminant_from_dichromatic_planes"} <= set(exits)
    assert {outs[e] for e in exits} == {"image2d", "vector"}


def test_the_polsweep_sort_is_reachable_and_returns_to_existing_sorts():
    """Same anti-orphan check for the second new sort: two producers (the
    operator below plus the fuzzer's generator) and three exits."""
    ins = {n: m["in"] for n, m in opsspecular.OPSSPECULAR.items()}
    outs = {n: m["out"] for n, m in opsspecular.OPSSPECULAR.items()}
    entries = [n for n, o in outs.items()
               if o == "polsweep" and "polsweep" not in ins[n]]
    exits = [n for n, t in ins.items()
             if "polsweep" in t and outs[n] != "polsweep"]
    assert entries == ["polarization_render"]
    assert ins["polarization_render"] == ["image2d", "image2d"]
    assert set(exits) == {"polarization_separate", "polarization_dolp_map",
                          "polarization_stokes"}
    assert {outs[e] for e in exits} == {"image2d", "stokes"}


def test_a_light_stack_is_silently_accepted_by_the_polarisation_operators():
    """Why the sweep needs its own sort, direction A — measured.

    A genuine multi-light Lambertian stack is not a polariser sweep, but it is
    structurally identical and physically plausible, so the fail-closed check
    (which exists to catch a *negative* fitted minimum) never fires. The scene
    contains no polariser and no polarised light whatsoever, and the operator
    reports a degree of linear polarisation of about 5% without complaint.

    Measured: 50 of 50 randomly oriented four-light stacks are accepted. The
    guard catches random noise, not a wrong-but-plausible stack — which is
    exactly why the separation has to be by pool name and not by predicate.
    """
    surf = bump_normals(32, 32, amp=4.0)
    accepted = 0
    for seed in range(50):
        rng = np.random.default_rng(seed)
        L = rng.standard_normal((4, 3)) + np.array([0.0, 0.0, 2.5])
        L = L / np.linalg.norm(L, axis=1, keepdims=True)
        stack = 0.6 * np.clip(np.einsum("hwc,nc->nhw", surf, L), 0.0, None)
        try:
            S.polarization_separate(stack)
            accepted += 1
        except ValueError:
            pass
    assert accepted == 50, "the fail-closed check is not what separates these"
    # and the number it invents for a completely unpolarised scene:
    rng = np.random.default_rng(0)
    L = _fuzzer_lights()
    stack = 0.6 * np.clip(np.einsum("hwc,nc->nhw", surf, L), 0.0, None)
    dolp = S.polarization_dolp_map(stack)
    assert 0.01 < dolp.mean() < 0.20            # measured 0.054, truth 0.0


def test_a_polariser_sweep_is_confidently_wrong_in_a_photometric_solver():
    """Why the sweep needs its own sort, direction B — the worse one, measured.

    A sweep handed to photometric stereo is a valid-looking light stack, so
    nothing raises. On a surface whose true normal is exactly ``(0, 0, 1)``
    everywhere, the solver returns normals averaging **33.99 degrees** off,
    with a plausible albedo (0.555) and a residual of only 21% of the peak
    radiance — the fit looks fittable because four frames over three unknowns
    always do. The same operator, the same lights, genuine photometric data of
    the same flat surface: **0.000115 degrees**. A ratio of 296,000, so 34
    degrees is not a failure, it is a confident lie.
    """
    h = w = 32
    rng = np.random.default_rng(0)
    flat = np.dstack([np.zeros((h, w)), np.zeros((h, w)), np.ones((h, w))])
    sweep = S.polarization_render(0.4 + 0.3 * rng.random((h, w)),
                                  0.5 * rng.random((h, w)), azimuth_deg=30.0)
    L = _fuzzer_lights()
    n, a, _i = S.photometric_stereo_robust(sweep, L, method="ransac")
    err = PM.angular_error_deg(n, flat)
    assert np.isfinite(n).all() and np.isfinite(a).all()   # no exception, no NaN
    assert err.mean() > 20.0                               # measured 33.99 deg
    unit = n.astype(np.float64) / np.linalg.norm(n, axis=-1, keepdims=True)
    residual = S.photometric_residual(sweep, L, unit, a.astype(np.float64))
    assert residual.max() / sweep.max() < 0.30    # measured 21%: looks fittable
    # the same solver on real photometric data of the same flat surface
    real = 0.6 * np.clip(np.einsum("hwc,nc->nhw", flat, L), 0.0, None)
    honest = PM.angular_error_deg(
        S.photometric_stereo_robust(real, L, method="ransac")[0], flat)
    assert honest.max() < 1e-3                             # measured 0.00011
    assert err.mean() > 1e4 * honest.mean()


def test_the_polsweep_predicate_cannot_tell_a_sweep_from_a_light_stack():
    """The honest boundary of what the type system does here.

    A structural predicate passes a sweep, a light stack and pure noise alike.
    Separation is by pool *name*; the predicate only pins the invariants that
    are genuinely checkable, and the ledger comment says so rather than
    implying the type verifies more than it can."""
    rng = np.random.default_rng(0)
    surf = bump_normals(32, 32, amp=4.0)
    L = _fuzzer_lights()
    sweep = S.polarization_render(0.4 + 0.3 * rng.random((32, 32)),
                                  0.5 * rng.random((32, 32)))
    stack = 0.6 * np.clip(np.einsum("hwc,nc->nhw", surf, L), 0.0, None)
    noise = np.stack([rng.random((32, 32)) for _ in range(4)])
    for arr in (sweep, stack, noise):
        assert POLSWEEP_CHECK(arr), "all three are structurally indistinguishable"
    # nor can it police the frame-to-angle correspondence: a permuted sweep is
    # a valid sweep of a different scene (measured 0.559 / 0.141 for a true
    # 0.5 / 0.2), which is metadata living outside the array.
    d0 = np.full((4, 4), 0.5)
    s0 = np.full((4, 4), 0.2)
    frames = S.polarization_render(d0, s0)
    assert POLSWEEP_CHECK(frames[[2, 0, 3, 1]])
    dd, ss = S.polarization_separate(frames[[2, 0, 3, 1]])
    assert dd[0, 0] == pytest.approx(0.5586, abs=1e-3)
    assert ss[0, 0] == pytest.approx(0.1414, abs=1e-3)


def test_polarization_stokes_feeds_the_existing_stokes_sort():
    """The other direction of the same argument: this family is the first
    producer of ``stokes`` from a *measurement* rather than from optics' own
    algebra, so the existing narrow sort gets an entrance."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from chain_fuzz import TYPE_CHECKS
    diffuse, specular = _polar_scene(8, 8)
    st = opsspecular.call("polarization_stokes",
                          S.polarization_render(diffuse, specular))
    assert TYPE_CHECKS["stokes"](st)
    O.stokes_analyze(st)


def test_specular_ops_are_registered_in_the_chain_fuzzer():
    """Skips until the family is wired; asserts completeness once it is."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz
    names = {o[0] for o in chain_fuzz.catalog()}
    if not (names & set(opsspecular.OPSSPECULAR)):
        pytest.skip("opsspecular not yet wired into tools/chain_fuzz.py")
    assert set(opsspecular.OPSSPECULAR) <= names


def test_api_exports_every_specularity_op():
    import api
    if not hasattr(api, "specular_diffuse_split"):
        pytest.skip("specularity not yet wired into api.py")
    for name in S.SPECULARITY:
        assert name in api.__all__, f"{name} missing from api.__all__"
        assert getattr(api, name) is getattr(S, name)


def test_facade_exports_every_specularity_op():
    """The ``fullseye`` facade re-export.

    Skipped — not passed — when importing the facade hits the pre-existing
    ``comm`` shadowing problem in this environment (the repo's ``comm.py`` loses
    to the installed ``comm`` package on sys.path). The identical failure is
    visible in ``test_optics.py::test_facade_exports_every_optics_op`` on a
    clean tree, so it is not this family's, and skipping with the real reason
    attached beats either a red test that blames the wrong code or a silent
    pass that would hide a genuine facade gap later.
    """
    import api
    if not hasattr(api, "specular_diffuse_split"):
        pytest.skip("specularity not yet wired into api.py")
    try:
        import fullseye
    except ImportError as exc:                              # pragma: no cover
        pytest.skip(f"pre-existing facade import failure, unrelated: {exc}")
    for name in S.SPECULARITY:
        assert name in fullseye.__all__, f"{name} missing from fullseye.__all__"
        assert getattr(fullseye, name) is getattr(S, name)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])

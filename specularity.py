# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Specular / diffuse reflection separation, reflectance lobes and robust
photometric stereo (numpy only).

:mod:`photometric` says it in its own docstring: the linear least-squares
solution is exact for a Lambertian surface under known lights with no shadow,
and *"shadow and specularity break the linearity, so a robust variant (median /
RANSAC over lights) is needed separately"*. This module is that separately —
plus the colour and polarisation routes that remove the highlight before any
shape solver ever sees it. Everything here is closed form, so every claim below
is a number a test reproduces rather than a promise.

Four families:

  * **dichromatic** — :func:`specular_diffuse_split`,
    :func:`specular_free_transform`, :func:`specular_coefficient_map`,
    :func:`illuminant_from_dichromatic_planes`. Shafer's dichromatic reflection
    model says the radiance of a dielectric is the sum of a *body* term whose
    colour is the surface's and an *interface* term whose colour is the
    illuminant's. The specular part therefore lives in a **one-dimensional
    subspace** — the illuminant direction in RGB — and removing it is a
    projection, not an optimisation.
  * **reflectance** — :func:`brdf_blinn_phong`, :func:`brdf_microfacet`,
    :func:`dichromatic_render`. The forward model, so the loop closes: render a
    known highlight, separate it, compare against what went in. Two lobe shapes
    on purpose, because the separators must not depend on the lobe.
  * **photometric** — :func:`photometric_stereo_robust`,
    :func:`photometric_residual`. Woodham's three-light solve wrapped in
    Fischler-Bolles maximum consensus and Rousseeuw's least-median-of-squares,
    both **exhaustive and deterministic** over 3-light subsets when the count
    allows it, so two runs give the same answer bit for bit.
  * **polarisation** — :func:`polarization_render`,
    :func:`polarization_separate`, :func:`polarization_dolp_map`,
    :func:`polarization_stokes`. A polariser sweep splits light into its
    unpolarised and linearly polarised parts in closed form; the last one hands
    a Stokes vector straight to :func:`optics.stokes_analyze`.

Deliberately **not** here (owned elsewhere — imported and composed, never
re-implemented):

  * **The Lambertian forward model and the normal-field integration** are
    :mod:`photometric` (``render_lambertian``, ``synthesize_ps_images``,
    ``normals_to_gradients``, ``integrate_gradients`` = Frankot-Chellappa,
    ``angular_error_deg``). :func:`dichromatic_render` *calls*
    ``render_lambertian`` for its body term, and
    :func:`photometric_stereo_robust` *calls* ``photometric_stereo`` for its
    ``method="lstsq"`` baseline — which is what makes "the plain version breaks
    here" a measurement rather than a claim.
  * **Polarisation algebra** is :mod:`optics` (``jones_element``,
    ``mueller_element``, ``stokes_analyze`` ...). :func:`polarization_stokes`
    produces the Stokes vector that ``stokes_analyze`` reads; the degree of
    polarisation, the azimuth and the ellipticity all come from there.
  * **Ray-surface interaction** is :mod:`match3d` (``reflect``, ``refract``,
    ``fresnel_reflectance`` = the exact unpolarised s/p average,
    ``normal_from_reflection`` = deflectometry). :func:`brdf_microfacet` uses
    Schlick's *approximation* to Fresnel by name and default, because that is
    what the microfacet literature specifies; when the exact curve matters,
    call ``match3d.fresnel_reflectance``.
  * **Colour space conversion, white balance, demosaicing** are the colour
    backends. Every operator here takes linear RGB and says so.

Conventions, stated once (these are the traps):

  * **Linear radiance, not display values.** Every image is linear in radiance.
    A gamma-encoded image violates the dichromatic model's additivity and the
    separation silently degrades — there is no way to detect it from the array,
    so it is stated here instead of guessed at.
  * **The illuminant colour is a direction, not a brightness.** ``illuminant_rgb``
    is normalised to a unit vector internally; only its direction matters. The
    default ``(1, 1, 1)`` is the white-balanced case.
  * **Normals are (H, W, 3) with +z toward the camera**, the same convention as
    :mod:`photometric`, so a normal map moves between the two modules unchanged.
  * **Light vectors point from the surface toward the light.** Same as
    ``photometric.render_lambertian``.
  * **Polariser angles are taken modulo 180 degrees**, because a linear
    polariser at 0 and at 180 is the same instrument. Two angles that coincide
    modulo 180 make the sinusoid fit rank-deficient and raise.

Honest disclosure (what these operators cannot do):

  * **:func:`specular_diffuse_split` without ``body_rgb`` needs one
    specular-free pixel.** With a known illuminant the body colour is only
    recoverable *up to its component along the illuminant*: adding ``eps *
    illuminant`` to the body colour and subtracting the same amount from the
    specular coefficient produces a **pixel-identical image**. That is a real
    ambiguity of the model, not a weakness of the solver, and the standard fix
    is the constraint used here — the specular coefficient is non-negative and
    its minimum over the image is zero. If every pixel of the surface is glossy,
    the split under-reports the specular term by a constant and **no test on the
    image alone can detect it**. Pass ``body_rgb`` when you know the albedo.
  * **The uniform-body route assumes one material.** The illuminant-orthogonal
    part of a single-material image is exactly rank one; two materials make it
    rank two. That is measurable, so it is measured: ``max_rank_ratio`` rejects
    the image instead of returning a plausible-looking wrong split.
  * **Polarisation separation equates "unpolarised" with "diffuse".** What the
    sinusoid fit recovers exactly is the unpolarised radiance ``2*I_min`` and
    the linearly polarised radiance ``I_max - I_min``. Calling the first diffuse
    and the second specular is an *additional physical assumption* — true near
    Brewster's angle for a dielectric, false at normal incidence (where specular
    reflection is unpolarised and the split returns all of it as diffuse) and
    false for metals (which depolarise much less on the diffuse side). The
    operator names follow the field's usage; the docstrings name the assumption.
  * **The BRDF lobes are shading models, not light transport.** No
    interreflection, no cast shadow, no subsurface term. They exist so a
    separation can be tested against a known highlight, in the same spirit as
    :mod:`visiondesign` returning limits rather than rendered images.
  * **Robust photometric stereo treats attached shadow as an outlier.** For a
    pixel whose true ``N.L`` is negative the *linear* model is wrong for that
    light, and the estimator discards it. That is the right behaviour, but it
    means the effective number of lights is smaller than ``N`` and fewer than
    three surviving lights leaves the normal undetermined — reported through
    the returned inlier mask, never hidden.

Fail-closed on untrusted input, like every Fullseye module: strings, bools,
complex numbers and masked arrays are refused rather than coerced (``float("50")``
succeeds, which is exactly how an unparsed configuration value becomes a
plausible wrong answer); NaN/Inf are refused on the way in; a zero-length
illuminant, an illuminant parallel to the body colour, coincident polariser
angles, a singular light matrix and a negative fitted radiance each raise a
``ValueError`` that names the problem. Sizes are capped
(:data:`MAX_PIXELS`, :data:`MAX_STACK_ELEMENTS`, :data:`MAX_LIGHTS`,
:data:`MAX_ROBUST_PIXELS`, :data:`MAX_ROBUST_WORK`, :data:`MAX_MATERIALS`) so a
mistyped exponent fails instead of allocating the machine's memory.

References (public literature, reimplemented from the papers):

  * Shafer, *Using color to separate reflection components*, Color Research &
    Application 10(4), 1985 — the dichromatic reflection model.
  * Klinker, Shafer & Kanade, *The measurement of highlights in color images*,
    IJCV 2(1), 1988 — the colour-space geometry of the dichromatic plane.
  * Lee, *Method for computing the scene-illuminant chromaticity from specular
    highlights*, JOSA A 3(10), 1986 — illuminant from intersecting dichromatic
    planes.
  * Mallick, Zickler, Kriegman & Belhumeur, *Beyond Lambert: reconstructing
    specular surfaces using color*, CVPR 2005 — the specular-invariant subspace
    orthogonal to the illuminant.
  * Woodham, *Photometric method for determining surface orientation from
    multiple images*, Optical Engineering 19(1), 1980 — photometric stereo.
  * Fischler & Bolles, *Random sample consensus*, CACM 24(6), 1981.
  * Rousseeuw, *Least median of squares regression*, JASA 79(388), 1984.
  * Wolff & Boult, *Constraining object features using a polarization
    reflectance model*, IEEE TPAMI 13(7), 1991 — polarisation-based separation.
  * Nayar, Fang & Boult, *Separation of reflection components using color and
    polarization*, IJCV 21(3), 1997.
  * Blinn, *Models of light reflection for computer synthesized pictures*,
    SIGGRAPH 1977 — the half-vector lobe.
  * Trowbridge & Reitz, *Average irregularity representation of a rough surface
    for ray reflection*, JOSA 65(5), 1975 — the GGX microfacet distribution.
  * Smith, *Geometrical shadowing of a random rough surface*, IEEE TAP 15(5),
    1967 — the masking-shadowing term.
  * Schlick, *An inexpensive BRDF model for physically-based rendering*,
    Computer Graphics Forum 13(3), 1994 — the Fresnel approximation.
"""
from __future__ import annotations

import itertools

import numpy as np

import optics
import photometric

__all__ = [
    "specular_diffuse_split", "specular_free_transform",
    "specular_coefficient_map", "illuminant_from_dichromatic_planes",
    "brdf_blinn_phong", "brdf_microfacet", "dichromatic_render",
    "photometric_stereo_robust", "photometric_residual",
    "polarization_render", "polarization_separate", "polarization_dolp_map",
    "polarization_stokes",
    "SPECULARITY", "ROBUST_METHODS", "BRDF_MODELS",
    "MAX_PIXELS", "MAX_STACK_ELEMENTS", "MAX_LIGHTS", "MAX_ROBUST_PIXELS",
    "MAX_ROBUST_WORK", "MAX_SUBSETS", "MAX_MATERIALS",
]

#: The public operators, by name (introspection / facade wiring).
SPECULARITY = [
    "specular_diffuse_split", "specular_free_transform",
    "specular_coefficient_map", "illuminant_from_dichromatic_planes",
    "brdf_blinn_phong", "brdf_microfacet", "dichromatic_render",
    "photometric_stereo_robust", "photometric_residual",
    "polarization_render", "polarization_separate", "polarization_dolp_map",
    "polarization_stokes",
]

#: Estimators accepted by :func:`photometric_stereo_robust`. ``"lstsq"`` is the
#: non-robust baseline (delegated to :func:`photometric.photometric_stereo`), so
#: "the plain version breaks under shadow" can be measured in the same call.
ROBUST_METHODS = ("lstsq", "median", "ransac")

#: Lobe shapes accepted by :func:`dichromatic_render`.
BRDF_MODELS = ("blinn_phong", "microfacet")

#: Cap on the pixel count of a single 2-D/RGB image.
MAX_PIXELS = 1 << 24

#: Cap on the total element count of an (N, H, W) image stack.
MAX_STACK_ELEMENTS = 1 << 26

#: Cap on the number of light directions / polariser angles in one stack.
MAX_LIGHTS = 64

#: Cap on the pixel count for :func:`photometric_stereo_robust`. Lower than
#: :data:`MAX_PIXELS` because the consensus refit holds a 3x3 normal matrix per
#: pixel (72 bytes/pixel), so this bound is what keeps that allocation at 72 MB.
MAX_ROBUST_PIXELS = 1 << 20

#: Cap on ``subsets * lights * pixels`` for :func:`photometric_stereo_robust`.
#: The estimator is exhaustive over 3-light subsets, so the cost is a product of
#: three user-controlled numbers and any one of them can be mistyped.
MAX_ROBUST_WORK = 1 << 28

#: Cap on the number of 3-light subsets evaluated per call.
MAX_SUBSETS = 4096

#: Cap on the number of distinct material labels in
#: :func:`illuminant_from_dichromatic_planes`.
MAX_MATERIALS = 1024

#: Below this the illuminant-orthogonal part of the image is treated as absent
#: (the body colour is parallel to the illuminant, so the two components are
#: algebraically indistinguishable). Relative to the Frobenius norm of the image.
_DEGENERATE_TOL = 1e-12


# --------------------------------------------------------------------------- #
# fail-closed input helpers                                                    #
# --------------------------------------------------------------------------- #
def _finite_scalar(v, name: str) -> float:
    """A real, finite Python float — or ``ValueError`` naming the problem."""
    if np.ma.is_masked(v):
        raise ValueError("%s is a masked value — fill or drop it explicitly" % (name,))
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s is a bool — refusing the silent True==1 promotion"
                         % (name,))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s is complex — a reflectance parameter is a real "
                         "quantity; coercion would silently drop the imaginary "
                         "part" % (name,))
    if isinstance(v, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s is a string (%r) — float('50') would silently "
                         "succeed and hide a configuration value that was never "
                         "parsed" % (name, v))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real scalar, got %r"
                         % (name, type(v).__name__)) from None
    if not np.isfinite(f):
        raise ValueError("%s must be finite, got %r (NaN/Inf would propagate "
                         "through every result)" % (name, v))
    return f


def _positive(v, name: str) -> float:
    f = _finite_scalar(v, name)
    if f <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, f))
    return f


def _unit_interval(v, name: str) -> float:
    f = _finite_scalar(v, name)
    if not (0.0 <= f <= 1.0):
        raise ValueError("%s must be in [0, 1] (it is a reflectance fraction), "
                         "got %g" % (name, f))
    return f


def _count(v, name: str, lo: int, hi: int) -> int:
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be an int, got %r" % (name, type(v).__name__))
    n = int(v)
    if n < lo or n > hi:
        raise ValueError("%s must be in [%d, %d], got %d (the cap is there so a "
                         "mistyped exponent fails instead of allocating "
                         "gigabytes)" % (name, lo, hi, n))
    return n


def _as_float_array(a, name: str) -> np.ndarray:
    """Coerce to float64, refusing every silent-truncation trap.

    ``np.asarray(["1", "2"], dtype=float)`` succeeds, so the dtype of the raw
    input is inspected *before* coercion — otherwise a list of strings from an
    unparsed config file passes as radiance.
    """
    if isinstance(a, (str, bytes)):
        raise ValueError("%s is a string (%r) — an image/vector must be numeric"
                         % (name, a))
    if np.ma.is_masked(a):
        raise ValueError("%s is a masked array with masked (invalid) entries — "
                         "coercion would strip the mask and use the raw values "
                         "underneath; fill or drop them explicitly" % (name,))
    try:
        raw = np.asarray(a)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s could not be read as an array: %s" % (name, exc)) from None
    if raw.dtype.kind in ("U", "S"):
        raise ValueError("%s has string dtype %r — numeric strings would be "
                         "coerced without complaint and hide an unparsed "
                         "configuration value" % (name, raw.dtype))
    if raw.dtype.kind == "O":
        raise ValueError("%s has object dtype — refusing to guess what its "
                         "elements are (a ragged list is the usual cause)"
                         % (name,))
    if raw.dtype.kind == "b":
        raise ValueError("%s has bool dtype — refusing the silent True==1 "
                         "promotion of a mask into radiance" % (name,))
    if raw.dtype.kind == "c":
        raise ValueError("%s is complex — coercion to float64 would silently "
                         "discard the imaginary part; take .real/.imag/abs() "
                         "explicitly" % (name,))
    arr = np.ascontiguousarray(raw, dtype=np.float64)
    if not np.isfinite(arr).all():
        n = int((~np.isfinite(arr)).sum())
        raise ValueError("%s has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (name, n))
    return arr


def _require_rgb(a, name: str, op: str) -> np.ndarray:
    """A strictly (H, W, 3) finite float image, size-capped."""
    arr = _as_float_array(a, name)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError("%s: %s must have shape (H, W, 3) — linear RGB, one "
                         "sample per channel — got shape %r; nothing is "
                         "reshaped silently" % (op, name, tuple(arr.shape)))
    if arr.shape[0] < 1 or arr.shape[1] < 1:
        raise ValueError("%s: %s is empty (shape %r)" % (op, name, tuple(arr.shape)))
    n = arr.shape[0] * arr.shape[1]
    if n > MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels (shape %r), over the %d cap "
                         "(specularity.MAX_PIXELS)"
                         % (op, name, n, tuple(arr.shape), MAX_PIXELS))
    return arr


def _require_map(a, name: str, op: str) -> np.ndarray:
    """A strictly 2-D finite float image, size-capped."""
    arr = _as_float_array(a, name)
    if arr.ndim != 2:
        raise ValueError("%s: %s must be a 2-D array, got a %d-D array of shape "
                         "%r" % (op, name, arr.ndim, tuple(arr.shape)))
    if arr.size > MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels, over the %d cap "
                         "(specularity.MAX_PIXELS)" % (op, name, arr.size, MAX_PIXELS))
    return arr


def _require_normals(a, name: str, op: str) -> np.ndarray:
    """A (H, W, 3) normal field, unit-normalised, +z toward the camera."""
    arr = _require_rgb(a, name, op)
    norm = np.linalg.norm(arr, axis=-1)
    if not (norm > 0.0).all():
        n = int((norm <= 0.0).sum())
        raise ValueError("%s: %s has %d zero-length normal(s) — a surface "
                         "element without an orientation has no reflectance; "
                         "mask those pixels out instead" % (op, name, n))
    return arr / norm[..., None]


def _require_direction(a, name: str, op: str) -> np.ndarray:
    """A 3-vector, returned as a unit direction. Zero length is refused."""
    arr = _as_float_array(a, name)
    if arr.shape != (3,):
        raise ValueError("%s: %s must be a 3-vector, got shape %r"
                         % (op, name, tuple(arr.shape)))
    n = float(np.linalg.norm(arr))
    if n <= 0.0:
        raise ValueError("%s: %s has zero length — a direction/colour of zero "
                         "length has no direction, and normalising it would be "
                         "a 0/0" % (op, name))
    return arr / n


def _require_stack(a, name: str, op: str) -> np.ndarray:
    """An (N, H, W) float stack (a list of equal-shaped 2-D images is fine)."""
    arr = _as_float_array(a, name)
    if arr.ndim != 3:
        raise ValueError("%s: %s must have shape (N, H, W) — %d images of the "
                         "same size — got a %d-D array of shape %r (a ragged "
                         "list of images lands here as object dtype and is "
                         "refused earlier)"
                         % (op, name, arr.shape[0] if arr.ndim else 0,
                            arr.ndim, tuple(arr.shape)))
    if arr.shape[0] > MAX_LIGHTS:
        raise ValueError("%s: %s has %d frames, over the %d cap "
                         "(specularity.MAX_LIGHTS)"
                         % (op, name, arr.shape[0], MAX_LIGHTS))
    if arr.size > MAX_STACK_ELEMENTS:
        raise ValueError("%s: %s has %d elements (shape %r), over the %d cap "
                         "(specularity.MAX_STACK_ELEMENTS)"
                         % (op, name, arr.size, tuple(arr.shape),
                            MAX_STACK_ELEMENTS))
    return arr


def _require_lights(a, n_frames: int, op: str, normalize: bool = True) -> np.ndarray:
    """An (N, 3) light-direction matrix matching the frame count."""
    arr = _as_float_array(a, "lights")
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError("%s: lights must have shape (N, 3), got %r"
                         % (op, tuple(arr.shape)))
    if arr.shape[0] != n_frames:
        raise ValueError("%s: %d light direction(s) for %d image(s) — the two "
                         "must correspond frame by frame"
                         % (op, arr.shape[0], n_frames))
    norms = np.linalg.norm(arr, axis=1)
    if not (norms > 0.0).all():
        k = int((norms <= 0.0).sum())
        raise ValueError("%s: %d light vector(s) have zero length — a light "
                         "with no direction contributes nothing but makes the "
                         "system rank-deficient" % (op, k))
    return arr / norms[:, None] if normalize else arr


def _require_angles(a, n_frames: int, op: str) -> np.ndarray:
    """Polariser angles in degrees, one per frame, distinct modulo 180."""
    arr = _as_float_array(a, "angles_deg")
    if arr.ndim != 1:
        raise ValueError("%s: angles_deg must be a 1-D array of degrees, got "
                         "shape %r" % (op, tuple(arr.shape)))
    if arr.size != n_frames:
        raise ValueError("%s: %d polariser angle(s) for %d image(s) — the two "
                         "must correspond frame by frame" % (op, arr.size, n_frames))
    if arr.size < 3:
        raise ValueError("%s: a polariser sweep needs at least 3 angles (the "
                         "model has 3 unknowns: mean, amplitude, azimuth), got "
                         "%d" % (op, arr.size))
    return arr


def _polarizer_design(angles_deg: np.ndarray, op: str) -> np.ndarray:
    """Design matrix ``[1, cos 2t, sin 2t]`` with a rank check.

    A linear polariser at 0 and at 180 degrees is the same instrument, so
    angles that coincide modulo 180 add a row but no information. The check is
    on the smallest singular value rather than on the angles themselves,
    because three angles can be pairwise distinct and still leave the fit
    rank-deficient.
    """
    t = np.radians(2.0 * angles_deg)
    M = np.stack([np.ones_like(t), np.cos(t), np.sin(t)], axis=1)   # (N, 3)
    s = np.linalg.svd(M, compute_uv=False)
    if s[-1] <= 1e-10 * s[0]:
        raise ValueError("%s: the polariser angles do not determine the three "
                         "unknowns (smallest singular value %.3g vs largest "
                         "%.3g). Angles are taken modulo 180 degrees, so 0 and "
                         "180 are the same measurement; use at least three "
                         "distinct orientations such as (0, 45, 90)"
                         % (op, s[-1], s[0]))
    return M


# --------------------------------------------------------------------------- #
# dichromatic reflection model                                                 #
# --------------------------------------------------------------------------- #
def _split_uniform_body(I, gamma, max_rank_ratio, max_negative_frac, op):
    """Uniform-body separation: rank-1 fit + the minimum-specular constraint.

    ``I(x) = m_d(x) * L + m_s(x) * G`` with ``L`` (body colour) constant and
    ``G`` (illuminant colour) known. Projecting out ``G`` leaves
    ``P I(x) = m_d(x) * P L`` — exactly rank one — so ``P L`` is the leading
    singular vector and ``m_d`` is the projection onto it. The component of
    ``L`` along ``G`` is *not* observable (see the module docstring), and is
    pinned by requiring ``m_s >= 0`` with ``min m_s = 0``.
    """
    H, W, _ = I.shape
    P = I.reshape(-1, 3)
    scale = float(np.linalg.norm(P))
    if scale <= 0.0:
        raise ValueError("%s: the image is identically zero — there is no "
                         "reflection to separate" % (op,))
    s_along = P @ gamma                                  # (P,) component on G
    D = P - s_along[:, None] * gamma[None, :]            # G-orthogonal part
    # Leading singular vector of the G-orthogonal part = the body direction,
    # projected. Economy SVD on the 3-column matrix is a 3x3 eigenproblem.
    _u, sv, vt = np.linalg.svd(D, full_matrices=False)
    if sv[0] <= _DEGENERATE_TOL * scale:
        raise ValueError("%s: the image has no component orthogonal to the "
                         "illuminant colour (largest singular value %.3g vs "
                         "image norm %.3g). The body colour is parallel to the "
                         "illuminant, so the two terms of the dichromatic model "
                         "are algebraically the same direction and no split "
                         "exists" % (op, sv[0], scale))
    if max_rank_ratio is not None:
        ratio = float(sv[1] / sv[0])
        if ratio > max_rank_ratio:
            raise ValueError(
                "%s: the illuminant-orthogonal part of this image has rank > 1 "
                "(second/first singular value %.4g > max_rank_ratio %.4g), so "
                "it is not a single-material surface. Pass body_rgb (a (3,) "
                "colour or an (H, W, 3) map) to separate a textured surface, or "
                "raise max_rank_ratio if you know the extra rank is noise"
                % (op, ratio, max_rank_ratio))
    u = vt[0]
    u = u - float(u @ gamma) * gamma                     # exactly orthogonal to G
    nu = float(np.linalg.norm(u))
    if nu <= 0.0:                                        # pragma: no cover
        raise ValueError("%s: the body direction collapsed onto the illuminant "
                         "direction" % (op,))
    u = u / nu
    m = D @ u                                            # (P,) diffuse strength
    if float(m.sum()) < 0.0:
        u, m = -u, -m
    # The rank test above is necessary but *not sufficient*, which the adversarial
    # pass measured rather than guessed: two materials whose illuminant-orthogonal
    # chromaticities are nearly anti-parallel leave the projected image rank one
    # (measured s2/s1 = 0.0815 for a half-and-half image the check therefore
    # waved through), and the only trace they leave is a body coefficient that
    # comes out negative on one of the two. A body coefficient is non-negative by
    # definition, so that is a sound second test and it costs nothing.
    if max_negative_frac is not None:
        big = 1e-9 * float(np.abs(m).max())
        neg = float((m < -big).mean())
        if neg > max_negative_frac:
            raise ValueError(
                "%s: the body (diffuse) coefficient is negative at %.4g of the "
                "pixels, and a body coefficient cannot be negative. That means "
                "more than one material is present with opposing chromaticity — "
                "a case the rank test above cannot see, because two opposed "
                "colours still span one line. Pass body_rgb to separate a "
                "textured surface, or raise max_negative_frac if you know the "
                "negatives are noise around zero" % (op, neg))
    # min-specular constraint: m_s(x) = s_along(x) - c * m(x) >= 0 with equality
    # somewhere. c is the ratio of the body colour's G-component to its
    # G-orthogonal length; the minimum ratio over lit pixels is exactly it.
    lit = m > 1e-12 * float(np.abs(m).max())
    if not lit.any():
        raise ValueError("%s: no pixel has a body (diffuse) component, so the "
                         "specular offset is undetermined" % (op,))
    c = float(np.min(s_along[lit] / m[lit]))
    m_s = s_along - c * m
    m_s = np.maximum(m_s, 0.0)          # the minimum is 0 by construction; this
    # only removes rounding-level negatives at the argmin pixel.
    specular = m_s[:, None] * gamma[None, :]
    diffuse = P - specular
    return (diffuse.reshape(H, W, 3), specular.reshape(H, W, 3),
            m_s.reshape(H, W))


def _split_known_body(I, gamma, body_rgb, op):
    """Exact per-pixel unmixing when the body colour is known.

    Three equations (RGB), two unknowns: least squares on ``[L G]`` has the
    closed form below, where ``b = L.G``. ``|b| -> 1`` is the degenerate case
    (body colour parallel to the illuminant) and is refused rather than
    returning the 0/0 that ``1 - b**2`` becomes.
    """
    H, W, _ = I.shape
    B = _as_float_array(body_rgb, "body_rgb")
    if B.shape == (3,):
        B = np.broadcast_to(B, (H, W, 3))
    elif B.shape != (H, W, 3):
        raise ValueError("%s: body_rgb must be a (3,) colour or an (H, W, 3) "
                         "map matching the image %r, got %r"
                         % (op, (H, W, 3), tuple(B.shape)))
    nb = np.linalg.norm(B, axis=-1)
    if not (nb > 0.0).all():
        k = int((nb <= 0.0).sum())
        raise ValueError("%s: body_rgb has %d zero-length colour(s) — a body "
                         "colour of zero length has no direction" % (op, k))
    L = B / nb[..., None]
    b = L @ gamma                                       # (H, W) = cos angle
    det = 1.0 - b * b
    worst = float(np.abs(b).max())
    if worst >= 1.0 - 1e-12:
        k = int((np.abs(b) >= 1.0 - 1e-12).sum())
        raise ValueError("%s: body_rgb is parallel to illuminant_rgb at %d "
                         "pixel(s) (|cos| = %.15g). The two model terms then "
                         "point the same way and their split is not defined — "
                         "the least-squares system is exactly singular"
                         % (op, k, worst))
    p = np.sum(I * L, axis=-1)
    q = I @ gamma
    m_d = (p - b * q) / det
    m_s = (q - b * p) / det
    diffuse = m_d[..., None] * L
    specular = m_s[..., None] * gamma[None, None, :]
    return diffuse, specular, m_s


def specular_diffuse_split(image_rgb, illuminant_rgb=(1.0, 1.0, 1.0),
                           body_rgb=None, max_rank_ratio=0.1,
                           max_negative_frac=0.02):
    """Split a linear-RGB image into its diffuse (body) and specular (interface) parts. → (diffuse, specular), both (H, W, 3).

    Shafer's dichromatic reflection model writes the radiance of a dielectric as
    ``I(x) = m_d(x) * L(x) + m_s(x) * G``: a body term carrying the surface
    colour ``L`` and an interface term carrying the **illuminant** colour ``G``.
    The specular part therefore occupies a single direction in RGB, and
    separating it is a projection with a closed form — no iteration, no
    optimisation, no learned prior.

    Two regimes, chosen by *body_rgb*:

    * **``body_rgb`` given** — a ``(3,)`` colour or an ``(H, W, 3)`` map. Each
      pixel solves the 3-equation, 2-unknown least-squares system exactly. This
      is the textured-surface path and it is exact to machine precision:
      re-adding ``m_s * G`` to the returned diffuse reproduces the input, and a
      synthetic image built from known ``(m_d, m_s)`` returns those numbers to
      about 1e-16 relative.
    * **``body_rgb`` omitted** — one material is assumed. The
      illuminant-orthogonal part of the image is then exactly rank one, so the
      body direction is its leading singular vector; the unobservable component
      of ``L`` along ``G`` is fixed by requiring ``m_s >= 0`` with the minimum
      over the image equal to zero. **At least one pixel must be specular-free**
      (see the module docstring: without one, the split under-reports the
      specular term by a constant and nothing in the image can reveal it).

    *illuminant_rgb* is a **direction**; only its orientation matters and it is
    unit-normalised internally. ``(1, 1, 1)`` is the white-balanced case. Get it
    from :func:`illuminant_from_dichromatic_planes` when you have two or more
    materials in frame.

    *max_rank_ratio* guards the uniform-body path: the second singular value of
    the illuminant-orthogonal part divided by the first. One material gives
    exactly 0 in the noiseless case (measured 1.1e-16 on the synthetic image in
    ``tests/test_specularity.py``) and stays small under noise (measured 0.0134
    at 1% Gaussian noise, 0.0672 at 5%); two materials give a large value
    (measured 0.518 for a two-albedo image). The default 0.1 sits between those
    measurements. Pass ``None`` to disable the check.

    **Raises** ``ValueError``: *image_rgb* is not ``(H, W, 3)``, is complex /
    masked / non-finite / string-typed, or exceeds :data:`MAX_PIXELS`;
    *illuminant_rgb* is not a non-zero 3-vector; the image is identically zero;
    the image has no component orthogonal to the illuminant (body colour
    parallel to it, so no split exists); the rank check fails; *body_rgb* has
    the wrong shape, a zero-length colour, or is parallel to the illuminant.

    Returns ``(diffuse, specular)`` with ``diffuse + specular == image_rgb`` to
    machine precision in both regimes.
    """
    op = "specular_diffuse_split"
    I = _require_rgb(image_rgb, "image_rgb", op)
    gamma = _require_direction(illuminant_rgb, "illuminant_rgb", op)
    max_rank_ratio, max_negative_frac = _split_guards(max_rank_ratio,
                                                      max_negative_frac)
    if body_rgb is None:
        diffuse, specular, _ = _split_uniform_body(I, gamma, max_rank_ratio,
                                                   max_negative_frac, op)
    else:
        diffuse, specular, _ = _split_known_body(I, gamma, body_rgb, op)
    return diffuse, specular


def specular_coefficient_map(image_rgb, illuminant_rgb=(1.0, 1.0, 1.0),
                             body_rgb=None, max_rank_ratio=0.1):
    """The scalar interface (specular) coefficient of the dichromatic model. → (H, W).

    The same decomposition as :func:`specular_diffuse_split`, returning the
    scalar ``m_s(x)`` instead of the coloured image ``m_s(x) * G``. That scalar
    is what an inspection routine thresholds: it is the amount of light the
    surface reflected *as a mirror does*, in the units of the input radiance,
    and it is zero wherever the surface behaved as a Lambertian body.

    ``specular_coefficient_map(...) * illuminant_unit`` equals the second return
    value of :func:`specular_diffuse_split` exactly, by construction — the two
    operators share one core.

    Arguments and failure modes are identical to
    :func:`specular_diffuse_split`.
    """
    op = "specular_coefficient_map"
    I = _require_rgb(image_rgb, "image_rgb", op)
    gamma = _require_direction(illuminant_rgb, "illuminant_rgb", op)
    if max_rank_ratio is not None:
        max_rank_ratio = _positive(max_rank_ratio, "max_rank_ratio")
    if body_rgb is None:
        _, _, m_s = _split_uniform_body(I, gamma, max_rank_ratio, op)
    else:
        _, _, m_s = _split_known_body(I, gamma, body_rgb, op)
    return m_s


def specular_free_transform(image_rgb, illuminant_rgb=(1.0, 1.0, 1.0)):
    """Project out the illuminant direction: the part of the image a highlight cannot touch. → (H, W, 3).

    ``I - (I.G) G`` for the unit illuminant colour ``G``. Under the dichromatic
    model the interface term is ``m_s * G``, so it lies entirely in the removed
    direction and the result is **invariant to any specular term whatsoever** —
    exactly, for any lobe shape, any strength, any spatial pattern. That is the
    specular-invariant subspace of Mallick et al. (2005); this operator is the
    projection itself, with no rotation into named channels, so it stays in RGB
    and composes with the rest of the family.

    Use it when the *shape* of the specular lobe is unknown or the surface is
    textured — feature matching, edge detection and correlation all work in this
    subspace without any of the assumptions
    :func:`specular_diffuse_split` needs.

    **This is a projection, not a picture.** The result loses one of three
    degrees of freedom (its component along ``G`` is exactly zero everywhere)
    and, for an image with negative values after black-level subtraction, keeps
    them. It is not a displayable "highlight-removed photo" and does not claim
    to be; for that, use :func:`specular_diffuse_split`.

    **Raises** ``ValueError``: *image_rgb* is not a valid ``(H, W, 3)`` linear
    RGB image (see :func:`specular_diffuse_split`); *illuminant_rgb* is not a
    non-zero 3-vector.
    """
    op = "specular_free_transform"
    I = _require_rgb(image_rgb, "image_rgb", op)
    gamma = _require_direction(illuminant_rgb, "illuminant_rgb", op)
    return I - (I @ gamma)[..., None] * gamma[None, None, :]


def illuminant_from_dichromatic_planes(image_rgb, labels, min_pixels=16,
                                       min_plane_ratio=1e-6,
                                       min_intersection_ratio=1e-6):
    """Recover the illuminant colour from two or more materials. → unit 3-vector.

    Lee's construction (1986). Under the dichromatic model every pixel of one
    material lies in the plane spanned by that material's body colour and the
    illuminant colour, so each material contributes a plane through the origin
    of RGB, and **all of those planes contain the illuminant direction**. Two
    materials with different body colours therefore intersect in exactly one
    line, and that line is the answer — a null-space computation, closed form.

    *labels* is an ``(H, W)`` integer map naming the material at each pixel;
    negative labels are ignored (background). Each material needs *min_pixels*
    pixels **and genuine highlight variation**: a material seen with no specular
    reflection at all has colours along a single ray, which defines no plane.
    That is measured by the second-to-first singular ratio of its colour matrix
    and rejected below *min_plane_ratio* rather than contributing an arbitrary
    normal.

    The returned direction is unit length with a positive component sum
    (illuminant colours are positive; the null space fixes the line, not the
    sign). On synthetic data with three known materials it reproduces the true
    illuminant to about 1e-16 (measured 8.0e-17 in
    ``tests/test_specularity.py``).

    *min_intersection_ratio* guards the answer itself: if the plane normals are
    nearly parallel — two materials whose body colours differ only in
    brightness, which is the same material twice — the intersection is
    ill-conditioned and the call raises instead of returning a direction picked
    by rounding error.

    **Raises** ``ValueError``: shape or dtype problems as in
    :func:`specular_diffuse_split`; *labels* is not an ``(H, W)`` integer map
    matching the image; more than :data:`MAX_MATERIALS` distinct labels; fewer
    than two materials survive the *min_pixels* and *min_plane_ratio* tests; the
    surviving planes do not intersect in a well-determined line.
    """
    op = "illuminant_from_dichromatic_planes"
    I = _require_rgb(image_rgb, "image_rgb", op)
    H, W, _ = I.shape
    min_pixels = _count(min_pixels, "min_pixels", 3, MAX_PIXELS)
    min_plane_ratio = _positive(min_plane_ratio, "min_plane_ratio")
    min_intersection_ratio = _positive(min_intersection_ratio,
                                       "min_intersection_ratio")
    if isinstance(labels, (str, bytes)):
        raise ValueError("%s: labels is a string" % (op,))
    lab = np.asarray(labels)
    if lab.dtype.kind not in ("i", "u"):
        raise ValueError("%s: labels must be an integer material map, got dtype "
                         "%r — float labels would be compared for equality "
                         "after rounding, which silently merges materials"
                         % (op, lab.dtype))
    if lab.shape != (H, W):
        raise ValueError("%s: labels must have shape %r to match the image, got "
                         "%r" % (op, (H, W), tuple(lab.shape)))
    uniq = np.unique(lab[lab >= 0])
    if uniq.size > MAX_MATERIALS:
        raise ValueError("%s: %d distinct material labels, over the %d cap "
                         "(specularity.MAX_MATERIALS) — a continuous-valued map "
                         "cast to int is the usual cause"
                         % (op, uniq.size, MAX_MATERIALS))
    P = I.reshape(-1, 3)
    flat = lab.reshape(-1)
    normals, used, skipped = [], [], []
    for k in uniq:
        pts = P[flat == k]
        if pts.shape[0] < min_pixels:
            skipped.append((int(k), "only %d pixel(s)" % pts.shape[0]))
            continue
        sv, vt = np.linalg.svd(pts, full_matrices=False)[1:]
        if sv[0] <= 0.0 or sv[1] <= min_plane_ratio * sv[0]:
            skipped.append((int(k), "colours span a ray, not a plane "
                                    "(s2/s1 = %.3g)"
                            % (sv[1] / sv[0] if sv[0] > 0 else 0.0)))
            continue
        normals.append(vt[2])                 # plane normal = smallest right sv
        used.append(int(k))
    if len(normals) < 2:
        raise ValueError("%s: need at least 2 materials whose colours span a "
                         "dichromatic plane; %d usable (%r), skipped %r. One "
                         "plane contains the illuminant but does not locate it"
                         % (op, len(normals), used, skipped))
    Nm = np.asarray(normals)                  # (K, 3)
    sv2, vt2 = np.linalg.svd(Nm, full_matrices=False)[1:]
    if sv2[1] <= min_intersection_ratio * sv2[0]:
        raise ValueError("%s: the %d dichromatic planes are nearly parallel "
                         "(second/first singular value %.3g), so their "
                         "intersection is not a well-determined line. Their "
                         "body colours must differ in chromaticity, not only in "
                         "brightness" % (op, len(normals), sv2[1] / sv2[0]))
    g = vt2[2]
    total = float(g.sum())
    if total < 0.0 or (total == 0.0 and g[int(np.argmax(np.abs(g)))] < 0.0):
        g = -g
    return g / float(np.linalg.norm(g))


# --------------------------------------------------------------------------- #
# reflectance lobes and the forward model                                      #
# --------------------------------------------------------------------------- #
def _lobe_geometry(normals, light, view, op):
    """Shared geometry: ``n.l``, ``n.v``, ``n.h``, ``v.h`` and the visibility."""
    n = _require_normals(normals, "normals", op)
    l = _require_direction(light, "light", op)
    v = _require_direction(view, "view", op)
    h = l + v
    hn = float(np.linalg.norm(h))
    if hn <= 0.0:
        raise ValueError("%s: light and view are exactly opposite, so the "
                         "half-vector is zero — no microfacet orientation can "
                         "produce that reflection" % (op,))
    h = h / hn
    ndl = n @ l
    ndv = n @ v
    ndh = n @ h
    vdh = float(v @ h)
    vis = (ndl > 0.0) & (ndv > 0.0)      # both shadowing and masking, so the
    # lobe stays reciprocal in l <-> v (a one-sided test would not be)
    return ndl, ndv, ndh, vdh, vis


def brdf_blinn_phong(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0),
                     shininess=32.0):
    """Blinn's half-vector specular lobe. → (H, W) in [0, 1].

    ``max(n.h, 0) ** shininess`` where ``h`` is the unit bisector of the light
    and view directions (Blinn 1977), zeroed wherever the surface faces away
    from either. Exactly 1 where the normal *is* the half-vector — the mirror
    condition — and it falls monotonically from there.

    **Unnormalised on purpose.** The classical Blinn-Phong lobe does not
    integrate to a fixed value; its peak is 1 and its energy grows as the
    exponent shrinks. It is a shading model, useful because its peak location is
    exact and because it is a *different* lobe shape from
    :func:`brdf_microfacet` — a separation routine that only works on one of the
    two is fitting the lobe, not the model. For an energy-consistent lobe use
    :func:`brdf_microfacet`.

    Reciprocal in light and view to machine precision (measured exactly 0.0
    maximum difference in ``tests/test_specularity.py``), because the
    half-vector is symmetric and the visibility test covers both sides.

    **Raises** ``ValueError``: *normals* is not an ``(H, W, 3)`` field or
    contains a zero-length normal; *light* / *view* are not non-zero 3-vectors;
    *shininess* is negative, non-finite, a string or a bool; light and view are
    exactly opposite.
    """
    op = "brdf_blinn_phong"
    shininess = _finite_scalar(shininess, "shininess")
    if shininess < 0.0:
        raise ValueError("shininess must be >= 0 (it is an exponent on a value "
                         "in [0, 1]; a negative exponent makes a grazing "
                         "microfacet brighter than a mirror), got %g" % shininess)
    _ndl, _ndv, ndh, _vdh, vis = _lobe_geometry(normals, light, view, op)
    lobe = np.power(np.clip(ndh, 0.0, 1.0), shininess)
    return np.where(vis, lobe, 0.0)


def brdf_microfacet(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0),
                    roughness=0.3, f0=0.04):
    """GGX / Trowbridge-Reitz microfacet specular BRDF. → (H, W), units 1/sr.

    ``f_s = D * G * F / (4 (n.l) (n.v))`` with

    * ``D`` the Trowbridge-Reitz (1975) / GGX normal distribution,
      ``a^2 / (pi * ((n.h)^2 (a^2 - 1) + 1)^2)`` for ``a = roughness^2``, which
      integrates to 1 against ``(n.h) dw`` over the hemisphere (measured
      relative error 4.1e-07 by quadrature in ``tests/test_specularity.py``);
    * ``G`` the separable Smith (1967) masking-shadowing term with the GGX
      lambda;
    * ``F`` Schlick's (1994) Fresnel approximation,
      ``f0 + (1 - f0) (1 - v.h)^5``. *f0* is the normal-incidence reflectance:
      about 0.04 for common dielectrics, 0.5 to 1.0 for metals. When the exact
      Fresnel curve matters, use ``match3d.fresnel_reflectance`` instead — this
      is the approximation the microfacet literature specifies, and it is named
      rather than hidden.

    Exact ground truth it reproduces: at normal incidence with light, view and
    normal aligned, every geometric factor is 1 and the value collapses to
    ``f0 / (4 pi roughness^4)`` in closed form. The lobe is reciprocal in light
    and view to machine precision, and its maximum sits at the half-vector.

    ``roughness`` is the perceptual parameter, squared once to reach the GGX
    ``alpha`` — the convention that makes a linear slider feel linear. A
    perfectly smooth surface (``roughness = 0``) is a delta function, not a
    finite BRDF, so it is refused rather than returned as an infinity.

    **Raises** ``ValueError``: geometry problems as in
    :func:`brdf_blinn_phong`; *roughness* outside ``(0, 1]``; *f0* outside
    ``[0, 1]``.
    """
    op = "brdf_microfacet"
    roughness = _positive(roughness, "roughness")
    if roughness > 1.0:
        raise ValueError("roughness must be in (0, 1], got %g" % roughness)
    f0 = _unit_interval(f0, "f0")
    ndl, ndv, ndh, vdh, vis = _lobe_geometry(normals, light, view, op)
    a = roughness * roughness
    a2 = a * a
    ch = np.clip(ndh, 0.0, 1.0)
    denom = ch * ch * (a2 - 1.0) + 1.0
    D = a2 / (np.pi * denom * denom)
    cl = np.clip(ndl, 1e-12, 1.0)
    cv = np.clip(ndv, 1e-12, 1.0)
    # Smith separable G1(x) = 2 (n.x) / ((n.x) + sqrt(a2 + (1 - a2) (n.x)^2))
    g1l = 2.0 * cl / (cl + np.sqrt(a2 + (1.0 - a2) * cl * cl))
    g1v = 2.0 * cv / (cv + np.sqrt(a2 + (1.0 - a2) * cv * cv))
    F = f0 + (1.0 - f0) * (1.0 - np.clip(vdh, 0.0, 1.0)) ** 5
    f = D * g1l * g1v * F / (4.0 * cl * cv)
    return np.where(vis, f, 0.0)


def dichromatic_render(normals, albedo_rgb=(0.80, 0.55, 0.35),
                       light=(0.3, 0.2, 1.0), illuminant_rgb=(1.0, 1.0, 1.0),
                       view=(0.0, 0.0, 1.0), specular=0.25, model="blinn_phong",
                       shininess=32.0, roughness=0.3, f0=0.04, ambient=0.0):
    """Forward dichromatic model: render a known highlight so a separation can be checked against it. → (H, W, 3).

    ``I = albedo_rgb * max(n.l, 0) + specular * lobe(n) * illuminant_unit``, the
    body term coming straight from :func:`photometric.render_lambertian` (called,
    not re-implemented, so the two modules cannot drift apart in convention) and
    the interface term carrying the **illuminant** colour, which is what makes
    the image obey the dichromatic model exactly.

    *albedo_rgb* may be a single ``(3,)`` colour — the single-material case that
    :func:`specular_diffuse_split` handles without help — or an ``(H, W, 3)``
    map, which is the textured case that needs ``body_rgb`` passed to the split.

    *model* selects the lobe: ``"blinn_phong"`` (*shininess*) or
    ``"microfacet"`` (*roughness*, *f0*). Both are available on purpose: the
    separation operators must be blind to the lobe shape, and swapping the model
    is how that is tested rather than asserted.

    **This is a shading model, not light transport.** No interreflection, no
    cast shadow, no subsurface term, no occlusion between pixels — the same
    boundary :mod:`visiondesign` draws. Its purpose is a synthetic image whose
    decomposition is known exactly.

    **Raises** ``ValueError``: geometry problems as in
    :func:`brdf_blinn_phong`; *albedo_rgb* is neither ``(3,)`` nor
    ``(H, W, 3)``; *specular* or *ambient* is negative, non-finite, a string or
    a bool; *model* is not in :data:`BRDF_MODELS`.
    """
    op = "dichromatic_render"
    n = _require_normals(normals, "normals", op)
    H, W, _ = n.shape
    gamma = _require_direction(illuminant_rgb, "illuminant_rgb", op)
    specular = _finite_scalar(specular, "specular")
    if specular < 0.0:
        raise ValueError("specular must be >= 0 (it is a reflected fraction), "
                         "got %g" % specular)
    ambient = _finite_scalar(ambient, "ambient")
    if ambient < 0.0:
        raise ValueError("ambient must be >= 0, got %g" % ambient)
    if model not in BRDF_MODELS:
        raise ValueError("model must be one of %r, got %r" % (BRDF_MODELS, model))
    A = _as_float_array(albedo_rgb, "albedo_rgb")
    if A.shape == (3,):
        A = np.broadcast_to(A, (H, W, 3))
    elif A.shape != (H, W, 3):
        raise ValueError("%s: albedo_rgb must be a (3,) colour or an (H, W, 3) "
                         "map matching the normals %r, got %r"
                         % (op, (H, W, 3), tuple(A.shape)))
    if (A < 0.0).any():
        raise ValueError("%s: albedo_rgb has %d negative component(s) — a "
                         "negative albedo emits light"
                         % (op, int((A < 0.0).sum())))
    # Body term: photometric's own Lambertian renderer with unit albedo gives
    # max(n.l, 0) + ambient, which we then colour. Same clipping, same light
    # normalisation, one implementation.
    shading = photometric.render_lambertian(n, 1.0, light, ambient).astype(np.float64)
    body = A * shading[..., None]
    if model == "blinn_phong":
        lobe = brdf_blinn_phong(n, light, view, shininess)
    else:
        lobe = brdf_microfacet(n, light, view, roughness, f0)
    interface = (specular * lobe)[..., None] * gamma[None, None, :]
    return body + interface


# --------------------------------------------------------------------------- #
# robust photometric stereo                                                    #
# --------------------------------------------------------------------------- #
def _light_subsets(n, max_subsets, seed):
    """3-light subsets: exhaustive when the count allows, else a fixed sample.

    Exhaustive enumeration is what makes the estimator deterministic — two runs
    give the same answer bit for bit and there is no seed to tune. Past
    *max_subsets* the enumeration is sampled with an explicit seed, and the
    number actually used is reported back to the caller so nobody has to guess
    which regime a result came from.
    """
    total = n * (n - 1) * (n - 2) // 6
    if total <= max_subsets:
        return list(itertools.combinations(range(n), 3)), total, True
    rng = np.random.default_rng(seed)
    seen, out = set(), []
    while len(out) < max_subsets:
        idx = tuple(sorted(rng.choice(n, size=3, replace=False).tolist()))
        if idx not in seen:
            seen.add(idx)
            out.append(idx)
    return out, total, False


def photometric_stereo_robust(images, lights, method="ransac", threshold=0.05,
                              max_subsets=512, normalize=True, seed=0,
                              min_inliers=3):
    """Photometric stereo that survives shadows and highlights. → (normals, albedo, inliers).

    Woodham's (1980) linear model ``I_n = albedo * max(n.L_n, 0)`` is exact only
    where every light reaches the pixel and the surface is Lambertian. A cast
    shadow zeroes one measurement, a highlight inflates another, and least
    squares spreads the error over the whole normal — the estimate does not
    fail, it **tilts**, which is worse. This operator solves the three-light
    system exactly on subsets and keeps the subset the data agrees with.

    *method*:

    * ``"lstsq"`` — the plain least-squares solution, delegated to
      :func:`photometric.photometric_stereo`. Present so the non-robust baseline
      is available through the same call and its failure is a measurement rather
      than a claim: with 3 of 8 lights blocked, the plain solve reaches 27.85
      degrees mean angular error where ``"ransac"`` reaches 0.00 degrees
      (measured in ``tests/test_specularity.py``).
    * ``"ransac"`` — Fischler-Bolles maximum consensus. Every 3-light subset is
      solved exactly, residuals are counted against *threshold*, and the subset
      with the largest consensus wins per pixel; the normal is then refitted by
      least squares on that consensus set. Tolerates up to ``N - 3`` bad lights
      if the good ones agree.
    * ``"median"`` — Rousseeuw's least median of squares. The subset minimising
      the median residual wins. Needs **more than half** the lights to be good,
      and needs no threshold at all — use it when the outlier magnitude is
      unknown.

    *threshold* is **relative to the brightest measurement at that pixel**, so
    the result is invariant to overall exposure: scaling every image by any
    positive constant returns bit-identical normals (verified in the tests).

    Enumeration is exhaustive and therefore deterministic whenever
    ``C(N, 3) <= max_subsets``; *seed* only matters past that point, and the
    regime is not hidden — a subset count above :data:`MAX_SUBSETS`, a pixel
    count above :data:`MAX_ROBUST_PIXELS` or a total work product above
    :data:`MAX_ROBUST_WORK` all raise instead of running for an hour.

    Returns ``(normals, albedo, inliers)``: ``normals`` ``(H, W, 3)`` float32
    unit vectors in :mod:`photometric`'s convention (``(0, 0, 1)`` where the
    albedo is degenerate), ``albedo`` ``(H, W)`` float32, and ``inliers``
    ``(N, H, W)`` bool — **which lights were believed at which pixel**. Pixels
    with fewer than *min_inliers* believed lights keep the winning subset's
    solution and are visible as a thin inlier count in that mask; that is the
    honest signal that the normal there rests on the minimum three
    measurements.

    **Raises** ``ValueError``: *images* is not an ``(N, H, W)`` stack or exceeds
    :data:`MAX_LIGHTS` / :data:`MAX_STACK_ELEMENTS` / :data:`MAX_ROBUST_PIXELS`;
    *lights* is not ``(N, 3)`` matching the frames or contains a zero-length
    direction; fewer than 3 lights; *method* not in :data:`ROBUST_METHODS`;
    *threshold* not positive; the work product exceeds
    :data:`MAX_ROBUST_WORK`; every 3-light subset is singular (all light
    directions coplanar through the origin, which no amount of robustness can
    repair).
    """
    op = "photometric_stereo_robust"
    if method not in ROBUST_METHODS:
        raise ValueError("method must be one of %r, got %r"
                         % (ROBUST_METHODS, method))
    I = _require_stack(images, "images", op)
    N, H, W = I.shape
    if N < 3:
        raise ValueError("%s: at least 3 light directions are required (three "
                         "unknowns per pixel), got %d" % (op, N))
    L = _require_lights(lights, N, op, normalize=bool(normalize))
    if method == "lstsq":
        normals, albedo = photometric.photometric_stereo(
            I, L, normalize=False)          # already normalised above if asked
        return normals, albedo, np.ones((N, H, W), dtype=bool)

    threshold = _positive(threshold, "threshold")
    max_subsets = _count(max_subsets, "max_subsets", 1, MAX_SUBSETS)
    min_inliers = _count(min_inliers, "min_inliers", 3, MAX_LIGHTS)
    P = H * W
    if P > MAX_ROBUST_PIXELS:
        raise ValueError("%s: %d pixels (shape %r), over the %d cap "
                         "(specularity.MAX_ROBUST_PIXELS). The consensus refit "
                         "holds a 3x3 normal matrix per pixel, so this bound is "
                         "what keeps that allocation bounded"
                         % (op, P, (H, W), MAX_ROBUST_PIXELS))
    subsets, total_subsets, exhaustive = _light_subsets(N, max_subsets, seed)
    work = len(subsets) * N * P
    if work > MAX_ROBUST_WORK:
        raise ValueError("%s: %d subsets x %d lights x %d pixels = %d units of "
                         "work, over the %d cap (specularity.MAX_ROBUST_WORK). "
                         "Lower max_subsets, crop the image, or use "
                         "method='lstsq'"
                         % (op, len(subsets), N, P, work, MAX_ROBUST_WORK))

    Iv = I.reshape(N, P)
    peak = np.abs(Iv).max(axis=0)
    tol = threshold * np.maximum(peak, np.finfo(np.float64).tiny)
    best_g = np.zeros((3, P))
    best_score = np.full(P, np.inf) if method == "median" else np.full(P, -1.0)
    best_tie = np.full(P, np.inf)
    n_used = 0
    for idx in subsets:
        Lt = L[list(idx)]                                   # (3, 3)
        if abs(float(np.linalg.det(Lt))) <= 1e-12:
            continue                                        # coplanar triple
        n_used += 1
        g = np.linalg.solve(Lt, Iv[list(idx)])              # (3, P) exact
        r = np.abs(L @ g - Iv)                              # (N, P)
        if method == "median":
            score = np.median(r, axis=0)
            take = score < best_score
            best_score = np.where(take, score, best_score)
        else:
            score = (r <= tol[None, :]).sum(axis=0).astype(np.float64)
            tie = np.median(r, axis=0)
            take = (score > best_score) | ((score == best_score) & (tie < best_tie))
            best_score = np.where(take, score, best_score)
            best_tie = np.where(take, tie, best_tie)
        best_g = np.where(take[None, :], g, best_g)
    if n_used == 0:
        raise ValueError("%s: every 3-light subset is singular — the light "
                         "directions are coplanar through the origin, so the "
                         "three components of the normal are not separable by "
                         "any method" % (op,))

    r_best = np.abs(L @ best_g - Iv)
    if method == "median":
        # Rousseeuw's scale estimate from the least median of squares.
        sigma = 1.4826 * (1.0 + 5.0 / max(N - 3, 1)) * best_score
        sigma = np.maximum(sigma, np.finfo(np.float64).tiny)
        inl = r_best <= 2.5 * sigma[None, :]
    else:
        inl = r_best <= tol[None, :]
    # Refit on the consensus set where it is big enough to be better than the
    # 3-light solve. Batched 3x3 normal equations, singular pixels left alone.
    w = inl.astype(np.float64)
    enough = w.sum(axis=0) >= min_inliers
    A = np.einsum("np,ni,nj->pij", w, L, L)
    b = np.einsum("np,ni->pi", w * Iv, L)
    det = np.linalg.det(A)
    ok = enough & (np.abs(det) > 1e-12 * np.maximum(
        np.abs(A).max(axis=(1, 2)) ** 3, np.finfo(np.float64).tiny))
    if ok.any():
        # (K, 3, 3) against (K, 3, 1): the trailing singleton is not decoration.
        # numpy's solve signature is (m,m),(m,n)->(m,n), so a bare (K, 3)
        # right-hand side is read as one 3x3 *matrix* broadcast over the batch.
        g_ref = np.linalg.solve(A[ok], b[ok][..., None])[..., 0]    # (K, 3)
        best_g[:, ok] = g_ref.T

    albedo = np.linalg.norm(best_g, axis=0)
    normals = np.zeros((3, P))
    good = albedo > 1e-8
    normals[:, good] = best_g[:, good] / albedo[good]
    normals[2, ~good] = 1.0
    return (normals.T.reshape(H, W, 3).astype(np.float32),
            albedo.reshape(H, W).astype(np.float32),
            inl.reshape(N, H, W))


def photometric_residual(images, lights, normals=None, albedo=None,
                         normalize=True):
    """How badly the Lambertian model fails, per pixel. → (H, W) RMS residual.

    ``sqrt(mean_n (albedo * (n.L_n) - I_n)^2)`` — the root-mean-square
    disagreement between the linear model and the measurements, in the units of
    the input radiance. Zero to machine precision on a synthetic Lambertian
    surface (measured maximum 1.3e-16 in ``tests/test_specularity.py``), and
    large exactly where the assumption broke: cast shadows, highlights,
    interreflections.

    This is the diagnostic that tells you *whether* you need
    :func:`photometric_stereo_robust` before you reach for it, and it is the
    map an inspection routine thresholds to find glossy defects.

    With *normals* and *albedo* omitted it solves them first with
    :func:`photometric.photometric_stereo` and reports the residual of that fit
    — the honest self-assessment of the plain estimator. Pass them to score an
    estimate that came from somewhere else (a robust fit, a CAD model, a
    previous frame).

    Note the residual uses ``n.L`` **without** the ``max(., 0)`` clamp, because
    that is the linear system the solver actually inverted; a pixel in attached
    shadow therefore shows a residual, which is the intended signal rather than
    an artefact.

    **Raises** ``ValueError``: *images* / *lights* problems as in
    :func:`photometric_stereo_robust`; *normals* is not ``(H, W, 3)`` matching
    the images; *albedo* is not ``(H, W)``; exactly one of *normals* / *albedo*
    is given (the pair is meaningless apart — the model is ``albedo * n``).
    """
    op = "photometric_residual"
    I = _require_stack(images, "images", op)
    N, H, W = I.shape
    if N < 3:
        raise ValueError("%s: at least 3 light directions are required, got %d"
                         % (op, N))
    L = _require_lights(lights, N, op, normalize=bool(normalize))
    if (normals is None) != (albedo is None):
        raise ValueError("%s: normals and albedo must be given together or not "
                         "at all — the model is albedo * normal and half of it "
                         "cannot be scored" % (op,))
    if normals is None:
        normals, albedo = photometric.photometric_stereo(I, L, normalize=False)
    n = _require_rgb(normals, "normals", op)
    if n.shape[:2] != (H, W):
        raise ValueError("%s: normals has shape %r but the images are %r"
                         % (op, tuple(n.shape), (H, W)))
    a = _require_map(albedo, "albedo", op)
    if a.shape != (H, W):
        raise ValueError("%s: albedo has shape %r but the images are %r"
                         % (op, tuple(a.shape), (H, W)))
    g = (a[..., None] * n).reshape(-1, 3).T                 # (3, P)
    r = L @ g - I.reshape(N, -1)                            # (N, P)
    return np.sqrt(np.mean(r * r, axis=0)).reshape(H, W)


# --------------------------------------------------------------------------- #
# polarisation                                                                 #
# --------------------------------------------------------------------------- #
#: The four orientations of a division-of-focal-plane polarisation sensor.
_DEFAULT_ANGLES = (0.0, 45.0, 90.0, 135.0)


def _polar_fit(images, angles_deg, op, max_violation_frac):
    """Fit ``I(t) = a0 + a1 cos 2t + a2 sin 2t`` per pixel and return the parts.

    Malus's law for partially polarised light: a linear analyser at angle ``t``
    transmits ``0.5 * (S0 + S1 cos 2t + S2 sin 2t)``. Three unknowns, so three
    angles determine it exactly and more are least squares.
    """
    I = _require_stack(images, "images", op)
    N, H, W = I.shape
    ang = _require_angles(angles_deg, N, op)
    M = _polarizer_design(ang, op)
    a = np.linalg.lstsq(M, I.reshape(N, -1), rcond=None)[0]     # (3, P)
    a0, a1, a2 = a[0], a[1], a[2]
    amp = np.hypot(a1, a2)
    i_min = a0 - amp
    bad = i_min < -1e-12 * np.maximum(np.abs(a0), 1.0)
    frac = float(bad.mean())
    if frac > max_violation_frac:
        worst = float(i_min.min())
        raise ValueError(
            "%s: the fitted minimum transmitted radiance is negative at %d of "
            "%d pixel(s) (%.3f, worst %.6g), so these frames are not a "
            "polariser sweep of a physical scene: the modulation amplitude "
            "exceeds the mean, which no analyser can produce. Check the frame "
            "order against angles_deg, or raise max_violation_frac to clamp "
            "sensor-noise-level violations to zero deliberately"
            % (op, int(bad.sum()), i_min.size, frac, worst))
    i_min = np.maximum(i_min, 0.0)
    return a0, a1, a2, amp, i_min, (H, W)


def polarization_render(diffuse, specular, angles_deg=_DEFAULT_ANGLES,
                        azimuth_deg=0.0):
    """Forward model of a polariser sweep: turn a known split into the frames a polarisation camera would record. → (N, H, W).

    ``I(t) = 0.5 * diffuse + specular * cos^2(t - azimuth)``. The diffuse term is
    treated as completely unpolarised, so it contributes half its radiance at
    every analyser angle; the specular term is treated as completely linearly
    polarised at *azimuth_deg*, so it follows Malus's law. Those are the two
    assumptions :func:`polarization_separate` inverts, and rendering with them
    is how the inversion gets a ground truth to be exact against.

    Physically the assumptions hold near Brewster's angle for a dielectric and
    fail at normal incidence; the module docstring says where. This operator
    does not model the incidence angle at all — it takes the two radiance maps
    you specify and produces the sweep they imply.

    **Raises** ``ValueError``: *diffuse* / *specular* are not 2-D arrays of the
    same shape, or are complex / masked / non-finite / string-typed; either has
    a negative value (a negative radiance is not a scene); *angles_deg* has
    fewer than 3 entries or does not determine the three unknowns.
    """
    op = "polarization_render"
    d = _require_map(diffuse, "diffuse", op)
    s = _require_map(specular, "specular", op)
    if d.shape != s.shape:
        raise ValueError("%s: diffuse %r and specular %r must have the same "
                         "shape" % (op, tuple(d.shape), tuple(s.shape)))
    for arr, name in ((d, "diffuse"), (s, "specular")):
        if (arr < 0.0).any():
            raise ValueError("%s: %s has %d negative value(s) (min %.6g) — a "
                             "negative radiance is not a scene"
                             % (op, name, int((arr < 0.0).sum()), float(arr.min())))
    ang = _as_float_array(angles_deg, "angles_deg")
    if ang.ndim != 1 or ang.size < 3:
        raise ValueError("%s: angles_deg must be a 1-D array of at least 3 "
                         "degrees, got shape %r" % (op, tuple(ang.shape)))
    if ang.size > MAX_LIGHTS:
        raise ValueError("%s: %d polariser angles, over the %d cap "
                         "(specularity.MAX_LIGHTS)" % (op, ang.size, MAX_LIGHTS))
    _polarizer_design(ang, op)              # same rank check as the inverse
    az = _finite_scalar(azimuth_deg, "azimuth_deg")
    if d.size * ang.size > MAX_STACK_ELEMENTS:
        raise ValueError("%s: %d frames x %d pixels is over the %d cap "
                         "(specularity.MAX_STACK_ELEMENTS)"
                         % (op, ang.size, d.size, MAX_STACK_ELEMENTS))
    t = np.radians(ang - az)[:, None, None]
    return 0.5 * d[None] + s[None] * np.cos(t) ** 2


def polarization_separate(images, angles_deg=_DEFAULT_ANGLES,
                          max_violation_frac=0.0):
    """Split a polariser sweep into its unpolarised and linearly polarised radiance. → (diffuse, specular), both (H, W).

    Fitting ``I(t) = 0.5 (S0 + S1 cos 2t + S2 sin 2t)`` per pixel gives
    ``I_min`` and ``I_max`` in closed form, and the classical separation
    (Wolff & Boult 1991; Nayar, Fang & Boult 1997) reads

        ``diffuse  = 2 * I_min``   (the unpolarised radiance)
        ``specular = I_max - I_min`` (the linearly polarised radiance)

    with ``diffuse + specular = I_min + I_max`` = the total scene radiance, so
    nothing is lost or invented. Round-tripping
    :func:`polarization_render` through this operator returns the inputs to
    about 1e-16 relative (measured in ``tests/test_specularity.py``).

    **Read the names as shorthand.** What is recovered exactly is the
    unpolarised and polarised parts. Calling them diffuse and specular assumes
    diffuse reflection is unpolarised and specular reflection is fully linearly
    polarised — true near Brewster's angle for a dielectric, **false at normal
    incidence**, where the specular reflection is unpolarised and this operator
    returns all of it as "diffuse", and unreliable for metals. The polarisation
    route is complementary to the colour route
    (:func:`specular_diffuse_split`), not a replacement: it needs no illuminant
    colour and works on textured, multi-material surfaces, but it needs a
    favourable geometry.

    *max_violation_frac* is the fraction of pixels allowed to fit a negative
    minimum radiance before the call fails. The default 0 is fail-closed: a
    negative fitted minimum means the modulation exceeded the mean, which no
    analyser can produce, and it usually means the frames and *angles_deg* are
    out of order. Raise it to clamp sensor-noise-level violations to zero as a
    deliberate, recorded choice.

    **Raises** ``ValueError``: *images* is not an ``(N, H, W)`` stack of at
    least 3 frames, or exceeds :data:`MAX_LIGHTS` / :data:`MAX_STACK_ELEMENTS`;
    *angles_deg* does not match the frame count or leaves the fit
    rank-deficient (two angles equal modulo 180); more than
    *max_violation_frac* of the pixels fit a negative minimum.
    """
    op = "polarization_separate"
    max_violation_frac = _finite_scalar(max_violation_frac, "max_violation_frac")
    if not (0.0 <= max_violation_frac <= 1.0):
        raise ValueError("max_violation_frac must be in [0, 1], got %g"
                         % max_violation_frac)
    a0, _a1, _a2, amp, i_min, (H, W) = _polar_fit(images, angles_deg, op,
                                                  max_violation_frac)
    i_max = a0 + amp
    return (2.0 * i_min).reshape(H, W), (i_max - i_min).reshape(H, W)


def polarization_dolp_map(images, angles_deg=_DEFAULT_ANGLES,
                          max_violation_frac=0.0):
    """Degree of linear polarisation, per pixel. → (H, W) in [0, 1].

    ``sqrt(S1^2 + S2^2) / S0``, from the same sinusoid fit as
    :func:`polarization_separate`. It answers the question that decides whether
    a polariser is worth mounting at all: **1** means the light at that pixel is
    fully linearly polarised and a crossed analyser extinguishes it completely,
    **0** means the polariser will only cost you a stop of exposure.

    Being a ratio, it is invariant to exposure exactly — scaling every frame by
    any positive constant returns bit-identical values — which is what makes it
    comparable across a production line where the lamps age.

    Pixels with zero total radiance have no degree of polarisation (every ratio
    would be 0/0) and are returned as 0.0 rather than as NaN; that is a
    convention, and it is stated here because a NaN spreading into a
    thresholding routine is exactly the silent failure this library refuses.

    **Raises** ``ValueError``: as :func:`polarization_separate`.
    """
    op = "polarization_dolp_map"
    max_violation_frac = _finite_scalar(max_violation_frac, "max_violation_frac")
    if not (0.0 <= max_violation_frac <= 1.0):
        raise ValueError("max_violation_frac must be in [0, 1], got %g"
                         % max_violation_frac)
    a0, _a1, _a2, amp, _i_min, (H, W) = _polar_fit(images, angles_deg, op,
                                                   max_violation_frac)
    dolp = np.zeros_like(a0)
    lit = a0 > 0.0
    np.divide(amp, a0, out=dolp, where=lit)
    return np.clip(dolp, 0.0, 1.0).reshape(H, W)


def polarization_stokes(images, angles_deg=_DEFAULT_ANGLES,
                        max_violation_frac=0.0):
    """The scene-integrated Stokes vector of a polariser sweep. → (4,), ready for :func:`optics.stokes_analyze`.

    Stokes parameters are linear in radiance, so the spatial mean of the frames
    has a Stokes vector that is the mean of the per-pixel ones — the vector a
    non-imaging polarimeter looking at the whole field would report. Fitting
    ``I(t) = 0.5 (S0 + S1 cos 2t + S2 sin 2t)`` gives ``(S0, S1, S2)`` directly.

    **S3 is always exactly 0, and that is a limitation, not a measurement.** A
    set of linear analysers cannot see circular polarisation; a quarter-wave
    plate is needed. The returned vector is therefore the linear part of the
    truth, and :func:`optics.stokes_analyze` will report ``handedness="linear"``
    for it no matter what the scene actually did. Returning an invented ``S3``
    would be worse, and returning a 3-vector would break the Stokes contract the
    optics family is built on.

    The result satisfies that contract by construction — ``S0 >= sqrt(S1^2 +
    S2^2 + S3^2)``, i.e. degree of polarisation at most 1 — because the same
    non-negativity check that guards :func:`polarization_separate` is exactly
    the condition for it. That is why ``optics.stokes_analyze`` accepts the
    output without a further test.

    **Raises** ``ValueError``: as :func:`polarization_separate`.
    """
    op = "polarization_stokes"
    max_violation_frac = _finite_scalar(max_violation_frac, "max_violation_frac")
    if not (0.0 <= max_violation_frac <= 1.0):
        raise ValueError("max_violation_frac must be in [0, 1], got %g"
                         % max_violation_frac)
    a0, a1, a2, amp, _i_min, _shape = _polar_fit(images, angles_deg, op,
                                                 max_violation_frac)
    s0 = 2.0 * float(a0.mean())
    s1 = 2.0 * float(a1.mean())
    s2 = 2.0 * float(a2.mean())
    pol = float(np.hypot(s1, s2))
    if pol > s0:
        # Reachable only when max_violation_frac allowed clamped pixels through:
        # the mean of clamped fits can break the inequality the fit guaranteed.
        # Scale the polarised part back rather than hand optics an unphysical
        # vector; the clamp the caller asked for is what caused it.
        if pol > 0.0:
            k = s0 / pol
            s1, s2 = s1 * k, s2 * k
    del amp
    return np.array([s0, s1, s2, 0.0], dtype=np.float64)

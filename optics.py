# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Optics operators for imaging systems and photonics (numpy + scipy only).

The layer *above* the lens and *below* the pixel. Industrial inspection and
Physical-AI perception both start with a decision nobody photographs — which
focal length, which f-number, how deep is the focus, how small can a defect be
before diffraction erases it, will the polariser kill the specular glare. Those
are closed-form calculations, and this module makes them first-class operators
in four families:

  * **geometric** — ``thin_lens`` / ``abcd_matrix`` / ``abcd_trace`` /
    ``depth_of_field`` / ``relative_illumination``: Gaussian imaging, paraxial
    ray transfer (the 2x2 ABCD algebra that composes a whole system), the
    photographic depth-of-field triple (near / far / hyperfocal) and the
    cos^4 natural-vignetting falloff.
  * **wave** — ``airy_pattern`` / ``angular_spectrum_propagate`` /
    ``fraunhofer_pattern`` / ``gaussian_beam``: the diffraction-limited PSF of
    a circular pupil, exact scalar free-space propagation by the angular
    spectrum, the far-field pattern of an aperture, and Gaussian-beam
    ``q``-parameter propagation (waist / wavefront radius / Gouy phase).
  * **imaging** — ``psf_to_mtf`` / ``mtf_diffraction`` / ``wavefront_stats``:
    the PSF -> OTF -> MTF chain that turns a measured spot into a resolution
    curve, the closed-form diffraction MTF to compare it against, and the
    wavefront statistics (RMS / PV / Strehl by Marechal) of a Zernike fit.
  * **polarisation** — ``jones_element`` / ``jones_apply`` /
    ``stokes_from_jones`` / ``mueller_element`` / ``mueller_apply`` /
    ``stokes_analyze``: the Jones calculus for fully-polarised light and the
    Stokes/Mueller calculus that also carries *partially* polarised light,
    which is what a real polarisation camera measures.

Deliberately **not** here (already owned elsewhere — imported and composed, never
re-implemented):

  * **Ray-surface interaction** lives in :mod:`match3d`: ``reflect`` (specular
    reflection), ``refract`` (vector Snell), ``snell_angle``,
    ``fresnel_reflectance`` (unpolarised s/p average) and
    ``normal_from_reflection`` (deflectometry). This module is paraxial and
    scalar; when you need a real ray bent at a real surface, call those.
  * **Zernike *fitting*** is :func:`match3d.fit_zernike` (disk image ->
    ``{(n, m): coefficient}``). :func:`wavefront_stats` consumes exactly that
    dict and reports the statistics — it re-uses ``match3d``'s own basis
    builder, so the two cannot drift apart in convention.
  * **PSF blur / deconvolution** is :mod:`volrestore` (``vol_gaussian_psf``,
    ``vol_richardson_lucy``) and :mod:`complexops` (``cx_wiener_deconvolve``).
    :func:`psf_to_mtf` only *characterises* a PSF; it does not deblur.
  * **FFT and complex-image plumbing** is :mod:`complexops` (``cx_fft`` and
    friends, ``phase_unwrap``). :func:`angular_spectrum_propagate` uses numpy's
    FFT internally but its input/output are *fields*, not spectra.
  * **Phase-shifting interferometry / fringe projection** is :mod:`fringe`
    (``wrapped_phase`` is the general N-step algorithm, ``unwrap_phase_2d``,
    ``phase_to_height``). A 4-step PSI op here would be a duplicate.

Units are encoded in every parameter name — ``_mm``, ``_um``, ``_deg``,
``_mrad``, ``_per_mm`` — because a silent millimetre/micrometre swap is a
plausible-wrong answer, not a crash. Nothing is normalised behind your back and
nothing guesses a unit from magnitude.

Sign conventions, stated once (the traps):

  * **Imaging (:func:`thin_lens`)**: the real-is-positive convention. Object
    distance ``s_o > 0`` is measured from the lens toward the object, image
    distance ``s_i > 0`` on the far side. ``1/f = 1/s_o + 1/s_i``.
    Magnification ``m = -s_i / s_o`` — *negative m means the image is
    inverted*, which is the normal case for a real image. A diverging lens
    (``f < 0``) yields ``s_i < 0`` = a virtual image on the object side.
  * **Paraxial rays (:func:`abcd_matrix`)**: state ``[y, theta]`` with ``y`` in
    mm and ``theta`` in **radians** internally (the API takes and returns
    milliradians). Elements are listed **in the order light meets them**, and
    the product is formed right-to-left accordingly. ``det(M) = n_in / n_out``,
    so ``det = 1`` exactly when the system starts and ends in the same medium —
    that identity is the cheapest self-check there is.
  * **Wave propagation (:func:`angular_spectrum_propagate`)**: the
    ``exp(-i*omega*t)`` time convention, so forward propagation multiplies by
    ``exp(+i*k_z*z)``. Evanescent components are **attenuated**, not zeroed,
    with ``exp(-2*pi*|z|*sqrt(-arg))`` — that keeps ``z = 0`` an exact identity
    and makes a forward/backward round trip exact for a band-limited field.
  * **Polarisation**: ``S2 = 2*Re(Ex*conj(Ey))``, ``S3 = 2*Im(Ex*conj(Ey))``,
    so ``S3 > 0`` is right-circular in this (``exp(-i*omega*t)``) convention.
    A retarder is symmetric: ``diag(exp(-i*d/2), exp(+i*d/2))`` with the fast
    axis along x before rotation. The Jones and Mueller families are pinned
    against *each other* in the tests, which is the only way a sign slip in one
    of them gets caught.

Honest disclosure (what these ops cannot do):

  * **Every geometric op here is paraxial and thin.** No aberrations, no
    thickness, no pupil aberration, no vignetting from mechanical stops. A real
    lens departs from ``1/f = 1/s + 1/s'`` and from ``cos^4`` — treat these as
    the *design starting point*, not as a lens model. ``relative_illumination``
    in particular is the ideal cosine-fourth law; real wide-angle lenses are
    deliberately designed away from it.
  * **The Marechal Strehl approximation is only valid for small aberration.**
    ``exp(-(2*pi*sigma)^2)`` is a series truncation; past roughly 0.1 waves RMS
    it overestimates. :func:`wavefront_stats` returns ``marechal_valid`` saying
    whether you are inside that range instead of quietly handing you a number.
  * **The scalar diffraction model ignores polarisation and high NA.** The
    angular spectrum is exact for a scalar field, but a real high-NA system
    needs a vector treatment; ``mtf_diffraction`` and ``airy_pattern`` assume a
    circular, unobstructed, aberration-free pupil.
  * **Two ops return a documented infinity** (never a silent one):
    :func:`depth_of_field` returns ``far_mm = inf`` at or beyond the hyperfocal
    distance, and :func:`gaussian_beam` returns ``wavefront_radius_mm = inf``
    at the waist, because a plane wavefront *is* infinite radius. Both also
    report a finite reciprocal so downstream arithmetic has a safe path.

Fail-closed on untrusted input, like every Fullseye module: units and shapes are
exact, NaN/Inf are rejected on the way in, a zero focal length / zero radius /
non-positive refractive index / opaque aperture / unphysical Stokes vector all
raise an explicit ``ValueError`` naming the problem — never a silent NaN, a
silent clamp, or a silent zero-division. Grid sizes are capped
(:data:`MAX_GRID`, :data:`MAX_FIELD_ELEMENTS`) so a mistyped exponent fails
instead of allocating the machine's memory.
"""
from __future__ import annotations

import warnings

import numpy as np

__all__ = [
    "thin_lens", "abcd_matrix", "abcd_trace", "depth_of_field",
    "relative_illumination",
    "airy_pattern", "angular_spectrum_propagate", "fraunhofer_pattern",
    "gaussian_beam",
    "psf_to_mtf", "mtf_diffraction", "wavefront_stats",
    "jones_element", "jones_apply", "stokes_from_jones",
    "mueller_element", "mueller_apply", "stokes_analyze",
    "OPTICS", "MAX_GRID", "MAX_FIELD_ELEMENTS", "MAX_SYSTEM_ELEMENTS",
    "MAX_ZERNIKE_TERMS", "MAX_ZERNIKE_ORDER", "MAX_ZERNIKE_BASIS",
    "JONES_KINDS", "MUELLER_KINDS",
]

#: The public optics operators, by name (introspection / facade wiring).
OPTICS = [
    "thin_lens", "abcd_matrix", "abcd_trace", "depth_of_field",
    "relative_illumination",
    "airy_pattern", "angular_spectrum_propagate", "fraunhofer_pattern",
    "gaussian_beam",
    "psf_to_mtf", "mtf_diffraction", "wavefront_stats",
    "jones_element", "jones_apply", "stokes_from_jones",
    "mueller_element", "mueller_apply", "stokes_analyze",
]

#: Largest side length for a *generated* grid (Airy pattern, sampled curves).
#: 4096^2 float64 = 128 MB, which is already past useful for a design aid.
MAX_GRID = 4096

#: Largest element count for a *supplied* field / PSF / aperture (2^24 elements
#: = 128 MB complex128 per FFT temporary, and the angular spectrum needs three).
MAX_FIELD_ELEMENTS = 1 << 24

#: Largest number of elements in one ABCD system description.
MAX_SYSTEM_ELEMENTS = 1024

#: Largest number of Zernike terms :func:`wavefront_stats` will accept.
MAX_ZERNIKE_TERMS = 512

#: Largest radial order ``n`` :func:`wavefront_stats` will accept. The shared
#: basis builder (``match3d._zernike_basis``) evaluates the radial polynomial
#: from its factorial definition, which cancels catastrophically at high order:
#: measured 2026-09-01, ``max|Z_n^m|`` over the unit disk is exactly 1.0 (the
#: analytic bound) through ``n = 44``, then 1.41 at ``n = 46``, 71.5 at
#: ``n = 50`` and 2.8e5 at ``n = 60``. Past the cap the numbers are garbage that
#: looks like a wavefront, so they are refused rather than returned.
MAX_ZERNIKE_ORDER = 40

#: Largest working set (float64 elements) for the Zernike basis
#: :func:`wavefront_stats` builds. The builder evaluates *every* ``(n, m)`` up to
#: ``n_max`` on the whole polar grid, so the allocation is
#: ``(n_max+1)(n_max+2)/2 * radial * angular`` — quadratic in an argument that
#: looks innocent. 2^25 elements = 268 MB, which admits ``n_max = 40`` on the
#: default grid (21 M) and refuses ``n_max = 40`` at 4096x4096 (1.4e10 = 108 GB).
MAX_ZERNIKE_BASIS = 1 << 25

#: Jones element kinds accepted by :func:`jones_element`.
JONES_KINDS = ("polarizer", "retarder", "quarter_wave", "half_wave", "rotator")

#: Mueller element kinds accepted by :func:`mueller_element`. Note the extra
#: ``depolarizer``: it has **no** Jones counterpart, which is precisely why the
#: Mueller calculus exists (Jones can only describe fully polarised light).
MUELLER_KINDS = ("polarizer", "retarder", "quarter_wave", "half_wave",
                 "rotator", "depolarizer")

#: Marechal's approximation is a truncated series; past this RMS (in waves) the
#: Strehl it predicts is optimistic. Reported as ``marechal_valid``, not hidden.
MARECHAL_RMS_LIMIT = 0.1


# --------------------------------------------------------------------------- #
# fail-closed input helpers                                                    #
# --------------------------------------------------------------------------- #
def _finite_scalar(v, name: str) -> float:
    """A real, finite Python float — or ``ValueError`` naming the problem."""
    if np.ma.is_masked(v):
        raise ValueError("%s is a masked value — fill or drop it explicitly" % (name,))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s is complex — an optical length/angle is a real "
                         "quantity; coercion would silently drop the imaginary "
                         "part" % (name,))
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s is a bool — refusing the silent True==1 promotion"
                         % (name,))
    if isinstance(v, (str, bytes, np.str_, np.bytes_)):
        # float("50") succeeds, so without this a *string* passes as a length
        # and the caller never learns their config was never parsed. Confirmed
        # by the 2026-09-01 adversarial pass: thin_lens("50", "200") returned a
        # perfectly plausible 66.667 mm.
        raise ValueError("%s is a string (%r) — a length/angle must be a number; "
                         "float('50') would silently succeed and hide an "
                         "unparsed configuration value" % (name, v))
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


def _nonzero(v, name: str, why: str) -> float:
    f = _finite_scalar(v, name)
    if f == 0.0:
        raise ValueError("%s must not be 0 — %s" % (name, why))
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
    """Coerce to float64, refusing the two silent-truncation traps."""
    if np.ma.is_masked(a):
        raise ValueError("%s is a masked array with masked (invalid) entries — "
                         "coercion would strip the mask and use the raw values "
                         "underneath; fill or drop them explicitly" % (name,))
    if np.iscomplexobj(a):
        raise ValueError("%s is complex — coercion to float64 would silently "
                         "discard the imaginary part; take .real/.imag/abs() "
                         "explicitly" % (name,))
    arr = np.ascontiguousarray(a, dtype=np.float64)
    if not np.isfinite(arr).all():
        n = int((~np.isfinite(arr)).sum())
        raise ValueError("%s has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (name, n))
    return arr


def _as_complex_array(a, name: str) -> np.ndarray:
    """Coerce to complex128 (real input is promoted, which loses nothing)."""
    if np.ma.is_masked(a):
        raise ValueError("%s is a masked array with masked (invalid) entries — "
                         "fill or drop them explicitly" % (name,))
    arr = np.ascontiguousarray(a, dtype=np.complex128)
    if not np.isfinite(arr).all():
        n = int((~np.isfinite(arr)).sum())
        raise ValueError("%s has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (name, n))
    return arr


def _require_image(a, name: str, op: str, complex_ok: bool = False) -> np.ndarray:
    """A strictly 2-D, at-least-2x2, finite, size-capped array."""
    arr = _as_complex_array(a, name) if complex_ok else _as_float_array(a, name)
    if arr.ndim != 2:
        raise ValueError("%s: %s must be a 2-D array, got a %d-D array of shape "
                         "%r — nothing is reshaped silently"
                         % (op, name, arr.ndim, tuple(np.shape(a))))
    if arr.shape[0] < 2 or arr.shape[1] < 2:
        raise ValueError("%s: %s must be at least 2x2, got %dx%d (a 1-pixel-wide "
                         "grid has no sampled spatial frequency)"
                         % (op, name, arr.shape[0], arr.shape[1]))
    if arr.size > MAX_FIELD_ELEMENTS:
        raise ValueError("%s: %s has %d elements (shape %r), over the %d cap "
                         "(optics.MAX_FIELD_ELEMENTS)"
                         % (op, name, arr.size, arr.shape, MAX_FIELD_ELEMENTS))
    return arr


def _require_vec(a, name: str, op: str, length: int,
                 complex_ok: bool = False) -> np.ndarray:
    """A strictly 1-D vector of exactly *length* components."""
    arr = _as_complex_array(a, name) if complex_ok else _as_float_array(a, name)
    if arr.ndim != 1:
        raise ValueError("%s: %s must be a 1-D vector, got a %d-D array of shape "
                         "%r" % (op, name, arr.ndim, tuple(np.shape(a))))
    if arr.size != length:
        raise ValueError("%s: %s must have exactly %d component(s), got %d"
                         % (op, name, length, arr.size))
    return arr


# --------------------------------------------------------------------------- #
# geometric optics                                                             #
# --------------------------------------------------------------------------- #
def thin_lens(focal_mm=50.0, object_mm=200.0):
    """Gaussian thin-lens imaging: where the image lands and how big it is.

    Solves ``1/f = 1/s_o + 1/s_i`` in the **real-is-positive** convention:
    *object_mm* (``s_o``) is the lens-to-object distance and must be positive;
    the returned ``image_mm`` (``s_i``) is positive for a real image on the far
    side of the lens and **negative for a virtual image** on the object side
    (which is what a diverging lens, ``focal_mm < 0``, always produces).

    Returns a dict: ``image_mm`` · ``magnification`` ``m = -s_i/s_o``
    (*negative = inverted*, the normal case for a real image; ``|m| < 1`` is a
    demagnified, i.e. machine-vision, geometry) · ``object_mm`` and
    ``focal_mm`` echoed back so a table of results is self-describing ·
    ``working_distance_mm`` ``= s_o + s_i`` for a real image, the
    object-to-sensor span a machine builder actually has to fit.

    Ground truth it reproduces exactly (verified in ``tests/test_optics.py``):
    ``f = 50, s_o = 200`` gives ``s_i = 200/3 = 66.6667`` and ``m = -1/3``; at
    ``s_o = 2f`` the image is at ``2f`` with ``m = -1`` (the 1:1 conjugate);
    the reciprocal identity ``1/f - 1/s_o - 1/s_i`` is 0 to machine precision
    over the whole tested range.

    **Raises** ``ValueError``: ``focal_mm == 0`` (not a lens), non-positive or
    non-finite *object_mm*, and — explicitly, instead of returning ``inf`` —
    ``object_mm == focal_mm``, where the object sits at the front focal point
    and images at infinity (a collimator, not an imaging conjugate).

    Paraxial and thin: no aberration, no principal-plane separation. HALCON has
    no equivalent (its camera model starts after the lens, at the projection).
    """
    f = _nonzero(focal_mm, "focal_mm",
                 "a zero focal length is not a lens (infinite power)")
    s_o = _positive(object_mm, "object_mm")
    denom = s_o - f
    if denom == 0.0:
        raise ValueError("thin_lens: object_mm == focal_mm (%g) — the object is "
                         "at the front focal point and images at infinity; that "
                         "is a collimator, not an imaging conjugate (refusing to "
                         "return inf)" % (f,))
    s_i = f * s_o / denom
    m = -s_i / s_o
    return {"image_mm": float(s_i), "magnification": float(m),
            "object_mm": float(s_o), "focal_mm": float(f),
            "working_distance_mm": float(s_o + s_i)}


def _element_matrix(el, index: int) -> tuple:
    """One ABCD element -> (2x2 matrix, n_in, n_out). Fail-closed on anything else."""
    if isinstance(el, str) or not isinstance(el, (list, tuple, np.ndarray)):
        raise ValueError("abcd_matrix: element %d must be a sequence like "
                         "('free', 100.0), got %r" % (index, type(el).__name__))
    seq = list(el)
    if not seq:
        raise ValueError("abcd_matrix: element %d is empty" % (index,))
    kind = seq[0]
    if not isinstance(kind, str):
        raise ValueError("abcd_matrix: element %d must start with a kind string "
                         "(one of free/lens/mirror/interface/curved), got %r"
                         % (index, type(kind).__name__))
    kind = kind.strip().lower()
    name = "abcd_matrix element %d (%s)" % (index, kind)

    def _need(n):
        if len(seq) != n + 1:
            raise ValueError("abcd_matrix: element %d kind %r takes %d "
                             "parameter(s), got %d" % (index, kind, n, len(seq) - 1))

    if kind == "free":
        _need(1)
        d = _finite_scalar(seq[1], name + " distance_mm")
        if d < 0.0:
            raise ValueError("abcd_matrix: element %d free-space distance must "
                             "be >= 0, got %g (light does not run backwards; "
                             "reverse the element order instead)" % (index, d))
        return np.array([[1.0, d], [0.0, 1.0]]), 1.0, 1.0
    if kind == "lens":
        _need(1)
        f = _nonzero(seq[1], name + " focal_mm",
                     "a zero focal length is infinite power")
        return np.array([[1.0, 0.0], [-1.0 / f, 1.0]]), 1.0, 1.0
    if kind == "mirror":
        _need(1)
        r = _nonzero(seq[1], name + " radius_mm",
                     "a zero radius of curvature is a point, not a mirror "
                     "(use ('free', 0.0) for a flat mirror in the unfolded system)")
        return np.array([[1.0, 0.0], [-2.0 / r, 1.0]]), 1.0, 1.0
    if kind == "interface":
        _need(2)
        n1 = _positive(seq[1], name + " n1")
        n2 = _positive(seq[2], name + " n2")
        return np.array([[1.0, 0.0], [0.0, n1 / n2]]), n1, n2
    if kind == "curved":
        _need(3)
        n1 = _positive(seq[1], name + " n1")
        n2 = _positive(seq[2], name + " n2")
        r = _nonzero(seq[3], name + " radius_mm",
                     "a zero radius is a point; use kind 'interface' for a flat "
                     "surface")
        return (np.array([[1.0, 0.0], [(n1 - n2) / (n2 * r), n1 / n2]]), n1, n2)
    raise ValueError("abcd_matrix: element %d has unknown kind %r — expected one "
                     "of free/lens/mirror/interface/curved" % (index, kind))


def abcd_matrix(elements):
    """Compose a paraxial system into one 2x2 ray-transfer (ABCD) matrix.

    *elements* is a sequence of ``(kind, *params)`` **in the order light meets
    them** (the matrix product is formed right-to-left accordingly, so the list
    reads like the optical layout, not like the algebra):

    ``("free", d_mm)`` free-space / homogeneous medium of length ``d >= 0`` ·
    ``("lens", f_mm)`` thin lens of focal length ``f != 0`` (negative =
    diverging) · ``("mirror", r_mm)`` curved mirror of radius ``r`` in the
    unfolded system (power ``-2/r``) · ``("interface", n1, n2)`` flat refracting
    surface · ``("curved", n1, n2, r_mm)`` curved refracting surface.

    Returns a ``(2, 2)`` float64 matrix acting on the ray state
    ``[y_mm, theta_rad]`` — feed it to :func:`abcd_trace`, which handles the
    milliradian conversion at the API boundary.

    Ground truth it reproduces exactly: a single free-space section is
    ``[[1, d], [0, 1]]``; ``det(M) = n_in / n_out``, hence **exactly 1** for any
    system that starts and ends in the same medium (checked to ~1e-16 in the
    tests, and the cheapest correctness self-check you have); two thin lenses
    separated by ``d`` compose to the classical combined power
    ``1/f = 1/f1 + 1/f2 - d/(f1*f2)``; a lens sandwiched between two
    free-space sections of length ``f`` gives the ``[[0, f], [-1/f, 0]]``
    Fourier-transform geometry.

    **Raises** ``ValueError``: an empty system, more than
    :data:`MAX_SYSTEM_ELEMENTS` elements, an element that is not a sequence, an
    unknown kind, the wrong parameter count for a kind, a negative free-space
    distance (reverse the list instead of running light backwards), a zero
    focal length or radius, a non-positive refractive index, or any non-finite
    parameter.

    HALCON: no equivalent (its optics stop at the pinhole camera model).
    """
    if isinstance(elements, (str, bytes)) or not isinstance(
            elements, (list, tuple, np.ndarray)):
        raise ValueError("abcd_matrix: elements must be a sequence of "
                         "(kind, *params) tuples, got %r"
                         % (type(elements).__name__,))
    seq = list(elements)
    if not seq:
        raise ValueError("abcd_matrix: the system is empty — an optical system "
                         "with no elements has no ray-transfer matrix (pass "
                         "[('free', 0.0)] if you want the identity)")
    if len(seq) > MAX_SYSTEM_ELEMENTS:
        raise ValueError("abcd_matrix: %d elements exceeds the %d cap "
                         "(optics.MAX_SYSTEM_ELEMENTS)"
                         % (len(seq), MAX_SYSTEM_ELEMENTS))
    total = np.eye(2, dtype=np.float64)
    for i, el in enumerate(seq):
        m, _n1, _n2 = _element_matrix(el, i)
        total = m @ total                      # light meets seq[0] first
    if not np.isfinite(total).all():
        raise ValueError("abcd_matrix: the composed matrix overflowed float64 — "
                         "the system mixes lengths and powers many orders of "
                         "magnitude apart; rescale to consistent millimetres")
    return np.ascontiguousarray(total, dtype=np.float64)


def abcd_trace(matrix, height_mm=1.0, angle_mrad=0.0):
    """Propagate one paraxial ray through an ABCD matrix.

    Applies ``[y', theta'] = M @ [y, theta]`` with ``y`` in millimetres and
    ``theta`` in radians internally; the API speaks **milliradians** because a
    paraxial angle is small by definition and mrad keeps the numbers readable.

    Returns a dict: ``height_mm`` and ``angle_mrad`` of the outgoing ray ·
    ``determinant`` of *M* (``= n_in/n_out``; a value that is not 1 for a
    same-medium system means the matrix is wrong, so it is reported rather than
    assumed) · ``imaging`` — True when ``|B| <= 1e-12 * (1 + |A| + |C| + |D|)``,
    i.e. the output height does not depend on the input angle, which is the
    definition of a conjugate (image) plane.

    Ground truth it reproduces exactly: free space of length ``d`` gives
    ``y' = y + d*theta`` and ``theta' = theta``; a thin lens leaves ``y``
    untouched and bends the ray by ``-y/f``; a ray parallel to the axis
    (``angle_mrad = 0``) entering a lens crosses the axis exactly one focal
    length behind it.

    **Raises** ``ValueError``: *matrix* is not ``(2, 2)``, is complex or masked,
    holds NaN/Inf, or has a determinant of 0 (a system that collapses every ray
    to a point is not a ray-transfer matrix); non-finite *height_mm* /
    *angle_mrad*; a result that overflowed float64.
    """
    m = _as_float_array(matrix, "matrix")
    if m.shape != (2, 2):
        raise ValueError("abcd_trace: matrix must be (2, 2), got shape %r — an "
                         "ABCD matrix is 2x2 by construction (build one with "
                         "abcd_matrix)" % (m.shape,))
    y = _finite_scalar(height_mm, "height_mm")
    th = _finite_scalar(angle_mrad, "angle_mrad") * 1e-3
    with np.errstate(over="ignore", invalid="ignore"):
        det = float(m[0, 0] * m[1, 1] - m[0, 1] * m[1, 0])
    if not np.isfinite(det):
        # Confirmed 2026-09-01: diag(1e200, 1e200) traced a *finite* ray while
        # handing back determinant = inf in the dict — a silent non-finite that
        # every downstream check would have believed.
        raise ValueError("abcd_trace: the determinant overflowed float64 "
                         "(matrix entries up to %g) — this is not a physically "
                         "scaled ray-transfer matrix; work in millimetres"
                         % (float(np.abs(m).max()),))
    if det == 0.0:
        raise ValueError("abcd_trace: matrix is singular (det = 0) — a "
                         "ray-transfer matrix has det = n_in/n_out > 0; this "
                         "one maps every ray onto a single state")
    out = m @ np.array([y, th], dtype=np.float64)
    if not np.isfinite(out).all():
        raise ValueError("abcd_trace: the traced ray overflowed float64 "
                         "(y=%g mm, theta=%g mrad through a matrix of norm %g)"
                         % (y, th * 1e3, float(np.abs(m).max())))
    scale = 1.0 + float(np.abs(m).sum())
    return {"height_mm": float(out[0]), "angle_mrad": float(out[1] * 1e3),
            "determinant": det, "imaging": bool(abs(m[0, 1]) <= 1e-12 * scale)}


def depth_of_field(focal_mm=50.0, f_number=8.0, subject_mm=2000.0, coc_mm=0.03):
    """Photographic depth of field: near limit, far limit and hyperfocal distance.

    The classical circle-of-confusion model. With ``H = f^2/(N*c) + f`` the
    hyperfocal distance and ``s`` the focused subject distance:

    ``near = s*(H - f) / (H + s - 2f)`` and ``far = s*(H - f) / (H - s)``.

    Returns a dict: ``near_mm`` · ``far_mm`` · ``depth_mm`` (``far - near``) ·
    ``hyperfocal_mm`` · ``far_is_infinite`` (a bool, so a caller never has to
    test for ``inf`` by accident).

    **``far_mm`` is ``inf`` at or beyond the hyperfocal distance, by contract,
    not by accident** — focus at ``H`` and everything from ``H/2`` to infinity
    is acceptably sharp, which is the whole point of the hyperfocal distance.
    ``depth_mm`` is then ``inf`` too. ``far_is_infinite`` says so explicitly,
    and the identity ``near(H) == H/2`` is exact (verified in the tests).

    *coc_mm* is the acceptable circle of confusion **in the image plane**: the
    35 mm convention is 0.03 mm, a machine-vision rule of thumb is 1-2 pixel
    pitches. It is a *choice*, not a property of the lens — halve it and the
    depth of field halves with it, which is why two depth-of-field calculators
    disagree.

    Ground truth: ``f = 50, N = 8, c = 0.03`` gives ``H = 10466.67 mm``; at
    ``s = H`` the near limit is exactly ``H/2 = 5233.33 mm`` and the far limit
    is ``inf``; the near/far limits bracket the subject for every ``s < H``.

    **Raises** ``ValueError``: non-positive or non-finite *focal_mm*,
    *f_number*, *subject_mm*, *coc_mm*; ``subject_mm <= focal_mm`` (an object
    inside the front focal length cannot be imaged by this lens — see
    :func:`thin_lens`); a hyperfocal distance that is not greater than the
    focal length (a degenerate combination of ``N`` and ``c``).

    Paraxial, thin, and blur-circle based: it ignores diffraction, which for
    small apertures becomes the real resolution limit — compare with
    :func:`mtf_diffraction` before trusting an ``N = 22`` calculation.
    """
    f = _positive(focal_mm, "focal_mm")
    n = _positive(f_number, "f_number")
    s = _positive(subject_mm, "subject_mm")
    c = _positive(coc_mm, "coc_mm")
    if s <= f:
        raise ValueError("depth_of_field: subject_mm (%g) must be greater than "
                         "focal_mm (%g) — an object at or inside the front focal "
                         "length has no real image (see thin_lens)" % (s, f))
    h = f * f / (n * c) + f
    if h <= f:
        raise ValueError("depth_of_field: the hyperfocal distance (%g mm) is not "
                         "greater than the focal length — f_number*coc_mm is far "
                         "too large for this lens" % (h,))
    near = s * (h - f) / (h + s - 2.0 * f)
    if s >= h:
        far = float("inf")
        depth = float("inf")
    else:
        far = s * (h - f) / (h - s)
        depth = far - near
    return {"near_mm": float(near), "far_mm": float(far), "depth_mm": float(depth),
            "hyperfocal_mm": float(h), "far_is_infinite": bool(s >= h)}


def relative_illumination(half_angle_deg=20.0, samples=64, exponent=4.0):
    """Natural vignetting: relative image-plane illuminance versus field angle.

    The cosine-fourth law ``E(theta)/E(0) = cos(theta)^4`` — one cosine from the
    inverse-square increase in distance to the off-axis point (twice), one from
    the tilt of the exit pupil as seen from there, one from the tilt of the
    image plane. Sampled uniformly in angle from 0 to *half_angle_deg*.

    Returns an ``(samples, 2)`` float64 ``pairs`` array: column 0 the field
    angle in degrees, column 1 the relative illuminance in [0, 1].

    *exponent* exists because the fourth power is the *ideal symmetric* case:
    a lens with pupil aberration, or a telecentric design, or one with a tilted
    entrance pupil, falls off closer to ``cos^3`` (or is deliberately corrected
    flatter still). Setting the exponent is how you say which lens you have —
    it is not a fudge factor to be tuned after the fact.

    Ground truth it reproduces exactly: ``cos^4(45 deg) = 1/4`` and
    ``cos^4(60 deg) = 1/16``, both to machine precision; the curve is 1.0 on
    axis and monotonically decreasing.

    **Raises** ``ValueError``: *half_angle_deg* outside ``(0, 90)`` — at 90
    degrees the illuminance is exactly 0 and the "relative" curve carries no
    information; *samples* outside ``[2, MAX_GRID]``; a negative or non-finite
    *exponent*.

    This is the *natural* falloff only. Mechanical vignetting (a stop clipping
    the oblique beam) is a separate, lens-specific effect that no closed form
    covers — measure it with a flat field.
    """
    a = _finite_scalar(half_angle_deg, "half_angle_deg")
    if not (0.0 < a < 90.0):
        raise ValueError("relative_illumination: half_angle_deg must be in "
                         "(0, 90), got %g (at 90 deg the illuminance is exactly "
                         "0 and the relative curve is meaningless)" % (a,))
    n = _count(samples, "samples", 2, MAX_GRID)
    p = _finite_scalar(exponent, "exponent")
    if p < 0.0:
        raise ValueError("relative_illumination: exponent must be >= 0, got %g "
                         "(a negative exponent would brighten the corners)" % (p,))
    ang = np.linspace(0.0, a, n)
    rel = np.cos(np.radians(ang)) ** p
    return np.ascontiguousarray(np.column_stack([ang, rel]), dtype=np.float64)


# --------------------------------------------------------------------------- #
# wave optics                                                                  #
# --------------------------------------------------------------------------- #
def airy_pattern(size=64, wavelength_um=0.55, f_number=5.6, pixel_pitch_um=0.5):
    """The diffraction-limited PSF of a circular pupil (Airy pattern).

    ``I(r) = [2*J1(v)/v]^2`` with ``v = pi*r/(lambda*N)``, ``r`` the radial
    distance in the image plane, ``N`` the working f-number. Sampled on a
    ``size x size`` grid centred between pixels for even *size* and on a pixel
    for odd *size*. The normalisation is **analytic** (``I(0) = 1`` by the
    ``v -> 0`` limit), not a division by the sampled maximum: for odd *size*
    the centre pixel is therefore exactly 1.0, and for even *size* the true
    peak falls between pixels so the largest *sample* is below it (0.9679 at
    ``size = 8`` with the defaults, measured). Rescaling to the sampled maximum
    instead would quietly change the physics with the parity of the grid.

    Returns a ``(size, size)`` float64 intensity image.

    Ground truth it reproduces (measured, ``tests/test_optics.py``): the first
    dark ring sits at the first zero of ``J1``, ``r = 1.2197*lambda*N`` — at
    ``lambda = 0.55 um``, ``N = 5.6`` that is ``3.7567 um``, and the sampled
    radial minimum lands at ``3.760 um`` on a 0.01 um grid (0.3 of a sample
    away, which is the sampling, not an error); the peak is exactly 1.0 at the
    centre and the pattern is symmetric to 1e-16.

    The encircled energy inside that ring is the textbook 83.8% of the *whole
    infinite* pattern — which a finite grid cannot measure: the Airy tails fall
    off only as ``1/r^3``, so a 25.6 um half-width grid reports 0.857 and a
    51.2 um one 0.847 (both measured). The number is quoted here as physics,
    not as something this op returns.

    The ``v -> 0`` limit is evaluated **explicitly** as 1.0 rather than left to
    ``0/0``: that division is the classic silent-NaN in every hand-rolled Airy
    routine, and the centre pixel is exactly where it bites.

    **Raises** ``ValueError``: *size* outside ``[2, MAX_GRID]``; non-positive or
    non-finite *wavelength_um*, *f_number*, *pixel_pitch_um*.

    Scalar, aberration-free, unobstructed circular pupil, low NA. A central
    obscuration (a mirror telescope) changes the ring structure; high NA needs a
    vector treatment. For the *measured* PSF of a real system use
    :func:`psf_to_mtf` on an image of a point source instead.
    """
    from scipy.special import j1                      # scipy is a hard dependency

    n = _count(size, "size", 2, MAX_GRID)
    lam = _positive(wavelength_um, "wavelength_um")
    fn = _positive(f_number, "f_number")
    pitch = _positive(pixel_pitch_um, "pixel_pitch_um")
    c = (n - 1) / 2.0
    ax = (np.arange(n, dtype=np.float64) - c) * pitch
    r = np.hypot(ax[:, None], ax[None, :])
    v = np.pi * r / (lam * fn)
    out = np.ones_like(v)
    nz = v != 0.0                                     # the 0/0 limit is 1, not NaN
    out[nz] = (2.0 * j1(v[nz]) / v[nz]) ** 2
    return np.ascontiguousarray(out, dtype=np.float64)


def angular_spectrum_propagate(field, wavelength_um=0.55, distance_um=100.0,
                               pixel_pitch_um=1.0):
    """Exact scalar free-space propagation of a complex field (angular spectrum).

    ``U(z) = IFFT{ FFT{U(0)} * exp(i*2*pi*z*sqrt(1/lambda^2 - fx^2 - fy^2)) }``
    in the ``exp(-i*omega*t)`` convention, so a positive *distance_um*
    propagates forward. Components beyond the propagating cone
    (``fx^2 + fy^2 > 1/lambda^2``) are **attenuated** by
    ``exp(-2*pi*|z|*sqrt(fx^2 + fy^2 - 1/lambda^2))``, which is the physical
    evanescent decay — not zeroed, so ``distance_um = 0`` is an *exact*
    identity and the transfer function is continuous through it.

    Unlike Fresnel propagation this makes no paraxial approximation: it is the
    exact solution of the Helmholtz equation for a band-limited field, valid
    from a fraction of a wavelength outward.

    Returns a complex128 array with the same shape as *field*.

    Ground truth it reproduces (measured): ``distance_um = 0`` returns the field
    bit-identically (it short-circuits the transform pair); propagating ``+z``
    then ``-z`` returns the original to a relative L2 error of 4.3e-16 for a
    band-limited field (no evanescent content); total power is conserved to
    1.7e-16 relative. A field *with*
    evanescent content does **not** round-trip — those components are gone by
    construction, in both directions, because that is what physically happens.

    *field* is a field in the **space** domain, not a spectrum: do not hand it
    the fftshifted output of :func:`complexops.cx_fft`. Real input is promoted
    to complex, which loses nothing.

    Aliasing: the discrete transfer function is periodic, so a field that
    diffracts past the array edge wraps around. The practical guard is the
    usual one — pad the field so the propagated support stays inside, and keep
    ``pixel_pitch_um`` below ``lambda/(2*NA)``. No warning can detect this
    reliably from the array alone, so none is invented.

    **Raises** ``ValueError``: *field* is not 2-D, smaller than 2x2, larger than
    :data:`MAX_FIELD_ELEMENTS`, masked, or non-finite; non-positive or
    non-finite *wavelength_um* / *pixel_pitch_um*; non-finite *distance_um*.
    """
    u = _require_image(field, "field", "angular_spectrum_propagate",
                       complex_ok=True)
    lam = _positive(wavelength_um, "wavelength_um")
    z = _finite_scalar(distance_um, "distance_um")
    pitch = _positive(pixel_pitch_um, "pixel_pitch_um")
    if z == 0.0:
        # Zero distance is the identity operator. Taking the FFT round trip
        # anyway would return the field with ~1e-16 of numerical dirt on it and
        # cost two transforms for nothing; a copy is both exact and cheaper.
        return np.ascontiguousarray(u, dtype=np.complex128).copy()
    h, w = u.shape
    fy = np.fft.fftfreq(h, d=pitch)[:, None]
    fx = np.fft.fftfreq(w, d=pitch)[None, :]
    arg = 1.0 / (lam * lam) - fx * fx - fy * fy
    prop = arg >= 0.0
    kz = np.zeros_like(arg)
    np.sqrt(arg, out=kz, where=prop)
    tf = np.empty(arg.shape, dtype=np.complex128)
    tf[prop] = np.exp(2j * np.pi * z * kz[prop])
    if (~prop).any():                       # evanescent: decay away from the source
        decay = np.sqrt(-arg[~prop])
        tf[~prop] = np.exp(-2.0 * np.pi * abs(z) * decay)
    out = np.fft.ifft2(np.fft.fft2(u) * tf)
    if not np.isfinite(out).all():
        raise ValueError("angular_spectrum_propagate: the propagated field "
                         "overflowed float64 — the input field's dynamic range "
                         "is beyond what an FFT of this size can carry")
    return np.ascontiguousarray(out, dtype=np.complex128)


def fraunhofer_pattern(aperture, wavelength_um=0.55, distance_mm=100.0,
                       pixel_pitch_um=10.0):
    """Far-field (Fraunhofer) diffraction intensity of an aperture.

    In the far field the diffracted amplitude is the Fourier transform of the
    aperture transmittance, so the intensity is
    ``|FFT{aperture}|^2`` (fftshifted, DC at the centre) normalised to a peak of
    exactly 1.0.

    Returns a float64 image with the same shape as *aperture*.

    **The output plane is sampled differently from the input plane** — this is
    the trap in every FFT diffraction routine. The observation-plane pitch is
    ``lambda*z/(N_pixels*input_pitch)``; with the defaults
    (``0.55 um``, ``100 mm``, ``10 um``) and a 64-pixel aperture that is
    ``0.55*100000/(64*10) = 85.9 um`` per pixel. The value is not returned as
    an image cannot carry it; compute it from the formula when you need
    absolute positions.

    A ``RuntimeWarning`` is emitted when the Fresnel number
    ``N_F = a^2/(lambda*z)`` (with ``a`` the aperture's support radius) is not
    below 1 — i.e. when you are asking for a far-field pattern at a distance
    where the near field still dominates. The result is still returned, because
    the Fourier relation is exactly what was asked for; the warning says the
    *physics*, not the arithmetic, is out of range.

    Ground truth it reproduces (measured): a rectangular slit ``w`` pixels wide
    in an ``N``-pixel array puts its diffraction zeros exactly on the DFT bins
    ``k*N/w``; a 4-pixel-wide slit in a 64-pixel array has **exactly** 0.0 at
    bins +/-16 and +/-32 from DC (the DFT of a boxcar vanishes there to the
    last bit, not merely to rounding); the pattern of a centred symmetric
    aperture is symmetric to 2.2e-16.

    **Raises** ``ValueError``: *aperture* is not 2-D / smaller than 2x2 / over
    the size cap / complex / masked / non-finite; a negative transmittance
    (that is not an aperture); an **opaque** aperture (everything zero — an
    opaque screen diffracts nothing and the normalisation would be 0/0);
    non-positive or non-finite *wavelength_um* / *distance_mm* /
    *pixel_pitch_um*.
    """
    a = _require_image(aperture, "aperture", "fraunhofer_pattern")
    lam = _positive(wavelength_um, "wavelength_um")
    z_um = _positive(distance_mm, "distance_mm") * 1e3
    pitch = _positive(pixel_pitch_um, "pixel_pitch_um")
    if (a < 0.0).any():
        raise ValueError("fraunhofer_pattern: aperture has %d negative value(s) "
                         "— a transmittance is >= 0 (an amplitude mask with a "
                         "sign is a complex field; use "
                         "angular_spectrum_propagate)" % (int((a < 0.0).sum()),))
    if not a.any():
        raise ValueError("fraunhofer_pattern: the aperture is entirely opaque "
                         "(all zeros) — an opaque screen diffracts nothing and "
                         "the peak normalisation would be 0/0")
    spec = np.fft.fftshift(np.fft.fft2(a))
    inten = np.abs(spec) ** 2
    peak = float(inten.max())
    if not np.isfinite(peak) or peak <= 0.0:
        raise ValueError("fraunhofer_pattern: the diffracted intensity peak is "
                         "%r — the transform overflowed float64" % (peak,))
    # far-field sanity: support radius of the aperture, in micrometres
    yy, xx = np.nonzero(a)
    h, w = a.shape
    rad = float(np.max(np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0)) * pitch)
    nf = rad * rad / (lam * z_um)
    if nf >= 1.0:
        warnings.warn("fraunhofer_pattern: Fresnel number %.3g >= 1 (aperture "
                      "radius %.3g um, distance %.3g mm) — the far-field "
                      "condition is not met; the returned pattern is the exact "
                      "Fourier transform but not the field at that distance "
                      "(use angular_spectrum_propagate)"
                      % (nf, rad, z_um * 1e-3), RuntimeWarning, stacklevel=2)
    return np.ascontiguousarray(inten / peak, dtype=np.float64)


def gaussian_beam(waist_um=100.0, wavelength_um=1.064, distance_mm=0.0,
                  n_medium=1.0):
    """Gaussian-beam propagation: spot size, wavefront curvature and Gouy phase.

    The ``q``-parameter solution of the paraxial wave equation, evaluated at
    *distance_mm* from the waist. With ``zR = pi*w0^2*n/lambda``:

    ``w(z) = w0*sqrt(1 + (z/zR)^2)`` · ``R(z) = z*(1 + (zR/z)^2)`` ·
    ``psi(z) = arctan(z/zR)`` (Gouy) · far-field half-divergence
    ``theta = lambda/(pi*n*w0)``.

    Returns a dict: ``radius_um`` the 1/e^2 field radius ``w(z)`` ·
    ``rayleigh_mm`` ``zR`` · ``wavefront_radius_mm`` ``R(z)`` ·
    ``curvature_per_mm`` ``1/R(z)`` · ``gouy_deg`` · ``divergence_mrad`` the
    far-field half angle · ``waist_um`` and ``distance_mm`` echoed back.

    **``wavefront_radius_mm`` is ``inf`` exactly at the waist, by contract**:
    the wavefront there is planar and a plane has infinite radius. That is why
    ``curvature_per_mm`` is also returned — it is 0 at the waist and finite
    everywhere, so downstream arithmetic never has to divide by an infinity.
    A negative ``R`` (before the waist, ``z < 0``) means a converging wavefront.

    Ground truth it reproduces exactly (verified at machine precision): at
    ``z = zR`` the spot is ``sqrt(2)*w0``, the wavefront radius is ``2*zR`` (its
    minimum over all z) and the Gouy phase is exactly 45 degrees; the
    beam-parameter product ``w0*theta = lambda/(pi*n)`` holds for every input.

    **Raises** ``ValueError``: non-positive or non-finite *waist_um*,
    *wavelength_um*, *n_medium*; non-finite *distance_mm*.

    Paraxial and fundamental-mode (TEM00) only: a real multimode beam needs an
    ``M^2`` factor, which this op deliberately does not fake by accepting one
    silently.
    """
    w0 = _positive(waist_um, "waist_um")
    lam = _positive(wavelength_um, "wavelength_um")
    n = _positive(n_medium, "n_medium")
    z_mm = _finite_scalar(distance_mm, "distance_mm")
    zr_um = np.pi * w0 * w0 * n / lam
    z_um = z_mm * 1e3
    t = z_um / zr_um
    w = w0 * np.sqrt(1.0 + t * t)
    if z_um == 0.0:
        r_mm = float("inf")
        curv = 0.0
    else:
        r_um = z_um * (1.0 + 1.0 / (t * t))
        r_mm = r_um * 1e-3
        curv = 1.0 / r_mm
    return {"radius_um": float(w), "rayleigh_mm": float(zr_um * 1e-3),
            "wavefront_radius_mm": float(r_mm), "curvature_per_mm": float(curv),
            "gouy_deg": float(np.degrees(np.arctan(t))),
            "divergence_mrad": float(lam / (np.pi * n * w0) * 1e3),
            "waist_um": float(w0), "distance_mm": float(z_mm)}


# --------------------------------------------------------------------------- #
# imaging quality                                                              #
# --------------------------------------------------------------------------- #
def psf_to_mtf(psf, pixel_pitch_um=1.0):
    """Radially-averaged MTF of a measured point-spread function.

    ``OTF = FFT{PSF}``, ``MTF = |OTF| / |OTF(0)|``, then averaged over annuli of
    constant spatial frequency out to the Nyquist limit ``1/(2*pitch)``. This
    is the measurement side of resolution: image a point source (or a slit, or
    differentiate a knife edge), hand the spot here, and compare the curve with
    the diffraction limit from :func:`mtf_diffraction`.

    Returns an ``(n, 2)`` float64 ``pairs`` array: column 0 the spatial
    frequency in **cycles per millimetre**, column 1 the MTF in [0, 1]. One row
    per non-empty radial bin (a very anisotropic array can leave a bin empty;
    those rows are dropped rather than filled with a NaN).

    Ground truth it reproduces (measured): a delta PSF gives MTF == 1 at every
    frequency **exactly** (max deviation 0.0); a Gaussian PSF of sigma pixels
    gives the closed form ``exp(-2*pi^2*sigma^2*f^2)`` — the maximum absolute
    deviation over the whole curve is 4.1e-4 at sigma = 2 px on 128x128,
    8.3e-4 at sigma = 1.5 px on 64x64 and 2.4e-4 at sigma = 3 px on 256x256
    (the residual is the radial average over a square grid, not an error in the
    transform). Doubling *pixel_pitch_um* halves every reported frequency and
    leaves the MTF column bit-identical.

    The PSF is **not** re-normalised or re-centred: a PSF whose energy is not
    centred carries a linear phase, which the modulus discards, so the MTF is
    unaffected — but the *phase* transfer function, which is where a
    decentred/asymmetric PSF shows up, is deliberately not summarised here.

    **Raises** ``ValueError``: *psf* is not 2-D / smaller than 2x2 / over the
    size cap / complex / masked / non-finite; a PSF that sums to zero or less
    (the DC normalisation would be 0/0 — an all-zero "PSF" is not a PSF);
    non-positive or non-finite *pixel_pitch_um*.
    """
    p = _require_image(psf, "psf", "psf_to_mtf")
    pitch = _positive(pixel_pitch_um, "pixel_pitch_um")
    with np.errstate(over="ignore", invalid="ignore"):
        total = float(p.sum())
    if not (total > 0.0):
        raise ValueError("psf_to_mtf: the PSF sums to %g — the DC normalisation "
                         "|OTF(0)| would be 0/0. An all-zero or net-negative "
                         "array is not a point-spread function" % (total,))
    with np.errstate(over="ignore", invalid="ignore"):
        otf = np.fft.fft2(p)
    dc = abs(complex(otf[0, 0]))
    if not np.isfinite(dc) or dc == 0.0 or not np.isfinite(otf).all():
        # Confirmed 2026-09-01: a PSF of 1e308 overflows the transform, so
        # |OTF| and |OTF(0)| are both inf and the MTF came back as a column of
        # silent NaN. The sum test above does not catch it — the sum overflows
        # to +inf too, which is > 0.
        raise ValueError("psf_to_mtf: the transform overflowed float64 "
                         "(|OTF(0)| = %r) — the PSF's dynamic range is beyond "
                         "what an FFT of this size can carry; rescale it (the "
                         "MTF is scale-invariant, so dividing the PSF by its "
                         "sum costs nothing)" % (dc,))
    mtf = np.abs(otf) / dc
    h, w = p.shape
    fy = np.fft.fftfreq(h, d=pitch)[:, None]
    fx = np.fft.fftfreq(w, d=pitch)[None, :]
    rho = np.hypot(fy, fx)                       # cycles / um
    nyq = 0.5 / pitch
    nbins = max(2, min(h, w) // 2)
    edges = np.linspace(0.0, nyq, nbins + 1)
    idx = np.digitize(rho.ravel(), edges) - 1
    keep = (idx >= 0) & (idx < nbins)
    counts = np.bincount(idx[keep], minlength=nbins)
    sums = np.bincount(idx[keep], weights=mtf.ravel()[keep], minlength=nbins)
    # Report each bin at the *mean frequency of the pixels in it*, not at the
    # geometric bin centre: the pixels are not uniformly distributed inside an
    # annulus, and pinning the curve to the bin centre put the Gaussian
    # reference 1.0e-2 off where the mean puts it 4.1e-4 off (measured).
    fsum = np.bincount(idx[keep], weights=rho.ravel()[keep], minlength=nbins)
    ok = counts > 0
    out = np.column_stack([fsum[ok] / counts[ok] * 1e3, sums[ok] / counts[ok]])
    return np.ascontiguousarray(out, dtype=np.float64)


def mtf_diffraction(f_number=5.6, wavelength_um=0.55, samples=64):
    """The diffraction-limited MTF of a circular pupil (closed form).

    ``MTF(x) = (2/pi)*(arccos(x) - x*sqrt(1 - x^2))`` with ``x = nu/nu_c`` the
    frequency normalised to the cutoff ``nu_c = 1/(lambda*N)``. This is the
    ceiling: no aberration-free lens at this f-number can do better, and a
    measured :func:`psf_to_mtf` curve above it means the measurement is wrong.

    Returns a ``(samples, 2)`` float64 ``pairs`` array: column 0 the spatial
    frequency in **cycles per millimetre** from 0 to the cutoff, column 1 the
    MTF in [0, 1].

    Ground truth it reproduces exactly (machine precision): ``MTF(0) = 1``,
    ``MTF(nu_c) = 0``, and at half the cutoff the textbook ``0.391``
    (``(2/pi)*(pi/3 - sqrt(3)/4) = 0.3910022...``). The cutoff itself at
    ``lambda = 0.55 um``, ``N = 5.6`` is ``324.7 cycles/mm`` — which is why
    stopping a machine-vision lens past f/8 stops buying depth of field and
    starts buying blur (compare :func:`depth_of_field`).

    **Raises** ``ValueError``: non-positive or non-finite *f_number* /
    *wavelength_um*; *samples* outside ``[2, MAX_GRID]``.

    Incoherent illumination, circular unobstructed pupil, no aberration, no
    defocus, and no detector: the pixel aperture and the sensor's own MTF
    multiply on top of this and are not included.
    """
    n = _positive(f_number, "f_number")
    lam = _positive(wavelength_um, "wavelength_um")
    k = _count(samples, "samples", 2, MAX_GRID)
    cutoff_per_um = 1.0 / (lam * n)
    x = np.linspace(0.0, 1.0, k)
    m = (2.0 / np.pi) * (np.arccos(x) - x * np.sqrt(np.clip(1.0 - x * x, 0.0, None)))
    out = np.column_stack([x * cutoff_per_um * 1e3, m])
    return np.ascontiguousarray(out, dtype=np.float64)


def _zernike_terms(coeffs, op: str):
    """Validate a ``{(n, m): coefficient}`` Zernike dict (fit_zernike's format)."""
    if not isinstance(coeffs, dict):
        raise ValueError("%s: coeffs must be a dict {(n, m): coefficient} — the "
                         "format match3d.fit_zernike returns — got %r"
                         % (op, type(coeffs).__name__))
    if not coeffs:
        raise ValueError("%s: coeffs is empty — an empty Zernike expansion has "
                         "no wavefront to characterise" % (op,))
    if len(coeffs) > MAX_ZERNIKE_TERMS:
        raise ValueError("%s: %d terms exceeds the %d cap "
                         "(optics.MAX_ZERNIKE_TERMS)"
                         % (op, len(coeffs), MAX_ZERNIKE_TERMS))
    out = {}
    for key, val in coeffs.items():
        if (not isinstance(key, tuple) or len(key) != 2
                or not all(isinstance(k, (int, np.integer))
                           and not isinstance(k, (bool, np.bool_)) for k in key)):
            raise ValueError("%s: coeffs key %r is not an (n, m) pair of ints — "
                             "use the dict match3d.fit_zernike returns"
                             % (op, key))
        n, m = int(key[0]), int(key[1])
        if n < 0 or abs(m) > n or (n - abs(m)) % 2 != 0:
            raise ValueError("%s: (%d, %d) is not a valid Zernike index — need "
                             "n >= 0, |m| <= n and n-|m| even" % (op, n, m))
        if n > MAX_ZERNIKE_ORDER:
            raise ValueError("%s: radial order n=%d exceeds the %d cap "
                             "(optics.MAX_ZERNIKE_ORDER) — the shared basis "
                             "builder's factorial recurrence loses all accuracy "
                             "above n~44 (measured max|Z| = 71.5 at n=50 against "
                             "the analytic bound of 1)" % (op, n, MAX_ZERNIKE_ORDER))
        out[(n, m)] = _finite_scalar(val, "%s: coefficient (%d, %d)" % (op, n, m))
    return out


def wavefront_stats(coeffs, radial=128, angular=192):
    """Wavefront error statistics from a Zernike expansion: RMS, PV and Strehl.

    *coeffs* is exactly the dict :func:`match3d.fit_zernike` returns —
    ``{(n, m): coefficient}``, coefficients **in waves** — and this op re-uses
    ``match3d``'s own basis builder, so the two cannot drift apart in
    normalisation or in the ``(n, m)`` convention. Fit with ``fit_zernike``,
    characterise here.

    The wavefront is reconstructed on a polar grid (*radial* x *angular*) over
    the unit pupil and reduced with the **area element** ``rho d(rho) d(theta)``
    — an unweighted mean over a uniform-in-rho grid over-counts the centre and
    is a real, silent, ~10% error.

    Returns a dict: ``rms_waves`` (piston removed — piston is not an
    aberration) · ``pv_waves`` peak-to-valley over the pupil · ``strehl`` the
    Marechal estimate ``exp(-(2*pi*rms)^2)`` · ``marechal_valid`` whether
    ``rms_waves <= MARECHAL_RMS_LIMIT`` (0.1), because past that the estimate is
    optimistic and reporting the number without the caveat is the dishonest
    option · ``terms`` and ``n_max`` of the expansion.

    Ground truth it reproduces (measured at the defaults): pure defocus
    ``{(2, 0): 0.1}`` — for which ``Z = 2*rho^2 - 1`` has an exact pupil RMS of
    ``1/sqrt(3)`` — gives ``rms_waves = 0.0577422`` against the exact
    ``0.0577350``, a relative error of 1.2e-4 from the discrete quadrature
    (3.1e-5 at ``radial=256``), and ``pv_waves = 0.2`` exactly; the Strehl is
    0.8766676 against the exact 0.8766962. Pure astigmatism ``{(2, 2): 0.1}``
    (exact RMS ``1/sqrt(6)``) gives 0.0408280 against 0.0408248. Piston alone
    (``{(0, 0): c}``) gives rms 0 and Strehl 1 for any ``c``, and RMS scales
    exactly linearly in the coefficients (doubling them doubles the RMS to
    machine precision).

    **Raises** ``ValueError``: *coeffs* is not a dict, is empty, holds more than
    :data:`MAX_ZERNIKE_TERMS` terms, has a key that is not an ``(n, m)`` int
    pair or is not a valid Zernike index (``n >= 0``, ``|m| <= n``, ``n-|m|``
    even), or a non-finite coefficient; a radial order above
    :data:`MAX_ZERNIKE_ORDER` (40 — the shared basis builder's factorial
    recurrence breaks its own ``|Z| <= 1`` bound at ``n = 46``, measured, and
    the same bound is re-checked at runtime); *radial* / *angular* outside
    ``[8, MAX_GRID]``.

    The radial quadrature is discrete, so its error grows with the order being
    integrated: measured, the relative RMS error tracks ``(n_max/radial)^2``
    within a factor 2 — 1.2e-4 at ``n_max=2``, 1.7e-3 at ``n_max=6`` and 4.3e-2
    at ``n_max=20``, all at the default ``radial=128``. Below
    ``radial >= 16*n_max`` a ``RuntimeWarning`` says so rather than letting a
    12%-wrong Strehl look authoritative. Raising *radial* fixes it at
    ``O(1/radial^2)``, but note the basis is built for *all* orders up to
    ``n_max``, so the working set grows as ``n_max^2 * radial * angular`` and is
    capped by :data:`MAX_ZERNIKE_BASIS`.

    Marechal is a small-aberration approximation and the RMS is over the *fitted*
    expansion, so it says nothing about wavefront structure finer than ``n_max``
    — and ``fit_zernike`` itself discloses ~10% inter-mode crosstalk at its
    default sampling. Both limits compound; treat the Strehl as an indicator,
    not a measurement.
    """
    terms = _zernike_terms(coeffs, "wavefront_stats")
    nr = _count(radial, "radial", 8, MAX_GRID)
    nt = _count(angular, "angular", 8, MAX_GRID)
    n_max = max(n for n, _m in terms)
    # The shared basis builder evaluates *every* (n, m) up to n_max on the whole
    # polar grid, so the working set is (n_max+1)(n_max+2)/2 * nr * nt float64 —
    # quadratic in an argument that looks innocent. Measured: n_max=40 with
    # radial=angular=4096 asks for 1.4e10 elements = 108 GB from a call whose
    # inputs are one dict and two ints. Refuse it up front.
    rows = (n_max + 1) * (n_max + 2) // 2
    need = rows * nr * nt
    if need > MAX_ZERNIKE_BASIS:
        raise ValueError("wavefront_stats: the Zernike basis for n_max=%d on a "
                         "%dx%d grid needs %d elements (%.1f GB), over the %d "
                         "cap (optics.MAX_ZERNIKE_BASIS) — lower radial/angular "
                         "or fit fewer orders"
                         % (n_max, nr, nt, need, need * 8 / 2 ** 30,
                            MAX_ZERNIKE_BASIS))
    if nr < 16 * n_max:
        # Measured 2026-09-01: the relative RMS error of the radial quadrature
        # tracks (n_max/radial)^2 to within a factor 2 — 1.7e-3 at n=6/nr=128,
        # 4.3e-2 at n=20/nr=128, 1.2e-1 at n=40/nr=128. Silence there would be
        # a quietly wrong Strehl.
        warnings.warn("wavefront_stats: radial=%d is under-sampled for n_max=%d "
                      "— the radial quadrature error grows as (n_max/radial)^2 "
                      "(measured ~%.1e relative here); raise radial to >= %d"
                      % (nr, n_max, (n_max / nr) ** 2, 16 * n_max),
                      RuntimeWarning, stacklevel=2)
    # match3d owns the Zernike basis (fit_zernike uses the same builder), so the
    # fitting and the statistics cannot disagree about normalisation. It is pure
    # numpy; the import is lazy only to keep this module's import cheap.
    from match3d import _zernike_basis
    basis, idx, rho = _zernike_basis(nr, nt, n_max)
    peak = float(np.abs(basis).max())
    if not np.isfinite(peak) or peak > 1.0 + 1e-6:
        # Belt and braces over MAX_ZERNIKE_ORDER: every Zernike polynomial is
        # bounded by 1 on the unit disk, so a basis that is not says the
        # evaluation lost precision — checked rather than assumed.
        raise ValueError("wavefront_stats: the Zernike basis up to n_max=%d "
                         "violates its own |Z| <= 1 bound (max %g) — the "
                         "polynomial evaluation lost precision at this order; "
                         "fit fewer terms" % (n_max, peak))
    lookup = {k: i for i, k in enumerate(idx)}
    w = np.zeros(basis.shape[1], dtype=np.float64)
    for key, c in terms.items():
        row = lookup.get(key)
        if row is None:                       # unreachable for a valid index
            raise ValueError("wavefront_stats: (%d, %d) is not in the Zernike "
                             "basis up to n_max=%d" % (key[0], key[1], n_max))
        w += c * basis[row]
    # Area element rho d(rho) d(theta), integrated with the trapezoidal rule in
    # rho. The basis grid is uniform in rho *including both endpoints*, so a
    # plain sum is the rectangle rule and converges only as O(1/nr): measured,
    # it put the pure-defocus RMS 0.79% high at nr=128. Halving the two endpoint
    # weights makes it O(1/nr^2): the same error becomes 1.2e-4 at nr=128 and
    # 3.1e-5 at nr=256, a clean factor-4 per doubling (measured).
    tw = np.ones(nr, dtype=np.float64)
    tw[0] = tw[-1] = 0.5
    weight = rho * np.repeat(tw, nt)
    wsum = float(weight.sum())
    mean = float((weight * w).sum() / wsum)
    var = float((weight * (w - mean) ** 2).sum() / wsum)
    rms = float(np.sqrt(max(var, 0.0)))
    pv = float(w.max() - w.min())
    strehl = float(np.exp(-((2.0 * np.pi * rms) ** 2)))
    return {"rms_waves": rms, "pv_waves": pv, "strehl": strehl,
            "marechal_valid": bool(rms <= MARECHAL_RMS_LIMIT),
            "terms": int(len(terms)), "n_max": int(n_max)}


# --------------------------------------------------------------------------- #
# polarisation                                                                 #
# --------------------------------------------------------------------------- #
def _rot2(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s], [s, c]], dtype=np.float64)


def jones_element(kind="polarizer", angle_deg=0.0, retardance_deg=90.0):
    """A 2x2 complex Jones matrix for one polarisation element.

    *kind* is one of :data:`JONES_KINDS`:

    ``"polarizer"`` ideal linear polariser, transmission axis at *angle_deg*
    from x · ``"retarder"`` linear retarder, fast axis at *angle_deg*,
    retardance *retardance_deg* · ``"quarter_wave"`` / ``"half_wave"``
    retarders with the retardance fixed at 90 / 180 degrees (*retardance_deg*
    is then **ignored** — stated here so a caller who passes one is not left
    wondering) · ``"rotator"`` optical rotator turning the polarisation by
    *angle_deg*.

    The retarder is written symmetrically, ``diag(exp(-i*d/2), exp(+i*d/2))``
    before rotation, so it introduces no common phase — the fast axis leads.
    Elements are built as ``R(+a) @ J0 @ R(-a)``.

    Returns a ``(2, 2)`` complex128 matrix acting on a Jones vector
    ``[Ex, Ey]``; compose a train with ``J_total = J_last @ ... @ J_first`` and
    apply it with :func:`jones_apply`.

    Ground truth it reproduces exactly (machine precision): two crossed ideal
    polarisers multiply to the zero matrix; a polariser is idempotent
    (``P @ P == P``); a half-wave plate is an involution up to a global phase
    (``H @ H == -I`` in this symmetric convention); a quarter-wave plate at 45
    degrees turns horizontal linear light into circular (``|S3| == 1``); the
    Malus law ``cos^2(theta)`` falls out of two polarisers at relative angle
    theta.

    **Raises** ``ValueError``: an unknown *kind* (the message lists the valid
    ones); non-finite *angle_deg* or *retardance_deg*.

    Ideal, lossless, normal-incidence elements. A real polariser has a finite
    extinction ratio and a real waveplate is chromatic; neither is modelled, and
    neither is silently approximated. Jones algebra can only carry **fully
    polarised** light — for partial polarisation use :func:`mueller_element`.
    """
    if not isinstance(kind, str):
        raise ValueError("jones_element: kind must be a string, got %r"
                         % (type(kind).__name__,))
    k = kind.strip().lower()
    a = np.radians(_finite_scalar(angle_deg, "angle_deg"))
    if k == "rotator":
        return np.ascontiguousarray(_rot2(a), dtype=np.complex128)
    if k == "polarizer":
        j0 = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=np.complex128)
    elif k in ("retarder", "quarter_wave", "half_wave"):
        d = {"quarter_wave": 90.0, "half_wave": 180.0}.get(
            k, None)
        if d is None:
            d = _finite_scalar(retardance_deg, "retardance_deg")
        d = np.radians(d)
        j0 = np.array([[np.exp(-0.5j * d), 0.0], [0.0, np.exp(0.5j * d)]],
                      dtype=np.complex128)
    else:
        raise ValueError("jones_element: unknown kind %r — expected one of %s"
                         % (kind, "/".join(JONES_KINDS)))
    r = _rot2(a).astype(np.complex128)
    return np.ascontiguousarray(r @ j0 @ r.T, dtype=np.complex128)


def jones_apply(jones, state):
    """Push a Jones vector through a Jones matrix: ``[Ex', Ey'] = J @ [Ex, Ey]``.

    *jones* is a ``(2, 2)`` matrix (complex, or real which is promoted) and
    *state* a 2-component complex Jones vector ``[Ex, Ey]`` of field
    amplitudes. Returns a ``(2,)`` complex128 vector — chain it through further
    elements, or hand it to :func:`stokes_from_jones` to get the observables.

    Ground truth it reproduces exactly: Malus's law — a linear polariser at
    *theta* on horizontal linear input returns amplitude ``cos(theta)``, hence
    intensity ``cos^2(theta)``, matching to 1e-15 over the full angle sweep;
    crossed polarisers return exactly ``[0, 0]``; the identity matrix returns
    the input bit-identically.

    **Note the zero vector is a legal result**, not an error: light blocked by
    crossed polarisers has zero amplitude. Downstream, :func:`stokes_analyze`
    is the op that refuses a zero-intensity Stokes vector, because *there* the
    degree of polarisation would be 0/0.

    **Raises** ``ValueError``: *jones* is not ``(2, 2)``, *state* is not a
    1-D 2-vector, either is masked or non-finite, or the product overflows.
    """
    j = _as_complex_array(jones, "jones")
    if j.ndim != 2 or j.shape != (2, 2):
        raise ValueError("jones_apply: jones must be a (2, 2) matrix, got shape "
                         "%r — build one with jones_element"
                         % (tuple(np.shape(jones)),))
    v = _require_vec(state, "state", "jones_apply", 2, complex_ok=True)
    out = j @ v
    if not np.isfinite(out).all():
        raise ValueError("jones_apply: the result overflowed float64 (matrix "
                         "norm %g, state norm %g)"
                         % (float(np.abs(j).max()), float(np.abs(v).max())))
    return np.ascontiguousarray(out, dtype=np.complex128)


def stokes_from_jones(state):
    """Jones vector -> Stokes vector (the four measurable intensities).

    ``S0 = |Ex|^2 + |Ey|^2`` · ``S1 = |Ex|^2 - |Ey|^2`` ·
    ``S2 = 2*Re(Ex*conj(Ey))`` · ``S3 = 2*Im(Ex*conj(Ey))``.

    In this convention (``exp(-i*omega*t)`` time dependence) ``S3 > 0`` is
    **right-circular**: the Jones vector ``[1, -i]/sqrt(2)`` maps to
    ``[1, 0, 0, +1]``. The convention is pinned by a test rather than left to
    the reader, because every textbook picks a different one and a sign slip
    here is invisible in intensity measurements.

    Returns a ``(4,)`` float64 vector. A Jones vector always describes fully
    polarised light, so the result always satisfies ``S0^2 = S1^2+S2^2+S3^2``
    exactly (degree of polarisation 1) — verified to 1e-15 in the tests. That
    identity is also the reason Jones cannot represent a partially polarised
    beam: for that, start from :func:`mueller_element` instead.

    **Raises** ``ValueError``: *state* is not a 1-D 2-vector, is masked, or is
    non-finite.
    """
    v = _require_vec(state, "state", "stokes_from_jones", 2, complex_ok=True)
    ex, ey = complex(v[0]), complex(v[1])
    cross = ex * np.conj(ey)
    s = np.array([abs(ex) ** 2 + abs(ey) ** 2,
                  abs(ex) ** 2 - abs(ey) ** 2,
                  2.0 * cross.real,
                  2.0 * cross.imag], dtype=np.float64)
    if not np.isfinite(s).all():
        raise ValueError("stokes_from_jones: the intensities overflowed float64 "
                         "(|E| = %g)" % (float(np.abs(v).max()),))
    return np.ascontiguousarray(s, dtype=np.float64)


def mueller_element(kind="polarizer", angle_deg=0.0, retardance_deg=90.0):
    """A 4x4 real Mueller matrix for one polarisation element.

    *kind* is one of :data:`MUELLER_KINDS` — the same five as
    :func:`jones_element` plus ``"depolarizer"`` (ideal, ``diag(1, 0, 0, 0)``),
    which has **no Jones counterpart at all**. That extra kind is the reason
    this family exists: Jones algebra can only carry fully polarised light,
    Mueller algebra carries partial polarisation, scattering and depolarisation
    — which is what a real polarisation camera sees.

    Angles are doubled inside (``c = cos(2a)``, ``s = sin(2a)``) because the
    Stokes parameters live on the Poincare sphere, where a physical rotation by
    ``a`` is a rotation by ``2a``.

    Returns a ``(4, 4)`` float64 matrix acting on ``[S0, S1, S2, S3]``; apply it
    with :func:`mueller_apply` and compose a train as
    ``M_last @ ... @ M_first``.

    Ground truth it reproduces exactly: an ideal polariser transmits exactly
    half of unpolarised light (``[1,0,0,0] -> S0 = 0.5``) and fully polarises
    it; two polarisers at relative angle theta transmit ``0.5*cos^2(theta)``
    (Malus); a rotator by 45 degrees turns horizontal into 45-degree linear;
    the depolariser leaves ``S0`` and kills ``S1..S3``. Cross-checked against
    the Jones family in the tests — for every kind and a sweep of angles, the
    Jones path and the Mueller path return the **same Stokes vector to 1e-14**,
    which is the only construction that catches a sign slip in either one.

    **Raises** ``ValueError``: an unknown *kind*; non-finite *angle_deg* or
    *retardance_deg*.

    Ideal, lossless (except the polariser's physical loss), normal-incidence
    elements; no diattenuation-plus-retardance combinations, no depolarisation
    other than the ideal case.
    """
    if not isinstance(kind, str):
        raise ValueError("mueller_element: kind must be a string, got %r"
                         % (type(kind).__name__,))
    k = kind.strip().lower()
    a = np.radians(_finite_scalar(angle_deg, "angle_deg"))
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
    elif k in ("retarder", "quarter_wave", "half_wave"):
        d = {"quarter_wave": 90.0, "half_wave": 180.0}.get(k, None)
        if d is None:
            d = _finite_scalar(retardance_deg, "retardance_deg")
        d = np.radians(d)
        cd, sd = np.cos(d), np.sin(d)
        m = np.array([[1.0, 0.0, 0.0, 0.0],
                      [0.0, c * c + s * s * cd, c * s * (1.0 - cd), -s * sd],
                      [0.0, c * s * (1.0 - cd), s * s + c * c * cd, c * sd],
                      [0.0, s * sd, -c * sd, cd]], dtype=np.float64)
    else:
        raise ValueError("mueller_element: unknown kind %r — expected one of %s"
                         % (kind, "/".join(MUELLER_KINDS)))
    return np.ascontiguousarray(m, dtype=np.float64)


def _require_stokes(s, op: str, name: str = "stokes") -> np.ndarray:
    v = _require_vec(s, name, op, 4)
    pol = float(np.sqrt(v[1] ** 2 + v[2] ** 2 + v[3] ** 2))
    if v[0] < 0.0:
        raise ValueError("%s: %s[0] (total intensity S0) is %g — a negative "
                         "intensity is not a physical state" % (op, name, v[0]))
    if pol > v[0] * (1.0 + 1e-9) + 1e-12:
        raise ValueError("%s: %s is not physically realisable — the polarised "
                         "part sqrt(S1^2+S2^2+S3^2) = %g exceeds the total "
                         "intensity S0 = %g (degree of polarisation > 1)"
                         % (op, name, pol, v[0]))
    return v


def mueller_apply(mueller, stokes):
    """Push a Stokes vector through a Mueller matrix: ``S' = M @ S``.

    *mueller* is a ``(4, 4)`` real matrix (build one with
    :func:`mueller_element`, or multiply several together) and *stokes* a
    4-component Stokes vector ``[S0, S1, S2, S3]``.

    The **input** is checked for physical realisability: ``S0 >= 0`` and
    ``sqrt(S1^2+S2^2+S3^2) <= S0`` (degree of polarisation at most 1). Handing
    an impossible state to a Mueller matrix returns a plausible-looking result
    that means nothing, so it is refused instead. The **output** is not
    re-checked, deliberately: an unphysical output is real evidence that
    *mueller* is not a physical Mueller matrix, and swallowing it would hide
    the bug — inspect it with :func:`stokes_analyze`, which will say so.

    Returns a ``(4,)`` float64 Stokes vector.

    Ground truth it reproduces exactly: unpolarised ``[1,0,0,0]`` through an
    ideal polariser gives ``S0 = 0.5`` with degree of polarisation 1; through
    two polarisers at relative angle theta, ``0.5*cos^2(theta)`` (Malus, to
    1e-16 over a full sweep); the identity matrix returns the input unchanged.

    **Raises** ``ValueError``: *mueller* is not ``(4, 4)``, *stokes* is not a
    1-D 4-vector, either is complex / masked / non-finite, the input Stokes
    vector is unphysical, or the product overflows float64.
    """
    m = _as_float_array(mueller, "mueller")
    if m.ndim != 2 or m.shape != (4, 4):
        raise ValueError("mueller_apply: mueller must be a (4, 4) matrix, got "
                         "shape %r — build one with mueller_element"
                         % (tuple(np.shape(mueller)),))
    s = _require_stokes(stokes, "mueller_apply")
    out = m @ s
    if not np.isfinite(out).all():
        raise ValueError("mueller_apply: the result overflowed float64 (matrix "
                         "norm %g, S0 %g)" % (float(np.abs(m).max()), float(s[0])))
    return np.ascontiguousarray(out, dtype=np.float64)


def stokes_analyze(stokes):
    """Read a Stokes vector: degree of polarisation, azimuth, ellipticity.

    Returns a dict: ``intensity`` ``S0`` · ``dop`` degree of polarisation
    ``sqrt(S1^2+S2^2+S3^2)/S0`` · ``dolp`` linear part ``sqrt(S1^2+S2^2)/S0`` ·
    ``docp`` circular part ``|S3|/S0`` · ``azimuth_deg`` orientation of the
    polarisation ellipse ``0.5*atan2(S2, S1)`` mapped into ``[0, 180)`` ·
    ``ellipticity_deg`` ``0.5*asin(S3/|S|)`` in ``[-45, +45]`` ·
    ``handedness`` one of ``"right"`` / ``"left"`` / ``"linear"``.

    **``azimuth_deg`` and ``ellipticity_deg`` are ``None`` when they are
    undefined** — azimuth when the linear part is exactly zero (circular or
    unpolarised light has no orientation), ellipticity when the polarised part
    is zero (unpolarised light has no ellipse). Returning 0.0 there would be a
    fabricated angle; ``None`` says the truth and forces the caller to handle
    it.

    Ground truth it reproduces exactly: ``[1,1,0,0]`` -> dop 1, azimuth 0,
    ellipticity 0, linear; ``[1,-1,0,0]`` -> azimuth 90; ``[1,0,1,0]`` ->
    azimuth 45; ``[1,0,0,1]`` -> docp 1, ellipticity +45, right-handed;
    ``[1,0,0,0]`` -> dop 0 with both angles ``None``;
    ``[2,1,0,0]`` -> dop 0.5 (a partially polarised beam, which is exactly the
    case Jones algebra cannot express).

    **Raises** ``ValueError``: *stokes* is not a 1-D 4-vector, is complex /
    masked / non-finite, is unphysical (``S0 < 0`` or degree of polarisation
    above 1 — which is how you find out a Mueller matrix was not physical), or
    has ``S0 == 0`` (no light at all: every ratio would be 0/0, and "the
    polarisation of darkness" is not a question with an answer).
    """
    s = _require_stokes(stokes, "stokes_analyze")
    s0 = float(s[0])
    if s0 == 0.0:
        raise ValueError("stokes_analyze: S0 (total intensity) is 0 — there is "
                         "no light, so every ratio would be 0/0; check for a "
                         "blocked beam (crossed polarisers) before analysing")
    lin = float(np.hypot(s[1], s[2]))
    pol = float(np.sqrt(s[1] ** 2 + s[2] ** 2 + s[3] ** 2))
    az = None
    if lin > 0.0:
        az = float(np.degrees(0.5 * np.arctan2(s[2], s[1])) % 180.0)
    ell = None
    if pol > 0.0:
        ell = float(np.degrees(0.5 * np.arcsin(np.clip(s[3] / pol, -1.0, 1.0))))
    hand = "linear" if s[3] == 0.0 else ("right" if s[3] > 0.0 else "left")
    return {"intensity": s0, "dop": float(min(pol / s0, 1.0)),
            "dolp": float(min(lin / s0, 1.0)),
            "docp": float(min(abs(s[3]) / s0, 1.0)),
            "azimuth_deg": az, "ellipticity_deg": ell, "handedness": hand}

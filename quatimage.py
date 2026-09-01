# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""quatimage — quaternion-valued images: the Riesz/monogenic signal and colour algebra.

A complex pixel carries two numbers and has **one** rotation axis: multiplying by
``exp(i*t)`` turns the (real, imaginary) plane and there is nothing else it can
do. :mod:`complexops` already gives Fullseye that object — spectra, wrapped
phase, unwrapping, transfer functions. A **quaternion** pixel carries four, and
its vector part is a *three*-dimensional space, so the conjugation
``q x conj(q)`` is a genuine rotation of a 3-vector. Two things follow, and they
are the whole reason this module exists:

* **A 2-D signal gets a real phase.** The 1-D analytic signal
  ``f + i*Hilbert(f)`` has no unique 2-D generalisation inside the complex
  numbers — the Hilbert transform needs a direction, and picking one is exactly
  what an oriented filter bank does. The **Riesz transform** is the isotropic
  2-D generalisation, and it is a *pair* ``(R1 f, R2 f)``, so the natural value
  of the transformed signal is the triple ``(f, R1 f, R2 f)`` — a quaternion
  (equivalently a Clifford number of ``R_{0,2}``). Its modulus is the local
  **amplitude**, its argument the local **phase**, and the direction of the
  vector part the local **orientation**, all three at once and all three
  isotropic. That is the *monogenic signal* of Felsberg & Sommer (2001), and it
  gives phase-based motion processing without a bank of oriented filters:
  **two** filters instead of ``scales * orientations`` of them, and a continuous
  per-pixel orientation instead of one quantised to the bank.
* **A colour pixel gets an algebra.** Writing an RGB triple as the pure
  quaternion ``0 + R i + G j + B k`` (Sangwine 1996) makes ``q x conj(q)`` a
  rotation *of the colour* — the operation that turns one hue towards another,
  which a per-channel pipeline cannot express at all because it never mixes
  channels.

Honest scope of the second claim — measured, not assumed
--------------------------------------------------------
The unit quaternions and ``SO(3)`` are isomorphic, so **every colour rotation
this module performs is also performed exactly by a 3x3 orthogonal matrix**, and
the quaternion Fourier transform below is a fixed linear recombination of the
three per-channel complex FFTs (:func:`qft2` gives the measured identity, max
error 1.14e-13). The honest separation is therefore three-way and this module
states it everywhere it matters:

* against a **channelwise** baseline — three independent scalar pipelines, which
  is what "run the existing complex ops on R, G and B" means — the quaternion
  ops do things that are *provably impossible*, because a per-channel gain is a
  diagonal matrix and cannot create a channel out of a zero. Measured: the best
  diagonal approximation to the grey-axis projection is off by 0.4714 on a pure
  red pixel, against 0.0 here (:func:`quat_color_filter`).
* against a **3x3 colour-matrix** baseline — no capability difference at all.
  What differs is representation cost (4 numbers vs 9), exact closure under
  composition, and ``slerp``; measured drift over 100,000 composed random
  rotations is 0.0 for the renormalised quaternion against
  ``|R^T R - I| = 4.4e-10`` for the plainly multiplied matrix
  (:func:`quat_color_rotate`). Real, and small.
* the **QFT is not faster** than three channel FFTs and this module never
  suggests otherwise: it moves four real transforms' worth of data where the
  channelwise route moves three, and pays for the symplectic pack on top.
  Measured about 2.4x *slower* on ``(256, 256)``, in :func:`qft2`.

The same accounting applies to the Riesz half, and there the losses are larger.
:func:`riesz_displacement` is exact to rounding *and* about twice as accurate as
the steerable route under noise *and* 1.2x-2.1x faster — but it carries a **13 %
silent displacement bias** on the repository's own default motion synthetic,
because a radial band has no orientation index and two gratings at different
orientations in one octave break the single-plane-wave model the monogenic signal
assumes. The full head-to-head table, including that loss, is in
:func:`riesz_displacement`.

Non-commutativity is an API problem, not just a maths problem
-------------------------------------------------------------
Quaternion multiplication is not commutative, so a "quaternion Fourier
transform" is two different transforms depending on which side the kernel is
applied. **Every operator here that is side-dependent takes a required ``side``
argument with no default** (:func:`qft2`, :func:`iqft2`,
:func:`quat_image_multiply`). A default would be a silent choice: the wrong side
raises nothing, produces no NaN, and returns a different — plausible — answer.
Measured on a random colour image, the left and right QFTs differ by
``max|F_L - F_R| = 33.35`` against a spectrum of peak modulus 892.9, and
round-tripping through the *wrong* side — ``iqft2(qft2(q, "left"), "right")`` —
returns an image with ``max|err| = 1.113`` on data whose own range is 0.9994:
a different picture entirely, finite and plausible throughout. Multiplying a
field by a rotor from the wrong side differs by as much as the data itself
(``max|left - right| = 3.143`` on data whose extreme is 3.372). See
:func:`qft2` and :func:`quat_image_multiply`.

Conventions
-----------
* A **quaternion image** (the ``qimage`` sort) is a real ``(H, W, 4)`` float64
  array with component order ``(w, x, y, z)`` — the same order
  :mod:`pose_quat` uses for its 3-D pose quaternions, deliberately, so a rotor
  built there can be handed straight to :func:`quat_color_rotate`.
* An **RGB image** is ``(H, W, 3)`` linear RGB (the ``rgbimage`` sort shared with
  :mod:`specularity`). :func:`rgb_to_quaternion` embeds it as ``(0, R, G, B)``;
  :func:`quaternion_to_rgb` takes the vector part back and **refuses** a
  quaternion with a non-negligible scalar part rather than dropping it silently.
* A **monogenic signal** is a ``qimage`` whose components are
  ``(band-pass image, R1, R2, 0)``. The ``k`` component is identically zero by
  construction, and :func:`monogenic_amplitude` / :func:`monogenic_phase` /
  :func:`monogenic_orientation` **check that** — which is what stops a colour
  quaternion (whose ``k`` component is the blue channel) from being read as a
  monogenic signal and answering with a plausible, wrong orientation.
* A **video** is ``(T, H, W)`` float64, the sort :mod:`videops` and
  :mod:`motionmag` use; ``dx`` is column motion and ``dy`` row motion, following
  :mod:`flow`.
* ``alpha`` in :func:`riesz_motion_magnify` is a **displacement gain** exactly as
  in :mod:`motionmag` (1 = identity, 2 = double the motion), so the two
  magnifiers are directly comparable with nothing to add or subtract first.

Where this sits next to what already exists
-------------------------------------------
* :mod:`pose_quat` owns the 3-D **pose** algebra (quaternion / dual quaternion /
  screw). It is imported, not re-implemented: :func:`quat_color_rotate` builds
  its rotor with ``pose_quat.axis_angle_to_quat`` and turns it into a matrix with
  ``pose_quat.quat_to_hom_mat3d``. Its per-quaternion helpers are scalar and this
  module needs per-pixel arithmetic, so the vectorised Hamilton product here is
  new code whose agreement with ``pose_quat.quat_compose`` is asserted in the
  tests to 1.4e-16. **One caveat found while doing that, documented in
  :func:`quat_color_rotate`**: ``pose_quat.quat_normalize`` divides by
  ``norm + 1e-12`` rather than refusing a zero quaternion, so a zero rotor
  becomes the identity rotation silently. This module validates before it calls.
* :mod:`complexops` owns the complex field. Nothing here duplicates it; the
  monogenic signal is the object complex numbers *cannot* hold in 2-D.
* :mod:`motionmag` owns phase-based magnification via a **complex steerable**
  bank. :func:`riesz_motion_magnify` and :func:`riesz_displacement` are a second
  answer to the same question, by the Riesz route of Wadhwa et al. (2014), and
  the module's tests measure them head to head against it on the same
  ``motionmag.synthesize_translation`` ground truth. The measured result — the
  Riesz route is *not* uniformly better — is in :func:`riesz_displacement`.
  ``motionmag.band_snr`` is imported by :func:`riesz_motion_magnify` rather than
  re-derived, so the two magnifiers report the honesty block on identical terms.
* :mod:`specularity` owns the dichromatic model. :func:`quat_color_filter`'s
  ``mode="remove"`` branch is **the same projection** as
  ``specularity.specular_free_transform`` and says so; it *delegates* to it
  rather than re-implementing, so the agreement is by construction, not by luck.

Provenance (public papers)
--------------------------
* **Riesz transform / monogenic signal** — M. Felsberg & G. Sommer, "The
  monogenic signal", *IEEE Trans. Signal Processing* 49(12), 3136-3144 (2001).
* **Riesz pyramids for motion magnification** — N. Wadhwa, M. Rubinstein,
  F. Durand, W. T. Freeman, "Riesz Pyramids for Fast Phase-Based Video
  Magnification", *ICCP* 2014.
* **Quaternion colour images / hypercomplex Fourier transform** — S. J. Sangwine,
  "Fourier transforms of colour images using quaternion, or hypercomplex,
  numbers", *Electronics Letters* 32(21), 1979-1980 (1996); T. A. Ell &
  S. J. Sangwine, "Hypercomplex Fourier transforms of color images", *IEEE
  Trans. Image Processing* 16(1), 22-35 (2007).
* **Quaternion correlation for colour matching** — S. J. Sangwine & T. A. Ell,
  "Hypercomplex auto- and cross-correlation of color images", *ICIP* 1999.
* **Specular-invariant colour subspace** (the projection reused by
  :func:`quat_color_filter`) — S. P. Mallick, T. Zickler, D. J. Kriegman,
  P. N. Belhumeur, "Beyond Lambert: Reconstructing specular surfaces using
  color", *CVPR* 2005.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    # convert / algebra
    "rgb_to_quaternion", "quaternion_to_rgb",
    "quat_norm", "quat_conjugate_image", "quat_normalize_image",
    "quat_image_multiply",
    # Riesz / monogenic
    "riesz_transform", "monogenic_signal",
    "monogenic_amplitude", "monogenic_phase", "monogenic_orientation",
    "riesz_motion_magnify", "riesz_displacement", "riesz_displacement_series",
    # colour
    "quat_color_rotate", "quat_color_filter",
    # hypercomplex Fourier
    "qft2", "iqft2",
    # matching
    "quat_correlate",
    # caps (public so a caller can see the bound before hitting it)
    "MAX_PIXELS", "MAX_FRAMES", "MAX_PYRAMID_ELEMENTS", "MAX_SCALES", "MAX_ALPHA",
    "QUATIMAGE",
]

#: The public quaternion-image functions, by name (introspection / facade
#: wiring), in the same style as ``complexops.COMPLEXOPS``.
QUATIMAGE = [
    "rgb_to_quaternion", "quaternion_to_rgb",
    "quat_norm", "quat_conjugate_image", "quat_normalize_image",
    "quat_image_multiply",
    "riesz_transform", "monogenic_signal",
    "monogenic_amplitude", "monogenic_phase", "monogenic_orientation",
    "riesz_motion_magnify", "riesz_displacement", "riesz_displacement_series",
    "quat_color_rotate", "quat_color_filter",
    "qft2", "iqft2",
    "quat_correlate",
]

# --------------------------------------------------------------------------- #
# Caps. Each one exists because a small-looking argument otherwise turns into a #
# large allocation, and each is applied *before* any float64 promotion (the     #
# lesson recorded in specularity._precheck_size: a cap checked after coercion   #
# does not prevent the copy it exists to prevent).                             #
# --------------------------------------------------------------------------- #

#: Largest pixel count in one frame / image (2^24 = 16.7 M, i.e. 4096x4096).
MAX_PIXELS = 1 << 24

#: Largest frame count accepted by the video operators.
MAX_FRAMES = 4096

#: Largest ``T * H * W`` for the Riesz video operators. Each radial band holds
#: three real ``(T, H, W)`` volumes (band, R1, R2) plus one complex one, so the
#: peak is near 56 bytes per element; 2^22 elements is then about 235 MB.
MAX_PYRAMID_ELEMENTS = 1 << 22

#: Largest number of radial scales. Unlike a steerable bank there is no
#: orientation count to multiply this by — that is the point of the Riesz route —
#: but a band per octave past 8 is below the sampling grid anyway.
MAX_SCALES = 8

#: Largest ``|alpha|`` for :func:`riesz_motion_magnify` (same bound and same
#: reason as ``motionmag.MAX_ALPHA``, so the two are comparable at the edge).
MAX_ALPHA = 200.0

#: A pixel whose quaternion modulus is below this fraction of the field's peak
#: carries rounding noise, not signal; its phase and orientation are meaningless
#: and it is muted rather than allowed to vote.
_AMP_FLOOR = 1e-12
_AMP_LIVE = 1e-6

#: How far the ``k`` component of a claimed monogenic signal may stray from zero,
#: relative to the field's peak modulus, before it is refused as not-a-monogenic
#: signal. Machine noise through two FFTs is ~1e-16 relative; a colour image's
#: blue channel is O(1) relative. Nothing real lives between them.
_MONOGENIC_K_TOL = 1e-9

#: How far a rotor's norm may stray from 1. A rotor with ``|q| != 1`` is a
#: rotation *and a scaling*, and ``q x conj(q)`` scales by ``|q|^2`` — which is
#: the silent-wrong-number failure this tolerance exists to stop.
_UNIT_TOL = 1e-9

_TWO_PI = 2.0 * np.pi


# --------------------------------------------------------------------------- #
# fail-closed input helpers                                                     #
# --------------------------------------------------------------------------- #
def _finite_scalar(v, name: str) -> float:
    """A real, finite Python float — or ``ValueError`` naming the problem.

    The string branch is not decoration: ``float("4")`` succeeds, so without it
    ``angle_rad="4"`` passes silently and the caller never learns the value came
    from an unparsed configuration file. The bool branch blocks the ``True == 1``
    promotion; as an ``fps`` that would silently mean a 1 Hz timebase, as an
    ``alpha`` the identity. Same three traps, same order, as
    ``motionmag._finite_scalar`` — the contract is shared on purpose so the two
    magnifiers cannot be told apart by their input discipline."""
    if np.ma.is_masked(v):
        raise ValueError("%s is a masked value — fill or drop it explicitly" % (name,))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s is complex — an angle / rate / gain is a real "
                         "quantity; coercion would silently drop the imaginary "
                         "part" % (name,))
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s is a bool — refusing the silent True==1 promotion "
                         "(as an fps that would mean a 1 Hz timebase, as a gain "
                         "the identity)" % (name,))
    if isinstance(v, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s is a string (%r) — an angle / rate / gain must be a "
                         "number; float('4') would silently succeed and hide an "
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


def _count(v, name: str, lo: int, hi: int) -> int:
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be an int, got %r" % (name, type(v).__name__))
    n = int(v)
    if n < lo or n > hi:
        raise ValueError("%s must be in [%d, %d], got %d (the cap is there so a "
                         "mistyped argument fails instead of allocating "
                         "gigabytes)" % (name, lo, hi, n))
    return n


def _precheck_size(a, name: str, op: str, cap: int, cap_name: str) -> None:
    """Reject an oversized array **before** it is copied to float64.

    The lesson is recorded in ``specularity._precheck_size`` and it is repeated
    here because the failure it describes is not hypothetical: a cap enforced
    after ``np.asarray(x, float64)`` has already asked the machine for the copy
    it was supposed to prevent. Reading ``ndarray.shape`` is free, so the bound
    is applied to the shape first and the coercion only happens for inputs that
    are already known to fit. Sequences (lists) have no free shape and fall
    through to the post-coercion check, which is the same bound one step later."""
    if isinstance(a, np.ndarray):
        n = 1
        for d in a.shape:
            n *= int(d)
        if n > cap:
            raise ValueError("%s: %s has %d elements (shape %r), over the %d cap "
                             "(quatimage.%s) — refused before conversion, so the "
                             "copy is never allocated"
                             % (op, name, n, tuple(a.shape), cap, cap_name))


def _as_float_array(a, name: str, op: str) -> np.ndarray:
    """Coerce to float64, refusing every silent-truncation trap.

    ``np.asarray(["1", "2"], dtype=float)`` succeeds, so the *raw* dtype is
    inspected before coercion; otherwise a list of strings from an unparsed
    config file passes as image data."""
    if isinstance(a, (str, bytes)):
        raise ValueError("%s: %s is a string (%r) — an image must be numeric"
                         % (op, name, a))
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked entries — coercion "
                         "would strip the mask and use the raw values underneath; "
                         "fill or drop them explicitly" % (op, name))
    try:
        raw = np.asarray(a)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s: %s could not be read as an array: %s"
                         % (op, name, exc)) from None
    if raw.dtype.kind in ("U", "S"):
        raise ValueError("%s: %s has string dtype %r — numeric strings would be "
                         "coerced without complaint and hide an unparsed "
                         "configuration value" % (op, name, raw.dtype))
    if raw.dtype.kind == "O":
        raise ValueError("%s: %s has object dtype — refusing to guess what its "
                         "elements are (a ragged list is the usual cause)"
                         % (op, name))
    if raw.dtype.kind == "b":
        raise ValueError("%s: %s has bool dtype — refusing the silent True==1 "
                         "promotion of a mask into image data" % (op, name))
    if raw.dtype.kind == "c":
        raise ValueError("%s: %s is complex — coercion to float64 would silently "
                         "discard the imaginary part. A quaternion image is a "
                         "real (H, W, 4) array, not a complex one; take "
                         ".real/.imag explicitly" % (op, name))
    arr = np.ascontiguousarray(raw, dtype=np.float64)
    if not np.isfinite(arr).all():
        n = int((~np.isfinite(arr)).sum())
        raise ValueError("%s: %s has %d non-finite value(s) (NaN/Inf) — refusing"
                         % (op, name, n))
    return arr


def _require_image(a, name: str, op: str) -> np.ndarray:
    """A real, finite, size-capped ``(H, W)`` float64 image."""
    _precheck_size(a, name, op, MAX_PIXELS, "MAX_PIXELS")
    arr = _as_float_array(a, name, op)
    if arr.ndim != 2:
        raise ValueError("%s: %s must be 2-D (H, W); got a %d-D array of shape %r "
                         "— nothing is reshaped silently"
                         % (op, name, arr.ndim, tuple(arr.shape)))
    if arr.shape[0] < 2 or arr.shape[1] < 2:
        raise ValueError("%s: %s is %dx%d; the Riesz kernel needs at least one "
                         "non-DC frequency on each axis, so a 1-pixel-wide image "
                         "carries no transform at all"
                         % (op, name, arr.shape[0], arr.shape[1]))
    if arr.size > MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels (shape %r), over the %d cap "
                         "(quatimage.MAX_PIXELS)"
                         % (op, name, arr.size, tuple(arr.shape), MAX_PIXELS))
    return arr


def _require_qimage(a, name: str, op: str) -> np.ndarray:
    """A real, finite, size-capped ``(H, W, 4)`` float64 quaternion image."""
    _precheck_size(a, name, op, MAX_PIXELS * 4, "MAX_PIXELS")
    arr = _as_float_array(a, name, op)
    if arr.ndim != 3 or arr.shape[2] != 4:
        raise ValueError("%s: %s must have shape (H, W, 4) — one quaternion "
                         "(w, x, y, z) per pixel — got shape %r; nothing is "
                         "reshaped silently. An (H, W, 3) colour image is the "
                         "rgbimage sort: pass it through rgb_to_quaternion first"
                         % (op, name, tuple(arr.shape)))
    if arr.shape[0] < 1 or arr.shape[1] < 1:
        raise ValueError("%s: %s is empty (shape %r)" % (op, name, tuple(arr.shape)))
    n = arr.shape[0] * arr.shape[1]
    if n > MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels (shape %r), over the %d cap "
                         "(quatimage.MAX_PIXELS)"
                         % (op, name, n, tuple(arr.shape), MAX_PIXELS))
    return arr


def _require_rgb(a, name: str, op: str) -> np.ndarray:
    """A real, finite, size-capped ``(H, W, 3)`` linear-RGB image."""
    _precheck_size(a, name, op, MAX_PIXELS * 3, "MAX_PIXELS")
    arr = _as_float_array(a, name, op)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError("%s: %s must have shape (H, W, 3) — linear RGB — got "
                         "shape %r; nothing is reshaped silently"
                         % (op, name, tuple(arr.shape)))
    if arr.shape[0] < 1 or arr.shape[1] < 1:
        raise ValueError("%s: %s is empty (shape %r)" % (op, name, tuple(arr.shape)))
    n = arr.shape[0] * arr.shape[1]
    if n > MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels (shape %r), over the %d cap "
                         "(quatimage.MAX_PIXELS)"
                         % (op, name, n, tuple(arr.shape), MAX_PIXELS))
    return arr


def _require_direction(a, name: str, op: str) -> np.ndarray:
    """A finite, non-degenerate 3-vector, returned unit length.

    Refuses the zero vector explicitly. ``pose_quat``'s helpers normalise with
    ``v / (norm + 1e-12)``, which turns a zero direction into a zero vector and
    then into the identity rotation without a word — the exact class of quiet
    wrong answer this module is built to refuse, so the check happens here,
    before anything from ``pose_quat`` is called."""
    v = _as_float_array(a, name, op).ravel()
    if v.size != 3:
        raise ValueError("%s: %s must be a 3-vector (an RGB direction), got %d "
                         "value(s)" % (op, name, v.size))
    n = float(np.linalg.norm(v))
    if n <= 0.0:
        raise ValueError("%s: %s is the zero vector — it names no direction. "
                         "(Normalising it with the usual `v / (norm + eps)` "
                         "would return zero and then the identity rotation, "
                         "silently)" % (op, name))
    if not np.isfinite(n):
        raise ValueError("%s: %s has a non-finite norm" % (op, name))
    return v / n


def _require_side(side, op: str) -> str:
    """``"left"`` or ``"right"`` — exactly, and there is no default anywhere.

    Quaternion multiplication does not commute, so a side-dependent operator has
    two answers and picking one for the caller is a silent choice: the wrong side
    raises nothing, makes no NaN, and returns a different plausible array. The
    argument is required at every call site in this module for that reason, and
    the string is matched exactly (no case folding) so that ``"Left"`` fails
    loudly instead of being guessed at."""
    if not isinstance(side, str):
        raise ValueError("%s: side must be the string 'left' or 'right', got %r. "
                         "There is no default: quaternion multiplication does not "
                         "commute, so the side is part of the operator's identity"
                         % (op, type(side).__name__))
    if side not in ("left", "right"):
        raise ValueError("%s: side must be exactly 'left' or 'right', got %r "
                         "(matched case-sensitively so a typo fails instead of "
                         "being guessed at)" % (op, side))
    return side


def _require_video(video, name: str, op: str, max_elements: int,
                   min_frames: int = 2) -> np.ndarray:
    """A validated ``(T, H, W)`` float64 clip, list-of-frames accepted.

    Same contract as ``videops`` / ``motionmag``: a 3-D array-like or a list of
    equal-shape 2-D frames, plus this module's size caps and the complex/masked
    refusals. Kept structurally identical to ``motionmag._require_video`` so that
    the head-to-head comparison in the tests differs only in the algorithm."""
    if isinstance(video, (list, tuple)):
        if not video:
            raise ValueError("%s: %s is an empty frame list" % (op, name))
        frames = []
        for i, f in enumerate(video):
            frames.append(_require_image(f, "%s[%d]" % (name, i), op))
        shapes = {f.shape for f in frames}
        if len(shapes) != 1:
            raise ValueError("%s: %s frames have differing shapes: %r"
                             % (op, name, sorted(shapes)))
        vid = np.stack(frames, axis=0)
    else:
        _precheck_size(video, name, op, max_elements, "MAX_PYRAMID_ELEMENTS")
        vid = _as_float_array(video, name, op)
    if vid.ndim != 3:
        raise ValueError("%s: %s must be a (T, H, W) clip, got a %d-D array of "
                         "shape %r — nothing is reshaped silently"
                         % (op, name, vid.ndim, tuple(vid.shape)))
    t, h, w = vid.shape
    if t < min_frames:
        raise ValueError("%s: %s has T=%d frames, need at least %d (a temporal "
                         "frequency is undefined below that)"
                         % (op, name, t, min_frames))
    if t > MAX_FRAMES:
        raise ValueError("%s: %s has T=%d frames, over the %d cap "
                         "(quatimage.MAX_FRAMES)" % (op, name, t, MAX_FRAMES))
    if h < 4 or w < 4:
        raise ValueError("%s: %s frames are %dx%d; at least 4x4 is needed for a "
                         "radial band to be sampled at all" % (op, name, h, w))
    if h * w > MAX_PIXELS:
        raise ValueError("%s: %s frames are %dx%d = %d pixels, over the %d cap "
                         "(quatimage.MAX_PIXELS)" % (op, name, h, w, h * w, MAX_PIXELS))
    if vid.size > max_elements:
        raise ValueError("%s: %s has T*H*W = %d elements (shape %r), over the %d "
                         "cap — this operator holds three real volumes and one "
                         "complex volume per band at once, so the cap is a memory "
                         "bound, not a preference"
                         % (op, name, vid.size, tuple(vid.shape), max_elements))
    return vid


def _require_band(f_lo, f_hi, fps, t: int, op: str):
    """Validate a temporal pass-band against the clip's own sampling.

    Four separate refusals, each one a way to get a plausible but wrong number:
    a non-positive ``fps`` (every frequency becomes infinite), a band that
    reaches DC (which scales *where the scene is* rather than its motion), a
    band above Nyquist (that frequency is not in the clip; folding it silently
    would report motion at the aliased rate), and an **empty** band (narrower
    than the clip's ``fps/T`` resolution, so the filter would return zeros and
    the caller would read "no motion")."""
    fs = _positive(fps, "fps")
    lo = _finite_scalar(f_lo, "f_lo")
    hi = _finite_scalar(f_hi, "f_hi")
    if lo <= 0.0:
        raise ValueError("%s: f_lo must be > 0, got %g — a pass-band that reaches "
                         "DC scales the static phase (where the scene *is*) "
                         "instead of its motion" % (op, lo))
    if hi <= lo:
        raise ValueError("%s: need f_lo < f_hi, got f_lo=%g f_hi=%g" % (op, lo, hi))
    nyq = 0.5 * fs
    if hi > nyq:
        raise ValueError("%s: f_hi=%g Hz is above the Nyquist frequency %g Hz "
                         "(fps=%g). That temporal frequency is not present in the "
                         "clip; it would alias onto a lower one. Refusing rather "
                         "than folding it silently" % (op, hi, nyq, fs))
    freq = np.fft.fftfreq(t, d=1.0 / fs)
    mask = (np.abs(freq) >= lo) & (np.abs(freq) <= hi)
    mask[0] = False
    if not mask.any():
        raise ValueError("%s: the pass-band [%g, %g] Hz contains no DFT bin. With "
                         "T=%d frames at fps=%g the bin spacing is %g Hz, so the "
                         "band must be at least that wide and must straddle a "
                         "multiple of it. Widen the band or record more frames"
                         % (op, lo, hi, t, fs, fs / t))
    return lo, hi, fs, mask


#: Reported dB values are clamped to the same window ``motionmag`` uses, for the
#: same reason: a noiseless synthetic has exactly zero out-of-band power, which
#: is a division by zero rather than an infinite SNR, and ``inf``/``nan`` would
#: poison every downstream arithmetic.
_MIN_SNR_DB = -100.0
_MAX_SNR_DB = 100.0


def _db(num: float, den: float) -> float:
    """``10*log10(num/den)`` clamped into the reported dB window."""
    if den <= 0.0:
        return _MAX_SNR_DB if num > 0.0 else _MIN_SNR_DB
    if num <= 0.0:
        return _MIN_SNR_DB
    v = 10.0 * np.log10(num / den)
    return float(min(max(v, _MIN_SNR_DB), _MAX_SNR_DB))


# --------------------------------------------------------------------------- #
# vectorised quaternion algebra (per pixel)                                    #
# --------------------------------------------------------------------------- #
def _hamilton(p: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Hamilton product of two ``(..., 4)`` quaternion fields, broadcasting.

    Component order ``(w, x, y, z)``, identical to ``pose_quat.quat_compose``;
    the tests assert agreement with it on random inputs to 1.4e-16. The scalar
    helper is not called in a loop because a ``(512, 512)`` image would mean a
    quarter of a million Python calls — the algebra is the same, the loop is not."""
    p0, p1, p2, p3 = p[..., 0], p[..., 1], p[..., 2], p[..., 3]
    q0, q1, q2, q3 = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack([
        p0 * q0 - p1 * q1 - p2 * q2 - p3 * q3,
        p0 * q1 + p1 * q0 + p2 * q3 - p3 * q2,
        p0 * q2 - p1 * q3 + p2 * q0 + p3 * q1,
        p0 * q3 + p1 * q2 - p2 * q1 + p3 * q0,
    ], axis=-1)


def rgb_to_quaternion(image_rgb) -> np.ndarray:
    """Embed a colour image as pure quaternions ``0 + R i + G j + B k``. → (H, W, 4).

    Sangwine's 1996 encoding, and the entry point of the whole colour half of
    this module: once a pixel is a quaternion, ``q x conj(q)`` rotates its colour
    and :func:`qft2` transforms the three channels as **one** hypercomplex signal
    instead of three unrelated real ones.

    The scalar (``w``) component is set to exactly zero — a *pure* quaternion —
    because that is what makes the conjugation a 3-D rotation. Values are not
    clamped: linear RGB after black-level subtraction legitimately goes negative,
    and clipping it would change the colour direction, which is the quantity
    every operator downstream reads.

    **Raises** ``ValueError``: *image_rgb* is not a finite ``(H, W, 3)`` numeric
    array, is complex / bool / string-typed / masked, or exceeds
    :data:`MAX_PIXELS`."""
    op = "rgb_to_quaternion"
    rgb = _require_rgb(image_rgb, "image_rgb", op)
    out = np.zeros(rgb.shape[:2] + (4,), np.float64)
    out[..., 1:] = rgb
    return out


def quaternion_to_rgb(qimage, allow_scalar: bool = False) -> np.ndarray:
    """Vector part of a quaternion image, as linear RGB. → (H, W, 3).

    The inverse of :func:`rgb_to_quaternion` — and, by default, a *checked*
    inverse. A quaternion image that picked up a scalar component somewhere (a
    Hamilton product with a non-pure quaternion, a monogenic signal handed here
    by mistake) is **refused** rather than silently truncated, because dropping
    the ``w`` component is exactly the kind of loss that produces a plausible
    picture from the wrong data. Pass ``allow_scalar=True`` to opt in to the
    truncation when it is what you meant.

    The tolerance is relative to the field's own peak modulus
    (:data:`_MONOGENIC_K_TOL`, 1e-9): a quaternion image that really is pure
    carries ``|w|`` at the 1e-17 level after a round trip through two FFTs, and
    anything with a meaningful scalar part is many orders above that. Nothing
    real lives in between.

    **Raises** ``ValueError``: *qimage* is not a finite ``(H, W, 4)`` array; or
    it has a non-negligible scalar part and ``allow_scalar`` is False."""
    op = "quaternion_to_rgb"
    q = _require_qimage(qimage, "qimage", op)
    if not isinstance(allow_scalar, (bool, np.bool_)):
        raise ValueError("%s: allow_scalar must be a bool, got %r"
                         % (op, type(allow_scalar).__name__))
    if not allow_scalar:
        peak = float(np.abs(q).max())
        wmax = float(np.abs(q[..., 0]).max())
        if peak > 0.0 and wmax > _MONOGENIC_K_TOL * peak:
            raise ValueError(
                "%s: the quaternion image is not pure — its scalar (w) component "
                "reaches %.6g against a field peak of %.6g (relative %.3g, over "
                "the %g tolerance). Dropping it would return a plausible colour "
                "image built from the wrong data. If the truncation is what you "
                "want, pass allow_scalar=True"
                % (op, wmax, peak, wmax / peak, _MONOGENIC_K_TOL))
    return np.ascontiguousarray(q[..., 1:])


def quat_norm(qimage) -> np.ndarray:
    """Per-pixel quaternion modulus ``|q| = sqrt(w^2+x^2+y^2+z^2)``. → (H, W).

    **Raw / unnormalised**, following ``complexops.cx_magnitude``: a modulus is a
    metric quantity and routinely exceeds one (a QFT spectrum's DC term is huge).
    For a colour quaternion it is the colour *magnitude* — the length of the RGB
    vector, i.e. luminance in the L2 sense; for a monogenic signal it is the
    local amplitude and :func:`monogenic_amplitude` is the name that says so.
    Use ``imgio.normalize`` for a displayable view."""
    op = "quat_norm"
    q = _require_qimage(qimage, "qimage", op)
    return np.sqrt((q * q).sum(axis=-1))


def quat_conjugate_image(qimage) -> np.ndarray:
    """Per-pixel quaternion conjugate ``(w, -x, -y, -z)``. → (H, W, 4).

    Exact and involutive: ``quat_conjugate_image(quat_conjugate_image(q)) is q``
    to the last bit (a sign flip is exact in IEEE 754). Agrees with
    ``pose_quat.quat_conjugate`` per pixel, asserted in the tests."""
    op = "quat_conjugate_image"
    q = _require_qimage(qimage, "qimage", op)
    out = q.copy()
    out[..., 1:] *= -1.0
    return out


def quat_normalize_image(qimage) -> np.ndarray:
    """Per-pixel normalisation to unit modulus. → (H, W, 4).

    **Fail-closed on a zero pixel**, which is the difference from
    ``pose_quat.quat_normalize``: that helper divides by ``norm + 1e-12``, so a
    zero quaternion comes back as (approximately) zero and, if it is then used as
    a rotor, ``pose_quat.quat_to_hom_mat3d`` normalises it *again* and returns
    the **identity rotation** — a wrong answer with no exception and no NaN. A
    quaternion image routinely contains exact zeros (a black pixel is
    ``(0,0,0,0)``), so the case is not hypothetical and it is refused by name,
    with the count and the first offending pixel in the message.

    **Raises** ``ValueError``: any pixel has modulus 0."""
    op = "quat_normalize_image"
    q = _require_qimage(qimage, "qimage", op)
    n = np.sqrt((q * q).sum(axis=-1))
    bad = n <= 0.0
    if bad.any():
        idx = np.argwhere(bad)
        raise ValueError("%s: %d pixel(s) have modulus 0 and no direction to "
                         "normalise towards — first at (row=%d, col=%d). This is "
                         "refused rather than divided by `norm + eps`, which "
                         "would return zero and, used as a rotor, the identity "
                         "rotation with nothing to signal it"
                         % (op, int(bad.sum()), int(idx[0, 0]), int(idx[0, 1])))
    return q / n[..., None]


def quat_image_multiply(qimage, other, side) -> np.ndarray:
    """Hamilton product of a quaternion image with a quaternion or a field. → (H, W, 4).

    ``side="left"`` computes ``other * qimage``; ``side="right"`` computes
    ``qimage * other``. **There is no default** — see :func:`_require_side`. The
    two results are genuinely different objects, not a sign convention: measured
    on a standard-normal ``(32, 32, 4)`` field against a unit rotor,
    ``max|left - right| = 3.143`` and ``mean|left - right| = 0.4948`` on data
    whose own extreme is 3.372 — that is, the two answers differ by as much as
    the data itself. Neither raises, neither is NaN, and both look like a
    perfectly good quaternion image.

    *other* is either a single quaternion (a ``(4,)`` array-like) or a full
    ``(H, W, 4)`` field of the same shape; anything else is refused rather than
    broadcast, because NumPy would happily broadcast a ``(H, 4)`` array along the
    wrong axis and produce an image-shaped answer to a different question.

    **Raises** ``ValueError``: either input is not a valid quaternion field;
    *other* is neither ``(4,)`` nor exactly ``qimage``'s shape; *side* is not
    ``'left'`` / ``'right'``."""
    op = "quat_image_multiply"
    q = _require_qimage(qimage, "qimage", op)
    s = _require_side(side, op)
    _precheck_size(other, "other", op, MAX_PIXELS * 4, "MAX_PIXELS")
    o = _as_float_array(other, "other", op)
    if o.shape == (4,):
        o = o.reshape(1, 1, 4)
    elif o.shape != q.shape:
        raise ValueError("%s: other must be a single quaternion of shape (4,) or "
                         "a field of exactly qimage's shape %r; got %r. Nothing "
                         "is broadcast along a guessed axis"
                         % (op, tuple(q.shape), tuple(o.shape)))
    return _hamilton(o, q) if s == "left" else _hamilton(q, o)


# --------------------------------------------------------------------------- #
# colour rotation and colour-selective filtering                                #
# --------------------------------------------------------------------------- #
def quat_color_rotate(qimage, axis_rgb, angle_rad) -> np.ndarray:
    """Rotate every pixel's colour about an RGB axis: ``q x conj(q)``. → (H, W, 4).

    The operation a complex pixel cannot express. ``axis_rgb`` is a direction in
    RGB space and ``angle_rad`` the rotation about it; the rotor
    ``q = cos(a/2) + sin(a/2) * axis`` is built with
    ``pose_quat.axis_angle_to_quat`` and the conjugation is applied to the vector
    part of every pixel, leaving the scalar part untouched (a conjugation cannot
    move it).

    Exactness and what it is worth
    ------------------------------
    The conjugation is applied through the ``3x3`` matrix from
    ``pose_quat.quat_to_hom_mat3d`` rather than by two per-pixel Hamilton
    products, because for a ``(512, 512)`` image that is 500k quaternion
    multiplications versus one ``einsum``. The two are the *same map*, measured:
    against per-pixel ``pose_quat.quat_rotate_point_3d`` the agreement is
    ``2.3e-12`` and the round trip ``rotate(rotate(q, ax, a), ax, -a)`` returns
    ``q`` to ``1.9e-12``.

    **Those are 1e-12, not 1e-16, and the reason is worth knowing.**
    ``pose_quat.quat_normalize`` divides by ``norm + 1e-12`` rather than by
    ``norm``, so even a perfectly unit rotor comes back scaled by
    ``1/(1 + 1e-12)`` and the matrix built from it is short of orthogonal by
    ``|R^T R - I| = 1.4e-12`` (measured; the exact Rodrigues matrix for the same
    rotor differs from ``pose_quat``'s by 1.1e-12). Every colour rotated through
    this operator is therefore shrunk by about one part in 1e12. That is far
    below any imaging tolerance and the reuse is worth more than the twelfth
    decimal, but it is a systematic bias rather than rounding and it is recorded
    here rather than left for someone to rediscover.

    The matrix identity is also the honest limit of the *capability* claim.
    ``SO(3)`` and the unit quaternions are isomorphic, so **a 3x3 orthogonal
    colour matrix does exactly this and nothing is lost by using one**. What a
    quaternion buys is 4 numbers instead of 9, exact closure under composition,
    and ``slerp``. Measured over 100,000 random small rotations composed in
    sequence, the quaternion (renormalised each step, 4 divisions) drifts from
    unit norm by **0.0** while the matrix (composed by multiplication, not
    re-orthonormalised) drifts to ``|R^T R - I| = 4.4e-10``. Real, and small.
    What a *channelwise* pipeline — three independent scalar filters, which is
    what running the complex ops on R, G and B separately means — cannot do is
    this operation at all: it never mixes channels, so it cannot turn red towards
    green. That is the comparison in ``tests/test_quatimage.py``, and it is the
    one that is decisive.

    Two traps in the rotor, both refused here rather than downstream
    ---------------------------------------------------------------
    ``pose_quat.axis_angle_to_quat`` normalises its axis as
    ``n / (norm + 1e-12)``, so a **zero axis** returns ``[cos(a/2), 0, 0, 0]``,
    which ``quat_to_hom_mat3d`` re-normalises to the identity: a rotation request
    silently becomes a no-op. Worse, at ``angle_rad = pi`` that same path gives
    ``[0, 0, 0, 0]``, whose normalisation is ``0/(0+1e-12) = 0`` and whose matrix
    is again the identity — a *180-degree* colour rotation silently becoming a
    copy. Both are stopped by :func:`_require_direction` and by an explicit
    unit-norm assertion on the finished rotor (tolerance :data:`_UNIT_TOL`), so
    this operator never hands a degenerate rotor to the matrix builder.

    **Raises** ``ValueError``: *qimage* is not a valid ``(H, W, 4)`` field;
    *axis_rgb* is not a finite non-zero 3-vector; *angle_rad* is not a finite
    real scalar; the constructed rotor is not unit norm."""
    op = "quat_color_rotate"
    import pose_quat

    q = _require_qimage(qimage, "qimage", op)
    axis = _require_direction(axis_rgb, "axis_rgb", op)
    ang = _finite_scalar(angle_rad, "angle_rad")
    rot = pose_quat.axis_angle_to_quat(axis[0], axis[1], axis[2], ang)
    nrm = float(np.linalg.norm(rot))
    if abs(nrm - 1.0) > _UNIT_TOL:
        raise ValueError("%s: the rotor built from axis=%r angle=%g has norm "
                         "%.17g, not 1 (tolerance %g). A non-unit rotor scales "
                         "the colour by |q|^2 as well as rotating it, which is a "
                         "wrong answer that raises nothing"
                         % (op, tuple(axis), ang, nrm, _UNIT_TOL))
    R = pose_quat.quat_to_hom_mat3d(rot)[:3, :3]
    out = q.copy()
    out[..., 1:] = np.einsum("ij,hwj->hwi", R, q[..., 1:])
    return out


def quat_color_filter(qimage, direction_rgb, mode) -> np.ndarray:
    """Keep or remove one colour direction, exactly. → (H, W, 4).

    ``mode="remove"`` returns ``v - (v.g) g`` for the unit RGB direction ``g``:
    the component along ``g`` is **exactly zero everywhere afterwards**, to
    machine precision (measured max residual 5.8e-16 and 6.5e-16 on two random
    colour images — seed-dependent only at the 1e-16 level),
    and ``remove + keep`` reproduces the input to **0.0** exactly.
    ``mode="keep"`` returns the complementary ``(v.g) g``. The scalar part is
    passed through untouched in both.

    **There is no default mode.** The two are opposites, both return a valid
    picture, and neither raises — so choosing for the caller would be a coin flip
    that never announces itself.

    Not a new algorithm, and this docstring will not pretend otherwise
    -----------------------------------------------------------------
    The ``remove`` branch **is** the specular-invariant projection of Mallick et
    al. (2005), which this repository already implements as
    ``specularity.specular_free_transform`` for the ``rgbimage`` sort. Rather
    than write the same three lines twice, this operator *delegates* to it — so
    agreement between the two sorts is by construction rather than by luck, and a
    future fix in one is a fix in both. What is added here is the ``keep``
    branch (which has no counterpart there) and the ``qimage`` sort, so the
    projection composes with :func:`quat_color_rotate` and :func:`qft2`.

    What this can do that a channelwise pipeline cannot
    ---------------------------------------------------
    A per-channel filter applies a diagonal matrix, and ``I - g g^T`` is diagonal
    only when ``g`` is a coordinate axis. For ``g = (1,1,1)/sqrt(3)`` — remove
    the grey axis, i.e. keep only chromatic content — the *best possible*
    diagonal approximation is off by ``||P - diag(P)||_2 = 0.666667`` in operator
    norm. Concretely, a pure red pixel ``(1, 0, 0)`` must become
    ``(0.666667, -0.333333, -0.333333)``; the best diagonal filter can only reach
    ``(0.666667, 0, 0)``, an error of ``0.471405`` — it cannot put anything into
    the green and blue channels, because it multiplies each channel by a number
    and both start at zero. The impossibility is structural, not a tuning gap.
    (A full 3x3 colour matrix, of course, does it exactly; see
    :func:`quat_color_rotate` for that half of the accounting.)

    **Raises** ``ValueError``: *qimage* is not a valid ``(H, W, 4)`` field;
    *direction_rgb* is not a finite non-zero 3-vector; *mode* is not
    ``'remove'`` / ``'keep'``."""
    op = "quat_color_filter"
    import specularity

    q = _require_qimage(qimage, "qimage", op)
    g = _require_direction(direction_rgb, "direction_rgb", op)
    if not isinstance(mode, str):
        raise ValueError("%s: mode must be the string 'remove' or 'keep', got %r. "
                         "There is no default: the two are opposites and both "
                         "return a valid-looking image"
                         % (op, type(mode).__name__))
    if mode not in ("remove", "keep"):
        raise ValueError("%s: mode must be exactly 'remove' or 'keep', got %r"
                         % (op, mode))
    v = np.ascontiguousarray(q[..., 1:])
    removed = specularity.specular_free_transform(v, g)
    out = q.copy()
    out[..., 1:] = removed if mode == "remove" else (v - removed)
    return out


# --------------------------------------------------------------------------- #
# hypercomplex Fourier transform                                                #
# --------------------------------------------------------------------------- #
#: The default transform axis: the grey (luminance) direction of RGB space. This
#: is Sangwine's original choice and it is not arbitrary — with ``mu`` along the
#: grey axis the symplectic decomposition splits every pixel into its luminance
#: part and its chromatic part, so the two halves of the spectrum have a colour
#: meaning instead of an arbitrary one.
_MU_GREY = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)


def _mu_basis(mu, op: str):
    """``(mu, nu, lam)``: an orthonormal basis of the pure quaternions.

    ``lam = mu * nu`` (their Hamilton product, which for orthogonal pure
    quaternions is their cross product). ``nu`` is chosen deterministically — the
    coordinate axis least aligned with ``mu``, orthogonalised — because a random
    or input-dependent choice would make the transform irreproducible.

    The choice of ``nu`` **does not affect the transform**: rotating ``nu`` by an
    angle ``a`` in the plane orthogonal to ``mu`` multiplies the symplectic part
    ``B`` by ``exp(-mu a)`` and ``nu`` itself by ``exp(+mu a)``, which cancel
    exactly. That is asserted numerically in the tests (two different ``nu``,
    max difference 0.0)."""
    m = _MU_GREY if mu is None else _require_direction(mu, "mu", op)
    e = np.eye(3)[int(np.argmin(np.abs(m)))]
    n = e - float(e @ m) * m
    nn = float(np.linalg.norm(n))
    if nn <= 0.0:                       # unreachable: e is the least-aligned axis
        raise ValueError("%s: could not build a basis orthogonal to mu=%r"
                         % (op, tuple(m)))
    n = n / nn
    lam = np.cross(m, n)
    return m, n, lam


def _to_symplectic(q: np.ndarray, m, n, lam):
    """``(A, B)`` complex fields with ``q = A + B * nu`` and ``A, B`` in ``C_mu``."""
    v = q[..., 1:]
    a = q[..., 0]
    b = v @ m
    c = v @ n
    d = v @ lam
    return a + 1j * b, c + 1j * d


def _from_symplectic(A: np.ndarray, B: np.ndarray, m, n, lam) -> np.ndarray:
    """Inverse of :func:`_to_symplectic`."""
    out = np.empty(A.shape + (4,), np.float64)
    out[..., 0] = np.real(A)
    out[..., 1:] = (np.imag(A)[..., None] * m[None, None, :]
                    + np.real(B)[..., None] * n[None, None, :]
                    + np.imag(B)[..., None] * lam[None, None, :])
    return out


def qft2(qimage, side, mu=None) -> np.ndarray:
    """Quaternion (hypercomplex) 2-D Fourier transform. → (H, W, 4) centred spectrum.

    The colour analogue of ``complexops.cx_fft``: a colour image is transformed
    as **one** hypercomplex signal rather than three unrelated real ones. The
    kernel is ``exp(-mu * 2*pi*(u*x/W + v*y/H))`` for a unit pure quaternion
    *mu* (default: the grey axis of RGB, Sangwine's choice), and because
    quaternions do not commute the kernel can be applied on either side:

    * ``side="left"``  — ``F[u,v] = sum_{x,y} E(x,y,u,v) * f[x,y]``
    * ``side="right"`` — ``F[u,v] = sum_{x,y} f[x,y] * E(x,y,u,v)``

    **The argument is required.** Left and right are not a sign convention. On
    the fuzzer's ``(32, 32)`` dichromatic render they differ by
    ``max|F_L - F_R| = 19.11`` against a peak modulus of ``1045`` (1.8 % of full
    scale) and on a random colour field by ``33.35`` against ``892.9`` (3.7 %; another seed
    gives 34.05 against 892) —
    with no exception and no NaN to mark the difference. **Mixing them across a
    round trip is much worse**, because there the disagreement is not attenuated
    by the spectrum's dynamic range: ``iqft2(qft2(q, "left"), "right")`` returns
    an image whose error reaches ``1.113`` on data whose own range is ``0.9994``
    — a completely different picture that still looks like a picture. (On the
    grey-axis-dominated dichromatic render the same mistake costs only ``0.054``
    against a range of ``1.076``, which is the dangerous case: a 5 % error is
    exactly the size that survives a visual check.)

    The spectrum is returned **centred** (DC at the array centre, via
    ``fftshift``), matching the convention ``complexops.cx_fft`` established for
    the ``cimage`` sort. :func:`iqft2` un-centres before inverting, and the round
    trip is exact: measured ``max|iqft2(qft2(q, s), s) - q| = 2.22e-15`` for both
    sides on a standard-normal ``(32, 32, 4)`` field.

    How it is computed, and why that is not a shortcut
    --------------------------------------------------
    Every quaternion splits as ``q = A + B*nu`` with ``A, B`` in the commutative
    subfield generated by ``mu`` (the *symplectic decomposition*, Ell &
    Sangwine 2007). The kernel commutes with ``A`` and *anti*-commutes past
    ``nu``, so the whole transform reduces to two ordinary complex FFTs — for
    the left transform both with the standard kernel, for the right one of them
    with the conjugate kernel. **That reduction is what makes left and right
    differ**, and it is verified against a brute-force ``O(N^2)`` quaternion DFT
    written straight from the definition, on a 4x4 image, for three different
    ``mu`` and both sides: the largest disagreement over all six combinations is
    **8.2e-15**. The fast path is checked against the definition, not against
    itself. The choice of the internal ``nu`` is likewise verified not to matter
    (two different ``nu``, max difference 1.4e-14 — see :func:`_mu_basis`).

    Honest accounting against the channelwise baseline
    --------------------------------------------------
    Because the decomposition above is *linear* in the channels, the QFT is a
    fixed recombination of the three per-channel complex FFTs: rebuilding
    ``qft2(q, "left")`` from three ``numpy.fft.fft2`` calls on the R, G and B
    planes agrees to ``max|err| = 1.14e-13``. So this transform **buys no
    information a channelwise FFT does not already contain**, and this module
    does not claim it does. It also does not buy speed — it moves four real
    transforms' worth of data where the channelwise route moves three, and pays
    for the symplectic pack/unpack on top: measured on ``(256, 256)``, best of
    20, **8.246 ms against 3.409 ms, i.e. 2.42x slower** (run to run, 2.3x-2.4x). What it buys is that
    the four numbers stay one algebraic object, so a rotor can be applied to the
    spectrum and the colour meaning of ``mu`` survives the transform.

    **Raises** ``ValueError``: *qimage* is not a valid ``(H, W, 4)`` field;
    *side* is not ``'left'`` / ``'right'``; *mu* is not a finite non-zero
    3-vector."""
    op = "qft2"
    q = _require_qimage(qimage, "qimage", op)
    s = _require_side(side, op)
    m, n, lam = _mu_basis(mu, op)
    A, B = _to_symplectic(q, m, n, lam)
    FA = np.fft.fft2(A)
    # left:  E * (B nu) = (E B) nu          -> standard kernel
    # right: (B nu) * E = (B conj(E)) nu    -> conjugate kernel
    FB = np.fft.fft2(B) if s == "left" else np.conj(np.fft.fft2(np.conj(B)))
    return _from_symplectic(np.fft.fftshift(FA), np.fft.fftshift(FB), m, n, lam)


def iqft2(spectrum, side, mu=None) -> np.ndarray:
    """Inverse quaternion Fourier transform of a **centred** spectrum. → (H, W, 4).

    The exact inverse of :func:`qft2` **for the same side and the same mu**:
    measured round-trip error ``2.22e-15`` for both sides on a standard-normal
    ``(32, 32, 4)`` field. The kernel is ``exp(+mu * 2*pi*(...))`` applied on the
    side named, and the ``1/(H*W)`` normalisation is carried here, as in
    ``numpy.fft.ifft2``.

    **Using the wrong side does not raise.** ``iqft2(qft2(q, "left"), "right")``
    returns a finite, plausible quaternion image that is simply not ``q``:
    measured ``max|err| = 1.113`` on a random colour image whose own range is
    ``0.9994`` (another seed: 1.063 against 1.0), and — the dangerous case — only ``0.054`` against a range of
    ``1.076`` on a grey-axis-dominated one, which is small enough to survive a
    look at the picture. The ``side`` argument is required at both ends for
    exactly this reason, and the two calls must agree: nothing in the data
    records which transform produced it, so nothing downstream can catch the
    mismatch for you.

    **Raises** ``ValueError``: *spectrum* is not a valid ``(H, W, 4)`` field;
    *side* is not ``'left'`` / ``'right'``; *mu* is not a finite non-zero
    3-vector."""
    op = "iqft2"
    F = _require_qimage(spectrum, "spectrum", op)
    s = _require_side(side, op)
    m, n, lam = _mu_basis(mu, op)
    FA, FB = _to_symplectic(F, m, n, lam)
    FA = np.fft.ifftshift(FA)
    FB = np.fft.ifftshift(FB)
    A = np.fft.ifft2(FA)
    # The B part of the inverse mirrors the forward: the conjugate kernel moves
    # to the other side, so exactly one of the two inverses is conjugated.
    B = np.fft.ifft2(FB) if s == "left" else np.conj(np.fft.ifft2(np.conj(FB)))
    return _from_symplectic(A, B, m, n, lam)


# --------------------------------------------------------------------------- #
# quaternion correlation                                                        #
# --------------------------------------------------------------------------- #
def quat_correlate(qimage, template) -> np.ndarray:
    """Quaternion cross-correlation ``sum_s conj(a(s)) * b(s+t)``. → (H, W, 4).

    Colour template matching that keeps the **colour geometry**, not just the
    colour magnitude. The scalar part of the result is
    ``sum (a_R b_R + a_G b_G + a_B b_B)`` — exactly the sum of the three
    per-channel correlations, i.e. what a channelwise pipeline computes and all
    it computes. The *vector* part is ``-sum (a x b)``, the accumulated colour
    cross-product, and it is zero exactly when the two colour fields are
    parallel. So the same call answers "how well does it match?" (scalar part)
    **and** "in what way does the colour fail to line up?" (vector part).

    Measured on a 32x32 patch whose colours lie in the red-green plane, matched
    against a copy of itself rotated about the blue axis. The scalar part is
    ``cos(angle)`` times the self-correlation, exactly, and
    ``atan2(|vector|, scalar)`` returns the rotation angle:

    ===========  ==================  =================  ==================
    rotation     scalar/self ratio   ``cos(angle)``     angle recovered
    ===========  ==================  =================  ==================
    0 deg        1.000000            1.000000           0.000000 deg
    30 deg       0.866025            0.866025           30.000000 deg
    90 deg       0.000000            0.000000           90.000000 deg
    ===========  ==================  =================  ==================

    with the vector direction at ``(0.000, 0.000, -1.000)`` — the **negative** of
    the rotation axis, because the conjugate sits on the left of the product. A
    channelwise pipeline has no term that can produce any of that: the
    cross-products are *cross*-channel products, and three independent channel
    correlations never form them. (Verified in the same test: the scalar part
    equals the summed per-channel correlation to 0.0 exactly, so the channelwise
    baseline recovers the scalar part and nothing else.)

    **The exact reading needs the colours to lie in the plane orthogonal to the
    rotation axis, and the docstring says so because the general case is
    biased.** For a colour field with a component along the axis, the vector part
    picks up terms in ``a_z`` and the recovered angle is wrong: measured on a
    uniform-random colour patch rotated 30 degrees about blue, the same formula
    returns **22.524 degrees** on an axis of ``(0.247, 0.419, -0.874)`` instead
    of ``(0, 0, -1)``. That is a quiet wrong number, it is inherent to summing
    per-pixel cross products, and it is not detectable from the result — so the
    precondition is part of the contract.

    Both inputs must be pure quaternion images for any of the above to hold; a
    non-zero scalar part is not refused (it is algebraically fine) but it
    contributes to both parts and the colour interpretation stops applying.

    **The correlation is circular** (computed with FFTs, like
    ``filters_freq``'s family): a template near the border wraps around. Pad the
    inputs if that matters. Shapes must match exactly; a smaller template must be
    zero-padded into the image's shape by the caller, because silently choosing
    a padding origin would move the peak.

    **Raises** ``ValueError``: either input is not a valid ``(H, W, 4)`` field,
    or the two shapes differ."""
    op = "quat_correlate"
    a = _require_qimage(qimage, "qimage", op)
    b = _require_qimage(template, "template", op)
    if a.shape != b.shape:
        raise ValueError("%s: qimage %r and template %r must have the same shape "
                         "— a smaller template must be zero-padded by the caller, "
                         "because choosing the padding origin here would move the "
                         "correlation peak without saying so"
                         % (op, tuple(a.shape), tuple(b.shape)))
    Fa = [np.fft.fft2(a[..., i]) for i in range(4)]
    Fb = [np.fft.fft2(b[..., i]) for i in range(4)]

    def xc(i, j):
        """Circular cross-correlation ``sum_s a_i(s) b_j(s+t)``."""
        return np.real(np.fft.ifft2(np.conj(Fa[i]) * Fb[j]))

    # conj(a) = (a0, -a1, -a2, -a3); expand the Hamilton product term by term.
    c0 = xc(0, 0) + xc(1, 1) + xc(2, 2) + xc(3, 3)
    c1 = xc(0, 1) - xc(1, 0) - xc(2, 3) + xc(3, 2)
    c2 = xc(0, 2) + xc(1, 3) - xc(2, 0) - xc(3, 1)
    c3 = xc(0, 3) - xc(1, 2) + xc(2, 1) - xc(3, 0)
    return np.stack([c0, c1, c2, c3], axis=-1)


# --------------------------------------------------------------------------- #
# Riesz transform / monogenic signal                                            #
# --------------------------------------------------------------------------- #
def _riesz_kernels(h: int, w: int):
    """``(H1, H2)``, the Riesz multipliers ``-i*u/|w|`` and ``-i*v/|w|``.

    Zero at DC, where the direction of the frequency vector is undefined. Both
    are purely imaginary and odd, so ``H(-w) = conj(H(w))`` and the transform of
    a real image is real — except at the (at most four) self-conjugate points of
    an even-sized grid, where ``-w`` maps to ``w`` and no purely imaginary
    multiplier can be self-conjugate. Taking the real part discards the residue
    there, which is not a fudge but the projection onto the Hermitian part, and
    is *identical* to zeroing the multiplier at those bins (their transform
    coefficient is real, so ``i*F`` is purely imaginary and ``Re`` kills it
    exactly).

    **How much is discarded is a property of the image, not a rounding error,
    and it can be large.** On a 64x64 uniform-random image the discarded
    imaginary part is 1.617e-01 of the real part in L1 — 16 %, because a random
    image has substantial energy at the Nyquist corners. On a band-passed image
    it is **exactly zero**: the log-radial band of :func:`monogenic_signal`
    evaluates to 0.0 at all three non-DC self-conjugate bins, so the residue
    there is 4.1e-17 against a signal of 2.1e-01. That is one of the reasons the
    monogenic signal band-passes first, and the reason to read
    :func:`riesz_transform` of a raw image with care."""
    fv = np.fft.fftfreq(h)[:, None]
    fu = np.fft.fftfreq(w)[None, :]
    r = np.sqrt(fu * fu + fv * fv)
    inv = np.where(r > 0.0, 1.0 / np.where(r > 0.0, r, 1.0), 0.0)
    return -1j * fu * inv, -1j * fv * inv, r


def riesz_transform(image) -> np.ndarray:
    """The 2-D Riesz transform of an image, as a pure quaternion field. → (H, W, 4).

    The isotropic generalisation of the Hilbert transform: a *pair* of filters
    with frequency responses ``-i*u/|w|`` and ``-i*v/|w|``, returned as the
    quaternion ``(0, R1 f, R2 f, 0)``. It is the 2-D object that has no complex
    analogue — the 1-D analytic signal needs a direction to say which way "90
    degrees later" is, and in 2-D there is no single direction, so the answer
    needs two components and therefore an algebra with room for them.

    Closed form, which is how this is tested rather than eyeballed
    -------------------------------------------------------------
    For a grating ``cos(2*pi*(u0*x + v0*y))`` sampled on the DFT grid,

        ``R1 = (u0/|w0|) * sin(2*pi*(u0*x + v0*y))``,
        ``R2 = (v0/|w0|) * sin(...)``

    exactly. Measured over a table of eight grid-exact orientations from 0 to
    159.4 degrees on a 64x64 frame, the largest absolute deviation from that
    closed form is **6.1e-15**, and the orientation recovered through
    :func:`monogenic_orientation` matches the grating's to **3.6e-15 rad** at
    every one of them. There is no tolerance to choose.

    Note the scalar component is 0, so this is the Riesz *transform* and not the
    monogenic signal — feeding it to :func:`monogenic_phase` gives ``pi/2``
    everywhere, correctly but uselessly. Use :func:`monogenic_signal`, which
    keeps the band-pass image in the scalar slot.

    **Raises** ``ValueError``: *image* is not a finite real ``(H, W)`` array with
    ``H, W >= 2``, or exceeds :data:`MAX_PIXELS`."""
    op = "riesz_transform"
    img = _require_image(image, "image", op)
    h, w = img.shape
    H1, H2, _r = _riesz_kernels(h, w)
    F = np.fft.fft2(img)
    out = np.zeros((h, w, 4), np.float64)
    out[..., 1] = np.real(np.fft.ifft2(F * H1))
    out[..., 2] = np.real(np.fft.ifft2(F * H2))
    return out


def monogenic_signal(image, wavelength_px=8.0, bandwidth_octaves=1.0) -> np.ndarray:
    """The monogenic signal of an image at one scale. → (H, W, 4).

    Felsberg & Sommer (2001). The image is band-passed by a log-radial raised
    cosine centred at ``1/wavelength_px`` cycles/pixel with half-width
    *bandwidth_octaves*, and the result is packed with its Riesz pair as the
    quaternion ``(band-pass image, R1, R2, 0)``. From that single object
    :func:`monogenic_amplitude`, :func:`monogenic_phase` and
    :func:`monogenic_orientation` read the local contrast, the local phase and
    the local orientation — the 2-D analogue of what ``|z|`` and ``arg z`` give
    a 1-D analytic signal, with orientation as the extra degree of freedom that
    only exists in 2-D.

    The band-pass is applied *before* the Riesz kernels because the Riesz
    multiplier has a jump at DC: without a band that excludes DC the "local
    phase" of the image mean is undefined, not merely noisy.

    Closed form
    -----------
    A grating exactly at the band centre passes with gain 1, so for
    ``contrast * cos(2*pi*(u0*x+v0*y) + p)`` the amplitude is ``contrast``
    everywhere, the phase is the grating's own phase, and the orientation is
    ``atan2(v0, u0) mod pi``. Measured on a 64x64 frame with an 8 px grating of
    unit contrast and phase 0.7: amplitude mean exactly ``1.0`` with a spread of
    ``8.9e-16`` across the frame, phase error ``5.3e-15`` rad, orientation error
    ``0.0`` rad.

    **Honest limit.** The phase is well defined only where the amplitude is; in a
    flat region the amplitude is at the rounding floor and the phase is the angle
    of numerical dust. Nothing here suppresses that — the amplitude map *is* the
    confidence map and it is returned in the same object, so a caller can mask on
    it. The operators that consume the signal (:func:`riesz_displacement`,
    :func:`riesz_motion_magnify`) do mask, with the same relative thresholds
    :mod:`motionmag` uses, so their numbers are comparable.

    **Raises** ``ValueError``: *image* is not a finite real ``(H, W)`` array;
    *wavelength_px* is not ``> 2`` (a shorter wavelength is past Nyquist and the
    band would be empty); *bandwidth_octaves* is not ``> 0``; the band contains
    no frequency bin of this frame size."""
    op = "monogenic_signal"
    img = _require_image(image, "image", op)
    lam = _positive(wavelength_px, "wavelength_px")
    bw = _positive(bandwidth_octaves, "bandwidth_octaves")
    if lam <= 2.0:
        raise ValueError("%s: wavelength_px=%g is at or past the two-pixel Nyquist "
                         "limit — that spatial frequency is not present in a "
                         "sampled image, so the band would be empty and the "
                         "'local phase' would be the phase of nothing"
                         % (op, lam))
    h, w = img.shape
    H1, H2, r = _riesz_kernels(h, w)
    r0 = 1.0 / lam
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.where(r > 0.0, np.log2(np.where(r > 0.0, r, 1.0) / r0), 0.0)
    G = np.where((r > 0.0) & (np.abs(x) <= bw), np.cos(0.5 * np.pi * x / bw), 0.0)
    if not (G > 0.0).any():
        raise ValueError("%s: the band centred at 1/%g = %g cycles/px with a "
                         "half-width of %g octave(s) contains no frequency bin of "
                         "a %dx%d frame. Widen bandwidth_octaves, lengthen "
                         "wavelength_px, or use a larger frame"
                         % (op, lam, r0, bw, h, w))
    F = np.fft.fft2(img) * G
    out = np.zeros((h, w, 4), np.float64)
    out[..., 0] = np.real(np.fft.ifft2(F))
    out[..., 1] = np.real(np.fft.ifft2(F * H1))
    out[..., 2] = np.real(np.fft.ifft2(F * H2))
    return out


def _require_monogenic(qimage, name: str, op: str) -> np.ndarray:
    """A ``qimage`` that really is a monogenic signal: its ``k`` component is 0.

    This is the guard that stops the module's two halves from being confused. A
    monogenic signal has ``(band, R1, R2, 0)`` — the fourth component is zero by
    construction. A **colour** quaternion has ``(0, R, G, B)`` and its fourth
    component is the blue channel. Without this check, handing a colour image to
    :func:`monogenic_orientation` would return ``atan2(G, R)`` — a finite,
    smooth, entirely plausible orientation map of nothing at all. That is the
    exact failure mode this repository's type discipline exists to prevent, and
    a shape check cannot catch it because both are ``(H, W, 4)``."""
    q = _require_qimage(qimage, name, op)
    peak = float(np.abs(q).max())
    kmax = float(np.abs(q[..., 3]).max())
    if peak > 0.0 and kmax > _MONOGENIC_K_TOL * peak:
        raise ValueError(
            "%s: %s is not a monogenic signal — its k component reaches %.6g "
            "against a field peak of %.6g (relative %.3g, over the %g "
            "tolerance). A monogenic signal is (band-pass image, R1, R2, 0); a "
            "colour quaternion from rgb_to_quaternion has the blue channel "
            "there, and reading it as a monogenic signal returns a perfectly "
            "smooth orientation map of nothing. Build the signal with "
            "monogenic_signal() or riesz_transform()"
            % (op, name, kmax, peak, kmax / peak, _MONOGENIC_K_TOL))
    return q


def monogenic_amplitude(qimage) -> np.ndarray:
    """Local amplitude ``sqrt(f^2 + R1^2 + R2^2)`` of a monogenic signal. → (H, W).

    The local contrast at the signal's scale, and the confidence map for
    :func:`monogenic_phase` / :func:`monogenic_orientation`, which mean nothing
    where this is at the rounding floor. **Raw / unnormalised** (a contrast is a
    metric quantity), in the same spirit as ``complexops.cx_magnitude``.

    For a unit-contrast grating at the band centre it is exactly 1.0 (measured
    spread 8.9e-16 over a 64x64 frame) and, unlike a squared oriented-filter
    response, it is *isotropic*: rotating the grating does not change it.
    Measured over eight grid-exact orientations the amplitude spans
    ``[0.99999999999999911, 1.0000000000000011]`` — a total spread of 2.0e-15
    across all of them, which is the isotropy claim as a number.

    **Raises** ``ValueError``: the input is not a valid quaternion field, or its
    ``k`` component is non-zero (see :func:`_require_monogenic`)."""
    op = "monogenic_amplitude"
    q = _require_monogenic(qimage, "qimage", op)
    return np.sqrt(q[..., 0] ** 2 + q[..., 1] ** 2 + q[..., 2] ** 2)


def monogenic_phase(qimage, display: bool = False) -> np.ndarray:
    """Local phase ``atan2(|R|, f)`` of a monogenic signal. → (H, W).

    In ``[0, pi]`` — the monogenic phase is measured against the *magnitude* of
    the Riesz vector, whose sign is carried by the orientation instead, so the
    range is a half turn rather than a full one. That is the standard
    convention (Felsberg & Sommer) and it is stated here because a caller
    arriving from ``complexops.cx_phase`` (whose raw range is ``(-pi, pi]``) will
    otherwise assume a full turn and see a "wrapped" map that is not wrapped.

    ``display=True`` maps ``[0, pi]`` to ``[0, 1]`` for viewing; the default is
    ``False`` — the **opposite** of ``cx_phase``'s default, deliberately,
    because the consumers of this quantity in this module are numerical, and a
    display scaling that arrives silently in a measurement is a factor of ``pi``
    that nothing announces.

    Phase is the quantity a translation shifts linearly, which is why the whole
    motion half of this module reads it. For an edge, phase 0 means the peak of
    a bright line, ``pi/2`` a step edge and ``pi`` the peak of a dark line — the
    local *structure type*, independent of contrast.

    **Raises** ``ValueError``: the input is not a valid quaternion field, or its
    ``k`` component is non-zero; *display* is not a bool."""
    op = "monogenic_phase"
    q = _require_monogenic(qimage, "qimage", op)
    if not isinstance(display, (bool, np.bool_)):
        raise ValueError("%s: display must be a bool, got %r"
                         % (op, type(display).__name__))
    ph = np.arctan2(np.sqrt(q[..., 1] ** 2 + q[..., 2] ** 2), q[..., 0])
    return ph / np.pi if display else ph


def monogenic_orientation(qimage, display: bool = False) -> np.ndarray:
    """Local orientation ``atan2(R2, R1)`` of a monogenic signal. → (H, W).

    Radians in ``[0, pi)``: an orientation is defined modulo ``pi`` (a grating at
    10 degrees and one at 190 degrees are the same grating), and the value is
    folded into that range rather than left in ``(-pi, pi]`` where the same
    structure would read as two different numbers on either side of a contrast
    reversal. ``display=True`` maps it to ``[0, 1]``.

    **Continuous, not quantised** — the angle is read directly from two filters,
    for any angle, where a steerable bank with ``K`` orientations interpolates
    between its ``K``. Measured against eight grid-exact grating orientations the
    error is at most **3.6e-15 rad**, including the obliques. (Whether that
    buys anything downstream is a separate question, and the measured answer is
    mostly *no* — see :func:`riesz_displacement`.)

    **Where it is undefined, and the mask is not the one you expect.** The
    orientation dies where the *Riesz vector* dies, which is at every
    even-symmetric point — local phase 0 or pi, the crest of a bright or dark
    line — and **the amplitude is at full strength there**. Measured on a 45-degree
    grating, the worst orientation error over the whole frame is 0.2764 rad, at a
    pixel where ``|R| = 6.8e-16`` and :func:`monogenic_amplitude` reads
    ``1.0000``. So masking on the amplitude does not protect you; mask on
    ``hypot(q[..., 1], q[..., 2])``, the Riesz magnitude. With that mask the
    error over the same eight orientations is at most 3.6e-15 rad.

    Where the Riesz vector is exactly zero, ``atan2(0, 0) = 0`` is returned —
    a *value*, not a measurement.

    **Raises** ``ValueError``: the input is not a valid quaternion field, or its
    ``k`` component is non-zero; *display* is not a bool."""
    op = "monogenic_orientation"
    q = _require_monogenic(qimage, "qimage", op)
    if not isinstance(display, (bool, np.bool_)):
        raise ValueError("%s: display must be a bool, got %r"
                         % (op, type(display).__name__))
    th = np.mod(np.arctan2(q[..., 2], q[..., 1]), np.pi)
    return th / np.pi if display else th


# --------------------------------------------------------------------------- #
# the radial (Riesz pyramid) bank                                              #
# --------------------------------------------------------------------------- #
_BANK_CACHE: dict = {}
_BANK_CACHE_MAX = 8


def _radial_bank(h: int, w: int, scales: int) -> dict:
    """Octave-wide radial sub-band filters that sum to **one**, exactly.

    ``A_s(r) = cos(pi/2 * (log2 r - c_s))`` on ``|log2 r - c_s| <= 1`` with
    ``c_s = -1-s``, exactly the radial half of ``motionmag._filter_bank`` — so
    the two decompositions cover the same frequencies and a comparison between
    them is about the *orientation* machinery and nothing else. The filters used
    here are the **squares** ``G_s = A_s^2``, because ``sum A_s^2 + L^2 + H^2``
    is identically 1 (that is what the raised cosine is for), which makes
    ``sum_s G_s = 1`` an *amplitude* partition of unity. Reconstruction is then
    plain addition of the sub-band images, exact to rounding, with no divisor
    correction and no tight-frame argument needed.

    There is no orientation index. That is the entire structural difference from
    a steerable bank: ``scales`` filters here against ``scales * orientations``
    there, with the orientation recovered per pixel from the Riesz pair instead
    of being selected by a filter."""
    key = (h, w, scales)
    hit = _BANK_CACHE.get(key)
    if hit is not None:
        return hit
    fv = np.fft.fftfreq(h)[:, None]
    fu = np.fft.fftfreq(w)[None, :]
    r = np.sqrt(fu * fu + fv * fv)
    nonzero = r > 0.0
    x = np.log2(np.where(nonzero, r, 1.0))
    filters, centres = [], []
    total = np.zeros((h, w))
    for s in range(scales):
        c = -1.0 - s
        u = x - c
        a = np.where((np.abs(u) <= 1.0) & nonzero, np.cos(0.5 * np.pi * u), 0.0)
        filters.append(a * a)
        centres.append(2.0 ** c)
        total += a * a
    resid = np.maximum(0.0, 1.0 - total)                 # already the squared form
    hi_mask = (x > -1.0) & nonzero
    hipass = np.where(hi_mask, resid, 0.0)
    lopass = resid - hipass
    inv = np.where(r > 0.0, 1.0 / np.where(r > 0.0, r, 1.0), 0.0)
    bank = {"bands": filters, "centre": centres,
            "lowpass": lopass, "highpass": hipass,
            "H1": -1j * fu * inv, "H2": -1j * fv * inv,
            "fu": fu, "fv": fv, "shape": (h, w), "scales": scales}
    total_all = np.sum(filters, axis=0) + lopass + hipass
    err = float(np.abs(total_all - 1.0).max())
    if err > 1e-12:
        raise ValueError("radial bank: the sub-band filters sum to 1 only to %g "
                         "for shape (%d, %d) with scales=%d — reconstruction "
                         "would lose energy silently, so the bank is refused"
                         % (err, h, w, scales))
    if len(_BANK_CACHE) >= _BANK_CACHE_MAX:
        _BANK_CACHE.clear()
    _BANK_CACHE[key] = bank
    return bank


def _band_monogenic(spec: np.ndarray, G: np.ndarray, bank: dict):
    """``(I, R1, R2)`` real ``(T, H, W)`` volumes for one radial band."""
    Fb = spec * G[None]
    return (np.real(np.fft.ifft2(Fb, axes=(1, 2))),
            np.real(np.fft.ifft2(Fb * bank["H1"][None], axes=(1, 2))),
            np.real(np.fft.ifft2(Fb * bank["H2"][None], axes=(1, 2))))


def _band_reference(I: np.ndarray, R1: np.ndarray, R2: np.ndarray):
    """Temporal-mean reference of one band: ``(nx, ny, zbar, z, live)``.

    The orientation ``n`` is taken **once**, from the temporal mean, and then
    held fixed while the frames are projected onto it. Taking it per frame
    instead is the obvious thing and it is wrong in a way that does not raise:
    the monogenic orientation is defined modulo ``pi``, so as a translating
    grating's local phase sweeps through zero the per-frame ``n`` flips sign and
    the "phase deviation" jumps by ``pi`` on a frame boundary with no warning.
    Projecting every frame onto one fixed direction keeps the analytic signal
    continuous and lets the phase go negative, which is what it is supposed to
    do."""
    Ibar = I.mean(axis=0)
    R1b = R1.mean(axis=0)
    R2b = R2.mean(axis=0)
    rmag = np.sqrt(R1b * R1b + R2b * R2b)
    safe = np.where(rmag > 0.0, rmag, 1.0)
    nx = np.where(rmag > 0.0, R1b / safe, 1.0)
    ny = np.where(rmag > 0.0, R2b / safe, 0.0)
    zbar = Ibar + 1j * rmag
    z = I + 1j * (R1 * nx[None] + R2 * ny[None])
    amp = np.abs(zbar)
    amp_max = float(amp.max())
    live = amp > _AMP_LIVE * amp_max if amp_max > 0.0 else np.zeros_like(amp, bool)
    return nx, ny, zbar, z, live, amp, amp_max, Ibar, R1b, R2b, rmag


def riesz_motion_magnify(video, alpha, f_lo, f_hi, fps, scales: int = 4) -> dict:
    """Scale a clip's in-band motion by *alpha*, by the Riesz route. → dict.

    The Riesz-pyramid magnifier of Wadhwa et al. (2014), and the direct
    counterpart of ``motionmag.motion_magnify``: same contract, same ``alpha``
    convention (a **displacement gain** — 1 is the identity, 2 doubles the
    motion, -1 reverses it), same honesty block, different decomposition.

    Each radial sub-band is turned into a monogenic signal, projected onto the
    band's temporal-mean orientation to give a complex analytic signal ``z``, and
    the temporal phase deviation ``angle(z * conj(z_mean))`` is band-passed and
    multiplied by ``alpha - 1``. The band is then re-rendered as
    ``I*cos(shift) - R_proj*sin(shift)`` — the real part of ``z * exp(i*shift)``
    — and the bands are summed. Because the radial filters are an *amplitude*
    partition of unity, that sum is the reconstruction: at ``alpha = 1`` the
    output equals the input to **5.55e-16** (measured on a 64x64x64 clip;
    ``motionmag.motion_magnify`` gives 7.77e-16 on the same clip).

    The gain really is the gain. Measuring the magnified clip's displacement with
    the *independent* steerable estimator ``motionmag.displacement_series``, on a
    single-grating clip of true amplitude 0.1 px:

    ========  ==========================  ==========================
    alpha     Riesz measured gain         steerable measured gain
    ========  ==========================  ==========================
    0.0        0.000000000000              0.000000000000
    2.0        2.000000000000              2.000000000000
    4.0        4.000000000000              4.000000000000
    -1.0      -1.000000000000             -1.000000000000
    20.0      20.000000000000             20.000000000000
    ========  ==========================  ==========================

    — twelve decimal places, for both, including the reversal.

    Returns the same shape of dict ``motionmag.motion_magnify`` returns —
    ``{"video", "alpha", "band_hz", "fps", "scales", "snr_in", "snr_out",
    "image_snr_change_db", "motion_snr_out_db", "motion_snr_change_db",
    "band_power_ratio", "phase_shift_max_rad", "phase_shift_rms_rad",
    "linear_regime", "reference_coherence"}`` — and it is the same dict because
    the SNR block is computed by **calling** ``motionmag.band_snr`` rather than
    re-deriving it. Two magnifiers that disagree about how to measure their own
    cost cannot be compared, so they share the measurement.

    **Magnification never improves the motion SNR**, here as there: scaling the
    in-band phase scales the in-band noise by the same factor. What degrades is
    the image SNR. Measured on the shared 64x64x64 / 32 fps / 0.2 px / 4 Hz
    synthetic under sigma = 0.01 noise, band 3-5 Hz, against
    ``motionmag.motion_magnify`` on the identical clip:

    ======  ==================  ==================  ==============  ==============
    alpha   image change (dB)   image change (dB)   band ratio      band ratio
            Riesz               steerable           Riesz           steerable
    ======  ==================  ==================  ==============  ==============
    2       -4.8611             -4.8260             0.937704        0.935433
    4       -10.3616            -10.3504            0.861162        0.858130
    8       -15.3515            -15.5097            0.629948        0.628597
    ======  ==================  ==================  ==============  ==============

    The two magnifiers cost essentially the same — within 0.16 dB and 0.3 % of
    band-power linearity at every gain. So the choice between them is **not**
    about magnification quality; it is about the displacement measurement (where
    the Riesz route has a 13 % failure mode on multi-orientation texture, see
    :func:`riesz_displacement`) and about cost (this one is 2.09x faster on the
    same clip: 0.1034 s against 0.2163 s, best of 7).

    **Raises** ``ValueError``: *video* is not a valid ``(T, H, W)`` clip or is
    over :data:`MAX_PYRAMID_ELEMENTS`; ``|alpha|`` is over :data:`MAX_ALPHA`;
    the pass-band is empty, reaches DC, or exceeds Nyquist; *scales* is outside
    ``[1, MAX_SCALES]``."""
    op = "riesz_motion_magnify"
    import motionmag

    vid = _require_video(video, "video", op, MAX_PYRAMID_ELEMENTS)
    t, h, w = vid.shape
    a = _finite_scalar(alpha, "alpha")
    if abs(a) > MAX_ALPHA:
        raise ValueError("%s: |alpha| = %g is over the %g cap (quatimage.MAX_ALPHA) "
                         "— at that gain the phase shift is far outside the linear "
                         "regime and the output is not a magnified measurement of "
                         "anything" % (op, abs(a), MAX_ALPHA))
    lo, hi, fs, mask = _require_band(f_lo, f_hi, fps, t, op)
    ns = _count(scales, "scales", 1, MAX_SCALES)
    bank = _radial_bank(h, w, ns)

    gain = a - 1.0
    spec = np.fft.fft2(vid, axes=(1, 2))
    out = np.zeros((t, h, w), np.float64)
    max_shift = 0.0
    w_shift2 = 0.0
    w_total = 0.0
    coh_num = 0.0
    coh_den = 0.0
    for G in bank["bands"]:
        I, R1, R2 = _band_monogenic(spec, G, bank)
        if gain == 0.0:
            out += I
            continue
        _nx, _ny, zbar, z, live, amp, amp_max, _Ib, _R1b, _R2b, _rm = \
            _band_reference(I, R1, R2)
        if amp_max <= _AMP_FLOOR * max(float(np.abs(vid).max()), 1.0):
            out += I                       # contrast-free band: nothing to shift
            continue
        dphi = np.angle(z * np.conj(zbar)[None])
        tspec = np.fft.fft(dphi, axis=0)
        tspec[~mask] = 0.0
        dphi = np.real(np.fft.ifft(tspec, axis=0))
        shift = gain * dphi * live[None]
        max_shift = max(max_shift, float(np.abs(shift).max()) if shift.size else 0.0)
        wgt = (amp * amp) * live
        w_shift2 += float((wgt[None] * shift * shift).sum())
        w_total += float(wgt.sum()) * t
        mabs = np.abs(z).mean(axis=0)
        ewgt = (mabs * mabs) * live
        coh_num += float((ewgt * amp).sum())
        coh_den += float((ewgt * mabs).sum())
        rproj = np.imag(z)
        out += I * np.cos(shift) - rproj * np.sin(shift)
    lp = np.real(np.fft.ifft2(spec * bank["lowpass"][None], axes=(1, 2)))
    hp = np.real(np.fft.ifft2(spec * bank["highpass"][None], axes=(1, 2)))
    out += lp + hp
    if not np.isfinite(out).all():
        raise ValueError("%s: the reconstruction produced non-finite samples — "
                         "this is a bug in the filter bank, not in the input "
                         "(the input was validated finite)" % (op,))

    rms_shift = float(np.sqrt(w_shift2 / w_total)) if w_total > 0.0 else 0.0
    coherence = float(coh_num / coh_den) if coh_den > 0.0 else 1.0
    snr_in = motionmag.band_snr(vid, lo, hi, fs)
    snr_out = motionmag.band_snr(out, lo, hi, fs)
    # band_snr estimates the in-band noise floor from the *out-of-band* bins,
    # which magnification does not touch — so reading motion_snr_db straight off
    # the magnified clip credits alpha^2 more in-band power against an unchanged
    # noise estimate and reports an improvement that did not happen. The noise
    # floor is a property of the recording, so the *input's* per-bin density is
    # the right reference, scaled by the gain the in-band content received. Same
    # correction, same dB window (motionmag.MIN_SNR_DB / MAX_SNR_DB) as there.
    noise_out = snr_in["noise_power_per_bin"] * snr_in["band_bins"] * a * a
    motion_out_db = _db(max(snr_out["band_power"] - noise_out, 0.0), noise_out)
    denom = snr_in["band_power"] * a * a
    band_ratio = (snr_out["band_power"] / denom) if denom > 0.0 else 1.0
    return {
        "video": out, "alpha": a, "band_hz": (lo, hi), "fps": fs, "scales": ns,
        "snr_in": snr_in, "snr_out": snr_out,
        "image_snr_change_db": snr_out["image_snr_db"] - snr_in["image_snr_db"],
        "motion_snr_out_db": motion_out_db,
        "motion_snr_change_db": motion_out_db - snr_in["motion_snr_db"],
        "band_power_ratio": float(band_ratio),
        "phase_shift_max_rad": max_shift,
        "phase_shift_rms_rad": rms_shift,
        "linear_regime": bool(rms_shift < np.pi),
        "reference_coherence": coherence,
    }


def riesz_displacement(video, f_lo, f_hi, fps, scales: int = 4) -> dict:
    """Sub-pixel displacement field from the monogenic phase. → dict.

    The measuring sibling of :func:`riesz_motion_magnify`, and the direct
    counterpart of ``motionmag.phase_displacement``: nothing is amplified, the
    displacement itself is returned in pixels.

    Per radial band, the temporal phase deviation obeys
    ``dphi = -(kx*dx + ky*dy)`` where ``(kx, ky)`` is the local wave vector —
    here ``k * n``, with the *direction* ``n`` read straight off the Riesz pair
    (continuous, per pixel) and the *magnitude* ``k`` from the spectral
    derivative ``Im(conj(z) d_n z)/|z|^2``. Each band gives one linear
    constraint on the same two unknowns and the bands are combined per pixel by
    weighted least squares with weights ``|z|^2``, solved by the closed-form 2x2
    pseudo-inverse so that a rank-1 pixel (the aperture problem) returns the
    component that *was* observed and exactly zero in the direction nothing
    constrained.

    Returns ``{"dx": (T, H, W), "dy": (T, H, W), "weight": (H, W),
    "valid": (H, W) bool, "rank": (H, W) int8, "fps", "band_hz", "frames",
    "wrap_limit_px", "reference_coherence"}`` — the same keys
    ``motionmag.phase_displacement`` returns, so the two are drop-in comparable.

    Head to head against the complex steerable route
    ------------------------------------------------
    All of the following is measured against ``motionmag.phase_displacement`` on
    identical clips (64x64x64, 32 fps, 4 Hz bin-centred, band 3-5 Hz), with the
    truth from an exact Fourier phase ramp and the error read as the deviation of
    the least-squares gain from 1. **The verdict is mixed and the losses are
    stated first.**

    *When the model holds — one moving component per band — the two are the same
    answer.* A single grating, translated:

    ============  ======================  ======================
    true d (px)   Riesz relative error    steerable rel. error
    ============  ======================  ======================
    0.001         1.463e-13               1.694e-13
    0.010         3.997e-15               6.217e-15
    0.100         3.331e-16               0.0
    0.500         3.331e-16               0.0
    1.000         0.0                     0.0
    2.000         0.0                     2.220e-16
    3.000         0.0                     0.0
    3.050         2.220e-16               2.220e-16
    3.060         1.332e-15               0.0
    3.070         1.573e+00  <- broken    1.573e+00  <- broken
    4.000         1.207e+00  <- broken    1.207e+00  <- broken
    ============  ======================  ======================

    Both are exact to rounding, and **both break in the same place, between 3.06
    and 3.07 px** — which is the closed-form ``J0`` zero, not an empirical
    tolerance: the temporal-mean phase reference equals ``c * J0(k*A)``, whose
    first zero at ``k*A = 2.4048`` is ``A = 2.4048/(2*pi/8) = 3.0619`` px for an
    8 px grating. The Riesz route does **not** lift that ceiling, because the
    ceiling belongs to the temporal-mean reference and not to the decomposition.

    *Where the Riesz route loses, and it loses badly.* A radial band has no
    orientation index, so two components at the same scale but different
    orientations land in **one** band and the single-plane-wave model behind the
    monogenic signal is simply false there. A steerable bank separates them by
    filter. On ``motionmag.synthesize_translation``, whose default is exactly
    that situation:

    ==================================  ==================  ==================
    clip                                Riesz rel. error    steerable rel. err
    ==================================  ==================  ==================
    lambda = (8, 16) px  [the default]  1.299e-01           4.441e-16
    lambda = (8, 32) px  [2 octaves]    2.220e-16           0.0
    lambda = (8, 8)  px  [same band]    6.256e-01           1.329e-02
    ==================================  ==================  ==================

    A **13 % displacement error that does not shrink as the displacement shrinks,
    with no exception and no NaN** — and 63 % when the two gratings share a
    wavelength outright. Separate the components by two octaves and the error
    returns to machine precision, which identifies the cause exactly. Any scene
    with texture at several orientations in one octave — that is, most real
    scenes — is in the bad case. This is the single most important limitation of
    the Riesz route and no amount of tuning removes it.

    *A second loss: it cannot measure everywhere.* The wave vector comes from the
    Riesz pair, which **vanishes at every even-symmetric point** (local phase 0
    or pi — the crest of a bright or dark line) even though the amplitude there
    is at full strength. Measured on the single-grating clip, 1024 of 4096 pixels
    (25.0 %) come back rank 0 against 0 of 4096 for the steerable route, whose
    orientation comes from the filter and never degenerates. The affected pixels
    are marked in ``rank`` and weighted zero, so they do not corrupt the answer —
    but they are holes in the field.

    *The theoretical win does not materialise.* Continuous per-pixel orientation
    should beat a 4-orientation bank on oblique structure. Measured, it does not
    — the raised-cosine angular windows already interpolate exactly:

    ===============  ==================  ==================
    grating (deg)    Riesz rel. error    steerable rel. err
    ===============  ==================  ==================
    0.0              3.331e-16           0.0
    20.6             4.441e-16           4.441e-16
    45.0             4.441e-16           4.441e-16
    69.4             4.441e-16           4.441e-16
    90.0             3.331e-16           0.0
    ===============  ==================  ==================

    *Two wins that are real.* Under noise the Riesz estimate is consistently
    about twice as accurate, because it spends its degrees of freedom on 4 bands
    instead of 19 and admits fewer noise-only sub-bands to the normal equations
    (single grating, A = 0.5 px):

    ==========  ==================  ==================
    sigma       Riesz rel. error    steerable rel. err
    ==========  ==================  ==================
    0.001       1.812e-05           2.329e-05
    0.010       3.008e-04           5.119e-04
    0.050       4.047e-03           8.670e-03
    ==========  ==================  ==================

    And it is cheaper: it builds ``scales`` = 4 sub-bands where the steerable
    bank builds ``scales * orientations + 3`` = 19. Measured wall clock on the
    64x64x64 clip, best of 7: **0.0888 s against 0.1063 s (1.20x)** here, and
    **0.1034 s against 0.2163 s (2.09x)** for the magnifiers — less than the
    19:4 filter ratio suggests, because each Riesz band costs three inverse FFTs
    (band, R1, R2) where a steerable band costs one.

    **Summary, honestly.** Use the steerable route when the scene has structure
    at several orientations per octave, which is the common case; use this one
    when the scene is narrow-band, when the clip is noisy, or when the 2x is
    worth having. The quaternion is the right *object* for the monogenic signal
    and gives orientation for free; it does not make the measurement better.

    **Raises** ``ValueError``: *video* is not a valid clip or is over
    :data:`MAX_PYRAMID_ELEMENTS`; the pass-band is empty, reaches DC or exceeds
    Nyquist; *scales* is outside ``[1, MAX_SCALES]``."""
    op = "riesz_displacement"
    vid = _require_video(video, "video", op, MAX_PYRAMID_ELEMENTS)
    t, h, w = vid.shape
    lo, hi, fs, mask = _require_band(f_lo, f_hi, fps, t, op)
    ns = _count(scales, "scales", 1, MAX_SCALES)
    bank = _radial_bank(h, w, ns)
    fu, fv = bank["fu"], bank["fv"]
    scale = float(np.abs(vid).max())

    spec = np.fft.fft2(vid, axes=(1, 2))
    a00 = np.zeros((h, w))
    a01 = np.zeros((h, w))
    a11 = np.zeros((h, w))
    b0 = np.zeros((t, h, w))
    b1 = np.zeros((t, h, w))
    weight = np.zeros((h, w))
    kmax = 0.0
    coh_num = 0.0
    coh_den = 0.0
    for G in bank["bands"]:
        I, R1, R2 = _band_monogenic(spec, G, bank)
        nx, ny, zbar, z, live, amp, amp_max, Ibar, R1b, R2b, rmag = \
            _band_reference(I, R1, R2)
        if amp_max <= _AMP_FLOOR * max(scale, 1.0):
            continue                       # contrast-free band votes zero anyway
        # Local wave vector, from the closed-form monogenic identity rather than
        # from the phase gradient. For a local plane wave A*cos(psi) the band and
        # its Riesz pair satisfy  d/dx I = -|k| * R1  and  d/dy I = -|k| * R2
        # *exactly* — both sides flip together when the orientation flips, so the
        # estimate is immune to the modulo-pi ambiguity. Taking Im(conj z dz)/|z|^2
        # instead (the steerable route's formula) is **wrong here** and was
        # measured to be: the monogenic reference has Im >= 0 by construction, so
        # its phase is folded into [0, pi] and the derivative of a folded phase
        # is the wrong sign on half the image. That produced a *constant* 23.42 %
        # displacement bias — no exception, no NaN, and no dependence on the
        # displacement, which is exactly the kind of error that survives review.
        rmag2 = rmag * rmag
        gate = live & (rmag2 > (_AMP_LIVE * amp_max) ** 2)
        ispec = np.fft.fft2(Ibar)
        Ix = np.real(np.fft.ifft2(ispec * (2j * np.pi * fu)))
        Iy = np.real(np.fft.ifft2(ispec * (2j * np.pi * fv)))
        den = np.where(gate, rmag2, 1.0)
        kmagn = np.where(gate, -(Ix * R1b + Iy * R2b) / den, 0.0)
        kx, ky = kmagn * nx, kmagn * ny
        dphi = np.angle(z * np.conj(zbar)[None])
        tspec = np.fft.fft(dphi, axis=0)
        tspec[~mask] = 0.0
        dphi = np.real(np.fft.ifft(tspec, axis=0))

        # Weight by |R|^2, not by the amplitude: the *constraint* is only as good
        # as the wave vector, and the wave vector is what dies where the Riesz
        # vector does (at an even-symmetric point, local phase 0 or pi, the
        # amplitude is at full strength but the orientation is undefined). See
        # the honest-limitation paragraph in this function's docstring.
        wgt = np.where(gate, rmag2, 0.0)
        a00 += wgt * kx * kx
        a01 += wgt * kx * ky
        a11 += wgt * ky * ky
        b0 -= (wgt * kx)[None] * dphi
        b1 -= (wgt * ky)[None] * dphi
        weight += wgt
        mabs = np.abs(z).mean(axis=0)
        ewgt = np.where(live, mabs * mabs, 0.0)
        coh_num += float((ewgt * amp).sum())
        coh_den += float((ewgt * mabs).sum())
        kmax = max(kmax, float(np.abs(kmagn).max()))

    # Minimum-norm least squares via the closed-form 2x2 symmetric eigenvalues —
    # the same guard motionmag uses and for the same reason: where every
    # contributing band shares an orientation the normal equations are rank 1
    # (the aperture problem), a plain inverse returns a huge number in the
    # unobservable direction, and refusing the pixel throws away the component
    # that *was* measured.
    half = 0.5 * (a00 + a11)
    disc = np.sqrt(np.maximum(0.25 * (a00 - a11) ** 2 + a01 * a01, 0.0))
    lam1 = half + disc
    lam2 = half - disc
    peak = float(lam1.max()) if lam1.size else 0.0
    alive = lam1 > 1e-12 * max(peak, np.finfo(float).tiny)
    rank2 = alive & (lam2 > 1e-8 * np.where(alive, lam1, 1.0))
    vx = a01
    vy = lam1 - a00
    norm = np.sqrt(vx * vx + vy * vy)
    degenerate = norm <= 0.0
    vx = np.where(degenerate, 1.0, vx / np.where(degenerate, 1.0, norm))
    vy = np.where(degenerate, 0.0, vy / np.where(degenerate, 1.0, norm))
    s_lam1 = np.where(alive, lam1, 1.0)
    det = a00 * a11 - a01 * a01
    s_det = np.where(rank2, det, 1.0)
    dx_full = (a11[None] * b0 - a01[None] * b1) / s_det[None]
    dy_full = (a00[None] * b1 - a01[None] * b0) / s_det[None]
    proj = (vx[None] * b0 + vy[None] * b1) / s_lam1[None]
    dx = np.where(rank2[None], dx_full, np.where(alive[None], proj * vx[None], 0.0))
    dy = np.where(rank2[None], dy_full, np.where(alive[None], proj * vy[None], 0.0))
    if not (np.isfinite(dx).all() and np.isfinite(dy).all()):
        raise ValueError("%s: the least-squares solve produced non-finite "
                         "displacements — this is a bug in the rank guard, not in "
                         "the input" % (op,))
    rank = np.where(rank2, 2, np.where(alive, 1, 0)).astype(np.int8)
    return {"dx": dx, "dy": dy, "weight": weight, "valid": alive, "rank": rank,
            "fps": fs, "band_hz": (lo, hi), "frames": t,
            "wrap_limit_px": (np.pi / kmax) if kmax > 0.0 else 0.0,
            "reference_coherence": float(coh_num / coh_den) if coh_den > 0.0 else 1.0}


def riesz_displacement_series(video, f_lo, f_hi, fps, scales: int = 4) -> np.ndarray:
    """Whole-frame displacement waveform from the monogenic phase. → (T, 2).

    The contrast-weighted spatial mean of :func:`riesz_displacement`: the
    rigid-body motion of the scene in pixels, one ``(dx, dy)`` row per frame.
    The ``(n, 2)`` layout is the shared 1-D convention (``dsp.spectrum``,
    ``funct1d``, ``opsoptics``'s MTF curves), so the trace can be handed to
    ``dsp.spectrum`` to read off a resonant frequency without any repacking.

    Weights are the ``|z|^2`` contrast the field solve uses, restricted to the
    pixels marked ``valid``, so blank regions do not drag the average towards
    zero. A clip with no valid pixel anywhere (a constant image) returns exact
    zeros rather than dividing by zero.

    Accuracy, the ``J0`` cliff and the multi-orientation failure all inherit from
    :func:`riesz_displacement` — read its head-to-head table before trusting a
    number from here. On a single-grating 64x64x64 / 8 px / 4 Hz clip a true
    0.5 px amplitude is recovered as **0.50000000000000 px** (2.2e-16 relative);
    on the two-grating ``motionmag.synthesize_translation`` default the same
    0.5 px comes back 13.0 % low, with nothing to signal it."""
    field = riesz_displacement(video, f_lo, f_hi, fps, scales)
    wgt = field["weight"] * field["valid"]
    total = float(wgt.sum())
    t = field["dx"].shape[0]
    if total <= 0.0:
        return np.zeros((t, 2), np.float64)
    dx = (field["dx"] * wgt[None]).sum(axis=(1, 2)) / total
    dy = (field["dy"] * wgt[None]).sum(axis=(1, 2)) / total
    return np.stack([dx, dy], axis=1)

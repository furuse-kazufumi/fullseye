# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Parallel-beam tomography — projections in, slice out (numpy + scipy only).

The half of computed tomography that Fullseye did not have. There are many
operators here for *handling* a CT volume — windowing, labelling, boundary
extraction, marching cubes, region properties — and, before this module, none at
all for **making one from projections**: no Radon transform, no sinogram, no
filtered back-projection, no algebraic reconstruction. (``backproject`` is a
different thing that shares a word: it lifts pixels into 3-D with a depth map and
a camera model. That is projective geometry; this is an integral transform.)

The one convention, stated once and never negotiated again::

    sinogram[i, j]   row i = projection ANGLE,  column j = DETECTOR bin
    ray (i, j)       the line  x cos(theta_i) + y sin(theta_i) = j - (n_det-1)/2
    x = col - (W-1)/2,  y = row - (H-1)/2      (so +y runs DOWN the array)

Six families of operator:

  * **layout** — :func:`projection_angles` / :func:`sinogram_design`: the scan
    before the scanner. Which angles, and what the geometry has already decided
    about what can be resolved. The counterpart of :func:`visiondesign` for the
    axial problem, and of :func:`interferometry.csi_design`.
  * **forward** — :func:`ellipse_phantom` / :func:`ellipse_sinogram` /
    :func:`radon_transform`: a known object, its **closed-form** Radon transform,
    and the discrete projector. Two forward models rather than one, because the
    closed form is what the discrete one is *tested against*.
  * **reconstruct** — :func:`backproject_sinogram` /
    :func:`filtered_backprojection` / :func:`sart_reconstruct`: the blurred
    baseline, the standard inversion, and the iterative solver that beats it when
    the data runs out.
  * **artefacts** — :func:`beam_hardening_apply` / :func:`beam_hardening_correct`,
    :func:`ring_artifact_apply` / :func:`ring_artifact_remove`,
    :func:`metal_trace_interpolate`. Always the forward model *and* the
    correction, so that every claim about a correction is checkable against an
    artefact whose true size is known.
  * **geometry** — :func:`sinogram_center_of_rotation` /
    :func:`sinogram_center_shift`: where the axis actually is, and how to move it.
  * **volume** — :func:`radon_volume` / :func:`fbp_volume`: the same thing slice
    by slice, so that the output is an ordinary volume and every existing 3-D
    operator applies to it unchanged.

Ground truth is closed-form, not golden files. The Radon transform of a uniform
ellipse is elementary — for a disc it is the chord length ``2 sqrt(r^2 - s^2)`` —
and densities add, so the Shepp-Logan phantom has an **exact** sinogram. Every
accuracy claim below is the discrete code measured against that, and every table
is reproduced by ``tests/test_tomography.py``.

The projector against the closed form (disc of radius 60 px in a 256-px grid,
180 views, as a fraction of the peak line integral):

    interior RMS   0.073 %      (the part where the phantom is smooth)
    whole sinogram 0.402 %      (the difference is the partial-volume edge)
    hard-edged phantom, interior RMS 0.276 %  -> anti-aliasing is worth 3.8x

**Three break tables**, because "it works" is not a measurement.

**1. How few views before it falls apart** (Shepp-Logan, analytic sinogram,
normalised RMS error against the truth):

    views    FBP ramp   FBP hann   SART x10   |  noisy: FBP ramp / hann / SART
      180     0.0250     0.0358     0.0175    |   0.0360 / 0.0371 / 0.0291
       90     0.0454        -       0.0195    |        -
       45     0.1039     0.0740     0.0353    |   0.1159 / 0.0766 / 0.0385
       32     0.1362        -       0.0497    |        -
       16     0.2341        -       0.0859    |   0.2481 / 0.1921 / 0.0864
        8     0.3635     0.3063     0.1257    |   0.3813 / 0.3093 / 0.1259

FBP degrades **14.5x** from 180 to 8 views; SART **7.2x**. There is no threshold
where FBP "breaks" — it degrades smoothly — and, contrary to the usual story,
there is **no crossing point either**: SART leads at every count tested, from
1.43x at 180 views to 2.9x at 8. What the view count changes is the price. At 180
views SART costs 312x the wall clock (37.7 s against 0.12 s, 256 px) for that
1.43x; at 8 views the 2.9x is nearly free. Under noise the apodisation windows
earn their keep at the sparse end and lose at the dense end, which is the same
statement in a different currency.

**2. What half a pixel of centre-of-rotation error costs** (180 views):

    shift    estimated by this module   FBP nRMS   after correction
    0.00 px         +0.0029 px           0.0250        0.0249
    0.50 px         +0.5029 px           0.0537        0.0358
    1.00 px         +1.0029 px           0.1016        0.0249
    2.00 px         +2.0029 px           0.1630        0.0249

Half a pixel doubles the error while still looking like a slightly soft picture.
Two pixels is a 6.5x error and an obvious double image. The estimator's bias is a
constant 0.0029 px, and note the half-pixel row: an integer miscentring is fully
repairable, a fractional one is not, because undoing it means resampling.

**3. Which structures a limited-angle scan loses.** By the central-slice theorem
a projection at ``theta`` fills the line through the origin at ``theta`` in the
2-D Fourier plane, so a scan over ``[0, span)`` leaves a *wedge* empty and the
structures that vanish are exactly those whose edges face into it. Fourier energy
retained, per 30-degree sector, against the truth:

    span      0-30   30-60   60-90   90-120  120-150  150-180   nRMS
    180 deg   0.97    0.95    0.94    0.94    0.95     0.97     0.0250
    120 deg   0.93    0.94    0.95    0.91    0.08     0.12     0.1302
     90 deg   0.93    0.94    0.96    0.17    0.07     0.13     0.1591
     60 deg   0.93    0.92    0.10    0.07    0.05     0.12     0.1811

The measured sectors go to 5-17 % **exactly** where the views stop, and the
covered ones stay above 0.90 — the loss is not a general blur, it is specific
directions being deleted. A limited-angle reconstruction is sharp in the
directions it kept, which is precisely why it is convincing and dangerous.

Fail-closed, like every Fullseye module. Zero projections, a non-finite value, a
detector too narrow to cover the phantom's diagonal, a sinogram whose row count
disagrees with the angle list, a relaxation past the divergence bound, an even
smoothing window, a metal mask that eats an entire view, a rotation-centre shift
that pushes the object off the detector, an angular span too narrow for the
centre-of-rotation fit to be identifiable — all raise a ``ValueError`` that names
the problem. The size caps are read off the **requested output** and not the
input, because in this module the small argument is the dangerous one: a 64x64
image with ``n_angles=100000`` is a 25 MB input asking for a 3 GB sinogram, and
``ellipse_phantom(size=10000, supersample=16)`` is two small ints asking for a
25 G-element intermediate.

Honest disclosure — what this cannot do, measured rather than assumed:

  * **Parallel beam only.** Real medical and industrial scanners are fan or cone
    beam, where the slices are *not* independent and an FDK-style weighting is
    required. Saying so costs less than a wrong ``fdk``.
  * **The obvious way to find a metal trace is worse than doing nothing.**
    Thresholding the sinogram — the first thing anyone tries — scores 1.3-1.4x
    *worse* than no correction at every implant density tested, because it flags
    the densest legitimate structure. Thresholding the reconstruction and
    forward-projecting that mask recovers essentially all of the damage
    (0.5214 -> 0.0257 at the highest density, against a clean 0.0250). The
    shortcut is not offered, and the numbers are in
    :func:`metal_trace_interpolate`.
  * **Ring removal is a compromise with a measured price.** The default window
    undoes 72 % of a 2 % detector gain error and costs +0.0002 nRMS on a sinogram
    that had no rings; wider windows undo barely more and cost up to 50x that.
    And a gain error only matters relative to the line integrals: the identical
    2 % error on the same phantom in raw pixel units (peak 70.9 rather than 1.18)
    moves the reconstruction by 2.1e-05 and there is nothing to remove.
  * **Beam-hardening correction by model inverse is a simulation tool.** It is
    exact (round trip 8.0e-09 relative) because it is handed the same ``w`` and
    ``k`` that did the hardening — which on real data nobody has. The polynomial
    route is the one that applies to real data, and it is only as good as the
    assumption that everything in the field of view attenuates like water.
  * **An un-filtered back-projection has no absolute scale at all.** Its raw
    values run 0.768-2.493 where the truth runs 0-0.0167. Auto-windowed for
    display it looks approximately right; the numbers underneath are off by a
    factor of 100.
  * **Nothing here detects a transposed sinogram**, and no structural check can:
    the transpose is a valid sinogram of a different scan. Measured, FBP on a
    square sinogram and on its transpose both return finite, plausible pictures
    that differ by 0.175 nRMS, and neither raises. That is why ``sinogram`` is
    its own sort in :mod:`opstomography` rather than riding on ``image2d``.

Provenance — textbook and cited public literature only (see
``docs/PROVENANCE.md``):

  * J. Radon, "Uber die Bestimmung von Funktionen durch ihre Integralwerte langs
    gewisser Mannigfaltigkeiten", *Berichte Sachsische Akademie der
    Wissenschaften* 69:262-277, 1917 — the transform and its inversion.
  * A. C. Kak & M. Slaney, *Principles of Computerized Tomographic Imaging*,
    IEEE Press 1988 (and SIAM 2001) — the filtered back-projection algorithm,
    the ramp/Shepp-Logan/Hamming filters, the view-count sampling rule of
    Section 3.5, and the beam-hardening and ring artefact mechanisms.
  * L. A. Shepp & B. F. Logan, "The Fourier reconstruction of a head section",
    *IEEE Transactions on Nuclear Science* NS-21(3):21-43, 1974 — the phantom and
    the apodised ramp.
  * A. H. Andersen & A. C. Kak, "Simultaneous algebraic reconstruction technique
    (SART): a superior implementation of the ART algorithm", *Ultrasonic Imaging*
    6(1):81-94, 1984 — the row-action update and its normalisers.
  * W. A. Kalender, R. Hebel & J. Ebersberger, "Reduction of CT artifacts caused
    by metallic implants", *Radiology* 164(2):576-577, 1987 — LI-MAR.
  * T. Donath, F. Beckmann & A. Schreyer, "Automated determination of the center
    of rotation in tomography data", *JOSA A* 23(5):1048-1057, 2006 — the
    centre-of-mass identity used here.
  * S. Winkelmann et al., "An optimal radial profile order based on the golden
    ratio for time-resolved MRI", *IEEE Trans. Med. Imaging* 26(1):68-76, 2007 —
    the golden-angle sequence.

Deliberately **not** here (owned elsewhere — composed with, never re-implemented):

  * **Everything downstream of the reconstruction** is the existing 3-D library:
    ``vol_window_level``, ``vol_label``, ``vol_region_props``, ``marching_cubes``,
    ``vol_boundary_points``, ``voxelize``. :func:`fbp_volume` returns a plain
    volume for exactly that reason, and
    ``examples/tomography_reconstruct.py`` runs the whole chain to a measured
    volume in mm^3.
  * **Generic 1-D filtering and FFTs** are :mod:`dsp` and :mod:`filters_freq`; the
    ramp filter here is not a general-purpose filter and is not exported as one.
  * **The evolutionary registry's ``tm_`` cluster** (``backends_tomo``) is a
    different thing with a similar name: those are ``fn(v, a, b)`` image-to-image
    ops for the genetic pipeline search, they fit their output back to the input
    shape, they are fail-*soft* by contract, and they use scikit-image when it is
    present. This module is the typed, fail-closed, dependency-light library that
    the ``fullseye`` facade exposes, and it shares no code with them.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "projection_angles", "ellipse_phantom", "ellipse_sinogram",
    "radon_transform", "sinogram_design",
    "backproject_sinogram", "filtered_backprojection", "sart_reconstruct",
    "beam_hardening_apply", "beam_hardening_correct",
    "ring_artifact_apply", "ring_artifact_remove", "metal_trace_interpolate",
    "sinogram_center_of_rotation", "sinogram_center_shift",
    "radon_volume", "fbp_volume",
    "TOMOGRAPHY", "FILTERS", "ANGLE_SCHEMES", "SHEPP_LOGAN",
    "MAX_IMAGE_ELEMENTS", "MAX_SINOGRAM_ELEMENTS", "MAX_ANGLES",
    "MAX_DETECTORS", "MAX_STACK_ELEMENTS", "VIEWS_PER_DETECTOR",
]

#: The public operators, by name (introspection / facade wiring).
TOMOGRAPHY = [
    "projection_angles", "ellipse_phantom", "ellipse_sinogram",
    "radon_transform", "sinogram_design",
    "backproject_sinogram", "filtered_backprojection", "sart_reconstruct",
    "beam_hardening_apply", "beam_hardening_correct",
    "ring_artifact_apply", "ring_artifact_remove", "metal_trace_interpolate",
    "sinogram_center_of_rotation", "sinogram_center_shift",
    "radon_volume", "fbp_volume",
]

#: Reconstruction filters accepted by :func:`filtered_backprojection` and
#: :func:`fbp_volume`. ``"none"`` is the un-filtered back-projection and exists so
#: the same operator can produce the blurred baseline the ramp filter fixes.
FILTERS = ("ramp", "shepp-logan", "cosine", "hann", "hamming", "none")

#: Angle-sequence schemes accepted by :func:`projection_angles`.
ANGLE_SCHEMES = ("uniform", "golden", "bit-reversed")

#: The Nyquist-like rule of thumb relating the number of views to the number of
#: detector samples for a parallel-beam scan: ``n_angles >= (pi/2) * n_detectors``
#: covers the disc of radius ``n_detectors/2`` with an angular sample spacing no
#: coarser than the detector pitch at its rim (Kak & Slaney 1988, Section 3.5).
#: :func:`sinogram_design` reports the ratio; it is a *design* number, not a hard
#: refusal, because sparse-view CT is exactly the business of violating it on
#: purpose and paying for it with a reconstruction algorithm.
VIEWS_PER_DETECTOR = 0.5 * np.pi

#: Largest number of pixels in a slice image (2^24 = 128 MB as float64).
MAX_IMAGE_ELEMENTS = 1 << 24

#: Largest number of elements in one ``(n_angles, n_detectors)`` sinogram.
MAX_SINOGRAM_ELEMENTS = 1 << 24

#: Largest number of elements in a ``(n_slices, n_angles, n_detectors)`` stack.
#: Lower than the 2-D caps in element count terms would suggest, because the
#: volume route holds the stack, the volume and several temporaries at once.
MAX_STACK_ELEMENTS = 1 << 25

#: Largest number of projection angles in one scan.
MAX_ANGLES = 1 << 16

#: Largest number of detector bins in one projection.
MAX_DETECTORS = 1 << 16

#: The modified Shepp-Logan head phantom, as ``(x0, y0, a, b, phi_deg, rho)``
#: rows in the normalised square ``[-1, 1]^2``: centre, semi-axes, the
#: counter-clockwise rotation of the ellipse, and the density that is *added*
#: where the ellipse covers (so the interior ones cut holes in the skull).
#:
#: The densities are the **modified** contrast set (Jain 1989, Table 10.2 /
#: Toft 1996) rather than Shepp & Logan's original 2.0/-0.98 skull pair: the
#: original's soft tissue spans 0.01 out of 1.0 total, which displays as a flat
#: grey and hides exactly the low-contrast detail a reconstruction test is
#: supposed to expose. Both sets are the same geometry.
#:
#: Source: L. A. Shepp & B. F. Logan, "The Fourier reconstruction of a head
#: section", *IEEE Transactions on Nuclear Science* NS-21(3):21-43, 1974.
SHEPP_LOGAN = (
    (0.0000,  0.0000, 0.6900, 0.9200,   0.0,  1.00),   # skull
    (0.0000, -0.0184, 0.6624, 0.8740,   0.0, -0.80),   # brain cavity
    (0.2200,  0.0000, 0.1100, 0.3100, -18.0, -0.20),   # right ventricle
    (-0.2200, 0.0000, 0.1600, 0.4100,  18.0, -0.20),   # left ventricle
    (0.0000,  0.3500, 0.2100, 0.2500,   0.0,  0.10),
    (0.0000,  0.1000, 0.0460, 0.0460,   0.0,  0.10),
    (0.0000, -0.1000, 0.0460, 0.0460,   0.0,  0.10),
    (-0.0800, -0.6050, 0.0460, 0.0230,  0.0,  0.10),
    (0.0000, -0.6060, 0.0230, 0.0230,   0.0,  0.10),
    (0.0600, -0.6050, 0.0230, 0.0460,  0.0,  0.10),
)

#: Golden-ratio angular increment in degrees, ``180 / phi`` with
#: ``phi = (1+sqrt5)/2``. Consecutive views land in the largest remaining gap, so
#: **any prefix** of the sequence is near-uniform — which is what makes a scan
#: interruptible without ruining it. Source: S. Winkelmann et al., "An optimal
#: radial profile order based on the golden ratio for time-resolved MRI",
#: *IEEE Trans. Med. Imaging* 26(1):68-76, 2007.
GOLDEN_ANGLE_DEG = 180.0 / ((1.0 + np.sqrt(5.0)) / 2.0)


# --------------------------------------------------------------------------- #
# fail-closed input helpers (same discipline as interferometry / photoncount)  #
# --------------------------------------------------------------------------- #
def _finite_scalar(v, name: str) -> float:
    """A real, finite Python float — or ``ValueError`` naming the problem."""
    if np.ma.is_masked(v):
        raise ValueError("%s is a masked value — fill or drop it explicitly" % (name,))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s is complex — an angle / length / attenuation is a real "
                         "quantity; coercion would silently drop the imaginary part"
                         % (name,))
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s is a bool — refusing the silent True==1 promotion "
                         "(True degrees is not an angle)" % (name,))
    if isinstance(v, (str, bytes, np.str_, np.bytes_)):
        raise ValueError("%s is a string (%r) — float('180') would silently succeed "
                         "and hide an unparsed configuration value" % (name, v))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real scalar, got %r"
                         % (name, type(v).__name__)) from None
    if not np.isfinite(f):
        raise ValueError("%s must be finite, got %r (NaN/Inf would propagate through "
                         "every ray of every projection)" % (name, v))
    return f


def _positive(v, name: str) -> float:
    f = _finite_scalar(v, name)
    if f <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, f))
    return f


def _nonneg(v, name: str) -> float:
    f = _finite_scalar(v, name)
    if f < 0.0:
        raise ValueError("%s must be >= 0, got %g" % (name, f))
    return f


def _count(v, name: str, lo: int, hi: int) -> int:
    """An int in ``[lo, hi]``. Floats are refused, not rounded.

    A fractional number of views or detector bins is an input mistake — usually a
    division that was meant to be integer — and rounding it hides the mistake in
    a geometry that then silently disagrees with the caller's own arithmetic.
    """
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be an int, got %r (a fractional number of views / "
                         "detector bins is an input mistake, not something to round)"
                         % (name, type(v).__name__))
    n = int(v)
    if n < lo or n > hi:
        raise ValueError("%s must be in [%d, %d], got %d (the cap is there so a "
                         "mistyped exponent fails instead of allocating gigabytes)"
                         % (name, lo, hi, n))
    return n


def _seed(v, name: str = "seed") -> int:
    """A non-negative integer seed. There is no ``None`` — determinism is a rule
    here (the chain fuzzer rejects non-deterministic ops)."""
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be a non-negative int (determinism is a contract "
                         "in this module — there is no seed=None), got %r"
                         % (name, type(v).__name__))
    n = int(v)
    if n < 0:
        raise ValueError("%s must be >= 0, got %d" % (name, n))
    return n


def _size_of(a) -> int:
    """Element count of *a* **without** promoting it to float64 first.

    The order matters: checking a cap *after* ``np.ascontiguousarray(a, float64)``
    does not prevent the allocation the cap exists to prevent — promoting a
    2^25-element uint8 array has already claimed 256 MB by the time the cap is
    consulted. Same helper, same reason, as :func:`interferometry._size_of`.
    """
    shp = getattr(a, "shape", None)
    if shp is None:
        shp = np.shape(a)
    n = 1
    for d in shp:
        n *= int(d)
    return n if shp else 1


def _as_float_array(a, name: str, cap: int, op: str) -> np.ndarray:
    """Coerce to float64 — after the size cap, and refusing the silent-truncation
    traps (masked arrays, complex, string/object/bool dtypes, non-finite)."""
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked (invalid) entries — "
                         "coercion would strip the mask and project the raw values "
                         "underneath; fill or drop them explicitly" % (op, name))
    if isinstance(a, (str, bytes)):
        raise ValueError("%s: %s is a string — a projection is an array of numbers"
                         % (op, name))
    n = _size_of(a)
    if n > cap:
        raise ValueError(
            "%s: %s has %d elements (shape %r), over the %d cap — refusing "
            "**before** the float64 promotion, because promoting first would "
            "already have allocated ~%d MB to discover the same thing"
            % (op, name, n, tuple(np.shape(a)), cap, n * 8 // (1 << 20)))
    if np.iscomplexobj(a):
        raise ValueError("%s: %s is complex — coercion to float64 would silently "
                         "discard the imaginary part; a line integral is a real "
                         "measured quantity, take .real explicitly if that is what "
                         "you mean" % (op, name))
    kind = getattr(getattr(a, "dtype", None), "kind", None)
    if kind is None and not isinstance(a, (int, float, np.number)):
        kind = np.asarray(a).dtype.kind if not isinstance(a, np.ndarray) else None
    if kind in ("U", "S", "O", "V", "b"):
        raise ValueError(
            "%s: %s has dtype '%s' — numpy would happily parse it into float64 "
            "(np.asarray(['1.0'], dtype=float) succeeds, and so does an object "
            "array of Decimals or a bool array of True/False), which is exactly how "
            "an unparsed configuration value or a mis-wired mask becomes a "
            "measurement. Convert it yourself and state what you meant."
            % (op, name, np.dtype(kind if kind != "b" else "bool").name
               if kind != "V" else "void"))
    arr = np.ascontiguousarray(a, dtype=np.float64)
    if not np.isfinite(arr).all():
        bad = int((~np.isfinite(arr)).sum())
        raise ValueError("%s: %s has %d non-finite value(s) (NaN/Inf) — refusing "
                         "(one NaN detector bin smears across the whole slice "
                         "through the back-projection)" % (op, name, bad))
    return arr


def _as_image(a, op: str, name: str = "image") -> np.ndarray:
    arr = _as_float_array(a, name, MAX_IMAGE_ELEMENTS, op)
    if arr.ndim != 2:
        raise ValueError("%s: %s must be 2-D (a slice), got ndim=%d shape %r"
                         % (op, name, arr.ndim, arr.shape))
    if arr.shape[0] < 2 or arr.shape[1] < 2:
        raise ValueError("%s: %s must be at least 2x2, got %r"
                         % (op, name, arr.shape))
    return arr


def _as_sinogram(a, op: str, name: str = "sinogram") -> np.ndarray:
    """A ``(n_angles, n_detectors)`` float64 sinogram, rows = projection angles.

    The axis order is checked structurally (2-D, both axes >= 2) and *cannot* be
    checked semantically — a transposed sinogram is a perfectly valid sinogram of
    a different scan. That is the whole reason ``sinogram`` is its own sort in the
    ledger rather than riding on ``image2d``; see ``opstomography``.
    """
    arr = _as_float_array(a, name, MAX_SINOGRAM_ELEMENTS, op)
    if arr.ndim != 2:
        raise ValueError(
            "%s: %s must be 2-D with rows = projection angles and columns = "
            "detector bins, got ndim=%d shape %r" % (op, name, arr.ndim, arr.shape))
    if arr.shape[0] < 2 or arr.shape[1] < 4:
        raise ValueError(
            "%s: %s must have at least 2 angles and 4 detector bins, got %r "
            "(if this is the transpose, the rows are your detector bins — this "
            "module's convention is rows = angles, and nothing downstream can "
            "detect the swap for you)" % (op, name, arr.shape))
    return arr


def _as_angles(angles_deg, n_rows: int | None, op: str) -> np.ndarray:
    """Projection angles in degrees, as a 1-D float64 array.

    ``None`` means "the uniform ``[0, 180)`` scan with one view per sinogram row",
    which is only available when *n_rows* is known.
    """
    if angles_deg is None:
        if n_rows is None:
            raise ValueError("%s: angles_deg=None needs a sinogram to take the view "
                             "count from" % (op,))
        return np.linspace(0.0, 180.0, int(n_rows), endpoint=False)
    arr = _as_float_array(angles_deg, "angles_deg", MAX_ANGLES, op)
    arr = np.atleast_1d(arr)
    if arr.ndim != 1:
        raise ValueError("%s: angles_deg must be 1-D, got shape %r"
                         % (op, arr.shape))
    if arr.size < 1:
        raise ValueError("%s: angles_deg is empty — a scan with zero projections "
                         "has no information in it; refusing rather than returning "
                         "an all-zero reconstruction that looks like a dark object"
                         % (op,))
    if arr.size >= 4:
        span = float(arr.max() - arr.min())
        if 0.0 < span <= 2.0 * np.pi:
            raise ValueError(
                "%s: the %d angles span only %.4f — in **degrees**, which is what "
                "this argument is, that is a scan through a %.4f-degree wedge, and "
                "a wedge that narrow carries no reconstructable information at all "
                "(measured: a 30-degree span already deletes 90 %% of the Fourier "
                "energy in the directions it misses). The overwhelmingly likely "
                "cause is that these are radians. Nothing downstream can catch it "
                "— passing radians to filtered_backprojection returns a finite, "
                "smooth, entirely plausible slice whose values are 39x too small "
                "(measured) — so it is refused here. Use np.rad2deg(), or "
                "projection_angles(), which returns degrees."
                % (op, arr.size, span, span))
    if n_rows is not None and arr.size != n_rows:
        raise ValueError(
            "%s: angles_deg has %d entries but the sinogram has %d rows. Rows are "
            "angles in this module; if your array is the detector axis you have the "
            "sinogram transposed, and every operator downstream would have accepted "
            "it silently" % (op, arr.size, n_rows))
    return arr


def _choice(v, allowed: tuple, name: str, op: str) -> str:
    if v is None:
        v = "none"
    if not isinstance(v, str):
        raise ValueError("%s: %s must be one of %r, got %r"
                         % (op, name, list(allowed), type(v).__name__))
    low = v.strip().lower()
    if low == "ram-lak" or low == "ramlak":
        low = "ramp"
    if low not in allowed:
        raise ValueError("%s: %s must be one of %r, got %r"
                         % (op, name, list(allowed), v))
    return low


def _default_detectors(h: int, w: int) -> int:
    """Enough bins to cover the image diagonal, forced odd so bin ``(n-1)/2`` is
    exactly the axis of rotation. An even count puts the axis *between* two bins,
    which is a half-pixel centre-of-rotation error that reconstructs as a faint
    double edge — the very artefact :func:`sinogram_center_of_rotation` exists to
    find, manufactured by the geometry itself."""
    n = int(np.ceil(np.hypot(h, w)))
    return n + 1 if n % 2 == 0 else n


# --------------------------------------------------------------------------- #
# internal projector / back-projector (parallel beam, unit detector pitch)     #
#                                                                              #
# Geometry, stated once and used by everything below:                          #
#   x = column - (W-1)/2,  y = row - (H-1)/2      (so +y runs DOWN the array)   #
#   a projection at angle theta measures the line  x cos(theta) + y sin(theta)  #
#   = s, parameterised by t along (-sin theta, cos theta)                       #
#   detector bin j sits at  s_j = j - (n_det-1)/2                               #
# --------------------------------------------------------------------------- #
def _bilinear_gather(img: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Bilinear sample of *img* at fractional ``(ys, xs)``, zero outside."""
    h, w = img.shape
    x0 = np.floor(xs).astype(np.int64)
    y0 = np.floor(ys).astype(np.int64)
    fx = xs - x0
    fy = ys - y0
    out = np.zeros(xs.shape, dtype=np.float64)
    for dy in (0, 1):
        for dx in (0, 1):
            xi = x0 + dx
            yi = y0 + dy
            ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
            wgt = (fx if dx else 1.0 - fx) * (fy if dy else 1.0 - fy)
            out += np.where(ok, img[np.clip(yi, 0, h - 1), np.clip(xi, 0, w - 1)] * wgt,
                            0.0)
    return out


def _project(img: np.ndarray, angles_rad: np.ndarray, n_det: int,
             oversample: int = 1) -> np.ndarray:
    """Forward parallel-beam projection -> ``(n_angles, n_det)`` sinogram.

    Ray sampling with bilinear interpolation and a trapezoidal sum, at
    *oversample* samples per pixel along the ray. Measured against the closed-form
    Radon transform of a disc (``tests/test_tomography.py``), the interior RMS
    error is **0.073 %** of the peak line integral at ``oversample=1`` and
    **0.070 %** at ``oversample=4`` — the residual is the bilinear resampling of
    the phantom's own anti-aliased edge, not the quadrature, which is why the
    default is 1 and not something four times slower for nothing.
    """
    h, w = img.shape
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0
    s = np.arange(n_det, dtype=np.float64) - (n_det - 1) / 2.0
    t_max = 0.5 * np.hypot(h, w) + 1.0
    n_t = int(np.ceil(2.0 * t_max * oversample)) + 1
    t = np.linspace(-t_max, t_max, n_t)
    dt = float(t[1] - t[0])
    out = np.empty((angles_rad.size, n_det), dtype=np.float64)
    for i, ang in enumerate(angles_rad):
        ca = float(np.cos(ang))
        sa = float(np.sin(ang))
        xs = s[:, None] * ca - t[None, :] * sa + cx
        ys = s[:, None] * sa + t[None, :] * ca + cy
        out[i] = _bilinear_gather(img, xs, ys).sum(axis=1) * dt
    return out


def _backproject(sino: np.ndarray, angles_rad: np.ndarray, size: int) -> np.ndarray:
    """Un-normalised back-projection: smear every projection back along its rays
    and sum. The caller supplies the ``d(theta)`` weight."""
    n_det = sino.shape[1]
    c = (size - 1) / 2.0
    grid = np.arange(size, dtype=np.float64) - c
    xg = grid[None, :]
    yg = grid[:, None]
    half = (n_det - 1) / 2.0
    acc = np.zeros((size, size), dtype=np.float64)
    for i, ang in enumerate(angles_rad):
        s = xg * float(np.cos(ang)) + yg * float(np.sin(ang)) + half
        j0 = np.floor(s).astype(np.int64)
        f = s - j0
        ok = (j0 >= 0) & (j0 + 1 < n_det)
        j0c = np.clip(j0, 0, n_det - 2)
        row = sino[i]
        acc += np.where(ok, row[j0c] * (1.0 - f) + row[j0c + 1] * f, 0.0)
    return acc


def _ramp_filter(n_pad: int, kind: str, cutoff: float) -> np.ndarray:
    """The reconstruction filter, sampled on ``rfft`` bins of a length-*n_pad*
    projection with unit detector pitch.

    The base is the exact ramp ``|f|`` in *ordinary* frequency (cycles per
    detector bin), because the inversion formula
    ``f(x) = int_0^pi int |f| P(f,theta) exp(2 pi i f s) df dtheta``
    is written in ordinary frequency too. Writing the ramp in *angular* frequency
    instead — ``|omega| = 2 pi |f|``, the other convention in the same textbooks —
    multiplies every reconstructed value by 2 pi and nothing in the picture says
    so, since a CT slice has no absolute grey level to check against. The unit
    test that pins this reconstructs a uniform disc of density 1.0 from its
    *analytic* sinogram and requires the interior to come back at 1.0.
    """
    f = np.fft.rfftfreq(n_pad, d=1.0)
    ramp = np.abs(f)
    nyq = 0.5
    with np.errstate(divide="ignore", invalid="ignore"):
        if kind == "ramp":
            win = np.ones_like(f)
        elif kind == "shepp-logan":
            x = np.pi * f / (2.0 * nyq)
            win = np.where(x == 0.0, 1.0, np.sin(np.where(x == 0.0, 1.0, x)) / np.where(x == 0.0, 1.0, x))
        elif kind == "cosine":
            win = np.cos(np.pi * f / (2.0 * nyq))
        elif kind == "hann":
            win = 0.5 * (1.0 + np.cos(np.pi * f / nyq))
        elif kind == "hamming":
            win = 0.54 + 0.46 * np.cos(np.pi * f / nyq)
        else:  # "none" — handled by the caller, never reaches here
            win = np.ones_like(f)
    h = ramp * win
    if cutoff < 1.0:
        h = np.where(f <= cutoff * nyq + 1e-12, h, 0.0)
    return h


def _filter_projections(sino: np.ndarray, kind: str, cutoff: float) -> np.ndarray:
    """Apply the reconstruction filter along the detector axis.

    Zero-padded to at least twice the detector count before the FFT. Without the
    pad the circular convolution wraps the ramp's long negative tails around the
    detector axis, which puts a smooth cup across the reconstruction that looks
    exactly like beam hardening — measured on a uniform disc as a **4.05 %**
    depression of the interior mean (0.9551 unpadded against 0.9954 padded, on a
    true density of 1.0) that the pad removes.
    """
    n_det = sino.shape[1]
    n_pad = 1
    while n_pad < 2 * n_det:
        n_pad <<= 1
    h = _ramp_filter(n_pad, kind, cutoff)
    padded = np.zeros((sino.shape[0], n_pad), dtype=np.float64)
    padded[:, :n_det] = sino
    out = np.fft.irfft(np.fft.rfft(padded, axis=1) * h[None, :], n=n_pad, axis=1)
    return np.ascontiguousarray(out[:, :n_det])


# --------------------------------------------------------------------------- #
# 1. scan layout                                                               #
# --------------------------------------------------------------------------- #
def projection_angles(n_angles=180, span_deg=180.0, scheme="uniform",
                      start_deg=0.0):
    """The angle sequence of a scan, in **degrees**, as a 1-D float64 array.

    Three schemes, and the difference between them is what happens when a scan is
    cut short:

    * ``"uniform"`` — ``start + span * k / n``. The textbook scan. A prefix of it
      covers only a wedge, so an interrupted uniform scan is a limited-angle scan.
    * ``"golden"`` — increments of ``180/phi = 111.246...`` degrees, wrapped into
      ``[start, start+span)``. Every prefix is near-uniform, so an interrupted
      golden scan is a *sparse* scan, which is a far easier problem. Largest
      angular gap left by a scan that stops early, measured:

        scheme          after 32 of 180    all 180
        uniform            149.000 deg     1.000 deg
        golden              10.031 deg     1.464 deg
        bit-reversed         8.000 deg     1.000 deg

      Uniform's 149-degree hole is the entire limited-angle problem arriving by
      accident. Bit-reversed is the only one of the three that is good at both
      ends; golden's price for working at *every* prefix length rather than only
      at powers of two is a completed set 1.46x less even than the grid.
    * ``"bit-reversed"`` — the uniform grid, visited in bit-reversed order. Same
      guarantee as golden for power-of-two prefixes and exactly uniform at the
      end, which golden is not.

    *span_deg* is the total angular range. 180 degrees is the complete data set
    for parallel beam — projections at ``theta`` and ``theta+180`` are mirror
    images and carry no new information — so a 360-degree span is redundancy, not
    resolution, and anything under 180 is the limited-angle problem.

    :param n_angles: number of views, ``1 .. 65536``.
    :param span_deg: total angular range in degrees, ``> 0``.
    :param scheme: one of :data:`ANGLE_SCHEMES`.
    :param start_deg: angle of the first view.
    :returns: ``(n_angles,)`` float64 array of degrees.
    :raises ValueError: on a non-int count, a non-positive span, a non-finite
        start, or an unknown scheme.
    """
    op = "projection_angles"
    n = _count(n_angles, "n_angles", 1, MAX_ANGLES)
    span = _positive(span_deg, "span_deg")
    start = _finite_scalar(start_deg, "start_deg")
    mode = _choice(scheme, ANGLE_SCHEMES, "scheme", op)
    if mode == "uniform":
        return start + span * np.arange(n, dtype=np.float64) / float(n)
    if mode == "golden":
        return start + np.mod(GOLDEN_ANGLE_DEG * np.arange(n, dtype=np.float64),
                              span)
    bits = 1
    while (1 << bits) < n:
        bits += 1
    order = []
    for k in range(1 << bits):
        r = 0
        for b in range(bits):
            if k & (1 << b):
                r |= 1 << (bits - 1 - b)
        if r < n:
            order.append(r)
    return start + span * np.asarray(order[:n], dtype=np.float64) / float(n)


def sinogram_design(n_angles=180, n_detectors=None, size=256,
                    detector_pitch_mm=1.0, span_deg=180.0):
    """What a scan geometry can and cannot resolve — **before** anything is built.

    The axial counterpart of :func:`visiondesign.imaging_budget` and of
    :func:`interferometry.csi_design`: no data goes in, only the geometry, and
    what comes out are the limits that the geometry has already decided.

    Returns a dict with, among others:

    * ``resolvable_feature_mm`` — ``2 * pitch``: two detector samples per cycle is
      the Nyquist floor, and no reconstruction algorithm recovers a detail finer
      than the detector saw.
    * ``views_for_full_sampling`` — ``ceil(pi/2 * n_detectors)``, the classical
      matching of angular to radial sampling (:data:`VIEWS_PER_DETECTOR`).
    * ``undersampling_factor`` — that number over ``n_angles``. **1.0 or below is
      a fully sampled scan.** Above it you are doing sparse-view CT on purpose and
      the reconstruction algorithm has to make up the difference; the measured
      cost is in this module's docstring and in the test suite's break table.
    * ``streak_free_radius_px`` — ``pitch / d(theta)`` in radians: the radius at
      which the *azimuthal* sample spacing between neighbouring views grows past
      the detector pitch. Outside it, filtered back-projection lays down visible
      streaks. For 180 views over 180 degrees this is 57.3 px, i.e. a 256-px
      phantom is already streaking at its corners.
    * ``sinogram_bytes`` / ``elements`` — what you are about to allocate.
    * ``verdict`` — ``"fully sampled"`` / ``"sparse view"``.

    :param n_angles: planned number of views.
    :param n_detectors: planned detector bins; ``None`` -> enough to cover the
        diagonal of a *size* x *size* image.
    :param size: reconstruction grid side in pixels.
    :param detector_pitch_mm: physical detector bin spacing.
    :param span_deg: angular range of the scan.
    :returns: dict of floats / ints / str.
    :raises ValueError: on non-int counts, non-positive pitch or span.
    """
    op = "sinogram_design"
    n_a = _count(n_angles, "n_angles", 1, MAX_ANGLES)
    sz = _count(size, "size", 2, 1 << 14)
    n_d = (_default_detectors(sz, sz) if n_detectors is None
           else _count(n_detectors, "n_detectors", 4, MAX_DETECTORS))
    pitch = _positive(detector_pitch_mm, "detector_pitch_mm")
    span = _positive(span_deg, "span_deg")
    if n_a * n_d > MAX_SINOGRAM_ELEMENTS:
        raise ValueError(
            "%s: %d angles x %d detectors = %d elements, over the %d cap. This is "
            "the design operator, so it refuses the *plan* rather than waiting for "
            "the allocation to fail later" % (op, n_a, n_d, n_a * n_d,
                                              MAX_SINOGRAM_ELEMENTS))
    d_theta = np.deg2rad(span) / n_a
    need = int(np.ceil(VIEWS_PER_DETECTOR * n_d))
    under = need / float(n_a)
    return {
        "n_angles": n_a,
        "n_detectors": n_d,
        "size": sz,
        "span_deg": span,
        "angular_step_deg": span / n_a,
        "detector_pitch_mm": pitch,
        "field_of_view_mm": n_d * pitch,
        "resolvable_feature_mm": 2.0 * pitch,
        "views_for_full_sampling": need,
        "undersampling_factor": under,
        "streak_free_radius_px": pitch / d_theta,
        "complete_angular_coverage": bool(span >= 180.0),
        "sinogram_elements": n_a * n_d,
        "sinogram_bytes": n_a * n_d * 8,
        "verdict": "fully sampled" if under <= 1.0 else "sparse view",
    }


# --------------------------------------------------------------------------- #
# 2. phantoms and the closed-form forward transform                            #
# --------------------------------------------------------------------------- #
def _as_ellipses(ellipses, op: str) -> np.ndarray:
    if ellipses is None:
        return np.asarray(SHEPP_LOGAN, dtype=np.float64)
    arr = _as_float_array(ellipses, "ellipses", 1 << 16, op)
    arr = np.atleast_2d(arr)
    if arr.ndim != 2 or arr.shape[1] != 6:
        raise ValueError(
            "%s: ellipses must be (N, 6) rows of (x0, y0, a, b, phi_deg, rho), got "
            "shape %r" % (op, arr.shape))
    if arr.shape[0] < 1:
        raise ValueError("%s: ellipses is empty" % (op,))
    if (arr[:, 2] <= 0.0).any() or (arr[:, 3] <= 0.0).any():
        bad = int(((arr[:, 2] <= 0.0) | (arr[:, 3] <= 0.0)).sum())
        raise ValueError(
            "%s: %d ellipse(s) have a non-positive semi-axis. A zero semi-axis is a "
            "degenerate line whose analytic Radon transform is a delta function; "
            "the rasterised phantom would show nothing while the analytic sinogram "
            "divided by zero, so the two would disagree without either raising"
            % (op, bad))
    return arr


def ellipse_phantom(size=256, ellipses=None, supersample=4):
    """Rasterise a sum of uniform ellipses onto a *size* x *size* slice.

    The default is :data:`SHEPP_LOGAN`. The normalised square ``[-1, 1]^2`` maps
    onto the grid, so ``x = (col - (size-1)/2) / (size/2)``; the same mapping is
    used by :func:`ellipse_sinogram`, which is what makes the two comparable
    without a fudge factor.

    *supersample* is the anti-aliasing factor: each pixel is the mean of
    ``supersample^2`` sub-samples, so an edge pixel carries its true area
    fraction. This is not cosmetic — a hard 0/1 rasterisation projects to a
    sinogram that disagrees with the closed form by **0.276 % interior RMS** of
    the peak, against **0.073 %** anti-aliased (measured), and the
    difference is entirely the partial-volume edge.

    :param size: side of the square grid, ``2 .. 16384``.
    :param ellipses: ``(N, 6)`` rows ``(x0, y0, a, b, phi_deg, rho)`` in
        normalised coordinates; ``None`` -> :data:`SHEPP_LOGAN`.
    :param supersample: anti-alias factor per axis, ``1 .. 16``.
    :returns: ``(size, size)`` float64 image; the Shepp-Logan default spans
        ``[0.0, 1.0]``.
    :raises ValueError: on a non-int size, a degenerate ellipse, or a grid over
        :data:`MAX_IMAGE_ELEMENTS`.
    """
    op = "ellipse_phantom"
    sz = _count(size, "size", 2, 1 << 14)
    ss = _count(supersample, "supersample", 1, 16)
    if sz * sz > MAX_IMAGE_ELEMENTS:
        raise ValueError(
            "%s: size=%d asks for %d pixels, over the %d cap (~%d MB as float64). "
            "The argument is one small int and the allocation is quadratic in it, "
            "so the cap is read off the *requested* size before anything is "
            "allocated" % (op, sz, sz * sz, MAX_IMAGE_ELEMENTS,
                           sz * sz * 8 // (1 << 20)))
    if sz * sz * ss * ss > 4 * MAX_IMAGE_ELEMENTS:
        raise ValueError(
            "%s: size=%d with supersample=%d needs a %d-element intermediate grid, "
            "over the %d cap. Both arguments are small ints and the product is "
            "quartic in them — this is the trap where a legal-looking call "
            "allocates gigabytes internally" % (op, sz, ss, sz * sz * ss * ss,
                                                4 * MAX_IMAGE_ELEMENTS))
    ell = _as_ellipses(ellipses, op)
    r = sz / 2.0
    c = (sz - 1) / 2.0
    sub = (np.arange(ss, dtype=np.float64) + 0.5) / ss - 0.5
    coord = ((np.arange(sz, dtype=np.float64)[:, None] + sub[None, :]).ravel() - c) / r
    out = np.zeros((sz * ss, sz * ss), dtype=np.float64)
    xg = coord[None, :]
    yg = coord[:, None]
    for x0, y0, a, b, phi_deg, rho in ell:
        ph = np.deg2rad(phi_deg)
        cp, sp = np.cos(ph), np.sin(ph)
        dx = xg - x0
        dy = yg - y0
        u = dx * cp + dy * sp
        v = -dx * sp + dy * cp
        out += np.where((u / a) ** 2 + (v / b) ** 2 <= 1.0, rho, 0.0)
    return out.reshape(sz, ss, sz, ss).mean(axis=(1, 3))


def ellipse_sinogram(size=256, ellipses=None, angles_deg=None, n_detectors=None):
    """The **closed-form** Radon transform of a sum of uniform ellipses.

    The ground truth this module is tested against, and a usable operator in its
    own right: a sinogram with no discretisation error to feed a reconstruction,
    so that any error in the picture belongs to the reconstruction and not to the
    projector.

    For one ellipse with centre ``(x0, y0)``, semi-axes ``(a, b)``, rotation
    ``phi`` and density ``rho``, the line integral along ``x cos(t) + y sin(t) =
    s`` is::

        A(t)^2 = a^2 cos^2(t - phi) + b^2 sin^2(t - phi)
        s'     = s - (x0 cos t + y0 sin t)
        p      = 2 rho a b sqrt(A^2 - s'^2) / A^2      for |s'| < A,  else 0

    which for a disc (``a = b = r``, ``rho = 1``) collapses to the chord length
    ``2 sqrt(r^2 - s^2)``. Densities add, so a sum of ellipses projects to a sum
    of these.

    The result is in the **same pixel units** as :func:`radon_transform` applied
    to :func:`ellipse_phantom` at the same *size*: the normalised half-width is
    ``size/2`` pixels, and a line integral scales with length, so the closed form
    is multiplied by ``size/2``. Getting that factor wrong is invisible in the
    picture — a sinogram has no absolute scale — and shows up only as a
    reconstruction whose density is off by a constant, which is why it is pinned
    by a test rather than by a comment.

    :param size: the pixel grid the units refer to (as in :func:`ellipse_phantom`).
    :param ellipses: as :func:`ellipse_phantom`; ``None`` -> :data:`SHEPP_LOGAN`.
    :param angles_deg: view angles; ``None`` -> ``linspace(0, 180, 180,
        endpoint=False)``.
    :param n_detectors: detector bins; ``None`` -> enough to cover the diagonal.
    :returns: ``(n_angles, n_detectors)`` float64 sinogram.
    :raises ValueError: on a degenerate ellipse or a sinogram over
        :data:`MAX_SINOGRAM_ELEMENTS`.
    """
    op = "ellipse_sinogram"
    sz = _count(size, "size", 2, 1 << 14)
    ell = _as_ellipses(ellipses, op)
    ang = (np.linspace(0.0, 180.0, 180, endpoint=False) if angles_deg is None
           else _as_angles(angles_deg, None, op))
    n_d = (_default_detectors(sz, sz) if n_detectors is None
           else _count(n_detectors, "n_detectors", 4, MAX_DETECTORS))
    if ang.size * n_d > MAX_SINOGRAM_ELEMENTS:
        raise ValueError(
            "%s: %d angles x %d detectors = %d elements, over the %d cap"
            % (op, ang.size, n_d, ang.size * n_d, MAX_SINOGRAM_ELEMENTS))
    r = sz / 2.0
    s = (np.arange(n_d, dtype=np.float64) - (n_d - 1) / 2.0) / r    # normalised
    t = np.deg2rad(ang)
    ct = np.cos(t)[:, None]
    st = np.sin(t)[:, None]
    out = np.zeros((ang.size, n_d), dtype=np.float64)
    for x0, y0, a, b, phi_deg, rho in ell:
        ph = np.deg2rad(phi_deg)
        cc = np.cos(t - ph)[:, None]
        ss_ = np.sin(t - ph)[:, None]
        a2 = (a * cc) ** 2 + (b * ss_) ** 2
        sp = s[None, :] - (x0 * ct + y0 * st)
        inside = a2 - sp ** 2
        out += np.where(inside > 0.0,
                        2.0 * rho * a * b * np.sqrt(np.maximum(inside, 0.0)) / a2,
                        0.0)
    return out * r


def radon_transform(image, angles_deg=None, n_detectors=None, oversample=1):
    """Forward parallel-beam projection: a slice in, a **sinogram** out.

    Rows of the result are projection angles and columns are detector bins. The
    convention is fixed here and never negotiated again; every other operator in
    this module reads it the same way, and a transposed sinogram is structurally
    indistinguishable from a valid one (see :mod:`opstomography` for the measured
    consequences of not giving it its own sort).

    The ray at detector bin ``j`` and angle ``theta`` is the line
    ``x cos(theta) + y sin(theta) = j - (n_det-1)/2``, with ``x`` the column
    offset from the image centre and ``y`` the row offset — so ``+y`` runs *down*
    the array, matching the rest of Fullseye's image indexing rather than a
    textbook's upward ``y``. The transform is the same either way (the sinogram is
    mirrored in the angle axis), but only one of the two agrees with
    :func:`ellipse_phantom`, and the tests hold them together.

    Accuracy against the closed form (a disc of radius 60 px in a 256-px grid,
    180 views), measured in ``tests/test_tomography.py``: interior RMS error
    **0.073 %** of the peak line integral, whole-sinogram RMS **0.402 %** — the
    difference between the two being the partial-volume edge, where the phantom's
    own anti-aliased boundary is what is being sampled.

    :param image: 2-D slice, at least 2x2.
    :param angles_deg: 1-D view angles in degrees; ``None`` ->
        ``linspace(0, 180, 180, endpoint=False)``.
    :param n_detectors: bins; ``None`` -> odd count covering the diagonal.
    :param oversample: ray samples per pixel, ``1 .. 8``. The default is 1
        because 4 measures no better (0.073 % against 0.070 %).
    :returns: ``(n_angles, n_detectors)`` float64 sinogram.
    :raises ValueError: on non-finite input, an empty angle list, a detector count
        under 4, or a sinogram over :data:`MAX_SINOGRAM_ELEMENTS`.
    """
    op = "radon_transform"
    img = _as_image(image, op)
    ang = (np.linspace(0.0, 180.0, 180, endpoint=False) if angles_deg is None
           else _as_angles(angles_deg, None, op))
    n_d = (_default_detectors(*img.shape) if n_detectors is None
           else _count(n_detectors, "n_detectors", 4, MAX_DETECTORS))
    ov = _count(oversample, "oversample", 1, 8)
    if ang.size * n_d > MAX_SINOGRAM_ELEMENTS:
        raise ValueError(
            "%s: %d angles x %d detectors = %d elements, over the %d cap. Note that "
            "both are *arguments*, not properties of the input image — a 64x64 "
            "image with 100000 angles is a small input asking for a huge output"
            % (op, ang.size, n_d, ang.size * n_d, MAX_SINOGRAM_ELEMENTS))
    diag = np.hypot(*img.shape)
    if n_d < diag - 1.0:
        raise ValueError(
            "%s: %d detector bins do not cover the %.1f-px diagonal of a %dx%d "
            "image. The corners project outside the detector and are silently "
            "truncated, which reconstructs as a bright ring at the edge of the "
            "field of view and as a density error everywhere inside it (the "
            "missing mass has to go somewhere). Pass n_detectors >= %d, or crop "
            "the image to the inscribed circle first."
            % (op, n_d, diag, img.shape[0], img.shape[1], int(np.ceil(diag))))
    return _project(img, np.deg2rad(ang), n_d, ov)


# --------------------------------------------------------------------------- #
# 3. reconstruction                                                            #
# --------------------------------------------------------------------------- #
def _recon_size(size, sino: np.ndarray, op: str) -> int:
    if size is None:
        n = int(np.floor(sino.shape[1] / np.sqrt(2.0)))
        return n if n % 2 == 1 else n - 1
    sz = _count(size, "size", 2, 1 << 14)
    if sz * sz > MAX_IMAGE_ELEMENTS:
        raise ValueError(
            "%s: size=%d asks for a %d-pixel reconstruction, over the %d cap. The "
            "sinogram may be tiny — the output size is an argument, and the cost is "
            "quadratic in it" % (op, sz, sz * sz, MAX_IMAGE_ELEMENTS))
    return sz


def backproject_sinogram(sinogram, angles_deg=None, size=None, span_deg=None):
    """Plain, **un-filtered** back-projection — the blurred baseline.

    Smear each projection back along the rays it came from and sum. The result is
    the true slice convolved with ``1/|r|``, so it is correct in the large and
    wrong everywhere in detail.

    Two numbers, because only one of them is the interesting one. Raw, on the
    Shepp-Logan phantom with 180 views, this operator's values run 0.768 to 2.493
    where the truth runs 0.0 to 0.0167 — the ``1/|r|`` kernel has no finite
    integral, so an un-filtered back-projection has **no meaningful absolute
    scale at all** and its normalised RMS error against the truth is 104. After
    the best least-squares rescaling onto the truth — which is what any display
    with an auto window does for you, silently — the error is **0.168** against
    **0.0246** for :func:`filtered_backprojection`, a factor of **6.8**. That
    second number is the ramp filter's real contribution; the first is a warning
    that a picture which looks approximately right after auto-windowing can be
    off by a factor of 100 in the numbers underneath it.

    It is a registered operator and not a private helper because the blur *is* the
    lesson, and because it is the correct starting point for iterative methods.

    Not to be confused with :func:`fullseye.backproject`, which lifts pixels into
    3-D using a depth map and a camera model; that one is projective geometry, this
    one is an integral transform, and the only thing they share is a word.

    :param sinogram: ``(n_angles, n_detectors)``, rows = angles.
    :param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``.
    :param size: output side; ``None`` -> the inscribed square, ``n_det/sqrt2``
        rounded down to an odd number.
    :param span_deg: angular range used for the ``d(theta)`` weight; ``None`` ->
        inferred from *angles_deg* (or 180 for the default scan).
    :returns: ``(size, size)`` float64 image.
    :raises ValueError: as :func:`filtered_backprojection`.
    """
    return filtered_backprojection(sinogram, angles_deg=angles_deg, size=size,
                                   filter_name="none", span_deg=span_deg,
                                   _op="backproject_sinogram")


def _span_weight(ang: np.ndarray, span_deg, op: str) -> float:
    """The ``d(theta)`` weight of the back-projection sum, in radians.

    ``span / n_angles``, because the inversion integrates over ``[0, pi)`` and the
    views are its quadrature nodes. Taking ``pi / n_angles`` unconditionally — the
    form printed in every textbook, which assumes a full half-turn — is the silent
    error this helper exists to prevent: a 90-degree limited-angle scan would come
    back at twice its true density, and a limited-angle reconstruction is expected
    to look wrong, so nobody would question the number.
    """
    if span_deg is not None:
        return np.deg2rad(_positive(span_deg, "span_deg")) / ang.size
    if ang.size == 1:
        return np.pi
    step = float(np.median(np.diff(np.sort(ang))))
    if step <= 0.0:
        raise ValueError(
            "%s: the angle list has a non-positive median step (duplicate angles?) "
            "— pass span_deg explicitly to say what range these views cover" % (op,))
    return np.deg2rad(step)


def filtered_backprojection(sinogram, angles_deg=None, size=None,
                            filter_name="ramp", cutoff=1.0, span_deg=None,
                            _op="filtered_backprojection"):
    """Filtered back-projection (FBP) — the standard CT reconstruction.

    Filter each projection along the detector axis with the ramp ``|f|`` (times an
    optional apodisation window), then back-project. This is the discretised
    inverse Radon transform, and with enough samples it is exact: reconstructing a
    uniform disc of density 1.0 from its **analytic** sinogram returns an interior
    mean of **0.9954** with 363 detector bins and **0.9997** with 727, converging
    on the truth as the *detector* is refined and not as the view count is (180,
    360 and 720 views give the same 0.9954 to six figures). That absolute value is
    what pins the ordinary-versus-angular frequency convention in the ramp: the
    other convention, equally defensible and printed in the same textbooks, would
    return ``2*pi`` times this, and a CT slice has no absolute grey level for
    anyone to notice against.

    Where it breaks, measured on the Shepp-Logan phantom (256 px, **analytic**
    sinogram so the projector contributes no error of its own; normalised RMS
    error against the truth):

        views     FBP (ramp)    SART (10 sweeps)    FBP/SART
          180        0.0250          0.0175           1.43
           90        0.0454          0.0195           2.33
           45        0.1039          0.0353           2.95
           32        0.1362          0.0497           2.74
           16        0.2341          0.0859           2.72
            8        0.3635          0.1257           2.89

    **There is no crossing point, and the expectation that there would be one was
    wrong.** The received story is that FBP wins when the data is complete and
    loses only in the sparse regime; measured here, SART with a non-negativity
    constraint is better at *every* view count — by 1.43x at 180 views and by
    about 2.9x once the scan is sparse. What changes with the view count is the
    price, not the ranking: at 180 views SART costs **312x** the wall clock
    (37.7 s against 0.12 s for a 256-px slice) to buy that 1.43x, which is why
    filtered back-projection is what production scanners run. At the sparse end
    the same 2.9x comes nearly free, because both methods scale with the views.

    With noise the ranking holds but the margins change, and the apodisation
    windows stop being decoration (Poisson counts at ``I0 = 2e4``, same phantom):

        views    FBP ramp    FBP hann    SART (10 sweeps)
          180      0.0360      0.0371         0.0291
           45      0.1159      0.0766         0.0385
           16      0.2481      0.1921         0.0864
            8      0.3813      0.3093         0.1259

    At 180 views the exact ramp beats Hann — the data is complete and the roll-off
    only blurs. At 45 views and below Hann beats the exact inverse by up to 1.5x,
    because the frequencies the ramp is busy amplifying were never measured.

    Filters, and what they trade: ``"ramp"`` is the exact inverse and therefore
    the sharpest and the noisiest; ``"shepp-logan"``, ``"cosine"``, ``"hann"`` and
    ``"hamming"`` roll the high frequencies off, in that order of aggressiveness.
    ``"none"`` skips the filter entirely and gives :func:`backproject_sinogram`.

    :param sinogram: ``(n_angles, n_detectors)``, rows = angles.
    :param angles_deg: view angles in degrees; ``None`` -> uniform ``[0, 180)``
        with one view per row.
    :param size: output side; ``None`` -> the inscribed square.
    :param filter_name: one of :data:`FILTERS`.
    :param cutoff: fraction of Nyquist to keep, ``(0, 1]``.
    :param span_deg: angular range for the ``d(theta)`` weight; ``None`` -> the
        median angular step.
    :returns: ``(size, size)`` float64 image.
    :raises ValueError: on a non-2-D or non-finite sinogram, an angle count that
        disagrees with the row count, an unknown filter, a cutoff outside
        ``(0, 1]``, or an output over :data:`MAX_IMAGE_ELEMENTS`.
    """
    op = _op
    sino = _as_sinogram(sinogram, op)
    ang = _as_angles(angles_deg, sino.shape[0], op)
    kind = _choice(filter_name, FILTERS, "filter_name", op)
    cut = _finite_scalar(cutoff, "cutoff")
    if not (0.0 < cut <= 1.0):
        raise ValueError("%s: cutoff must be in (0, 1], got %g" % (op, cut))
    sz = _recon_size(size, sino, op)
    d_theta = _span_weight(ang, span_deg, op)
    work = sino if kind == "none" else _filter_projections(sino, kind, cut)
    return _backproject(work, np.deg2rad(ang), sz) * d_theta


def sart_reconstruct(sinogram, angles_deg=None, size=None, n_iter=10,
                     relaxation=0.3, initial=None, nonnegative=True):
    """SART — simultaneous algebraic reconstruction, one angle at a time.

    An iterative solver for ``A x = p`` where ``A`` is the projector: for each
    view in turn, project the current estimate, take the residual, and
    back-project it with the row and column sums of ``A`` as normalisers::

        x <- x + lambda * BP_theta( (p_theta - FP_theta(x)) / rowsum_theta )
                          / colsum_theta

    *rowsum* is the length of each ray through the grid and *colsum* is how many
    rays touched each pixel, so the update is dimensionally a density and does not
    depend on the grid size. One "iteration" is one pass over all views.

    Why it exists next to :func:`filtered_backprojection`: FBP inverts an integral
    transform and therefore *needs* the transform to have been sampled; SART
    solves a linear system and merely does worse when the system is
    underdetermined. Measured, it is better at every view count tested (the table
    in :func:`filtered_backprojection`), by 1.43x at 180 views and 2.9x at 8.

    The cost is honest and it is the reason this is not the default: 10 sweeps
    over 180 views is 1800 forward *and* 1800 back-projections against FBP's 180
    back-projections, measured at **37.7 s** against **0.12 s** for a 256-px
    reconstruction — a factor of **312**. At 8 views it is 2.14 s against 0.01 s,
    the same ratio applied to a much smaller number.

    ``nonnegative=True`` clips the estimate at zero after every sweep. Attenuation
    coefficients cannot be negative, so this is a genuine constraint and not a
    cosmetic clip, and it carries a large part of the advantage above — measured
    on the analytic Shepp-Logan sinogram, normalised RMS with the constraint
    against without:

        views     with     without
          180    0.0175    0.0300
           45    0.0353    0.0626
            8    0.1257    0.1428

    so at 180 views the constraint alone is worth 1.7x, and it is the *only*
    reason SART leads FBP there at all (FBP scores 0.0250, between the two).

    :param sinogram: ``(n_angles, n_detectors)``, rows = angles.
    :param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``.
    :param size: output side; ``None`` -> the inscribed square.
    :param n_iter: sweeps over the full angle set, ``1 .. 500``.
    :param relaxation: step size ``lambda``, ``(0, 2)``. Over 1 the iteration can
        oscillate; over 2 it provably diverges, and is refused.
    :param initial: starting estimate, ``(size, size)``; ``None`` -> zeros.
    :param nonnegative: clip to ``>= 0`` after each sweep.
    :returns: ``(size, size)`` float64 image.
    :raises ValueError: as :func:`filtered_backprojection`, plus a relaxation
        outside ``(0, 2)`` and an *initial* whose shape is not ``(size, size)``.
    """
    op = "sart_reconstruct"
    sino = _as_sinogram(sinogram, op)
    ang = _as_angles(angles_deg, sino.shape[0], op)
    sz = _recon_size(size, sino, op)
    n_it = _count(n_iter, "n_iter", 1, 500)
    lam = _finite_scalar(relaxation, "relaxation")
    if not (0.0 < lam < 2.0):
        raise ValueError(
            "%s: relaxation must be in (0, 2), got %g. The bound is the classical "
            "convergence condition for a relaxed row-action method; at 2 or above "
            "the iteration provably diverges, and it diverges *slowly* — after 10 "
            "sweeps at lambda=2.0 the picture still looks like a noisy "
            "reconstruction rather than an obvious failure" % (op, lam))
    if not isinstance(nonnegative, (bool, np.bool_)):
        raise ValueError("%s: nonnegative must be a bool, got %r"
                         % (op, type(nonnegative).__name__))
    rad = np.deg2rad(ang)
    n_det = sino.shape[1]

    if initial is None:
        x = np.zeros((sz, sz), dtype=np.float64)
    else:
        x = _as_image(initial, op, "initial").copy()
        if x.shape != (sz, sz):
            raise ValueError("%s: initial has shape %r but the reconstruction is "
                             "%dx%d" % (op, x.shape, sz, sz))

    ones_img = np.ones((sz, sz), dtype=np.float64)
    ones_sino = np.ones((1, n_det), dtype=np.float64)
    eps = 1e-9
    row_sums = _project(ones_img, rad, n_det, 1)            # ray lengths, per view
    col_sums = [np.maximum(_backproject(ones_sino, rad[i:i + 1], sz), eps)
                for i in range(rad.size)]
    for _ in range(n_it):
        for i in range(rad.size):
            fp = _project(x, rad[i:i + 1], n_det, 1)[0]
            resid = (sino[i] - fp) / np.maximum(row_sums[i], eps)
            x = x + lam * _backproject(resid[None, :], rad[i:i + 1], sz) / col_sums[i]
        if nonnegative:
            np.clip(x, 0.0, None, out=x)
    return x


# --------------------------------------------------------------------------- #
# 4. artefacts: the forward model and the correction, always as a pair         #
# --------------------------------------------------------------------------- #
def beam_hardening_apply(sinogram, high_energy_fraction=0.5,
                         attenuation_ratio=0.4):
    """Turn a monochromatic sinogram into a **polychromatic** one — cupping.

    A real X-ray tube emits a spectrum, and low-energy photons are absorbed more,
    so the beam that survives a thick path is *harder* (higher mean energy) and
    therefore attenuated less per unit length than the beam that survives a thin
    one. The line integral stops being linear in path length, and the
    reconstruction of a uniform object comes back with a depressed centre: the
    cupping artefact.

    The two-spectrum model used here is the smallest one that is physics and not a
    curve::

        I/I0    = (1-w) exp(-p) + w exp(-k p)
        p_meas  = -ln(I/I0)

    with *w* the fraction of the beam at the high energy and *k < 1* its relative
    attenuation. It is exact at ``p = 0``, concave everywhere, and monotone — so
    it is invertible, which is what :func:`beam_hardening_correct` inverts.

    Measured on a uniform disc (radius 60 px in 256 px, density 1/60 so the peak
    line integral is 2.0) at ``w = 0.5, k = 0.4``: the FBP reconstruction's
    centre-to-rim ratio drops to **0.9312**, against **0.9981** before hardening,
    and :func:`beam_hardening_correct` returns it to **0.9981** — the clean value
    in all four digits. (The clean ratio is 0.9981 rather than exactly 1 because
    of the detector sampling discussed in :func:`filtered_backprojection`. The
    cupping is the 6.7-point drop, not the 0.2-point one.)

    :param sinogram: ``(n_angles, n_detectors)`` monochromatic line integrals,
        which must be ``>= 0``.
    :param high_energy_fraction: *w*, in ``[0, 1)``. 0 is a monochromatic beam and
        the operator is then the identity.
    :param attenuation_ratio: *k*, in ``(0, 1)``. 1 is again monochromatic.
    :returns: ``(n_angles, n_detectors)`` float64 hardened sinogram.
    :raises ValueError: on a negative sinogram (a negative line integral is not a
        measurement this model can harden — the logarithm of the transmitted
        intensity has already gone wrong upstream), or parameters outside range.
    """
    op = "beam_hardening_apply"
    sino = _as_sinogram(sinogram, op)
    w = _finite_scalar(high_energy_fraction, "high_energy_fraction")
    k = _finite_scalar(attenuation_ratio, "attenuation_ratio")
    if not (0.0 <= w < 1.0):
        raise ValueError("%s: high_energy_fraction must be in [0, 1), got %g"
                         % (op, w))
    if not (0.0 < k <= 1.0):
        raise ValueError("%s: attenuation_ratio must be in (0, 1], got %g (a ratio "
                         "above 1 would mean the harder half of the beam is "
                         "absorbed *more*, which inverts the artefact into a "
                         "capping one that no correction here undoes)" % (op, k))
    if (sino < 0.0).any():
        bad = int((sino < 0.0).sum())
        raise ValueError(
            "%s: the sinogram has %d negative value(s). A line integral of a "
            "non-negative attenuation cannot be negative; this input has already "
            "been through something (a filter, a subtraction) that the exponential "
            "model does not describe, and hardening it would return a plausible "
            "array with no physical meaning" % (op, bad))
    return -np.log((1.0 - w) * np.exp(-sino) + w * np.exp(-k * sino))


def beam_hardening_correct(sinogram, high_energy_fraction=0.5,
                           attenuation_ratio=0.4, poly_coeffs=None,
                           n_table=4096):
    """Undo cupping — either the exact model inverse, or a calibrated polynomial.

    Two routes, and the difference between them is what you are allowed to claim:

    * **Model inverse** (default). :func:`beam_hardening_apply` is a monotone
      scalar function of the line integral, so it has an exact inverse; this
      builds it by interpolating the forward curve on *n_table* nodes. Round-trip
      error on the disc phantom: **1.6e-08** absolute and **8.0e-09** relative to
      the peak line integral — the table resolution and nothing else.
      This is a *simulation* tool — it needs the same ``w`` and ``k`` the
      hardening used, which on real data nobody has.
    * **Polynomial** (*poly_coeffs*). ``p_corr = c1 p + c2 p^2 + ...``, the
      water-correction of every clinical scanner, whose coefficients come from
      scanning a uniform water phantom and fitting for a flat reconstruction.
      This is what applies to real data, and it is only as good as the assumption
      that everything in the field of view attenuates like water.

    The honest limitation is the same one every scanner has: the correction is
    **material-specific**. A water calibration applied to a slice containing bone
    or metal over-corrects the dense material and leaves dark bands between dense
    objects, and nothing in the sinogram says which case you are in.

    :param sinogram: ``(n_angles, n_detectors)`` hardened line integrals.
    :param high_energy_fraction: *w* used by the forward model.
    :param attenuation_ratio: *k* used by the forward model.
    :param poly_coeffs: ``(c1, c2, ...)``; when given, the polynomial route is
        used and *w* / *k* are ignored.
    :param n_table: nodes of the inverse table, ``64 .. 1048576``.
    :returns: ``(n_angles, n_detectors)`` float64 corrected sinogram.
    :raises ValueError: as :func:`beam_hardening_apply`, plus an empty or
        non-finite *poly_coeffs*.
    """
    op = "beam_hardening_correct"
    sino = _as_sinogram(sinogram, op)
    if poly_coeffs is not None:
        co = _as_float_array(poly_coeffs, "poly_coeffs", 1 << 10, op)
        co = np.atleast_1d(co)
        if co.ndim != 1 or co.size < 1:
            raise ValueError("%s: poly_coeffs must be a non-empty 1-D sequence "
                             "(c1, c2, ...), got shape %r" % (op, co.shape))
        out = np.zeros_like(sino)
        for power, c in enumerate(co, start=1):
            out += c * sino ** power
        return out
    w = _finite_scalar(high_energy_fraction, "high_energy_fraction")
    k = _finite_scalar(attenuation_ratio, "attenuation_ratio")
    if not (0.0 <= w < 1.0):
        raise ValueError("%s: high_energy_fraction must be in [0, 1), got %g"
                         % (op, w))
    if not (0.0 < k <= 1.0):
        raise ValueError("%s: attenuation_ratio must be in (0, 1], got %g"
                         % (op, k))
    n_tab = _count(n_table, "n_table", 64, 1 << 20)
    if w == 0.0 or k == 1.0:
        return sino.copy()
    if (sino < 0.0).any():
        bad = int((sino < 0.0).sum())
        raise ValueError(
            "%s: the sinogram has %d negative value(s); the hardening curve is "
            "only defined for non-negative line integrals and extrapolating it "
            "would return finite nonsense" % (op, bad))
    hi = float(sino.max())
    # The forward curve saturates: p_meas -> -ln(w) - ... , so the domain of the
    # inverse is bounded. Refuse rather than extrapolate off the end of the table.
    p_max = 1.0
    while -np.log((1.0 - w) * np.exp(-p_max) + w * np.exp(-k * p_max)) < hi:
        p_max *= 2.0
        if p_max > 1e6:
            raise ValueError(
                "%s: the largest measured line integral (%g) is above everything "
                "this (w=%g, k=%g) beam can produce — its hardened output "
                "saturates at %g. Either the parameters are not the ones that "
                "hardened this sinogram, or the data is not in line-integral "
                "units. Extrapolating would invent an attenuation."
                % (op, hi, w, k, -np.log(w) if w > 0 else np.inf))
    grid = np.linspace(0.0, p_max, n_tab)
    meas = -np.log((1.0 - w) * np.exp(-grid) + w * np.exp(-k * grid))
    return np.interp(sino, meas, grid)


def ring_artifact_apply(sinogram, gain_sigma=0.02, seed=0, offsets=None):
    """Give the detector a per-bin gain error — the source of ring artefacts.

    A detector bin whose gain is ``g`` reports ``I = g I_true``, so after the
    logarithm the line integral picks up a **constant offset** ``-ln g`` at that
    bin, the same at every angle. Back-projecting a constant column smears it
    around the rotation axis, and the reconstruction grows a ring at the radius
    that bin's rays are tangent to. One bad pixel, one perfect circle.

    The offsets are drawn once from ``N(0, gain_sigma)`` with a fixed *seed* and
    applied to every row, because the whole point is that the error does **not**
    vary with angle — that is what distinguishes a ring from noise, and what makes
    :func:`ring_artifact_remove` possible.

    :param sinogram: ``(n_angles, n_detectors)``.
    :param gain_sigma: standard deviation of the per-bin offset, ``>= 0``.
    :param seed: RNG seed; there is no ``None`` (determinism is a contract here).
    :param offsets: explicit ``(n_detectors,)`` offsets; overrides the random draw.
    :returns: ``(n_angles, n_detectors)`` float64 sinogram.
    :raises ValueError: on a negative sigma, a non-int seed, or an *offsets* whose
        length is not the detector count.
    """
    op = "ring_artifact_apply"
    sino = _as_sinogram(sinogram, op)
    if offsets is None:
        sig = _nonneg(gain_sigma, "gain_sigma")
        sd = _seed(seed)
        off = np.random.default_rng(sd).normal(0.0, sig, size=sino.shape[1])
    else:
        off = _as_float_array(offsets, "offsets", MAX_DETECTORS, op)
        off = np.atleast_1d(off)
        if off.ndim != 1 or off.size != sino.shape[1]:
            raise ValueError(
                "%s: offsets must be a 1-D array of %d values (one per detector "
                "bin), got shape %r. A per-*angle* array of the same length would "
                "be accepted by broadcasting if this check were absent, and would "
                "add a smooth shading instead of rings — plausible, and wrong."
                % (op, sino.shape[1], off.shape))
    return sino + off[None, :]


def ring_artifact_remove(sinogram, window=5, mode="median"):
    """Remove per-detector-bin offsets by flattening the angle-averaged profile.

    The mean of a sinogram column over all angles is a smooth function of the
    detector position for any object that stays inside the field of view — it is
    essentially the object's mass seen from every side. A gain error adds a
    *constant* to one column, so it appears in that mean as a spike on a smooth
    curve. Smoothing the mean profile and subtracting the difference removes the
    spike and leaves the object.

    Measured on the Shepp-Logan phantom scaled to a peak line integral of 1.18
    (i.e. CT-realistic, see the note below) with ``gain_sigma=0.02``: the
    reconstruction's normalised RMS error against the truth goes 0.0250 (clean)
    -> 0.0643 (with rings) -> **0.0358** (removed at the default window), so
    **72 %** of the damage is undone.

    The window is the whole argument, and it was chosen by measurement rather
    than by taste. Removed fraction, against the damage the same call does to an
    already-clean sinogram:

        window   median: undone / damage    mean: undone / damage
           3       61.0 % / +0.0000           70.4 % / +0.0004
           5       72.3 % / +0.0002           82.6 % / +0.0019
           7       74.3 % / +0.0017           82.4 % / +0.0042
          11       73.6 % / +0.0025           74.0 % / +0.0091
          31       73.3 % / +0.0043           37.4 % / +0.0244
          61       58.2 % / +0.0109            9.0 % / +0.0356

    The default is ``window=5, mode="median"`` because it is the setting that
    removes most of the rings while doing almost nothing to a sinogram that did
    not need it — and *that* is the property that matters, because this operator
    will be run on scans whose rings nobody has measured. ``mean`` at the same
    window removes 10 points more and costs 10x the collateral damage; wide
    windows are worse at both.

    Two failure modes are stated rather than hidden. This **cannot** separate a
    real object feature that is thin in the detector direction and present at
    every angle — the axis of rotation itself is the extreme case — from a gain
    error. And *gain_sigma is in line-integral units*, so how much a given gain
    error matters depends entirely on how large the line integrals are: on the
    same phantom left in raw pixel units (peak line integral 70.9 rather than
    1.18) the identical 2 % gain error changes the reconstruction's error by less
    than 0.0001 and this operator has nothing to do. That is not a bug in either
    place — it is what "2 % of the signal" means when the signal is 60x larger.

    :param sinogram: ``(n_angles, n_detectors)``.
    :param window: smoothing width in detector bins, an **odd** int ``3 .. n_det``.
    :param mode: ``"median"`` (robust, the default) or ``"mean"``.
    :returns: ``(n_angles, n_detectors)`` float64 sinogram.
    :raises ValueError: on an even or out-of-range window, or an unknown mode.
    """
    op = "ring_artifact_remove"
    sino = _as_sinogram(sinogram, op)
    n_det = sino.shape[1]
    win = _count(window, "window", 3, n_det)
    if win % 2 == 0:
        raise ValueError(
            "%s: window must be odd, got %d. An even window has no centre bin, so "
            "the smoothed profile is shifted by half a bin against the profile it "
            "is subtracted from — which *adds* a half-bin derivative to every "
            "projection and reconstructs as a faint edge enhancement that looks "
            "like a sharper image" % (op, win))
    md = _choice(mode, ("median", "mean"), "mode", op)
    prof = sino.mean(axis=0)
    pad = win // 2
    ext = np.pad(prof, pad, mode="edge")
    view = np.lib.stride_tricks.sliding_window_view(ext, win)
    smooth = np.median(view, axis=-1) if md == "median" else view.mean(axis=-1)
    return sino - (prof - smooth)[None, :]


def metal_trace_interpolate(sinogram, angles_deg=None, image_threshold=None,
                            mask=None, size=None):
    """Linear-interpolation metal artefact reduction (LI-MAR).

    A metal implant attenuates so strongly that its detector bins carry almost no
    photons; the measured line integrals there are dominated by scatter and by the
    noise floor of the logarithm, and back-projecting them lays down the dark
    bands and bright streaks between dense objects that make a slice unreadable.

    The oldest working answer, and still the baseline every newer method is
    compared against: declare the affected bins *missing* and fill them by linear
    interpolation along the detector axis, per angle. The result is not the truth
    — it is a smooth guess with the streaks removed — and it blurs whatever was
    genuinely behind the metal.

    **How the affected bins are found matters more than the interpolation, and
    the obvious way is measurably worse than doing nothing.** The metal trace is
    located the way LI-MAR actually does it: reconstruct once with
    :func:`filtered_backprojection`, threshold the *image* at
    ``mean + 3*std``, forward-project that binary mask, and treat the bins it
    touches as missing. Thresholding the **sinogram** directly is the shortcut
    that suggests itself, and on the Shepp-Logan phantom with a 6-px implant it
    goes wrong in the direction that is hardest to notice — it flags the densest
    *legitimate* structure (the skull, seen edge-on) and interpolates it away:

        implant density   uncorrected   sinogram threshold   image threshold
             x8             0.0487           0.0626              0.0255
            x30             0.1583           0.2249              0.0255
           x100             0.5214           0.7127              0.0257

    (normalised RMS error against the metal-free truth, outside the implant
    footprint; the metal-free reconstruction itself scores 0.0250.) The image
    route recovers essentially all of the damage at every density. The sinogram
    route makes it 1.3-1.4x *worse* than not correcting at all, at every density,
    while still producing a picture with fewer visible streaks — which is why the
    shortcut is not offered as an option here rather than merely discouraged.

    Inside the implant footprint the reconstruction is now wrong on purpose: the
    metal is gone. Clinical practice puts it back from the thresholded
    reconstruction afterwards; that step is not implemented.

    :param sinogram: ``(n_angles, n_detectors)``.
    :param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``. Used for the
        internal reconstruction and re-projection, so a wrong angle set here
        misplaces the trace.
    :param image_threshold: image-domain metal threshold; ``None`` ->
        ``mean + 3*std`` of the internal reconstruction.
    :param mask: explicit boolean ``(n_angles, n_detectors)`` metal trace. When
        given, no reconstruction is done and *image_threshold* is ignored — this
        is the route to use when the trace comes from a segmentation you trust.
    :param size: side of the internal reconstruction; ``None`` -> the inscribed
        square.
    :returns: ``(n_angles, n_detectors)`` float64 sinogram.
    :raises ValueError: if the mask shape disagrees with the sinogram, if the mask
        is not boolean, if nothing is left to interpolate from, or if any *row* is
        entirely masked.
    """
    op = "metal_trace_interpolate"
    sino = _as_sinogram(sinogram, op)
    if mask is None:
        ang = _as_angles(angles_deg, sino.shape[0], op)
        sz = _recon_size(size, sino, op)
        rec = filtered_backprojection(sino, ang, size=sz)
        thr = (float(rec.mean() + 3.0 * rec.std()) if image_threshold is None
               else _finite_scalar(image_threshold, "image_threshold"))
        metal_img = (rec > thr).astype(np.float64)
        if not metal_img.any():
            return sino.copy()
        n_det = sino.shape[1]
        trace = _project(metal_img, np.deg2rad(ang), n_det, 1)
        m = trace > 0.5
    else:
        m = np.asarray(mask)
        if m.dtype != np.bool_:
            raise ValueError(
                "%s: mask must be a boolean array, got dtype %r. A float or int "
                "mask would be truthy wherever it is non-zero, which for a "
                "*sinogram-shaped* array is almost everywhere — the operator would "
                "interpolate the entire scan away and return a smooth, finite, "
                "meaningless picture" % (op, m.dtype))
        if m.shape != sino.shape:
            raise ValueError("%s: mask has shape %r, sinogram has %r"
                             % (op, m.shape, sino.shape))
    if not m.any():
        return sino.copy()
    if m.all():
        raise ValueError("%s: every bin is flagged as metal — there is nothing "
                         "left to interpolate from" % (op,))
    full_rows = int(m.all(axis=1).sum())
    if full_rows:
        raise ValueError(
            "%s: %d projection(s) are entirely flagged as metal. Those views carry "
            "no usable data at all, and filling them from their own (empty) "
            "neighbours would fabricate a projection. Drop those angles from the "
            "scan instead, or raise image_threshold" % (op, full_rows))
    out = sino.copy()
    idx = np.arange(sino.shape[1], dtype=np.float64)
    for i in range(sino.shape[0]):
        bad = m[i]
        if not bad.any():
            continue
        good = ~bad
        out[i, bad] = np.interp(idx[bad], idx[good], sino[i, good])
    return out


# --------------------------------------------------------------------------- #
# 5. the axis of rotation                                                      #
# --------------------------------------------------------------------------- #
def sinogram_center_of_rotation(sinogram, angles_deg=None, min_condition=1e-6):
    """Where the axis of rotation actually is, in detector bins from the centre.

    The centre-of-mass identity, which is exact and needs no reconstruction: the
    first moment of a projection is the projection of the object's centre of
    mass, so::

        s_cm(theta) = x0 cos(theta) + y0 sin(theta) + c

    with ``(x0, y0)`` the centre of mass in the slice and ``c`` the offset of the
    rotation axis from the detector centre. Fitting the three unknowns by least
    squares over all views gives *c* directly. Measured on the Shepp-Logan
    phantom with 180 views, recovering a deliberately introduced shift, together
    with the cost of not correcting it (normalised RMS error of the FBP
    reconstruction against the truth):

        true shift   estimated    error     uncorrected   after this fix
          0.00 px    +0.0029 px   0.0029      0.0250          0.0249
          0.50 px    +0.5029 px   0.0029      0.0537          0.0358
          1.00 px    +1.0029 px   0.0029      0.1016          0.0249
          2.00 px    +2.0029 px   0.0029      0.1630          0.0249

    Three things in that table are worth reading twice. **Half a pixel already
    doubles the error** (0.0250 -> 0.0537) and does not look like a mistake — it
    looks like a slightly soft reconstruction, which is why this is a measurement
    and not an inspection. The estimator's own bias is a **constant 0.0029 px**
    across every shift, so it is a property of the phantom and the detector
    sampling, not of the size of the error being measured. And the half-pixel row
    is the only one the fix does not fully repair (0.0358 against 0.0249),
    because correcting a *fractional* shift means resampling, and the linear
    interpolation costs more than the integer shifts do — see
    :func:`sinogram_center_shift`.

    Two things this needs, both refused rather than assumed. The object must be
    **entirely inside the field of view** — the identity is about the whole mass,
    and a truncated object has a different mass at every angle. And the views must
    span enough angle for ``[cos, sin, 1]`` to be independent: over a narrow
    wedge, ``cos(theta)`` and the constant are nearly the same vector and the fit
    puts the object's own offset into *c*. The condition number is checked and a
    degenerate design is refused.

    :param sinogram: ``(n_angles, n_detectors)``, rows = angles.
    :param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``.
    :param min_condition: smallest acceptable reciprocal condition number of the
        3-column design matrix.
    :returns: ``float`` — the axis offset in detector bins, positive towards
        higher bin indices.
    :raises ValueError: on a sinogram whose total mass is zero, on fewer than 3
        views, or on an angular span too narrow to separate the offset from the
        object's own position.
    """
    op = "sinogram_center_of_rotation"
    sino = _as_sinogram(sinogram, op)
    ang = _as_angles(angles_deg, sino.shape[0], op)
    if ang.size < 3:
        raise ValueError("%s: needs at least 3 views to fit (x0, y0, c), got %d"
                         % (op, ang.size))
    rc = _positive(min_condition, "min_condition")
    n_det = sino.shape[1]
    s = np.arange(n_det, dtype=np.float64) - (n_det - 1) / 2.0
    mass = sino.sum(axis=1)
    if not (mass > 0.0).all():
        bad = int((mass <= 0.0).sum())
        raise ValueError(
            "%s: %d projection(s) have zero or negative total mass, so their centre "
            "of mass is undefined (or, worse, defined and meaningless — a mass of "
            "-1e-16 flips the sign of the whole moment). This is a filtered or "
            "background-subtracted sinogram; the identity this operator uses holds "
            "for raw line integrals" % (op, bad))
    s_cm = (sino * s[None, :]).sum(axis=1) / mass
    t = np.deg2rad(ang)
    design = np.column_stack([np.cos(t), np.sin(t), np.ones_like(t)])
    sv = np.linalg.svd(design, compute_uv=False)
    cond = float(sv[-1] / sv[0]) if sv[0] > 0 else 0.0
    if cond < rc:
        raise ValueError(
            "%s: the angle set spans %.1f degrees, over which cos(theta), "
            "sin(theta) and 1 are nearly linearly dependent (reciprocal condition "
            "number %.2e < %.2e). The fit would happily return a number, but it "
            "would be the object's own offset from the axis rather than the axis's "
            "offset from the detector centre — a plausible float with the wrong "
            "meaning. A span of 180 degrees makes the three separable."
            % (op, float(ang.max() - ang.min()), cond, rc))
    coef, *_ = np.linalg.lstsq(design, s_cm, rcond=None)
    return float(coef[2])


def sinogram_center_shift(sinogram, shift_px=None, angles_deg=None):
    """Re-centre a sinogram on its axis of rotation.

    Shifts every projection by ``-shift_px`` along the detector axis with linear
    interpolation. With ``shift_px=None`` the shift is measured first by
    :func:`sinogram_center_of_rotation`, which makes this the one-call fix.

    Round-trip on the Shepp-Logan phantom, shifting by *d* and back:

        d        max |error|    relative to the peak line integral
        1.00 px   0.0e+00        0.0e+00     (an integer shift is exact)
        0.50 px   1.4e-01        1.2e-01
        0.25 px   1.1e-01        9.2e-02

    A *fractional* shift is **not** a small operation and this is the operator's
    honest limitation: 12 % of the peak, on a phantom with sharp edges, from one
    round trip. Interpolation is a low-pass filter and the sinogram of an edge is
    not band-limited, so there is nothing to recover on the way back. Using a
    Fourier shift instead would trade this visible blur for invisible ringing at
    the detector edges, which is worse in the way that matters here. The
    consequence is in :func:`sinogram_center_of_rotation`'s table: an integer
    centre error is fully repairable, a half-pixel one is not.

    :param sinogram: ``(n_angles, n_detectors)``.
    :param shift_px: axis offset in detector bins; ``None`` -> measure it.
    :param angles_deg: view angles, used only when *shift_px* is ``None``.
    :returns: ``(n_angles, n_detectors)`` float64 sinogram.
    :raises ValueError: if ``|shift_px|`` is at or past half the detector width —
        past that the object has been shifted out of the field of view and what
        comes back is edge padding, which reconstructs as a plausible, empty slice.
    """
    op = "sinogram_center_shift"
    sino = _as_sinogram(sinogram, op)
    if shift_px is None:
        sh = sinogram_center_of_rotation(sino, angles_deg)
    else:
        sh = _finite_scalar(shift_px, "shift_px")
    n_det = sino.shape[1]
    if abs(sh) >= n_det / 2.0:
        raise ValueError(
            "%s: shift_px = %g is at or past half the detector width (%d bins). "
            "Every ray of the object would leave the detector and the result would "
            "be edge padding — finite, smooth, and reconstructing to an empty slice "
            "that looks like a failed scan rather than a bad argument"
            % (op, sh, n_det))
    idx = np.arange(n_det, dtype=np.float64)
    src = idx + sh
    out = np.empty_like(sino)
    for i in range(sino.shape[0]):
        out[i] = np.interp(src, idx, sino[i], left=sino[i, 0], right=sino[i, -1])
    return out


# --------------------------------------------------------------------------- #
# 6. the volume route (parallel beam, slice by slice)                          #
# --------------------------------------------------------------------------- #
def radon_volume(volume, angles_deg=None, n_detectors=None, oversample=1):
    """Project every slice of a ``(Z, H, W)`` volume -> a ``(Z, A, D)`` stack.

    Parallel-beam geometry with the rotation axis along ``Z``, which is the case
    where the 3-D problem really is a stack of independent 2-D ones — each slice
    projects into its own sinogram and nothing crosses between them. (A cone beam
    does not have this property and is not implemented; saying so is cheaper than
    a wrong ``FDK``.)

    The output's axis order is ``(slice, angle, detector)`` so that ``stack[k]``
    is a sinogram in this module's own convention and every 2-D operator here
    applies to it unchanged.

    :param volume: ``(Z, H, W)`` float volume, ``Z >= 1``.
    :param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``, 180 views.
    :param n_detectors: bins; ``None`` -> covers the in-plane diagonal.
    :param oversample: ray samples per pixel, ``1 .. 8``.
    :returns: ``(Z, n_angles, n_detectors)`` float64 stack.
    :raises ValueError: on a non-3-D input or a stack over
        :data:`MAX_STACK_ELEMENTS`.
    """
    op = "radon_volume"
    vol = _as_float_array(volume, "volume", MAX_STACK_ELEMENTS, op)
    if vol.ndim != 3:
        raise ValueError("%s: volume must be 3-D (Z, H, W), got ndim=%d shape %r"
                         % (op, vol.ndim, vol.shape))
    z, h, w = vol.shape
    if h < 2 or w < 2:
        raise ValueError("%s: each slice must be at least 2x2, got %r"
                         % (op, vol.shape))
    ang = (np.linspace(0.0, 180.0, 180, endpoint=False) if angles_deg is None
           else _as_angles(angles_deg, None, op))
    n_d = (_default_detectors(h, w) if n_detectors is None
           else _count(n_detectors, "n_detectors", 4, MAX_DETECTORS))
    ov = _count(oversample, "oversample", 1, 8)
    total = z * ang.size * n_d
    if total > MAX_STACK_ELEMENTS:
        raise ValueError(
            "%s: %d slices x %d angles x %d detectors = %d elements, over the %d "
            "cap (~%d MB). The volume can be small and the request still enormous "
            "— the angle count is an argument"
            % (op, z, ang.size, n_d, total, MAX_STACK_ELEMENTS, total * 8 // (1 << 20)))
    diag = np.hypot(h, w)
    if n_d < diag - 1.0:
        raise ValueError(
            "%s: %d detector bins do not cover the %.1f-px in-plane diagonal"
            % (op, n_d, diag))
    rad = np.deg2rad(ang)
    out = np.empty((z, ang.size, n_d), dtype=np.float64)
    for k in range(z):
        out[k] = _project(vol[k], rad, n_d, ov)
    return out


def fbp_volume(stack, angles_deg=None, size=None, filter_name="ramp",
               cutoff=1.0, span_deg=None):
    """Reconstruct every sinogram of a ``(Z, A, D)`` stack -> a ``(Z, S, S)`` volume.

    The inverse of :func:`radon_volume`, slice by slice. The result is a plain
    volume and every existing 3-D operator applies to it directly — windowing,
    labelling, boundary extraction, marching cubes — which is the point of
    returning ``voxel`` rather than something tomography-specific.

    One number worth carrying into that pipeline: the reconstructed slice grid is
    isotropic **in-plane only**. The slice spacing is whatever the scan used, and
    it is usually coarser; the volume itself does not carry it. Passing this
    volume to a measurement without its spacing is the most common way a
    tomographic volume becomes a wrong number — see
    ``examples/tomography_reconstruct.py``, which measures the size of the error.

    :param stack: ``(Z, n_angles, n_detectors)``.
    :param angles_deg: view angles; ``None`` -> uniform ``[0, 180)``.
    :param size: output side per slice; ``None`` -> the inscribed square.
    :param filter_name: one of :data:`FILTERS`.
    :param cutoff: fraction of Nyquist to keep.
    :param span_deg: angular range for the ``d(theta)`` weight.
    :returns: ``(Z, size, size)`` float64 volume.
    :raises ValueError: on a non-3-D stack, or an output over
        :data:`MAX_STACK_ELEMENTS`.
    """
    op = "fbp_volume"
    st = _as_float_array(stack, "stack", MAX_STACK_ELEMENTS, op)
    if st.ndim != 3:
        raise ValueError(
            "%s: stack must be 3-D (slice, angle, detector), got ndim=%d shape %r. "
            "Note this is *not* the (Z, H, W) layout of a reconstructed volume — "
            "the two are both 3-D float arrays and no structural check can tell "
            "them apart, which is why the ledger gives the stack its own sort"
            % (op, st.ndim, st.shape))
    z, n_a, n_d = st.shape
    if n_a < 2 or n_d < 4:
        raise ValueError("%s: each slice needs >= 2 angles and >= 4 detector bins, "
                         "got %r" % (op, st.shape))
    ang = _as_angles(angles_deg, n_a, op)
    sz = _recon_size(size, st[0], op)
    if z * sz * sz > MAX_STACK_ELEMENTS:
        raise ValueError(
            "%s: %d slices x %dx%d = %d elements, over the %d cap"
            % (op, z, sz, sz, z * sz * sz, MAX_STACK_ELEMENTS))
    out = np.empty((z, sz, sz), dtype=np.float64)
    for k in range(z):
        out[k] = filtered_backprojection(st[k], angles_deg=ang, size=sz,
                                         filter_name=filter_name, cutoff=cutoff,
                                         span_deg=span_deg)
    return out

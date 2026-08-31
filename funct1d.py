# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""1-D function (profile / signal) operators — the HALCON ``funct_1d`` family (numpy + scipy).

A *function* here is what HALCON's Tools chapter calls a ``funct_1d``: a finite
sequence of samples ``y[0..n-1]`` on an implicit equidistant x-grid ``x = 0, 1,
..., n-1`` (index units). Gray-value profiles from :mod:`measure`
(``line_profile``), time series from sensors, and evaluation curves all fit this
shape. This module is the *analysis* side: smoothing, differentiation,
integration, zero crossings, local extrema, algebra on y-values, resampling,
composition, inversion, affine transforms and translation matching.

It complements — and does not duplicate — :mod:`signal1d` (polynomial fitting /
FFT filtering / splines) and :mod:`dsp` (acoustic / vibration I/O and spectra):
``funct1d`` is the HALCON-named, index-grid profile toolkit.

HALCON correspondence (one function per operator, genuine numpy implementations):

  =============================  =====================================================
  HALCON operator                This module
  =============================  =====================================================
  ``smooth_funct_1d_gauss``      :func:`smooth_funct_1d_gauss`
  ``smooth_funct_1d_mean``       :func:`smooth_funct_1d_mean`
  ``derivate_funct_1d``          :func:`derivate_funct_1d`
  ``integrate_funct_1d``         :func:`integrate_funct_1d`
  ``zero_crossings_funct_1d``    :func:`zero_crossings_funct_1d`
  ``local_min_max_funct_1d``     :func:`local_min_max_funct_1d`
  ``funct_1d_to_pairs``          :func:`funct_1d_to_pairs`
  ``abs_funct_1d``               :func:`abs_funct_1d`
  ``negate_funct_1d``            :func:`negate_funct_1d`
  ``scale_y_funct_1d``           :func:`scale_y_funct_1d`
  ``compose_funct_1d``           :func:`compose_funct_1d`
  ``num_points_funct_1d``        :func:`num_points_funct_1d`
  ``distance_funct_1d``          :func:`distance_funct_1d`
  ``sample_funct_1d``            :func:`sample_funct_1d`
  ``get_pair_funct_1d``          :func:`get_pair_funct_1d`
  ``invert_funct_1d``            :func:`invert_funct_1d`
  ``transform_funct_1d``         :func:`transform_funct_1d`
  ``x_range_funct_1d``           :func:`x_range_funct_1d`
  ``y_range_funct_1d``           :func:`y_range_funct_1d`
  ``get_y_value_funct_1d``       :func:`get_y_value_funct_1d`
  ``create_funct_1d_array``      :func:`create_funct_1d_array`
  ``create_funct_1d_pairs``      :func:`create_funct_1d_pairs`
  ``match_funct_1d_trans``       :func:`match_funct_1d_trans`
  =============================  =====================================================

Conventions (shared by every function):

  * x is the **sample index** unless a function says otherwise: derivatives are in
    y-units *per sample*, integrals in y-units *times samples*. To convert to
    physical units divide / multiply by the sample spacing ``dt`` yourself.
  * Positions (zero crossings, extrema) are integer sample indices — there is no
    sub-sample interpolation of positions.
  * Every function coerces its input to a float64 numpy array and returns fresh
    arrays (inputs are never modified in place).

Honest limitations (each is documented on the function it concerns):

  * :func:`zero_crossings_funct_1d` uses a strict sign product: a crossing that
    lands **exactly on a zero sample** (e.g. ``[-1, 0, 1]``) is *not* reported.
  * :func:`local_min_max_funct_1d` uses strict inequalities: plateau extrema
    (two equal neighbouring samples at the top) are *not* reported, and the two
    boundary samples are never extrema.
  * :func:`invert_funct_1d` is a true inverse only for monotonic input; a
    non-monotonic function is returned as y-sorted pairs (multi-valued regions
    are interleaved, not resolved).
  * :func:`compose_funct_1d` and :func:`get_y_value_funct_1d` **clamp** x values
    to the domain instead of failing or extrapolating (HALCON errors on
    out-of-domain composition; the clamp is the documented difference).
  * :func:`match_funct_1d_trans` recovers integer translation only (no sub-sample
    shift, no x-scaling), by full cross-correlation of mean-subtracted signals.

Fail-closed on untrusted input: every entry point requires a **1-D** array
(anything else raises ``ValueError``), rejects NaN / Inf samples and parameters
explicitly, and enforces the per-function minimum length stated in its
docstring. A malformed input raises ``ValueError`` naming the problem — it is
never silently coerced into a wrong-but-plausible answer.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = [
    "smooth_funct_1d_gauss", "smooth_funct_1d_mean",
    "derivate_funct_1d", "integrate_funct_1d",
    "zero_crossings_funct_1d", "local_min_max_funct_1d",
    "funct_1d_to_pairs", "abs_funct_1d", "negate_funct_1d", "scale_y_funct_1d",
    "compose_funct_1d", "num_points_funct_1d", "distance_funct_1d",
    "sample_funct_1d", "get_pair_funct_1d", "invert_funct_1d",
    "transform_funct_1d", "x_range_funct_1d", "y_range_funct_1d",
    "get_y_value_funct_1d", "create_funct_1d_array", "create_funct_1d_pairs",
    "match_funct_1d_trans",
    "FUNCT1D_OPS",
]

#: The public 1-D function operators, by name (introspection / facade wiring),
#: same shape as ``volops.VOLOPS``.
FUNCT1D_OPS = [
    "smooth_funct_1d_gauss", "smooth_funct_1d_mean",
    "derivate_funct_1d", "integrate_funct_1d",
    "zero_crossings_funct_1d", "local_min_max_funct_1d",
    "funct_1d_to_pairs", "abs_funct_1d", "negate_funct_1d", "scale_y_funct_1d",
    "compose_funct_1d", "num_points_funct_1d", "distance_funct_1d",
    "sample_funct_1d", "get_pair_funct_1d", "invert_funct_1d",
    "transform_funct_1d", "x_range_funct_1d", "y_range_funct_1d",
    "get_y_value_funct_1d", "create_funct_1d_array", "create_funct_1d_pairs",
    "match_funct_1d_trans",
]


# --------------------------------------------------------------------------- #
# fail-closed validation helpers
# --------------------------------------------------------------------------- #

def _f1d(y, name: str = "y", min_len: int = 0) -> np.ndarray:
    """Coerce *y* to a 1-D float64 array, fail-closed.

    Raises ``ValueError`` if *y* is not 1-D, contains NaN / Inf, or has fewer
    than *min_len* samples.
    """
    arr = np.asarray(y, dtype=float)
    if arr.ndim != 1:
        raise ValueError(
            f"funct_1d input '{name}' must be a 1-D array, got shape {arr.shape}")
    if arr.size and not np.all(np.isfinite(arr)):
        raise ValueError(f"funct_1d input '{name}' contains NaN or Inf")
    if arr.size < min_len:
        raise ValueError(
            f"funct_1d input '{name}' needs at least {min_len} samples, got {arr.size}")
    return arr


def _finite_scalar(v, name: str) -> float:
    """Coerce parameter *v* to a finite float (``ValueError`` otherwise)."""
    try:
        f = float(v)
    except (TypeError, ValueError) as e:
        raise ValueError(f"parameter '{name}' must be a real number, got {v!r}") from e
    if not np.isfinite(f):
        raise ValueError(f"parameter '{name}' must be finite, got {f!r}")
    return f


def _int_param(v, name: str, min_value: int) -> int:
    """Coerce parameter *v* to ``int(v)`` (truncating, as the historical behaviour
    did) and require ``>= min_value``. NaN / Inf / non-numeric raise ``ValueError``."""
    f = _finite_scalar(v, name)
    i = int(f)
    if i < min_value:
        raise ValueError(f"parameter '{name}' must be >= {min_value}, got {i}")
    return i


# --------------------------------------------------------------------------- #
# smoothing
# --------------------------------------------------------------------------- #

def smooth_funct_1d_gauss(y, sigma: float = 1.0):
    """Gaussian smoothing of a 1-D function (HALCON ``smooth_funct_1d_gauss``).

    Convolves *y* with a Gaussian of standard deviation *sigma* (in samples),
    ``reflect`` boundary handling (scipy default). The DC level is preserved;
    zero-mean noise variance shrinks by roughly ``1 / (2 * sigma * sqrt(pi))``.

    :param y: 1-D function, at least 1 sample.
    :param sigma: Gaussian standard deviation in samples; must be finite and > 0.
    :returns: smoothed float64 array, same length as *y*.
    :raises ValueError: non-1-D / NaN / Inf input, empty input, or ``sigma <= 0``.
    """
    arr = _f1d(y, "y", min_len=1)
    s = _finite_scalar(sigma, "sigma")
    if s <= 0.0:
        raise ValueError(f"parameter 'sigma' must be > 0, got {s}")
    return ndimage.gaussian_filter1d(arr, sigma=s)


def smooth_funct_1d_mean(y, size=3, iterations=1):
    """Iterated moving-average smoothing (HALCON ``smooth_funct_1d_mean``).

    Applies a length-*size* uniform (box) filter *iterations* times with
    ``nearest`` (edge-replicating) boundary handling. Repeated box filtering
    approaches a Gaussian (central limit theorem).

    :param y: 1-D function, at least 1 sample.
    :param size: window length in samples; truncated to int, must be >= 1.
        **Even sizes are accepted but shift the window origin by half a sample**
        (scipy's origin convention) — prefer odd sizes for a symmetric window.
    :param iterations: number of passes; truncated to int, must be >= 0.
        ``iterations=0`` returns the (float64-coerced) input unchanged.
    :returns: smoothed float64 array, same length as *y*.
    :raises ValueError: non-1-D / NaN / Inf input, empty input, ``size < 1``,
        or ``iterations < 0``.
    """
    arr = _f1d(y, "y", min_len=1)
    sz = _int_param(size, "size", 1)
    it = _int_param(iterations, "iterations", 0)
    for _ in range(it):
        arr = ndimage.uniform_filter1d(arr, sz, mode="nearest")
    return arr


# --------------------------------------------------------------------------- #
# calculus
# --------------------------------------------------------------------------- #

def derivate_funct_1d(y):
    """First derivative by central differences (HALCON ``derivate_funct_1d``).

    Units are **y per sample** (the x-grid is the index): for a physical signal
    sampled every ``dt`` seconds, divide the result by ``dt``. Interior points
    use the second-order central difference; the two boundary points use one-sided
    differences (``numpy.gradient``).

    :param y: 1-D function, at least 2 samples (a derivative needs a neighbour).
    :returns: float64 array of the same length.
    :raises ValueError: non-1-D / NaN / Inf input, or fewer than 2 samples.
    """
    arr = _f1d(y, "y", min_len=2)
    return np.gradient(arr)


def integrate_funct_1d(y):
    """Cumulative integral by the trapezoidal rule (HALCON ``integrate_funct_1d``).

    ``out[i]`` is the integral of *y* from x=0 to x=i in **y-units times
    samples** (multiply by the physical sample spacing ``dt`` yourself);
    ``out[0]`` is always 0. For smooth signals
    ``integrate_funct_1d(derivate_funct_1d(y)) ~= y - y[0]`` to second order.

    :param y: 1-D function, at least 1 sample (a single sample integrates to ``[0.]``).
    :returns: float64 array of the same length.
    :raises ValueError: non-1-D / NaN / Inf input, or empty input.
    """
    arr = _f1d(y, "y", min_len=1)
    out = np.zeros_like(arr)
    out[1:] = np.cumsum((arr[:-1] + arr[1:]) / 2.0)
    return out


# --------------------------------------------------------------------------- #
# feature extraction
# --------------------------------------------------------------------------- #

def zero_crossings_funct_1d(y):
    """Indices where the function changes sign (HALCON ``zero_crossings_funct_1d``).

    Returns the integer indices ``i`` with ``sign(y[i]) * sign(y[i+1]) < 0`` —
    the sample *before* each crossing. An empty input returns an empty index
    array (degenerate case, not an error).

    Honest limitation: the test is a **strict** sign product, so a crossing that
    lands exactly on a zero sample (``[-1, 0, 1]``) is *not* reported, nor is a
    touch of zero without a sign change (``[1, 0, 1]``).

    :param y: 1-D function (may be empty).
    :returns: int index array (possibly empty).
    :raises ValueError: non-1-D / NaN / Inf input.
    """
    arr = _f1d(y, "y")
    s = np.sign(arr)
    return np.nonzero((s[:-1] * s[1:]) < 0)[0]


def local_min_max_funct_1d(y):
    """Indices of strict local maxima / minima (HALCON ``local_min_max_funct_1d``).

    ``{"max": indices, "min": indices}`` where index ``i`` is a maximum iff
    ``y[i] > y[i-1] and y[i] > y[i+1]`` (mirrored for minima). Inputs shorter
    than 3 samples have no interior point and return two empty arrays
    (degenerate case, not an error).

    Honest limitation: inequalities are **strict** — plateau extrema (equal
    neighbouring samples at the top/bottom) are not reported, and the boundary
    samples ``0`` and ``n-1`` are never extrema.

    :param y: 1-D function (may be empty).
    :returns: dict ``{"max": int array, "min": int array}``.
    :raises ValueError: non-1-D / NaN / Inf input.
    """
    arr = _f1d(y, "y")
    mx = np.nonzero((arr[1:-1] > arr[:-2]) & (arr[1:-1] > arr[2:]))[0] + 1
    mn = np.nonzero((arr[1:-1] < arr[:-2]) & (arr[1:-1] < arr[2:]))[0] + 1
    return {"max": mx, "min": mn}


# --------------------------------------------------------------------------- #
# representation / algebra on y-values
# --------------------------------------------------------------------------- #

def funct_1d_to_pairs(y):
    """The function as explicit ``(x, y)`` pairs (HALCON ``funct_1d_to_pairs``).

    :param y: 1-D function (may be empty).
    :returns: ``(n, 2)`` float64 array, column 0 the index grid ``0..n-1``,
        column 1 the y-values.
    :raises ValueError: non-1-D / NaN / Inf input.
    """
    arr = _f1d(y, "y")
    return np.column_stack([np.arange(len(arr), dtype=float), arr])


def abs_funct_1d(y):
    """Absolute value of the y-values (HALCON ``abs_funct_1d``).

    :param y: 1-D function (may be empty).
    :raises ValueError: non-1-D / NaN / Inf input.
    """
    return np.abs(_f1d(y, "y"))


def negate_funct_1d(y):
    """Sign-flipped y-values (HALCON ``negate_funct_1d``).

    :param y: 1-D function (may be empty).
    :raises ValueError: non-1-D / NaN / Inf input.
    """
    return -_f1d(y, "y")


def scale_y_funct_1d(y, mult=1.0, add=0.0):
    """Linear map of the y-values, ``mult * y + add`` (HALCON ``scale_y_funct_1d``).

    The x-grid is untouched (use :func:`transform_funct_1d` to move x too).

    :param y: 1-D function (may be empty).
    :param mult: finite multiplier.
    :param add: finite offset.
    :raises ValueError: non-1-D / NaN / Inf input, or non-finite parameter.
    """
    arr = _f1d(y, "y")
    m = _finite_scalar(mult, "mult")
    a = _finite_scalar(add, "add")
    return m * arr + a


def compose_funct_1d(y1, y2):
    """Composition ``y1(y2)``: the values of *y2* used as positions into *y1*
    (HALCON ``compose_funct_1d``).

    Each ``y2[i]`` is rounded to the nearest integer and **clamped** into
    ``[0, len(y1) - 1]``, then ``out[i] = y1[that index]``. Nearest-neighbour
    lookup, no interpolation.

    Domain policy (documented difference from HALCON, which errors when the
    range of *y2* leaves the domain of *y1*): out-of-domain positions are
    clamped to the first / last sample of *y1*, never extrapolated. If you need
    the strict check, compare ``y_range_funct_1d(y2)`` against
    ``x_range_funct_1d(y1)`` before composing.

    :param y1: outer function, at least 1 sample.
    :param y2: inner function supplying positions (may be empty).
    :returns: float64 array with the length of *y2*.
    :raises ValueError: non-1-D / NaN / Inf input, or empty *y1*.
    """
    a1 = _f1d(y1, "y1", min_len=1)
    a2 = _f1d(y2, "y2")
    idx = np.clip(np.round(a2).astype(int), 0, len(a1) - 1)
    return a1[idx]


def num_points_funct_1d(y) -> int:
    """Number of samples (HALCON ``num_points_funct_1d``).

    :param y: 1-D function (may be empty).
    :raises ValueError: non-1-D / NaN / Inf input.
    """
    return int(_f1d(y, "y").size)


def distance_funct_1d(y1, y2, mode="max") -> float:
    """Distance between two functions on the same grid (HALCON ``distance_funct_1d``).

    ``mode="max"`` is the Chebyshev / sup distance ``max |y1 - y2|``;
    ``mode="mean"`` the mean absolute difference. Both are symmetric and zero
    iff the functions are identical.

    :param y1: 1-D function, at least 1 sample.
    :param y2: 1-D function, **same length** as *y1* (unequal lengths raise —
        pointwise distance is undefined across different grids; silent numpy
        broadcasting is explicitly rejected).
    :param mode: ``"max"`` or ``"mean"`` (anything else raises).
    :raises ValueError: non-1-D / NaN / Inf input, empty input, length mismatch,
        or unknown *mode*.
    """
    a1 = _f1d(y1, "y1", min_len=1)
    a2 = _f1d(y2, "y2", min_len=1)
    if a1.size != a2.size:
        raise ValueError(
            f"distance_funct_1d needs equal lengths, got {a1.size} and {a2.size}")
    if mode not in ("max", "mean"):
        raise ValueError(f"parameter 'mode' must be 'max' or 'mean', got {mode!r}")
    d = np.abs(a1 - a2)
    return float(d.max() if mode == "max" else d.mean())


def sample_funct_1d(y, step=2):
    """Every *step*-th sample (HALCON ``sample_funct_1d``).

    Keeps samples ``0, step, 2*step, ...`` — decimation without an
    anti-aliasing filter (smooth first if the signal has content above the new
    Nyquist rate).

    :param y: 1-D function (may be empty).
    :param step: truncated to int, must be >= 1 (``step=1`` copies).
    :raises ValueError: non-1-D / NaN / Inf input, or ``step < 1``.
    """
    arr = _f1d(y, "y")
    st = _int_param(step, "step", 1)
    return arr[::st]


def get_pair_funct_1d(y, index=0):
    """The ``(x, y)`` pair at *index* (HALCON ``get_pair_funct_1d``).

    *index* is truncated to int and **clamped** into ``[0, n-1]`` (historical
    behaviour, kept and documented rather than made an error): asking for
    index -3 returns pair 0, asking past the end returns the last pair.

    :param y: 1-D function, at least 1 sample.
    :param index: sample position (clamped).
    :returns: float64 array ``[x, y[x]]``.
    :raises ValueError: non-1-D / NaN / Inf input, empty input, or non-finite *index*.
    """
    arr = _f1d(y, "y", min_len=1)
    raw = int(_finite_scalar(index, "index"))  # finite; range handled by the clamp
    i = int(np.clip(raw, 0, len(arr) - 1))
    return np.array([float(i), float(arr[i])])


def invert_funct_1d(y):
    """Swap the roles of x and y: ``x = f^-1(y)`` (HALCON ``invert_funct_1d``).

    Returns ``{"x": y-values sorted ascending, "y": their original indices}``,
    i.e. the (y, x) pairs ordered so the new abscissa is monotonic — ready for
    ``numpy.interp``-style lookup.

    Honest limitation: this is a true inverse only when *y* is monotonic. A
    non-monotonic function is multi-valued; the sort interleaves its branches
    instead of resolving them (ties keep index order — numpy stable-ish
    argsort). An empty input returns two empty arrays.

    :param y: 1-D function (may be empty).
    :returns: dict ``{"x": float64 array, "y": float64 array}``.
    :raises ValueError: non-1-D / NaN / Inf input.
    """
    arr = _f1d(y, "y")
    x = np.arange(len(arr), dtype=float)
    order = np.argsort(arr, kind="stable")
    return {"x": arr[order], "y": x[order]}


def transform_funct_1d(y, mult_x=1.0, add_x=0.0, mult_y=1.0, add_y=0.0):
    """Independent affine transform of x and y (HALCON ``transform_funct_1d``).

    Returns explicit pairs ``(mult_x * i + add_x, mult_y * y[i] + add_y)`` for
    ``i = 0..n-1``. Note ``mult_x = 0`` collapses the abscissa to a single
    point (accepted; the result is then not a function of x).

    :param y: 1-D function (may be empty).
    :param mult_x, add_x, mult_y, add_y: finite affine coefficients.
    :returns: ``(n, 2)`` float64 array of ``(x, y)`` pairs.
    :raises ValueError: non-1-D / NaN / Inf input, or non-finite parameter.
    """
    arr = _f1d(y, "y")
    mx = _finite_scalar(mult_x, "mult_x")
    ax = _finite_scalar(add_x, "add_x")
    my = _finite_scalar(mult_y, "mult_y")
    ay = _finite_scalar(add_y, "add_y")
    x = np.arange(len(arr), dtype=float)
    return np.column_stack([mx * x + ax, my * arr + ay])


def x_range_funct_1d(y):
    """The x-domain ``(0.0, n - 1.0)`` (HALCON ``x_range_funct_1d``).

    :param y: 1-D function, at least 1 sample (an empty function has no domain).
    :raises ValueError: non-1-D / NaN / Inf input, or empty input.
    """
    arr = _f1d(y, "y", min_len=1)
    return (0.0, float(arr.size - 1))


def y_range_funct_1d(y):
    """The value range ``(min(y), max(y))`` (HALCON ``y_range_funct_1d``).

    :param y: 1-D function, at least 1 sample.
    :raises ValueError: non-1-D / NaN / Inf input, or empty input.
    """
    arr = _f1d(y, "y", min_len=1)
    return (float(arr.min()), float(arr.max()))


def get_y_value_funct_1d(y, x, interpolate=True):
    """The y-value at (fractional) position *x* (HALCON ``get_y_value_funct_1d``).

    With ``interpolate=True`` (default) the value is linearly interpolated
    between the two neighbouring samples; with ``interpolate=False`` the nearest
    sample is returned.

    Domain policy (documented, not extrapolated): *x* outside ``[0, n-1]``
    **clamps** to the boundary value (``numpy.interp`` end-hold semantics /
    index clip). HALCON's ``'zero'``-border variant is not offered.

    :param y: 1-D function, at least 1 sample.
    :param x: finite scalar position in index units.
    :param interpolate: linear interpolation (True) or nearest sample (False).
    :returns: float.
    :raises ValueError: non-1-D / NaN / Inf input, empty input, or non-finite *x*.
    """
    arr = _f1d(y, "y", min_len=1)
    xf = _finite_scalar(x, "x")
    if interpolate:
        return float(np.interp(xf, np.arange(len(arr)), arr))
    i = int(np.clip(round(xf), 0, len(arr) - 1))
    return float(arr[i])


# --------------------------------------------------------------------------- #
# construction
# --------------------------------------------------------------------------- #

def create_funct_1d_array(y):
    """A 1-D function from equidistant samples (HALCON ``create_funct_1d_array``).

    Pure validation + float64 coercion: the returned array *is* the function,
    on the implicit index grid. Accepts an empty sequence (an empty function).

    :param y: 1-D sample sequence.
    :raises ValueError: non-1-D / NaN / Inf input.
    """
    return _f1d(y, "y")


def create_funct_1d_pairs(x, y):
    """A 1-D function from arbitrary ``(x, y)`` pairs, resampled to an
    equidistant grid (HALCON ``create_funct_1d_pairs``).

    The pairs are sorted by x and linearly interpolated onto the **integer**
    grid ``floor(min(x)) .. ceil(max(x))`` (step 1). Grid points outside the
    convex hull of the data (only the two end points can be) hold the nearest
    sample's value — ``numpy.interp`` end-hold, no extrapolation. Duplicate x
    values keep numpy's interp behaviour (the segment between duplicates is a
    step). Note the returned function's index 0 corresponds to physical
    ``x = floor(min(x))``, not necessarily 0.

    :param x: 1-D abscissa values, at least 1 pair, finite.
    :param y: 1-D ordinate values, same length as *x*, finite.
    :returns: float64 array on the integer grid.
    :raises ValueError: non-1-D / NaN / Inf input, empty input, or length mismatch.
    """
    ax = _f1d(x, "x", min_len=1)
    ay = _f1d(y, "y", min_len=1)
    if ax.size != ay.size:
        raise ValueError(
            f"create_funct_1d_pairs needs len(x) == len(y), got {ax.size} and {ay.size}")
    order = np.argsort(ax, kind="stable")
    ax, ay = ax[order], ay[order]
    xi = np.arange(int(np.floor(ax.min())), int(np.ceil(ax.max())) + 1)
    return np.interp(xi, ax, ay)


# --------------------------------------------------------------------------- #
# matching
# --------------------------------------------------------------------------- #

def match_funct_1d_trans(y1, y2):
    """Best integer translation between two functions by cross-correlation
    (HALCON ``match_funct_1d_trans``, translation only).

    Both signals are mean-subtracted, then the full cross-correlation is taken;
    the returned ``shift`` is the lag of its peak, with the convention

        ``y1[i] ~= y2[i - shift]``

    i.e. if *y2* is *y1* delayed (rolled right) by ``s`` samples, ``shift`` is
    ``-s``. ``score`` is the raw (unnormalised) correlation value at the peak —
    it is invariant in *position* under positive y-scaling of either input, but
    its magnitude scales with amplitude and overlap length; compare scores only
    between candidates of the same length.

    Honest limitations: integer lag only (no sub-sample refinement), no x-scale
    or y-offset model beyond the mean subtraction, and a length-1 input
    degenerates to ``shift 0, score 0`` (mean subtraction leaves nothing).
    Because the correlation is **unnormalised**, a strong amplitude envelope
    (e.g. an exponentially decaying oscillation) can bias the peak by a few
    samples toward the high-amplitude overlap; whiten first (e.g. match the
    :func:`derivate_funct_1d` of both signals) when the envelope is not flat —
    ``examples/signal_funct1d.py`` demonstrates exact recovery this way.

    :param y1: 1-D function, at least 1 sample.
    :param y2: 1-D function, at least 1 sample (lengths may differ).
    :returns: dict ``{"shift": int, "score": float}``.
    :raises ValueError: non-1-D / NaN / Inf input, or empty input.
    """
    a = _f1d(y1, "y1", min_len=1)
    b = _f1d(y2, "y2", min_len=1)
    a = a - a.mean()
    b = b - b.mean()
    corr = np.correlate(a, b, mode="full")
    shift = int(corr.argmax() - (len(b) - 1))
    return {"shift": shift, "score": float(corr.max())}

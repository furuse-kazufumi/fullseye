"""3-D virtual probe measurement — 1-D edge metrology along a line through a volume.

The 3-D counterpart of the 2-D 1-D caliper package (:mod:`measure` /
:mod:`backends_measure1d`, HALCON's *measure* operators): fit a virtual probe
(a straight line between two voxel-space points) into a ``(D, H, W)`` volume,
sample the gray-value profile along it, locate sub-sample edges as extrema of
the Gaussian-smoothed derivative, and pair opposite-polarity edges into wall
thicknesses. This is the core measurement of industrial CT: probe a casting or
an additively-manufactured part along a surface normal and read off the wall /
coating thickness directly, without segmenting the whole volume.

Frame convention (shared with :mod:`volio` / :mod:`volops`): a volume is a
``(D, H, W)`` float64 array indexed ``[z, y, x]``; points are ``(z, y, x)``
voxel coordinates (fractional allowed); ``spacing`` is ``(sz, sy, sx)`` in
millimetres, lined up with those axes (a :class:`volio.VolumeMeta` may be
passed wherever ``spacing`` is accepted). All returned distances (``t_mm``)
are *physical* distances from the probe start — millimetres when a spacing is
given, voxel units otherwise. Anisotropic spacing is handled exactly: the
distance of each sample is the Euclidean norm of the difference of the
*physical* coordinates (``index * spacing``), so an oblique probe through
(2, 1, 1)-spaced voxels reports true geometric length, not index length.

Edge model (matching the 2-D measure1d package): the profile is smoothed with
a 1-D Gaussian (``sigma``, in **samples**), differentiated with respect to the
physical abscissa ``t_mm``, and local extrema of ``|d gray / d t|`` are edges.
Each extremum is refined to sub-sample precision by a 3-point parabolic fit on
the derivative magnitude; twin peaks closer than 1.5 samples (the plateau a
grid-sampled step produces) are merged, keeping the strongest. Edge *polarity*
is the sign of the derivative along the probe direction p0 -> p1 (+1 rising =
dark -> bright, -1 falling = bright -> dark).

Honest limitations:

  * **Edge localisation accuracy is bounded by the profile resolution and
    ``sigma``.** The default sampling is ~1 voxel-step; a *binary* voxelised
    surface can only be located to the midpoint between the last background
    and first foreground sample (inherent ~half-voxel uncertainty). Sub-voxel
    accuracy requires gray-value (partial-volume / anti-aliased) data, and a
    large ``sigma`` merges edges closer than a few samples.
  * **``threshold`` is an absolute derivative amplitude** in intensity per
    physical distance unit (per mm when a spacing is given, per voxel
    otherwise) — it is *not* normalised to the profile's own maximum, unlike
    the relative thresholds of the 2-D ``m1_*`` ops. Data that is not in a
    known intensity range needs a user-chosen threshold; note the same
    physical edge yields a *smaller* amplitude at coarser spacing (the
    intensity step spreads over a longer physical distance).
  * ``sigma`` is expressed in **samples** (profile resolution), not
    millimetres, so its physical extent varies with spacing and probe
    direction under anisotropic voxels.
  * The probe is a pure line — there is no perpendicular band averaging (the
    2-D ``measure_projection`` band), so single-voxel noise lands directly on
    the profile; smooth noisy volumes first or raise ``sigma``.
  * ``vol_wall_thickness`` pairs *rising -> falling* edges in order (bright
    material on a dark background, the industrial-CT convention). Edges that
    do not complete such a pair — a probe ending inside material, an inverted
    (dark cavity) polarity sequence — are silently ignored, not paired
    creatively; probe dark-walled data with an inverted volume.

Fail-closed on untrusted input, per the :mod:`volops` contract: entry points
require a 3-D ``(D, H, W)`` array, coerce to float64, reject NaN / Inf, cap
the voxel count before heavy work, and reject probe endpoints outside the
volume, coincident endpoints, and malformed parameters with a ``ValueError``
naming the problem.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter1d, map_coordinates

__all__ = [
    "vol_profile_line", "vol_edge_probe", "vol_wall_thickness",
    "VOLPROBE_OPS", "MAX_VOXELS",
]

#: The public virtual-probe operators, by name (introspection / facade wiring).
VOLPROBE_OPS = ["vol_profile_line", "vol_edge_probe", "vol_wall_thickness"]

#: Refuse a volume larger than this (same cap as :data:`volops.MAX_VOXELS`,
#: ~134 M voxels = 1 GiB as float64).
MAX_VOXELS = 1 << 27

#: Merge derivative peaks closer than this many *samples* — a step sampled on
#: the grid yields a two-sample derivative plateau whose halves both refine to
#: the same sub-sample position (same constant as the 2-D measure1d package).
_MERGE_SEP = 1.5


# --------------------------------------------------------------------------- #
# fail-closed input helpers (contract identical to volops)                     #
# --------------------------------------------------------------------------- #
def _require_volume(vol, name: str = "vol") -> np.ndarray:
    """Coerce to a contiguous ``(D, H, W)`` float64 array or raise ``ValueError``.

    Rejects anything that is not exactly 3-D and any NaN / Inf — a poisoned
    voxel would silently corrupt the interpolated profile and every derived
    edge position."""
    v = np.ascontiguousarray(vol, dtype=np.float64)
    if v.ndim != 3:
        raise ValueError("%s must be a 3-D (D, H, W) volume, got a %d-D array of shape %r"
                         % (name, v.ndim, tuple(np.shape(vol))))
    if not np.isfinite(v).all():
        n = int((~np.isfinite(v)).sum())
        raise ValueError("%s has %d non-finite voxel(s) (NaN/Inf) — refusing "
                         "(they would poison the interpolated profile)" % (name, n))
    if v.size > MAX_VOXELS:
        raise ValueError("%s: a %d-voxel volume (shape %r) exceeds the %d cap "
                         "(volprobe.MAX_VOXELS) — crop to an ROI or downsample first"
                         % (name, v.size, v.shape, MAX_VOXELS))
    return v


def _spacing_tuple(spacing, name: str = "spacing"):
    """Normalise a spacing argument to ``(sz, sy, sx)`` floats, or ``None``.

    Accepts a 3-tuple *or* a :class:`volio.VolumeMeta` (whose ``spacing_mm``
    is already ``(sz, sy, sx)``). Same behaviour as ``volops._spacing_tuple``."""
    if spacing is None:
        return None
    if hasattr(spacing, "spacing_mm"):
        spacing = spacing.spacing_mm
    try:
        sp = tuple(float(s) for s in spacing)
    except (TypeError, ValueError):
        raise ValueError("%s must be a length-3 (sz, sy, sx) sequence or a "
                         "VolumeMeta, got %r" % (name, spacing)) from None
    if len(sp) != 3 or any(not np.isfinite(s) or s <= 0.0 for s in sp):
        raise ValueError("%s must be 3 positive finite values (sz, sy, sx), got %r"
                         % (name, sp))
    return sp


def _point3(p, shape, name: str) -> np.ndarray:
    """Validate a ``(z, y, x)`` voxel-coordinate point (fractional allowed).

    Fail-closed: a point outside ``[0, dim-1]`` on any axis raises
    ``ValueError`` — the probe must lie entirely inside the volume, so that no
    sample is an extrapolated (fabricated) intensity."""
    try:
        q = tuple(float(c) for c in p)
    except (TypeError, ValueError):
        raise ValueError("%s must be a (z, y, x) coordinate triple, got %r"
                         % (name, p)) from None
    if len(q) != 3 or any(not np.isfinite(c) for c in q):
        raise ValueError("%s must be 3 finite (z, y, x) values, got %r" % (name, q))
    for c, dim, ax in zip(q, shape, "zyx"):
        if c < 0.0 or c > dim - 1:
            raise ValueError("%s %s-coordinate %g is outside the volume "
                             "(valid range [0, %d]) — refusing to extrapolate"
                             % (name, ax, c, dim - 1))
    return np.array(q, np.float64)


def _exact_int(x, name: str) -> int:
    """*x* as an exact integer or ``ValueError`` — a 1.9 must never be silently
    truncated to a different interpolation order / sample count (same
    convention as ``volxform._check_order``)."""
    try:
        f = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s must be an integer, got %r" % (name, x)) from None
    if not np.isfinite(f) or f != int(f):
        raise ValueError("%s must be an exact integer (never truncated), got %r"
                         % (name, x))
    return int(f)


# --------------------------------------------------------------------------- #
# 1) intensity profile along the probe                                        #
# --------------------------------------------------------------------------- #
def vol_profile_line(vol, p0, p1, n=None, spacing=None, order=1):
    """Gray-value profile along the straight probe ``p0 -> p1``.

    The segment between the two ``(z, y, x)`` voxel-space points (fractional
    coordinates allowed) is sampled at ``n`` evenly-spaced positions with
    spline interpolation of the given ``order`` (``scipy.ndimage.map_coordinates``;
    1 = trilinear, the default). ``n`` defaults to one sample per unit of
    *index-space* length (~1 voxel-step resolution regardless of spacing).

    Parameters
    ----------
    vol : (D, H, W) array — the volume (float64, finite; fail-closed otherwise).
    p0, p1 : (z, y, x) — probe start / end, inside the volume on every axis.
    n : int, optional — sample count (>= 2). Default ``ceil(index_length) + 1``.
    spacing : (sz, sy, sx) or volio.VolumeMeta, optional — voxel size in mm.
    order : int in [0, 5] — interpolation spline order (1 = trilinear).

    Returns
    -------
    (t_mm, values) : two float64 arrays of length ``n``. ``t_mm[i]`` is the
    *physical* distance of sample ``i`` from ``p0`` — the cumulative Euclidean
    norm of the differences of the physical sample coordinates
    (``index * spacing``), exact under anisotropic spacing; in plain voxel
    units when ``spacing`` is None. ``values[i]`` is the interpolated gray
    value.

    Raises ``ValueError`` on a malformed volume, an endpoint outside the
    volume, coincident endpoints (``p0 == p1``: no probe direction), ``n < 2``
    or an invalid ``order`` / ``spacing``.
    """
    v = _require_volume(vol, "vol")
    a = _point3(p0, v.shape, "p0")
    b = _point3(p1, v.shape, "p1")
    sp = _spacing_tuple(spacing)
    sp_arr = np.array(sp if sp is not None else (1.0, 1.0, 1.0), np.float64)

    d_idx = b - a
    length_idx = float(np.linalg.norm(d_idx))
    if length_idx <= 1e-12:
        raise ValueError("p0 and p1 coincide (index-space length %g) — the probe "
                         "has no direction" % length_idx)
    if n is None:
        n = max(2, int(np.ceil(length_idx)) + 1)
    else:
        n = _exact_int(n, "n")                        # 5.7 is rejected, never truncated
        if n < 2:
            raise ValueError("n must be >= 2 samples, got %d" % n)
        if n > MAX_VOXELS:
            raise ValueError("n=%d exceeds the %d cap (volprobe.MAX_VOXELS)"
                             % (n, MAX_VOXELS))
    order = _exact_int(order, "order")                # 1.9 is rejected, never truncated
    if order < 0 or order > 5:
        raise ValueError("order must be an integer in [0, 5], got %d" % order)

    ts = np.linspace(0.0, 1.0, n)
    coords = a[None, :] + ts[:, None] * d_idx[None, :]      # (n, 3) index coords
    values = map_coordinates(v, [coords[:, 0], coords[:, 1], coords[:, 2]],
                             order=order, mode="nearest")
    # Physical abscissa: cumulative norm of physical-coordinate differences —
    # exact for anisotropic spacing and oblique probes (not index length).
    phys = coords * sp_arr[None, :]
    seg = np.linalg.norm(np.diff(phys, axis=0), axis=1)
    t_mm = np.concatenate([[0.0], np.cumsum(seg)])
    return t_mm, np.asarray(values, np.float64)


# --------------------------------------------------------------------------- #
# 2) sub-sample edges on the profile                                          #
# --------------------------------------------------------------------------- #
def vol_edge_probe(vol, p0, p1, sigma=1.0, threshold=0.1, spacing=None,
                   polarity="all"):
    """Sub-sample edges along the probe ``p0 -> p1``.

    The profile (default sampling of :func:`vol_profile_line`) is smoothed
    with a 1-D Gaussian of ``sigma`` **samples**, differentiated with respect
    to the physical abscissa ``t_mm``, and local extrema of the derivative
    magnitude are taken as edges. Each is refined to sub-sample precision by a
    3-point parabolic fit; plateau twins closer than 1.5 samples are merged.

    ``threshold`` is an **absolute** derivative amplitude in intensity per
    physical distance unit (per mm when ``spacing`` is given, per voxel
    otherwise) — edges with ``|d gray / d t| < threshold`` at the peak are
    discarded. It is *not* relative to the profile's own maximum: choose it
    for your data's intensity range and spacing.

    ``polarity`` selects ``"positive"`` (rising, dark -> bright along the
    probe), ``"negative"`` (falling) or ``"all"``.

    Returns a list of dicts ordered by distance, each::

        {"t_mm":      physical distance of the edge from p0,
         "position":  (z, y, x) interpolated voxel coordinate of the edge,
         "amplitude": |d gray / d t| at the peak (intensity / distance unit),
         "polarity":  +1 rising, -1 falling}

    Raises ``ValueError`` on the same malformed inputs as
    :func:`vol_profile_line`, a negative / non-finite ``sigma`` or
    ``threshold``, or an unknown ``polarity``.
    """
    if polarity not in ("positive", "negative", "all"):
        raise ValueError('polarity must be "positive", "negative" or "all", got %r'
                         % (polarity,))
    sigma = float(sigma)
    if not np.isfinite(sigma) or sigma < 0.0:
        raise ValueError("sigma must be a finite value >= 0 (samples), got %r" % sigma)
    threshold = float(threshold)
    if not np.isfinite(threshold) or threshold < 0.0:
        raise ValueError("threshold must be a finite value >= 0 "
                         "(intensity per distance unit), got %r" % threshold)

    t_mm, values = vol_profile_line(vol, p0, p1, spacing=spacing, order=1)
    n = len(values)
    smoothed = (gaussian_filter1d(values, sigma, mode="nearest")
                if sigma > 0.0 and n >= 3 else values)
    g = np.gradient(smoothed, t_mm)                     # d gray / d t (physical)
    ag = np.abs(g)

    # Local maxima of |g| with 3-point parabolic sub-sample refinement.
    raw = []                                            # (index, amplitude, sign)
    for i in range(1, n - 1):
        if ag[i] >= ag[i - 1] and ag[i] >= ag[i + 1] and ag[i] > 1e-12 \
                and ag[i] >= threshold:
            den = ag[i - 1] - 2.0 * ag[i] + ag[i + 1]
            delta = 0.5 * (ag[i - 1] - ag[i + 1]) / den if abs(den) > 1e-12 else 0.0
            delta = float(np.clip(delta, -1.0, 1.0))
            raw.append((i + delta, float(ag[i]), 1.0 if g[i] >= 0.0 else -1.0))

    # Merge plateau twins (< _MERGE_SEP samples apart), keeping the strongest.
    merged = []
    for pos, amp, sign in raw:                          # raw is index-ordered
        if merged and pos - merged[-1][0] < _MERGE_SEP:
            if amp > merged[-1][1]:
                merged[-1] = [pos, amp, sign]
        else:
            merged.append([pos, amp, sign])

    a = _point3(p0, np.shape(vol), "p0")
    b = _point3(p1, np.shape(vol), "p1")
    d_idx = b - a
    idx_axis = np.arange(n, dtype=np.float64)
    out = []
    for pos, amp, sign in merged:
        if polarity == "positive" and sign < 0.0:
            continue
        if polarity == "negative" and sign > 0.0:
            continue
        frac = pos / (n - 1)
        point = a + frac * d_idx
        out.append({
            "t_mm": float(np.interp(pos, idx_axis, t_mm)),
            "position": (float(point[0]), float(point[1]), float(point[2])),
            "amplitude": float(amp),
            "polarity": int(sign),
        })
    return out


# --------------------------------------------------------------------------- #
# 3) wall thickness = paired rising -> falling edges                          #
# --------------------------------------------------------------------------- #
def vol_wall_thickness(vol, p0, p1, sigma=1.0, threshold=0.1, spacing=None):
    """Wall thicknesses along the probe ``p0 -> p1`` — the industrial-CT
    measurement itself.

    Runs :func:`vol_edge_probe` (all polarities) and pairs consecutive
    opposite-polarity edges *rising -> falling* in probe order: each pair is
    one traversal of bright material (entry surface -> exit surface), and its
    thickness is the difference of the two edges' ``t_mm`` (physical units —
    mm with a spacing, voxels without). A probe crossing both walls of a pipe
    therefore yields two thicknesses.

    Edges that do not complete a rising -> falling pair (a probe starting or
    ending inside material, consecutive same-polarity edges) are **ignored**,
    not paired creatively — the count of returned thicknesses can be smaller
    than ``len(edges) // 2``. Dark walls on a bright background need an
    inverted volume (the pairing convention is bright material).

    Returns a list of float thicknesses, in probe order (possibly empty).
    Raises ``ValueError`` on the same malformed inputs as
    :func:`vol_edge_probe`.
    """
    edges = vol_edge_probe(vol, p0, p1, sigma=sigma, threshold=threshold,
                           spacing=spacing, polarity="all")
    thicknesses = []
    i = 0
    while i < len(edges) - 1:
        if edges[i]["polarity"] > 0 and edges[i + 1]["polarity"] < 0:
            thicknesses.append(float(edges[i + 1]["t_mm"] - edges[i]["t_mm"]))
            i += 2
        else:
            i += 1
    return thicknesses

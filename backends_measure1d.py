"""1-D caliper / projection measurement along a line (image -> feature / contour).

HALCON's *measure* package fits a 1-D measure object (a line or arc) onto an image
and analyses the gray-value profile sampled along it: `measure_projection` (the
1-D projection of the measure rectangle), `measure_pos` (sub-pixel edge
positions), `measure_thresh` (profile crossings of a gray-value threshold),
`measure_pairs` (rising/falling edge pairs), and `fuzzy_measure_pos` (edges
selected by a fuzzy membership score).  This module reproduces those genuinely
and exposes them as ``m1_*`` ops.

Geometry (shared by every op):
  * The caliper line runs *edge to edge* across the image.  ``a`` sets its
    orientation ``theta = a*pi``; the line direction is ``d = (sin theta, cos
    theta)`` in (row, col) and the perpendicular is ``n = (-cos theta, sin
    theta)``.  The line passes through the image centre, shifted along ``n`` by a
    perpendicular offset.  The infinite line is clipped to the image rectangle
    (Liang-Barsky) and the visible segment is bilinearly sampled at ~1 px
    spacing, giving a 1-D intensity profile.
  * Edges along the profile are the peaks of ``|d/ds gray|`` after a small
    Gaussian smoothing (HALCON's ``Sigma``); each peak is refined to sub-pixel by
    a 3-tap parabola on the gradient magnitude, and its polarity is the sign of
    the gradient (rising = dark->bright, falling = bright->dark).

Per-op use of ``b``:
  * ``m1_measure_projection`` — ``b`` is the perpendicular *offset* (0..1, 0.5 =
    centred) of the caliper line; the op band-averages perpendicular to the line
    (the true projection) and returns the projection's mean gray value -> feature.
  * ``m1_measure_pos`` — centred line; ``b`` is the (relative) minimum edge
    amplitude.  Sub-pixel edge positions -> contour (one point per edge, in
    (row, col)); the primary result is the edge count (``count_contours``).
  * ``m1_measure_thresh`` — centred line; ``b`` is the gray-value threshold.
    Number of times the raw profile crosses level ``b`` -> feature.
  * ``m1_measure_pairs`` — centred line; ``b`` is the (relative) edge amplitude.
    Number of rising->falling edge PAIRS (bright objects) -> feature.
  * ``m1_fuzzy_measure_pos`` — centred line; each edge gets a fuzzy amplitude
    membership score in [0, 1]; edges with score >= ``b`` are kept -> contour.

Same contract as the other backend modules: ``build()`` returns typed ``Op``
wrappers, each exception-safe, deterministic and finite.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter1d, map_coordinates

_SMOOTH_SIGMA = 1.0          # profile Gaussian smoothing (HALCON "Sigma")
_MERGE_SEP = 1.5             # merge gradient peaks closer than this (px)


# --------------------------------------------------------------------------- #
# Input coercion.                                                             #
# --------------------------------------------------------------------------- #
def _as_image(v):
    """Coerce input to a 2-D float64 image in [0, 1]; None if not usable."""
    x = np.asarray(v, np.float64)
    if x.ndim == 3:
        x = x.mean(-1)
    if x.ndim != 2 or x.shape[0] < 2 or x.shape[1] < 2:
        return None
    x = np.nan_to_num(x, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(x, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# Line clipping and profile sampling.                                        #
# --------------------------------------------------------------------------- #
def _clip_line(c0, d, H, W):
    """Clip the infinite line ``c0 + t*d`` to [0, H-1] x [0, W-1].

    Returns (tmin, tmax) arc-length range (``d`` is unit, so ``t`` is pixels) or
    None when the line misses the image.
    """
    tmin, tmax = -np.inf, np.inf
    for pos, dd, hi in ((c0[0], d[0], H - 1), (c0[1], d[1], W - 1)):
        if abs(dd) < 1e-12:
            if pos < 0.0 or pos > hi:
                return None
        else:
            t0 = (0.0 - pos) / dd
            t1 = (hi - pos) / dd
            lo, hh = (t0, t1) if t0 <= t1 else (t1, t0)
            tmin = max(tmin, lo)
            tmax = min(tmax, hh)
    if not (np.isfinite(tmin) and np.isfinite(tmax)) or tmax <= tmin:
        return None
    return tmin, tmax


def _sample(img, a, offset01, band=0.0):
    """Sample the intensity profile along the caliper line.

    Returns a dict with the 1-D ``prof`` plus the line geometry (``c0``, ``d``,
    ``tmin``, ``ds``) so a fractional profile index maps back to (row, col), or
    None when the clipped segment is shorter than 2 px.
    """
    H, W = img.shape
    theta = float(np.clip(a, 0.0, 1.0)) * np.pi
    d = np.array([np.sin(theta), np.cos(theta)], np.float64)   # (dr, dc), unit
    n = np.array([-np.cos(theta), np.sin(theta)], np.float64)  # perpendicular
    center = np.array([(H - 1) / 2.0, (W - 1) / 2.0], np.float64)
    extent = float(min(H - 1, W - 1))
    shift = (float(np.clip(offset01, 0.0, 1.0)) - 0.5) * extent
    c0 = center + shift * n
    clip = _clip_line(c0, d, H, W)
    if clip is None:
        return None
    tmin, tmax = clip
    length = tmax - tmin
    if length < 2.0:
        return None
    N = max(2, int(round(length)) + 1)
    ts = tmin + np.linspace(0.0, length, N)
    if band <= 0.0:
        rows = c0[0] + ts * d[0]
        cols = c0[1] + ts * d[1]
        prof = map_coordinates(img, [rows, cols], order=1, mode="nearest")
    else:
        k = max(1, int(round(band)))
        ws = np.linspace(-band, band, 2 * k + 1)
        acc = np.zeros(N, np.float64)
        for w in ws:
            cc = c0 + w * n
            rows = cc[0] + ts * d[0]
            cols = cc[1] + ts * d[1]
            acc += map_coordinates(img, [rows, cols], order=1, mode="nearest")
        prof = acc / len(ws)
    prof = np.nan_to_num(np.asarray(prof, np.float64), nan=0.0, posinf=1.0, neginf=0.0)
    return {"prof": prof, "c0": c0, "d": d, "tmin": tmin, "ds": length / (N - 1)}


# --------------------------------------------------------------------------- #
# Edge extraction on the 1-D profile.                                        #
# --------------------------------------------------------------------------- #
def _merge_peaks(edges):
    """Merge gradient peaks closer than ``_MERGE_SEP`` px, keeping the strongest.

    A step sampled on the integer grid yields a two-sample gradient plateau; both
    samples parabola-refine to the same sub-pixel position, so merging collapses
    them into a single edge.
    """
    if not edges:
        return []
    edges = sorted(edges, key=lambda e: e[0])
    merged = [list(edges[0])]
    for pos, amp, sign in edges[1:]:
        if pos - merged[-1][0] < _MERGE_SEP:
            if amp > merged[-1][1]:
                merged[-1] = [pos, amp, sign]
        else:
            merged.append([pos, amp, sign])
    return [tuple(e) for e in merged]


def _profile_edges(prof):
    """Sub-pixel edges of a 1-D profile: (pos_index, amplitude, sign) list.

    ``sign`` = +1 rising (dark->bright), -1 falling (bright->dark).
    """
    p = np.asarray(prof, np.float64)
    if p.size >= 3:
        p = gaussian_filter1d(p, _SMOOTH_SIGMA, mode="nearest")
    g = np.gradient(p)
    ag = np.abs(g)
    out = []
    for i in range(1, len(ag) - 1):
        if ag[i] >= ag[i - 1] and ag[i] >= ag[i + 1] and ag[i] > 1e-9:
            den = ag[i - 1] - 2.0 * ag[i] + ag[i + 1]
            delta = 0.5 * (ag[i - 1] - ag[i + 1]) / den if abs(den) > 1e-12 else 0.0
            delta = float(np.clip(delta, -1.0, 1.0))
            out.append((i + delta, float(ag[i]), 1.0 if g[i] >= 0.0 else -1.0))
    return _merge_peaks(out)


def _index_to_rc(samp, idx):
    """Map a fractional profile index back to an (row, col) point on the line."""
    t = samp["tmin"] + idx * samp["ds"]
    r = samp["c0"][0] + t * samp["d"][0]
    c = samp["c0"][1] + t * samp["d"][1]
    return float(r), float(c)


def _points_dict(shape, pts):
    """Wrap (row, col) points as a CONTOUR dict (one 1x2 sub-contour per point)."""
    H, W = shape
    cs = []
    for r, c in pts:
        if np.isfinite(r) and np.isfinite(c):
            r = float(np.clip(r, 0.0, H - 1))
            c = float(np.clip(c, 0.0, W - 1))
            cs.append(np.array([[r, c]], np.float64))
    return {"shape": (int(H), int(W)), "cs": cs}


def _empty_contour(v):
    img = _as_image(v)
    shp = img.shape if img is not None else (1, 1)
    return {"shape": (int(shp[0]), int(shp[1])), "cs": []}


# --------------------------------------------------------------------------- #
# Module-level op functions (so tests can call them directly).               #
# --------------------------------------------------------------------------- #
def m1_measure_projection(v, a, b):
    """Mean gray value of the 1-D projection of the caliper band (feature)."""
    img = _as_image(v)
    if img is None:
        return np.float64(0.0)
    samp = _sample(img, a, b, band=1.0)   # b = perpendicular offset
    if samp is None:
        return np.float64(0.0)
    val = float(np.mean(samp["prof"]))
    if not np.isfinite(val):
        return np.float64(0.0)
    return np.float64(np.clip(val, 0.0, 1.0))


def m1_measure_pos(v, a, b):
    """Sub-pixel positions of the strongest edges along the centred line (contour)."""
    img = _as_image(v)
    if img is None:
        return _empty_contour(v)
    samp = _sample(img, a, 0.5)
    if samp is None:
        return _empty_contour(v)
    edges = _profile_edges(samp["prof"])
    if not edges:
        return _points_dict(img.shape, [])
    gmax = max(e[1] for e in edges)
    thr = max(1e-6, float(np.clip(b, 0.0, 1.0)) * gmax)
    pts = [_index_to_rc(samp, pos) for (pos, amp, _s) in edges if amp >= thr]
    return _points_dict(img.shape, pts)


def m1_measure_thresh(v, a, b):
    """Number of times the profile crosses gray-value level ``b`` (feature)."""
    img = _as_image(v)
    if img is None:
        return np.float64(0.0)
    samp = _sample(img, a, 0.5)
    if samp is None:
        return np.float64(0.0)
    level = float(np.clip(b, 0.0, 1.0))
    sgn = np.sign(samp["prof"] - level)
    nz = sgn[sgn != 0.0]
    if nz.size < 2:
        return np.float64(0.0)
    return np.float64(int(np.count_nonzero(np.diff(nz) != 0.0)))


def m1_measure_pairs(v, a, b):
    """Number of rising->falling edge pairs (bright objects) along the line (feature)."""
    img = _as_image(v)
    if img is None:
        return np.float64(0.0)
    samp = _sample(img, a, 0.5)
    if samp is None:
        return np.float64(0.0)
    edges = _profile_edges(samp["prof"])
    if len(edges) < 2:
        return np.float64(0.0)
    gmax = max(e[1] for e in edges)
    thr = max(1e-6, float(np.clip(b, 0.0, 1.0)) * gmax)
    es = [e for e in edges if e[1] >= thr]
    count = 0
    i = 0
    while i < len(es) - 1:
        if es[i][2] > 0.0 and es[i + 1][2] < 0.0:   # rising then falling
            count += 1
            i += 2
        else:
            i += 1
    return np.float64(count)


def m1_fuzzy_measure_pos(v, a, b):
    """Edges kept by a fuzzy amplitude membership score >= ``b`` (contour)."""
    img = _as_image(v)
    if img is None:
        return _empty_contour(v)
    samp = _sample(img, a, 0.5)
    if samp is None:
        return _empty_contour(v)
    edges = _profile_edges(samp["prof"])
    if not edges:
        return _points_dict(img.shape, [])
    gmax = max(e[1] for e in edges)
    if gmax <= 1e-9:
        return _points_dict(img.shape, [])
    lo = 0.05 * gmax
    thr = float(np.clip(b, 0.0, 1.0))
    pts = []
    for pos, amp, _s in edges:
        mu = float(np.clip((amp - lo) / (gmax - lo) if gmax > lo else 1.0, 0.0, 1.0))
        if mu >= thr:
            pts.append(_index_to_rc(samp, pos))
    return _points_dict(img.shape, pts)


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Return the 1-D caliper measurement ops (image -> feature / contour)."""
    def _safe_feature(fn):
        def w(v, a, b):
            try:
                out = fn(v, a, b)
                val = np.float64(out)
                if not np.isfinite(val):
                    return np.float64(0.0)
                return val
            except Exception:
                return np.float64(0.0)
        return w

    def _safe_contour(fn):
        def w(v, a, b):
            try:
                out = fn(v, a, b)
            except Exception:
                out = None
            if isinstance(out, dict) and "cs" in out and "shape" in out:
                return out
            return _empty_contour(v)
        return w

    return [
        Op("m1_measure_projection", "measure1d", "measure_projection", IMAGE, FEATURE, _safe_feature(m1_measure_projection)),
        Op("m1_measure_pos", "measure1d", "measure_pos", IMAGE, CONTOUR, _safe_contour(m1_measure_pos)),
        Op("m1_measure_thresh", "measure1d", "measure_thresh", IMAGE, FEATURE, _safe_feature(m1_measure_thresh)),
        Op("m1_measure_pairs", "measure1d", "measure_pairs", IMAGE, FEATURE, _safe_feature(m1_measure_pairs)),
        Op("m1_fuzzy_measure_pos", "measure1d", "fuzzy_measure_pos", IMAGE, CONTOUR, _safe_contour(m1_fuzzy_measure_pos)),
    ]

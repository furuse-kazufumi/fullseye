"""Binary-region operators, round 3 (registry tier, prefix ``r3_``).

Genuine region-processing operators over binary region masks, each implementing the
algorithm named by a real, previously-uncovered HALCON operator (verified against
``data/halcon_graph.json``: every non-empty ``halcon`` name below has ``covered =
False`` there).  Every op is a module-level ``fn(v, a, b)`` so tests can call it
directly; the tier is assembled by :func:`build`, which the caller wires into the op
registry.  ``build`` wraps each fn in a sort-aware, exception-safe guard so a fn can
never raise into the registry and always returns a contract-valid result.

Region contract: input/return is a 2-D float64 mask (0/1) in [0,1] with the SAME shape
as the input; feature ops return a finite scalar float64.  All fns are deterministic
and fail-soft on empty / const / tiny / malformed input (never raise).

Honesty notes
-------------
* ``r3_rank_region`` implements the GENUINE HALCON ``rank_region`` — a *morphological
  rank operator* (a pixel is set iff at least ``number`` of the pixels in a
  ``width x height`` window belong to the region; ``number = w*h`` => erosion,
  ``number = 1`` => dilation).  This deliberately differs from a "keep the k-th
  component by area" reading, which would neither match ``rank_region`` nor add new
  coverage (that behaviour is already the ``sort_region`` op in ``backends_regions2``).
* ``r3_polar_trans_region`` returns a REGION (per the real operator's ``-> HObject``
  return), even though the graph's ``sort_out_hint`` heuristically says "feature".
* ``r3_region_features`` / ``r3_runlength_distribution`` return a single scalar because
  the FEATURE sort is scalar; they compute a genuine member of the operator's output
  (a shape feature; a summary of the run-length distribution).  Same modelling choice
  as ``r2_runlength_features`` in the sibling tier.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

# HALCON operators intentionally NOT implemented in this tier (with honest reason).
SKIPPED: dict[str, str] = {}


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def _as_mask(v) -> np.ndarray:
    """Coerce any region-ish input to a 2-D boolean foreground mask (fail-soft)."""
    a = np.asarray(v, dtype=np.float64)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(1, -1)
    elif a.ndim > 2:
        a = a.reshape(a.shape[0], -1)
    return np.isfinite(a) & (a > 0.5)


def _as_gray(v) -> np.ndarray:
    """Coerce input to a finite 2-D float64 array clipped to [0,1] (fail-soft)."""
    a = np.asarray(v, dtype=np.float64)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(1, -1)
    elif a.ndim > 2:
        a = a.reshape(a.shape[0], -1)
    a = np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=0.0)
    return np.clip(a, 0.0, 1.0)


def _clip01(a: np.ndarray) -> np.ndarray:
    return np.clip(np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)


def _knob(x) -> float:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return 0.5
    if not np.isfinite(x):
        return 0.5
    return min(1.0, max(0.0, x))


def _row_runs(row: np.ndarray):
    """Return (starts, lengths) of maximal True runs in a 1-D boolean row."""
    padded = np.concatenate(([0], row.astype(np.int8), [0]))
    d = np.diff(padded)
    starts = np.where(d == 1)[0]
    ends = np.where(d == -1)[0]
    return starts, ends - starts


def _all_run_lengths(m: np.ndarray) -> np.ndarray:
    """All horizontal foreground run lengths across every row of ``m`` (bool)."""
    lengths: list[int] = []
    for row in m:
        if row.any():
            _, lens = _row_runs(row)
            lengths.extend(lens.tolist())
    return np.asarray(lengths, dtype=np.float64)


# --------------------------------------------------------------------------- #
# operators
# --------------------------------------------------------------------------- #
def r3_background_seg(v, a, b):
    """Connected components of the background of the region (HALCON background_seg).

    The background is the complement of the foreground; its connected components are
    labelled and returned as a mask.  ``a`` acts as a relative area filter: components
    smaller than ``a * (largest background component)`` are dropped (``a = 0`` returns
    the full background, i.e. the exact ``background_seg`` result).
    """
    m = _as_mask(v)
    bg = ~m
    out = np.zeros(m.shape, np.float64)
    lab, n = ndimage.label(bg)
    if n == 0:
        return out
    sizes = ndimage.sum(np.ones_like(lab, dtype=np.float64), lab,
                        index=np.arange(1, n + 1))
    thresh = _knob(a) * float(sizes.max())
    keep = np.zeros(m.shape, dtype=bool)
    for i, s in enumerate(sizes, start=1):
        if s >= thresh:
            keep |= (lab == i)
    out[keep] = 1.0
    return _clip01(out)


def r3_clip_region(v, a, b):
    """Clip the region to a central rectangle (HALCON clip_region).

    ``a`` = kept fraction of the height, ``b`` = kept fraction of the width; the window
    is centred.  Region pixels outside the window are removed.
    """
    m = _as_mask(v)
    h, w = m.shape
    wh = max(1, int(round(_knob(a) * h)))
    ww = max(1, int(round(_knob(b) * w)))
    r0 = (h - wh) // 2
    c0 = (w - ww) // 2
    out = np.zeros(m.shape, np.float64)
    out[r0:r0 + wh, c0:c0 + ww] = m[r0:r0 + wh, c0:c0 + ww].astype(np.float64)
    return _clip01(out)


def r3_eliminate_runs(v, a, b):
    """Remove horizontal foreground runs shorter than a threshold (eliminate_runs).

    A pixel survives only if it belongs to a horizontal run of length ``>= min_len``,
    where ``min_len = 1 + max(1, round(a*8))`` (a small pixel count).  Thin one-pixel
    bridges (runs of length 1) are severed at ``a = 0`` (min_len = 2).
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    if not m.any():
        return out
    min_len = 1 + max(1, int(round(_knob(a) * 8)))
    for i, row in enumerate(m):
        if not row.any():
            continue
        starts, lens = _row_runs(row)
        for s, ln in zip(starts, lens):
            if ln >= min_len:
                out[i, s:s + ln] = 1.0
    return _clip01(out)


def r3_rank_region(v, a, b):
    """Morphological rank operator over the region (GENUINE HALCON rank_region).

    A pixel is set iff at least ``number`` of the pixels in a ``sz x sz`` window belong
    to the region.  ``sz`` (odd, 3..7) comes from ``a``; ``number`` from ``b`` as a
    fraction of the window area (>= 1).  ``number = sz*sz`` => erosion, ``number = 1``
    => dilation, intermediate => rank/median filtering.
    """
    m = _as_mask(v).astype(np.int64)
    sz = 1 + 2 * max(1, int(round(_knob(a) * 3)))          # 3,5,7
    area = sz * sz
    number = int(round(_knob(b) * area))
    number = min(area, max(1, number))
    kernel = np.ones((sz, sz), dtype=np.int64)
    count = ndimage.convolve(m, kernel, mode="constant", cval=0)
    return _clip01((count >= number).astype(np.float64))


def r3_region_features(v, a, b):
    """Region -> feature: a genuine HALCON shape feature (region_features).

    ``a < 0.5`` returns the normalised area (foreground fraction); ``a >= 0.5`` returns
    the compactness ``P^2 / (4*pi*A)`` (== 1 for an ideal disk, 16/(4*pi) ~ 1.273 for a
    square, and grows with elongation), where ``P`` is the 4-connected edge perimeter.
    """
    m = _as_mask(v)
    area = float(m.sum())
    if area == 0.0:
        return np.float64(0.0)
    if _knob(a) < 0.5:
        return np.float64(area / float(m.size))
    lost = float(np.sum(m[:, 1:] & m[:, :-1]) + np.sum(m[1:, :] & m[:-1, :]))
    perim = 4.0 * area - 2.0 * lost
    comp = (perim * perim) / (4.0 * np.pi * area)
    return np.float64(comp if np.isfinite(comp) else 0.0)


def r3_runlength_distribution(v, a, b):
    """Region -> feature: summary of the horizontal run-length distribution.

    ``a < 0.5`` returns the (population) variance of run lengths; ``a >= 0.5`` returns
    the Shannon entropy (bits) of the run-length histogram.  Both are genuine scalar
    summaries of the distribution produced by HALCON runlength_distribution.
    """
    m = _as_mask(v)
    lengths = _all_run_lengths(m)
    if lengths.size == 0:
        return np.float64(0.0)
    if _knob(a) < 0.5:
        return np.float64(float(np.var(lengths)))
    _, counts = np.unique(lengths, return_counts=True)
    p = counts.astype(np.float64) / float(counts.sum())
    ent = -float(np.sum(p * np.log2(p)))
    return np.float64(ent if np.isfinite(ent) else 0.0)


def r3_select_region_point(v, a, b):
    """Keep the connected component containing the point at (a*H, b*W) (select_region_point).

    If the addressed pixel is background, the result is empty.
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    h, w = m.shape
    r = min(h - 1, max(0, int(round(_knob(a) * (h - 1)))))
    c = min(w - 1, max(0, int(round(_knob(b) * (w - 1)))))
    lab, n = ndimage.label(m)
    if n == 0:
        return out
    lv = int(lab[r, c])
    if lv > 0:
        out[lab == lv] = 1.0
    return _clip01(out)


def r3_partition_dynamic(v, a, b):
    """Partition the region horizontally at columns of small vertical extent (partition_dynamic).

    Columns whose foreground density is positive but ``<= a * max_density`` are treated
    as necks and cleared, splitting the region there.  A region of uniform density has
    no such columns and is returned unchanged.
    """
    m = _as_mask(v)
    out = m.astype(np.float64).copy()
    if not m.any():
        return np.zeros(m.shape, np.float64)
    density = m.sum(axis=0).astype(np.float64)
    cols = np.where(density > 0)[0]
    c0, c1 = int(cols.min()), int(cols.max())
    maxd = float(density[c0:c1 + 1].max())
    thresh = _knob(a) * maxd
    interior = np.arange(c0 + 1, c1)                       # never cut the two ends
    for j in interior:
        if 0.0 < density[j] <= thresh:
            out[:, j] = 0.0
    return _clip01(out)


def r3_polar_trans_region(v, a, b):
    """Polar remap of the region about its centroid (polar_trans_region).

    Output rows are the radial axis (0..``rmax``), output columns the angular axis
    (0..``angle_end``).  ``a`` scales the radial extent, ``b`` the angular sweep.  Output
    keeps the input shape.  Nearest-neighbour sampling.
    """
    m = _as_mask(v)
    out = np.zeros(m.shape, np.float64)
    if not m.any():
        return out
    h, w = m.shape
    ys, xs = np.where(m)
    cy = float(ys.mean())
    cx = float(xs.mean())
    rmax = float(np.sqrt((((ys - cy) ** 2) + ((xs - cx) ** 2)).max())) * (0.25 + 0.75 * _knob(a))
    angle_end = 2.0 * np.pi * (0.25 + 0.75 * _knob(b))
    ii, jj = np.mgrid[0:h, 0:w].astype(np.float64)
    r = rmax * ii / max(h - 1, 1)
    th = angle_end * jj / max(w - 1, 1)
    sr = np.rint(cy - r * np.sin(th)).astype(np.int64)
    sc = np.rint(cx + r * np.cos(th)).astype(np.int64)
    ok = (sr >= 0) & (sr < h) & (sc >= 0) & (sc < w)
    vals = np.zeros(m.shape, dtype=bool)
    vals[ok] = m[sr[ok], sc[ok]]
    out[vals] = 1.0
    return _clip01(out)


def r3_label_to_region(v, a, b):
    """Extract the region of pixels sharing one gray value from a label image (label_to_region).

    Distinct positive gray values (rounded to 3 decimals) are the labels, sorted
    ascending; the label at index ``round(a * maxlabel)`` is selected and its pixels are
    returned as a mask.  A plain 0/1 mask has a single label and yields its foreground.
    """
    arr = _as_gray(v)
    q = np.round(arr, 3)
    levels = np.unique(q[q > 0.0])
    out = np.zeros(arr.shape, np.float64)
    if levels.size == 0:
        return out
    k = min(levels.size - 1, max(0, int(round(_knob(a) * (levels.size - 1)))))
    target = float(levels[k])
    out[q == target] = 1.0
    return _clip01(out)


# --------------------------------------------------------------------------- #
# registry assembly
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Return the r3_ binary-region operator tier (each fn sort-aware & exception-safe)."""
    cat = "region"
    defs = [
        ("r3_background_seg", "background_seg", REGION, REGION, r3_background_seg),
        ("r3_clip_region", "clip_region", REGION, REGION, r3_clip_region),
        ("r3_eliminate_runs", "eliminate_runs", REGION, REGION, r3_eliminate_runs),
        ("r3_rank_region", "rank_region", REGION, REGION, r3_rank_region),
        ("r3_region_features", "region_features", REGION, FEATURE, r3_region_features),
        ("r3_runlength_distribution", "runlength_distribution", REGION, FEATURE,
         r3_runlength_distribution),
        ("r3_select_region_point", "select_region_point", REGION, REGION,
         r3_select_region_point),
        ("r3_partition_dynamic", "partition_dynamic", REGION, REGION, r3_partition_dynamic),
        ("r3_polar_trans_region", "polar_trans_region", REGION, REGION,
         r3_polar_trans_region),
        ("r3_label_to_region", "label_to_region", REGION, REGION, r3_label_to_region),
    ]

    def _wrap(fn, osort):
        def inner(v, a, b):
            try:
                out = fn(v, a, b)
            except Exception:
                out = None
            if osort == FEATURE:
                try:
                    f = float(out)
                except (TypeError, ValueError):
                    return np.float64(0.0)
                return np.float64(f if np.isfinite(f) else 0.0)
            # region output: enforce shape / dtype / 0-1 domain, fail-soft to zeros
            shape = _as_mask(v).shape
            if not isinstance(out, np.ndarray) or out.shape != shape:
                return np.zeros(shape, np.float64)
            return _clip01(np.where(out > 0.5, 1.0, 0.0)).astype(np.float64)
        inner.__name__ = getattr(fn, "__name__", "op")
        return inner

    return [Op(name, cat, halcon, isort, osort, _wrap(fn, osort))
            for (name, halcon, isort, osort, fn) in defs]

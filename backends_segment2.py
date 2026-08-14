"""Adaptive / unsupervised segmentation operators (registry tier, prefix ``sg_``).

Every op *fits its parameters at call time* — the "Python x ML" angle: rather than
applying a fixed threshold, each operator learns a partition of the pixels (EM for a
Gaussian mixture, Lloyd iterations for k-means, a graph cut for the spectral split,
a superpixel over-segmentation for SLIC / Felzenszwalb, a flood from a seed, or a
gradient watershed).  Inputs are grayscale images (``in_sort = image``); outputs are
region masks (``out_sort = region``) — either the segmented object region or the
boundary lattice of an over-segmentation, as documented per op.

Honesty notes
-------------
* **Every op carries ``halcon = ""``** — these are NEW capabilities with no genuine,
  currently-uncovered HALCON analog:
  - ``slic_superpixels`` / ``felzenszwalb`` / ``gmm_segment`` / ``kmeans_intensity`` /
    ``normalized_cut_2`` / ``watershed_gradient`` — no matching HALCON operator name
    exists in ``data/halcon_graph.json``.
  - ``region_growing_seeded`` implements a seeded flood/region-grow.  The natural
    HALCON name ``regiongrowing`` **is already covered** (verified: it is
    ``covered = True`` in the graph AND present in ``ops.REGISTRY``), so claiming it
    here would be a duplicate/false coverage claim.  Hence ``halcon = ""``.

Region contract: fns return a 2-D float64 0/1 mask with the SAME shape as the input
image.  All fns are deterministic and fail-soft on empty / const / tiny / malformed
input (never raise); :func:`build` additionally wraps every fn so it can never raise
into the registry and always returns a contract-valid mask.
"""
from __future__ import annotations

import warnings

import numpy as np
from scipy import ndimage

try:  # heavy but standard deps; fail-soft to zeros if somehow unavailable
    import scipy.linalg as _sla
    from skimage.filters import sobel as _sobel
    from skimage.morphology import h_minima as _h_minima
    from skimage.segmentation import (
        felzenszwalb as _felzenszwalb,
    )
    from skimage.segmentation import (
        find_boundaries as _find_boundaries,
    )
    from skimage.segmentation import (
        slic as _slic,
    )
    from skimage.segmentation import (
        watershed as _watershed,
    )
    _HAVE_SKI = True
except Exception:  # pragma: no cover - deps present in this project
    _HAVE_SKI = False

# HALCON operators intentionally NOT implemented in this tier (with honest reason).
SKIPPED: dict[str, str] = {}


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# operators
# --------------------------------------------------------------------------- #
def sg_slic_superpixels(v, a, b):
    """SLIC superpixel over-segmentation; return the boundary lattice (region).

    ``a`` controls compactness/size jointly: larger ``a`` => larger, more compact
    superpixels (fewer segments, higher compactness).  The returned mask is the
    outer boundary of the SLIC label image — a lattice that tiles the plane into
    superpixels and, at low compactness, snaps to intensity edges (so it encloses
    the objects present).
    """
    g = _as_gray(v)
    if not _HAVE_SKI or g.shape[0] < 4 or g.shape[1] < 4:
        return np.zeros(g.shape, np.float64)
    ka = _knob(a)
    n_seg = max(2, int(round(6 + (1.0 - ka) * 40)))
    compactness = 0.01 + ka * 0.2
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        labels = _slic(g, n_segments=n_seg, compactness=compactness,
                       channel_axis=None, start_label=1)
        bnd = _find_boundaries(labels, mode="outer")
    return bnd.astype(np.float64)


def sg_felzenszwalb(v, a, b):
    """Felzenszwalb graph-based segmentation; return the region boundaries.

    ``a`` sets the ``scale`` (larger => larger clusters, coarser segmentation); ``b``
    sets the minimum component size.  The returned mask is the outer boundary of the
    resulting label image, which follows the true object contours.
    """
    g = _as_gray(v)
    if not _HAVE_SKI or g.shape[0] < 4 or g.shape[1] < 4:
        return np.zeros(g.shape, np.float64)
    scale = 40.0 + _knob(a) * 500.0
    min_size = int(round(15 + _knob(b) * 85))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        labels = _felzenszwalb(g, scale=scale, sigma=0.5, min_size=min_size)
        bnd = _find_boundaries(labels, mode="outer")
    return bnd.astype(np.float64)


def _em_two_gaussian(x: np.ndarray):
    """Deterministic 1-D 2-component Gaussian-mixture EM.

    Returns ``(mean_lo, mean_hi, resp_hi)`` where ``resp_hi`` is the posterior
    responsibility of the higher-mean component for every sample.  Initialised from
    the 25th/75th percentiles (no randomness => deterministic).
    """
    m0, m1 = float(np.percentile(x, 25)), float(np.percentile(x, 75))
    if m1 <= m0:
        m0, m1 = float(x.min()), float(x.max())
    var = max(float(np.var(x)), 1e-4)
    v0 = v1 = var
    w0 = w1 = 0.5
    r1 = np.full(x.shape, 0.5)
    for _ in range(100):
        p0 = w0 / np.sqrt(2.0 * np.pi * v0) * np.exp(-((x - m0) ** 2) / (2.0 * v0))
        p1 = w1 / np.sqrt(2.0 * np.pi * v1) * np.exp(-((x - m1) ** 2) / (2.0 * v1))
        s = p0 + p1
        s[s < 1e-300] = 1e-300
        r1 = p1 / s
        r0 = 1.0 - r1
        n0, n1 = float(r0.sum()), float(r1.sum())
        if n0 < 1e-6 or n1 < 1e-6:
            break
        m0n = float((r0 * x).sum() / n0)
        m1n = float((r1 * x).sum() / n1)
        v0 = max(float((r0 * (x - m0n) ** 2).sum() / n0), 1e-4)
        v1 = max(float((r1 * (x - m1n) ** 2).sum() / n1), 1e-4)
        w0, w1 = n0 / x.size, n1 / x.size
        if abs(m0n - m0) + abs(m1n - m0) < 1e-9 and abs(m1n - m1) < 1e-9:
            m0, m1 = m0n, m1n
            break
        m0, m1 = m0n, m1n
    if m1 >= m0:
        return m0, m1, r1
    return m1, m0, 1.0 - r1


def sg_gmm_segment(v, a, b):
    """2-class Gaussian-mixture (EM on intensity) segmentation -> brighter region.

    A 2-component 1-D Gaussian mixture is fit to the pixel intensities by EM; the
    component with the higher mean is the "bright" class.  A pixel joins the bright
    region when its posterior responsibility for that class is >= a threshold derived
    from ``a`` (``t = 0.25 + 0.5*a``; ``a`` therefore tunes how confidently a pixel
    must belong to the bright class).
    """
    g = _as_gray(v)
    x = g.ravel()
    if x.size < 4 or float(np.ptp(x)) < 1e-6:
        return np.zeros(g.shape, np.float64)
    _, _, resp_hi = _em_two_gaussian(x)
    t = 0.25 + 0.5 * _knob(a)
    return (resp_hi.reshape(g.shape) >= t).astype(np.float64)


def sg_kmeans_intensity(v, a, b):
    """k-means on intensity (k = 2 + round(a*4)); return the brightest cluster.

    Lloyd's algorithm is run on the 1-D intensity values with ``k = 2 + round(a*4)``
    clusters (deterministic init from evenly spaced intensity percentiles).  The
    region of the cluster with the highest centroid (brightest) is returned.
    """
    g = _as_gray(v)
    x = g.ravel()
    k = 2 + int(round(_knob(a) * 4))
    if x.size < k or float(np.ptp(x)) < 1e-6:
        return np.zeros(g.shape, np.float64)
    cents = np.percentile(x, np.linspace(5.0, 95.0, k))
    labels = np.zeros(x.shape, dtype=np.int64)
    for _ in range(100):
        d = np.abs(x[:, None] - cents[None, :])
        labels = d.argmin(axis=1)
        new = np.array([x[labels == j].mean() if np.any(labels == j) else cents[j]
                        for j in range(k)], dtype=np.float64)
        if np.allclose(new, cents, atol=1e-9):
            cents = new
            break
        cents = new
    bright = int(cents.argmax())
    return (labels.reshape(g.shape) == bright).astype(np.float64)


def sg_region_growing_seeded(v, a, b):
    """Seeded flood / region-grow from the central pixel with tolerance ``a``.

    Starting from the image-centre seed, the region is the connected component of all
    pixels whose intensity is within ``+/- a`` of the seed's intensity (homogeneity
    criterion).  ``b`` selects connectivity: 8-connected when ``b > 0.5``, else
    4-connected.
    """
    g = _as_gray(v)
    h, w = g.shape
    if h < 1 or w < 1:
        return np.zeros(g.shape, np.float64)
    sr, sc = h // 2, w // 2
    tol = _knob(a)
    seed_val = float(g[sr, sc])
    within = np.abs(g - seed_val) <= tol
    conn = 2 if _knob(b) > 0.5 else 1
    struct = ndimage.generate_binary_structure(2, conn)
    lab, n = ndimage.label(within, structure=struct)
    out = np.zeros(g.shape, np.float64)
    if n > 0 and lab[sr, sc] > 0:
        out[lab == lab[sr, sc]] = 1.0
    return out


def sg_normalized_cut_2(v, a, b):
    """2-way spectral / normalized-cut split of a downsampled intensity graph.

    The image is downsampled, an affinity graph ``W_ij = exp(-dI^2/sig_i^2) *
    exp(-dx^2/sig_x^2)`` is built over the small grid, and the Fiedler vector (2nd
    eigenvector of the generalised problem ``(D-W)y = lambda D y``, Shi & Malik) is
    thresholded at its median to split the pixels into two groups.  The brighter
    group is returned as the region, upsampled (nearest) to the full resolution.
    ``a`` sets the intensity bandwidth ``sig_i``; ``b`` sets the downsample resolution.
    """
    g = _as_gray(v)
    H, W = g.shape
    if not _HAVE_SKI or H < 2 or W < 2:
        return np.zeros(g.shape, np.float64)
    sdim = int(round(10 + _knob(b) * 14))
    zy = max(1, int(np.ceil(H / sdim)))
    zx = max(1, int(np.ceil(W / sdim)))
    small = g[::zy, ::zx]
    sh, sw = small.shape
    n = sh * sw
    if n < 2:
        return np.zeros(g.shape, np.float64)
    ii, jj = np.mgrid[0:sh, 0:sw]
    coords = np.stack([ii.ravel(), jj.ravel()], axis=1).astype(np.float64)
    inten = small.ravel()
    sig_i = 0.05 + _knob(a) * 0.5
    sig_x = max(sh, sw) / 2.0
    di = inten[:, None] - inten[None, :]
    dx2 = ((coords[:, None, :] - coords[None, :, :]) ** 2).sum(axis=2)
    aff = np.exp(-(di ** 2) / (sig_i ** 2)) * np.exp(-dx2 / (sig_x ** 2))
    deg = aff.sum(axis=1)
    D = np.diag(deg)
    try:
        _, vecs = _sla.eigh(D - aff, D)
    except Exception:
        return np.zeros(g.shape, np.float64)
    if vecs.shape[1] < 2:
        return np.zeros(g.shape, np.float64)
    fiedler = vecs[:, 1]
    side = (fiedler > np.median(fiedler)).reshape(sh, sw)
    # orient so the region is the brighter side
    if side.any() and (~side).any() and small[side].mean() < small[~side].mean():
        side = ~side
    yi = np.minimum(np.arange(H) // zy, sh - 1)
    xi = np.minimum(np.arange(W) // zx, sw - 1)
    big = side[np.ix_(yi, xi)]
    return big.astype(np.float64)


def sg_watershed_gradient(v, a, b):
    """Gradient-magnitude watershed from h-minima markers (marker depth ``a``).

    The Sobel gradient magnitude is computed and normalised; regional minima that
    survive an h-minima transform of depth ``h = 0.02 + a*0.3`` become the watershed
    markers (larger ``a`` => fewer, deeper markers => coarser segmentation).  The
    watershed of the gradient is computed from those markers and its boundary lattice
    (the dam lines separating catchment basins / objects) is returned as the region.
    """
    g = _as_gray(v)
    if not _HAVE_SKI or g.shape[0] < 4 or g.shape[1] < 4:
        return np.zeros(g.shape, np.float64)
    grad = _sobel(g)
    gmax = float(grad.max())
    if gmax < 1e-9:
        return np.zeros(g.shape, np.float64)
    gn = grad / gmax
    depth = 0.02 + _knob(a) * 0.3
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        hm = _h_minima(gn, depth)
        markers, nm = ndimage.label(hm)
        if nm < 1:
            return np.zeros(g.shape, np.float64)
        ws = _watershed(gn, markers)
        bnd = _find_boundaries(ws, mode="outer")
    return bnd.astype(np.float64)


# --------------------------------------------------------------------------- #
# registry assembly
# --------------------------------------------------------------------------- #
def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Return the sg_ adaptive-segmentation tier (each fn sort-aware & exception-safe)."""
    cat = "segment"
    defs = [
        ("sg_slic_superpixels", "", IMAGE, REGION, sg_slic_superpixels),
        ("sg_felzenszwalb", "", IMAGE, REGION, sg_felzenszwalb),
        ("sg_gmm_segment", "", IMAGE, REGION, sg_gmm_segment),
        ("sg_kmeans_intensity", "", IMAGE, REGION, sg_kmeans_intensity),
        ("sg_region_growing_seeded", "", IMAGE, REGION, sg_region_growing_seeded),
        ("sg_normalized_cut_2", "", IMAGE, REGION, sg_normalized_cut_2),
        ("sg_watershed_gradient", "", IMAGE, REGION, sg_watershed_gradient),
    ]

    def _wrap(fn, osort):
        def inner(v, a, b):
            shape = _as_gray(v).shape
            try:
                out = fn(v, a, b)
            except Exception:
                out = None
            if not isinstance(out, np.ndarray) or out.shape != shape:
                return np.zeros(shape, np.float64)
            return _clip01(np.where(out > 0.5, 1.0, 0.0)).astype(np.float64)
        inner.__name__ = getattr(fn, "__name__", "op")
        return inner

    return [Op(name, cat, halcon, isort, osort, _wrap(fn, osort))
            for (name, halcon, isort, osort, fn) in defs]

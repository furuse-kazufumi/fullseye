# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Compare two segmentations — contingency, variation of information, Rand indices (numpy only).

Connectomics lives on this question: a neuron segmentation from electron microscopy is
scored against a proofread ground truth by how much it **splits** true objects and how
much it **merges** different ones. The standard measures are all functions of one table,
the contingency table ``n_ij`` (pixels labelled ``i`` in the truth and ``j`` in the
candidate), so every op here builds that table first and reads its answer off it.

Three operators (``labels2d, labels2d -> table``; the arrays may be 2-D or 3-D):

  * :func:`seg_contingency` — the table itself (sparse: the label pairs that co-occur).
  * :func:`seg_variation_of_information` — VOI = H(a|b) + H(b|a) with its two halves named:
    ``split = H(b|a)`` (the candidate cuts true objects) and ``merge = H(a|b)`` (the
    candidate glues different objects). Meila 2007.
  * :func:`seg_rand` — Rand index, adjusted Rand index (Hubert & Arabie 1985) and the
    adapted Rand error of the CREMI / SNEMI challenges (Arganda-Carreras et al. 2015),
    with the pair precision and recall it is made of.

Two more (``labels2d[, labels2d], table -> table``) read the **wiring diagram** a segmentation
implies from synapse annotations (each synapse's pre and post point):

  * :func:`seg_synapse_partners` — which object each synapse end lands in, and the distinct
    (pre object, post object) connections.
  * :func:`seg_wiring_variation` — the same VOI split / merge measured where the wiring is
    read: at the synapse ends, and over synapses grouped by connection.

``a`` is the ground truth and ``b`` the candidate — the split/merge names depend on it.
``ignore_label`` drops every pixel whose **truth** label equals it (the convention of the
challenges, where 0 marks unlabelled space).

Identities (the tests are built on these): relabelling either input by any permutation
changes nothing; ``VOI(a, a) == 0`` and ``ARI(a, a) == 1``; VOI is a metric (symmetric,
triangle inequality); cutting one true region of ``m`` pixels into two equal halves raises
``split`` by exactly ``m / N`` bits and leaves ``merge`` at 0; the Rand index equals a
brute-force count over all pixel pairs. Second implementations: scikit-image
``variation_of_information`` / ``adapted_rand_error`` and scikit-learn
``adjusted_rand_score`` (pinned in the tests when installed).

Provenance: Meila, *J. Multivariate Anal.* 2007 (VOI); Rand, *JASA* 1971; Hubert & Arabie,
*J. Classif.* 1985 (ARI); Arganda-Carreras et al., *Front. Neuroanat.* 2015 (adapted Rand,
SNEMI3D); the CREMI challenge (cremi.org).
"""
from __future__ import annotations

import numpy as np

MAX_SEG_PIXELS = 500_000_000


def _labels(x, name, op):
    if isinstance(x, (str, bytes)) or np.ma.is_masked(x):
        raise ValueError("%s: %s must be an integer label array" % (op, name))
    a = np.asarray(x)
    if a.dtype.kind == "b":
        a = a.astype(np.int64)
    if a.dtype.kind == "f":
        if not np.isfinite(a).all() or not np.array_equal(a, np.round(a)):
            raise ValueError("%s: %s has non-integer values — labels must be integers" % (op, name))
        a = a.astype(np.int64)
    if a.dtype.kind not in "iu":
        raise ValueError("%s: %s has dtype %s — labels must be integers" % (op, name, a.dtype))
    if a.ndim not in (2, 3):
        raise ValueError("%s: %s must be a 2-D or 3-D label array, got %d-D" % (op, name, a.ndim))
    if a.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if a.size > MAX_SEG_PIXELS:
        raise ValueError("%s: %s has %d pixels, over the %d cap" % (op, name, a.size, MAX_SEG_PIXELS))
    return a


def _table(a, b, ignore_label, op):
    a = _labels(a, "a", op)
    b = _labels(b, "b", op)
    if a.shape != b.shape:
        raise ValueError("%s: a %r and b %r differ in shape" % (op, a.shape, b.shape))
    a, b = a.ravel(), b.ravel()
    if ignore_label is not None:
        keep = a != int(ignore_label)
        a, b = a[keep], b[keep]
        if a.size == 0:
            raise ValueError("%s: every pixel carries ignore_label=%r in the truth" % (op, ignore_label))
    ua, ia = np.unique(a, return_inverse=True)
    ub, ib = np.unique(b, return_inverse=True)
    pair = ia.astype(np.int64) * len(ub) + ib
    up, cnt = np.unique(pair, return_counts=True)
    return ua, ub, up // len(ub), up % len(ub), cnt.astype(np.int64), int(a.size)


def seg_contingency(a, b, ignore_label=None):
    """The contingency table of truth ``a`` against candidate ``b`` (sparse).

    Returns ``labels_a`` / ``labels_b`` (the distinct labels), ``rows`` / ``cols`` (indices
    into them) and ``counts`` for every co-occurring pair, plus ``n`` (pixels counted),
    ``row_sums`` (size of each truth object) and ``col_sums`` (size of each candidate object).
    ``counts.sum() == n``, ``row_sums.sum() == col_sums.sum() == n``.

    **Raises** ``ValueError``: non-integer, non-finite, boolean-free-but-string or masked input;
    not 2-D / 3-D; empty; different shapes; every pixel ignored.
    """
    ua, ub, r, c, cnt, n = _table(a, b, ignore_label, "seg_contingency")
    return {"labels_a": ua, "labels_b": ub, "rows": r, "cols": c, "counts": cnt, "n": n,
            "row_sums": np.bincount(r, weights=cnt, minlength=len(ua)).astype(np.int64),
            "col_sums": np.bincount(c, weights=cnt, minlength=len(ub)).astype(np.int64)}


def _entropy(p):
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def _conditional(cnt, given, n):
    """H(X | Y) in bits from the joint counts ``cnt`` and the counts ``given`` of Y on each cell.

    Summed directly as ``-sum p_xy log2(n_xy / n_y)`` — not ``H(X, Y) - H(Y)``, whose two
    large terms leave ~1e-15 of rounding dust when the answer is exactly 0 (a relabelling).
    A cell with ``n_xy == n_y`` contributes ``log2(1.0) == 0`` exactly.
    """
    cnt = np.asarray(cnt, dtype=np.float64)
    return float(max(-(cnt / n * np.log2(cnt / given)).sum(), 0.0))


def seg_variation_of_information(a, b, ignore_label=None):
    """Variation of information between truth ``a`` and candidate ``b``, in bits.

    Returns ``voi`` = ``split`` + ``merge``, with ``split = H(b|a)`` (how much the candidate
    cuts true objects apart) and ``merge = H(a|b)`` (how much it glues different true objects
    together), plus the entropies ``h_a``, ``h_b`` and the mutual information ``mi``.

    **Raises** ``ValueError``: as :func:`seg_contingency`.
    """
    ua, ub, r, c, cnt, n = _table(a, b, ignore_label, "seg_variation_of_information")
    na = np.bincount(r, weights=cnt, minlength=len(ua))
    nb = np.bincount(c, weights=cnt, minlength=len(ub))
    h_a, h_b = _entropy(na / n), _entropy(nb / n)
    split = _conditional(cnt, na[r], n)      # H(b|a)
    merge = _conditional(cnt, nb[c], n)      # H(a|b)
    return {"voi": split + merge, "split": split, "merge": merge,
            "h_a": h_a, "h_b": h_b, "mi": max(h_a - merge, 0.0), "n": n}


def seg_rand(a, b, ignore_label=None):
    """Rand index, adjusted Rand index and the adapted Rand error (CREMI / SNEMI).

    With ``n_ij`` the contingency table, ``a_i`` / ``b_j`` its row and column sums and ``N``
    the pixel count:

      * ``rand_index`` = fraction of pixel pairs on which the two agree (same/different);
      * ``adjusted_rand_index`` = Hubert & Arabie's chance-corrected version (1 = identical,
        about 0 = independent);
      * ``adapted_rand_error`` = 1 - F over **pairs of distinct pixels**: pair ``precision`` =
        (sum n_ij^2 - N) / (sum b_j^2 - N) — of the pairs the candidate puts together, the
        fraction the truth also puts together — and ``recall`` = (sum n_ij^2 - N) /
        (sum a_i^2 - N) (Arganda-Carreras et al. 2015). The ``- N`` removes each pixel's pair
        with itself. scikit-image's ``adapted_rand_error`` returns the same error, but its
        ``precision`` is divided by the **truth** pairs (its code sums the rows of the
        truth-by-test table), i.e. it is this ``recall``; its docstring says otherwise.

    **Raises** ``ValueError``: as :func:`seg_contingency`; fewer than 2 counted pixels.
    """
    op = "seg_rand"
    ua, ub, r, c, cnt, n = _table(a, b, ignore_label, op)
    if n < 2:
        raise ValueError("%s: need at least 2 pixels to form a pair" % op)
    ai = np.bincount(r, weights=cnt, minlength=len(ua))
    bj = np.bincount(c, weights=cnt, minlength=len(ub))
    cnt = cnt.astype(np.float64)

    def pairs(x):
        return float((x * (x - 1) / 2.0).sum())

    s_ij, s_a, s_b = pairs(cnt), pairs(ai), pairs(bj)
    total = n * (n - 1) / 2.0
    agree = total + 2.0 * s_ij - s_a - s_b
    expected = s_a * s_b / total
    denom = 0.5 * (s_a + s_b) - expected
    ari = 1.0 if denom == 0 else (s_ij - expected) / denom
    sq_ij = float((cnt ** 2).sum()) - n          # ordered pairs of distinct pixels, same in both
    sq_a = float((ai ** 2).sum()) - n            # ... same in the truth
    sq_b = float((bj ** 2).sum()) - n            # ... same in the candidate
    precision = sq_ij / sq_b if sq_b > 0 else 1.0
    recall = sq_ij / sq_a if sq_a > 0 else 1.0
    are = 1.0 - (2.0 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0)
    return {"rand_index": agree / total, "adjusted_rand_index": float(ari),
            "adapted_rand_error": float(are), "precision": precision, "recall": recall, "n": n}


# --------------------------------------------------------------------------- wiring
# A connectome is read off a segmentation: each synapse is a (pre, post) pair of points,
# and the connection it belongs to is (object under pre, object under post). So every
# split or merge of the segmentation turns into an error of the wiring diagram — and the
# same VOI, taken over synapses grouped by connection, says which kind.


def _points(p, name, op, ndim):
    if isinstance(p, (str, bytes)):
        raise ValueError("%s: %s must be an (n, %d) array of coordinates" % (op, name, ndim))
    arr = np.asarray(p, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != ndim or arr.shape[0] == 0:
        raise ValueError("%s: %s must be a non-empty (n, %d) array, got shape %r" % (op, name, ndim, arr.shape))
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s has non-finite coordinates" % (op, name))
    return arr


def _lookup(labels, pts, spacing, name, op):
    idx = np.floor(pts / spacing).astype(np.int64)
    bad = (idx < 0) | (idx >= np.asarray(labels.shape))
    if bad.any():
        i = int(np.nonzero(bad.any(axis=1))[0][0])
        raise ValueError("%s: %s point %d at %r falls outside the volume" % (op, name, i, pts[i].tolist()))
    return labels[tuple(idx.T)]


def _split_synapses(synapses, op):
    """``{"pre": (n, d), "post": (n, d)}`` or an ``(n, 2, d)`` array -> (pre, post)."""
    if isinstance(synapses, dict):
        if "pre" not in synapses or "post" not in synapses:
            raise ValueError("%s: synapses must have 'pre' and 'post' columns, got %r" % (op, sorted(synapses)))
        return synapses["pre"], synapses["post"]
    if isinstance(synapses, (str, bytes)):
        raise ValueError("%s: synapses must be a table {'pre', 'post'} or an (n, 2, d) array" % op)
    arr = np.asarray(synapses, dtype=np.float64)
    if arr.ndim != 3 or arr.shape[1] != 2:
        raise ValueError("%s: synapses must be a table {'pre', 'post'} or an (n, 2, d) array, got shape %r"
                         % (op, arr.shape))
    return arr[:, 0], arr[:, 1]


def _synapse_ids(labels, synapses, spacing, name, op):
    lab = _labels(labels, name, op)
    pre, post = _split_synapses(synapses, op)
    pre = _points(pre, "pre", op, lab.ndim)
    post = _points(post, "post", op, lab.ndim)
    if len(pre) != len(post):
        raise ValueError("%s: pre has %d points but post has %d" % (op, len(pre), len(post)))
    sp = np.ones(lab.ndim) if spacing is None else np.asarray(spacing, dtype=np.float64).ravel()
    if sp.shape != (lab.ndim,) or not np.isfinite(sp).all() or (sp <= 0).any():
        raise ValueError("%s: spacing must be %d positive numbers, got %r" % (op, lab.ndim, spacing))
    return (_lookup(lab, pre, sp, "pre", op).astype(np.int64),
            _lookup(lab, post, sp, "post", op).astype(np.int64))


def _codes(u, v):
    """Group synapses by their (pre object, post object) pair; returns a connection index per synapse."""
    pair = np.stack([u, v], axis=1)
    edges, inv, cnt = np.unique(pair, axis=0, return_inverse=True, return_counts=True)
    return edges, inv.ravel(), cnt


def seg_synapse_partners(labels, synapses, spacing=None, background=0):
    """Read the wiring diagram a segmentation implies: which object each synapse connects.

    ``synapses`` is a table ``{"pre": (n, ndim), "post": (n, ndim)}`` (or an ``(n, 2, ndim)``
    array) holding the two ends of ``n`` synapses in physical units (divided by ``spacing`` per axis, default 1, then floored to a voxel).
    Returns ``pre_ids`` / ``post_ids`` (the object under each end), ``connection`` (index
    of each synapse's connection in ``edges``), ``edges`` (``(k, 2)`` distinct
    (pre object, post object) pairs), ``synapses_per_edge``, ``n_background`` (synapses
    with an end on ``background``) and ``n_autapse`` (both ends in the same non-background
    object — a merge, or a real autapse).

    **Raises** ``ValueError``: bad labels (as :func:`seg_contingency`); ``synapses`` not a
    table with ``pre`` / ``post`` nor an ``(n, 2, ndim)`` array; points not ``(n, ndim)``, non-finite, of different counts or outside the volume; bad spacing.
    """
    op = "seg_synapse_partners"
    u, v = _synapse_ids(labels, synapses, spacing, "labels", op)
    edges, conn, cnt = _codes(u, v)
    bg = int(background)
    return {"pre_ids": u, "post_ids": v, "connection": conn, "edges": edges,
            "synapses_per_edge": cnt.astype(np.int64),
            "n_background": int(((u == bg) | (v == bg)).sum()),
            "n_autapse": int(((u == v) & (u != bg)).sum()), "n": int(len(u))}


def _voi_codes(ca, cb):
    """split = H(cb|ca), merge = H(ca|cb) for two integer codings of the same items."""
    n = len(ca)
    _, ia = np.unique(ca, return_inverse=True)
    _, ib = np.unique(cb, return_inverse=True)
    ia, ib = ia.ravel().astype(np.int64), ib.ravel().astype(np.int64)
    up, pc = np.unique(ia * (int(ib.max()) + 1) + ib, return_counts=True)
    r, c = up // (int(ib.max()) + 1), up % (int(ib.max()) + 1)
    split = _conditional(pc, np.bincount(ia)[r], n)
    merge = _conditional(pc, np.bincount(ib)[c], n)
    return split, merge, ia, ib


def seg_wiring_variation(a, b, synapses, spacing=None, background=0):
    """How a candidate segmentation ``b`` corrupts the wiring diagram of truth ``a``, in bits.

    Two levels, both VOI split / merge (``synapses`` as in :func:`seg_synapse_partners`):

      * **synapse ends** (``split`` / ``merge``, ``voi``): the segmentation VOI measured only
        at the ``2n`` synapse ends instead of every pixel. ``split`` = two ends on one true
        neuron now on different objects (the neuron was cut between its synapses); ``merge``
        = ends on different true neurons now on one object (they were glued). Cutting a
        neuron whose ``s`` ends divide ``s1`` / ``s2`` raises ``split`` by exactly
        ``(s / 2n)·H2(s1 / s)``. Pixels far from any synapse cost nothing here.
      * **connections** (``connection_split`` / ``connection_merge``): synapses grouped by
        their (pre object, post object) pair — one true connection scattered over several,
        or different true connections fused into one (synapses attributed to the wrong
        partner). A connection with a single synapse cannot scatter, so this level is blind
        to cuts that only rename a one-synapse connection; the ends level is not. Synapses with an end on
    ``background`` in the truth are dropped; in the candidate, each such synapse is **lost**
    and counted in ``n_lost`` as its own singleton at both levels (not one shared
    "background" object, which would fake a huge merge). Also returns ``split_connections`` (true connections
    spread over 2+ candidate ones), ``merged_connections`` (candidate connections holding
    synapses of 2+ true ones), ``edges_a`` / ``edges_b`` and ``n`` (synapses scored).

    **Raises** ``ValueError``: as :func:`seg_synapse_partners`; shapes of ``a`` and ``b``
    differ; no synapse left after dropping background in the truth.
    """
    op = "seg_wiring_variation"
    ua, va = _synapse_ids(a, synapses, spacing, "a", op)
    ub, vb = _synapse_ids(b, synapses, spacing, "b", op)
    if np.shape(a) != np.shape(b):
        raise ValueError("%s: a %r and b %r differ in shape" % (op, np.shape(a), np.shape(b)))
    bg = int(background)
    keep = (ua != bg) & (va != bg)
    if not keep.any():
        raise ValueError("%s: every synapse has an end on background in the truth" % op)
    ua, va, ub, vb = ua[keep], va[keep], ub[keep], vb[keep]
    n = len(ua)
    # ends: a candidate end on background is its own singleton (lost), never one shared object
    ends_a = np.concatenate([ua, va])
    ends_b = np.concatenate([ub, vb]).copy()
    off = ends_b == bg
    ends_b[off] = int(max(ends_b.max(), 0)) + 1 + np.arange(int(off.sum()))
    split, merge, _, _ = _voi_codes(ends_a, ends_b)
    # connections
    ea, ca, _ = _codes(ua, va)
    lost = (ub == bg) | (vb == bg)
    _, cb, _ = _codes(ub, vb)
    cb = cb.copy()
    cb[lost] = cb.max() + 1 + np.arange(int(lost.sum()))     # each lost synapse on its own
    c_split, c_merge, ia, ib = _voi_codes(ca, cb)
    pairs = np.unique(np.stack([ia, ib], 1), axis=0)
    n_b_per_a = np.bincount(pairs[:, 0])
    n_a_per_b = np.bincount(pairs[:, 1])
    return {"voi": split + merge, "split": split, "merge": merge,
            "connection_split": c_split, "connection_merge": c_merge,
            "split_connections": int((n_b_per_a > 1).sum()),
            "merged_connections": int((n_a_per_b > 1).sum()),
            "n_lost": int(lost.sum()), "edges_a": int(len(ea)),
            "edges_b": int(len(np.unique(np.stack([ub, vb], 1)[~lost], axis=0))), "n": int(n)}

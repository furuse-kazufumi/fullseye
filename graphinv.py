# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Graph invariants of a wiring matrix — degrees, cycles, reciprocity, a degree-preserving null, and a swap symmetry (numpy only).

A connectome, a vessel network, a pipe-and-valve map: once it is an adjacency matrix,
the question "is this wiring anything more than its degree sequence?" has exact
answers. Raw counts (2,710 directed 3-cycles) depend on size and cannot be compared
across graphs; the ratio against a **degree-preserving null** can. Every operator here
carries an identity that holds to the last integer, not a fitted threshold.

Four operators (all ``matrix -> table``, no new type vocabulary):

  * :func:`graph_degree_summary` — n, |E|, in/out degrees, density, self-loops,
    reciprocal pairs. Identity: ``sum(in) == sum(out) == |E|`` for a directed graph.
  * :func:`graph_cycle3` — directed 3-cycles ``tr(B^3) / 3``. Second implementation:
    brute-force enumeration agrees on small graphs (pinned in the tests).
  * :func:`graph_degree_preserving_null` — rewires by edge swaps that keep every node's
    in- and out-degree **exactly** (checked per sample, fail-closed), then reports the
    null mean / sd / z of 3-cycles and reciprocity. This is the only honest way to say
    "beyond what the degrees imply".
  * :func:`graph_swap_symmetry` — Jaccard overlap between the wiring and the wiring
    with node pairs exchanged (left/right partners, say). Identity: the identity pairing
    gives exactly 1; exchanging a pair twice returns the original.

Measured — the identities the tests are built on (``tests/test_graphinv.py``):

    quantity                                        analytic / measured
    sum(in-degree) == sum(out-degree) == |E|        exact
    tr(B^3)/3 == brute-force 3-cycle count          exact (40-node random graph)
    rewired sample keeps in/out degree sequences    exact, every sample
    swap symmetry with identity pairs               Jaccard == 1.0
    swapping a pair twice                           B recovered exactly
    C. elegans hermaphrodite chemical (Cook 2019)   302 listed - 300 wired == {CANL, CANR}

Provenance (public standards and textbooks only): Maslov & Sneppen, *Science* 2002
(degree-preserving rewiring); Milo et al., *Science* 2002 (network motifs);
Cook et al., *Nature* 2019 (C. elegans connectome, the worked example).
"""
from __future__ import annotations

import numpy as np

MAX_GRAPH_NODES = 20_000


def _as_binary_adjacency(a, name: str, op: str) -> np.ndarray:
    """Coerce to a square 0/1 int8 adjacency, refusing the silent traps.

    Weights are thresholded at ``> 0`` (a wiring matrix's weight is a synapse count or
    a contact depth; the invariants here are about *presence*). Negative, non-finite,
    complex, string / object / bool inputs are refused rather than plausibly coerced.
    """
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked entries — fill or drop "
                         "them explicitly" % (op, name))
    if isinstance(a, (str, bytes)):
        raise ValueError("%s: %s is a string — expected a square numeric matrix" % (op, name))
    if np.iscomplexobj(a):
        raise ValueError("%s: %s is complex — a wiring matrix is real" % (op, name))
    kind = getattr(getattr(a, "dtype", None), "kind", None) or np.asarray(a).dtype.kind
    if kind in ("U", "S", "O", "V", "b"):
        raise ValueError("%s: %s has dtype '%s' — convert it to numbers explicitly"
                         % (op, name, kind))
    arr = np.asarray(a, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[0] != arr.shape[1]:
        raise ValueError("%s: %s must be a square 2-D matrix, got shape %r"
                         % (op, name, arr.shape))
    if arr.shape[0] == 0:
        raise ValueError("%s: %s is empty (0 nodes)" % (op, name))
    if arr.shape[0] > MAX_GRAPH_NODES:
        raise ValueError("%s: %s has %d nodes, over the %d cap — the dense O(n^3) "
                         "cycle count would not finish" % (op, name, arr.shape[0], MAX_GRAPH_NODES))
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s has non-finite entries (nan/inf)" % (op, name))
    if (arr < 0).any():
        raise ValueError("%s: %s has negative entries — a wiring weight is a count or a "
                         "depth; a signed matrix needs a different operator" % (op, name))
    return (arr > 0).astype(np.int8)


def graph_degree_summary(adj):
    """Degrees, density and reciprocity of a directed wiring matrix.

    ``adj`` is a square matrix; entry ``(i, j) > 0`` means an edge ``i -> j``. Self-loops
    are counted separately and excluded from the edge statistics. Returns a dict with
    ``n``, ``edges``, ``self_loops``, the ``in_degree`` / ``out_degree`` arrays,
    ``density`` (``edges / (n (n-1))``), and ``reciprocal_pairs`` (unordered pairs wired
    in both directions).

    The identity ``in_degree.sum() == out_degree.sum() == edges`` holds exactly for
    any directed graph and is checked before returning (fail-closed — if it ever broke,
    the matrix was not what the caller thought).

    **Raises** ``ValueError``: non-square / empty / non-finite / negative input, or a
    matrix over the node cap.
    """
    op = "graph_degree_summary"
    B = _as_binary_adjacency(adj, "adj", op)
    loops = int(np.trace(B))
    np.fill_diagonal(B, 0)
    kin = B.sum(axis=0).astype(int)
    kout = B.sum(axis=1).astype(int)
    E = int(B.sum())
    if not (int(kin.sum()) == int(kout.sum()) == E):
        raise ValueError("%s: degree sums disagree with the edge count (%d, %d, %d) — "
                         "the adjacency is inconsistent" % (op, kin.sum(), kout.sum(), E))
    n = B.shape[0]
    rec = int((B * B.T).sum()) // 2
    return {
        "n": n, "edges": E, "self_loops": loops,
        "in_degree": kin, "out_degree": kout,
        "density": E / (n * (n - 1)) if n > 1 else 0.0,
        "reciprocal_pairs": rec,
    }


def graph_cycle3(adj):
    """Number of directed 3-cycles ``i -> j -> k -> i`` as ``tr(B^3) / 3``.

    Each cycle is counted once (the trace visits it from each of its three starting
    nodes). Self-loops are removed first. Returns a dict with ``cycles3`` and ``n``.

    A second, independent implementation (brute-force enumeration) agrees exactly on
    small graphs — pinned in the tests, because a single implementation of a counting
    formula cannot catch its own off-by-three.

    **Raises** ``ValueError``: as :func:`graph_degree_summary`.
    """
    op = "graph_cycle3"
    B = _as_binary_adjacency(adj, "adj", op)
    np.fill_diagonal(B, 0)
    M = B.astype(np.int64)
    c3 = int(np.trace(M @ M @ M)) // 3
    return {"cycles3": c3, "n": int(B.shape[0])}


def _rewire(B: np.ndarray, rng, n_swaps: int) -> np.ndarray:
    """Degree-preserving edge swaps ``(a->b, c->d) -> (a->d, c->b)``.

    A swap is skipped (not retried elsewhere) when it would create a self-loop, a
    duplicate edge, or involve fewer than four distinct nodes. Each accepted swap
    leaves every in- and out-degree unchanged — that is the whole point, and the
    caller checks it.
    """
    R = B.copy()
    edges = np.argwhere(R == 1)
    m = len(edges)
    done = 0
    for _ in range(n_swaps * 3):
        if done >= n_swaps:
            break
        i, j = rng.integers(m, size=2)
        a, b = edges[i]
        c, d = edges[j]
        if a == c or b == d or a == d or c == b or R[a, d] or R[c, b]:
            continue
        R[a, b] = 0; R[c, d] = 0
        R[a, d] = 1; R[c, b] = 1
        edges[i] = (a, d); edges[j] = (c, b)
        done += 1
    return R


def graph_degree_preserving_null(adj, n_samples=20, swaps_per_edge=5, seed=0):
    """Compare 3-cycles and reciprocity against a degree-preserving null model.

    Each null sample rewires the graph by ``swaps_per_edge * |E|`` edge swaps that keep
    every node's in- and out-degree **exactly** (Maslov & Sneppen 2002). The sample's
    degree sequences are checked against the original before it is used — a null that
    drifted would make every ratio a lie, so this fails closed.

    Returns a dict with the observed ``cycles3`` and ``reciprocal_pairs``, the null
    ``*_null_mean`` / ``*_null_sd``, the ``*_ratio`` (observed / null mean) and ``*_z``,
    plus ``n_samples`` and ``swaps``. Ratios are what let graphs of different size be
    compared; raw counts cannot.

    **Raises** ``ValueError``: as :func:`graph_degree_summary`; ``n_samples < 2``
    (no spread to estimate); ``swaps_per_edge < 1``; a graph with fewer than 2 edges
    (nothing to swap).
    """
    op = "graph_degree_preserving_null"
    B = _as_binary_adjacency(adj, "adj", op)
    np.fill_diagonal(B, 0)
    if int(n_samples) < 2:
        raise ValueError("%s: n_samples must be >= 2 to estimate a spread, got %r" % (op, n_samples))
    if int(swaps_per_edge) < 1:
        raise ValueError("%s: swaps_per_edge must be >= 1, got %r" % (op, swaps_per_edge))
    E = int(B.sum())
    if E < 2:
        raise ValueError("%s: need at least 2 edges to swap, got %d" % (op, E))
    kin, kout = B.sum(axis=0), B.sum(axis=1)
    M = B.astype(np.int64)
    c3 = int(np.trace(M @ M @ M)) // 3
    rec = int((B * B.T).sum()) // 2
    rng = np.random.default_rng(seed)
    null_c3, null_rec = [], []
    for _ in range(int(n_samples)):
        R = _rewire(B, rng, int(swaps_per_edge) * E)
        if not (np.array_equal(R.sum(axis=0), kin) and np.array_equal(R.sum(axis=1), kout)
                and int(R.sum()) == E):
            raise ValueError("%s: a null sample changed the degree sequence — the "
                             "rewiring is broken, refusing to report ratios" % op)
        RM = R.astype(np.int64)
        null_c3.append(int(np.trace(RM @ RM @ RM)) // 3)
        null_rec.append(int((R * R.T).sum()) // 2)
    c3m, c3s = float(np.mean(null_c3)), float(np.std(null_c3, ddof=1))
    rm, rs = float(np.mean(null_rec)), float(np.std(null_rec, ddof=1))

    def ratio(x, m):
        return float(x) / m if m > 0 else float("nan")

    def z(x, m, s):
        return (float(x) - m) / s if s > 0 else float("nan")

    return {
        "n": int(B.shape[0]), "edges": E,
        "cycles3": c3, "cycles3_null_mean": c3m, "cycles3_null_sd": c3s,
        "cycles3_ratio": ratio(c3, c3m), "cycles3_z": z(c3, c3m, c3s),
        "reciprocal_pairs": rec, "reciprocal_null_mean": rm, "reciprocal_null_sd": rs,
        "reciprocal_ratio": ratio(rec, rm), "reciprocal_z": z(rec, rm, rs),
        "n_samples": int(n_samples), "swaps": int(swaps_per_edge) * E,
    }


def graph_swap_symmetry(adj, pairs):
    """How much of the wiring survives exchanging node pairs (a left/right test).

    ``pairs`` is a sequence of ``(i, j)`` index pairs to exchange (each node in at most
    one pair). The wiring is re-indexed by the exchange and compared with the original:
    ``jaccard = |E ∩ E'| / |E ∪ E'|`` over directed edges (self-loops removed). Returns
    a dict with ``jaccard``, ``shared``, ``union``, ``edges``, and ``n_pairs``.

    Identities: the identity pairing (or an empty ``pairs``) gives exactly 1.0; applying
    the exchange twice recovers the original matrix exactly. For the C. elegans
    hermaphrodite chemical connectome with its 98 named left/right pairs the measured
    value is 0.470 — half the wiring is not mirrored.

    **Raises** ``ValueError``: as :func:`graph_degree_summary`; an index out of range;
    a node appearing in two pairs; a pair of a node with itself.
    """
    op = "graph_swap_symmetry"
    B = _as_binary_adjacency(adj, "adj", op)
    np.fill_diagonal(B, 0)
    n = B.shape[0]
    perm = np.arange(n)
    seen = set()
    for k, (i, j) in enumerate(pairs):
        i, j = int(i), int(j)
        if not (0 <= i < n and 0 <= j < n):
            raise ValueError("%s: pair %d = (%d, %d) is out of range for n=%d" % (op, k, i, j, n))
        if i == j:
            raise ValueError("%s: pair %d exchanges node %d with itself" % (op, k, i))
        if i in seen or j in seen:
            raise ValueError("%s: node %d or %d appears in more than one pair" % (op, i, j))
        seen.add(i); seen.add(j)
        perm[i], perm[j] = j, i
    Bm = B[np.ix_(perm, perm)]
    shared = int(((B == 1) & (Bm == 1)).sum())
    union = int(((B == 1) | (Bm == 1)).sum())
    return {
        "jaccard": shared / union if union else 1.0,
        "shared": shared, "union": union, "edges": int(B.sum()),
        "n_pairs": len(seen) // 2,
    }

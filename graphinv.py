# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Graph invariants of a wiring matrix — degrees, cycles, reciprocity, a degree-preserving null, and a swap symmetry (numpy only).

A connectome, a vessel network, a pipe-and-valve map: once it is an adjacency matrix,
the question "is this wiring anything more than its degree sequence?" has exact
answers. Raw counts (2,710 directed 3-cycles) depend on size and cannot be compared
across graphs; the ratio against a **degree-preserving null** can. Every operator here
carries an identity that holds to the last integer, not a fitted threshold.

Five operators (``matrix -> table``, and one ``table -> table``; no new type vocabulary):

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
  * :func:`graph_edge_consensus` — K wirings of K individuals on one node order: how many
    individuals carry each edge, pairwise Jaccard, the synapse share by occupancy, the
    developmental split stable / added / lost / flicker, and a null that rewires every
    individual independently. Identity: ``sum_c c * h[c] == sum_i |E_i|``.
  * :func:`graph_kcore` — the k-core decomposition (Seidman 1983) by in-, out-, total or
    undirected degree, or its weighted twin the s-core (Eidsaa & Almaas 2013). Identities:
    a complete graph is one core of index n−1, a tree has index 1, a cycle 2; the s-core
    of a 0/1 matrix is the k-core; scaling every weight by c scales every s-core index by c.
  * :func:`graph_rich_club_curve` — the rich-club coefficient φ(k) for every k at once,
    normalised by the degree-preserving null. Identity: φ(k) equals the single-k
    ``conngraph.graph_rich_club`` for every k; the null of a complete graph is itself.
  * :func:`graph_core_persistence` — K wirings on one node order: which nodes sit in the
    innermost core of every individual (persistent), of some (recurrent), of one
    (transient). Identity: ``sum_i |inner_i| == sum_v appearances[v]``.

Measured — the identities the tests are built on (``tests/test_graphinv.py``):

    quantity                                        analytic / measured
    sum(in-degree) == sum(out-degree) == |E|        exact
    tr(B^3)/3 == brute-force 3-cycle count          exact (40-node random graph)
    rewired sample keeps in/out degree sequences    exact, every sample
    swap symmetry with identity pairs               Jaccard == 1.0
    swapping a pair twice                           B recovered exactly
    C. elegans hermaphrodite chemical (Cook 2019)   302 listed - 300 wired == {CANL, CANR}
    core C + unique u per individual, K of them     h[K] == C, h[1] == K*u, Jaccard == C/(C+2u)
    C. elegans, 8 worms (Witvliet 2021)             442 edges in all 8; null max 0 in 20 samples
    complete graph K_n, k-core                      every node has index n−1 (exact)
    tree / cycle, k-core                            index 1 / 2 (exact)
    s-core of a 0/1 matrix                          == k-core (exact); weights × c → indices × c
    rich club φ(k) vs conngraph.graph_rich_club     equal for every k (exact)

Provenance (public standards and textbooks only): Maslov & Sneppen, *Science* 2002
(degree-preserving rewiring); Milo et al., *Science* 2002 (network motifs);
Cook et al., *Nature* 2019 (C. elegans connectome, the worked example);
Witvliet et al., *Nature* 2021 (8 isogenic worms from birth to adulthood).
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
    return _rewire_counted(B, rng, n_swaps)[0]


def _rewire_counted(B: np.ndarray, rng, n_swaps: int):
    """:func:`_rewire` plus the number of swaps actually accepted (``(R, accepted)``).

    ★2026-10-07: 試行は ``3 * n_swaps`` 回で打ち切るので、密なグラフ(密度 0.9)では
    7005 回を頼んで通るのは 1 割未満 —— 頼んだ数だけを ``swaps`` と報告すると混ぜ具合を過大に見せる。
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
    return R, done


def graph_degree_preserving_null(adj, n_samples=20, swaps_per_edge=5, seed=0):
    """Compare 3-cycles and reciprocity against a degree-preserving null model.

    Each null sample requests ``swaps_per_edge * |E|`` edge swaps that keep every node's
    in- and out-degree **exactly** (Maslov & Sneppen 2002); a swap that would create a
    self-loop or duplicate edge is skipped, so dense graphs accept fewer
    (``swaps_accepted``). The sample's
    degree sequences are checked against the original before it is used — a null that
    drifted would make every ratio a lie, so this fails closed.

    Returns a dict with the observed ``cycles3`` and ``reciprocal_pairs``, the null
    ``*_null_mean`` / ``*_null_sd``, the ``*_ratio`` (observed / null mean) and ``*_z``,
    plus ``n_samples``, ``swaps`` (requested per sample) and ``swaps_accepted`` (list,
    accepted per sample). Ratios are what let graphs of different size be compared;
    raw counts cannot.

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
    null_c3, null_rec, accepted = [], [], []
    for _ in range(int(n_samples)):
        R, acc = _rewire_counted(B, rng, int(swaps_per_edge) * E)
        accepted.append(int(acc))
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
        "swaps_accepted": accepted,                     # ★2026-10-07: 実際に通った入れ替え数(標本ごと)
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


def _as_weight_matrix(a, name: str, op: str) -> np.ndarray:
    """The weighted twin of :func:`_as_binary_adjacency` (same refusals, float64 kept)."""
    _as_binary_adjacency(a, name, op)          # every refusal lives in one place
    return np.array(a, dtype=np.float64)


def graph_edge_consensus(adjs, ordered=False, n_null=0, swaps_per_edge=5, seed=0):
    """How many individuals share each connection — K wiring matrices on one node order.

    ``adjs`` is either a list of K square matrices or a table ``{name: matrix}`` (its
    insertion order is the individual order), all on the **same** node order (align
    the cell names first; a node absent from an individual is a zero row and column).
    Weights (synapse counts) are kept for the synapse shares; presence is ``> 0``.
    Self-loops are dropped.

    Returns a dict with:

      * ``k`` (K), ``n``, ``names``, ``edges_per_individual`` and ``union`` (edges
        seen in at least one individual)
      * ``occupancy_hist`` — ``h[c]`` = number of edges present in exactly ``c``
        individuals, ``c = 0..K`` (``h[0]`` is always 0: only the union is counted)
      * ``jaccard`` — the K x K pairwise overlap ``|Ei ∩ Ej| / |Ei ∪ Ej|``
      * ``synapse_share`` — for each ``c``, the fraction of all synapses (summed over
        individuals) on edges of occupancy ``c`` (with a 0/1 input: the edge share)
      * with ``ordered=True`` (individuals listed in developmental order): the union is
        split by its presence pattern along the order into ``stable`` (present in all),
        ``added`` (absent, then present to the end: ``0..01..1``), ``lost``
        (``1..10..0``) and ``flicker`` (anything else). The four sum to ``union``.
      * with ``n_null >= 2``: every individual is rewired **independently** by
        degree-preserving swaps (each node's in/out degree kept exactly, checked per
        sample, fail-closed) and the occupancy histogram is re-counted. Reports
        ``occupancy_null_mean`` / ``occupancy_null_sd`` per ``c`` and
        ``shared_all_ratio`` (edges present in all K, observed over the null mean; inf
        when the null never shares one, so ``shared_all_null_max`` is reported too):
        the chance level of "the same connection in every animal" given only each
        animal's degrees.

    Identities (the tests are built on these, not on fitted numbers):
    ``sum_c c * h[c] == sum_i |E_i|``; ``sum_c h[c] == union``; K identical inputs give
    ``h[K] == union`` and every Jaccard == 1; the Jaccard matrix is symmetric with a unit
    diagonal; ``stable + added + lost + flicker == union``; ``synapse_share`` sums to 1.

    **Raises** ``ValueError``: ``adjs`` not a list / table; fewer than 2 individuals;
    matrices of different sizes; any refusal of :func:`graph_degree_summary`
    (non-square, negative, non-finite, string / bool / complex / masked input); an
    individual with no edges; ``n_null`` equal to 1 (no spread) or negative;
    ``swaps_per_edge < 1``.
    """
    op = "graph_edge_consensus"
    if isinstance(adjs, dict):
        names = [str(k) for k in adjs.keys()]
        mats = list(adjs.values())
    elif isinstance(adjs, (list, tuple)):
        names = ["%d" % i for i in range(len(adjs))]
        mats = list(adjs)
    else:
        raise ValueError("%s: adjs must be a list of matrices or a table {name: matrix}, "
                         "got %s" % (op, type(adjs).__name__))
    K = len(mats)
    if K < 2:
        raise ValueError("%s: need at least 2 individuals to compare, got %d" % (op, K))
    n_null = int(n_null)
    if n_null < 0 or n_null == 1:
        raise ValueError("%s: n_null must be 0 (off) or >= 2, got %r" % (op, n_null))
    if int(swaps_per_edge) < 1:
        raise ValueError("%s: swaps_per_edge must be >= 1, got %r" % (op, swaps_per_edge))
    W = [_as_weight_matrix(m, "adjs[%s]" % names[i], op) for i, m in enumerate(mats)]
    n = W[0].shape[0]
    for i, w in enumerate(W):
        if w.shape[0] != n:
            raise ValueError("%s: adjs[%s] has %d nodes but adjs[%s] has %d — put every "
                             "individual on one node order first"
                             % (op, names[i], w.shape[0], names[0], n))
        np.fill_diagonal(w, 0.0)
    P = np.stack([(w > 0) for w in W]).astype(np.int8)            # (K, n, n)
    E = P.reshape(K, -1).sum(axis=1).astype(int)
    if (E == 0).any():
        raise ValueError("%s: individual %s has no edges — nothing to share"
                         % (op, names[int(np.argmin(E))]))
    occ = P.sum(axis=0).astype(np.int64)                           # (n, n), 0..K
    hist = np.bincount(occ.ravel(), minlength=K + 1)
    hist[0] = 0
    union = int((occ > 0).sum())
    flat = P.reshape(K, -1).astype(np.int64)
    inter = flat @ flat.T
    J = np.empty((K, K))
    for i in range(K):
        for j in range(K):
            u = E[i] + E[j] - inter[i, j]
            J[i, j] = inter[i, j] / u if u else 1.0
    S = np.stack(W).sum(axis=0)                                    # synapses summed over individuals
    tot = float(S.sum())
    share = [float(S[occ == c].sum() / tot) if c > 0 else 0.0 for c in range(K + 1)]
    out = {
        "k": K, "n": int(n), "names": names,
        "edges_per_individual": [int(e) for e in E], "union": union,
        "occupancy_hist": [int(h) for h in hist],
        "jaccard": J, "synapse_share": share,
    }
    if ordered:
        pat = P.reshape(K, -1)[:, occ.ravel() > 0].T.astype(np.int8)  # (union, K)
        stable = int((pat.sum(axis=1) == K).sum())
        steps = np.diff(pat, axis=1)
        n_up = (steps == 1).sum(axis=1)
        n_dn = (steps == -1).sum(axis=1)
        added = int(((n_up == 1) & (n_dn == 0) & (pat[:, 0] == 0)).sum())
        lost = int(((n_up == 0) & (n_dn == 1) & (pat[:, 0] == 1)).sum())
        out.update({"stable": stable, "added": added, "lost": lost,
                    "flicker": union - stable - added - lost})
    if n_null >= 2:
        rng = np.random.default_rng(seed)
        hs = []
        for _ in range(n_null):
            occ_r = np.zeros((n, n), dtype=np.int64)
            for i in range(K):
                B = P[i]
                R = _rewire(B, rng, int(swaps_per_edge) * int(E[i])) if E[i] >= 2 else B.copy()
                if not (np.array_equal(R.sum(axis=0), B.sum(axis=0))
                        and np.array_equal(R.sum(axis=1), B.sum(axis=1))):
                    raise ValueError("%s: a null sample changed the degree sequence of "
                                     "individual %s — refusing to report" % (op, names[i]))
                occ_r += R
            h = np.bincount(occ_r.ravel(), minlength=K + 1)
            h[0] = 0
            hs.append(h)
        hs = np.array(hs, dtype=float)
        m, s = hs.mean(axis=0), hs.std(axis=0, ddof=1)
        out.update({
            "occupancy_null_mean": [float(x) for x in m],
            "occupancy_null_sd": [float(x) for x in s],
            "shared_all_ratio": float(hist[K] / m[K]) if m[K] > 0 else float("inf"),
            # the ratio is inf when no null sample shares any edge; the max says how far
            # the observed count sits above every sample drawn
            "shared_all_null_max": int(hs[:, K].max()),
            "n_null": n_null,
        })
    return out


def _rank(x: np.ndarray) -> np.ndarray:
    """Average ranks (ties share the mean rank), 1-based — what Spearman is defined on."""
    x = np.asarray(x, dtype=np.float64)
    order = np.argsort(x, kind="stable")
    ranks = np.empty(len(x), dtype=np.float64)
    ranks[order] = np.arange(1, len(x) + 1)
    _u, inv, cnt = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.bincount(inv.ravel(), weights=ranks)
    return sums[inv.ravel()] / cnt[inv.ravel()]


def _spearman(x, y) -> float:
    if len(x) < 3:
        return 0.0
    rx, ry = _rank(x), _rank(y)
    rx, ry = rx - rx.mean(), ry - ry.mean()
    d = float(np.sqrt((rx ** 2).sum() * (ry ** 2).sum()))
    return 0.0 if d == 0.0 else float((rx * ry).sum() / d)


def graph_strength_growth(a, b, hub_fraction=0.1):
    """Where the new synapses went — one wiring matrix ``a`` (earlier) against ``b`` (later).

    Both are weight matrices (synapse counts) on the **same** node order; self-loops are
    dropped. With ``S = sum`` of each matrix and ``dS = S_b - S_a``:

      * per node: ``in_a``, ``out_a``, ``in_b``, ``out_b`` (strengths), ``degree_a`` (number of
        partners, in + out, presence ``> 0``), ``gain_in = in_b - in_a``, ``gain_out``.
        Identity: ``gain_in.sum() == gain_out.sum() == dS`` (every synapse has one pre and one post).
      * ``strengthened`` / ``weakened`` (weight change on edges present in both), ``added``
        (weight of edges only in ``b``), ``lost`` (weight of edges only in ``a``);
        ``strengthened - weakened + added - lost == dS``.
      * ``rho_in`` / ``rho_out`` — Spearman rank correlation of ``degree_a`` with ``gain_in`` /
        ``gain_out`` over nodes with ``degree_a > 0`` (0.0 with fewer than 3 such nodes or no
        variance); ``n_ranked``.
      * hubs = the top ``hub_fraction`` of ranked nodes by ``degree_a`` (at least 1):
        ``hub_share_in_a`` (their share of ``S_a`` as post-synaptic partners), ``hub_share_gain_in``
        (their share of ``dS`` arriving as inputs), and the same for outputs. If new synapses were
        spread in proportion to existing strength, the two shares would be equal — the gap is
        what "hubs grow disproportionately" means in numbers.

    **Raises** ``ValueError``: either matrix not square / non-finite / negative / a string or
    masked array; shapes differ; ``hub_fraction`` outside ``(0, 1]``; ``dS == 0`` is allowed
    (shares of the gain are then 0).
    """
    op = "graph_strength_growth"
    A = _as_weight_matrix(a, "a", op)
    B = _as_weight_matrix(b, "b", op)
    if A.shape != B.shape:
        raise ValueError("%s: a %r and b %r differ in shape" % (op, A.shape, B.shape))
    if (A < 0).any() or (B < 0).any():
        raise ValueError("%s: weights must be non-negative synapse counts" % op)
    hf = float(hub_fraction)
    if not (0.0 < hf <= 1.0):
        raise ValueError("%s: hub_fraction must be in (0, 1], got %r" % (op, hub_fraction))
    np.fill_diagonal(A, 0.0)
    np.fill_diagonal(B, 0.0)
    in_a, out_a, in_b, out_b = A.sum(0), A.sum(1), B.sum(0), B.sum(1)
    pa, pb = A > 0, B > 0
    both = pa & pb
    diff = B - A
    s_a, s_b = float(A.sum()), float(B.sum())
    deg = (pa.sum(0) + pa.sum(1)).astype(np.int64)      # partners as post + as pre
    gain_in, gain_out = in_b - in_a, out_b - out_a
    ranked = np.nonzero(deg > 0)[0]
    rho_in = _spearman(deg[ranked], gain_in[ranked])
    rho_out = _spearman(deg[ranked], gain_out[ranked])
    n_hub = max(1, int(round(hf * len(ranked)))) if len(ranked) else 0
    hubs = ranked[np.argsort(-deg[ranked], kind="stable")[:n_hub]]
    ds = s_b - s_a

    def share(x, total):
        return float(x[hubs].sum() / total) if total != 0 else 0.0

    return {"n": int(A.shape[0]), "s_a": s_a, "s_b": s_b, "ds": ds,
            "in_a": in_a, "out_a": out_a, "in_b": in_b, "out_b": out_b, "degree_a": deg,
            "gain_in": gain_in, "gain_out": gain_out,
            "strengthened": float(np.clip(diff[both], 0, None).sum()),
            "weakened": float(-np.clip(diff[both], None, 0).sum()),
            "added": float(B[pb & ~pa].sum()), "lost": float(A[pa & ~pb].sum()),
            "rho_in": rho_in, "rho_out": rho_out, "n_ranked": int(len(ranked)),
            "hubs": hubs, "hub_share_in_a": share(in_a, s_a), "hub_share_gain_in": share(gain_in, ds),
            "hub_share_out_a": share(out_a, s_a), "hub_share_gain_out": share(gain_out, ds)}


# ---------------------------------------------------------------------------------------------------
# k-core / s-core, rich club curve, and the persistence of the innermost core across individuals.
# ---------------------------------------------------------------------------------------------------

_CORE_MODES = ("in", "out", "total", "undirected")


def _core_degree_matrix(W: np.ndarray, mode: str, weighted: bool) -> np.ndarray:
    """The matrix whose row / column sums are the degrees to peel on.

    0/1 presence unless ``weighted``. For ``undirected`` the matrix is symmetrised first
    (``max(W, W.T)``: an edge in either direction counts once, with its larger weight).
    """
    A = W if weighted else (W > 0).astype(np.float64)
    if mode == "undirected":
        A = np.maximum(A, A.T)
    return A


def _peel(A: np.ndarray, mode: str) -> np.ndarray:
    """Generalised core decomposition by repeated removal of the minimum-degree node.

    The index of the removed node is the running maximum of the minimum degree seen so far
    (Batagelj & Zaveršnik 2003 for k-cores; the same peeling with real weights is the s-core
    of Eidsaa & Almaas 2013). With 0/1 weights this is exactly the classic k-core. O(n^2).
    """
    n = A.shape[0]
    if mode == "in":
        deg = A.sum(axis=0).astype(np.float64)
    elif mode == "out":
        deg = A.sum(axis=1).astype(np.float64)
    elif mode == "total":
        deg = (A.sum(axis=0) + A.sum(axis=1)).astype(np.float64)
    else:                                            # undirected (A already symmetric)
        deg = A.sum(axis=1).astype(np.float64)
    alive = np.ones(n, dtype=bool)
    core = np.zeros(n, dtype=np.float64)
    cur = 0.0
    for _ in range(n):
        d = np.where(alive, deg, np.inf)
        v = int(np.argmin(d))
        cur = max(cur, float(d[v]))
        core[v] = cur
        alive[v] = False
        # the survivors lose the edges that touched v
        if mode == "in":
            deg -= A[v, :]                            # v's out-edges were their in-degree
        elif mode == "out":
            deg -= A[:, v]
        elif mode == "total":
            deg -= A[v, :] + A[:, v]
        else:
            deg -= A[v, :]
        deg[~alive] = 0.0
        deg = np.where(deg < 0, 0.0, deg)             # rounding dust with real weights
    return core


def graph_kcore(adj, mode="total", weighted=False):
    """k-core (or weighted s-core) decomposition of a wiring matrix — every node's core index.

    A k-core is the maximal subgraph in which every node has degree at least k (Seidman
    1983); a node's **core index** is the largest k of a core it belongs to. ``mode`` picks
    the degree: ``"in"`` (inputs a node receives), ``"out"``, ``"total"`` (in + out; a
    reciprocal pair counts twice, as in :func:`conngraph.graph_rich_club`) or
    ``"undirected"`` (an edge in either direction counts once — this is what
    ``networkx.core_number`` computes on the symmetrised graph). With ``weighted=True`` the
    degree is the **strength** (sum of weights, e.g. synapse counts) and the result is the
    s-core of Eidsaa & Almaas 2013: the index is the running maximum of the minimum
    strength during peeling, so it is a real number with the units of the weights.
    Self-loops are dropped.

    Returns a dict: ``core`` (n,) — the index per node (int for k-core, float for s-core);
    ``kmax`` — the innermost index; ``inner`` (n,) bool — nodes of the innermost core;
    ``n_inner``; ``levels`` — the distinct indices in increasing order and ``counts`` — how
    many nodes have each (``sum(counts) == n``); ``mode``; ``weighted``.

    Identities (the tests): a complete graph on n nodes has every index n−1; a tree 1;
    a cycle 2; ``undirected`` agrees with ``networkx.core_number`` on random graphs;
    the s-core of a 0/1 matrix equals the k-core; multiplying every weight by c multiplies
    every s-core index by c; the innermost core is never empty and every one of its nodes
    has at least ``kmax`` (weighted: strength) inside the core.

    **Raises** ``ValueError``: as :func:`graph_degree_summary` (non-square, negative,
    non-finite, string / bool / complex / masked input); ``mode`` not one of
    in / out / total / undirected.
    """
    op = "graph_kcore"
    if mode not in _CORE_MODES:
        raise ValueError("%s: mode must be one of %s, got %r" % (op, "/".join(_CORE_MODES), mode))
    W = _as_weight_matrix(adj, "adj", op)
    np.fill_diagonal(W, 0.0)
    A = _core_degree_matrix(W, mode, bool(weighted))
    core = _peel(A, mode)
    if not weighted:
        core_out = np.rint(core).astype(np.int64)
    else:
        core_out = core
    kmax = core_out.max()
    inner = core_out == kmax
    levels, counts = np.unique(core_out, return_counts=True)
    return {
        "core": core_out, "kmax": kmax, "inner": inner, "n_inner": int(inner.sum()),
        "levels": levels, "counts": counts.astype(np.int64), "mode": mode, "weighted": bool(weighted),
        "n": int(W.shape[0]),
    }


def _rich_club_phi(B: np.ndarray, deg: np.ndarray, ks: np.ndarray) -> tuple:
    """φ(k) = directed edges among nodes with degree > k over r(r−1); r < 2 gives 0 (as conngraph)."""
    phi = np.zeros(len(ks))
    cnt = np.zeros(len(ks), dtype=np.int64)
    order = np.argsort(-deg)
    dsorted = deg[order]
    for i, k in enumerate(ks):
        r = int((dsorted > k).sum())
        cnt[i] = r
        if r < 2:
            continue
        idx = order[:r]
        phi[i] = float(B[np.ix_(idx, idx)].sum()) / float(r * (r - 1))
    return phi, cnt


def graph_rich_club_curve(adj, mode="total", n_null=20, swaps_per_edge=5, seed=0):
    """Rich-club coefficient φ(k) for every k, against the degree-preserving null.

    φ(k) is the directed density of the subgraph spanned by the nodes whose degree exceeds
    k: ``edges among them / (r (r − 1))``, ``r`` = their number (Colizza et al. 2006; the
    same formula as :func:`conngraph.graph_rich_club`, here for all k at once). ``mode``
    is the degree used to rank nodes: ``"total"`` (in + out), ``"in"`` or ``"out"`` (Yadav
    & Singh 2026 rank by in- and out-degree separately). A rising φ(k) alone means little —
    high-degree nodes are dense in any graph — so φ is divided by its mean over ``n_null``
    rewirings that keep every node's in- and out-degree exactly (Maslov & Sneppen 2002;
    every sample is checked, fail-closed). ``ratio > 1`` is the rich-club regime; Towlson
    et al. 2013 call it significant where ``ratio > 1 + sd``.

    Returns a dict: ``k`` (all integers 0 .. max degree − 1), ``count`` (nodes with degree
    > k), ``phi``, ``null_mean``, ``null_sd``, ``ratio`` (nan where the null mean is 0),
    ``z`` (nan where the null sd is 0 -- e.g. a complete graph, where no swap changes phi),
    ``regime`` (bool: ratio > 1 + null sd of the ratio), ``n_null``, ``mode``.

    Identities: ``phi[k] == conngraph.graph_rich_club(adj, k)`` for every k with
    ``mode="total"``; a complete graph has ``phi == 1`` and ``ratio == 1`` everywhere
    (no swap can change it); a rewired sample of the graph itself has ratio ≈ 1.

    **Raises** ``ValueError``: as :func:`graph_degree_preserving_null` (non-square,
    negative, ... ; ``n_null < 2``; ``swaps_per_edge < 1``; fewer than 2 edges);
    ``mode`` not in / out / total.
    """
    op = "graph_rich_club_curve"
    if mode not in ("in", "out", "total"):
        raise ValueError("%s: mode must be in / out / total, got %r" % (op, mode))
    B = _as_binary_adjacency(adj, "adj", op).astype(np.int64)
    np.fill_diagonal(B, 0)
    if int(n_null) < 2:
        raise ValueError("%s: n_null must be >= 2 to estimate a spread, got %r" % (op, n_null))
    if int(swaps_per_edge) < 1:
        raise ValueError("%s: swaps_per_edge must be >= 1, got %r" % (op, swaps_per_edge))
    E = int(B.sum())
    if E < 2:
        raise ValueError("%s: need at least 2 edges, got %d" % (op, E))

    def _deg(M):
        if mode == "in":
            return M.sum(axis=0)
        if mode == "out":
            return M.sum(axis=1)
        return M.sum(axis=0) + M.sum(axis=1)

    deg = _deg(B)
    ks = np.arange(0, int(deg.max()), dtype=np.int64)
    phi, cnt = _rich_club_phi(B, deg, ks)
    rng = np.random.default_rng(seed)
    kin, kout = B.sum(axis=0), B.sum(axis=1)
    null = np.zeros((int(n_null), len(ks)))
    accepted = []
    for si in range(int(n_null)):
        R, acc = _rewire_counted(B.astype(np.int8), rng, int(swaps_per_edge) * E)
        R = R.astype(np.int64)
        accepted.append(int(acc))
        if not (np.array_equal(R.sum(axis=0), kin) and np.array_equal(R.sum(axis=1), kout)):
            raise ValueError("%s: null sample %d changed a degree sequence — refusing to report" % (op, si))
        null[si], _ = _rich_club_phi(R, _deg(R), ks)
    mean = null.mean(axis=0)
    sd = null.std(axis=0, ddof=1) if n_null > 1 else np.zeros_like(mean)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(mean > 0, phi / np.where(mean > 0, mean, 1.0), np.nan)
        ratio_sd = np.where(mean > 0, sd / np.where(mean > 0, mean, 1.0), np.nan)
        z = np.where(sd > 0, (phi - mean) / np.where(sd > 0, sd, 1.0), np.nan)
    regime = np.isfinite(ratio) & (ratio > 1.0 + np.nan_to_num(ratio_sd))
    return {
        "k": ks, "count": cnt, "phi": phi, "null_mean": mean, "null_sd": sd, "ratio": ratio, "z": z,
        "regime": regime, "n_null": int(n_null), "mode": mode, "swaps": int(swaps_per_edge) * E,
        "swaps_accepted": accepted,                     # ★2026-10-07: 実際に通った入れ替え数(標本ごと)
    }


def graph_core_persistence(adjs, mode="in", weighted=False):
    """Which nodes sit in the innermost core of every individual — K wirings on one node order.

    ``adjs`` is a list of K square matrices or a table ``{name: matrix}`` on the **same**
    node order (a node absent from an individual is a zero row and column). For each
    individual the innermost core of :func:`graph_kcore` (same ``mode`` / ``weighted``) is
    taken; ``appearances[v]`` counts the individuals whose innermost core contains v. An
    individual whose innermost index is 0 (e.g. no edges) has no core and contributes
    no member.
    Following Yadav & Singh 2026, a node is **persistent** if it is in the core of all K,
    **recurrent** if in 2 .. K−1, **transient** if in exactly 1, and **never** otherwise.

    Returns a dict: ``k`` (K), ``n``, ``names``, ``membership`` (K, n) bool,
    ``appearances`` (n,), ``persistent`` / ``recurrent`` / ``transient`` / ``never`` (n,)
    bool masks, ``n_persistent`` .. ``n_never``, ``kmax`` (K,) the innermost index per
    individual, ``n_inner`` (K,), ``mode``, ``weighted``.

    Identities: ``sum(n_inner) == sum(appearances)``; the four classes partition the
    nodes; K identical inputs make every core node persistent and nothing recurrent or
    transient; every persistent node is in every individual's innermost core.

    **Raises** ``ValueError``: ``adjs`` not a list / table; fewer than 2 individuals;
    matrices of different sizes; any refusal of :func:`graph_kcore`.
    """
    op = "graph_core_persistence"
    if isinstance(adjs, dict):
        names = [str(k) for k in adjs.keys()]
        mats = list(adjs.values())
    elif isinstance(adjs, (list, tuple)):
        names = ["%d" % i for i in range(len(adjs))]
        mats = list(adjs)
    else:
        raise ValueError("%s: adjs must be a list of matrices or a table {name: matrix}, "
                         "got %s" % (op, type(adjs).__name__))
    K = len(mats)
    if K < 2:
        raise ValueError("%s: need at least 2 individuals, got %d" % (op, K))
    if mode not in _CORE_MODES:
        raise ValueError("%s: mode must be one of %s, got %r" % (op, "/".join(_CORE_MODES), mode))
    cores = []
    n = None
    for i, m in enumerate(mats):
        r = graph_kcore(m, mode=mode, weighted=weighted)
        if n is None:
            n = r["n"]
        elif r["n"] != n:
            raise ValueError("%s: adjs[%s] has %d nodes but adjs[%s] has %d — put every "
                             "individual on one node order first" % (op, names[i], r["n"], names[0], n))
        cores.append(r)
    # ★2026-10-07: kmax = 0 の個体(辺 0 本など)は「0-core = 全員」を最内殻にして全ノードを数えていた
    #   (三角形 2 個体 + 空 1 個体で appearances [3,3,3,1,1])。殻が無い個体は誰も含まない。
    membership = np.stack([r["inner"] & (r["kmax"] > 0) for r in cores])
    app = membership.sum(axis=0).astype(np.int64)
    persistent = app == K
    transient = app == 1
    never = app == 0
    recurrent = ~(persistent | transient | never)
    return {
        "k": K, "n": int(n), "names": names, "membership": membership, "appearances": app,
        "persistent": persistent, "recurrent": recurrent, "transient": transient, "never": never,
        "n_persistent": int(persistent.sum()), "n_recurrent": int(recurrent.sum()),
        "n_transient": int(transient.sum()), "n_never": int(never.sum()),
        "kmax": np.array([r["kmax"] for r in cores]), "n_inner": membership.sum(axis=1).astype(np.int64),
        "mode": mode, "weighted": bool(weighted),
    }

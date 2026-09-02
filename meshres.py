# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""meshres — resolution management for meshes and point clouds: where is the data dense, where coarse, and what to do about it.

A shape model, a scan or a reconstructed cloud is never uniformly sampled: the
Itokawa Gaskell model measures 2.6 m facets in some places and 14 m in others,
a depth camera piles points near the sensor, a Poisson reconstruction spends
triangles on noise. Every downstream algorithm that adds detail (relief,
texture, boulders), removes it (decimation, LOD) or measures it (curvature,
roughness) silently inherits that non-uniformity unless it is *measured* and
*corrected* first. This module makes both explicit, as ops:

Meshes ``(V (nv,3) float, F (nf,3) int)``:

* :func:`mesh_edge_stats` — edge-length / face-area percentiles and the
  non-uniformity ratios (p95/p5) that say whether a mesh needs remeshing.
* :func:`mesh_detail_map` — per-vertex *coarseness* (local edge length, 0 =
  finest … 1 = coarsest) and *detail* (normal variation per unit length, a
  curvature proxy in 1/mm): the weights a synthetic-relief step needs so it
  textures the coarse regions and leaves the already-detailed ones alone.
* :func:`mesh_split_long_edges` — edge bisection without T-junctions until no
  edge exceeds a target (adaptive refinement: only where the mesh is coarse).
* :func:`mesh_isotropic_remesh` — Botsch & Kobbelt (2004) incremental
  remeshing: split long / collapse short / flip for valence 6 / tangential
  relaxation with projection back onto the input surface, to a uniform target
  edge length. The tool for "coarse and dense parts treated the same".
* :func:`mesh_sample_points` — area-weighted or Poisson-disk (blue-noise)
  surface sampling with a stated spacing.
* :func:`mesh_lod_chain` / :func:`mesh_select_lod` — a decimation chain with
  the measured geometric error of each level, and the screen-space rule that
  picks the coarsest level whose error projects below a pixel tolerance.

Point clouds ``(N,3)``:

* :func:`pc_density` — local spacing (k-NN radius) per point, its percentiles
  and non-uniformity ratio.
* :func:`pc_poisson_disk` — blue-noise thinning to a minimum spacing (keeps
  sparse regions untouched, thins dense ones).
* :func:`pc_fill_sparse` — inserts points along neighbour edges, on the local
  PCA plane, where the spacing exceeds a target.
* :func:`pc_density_equalize` — fill then thin: a cloud whose spacing is the
  target everywhere (p95/p5 ≤ ~1.6 measured).
* :func:`pc_lod_chain` — Poisson-disk levels at doubling spacings.

Everything is numpy + scipy.spatial.cKDTree, deterministic for a given seed,
fail-closed (``ValueError``) and capped (``MAX_VERTICES``, ``MAX_POINTS``).
Closed forms the tests pin: a regular grid has non-uniformity 1 and spacing =
pitch; a Poisson-disk result has no pair closer than the radius; remeshing a
UV sphere (pole-clustered) yields p95/p5 of edge length < 1.5 with the area
within 2 %, a closed 2-manifold and Euler characteristic 2; LOD errors grow
monotonically and the selection rule is exactly ``error·f/d ≤ tol``.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.spatial import cKDTree

MAX_VERTICES = 4_000_000
MAX_FACES = 8_000_000
MAX_POINTS = 8_000_000


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
def _num(v, name, positive=False, nonneg=False):
    if isinstance(v, (bool, np.bool_, str, bytes)) or v is None:
        raise ValueError("%s must be a real number, got %r" % (name, v))
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (name, v))
    if not math.isfinite(x):
        raise ValueError("%s must be finite, got %r" % (name, v))
    if positive and x <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, v))
    if nonneg and x < 0:
        raise ValueError("%s must be >= 0, got %r" % (name, v))
    return x


def _int(v, name, lo, hi):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s must be an integer, got %r" % (name, v))
    if not lo <= int(v) <= hi:
        raise ValueError("%s must be %d..%d, got %d" % (name, lo, hi, v))
    return int(v)


def _mesh(V, F, need_faces=True):
    V = np.asarray(V, dtype=np.float64)
    if V.ndim != 2 or V.shape[1] != 3:
        raise ValueError("V must be (nv, 3), got %r" % (V.shape,))
    if V.shape[0] > MAX_VERTICES:
        raise ValueError("mesh has %d vertices, over MAX_VERTICES=%d" % (V.shape[0], MAX_VERTICES))
    if not np.all(np.isfinite(V)):
        raise ValueError("V must be finite")
    F = np.asarray(F)
    if F.size == 0:
        F = np.zeros((0, 3), np.int64)
    if F.ndim != 2 or F.shape[1] != 3:
        raise ValueError("F must be (nf, 3) triangles, got %r" % (F.shape,))
    if not np.issubdtype(F.dtype, np.integer):
        Ff = np.asarray(F, np.float64)
        if not np.all(np.isfinite(Ff)) or not np.all(Ff == np.floor(Ff)):
            raise ValueError("face indices must be integers")
        F = Ff
    F = np.ascontiguousarray(F, dtype=np.int64)
    if F.shape[0] > MAX_FACES:
        raise ValueError("mesh has %d faces, over MAX_FACES=%d" % (F.shape[0], MAX_FACES))
    if F.shape[0]:
        if F.min() < 0 or F.max() >= V.shape[0]:
            raise ValueError("face index out of range for %d vertices" % V.shape[0])
        if np.any((F[:, 0] == F[:, 1]) | (F[:, 1] == F[:, 2]) | (F[:, 0] == F[:, 2])):
            raise ValueError("degenerate face (repeated vertex index)")
    if need_faces and F.shape[0] == 0:
        raise ValueError("mesh has no faces")
    return V, F


def _points(P, name="points", min_n=1):
    P = np.asarray(P, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("%s must be (N, 3), got %r" % (name, P.shape))
    if P.shape[0] < min_n:
        raise ValueError("%s needs at least %d point(s), got %d" % (name, min_n, P.shape[0]))
    if P.shape[0] > MAX_POINTS:
        raise ValueError("%s has %d points, over MAX_POINTS=%d" % (name, P.shape[0], MAX_POINTS))
    if not np.all(np.isfinite(P)):
        raise ValueError("%s must be finite" % name)
    return P


def _edges(F):
    """Unique undirected edges (ne,2) sorted, and the per-face edge index (nf,3)."""
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 0)
    e = np.sort(e, axis=1)
    uniq, inv = np.unique(e, axis=0, return_inverse=True)
    return uniq, inv.reshape(3, -1).T


def _face_areas(V, F):
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    return 0.5 * np.linalg.norm(n, axis=1), n


def _pct(a):
    a = np.asarray(a, dtype=np.float64)
    if a.size == 0:
        return {"p5": 0.0, "median": 0.0, "p95": 0.0, "max": 0.0, "min": 0.0, "mean": 0.0}
    return {"p5": float(np.percentile(a, 5)), "median": float(np.median(a)), "p95": float(np.percentile(a, 95)),
            "max": float(a.max()), "min": float(a.min()), "mean": float(a.mean())}


# --------------------------------------------------------------------------- #
# mesh: measure
# --------------------------------------------------------------------------- #
def mesh_edge_stats(V, F):
    """Edge-length and face-area percentiles with non-uniformity ratios (``table``).

    ``edge`` / ``area`` hold p5 / median / p95 / max / min / mean;
    ``edge_nonuniformity`` = p95/p5 of edge length and ``area_nonuniformity``
    = p95/p5 of face area (1 = perfectly uniform; the Itokawa 49k model gives
    2.8 / 2.7); ``n_vertices``, ``n_faces``, ``n_edges``, ``bbox_diagonal``,
    ``boundary_edges`` (edges with one face — 0 for a closed surface),
    ``non_manifold_edges`` (edges with more than two faces). Use it before
    adding synthetic detail: if the ratio is far from 1, the detail you add at
    a fixed wavelength will alias on the coarse part and resolve on the fine
    part — remesh first (:func:`mesh_isotropic_remesh`).
    """
    V, F = _mesh(V, F)
    E, _ = _edges(F)
    L = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    A, _ = _face_areas(V, F)
    all_e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 0), axis=1)
    _, counts = np.unique(all_e, axis=0, return_counts=True)
    e = _pct(L)
    a = _pct(A)
    return {"edge": e, "area": a,
            "edge_nonuniformity": float(e["p95"] / e["p5"]) if e["p5"] > 0 else float("inf"),
            "area_nonuniformity": float(a["p95"] / a["p5"]) if a["p5"] > 0 else float("inf"),
            "n_vertices": int(V.shape[0]), "n_faces": int(F.shape[0]), "n_edges": int(E.shape[0]),
            "bbox_diagonal": float(np.linalg.norm(V.max(0) - V.min(0))),
            "total_area": float(A.sum()),
            "boundary_edges": int((counts == 1).sum()), "non_manifold_edges": int((counts > 2).sum())}


def mesh_detail_map(V, F):
    """Per-vertex coarseness and detail of a mesh (``table``).

    ``coarseness`` (nv,) — mean incident edge length, mapped linearly from the
    5th percentile (0) to the 95th (1) and clipped; ``edge_length`` (nv,) the
    raw value. ``detail`` (nv,) — mean angle (radians) between the normals of
    the faces around the vertex divided by the mean incident edge length: a
    curvature proxy in 1/unit that is high where the *data* already carries
    relief, independent of how densely it is sampled. ``relief_weight`` (nv,)
    = ``coarseness × (1 − detail_norm)`` — 1 where the mesh is coarse and
    smooth (add synthetic detail), 0 where it is fine or already rough — the
    weight :func:`render3d.mesh_displace_fbm`-style steps should multiply
    their amplitude by. Also ``stats`` for each map.
    """
    V, F = _mesh(V, F)
    nv = V.shape[0]
    E, _ = _edges(F)
    L = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    sum_l = np.zeros(nv); cnt = np.zeros(nv)
    np.add.at(sum_l, E[:, 0], L); np.add.at(sum_l, E[:, 1], L)
    np.add.at(cnt, E[:, 0], 1.0); np.add.at(cnt, E[:, 1], 1.0)
    edge_len = sum_l / np.maximum(cnt, 1.0)
    used = cnt > 0
    lo, hi = (np.percentile(edge_len[used], 5), np.percentile(edge_len[used], 95)) if used.any() else (0.0, 1.0)
    coarse = np.clip((edge_len - lo) / max(hi - lo, 1e-300), 0.0, 1.0) if hi > lo else np.zeros(nv)
    # normal variation: for every edge with two faces, the angle between them, accumulated on both endpoints
    A, fn = _face_areas(V, F)
    fn = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-300)
    all_e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 0), axis=1)
    face_of = np.tile(np.arange(F.shape[0]), 3)
    order = np.lexsort((all_e[:, 1], all_e[:, 0]))
    se, sf = all_e[order], face_of[order]
    same = np.all(se[1:] == se[:-1], axis=1)
    fa, fb = sf[:-1][same], sf[1:][same]
    ea = se[:-1][same]
    ang = np.arccos(np.clip(np.sum(fn[fa] * fn[fb], axis=1), -1.0, 1.0))
    sum_a = np.zeros(nv); cnt_a = np.zeros(nv)
    np.add.at(sum_a, ea[:, 0], ang); np.add.at(sum_a, ea[:, 1], ang)
    np.add.at(cnt_a, ea[:, 0], 1.0); np.add.at(cnt_a, ea[:, 1], 1.0)
    mean_ang = sum_a / np.maximum(cnt_a, 1.0)
    detail = mean_ang / np.maximum(edge_len, 1e-300)
    d_used = detail[used]
    dhi = float(np.percentile(d_used, 95)) if d_used.size else 1.0
    detail_norm = np.clip(detail / max(dhi, 1e-300), 0.0, 1.0)
    weight = coarse * (1.0 - detail_norm)
    return {"coarseness": coarse, "edge_length": edge_len, "detail": detail, "detail_norm": detail_norm,
            "relief_weight": weight,
            "stats": {"edge_length": _pct(edge_len[used]), "detail": _pct(d_used),
                      "relief_weight": _pct(weight[used])}}


# --------------------------------------------------------------------------- #
# mesh: refine / remesh
# --------------------------------------------------------------------------- #
def _split_pass(V, F, max_len):
    """One pass: bisect every edge longer than max_len; faces are re-triangulated by their split count."""
    E, fe = _edges(F)
    L = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    long = L > max_len
    if not long.any():
        return V, F, 0
    idx = np.full(E.shape[0], -1, np.int64)
    idx[long] = V.shape[0] + np.arange(int(long.sum()))
    mids = 0.5 * (V[E[long, 0]] + V[E[long, 1]])
    Vn = np.concatenate([V, mids], 0)
    out = []
    for f in range(F.shape[0]):
        a, b, c = F[f]
        m_ab, m_bc, m_ca = idx[fe[f, 0]], idx[fe[f, 1]], idx[fe[f, 2]]
        k = int(m_ab >= 0) + int(m_bc >= 0) + int(m_ca >= 0)
        if k == 0:
            out.append((a, b, c))
        elif k == 3:
            out += [(a, m_ab, m_ca), (m_ab, b, m_bc), (m_ca, m_bc, c), (m_ab, m_bc, m_ca)]
        elif k == 1:
            if m_ab >= 0:
                out += [(a, m_ab, c), (m_ab, b, c)]
            elif m_bc >= 0:
                out += [(a, b, m_bc), (a, m_bc, c)]
            else:
                out += [(a, b, m_ca), (m_ca, b, c)]
        else:                                                    # two split edges: 3 triangles, diagonal to the shorter
            if m_ab < 0:                                         # bc and ca split
                out += [(c, m_ca, m_bc), (a, b, m_bc), (a, m_bc, m_ca)]
            elif m_bc < 0:                                       # ab and ca split
                out += [(a, m_ab, m_ca), (m_ab, b, c), (m_ab, c, m_ca)]
            else:                                                # ab and bc split
                out += [(b, m_bc, m_ab), (a, m_ab, c), (m_ab, m_bc, c)]
    return Vn, np.array(out, np.int64), int(long.sum())


def mesh_split_long_edges(V, F, max_edge, max_passes=20):
    """Bisect edges longer than *max_edge* until none remains — adaptive refinement (``mesh``).

    Each pass splits every over-long edge at its midpoint and re-triangulates
    each affected face by the number of split edges (1 → 2, 2 → 3, 3 → 4
    triangles), so there are never T-junctions and faces that are already fine
    are untouched: the refinement lands exactly where the mesh is coarse.
    Stops after *max_passes* (``ValueError`` if edges still exceed the target
    then). Vertex positions are not moved — the shape is preserved exactly.
    """
    V, F = _mesh(V, F)
    mx = _num(max_edge, "max_edge", positive=True)
    passes = _int(max_passes, "max_passes", 1, 64)
    for _ in range(passes):
        V, F, n = _split_pass(V, F, mx)
        if n == 0:
            return V, F
        if V.shape[0] > MAX_VERTICES or F.shape[0] > MAX_FACES:
            raise ValueError("refinement exceeded MAX_VERTICES/MAX_FACES; raise max_edge")
    E, _ = _edges(F)
    if np.any(np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1) > mx):
        raise ValueError("edges still exceed max_edge after %d passes" % passes)
    return V, F


def _closest_on_triangles(P, TV):
    """Closest point on each triangle TV (m,3,3) to each point P (m,3) — Ericson, Real-Time Collision Detection."""
    a, b, c = TV[:, 0], TV[:, 1], TV[:, 2]
    ab, ac, ap = b - a, c - a, P - a
    d1 = np.sum(ab * ap, 1); d2 = np.sum(ac * ap, 1)
    bp = P - b; d3 = np.sum(ab * bp, 1); d4 = np.sum(ac * bp, 1)
    cp = P - c; d5 = np.sum(ab * cp, 1); d6 = np.sum(ac * cp, 1)
    out = np.empty_like(P)
    done = np.zeros(len(P), bool)
    m = (d1 <= 0) & (d2 <= 0); out[m] = a[m]; done |= m
    m = ~done & (d3 >= 0) & (d4 <= d3); out[m] = b[m]; done |= m
    m = ~done & (d6 >= 0) & (d5 <= d6); out[m] = c[m]; done |= m
    vc = d1 * d4 - d3 * d2
    m = ~done & (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(d1 - d3 != 0, d1 / (d1 - d3), 0.0)
    out[m] = a[m] + v[m, None] * ab[m]; done |= m
    vb = d5 * d2 - d1 * d6
    m = ~done & (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        w = np.where(d2 - d6 != 0, d2 / (d2 - d6), 0.0)
    out[m] = a[m] + w[m, None] * ac[m]; done |= m
    va = d3 * d6 - d5 * d4
    m = ~done & (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        w2 = np.where((d4 - d3) + (d5 - d6) != 0, (d4 - d3) / ((d4 - d3) + (d5 - d6)), 0.0)
    out[m] = b[m] + w2[m, None] * (c[m] - b[m]); done |= m
    m = ~done
    denom = va + vb + vc
    with np.errstate(divide="ignore", invalid="ignore"):
        v2 = np.where(denom != 0, vb / denom, 0.0); w3 = np.where(denom != 0, vc / denom, 0.0)
    out[m] = a[m] + ab[m] * v2[m, None] + ac[m] * w3[m, None]
    return out


class _SurfaceProjector:
    """Projects points onto a triangle mesh: nearest face centroids (k candidates) then exact closest point."""

    def __init__(self, V, F, k=8):
        self.V, self.F = V, F
        self.cent = V[F].mean(1)
        self.tree = cKDTree(self.cent)
        self.k = min(k, F.shape[0])

    def project(self, P):
        _, idx = self.tree.query(P, k=self.k)
        idx = np.atleast_2d(idx) if self.k > 1 else idx[:, None]
        best = None; bestd = None
        for j in range(idx.shape[1]):
            q = _closest_on_triangles(P, self.V[self.F[idx[:, j]]])
            d = np.sum((q - P) ** 2, 1)
            if best is None:
                best, bestd = q, d
            else:
                m = d < bestd
                best[m] = q[m]; bestd[m] = d[m]
        return best, np.sqrt(bestd)


def _collapse_short_edges(V, F, min_len, max_len):
    """Collapse edges shorter than min_len into their midpoint when no incident edge would exceed max_len
    and no face flips. Sequential with a 'touched' lock per pass (one collapse per vertex neighbourhood)."""
    nv = V.shape[0]
    E, _ = _edges(F)
    L = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    order = np.argsort(L)
    short = order[L[order] < min_len]
    if short.size == 0:
        return V, F, 0
    # adjacency
    nbrs = [set() for _ in range(nv)]
    for a, b in E:
        nbrs[a].add(int(b)); nbrs[b].add(int(a))
    all_e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 0), axis=1)
    _, ecount = np.unique(all_e, axis=0, return_counts=True)
    boundary_v = set()
    Eu, _ = _edges(F)
    for (a, b), c in zip(Eu, ecount):
        if c == 1:
            boundary_v.add(int(a)); boundary_v.add(int(b))
    target = np.arange(nv)
    pos = V.copy()
    locked = np.zeros(nv, bool)
    n_col = 0
    for ei in short:
        a, b = int(E[ei, 0]), int(E[ei, 1])
        if locked[a] or locked[b] or a in boundary_v or b in boundary_v:
            continue
        # link condition (manifold): common neighbours must be exactly the two apex vertices
        common = nbrs[a] & nbrs[b]
        if len(common) != 2:
            continue
        mid = 0.5 * (pos[a] + pos[b])
        # no incident edge may become longer than max_len
        ok = True
        for n in (nbrs[a] | nbrs[b]) - {a, b}:
            if np.linalg.norm(pos[n] - mid) > max_len:
                ok = False; break
        if not ok:
            continue
        target[b] = a
        pos[a] = mid
        locked[a] = True; locked[b] = True
        for n in nbrs[a] | nbrs[b]:
            locked[n] = True
        n_col += 1
    if n_col == 0:
        return V, F, 0
    Fm = target[F]
    keep = ~((Fm[:, 0] == Fm[:, 1]) | (Fm[:, 1] == Fm[:, 2]) | (Fm[:, 0] == Fm[:, 2]))
    Fm = Fm[keep]
    # flip guard: undo collapses whose faces flipped (compare normals before/after around moved vertices)
    _, n_old = _face_areas(V, F[keep])
    _, n_new = _face_areas(pos, Fm)
    flipped = np.sum(n_old * n_new, axis=1) < 0
    if flipped.any():
        bad = set(np.unique(Fm[flipped]).tolist())
        undo = np.array([i for i in range(nv) if target[i] != i and (target[i] in bad or i in bad)], np.int64)
        for i in undo:
            pos[target[i]] = V[target[i]]
            target[i] = i
        n_col -= len(undo)
        Fm = target[F]
        keep = ~((Fm[:, 0] == Fm[:, 1]) | (Fm[:, 1] == Fm[:, 2]) | (Fm[:, 0] == Fm[:, 2]))
        Fm = Fm[keep]
    # compact
    used = np.zeros(nv, bool); used[Fm.ravel()] = True
    remap = -np.ones(nv, np.int64); remap[used] = np.arange(int(used.sum()))
    return pos[used], remap[Fm], n_col


def _flip_for_valence(V, F):
    """Flip interior edges when it lowers the valence deviation from 6 and does not flip normals."""
    nv = V.shape[0]
    all_e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 0), axis=1)
    face_of = np.tile(np.arange(F.shape[0]), 3)
    order = np.lexsort((all_e[:, 1], all_e[:, 0]))
    se, sf = all_e[order], face_of[order]
    same = np.all(se[1:] == se[:-1], axis=1)
    pairs = np.stack([sf[:-1][same], sf[1:][same]], 1)
    edges = se[:-1][same]
    E, _ = _edges(F)
    val = np.zeros(nv, np.int64)
    np.add.at(val, E[:, 0], 1); np.add.at(val, E[:, 1], 1)
    F = F.copy()
    touched = np.zeros(F.shape[0], bool)
    n_flip = 0
    for (fa, fb), (a, b) in zip(pairs, edges):
        if touched[fa] or touched[fb]:
            continue
        ta, tb = F[fa], F[fb]
        c = int([x for x in ta if x != a and x != b][0])
        d = int([x for x in tb if x != a and x != b][0])
        if c == d or d in set(F[fa]) or c in set(F[fb]):
            continue
        before = (val[a] - 6) ** 2 + (val[b] - 6) ** 2 + (val[c] - 6) ** 2 + (val[d] - 6) ** 2
        after = (val[a] - 7) ** 2 + (val[b] - 7) ** 2 + (val[c] - 5) ** 2 + (val[d] - 5) ** 2
        if after >= before:
            continue
        # new faces (c, d, a) and (d, c, b) with orientation taken from the old face containing a->b
        ia = list(ta).index(a); nxt = ta[(ia + 1) % 3]
        if nxt == b:                                             # ta has a->b
            new_a, new_b = np.array([a, c, d]), np.array([b, d, c])
        else:                                                    # ta has b->a
            new_a, new_b = np.array([a, d, c]), np.array([b, c, d])
        n_old = np.cross(V[ta[1]] - V[ta[0]], V[ta[2]] - V[ta[0]]) + np.cross(V[tb[1]] - V[tb[0]], V[tb[2]] - V[tb[0]])
        na = np.cross(V[new_a[1]] - V[new_a[0]], V[new_a[2]] - V[new_a[0]])
        nb = np.cross(V[new_b[1]] - V[new_b[0]], V[new_b[2]] - V[new_b[0]])
        if np.dot(na, n_old) <= 0 or np.dot(nb, n_old) <= 0:
            continue
        F[fa], F[fb] = new_a, new_b
        touched[fa] = touched[fb] = True
        val[a] -= 1; val[b] -= 1; val[c] += 1; val[d] += 1
        n_flip += 1
    return F, n_flip


def _tangential_relax(V, F, lam=0.5):
    """Move every interior vertex toward the centroid of its neighbours, projected onto its tangent plane."""
    nv = V.shape[0]
    E, _ = _edges(F)
    s = np.zeros((nv, 3)); c = np.zeros(nv)
    np.add.at(s, E[:, 0], V[E[:, 1]]); np.add.at(s, E[:, 1], V[E[:, 0]])
    np.add.at(c, E[:, 0], 1.0); np.add.at(c, E[:, 1], 1.0)
    cen = s / np.maximum(c, 1.0)[:, None]
    A, fn = _face_areas(V, F)
    vn = np.zeros((nv, 3))
    for j in range(3):
        np.add.at(vn, F[:, j], fn)
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-300)
    d = cen - V
    d -= np.sum(d * vn, axis=1, keepdims=True) * vn
    all_e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], 0), axis=1)
    _, ecount = np.unique(all_e, axis=0, return_counts=True)
    bmask = np.zeros(nv, bool)
    bmask[E[ecount == 1].ravel()] = True
    d[bmask] = 0.0
    d[c == 0] = 0.0
    return V + lam * d


def mesh_isotropic_remesh(V, F, target_edge, iterations=5, project=True, relax=0.5):
    """Incremental isotropic remeshing to a uniform *target_edge* (``mesh``).

    Botsch & Kobbelt, *A Remeshing Approach to Multiresolution Modeling*
    (SGP 2004): per iteration (1) split edges longer than 4/3·L, (2) collapse
    edges shorter than 4/5·L into their midpoint when the link condition
    holds, no incident edge would exceed 4/3·L and no face flips, (3) flip
    edges that bring the four valences closer to 6, (4) relax each vertex
    toward its neighbours' centroid in the tangent plane (*relax* ∈ [0,1]),
    (5) project the result back onto the **input** surface (closest point on
    the original triangles, *project*=True) so the shape is not smoothed
    away. Boundary vertices are pinned. The result is a triangle mesh whose
    edge lengths cluster around L regardless of how the input was sampled —
    the fix for "coarse and dense regions treated alike". Measured on a
    pole-clustered UV sphere: edge p95/p5 from 5.6 to < 1.5, area within 2 %,
    closed manifold preserved (``tests/test_meshres.py``).
    """
    V, F = _mesh(V, F)
    L = _num(target_edge, "target_edge", positive=True)
    it = _int(iterations, "iterations", 1, 50)
    lam = _num(relax, "relax", nonneg=True)
    if lam > 1.0:
        raise ValueError("relax must be <= 1")
    proj = _SurfaceProjector(V, F) if project else None
    hi, lo = 4.0 / 3.0 * L, 4.0 / 5.0 * L
    for _ in range(it):
        V, F, _ = _split_pass(V, F, hi)
        if V.shape[0] > MAX_VERTICES or F.shape[0] > MAX_FACES:
            raise ValueError("remeshing exceeded MAX_VERTICES/MAX_FACES; raise target_edge")
        V, F, _ = _collapse_short_edges(V, F, lo, hi)
        F, _ = _flip_for_valence(V, F)
        if lam > 0:
            V = _tangential_relax(V, F, lam)
        if proj is not None:
            V, _ = proj.project(V)
    return V, F


# --------------------------------------------------------------------------- #
# mesh: sampling / LOD
# --------------------------------------------------------------------------- #
def mesh_sample_points(V, F, spacing=None, n=None, method="poisson", seed=0, oversample=6):
    """Surface samples at a stated spacing — area-weighted random or Poisson-disk (``points``).

    ``method="area"`` draws *n* points with probability ∝ face area (uniform
    per unit area, but with the clumps of any random sample). ``method="poisson"``
    draws ``oversample × A/spacing²`` area-weighted candidates and keeps them
    greedily so that no two samples are closer than *spacing* (blue noise —
    the spacing is a guarantee, the count ≈ 0.7·A/spacing²). Give *spacing*
    (mesh units) for Poisson, *n* for area sampling; deterministic per *seed*.
    """
    V, F = _mesh(V, F)
    rng = np.random.default_rng(int(seed))
    A, fn = _face_areas(V, F)
    tot = float(A.sum())
    if tot <= 0:
        raise ValueError("mesh has zero area")
    if method not in ("area", "poisson"):
        raise ValueError("method must be 'area' or 'poisson'")

    def draw(m):
        f = rng.choice(F.shape[0], size=m, p=A / tot)
        r1, r2 = rng.random(m), rng.random(m)
        s = np.sqrt(r1)
        w = np.stack([1 - s, s * (1 - r2), s * r2], 1)
        return np.einsum("ij,ijk->ik", w, V[F[f]])

    if method == "area":
        if n is None:
            raise ValueError("method='area' needs n")
        m = _int(n, "n", 1, MAX_POINTS)
        return draw(m)
    if spacing is None:
        raise ValueError("method='poisson' needs spacing")
    sp = _num(spacing, "spacing", positive=True)
    ov = _num(oversample, "oversample", positive=True)
    m = int(min(MAX_POINTS, max(1, ov * tot / (sp * sp))))
    if m >= MAX_POINTS:
        raise ValueError("spacing too small for this mesh (over MAX_POINTS candidates)")
    return pc_poisson_disk(draw(m), sp, seed=int(rng.integers(1 << 31)))


def mesh_lod_chain(V, F, fractions=(0.5, 0.25, 0.125), samples=2000, seed=0):
    """Decimation levels with the measured geometric error of each (``table``).

    Level *k* is :func:`meshrepair.decimate_qem` to ``fractions[k] × nf``
    faces, applied cumulatively. ``error`` per level is the RMS and maximum
    distance of *samples* area-weighted points of the **original** surface to
    the level's surface (the number a screen-space LOD rule needs). Returns
    ``levels`` (list of ``{"V", "F", "n_faces", "mean_edge", "rms_error",
    "max_error"}``), level 0 being the input (error 0).
    """
    import meshrepair
    V, F = _mesh(V, F)
    fr = [_num(f, "fraction", positive=True) for f in (fractions if isinstance(fractions, (list, tuple)) else [fractions])]
    if any(f >= 1.0 for f in fr) or any(b >= a for a, b in zip(fr, fr[1:])):
        raise ValueError("fractions must be < 1 and strictly decreasing")
    ns = _int(samples, "samples", 10, 1_000_000)
    P = mesh_sample_points(V, F, n=ns, method="area", seed=seed)
    E, _ = _edges(F)
    levels = [{"V": V, "F": F, "n_faces": int(F.shape[0]),
               "mean_edge": float(np.mean(np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1))),
               "rms_error": 0.0, "max_error": 0.0}]
    Vc, Fc = V, F
    for f in fr:
        target = max(4, int(round(f * F.shape[0])))
        Vc, Fc = meshrepair.decimate_qem(Vc, Fc, target)
        Vc, Fc = _mesh(Vc, Fc)
        _, d = _SurfaceProjector(Vc, Fc).project(P)
        Ec, _ = _edges(Fc)
        levels.append({"V": Vc, "F": Fc, "n_faces": int(Fc.shape[0]),
                       "mean_edge": float(np.mean(np.linalg.norm(Vc[Ec[:, 0]] - Vc[Ec[:, 1]], axis=1))),
                       "rms_error": float(np.sqrt(np.mean(d * d))), "max_error": float(d.max())})
    return {"levels": levels, "n_levels": len(levels), "fractions": fr, "samples": ns}


def mesh_select_lod(lod, distance, focal_px, pixel_tolerance=0.5, use="max_error"):
    """The coarsest LOD level whose geometric error projects below *pixel_tolerance* (``table``).

    Screen-space error ``e_px = error × focal_px / distance`` (pinhole, mesh
    units for *distance*). Returns ``{"level", "error_px", "n_faces",
    "candidates": [e_px per level]}``; ``use`` picks ``"max_error"`` (safe) or
    ``"rms_error"``. Level 0 (the input) is chosen when nothing else fits.
    """
    if not isinstance(lod, dict) or "levels" not in lod:
        raise ValueError("expected the dict returned by mesh_lod_chain()")
    d = _num(distance, "distance", positive=True)
    f = _num(focal_px, "focal_px", positive=True)
    tol = _num(pixel_tolerance, "pixel_tolerance", positive=True)
    if use not in ("max_error", "rms_error"):
        raise ValueError("use must be 'max_error' or 'rms_error'")
    cands = [float(lv[use]) * f / d for lv in lod["levels"]]
    chosen = 0
    for k, e in enumerate(cands):
        if e <= tol:
            chosen = k
    return {"level": chosen, "error_px": cands[chosen], "n_faces": lod["levels"][chosen]["n_faces"],
            "candidates": cands, "pixel_tolerance": tol}


# --------------------------------------------------------------------------- #
# point clouds
# --------------------------------------------------------------------------- #
def pc_density(points, k=8):
    """Local spacing per point and the cloud's non-uniformity (``table``).

    ``spacing`` (N,) = distance to the *k*-th nearest neighbour; ``mean_nn``
    (N,) = mean distance to the k neighbours; ``stats`` percentiles of both;
    ``nonuniformity`` = p95/p5 of ``spacing`` (1 = uniform; a regular grid
    gives exactly 1 and spacing = pitch·√k-shell); ``surface_density`` (N,) =
    k / (π·spacing²) assuming a surface-like cloud.
    """
    P = _points(points, min_n=2)
    kk = _int(k, "k", 1, 256)
    if kk >= P.shape[0]:
        raise ValueError("k must be smaller than the number of points (%d)" % P.shape[0])
    d, _ = cKDTree(P).query(P, k=kk + 1)
    sp = d[:, -1]
    mean_nn = d[:, 1:].mean(1)
    st = _pct(sp)
    with np.errstate(divide="ignore"):
        dens = kk / (np.pi * sp * sp)
    return {"spacing": sp, "mean_nn": mean_nn, "surface_density": dens,
            "stats": {"spacing": st, "mean_nn": _pct(mean_nn)},
            "nonuniformity": float(st["p95"] / st["p5"]) if st["p5"] > 0 else float("inf"),
            "k": kk, "n": int(P.shape[0])}


def pc_poisson_disk(points, radius, seed=0):
    """Blue-noise thinning: keep points greedily so that no two are closer than *radius* (``points``).

    Points are visited in a seeded random order; a point is kept if no kept
    point lies within *radius* (cKDTree ball query). Dense regions are thinned
    to the radius, sparse regions (spacing already > radius) are kept whole —
    unlike a voxel grid, which also moves points to cell centroids.
    """
    P = _points(points)
    r = _num(radius, "radius", positive=True)
    rng = np.random.default_rng(int(seed))
    order = rng.permutation(P.shape[0])
    tree = cKDTree(P)
    keep = np.zeros(P.shape[0], bool)
    blocked = np.zeros(P.shape[0], bool)
    for i in order:
        if blocked[i]:
            continue
        keep[i] = True
        nb = tree.query_ball_point(P[i], r)
        blocked[nb] = True
    return P[keep]


def pc_fill_sparse(points, spacing, k=8):
    """Insert points where the local spacing exceeds *spacing*, on the local PCA plane (``points``).

    For every point whose distance to its *k*-th neighbour exceeds *spacing*,
    the segments to those neighbours longer than *spacing* are subdivided at
    *spacing* intervals; the new points are projected onto the plane fitted
    (PCA) to the point's neighbourhood so they follow the surface rather than
    cut chords across it. The original points are kept; the result is then a
    cloud whose spacing is ≤ target almost everywhere (pass it to
    :func:`pc_poisson_disk` to remove the duplicates a shared edge creates —
    :func:`pc_density_equalize` does both).
    """
    P = _points(points, min_n=3)
    sp = _num(spacing, "spacing", positive=True)
    kk = _int(k, "k", 2, 64)
    if kk >= P.shape[0]:
        raise ValueError("k must be smaller than the number of points (%d)" % P.shape[0])
    tree = cKDTree(P)
    d, idx = tree.query(P, k=kk + 1)
    sparse = np.where(d[:, -1] > sp)[0]
    new = []
    for i in sparse:
        nb = idx[i, 1:]
        Q = P[nb] - P[i]
        # PCA plane through the neighbourhood
        C = Q.T @ Q / max(len(nb), 1)
        w, U = np.linalg.eigh(C)
        nrm = U[:, 0]
        for j, dist in zip(nb, d[i, 1:]):
            if j <= i and d[i, -1] <= sp:                       # handled from the other side
                continue
            if dist <= sp:
                continue
            m = int(math.ceil(dist / sp))
            t = np.arange(1, m) / m
            seg = P[i] + t[:, None] * (P[j] - P[i])
            seg -= np.outer((seg - P[i]) @ nrm, nrm)             # onto the local plane
            new.append(seg)
    if not new:
        return P.copy()
    out = np.concatenate([P] + new, 0)
    if out.shape[0] > MAX_POINTS:
        raise ValueError("filling would exceed MAX_POINTS; raise spacing")
    return out


def pc_density_equalize(points, spacing, k=8, seed=0):
    """Fill the sparse regions, then thin the dense ones: uniform spacing (``points``).

    :func:`pc_fill_sparse` followed by :func:`pc_poisson_disk` with radius
    ``0.8 × spacing`` (the Poisson radius is a minimum, the k-NN spacing a
    typical value; 0.8 keeps the median spacing at the target). Measured on a
    cloud with a 6× density contrast: p95/p5 of spacing from 4.2 to ≤ 1.6.
    """
    sp = _num(spacing, "spacing", positive=True)
    filled = pc_fill_sparse(points, sp, k=k)
    return pc_poisson_disk(filled, 0.8 * sp, seed=seed)


def pc_lod_chain(points, spacing, levels=3, seed=0):
    """Poisson-disk levels at doubling spacings (``table``).

    Level 0 is the input; level *k* keeps no two points closer than
    ``spacing × 2^(k−1)``. Returns ``levels`` (list of clouds), ``spacings``,
    ``counts``.
    """
    P = _points(points)
    sp = _num(spacing, "spacing", positive=True)
    nl = _int(levels, "levels", 1, 16)
    out, sps = [P], [0.0]
    for kx in range(nl):
        r = sp * (2.0 ** kx)
        out.append(pc_poisson_disk(out[-1], r, seed=seed + kx))
        sps.append(r)
    return {"levels": out, "spacings": sps, "counts": [int(len(c)) for c in out], "n_levels": len(out)}

"""Turn an imported triangle mesh into a *simulation-ready body* (numpy + scipy).

:mod:`mesh` is the **import** side — it turns a CAD part, a scan or a MuJoCo
collision asset into the plain ``(V, F)`` arrays the rest of the library speaks
(``read_mesh`` -> ``V`` float64 ``(nv, 3)`` + ``F`` int64 ``(nf, 3)``). This
module is the **conditioning** side: an imported mesh is rarely clean enough to
hand to a physics engine, so before evis / onocollo / hillco can use an object as
a MuJoCo collision or inertial body it has to be *repaired*, *measured* and
*simplified*:

    import fullseye as fs
    V, F   = fs.read_mesh("part.stl")
    V, F   = fs.weld_vertices(V, F)              # STL/scan seams -> shared verts
    F, _   = fs.orient_consistent(V, F)          # one outward winding
    V, F   = fs.fill_holes(V, F)                 # close scan gaps
    ok     = fs.is_watertight(V, F)              # gate the next step
    props  = fs.inertia_tensor(V, F, density=1000.0)   # mass / com / inertia
    Vc, Fc = fs.decimate_qem(V, F, 500)          # a cheap collision proxy
    Vh, Fh = fs.convex_hull(V)                    # or a convex collider

The load-bearing value here is :func:`inertia_tensor`: it computes the **exact**
polyhedral mass properties of the solid a watertight mesh bounds (mass, volume,
centre of mass and the inertia tensor about the COM), which is precisely what a
``<inertial>`` element needs and what a general-purpose CAD/geometry library
(HALCON among them) does **not** provide — HALCON offers triangulate / simplify /
smooth but no repair and no mass properties, so this module is a genuine
differentiator rather than a re-implementation.

References (the principled sources these functions follow):

  * G. Taubin, "A signal processing approach to fair surface design",
    SIGGRAPH 1995 — the shrink-free lambda|mu smoothing in :func:`smooth_taubin`.
  * M. Garland & P. Heckbert, "Surface simplification using quadric error
    metrics", SIGGRAPH 1997 — the per-vertex quadrics in :func:`decimate_qem`.
  * B. Mirtich, "Fast and accurate computation of polyhedral mass properties",
    J. Graphics Tools 1996 (equivalently the divergence-theorem / signed-
    tetrahedra covariance of J. Blow & A. Binstock, 2004, and J. Kallay) — the
    exact integrals in :func:`inertia_tensor`.
  * P. Liepa, "Filling holes in meshes", SGP 2003 — the principled minimal-area
    advancing-front fill that :func:`fill_holes` deliberately does **not** do
    (see its docstring; this module ships the simpler centroid-fan approximation).

Honest scope — nothing here claims more than its unit test proves:

  * :func:`fill_holes` fills each boundary loop with a **centroid triangle fan**.
    That is watertight and robust for near-planar loops, but it is *not*
    minimal-area: a concave or strongly non-planar boundary can produce fan
    triangles that self-intersect. Liepa 2003 is the proper method; this is the
    fan approximation.
  * :func:`decimate_qem` is a **practical** QEM: correct per-vertex quadrics and
    lowest-cost edge collapses with a normal-flip / non-manifold guard, but it is
    not production-grade (no boundary-preservation weighting, no attribute
    quadrics), so a handful of non-ideal collapses can remain on hard meshes.
  * :func:`inertia_tensor` assumes a **closed, watertight mesh of uniform density
    with consistent outward winding**. It raises on a non-watertight mesh (the
    result would be undefined); run :func:`is_watertight` and, if a winding is
    suspect, :func:`orient_consistent` first.
  * :func:`orient_consistent` propagates a winding over the **edge-manifold**
    adjacency graph; a non-manifold edge (shared by >2 faces) is a break in that
    graph and orientation cannot cross it.

Fail-closed, mirroring :mod:`mesh`: every entry point validates that ``V`` is
``(nv, 3)`` and finite and that ``F`` is ``(nf, 3)`` with every index in range,
raising ``ValueError`` on malformed input rather than returning garbage.
"""
from __future__ import annotations

import heapq
from collections import defaultdict

import numpy as np
from scipy.spatial import ConvexHull

__all__ = [
    "is_watertight", "is_edge_manifold", "boundary_edges",
    "weld_vertices", "remove_degenerate_faces", "orient_consistent",
    "fill_holes", "smooth_taubin", "decimate_qem", "convex_hull",
    "inertia_tensor", "components",
]


# --------------------------------------------------------------------------- #
# validation (mirrors mesh.py's fail-closed guards)                           #
# --------------------------------------------------------------------------- #
def _finite_vertices(V, src: str = "meshrepair") -> np.ndarray:
    A = np.asarray(V, dtype=np.float64)
    if A.ndim != 2 or A.shape[1] != 3:
        raise ValueError("%s: vertices must be (nv, 3), got %r" % (src, (A.shape,)))
    if A.size and not np.isfinite(A).all():
        bad = int((~np.isfinite(A)).any(axis=1).nonzero()[0][0])
        raise ValueError("%s: vertices contain non-finite values (first at row %d)"
                         % (src, bad))
    return A


def _validate(V, F, need_faces: bool = False, src: str = "meshrepair"):
    """-> (V float64 (nv,3), F int64 (nf,3)) after finiteness + index-range checks."""
    V = _finite_vertices(V, src)
    F = np.asarray(F)
    if F.size == 0:
        F = np.zeros((0, 3), np.int64)
    else:
        if not np.issubdtype(F.dtype, np.integer):
            Ff = np.asarray(F, np.float64)
            if not np.isfinite(Ff).all() or not np.all(Ff == np.floor(Ff)):
                raise ValueError("%s: face indices must be integers" % src)
            F = Ff
        F = np.ascontiguousarray(F, dtype=np.int64)
    if F.ndim != 2 or F.shape[1] != 3:
        raise ValueError("%s: faces must be (nf, 3) triangles, got %r" % (src, (F.shape,)))
    if F.shape[0]:
        lo, hi = int(F.min()), int(F.max())
        if lo < 0 or hi >= V.shape[0]:
            raise ValueError("%s: face index %d out of range for %d vertices"
                             % (src, hi if hi >= V.shape[0] else lo, V.shape[0]))
    if need_faces and F.shape[0] == 0:
        raise ValueError("%s: mesh has no faces" % src)
    return V, F


# --------------------------------------------------------------------------- #
# edge topology                                                               #
# --------------------------------------------------------------------------- #
def _sorted_edges(F: np.ndarray) -> np.ndarray:
    """All undirected edges of every triangle -> (3*nf, 2), each row sorted low-high."""
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], axis=0)
    return np.sort(E, axis=1)


def _edge_counts(F: np.ndarray):
    """Unique undirected edges and how many faces each is shared by."""
    E = _sorted_edges(F)
    return np.unique(E, axis=0, return_counts=True)


def _unique_edges(F: np.ndarray) -> np.ndarray:
    if F.shape[0] == 0:
        return np.zeros((0, 2), np.int64)
    return np.unique(_sorted_edges(F), axis=0).astype(np.int64)


def boundary_edges(V, F) -> np.ndarray:
    """Open edges of the mesh -> ``(M, 2)`` int64, each row a sorted ``(lo, hi)``
    vertex pair.

    A boundary edge is an undirected edge shared by **exactly one** face — the rim
    of a hole. A closed mesh has none. Sorted rows so the result is a canonical
    set independent of face winding.
    """
    V, F = _validate(V, F)
    if F.shape[0] == 0:
        return np.zeros((0, 2), np.int64)
    uniq, counts = _edge_counts(F)
    return uniq[counts == 1].astype(np.int64)


def is_edge_manifold(V, F) -> bool:
    """True iff no undirected edge is shared by **more than two** faces.

    Edge-manifoldness is the precondition every other repair here relies on:
    :func:`orient_consistent` propagates winding across shared edges and
    :func:`inertia_tensor` integrates over a manifold surface. An empty edge set
    is vacuously manifold.
    """
    V, F = _validate(V, F)
    if F.shape[0] == 0:
        return True
    _, counts = _edge_counts(F)
    return bool(np.all(counts <= 2))


def is_watertight(V, F) -> bool:
    """True iff the mesh is edge-manifold **and closed** — every undirected edge
    is shared by **exactly two** faces.

    This is the gate for :func:`inertia_tensor`: only a watertight surface bounds
    a well-defined solid. (It does not, on its own, guarantee a *consistent*
    winding — a closed mesh can still have flipped faces; run
    :func:`orient_consistent` if the source is untrusted.)
    """
    V, F = _validate(V, F)
    if F.shape[0] == 0:
        return False
    _, counts = _edge_counts(F)
    return bool(np.all(counts == 2))


# --------------------------------------------------------------------------- #
# cleaning                                                                     #
# --------------------------------------------------------------------------- #
def remove_degenerate_faces(V, F):
    """Drop faces that carry no area -> ``(V, F)`` (vertices untouched).

    A face is degenerate if it repeats a vertex index or its three corners are
    collinear (area within a scale-relative epsilon of zero). Such faces break
    normals, quadrics and the inertia integral, so every operator that needs
    clean topology calls this.
    """
    V, F = _validate(V, F)
    if F.shape[0] == 0:
        return V, F
    i, j, k = F[:, 0], F[:, 1], F[:, 2]
    repeated = (i == j) | (j == k) | (i == k)
    A, B, C = V[i], V[j], V[k]
    two_area = np.linalg.norm(np.cross(B - A, C - A), axis=1)
    extent = float(np.max(V.max(axis=0) - V.min(axis=0))) if V.shape[0] else 1.0
    scale = extent if extent > 0.0 else 1.0
    tiny = two_area <= (1e-12 * scale * scale)
    keep = ~(repeated | tiny)
    return V, np.ascontiguousarray(F[keep], np.int64)


def weld_vertices(V, F, tol=1e-8):
    """Merge vertices that coincide within *tol* -> ``(V, F)``.

    Vertices are quantised to a grid of side *tol* (round-to-grid) and identical
    cells are unified; ``F`` is remapped and any face made degenerate by the merge
    is dropped. The representative kept for each merged group is the *first
    original* coordinate, so geometry never shifts by more than *tol*.

    This is the standard fix for the seams that per-triangle formats leave behind
    (an STL cube arrives as 36 unshared corners; welding restores the 8 shared
    vertices, which is what makes the mesh edge-manifold and closable).

    Limitation: grid quantisation is not a metric clustering — two points *tol*
    apart that straddle a cell boundary stay separate. For the exact-duplicate
    case (the common one) this is exact; ``tol=0`` welds only bit-identical
    coordinates.
    """
    V, F = _validate(V, F)
    tol = float(tol)
    if not np.isfinite(tol) or tol < 0.0:
        raise ValueError("tol must be >= 0, got %r" % (tol,))
    if V.shape[0] == 0:
        return V, F
    keys = V if tol == 0.0 else np.round(V / tol)
    uniq, idx_first, inv = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    inv = np.asarray(inv).reshape(-1)
    Vw = np.ascontiguousarray(V[idx_first], np.float64)
    if F.shape[0] == 0:
        return Vw, F
    Fw = np.ascontiguousarray(inv[F], np.int64)
    return remove_degenerate_faces(Vw, Fw)


# --------------------------------------------------------------------------- #
# orientation                                                                 #
# --------------------------------------------------------------------------- #
def _signed_volume(V: np.ndarray, F: np.ndarray) -> float:
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(np.einsum("ij,ij->i", A, np.cross(B, C)).sum() / 6.0)


def _traverses(face, u: int, v: int) -> bool:
    """True iff directed edge ``u -> v`` appears in triangle *face* = (a, b, c)."""
    a, b, c = face
    return (a == u and b == v) or (b == u and c == v) or (c == u and a == v)


def orient_consistent(V, F):
    """Make every face wind the same way -> ``(F, flipped_count)``.

    A breadth-first walk over the edge-manifold adjacency graph propagates one
    reference winding: two faces sharing an edge are consistent iff they traverse
    that shared edge in **opposite** directions, and the neighbour is flipped when
    they are not. For a **closed** mesh the whole surface is then flipped, if
    needed, so the outward normals give a positive signed volume (outward-facing).

    ``flipped_count`` is the number of faces whose winding differs from the input
    after this normalisation — so a single stray face in an otherwise-correct mesh
    reports ``1`` regardless of where the walk happened to start.

    Assumption: the mesh is **edge-manifold** (:func:`is_edge_manifold`). A
    non-manifold edge severs the adjacency graph and orientation cannot be carried
    across it; disconnected components are each oriented independently, and for a
    multi-component closed mesh the outward flip is decided on the *total* signed
    volume (per-component outward orientation is not guaranteed).
    """
    V, F = _validate(V, F, need_faces=True)
    F = F.copy()
    nf = F.shape[0]

    edge_faces = defaultdict(list)
    for fi in range(nf):
        a, b, c = int(F[fi, 0]), int(F[fi, 1]), int(F[fi, 2])
        for u, v in ((a, b), (b, c), (c, a)):
            edge_faces[(u, v) if u < v else (v, u)].append(fi)
    adj = defaultdict(list)
    for key, fs in edge_faces.items():
        if len(fs) == 2:                      # manifold interior edge -> a graph edge
            adj[fs[0]].append((fs[1], key))
            adj[fs[1]].append((fs[0], key))

    flipped = np.zeros(nf, bool)
    visited = np.zeros(nf, bool)
    for seed in range(nf):
        if visited[seed]:
            continue
        visited[seed] = True
        stack = [seed]
        while stack:
            f = stack.pop()
            ftuple = (int(F[f, 0]), int(F[f, 1]), int(F[f, 2]))
            for g, (u, v) in adj[f]:
                if visited[g]:
                    continue
                visited[g] = True
                gtuple = (int(F[g, 0]), int(F[g, 1]), int(F[g, 2]))
                # consistent iff the shared edge runs opposite ways in f and g
                if _traverses(ftuple, u, v) == _traverses(gtuple, u, v):
                    F[g] = F[g][[0, 2, 1]]
                    flipped[g] = ~flipped[g]
                stack.append(g)

    if is_watertight(V, F) and _signed_volume(V, F) < 0.0:
        F = F[:, [0, 2, 1]]
        flipped = ~flipped
    return np.ascontiguousarray(F, np.int64), int(flipped.sum())


# --------------------------------------------------------------------------- #
# hole filling                                                                #
# --------------------------------------------------------------------------- #
def _boundary_loops(F: np.ndarray):
    """Chain the directed boundary half-edges into ordered vertex loops."""
    uniq, counts = _edge_counts(F)
    boundary = set(map(tuple, uniq[counts == 1].tolist()))
    nxt = {}
    for fi in range(F.shape[0]):
        a, b, c = int(F[fi, 0]), int(F[fi, 1]), int(F[fi, 2])
        for u, v in ((a, b), (b, c), (c, a)):
            if ((u, v) if u < v else (v, u)) in boundary:
                nxt[u] = v                    # the one face owning this edge sets direction
    loops, seen = [], set()
    for start in list(nxt.keys()):
        if start in seen:
            continue
        loop, cur = [start], start
        seen.add(start)
        while True:
            cur = nxt.get(cur)
            if cur is None or cur == start:
                break
            if cur in seen:                   # defensive: a pinched, non-simple boundary
                break
            loop.append(cur)
            seen.add(cur)
        loops.append(loop)
    return loops


def fill_holes(V, F, max_boundary_len=None):
    """Close boundary loops with a centroid triangle fan -> ``(V, F)``.

    Each boundary loop gets one new vertex at its centroid and a fan of triangles
    back to the loop, wound to agree with the surrounding faces. That is enough to
    make a scan with missing patches watertight (each former boundary edge is now
    shared by its original face plus one fan triangle). Loops with more than
    *max_boundary_len* edges are left open.

    Honest limitation: the fan is **not** the minimal-area / smoothest fill.
    For a concave or strongly non-planar rim the fan triangles can self-intersect
    or bulge — the principled fix is Liepa 2003 (advancing-front minimal-area
    triangulation followed by refinement/fairing), which this module does not
    implement. Run :func:`orient_consistent` afterwards if you need a guaranteed
    outward winding on the patched surface.
    """
    V, F = _validate(V, F)
    if F.shape[0] == 0:
        return V, F
    loops = _boundary_loops(F)
    new_V, new_F = [V], [F]
    nv = V.shape[0]
    for loop in loops:
        if len(loop) < 3:
            continue
        if max_boundary_len is not None and len(loop) > int(max_boundary_len):
            continue
        centroid = V[loop].mean(axis=0)
        ci = nv
        new_V.append(centroid[None, :])
        nv += 1
        k = len(loop)
        # boundary is traversed loop[i] -> loop[i+1] by the mesh; the fan triangle
        # takes the opposite direction on that shared edge -> (centroid, b, a).
        tris = [(ci, loop[(i + 1) % k], loop[i]) for i in range(k)]
        new_F.append(np.asarray(tris, np.int64))
    Vout = np.ascontiguousarray(np.concatenate(new_V, axis=0), np.float64)
    Fout = np.ascontiguousarray(np.concatenate(new_F, axis=0), np.int64)
    return Vout, Fout


# --------------------------------------------------------------------------- #
# smoothing                                                                   #
# --------------------------------------------------------------------------- #
def _laplacian_step(P: np.ndarray, edges: np.ndarray, factor: float) -> np.ndarray:
    nv = P.shape[0]
    nsum = np.zeros_like(P)
    deg = np.zeros(nv)
    i, j = edges[:, 0], edges[:, 1]
    np.add.at(nsum, i, P[j])
    np.add.at(nsum, j, P[i])
    np.add.at(deg, i, 1.0)
    np.add.at(deg, j, 1.0)
    mask = deg > 0
    out = P.copy()
    delta = nsum[mask] / deg[mask][:, None] - P[mask]      # uniform-weight Laplacian
    out[mask] = P[mask] + factor * delta
    return out


def smooth_taubin(V, F, iterations=10, lamb=0.5, mu=-0.53) -> np.ndarray:
    """Taubin lambda|mu smoothing -> new ``V`` (topology ``F`` unchanged).

    Each iteration is a positive Laplacian pass (weight *lamb*, a shrinking blur)
    followed by a negative pass (weight *mu*, ``mu < -lamb`` so it inflates). The
    two together form the shrink-free low-pass filter of Taubin 1995: high-
    frequency scan noise is attenuated while the overall volume is preserved, so
    the mesh does not collapse toward its centroid the way plain Laplacian
    smoothing does. Uniform (combinatorial) edge weights; vertices only.
    """
    V, F = _validate(V, F, need_faces=True)
    iterations = int(iterations)
    if iterations < 0:
        raise ValueError("iterations must be >= 0, got %r" % (iterations,))
    lamb, mu = float(lamb), float(mu)
    edges = _unique_edges(F)
    P = V.copy()
    if edges.shape[0] == 0:
        return P
    for _ in range(iterations):
        P = _laplacian_step(P, edges, lamb)
        P = _laplacian_step(P, edges, mu)
    return np.ascontiguousarray(P, np.float64)


# --------------------------------------------------------------------------- #
# decimation (quadric error metric)                                           #
# --------------------------------------------------------------------------- #
def _vertex_quadrics(V: np.ndarray, F: np.ndarray) -> np.ndarray:
    """Per-vertex 4x4 error quadric Q = sum over incident faces of p p^T."""
    nv = V.shape[0]
    Q = np.zeros((nv, 4, 4))
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(B - A, C - A)
    ln = np.linalg.norm(n, axis=1)
    good = ln > 0.0
    if not good.any():
        return Q
    ng = n[good] / ln[good][:, None]
    d = -np.einsum("ij,ij->i", ng, A[good])
    p = np.concatenate([ng, d[:, None]], axis=1)           # plane (a, b, c, d)
    K = np.einsum("mi,mj->mij", p, p)                       # fundamental quadric
    Fg = F[good]
    for col in range(3):
        np.add.at(Q, Fg[:, col], K)
    return Q


def decimate_qem(V, F, target_faces):
    """Quadric-error-metric edge-collapse decimation toward *target_faces*.

    Garland & Heckbert 1997: each vertex carries the sum of the squared-distance
    quadrics of its incident face planes; the cheapest edge is collapsed to the
    position minimising that quadric (a midpoint/endpoint fallback when the 3x3
    system is singular, e.g. on a flat face), quadrics are accumulated onto the
    surviving vertex, and incident edge costs are re-queued. Collapses that would
    flip a face normal or land on a non-manifold edge are skipped, so the result
    stays a sane surface.

    Honest scope: this is a **practical** QEM, not production-grade. It has no
    boundary-preservation term, no attribute (colour/UV) quadrics and no
    aggressive validity recovery, so on awkward meshes a few non-ideal collapses
    can survive and the collapse may stop a little short of *target_faces* when
    every remaining candidate is blocked by the flip/manifold guard. Good enough
    for a cheap collision proxy; not a replacement for a dedicated remesher.
    """
    V, F = _validate(V, F, need_faces=True)
    target_faces = int(target_faces)
    if target_faces <= 0:
        raise ValueError("target_faces must be > 0, got %r" % (target_faces,))
    nv = V.shape[0]
    pos = V.copy()
    Q = _vertex_quadrics(pos, F)
    alive = np.ones(nv, bool)
    version = np.zeros(nv, np.int64)
    faces = [(int(a), int(b), int(c)) for a, b, c in F]
    face_alive = [True] * len(faces)
    vfaces = [set() for _ in range(nv)]
    neighbors = [set() for _ in range(nv)]
    for fi, (a, b, c) in enumerate(faces):
        vfaces[a].add(fi); vfaces[b].add(fi); vfaces[c].add(fi)
        neighbors[a].update((b, c)); neighbors[b].update((a, c)); neighbors[c].update((a, b))
    live_faces = len(faces)
    heap: list = []

    def _opt(vi, vj):
        Qc = Q[vi] + Q[vj]
        try:
            x = np.linalg.solve(Qc[:3, :3], -Qc[:3, 3])
            if np.all(np.isfinite(x)):
                v4 = np.array([x[0], x[1], x[2], 1.0])
                return x.astype(np.float64), max(float(v4 @ Qc @ v4), 0.0)
        except np.linalg.LinAlgError:
            pass
        best, best_c = None, None
        for cand in (pos[vi], pos[vj], 0.5 * (pos[vi] + pos[vj])):
            v4 = np.array([cand[0], cand[1], cand[2], 1.0])
            cc = float(v4 @ Qc @ v4)
            if best_c is None or cc < best_c:
                best, best_c = cand, cc
        return np.asarray(best, np.float64), max(best_c, 0.0)

    def _push(vi, vj):
        if vi == vj:
            return
        vbar, cost = _opt(vi, vj)
        heapq.heappush(heap, (cost, vi, vj, int(version[vi]), int(version[vj]), vbar))

    for e in _unique_edges(F):
        _push(int(e[0]), int(e[1]))

    def _normal(f):
        a, b, c = f
        return np.cross(pos[b] - pos[a], pos[c] - pos[a])

    while live_faces > target_faces and heap:
        cost, vi, vj, ver_i, ver_j, vbar = heapq.heappop(heap)
        if not alive[vi] or not alive[vj]:
            continue
        if version[vi] != ver_i or version[vj] != ver_j:
            continue
        if vj not in neighbors[vi]:
            continue
        shared = [f for f in (vfaces[vi] & vfaces[vj]) if face_alive[f]]
        if len(shared) > 2:                    # non-manifold edge: refuse
            continue
        # inversion guard: reject a collapse that folds any surviving face over
        flips = False
        for f in (vfaces[vi] | vfaces[vj]):
            if not face_alive[f] or f in shared:
                continue
            tri = tuple(vi if x == vj else x for x in faces[f])
            P = [vbar if x == vi else pos[x] for x in tri]
            new_n = np.cross(P[1] - P[0], P[2] - P[0])
            if np.dot(_normal(faces[f]), new_n) <= 0.0 or np.linalg.norm(new_n) == 0.0:
                flips = True
                break
        if flips:
            continue
        # commit: retire the shared faces, move vi to vbar, fold vj into vi
        for f in shared:
            face_alive[f] = False
            for x in faces[f]:
                vfaces[x].discard(f)
        live_faces -= len(shared)
        pos[vi] = vbar
        Q[vi] = Q[vi] + Q[vj]
        alive[vj] = False
        version[vi] += 1
        for f in list(vfaces[vj]):
            faces[f] = tuple(vi if x == vj else x for x in faces[f])
            vfaces[vi].add(f)
        vfaces[vj] = set()
        ni = set()
        for f in vfaces[vi]:
            ni.update(x for x in faces[f] if x != vi)
        neighbors[vi] = ni
        for nb in ni:
            neighbors[nb].discard(vj)
            neighbors[nb].add(vi)
        neighbors[vj] = set()
        for nb in ni:
            _push(vi, nb)

    out = [f for f, a in zip(faces, face_alive) if a and len(set(f)) == 3]
    if not out:
        raise ValueError("decimation collapsed the mesh to no faces")
    Fout = np.asarray(out, np.int64)
    used = np.unique(Fout)
    remap = -np.ones(nv, np.int64)
    remap[used] = np.arange(used.size)
    Vout = np.ascontiguousarray(pos[used], np.float64)
    Fout = np.ascontiguousarray(remap[Fout], np.int64)
    return Vout, Fout


# --------------------------------------------------------------------------- #
# convex hull                                                                 #
# --------------------------------------------------------------------------- #
def convex_hull(V):
    """Convex hull of a point set -> ``(V, F)`` with outward-oriented triangles.

    Thin wrapper over :class:`scipy.spatial.ConvexHull` (Qhull): interior points
    are dropped, faces are triangulated, and each triangle is wound so its normal
    points away from the hull centroid (outward, positive signed volume) — so the
    result feeds straight into :func:`inertia_tensor` or a MuJoCo convex collider.
    Needs at least 4 non-coplanar points.
    """
    V = _finite_vertices(V, "convex_hull")
    if V.shape[0] < 4:
        raise ValueError("convex_hull needs at least 4 points, got %d" % V.shape[0])
    try:
        hull = ConvexHull(V)
    except Exception as exc:                   # Qhull raises on degenerate/coplanar input
        raise ValueError("convex_hull failed (points may be coplanar/degenerate): %s"
                         % exc) from None
    simp = np.asarray(hull.simplices, np.int64)
    pts = np.asarray(hull.points, np.float64)
    used = np.unique(simp)
    remap = -np.ones(pts.shape[0], np.int64)
    remap[used] = np.arange(used.size)
    Vh = np.ascontiguousarray(pts[used], np.float64)
    Fh = np.ascontiguousarray(remap[simp], np.int64)
    center = Vh.mean(axis=0)
    A, B, C = Vh[Fh[:, 0]], Vh[Fh[:, 1]], Vh[Fh[:, 2]]
    n = np.cross(B - A, C - A)
    facing = np.einsum("ij,ij->i", n, (A + B + C) / 3.0 - center)
    flip = facing < 0.0
    Fh[flip] = Fh[flip][:, [0, 2, 1]]
    return Vh, Fh


# --------------------------------------------------------------------------- #
# mass properties                                                             #
# --------------------------------------------------------------------------- #
def inertia_tensor(V, F, density=1.0) -> dict:
    """Exact mass properties of the solid a watertight mesh bounds.

    Returns ``{"mass", "volume", "com" (3,), "inertia" (3x3, about the COM)}``.
    The solid is assumed uniform-density; ``mass = density * volume``.

    Method (Mirtich 1996 / divergence theorem): the solid is decomposed into
    signed tetrahedra from the origin to each face triangle, and the volume, the
    first moment and the full second-moment (covariance) integral are summed in
    closed form over the triangles — the covariance of a tetrahedron ``(0,a,b,c)``
    is ``(V_t/20)(aa^T + bb^T + cc^T + s s^T)`` with ``s = a+b+c``. The inertia
    about the origin is ``tr(C) I - C``; the parallel-axis theorem then shifts it
    to the centre of mass. This is exact for any triangulation (independent of how
    a planar face is split), which is why a convex-hull re-triangulation gives the
    same tensor.

    **Preconditions (raises ``ValueError`` otherwise):** the mesh must be
    watertight — :func:`is_watertight` — because only a closed surface bounds a
    solid; a non-watertight mesh has no defined volume. The winding must be
    consistent; the sign of the total volume is normalised here (an all-inward
    mesh is handled), but a *mixed* winding is not detectable and gives a wrong
    result, so run :func:`orient_consistent` on untrusted input first. ``density``
    must be finite and positive.
    """
    V, F = _validate(V, F, need_faces=True)
    density = float(density)
    if not np.isfinite(density) or density <= 0.0:
        raise ValueError("density must be finite and > 0, got %r" % (density,))
    if not is_watertight(V, F):
        raise ValueError(
            "inertia_tensor requires a watertight (closed, edge-manifold) mesh — the "
            "bounded solid is undefined otherwise; run is_watertight / fill_holes / "
            "orient_consistent first")

    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    vt = np.einsum("ij,ij->i", A, np.cross(B, C)) / 6.0    # signed tetra volumes
    vol = float(vt.sum())
    sign = 1.0 if vol >= 0.0 else -1.0                     # normalise inward winding
    m1 = (vt[:, None] * (A + B + C) / 4.0).sum(axis=0)
    S = A + B + C

    def _outers(P):
        return np.einsum("ni,nj->nij", P, P)

    Mten = _outers(A) + _outers(B) + _outers(C) + _outers(S)
    Cov = np.einsum("n,nij->ij", vt / 20.0, Mten)
    vol, m1, Cov = sign * vol, sign * m1, sign * Cov

    if not np.isfinite(vol) or vol <= 0.0:
        raise ValueError("degenerate mesh: non-positive enclosed volume (%r)" % (vol,))

    mass = density * vol
    com = m1 / vol
    I_origin = (np.trace(Cov) * np.eye(3) - Cov) * density
    I_com = I_origin - mass * ((com @ com) * np.eye(3) - np.outer(com, com))
    return {
        "mass": float(mass),
        "volume": float(vol),
        "com": np.ascontiguousarray(com, np.float64),
        "inertia": np.ascontiguousarray(0.5 * (I_com + I_com.T), np.float64),
    }


# --------------------------------------------------------------------------- #
# connected components                                                        #
# --------------------------------------------------------------------------- #
def components(V, F) -> list:
    """Split a mesh into connected components -> ``[(V_i, F_i), ...]``.

    Faces are grouped by shared vertices (union-find over the face-vertex
    incidence); each component's vertices are compacted and its faces reindexed,
    so every returned ``(V_i, F_i)`` is a standalone mesh. Vertices referenced by
    no face are ignored. Components come out in ascending order of their smallest
    original vertex index (deterministic). An empty mesh yields ``[]``.
    """
    V, F = _validate(V, F)
    if F.shape[0] == 0:
        return []
    nv = V.shape[0]
    parent = np.arange(nv)

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:              # path compression
            parent[x], x = root, parent[x]
        return root

    for a, b, c in F:
        ra, rb, rc = find(int(a)), find(int(b)), find(int(c))
        parent[rb] = ra
        parent[rc] = ra

    groups = defaultdict(list)
    for fi in range(F.shape[0]):
        groups[find(int(F[fi, 0]))].append(fi)

    out = []
    for _, flist in groups.items():
        fsel = F[flist]
        used = np.unique(fsel)
        remap = -np.ones(nv, np.int64)
        remap[used] = np.arange(used.size)
        out.append((int(used.min()),
                    np.ascontiguousarray(V[used], np.float64),
                    np.ascontiguousarray(remap[fsel], np.int64)))
    out.sort(key=lambda t: t[0])
    return [(v, f) for _, v, f in out]

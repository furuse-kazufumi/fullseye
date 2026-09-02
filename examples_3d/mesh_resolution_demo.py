# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Resolution management: measure where a mesh / cloud is coarse or dense, then treat them differently.

    py -3.11 examples_3d/mesh_resolution_demo.py

The user's observation on the Itokawa render — 「点群の粗い部分と密な部分の使い分けが
出来ていない」 — is a measurable property, and every step here prints the number:

1. ``mesh_edge_stats`` on a pole-clustered UV sphere (edge p95/p5 = 5.4; the real
   Itokawa 49k model gives 2.8 with 2.6–14 m facets) and on the Itokawa STL when
   it is cached locally (no download).
2. ``mesh_detail_map``: coarseness / detail / relief weight per vertex — the cube's
   sharp edges get detail ≫ its flat faces, so synthetic relief would go to the
   flat coarse regions only.
3. ``mesh_split_long_edges`` (refine only where coarse, exact geometry) and
   ``mesh_isotropic_remesh`` (uniform target edge; area within 1 %, closed manifold).
4. Academic rule — never thin silently: ``mesh_lod_chain`` reports the geometric
   error of every level, ``mesh_select_lod`` applies the screen-space rule,
   ``mesh_decimate_preserving`` keeps the detailed vertices exactly and
   ``mesh_reduction_report`` says what a reduction lost (and refuses when a
   protected feature would move more than ``max_error``).
5. Point clouds: ``pc_density`` (non-uniformity), ``pc_poisson_disk`` (never removes
   an isolated point — ``pc_thinning_report`` proves it), ``pc_fill_sparse`` /
   ``pc_density_equalize`` (uniform spacing), ``pc_lod_chain``.

EXTEND: replace the synthetic shapes with your mesh (``V, F``) or cloud, choose the
target edge / spacing in your units, and read the reports before deciding whether
a reduction is acceptable for your analysis.
"""
import os
import re
import sys
import time

import numpy as np
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import meshres as M  # noqa: E402
import meshrepair  # noqa: E402


def uv_sphere(nu=24, nv=48, r=1.0):
    th = np.linspace(0, np.pi, nu + 1)
    ph = np.linspace(0, 2 * np.pi, nv, endpoint=False)
    V = [[0.0, 0.0, r]]
    for t in th[1:-1]:
        for p in ph:
            V.append([r * np.sin(t) * np.cos(p), r * np.sin(t) * np.sin(p), r * np.cos(t)])
    V.append([0.0, 0.0, -r])
    V = np.array(V)
    F = []

    def ring(i, j):
        return 1 + i * nv + (j % nv)

    for j in range(nv):
        F.append([0, ring(0, j), ring(0, j + 1)])
    for i in range(nu - 2):
        for j in range(nv):
            F += [[ring(i, j), ring(i + 1, j), ring(i + 1, j + 1)], [ring(i, j), ring(i + 1, j + 1), ring(i, j + 1)]]
    last = len(V) - 1
    for j in range(nv):
        F.append([last, ring(nu - 2, j + 1), ring(nu - 2, j)])
    return V, np.array(F)


def cube(n=10):
    V, F = [], []
    g = np.linspace(-0.5, 0.5, n + 1)
    for axis in range(3):
        for sgn in (-1.0, 1.0):
            base = len(V)
            for a in g:
                for b in g:
                    p = [0.0, 0.0, 0.0]
                    p[axis] = 0.5 * sgn
                    p[(axis + 1) % 3] = a
                    p[(axis + 2) % 3] = b
                    V.append(p)
            for i in range(n):
                for j in range(n):
                    q = base + i * (n + 1) + j
                    t1, t2 = [q, q + 1, q + n + 2], [q, q + n + 2, q + n + 1]
                    if sgn < 0:
                        t1, t2 = t1[::-1], t2[::-1]
                    F += [t1, t2]
    V = np.array(V)
    _, idx, inv = np.unique(np.round(V, 9), axis=0, return_index=True, return_inverse=True)
    return V[idx], inv.ravel()[np.array(F)]


def load_itokawa():
    p = os.path.join(ROOT, "data", "sample_3d_cache", "itokawa_f0049152.stl")
    if not os.path.exists(p):
        return None
    txt = open(p, encoding="ascii", errors="ignore").read()
    tri = np.array(re.findall(r"vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)", txt), float).reshape(-1, 3, 3)
    keys = np.round(tri.reshape(-1, 3), 9)
    V, inv = np.unique(keys, axis=0, return_inverse=True)
    return V * 1000.0, inv.reshape(-1, 3)                       # km -> m


def main():
    # 1. measure -------------------------------------------------------------------
    V, F = uv_sphere()
    s = M.mesh_edge_stats(V, F)
    print("[1] UV sphere: %d faces, edge p5/median/p95 = %.3f / %.3f / %.3f, non-uniformity %.2f, closed=%s"
          % (s["n_faces"], s["edge"]["p5"], s["edge"]["median"], s["edge"]["p95"], s["edge_nonuniformity"],
             s["boundary_edges"] == 0))
    assert s["edge_nonuniformity"] > 4.0
    ito = load_itokawa()
    if ito is not None:
        si = M.mesh_edge_stats(*ito)
        print("    Itokawa (cached STL): %d faces, edge p5/median/p95 = %.1f / %.1f / %.1f m, non-uniformity %.2f"
              % (si["n_faces"], si["edge"]["p5"], si["edge"]["median"], si["edge"]["p95"], si["edge_nonuniformity"]))

    # 2. detail map -------------------------------------------------------------------
    Vc, Fc = cube()
    d = M.mesh_detail_map(Vc, Fc)
    on_edge = np.sum(np.isclose(np.abs(Vc), 0.5), axis=1) >= 2
    print("[2] cube detail: edges %.2f vs faces %.4f (1/unit); relief weight on edges max %.2f (rough -> no synthetic relief)"
          % (d["detail"][on_edge].mean(), d["detail"][~on_edge].max(), d["relief_weight"][on_edge].max()))
    assert d["detail"][on_edge].min() > 10 * d["detail"][~on_edge].max()

    # 3. refine where coarse / remesh uniformly ----------------------------------------
    Vs, Fs = M.mesh_split_long_edges(V, F, 0.15)
    ss = M.mesh_edge_stats(Vs, Fs)
    t0 = time.time()
    Vr, Fr = M.mesh_isotropic_remesh(V, F, 0.12, iterations=10)
    sr = M.mesh_edge_stats(Vr, Fr)
    print("[3] split long edges: %d -> %d faces, max edge %.3f (vertices untouched, area change %.1e)"
          % (len(F), len(Fs), ss["edge"]["max"], ss["total_area"] - s["total_area"]))
    print("    isotropic remesh to L=0.12: %d faces, median edge %.3f, non-uniformity %.2f, area err %.2f %%, radius err %.4f, %.1fs"
          % (len(Fr), sr["edge"]["median"], sr["edge_nonuniformity"],
             100 * (sr["total_area"] - 4 * np.pi) / (4 * np.pi), np.abs(np.linalg.norm(Vr, axis=1) - 1).max(), time.time() - t0))
    assert sr["edge_nonuniformity"] < 1.8 and sr["boundary_edges"] == 0

    # 4. reductions with an audit trail ------------------------------------------------
    lod = M.mesh_lod_chain(V, F, fractions=(0.5, 0.25, 0.125))
    print("[4] LOD chain:", ", ".join("%d faces / max err %.4f" % (lv["n_faces"], lv["max_error"]) for lv in lod["levels"]))
    for dist in (2.0, 20.0, 200.0):
        sel = M.mesh_select_lod(lod, distance=dist, focal_px=800.0, pixel_tolerance=0.5)
        print("    camera at %5.0f: level %d (%d faces, %.3f px error)" % (dist, sel["level"], sel["n_faces"], sel["error_px"]))
    r = M.mesh_decimate_preserving(Vc, Fc, 300, protect_quantile=0.7)
    rep = r["report"]
    print("    protected decimation of the cube: %d -> %d faces, %d protected vertices, detail max error %.1e, overall max error %.3f"
          % (len(Fc), len(r["F"]), r["protected_vertices"], rep["detail_max_error"], rep["max_error"]))
    assert rep["detail_max_error"] < 1e-9
    try:
        M.mesh_decimate_preserving(V, F, 200, max_error=1e-9)
        raise AssertionError("expected a refusal")
    except ValueError as e:
        print("    refused as designed:", str(e)[:70], "...")
    plain = M.mesh_reduction_report(V, F, *meshrepair.decimate_qem(V, F, 60))
    print("    plain QEM to 60 faces: max error %.3f, detail max error %.3f, area change %.1f %% <- what a brutal reduction costs"
          % (plain["max_error"], plain["detail_max_error"], 100 * plain["area_change"]))

    # 5. point clouds -------------------------------------------------------------------
    rng = np.random.default_rng(0)
    A = rng.random((3000, 3)) * [1.0, 1.0, 0.0]
    B = rng.random((500, 3)) * [1.0, 1.0, 0.0] + [1.2, 0.0, 0.0]
    lone = np.array([[3.0, 3.0, 0.0]])
    P = np.concatenate([A, B, lone])
    dn = M.pc_density(P)
    Q = M.pc_poisson_disk(P, 0.06)
    tr = M.pc_thinning_report(P, Q, radius=0.06)
    Eq = M.pc_density_equalize(P, 0.06)
    print("[5] cloud: %d points, spacing non-uniformity %.2f -> poisson-disk %d points (isolated removed: %d, max gap %.3f)"
          % (len(P), dn["nonuniformity"], len(Q), tr["isolated_removed"], tr["max_gap"]))
    print("    equalised (fill sparse + thin dense): %d points, non-uniformity %.2f" % (len(Eq), M.pc_density(Eq)["nonuniformity"]))
    assert tr["isolated_removed"] == 0
    dmin, _ = cKDTree(Q).query(Q, k=2)
    assert dmin[:, 1].min() >= 0.06 - 1e-12
    print("ALL GT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())

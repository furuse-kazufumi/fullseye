# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Neuron trees from SWC — structure check, morphometry and Sholl analysis (numpy only).

A reconstructed neuron (NeuroMorpho.Org and every tracing tool) is a tree in the SWC
format: one line per node ``id type x y z radius parent``. The format carries promises —
one root, a parent id smaller than its child's, nodes = edges + 1 — and those promises are
the first gate: a file that breaks them is refused, not repaired.

Three operators (``text -> table`` and ``table -> table``; no new type vocabulary):

  * :func:`tree_from_swc` — parse and check an SWC text (or file path). Refuses duplicate
    ids, zero or several roots, a parent id not smaller than its child, a missing parent,
    non-finite coordinates and negative radii.
  * :func:`tree_morphometry` — nodes, edges, bifurcations (nodes with >= 2 children), tips,
    total cable length, maximum path length from the root, maximum radial extent.
    Identity: ``tips == 1 + sum(children - 1 over branching nodes)`` for any tree, and
    ``nodes == edges + 1``.
  * :func:`tree_sholl` — Sholl analysis: how many segments cross each sphere (``plane=None``)
    or circle (``plane="xy"`` etc., the view an image gives) around the root. A segment
    crosses radius ``r`` when its two end points lie on opposite sides of it (the endpoint
    rule of L-Measure and most tools). Identities: the 3-D counts do not move a single
    integer under any rotation about the centre; and the counts integrate exactly to
    ``sum |d_child - d_parent|`` (d = distance of an end point from the centre).

Measured (``examples/poc_swc_tree_truth.py``, three mouse neocortex neurons from
NeuroMorpho.Org): the projected Sholl moves by up to 9-16 crossings with the viewing
direction while the 3-D Sholl does not move at all.

Provenance: Sholl, *J. Anat.* 1953 (concentric-circle analysis); Cannon et al.,
*J. Neurosci. Methods* 1998 (the SWC format); Ascoli et al., *J. Neurosci.* 2007
(NeuroMorpho.Org); Scorcioni et al., *Nat. Protoc.* 2008 (L-Measure).
"""
from __future__ import annotations

import os

import numpy as np

MAX_TREE_NODES = 2_000_000
_PLANES = {"xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}


def tree_from_swc(swc):
    """Parse an SWC text (or a path to a ``.swc`` file) into a checked tree table.

    Returns a dict with ``id`` (n,), ``type`` (n,), ``xyz`` (n, 3), ``radius`` (n,),
    ``parent_index`` (n,; -1 for the root, otherwise the row of the parent) and ``root``
    (row of the root). Rows keep the file order. Comment lines (``#``) and blank lines
    are skipped.

    **Raises** ``ValueError``: not a string; a data line with fewer than 7 fields or
    unparsable numbers; no nodes; duplicate ids; zero or more than one root
    (parent == -1); a parent id that is not smaller than its child's; a parent id that
    does not exist; non-finite coordinates or radius; a negative radius; more than
    ``MAX_TREE_NODES`` nodes.
    """
    op = "tree_from_swc"
    if not isinstance(swc, str):
        raise ValueError("%s: expected SWC text or a path, got %s" % (op, type(swc).__name__))
    text = swc
    if "\n" not in swc and swc.strip().lower().endswith(".swc"):
        if not os.path.isfile(swc):
            raise ValueError("%s: no such file %r" % (op, swc))
        with open(swc, encoding="utf-8", errors="replace") as f:
            text = f.read()
    rows = []
    for k, ln in enumerate(text.splitlines(), 1):
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        f = s.split()
        if len(f) < 7:
            raise ValueError("%s: line %d has %d fields, SWC needs 7" % (op, k, len(f)))
        try:
            rows.append((int(f[0]), int(f[1]), float(f[2]), float(f[3]), float(f[4]),
                         float(f[5]), int(f[6])))
        except ValueError:
            raise ValueError("%s: line %d is not numeric: %r" % (op, k, s[:60])) from None
    if not rows:
        raise ValueError("%s: no nodes" % op)
    if len(rows) > MAX_TREE_NODES:
        raise ValueError("%s: %d nodes, over the %d cap" % (op, len(rows), MAX_TREE_NODES))
    ids = np.array([r[0] for r in rows], dtype=np.int64)
    par = np.array([r[6] for r in rows], dtype=np.int64)
    xyz = np.array([[r[2], r[3], r[4]] for r in rows], dtype=np.float64)
    rad = np.array([r[5] for r in rows], dtype=np.float64)
    if len(np.unique(ids)) != ids.size:
        raise ValueError("%s: duplicate node ids" % op)
    roots = np.flatnonzero(par == -1)
    if roots.size != 1:
        raise ValueError("%s: %d roots (parent == -1); a tree has exactly one" % (op, roots.size))
    if not (np.isfinite(xyz).all() and np.isfinite(rad).all()):
        raise ValueError("%s: non-finite coordinate or radius" % op)
    if (rad < 0).any():
        raise ValueError("%s: negative radius at id %d" % (op, int(ids[np.argmax(rad < 0)])))
    pos = {int(i): k for k, i in enumerate(ids)}
    pidx = np.full(ids.size, -1, dtype=np.int64)
    for k in range(ids.size):
        p = int(par[k])
        if p == -1:
            continue
        if not p < int(ids[k]):
            raise ValueError("%s: parent id %d is not smaller than child id %d" % (op, p, int(ids[k])))
        if p not in pos:
            raise ValueError("%s: parent id %d of node %d does not exist" % (op, p, int(ids[k])))
        pidx[k] = pos[p]
    return {"id": ids, "type": np.array([r[1] for r in rows], dtype=np.int64), "xyz": xyz,
            "radius": rad, "parent_index": pidx, "root": int(roots[0])}


def _check_tree(tree, op):
    if not isinstance(tree, dict) or not {"xyz", "parent_index", "root"} <= set(tree):
        raise ValueError("%s: expected a tree table from tree_from_swc (keys xyz, parent_index, root)" % op)
    xyz = np.asarray(tree["xyz"], dtype=np.float64)
    pidx = np.asarray(tree["parent_index"], dtype=np.int64)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or pidx.shape != (xyz.shape[0],):
        raise ValueError("%s: xyz must be (n, 3) and parent_index (n,)" % op)
    n = xyz.shape[0]
    if int((pidx == -1).sum()) != 1 or ((pidx < -1) | (pidx >= n)).any():
        raise ValueError("%s: parent_index must have exactly one -1 (the root) and valid rows" % op)
    if not np.isfinite(xyz).all():
        raise ValueError("%s: non-finite coordinates" % op)
    return xyz, pidx, int(np.flatnonzero(pidx == -1)[0])


def tree_morphometry(tree):
    """Counts and lengths of a tree table (from :func:`tree_from_swc`).

    Returns ``nodes``, ``edges``, ``bifurcations`` (nodes with two or more children),
    ``tips`` (nodes with no child), ``cable_length`` (sum of segment lengths),
    ``max_path_length`` (longest root-to-node path along the tree) and ``max_radial``
    (largest straight distance from the root).

    Identities (checked inside, fail-closed): ``nodes == edges + 1``, and
    ``tips == 1 + sum(children - 1)`` over the nodes that have children — tips are counted
    from the child counts directly, the right side from the branching nodes, so a bug in
    either count breaks the equality. A root with one child is not a tip.

    **Raises** ``ValueError``: not a tree table (see :func:`tree_from_swc`).
    """
    op = "tree_morphometry"
    xyz, pidx, root = _check_tree(tree, op)
    n = xyz.shape[0]
    child = np.flatnonzero(pidx >= 0)
    parent = pidx[child]
    seg = np.linalg.norm(xyz[child] - xyz[parent], axis=1)
    nchild = np.bincount(parent, minlength=n)
    tips = int((nchild == 0).sum())
    edges = int(child.size)
    if tips != 1 + int((nchild[nchild >= 1] - 1).sum()) or n != edges + 1:
        raise ValueError("%s: counting identity failed — the tree table is inconsistent" % op)
    # path length: parents come first when ids increase, but rows may be in any order —
    # walk in an order where every parent precedes its child
    order = _topological(pidx, root)
    path = np.zeros(n)
    for k in order[1:]:
        path[k] = path[pidx[k]] + np.linalg.norm(xyz[k] - xyz[pidx[k]])
    return {"nodes": int(n), "edges": edges, "bifurcations": int((nchild >= 2).sum()),
            "tips": tips, "cable_length": float(seg.sum()),
            "max_path_length": float(path.max()),
            "max_radial": float(np.linalg.norm(xyz - xyz[root], axis=1).max())}


def _topological(pidx, root):
    n = pidx.size
    kids = [[] for _ in range(n)]
    for k in range(n):
        if pidx[k] >= 0:
            kids[pidx[k]].append(k)
    order, stack = [], [root]
    while stack:
        k = stack.pop()
        order.append(k)
        stack.extend(kids[k])
    if len(order) != n:
        raise ValueError("tree: not every node is reachable from the root (a cycle or a second component)")
    return np.array(order)


def tree_sholl(tree, radii=None, n_radii=50, plane=None, center=None):
    """Sholl analysis: segments crossing spheres (3-D) or circles (a projection) around the root.

    ``radii`` are the shell radii (ascending, positive); if omitted, ``n_radii`` shells at
    the mid-points of equal steps up to the largest distance from the centre (never exactly
    on a node's distance). A shell passing exactly through a node is ambiguous under
    rounding — a rotation may move that node by one ulp to either side. ``plane=None`` measures in 3-D;
    ``plane="xy" | "xz" | "yz"`` drops the third axis first — what a single image sees.
    ``center`` defaults to the root position.

    A segment (parent-child) crosses radius ``r`` when its end points lie strictly on
    opposite sides of ``r`` (the endpoint rule). Returns ``radii``, ``crossings`` (int array),
    ``max_crossings``, ``radius_at_max`` and ``integral`` — the exact area under the whole
    continuous Sholl curve, computed from the segments' intervals (independent of where
    the shells are placed).

    Identities: in 3-D the crossings are invariant, integer for integer, under any rotation
    about the centre; and ``integral`` equals ``sum |d_child - d_parent|`` (the tests also
    check that the mid-point sum of the sampled crossings converges to it — a second
    implementation).

    **Raises** ``ValueError``: not a tree table; ``plane`` not one of None/xy/xz/yz;
    radii not 1-D, not finite, not positive or not strictly increasing; ``n_radii < 1``.
    """
    op = "tree_sholl"
    xyz, pidx, root = _check_tree(tree, op)
    if plane is not None and plane not in _PLANES:
        raise ValueError("%s: plane must be None, 'xy', 'xz' or 'yz', got %r" % (op, plane))
    c = xyz[root] if center is None else np.asarray(center, dtype=np.float64).reshape(3)
    p = xyz - c
    if plane is not None:
        p = p[:, list(_PLANES[plane])]
    d = np.linalg.norm(p, axis=1)
    if radii is None:
        if int(n_radii) < 1:
            raise ValueError("%s: n_radii must be >= 1" % op)
        top = float(d.max())
        # ★殻の中点に置く((k - 1/2) * top / n)。上端を top ちょうどにすると最も遠い節点が
        #   殻の上に乗り、回転で 1 ulp 動いただけで「内側/外側」が反転して交点が 1 -> 0 になった
        #   (回転不変の門が捕まえた)。
        nr = int(n_radii)
        radii = (np.arange(nr) + 0.5) * (top / nr) if top > 0 else np.array([1.0])
    r = np.asarray(radii, dtype=np.float64)
    if r.ndim != 1 or r.size == 0 or not np.isfinite(r).all() or (r <= 0).any() or (np.diff(r) <= 0).any():
        raise ValueError("%s: radii must be a non-empty, finite, positive, strictly increasing 1-D array" % op)
    child = np.flatnonzero(pidx >= 0)
    lo = np.minimum(d[child], d[pidx[child]])
    hi = np.maximum(d[child], d[pidx[child]])
    lo_s, hi_s = np.sort(lo), np.sort(hi)
    # crossings(r) = #{lo < r} - #{hi <= r}  (strictly between the two end distances)
    cross = (np.searchsorted(lo_s, r, side="left") - np.searchsorted(hi_s, r, side="right")).astype(np.int64)
    k = int(np.argmax(cross))
    area = float((hi - lo).sum())
    return {"radii": r, "crossings": cross, "max_crossings": int(cross[k]),
            "radius_at_max": float(r[k]), "integral": area}

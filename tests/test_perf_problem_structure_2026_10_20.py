"""Regression gates for optimisations that exploit existing problem structure."""
from __future__ import annotations

import math

import numpy as np
import pytest

import anomeval
import seggraph


def _old_operating_point(scores, labels, recall=0.95, confidence=0.95):
    """Reference kept from the pre-optimisation implementation."""
    s = np.asarray(scores, dtype=np.float64).ravel()
    y = np.asarray(labels, dtype=bool).ravel()
    rec, conf = float(recall), float(confidence)
    alpha = 1.0 - conf
    pos = int(y.sum())
    neg = int(y.size - pos)
    n_req = int(math.ceil(math.log(alpha) / math.log(rec) - 1e-12))
    if pos < n_req:
        raise ValueError
    ds = np.sort(s[y])[::-1]
    k = next(kk for kk in range(1, pos + 1)
             if anomeval._cp_lower(kk, pos, alpha) >= rec)
    thr = float(ds[k - 1])
    detected = int((ds >= thr).sum())
    fa = int((s[~y] >= thr).sum())
    return {"threshold": thr, "recall_observed": detected / pos,
            "recall_lower": anomeval._cp_lower(detected, pos, alpha),
            "detected": detected, "n_pos": pos, "n_neg": neg,
            "fpr": fa / neg, "fpr_upper": anomeval._cp_upper(fa, neg, alpha),
            "n_required": n_req, "recall": rec, "confidence": conf}, k


@pytest.mark.parametrize("n_pos", [10, 1_000, 100_000])
@pytest.mark.parametrize("recall,confidence", [(0.01, 0.01), (0.5, 0.9), (0.999, 0.01)])
def test_operating_point_bisection_matches_linear_with_ties(n_pos, recall, confidence):
    rng = np.random.default_rng(800 + n_pos)
    defect = rng.integers(0, 17, n_pos).astype(float)
    good = rng.integers(0, 17, max(7, n_pos // 5)).astype(float)
    scores = np.r_[defect, good]
    labels = np.r_[np.ones(n_pos, bool), np.zeros(good.size, bool)]
    try:
        expected, expected_k = _old_operating_point(scores, labels, recall, confidence)
    except ValueError:
        with pytest.raises(ValueError):
            anomeval.anomaly_operating_point(scores, labels, recall, confidence)
        return
    actual = anomeval.anomaly_operating_point(scores, labels, recall, confidence)
    assert actual == expected
    assert actual["detected"] >= expected_k  # ties at the selected score are recounted


def test_operating_point_bound_calls_are_logarithmic(monkeypatch):
    n = 100_000
    scores = np.r_[np.arange(n, dtype=float), -1.0]
    labels = np.r_[np.ones(n, bool), False]
    original = anomeval._cp_lower
    calls = 0

    def counted(k, total, alpha):
        nonlocal calls
        calls += 1
        return original(k, total, alpha)

    monkeypatch.setattr(anomeval, "_cp_lower", counted)
    anomeval.anomaly_operating_point(scores, labels, recall=0.95, confidence=0.95)
    assert calls <= math.ceil(math.log2(n)) + 2


def _old_anomaly_pro(scores, masks, fpr_max):
    """Full-sort reference kept from the pre-optimisation implementation."""
    s = np.asarray(scores, dtype=np.float64)
    if s.ndim == 2:
        s = s[None]
    mk = np.asarray(masks, dtype=bool)
    if mk.ndim == 2:
        mk = mk[None]
    labs, areas, nreg = anomeval._regions(mk)
    nneg = int((~mk).sum())
    w = np.zeros(nreg + 1)
    w[1:] = 1.0 / (areas * float(nreg))
    flat = s.ravel()
    order = np.argsort(-flat, kind="mergesort")
    sv = flat[order]
    cp = np.cumsum(w[labs.ravel()[order]])
    cn = np.cumsum((~mk.ravel()[order]).astype(np.float64)) / nneg
    last = np.r_[np.nonzero(np.diff(sv) != 0)[0], sv.size - 1]
    fpr = np.r_[0.0, cn[last]]
    pro = np.r_[0.0, cp[last]]
    cut = int(np.searchsorted(fpr, fpr_max, side="right"))
    fx, py = fpr[:cut], pro[:cut]
    if cut < fpr.size and fx[-1] < fpr_max:
        x0, x1, y0, y1 = fpr[cut - 1], fpr[cut], pro[cut - 1], pro[cut]
        yi = y0 + (y1 - y0) * (fpr_max - x0) / (x1 - x0) if x1 > x0 else y1
        fx, py = np.r_[fx, fpr_max], np.r_[py, yi]
    area = float(np.sum((fx[1:] - fx[:-1]) * (py[1:] + py[:-1]) * 0.5))
    return area / fpr_max, fx, py


@pytest.mark.parametrize("fpr_max", [0.05, 0.3, 1.0])
@pytest.mark.parametrize("quantised", [False, True])
def test_anomaly_pro_partial_sort_matches_full_sort(fpr_max, quantised):
    rng = np.random.default_rng(802)
    scores = rng.random((3, 37, 41))
    if quantised:
        scores = (scores * 8).astype(np.uint8)  # massive tied score groups
    masks = np.zeros(scores.shape, bool)
    masks[0, 2:12, 3:15] = True
    masks[1, 20:34, 10:35] = True
    masks[2, 5:30, 20:22] = True
    scores[masks] = np.min(scores)  # defects may all have the lowest score
    expected = _old_anomaly_pro(scores, masks, fpr_max)
    actual = anomeval.anomaly_pro(scores, masks, fpr_max)
    assert actual["aupro"] == pytest.approx(expected[0], abs=1e-12)
    np.testing.assert_allclose(actual["fpr"], expected[1], atol=1e-12, rtol=0)
    np.testing.assert_allclose(actual["pro"], expected[2], atol=1e-12, rtol=0)


def test_anomaly_pro_sorts_only_needed_range(monkeypatch):
    scores = np.arange(10_000, dtype=float).reshape(100, 100)
    masks = np.zeros_like(scores, bool)
    masks[:10, :10] = True
    sizes = []
    original = np.argsort

    def counted(a, *args, **kwargs):
        sizes.append(np.asarray(a).size)
        return original(a, *args, **kwargs)

    monkeypatch.setattr(np, "argsort", counted)
    anomeval.anomaly_pro(scores, masks, 0.05)
    assert sizes == [596]


def _old_max_tree(image, connectivity):
    """Per-pixel-neighbour-list reference from the old implementation."""
    img = np.asarray(image, dtype=float)
    h, w = img.shape
    f = img.ravel()
    n = f.size
    order = np.argsort(f, kind="stable")
    ei, ej, _ = seggraph._grid_edges(h, w, connectivity)
    nbr = [[] for _ in range(n)]
    for a, b in zip(ei.tolist(), ej.tolist()):
        nbr[a].append(b)
        nbr[b].append(a)
    parent = list(range(n))
    zpar = [-1] * n
    ordl = order.tolist()
    for p in reversed(ordl):
        parent[p] = zpar[p] = p
        for q in nbr[p]:
            if zpar[q] < 0:
                continue
            r = q
            while zpar[r] != r:
                r = zpar[r]
            x = q
            while zpar[x] != r:
                zpar[x], x = r, zpar[x]
            if r != p:
                parent[r] = zpar[r] = p
    fl = f.tolist()
    for p in ordl:
        q = parent[p]
        if fl[parent[q]] == fl[q]:
            parent[p] = parent[q]
    par = np.array(parent, dtype=np.int64)
    root = ordl[0]
    canon = (f[par] != f) | (np.arange(n) == root)
    area = np.ones(n, np.int64)
    hmax = f.copy()
    rr, cc = np.divmod(np.arange(n), w)
    r0, r1, c0, c1 = rr.copy(), rr.copy(), cc.copy(), cc.copy()
    for p in reversed(ordl):
        if p == root:
            continue
        q = parent[p]
        area[q] += area[p]
        hmax[q] = max(hmax[q], hmax[p])
        r0[q], r1[q] = min(r0[q], r0[p]), max(r1[q], r1[p])
        c0[q], c1[q] = min(c0[q], c0[p]), max(c1[q], c1[p])
    return {"parent": par.reshape(h, w), "order": order,
            "canonical": canon.reshape(h, w), "area": area.reshape(h, w),
            "height": (hmax - f).reshape(h, w),
            "diameter": np.maximum(r1-r0+1, c1-c0+1).reshape(h, w),
            "n_nodes": int(np.count_nonzero(canon)), "root": int(root),
            "connectivity": connectivity}


@pytest.mark.parametrize("connectivity", [4, 8])
@pytest.mark.parametrize("shape", [(33, 41), (1, 57), (57, 1)])
def test_max_tree_implicit_grid_matches_neighbour_lists(connectivity, shape):
    rng = np.random.default_rng(803)
    image = rng.integers(0, 4, shape)  # large plateaus
    expected = _old_max_tree(image, connectivity)
    actual = seggraph.max_tree(image, connectivity=connectivity)
    assert actual.keys() == expected.keys()
    for key in actual:
        if isinstance(actual[key], np.ndarray):
            np.testing.assert_array_equal(actual[key], expected[key])
        else:
            assert actual[key] == expected[key]

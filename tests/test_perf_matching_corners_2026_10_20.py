"""Performance slice 9: optimized kernels must preserve their former results."""
from __future__ import annotations

import numpy as np
import pytest

import contours_xld2 as C
import features as F
import fourierdesc as D
import matching as M


def _old_ncc_map(template, image):
    t = np.asarray(template, np.float64)
    img = np.asarray(image, np.float64)
    t0 = t - t.mean()
    tn = np.sqrt((t0 ** 2).sum()) + 1e-12
    h, w = t.shape
    out = np.full((max(img.shape[0] - h + 1, 0),
                   max(img.shape[1] - w + 1, 0)), -1.0)
    for i in range(out.shape[0]):
        for j in range(out.shape[1]):
            p = img[i:i + h, j:j + w]
            p0 = p - p.mean()
            out[i, j] = ((p0 * t0).sum()
                         / (np.sqrt((p0 ** 2).sum()) * tn + 1e-12))
    return out


def _old_best_match(template, image):
    t = np.asarray(template, np.float64)
    img = np.asarray(image, np.float64)
    best = None
    for i in range(img.shape[0] - t.shape[0] + 1):
        for j in range(img.shape[1] - t.shape[1] + 1):
            error = float(((img[i:i + t.shape[0], j:j + t.shape[1]] - t) ** 2).sum())
            if best is None or error < best[0]:
                best = error, i, j
    return best


def _old_fast_corners(img, thresh=.05, min_distance=5, max_n=500, n_contig=9):
    g = F._gray(img)
    ring = [(-3, 0), (-3, 1), (-2, 2), (-1, 3), (0, 3), (1, 3),
            (2, 2), (3, 1), (3, 0), (3, -1), (2, -2), (1, -3),
            (0, -3), (-1, -3), (-2, -2), (-3, -1)]
    vals = np.stack([np.roll(np.roll(g, -dy, 0), -dx, 1)
                     for dy, dx in ring])
    bright, dark = vals > g + thresh, vals < g - thresh

    def contig(mask):
        m2 = np.concatenate([mask, mask[:n_contig - 1]], 0)
        run = np.zeros_like(g)
        cur = np.zeros_like(g)
        for plane in m2:
            cur = np.where(plane, cur + 1, 0.0)
            run = np.maximum(run, cur)
        return run >= n_contig

    corner = contig(bright) | contig(dark)
    score = np.abs(vals - g).sum(0) * corner
    score[:3] = score[-3:] = 0
    score[:, :3] = score[:, -3:] = 0
    if score.max() <= 0:
        return np.empty((0, 2), int)
    return F._nms_peaks(score, min_distance, 1e-9, max_n)


@pytest.mark.parametrize("shape,side", [
    (shape, side) for shape in ((128, 128), (512, 512), (1024, 1024))
    for side in (5, 15, 31, 63)
])
def test_matching_maps_agree_with_loop(shape, side):
    rng = np.random.default_rng(side + shape[0])
    image = rng.random(shape)
    template = rng.random((side, side))
    expected = _old_ncc_map(template, image)
    actual = M._ncc_map(template, image)
    assert np.allclose(actual, expected, rtol=0, atol=1e-10)
    assert np.argmax(actual) == np.argmax(expected)


def test_matching_flat_ties_and_empty_search_range():
    flat = np.ones((24, 24))
    assert np.array_equal(M._ncc_map(flat[:5, :5], flat),
                          _old_ncc_map(flat[:5, :5], flat))
    repeated = np.zeros((30, 30)); repeated[2:7, 3:8] = 1; repeated[12:17, 13:18] = 1
    result = M.best_match(np.ones((5, 5)), repeated)
    assert (result["row_tl"], result["col_tl"]) == (2, 3)
    assert M._ncc_map(np.zeros((31, 31)), flat).shape == (0, 0)
    assert M.best_match(np.zeros((31, 31)), flat)["row"] == -1


def test_best_match_agrees_with_loop_on_random_image():
    rng = np.random.default_rng(91)
    image = rng.random((96, 103)); template = rng.random((15, 13))
    expected = _old_best_match(template, image)
    actual = M.best_match(template, image)
    assert (actual["error"], actual["row_tl"], actual["col_tl"]) == expected


@pytest.mark.parametrize("n_contig", [9, 12, 16])
def test_fast_matches_old_on_random_and_structured_images(n_contig):
    rng = np.random.default_rng(n_contig)
    random = rng.random((96, 111))
    structured = np.zeros((80, 90)); structured[20:60, 25:65] = 1
    for image in (random, structured):
        assert np.array_equal(F.fast_corners(image, n_contig=n_contig),
                              _old_fast_corners(image, n_contig=n_contig))


@pytest.mark.parametrize("n_contig", [8, 17])
def test_fast_rejects_run_lengths_outside_the_supported_ring(n_contig):
    with pytest.raises(ValueError, match="between 9 and 16"):
        F.fast_corners(np.zeros((16, 16)), n_contig=n_contig)


def test_cocircular_fits_each_input_once_plus_each_merge(monkeypatch):
    arcs = []
    for circle in range(10):
        for arc in range(20):
            angle = np.linspace(arc * .25, arc * .25 + .18, 6)
            radius = 10.0 + circle * 10
            arcs.append(np.column_stack([100 + radius * np.sin(angle),
                                         100 + radius * np.cos(angle)]))
    contour = {"shape": (256, 256), "cs": arcs}
    original = C._fit_circle
    calls = 0

    def counted(points):
        nonlocal calls
        calls += 1
        return original(points)

    def old_union(value, max_radius_diff=5.0):
        cs = [a.copy() for a in value["cs"]]
        merged = True
        while merged and len(cs) > 1:
            merged = False
            for i in range(len(cs)):
                for j in range(i + 1, len(cs)):
                    if len(cs[i]) < 3 or len(cs[j]) < 3:
                        continue
                    ci, ri = original(cs[i]); cj, rj = original(cs[j])
                    if (abs(ri - rj) < max_radius_diff
                            and np.linalg.norm(ci - cj) < max_radius_diff):
                        cs[i] = np.vstack([cs[i], cs[j]])
                        cs.pop(j); merged = True
                        break
                if merged:
                    break
        return cs

    expected = old_union(contour, max_radius_diff=1)
    monkeypatch.setattr(C, "_fit_circle", counted)
    result = C.union_cocircular_contours_xld(contour, max_radius_diff=1)
    merges = len(arcs) - len(result["cs"])
    assert calls == len(arcs) + merges
    assert len(result["cs"]) == len(expected)
    assert all(np.array_equal(a, b) for a, b in zip(result["cs"], expected))


def test_amplitudes_batch_svd_once_and_matches_loop(monkeypatch):
    rng = np.random.default_rng(42)
    coeffs = rng.normal(size=(1000, 4))
    expected = np.stack([np.linalg.svd(c.reshape(2, 2), compute_uv=False)
                         for c in coeffs])
    original = np.linalg.svd
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(np.linalg, "svd", counted)
    actual = D._amplitudes(coeffs)
    assert calls == 1
    assert np.allclose(actual, expected, rtol=0, atol=1e-12)
    assert D._amplitudes(np.empty((0, 4))).shape == (0, 2)

"""Result-different performance modes retained from review batches 20/22/26."""

import numpy as np

import curvature3d


def _original_curvatures(points, k, normals=None):
    """Reference copied from the pre-carry-over implementation."""
    p = np.asarray(points, float)
    n = len(p)
    if normals is not None:
        normals = curvature3d._validate_normals(normals, n)
    idx = curvature3d._knn_idx(p, k)
    k1, k2, nrm = np.zeros(n), np.zeros(n), np.zeros((n, 3))
    for i in range(n):
        local = p[idx[i]] - p[i]
        orient = None if normals is None else normals[i]
        k1[i], k2[i], nrm[i] = curvature3d._principal_at(local, orient)
    return k1, k2, nrm


def _clouds():
    rng = np.random.default_rng(20113)
    xy = rng.normal(size=(80, 2))
    plane = np.c_[xy, 0.02 * rng.normal(size=80)]
    uv = rng.uniform(-0.7, 0.7, (90, 2))
    saddle = np.c_[uv, uv[:, 0] ** 2 - 0.6 * uv[:, 1] ** 2]
    return plane, saddle


def test_batch20_113_114_exact_default_keeps_original_and_fast_is_bounded():
    worst = 0.0
    for points in _clouds():
        for k in (9, 17):
            ref = _original_curvatures(points, k)
            got = curvature3d._curvatures(points, k)
            for actual, expected in zip(got, ref):
                assert np.array_equal(actual, expected)
            fast = curvature3d._curvatures(points, k, method="fast")
            worst = max(worst, float(np.max(np.abs(fast[0] - ref[0]))),
                        float(np.max(np.abs(fast[1] - ref[1]))))
            assert np.array_equal(fast[2], ref[2])
            assert np.array_equal(curvature3d.estimate_normals(points, k), ref[2])
            np.testing.assert_allclose(
                curvature3d.estimate_normals(points, k, method="fast"), ref[2],
                atol=2e-12, rtol=0)
    assert worst <= 2e-12


def test_batch20_curvature_method_validation():
    with np.testing.assert_raises_regex(ValueError, "method"):
        curvature3d.estimate_normals(_clouds()[0], method="quick")

"""Result-different performance modes retained from review batches 20/22/26."""

import numpy as np

import curvature3d
import coherent
import lighttransport


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
            assert len(got) == len(ref) == 3
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


def _original_laser_line(**kwargs):
    """Reference entry point fixed to the pre-carry-over exact path."""
    return coherent.laser_line_coherent(**kwargs, method="exact")


def test_batch22_198_199_integrated_accumulation_tolerance_and_zero_roughness():
    worst = 0.0
    cases = [
        dict(shape=(16, 24), pixel_oversample=2, roughness_rad=None, seed=198),
        dict(shape=(18, 20), pixel_oversample=3, roughness_rad=0.7, seed=199),
    ]
    for case in cases:
        for patterns in (2, 5):
            ref = _original_laser_line(**case, n_patterns=patterns)
            assert np.array_equal(coherent.laser_line_coherent(
                **case, n_patterns=patterns), ref)
            fast = coherent.laser_line_coherent(
                **case, n_patterns=patterns, method="fast")
            worst = max(worst, float(np.max(np.abs(fast - ref))))
    assert worst <= 2e-15
    zero = dict(shape=(18, 22), pixel_oversample=2, roughness_rad=0.0, seed=200)
    np.testing.assert_allclose(
        coherent.laser_line_coherent(**zero, n_patterns=7, method="fast"),
        _original_laser_line(**zero, n_patterns=7), atol=2e-15, rtol=0)


def _original_radiosity_patterns(profile, irradiance, albedo):
    """Reference based on the original full-matrix public operation."""
    transport = lighttransport.transport_matrix_radiosity(profile, albedo)
    source = np.asarray(irradiance, float)
    return (transport["transport"] @ source.T).T


def test_batch26_302_dedicated_pattern_solve_matches_full_matrix():
    for count, angle in ((18, 61), (27, 76)):
        profile = lighttransport.groove_profile(n_patches=count, angle_deg=angle)
        x = np.linspace(0.0, 1.0, count)
        for sources in (x, np.stack([x, x[::-1], np.sin(np.pi * x) ** 2])):
            ref = _original_radiosity_patterns(profile, sources, 0.63)
            got = lighttransport.solve_radiosity_patterns(profile, sources, 0.63)
            np.testing.assert_allclose(got, ref, atol=2e-12, rtol=0)

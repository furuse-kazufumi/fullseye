"""Performance slice 11: optimized paths agree with the previous algorithms."""
from __future__ import annotations

import numpy as np
import pytest
from scipy.interpolate import griddata

import backends_texture as texture
import normals_orient
import render_ao
import scattered
import watershed3d


def _old_box_counts(mask):
    h, w = mask.shape
    out = []
    s = 1
    while s <= min(h, w) // 2:
        padded = np.pad(mask, ((0, (-h) % s), (0, (-w) % s)))
        boxes = padded.reshape(padded.shape[0] // s, s, padded.shape[1] // s, s)
        out.append((s, int(boxes.any(axis=(1, 3)).sum())))
        s *= 2
    return out


@pytest.mark.parametrize("shape,kind", [((9, 13), "random"), ((7, 5), "empty"),
                                          ((7, 5), "single"), ((7, 5), "full")])
def test_fractal_occupancy_pyramid_matches_old_counts(monkeypatch, shape, kind):
    rng = np.random.default_rng(11)
    mask = rng.random(shape) > 0.55
    if kind == "empty":
        mask[:] = False
    elif kind == "single":
        mask[:] = False
        mask[-1, -1] = True
    elif kind == "full":
        mask[:] = True
    seen = []
    real = np.polyfit

    def capture(x, y, degree):
        seen.append((x.copy(), y.copy()))
        return real(x, y, degree)

    monkeypatch.setattr(texture.np, "polyfit", capture)
    got = texture.fractal_dimension(mask, 0.5, 0.0)
    old = _old_box_counts(mask)
    valid = [(s, c) for s, c in old if c > 0]
    if len(valid) < 2:
        assert got == 0.0
    else:
        sizes, counts = map(np.asarray, zip(*valid))
        expected = max(0.0, real(np.log(1.0 / sizes), np.log(counts), 1)[0])
        assert abs(float(got) - expected) <= 1e-12
        assert np.array_equal(seen[0][0], np.log(1.0 / sizes))
        assert np.array_equal(seen[0][1], np.log(counts))


@pytest.mark.parametrize("method", ["linear", "cubic", "nearest"])
def test_materialized_scattered_interpolator_matches_griddata(method, monkeypatch):
    rng = np.random.default_rng(12)
    points = rng.random((80, 2))
    points = np.vstack((points, points[:3]))  # duplicate coordinates are supported
    values = np.sin(points[:, 0] * 3) + points[:, 1]
    query = np.vstack((rng.random((90, 2)), [[-2, -2], [3, 3]]))
    expected = griddata(points, values, query, method=method)
    if method != "nearest":
        near = griddata(points, values, query, method="nearest")
        expected = np.where(np.isnan(expected), near, expected)
    interp = scattered.create_scattered_data_interpolator(points, values, method)
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return griddata(*args, **kwargs)

    monkeypatch.setattr("scipy.interpolate.griddata", counted)
    got = scattered.interpolate_scattered_data(interp, query)
    assert calls == 0
    assert np.array_equal(np.isnan(got), np.isnan(expected))
    assert np.allclose(got, expected, rtol=0.0, atol=1e-12, equal_nan=True)
    old_format = {k: interp[k] for k in ("points", "values", "method")}
    assert np.allclose(scattered.interpolate_scattered_data(old_format, query), expected,
                       rtol=0.0, atol=1e-12, equal_nan=True)


def test_oriented_normals_build_one_tree_and_are_bit_identical(monkeypatch):
    rng = np.random.default_rng(13)
    points = rng.normal(size=(800, 3))
    expected = normals_orient.orient_normals(
        points, normals_orient.estimate_normals(points, k=16), k=16)
    real = normals_orient.cKDTree
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(normals_orient, "cKDTree", counted)
    got = normals_orient.estimate_oriented_normals(points, k=16)
    assert calls == 1
    assert np.array_equal(got, expected)


def _old_markers(dist, min_distance):
    markers = np.zeros(dist.shape, np.int32)
    coords = watershed3d._vol_local_maxima(dist, min_distance=max(1, int(round(min_distance))))
    vals = dist[tuple(coords.T)] if len(coords) else np.empty(0)
    coords, vals = coords[vals > 0], vals[vals > 0]
    accepted = []
    for i in np.argsort(vals)[::-1]:
        p = coords[i].astype(float)
        if all(np.linalg.norm(p - np.asarray(a, float)) >= min_distance for a in accepted):
            accepted.append(tuple(int(v) for v in coords[i]))
    for label, p in enumerate(accepted, 1):
        markers[p] = label
    return markers, accepted


@pytest.mark.parametrize("md", [0.0, 2.0, 3.0])
def test_spatial_hash_markers_match_old_nms(md):
    rng = np.random.default_rng(14)
    dist = rng.random((19, 21, 23))
    # Deliberate equal-distance candidates exercise the >= boundary.
    dist[:] *= 0.1
    dist[5, 5, 5] = 3.0
    dist[5, 5, 5 + int(md)] = 2.0
    expected = _old_markers(dist, md)
    got = watershed3d._markers_from_peaks(dist, md)
    assert np.array_equal(got[0], expected[0])
    assert got[1] == expected[1]


def _old_rays_hit_any(o, D, A, e1, e2, tmin, tmax):
    pvec = np.cross(D[:, None, :], e2[None, :, :])
    det = np.einsum("md,kmd->km", e1, pvec)
    nz = np.abs(det) > render_ao._DET_EPS
    inv = np.zeros_like(det)
    inv[nz] = 1.0 / det[nz]
    tvec = o[None, :] - A
    u = np.einsum("md,kmd->km", tvec, pvec) * inv
    qvec = np.cross(tvec, e1)
    v = np.einsum("kd,md->km", D, qvec) * inv
    t = np.einsum("md,md->m", e2, qvec)[None, :] * inv
    hit = (nz & (u >= -render_ao._BARY_EPS) & (u <= 1 + render_ao._BARY_EPS)
           & (v >= -render_ao._BARY_EPS) & (u + v <= 1 + render_ao._BARY_EPS)
           & (t > tmin) & (t < tmax))
    return hit.any(axis=1)


def test_blocked_ray_intersections_are_bit_identical():
    rng = np.random.default_rng(15)
    D = rng.normal(size=(513, 3))
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    A = rng.normal(size=(777, 3))
    e1 = rng.normal(size=(777, 3))
    e2 = rng.normal(size=(777, 3))
    args = (np.array([0.1, -0.2, 0.3]), D, A, e1, e2, 1e-5, 8.0)
    assert np.array_equal(render_ao._rays_hit_any(*args), _old_rays_hit_any(*args))

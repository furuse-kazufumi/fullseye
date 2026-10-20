"""Agreement gates for performance review batch 25.

Reference helpers intentionally preserve the pre-optimisation arithmetic.
"""

import numpy as np
from scipy import ndimage

import occupancy
import varmodel


def _inflate_reference(occ, radius, voxel_size=1.0):
    occ = np.asarray(occ, bool)
    if radius == 0.0 or not occ.any():
        return occ.copy()
    if occ.all():
        field = np.full(occ.shape, -np.inf, np.float64)
    else:
        field = (ndimage.distance_transform_edt(~occ, sampling=voxel_size)
                 - ndimage.distance_transform_edt(occ, sampling=voxel_size))
    return field <= radius


def _esdf_reference(occ, voxel_size=1.0):
    occ = np.asarray(occ, bool)
    if not occ.any():
        return np.full(occ.shape, np.inf)
    if occ.all():
        return np.full(occ.shape, -np.inf)
    return (ndimage.distance_transform_edt(~occ, sampling=voxel_size)
            - ndimage.distance_transform_edt(occ, sampling=voxel_size))


def _occupancy_grid_reference(points, bounds, res):
    points = np.asarray(points, np.float64)
    bounds = np.asarray(bounds, np.float64)
    res = np.broadcast_to(np.asarray(res, np.int64), (3,))
    frac = (points - bounds[:, 0]) / (bounds[:, 1] - bounds[:, 0])
    frac = frac[np.all((frac >= 0.0) & (frac <= 1.0), axis=1)]
    idx = np.minimum((frac * res).astype(np.int64), res - 1)
    grid = np.zeros(tuple(res), bool)
    grid[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    return grid


def _query_distance_reference(esdf_grid, bounds, res, query_points):
    bounds = np.asarray(bounds, np.float64)
    res = np.broadcast_to(np.asarray(res, np.int64), (3,))
    c = ((query_points - bounds[:, 0]) / (bounds[:, 1] - bounds[:, 0])
         * res - 0.5)
    c0 = np.floor(c).astype(np.int64)
    t = c - c0
    out = np.zeros(len(query_points), np.float64)
    for dx in (0, 1):
        wx = t[:, 0] if dx else 1.0 - t[:, 0]
        i = np.clip(c0[:, 0] + dx, 0, res[0] - 1)
        for dy in (0, 1):
            wy = t[:, 1] if dy else 1.0 - t[:, 1]
            j = np.clip(c0[:, 1] + dy, 0, res[1] - 1)
            for dz in (0, 1):
                wz = t[:, 2] if dz else 1.0 - t[:, 2]
                k = np.clip(c0[:, 2] + dz, 0, res[2] - 1)
                out += wx * wy * wz * esdf_grid[i, j, k]
    return out


def test_269_inflate_matches_two_edt_reference(monkeypatch):
    rng = np.random.default_rng(269)
    fixtures = [np.zeros((9, 8, 7), bool), np.ones((9, 8, 7), bool),
                rng.random((9, 8, 7)) < 0.2]
    for occ in fixtures:
        original = occ.copy()
        for radius in (0.0, 1.3, 20.0):
            for spacing in (1.0, (0.5, 1.5, 2.0)):
                assert np.array_equal(occupancy.inflate(occ, radius, spacing),
                                      _inflate_reference(occ, radius, spacing))
        assert np.array_equal(occ, original)

    calls = 0
    real = occupancy.ndimage.distance_transform_edt

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(occupancy.ndimage, "distance_transform_edt", counted)
    occupancy.inflate(fixtures[-1], 2.0)
    assert calls == 1


def test_270_esdf_matches_reference_and_preserves_input():
    rng = np.random.default_rng(270)
    occ = rng.random((17, 15, 13)) < 0.3
    before = occ.copy()
    got = occupancy.esdf(occ, (0.5, 1.0, 2.0))
    assert np.array_equal(got, _esdf_reference(occ, (0.5, 1.0, 2.0)))
    assert np.array_equal(occ, before)


def test_271_272_query_distance_chunked_matches_reference():
    rng = np.random.default_rng(271)
    grid = rng.normal(size=(19, 17, 13))
    points = rng.uniform(-2.0, 3.0, size=(10003, 3))
    bounds = ((-1.0, 2.0), (-0.5, 1.5), (0.0, 1.0))
    expected = _query_distance_reference(grid, bounds, grid.shape, points)
    got = occupancy.query_distance(grid, bounds, grid.shape, points, chunk=127)
    assert np.array_equal(got, expected)


def test_273_occupancy_grid_chunked_matches_reference():
    rng = np.random.default_rng(273)
    points = rng.uniform(-0.2, 1.2, size=(10003, 3))
    points[:2] = (0.0, 1.0, 0.5), (1.0, 0.0, 1.0)
    bounds = ((0.0, 1.0),) * 3
    expected = _occupancy_grid_reference(points, bounds, (23, 19, 17))
    got = occupancy.occupancy_grid(points, bounds, (23, 19, 17), chunk=127)
    assert np.array_equal(got, expected)


def test_256_calibration_map_matches_full_score_without_explanations(monkeypatch):
    rng = np.random.default_rng(256)
    center = rng.normal(size=(48, 52))
    model = {
        "center": center, "spread": np.full(center.shape, 0.7),
        "valid": np.ones(center.shape, bool), "k": 2.5, "far": 0.01,
        "spread_kind": "std", "n": 20,
        "alignment": {"observable": False, "max_misalign_px": 0.5},
    }
    image = center + rng.normal(scale=0.3, size=center.shape)
    full = varmodel.varmodel_score(image, model, align="translate")
    z, valid = varmodel._calibration_z_valid(image, model)
    assert np.array_equal(z, full["z"])
    assert np.array_equal(valid, full["valid"])

    def forbidden(*args, **kwargs):
        raise AssertionError("calibration executed explanation work")

    monkeypatch.setattr(varmodel._stats(), "binom", forbidden)
    monkeypatch.setattr(varmodel.ndimage if hasattr(varmodel, "ndimage") else ndimage,
                        "label", forbidden)
    # Enough pixels for the far-tail gate; a zero offset avoids unrelated FFT work.
    out = varmodel.varmodel_calibrate(model, np.stack([image] * 5), far=0.01)
    assert out["calibration_n_pixels"] == image.size * 5

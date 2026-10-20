"""Agreement gates for performance review batch 25.

Reference helpers intentionally preserve the pre-optimisation arithmetic.
"""

import numpy as np
from scipy import ndimage

import occupancy


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

"""Verification gates for performance batch 19 B (items 96--105)."""

import numpy as np

import regionprops3d
import backends_measure1d
import pcl_filter
from scipy.ndimage import map_coordinates


def _original_surface_area(mask):
    if not mask.any():
        return 0
    padded = np.pad(mask.astype(np.int8), 1)
    return sum(int(np.count_nonzero(np.diff(padded, axis=axis))) for axis in range(3))


def test_99_surface_area_is_exact_six_neighbour_count():
    probes = [
        np.array([[[1]]], dtype=bool),
        np.random.default_rng(99).random((7, 11, 5)) > 0.63,
        np.pad(np.ones((3, 4, 2), dtype=bool), ((0, 2), (1, 0), (0, 3))),
    ]
    for mask in probes:
        got = regionprops3d._surface_area(mask)
        assert got == _original_surface_area(mask)
        exposed = 0
        for index in np.argwhere(mask):
            for axis in range(3):
                for step in (-1, 1):
                    neighbour = index.copy()
                    neighbour[axis] += step
                    if (neighbour[axis] < 0 or neighbour[axis] >= mask.shape[axis]
                            or not mask[tuple(neighbour)]):
                        exposed += 1
        assert got == exposed


def _original_sample(img, a, offset01, band):
    height, width = img.shape
    theta = float(np.clip(a, 0.0, 1.0)) * np.pi
    direction = np.array([np.sin(theta), np.cos(theta)])
    normal = np.array([-np.cos(theta), np.sin(theta)])
    center = np.array([(height - 1) / 2, (width - 1) / 2])
    center += (float(np.clip(offset01, 0, 1)) - .5) * min(height - 1, width - 1) * normal
    clipped = backends_measure1d._clip_line(center, direction, height, width)
    tmin, tmax = clipped
    count = max(2, int(round(tmax - tmin)) + 1)
    ts = tmin + np.linspace(0.0, tmax - tmin, count)
    offsets = np.linspace(-band, band, 2 * max(1, int(round(band))) + 1)
    acc = np.zeros(count)
    for offset in offsets:
        shifted = center + offset * normal
        acc += map_coordinates(img, [shifted[0] + ts * direction[0],
                                     shifted[1] + ts * direction[1]], order=1, mode="nearest")
    return acc / len(offsets)


def test_100_banded_sample_batches_offsets_bit_identically():
    for shape, angle, offset, band in [((31, 47), .13, .5, 1.0),
                                        ((48, 29), .81, .17, 3.4),
                                        ((9, 7), .5, 1.0, 12.0)]:
        image = np.random.default_rng(sum(shape)).normal(size=shape)
        expected = _original_sample(image, angle, offset, band)
        got = backends_measure1d._sample(image, angle, offset, band)["prof"]
        assert np.array_equal(got, expected, equal_nan=True)


def test_101_order_zero_direct_mean_matches_exact_and_handles_degenerate_input():
    rng = np.random.default_rng(101)
    for points, radius, chunk in [
        (np.c_[rng.normal(size=(80, 2)), rng.normal(scale=.02, size=80)], .8, None),
        (rng.normal(size=(45, 3)), 1.5, 7),
    ]:
        expected = pcl_filter.mls_smooth(points, radius, order=0, chunk=chunk)
        got = pcl_filter.mls_smooth(points, radius, order=0, chunk=chunk, method="mean")
        np.testing.assert_allclose(got, expected, rtol=1e-12, atol=1e-14)
    repeated = np.ones((12, 3))
    got = pcl_filter.mls_smooth(repeated, 1.0, order=0, method="mean")
    assert np.array_equal(got, repeated, equal_nan=True)

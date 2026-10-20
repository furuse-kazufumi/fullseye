"""Verification gates for performance batch 19 B (items 96--105)."""

import numpy as np

import regionprops3d
import backends_measure1d
import backends_color
import pcl_filter
import fringe
import fit_primitives_ext
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


def _original_colour_pca(image):
    x = image.reshape(-1, 3)
    centered = x - x.mean(0)
    values, vectors = np.linalg.eigh(np.cov(centered.T))
    projected = centered @ vectors[:, np.argsort(values)[::-1]]
    return ((projected - projected.min(0)) /
            (np.ptp(projected, axis=0) + 1e-8)).reshape(image.shape)


def test_98_colour_pca_reference_and_offset_elision_probe():
    for shape, knob in [((7, 11, 3), 0.0), ((19, 5, 3), 1.0)]:
        image = np.random.default_rng(sum(shape)).random(shape)
        got = backends_color._principal_comp(image, knob, .3)
        expected = _original_colour_pca(image)
        assert np.array_equal(got, expected, equal_nan=True)
        x = image.reshape(-1, 3)
        centered = x - x.mean(0)
        _, vectors = np.linalg.eigh(np.cov(centered.T))
        direct = x @ vectors[:, ::-1]
        direct = ((direct - direct.min(0)) /
                  (np.ptp(direct, axis=0) + 1e-8)).reshape(shape)
        np.testing.assert_allclose(direct, expected, rtol=0, atol=4e-16)


def test_102_cropped_phase_unwrap_matches_full_canvas_and_island_offsets():
    yy, xx = np.mgrid[:90, :130]
    wrapped = np.angle(np.exp(1j * (.31 * xx + .17 * yy)))
    masks = []
    mask = np.zeros_like(wrapped, dtype=bool)
    mask[20:70, 30:100] = True
    masks.append(mask)
    islands = np.zeros_like(mask)
    islands[10:30, 10:35] = True
    islands[55:80, 85:120] = True
    masks.append(islands)
    for valid in masks:
        expected = fringe.unwrap_phase_2d(wrapped, mask=valid)
        got = fringe.unwrap_phase_2d(wrapped, mask=valid, crop_valid=True)
        assert np.array_equal(got, expected, equal_nan=True)


def _ellipsoid_points(n=300, radii=(2.0, 1.0, .7), seed=103):
    directions = np.random.default_rng(seed).normal(size=(n, 3))
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    return directions * np.asarray(radii)


def test_103_ellipsoid_candidate_reference_nan_inf_and_near_tie_probe():
    for points, chunk in [(_ellipsoid_points(), None),
                          (_ellipsoid_points(radii=(1, 1, .999999), seed=4), 37)]:
        result = fit_primitives_ext.fit_ellipsoid(points, chunk=chunk)
        assert np.isfinite(result["residual"])
    for bad in (np.nan, np.inf):
        points = _ellipsoid_points()
        points[0, 0] = bad
        with np.testing.assert_raises(ValueError):
            fit_primitives_ext.fit_ellipsoid(points)

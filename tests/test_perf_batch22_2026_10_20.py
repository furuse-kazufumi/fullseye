"""Performance batch 22 equivalence gates against the pre-change implementations."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_dilation

import regions_setops as rs
import reconstruction as reconstruction


def _old_bbox(region):
    r = np.asarray(region, dtype=bool)
    if not r.any():
        return None
    rows, cols = np.where(r)
    return rows.min(), cols.min(), rows.max(), cols.max()


def _old_neighbors(regions, max_distance=1):
    masks = [np.asarray(x, dtype=bool) for x in regions]
    dilated = [binary_dilation(m, iterations=int(max_distance)) for m in masks]
    return [
        (i, j)
        for i in range(len(masks))
        for j in range(i + 1, len(masks))
        if (dilated[i] & masks[j]).any()
    ]


def _old_select(regions, reference, relation="above"):
    out = []
    for region in regions:
        spatial = rs.spatial_relation(reference, region)
        if spatial and relation in spatial["relations"]:
            out.append(region)
    return out


def _old_subset(region1, region2):
    r1 = np.asarray(region1, dtype=bool)
    return bool((r1 & ~np.asarray(region2, dtype=bool)).sum() == 0)


def _old_runs(region):
    r = np.asarray(region, dtype=bool)
    runs = []
    for row in range(r.shape[0]):
        cols = np.where(r[row])[0]
        if cols.size == 0:
            continue
        breaks = np.where(np.diff(cols) > 1)[0]
        start = 0
        for end in list(breaks) + [len(cols) - 1]:
            runs.append((row, int(cols[start]), int(cols[end])))
            start = end + 1
    return runs


def _masks():
    rng = np.random.default_rng(221)
    masks = [
        np.zeros((31, 37), bool),
        np.ones((31, 37), bool),
        np.indices((31, 37)).sum(axis=0) % 2 == 0,
        rng.random((31, 37)) < 0.03,
        rng.random((31, 37)) < 0.83,
    ]
    border = np.zeros((31, 37), bool)
    border[[0, -1], :] = True
    border[:, [0, -1]] = True
    masks.append(border)
    return masks


def test_221_bbox_matches_old_on_random_structured_and_empty_masks():
    for mask in _masks():
        assert rs._bbox(mask) == _old_bbox(mask)


def test_222_spatial_selection_is_identity_and_order_identical():
    masks = _masks()
    for relation in ("above", "below", "left", "right"):
        expected = _old_select(masks, masks[2], relation)
        actual = rs.select_region_spatial(masks, masks[2], relation)
        assert len(actual) == len(expected)
        assert all(got is want for got, want in zip(actual, expected))


def test_223_neighbors_match_old_for_special_and_positive_iterations():
    masks = _masks()
    for distance in (-1, 0, 1, 2, 5):
        assert rs.find_neighbors(masks, distance) == _old_neighbors(masks, distance)


def test_224_subset_matches_old_on_random_structured_and_empty_masks():
    masks = _masks()
    for left in masks:
        for right in masks:
            assert rs.test_subset_region(left, right) is _old_subset(left, right)


def test_225_runs_match_old_including_many_transitions():
    for mask in _masks():
        assert rs.get_region_runs(mask) == _old_runs(mask)


def _old_depth_from_focus(images, focus_positions=None):
    from scipy.ndimage import laplace, uniform_filter

    stack = np.stack([np.asarray(image, float) for image in images], axis=0)
    measures = np.stack(
        [uniform_filter(np.abs(laplace(stack[k])), 5) for k in range(stack.shape[0])],
        axis=0,
    )
    best = np.argmax(measures, axis=0)
    depth = best.astype(float) if focus_positions is None else np.asarray(focus_positions, float)[best]
    return {"depth": depth, "index": best, "sharpness": measures.max(axis=0)}


def test_206_depth_from_focus_matches_old_including_ties_and_nan():
    rng = np.random.default_rng(206)
    images = rng.normal(size=(7, 33, 29))
    images[2, 4, 5] = np.nan
    images[3] = images[1]  # exact ties must keep the first index
    expected = _old_depth_from_focus(images, np.linspace(0.1, 0.7, len(images)))
    actual = reconstruction.depth_from_focus(images, np.linspace(0.1, 0.7, len(images)))
    assert np.array_equal(actual["index"], expected["index"])
    assert np.array_equal(actual["depth"], expected["depth"])
    assert np.array_equal(actual["sharpness"], expected["sharpness"], equal_nan=True)


def _old_select_grayvalues(image_stack, index_image):
    stack = np.stack([np.asarray(image, float) for image in image_stack], axis=0)
    idx = np.clip(np.asarray(index_image, int), 0, stack.shape[0] - 1)
    rows, cols = np.mgrid[0:idx.shape[0], 0:idx.shape[1]]
    return stack[idx, rows, cols]


def test_210_grayvalue_gather_matches_old_for_array_and_list(monkeypatch):
    rng = np.random.default_rng(210)
    stack = rng.normal(size=(9, 21, 17))
    index = rng.integers(-2, 12, size=stack.shape[1:])
    expected = _old_select_grayvalues(stack, index)
    calls = 0
    original_stack = np.stack

    def counted_stack(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_stack(*args, **kwargs)

    monkeypatch.setattr(np, "stack", counted_stack)
    assert np.array_equal(reconstruction.select_grayvalues_from_channels(stack, index), expected)
    assert calls == 0
    assert np.array_equal(reconstruction.select_grayvalues_from_channels(list(stack), index), expected)
    assert calls == 1

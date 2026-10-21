"""Performance slice 12 gates against the implementations replaced here."""
from __future__ import annotations

import numpy as np
import pytest

import blob2d as B
import region_morph as R
import volgray as V
from scipy import ndimage


def _old_blob_select(labels, feature, vmin=None, vmax=None, spacing=1.0):
    lab = B._as_labels(labels, "blob_select")
    features = B.blob_features(lab, spacing)
    if features["n"] == 0:
        return np.zeros_like(lab)
    values = np.asarray(features[feature], np.float64)
    keep = np.ones(values.shape, bool)
    if vmin is not None:
        keep &= values >= float(vmin)
    if vmax is not None:
        keep &= values <= float(vmax)
    return B._renumber(lab, features["label"][keep])


def _old_blob_select_largest(labels, count=1):
    lab = B._as_labels(labels, "blob_select_largest")
    features = B.blob_features(lab)
    if features["n"] == 0:
        return np.zeros_like(lab)
    order = np.argsort(-np.asarray(features["area"], np.float64), kind="stable")
    return B._renumber(lab, features["label"][order[:int(count)]])


def _many_blobs():
    mask = np.zeros((224, 224), bool)
    mask[1:201:2, 1:201:2] = True
    mask[205:210, 2:12] = True
    mask[205:210, 20:30] = True
    mask[205:215, 40:50] = True
    return B.blob_label(mask)


@pytest.mark.parametrize("feature", B.FEATURE_KEYS)
def test_blob_select_matches_full_feature_reference(feature):
    lab = _many_blobs()
    values = np.asarray(B.blob_features(lab, 0.25)[feature], np.float64)
    lo, hi = np.quantile(values, [0.25, 0.75])
    expected = _old_blob_select(lab, feature, float(lo), float(hi), 0.25)
    actual = B.blob_select(lab, feature, float(lo), float(hi), 0.25)
    assert np.array_equal(actual, expected)


def test_blob_selection_fast_paths_skip_blob_features(monkeypatch):
    lab = _many_blobs()
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("fast selection path called blob_features")

    monkeypatch.setattr(B, "blob_features", counted)
    B.blob_select(lab, "area", vmin=2)
    B.blob_select(lab, "touches_border", vmin=0)
    B.blob_select_largest(lab, 2)
    assert calls == 0


def test_blob_select_largest_matches_reference_with_ties_and_label_gaps():
    lab = _many_blobs()
    lab[lab == 7] = 0
    expected = _old_blob_select_largest(lab, 3)
    actual = B.blob_select_largest(lab, 3)
    assert np.array_equal(actual, expected)
    assert actual[206, 3] == 2
    assert actual[206, 21] == 3


def _old_reconstruct(seed, mask):
    previous = seed
    iterations = 0
    while True:
        current = np.minimum(
            ndimage.grey_dilation(previous, footprint=np.ones((3, 3), bool)), mask)
        iterations += 1
        if np.array_equal(current, previous):
            return current, iterations
        previous = current


def _winding_reconstruction(dtype):
    mask = np.zeros((129, 129), dtype=dtype)
    for row in range(1, 128, 2):
        index = (row - 1) // 2
        mask[row, 1:128] = 7
        mask[row + 1, 127 if index % 2 == 0 else 1] = 7
    seed = np.zeros_like(mask)
    seed[1, 1] = 5
    return seed, mask


@pytest.mark.parametrize("dtype", [np.uint16, np.float64])
def test_reconstruct_queue_matches_iterative_on_winding_path(dtype):
    seed, mask = _winding_reconstruction(dtype)
    expected, iterations = _old_reconstruct(seed, mask)
    actual = B._reconstruct_by_dilation(seed, mask)
    assert iterations > 4_000
    assert np.array_equal(actual, expected)


@pytest.mark.parametrize("case", ["equal", "zero", "random"])
@pytest.mark.parametrize("dtype", [np.int16, np.float32, np.float64])
def test_reconstruct_queue_edge_cases_match_iterative(case, dtype):
    rng = np.random.default_rng(1202)
    mask = rng.integers(0, 20, (17, 19)).astype(dtype)
    if case == "equal":
        seed = mask.copy()
    elif case == "zero":
        seed = np.zeros_like(mask)
    else:
        seed = np.minimum(mask, rng.integers(0, 20, mask.shape).astype(dtype))
    expected, _ = _old_reconstruct(seed, mask)
    assert np.array_equal(B._reconstruct_by_dilation(seed, mask), expected)


def _morph_masks():
    rng = np.random.default_rng(1203)
    random = rng.random((79, 83)) > 0.55
    structured = np.zeros((79, 83), bool)
    structured[:25, :31] = True
    structured[35:70, 20:72] = True
    structured[45:55, 35:45] = False
    return [random, structured, np.zeros_like(random), np.ones_like(random)]


@pytest.mark.parametrize("radius", range(1, 65))
def test_disc_edt_matches_structuring_element_for_all_radii(radius):
    footprint = R._disc(radius)
    for mask in _morph_masks():
        expected_eroded = ndimage.binary_erosion(mask, structure=footprint)
        expected_dilated = ndimage.binary_dilation(mask, structure=footprint)
        actual_eroded = R._disc_erosion(mask, radius)
        actual_dilated = R._disc_dilation(mask, radius)
        assert np.array_equal(actual_eroded, expected_eroded)
        assert np.array_equal(actual_dilated, expected_dilated)
        assert np.array_equal(
            R._disc_dilation(actual_eroded, radius),
            ndimage.binary_dilation(expected_eroded, structure=footprint))
        assert np.array_equal(
            R._disc_erosion(actual_dilated, radius),
            ndimage.binary_erosion(expected_dilated, structure=footprint))


@pytest.mark.parametrize("radius", range(1, 65))
def test_top_and_bottom_hat_match_structuring_element(radius):
    mask = _morph_masks()[1]
    footprint = R._disc(radius)
    expected_top = mask & ~ndimage.binary_opening(mask, structure=footprint)
    expected_bottom = ndimage.binary_closing(mask, structure=footprint) & ~mask
    assert np.array_equal(R.top_hat(mask, size=radius - 1), expected_top)
    assert np.array_equal(R.bottom_hat(mask, size=radius - 1), expected_bottom)


def _old_vol_equalize(volume, nbins=256, mask=None):
    value = V._require_volume(volume)
    selected = None
    if mask is not None:
        domain = V._require_volume(mask, "mask") > 0.5
        selected = value[domain]
    vmin, vmax = float(value.min()), float(value.max())
    if vmax <= vmin:
        return value.copy()
    if selected is None:
        selected = value.ravel()
    scale = nbins / (vmax - vmin)
    selected_index = ((selected - vmin) * scale).astype(np.int64)
    np.clip(selected_index, 0, nbins - 1, out=selected_index)
    histogram = np.bincount(selected_index, minlength=nbins)
    lut = np.cumsum(histogram, dtype=np.float64) / histogram.sum()
    index = ((value - vmin) * scale).astype(np.int64)
    np.clip(index, 0, nbins - 1, out=index)
    return lut[index]


@pytest.mark.parametrize("masked", [False, True])
def test_vol_equalize_shared_bins_matches_two_bin_array_reference(masked):
    rng = np.random.default_rng(1204)
    volume = rng.normal(1.0e6, 1.0e-6, (32, 35, 37))
    mask = rng.random(volume.shape) > 0.35 if masked else None
    expected = _old_vol_equalize(volume, 257, mask)
    actual = V.vol_equalize(volume, 257, mask)
    assert np.array_equal(actual, expected)


def test_vol_equalize_shared_bins_peak_is_at_most_seventy_percent():
    import gc
    import tracemalloc

    volume = np.linspace(-3.0, 7.0, 256 ** 3, dtype=np.float64).reshape((256,) * 3)

    def peak(function):
        gc.collect()
        tracemalloc.start()
        result = function(volume)
        _, measured = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert result.shape == volume.shape
        del result
        return measured

    old_peak = peak(_old_vol_equalize)
    new_peak = peak(V.vol_equalize)
    assert old_peak > 200_000_000
    assert new_peak <= 0.7 * old_peak, (old_peak, new_peak)

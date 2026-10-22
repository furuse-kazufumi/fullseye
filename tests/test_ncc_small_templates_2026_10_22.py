"""Accuracy and fallback gates for small NCC templates."""

import numpy as np
import pytest
from numpy.lib.stride_tricks import sliding_window_view

import matching


SIZES = (7, 8, 9, 15, 16, 17)


def _oracle(template, image):
    windows = sliding_window_view(image, template.shape)
    centered = windows - windows.mean(axis=(-2, -1), keepdims=True)
    norms = np.linalg.norm(centered, axis=(-2, -1))
    t0 = template - template.mean()
    t0 /= np.linalg.norm(t0)
    numerators = np.einsum("ijkl,kl->ij", centered, t0)
    return np.divide(numerators, norms, out=np.zeros_like(norms), where=norms > np.finfo(float).tiny)


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("case", ("random", "dc", "low_contrast", "constant_patch"))
def test_small_ncc_matches_direct_pearson_oracle(size, case):
    rng = np.random.default_rng(20261022 + size)
    image = rng.random((96, 96))
    if case == "dc":
        image += 1e6
    elif case == "low_contrast":
        y, x = np.mgrid[-1:1:96j, -1:1:96j]
        image = 0.4 + 0.2 * np.exp(-4 * (x * x + y * y))
    elif case == "constant_patch":
        image[20:60, 20:60] = 0.5
    template = rng.random((size, size))
    actual = matching._ncc_map(template, image)
    expected = _oracle(template, image)
    tolerance = 1e-6 if case == "dc" else 1e-9
    assert np.max(np.abs(actual - expected)) <= tolerance
    assert np.unravel_index(np.argmax(actual), actual.shape) == np.unravel_index(
        np.argmax(expected), expected.shape
    )
    if case == "constant_patch":
        # Undefined Pearson correlation retains the established score of zero.
        assert actual[20, 20] == 0.0


@pytest.mark.parametrize("size", SIZES)
def test_random_image_exact_fallback_fraction_below_five_percent(size):
    rng = np.random.default_rng(20261022 + size)
    image = rng.random((96, 96))
    template = rng.random((size, size))
    flagged, total = matching._ncc_unstable_count(template, image)
    assert flagged / total < 0.05

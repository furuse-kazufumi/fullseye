"""Constant-search-image and bounded NCC fallback regression gates."""
from __future__ import annotations

import os
import time

import numpy as np
import pytest

import matching


def _direct_pearson(template, image):
    t0 = template - template.mean()
    t0 /= np.linalg.norm(t0)
    shape = tuple(np.subtract(image.shape, template.shape) + 1)
    result = np.zeros(shape, dtype=np.float64)
    for row in range(shape[0]):
        for column in range(shape[1]):
            patch = image[row:row + template.shape[0],
                          column:column + template.shape[1]]
            centered = patch - patch.mean()
            norm = np.linalg.norm(centered)
            if norm > np.finfo(np.float64).tiny:
                result[row, column] = (centered * t0).sum() / norm
    return np.clip(result, -1.0, 1.0)


def test_constant_search_image_returns_documented_zero_map():
    template = np.arange(25, dtype=np.float64).reshape(5, 5)
    actual = matching._ncc_map(template, np.ones((160, 192)))
    assert actual.shape == (156, 188)
    assert actual.dtype == np.dtype(np.float64)
    assert np.array_equal(actual, np.zeros((156, 188), dtype=np.float64))


def test_constant_template_contract_is_unchanged():
    rng = np.random.default_rng(20261022)
    actual = matching._ncc_map(np.ones((5, 5)), rng.random((32, 35)))
    assert actual.shape == (28, 31)
    assert actual.dtype == np.dtype(np.float64)
    assert np.count_nonzero(actual) == 0


def test_partially_constant_image_matches_direct_pearson_oracle_bitwise():
    rng = np.random.default_rng(20261022)
    # This small, large-DC fixture deliberately takes the exact-window path
    # for every position, including the locally constant interior.
    image = 1e6 + rng.random((96, 101))
    image[24:72, 27:75] = 1e6 + 0.25
    template = rng.random((7, 7))
    actual = matching._ncc_map(template, image)
    expected = _direct_pearson(template, image)
    np.testing.assert_array_equal(actual, expected)
    assert actual[30, 30] == 0.0


@pytest.mark.skipif(bool(os.environ.get("PYTEST_XDIST_WORKER")),
                    reason="timing gate must not share an xdist worker")
def test_constant_search_is_at_most_quarter_of_random_search_time():
    rng = np.random.default_rng(20261022)
    template = rng.random((16, 16))
    constant = np.ones((512, 512))
    random = rng.random((512, 512))

    matching._ncc_map(template, constant)
    matching._ncc_map(template, random)

    def elapsed(image):
        start = time.perf_counter()
        matching._ncc_map(template, image)
        return time.perf_counter() - start

    constant_time = min(elapsed(constant) for _ in range(3))
    random_time = min(elapsed(random) for _ in range(3))
    assert constant_time <= random_time * 0.25

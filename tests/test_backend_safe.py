"""Contract tests for the shared backend safety net.

``backend_safe.sanitize`` is the single funnel every library-backed operator's
output passes through. Its docstring promises a *finite, sort-valid* result — the
tests below pin the SORT-VALID half (region range), which the 2026-08-16 audit
found was only guaranteed by convention, and re-pin the finiteness half so a
future edit cannot trade one for the other.
"""
from __future__ import annotations

import numpy as np

import backend_safe


# --------------------------------------------------------------------------- #
# M5 — the region {0,1} range contract                                        #
# --------------------------------------------------------------------------- #
def test_finite_out_of_range_float_region_is_coerced_to_01():
    """A finite float region outside {0,1} used to pass straight through.

    ``sanitize`` only checked ``np.all(np.isfinite(...))`` on the success path, so
    a soft mask / label map declared ``out_sort="region"`` was returned untouched
    and every downstream region consumer (blob_count, area_frac, region morphology)
    silently received a non-binary array.
    """
    soft = np.array([[0.3, 2.5], [-1.0, 0.9]])
    out = backend_safe.sanitize(soft, np.zeros((2, 2)), "region")
    assert out.dtype == np.float64
    assert set(np.unique(out).tolist()) <= {0.0, 1.0}
    # binarised at 0.5, the same rule api._coerce_input applies on the input side
    assert np.array_equal(out, np.array([[0.0, 1.0], [0.0, 1.0]]))


def test_integer_and_bool_regions_are_coerced_to_01_float():
    """int/bool region outputs skipped the float branch entirely and hit `return out`."""
    labels = np.array([[0, 2], [3, 0]], np.int32)
    out = backend_safe.sanitize(labels, np.zeros((2, 2)), "region")
    assert out.dtype == np.float64 and set(np.unique(out).tolist()) <= {0.0, 1.0}
    assert np.array_equal(out, np.array([[0.0, 1.0], [1.0, 0.0]]))

    mask = np.array([[True, False], [False, True]])
    out_b = backend_safe.sanitize(mask, np.zeros((2, 2)), "region")
    assert out_b.dtype == np.float64
    assert np.array_equal(out_b, np.array([[1.0, 0.0], [0.0, 1.0]]))


def test_valid_region_is_returned_untouched():
    """Every current region op astype()s from bool, so the guard must be an identity."""
    ok = np.array([[0.0, 1.0], [1.0, 0.0]])
    assert backend_safe.sanitize(ok, np.zeros((2, 2)), "region") is ok
    empty = np.zeros((0, 0))
    assert backend_safe.sanitize(empty, np.zeros((2, 2)), "region") is empty


def test_range_guard_does_not_touch_other_sorts():
    """Only `region` declares a {0,1} range — an image/feature must be left alone."""
    img = np.array([[0.3, 2.5], [-1.0, 0.9]])
    assert backend_safe.sanitize(img, np.zeros((2, 2)), "image") is img
    assert backend_safe.sanitize(img, np.zeros((2, 2)), None) is img
    assert backend_safe.sanitize(np.float64(7.5), np.zeros((2, 2)), "feature") == 7.5


def test_region01_leaves_non_array_output_alone():
    """A region op returning a dict/None is a SORT bug; the range guard must not mask it."""
    d = {"shape": (4, 4), "cs": []}
    assert backend_safe.region01(d) is d


def test_nonfinite_region_is_still_scrubbed_and_binary():
    """The finiteness half must keep working, and its result must also be in-contract."""
    out = backend_safe.sanitize(np.array([[np.nan, 2.5], [np.inf, 0.0]]),
                                np.zeros((2, 2)), "region")
    assert np.all(np.isfinite(out))
    assert set(np.unique(out).tolist()) <= {0.0, 1.0}


def test_failed_op_still_degrades_to_an_empty_region():
    """Backward compatibility with the documented fail-open registry contract."""
    empty = backend_safe.sanitize(None, np.zeros((16, 16)), "region")
    assert isinstance(empty, np.ndarray) and empty.shape == (16, 16) and empty.sum() == 0.0

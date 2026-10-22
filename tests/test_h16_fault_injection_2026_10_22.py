"""H16: an empty answer and a failed operator are observably different.

The registry deliberately degrades by default.  These tests inject the same
``FsValueError`` immediately outside and immediately inside that wrapper: the
former proves the raw failure, while the latter pins strict propagation and the
fallback ledger.  Empty inputs use the real implementation, not the probe.
"""
from __future__ import annotations

import inspect
import warnings

import numpy as np
import pytest

import api
import backend_safe as bs
import blob2d
import image_gen
import ops
from fslib import FImage, FsTypeError, FsValueError, Region, connection, threshold


# name, input sort, output sort.  Together these cover region connection /
# selection / measurement, distance transforms, mean/rank filters, thresholding
# and contours. Domain and blob families have direct-contract tests below.
OPS = [
    ("threshold", "image", "region"),
    ("dyn_threshold", "image", "region"),
    ("mean_box_wh", "image", "image"),
    ("mean_image", "image", "image"),
    ("median", "image", "image"),
    ("dist_transform", "region", "image"),
    ("dist_transform_abs", "region", "image"),
    ("select_largest", "region", "region"),
    ("blob_count", "region", "feature"),
    ("area_center", "region", "match"),
    ("gen_contour_region_xld", "region", "contour"),
    ("edges_sub_pix", "image", "contour"),
]


@pytest.fixture(autouse=True)
def _clean_fallback_ledger():
    bs.clear_fallbacks(reset_warnings=True)
    yield
    bs.clear_fallbacks(reset_warnings=True)


@pytest.mark.parametrize(
    "name,in_sort,out_sort", OPS,
    ids=[f"{name}-empty" for name, _, _ in OPS],
)
def test_legitimate_empty_input_is_not_a_fallback(name, in_sort, out_sort):
    empty = np.zeros((8, 8), np.float64)
    result = api.apply(empty, name, 0.4, 0.6, on_error="raise")
    assert result is not None
    assert bs.fallbacks() == []
    if out_sort in {"image", "region"}:
        assert np.asarray(result).shape == empty.shape
    if in_sort == "region" and out_sort == "region":
        assert not np.asarray(result).any()


@pytest.mark.parametrize(
    "name,in_sort,out_sort", OPS,
    ids=[f"{name}-nan-fault" for name, _, _ in OPS],
)
def test_nan_wrapper_routes_propagate_an_injected_failure(
    monkeypatch, name, in_sort, out_sort
):
    """The exact same repository exception crosses both sides of the guard."""
    bad = np.zeros((8, 8), np.float64)
    bad[3, 4] = np.nan

    def raw(value, a, b):
        if not np.isfinite(np.asarray(value, dtype=np.float64)).all():
            raise FsValueError(f"{name}: image input contains NaN")
        return value

    with pytest.raises(FsValueError, match=rf"{name}.*NaN"):
        raw(bad, 0.4, 0.6)

    monkeypatch.setitem(ops.RT, name, bs.guard(raw, out_sort, name=name))
    with pytest.raises(FsValueError, match=rf"{name}.*NaN"):
        api.apply(bad, name, 0.4, 0.6, on_error="raise")
    assert bs.fallbacks() == []

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", bs.FullseyeFallbackWarning)
        degraded = api.apply(bad, name, 0.4, 0.6)
    assert degraded is not None
    event = bs.fallbacks()[-1]
    assert event["name"] == name
    assert event["source"] == "op"
    assert "NaN" in event["error"]


_FAIL_CLOSED = {
    "threshold", "dyn_threshold", "dist_transform", "dist_transform_abs",
    "select_largest", "blob_count", "area_center",
    "gen_contour_region_xld", "edges_sub_pix",
}


@pytest.mark.parametrize(
    "name,in_sort,out_sort",
    OPS,
    ids=[name for name, _, _ in OPS],
)
def test_nan_input_contract_of_the_real_operator(name, in_sort, out_sort):
    """Call the innermost implementation behind the registry's real callable."""
    bad = np.zeros((8, 8), np.float64)
    bad[3, 4] = np.nan
    op = next(op for op in ops.REGISTRY if op.name == name)
    raw = inspect.unwrap(op.fn)
    if name in _FAIL_CLOSED:
        with pytest.raises(FsValueError, match=rf"{name}.*NaN"):
            raw(bad, 0.4, 0.6)
        with pytest.raises(FsValueError, match=rf"{name}.*NaN"):
            api.apply(bad, name, 0.4, 0.6, on_error="raise")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", bs.FullseyeFallbackWarning)
            assert api.apply(bad, name, 0.4, 0.6) is not None
        event = bs.fallbacks()[-1]
        assert event["name"] == name and "NaN" in event["error"]
        return

    result = raw(bad, 0.4, 0.6)
    nan = np.isnan(result)
    assert nan.sum() >= 1
    if name != "median":
        assert nan[3, 4]


@pytest.mark.parametrize(
    "name,in_sort,out_sort", OPS,
    ids=[f"{name}-swapped-sort" for name, _, _ in OPS],
)
def test_swapped_typed_sort_is_rejected(name, in_sort, out_sort):
    wrong = Region(np.zeros((8, 8), bool)) if in_sort == "image" else FImage(
        np.zeros((8, 8)), (0.0, 1.0)
    )
    with pytest.raises((TypeError, ValueError), match="expects|numeric|ndim|shape"):
        api.apply(wrong, name, 0.4, 0.6, on_error="raise")
    assert bs.fallbacks() == []


@pytest.mark.parametrize(
    "operator", [image_gen.change_domain, image_gen.reduce_domain],
    ids=lambda fn: f"{fn.__name__}-empty-nan-sort",
)
def test_domain_raw_contract(operator):
    image = np.ones((4, 5), np.float64)
    result = operator(image, np.zeros(image.shape, bool))
    assert not result["domain"].any()
    bad = image.copy(); bad[0, 0] = np.nan
    with pytest.raises(FsValueError, match=rf"{operator.__name__}.*NaN"):
        operator(bad, np.zeros(image.shape, bool))
    with pytest.raises(FsTypeError, match=rf"{operator.__name__}.*region"):
        operator(image, np.full(image.shape, 0.25))


def test_typed_connection_and_threshold_raw_contracts():
    assert connection(Region(np.zeros((4, 5), bool))).ids.size == 0
    assert threshold(FImage(np.zeros((4, 5)), (0.0, 1.0)), 0.5, 1.0).area() == 0
    with pytest.raises(FsTypeError, match="connection.*Region"):
        connection(FImage(np.zeros((4, 5)), (0.0, 1.0)))
    with pytest.raises(FsTypeError, match="threshold.*FImage"):
        threshold(Region(np.zeros((4, 5), bool)), 0.5, 1.0)


@pytest.mark.parametrize(
    "operator,kwargs", [
        pytest.param(blob2d.blob_select, {"feature": "area", "vmin": 1}, id="blob_select-empty-sort"),
        pytest.param(blob2d.blob_select_largest, {}, id="blob_select_largest-empty-sort"),
    ],
)
def test_blob_measurement_empty_and_wrong_sort(operator, kwargs):
    out = operator(np.zeros((4, 5), np.int32), **kwargs)
    assert out.dtype == np.int32 and not out.any()
    with pytest.raises((TypeError, ValueError)):
        operator(np.zeros((4, 5), bool), **kwargs)

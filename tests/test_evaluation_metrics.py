"""Shared metric policies are explicit at every call site."""

import numpy as np
import pytest

from fullseye.evaluation.metrics import dice, iou, mae, relative_error, rmse


KW = {
    "nan_policy": "raise",
    "weights": None,
    "unit": "mm",
    "reduction": "mean",
    "empty": "raise",
    "domain": "array",
}


def test_rmse_and_mae_honor_mask_and_weights():
    measured = np.array([0.0, 2.0, 8.0])
    expected = np.array([0.0, 0.0, 0.0])
    mask = np.array([True, True, False])
    assert rmse(measured, expected, mask=mask, **KW) == pytest.approx(np.sqrt(2.0))
    weighted = dict(KW, weights=np.array([1.0, 3.0, 1.0]))
    assert mae(measured, expected, mask=mask, **weighted) == pytest.approx(1.5)


def test_nan_policies_and_empty_policies_are_not_implicit():
    a = np.array([1.0, np.nan])
    b = np.array([0.0, 0.0])
    with pytest.raises(ValueError, match="NaN"):
        rmse(a, b, mask=None, **KW)
    omit = dict(KW, nan_policy="omit")
    assert rmse(a, b, mask=None, **omit) == 1.0
    propagate = dict(KW, nan_policy="propagate")
    assert np.isnan(rmse(a, b, mask=None, **propagate))
    empty = dict(KW, empty="nan")
    assert np.isnan(mae(a, b, mask=np.zeros(2, bool), **empty))


def test_relative_error_uses_explicit_denominator_floor():
    result = relative_error(
        np.array([0.1, 2.0]),
        np.array([0.0, 1.0]),
        denominator_floor=0.5,
        mask=None,
        **KW,
    )
    assert result == pytest.approx(0.6)
    with pytest.raises(ValueError, match="denominator_floor"):
        relative_error([1.0], [1.0], denominator_floor=0.0, mask=None, **KW)


def test_iou_and_dice_apply_empty_policy_and_mask():
    binary_kw = dict(KW, unit="1")
    a = np.array([True, True, False, False])
    b = np.array([True, False, True, False])
    assert iou(a, b, mask=None, **binary_kw) == pytest.approx(1 / 3)
    assert dice(a, b, mask=None, **binary_kw) == pytest.approx(0.5)
    empty_kw = dict(binary_kw, empty="one")
    assert iou(np.zeros(4, bool), np.zeros(4, bool), mask=None, **empty_kw) == 1.0
    with pytest.raises(ValueError, match="selection is empty"):
        dice(np.zeros(4, bool), np.zeros(4, bool), mask=None, **binary_kw)

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Evaluation metrics with explicit mask, NaN, weighting, unit, and empty policies.

The numerical bases are existing, tested implementations:

* RMSE delegates to :func:`imgmetrics.rmse` or
  :func:`metrics3d.rmse_correspondence`.
* MAE delegates to :func:`fullseye.validation_kit.aggregate`.
* IoU and Dice delegate to :func:`metrics3d.voxel_iou` and
  :func:`metrics3d.voxel_dice` for their unweighted scalar form.

Only policy selection and input preparation live here.
"""

from __future__ import annotations

from typing import Any

import numpy as np


_NAN_POLICIES = frozenset({"raise", "omit", "propagate"})
_REDUCTIONS = frozenset({"mean", "sum", "none"})
_EMPTY_POLICIES = frozenset({"raise", "nan", "zero", "one"})
_DOMAINS = frozenset({"array", "image2d", "volume3d", "points3d"})


def rmse(
    measured,
    expected,
    *,
    mask=None,
    nan_policy: str,
    weights=None,
    unit: str,
    reduction: str,
    empty: str,
    domain: str,
):
    """Root-mean-square error with every interpretation choice explicit."""
    a, b, selected, w = _prepare_numeric(
        measured,
        expected,
        mask=mask,
        nan_policy=nan_policy,
        weights=weights,
        unit=unit,
        reduction=reduction,
        empty=empty,
        domain=domain,
    )
    if not selected.any():
        return _empty_value(empty)
    sq = (a - b) ** 2
    if reduction == "none":
        return _restore(sq**0.5, selected)
    if reduction == "sum":
        return float(np.sum(sq if w is None else sq * w) ** 0.5)
    if w is not None:
        return float(np.sqrt(np.sum(sq * w) / np.sum(w)))
    if nan_policy == "propagate" and not np.all(np.isfinite(sq)):
        return float(np.sqrt(np.mean(sq)))
    if domain == "points3d" and mask is None and nan_policy == "raise":
        import metrics3d

        return metrics3d.rmse_correspondence(a.reshape(-1, 3), b.reshape(-1, 3))
    import imgmetrics

    return imgmetrics.rmse(a, b)


def mae(
    measured,
    expected,
    *,
    mask=None,
    nan_policy: str,
    weights=None,
    unit: str,
    reduction: str,
    empty: str,
    domain: str,
):
    """Mean absolute error backed by ``validation_kit.aggregate``."""
    a, b, selected, w = _prepare_numeric(
        measured,
        expected,
        mask=mask,
        nan_policy=nan_policy,
        weights=weights,
        unit=unit,
        reduction=reduction,
        empty=empty,
        domain=domain,
    )
    if not selected.any():
        return _empty_value(empty)
    err = np.abs(a - b)
    if reduction == "none":
        return _restore(err, selected)
    if reduction == "sum":
        return float(np.sum(err if w is None else err * w))
    if w is not None:
        return float(np.sum(err * w) / np.sum(w))
    if nan_policy == "propagate" and not np.all(np.isfinite(err)):
        return float(np.mean(err))
    from fullseye.validation_kit import aggregate

    return float(aggregate(b.ravel().tolist(), a.ravel().tolist())["mean_abs_error"])


def relative_error(
    measured,
    expected,
    *,
    denominator_floor: float,
    mask=None,
    nan_policy: str,
    weights=None,
    unit: str,
    reduction: str,
    empty: str,
    domain: str,
):
    """Absolute relative error ``|measured-expected|/max(|expected|, floor)``."""
    if not np.isfinite(denominator_floor) or denominator_floor <= 0:
        raise ValueError("denominator_floor must be positive and finite")
    a, b, selected, w = _prepare_numeric(
        measured,
        expected,
        mask=mask,
        nan_policy=nan_policy,
        weights=weights,
        unit=unit,
        reduction=reduction,
        empty=empty,
        domain=domain,
    )
    if not selected.any():
        return _empty_value(empty)
    err = np.abs(a - b) / np.maximum(np.abs(b), float(denominator_floor))
    if reduction == "none":
        return _restore(err, selected)
    if reduction == "sum":
        return float(np.sum(err if w is None else err * w))
    return float(np.mean(err) if w is None else np.sum(err * w) / np.sum(w))


def iou(
    measured,
    expected,
    *,
    mask=None,
    nan_policy: str,
    weights=None,
    unit: str,
    reduction: str,
    empty: str,
    domain: str,
):
    """Boolean intersection-over-union under an explicit evaluation mask."""
    return _overlap(
        measured,
        expected,
        metric="iou",
        mask=mask,
        nan_policy=nan_policy,
        weights=weights,
        unit=unit,
        reduction=reduction,
        empty=empty,
        domain=domain,
    )


def dice(
    measured,
    expected,
    *,
    mask=None,
    nan_policy: str,
    weights=None,
    unit: str,
    reduction: str,
    empty: str,
    domain: str,
):
    """Boolean Dice coefficient under an explicit evaluation mask."""
    return _overlap(
        measured,
        expected,
        metric="dice",
        mask=mask,
        nan_policy=nan_policy,
        weights=weights,
        unit=unit,
        reduction=reduction,
        empty=empty,
        domain=domain,
    )


def _prepare_numeric(
    measured,
    expected,
    *,
    mask,
    nan_policy: str,
    weights,
    unit: str,
    reduction: str,
    empty: str,
    domain: str,
):
    _validate_policies(nan_policy, unit, reduction, empty, domain)
    a = np.asarray(measured, dtype=np.float64)
    b = np.asarray(expected, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(f"measured and expected shapes differ: {a.shape} != {b.shape}")
    if a.size == 0:
        return a, b, np.zeros(a.shape, bool), None
    _validate_domain(a, domain)
    selected = _selection(mask, a.shape)
    finite = np.isfinite(a) & np.isfinite(b)
    if nan_policy == "raise" and np.any(selected & ~finite):
        raise ValueError("selected values contain NaN or inf")
    if nan_policy == "omit":
        selected &= finite
    w = _weights(weights, a.shape, selected, nan_policy)
    a_sel, b_sel = a[selected], b[selected]
    w_sel = None if w is None else w[selected]
    if w_sel is not None and not np.any(w_sel > 0):
        a_sel = a_sel[:0]
        b_sel = b_sel[:0]
        w_sel = w_sel[:0]
        selected &= False
    return a_sel, b_sel, selected, w_sel


def _overlap(
    measured,
    expected,
    *,
    metric: str,
    mask,
    nan_policy: str,
    weights,
    unit: str,
    reduction: str,
    empty: str,
    domain: str,
):
    _validate_policies(nan_policy, unit, reduction, empty, domain)
    if reduction != "mean":
        raise ValueError("IoU and Dice are scalar set metrics; reduction must be 'mean'")
    a0 = np.asarray(measured)
    b0 = np.asarray(expected)
    if a0.shape != b0.shape:
        raise ValueError(f"measured and expected shapes differ: {a0.shape} != {b0.shape}")
    if a0.size == 0:
        return _empty_value(empty)
    _validate_domain(a0, domain)
    selected = _selection(mask, a0.shape)
    finite = _finite_for_overlap(a0) & _finite_for_overlap(b0)
    if nan_policy == "raise" and np.any(selected & ~finite):
        raise ValueError("selected values contain NaN or inf")
    if nan_policy == "omit":
        selected &= finite
    if nan_policy == "propagate" and np.any(selected & ~finite):
        return float("nan")
    if not selected.any():
        return _empty_value(empty)
    a = np.asarray(a0, dtype=bool)[selected]
    b = np.asarray(b0, dtype=bool)[selected]
    w = _weights(weights, a0.shape, selected, nan_policy)
    if w is None:
        if not np.any(a | b):
            return _empty_value(empty)
        import metrics3d

        return metrics3d.voxel_iou(a, b, iso=0.5) if metric == "iou" else metrics3d.voxel_dice(a, b, iso=0.5)
    ww = w[selected]
    if not np.any(ww > 0):
        return _empty_value(empty)
    inter = float(np.sum(ww[a & b]))
    if metric == "iou":
        den = float(np.sum(ww[a | b]))
    else:
        den = float(np.sum(ww[a]) + np.sum(ww[b]))
        inter *= 2.0
    return _empty_value(empty) if den == 0 else inter / den


def _validate_policies(nan_policy: str, unit: str, reduction: str, empty: str, domain: str) -> None:
    if nan_policy not in _NAN_POLICIES:
        raise ValueError("nan_policy must be raise/omit/propagate")
    if reduction not in _REDUCTIONS:
        raise ValueError("reduction must be mean/sum/none")
    if empty not in _EMPTY_POLICIES:
        raise ValueError("empty must be raise/nan/zero/one")
    if domain not in _DOMAINS:
        raise ValueError("domain must be array/image2d/volume3d/points3d")
    if not isinstance(unit, str) or not unit:
        raise ValueError("unit must be a non-empty string")


def _validate_domain(a: np.ndarray, domain: str) -> None:
    if domain == "image2d" and a.ndim != 2:
        raise ValueError(f"image2d metric requires 2-D arrays, got {a.shape}")
    if domain == "volume3d" and a.ndim != 3:
        raise ValueError(f"volume3d metric requires 3-D arrays, got {a.shape}")
    if domain == "points3d" and (a.ndim != 2 or a.shape[1] != 3):
        raise ValueError(f"points3d metric requires (N,3), got {a.shape}")


def _selection(mask, shape: tuple[int, ...]) -> np.ndarray:
    if mask is None:
        return np.ones(shape, dtype=bool)
    selected = np.asarray(mask)
    if selected.shape != shape:
        raise ValueError(f"mask shape {selected.shape} must equal data shape {shape}")
    if selected.dtype != np.bool_:
        raise ValueError("mask must have boolean dtype")
    return selected.copy()


def _weights(weights, shape: tuple[int, ...], selected: np.ndarray, nan_policy: str):
    if weights is None:
        return None
    w = np.asarray(weights, dtype=np.float64)
    if w.shape != shape:
        raise ValueError(f"weights shape {w.shape} must equal data shape {shape}")
    if np.any(w[selected] < 0):
        raise ValueError("weights must be non-negative")
    if nan_policy == "raise" and np.any(~np.isfinite(w[selected])):
        raise ValueError("selected weights contain NaN or inf")
    if nan_policy == "omit":
        selected &= np.isfinite(w)
    return w


def _empty_value(policy: str):
    if policy == "raise":
        raise ValueError("metric selection is empty")
    if policy == "nan":
        return float("nan")
    if policy == "zero":
        return 0.0
    return 1.0


def _restore(values: np.ndarray, selected: np.ndarray):
    if selected.all():
        return values.reshape(selected.shape)
    out = np.full(selected.shape, np.nan, dtype=np.float64)
    out[selected] = values
    return out


def _finite_for_overlap(a: np.ndarray) -> np.ndarray:
    if np.issubdtype(a.dtype, np.number):
        return np.isfinite(a)
    return np.ones(a.shape, dtype=bool)

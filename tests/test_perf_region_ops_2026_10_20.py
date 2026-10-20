"""Performance slice 12 gates against the implementations replaced here."""
from __future__ import annotations

import numpy as np
import pytest

import blob2d as B


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

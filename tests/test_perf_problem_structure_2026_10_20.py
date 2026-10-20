"""Regression gates for optimisations that exploit existing problem structure."""
from __future__ import annotations

import math

import numpy as np
import pytest

import anomeval


def _old_operating_point(scores, labels, recall=0.95, confidence=0.95):
    """Reference kept from the pre-optimisation implementation."""
    s = np.asarray(scores, dtype=np.float64).ravel()
    y = np.asarray(labels, dtype=bool).ravel()
    rec, conf = float(recall), float(confidence)
    alpha = 1.0 - conf
    pos = int(y.sum())
    neg = int(y.size - pos)
    n_req = int(math.ceil(math.log(alpha) / math.log(rec) - 1e-12))
    if pos < n_req:
        raise ValueError
    ds = np.sort(s[y])[::-1]
    k = next(kk for kk in range(1, pos + 1)
             if anomeval._cp_lower(kk, pos, alpha) >= rec)
    thr = float(ds[k - 1])
    detected = int((ds >= thr).sum())
    fa = int((s[~y] >= thr).sum())
    return {"threshold": thr, "recall_observed": detected / pos,
            "recall_lower": anomeval._cp_lower(detected, pos, alpha),
            "detected": detected, "n_pos": pos, "n_neg": neg,
            "fpr": fa / neg, "fpr_upper": anomeval._cp_upper(fa, neg, alpha),
            "n_required": n_req, "recall": rec, "confidence": conf}, k


@pytest.mark.parametrize("n_pos", [10, 1_000, 100_000])
@pytest.mark.parametrize("recall,confidence", [(0.01, 0.01), (0.5, 0.9), (0.999, 0.01)])
def test_operating_point_bisection_matches_linear_with_ties(n_pos, recall, confidence):
    rng = np.random.default_rng(800 + n_pos)
    defect = rng.integers(0, 17, n_pos).astype(float)
    good = rng.integers(0, 17, max(7, n_pos // 5)).astype(float)
    scores = np.r_[defect, good]
    labels = np.r_[np.ones(n_pos, bool), np.zeros(good.size, bool)]
    try:
        expected, expected_k = _old_operating_point(scores, labels, recall, confidence)
    except ValueError:
        with pytest.raises(ValueError):
            anomeval.anomaly_operating_point(scores, labels, recall, confidence)
        return
    actual = anomeval.anomaly_operating_point(scores, labels, recall, confidence)
    assert actual == expected
    assert actual["detected"] >= expected_k  # ties at the selected score are recounted


def test_operating_point_bound_calls_are_logarithmic(monkeypatch):
    n = 100_000
    scores = np.r_[np.arange(n, dtype=float), -1.0]
    labels = np.r_[np.ones(n, bool), False]
    original = anomeval._cp_lower
    calls = 0

    def counted(k, total, alpha):
        nonlocal calls
        calls += 1
        return original(k, total, alpha)

    monkeypatch.setattr(anomeval, "_cp_lower", counted)
    anomeval.anomaly_operating_point(scores, labels, recall=0.95, confidence=0.95)
    assert calls <= math.ceil(math.log2(n)) + 2

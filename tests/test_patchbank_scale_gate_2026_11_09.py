"""patchbank_fit / patchbank_score: 学習時の画素の尺度を覚えていなかった(2026-11-09 点検)。

float [0, 1] で学習し、同じ良品を uint8 で採点すると image_score が 8.08 → 4366(540 倍)、例外なし。
"""
import numpy as np
import pytest
from scipy import ndimage

import anomaly_patch as A


def _goods(n=4, seed=0):
    rng = np.random.default_rng(seed)
    return [np.clip(ndimage.gaussian_filter(rng.random((48, 48)), 1.5) * 1.6 - 0.3, 0, 1) for _ in range(n)]


def _model():
    return A.patchbank_fit(_goods(), patch=8, stride=8, scales=(1.0,), groups=("gradient",), coreset=1.0,
                           proj_dim=None)


def test_model_remembers_the_scale():
    m = _model()
    lo, hi = m["input_range"]
    assert 0.0 <= lo < hi <= 1.0 and m["input_integer"] is False


def test_uint8_image_on_a_float_model_is_refused():
    m = _model()
    good = _goods(1, seed=9)[0]
    s = A.patchbank_score(good, m)["image_score"]
    assert np.isfinite(s)
    with pytest.raises(ValueError, match="fitted on float"):
        A.patchbank_score(np.round(good * 255).astype(np.uint8), m)
    with pytest.raises(ValueError, match="pixel scale"):
        A.patchbank_score(good * 255.0, m)


def test_same_scale_scores_unchanged_by_the_gate():
    m = _model()
    good = _goods(1, seed=9)[0]
    a = A.patchbank_score(good, m)["image_score"]
    m2 = {k: v for k, v in m.items() if k not in ("input_range", "input_integer")}
    assert A.patchbank_score(good, m2)["image_score"] == a

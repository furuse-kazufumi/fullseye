"""vol_distance_transform: 背景が 1 つも無い体積で scipy の不定な斜面を返した(2026-11-09 点検)。

(1, 8, 8) の全前景で最大 9.95・最小 1.0。2-D の distance_transform は 2026-11-05 に直した(全 1)。
"""
import numpy as np
from scipy import ndimage

import volops as V


def test_all_foreground_is_infinitely_far():
    out = V.vol_distance_transform(np.ones((1, 8, 8), bool))
    assert out.shape == (1, 8, 8) and np.isinf(out).all() and (out > 0).all()
    out = V.vol_distance_transform(np.ones((3, 4, 5)), spacing=(2.0, 1.0, 1.0))
    assert np.isinf(out).all()


def test_normal_input_still_matches_scipy():
    m = np.zeros((3, 20, 20), bool)
    m[:, 5:15, 4:18] = True
    m[1, 10, 10] = False
    assert np.array_equal(V.vol_distance_transform(m), ndimage.distance_transform_edt(m))
    assert np.array_equal(V.vol_distance_transform(m, spacing=(5.0, 1.0, 2.0)),
                          ndimage.distance_transform_edt(m, sampling=(5.0, 1.0, 2.0)))

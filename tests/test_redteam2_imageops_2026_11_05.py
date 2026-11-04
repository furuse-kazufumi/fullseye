"""敵対的検証 2026-11-05 第 2 巡(imageops)の回帰テスト。

報告の再現を「真値・不変量・独立実装と比べる」形で固定する。各節の見出しに ID(P1〜)を書く。
"""
from __future__ import annotations

import warnings

import numpy as np
import pytest
from scipy import ndimage

import api

warnings.filterwarnings("ignore")


def ap(x, name, a=0.5, b=0.5):
    return np.asarray(api.apply(np.asarray(x, float).copy(), name, a, b, on_error="raise"), float)


def _diag_squares(H=96):
    """斜めに 1 点で接する 2 つの 20x20 の正方形(8 連結で 1 物体、4 連結で 2 物体)。"""
    m = np.zeros((H, H))
    m[10:30, 10:30] = 1
    m[30:50, 30:50] = 1
    return m


# --------------------------------------------------------------------------------------------- #
# P1: 前景の連結成分は 8 連結(HALCON の connection の既定、count_obj と同じ)
# --------------------------------------------------------------------------------------------- #
def test_p1_the_probe_is_one_object_under_8_connectivity():
    m = _diag_squares()
    assert ndimage.label(m > 0.5, structure=np.ones((3, 3)))[1] == 1
    assert ndimage.label(m > 0.5)[1] == 2
    assert ap(m, "count_obj") == 1.0


SELECTORS = ["select_largest", "select_shape_std", "r2_sort_region"]


@pytest.mark.parametrize("name", SELECTORS)
def test_p1_selecting_the_largest_keeps_the_whole_8_connected_object(name):
    m = _diag_squares()
    y = ap(m, name, 0.0, 0.5)
    assert int((y > 0.5).sum()) == int(m.sum()) == 800
    assert np.array_equal(y > 0.5, m > 0.5)


def test_p1_select_region_point_takes_the_whole_8_connected_object():
    m = _diag_squares()
    y = ap(m, "r3_select_region_point", 15 / 95, 15 / 95)      # (15, 15) は左上の正方形
    assert np.array_equal(y > 0.5, m > 0.5)


def test_p1_remove_small_does_not_drop_diagonally_touching_halves():
    """2 つの半分(各 100 画素)は 8 連結で 200 画素の 1 物体。閾値 150 画素で残るべき。"""
    m = np.zeros((64, 64))
    m[10:20, 10:20] = 1
    m[20:30, 20:30] = 1
    a = (150 / m.size - 0.01) / 0.15                          # ops.remove_small: thr = (0.01+0.15a)*画素数
    assert 0.0 < a < 1.0
    assert int((ap(m, "remove_small", a, 0.5) > 0.5).sum()) == 200
    a2 = (150 - 16) / 200                                     # select_shape: thr = int(16+200a)
    assert int((ap(m, "select_shape", a2, 0.5) > 0.5).sum()) == 200


def test_p1_region_features_measure_the_whole_8_connected_object():
    """周囲長は skimage の regionprops(8 連結の 1 物体)と、2 次モーメントは 1 物体の閉形式と一致する。"""
    from skimage import measure
    m = _diag_squares()
    rp = measure.regionprops(measure.label(m > 0.5, connectivity=2))
    assert len(rp) == 1
    assert ap(m, "contlength") == pytest.approx(rp[0].perimeter, rel=1e-9)
    one = np.zeros_like(m)
    one[10:30, 10:30] = 1
    assert ap(m, "contlength") > 1.9 * ap(one, "contlength")
    assert ap(m, "diameter_region") > 2.0 * ap(one, "diameter_region") - 1.0
    # 1 物体の面積は 800: 凸性 = 面積 / 凸包の面積 は 1 未満(片方の正方形なら 1.0)
    assert ap(m, "convexity") == pytest.approx(rp[0].area / rp[0].area_convex, rel=1e-9)
    assert ap(m, "convexity") < 0.75


def test_p1_classify_shape_measures_the_whole_object():
    m = _diag_squares()
    one = np.zeros_like(m)
    one[10:30, 10:30] = 1
    # 2 つの正方形をつないだ形は 1 つの正方形より円から遠い
    assert ap(m, "classify_shape") < ap(one, "classify_shape") - 0.1


def test_p1_split_skeleton_lines_keeps_a_diagonal_segment():
    """斜め 45 度の 1 本の太い棒の骨格は 8 連結の 1 本の線。min_len で消えてはならない。"""
    m = np.zeros((64, 64))
    for i in range(8, 56):
        m[i, max(0, i - 3):i + 4] = 1
    sk = ap(m, "r2_split_skeleton_lines", 0.0, 0.5)
    n_sk = int((sk > 0.5).sum())
    assert n_sk >= 30
    kept = ap(m, "r2_split_skeleton_lines", 1.0, 0.5)          # min_len = 8
    assert int((kept > 0.5).sum()) >= n_sk - 8


def test_p1_accel_label_paths_use_the_same_connectivity():
    torch = pytest.importorskip("torch")
    import accel_label as AL
    m = _diag_squares()
    t = torch.as_tensor(m[None, None])
    for fn, name in [(AL._select_largest, "select_shape_std"), (AL._sort_region, "r2_sort_region")]:
        got = fn(t, 0.0, 0.5, "cpu")[0, 0].numpy()
        assert np.array_equal(got > 0.5, ap(m, name, 0.0, 0.5) > 0.5)
        assert int((got > 0.5).sum()) == 800


# --------------------------------------------------------------------------------------------- #
# P2: compactness は HALCON と同じ max(1, L²/(4πF))。説明文も同じことを言う
# --------------------------------------------------------------------------------------------- #
def test_p2_compactness_is_halcon_max_one_and_the_help_says_so():
    from skimage import draw, measure
    import ops
    radii = [3, 6, 20, 40]
    assert len(radii) == 4
    for r in radii:
        d = np.zeros((96, 96))
        rr, cc = draw.disk((48, 48), r, shape=d.shape)
        d[rr, cc] = 1
        rp = measure.regionprops(d.astype(int))[0]
        raw = rp.perimeter ** 2 / (4 * np.pi * rp.area)
        assert ap(d, "compactness") == pytest.approx(max(1.0, raw), rel=1e-9)
    assert ap(np.zeros((16, 16)), "compactness") == 0.0          # HALCON: 空の領域は 0
    doc = ops._BY_NAME["compactness"].doc
    assert "max(1, 周囲長²" in doc
    assert "ここでは切らない。" not in doc

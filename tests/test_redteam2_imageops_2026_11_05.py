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


# --------------------------------------------------------------------------------------------- #
# P3: 二値 closing は拡大的で、画像の外へ続く平面の上の closing を切り戻したものと同じ
# --------------------------------------------------------------------------------------------- #
def _border_probe():
    X = np.zeros((40, 48))
    X[0:15, 0:20] = 1          # 左上の角に接する矩形
    X[25:40, 30:48] = 1        # 右下の角に接する矩形
    X[18:22, 10:14] = 1
    X[5:8, 30:33] = 1
    X[30, 5] = 1               # 孤立画素
    X[1, 40] = 1               # 縁の近くの孤立画素(border_value=1 だと角の楔が生える)
    return X


CLOSINGS = ["closing_circle", "closing_rectangle1", "closing_golay", "hx_closing", "reg_close", "convex_fill"]


@pytest.mark.parametrize("name", CLOSINGS)
@pytest.mark.parametrize("a", [0.0, 0.5, 1.0])
def test_p3_binary_closing_is_extensive_and_equals_the_unbounded_plane(name, a):
    X = _border_probe()
    y = ap(X, name, a) > 0.5
    assert not ((X > 0.5) & ~y).any(), "closing は入力の前景を削らない(X ⊆ φ(X))"
    # 真値: 余白 24 の大きな画像の上で同じ op を当て、元の窓に切り戻したもの(縁はもう縁でない)
    P = 24
    big = np.pad(X, P)
    ref = ap(big, name, a)[P:-P, P:-P] > 0.5
    assert np.array_equal(y, ref)
    assert np.array_equal(ap(y, name, a) > 0.5, y), "冪等"


def test_p3_reg_close_does_not_grow_a_wedge_from_a_lone_pixel_near_the_corner():
    X = np.zeros((20, 20))
    X[1, 1] = 1
    for a in (0.0, 0.5, 1.0):
        assert int((ap(X, "reg_close", a) > 0.5).sum()) == 1


def test_p3_close_edges_keeps_edges_on_the_image_border():
    ones = np.ones((20, 20))
    for b in (0.0, 0.5, 1.0):
        assert int((ap(ones, "hx_close_edges", 0.5, b) > 0.5).sum()) == 400
    assert int((ap(ones, "hx_close_edges_length", 0.5, 0.5) > 0.5).sum()) == 400


def test_p3_close_edges_length_counts_diagonal_lines_as_one_piece():
    """1 画素幅の斜め線(長さ 20)は 8 近傍で 1 成分。min_len = 2+int(b*20) = 12 で消えない。"""
    v = np.zeros((40, 40))
    for i in range(20):
        v[10 + i, 10 + i] = 1.0
    y = ap(v, "hx_close_edges_length", 0.5, 0.5)
    assert int((y > 0.5).sum()) >= 20


# --------------------------------------------------------------------------------------------- #
# P4 / P4b: 距離を測る相手が画像に無い入力、領域の量は画像の縁に依らない
# --------------------------------------------------------------------------------------------- #
@pytest.mark.parametrize("name,x", [("dist_transform", np.ones((6, 8))), ("distance_transform", np.ones((6, 8))),
                                    ("closest_point_transform", np.zeros((6, 8)))])
def test_p4_normalised_distance_with_nothing_to_reach_is_uniform_one(name, x):
    """相手が無い = どこも無限に遠い -> 正規化した答えは一様 1.0(xsp_chamfer_dist / cv_dist と同じ)。"""
    y = ap(x, name, 0.0, 0.0)
    assert np.array_equal(y, np.ones_like(x))
    assert np.array_equal(y, ap(x[:, ::-1], name, 0.0, 0.0)[:, ::-1])


@pytest.mark.parametrize("a", [0.0, 0.5, 1.0])
def test_p4_absolute_distance_with_nothing_to_reach_is_refused(a):
    from fslib import FsValueError
    import ops
    with pytest.raises(FsValueError, match="undefined"):
        ops._dist_transform_abs(np.ones((6, 8)), a, 0.0)
    with pytest.raises(FsValueError, match="undefined"):
        ops._dist_transform_abs(np.zeros((6, 8)), a, 1.0)
    # 相手が 1 画素でもあれば距離は有限で、左右の反転と可換
    x = np.ones((6, 8))
    x[2, 3] = 0
    y = ops._dist_transform_abs(x, a, 0.0)
    assert np.isfinite(y).all() and y[2, 3] == 0.0


def test_p4b_the_documented_example_values_hold():
    import ops
    for k, centre in [(3, 2.0), (9, 5.0)]:
        sq = np.pad(np.ones((k, k)), 1)
        assert ops._dist_transform_abs(sq, 0.0, 0.0)[1 + k // 2, 1 + k // 2] == pytest.approx(centre)
    doc = ops._dist_transform_abs.__doc__
    assert "np.pad(np.ones((3, 3)), 1)" in doc


def test_p4_region_thickness_does_not_depend_on_the_image_border():
    """太さは領域そのものの量: 画像を広げても同じ。全面の 60x80 は 60、縁に接する 30x70 は 30。"""
    full = np.ones((60, 80))
    assert ap(full, "get_region_thickness") == pytest.approx(ap(np.pad(full, 10), "get_region_thickness"))
    assert ap(full, "get_region_thickness") == pytest.approx(60.0, abs=1.0)
    r = np.zeros((50, 80))
    r[0:30, 10:80] = 1
    assert ap(r, "get_region_thickness") == pytest.approx(ap(np.pad(r, 10), "get_region_thickness"))
    assert ap(r, "get_region_thickness") == pytest.approx(30.0, abs=1.0)


def test_p4_inner_circle_stays_inside_a_region_that_fills_the_image():
    full = np.ones((20, 30))
    y = ap(full, "r2_inner_circle", 0.5, 0.5) > 0.5
    ref = ap(np.pad(full, 12), "r2_inner_circle", 0.5, 0.5)[12:-12, 12:-12] > 0.5
    assert np.array_equal(y, ref)
    assert int(y.sum()) < 0.6 * full.size                    # 半径 ~10 の円(以前は画像全体 600 画素)
    ys, xs = np.nonzero(y)
    assert abs(ys.mean() - 9.5) <= 1.0 and abs(xs.mean() - 14.5) <= 6.0


# --------------------------------------------------------------------------------------------- #
# P5: xsk_blob_doh のしきい値は DoH の応答の桁に合う(b=0.5 で skimage の既定 0.01)
# --------------------------------------------------------------------------------------------- #
@pytest.mark.parametrize("sigma", [3.0, 6.0])
def test_p5_blob_doh_counts_the_gaussian_spots_like_skimage(sigma):
    from skimage import feature
    x = np.zeros((128, 128))
    centres = [(25, 25), (25, 95), (64, 60), (100, 25), (100, 100)]
    for (r, c) in centres:
        x[r, c] = 1
    x = ndimage.gaussian_filter(x, sigma)
    x = 0.1 + 0.8 * x / x.max()
    assert len(feature.blob_doh(x)) == len(centres)                   # 独立参照: skimage の既定
    assert ap(x, "xsk_blob_doh", 0.5, 0.5) == len(centres)
    counts = [ap(x, "xsk_blob_doh", 1.0, b) for b in (0.0, 0.25, 0.5, 0.75, 1.0)]
    assert len(counts) == 5
    assert all(c1 >= c2 for c1, c2 in zip(counts, counts[1:])), "しきい値を上げると数は減る"
    assert ap(x, "xsk_blob_log", 0.5, 0.5) == len(centres)            # LoG は変えていない

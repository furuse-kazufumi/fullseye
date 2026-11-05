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
def test_p4_absolute_distance_with_nothing_to_reach_is_uniform_zero(a):
    """相手が無い入力は正当な空入力: 例外でなく一様 0(斜面や -1 ではない)、反転と可換。"""
    import ops
    for x, b in ((np.ones((6, 8)), 0.0), (np.zeros((6, 8)), 1.0)):
        y = ops._dist_transform_abs(x, a, b)
        assert np.array_equal(y, np.zeros_like(x))
        assert np.array_equal(ap(x, "dist_transform_abs", a, b), np.zeros_like(x))
    # 相手が 1 画素でもあれば距離は有限で、その画素は 0
    x = np.ones((6, 8))
    x[2, 3] = 0
    y = ops._dist_transform_abs(x, a, 0.0)
    assert np.isfinite(y).all() and y[2, 3] == 0.0 and y.max() > 0


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


# --------------------------------------------------------------------------------------------- #
# P6: 微分の応答は一様な画像で定数、明るさの一様な足し算で変わらない(枠の 0 埋めの偽応答が無い)
# --------------------------------------------------------------------------------------------- #
P6_OPS = ["sk_corner_harris", "points_harris_binomial", "points_foerstner", "sk_hessian_det", "xsk_hessian_eig",
          "sk_shape_index", "xsk_struct_coherence", "xsk2_corner_kr"]


def _offset_probe():
    rng = np.random.default_rng(7)
    x = ndimage.gaussian_filter(rng.random((40, 48)), 1.5)
    x = (x - x.min()) / (x.max() - x.min()) * 0.6 + 0.15
    yy, xx = np.mgrid[0:40, 0:48]
    x[(yy - 20) ** 2 + (xx - 24) ** 2 < 36] = 0.8
    return x


@pytest.mark.parametrize("name", P6_OPS)
def test_p6_uniform_image_has_no_structure(name):
    for c in (0.0, 0.3, 0.7):
        y = ap(np.full((32, 32), c), name)
        assert float(np.ptp(y)) < 1e-6, (name, c, float(np.ptp(y)))


@pytest.mark.parametrize("name", P6_OPS)
def test_p6_response_is_invariant_to_a_brightness_offset(name):
    """微分だけで作る量は明るさの一様な足し算で変わらない —— 縁も内側も。"""
    x = _offset_probe()
    d = np.abs(ap(x + 0.1, name) - ap(x, name))
    assert float(d.max()) < 1e-6, (name, float(d.max()))


# --------------------------------------------------------------------------------------------- #
# P7: Perona–Malik 系は画像の縁で巻かない(局所性: n 回の 4 近傍の反復は n 画素より遠くへ届かない)
# --------------------------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["anisotropic_diffusion", "coherence_enhancing_diff", "alife_perona_malik",
                                  "dl_aniso_diffusion", "ph_perona_malik"])
def test_p7_diffusion_does_not_wrap_around_the_image(name):
    if name == "dl_aniso_diffusion":
        pytest.importorskip("torch")
    st = np.full((32, 64), 0.5)
    st[:, 0] = 0.4                                       # 左端の 1 列だけ段差。右端は 63 px 離れている
    o = ap(st, name, 1.0, 1.0)
    assert float(np.abs(o[:, 0] - st[:, 0]).max()) > 1e-3, "左端は拡散する(op が効いている)"
    assert float(np.abs(o[:, -24:] - st[:, -24:]).max()) == 0.0, "右の 24 列には届かない(反復 ≤ 20 回)"


def test_p7_monotony_does_not_compare_with_the_opposite_border():
    """左端だけ明るい列の画素: 画像の中の暗い近傍は右の 3 つだけ(8 近傍のうち 3)。反対側の縁(右端、暗い)を
    近傍に数えると 6 になる。"""
    x = np.zeros((8, 8))
    x[:, 0] = 1.0
    y = ap(x, "monotony")
    assert y[3, 0] == pytest.approx(3 / 8)


# --------------------------------------------------------------------------------------------- #
# P8 / P9: 中心基準の変換は画素中心の規約 ((H-1)/2, (W-1)/2)、サイズ指定の縮小は画素中心合わせ
# --------------------------------------------------------------------------------------------- #
def _smooth(H=40, W=56, seed=1):
    rng = np.random.default_rng(seed)
    x = ndimage.gaussian_filter(rng.random((H, W)), 2.0)
    return (x - x.min()) / (x.max() - x.min()) * 0.8 + 0.1


@pytest.mark.parametrize("name,a,b", [("zoom_image_factor", 1.0, 1.0), ("zoom_image_factor", 0.0, 0.3),
                                      ("affine_trans_image", 0.75, 0.5), ("affine_trans_image", 0.5, 1.0),
                                      ("rescale_img", 0.9, 0.5), ("affine_warp", 0.8, 0.7)])
def test_p8_centred_transforms_commute_with_a_half_turn(name, a, b):
    """画像の中心まわりの変換は、中心まわりの 180 度回転と可換(中心が半画素ずれると可換でない)。"""
    x = _smooth()
    y1 = ap(np.rot90(x, 2), name, a, b)
    y2 = np.rot90(ap(x, name, a, b), 2)
    assert float(np.abs(y1 - y2)[4:-4, 4:-4].max()) < 1e-9


def test_p8_zoom_keeps_the_centre_pixel_and_matches_scipy_zoom_about_the_pixel_centre():
    x = _smooth()
    H, W = x.shape
    s = 1.3
    c = np.array([(H - 1) / 2, (W - 1) / 2])
    ref = ndimage.affine_transform(x, np.diag([1 / s, 1 / s]), offset=c - c / s, mode="reflect")
    assert float(np.abs(ap(x, "zoom_image_factor", 1.0, 1.0) - ref)[4:-4, 4:-4].max()) < 1e-9
    d = np.zeros((41, 41))
    d[20, 20] = 1.0
    g = ndimage.gaussian_filter(d, 2.0)
    g /= g.max()
    Y, X = np.mgrid[0:41, 0:41]
    for name, a, b in [("zoom_image_factor", 1.0, 1.0), ("affine_trans_image", 1.0, 0.5)]:
        z = ap(g, name, a, b)
        assert (z * Y).sum() / z.sum() == pytest.approx(20.0, abs=1e-6)
        assert (z * X).sum() / z.sum() == pytest.approx(20.0, abs=1e-6)


@pytest.mark.parametrize("name", ["zoom_region", "affine_trans_region"])
def test_p8_region_transforms_keep_a_centred_square_centred(name):
    zr = np.zeros((41, 41))
    zr[16:25, 16:25] = 1
    ys, xs = np.nonzero(ap(zr, name, 1.0, 0.5) > 0.5)
    assert len(ys) > 0
    assert ys.mean() == pytest.approx(20.0, abs=1e-6) and xs.mean() == pytest.approx(20.0, abs=1e-6)


def test_p8_polar_transform_is_centred_on_the_image_centre():
    """画像の中心について回転対称な像の極座標展開は、角度(行)方向にほぼ一定。"""
    h, w = 40, 56
    yy, xx = np.mgrid[0:h, 0:w]
    img = np.exp(-((yy - (h - 1) / 2) ** 2 + (xx - (w - 1) / 2) ** 2) / (2 * 6.0 ** 2))
    out = ap(img, "polar_trans_image", 0.5, 0.5)
    assert float(np.ptp(out[:, 1:20], axis=0).max()) < 0.02     # 旧(中心 w/2、最近傍)は 0.25


def test_p9_zoom_image_size_samples_pixel_centres_like_cv2_resize():
    cv2 = pytest.importorskip("cv2")
    H = W = 64
    ramp = np.tile((np.arange(H) / (H - 1))[:, None], (1, W))
    small = ap(ramp, "zoom_image_size", 0.0, 0.0)[:32, :32]   # Ht = Wt = 32
    ref = cv2.resize(ramp.astype(np.float32), (32, 32), interpolation=cv2.INTER_LINEAR)
    assert float(np.abs(small - ref).max()) < 1e-6
    assert small.mean() == pytest.approx(ramp.mean(), abs=1e-9)
    x = _smooth(48, 48)
    got = ap(x, "zoom_image_size", 0.25, 0.25)                    # 0.75 倍 -> 36 x 36
    ref2 = cv2.resize(x.astype(np.float32), (36, 36), interpolation=cv2.INTER_LINEAR)
    assert float(np.abs(got[:36, :36] - ref2)[2:-2, 2:-2].max()) < 1e-5


def _ellipse_contour(H=41, W=61):
    t = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    c = np.column_stack([(H - 1) / 2 + 10 * np.sin(t), (W - 1) / 2 + 15 * np.cos(t)])
    return {"shape": (H, W), "cs": [c]}


@pytest.mark.parametrize("name,a,b", [("affine_trans_contour_xld", 1.0, 0.0), ("hx_radial_distort_contour", 1.0, 0.0),
                                      ("hx_radial_distort_contour", 0.0, 0.0)])
def test_p8_contour_transforms_keep_a_centred_contour_centred(name, a, b):
    cv = _ellipse_contour()
    out = api.apply(cv, name, a, b, on_error="raise")
    assert len(out["cs"]) == 1
    m = np.asarray(out["cs"][0], float).mean(0)
    assert m[0] == pytest.approx(20.0, abs=1e-6) and m[1] == pytest.approx(30.0, abs=1e-6)


def test_p8_crop_contours_is_symmetric_about_the_image_centre():
    """中心について対称な点の集合を中心の窓で切ると、残る点も中心について対称。"""
    H, W = 41, 61
    yy, xx = np.mgrid[0:H, 0:W]
    pts = np.column_stack([yy.ravel(), xx.ravel()]).astype(float)
    out = api.apply({"shape": (H, W), "cs": [pts]}, "hx_crop_contours", 0.37, 0.41, on_error="raise")
    kept = np.asarray(out["cs"][0], float)
    assert len(kept) > 0
    assert kept.mean(0) == pytest.approx([20.0, 30.0], abs=1e-9)


# --------------------------------------------------------------------------------------------- #
# P10: kirsch_dir / robinson_dir の同点は丸めでなく決まる(小さい番号)。整数の厳密な畳み込みと一致
# --------------------------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["kirsch_dir", "robinson_dir"])
def test_p10_compass_direction_matches_exact_integer_arithmetic_and_ignores_offsets(name):
    import backends_auto as BA
    rng = np.random.default_rng(7)
    q = np.round(ndimage.gaussian_filter(rng.random((40, 48)), 1.5) * 255).astype(np.int64)
    q[15:25, 10:20] = 200                                   # 平らな面と、2 方向が厳密に同点になる斜面
    q[:, 30:] = np.arange(18)[None, :] * 3 + 40
    x = q / 255.0
    if name == "kirsch_dir":
        ks = BA._KIRSCH
    else:
        ks = ([np.rot90(BA._ROBINSON[0], i) for i in range(4)] + [np.rot90(BA._ROBINSON[1], i) for i in range(4)])
    assert len(ks) == 8
    resp = np.stack([ndimage.convolve(q, k.astype(np.int64)) for k in ks])     # 整数で厳密
    ref = np.argmax(resp == resp.max(0), 0) / 7.0
    ref[(resp == 0).all(0)] = 0.0
    y = ap(x, name)
    assert np.array_equal(y, ref)
    for off in (0.1, -0.07, 0.31):
        assert np.array_equal(ap(x + off, name), y)


# --------------------------------------------------------------------------------------------- #
# P11: cv_corner_harris の応答は正方形の 4 隅で中心対称(偶数の窓の半画素の片寄りが無い)
# --------------------------------------------------------------------------------------------- #
def test_p11_cv_corner_harris_peaks_are_symmetric_about_the_square_centre():
    pytest.importorskip("cv2")
    x = np.full((40, 40), 0.2)
    x[10:30, 10:30] = 0.8                                   # 画素 10..29、中心 19.5
    x = ndimage.gaussian_filter(x, 0.7)
    y = ap(x, "cv_corner_harris")
    peaks = []
    for (r0, r1, c0, c1) in [(0, 20, 0, 20), (20, 40, 20, 40), (0, 20, 20, 40), (20, 40, 0, 20)]:
        sub = y[r0:r1, c0:c1]
        i, j = np.unravel_index(np.argmax(sub), sub.shape)
        peaks.append((i + r0, j + c0))
    assert len(peaks) == 4
    (a1, b1), (a2, b2), (a3, b3), (a4, b4) = peaks
    assert ((a1 + a2) / 2, (b1 + b2) / 2) == (19.5, 19.5)
    assert ((a3 + a4) / 2, (b3 + b4) / 2) == (19.5, 19.5)
    # 応答の場そのものも 180 度回転と可換
    assert float(np.abs(ap(np.rot90(x, 2), "cv_corner_harris") - np.rot90(y, 2)).max()) < 1e-5


# --------------------------------------------------------------------------------------------- #
# 疑い(再現できたので直した): zero_crossing と ph_total_variation_flow は像の反転・転置と可換
# --------------------------------------------------------------------------------------------- #
FLIPS = [np.flipud, np.fliplr, np.transpose]


@pytest.mark.parametrize("name", ["zero_crossing", "ph_total_variation_flow"])
@pytest.mark.parametrize("a,b", [(0.5, 0.5), (0.2, 0.9)])
def test_suspect_flip_covariance(name, a, b):
    x = _smooth()
    y = ap(x, name, a, b)
    assert len(FLIPS) == 3
    for fl in FLIPS:
        assert float(np.abs(fl(y) - ap(fl(x).copy(), name, a, b)).max()) < 1e-9, fl.__name__


def test_suspect_zero_crossing_marks_the_pixel_closest_to_the_zero():
    """1 本の縦の段差(列 19|20)の LoG のゼロ交差は、段差を挟んで対称 —— 反転しても同じ列の対に付く。"""
    x = np.full((32, 40), 0.2)
    x[:, 20:] = 0.8
    y = ap(x, "zero_crossing", 0.5, 0.5)
    cols = sorted(set(np.nonzero(y[10] > 0.5)[0].tolist()))
    assert cols, "ゼロ交差がある"
    assert cols == sorted(set((39 - np.nonzero(ap(x[:, ::-1].copy(), "zero_crossing", 0.5, 0.5)[10] > 0.5)[0]).tolist()))

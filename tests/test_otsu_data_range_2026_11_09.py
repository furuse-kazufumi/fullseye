"""otsu と bin_threshold を実データの範囲で揃える(2026-11-09 点検 g4_2d_stats の med 2 件)。

1. otsu は [0,1] に収まる入力だけ [0,1] を 256 ビンに切っていた。値域 0.40〜0.45 の像で分解能が全幅の 1/256 に
   落ち、誤分類 3.59 %(skimage・bin_threshold 3.09 %)。
2. bin_threshold は [0,1] へ clip してから大津をかけた。0..255 の float で前景 0 %(真 44 %)、定数 0.4 の像で
   otsu = 全前景・bin_threshold = 全背景と、同じ大津を名乗る 2 つの op が逆の答えを返した。
"""
import numpy as np
import pytest
from scipy import ndimage

import fullseye as fs
import detect


def A(x, name):
    return np.asarray(fs.apply(x, name, coerce=False), np.float64)


def _scene(seed=4):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:96, 0:96]
    truth = ((yy - 40) ** 2 + (xx - 50) ** 2 < 25 ** 2)
    img = np.where(truth, 0.65, 0.35) + rng.normal(0, 0.08, truth.shape)
    img = ndimage.gaussian_filter(img, 0.7)
    img = (img - img.min()) / np.ptp(img)
    return img, truth


def test_otsu_is_equivariant_to_an_affine_map_inside_unit_range():
    img, _ = _scene()
    base = A(img, "otsu")
    narrow = A(0.40 + 0.05 * img, "otsu")
    assert int((base != narrow).sum()) == 0


def test_bin_threshold_and_otsu_give_the_same_answer():
    img, _ = _scene()
    for x in (img, 0.40 + 0.05 * img, img * 255.0):
        assert int((A(x, "otsu") != A(x, "bin_threshold")).sum()) == 0
        assert int((A(x, "otsu") != A(x, "binary_threshold")).sum()) == 0


def test_float_0_255_is_not_saturated():
    img, truth = _scene()
    fg = A(img * 255.0, "bin_threshold")
    assert abs(fg.mean() - truth.mean()) < 0.05
    assert int((fg != A(img, "bin_threshold")).sum()) == 0


def test_constant_image_same_answer_for_both():
    for c in (0.0, 0.4, 1.0):
        x = np.full((16, 16), c)
        assert A(x, "otsu").mean() == A(x, "bin_threshold").mean() == (1.0 if c > 0 else 0.0)


def test_close_to_skimage_on_unit_range_image():
    filters = pytest.importorskip("skimage.filters")
    img, _ = _scene()
    for x in (img, 0.40 + 0.05 * img):
        sk = x > filters.threshold_otsu(x)
        # 違いは argmax ビンの上端で切るか(Fullseye)中点で切るか(skimage)の 1 ビンの中だけ
        assert int((A(x, "otsu").astype(bool) != sk).sum()) <= 0.005 * x.size


def test_segment_objects_mask_follows_the_core_op():
    img, _ = _scene()
    for x in (img, 0.40 + 0.05 * img):
        assert np.array_equal(detect._otsu_mask(x), A(x, "otsu").astype(bool))


def test_gpu_port_agrees_on_a_narrow_range():
    torch = pytest.importorskip("torch", reason="accel._otsu は torch の経路")
    import accel
    img, _ = _scene()
    x = 0.40 + 0.05 * img
    got = accel._otsu(torch.as_tensor(x[None], dtype=torch.float64), 0.0, 0.0, "cpu")[0].numpy()
    assert int((got.astype(bool) != A(x, "otsu").astype(bool)).sum()) == 0


def _out_of_range_inputs():
    img, _ = _scene()
    return [img * 255.0, img * 2.0 - 0.5, -3.0 + 0.01 * img]


def test_segment_objects_mask_follows_the_core_op_out_of_range():
    """detect._otsu_mask は先に [0,1] へ clip していたので、範囲外で中核と割れた(独立レビュー R4: 7,269 px)。"""
    xs = _out_of_range_inputs()
    assert len(xs) == 3
    for x in xs:
        assert int((detect._otsu_mask(x) != A(x, "otsu").astype(bool)).sum()) == 0


def test_gpu_port_agrees_out_of_range():
    torch = pytest.importorskip("torch", reason="accel._otsu は torch の経路")
    import accel
    xs = _out_of_range_inputs()
    assert len(xs) == 3
    for x in xs:
        got = accel._otsu(torch.as_tensor(x[None], dtype=torch.float64), 0.0, 0.0, "cpu")[0].numpy()
        assert int((got.astype(bool) != A(x, "otsu").astype(bool)).sum()) == 0


@pytest.mark.parametrize("c", [300.0, -2.0, 0.4, 0.0])
def test_constant_image_twins_follow_the_core(c):
    """定数 300 の像で detect は全背景・中核は全前景と割れていた(2 回目の確認)。"""
    x = np.full((16, 16), c)
    core = A(x, "otsu").astype(bool)
    assert np.array_equal(detect._otsu_mask(x), core)
    torch = pytest.importorskip("torch")
    import accel
    got = accel._otsu(torch.as_tensor(x[None], dtype=torch.float64), 0.0, 0.0, "cpu")[0].numpy().astype(bool)
    assert np.array_equal(got, core)


@pytest.mark.parametrize("v", [np.nan, np.inf, -np.inf])
def test_all_nonfinite_is_refused_by_the_twins_like_the_core(v):
    """中核は ValueError なのに、detect と accel は黙って値を返していた(2 回目の確認)。"""
    import ops
    x = np.full((8, 8), v)
    with pytest.raises(ValueError, match="no finite pixel"):
        ops._otsu(x, 0, 0)
    with pytest.raises(ValueError, match="no finite pixel"):
        detect._otsu_mask(x)
    torch = pytest.importorskip("torch")
    import accel
    with pytest.raises(ValueError, match="no finite pixel"):
        accel._otsu(torch.as_tensor(x[None], dtype=torch.float64), 0.0, 0.0, "cpu")

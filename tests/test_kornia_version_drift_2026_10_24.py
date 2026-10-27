"""kornia の版で値が変わらないことを、kornia と独立な参照で確かめる(2026-10-24)。

マージ後レビューの指摘(PR #134 の後):

* ``xkor_hessian`` が kornia 0.8.3 と 0.9.0 で内側でも最大 0.68 ずれた。0.9 で
  ``spatial_gradient(order=2, normalized=True)`` の正規化が変わった(0.8 は各カーネルを
  絶対値和で割るので Ixy だけが 64/36 倍に効き、行列式が Hessian の行列式でなかった)。
  正規化なしの 5x5 Sobel 2 階カーネルを自前で 64 で割る形に固定した —— 2 次・3 次の
  曲面で微分値そのものになり、版に依らない。
* ``xkor_clahe`` が版で最大 0.46 ずれた。0.9 で ``equalize_clahe`` の中身(ヒストグラムの
  bin・余りの配り方・LUT の丸め・タイル補間)が OpenCV に寄せて直された。引数では
  揃えられないので、0.9 未満では理由つきで断る。
* ``xkor_laplacian`` / ``xkor_dog`` / ``xkor_harris`` / ``xkor_gftt`` が 4x4・3x7 の画像で
  「Padding size should be less than…」(鏡映の半径 >= 画像の辺)で fallback に落ちた。

参照はすべて scipy / OpenCV と、この file に手で書いたカーネル(kornia から取らない)。
"""
import re

import numpy as np
import pytest

pytest.importorskip("torch")
kornia = pytest.importorskip("kornia")
ndi = pytest.importorskip("scipy.ndimage")

import backend_safe  # noqa: E402
import ops  # noqa: E402

_KS = (3, 5, 7, 9)  # backends_kornia._k
_VER = tuple(int(x) for x in re.match(r"(\d+)\.(\d+)", kornia.__version__).groups())

#: 5x5 Sobel 2 階微分(Ixx・Ixy)。[1,4,6,4,1] で平滑化し、間隔 2 の 2 階差分 / 中心差分を
#: 取る。64 で割ると 2 次・3 次の曲面で微分値そのものになる。
_SXX = np.outer([1, 4, 6, 4, 1], [1, 0, -2, 0, 1]).astype(np.float64)
_SXY = np.outer([-1, -2, 0, 2, 1], [-1, -2, 0, 2, 1]).astype(np.float64)


def _op(name):
    found = [o for o in ops.REGISTRY if o.name == name]
    if not found:
        pytest.skip(f"{name} が登録されていない(kornia 無し)")
    return found[0]


def _call(name, v, a=0.5, b=0.5):
    """strict で呼ぶ(fallback に落ちたら例外 = 黙った劣化を通さない)。"""
    with backend_safe.strict_mode(True):
        return _op(name).fn(v, a, b)


def _f32(v):
    """op は入力を [0,1] に clip して float32 で計算する —— 参照も同じ入力から始める。"""
    return np.clip(v, 0, 1).astype(np.float32).astype(np.float64)


def _unit(x):
    m = float(np.max(np.abs(x)))
    return x / m if m > 0 else x


_SHAPES = [(32, 40), (16, 16), (9, 9), (4, 4), (3, 7), (1, 5)]


# ------------------------------------------------------------------ hessian
@pytest.mark.parametrize("shape", _SHAPES)
def test_hessian_matches_independent_scipy_determinant(shape):
    v = np.random.default_rng(11).random(shape)
    x = _f32(v)
    dxx = ndi.correlate(x, _SXX, mode="nearest") / 64.0
    dyy = ndi.correlate(x, _SXX.T, mode="nearest") / 64.0
    dxy = ndi.correlate(x, _SXY, mode="nearest") / 64.0
    want = _unit(np.abs(dxx * dyy - dxy ** 2))
    got = _call("xkor_hessian", v)
    assert got.shape == v.shape
    np.testing.assert_allclose(got, want, rtol=0, atol=2e-5)


def test_hessian_is_the_true_determinant_on_a_cubic_surface():
    """f = (x-10)^3/6 + x y + y^2/2 → det H = (x-10)·1 − 1² = x − 11(内側で厳密)。

    0.8 の正規化(Ixy を 36 で割る)だと det = (x−10) − (64/36)² で零点が x ≈ 13.2 にずれる。
    """
    yy, xx = np.mgrid[0:24, 0:24].astype(np.float64)
    f = (xx - 10) ** 3 / 6 + xx * yy + yy ** 2 / 2
    s = 1.0 / 2400.0
    v = 0.5 + s * (f - f.mean())
    assert 0.0 <= v.min() and v.max() <= 1.0
    got = _call("xkor_hessian", v)[2:-2, 2:-2]
    want = np.abs(xx - 11)[2:-2, 2:-2]
    np.testing.assert_allclose(_unit(got), _unit(want), rtol=0, atol=2e-3)
    assert got[:, 11 - 2].max() < 2e-3 * got.max()  # 零点は x = 11 の列


# ------------------------------------------------------------------ laplacian
@pytest.mark.parametrize("a", [0.0, 0.3, 0.6, 1.0])
@pytest.mark.parametrize("shape", _SHAPES)
def test_laplacian_matches_scipy_with_reflect_border(a, shape):
    v = np.random.default_rng(12).random(shape)
    k = _KS[min(3, int(a * 4))]
    ker = np.ones((k, k))
    ker[k // 2, k // 2] = 1 - k * k
    r = k // 2
    want = ndi.correlate(np.pad(_f32(v), r, mode="reflect"), ker, mode="constant")[r:-r, r:-r]
    got = _call("xkor_laplacian", v, a)
    assert got.shape == v.shape
    np.testing.assert_allclose(got, _unit(np.abs(want)), rtol=0, atol=2e-5)


# ------------------------------------------------------------------ dog
@pytest.mark.parametrize("shape", _SHAPES)
def test_dog_matches_scipy_gaussian_difference(shape):
    """DoG = G(σ=1.6, 13x13) − G(σ=1.0, 9x9)、端は鏡映(kornia の gaussian_blur2d の既定)。"""
    v = np.random.default_rng(13).random(shape)
    x = np.pad(_f32(v), 6, mode="reflect")
    g1 = ndi.gaussian_filter(x, 1.0, mode="constant", truncate=4.0)       # 半径 4
    g2 = ndi.gaussian_filter(x, 1.6, mode="constant", truncate=6 / 1.6)   # 半径 6
    want = _unit(np.abs(g2 - g1)[6:-6, 6:-6])
    got = _call("xkor_dog", v)
    assert got.shape == v.shape
    np.testing.assert_allclose(got, want, rtol=0, atol=2e-5)


# ------------------------------------------------------------------ harris / gftt
@pytest.mark.parametrize("name", ["xkor_harris", "xkor_gftt"])
@pytest.mark.parametrize("shape", [(3, 7), (1, 5), (2, 2), (3, 3)])
def test_corner_responses_run_on_images_smaller_than_the_window(name, shape):
    v = np.random.default_rng(14).random(shape)
    got = _call(name, v, 0.5)  # strict: fallback なら例外
    assert got.shape == v.shape and np.isfinite(got).all()


@pytest.mark.parametrize("shape", [(4, 4), (16, 16), (9, 13)])
def test_corner_responses_unchanged_where_kornia_already_worked(shape):
    """小さい画像の経路は「kornia が例外を出す大きさ」だけ —— それ以外の値は 1 ビットも変えない。"""
    import torch
    from backend_safe import signed01

    v = np.random.default_rng(15).random(shape)
    t = torch.as_tensor(_f32(v).astype(np.float32))[None, None]
    want_h = signed01(kornia.feature.harris_response(t, k=0.04 + 0.02 * 0.5).numpy()[0, 0])
    np.testing.assert_array_equal(_call("xkor_harris", v, 0.5), want_h)
    g = np.abs(kornia.feature.gftt_response(t).numpy()[0, 0].astype(np.float64))
    want_g = g / g.max() if g.max() > 1e-5 * v.max() else np.zeros_like(g)
    np.testing.assert_array_equal(_call("xkor_gftt", v, 0.5), want_g)


# ------------------------------------------------------------------ clahe
def test_clahe_refuses_or_matches_opencv():
    """0.9 以上: OpenCV の CLAHE(8x8 タイル)に近い。0.9 未満: 理由つきで断る。"""
    cv2 = pytest.importorskip("cv2")
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[0:64, 0:80]
    imgs = [rng.random((64, 80)), 0.5 + 0.4 * np.sin(xx / 4.0) * np.cos(yy / 5.0),
            0.2 * rng.random((64, 80)) ** 2]
    for v in imgs:
        v8 = np.round(v * 255).astype(np.uint8)
        vq = v8.astype(np.float64) / 255.0
        if _VER < (0, 9):
            with pytest.raises(ValueError, match="0.9"):
                _call("xkor_clahe", vq, 0.5)
            continue
        got = _call("xkor_clahe", vq, 0.5)
        want = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(v8) / 255.0
        d = np.abs(got - want)
        # 実測(kornia 0.9.0, OpenCV 5.0): 平均 0.001〜0.012・最大 0.047。0.8.3 は平均 0.06〜0.17・最大 0.46
        assert d.mean() < 0.02 and d.max() < 0.06, (d.mean(), d.max())


# ------------------------------------------------------------------ golden(全 xkor_* op)
def _golden_image():
    yy, xx = np.mgrid[0:24, 0:28].astype(np.float64)
    rng = np.random.default_rng(2026)
    return np.clip(0.5 + 0.3 * np.sin(xx / 3.0) * np.cos(yy / 4.0)
                   + 0.15 * rng.random((24, 28)), 0, 1)


_GOLDEN_PIX = [(0, 0), (5, 7), (12, 14), (23, 27)]

#: ``_golden_image()`` に (a, b) = (0.6, 0.7) を当てた出力の [平均, 標準偏差, 4 画素の値]。
#: kornia 0.9.0 で取り、0.8.3 でも差が 9e-7 以内(laplacian、float32 の丸め)なのを確かめた
#: (2026-10-24、xkor_clahe だけは 0.8 で断るので 0.9 以上でしか比べない)。CI は最新の
#: kornia を入れるので、**次に kornia が既定や中身を変えた日にここが赤になる** —— 黙って
#: 値が変わる代わりに。xkor_* を足したらここにも足す(下の門が数える)。
_GOLDEN = {
    "xkor_gaussian": [0.5741725, 0.1278215, 0.6476321, 0.6350738, 0.8298413, 0.7172384],
    "xkor_bilateral": [0.5741145, 0.1271015, 0.6482269, 0.6352212, 0.824989, 0.7200639],
    "xkor_median": [0.5258933, 0.1433267, 0.0, 0.6191413, 0.765496, 0.0],
    "xkor_unsharp": [0.5751977, 0.1845397, 0.4062234, 0.6121316, 0.8082247, 0.7395867],
    "xkor_motion_blur": [0.4916549, 0.1472694, 0.0478946, 0.5931579, 0.7348734, 0.0662155],
    "xkor_canny": [0.1324405, 0.338969, 0.0, 0.0, 0.0, 0.0],
    "xkor_clahe": [0.5563346, 0.202556, 0.0823529, 0.5591503, 0.5882353, 0.270098],
    "xkor_laplacian": [0.2700455, 0.1971004, 0.903732, 0.0265648, 0.2429955, 0.0583453],
    "xkor_harris": [0.597622, 0.0934391, 0.3962214, 0.5333877, 0.5338541, 0.4758041],
    "xkor_gftt": [0.2857786, 0.1369102, 0.0884658, 0.1479543, 0.1855468, 0.0909272],
    "xkor_hessian": [0.19787, 0.1825747, 0.0612549, 0.042663, 0.16445, 0.215974],
    "xkor_dog": [0.2937379, 0.2130649, 0.7226238, 0.0918149, 0.6914338, 0.0660189],
}


def test_golden_table_names_every_xkor_op():
    names = {o.name for o in ops.REGISTRY if o.name.startswith("xkor_")}
    if not names:
        pytest.skip("xkor_* が登録されていない")
    assert names == set(_GOLDEN), sorted(names ^ set(_GOLDEN))


@pytest.mark.parametrize("name", sorted(_GOLDEN))
def test_every_xkor_op_matches_the_golden_values(name):
    if name == "xkor_clahe" and _VER < (0, 9):
        pytest.skip("xkor_clahe は kornia 0.9 未満で断る(test_clahe_refuses_or_matches_opencv)")
    r = np.asarray(_call(name, _golden_image(), 0.6, 0.7), np.float64)
    got = [float(r.mean()), float(r.std())] + [float(r[p]) for p in _GOLDEN_PIX]
    np.testing.assert_allclose(got, _GOLDEN[name], rtol=0, atol=5e-6,
                               err_msg="kornia %s で %s の値が変わった" % (kornia.__version__, name))

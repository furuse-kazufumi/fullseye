"""kornia の境界の規約を版に依らず固定する(2026-10-24)。

kornia 0.9.0 で median_blur / motion_blur の境界が 0 埋めから鏡映に変わり、
4x4 の画像に 9x9 の窓で例外(master の CI が赤)、普通の画像でも縁の画素が
黙って変わった。backends_kornia._zero_border で 0 埋めに固定したことを、
kornia と独立な実装(scipy の 0 埋め中央値)と照合して確かめる。
"""
import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("kornia")
ndi = pytest.importorskip("scipy.ndimage")

import ops  # noqa: E402

_KS = (3, 5, 7, 9)  # backends_kornia._k: (3,5,7,9)[min(3, int(a*4))]


def _op(name):
    found = [o for o in ops.REGISTRY if o.name == name]
    if not found:
        pytest.skip(f"{name} が登録されていない(kornia 無し)")
    return found[0]


@pytest.mark.parametrize("a", [0.0, 0.3, 0.6, 1.0])
@pytest.mark.parametrize("shape", [(4, 4), (16, 16), (7, 12)])
def test_median_border_is_zero_padding_like_scipy(a, shape):
    op = _op("xkor_median")
    v = np.random.default_rng(7).random(shape)
    k = _KS[min(3, int(a * 4))]
    want = ndi.median_filter(v.astype(np.float32), size=k, mode="constant",
                             cval=0.0).astype(np.float64)
    got = op.fn(v, a, 0.5)
    assert got.shape == v.shape
    np.testing.assert_allclose(got, want, rtol=0, atol=1e-7)


@pytest.mark.parametrize("a, b", [(0.0, 0.5), (0.3, 0.1), (0.5, 0.5), (1.0, 0.9)])
@pytest.mark.parametrize("shape", [(4, 4), (16, 16), (7, 12)])
def test_motion_blur_border_is_zero_padding_like_scipy(a, b, shape):
    """全画素を scipy の 0 埋め相関と比べる(2026-10-24 のレビュー指摘 8)。

    前の版は一様な 1 の画像の隅 1 画素が 1 未満かしか見ておらず、縁の他の画素や
    内側がずれても通っていた。カーネルは kornia の ``get_motion_kernel2d`` から取り
    (op が使う窓そのもの)、境界と畳み込みは scipy で独立に計算する。
    """
    import kornia.filters as KF

    op = _op("xkor_motion_blur")
    v = np.random.default_rng(8).random(shape)
    ks = 2 * int(2 + a * 6) + 1                     # backends_kornia._motion と同じ写し
    ker = KF.get_motion_kernel2d(ks, float(360 * a), float(2 * b - 1)).numpy()[0]
    x = v.astype(np.float32).astype(np.float64)
    want = np.clip(ndi.correlate(x, ker.astype(np.float64), mode="constant", cval=0.0), 0, 1)
    got = op.fn(v, a, b)
    assert got.shape == v.shape
    # 実測(kornia 0.8.3 / 0.9.0): 最大 1.3e-7(float32 の和の丸め)
    np.testing.assert_allclose(got, want, rtol=0, atol=1e-6)

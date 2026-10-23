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


@pytest.mark.parametrize("a", [0.0, 0.5, 1.0])
@pytest.mark.parametrize("shape", [(4, 4), (16, 16)])
def test_motion_blur_runs_on_tiny_images_and_borders_see_zeros(a, shape):
    op = _op("xkor_motion_blur")
    v = np.ones(shape)
    got = op.fn(v, a, 0.5)
    assert got.shape == v.shape and np.isfinite(got).all()
    # 一様な 1 の画像: 0 埋めなら縁は 1 未満に暗くなり、鏡映なら 1 のまま
    assert got[0, 0] < 1.0 - 1e-3

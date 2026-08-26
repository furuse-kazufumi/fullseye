"""3D GPU 視覚 toolkit テスト: voxel NCC マッチング / pyramid / sub-voxel 重心 / 3D region morphology。

cv2 に 3D matchTemplate は無く、GPU voxel マッチングはツールとして空いている(差別化領域)。
2D NCC(強い GPU 勝ち)× 3D volume op の融合。CT/MRI/depth-stack の対象定位・3D 検査に。

device 非依存(CPU torch でも成立)。torch 不在なら skip。
"""
import numpy as np
import pytest
from scipy import ndimage

import accel_vol as V
import accel_match as M

HAS = V._HAS_TORCH
skip = pytest.mark.skipif(not HAS, reason="torch 不在")


def _template(rad=3, sig=4.0):
    a = np.arange(-rad, rad + 1)
    z, y, x = np.meshgrid(a, a, a, indexing="ij")
    return np.exp(-(x * x + y * y + z * z) / sig)


def _scene(T, size=40, seed=0):
    rad = T.shape[0] // 2
    r = np.random.default_rng(seed)
    base = r.random((size, size, size)) * 0.3
    d = int(r.integers(rad + 2, size - rad - 2))
    h = int(r.integers(rad + 2, size - rad - 2))
    w = int(r.integers(rad + 2, size - rad - 2))
    base[d - rad:d + rad + 1, h - rad:h + rad + 1, w - rad:w + rad + 1] = np.maximum(
        base[d - rad:d + rad + 1, h - rad:h + rad + 1, w - rad:w + rad + 1], T)
    return np.clip(base + r.normal(0, 0.05, base.shape), 0, 1), (d, h, w)


@skip
def test_ncc_3d_localizes_exactly():
    T = _template()
    vols, gts = zip(*[_scene(T, 40, s) for s in range(4)])
    res = M.ncc_locate_3d(list(vols), T, "cpu", subvoxel=False)
    for (sc, d, h, w), (gd, gh, gw) in zip(res, gts):
        assert (int(d), int(h), int(w)) == (gd, gh, gw)
        assert sc > 0.5


@skip
def test_ncc_3d_subvoxel_accuracy():
    T = _template()
    v, gt = _scene(T, 40, 7)
    sc, d, h, w = M.ncc_locate_3d([v], T, "cpu", subvoxel=True)[0]
    assert abs(d - gt[0]) + abs(h - gt[1]) + abs(w - gt[2]) < 0.5   # 連続座標で sub-voxel


@skip
def test_ncc_3d_pyramid_matches_full():
    T = _template(rad=7, sig=25.0)                                  # 15³ テンプレ
    vols, gts = zip(*[_scene(T, 80, s) for s in range(3)])
    pyr = M.ncc_locate_3d_pyramid(list(vols), T, "cpu", levels=2, win=3)
    for (sc, d, h, w), gt in zip(pyr, gts):
        assert abs(d - gt[0]) + abs(h - gt[1]) + abs(w - gt[2]) < 1.5


@skip
def test_ncc_3d_no_template_zeros():
    out = M.ncc_locate_3d([np.zeros((20, 20, 20))], None, "cpu")
    assert np.array_equal(out[0], np.zeros(4))


@skip
@pytest.mark.parametrize("a", [0.2, 0.56])
def test_vol_region_morphology_bit_exact(a):
    rad = 1 + int(a * 3)
    A = np.arange(-rad, rad + 1)
    zz, yy, xx = np.meshgrid(A, A, A, indexing="ij")
    ball = (xx * xx + yy * yy + zz * zz) <= rad * rad
    rng = np.random.default_rng(1)
    vols = [(rng.random((24, 24, 24)) > 0.55).astype(np.float64) for _ in range(3)]
    refs = {
        "vol_erosion_ball_g": lambda v: ndimage.binary_erosion(v > 0.5, ball).astype(float),
        "vol_dilation_ball_g": lambda v: ndimage.binary_dilation(v > 0.5, ball).astype(float),
        "vol_opening_ball_g": lambda v: ndimage.binary_opening(v > 0.5, ball).astype(float),
        "vol_reg_dilate_g": lambda v: ndimage.binary_dilation(v > 0.5, iterations=rad).astype(float),
        "vol_reg_erode_g": lambda v: ndimage.binary_erosion(v > 0.5, iterations=rad).astype(float),
    }
    for name, ref in refs.items():
        got = V.run_batch_vol(name, vols, a, 0.0, "cpu")
        assert all(np.array_equal(np.asarray(g), ref(v)) for v, g in zip(vols, got)), name

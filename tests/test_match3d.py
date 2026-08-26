"""match3d(3D マッチング・マトリクス)テスト。data 構造 × 2D 手法 × 変換。

位相相関(FFT)/ 形状ベース(勾配方向=輪郭マッチング、コントラスト不変)/ splat 変換 /
点群 NCC。GPU 速度は docs/BENCH_VS_OPENCV 系で別途(phase 18-28× / shape 68-89× vs CPU)。
device 非依存。torch 不在なら skip。
"""
import numpy as np
import pytest

import match3d as X

HAS = X._HAS_TORCH
skip = pytest.mark.skipif(not HAS, reason="torch 不在")


@skip
def test_phase_corr_recovers_shift():
    a = np.random.default_rng(0).random((32, 32, 32))
    s = (5, -3, 7)
    b = np.roll(a, s, axis=(0, 1, 2))
    sh = X.match_phase_3d(a, b, "cpu")
    assert tuple(-x for x in sh) == s or sh == s          # 符号規約差は許容


@skip
def test_shape_based_contrast_invariant():
    """勾配方向マッチングは弱コントラスト(0.4×)でも定位する = 強度不変。"""
    z, y, x = np.ogrid[-4:5, -4:5, -4:5]
    T = np.exp(-(x * x + y * y + z * z) / 8.0)
    rng = np.random.default_rng(1)
    scene = rng.random((48, 48, 48)) * 0.3
    d, h, w = 30, 12, 22
    scene[d - 4:d + 5, h - 4:h + 5, w - 4:w + 5] += 0.4 * T
    r = X.match_shape_3d(np.clip(scene, 0, 1), T, "cpu", mc=0.02)
    assert abs(r[1] - d) + abs(r[2] - h) + abs(r[3] - w) < 1.5


@skip
def test_gaussians_to_voxel_peaks_at_means():
    means = np.array([[0.3, 0.5, 0.7]])
    vol = X.gaussians_to_voxel(means, [0.03], [1.0], 32,
                               (np.zeros(3), np.ones(3)), "cpu")
    pk = np.unravel_index(np.argmax(vol), vol.shape)
    exp = tuple(int(m * 31) for m in means[0])
    assert sum(abs(p - e) for p, e in zip(pk, exp)) <= 2


@skip
def test_points_to_voxel_and_mip():
    rng = np.random.default_rng(2)
    pts = rng.random((500, 3))
    vol = X.points_to_voxel(pts, 24, (np.zeros(3), np.ones(3)), "cpu")
    assert vol.shape == (24, 24, 24) and vol.sum() > 0
    mips = X.voxel_to_mips(vol)
    assert len(mips) == 3 and all(m.shape == (24, 24) for m in mips)


@skip
def test_points_ncc_locates_cluster():
    """構造ある点群: 疎な背景 + 既知位置の密クラスタ。model=クラスタ点で定位。"""
    rng = np.random.default_rng(3)
    bg = rng.random((1500, 3))
    c = np.array([0.65, 0.35, 0.55])
    cluster = c + rng.normal(0, 0.03, (400, 3))
    scene = np.vstack([bg, cluster])
    res = X.match_points_ncc(scene, cluster, 32, (np.zeros(3), np.ones(3)), "cpu")
    # 復元位置(voxel)を [0,1] へ戻して真のクラスタ中心と比較
    pos01 = np.array(res[1:]) / 31.0
    assert np.linalg.norm(pos01 - c) < 0.12

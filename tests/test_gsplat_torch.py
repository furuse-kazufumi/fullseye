"""純 torch 3DGS レンダラの回帰(CPU で動く範囲: 幾何・初期化・単一ガウシアン)。

GPU 学習の実証は別途 venv(cu128)で実施済み(test 新規視点 PSNR 26dB)。ここは
数式の正しさを CPU で固定する。"""
from __future__ import annotations
import numpy as np
import pytest

torch = pytest.importorskip("torch")
import gsplat_torch as G  # noqa: E402


def test_identity_quat_is_identity():
    R = G.quat_to_rotmat(torch.tensor([[1.0, 0, 0, 0]]))
    assert torch.allclose(R[0], torch.eye(3), atol=1e-6)


def test_knn_scale_shape():
    pts = np.random.RandomState(0).randn(20, 3).astype(np.float32)
    s = G.knn_scale(pts, k=3)
    assert s.shape == (20, 3) and (s > 0).all()


def test_single_gaussian_renders_at_center():
    """world 原点の赤ガウシアンが、正面カメラで画像中心に描画される(投影の正しさ)。"""
    dev = "cpu"
    gm = G.GaussianModel(np.array([[0., 0, 0]]), np.array([[1., 0, 0]]),
                         np.array([[0.05, 0.05, 0.05]]), device=dev)
    c2w = torch.eye(4); c2w[2, 3] = 2.0                    # (0,0,2) から -Z を見る
    K = torch.tensor([[150., 0, 30], [0, 150., 30], [0, 0, 1]])
    img = G.render(gm, c2w, K, 60, 60).detach().numpy()
    row, col = np.unravel_index(np.argmax(img[:, :, 0] - img[:, :, 1]), img[:, :, 0].shape)
    assert abs(row - 30) <= 1 and abs(col - 30) <= 1        # 中心 ±1px
    assert img[30, 30, 0] > 0.5 and img[30, 30, 1] < 0.3    # 赤い
    assert abs(img[0, 0, 0] - 0.29) < 0.05                  # 隅は背景


def test_psnr_identical_is_inf():
    a = torch.rand(8, 8, 3)
    assert G.psnr(a, a) == float("inf")

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


def test_tiled_matches_dense_single_gaussian():
    """render_tiled は render(密・厳密参照)と一致する(CPU、単一ガウシアン)。"""
    dev = "cpu"
    gm = G.GaussianModel(np.array([[0., 0, 0]]), np.array([[1., 0, 0]]),
                         np.array([[0.05, 0.05, 0.05]]), device=dev)
    c2w = torch.eye(4); c2w[2, 3] = 2.0
    K = torch.tensor([[150., 0, 30], [0, 150., 30], [0, 0, 1]])
    d = G.render(gm, c2w, K, 60, 60)
    t = G.render_tiled(gm, c2w, K, 60, 60, tile=16)
    assert t.shape == (60, 60, 3)
    assert G.psnr(d, t) > 45.0                             # 実質同一(3σ カリング差のみ)


def test_tiled_multi_gaussian_parity():
    """複数ガウシアンでも tiled と dense が高 PSNR で一致(タイル境界の連続性)。"""
    rng = np.random.RandomState(1)
    dev = "cpu"
    N, res = 200, 64
    means = (rng.rand(N, 3) * 1.2 - 0.6).astype(np.float32)
    cols = rng.rand(N, 3).astype(np.float32)
    scales = np.full((N, 3), 0.04, np.float32)
    gm = G.GaussianModel(means, cols, scales, device=dev)
    c2w = torch.eye(4); c2w[2, 3] = 3.0
    K = torch.tensor([[res * 1.2, 0, res / 2], [0, res * 1.2, res / 2], [0, 0, 1.0]])
    d = G.render(gm, c2w, K, res, res)
    t = G.render_tiled(gm, c2w, K, res, res, tile=16)
    assert G.psnr(d, t) > 40.0


def test_tiled_backward_flows():
    """render_tiled で backward が通り、means に有限勾配が乗る(学習可能性)。"""
    dev = "cpu"
    rng = np.random.RandomState(2)
    N, res = 50, 32
    gm = G.GaussianModel((rng.rand(N, 3) - 0.5).astype(np.float32),
                         rng.rand(N, 3).astype(np.float32),
                         np.full((N, 3), 0.05, np.float32), device=dev)
    c2w = torch.eye(4); c2w[2, 3] = 3.0
    K = torch.tensor([[res * 1.2, 0, res / 2], [0, res * 1.2, res / 2], [0, 0, 1.0]])
    img = G.render_tiled(gm, c2w, K, res, res, tile=16)
    ((img - 0.5) ** 2).mean().backward()
    g = gm.means.grad
    assert g is not None and torch.isfinite(g).all()

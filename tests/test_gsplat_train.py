"""3DGS トレーナ部品の CPU 回帰(SSIM・densify/prune)。GPU 学習実証は別途 venv。"""
from __future__ import annotations
import numpy as np
import pytest

torch = pytest.importorskip("torch")
import gsplat_train as T  # noqa: E402
import gsplat_torch as G  # noqa: E402


def test_ssim_identical_is_one():
    a = torch.rand(32, 32, 3)
    assert abs(T.ssim(a, a).item() - 1.0) < 1e-3


def test_ssim_symmetric():
    a, b = torch.rand(24, 24, 3), torch.rand(24, 24, 3)
    assert abs(T.ssim(a, b).item() - T.ssim(b, a).item()) < 1e-4


def test_densify_prunes_low_opacity_and_big():
    """不透明度ゼロ/巨大スケールのガウシアンが除去される。"""
    n = 50
    means = np.random.RandomState(0).randn(n, 3).astype(np.float32)
    gm = G.GaussianModel(means, np.ones((n, 3)) * 0.5, np.ones((n, 3)) * 0.02, device="cpu")
    with torch.no_grad():
        gm.raw_opacity[:10] = -20.0        # opacity≈0 → prune
        gm.log_scales[10:15] = np.log(5.0)  # 巨大 → prune
    ga = torch.zeros(n)
    gm2, st = T.densify_and_prune(gm, ga, grad_thresh=None, max_scale=0.3, device="cpu")
    assert st["pruned"] == 15 and gm2.n == n - 15


def test_densify_clones_high_grad():
    n = 20
    gm = G.GaussianModel(np.random.RandomState(1).randn(n, 3).astype(np.float32),
                         np.ones((n, 3)) * 0.5, np.ones((n, 3)) * 0.02, device="cpu")
    ga = torch.zeros(n); ga[:5] = 100.0     # 上位を clone
    gm2, st = T.densify_and_prune(gm, ga, grad_thresh=torch.tensor(50.0), device="cpu")
    assert st["cloned"] == 5 and gm2.n == n + 5

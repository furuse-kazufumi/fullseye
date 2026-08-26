"""metrics3d — 評価メトリクスの ground-truth 検証(進化 fitness 土台)。"""
import numpy as np
import pytest
pytest.importorskip("scipy")
import metrics3d as M


def _cloud(seed=0, n=800):
    rng = np.random.default_rng(seed)
    return rng.uniform(-5, 5, (n, 3))


def test_identical_clouds_perfect():
    """同一点群 → chamfer/Hausdorff=0、fscore=1、IoU=1、法線一致=1。"""
    a = _cloud(0)
    assert M.chamfer_distance(a, a) == 0.0
    assert M.hausdorff_distance(a, a) == 0.0
    f, p, r = M.fscore(a, a, tau=0.1)
    assert f == 1.0 and p == 1.0 and r == 1.0
    n = np.tile([0.0, 0.0, 1.0], (len(a), 1))
    assert abs(M.normal_consistency(a, n, a, n) - 1.0) < 1e-9


def test_rmse_known_offset():
    """index 対応の RMSE が既知オフセットのノルムに一致。"""
    a = _cloud(1)
    t = np.array([0.3, -0.4, 1.2])  # |t| = 1.3
    b = a + t
    assert abs(M.rmse_correspondence(a, b) - np.linalg.norm(t)) < 1e-9


def test_chamfer_monotonic_in_noise():
    """ノイズ増加で chamfer 距離が単調増加。"""
    a = _cloud(2)
    rng = np.random.default_rng(3)
    d0 = M.chamfer_distance(a, a + 0.05 * rng.standard_normal(a.shape))
    d1 = M.chamfer_distance(a, a + 0.20 * rng.standard_normal(a.shape))
    assert 0 < d0 < d1


def test_fscore_decreases_with_noise():
    """ノイズ増加で F-score 低下。"""
    a = _cloud(4)
    rng = np.random.default_rng(5)
    f_lo = M.fscore(a, a + 0.02 * rng.standard_normal(a.shape), tau=0.1)[0]
    f_hi = M.fscore(a, a + 0.30 * rng.standard_normal(a.shape), tau=0.1)[0]
    assert f_lo > f_hi


def test_pose_error_known():
    """既知回転+並進で pose_error が正しい角度/距離を返す。"""
    th = np.radians(30.0)
    Rz = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1.0]])
    rot, tr = M.pose_error(np.eye(3), np.zeros(3), Rz, np.array([1.0, 0, 0]))
    assert abs(rot - 30.0) < 1e-6 and abs(tr - 1.0) < 1e-9
    rot0, tr0 = M.pose_error(Rz, np.ones(3), Rz, np.ones(3))
    assert rot0 < 1e-6 and tr0 < 1e-9


def test_voxel_iou_dice():
    """半分重なる占有 → IoU/Dice が既知値。"""
    a = np.zeros((10, 10, 10)); a[:5] = 1.0
    b = np.zeros((10, 10, 10)); b[3:8] = 1.0
    # |A|=500,|B|=500, inter=2 slabs(3,4)=200, union=800 → IoU 0.25, Dice 0.4
    assert abs(M.voxel_iou(a, b) - 0.25) < 1e-9
    assert abs(M.voxel_dice(a, b) - 0.4) < 1e-9
    assert M.voxel_iou(a, a) == 1.0


def test_accuracy_completeness_subset():
    """b が a の部分集合 → completeness<1 だが accuracy(部分集合→全体)=1。"""
    a = _cloud(6, n=1000)
    b = a[:400]  # a の部分
    # b の各点は a に厳密に存在 → accuracy(b,a)=1
    assert M.accuracy(b, a, tau=1e-6) == 1.0
    # a の点で b の近くにあるのは一部 → completeness(a,b)<1
    assert M.completeness(a, b, tau=1e-6) < 1.0

"""curve3d — 空間曲線の微分幾何量を螺旋の解析値で ground-truth 検証。"""
import numpy as np
import pytest
import curve3d as C


def _helix(a=2.0, b=1.0, turns=4, n=600):
    t = np.linspace(0, turns * 2 * np.pi, n)
    return np.stack([a * np.cos(t), a * np.sin(t), b * t], axis=1), t


def test_curvature_torsion_helix():
    """螺旋の κ=a/(a²+b²), τ=b/(a²+b²) を数値微分で回復(内部で解析値一致)。"""
    a, b = 2.0, 1.0
    curve, _ = _helix(a, b)
    kappa, tau = C.curvature_torsion(curve)
    k_gt = a / (a ** 2 + b ** 2)
    t_gt = b / (a ** 2 + b ** 2)
    ki = kappa[5:-5]; ti = tau[5:-5]
    assert abs(ki.mean() - k_gt) / k_gt < 0.02, f"kappa {ki.mean():.4f} vs {k_gt:.4f}"
    assert abs(ti.mean() - t_gt) / t_gt < 0.02, f"tau {ti.mean():.4f} vs {t_gt:.4f}"


def test_arc_length_helix():
    """螺旋の全長 = turns*2π*sqrt(a²+b²) と一致。"""
    a, b, turns = 2.0, 1.0, 4
    curve, _ = _helix(a, b, turns)
    _, total = C.arc_length(curve)
    gt = turns * 2 * np.pi * np.sqrt(a ** 2 + b ** 2)
    assert abs(total - gt) / gt < 1e-3


def test_frenet_orthonormal():
    """Frenet 標構 T,N,B が正規直交(内部点)。"""
    curve, _ = _helix()
    T, N, B = C.frenet_frame(curve)
    i = slice(5, -5)
    assert np.allclose(np.linalg.norm(T[i], axis=1), 1.0, atol=1e-6)
    assert np.abs(np.sum(T[i] * N[i], axis=1)).max() < 1e-6
    assert np.allclose(np.cross(T[i], N[i]), B[i], atol=1e-6)


def test_straight_line_zero_curvature():
    """直線 → 曲率 ~0。"""
    t = np.linspace(0, 10, 100)
    line = np.stack([t, 2 * t, -t], axis=1)
    kappa, _ = C.curvature_torsion(line)
    assert np.abs(kappa[3:-3]).max() < 1e-6


def test_planar_circle_zero_torsion():
    """平面円 → 捩率 ~0、曲率 = 1/R。"""
    R = 3.0
    t = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    circle = np.stack([R * np.cos(t), R * np.sin(t), np.zeros_like(t)], axis=1)
    kappa, tau = C.curvature_torsion(circle)
    assert abs(kappa[5:-5].mean() - 1.0 / R) / (1.0 / R) < 0.02
    assert np.abs(tau[5:-5]).max() < 1e-3


def test_resample_uniform_spacing():
    """弧長等間隔リサンプル → 区間長がほぼ一定。"""
    curve, _ = _helix()
    rs = C.resample_uniform(curve, 200)
    seg = np.linalg.norm(np.diff(rs, axis=0), axis=1)
    assert seg.std() / seg.mean() < 0.02


def test_fit_spline_smooths_noise():
    """ノイズ螺旋をスプライン平滑 → 元螺旋への最近傍残差が生ノイズより小。"""
    pytest.importorskip("scipy")
    clean, _ = _helix(n=300)
    rng = np.random.default_rng(0)
    noisy = clean + 0.1 * rng.standard_normal(clean.shape)
    smoothed = C.fit_spline_curve(noisy, smooth=len(clean) * 0.05, n=300)
    from scipy.spatial import cKDTree
    d_noisy = cKDTree(clean).query(noisy)[0].mean()
    d_smooth = cKDTree(clean).query(smoothed)[0].mean()
    assert d_smooth < d_noisy

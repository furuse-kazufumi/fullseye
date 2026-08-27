"""curve3d — 空間曲線の微分幾何量を螺旋の解析値で ground-truth 検証。"""
import numpy as np
import pytest
import curve3d as C


def _helix(a=2.0, b=1.0, turns=4, n=600, scale=1.0):
    t = np.linspace(0, turns * 2 * np.pi, n)
    c = np.stack([a * np.cos(t), a * np.sin(t), b * t], axis=1) * scale
    return c, t


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


def test_curvature_torsion_scale_invariance():
    """一様スケール s に対し κ→κ/s, τ→τ/s と正しくスケールする(相対 epsilon)。

    絶対 epsilon だと cross_norm²(~s⁴)を小スケールで支配し τ が全滅する(旧挙動 FAIL)。
    小座標スケールでも解析値 κ=a/(a²+b²)/s, τ=b/(a²+b²)/s を回復すること。
    """
    a, b = 2.0, 1.0
    k_gt = a / (a ** 2 + b ** 2)
    t_gt = b / (a ** 2 + b ** 2)
    for s in (1.0, 1e-1, 1e-2, 1e-3):
        curve, _ = _helix(a, b, scale=s)
        kappa, tau = C.curvature_torsion(curve)
        ki = kappa[5:-5].mean(); ti = tau[5:-5].mean()
        assert abs(ki - k_gt / s) / (k_gt / s) < 0.02, f"scale={s} kappa {ki:.5g} vs {k_gt/s:.5g}"
        assert abs(ti - t_gt / s) / (t_gt / s) < 0.02, f"scale={s} tau {ti:.5g} vs {t_gt/s:.5g}"


def test_curvature_torsion_degenerate_raises():
    """全点が一致(‖r'‖=0)は fail-closed で ValueError(静かに誤値を返さない)。"""
    degenerate = np.zeros((50, 3))
    with pytest.raises(ValueError):
        C.curvature_torsion(degenerate)


def test_total_curvature_scale_invariance():
    """全曲率 ∫κ ds は座標の一様スケールに不変(κ→κ/s, ds→s·ds で相殺)。

    旧挙動: 絶対 epsilon が κ を小スケールで潰し ∫κ ds が半減以下に崩壊(FAIL)。
    螺旋の解析全曲率 = κ·L = a/(a²+b²) · turns·2π·√(a²+b²) をスケール不変に回復。
    """
    a, b, turns = 2.0, 1.0, 4
    gt = (a / (a ** 2 + b ** 2)) * (turns * 2 * np.pi * np.sqrt(a ** 2 + b ** 2))
    vals = []
    for s in (1.0, 1e-2, 1e-3):
        curve, _ = _helix(a, b, turns, scale=s)
        vals.append(C.total_curvature(curve))
    for s, v in zip((1.0, 1e-2, 1e-3), vals):
        assert abs(v - gt) / gt < 0.02, f"scale={s} total_curvature {v:.5g} vs GT {gt:.5g}"
    # 相互一致(スケール間の相対差)も厳しく確認。
    assert (max(vals) - min(vals)) / vals[0] < 1e-3, f"scale-variance across scales: {vals}"


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
    assert np.allclose(np.linalg.norm(N[i], axis=1), 1.0, atol=1e-6)
    assert np.allclose(np.linalg.norm(B[i], axis=1), 1.0, atol=1e-6)
    assert np.abs(np.sum(T[i] * N[i], axis=1)).max() < 1e-6
    assert np.abs(np.sum(T[i] * B[i], axis=1)).max() < 1e-6
    assert np.abs(np.sum(N[i] * B[i], axis=1)).max() < 1e-6


def test_frenet_matches_analytic_helix():
    """Frenet 標構を螺旋の**解析的 Frenet 標構**と数値一致で検証(独立 GT)。

    r(t)=(a cos t, a sin t, b t) の解析標構:
      T=(-a sin t, a cos t, b)/√(a²+b²)、N=(-cos t, -sin t, 0)、
      B=(b sin t, -b cos t, a)/√(a²+b²)。
    B=cross(T,N) という定義から従う恒真式ではなく、既知 GT との一致を要求する
    (誤った B は cross(T,N)==B を通しても、この GT 検証で必ず落ちる)。
    """
    a, b = 2.0, 1.0
    curve, t = _helix(a, b)
    T, N, B = C.frenet_frame(curve)
    den = np.sqrt(a ** 2 + b ** 2)
    T_gt = np.stack([-a * np.sin(t), a * np.cos(t), b * np.ones_like(t)], axis=1) / den
    N_gt = np.stack([-np.cos(t), -np.sin(t), np.zeros_like(t)], axis=1)
    B_gt = np.stack([b * np.sin(t), -b * np.cos(t), a * np.ones_like(t)], axis=1) / den
    i = slice(5, -5)
    assert np.abs(T[i] - T_gt[i]).max() < 1e-3, f"T max err {np.abs(T[i]-T_gt[i]).max():.2e}"
    assert np.abs(N[i] - N_gt[i]).max() < 1e-3, f"N max err {np.abs(N[i]-N_gt[i]).max():.2e}"
    assert np.abs(B[i] - B_gt[i]).max() < 1e-3, f"B max err {np.abs(B[i]-B_gt[i]).max():.2e}"


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

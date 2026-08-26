"""curve3d — 空間曲線の計測(Frenet 標構・曲率・捩率・弧長・スプライン平滑)。

match3d.fit_line_3d / fit_circle_3d は直線・円だが、ここは**一般の 3D 曲線**(シーム・エッジ・
軌跡)の微分幾何量を出す。曲率 κ と捩率 τ は **再パラメータ化不変**(κ=|r'×r''|/|r'|³,
τ=(r'×r'')·r'''/|r'×r''|²)なので、順序付き点列に対し index パラメータの数値微分で厳密に計算できる。
螺旋 r=(a cosθ, a sinθ, bθ) の解析値 κ=a/(a²+b²)・τ=b/(a²+b²) で GT 検証。

用途: エッジ/シームの曲がり計測、軌跡解析、把持経路の曲率制約(Physical AI)。
"""
import numpy as np


def _d(curve):
    """順序付き曲線 (N,3) の 1〜3 階数値微分(index パラメータ)。→ (r1, r2, r3)。"""
    c = np.asarray(curve, float)
    r1 = np.gradient(c, axis=0)
    r2 = np.gradient(r1, axis=0)
    r3 = np.gradient(r2, axis=0)
    return r1, r2, r3


def arc_length(curve):
    """曲線の累積弧長と全長。→ (cumulative (N,), total float)。"""
    c = np.asarray(curve, float)
    seg = np.linalg.norm(np.diff(c, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    return cum, float(cum[-1])


def frenet_frame(curve):
    """Frenet 標構(接線 T, 主法線 N, 陪法線 B)を各点で。→ (T, N, B) 各 (Npts,3) 単位ベクトル。"""
    r1, r2, _ = _d(curve)
    T = r1 / (np.linalg.norm(r1, axis=1, keepdims=True) + 1e-12)
    # 主法線 = 接線変化方向(r2 の T 直交成分)
    proj = np.sum(r2 * T, axis=1, keepdims=True) * T
    Nn = r2 - proj
    N = Nn / (np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-12)
    B = np.cross(T, N)
    return T, N, B


def curvature_torsion(curve):
    """各点の曲率 κ と捩率 τ(再パラメータ化不変な閉形式)。→ (kappa (N,), tau (N,))。"""
    r1, r2, r3 = _d(curve)
    cross = np.cross(r1, r2)
    cross_norm = np.linalg.norm(cross, axis=1)
    r1_norm = np.linalg.norm(r1, axis=1)
    kappa = cross_norm / (r1_norm ** 3 + 1e-12)
    triple = np.sum(cross * r3, axis=1)
    tau = triple / (cross_norm ** 2 + 1e-12)
    return kappa, tau


def total_curvature(curve):
    """全曲率 ∫κ ds(曲線の総曲がり量)。→ scalar。"""
    kappa, _ = curvature_torsion(curve)
    cum, _ = arc_length(curve)
    ds = np.gradient(cum)
    return float(np.sum(kappa * ds))


def resample_uniform(curve, n):
    """弧長で等間隔に n 点へ再サンプル(線形補間)。→ (n,3)。"""
    c = np.asarray(curve, float)
    cum, total = arc_length(c)
    if total < 1e-12:
        return np.repeat(c[:1], n, axis=0)
    targets = np.linspace(0.0, total, n)
    out = np.empty((n, 3))
    for j in range(3):
        out[:, j] = np.interp(targets, cum, c[:, j])
    return out


def fit_spline_curve(points, smooth=0.0, k=3, n=None):
    """順序付き 3D 点列を B スプラインで平滑し再サンプル。→ (M,3)。ノイズのある軌跡/エッジの平滑化。

    scipy.interpolate.splprep/splev。smooth=0 は補間、>0 で平滑。n=出力点数(既定=入力数)。
    """
    from scipy.interpolate import splprep, splev
    c = np.asarray(points, float)
    if len(c) <= k:
        raise ValueError("点数がスプライン次数 k より多く必要")
    n = len(c) if n is None else n
    tck, _ = splprep([c[:, 0], c[:, 1], c[:, 2]], s=smooth, k=k)
    u = np.linspace(0.0, 1.0, n)
    x, y, z = splev(u, tck)
    return np.stack([x, y, z], axis=1)

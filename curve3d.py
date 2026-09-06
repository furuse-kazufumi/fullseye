# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
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
    """曲線の累積弧長と全長。→ (cumulative (N,), total float)。

    順序付き点列 ``curve`` (N,3) を index 順に折れ線とみなし、隣接点間のユークリッド距離
    を累積する。``cumulative[0]=0``、``cumulative[i]`` = 先頭から i 番目までの折れ線長、
    ``total = cumulative[-1]``。単位は座標と同じ。

    - 入力は ``float`` に変換されるだけで形状検証は無い(列数が 3 以外でも計算は通る)。
    - N=1 では ``cumulative=[0.0]``・``total=0.0``。閉曲線でも終点→始点の区間は数えない
      (閉じたい場合は先頭点を末尾に複製してから渡す)。
    - 重複点(距離 0 の区間)はそのまま 0 として累積されるので ``cumulative`` は単調非減少
      だが狭義増加ではない。

    ``resample_uniform`` はこの累積弧長をパラメータに線形補間する。曲率の弧長積分など
    ``curvature_torsion`` と組み合わせるときの ds はこの差分から取る。
    """
    c = np.asarray(curve, float)
    seg = np.linalg.norm(np.diff(c, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    return cum, float(cum[-1])


def frenet_frame(curve):
    """Frenet 標構(接線 T, 主法線 N, 陪法線 B)を各点で。→ (T, N, B) 各 (Npts,3) 単位ベクトル。

    順序付き点列 (N,3) を index パラメータで ``np.gradient``(内部は中心差分、両端は
    片側差分)して r', r'' を取り、
    - T = r' / ‖r'‖
    - N = (r'' − (r''·T) T) / ‖…‖(r'' の T 直交成分 = 曲率中心へ向く向き)
    - B = T × N
    を各点で計算する。r'' の T 直交成分の向きは再パラメータ化に不変なので、点間隔が
    滑らかに変わる限り index パラメータで正しい向きが出る。

    - 分母には絶対値 1e-12 を足すだけで、正規化しきれない箇所は単位長にならない。直線区間
      (r'' ∥ T または 0)では N・B がほぼゼロベクトルになり、変曲点の前後で N の向きが
      反転する。「単位ベクトル」の保証はそこでは成り立たない。
    - N<2 の点列は ``np.gradient`` が ``ValueError`` を出す。形状検証はそれ以外に無い。
    - 両端 2 点は片側差分なので精度が落ちる。等間隔化(``resample_uniform``)や平滑
      (``fit_spline_curve``)を先に掛けると安定する。

    曲率・捩率の数値そのものは ``curvature_torsion``、弧長は ``arc_length``。
    """
    r1, r2, _ = _d(curve)
    T = r1 / (np.linalg.norm(r1, axis=1, keepdims=True) + 1e-12)
    # 主法線 = 接線変化方向(r2 の T 直交成分)
    proj = np.sum(r2 * T, axis=1, keepdims=True) * T
    Nn = r2 - proj
    N = Nn / (np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-12)
    B = np.cross(T, N)
    return T, N, B


def curvature_torsion(curve):
    """各点の曲率 κ と捩率 τ(再パラメータ化不変な閉形式)。→ (kappa (N,), tau (N,))。

    座標の一様スケール s に対し κ→κ/s, τ→τ/s と正しくスケールする。0 割り防止の epsilon は
    **相対化**する: 絶対 1e-12 は cross_norm²(~s⁴)・r1_norm³(~s³)を小座標スケールで支配し、
    κ/τ を破壊するため、代表スケール L=median‖r'‖(座標スケール s に線形)で各分母と同次元に
    正規化した相対 eps を使う。これは曲線を L で正規化してから計算し 1/L で戻すのと厳密に等価。

    計算は順序付き点列 (N,3) を index パラメータで ``np.gradient`` 3 回(中心差分、両端は
    片側差分)した r', r'', r''' から
    - κ = ‖r'×r''‖ / ‖r'‖³
    - τ = (r'×r'')·r''' / ‖r'×r''‖²
    で求める。単位は κ・τ とも 1/座標単位。τ の符号は右手系の螺旋
    (a cosθ, a sinθ, bθ), b>0 で正。直線区間(‖r'×r''‖≈0)では κ≈0、τ は分母が eps だけに
    なるため値は信頼できない。

    - ``ValueError``: 全点が重なり median‖r'‖ が 0 または非有限のとき。
    - 点間隔が急に変わる箇所は数値微分が乱れるので、先に ``resample_uniform`` で等間隔化
      するか ``fit_spline_curve`` で平滑化してから渡す。両端 2 点は片側差分で精度が落ちる。
    - N<2 は ``np.gradient`` が ``ValueError``。形状 (N,3) の検証はしていない。

    標構(T,N,B)が要るなら ``frenet_frame``、弧長 ds は ``arc_length`` から取る。
    """
    r1, r2, r3 = _d(curve)
    cross = np.cross(r1, r2)
    cross_norm = np.linalg.norm(cross, axis=1)
    r1_norm = np.linalg.norm(r1, axis=1)
    # 代表スケール L(典型 ‖r'‖, index param)。座標スケール s に線形に伴走する。
    L = float(np.median(r1_norm))
    if not np.isfinite(L) or L <= 0.0:
        raise ValueError("degenerate curve: all points coincide/overlap so ||r'||=0, cannot compute kappa/tau")
    eps_k = 1e-12 * L ** 3   # r1_norm³ と同次元(~s³)
    eps_t = 1e-12 * L ** 4   # cross_norm² と同次元(~s⁴)
    kappa = cross_norm / (r1_norm ** 3 + eps_k)
    triple = np.sum(cross * r3, axis=1)
    tau = triple / (cross_norm ** 2 + eps_t)
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
        raise ValueError("number of points must exceed spline degree k")
    n = len(c) if n is None else n
    tck, _ = splprep([c[:, 0], c[:, 1], c[:, 2]], s=smooth, k=k)
    u = np.linspace(0.0, 1.0, n)
    x, y, z = splev(u, tck)
    return np.stack([x, y, z], axis=1)

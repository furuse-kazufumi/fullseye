# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""スーパー2次曲面フィット(把持・物体モデリング用の陰関数体積プリミティブ)。

スーパー2次曲面(superquadric / superellipsoid)は 5 個の形状パラメータ
(半径 ``a=(a1,a2,a3)`` + 形状指数 ``eps=(eps1,eps2)``)だけで球・箱・円柱・
八面体・紡錘形までを連続的に表現できる陰関数プリミティブで、Physical AI の
把持計画では「未知物体を 1 個の握れる体積」として当てはめるのに使う
(Solina & Bajcsy 1990 / Gross & Boult)。RANSAC の平面・球・円柱よりも
表現力が高く(角の丸みや扁平を 2 パラメータで連続変形)、点群 1 つに対して
姿勢付きの解析的な内外関数 ``F`` を与えるので、把持点・接触法線・体積を
そのまま導出できる。

内外関数(inside-outside function):

    F(X) = ( |x/a1|^(2/eps2) + |y/a2|^(2/eps2) )^(eps2/eps1) + |z/a3|^(2/eps1)

表面は ``F = 1``、内部は ``F < 1``、外部は ``F > 1``。姿勢 ``(R, t)`` は
world→body を ``X_body = R.T @ (X - t)`` で与える(``R`` の列 = body 軸の
world 表現)。

フィットは Solina-Bajcsy の体積補正付き誤差(Gross-Boult 半径距離近似)

    E = mean( ( sqrt(a1 a2 a3) * (F^eps1 - 1) )^2 )

を ``scipy.optimize.least_squares``(11 パラメータ = a3 + eps2 + rotvec3 + t3)で
最小化する。初期姿勢は慣性テンソル(= 共分散)の固有ベクトル、初期半径は
主軸方向の bounding box 半分、初期形状指数は ``eps=(1,1)``(楕円体)。

近似の限界(honest):
  * eps を小さくした箱状の表面パラメトリックサンプリングは角付近に密・平面に
    疎という既知の非一様性があり、フィットの重み付けを偏らせる。
  * 誤差 ``E`` は真の点-表面ユークリッド距離そのものではなく Gross-Boult の
    半径距離近似(表面近傍で 1 次まで一致)。外れ値には無防備なので、必要なら
    ransac_fit で inlier を選別してから渡す。
  * least_squares は局所最適器。初期姿勢が主軸で決まるため近球状(主軸が縮退)
    の物体では回転が不定になりうる。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "inside_outside",
    "sample_surface",
    "superquadric_residual",
    "fit_superquadric",
]

# ``|.|`` の指数評価で 0 割・overflow を避けるためのクリップ。表面近傍
# (F~1)には全く影響しない大きさに取り、F が発散する退化パラメータでのみ効く。
_EPS = 1e-12
_F_CLIP = 1e12


def _pts(points) -> np.ndarray:
    """(N,3) float64 へ正規化(検証つき)。"""
    P = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    return P


def _to_body(P: np.ndarray, R, t) -> np.ndarray:
    """world 点群を body 座標へ: X_body = R.T @ (X - t)。行ベクトル束では (P-t) @ R。"""
    if t is not None:
        P = P - np.asarray(t, dtype=np.float64).reshape(3)
    if R is not None:
        # (R.T @ v) を行ベクトル束で表すと v_row @ R(= (R.T v)^T)。
        P = P @ np.asarray(R, dtype=np.float64).reshape(3, 3)
    return P


def _signed_pow(base: np.ndarray, exp: float) -> np.ndarray:
    """符号付きべき: sign(base) * |base|^exp(cos/sin が負でも符号を保持)。"""
    return np.sign(base) * (np.abs(base) ** exp)


def inside_outside(points, a, eps, R=None, t=None) -> np.ndarray:
    """スーパー2次曲面の内外関数 F(表面=1, 内部<1, 外部>1)。

    ``F(X) = (|x/a1|^(2/eps2) + |y/a2|^(2/eps2))^(eps2/eps1) + |z/a3|^(2/eps1)``。
    ``R, t`` で姿勢(``X_body = R.T @ (X - t)``)。

    Parameters
    ----------
    points : array_like (N,3)
    a : (a1,a2,a3) 半径(すべて正)
    eps : (eps1,eps2) 形状指数(> 0)
    R : (3,3) 回転(列 = body 軸の world 表現)、既定 = 単位
    t : (3,) 平行移動(body 中心の world 位置)、既定 = 原点

    Returns
    -------
    np.ndarray, shape (N,)
    """
    P = _pts(points)
    a1, a2, a3 = (float(v) for v in a)
    eps1, eps2 = (float(v) for v in eps)
    B = _to_body(P, R, t)
    x = B[:, 0] / a1
    y = B[:, 1] / a2
    z = B[:, 2] / a3
    inner = np.abs(x) ** (2.0 / eps2) + np.abs(y) ** (2.0 / eps2)
    term = inner ** (eps2 / eps1) + np.abs(z) ** (2.0 / eps1)
    return term


def sample_surface(a, eps, n_u: int = 40, n_v: int = 40, R=None, t=None) -> np.ndarray:
    """スーパー2次曲面の表面点を (eta, omega) パラメトリックにサンプリング。

    ``x = a1 * sgn|cos eta|^eps1 * sgn|cos omega|^eps2`` などの符号付きべきで
    全 8 象限を張る(eta in [-pi/2, pi/2], omega in [-pi, pi])。生成点は
    厳密に ``F = 1`` を満たす(cos^2+sin^2=1 が指数を打ち消すため)。

    Parameters
    ----------
    a, eps : inside_outside と同じ
    n_u : omega(経度)方向サンプル数
    n_v : eta(緯度)方向サンプル数
    R, t : 姿勢(body→world: X_world = R @ X_body + t)

    Returns
    -------
    np.ndarray, shape (n_u*n_v, 3)
    """
    a1, a2, a3 = (float(v) for v in a)
    eps1, eps2 = (float(v) for v in eps)
    eta = np.linspace(-np.pi / 2.0, np.pi / 2.0, int(n_v))
    omega = np.linspace(-np.pi, np.pi, int(n_u))
    E, O = np.meshgrid(eta, omega)      # (n_u, n_v)
    E = E.ravel()
    O = O.ravel()
    ce = _signed_pow(np.cos(E), eps1)
    se = _signed_pow(np.sin(E), eps1)
    co = _signed_pow(np.cos(O), eps2)
    so = _signed_pow(np.sin(O), eps2)
    x = a1 * ce * co
    y = a2 * ce * so
    z = a3 * se
    body = np.column_stack([x, y, z])
    if R is not None:
        body = body @ np.asarray(R, dtype=np.float64).reshape(3, 3).T
    if t is not None:
        body = body + np.asarray(t, dtype=np.float64).reshape(3)
    return body


def _residual_vector(P: np.ndarray, a, eps, R, t) -> np.ndarray:
    """least_squares 用の点毎残差 sqrt(a1 a2 a3) * (F^eps1 - 1)。"""
    a1, a2, a3 = (float(v) for v in a)
    eps1 = float(eps[0])
    F = inside_outside(P, a, eps, R, t)
    F = np.clip(F, 0.0, _F_CLIP)
    vol = np.sqrt(max(a1 * a2 * a3, _EPS))
    return vol * (F ** eps1 - 1.0)


def superquadric_residual(points, a, eps, R, t) -> float:
    """Gross-Boult 体積補正残差 mean( (sqrt(a1 a2 a3)(F^eps1 - 1))^2 )。"""
    P = _pts(points)
    r = _residual_vector(P, a, eps, R, t)
    return float(np.mean(r ** 2))


def _principal_frame(P: np.ndarray):
    """慣性テンソル(= 共分散)固有ベクトルから初期姿勢と主軸 bbox 半径を得る。

    Returns (t0, R0, a0):
      t0 = 重心、R0 = 主軸(固有値降順)を列に持つ proper rotation、
      a0 = 主軸方向の bounding box 半分。
    """
    t0 = P.mean(axis=0)
    C = P - t0
    # 慣性主軸 = 共分散行列の固有ベクトル(inertia = tr(cov)I - cov で固有ベクトル同一)。
    cov = np.cov(C.T) if len(P) > 1 else np.eye(3)
    evals, evecs = np.linalg.eigh(cov)          # 昇順
    order = np.argsort(evals)[::-1]             # 降順(最大分散が軸0)
    R0 = evecs[:, order]
    if np.linalg.det(R0) < 0:                    # proper rotation を保証
        R0[:, 2] = -R0[:, 2]
    proj = C @ R0                                # 主軸フレームへ射影
    ext = proj.max(axis=0) - proj.min(axis=0)
    a0 = np.maximum(ext / 2.0, _EPS)
    return t0, R0, a0


def fit_superquadric(points) -> dict:
    """点群にスーパー2次曲面を least_squares で当てはめ dict{a,eps,R,t,residual} を返す。

    初期姿勢 = 慣性テンソル固有ベクトル、初期 a = 主軸 bbox 半分、初期 eps=(1,1)。
    ``a`` は正、``eps`` は [0.1, 2.0] にクリップして最適化する。

    Returns
    -------
    dict: {'a': (3,), 'eps': (2,), 'R': (3,3), 't': (3,), 'residual': float}
    """
    from scipy.optimize import least_squares
    from scipy.spatial.transform import Rotation

    P = _pts(points)
    if len(P) < 6:
        raise ValueError(f"fit_superquadric: at least 6 points required (got N={len(P)})")

    t0, R0, a0 = _principal_frame(P)
    rotvec0 = Rotation.from_matrix(R0).as_rotvec()
    diag = float(np.linalg.norm(P.max(axis=0) - P.min(axis=0))) + _EPS

    # p = [a1,a2,a3, eps1,eps2, rvx,rvy,rvz, tx,ty,tz]
    p0 = np.concatenate([a0, [1.0, 1.0], rotvec0, t0]).astype(np.float64)

    lb = np.array([1e-3 * diag, 1e-3 * diag, 1e-3 * diag,
                   0.1, 0.1,
                   -2.0 * np.pi, -2.0 * np.pi, -2.0 * np.pi,
                   t0[0] - 5.0 * diag, t0[1] - 5.0 * diag, t0[2] - 5.0 * diag])
    ub = np.array([10.0 * diag, 10.0 * diag, 10.0 * diag,
                   2.0, 2.0,
                   2.0 * np.pi, 2.0 * np.pi, 2.0 * np.pi,
                   t0[0] + 5.0 * diag, t0[1] + 5.0 * diag, t0[2] + 5.0 * diag])
    p0 = np.clip(p0, lb, ub)

    def resid(p):
        a = p[0:3]
        eps = p[3:5]
        R = Rotation.from_rotvec(p[5:8]).as_matrix()
        t = p[8:11]
        return _residual_vector(P, a, eps, R, t)

    sol = least_squares(resid, p0, bounds=(lb, ub), method="trf",
                        xtol=1e-10, ftol=1e-10, max_nfev=4000)
    p = sol.x
    a = np.asarray(p[0:3], dtype=np.float64)
    eps = np.clip(np.asarray(p[3:5], dtype=np.float64), 0.1, 2.0)
    R = Rotation.from_rotvec(p[5:8]).as_matrix()
    t = np.asarray(p[8:11], dtype=np.float64)
    residual = superquadric_residual(P, a, eps, R, t)
    return {"a": a, "eps": eps, "R": R, "t": t, "residual": residual}

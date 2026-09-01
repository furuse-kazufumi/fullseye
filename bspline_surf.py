# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""B スプライン自由曲面 / 自由曲線フィッティング(scipy FITPACK, numpy in/out)。

match3d.fit_poly_surface(多項式最小二乗)は大域基底なので低次のうねりしか
表現できない。本モジュールは区分多項式(B スプライン)で局所的に曲がる
「自由曲面 z=f(x,y)」を張り、外観検査・形状計測(平面度/球面度を超えた自由
形状の逸脱量)に使う。曲線側(splprep)はシーム/エッジなど順序付き 3D 点列を
滑らかな 3D 自由曲線として復元する。

用語:
- tck = FITPACK の節点(knot)+ 係数(coefficient)+ 次数(degree)の三つ組。
  曲面は list ``[tx, ty, c, kx, ky]``、曲線は tuple ``(t, c, k)``。
- smooth(平滑化係数 s)= 残差二乗和の許容上限。0 = 全点通過(補間・過適合寄り)、
  大きいほど滑らか(ノイズを吸うが形状を鈍らせる)。

エラー処理方針: 点数不足・次数過大・縮退(共線/重複点)を握り潰さず、原因の
分かる ``ValueError`` に翻訳する。次数は利用可能点数に収まるよう自動で下げる。
"""
from __future__ import annotations

import math
import warnings

import numpy as np

__all__ = [
    "fit_bspline_surface",
    "eval_bspline_surface",
    "surface_residual",
    "fit_bspline_curve",
    "eval_bspline_curve",
]


# --------------------------------------------------------------------------- #
# 曲面(散布データ z = f(x, y))                                                #
# --------------------------------------------------------------------------- #
def _check_tck(tck, want: int, kind: str):
    """FITPACK の tck を **fail-closed** に検証する(要素数で曲面/曲線を判別)。

    曲面は ``[tx, ty, c, kx, ky]``(5 要素)、曲線は ``(t, c, k)``(3 要素)。
    どちらも list/tuple なので取り違えても素の呼び出しは通ってしまい、
    scipy の奥で不可解な例外になる。多項式モデル(``match3d.fit_poly_surface``
    の dict)を渡された場合も同様なので、ここで名指しで拒否する。

    Raises
    ------
    ValueError
        tck が list/tuple でない、または要素数が *want* と違う。
    """
    if isinstance(tck, dict):
        raise ValueError(
            f"{kind}: tck must be the FITPACK tuple/list from the matching fit "
            "function, but a dict was given — that is a polynomial surface model "
            "(match3d.fit_poly_surface); evaluate it with match3d.eval_poly_surface")
    if not isinstance(tck, (list, tuple)):
        raise ValueError(
            f"{kind}: tck must be a list/tuple from the matching fit function "
            f"(got {type(tck).__name__})")
    if len(tck) != want:
        other = "a curve tck (t, c, k)" if len(tck) == 3 else (
            "a surface tck [tx, ty, c, kx, ky]" if len(tck) == 5 else
            f"{len(tck)} elements")
        raise ValueError(
            f"{kind}: tck must have {want} elements, got {other}. "
            "Surface models come from fit_bspline_surface and curve models from "
            "fit_bspline_curve; they are not interchangeable")
    return tck


def _auto_surface_smooth(m: int) -> float:
    """点数 m から FITPACK 既定の平滑化係数 s = m - sqrt(2m) を算出(下限 0)。

    標準偏差 1 相当のノイズを想定した古典的な既定値。過適合(s=0)と過平滑の
    中間に落とす。点数が少ないと sqrt(2m) が支配的になり s→0(ほぼ補間)。
    """
    return float(max(0.0, m - math.sqrt(2.0 * m)))


def fit_bspline_surface(x, y, z, kx=3, ky=3, smooth=None):
    """散布 (x, y, z) に双三次(既定)B スプライン曲面を最小二乗フィット(bisplrep)。

    Parameters
    ----------
    x, y, z : array_like
        同数の散布サンプル座標と高さ。任意形状で与えてよく内部で 1 次元化する。
    kx, ky : int
        x/y 方向の B スプライン次数(1=線形, 3=三次)。点数が (kx+1)*(ky+1) に
        満たない場合は自動で下げる(縮退回避)。
    smooth : float or None
        平滑化係数 s。None は点数ベースの自動値(``_auto_surface_smooth``)。
        0.0 で全点通過(補間寄り=過適合しやすい)、大きいほど滑らか。

    Returns
    -------
    tck : list
        ``[tx, ty, c, kx, ky]``。eval_bspline_surface / surface_residual に渡す。

    Raises
    ------
    ValueError
        点数が線形曲面にすら足りない(m<4)、x/y/z の長さ不一致、非有限値、
        あるいは共線・重複による FITPACK 縮退で近似が得られない場合。
    """
    from scipy.interpolate import bisplrep

    xr = np.asarray(x, float).ravel()
    yr = np.asarray(y, float).ravel()
    zr = np.asarray(z, float).ravel()
    if not (xr.size == yr.size == zr.size):
        raise ValueError(
            f"x, y, z must have equal length (got {xr.size}, {yr.size}, {zr.size})."
        )
    m = xr.size
    if m < 4:
        raise ValueError(
            f"B-spline surface needs at least 4 points (linear kx=ky=1). Got {m} points."
        )
    if not (np.all(np.isfinite(xr)) and np.all(np.isfinite(yr)) and np.all(np.isfinite(zr))):
        raise ValueError("x, y, z contain non-finite values (NaN/Inf).")

    kx = int(kx)
    ky = int(ky)
    if kx < 1 or ky < 1:
        raise ValueError(f"kx, ky must be >= 1 (got kx={kx}, ky={ky}).")
    # 次数が過大で係数数 (kx+1)*(ky+1) が点数を超えると縮退するので下げる。
    while (kx + 1) * (ky + 1) > m and (kx > 1 or ky > 1):
        if kx >= ky:
            kx -= 1
        else:
            ky -= 1

    s = _auto_surface_smooth(m) if smooth is None else float(smooth)
    if s < 0:
        raise ValueError(f"smooth must be non-negative (got {s}).")

    try:
        with warnings.catch_warnings():
            # FITPACK は反復打ち切り等を warning で報せるが tck 自体は返る。
            warnings.simplefilter("ignore")
            tck = bisplrep(xr, yr, zr, kx=kx, ky=ky, s=s)
    except Exception as exc:  # noqa: BLE001 - FITPACK は素の ValueError/RuntimeError
        raise ValueError(
            "B-spline surface fit failed (points may be collinear/duplicate, or "
            f"smoothing factor too small causing degeneracy): {exc}"
        ) from exc

    # bisplrep は失敗時に None を返すことがある。
    if tck is None or tck[2] is None or len(np.asarray(tck[2])) == 0:
        raise ValueError(
            "no B-spline surface coefficients obtained (degenerate data arrangement)."
        )
    return tck


def eval_bspline_surface(tck, x, y, grid=False):
    """フィット済み曲面 tck を評価(bisplev)。散布点(既定)または格子の 2 モード。

    Parameters
    ----------
    tck : list
        fit_bspline_surface が返した ``[tx, ty, c, kx, ky]``。
    x, y : array_like
        grid=False(既定): 同一 shape の散布/対応点。各 (x[i], y[i]) で評価し
        入力と同じ shape の z を返す(計測=各サンプル位置での曲面高さ)。
        grid=True: x, y を昇順の 1 次元軸として扱い、テンソル格子
        (len(x), len(y)) 上で評価(密な可視化・再サンプリング用)。
    grid : bool
        評価モード。曲面残差など点対応の比較には False。

    Returns
    -------
    z : numpy.ndarray
        grid=False なら x と同 shape、grid=True なら (len(x), len(y))。

    Raises
    ------
    ValueError
        tck が曲面モデル([tx,ty,c,kx,ky])でない(曲線 tck / 多項式 dict を含む)、
        または x, y の shape 不一致・空。
    """
    from scipy.interpolate import bisplev

    _check_tck(tck, 5, "eval_bspline_surface")
    if grid:
        gx = np.asarray(x, float).ravel()
        gy = np.asarray(y, float).ravel()
        if gx.size == 0 or gy.size == 0:
            raise ValueError("grid evaluation requires at least 1 point for both x and y.")
        # bisplev は昇順を仮定するので並べ替え、評価後に元の順序へ戻す。
        ox = np.argsort(gx, kind="mergesort")
        oy = np.argsort(gy, kind="mergesort")
        zz = np.atleast_2d(bisplev(gx[ox], gy[oy], tck))
        out = np.empty_like(zz)
        out[np.ix_(ox, oy)] = zz
        return out

    xa = np.asarray(x, float)
    ya = np.asarray(y, float)
    if xa.shape != ya.shape:
        raise ValueError(
            f"scattered evaluation requires x and y to have the same shape (x={xa.shape}, y={ya.shape})."
            " For grid evaluation, pass grid=True."
        )
    xf = xa.ravel()
    yf = ya.ravel()
    # bisplev はスカラー入力で 0 次元を返す。点毎に評価して元 shape へ復元。
    z = np.array([float(bisplev(float(xi), float(yi), tck)) for xi, yi in zip(xf, yf)])
    return z.reshape(xa.shape)


def surface_residual(x, y, z, tck):
    """散布データと曲面 tck の残差統計を返す(形状誤差=フィットからの逸脱)。

    各サンプル位置で曲面高さを評価し、観測 z との差の RMS / 最大絶対値 / PV
    (peak-to-valley = 最大 - 最小)を計測する。検査ではこれが自由曲面からの
    ずれ量(打痕・うねり・欠肉)の定量指標になる。

    Returns
    -------
    dict
        ``{"rms": float, "max": float, "pv": float}``。max は最大絶対残差、
        pv は符号付き残差の最大 - 最小(片側だけの凸/凹も捉える)。
    """
    zr = np.asarray(z, float).ravel()
    zhat = eval_bspline_surface(tck, x, y, grid=False).ravel()
    resid = zr - zhat
    return {
        "rms": float(np.sqrt(np.mean(resid ** 2))),
        "max": float(np.max(np.abs(resid))),
        "pv": float(resid.max() - resid.min()),
    }


# --------------------------------------------------------------------------- #
# 曲線(順序付き点列 → 3D 自由曲線)                                            #
# --------------------------------------------------------------------------- #
def fit_bspline_curve(points, smooth=0.0, k=3, nest=None):
    """順序付き点列(M,D)に B スプライン曲線をフィット(splprep, パラメトリック)。

    シーム/エッジ/計測プローブ軌跡など「並び順が意味を持つ」点列を滑らかな
    パラメトリック曲線 r(u), u∈[0,1] として復元する。z=f(x,y) と違い多価
    (折り返し・ループ)な形も表せる。

    Parameters
    ----------
    points : array_like, shape (M, D)
        順序付き頂点。D=3 が典型(3D 曲線)だが 2D 以上を許容。
    smooth : float
        平滑化係数 s。0.0 で全点通過(補間)、大きいほど滑らか。
    k : int
        次数(既定 3=三次)。点数が k+1 未満なら自動で下げる。
    nest : int or None
        節点数の上限(splprep へそのまま渡す)。None で自動。

    Returns
    -------
    tck : tuple
        ``(t, c, k)``。eval_bspline_curve に渡す。

    Raises
    ------
    ValueError
        点数が 2 未満、次元不整合、非有限値、または重複/縮退で splprep が
        曲線を返せない場合。
    """
    from scipy.interpolate import splprep

    pts = np.asarray(points, float)
    if pts.ndim != 2:
        raise ValueError(f"points must be a 2D array of shape (M, D) (got shape {pts.shape}).")
    m, d = pts.shape
    if m < 2:
        raise ValueError(f"curve fitting needs at least 2 points (got {m}).")
    if d < 2:
        raise ValueError(f"points dimension D must be >= 2 (got D={d}).")
    if not np.all(np.isfinite(pts)):
        raise ValueError("points contain non-finite values (NaN/Inf).")

    k = int(k)
    if k < 1:
        raise ValueError(f"k must be >= 1 (got {k}).")
    if k >= m:  # splprep は m > k を要求
        k = m - 1

    s = float(smooth)
    if s < 0:
        raise ValueError(f"smooth must be non-negative (got {s}).")

    coords = [pts[:, j] for j in range(d)]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tck, _u = splprep(coords, s=s, k=k, nest=nest)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(
            "B-spline curve fit failed (possibly due to consecutive duplicate points or "
            f"a degenerate arrangement): {exc}"
        ) from exc
    return tck


def eval_bspline_curve(tck, n=200):
    """曲線 tck をパラメータ u∈[0,1] 上 n 点で等間隔評価(splev)。

    Parameters
    ----------
    tck : tuple
        fit_bspline_curve が返した ``(t, c, k)``。
    n : int
        評価点数(既定 200)。2 以上。

    Returns
    -------
    numpy.ndarray, shape (n, D)
        曲線上の点列。D は fit 時の入力次元(3D 入力なら (n, 3))。
    """
    from scipy.interpolate import splev

    _check_tck(tck, 3, "eval_bspline_curve")
    n = int(n)
    if n < 2:
        raise ValueError(f"n must be >= 2 (got {n}).")
    u = np.linspace(0.0, 1.0, n)
    out = splev(u, tck)  # D 本の 1 次元配列のリスト
    return np.stack(out, axis=1)

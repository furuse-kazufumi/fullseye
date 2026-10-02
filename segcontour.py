# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""変分・動的輪郭: 離散 snake(Kass–Witkin–Terzopoulos 1988)、勾配ベクトル流 GVF(Xu–Prince 1998)、Chan–Vese の
エネルギーと勾配流(2001)、形態学的 Chan–Vese と形態学的測地的 active contour(Márquez-Neila–Baumela–Álvarez 2014)、
エッジ停止関数 g、符号付き距離への再初期化(Sussman–Smereka–Osher 1994 + Russo–Smereka 2000 の subcell fix)、
距離正則化レベルセット DRLSE(Li–Xu–Gui–Fox 2010)、平均曲率流。

## 何を作るか

セグメンテーション拡充 第 2 陣「変分・動的輪郭」。**学習器は載せない**(numpy + scipy のルールベース)。どの op も
**定理か第 2 実装の門** を持つ:

1. ``snake_evolve`` —— Kass ら 1988 の式 (19)(20) の半陰的な更新 x_t = (A + γI)^(-1)(γ x_(t-1) − f_x)。内部エネルギーは
   陰的(帯行列 A)、外力は陽的。門: (a) 外力 0 で円は **離散の閉形式どおり** 縮む —— 円は巡回行列 A の第 1 Fourier
   モードなので 1 反復ごとに半径が γ / (γ + λ_1) 倍、λ_1 = 4α sin²(π/N) + 16β sin⁴(π/N)(厳密)。
   (b) 勾配の外力なら 1 反復は「二次の内部エネルギー + 外力の線形化 + γ/2 |x − x_old|²」の最小化(近接勾配法)なので、
   γ ≥ L(外力の勾配の Lipschitz 定数)ならエネルギーは単調非増加(降下補題)。L の見積りと実測の増加回数を返す。
   (c) 第 2 実装 = ``skimage.segmentation.active_contour``(同じ式、``max_px_move`` の tanh 制限つき)。
2. ``gvf_field`` —— Xu–Prince 1998 の GVF: E = ∬ μ(u_x² + u_y² + v_x² + v_y²) + |∇f|² |v − ∇f|² を最小化する場。
   Euler 方程式 μ∇²u − (u − f_x)(f_x² + f_y²) = 0(v も同様)は **線形** なので、反復(論文の時間発展)と疎行列の直接解の
   2 通りで解き、残差を返す(門 = 残差 ≈ 0、2 解法の一致)。
3. ``chan_vese_energy`` / ``chan_vese_evolve`` —— Chan–Vese 2001 の F(c1, c2, C) = μ Length(C) + ν Area(inside(C))
   + λ1 ∫_inside |u0 − c1|² + λ2 ∫_outside |u0 − c2|²、c1 / c2 = 内 / 外の平均(式 (6)(7))、H_ε は論文の arctan 版。
   evolve は **離散エネルギーの厳密な勾配**(長さ項は前進差分とその随伴)で降下し、Armijo の後退で単調非増加を保証する
   (後退した回数を返す = 固定の刻みで足りたかの記録)。c1, c2 は φ ごとの最適値なので包絡線定理で勾配に入らない。
4. ``morph_chan_vese`` / ``morph_geodesic_ac`` —— Márquez-Neila ら 2014 の形態学的近似(データ項の符号で画素を反転 →
   曲率の作用素 SI∘IS / IS∘SI)。門: (a) データ項の 1 段は c を固定すると画素ごとに分離した和なので、反転した画素の
   1 つ 1 つが当てはめのエネルギーを下げ、c を平均に更新するとさらに下がる = **データ段の前後で当てはめのエネルギーは
   単調非増加**(厳密)。平滑段は上げうる(実測を返す)。(b) 第 2 実装 = skimage の同名関数(同じ作用素列なら画素一致)。
5. ``edge_stop_g`` —— g = 1 / (1 + |∇(G_σ * I)|² / k²)(Caselles–Kimmel–Sapiro 1997 の p = 2 の形、k = 1 で依頼の式)。
   門: g ∈ (0, 1]、平坦な画像で g ≡ 1。
6. ``level_set_reinit`` —— φ_τ + S(φ0)(|∇φ| − 1) = 0(Sussman–Smereka–Osher 1994、Chan–Vese 2001 の式 (10) が引用する
   もの)を Godunov の風上差分で解き、界面に接する格子点は Russo–Smereka 2000 の subcell fix で零等高線を動かさない。
   第 2 実装 = 距離変換(``scipy.ndimage.distance_transform_edt``)の符号付き距離。門: 帯の中で |∇φ| ≈ 1、前後の零等高線の
   Hausdorff ≤ 1 px。
7. ``drle_evolve`` —— Li ら 2010 の DRLSE(エッジ版): φ_t = μ div(d_p(|∇φ|)∇φ) + λ δ_ε(φ) div(g ∇φ/|∇φ|) + α g δ_ε(φ)、
   二重井戸 p2(s) = (1 − cos 2πs)/(2π)²(s ≤ 1)、(s − 1)²/2(s ≥ 1)。再初期化をしない。門: 零等高線の近くの |∇φ| の分位点
   を **測って** 返す(論文の主張「符号付き距離の形を保つ」の確認)、真円の縁で輪郭が止まる(外力の釣り合い)。
8. ``curvature_flow`` —— 平均曲率流 φ_t = |∇φ| div(∇φ/|∇φ|)。門: 閉曲線の囲む面積は dA/dt = −∮ κ ds = −2π(埋め込まれた
   単純閉曲線の回転数 1、凸でなくても成り立つ)、円なら r(t)² = r0² − 2t(Gage–Hamilton 1986 / Grayson 1987 の流れの
   円の場合)。

## 規約

* 画素の添字 (row, col) = (y, x)。snake の点は (N, 2) の [row, col] で skimage と同じ。
* レベルセットは **φ < 0 が内側**(Sussman・Li の流儀)。Chan–Vese の「内側」も φ < 0 で、H_ε(−φ) を内側の重みにする。
* マスクから φ を作るときは距離変換の符号付き距離(画素の中心の間の半画素をずらす: 内側 −(d_in − 0.5)、外側 d_out − 0.5)。
* 返り値はどれも dict。入力が不正なら ValueError(黙って直さない)。

## 原論文で確認したこと / 要確認(self_reported)

* 確認: Kass 1988 の式 (1)(全エネルギー = 内部 + 画像 + 拘束の積分)と (17)〜(20)(内部は陰的、外力は陽的、
  x_t = (A + γI)^(-1)(γ x_(t-1) − f_x))を原論文の版面で目視。
* 確認: Chan–Vese 2001 のエネルギー(μ Length + ν Area + λ1, λ2 の当てはめ)、c1/c2 = 内外の平均(式 (6)(7))、
  「再初期化は任意」と Sussman の式 (10) の引用を本文で確認。**論文はエネルギーの単調減少を主張していない**
  (単調性はここでの離散勾配 + 後退の性質で、論文の定理ではない)。
* 要確認(二次資料のみ): GVF のエネルギーと Euler 方程式(Wikipedia の Xu–Prince 1998 の引用で照合)、時間刻みの安定条件
  Δt ≤ ΔxΔy/(4μ)(記憶、原論文未確認)。Márquez-Neila 2014 の「作用素列は Chan–Vese / GAC の PDE と無限小で同値」は
  skimage の docstring の記述で、原論文の定理の文言は未確認。DRLSE の「再初期化が要らない」「零等高線の近くで符号付き
  距離の形を保つ」と CFL 条件 μΔt < 1/4 は Li らの配布コードの流儀と記憶による(原論文の文言は未確認)。
  Sussman 1994 / Russo–Smereka 2000 の式は記憶による(門 = 距離変換との一致で数値的に確かめる)。
* snake の外力 0 の縮みは **曲線短縮流ではない**: パラメータ s は固定(弧長でない)なので α 項は s についての熱方程式、
  円の半径は r² = r0² − 2αt でなく指数的に縮む(上の閉形式)。r² = r0² − 2t の法則は ``curvature_flow`` の門。
* GVF の力は一般に勾配場でない(回転成分を持つ)ので、GVF snake には **エネルギーが無い**(Xu–Prince は力の釣り合いで
  定式化)。``snake_evolve(external="gvf")`` のエネルギーは内部の分だけ返し、単調性の判定はしない(None)。
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import ndimage as ndi
from scipy import sparse
from scipy.interpolate import RectBivariateSpline
from scipy.sparse import linalg as spla

import segeval

__all__ = [
    "MAX_PIXELS", "MAX_ITER", "MAX_POINTS",
    "snake_evolve", "gvf_field", "chan_vese_energy", "chan_vese_evolve", "morph_chan_vese", "morph_geodesic_ac",
    "edge_stop_g", "level_set_reinit", "drle_evolve", "curvature_flow",
]

#: 1 枚の画像の画素数の上限(疎行列の直接解・履歴の保持を抑える)。
MAX_PIXELS = 4_000_000
#: 反復回数の上限。
MAX_ITER = 100_000
#: snake の点の数の上限((N, N) の逆行列を持つ)。
MAX_POINTS = 5_000


# ───────────────────────────── 入力の検査 ─────────────────────────────
def _image(x, name: str, op: str) -> np.ndarray:
    """2-D の有限な実数画像に揃える(bool / 整数は float64 に)。"""
    if isinstance(x, (str, bytes, dict)) or np.ma.is_masked(x):
        raise ValueError("%s: %s must be a 2-D real image" % (op, name))
    a = np.asarray(x)
    if a.dtype.kind not in "biuf":
        raise ValueError("%s: %s has dtype %s — must be real" % (op, name, a.dtype))
    a = a.astype(np.float64)
    if a.ndim != 2 or a.shape[0] < 3 or a.shape[1] < 3:
        raise ValueError("%s: %s must be a 2-D image of at least 3 x 3, got shape %r" % (op, name, a.shape))
    if a.size > MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels > MAX_PIXELS=%d" % (op, name, a.size, MAX_PIXELS))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s has non-finite values" % (op, name))
    return a


def _mask(x, name: str, op: str, shape: Tuple[int, int], need_both: bool = True) -> np.ndarray:
    """2-D の 0/1 マスクに揃える(bool / 0・1 の整数・0・1 の float)。内側と外側の両方が要る(need_both)。"""
    if isinstance(x, (str, bytes, dict)) or np.ma.is_masked(x):
        raise ValueError("%s: %s must be a 2-D mask" % (op, name))
    a = np.asarray(x)
    if a.dtype.kind == "b":
        m = a
    elif a.dtype.kind in "iuf":
        if a.dtype.kind == "f" and not np.isfinite(a).all():
            raise ValueError("%s: %s has non-finite values" % (op, name))
        if np.count_nonzero((a != 0) & (a != 1)) > 0:
            raise ValueError("%s: %s must hold only 0 and 1" % (op, name))
        m = a != 0
    else:
        raise ValueError("%s: %s has dtype %s — must be bool or 0/1" % (op, name, a.dtype))
    if m.ndim != 2 or m.shape != tuple(shape):
        raise ValueError("%s: %s must have shape %r, got %r" % (op, name, tuple(shape), m.shape))
    n_in = int(np.count_nonzero(m))
    if need_both and (n_in == 0 or n_in == m.size):
        raise ValueError("%s: %s must contain both inside and outside pixels" % (op, name))
    return m.astype(bool)


def _num(v, name: str, op: str, lo: float = -math.inf, hi: float = math.inf, lo_open: bool = False) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number (got %r)" % (op, name, v)) from None
    if not math.isfinite(f) or f < lo or f > hi or (lo_open and f == lo):
        raise ValueError("%s: %s must be finite and in %s%g, %g] (got %r)" % (op, name, "(" if lo_open else "[", lo, hi, v))
    return f


def _int(v, name: str, op: str, lo: int = 0, hi: int = MAX_ITER) -> int:
    if isinstance(v, bool):
        raise ValueError("%s: %s must be an integer (got %r)" % (op, name, v))
    try:
        k = int(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be an integer (got %r)" % (op, name, v)) from None
    if k != v or not (lo <= k <= hi):
        raise ValueError("%s: %s must be an integer in [%d, %d] (got %r)" % (op, name, lo, hi, v))
    return k


def _choice(v, name: str, op: str, allowed) -> str:
    if v not in allowed:
        raise ValueError("%s: %s must be one of %s (got %r)" % (op, name, ", ".join(allowed), v))
    return v


# ───────────────────────────── 共通の道具 ─────────────────────────────
def _signed_distance(inside: np.ndarray) -> np.ndarray:
    """マスク → 符号付き距離(内側 < 0)。零等高線は内外の画素の中心の中間(半画素ずらし)。"""
    d_out = ndi.distance_transform_edt(~inside)
    d_in = ndi.distance_transform_edt(inside)
    return np.where(inside, -(d_in - 0.5), d_out - 0.5)


def _phi_or_mask(x, name: str, op: str) -> np.ndarray:
    """bool のマスクなら符号付き距離に、実数なら φ(内側 < 0)としてそのまま。"""
    a = np.asarray(x)
    if a.dtype.kind == "b":
        m = _mask(a, name, op, a.shape if a.ndim == 2 else (0, 0))
        return _signed_distance(m)
    phi = _image(a, name, op)
    n_in = int(np.count_nonzero(phi < 0))
    if n_in == 0 or n_in == phi.size:
        raise ValueError("%s: %s must have both negative (inside) and non-negative (outside) values" % (op, name))
    return phi


def _lap(u: np.ndarray) -> np.ndarray:
    """5 点の Laplacian、Neumann 境界(縁の画素を複製)。"""
    p = np.pad(u, 1, mode="edge")
    return p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] - 4.0 * u


def _lap_matrix(h: int, w: int) -> sparse.csr_matrix:
    """``_lap`` と同じ離散 Laplacian の疎行列(Neumann、行優先の並び)。"""
    def d1(n):
        main = -2.0 * np.ones(n)
        main[0] = main[-1] = -1.0
        off = np.ones(n - 1)
        return sparse.diags([off, main, off], [-1, 0, 1], format="csr")
    return (sparse.kron(sparse.identity(h), d1(w)) + sparse.kron(d1(h), sparse.identity(w))).tocsr()


def _quantiles_in_band(phi: np.ndarray, band: float) -> Dict[str, float]:
    """|φ| ≤ band の画素での |∇φ|(中心差分)の 10・50・90 % 点と画素数。"""
    gy, gx = np.gradient(phi)
    s = np.hypot(gx, gy)
    sel = np.abs(phi) <= band
    n = int(np.count_nonzero(sel))
    if n == 0:
        return {"q10": float("nan"), "q50": float("nan"), "q90": float("nan"), "n": 0}
    q = np.percentile(s[sel], [10, 50, 90])
    return {"q10": float(q[0]), "q50": float(q[1]), "q90": float(q[2]), "n": n}


def _zero_set_hausdorff(phi_a: np.ndarray, phi_b: np.ndarray) -> float:
    """2 つの φ の零等高線(内側 φ < 0 のマスクの境界)の Hausdorff 距離(segeval の境界の規約)。"""
    return float(segeval.seg_hausdorff((phi_a < 0).astype(np.int64), (phi_b < 0).astype(np.int64))["hausdorff"])


def _polygon_mask(points: np.ndarray, shape: Tuple[int, int]) -> np.ndarray:
    """閉じた折れ線 [row, col] の内側(偶奇規則、画素の中心で判定)。"""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    inside = np.zeros(shape, bool)
    r = points[:, 0]
    c = points[:, 1]
    r2 = np.roll(r, -1)
    c2 = np.roll(c, -1)
    assert len(r) > 0
    for k in range(len(r)):
        if r[k] == r2[k]:
            continue
        cross = (r[k] > yy) != (r2[k] > yy)
        xint = (c2[k] - c[k]) * (yy - r[k]) / (r2[k] - r[k]) + c[k]
        inside ^= cross & (xx < xint)
    return inside


def _resample_closed(points: np.ndarray, n: int) -> np.ndarray:
    """閉じた折れ線を弧長で等間隔の n 点に打ち直す。"""
    p = np.vstack([points, points[:1]])
    seg = np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1]))
    s = np.concatenate([[0.0], np.cumsum(seg)])
    if s[-1] <= 0:
        return points.copy()
    t = np.linspace(0.0, s[-1], n, endpoint=False)
    return np.stack([np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])], axis=1)


# ───────────────────────────── 5. エッジ停止関数 ─────────────────────────────
def edge_stop_g(image, *, sigma: float = 1.0, k: float = 1.0) -> Dict[str, object]:
    """エッジ停止関数 g = 1 / (1 + |∇(G_σ * I)|² / k²)(Caselles–Kimmel–Sapiro 1997 の p = 2 の形)。

    ``sigma`` = ガウスの標準偏差(0 なら平滑化なしの中心差分)、``k`` = 勾配の尺度(k = 1 で g = 1/(1 + |∇G_σ*I|²))。
    画像の値域に依存する: Li ら 2010 の配布例は 0〜255 の画像で k = 1 なので、[0, 1] の画像なら k = 1/255 が同じ挙動。
    返り値: ``g``(0 < g ≤ 1、平坦で 1)、``grad_mag``、``g_min`` / ``g_max``、``sigma``、``k``。
    門: g ∈ (0, 1] —— 分母 ≥ 1、平坦な画像で g ≡ 1(勾配 0)。"""
    op = "edge_stop_g"
    im = _image(image, "image", op)
    sg = _num(sigma, "sigma", op, 0.0, 100.0)
    kk = _num(k, "k", op, 0.0, 1e12, lo_open=True)
    if sg > 0:
        gm = ndi.gaussian_gradient_magnitude(im, sg, mode="nearest")
    else:
        gy, gx = np.gradient(im)
        gm = np.hypot(gx, gy)
    g = 1.0 / (1.0 + (gm / kk) ** 2)
    return {"g": g, "grad_mag": gm, "g_min": float(g.min()), "g_max": float(g.max()), "sigma": sg, "k": kk}


# ───────────────────────────── 2. GVF ─────────────────────────────
def gvf_field(image, *, mu: float = 0.2, sigma: float = 1.0, method: str = "direct", n_iter: int = 2000,
              dt: Optional[float] = None, edge_map=None) -> Dict[str, object]:
    """勾配ベクトル流(Xu–Prince 1998): 辺の地図 f の勾配を、辺から離れた所へ滑らかに拡散した場 (u, v)。

    E = ∬ μ(u_x² + u_y² + v_x² + v_y²) + |∇f|² |(u, v) − ∇f|² の最小化。Euler 方程式
    μ∇²u − (u − f_x)(f_x² + f_y²) = 0、μ∇²v − (v − f_y)(f_x² + f_y²) = 0(線形)。
    ``method="iterate"`` = 論文の時間発展 u ← u + Δt(μ∇²u − b(u − f_x))、b = |∇f|²(陽的、Δt ≤ 1/(4μ + max b))。
    ``method="direct"`` = 同じ離散方程式 (μL − diag b) u = −b f_x を疎行列で直接解く(定常解そのもの)。
    辺の地図 f は既定で |∇(G_σ * I)| を最大 1 に正規化したもの(``edge_map`` で直接与えてもよい)。境界は Neumann。
    u = 列(x)方向、v = 行(y)方向の成分。
    返り値: ``u`` / ``v``、``edge_map``、``fx`` / ``fy``、``residual_max``(Euler 方程式の残差の最大)、``residual_rel``
    (残差 / max(b |∇f|))、``n_iter``、``method``、``mu``。f が平坦なら場は 0(残差 0)。"""
    op = "gvf_field"
    im = _image(image, "image", op)
    m = _num(mu, "mu", op, 0.0, 1e6, lo_open=True)
    sg = _num(sigma, "sigma", op, 0.0, 100.0)
    meth = _choice(method, "method", op, ("direct", "iterate"))
    if edge_map is None:
        if sg > 0:
            f = ndi.gaussian_gradient_magnitude(im, sg, mode="nearest")
        else:
            gy0, gx0 = np.gradient(im)
            f = np.hypot(gx0, gy0)
        fmax = float(f.max())
        f = f / fmax if fmax > 0 else f
    else:
        f = _image(edge_map, "edge_map", op)
        if f.shape != im.shape:
            raise ValueError("%s: edge_map shape %r differs from image %r" % (op, f.shape, im.shape))
    fy, fx = np.gradient(f)
    b = fx * fx + fy * fy
    h, w = f.shape
    n_done = 0
    if float(b.max()) == 0.0:
        u = np.zeros_like(f)
        v = np.zeros_like(f)
    elif meth == "direct":
        L = _lap_matrix(h, w)
        M = (m * L - sparse.diags(b.ravel())).tocsc()
        lu = spla.splu(M)
        u = lu.solve(-(b * fx).ravel()).reshape(h, w)
        v = lu.solve(-(b * fy).ravel()).reshape(h, w)
    else:
        ni = _int(n_iter, "n_iter", op, 1)
        bmax = float(b.max())
        step = 1.0 / (4.0 * m + bmax) if dt is None else _num(dt, "dt", op, 0.0, 1e6, lo_open=True)
        if step * (8.0 * m + bmax) > 2.0:
            raise ValueError("%s: dt=%g violates the explicit stability bound dt <= 2/(8 mu + max b) = %g"
                             % (op, step, 2.0 / (8.0 * m + bmax)))
        u, v = fx.copy(), fy.copy()
        for _ in range(ni):
            u = u + step * (m * _lap(u) - b * (u - fx))
            v = v + step * (m * _lap(v) - b * (v - fy))
        n_done = ni
    ru = m * _lap(u) - b * (u - fx)
    rv = m * _lap(v) - b * (v - fy)
    res = float(max(np.abs(ru).max(), np.abs(rv).max()))
    scale = float(np.max(b * np.sqrt(b)))
    return {"u": u, "v": v, "edge_map": f, "fx": fx, "fy": fy, "residual_max": res,
            "residual_rel": res / scale if scale > 0 else 0.0, "n_iter": n_done, "method": meth, "mu": m}


# ───────────────────────────── 1. snake ─────────────────────────────
def _snake_matrix(n: int, alpha: float, beta: float) -> np.ndarray:
    """周期境界の A = −α D2 + β D4(D2 = 2 階差分、D4 = 4 階差分)。½ xᵀ A x = ½ Σ (α|Δx|² + β|Δ²x|²)。"""
    eye = np.eye(n)
    a = np.roll(eye, -1, axis=0) + np.roll(eye, -1, axis=1) - 2 * eye
    b = (np.roll(eye, -2, axis=0) + np.roll(eye, -2, axis=1) - 4 * np.roll(eye, -1, axis=0)
         - 4 * np.roll(eye, -1, axis=1) + 6 * eye)
    return -alpha * a + beta * b


def _internal_energy(p: np.ndarray, alpha: float, beta: float) -> float:
    d1 = np.roll(p, -1, axis=0) - p
    d2 = np.roll(p, -1, axis=0) - 2 * p + np.roll(p, 1, axis=0)
    return 0.5 * float(alpha * np.sum(d1 * d1) + beta * np.sum(d2 * d2))


def snake_evolve(image, init_points, *, alpha: float = 0.1, beta: float = 0.1, gamma: float = 1.0,
                 external: str = "edge", w_line: float = 0.0, w_edge: float = 1.0, sigma: float = 1.0,
                 kappa: float = 1.0, gvf=None, gvf_mu: float = 0.2, max_px_move: Optional[float] = None,
                 n_iter: int = 300, spline_order: int = 3, tol: float = 0.0, resample_every: int = 0,
                 record_every: int = 0) -> Dict[str, object]:
    """離散 snake(Kass–Witkin–Terzopoulos 1988)の半陰的な更新 x_t = (A + γI)^(-1)(γ x_(t-1) − f_x)(式 (19)(20))。

    閉じた snake(周期境界)の点 ``init_points``(N, 2)= [row, col]、N ≥ 5。内部エネルギー
    E_int = ½ Σ (α |v_(i+1) − v_i|² + β |v_(i+1) − 2v_i + v_(i−1)|²) = ½ xᵀ A x(陰的)。外力(陽的)は ``external`` で選ぶ:
    ``"edge"`` = ポテンシャル P = w_line · G_σ*I + w_edge · |∇(G_σ*I)|²、E_ext = −κ Σ P(v_i)(Kass の E_line と E_edge)、
    ``"potential"`` = ``image`` をそのまま P として使う(第 2 実装と同じ P を渡すため)、
    ``"gvf"`` = 力そのものが −κ (v, u)(GVF、``gvf`` に ``gvf_field`` の返りを渡すか、``gvf_mu`` で内部で作る)、
    ``"none"`` = 外力 0。P は ``spline_order`` 次の補間スプライン(値と微分が整合)で点の位置へ。
    ``max_px_move`` を与えると 1 反復の移動を max_px_move · tanh(Δ) に制限(skimage と同じ。近接勾配の性質は失う)。
    ``resample_every`` > 0 なら k 反復ごとに弧長で等間隔に打ち直す(凹部へ入るとき点が疎になるのを防ぐ。エネルギーの
    単調性はその時点で途切れる)。点は画像の範囲 [0, H−1] × [0, W−1] に切り詰める。
    返り値: ``points``(N, 2)、``mask``(折れ線の内側)、``energy`` / ``energy_internal`` / ``energy_external``(反復ごと、
    先頭 = 初期。GVF では外力のエネルギーが定義されないので total と external は NaN)、``n_increase``(エネルギーが
    増えた反復の数、GVF なら None)、``max_increase``、``lipschitz``(κP のヘッセ行列のスペクトルノルムの格子上の最大 =
    外力の勾配の Lipschitz 定数の見積り)、``gamma_ge_lipschitz``(γ ≥ L なら降下補題で単調非増加が保証される)、
    ``radius_factor``(外力 0 の円の 1 反復の縮み γ/(γ + λ_1) の閉形式)、``history``(record_every ごとの点)、
    ``n_iter``、``converged``。"""
    op = "snake_evolve"
    im = _image(image, "image", op)
    h, w = im.shape
    pts = np.asarray(init_points, dtype=np.float64) if not isinstance(init_points, (str, bytes, dict)) else None
    if pts is None or pts.ndim != 2 or pts.shape[1] != 2 or not (5 <= pts.shape[0] <= MAX_POINTS):
        raise ValueError("%s: init_points must be an (N, 2) array of [row, col] with 5 <= N <= %d" % (op, MAX_POINTS))
    if not np.isfinite(pts).all():
        raise ValueError("%s: init_points has non-finite values" % op)
    if pts[:, 0].min() < 0 or pts[:, 0].max() > h - 1 or pts[:, 1].min() < 0 or pts[:, 1].max() > w - 1:
        raise ValueError("%s: init_points must lie inside the image [0, H-1] x [0, W-1]" % op)
    al = _num(alpha, "alpha", op, 0.0, 1e6)
    be = _num(beta, "beta", op, 0.0, 1e6)
    ga = _num(gamma, "gamma", op, 0.0, 1e9, lo_open=True)
    ext = _choice(external, "external", op, ("edge", "potential", "gvf", "none"))
    wl = _num(w_line, "w_line", op, -1e6, 1e6)
    we = _num(w_edge, "w_edge", op, -1e6, 1e6)
    sg = _num(sigma, "sigma", op, 0.0, 100.0)
    ka = _num(kappa, "kappa", op, -1e9, 1e9)
    mpm = None if max_px_move is None else _num(max_px_move, "max_px_move", op, 0.0, 1e6, lo_open=True)
    ni = _int(n_iter, "n_iter", op, 0)
    so = _int(spline_order, "spline_order", op, 1, 5)
    tl = _num(tol, "tol", op, 0.0, 1e6)
    rs = _int(resample_every, "resample_every", op, 0)
    rec = _int(record_every, "record_every", op, 0)
    n = pts.shape[0]
    A = _snake_matrix(n, al, be)
    inv = np.linalg.inv(A + ga * np.eye(n))
    lam1 = 4.0 * al * math.sin(math.pi / n) ** 2 + 16.0 * be * math.sin(math.pi / n) ** 4
    rows = np.arange(h, dtype=np.float64)
    cols = np.arange(w, dtype=np.float64)

    spl = None
    field = None
    lip = 0.0
    if ext in ("edge", "potential"):
        if ext == "edge":
            ims = ndi.gaussian_filter(im, sg, mode="nearest") if sg > 0 else im
            gy, gx = np.gradient(ims)
            P = wl * ims + we * (gx * gx + gy * gy)
        else:
            P = im
        spl = RectBivariateSpline(rows, cols, P, kx=so, ky=so, s=0)
        if so >= 3:          # 2 階微分はスプラインの次数 ≥ 3 でしか取れない(FITPACK の制約)
            Pyy, Pxx, Pxy = spl(rows, cols, dx=2), spl(rows, cols, dy=2), spl(rows, cols, dx=1, dy=1)
        else:                # 低次: 差分で見積もる(Lipschitz は目安)
            Pr, Pc = np.gradient(P)
            Pyy, Pxy = np.gradient(Pr)
            Pxx = np.gradient(Pc, axis=1)
        lip = float(np.max(np.abs(ka) * (0.5 * np.abs(Pyy + Pxx) + np.sqrt(0.25 * (Pyy - Pxx) ** 2 + Pxy ** 2))))
    elif ext == "gvf":
        g = gvf if gvf is not None else gvf_field(im, mu=gvf_mu, sigma=sg)
        if not isinstance(g, dict) or "u" not in g or "v" not in g:
            raise ValueError("%s: gvf must be the dict returned by gvf_field" % op)
        gu, gv = np.asarray(g["u"], np.float64), np.asarray(g["v"], np.float64)
        if gu.shape != im.shape or gv.shape != im.shape:
            raise ValueError("%s: gvf field shape differs from the image" % op)
        field = (gv, gu)

    def forces(p):
        """∂E_ext/∂(row, col) at the points (for gvf: minus the field)."""
        if spl is not None:
            fr = -ka * spl.ev(p[:, 0], p[:, 1], dx=1)
            fc = -ka * spl.ev(p[:, 0], p[:, 1], dy=1)
            return fr, fc
        if field is not None:
            co = [p[:, 0], p[:, 1]]
            fr = -ka * ndi.map_coordinates(field[0], co, order=1, mode="nearest")
            fc = -ka * ndi.map_coordinates(field[1], co, order=1, mode="nearest")
            return fr, fc
        return np.zeros(n), np.zeros(n)

    def ext_energy(p):
        if spl is not None:
            return float(-ka * np.sum(spl.ev(p[:, 0], p[:, 1])))
        if field is not None:
            return float("nan")
        return 0.0

    p = pts.copy()
    e_int = [_internal_energy(p, al, be)]
    e_ext = [ext_energy(p)]
    history: List[np.ndarray] = [p.copy()] if rec else []
    converged = False
    done = 0
    for it in range(ni):
        fr, fc = forces(p)
        rn = inv @ (ga * p[:, 0] - fr)
        cn = inv @ (ga * p[:, 1] - fc)
        if mpm is not None:
            rn = p[:, 0] + mpm * np.tanh(rn - p[:, 0])
            cn = p[:, 1] + mpm * np.tanh(cn - p[:, 1])
        newp = np.stack([np.clip(rn, 0.0, h - 1.0), np.clip(cn, 0.0, w - 1.0)], axis=1)
        move = float(np.max(np.abs(newp - p)))
        p = newp
        if rs and (it + 1) % rs == 0:
            p = _resample_closed(p, n)
        done = it + 1
        e_int.append(_internal_energy(p, al, be))
        e_ext.append(ext_energy(p))
        if rec and done % rec == 0:
            history.append(p.copy())
        if tl > 0 and move < tl:
            converged = True
            break
    ei = np.array(e_int)
    ee = np.array(e_ext)
    et = ei + ee
    if field is not None:
        n_inc = None
        max_inc = float("nan")
    else:
        d = np.diff(et)
        scale = max(1.0, float(np.max(np.abs(et))))
        n_inc = int(np.count_nonzero(d > 1e-10 * scale))
        max_inc = float(d.max()) if d.size else 0.0
    return {"points": p, "mask": _polygon_mask(p, (h, w)), "energy": et, "energy_internal": ei, "energy_external": ee,
            "n_increase": n_inc, "max_increase": max_inc, "lipschitz": lip, "gamma_ge_lipschitz": bool(ga >= lip),
            "radius_factor": ga / (ga + lam1), "history": history, "n_iter": done, "converged": converged}


# ───────────────────────────── 3. Chan–Vese ─────────────────────────────
def _heav(z: np.ndarray, eps: float) -> np.ndarray:
    """Chan–Vese 2001 の H_ε(z) = ½(1 + (2/π) arctan(z/ε))。"""
    return 0.5 * (1.0 + (2.0 / math.pi) * np.arctan(z / eps))


def _dirac(z: np.ndarray, eps: float) -> np.ndarray:
    """δ_ε = H_ε' = (1/π) ε / (ε² + z²)。"""
    return (eps / math.pi) / (eps * eps + z * z)


def _dirac_prime(z: np.ndarray, eps: float) -> np.ndarray:
    return -(2.0 * eps / math.pi) * z / (eps * eps + z * z) ** 2


def _fwd(phi: np.ndarray):
    """前進差分(最後の列・行は 0 = Neumann)。"""
    dx = np.zeros_like(phi)
    dy = np.zeros_like(phi)
    dx[:, :-1] = phi[:, 1:] - phi[:, :-1]
    dy[:-1, :] = phi[1:, :] - phi[:-1, :]
    return dx, dy


def _fwd_adjoint(wx: np.ndarray, wy: np.ndarray) -> np.ndarray:
    """前進差分の随伴 Dᵀ: ⟨Dφ, w⟩ = ⟨φ, Dᵀw⟩。"""
    out = np.zeros_like(wx)
    wx = wx.copy()
    wy = wy.copy()
    wx[:, -1] = 0.0
    wy[-1, :] = 0.0
    out[:, 1:] += wx[:, :-1]
    out[:, :] -= wx
    out[1:, :] += wy[:-1, :]
    out[:, :] -= wy
    return out


def _cv_parts(im, phi, mu, nu, l1, l2, eps, eta):
    hin = _heav(-phi, eps)
    hout = 1.0 - hin
    s_in, s_out = float(hin.sum()), float(hout.sum())
    c1 = float((im * hin).sum() / s_in) if s_in > 0 else 0.0
    c2 = float((im * hout).sum() / s_out) if s_out > 0 else 0.0
    dx, dy = _fwd(phi)
    gn = np.sqrt(dx * dx + dy * dy + eta * eta)
    dl = _dirac(phi, eps)
    length = float(np.sum(dl * gn))
    area = float(hin.sum())
    fin = float(np.sum((im - c1) ** 2 * hin))
    fout = float(np.sum((im - c2) ** 2 * hout))
    e = mu * length + nu * area + l1 * fin + l2 * fout
    return {"energy": e, "length": length, "area": area, "fit_inside": fin, "fit_outside": fout, "c1": c1, "c2": c2,
            "_dx": dx, "_dy": dy, "_gn": gn, "_dl": dl}


def _cv_grad(im, phi, parts, mu, nu, l1, l2, eps):
    dx, dy, gn, dl = parts["_dx"], parts["_dy"], parts["_gn"], parts["_dl"]
    g_len = _dirac_prime(phi, eps) * gn + _fwd_adjoint(dl * dx / gn, dl * dy / gn)
    # 内側の重み H_ε(−φ) の φ 微分は −δ_ε(φ)
    g_reg = -dl * (nu + l1 * (im - parts["c1"]) ** 2 - l2 * (im - parts["c2"]) ** 2)
    return mu * g_len + g_reg


def chan_vese_energy(image, phi, *, mu: float = 0.1, nu: float = 0.0, lambda1: float = 1.0, lambda2: float = 1.0,
                     eps: float = 1.0, eta: float = 0.1) -> Dict[str, float]:
    """Chan–Vese 2001 のエネルギー F = μ Length + ν Area(inside) + λ1 ∫_in |I − c1|² + λ2 ∫_out |I − c2|²(2 相)。

    ``phi`` は φ(内側 φ < 0)か bool のマスク(符号付き距離に直す)。正則化: 内側の重み H_ε(−φ)(論文の arctan 版)、
    長さ = Σ δ_ε(φ) |Dφ|_η(前進差分、|Dφ|_η = √(D_x² + D_y² + η²))。c1 / c2 = 内 / 外の H_ε で重みづけた平均(式 (6)(7))。
    同じマスクの「鋭い」版(``energy_sharp``)も返す: 長さ = 4 近傍で内外が変わる辺の数、内外は φ < 0 で 0/1。
    返り値: ``energy``、``length``、``area``、``fit_inside`` / ``fit_outside``、``c1`` / ``c2``(H_ε で重みづけた平均 ——
    ε = 1 の arctan は裾が長いので 2 値の画像でも 0/1 から離れる)、``energy_sharp``、``perimeter_sharp``、
    ``c1_sharp`` / ``c2_sharp``(φ < 0 の内外の平均)。"""
    op = "chan_vese_energy"
    im = _image(image, "image", op)
    ph = _phi_or_mask(phi, "phi", op)
    if ph.shape != im.shape:
        raise ValueError("%s: phi shape %r differs from image %r" % (op, ph.shape, im.shape))
    m = _num(mu, "mu", op, 0.0, 1e9)
    nu_ = _num(nu, "nu", op, -1e9, 1e9)
    l1 = _num(lambda1, "lambda1", op, 0.0, 1e9)
    l2 = _num(lambda2, "lambda2", op, 0.0, 1e9)
    ep = _num(eps, "eps", op, 0.0, 1e6, lo_open=True)
    et = _num(eta, "eta", op, 0.0, 1e6, lo_open=True)
    parts = _cv_parts(im, ph, m, nu_, l1, l2, ep, et)
    inside = ph < 0
    per = int(np.count_nonzero(inside[:, 1:] != inside[:, :-1]) + np.count_nonzero(inside[1:, :] != inside[:-1, :]))
    n_in = int(np.count_nonzero(inside))
    c1s = float(im[inside].mean()) if n_in else 0.0
    c2s = float(im[~inside].mean()) if n_in < im.size else 0.0
    es = (m * per + nu_ * n_in + l1 * float(np.sum((im[inside] - c1s) ** 2))
          + l2 * float(np.sum((im[~inside] - c2s) ** 2)))
    out = {k: v for k, v in parts.items() if not k.startswith("_")}
    out.update({"energy_sharp": float(es), "perimeter_sharp": per, "c1_sharp": c1s, "c2_sharp": c2s})
    return out


def _sharp_energy(im, u, mu, nu, l1, l2):
    """鋭い Chan–Vese エネルギー(4 近傍の割れ目の数 = 異方的な離散 TV、c は内外の平均)。"""
    per = int(np.count_nonzero(u[:, 1:] != u[:, :-1]) + np.count_nonzero(u[1:, :] != u[:-1, :]))
    n_in = int(np.count_nonzero(u))
    c1 = float(im[u].mean()) if n_in else 0.0
    c2 = float(im[~u].mean()) if n_in < im.size else 0.0
    e = mu * per + nu * n_in + l1 * float(np.sum((im[u] - c1) ** 2)) + l2 * float(np.sum((im[~u] - c2) ** 2))
    return float(e), c1, c2


def _cen_solve(r, mu, u0, px0, py0, n_inner):
    """min_(u ∈ [0,1]) μ Σ(|D_x u| + |D_y u|) + Σ r u を Chambolle–Pock(τ = σ = 0.35、‖D‖² ≤ 8)で解く。"""
    u = u0.copy()
    ub = u.copy()
    px, py = px0.copy(), py0.copy()
    tau = sig = 0.35
    for _ in range(n_inner):
        dx, dy = _fwd(ub)
        px = np.clip(px + sig * dx, -mu, mu)
        py = np.clip(py + sig * dy, -mu, mu)
        un = np.clip(u - tau * (_fwd_adjoint(px, py) + r), 0.0, 1.0)
        ub = 2.0 * un - u
        u = un
    dx, dy = _fwd(u)
    primal = mu * float(np.abs(dx).sum() + np.abs(dy).sum()) + float(np.sum(r * u))
    dual = float(np.minimum(_fwd_adjoint(px, py) + r, 0.0).sum())
    return u, px, py, primal - dual


def _cv_convex(im, init, op, mu, nu, lambda1, lambda2, n_iter, n_inner, record_every):
    if np.asarray(init).dtype.kind == "b":
        u = _mask(init, "init", op, im.shape)
    else:
        ph = _phi_or_mask(init, "init", op)
        if ph.shape != im.shape:
            raise ValueError("%s: init shape %r differs from image %r" % (op, ph.shape, im.shape))
        u = ph < 0
    m = _num(mu, "mu", op, 0.0, 1e9)
    nu_ = _num(nu, "nu", op, -1e9, 1e9)
    l1 = _num(lambda1, "lambda1", op, 0.0, 1e9)
    l2 = _num(lambda2, "lambda2", op, 0.0, 1e9)
    ni = _int(n_iter, "n_iter", op, 0)
    nin = _int(n_inner, "n_inner", op, 1)
    rec = _int(record_every, "record_every", op, 0)
    e, c1, c2 = _sharp_energy(im, u, m, nu_, l1, l2)
    energy = [e]
    gaps = []
    history: List[np.ndarray] = [u.copy()] if rec else []
    uf = u.astype(np.float64)
    px = np.zeros_like(uf)
    py = np.zeros_like(uf)
    n_guard = 0
    done = 0
    converged = False
    for it in range(ni):
        r = nu_ + l1 * (im - c1) ** 2 - l2 * (im - c2) ** 2
        uf, px, py, gap = _cen_solve(r, m, uf, px, py, nin)
        un = uf > 0.5
        en, c1n, c2n = _sharp_energy(im, un, m, nu_, l1, l2)
        gaps.append(gap)
        if en > e + 1e-9 * max(1.0, abs(e)):
            n_guard += 1
            break
        changed = int(np.count_nonzero(un != u))
        u, e, c1, c2 = un, en, c1n, c2n
        energy.append(e)
        done = it + 1
        if rec and done % rec == 0:
            history.append(u.copy())
        if changed == 0:
            converged = True
            break
    en_arr = np.array(energy)
    return {"mask": u, "phi": _signed_distance(u) if 0 < np.count_nonzero(u) < u.size else np.where(u, -1.0, 1.0),
            "energy": en_arr, "c1": c1, "c2": c2, "n_guard": n_guard, "n_rejected": 0,
            "n_increase": int(np.count_nonzero(np.diff(en_arr) > 0)), "duality_gap": np.array(gaps),
            "history": history, "n_iter": done, "converged": converged, "method": "convex"}


def chan_vese_evolve(image, init, *, method: str = "convex", mu: float = 0.1, nu: float = 0.0, lambda1: float = 1.0,
                     lambda2: float = 1.0, eps: float = 1.0, eta: float = 0.1, dt: float = 5.0, n_iter: int = 200,
                     n_inner: int = 200, tol: float = 0.0, record_every: int = 0) -> Dict[str, object]:
    """Chan–Vese 2001 の 2 相のエネルギーを最小化する(既定は凸緩和の交互最小化、レベルセットの勾配降下も選べる)。

    2 つの方法:

    ``method="convex"``(既定)= c の更新(内外の平均 = 最適)と、c を固定した分割の更新の交互最小化。分割の更新は
    Chan–Esedoglu–Nikolova 2006 の凸緩和 min_(u∈[0,1]) μ TV(u) + Σ (ν + λ1 (I − c1)² − λ2 (I − c2)²) u を
    Chambolle–Pock で ``n_inner`` 回解いて 1/2 で 2 値化する(TV は異方的な前進差分 = 2 値なら 4 近傍の割れ目の数 =
    ``chan_vese_energy`` の ``perimeter_sharp``。離散の余面積公式で、緩和の最小解をどの閾値で切っても 2 値の最小解)。
    鋭いエネルギー(``energy`` = ``chan_vese_energy`` の ``energy_sharp``)は交互最小化で単調非増加 —— 内側の解法の誤差で
    増えそうなら更新を捨てて止める(``n_guard``、0 のはず)。
    ``method="level_set"`` = 滑らかなエネルギー(``chan_vese_energy`` の ``energy``)を **離散エネルギーの厳密な勾配** で降下する。

    勾配 = μ(δ_ε'(φ) |Dφ|_η + Dᵀ(δ_ε(φ) Dφ / |Dφ|_η)) − δ_ε(φ)(ν + λ1 (I − c1)² − λ2 (I − c2)²)(D = 前進差分、
    Dᵀ = その随伴。連続の極限で −δ_ε κ μ の項になり論文の式 (9) の右辺の符号反転と一致)。c1, c2 は φ ごとの最適値なので
    包絡線定理で勾配に入らない。刻みは ``dt`` から始め、Armijo 条件 E_new ≤ E − 10⁻⁴ dt |∇E|² を満たすまで半分にする
    (満たしたら次の反復は 1.1 倍、上限 dt)。よってエネルギーは単調非増加(``n_increase`` は 0 のはず、後退の回数は
    ``n_rejected``)。**実測の限界**: 厳密な勾配は界面を動かすより |φ| を膨らませて H_ε を鋭くする向きにも下がるので、
    遠い画素(δ_ε が小さい)は事実上動かず局所解で止まる(楕円 + 雑音 σ = 0.2 で 300 反復後も誤り約 800 画素、convex は
    数十画素)。論文が再初期化を「任意」として載せている理由の 1 つ。``init`` = bool のマスク(内側)か φ(内側 φ < 0)。
    返り値: ``mask``(φ < 0)、``phi``(convex は 2 値の符号付き距離)、``energy``(先頭 = 初期)、``c1`` / ``c2``、
    ``n_rejected``、``n_guard``、``n_increase``、``duality_gap``(convex の内側の解法の主双対ギャップ、外側の反復ごと)、
    ``history``(record_every ごとのマスク)、``n_iter``、``converged``、``method``。"""
    op = "chan_vese_evolve"
    im = _image(image, "image", op)
    meth = _choice(method, "method", op, ("convex", "level_set"))
    if meth == "convex":
        return _cv_convex(im, init, op, mu, nu, lambda1, lambda2, n_iter, n_inner, record_every)
    if np.asarray(init).dtype.kind == "b":
        phi = _signed_distance(_mask(init, "init", op, im.shape))
    else:
        phi = _phi_or_mask(init, "init", op)
        if phi.shape != im.shape:
            raise ValueError("%s: init shape %r differs from image %r" % (op, phi.shape, im.shape))
    m = _num(mu, "mu", op, 0.0, 1e9)
    nu_ = _num(nu, "nu", op, -1e9, 1e9)
    l1 = _num(lambda1, "lambda1", op, 0.0, 1e9)
    l2 = _num(lambda2, "lambda2", op, 0.0, 1e9)
    ep = _num(eps, "eps", op, 0.0, 1e6, lo_open=True)
    et = _num(eta, "eta", op, 0.0, 1e6, lo_open=True)
    dt0 = _num(dt, "dt", op, 0.0, 1e6, lo_open=True)
    ni = _int(n_iter, "n_iter", op, 0)
    tl = _num(tol, "tol", op, 0.0, 1.0)
    rec = _int(record_every, "record_every", op, 0)
    parts = _cv_parts(im, phi, m, nu_, l1, l2, ep, et)
    energy = [parts["energy"]]
    history: List[np.ndarray] = [phi < 0] if rec else []
    step = dt0
    n_rej = 0
    done = 0
    converged = False
    for it in range(ni):
        g = _cv_grad(im, phi, parts, m, nu_, l1, l2, ep)
        g2 = float(np.sum(g * g))
        if g2 == 0.0:
            converged = True
            break
        accepted = False
        for _ in range(60):
            cand = phi - step * g
            cp = _cv_parts(im, cand, m, nu_, l1, l2, ep, et)
            if cp["energy"] <= parts["energy"] - 1e-4 * step * g2:
                accepted = True
                break
            step *= 0.5
            n_rej += 1
        if not accepted:
            converged = True
            break
        e_old = parts["energy"]
        phi, parts = cand, cp
        energy.append(parts["energy"])
        step = min(step * 1.1, dt0)
        done = it + 1
        if rec and done % rec == 0:
            history.append(phi < 0)
        if tl > 0 and abs(e_old - parts["energy"]) <= tl * max(abs(e_old), 1e-300):
            converged = True
            break
    e = np.array(energy)
    d = np.diff(e)
    return {"mask": phi < 0, "phi": phi, "energy": e, "c1": parts["c1"], "c2": parts["c2"], "n_rejected": n_rej,
            "n_guard": 0, "n_increase": int(np.count_nonzero(d > 0)), "duality_gap": np.array([]), "history": history,
            "n_iter": done, "converged": converged, "method": "level_set"}


# ───────────────────────────── 4. 形態学的 snake ─────────────────────────────
_P2 = [np.eye(3, dtype=bool), np.array([[0, 1, 0]] * 3, dtype=bool), np.flipud(np.eye(3, dtype=bool)),
       np.rot90(np.array([[0, 1, 0]] * 3, dtype=bool))]


def _si(u: np.ndarray) -> np.ndarray:
    """SI 作用素 = 4 本の線分の構造要素での収縮の最大(sup of inf)。"""
    out = np.zeros(u.shape, bool)
    assert len(_P2) > 0
    for P in _P2:
        out |= ndi.binary_erosion(u, P)
    return out


def _is(u: np.ndarray) -> np.ndarray:
    """IS 作用素 = 4 本の線分の構造要素での膨張の最小(inf of sup)。"""
    out = np.ones(u.shape, bool)
    assert len(_P2) > 0
    for P in _P2:
        out &= ndi.binary_dilation(u, P)
    return out


def _curv(u: np.ndarray, phase: int) -> np.ndarray:
    """曲率の作用素: phase 偶数 = SI∘IS、奇数 = IS∘SI(交互に使う)。"""
    return _si(_is(u)) if phase % 2 == 0 else _is(_si(u))


def _fit_energy(im: np.ndarray, u: np.ndarray, l1: float, l2: float) -> Tuple[float, float, float]:
    n_in = int(np.count_nonzero(u))
    c1 = float(im[u].mean()) if n_in else 0.0
    c0 = float(im[~u].mean()) if n_in < im.size else 0.0
    e = l1 * float(np.sum((im[u] - c1) ** 2)) + l2 * float(np.sum((im[~u] - c0) ** 2))
    return e, c1, c0


def morph_chan_vese(image, init, *, n_iter: int = 100, smoothing: int = 1, lambda1: float = 1.0, lambda2: float = 1.0,
                    phase: int = 0, record_every: int = 0) -> Dict[str, object]:
    """形態学的 Chan–Vese(Márquez-Neila–Baumela–Álvarez 2014 の MorphACWE)。1 反復 = データ段 + 平滑段。

    データ段: c1 = 内側の平均、c0 = 外側の平均、aux = |∇u|(λ1 (I − c1)² − λ2 (I − c0)²)、aux < 0 の画素を内側、
    aux > 0 を外側に(|∇u| ≠ 0 = 境界の近くだけが動く)。平滑段: 曲率の作用素(SI∘IS と IS∘SI を交互)を ``smoothing`` 回。
    ``phase`` = 最初に使う作用素(0 = SI∘IS)。skimage の実装は交互の位相をモジュールの大域状態に持つので、
    同じ入力でも直前の呼び出しで結果が変わりうる —— ここは呼び出しごとに ``phase`` から始める(決定的)。
    当てはめのエネルギー E_fit = λ1 Σ_in (I − c1)² + λ2 Σ_out (I − c0)² を各段の前後で記録する。
    門(厳密): c を固定した E_fit は画素ごとの和なので、データ段で反転した画素はどれも E_fit を下げ(または等しく)、
    その後 c を平均に更新するとさらに下がる ⇒ データ段の前後で E_fit は単調非増加(``n_data_increase`` = 0)。
    平滑段は E_fit を上げうる(``fit_after_smooth`` で実測)。
    返り値: ``mask``、``fit_before_data`` / ``fit_after_data`` / ``fit_after_smooth``(反復ごと)、``n_data_increase``、
    ``history``、``n_iter``、``n_changed``(反復ごとに変わった画素数)。"""
    op = "morph_chan_vese"
    im = _image(image, "image", op)
    u = _mask(init, "init", op, im.shape)
    ni = _int(n_iter, "n_iter", op, 0)
    sm = _int(smoothing, "smoothing", op, 0, 100)
    l1 = _num(lambda1, "lambda1", op, 0.0, 1e9)
    l2 = _num(lambda2, "lambda2", op, 0.0, 1e9)
    ph = _int(phase, "phase", op, 0, 1)
    rec = _int(record_every, "record_every", op, 0)
    before, after, after_s, changed = [], [], [], []
    history: List[np.ndarray] = [u.copy()] if rec else []
    k = ph
    for it in range(ni):
        prev = u.copy()
        e0, c1, c0 = _fit_energy(im, u, l1, l2)
        # skimage と同じ: c は +1e-8 の分母、|∇u| は np.gradient の絶対値の和
        uf = u.astype(np.int8)
        c0s = float((im * (1 - uf)).sum() / float((1 - uf).sum() + 1e-8))
        c1s = float((im * uf).sum() / float(uf.sum() + 1e-8))
        du = np.gradient(uf)
        abs_du = np.abs(du[0]) + np.abs(du[1])
        aux = abs_du * (l1 * (im - c1s) ** 2 - l2 * (im - c0s) ** 2)
        u = u.copy()
        u[aux < 0] = True
        u[aux > 0] = False
        e1 = _fit_energy(im, u, l1, l2)[0]
        for _ in range(sm):
            u = _curv(u, k)
            k += 1
        e2 = _fit_energy(im, u, l1, l2)[0]
        before.append(e0)
        after.append(e1)
        after_s.append(e2)
        changed.append(int(np.count_nonzero(u != prev)))
        if rec and (it + 1) % rec == 0:
            history.append(u.copy())
    b, a = np.array(before), np.array(after)
    scale = max(1.0, float(np.max(np.abs(b)))) if b.size else 1.0
    return {"mask": u, "fit_before_data": b, "fit_after_data": a, "fit_after_smooth": np.array(after_s),
            "n_data_increase": int(np.count_nonzero(a - b > 1e-9 * scale)), "history": history, "n_iter": ni,
            "n_changed": np.array(changed, dtype=np.int64)}


def morph_geodesic_ac(gimage, init, *, n_iter: int = 100, smoothing: int = 1, threshold="auto", balloon: float = 0.0,
                      phase: int = 0, record_every: int = 0) -> Dict[str, object]:
    """形態学的な測地的 active contour(Márquez-Neila ら 2014 の MorphGAC)。``gimage`` = 縁で小さい画像(``edge_stop_g`` の g)。

    1 反復 = 風船段(balloon > 0 で 3×3 の膨張、< 0 で収縮を g > threshold/|balloon| の画素にだけ)+ 引力段
    (∇g · ∇u > 0 の画素を内側、< 0 を外側 = g の谷へ輪郭を引く)+ 平滑段(曲率の作用素を ``smoothing`` 回、交互)。
    ``threshold="auto"`` は g の 40 % 点(skimage と同じ)。**落とし穴(実測)**: 背景が厳密に平坦だと g ≡ 1 の画素が 40 % を
    超え、閾値 = 1 で「g > 1/|balloon|」の画素が無くなり風船が一度も働かない(輪郭は初期のまま止まる)。ぼかしの裾で g が
    1 − 10⁻¹³ になる画像では偶然働く。平坦な合成画像では閾値を数で与えること。``phase`` は ``morph_chan_vese`` と同じ。
    返り値: ``mask``、``threshold``、``history``、``n_iter``、``n_changed``(反復ごと)。"""
    op = "morph_geodesic_ac"
    g = _image(gimage, "gimage", op)
    u = _mask(init, "init", op, g.shape)
    ni = _int(n_iter, "n_iter", op, 0)
    sm = _int(smoothing, "smoothing", op, 0, 100)
    bl = _num(balloon, "balloon", op, -1e6, 1e6)
    ph = _int(phase, "phase", op, 0, 1)
    rec = _int(record_every, "record_every", op, 0)
    th = float(np.percentile(g, 40)) if threshold == "auto" else _num(threshold, "threshold", op, -1e12, 1e12)
    structure = np.ones((3, 3), dtype=np.int8)
    dg = np.gradient(g)
    bmask = g > th / abs(bl) if bl != 0 else None
    history: List[np.ndarray] = [u.copy()] if rec else []
    changed = []
    k = ph
    for it in range(ni):
        prev = u.copy()
        u = u.copy()
        if bl != 0:
            aux_b = ndi.binary_dilation(u, structure) if bl > 0 else ndi.binary_erosion(u, structure)
            u[bmask] = aux_b[bmask]
        du = np.gradient(u.astype(np.int8))
        aux = dg[0] * du[0] + dg[1] * du[1]
        u[aux > 0] = True
        u[aux < 0] = False
        for _ in range(sm):
            u = _curv(u, k)
            k += 1
        changed.append(int(np.count_nonzero(u != prev)))
        if rec and (it + 1) % rec == 0:
            history.append(u.copy())
    return {"mask": u, "threshold": th, "history": history, "n_iter": ni, "n_changed": np.array(changed, dtype=np.int64)}


# ───────────────────────────── 6. 再初期化 ─────────────────────────────
def _godunov(phi: np.ndarray, sgn: np.ndarray) -> np.ndarray:
    """Godunov の風上で |∇φ|(h = 1、縁は複製)。sgn > 0 と < 0 で風上の向きが逆。"""
    p = np.pad(phi, 1, mode="edge")
    a = phi - p[1:-1, :-2]      # D−x
    b = p[1:-1, 2:] - phi       # D+x
    c = phi - p[:-2, 1:-1]      # D−y
    d = p[2:, 1:-1] - phi       # D+y
    pos = np.sqrt(np.maximum(np.maximum(a, 0) ** 2, np.minimum(b, 0) ** 2)
                  + np.maximum(np.maximum(c, 0) ** 2, np.minimum(d, 0) ** 2))
    neg = np.sqrt(np.maximum(np.minimum(a, 0) ** 2, np.maximum(b, 0) ** 2)
                  + np.maximum(np.minimum(c, 0) ** 2, np.maximum(d, 0) ** 2))
    return np.where(sgn > 0, pos, np.where(sgn < 0, neg, 0.0))


def level_set_reinit(phi, *, method: str = "sussman", n_iter: int = 100, dt: float = 0.5,
                     band: float = 3.0) -> Dict[str, object]:
    """φ(内側 φ < 0)を同じ零等高線の符号付き距離に直す。

    ``method="sussman"`` = φ_τ + S(φ0)(|∇φ| − 1) = 0(Sussman–Smereka–Osher 1994)を Godunov の風上差分で
    ``n_iter`` 回(刻み ``dt`` ≤ 0.5)。界面に接する格子点(4 近傍で符号が変わる)は Russo–Smereka 2000 の subcell fix:
    D = φ0 / Δφ0(Δφ0 = 中心差分の勾配の大きさと片側差分の最大)へ緩和させ、零等高線を動かさない。
    ``method="edt"`` = マスク φ < 0 から距離変換で作る符号付き距離(第 2 実装。零等高線は画素の中心の中間に量子化され、
    最大で半画素動く)。bool のマスクを渡すと edt の符号付き距離を φ0 として使う。
    返り値: ``phi``、``grad``(|φ| ≤ band での |∇φ| の 10/50/90 % 点と画素数)、``grad_before``(同、入力)、
    ``zero_hausdorff``(前後の零等高線の Hausdorff、画素)、``method``、``n_iter``。"""
    op = "level_set_reinit"
    p0 = _phi_or_mask(phi, "phi", op)
    meth = _choice(method, "method", op, ("sussman", "edt"))
    ni = _int(n_iter, "n_iter", op, 0)
    st = _num(dt, "dt", op, 0.0, 0.5, lo_open=True)
    bd = _num(band, "band", op, 0.0, 1e6, lo_open=True)
    if meth == "edt":
        out = _signed_distance(p0 < 0)
        done = 0
    else:
        sgn = np.sign(p0)
        pp = np.pad(p0, 1, mode="edge")
        nb = [pp[1:-1, :-2], pp[1:-1, 2:], pp[:-2, 1:-1], pp[2:, 1:-1]]
        assert len(nb) > 0
        near = np.zeros(p0.shape, bool)
        for q in nb:
            near |= (q * p0) < 0
        gx = 0.5 * (pp[1:-1, 2:] - pp[1:-1, :-2])
        gy = 0.5 * (pp[2:, 1:-1] - pp[:-2, 1:-1])
        dphi = np.hypot(gx, gy)
        for q in nb:
            dphi = np.maximum(dphi, np.abs(q - p0))
        dphi = np.maximum(dphi, 1e-12)
        D = p0 / dphi
        out = p0.copy()
        for _ in range(ni):
            G = _godunov(out, sgn) - 1.0
            upd = out - st * sgn * G
            fix = out - st * (sgn * np.abs(out) - D)
            out = np.where(near, fix, upd)
        done = ni
    return {"phi": out, "grad": _quantiles_in_band(out, bd), "grad_before": _quantiles_in_band(p0, bd),
            "zero_hausdorff": _zero_set_hausdorff(p0, out), "method": meth, "n_iter": done}


# ───────────────────────────── 7. DRLSE ─────────────────────────────
def _neumann(f: np.ndarray) -> np.ndarray:
    """Li ら の配布コードの NeumannBoundCond: 縁の 1 列を内側 2 列目の値で置く(鏡映)。"""
    g = f.copy()
    g[0, 0], g[0, -1], g[-1, 0], g[-1, -1] = g[2, 2], g[2, -3], g[-3, 2], g[-3, -3]
    g[0, 1:-1] = g[2, 1:-1]
    g[-1, 1:-1] = g[-3, 1:-1]
    g[1:-1, 0] = g[1:-1, 2]
    g[1:-1, -1] = g[1:-1, -3]
    return g


def _div(nx: np.ndarray, ny: np.ndarray) -> np.ndarray:
    return np.gradient(nx, axis=1) + np.gradient(ny, axis=0)


def _drl_dirac(x: np.ndarray, eps: float) -> np.ndarray:
    """Li 2010 の δ_ε(x) = (1/2ε)(1 + cos(πx/ε))(|x| ≤ ε)、外は 0。"""
    f = (1.0 / (2.0 * eps)) * (1.0 + np.cos(math.pi * x / eps))
    return np.where(np.abs(x) <= eps, f, 0.0)


def _drl_heav(x: np.ndarray, eps: float) -> np.ndarray:
    """Li 2010 の H_ε(x) = ½(1 + x/ε + sin(πx/ε)/π)(|x| ≤ ε)、x > ε で 1、x < −ε で 0。"""
    f = 0.5 * (1.0 + x / eps + np.sin(math.pi * x / eps) / math.pi)
    return np.where(x > eps, 1.0, np.where(x < -eps, 0.0, f))


def _p2(s: np.ndarray) -> np.ndarray:
    """二重井戸 p2(s) = (1 − cos 2πs)/(2π)²(s ≤ 1)、(s − 1)²/2(s ≥ 1)。"""
    return np.where(s <= 1.0, (1.0 - np.cos(2 * math.pi * s)) / (2 * math.pi) ** 2, 0.5 * (s - 1.0) ** 2)


def drle_evolve(image, init, *, mu: Optional[float] = None, lambda_: float = 5.0, alpha: float = 1.5,
                epsilon: float = 1.5, dt: float = 1.0, sigma: float = 1.5, k: float = 1.0 / 255.0, g=None,
                n_iter: int = 300, c0: float = 2.0, potential: str = "double_well",
                record_every: int = 0) -> Dict[str, object]:
    """距離正則化レベルセット DRLSE(Li–Xu–Gui–Fox 2010)のエッジ版。再初期化しない。

    φ_t = μ div(d_p(|∇φ|)∇φ) + λ δ_ε(φ) div(g ∇φ/|∇φ|) + α g δ_ε(φ)(φ < 0 が内側、α > 0 で縮む)。
    d_p(s) = p'(s)/s。二重井戸 p2(s) = (1 − cos 2πs)/(2π)²(s ≤ 1)、(s − 1)²/2(s ≥ 1)、単井戸 p1(s) = (s − 1)²/2。
    初期 = 2 値の段差(内側 −c0、外側 +c0、Li の例と同じ)。g = ``edge_stop_g(image, sigma, k)`` の g(``g`` で直接与えても
    よい)。μ の既定は 0.2/dt、CFL 条件 μ dt < 1/4 を満たさなければ ValueError。境界は Li のコードの Neumann。
    エネルギー ε(φ) = μ Σ p(|∇φ|) + λ Σ g δ_ε(φ)|∇φ| + α Σ g H_ε(−φ) も各反復で記録する(実測、門ではない)。
    返り値: ``mask``(φ < 0)、``phi``、``grad``(|φ| ≤ ε の |∇φ| 分位点)、``grad_trace``(record_every ごとの中央値)、
    ``energy``、``n_increase``、``history``、``n_iter``。"""
    op = "drle_evolve"
    im = _image(image, "image", op)
    ins = _mask(init, "init", op, im.shape)
    st = _num(dt, "dt", op, 0.0, 1e3, lo_open=True)
    m = 0.2 / st if mu is None else _num(mu, "mu", op, 0.0, 1e6)
    if m * st >= 0.25:
        raise ValueError("%s: mu * dt = %g violates the CFL condition mu * dt < 1/4" % (op, m * st))
    lam = _num(lambda_, "lambda_", op, -1e6, 1e6)
    al = _num(alpha, "alpha", op, -1e6, 1e6)
    ep = _num(epsilon, "epsilon", op, 0.0, 1e3, lo_open=True)
    sg = _num(sigma, "sigma", op, 0.0, 100.0)
    kk = _num(k, "k", op, 0.0, 1e12, lo_open=True)
    ni = _int(n_iter, "n_iter", op, 0)
    cc = _num(c0, "c0", op, 0.0, 1e6, lo_open=True)
    pot = _choice(potential, "potential", op, ("double_well", "single_well"))
    rec = _int(record_every, "record_every", op, 0)
    if g is None:
        gg = edge_stop_g(im, sigma=sg, k=kk)["g"]
    else:
        gg = _image(g, "g", op)
        if gg.shape != im.shape:
            raise ValueError("%s: g shape differs from the image" % op)
    vy, vx = np.gradient(gg)
    phi = np.where(ins, -cc, cc).astype(np.float64)

    def energy(ph):
        py, px = np.gradient(ph)
        s = np.hypot(px, py)
        pr = _p2(s) if pot == "double_well" else 0.5 * (s - 1.0) ** 2
        return float(m * pr.sum() + lam * np.sum(gg * _drl_dirac(ph, ep) * s) + al * np.sum(gg * _drl_heav(-ph, ep)))

    en = [energy(phi)]
    trace = []
    history: List[np.ndarray] = [phi < 0] if rec else []
    for it in range(ni):
        phi = _neumann(phi)
        py, px = np.gradient(phi)
        s = np.sqrt(px * px + py * py)
        nx = px / (s + 1e-10)
        ny = py / (s + 1e-10)
        curv = _div(nx, ny)
        if pot == "double_well":
            a = (s >= 0) & (s <= 1)
            b = s > 1
            ps = a * np.sin(2 * math.pi * s) / (2 * math.pi) + b * (s - 1.0)
            dps = np.where(ps != 0, ps, 1.0) / np.where(s != 0, s, 1.0)
            reg = _div(dps * px - px, dps * py - py) + _lap(phi)
        else:
            reg = _lap(phi) - curv
        dl = _drl_dirac(phi, ep)
        area = dl * gg
        edge = dl * (vx * nx + vy * ny) + dl * gg * curv
        phi = phi + st * (m * reg + lam * edge + al * area)
        en.append(energy(phi))
        if rec and (it + 1) % rec == 0:
            history.append(phi < 0)
            trace.append(_quantiles_in_band(phi, ep)["q50"])
    e = np.array(en)
    return {"mask": phi < 0, "phi": phi, "grad": _quantiles_in_band(phi, ep), "grad_trace": np.array(trace),
            "energy": e, "n_increase": int(np.count_nonzero(np.diff(e) > 1e-9 * max(1.0, float(np.abs(e).max())))),
            "history": history, "n_iter": ni}


# ───────────────────────────── 8. 平均曲率流 ─────────────────────────────
def _area_from_phi(phi: np.ndarray) -> float:
    """φ の内側の面積の亜画素の見積り: 画素ごとに clip(0.5 − φ/|∇φ|, 0, 1)(界面が画素の中を直線で横切る近似)。"""
    gy, gx = np.gradient(phi)
    s = np.maximum(np.hypot(gx, gy), 1e-12)
    return float(np.clip(0.5 - phi / s, 0.0, 1.0).sum())


def curvature_flow(phi, *, t_end: float = 50.0, dt: float = 0.2, eta: float = 1e-8,
                   record_every: int = 0) -> Dict[str, object]:
    """平均曲率流(曲線短縮流)のレベルセット版 φ_t = |∇φ| div(∇φ/|∇φ|)(φ < 0 が内側、凸な所から縮む)。

    陽的な中心差分: φ_t = (φ_xx φ_y² − 2 φ_x φ_y φ_xy + φ_yy φ_x²) / (φ_x² + φ_y² + η)、刻み dt ≤ 0.25(安定条件)。
    ``phi`` = φ か bool のマスク(符号付き距離に直す)。面積は各刻みで ``clip(0.5 − φ/|∇φ|, 0, 1)`` の和。
    門: 単純閉曲線の囲む面積は dA/dt = −∮ κ ds = −2π(回転数 1、凸でなくても)。円なら r(t)² = r0² − 2t。
    返り値: ``phi``、``mask``、``times``、``areas``、``area_rate``(面積 vs 時間の最小二乗の傾き)、``area_rate_theory`` = −2π、
    ``history``(record_every 刻みごとのマスク)、``n_steps``。"""
    op = "curvature_flow"
    p = _phi_or_mask(phi, "phi", op).copy()
    te = _num(t_end, "t_end", op, 0.0, 1e7, lo_open=True)
    st = _num(dt, "dt", op, 0.0, 0.25, lo_open=True)
    et = _num(eta, "eta", op, 0.0, 1.0, lo_open=True)
    rec = _int(record_every, "record_every", op, 0)
    n = int(math.ceil(te / st))
    if n > MAX_ITER:
        raise ValueError("%s: t_end/dt = %d steps > MAX_ITER=%d" % (op, n, MAX_ITER))
    times = [0.0]
    areas = [_area_from_phi(p)]
    history: List[np.ndarray] = [p < 0] if rec else []
    for i in range(n):
        q = np.pad(p, 1, mode="edge")
        px = 0.5 * (q[1:-1, 2:] - q[1:-1, :-2])
        py = 0.5 * (q[2:, 1:-1] - q[:-2, 1:-1])
        pxx = q[1:-1, 2:] - 2 * p + q[1:-1, :-2]
        pyy = q[2:, 1:-1] - 2 * p + q[:-2, 1:-1]
        pxy = 0.25 * (q[2:, 2:] - q[2:, :-2] - q[:-2, 2:] + q[:-2, :-2])
        num = pxx * py * py - 2 * px * py * pxy + pyy * px * px
        p = p + st * num / (px * px + py * py + et)
        times.append((i + 1) * st)
        areas.append(_area_from_phi(p))
        if rec and (i + 1) % rec == 0:
            history.append(p < 0)
    t = np.array(times)
    a = np.array(areas)
    rate = float(np.polyfit(t, a, 1)[0]) if len(t) >= 2 else float("nan")
    return {"phi": p, "mask": p < 0, "times": t, "areas": a, "area_rate": rate, "area_rate_theory": -2.0 * math.pi,
            "history": history, "n_steps": n}

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""radiosity3d — 3-D form factors, progressive radiosity (Cohen et al. 1988) and an inspection render that counts interreflection without losing the photometric truth (numpy only).

ユーザー(2026-10-15)「本当にリアルに近づけるなら、ある程度は収束型の演算もいるかもしれない」。

``optscene.render_optscene`` は検査用で、実在の照明器具を物理単位で置いて**直接光だけ**を数える
(測光に根拠があり、真値と突き合わせられる)。``optscene.render_studio`` は多重反射まで解くが、
明るさの絶対値に意味が無い(見せる絵)。``lighttransport`` のラジオシティは 2-D の押し出し形状
だけ。凹んだ部品 —— 加工ポケット・内角・箱の隅 —— の実写に直接光だけのモデルを合わせると、
相互反射の分が反射率や照明の強さに**吸収されて、もっともらしく合ってしまう**。本モジュールは
その間を埋める: optscene のシーンと illumdesign の照明をそのまま受け、直接光の測光を 1 桁も変えずに、
相互反射を n 回まで、または収束まで足し、**収束した証拠**(残エネルギーの履歴・反復数・
converged)と「何回数えれば足りるか」を返す。

7 の op(並びは計算の順):

  * :func:`form_factor_parallel_rects` — Howell の表 C-11(平行で正対する同じ長方形)の閉形式。
  * :func:`form_factor_perpendicular_rects` — Howell の表 C-14(辺を共有して直角に交わる長方形)の閉形式。
  * :func:`form_factor_polygons` — 平らな凸多角形(三角形・四角形)どうしの形態係数を数値で。
    受け側は Gauss–Legendre の点、送り側は点から多角形への Lambert の閉形式(輪郭の和)。
  * :func:`radiosity_patches` — パッチの組(``rad_patches`` の印つき table)を、多角形の配列か
    optscene のシーン(箱・箱をくり抜いたポケット・有限の板)から作る。
  * :func:`form_factor_matrix` — パッチの組の全対の形態係数(遮蔽はシーンの光線で判定)。
  * :func:`radiosity_progressive_3d` — Cohen ら 1988 の漸進ラジオシティ(shooting、式 7・8)。
    未放射エネルギー ΔB·A が最大のパッチから撃ち、残エネルギー Σ ΔB·A の履歴を返す。
  * :func:`render_optscene_gi` — 検査用の多重反射描画。直接光は ``render_optscene`` と同じ式・同じ値
    (反射 0 回で一致を門にしてある)、相互反射は n 回の Neumann 和か漸進法で収束まで、直接光だけの
    描画との差の地図、反射の回数に対する観測収束比と GCI 型の残差の見積もり。

★設計判断(出典が決めていないところ):
  * **止め方**。Cohen 1988 は "until the solution converges to within the desired tolerance" と
    書くだけで閾値を数値で決めていない(§3.1 の擬似コード、本文で確認)。本モジュールは
    残エネルギー Σ ΔB_i A_i が初期の総エネルギー Σ E_i A_i の ``tol`` 倍以下になったら止める ——
    これは**こちらの判断**で、未放射の光が全部吸収されずに戻ってきても、各パッチの誤差は
    この残エネルギーで上から抑えられる(全部が 1 枚に集まる最悪の場合)。止まらなければ
    ``converged=False`` で返し、値を「収束した」とは言わない。
  * **相反則**。数値の形態係数は A_i F_ij = A_j F_ji を求積の精度でしか満たさない。
    ``form_factor_matrix`` は既定で面積で重みづけた行列を対称化して相反則を厳密に入れる
    (``symmetric=False`` で生の値)。shooting の式 8 の F_ij A_i/A_j はそのまま F_ji になる。
  * **同点**。撃つパッチの選択は ΔB·A を相対 1e-12 に丸めてから最大を取り、同点なら宣言順
    (番号の小さい方)。乱数は引かない。
  * **反射回数の収束**は格子の細分ではなく等比級数(Neumann 和)の収束なので、Roache の
    観測収束次数 p は定義できない。代わりに隣り合う増分の比 g(観測収束比、p の類似物)と、
    等比の残り Δ_k g/(1 − g) に安全係数 1.25(Roache 1994 の 3 水準の値)を掛けた GCI 型の
    見積もりを返す。収束した解と比べた実際の誤差も並べる(見積もりが楽観していないかの門)。

真値(``tests/test_radiosity3d.py``):
  * Howell C-11 の X = Y = 1 で 0.199825、C-14 の H = W = 1 で 0.200044(Howell のカタログの表の値)。
    数値の form_factor_polygons が両方の閉形式と一致、相反則、閉じた箱の行和 = 1。
  * 漸進法が逆行列の解(``numpy.linalg.solve``)と一致。押し出した V 溝の中央の断面が
    ``lighttransport.transport_matrix_radiosity``(2-D、crossed-strings の厳密解)へ、
    長さを伸ばすほど近づく。
  * 反射 0 回の描画が ``optscene.render_optscene`` と一致(同じ照明・同じシーン)。

★正直に書いておくこと(範囲):
  * **Lambert(完全拡散)だけ**。導体・誘電体・加工目(finish)・欠陥(defect)を持つ部品は
    拒む(fail-closed)。鏡面の相互反射の真値は ``gi_render``(Mitsuba、optional)の領分。
  * シーンの形は 箱 / 箱から箱をくり抜いた差集合(ポケット・角穴)/ 有限の板 だけ。
    球・円筒・入れ子の差集合は拒む。無限の板は**反射率 0 のときだけ**受け付ける(背景の黒い
    台。メッシュに入れずに遮蔽物としてだけ使う —— 反射する無限の板は有限に切れないので拒む)。
  * パッチ内のラジオシティは一様(区分一定)。画素の相互反射の照度は、パッチのラジオシティを
    画素の点から点-多角形の閉形式で集め直す(final gather、遮蔽はパッチ中心への光線 1 本)。
    パッチの一部だけが隠れる配置では、その遮蔽は中心の 1 本で 0/1 に丸まる。
  * 直接光の照度はパッチの中では受け側の求積点で平均する(``shadows=True`` の影つき)。

出典:
  * M. F. Cohen, S. E. Chen, J. R. Wallace, D. P. Greenberg, "A Progressive Refinement Approach to
    Fast Radiosity Image Generation", Computer Graphics 22(4) (SIGGRAPH '88), pp. 75–84。§3.1 の
    式 (5)–(8) と擬似コード(ΔRad = ρ_j ΔB_i F_ij A_i/A_j、ΔB_i = 0 に戻す)、§3.2 の「ΔB_i A_i が
    最大のパッチから撃つ」を本文で読んだ。式 (10)–(13) の ambient 項は表示用の推定なので入れていない。
  * J. R. Howell, "A Catalog of Radiation Heat Transfer Configuration Factors"(Univ. of Texas at
    Austin、web 版)の C-11 と C-14 の式と定義(X = a/c、Y = b/c / H = h/l、W = w/l)を読んだ。
  * 点から多角形への形態係数の輪郭和は Lambert(1760)の式で、教科書の標準形
    F = (1/2π) Σ_k n·Γ_k(Γ_k は辺 k が張る角を大きさに持つ法線)。
  * P. J. Roache, "Perspective: A Method for Uniform Reporting of Grid Refinement Studies",
    J. Fluids Eng. 116 (1994)。安全係数 1.25 だけを借りた(上の★のとおり、級数への転用はこちらの判断)。
"""
from __future__ import annotations

import collections
import hashlib
import math

import numpy as np

import optscene as _os

__all__ = [
    "form_factor_parallel_rects",
    "form_factor_perpendicular_rects",
    "form_factor_polygons",
    "radiosity_patches",
    "form_factor_matrix",
    "radiosity_progressive_3d",
    "render_optscene_gi",
]

#: パッチの組であることを示す印(消費する op が fail-closed で確かめる)。
PATCHES_KIND = "rad_patches"
#: 漸進ラジオシティの結果の印。
SOLUTION_KIND = "rad_solution"
#: 多重反射描画の結果の印。
RENDER_KIND = "gi_render"
#: パッチ数の上限(P×P の行列を確保する前に拒む)。
MAX_PATCHES = 6000
#: GCI の安全係数(Roache 1994、3 水準以上の細分)。
GCI_SAFETY = 1.25
#: 同点の判定に使う相対の丸め(撃つ順の選択)。
_TIE_ROUND = 1e-12
_TWO_PI = 2.0 * math.pi
_GEOM_CACHE: "collections.OrderedDict[str, dict]" = collections.OrderedDict()
_GEOM_CACHE_MAX = 4


# --------------------------------------------------------------------------- #
# 入力の検証(fail-closed)
# --------------------------------------------------------------------------- #
def _num(v, name, op, lo=None, hi=None, lo_open=False):
    if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, v))
    v = float(v)
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if lo is not None and (v < lo or (lo_open and v <= lo)):
        raise ValueError("%s: %s must be %s %g, got %r" % (op, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and v > hi:
        raise ValueError("%s: %s must be <= %g, got %r" % (op, name, hi, v))
    return v


def _int(v, name, op, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    v = int(v)
    if not lo <= v <= hi:
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, v))
    return v


def _poly_array(p, name, op):
    """(V, 3) または (N, V, 3) の多角形 → (N, 4, 3)(三角形は最後の頂点を重ねて 4 点に)。"""
    a = np.asarray(p, dtype=np.float64)
    if a.ndim == 2:
        a = a[None]
    if a.ndim != 3 or a.shape[-1] != 3 or a.shape[1] not in (3, 4):
        raise ValueError("%s: %s must be (3|4, 3) or (N, 3|4, 3) vertices, got shape %s" % (op, name, a.shape))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s has NaN or inf" % (op, name))
    if a.shape[1] == 3:
        a = np.concatenate([a, a[:, 2:3]], axis=1)
    return a


def _newell(polys):
    """(N, 4, 3) → 面積ベクトル(Newell の方法)。大きさ = 面積、向き = 右手の法線。"""
    s = np.zeros(polys.shape[:1] + (3,))
    for k in range(4):
        a, b = polys[:, k], polys[:, (k + 1) % 4]
        s += np.cross(a, b)
    return 0.5 * s


def _check_planar_convex(polys, op, name):
    """平らで凸、面積が正であることを確かめ、(normals, areas, centers) を返す。"""
    av = _newell(polys)
    area = np.linalg.norm(av, axis=-1)
    if (area <= 0.0).any():
        raise ValueError("%s: %s has a degenerate (zero-area) polygon" % (op, name))
    n = av / area[:, None]
    size = np.sqrt(area)
    off = np.abs(((polys - polys[:, :1]) * n[:, None, :]).sum(-1)).max(-1)
    if (off > 1e-9 * np.maximum(size, 1.0)).any():
        raise ValueError("%s: %s has a non-planar quad (vertex off the plane by %.3g)" % (op, name, off.max()))
    # 凸: 各頂点で隣の辺の外積が法線と同じ向き(重なった頂点の 0 は許す)
    for k in range(4):
        e1 = polys[:, (k + 1) % 4] - polys[:, k]
        e2 = polys[:, (k + 2) % 4] - polys[:, (k + 1) % 4]
        turn = (np.cross(e1, e2) * n).sum(-1)
        if (turn < -1e-12 * np.maximum(area, 1.0)).any():
            raise ValueError("%s: %s has a non-convex (or self-crossing) polygon" % (op, name))
    return n, area, _centroids(polys, area)


def _centroids(polys, area):
    """多角形の重心(三角形 2 枚に分けて面積で重みづけ)。"""
    a, b, c, d = polys[:, 0], polys[:, 1], polys[:, 2], polys[:, 3]
    a1 = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=-1)
    a2 = 0.5 * np.linalg.norm(np.cross(c - a, d - a), axis=-1)
    g1, g2 = (a + b + c) / 3.0, (a + c + d) / 3.0
    w = np.maximum(a1 + a2, 1e-300)
    return (a1[:, None] * g1 + a2[:, None] * g2) / w[:, None]


# --------------------------------------------------------------------------- #
# 閉形式(Howell の表)
# --------------------------------------------------------------------------- #
def form_factor_parallel_rects(a=1.0, b=1.0, c=1.0):
    """View factor between two identical, parallel, directly opposed rectangles a × b at distance c (Howell's catalogue C-11, closed form).

    With ``X = a/c`` and ``Y = b/c``::

        F = 2/(π X Y) { ln[ (1+X²)(1+Y²)/(1+X²+Y²) ]^(1/2)
                        + X √(1+Y²) atan(X/√(1+Y²)) + Y √(1+X²) atan(Y/√(1+X²))
                        − X atan X − Y atan Y }

    ``X = Y = 1`` (unit squares one unit apart) gives 0.199825. Symmetric in the
    two rectangles (equal areas), so reciprocity is trivially ``F_12 = F_21``.

    Returns the view factor (``measurement``, dimensionless, in ``(0, 1)``).

    **Raises** ``ValueError``: a non-positive or non-finite length.
    """
    op = "form_factor_parallel_rects"
    a, b, c = (_num(v, n, op, lo=0.0, lo_open=True) for v, n in ((a, "a"), (b, "b"), (c, "c")))
    X, Y = a / c, b / c
    x2, y2 = X * X, Y * Y
    s = 0.5 * math.log((1.0 + x2) * (1.0 + y2) / (1.0 + x2 + y2))
    s += X * math.sqrt(1.0 + y2) * math.atan(X / math.sqrt(1.0 + y2))
    s += Y * math.sqrt(1.0 + x2) * math.atan(Y / math.sqrt(1.0 + x2))
    s -= X * math.atan(X) + Y * math.atan(Y)
    return 2.0 / (math.pi * X * Y) * s


def form_factor_perpendicular_rects(h=1.0, w=1.0, length=1.0):
    """View factor from a rectangle w × l to a rectangle h × l sharing the edge of length l at 90° (Howell's catalogue C-14, closed form).

    With ``H = h/l`` and ``W = w/l`` (surface 1 is the ``w`` side, surface 2 the ``h``
    side)::

        F_12 = 1/(π W) ( W atan(1/W) + H atan(1/H) − √(H²+W²) atan(1/√(H²+W²))
               + ¼ ln{ (1+W²)(1+H²)/(1+W²+H²)
                       · [W²(1+W²+H²)/((1+W²)(W²+H²))]^(W²)
                       · [H²(1+H²+W²)/((1+H²)(H²+W²))]^(H²) } )

    ``H = W = 1`` (two unit squares on a common edge) gives 0.200044. Reciprocity:
    ``w F_12 = h F_21`` (``form_factor_perpendicular_rects(w, h, l)`` is ``F_21``).

    Returns the view factor ``F_12`` (``measurement``).

    **Raises** ``ValueError``: a non-positive or non-finite length.
    """
    op = "form_factor_perpendicular_rects"
    h, w, L = (_num(v, n, op, lo=0.0, lo_open=True) for v, n in ((h, "h"), (w, "w"), (length, "length")))
    H, W = h / L, w / L
    h2, w2 = H * H, W * W
    s2 = h2 + w2
    r = math.sqrt(s2)
    t = W * math.atan(1.0 / W) + H * math.atan(1.0 / H) - r * math.atan(1.0 / r)
    lg = math.log((1.0 + w2) * (1.0 + h2) / (1.0 + s2))
    lg += w2 * math.log(w2 * (1.0 + s2) / ((1.0 + w2) * s2))
    lg += h2 * math.log(h2 * (1.0 + s2) / ((1.0 + h2) * s2))
    return (t + 0.25 * lg) / (math.pi * W)


# --------------------------------------------------------------------------- #
# 数値の形態係数(点 → 多角形の閉形式 + 受け側の Gauss 求積)
# --------------------------------------------------------------------------- #
def _cross(a, b):
    """np.cross の速い代わり(最後の軸が 3)。"""
    return np.stack([a[..., 1] * b[..., 2] - a[..., 2] * b[..., 1],
                     a[..., 2] * b[..., 0] - a[..., 0] * b[..., 2],
                     a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]], axis=-1)


def _gauss01(n):
    x, w = np.polynomial.legendre.leggauss(int(n))
    return 0.5 * (x + 1.0), 0.5 * w


def _quad_points(polys, n):
    """(N, 4, 3) の四角形(三角形は退化した四角形)の上の n×n の Gauss 点と重み(和 = 面積)。"""
    s, ws = _gauss01(n)
    S, T = np.meshgrid(s, s, indexing="ij")
    W = np.outer(ws, ws).ravel()
    S, T = S.ravel()[None, :, None], T.ravel()[None, :, None]
    v0, v1, v2, v3 = (polys[:, k][:, None, :] for k in range(4))
    X = (1 - S) * (1 - T) * v0 + S * (1 - T) * v1 + S * T * v2 + (1 - S) * T * v3
    dXs = (1 - T) * (v1 - v0) + T * (v2 - v3)
    dXt = (1 - S) * (v3 - v0) + S * (v2 - v1)
    J = np.linalg.norm(np.cross(dXs, dXt), axis=-1)
    return X, W[None, :] * J


def _point_polygon(x, nx, polys):
    """点 x(法線 nx)から多角形への微小面-有限面の形態係数(Lambert の輪郭和)。

    x (M, 3), nx (M, 3), polys (M, 4, 3) は行ごとに対。多角形は受け側の半球の内側に
    あること(呼び手が確かめる)。向きは多角形の頂点の巡り方に依らない(絶対値)。
    """
    R = polys - x[:, None, :]
    R2 = np.roll(R, -1, axis=1)
    c = _cross(R, R2)
    cn = np.sqrt(np.einsum("mkc,mkc->mk", c, c))
    ang = np.arctan2(cn, np.einsum("mkc,mkc->mk", R, R2))
    cdotn = np.einsum("mkc,mc->mk", c, nx)
    w = np.where(cn > 1e-300, ang / np.maximum(cn, 1e-300), 0.0)
    return np.abs((w * cdotn).sum(-1)) / _TWO_PI


def _point_polygon_sampled(x, nx, polys, n=10):
    """多角形が受け側の面をまたぐときの代わり: 多角形の上の n×n 点で cos を 0 で切って数値積分。"""
    q, w = _quad_points(polys, n)                                   # (M, Q, 3), (M, Q)
    pn = _newell(polys)
    pn = pn / np.maximum(np.linalg.norm(pn, axis=-1, keepdims=True), 1e-300)
    d = q - x[:, None, :]
    r2 = np.maximum((d * d).sum(-1), 1e-300)
    r = np.sqrt(r2)
    ci = np.clip((d * nx[:, None, :]).sum(-1) / r, 0.0, None)
    cj = np.abs((d * pn[:, None, :]).sum(-1)) / r
    return (w * ci * cj / (math.pi * r2)).sum(-1)


def _visible(occluders, o, t_pts):
    """o から t_pts への線分が遮られていなければ True(o, t_pts は (M, 3))。"""
    if not occluders:
        return np.ones(o.shape[0], bool)
    v = t_pts - o
    dist = np.linalg.norm(v, axis=-1)
    d = v / np.maximum(dist, 1e-300)[:, None]
    start = o + 1e-4 * d
    reach = dist - 1e-4
    tol = 1e-6 * np.maximum(dist, 1.0) + 1e-5
    vis = np.ones(o.shape[0], bool)
    for obj in occluders:
        t = _os._hit(obj, start, d)
        vis &= ~(t < reach - tol)
    return vis


def _ff_pairs(xq, nxq, wq, area_i, polys_j, cen_j, n_j, occluders, eps):
    """受け側の求積点(Q 個、重み wq)から多角形 j への F_ij(行ごとの対、M 組)。

    xq (M, Q, 3) nxq (M, 3) wq (M, Q)。前面判定・またぎ・遮蔽を含めて (M,) を返す。
    """
    M, Q = wq.shape
    out = np.zeros(M)
    for q in range(Q):
        x = xq[:, q, :]
        front_j = ((x - cen_j) * n_j).sum(-1) > eps                     # 送り側の表から見えている
        sd = ((polys_j - x[:, None, :]) * nxq[:, None, :]).sum(-1)       # 受け側の面からの高さ
        any_front = (sd > eps).any(-1)
        straddle = (sd < -eps).any(-1) & any_front
        ok = front_j & any_front
        if not ok.any():
            continue
        f = np.zeros(M)
        clean = ok & ~straddle
        if clean.any():
            f[clean] = _point_polygon(x[clean], nxq[clean], polys_j[clean])
        if (ok & straddle).any():
            m = ok & straddle
            f[m] = _point_polygon_sampled(x[m], nxq[m], polys_j[m])
        if occluders:
            m = f > 0.0
            if m.any():
                vis = _visible(occluders, x[m], cen_j[m])
                f[np.flatnonzero(m)[~vis]] = 0.0
        out += wq[:, q] * f
    return out / area_i


def form_factor_polygons(poly_i, poly_j, n_quad=8, occluders=None):
    """View factor F_ij between two flat convex polygons (triangles or quads) in 3-D, numerically.

    ``F_ij = (1/A_i) ∫_{A_i} F_{dA→A_j} dA``: the inner factor from a point to the
    polygon ``j`` is Lambert's closed contour sum ``(1/2π) Σ_k n·Γ_k`` (exact, no
    quadrature), the outer integral over ``i`` an ``n_quad × n_quad`` Gauss–Legendre
    rule on the (bilinearly mapped) polygon. A polygon that straddles the receiver's
    plane is integrated by points with the cosine clipped at 0 instead. Each polygon
    is ``(3, 3)`` or ``(4, 3)`` vertices ``(x, y, z)`` in order around its edge; the
    sides that face each other count (the vertex order does not matter).

    *occluders* is ``None`` (nothing in between — true inside a convex cavity) or an
    optscene scene (list of ``scene_*`` dicts): each quadrature point is then tested
    with one ray to the centre of ``j``.

    Gates: Howell's C-11 (0.199825) and C-14 (0.200044) to the quadrature accuracy,
    reciprocity ``A_i F_ij = A_j F_ji``.

    Returns ``F_ij`` (``measurement``).

    **Raises** ``ValueError``: an empty polygon, or one that is not ``(3|4, 3)``,
    non-finite, degenerate, non-planar or non-convex; *n_quad* not an integer in ``[1, 64]``;
    *occluders* that are not optscene primitives.
    """
    op = "form_factor_polygons"
    pi_ = _poly_array(poly_i, "poly_i", op)
    pj_ = _poly_array(poly_j, "poly_j", op)
    if pi_.shape[0] != 1 or pj_.shape[0] != 1:
        raise ValueError("%s: give one polygon each (use form_factor_matrix for many)" % op)
    nq = _int(n_quad, "n_quad", op, 1, 64)
    occ = None if occluders is None else _os._check_scene(occluders)
    ni, ai, _ = _check_planar_convex(pi_, op, "poly_i")
    nj, aj, cj = _check_planar_convex(pj_, op, "poly_j")
    xq, wq = _quad_points(pi_, nq)
    eps = 1e-12 * max(1.0, float(np.abs(np.concatenate([pi_, pj_])).max()))
    # 受け側の法線は j の方を向く側を取る
    if float(((cj - pi_.mean(1)) * ni).sum()) < 0.0:
        ni = -ni
    if float(((pi_.mean(1) - cj) * nj).sum()) < 0.0:
        nj = -nj
    return float(_ff_pairs(xq, ni, wq, ai, pj_, cj, nj, occ, eps)[0])


# --------------------------------------------------------------------------- #
# パッチの組
# --------------------------------------------------------------------------- #
def _check_patches(p, op):
    if not isinstance(p, dict) or p.get("kind") != PATCHES_KIND:
        raise ValueError("%s: expected a radiosity_patches table (kind=%r), got %s"
                         % (op, PATCHES_KIND, type(p).__name__ if not isinstance(p, dict) else p.get("kind")))
    for key in ("polygons", "normals", "areas", "centers", "albedo"):
        if key not in p:
            raise ValueError("%s: the patches table is missing %r" % (op, key))
    return p


def _material_albedo(obj, i, op):
    mat = obj.get("material") or {}
    if mat.get("kind") != "lambert":
        raise ValueError("%s: scene[%d] is %r — only Lambertian materials are supported (specular "
                         "interreflection needs gi_render / Mitsuba)" % (op, i, mat.get("kind")))
    for key in ("defect", "finish"):
        if obj.get(key) is not None:
            raise ValueError("%s: scene[%d] carries a surface %s — not modelled by the radiosity patches "
                             "(render it with render_optscene, direct light only)" % (op, i, key))
    return np.asarray(mat["albedo"], float).reshape(3)


def _box_bounds(obj):
    return obj["c"] - obj["h"], obj["c"] + obj["h"]


def _inside_solid(obj, p, closed, eps):
    """p (N, 3) が立体 obj(箱・箱の差集合)の内側か。closed=True は境界も内側に数える。"""
    if obj["kind"] == "box":
        lo, hi = _box_bounds(obj)
        if closed:
            return ((p >= lo - eps) & (p <= hi + eps)).all(-1)
        return ((p > lo + eps) & (p < hi - eps)).all(-1)
    if obj["kind"] == "difference":
        return _inside_solid(obj["a"], p, closed, eps) & ~_inside_solid(obj["b"], p, not closed, eps)
    return np.zeros(p.shape[0], bool)


def _face_rects(lo, hi, outward=True):
    """箱の 6 面: (法線の軸, 符号, 座標, (u 軸, v 軸), (u0, u1), (v0, v1))。"""
    out = []
    for ax in range(3):
        u, v = [a for a in range(3) if a != ax]
        for sgn, val in ((-1.0, lo[ax]), (1.0, hi[ax])):
            s = sgn if outward else -sgn
            out.append((ax, s, float(val), (u, v), (float(lo[u]), float(hi[u])), (float(lo[v]), float(hi[v]))))
    return out


def _splits(a0, a1, breaks, size):
    """[a0, a1] を breaks で切り、各区間を size 以下の等分に。"""
    pts = [a0] + sorted(b for b in breaks if a0 < b < a1) + [a1]
    edges = [a0]
    for s, e in zip(pts[:-1], pts[1:]):
        if e - s <= 0.0:
            continue
        k = max(1, int(math.ceil((e - s) / size - 1e-9)))
        edges.extend(list(np.linspace(s, e, k + 1)[1:]))
    return np.asarray(edges)


def _scene_patches(scene, patch_mm, op, outer_mm=None):
    scene = _os._check_scene(scene)
    breaks = [set(), set(), set()]
    solids = []
    for i, obj in enumerate(scene):
        k = obj["kind"]
        if k == "plane":
            if obj["half"] is None:
                if np.any(np.asarray((obj.get("material") or {}).get("albedo", [1.0]), float) != 0.0):
                    raise ValueError("%s: scene[%d] is an infinite plane with a non-zero albedo — it cannot be "
                                     "split into patches (give half_size_mm, or albedo 0 for a black stage)" % (op, i))
                continue
            _material_albedo(obj, i, op)
            hx, hy = obj["half"]
            breaks[0].update((-hx, hx))
            breaks[1].update((-hy, hy))
            breaks[2].add(obj["z"])
        elif k == "box":
            _material_albedo(obj, i, op)
            lo, hi = _box_bounds(obj)
            for ax in range(3):
                breaks[ax].update((lo[ax], hi[ax]))
            solids.append(i)
        elif k == "difference":
            _material_albedo(obj, i, op)
            if obj["a"]["kind"] != "box" or obj["b"]["kind"] != "box":
                raise ValueError("%s: scene[%d] is a difference of %s minus %s — only a box minus a box "
                                 "(a pocket or a rectangular hole) is supported"
                                 % (op, i, obj["a"]["kind"], obj["b"]["kind"]))
            for part in (obj["a"], obj["b"]):
                lo, hi = _box_bounds(part)
                for ax in range(3):
                    breaks[ax].update((lo[ax], hi[ax]))
            solids.append(i)
        else:
            raise ValueError("%s: scene[%d] is a %s — the radiosity patches support boxes, a box minus a box "
                             "and finite planes only" % (op, i, k))
    scale = max(1.0, max((abs(b) for bs in breaks for b in bs), default=1.0))
    eps = 1e-9 * scale
    contact_planes = [float(o["z"]) for o in scene if o["kind"] == "plane" and o["half"] is None]
    polys, labels, regions, albedo = [], [], [], []

    def add_face(ax, sgn, val, uv, ur, vr, i, region, keep):
        u, v = uv
        size = patch_mm if (region == "cavity" or outer_mm is None) else outer_mm
        ue = _splits(ur[0], ur[1], breaks[u], size)
        ve = _splits(vr[0], vr[1], breaks[v], size)
        U0, V0 = np.meshgrid(ue[:-1], ve[:-1], indexing="ij")
        U1, V1 = np.meshgrid(ue[1:], ve[1:], indexing="ij")
        n = U0.size
        cen = np.zeros((n, 3))
        cen[:, ax] = val
        cen[:, u] = 0.5 * (U0 + U1).ravel()
        cen[:, v] = 0.5 * (V0 + V1).ravel()
        mask = keep(cen)
        for pl in contact_planes:                       # 黒い無限の台に接した面(箱の底)は光を交わさない
            if sgn < 0.0 and ax == 2:
                mask &= ~(np.abs(cen[:, 2] - pl) <= eps)
        for other in solids:
            if other != i:
                mask &= ~_inside_solid(scene[other], cen, True, eps)
        if not mask.any():
            return
        corners = []
        for (cu, cv) in ((U0, V0), (U1, V0), (U1, V1), (U0, V1)):
            c = np.zeros((n, 3))
            c[:, ax] = val
            c[:, u] = cu.ravel()
            c[:, v] = cv.ravel()
            corners.append(c)
        P = np.stack(corners, axis=1)[mask]
        # 頂点の巡りを法線(sgn·e_ax)の右手に揃える
        nrm = _newell(P)
        flip = nrm[:, ax] * sgn < 0.0
        P[flip] = P[flip][:, ::-1]
        polys.append(P)
        labels.extend([i] * len(P))
        regions.extend([region] * len(P))
        albedo.extend([_material_albedo(scene[i], i, op)] * len(P))

    for i, obj in enumerate(scene):
        if obj["kind"] == "plane":
            if obj["half"] is None:
                continue
            hx, hy = obj["half"]
            add_face(2, 1.0, obj["z"], (0, 1), (-hx, hx), (-hy, hy), i, "plane",
                     lambda c: np.ones(len(c), bool))
        elif obj["kind"] == "box":
            lo, hi = _box_bounds(obj)
            for f in _face_rects(lo, hi):
                add_face(*f, i, "outer", lambda c: np.ones(len(c), bool))
        else:
            A, B = obj["a"], obj["b"]
            lo, hi = _box_bounds(A)
            for f in _face_rects(lo, hi):
                add_face(*f, i, "outer", lambda c, B=B: ~_inside_solid(B, c, True, eps))
            lo, hi = _box_bounds(B)
            for f in _face_rects(lo, hi, outward=False):
                add_face(*f, i, "cavity", lambda c, A=A: _inside_solid(A, c, False, eps))
    if not polys:
        raise ValueError("%s: the scene yields no patches" % op)
    return (np.concatenate(polys), np.asarray(labels, int), np.asarray(regions), np.asarray(albedo, float), scene)


def radiosity_patches(polygons=None, albedo=None, scene=None, patch_mm=2.0, outer_mm=None):
    """Build a set of flat radiosity patches (``rad_patches`` table) from polygons or from an optscene scene.

    Either *polygons* — ``(N, 3|4, 3)`` flat convex triangles or quads, one patch each,
    vertices in order around the edge, normal = right-hand rule (the side that emits) —
    with *albedo* a scalar, ``(N,)`` or ``(N, 3)`` (RGB) in ``[0, 1]`` (``None`` = 0.5); or *scene* —
    an optscene scene (``scene_box``, ``scene_difference`` of a box minus a box, finite
    ``scene_plane``; an infinite plane only with albedo 0) whose Lambertian faces are cut
    into rectangles no larger than *patch_mm* (cut also at every other face's plane, so
    no patch straddles another face; *outer_mm*, when given, is the size used on every face
    that is not the inside of a pocket — the outside of a part rarely exchanges light with
    anything, so it can be coarse)
    no patch straddles another face). Faces in contact with another solid are dropped.
    Albedo then comes from each primitive's material (passing *albedo* too is refused —
    two sources for one number).

    Returns a dict (``table``) with ``kind = "rad_patches"``, ``polygons`` (N, 4, 3),
    ``normals`` (N, 3), ``areas`` (N,), ``centers`` (N, 3), ``albedo`` (N, 3),
    ``labels`` (N,) (scene index, or -1), ``regions`` (N,) (``"outer"`` / ``"cavity"`` /
    ``"plane"`` / ``"polygon"``) and ``occluders`` (the scene, or ``None``).

    **Raises** ``ValueError``: both or neither of *polygons* / *scene* (an empty polygon
    array or scene included); *albedo* given with *scene*; a polygon that is degenerate, non-planar or non-convex; an albedo outside ``[0, 1]`` or of the
    wrong shape; a scene primitive that is not supported (sphere, cylinder, nested
    difference, reflective infinite plane) or not Lambertian; more than 6000 patches.
    """
    op = "radiosity_patches"
    if (polygons is None) == (scene is None):
        raise ValueError("%s: give exactly one of polygons= or scene=" % op)
    if scene is not None:
        if albedo is not None:
            raise ValueError("%s: albedo comes from the scene's materials — do not pass albedo= with scene=" % op)
        pm = _num(patch_mm, "patch_mm", op, lo=0.0, lo_open=True)
        om = None if outer_mm is None else _num(outer_mm, "outer_mm", op, lo=0.0, lo_open=True)
        polys, labels, regions, alb, occ = _scene_patches(scene, pm, op, om)
    else:
        polys = _poly_array(polygons, "polygons", op)
        a = np.asarray(0.5 if albedo is None else albedo, dtype=np.float64)
        if a.ndim == 0:
            a = np.full((polys.shape[0], 3), float(a))
        elif a.ndim == 1 and a.shape[0] == polys.shape[0]:
            a = np.repeat(a[:, None], 3, axis=1)
        if a.shape != (polys.shape[0], 3):
            raise ValueError("%s: albedo must be a scalar, (N,) or (N, 3), got shape %s" % (op, a.shape))
        alb = a
        labels = np.full(polys.shape[0], -1)
        regions = np.full(polys.shape[0], "polygon")
        occ = None
    if not np.isfinite(alb).all() or (alb < 0.0).any() or (alb > 1.0).any():
        raise ValueError("%s: albedo must be finite and in [0, 1] (energy conservation)" % op)
    if polys.shape[0] > MAX_PATCHES:
        raise ValueError("%s: %d patches (cap %d) — raise patch_mm" % (op, polys.shape[0], MAX_PATCHES))
    n, area, cen = _check_planar_convex(polys, op, "polygons")
    return {"kind": PATCHES_KIND, "polygons": polys, "normals": n, "areas": area, "centers": cen,
            "albedo": alb, "labels": labels, "regions": regions, "occluders": occ,
            "patch_mm": None if scene is None else float(patch_mm),
            "outer_mm": None if (scene is None or outer_mm is None) else float(outer_mm)}


# --------------------------------------------------------------------------- #
# 全対の形態係数
# --------------------------------------------------------------------------- #
def _candidates(polys, normals, eps):
    """向き合っている対: j の頂点のどれかが i の面の前、i の頂点のどれかが j の面の前(背中合わせ・同じ面は除く)。"""
    sd_ji = np.einsum("jkc,ic->ijk", polys, normals) - (normals * polys[:, 0]).sum(-1)[:, None, None]
    front_j_of_i = (sd_ji > eps * 10).any(-1)
    cand = front_j_of_i & front_j_of_i.T
    np.fill_diagonal(cand, False)
    return cand


def _ff_matrix(polys, normals, areas, centers, n_quad, occluders, chunk=60000, far_ratio=None,
               memory_budget_mb=256.0):
    P = polys.shape[0]
    scale = max(1.0, float(np.abs(polys).max()))
    eps = 1e-12 * scale
    F = np.zeros((P, P))
    xq, wq = _quad_points(polys, n_quad)
    # 遠い対(中心間の距離 > far_ratio x 大きい方のパッチの差し渡し)は受け側を重心 1 点で代表する。
    # 点 → 多角形は閉形式のままなので、落ちるのは受け側の面の上での変化だけ(距離の 2 乗で小さくなる)。
    diam = np.sqrt(2.0 * areas)
    # _candidates の einsum と平面オフセットの減算は、ともに (P, P, 4) の
    # float64 を生かす。式のピーク 2 * P * P * 4 * 8 byte を割当て前に判定する。
    full_candidate_bytes = 64 * P * P
    block_candidates = full_candidate_bytes > memory_budget_mb * 1024.0 ** 2
    plane = (normals * polys[:, 0]).sum(-1)
    candidate_ranges = range(0, P, 256) if block_candidates else (0,)
    for first in candidate_ranges:
        if not block_candidates:
            I, J = np.nonzero(_candidates(polys, normals, eps))
            stop = P
        else:
            stop = min(first + 256, P)
            pb, nb = polys[first:stop], normals[first:stop]
            front_j = (np.einsum("jkc,ic->ijk", polys, nb) - plane[first:stop, None, None] > eps * 10).any(-1)
            front_i = (np.einsum("ikc,jc->ijk", pb, normals) - plane[None, :, None] > eps * 10).any(-1)
            cand = front_j & front_i
            cand[np.arange(stop - first), np.arange(first, stop)] = False
            ib, J = np.nonzero(cand)
            I = ib + first
        far = np.zeros(len(I), bool)
        if far_ratio is not None:
            dist = np.linalg.norm(centers[I] - centers[J], axis=-1)
            far = dist > far_ratio * np.maximum(diam[I], diam[J])
        for sel, xs, ws in ((~far, xq, wq), (far, centers[:, None, :], areas[:, None])):
            Is, Js = I[sel], J[sel]
            for s in range(0, len(Is), chunk):
                ii, jj = Is[s:s + chunk], Js[s:s + chunk]
                F[ii, jj] = _ff_pairs(xs[ii], normals[ii], ws[ii], areas[ii], polys[jj], centers[jj], normals[jj],
                                      occluders, eps)
    return F


def form_factor_matrix(patches, n_quad=3, symmetric=True, far_ratio=8.0, memory_budget_mb=256.0):
    """All patch-to-patch view factors F_ij of a ``radiosity_patches`` set (occlusion by the scene's rays).

    Each pair is :func:`form_factor_polygons` (``n_quad × n_quad`` Gauss points on the
    receiver, Lambert's contour sum to the sender) restricted to pairs that face each
    other; when the patches came from a scene, each Gauss point tests one ray to the
    sender's centre against the scene. Pairs farther apart than *far_ratio* times the
    larger patch's diagonal use the receiver's centroid alone (the sender is still
    exact); ``far_ratio=None`` integrates every pair fully. ``symmetric=True`` (default) enforces
    reciprocity exactly by averaging ``A_i F_ij`` and ``A_j F_ji`` (the raw values agree
    to the quadrature accuracy) — the progressive solver's ``F_ij A_i / A_j`` is then
      exactly ``F_ji``.

    Candidate pairs use the former, faster all-at-once calculation while its largest
    temporary fits *memory_budget_mb*, and 256-patch blocks otherwise.  The default
    256 MB keeps the former path for a 384-patch closed box but blocks 4,096 patches,
    whose candidate expression alone needs 1.00 GiB.  On the 2026-10-21 development
    machine, whole-call CPU time / ``tracemalloc`` peak were 0.234 s / 115 MiB
    (original), 0.219 s / 60 MiB (default), and 0.234 s / 60 MiB (forced blocks) for
    384 patches; the isolated 4,096-patch candidate case measured 0.547 s / 1,152 MiB,
    1.500 s / 195 MiB, and 1.516 s / 195 MiB respectively.  Pass 0 to always block,
    or a sufficiently large value to never block.

    Returns the ``(N, N)`` matrix (``matrix``), zero diagonal. In a closed enclosure
    each row sums to 1 (to the quadrature accuracy); an opening shows as a row sum < 1.

    **Raises** ``ValueError``: an empty or unmarked table (not ``radiosity_patches``);
      *n_quad* not an integer in ``[1, 16]``; *far_ratio* below 1; or a negative or
      non-finite *memory_budget_mb*.
    """
    op = "form_factor_matrix"
    p = _check_patches(patches, op)
    nq = _int(n_quad, "n_quad", op, 1, 16)
    fr = None if far_ratio is None else _num(far_ratio, "far_ratio", op, lo=1.0)
    mb = _num(memory_budget_mb, "memory_budget_mb", op, lo=0.0)
    F = _ff_matrix(p["polygons"], p["normals"], p["areas"], p["centers"], nq,
                   p.get("occluders"), far_ratio=fr, memory_budget_mb=mb)
    if symmetric:
        S = p["areas"][:, None] * F
        S = 0.5 * (S + S.T)
        F = S / p["areas"][:, None]
    return F


# --------------------------------------------------------------------------- #
# 漸進ラジオシティ(Cohen ら 1988)
# --------------------------------------------------------------------------- #
def _as_channels(x, P, name, op):
    a = np.asarray(x, dtype=np.float64)
    if a.ndim == 0:
        a = np.full((P, 1), float(a))
    elif a.ndim == 1:
        if a.shape[0] != P:
            raise ValueError("%s: %s must have one value per patch (%d), got %d" % (op, name, P, a.shape[0]))
        a = a[:, None]
    if a.ndim != 2 or a.shape[0] != P:
        raise ValueError("%s: %s must be (N,) or (N, C), got shape %s" % (op, name, a.shape))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s has NaN or inf" % (op, name))
    return a


def _shoot(F, rho, A, E, tol, max_shots):
    """Cohen 1988 §3.1–3.2 の shooting。E (P, C)、rho (P, C)。"""
    B = E.copy()
    dB = E.copy()
    total0 = float((E.sum(-1) * A).sum())
    hist = [total0]
    if total0 <= 0.0:
        return B, hist, 0, True, total0
    thr = tol * total0
    shots = 0
    converged = False
    while shots < max_shots:
        energy = dB.sum(-1) * A
        res = float(energy.sum())
        if res <= thr:
            converged = True
            break
        top = float(energy.max())
        key = np.round(energy / top / _TIE_ROUND) if top > 0 else energy
        i = int(np.argmax(key))                                       # 同点は宣言順(小さい番号)
        dBi = dB[i].copy()
        # 式 8: 全パッチ j に ΔRad = ρ_j ΔB_i F_ij A_i / A_j
        drad = rho * (F[i] * (A[i] / A))[:, None] * dBi[None, :]
        B += drad
        dB += drad
        dB[i] = 0.0                                                   # 撃ち終えた分を 0 に戻す
        shots += 1
        hist.append(float((dB.sum(-1) * A).sum()))
    else:
        res = float((dB.sum(-1) * A).sum())
        converged = res <= thr
    return B, hist, shots, converged, total0


def radiosity_progressive_3d(patches, emission, form_factors=None, albedo=None, tol=1e-6, max_shots=None,
                             n_quad=3):
    """Progressive-refinement radiosity (Cohen et al. 1988, shooting, eqs. 7–8) on a 3-D patch set, with the evidence that it converged.

    Solves ``B = E + diag(ρ) F̃ B`` (``F̃_ji = F_ij A_i/A_j``, eq. 8) by shooting: all
    patches start with ``B = ΔB = E`` (the emitted, or first-reflected, radiosity);
    repeatedly the patch with the largest **unshot energy** ``ΔB_i A_i`` shoots —
    every patch ``j`` gains ``ΔRad = ρ_j ΔB_i F_ij A_i/A_j`` in both ``B_j`` and
    ``ΔB_j`` — and its ``ΔB_i`` is reset to 0. Ties (equal after rounding to 1e-12
    relative) go to the lower index; nothing is random.

    **Stopping rule — our choice, not Cohen's**: the paper stops "when the solution
    converges to within the desired tolerance" without a number. Here the shooting
    stops when the residual unshot energy ``Σ ΔB_i A_i`` falls to ``tol`` times the
    initial energy ``Σ E_i A_i`` (a bound on the energy still missing from the
    solution). ``max_shots`` (default ``200 × N``) caps the work; hitting it returns
    ``converged=False``.

    *emission* ``E`` is ``(N,)`` or ``(N, C)`` (C colour channels), non-negative.
    *albedo* defaults to the patches' (RGB when *emission* has 3 channels, else the
    channel mean). *form_factors* defaults to :func:`form_factor_matrix` (``n_quad``).

    Returns a dict (``table``) with ``kind = "rad_solution"``, ``radiosity`` (N, C),
    ``unshot_history`` (the residual energy before each shot), ``n_shots``,
    ``converged``, ``tol``, ``residual_energy`` (relative), ``initial_energy`` and the
    ``stop_rule`` text.

    **Raises** ``ValueError``: an empty or unmarked table (not ``radiosity_patches``);
    emission or albedo of the wrong shape, negative or non-finite; an albedo outside
    ``[0, 1]``; *tol* not in ``(0, 1]``; a form-factor matrix of the wrong shape. (An
    albedo of 1 in a closed enclosure never loses energy: the shooting then stops at
    *max_shots* with ``converged=False`` instead of raising.)
    """
    op = "radiosity_progressive_3d"
    p = _check_patches(patches, op)
    P = p["polygons"].shape[0]
    E = _as_channels(emission, P, "emission", op)
    if (E < 0.0).any():
        raise ValueError("%s: emission must be >= 0" % op)
    C = E.shape[1]
    if albedo is None:
        rho = p["albedo"] if C == 3 else np.repeat(p["albedo"].mean(-1, keepdims=True), C, axis=1)
    else:
        rho = _as_channels(albedo, P, "albedo", op)
        if rho.shape[1] == 1 and C > 1:
            rho = np.repeat(rho, C, axis=1)
        if rho.shape != (P, C):
            raise ValueError("%s: albedo channels %s do not match emission %s" % (op, rho.shape, E.shape))
    if (rho < 0.0).any() or (rho > 1.0).any():
        raise ValueError("%s: albedo must be in [0, 1]" % op)
    t = _num(tol, "tol", op, lo=0.0, lo_open=True, hi=1.0)
    ms = 200 * P if max_shots is None else _int(max_shots, "max_shots", op, 0, 10 ** 8)
    F = form_factor_matrix(p, n_quad=n_quad) if form_factors is None else np.asarray(form_factors, float)
    if F.shape != (P, P) or not np.isfinite(F).all():
        raise ValueError("%s: form_factors must be a finite (%d, %d) matrix, got %s" % (op, P, P, F.shape))
    B, hist, shots, conv, e0 = _shoot(F, rho, p["areas"], E, t, ms)
    return {"kind": SOLUTION_KIND, "radiosity": B, "unshot_history": np.asarray(hist), "n_shots": shots,
            "converged": bool(conv), "tol": t,
            "residual_energy": (hist[-1] / e0) if e0 > 0 else 0.0, "initial_energy": e0,
            "stop_rule": "stop when sum(dB*A) <= tol * sum(E*A) (our choice; Cohen 1988 gives no number)"}


# --------------------------------------------------------------------------- #
# 検査用の多重反射描画
# --------------------------------------------------------------------------- #
def _fp_update(h, a):
    h.update(np.ascontiguousarray(np.asarray(a, dtype=np.float64)).tobytes())


def _geom_key(scene, camera, patch_mm, outer_mm, n_quad):
    h = hashlib.sha256()
    for obj in scene:
        h.update(obj["kind"].encode())
        stack = [obj]
        while stack:
            o = stack.pop()
            for key in ("c", "h", "z", "r", "hz"):
                if key in o and o[key] is not None:
                    _fp_update(h, o[key])
            if o.get("half") is not None:
                _fp_update(h, o["half"])
            if o["kind"] == "difference":
                stack.extend([o["a"], o["b"]])
    for key in ("K", "R", "eye"):
        _fp_update(h, camera[key])
    _fp_update(h, [camera["width"], camera["height"], patch_mm, -1.0 if outer_mm is None else outer_mm, n_quad])
    return h.hexdigest()


def _light_key(light):
    h = hashlib.sha256()
    _fp_update(h, light["emitters"])
    _fp_update(h, light["directions"])
    _fp_update(h, [float(light.get("cos_exponent", 1.0)), float(light.get("size_mm", 0.0))])
    return h.hexdigest()


def _pixel_patch(hit, patches, scale):
    """画素の当たり点 → パッチ番号(当たらない・パッチの無い面は -1)。"""
    idx, pt, nh = hit["index"], hit["point"], hit["normal"]
    out = np.full(idx.shape[0], -1)
    polys, nrm, lab = patches["polygons"], patches["normals"], patches["labels"]
    lo, hi = polys.min(1), polys.max(1)
    tol = 1e-7 * scale + 1e-7
    for k in np.unique(idx[idx >= 0]):
        pix = np.flatnonzero(idx == k)
        cand = np.flatnonzero(lab == k)
        if cand.size == 0:
            continue
        for s in range(0, pix.size, 2048):
            pp = pix[s:s + 2048]
            x = pt[pp]
            m = ((x[:, None, :] >= lo[cand][None] - tol) & (x[:, None, :] <= hi[cand][None] + tol)).all(-1)
            m &= (nh[pp] @ nrm[cand].T) > 0.5
            m &= np.abs(((x[:, None, :] - patches["centers"][cand][None]) * nrm[cand][None]).sum(-1)) <= tol * 10
            has = m.any(1)
            first = m.argmax(1)
            out[pp[has]] = cand[first[has]]
            if (~has).any():                                       # 縁の丸め: 法線の合う最も近い中心
                miss = pp[~has]
                d2 = ((pt[miss][:, None, :] - patches["centers"][cand][None]) ** 2).sum(-1)
                d2 = np.where((nh[miss] @ nrm[cand].T) > 0.5, d2, np.inf)
                ok = np.isfinite(d2.min(1))
                out[miss[ok]] = cand[d2.argmin(1)[ok]]
    return out


def _pixel_gather(hit, patches, pix_patch, cand, occluders, eps, chunk=400000):
    """画素の点から各パッチへの微小面-有限面の形態係数(疎: rows, cols, vals)。

    画素の点はその画素のパッチ i の中にあるので、点から見える j はパッチの対の候補 cand[i]
    (向き合っているか)の部分集合 —— 候補だけを数える。
    """
    pt, nh = hit["point"], hit["normal"]
    polys, nrm, cen = patches["polygons"], patches["normals"], patches["centers"]
    pix = np.flatnonzero(pix_patch >= 0)
    nb = cand.sum(1)
    cnt = nb[pix_patch[pix]]
    rows, cols, vals = [], [], []
    lists = [np.flatnonzero(cand[i]) for i in range(cand.shape[0])]
    starts = np.concatenate([[0], np.cumsum(cnt)])
    s = 0
    while s < pix.size:
        e = int(np.searchsorted(starts, starts[s] + chunk, side="right")) - 1
        e = max(e, s + 1)
        pp = pix[s:e]
        mi = np.repeat(np.arange(pp.size), cnt[s:e])
        mj = np.concatenate([lists[i] for i in pix_patch[pp]]) if mi.size else np.zeros(0, int)
        s = e
        if mi.size == 0:
            continue
        xs, ns = pt[pp][mi], nh[pp][mi]
        sd = np.einsum("mkc,mc->mk", polys[mj], ns) - (xs * ns).sum(-1)[:, None]
        front_pix = (sd > eps * 10).any(-1)
        front_patch = ((xs - cen[mj]) * nrm[mj]).sum(-1) > eps * 10
        ok = front_pix & front_patch
        mi, mj, xs, ns, sd = mi[ok], mj[ok], xs[ok], ns[ok], sd[ok]
        straddle = (sd < -eps * 10).any(-1)
        f = np.zeros(mi.size)
        c = ~straddle
        if c.any():
            f[c] = _point_polygon(xs[c], ns[c], polys[mj[c]])
        if straddle.any():
            f[straddle] = _point_polygon_sampled(xs[straddle], ns[straddle], polys[mj[straddle]])
        if occluders:
            vis = _visible(occluders, xs, cen[mj])
            f = np.where(vis, f, 0.0)
        keep = f > 0.0
        rows.append(pp[mi[keep]])
        cols.append(mj[keep])
        vals.append(f[keep])
    if not rows:
        return np.zeros(0, int), np.zeros(0, int), np.zeros(0)
    return np.concatenate(rows), np.concatenate(cols), np.concatenate(vals)


def _gi_geometry(scene, camera, patch_mm, outer_mm, n_quad):
    key = _geom_key(scene, camera, patch_mm, outer_mm, n_quad)
    g = _GEOM_CACHE.get(key)
    if g is not None:
        _GEOM_CACHE.move_to_end(key)
        return g
    patches = radiosity_patches(scene=scene, patch_mm=patch_mm, outer_mm=outer_mm)
    F = form_factor_matrix(patches, n_quad=n_quad)
    o, d = _os.camera_rays(camera)
    hit = _os.trace_rays(scene, o, d)
    scale = max(1.0, float(np.abs(patches["polygons"]).max()))
    pix_patch = _pixel_patch(hit, patches, scale)
    cand = _candidates(patches["polygons"], patches["normals"], 1e-12 * scale)
    gr, gc, gv = _pixel_gather(hit, patches, pix_patch, cand, patches["occluders"], 1e-12 * scale)
    g = {"patches": patches, "F": F, "rays": (o, d), "hit": hit, "pix_patch": pix_patch,
         "gather": (gr, gc, gv), "lights": {}}
    _GEOM_CACHE[key] = g
    while len(_GEOM_CACHE) > _GEOM_CACHE_MAX:
        _GEOM_CACHE.popitem(last=False)
    return g


def _unit_light(light):
    lt = dict(light)
    lt["intensity"] = 1.0
    return lt


def _gi_direct(g, scene, light, n_quad):
    """単位強度の直接光: 画素の照度、パッチの平均照度、外れた画素の光源の背景。"""
    lk = _light_key(light)
    d = g["lights"].get(lk)
    if d is not None:
        return d
    lt = _unit_light(light)
    hit = g["hit"]
    m = hit["index"] >= 0
    E_pix = np.zeros(hit["index"].shape[0])
    if m.any():
        E_pix[m] = _os._irradiance(scene, hit["point"][m], hit["normal"][m], lt, True, None)[0]
    pt = g["patches"]
    xq, wq = _quad_points(pt["polygons"], max(2, min(n_quad, 3)))
    Pn, Q = wq.shape
    pts = xq.reshape(-1, 3)
    nn = np.repeat(pt["normals"], Q, axis=0)
    # 面の上の点から 1e-6 mm だけ表に出して撃つ(自分の面に当たらない)
    Eq = _os._irradiance(scene, pts + 1e-6 * nn, nn, lt, True, None)[0].reshape(Pn, Q)
    E_patch = (Eq * wq).sum(-1) / pt["areas"]
    o, dd = g["rays"]
    bg = _os._light_background([lt], o[~m], dd[~m])
    d = {"E_pix": E_pix, "E_patch": E_patch, "bg": bg}
    g["lights"][lk] = d
    return d


def _bounce_study(K, rho_patch, E_patch, gather, rho_pix, E_pix, n_pix, B_conv, study, peak):
    """反射 k = 0..K の像の増分・観測収束比・GCI 型の見積もり・収束解との実誤差。"""
    gr, gc, gv = gather
    C = rho_patch.shape[1]
    Bk = np.zeros_like(rho_patch)                                      # 反射 k-1 回までのパッチのラジオシティ
    first = rho_patch * E_patch[:, None]
    imgs = []                                                           # 反射 k 回の像を全部持つ(study は小さい)
    for k in range(study + 1):
        H = np.zeros((n_pix, C))
        for c in range(C):
            H[:, c] = np.bincount(gr, weights=gv * Bk[gc, c], minlength=n_pix)
        imgs.append(rho_pix * (E_pix[:, None] + H) / math.pi)
        Bk = first + rho_patch * (K @ Bk)
    rows = []
    prev_delta = None
    H = np.zeros((n_pix, C))
    for c in range(C):
        H[:, c] = np.bincount(gr, weights=gv * B_conv[gc, c], minlength=n_pix)
    conv_img = rho_pix * (E_pix[:, None] + H) / math.pi
    # 定義できない量(k < 2 の比、比が [0, 1) の外の残り)は NaN でなく None —— 数として読まれない。
    # 漸近域: 観測収束比が 2 回続けて前の回と 5 % 以内でしか動かない(Roache の「漸近域にあるか」の
    # 確かめの級数版)。漸近域の前の見積もりは楽観しうる —— 実測(加工ポケット、反射率 0.7): k = 3 で
    # 見積もり 0.050 に実際 0.052。比が 0.504 → 0.506 と 1 回だけ揃ったあと、最大値をとる画素が入れ替わって
    # 0.609 へ跳んだ(だから 1 回の一致では漸近域と言わない)。
    prev_ratio, prev_stable = None, False
    for k in range(study + 1):
        delta = float(np.abs(imgs[k] - imgs[k - 1]).max()) / peak if k else None
        ratio = delta / prev_delta if (k >= 2 and prev_delta) else None
        tail = delta * ratio / (1.0 - ratio) if (ratio is not None and 0.0 < ratio < 1.0) else None
        gci = GCI_SAFETY * tail if tail is not None else None
        err = float(np.abs(conv_img - imgs[k]).max()) / peak
        stable = bool(ratio is not None and prev_ratio is not None and abs(ratio - prev_ratio) <= 0.05 * ratio)
        asym = stable and prev_stable
        rows.append({"bounces": k, "increment": delta, "observed_ratio": ratio, "tail_estimate": tail,
                     "gci": gci, "asymptotic": asym, "error_vs_converged": err})
        prev_delta = delta if k else None
        prev_ratio, prev_stable = ratio, stable
    return rows


def render_optscene_gi(scene, camera, lights, bounces=None, patch_mm=2.0, outer_mm=None, tol=1e-6, n_quad=3,
                       supersample=1, study_bounces=8, study_tol=0.01):
    """Inspection render with interreflection: the photometry of ``render_optscene`` plus n bounces (or the converged sum) between Lambertian patches.

    The same scene (``optscene.scene_*``), camera (``optical_camera``) and lights
    (``illumdesign.light_source`` results) as :func:`optscene.render_optscene`. The
    direct part is computed with the very same irradiance function, so
    ``bounces=0`` reproduces ``render_optscene`` exactly (a test gate). On top of it
    the surfaces are cut into patches (:func:`radiosity_patches`, at most *patch_mm*
    inside pockets and *outer_mm* (default *patch_mm*) elsewhere
    on a side), their view factors computed with occlusion
    (:func:`form_factor_matrix`), and the light reflected between them added:

    * ``bounces=None`` — converged, by progressive shooting
      (:func:`radiosity_progressive_3d`, stop at residual energy ``tol``);
    * ``bounces=k`` — the Neumann partial sum: light that bounced at most ``k``
      times between surfaces before reaching the camera (``0`` = direct only,
      ``1`` = one interreflection).

    Each pixel's interreflected irradiance is gathered from the patch radiosities
    with the point-to-polygon closed form at the pixel's own surface point
    (final gather, one visibility ray per patch), so it is smooth inside a patch.
    Pixel radiance = ``ρ/π (E_direct + E_interreflected)`` in the same linear units as
    ``render_optscene``. Light intensity enters linearly (the geometry is cached by
    a SHA-256 of the scene's shapes, camera and patch size — materials and light
    intensity are read on every call, so a calibration loop that varies albedo or
    intensity re-solves only the radiosity).

    *study_bounces* ``K > 0`` adds a **bounce study**: the images after 0..K bounces,
    the increment of each (max abs change / image peak), the observed ratio of
    successive increments ``g`` (the geometric analogue of an observed order of
    convergence), a GCI-style estimate ``1.25 · Δ_k g/(1 − g)`` of what the remaining
    bounces still add, whether ``k`` is in the asymptotic range (``g`` moved by at most
    5 % at ``k`` and at ``k − 1``; before it the estimate can be optimistic), the actual error
    against the converged image, and ``bounces_needed`` = the first ``k`` in the
    asymptotic range whose GCI estimate is below *study_tol*.

    Returns a dict (``table``) with ``kind = "gi_render"``, ``image`` (H, W, 3),
    ``direct`` (H, W, 3, identical to ``render_optscene``), ``difference`` (H, W, 3)
    = image − direct (the interreflection map), ``indirect_share`` (H, W),
    ``bounces``, ``converged``, ``n_shots``, ``unshot_history``, ``n_patches``,
    ``patch_radiosity`` (N, 3), ``bounce_study`` (list of rows, or ``None``),
    ``bounces_needed`` and ``notes``.

    **Raises** ``ValueError``: an empty scene, or an unsupported one (see :func:`radiosity_patches`:
    Lambertian boxes, box-minus-box pockets, finite planes; an infinite plane only
    black); no lights; *bounces* not ``None`` or an integer in ``[0, 1000]``; bad
    *patch_mm*, *tol*, *n_quad*, *supersample*, *study_bounces* or *study_tol*; an
    all-zero image (as ``render_optscene``).
    """
    op = "render_optscene_gi"
    _os._check_camera(camera, op)
    scene = _os._check_scene(scene)
    lights = [lights] if isinstance(lights, dict) else list(lights)
    if not lights:
        raise ValueError("%s: lights must contain at least one illumdesign.light_source() result" % op)
    for lt in lights:
        _os._emitters(lt)
    if bounces is not None:
        bounces = _int(bounces, "bounces", op, 0, 1000)
    pm = _num(patch_mm, "patch_mm", op, lo=0.0, lo_open=True)
    om = None if outer_mm is None else _num(outer_mm, "outer_mm", op, lo=0.0, lo_open=True)
    t = _num(tol, "tol", op, lo=0.0, lo_open=True, hi=1.0)
    nq = _int(n_quad, "n_quad", op, 1, 8)
    ss = _int(supersample, "supersample", op, 1, 8)
    sb = _int(study_bounces, "study_bounces", op, 0, 200)
    st = _num(study_tol, "study_tol", op, lo=0.0, lo_open=True, hi=1.0)
    cam = _os._supersampled(camera, ss) if ss > 1 else camera
    g = _gi_geometry(scene, cam, pm, om, nq)
    pt = g["patches"]
    hit = g["hit"]
    npx = hit["index"].shape[0]
    # 材質は毎回読む(較正で反射率を動かす)
    alb_by_obj = {i: _material_albedo(obj, i, op) for i, obj in enumerate(scene)
                  if not (obj["kind"] == "plane" and obj["half"] is None)}
    rho_patch = np.stack([alb_by_obj[int(i)] for i in pt["labels"]]) if pt["labels"].size else pt["albedo"]
    rho_pix = np.zeros((npx, 3))
    m = hit["index"] >= 0
    for i, obj in enumerate(scene):
        sel = hit["index"] == i
        if sel.any():
            rho_pix[sel] = np.asarray(obj["material"]["albedo"], float).reshape(3)
    E_pix = np.zeros(npx)
    E_patch = np.zeros(pt["polygons"].shape[0])
    bg = np.zeros(int((~m).sum()))
    for lt in lights:
        d = _gi_direct(g, scene, lt, nq)
        inten = float(lt.get("intensity", 1.0))
        E_pix += inten * d["E_pix"]
        E_patch += inten * d["E_patch"]
        bg += inten * d["bg"]
    direct = rho_pix * E_pix[:, None] / math.pi
    first = rho_patch * E_patch[:, None]                                # 1 回目に反射して出ていく光
    F = g["F"]
    A = pt["areas"]
    Kmat = (F.T * A[None, :]) / A[:, None]                              # F̃_ij = F_ji A_j / A_i(相反則なら F_ij)
    notes = []
    shots, hist, conv = 0, np.zeros(0), True
    if bounces is None:
        B, h, shots, conv, e0 = _shoot(F, rho_patch, A, first, t, 200 * len(A))
        hist = np.asarray(h) / e0 if e0 > 0 else np.asarray(h)
        if not conv:
            notes.append("progressive shooting hit the shot cap before the residual energy fell to tol — "
                         "the image is NOT converged")
        Bsrc = B
    else:
        Bk = np.zeros_like(first)
        for _ in range(bounces):
            Bk = first + rho_patch * (Kmat @ Bk)
        Bsrc = Bk                                                         # 反射 bounces-1 回までに出ていく光
    gr, gc, gv = g["gather"]
    H = np.zeros((npx, 3))
    for c in range(3):
        H[:, c] = np.bincount(gr, weights=gv * Bsrc[gc, c], minlength=npx)
    img = direct + rho_pix * H / math.pi
    img[~m] = bg[:, None]
    direct[~m] = bg[:, None]
    if float(img.max()) == 0.0:
        raise ValueError("%s: produced an all-zero image — the lights reach no visible surface "
                         "(same causes as render_optscene)" % op)
    study_rows, needed = None, None
    if sb > 0:
        Bc = Bsrc if bounces is None else _shoot(F, rho_patch, A, first, t, 200 * len(A))[0]
        peak = float(img.max())
        study_rows = _bounce_study(Kmat, rho_patch, E_patch, (gr, gc, gv), rho_pix, E_pix, npx, Bc, sb,
                                            peak)
        for r in study_rows:
            if r["asymptotic"] and r["gci"] is not None and r["gci"] <= st:
                needed = r["bounces"]
                break
        if needed is None:
            notes.append("no bounce count up to %d brought the GCI estimate below %g" % (sb, st))
    H_, W_ = cam["height"], cam["width"]
    image = img.reshape(H_, W_, 3)
    dire = direct.reshape(H_, W_, 3)
    if ss > 1:
        image, dire = _os._box_average(image, ss), _os._box_average(dire, ss)
    diff = image - dire
    share = np.where(image.sum(-1) > 0, diff.sum(-1) / np.maximum(image.sum(-1), 1e-300), 0.0)
    return {"kind": RENDER_KIND, "image": image, "direct": dire, "difference": diff, "indirect_share": share,
            "bounces": bounces, "converged": bool(conv), "n_shots": int(shots), "unshot_history": hist,
            "n_patches": int(len(A)), "patch_radiosity": Bsrc, "bounce_study": study_rows,
            "bounces_needed": needed, "study_tol": st, "notes": notes}

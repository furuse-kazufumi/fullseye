# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tacdome — ドーム状の柔らかい指先センサが平らな物に押される大変形接触を、べき乗則断面のスケーリング則で門にする(2026-10-05)。

物理シミュ × Fullseye 系列(視触覚 (b))。tacsim の Hertz(小変形・半無限の膜)の先: 指先のドーム(高さ L)を平板で δ 押すと、δ/L が
0.3 を超えたあたりから Hertz が力も接触半径も小さく見積もる。真値は外から来る 3 系統:

  * **大変形のスケーリング則**(T. Mu ほか, "A scaling law for large-deformation contact in soft materials", arXiv:2509.18581, 2025):
    断面 f(r) = c·rᵖ の線形解 F_L = C·δⁿ、n = 1 + 1/p(式 1)、a_L = D·δ^{1/p}(式 5)。大変形は F = κₙ(δ/L)·F_L(式 2)、
    接触半径 a = (1/p)·B_d(1/p, 3/2)·d^{−1/p}/√(1 − d)·a_L(式 4、d = δ/L、B は不完全ベータ)、普遍形 κ(d) = (1 − k·d)⁻¹、k = 10/9(式 6)。
    論文の検証範囲は δ/L ≤ 0.5(有限要素 = 非圧縮 neo-Hookean、摩擦なし)。
  * **式 (3) の 1 次の係数**: 原文 PDF の該当ページを画像にして目視した活字は κₙ(d) = [1 − (4+2n)/(1+n)·d + n/(2+n)·d²]/(1 − d)²。
    これは円柱(n = 1)で d = 0.5 のとき κ = −1.67(力が負)になり、論文自身の「Hertz は過小評価」とも矛盾する。本文の記述
    (「1D の非線形ばねの列、各ばねは同じ超弾性材料の円柱」)どおりに模型を組み直して積分すると(下の導出)、
    **κₙ(d) = [1 − 2n/(1+n)·d + n/(2+n)·d²]/(1 − d)²** になる —— 2 次の係数 n/(2+n) と式 (4) は活字と一字一句一致し、1 次だけが違う。
    以前のメモの「2/(1+n)」は n = 1 でだけ一致する読みで、n > 1 では本模型の定理 κₙ ≤ κ₁ を破る(図 4B の挿入図の並び
    n = 2 が上・n = 1 が下とも逆)。既定は導出した係数、``reading`` で活字(``"printed"``)とメモ(``"memo"``)も選べる(門で棄却するため)。
  * **連続体の厳密解**: 非圧縮 neo-Hookean の円柱を摩擦なしで一軸圧縮すると公称応力 P = μ(λ⁻² − λ)、半径は λ^{−1/2} 倍(教科書の結果)。
    n = 1 の κ₁ と p = ∞ の式 (4) はこれと厳密に一致しなければならない。
  * **Hertz の小変形極限**(Johnson, *Contact Mechanics*, CUP 1985, §3): d → 0 で κ → 1・a → a_L、球なら F = (4/3)E*√R δ^{3/2}
    (:mod:`tacsim` の ``hertz_force`` と同じ数)。

自分で作ったもの(正直に): 式 (3)(4) の導出 —— MDR(Popov と Heß の次元縮約)の 1D 断面 g(x) = κ_p·c·|x|ᵖ
(κ_p = √π Γ(p/2 + 1)/Γ(p/2 + 1/2))の各点に、長さ ℓ = L − g(x) の neo-Hookean 円柱ばね(線形の極限で MDR の剛性 E*·dx になる断面)を
置き、全部を同じ長さ L − δ まで縮める(伸び λ = (L − δ)/ℓ)。力 dF = E*·dx·ℓ·(λ⁻² − λ)/3、幅は λ^{−1/2} 倍で、接触半径 a = ∫λ^{−1/2}dx。
x を積分すると上の κₙ と式 (4) が閉形式で出る(1 次の係数は 2(p+1)/(2p+1) = 2n/(1+n)、2 次は (p+1)/(3p+1) = n/(2+n))。
局所のひずみ (δ − g)/(L − g) は d 以下なので、κₙ は κ₁ の重みつき平均 = κₙ ≤ κ₁(定理)。数値のばね列(:func:`mdr_spring_bed`)は
閉形式と別の経路(中点則)で同じ模型を積分する第 2 実装。センサの像(:func:`dome_contact_image`、接触域が明るい内側カメラ)と
面積法の半径(:func:`contact_patch_radius`、被覆率の線形和で縁の副画素まで)。

被験者: :mod:`tacsim` の Hertz(``hertz_force`` / ``hertz_sphere``)—— 接触半径から力を読むと大変形でも数 % しか外れない(球)が、
押し込みから読むと δ/L = 0.3 で 28 % 小さい、という「何を観測するかで外れ方が変わる」を数で出す。:func:`measure.fit_circle`(縁の画素)。

op(台帳 ``tacdome``、opsdrive、全部 numpy): :func:`powerlaw_linear_contact` / :func:`largedef_correction` /
:func:`largedef_radius_ratio` / :func:`largedef_universal_correction` / :func:`large_deformation_contact` / :func:`large_deformation_inverse` /
:func:`mdr_spring_bed` / :func:`neohookean_cylinder_exact` / :func:`hertz_small_strain_error` / :func:`dome_contact_image` /
:func:`contact_patch_radius` / :func:`largedef_c1_coefficient`(式 (3) の 1 次の係数を 3 つの読みで)。

限界: 半球は放物線(p = 2)で近似(論文と同じ)。摩擦なし・準静的・非圧縮。式 (3) の 1 次の係数は付録(本文に無い、未読)と照合できて
いない。論文の図 5C(半球 1 個の接触半径 vs 力)は Hertz の半径が模型より 1 割以上大きく描かれているが、導出した模型では
同じ力での半径の差は 2 % 以内で、この図は再現できない(付録の条件 —— 寸法・弾性率・固定 —— が未読)。

規約: 長さ m、力 N。d = δ/L(無次元)。E* は複合弾性率(非圧縮で剛体の相手なら E* = 4μ)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "powerlaw_linear_contact", "largedef_correction", "largedef_radius_ratio", "largedef_universal_correction",
    "large_deformation_contact", "large_deformation_inverse", "mdr_spring_bed", "neohookean_cylinder_exact",
    "hertz_small_strain_error", "dome_contact_image", "contact_patch_radius", "largedef_c1_coefficient",
    "DOME_SHAPES", "C1_READINGS", "UNIVERSAL_K", "VALIDATED_D",
]

#: :func:`powerlaw_linear_contact` の断面: 球(放物線 p = 2)・円錐(p = 1)・平頭の円柱(p = ∞)・任意のべき乗
DOME_SHAPES = ("sphere", "cone", "punch", "power")
#: 式 (3) の 1 次の係数の読み: 導出(既定)/ 原文の活字 / 以前のメモ
C1_READINGS = ("derived", "printed", "memo")
#: 普遍形の係数(式 6)
UNIVERSAL_K = 10.0 / 9.0
#: 論文が有限要素と実験で確かめた範囲 δ/L ≤ 0.5
VALIDATED_D = 0.5


# ----------------------------------------------------------------------------------------------------------------------
# 入力の検査
def _as_d(d, name="d", allow_zero=True):
    """d = δ/L を配列にして検査(0 ≤ d < 1、有限)。返り (配列, スカラー入力だったか)。文字列は数に見えても拒否する。"""
    if isinstance(d, (str, bytes)) or (isinstance(d, np.ndarray) and d.dtype.kind in "USO"):
        raise ValueError("tacdome: %s must be a number or a numeric array, got %r" % (name, type(d).__name__))
    arr = np.asarray(d, dtype=np.float64)
    scalar = arr.ndim == 0
    arr = np.atleast_1d(arr)
    if arr.size == 0:
        raise ValueError("tacdome: %s is empty" % name)
    if not np.all(np.isfinite(arr)):
        raise ValueError("tacdome: %s must be finite" % name)
    lo_ok = (arr >= 0.0) if allow_zero else (arr > 0.0)
    if not np.all(lo_ok & (arr < 1.0)):
        raise ValueError("tacdome: %s = δ/L must be in %s0, 1), got min %.4g max %.4g"
                         % (name, "[" if allow_zero else "(", float(arr.min()), float(arr.max())))
    return arr, scalar


def _out(arr, scalar):
    return float(arr[0]) if scalar else arr


def _num(v, name):
    """数 1 個(文字列・bool・None は数に見えても拒否)。"""
    if isinstance(v, (str, bytes, bool)) or v is None:
        raise ValueError("tacdome: %s must be a number, got %r" % (name, v))
    try:
        return float(v)
    except (TypeError, ValueError) as exc:
        raise ValueError("tacdome: %s must be a number, got %r" % (name, v)) from exc


def _check_n(n):
    n = _num(n, "n")
    if not (math.isfinite(n) and 1.0 <= n <= 3.0):
        raise ValueError("tacdome: exponent n must be in [1, 3] (n = 1 + 1/p), got %r" % n)
    return n


def _check_p(p):
    p = _num(p, "p")
    if math.isinf(p) and p > 0:
        return p
    if not (math.isfinite(p) and 0.5 <= p <= 1000.0):
        raise ValueError("tacdome: profile exponent p must be in [0.5, 1000] or +inf, got %r" % p)
    return p


def _check_lin(lin):
    keys = ("p", "n", "C", "D", "Estar", "shape")
    if not isinstance(lin, dict) or not all(k in lin for k in keys):
        raise ValueError("tacdome: lin must be the dict from powerlaw_linear_contact()")
    return lin


def _pos(v, name):
    v = _num(v, name)
    if not (math.isfinite(v) and v > 0.0):
        raise ValueError("tacdome: %s must be finite and > 0, got %r" % (name, v))
    return v


# ----------------------------------------------------------------------------------------------------------------------
# 線形解(MDR、小変形)
def _kappa_p(p: float) -> float:
    """MDR の断面の係数 κ_p = √π Γ(p/2 + 1)/Γ(p/2 + 1/2)(Popov–Heß、球 p = 2 で 2、円錐 p = 1 で π/2)。"""
    return math.exp(0.5 * math.log(math.pi) + math.lgamma(p / 2.0 + 1.0) - math.lgamma(p / 2.0 + 0.5))


def powerlaw_linear_contact(shape: str, size: float, Estar: float, p: float | None = None) -> dict:
    """べき乗則断面 f(r) = c·rᵖ を平板で押す線形解(式 1・5): F_L = C·δⁿ、a_L = D·δ^{1/p}、n = 1 + 1/p。

    ``shape``: ``"sphere"``(``size`` = 半径 R、放物線 c = 1/(2R)、C = (4/3)E*√R、D = √R = Hertz)/ ``"cone"``(``size`` = 側面の
    傾き tanα = 高さ/底の半径、C = 2E*/(π tanα)、D = 2/(π tanα))/ ``"punch"``(平頭の円柱、``size`` = 半径 a0、n = 1、C = 2E*a0、
    a_L = a0 で一定)/ ``"power"``(``size`` = c、``p`` が要る)。MDR の 1D 断面は g(x) = κ_p c |x|ᵖ で、
    C = 2E*·p/(p+1)·(κ_p c)^{−1/p}、D = (κ_p c)^{−1/p}。

    返り: ``shape``・``p``・``n``・``c``・``kappa_p``・``g_coef``(= κ_p c、punch は 0)・``C``・``D``・``Estar``・``size``。
    **Raises** ``ValueError``: 知らない shape(綴り違い)、size・E* ≤ 0、power で p が無い / 範囲外、power 以外で p を渡した。"""
    if not isinstance(shape, str) or shape not in DOME_SHAPES:
        raise ValueError("powerlaw_linear_contact: shape must be one of %s, got %r" % (DOME_SHAPES, shape))
    size, Estar = _pos(size, "size"), _pos(Estar, "Estar")
    if shape != "power" and p is not None:
        raise ValueError("powerlaw_linear_contact: p is fixed by shape=%r (give p only with shape='power')" % shape)
    if shape == "punch":
        return {"shape": shape, "p": math.inf, "n": 1.0, "c": 0.0, "kappa_p": 1.0, "g_coef": 0.0,
                "C": 2.0 * Estar * size, "D": size, "Estar": Estar, "size": size}
    if shape == "sphere":
        pp, c = 2.0, 1.0 / (2.0 * size)
    elif shape == "cone":
        pp, c = 1.0, size
    else:
        if p is None:
            raise ValueError("powerlaw_linear_contact: shape='power' needs p")
        pp, c = _check_p(p), size
        if math.isinf(pp):
            raise ValueError("powerlaw_linear_contact: p = inf is shape='punch'")
    kp = _kappa_p(pp)
    g = kp * c
    D = g ** (-1.0 / pp)
    C = 2.0 * Estar * pp / (pp + 1.0) * D
    return {"shape": shape, "p": pp, "n": 1.0 + 1.0 / pp, "c": c, "kappa_p": kp, "g_coef": g, "C": C, "D": D,
            "Estar": Estar, "size": size}


# ----------------------------------------------------------------------------------------------------------------------
# 大変形の補正(式 3・4・6)
def largedef_c1_coefficient(n: float, reading: str = "derived") -> float:
    """式 (3) の 1 次の係数 c₁: ``"derived"`` = 2n/(1+n)(導出)、``"printed"`` = (4+2n)/(1+n)(原文の活字)、``"memo"`` = 2/(1+n)。

    **Raises** ``ValueError``: 知らない読み、n が [1, 3] の外。"""
    n = _check_n(n)
    if reading == "derived":
        return 2.0 * n / (1.0 + n)
    if reading == "printed":
        return (4.0 + 2.0 * n) / (1.0 + n)
    if reading == "memo":
        return 2.0 / (1.0 + n)
    raise ValueError("largedef_c1_coefficient: reading must be one of %s, got %r" % (C1_READINGS, reading))


def largedef_correction(d, n: float, reading: str = "derived"):
    """大変形の補正 κₙ(d) = [1 − c₁·d + n/(2+n)·d²]/(1 − d)²(式 3、c₁ は :func:`largedef_c1_coefficient`)。F = κₙ·F_L。

    ``d`` はスカラーか配列(0 ≤ d < 1)。既定の読みは導出した c₁ = 2n/(1+n)。d → 0 で 1 + 2d/(1+n)、n = 1 で neo-Hookean の円柱の
    厳密解 [(1 − d)⁻² − (1 − d)]/(3d) に一致する。**Raises** ``ValueError``: d が [0, 1) の外、n が [1, 3] の外、読みの綴り違い。"""
    arr, scalar = _as_d(d)
    n = _check_n(n)
    c1 = largedef_c1_coefficient(n, reading)
    k = (1.0 - c1 * arr + n / (2.0 + n) * arr * arr) / (1.0 - arr) ** 2
    return _out(k, scalar)


# 区間を 1 に寄せた複合 Gauss–Legendre(uᵖ は p が大きいと u = 1 の近くで急に立つ)
_GL_X, _GL_W = np.polynomial.legendre.leggauss(24)
# 区間の端は両側に幾何級数で寄せる: u = 0 側は p が整数でないと uᵖ の高階微分が発散する(p = 1.5 で 1 区間だと 2e-9)。
_EDGES = np.concatenate([[0.0], 0.5 ** np.arange(16, 0, -1), 1.0 - 0.5 ** np.arange(2, 16), [1.0]])


def _gl_nodes():
    xs, ws = [], []
    for lo, hi in zip(_EDGES[:-1], _EDGES[1:]):
        xs.append(0.5 * (hi - lo) * _GL_X + 0.5 * (hi + lo))
        ws.append(0.5 * (hi - lo) * _GL_W)
    return np.concatenate(xs), np.concatenate(ws)


_U, _WU = _gl_nodes()


def _betacf(a, b, x, itmax=400, eps=1e-16):
    """正則化不完全ベータの連分数(修正 Lentz)。x < (a+1)/(a+b+2) で速く収束する側。"""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, dd = 1.0, 1.0 - qab * x / qap
    dd = 1.0 / (dd if abs(dd) > tiny else tiny)
    h = dd
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        dd = 1.0 + aa * dd
        dd = 1.0 / (dd if abs(dd) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= dd * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        dd = 1.0 + aa * dd
        dd = 1.0 / (dd if abs(dd) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        de = dd * c
        h *= de
        if abs(de - 1.0) < eps:
            return h
    raise ValueError("tacdome: incomplete beta continued fraction did not converge (a=%r b=%r x=%r)" % (a, b, x))


def _betainc_lower(x: float, a: float, b: float) -> float:
    """正則化しない不完全ベータ B_x(a, b) = ∫₀ˣ t^{a−1}(1 − t)^{b−1} dt(連分数、Numerical Recipes §6.4 の形)。"""
    if x <= 0.0:
        return 0.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(a * math.log(x) + b * math.log1p(-x) - lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        reg = front * _betacf(a, b, x) / a
    else:
        reg = 1.0 - front * _betacf(b, a, 1.0 - x) / b
    return reg * math.exp(lbeta)


def largedef_radius_ratio(d, p: float, method: str = "quadrature"):
    """大変形の接触半径の比 a/a_L(式 4)= (1/p)·B_d(1/p, 3/2)·d^{−1/p}/√(1 − d) = ∫₀¹ √((1 − d·uᵖ)/(1 − d)) du。

    ``method="quadrature"``(既定): 右の積分を 1 に寄せた複合 Gauss–Legendre で。``"beta"``: 原文の形どおり不完全ベータの
    連分数で(別の経路、照合用)。p = ∞(平頭)は非圧縮の半径の伸び 1/√(1 − d)。d → 0 で 1 + d·p/(2(p+1))。
    p = 1・2 の閉形式は (2/(3d))(1 − (1 − d)^{3/2})/√(1 − d) と [√(1−d)/2 + atan2(√d, √(1−d))/(2√d)]/√(1 − d)。
    **Raises** ``ValueError``: d が [0, 1) の外、p が範囲外、method の綴り違い。"""
    arr, scalar = _as_d(d)
    p = _check_p(p)
    if method not in ("quadrature", "beta"):
        raise ValueError("largedef_radius_ratio: method must be 'quadrature' or 'beta', got %r" % method)
    if math.isinf(p):
        return _out(1.0 / np.sqrt(1.0 - arr), scalar)
    if method == "quadrature":
        up = _U ** p
        val = np.array([float(np.sum(_WU * np.sqrt(1.0 - di * up))) for di in arr]) / np.sqrt(1.0 - arr)
        return _out(val, scalar)
    out = np.empty_like(arr)
    for i, di in enumerate(arr):
        if di == 0.0:
            out[i] = 1.0
        else:
            out[i] = (1.0 / p) * _betainc_lower(float(di), 1.0 / p, 1.5) * di ** (-1.0 / p) / math.sqrt(1.0 - di)
    return _out(out, scalar)


def largedef_universal_correction(d, k: float = UNIVERSAL_K):
    """普遍形の補正 κ(d) = (1 − k·d)⁻¹(式 6、k = 10/9)。**Raises** ``ValueError``: d が [0, 1) の外、k·d ≥ 1、k ≤ 0。"""
    arr, scalar = _as_d(d)
    k = _pos(k, "k")
    if np.any(k * arr >= 1.0):
        raise ValueError("largedef_universal_correction: k·d must be < 1 (k=%.4g, max d=%.4g)" % (k, float(arr.max())))
    return _out(1.0 / (1.0 - k * arr), scalar)


# ----------------------------------------------------------------------------------------------------------------------
# 順と逆
def _radius_lin(delta, lin):
    if math.isinf(lin["p"]):
        return lin["D"] * np.ones_like(np.asarray(delta, float))
    return lin["D"] * np.asarray(delta, float) ** (1.0 / lin["p"])


def _hertz_force_from_radius(a, lin):
    """線形解を接触半径から逆に読む力 C·(a/D)^{p·n}(平頭は a が δ を決めないので nan)。"""
    if math.isinf(lin["p"]):
        return np.full(np.shape(a), np.nan)
    return lin["C"] * (np.asarray(a, float) / lin["D"]) ** (lin["p"] * lin["n"])


def large_deformation_contact(delta, L: float, lin: dict, reading: str = "derived") -> dict:
    """押し込み δ(スカラーか配列)から大変形の力と接触半径(式 2・4)と、同じ δ の線形解(Hertz)との差。

    返り: ``d``・``delta``・``F_L``(線形)・``a_L``・``kappa``・``F``(= κ F_L)・``radius_ratio``・``a``・``F_universal``
    (式 6、k·d ≥ 1 は inf)・``F_hertz_from_radius``(測った a を線形解で読んだ力、平頭は nan)・``err_force_from_delta_pct``
    (F_L/F − 1)・``err_radius_from_delta_pct``(a_L/a − 1)・``err_force_from_radius_pct``・``beyond_validated``(d > 0.5)。
    **Raises** ``ValueError``: δ ≤ 0 か δ ≥ L、L ≤ 0、lin が powerlaw_linear_contact の表でない、読みの綴り違い。"""
    lin = _check_lin(lin)
    L = _pos(L, "L")
    dl = np.asarray(delta, dtype=np.float64)
    scalar = dl.ndim == 0
    darr, _ = _as_d(np.atleast_1d(dl) / L, "delta/L", allow_zero=False)
    delta_a = darr * L
    FL = lin["C"] * delta_a ** lin["n"]
    aL = _radius_lin(delta_a, lin)
    kap = np.atleast_1d(largedef_correction(darr, lin["n"], reading))
    rr = np.atleast_1d(largedef_radius_ratio(darr, lin["p"]))
    F = kap * FL
    a = rr * aL
    with np.errstate(divide="ignore"):
        Fu = np.where(UNIVERSAL_K * darr < 1.0, FL / np.maximum(1.0 - UNIVERSAL_K * darr, 1e-300), np.inf)
    FhA = _hertz_force_from_radius(a, lin)
    o = {"d": darr, "delta": delta_a, "F_L": FL, "a_L": aL, "kappa": kap, "F": F, "radius_ratio": rr, "a": a,
         "F_universal": Fu, "F_hertz_from_radius": FhA,
         "err_force_from_delta_pct": 100.0 * (FL / F - 1.0), "err_radius_from_delta_pct": 100.0 * (aL / a - 1.0),
         "err_force_from_radius_pct": 100.0 * (FhA / F - 1.0), "beyond_validated": darr > VALIDATED_D,
         "L": L, "reading": reading}
    if scalar:
        o = {k: (v.item() if isinstance(v, np.ndarray) else v) for k, v in o.items()}
    return o


def large_deformation_inverse(a: float, L: float, lin: dict, reading: str = "derived", tol: float = 1e-14) -> dict:
    """測った接触半径 a から押し込みと力を逆に読む(式 4 を d について解き、式 2 で力)。センサの読み出しの本体。

    平頭は閉形式 d = 1 − (a0/a)²。それ以外は a(d) = (a/a_L)(d)·D·(dL)^{1/p} が d の単調増加なので二分法(相対 ``tol``)。
    返り: ``d``・``delta``・``F``・``F_L``・``kappa``・``F_hertz_from_radius``(同じ a を線形解 = Hertz で読んだ力)・
    ``err_hertz_pct``(Hertz で読んだ力の誤差)・``beyond_validated``・``iterations``。
    **Raises** ``ValueError``: a ≤ 0、平頭で a ≤ a0、d が 1 に届いても a に足りない(数値の範囲外)。"""
    lin = _check_lin(lin)
    a = _pos(a, "a")
    L = _pos(L, "L")
    p = lin["p"]
    it = 0
    if math.isinf(p):
        a0 = lin["D"]
        if not (a > a0):
            raise ValueError("large_deformation_inverse: punch contact radius must exceed a0=%.4g (got %.4g)" % (a0, a))
        d = 1.0 - (a0 / a) ** 2
    else:
        def a_of(dd):
            return float(largedef_radius_ratio(dd, p)) * lin["D"] * (dd * L) ** (1.0 / p)
        lo, hi = 0.0, 1.0 - 1e-9
        if a_of(hi) < a:
            raise ValueError("large_deformation_inverse: a=%.4g is beyond d → 1 (max %.4g)" % (a, a_of(hi)))
        while hi - lo > tol * max(hi, 1e-300) and it < 200:
            mid = 0.5 * (lo + hi)
            if a_of(mid) < a:
                lo = mid
            else:
                hi = mid
            it += 1
        assert it >= 1
        d = 0.5 * (lo + hi)
    if not (0.0 < d < 1.0):
        raise ValueError("large_deformation_inverse: no admissible d for a=%.4g" % a)
    fw = large_deformation_contact(d * L, L, lin, reading)
    FhA = float(_hertz_force_from_radius(np.array([a]), lin)[0])
    return {"d": d, "delta": d * L, "F": fw["F"], "F_L": fw["F_L"], "kappa": fw["kappa"], "F_hertz_from_radius": FhA,
            "err_hertz_pct": 100.0 * (FhA / fw["F"] - 1.0), "beyond_validated": d > VALIDATED_D, "iterations": it}


# ----------------------------------------------------------------------------------------------------------------------
# 第 2 実装(数値のばね列)と連続体の厳密解
def mdr_spring_bed(delta: float, L: float, lin: dict, n_springs: int = 4000) -> dict:
    """1D の非線形ばね列を中点則で直接積分する(閉形式 :func:`largedef_correction` / :func:`largedef_radius_ratio` の第 2 実装)。

    ばね x ∈ [0, a_L] (片側、力は 2 倍): MDR の断面 g = g_coef·xᵖ、長さ ℓ = L − g、伸び λ = (L − δ)/ℓ、力 E*·dx·ℓ·(λ⁻² − λ)/3
    (線形の極限で E*·dx·(δ − g) = MDR)、幅は λ^{−1/2} 倍。平頭は g = 0(全部 λ = 1 − d)。返り: ``x``・``g``・``length``・
    ``stretch``・``width_factor``・``x_deformed``(幅の累積 = 変形後の位置)・``F``・``F_lin``・``kappa``(= F/F_lin)・``a``・
    ``radius_ratio``(= a/a_L)・``strain_max``・``spring_force``(dF/dx)。
    **Raises** ``ValueError``: n_springs < 16、δ/L が (0, 1) の外。"""
    lin = _check_lin(lin)
    L = _pos(L, "L")
    delta = _pos(delta, "delta")
    n_springs = int(n_springs)
    if n_springs < 16:
        raise ValueError("mdr_spring_bed: n_springs must be >= 16, got %r" % n_springs)
    _as_d(delta / L, "delta/L", allow_zero=False)
    Es = lin["Estar"]
    aL = float(_radius_lin(np.array([delta]), lin)[0])
    h = aL / n_springs
    x = (np.arange(n_springs) + 0.5) * h
    g = np.zeros_like(x) if math.isinf(lin["p"]) else lin["g_coef"] * x ** lin["p"]
    ell = L - g
    lam = (L - delta) / ell
    fx = Es * ell * (lam ** -2 - lam) / 3.0
    flin = Es * (delta - g)
    wf = lam ** -0.5
    F = 2.0 * float(np.sum(fx) * h)
    Fl = 2.0 * float(np.sum(flin) * h)
    a = float(np.sum(wf) * h)
    return {"x": x, "g": g, "length": ell, "stretch": lam, "width_factor": wf, "x_deformed": np.cumsum(wf) * h,
            "F": F, "F_lin": Fl, "kappa": F / Fl, "a": a, "a_L": aL, "radius_ratio": a / aL,
            "strain_max": float(1.0 - lam.min()), "spring_force": fx}


def neohookean_cylinder_exact(d, mu: float = 1.0, area: float = 1.0) -> dict:
    """非圧縮 neo-Hookean の円柱を摩擦なしで一軸に圧縮する厳密解(連続体の教科書の結果、模型と独立)。

    伸び λ = 1 − d、横は λ^{−1/2}(体積一定)。公称応力 P = μ(λ⁻² − λ)(圧縮を正)、Cauchy 応力 σ = μ(λ⁻¹ − λ²)、力 F = P·area、
    線形の力 3μ·d·area(E = 3μ)、``kappa`` = F/線形、``radius_ratio`` = λ^{−1/2}。
    **Raises** ``ValueError``: d が [0, 1) の外、μ・area ≤ 0。"""
    arr, scalar = _as_d(d)
    mu, area = _pos(mu, "mu"), _pos(area, "area")
    lam = 1.0 - arr
    P = mu * (lam ** -2 - lam)
    Flin = 3.0 * mu * arr * area
    with np.errstate(invalid="ignore", divide="ignore"):
        kap = np.where(arr > 0, P * area / np.where(Flin > 0, Flin, 1.0), 1.0)
    return {"stretch": _out(lam, scalar), "nominal_stress": _out(P, scalar), "cauchy_stress": _out(mu * (1.0 / lam - lam ** 2), scalar),
            "F": _out(P * area, scalar), "F_lin": _out(Flin, scalar), "kappa": _out(kap, scalar),
            "radius_ratio": _out(lam ** -0.5, scalar)}


def hertz_small_strain_error(d, p: float, reading: str = "derived") -> dict:
    """小変形の線形解(Hertz)を大変形に当てたときの誤差 [%] (d だけで決まり、L・寸法・弾性率に依らない)。

    ``force_from_delta`` = 1/κₙ − 1(押し込みから力を読む)、``radius_from_delta`` = 1/(a/a_L) − 1、``force_from_radius`` =
    (a/a_L)^{p+1}/κₙ − 1(接触半径から力を読む = 視触覚センサの読み方、平頭は nan)、``force_universal`` = 普遍形 (1 − k d)⁻¹ で読んだ力の誤差
    κ_universal/κₙ − 1(k·d ≥ 1 は nan)。
    **Raises** ``ValueError``: d が [0, 1) の外、p が範囲外。"""
    arr, scalar = _as_d(d)
    p = _check_p(p)
    n = 1.0 + (0.0 if math.isinf(p) else 1.0 / p)
    kap = np.atleast_1d(largedef_correction(arr, n, reading))
    rr = np.atleast_1d(largedef_radius_ratio(arr, p))
    ffr = np.full_like(arr, np.nan) if math.isinf(p) else 100.0 * (rr ** (p + 1.0) / kap - 1.0)
    ok = UNIVERSAL_K * arr < 1.0
    ku = np.where(ok, 1.0 / np.where(ok, 1.0 - UNIVERSAL_K * arr, 1.0), np.nan)
    return {"d": _out(arr, scalar), "force_from_delta": _out(100.0 * (1.0 / kap - 1.0), scalar),
            "radius_from_delta": _out(100.0 * (1.0 / rr - 1.0), scalar), "force_from_radius": _out(ffr, scalar),
            "force_universal": _out(100.0 * (ku / kap - 1.0), scalar)}


# ----------------------------------------------------------------------------------------------------------------------
# センサの像(内側カメラ)と読み出し
def dome_contact_image(a: float, pitch: float, n: int = 128, centre=None, fg: float = 1.0, bg: float = 0.12,
                       footprint: float | None = None, outside: float = 0.0, noise: float = 0.0, seed: int = 0,
                       ss: int = 8) -> np.ndarray:
    """ドームの内側から撮った接触の像(接触域が明るい、全反射の破れ型の照明の理想化)。(n, n) の float。

    半径 ``a`` [m] の円盤 = ``fg``、ドームの底の円(``footprint`` [m]、None なら全面)の残り = ``bg``、外 = ``outside``。縁は画素を
    ``ss`` × ``ss`` に割った被覆率で反エイリアス(補間しない)。``centre`` = (行, 列)[px] (既定は中央 + 副画素のずれ 0.37, −0.21)。
    ``noise`` = 画素ごとの正規雑音の σ。**Raises** ``ValueError``: a・pitch ≤ 0、n < 16、ss < 1、円盤が窓からはみ出す、fg ≤ bg。"""
    a, pitch = _pos(a, "a"), _pos(pitch, "pitch")
    n, ss = int(n), int(ss)
    if n < 16 or ss < 1:
        raise ValueError("dome_contact_image: need n >= 16 and ss >= 1")
    if not (float(fg) > float(bg)):
        raise ValueError("dome_contact_image: fg must be brighter than bg")
    cy, cx = ((n - 1) / 2.0 + 0.37, (n - 1) / 2.0 - 0.21) if centre is None else (float(centre[0]), float(centre[1]))
    r_px = a / pitch
    if cy - r_px < 0.5 or cx - r_px < 0.5 or cy + r_px > n - 1.5 or cx + r_px > n - 1.5:
        raise ValueError("dome_contact_image: contact disc (r=%.1f px) does not fit the %d px window" % (r_px, n))
    off = (np.arange(ss) + 0.5) / ss - 0.5
    yy = np.arange(n, dtype=np.float64)[:, None, None, None] + off[None, None, :, None] - cy
    xx = np.arange(n, dtype=np.float64)[None, :, None, None] + off[None, None, None, :] - cx
    rr2 = yy * yy + xx * xx
    cov = np.mean(rr2 <= r_px * r_px, axis=(2, 3))
    if footprint is None:
        base = np.full((n, n), float(bg))
    else:
        rf = _pos(footprint, "footprint") / pitch
        covf = np.mean(rr2 <= rf * rf, axis=(2, 3))
        base = float(outside) + (float(bg) - float(outside)) * covf
    img = base + (float(fg) - float(bg)) * cov
    if noise:
        img = img + np.random.default_rng(int(seed)).normal(0.0, float(noise), img.shape)
    return img


def contact_patch_radius(img, pitch: float, ring_px: float = 4.0) -> dict:
    """接触の像(:func:`dome_contact_image` の型)から接触半径を読む。被覆率の線形和(面積法)で縁の副画素まで使う。

    1) しきい値 (1 % 点 + 99.9 % 点)/2 で粗い円盤 → 重心と半径 r_t。2) 内側 r < r_t − ``ring_px`` の中央値を fg、外の輪
    r_t + ``ring_px`` 〜 r_t + 2·``ring_px`` の中央値を bg。3) 被覆率 (I − bg)/(fg − bg) を r < r_t + ``ring_px`` で**切らずに**足す
    (切ると雑音が片側に偏る)→ a = pitch·√(Σ/π)、重心は被覆率の重み。返り: ``a``・``a_px``・``a_threshold``(しきい値の画素数の円)・
    ``centre``(行, 列)・``fg``・``bg``・``edge_points``(しきい値の円盤の境界画素 (行, 列)、measure.fit_circle に渡せる)。
    **Raises** ``ValueError``: 2 次元でない、明るい円盤が無い(コントラスト 0)、円盤が小さすぎる(r_t < 3 px)か窓の縁に触れる。"""
    pitch = _pos(pitch, "pitch")
    if not isinstance(img, np.ndarray) or img.dtype.kind not in "fiub":
        raise ValueError("contact_patch_radius: img must be a numeric numpy array, got %r" % type(img).__name__)
    im = np.asarray(img, dtype=np.float64)
    if im.ndim != 2 or min(im.shape) < 16:
        raise ValueError("contact_patch_radius: img must be a 2-D image of at least 16×16")
    if not np.all(np.isfinite(im)):
        raise ValueError("contact_patch_radius: img has non-finite pixels")
    lo, hi = np.percentile(im, 1.0), np.percentile(im, 99.9)
    if not (hi > lo):
        raise ValueError("contact_patch_radius: no contrast (flat image)")
    t = 0.5 * (lo + hi)
    mask = im > t
    cnt = int(mask.sum())
    if cnt < 30:
        raise ValueError("contact_patch_radius: no bright contact patch (only %d px above threshold)" % cnt)
    H, W = im.shape
    rows, cols = np.nonzero(mask)
    cy, cx = float(rows.mean()), float(cols.mean())
    r_t = math.sqrt(cnt / math.pi)
    if r_t < 3.0:
        raise ValueError("contact_patch_radius: contact patch too small (r=%.2f px)" % r_t)
    rp = float(ring_px)
    if cy - r_t - 2 * rp < 0 or cx - r_t - 2 * rp < 0 or cy + r_t + 2 * rp > H - 1 or cx + r_t + 2 * rp > W - 1:
        raise ValueError("contact_patch_radius: contact patch touches the window border")
    Y, X = np.mgrid[0:H, 0:W]
    R = np.hypot(Y - cy, X - cx)
    inner = R < max(r_t - rp, 1.5)
    ring = (R > r_t + rp) & (R < r_t + 2 * rp)
    assert int(inner.sum()) >= 1 and int(ring.sum()) >= 8
    fg, bg = float(np.median(im[inner])), float(np.median(im[ring]))
    if not (fg > bg):
        raise ValueError("contact_patch_radius: patch is not brighter than its surroundings")
    sel = R < r_t + rp
    cov = (im[sel] - bg) / (fg - bg)
    s = float(cov.sum())
    if not (s > 0):
        raise ValueError("contact_patch_radius: non-positive covered area")
    cyw = float(np.sum(cov * Y[sel]) / s)
    cxw = float(np.sum(cov * X[sel]) / s)
    a_px = math.sqrt(s / math.pi)
    inner_m = np.zeros_like(mask)
    inner_m[1:-1, 1:-1] = mask[1:-1, 1:-1] & mask[:-2, 1:-1] & mask[2:, 1:-1] & mask[1:-1, :-2] & mask[1:-1, 2:]
    edge = np.argwhere(mask & ~inner_m).astype(np.float64)
    return {"a": a_px * pitch, "a_px": a_px, "a_threshold": r_t * pitch, "centre": (cyw, cxw), "fg": fg, "bg": bg,
            "edge_points": edge}

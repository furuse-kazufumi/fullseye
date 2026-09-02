# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""render_shade — 法線マップに鏡面反射(specular)を足す静止 3D シェーディング。

既存のシェーディングは **拡散のみ(Lambertian)** だった
(``photometric.render_lambertian`` / ``match3d.render_shaded``)。拡散反射は
``N·L`` に比例した滑らかな明暗しか作れず、金属・プラスチック・濡れた面のような
「テカリ(鏡面ハイライト)」を持てない。ハイライトこそが素材感と立体感を一目で
伝えるので、静止画で 3D を「映えさせる」には鏡面項が要る。

本モジュールは 2 つの古典的レンダ手法を numpy だけで足す:

  * :func:`phong_shade` — Phong 反射モデル。環境光 + 拡散 + **鏡面**。光源方向 ``L`` を
    面法線 ``N`` で鏡面反射した理想反射方向 ``R`` が視線 ``V`` に揃うほど鋭く光る
    (``spec = max(R·V, 0)^shininess``)。ハイライトのピークは拡散最大(``N=L``)ではなく
    **半角方向**(``N = normalize(L+V)``)に立つ — これが拡散だけでは決して出せない情報。
  * :func:`matcap_shade` — MatCap(material capture / lit sphere)。ある素材を球に
    ライティングして撮った 1 枚のテクスチャを、視空間法線の ``(nx, ny)`` をテクスチャ
    座標に写して引くだけで、任意形状に同じ素材の見えを転写する。ライト計算ゼロで
    金属・粘土・トゥーンなど「素材の見え」を丸ごと持ってこられる(DCC/ゲームの定番)。

規約(既存シェーダと一致):
  * ``normals`` は float ``(H, W, 3)``。長さ 0 のベクトルは背景(``render3d.render_mesh``
    の空画素)とみなし、出力を 0(背景)にする — 背景を誤って光らせない。
  * ``light`` / ``view`` は「面から光源へ / 面から視点へ」向かう方向ベクトル(内部で単位化)。
    ``render_lambertian`` / ``render_shaded`` と同じ向き規約。
  * カメラは ``render3d`` に合わせ ``-Z`` を見る(視点は ``+Z`` 側)ので ``view=(0,0,1)`` が既定。

honest な前提: これは **解析的な局所反射モデル** であり、相互反射・環境マップ・
影・フレネルは含まない(影は ``render3d`` の可視性、透明体は ``match3d`` の
``refract`` / ``fresnel_reflectance`` が別途担当)。鏡面ローブは経験的な
``cos^n`` で、物理ベース(GGX 等)ではない。それでも「拡散に鏡面ハイライトを足す」
という目的には十分で、ハイライト位置は反射幾何と解析的に一致する(GT 検証可能)。

Reference (public): B. T. Phong, "Illumination for Computer Generated Pictures",
CACM 18(6), 1975. MatCap は Sphere Environment Mapping の実務系譜(ZBrush 等)。
"""
from __future__ import annotations

import numpy as np

__all__ = ["phong_shade", "matcap_shade", "lommel_seeliger_reflectance",
           "hapke_reflectance", "brdf_shade", "brdf_lommel_seeliger", "brdf_hapke"]

#: このノルム未満の法線ベクトルは背景(未被覆画素)とみなす。
_BG_EPS = 1e-6


def _as_normal_map(normals) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``normals`` を float ``(H, W, 3)`` に検証し、単位法線と前景マスクを返す。

    戻り値 ``(Nunit, mask, mag)``: ``Nunit`` は前景画素で単位化した法線
    (背景は 0)、``mask`` は ``|N| > _BG_EPS`` の bool ``(H, W)``、``mag`` は元の長さ。
    fail-closed: 形状不正・非有限は ``ValueError``。
    """
    N = np.asarray(normals, np.float64)
    if N.ndim != 3 or N.shape[2] != 3:
        raise ValueError(f"normals must be (H, W, 3), got shape {N.shape}")
    if N.shape[0] < 1 or N.shape[1] < 1:
        raise ValueError(f"normals must be non-empty, got shape {N.shape}")
    if not np.all(np.isfinite(N)):
        raise ValueError("normals contains non-finite values")
    mag = np.linalg.norm(N, axis=2)                 # (H, W)
    mask = mag > _BG_EPS
    safe = np.where(mask, mag, 1.0)[..., None]      # 0 除算回避(背景は後で 0 化)
    Nunit = np.where(mask[..., None], N / safe, 0.0)
    return Nunit, mask, mag


def _as_dir(v, name: str) -> np.ndarray:
    """長さ 3 の方向ベクトルを単位化して返す。fail-closed(形状/非有限/ゼロ長)。"""
    d = np.asarray(v, np.float64).reshape(-1)
    if d.shape != (3,):
        raise ValueError(f"{name} must be a length-3 vector, got shape {d.shape}")
    if not np.all(np.isfinite(d)):
        raise ValueError(f"{name} contains non-finite values")
    n = float(np.linalg.norm(d))
    if n < 1e-12:
        raise ValueError(f"{name} is a zero-length vector (undefined direction)")
    return d / n


def _as_coef(x, name: str) -> float:
    """陰影係数を検証(有限・非負)。fail-closed。"""
    f = float(x)
    if not np.isfinite(f) or f < 0.0:
        raise ValueError(f"{name} must be a finite, non-negative number, got {x!r}")
    return f


def phong_shade(normals, view=(0.0, 0.0, 1.0), light=(0.0, 0.0, 1.0),
                ambient: float = 0.1, diffuse: float = 0.8,
                specular: float = 0.5, shininess: float = 32.0,
                clip: bool = True) -> np.ndarray:
    """Phong 反射モデルで法線マップを陰影付け(環境光 + 拡散 + **鏡面**)。→ ``(H, W)``。

    各前景画素で単位法線 ``N`` に対し、光源方向 ``L`` を ``N`` で鏡面反射した理想反射方向
    ``R = 2(N·L)N − L`` を求め、視線 ``V`` との一致で鏡面項を作る::

        I = ambient + diffuse * max(N·L, 0) + specular * max(R·V, 0)^shininess

    鏡面項は光の当たる面(``N·L > 0``)にのみ乗る。``render_lambertian`` に鏡面ローブを
    足したもので、ハイライトのピークは拡散最大(``N=L``)ではなく **半角方向**
    ``N = normalize(L+V)`` に立つ(このとき ``R=V`` で ``R·V=1``)。

    背景(長さ 0 の法線 = ``render3d.render_mesh`` の空画素)は 0。``clip=True`` で出力を
    ``[0, 1]`` にクリップ(表示向き)、``clip=False`` で生の加算強度を返す(``argmax`` で
    ハイライト位置を厳密に取りたいときはこちら — 飽和で頂点が同点にならない)。

    引数:
      * ``normals``  : float ``(H, W, 3)`` 法線マップ(視空間、視点向き。長さ 0 = 背景)。
      * ``view``     : 面→視点の方向(既定 ``(0,0,1)`` = ``render3d`` の視点)。
      * ``light``    : 面→光源の方向。
      * ``ambient/diffuse/specular`` : 各項の係数(有限・非負)。
      * ``shininess``: 鏡面ローブの鋭さ(> 0。大きいほど鋭い/小さいほど広い)。
      * ``clip``     : ``[0,1]`` にクリップするか。

    fail-closed: 形状不正・非有限・ゼロ長方向・非正の ``shininess``・負係数は ``ValueError``。
    """
    Nn, mask, _ = _as_normal_map(normals)
    V = _as_dir(view, "view")
    L = _as_dir(light, "light")
    ka = _as_coef(ambient, "ambient")
    kd = _as_coef(diffuse, "diffuse")
    ks = _as_coef(specular, "specular")
    sh = float(shininess)
    if not np.isfinite(sh) or sh <= 0.0:
        raise ValueError(f"shininess must be a finite positive number, got {shininess!r}")

    ndl = np.einsum("ijk,k->ij", Nn, L)             # N·L(生)
    lit = ndl > 0.0                                 # 光の当たる面のみ鏡面を許す
    ndl_pos = np.clip(ndl, 0.0, None)

    # R = 2(N·L)N − L(光源方向を法線で鏡面反射した理想反射方向)
    R = 2.0 * ndl[..., None] * Nn - L
    rdv = np.clip(np.einsum("ijk,k->ij", R, V), 0.0, None)
    spec = ks * np.where(lit, np.power(rdv, sh), 0.0)

    img = ka + kd * ndl_pos + spec
    img = np.where(mask, img, 0.0)                  # 背景は暗く(誤点灯を防ぐ)
    if clip:
        img = np.clip(img, 0.0, 1.0)
    return img.astype(np.float64)


def matcap_shade(normals, matcap) -> np.ndarray:
    """MatCap: 視空間法線を lit-sphere テクスチャに写して素材の見えを転写。→ ``(H, W[, C])``。

    視空間の単位法線 ``(nx, ny)``(``[-1,1]``)をテクスチャ座標に写像し
    (``u = (nx+1)/2``, ``v = (1−ny)/2``、行方向で y を反転)、``matcap`` 画像を
    **双線形補間** で引く。ライト計算をせず、球にライティングして撮った 1 枚の素材見えを
    任意形状へそのまま貼れる(金属・粘土・トゥーンなど)。

    ``matcap`` は正方に近い lit-sphere テクスチャ:
      * グレースケール ``(h, w)``      → 出力 ``(H, W)``
      * カラー ``(h, w, C)``(C 任意)  → 出力 ``(H, W, C)``

    背景(長さ 0 の法線)は 0。テクスチャ座標は端でクランプ(球外縁の法線 ``|(nx,ny)|→1`` は
    テクスチャ縁を指す)。

    fail-closed: 形状不正・非有限・小さすぎる(``h,w < 2``)テクスチャは ``ValueError``。
    """
    Nn, mask, _ = _as_normal_map(normals)
    M = np.asarray(matcap, np.float64)
    squeeze = False
    if M.ndim == 2:
        M = M[..., None]                            # (h, w) -> (h, w, 1)
        squeeze = True
    elif M.ndim != 3:
        raise ValueError(f"matcap must be (h, w) or (h, w, C), got shape {M.shape}")
    if not np.all(np.isfinite(M)):
        raise ValueError("matcap contains non-finite values")
    h, w = M.shape[0], M.shape[1]
    if h < 2 or w < 2:
        raise ValueError(f"matcap must be at least 2x2, got {(h, w)}")

    nx = Nn[..., 0]
    ny = Nn[..., 1]
    # 法線 (nx, ny) ∈ [-1,1] → テクスチャ座標(u=列, v=行、y 反転)
    u = (nx * 0.5 + 0.5) * (w - 1)
    v = (0.5 - ny * 0.5) * (h - 1)

    u0 = np.floor(u).astype(np.int64)
    v0 = np.floor(v).astype(np.int64)
    fu = (u - u0)[..., None]                         # (H, W, 1)
    fv = (v - v0)[..., None]
    u0c = np.clip(u0, 0, w - 1)
    u1c = np.clip(u0 + 1, 0, w - 1)
    v0c = np.clip(v0, 0, h - 1)
    v1c = np.clip(v0 + 1, 0, h - 1)

    c00 = M[v0c, u0c]                                # (H, W, C)
    c01 = M[v0c, u1c]
    c10 = M[v1c, u0c]
    c11 = M[v1c, u1c]
    top = c00 * (1.0 - fu) + c01 * fu
    bot = c10 * (1.0 - fu) + c11 * fu
    out = top * (1.0 - fv) + bot * fv               # 双線形

    out = np.where(mask[..., None], out, 0.0)
    if squeeze:
        out = out[..., 0]
    return out.astype(np.float64)


# --------------------------------------------------------------------------- #
# 惑星表面(レゴリス)の反射則 — Lommel-Seeliger / Hapke                        #
# --------------------------------------------------------------------------- #
# 小惑星の撮像は Lambert では再現できない(2026-09-03、イトカワの hero 画像への
# 指摘「影が不自然」の診断で確定)。Lambert は縁(limb)を暗く・明暗境界
# (terminator)をなだらかにするが、はやぶさ AMICA の実画像は縁まで明るく平坦で、
# 境界は粗さの影で鋭く落ちる。ここでは惑星測光の標準形を numpy で実装する:
#
#   * Lommel-Seeliger  r = (w/4π) · μ0/(μ0+μ)                 [sr^-1]
#   * Hapke (1981/1984/1986)
#       r = (w/4π) · μ0e/(μ0e+μe) · [(1+B(g))P(g) + H(μ0e)H(μe) − 1] · S(i,e,g,θ̄)
#     B(g) = B0 / (1 + tan(g/2)/h)                 対向効果(opposition surge)
#     P(g) = (1−ξ²)/(1 + 2ξ cos g + ξ²)^{3/2}        Henyey-Greenstein 1 葉(ξ<0 で後方散乱)
#     H(x) = (1+2x)/(1+2x√(1−w))                     Chandrasekhar H の Hapke 近似
#     S, μ0e, μe = Hapke 1984 の巨視的粗さ(θ̄)補正(下記 _hapke_roughness)
#
# 記号: μ0 = cos i(入射)、μ = cos e(射出)、g = 位相角(光源-面-視点)。
# 放射輝度係数(radiance factor, I/F)= π r。画像として返すのは I/F。
# 参照: Hapke, "Theory of Reflectance and Emittance Spectroscopy", Cambridge UP 1993/2012。
# Itokawa の典型値(Kitazato et al. 2008, Icarus 194): w≈0.42, ξ≈−0.35, B0≈0.87,
# h≈0.01, θ̄≈26°(S 型小惑星の標準的な組)。


def _check_w(w) -> float:
    ww = float(w)
    if not np.isfinite(ww) or ww <= 0.0 or ww > 1.0:
        raise ValueError(f"single-scattering albedo w must be in (0, 1], got {w!r}")
    return ww


def lommel_seeliger_reflectance(mu0, mu, w: float = 0.42) -> np.ndarray:
    """Lommel-Seeliger 双方向反射率 r = (w/4π)·μ0/(μ0+μ) [sr^-1](μ0 または μ ≤ 0 は 0)。

    ``mu0 = cos i``(入射余弦)、``mu = cos e``(射出余弦)、``w`` = 単一散乱アルベド。
    μ0 = μ のとき r = w/(8π)、μ0 → 0(明暗境界)で 0、μ → 0(縁)では有限で暗くならない
    ―― これが「縁まで明るい」小惑星画像の由来。fail-closed: w ∉ (0,1] は ``ValueError``。"""
    ww = _check_w(w)
    m0 = np.asarray(mu0, np.float64)
    m1 = np.asarray(mu, np.float64)
    if not (np.all(np.isfinite(m0)) and np.all(np.isfinite(m1))):
        raise ValueError("mu0 / mu contain non-finite values")
    lit = (m0 > 0.0) & (m1 > 0.0)
    den = np.where(lit, m0 + m1, 1.0)
    r = (ww / (4.0 * np.pi)) * np.where(lit, m0 / den, 0.0)
    return r.astype(np.float64)


def _hapke_H(x: np.ndarray, w: float) -> np.ndarray:
    """Chandrasekhar H 関数の Hapke(1981)近似 (1+2x)/(1+2x√(1−w))。"""
    gamma = np.sqrt(max(1.0 - w, 0.0))
    return (1.0 + 2.0 * x) / (1.0 + 2.0 * x * gamma)


def _hapke_roughness(mu0, mu, cos_g, theta_bar: float):
    """Hapke(1984)の巨視的粗さ補正 ``(mu0e, mu, S)`` を返す(θ̄ = 平均傾斜角 [rad])。

    表面が傾斜角分布(平均 θ̄)を持つ小面の集まりだとして、実効的な入射/射出余弦
    ``μ0e, μe`` と影の補正係数 ``S`` を求める。ψ は入射面と射出面の方位差
    (cos ψ = (cos g − μ0 μ)/(sin i sin e))。θ̄ = 0 では μ0e=μ0, μe=μ, S=1 に厳密に戻る
    (テストで固定)。i ≤ e と i > e で式が入れ替わる(Hapke 1993 §12.C.4)。"""
    m0 = np.clip(np.asarray(mu0, np.float64), 0.0, 1.0)
    m1 = np.clip(np.asarray(mu, np.float64), 0.0, 1.0)
    if theta_bar <= 0.0:
        return m0, m1, np.ones_like(m0)
    tb = float(theta_bar)
    tan_tb = np.tan(tb)
    cot_tb = 1.0 / tan_tb
    chi = 1.0 / np.sqrt(1.0 + np.pi * tan_tb * tan_tb)
    i = np.arccos(m0)
    e = np.arccos(m1)
    si, se = np.sin(i), np.sin(e)
    with np.errstate(divide="ignore", invalid="ignore"):
        cpsi = (np.asarray(cos_g, np.float64) - m0 * m1) / np.where(si * se > 1e-9, si * se, 1.0)
    cpsi = np.where(si * se > 1e-9, np.clip(cpsi, -1.0, 1.0), 1.0)
    psi = np.arccos(cpsi)
    f_psi = np.exp(-2.0 * np.tan(psi / 2.0))
    sin2_half = np.sin(psi / 2.0) ** 2

    def _cot(x):
        s = np.sin(x)
        return np.where(s > 1e-12, np.cos(x) / np.where(s > 1e-12, s, 1.0), 1e12)

    def E1(x):
        return np.exp(-(2.0 / np.pi) * cot_tb * _cot(x))

    def E2(x):
        return np.exp(-(1.0 / np.pi) * cot_tb * cot_tb * _cot(x) ** 2)

    def eta(x, cx, sx):
        return chi * (cx + sx * tan_tb * E2(x) / (2.0 - E1(x)))

    E1i, E2i, E1e, E2e = E1(i), E2(i), E1(e), E2(e)
    np.seterr(all="ignore")                    # 縁(i,e→90°)の 0/0 は下で 0 に潰す
    # i <= e の式
    den_a = 2.0 - E1e - (psi / np.pi) * E1i
    mu0e_a = chi * (m0 + si * tan_tb * (cpsi * E2e + sin2_half * E2i) / den_a)
    mue_a = chi * (m1 + se * tan_tb * (E2e - sin2_half * E2i) / den_a)
    S_a = (mue_a / eta(e, m1, se)) * (m0 / eta(i, m0, si)) * chi \
        / (1.0 - f_psi + f_psi * chi * (m0 / eta(i, m0, si)))
    # i > e の式
    den_b = 2.0 - E1i - (psi / np.pi) * E1e
    mu0e_b = chi * (m0 + si * tan_tb * (E2i - sin2_half * E2e) / den_b)
    mue_b = chi * (m1 + se * tan_tb * (cpsi * E2i + sin2_half * E2e) / den_b)
    S_b = (mue_b / eta(e, m1, se)) * (m0 / eta(i, m0, si)) * chi \
        / (1.0 - f_psi + f_psi * chi * (m1 / eta(e, m1, se)))
    use_a = i <= e
    mu0e = np.where(use_a, mu0e_a, mu0e_b)
    mue = np.where(use_a, mue_a, mue_b)
    S = np.where(use_a, S_a, S_b)
    S = np.where(np.isfinite(S), np.clip(S, 0.0, None), 0.0)
    return np.clip(mu0e, 0.0, 1.0), np.clip(mue, 1e-9, 1.0), S


def hapke_reflectance(mu0, mu, phase, *, w: float = 0.42, g: float = -0.35,
                      B0: float = 0.87, h: float = 0.01, roughness_deg: float = 0.0,
                      multiple_scattering: bool = True) -> np.ndarray:
    """Hapke 双方向反射率 r [sr^-1](単一散乱 + 対向効果 + 多重散乱 H + 粗さ θ̄)。

    引数:
      * ``mu0``/``mu``  cos i / cos e(配列可)。``phase``  位相角 g [rad](スカラー or 配列)。
      * ``w``  単一散乱アルベド (0,1]。``g``  Henyey-Greenstein 非対称パラメータ (−1,1)
        (負 = 後方散乱)。``B0``/``h``  対向効果の振幅/幅。``roughness_deg``  平均傾斜角 θ̄。
      * ``multiple_scattering=False`` で H 項を落とす → r = Lommel-Seeliger × (1+B(g)) P(g)
        (テストで固定する極限)。

    fail-closed: w ∉ (0,1]、|g| ≥ 1、B0/h/θ̄ が負・非有限は ``ValueError``。
    honest: H は Hapke 1981 の近似式、粗さは Hapke 1984 の解析近似で、多重散乱への粗さの
    影響は Hapke の処方どおり μ0e/μe の置換のみ(モンテカルロではない)。"""
    ww = _check_w(w)
    xi = float(g)
    if not np.isfinite(xi) or abs(xi) >= 1.0:
        raise ValueError(f"Henyey-Greenstein parameter g must be in (-1, 1), got {g!r}")
    b0, hh, tb = float(B0), float(h), float(roughness_deg)
    for nm, val in (("B0", b0), ("h", hh), ("roughness_deg", tb)):
        if not np.isfinite(val) or val < 0.0:
            raise ValueError(f"{nm} must be finite and >= 0, got {val!r}")
    if hh == 0.0 and b0 > 0.0:
        raise ValueError("h must be > 0 when B0 > 0 (opposition surge width)")
    m0 = np.asarray(mu0, np.float64)
    m1 = np.asarray(mu, np.float64)
    ph = np.asarray(phase, np.float64)
    if not (np.all(np.isfinite(m0)) and np.all(np.isfinite(m1)) and np.all(np.isfinite(ph))):
        raise ValueError("mu0 / mu / phase contain non-finite values")
    m0, m1, ph = np.broadcast_arrays(m0, m1, ph)
    cos_g = np.cos(ph)
    lit = (m0 > 0.0) & (m1 > 0.0)
    mu0e, mue, S = _hapke_roughness(np.where(lit, m0, 0.0), np.where(lit, m1, 1.0),
                                    cos_g, np.deg2rad(tb))
    # 位相関数・対向効果
    P = (1.0 - xi * xi) / np.power(1.0 + 2.0 * xi * cos_g + xi * xi, 1.5)
    B = b0 / (1.0 + np.tan(np.abs(ph) / 2.0) / hh) if b0 > 0.0 else np.zeros_like(ph)
    bracket = (1.0 + B) * P
    if multiple_scattering:
        bracket = bracket + _hapke_H(mu0e, ww) * _hapke_H(mue, ww) - 1.0
    den = np.where(lit, mu0e + mue, 1.0)
    r = (ww / (4.0 * np.pi)) * np.where(lit, mu0e / den, 0.0) * bracket * S
    return np.where(lit, np.clip(r, 0.0, None), 0.0).astype(np.float64)


def brdf_shade(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0), model: str = "lommel_seeliger",
               **params) -> np.ndarray:
    """法線マップを惑星測光の反射則で陰影付けし放射輝度係数 I/F = π·r の ``(H, W)`` を返す。

    ``model``: ``'lambert'``(I/F = w·μ0)/ ``'lommel_seeliger'`` / ``'hapke'``。``params`` は
    :func:`hapke_reflectance` の引数(``w, g, B0, h, roughness_deg, multiple_scattering``;
    lambert / lommel_seeliger は ``w`` のみ使う)。``light``/``view`` は面→光源 / 面→視点の
    方向(平行光・正射影近似: 位相角は画面内で一定)。背景(長さ 0 の法線)は 0。"""
    Nn, mask, _ = _as_normal_map(normals)
    L = _as_dir(light, "light")
    Vd = _as_dir(view, "view")
    if model not in ("lambert", "lommel_seeliger", "hapke"):
        raise ValueError(f"model must be lambert|lommel_seeliger|hapke, got {model!r}")
    mu0 = np.clip(np.einsum("ijk,k->ij", Nn, L), 0.0, 1.0)
    mu = np.clip(np.einsum("ijk,k->ij", Nn, Vd), 0.0, 1.0)
    if model == "lambert":
        ww = _check_w(params.get("w", 0.42))
        extra = set(params) - {"w"}
        if extra:
            raise ValueError(f"unknown parameters for lambert: {sorted(extra)}")
        img = ww * mu0
    elif model == "lommel_seeliger":
        extra = set(params) - {"w"}
        if extra:
            raise ValueError(f"unknown parameters for lommel_seeliger: {sorted(extra)}")
        img = np.pi * lommel_seeliger_reflectance(mu0, mu, w=params.get("w", 0.42))
    else:
        phase = float(np.arccos(np.clip(float(L @ Vd), -1.0, 1.0)))
        img = np.pi * hapke_reflectance(mu0, mu, phase, **params)
    return np.where(mask, img, 0.0).astype(np.float64)


def brdf_lommel_seeliger(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0),
                         w: float = 0.42) -> np.ndarray:
    """Lommel-Seeliger 反射則(縁まで明るいレゴリス)で法線マップを陰影付けし I/F ``(H, W)`` を返す。

    Lambert(``phong_shade`` の拡散項)は縁(μ→0)で 0 になるが、Lommel-Seeliger は
    μ0/(μ0+μ) なので縁でも μ0 のまま明るく、小惑星・月の「平坦な円盤」の見えになる。
    ``w`` = 単一散乱アルベド。fail-closed(法線形状・w の範囲)。"""
    return brdf_shade(normals, light=light, view=view, model="lommel_seeliger", w=w)


def brdf_hapke(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0), w: float = 0.42,
               g: float = -0.35, B0: float = 0.87, h: float = 0.01,
               roughness_deg: float = 26.0) -> np.ndarray:
    """Hapke 反射則(対向効果 + 多重散乱 + 巨視的粗さ θ̄)で法線マップを陰影付けし I/F ``(H, W)`` を返す。

    既定値はイトカワの S 型典型値(Kitazato et al. 2008): w=0.42, g=−0.35, B0=0.87,
    h=0.01, θ̄=26°。位相角は ``light``/``view`` から一定値として求める(平行光・正射影近似)。
    fail-closed: 各パラメータの範囲外・法線形状不正は ``ValueError``。"""
    return brdf_shade(normals, light=light, view=view, model="hapke", w=w, g=g, B0=B0, h=h,
                      roughness_deg=roughness_deg)

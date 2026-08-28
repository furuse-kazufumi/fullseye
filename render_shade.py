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

__all__ = ["phong_shade", "matcap_shade"]

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

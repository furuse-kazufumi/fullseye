# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""glassmirror — ガラスと鏡面の光学(界面・吸収・分散を閉じた式で)。

動機(2026-09-04、ユーザー「光学的にガラスや鏡面を扱う op が沢山あると良いね」):
既存の `match3d` にはスカラの Fresnel と 1 本用の屈折があるだけで、**金属鏡の色**
(複素屈折率)・**ガラスの吸収**(Beer–Lambert)・**平行平板の多重反射**・**プリズムの分散**
が無かった。ここはそれを埋める層で、どれも光線追跡を要さない**閉じた式**である。

内容(10 op):
  界面    `fresnel_dielectric`(誘電体、s/p/無偏光)/ `fresnel_conductor`(金属、複素屈折率)
          `brewster_angle_deg` / `critical_angle_deg`
  金属鏡  `metal_optical_constants`(Ag/Au/Al/Cu/Cr の n,k)/ `metal_mirror_rgb`(鏡の色)
  ガラス  `beer_lambert_transmittance`(吸収)/ `slab_transmittance`(平行平板の多重反射)
  光線    `refract_rays`(**画素ごとに TIR を判定する**ベクトル版)
  分散    `prism_min_deviation_deg`(最小偏角、実硝材の分散つき)

既存資産との棲み分け(再実装せず import して合成):
  * `match3d.reflect` / `refract` / `fresnel_reflectance` / `snell_angle` は
    **スカラ・単一光線の教材版**。`refract` は「1 本でも TIR ならバッチ全体が None」
    という契約で、画像サイズのバッチには使えない ―― こちらの `refract_rays` は
    per-ray マスクを返す。`fresnel_reflectance` はスカラ専用(float を要求する番人つき)。
  * 硝材の分散は `raytrace.refractive_index`(Sellmeier、実硝材 20 種)をそのまま使う。
    ここで硝材表を作り直さない ―― プリズムの虹が**実在の硝材の分散**で出るのが要点。
  * 分光 → RGB は `matappear.spectrum_to_srgb`(CIE 1931 + D65 白色順応)。金属の色は
    塗るのではなく **n,k から反射スペクトルを計算して等色関数で落とす**。
  * 薄膜干渉(`matappear.thin_film_reflectance`)は「膜」、こちらは「界面と体積」。

来歴(公開文献のみ): Born & Wolf, *Principles of Optics* §1.5–1.6(Fresnel・全反射・平板)/
Johnson & Christy, *Phys. Rev. B* 6, 4370 (1972)(Au/Ag/Cu の n,k)/ Rakić et al.,
*Appl. Opt.* 37, 5271 (1998)(Al)/ Hecht, *Optics* §5.5(プリズムの最小偏角)。

規約: 角度は度、波長は nm、距離は mm、吸収係数は 1/mm。cos_i は入射側媒質での
入射角の cos(0–1)。返す RGB は線形 sRGB。
"""
from __future__ import annotations

import numpy as np

import matappear

#: 金属の複素屈折率 n + ik(可視域の粗い表引き、線形補間して使う)。
#: 出典: Au/Ag/Cu = Johnson & Christy 1972、Al = Rakić 1998、Cr = Johnson & Christy 1974。
#: **粗い表**であることを隠さない: 5 点の線形補間なので、細い吸収構造は再現しない。
#: それでも「銀はほぼ中性で最も明るい / 金と銅は 500 nm 付近で立ち上がる赤黄色 /
#: アルミはやや暗いが平坦」という**色の順序**は正しく出る(テストで固定)。
_METAL_NK = {
    "ag": ((400.0, 0.173, 1.950), (500.0, 0.130, 2.920), (600.0, 0.124, 3.730),
           (700.0, 0.140, 4.520), (800.0, 0.160, 5.290)),
    "au": ((400.0, 1.660, 1.956), (500.0, 0.971, 1.866), (600.0, 0.247, 2.970),
           (700.0, 0.131, 3.842), (800.0, 0.156, 4.838)),
    "al": ((400.0, 0.490, 4.860), (500.0, 0.769, 6.080), (600.0, 1.200, 7.260),
           (700.0, 1.830, 8.310), (800.0, 2.630, 8.600)),
    "cu": ((400.0, 1.180, 2.210), (500.0, 1.120, 2.600), (600.0, 0.272, 3.240),
           (700.0, 0.213, 4.049), (800.0, 0.260, 5.260)),
    "cr": ((400.0, 2.140, 2.960), (500.0, 2.760, 3.310), (600.0, 3.130, 3.330),
           (700.0, 3.280, 3.310), (800.0, 3.350, 3.320)),
}

METALS = tuple(sorted(_METAL_NK))


def _arr(v, name: str, op: str) -> np.ndarray:
    a = np.asarray(v, dtype=np.float64)
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{op}: {name} contains non-finite values")
    return a


def _index(v, name: str, op: str) -> float:
    x = float(v)
    if not np.isfinite(x) or x <= 0.0:
        raise ValueError(f"{op}: {name} must be a positive refractive index: got {v!r}")
    return x


def _cos(cos_i, op: str) -> np.ndarray:
    c = _arr(cos_i, "cos_i", op)
    if np.any(c < -1.0) or np.any(c > 1.0):
        raise ValueError(f"{op}: cos_i must lie in [-1, 1]")
    return np.abs(c)


def _pol(polarization: str, op: str) -> str:
    p = str(polarization).lower()
    if p not in ("unpolarized", "s", "p"):
        raise ValueError(f"{op}: polarization must be 'unpolarized', 's' or 'p': got {polarization!r}")
    return p


# --------------------------------------------------------------------------- #
# 1. 界面(誘電体・金属)                                                        #
# --------------------------------------------------------------------------- #
def fresnel_dielectric(cos_i, n1=1.0, n2=1.5, polarization="unpolarized") -> np.ndarray:
    """誘電体界面の Fresnel 反射率(配列対応、全反射を含む)。

    cos_i: 入射角の cos(スカラまたは配列、0–1)。
    n1/n2: 入射側 / 透過側の実屈折率。
    polarization: "unpolarized"(既定、s と p の平均)/ "s" / "p"。

    返り値: 反射率 R(cos_i と同形、0–1)。臨界角を超えた入射は **厳密に 1.0**(全反射)。

    検算(テストで固定): 垂直入射で ((n1−n2)/(n1+n2))²(air→BK7 = 0.04)、
    Brewster 角で p 偏光が 0(1e-15 未満)、臨界角超で 1.0。
    透過率は 1 − R(吸収の無い界面なのでエネルギーが閉じる)。
    """
    op = "fresnel_dielectric"
    ci = _cos(cos_i, op)
    a, b = _index(n1, "n1", op), _index(n2, "n2", op)
    p = _pol(polarization, op)
    sin2t = (a / b) ** 2 * (1.0 - ci ** 2)
    tir = sin2t > 1.0
    ct = np.sqrt(np.maximum(1.0 - sin2t, 0.0))
    rs = ((a * ci - b * ct) / np.maximum(a * ci + b * ct, 1e-300)) ** 2
    rp = ((a * ct - b * ci) / np.maximum(a * ct + b * ci, 1e-300)) ** 2
    r = rs if p == "s" else rp if p == "p" else 0.5 * (rs + rp)
    return np.where(tir, 1.0, r)


def fresnel_conductor(cos_i, n, k, polarization="unpolarized") -> np.ndarray:
    """金属(複素屈折率 n + ik)界面の反射率。入射側は真空/空気を仮定。

    cos_i: 入射角の cos。n / k: 実部 / 消衰係数(配列可、cos_i とブロードキャスト)。
    polarization: "unpolarized" / "s" / "p"。

    返り値: 反射率 R。**金属に「臨界角」は無い** — k>0 なので透過波は減衰波であり、
    どの角度でも一部が吸収される(R<1)。

    式: η² = (n+ik)² − sin²θ として rs = (cosθ − η)/(cosθ + η)、
    rp = ((n+ik)² cosθ − η)/((n+ik)² cosθ + η)(Born & Wolf §13.2 の複素形)。
    """
    op = "fresnel_conductor"
    ci = _cos(cos_i, op)
    nn = _arr(n, "n", op)
    kk = _arr(k, "k", op)
    if np.any(nn <= 0.0) or np.any(kk < 0.0):
        raise ValueError(f"{op}: n must be > 0 and k must be >= 0")
    p = _pol(polarization, op)
    m = nn + 1j * kk
    s2 = 1.0 - ci ** 2
    eta = np.sqrt(m ** 2 - s2)
    rs = (ci - eta) / (ci + eta)
    rp = (m ** 2 * ci - eta) / (m ** 2 * ci + eta)
    Rs, Rp = np.abs(rs) ** 2, np.abs(rp) ** 2
    return Rs if p == "s" else Rp if p == "p" else 0.5 * (Rs + Rp)


def brewster_angle_deg(n1=1.0, n2=1.5) -> float:
    """Brewster 角 [deg] = atan(n2/n1)。この角度で p 偏光の反射が厳密に 0 になる。

    偏光板でガラスの映り込みが消える角度そのもの。`fresnel_dielectric(..., "p")` に
    この角度の cos を渡すと 0 が返る(テストで 1e-15 未満を確認)。
    """
    op = "brewster_angle_deg"
    return float(np.degrees(np.arctan(_index(n2, "n2", op) / _index(n1, "n1", op))))


def critical_angle_deg(n1=1.5, n2=1.0) -> float:
    """全反射の臨界角 [deg] = asin(n2/n1)。n1 > n2 でなければ ValueError(存在しない)。

    ガラスから空気へ出るときだけ起きる。光ファイバ・プリズムの全反射面の設計値。
    """
    op = "critical_angle_deg"
    a, b = _index(n1, "n1", op), _index(n2, "n2", op)
    if a <= b:
        raise ValueError(f"{op}: total internal reflection needs n1 > n2: got n1={a}, n2={b}")
    return float(np.degrees(np.arcsin(b / a)))


# --------------------------------------------------------------------------- #
# 2. 金属鏡の色                                                                 #
# --------------------------------------------------------------------------- #
def metal_optical_constants(metal="ag", wavelength_nm=550.0):
    """金属の複素屈折率 (n, k) を波長で引く(可視域、線形補間)。

    metal: "ag" / "au" / "al" / "cu" / "cr"(`METALS`)。
    wavelength_nm: スカラまたは配列 [nm]。表の外は端の値で頭打ち(外挿しない)。

    返り値: (n, k) の 2 要素タプル(入力と同形の配列)。
    出典は表の定義(`_METAL_NK`)を参照 — 5 点の粗い表であることを隠さない。
    """
    op = "metal_optical_constants"
    key = str(metal).lower()
    if key not in _METAL_NK:
        raise ValueError(f"{op}: unknown metal {metal!r}; known: {METALS}")
    w = _arr(wavelength_nm, "wavelength_nm", op)
    if np.any(w <= 0):
        raise ValueError(f"{op}: wavelength_nm must be positive")
    tab = np.asarray(_METAL_NK[key], dtype=np.float64)
    n = np.interp(w, tab[:, 0], tab[:, 1])
    k = np.interp(w, tab[:, 0], tab[:, 2])
    return n, k


def metal_mirror_rgb(metal="ag", cos_i=1.0, samples=61) -> np.ndarray:
    """金属鏡の**色**(線形 sRGB)。n,k → 分光反射率 → CIE 等色関数 → sRGB。

    metal: `METALS` のいずれか。cos_i: 入射角の cos(スカラまたは配列)。
    samples: 380–780 nm を刻む点数。

    返り値: cos_i の形 + 末尾 3 の線形 sRGB。**色を塗っていない**ので、金が黄色いのも
    銀が中性なのも表の n,k から出る(テストで R>G>B の順序と銀の中性を固定)。
    """
    op = "metal_mirror_rgb"
    ci = _cos(cos_i, op)
    grid = np.linspace(380.0, 780.0, int(samples))
    n, k = metal_optical_constants(metal, grid)
    R = fresnel_conductor(ci[..., None], n, k)
    return matappear.spectrum_to_srgb(grid, R)


# --------------------------------------------------------------------------- #
# 3. ガラスの体積(吸収)と平行平板                                              #
# --------------------------------------------------------------------------- #
def beer_lambert_transmittance(path_mm, sigma_per_mm=0.01) -> np.ndarray:
    """Beer–Lambert の内部透過率 T = exp(−σ·L)。色ガラス・厚いガラスの緑かぶり。

    path_mm: 媒質中の光路長 [mm] (配列可、非負)。
    sigma_per_mm: 吸収係数 [1/mm] (配列可 — 波長ごとに変えれば**色**になる)。

    返り値: 内部透過率(0–1)。界面の反射は含まない(それは `slab_transmittance`)。
    """
    op = "beer_lambert_transmittance"
    L = _arr(path_mm, "path_mm", op)
    s = _arr(sigma_per_mm, "sigma_per_mm", op)
    if np.any(L < 0):
        raise ValueError(f"{op}: path_mm must be >= 0")
    if np.any(s < 0):
        raise ValueError(f"{op}: sigma_per_mm must be >= 0 (negative = amplification)")
    return np.exp(-s * L)


def slab_transmittance(cos_i, n1=1.0, n2=1.5, thickness_mm=3.0, sigma_per_mm=0.0) -> np.ndarray:
    """平行平板(窓ガラス)の透過率。**両面での多重反射**と内部吸収を含む。

    cos_i / n1 / n2 / thickness_mm / sigma_per_mm は上記と同じ。

    返り値: 全透過率 T。式は T = (1−R)²·a / (1 − R²·a²)、a = 内部透過率
    (板内の斜め光路 L = d/cosθ_t を使う)。無限級数の和 = 多重反射を数え落とさない形。

    検算: 吸収 0・垂直入射の air→BK7(n=1.5)板は T = 0.9231(= 2n/(n²+1) の
    よく知られた値)。σ を上げると単調に下がり、臨界角超(板の内側から)では 0。
    """
    op = "slab_transmittance"
    ci = _cos(cos_i, op)
    a, b = _index(n1, "n1", op), _index(n2, "n2", op)
    d = float(thickness_mm)
    if not np.isfinite(d) or d < 0.0:
        raise ValueError(f"{op}: thickness_mm must be >= 0: got {thickness_mm!r}")
    R = fresnel_dielectric(ci, a, b)
    sin2t = (a / b) ** 2 * (1.0 - ci ** 2)
    tir = sin2t > 1.0
    ct = np.sqrt(np.maximum(1.0 - sin2t, 1e-300))
    path = d / ct
    inner = beer_lambert_transmittance(path, sigma_per_mm)
    T = (1.0 - R) ** 2 * inner / np.maximum(1.0 - (R * inner) ** 2, 1e-300)
    return np.where(tir, 0.0, T)


# --------------------------------------------------------------------------- #
# 4. 光線(ベクトル、per-ray TIR)                                               #
# --------------------------------------------------------------------------- #
def refract_rays(directions, normals, n1=1.0, n2=1.5):
    """Snell 屈折のベクトル版。**光線ごとに全反射を判定**して (方向, TIR マスク) を返す。

    directions: (..., 3) 入射方向(面へ向かう)。normals: (..., 3) 入射側の外向き法線。
    n1 / n2: 入射側 / 透過側の屈折率。

    返り値: (refracted (...,3), tir (...,)) —— TIR の光線は方向を**鏡面反射**で埋め、
    マスクを True にする(NaN を返さない: 下流のレンダが黙って穴を開けるより、
    物理的に正しい「全反射した」方向を返す方が使える)。

    ★ `match3d.refract` との違い: あちらは「1 本でも TIR ならバッチ全体が None」。
    画像サイズのバッチでは 1 画素の全反射で**全部が消える**ので、per-ray に直した。
    """
    op = "refract_rays"
    d = _arr(directions, "directions", op)
    m = _arr(normals, "normals", op)
    if d.shape[-1] != 3 or m.shape[-1] != 3:
        raise ValueError(f"{op}: directions/normals must have last axis 3")
    d = d / np.maximum(np.linalg.norm(d, axis=-1, keepdims=True), 1e-300)
    m = m / np.maximum(np.linalg.norm(m, axis=-1, keepdims=True), 1e-300)
    a, b = _index(n1, "n1", op), _index(n2, "n2", op)
    eta = a / b
    cosi = -np.sum(d * m, axis=-1, keepdims=True)
    sin2t = eta * eta * (1.0 - cosi ** 2)
    tir = (sin2t > 1.0)[..., 0]
    cost = np.sqrt(np.maximum(1.0 - sin2t, 0.0))
    refr = eta * d + (eta * cosi - cost) * m
    refl = d + 2.0 * cosi * m
    out = np.where(tir[..., None], refl, refr)
    return out / np.maximum(np.linalg.norm(out, axis=-1, keepdims=True), 1e-300), tir


# --------------------------------------------------------------------------- #
# 5. プリズムの分散                                                             #
# --------------------------------------------------------------------------- #
def prism_min_deviation_deg(wavelength_nm=550.0, apex_deg=60.0, glass="N-BK7") -> np.ndarray:
    """プリズムの最小偏角 [deg]。**実硝材の分散**で波長ごとに変わる = 虹が出る理由。

    wavelength_nm: スカラまたは配列 [nm]。**データ入力なので第 1 引数**
        (2026-09-04 の敵対的検証で判明: 台帳は「先頭 N 個が宣言 in 型のデータ」という
        規約なのに、この op だけ `apex_deg` を先頭に置いていた。波長の配列が
        `apex_deg` に入り `float(配列)` が**素の TypeError** を投げていた ―― 規約に
        揃えるのが正しい直し方で、番人を足すのは対症療法)。
    apex_deg: 頂角 A [deg]。glass: `raytrace.glass_catalog` の硝材名、または屈折率の数値。

    返り値: 最小偏角 δ_min = 2·asin(n·sin(A/2)) − A(Hecht §5.5)。n·sin(A/2) > 1 の
    波長は光が出られない(全反射)ので NaN。

    検算: N-BK7・A=60° で d 線(587.6 nm)の δ_min ≈ 38.9°、F 線(486.1)と C 線(656.3)の
    差(角分散)が **Abbe 数から予想される向き**(短波長ほど大きく曲がる)になる。
    """
    op = "prism_min_deviation_deg"
    if np.ndim(apex_deg) != 0:
        raise ValueError(f"{op}: apex_deg must be a scalar (the wavelength is the "
                         f"first argument): got shape={np.shape(apex_deg)}")
    A = float(apex_deg)
    if not np.isfinite(A) or not (0.0 < A < 180.0):
        raise ValueError(f"{op}: apex_deg must lie in (0, 180): got {apex_deg!r}")
    w = _arr(wavelength_nm, "wavelength_nm", op)
    if np.any(w <= 0):
        raise ValueError(f"{op}: wavelength_nm must be positive")
    if isinstance(glass, str):
        import raytrace
        n = np.array([raytrace.refractive_index(glass, float(x) / 1000.0) for x in np.atleast_1d(w)])
        n = n.reshape(w.shape) if w.shape else n[0]
    else:
        n = np.broadcast_to(_index(glass, "glass", op), w.shape if w.shape else ())
    half = np.radians(A / 2.0)
    s = n * np.sin(half)
    with np.errstate(invalid="ignore"):
        delta = 2.0 * np.degrees(np.arcsin(np.where(np.abs(s) <= 1.0, s, np.nan))) - A
    return delta

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""surfacelib — 金属・ガラス以外の素材と表面処理(粗い拡散・塗装・布・木・濡れ・腐食)。

動機(2026-09-04、ユーザー「他にもいろんな素材や表面を再現できるなら対応してほしい」):
`glassmirror` が界面と体積(ガラス・鏡面)、`metalfinish` が加工された金属面を担う。
残りの大半 ―― 紙・石膏・コンクリート・プラスチック・塗装・陶器・布・木・皮革・
濡れた面・錆びた面 ―― は **(1) 粗い拡散 (2) 透明な上塗り (3) 微細構造 (4) むら**
の 4 つの組み合わせで説明できる。ここはその 4 つを op にした層である。

内容(11 op):
  拡散    `oren_nayar`(粗い拡散。σ=0 で Lambert に厳密一致)
  上塗り  `clearcoat_shade`(塗装・釉薬・クリア塗り。Fresnel で下地を減衰させる)
          `metallic_flake_normals`(メタリック塗装のフレーク)
  布      `sheen_shade`(ベルベットの縁光沢)/ `weave_normals`(織り目・カーボン)
  木      `wood_grain`(年輪の接線場と色の変調)
  状態    `wetness`(濡れ = 拡散が暗くなり鏡面が増える)/ `corrosion_mask`(錆・緑青のむら)
          `subsurface_approx`(半透明の回り込み)
  ガラス面 `rough_transmission`(すりガラス: 直進成分と拡散成分の分配)
  一覧    `material_catalog`(素材名 → 既定パラメータ)

規約: 法線マップは (H,W,3)(長さ 0 = 背景)。方向はカメラ系、視線は +Z。
返す色は線形 sRGB(ガンマ前)。拡散のアルベドは 0–1。

来歴(公開文献のみ): Oren & Nayar, *SIGGRAPH* 1994(粗い拡散)/ Ashikhmin, Premože &
Shirley, *SIGGRAPH* 2000(微小面の分布と布)/ Burley, *SIGGRAPH Course* 2012
(clearcoat と sheen の実務モデル)/ Jensen et al., *SIGGRAPH* 2001(半透明)/
Lekner & Dorf, *Appl. Opt.* 1988(濡れた面が暗く見える理由)。
"""
from __future__ import annotations

import numpy as np

import glassmirror
import matappear

#: 素材名 → 既定パラメータ。値は見え方のための設計値で、実測の物性値ではない
#: (そこは正直に)。意味を持つのは**大小関係**: 紙 < プラ < 陶器 < 車の塗装 の順に
#: 上塗りが強く、コンクリート > 紙 > プラ の順に拡散が粗い。
_MATERIALS = {
    "paper":      {"roughness_deg": 22.0, "coat": 0.0,  "coat_rough": 0.0,  "sheen": 0.0},
    "plaster":    {"roughness_deg": 30.0, "coat": 0.0,  "coat_rough": 0.0,  "sheen": 0.0},
    "concrete":   {"roughness_deg": 35.0, "coat": 0.0,  "coat_rough": 0.0,  "sheen": 0.0},
    "rubber":     {"roughness_deg": 18.0, "coat": 0.05, "coat_rough": 0.30, "sheen": 0.0},
    "plastic":    {"roughness_deg": 8.0,  "coat": 0.5,  "coat_rough": 0.10, "sheen": 0.0},
    "ceramic":    {"roughness_deg": 5.0,  "coat": 0.9,  "coat_rough": 0.03, "sheen": 0.0},
    "car_paint":  {"roughness_deg": 6.0,  "coat": 1.0,  "coat_rough": 0.02, "sheen": 0.0},
    "wood":       {"roughness_deg": 20.0, "coat": 0.3,  "coat_rough": 0.15, "sheen": 0.0},
    "leather":    {"roughness_deg": 26.0, "coat": 0.2,  "coat_rough": 0.25, "sheen": 0.10},
    "fabric":     {"roughness_deg": 30.0, "coat": 0.0,  "coat_rough": 0.0,  "sheen": 0.55},
    "velvet":     {"roughness_deg": 34.0, "coat": 0.0,  "coat_rough": 0.0,  "sheen": 1.00},
}

MATERIALS = tuple(sorted(_MATERIALS))


def _dir(v, name: str, op: str) -> np.ndarray:
    a = np.asarray(v, dtype=np.float64)
    if a.shape[-1] != 3 or not np.all(np.isfinite(a)):
        raise ValueError(f"{op}: {name} must be a finite 3-vector")
    n = float(np.linalg.norm(a))
    if n < 1e-12:
        raise ValueError(f"{op}: {name} must not be zero-length")
    return a / n


def _unit_scalar(v, name: str, op: str, lo=0.0, hi=1.0) -> float:
    x = float(v)
    if not np.isfinite(x) or not (lo <= x <= hi):
        raise ValueError(f"{op}: {name} must lie in [{lo}, {hi}]: got {v!r}")
    return x


def _shape2(shape, op: str):
    s = tuple(int(v) for v in shape)
    if len(s) != 2 or min(s) < 1:
        raise ValueError(f"{op}: shape must be (H, W) with positive sides: got {shape!r}")
    return s


def material_catalog() -> dict:
    """素材名 → 既定パラメータ(拡散の粗さ / 上塗りの強さ・粗さ / 布の縁光沢)。

    実測の物性値ではなく見え方の設計値。意味があるのは順序(上塗り: 紙 < プラ <
    陶器 < 車の塗装 / 拡散の粗さ: コンクリート > 紙 > プラ)。
    """
    return {k: dict(v) for k, v in _MATERIALS.items()}


# --------------------------------------------------------------------------- #
# 1. 粗い拡散(Oren–Nayar)                                                      #
# --------------------------------------------------------------------------- #
def oren_nayar(normals, light=(0.3, 0.4, 0.87), view=(0.0, 0.0, 1.0),
               roughness_deg=20.0, albedo=1.0) -> np.ndarray:
    """粗い拡散面の陰影(Oren–Nayar)。紙・石膏・コンクリート・月の見え方。

    normals: (H, W, 3)。light / view: 面から光源 / 視点への方向。
    roughness_deg: 微小面の傾きの標準偏差 [deg]。**0 で Lambert に厳密一致**。
    albedo: 拡散反射率(スカラまたは (H,W))。

    返り値: (H, W) の放射輝度係数(0 以上)。

    なぜ Lambert では足りないか: Lambert は端(терminator)で cos に比例して落ちるが、
    粗い面は微小面の相互遮蔽と相互反射で**端が平らに明るいまま**になる。満月が
    円盤のように一様に見えるのがこれで、Lambert だと縁が暗くなって球に見えてしまう。
    """
    op = "oren_nayar"
    N, mask = matappear._normal_map(normals, op)
    L = _dir(light, "light", op)
    V = _dir(view, "view", op)
    s = float(roughness_deg)
    if not np.isfinite(s) or s < 0.0 or s > 90.0:
        raise ValueError(f"{op}: roughness_deg must lie in [0, 90]: got {roughness_deg!r}")
    alb = np.asarray(albedo, dtype=np.float64)
    if np.any(alb < 0.0):
        raise ValueError(f"{op}: albedo must be >= 0")

    ndl = np.clip(np.sum(N * L[None, None, :], axis=-1), 0.0, 1.0)
    ndv = np.clip(np.sum(N * V[None, None, :], axis=-1), 0.0, 1.0)
    sigma = np.radians(s)
    s2 = sigma ** 2
    A = 1.0 - 0.5 * s2 / (s2 + 0.33)
    B = 0.45 * s2 / (s2 + 0.09)
    ti = np.arccos(np.clip(ndl, -1.0, 1.0))
    to = np.arccos(np.clip(ndv, -1.0, 1.0))
    alpha = np.maximum(ti, to)
    beta = np.minimum(ti, to)
    # 方位角差の cos: 投影した方向どうしの内積
    li = L[None, None, :] - N * ndl[..., None]
    vo = V[None, None, :] - N * ndv[..., None]
    denom = np.maximum(np.linalg.norm(li, axis=-1) * np.linalg.norm(vo, axis=-1), 1e-12)
    cos_dphi = np.clip(np.sum(li * vo, axis=-1) / denom, -1.0, 1.0)
    out = alb * ndl * (A + B * np.maximum(cos_dphi, 0.0) * np.sin(alpha) * np.tan(beta))
    return np.where(mask & (ndl > 0.0), out, 0.0)


# --------------------------------------------------------------------------- #
# 2. 上塗り(塗装・釉薬・クリア)                                                 #
# --------------------------------------------------------------------------- #
def clearcoat_shade(base_rgb, normals, light=(0.3, 0.4, 0.87), view=(0.0, 0.0, 1.0),
                    ior=1.5, coat=1.0, coat_roughness=0.05) -> np.ndarray:
    """透明な上塗りを被せる(車の塗装・陶器の釉薬・光沢プラスチック)。

    base_rgb: 下地の色 (H,W,3) または (3,)。normals / light / view: 上記と同じ。
    ior: 上塗りの屈折率(クリア塗料 ~1.5)。coat: 上塗りの強さ(0–1)。
    coat_roughness: 上塗りのざらつき(0 = 完全な鏡面、大きいほどぼける)。

    返り値: (H, W, 3) 線形 sRGB。

    ★ 要点は**エネルギーの引き算**: 上塗りで反射した分だけ下地に届く光が減る。
    下地は (1 − F(入射)) × (1 − F(出射)) で減衰する ―― これを掛けないと、
    上塗りを足すほど全体が明るくなる(物理的にありえない)。
    """
    op = "clearcoat_shade"
    N, mask = matappear._normal_map(normals, op)
    L = _dir(light, "light", op)
    V = _dir(view, "view", op)
    c = _unit_scalar(coat, "coat", op)
    r = float(coat_roughness)
    if not np.isfinite(r) or r < 0.0:
        raise ValueError(f"{op}: coat_roughness must be >= 0: got {coat_roughness!r}")
    base = np.asarray(base_rgb, dtype=np.float64)
    if base.ndim == 1:
        base = np.broadcast_to(base.reshape(1, 1, -1), N.shape)
    if base.shape != N.shape:
        raise ValueError(f"{op}: base_rgb shape {base.shape} does not match normals {N.shape}")

    ndl = np.clip(np.sum(N * L[None, None, :], axis=-1), 0.0, 1.0)
    ndv = np.clip(np.sum(N * V[None, None, :], axis=-1), 0.0, 1.0)
    H = L + V
    H = H / max(float(np.linalg.norm(H)), 1e-12)
    ndh = np.clip(np.sum(N * H[None, None, :], axis=-1), 0.0, 1.0)

    F_in = glassmirror.fresnel_dielectric(np.maximum(ndl, 1e-9), 1.0, ior)
    F_out = glassmirror.fresnel_dielectric(np.maximum(ndv, 1e-9), 1.0, ior)
    # 上塗りの鏡面: 粗さを微小面のガウス分布として与える(r→0 で鏡のように細い)
    a = max(r, 1e-4)
    spec = np.exp(-np.arccos(ndh) ** 2 / (2.0 * a * a)) * glassmirror.fresnel_dielectric(
        np.maximum(ndh, 1e-9), 1.0, ior)
    through = (1.0 - c * F_in) * (1.0 - c * F_out)
    out = base * (ndl * through)[..., None] + (c * spec)[..., None]
    return np.clip(out, 0.0, None) * mask[..., None]


def metallic_flake_normals(shape, density=0.06, size_px=2.0, tilt=0.35, seed=0) -> np.ndarray:
    """メタリック塗装のフレーク(アルミ片)の法線場を作る。

    shape: (H, W)。density: 面積あたりのフレーク率(0–1)。size_px: フレークの大きさ。
    tilt: 傾きの強さ(0–1)。seed: 乱数種。

    返り値: (H, W, 3) の単位法線場(フレークの無い所は (0,0,1))。上塗りの下に置くと
    **粒がキラつく**。density を上げると粒の数がそのまま増える(テストで確認)。
    """
    op = "metallic_flake_normals"
    h, w = _shape2(shape, op)
    d = _unit_scalar(density, "density", op)
    sz = float(size_px)
    if not np.isfinite(sz) or sz <= 0.0:
        raise ValueError(f"{op}: size_px must be positive: got {size_px!r}")
    t = _unit_scalar(tilt, "tilt", op)
    rng = np.random.default_rng(int(seed))
    gh, gw = max(int(h / sz), 1), max(int(w / sz), 1)
    hit = rng.random((gh, gw)) < d
    ang = rng.uniform(0.0, 2.0 * np.pi, (gh, gw))
    mag = rng.uniform(0.0, t, (gh, gw)) * hit
    nx = mag * np.cos(ang)
    ny = mag * np.sin(ang)
    yi = np.clip((np.arange(h) * gh / h).astype(int), 0, gh - 1)
    xi = np.clip((np.arange(w) * gw / w).astype(int), 0, gw - 1)
    n = np.stack([nx[np.ix_(yi, xi)], ny[np.ix_(yi, xi)], np.ones((h, w))], -1)
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)


# --------------------------------------------------------------------------- #
# 3. 布                                                                        #
# --------------------------------------------------------------------------- #
def sheen_shade(normals, light=(0.3, 0.4, 0.87), view=(0.0, 0.0, 1.0),
                sheen=1.0, exponent=4.0) -> np.ndarray:
    """布の**縁の光沢**(ベルベット・サテン)。視線に対して寝た所ほど明るい。

    normals / light / view: 上記と同じ。sheen: 強さ。exponent: 縁への集中度。

    返り値: (H, W)。**鏡面反射とは逆**に、正面(n·v = 1)で 0 に近く、縁(n·v → 0)で
    最大になる ―― ベルベットの縁が白く光るのはこれで、Phong では絶対に出せない。
    """
    op = "sheen_shade"
    N, mask = matappear._normal_map(normals, op)
    L = _dir(light, "light", op)
    V = _dir(view, "view", op)
    s = float(sheen)
    e = float(exponent)
    if not np.isfinite(s) or s < 0.0:
        raise ValueError(f"{op}: sheen must be >= 0: got {sheen!r}")
    if not np.isfinite(e) or e <= 0.0:
        raise ValueError(f"{op}: exponent must be positive: got {exponent!r}")
    ndl = np.clip(np.sum(N * L[None, None, :], axis=-1), 0.0, 1.0)
    ndv = np.clip(np.sum(N * V[None, None, :], axis=-1), 0.0, 1.0)
    rim = np.power(np.clip(1.0 - ndv, 0.0, 1.0), e)
    return np.where(mask, s * rim * ndl, 0.0)


def weave_normals(shape, warp_px=8.0, weft_px=8.0, depth=0.25, angle_deg=0.0) -> np.ndarray:
    """織り目の法線場(布・カーボンファイバー・金網)。直交する 2 周期の畝。

    shape: (H, W)。warp_px / weft_px: 経糸 / 緯糸の間隔 [px]。depth: 畝の深さ。
    angle_deg: 織りの向き [deg]。

    返り値: (H, W, 3) の単位法線場。**2 方向に周期がある**のが要点(FFT に 2 本の
    ピークが立つ、テストで確認)。カーボンは warp/weft を変えて綾織りにする。
    """
    op = "weave_normals"
    h, w = _shape2(shape, op)
    for nm, v in (("warp_px", warp_px), ("weft_px", weft_px)):
        if not np.isfinite(float(v)) or float(v) <= 0.0:
            raise ValueError(f"{op}: {nm} must be positive: got {v!r}")
    d = float(depth)
    if not np.isfinite(d) or d < 0.0:
        raise ValueError(f"{op}: depth must be >= 0: got {depth!r}")
    a = np.radians(float(angle_deg))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    u = xx * np.cos(a) + yy * np.sin(a)
    v = -xx * np.sin(a) + yy * np.cos(a)
    du = -d * np.sin(2.0 * np.pi * u / float(warp_px))
    dv = -d * np.sin(2.0 * np.pi * v / float(weft_px))
    nx = du * np.cos(a) - dv * np.sin(a)
    ny = du * np.sin(a) + dv * np.cos(a)
    n = np.stack([nx, ny, np.ones((h, w))], -1)
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)


# --------------------------------------------------------------------------- #
# 4. 木                                                                        #
# --------------------------------------------------------------------------- #
def wood_grain(shape, ring_px=18.0, angle_deg=15.0, wobble=0.25, seed=0):
    """木目(年輪)の**色の変調**と**繊維の向き**を作る。

    shape: (H, W)。ring_px: 年輪の間隔 [px]。angle_deg: 木取りの向き [deg]。
    wobble: 年輪のうねり(0 で同心の直線)。seed: 乱数種。

    返り値: (modulation (H,W) 0–1, tangent (H,W,3)) —— 変調は木の色(明るい早材と
    暗い晩材)に掛け、接線は繊維方向なので `matappear.ward_anisotropic` に渡すと
    **木目に沿った光沢**になる(木は繊維方向に異方性を持つ)。
    """
    op = "wood_grain"
    h, w = _shape2(shape, op)
    rp = float(ring_px)
    if not np.isfinite(rp) or rp <= 0.0:
        raise ValueError(f"{op}: ring_px must be positive: got {ring_px!r}")
    wb = float(wobble)
    if not np.isfinite(wb) or wb < 0.0:
        raise ValueError(f"{op}: wobble must be >= 0: got {wobble!r}")
    a = np.radians(float(angle_deg))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    u = xx * np.cos(a) + yy * np.sin(a)
    v = -xx * np.sin(a) + yy * np.cos(a)
    rng = np.random.default_rng(int(seed))
    ph = wb * (np.sin(v / (3.1 * rp) + rng.uniform(0, 6.28))
               + 0.5 * np.sin(v / (1.3 * rp) + rng.uniform(0, 6.28)))
    mod = 0.5 + 0.5 * np.cos(2.0 * np.pi * (u / rp + ph))
    mod = np.clip(mod ** 1.6, 0.0, 1.0)                  # 晩材を細く濃く
    t = np.zeros((h, w, 3))
    t[..., 0] = -np.sin(a)                                # 繊維は年輪に直交する向き
    t[..., 1] = np.cos(a)
    return mod, t


# --------------------------------------------------------------------------- #
# 5. 状態(濡れ・腐食・半透明)                                                   #
# --------------------------------------------------------------------------- #
def wetness(base_rgb, wet=1.0, ior=1.33) -> np.ndarray:
    """濡れた面の下地色。**拡散が暗くなる**(そして鏡面が増える)。

    base_rgb: 乾いた状態の色 (H,W,3) または (3,)。wet: 濡れ具合(0–1)。
    ior: 水膜の屈折率。

    返り値: 濡れた状態の拡散色(同形)。

    なぜ暗くなるか: 水膜の内側で全反射が起き、拡散光が何度も表面へ戻されて
    そのたびに吸収される。近似として、乾いた反射率 ρ に対し内部反射率
    Ri = 1 − (1 − Ri0)/n² 相当の再吸収を掛ける ―― 濡れた砂が黒く見える現象そのもの
    (鏡面が増えるのは `clearcoat_shade(coat=wet)` を重ねて表す)。
    """
    op = "wetness"
    base = np.asarray(base_rgb, dtype=np.float64)
    if np.any(base < 0.0):
        raise ValueError(f"{op}: base_rgb must be >= 0")
    a = _unit_scalar(wet, "wet", op)
    n = float(ior)
    if not np.isfinite(n) or n <= 1.0:
        raise ValueError(f"{op}: ior must be > 1: got {ior!r}")
    ri = 1.0 - (1.0 - glassmirror.fresnel_dielectric(1.0, 1.0, n)) / (n * n)
    darkened = base * (1.0 - ri) / np.maximum(1.0 - ri * base, 1e-12)
    return (1.0 - a) * base + a * darkened


def corrosion_mask(shape, coverage=0.3, scale_px=24.0, seed=0) -> np.ndarray:
    """錆・緑青・汚れの**むら**(0–1 のマスク)。

    shape: (H, W)。coverage: 覆われる面積の目安(0–1)。scale_px: 斑の大きさ [px]。

    返り値: (H, W) の 0–1 マスク。素材色の混合率として使う
    (`(1-m)*metal + m*rust`)。実測の面積率は `coverage` にほぼ一致する
    (分位点で閾値を決めているため、テストで確認)。
    """
    op = "corrosion_mask"
    h, w = _shape2(shape, op)
    cov = _unit_scalar(coverage, "coverage", op)
    sc = float(scale_px)
    if not np.isfinite(sc) or sc <= 0.0:
        raise ValueError(f"{op}: scale_px must be positive: got {scale_px!r}")
    rng = np.random.default_rng(int(seed))
    field = np.zeros((h, w))
    amp = 1.0
    for octave in range(4):                               # 粗→細の重ね(fBm 代用)
        s = max(sc / (2 ** octave), 1.0)
        gh, gw = max(int(h / s), 2), max(int(w / s), 2)
        g = rng.normal(0.0, 1.0, (gh, gw))
        yi = np.clip((np.arange(h) * gh / h).astype(int), 0, gh - 1)
        xi = np.clip((np.arange(w) * gw / w).astype(int), 0, gw - 1)
        field += amp * g[np.ix_(yi, xi)]
        amp *= 0.5
    if cov <= 0.0:
        return np.zeros((h, w))
    thr = np.quantile(field, 1.0 - cov)                   # 面積率を分位点で保証
    soft = np.clip((field - thr) / max(field.std(), 1e-12) * 2.0 + 0.5, 0.0, 1.0)
    return soft


def subsurface_approx(normals, light=(0.3, 0.4, 0.87), view=(0.0, 0.0, 1.0),
                      thickness=0.5, wrap=0.5) -> np.ndarray:
    """半透明の回り込み(葉・肌・大理石・プラ乳白)の近似。

    thickness: 透け具合(0–1、大きいほど裏から回り込む)。wrap: 影側への回り込みの広さ。

    返り値: (H, W)。**光源が裏にあるほど明るい**成分(back-scatter)と、影側へ
    回り込む成分(wrap lighting)の和。Lambert では 0 になる領域に光が残るのが要点。
    """
    op = "subsurface_approx"
    N, mask = matappear._normal_map(normals, op)
    L = _dir(light, "light", op)
    V = _dir(view, "view", op)
    t = _unit_scalar(thickness, "thickness", op)
    wp = _unit_scalar(wrap, "wrap", op)
    ndl = np.sum(N * L[None, None, :], axis=-1)
    wrap_term = np.clip((ndl + wp) / (1.0 + wp), 0.0, 1.0)
    back = np.clip(np.sum(-L[None, None, :] * V[None, None, :], axis=-1), 0.0, 1.0)
    back = np.broadcast_to(back, ndl.shape) if np.ndim(back) == 0 else back
    trans = t * np.clip(-ndl, 0.0, 1.0)
    return np.where(mask, wrap_term + trans * (0.4 + 0.6 * back), 0.0)


# --------------------------------------------------------------------------- #
# 6. すりガラス                                                                 #
# --------------------------------------------------------------------------- #
def rough_transmission(cos_i, roughness=0.3, n1=1.0, n2=1.5):
    """すりガラスの透過を「直進成分」と「拡散成分」に分ける。

    cos_i: 入射角の cos。roughness: 面の粗さ(0 = 透明、1 = 完全拡散)。

    返り値: (直進 T_spec, 拡散 T_diff) の 2 本。合計は透明板の透過率に一致する
    (エネルギーを作らない ―― テストで確認)。曇りガラス越しの見え方は、この
    直進成分が落ちて拡散成分が増えるだけで説明できる。
    """
    op = "rough_transmission"
    r = _unit_scalar(roughness, "roughness", op)
    T = glassmirror.slab_transmittance(cos_i, n1, n2, 0.0, 0.0)
    keep = np.exp(-(r * 3.0) ** 2)                        # 粗いほど直進が残らない
    return T * keep, T * (1.0 - keep)

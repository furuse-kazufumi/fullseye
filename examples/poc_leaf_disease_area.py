# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""葉の病斑面積率を測る —— 色の軸は照明に勝つが、等級は葉マスクと縁の定義で決まる。

作物の葉を撮って病斑(褐色の壊死斑)の**面積率**(病斑画素 / 葉画素)を出し、
重症度の等級に畳む、という仕事です。現場では等級 0 / 1〜5 / 6〜25 / 26〜50 /
51〜100 % で判定するので、**等級の境目の近くで何枚が誤等級になるか**を知らずには
使えません。土の背景は病斑と同じ褐色で、片側からの照明むら・白飛びの鏡面反射・
影が重なります。

EXTEND: 実写に差し替えるなら :func:`make_scene` が返す辞書の ``img``(撮影画像、
sRGB 8 bit)と ``leaf`` / ``lesion``(真値マスク)を、撮影画像と目視ラベルに
置き換えます。真値の「面積の定義」(病斑の縁のどこを境界とするか)は**明示して**
記録すること —— 5 節で、縁のぼけ幅 4 px の病斑では定義だけで面積率が ±3.5 pt
動くことを示しています。ラベル付けの人が縁を「内側」に取るか「外側」に取るかで、
同じ画像・同じ手法の誤差の符号が変わります。重症(26 % 以上)の葉は**黒布の上で**
撮ること(7 節: 土の上では葉マスクが緑で作れない)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(緑チャネルの固定しきい値)は土に負ける**。土は病斑と同じ褐色なので
   緑の明るさでは分けられない。土だけで面積率の誤差 +65.2 pt、葉マスクの面積誤差
   +295.8 %。黒布の対照では +2.5 pt —— 壊れていたのは病斑の分離ではなく
   **葉の切り出し**。影だけでも +28.8 pt(影の中の健全葉がしきい値を割る)。
2. **白色方向を射影で消した G(= 非正規化 ExG)で葉を切り、Lab の a* で病斑を
   切ると土は消える**。標準場面(土・照明むら 30 %・鏡面 4 %・影)で面積率の
   誤差 -0.8 pt、葉マスクの面積誤差 -5.9 %。**葉マスクの誤差と病斑マスクの誤差を
   別に数える**と、FN 339 px の内訳は 影 152 / 縁のぼけ帯 136 / 鏡面 51、FP 178 px
   は 鏡面 140 / 縁 21。葉マスクの取りこぼし 717 px は**全部が影の中**。
   ★**正規化した ExG 色度は暗い背景で発散する**: 黒布の上で照明むら 30 % を
   掛けただけで葉マスク +25.9 %、面積率 +13.4 pt(影だけなら葉マスク +147.7 %)。
   和で割る色度は暗い画素で雑音が桁で増える。和で割らない射影 G なら +1.2 %。
3. ★**照明むらの崖: ゼロ点は 30 % で ±5 pt を超える。色相と a* は 50 % まで
   超えない**(ExG 色度は 25 %)。ゼロ点の崖は幾何で予測できる —— 雑音もぼけも無い
   反射率に減光だけ掛けて固定しきい値で数えると、0 % からの増分は 40 / 50 % で
   実測 +8.9 / +23.3 pt、予測 +8.7 / +24.2 pt。30 % では実測 +3.1 に対し予測 +1.8
   (縁のぼけと雑音を予測に入れていないぶん、崖の手前が甘い)。
4. ★★**鏡面反射(白飛び)で a* は偽陽性しか出さない。予想は「面積が増えると偽陽性と
   偽陰性が逆転する点がある」だったが、逆転は起きなかった**。鏡面 20 % で
   FP 12.6 pt、葉マスクの中の FN 0.0 pt。白は a* ≈ 0 で、葉(-36)と病斑(+7)の
   大津のしきい値(-14.7)より上に落ちる。FN 1.8 pt は葉の縁の反射が葉マスクに
   湾を作って落とすぶんで、**3 手法で同じ値**(手法ではなく葉マスクの誤差)。
   ★**色相は白を足しても動かない**(HSV の定義: 白の加算は S と V だけを変える)
   ので FP 2.0 pt、それも白飛びして S=0 になった画素(H=0)だけ。
   振幅を振ると(面積 8 %)FP が +1 pt を超えるのは a* 1.00 / 射影 1.00 /
   色相 2.5 まで無し。予測は a* 0.60(希釈で葉の a* がしきい値を跨ぐ振幅、閉形式)
   と射影 0.70(G が飽和する振幅)—— 斑の中心が跨いでも面積はまだ小さいので、
   実測の崖は予測より 0.3〜0.4 遅い。
   ★fullseye の ``specular_free_transform``(白の方向を射影で消す)は、飽和した
   画素が二色性モデルに乗っていないので白飛びには効かず(20 % で FP 7.5 pt)、
   白飛びしない反射なら a* も色相も既に耐えている —— **射影の出番はなかった**。
   線形空間で使うと暗い葉の縁を病斑側に落とす +1.5 pt の下駄もつく。
5. ★★**病斑の縁のぼけ幅 w で「面積の定義」そのものが動く**。真値を「不透明度
   50 % の等高線」に置くと、25 % / 75 % の等高線で数えた面積率は w = 8 px で
   +7.94 / -5.95 pt、w = 4 px で +3.81 / -3.24 pt。Steiner の式(平行集合の面積
   A + P·δ + π δ²、δ = w/4)の予測は +8.36 / -6.34、+3.93 / -3.42 で 0.4 pt 以内。
   **大津はこの帯が広がるとしきい値ごと動く**(w = 8 で +4.92 pt)。校正した
   固定しきい値なら +0.45 pt —— つまり w = 4 px では手法の誤差(+0.17)より
   **定義の幅(±3.5 pt)のほうが 20 倍大きい**。
6. **小さい病斑の崖: 直径 3 px で検出率 1.00、2 px で 0.29**。予測は光学ぼけ
   σ 0.7 px + 縁のぼけ 1.5 px から σ_eff 0.82 px、しきい値を跨ぐのに要る濃さ 46 %
   から直径 1.8 px —— 実測の崖(2〜3 px)より 0.5 px 楽観(8 bit と雑音を
   入れていない)。画素の回収率は 3 px で 0.85、8 px で 0.98 —— **検出できても
   縁の半分はしきい値の外**。★病斑が葉の 0.4 % しか無いと**大津は使えない**
   (2 クラスが無く葉脈と葉身を切って +15.3 pt)。20 px の見逃し 1 個は葉の縁に
   接した塊(湾になって葉マスクから落ちる)。
7. ★★**等級の境目の近く 40 枚(境界 ±3 pt、0.5 % は ±0.4 pt): 土の背景で
   誤等級はゼロ点 35 / a* 大津 26 / a* 校正固定 21 / 色相 校正固定 19 枚**。
   境界 50 % はどの手法も 8〜10 枚 —— 重症の葉は緑がばらばらになり、葉マスクが
   平均 14.1 pt ぶんの病斑ごと葉を落とす。**同じ病斑配置を黒布の上で撮り、明るさ
   で葉を切る**対照群では色相 校正固定が 8 枚(平均誤差 -0.24 pt、葉マスクの
   取りこぼし 0.04 pt)。a* 校正固定は布でも 24 枚で**全部が上の等級へ**(鏡面の
   FP +6.0 pt)。★**誤等級の向きは手法で決まっている**: ゼロ点は 35 枚全部が上、
   a* は上、色相は上下半々。境界 0.5 %(無病 vs 微病)は鏡面 4 % の FP だけで
   跨ぐので、等級 0 を出したいなら反射を撮らないことが先。

【グラウンドトゥルース】
葉は**閉形式の輪郭**(軸に沿った t ∈ [0,1] で半幅 h(t) = (W/2)·sin(πt)^0.65)
と主脈・側脈。病斑は既知の中心・半径(円と、フーリエ級数で歪めた不整形)で、
**符号つき距離で不透明度**を決め(縁のぼけ幅 w の線形ランプ)、不透明度 ≥ 0.5 を
真値マスクとする。真値の面積率は「病斑 ∧ 葉」画素数 / 葉画素数。狙った面積率に
なるよう半径の倍率を二分法で合わせる(マスクは閉形式なので安い)。
照明むらは列方向の線形減光、影は青みのある(天空光)乗算、鏡面反射は白色光源
方向の加算(二色性反射モデルの界面項)で、光学ぼけ σ 0.7 px → 雑音 → sRGB →
8 bit 量子化の順に撮像する。

来歴(公開文献のみ): Otsu (1979) 判別分析法 / Woebbecke et al. (1995) ExG 指数 /
Shafer (1985) 二色性反射モデル / Mallick et al. (2005) 鏡面不変部分空間 /
Steiner (1840) 平行集合の面積 / Bock et al. (2010) 植物病害重症度の画像評価 /
CIE 1976 L*a*b*。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N = 224                    # 画像 [px]
LEAF_LEN = 170.0           # 葉の長さ [px]
LEAF_W = 92.0              # 葉の最大幅 [px]
LEAF_ANG = 0.42            # 葉の軸の向き [rad]
SEED = 7

# 反射率(線形 RGB)。葉緑素の吸収で葉は緑が高く赤青が低い。病斑と土はどちらも褐色。
RHO_LEAF = np.array([0.09, 0.30, 0.05])
RHO_VEIN = np.array([0.22, 0.42, 0.12])
RHO_LESION = np.array([0.28, 0.13, 0.04])
RHO_SOIL = np.array([0.16, 0.11, 0.06])
RHO_CLOTH = np.array([0.03, 0.03, 0.03])       # 対照群の「背景なし」= 黒布
SHADOW_GAIN = np.array([0.38, 0.41, 0.50])     # 影は天空光で青い
PSF_SIGMA = 0.7            # 光学ぼけ [px]
NOISE = 0.008              # 雑音 σ(線形)
LESION_R = (3.0, 10.0)     # 標準場面の病斑半径の範囲 [px]

# 標準場面(等級表・内訳に使う)の妨害条件
STD = dict(illum=0.30, spec=0.04, spec_amp=1.5, shadow=True, soil=True, edge=1.5)
CTRL = dict(illum=0.0, spec=0.0, spec_amp=1.5, shadow=False, soil=False, edge=1.5)

GRADE_EDGES = (0.5, 5.0, 25.0, 50.0)          # 等級 0 / 1 / 2 / 3 / 4 の境界 [%]

_L = fs.ledger


# --------------------------------------------------------------------------- #
# 幾何 —— 葉と病斑は閉形式                                                      #
# --------------------------------------------------------------------------- #
def _leaf_coords():
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    c = (N - 1) / 2.0
    u = np.array([np.cos(LEAF_ANG), np.sin(LEAF_ANG)])     # 軸(x, y)
    a = (xx - c) * u[0] + (yy - c) * u[1]                  # 軸方向
    s = -(xx - c) * u[1] + (yy - c) * u[0]                 # 幅方向
    t = a / LEAF_LEN + 0.5
    return a, s, t


def leaf_masks() -> dict:
    """葉の内側(bool)、葉脈の濃さ [0,1]、軸座標。"""
    a, s, t = _leaf_coords()
    tt = np.clip(t, 0.0, 1.0)
    half = 0.5 * LEAF_W * np.sin(np.pi * tt) ** 0.65
    inside = (t >= 0.0) & (t <= 1.0) & (np.abs(s) <= half)
    vein = np.clip(1.0 - np.abs(s) / 1.3, 0.0, 1.0)         # 主脈
    tan_phi = np.tan(np.deg2rad(52.0))
    for k in range(1, 11):
        ak = (-0.5 + 0.08 * k) * LEAF_LEN
        for sign in (1.0, -1.0):
            d = np.abs(s - sign * (a - ak) * tan_phi) * np.cos(np.deg2rad(52.0))
            seg = (a >= ak) & (a - ak <= 0.09 * LEAF_LEN)
            vein = np.maximum(vein, np.where(seg, np.clip(1.0 - d / 0.9, 0.0, 1.0), 0.0))
    vein = np.where(inside, vein, 0.0)
    return {"inside": inside, "vein": vein, "t": t, "s": s, "a": a}


def lesion_sdf(centres, radii, shapes, scale: float) -> np.ndarray:
    """全病斑の符号つき距離の最小値(負 = 内側)。不整形は r(θ) をフーリエ級数で歪める。"""
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    sdf = np.full((N, N), np.inf)
    for (cy, cx), r0, coef in zip(centres, radii, shapes):
        r = r0 * scale
        dy, dx = yy - cy, xx - cx
        rho = np.hypot(dy, dx)
        if coef is None:
            rr = r
        else:
            th = np.arctan2(dy, dx)
            rr = r * (1.0 + sum(c * np.cos(k * th + p) for k, (c, p) in enumerate(coef, 2)))
        sdf = np.minimum(sdf, rho - rr)
    return sdf


def opacity(sdf: np.ndarray, edge: float) -> np.ndarray:
    """縁のぼけ幅 ``edge`` [px] の線形ランプ。境界(sdf=0)で 0.5。"""
    if edge <= 0.0:
        return (sdf <= 0.0).astype(np.float64)
    return np.clip(0.5 - sdf / edge, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 場面 —— 真値は幾何で決まり、撮像は物理で汚す                                   #
# --------------------------------------------------------------------------- #
def _draw_lesions(rng, geo, n, r_range):
    a, s = geo["a"], geo["s"]
    ins = geo["inside"]
    ys, xs = np.nonzero(ins & (np.abs(geo["t"] - 0.5) < 0.36) & (np.abs(s) < 0.35 * LEAF_W))
    pick = rng.choice(len(ys), size=n, replace=False)
    centres = [(float(ys[i]) + rng.uniform(-0.5, 0.5), float(xs[i]) + rng.uniform(-0.5, 0.5))
               for i in pick]
    radii = rng.uniform(r_range[0], r_range[1], n)
    shapes = []
    for _ in range(n):
        if rng.random() < 0.5:
            shapes.append(None)                                    # 円
        else:
            shapes.append([(rng.uniform(0.04, 0.12), rng.uniform(0, 2 * np.pi))
                           for _k in range(4)])                    # 不整形
    return centres, radii, shapes


def make_scene(severity: float, *, seed: int = SEED, n_lesions: int = 9,
               r_range=LESION_R, lesions=None, illum=0.0, spec=0.0, spec_amp=1.5,
               shadow=False, soil=True, edge=1.5, noise=NOISE, psf=PSF_SIGMA) -> dict:
    """面積率 ``severity`` [%] を狙った葉の場面。``img`` は sRGB 8 bit 相当の float。

    ``lesions=(centres, radii, shapes)`` を渡すと**その半径のまま**置く(倍率 1、
    面積率は狙わない)。小さい病斑の掃引で使う。
    """
    rng = np.random.default_rng(seed)
    geo = leaf_masks()
    leaf = geo["inside"]
    n_leaf = int(leaf.sum())
    if lesions is None:
        # 重症ほど個数を増やす(半径だけ伸ばすと葉の縁を跨いで葉を分断する)
        n_lesions = n_lesions + int(max(severity, 0.0) / 2.5)
        centres, radii, shapes = _draw_lesions(rng, geo, n_lesions, r_range)
    else:
        centres, radii, shapes = lesions
        severity = -1.0

    # 半径の倍率を二分法で合わせる(真値は閉形式なので安い)
    def sev_of(scale):
        return 100.0 * float(((lesion_sdf(centres, radii, shapes, scale) <= 0) & leaf).sum()) / n_leaf
    if lesions is not None:
        scale = 1.0
        sdf = lesion_sdf(centres, radii, shapes, scale)
    elif severity <= 0.0:
        scale = 0.0
        sdf = np.full((N, N), np.inf)
    else:
        lo, hi = 0.02, 1.0
        while sev_of(hi) < severity and hi < 6.0:
            hi *= 1.5
        for _ in range(22):
            mid = 0.5 * (lo + hi)
            if sev_of(mid) < severity:
                lo = mid
            else:
                hi = mid
        scale = 0.5 * (lo + hi)
        sdf = lesion_sdf(centres, radii, shapes, scale)
    alpha = opacity(sdf, edge)
    lesion = (sdf <= 0.0) & leaf
    true_sev = 100.0 * lesion.sum() / n_leaf

    # 反射率
    refl = np.empty((N, N, 3))
    bg = RHO_SOIL if soil else RHO_CLOTH
    if soil:
        lowf = np.asarray(fs.apply(rng.standard_normal((N, N)), "gaussian", a=1.0))
        lowf = lowf / (lowf.std() + 1e-12)
        tex = 1.0 + 0.35 * lowf + 0.20 * rng.standard_normal((N, N))
        refl[:] = bg[None, None, :] * np.clip(tex, 0.25, 2.0)[..., None]
    else:
        refl[:] = bg[None, None, :] * (1.0 + 0.05 * rng.standard_normal((N, N)))[..., None]
    leaf_col = RHO_LEAF[None, None, :] * (1.0 + 0.06 * rng.standard_normal((N, N, 1)))
    leaf_col = leaf_col + geo["vein"][..., None] * (RHO_VEIN - RHO_LEAF)[None, None, :]
    # 病斑: 中心ほど暗い壊死
    depth = np.clip(-sdf / 6.0, 0.0, 1.0)
    les_col = RHO_LESION[None, None, :] * (1.0 - 0.25 * depth)[..., None]
    a3 = (alpha * leaf)[..., None]
    plant = leaf_col * (1.0 - a3) + les_col * a3
    refl = np.where(leaf[..., None], plant, refl)
    refl_g = refl[..., 1].copy()                             # 照明を掛ける前の緑反射率(予測用)

    # 照明: 片側からの減光 × 影 + 鏡面反射(白色光源方向の加算)
    xx = np.arange(N, dtype=np.float64)[None, :]
    gain = (1.0 - illum * xx / (N - 1)) * np.ones((N, N))
    shade = np.ones((N, N, 3))
    if shadow:
        yy, xx2 = np.mgrid[0:N, 0:N].astype(np.float64)
        line = (yy - 0.5 * N) * np.cos(0.9) + (xx2 - 0.5 * N) * np.sin(0.9)
        soft = np.clip(0.5 + (line - 18.0) / 4.0, 0.0, 1.0)
        shade = 1.0 - soft[..., None] * (1.0 - SHADOW_GAIN)[None, None, :]
    shadow_mask = shade[..., 1] < 0.75
    spec_add = np.zeros((N, N))
    spec_mask = np.zeros((N, N), bool)
    if spec > 0.0:
        yy, xx2 = np.mgrid[0:N, 0:N].astype(np.float64)
        ys, xs = np.nonzero(leaf)
        for _ in range(200):
            i = rng.integers(len(ys))
            sg = rng.uniform(2.5, 6.0)
            spec_add += np.exp(-((yy - ys[i]) ** 2 + (xx2 - xs[i]) ** 2) / (2 * sg * sg))
            spec_mask = spec_add > 0.25
            if (spec_mask & leaf).sum() >= spec * n_leaf:
                break
    lin = refl * gain[..., None] * shade + spec_amp * spec_add[..., None] * gain[..., None]
    lin = np.clip(lin, 0.0, 1.0)
    if psf > 0.0:
        a_knob = (psf - 0.3) / 2.7
        lin = np.stack([np.asarray(fs.apply(lin[..., k], "gaussian", a=a_knob))
                        for k in range(3)], -1)
    lin = np.clip(lin + noise * rng.standard_normal(lin.shape), 0.0, 1.0)
    img = np.asarray(_L.linear_to_srgb(lin))
    img = np.round(img * 255.0) / 255.0                      # 8 bit 量子化
    return {"img": img, "leaf": leaf, "lesion": lesion, "sdf": sdf, "alpha": alpha,
            "true_sev": true_sev, "n_leaf": n_leaf, "vein": geo["vein"] > 0.5,
            "spec": spec_mask, "shadow": shadow_mask, "edge": edge,
            "centres": centres, "radii": np.asarray(radii) * scale, "scale": scale,
            "refl_g": refl_g}


# --------------------------------------------------------------------------- #
# 推定器 —— ゼロ点と、色空間 + 大津                                             #
# --------------------------------------------------------------------------- #
def otsu_above(vals: np.ndarray) -> np.ndarray:
    """1 次元の値の列に大津(``sk_otsu``、アフィン不変)を掛け、上側を True。"""
    v = np.asarray(vals, np.float64).reshape(-1, 1)
    if v.size < 2 or float(v.max() - v.min()) < 1e-9:
        return np.zeros(v.size, bool)
    return np.asarray(fs.apply(v, "sk_otsu")).ravel() > 0.5


def otsu_threshold(vals: np.ndarray) -> float:
    """大津のしきい値の値そのもの(op は二値しか返さないので、境目の両側から復元する)。"""
    v = np.asarray(vals, np.float64).ravel()
    above = otsu_above(v)
    if not above.any() or above.all():
        return float("nan")
    return 0.5 * (float(v[~above].max()) + float(v[above].min()))


def green(img):
    return np.asarray(fs.apply(img, "access_channel", a=0.5))   # a=0.5 -> G


def exg(img):
    """ExG = (2g - r - b) / (r + g + b)。**公開経路に無い**ので自前(vegetation_cover と同じ)。"""
    s = img.sum(-1) + 1e-9
    return (2.0 * img[..., 1] - img[..., 0] - img[..., 2]) / s


def hue_deg(img):
    """``trans_from_rgb`` a=0 → HSV(OpenCV 8 bit、H は 0..179/255)。度に直す。"""
    hsv = np.asarray(fs.apply(img, "trans_from_rgb", a=0.0))
    return hsv[..., 0] * 255.0 * 2.0


def lab_a(img):
    return np.asarray(_L.rgb_to_lab(np.clip(img, 0.0, 1.0)))[..., 1]


def lab_a_8bit(img):
    """``trans_from_rgb`` a=0.25 → Lab(OpenCV 8 bit)。a* = ch·255 - 128。"""
    lab = np.asarray(fs.apply(img, "trans_from_rgb", a=0.25))
    return lab[..., 1] * 255.0 - 128.0


def specfree_g(img):
    """白色光源方向を射影で消した残りの G 成分(= ExG/3 と同じ向き、正規化なし)。"""
    lin = np.asarray(_L.srgb_to_linear(np.clip(img, 0.0, 1.0)))
    out = np.asarray(_L.specular_free_transform(lin, illuminant_rgb=(1.0, 1.0, 1.0)))
    return out[..., 1]


def _leaf_post(green_mask: np.ndarray) -> np.ndarray:
    """緑の画素 → 閉(reg_close)→ 穴埋め(fill_holes)→ 最大成分。病斑は穴として埋まる。"""
    g = np.asarray(fs.apply(green_mask.astype(np.float64), "reg_close", a=0.5))
    g = np.asarray(fs.apply(g, "fill_holes"))
    g = np.asarray(fs.apply(g, "select_largest"))
    return g > 0.5


def leaf_mask_chroma(img) -> np.ndarray:
    """ExG **色度**(和で正規化)+ 大津。★暗い背景で発散する(3 節の表を参照)。"""
    return _leaf_post(otsu_above(exg(img).ravel()).reshape(N, N))


def proj_green(img):
    """白色方向を射影で消した G 成分(sRGB 値のまま)= (2G - R - B)/3。ExG の**非正規化**版。

    ``specular_free_transform`` を線形化せずに掛ける —— 物理(二色性モデル)ではなく
    線形代数として使う。暗い画素で色度が発散しない(和で割らない)のが利点。
    """
    return np.asarray(_L.specular_free_transform(np.clip(img, 0.0, 1.0),
                                                 illuminant_rgb=(1.0, 1.0, 1.0)))[..., 1]


def leaf_mask_proj(img) -> np.ndarray:
    """非正規化 ExG(射影 G)+ 大津。標準の葉マスク。"""
    return _leaf_post(otsu_above(proj_green(img).ravel()).reshape(N, N))


class Estimator:
    """葉マスクと病斑マスクを別々に返す(誤差を別に数えるため)。"""

    def __init__(self, name, leaf_fn, lesion_fn):
        self.name, self.leaf_fn, self.lesion_fn = name, leaf_fn, lesion_fn

    def __call__(self, img):
        leaf = self.leaf_fn(img)
        lesion = self.lesion_fn(img, leaf) & leaf
        n = int(leaf.sum())
        sev = 100.0 * lesion.sum() / n if n else np.nan
        return {"leaf": leaf, "lesion": lesion, "sev": sev}


_ZERO_T = {}


def calibrate_zero(scene: dict) -> None:
    """ゼロ点のしきい値: 対照画像の緑チャネルで、クラス平均の中点に置く。"""
    g = green(scene["img"])
    m_bg = float(g[~scene["leaf"]].mean())
    m_les = float(g[scene["lesion"]].mean())
    m_leaf = float(g[scene["leaf"] & ~scene["lesion"]].mean())
    _ZERO_T["lo"] = 0.5 * (m_bg + m_les)
    _ZERO_T["hi"] = 0.5 * (m_les + m_leaf)
    _ZERO_T["means"] = (m_bg, m_les, m_leaf)


def _zero_leaf(img):
    return green(img) >= _ZERO_T["lo"]


def _zero_lesion(img, leaf):
    return green(img) < _ZERO_T["hi"]



def _feature_lesion(fn, invert=False):
    def f(img, leaf):
        v = fn(img)
        out = np.zeros((N, N), bool)
        sel = otsu_above(v[leaf])
        out[leaf] = ~sel if invert else sel
        return out
    return f


_CAL = {}


def calibrate_thresholds(scene: dict) -> dict:
    """固定しきい値の校正: 参照画像(面積率 12 %)の葉の中で大津が選んだ値を凍結する。"""
    leaf = leaf_mask_proj(scene["img"])
    _CAL["a"] = otsu_threshold(lab_a(scene["img"])[leaf])
    _CAL["h"] = otsu_threshold(hue_deg(scene["img"])[leaf])
    return dict(_CAL)


def _fixed_a_lesion(img, leaf):
    return leaf & (lab_a(img) > _CAL["a"])


def _fixed_h_lesion(img, leaf):
    return leaf & (hue_deg(img) < _CAL["h"])


def leaf_mask_cloth(img) -> np.ndarray:
    """背景が黒布のときの葉マスク: 明るさが**画像の縁(= 布)の中央値の 1.5 倍**を超える画素。

    背景を制御して撮る、という現場の定石そのもの。色を使わないので、重症で緑が
    ばらばらになった葉でも 1 つの塊として切れる(7 節の対照群)。
    """
    v = img.max(-1)
    border = np.concatenate([v[0], v[-1], v[:, 0], v[:, -1]])
    return _leaf_post(v > 1.5 * float(np.median(border)))


EST = {
    "ゼロ点(緑 固定)": Estimator("ゼロ点(緑 固定)", _zero_leaf, _zero_lesion),
    "ExG色度 大津": Estimator("ExG色度 大津", leaf_mask_chroma, _feature_lesion(exg, invert=True)),
    "色相 大津": Estimator("色相 大津", leaf_mask_proj, _feature_lesion(hue_deg, invert=True)),
    "a* 大津": Estimator("a* 大津", leaf_mask_proj, _feature_lesion(lab_a)),
    "a*(8bit) 大津": Estimator("a*(8bit) 大津", leaf_mask_proj, _feature_lesion(lab_a_8bit)),
    "鏡面除去 大津": Estimator("鏡面除去 大津", leaf_mask_proj,
                          _feature_lesion(specfree_g, invert=True)),
    "a* 校正固定": Estimator("a* 校正固定", leaf_mask_proj, _fixed_a_lesion),
    "色相 校正固定": Estimator("色相 校正固定", leaf_mask_proj, _fixed_h_lesion),
    "a* 校正固定(布)": Estimator("a* 校正固定(布)", leaf_mask_cloth, _fixed_a_lesion),
    "色相 校正固定(布)": Estimator("色相 校正固定(布)", leaf_mask_cloth, _fixed_h_lesion),
}
MAIN = "a* 大津"


# --------------------------------------------------------------------------- #
# 評価 —— 葉マスクと病斑マスクの誤差を別に、壊れ方は種類ごとに                    #
# --------------------------------------------------------------------------- #
def evaluate(scene: dict, est: dict) -> dict:
    tl, tm = scene["leaf"], scene["lesion"]
    el, em = est["leaf"], est["lesion"]
    leaf_area_err = 100.0 * (el.sum() - tl.sum()) / tl.sum()
    leaf_iou = (el & tl).sum() / max((el | tl).sum(), 1)
    fp = em & ~tm
    fn = tm & ~em
    n = tl.sum()
    return {"sev": est["sev"], "dsev": est["sev"] - scene["true_sev"],
            "leaf_area_err": leaf_area_err, "leaf_iou": leaf_iou,
            "fp_pt": 100.0 * fp.sum() / n, "fn_pt": 100.0 * fn.sum() / n,
            "fn_in_pt": 100.0 * (fn & el).sum() / n,        # 葉マスクの中で見逃した
            "fn_loss_pt": 100.0 * (fn & ~el).sum() / n,     # 葉マスクごと失った
            "fp": fp, "fn": fn}


def error_kinds(scene: dict, ev: dict) -> dict:
    """FP / FN の画素を原因の種類ごとに数える(優先順に 1 つの種類へ)。"""
    edge_band = np.abs(scene["sdf"]) <= 0.5 * scene["edge"] + 0.5
    kinds = [("縁のぼけ帯", edge_band), ("鏡面反射", scene["spec"]),
             ("影", scene["shadow"]), ("葉脈", scene["vein"]),
             ("葉マスク外", ~scene["leaf"])]
    out = {}
    for label, m in (("FP", ev["fp"]), ("FN", ev["fn"])):
        rest = m.copy()
        row = {}
        for name, k in kinds:
            hit = rest & k
            row[name] = int(hit.sum())
            rest &= ~k
        row["その他"] = int(rest.sum())
        row["合計"] = int(m.sum())
        out[label] = row
    return out


def grade(sev: float) -> int:
    return int(np.searchsorted(np.asarray(GRADE_EDGES), sev, side="right"))


# --------------------------------------------------------------------------- #
# 1-2. ゼロ点と色の手法 —— 標準場面と対照群                                     #
# --------------------------------------------------------------------------- #
def section_baseline() -> dict:
    print("\n" + "=" * 78)
    print("1-2) ゼロ点(緑 固定しきい値)と 色空間 + 大津 —— 葉と病斑の誤差を別に数える")
    print("=" * 78)
    ctrl = make_scene(12.0, **CTRL)
    calibrate_zero(ctrl)
    cal = calibrate_thresholds(ctrl)
    tau = cal["a"]
    a_ctrl = lab_a(ctrl["img"])
    h_ctrl = hue_deg(ctrl["img"])
    print("  a* の分布(対照): 健全葉 %.1f / 病斑 %.1f / 背景 %.1f → 葉の中の大津しきい値 %.1f"
          % (a_ctrl[ctrl["leaf"] & ~ctrl["lesion"]].mean(), a_ctrl[ctrl["lesion"]].mean(),
             a_ctrl[~ctrl["leaf"]].mean(), tau))
    print("  色相の分布(対照): 健全葉 %.0f° / 病斑 %.0f° → 葉の中の大津しきい値 %.0f°"
          % (h_ctrl[ctrl["leaf"] & ~ctrl["lesion"]].mean(), h_ctrl[ctrl["lesion"]].mean(), cal["h"]))
    print("  ゼロ点のしきい値(対照画像で校正): 背景/病斑/葉 の緑 = %.3f / %.3f / %.3f "
          "→ T_lo %.3f, T_hi %.3f" % (*_ZERO_T["means"], _ZERO_T["lo"], _ZERO_T["hi"]))
    conds = [("対照(黒布・均一・反射なし・影なし)", CTRL),
             ("土だけ", dict(CTRL, soil=True)),
             ("照明むら 30 % だけ", dict(CTRL, illum=0.30)),
             ("鏡面 4 % だけ", dict(CTRL, spec=0.04)),
             ("影だけ", dict(CTRL, shadow=True)),
             ("標準(全部)", STD)]
    names = ["ゼロ点(緑 固定)", "ExG色度 大津", "色相 大津", "a* 大津", "a*(8bit) 大津"]
    res = {}
    leaf_lost = {}
    scenes = {}
    print("  真値の面積率 %.2f %%(葉 %d px)" % (ctrl["true_sev"], ctrl["n_leaf"]))
    print("  %-30s" % "条件" + "".join("%18s" % n for n in names))
    print("  %-30s" % "" + "".join("%18s" % "Δ率[pt] 葉[%]" for _ in names))
    for cname, kw in conds:
        sc = make_scene(12.0, **kw)
        scenes[cname] = sc
        row = {}
        for n in names:
            ev = evaluate(sc, EST[n](sc["img"]))
            row[n] = ev
        res[cname] = row
        print("  %-30s" % cname + "".join("%+9.1f %+8.1f" % (row[n]["dsev"], row[n]["leaf_area_err"])
                                         for n in names))

    std = scenes["標準(全部)"]
    ev = evaluate(std, EST[MAIN](std["img"]))
    kinds = error_kinds(std, ev)
    print("\n  標準場面での %s の壊れ方の内訳 [px](葉 %d px、真値 %.2f %%):"
          % (MAIN, std["n_leaf"], std["true_sev"]))
    keys = list(kinds["FP"].keys())
    print("  %-6s" % "" + "".join("%10s" % k for k in keys))
    for lab in ("FP", "FN"):
        print("  %-6s" % lab + "".join("%10d" % kinds[lab][k] for k in keys))
    est_main = EST[MAIN](std["img"])
    lost = std["leaf"] & ~est_main["leaf"]
    print("  葉マスクの取りこぼし %d px: 影だけ %d / 鏡面だけ %d / 両方 %d / どちらでもない %d px"
          % (lost.sum(), (lost & std["shadow"] & ~std["spec"]).sum(),
             (lost & std["spec"] & ~std["shadow"]).sum(), (lost & std["spec"] & std["shadow"]).sum(),
             (lost & ~std["spec"] & ~std["shadow"]).sum()))
    zero_ev = res["標準(全部)"]["ゼロ点(緑 固定)"]
    zero_k = error_kinds(std, zero_ev)
    print("  (ゼロ点は FP %d px のうち葉マスク外 %d px)"
          % (zero_k["FP"]["合計"], zero_k["FP"]["葉マスク外"]))

    # 図: 場面
    a_map = lab_a(std["img"])
    truth_rgb = np.stack([std["lesion"], std["leaf"] & ~std["lesion"], np.zeros((N, N))], -1).astype(float)
    det = _L.blob_label(EST[MAIN](std["img"])["lesion"])
    figs.save_grid("scene", [std["img"], truth_rgb, (a_map - a_map.min()) / (np.ptp(a_map) + 1e-9),
                             _L.blob_overlay(std["img"][..., 1], det)],
                   ["撮影画像(土・照明むら 30 %・鏡面・影)", "真値(赤 = 病斑、緑 = 健全葉)",
                    "Lab a*(緑 → 褐色)", "%s の病斑(%d 塊)" % (MAIN, int(det.max()))],
                   ncols=2, title="葉の病斑面積率(真値 %.1f %%、%d x %d px)" % (std["true_sev"], N, N),
                   caption="病斑と土は同じ褐色。葉を色度で切り、葉の中を a* で切る。")
    kind_map = np.zeros((N, N, 3))
    kind_map[..., 1] = std["img"][..., 1] * 0.6
    kind_map[ev["fp"]] = (1.0, 0.2, 0.2)
    kind_map[ev["fn"]] = (0.2, 0.4, 1.0)
    figs.save_grid("error_map", [kind_map, std["spec"].astype(float) + 0.5 * std["shadow"]],
                   ["FP(赤)/ FN(青)の画素", "鏡面反射(白)と影(灰)の場所"],
                   title="%s の誤り画素の地図(標準場面)" % MAIN,
                   caption="FN(青)の大きな塊は影と鏡面反射が重なった病斑(葉マスクごと落ちる)。"
                           "FP(赤)は鏡面反射の下と病斑の縁。")
    figs.save_grid("frames_conditions",
                   [scenes[c]["img"] for c, _ in conds[:4]] + [scenes[conds[4][0]]["img"], std["img"]],
                   [c for c, _ in conds], ncols=3, title="対照群と妨害要因(1 つずつ)")
    return {"res": res, "scenes": scenes, "kinds": kinds, "zero_kinds": zero_k, "tau": tau,
            "leaf_lost": int(lost.sum()),
            "leaf_lost_shadow": int((lost & std["shadow"]).sum())}


# --------------------------------------------------------------------------- #
# 3. 照明むらの崖 —— 幾何で予測してから測る                                      #
# --------------------------------------------------------------------------- #
def predict_zero_illum(scene_ctrl: dict, s: float) -> float:
    """ゼロ点の幾何予測: 雑音もぼけも無い反射率に減光だけ掛け、固定しきい値で数える。"""
    to_lin = lambda v: float(np.asarray(_L.srgb_to_linear(np.array([[v]])))[0, 0])   # noqa: E731
    t_lo, t_hi = to_lin(_ZERO_T["lo"]), to_lin(_ZERO_T["hi"])
    xx = np.arange(N, dtype=np.float64)[None, :] * np.ones((N, 1))
    g = scene_ctrl["refl_g"] * (1.0 - s * xx / (N - 1))
    leaf_est = g >= t_lo
    les_est = leaf_est & (g < t_hi)
    return 100.0 * les_est.sum() / max(leaf_est.sum(), 1) - scene_ctrl["true_sev"]


def section_illum(base: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) 崖: 照明むら 0 → 50 % —— どこで ±5 pt を外れるか")
    print("=" * 78)
    names = ["ゼロ点(緑 固定)", "ExG色度 大津", "色相 大津", "a* 大津"]
    ss = np.arange(0.0, 0.501, 0.05)
    ctrl = base["scenes"]["対照(黒布・均一・反射なし・影なし)"]
    rows = {n: [] for n in names}
    pred = []
    print("  %-8s" % "むら[%]" + "".join("%16s" % n for n in names) + "%14s" % "幾何予測(ゼロ点)")
    for s in ss:
        sc = make_scene(12.0, **dict(CTRL, illum=float(s)))
        p = predict_zero_illum(ctrl, float(s))
        pred.append(p)
        for n in names:
            rows[n].append(evaluate(sc, EST[n](sc["img"]))["dsev"])
        print("  %-8.0f" % (100 * s) + "".join("%+16.2f" % rows[n][-1] for n in names) + "%+12.2f" % p)
    z = "ゼロ点(緑 固定)"
    print("  ゼロ点の 0 %% からの増分: 実測 %+.1f / %+.1f / %+.1f pt(30/40/50 %%)、幾何予測 %+.1f / %+.1f / %+.1f pt"
          % (rows[z][6] - rows[z][0], rows[z][8] - rows[z][0], rows[z][10] - rows[z][0],
             pred[6] - pred[0], pred[8] - pred[0], pred[10] - pred[0]))
    cliff = {}
    for n in names:
        bad = [100 * s for s, d in zip(ss, rows[n]) if abs(d) > 5.0]
        cliff[n] = bad[0] if bad else None
        print("  %s: ±5 pt を初めて超えるむら = %s" % (n, "%.0f %%" % cliff[n] if bad else "50 % まで無し"))
    figs.save_plot("cliff_illumination",
                   [(n, 100 * ss, np.asarray(rows[n])) for n in names]
                   + [("ゼロ点の幾何予測", 100 * ss, np.asarray(pred))],
                   xlabel="照明むら(暗い側の減光)[%]", ylabel="面積率の誤差 [pt]",
                   title="照明むらの崖(対照 + むらだけ)",
                   caption="ゼロ点は固定しきい値を葉が割る列から予測できる。色の手法は 50 % まで平ら。")
    return {"ss": ss, "rows": rows, "pred": pred, "cliff": cliff}


# --------------------------------------------------------------------------- #
# 4. 鏡面反射 —— FP と FN を別に数える。白を足しても色相は動かない                 #
# --------------------------------------------------------------------------- #
def _a_star_of_diluted(w: float) -> float:
    """健全葉に白(振幅 w、線形)を足した画素の a*(閉形式: 反射率 + w → sRGB → Lab)。"""
    lin = np.clip(RHO_LEAF + w, 0.0, 1.0)[None, None, :]
    srgb = np.asarray(_L.linear_to_srgb(lin))
    return float(np.asarray(_L.rgb_to_lab(srgb))[0, 0, 1])


def section_specular(tau: float) -> dict:
    print("\n" + "=" * 78)
    print("4) 崖: 鏡面反射 —— 面積(白飛びあり)と振幅(面積 8 %)を振り、FP / FN を別に数える")
    print("=" * 78)
    names = ["a* 大津", "色相 大津", "鏡面除去 大津"]
    fr = np.array([0.0, 0.02, 0.04, 0.08, 0.12, 0.16, 0.20])
    print("  -- 面積の掃引(振幅 1.5 = 白飛び) --")
    print("  %-8s" % "鏡面[%]" + "".join("%26s" % n for n in names))
    print("  %-8s" % "" + "".join("%26s" % "Δ率 / FP / FN内 / FN葉" for _ in names))
    area = {n: {"d": [], "fp": [], "fn_in": [], "fn_loss": []} for n in names}
    for f in fr:
        sc = make_scene(12.0, **dict(CTRL, spec=float(f), spec_amp=1.5))
        line = "  %-8.0f" % (100 * f)
        for n in names:
            ev = evaluate(sc, EST[n](sc["img"]))
            for k, v in (("d", ev["dsev"]), ("fp", ev["fp_pt"]), ("fn_in", ev["fn_in_pt"]),
                         ("fn_loss", ev["fn_loss_pt"])):
                area[n][k].append(v)
            line += "   %+6.2f %5.2f %5.2f %5.2f" % (ev["dsev"], ev["fp_pt"], ev["fn_in_pt"], ev["fn_loss_pt"])
        print(line)
    figs.save_plot("cliff_specular_area",
                   [("%s FP" % n, 100 * fr, np.asarray(area[n]["fp"])) for n in names]
                   + [("FN(葉マスクごと失う、3 法共通)", 100 * fr, np.asarray(area[MAIN]["fn_loss"]))],
                   xlabel="鏡面反射が覆う葉の面積 [%]", ylabel="誤り画素 / 葉画素 [pt]",
                   title="鏡面反射の面積(白飛びあり、振幅 1.5)",
                   caption="FP は手法で桁が違う。FN は葉の縁の反射が葉マスクを欠くぶんで、手法によらない。")

    # 振幅の掃引 —— 予測: 射影は G が飽和する振幅 1 - ρ_G から、a* は希釈で τ を跨ぐ振幅から
    amps = np.array([0.1, 0.2, 0.35, 0.5, 0.7, 1.0, 1.5, 2.5])
    w_clip = 1.0 - RHO_LEAF[1]
    ws = np.linspace(0.0, 1.0, 2001)
    a_curve = np.array([_a_star_of_diluted(w) for w in ws])
    cross = ws[np.argmax(a_curve > tau)] if (a_curve > tau).any() else np.nan
    print("\n  -- 振幅の掃引(面積 8 %) --")
    print("  予測: 射影(鏡面除去)は G が飽和する振幅 %.2f から / a* は白の希釈で葉の a* が"
          "しきい値 %.1f を跨ぐ振幅 %.2f から(斑の中心での値、閉形式)" % (w_clip, tau, cross))
    print("  %-8s" % "振幅" + "".join("%14s" % n for n in names) + "%14s" % "葉+白の a*")
    amp = {n: [] for n in names}
    for A in amps:
        sc = make_scene(12.0, **dict(CTRL, spec=0.08, spec_amp=float(A)))
        line = "  %-8.2f" % A
        for n in names:
            ev = evaluate(sc, EST[n](sc["img"]))
            amp[n].append(ev["fp_pt"])
            line += "%14.2f" % ev["fp_pt"]
        print(line + "%14.1f" % _a_star_of_diluted(min(A, 1.0)))
    figs.save_plot("cliff_specular_amplitude",
                   [("%s FP" % n, amps, np.asarray(amp[n])) for n in names],
                   xlabel="鏡面反射の振幅(線形、1 = 白飛びの始まり付近)", ylabel="FP 画素 / 葉画素 [pt]",
                   title="鏡面反射の振幅(面積 8 %)",
                   caption="色相は白を足しても動かない(定義)。a* は希釈で境界を跨ぐ。射影は飽和で壊れる。")
    onset = {}
    for n in names:
        base_fp = amp[n][0]
        bad = [A for A, v in zip(amps, amp[n]) if v > base_fp + 1.0]
        onset[n] = bad[0] if bad else None
        print("  %s: FP が +1 pt を超える振幅 = %s" % (n, "%.2f" % onset[n] if bad else "2.5 まで無し"))
    return {"fr": fr, "area": area, "amps": amps, "amp": amp, "onset": onset,
            "w_clip": w_clip, "cross": cross}


# --------------------------------------------------------------------------- #
# 5. 縁のぼけ幅 —— 「面積の定義」がどれだけ動くか(Steiner の式で予測)            #
# --------------------------------------------------------------------------- #
def section_edge() -> dict:
    print("\n" + "=" * 78)
    print("5) 崖: 病斑の縁のぼけ幅 0 → 8 px —— 面積の定義(不透明度 25/50/75 %)の幅")
    print("=" * 78)
    ws = [0.0, 1.0, 2.0, 4.0, 6.0, 8.0]
    print("  %-6s %8s %8s %8s %9s %9s %10s %10s %12s" % (
        "w[px]", "真値50%", "25%線", "75%線", "予測25%", "予測75%", MAIN, "a* 校正固定", "ExG色度 大津"))
    rows = []
    for w in ws:
        sc = make_scene(12.0, **dict(CTRL, edge=w))
        n = sc["n_leaf"]
        s25 = 100.0 * ((sc["alpha"] >= 0.25) & sc["leaf"]).sum() / n
        s75 = 100.0 * ((sc["alpha"] >= 0.75) & sc["leaf"]).sum() / n
        # Steiner: 平行集合の面積 A(δ) = A + P·δ + π δ²(閉曲線 1 本につき)。δ = w/4。
        f = _L.blob_features(_L.blob_label(sc["lesion"]))
        perim, n_blob = float(np.sum(f["perimeter"])), int(f["n"])
        delta = w / 4.0
        p25 = 100.0 * (perim * delta + n_blob * np.pi * delta ** 2) / n
        p75 = 100.0 * (-perim * delta + n_blob * np.pi * delta ** 2) / n
        d_main = evaluate(sc, EST[MAIN](sc["img"]))["dsev"]
        d_fix = evaluate(sc, EST["a* 校正固定"](sc["img"]))["dsev"]
        d_exg = evaluate(sc, EST["ExG色度 大津"](sc["img"]))["dsev"]
        rows.append((w, sc["true_sev"], s25 - sc["true_sev"], s75 - sc["true_sev"], p25, p75,
                     d_main, d_fix, d_exg))
        print("  %-6.1f %8.2f %+8.2f %+8.2f %+9.2f %+9.2f %+10.2f %+10.2f %+12.2f" % rows[-1])
    r = np.asarray(rows)
    figs.save_plot("cliff_edge_blur",
                   [("25 % 線 - 真値", r[:, 0], r[:, 2]), ("75 % 線 - 真値", r[:, 0], r[:, 3]),
                    ("Steiner 予測 25 %", r[:, 0], r[:, 4]), ("Steiner 予測 75 %", r[:, 0], r[:, 5]),
                    ("%s の誤差" % MAIN, r[:, 0], r[:, 6])],
                   xlabel="縁のぼけ幅 w [px]", ylabel="面積率の差 [pt]",
                   title="縁のぼけ幅と「面積の定義」の幅",
                   caption="真値を 50 % 線に置いても、25 % / 75 % 線は P·w/4 ± π(w/4)² だけ離れる。")
    return {"rows": r}


# --------------------------------------------------------------------------- #
# 6. 小さい病斑 —— 検出率と画素の回収率(しきい値は校正固定: 大津は病斑が無いと葉脈を切る) #
# --------------------------------------------------------------------------- #
def section_size(tau: float) -> dict:
    print("\n" + "=" * 78)
    print("6) 崖: 病斑の直径 2 → 20 px —— 検出率と画素の回収率")
    print("=" * 78)
    ds = [2, 3, 4, 6, 8, 12, 16, 20]
    edge = 1.5
    sig_eff = float(np.sqrt(PSF_SIGMA ** 2 + edge ** 2 / 12.0))
    a_leaf = _a_star_of_diluted(0.0)
    lin = RHO_LESION[None, None, :]
    a_les = float(np.asarray(_L.rgb_to_lab(np.asarray(_L.linear_to_srgb(lin))))[0, 0, 1])
    need = (tau - a_leaf) / (a_les - a_leaf)          # しきい値を跨ぐのに要るコントラストの割合
    d_star = 2.0 * sig_eff * float(np.sqrt(-2.0 * np.log(1.0 - need)))
    print("  予測: σ_eff = sqrt(%.2f² + %.1f²/12) = %.2f px。葉 a* %.1f → 病斑 a* %.1f のうち"
          "しきい値 %.1f までに要る割合 %.2f → 中心がそこを割る直径 %.2f px"
          % (PSF_SIGMA, edge, sig_eff, a_leaf, a_les, tau, need, d_star))
    print("  (大津は使えない: 病斑が葉の 0.4 % しか無いと 2 クラスが無く、葉脈と葉身を切る —— "
          "直径 2 px で大津の Δ率は下の表の右端)")
    print("  %-8s %8s %10s %10s %12s %12s %12s" % ("d[px]", "個数", "検出率", "画素回収率", "Δ率[pt]", "大津Δ率[pt]", "見逃し=縁"))
    rows = []
    for d in ds:
        n_les = 14 if d <= 8 else 6
        rng = np.random.default_rng(SEED + 3)
        centres, radii, _ = _draw_lesions(rng, leaf_masks(), n_les, (d / 2.0, d / 2.0))
        sc = make_scene(0.0, lesions=(centres, radii, [None] * n_les), **dict(CTRL, edge=edge))
        est = EST["a* 校正固定"](sc["img"])
        lab_t = _L.blob_label(sc["lesion"])
        n_t = int(lab_t.max())
        inner = np.asarray(fs.apply(sc["leaf"].astype(np.float64), "reg_erode", a=0.0)) > 0.5
        hit, rec, miss_border = 0, [], 0
        for k in range(1, n_t + 1):
            m = lab_t == k
            frac = (est["lesion"] & m).sum() / m.sum()
            hit += frac >= 0.5
            rec.append(frac)
            if frac < 0.5 and (m & ~inner).any():
                miss_border += 1                     # 見逃した塊が葉の縁に接している
        rate = hit / max(n_t, 1)
        dsev = evaluate(sc, est)["dsev"]
        d_otsu = evaluate(sc, EST[MAIN](sc["img"]))["dsev"]
        rows.append((d, n_t, rate, float(np.mean(rec)), dsev, d_otsu, miss_border))
        print("  %-8d %8d %10.2f %10.2f %+12.2f %+12.2f %12d" % rows[-1])
    r = np.asarray(rows)
    figs.save_plot("cliff_lesion_size",
                   [("検出率(塊の 50 % 以上)", r[:, 0], r[:, 2]), ("画素の回収率", r[:, 0], r[:, 3])],
                   xlabel="病斑の直径 [px]", ylabel="比 [-]", title="小さい病斑の崖(a* 校正固定)",
                   caption="予測の崖 %.1f px。検出できても縁の半分はしきい値の外で、画素は小さく出る。" % d_star,
                   ylim=(0.0, 1.05))
    return {"rows": r, "d_star": d_star}


# --------------------------------------------------------------------------- #
# 7. 等級の境目 —— 何枚が誤等級になるか、どちら向きに                             #
# --------------------------------------------------------------------------- #
def section_grades() -> dict:
    print("\n" + "=" * 78)
    print("7) 等級の境目(0.5 / 5 / 25 / 50 %)の近くに置いた画像の誤等級")
    print("=" * 78)
    blocks = [("土の背景(標準場面)", STD,
               ["ゼロ点(緑 固定)", "a* 大津", "a* 校正固定", "色相 校正固定"]),
              ("黒布の背景(対照群: 明るさで葉を切る)", dict(STD, soil=False),
               ["a* 校正固定(布)", "色相 校正固定(布)"])]
    per_b = 10
    out = {}
    header = ["境界 [%]"]
    cols = {}
    for bl, kw, names in blocks:
        print("  -- %s --" % bl)
        rng = np.random.default_rng(SEED + 11)          # 同じ乱数列 → 同じ病斑配置で背景だけ違う
        total = {n: 0 for n in names}
        signs = {n: {"up": 0, "down": 0} for n in names}
        dsum = {n: 0.0 for n in names}
        leaf_loss = {n: 0.0 for n in names}
        n_img = 0
        for b in GRADE_EDGES:
            wrong = {n: 0 for n in names}
            for _k in range(per_b):
                span = 0.4 if b < 1.0 else 3.0
                target = max(0.0, b + rng.uniform(-span, span))
                sc = make_scene(target, seed=int(rng.integers(1 << 30)), **kw)
                tg = grade(sc["true_sev"])
                for n in names:
                    ev = evaluate(sc, EST[n](sc["img"]))
                    g = grade(ev["sev"])
                    if g != tg:
                        wrong[n] += 1
                        signs[n]["up" if g > tg else "down"] += 1
                    dsum[n] += ev["dsev"]
                    leaf_loss[n] += ev["fn_loss_pt"]
                n_img += 1
            for n in names:
                total[n] += wrong[n]
                cols.setdefault(n, {})[b] = wrong[n]
            print("  境界 %5.1f %%: " % b + "  ".join("%s %2d/%d" % (n, wrong[n], per_b) for n in names))
        print("  合計 %d 枚: " % n_img + "  ".join("%s %d 枚" % (n, total[n]) for n in names))
        for n in names:
            print("    %s: 上へ %d / 下へ %d 枚、平均Δ %+.2f pt、うち葉マスクごと失った病斑 %.2f pt"
                  % (n, signs[n]["up"], signs[n]["down"], dsum[n] / n_img, leaf_loss[n] / n_img))
        out[bl] = {"total": total, "signs": signs, "n_img": n_img,
                   "mean_d": {n: dsum[n] / n_img for n in names},
                   "leaf_loss": {n: leaf_loss[n] / n_img for n in names}}
    names_all = [n for _, _, ns in blocks for n in ns]
    header += names_all
    rows = [["%.1f" % b] + ["%d" % cols[n][b] for n in names_all] for b in GRADE_EDGES]
    rows.append(["合計"] + ["%d" % sum(cols[n].values()) for n in names_all])
    figs.save_table("grade_confusion", header, rows,
                    title="等級境界の近く(±3 pt、0.5 %% は ±0.4 pt)での誤等級の枚数(各境界 %d 枚)" % per_b,
                    caption="左 4 列は土の背景、右 2 列は同じ病斑配置を黒布の上で撮った対照群。"
                            "大津は病斑の無い葉(0.5 %)で葉脈を切る。50 % は葉マスクが緑で作れず布が要る。")
    return out


# --------------------------------------------------------------------------- #
# 8. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)
    names = set(fs.op_names()) | set(_L) | set(dir(fs))
    assert not any(n in names for n in ("exg", "excess_green", "vegetation_index", "ngrdi"))
    print("  (a) ExG(2g-r-b)や NGRDI など**可視 3 バンドの植生指数が無い**。"
          "spec_index は 2 バンドの正規化差だけ。poc_vegetation_cover に続き 2 本目の自前実装。")
    assert "trans_from_rgb" in names
    print("  (b) trans_from_rgb は 8 bit 経由(OpenCV)。a*(8bit) と a*(float, rgb_to_lab)の差は"
          "上の表のとおり小さいが、Lab の a* が 1 刻みに丸まる。色相は 2° 刻み。")
    assert not any(n in names for n in ("otsu_threshold", "threshold_value"))
    print("  (c) 大津の**しきい値そのもの**を返す口が無い(sk_otsu は二値画像だけ返す)。"
          "マスク内だけで決めたしきい値を全画素に掛け直す、という定石が組めない。")
    print("  (d) remove_small の最小面積は画像の 1 %%(%d px)から —— 直径 2 px の斑点を残して"
          "3 px 未満のごみだけ落とす、が op では書けない(台帳の blob_select なら書ける)。" % int(0.01 * N * N))
    assert not any(n in names for n in ("severity_grade", "area_fraction"))
    print("  (e) 「マスク A ∧ B の画素数 / B の画素数」という**面積率**と等級化の口は無い"
          "(1 行だが、等級境界の規約と一緒に置く価値はある)。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("葉の病斑面積率 —— 色の軸は照明に勝つが、等級は葉マスクと縁の定義で決まる")
    print("%d x %d px / 葉 %.0f x %.0f px / 光学ぼけ σ %.1f px / 雑音 σ %.3f" % (N, N, LEAF_LEN, LEAF_W, PSF_SIGMA, NOISE))
    print("=" * 78)

    base = section_baseline()
    il = section_illum(base)
    sp = section_specular(base["tau"])
    ed = section_edge()
    sz = section_size(base["tau"])
    gr = section_grades()
    section_tool_gaps()

    res = base["res"]
    z_soil = res["土だけ"]["ゼロ点(緑 固定)"]
    z_ctrl = res["対照(黒布・均一・反射なし・影なし)"]["ゼロ点(緑 固定)"]
    m_std = res["標準(全部)"][MAIN]
    e_ill = res["照明むら 30 % だけ"]["ExG色度 大津"]
    k = base["kinds"]
    zc, mc = il["cliff"]["ゼロ点(緑 固定)"], il["cliff"][MAIN]
    zrow, prow = il["rows"]["ゼロ点(緑 固定)"], il["pred"]
    ar = sp["area"]
    r8, r4 = ed["rows"][-1], ed["rows"][3]
    sz2, sz3, sz20 = sz["rows"][0], sz["rows"][1], sz["rows"][-1]
    g_soil = gr["土の背景(標準場面)"]
    g_cloth = gr["黒布の背景(対照群: 明るさで葉を切る)"]

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点は土で壊れる: 土だけで Δ率 %+.1f pt(葉マスク面積 %+.1f %%)、黒布の対照では %+.1f pt。"
          % (z_soil["dsev"], z_soil["leaf_area_err"], z_ctrl["dsev"]))
    print("  * %s は標準場面で Δ率 %+.1f pt、葉マスク面積 %+.1f %%。FN %d px の内訳: 影 %d / 縁のぼけ帯 %d / 鏡面 %d。"
          % (MAIN, m_std["dsev"], m_std["leaf_area_err"], k["FN"]["合計"], k["FN"]["影"],
             k["FN"]["縁のぼけ帯"], k["FN"]["鏡面反射"]))
    print("  * ExG 色度は黒布で発散: 照明むら 30 %% だけで Δ率 %+.1f pt、葉マスク %+.1f %%。"
          % (e_ill["dsev"], e_ill["leaf_area_err"]))
    print("  * 照明むらの崖: ゼロ点 %s、%s %s。ゼロ点の増分 40→50 %% は実測 %+.1f→%+.1f、予測 %+.1f→%+.1f pt。"
          % ("%.0f %%" % zc if zc else "無し", MAIN, "%.0f %%" % mc if mc else "50 % まで無し",
             zrow[8] - zrow[0], zrow[10] - zrow[0], prow[8] - prow[0], prow[10] - prow[0]))
    print("  * 鏡面 20 %%(白飛び): FP a* %.1f / 色相 %.1f / 射影 %.1f pt、FN(葉マスクごと)%.1f pt は 3 法共通。"
          % (ar[MAIN]["fp"][-1], ar["色相 大津"]["fp"][-1], ar["鏡面除去 大津"]["fp"][-1], ar[MAIN]["fn_loss"][-1]))
    print("  * 振幅の崖(+1 pt): a* %s / 射影 %s / 色相 %s(予測: a* %.2f、射影 %.2f)。"
          % tuple(["%.2f" % sp["onset"][n] if sp["onset"][n] else "2.5 まで無し"
                   for n in (MAIN, "鏡面除去 大津", "色相 大津")] + [sp["cross"], sp["w_clip"]]))
    print("  * 縁のぼけ w = 8 px: 25 %% 線 %+.2f / 75 %% 線 %+.2f pt(Steiner 予測 %+.2f / %+.2f)。"
          "大津 %+.2f、校正固定 %+.2f pt。" % (r8[2], r8[3], r8[4], r8[5], r8[6], r8[7]))
    print("  * 直径 2 px で検出率 %.2f、3 px で %.2f(予測の崖 %.1f px)。20 px の見逃し %d 個は葉の縁に接する塊。"
          % (sz2[2], sz3[2], sz["d_star"], int(sz20[6])))
    print("  * 等級境界の近く %d 枚: 土の背景で ゼロ点 %d / a* 大津 %d / a* 校正固定 %d / 色相 校正固定 %d 枚が誤等級。"
          "黒布なら a* %d / 色相 %d 枚。" % (g_soil["n_img"], g_soil["total"]["ゼロ点(緑 固定)"],
                                       g_soil["total"]["a* 大津"], g_soil["total"]["a* 校正固定"],
                                       g_soil["total"]["色相 校正固定"], g_cloth["total"]["a* 校正固定(布)"],
                                       g_cloth["total"]["色相 校正固定(布)"]))

    # ---- 所見を固定する(壊れたら鳴る) ---------------------------------------- #
    assert z_soil["dsev"] > 20.0 and abs(z_ctrl["dsev"]) < 5.0, (z_soil["dsev"], z_ctrl["dsev"])
    assert abs(m_std["dsev"]) < 3.0 and abs(m_std["leaf_area_err"]) < 10.0, m_std
    assert k["FN"]["影"] + k["FN"]["縁のぼけ帯"] >= 0.8 * k["FN"]["合計"], k["FN"]
    assert e_ill["leaf_area_err"] > 10.0, e_ill                        # 色度は暗い背景で発散
    assert zc is not None and mc is None, il["cliff"]
    assert abs((zrow[10] - zrow[0]) - (prow[10] - prow[0])) < 3.0, (zrow, prow)
    assert ar[MAIN]["fp"][-1] > 5.0 * ar["色相 大津"]["fp"][-1], (ar[MAIN]["fp"][-1], ar["色相 大津"]["fp"][-1])
    assert ar[MAIN]["fn_in"][-1] < 0.5 and abs(ar[MAIN]["fn_loss"][-1] - ar["色相 大津"]["fn_loss"][-1]) < 1e-9
    assert sp["onset"]["色相 大津"] is None or sp["onset"]["色相 大津"] > sp["onset"][MAIN]
    assert abs(r8[2] - r8[4]) < 1.0 and abs(r8[3] - r8[5]) < 1.0, r8
    assert abs(r8[7]) < 1.0 < r8[6], r8                                 # 大津は帯が広がると動く
    assert sz3[2] > 0.9 and sz2[2] < 0.5, (sz2, sz3)
    assert int(sz20[6]) == int(round((1.0 - sz20[2]) * sz20[1])), sz20   # 見逃し = 縁の塊
    assert g_soil["total"]["ゼロ点(緑 固定)"] > g_soil["total"]["a* 校正固定"], g_soil["total"]
    assert g_soil["signs"]["ゼロ点(緑 固定)"]["down"] == 0, g_soil["signs"]
    assert g_cloth["leaf_loss"]["色相 校正固定(布)"] < g_soil["leaf_loss"]["色相 校正固定"], (
        g_cloth["leaf_loss"], g_soil["leaf_loss"])
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

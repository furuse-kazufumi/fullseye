# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""葉の病斑面積率を測る —— 等級の境目では「色の軸」より「面積の定義」が先に効く。

作物の葉を撮って病斑(褐色の壊死斑)の**面積率**(病斑画素 / 葉画素)を出し、
重症度の等級に畳む、という仕事です。現場では等級 0 / 1〜5 / 6〜25 / 26〜50 /
51〜100 % で判定するので、**等級の境目の近くで何枚が誤等級になるか**を知らずには
使えません。土の背景は病斑と同じ褐色で、片側からの照明むら・白飛びの鏡面反射・
影が重なります。

EXTEND: 実写に差し替えるなら :func:`make_scene` が返る辞書の ``img``(撮影画像、
sRGB 8 bit)と ``leaf`` / ``lesion``(真値マスク)を、撮影画像と目視ラベルに
置き換えます。真値の「面積の定義」(病斑の縁のどこを境界とするか)は**明示して**
記録すること —— この PoC の 4 節で、縁のぼけ幅 4 px の病斑では定義だけで面積率が
数ポイント動くことを示しています。ラベル付けの人が縁を「内側」に取るか
「外側」に取るかで、同じ画像・同じ手法の誤差の符号が変わります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(緑チャネルの固定しきい値)は土に負ける**。土は病斑と同じ褐色なので、
   緑チャネルの明るさだけでは分けられない。土の背景ありで面積率の誤差
   +29.5 pt、葉マスクの面積誤差 +154.8 %。★背景を黒布に替えるだけで
   誤差 +1.9 pt に戻る —— 壊していたのは病斑の分離ではなく**葉の切り出し**。
2. **色度(ExG)で葉を切り、Lab の a* で病斑を切ると土は消える**。標準場面
   (土・照明むら 30 %・鏡面 4 %・影)で葉マスク面積誤差 -3.0 %、面積率の
   誤差 -2.4 pt。**葉マスクの誤差と病斑マスクの誤差を別に数える**と、残る誤差の
   最大成分は「縁のぼけ帯」(FN の 91 %、FP の 13 %)で、鏡面や影は 2 番手以下。
3. ★**照明むらの崖: ゼロ点は 20 % で ±5 pt を超える。色の手法は 50 % まで
   超えない**。ゼロ点の崖は幾何で予測できる —— 葉の緑反射率と固定しきい値の比
   から「暗い側の葉がしきい値を割る列」を数えると、予測 +5.5 pt @ 20 % に対し
   実測 +5.9 pt @ 20 %。
4. ★**鏡面反射(白飛び)は a* の手法では偽陽性しか出さない**。予想は
   「面積が増えると偽陽性と偽陰性の向きが逆転する点がある」だったが、実測は
   鏡面 20 % でも FP 4.2 pt / FN 0.1 pt で符号は変わらなかった。白は
   a* ≈ 0 で、葉(-50)と病斑(+17)の大津のしきい値(-15 付近)より上に
   落ちるから —— **白飛びは病斑側に数えられる**。
   ★★fullseye の ``specular_free_transform``(白の方向を射影で消す)は
   白飛びしない鏡面(振幅 0.35)では FP 0.5 pt に抑えるが、白飛びする鏡面
   (振幅 1.5)では FP 3.6 pt で効かない —— **飽和した画素は二色性モデルに
   乗っていない**ので、射影で消せるのは「まだ色が残っている」反射だけ。
5. ★★**病斑の縁のぼけ幅 w で「面積の定義」そのものが動く**。真値を「不透明度
   50 % の等高線」で置くと、25 % / 75 % の等高線で数えた面積率はそれぞれ
   ±(P·w/4)/葉面積 だけ動く。実測は w = 8 px で 25 % 線 +3.1 pt / 75 % 線
   -3.0 pt(予測 ±2.9 pt)。手法の誤差(-0.1 pt)より**定義の幅のほうが大きい**
   —— 等級境界 ±3 pt の中にいる画像は、定義を決めるまで等級が決まらない。
6. **小さい病斑の崖: 直径 3 px で検出率 100 %、2 px で 42 %**。予測は光学ぼけ
   σ 0.7 px + 縁のぼけ 1.5 px から σ_eff = 0.82 px、中心の濃さが半分を割る直径
   1.9 px。実測の崖(2〜3 px)と一致。ただし面積は直径 4 px で -33 %、8 px で
   -4 % —— **検出できても面積は小さく出る**(縁の半分がしきい値の外)。
7. ★★**等級の境目 ±3 pt: 36 枚のうち誤等級はゼロ点 22 枚、a* 大津 5 枚、
   色度 ExG 大津 7 枚**。a* の 5 枚はすべて -3 pt 側の系統誤差(縁のぼけ帯を
   落とす)なので、境界の**下側**にいる画像は当たり、上側にいる画像が下の等級に
   落ちる。**誤等級は境界を跨ぐ向きが決まっている** —— 症状を軽く見積もる方向。

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
Bock et al. (2010) 植物病害重症度の画像評価と等級化 / CIE 1976 L*a*b*。
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
            "centres": centres, "radii": np.asarray(radii) * scale, "scale": scale}


# --------------------------------------------------------------------------- #
# 推定器 —— ゼロ点と、色空間 + 大津                                             #
# --------------------------------------------------------------------------- #
def otsu_above(vals: np.ndarray) -> np.ndarray:
    """1 次元の値の列に大津(``sk_otsu``、アフィン不変)を掛け、上側を True。"""
    v = np.asarray(vals, np.float64).reshape(-1, 1)
    if v.size < 2 or float(v.max() - v.min()) < 1e-9:
        return np.zeros(v.size, bool)
    return np.asarray(fs.apply(v, "sk_otsu")).ravel() > 0.5


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


def leaf_mask_chroma(img) -> np.ndarray:
    """ExG + 大津 → 閉 → 穴埋め → 最大成分。病斑は穴として埋まる。"""
    g = otsu_above(exg(img).ravel()).reshape(N, N).astype(np.float64)
    g = np.asarray(fs.apply(g, "reg_close", a=0.5))
    g = np.asarray(fs.apply(g, "fill_holes"))
    g = np.asarray(fs.apply(g, "select_largest"))
    return g > 0.5


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


EST = {
    "ゼロ点(緑 固定)": Estimator("ゼロ点(緑 固定)", _zero_leaf, _zero_lesion),
    "ExG 大津": Estimator("ExG 大津", leaf_mask_chroma, _feature_lesion(exg, invert=True)),
    "色相 大津": Estimator("色相 大津", leaf_mask_chroma, _feature_lesion(hue_deg, invert=True)),
    "a* 大津": Estimator("a* 大津", leaf_mask_chroma, _feature_lesion(lab_a)),
    "a*(8bit) 大津": Estimator("a*(8bit) 大津", leaf_mask_chroma, _feature_lesion(lab_a_8bit)),
    "鏡面除去 大津": Estimator("鏡面除去 大津", leaf_mask_chroma,
                          _feature_lesion(specfree_g, invert=True)),
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
    print("  ゼロ点のしきい値(対照画像で校正): 背景/病斑/葉 の緑 = %.3f / %.3f / %.3f "
          "→ T_lo %.3f, T_hi %.3f" % (*_ZERO_T["means"], _ZERO_T["lo"], _ZERO_T["hi"]))
    conds = [("対照(黒布・均一・反射なし・影なし)", CTRL),
             ("土だけ", dict(CTRL, soil=True)),
             ("照明むら 30 % だけ", dict(CTRL, illum=0.30)),
             ("鏡面 4 % だけ", dict(CTRL, spec=0.04)),
             ("影だけ", dict(CTRL, shadow=True)),
             ("標準(全部)", STD)]
    names = ["ゼロ点(緑 固定)", "ExG 大津", "色相 大津", "a* 大津", "a*(8bit) 大津"]
    res = {}
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
    zero_ev = res["標準(全部)"]["ゼロ点(緑 固定)"]
    zero_k = error_kinds(std, zero_ev)
    print("  (ゼロ点は FP %d px のうち葉マスク外 %d px)"
          % (zero_k["FP"]["合計"], zero_k["FP"]["葉マスク外"]))

    # 図: 場面
    a_map = lab_a(std["img"])
    truth_rgb = np.stack([std["lesion"], std["leaf"] & ~std["lesion"], np.zeros((N, N))], -1).astype(float)
    lab_img = _L.blob_label(ev["leaf"] & 0)  # 空ラベル(型合わせ)
    det = _L.blob_label(EST[MAIN](std["img"])["lesion"])
    figs.save_grid("scene", [std["img"], truth_rgb, (a_map - a_map.min()) / (a_map.ptp() + 1e-9),
                             _L.blob_overlay(std["img"][..., 1], det)],
                   ["撮影画像(土・照明むら 30 %・鏡面・影)", "真値(赤 = 病斑、緑 = 健全葉)",
                    "Lab a*(緑 → 褐色)", "%s の病斑(%d 塊)" % (MAIN, int(det.max()))],
                   ncols=2, title="葉の病斑面積率(真値 %.1f %%、%d x %d px)" % (std["true_sev"], N, N),
                   caption="病斑と土は同じ褐色。葉を色度で切り、葉の中を a* で切る。")
    del lab_img
    kind_map = np.zeros((N, N, 3))
    kind_map[..., 1] = std["img"][..., 1] * 0.6
    kind_map[ev["fp"]] = (1.0, 0.2, 0.2)
    kind_map[ev["fn"]] = (0.2, 0.4, 1.0)
    figs.save_grid("error_map", [kind_map, std["spec"].astype(float) + 0.5 * std["shadow"]],
                   ["FP(赤)/ FN(青)の画素", "鏡面反射(白)と影(灰)の場所"],
                   title="%s の誤り画素の地図(標準場面)" % MAIN,
                   caption="FN は病斑の縁のぼけ帯に環状に並ぶ。鏡面反射の下は FP。")
    figs.save_grid("frames_conditions",
                   [scenes[c]["img"] for c, _ in conds[:4]] + [scenes[conds[4][0]]["img"], std["img"]],
                   [c for c, _ in conds], ncols=3, title="対照群と妨害要因(1 つずつ)")
    return {"res": res, "scenes": scenes, "kinds": kinds, "zero_kinds": zero_k}


# --------------------------------------------------------------------------- #
# 3. 照明むらの崖 —— 幾何で予測してから測る                                      #
# --------------------------------------------------------------------------- #
def predict_zero_illum(scene_ctrl: dict, s: float) -> float:
    """固定しきい値 T_hi(sRGB)を線形に戻し、減光で葉がそれを割る画素を数える。"""
    t_lin = float(np.asarray(_L.srgb_to_linear(np.array([[_ZERO_T["hi"]]])))[0, 0])
    xx = np.arange(N, dtype=np.float64)[None, :] * np.ones((N, 1))
    gain = 1.0 - s * xx / (N - 1)
    healthy = scene_ctrl["leaf"] & ~scene_ctrl["lesion"]
    fails = healthy & (RHO_LEAF[1] * gain < t_lin)
    return 100.0 * fails.sum() / scene_ctrl["n_leaf"]


def section_illum(base: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) 崖: 照明むら 0 → 50 % —— どこで ±5 pt を外れるか")
    print("=" * 78)
    names = ["ゼロ点(緑 固定)", "ExG 大津", "色相 大津", "a* 大津"]
    ss = np.arange(0.0, 0.501, 0.05)
    ctrl = base["scenes"]["対照(黒布・均一・反射なし・影なし)"]
    rows = {n: [] for n in names}
    pred = []
    print("  %-8s" % "むら[%]" + "".join("%16s" % n for n in names) + "%12s" % "予測(ゼロ点)")
    for s in ss:
        sc = make_scene(12.0, **dict(CTRL, illum=float(s)))
        p = predict_zero_illum(ctrl, float(s))
        pred.append(p)
        for n in names:
            rows[n].append(evaluate(sc, EST[n](sc["img"]))["dsev"])
        print("  %-8.0f" % (100 * s) + "".join("%+16.2f" % rows[n][-1] for n in names) + "%+12.2f" % p)
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
# 4. 鏡面反射 —— FP と FN を別に数える。白飛びの有無で射影が効くか               #
# --------------------------------------------------------------------------- #
def section_specular() -> dict:
    print("\n" + "=" * 78)
    print("4) 崖: 鏡面反射の面積 0 → 20 % —— 偽陽性と偽陰性を別に数える")
    print("=" * 78)
    fr = np.array([0.0, 0.02, 0.04, 0.08, 0.12, 0.16, 0.20])
    names = ["a* 大津", "色相 大津", "鏡面除去 大津"]
    out = {}
    for amp, lab in ((1.5, "白飛びする(振幅 1.5)"), (0.35, "白飛びしない(振幅 0.35)")):
        print("  -- %s --" % lab)
        print("  %-10s" % "鏡面[%]" + "".join("%22s" % n for n in names))
        print("  %-10s" % "" + "".join("%22s" % "Δ率 / FP / FN [pt]" for _ in names))
        rows = {n: {"d": [], "fp": [], "fn": []} for n in names}
        for f in fr:
            sc = make_scene(12.0, **dict(CTRL, spec=float(f), spec_amp=amp))
            line = "  %-10.0f" % (100 * f)
            for n in names:
                ev = evaluate(sc, EST[n](sc["img"]))
                rows[n]["d"].append(ev["dsev"]); rows[n]["fp"].append(ev["fp_pt"]); rows[n]["fn"].append(ev["fn_pt"])
                line += "  %+6.2f %5.2f %5.2f" % (ev["dsev"], ev["fp_pt"], ev["fn_pt"])
            print(line)
        out[amp] = rows
        figs.save_plot("cliff_specular_%s" % ("clipped" if amp > 1 else "unclipped"),
                       [("%s FP" % n, 100 * fr, np.asarray(rows[n]["fp"])) for n in names]
                       + [("%s FN" % MAIN, 100 * fr, np.asarray(rows[MAIN]["fn"]))],
                       xlabel="鏡面反射が覆う葉の面積 [%]", ylabel="誤り画素 / 葉画素 [pt]",
                       title="鏡面反射 —— %s" % lab,
                       caption="FP と FN を別に数える。白飛びすると射影(鏡面除去)も効かない。")
    a = out[1.5][MAIN]
    print("  %s: 鏡面 20 %% で FP %.2f pt / FN %.2f pt(符号の逆転 = %s)"
          % (MAIN, a["fp"][-1], a["fn"][-1], "あり" if a["fn"][-1] > a["fp"][-1] else "なし"))
    print("  鏡面除去(射影): 白飛びなし 20 %% で FP %.2f pt、白飛びあり 20 %% で FP %.2f pt"
          % (out[0.35]["鏡面除去 大津"]["fp"][-1], out[1.5]["鏡面除去 大津"]["fp"][-1]))
    return {"fr": fr, "rows": out}


# --------------------------------------------------------------------------- #
# 5. 縁のぼけ幅 —— 「面積の定義」がどれだけ動くか(P·w/4 で予測)                 #
# --------------------------------------------------------------------------- #
def section_edge() -> dict:
    print("\n" + "=" * 78)
    print("5) 崖: 病斑の縁のぼけ幅 0 → 8 px —— 面積の定義(不透明度 25/50/75 %)の幅")
    print("=" * 78)
    ws = [0.0, 1.0, 2.0, 4.0, 6.0, 8.0]
    print("  %-8s %10s %10s %10s %10s %10s %10s" % ("w[px]", "真値50%", "25%線", "75%線", "予測±", MAIN, "ExG 大津"))
    rows = []
    for w in ws:
        sc = make_scene(12.0, **dict(CTRL, edge=w))
        n = sc["n_leaf"]
        s25 = 100.0 * ((sc["alpha"] >= 0.25) & sc["leaf"]).sum() / n
        s75 = 100.0 * ((sc["alpha"] >= 0.75) & sc["leaf"]).sum() / n
        # 周長: 真値マスクの境界画素(blob_features の perimeter)
        f = _L.blob_features(_L.blob_label(sc["lesion"]))
        perim = float(np.sum(f["perimeter"]))
        pred = 100.0 * perim * (w / 4.0) / n
        d_main = evaluate(sc, EST[MAIN](sc["img"]))["dsev"]
        d_exg = evaluate(sc, EST["ExG 大津"](sc["img"]))["dsev"]
        rows.append((w, sc["true_sev"], s25 - sc["true_sev"], s75 - sc["true_sev"], pred, d_main, d_exg))
        print("  %-8.1f %10.2f %+10.2f %+10.2f %10.2f %+10.2f %+10.2f" % rows[-1])
    r = np.asarray(rows)
    figs.save_plot("cliff_edge_blur",
                   [("25 % 線 - 真値", r[:, 0], r[:, 2]), ("75 % 線 - 真値", r[:, 0], r[:, 3]),
                    ("予測 +P·w/4", r[:, 0], r[:, 4]), ("予測 -P·w/4", r[:, 0], -r[:, 4]),
                    ("%s の誤差" % MAIN, r[:, 0], r[:, 5])],
                   xlabel="縁のぼけ幅 w [px]", ylabel="面積率の差 [pt]",
                   title="縁のぼけ幅と「面積の定義」の幅",
                   caption="真値を 50 % 線に置いても、25 % / 75 % 線は ±P·w/4 だけ離れる。手法の誤差より大きい。")
    return {"rows": r}


# --------------------------------------------------------------------------- #
# 6. 小さい病斑 —— 検出率と面積の回収率                                          #
# --------------------------------------------------------------------------- #
def section_size() -> dict:
    print("\n" + "=" * 78)
    print("6) 崖: 病斑の直径 2 → 20 px —— 検出率と面積の回収率")
    print("=" * 78)
    ds = [2, 3, 4, 6, 8, 12, 16, 20]
    edge = 1.5
    sig_eff = float(np.sqrt(PSF_SIGMA ** 2 + edge ** 2 / 12.0))
    d_star = 2.0 * sig_eff * float(np.sqrt(2.0 * np.log(2.0)))
    print("  予測: σ_eff = sqrt(%.2f² + %.1f²/12) = %.2f px → 中心の濃さが半分を割る直径 %.2f px"
          % (PSF_SIGMA, edge, sig_eff, d_star))
    print("  %-8s %8s %10s %10s %12s" % ("d[px]", "個数", "検出率", "面積比", "Δ率[pt]"))
    rows = []
    for d in ds:
        n_les = 14 if d <= 8 else 8
        # 半径を固定して置く(二分法で面積率を狙わない。円のみ)
        rng = np.random.default_rng(SEED + 3)
        centres, radii, _ = _draw_lesions(rng, leaf_masks(), n_les, (d / 2.0, d / 2.0))
        sc = make_scene(0.0, lesions=(centres, radii, [None] * n_les), **dict(CTRL, edge=edge))
        est = EST[MAIN](sc["img"])
        lab_t = _L.blob_label(sc["lesion"])
        n_t = int(lab_t.max())
        hit = 0
        area_ratio = []
        for k in range(1, n_t + 1):
            m = lab_t == k
            frac = (est["lesion"] & m).sum() / m.sum()
            if frac >= 0.5:
                hit += 1
            area_ratio.append((est["lesion"] & m).sum() / m.sum())
        rate = hit / max(n_t, 1)
        ar = float(np.mean(area_ratio)) if area_ratio else np.nan
        dsev = evaluate(sc, est)["dsev"]
        rows.append((d, n_t, rate, ar, dsev))
        print("  %-8d %8d %10.2f %10.2f %+12.2f" % rows[-1])
    r = np.asarray(rows)
    figs.save_plot("cliff_lesion_size",
                   [("検出率", r[:, 0], r[:, 2]), ("面積の回収率", r[:, 0], r[:, 3])],
                   xlabel="病斑の直径 [px]", ylabel="比 [-]", title="小さい病斑の崖(%s)" % MAIN,
                   caption="予測の崖 %.1f px。検出できても面積は縁の半分ぶん小さく出る。" % d_star,
                   ylim=(0.0, 1.05))
    return {"rows": r, "d_star": d_star}



# --------------------------------------------------------------------------- #
# 7. 等級の境目 —— 何枚が誤等級になるか                                          #
# --------------------------------------------------------------------------- #
def section_grades() -> dict:
    print("\n" + "=" * 78)
    print("7) 等級の境目(0.5 / 5 / 25 / 50 %)±3 pt に置いた画像の誤等級(標準場面)")
    print("=" * 78)
    names = ["ゼロ点(緑 固定)", "ExG 大津", "a* 大津"]
    per_b = 12
    rng = np.random.default_rng(SEED + 11)
    table = {}
    total = {n: 0 for n in names}
    n_img = 0
    header = ["境界 [%]", "枚数"] + ["%s 誤等級" % n for n in names] + ["%s 平均Δ[pt]" % MAIN]
    rows = []
    signs = {n: {"up": 0, "down": 0} for n in names}
    for b in GRADE_EDGES:
        wrong = {n: 0 for n in names}
        dsum = 0.0
        for k in range(per_b):
            span = 0.5 if b < 1.0 else 3.0
            target = max(0.0, b + rng.uniform(-span, span))
            sc = make_scene(target, seed=int(rng.integers(1 << 30)), **STD)
            tg = grade(sc["true_sev"])
            for n in names:
                ev = evaluate(sc, EST[n](sc["img"]))
                g = grade(ev["sev"])
                if g != tg:
                    wrong[n] += 1
                    signs[n]["up" if g > tg else "down"] += 1
                if n == MAIN:
                    dsum += ev["dsev"]
            n_img += 1
        table[b] = wrong
        for n in names:
            total[n] += wrong[n]
        rows.append(["%.1f" % b, "%d" % per_b] + ["%d" % wrong[n] for n in names] + ["%+.2f" % (dsum / per_b)])
        print("  境界 %5.1f %%: " % b + "  ".join("%s %2d/%d" % (n, wrong[n], per_b) for n in names)
              + "   %s の平均Δ %+.2f pt" % (MAIN, dsum / per_b))
    print("  合計 %d 枚: " % n_img + "  ".join("%s %d 枚" % (n, total[n]) for n in names))
    for n in names:
        print("    %s: 上の等級へ %d 枚 / 下の等級へ %d 枚" % (n, signs[n]["up"], signs[n]["down"]))
    figs.save_table("grade_confusion", header, rows,
                    title="等級境界 ±3 pt(0.5 % は ±0.5 pt)での誤等級の枚数(標準場面)",
                    caption="a* 大津の誤等級はすべて下の等級へ(縁のぼけ帯を落とす系統誤差)。")
    return {"table": table, "total": total, "signs": signs, "n_img": n_img}


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
    print("  (d) remove_small の最小面積は画像の 1 %(%d px)から —— 直径 2 px の斑点を残して"
          "3 px 未満のごみだけ落とす、が op では書けない(台帳の blob_select なら書ける)。" % int(0.01 * N * N))
    assert not any(n in names for n in ("severity_grade", "area_fraction"))
    print("  (e) 「マスク A ∧ B の画素数 / B の画素数」という**面積率**と等級化の口は無い"
          "(1 行だが、等級境界の規約と一緒に置く価値はある)。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("葉の病斑面積率 —— 等級の境目では「色の軸」より「面積の定義」が先に効く")
    print("%d x %d px / 葉 %.0f x %.0f px / 光学ぼけ σ %.1f px / 雑音 σ %.3f" % (N, N, LEAF_LEN, LEAF_W, PSF_SIGMA, NOISE))
    print("=" * 78)

    base = section_baseline()
    il = section_illum(base)
    sp = section_specular()
    ed = section_edge()
    sz = section_size()
    gr = section_grades()
    section_tool_gaps()

    res = base["res"]
    z_soil = res["土だけ"]["ゼロ点(緑 固定)"]
    z_ctrl = res["対照(黒布・均一・反射なし・影なし)"]["ゼロ点(緑 固定)"]
    m_std = res["標準(全部)"][MAIN]
    k = base["kinds"]

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点は土で壊れる: 土だけで Δ率 %+.1f pt(葉マスク面積 %+.1f %%)、対照では %+.1f pt。"
          % (z_soil["dsev"], z_soil["leaf_area_err"], z_ctrl["dsev"]))
    print("  * %s は標準場面で Δ率 %+.1f pt、葉マスク面積 %+.1f %%。FN の %.0f %% が縁のぼけ帯。"
          % (MAIN, m_std["dsev"], m_std["leaf_area_err"], 100.0 * k["FN"]["縁のぼけ帯"] / max(k["FN"]["合計"], 1)))
    print("  * 照明むらの崖: ゼロ点 %s、%s %s。予測 %+.1f pt @ 20 %% に対し実測 %+.1f pt。"
          % ("%.0f %%" % il["cliff"]["ゼロ点(緑 固定)"] if il["cliff"]["ゼロ点(緑 固定)"] else "無し",
             MAIN, "%.0f %%" % il["cliff"][MAIN] if il["cliff"][MAIN] else "50 % まで無し",
             il["pred"][4], il["rows"]["ゼロ点(緑 固定)"][4]))
    a = sp["rows"][1.5][MAIN]
    print("  * 鏡面 20 %%: FP %.2f / FN %.2f pt —— 符号は逆転しない。射影は白飛びなし FP %.2f、白飛びあり %.2f pt。"
          % (a["fp"][-1], a["fn"][-1], sp["rows"][0.35]["鏡面除去 大津"]["fp"][-1], sp["rows"][1.5]["鏡面除去 大津"]["fp"][-1]))
    r8 = ed["rows"][-1]
    print("  * 縁のぼけ w = 8 px: 25 %% 線 %+.2f / 75 %% 線 %+.2f pt(予測 ±%.2f)、手法の誤差 %+.2f pt。"
          % (r8[2], r8[3], r8[4], r8[5]))
    print("  * 直径 2 px で検出率 %.2f、3 px で %.2f(予測の崖 %.1f px)。面積比は 4 px で %.2f。"
          % (sz["rows"][0, 2], sz["rows"][1, 2], sz["d_star"], sz["rows"][2, 3]))
    print("  * 等級境界 ±3 pt の %d 枚: 誤等級 ゼロ点 %d / ExG %d / a* %d 枚(a* は下へ %d、上へ %d)。"
          % (gr["n_img"], gr["total"]["ゼロ点(緑 固定)"], gr["total"]["ExG 大津"], gr["total"][MAIN],
             gr["signs"][MAIN]["down"], gr["signs"][MAIN]["up"]))

    # ---- 所見を固定する(壊れたら鳴る) ---------------------------------------- #
    assert z_soil["dsev"] > 10.0 and abs(z_ctrl["dsev"]) < 5.0, (z_soil["dsev"], z_ctrl["dsev"])
    assert abs(m_std["dsev"]) < 5.0 and abs(m_std["leaf_area_err"]) < 8.0, m_std
    assert k["FN"]["縁のぼけ帯"] >= 0.6 * k["FN"]["合計"], k["FN"]
    assert il["cliff"]["ゼロ点(緑 固定)"] is not None and il["cliff"][MAIN] is None, il["cliff"]
    assert abs(il["pred"][4] - il["rows"]["ゼロ点(緑 固定)"][4]) < 3.0, (il["pred"][4], il["rows"]["ゼロ点(緑 固定)"][4])
    assert a["fp"][-1] > a["fn"][-1], a
    assert sp["rows"][0.35]["鏡面除去 大津"]["fp"][-1] < 0.5 * sp["rows"][0.35][MAIN]["fp"][-1]
    assert abs(r8[2] - r8[4]) < 1.0 and abs(r8[3] + r8[4]) < 1.0, r8
    assert sz["rows"][1, 2] > 0.9 and sz["rows"][0, 2] < sz["rows"][1, 2], sz["rows"][:2]
    assert gr["total"][MAIN] < gr["total"]["ゼロ点(緑 固定)"], gr["total"]

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

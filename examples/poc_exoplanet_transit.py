# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""系外惑星トランジットを開口測光で取り出す —— 深さと継続時間は別々に壊れる。

恒星の前を惑星が横切ると、星の明るさが **1 % ほど**、数時間だけ暗くなる
(トランジット)。地上の小望遠鏡でこれを測る仕事は、画像列から目標星と
比較星を開口測光し、**比を取って**大気の透明度変動を消し、残った光度曲線に
解析モデルを当てはめて深さ δ(惑星半径)と継続時間 T14(軌道)を出す、
というものです。δ の誤差と T14 の誤差は**別の量**で、壊れ方も別なので、
この PoC は最後まで 2 つを分けて数えます。単位は ppt(千分率、10 ppt = 1 %)
と フレーム(fr)。

EXTEND: 実写に差し替えるなら :func:`make_series` が返す辞書の ``frames``
(画像列)を撮影画像に、``model``(真のトランジット光度曲線)と ``rows`` /
``cols`` / ``ratio``(星の真の位置と明るさの比)を既知の系(既知惑星の暦と
星表)に置き換えます。**フラット ``gain`` と位置ずれ ``shifts`` の真値は実写では
手に入らない**ので、5 節の「ドリフト × フラット」の分解は実写では再現できず、
代わりに 5 節の予測式(``a * sqrt(sum w^2)``)で上限を見積もることになります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(目標星の開口積分だけ)は雲で死ぬ**。透明度変動 rms 3 % の下で
   深さは +82.2 ppt(真値 10 ppt、誤差 **+72.2 ppt = 真値の 7 倍**)、
   T14 は 60.8 fr(真値 80、誤差 -19.2)。対照群(雲なし)では同じゼロ点が
   誤差 +0.16 ppt / +0.8 fr で当たる —— 壊すのは手法ではなく雲。比較星 5 個の
   和との比を取ると雲ありでも -0.13 ppt / -0.9 fr(残差 rms 1.93 ppt)。
2. ★**比較星の選び方で精度が 6.0 倍変わる**。残差 rms は最良(明るい 2 星の
   和)1.91 ppt、最悪(1/20 の明るさの 1 星)11.43 ppt。深さの σ は 0.30 →
   1.84 ppt とその比で動くが、★**T14 の誤差はそうならない**(最悪の星でも
   -0.5 fr、最良で -1.4 fr)—— 入出の傾斜は深さより雑音に強い。
   ★★**逆分散重みは生の分散で決めると罠**: 雲(全星共通)が明るい星の分散を
   支配して重みが暗い星へ行き、単純和 1.93 ppt より悪い 2.92 ppt(1.52 倍)。
   共通モードを外してから測り直すと 1.98 ppt。
3. ★★**開口半径の崖(小さい側)は、予想した重心誤差ではなかった**。予想は
   「r = 1σ では重心誤差(実測 rms 0.039 px)が明るさに化けて理論より 27 %
   悪い」。実測は +14 % —— そして**星が画素に対して不動の対照群では +69 % と
   逆に悪化**した。開口は中心対称なので位置誤差 ε は 2 次(ε² = 0.0015 px²)
   でしか効かない。効いていたのは op の**開口マスクの階段**: ``supersample=8``
   は縁の画素の重みを 1/64 刻みで量子化し、r = 1σ では縁の 1 画素が総光量の
   5.5 % を持つので 1 段の跳びが 0.86 ppt。``supersample=32`` で 動く星 2.54 /
   不動 2.67 ppt(理論比 0.89 / 0.93)に落ちる。r ≥ 2σ ではどの条件も理論比
   0.90〜1.03 で、大きい側の坂(6σ で 2.29 ppt)は背景推定の雑音 ``A² σ_B²
   (π/2)/n_annulus`` を CCD 式に足すと合う(★これも最初は忘れていて 12 % 外れた)。
4. **検出限界(SNR = 5)は暦既知なら CCD 式 + Fisher が当てる**: 実測 1.48 ppt
   / 理論 1.45 ppt(比 0.82〜0.98)。★暦未知(t0 と T14 も探す)だと崖は
   2.0 ppt(|T14 誤差| < 5 fr になる最小の δ)で Fisher 限界の 1.4 倍。
   限界の下では ★**深さより先に継続時間が壊れる**: δ = 0.5 ppt で深さの誤差は
   +0.11 ppt なのに |T14 誤差| は 26.5 fr。そして暦未知の SNR(推定深さ/σ)は
   限界の下でも 1.7〜4.2 と出る —— 雑音を惑星と呼んでいる。
5. ★★**ドリフトとフラット不均一は単独では無害、掛け算で偽の深さを作る**。
   深さ誤差 rms は ドリフト 2 px・フラット均一で 0.16 ppt、ドリフト 0・画素
   フラット 3 % で 0.08 ppt、**両方あると 0.94 ppt(真値の 9 %)、4 px なら
   2.97 ppt(30 %)**。予測式の上限 ``a * sqrt(sum w^2) = 0.185 a``(3 % で
   5.54 ppt)に対し 2 px で 17 %、4 px で 54 % —— 直線基線が大半を吸い、動く量が
   PSF の幅を超えると吸えなくなる。雑音を切って真の位置で測った**系統分だけの
   予測**は seed ごとに実測と一致する(差の rms 0.05〜0.23 ppt = 雑音の床)。
   T14 も 4 px・3 % で rms 4.3 fr 外れる。
6. ★**当てはめのバグが偽の所見を出しかけた**。最初の格子初期化は
   ``y ≈ a·m + c1·x`` と書いて深さを基線に縛っていたので δ が小さいほど真の解を
   外し、「暦未知だと崖は 10 ppt(Fisher の 6.9 倍)」という数字が出た。
   **暦未知の残差 rms が暦既知より大きい**(2.20 vs 2.00 ppt)ことが局所解の
   印だった。深さを線形係数にした格子に直すと崖は 2.0 ppt。

【グラウンドトゥルース】
星は erf による**画素の厳密積分**のガウス PSF(σ = 1.5 px)、トランジットは
Mandel & Agol の小惑星近似(2 円の重なり面積 × 惑星中心での周辺減光強度、
2 次周辺減光 u1 = 0.40, u2 = 0.25)の**閉形式**。系統誤差は 4 つを別々の
乱数で仕込む —— 透明度(全星共通の乗算)、副画素ドリフト(全星共通の平行
移動 + フレームごとのジッタ)、フラット不均一(画素ごとの感度、低次勾配 +
画素ランダム)、光子雑音(Poisson + 読み出し)。どれも**止められる**ので
対照群が作れる。測る側は fullseye の ``sigma_clip_stack``(基準像)→
``star_detect``(星表)→ ``frame_align``(各フレームの平行移動)→
``aperture_photometry``(開口測光)で、真の位置は星の名付けにしか使わない。

【道具の穴(この PoC で分かったこと)】
* ``fs.ledger.synth_starfield`` は ``(frame, truth)`` のうち **frame しか返さない**
  (``astrostack.synth_starfield`` 直呼びなら truth も出る)。真値の供給源なのに
  公開経路で真値が落ちる。ここでは星ごとに時間変化する明るさが要るので自前で描いた。
* ``aperture_photometry`` の ``supersample=8`` は小開口で**雑音源**になる(3 節)。
  docstring は「円の面積の離散化だけを直す」と書くが、星が動くと縁の重みの階段が
  そのまま光度曲線に乗る。小開口の測光は 32 を使うか、既定を上げる価値がある。
* トランジット光度曲線のモデル、光度曲線の当てはめ(基線 + 暦)、比較星の
  アンサンブル重み付けは公開経路に無い(すべて自前)。

来歴(公開文献のみ): Mandel & Agol, *ApJ* 580 (2002) L171 —— トランジット
光度曲線の解析式 / Howell, *Handbook of CCD Astronomy* (2006) —— CCD 式 /
Collins et al., *AJ* 153 (2017) 77 —— AstroImageJ の比較星アンサンブル測光。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares
from scipy.special import erf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

_AS = fs.ledger        # astrostack 族の公開経路(star_detect / frame_align / aperture_photometry)

# --- 場面の諸元 -------------------------------------------------------------- #
SHAPE = (112, 112)         # 視野 [px]
SIGMA = 1.5                # PSF σ [px](FWHM 3.53 px)
SKY = 400.0                # 背景 [e-/px/frame](明るめの空: 大開口側の坂を残す)
READ = 5.0                 # 読み出し雑音 [e- rms]
F_TARGET = 400000.0        # 目標星の明るさ [e-/frame](1 枚で 1.6 ppt の光子雑音)
T = 240                    # 枚数
SEED = 11

#: 星表。目標星が先頭、続く 5 個が比較星(明るさは目標星に対する比)。
#: 比較星の明るさは**わざと 2 倍〜1/20 に散らして**ある —— 2 節で「どれを
#: 選ぶか」の効き目を測るため。位置は互いに 36 px 以上離す(背景環が重ならない)。
STARS = {
    "目標":   {"row": 56.0, "col": 56.0, "ratio": 1.00},
    "比較A":  {"row": 24.0, "col": 26.0, "ratio": 2.00},
    "比較B":  {"row": 26.0, "col": 88.0, "ratio": 1.00},
    "比較C":  {"row": 88.0, "col": 22.0, "ratio": 0.50},
    "比較D":  {"row": 86.0, "col": 90.0, "ratio": 0.20},
    "比較E":  {"row": 20.0, "col": 58.0, "ratio": 0.05},
}
NAMES = list(STARS)

# --- トランジット(真値) ------------------------------------------------------ #
DEPTH = 0.010              # 深さ δ(最深部の減光率)
T0 = 120.0                 # 中心時刻 [frame]
T14 = 80.0                 # 第 1〜第 4 接触の継続時間 [frame]
B = 0.30                   # 衝突径数(恒星半径単位)
U1, U2 = 0.40, 0.25        # 2 次周辺減光係数
IBAR = 1.0 - U1 / 3.0 - U2 / 6.0     # 円盤平均強度(中心 1 に対する)

# --- 系統誤差(既定値。各節で止めたり振ったりする) ---------------------------- #
CLOUD_RMS = 0.03           # 透明度変動の rms(乗算、全星共通)
CLOUD_TREND = -0.02        # 一晩の大気量の傾き(終端での減光率)
DRIFT_PX = 1.0             # 一晩の位置ドリフト [px](直線)
DRIFT_DEG = 35.0           # ドリフトの向き
JITTER_PX = 0.05           # フレームごとの位置のばらつき [px rms]
FLAT_LO = 0.04             # フラットの低次勾配(視野端での振幅)
FLAT_PX = 0.01             # 画素ごとの感度ばらつき rms

# --- 開口 ---------------------------------------------------------------------- #
R_AP = 3.0 * SIGMA         # 開口半径(3σ = 98.9 % を拾う)
R_IN, R_OUT = 8.0, 12.0    # 背景環
DETECT_SIGMA = 8.0         # star_detect のしきい値 [σ]
N_REF = 10                 # 基準像に重ねる枚数


# --------------------------------------------------------------------------- #
# 真値: トランジット光度曲線(閉形式)                                          #
# --------------------------------------------------------------------------- #
def limb(mu):
    """2 次周辺減光 ``I(mu)/I(1)``。"""
    return 1.0 - U1 * (1.0 - mu) - U2 * (1.0 - mu) ** 2


def depth_to_p(depth: float, b: float = B) -> float:
    """深さ δ から惑星/恒星の半径比 p を出す(小惑星近似の逆)。"""
    return float(np.sqrt(depth * IBAR / limb(np.sqrt(1.0 - b * b))))


def overlap_area(z, p: float):
    """半径 1 の円と半径 p の円が距離 z にあるときの重なり面積。"""
    z = np.asarray(z, np.float64)
    a = np.zeros_like(z)
    a[z <= 1.0 - p] = np.pi * p * p
    part = (z > 1.0 - p) & (z < 1.0 + p)
    zz = z[part]
    k0 = np.arccos(np.clip((p * p + zz * zz - 1.0) / (2.0 * p * zz), -1, 1))
    k1 = np.arccos(np.clip((1.0 - p * p + zz * zz) / (2.0 * zz), -1, 1))
    a[part] = (p * p * k0 + k1
               - 0.5 * np.sqrt(np.maximum(4.0 * zz * zz - (1.0 + zz * zz - p * p) ** 2, 0.0)))
    return a


def transit_model(t, depth: float, t0: float, t14: float, b: float = B):
    """相対光度 ``1 - λ(t)``。Mandel & Agol (2002) の小惑星近似。

    ``λ = (重なり面積 / π) * I(惑星中心) / Ī``。最深部(z = b)で λ = δ。
    """
    t = np.asarray(t, np.float64)
    if depth <= 0.0:
        return np.ones_like(t)
    p = depth_to_p(depth, b)
    v = np.sqrt((1.0 + p) ** 2 - b * b) / (0.5 * t14)
    z = np.sqrt(b * b + (v * (t - t0)) ** 2)
    zc = np.clip(z, 0.0, 1.0)
    return 1.0 - overlap_area(z, p) / np.pi * limb(np.sqrt(1.0 - zc * zc)) / IBAR


# --------------------------------------------------------------------------- #
# 場面を作る                                                                    #
# --------------------------------------------------------------------------- #
def render_stars(rows, cols, fluxes, sigma: float = SIGMA, shape=SHAPE):
    """ガウス PSF の星を erf で**画素積分**して足す(総和は与えた flux に厳密)。"""
    h, w = shape
    y = np.arange(h, dtype=np.float64)[:, None]
    x = np.arange(w, dtype=np.float64)[None, :]
    s = sigma * np.sqrt(2.0)
    img = np.zeros(shape)
    for r, c, f in zip(rows, cols, fluxes):
        gy = 0.5 * (erf((y + 0.5 - r) / s) - erf((y - 0.5 - r) / s))
        gx = 0.5 * (erf((x + 0.5 - c) / s) - erf((x - 0.5 - c) / s))
        img += f * (gy * gx)
    return img


def make_flat(flat_px: float, flat_lo: float, seed: int):
    """フラット(画素感度)。低次勾配 + 画素ごとのランダム。"""
    h, w = SHAPE
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    lo = 0.5 * flat_lo * ((xx - w / 2) / (w / 2)) + 0.5 * flat_lo * ((yy - h / 2) / (h / 2))
    rng = np.random.default_rng(seed)
    return 1.0 + lo + flat_px * rng.standard_normal(SHAPE)


def make_series(depth: float = DEPTH, cloud: bool = True, drift_px: float = DRIFT_PX,
                flat_px: float = FLAT_PX, flat_lo: float = FLAT_LO, seed: int = SEED,
                flat_seed: int | None = None, jitter_px: float = JITTER_PX,
                photon: bool = True) -> dict:
    """画像列 + 真値。4 つの系統誤差はそれぞれ独立に止められる。

    ``photon=False`` は光子雑音も読み出し雑音も載せない期待値画像(5 節の
    「系統分だけ」の予測に使う。検出は通らないので真の位置で測る)。
    """
    rng = np.random.default_rng(seed)
    t = np.arange(T, dtype=np.float64)
    model = transit_model(t, depth, T0, T14)

    # (a) 透明度: なめらかな乱数(rms CLOUD_RMS)+ 一晩の傾き。全星共通の乗算
    if cloud:
        tau = gaussian_filter1d(rng.standard_normal(T), 12.0)
        tau = 1.0 + CLOUD_RMS * tau / tau.std() + CLOUD_TREND * t / (T - 1)
    else:
        tau = np.ones(T)

    # (b) ドリフト: 直線 + フレームごとのばらつき。全星共通の平行移動
    ang = np.deg2rad(DRIFT_DEG)
    shifts = np.stack([drift_px * t / (T - 1) * np.cos(ang),
                       drift_px * t / (T - 1) * np.sin(ang)], axis=1)
    shifts += jitter_px * rng.standard_normal((T, 2))

    # (c) フラット: 画素感度(補正されていない、または補正の残差)
    gain = make_flat(flat_px, flat_lo, SEED * 7 + 1 if flat_seed is None else flat_seed)

    rows0 = np.array([STARS[n]["row"] for n in NAMES])
    cols0 = np.array([STARS[n]["col"] for n in NAMES])
    ratio = np.array([STARS[n]["ratio"] for n in NAMES])

    frames = np.empty((T,) + SHAPE)
    for k in range(T):
        flux = F_TARGET * ratio * tau[k]
        flux[0] *= model[k]                                   # 目標星だけ減光
        exp_ = (render_stars(rows0 + shifts[k, 0], cols0 + shifts[k, 1], flux) + SKY) * gain
        # (d) 光子雑音 + 読み出し雑音
        if photon:
            frames[k] = rng.poisson(exp_) + READ * rng.standard_normal(SHAPE)
        else:
            frames[k] = exp_
    return {"frames": frames, "model": model, "tau": tau, "shifts": shifts,
            "gain": gain, "rows": rows0, "cols": cols0, "ratio": ratio,
            "depth": depth, "t": t}


# --------------------------------------------------------------------------- #
# 測る: 基準像 → 星表 → 各フレームの位置合わせ → 開口測光(すべて fullseye op) #
# --------------------------------------------------------------------------- #
def locate(frames, rows_true, cols_true):
    """基準像(先頭 N_REF 枚の κ-σ 合成)で星を検出し、星表の順に並べる。

    真の位置は**どの検出がどの星かを名付ける**ためだけに使う(1 px 以内)。
    測る位置は検出の重心。
    """
    ref = np.asarray(_AS.sigma_clip_stack(list(frames[:N_REF]), mode="sigma_clip"))
    if ref.ndim == 3:                       # (image, mask) が返る実装への保険
        ref = ref[0]
    det = np.asarray(_AS.star_detect(ref, threshold_sigma=DETECT_SIGMA, min_separation=4))
    ctr = np.empty((len(rows_true), 2))
    for i, (r, c) in enumerate(zip(rows_true, cols_true)):
        d = np.hypot(det[:, 0] - r, det[:, 1] - c)
        j = int(np.argmin(d))
        assert d[j] < 1.0, ("星表と検出が合わない", r, c, det[j])
        ctr[i] = det[j]
    return ref, ctr


def track(frames, ref, ctr):
    """各フレームの平行移動を ``frame_align`` で出し、星表の位置を追わせる。"""
    centers = np.empty((len(frames),) + ctr.shape)
    est = np.empty((len(frames), 2))
    for k, fr in enumerate(frames):
        m = np.asarray(_AS.frame_align(ref, fr, model="translation",
                                       threshold_sigma=DETECT_SIGMA))
        # m は frame → reference。基準の座標を frame へ移すには並進を引く
        est[k] = -m[:2, 2]
        centers[k] = ctr + est[k]
    return centers, est


def photometry(frames, centers, r_ap: float = R_AP, r_in: float = R_IN,
               r_out: float = R_OUT, supersample: int = 8):
    """開口測光。返りは ``(T, 星数)`` の flux [e-]。``supersample`` は op の既定 8。"""
    out = np.empty(centers.shape[:2])
    for k, fr in enumerate(frames):
        ph = _AS.aperture_photometry(fr, centers[k], r_aperture=r_ap, r_inner=r_in,
                                     r_outer=r_out, read_sigma=READ, supersample=supersample)
        out[k] = [p["flux"] for p in ph]
    return out


def measure(sc: dict, r_ap: float = R_AP, r_in: float = R_IN, r_out: float = R_OUT,
            recenter: bool = True) -> dict:
    ref, ctr = locate(sc["frames"], sc["rows"], sc["cols"])
    if recenter:
        centers, est = track(sc["frames"], ref, ctr)
    else:
        centers = np.repeat(ctr[None], len(sc["frames"]), axis=0)
        est = np.zeros((len(sc["frames"]), 2))
    flux = photometry(sc["frames"], centers, r_ap, r_in, r_out)
    return {"flux": flux, "centers": centers, "est_shift": est, "ref": ref}


# --------------------------------------------------------------------------- #
# 光度曲線と当てはめ                                                            #
# --------------------------------------------------------------------------- #
def oot_mask(t=None):
    """トランジット外(out-of-transit)のフレーム。"""
    t = np.arange(T) if t is None else t
    return np.abs(t - T0) > 0.5 * T14 + 2.0


def normalize(y):
    return y / np.median(y[oot_mask()])


def lightcurve(flux, which=("sum",)):
    """目標星 / 比較星アンサンブル。``which``: 星名の列、"sum"、"weighted"。"""
    tgt = flux[:, 0]
    comps = flux[:, 1:]
    if which == ("sum",):
        ref = comps.sum(axis=1)
    elif which == ("weighted_raw",):
        # 生の分散で逆分散重み —— 雲(全星共通)が分散を支配するので**罠**(2 節)
        oot = oot_mask()
        var = comps[oot].var(axis=0)
        w = comps[oot].mean(axis=0) / var
        ref = comps @ w
    elif which == ("weighted",):
        # 共通モードを外した残差の分散で重み(各星を「他の星の和」で割ってから測る)
        oot = oot_mask()
        ens = comps.sum(axis=1, keepdims=True)
        q = comps / (ens - comps)
        q = q / np.median(q[oot], axis=0)
        w = 1.0 / q[oot].var(axis=0)
        ref = (comps / np.median(comps[oot], axis=0)) @ w
    elif which == ("zero",):
        return normalize(tgt)
    else:
        idx = [NAMES.index(n) - 1 for n in which]
        ref = comps[:, idx].sum(axis=1)
    return normalize(tgt / ref)


def _full_model(t, p):
    """5 パラメータ ``(δ, t0, T14, c0, c1)`` → 相対光度(直線基線 × トランジット)。"""
    d, t0, t14, c0, c1 = p
    tc = 0.5 * (T - 1)
    return (c0 + c1 * (t - tc) / T) * transit_model(t, d, t0, t14)


def _jacobian(t, p, free):
    """固定刻みの中心差分ヤコビアン(``free`` の添字だけ)。

    ★``least_squares`` の ``res.jac``(刻み ≈ 1e-8 × 値)は δ が 1e-3 のとき
    刻みが 1e-11 になり、p = sqrt(δ) を通る経路で丸めに負けて共分散が膨らんだ
    (暦既知の σ̂ が理論の 1.4 倍に見えた)。刻みを量の尺度で固定する。
    """
    h = np.array([1e-5, 1e-2, 1e-2, 1e-5, 1e-5])
    cols = []
    for i in free:
        dp = np.zeros(5)
        dp[i] = h[i]
        cols.append((_full_model(t, p + dp) - _full_model(t, p - dp)) / (2 * h[i]))
    return np.stack(cols, axis=1)


def _grid_init(t, y, d0: float = 0.01):
    """粗い格子(t0 2 フレーム刻み × T14 5 刻み)で χ² 最小の ``(t0, T14, δ)``。

    各格子点は ``y ≈ c0 + c1 x + δ (m-1)/d0`` の**線形**最小二乗(正規方程式を
    t0 方向にまとめて解く)。t0 の格子は整数なので、テンプレートを整数だけ
    ずらして作る(モデルの再計算は T14 ごとに 1 回)。
    """
    tc = 0.5 * (T - 1)
    x = (t - tc) / T
    t0s = np.arange(40.0, 200.0, 2.0)
    ext = np.arange(-T, 2 * T, dtype=np.float64)
    best = None
    a11, a12, a22 = float(t.size), float(x.sum()), float(x @ x)
    b1, b2 = float(y.sum()), float(x @ y)
    for t14 in np.arange(20.0, 130.0, 5.0):
        tmpl = transit_model(ext, d0, 0.0, t14)
        idx = (t[None, :] - t0s[:, None]).astype(int) + T
        sm = (tmpl[idx] - 1.0) / d0                              # (n_t0, T)
        a13, a23, a33 = sm.sum(axis=1), sm @ x, (sm * sm).sum(axis=1)
        b3 = sm @ y
        n = t0s.size
        amat = np.empty((n, 3, 3))
        amat[:, 0, 0], amat[:, 0, 1], amat[:, 0, 2] = a11, a12, a13
        amat[:, 1, 0], amat[:, 1, 1], amat[:, 1, 2] = a12, a22, a23
        amat[:, 2, 0], amat[:, 2, 1], amat[:, 2, 2] = a13, a23, a33
        bvec = np.stack([np.full(n, b1), np.full(n, b2), b3], axis=1)
        coef = np.linalg.solve(amat, bvec[..., None])[..., 0]    # (n, 3)
        pred = coef[:, [0]] + coef[:, [1]] * x[None, :] + coef[:, [2]] * sm
        chi = ((y[None, :] - pred) ** 2).sum(axis=1)
        j = int(np.argmin(chi))
        if best is None or chi[j] < best[0]:
            best = (float(chi[j]), float(t0s[j]), float(t14), float(coef[j, 2]))
    _, t0i, t14i, di = best
    return t0i, t14i, float(np.clip(di, 1e-4, 0.29))


def fit_transit(t, y, fixed=None):
    """深さ・中心・継続時間 + 直線基線の 5 パラメータ最小二乗。

    初期値は :func:`_grid_init` の粗い格子から取る —— 真値を初期値に使わない
    (★最初は格子で ``y ≈ a m + c1 x`` と書いて深さを基線に縛っていたので、
    δ が小さいほど格子が真の解を外し、局所解に落ちて「暦未知だと崖は 10 ppt」
    という**偽の所見**を出しかけた。当てはめの残差が暦既知より**大きい**ことが
    その印だった)。``fixed=(t0, t14)`` なら暦を既知として深さと基線 2 つだけを
    当てはめる(既知惑星の追観測に相当)。誤差は残差 rms × 数値ヤコビアンの
    ``(JᵀJ)⁻¹``。
    """
    if fixed is not None:
        t0f, t14f = fixed
        free = [0, 3, 4]

        def resid_f(q):
            return y - _full_model(t, np.array([q[0], t0f, t14f, q[1], q[2]]))

        res = least_squares(resid_f, [0.01, 1.0, 0.0], bounds=([0.0, 0.5, -1.0], [0.3, 1.5, 1.0]),
                            x_scale=[0.01, 1, 0.1])
        pfull = np.array([res.x[0], t0f, t14f, res.x[1], res.x[2]])
    else:
        t0i, t14i, di = _grid_init(t, y)
        free = [0, 1, 2, 3, 4]

        def resid(q):
            return y - _full_model(t, np.asarray(q))

        lo = [0.0, 30.0, 10.0, 0.5, -1.0]
        hi = [0.30, 210.0, 160.0, 1.5, 1.0]
        res = least_squares(resid, [di, t0i, t14i, 1.0, 0.0], bounds=(lo, hi),
                            x_scale=[0.01, 10, 10, 1, 0.1])
        pfull = np.asarray(res.x)
    n, k = y.size, len(free)
    rss = float(res.fun @ res.fun)
    jac = _jacobian(t, pfull, free)
    try:
        cov = np.linalg.inv(jac.T @ jac) * rss / (n - k)
        sig = np.sqrt(np.maximum(np.diag(cov), 0.0))
    except np.linalg.LinAlgError:
        sig = np.full(k, np.nan)
    sig_t14 = float(sig[2]) if fixed is None else 0.0
    return {"depth": float(pfull[0]), "t0": float(pfull[1]), "t14": float(pfull[2]),
            "sig_depth": float(sig[0]), "sig_t14": sig_t14, "rms": float(np.std(res.fun)),
            "resid": res.fun, "fit": y - res.fun}


# --------------------------------------------------------------------------- #
# 理論(CCD 式)                                                                 #
# --------------------------------------------------------------------------- #
def frac_in(r: float, sigma: float = SIGMA) -> float:
    return 1.0 - np.exp(-r * r / (2.0 * sigma * sigma))


def theory_rel_noise(r: float, ratio, which=("sum",), r_in: float = R_IN,
                     r_out: float = R_OUT) -> float:
    """比 目標/アンサンブル の 1 フレーム相対雑音(Howell の CCD 式)。

    背景を環の**中央値**で推定する雑音 ``A² σ_B² (π/2) / n_annulus`` も足す
    (中央値の効率は平均の 2/π)。★最初はこれを忘れていて、大開口側で
    実測が理論より 12 % 悪かった —— 開口の画素数 A が背景の誤差を A 倍する。
    """
    f = frac_in(r)
    area = np.pi * r * r
    n_ann = np.pi * (r_out ** 2 - r_in ** 2)
    fl = F_TARGET * np.asarray(ratio, np.float64)
    var = (f * fl + area * (SKY + READ ** 2)
           + area ** 2 * (SKY + READ ** 2) * (np.pi / 2.0) / n_ann)
    rel_t = var[0] / (f * fl[0]) ** 2
    if which == ("sum",):
        sel = np.arange(1, fl.size)
        rel_c = var[sel].sum() / (f * fl[sel].sum()) ** 2
    elif which == ("weighted",):
        sel = np.arange(1, fl.size)
        w = f * fl[sel] / var[sel]
        rel_c = (w * w * var[sel]).sum() / (w * f * fl[sel]).sum() ** 2
    else:
        sel = np.array([NAMES.index(n) for n in which])
        rel_c = var[sel].sum() / (f * fl[sel].sum()) ** 2
    return float(np.sqrt(rel_t + rel_c))


def theory_sig_depth(rel_noise: float, depth: float = DEPTH, fixed: bool = False) -> float:
    """深さの推定誤差の理論値 —— Fisher 下限(``σ_rel² (JᵀJ)⁻¹`` の対角)。

    箱形近似 ``σ_rel * sqrt(1/N_in + 1/N_out)`` は t0 / T14 / 基線を同時に
    推定する分を無視するので楽観的になる。``fixed=True`` は暦既知
    (δ と基線 2 つ)、``False`` は暦未知(5 パラメータ)。
    """
    t = np.arange(T, dtype=np.float64)
    p = np.array([depth, T0, T14, 1.0, 0.0])
    jac = _jacobian(t, p, [0, 3, 4] if fixed else [0, 1, 2, 3, 4])
    cov = np.linalg.inv(jac.T @ jac) * rel_noise ** 2
    return float(np.sqrt(cov[0, 0]))


# --------------------------------------------------------------------------- #
# 1. ゼロ点 vs 相対測光(雲あり / 雲なし)                                       #
# --------------------------------------------------------------------------- #
def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点(目標星の開口積分だけ)は雲で死ぬ —— 比較星との比が救う")
    print("=" * 78)
    t = np.arange(T, dtype=np.float64)
    out = {}
    for label, cloud in (("雲あり", True), ("雲なし(対照)", False)):
        sc = make_series(cloud=cloud)
        me = measure(sc)
        rows = []
        for name, which in (("ゼロ点(目標星のみ)", ("zero",)),
                            ("比(目標 / 全比較星の和)", ("sum",))):
            y = lightcurve(me["flux"], which)
            f = fit_transit(t, y)
            rows.append((name, f))
            print("   %-12s %-24s 深さ %+7.2f ppt(誤差 %+6.2f) T14 %6.1f fr(誤差 %+5.1f) "
                  "残差 rms %5.2f ppt" % (label, name, 1e3 * f["depth"],
                                         1e3 * (f["depth"] - DEPTH), f["t14"],
                                         f["t14"] - T14, 1e3 * f["rms"]))
        out[label] = {"scene": sc, "meas": me, "fits": rows}

    sc, me = out["雲あり"]["scene"], out["雲あり"]["meas"]
    # 位置合わせの検算(ドリフトの真値との差)
    d_shift = me["est_shift"] - (sc["shifts"] - sc["shifts"][:N_REF].mean(axis=0))
    print("   位置合わせ(frame_align, 平行移動)の誤差 rms %.3f px / 最大 %.3f px"
          % (np.sqrt((d_shift ** 2).mean()), np.abs(d_shift).max()))
    out["shift_rms"] = float(np.sqrt((d_shift ** 2).mean()))

    # --- 図: 場面 ---
    fr0 = sc["frames"][0]
    oot = oot_mask()
    mid = np.abs(t - T0) < 0.2 * T14
    diff = sc["frames"][mid].mean(axis=0) - sc["frames"][oot].mean(axis=0)
    diff_pre = sc["frames"][t < 30].mean(axis=0) - sc["frames"][oot].mean(axis=0)
    up = lambda a: np.kron(a, np.ones((2, 2)))                    # 2 倍に拡大(見出しが入る幅)
    figs.save_grid("scene_starfield",
                   [up(np.sqrt(np.clip(fr0, 0, None))), up(sc["gain"] - 1.0),
                    up(diff_pre), up(diff)],
                   ["フレーム 0 [√e-]", "感度 - 1", "差分 前半 [e-]", "差分 最深部 [e-]"],
                   title="星野(目標星は中央、比較星 5 個)と、最深部で目標星だけが沈む差分",
                   ncols=2, signed=[False, True, True, True],
                   caption="112x112 px の星野を 2 倍に拡大。差分はトランジット外の平均との差 [e-]。"
                           "前半の差分に見える双極子はドリフト(位置ずれ)で、最深部では目標星(中央)だけが沈む")
    # トランジット外との差分をフレーム群ごとに(段階の図)
    phases = [("前", t < 60), ("入", (t > 78) & (t < 92)),
              ("最深部", mid), ("出", (t > 148) & (t < 162)), ("後", t > 180)]
    cut = (slice(40, 73), slice(40, 73))
    panels = [np.kron((sc["frames"][m].mean(axis=0) - sc["frames"][oot].mean(axis=0))[cut],
                      np.ones((4, 4))) for _, m in phases]
    figs.save_grid("frames_transit_phases", panels, [p for p, _ in phases],
                   title="目標星まわり 33 px の差分(各段階の平均 - トランジット外の平均)[e-]",
                   ncols=5, signed=True,
                   caption="前/入/最深部/出/後の各段階で平均した画像からトランジット外の平均を引いた [e-]。4 倍拡大")
    # 光度曲線
    zero = lightcurve(me["flux"], ("zero",))
    comp = normalize(me["flux"][:, 1:].sum(axis=1))
    ratio = lightcurve(me["flux"], ("sum",))
    figs.save_plot("lightcurve_zero_vs_relative",
                   [("目標星の開口積分(ゼロ点)", t, zero),
                    ("比較星 5 個の和(-0.12)", t, comp - 0.12),
                    ("比 目標/比較星(-0.22)", t, ratio - 0.22),
                    ("真のトランジット(-0.22)", t, sc["model"] - 0.22)],
                   xlabel="フレーム", ylabel="相対光度(見やすさのため上下にずらした)",
                   title="雲(透明度 rms 3 %)の下で: ゼロ点は雲そのもの、比を取ると 1 % の凹みが残る",
                   caption="ゼロ点と比較星の和は雲(全星共通)そのもの。比を取ると 10 ppt の凹みが真値の上に乗る")
    figs.save_plot("transparency_truth", [("透明度 τ(t)", t, sc["tau"]),
                                          ("目標星のモデル", t, sc["model"])],
                   xlabel="フレーム", ylabel="相対値",
                   title="仕込んだ透明度変動(全星共通)と、目標星だけの減光")
    return out


# --------------------------------------------------------------------------- #
# 2. 比較星の選び方                                                             #
# --------------------------------------------------------------------------- #
def section_comparison_choice(sec1: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) 比較星の選び方で精度が何倍変わるか(同じ画像列、同じ開口)")
    print("=" * 78)
    me = sec1["雲あり"]["meas"]
    sc = sec1["雲あり"]["scene"]
    t = np.arange(T, dtype=np.float64)
    choices = [("A(明るい 2.0 倍)1 星", ("比較A",)),
               ("B(同じ明るさ)1 星", ("比較B",)),
               ("C(0.5 倍)1 星", ("比較C",)),
               ("E(0.12 倍)1 星", ("比較E",)),
               ("A+B(明るい 2 星の和)", ("比較A", "比較B")),
               ("全 5 星の単純和", ("sum",)),
               ("逆分散重み(生の分散)", ("weighted_raw",)),
               ("逆分散重み(共通モード除去後)", ("weighted",))]
    rows, res = [], {}
    print("   %-24s 残差rms  理論   深さ誤差  σ(深さ)  T14誤差  σ(T14)" % "比較星")
    for name, which in choices:
        f = fit_transit(t, lightcurve(me["flux"], which))
        th = theory_rel_noise(R_AP, sc["ratio"], ("weighted",) if which == ("weighted_raw",) else which)
        res[name] = (f, th)
        print("   %-24s %5.2f  %5.2f   %+6.2f    %5.2f    %+5.1f    %4.1f  [ppt / fr]" % (
            name, 1e3 * f["rms"], 1e3 * th, 1e3 * (f["depth"] - DEPTH),
            1e3 * f["sig_depth"], f["t14"] - T14, f["sig_t14"]))
    best = min(res.values(), key=lambda v: v[0]["rms"])[0]["rms"]
    worst = max(res.values(), key=lambda v: v[0]["rms"])[0]["rms"]
    for name, (f, th) in res.items():
        rows.append([name, "%.2f" % (1e3 * f["rms"]), "%.2f" % (1e3 * th),
                     "%+.2f" % (1e3 * (f["depth"] - DEPTH)), "%.2f" % (1e3 * f["sig_depth"]),
                     "%+.1f" % (f["t14"] - T14), "%.1f" % f["sig_t14"],
                     "%.1f 倍" % (f["rms"] / best)])
    print("\n   ★最良 %.2f ppt / 最悪 %.2f ppt = **%.1f 倍**。深さの σ はその比で動くが、"
          "T14 の誤差はそうならない。" % (1e3 * best, 1e3 * worst, worst / best))
    raw = res["逆分散重み(生の分散)"][0]["rms"]
    good = res["逆分散重み(共通モード除去後)"][0]["rms"]
    print("   ★逆分散重みは**生の分散で決めると罠**: 雲(全星共通)が明るい星の分散を支配し"
          "重みが暗い星へ行く → %.2f ppt(単純和 %.2f の %.2f 倍)。共通モードを外して"
          "測り直すと %.2f ppt。" % (1e3 * raw, 1e3 * res["全 5 星の単純和"][0]["rms"],
                                   raw / res["全 5 星の単純和"][0]["rms"], 1e3 * good))
    figs.save_table("comparison_choice",
                    ["比較星", "残差 rms ppt", "理論 ppt", "深さ誤差 ppt", "σ深さ ppt",
                     "T14 誤差 fr", "σT14 fr", "最良比"],
                    rows, title="比較星の選び方(同じ画像列・開口 3σ)")
    return {"res": res, "ratio": worst / best, "raw": raw, "good": good}


# --------------------------------------------------------------------------- #
# 3. 崖 A: 開口半径                                                             #
# --------------------------------------------------------------------------- #
def section_aperture_sweep(sec1: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) 開口半径の崖 —— 小さい側で壊れるのは重心誤差ではなかった")
    print("=" * 78)
    sc = sec1["雲あり"]["scene"]
    t = np.arange(T, dtype=np.float64)
    ref, ctr = locate(sc["frames"], sc["rows"], sc["cols"])
    centers, _ = track(sc["frames"], ref, ctr)
    # 対照群: 位置のジッタもドリフトも止める(星は画素に対して動かない)
    sc0 = make_series(drift_px=0.0, jitter_px=0.0)
    ref0, ctr0 = locate(sc0["frames"], sc0["rows"], sc0["cols"])
    centers0, _ = track(sc0["frames"], ref0, ctr0)
    ks = np.array([1.0, 1.5, 2.0, 3.0, 4.0, 6.0])
    meas, theo, derr, terr, ctl, meas32, ctl32 = [], [], [], [], [], [], []
    print("   r/σ   r[px]  理論   動く(ss8) 比    不動(ss8) 比    動く(ss32) 比   不動(ss32) 比"
          "   深さ誤差  T14誤差")
    for k in ks:
        r = k * SIGMA
        r_in = max(R_IN, r + 1.5)
        th = theory_rel_noise(r, sc["ratio"], r_in=r_in, r_out=r_in + 4.0)
        f = fit_transit(t, lightcurve(photometry(sc["frames"], centers, r, r_in, r_in + 4.0),
                                      ("sum",)))
        f0 = fit_transit(t, lightcurve(photometry(sc0["frames"], centers0, r, r_in, r_in + 4.0),
                                       ("sum",)))
        f32 = fit_transit(t, lightcurve(photometry(sc["frames"], centers, r, r_in, r_in + 4.0,
                                                   supersample=32), ("sum",)))
        f032 = fit_transit(t, lightcurve(photometry(sc0["frames"], centers0, r, r_in, r_in + 4.0,
                                                    supersample=32), ("sum",)))
        meas.append(f["rms"]); theo.append(th); ctl.append(f0["rms"])
        meas32.append(f32["rms"]); ctl32.append(f032["rms"])
        derr.append(f["depth"] - DEPTH); terr.append(f["t14"] - T14)
        print("   %3.1f   %4.2f  %5.2f   %5.2f   %4.2f   %5.2f   %4.2f   %5.2f    %4.2f   %5.2f   %4.2f"
              "   %+6.2f    %+5.1f  [ppt / fr]"
              % (k, r, 1e3 * th, 1e3 * f["rms"], f["rms"] / th, 1e3 * f0["rms"], f0["rms"] / th,
                 1e3 * f32["rms"], f32["rms"] / th, 1e3 * f032["rms"], f032["rms"] / th,
                 1e3 * (f["depth"] - DEPTH), f["t14"] - T14))
    meas, theo, ctl = np.array(meas), np.array(theo), np.array(ctl)
    meas32, ctl32 = np.array(meas32), np.array(ctl32)
    print("\n   ★予想は「r=1σ では重心誤差(rms %.3f px)が明るさに化けて理論より 27 %% 悪い」。"
          "実測は %+.0f %%、対照群(星が画素に対して不動)では**%+.0f %%(逆に悪化)**。"
          % (sec1["shift_rms"], 100 * (meas[0] / theo[0] - 1), 100 * (ctl[0] / theo[0] - 1)))
    print("   開口が中心対称なので位置誤差 ε の効き目は 2 次(ε² ≈ %.4f px²)で効かない。"
          "効いていたのは **op の開口マスクの階段**: supersample=8 は縁の画素の重みを 1/64 刻みで"
          "\n   量子化するので、r=1σ では縁の 1 画素が総光量の %.1f %% を持ち、1 段の跳びが %.2f ppt。"
          "supersample=32 にすると 動く %.2f / 不動 %.2f ppt(理論比 %.2f / %.2f)に落ちる。"
          % (sec1["shift_rms"] ** 2,
             100 * float(render_stars([20.0], [20.0], [1.0], SIGMA, (41, 41))[20, 21]),
             1e3 * float(render_stars([20.0], [20.0], [1.0], SIGMA, (41, 41))[20, 21]) / 64,
             1e3 * meas32[0], 1e3 * ctl32[0], meas32[0] / theo[0], ctl32[0] / theo[0]))
    figs.save_plot("aperture_sweep",
                   [("動く星, supersample 8(op 既定)", ks, 1e3 * meas),
                    ("不動の星, supersample 8", ks, 1e3 * ctl),
                    ("動く星, supersample 32", ks, 1e3 * meas32),
                    ("不動の星, supersample 32", ks, 1e3 * ctl32),
                    ("理論 CCD 式(背景推定込み)", ks, 1e3 * theo)],
                   xlabel="開口半径 r / σ", ylabel="比の 1 フレーム雑音 [ppt]",
                   title="開口半径の掃引: 小さい側の崖は開口マスクの階段、大きい側の坂は空と背景推定")
    figs.save_plot("aperture_depth_bias",
                   [("深さの誤差", ks, 1e3 * np.array(derr))],
                   xlabel="開口半径 r / σ", ylabel="深さの誤差 [ppt](真値 10 ppt)",
                   title="開口が小さいと深さも偏る")
    return {"k": ks, "meas": meas, "theo": theo, "ctl": ctl, "meas32": meas32,
            "ctl32": ctl32, "derr": np.array(derr), "terr": np.array(terr)}


# --------------------------------------------------------------------------- #
# 4. 崖 B: 深さの検出限界                                                       #
# --------------------------------------------------------------------------- #
def section_depth_cliff() -> dict:
    print("\n" + "=" * 78)
    print("4) 深さの崖 —— SNR = 5 の境目を理論の CCD 式が予測できるか")
    print("=" * 78)
    t = np.arange(T, dtype=np.float64)
    depths = np.array([0.0005, 0.001, 0.0015, 0.002, 0.003, 0.005, 0.010])
    seeds = (101, 102, 103)
    th_noise = theory_rel_noise(R_AP, np.array([STARS[n]["ratio"] for n in NAMES]))
    snr_m, snr_t, derr, terr, rms_m = [], [], [], [], []
    print("   δ[ppt]  暦未知: SNR(δ^/σ^) 理論  深さ誤差[ppt] |T14誤差|[fr]   暦既知: δ/σ^  理論  "
          "既知/理論  深さ誤差   (3 seed の平均)")
    snr_true, derr_k, snr_t5 = [], [], []
    for d in depths:
        sm, st_, de, dk, te, rr = [], [], [], [], [], []
        for s in seeds:
            sc = make_series(depth=d, seed=s, drift_px=0.0, flat_px=0.0)
            y = lightcurve(measure(sc)["flux"], ("sum",))
            f = fit_transit(t, y)                              # 暦未知(t0, T14 も探す)
            fk = fit_transit(t, y, fixed=(T0, T14))            # 暦既知(深さだけ)
            sm.append(f["depth"] / f["sig_depth"]); st_.append(d / fk["sig_depth"])
            de.append(f["depth"] - d); dk.append(fk["depth"] - d)
            te.append(abs(f["t14"] - T14)); rr.append(f["rms"])
        st = d / theory_sig_depth(th_noise, d, fixed=True)
        st5 = d / theory_sig_depth(th_noise, d, fixed=False)
        snr_m.append(np.mean(sm)); snr_true.append(np.mean(st_)); snr_t.append(st)
        snr_t5.append(st5)
        derr.append(np.mean(de)); derr_k.append(np.mean(dk)); terr.append(np.mean(te))
        rms_m.append(np.mean(rr))
        print("   %5.1f         %5.2f       %5.2f   %+6.2f       %6.1f          %5.2f   %5.2f    %4.2f"
              "    %+6.2f"
              % (1e3 * d, np.mean(sm), st5, 1e3 * np.mean(de), np.mean(te), np.mean(st_), st,
                 np.mean(st_) / st, 1e3 * np.mean(dk)))
    snr_m, snr_t, snr_true = np.array(snr_m), np.array(snr_t), np.array(snr_true)
    snr_t5 = np.array(snr_t5)

    def cross(snr):
        # SNR は δ にほぼ比例するので log-log で 5 を横切る δ を補間
        return float(np.exp(np.interp(np.log(5.0), np.log(snr), np.log(depths))))
    dm, dt_ = cross(snr_true), cross(snr_t)
    blind = [1e3 * d for d, e in zip(depths, terr) if e < 5.0]
    blind_min = min(blind) if blind else float("nan")
    print("\n   SNR = 5 の境目(暦既知): 実測 %.2f ppt / 理論(CCD 式 + Fisher)%.2f ppt。"
          "既知/理論の比は %.2f〜%.2f。暦未知の理論(5 パラメータ)は %.2f ppt。"
          % (1e3 * dm, 1e3 * dt_, (snr_true / snr_t).min(), (snr_true / snr_t).max(),
             1e3 * cross(snr_t5)))
    print("   ★暦未知だと崖は %.1f ppt(|T14 誤差| < 5 fr になる最小の δ)—— 暦既知の Fisher 限界の "
          "%.1f 倍。局所の下限は t0/T14 を知らない探索には効かない。" % (blind_min, blind_min / (1e3 * dt_)))
    print("   ★暦未知の SNR(δ^/σ^)は限界の下でも %.1f〜%.1f と出る(δ^ が過大: δ=%.1f ppt で "
          "%+.2f ppt)—— 雑音を惑星と呼んでいる。" % (snr_m[0], snr_m[2], 1e3 * depths[0], 1e3 * derr[0]))
    print("   ★検出できない δ=%.1f ppt では |T14 誤差| %.0f フレーム —— 深さより先に"
          "継続時間が壊れる。" % (1e3 * depths[0], terr[0]))
    figs.save_plot("depth_cliff",
                   [("暦未知の当てはめ(推定深さ/σ)", 1e3 * depths, snr_m),
                    ("暦既知の当てはめ(真の深さ/σ)", 1e3 * depths, snr_true),
                    ("理論(暦既知)CCD 式 + Fisher", 1e3 * depths, snr_t),
                    ("理論(暦未知)", 1e3 * depths, snr_t5),
                    ("SNR = 5", 1e3 * depths, np.full(depths.size, 5.0))],
                   xlabel="深さ δ [ppt]", ylabel="深さの検出 SNR",
                   title="深さの検出限界: 暦既知なら理論どおり、暦未知は限界の下で SNR が嘘をつく")
    figs.save_plot("depth_cliff_t14",
                   [("|T14 の誤差| [frame]", 1e3 * depths, np.array(terr)),
                    ("深さの誤差 [0.1 ppt]", 1e3 * depths, 1e4 * np.array(derr))],
                   xlabel="深さ δ [ppt]", ylabel="誤差",
                   title="検出限界の下では継続時間が先に壊れる")
    return {"depths": depths, "snr_m": snr_m, "snr_t": snr_t, "snr_true": snr_true,
            "derr": np.array(derr), "derr_k": np.array(derr_k), "blind_min": blind_min,
            "snr_t5": snr_t5,
            "terr": np.array(terr), "cross_m": dm, "cross_t": dt_}


# --------------------------------------------------------------------------- #
# 5. 崖 C: ドリフト × フラット不均一                                            #
# --------------------------------------------------------------------------- #
def psf_weight_norm(sigma: float = SIGMA) -> float:
    """``sqrt(sum w^2)``: 画素フラットのばらつきが星の明るさに移る係数。"""
    w = render_stars([20.0], [20.0], [1.0], sigma, (41, 41))
    return float(np.sqrt((w * w).sum()))


def section_drift_flat() -> dict:
    print("\n" + "=" * 78)
    print("5) ドリフト × フラット不均一 —— 単独では無害、掛け算で偽の深さ")
    print("=" * 78)
    t = np.arange(T, dtype=np.float64)
    drifts = np.array([0.0, 1.0, 2.0, 4.0])
    flats = np.array([0.0, 0.01, 0.03])
    seeds = (201, 202)
    coef = psf_weight_norm()
    print("   予測(上限): 偽の明るさ変化 rms ≈ a * sqrt(Σw²) = %.3f a → a=1 %% で %.2f ppt、"
          "a=3 %% で %.2f ppt" % (coef, 1e3 * 0.01 * coef, 1e3 * 0.03 * coef))
    print("   ドリフト[px]  画素フラット  深さ誤差 rms[ppt]  系統分の予測 rms  差の rms  "
          "|T14誤差| rms[fr]  残差rms[ppt]  (2 seed)")
    grid = np.zeros((flats.size, drifts.size))       # 深さ誤差の rms(符号はフラット次第)
    grid_p = np.zeros_like(grid)                     # 雑音なし・真の位置で測った系統分
    grid_t = np.zeros_like(grid)
    rows = []
    for i, a in enumerate(flats):
        for j, dpx in enumerate(drifts):
            de, dp, te, rr = [], [], [], []
            for s in seeds:
                sc = make_series(drift_px=dpx, flat_px=a, cloud=False, seed=s,
                                 flat_seed=s * 13 + 5)
                f = fit_transit(t, lightcurve(measure(sc)["flux"], ("sum",)))
                de.append(f["depth"] - DEPTH); te.append(f["t14"] - T14); rr.append(f["rms"])
                # 系統分の予測: 同じフラット・同じドリフトで雑音を切り、真の位置に開口を置く
                # (フラット均一なら恒等的に 0 なので省く)
                if a == 0.0:
                    dp.append(0.0)
                    continue
                sn = make_series(drift_px=dpx, flat_px=a, cloud=False, seed=s,
                                 flat_seed=s * 13 + 5, photon=False)
                ctr = np.stack([sn["rows"], sn["cols"]], axis=1)
                fp = fit_transit(t, lightcurve(photometry(sn["frames"], ctr[None] + sn["shifts"][:, None, :]),
                                               ("sum",)))
                dp.append(fp["depth"] - DEPTH)
            de, dp = np.array(de), np.array(dp)
            grid[i, j] = np.sqrt(np.mean(de ** 2))
            grid_p[i, j] = np.sqrt(np.mean(dp ** 2))
            grid_t[i, j] = np.sqrt(np.mean(np.square(te)))
            resid = np.sqrt(np.mean((de - dp) ** 2))
            rows.append(["%.1f" % dpx, "%.0f %%" % (100 * a), "%.2f" % (1e3 * grid[i, j]),
                         "%.2f" % (1e3 * grid_p[i, j]), "%.2f" % (1e3 * resid),
                         "%.1f" % grid_t[i, j], "%.2f" % (1e3 * np.mean(rr))])
            print("   %5.1f         %4.0f %%         %5.2f            %5.2f         %5.2f       %5.1f"
                  "          %5.2f" % (dpx, 100 * a, 1e3 * grid[i, j], 1e3 * grid_p[i, j],
                                       1e3 * resid, grid_t[i, j], 1e3 * np.mean(rr)))
    print("\n   対照群(深さ誤差 rms): ドリフト 2 px・フラット均一 %.2f ppt / ドリフト 0・"
          "フラット 3 %% %.2f ppt / 両方 %.2f ppt(真値 10 ppt の %.0f %%)/ ドリフト 4 px・"
          "3 %% %.2f ppt(%.0f %%)"
          % (1e3 * grid[0, 2], 1e3 * grid[-1, 0], 1e3 * grid[-1, 2], 100 * grid[-1, 2] / DEPTH,
             1e3 * grid[-1, -1], 100 * grid[-1, -1] / DEPTH))
    print("   予測上限 %.2f ppt に対し 2 px で %.2f ppt = %.0f %%、4 px で %.0f %%"
          "(直線基線が大半を吸う。動く量が PSF の幅を超えると吸えなくなる)"
          % (1e3 * 0.03 * coef, 1e3 * grid[-1, 2], 100 * grid[-1, 2] / (0.03 * coef),
             100 * grid[-1, -1] / (0.03 * coef)))
    print("   雑音を切って真の位置で測った系統分の予測は、実測と seed ごとに一致する"
          "(差の rms は雑音の床 %.2f ppt 程度)。" % (1e3 * np.sqrt(np.mean(grid[0] ** 2))))
    figs.save_table("drift_flat_table",
                    ["ドリフト px", "画素フラット", "深さ誤差 rms ppt", "系統分の予測 rms ppt",
                     "差の rms ppt", "|T14 誤差| rms fr", "残差 rms ppt"], rows,
                    title="ドリフト × フラット不均一(雲なし・開口 3σ・2 seed)")
    figs.save_plot("drift_flat_map",
                   [("フラット均一(対照)", drifts, 1e3 * grid[0]),
                    ("画素フラット 1 %", drifts, 1e3 * grid[1]),
                    ("画素フラット 3 %", drifts, 1e3 * grid[2]),
                    ("3 % の系統分予測(雑音なし)", drifts, 1e3 * grid_p[2])],
                   xlabel="一晩のドリフト [px]", ylabel="深さの誤差 rms [ppt](真値 10 ppt)",
                   title="偽の深さはドリフトとフラットの積で生まれる")
    return {"grid": grid, "grid_p": grid_p, "grid_t": grid_t, "coef": coef, "drifts": drifts,
            "flats": flats}


# --------------------------------------------------------------------------- #
def main() -> int:
    t_start = time.perf_counter()
    print("系外惑星トランジット: %dx%d px, %d 枚, PSF σ %.1f px, 目標星 %.0f e-/枚, "
          "δ %.1f ppt, T14 %.0f fr, b %.2f, u1/u2 %.2f/%.2f"
          % (SHAPE[0], SHAPE[1], T, SIGMA, F_TARGET, 1e3 * DEPTH, T14, B, U1, U2))
    p = depth_to_p(DEPTH)
    print("   半径比 p = %.4f(δ = p² I(b)/Ī)、開口 r = %.1f px(%.1f σ、拾う割合 %.3f)"
          % (p, R_AP, R_AP / SIGMA, frac_in(R_AP)))
    # モデルの検算: 最深部の減光が δ に一致、トランジット外は厳密に 1
    m = transit_model(np.arange(T), DEPTH, T0, T14)
    assert abs((1.0 - m.min()) - DEPTH) < 1e-12, m.min()
    assert np.all(m[oot_mask()] == 1.0)

    tt = time.perf_counter()
    s1 = section_zero_point()
    s2 = section_comparison_choice(s1)
    print("   [%.1f s]" % (time.perf_counter() - tt)); tt = time.perf_counter()
    s3 = section_aperture_sweep(s1)
    print("   [%.1f s]" % (time.perf_counter() - tt)); tt = time.perf_counter()
    s4 = section_depth_cliff()
    print("   [%.1f s]" % (time.perf_counter() - tt)); tt = time.perf_counter()
    s5 = section_drift_flat()
    print("   [%.1f s]" % (time.perf_counter() - tt))

    # --- 所見を固定する(壊れたら鳴る) ---------------------------------------
    fz, fr_ = s1["雲あり"]["fits"][0][1], s1["雲あり"]["fits"][1][1]
    fz0 = s1["雲なし(対照)"]["fits"][0][1]
    assert abs(fz["depth"] - DEPTH) > 0.03, "雲でゼロ点が壊れていない"
    assert abs(fz0["depth"] - DEPTH) < 0.5e-3 and abs(fz0["t14"] - T14) < 3.0, "雲なしのゼロ点は当たるはず"
    assert abs(fr_["depth"] - DEPTH) < 0.5e-3 and abs(fr_["t14"] - T14) < 3.0, "比は雲ありでも当たるはず"
    assert s1["shift_rms"] < 0.1
    assert s2["ratio"] > 4.0, s2["ratio"]
    assert s2["raw"] > 1.3 * s2["res"]["全 5 星の単純和"][0]["rms"], "生の分散の罠が消えた"
    assert s2["good"] < 1.1 * s2["res"]["全 5 星の単純和"][0]["rms"]
    assert s3["ctl"][0] / s3["theo"][0] > 1.4, "不動の星の r=1σ が理論並みになった(階段が消えた?)"
    assert s3["meas32"][0] / s3["theo"][0] < 1.0 and s3["ctl32"][0] / s3["theo"][0] < 1.0
    assert np.all(s3["meas"][2:] / s3["theo"][2:] < 1.15)
    assert abs(s4["cross_m"] - s4["cross_t"]) < 0.3e-3, (s4["cross_m"], s4["cross_t"])
    assert np.all((s4["snr_true"] / s4["snr_t"])[1:] > 0.9)
    assert s4["blind_min"] <= 3.0 and s4["terr"][0] > 15.0
    g, gp = s5["grid"], s5["grid_p"]
    assert g[0, 2] < 0.3e-3 and g[2, 0] < 0.3e-3, "単独では無害のはず"
    assert g[2, 2] > 0.6e-3 and g[2, 3] > 2.0e-3, "掛け算で偽の深さ"
    assert abs(g[2, 3] - gp[2, 3]) < 0.3e-3, "系統分の予測が実測と合わない"
    assert g[2, 3] < 0.03 * s5["coef"], "予測上限を超えた"
    print("\n所要 %.1f s" % (time.perf_counter() - t_start))
    if figs.errors():
        print("図の警告:", figs.errors())
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

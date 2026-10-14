# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: ピクセルシフト撮像 —— センサを 1 画素動かすと偽色が消え、半画素動かすと折り返しが消える。ただし MTF は上がらない。

    py -3.11 examples/poc_pixel_shift.py

【問い】ピクセルシフト(撮像素子を圧電アクチュエータで 1 画素 / 半画素ずつ動かして複数枚撮る)は、外観検査で何を
増やし、何を増やさないか。いつ壊れるか。新 op 6 本(``pixelshift``)を、閉形式の真値と既存の op(``gfx2d`` の
デモザイク、``edgesfr`` の傾いたエッジ、``optics`` の Airy と回折の MTF、``astrostack`` の drizzle)で採点する。

  0. **閉形式を先に印字**: 画素の開口の MTF = |sinc(f)|(ナイキスト 0.5 cyc/px で 2/π = 0.637、MTF50 は
     0.603 cyc/px)、1 枚では f > 0.5 が |f − round f| に折り返る、半画素シフトでナイキストは 1.0、
     回折は Q = λN/p で決まり Q ≥ 2 ならレンズ律速、雑音は同じ点の標本数 n で σ/√n。
  1. **1 画素シフト 4 枚で偽色が消える**(基板の配線・織物・印刷の網点・解像チャートの 4 題材、Bayer):
     1 枚 + 双線形デモザイク(``gfx2d.raw_demosaic_bilinear``)と比べ、偽色(``false_color_metric``)と輝度の誤差。
     ★静止・シフト誤差 0・雑音なしなら 4 枚の偽色は**定義上 0**(各画素の R・G・B が同じ開口で同じ点を見る)——
     「異常に良い」のではなく、そう作ったから。壊れる条件は 4・5 章。
  2. **半画素シフトで折り返しが消える**(白黒センサ、half4): 縞 f₀ = 0.30〜0.90 cyc/px の FFT の山は、1 枚では
     折り返し 1 − f₀ に、半画素シフトでは f₀ に立つ。山の高さは sinc(f₀)·MTF_lens(f₀Q) の閉形式。drizzle
     (``astrostack.drizzle_resample``)で独立に合わせて一致を確かめる。★傾いたエッジの MTF50 は 1 枚でも半画素
     シフトでも同じ(開口の sinc は動かない)—— 「解像度が 2 倍」は MTF の話ではない。Bayer の 16 枚は色と帯域の両方。
  3. **レンズ律速と画素律速の境目**: 画素 3.45 µm、F 1.4〜22(Q = 0.22〜3.5)で f₀ = 0.7 cyc/px の縞を半画素
     シフトで撮り、山の高さを閉形式と突き合わせる。Q > 1/0.7 = 1.43 でレンズが縞を消し、シフトしても何も戻らない。
     開口率 0.5(マイクロレンズなし)なら開口の零点が 2 cyc/px に下がり、シフトの得が大きい。
  4. **シフトの誤差と振動**: 1 枚だけ dc が δ 外れたときの色の誤差は 2πf·a·sinc(f)·δ/√2(小さい δ の閉形式)。
     乱数の誤差 σ = 0〜0.2 px で偽色がどう増え、どこで 1 枚のデモザイクに追いつくか。
  5. **動く被写体(搬送中のワーク)**: 4 枚の間に部品が 0.25 px/枚 動くと、合わせた像に櫛と色の縁が出る。
     動き検出(同じ点の 2 つの G の食い違い、``pixel_shift_motion_mask``)で動いた所だけ 1 枚のデモザイクに
     差し戻すと、動いた所の偽色が下がり、止まっている所は 4 枚の画質のまま。
  6. **雑音は √N、動けば誤差**: 4 枚を c 周(4c 枚)撮ると、R・B は σ/√c、G は σ/√(2c)。動く被写体では枚数を
     増やすほど静止部の雑音は下がるが、動いた所の誤差は増える。

【外部真値】閉形式(sinc の開口 MTF、回折の MTF、ナイキストと折り返し、√N)、合成シーンの既知の周波数と既知のシフト、
既存 op(gfx2d のデモザイク、edgesfr の ISO 12233 の手順、optics の Airy・回折 MTF、astrostack の drizzle)。【学習】0。
【較正】0。

★正直に書いておくこと:
  * 合成のシーンと理想の撮像素子(箱の開口、画素間のクロストークなし、マイクロレンズは開口率で代表)。実機の
    センサの開口は箱でなく、カラーフィルタの分光の重なりもある(ここでは 3 色が完全に分かれる)。
  * シーンは 1 センサ画素 = 8 × 8 標本で描き、標本の升の中を一定とみなす。開口の積分はその仮定のもとで厳密(op の
    テストで 1e-12)。縞は升の平均で描いたので、升の境界に乗るシフト(1 画素・半画素)では連続の縞と同じ値になる。
  * 双線形のデモザイクは教科書の基準(gfx2d にあるのはこれだけ)。エッジに沿う補間・周波数領域の手法なら偽色は
    もっと少ない —— 4 枚との差はここで見るより縮む。
  * 動き検出の閾値 4σ はこの PoC の選択。雑音の σ は差の中央値から推定(動く画素が半数を超えると壊れる)。

EXTEND: 実機でやるなら、``pixel_shift_capture`` を実カメラの連写(シフト機能のある機種の raw、または圧電ステージに
載せた検査カメラ)に置き換え、``pixel_shift_merge`` には**公称の**シフトを渡す。真値が無いので、(1) 静止した解像
チャートで 4 枚 / 1 枚の偽色を ``false_color_metric``(無彩色のチャートなら reference なし)で比べ、(2) 傾いたエッジ
で ``edgesfr`` の MTF50 が 1 枚と半画素シフトで変わらないことを確かめ、(3) ゾーンプレートか縞で折り返しの山の位置を
読む。レンズの F 値は ``pixel_shift_resolution_budget`` で Q = λN/p < 2 を先に確かめてから選ぶ(Q ≥ 2 なら
ピクセルシフトに払う時間は解像を買わない)。動く対象では ``motion_threshold`` を必ず立て、``pixel_shift_motion_mask``
の割合を検査の記録に残す。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np
from scipy import ndimage as ndi
from scipy import signal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import astrostack as AS  # noqa: E402
import edgesfr as ES  # noqa: E402
import examplefig as figs  # noqa: E402
import gfx2d  # noqa: E402
import optics  # noqa: E402
import pixelshift as PS  # noqa: E402
import printpath  # noqa: E402
import surfacelib  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

F = 8                                   # 1 センサ画素あたりのシーンの標本数
PITCH_UM = 3.45                         # 画素の間隔(産業用の 5 Mpx 級でよく見る値)
LAM_UM = 0.55
N_DEFAULT = 2.8                         # 既定のレンズの F 値(Q = 0.45: 画素律速)
NS = 64 if REDUCED else 112             # センサの画素数(一辺)
MARGIN = 2                              # シフトの余白(全シフトで同じ m にそろえる)

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


# ─────────────────────────────── シーン(1 センサ画素 = F × F 標本) ───────────────────────────────
def _grid(n_px):
    """シーンの標本の中心の座標 [センサ画素] (余白込み)。"""
    hs = (n_px + 2 * MARGIN) * F
    c = (np.arange(hs) + 0.5) / F
    return np.meshgrid(c, c, indexing="ij")


def _lens_blur(img, f_number=N_DEFAULT):
    """回折のぼけ(``optics.airy_pattern`` を標本の間隔で引いた PSF)。"""
    psf = optics.airy_pattern(size=8 * F + 1, wavelength_um=LAM_UM, f_number=f_number, pixel_pitch_um=PITCH_UM / F)
    psf = psf / psf.sum()
    pad = psf.shape[0] // 2
    out = np.empty_like(img)
    chans = [img] if img.ndim == 2 else [img[..., k] for k in range(img.shape[2])]
    for k, ch in enumerate(chans):
        p = np.pad(ch, pad, mode="reflect")
        b = signal.fftconvolve(p, psf, mode="same")[pad:-pad, pad:-pad]
        if img.ndim == 2:
            out = b
        else:
            out[..., k] = b
    return np.clip(out, 0.0, 1.0)


def _soft(d, w=0.5 / F):
    """距離 d [px] からの被覆率(幅 1 標本の傾斜)。"""
    return np.clip(0.5 - d / (2 * w), 0.0, 1.0)


def scene_pcb(n_px, seed=1):
    """基板: 緑のソルダーレジストの上に銅の配線(間隔 2.4〜2.8 px、0°・45°)、電源線、ビア、白いシルク。"""
    y, x = _grid(n_px)
    rng = np.random.default_rng(seed)
    base = np.array([0.10, 0.36, 0.17])
    tex = ndi.gaussian_filter(rng.standard_normal(y.shape), F * 0.8) * 0.15
    img = base[None, None, :] * (1.0 + tex[..., None])
    copper = np.array([0.86, 0.58, 0.32])
    silk = np.array([0.93, 0.93, 0.90])
    cov = np.zeros(y.shape)
    # 水平の配線の束(間隔 2.4 px、幅 1.1 px)と 45° の束(間隔 2.8 px、幅 1.2 px)、太い電源線
    for k in range(int(n_px * 0.45 / 2.4)):
        yc = 4.0 + k * 2.4
        cov = np.maximum(cov, _soft(np.abs(y - yc) - 0.55) * (x < n_px * 0.55))
    u = (x - y) / math.sqrt(2.0)
    for k in range(-30, 30):
        uc = k * 2.8
        cov = np.maximum(cov, _soft(np.abs(u - uc) - 0.6) * (x > n_px * 0.58) * (y < n_px * 0.62))
    cov = np.maximum(cov, _soft(np.abs(x - n_px * 0.3) - 1.6) * (y > n_px * 0.5))
    for k in range(6):                                  # ビア
        cy, cx = n_px * (0.7 + 0.04 * k), n_px * (0.62 + 0.05 * k)
        r = np.hypot(y - cy, x - cx)
        cov = np.maximum(cov, _soft(r - 1.4))
        img = img * (1 - _soft(r - 0.6)[..., None]) + 0.05 * _soft(r - 0.6)[..., None]
    img = img * (1 - cov[..., None]) + copper[None, None, :] * cov[..., None]
    # シルクの細い文字の代わりに、0.6 px 幅の細線の格子(部品の枠)
    box = (np.abs(((y - n_px * 0.08) % 6.0) - 3.0) < 0.3) & (x > n_px * 0.62) & (x < n_px * 0.95) & (y > n_px * 0.66)
    img[box] = silk
    return _lens_blur(img)


def scene_weave(n_px):
    """織物: 経糸(紺)と緯糸(生成り)が 3.6 px 周期で交差し、8° 傾く。法線は ``surfacelib.weave_normals``。"""
    hs = (n_px + 2 * MARGIN) * F
    per = 3.6 * F
    ang = 8.0
    nrm = surfacelib.weave_normals((hs, hs), warp_px=per, weft_px=per, depth=0.45, angle_deg=ang)
    light = np.array([0.35, -0.25, 0.9])
    light = light / np.linalg.norm(light)
    shade = np.clip(nrm @ light, 0.0, 1.0)
    yy, xx = np.mgrid[0:hs, 0:hs].astype(np.float64)
    a = math.radians(ang)
    u = xx * math.cos(a) + yy * math.sin(a)
    v = -xx * math.sin(a) + yy * math.cos(a)
    warp_on_top = np.cos(2 * np.pi * u / per) * np.cos(2 * np.pi * v / per) > 0
    c_warp = np.array([0.16, 0.22, 0.52])
    c_weft = np.array([0.88, 0.82, 0.66])
    col = np.where(warp_on_top[..., None], c_warp, c_weft)
    return _lens_blur(np.clip(col * (0.35 + 0.75 * shade[..., None]), 0.0, 1.0))


def scene_halftone(n_px):
    """印刷の網点: 空色の地・赤い円・黄色の帯の絵柄を C・M・Y の 3 版(15°・75°・0°、周期 4.0 px)で網にかける
    (``printpath.halftone_screen``)。"""
    y, x = _grid(n_px)
    hs = y.shape[0]
    pix_um = 25.4                                        # シーンの標本 1 つを 1000 dpi とみなす
    lpi = 1000.0 / (4.0 * F)                             # 網の周期 = 4.0 センサ画素
    # 絵柄(印刷したい色): 上から下へ明るくなる空色の地、赤い円、黄色の帯。tone = 版ごとの紙の残り(1 = 紙)
    g = y / n_px
    want = np.stack([0.55 + 0.35 * g, 0.75 + 0.2 * g, 0.95 + 0.0 * g], axis=-1)
    disc = np.hypot(y - n_px * 0.5, x - n_px * 0.5) < n_px * 0.24
    want[disc] = (0.86, 0.18, 0.16)
    band = np.abs(y - n_px * 0.82) < n_px * 0.07
    want[band] = (0.98, 0.84, 0.12)
    t1, t2, t3 = want[..., 0], want[..., 1], want[..., 2]
    planes = []
    for tone, ang in ((t1, 15.0), (t2, 75.0), (t3, 0.0)):
        planes.append(printpath.halftone_screen(tone.reshape(hs, hs), lpi=lpi, angle_deg=ang, pixel_um=pix_um,
                                                sharpness=6.0))
    paper = np.array([0.95, 0.94, 0.90])
    rgb = np.stack([planes[0] * paper[0], planes[1] * paper[1], planes[2] * paper[2]], axis=-1)
    return _lens_blur(rgb)


def scene_chart(n_px):
    """解像チャート(ISO 12233 風、無彩色): 星形チャート・収束する線の楔・傾いたエッジ。"""
    y, x = _grid(n_px)
    g = np.full(y.shape, 0.85)
    cy, cx, R = n_px * 0.32, n_px * 0.32, n_px * 0.27
    r = np.hypot(y - cy, x - cx)
    th = np.arctan2(y - cy, x - cx)
    star = (np.cos(36 * th) > 0) & (r < R)
    g = np.where(star, 0.08, g)
    # 楔: 線の間隔が 3.0 → 1.1 px に縮む(縦線)
    wy0, wy1 = n_px * 0.66, n_px * 0.95
    t = np.clip((y - wy0) / (wy1 - wy0), 0, 1)
    per = 3.0 - 1.9 * t
    phase = (x - n_px * 0.06) / per
    wedge = (np.cos(2 * np.pi * phase) > 0) & (y > wy0) & (y < wy1) & (x > n_px * 0.06) & (x < n_px * 0.58)
    g = np.where(wedge, 0.08, g)
    # 傾いたエッジ(5°)
    a = math.radians(5.0)
    d = (x - n_px * 0.78) * math.cos(a) - (y - n_px * 0.3) * math.sin(a)
    sq = (y > n_px * 0.08) & (y < n_px * 0.55) & (x > n_px * 0.60)
    g = np.where(sq, 0.08 + 0.77 * _soft(-d), g)
    rgb = np.repeat(g[..., None], 3, axis=-1)
    return _lens_blur(rgb)


def grating(n_px, f0, amp=0.4, mean=0.5, f_number=None, fill_cells=True):
    """縦縞 mean + amp·cos(2π f0 x)(白黒)。升の平均で描く(升の境界に乗る開口では連続の縞と同じ積分になる)。"""
    hs = (n_px + 2 * MARGIN) * F
    xc = (np.arange(hs) + 0.5) / F
    row = mean + amp * np.cos(2 * np.pi * f0 * xc) * (np.sinc(f0 / F) if fill_cells else 1.0)
    if f_number is not None:
        psf = optics.airy_pattern(size=48 * F + 1, wavelength_um=LAM_UM, f_number=f_number, pixel_pitch_um=PITCH_UM / F)
        lsf = psf.sum(axis=0)
        lsf = lsf / lsf.sum()
        pad = lsf.size
        row = np.convolve(np.pad(row, pad, mode="wrap" if False else "reflect"), lsf, mode="same")[pad:-pad]
    return np.repeat(row[None, :], hs, axis=0)


# ─────────────────────────────── 道具 ───────────────────────────────
def truth_rgb(scene, fill=1.0):
    """理想センサ(各画素で 3 色、シフト 0)= 真値。"""
    return PS.pixel_shift_capture(scene, F, [[0.0, 0.0]], None, fill_factor=fill, margin=MARGIN)[0]


def single_demosaic(scene):
    raw = PS.pixel_shift_capture(scene, F, [[0.0, 0.0]], "RGGB", margin=MARGIN)[0]
    return gfx2d.raw_demosaic_bilinear(np.clip(raw, 0, 1), "RGGB"), raw


def four_shot(scene, shifts_actual=None, per_frame=False, nominal=None):
    nom = PS.pixel_shift_pattern("4shot") if nominal is None else nominal
    act = nom if shifts_actual is None else shifts_actual
    raw = PS.pixel_shift_capture(scene, F, act, "RGGB", margin=MARGIN, per_frame=per_frame)
    return raw, nom


def psnr(a, b, border=2):
    d = (a - b)[border:-border, border:-border]
    mse = float(np.mean(d ** 2))
    return float("inf") if mse == 0.0 else 10 * math.log10(1.0 / mse)


def db(v):
    return "∞(誤差 0)" if math.isinf(v) else "%.1f dB" % v


def spectrum_peak(img, scale):
    """行の平均の FFT の山(0 を除く): (周波数 [cyc/センサ画素], 振幅)。窓は Hann、振幅は窓の利得で割る。"""
    row = img[img.shape[0] // 4: 3 * img.shape[0] // 4].mean(axis=0)
    row = row - row.mean()
    w = np.hanning(row.size)
    spec = np.abs(np.fft.rfft(row * w)) * 2 / w.sum()
    f = np.fft.rfftfreq(row.size, d=1.0 / scale)
    k = int(np.argmax(spec[2:])) + 2
    # 3 点の放物線で山の位置と高さを詰める(Hann の主葉)
    a, b, c = spec[k - 1], spec[k], spec[k + 1] if k + 1 < spec.size else spec[k]
    den = a - 2 * b + c
    dk = 0.5 * (a - c) / den if den != 0 else 0.0
    peak = b - 0.25 * (a - c) * dk
    return float(f[k] + dk * (f[1] - f[0])), float(peak), f, spec


def fit_amplitude(img, f0, scale):
    """既知の周波数 f0 [cyc/センサ画素] の振幅を最小二乗で(行の平均、標本の位置 = 添字 / scale)。"""
    row = img[img.shape[0] // 4: 3 * img.shape[0] // 4].mean(axis=0)
    xpos = np.arange(row.size) / scale
    A = np.column_stack([np.ones_like(xpos), np.cos(2 * np.pi * f0 * xpos), np.sin(2 * np.pi * f0 * xpos)])
    coef, *_ = np.linalg.lstsq(A, row, rcond=None)
    return float(math.hypot(coef[1], coef[2]))


def zoom(img, k):
    return np.repeat(np.repeat(img, k, axis=0), k, axis=1)


def mosaic_view(raw, pattern="RGGB"):
    """生の Bayer を、画素ごとにそのフィルタの色で塗る(人が見るための絵)。"""
    idx = PS._cfa_index(pattern, raw.shape)
    out = np.zeros(raw.shape + (3,))
    for k in range(3):
        out[..., k] = np.where(idx == k, raw, 0.0)
    return np.clip(out, 0, 1)


# ─────────────────────────────── 0. 閉形式 ───────────────────────────────
def chapter_closed_form():
    print("\n0. 閉形式(実測の前に印字する)")
    s05 = float(np.sinc(0.5))
    b = PS.pixel_shift_resolution_budget(PITCH_UM, N_DEFAULT, LAM_UM, 1.0, 0.5)
    b_ap = PS.pixel_shift_resolution_budget(PITCH_UM, 1e-6, LAM_UM, 1.0, 0.5)       # レンズなし(Q → 0)
    print("   開口の MTF |sinc(f)|: f = 0.5 → %.4f(2/π)、f = 1 → 0。開口だけの MTF50 = %.4f cyc/px" % (s05, b_ap["mtf50_cyc_px"]))
    print("   1 枚のナイキスト 0.5、半画素シフト 1.0。1 枚で f₀ ∈ (0.5, 1) は 1 − f₀ に折り返る")
    print("   画素 %.2f µm・F %.1f・λ %.2f µm: Q = λN/p = %.3f(%s)、レンズの遮断 %.2f cyc/px、系の MTF50 %.4f・MTF10 %.4f cyc/px"
          % (PITCH_UM, N_DEFAULT, LAM_UM, b["Q"], b["regime"], b["lens_cutoff_cyc_px"], b["mtf50_cyc_px"], b["mtf10_cyc_px"]))
    print("   使える帯域(折り返しなし・系の MTF ≥ 0.1): 1 枚 %.3f → 半画素 %.3f cyc/px(%.2f 倍)"
          % (b["usable_band_single"], b["usable_band_shifted"], b["gain"]))
    NUMBERS.update({"mtf50_aperture": b_ap["mtf50_cyc_px"], "Q_default": b["Q"], "mtf50_system": b["mtf50_cyc_px"],
                    "band_gain": b["gain"]})
    gate("開口の MTF はナイキストで 2/π(%.6f)" % b["mtf_at_nyquist_single"]["aperture"],
         abs(b["mtf_at_nyquist_single"]["aperture"] - 2 / math.pi) < 1e-12)
    gate("開口だけの MTF50 = 0.6034 cyc/px(sinc(f) = 0.5 の根)", abs(b_ap["mtf50_cyc_px"] - 0.60335) < 1e-4,
         "%.5f" % b_ap["mtf50_cyc_px"])
    # 予算の回折の MTF を既存の optics.mtf_diffraction と突き合わせる(独立の実装)
    md = optics.mtf_diffraction(N_DEFAULT, LAM_UM, 64)
    f_cyc_px = md[:, 0] * PITCH_UM / 1000.0
    mine = PS._diffraction_mtf(f_cyc_px * b["Q"])
    gate("予算の回折 MTF は optics.mtf_diffraction と 1e-12 で一致(64 点)", float(np.max(np.abs(mine - md[:, 1]))) < 1e-12)
    gate("Q < 2 は画素律速、Q ≥ 2 はレンズ律速(F 2.8 → %s、F 16 → %s)"
         % (b["regime"], PS.pixel_shift_resolution_budget(PITCH_UM, 16.0)["regime"]),
         b["regime"] == "pixel_limited" and PS.pixel_shift_resolution_budget(PITCH_UM, 16.0)["regime"] == "lens_limited")
    return b


# ─────────────────────────────── 1. 1 画素シフト 4 枚 = 全色 ───────────────────────────────
SCENES = (("基板の配線", scene_pcb), ("織物", scene_weave), ("網点の印刷", scene_halftone), ("解像チャート", scene_chart))


def chapter_four_shot():
    print("\n1. 1 画素シフト 4 枚: 各画素で R・G・B を実測する(Bayer、静止・誤差 0・雑音なし)")
    rows, panels = [], []
    for name, mk in SCENES:
        sc = mk(NS)
        tr = truth_rgb(sc)
        one, _raw = single_demosaic(sc)
        raw4, nom = four_shot(sc)
        m4 = PS.pixel_shift_merge(raw4, nom, "RGGB")
        fc1 = PS.false_color_metric(one, reference=tr, border=2)
        fc4 = PS.false_color_metric(m4, reference=tr, border=2)
        p1, p4 = psnr(one, tr), psnr(m4, tr)
        rows.append((name, fc1, fc4, p1, p4))
        print("   %-8s 偽色(平均 / 99%%点): 1 枚 %.4f / %.4f → 4 枚 %.1e / %.1e、PSNR %s → %s"
              % (name, fc1["mean"], fc1["p99"], fc4["mean"], fc4["p99"], db(p1), db(p4)))
        panels.append((sc, tr, one, m4))
    worst4 = max(r[2]["max"] for r in rows)
    least1 = min(r[1]["mean"] for r in rows)
    NUMBERS.update({"fc4_max": worst4, "fc1_min_mean": least1})
    for name, fc1, _fc4, _p1, _p4 in rows:
        NUMBERS["fc1_mean_" + name] = fc1["mean"]
    gate("4 枚の偽色は 4 題材とも 1e-9 未満(定義上 0: 同じ開口・同じ点・誤差なし —— 異常に良いのではなく、そう作った)",
         worst4 < 1e-9, "最大 %.1e" % worst4)
    gate("1 枚 + 双線形デモザイクの偽色は 4 題材とも平均 0.005 以上(8 bit で 1 階調超)", least1 > 0.005, "最小 %.4f" % least1)
    gate("4 枚の PSNR は 4 題材とも 1 枚より 10 dB 以上高い", all(r[4] - r[3] > 10 for r in rows),
         ", ".join(db(r[4] - r[3]) for r in rows))
    return rows, panels


# ─────────────────────────────── 2. 半画素シフト ───────────────────────────────
def chapter_half_pixel():
    print("\n2. 半画素シフト(白黒、half4): 折り返しが消える。MTF は上がらない")
    nom = PS.pixel_shift_pattern("half4")
    f0s = (0.30, 0.45, 0.60, 0.70, 0.80, 0.90)
    res = []
    worst_amp = 0.0
    ok_pos = True
    for f0 in f0s:
        sc = grating(NS, f0)
        one = PS.pixel_shift_capture(sc, F, [[0.0, 0.0]], None, margin=MARGIN)[0]
        hr = PS.pixel_shift_merge(PS.pixel_shift_capture(sc, F, nom, None, margin=MARGIN), nom, None, scale=2)
        pk1 = spectrum_peak(one, 1)
        pk2 = spectrum_peak(hr, 2)
        alias = abs(f0 - round(f0))
        expect = 0.4 * abs(float(np.sinc(f0)))
        a2 = fit_amplitude(hr, f0, 2)
        a1 = fit_amplitude(one, alias, 1)
        worst_amp = max(worst_amp, abs(a2 / expect - 1), abs(a1 / expect - 1))
        df = 1.0 / one.shape[1]
        ok_pos &= abs(pk1[0] - alias) < df and abs(pk2[0] - f0) < df
        res.append((f0, alias, pk1[0], pk2[0], a1, a2, expect))
        print("   f₀ = %.2f: 1 枚の山 %.3f(閉形式 %.3f)、半画素の山 %.3f;振幅 1 枚 %.4f・半画素 %.4f・閉形式 0.4·sinc = %.4f"
              % (f0, pk1[0], alias, pk2[0], a1, a2, expect))
    NUMBERS["amp_worst_rel"] = worst_amp
    gate("FFT の山: 1 枚は 1 − f₀(折り返し)、半画素は f₀ に、6 本とも 1 bin 以内", ok_pos)
    gate("縞の振幅は 0.4·sinc(f₀) と 1 % 以内(1 枚の折り返しも同じ高さ —— 偽の縞は本物と同じ強さで写る)", worst_amp < 0.01,
         "最大 %.2e" % worst_amp)
    # drizzle(既存 op、面積保存の別実装)で独立に合わせる。★drizzle の shifts は「フレームの中身が基準からずれた向き」
    # なので、センサのシフト(画素 (r, c) がシーンの c + dc を見る = 中身は −dc ずれる)とは**符号が逆**。
    f0 = 0.7
    sc = grating(NS, f0)
    frames = PS.pixel_shift_capture(sc, F, nom, None, margin=MARGIN)
    hr = PS.pixel_shift_merge(frames, nom, None, scale=2)
    a_hr = fit_amplitude(hr[8:-8, 8:-8], f0, 2)
    dz = {}
    for sgn in (-1.0, 1.0):
        sci, wht = AS.drizzle_resample(list(frames), shifts=sgn * nom, scale=2.0, pixfrac=0.5)
        dz[sgn] = (sci / np.maximum(wht, 1e-12) * (0.5 * 2.0) ** 2)[8:-8, 8:-8]   # 階調は (pixfrac·scale)² 倍に縮む
    pk_ok, pk_bad = spectrum_peak(dz[-1.0], 2)[0], spectrum_peak(dz[1.0], 2)[0]
    a_dz = fit_amplitude(dz[-1.0], f0, 2)
    mean_dz = float(dz[-1.0].mean())
    NUMBERS.update({"drizzle_amp_ratio": a_dz / a_hr, "drizzle_wrong_sign_peak": pk_bad})
    print("   drizzle(pixfrac 0.5、shifts = −センサのシフト): 山 %.3f、振幅 merge の %.2f 倍(しずくと出力画素の箱のぶん下がる)、"
          "平均 %.4f;★符号を逆に渡すと山は %.3f(折り返しと同じ位置、例外は出ない)" % (pk_ok, a_dz / a_hr, mean_dz, pk_bad))
    df = 1.0 / dz[-1.0].shape[1] * 2
    gate("drizzle(astrostack、独立の実装)でも f₀ = 0.7 の山が f₀ に立ち、階調の平均は 0.5(振幅は merge 以下)",
         abs(pk_ok - f0) < df and abs(mean_dz - 0.5) < 0.01 and 0.2 < a_dz / a_hr <= 1.0 + 1e-9,
         "山 %.3f、振幅比 %.2f" % (pk_ok, a_dz / a_hr))
    gate("★drizzle に センサのシフトをそのまま渡すと、山は 1 − f₀ に立つ(符号の取り違えは折り返しに化けて見える)",
         abs(pk_bad - (1 - f0)) < df, "%.3f" % pk_bad)
    # 傾いたエッジの MTF50: 1 枚と半画素シフトで同じ(開口の sinc は動かない)
    sc = scene_chart(NS)[..., 1]
    one = PS.pixel_shift_capture(sc, F, [[0.0, 0.0]], None, margin=MARGIN)[0]
    hr = PS.pixel_shift_merge(PS.pixel_shift_capture(sc, F, nom, None, margin=MARGIN), nom, None, scale=2)
    y0, y1 = int(NS * 0.12), int(NS * 0.5)
    x0, x1 = int(NS * 0.78) - 2 - 10, int(NS * 0.78) - 2 + 12      # 黒い四角の左の縁(0.60 NS)を入れない
    e1 = ES.edge_spread(one, (y0, y1, x0, x1), oversample=4)
    s1 = ES.sfr_from_edge(e1, 8.0, correction="derivative+bin")
    e2 = ES.edge_spread(hr, (2 * y0, 2 * y1, 2 * x0, 2 * x1), oversample=4)
    s2 = ES.sfr_from_edge(e2, 16.0, correction="derivative+bin")
    m1 = ES.mtf50(s1)
    m2 = ES.mtf50(s2) * 2.0                              # 出力画素 = ½ センサ画素 → cyc/センサ画素
    closed = NUMBERS["mtf50_system"]
    NUMBERS.update({"mtf50_single": m1, "mtf50_half": m2})
    print("   傾いたエッジ(5°)の MTF50: 1 枚 %.4f、半画素 %.4f cyc/px、閉形式(sinc × 回折 F %.1f)%.4f"
          % (m1, m2, N_DEFAULT, closed))
    gate("MTF50 は 1 枚・半画素とも閉形式と 3 % 以内、互いに 3 % 以内(★シフトで MTF は上がらない)",
         abs(m1 / closed - 1) < 0.03 and abs(m2 / closed - 1) < 0.03 and abs(m2 / m1 - 1) < 0.03,
         "%.4f / %.4f / %.4f" % (m1, m2, closed))
    return res, (s1, s2), (one, hr)


def chapter_sixteen():
    print("\n2b. 16 枚(Bayer、半画素 4 位相 × 1 画素 4 枚): 色と帯域の両方")
    sc = scene_chart(NS)
    nom16 = PS.pixel_shift_pattern("16shot")
    raw16 = PS.pixel_shift_capture(sc, F, nom16, "RGGB", margin=MARGIN)
    m16 = PS.pixel_shift_merge(raw16, nom16, "RGGB", scale=2)
    t16 = np.zeros_like(m16)
    for a in (0, 1):
        for b in (0, 1):
            t16[a::2, b::2] = PS.pixel_shift_capture(sc, F, [[a / 2, b / 2]], None, margin=MARGIN)[0]
    err = float(np.abs(m16 - t16)[4:-4, 4:-4].max())
    fc = PS.false_color_metric(m16, reference=t16, border=4)
    gate("16 枚の合成は、半画素の格子で 3 色を撮った理想センサと内側で一致(1e-9)、偽色 %.1e" % fc["max"], err < 1e-9,
         "最大差 %.1e" % err)
    one, _ = single_demosaic(sc)
    return one, m16


# ─────────────────────────────── 3. レンズ律速と画素律速 ───────────────────────────────
def chapter_lens_vs_pixel():
    print("\n3. レンズ律速と画素律速の境目(画素 %.2f µm、f₀ = 0.7 cyc/px の縞、半画素シフト)" % PITCH_UM)
    f0 = 0.7
    nom = PS.pixel_shift_pattern("half4")
    fnums = (1.4, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0, 22.0) if not REDUCED else (1.4, 4.0, 8.0, 16.0)
    rows = []
    worst = 0.0
    for N in fnums:
        sc = grating(NS, f0, f_number=N)
        hr = PS.pixel_shift_merge(PS.pixel_shift_capture(sc, F, nom, None, margin=MARGIN), nom, None, scale=2)
        meas = fit_amplitude(hr, f0, 2) / 0.4
        b = PS.pixel_shift_resolution_budget(PITCH_UM, N, LAM_UM, 1.0, 0.5)
        closed = float(np.sinc(f0)) * float(PS._diffraction_mtf(f0 * b["Q"]))
        worst = max(worst, abs(meas - closed))
        rows.append((N, b["Q"], meas, closed, b["regime"], b["gain"]))
        print("   F %4.1f  Q = %.2f  縞の変調 実測 %.4f / 閉形式 %.4f  (%s、帯域の得 %.2f 倍)"
              % (N, b["Q"], meas, closed, b["regime"], b["gain"]))
    NUMBERS["lens_sweep_worst"] = worst
    gate("f₀ = 0.7 の変調は sinc(f₀)·MTF_diff(f₀Q) と全 F 値で 0.02 以内(Airy の LSF で独立にぼかした)", worst < 0.02,
         "最大差 %.4f" % worst)
    dead = [r for r in rows if r[1] > 1 / f0]
    gate("Q > 1/0.7 = 1.43 ではレンズが縞を消す(変調 < 0.02)—— シフトしても戻らない",
         all(r[2] < 0.02 for r in dead) and len(dead) >= 1, "%d 本" % len(dead))
    lens_lim = [r for r in rows if r[4] == "lens_limited"]
    gate("レンズ律速(Q ≥ 2)では半画素シフトの帯域の得は 1.0 倍", all(abs(r[5] - 1.0) < 1e-12 for r in lens_lim),
         ", ".join("F%.0f" % r[0] for r in lens_lim))
    # ★Q = 2 は「折り返しが出るか」の境目。見える解像の得(系の MTF ≥ 0.1 の帯域)が尽きるのはもっと手前:
    #   sinc(0.5)·MTF(0.5Q) = 0.1 の Q*。F 11(Q = 1.75)は画素律速の判定でも得は 1.0 倍。
    lo_q, hi_q = 0.5, 2.0
    for _ in range(60):
        mid = 0.5 * (lo_q + hi_q)
        g = PS.pixel_shift_resolution_budget(PITCH_UM, mid * PITCH_UM / LAM_UM, LAM_UM, 1.0, 0.5)["gain"]
        lo_q, hi_q = (mid, hi_q) if g > 1.0 + 1e-9 else (lo_q, mid)
    q_star = 0.5 * (lo_q + hi_q)
    closed_x = float(PS._diffraction_mtf(0.5 * q_star))   # 回折の MTF の引数 x = fQ(f = 0.5)
    NUMBERS["q_star"] = q_star
    print("   得が尽きる Q* = %.3f(F %.1f 相当): sinc(0.5)·MTF(0.5 Q*) = %.4f(= 0.1)"
          % (q_star, q_star * PITCH_UM / LAM_UM, float(np.sinc(0.5)) * float(PS._diffraction_mtf(0.5 * q_star))))
    gate("★Q = 2 は折り返しの境目で、解像の得はもっと手前の Q* = %.2f で尽きる(Q* < Q < 2 は「画素律速なのに得 1.0 倍」)"
         % q_star, 1.3 < q_star < 1.6 and abs(float(np.sinc(0.5)) * closed_x - 0.1) < 1e-6
         and all((r[5] > 1.0) == (r[1] < q_star) for r in rows))
    # 開口率 0.5(マイクロレンズなし)
    sc = grating(NS, 0.8)
    out = {}
    for fill in (1.0, 0.5):
        hr = PS.pixel_shift_merge(PS.pixel_shift_capture(sc, F, nom, None, fill_factor=fill, margin=MARGIN), nom, None, scale=2)
        out[fill] = fit_amplitude(hr, 0.8, 2) / 0.4
    c1, c5 = abs(float(np.sinc(0.8))), abs(float(np.sinc(0.4)))
    NUMBERS.update({"fill1_08": out[1.0], "fill05_08": out[0.5]})
    print("   開口率: f = 0.8 cyc/px の変調 fill 1.0 → %.4f(sinc 0.8 = %.4f)、fill 0.5 → %.4f(sinc 0.4 = %.4f)"
          % (out[1.0], c1, out[0.5], c5))
    gate("開口率 0.5 は開口の零点を 2 cyc/px に下げ、0.8 cyc/px の変調が %.1f 倍(閉形式どおり 1 %% 以内)" % (out[0.5] / out[1.0]),
         abs(out[1.0] / c1 - 1) < 0.01 and abs(out[0.5] / c5 - 1) < 0.01)
    return rows


# ─────────────────────────────── 4. シフトの誤差 ───────────────────────────────
def chapter_shift_error():
    print("\n4. シフトの誤差(圧電の位置決め・振動)")
    f0, amp, delta = 0.35, 0.4, 0.05
    sc = np.repeat(grating(NS, f0, amp=amp)[..., None], 3, axis=-1)
    nom = PS.pixel_shift_pattern("4shot")
    act = nom.copy()
    act[1, 1] += delta                                    # 2 枚目((0, 1))だけ dc が δ 外れる
    raw = PS.pixel_shift_capture(sc, F, act, "RGGB", margin=MARGIN)
    m = PS.pixel_shift_merge(raw, nom, "RGGB")
    tr = truth_rgb(sc)
    # RGGB で 2 枚目((0,1))は、R を (偶, 奇)、G を (偶, 偶)と(奇, 奇)、B を (奇, 偶)の画素に配る
    err_r = (m[..., 0] - tr[..., 0])[2:-2:2, 3:-2:2]
    meas = float(np.sqrt(np.mean(err_r ** 2)))
    pred = 2 * math.pi * f0 * amp * float(np.sinc(f0)) * delta / math.sqrt(2)
    NUMBERS.update({"shift_err_meas": meas, "shift_err_pred": pred})
    print("   1 枚だけ δ = %.2f px: その枚から来た R の誤差 RMS 実測 %.5f、閉形式 2πf·a·sinc(f)·δ/√2 = %.5f"
          % (delta, meas, pred))
    gate("1 枚の誤差 δ の色の誤差は閉形式と 5 % 以内(小さい δ の 1 次)", abs(meas / pred - 1) < 0.05, "%.3f" % (meas / pred))
    # 乱数の誤差 σ の掃引(基板)
    scp = scene_pcb(NS)
    trp = truth_rgb(scp)
    one, _ = single_demosaic(scp)
    fc_one = PS.false_color_metric(one, reference=trp, border=2)["mean"]
    sigmas = (0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.45)
    seeds = range(3 if REDUCED else 8)
    curve = []
    for s in sigmas:
        vals = []
        for sd in seeds:
            act = PS.pixel_shift_pattern("4shot", error_px=s, seed=sd)
            raw = PS.pixel_shift_capture(scp, F, act, "RGGB", margin=MARGIN)
            vals.append(PS.false_color_metric(PS.pixel_shift_merge(raw, nom, "RGGB"), reference=trp, border=2)["mean"])
        curve.append((s, float(np.mean(vals)), float(np.std(vals))))
        print("   σ = %.2f px: 4 枚の偽色 平均 %.4f ± %.4f(1 枚のデモザイク %.4f)" % (s, curve[-1][1], curve[-1][2], fc_one))
    xs = np.array([c[0] for c in curve])
    ys = np.array([c[1] for c in curve])
    above = np.nonzero(ys >= fc_one)[0]
    if above.size:
        i = int(above[0])
        be = float(xs[i - 1] + (fc_one - ys[i - 1]) * (xs[i] - xs[i - 1]) / (ys[i] - ys[i - 1]))
    else:
        be = float("inf")
    NUMBERS["break_even_sigma"] = be
    NUMBERS["fc4_at_0.1"] = float(ys[list(xs).index(0.1)])
    print("   4 枚が 1 枚のデモザイクに追いつく誤差: σ ≈ %s px" % ("%.3f" % be if math.isfinite(be) else "掃引の外(> 0.45)"))
    gate("偽色は誤差 σ とともに単調に増える(平均)", bool(np.all(np.diff(ys) > 0)))
    gate("圧電の典型 σ = 0.1 px でも 4 枚の偽色は 1 枚のデモザイクより少ない", NUMBERS["fc4_at_0.1"] < fc_one,
         "%.4f < %.4f" % (NUMBERS["fc4_at_0.1"], fc_one))
    return curve, fc_one, be


# ─────────────────────────────── 5. 動く被写体 ───────────────────────────────
def chapter_motion():
    print("\n5. 動く被写体(搬送中のワーク: チップ部品が v px/枚 で右へ)")
    rng = np.random.default_rng(5)
    base = scene_pcb(NS, seed=3)
    hs = base.shape[0]
    y, x = _grid(NS)
    cy, cx, hh, hw = NS * 0.5, NS * 0.42, NS * 0.16, NS * 0.2

    def chip(dx):
        box = (np.abs(y - cy) < hh) & (np.abs(x - (cx + dx)) < hw)
        body = np.array([0.12, 0.12, 0.13])
        img = base.copy()
        img[box] = body
        # 端子(銀の縞、間隔 3.2 px)
        leg = (np.abs(y - cy) < hh + 2.0) & (np.abs(y - cy) > hh) & (np.cos(2 * np.pi * (x - dx) / 3.2) > 0.0) \
            & (np.abs(x - (cx + dx)) < hw - 1)
        img[leg] = np.array([0.82, 0.83, 0.85])
        marks = box & (np.abs(((x - dx) % 2.4) - 1.2) < 0.35) & (np.abs(y - cy) < hh * 0.3)
        img[marks] = np.array([0.75, 0.75, 0.72])
        return _lens_blur(img)

    def fc_in(img, tr, m):
        c = (img - tr) @ PS._CBCR.T
        return float(np.sqrt((c ** 2).sum(-1))[m].mean())

    def err_in(img, tr, m, q=None):
        e = np.sqrt(((img - tr) ** 2).sum(-1))[m]
        return float(np.sqrt(np.mean(e ** 2))) if q is None else float(np.percentile(e, q))

    nom = PS.pixel_shift_pattern("4shot")
    sig = 0.004
    speeds = (0.1, 0.25, 0.5, 1.0, 2.0) if not REDUCED else (0.25, 1.0, 2.0)
    table = []
    keep = None
    for v in speeds:
        scenes = np.stack([chip(v * i) for i in range(4)])
        raw = PS.pixel_shift_capture(scenes, F, nom, "RGGB", margin=MARGIN, per_frame=True)
        raw = raw + rng.normal(0.0, sig, raw.shape)
        tr = truth_rgb(scenes[0])
        naive = PS.pixel_shift_merge(raw, nom, "RGGB")
        fixed = PS.pixel_shift_merge(raw, nom, "RGGB", motion_threshold=4.0)
        mask = PS.pixel_shift_motion_mask(raw, nom, "RGGB", threshold=4.0)
        one = gfx2d.raw_demosaic_bilinear(np.clip(raw[0], 0, 1), "RGGB")
        # 動いた所 = 4 枚の間で真値が変わった画素(物体の縁と端子)
        moved = np.zeros(tr.shape[:2], bool)
        for i in range(1, 4):
            moved |= np.abs(truth_rgb(scenes[i]) - tr).max(axis=-1) > 0.02
        moved_d = ndi.binary_dilation(moved, iterations=1)
        static = ~ndi.binary_dilation(moved, iterations=3)
        static[:3], static[-3:], static[:, :3], static[:, -3:] = False, False, False, False
        r = {k: (err_in(im, tr, moved_d), fc_in(im, tr, static), err_in(im, tr, moved_d, 99), fc_in(im, tr, moved_d))
             for k, im in (("one", one), ("naive", naive), ("fixed", fixed))}
        det = float(mask.astype(bool)[moved].mean())
        fp = float(mask.astype(bool)[static].mean())
        table.append((v, r, det, fp))
        print("   %.2f px/枚: 動いた所の RGB 誤差 RMS(99 %%点)1 枚 %.3f(%.3f)・4 枚 %.3f(%.3f)・差し戻し %.3f(%.3f);"
              "静止部の偽色 4 枚 %.4f・差し戻し %.4f;検出 %.0f %%・誤検出 %.2f %%"
              % (v, r["one"][0], r["one"][2], r["naive"][0], r["naive"][2], r["fixed"][0], r["fixed"][2],
                 r["naive"][1], r["fixed"][1], 100 * det, 100 * fp))
        if v == 2.0:
            keep = (scenes, raw, tr, naive, fixed, mask, one)
    by = {t[0]: t for t in table}
    slow, mid, fast = by[0.25], by[1.0], by[2.0]
    NUMBERS.update({"motion_err_naive_2": fast[1]["naive"][0], "motion_err_fixed_2": fast[1]["fixed"][0],
                    "motion_err_naive_025": slow[1]["naive"][0], "motion_err_fixed_025": slow[1]["fixed"][0],
                    "motion_err_one_025": slow[1]["one"][0], "motion_det_2": fast[2],
                    "motion_fp_max": max(t[3] for t in table)})
    lo = [t for t in table if t[0] <= 0.5]
    gate("4 枚の合成の誤差(動いた所)は 0.5 px/枚 までは速さとともに増え、その先は頭打ち(ずれが端子の幅を超える)",
         all(b_[1]["naive"][0] > a_[1]["naive"][0] for a_, b_ in zip(lo, lo[1:]))
         and min(t[1]["naive"][0] for t in table if t[0] >= 0.5) > slow[1]["naive"][0],
         " → ".join("%.3f" % t[1]["naive"][0] for t in table))
    gate("★分かれ目: 0.25 px/枚 では 4 枚の破綻のほうが 1 枚のデモザイクより小さく、1 px/枚 以上では逆転する",
         slow[1]["naive"][0] < slow[1]["one"][0] and all(t[1]["naive"][0] > t[1]["one"][0] for t in table if t[0] >= 1.0),
         "0.25: %.3f < %.3f、1.0: %.3f > %.3f" % (slow[1]["naive"][0], slow[1]["one"][0], mid[1]["naive"][0], mid[1]["one"][0]))
    gate("1・2 px/枚 では差し戻しで動いた所の誤差が下がり、天井(1 枚のデモザイクの誤差)の 2 % 以内に届く",
         all(t[1]["fixed"][0] < t[1]["naive"][0] and t[1]["fixed"][0] <= 1.02 * t[1]["one"][0] for t in (mid, fast)),
         "RMS %.3f → %.3f(1 枚 %.3f)、%.3f → %.3f(1 枚 %.3f)" % (mid[1]["naive"][0], mid[1]["fixed"][0], mid[1]["one"][0],
                                                            fast[1]["naive"][0], fast[1]["fixed"][0], fast[1]["one"][0]))
    gate("★0.25 px/枚 では差し戻しは損(戻し先の 1 枚のデモザイクが細い端子で 4 枚の破綻より大きく誤る)",
         slow[1]["fixed"][0] > slow[1]["naive"][0], "%.3f vs %.3f" % (slow[1]["fixed"][0], slow[1]["naive"][0]))
    gate("止まっている所は 4 枚の画質のまま(誤検出 2 % 未満、静止部の偽色は 1 枚より小さい、全速度)",
         all(t[3] < 0.02 and t[1]["fixed"][1] < t[1]["one"][1] for t in table),
         "誤検出 最大 %.2f %%" % (100 * NUMBERS["motion_fp_max"]))
    scenes, raw, tr, naive, fixed, mask, one = keep
    return scenes, raw, tr, naive, fixed, mask, one


# ─────────────────────────────── 6. 雑音 √N ───────────────────────────────
def chapter_noise():
    print("\n6. 雑音は同じ点の標本数で √n(4 枚を c 周)")
    rng = np.random.default_rng(6)
    sig = 0.02
    flat = np.full(((NS + 2 * MARGIN) * F,) * 2 + (3,), 0.5)
    rows = []
    worst = 0.0
    for c in (1, 2, 4, 8):
        nom = PS.pixel_shift_pattern("4shot", cycles=c)
        raw = PS.pixel_shift_capture(flat, F, nom, "RGGB", margin=MARGIN)
        raw = raw + rng.normal(0.0, sig, raw.shape)
        m = PS.pixel_shift_merge(raw, nom, "RGGB")[2:-2, 2:-2]
        sR, sG, sB = (float(m[..., k].std()) for k in range(3))
        pR, pG = sig / math.sqrt(c), sig / math.sqrt(2 * c)
        worst = max(worst, abs(sR / pR - 1), abs(sB / pR - 1), abs(sG / pG - 1))
        rows.append((4 * c, sR, sG, sB, pR, pG))
        print("   %2d 枚: σ_R %.5f・σ_G %.5f・σ_B %.5f(閉形式 R・B %.5f、G %.5f)" % (4 * c, sR, sG, sB, pR, pG))
    NUMBERS["noise_worst_rel"] = worst
    gate("R・B は σ/√c、G は σ/√(2c)(各画素の G は 2 枚から)と 5 % 以内", worst < 0.05, "最大 %.3f" % worst)
    one, _ = single_demosaic(np.full_like(flat, 0.5))
    # 動く被写体では枚数を増やすほど動いた所の誤差が増える(縞の上を 0.1 px/枚 で動く)
    f0 = 0.3
    out = []
    for c in (1, 2, 4):
        nom = PS.pixel_shift_pattern("4shot", cycles=c)
        scenes = np.stack([np.repeat(np.roll(grating(NS, f0), int(round(0.1 * F * i)), axis=1)[..., None], 3, -1)
                           for i in range(4 * c)])
        raw = PS.pixel_shift_capture(scenes, F, nom, "RGGB", margin=MARGIN, per_frame=True)
        m = PS.pixel_shift_merge(raw, nom, "RGGB")
        tr = truth_rgb(scenes[0])
        out.append((4 * c, float(np.sqrt(np.mean((m - tr)[4:-4, 4:-4] ** 2)))))
        print("   動く縞(0.1 px/枚)を %2d 枚で合わせた誤差 RMS %.4f" % (4 * c, out[-1][1]))
    gate("動く被写体では枚数を増やすほど誤差が増える(√N の得が裏返る)", all(b[1] > a[1] for a, b in zip(out, out[1:])),
         " → ".join("%.4f" % o[1] for o in out))
    return rows, out


# ─────────────────────────────── 図 ───────────────────────────────
def make_figures(cf, four, half, sixteen, lens_rows, shift, motion, noise):
    rows, panels = four
    k, w = 5, 44
    centres = ((0.50, 0.52), (0.5, 0.5), (0.30, 0.42), (0.30, 0.30))   # 題材ごとの切り出しの中心(行, 列)/ NS
    grid_p, caps = [], []
    for (name, fc1, fc4, _p1, _p4), (_sc, tr, one, m4), (fy, fx) in zip(rows, panels, centres):
        cut = slice(int(NS * fy) - w // 2, int(NS * fy) + w // 2)
        cut2 = slice(int(NS * fx) - w // 2, int(NS * fx) + w // 2)
        for im, lab in ((tr, "%s: 真値" % name), (one, "1枚+デモザイク 偽色%.3f" % fc1["mean"]),
                        (m4, "4枚シフト 偽色%.0e" % fc4["mean"])):
            grid_p.append(zoom(np.clip(im[cut, cut2], 0, 1), k))
            caps.append(lab)
    figs.save_grid("four_shot_false_color", grid_p, captions=caps, ncols=3,
                   title="1 画素シフト 4 枚: 各画素で R・G・B を実測 → 偽色が消える",
                   caption="基板の配線・織物・網点・解像チャート(上から)。左 = 3 色を各画素で取る理想センサ、中 = Bayer 1 枚 + "
                           "双線形デモザイク、右 = 1 画素シフト 4 枚。44 × 44 画素を最近傍で 5 倍。静止・誤差 0 では 4 枚の偽色は"
                           "定義上 0(4・5 章が壊れる条件)。")
    # 1 枚の絵で見せる: 星形チャートの左半分 = 1 枚 + デモザイク、右半分 = 4 枚(ViEW2026 のサムネイルの元)
    _n, _f1, _f4, _a, _b = rows[3]
    _sc, _tr, one_s, m4_s = panels[3]
    c0 = int(NS * 0.30)
    win = slice(c0 - 24, c0 + 24)
    left = np.clip(one_s[win, win], 0, 1)[:, :24]
    right = np.clip(m4_s[win, win], 0, 1)[:, 24:]
    split = zoom(np.concatenate([left, right], axis=1), 6)
    split[:, 24 * 6 - 1:24 * 6 + 1] = 1.0
    figs.save("star_split", split,
              caption="解像チャートの 星形チャート(48 × 48 画素を 6 倍)。左半分 = Bayer 1 枚 + 双線形デモザイク(色のモアレ)、"
                      "右半分 = 1 画素シフト 4 枚(偽色 0)。")
    figs.save_table("false_color_table", ["題材", "偽色 1 枚(平均)", "偽色 1 枚(99 %)", "偽色 4 枚", "PSNR 1 枚", "PSNR 4 枚"],
                    [[r[0], "%.4f" % r[1]["mean"], "%.4f" % r[1]["p99"], "%.1e" % r[2]["mean"], db(r[3]), db(r[4])] for r in rows],
                    title="偽色(真値との Cb・Cr の差の大きさ)と PSNR",
                    caption="偽色は 0〜1 の階調の色差(0.004 ≈ 8 bit の 1 階調)。")
    res, (s1, s2), (one_e, hr_e) = half
    sc = grating(NS, 0.7)
    one = PS.pixel_shift_capture(sc, F, [[0.0, 0.0]], None, margin=MARGIN)[0]
    nom = PS.pixel_shift_pattern("half4")
    hr = PS.pixel_shift_merge(PS.pixel_shift_capture(sc, F, nom, None, margin=MARGIN), nom, None, scale=2)
    _p1, _a1, f1, sp1 = spectrum_peak(one, 1)
    _p2, _a2, f2, sp2 = spectrum_peak(hr, 2)
    figs.save_plot("grating_spectrum", [("1 枚", f1, sp1), ("半画素シフト 4 枚", f2, sp2),
                                        ("真の f₀ = 0.7", np.array([0.7, 0.7]), np.array([0.0, 0.2])),
                                        ("折り返し 0.3", np.array([0.3, 0.3]), np.array([0.0, 0.2]))],
                   xlabel="空間周波数 [cyc/センサ画素]", ylabel="振幅", styles=[None, None, "dashed", "dotted"],
                   colors=["wrong", "right", "reference", "neutral"], xlim=(0.0, 1.0),
                   title="0.7 cyc/px の縞: 1 枚は 0.3 に、半画素シフトは 0.7 に山が立つ",
                   caption="1 枚(ナイキスト 0.5)では縞が 1 − f₀ = 0.3 に折り返り、本物と同じ高さの偽の縞(モアレ)になる。"
                           "半画素シフトでナイキストが 1.0 に上がり、山は正しい位置へ。高さは 0.4·sinc(0.7) = %.3f。"
                           % (0.4 * float(np.sinc(0.7))))
    figs.save_grid("grating_crops", [zoom(one[20:44, 20:44], 8), zoom(hr[40:88, 40:88], 4)],
                   captions=["1枚: 0.7cyc/pxが0.3に化ける", "半画素4枚: 正しい細かさ"], ncols=2, gray=True,
                   title="同じ 24 × 24 センサ画素(最近傍で拡大)",
                   caption="左は画素 1 つ = 8 × 8、右は出力画素 1 つ(= ½ センサ画素)= 4 × 4 で表示。左の太い縞は存在しない。")
    fz = np.linspace(0, 1.0, 201)
    ap = np.abs(np.sinc(fz))
    ln = PS._diffraction_mtf(fz * cf["Q"])
    s2 = s2[s2[:, 0] * 2.0 <= 1.0 + 1e-12]               # 出力画素の周波数を cyc/センサ画素へ(1 まで)
    figs.save_plot("edge_mtf", [("1 枚(傾いたエッジ)", s1[:, 0], s1[:, 1]), ("半画素シフト", s2[:, 0] * 2.0, s2[:, 1]),
                                ("閉形式 sinc × 回折", fz, ap * ln), ("ナイキスト 0.5", np.array([0.5, 0.5]), np.array([0, 1]))],
                   xlabel="空間周波数 [cyc/センサ画素]", ylabel="MTF", styles=[None, None, "dashed", "dotted"],
                   colors=["wrong", "emphasis", "reference", "neutral"], xlim=(0, 1.0), ylim=(0, 1.05),
                   title="MTF50: 1 枚 %.3f・半画素 %.3f・閉形式 %.3f(MTF は上がらない)"
                         % (NUMBERS["mtf50_single"], NUMBERS["mtf50_half"], NUMBERS["mtf50_system"]),
                   caption="傾いたエッジの手順(ISO 12233)は 1 枚でも画素より細かく ESF を作るので、開口の sinc と"
                           "レンズの MTF の積をそのまま測る。半画素シフトが変えるのは折り返しで、MTF ではない。")
    one_c, m16 = sixteen
    cy = slice(int(NS * 0.66), int(NS * 0.95))
    cx = slice(int(NS * 0.06), int(NS * 0.06) + 40)
    cy2 = slice(2 * cy.start, 2 * cy.stop)
    cx2 = slice(2 * cx.start, 2 * cx.stop)
    figs.save_grid("sixteen_shot_wedge", [zoom(np.clip(one_c[cy, cx], 0, 1), 6), zoom(np.clip(m16[cy2, cx2], 0, 1), 3)],
                   captions=["Bayer 1枚+デモザイク", "16枚シフト(半画素×全色)"], ncols=2,
                   title="線の楔(周期 3.0 → 1.1 px、上 → 下)",
                   caption="16 枚 = 半画素 4 位相 × 1 画素 4 枚。半画素の格子の各点に R・G・G・B が揃い、1 枚では色の付いた"
                           "モアレになる 1.1〜1.5 px 周期の線が、無彩色の正しい細さで出る。")
    Q = np.array([r[1] for r in lens_rows])
    qq = np.linspace(0.05, max(Q.max(), 3.6), 200)
    figs.save_plot("lens_vs_pixel", [("実測(半画素シフト)", Q, np.array([r[2] for r in lens_rows])),
                                     ("閉形式 sinc(0.7)·MTF(0.7Q)", qq, float(np.sinc(0.7)) * PS._diffraction_mtf(0.7 * qq)),
                                     ("Q = 2(律速の境目)", np.array([2.0, 2.0]), np.array([0.0, 0.45]))],
                   xlabel="Q = λN/p", ylabel="0.7 cyc/px の縞の変調", kinds=["scatter", "line", "line"],
                   styles=[None, "dashed", "dotted"], colors=["emphasis", "reference", "neutral"], ylim=(0, 0.45),
                   title="レンズが先に落ちていれば、ピクセルシフトしても解像は戻らない",
                   caption="画素 3.45 µm、λ 0.55 µm で F 1.4〜22。Q > 1.43 で回折の MTF が 0.7 cyc/px で 0 になり、半画素シフトの"
                           "像にも縞は残らない。Q ≥ 2 では 0.5 cyc/px より上に信号が無く、シフトの得は 1.0 倍。")
    curve, fc_one, be = shift
    xs = np.array([c[0] for c in curve])
    figs.save_plot("shift_error", [("4 枚(誤差 σ、平均)", xs, np.array([c[1] for c in curve])),
                                   ("1 枚 + デモザイク", xs, np.full(xs.size, fc_one))],
                   xlabel="シフトの誤差 σ [px] (各枚・各軸)", ylabel="偽色(平均)", kinds=["line", "line"],
                   styles=[None, "dashed"], colors=["emphasis", "wrong"],
                   title=("圧電の誤差: σ ≈ %.2f px で 1 枚のデモザイクに追いつく" % be) if math.isfinite(be)
                   else "圧電の誤差: σ = 0.45 px でも 1 枚のデモザイクより偽色が少ない",
                   caption="基板の配線、乱数の誤差 %d 通りの平均。誤差が無ければ 0、σ が大きいと細い配線の縁に色が付く。"
                           % (3 if REDUCED else 8))
    scenes, raw, tr, naive, fixed, mask, one = motion
    ry = slice(int(NS * 0.30), int(NS * 0.30) + 44)
    rx = slice(int(NS * 0.42 - NS * 0.2) - 10, int(NS * 0.42 - NS * 0.2) + 34)
    errn = np.sqrt(((naive - tr) ** 2).sum(-1))
    figs.save_grid("motion_fallback", [zoom(np.clip(a[ry, rx], 0, 1), 4) for a in (tr, one, naive, fixed)]
                   + [zoom(np.repeat(mask[ry, rx, None], 3, -1), 4),
                      zoom(np.repeat(np.clip(errn[ry, rx] / 0.5, 0, 1)[..., None], 3, -1), 4)],
                   captions=["真値(1枚目の位置)", "1枚+デモザイク", "4枚(差し戻しなし)", "4枚+動き検出",
                             "動いたと判定", "4枚の誤差(白=0.5)"], ncols=3,
                   title="搬送中のチップ(2 px/枚): 櫛と色の縁 → 差し戻し",
                   caption="動き検出は同じ点の 2 つの G の食い違い(4σ)。動いた所だけ 1 枚目のデモザイクに戻すので、"
                           "そこはピクセルシフトしなかった画質になるが、櫛と色の縁は消える。")
    nrows, nmov = noise
    n = np.array([r[0] for r in nrows], float)
    figs.save_plot("noise_sqrt_n", [("σ_R 実測", n, np.array([r[1] for r in nrows])), ("σ_G 実測", n, np.array([r[2] for r in nrows])),
                                    ("σ/√(N/4)", n, np.array([r[4] for r in nrows])), ("σ/√(N/2)", n, np.array([r[5] for r in nrows]))],
                   xlabel="枚数 N", ylabel="雑音 σ", kinds=["scatter", "scatter", "line", "line"],
                   styles=[None, None, "dashed", "dashed"], colors=["wrong", "right", "wrong", "right"],
                   title="雑音は同じ点の標本数で √n(R・B は N/4、G は N/2 個)",
                   caption="4 枚のピクセルシフトは雑音を下げるためのものではない(R・B は 1 枚と同じ)。下げるには周を重ねるが、"
                           "動く被写体では枚数とともに誤差が増える(%s)。" % " → ".join("%.3f" % o[1] for o in nmov))
    # GIF: 4 枚の撮像(センサが動き、各画素の色が入れ替わる)→ 合わせた像
    import fullseye as fs
    sc = panels[0][0]
    nom = PS.pixel_shift_pattern("4shot")
    raw4 = PS.pixel_shift_capture(sc, F, nom, "RGGB", margin=MARGIN)
    w, z = 24, 10
    gy = slice(int(NS * 0.40) - w // 2, int(NS * 0.40) + w // 2)      # 水平の配線の束の端と 45° の束が入る所
    gx = slice(int(NS * 0.56) - w // 2, int(NS * 0.56) + w // 2)
    frames = []
    acc = np.zeros((w, w, 3))
    have = np.zeros((w, w, 3), bool)
    idx = PS._cfa_index("RGGB", raw4.shape[1:])
    names = ("R", "G", "B")
    for i in range(4):
        dr, dc = int(nom[i, 0]), int(nom[i, 1])
        # i 枚目の画素 (r, c) はシーンの (r + dr, c + dc) を見る → 合わせた格子の位置へ置く。左の絵も同じだけずらして、
        # センサ(色フィルタの並び)がシーンの上を動く様子として見せる。
        mv = np.roll(np.roll(mosaic_view(np.clip(raw4[i] * 1.4, 0, 1)), dr, 0), dc, 1)
        for kch in range(3):
            plane = np.full(raw4.shape[1:], np.nan)
            plane[idx == kch] = raw4[i][idx == kch]
            plane = np.roll(np.roll(plane, dr, 0), dc, 1)[gy, gx]
            ok = np.isfinite(plane)
            acc[..., kch][ok] = plane[ok]
            have[..., kch] |= ok
        full = float(have.all(axis=-1).mean())
        left = zoom(np.clip(mv[gy, gx], 0, 1), z)
        right = zoom(np.clip(np.where(have, acc, 0.0), 0, 1), z)
        fig = fs.annotate_figure_grid([left, right], ncols=2, letters=False,
                                      captions=["%d 枚目: センサを (%d, %d) 画素" % (i + 1, dr, dc),
                                                "3 色が揃った画素 %.0f %%" % (100 * full)],
                                      title="1 画素シフト 4 枚(基板の配線、%d × %d 画素)" % (w, w))
        frames += [np.asarray(fig)] * 2
    final = zoom(np.clip(panels[0][3][gy, gx], 0, 1), z)
    one_v = zoom(np.clip(panels[0][2][gy, gx], 0, 1), z)
    fig = fs.annotate_figure_grid([one_v, final], ncols=2, letters=False,
                                  captions=["1 枚 + デモザイク(偽色)", "4 枚の合成(偽色 0)"],
                                  title="1 画素シフト 4 枚(基板の配線、%d × %d 画素)" % (w, w))
    frames += [np.asarray(fig)] * 4
    figs.save_gif("four_shot_capture", frames, fps=1.5,
                  caption="左 = その枚の Bayer の生の値(画素ごとにフィルタの色で表示、センサの位置へずらして描く)、右 = 合わせた"
                          "格子に R・G・B が揃っていく様子。最後は 1 枚のデモザイクと 4 枚の合成(%d × %d 画素を %d 倍)。" % (w, w, z))

def main():
    t0 = time.time()
    print("PoC ピクセルシフト撮像(予算 %s、センサ %d × %d 画素、1 画素 = %d × %d 標本)" % ("reduced" if REDUCED else "full", NS, NS, F, F))
    cf = chapter_closed_form()
    four = chapter_four_shot()
    half = chapter_half_pixel()
    sixteen = chapter_sixteen()
    lens_rows = chapter_lens_vs_pixel()
    shift = chapter_shift_error()
    motion = chapter_motion()
    noise = chapter_noise()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(cf, four, half, sixteen, lens_rows, shift, motion, noise)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()

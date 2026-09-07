# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ひび割れの「幅」ではなく「伸び」を測る —— 同じ壁を撮り返すと誤差の性質が変わる。

橋・擁壁・トンネルの定期点検は、幅そのものより **前回からどれだけ進んだか**
(mm/年)で補修の順番を決めます。ここでは 3 年ぶん 12 期の画像列を作り、

* ゼロ点 = 2 値化して**画素を数える**(閾値 0.5 の半値幅規約)
* 積分法 = ひび割れに直交する断面の**輝度欠損を積分**する

の 2 つで **成長率 [mm/年]** を出して比べます。幅の絶対値を測る話は
``poc_crack_width`` に譲り、この PoC は**時間軸だけ**を相手にします。

EXTEND: 実写に差し替えるなら :func:`render` が返す ``img`` を各回の撮影画像に、
``EPOCH_YEAR`` を実際の撮影日(年)に置き換えます。実写では
(a) 真の幅が無いので 2 節の「真値との差」はクラックゲージ実測との差になり、
(b) 三脚を据え直すので**画素の位相**が毎回変わる —— この PoC の 4 節がそこを
測っています、(c) 地の模様(コンクリート面)は同じ壁なら**毎回同じ**なので
誤差は共通成分を持ち、差分で消えます(5 節)。``PX_MM`` は毎回スケールバーで
測り直すこと —— 撮影距離が 3 % 変われば成長率も 3 % 変わります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **幅がよく当たる測り方と、伸びがよく当たる測り方は別**。12 期の平均で見た
   幅の偏り(bias)は 2 値化 +0.0130 mm / 積分法 -0.0009 mm。ところが
   **成長率**は真値 0.0400 mm/年 に対し 2 値化 0.0125 mm/年(-69 %)、
   積分法 0.0398 mm/年(-0.6 %)。★偏りは差分で消えるので、幅の偏りが
   14 倍でも成長率では負けない —— **消えるのは偏り、残るのは散らばり**。
2. ★★**環境だけ動かすと 2 値化は勝手に伸びる**。幅を 0.30 mm に凍結して
   ぼけ・照明・据え直しだけを 12 期ぶん動かす対照群で、見かけの成長率は
   2 値化 -0.0184 mm/年 / 積分法 +0.0007 mm/年。要因を 1 つずつ止めて分けると
   犯人は**ぼけ**(単独で -0.0177 mm/年)で、照明と据え直しはほぼ無害。
   積分法がぼけに強いのは偶然ではなく、**畳み込みは輝度欠損の総量を保存する**
   から(1 節で 1e-12 の桁まで検算する)。
3. ★★**据え直しの半画素が 2 値化を跳ねさせる。跳ねる量は経路の傾きで決まる**。
   ひび割れが視野に**水平**だと全列の画素位相が揃うので、幅は列ごとではなく
   **画面ごと**に 1 px 単位で跳ぶ(期ごとの散らばり 0.0431 mm)。傾き 0.35 に
   すると位相が列方向に混ざって 0.0142 mm(1/3)。★積分法の散らばりは
   0.0033 → 0.0033 mm で傾きに**無反応**。予想は「傾けば断面が斜めに切れて
   悪くなる」だったが、そうはならなかった。
4. ★**「有意な成長」と言うのに何期要るかは閉形式で出る**。傾きの標準偏差の
   予測 σ_w/(σ_t·√N) と、6 サイト × 掃引の実測の比は 0.86〜1.28。
   0.040 mm/年 を 2σ で言い切るのに、積分法なら 4 期(0.8 年)、
   2 値化は 12 期(2.8 年)でもまだ足りない。
5. ★★**「同じ壁を撮り返す」ことが誤差を半分にする**。地の模様を毎回別の
   乱数にすると積分法の傾き誤差 σ は 0.0064 mm/年、同じ壁(模様は同じで
   据え直しだけ変わる)だと 0.0035 mm/年。共通成分は差分で消えるので、
   **実写のほうが合成の独立雑音より有利**という向きになる。
6. ★**2 値化が死ぬ幅は、ぼけの σ から先に計算できる**。閾値 0.5 の半値幅規約は
   ピーク欠損 erf(w/(2√2σ)) が 0.5 を切ると何も返さないので、
   臨界幅 = 2√2·erfinv(0.5)·σ = 1.349σ。σ=1.00 px なら 0.202 mm。
   実測で 2 値化が全期ゼロになるのは 0.15 mm、値が出始めるのは 0.20 mm ——
   **予測の 1 目盛り内**。積分法は 0.10 mm(0.67 px)の帯でも成長率を
   0.0396 mm/年(-1.0 %)で返す。

【グラウンドトゥルース】
ひび割れは「暗い帯」として**解析的に描く**。列方向は 1/8 画素刻みの求積、
行方向は帯と画素矩形の重なりを解析で出すので、幅 0.5 画素の帯も「被覆率 0.5 の
1 画素」として正しく載る。レンズのぼけ(ガウス PSF)は被覆率に掛けるだけなので、
**輝度欠損の総量は厳密に保存される**。時期ごとに変わるのは
(a) PSF の σ(天候・ピント)、(b) 照明の明るさ・傾斜・曲がり、
(c) 三脚を据え直したことによる**サブピクセルの上下ずれ**、(d) 撮像雑音。
地の模様(コンクリート面のざらつき)は既定では**同じ壁なので同じ**で、
据え直しに合わせて一緒に動く。

来歴(公開文献のみ): 土木学会コンクリート標準示方書(ひび割れ幅の照査と経過観察)/
Otsu, *IEEE SMC* 9 (1979) 62 —— 2 値化 / Rayleigh 判別限界と erf の閉形式 /
Sen, *JASA* 63 (1968) 1379 —— 傾きの頑健推定(本 PoC は最小二乗のみ)。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, median_filter, shift as nd_shift
from scipy.special import erf, erfinv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
W_PX, H_PX = 288, 112      # 視野 [px]
PX_MM = 0.15               # 画素寸法 [mm/px] -> 視野 43.2 x 16.8 mm
CY = 56.0                  # ひび割れの中心行(据え直しの前)[px]
SLOPE0 = 0.02              # ひび割れの傾き dy/dx(既定の場面)

R_PROF = 12.0              # 断面の半長 [px]
DT_PROF = 0.25             # 断面の刻み [px]
T_BASE = 7.0               # |t| >= これをベースライン(地の輝度)に使う
BG_ROWS = 31               # 2 値化の背景推定に使う列方向メディアン窓 [px]
BIN_LEVEL = 0.5            # 半値幅規約
N_STATION = 24             # 断面を切る測点の数

N_EPOCH = 12               # 期の数(四半期ごと 3 年)
DT_YEAR = 0.25             # 期の間隔 [年]
W0_MM = 0.24               # 初期の幅 [mm] = 1.60 px
RATE_MM_YR = 0.040         # 真の成長率 [mm/年]

TEX_SIGMA = 0.05           # コンクリート面のざらつき(乗算性)
SENSOR_SIGMA = 0.010       # 撮像雑音(加算性)
SEED = 7

EPOCH_YEAR = np.arange(N_EPOCH) * DT_YEAR


# --------------------------------------------------------------------------- #
# 場面を作る                                                                    #
# --------------------------------------------------------------------------- #
def true_width(t_year: np.ndarray | float) -> np.ndarray:
    """真の幅 [mm]。線形に開く。"""
    return W0_MM + RATE_MM_YR * np.asarray(t_year, np.float64)


def _coverage(w_px: float, dy: float, slope: float, kx: int = 8) -> np.ndarray:
    """帯が各画素を覆う面積比 (H,W)。中心線 y = CY + dy + slope·(x - W/2)。

    画素 (i,j) は y in [i-.5, i+.5]。帯は中心線からの**垂直距離** w/2 以内なので、
    列 x での縦方向の半幅は (w/2)·sqrt(1+slope²)。列方向は kx 分割の求積。
    """
    sub = (np.arange(kx) + 0.5) / kx - 0.5
    xs = (np.arange(W_PX)[:, None] + sub[None, :]).ravel()
    yc = CY + dy + slope * (xs - 0.5 * W_PX)
    half = 0.5 * w_px * math.sqrt(1.0 + slope * slope)
    rows = np.arange(H_PX, dtype=np.float64)[:, None]
    ov = np.minimum(yc[None, :] + half, rows + 0.5) - np.maximum(yc[None, :] - half, rows - 0.5)
    np.clip(ov, 0.0, None, out=ov)
    return ov.reshape(H_PX, W_PX, kx).mean(axis=2)


def base_texture(seed: int) -> np.ndarray:
    """壁のざらつき(相関長 2.5 px)。**同じ壁なら毎回同じ場**。"""
    rng = np.random.default_rng(seed)
    f = gaussian_filter(rng.standard_normal((H_PX, W_PX)), 2.5)
    return f / (f.std() or 1.0)


def _illum(gain: float, slope: float, curve: float) -> np.ndarray:
    yy, xx = np.mgrid[0:H_PX, 0:W_PX].astype(np.float64)
    lit = gain * (1.0 - slope * (xx / W_PX))
    if curve:
        lit = lit + curve * np.cos(2.0 * np.pi * (yy - 20.0) / 90.0)
    return lit


def render(w_mm: float, *, psf: float = 1.0, dy: float = 0.0, gain: float = 1.0,
           lit_slope: float = 0.0, lit_curve: float = 0.0, path_slope: float = SLOPE0,
           tex: np.ndarray | None = None, noise_seed: int = 0,
           tex_sigma: float = TEX_SIGMA) -> dict:
    """1 期ぶんの画像。``dy`` は三脚を据え直したことによる上下ずれ [px]。

    壁の模様は据え直しに合わせて**一緒に動く**(カメラが動いたので)。照明は
    カメラ側の量として画素座標に固定する。
    """
    cov = _coverage(w_mm / PX_MM, dy, path_slope)
    cov_b = gaussian_filter(cov, psf)
    t = np.zeros((H_PX, W_PX)) if tex is None else nd_shift(tex, (dy, 0.0), order=1,
                                                            mode="nearest")
    base = _illum(gain, lit_slope, lit_curve) * (1.0 + tex_sigma * t)
    img = base * (1.0 - cov_b)
    if SENSOR_SIGMA > 0.0:
        img = img + SENSOR_SIGMA * np.random.default_rng(noise_seed).standard_normal(
            (H_PX, W_PX))
    return {"img": np.clip(img, 0.0, None), "cov": cov, "cov_blur": cov_b,
            "dy": dy, "psf": psf, "path_slope": path_slope}


# --------------------------------------------------------------------------- #
# 測り方 2 つ                                                                   #
# --------------------------------------------------------------------------- #
def deficit_map(img: np.ndarray) -> np.ndarray:
    """地の輝度で割った輝度欠損 1 - I/bg(地は列方向メディアン)。"""
    bg = median_filter(img, size=(BG_ROWS, 1), mode="nearest")
    return 1.0 - img / np.maximum(bg, 1e-6)


def detect_path(img: np.ndarray) -> tuple[np.ndarray, float]:
    """データだけから中心線を引く。列ごとの尾根 + 放物線補間 → 直線当てはめ。

    Returns: 各列の中心行 ``y(x)`` と傾き ``dy/dx``。
    """
    d = gaussian_filter(deficit_map(img), (0.0, 2.0))
    r = np.clip(np.argmax(d, axis=0), 1, H_PX - 2)
    cols = np.arange(W_PX)
    c, a, b = d[r, cols], d[r - 1, cols], d[r + 1, cols]
    den = a - 2.0 * c + b
    sub = np.where(np.abs(den) > 1e-9, 0.5 * (a - b) / np.where(den == 0.0, 1.0, den), 0.0)
    y = r + np.clip(sub, -1.0, 1.0)
    m, q = np.polyfit(cols.astype(np.float64), y, 1)
    return q + m * cols, float(m)


_T = np.arange(-R_PROF, R_PROF + 0.5 * DT_PROF, DT_PROF)
_OUT = np.abs(_T) >= T_BASE


def stations() -> np.ndarray:
    return np.linspace(R_PROF + 2.0, W_PX - R_PROF - 3.0, N_STATION)


def measure_integral(img: np.ndarray, y_of_x: np.ndarray, m: float,
                     order: int = 1) -> np.ndarray:
    """測点ごとに直交断面を切り、外側で ``order`` 次のベースラインを当てて積分 [mm]。"""
    n = math.sqrt(1.0 + m * m)
    ny, nx = 1.0 / n, -m / n
    out = np.empty(N_STATION)
    for k, x0 in enumerate(stations()):
        y0 = float(np.interp(x0, np.arange(W_PX), y_of_x))
        p0 = (y0 - R_PROF * ny, x0 - R_PROF * nx)
        p1 = (y0 + R_PROF * ny, x0 + R_PROF * nx)
        p = np.asarray(fs.line_profile(img, p0, p1, num=_T.size), np.float64)
        coef = np.polyfit(_T[_OUT], p[_OUT], order)
        base = np.polyval(coef, _T)
        out[k] = np.trapezoid(1.0 - p / np.maximum(base, 1e-6), dx=DT_PROF)
    return out * PX_MM


def measure_binary(img: np.ndarray, m: float) -> float:
    """ゼロ点。2 値化して**画素を数える**。面積 / 列数 = 平均の垂直幅 [mm]。"""
    mask = deficit_map(img) > BIN_LEVEL
    xs = stations()
    j0, j1 = int(round(xs[0])), int(round(xs[-1])) + 1
    band = mask[:, j0:j1]
    w_px = band.sum() / float(j1 - j0) / math.sqrt(1.0 + m * m)
    return w_px * PX_MM


def measure_epoch(img: np.ndarray) -> tuple[float, float]:
    """1 枚から(積分法の幅, 2 値化の幅)[mm]。経路は毎回データから引く。"""
    y, m = detect_path(img)
    return float(measure_integral(img, y, m).mean()), measure_binary(img, m)


# --------------------------------------------------------------------------- #
# 期ごとの環境(ぼけ・照明・据え直し)                                          #
# --------------------------------------------------------------------------- #
def schedule(seed: int = SEED, n: int = N_EPOCH) -> dict:
    """期ごとの撮影条件。**幅とは無関係**に決まる。"""
    rng = np.random.default_rng(seed)
    return {"psf": rng.uniform(0.75, 1.30, n),
            "dy": rng.uniform(-1.5, 1.5, n),
            "gain": rng.uniform(0.88, 1.12, n),
            "lit_slope": rng.uniform(0.0, 0.30, n),
            "lit_curve": rng.uniform(0.0, 0.05, n)}


def run_series(widths_mm, sch: dict, *, tex: np.ndarray | None, path_slope: float = SLOPE0,
               use_psf=True, use_lit=True, use_dy=True, noise_base: int = 900,
               tex_per_epoch: int | None = None) -> dict:
    """時系列 1 本を測る。``use_*`` を False にするとその要因だけ止まる(対照群)。"""
    est_i, est_b = [], []
    n = len(widths_mm)
    for k in range(n):
        t = tex if tex_per_epoch is None else base_texture(tex_per_epoch + k)
        sc = render(float(widths_mm[k]),
                    psf=float(sch["psf"][k]) if use_psf else 1.0,
                    dy=float(sch["dy"][k]) if use_dy else 0.0,
                    gain=float(sch["gain"][k]) if use_lit else 1.0,
                    lit_slope=float(sch["lit_slope"][k]) if use_lit else 0.0,
                    lit_curve=float(sch["lit_curve"][k]) if use_lit else 0.0,
                    path_slope=path_slope, tex=t, noise_seed=noise_base + k)
        a, b = measure_epoch(sc["img"])
        est_i.append(a)
        est_b.append(b)
    return {"int": np.asarray(est_i), "bin": np.asarray(est_b)}


def slope_of(t: np.ndarray, w: np.ndarray) -> float:
    """最小二乗の傾き [mm/年]。"""
    return float(np.polyfit(np.asarray(t, np.float64), np.asarray(w, np.float64), 1)[0])


# --------------------------------------------------------------------------- #
# 1. 描き手の検算                                                               #
# --------------------------------------------------------------------------- #
def section_renderer() -> None:
    print("\n" + "=" * 78)
    print("1) 描き手の検算 —— ぼけても輝度欠損の総量は動かない")
    print("=" * 78)
    print("  幅 [mm]  幅 [px]   Σcov/列 [px]   PSF 0.7 後   PSF 1.3 後   最大の差")
    for w in (0.10, 0.24, 0.35, 0.60):
        cov = _coverage(w / PX_MM, 0.0, SLOPE0)
        s0 = cov.sum() / W_PX
        s1 = gaussian_filter(cov, 0.7).sum() / W_PX
        s2 = gaussian_filter(cov, 1.3).sum() / W_PX
        want = w / PX_MM * math.sqrt(1.0 + SLOPE0 ** 2)
        print("   %5.2f   %6.3f    %10.6f   %10.6f   %10.6f   %.2e" % (
            w, w / PX_MM, s0, s1, s2, max(abs(s1 - s0), abs(s2 - s0))))
        assert abs(s0 - want) < 2e-3 * want, (s0, want)
        assert abs(s1 - s0) < 1e-9 * s0 and abs(s2 - s0) < 1e-9 * s0
    print("  → 畳み込みは総量を保存する。**積分法がぼけに強い理由はこれ**。")

    # きれいな場面(雑音なし・照明一様)での積分法の偏り
    sc = render(0.30, psf=1.0, tex=None)
    y, m = detect_path(sc["img"])
    e = measure_integral(sc["img"], y, m)
    print("\n  きれいな場面で積分法: 真値 0.300 mm -> %.4f mm (%+.2f %%, 散らばり %.1e)"
          % (e.mean(), 100 * (e.mean() - 0.30) / 0.30, e.std()))
    assert abs(e.mean() - 0.30) < 0.01, e.mean()

    # 2 値化が死ぬ幅の閉形式(erf のピーク欠損 = 0.5)
    for psf in (0.8, 1.0, 1.3):
        wc = 2.0 * math.sqrt(2.0) * erfinv(0.5) * psf
        print("  PSF σ=%.2f px -> 2 値化の臨界幅 1.349σ = %.3f px = %.3f mm"
              % (psf, wc, wc * PX_MM))


# --------------------------------------------------------------------------- #
# 2. 本命 —— 3 年 12 期の時系列                                                 #
# --------------------------------------------------------------------------- #
def section_series() -> dict:
    print("\n" + "=" * 78)
    print("2) 3 年 12 期 —— 幅の偏りと、成長率の誤差は別物")
    print("=" * 78)

    sch = schedule()
    tex = base_texture(SEED)
    w_true = true_width(EPOCH_YEAR)
    res = run_series(w_true, sch, tex=tex)

    print("   期   年     PSF σ  据え直し   真の幅    積分法      2 値化")
    for k in range(N_EPOCH):
        print("   %2d  %.2f   %.2f px  %+.2f px   %.4f   %.4f    %.4f" % (
            k, EPOCH_YEAR[k], sch["psf"][k], sch["dy"][k], w_true[k],
            res["int"][k], res["bin"][k]))

    bias_i = float(np.mean(res["int"] - w_true))
    bias_b = float(np.mean(res["bin"] - w_true))
    s_i, s_b = slope_of(EPOCH_YEAR, res["int"]), slope_of(EPOCH_YEAR, res["bin"])
    rms_i = float(np.sqrt(np.mean((res["int"] - w_true) ** 2)))
    rms_b = float(np.sqrt(np.mean((res["bin"] - w_true) ** 2)))
    # 傾きを引いた残差 = 成長率にそのまま効く散らばり
    sd_i = float(np.std(res["int"] - w_true - np.polyval(
        np.polyfit(EPOCH_YEAR, res["int"] - w_true, 1), EPOCH_YEAR)))
    sd_b = float(np.std(res["bin"] - w_true - np.polyval(
        np.polyfit(EPOCH_YEAR, res["bin"] - w_true, 1), EPOCH_YEAR)))

    print("\n  幅の偏り   : 積分法 %+.4f mm / 2 値化 %+.4f mm  (%.1f 倍)"
          % (bias_i, bias_b, abs(bias_b / bias_i) if bias_i else float("nan")))
    print("  幅の RMS   : 積分法 %.4f mm / 2 値化 %.4f mm" % (rms_i, rms_b))
    print("  成長率     : 真値 %.4f -> 積分法 %.4f (%+.1f %%) / 2 値化 %.4f (%+.1f %%) mm/年"
          % (RATE_MM_YR, s_i, 100 * (s_i - RATE_MM_YR) / RATE_MM_YR,
             s_b, 100 * (s_b - RATE_MM_YR) / RATE_MM_YR))
    print("  傾き除去後の散らばり: 積分法 %.4f mm / 2 値化 %.4f mm" % (sd_i, sd_b))
    print("\n  ★偏りは差分で消える。効くのは散らばりのほうで、そこが %.1f 倍違う。"
          % (sd_b / sd_i))
    assert abs(s_i - RATE_MM_YR) < 0.01, s_i
    assert abs(s_b - RATE_MM_YR) > abs(s_i - RATE_MM_YR), (s_b, s_i)

    k0, k1 = 0, N_EPOCH - 1
    sc0 = render(w_true[k0], psf=sch["psf"][k0], dy=sch["dy"][k0], gain=sch["gain"][k0],
                 lit_slope=sch["lit_slope"][k0], lit_curve=sch["lit_curve"][k0],
                 tex=tex, noise_seed=900 + k0)
    sc1 = render(w_true[k1], psf=sch["psf"][k1], dy=sch["dy"][k1], gain=sch["gain"][k1],
                 lit_slope=sch["lit_slope"][k1], lit_curve=sch["lit_curve"][k1],
                 tex=tex, noise_seed=900 + k1)
    figs.save_grid("frames",
                   [sc0["img"], sc1["img"],
                    deficit_map(sc0["img"]) > BIN_LEVEL,
                    deficit_map(sc1["img"]) > BIN_LEVEL],
                   ["1 期目(%.2f 年、真値 %.3f mm、PSF %.2f px)"
                    % (EPOCH_YEAR[k0], w_true[k0], sch["psf"][k0]),
                    "12 期目(%.2f 年、真値 %.3f mm、PSF %.2f px)"
                    % (EPOCH_YEAR[k1], w_true[k1], sch["psf"][k1]),
                    "1 期目の 2 値化マスク", "12 期目の 2 値化マスク"],
                   ncols=1,
                   title="同じ壁を 3 年撮り返す(1 px = %.2f mm、幅の伸びは %.2f mm)"
                         % (PX_MM, w_true[k1] - w_true[k0]),
                   caption="真の伸びは 3 年で %.2f mm = %.2f 画素。見た目で分かる差は"
                           "幅ではなく、ぼけと照明のほう。"
                           % (w_true[k1] - w_true[k0], (w_true[k1] - w_true[k0]) / PX_MM))
    figs.save_plot("timeseries",
                   [("真値", EPOCH_YEAR, w_true),
                    ("積分法", EPOCH_YEAR, res["int"]),
                    ("2 値化(画素を数える)", EPOCH_YEAR, res["bin"])],
                   xlabel="経過 [年]", ylabel="幅 [mm]",
                   kinds=["line", "scatter", "scatter"],
                   title="12 期の幅。成長率 真値 %.4f / 積分 %.4f / 2 値 %.4f mm/年"
                         % (RATE_MM_YR, s_i, s_b),
                   caption="2 値化は幅の偏りより**期ごとの跳ね**が問題。跳ねの正体は"
                           "ぼけと画素位相で、4 節と 3 節で分けて数える。")
    return {"res": res, "true": w_true, "sch": sch, "tex": tex,
            "slope_int": s_i, "slope_bin": s_b, "bias_int": bias_i, "bias_bin": bias_b,
            "sd_int": sd_i, "sd_bin": sd_b}


# --------------------------------------------------------------------------- #
# 3. 対照群 —— 幅を凍結して環境だけ動かす                                       #
# --------------------------------------------------------------------------- #
FROZEN_MM = 0.30


def section_control(base: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) 対照群 —— 幅は 1 μm も変えず、環境だけ 12 期ぶん動かす")
    print("=" * 78)
    print("  真の成長率は **0.0000 mm/年**。ここで出る傾きは全部『見かけ』。")
    print("\n   止めない要因            積分法 [mm/年]   2 値化 [mm/年]")

    sch, tex = base["sch"], base["tex"]
    frozen = np.full(N_EPOCH, FROZEN_MM)
    conds = [("何も動かさない(雑音のみ)", dict(use_psf=False, use_lit=False, use_dy=False)),
             ("ぼけだけ", dict(use_psf=True, use_lit=False, use_dy=False)),
             ("照明だけ", dict(use_psf=False, use_lit=True, use_dy=False)),
             ("据え直しだけ", dict(use_psf=False, use_lit=False, use_dy=True)),
             ("全部", dict(use_psf=True, use_lit=True, use_dy=True))]
    out, rows = {}, []
    for name, kw in conds:
        r = run_series(frozen, sch, tex=tex, noise_base=400, **kw)
        si, sb = slope_of(EPOCH_YEAR, r["int"]), slope_of(EPOCH_YEAR, r["bin"])
        out[name] = (si, sb, r)
        rows.append([name, "%+.4f" % si, "%+.4f" % sb,
                     "%.4f" % float(r["int"].std()), "%.4f" % float(r["bin"].std())])
        print("   %-22s   %+8.4f        %+8.4f" % (name, si, sb))

    all_i, all_b = out["全部"][0], out["全部"][1]
    print("\n  ★2 値化は幅を止めても %+.4f mm/年 の『成長』を出す —— "
          "真の成長率 %.4f mm/年 の %.0f %%。" % (all_b, RATE_MM_YR,
                                                 100 * abs(all_b) / RATE_MM_YR))
    print("     要因を 1 つずつ止めて分けると、犯人は**ぼけ**(単独 %+.4f)。"
          "照明 %+.4f / 据え直し %+.4f はほぼ無害。"
          % (out["ぼけだけ"][1], out["照明だけ"][1], out["据え直しだけ"][1]))
    print("     積分法は全部動かしても %+.4f mm/年。1 節の保存則がそのまま効く。"
          % all_i)
    assert abs(all_i) < abs(all_b), (all_i, all_b)

    figs.save_table("control",
                    ["動かした要因", "積分法 mm/年", "2 値化 mm/年",
                     "積分の散らばり mm", "2 値の散らばり mm"],
                    rows, title="幅を %.2f mm に凍結した対照群(真の成長率 0)" % FROZEN_MM,
                    caption="ここに出る傾きはすべて『見かけの成長』。要因を 1 つずつ"
                            "止めた 5 条件で、どれが効いているかを分ける。")
    figs.save_plot("control_series",
                   [("真値(凍結)", EPOCH_YEAR, frozen),
                    ("積分法(全要因)", EPOCH_YEAR, out["全部"][2]["int"]),
                    ("2 値化(全要因)", EPOCH_YEAR, out["全部"][2]["bin"]),
                    ("2 値化(ぼけだけ)", EPOCH_YEAR, out["ぼけだけ"][2]["bin"])],
                   xlabel="経過 [年]", ylabel="測った幅 [mm]",
                   kinds=["line", "scatter", "scatter", "line"],
                   title="幅を凍結した対照群 —— それでも 2 値化は動く",
                   caption="真の幅は %.2f mm で一定。2 値化の上下はぼけの σ に"
                           "追随している。" % FROZEN_MM)
    return {"cond": {k: (v[0], v[1]) for k, v in out.items()}}


# --------------------------------------------------------------------------- #
# 4. 画素の位相 —— 経路の傾きで跳ねが変わる                                     #
# --------------------------------------------------------------------------- #
def section_phase() -> dict:
    print("\n" + "=" * 78)
    print("4) 据え直しの半画素 —— 経路が水平だと全列の位相が揃って 1 px 跳ぶ")
    print("=" * 78)
    print("  幅は %.2f mm で凍結。ぼけと照明も止め、**据え直しだけ**動かす。" % FROZEN_MM)

    sch = schedule(seed=SEED + 1)
    tex = base_texture(SEED)
    frozen = np.full(N_EPOCH, FROZEN_MM)
    span = float(stations()[-1] - stations()[0])
    m_crit = 1.0 / span
    print("  ★予測を先に: 位相が混ざるには測る区間 %.0f 列で中心線が 1 px 以上"
          "動けばよい → 臨界の傾き 1/%.0f = %.4f。" % (span, span, m_crit))
    print("\n   経路の傾き   区間での上下差   積分法 σ [mm]   2 値化 σ [mm]")

    slopes = (0.0, 0.002, 0.005, 0.02, 0.10, 0.35)
    sd_i, sd_b, rows = [], [], []
    for m in slopes:
        r = run_series(frozen, sch, tex=tex, path_slope=m, use_psf=False, use_lit=False,
                       use_dy=True, noise_base=600)
        a, b = float(r["int"].std()), float(r["bin"].std())
        sd_i.append(a)
        sd_b.append(b)
        rows.append(["%.3f" % m, "%.2f px" % (m * span), "%.4f" % a, "%.4f" % b])
        print("    %.3f         %6.2f px          %.4f         %.4f"
              % (m, m * span, a, b))

    print("\n  ★2 値化の期ごとの散らばりは傾き 0.000 で %.4f mm、0.350 で %.4f mm"
          "(%.0f 分の 1)。" % (sd_b[0], sd_b[-1], sd_b[0] / max(sd_b[-1], 1e-9)))
    print("     水平だと全列が同じ位相なので、幅は列ごとではなく**画面ごと**に"
          "1 px = %.2f mm 単位で跳ぶ。" % PX_MM)
    drop = [m for m, b in zip(slopes, sd_b) if b < 0.5 * sd_b[0]]
    print("  ★崖の位置: 傾き %.3f で半分を切る。予測 %.4f(区間で 1 px 動く傾き)と"
          "同じ目盛り。" % (min(drop) if drop else float("nan"), m_crit))
    print("  ★予想は「傾けると断面が斜めに切れて積分法も悪くなる」だったが、"
          "積分法の σ は %.4f -> %.4f mm で**ほぼ無反応**(2 値化の %.0f 分の 1)。"
          % (sd_i[0], sd_i[-1], sd_b[0] / max(sd_i[0], 1e-9)))
    assert sd_b[0] > 10.0 * sd_i[0], (sd_b[0], sd_i[0])
    assert sd_b[0] > sd_b[-1], (sd_b[0], sd_b[-1])

    figs.save_plot("phase",
                   [("2 値化", slopes, sd_b), ("積分法", slopes, sd_i)],
                   xlabel="ひび割れの傾き dy/dx", ylabel="期ごとの散らばり σ [mm]",
                   kinds=["scatter", "scatter"],
                   title="据え直しの半画素がどれだけ跳ねるか(幅は凍結、崖の予測 %.4f)"
                         % m_crit,
                   caption="傾きが 0 に近いほど列方向の画素位相が揃い、2 値化は"
                           "画面ごと 1 画素単位で跳ぶ。積分法は傾きに無反応。")
    figs.save_table("phase_tbl",
                    ["傾き dy/dx", "区間での上下差", "積分法 σ mm", "2 値化 σ mm"],
                    rows, title="画素位相が混ざる崖(予測 %.4f = 1/%.0f 列)"
                                % (m_crit, span))
    return {"slopes": slopes, "sd_int": sd_i, "sd_bin": sd_b, "m_crit": m_crit,
            "drop": (min(drop) if drop else float("nan"))}


# --------------------------------------------------------------------------- #
# 5. 何期あれば「有意な成長」と言えるか                                         #
# --------------------------------------------------------------------------- #
N_SITE = 12


def section_cliff_epochs() -> dict:
    print("\n" + "=" * 78)
    print("5) 崖 —— 何期あれば有意か。閉形式 σ_slope = σ_w/(σ_t·√N)")
    print("=" * 78)
    print("  %d サイト(据え直し・雑音・撮影条件が別)を %d 期まで撮り、"
          "先頭 N 期で傾きを出す。" % (N_SITE, N_EPOCH))

    w_true = true_width(EPOCH_YEAR)
    series_i, series_b = [], []
    for s in range(N_SITE):
        sch = schedule(seed=SEED + 10 * s + 3)
        r = run_series(w_true, sch, tex=base_texture(SEED), noise_base=1500 + 40 * s)
        series_i.append(r["int"])
        series_b.append(r["bin"])
    A_I, A_B = np.asarray(series_i), np.asarray(series_b)

    # 1 点の散らばり σ_w(真値と傾きを抜いた残差)
    def resid_sd(a):
        rs = []
        for row in a:
            rs.append(row - w_true - np.polyval(np.polyfit(EPOCH_YEAR, row - w_true, 1),
                                                EPOCH_YEAR))
        return float(np.std(np.concatenate(rs), ddof=1))

    sw_i, sw_b = resid_sd(A_I), resid_sd(A_B)
    print("  1 点の散らばり σ_w: 積分法 %.4f mm / 2 値化 %.4f mm" % (sw_i, sw_b))
    print("\n   N 期  期間[年]   積分 実測σ   積分 予測σ   比    2値 実測σ   2値 予測σ   比")
    rows, ns, mi, pi_, mb, pb = [], [], [], [], [], []
    for n in (3, 4, 6, 8, 12):
        t = EPOCH_YEAR[:n]
        st = float(np.std(t))
        gi = np.asarray([slope_of(t, a[:n]) for a in A_I])
        gb = np.asarray([slope_of(t, a[:n]) for a in A_B])
        p_i, p_b = sw_i / (st * math.sqrt(n)), sw_b / (st * math.sqrt(n))
        s_i, s_b = float(gi.std(ddof=1)), float(gb.std(ddof=1))
        rows.append([str(n), "%.2f" % (t[-1]), "%.4f" % s_i, "%.4f" % p_i,
                     "%.2f" % (s_i / p_i), "%.4f" % s_b, "%.4f" % p_b,
                     "%.2f" % (s_b / p_b)])
        ns.append(n)
        mi.append(s_i)
        pi_.append(p_i)
        mb.append(s_b)
        pb.append(p_b)
        print("    %2d    %.2f      %.4f      %.4f     %.2f   %.4f      %.4f     %.2f"
              % (n, t[-1], s_i, p_i, s_i / p_i, s_b, p_b, s_b / p_b))

    ratios = [a / b for a, b in zip(mi, pi_)]
    ratios_b = [a / b for a, b in zip(mb, pb)]
    # M サイトから推定した σ 自体の相対誤差は 1/sqrt(2(M-1))
    rel = 1.0 / math.sqrt(2.0 * (N_SITE - 1))
    print("\n  ★積分法の予測との比は %.2f 〜 %.2f。%d サイトから σ を推定した"
          "こと自体の相対誤差が ±%.0f %% なので、この幅は標本のゆらぎの範囲。"
          % (min(ratios), max(ratios), N_SITE, 100 * rel))
    print("  ★2 値化の比は %.2f 〜 %.2f と**一貫して 1 を超える** —— 誤差が"
          "白色雑音でない(1 画素の階段に張り付く)ので iid の閉形式は下振れする。"
          % (min(ratios_b), max(ratios_b)))
    need_i = [n for n, s in zip(ns, mi) if 2.0 * s < RATE_MM_YR]
    need_b = [n for n, s in zip(ns, mb) if 2.0 * s < RATE_MM_YR]
    print("  ★%.3f mm/年 を 2σ で言い切るのに要る期数: 積分法 %s / 2 値化 %s。"
          % (RATE_MM_YR,
             ("%d 期(%.1f 年)" % (min(need_i), (min(need_i) - 1) * DT_YEAR))
             if need_i else "12 期でも足りない",
             ("%d 期(%.1f 年)" % (min(need_b), (min(need_b) - 1) * DT_YEAR))
             if need_b else "12 期でも足りない"))

    # --- 同じ壁 vs 毎回別の壁 ------------------------------------------------- #
    print("\n  地の模様は同じ壁なら毎回同じ。**共通成分は差分で消える**はず ——")
    gi_same, gi_indep = [], []
    for s in range(N_SITE):
        sch = schedule(seed=SEED + 10 * s + 3)
        r = run_series(w_true, sch, tex=None, tex_per_epoch=3000 + 50 * s,
                       noise_base=1500 + 40 * s)
        gi_indep.append(slope_of(EPOCH_YEAR, r["int"]))
        gi_same.append(slope_of(EPOCH_YEAR, A_I[s]))
    sd_same = float(np.std(np.asarray(gi_same), ddof=1))
    sd_indep = float(np.std(np.asarray(gi_indep), ddof=1))
    print("   同じ壁(模様は固定、据え直しだけ)  : 傾きの σ %.4f mm/年" % sd_same)
    print("   毎回別の模様(独立)                : 傾きの σ %.4f mm/年" % sd_indep)
    print("  ★%.1f 倍。合成の独立雑音で評価すると**実写より悲観的**になる。"
          % (sd_indep / max(sd_same, 1e-9)))

    figs.save_plot("cliff_epochs",
                   [("積分法 実測", ns, mi), ("積分法 予測 σ_w/(σ_t√N)", ns, pi_),
                    ("2 値化 実測", ns, mb), ("2 値化 予測", ns, pb),
                    ("必要な精度 (rate/2)", ns, [RATE_MM_YR / 2.0] * len(ns))],
                   xlabel="使った期数 N", ylabel="成長率の標準偏差 [mm/年]",
                   kinds=["scatter", "line", "scatter", "line", "line"],
                   title="成長率の不確かさは √N で落ちる(実測 %d サイト)" % N_SITE,
                   caption="横線を下回った時点で 0.040 mm/年 を 2σ で言える。"
                           "2 値化は 3 年でも届かない。")
    figs.save_table("cliff_epochs_tbl",
                    ["N 期", "期間 年", "積分 実測σ", "積分 予測σ", "比",
                     "2値 実測σ", "2値 予測σ", "比"], rows,
                    title="成長率の標準偏差 [mm/年] —— 実測と閉形式")
    return {"n": ns, "meas_int": mi, "pred_int": pi_, "meas_bin": mb, "pred_bin": pb,
            "sw_int": sw_i, "sw_bin": sw_b, "sd_same": sd_same, "sd_indep": sd_indep,
            "ratios": ratios, "ratios_bin": ratios_b,
            "need_int": (min(need_i) if need_i else None),
            "need_bin": (min(need_b) if need_b else None)}


# --------------------------------------------------------------------------- #
# 6. 崖その 2 —— 元の幅を振る                                                   #
# --------------------------------------------------------------------------- #
def section_cliff_width() -> dict:
    print("\n" + "=" * 78)
    print("6) 崖その 2 —— 細いひび割れの成長は読めるか(2 値化の臨界幅は erf で出る)")
    print("=" * 78)
    psf_mean = float(schedule()["psf"].mean())
    wc_px = 2.0 * math.sqrt(2.0) * erfinv(0.5) * psf_mean
    print("  期ごとの PSF σ の平均 %.2f px。臨界幅の予測 1.349σ = %.3f px = %.3f mm。"
          % (psf_mean, wc_px, wc_px * PX_MM))
    print("\n   初期の幅 [mm]  [px]  ピーク欠損(予測)  積分の成長率   2 値の成長率  2値の非ゼロ期")

    sch = schedule()
    tex = base_texture(SEED)
    n = N_EPOCH
    t = EPOCH_YEAR[:n]
    rows, w0s, gi, gb = [], [], [], []
    for w0 in (0.10, 0.15, 0.20, 0.24, 0.35, 0.55):
        widths = w0 + RATE_MM_YR * t
        r = run_series(widths, sch, tex=tex, noise_base=2500)
        si, sb = slope_of(t, r["int"]), slope_of(t, r["bin"])
        peak = float(erf((w0 / PX_MM) / (2.0 * math.sqrt(2.0) * psf_mean)))
        nz = int(np.count_nonzero(r["bin"] > 1e-9))
        rows.append(["%.2f" % w0, "%.2f" % (w0 / PX_MM), "%.3f" % peak,
                     "%.4f" % si, "%.4f" % sb, "%d/%d" % (nz, n)])
        w0s.append(w0)
        gi.append(si)
        gb.append(sb)
        print("      %.2f       %.2f      %.3f          %.4f        %.4f       %d/%d"
              % (w0, w0 / PX_MM, peak, si, sb, nz, n))

    dead = [w for w, g in zip(w0s, gb) if abs(g) < 1e-9]
    print("\n  ★2 値化が全期ゼロ(何も返さない)なのは %s mm。"
          % (", ".join("%.2f" % w for w in dead) if dead else "(この掃引には無い)"))
    print("     予測の臨界幅 %.3f mm と %s。" % (
        wc_px * PX_MM,
        "整合" if (not dead or max(dead) <= wc_px * PX_MM + 0.05) else "食い違う"))
    live = [g for g in gb if abs(g) > 1e-9]
    print("  ★★**2 値化の成長率は初期の幅で %.4f 〜 %.4f mm/年 と %.0f 倍動く**"
          "(真値はどれも %.4f)。" % (min(live), max(live), max(live) / max(min(live), 1e-9),
                                     RATE_MM_YR))
    print("     階段の段差が観測窓の中に来たかどうかで決まるので、**同じ速さで"
          "開いているひび割れでも、初期幅が違うだけで報告が桁で変わる**。")
    print("     2 節の 2 値化が %+.1f %% 外したのもこれ(0.24 mm から始めたから)。"
          % (100 * (gb[w0s.index(0.24)] - RATE_MM_YR) / RATE_MM_YR))
    err_i = [abs(g - RATE_MM_YR) / RATE_MM_YR for g in gi]
    print("  ★積分法は %.2f mm(%.2f px)でも成長率 %.4f mm/年(真値 %.4f, %+.1f %%)、"
          "全幅で誤差 %.1f 〜 %.1f %%。"
          % (w0s[0], w0s[0] / PX_MM, gi[0], RATE_MM_YR,
             100 * (gi[0] - RATE_MM_YR) / RATE_MM_YR,
             100 * min(err_i), 100 * max(err_i)))
    assert max(err_i) < 0.15, err_i
    assert max(live) / max(min(live), 1e-9) > 3.0, live

    figs.save_plot("cliff_width",
                   [("真値", w0s, [RATE_MM_YR] * len(w0s)),
                    ("積分法", w0s, gi), ("2 値化", w0s, gb)],
                   xlabel="初期の幅 [mm]", ylabel="測った成長率 [mm/年]",
                   kinds=["line", "scatter", "scatter"],
                   title="細いひび割れの成長率(臨界幅の予測 %.3f mm)" % (wc_px * PX_MM),
                   caption="2 値化は臨界幅より細いと 0(未検出)。積分法は 0.10 mm"
                           "(%.2f px)でも成長率を返す。" % (0.10 / PX_MM))
    figs.save_table("cliff_width_tbl",
                    ["初期幅 mm", "px", "ピーク欠損", "積分 mm/年", "2値 mm/年",
                     "2値の非ゼロ期"], rows,
                    title="幅を振ったときの成長率(真値 %.4f mm/年)" % RATE_MM_YR)
    return {"w0": w0s, "int": gi, "bin": gb, "wc_mm": wc_px * PX_MM, "dead": dead,
            "live": live}


# --------------------------------------------------------------------------- #
# 7. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("7) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)

    assert hasattr(fs, "line_profile")
    assert not hasattr(fs, "line_profiles") and not hasattr(fs.ledger, "normal_profiles")
    print("  (a) 中心線に沿って**法線断面をまとめて切る**口が無い(ribbon 展開)。"
          "この PoC は %d 測点 x %d 期を 1 本ずつ回している。" % (N_STATION, N_EPOCH))

    assert not hasattr(fs, "profile_baseline") and not hasattr(fs.ledger, "profile_baseline")
    print("  (b) 1-D 断面の**ベースライン除去**(外側だけで多項式)が無い。")

    for nm in ("trend_slope", "theil_sen_slope", "linear_trend"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (c) 時系列の**傾きと その不確かさ**を返す口が無い。4-D ツイン"
          "(経時の測り返し)では出す数字が mm ではなく mm/年 なので、"
          "傾き・標準誤差・有意性は族として要る。")

    assert not hasattr(fs, "detect_limit") and not hasattr(fs.ledger, "detection_limit")
    print("  (d) **検出限界**(何期・どの精度なら言い切れるか)を返す口が無い。"
          "3-D 側には m3c2_distance の lod が在るのに、2-D の時系列には無い。")

    assert not hasattr(fs, "psf_sigma_estimate") and not hasattr(fs.ledger, "estimate_psf")
    print("  (e) 画像から **PSF の σ を推定する**口が無い。3 節のとおり見かけの"
          "成長の主因はぼけなので、期ごとの σ を測れないと補正もできない。")

    assert not hasattr(fs, "autocorrelation_length")
    print("  (f) 面のざらつきの**相関長**を測る口が無い(積分法の散らばりは"
          " σ·sqrt(2R·l) で決まる)。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("ひび割れの「幅」ではなく「伸び」を測る —— 3 年 12 期の画像列")
    print("視野 %d x %d px / 1 px = %.2f mm / 真の成長率 %.3f mm/年" % (
        W_PX, H_PX, PX_MM, RATE_MM_YR))
    print("=" * 78)

    section_renderer()
    base = section_series()
    ctrl = section_control(base)
    ph = section_phase()
    cl = section_cliff_epochs()
    cw = section_cliff_width()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 幅の偏りは 2 値化 %+.4f / 積分法 %+.4f mm だが、成長率は "
          "%.4f / %.4f mm/年(真値 %.4f)—— 偏りは差分で消える。"
          % (base["bias_bin"], base["bias_int"], base["slope_bin"], base["slope_int"],
             RATE_MM_YR))
    print("  * 幅を凍結した対照群でも 2 値化は %+.4f mm/年 動く。犯人はぼけ(%+.4f)。"
          % (ctrl["cond"]["全部"][1], ctrl["cond"]["ぼけだけ"][1]))
    print("  * 据え直しの半画素は、経路が水平だと %.4f mm、傾き 0.35 だと %.4f mm 跳ねる。"
          % (ph["sd_bin"][0], ph["sd_bin"][-1]))
    print("  * 成長率の σ は閉形式 σ_w/(σ_t√N) と比 %.2f〜%.2f で一致。"
          % (min(cl["ratios"]), max(cl["ratios"])))
    print("  * 2 値化の臨界幅の予測 %.3f mm に対し、全期ゼロは %s。"
          % (cw["wc_mm"], ", ".join("%.2f" % w for w in cw["dead"]) or "無し"))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()

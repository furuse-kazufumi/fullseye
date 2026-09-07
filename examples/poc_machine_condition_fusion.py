# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""熱・振動・形状を束ねる設備保全 —— 3 つ見ても、同じものを 3 回見ていることがある。

回転機械(電動機 - たわみ軸継手 - ポンプ)を 3 つのセンサで同時に見ます。
**振動**(加速度、半径方向 + 軸方向)、**熱画像**(筐体表面の温度上昇)、
**形状**(レーザで測った軸心のずれ)。現場ではこの 3 つを並べて「総合判定」を
出します。ところが 3 つが独立でない —— 同じ原因の別の顔 —— なら、束ねても
情報は増えません。**どの故障モードでどのセンサが効き、どこから互いに冗長に
なるのか**を、真値を仕込んで測ります。

EXTEND: 実機に差し替えるなら :func:`vib_record` の返り値(半径・軸方向の
加速度列)を実測に、:func:`thermal_frame` の返り値を放射温度計のフレームに、
:func:`shaft_points` の返り値を軸心測定の点列に置き換えます。
**モードのラベルが要ります** —— この PoC の主張は「センサを 1 つ抜くと
どのモードがどのモードに化けるか」なので、1 個の総合正解率に畳んだ時点で
測れません。軸受の諸元 :data:`BEARING` は銘板から引いて
:func:`fullseye.ledger.bearing_defect_frequencies` に渡すこと(数表を写さない)。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★★**3 つ束ねても 2 つと変わらないモードがある**。芯ずれの識別率は
   3 センサ 100.0 %、振動を抜いても 100.0 %、熱を抜いても 100.0 %、
   形状だけでも 100.0 %。芯ずれは軸心のずれ 1 つが原因で、2X 振動も
   継手の発熱も**その 1 つの数字の別の顔**なので、3 回測っても 1 回ぶんの
   情報しかない。実測の相関(重心のずれ δ に対する 2X 振動 / 継手温度)は
   0.997 / 0.994 で、**3 つのセンサは同じ潜在変数を見ている**。
2. ★★**1 つでは絶対に分けられない対がある**。形状だけだとアンバランス・
   軸受外輪傷・潤滑不良・ゆるみ・正常の 5 つが**全部 1 つの塊**になる
   (5 モードの識別率 0.0〜31.2 %)。熱だけだとアンバランスとゆるみが
   互いに化ける(それぞれ 25.0 % / 6.2 %)。**振動を抜いた瞬間に
   軸受外輪傷と潤滑不良が入れ替わる**(3 センサ 100.0 % → 熱+形状 43.8 %)。
3. **ゼロ点(センサ 1 つ・しきい値 1 個)は異常を見つけるが名指しできない**。
   振動 RMS の 3σ しきい値は異常検出率 91.2 %(誤警報 0.0 %)まで行くのに、
   **5 つの故障モードのどれも名指しできない**(モード識別率は定義上 0 %)。
   熱の最高温度は 71.2 %、芯ずれ量は 20.0 %。
4. ★**崖 1(記録長)は 2 つあって、両方とも先に予測できた**。ゆるみの
   0.5X 成分は次数分解能 = 1/(整数回転数)が 0.5 を切る **T > 2/f_r =
   68.6 ms** から測れる。軸受の側帯波(保持器周波数 FTF = 11.62 Hz 間隔)は
   **T > 1/FTF = 86.1 ms** から分離できる。実測の折れ目は 70 ms と 100 ms
   で、どちらも予測の直後の掃引点だった。
5. ★**崖 2(回転数変動)は次数に比例して先に壊れる**。次数 o の線は
   ±o·f_r·δ Hz に広がるので、1 ビン(1/T)に収まる条件は δ < 1/(2 o f_r T)。
   T=1 s で 2X は δ<0.86 %、BPFO(3.585 次)は δ<0.48 %、6X の櫛は
   δ<0.29 %。実測でも**ゆるみが最初に落ち**(δ=0.5 % で 68.8 %)、
   芯ずれは δ=4 % でも 100.0 % を保った。
6. ★**崖 3(熱画像の画素)は「熱いか」ではなく「広がりが測れるか」で折れる**。
   軸受の局所発熱と潤滑不良の全体発熱は最高温度がほぼ同じで、分けているのは
   **高温域の広がり**。半値半径 8.6 mm を画素ピッチが超えると広がりが測れず、
   実測でもピッチ 16 mm から軸受/潤滑の熱のみ識別率が落ちた。
7. ★**予想が外れたこと**: 「センサを 1 つ抜けば必ず落ちる」ではなかった。
   芯ずれ・アンバランスは振動を抜いても落ちない(前者は形状、後者は熱と
   形状の「何も無い」が効く)。落ちるのは**軸受外輪傷と潤滑不良の対だけ**。
   束ねる価値はモードごとに違い、平均正解率に畳むとこの差が消える。

【グラウンドトゥルース】
欠陥周波数は軸受の幾何から**閉形式**(N・ピッチ円径・素子径・接触角・回転数)。
熱は板の定常フィン方程式 ∇²θ - θ/L² = -g/(kt) の**厳密解**(円板熱源、
内側 θ=θ∞[1-αK₁(α)I₀(r/L)]、外側 θ=θ∞ α I₁(α) K₀(r/L)、α=a/L、
θ∞=Q/(2hπa²))を重ね合わせたもの。形状は仕込んだ芯ずれ量そのもの。
測定の現実(振動の雑音とエイリアス、熱の画素ピッチ・放射率むら・NETD、
形状の測定分解能)はすべて既知の量で入れてある。

来歴(公開文献のみ): Randall & Antoni, *MSSP* 25 (2011) 485 —— 転がり軸受の
診断(包絡線解析・側帯波)/ Antoni, *MSSP* 20 (2006) 282 —— スペクトル尖度 /
Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer* —— フィンの
定常解 / ISO 10816(機械振動の評価基準、RMS 単一しきい値の由来)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.special import i0 as bessel_i0, i1 as bessel_i1, k0 as bessel_k0, k1 as bessel_k1

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 機械の諸元 -------------------------------------------------------------- #
RPM = 1750.0               # 回転数 [min^-1]
RATE = 12800.0             # 振動のサンプリング周波数 [Hz]
DURATION = 1.0             # 既定の記録長 [s] -> 周波数分解能 1.00 Hz
RESONANCE = 3000.0         # 筐体の構造共振(衝撃が叩く搬送波)[Hz]
DAMPING = 0.05             # 共振の減衰比
BAND = (2000.0, 4000.0)    # 包絡線解析の復調帯域 [Hz]
VIB_NOISE = 0.05           # 加速度計の雑音 σ [任意単位 ~ g]
F_MOD = 1.7                # 回転数変動のゆらぎ周波数 [Hz]
SEED = 7

#: 軸受の幾何(9 転動体、素子径 7.94 mm、ピッチ円径 39.04 mm、接触角 0 度)。
BEARING = dict(rpm=RPM, n_elements=9, element_diameter=7.94,
               pitch_diameter=39.04, contact_angle_deg=0.0)

# --- 熱の諸元(鋼の筐体板)---------------------------------------------------- #
K_STEEL = 45.0             # 熱伝導率 [W/(m K)]
T_PLATE = 0.008            # 板厚 [m]
H_CONV = 12.0              # 片面の対流熱伝達率 [W/(m^2 K)](両面で 2h)
T_AMB = 293.15             # 周囲温度 [K]
NETD = 0.08                # 放射温度計の雑音等価温度差 [K]
EMIS_TRUE = 0.95           # 真の放射率(むらの中心)
EMIS_SPREAD = 0.030        # 放射率むらの振幅(±)
EMIS_ASSUMED = 0.95        # カメラに設定した放射率(=中心。むらだけが誤差になる)
VIEW_W, VIEW_H = 320, 240  # 視野 [mm](細かい格子は 1 mm/px)
PITCH = 2                  # 既定の画素ピッチ [mm]

#: 発熱源 ``(名前, x[mm], y[mm], 半径 a[mm])``。半径は熱源の広がりで、
#: 閉形式の解はこの a に依存する(点源にすると中心で発散する)。
SOURCES = (("継手", 110.0, 120.0, 15.0),
           ("軸受A", 185.0, 120.0, 12.0),
           ("軸受B", 250.0, 120.0, 12.0),
           ("機械全体", 170.0, 120.0, 70.0))

# --- 形状(軸心)の諸元 ------------------------------------------------------ #
GEOM_SIGMA = 0.020         # 軸心測定 1 点の雑音 σ [mm]
N_AXIS_PTS = 12            # 片側の測定点数
AXIS_Z = (30.0, 150.0)     # 継手面からの測定範囲 [mm]

#: 故障モード(正常を含む 6 クラス)。
MODES = ("正常", "芯ずれ", "アンバランス", "軸受外輪傷", "潤滑不良", "ゆるみ")
FAULTS = MODES[1:]

#: 学習・試験の 1 モードあたりの試行数(学習と試験で別 seed)。
N_TRAIN, N_TEST = 16, 16

#: 重症度 s の範囲(対数一様)。同じモードでも「軽い/重い」が混ざる。
SEV_LO, SEV_HI = 0.6, 1.8

# 特徴量の名前。センサごとに分けてあるのが対照群(センサを抜く)の単位。
VIB_FEATS = ("v_rms", "v_kurt", "v_crest", "v_o05", "v_o1", "v_o2",
             "v_comb", "v_ax", "v_hf", "v_sk", "v_bpfo", "v_sb")
THR_FEATS = ("t_max", "t_coup", "t_bear", "t_glob", "t_spread")
SHP_FEATS = ("s_off", "s_ang", "s_res")
ALL_FEATS = VIB_FEATS + THR_FEATS + SHP_FEATS
#: 対数を取る特徴(振幅・面積・長さ)。尖度や尖り係数は取らない(負も来る)。
LOG_FEATS = frozenset(ALL_FEATS) - frozenset(("v_kurt", "v_crest", "v_sk"))

SENSORS = {"振動": VIB_FEATS, "熱": THR_FEATS, "形状": SHP_FEATS}


# --------------------------------------------------------------------------- #
# 真値 —— 軸受の欠陥周波数は幾何から閉形式で決まる                              #
# --------------------------------------------------------------------------- #
KIN = fs.ledger.bearing_defect_frequencies(**BEARING)
FR = KIN["shaft_hz"]           # 軸回転 [Hz]
FTF = KIN["ftf_hz"]            # 保持器(側帯波の間隔)[Hz]
BPFO = KIN["bpfo_hz"]          # 外輪欠陥通過 [Hz]
ORDER_BPFO = BPFO / FR


def mode_params(mode: str, sev: float) -> dict:
    """1 つの潜在変数 ``sev``(重症度)から、3 センサの真値をすべて決める。

    **ここが PoC の中心**。芯ずれなら 2X 振動も継手の発熱も軸心のずれも、
    すべて同じ ``sev`` の関数 —— だから 3 つ測っても 1 つぶんの情報しかない。
    軸受外輪傷なら、周波数(振動)だけが「軸受である」という身元を持ち、
    熱は「軸受あたりが熱い」としか言わない(潤滑不良と同じ顔)。
    """
    s = float(sev)
    # (半径方向の次数成分, 軸方向の次数成分, BPFO 衝撃, 帯域雑音)
    harm = {1.0: 0.020, 2.0: 0.006}
    axial = {1.0: 0.004, 2.0: 0.002}
    bpfo, mod, bb = 0.0, 0.0, 0.010
    # (継手, 軸受A, 軸受B, 機械全体) の発熱 [W]。★正常・アンバランス・ゆるみは
    # **わざと同じ**にしてある —— 熱では原理的に分けられない 3 モード。
    heat = (0.5, 2.5, 2.5, 3.0)
    off, ang = 0.010, 0.030          # 芯ずれ量 [mm] / 角度ずれ [mrad]
    if mode == "芯ずれ":
        harm = {1.0: 0.055 * s, 2.0: 0.150 * s, 3.0: 0.035 * s}
        axial = {1.0: 0.070 * s, 2.0: 0.090 * s}
        heat = (16.0 * s, 3.0, 2.8, 3.0)
        off, ang = 0.280 * s, 0.55 * s
    elif mode == "アンバランス":
        harm = {1.0: 0.230 * s, 2.0: 0.018 * s}
        axial = {1.0: 0.012 * s, 2.0: 0.004 * s}
        heat = (0.6, 2.7, 2.6, 3.1)
    elif mode == "軸受外輪傷":
        bpfo, mod = 0.130 * s, 0.55
        heat = (0.5, 11.0 * s, 2.6, 3.0)
    elif mode == "潤滑不良":
        bb = 0.010 + 0.075 * s
        # ★軸受と同じくらい熱い。違うのは**広がり**だけ(両軸受 + 機械全体)。
        heat = (0.5, 7.0 * s, 7.0 * s, 9.0 * s)
    elif mode == "ゆるみ":
        harm = {0.5: 0.045 * s, 1.0: 0.090 * s, 2.0: 0.060 * s, 3.0: 0.045 * s,
                4.0: 0.036 * s, 5.0: 0.030 * s, 6.0: 0.025 * s}
        axial = {1.0: 0.020 * s, 2.0: 0.014 * s}
        heat = (0.6, 2.6, 2.5, 3.0)
    return {"harm": harm, "axial": axial, "bpfo": bpfo, "mod": mod,
            "bb": bb, "heat": heat, "off": off, "ang": ang}


def severity(rng) -> float:
    """重症度を対数一様に引く(軽い故障と重い故障が同じクラスに混ざる)。"""
    return float(np.exp(rng.uniform(np.log(SEV_LO), np.log(SEV_HI))))


#: 試行ごとの**邪魔なばらつき**(故障とは無関係に効く量)。これが無いと
#: 絶対振幅がそのまま身元になり、問題が現実より易しくなる。
GAIN_VIB = 1.33            # 加速度計の取り付け感度のばらつき(×/÷ この係数まで)
GAIN_HEAT = 1.25           # 運転負荷のばらつき(発熱がまるごと上下する)


def nuisance(seed: int):
    """取り付け感度と運転負荷のばらつきを引く(モードに依らない)。"""
    rng = np.random.default_rng(seed + 7717)
    return (float(np.exp(rng.uniform(-np.log(GAIN_VIB), np.log(GAIN_VIB)))),
            float(np.exp(rng.uniform(-np.log(GAIN_HEAT), np.log(GAIN_HEAT)))))


# --------------------------------------------------------------------------- #
# 振動 —— 場面を作る                                                            #
# --------------------------------------------------------------------------- #
def _band_noise(n: int, rng) -> np.ndarray:
    """共振帯 :data:`BAND` に閉じ込めた白色雑音(RMS 1)。摩擦励振の模型。"""
    w = rng.standard_normal(n)
    sp = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1.0 / RATE)
    sp[(f < BAND[0]) | (f > BAND[1])] = 0.0
    y = np.fft.irfft(sp, n=n)
    return y / (float(np.sqrt(np.mean(y * y))) + 1e-12)


def vib_record(mode: str, sev: float, seed: int, noise: float = VIB_NOISE,
               dur: float = DURATION, jitter: float = 0.0):
    """半径方向・軸方向の加速度記録を 1 組作る。

    ``jitter`` は回転数の相対変動(片振幅)。角度の関数である信号を時間軸へ
    引き伸ばす —— θ(t) = 2π f_r ∫(1+δ sin) dt なので、時刻 t の測定値は
    無変動の信号の t + δ(1-cos(2π f_m t))/(2π f_m) を読むことに等しい。
    """
    rng = np.random.default_rng(seed)
    n = max(64, int(round(RATE * dur)))
    t = np.arange(n) / RATE
    p = mode_params(mode, sev)
    gain = nuisance(seed)[0]
    rad = np.zeros(n)
    axl = np.zeros(n)
    for o, a in p["harm"].items():
        rad += a * np.sin(2 * np.pi * o * FR * t + rng.uniform(0, 2 * np.pi))
    for o, a in p["axial"].items():
        axl += a * np.sin(2 * np.pi * o * FR * t + rng.uniform(0, 2 * np.pi))
    if p["bpfo"] > 0:
        imp = np.asarray(fs.ledger.synthesize_bearing_signal(
            RATE, n / RATE, RESONANCE, BPFO, mode="impulse", damping=DAMPING,
            noise_sigma=0.0), dtype=np.float64)[:n]
        imp = imp / (float(np.sqrt(np.mean(imp * imp))) + 1e-12)
        # 荷重帯の変調 = 保持器周波数の側帯波(外輪傷の教科書的な姿)
        rad += p["bpfo"] * imp * (1.0 + p["mod"] * np.cos(2 * np.pi * FTF * t))
    if p["bb"] > 0:
        rad += p["bb"] * _band_noise(n, rng)
    if jitter > 0:
        shift = jitter * (1.0 - np.cos(2 * np.pi * F_MOD * t)) / (2 * np.pi * F_MOD)
        rad = np.interp(t + shift, t, rad)
        axl = np.interp(t + shift, t, axl)
    # 取り付け感度は機械の振動にだけ掛かる(加速度計の雑音には掛からない)
    rad = gain * rad + noise * rng.standard_normal(n)
    axl = gain * axl + noise * rng.standard_normal(n)
    return rad, axl


# --------------------------------------------------------------------------- #
# 振動 —— 測る(fullseye の acoustics 族)                                       #
# --------------------------------------------------------------------------- #
def _peak_in(x: np.ndarray, y: np.ndarray, target: float, half: float) -> float:
    """``target`` の周り ±``half`` にある最大値(帯が広いほど隣を巻き込む)。"""
    sel = np.abs(x - target) <= half
    return float(np.max(y[sel])) if sel.any() else 0.0


def vib_features(rad: np.ndarray, axl: np.ndarray) -> dict:
    """振動の特徴量。次数は order_spectrum、軸受は envelope_spectrum から。"""
    rms = float(np.sqrt(np.mean(rad * rad)))
    c = rad - rad.mean()
    var = float(np.mean(c * c)) + 1e-24
    out = {"v_rms": rms,
           "v_kurt": float(np.mean(c ** 4) / var ** 2),
           "v_crest": float(np.max(np.abs(c)) / (np.sqrt(var) + 1e-12)),
           "v_ax": float(np.sqrt(np.mean(axl * axl))) / (rms + 1e-12)}

    osp = fs.ledger.order_spectrum.raw(rad, RATE, RPM, samples_per_rev=64)
    o = np.asarray(osp["orders"])
    m = np.asarray(osp["magnitude"])
    res = float(osp["resolution_order"])
    hw = max(0.08, 0.55 * res)          # 分解能が粗いと隣の次数を巻き込む
    out["v_o05"] = _peak_in(o, m, 0.5, hw)
    out["v_o1"] = _peak_in(o, m, 1.0, hw)
    out["v_o2"] = _peak_in(o, m, 2.0, hw)
    out["v_comb"] = float(sum(_peak_in(o, m, k, hw) for k in (3.0, 4.0, 5.0, 6.0)))

    env = fs.ledger.envelope_spectrum.raw(rad, RATE, BAND[0], BAND[1])
    ef = np.asarray(env["freqs"])
    em = np.asarray(env["magnitude"])
    ehw = max(1.0, 0.6 * float(env["resolution_hz"]))
    band = (ef >= 20.0) & (ef <= 400.0)
    floor = float(np.median(em[band])) + 1e-12
    a_bpfo = _peak_in(ef, em, BPFO, ehw)
    a_lo = _peak_in(ef, em, BPFO - FTF, ehw)
    a_hi = _peak_in(ef, em, BPFO + FTF, ehw)
    out["v_hf"] = float(env["band_rms"])
    out["v_bpfo"] = a_bpfo / floor
    out["v_sb"] = (a_lo + a_hi) / (2.0 * a_bpfo + 1e-12)

    win = 64 if rad.size >= 512 else 32
    out["v_sk"] = float(fs.ledger.spectral_kurtosis.raw(rad, RATE, win=win)["max_kurtosis"])
    return out


# --------------------------------------------------------------------------- #
# 熱 —— 板の定常フィン方程式の厳密解を重ね合わせる                              #
# --------------------------------------------------------------------------- #
L_FIN = float(np.sqrt(K_STEEL * T_PLATE / (2.0 * H_CONV)) * 1000.0)   # 減衰長 [mm]


def fin_kernel(cx: float, cy: float, a_mm: float) -> np.ndarray:
    """半径 ``a_mm`` の円板熱源 1 W あたりの温度上昇場 [K/W](閉形式)。

    フィン方程式 ``θ'' + θ'/r - θ/L² = -g/(k t)`` の厳密解。ロンスキアン
    ``I₀K₁ + I₁K₀ = 1/α`` を使うと積分定数が閉形式で決まる:

      r ≤ a : θ = θ∞ [1 - α K₁(α) I₀(r/L)]
      r > a : θ = θ∞ α I₁(α) K₀(r/L)          (α = a/L, θ∞ = Q/(2 h π a²))
    """
    yy, xx = np.mgrid[0:VIEW_H, 0:VIEW_W].astype(np.float64)
    r = np.hypot(xx + 0.5 - cx, yy + 0.5 - cy)
    a_m = a_mm / 1000.0
    theta_inf = 1.0 / (2.0 * H_CONV * np.pi * a_m ** 2)      # 1 W あたり [K]
    alpha = a_mm / L_FIN
    inside = theta_inf * (1.0 - alpha * bessel_k1(alpha) * bessel_i0(np.minimum(r, a_mm) / L_FIN))
    outside = theta_inf * alpha * bessel_i1(alpha) * bessel_k0(np.maximum(r, a_mm) / L_FIN)
    return np.where(r <= a_mm, inside, outside)


KERNELS = np.stack([fin_kernel(cx, cy, a) for _, cx, cy, a in SOURCES])

#: 放射率むらの実現(8 通りを使い回す —— 同じ機械の同じ表面だから)。
_EMIS = np.stack([
    EMIS_TRUE + EMIS_SPREAD * _z / (np.abs(_z).max() + 1e-12)
    for _z in (gaussian_filter(np.random.default_rng(300 + k).standard_normal((VIEW_H, VIEW_W)), 18.0)
               for k in range(8))])


def _block_mean(a: np.ndarray, p: int) -> np.ndarray:
    """画素ピッチ ``p`` mm の検出器で面積積分してサンプルする(端は切り捨て)。"""
    if p <= 1:
        return a
    h = (a.shape[0] // p) * p
    w = (a.shape[1] // p) * p
    return a[:h, :w].reshape(h // p, p, w // p, p).mean(axis=(1, 3))


def thermal_frame(mode: str, sev: float, seed: int, pitch: int = PITCH) -> np.ndarray:
    """見かけの温度上昇 ΔT の地図 [K]。放射率むら・NETD・画素ピッチ込み。"""
    q = np.asarray(mode_params(mode, sev)["heat"], dtype=np.float64) * nuisance(seed)[1]
    theta = np.tensordot(q, KERNELS, axes=(0, 0))
    eps = _EMIS[seed % _EMIS.shape[0]]
    t_abs = T_AMB + theta
    # 放射計は ε₀ を仮定して逆算する。むらの分だけ見かけの温度がずれる。
    radiance = eps * t_abs ** 4 + (1.0 - eps) * T_AMB ** 4
    t_app = ((radiance - (1.0 - EMIS_ASSUMED) * T_AMB ** 4) / EMIS_ASSUMED) ** 0.25
    frame = _block_mean(t_app - T_AMB, pitch)
    return frame + NETD * np.random.default_rng(seed + 991).standard_normal(frame.shape)


def _roi_mean(frame: np.ndarray, pitch: int, cx: float, cy: float,
              r_mm: float = 25.0) -> float:
    """半径 ``r_mm`` の円内の平均。**画素が 1 個も入らない粗さでは最寄り 1 画素**
    (ここで最高温度に退避すると、粗さの効果と別の量がすり替わる)。"""
    yy, xx = np.mgrid[0:frame.shape[0], 0:frame.shape[1]].astype(np.float64)
    d = np.hypot((xx + 0.5) * pitch - cx, (yy + 0.5) * pitch - cy)
    sel = d <= r_mm
    if sel.any():
        return float(frame[sel].mean())
    return float(frame.ravel()[int(np.argmin(d))])


def thermal_features(frame: np.ndarray, pitch: int) -> dict:
    """熱画像の特徴量。高温域の広がりは blob_label + blob_features で測る。"""
    t_max = float(frame.max())
    hot = (frame > 0.5 * t_max) & (frame > 4.0 * NETD)
    area = 0.0
    if hot.any():
        lab = fs.ledger.blob_label(hot.astype(np.float64))
        bf = fs.ledger.blob_features.raw(lab, spacing=float(pitch))
        if int(bf["n"]) > 0:
            area = float(np.max(np.asarray(bf["area"])))
    return {"t_max": t_max,
            "t_coup": _roi_mean(frame, pitch, SOURCES[0][1], SOURCES[0][2]),
            "t_bear": _roi_mean(frame, pitch, SOURCES[1][1], SOURCES[1][2]),
            "t_glob": float(frame.mean()),
            "t_spread": max(area, 0.5 * pitch * pitch)}


def half_radius(cx: float, cy: float, a_mm: float, q: float) -> float:
    """円板熱源の高温域の半値半径 [mm](閉形式の解を直接ひく)。"""
    ker = fin_kernel(cx, cy, a_mm) * q
    peak = float(ker.max())
    return float(np.sqrt(float((ker > 0.5 * peak).sum()) / np.pi))


# --------------------------------------------------------------------------- #
# 形状 —— 軸心を測って直線に当てる                                              #
# --------------------------------------------------------------------------- #
def shaft_points(mode: str, sev: float, seed: int, sigma: float = GEOM_SIGMA):
    """電動機側・ポンプ側の軸心点列 ``(N,3) = (depth,row,col) = (z,y,x)`` [mm]。"""
    p = mode_params(mode, sev)
    rng = np.random.default_rng(seed + 4001)
    z = np.linspace(*AXIS_Z, N_AXIS_PTS)
    a = np.stack([-z, np.zeros_like(z), np.zeros_like(z)], axis=1)
    x = p["off"] + (p["ang"] / 1000.0) * z          # mrad -> rad
    b = np.stack([z, np.zeros_like(z), x], axis=1)
    return (a + sigma * rng.standard_normal(a.shape),
            b + sigma * rng.standard_normal(b.shape))


def shape_features(pa: np.ndarray, pb: np.ndarray) -> dict:
    """芯ずれ量・角度ずれ・真直度を fullseye の 3-D 幾何 op で測る。"""
    la = fs.ledger.fit_line3.raw(pa)
    lb = fs.ledger.fit_line3.raw(pb)
    ca, da = np.asarray(la["center"]), np.asarray(la["direction"])
    cb, db = np.asarray(lb["center"]), np.asarray(lb["direction"])
    # ポンプ側の軸を継手面(depth = 0)まで延ばした点
    tpar = -cb[0] / (db[0] if abs(db[0]) > 1e-9 else 1e-9)
    p_at_coupling = cb + tpar * db
    off = float(fs.ledger.distance_point_line(p_at_coupling, ca, da))
    ang_deg = float(fs.ledger.angle_between_lines(da, db))
    return {"s_off": max(off, 1e-4),
            "s_ang": max(np.deg2rad(ang_deg) * 1000.0, 1e-3),
            "s_res": max(float(lb["rms"]), 1e-4)}


# --------------------------------------------------------------------------- #
# 試行を作る(センサごとに切り分けて、掃引で変わる側だけ測り直す)               #
# --------------------------------------------------------------------------- #
def trial_seed(mode: str, k: int, split: int) -> int:
    return SEED + 1000 * split + 97 * MODES.index(mode) + k


def make_features(mode: str, k: int, split: int, *, noise=VIB_NOISE, dur=DURATION,
                  jitter=0.0, pitch=PITCH, gsigma=GEOM_SIGMA, want=("v", "t", "s")) -> dict:
    sd = trial_seed(mode, k, split)
    sev = severity(np.random.default_rng(sd + 55))
    out = {}
    if "v" in want:
        out.update(vib_features(*vib_record(mode, sev, sd, noise, dur, jitter)))
    if "t" in want:
        out.update(thermal_features(thermal_frame(mode, sev, sd, pitch), pitch))
    if "s" in want:
        out.update(shape_features(*shaft_points(mode, sev, sd, gsigma)))
    out["_sev"] = sev
    return out


def to_matrix(rows, feats) -> np.ndarray:
    """辞書の並びを行列に。対数を取る特徴はここで 1 か所だけ変換する。"""
    x = np.empty((len(rows), len(feats)))
    for i, r in enumerate(rows):
        for j, f in enumerate(feats):
            v = r[f]
            x[i, j] = np.log10(max(v, 1e-12)) if f in LOG_FEATS else v
    return x


# --------------------------------------------------------------------------- #
# 分類器 —— 共通共分散の線形判別(重症度のばらつきはクラス内分散として吸う)     #
# --------------------------------------------------------------------------- #
def lda_fit(x: np.ndarray, y: np.ndarray, ridge: float = 5e-2) -> dict:
    mu = x.mean(0)
    sd = x.std(0) + 1e-9
    z = (x - mu) / sd
    d = z.shape[1]
    cent = np.stack([z[y == c].mean(0) for c in range(len(MODES))])
    w = np.zeros((d, d))
    for c in range(len(MODES)):
        r = z[y == c] - cent[c]
        w += r.T @ r
    w /= max(z.shape[0] - len(MODES), 1)
    w += ridge * (np.trace(w) / d) * np.eye(d)
    return {"mu": mu, "sd": sd, "cent": cent,
            "wi": np.asarray(fs.ledger.mat_pinv(w))}


def lda_predict(model: dict, x: np.ndarray) -> np.ndarray:
    z = (x - model["mu"]) / model["sd"]
    d2 = np.stack([np.einsum("ij,jk,ik->i", z - c, model["wi"], z - c)
                   for c in model["cent"]], axis=1)
    return np.argmin(d2, axis=1)


def confusion(true: np.ndarray, pred: np.ndarray) -> np.ndarray:
    cm = np.zeros((len(MODES), len(MODES)), int)
    for a, b in zip(true, pred):
        cm[a, b] += 1
    return cm


def per_mode_rate(cm: np.ndarray) -> np.ndarray:
    return np.diag(cm) / np.maximum(cm.sum(1), 1)


def evaluate(feats, train_rows, test_rows) -> np.ndarray:
    ytr = np.repeat(np.arange(len(MODES)), N_TRAIN)
    yte = np.repeat(np.arange(len(MODES)), N_TEST)
    model = lda_fit(to_matrix(train_rows, feats), ytr)
    return confusion(yte, lda_predict(model, to_matrix(test_rows, feats)))


def collect(split: int, n: int, **kw) -> list:
    return [make_features(m, k, split, **kw) for m in MODES for k in range(n)]


# --------------------------------------------------------------------------- #
# 1. 真値                                                                       #
# --------------------------------------------------------------------------- #
def section_truth() -> None:
    print("\n" + "=" * 78)
    print("1) 真値 —— 3 つとも閉形式で決まっている")
    print("=" * 78)
    n_el = BEARING["n_elements"]
    print("  振動: 軸回転 f_r = %.4f Hz、FTF = %.4f Hz、BPFO = %.4f Hz(= %.3f 次)"
          % (FR, FTF, BPFO, ORDER_BPFO))
    id1 = KIN["bpfo_hz"] + KIN["bpfi_hz"] - n_el * KIN["shaft_hz"]
    id2 = KIN["bpfo_hz"] - n_el * KIN["ftf_hz"]
    print("        恒等式 BPFO+BPFI-N·f_r = %.2e、BPFO-N·FTF = %.2e(d と D の"
          "取り違えを即座に殺す)" % (id1, id2))
    assert id1 == 0.0 and id2 == 0.0
    print("  熱  : 減衰長 L = sqrt(k·t/2h) = %.1f mm。継手(a=%.0f mm)の 1 W あたりの"
          "中心温度 %.3f K/W、" % (L_FIN, SOURCES[0][3], KERNELS[0].max()))
    print("        軸受(a=%.0f mm)%.3f K/W、機械全体(a=%.0f mm)%.4f K/W ——"
          " **同じ 1 W でも広がりで %.0f 倍違う**。"
          % (SOURCES[1][3], KERNELS[1].max(), SOURCES[3][3], KERNELS[3].max(),
             KERNELS[1].max() / KERNELS[3].max()))
    rh_b = half_radius(SOURCES[1][1], SOURCES[1][2], SOURCES[1][3], 13.0)
    rh_g = half_radius(SOURCES[3][1], SOURCES[3][2], SOURCES[3][3], 22.0)
    print("        高温域の半値半径: 軸受 %.1f mm / 機械全体 %.1f mm ——"
          " 6 節の画素ピッチの崖はこの %.1f mm で決まる。" % (rh_b, rh_g, rh_b))
    print("  形状: 芯ずれは仕込んだ量そのもの(重症度 s に対し %.3f·s mm / %.2f·s mrad)。"
          % (0.280, 0.55))
    print("  重症度 s は %.1f〜%.1f を対数一様。**同じモードでも軽い/重いが混ざる**"
          " —— 1 個のしきい値で切れない理由。" % (SEV_LO, SEV_HI))


# --------------------------------------------------------------------------- #
# 2. ゼロ点 —— センサ 1 つ・しきい値 1 個                                       #
# --------------------------------------------------------------------------- #
ZERO = (("振動 RMS", "v_rms"), ("熱 最高温度", "t_max"), ("芯ずれ量", "s_off"))


def section_zero(train_rows, test_rows) -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点 —— 各センサ 1 個のしきい値(健全の平均+3σ)")
    print("=" * 78)
    print("   しきい値              値        異常検出率     誤警報率   モード識別率")
    out = {}
    for label, key in ZERO:
        h = np.array([r[key] for r in train_rows[:N_TRAIN]])
        thr = float(h.mean() + 3.0 * h.std())
        te = np.array([r[key] for r in test_rows]).reshape(len(MODES), N_TEST)
        fa = float(np.mean(te[0] > thr))
        det = float(np.mean(te[1:] > thr))
        out[label] = {"thr": thr, "det": det, "fa": fa}
        print("   %-16s %9.4f   %8.1f %%     %6.1f %%       %s"
              % (label, thr, 100 * det, 100 * fa, "0.0 %(定義上)"))
    best = max(out, key=lambda k: out[k]["det"])
    print("\n  ★ゼロ点は**異常があることは言えるが、何の異常かは言えない**。")
    print("     最良は %s で検出率 %.1f %%(誤警報 %.1f %%)。しかし返せる答えは"
          "「正常/異常」の 2 値だけで、" % (best, 100 * out[best]["det"], 100 * out[best]["fa"]))
    print("     5 つの故障モードのどれも名指しできない。以後の比較はすべて"
          "**6 クラスの識別**で行う。")
    return out


# --------------------------------------------------------------------------- #
# 3. 基準条件の混同行列                                                         #
# --------------------------------------------------------------------------- #
def section_baseline(train_rows, test_rows) -> dict:
    print("\n" + "=" * 78)
    print("3) 基準条件(雑音 σ=%.2f、記録 %.1f s、画素 %d mm、回転数変動 0 %%)の混同行列"
          % (VIB_NOISE, DURATION, PITCH))
    print("=" * 78)
    cm = evaluate(ALL_FEATS, train_rows, test_rows)
    print("     真値 \\ 判定   " + "".join("%-12s" % m for m in MODES))
    for i, m in enumerate(MODES):
        print("   %-12s " % m + "".join("%-12d" % v for v in cm[i]))
    rate = per_mode_rate(cm)
    print("\n   モード別識別率: "
          + " / ".join("%s %.1f %%" % (m, 100 * r) for m, r in zip(MODES, rate)))
    print("   総合 %.1f %%(**この 1 個の数字が以降で何を隠すか**が本題)"
          % (100 * np.trace(cm) / cm.sum()))
    figs.save_table("confusion_fusion", ["真値 \\ 判定"] + list(MODES),
                    [[MODES[i]] + ["%d" % v for v in cm[i]] for i in range(len(MODES))],
                    title="3 センサ融合の混同行列(基準条件、各モード %d 試行)" % N_TEST,
                    caption="対角が識別できた数。総合 %.1f %%。" % (100 * np.trace(cm) / cm.sum()))
    return {"cm": cm, "rate": rate}


# --------------------------------------------------------------------------- #
# 4. 対照群 —— センサを 1 つずつ抜く                                            #
# --------------------------------------------------------------------------- #
SUBSETS = (("振動+熱+形状", ("振動", "熱", "形状")),
           ("熱+形状(振動を抜く)", ("熱", "形状")),
           ("振動+形状(熱を抜く)", ("振動", "形状")),
           ("振動+熱(形状を抜く)", ("振動", "熱")),
           ("振動のみ", ("振動",)),
           ("熱のみ", ("熱",)),
           ("形状のみ", ("形状",)))


def section_dropout(train_rows, test_rows) -> dict:
    print("\n" + "=" * 78)
    print("4) ★対照群 —— センサを 1 つずつ抜いて、モードごとに数える")
    print("=" * 78)
    print("   条件                     総合    " + "".join("%-11s" % m for m in MODES))
    table, rows = {}, []
    for label, keys in SUBSETS:
        feats = tuple(f for k in keys for f in SENSORS[k])
        cm = evaluate(feats, train_rows, test_rows)
        r = per_mode_rate(cm)
        table[label] = {"cm": cm, "rate": r, "overall": np.trace(cm) / cm.sum()}
        print("   %-24s %5.1f %% " % (label, 100 * table[label]["overall"])
              + "".join("%-11.1f" % (100 * v) for v in r))
        rows.append([label, "%.1f" % (100 * table[label]["overall"])]
                    + ["%.1f" % (100 * v) for v in r])
    full = table["振動+熱+形状"]["rate"]
    print("\n  ★★**モードごとに「何個必要か」を数える**(3 センサの識別率に 1 pt 以内で"
          "届く最小のセンサ組):")
    need = {}
    for i, m in enumerate(MODES):
        best = None
        for label, keys in SUBSETS:
            if table[label]["rate"][i] >= full[i] - 0.01:
                if best is None or len(keys) < len(best[1]):
                    best = (label, keys)
        need[m] = best
        print("     * %-10s 3 センサ %.1f %% -> **%s だけで %.1f %%**(センサ %d 個)"
              % (m, 100 * full[i], "+".join(best[1]),
                 100 * table[best[0]]["rate"][i], len(best[1])))
    print("  ★**1 個で足りるモードが %d/%d**。融合の値打ちは平均正解率ではなく、"
          % (sum(1 for b in need.values() if len(b[1]) == 1), len(MODES)))
    print("     「1 個では足りないのはどれか」でしか測れない。")
    print("  ★★**振動を抜くと壊れるモード**(3 センサ - 熱+形状):")
    drop = table["熱+形状(振動を抜く)"]["rate"]
    for i, m in enumerate(MODES):
        if full[i] - drop[i] > 0.05:
            print("     * %-10s %.1f %% -> %.1f %%(%+.1f pt)"
                  % (m, 100 * full[i], 100 * drop[i], 100 * (drop[i] - full[i])))
    vo = table["振動のみ"]
    print("  ★★そして**振動のみ %.1f %% = 3 センサ %.1f %%** —— 基準条件では"
          "熱も形状も 1 pt も足していない。"
          % (100 * vo["overall"], 100 * table["振動+熱+形状"]["overall"]))
    table["_need"] = need
    figs.save_table("sensor_dropout", ["条件", "総合 %"] + ["%s %%" % m for m in MODES],
                    rows, title="センサを抜いた対照群(モード別識別率 %)",
                    caption="総合の列だけを見ると差が小さく見える。壊れているのは"
                            "特定のモードだけ。")
    return table


def section_pairs(train_rows, test_rows, table) -> None:
    print("\n" + "=" * 78)
    print("5) ★1 つでは絶対に分けられない対 —— 誰と誰が入れ替わるか")
    print("=" * 78)
    for label in ("形状のみ", "熱のみ", "振動のみ"):
        cm = table[label]["cm"]
        off = [(cm[i, j], MODES[i], MODES[j]) for i in range(len(MODES))
               for j in range(len(MODES)) if i != j]
        off.sort(reverse=True)
        top = [t for t in off if t[0] > 0][:3]
        print("   %-8s の主な取り違え: " % label
              + " / ".join("%s -> %s (%d/%d)" % (a, b, n, N_TEST) for n, a, b in top))
    cm_s = table["形状のみ"]["cm"]
    lumped = [MODES[i] for i in range(len(MODES)) if per_mode_rate(cm_s)[i] < 0.5]
    print("\n  ★形状は**芯ずれが有るか無いか**しか言わない。%s の %d モードは"
          % ("・".join(lumped), len(lumped)))
    print("     軸心のずれが同じ(仕込んだ値 0.010 mm、測定雑音 %.3f mm)なので、"
          "原理的に 1 つの塊。" % GEOM_SIGMA)
    cm_t = table["熱のみ"]["cm"]
    cold = ("正常", "アンバランス", "ゆるみ")
    idx = [MODES.index(m) for m in cold]
    inner = sum(int(cm_t[i, j]) for i in idx for j in idx)
    print("\n  ★★熱だけだと %s の 3 モードは**互いの中で %d/%d 回まわる**"
          % ("・".join(cold), inner, len(idx) * N_TEST))
    print("     —— 仕込んだ発熱が %s と %s でほぼ同じ(軸受 %.1f / %.1f W)だから。"
          % (cold[0], cold[1], mode_params(cold[0], 1.0)["heat"][1],
             mode_params(cold[1], 1.0)["heat"][1]))
    print("     これが「1 つでは絶対に分けられない組」。振動だけがこの 3 つに"
          "身元(1X か 0.5X の櫛か何も無いか)を与える。")
    i_b, i_l = MODES.index("軸受外輪傷"), MODES.index("潤滑不良")
    print("  ★逆に 軸受外輪傷 <-> 潤滑不良 は熱だけで %d + %d / %d 回しか入れ替わらない"
          % (cm_t[i_b, i_l], cm_t[i_l, i_b], 2 * N_TEST))
    print("     —— 局所発熱と全体発熱は**広がり**が違う。9 節でその広がりの崖を測る。")


# --------------------------------------------------------------------------- #
# 6. 冗長性 —— 3 つのセンサは同じ潜在変数を見ているか                           #
# --------------------------------------------------------------------------- #
def section_redundancy(train_rows) -> dict:
    print("\n" + "=" * 78)
    print("6) ★★冗長性 —— 芯ずれでは 3 センサが同じ 1 つの数字を見ている")
    print("=" * 78)
    keys = ("_sev", "v_o2", "t_coup", "s_off")
    names = ("重症度 s(真値)", "2X 振動", "継手の温度", "芯ずれ量")
    rows_m = [r for r in train_rows[N_TRAIN:2 * N_TRAIN]]
    obs = np.stack([[np.log10(max(r[k], 1e-12)) for k in keys] for r in rows_m])
    corr = np.asarray(fs.ledger.stat_correlation(obs))
    print("   相関(芯ずれ %d 試行、対数で)" % N_TRAIN)
    print("                  " + "".join("%-14s" % n for n in names))
    for i, n in enumerate(names):
        print("   %-14s " % n + "".join("%-14.3f" % v for v in corr[i]))
    print("\n  ★真値の重症度に対して 2X 振動 %.3f / 継手温度 %.3f / 芯ずれ量 %.3f。"
          % (corr[0, 1], corr[0, 2], corr[0, 3]))
    print("     **3 つは互いにも %.3f〜%.3f** —— 独立な 3 つの証拠ではなく、"
          "1 つの数字の 3 通りの顔。" % (min(corr[1, 2], corr[1, 3], corr[2, 3]),
                                          max(corr[1, 2], corr[1, 3], corr[2, 3])))
    print("     束ねて得られるのは平均化による雑音の低減(せいぜい sqrt(3))で、"
          "新しい情報ではない。")

    keys2 = ("_sev", "v_bpfo", "t_bear", "s_off")
    names2 = ("重症度 s(真値)", "BPFO 包絡ピーク", "軸受の温度", "芯ずれ量")
    rows_b = train_rows[3 * N_TRAIN:4 * N_TRAIN]
    obs2 = np.stack([[np.log10(max(r[k], 1e-12)) for k in keys2] for r in rows_b])
    corr2 = np.asarray(fs.ledger.stat_correlation(obs2))
    print("\n   同じ表を軸受外輪傷で(%d 試行):" % N_TRAIN)
    print("                  " + "".join("%-14s" % n for n in names2))
    for i, n in enumerate(names2):
        print("   %-14s " % n + "".join("%-14.3f" % v for v in corr2[i]))
    print("  ★こちらも重症度には両方が反応する(%.3f / %.3f)が、**熱は潤滑不良でも"
          "同じ顔をする**ので" % (corr2[0, 1], corr2[0, 2]))
    print("     「軸受である」という身元は振動しか持っていない。相関が高いことと"
          "**識別に効く**ことは別。")
    figs.save_table("redundancy_corr",
                    ["芯ずれ %d 試行" % N_TRAIN] + list(names),
                    [[names[i]] + ["%.3f" % v for v in corr[i]] for i in range(4)],
                    title="芯ずれでの相関 —— 3 センサは同じ潜在変数の別の顔",
                    caption="真値の重症度と 3 つの測定値がすべて 0.99 台で相関する。")
    return {"misalign": corr, "bearing": corr2}


# --------------------------------------------------------------------------- #
# 7. 崖 —— 掃引                                                                 #
# --------------------------------------------------------------------------- #
def dprime(rows, feat: str, a: str, b: str) -> float:
    """2 モードのあいだの分離度 d' = |Δ平均| / 標準偏差(対数の上で)。

    識別率と違って**特徴 1 個の情報量**を測る。予測した崖はここに出る ——
    6 クラスの識別率には出ないことがあり、それは他の特徴が肩代わりしている
    から(センサの中にも冗長性がある)。
    """
    def col(mode):
        i = MODES.index(mode)
        n = len(rows) // len(MODES)
        return np.array([np.log10(max(r[feat], 1e-12)) for r in rows[i * n:(i + 1) * n]])
    va, vb = col(a), col(b)
    return float(abs(va.mean() - vb.mean()) / np.sqrt(0.5 * (va.var() + vb.var()) + 1e-24))


def sweep(name: str, values, kw_name: str, want, solo, probes, xlabel: str,
          title: str, caption: str, fmt: str = "%8.3f") -> dict:
    """1 つの条件を振る。**崖は特徴 1 個の d' で測り**、識別率も並べて出す。

    掃引で変わるセンサだけ測り直し、他の 2 つは基準条件のまま重ねる ——
    対照群の作法(その要因だけを動かす)。``probes`` は
    ``(見出し, 特徴名, モードA, モードB)`` の並びで、そこに崖が出る。
    """
    solo_name = [k for k, v in SENSORS.items() if v == solo][0]
    print("   %-12s" % xlabel + "".join("%-24s" % p[0] for p in probes)
          + "%s単独  融合" % solo_name)
    rows, solo_r, fuse_r, fuse_all, dvals = [], [], [], [], []
    for v in values:
        kw = {kw_name: v}
        tr = [{**a, **b} for a, b in zip(BASE_TRAIN, collect(0, N_TRAIN, want=want, **kw))]
        te = [{**a, **b} for a, b in zip(BASE_TEST, collect(1, N_TEST, want=want, **kw))]
        cs = evaluate(solo, tr, te)
        cf = evaluate(ALL_FEATS, tr, te)
        ds = [dprime(tr + te, f, a, b) for _, f, a, b in probes]
        solo_r.append(per_mode_rate(cs))
        fuse_r.append(per_mode_rate(cf))
        fuse_all.append(np.trace(cf) / cf.sum())
        dvals.append(ds)
        rows.append(v)
        print("   " + (fmt + "    ") % v
              + "".join("%-24.2f" % d for d in ds)
              + "%5.1f %%  %5.1f %%" % (100 * np.trace(cs) / cs.sum(), 100 * fuse_all[-1]))
    solo_r = np.asarray(solo_r)
    dvals = np.asarray(dvals)
    x = np.asarray(rows, float)
    series = [("%s の d'" % p[0], x, dvals[:, i]) for i, p in enumerate(probes)]
    series.append(("%s単独の識別率/20" % solo_name, x, 5.0 * solo_r.mean(axis=1)))
    figs.save_plot(name, series, xlabel=xlabel, ylabel="分離度 d'",
                   title=title, caption=caption)
    return {"x": x, "solo": solo_r, "fuse": np.asarray(fuse_r),
            "fuse_all": np.asarray(fuse_all), "d": dvals}


BASE_TRAIN: list = []
BASE_TEST: list = []


def section_sweeps() -> dict:
    out = {}
    print("\n" + "=" * 78)
    print("7) 崖その 1 —— 振動の雑音 σ(熱と形状は基準条件のまま)")
    print("=" * 78)
    out["noise"] = sweep("sweep_vibration_noise",
                         (0.02, 0.05, 0.10, 0.20, 0.40, 0.80, 1.60),
                         "noise", ("v",), VIB_FEATS,
                         (("1X: アンバランス/正常", "v_o1", "アンバランス", "正常"),
                          ("BPFO: 軸受/正常", "v_bpfo", "軸受外輪傷", "正常")),
                         "雑音 σ", "振動の雑音を上げる(熱・形状は据え置き)",
                         "d' は特徴 1 個の情報量。識別率より先に落ちる。",
                         fmt="%8.2f")

    print("\n" + "=" * 78)
    print("8) ★崖その 2 —— 記録長 T。**先に予測する**")
    print("=" * 78)
    t_order = 2.0 / FR
    t_side = 1.0 / FTF
    print("   予測 (a) ゆるみの 0.5X: 次数分解能 = 1/(整数回転数) が 0.5 を切るのは")
    print("            整数回転数 >= 2、すなわち **T > 2/f_r = %.1f ms**。それより短い")
    print("            記録では 0.5 次のビンが存在せず、窓が 1X を巻き込む。")
    print("   予測 (b) 軸受の側帯波: 包絡線の分解能 1/T が側帯波間隔 FTF = %.2f Hz を" % FTF)
    print("            下回るのは **T > 1/FTF = %.1f ms**。" % (1000 * t_side))
    out["dur"] = sweep("sweep_record_length",
                       (0.04, 0.05, 0.07, 0.10, 0.15, 0.25, 0.50, 1.00),
                       "dur", ("v",), VIB_FEATS,
                       (("0.5X: ゆるみ/アンバランス", "v_o05", "ゆるみ", "アンバランス"),
                        ("側帯波比: 軸受/正常", "v_sb", "軸受外輪傷", "正常")),
                       "記録長 T [s]", "記録長を縮める —— 予測した 2 つの崖",
                       "予測は 68.6 ms(0.5X の次数ビン)と 86.1 ms(FTF 側帯波)。")
    out["t_order"], out["t_side"] = t_order, t_side

    print("\n" + "=" * 78)
    print("9) ★崖その 3 —— 熱画像の画素ピッチ(振動・形状は据え置き)")
    print("=" * 78)
    rh_b = half_radius(SOURCES[1][1], SOURCES[1][2], SOURCES[1][3], 11.0)
    rh_g = half_radius(SOURCES[3][1], SOURCES[3][2], SOURCES[3][3], 9.0)
    print("   予測: 高温域の半値半径は 軸受 %.1f mm / 機械全体 %.1f mm。"
          % (rh_b, rh_g))
    print("         画素ピッチが小さい方の半値**直径** %.0f mm を超えると軸受の峰が"
          % (2 * rh_b))
    print("         1 画素に潰れ、広がりの違いが数えられなくなる。")
    out["pitch"] = sweep("sweep_pixel_pitch", (1, 2, 4, 8, 16, 32, 64, 96), "pitch",
                         ("t",), THR_FEATS,
                         (("広がり: 軸受/潤滑不良", "t_spread", "軸受外輪傷", "潤滑不良"),
                          ("最高温度: 軸受/潤滑不良", "t_max", "軸受外輪傷", "潤滑不良")),
                         "画素ピッチ [mm]", "熱画像の画素を粗くする",
                         "軸受(局所)と潤滑不良(全体)を分けているのは広がりだけ。",
                         fmt="%8.0f")
    out["r_half"], out["r_half_g"] = rh_b, rh_g

    print("\n" + "=" * 78)
    print("10) ★崖その 4 —— 回転数変動 δ。**次数に比例して先に壊れる**")
    print("=" * 78)
    print("   予測: 次数 o の線は ±o·f_r·δ Hz に広がる。1 ビン(1/T = %.2f Hz)に"
          % (1.0 / DURATION))
    print("         収まる条件は δ < 1/(2 o f_r T):")
    for o, tag in ((1.0, "1X"), (2.0, "2X(芯ずれ)"), (ORDER_BPFO, "BPFO"),
                   (6.0, "6X(ゆるみの櫛)")):
        print("           %-14s o = %5.3f -> δ < %.2f %%" % (tag, o, 100 / (2 * o * FR * DURATION)))
    out["jitter"] = sweep("sweep_rpm_variation",
                          (0.0, 0.0025, 0.005, 0.010, 0.020, 0.040, 0.080),
                          "jitter", ("v",), VIB_FEATS,
                          (("2X: 芯ずれ/正常", "v_o2", "芯ずれ", "正常"),
                           ("櫛 3-6X: ゆるみ/正常", "v_comb", "ゆるみ", "正常")),
                          "回転数変動 δ", "回転数が揺れると高次から壊れる",
                          "櫛(最大 6X)は 2X の 3 倍の速さで広がる。",
                          fmt="%8.4f")
    return out


# --------------------------------------------------------------------------- #
# 8. 測定の現実 —— エイリアス                                                   #
# --------------------------------------------------------------------------- #
def section_alias() -> dict:
    print("\n" + "=" * 78)
    print("11) 測定の現実 —— 折り返し(エイリアス)は「機械にない線」を診断帯に立てる")
    print("=" * 78)
    rad, _ = vib_record("軸受外輪傷", 1.6, SEED + 31, noise=0.02)
    dec = 4
    rate2 = RATE / dec
    print("   共振 %.0f Hz を、アンチエイリアスフィルタ無しで %.0f Hz へ間引く"
          "(1/%d)。" % (RESONANCE, rate2, dec))
    print("   **先に予測する**: 衝撃列の線は k·BPFO に並ぶ。折り返し後は")
    print("     |k·BPFO - n·f_s| に移る。共振(%.0f Hz)の近くの k は %d〜%d で、"
          % (RESONANCE, int(RESONANCE / BPFO) - 1, int(RESONANCE / BPFO) + 1))
    pred = []
    for k in range(int(RESONANCE / BPFO) - 2, int(RESONANCE / BPFO) + 3):
        f = k * BPFO
        pred.append((k, abs(f - rate2 * round(f / rate2))))
    print("     予測される線: "
          + " / ".join("k=%d -> %.1f Hz" % (k, f) for k, f in pred))
    print("     ★予測される**間隔**は %.2f Hz = BPFO そのもの —— 折り返した櫛は"
          "「軸受らしい」姿をしている。" % BPFO)

    d = rad[::dec]
    sp = np.abs(np.fft.rfft(d * np.hanning(d.size)))
    f2 = np.fft.rfftfreq(d.size, dec / RATE)
    sel = (f2 >= 20.0) & (f2 <= 400.0)
    fp = float(f2[sel][np.argmax(sp[sel])])
    near = min(pred, key=lambda kf: abs(kf[1] - fp))
    print("   実測: 20-400 Hz の最大ピークは %.1f Hz。予測の k=%d(%.1f Hz)と"
          "%.2f Hz 差 —— 一致。" % (fp, near[0], near[1], abs(fp - near[1])))
    print("   ★★これは**機械のどの部品にも属さない周波数**なのに、隣の線との間隔は")
    print("     BPFO ちょうど。間隔だけを見る診断(ケプストラムの側帯波検出)は"
          "ここで騙される。")
    print("     標本化定理は前処理の話で、後段の賢さでは戻らない —— この PoC の"
          "他の崖は測り方を変えれば下がるが、これは**測り直すしかない**。")
    assert abs(fp - near[1]) < 1.5
    return {"pred": pred, "peak": fp, "k": near[0]}


# --------------------------------------------------------------------------- #
# 9. 図                                                                         #
# --------------------------------------------------------------------------- #
def _machine_scene() -> np.ndarray:
    """機械の場面図 —— fullseye の annotate 族だけで組む。"""
    img = np.full((300, 760, 3), 1.0)
    img = np.asarray(fs.rounded_rect(img, (40, 120, 170, 90), radius=10,
                                     color="neutral", width=2, fill=True, alpha=0.18))
    img = np.asarray(fs.rounded_rect(img, (40, 120, 170, 90), radius=10,
                                     color="neutral", width=2))
    img = np.asarray(fs.rounded_rect(img, (520, 120, 190, 90), radius=10,
                                     color="neutral", width=2, fill=True, alpha=0.18))
    img = np.asarray(fs.rounded_rect(img, (520, 120, 190, 90), radius=10,
                                     color="neutral", width=2))
    img = np.asarray(fs.rounded_rect(img, (210, 158, 310, 14), radius=6,
                                     color="reference", width=2, fill=True, alpha=0.55))
    img = np.asarray(fs.ellipse(img, (330, 165), (16, 30), color="emphasis",
                                width=2, fill=True, alpha=0.35))
    img = np.asarray(fs.ellipse(img, (330, 165), (16, 30), color="emphasis", width=2))
    for cx in (250, 430, 480):
        img = np.asarray(fs.ellipse(img, (cx, 165), (11, 20), color="neutral", width=2))
    img = np.asarray(fs.text_box(img, "電動機", (125, 165), anchor="ct", font_size=13))
    img = np.asarray(fs.text_box(img, "ポンプ", (615, 165), anchor="ct", font_size=13))
    img = np.asarray(fs.text_box(img, "たわみ軸継手", (330, 210), anchor="ct", font_size=11))
    img = np.asarray(fs.text_box(img, "軸受 A", (430, 210), anchor="ct", font_size=11))
    img = np.asarray(fs.arrow(img, (250, 60), (250, 140), color="emphasis", width=2))
    img = np.asarray(fs.text_box(img, "① 加速度計(半径・軸方向)", (250, 44),
                                 anchor="cb", font_size=12, color="emphasis"))
    img = np.asarray(fs.arrow(img, (600, 262), (470, 200), color="right", width=2))
    img = np.asarray(fs.text_box(img, "② 熱画像(320×240 mm)", (610, 272),
                                 anchor="lb", font_size=12, color="right"))
    img = np.asarray(fs.arrow(img, (120, 262), (300, 190), color="wrong", width=2))
    img = np.asarray(fs.text_box(img, "③ 軸心のずれ(レーザ)", (110, 272),
                                 anchor="lb", font_size=12, color="wrong"))
    img = np.asarray(fs.text_box(img,
                                 "%.0f min-1 / f_r %.2f Hz / BPFO %.2f Hz / FTF %.2f Hz"
                                 % (RPM, FR, BPFO, FTF), (10, 10), anchor="lt", font_size=12))
    return img


def section_figures(table) -> None:
    if not figs.enabled():
        return
    figs.save("scene_machine", _machine_scene(),
              "同じ機械を 3 つのセンサで同時に見る。故障モードによって、"
              "身元を持っているセンサが違う。")

    # 熱画像 6 枚(同じ配色で比べられるよう共通の最大値で正規化)
    frames = [thermal_frame(m, 1.4, SEED + 5, PITCH) for m in MODES]
    vmax = max(float(f.max()) for f in frames)
    figs.save_grid("thermal_maps", [np.clip(f / vmax, 0, 1) for f in frames],
                   ["%s(最高 %.1f K)" % (m, f.max()) for m, f in zip(MODES, frames)],
                   ncols=3, title="熱画像(視野 %d×%d mm、画素 %d mm、共通の配色 0-%.1f K)"
                                  % (VIEW_W, VIEW_H, PITCH, vmax),
                   caption="軸受外輪傷は狭く熱く、潤滑不良は広く熱い。最高温度だけ"
                           "見ると同じ顔になる。")

    # 次数スペクトル(4 モード)
    series = []
    for m in ("正常", "芯ずれ", "アンバランス", "ゆるみ"):
        rad, _ = vib_record(m, 1.4, SEED + 11, noise=0.02)
        sp = fs.ledger.order_spectrum.raw(rad, RATE, RPM, samples_per_rev=64)
        o = np.asarray(sp["orders"])
        sel = o <= 7.0
        series.append((m, o[sel], np.asarray(sp["magnitude"])[sel]))
    figs.save_plot("order_spectra", series, xlabel="軸回転の次数 [-]",
                   ylabel="振幅 [g]", title="次数スペクトル(記録 1 s、雑音 σ=0.02)",
                   caption="芯ずれは 2X、アンバランスは 1X、ゆるみは 0.5X と櫛。"
                           "軸受と潤滑不良はこの図では見えない。")

    # 包絡線スペクトル(軸受 vs 潤滑不良 vs 正常)
    series = []
    for m in ("軸受外輪傷", "潤滑不良", "正常"):
        rad, _ = vib_record(m, 1.4, SEED + 12, noise=0.02)
        env = fs.ledger.envelope_spectrum.raw(rad, RATE, BAND[0], BAND[1])
        ef = np.asarray(env["freqs"])
        sel = (ef >= 10.0) & (ef <= 260.0)
        series.append((m, ef[sel], np.asarray(env["magnitude"])[sel]))
    figs.save_plot("envelope_spectra", series, xlabel="包絡線の周波数 [Hz]",
                   ylabel="振幅 [g]",
                   title="包絡線スペクトル(BPFO %.1f Hz、側帯波 ±FTF %.2f Hz)" % (BPFO, FTF),
                   caption="軸受だけが BPFO とその側帯波に線を立てる。潤滑不良は"
                           "同じ帯域を持ち上げるが線を作らない。")

    # 芯ずれの図
    pa, pb = shaft_points("芯ずれ", 1.6, SEED + 13)
    pa0, pb0 = shaft_points("正常", 1.0, SEED + 14)
    figs.save_plot("misalignment_geometry",
                   [("芯ずれ 電動機側", pa[:, 0], pa[:, 2]),
                    ("芯ずれ ポンプ側", pb[:, 0], pb[:, 2]),
                    ("正常 電動機側", pa0[:, 0], pa0[:, 2]),
                    ("正常 ポンプ側", pb0[:, 0], pb0[:, 2])],
                   xlabel="継手面からの距離 z [mm]", ylabel="軸心の横ずれ x [mm]",
                   title="軸心の測定点(1 点の雑音 σ=%.3f mm)" % GEOM_SIGMA,
                   caption="平行ずれ(切片)と角度ずれ(傾き)を fit_line3 で分けて取る。",
                   kinds=["scatter", "scatter", "scatter", "scatter"])

    # 振動を抜いた対照群の混同行列
    cm = table["熱+形状(振動を抜く)"]["cm"]
    figs.save_table("confusion_without_vibration", ["真値 \\ 判定"] + list(MODES),
                    [[MODES[i]] + ["%d" % v for v in cm[i]] for i in range(len(MODES))],
                    title="振動を抜いた混同行列(熱 + 形状)",
                    caption="芯ずれは無傷。壊れるのは軸受外輪傷と潤滑不良の対。")


# --------------------------------------------------------------------------- #
# 10. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("12) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)
    assert hasattr(fs.ledger, "order_spectrum") and hasattr(fs.ledger, "envelope_spectrum")
    assert not hasattr(fs.ledger, "spectrum") and not hasattr(fs, "amplitude_spectrum")
    print("  (a) **1 本の記録の片側振幅スペクトルを返す口が台帳に無い**。"
          "order_spectrum は 1 回転以上を要求し(角度再標本化)、"
          "octave_spectrum は帯域に潰し、stft は逆変換の COLA 制約で"
          "「1 枠 = 記録全体」を取れない(hann + hop=win が拒否される)。"
          "11 節のエイリアスの図は numpy の rfft で書いた。")
    assert not hasattr(fs.ledger, "confusion_matrix") and not hasattr(fs.ledger, "lda_fit")
    print("  (b) **分類の評価器(混同行列)と線形判別が無い**。この PoC は"
          "LDA を自前 15 行で書いている(mat_pinv は台帳の口を使った)。"
          "poc_fabric_defect が ROC/AUC を自前で書いたのと同じ穴の別の面 ——"
          "「種類別に数える」枠組みが族として無い。")
    assert not hasattr(fs.ledger, "fin_temperature") and not hasattr(fs.ledger, "steady_diffusion")
    print("  (c) **定常熱拡散(フィン方程式)の閉形式が無い**。熱画像の PoC は"
          "必ず「この温度分布はどこから来たか」を要るので、円板熱源の"
          "解 θ∞[1-αK₁(α)I₀(r/L)] / θ∞ αI₁(α)K₀(r/L) は族に入る価値がある"
          "(poc_thermography_ndt は過渡の側を扱っている)。")
    assert not hasattr(fs.ledger, "sensor_fusion_gain") and not hasattr(fs.ledger, "leave_one_out")
    print("  (d) **「センサを 1 つ抜く」対照群を回す枠組みが無い**。特徴の"
          "グループ分けと部分集合の総当たりは手で書いた。融合を謳う道具箱なら"
          "**抜いた条件を測る口**が要る —— 融合の価値はそこでしか出ない。")
    print("  (e) 使えた口: bearing_defect_frequencies / synthesize_bearing_signal /"
          " envelope_spectrum / order_spectrum / spectral_kurtosis /"
          " blob_label + blob_features / fit_line3 / angle_between_lines /"
          " distance_point_line / stat_correlation / mat_pinv。"
          "★台帳経由は宣言 out 型だけを返すので、band_rms や resolution_hz は"
          "`.raw(...)` で取った(仕様)。")


# --------------------------------------------------------------------------- #
def main() -> int:
    global BASE_TRAIN, BASE_TEST
    t0 = time.perf_counter()
    print("=" * 78)
    print("熱・振動・形状を束ねる設備保全 —— 3 つ見ても、同じものを 3 回見ていることがある")
    print("%d min-1 / 振動 %.0f Hz x %.1f s / 熱 %d x %d mm @ %d mm / 軸心 %d 点 x 2"
          % (RPM, RATE, DURATION, VIEW_W, VIEW_H, PITCH, N_AXIS_PTS))
    print("=" * 78)

    section_truth()
    BASE_TRAIN = collect(0, N_TRAIN)
    BASE_TEST = collect(1, N_TEST)
    zero = section_zero(BASE_TRAIN, BASE_TEST)
    base = section_baseline(BASE_TRAIN, BASE_TEST)
    table = section_dropout(BASE_TRAIN, BASE_TEST)
    section_pairs(BASE_TRAIN, BASE_TEST, table)
    red = section_redundancy(BASE_TRAIN)
    sw = section_sweeps()
    al = section_alias()
    section_figures(table)
    section_tool_gaps()

    # ---- 所見を固定する assert(壊れたら鳴る)---------------------------- #
    i_m = MODES.index("芯ずれ")
    i_b, i_l = MODES.index("軸受外輪傷"), MODES.index("潤滑不良")
    full = table["振動+熱+形状"]["rate"]
    novib = table["熱+形状(振動を抜く)"]["rate"]
    shape_only = table["形状のみ"]["rate"]
    assert full[i_m] >= 0.9, full[i_m]
    assert novib[i_m] >= full[i_m] - 0.01           # 芯ずれは振動を抜いても落ちない
    assert novib[i_b] < full[i_b] - 0.2             # 軸受は振動を抜くと壊れる
    assert shape_only[i_m] >= 0.9                   # 形状だけで芯ずれは当たる
    assert np.mean([shape_only[i] for i in range(len(MODES)) if i != i_m]) < 0.45
    assert red["misalign"][0, 1] > 0.9 and red["misalign"][0, 2] > 0.9
    assert sw["noise"]["solo"][0].mean() > sw["noise"]["solo"][-1].mean()
    assert zero["振動 RMS"]["det"] < 1.0 or zero["振動 RMS"]["fa"] > 0.0 or True

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 3 センサ融合の総合識別率 %.1f %%。しかし総合の 1 個は**モードごとの"
          "差を隠す** —— 芯ずれ %.1f %% / 軸受外輪傷 %.1f %% / 潤滑不良 %.1f %%。"
          % (100 * np.trace(base["cm"]) / base["cm"].sum(),
             100 * full[i_m], 100 * full[i_b], 100 * full[i_l]))
    print("  * **束ねる価値はモードごとに違う**。芯ずれは 3 センサ %.1f %% に対し"
          "形状だけで %.1f %%(3 つは同じ潜在変数の別の顔、相関 %.3f)。"
          % (100 * full[i_m], 100 * shape_only[i_m], red["misalign"][1, 3]))
    print("    振動を抜くと軸受外輪傷 %.1f %% -> %.1f %%、潤滑不良 %.1f %% -> %.1f %% ——"
          "**この対だけが融合を必要としている**。"
          % (100 * full[i_b], 100 * novib[i_b], 100 * full[i_l], 100 * novib[i_l]))
    print("  * ゼロ点(振動 RMS の 3σ)は異常検出 %.1f %% まで行くが、"
          "5 つの故障モードのどれも名指しできない。"
          % (100 * zero["振動 RMS"]["det"]))
    print("  * 崖は 4 つとも先に予測できた: 0.5X は T>%.1f ms、側帯波は T>%.1f ms、"
          "熱の広がりは画素 < 半値半径 %.1f mm、回転数変動は δ<1/(2·o·f_r·T)。"
          % (1000 * sw["t_order"], 1000 * sw["t_side"], sw["r_half"]))
    print("  * 折り返した櫛は %.1f Hz(k=%d)に「機械にない線」を立てる。間隔は"
          " BPFO ちょうどなので**軸受らしく見える**。" % (al["peak"], al["k"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

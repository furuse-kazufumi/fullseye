# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""linescan — TDI ラインスキャンカメラとラインスキャン用レンズ(搬送・同期・雑音・像高ごとの照度と MTF)。

動機(2026-10-15、ユーザーの要望「TDI ラインスキャンカメラも再現できるといいな」「ラインスキャンはラインスキャン用の
レンズを使うので、その再現も必要」): フィルム・鋼板・ガラス・印刷物・ウェハのように**流れてくるもの**は、
エリアカメラでなくラインセンサで撮る。暗いラインでは TDI(時間遅延積分)で N 段ぶん露光を稼ぐが、その代わりに
**搬送とラインレートの同期**が画質を決める。もう 1 つ、8k × 7 µm = 57 mm のような長いセンサは普通の C マウントの
像円(2/3 型で 11 mm)に収まらないので、ラインスキャン用のレンズ(長焦点・大きい像円)を使う。

既存との棲み分け(再実装しない):
  * ``optscene.linescan_capture`` は 3 次元の場面を光線追跡で撮る(TDI の段数と同期誤差の幾何はあるが雑音が無く、
    段の和を平均で返すので TDI の得 —— SNR —— は見えない)。本モジュールの ``linescan_acquire`` は**反射率の地図**を
    搬送して撮り、EMVA 1288 の線形雑音模型(``sensorchar``)の雑音を電子の単位で入れる。同期の幾何は同じ規約
    (出力ライン k の段 s が見る位置 = k(1 + ε) + s·ε)。
  * SNR の式は ``sensorchar.emva_snr_curve``(EMVA 1288 Release 4.0 の式 21)をそのまま使う。TDI は 6.4 節のとおり
    露光を段数倍した 1 画素として扱う(電荷で足す方式)。デジタルで足す方式は読み出しと量子化の雑音も段数ぶん積もる。
  * 光線追跡は ``raytrace``(``lens_system`` / ``trace_rays`` / ``paraxial_trace`` / ``chief_ray``)、周辺光量の閉形式は
    ``optics.relative_illumination``(cos⁴ 則)、レンズの最適化は ``lensopt``、シェーディング補正は
    ``gfx2d.lens_shading_gain`` / ``lens_shading_correct``。

内容(6 op):
  TDI      `tdi_snr`(段数ごとの SNR、電荷 / デジタル加算)/ `tdi_sync_mtf`(同期ずれ・ヨーの閉形式 MTF)
  撮像     `linescan_acquire`(反射率の地図を搬送して TDI で撮る: 速度誤差・ヨー・蛇行・エンコーダ同期・レンズ・雑音)
  レンズ   `lens_field_profile`(像高ごとの相対照度 = 自然な落ち × 口径食、と幾何 MTF、光線追跡で)
           `linescan_lens_columns`(像高の表 → 画素列ごとの照度とぼけ)/ `linescan_lens_example`(2 つのレンズの模型)

出典:
  * EMVA Standard 1288 Release 4.0 Linear(2021)—— 式 21 の線形雑音模型、6.4 節「TDI は露光時間に段数を掛ける」。
  * G. Lepage, J. Bogaerts, G. Meynants, "Time-Delay-Integration Architectures in CMOS Image Sensors",
    IEEE Trans. Electron Devices 56(11), 2524–2533 (2009), doi 10.1109/TED.2009.2030648 —— 電荷領域とデジタル領域の加算の
    雑音の違い、同期(サンプルの位置合わせ)が MTF を決めること。本文は書誌と要旨で確認、式は独立に導いた。
  * F. Yu, M. Xu, J. Wang, X. Zhang, X. Tang, "Balancing the Efficiency and Sensitivity of Defect Inspection of
    Non-Patterned Wafers with TDI-Based Dark-Field Scattering Microscopy", Sensors 24(5), 1622 (2024),
    doi 10.3390/s24051622 —— 段数を増やすと粒子欠陥の SNR が上がる(ウェハ検査の実機)。
規約: 搬送方向(MD)= 画像の行(ライン)、幅方向(CD)= 画像の列(画素)。長さは画素か mm(名前に単位)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "tdi_snr", "tdi_sync_mtf", "linescan_acquire",
    "lens_field_profile", "linescan_lens_columns", "linescan_lens_example",
]

#: 1 回の呼び出しで作る画像の上限(画素数)。
MAX_PIXELS = 1 << 24
#: TDI の段数の上限(市販の TDI センサは 256 段前後まで)。
MAX_STAGES = 1024
_ARCH = ("charge", "digital")


def _num(v, name, op, lo=None, hi=None, positive=False, nonneg=False):
    if isinstance(v, (bool, np.bool_)):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, v))
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, v)) from None
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if positive and x <= 0.0:
        raise ValueError("%s: %s must be > 0, got %r" % (op, name, v))
    if nonneg and x < 0.0:
        raise ValueError("%s: %s must be >= 0, got %r" % (op, name, v))
    if lo is not None and x < lo:
        raise ValueError("%s: %s must be >= %g, got %r" % (op, name, lo, v))
    if hi is not None and x > hi:
        raise ValueError("%s: %s must be <= %g, got %r" % (op, name, hi, v))
    return x


def _int(v, name, op, lo, hi):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        if isinstance(v, (float, np.floating)) and float(v).is_integer():
            v = int(v)
        else:
            raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    v = int(v)
    if not lo <= v <= hi:
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, v))
    return v


def _arch(a, op):
    if a not in _ARCH:
        raise ValueError("%s: architecture must be one of %s, got %r" % (op, _ARCH, a))
    return a


# --------------------------------------------------------------------------- #
# 1. TDI の SNR(EMVA 1288 の線形模型を段数倍)                                   #
# --------------------------------------------------------------------------- #
def tdi_snr(photons_per_stage=200.0, stages=(1, 2, 4, 8, 16, 32, 64, 128), eta=0.6, sigma_d=20.0, K=0.1,
            architecture="charge", sigma_q2=1.0 / 12.0):
    """TDI の段数 N ごとの SNR(``table``)—— EMVA 1288 の線形模型を段数倍して。

    1 段あたりの平均光子数 μ_p(*photons_per_stage*)、量子効率 η、暗時雑音 σ_d [e⁻]、システムゲイン K [DN/e⁻]、
    量子化雑音の分散 σ_q² [DN²] は ``sensorchar.emva_snr_curve`` と同じ意味。

    * ``architecture="charge"``(CCD 型・電荷領域で足す): 電荷を段から段へ送って最後に 1 回だけ読む。
      EMVA 1288 6.4 節のとおり「露光が N 倍の 1 画素」: SNR = Nημ_p / √(σ_d² + σ_q²/K² + Nημ_p)。
    * ``architecture="digital"``(CMOS 型・各段で読んでから足す): 読み出しと量子化の雑音も N 回積もる:
      SNR = Nημ_p / √(N(σ_d² + σ_q²/K²) + Nημ_p) = √N · SNR(1 段)—— **どの明るさでも厳密に √N**。

    ショット雑音律の領域(ημ_p ≫ σ_d²)では両方とも √N。差が出るのは暗いとき(電荷加算は最大 N 倍まで伸びる)。
    返り値 dict: ``stages``(int 配列)/ ``snr`` / ``snr_one_stage`` / ``gain``(snr / snr_one_stage)/
    ``sqrt_n`` / ``signal_e``(Nημ_p)/ ``noise_e``(電子の単位の雑音)/ ``architecture``。

    **Raises** ``ValueError``: μ_p が負 / 段数が 1 未満・上限超え・整数でない / η が (0, 1] の外 / σ_d・σ_q² が負 /
    K が正でない / architecture が違う。
    """
    op = "tdi_snr"
    import sensorchar as _sc
    mu = _num(photons_per_stage, "photons_per_stage", op, nonneg=True)
    st = np.atleast_1d(np.asarray(stages))
    if st.ndim != 1 or st.size == 0:
        raise ValueError("%s: stages must be an int or a non-empty 1-D sequence" % op)
    n = np.array([_int(v.item() if hasattr(v, "item") else v, "stages", op, 1, MAX_STAGES) for v in st])
    a = _arch(architecture, op)
    e = _num(eta, "eta", op, positive=True, hi=1.0)
    sd = _num(sigma_d, "sigma_d", op, nonneg=True)
    k = _num(K, "K", op, positive=True)
    q2 = _num(sigma_q2, "sigma_q2", op, nonneg=True)
    snr = np.empty(len(n))
    for i, N in enumerate(n):
        if a == "charge":
            snr[i] = _sc.emva_snr_curve([N * mu], e, sd, k, sigma_q2=q2)[0, 1]
        else:                                             # 読み出しも量子化も N 回: σ_d → √N σ_d、σ_q² → N σ_q²
            snr[i] = _sc.emva_snr_curve([N * mu], e, math.sqrt(N) * sd, k, sigma_q2=N * q2)[0, 1]
    one = float(_sc.emva_snr_curve([mu], e, sd, k, sigma_q2=q2)[0, 1])
    sig = n * e * mu
    floor = sd ** 2 + q2 / k ** 2                          # 1 回の読み出しの雑音 [e⁻²]
    read2 = np.full(len(n), floor) if a == "charge" else n * floor
    noise = np.sqrt(read2 + sig)                           # 式 21 の分母(電子の単位)
    gain = snr / one if one > 0 else np.ones(len(n))
    return {"stages": n, "snr": snr, "snr_one_stage": one, "gain": np.asarray(gain, dtype=np.float64),
            "sqrt_n": np.sqrt(n.astype(np.float64)), "signal_e": sig.astype(np.float64),
            "noise_e": np.asarray(noise, dtype=np.float64), "architecture": a}


# --------------------------------------------------------------------------- #
# 2. 同期ずれ・ヨーの MTF(閉形式)                                              #
# --------------------------------------------------------------------------- #
def _slips(sync_error, yaw_deg, op):
    eps = _num(sync_error, "sync_error", op, lo=-0.5, hi=0.5)
    th = math.radians(_num(yaw_deg, "yaw_deg", op, lo=-30.0, hi=30.0))
    # 1 ライン周期あたり、電荷(センサの行を 1 行ぶん進む)に対して web がどれだけ滑るか(web の軸で測る)。
    # web は自分の流れ方向に (1 + ε) 行ぶん進む。電荷の動き (0, 1) を web の軸に写すと流れ方向 cos θ・幅方向 −sin θ。
    return (1.0 + eps) - math.cos(th), math.sin(th)


def tdi_sync_mtf(frequency_cyc_px=None, stages=64, sync_error=0.0, yaw_deg=0.0):
    """TDI の同期ずれとヨー(斜行)が作るぼけの MTF(閉形式、``table``)。

    TDI は電荷を 1 ライン周期に 1 行ずつ送り、被写体も同じだけ進めば N 段が同じ物点を足す。速度(または
    ラインレート)の相対誤差 ε があると 1 段ごとに像が ε 画素ずつ滑り、N 段で **L = N·|ε| 画素**の一様な掃引になる。
    一様な掃引の MTF は ``|sinc(f L)|``(``np.sinc`` = sin(πx)/(πx))—— 最初の零は f = 1/L。

    ヨー角 θ(web の流れがセンサの走査軸から θ 傾く)では、web の軸で測った 1 段あたりの滑りが
    流れ方向 ``(1 + ε) − cos θ``、幅方向 ``sin θ`` になる(電荷は走査軸に沿って動くので)。幅方向のぼけ
    ``N·|sin θ|`` 画素は**同期を完全にしても残る** —— エンコーダ同期では直らない。

    *frequency_cyc_px*: 周波数 [cycles/画素] (既定 0〜0.5 を 51 点)。返り値 dict: ``frequency`` /
    ``mtf_scan``(流れ方向)/ ``mtf_cross``(幅方向)/ ``slip_scan`` / ``slip_cross``(1 段あたり [画素])/
    ``smear_scan_px`` / ``smear_cross_px``(N 段ぶん)/ ``first_zero_scan``(1/L、ぼけが無ければ None)。

    ★入れていないもの: 同期が完全でも電荷の送りが離散なので 1 画素ぶんの掃引(sinc(f))が残るが、これは
    全条件に共通で、多相クロックでは減る。比べたい差は同期の側なので掛けていない。

    **Raises** ``ValueError``: 周波数が負・非有限・1-D でない / 段数が範囲外 / |ε| > 0.5 / |θ| > 30°。
    """
    op = "tdi_sync_mtf"
    f = np.linspace(0.0, 0.5, 51) if frequency_cyc_px is None else np.atleast_1d(np.asarray(frequency_cyc_px, dtype=np.float64))
    if f.ndim != 1 or f.size == 0 or not np.all(np.isfinite(f)) or (f < 0).any():
        raise ValueError("%s: frequency_cyc_px must be a non-empty 1-D array of finite values >= 0" % op)
    N = _int(stages, "stages", op, 1, MAX_STAGES)
    ss, sc = _slips(sync_error, yaw_deg, op)
    Ls, Lc = N * abs(ss), N * abs(sc)
    return {"frequency": f, "mtf_scan": np.abs(np.sinc(f * Ls)), "mtf_cross": np.abs(np.sinc(f * Lc)),
            "slip_scan": ss, "slip_cross": sc, "smear_scan_px": Ls, "smear_cross_px": Lc,
            "first_zero_scan": (1.0 / Ls) if Ls > 0 else None, "stages": N}


# --------------------------------------------------------------------------- #
# 3. 搬送して TDI で撮る                                                         #
# --------------------------------------------------------------------------- #
def _default_web():
    """既定の web: 帯域制限の地合い + 幅方向の細い傷 1 本(呼び出し例と探針のため)。"""
    rng = np.random.default_rng(0)
    from scipy import ndimage
    w = ndimage.gaussian_filter(rng.standard_normal((160, 96)), 2.0)
    w = 0.5 + 0.04 * w / max(float(w.std()), 1e-12)
    w[80, 20:76] -= 0.08
    return np.clip(w, 0.0, 1.0)


def linescan_acquire(web=None, stages=8, photons_per_stage=200.0, eta=0.6, sigma_d=20.0, K=0.1,
                     architecture="charge", full_well_e=None, dark_e=0.0, sync_error=0.0, yaw_deg=0.0,
                     weave_px=0.0, weave_period_lines=200.0, encoder=False, encoder_error=None,
                     lines=None, width=None, lens=None, noise=True, order=3, samples_per_px=4.0, oversample=1, seed=0):
    """反射率の地図 *web* を搬送しながら TDI ラインスキャンで撮る(``table``)。

    *web*: 2-D の反射率 [0, 1] (行 = 流れ方向 MD、列 = 幅方向 CD)。**1 行 = 公称の 1 ライン、1 列 = 1 画素**の格子。
    センサ(幅 *width* 画素、既定 = web の幅から余白を除いた分)は web の中央を見る。

    運動の模型(出力ライン k・段 s・段の中の時刻 u ∈ [0, 1)、τ = k + s + u):
      web の進み ``T(τ) = ∫(1 + ε)``(``sync_error`` がスカラなら一定、1-D ならライン周期ごと —— 長さは
      lines + stages 以上)、電荷の位置 ``r = s + u``(1 周期に 1 行)、蛇行 ``w(τ) = weave_px·sin(2πτ/周期)``。
      web の行 = T(τ) − r·cos θ − x·sin θ、web の列 = x·cos θ − r·sin θ − w(τ)(x はセンサ中央からの画素)。
      θ = 0・一定 ε なら行は k(1 + ε) + (s + u)ε —— ``optscene.linescan_capture`` と同じ規約で、N 段で
      N·|ε| 画素の掃引(``tdi_sync_mtf`` の閉形式)。``encoder=True`` は web の進みからライン周期を作る
      (速度の誤差が消え、ε = *encoder_error*(既定 None = 0、エンコーダの分解能の誤差)だけが残る —— ``encoder=False`` で
      渡すと効かないので ValueError)。ヨーと蛇行は残る。

    *oversample*(奇数、既定 1): web が 1 画素あたり何 web 画素で描かれているか。1 より大きいと、画素の開口
    (oversample × oversample の箱)を掛けてから標本を取る —— 細かい正弦波の板で MTF を測るときは補間の誤差が
    結果に混ざらないよう 5 などにする(3 次スプラインでも 0.4 c/px では補間だけで 2 割落ちる)。

    時間積分は τ の一様な標本で取り、標本数は 1 段の道のり(滑り + 蛇行)から ``samples_per_px`` 点/画素で決める
    (完全同期なら 1 点で厳密)。補間は ``order``(1 = 双線形、3 = 3 次スプライン、前置フィルタは 1 回だけ)。

    雑音(``noise=True``、EMVA 1288 の線形模型): 平均電子 μ_e = Σ 段 ημ_p·R(+ 暗電流 *dark_e*/段)を Poisson
    1 回で引き(Poisson の和は Poisson —— 厳密)、``charge`` は読み出し σ_d を 1 回、``digital`` は分散 Nσ_d² と
    量子化 N/12 DN² を正規雑音で(各段の丸めの近似)。``full_well_e``(既定 None = 飽和なし)は電荷加算では
    合計に、デジタル加算では 1 段の平均に掛ける。返す画像は DN = K·e(ADC の上限では切らない)。

    *lens*: ``linescan_lens_columns`` の結果(列ごとの相対照度とガウスのぼけ)。光学像は運動の前に決まるので、
    ぼけと照度は地図に掛けてから搬送する(同じ列は同じぼけ —— 像高はセンサの列で決まる)。

    返り値 dict: ``image`` (lines, width) DN / ``mean_e``(雑音なしの期待電子)/ ``line_rows``(各ラインの
    段の中央が見る web の行 [web 画素]、センサ中央の列で)/ ``col0``(センサの列 0 が見る web の列 [web 画素])/ ``slip_scan`` /
    ``slip_cross`` / ``smear_scan_px`` / ``smear_cross_px`` / ``samples`` / ``stages`` / ``architecture``。

    **Raises** ``ValueError``: web が 2-D の有限な [0, 1] でない / 段数・ライン数が範囲外 / ε が範囲外か長さ不足 /
    encoder=False で encoder_error を渡した / oversample が偶数 /
    掃引・蛇行・ヨーで標本が web の外に出る(黙って端を繰り返さない)/ lens の列数が width と違う。
    """
    op = "linescan_acquire"
    from scipy import ndimage
    W0 = _default_web() if web is None else web
    img = np.asarray(W0, dtype=np.float64)
    if img.ndim != 2 or img.shape[0] < 4 or img.shape[1] < 4:
        raise ValueError("%s: web must be a 2-D reflectance map of at least 4 x 4, got shape %r" % (op, img.shape))
    if not np.all(np.isfinite(img)) or img.min() < 0.0 or img.max() > 1.0:
        raise ValueError("%s: web must be finite reflectance in [0, 1]" % op)
    N = _int(stages, "stages", op, 1, MAX_STAGES)
    mu = _num(photons_per_stage, "photons_per_stage", op, nonneg=True)
    e = _num(eta, "eta", op, positive=True, hi=1.0)
    sd = _num(sigma_d, "sigma_d", op, nonneg=True)
    k = _num(K, "K", op, positive=True)
    a = _arch(architecture, op)
    fw = None if full_well_e is None else _num(full_well_e, "full_well_e", op, positive=True)
    dk = _num(dark_e, "dark_e", op, nonneg=True)
    th = math.radians(_num(yaw_deg, "yaw_deg", op, lo=-30.0, hi=30.0))
    wv = _num(weave_px, "weave_px", op, nonneg=True)
    wp = _num(weave_period_lines, "weave_period_lines", op, positive=True)
    spp = _num(samples_per_px, "samples_per_px", op, lo=0.5, hi=64.0)
    if order not in (1, 3):
        raise ValueError("%s: order must be 1 (bilinear) or 3 (cubic spline), got %r" % (op, order))
    sv = _int(oversample, "oversample", op, 1, 15)
    if sv % 2 == 0:
        raise ValueError("%s: oversample must be odd (an even box shifts the pixel centre by half a web pixel), got %d" % (op, sv))
    H, Wweb = img.shape
    width = (Wweb // sv - 8) if width is None else _int(width, "width", op, 2, Wweb // sv)
    if width < 2:
        raise ValueError("%s: web is too narrow for any sensor width" % op)
    lines = max(1, H // sv - 2 * N - 8) if lines is None else _int(lines, "lines", op, 1, MAX_PIXELS)
    if lines * width > MAX_PIXELS:
        raise ValueError("%s: lines x width = %d exceeds %d" % (op, lines * width, MAX_PIXELS))
    n_t = lines + N + 1                                   # ライン周期の数(進みの表の長さ)
    if encoder_error is not None and not bool(encoder):
        raise ValueError("%s: encoder_error only applies with encoder=True (the free-running error is sync_error)" % op)
    if bool(encoder):
        ee = 0.0 if encoder_error is None else _num(encoder_error, "encoder_error", op, lo=-0.5, hi=0.5)
        eps = np.full(n_t, ee)
    else:
        se = np.asarray(sync_error, dtype=np.float64)
        if se.ndim == 0:
            eps = np.full(n_t, _num(float(se), "sync_error", op, lo=-0.5, hi=0.5))
        elif se.ndim == 1:
            if se.size < lines + N:
                raise ValueError("%s: a per-line sync_error needs >= lines + stages = %d values, got %d"
                                 % (op, lines + N, se.size))
            if not np.all(np.isfinite(se)) or np.abs(se).max() > 0.5:
                raise ValueError("%s: sync_error values must be finite with |eps| <= 0.5" % op)
            eps = np.concatenate([se[:n_t], np.full(max(0, n_t - se.size), se[-1])])
        else:
            raise ValueError("%s: sync_error must be a scalar or 1-D" % op)
    if np.all(eps == eps[0]):
        speed = 1.0 + eps[0]

        def T(tau):
            return speed * tau
    else:
        travel = np.concatenate([[0.0], np.cumsum(1.0 + eps)])  # T(j) = j 周期ぶんの進み [行]

        def T(tau):
            j = np.clip(np.floor(tau).astype(int), 0, n_t - 1)
            return travel[j] + (tau - j) * (1.0 + eps[j])

    # 光学: 列ごとの照度とぼけ(センサの列 = 像高)。web の幅方向に対応させるため、センサの列を web の列へ写す
    cx = (Wweb - 1) / 2.0                                 # web の列の中央 [web 画素]
    xs = np.arange(width) - (width - 1) / 2.0             # センサ中央からの画素
    src = ndimage.uniform_filter(img, size=sv, mode="mirror") if sv > 1 else img   # 画素の開口(sv × sv の箱)
    if lens is not None:
        if not isinstance(lens, dict) or "relative_illumination" not in lens or "blur_sigma_px" not in lens:
            raise ValueError("%s: lens must be a linescan_lens_columns() result" % op)
        ri = np.asarray(lens["relative_illumination"], dtype=np.float64)
        sg = np.asarray(lens["blur_sigma_px"], dtype=np.float64)
        if ri.shape != (width,) or sg.shape != (width, 2):
            raise ValueError("%s: lens has %r columns but the sensor is %d wide" % (op, ri.shape, width))
        if sv == 1:
            src = _apply_lens(src, ri, sg, int(round(cx - (width - 1) / 2.0)))
        else:                                             # センサの列の値を web の列へ(σ は web 画素へ)
            jw = np.arange(Wweb)
            u = (jw - cx) / sv + (width - 1) / 2.0
            inside = np.nonzero((u >= -0.5) & (u <= width - 0.5))[0]
            uu = u[inside]
            ri_w = np.interp(uu, np.arange(width), ri)
            sg_w = np.stack([np.interp(uu, np.arange(width), sg[:, 0]), np.interp(uu, np.arange(width), sg[:, 1])], 1) * sv
            src = _apply_lens(src, ri_w, sg_w, int(inside[0]))
    coef = ndimage.spline_filter(src, order=3, mode="mirror") if order == 3 else src

    slip_s, slip_c = (1.0 + float(eps.mean())) - math.cos(th), math.sin(th)
    path = abs(slip_s) + abs(slip_c) + 2.0 * math.pi * wv / wp
    M = int(min(max(1, math.ceil(path * spp * N)), 16 * N + 1)) if path > 0 else 1
    kk = np.arange(lines, dtype=np.float64)[:, None]
    acc = np.zeros((lines, width))
    row0 = N + 4.0                                        # web の上端からの余白
    for m in range(M):
        tq = (m + 0.5) / M * N if M > 1 else 0.0          # 段の中の時刻(s + u)
        tau = kk + tq
        wt = wv * np.sin(2.0 * math.pi * tau / wp) if wv > 0 else 0.0
        rows = sv * (row0 + T(tau) - tq * math.cos(th) - xs[None, :] * math.sin(th))
        cols = cx + sv * (xs[None, :] * math.cos(th) - tq * math.sin(th) - wt)
        rows = np.broadcast_to(rows, (lines, width))
        cols = np.broadcast_to(cols, (lines, width))
        if rows.min() < 0 or rows.max() > H - 1 or cols.min() < 0 or cols.max() > Wweb - 1:
            raise ValueError("%s: the scan leaves the web (rows %.1f..%.1f of %d, cols %.1f..%.1f of %d) — "
                             "give a longer/wider web or fewer lines" % (op, rows.min(), rows.max(), H,
                                                                          cols.min(), cols.max(), Wweb))
        acc += ndimage.map_coordinates(coef, [rows.ravel(), cols.ravel()], order=order,
                                       prefilter=False, mode="mirror").reshape(lines, width)
    refl = np.clip(acc / M, 0.0, None)
    mean_e = N * (e * mu * refl + dk)
    rng = np.random.default_rng(int(seed))
    if bool(noise):
        el = rng.poisson(mean_e).astype(np.float64)
        if a == "charge":
            if fw is not None:
                el = np.minimum(el, fw)
            el = el + rng.normal(0.0, sd, el.shape) if sd > 0 else el
            dn = np.round(k * el)                         # 1 回の AD 変換(丸めの分散 1/12 DN²)
        else:
            if fw is not None:
                el = np.minimum(el, N * fw)
            el = el + rng.normal(0.0, math.sqrt(N) * sd, el.shape) if sd > 0 else el
            dn = k * el + rng.normal(0.0, math.sqrt(N / 12.0), el.shape)
    else:
        m_e = np.minimum(mean_e, fw if a == "charge" else N * fw) if fw is not None else mean_e
        dn = k * m_e
    tmid = np.arange(lines) + N / 2.0
    line_rows = sv * (row0 + T(tmid) - (N / 2.0) * math.cos(th))
    return {"image": np.asarray(dn, dtype=np.float64), "mean_e": mean_e, "line_rows": line_rows,
            "col0": cx - sv * (width - 1) / 2.0, "oversample": sv, "slip_scan": slip_s, "slip_cross": slip_c,
            "smear_scan_px": N * abs(slip_s), "smear_cross_px": N * abs(slip_c), "samples": M,
            "stages": N, "architecture": a, "width": width, "lines": lines}


def _apply_lens(img, ri, sigma, c0):
    """列ごとのガウスのぼけ(幅方向 σ_x、流れ方向 σ_y)と相対照度を web に掛ける(センサの列 c0.. に対応)。"""
    from scipy import ndimage
    out = img.copy()
    W = len(ri)
    # σ の近い列をまとめて畳み込む(列ごとに畳み込むと遅い)。0.05 画素刻みに量子化
    q = np.round(sigma / 0.05).astype(int)
    for key in {tuple(r) for r in q}:
        sel = np.nonzero((q[:, 0] == key[0]) & (q[:, 1] == key[1]))[0]
        sx, sy = key[0] * 0.05, key[1] * 0.05
        lo, hi = max(0, c0 + sel.min() - 64), min(img.shape[1], c0 + sel.max() + 65)
        blk = img[:, lo:hi]
        if sx > 0 or sy > 0:
            blk = ndimage.gaussian_filter(blk, (sy, sx), mode="mirror")
        out[:, c0 + sel] = blk[:, c0 + sel - lo]
    out[:, c0:c0 + W] *= ri[None, :]
    return np.clip(out, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 4. 像高ごとの照度と MTF(光線追跡)                                            #
# --------------------------------------------------------------------------- #
def _flux_trace(system, H, para, grid, op):
    """物点 (0, H) から射影立体角の一様格子で光線を出す → (有効な光線の像面座標, 1 セルの射影立体角, 合計)。

    方向余弦 (L, M) の一様格子は **射影立体角** dL dM = cos θ dΩ の一様格子なので、Lambert の物点から出る光束は
    「通った光線の数 × セルの面積」で厳密に(格子の細かさの範囲で)数えられる。窓は近軸の入射瞳を囲む箱の
    1.5 倍で、窓の縁の光線が通っていたら窓を広げて引き直す(3 回まで、だめなら ValueError)。
    """
    import raytrace as RT
    obj = system["object_mm"]
    P0 = np.array([0.0, H, -obj])
    ang = np.linspace(0.0, 2.0 * math.pi, 96, endpoint=False)
    rim = np.stack([para["ep_radius"] * np.cos(ang), para["ep_radius"] * np.sin(ang),
                    np.full(96, para["ep_position"])], 1)
    d = rim - P0
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    cL, cM = 0.5 * (d[:, 0].min() + d[:, 0].max()), 0.5 * (d[:, 1].min() + d[:, 1].max())
    hw = 0.75 * max(d[:, 0].max() - d[:, 0].min(), d[:, 1].max() - d[:, 1].min())
    g = (np.arange(grid) + 0.5) / grid * 2.0 - 1.0
    for _ in range(4):
        LL, MM = np.meshgrid(cL + hw * g, cM + hw * g)
        LL, MM = LL.ravel(), MM.ravel()
        r2 = LL * LL + MM * MM
        ok = r2 < 0.98
        D = np.stack([LL[ok], MM[ok], np.sqrt(1.0 - r2[ok])], 1)
        tr = RT.trace_rays(system, np.tile(P0, (len(D), 1)), D)
        v = tr["valid"]
        edge = (np.abs(LL[ok] - cL) > hw * (1.0 - 1.5 / grid)) | (np.abs(MM[ok] - cM) > hw * (1.0 - 1.5 / grid))
        if not (v & edge).any():
            cell = (2.0 * hw / grid) ** 2
            return tr["points"][v, -1, :2], cell, float(v.sum()) * cell
        hw *= 1.6
    raise ValueError("%s: rays still pass at the edge of the sampling window at object height %.4g mm — "
                     "the pupil is not where the paraxial trace says (check the stop)" % (op, H))


def lens_field_profile(system=None, image_heights_mm=None, frequencies_lp_mm=(10.0, 20.0, 35.0), grid=96,
                       wavelength_um=None):
    """像高ごとの**相対照度**と **MTF** を光線追跡で(``table``、有限距離の物体 = ラインスキャンの使い方)。

    照度: Lambert の物点から射影立体角の一様格子で光線を出し、像面に届いた光束を数える(``_flux_trace``)。
    像面の照度 = 光束 ÷ 像の面積要素(径方向の倍率 × 接線方向の倍率、像高の有限差分 —— 歪曲も入る)。
    相対照度は 3 つの積に**厳密に**分かれる(どれも返す):

      ``relative_illumination = cos4 × pupil_factor × area_gain``

    * ``cos4``: 物体側の主光線角(物点から近軸の入射瞳の中心へ)の cos⁴ —— 自然な周辺減光の閉形式
      (``optics.relative_illumination`` と同じ式)。
    * ``pupil_factor`` = (光束の比) / cos4: 1 なら理想の cos⁴、1 未満は**口径食**(鏡筒・レンズの縁・面の
      球の端で光束が欠ける)、1 より大きいのは軸外で入射瞳が広がって見える(瞳収差)。
    * ``area_gain`` = 軸上の面積要素 / その像高の面積要素: 樽型歪曲は像を縮めるので照度を**上げる**。

    MTF: 通った光線の像面の座標から幾何光学の OTF の絶対値 |⟨exp(−2πi ν (x − x̄))⟩|(各光線は等しい光束)を、
    サジタル(像高に直交、x)とタンジェンシャル(像高の向き、y)で。回折の MTF(円形瞳、近軸の作動 F 値)を
    ``mtf_diffraction`` に並べ、``mtf_sagittal`` / ``mtf_tangential`` は幾何 × 回折(積の近似 —— 収差が回折より
    十分大きいか小さいときに良い)。ラインセンサは径方向に 1 列に並ぶので、**タンジェンシャル = 幅方向
    (画素の並び)、サジタル = 流れ方向**。

    *system*: ``raytrace.lens_system``(有限距離の物体、既定 = ``linescan_lens_example("linescan")``)。
    *image_heights_mm*: 像高(既定 0〜28.672 mm = 8192 × 7 µm の半分を 9 点)—— 物体高は近軸倍率で割って出す。
    像高の位置(面積要素)は主光線、主光線が通らなければ通った光線の重心で測る。
    返り値 dict: ``image_height_mm`` / ``object_height_mm`` / ``chief_image_mm`` / ``distortion_percent`` /
    ``relative_illumination`` / ``cos4`` / ``pupil_factor`` / ``area_gain`` / ``flux_ratio`` /
    ``frequencies_lp_mm`` / ``mtf_sagittal`` / ``mtf_tangential``(像高 × 周波数)/ ``mtf_geometric_sagittal`` /
    ``mtf_geometric_tangential`` / ``mtf_diffraction`` / ``covered``(光線が 3 本以上届いたか)/
    ``magnification`` / ``working_fno``。届かない像高は照度 0・MTF NaN(``covered`` False)。

    **Raises** ``ValueError``: 物体が無限遠(像の面積要素の扱いが違う —— ``optics.relative_illumination`` /
    ``lensimage`` を使う)/ 像高・周波数が非有限か負 / grid が [16, 256] の外 / 軸上で光線が 1 本も通らない /
    窓を広げても光線が窓の縁を通る。
    """
    op = "lens_field_profile"
    import raytrace as RT
    sysd = linescan_lens_example("linescan") if system is None else system
    RT._check_system(sysd)
    if not math.isfinite(sysd["object_mm"]):
        raise ValueError("%s: the object must be at a finite distance (a line-scan setup); for an object at "
                         "infinity use optics.relative_illumination / lensimage" % op)
    if wavelength_um is not None:
        sysd = RT.with_wavelength(sysd, _num(wavelength_um, "wavelength_um", op, positive=True))
    hs = np.linspace(0.0, 28.672, 9) if image_heights_mm is None else np.atleast_1d(np.asarray(image_heights_mm, dtype=np.float64))
    if hs.ndim != 1 or hs.size == 0 or not np.all(np.isfinite(hs)) or (hs < 0).any():
        raise ValueError("%s: image_heights_mm must be a non-empty 1-D array of finite values >= 0" % op)
    fq = np.atleast_1d(np.asarray(frequencies_lp_mm, dtype=np.float64))
    if fq.ndim != 1 or fq.size == 0 or not np.all(np.isfinite(fq)) or (fq < 0).any():
        raise ValueError("%s: frequencies_lp_mm must be a non-empty 1-D array of finite values >= 0" % op)
    G = _int(grid, "grid", op, 16, 256)
    para = RT.paraxial_trace(sysd)
    m = para["magnification"]
    if not (math.isfinite(m) and m != 0.0):
        raise ValueError("%s: the system has no finite magnification" % op)
    wl_mm = sysd["wavelength_um"] * 1e-3
    nw = 1.0 / (2.0 * para["na_image"]) if para["na_image"] > 0 else float("inf")
    x = np.clip(fq * wl_mm * nw, 0.0, 1.0)
    mtf_d = (2.0 / math.pi) * (np.arccos(x) - x * np.sqrt(1.0 - x * x))
    dist_to_ep = sysd["object_mm"] + para["ep_position"]
    cache = {}

    def bundle(H):
        if H not in cache:
            cache[H] = _flux_trace(sysd, H, para, G, op)
        return cache[H]

    def img_y(H):
        """像高の位置: 主光線、通らなければ光束の重心(どちらも無ければ NaN)。"""
        cr = RT.chief_ray(sysd, field=H)
        if cr["valid"]:
            return cr["image_y"]
        xy = bundle(H)[0]
        return float(xy[:, 1].mean()) if len(xy) else float("nan")

    def area(H):
        y = img_y(H)
        dH = 1e-3 * max(1.0, abs(H))
        m_r = (img_y(H + dH) - img_y(H - dH)) / (2.0 * dH) if H != 0 else (img_y(dH) - img_y(-dH)) / (2.0 * dH)
        m_t = y / H if H != 0 else m_r
        return y, abs(m_r * m_t)

    _y0, A0 = area(0.0)
    F0 = bundle(0.0)[2]
    if not (F0 > 0 and math.isfinite(A0) and A0 > 0):
        raise ValueError("%s: no ray reaches the image on axis — the system does not image" % op)
    n = len(hs)
    keys = ("object_height_mm", "chief_image_mm", "distortion_percent", "relative_illumination", "cos4",
            "pupil_factor", "area_gain", "flux_ratio")
    out = {kk: np.full(n, np.nan) for kk in keys}
    ms, mt = np.full((n, len(fq)), np.nan), np.full((n, len(fq)), np.nan)
    covered = np.zeros(n, bool)
    for i, h in enumerate(hs):
        H = float(h) / m
        xy, _cell, flux = bundle(H)
        c4 = math.cos(math.atan2(abs(H), dist_to_ep)) ** 4
        out["object_height_mm"][i] = H
        out["cos4"][i] = c4
        out["flux_ratio"][i] = flux / F0
        out["pupil_factor"][i] = flux / F0 / c4
        if len(xy) < 3:
            out["relative_illumination"][i] = 0.0
            continue
        covered[i] = True
        y, A = area(H)
        out["chief_image_mm"][i] = y
        out["distortion_percent"][i] = 100.0 * (abs(y) - h) / h if h > 0 else 0.0
        out["area_gain"][i] = A0 / A if A > 0 else float("nan")
        out["relative_illumination"][i] = flux / F0 * out["area_gain"][i]
        c = xy.mean(0)
        ms[i] = np.abs(np.exp(-2j * math.pi * np.outer(fq, xy[:, 0] - c[0])).mean(1))
        mt[i] = np.abs(np.exp(-2j * math.pi * np.outer(fq, xy[:, 1] - c[1])).mean(1))
    out.update({"image_height_mm": hs, "frequencies_lp_mm": fq, "mtf_geometric_sagittal": ms,
                "mtf_geometric_tangential": mt, "mtf_diffraction": mtf_d,
                "mtf_sagittal": ms * mtf_d[None, :], "mtf_tangential": mt * mtf_d[None, :],
                "covered": covered, "magnification": m, "working_fno": nw})
    return out


def linescan_lens_columns(profile=None, width=8192, pixel_um=7.0, frequency_index=None):
    """``lens_field_profile`` の像高の表を、ラインセンサの**画素列ごと**の照度とぼけにする(``table``)。

    列 j の像高 = |j − (width − 1)/2| × 画素ピッチ。照度は像高で線形補間(表の外は ValueError —— 外挿しない)。
    ぼけは MTF を 1 つの周波数 ν(``frequency_index``、既定は表の真ん中)でガウスに合わせた σ:
    MTF(ν) = exp(−2π²σ²ν²) → σ = √(−ln MTF / (2π²ν²))。幅方向 = タンジェンシャル、流れ方向 = サジタル。
    ★ガウスは近似(コマや口径食の非対称な PSF を対称にしてしまう)。MTF が 0.02 未満の列は σ を
    「その周波数で 0.02」に当たる値で止める(どうせ見えない; 光が届かない列は照度 0)。

    返り値 dict: ``relative_illumination`` (width,) / ``blur_sigma_px`` (width, 2) = (幅方向, 流れ方向)/
    ``image_height_mm`` (width,) / ``frequency_lp_mm`` / ``pixel_um``。

    **Raises** ``ValueError``: profile が ``lens_field_profile`` の結果でない / センサが表の像高の範囲を超える /
    width・pixel_um が範囲外 / frequency_index が範囲外 / 選んだ周波数が 0。
    """
    op = "linescan_lens_columns"
    prof = lens_field_profile() if profile is None else profile
    if not isinstance(prof, dict) or "mtf_tangential" not in prof or "image_height_mm" not in prof:
        raise ValueError("%s: profile must be a lens_field_profile() result" % op)
    Wd = _int(width, "width", op, 2, 1 << 16)
    px = _num(pixel_um, "pixel_um", op, positive=True)
    hs = np.asarray(prof["image_height_mm"], dtype=np.float64)
    fq = np.asarray(prof["frequencies_lp_mm"], dtype=np.float64)
    fi = len(fq) // 2 if frequency_index is None else _int(frequency_index, "frequency_index", op, 0, len(fq) - 1)
    nu = float(fq[fi])
    if nu <= 0:
        raise ValueError("%s: the chosen frequency is 0 — a Gaussian cannot be fitted there" % op)
    h = np.abs(np.arange(Wd) - (Wd - 1) / 2.0) * px * 1e-3
    if h.max() > hs.max() * (1 + 1e-9) or hs.min() > 1e-9:
        raise ValueError("%s: the sensor reaches %.3f mm but the profile covers %.3f..%.3f mm"
                         % (op, h.max(), hs.min(), hs.max()))
    order = np.argsort(hs)
    ri = np.interp(h, hs[order], np.nan_to_num(np.asarray(prof["relative_illumination"])[order], nan=0.0))

    def sig(mtf):
        mm = np.clip(np.nan_to_num(np.asarray(mtf, dtype=np.float64)[order, fi], nan=0.02), 0.02, 1.0)
        s_mm = np.sqrt(-np.log(mm) / (2.0 * math.pi ** 2 * nu ** 2))
        return np.interp(h, hs[order], s_mm) / (px * 1e-3)

    return {"relative_illumination": ri, "blur_sigma_px": np.stack([sig(prof["mtf_tangential"]),
                                                                    sig(prof["mtf_sagittal"])], 1),
            "image_height_mm": h, "frequency_lp_mm": nu, "pixel_um": px}


#: 2 つのレンズの模型(Cooke の三枚玉 —— 教科書の f 50 mm を出発点に ``lensopt.optimize_lens`` で、倍率 −0.1911
#: (57.344 mm のセンサで 300 mm の視野)の有限距離に合わせて最適化した処方。R, 次の面までの距離, 媒質)。
#: "cmount": f 35 mm、2/3 型(像高 5.5 mm)の視野だけで最適化し、口径も 2/3 型用(縁の口径 7 mm、絞り 2.4 mm)。
#: "linescan": f 90 mm、像高 28.7 mm まで最適化し、口径も大きい(縁の口径 17 mm、絞り 6.2 mm)。
#: 同じ設計の形・同じ硝材 —— 違いは**どの像円のために作ったか**だけにしてある。
_LENSES = {
    "cmount": {"object_mm": 201.43533905907663, "ap": 7.0, "stop_ap": 2.4, "rows": [
        (10.775748108000093, 2.281272, "N-SK16"), (-121.85069487882386, 3.289505479420517, 1.0),
        (-18.279445966501342, 0.69999853, "N-F2"), (8.611981158562877, 8.78859278581853, 1.0),
        (57.135484969452705, 2.0665525999999996, "N-SK16"), (-15.681390264329249, 34.93682403828906, 1.0)]},
    "linescan": {"object_mm": 518.8192718882401, "ap": 17.0, "stop_ap": 6.2, "rows": [
        (58.12948941947101, 5.866128000000001, "N-SK16"), (-39.330842208453596, 1.7934318596256156, 1.0),
        (-26.883036893641876, 1.79999622, "N-F2"), (30.979506592462233, 18.44180665488329, 1.0),
        (-1063.1929917515113, 5.3139924, "N-SK16"), (-29.591028222445807, 125.11406307066716, 1.0)]},
}


def linescan_lens_example(kind="linescan"):
    """ラインスキャンの撮像系の模型 2 つ(``raytrace.lens_system`` の ``table``)。

    どちらも Cooke の三枚玉(SK16 相当のクラウン / F2 相当のフリント / SK16 相当、絞りは中玉の後ろ)を、57.344 mm(8192 × 7 µm)のセンサで
    幅 300 mm の web を見る倍率 −0.1911 に合わせて ``lensopt.optimize_lens`` で最適化した処方:

    * ``"linescan"``: f 90 mm、物体距離 519 mm、像高 28.7 mm(センサの端)まで最適化、大きい口径
      —— **ラインスキャン用レンズ**の模型(像円がセンサを覆う)。
    * ``"cmount"``: f 35 mm、物体距離 201 mm、2/3 型の像高 5.5 mm までで最適化し、口径も 2/3 型用
      —— **普通の C マウントレンズを長いセンサに流用**した模型。同じ形・同じ硝材で、違いは像円だけ。

    実在の型番の処方ではない(メーカーの処方は公開されていない)。像円の大きさと口径食の有無という
    **性質**を見るための模型。

    **Raises** ``ValueError``: kind が ``"linescan"`` / ``"cmount"`` でない。
    """
    import raytrace as RT
    if kind not in _LENSES:
        raise ValueError("linescan_lens_example: kind must be one of %s, got %r" % (sorted(_LENSES), kind))
    d = _LENSES[kind]
    surf = [{"R": R, "t": t, "n": n, "ap": (d["stop_ap"] if i == 3 else d["ap"])} for i, (R, t, n) in enumerate(d["rows"])]
    return RT.lens_system(surf, stop=3, object_mm=d["object_mm"])

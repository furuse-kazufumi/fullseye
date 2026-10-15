# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""octscan — 光干渉断層(OCT): 層構造の干渉スペクトル → k 線形化 → 分散補償 → A スキャン → 層厚。

動機(2026-10-15、ViEW2026 向けの展示会調査の 2 位): 塗装・コンフォーマルコート・接着層・多層フィルムの
**層厚と内部欠陥を深さ方向に**見る。既存の白色干渉(``interferometry`` の CSI)は**表面の高さ**を、
クロマティック共焦点は**1 点の距離**を、薄膜の分光反射は**サブ µm の膜厚**を出す。OCT はその間 ——
数 µm〜数 mm の**層の並び**を、1 本の干渉スペクトルの FFT で一度に出す。

内容(13 op):
  設計      `oct_design`(軸分解能 0.44 λ0²/Δλ・深さ範囲 λ0²/(4δλ)・感度の roll-off・ショット雑音律の SNR・
            横分解能と焦点深度を、撮る前に閉形式で)/ `oct_dispersion_broadening`(分散の不一致による広がり
            √(1 + σ⁴φ₂²) と、補償に使う係数 a2・a3)
  合成      `oct_interferogram`(層の並び + 光源 + 分光器 / 波長掃引 → 1 本の干渉スペクトル。場の和の |E|² なので
            相互相関・自己相関・DC が全部入る)/ `oct_bscan_simulate`(界面の深さの分布・空洞・散乱体・ビームの
            横の広がりと焦点 → B スキャンの干渉スペクトルの束)
  処理      `oct_k_linearize`(λ 等間隔 → k 等間隔)/ `oct_dispersion_estimate`(鏡の位相 / 鋭さ最大)/
            `oct_dispersion_compensate`(解析信号に exp(−i(a2Δk² + a3Δk³)))/ `oct_ascan`(窓・DC 除去・
            直交成分による鏡像の分離・FFT)/ `oct_bscan`(束を一度に)
  計測      `oct_layer_thickness`(A スキャンの界面のピーク → 光学厚 → 群屈折率で物理厚、分離できなければ拒否)/
            `oct_bscan_boundaries`(B スキャンの画像から界面を動的計画法で辿る。実画像の図にも使える)
            `oct_bscan_flatten`(面に沿って平らに並べ、横に平均した深さの断面 → oct_layer_thickness へ)
  入口      `oct_from_spectra`(装置・公開データの生のスペクトルと波長の較正を、この族の表にする)

規約: 長さは µm、波長は nm、波数 k = 2π/λ は rad/µm。深さ z は**片道の光路長**(空気中の µm)で、
物理厚 = 光学厚 / 群屈折率 n_g(位相屈折率 n ではない —— 包絡のピークは群遅延で動く)。
層の材料は ``materials`` の名前(分散つき)、数(分散なし)、``{"n": …, "n_group": …}``(k について 1 次の模型)。
群屈折率と分散は ``fiberoptics.material_group_index`` と同じ定義(n − λ dn/dλ)。ピークの位置は
``dsp.find_peaks`` / ``dsp.peak_subbin``、鏡の位相のアンラップは ``complexops.phase_unwrap``、
雑音は ``sensorchar`` の EMVA 1288 の線形模型(η・σ_d・K)と同じ規約。

真値(外部): 軸分解能 δz = (2 ln 2/π) λ0²/Δλ(ガウス光源、空気中の FWHM)と深さ範囲 z_max = λ0²/(4δλ)
(Drexler & Fujimoto 編 *Optical Coherence Tomography*、2nd ed. 2015 / Fercher ら Rep. Prog. Phys. 66, 239, 2003)、
画素の有限幅による roll-off |sin(zδk)/(zδk)| と分光器の分解能のガウス(Yun ら Opt. Express 11, 3598, 2003 /
Hu & Rollins Opt. Lett. 32, 3525, 2007)、ショット雑音律の SNR = η × (試料腕の光子の総数)(Leitgeb ら
Opt. Express 11, 889, 2003)、数値分散補償 exp(−i(a2Δk² + a3Δk³))(Wojtkowski ら Opt. Express 12, 2404, 2004)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "oct_design", "oct_dispersion_broadening", "oct_interferogram", "oct_bscan_simulate",
    "oct_k_linearize", "oct_dispersion_estimate", "oct_dispersion_compensate", "oct_ascan", "oct_bscan",
    "oct_layer_thickness", "oct_bscan_boundaries", "oct_bscan_flatten", "oct_from_spectra",
]

LN2 = math.log(2.0)
#: 細かい k 格子の上限(メモリの上限: 画素 × oversample)。
MAX_FINE = 1 << 18
#: 反射体の数の上限(1 本の A スキャンあたり)。
MAX_REFLECTORS = 20000


# --------------------------------------------------------------------------- #
# 入力の検査                                                                    #
# --------------------------------------------------------------------------- #
def _pos(v, name, op):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, v)) from None
    if not (math.isfinite(x) and x > 0.0):
        raise ValueError("%s: %s must be finite and > 0, got %r" % (op, name, v))
    return x


def _nonneg(v, name, op):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, v)) from None
    if not (math.isfinite(x) and x >= 0.0):
        raise ValueError("%s: %s must be finite and >= 0, got %r" % (op, name, v))
    return x


def _finite(v, name, op):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, v)) from None
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    return x


def _count(v, name, op, lo, hi):
    if isinstance(v, bool) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    if not (lo <= int(v) <= hi):
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, int(v)))
    return int(v)


def _table(t, kind, op):
    if not isinstance(t, dict) or t.get("kind") not in (kind if isinstance(kind, tuple) else (kind,)):
        got = t.get("kind") if isinstance(t, dict) else type(t).__name__
        raise ValueError("%s: expected a table with kind %r, got %r" % (op, kind, got))
    return t


# --------------------------------------------------------------------------- #
# 屈折率(材料表・数・1 次の模型)                                                #
# --------------------------------------------------------------------------- #
def _index_fn(material, k0, op):
    """材料 → n(k) を返す関数(k は rad/µm の配列)と、表示用の名前。"""
    if isinstance(material, str):
        if material.strip().upper() in ("AIR", "VACUUM"):
            return (lambda k: np.ones_like(np.asarray(k, float))), "air"
        import materials as _mat
        rec = _mat._record(material, op)

        def f(k, rec=rec):
            k = np.asarray(k, float)
            return _mat._nk(rec, 2.0 * np.pi / k, op)[0].reshape(k.shape)
        return f, rec["name"]
    if isinstance(material, dict):
        n0 = _pos(material.get("n"), "material['n']", op)
        ng = _pos(material.get("n_group", n0), "material['n_group']", op)
        b = (ng - n0) / k0                       # n(k) = n0 + b (k − k0)  →  n_g(k0) = n0 + k0 b
        return (lambda k, n0=n0, b=b: n0 + b * (np.asarray(k, float) - k0)), str(material.get("name", "model"))
    n = _pos(material, "material", op)
    return (lambda k, n=n: np.full_like(np.asarray(k, float), n)), "n=%.4g" % n


def _group_index_at(material, center_nm, op):
    """群屈折率 n_g = d(nk)/dk を中心波長で(材料表は中心差分、数はそのまま、模型は n_group)。"""
    if isinstance(material, (int, float, np.floating, np.integer)) and not isinstance(material, bool):
        return _pos(material, "n_group", op)
    k0 = 2.0 * np.pi / (center_nm / 1000.0)
    f, _ = _index_fn(material, k0, op)
    h = k0 * 1e-4
    kk = np.array([k0 - h, k0 + h])
    nk = f(kk) * kk
    return float((nk[1] - nk[0]) / (2 * h))


def _nk_derivs(material, k0, op):
    """(nk) の k に関する 2 階・3 階の微分(中心差分、材料表の継ぎ目を跨がない刻み)。"""
    f, _ = _index_fn(material, k0, op)
    h = k0 * 2e-3
    kk = k0 + h * np.arange(-2, 3)
    p = f(kk) * kk
    d2 = (p[3] - 2 * p[2] + p[1]) / h ** 2
    d3 = (p[4] - 2 * p[3] + 2 * p[1] - p[0]) / (2 * h ** 3)
    return float(d2), float(d3)


# --------------------------------------------------------------------------- #
# 1. 設計(閉形式)                                                              #
# --------------------------------------------------------------------------- #
def _sd_grid(center_nm, bandwidth_nm, n_pixels, wl_min_nm, wl_max_nm, op):
    lo = center_nm - 1.6 * bandwidth_nm if wl_min_nm is None else _pos(wl_min_nm, "wl_min_nm", op)
    hi = center_nm + 1.6 * bandwidth_nm if wl_max_nm is None else _pos(wl_max_nm, "wl_max_nm", op)
    if not (0.0 < lo < center_nm < hi):
        raise ValueError("%s: need 0 < wl_min_nm < center_nm < wl_max_nm, got %.6g / %.6g / %.6g"
                         % (op, lo, center_nm, hi))
    return lo, hi


def _rolloff(z_um, dk_pixel, sigma_k):
    """片道の光路 z の roll-off(振幅): 画素の箱 |sin(z δk)/(z δk)| × 分光器 / 線幅のガウス exp(−2σ²z²)。"""
    z = np.asarray(z_um, float)
    box = np.abs(np.sinc(z * dk_pixel / np.pi)) if dk_pixel > 0 else np.ones_like(z)
    return box * np.exp(-2.0 * sigma_k ** 2 * z ** 2)


def oct_design(center_nm=840.0, bandwidth_nm=50.0, n_pixels=2048, wl_min_nm=None, wl_max_nm=None, mode="sd",
               spectrometer_fwhm_px=1.0, linewidth_nm=None, n_group=1.0, beam_waist_um=None, focal_mm=None,
               beam_diameter_mm=None, photons_mirror_per_pixel=None, photons_ref_per_pixel=None, eta=0.8,
               sigma_d=10.0, window="hann", reflectivity=None, grid="lambda"):
    """OCT の性能を**撮る前に**閉形式で(``table``): 軸分解能・深さ範囲・感度の roll-off・SNR・横分解能と焦点深度。

    * 軸分解能(FWHM、ガウス光源、窓なし)δz = (2 ln 2/π) λ0²/Δλ ≈ 0.44 λ0²/Δλ(空気中)、媒質中は ÷ n_g。
      ``window`` を掛けると広がる(倍率 ``window_broadening`` は光源 × 窓の |FT| の FWHM から数値で求める。
      ガウス光源が範囲の中に収まっていれば hann で約 1.2 倍)。
    * 深さ範囲(片道の光路、ナイキスト)z_max = π/(2 δk) = λ0²/(4 δλ)(δλ = 1 画素の波長幅)、媒質中は ÷ n_g。
      ``grid="lambda"``(既定)は λ 等間隔の分光器(δk は中心の値)、``"k"`` は k 等間隔の分光器(Hu & Rollins 2007)。
    * roll-off(振幅): SD は画素の箱 |sin(z δk)/(z δk)| と分光器の分解能のガウス exp(−2σ²z²)(σ = 分解能の
      FWHM/2.355、k で)。SS は瞬時線幅 ``linewidth_nm`` のガウスだけ(``mode="ss"``)。−6 dB の深さを数値で解く。
    * SNR(ショット雑音 + 読み出し雑音、窓つき): 画素 i の参照光の電子 N_r,i と、反射率 1 の鏡の電子 N_s,i で
      SNR = (Σ w_i √(N_r,i N_s,i))² / Σ w_i² (N_r,i + σ_d²)(参照光が強ければ η × 試料の光子の総数 × 窓の係数)。
      ``sensitivity_db`` = 10 log10(SNR)(弱い反射体の SNR を反射率 1 へ外挿した値 = 検出の下限 1/R_min)。
      ``reflectivity`` R を渡すと、その反射体自身のショット雑音(N_s,i R)も分母に入れた SNR を ``snr_db`` に返す
      (強い反射体では参照光が支配的という前提が崩れ、外挿より小さくなる)。光子が渡されないときは None。
    * 横分解能: ビームのくびれ半径 w0(1/e²)から、慣用の Δx = 2 w0 = (4λ/π)(f/d) と、A スキャンの振幅で見た
      点像の FWHM √(2 ln 2) w0(往復で exp(−2x²/w²))。焦点深度 b = 2 z_R = 2π w0² n/λ(慣用 = π Δx²/(2λ))。

    返り値: dict(kind="oct_design", axial_resolution_air_um, axial_resolution_um, depth_range_air_um,
    depth_range_um, pixel_nm, dk_pixel, rolloff_6db_air_um, rolloff_6db_um, rolloff(pairs: 光路 µm, 振幅),
    snr_db / sensitivity_db, lateral_resolution_um, lateral_fwhm_um, depth_of_focus_um, …)。
    """
    op = "oct_design"
    lam0 = _pos(center_nm, "center_nm", op)
    dlam = _pos(bandwidth_nm, "bandwidth_nm", op)
    if mode not in ("sd", "ss"):
        raise ValueError("%s: mode must be 'sd' or 'ss', got %r" % (op, mode))
    N = _count(n_pixels, "n_pixels", op, 16, 1 << 16)
    lo, hi = _sd_grid(lam0, dlam, N, wl_min_nm, wl_max_nm, op)
    ng = _pos(n_group, "n_group", op)
    k0 = 2 * np.pi / (lam0 / 1000.0)
    dk_fwhm = 2 * np.pi * (dlam / 1000.0) / (lam0 / 1000.0) ** 2
    sigma_src = dk_fwhm / (2 * math.sqrt(2 * LN2))
    if grid not in ("lambda", "k"):
        raise ValueError("%s: grid must be 'lambda' or 'k', got %r" % (op, grid))
    pixel_nm = (hi - lo) / (N - 1)
    if grid == "lambda":
        dk_pix = 2 * np.pi * (pixel_nm / 1000.0) / (lam0 / 1000.0) ** 2
    else:
        dk_pix = (2 * np.pi / (lo / 1000.0) - 2 * np.pi / (hi / 1000.0)) / (N - 1)
    dz_air = 4 * LN2 / dk_fwhm                              # = (2 ln2/π) λ0²/Δλ
    zmax_air = np.pi / (2 * dk_pix)                          # = λ0²/(4 δλ)
    if mode == "sd":
        fw = _nonneg(spectrometer_fwhm_px, "spectrometer_fwhm_px", op)
        sig = fw * dk_pix / (2 * math.sqrt(2 * LN2))
        box = dk_pix
    else:
        lw = 0.0 if linewidth_nm is None else _nonneg(linewidth_nm, "linewidth_nm", op)
        sig = 2 * np.pi * (lw / 1000.0) / (lam0 / 1000.0) ** 2 / (2 * math.sqrt(2 * LN2))
        box = 0.0
    zz = np.linspace(0.0, zmax_air, 401)
    ro = _rolloff(zz, box, sig)
    below = np.flatnonzero(ro < 0.5)
    if below.size:
        i = int(below[0])
        z6 = float(np.interp(0.5, [ro[i], ro[i - 1]], [zz[i], zz[i - 1]]))
    else:
        z6 = None
    # 窓による広がり(数値): ガウスの光源 × 窓 の |FT| の FWHM / 窓なしの FWHM
    wb = _window_broadening(window, sigma_src, k0, lo, hi, N)
    out = {"kind": "oct_design", "mode": mode, "grid": grid, "center_nm": lam0, "bandwidth_nm": dlam, "n_pixels": N,
           "wl_min_nm": lo, "wl_max_nm": hi, "pixel_nm": pixel_nm, "dk_pixel": dk_pix, "dk_fwhm": dk_fwhm,
           "n_group": ng, "axial_resolution_air_um": dz_air, "axial_resolution_um": dz_air / ng,
           "window": window, "window_broadening": wb, "axial_resolution_windowed_um": dz_air * wb / ng,
           "depth_range_air_um": zmax_air, "depth_range_um": zmax_air / ng,
           "rolloff_6db_air_um": z6, "rolloff_6db_um": None if z6 is None else z6 / ng,
           "rolloff_at_depth_range": float(_rolloff([zmax_air], box, sig)[0]),
           "rolloff": np.stack([zz, ro], axis=1), "sigma_k_rolloff": sig}
    # SNR
    if photons_mirror_per_pixel is not None:
        pm = _pos(photons_mirror_per_pixel, "photons_mirror_per_pixel", op)
        pr = pm if photons_ref_per_pixel is None else _pos(photons_ref_per_pixel, "photons_ref_per_pixel", op)
        et = _pos(eta, "eta", op)
        sd = _nonneg(sigma_d, "sigma_d", op)
        # 窓は k 等間隔に並べ直したあとに掛かる(λ 等間隔でも、処理は k 等間隔の点で行う)
        k = np.linspace(2 * np.pi / (hi / 1000.0), 2 * np.pi / (lo / 1000.0), N)
        S = np.exp(-4 * LN2 * (k - k0) ** 2 / dk_fwhm ** 2)
        w = _window(window, N, op)
        Nr, Ns = et * pr * S, et * pm * S
        snr = (np.sum(w * np.sqrt(Nr * Ns))) ** 2 / np.sum(w ** 2 * (Nr + sd ** 2))
        out["snr_mirror"] = float(snr)
        out["sensitivity_db"] = float(10 * np.log10(snr))
        if reflectivity is not None:
            R = _pos(reflectivity, "reflectivity", op)
            sR = (np.sum(w * np.sqrt(Nr * Ns * R))) ** 2 / np.sum(w ** 2 * (Nr + Ns * R + sd ** 2))
            out["snr_db"] = float(10 * np.log10(sR))
        else:
            out["snr_db"] = None
    else:
        out["snr_mirror"] = out["sensitivity_db"] = out["snr_db"] = None
    # 横
    lam_um = lam0 / 1000.0
    if beam_waist_um is not None:
        w0 = _pos(beam_waist_um, "beam_waist_um", op)
    elif focal_mm is not None and beam_diameter_mm is not None:
        w0 = 2 * lam_um * _pos(focal_mm, "focal_mm", op) / (np.pi * _pos(beam_diameter_mm, "beam_diameter_mm", op))
    else:
        w0 = None
    if w0 is not None:
        out.update({"beam_waist_um": w0, "lateral_resolution_um": 2 * w0,
                    "lateral_fwhm_um": math.sqrt(2 * LN2) * w0,
                    "rayleigh_um": np.pi * w0 ** 2 * ng / lam_um,
                    "depth_of_focus_um": 2 * np.pi * w0 ** 2 * ng / lam_um})
    else:
        out.update({"beam_waist_um": None, "lateral_resolution_um": None, "lateral_fwhm_um": None,
                    "rayleigh_um": None, "depth_of_focus_um": None})
    return out


def _window(window, n, op):
    if window in (None, "none", "rect"):
        return np.ones(n)
    if window == "hann":
        return np.hanning(n)
    if window == "hamming":
        return np.hamming(n)
    if window == "blackman":
        return np.blackman(n)
    raise ValueError("%s: window must be 'none', 'hann', 'hamming' or 'blackman', got %r" % (op, window))


def _window_broadening(window, sigma, k0, lo, hi, N):
    if window in (None, "none", "rect"):
        return 1.0
    k = np.linspace(2 * np.pi / (hi / 1000.0), 2 * np.pi / (lo / 1000.0), N)
    S = np.exp(-(k - k0) ** 2 / (2 * sigma ** 2))
    w = _window(window, N, "oct_design")
    P = 64 * N

    def fwhm(x):
        a = np.abs(np.fft.fft(x, P))
        a = np.concatenate([a[P // 2:], a[:P // 2]])
        m = a.max()
        idx = np.flatnonzero(a >= m / 2)
        return idx[-1] - idx[0]
    return float(fwhm(S * w) / fwhm(S))


def oct_dispersion_broadening(material="SILICA", length_mm=10.0, center_nm=840.0, bandwidth_nm=50.0):
    """試料腕だけにある材料(長さ L、往復)の分散の不一致で A スキャンのピークが何倍に広がるか(``table``、閉形式)。

    往復の位相 φ(k) = 2 L k (n(k) − n_g(k0))(群遅延は参照腕で合わせた前提)を k0 で展開し、
    φ₂ = 2L d²(nk)/dk²、φ₃ = 2L d³(nk)/dk³。ガウス光源(パワーの標準偏差 σ = Δk/2.355)の包絡は
    **√(1 + σ⁴ φ₂²) 倍**に広がる(2 次まで厳密、3 次は非対称な裾)。数値補償の係数は a2 = φ₂/2 [µm²]、
    a3 = φ₃/6 [µm³] で、展開の中心は k0 = 2π/λ0(``k_center``)—— ``oct_dispersion_compensate`` /
    ``oct_ascan`` には a2・a3 と**同じ k_center** を渡す(中心がずれると a2 が 3 a3 δk だけ変わる)。層そのものの分散(厚い樹脂の底の界面が
    広がる)も同じ式で、L に層の厚さを入れる。

    返り値: dict(kind="oct_dispersion", phi2_um2, phi3_um3, a2, a3, broadening, group_index, gvd_fs2_per_mm)。
    """
    op = "oct_dispersion_broadening"
    lam0 = _pos(center_nm, "center_nm", op)
    dlam = _pos(bandwidth_nm, "bandwidth_nm", op)
    L_um = _nonneg(length_mm, "length_mm", op) * 1000.0
    k0 = 2 * np.pi / (lam0 / 1000.0)
    d2, d3 = _nk_derivs(material, k0, op)
    phi2, phi3 = 2 * L_um * d2, 2 * L_um * d3
    sigma = 2 * np.pi * (dlam / 1000.0) / (lam0 / 1000.0) ** 2 / (2 * math.sqrt(2 * LN2))
    # 群速度分散 β2 = d²(n ω/c)/dω² = (1/c²) d²(nk)/dk² [fs²/µm] → ×1000 で fs²/mm(c = 0.299792458 µm/fs)
    c = 0.299792458
    gvd = d2 / (c * c) * 1000.0
    return {"kind": "oct_dispersion", "material": material if isinstance(material, str) else str(material),
            "length_mm": L_um / 1000.0, "center_nm": lam0, "bandwidth_nm": dlam,
            "group_index": _group_index_at(material, lam0, op),
            "phi2_um2": phi2, "phi3_um3": phi3, "a2": phi2 / 2.0, "a3": phi3 / 6.0,
            "sigma_k": sigma, "broadening": math.sqrt(1.0 + (sigma ** 2 * phi2) ** 2), "gvd_fs2_per_mm": gvd,
            "k_center": k0}


# --------------------------------------------------------------------------- #
# 2. 合成: 反射体の並び → 干渉スペクトル                                         #
# --------------------------------------------------------------------------- #
def _parse_layers(sample, k0, op):
    if not isinstance(sample, dict):
        raise ValueError("%s: sample must be a dict with 'layers' (list of dicts), got %r" % (op, type(sample).__name__))
    layers = sample.get("layers")
    if not isinstance(layers, (list, tuple)) or not layers:
        raise ValueError("%s: sample['layers'] must be a non-empty list" % op)
    out = []
    for i, L in enumerate(layers):
        if not isinstance(L, dict) or "material" not in L or "thickness_um" not in L:
            raise ValueError("%s: layer %d needs 'material' and 'thickness_um'" % (op, i))
        f, name = _index_fn(L["material"], k0, op)
        out.append({"fn": f, "material": L["material"], "label": L.get("name", name),
                    "thickness_um": _pos(L["thickness_um"], "layers[%d].thickness_um" % i, op),
                    "mu_per_mm": _nonneg(L.get("attenuation_per_mm", 0.0), "attenuation_per_mm", op),
                    "scatterers_per_mm": _nonneg(L.get("scatterers_per_mm", 0.0), "scatterers_per_mm", op),
                    "scatter_amplitude": _nonneg(L.get("scatter_amplitude", 0.0), "scatter_amplitude", op)})
    amb_f, amb = _index_fn(sample.get("ambient", "air"), k0, op)
    sub_f, sub = _index_fn(sample.get("substrate", 1.5), k0, op)
    return amb_f, out, sub_f, sub


class _Rx:
    """反射体の集まり: 振幅 a(k)、各材料の中の片道の距離(行列)、空気中のずれ。位相 = 2k(off + P·n(k))。"""

    def __init__(self):
        self.amp, self.off, self.path, self.r_fn = [], [], [], []

    def add(self, amp, off, path, r_fn=None):
        self.amp.append(complex(amp))
        self.off.append(float(off))
        self.path.append(path)
        self.r_fn.append(r_fn)


def _field(k, rx, fns, n_cache=None):
    """E_s(k) = Σ a_j r_j(k) exp(2ik(off_j + Σ_m P_jm n_m(k)))。"""
    if not rx.amp:
        return np.zeros(k.shape, complex)
    if len(rx.amp) > MAX_REFLECTORS:
        raise ValueError("oct: %d reflectors exceed the cap %d" % (len(rx.amp), MAX_REFLECTORS))
    N = np.stack([f(k) for f in fns]) if n_cache is None else n_cache      # (M, K)
    P = np.array(rx.path, float).reshape(len(rx.amp), len(fns))
    delay = np.asarray(rx.off)[:, None] + P @ N                            # (R, K)
    amp = np.asarray(rx.amp)[:, None] * np.ones((1, k.size))
    for j, rf in enumerate(rx.r_fn):
        if rf is not None:
            amp[j] = amp[j] * rf(N)
    return np.sum(amp * np.exp(2j * k[None, :] * delay), axis=0)


def _detector(k_fine, I_fine, edges_k, blur_sigma_k, points=None):
    """細かい等間隔 k の強度 → ガウスでぼかし(分光器の分解能 / 瞬時線幅)→ 各画素の k の区間で平均
    (分光器の画素の箱)。``points`` を渡すと区間で平均せず、その k で標本化する(波長掃引の瞬時の標本)。"""
    dk = k_fine[1] - k_fine[0]
    if blur_sigma_k > 0:
        from scipy import ndimage
        I_fine = ndimage.gaussian_filter1d(I_fine, blur_sigma_k / dk, mode="nearest", axis=-1)
    if points is not None:
        from scipy.interpolate import CubicSpline
        return CubicSpline(k_fine, I_fine, axis=-1)(points)
    C = np.concatenate([np.zeros(I_fine.shape[:-1] + (1,)), np.cumsum(0.5 * (I_fine[..., 1:] + I_fine[..., :-1]) * dk,
                                                                     axis=-1)], axis=-1)
    a, b = np.minimum(edges_k[:, 0], edges_k[:, 1]), np.maximum(edges_k[:, 0], edges_k[:, 1])
    if C.ndim == 1:
        return (np.interp(b, k_fine, C) - np.interp(a, k_fine, C)) / (b - a)
    return np.stack([(np.interp(b, k_fine, c) - np.interp(a, k_fine, c)) / (b - a) for c in C])


def _acq_setup(op, center_nm, bandwidth_nm, mode, n_pixels, wl_min_nm, wl_max_nm, spectrometer_fwhm_px,
               linewidth_nm, sweep_nonlinearity, source_spectrum, oversample, grid="lambda"):
    lam0 = _pos(center_nm, "center_nm", op)
    dlam = _pos(bandwidth_nm, "bandwidth_nm", op)
    if mode not in ("sd", "ss"):
        raise ValueError("%s: mode must be 'sd' (spectrometer) or 'ss' (swept source), got %r" % (op, mode))
    N = _count(n_pixels, "n_pixels", op, 16, 1 << 16)
    M = _count(oversample, "oversample", op, 2, 64)
    lo, hi = _sd_grid(lam0, dlam, N, wl_min_nm, wl_max_nm, op)
    k0 = 2 * np.pi / (lam0 / 1000.0)
    dk_fwhm = 2 * np.pi * (dlam / 1000.0) / (lam0 / 1000.0) ** 2
    if grid not in ("lambda", "k"):
        raise ValueError("%s: grid must be 'lambda' (spectrometer pixels uniform in wavelength) or 'k', got %r"
                         % (op, grid))
    if mode == "sd" and grid == "lambda":
        wl = np.linspace(lo, hi, N)
        dwl = wl[1] - wl[0]
        edges_wl = np.stack([wl - dwl / 2, wl + dwl / 2], axis=1)
        edges_k = 2 * np.pi / (edges_wl / 1000.0)
        k_px = 2 * np.pi / (wl / 1000.0)
        fw = _nonneg(spectrometer_fwhm_px, "spectrometer_fwhm_px", op)
        blur = fw * (2 * np.pi * (dwl / 1000.0) / (lam0 / 1000.0) ** 2) / (2 * math.sqrt(2 * LN2))
        if sweep_nonlinearity:
            raise ValueError("%s: sweep_nonlinearity applies to mode='ss' only" % op)
    elif mode == "sd":
        k_px = np.linspace(2 * np.pi / (hi / 1000.0), 2 * np.pi / (lo / 1000.0), N)
        dkp = k_px[1] - k_px[0]
        edges_k = np.stack([k_px - dkp / 2, k_px + dkp / 2], axis=1)
        wl = 2 * np.pi / k_px * 1000.0
        fw = _nonneg(spectrometer_fwhm_px, "spectrometer_fwhm_px", op)
        blur = fw * dkp / (2 * math.sqrt(2 * LN2))
        if sweep_nonlinearity:
            raise ValueError("%s: sweep_nonlinearity applies to mode='ss' only" % op)
    else:
        eps = _finite(sweep_nonlinearity, "sweep_nonlinearity", op)
        if abs(eps) >= 1.0:
            raise ValueError("%s: |sweep_nonlinearity| must be < 1 (the sweep must stay monotonic)" % op)
        k_lo, k_hi = 2 * np.pi / (hi / 1000.0), 2 * np.pi / (lo / 1000.0)
        t = (np.arange(N) + 0.5) / N
        te = np.stack([np.arange(N) / N, (np.arange(N) + 1) / N], axis=1)

        def kt(tt):
            return k_lo + (k_hi - k_lo) * (tt + eps * tt * (1 - tt))
        k_px, edges_k = kt(t), kt(te)
        wl = 2 * np.pi / k_px * 1000.0
        lw = 0.0 if linewidth_nm is None else _nonneg(linewidth_nm, "linewidth_nm", op)
        blur = 2 * np.pi * (lw / 1000.0) / (lam0 / 1000.0) ** 2 / (2 * math.sqrt(2 * LN2))
    kmin, kmax = float(edges_k.min()), float(edges_k.max())
    min_w = float(np.min(np.abs(edges_k[:, 1] - edges_k[:, 0])))
    dkf = min_w / M
    margin = 5 * blur + 2 * dkf
    nf = int(math.ceil((kmax - kmin + 2 * margin) / dkf)) + 1
    if nf > MAX_FINE:
        raise ValueError("%s: fine grid %d > %d samples; lower n_pixels or oversample" % (op, nf, MAX_FINE))
    k_fine = kmin - margin + dkf * np.arange(nf)
    if source_spectrum is None:
        S_fn = (lambda k: np.exp(-4 * LN2 * (k - k0) ** 2 / dk_fwhm ** 2))
    else:
        sp = np.asarray(source_spectrum, float)
        if sp.ndim != 2 or sp.shape[1] != 2 or sp.shape[0] < 4 or not np.all(np.isfinite(sp)):
            raise ValueError("%s: source_spectrum must be finite pairs (lambda_nm, power) with >= 4 rows" % op)
        o = np.argsort(sp[:, 0])
        sk, sv = 2 * np.pi / (sp[o, 0][::-1] / 1000.0), sp[o, 1][::-1]
        if np.any(sv < 0):
            raise ValueError("%s: source_spectrum power must be >= 0" % op)
        mx = float(sv.max())
        if mx <= 0:
            raise ValueError("%s: source_spectrum is all zero" % op)
        S_fn = (lambda k, sk=sk, sv=sv / mx: np.interp(k, sk, sv, left=0.0, right=0.0))
    return {"lam0": lam0, "dlam": dlam, "N": N, "lo": lo, "hi": hi, "k0": k0, "wl": wl, "k_px": k_px,
            "edges_k": edges_k, "blur": blur, "k_fine": k_fine, "S_fn": S_fn, "mode": mode,
            "k_uniform": bool(mode == "sd" and grid == "k")}


def _noise(mean_e, rng, eta_unused, sigma_d, K, full_well, quantize):
    e = mean_e + rng.standard_normal(mean_e.shape) * np.sqrt(np.maximum(mean_e, 0.0))   # ショット雑音(ガウス近似)
    e = e + rng.standard_normal(mean_e.shape) * sigma_d
    if full_well is not None:
        e = np.minimum(e, full_well)
    y = K * e
    if quantize:
        y = np.round(y)
    return y


def _acquire(acq, fields_fine, photons_ref, photons_mirror, ref_phase, eta, sigma_d, K, full_well, quantize,
             noise, rng):
    """場 E_s(k)(参照光の振幅で規格化)→ 平均電子 → 雑音つきの DN。fields_fine は (K,) か (C, K)。"""
    S = acq["S_fn"](acq["k_fine"])
    s = math.sqrt(photons_mirror / photons_ref)
    Er = np.exp(1j * ref_phase)
    I = S * np.abs(Er + s * fields_fine) ** 2
    Iref = S * 1.0
    pts = acq["k_px"] if acq["mode"] == "ss" else None
    mean = eta * photons_ref * _detector(acq["k_fine"], I, acq["edges_k"], acq["blur"], pts)
    ref = eta * photons_ref * _detector(acq["k_fine"], Iref, acq["edges_k"], acq["blur"], pts)
    samp = eta * photons_ref * _detector(acq["k_fine"], S * np.abs(s * fields_fine) ** 2, acq["edges_k"], acq["blur"],
                                         pts)
    if noise:
        y = _noise(mean, rng, eta, sigma_d, K, full_well, quantize)
    else:
        y = K * mean if full_well is None else K * np.minimum(mean, full_well)
    return y, K * ref, K * samp, mean


def oct_interferogram(sample=None, center_nm=840.0, bandwidth_nm=50.0, mode="sd", n_pixels=2048, wl_min_nm=None,
                      wl_max_nm=None, spectrometer_fwhm_px=1.0, linewidth_nm=None, sweep_nonlinearity=0.0,
                      source_spectrum=None, photons_ref_per_pixel=20000.0, photons_mirror_per_pixel=None,
                      eta=0.8, sigma_d=10.0, K=1.0, full_well=None, quantize=False, reference_phase_rad=0.0,
                      mismatch_material=None, mismatch_length_mm=0.0, focus_um=None, beam_waist_um=None,
                      oversample=8, noise=True, seed=0, grid="lambda"):
    """層の並び(``sample``)を OCT で 1 本測った**干渉スペクトル**(``table``)。

    ``sample`` = {"ambient": "air", "surface_um": 表面の光路(参照腕との差、空気中 µm、負なら鏡像の側),
    "layers": [{"material", "thickness_um", "attenuation_per_mm"(強度の減衰係数 µ_t、往復で exp(−2µd)),
    "scatterers_per_mm"(層の中の点散乱体の密度)、"scatter_amplitude"(1 個の振幅反射率)}, …],
    "substrate": 材料}。省略時は空気 / PMMA 25 µm / ポリカーボネート 40 µm / ガラス相当の基板。

    場の和: E_s(k) = Σ_j r_j(k) T_j A_j exp(2ik Δ_j(k))、Δ_j(k) = surface + Σ_(上の層) n_i(k) d_i
    (位相屈折率で位相、**群遅延は自然に出る**)、r_j = (n_上 − n_下)/(n_上 + n_下)(各 k で)、T_j = Π(1 − r²)、
    A_j = exp(−Σ µ_i d_i)。参照光(振幅 1、位相 ``reference_phase_rad``)と足して |E_r + s·E_s|² ×光源 S(k)
    (s² = photons_mirror/photons_ref)—— 相互相関・自己相関・DC が全部入る。

    検出: ``mode="sd"`` は分光器(``grid="lambda"`` = λ 等間隔の画素、``"k"`` = k 等間隔の画素。画素の箱で
    積分 + 分解能 ``spectrometer_fwhm_px`` のガウス)、
    ``mode="ss"`` は時間等間隔の波長掃引(k(t) = k_lo + Δk (t + ε t(1−t))、ε = ``sweep_nonlinearity``、
    瞬時線幅 ``linewidth_nm`` のガウス、各標本は瞬時の値 —— 画素の箱が無いので roll-off は線幅だけで決まる)。
    細かい等間隔 k(1 画素 ``oversample`` 点)で作ってから、分光器は画素の区間で積分、掃引は標本の k で読む。
    雑音: ショット(電子の平方根)+ 読み出し σ_d e⁻、×K で DN、``full_well`` で飽和、``quantize`` で整数化。
    分散の不一致: 試料腕だけに ``mismatch_material`` が ``mismatch_length_mm``(群遅延は参照腕で合わせる)。
    焦点: ``focus_um``(物理深さ)と ``beam_waist_um`` を渡すと、共焦点の結合 (1 + ((z − z_f)/z_R)²)^(−1/2)。

    返り値: dict(kind="oct_interferogram", spectrum (N,) DN, wavelength_nm, k_rad_per_um(画素の中心の真の k)、
    reference_spectrum(参照腕だけ・雑音なし)、sample_only_spectrum(試料腕だけ・雑音なし = 自己相関の素)、
    interfaces(真値: 物理深さ・群遅延の光路・反射率)、settings)。
    """
    op = "oct_interferogram"
    if sample is None:
        sample = {"layers": [{"material": "PMMA", "thickness_um": 25.0},
                             {"material": "POLYCARBONATE", "thickness_um": 40.0}],
                  "substrate": {"n": 1.51, "n_group": 1.53, "name": "glass"}, "surface_um": 150.0}
    acq = _acq_setup(op, center_nm, bandwidth_nm, mode, n_pixels, wl_min_nm, wl_max_nm, spectrometer_fwhm_px,
                     linewidth_nm, sweep_nonlinearity, source_spectrum, oversample, grid)
    k0 = acq["k0"]
    amb_f, layers, sub_f, sub = _parse_layers(sample, k0, op)
    surf = _finite(sample.get("surface_um", 150.0), "surface_um", op)
    pr = _pos(photons_ref_per_pixel, "photons_ref_per_pixel", op)
    pm = pr if photons_mirror_per_pixel is None else _pos(photons_mirror_per_pixel, "photons_mirror_per_pixel", op)
    et = _pos(eta, "eta", op)
    sd = _nonneg(sigma_d, "sigma_d", op)
    Kg = _pos(K, "K", op)
    fwell = None if full_well is None else _pos(full_well, "full_well", op)
    rng = np.random.default_rng(int(seed))
    fns = [amb_f] + [L["fn"] for L in layers] + [sub_f]
    nm = len(fns)
    kf = acq["k_fine"]
    Nk = np.stack([f(kf) for f in fns])
    # 共焦点
    if (focus_um is None) != (beam_waist_um is None):
        raise ValueError("%s: pass both focus_um and beam_waist_um (or neither)" % op)
    if focus_um is not None:
        zf = _finite(focus_um, "focus_um", op)
        w0 = _pos(beam_waist_um, "beam_waist_um", op)
        zR = np.pi * w0 ** 2 * 1.5 / (acq["lam0"] / 1000.0)
        gate = (lambda z: (1.0 + ((z - zf) / zR) ** 2) ** -0.5)
    else:
        gate = (lambda z: 1.0)
    rx = _Rx()
    truth = []
    path = np.zeros(nm)
    z_phys, amp_t, att = 0.0, 1.0, 1.0
    bounds = [0] + list(range(1, len(layers) + 1))
    for j in range(len(layers) + 1):
        up, dn = j, j + 1                      # 材料の番号: 0 = 周囲、1..L = 層、L+1 = 基板

        def rfn(Nm, up=up, dn=dn):
            return (Nm[up] - Nm[dn]) / (Nm[up] + Nm[dn])
        r0 = float(rfn(np.stack([f(np.array([k0])) for f in fns]))[0])
        a = amp_t * att * gate(z_phys)
        rx.add(a, surf, path.copy(), rfn)
        ng_path = surf + sum(path[m] * _group_index_at(_mat_of(sample, m), acq["lam0"], op) if m > 0 else path[m]
                             for m in range(nm))
        truth.append({"index": j, "depth_um": z_phys, "group_delay_um": ng_path, "r": r0, "R": r0 * r0,
                      "amplitude": a * r0})
        if j == len(layers):
            break
        L = layers[j]
        # 層の中の散乱体
        nsc = rng.poisson(L["scatterers_per_mm"] * L["thickness_um"] / 1000.0) if L["scatterers_per_mm"] > 0 else 0
        T_in = amp_t * (1 - r0 * r0)
        for zz in np.sort(rng.uniform(0, L["thickness_um"], nsc)):
            p = path.copy()
            p[dn] += zz
            aa = T_in * att * math.exp(-L["mu_per_mm"] * zz / 1000.0) * gate(z_phys + zz)
            rx.add(aa * L["scatter_amplitude"] * rng.standard_normal(), surf, p, None)
        amp_t = T_in
        att *= math.exp(-L["mu_per_mm"] * L["thickness_um"] / 1000.0)
        path[dn] += L["thickness_um"]
        z_phys += L["thickness_um"]
    _ = bounds
    E = _field(kf, rx, fns, Nk)
    if mismatch_material is not None and _nonneg(mismatch_length_mm, "mismatch_length_mm", op) > 0:
        Lm = float(mismatch_length_mm) * 1000.0
        fm, _n = _index_fn(mismatch_material, k0, op)
        ngm = _group_index_at(mismatch_material, acq["lam0"], op)
        E = E * np.exp(2j * kf * Lm * (fm(kf) - ngm))
    y, ref, samp, mean = _acquire(acq, E, pr, pm, float(reference_phase_rad), et, sd, Kg, fwell, bool(quantize),
                                  bool(noise), rng)
    return {"kind": "oct_interferogram", "mode": acq["mode"], "spectrum": y, "wavelength_nm": acq["wl"],
            "k_rad_per_um": acq["k_px"], "k_linear": acq["k_uniform"], "reference_spectrum": ref,
            "sample_only_spectrum": samp, "mean_electrons": mean, "center_nm": acq["lam0"],
            "bandwidth_nm": acq["dlam"], "interfaces": truth,
            "layers": [{"label": L["label"], "thickness_um": L["thickness_um"],
                        "group_index": _group_index_at(_mat_of(sample, i + 1), acq["lam0"], op)}
                       for i, L in enumerate(layers)],
            "settings": {"photons_ref_per_pixel": pr, "photons_mirror_per_pixel": pm, "eta": et, "sigma_d": sd,
                         "K": Kg, "n_pixels": acq["N"], "wl_min_nm": acq["lo"], "wl_max_nm": acq["hi"],
                         "reference_phase_rad": float(reference_phase_rad)}}


def _mat_of(sample, m):
    """材料の番号 → 材料(0 = 周囲、1..L = 層、L+1 = 基板)。"""
    layers = sample["layers"]
    if m == 0:
        return sample.get("ambient", "air") if not (isinstance(sample.get("ambient"), str) and
                                                    sample.get("ambient", "air").upper() in ("AIR", "VACUUM")) else 1.0
    if m <= len(layers):
        return layers[m - 1]["material"]
    return sample.get("substrate", 1.5)


# --------------------------------------------------------------------------- #
# 3. B スキャンの合成                                                            #
# --------------------------------------------------------------------------- #
def oct_bscan_simulate(sample2d=None, width_um=1500.0, n_columns=256, center_nm=840.0, bandwidth_nm=50.0, mode="sd",
                       n_pixels=1024, wl_min_nm=None, wl_max_nm=None, spectrometer_fwhm_px=1.0, linewidth_nm=None,
                       sweep_nonlinearity=0.0, photons_ref_per_pixel=20000.0, photons_mirror_per_pixel=None,
                       eta=0.8, sigma_d=10.0, K=1.0, beam_waist_um=6.0, focus_um=None, illumination="point",
                       focus_medium_index=1.5, oversample=4, noise=True, seed=0):
    """断面(``sample2d``)を横に走査した **B スキャンの干渉スペクトルの束**(``table``)。

    ``sample2d`` = {"materials": [周囲, 層 1, …, 基板], "interfaces_um": [(W_fine,) の物理深さ, …] (上から、
    W_fine は任意の本数で横に線形補間。深さ 0 = 周囲の媒質の中の基準面)、"surface_um": 基準面の光路
    (参照腕との差、空気中 µm)、"scatter": [{"layer": i,
    "density_per_mm2", "amplitude"}] (断面内の点散乱体 —— 塗装の顔料・接着剤のフィラー)、
    "inclusions": [{"x_um", "z_um", "radius_um", "material"}] (空洞・異物。上下の面で反射し、
    その下の界面の光路を変える)、"points": [{"x_um", "z_um", "amplitude"}] (置いた点散乱体 —— 横の点像の採点用)、"attenuation_per_mm": 層ごとの減衰}。省略時は段差を越えるコートの例。

    各列: 細かい横の副標本(ビーム半径の 1/3 間隔)ごとに上から材料の区間を作り、境界 = 反射体、
    光路 = 材料ごとの距離。ビームの重み exp(−2(x − x')²/w(z)²)(往復、w(z) = w0 √(1 + (Δz/z_R)²))、
    共焦点の結合: ``illumination="point"`` は (1 + u²)^(−1/2)、``"line"``(ライン照明、片方向だけ共焦点)は
    (1 + u²)^(−1/4)、u = (z − z_f)/z_R、z_R = π w0² n/λ0。ライン照明は 1 回で全列を撮る(走査の時間ずれなし)。

    返り値: dict(kind="oct_bscan_spectra", spectra (W, N), wavelength_nm, k_rad_per_um, reference_spectrum,
    sample_only_spectrum(列ごとの試料腕だけ・雑音なし —— 自己相関のアーチファクトの素),
    x_um, truth={interfaces_um (n_if, W), inclusions}, settings)。
    """
    op = "oct_bscan_simulate"
    W = _count(n_columns, "n_columns", op, 2, 4096)
    width = _pos(width_um, "width_um", op)
    if illumination not in ("point", "line"):
        raise ValueError("%s: illumination must be 'point' or 'line', got %r" % (op, illumination))
    acq = _acq_setup(op, center_nm, bandwidth_nm, mode, n_pixels, wl_min_nm, wl_max_nm, spectrometer_fwhm_px,
                     linewidth_nm, sweep_nonlinearity, None, oversample)
    k0, lam_um = acq["k0"], acq["lam0"] / 1000.0
    if sample2d is None:
        xs = np.linspace(0, 1, 64)
        step = 60.0 * (xs > 0.5)
        sample2d = {"materials": ["air", {"n": 1.50, "n_group": 1.52, "name": "coat"}, {"n": 1.55, "n_group": 1.58}],
                    "interfaces_um": [0.0 + 0 * xs, 40.0 + step * 0.0 + 0 * xs], "surface_um": 100.0}
    if not isinstance(sample2d, dict) or "materials" not in sample2d or "interfaces_um" not in sample2d:
        raise ValueError("%s: sample2d needs 'materials' and 'interfaces_um'" % op)
    mats = list(sample2d["materials"])
    ifs = [np.atleast_1d(np.asarray(z, float)) for z in sample2d["interfaces_um"]]
    if len(mats) != len(ifs) + 1:
        raise ValueError("%s: need len(materials) == len(interfaces_um) + 1 (got %d and %d)" % (op, len(mats), len(ifs)))
    for z in ifs:
        if not np.all(np.isfinite(z)):
            raise ValueError("%s: interfaces_um must be finite" % op)
    fns = [_index_fn(m, k0, op)[0] for m in mats]
    incs = list(sample2d.get("inclusions", []))
    inc_mat_idx = []
    for inc in incs:
        for key in ("x_um", "z_um", "radius_um", "material"):
            if key not in inc:
                raise ValueError("%s: inclusion needs %s" % (op, key))
        fns.append(_index_fn(inc["material"], k0, op)[0])
        inc_mat_idx.append(len(fns) - 1)
    nmat = len(fns)
    att = list(sample2d.get("attenuation_per_mm", [0.0] * len(mats)))
    if len(att) != len(mats):
        raise ValueError("%s: attenuation_per_mm needs one value per material" % op)
    att = [_nonneg(a, "attenuation_per_mm", op) for a in att] + [0.0] * len(incs)
    surf = _finite(sample2d.get("surface_um", 100.0), "surface_um", op)
    w0 = _pos(beam_waist_um, "beam_waist_um", op)
    nfoc = _pos(focus_medium_index, "focus_medium_index", op)
    zR = np.pi * w0 ** 2 * nfoc / lam_um
    zf = float(np.mean([np.mean(z) for z in ifs])) if focus_um is None else _finite(focus_um, "focus_um", op)
    expo = -0.5 if illumination == "point" else -0.25
    pr = _pos(photons_ref_per_pixel, "photons_ref_per_pixel", op)
    pm = pr if photons_mirror_per_pixel is None else _pos(photons_mirror_per_pixel, "photons_mirror_per_pixel", op)
    rng = np.random.default_rng(int(seed))
    x_cols = np.linspace(0, width, W)
    dxs = w0 / 3.0
    xs_fine = np.arange(-3 * w0, width + 3 * w0 + dxs, dxs)
    prof_x = np.linspace(0, width, max(len(z) for z in ifs))
    zif = np.stack([np.interp(xs_fine, np.linspace(0, width, len(z)), z) if len(z) > 1 else np.full(xs_fine.size, z[0])
                    for z in ifs])                                          # (n_if, Wf)
    _ = prof_x
    # 散乱体(断面内)
    scat = []
    for s in sample2d.get("scatter", []):
        li = int(s["layer"])
        if not (1 <= li <= len(ifs) - 1 + 1) or li >= len(mats):
            raise ValueError("%s: scatter layer %r out of range" % (op, li))
        dens = _nonneg(s.get("density_per_mm2", 0.0), "density_per_mm2", op)
        amp = _nonneg(s.get("amplitude", 1e-3), "amplitude", op)
        top = zif[li - 1]
        bot = zif[li] if li < len(ifs) else zif[li - 1] + _pos(s.get("depth_um", 200.0), "depth_um", op)
        area = float(np.sum(np.maximum(bot - top, 0)) * dxs) / 1e6
        n = rng.poisson(dens * area)
        if n > MAX_REFLECTORS * 4:
            raise ValueError("%s: %d scatterers exceed the cap" % (op, n))
        xi = rng.uniform(xs_fine[0], xs_fine[-1], n)
        tb = np.interp(xi, xs_fine, top)
        bb = np.interp(xi, xs_fine, bot)
        zi = tb + rng.uniform(0, 1, n) * np.maximum(bb - tb, 0)
        scat.append((li, xi, zi, amp * rng.standard_normal(n)))

    def segments(x):
        """x での上から下への (z_top, z_bot, material) の区間。"""
        zz = [np.interp(x, xs_fine, zif[i]) for i in range(len(ifs))]
        segs = [(-np.inf, zz[0], 0)]
        for i in range(len(ifs)):
            segs.append((zz[i], zz[i + 1] if i + 1 < len(ifs) else np.inf, i + 1))
        for ci, inc in enumerate(incs):
            dx = x - float(inc["x_um"])
            r = float(inc["radius_um"])
            if abs(dx) < r:
                h = math.sqrt(r * r - dx * dx)
                a, b = float(inc["z_um"]) - h, float(inc["z_um"]) + h
                new = []
                for (t, bt, m) in segs:
                    if bt <= a or t >= b:
                        new.append((t, bt, m))
                        continue
                    if t < a:
                        new.append((t, a, m))
                    new.append((max(t, a), min(bt, b), inc_mat_idx[ci]))
                    if bt > b:
                        new.append((b, bt, m))
                segs = new
        return segs

    def path_to(segs, z):
        p = np.zeros(nmat)
        a = 1.0
        for (t, b, m) in segs:
            if t == -np.inf:
                t = 0.0                      # 周囲の媒質は深さ 0(参照面)から数える
            if z <= t:
                break
            d = min(b, z) - t
            p[m] += d
            a *= math.exp(-att[m] * d / 1000.0)
        return p, a

    kf = acq["k_fine"]
    Nk = np.stack([f(kf) for f in fns])
    N0 = np.stack([f(np.array([k0])) for f in fns])[:, 0]
    # 副標本ごとの反射体(境界)
    sub_rx = []
    for xf in xs_fine:
        segs = segments(xf)
        items = []
        T = 1.0
        for i in range(1, len(segs)):
            z = segs[i][0]
            up, dn = segs[i - 1][2], segs[i][2]
            if up == dn:
                continue
            p, a = path_to(segs, z)
            r0 = (N0[up] - N0[dn]) / (N0[up] + N0[dn])
            items.append((z, p, a * T, up, dn))
            T *= (1 - r0 * r0)
        sub_rx.append(items)
    # 散乱体の光路(最寄りの副標本の区間で)
    scat_items = []
    for (li, xi, zi, ai) in scat:
        for x, z, a in zip(xi, zi, ai):
            segs = segments(x)
            p, at = path_to(segs, z)
            scat_items.append((x, z, p, a * at))
    for pt in sample2d.get("points", []):
        for key in ("x_um", "z_um", "amplitude"):
            if key not in pt:
                raise ValueError("%s: point needs %s" % (op, key))
        x, z = _finite(pt["x_um"], "point x_um", op), _finite(pt["z_um"], "point z_um", op)
        p, at = path_to(segments(x), z)
        scat_items.append((x, z, p, _finite(pt["amplitude"], "point amplitude", op) * at))
    spectra = np.empty((W, acq["N"]))
    E_all = np.empty((W, kf.size), complex)
    for c, xc in enumerate(x_cols):
        rx = _Rx()
        near = np.flatnonzero(np.abs(xs_fine - xc) <= 3 * w0 * 3)
        wsum = {}
        for j in near:
            for (z, p, a, up, dn) in sub_rx[j]:
                u = (z - zf) / zR
                wz = w0 * math.sqrt(1 + u * u)
                g = math.exp(-2 * (xs_fine[j] - xc) ** 2 / wz ** 2)
                gate = (1 + u * u) ** expo

                def rfn(Nm, up=up, dn=dn):
                    return (Nm[up] - Nm[dn]) / (Nm[up] + Nm[dn])
                rx.add(a * g * gate * dxs / (math.sqrt(math.pi / 2) * wz), surf, p, rfn)
                wsum[j] = 1
        for (x, z, p, a) in scat_items:
            u = (z - zf) / zR
            wz = w0 * math.sqrt(1 + u * u)
            d = x - xc
            if abs(d) > 3 * wz:
                continue
            rx.add(a * math.exp(-2 * d * d / wz ** 2) * (1 + u * u) ** expo, surf, p, None)
        E_all[c] = _field(kf, rx, fns, Nk)
    y, ref, samp, mean = _acquire(acq, E_all, pr, pm, 0.0, _pos(eta, "eta", op), _nonneg(sigma_d, "sigma_d", op),
                                  _pos(K, "K", op), None, False, bool(noise), rng)
    spectra[:] = y
    truth_if = np.stack([np.interp(x_cols, xs_fine, zif[i]) for i in range(len(ifs))])
    return {"kind": "oct_bscan_spectra", "mode": acq["mode"], "spectra": spectra, "wavelength_nm": acq["wl"],
            "k_rad_per_um": acq["k_px"], "k_linear": False, "reference_spectrum": ref,
            "sample_only_spectrum": samp,
            "center_nm": acq["lam0"], "bandwidth_nm": acq["dlam"], "x_um": x_cols,
            "truth": {"interfaces_um": truth_if, "inclusions": incs, "surface_um": surf,
                      "group_index": [_group_index_at(m if not (isinstance(m, str) and m.upper() == "AIR") else 1.0,
                                                      acq["lam0"], op) for m in mats]},
            "settings": {"beam_waist_um": w0, "rayleigh_um": zR, "focus_um": zf, "illumination": illumination,
                         "n_pixels": acq["N"], "photons_ref_per_pixel": pr, "photons_mirror_per_pixel": pm}}


# --------------------------------------------------------------------------- #
# 4. 処理                                                                        #
# --------------------------------------------------------------------------- #
def _spectra_of(t, op):
    t = _table(t, ("oct_interferogram", "oct_bscan_spectra"), op)
    key = "spectrum" if t["kind"] == "oct_interferogram" else "spectra"
    s = np.asarray(t[key])
    k = np.asarray(t["k_rad_per_um"], float)
    if s.shape[-1] != k.size or k.size < 16:
        raise ValueError("%s: spectrum length %d does not match k (%d)" % (op, s.shape[-1], k.size))
    if not np.all(np.isfinite(s)) or not np.all(np.isfinite(k)):
        raise ValueError("%s: spectrum / k must be finite" % op)
    d = np.diff(k)
    if not (np.all(d > 0) or np.all(d < 0)):
        raise ValueError("%s: k must be strictly monotonic" % op)
    return t, key, s, k


def oct_k_linearize(interferogram, method="cubic", n_out=None, k_calibration=None):
    """干渉スペクトルを **k 等間隔**に並べ直す(``table`` → ``table``)。

    分光器の画素は λ で等間隔、波長掃引の標本は時間で等間隔 —— どちらも k(= 2π/λ)では等間隔でなく、
    そのまま FFT すると**深いほどピークが広がる**(深さに比例する chirp)。``method``: "cubic"(3 次スプライン、
    既定)/ "linear"(線形補間 —— 深いところで副ピークと roll-off の悪化が出る)/ "none"(並べ直さずに k を
    等間隔と**仮定する**だけ。比較用 —— 何が壊れるかを見るため)。``k_calibration`` を渡すと表の
    ``k_rad_per_um`` の代わりにそれを各標本の k とみなす(波長掃引の k クロック・分光器の較正の誤り)。

    出力の k は昇順の等間隔(点数 ``n_out``、既定は入力と同じ)。``reference_spectrum`` も同じく並べ直す。
    """
    op = "oct_k_linearize"
    t, key, s, k = _spectra_of(interferogram, op)
    if k_calibration is not None:
        kc = np.asarray(k_calibration, float)
        if kc.shape != k.shape or not np.all(np.isfinite(kc)):
            raise ValueError("%s: k_calibration must be finite with the same length as the spectrum" % op)
        dk = np.diff(kc)
        if not (np.all(dk > 0) or np.all(dk < 0)):
            raise ValueError("%s: k_calibration must be strictly monotonic" % op)
        k = kc
    n = k.size if n_out is None else _count(n_out, "n_out", op, 16, 1 << 18)
    o = np.argsort(k)
    ks = k[o]
    ku = np.linspace(ks[0], ks[-1], n)

    def rs(y):
        y = np.asarray(y, float)[..., o]
        if method == "cubic":
            from scipy.interpolate import CubicSpline
            return CubicSpline(ks, y, axis=-1)(ku)
        if method == "linear":
            if y.ndim == 1:
                return np.interp(ku, ks, y)
            return np.stack([np.interp(ku, ks, r) for r in y])
        if method == "none":
            if n != k.size:
                raise ValueError("%s: method='none' cannot change the number of samples" % op)
            return y
        raise ValueError("%s: method must be 'cubic', 'linear' or 'none', got %r" % (op, method))
    out = dict(t)
    out[key] = rs(s)
    if t.get("reference_spectrum") is not None:
        out["reference_spectrum"] = rs(t["reference_spectrum"])
    if t.get("sample_only_spectrum") is not None:
        out["sample_only_spectrum"] = rs(t["sample_only_spectrum"])
    out["k_rad_per_um"] = ku
    out["wavelength_nm"] = 2 * np.pi / ku * 1000.0
    out["k_linear"] = True
    out["k_linearize_method"] = method
    return out


def _require_linear(t, op):
    if not t.get("k_linear"):
        raise ValueError("%s: the spectrum is not on a uniform k grid — call oct_k_linearize first" % op)
    k = np.asarray(t["k_rad_per_um"], float)
    d = np.diff(k)
    if np.max(np.abs(d - d.mean())) > 1e-6 * abs(d.mean()):
        raise ValueError("%s: k_rad_per_um is not uniformly spaced" % op)
    return k


def _dc_removed(t, key, s, dc, op):
    s = np.asarray(s)
    if dc == "reference":
        ref = t.get("reference_spectrum")
        if ref is None:
            raise ValueError("%s: dc='reference' needs reference_spectrum in the table" % op)
        return s - np.asarray(ref)
    if dc == "reference+sample":
        ref, so = t.get("reference_spectrum"), t.get("sample_only_spectrum")
        if ref is None or so is None:
            raise ValueError("%s: dc='reference+sample' needs reference_spectrum and sample_only_spectrum" % op)
        return s - np.asarray(ref) - np.asarray(so)
    if dc == "mean":
        if s.ndim == 1:
            return s - s.mean()
        return s - np.median(s, axis=0, keepdims=True)
    if dc == "smooth":
        from scipy import ndimage
        sig = max(2.0, s.shape[-1] / 80.0)
        return s - ndimage.gaussian_filter1d(np.real(s), sig, axis=-1, mode="nearest")
    if dc in (None, "none"):
        return s
    raise ValueError("%s: dc must be 'reference', 'reference+sample', 'mean', 'smooth' or 'none', got %r"
                     % (op, dc))


def oct_dispersion_compensate(interferogram, a2=0.0, a3=0.0, k_center=None, dc="reference"):
    """数値分散補償(``table`` → ``table``): DC を除いた k 等間隔のスペクトルを解析信号にして exp(−i(a2Δk² + a3Δk³))。

    Δk = k − k_c(既定は k の範囲の中央)。a2 [µm²]、a3 [µm³] は ``oct_dispersion_broadening`` の a2・a3
    (既知の材料)か ``oct_dispersion_estimate``(測ったスペクトルから)。解析信号は正の周波数だけなので、
    補償後の A スキャンは片側(鏡像の側は捨てる —— 鏡像の分離ではない)。k 等間隔でなければ拒否。
    """
    op = "oct_dispersion_compensate"
    t, key, s, _k = _spectra_of(interferogram, op)
    k = _require_linear(t, op)
    from scipy.signal import hilbert
    x = _dc_removed(t, key, s, dc, op)
    if np.iscomplexobj(x):
        z = x
    else:
        z = hilbert(x, axis=-1)
    kc = 0.5 * (k[0] + k[-1]) if k_center is None else _pos(k_center, "k_center", op)
    dk = k - kc
    ph = _finite(a2, "a2", op) * dk ** 2 + _finite(a3, "a3", op) * dk ** 3
    out = dict(t)
    out[key] = z * np.exp(-1j * ph)
    out["dc_removed"] = True
    out["dispersion"] = {"a2": float(a2), "a3": float(a3), "k_center": kc}
    for extra in ("reference_spectrum", "sample_only_spectrum"):
        out.pop(extra, None)
    return out


def oct_dispersion_estimate(interferogram, method="sharpness", a2_range=(-2000.0, 2000.0), a3_range=None,
                            z_range_um=None, dc="reference", n_grid=81):
    """分散補償の係数 a2・a3 を測ったスペクトルから推定する(``table`` → ``table``)。

    ``method="mirror"``: 鏡(反射体 1 つ)のスペクトル。FFT でピークだけを切り出し、逆 FFT した解析信号の位相を
    ``complexops.phase_unwrap`` でアンラップし、振幅の重みで Δk の 3 次式に当てる → a2 = 2 次の係数、
    a3 = 3 次の係数(Wojtkowski ら 2004 の鏡による較正)。
    ``method="sharpness"``: 試料そのもの。A スキャンの鋭さ Σ|A|⁴/(Σ|A|²)² が最大になる a2(と a3)を格子 →
    黄金分割で探す(``z_range_um`` の範囲で数える)。どちらも k 等間隔が前提(でなければ拒否)。

    返り値: dict(kind="oct_dispersion_fit", a2, a3, method, sharpness / residual_rad)。
    """
    op = "oct_dispersion_estimate"
    t, key, s, _k = _spectra_of(interferogram, op)
    k = _require_linear(t, op)
    x = _dc_removed(t, key, s, dc, op)
    if x.ndim != 1:
        x = x.reshape(-1, x.shape[-1])
    kc = 0.5 * (k[0] + k[-1])
    dk = k - kc
    N = k.size
    if method == "mirror":
        if x.ndim != 1:
            raise ValueError("%s: method='mirror' needs a single spectrum" % op)
        from scipy.signal import hilbert
        z = hilbert(np.real(x)) if not np.iscomplexobj(x) else x
        F = np.fft.fft(z)
        mag = np.abs(F[1:N // 2])
        j = int(np.argmax(mag)) + 1
        half = max(4, int(0.05 * N))
        G = np.zeros_like(F)
        G[max(1, j - half):j + half + 1] = F[max(1, j - half):j + half + 1]
        a = np.fft.ifft(G)
        import complexops
        ph = complexops.phase_unwrap(np.angle(a)[None, :])[0]
        w = np.abs(a) ** 2
        msk = w > 0.05 * w.max()
        if np.count_nonzero(msk) < 8:
            raise ValueError("%s: too little spectral support to fit the mirror phase" % op)
        c = np.polyfit(dk[msk], ph[msk], 3, w=np.sqrt(w[msk]))
        res = ph[msk] - np.polyval(c, dk[msk])
        return {"kind": "oct_dispersion_fit", "method": "mirror", "a2": float(c[1]), "a3": float(c[0]),
                "k_center": kc, "residual_rad": float(np.sqrt(np.mean(res ** 2)))}
    if method != "sharpness":
        raise ValueError("%s: method must be 'mirror' or 'sharpness', got %r" % (op, method))
    from scipy.signal import hilbert
    zx = x if np.iscomplexobj(x) else hilbert(x, axis=-1)
    zxs = np.atleast_2d(zx)
    dz = np.pi / (N * (k[1] - k[0]))
    zz = np.arange(N) * dz
    if z_range_um is None:
        sel = (zz > 5 * dz) & (zz < zz[N // 2])
    else:
        lo, hi = float(z_range_um[0]), float(z_range_um[1])
        sel = (zz >= lo) & (zz <= hi)
    if np.count_nonzero(sel) < 8:
        raise ValueError("%s: z_range_um selects too few samples" % op)

    def sharp(a2, a3):
        A = np.fft.fft(zxs * np.exp(-1j * (a2 * dk ** 2 + a3 * dk ** 3)), axis=-1)[:, sel]
        p = np.abs(A) ** 2
        return float(np.sum(p ** 2) / np.sum(p) ** 2)
    a2lo, a2hi = float(a2_range[0]), float(a2_range[1])
    if not (a2lo < a2hi):
        raise ValueError("%s: a2_range must be (lo, hi) with lo < hi" % op)
    ng = _count(n_grid, "n_grid", op, 5, 2001)

    def best1(f, lo, hi):
        g = np.linspace(lo, hi, ng)
        v = [f(a) for a in g]
        i = int(np.argmax(v))
        a, b = g[max(0, i - 1)], g[min(ng - 1, i + 1)]
        gr = (math.sqrt(5) - 1) / 2
        c, d = b - gr * (b - a), a + gr * (b - a)
        fc, fd = f(c), f(d)
        for _ in range(40):
            if fc > fd:
                b, d, fd = d, c, fc
                c = b - gr * (b - a)
                fc = f(c)
            else:
                a, c, fc = c, d, fd
                d = a + gr * (b - a)
                fd = f(d)
        return 0.5 * (a + b)
    a2 = best1(lambda a: sharp(a, 0.0), a2lo, a2hi)
    a3 = 0.0
    if a3_range is not None:
        a3 = best1(lambda a: sharp(a2, a), float(a3_range[0]), float(a3_range[1]))
        a2 = best1(lambda a: sharp(a, a3), a2 - (a2hi - a2lo) / ng * 2, a2 + (a2hi - a2lo) / ng * 2)
    return {"kind": "oct_dispersion_fit", "method": "sharpness", "a2": float(a2), "a3": float(a3), "k_center": kc,
            "sharpness": sharp(a2, a3), "sharpness_uncompensated": sharp(0.0, 0.0)}


def oct_ascan(interferogram, window="hann", dc="reference", zero_pad=2, quadrature=None, a2=0.0, a3=0.0,
              k_center=None):
    """k 等間隔の干渉スペクトル → **A スキャン**(深さ方向の反射の振幅、``table``)。

    手順: DC 除去(``dc``: "reference" = 参照腕だけのスペクトルを引く / "reference+sample" = 試料腕だけも引く
    (自己相関のアーチファクトを消す)/ "mean"(束なら列の中央値)/ "smooth"(各スペクトルの緩やかな包絡 =
    幅 N/80 のガウスの低域を引く。参照を測っていない記録向け)/ "none")→ 窓(``window``)→ 分散補償(a2・a3、0 なら何もしない)
    → ``zero_pad`` 倍に詰めて FFT。深さ = **片道の光路**(空気中 µm)z_j = π j/(N_pad δk)、範囲 z_max = π/(2δk)。

    実数のスペクトルは ±z が区別できない(**鏡像**: 参照腕より手前の面は同じ深さに折り返して見える)ので
    正の側だけを返す。``quadrature`` に参照腕の位相を π/2 ずらしたスペクトル(同じ表の形)を渡すと
    複素のスペクトル I₀ + i I_{π/2} を組み、**両側**(−z_max〜+z_max)を返す(full range)。
    分散補償を掛けたスペクトル(複素、``oct_dispersion_compensate`` の出力)は片側。

    返り値: dict(kind="oct_ascan", z_um, amplitude(|A|)、db(20 log10 |A|)、noise_sigma(|A|² の中央値から
    推定した雑音の rms、信号が深さの一部しか占めない前提)、snr_db(最大ピーク)、z_max_um、center_nm、
    bandwidth_nm、two_sided)。
    """
    op = "oct_ascan"
    t, key, s, _k = _spectra_of(interferogram, op)
    k = _require_linear(t, op)
    N = k.size
    dk = k[1] - k[0]
    P = _count(zero_pad, "zero_pad", op, 1, 64)
    already = bool(t.get("dc_removed"))
    x = s if already else _dc_removed(t, key, s, dc, op)
    two = False
    if quadrature is not None:
        tq, keyq, sq, kq = _spectra_of(quadrature, op)
        if sq.shape != np.shape(s) or not np.allclose(_require_linear(tq, op), k):
            raise ValueError("%s: quadrature spectrum must match the main spectrum's shape and k grid" % op)
        xq = _dc_removed(tq, keyq, sq, dc, op)
        if np.iscomplexobj(x) or np.iscomplexobj(xq):
            raise ValueError("%s: quadrature needs two real spectra (not an analytic / compensated one)" % op)
        x = x + 1j * xq
        two = True
    w = _window(window, N, op)
    kc = 0.5 * (k[0] + k[-1]) if k_center is None else _pos(k_center, "k_center", op)
    a2f, a3f = _finite(a2, "a2", op), _finite(a3, "a3", op)
    if a2f or a3f:
        if not np.iscomplexobj(x):
            from scipy.signal import hilbert
            x = hilbert(x, axis=-1)
        x = x * np.exp(-1j * (a2f * (k - kc) ** 2 + a3f * (k - kc) ** 3))
    # e^{+2ikz} は k の標本 n について e^{+i 2δk z n}: numpy の FFT(核 e^{−2πijn/M})では正の番号
    # j = z δk M/π に立つ → 深さの刻み dz = π/(M δk)。解析信号(Hilbert)も直交の組 I₀ + i I_{π/2} も
    # 正の z を正の番号に置く(参照の位相 π/2 で干渉項は sin(2kz) になるため)。
    F = np.fft.fft(x * w, n=N * P, axis=-1)
    dz = np.pi / (N * P * dk)
    if two:
        A = np.fft.fftshift(F, axes=-1)
        z = (np.arange(N * P) - N * P // 2) * dz
    else:
        A = F[..., :N * P // 2]
        z = np.arange(N * P // 2) * dz
    amp = np.abs(A)
    p = amp ** 2
    ref_sel = np.ones(z.shape, bool)
    ref_sel &= np.abs(z) > 0.15 * np.max(np.abs(z))
    noise = math.sqrt(float(np.median(np.atleast_2d(p)[..., ref_sel])) / LN2)
    pk = float(np.max(np.atleast_2d(amp)[..., np.abs(z) > 4 * dz * P]))
    # 点像の幅(FWHM): 公称の光源(ガウス、center_nm・bandwidth_nm)× 窓 の |FT| を、この k の格子で数値に
    psf = None
    lam0, dlam = t.get("center_nm"), t.get("bandwidth_nm")
    if lam0 and dlam:
        k0 = 2 * np.pi / (float(lam0) / 1000.0)
        dkf = 2 * np.pi * (float(dlam) / 1000.0) / (float(lam0) / 1000.0) ** 2
        S = np.exp(-4 * LN2 * (k - k0) ** 2 / dkf ** 2)
        Q = 64 * N
        g = np.abs(np.fft.fft(S * w, Q))
        g = np.concatenate([g[Q // 2:], g[:Q // 2]])
        hi = np.flatnonzero(g >= g.max() / 2)
        psf = float((hi[-1] - hi[0]) * np.pi / (Q * dk))
    return {"kind": "oct_ascan", "z_um": z, "amplitude": amp, "db": 20 * np.log10(np.maximum(amp, 1e-300)),
            "psf_fwhm_um": psf,
            "noise_sigma": noise, "snr_db": float(20 * np.log10(max(pk, 1e-300) / max(noise, 1e-300))),
            "z_max_um": float(np.pi / (2 * dk)), "dz_um": float(dz), "zero_pad": P, "two_sided": two,
            "window": window, "center_nm": t.get("center_nm"), "bandwidth_nm": t.get("bandwidth_nm"),
            "n_samples": N}


def oct_bscan(spectra, window="hann", dc="reference", zero_pad=1, a2=0.0, a3=0.0, method="cubic", db_range=None,
              k_center=None):
    """B スキャンの干渉スペクトルの束 → **断面像**(深さ × 横、``table``。台帳の宣言は 20 log10 の画像 image2d)。

    各列を ``oct_k_linearize``(``method``)→ ``oct_ascan`` にかける。``dc``: "reference"(既定、参照腕だけの
    スペクトルを引く)/ "mean"(参照を測っていない装置の常套手段 = 列の中央値を引く。★横に一様な界面 ——
    平らな表面 —— の干渉縞も全列に共通なので**一緒に消え**、段差があると片側の深さに負の幽霊が出る)/
    "reference+sample"(自己相関も消す)/ "none"。返り値: dict(kind="oct_bscan", image_db (Z, W)、z_um、x_um、noise_db
    (雑音の rms の dB)、center_nm、bandwidth_nm)。``db_range`` = (下, 上) を渡すと image_db をその範囲に切る。
    """
    op = "oct_bscan"
    t = _table(spectra, "oct_bscan_spectra", op)
    lin = t if t.get("k_linear") else oct_k_linearize(t, method=method)
    a = oct_ascan(lin, window=window, dc=dc, zero_pad=zero_pad, a2=a2, a3=a3, k_center=k_center)
    img = a["db"].T
    if db_range is not None:
        lo, hi = float(db_range[0]), float(db_range[1])
        if not lo < hi:
            raise ValueError("%s: db_range must be (lo, hi) with lo < hi" % op)
        img = np.clip(img, lo, hi)
    return {"kind": "oct_bscan", "image_db": img, "z_um": a["z_um"], "x_um": np.asarray(t.get("x_um")),
            "noise_db": float(20 * np.log10(max(a["noise_sigma"], 1e-300))), "dz_um": a["dz_um"],
            "z_max_um": a["z_max_um"], "center_nm": t.get("center_nm"), "bandwidth_nm": t.get("bandwidth_nm")}


# --------------------------------------------------------------------------- #
# 5. 計測                                                                        #
# --------------------------------------------------------------------------- #
def oct_layer_thickness(ascan, n_group=None, n_interfaces=None, min_snr_db=12.0, z_range_um=None,
                        min_separation_um=None, min_separation_fwhm=1.4, min_prominence_db=0.0,
                        dynamic_range_db=80.0):
    """A スキャンの界面のピーク → **層の光学厚と物理厚**(``table``)。分離できない・見えないときは拒否する。

    ピーク: 雑音の rms(``oct_ascan`` の noise_sigma)の ``min_snr_db`` 上を超える極大(``dsp.find_peaks``、
    間隔 ≥ ``min_separation_um``、既定は軸分解能 0.44 λ0²/Δλ の 0.8 倍)を、``n_interfaces`` 本(強い順に
    選んで深さ順に並べる)。位置は ``dsp.peak_subbin(mode="gauss")``(ガウスの頂点 = 対数放物線で厳密)。
    光学厚 = 隣の界面の光路の差、物理厚 = 光学厚 / n_g。``n_group`` は層ごとの群屈折率(数・``materials``
    の名前・{"n", "n_group"} の模型)、None なら光学厚だけ。

    拒否(ValueError): 見えた界面が ``n_interfaces`` より少ない(薄すぎて 2 本が 1 本に融合した / 散乱で
    下の界面が雑音に沈んだ / 深さ範囲の外)、または隣の界面の間隔が点像の幅(``oct_ascan`` の psf_fwhm_um、窓込み)
    の ``min_separation_fwhm`` 倍より狭い —— 2 つの点像が重なると互いの頂点を引き寄せ、干渉で形も歪むので、
    分離して**見えても**厚さは偏る(1.4 倍で偏りが 1 % を切る —— PoC ``poc_industrial_oct`` の掃引)。
    ``dynamic_range_db``: 探す範囲の最大のピークよりこれ以上弱い極大は数えない(窓の副ローブと数値の床 ——
    雑音の無い合成や SNR が 100 dB を超える強い面では、雑音の床の上に副ローブが「界面」として立つ)。
    ``min_prominence_db`` > 0 なら、ピークが周りの谷から立つ高さ(``scipy.signal.peak_prominences``、探す範囲の
    中だけで数える)がそれ未満のものを界面と数えない —— 強く散乱する層(白の塗装)の中は滑らかに減衰する
    連続体で、その揺らぎの小さな極大を「下の面」と読まないため。
    メッセージに見えた本数と分解能を書く。
    返り値: dict(kind="oct_layers", z_opt_um(界面)、peak_db、optical_thickness_um、group_index、
    thickness_um、resolution_um、snr_db(界面ごと))。
    """
    op = "oct_layer_thickness"
    a = _table(ascan, "oct_ascan", op)
    if a.get("two_sided"):
        raise ValueError("%s: pass a one-sided A-scan (the two-sided full-range scan has a sign to choose first)" % op)
    z = np.asarray(a["z_um"], float)
    amp = np.asarray(a["amplitude"], float)
    if amp.ndim != 1:
        raise ValueError("%s: expected a single A-scan (got shape %s)" % (op, amp.shape))
    lam0 = a.get("center_nm")
    dlam = a.get("bandwidth_nm")
    res = (2 * LN2 / np.pi) * (lam0 / 1000.0) ** 2 / (dlam / 1000.0) if (lam0 and dlam) else 4 * a["dz_um"]
    sep = 0.8 * res if min_separation_um is None else _pos(min_separation_um, "min_separation_um", op)
    thr = a["noise_sigma"] * 10 ** (_finite(min_snr_db, "min_snr_db", op) / 20.0)
    sel = np.ones(z.shape, bool)
    sel &= z > 2.0 * res                                  # DC の近く(残った自己相関)は界面としない
    if z_range_um is not None:
        sel &= (z >= float(z_range_um[0])) & (z <= float(z_range_um[1]))
    if np.any(sel):
        thr = max(thr, float(np.max(amp[sel])) * 10 ** (-_pos(dynamic_range_db, "dynamic_range_db", op) / 20.0))
    import dsp
    work = np.where(sel, amp, 0.0)
    idx = dsp.find_peaks(work, height=thr, distance=max(1, int(round(sep / a["dz_um"]))))
    # ★窓の端で振幅が下り坂のところは、0 で埋めた外側との段差が「極大」に見える → 元の振幅で極大のものだけ
    idx = np.array([i for i in idx if 0 < i < amp.size - 1 and amp[i] >= amp[i - 1] and amp[i] >= amp[i + 1]],
                   dtype=np.int64)
    prom_min = _nonneg(min_prominence_db, "min_prominence_db", op)
    prominence = np.full(idx.size, np.nan)
    if idx.size:
        from scipy.signal import peak_prominences
        on = np.flatnonzero(sel)
        lo_i, hi_i = int(on[0]), int(on[-1]) + 1
        dbs = 20 * np.log10(np.maximum(amp[lo_i:hi_i], 1e-300))
        inside = (idx >= lo_i) & (idx < hi_i)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")          # 高さ 0 の極大(平らな頂上)は prominence 0 で正しく落ちる
            prominence[inside] = peak_prominences(dbs, idx[inside] - lo_i)[0]
        if prom_min > 0:
            keep = np.isfinite(prominence) & (prominence >= prom_min)
            idx, prominence = idx[keep], prominence[keep]
    if n_interfaces is not None:
        n_if = _count(n_interfaces, "n_interfaces", op, 1, 1000)
        if idx.size < n_if:
            raise ValueError("%s: found %d interface(s) above %.1f dB SNR, %d requested — the layers are thinner than "
                             "the axial resolution (%.2f um optical) or a deeper interface is below the noise"
                             % (op, idx.size, float(min_snr_db), n_if, res))
        order = np.argsort(amp[idx])[::-1][:n_if]
        idx, prominence = idx[order], prominence[order]
        o2 = np.argsort(idx)
        idx, prominence = idx[o2], prominence[o2]
    if idx.size == 0:
        raise ValueError("%s: no interface above %.1f dB SNR" % (op, float(min_snr_db)))
    zr = []
    for i in idx:
        if 0 < i < amp.size - 1 and np.all(amp[i - 1:i + 2] > 0):
            zr.append(float(np.interp(dsp.peak_subbin(amp, np.array([i]), mode="gauss")[0], np.arange(z.size), z)))
        else:
            zr.append(float(z[i]))
    zr = np.array(zr)
    opt = np.diff(zr)
    psf = a.get("psf_fwhm_um")
    if psf and opt.size and min_separation_fwhm:
        lim = _nonneg(min_separation_fwhm, "min_separation_fwhm", op) * float(psf)
        if np.min(opt) < lim:
            raise ValueError("%s: interfaces %.2f um apart (optical) are closer than %.2f x the point-spread width "
                             "(%.2f um) — the peaks overlap and bias each other; the layer is too thin to measure "
                             "with this source" % (op, float(np.min(opt)), float(min_separation_fwhm), float(psf)))
    out = {"kind": "oct_layers", "z_opt_um": zr, "peak_db": 20 * np.log10(amp[idx]),
           "snr_db": 20 * np.log10(amp[idx] / a["noise_sigma"]), "prominence_db": prominence,
           "optical_thickness_um": opt,
           "resolution_um": res, "psf_fwhm_um": psf, "group_index": None, "thickness_um": None}
    if n_group is not None:
        ngs = list(n_group) if isinstance(n_group, (list, tuple)) else [n_group] * opt.size
        if len(ngs) != opt.size:
            raise ValueError("%s: n_group has %d entries for %d layers" % (op, len(ngs), opt.size))
        if lam0 is None and any(not isinstance(v, (int, float)) for v in ngs):
            raise ValueError("%s: material names need the A-scan's center_nm" % op)
        g = np.array([_group_index_at(v, lam0, op) if not isinstance(v, dict) else _pos(v.get("n_group", v.get("n")),
                                                                                       "n_group", op) for v in ngs])
        out["group_index"] = g
        out["thickness_um"] = opt / g
    return out


def _per_column(v, W, name, op):
    a = np.asarray(v, float)
    if a.ndim == 0:
        return np.full(W, float(a))
    if a.shape != (W,) or not np.all(np.isfinite(a)):
        raise ValueError("%s: %s must be a number or a finite (W,) array" % (op, name))
    return a


def oct_bscan_boundaries(image, n_boundaries=2, um_per_px=1.0, n_group=None, min_gap_px=4, max_jump_px=2,
                         jump_penalty=0.0, smooth_sigma=1.0, mode="peak", top_px=None, bottom_px=None,
                         reference_rows=None, offset_px=None):
    """B スキャンの**画像**から界面を横に辿る(``image2d`` → ``table``)。装置の出力の図にも使える。

    各界面 = 列ごとに 1 行を選ぶ道で、隣の列との行の差 ≤ ``max_jump_px``、費用 = −(明るさの z 値)の和 +
    ``jump_penalty`` × |行の差| が最小のもの(動的計画法。網膜の層分割の Chiu ら 2010、塗膜の Dong ら 2016 と
    同じ「最短路」の考え方の 1 本ずつ版)。``mode="peak"`` は明るさ(界面は明るい線)、``"edge"`` は下向きの
    明るさの増え方(暗 → 明、散乱の多い層の上の面)。見つけた道の上下 ``min_gap_px`` は次の道で使わない。
    探す範囲: ``top_px`` / ``bottom_px``(数か列ごとの (W,))、または ``reference_rows``(既に見つけた面、例えば
    表面)からの相対 ``offset_px`` = (下限, 上限)。★相対で探すと、面と平行な界面に罰が掛からず、表面の傾きに
    従わない平らな線 —— 自己相関のアーチファクト(層の光学厚の深さに水平に出る)—— は ``jump_penalty`` で
    不利になる。行は明るさの放物線で行以下に詰める。

    厚さ = 隣の界面の行の差 × ``um_per_px``(縦の 1 画素の µm、光路)÷ ``n_group``(層ごと、None なら光学厚)。
    ``reference_rows`` を渡したときは、それを 1 本目の界面として行の表に含める。
    返り値: dict(kind="oct_boundaries", rows (n, W)、thickness_um (n − 1, W)、mean_um、std_um、contrast)。
    画像が平ら・範囲が狭すぎて道が置けないときは拒否。
    """
    op = "oct_bscan_boundaries"
    img = np.asarray(image, float)
    if img.ndim == 3 and img.shape[2] in (3, 4):
        img = img[..., :3].mean(axis=2)
    if img.ndim != 2 or min(img.shape) < 8:
        raise ValueError("%s: need a 2-D image (H, W) with H, W >= 8, got %s" % (op, img.shape))
    if not np.all(np.isfinite(img)):
        raise ValueError("%s: image must be finite" % op)
    nb = _count(n_boundaries, "n_boundaries", op, 1, 64)
    gap = _count(min_gap_px, "min_gap_px", op, 0, 10000)
    J = _count(max_jump_px, "max_jump_px", op, 0, 1000)
    pen = _nonneg(jump_penalty, "jump_penalty", op)
    upp = _pos(um_per_px, "um_per_px", op)
    H, W = img.shape
    if np.ptp(img) <= 0:
        raise ValueError("%s: the image is flat — no boundary to follow" % op)
    from scipy import ndimage
    sg = _nonneg(smooth_sigma, "smooth_sigma", op)
    g = ndimage.gaussian_filter(img, sg) if sg > 0 else img.copy()
    if mode == "peak":
        score = g.copy()
    elif mode == "edge":
        score = np.zeros_like(g)
        score[1:] = g[1:] - g[:-1]
    else:
        raise ValueError("%s: mode must be 'peak' or 'edge', got %r" % (op, mode))
    score = (score - np.median(score)) / max(float(np.std(score)), 1e-12)
    cols = np.arange(W)
    if reference_rows is not None:
        ref = _per_column(reference_rows, W, "reference_rows", op)
        if offset_px is None or len(offset_px) != 2:
            raise ValueError("%s: reference_rows needs offset_px = (lo, hi)" % op)
        lo, hi = int(offset_px[0]), int(offset_px[1])
        if hi - lo < 2:
            raise ValueError("%s: offset_px range is too narrow" % op)
        base = np.round(ref).astype(int)
        offs = np.arange(lo, hi + 1)
        rows_of = base[None, :] + offs[:, None]                       # (O, W) の行
    else:
        t = _per_column(0 if top_px is None else top_px, W, "top_px", op)
        b = _per_column(H if bottom_px is None else bottom_px, W, "bottom_px", op)
        rows_of = np.arange(H)[:, None] * np.ones((1, W), int)
        lo_b, hi_b = np.round(t).astype(int), np.round(b).astype(int)
        ref = None
    nO = rows_of.shape[0]
    inside = (rows_of >= 0) & (rows_of < H)
    if reference_rows is None:
        inside &= (rows_of >= lo_b[None, :]) & (rows_of < hi_b[None, :])
    BIG = 1e9
    blocked = np.zeros((H, W), bool)
    found = []
    steps = np.arange(-J, J + 1)
    for _ in range(nb):
        rr = np.clip(rows_of, 0, H - 1)
        cost = np.where(inside & ~blocked[rr, cols[None, :]], -score[rr, cols[None, :]], BIG)
        acc = cost[:, 0].copy()
        back = np.zeros((nO, W), np.int32)
        idx = np.arange(nO)
        for c in range(1, W):
            best = np.full(nO, np.inf)
            arg = np.zeros(nO, np.int32)
            for d in steps:
                src = idx - d
                ok = (src >= 0) & (src < nO)
                v = np.full(nO, np.inf)
                v[ok] = acc[src[ok]] + pen * abs(int(d))
                better = v < best
                best[better] = v[better]
                arg[better] = src[better]
            acc = best + cost[:, c]
            back[:, c] = arg
        o = int(np.argmin(acc))
        if not np.isfinite(acc[o]) or acc[o] >= BIG * 0.5:
            raise ValueError("%s: could not place boundary %d inside the search range" % (op, len(found) + 1))
        path = np.zeros(W, np.int64)
        path[-1] = o
        for c in range(W - 1, 0, -1):
            path[c - 1] = back[path[c], c]
        prow = rows_of[path, cols]
        found.append(prow)
        for c in range(W):
            blocked[max(0, prow[c] - gap):min(H, prow[c] + gap + 1), c] = True
    found.sort(key=lambda p: float(np.mean(p)))
    rows_f = np.zeros((len(found), W))
    contrast = np.zeros(len(found))
    for bi, p in enumerate(found):
        for c in range(W):
            i = int(p[c])
            if 0 < i < H - 1:
                y0, y1, y2 = g[i - 1, c], g[i, c], g[i + 1, c]
                den = y0 - 2 * y1 + y2
                off = 0.5 * (y0 - y2) / den if den < 0 else 0.0
                rows_f[bi, c] = i + float(np.clip(off, -0.5, 0.5))
            else:
                rows_f[bi, c] = float(i)
        contrast[bi] = float(np.median(g[p, cols]) - np.median(g))
    if ref is not None:
        rows_f = np.vstack([ref[None, :], rows_f])
        contrast = np.concatenate([[np.nan], contrast])
    nL = rows_f.shape[0] - 1
    th = np.diff(rows_f, axis=0) * upp
    if n_group is not None and nL > 0:
        ngs = list(n_group) if isinstance(n_group, (list, tuple)) else [n_group] * nL
        if len(ngs) != nL:
            raise ValueError("%s: n_group has %d entries for %d layers" % (op, len(ngs), nL))
        th = th / np.array([_pos(v, "n_group", op) for v in ngs])[:, None]
    return {"kind": "oct_boundaries", "rows": rows_f, "thickness_um": th,
            "mean_um": th.mean(axis=1) if nL > 0 else np.zeros(0),
            "std_um": th.std(axis=1) if nL > 0 else np.zeros(0),
            "contrast": contrast, "um_per_px": upp}


def oct_from_spectra(spectra, wavelength_nm, reference_spectrum=None, dark=None, center_nm=None, bandwidth_nm=None,
                     x_um=None):
    """装置が記録した生のスペクトルを、この族の op が読む表にする(``matrix`` → ``table``)。実機・公開データの入口。

    ``spectra``: (N,) の 1 本、または (W, N) の束(行 = A ライン)。``wavelength_nm``: (N,) の画素ごとの波長
    (分光器の較正。等間隔でなくてよい —— ``oct_k_linearize`` が k 等間隔に並べ直す)。``reference_spectrum``:
    参照腕だけで測ったスペクトル(無ければ ``oct_ascan`` で dc="mean" か "smooth" を使う)。``dark``:
    暗時の値(数か (N,))を全部から引く。``center_nm`` / ``bandwidth_nm``: 光源の公称値(軸分解能の基準と
    群屈折率の評価波長に使う。省略時はスペクトルの重心と RMS 幅から 2.355σ で推定)。
    返り値: 1 本なら kind="oct_interferogram"、束なら kind="oct_bscan_spectra"。空(A ライン 0 本)・値が有限でない・波長が
    単調でない・長さが合わないときは拒否。
    """
    op = "oct_from_spectra"
    s = np.asarray(spectra, float)
    wl = np.asarray(wavelength_nm, float).ravel()
    if s.size == 0:
        raise ValueError("%s: spectra is empty (no A-lines)" % op)
    if s.ndim not in (1, 2) or s.shape[-1] != wl.size or wl.size < 16:
        raise ValueError("%s: spectra must be (N,) or (W, N) with N == len(wavelength_nm) >= 16, got %s and %d"
                         % (op, s.shape, wl.size))
    if not (np.all(np.isfinite(s)) and np.all(np.isfinite(wl))) or np.any(wl <= 0):
        raise ValueError("%s: spectra and wavelengths must be finite (wavelengths > 0)" % op)
    d = np.diff(wl)
    if not (np.all(d > 0) or np.all(d < 0)):
        raise ValueError("%s: wavelength_nm must be strictly monotonic" % op)
    if dark is not None:
        dk = np.asarray(dark, float)
        if dk.ndim not in (0, 1) or (dk.ndim == 1 and dk.size != wl.size) or not np.all(np.isfinite(dk)):
            raise ValueError("%s: dark must be a number or (N,)" % op)
        s = s - dk
    ref = None
    if reference_spectrum is not None:
        ref = np.asarray(reference_spectrum, float).ravel()
        if ref.size != wl.size or not np.all(np.isfinite(ref)):
            raise ValueError("%s: reference_spectrum must be finite with N samples" % op)
        if dark is not None:
            ref = ref - np.asarray(dark, float)
    mean = s if s.ndim == 1 else s.mean(axis=0)
    w = np.clip(mean - np.percentile(mean, 5), 0, None)
    if center_nm is None or bandwidth_nm is None:
        if w.sum() <= 0:
            raise ValueError("%s: cannot estimate the source centre from a flat spectrum; pass center_nm" % op)
        c = float(np.sum(w * wl) / w.sum())
        sd = float(np.sqrt(np.sum(w * (wl - c) ** 2) / w.sum()))
    lam0 = c if center_nm is None else _pos(center_nm, "center_nm", op)
    dlam = 2 * math.sqrt(2 * LN2) * sd if bandwidth_nm is None else _pos(bandwidth_nm, "bandwidth_nm", op)
    out = {"k_rad_per_um": 2 * np.pi / (wl / 1000.0), "wavelength_nm": wl, "k_linear": False,
           "reference_spectrum": ref, "center_nm": lam0, "bandwidth_nm": dlam}
    if s.ndim == 1:
        out.update({"kind": "oct_interferogram", "spectrum": s, "mode": "sd"})
    else:
        out.update({"kind": "oct_bscan_spectra", "spectra": s, "mode": "sd",
                    "x_um": np.arange(s.shape[0], dtype=float) if x_um is None else np.asarray(x_um, float)})
    return out


def oct_bscan_flatten(bscan, reference_rows, above_um=20.0, below_um=300.0, noise_rows=0.15):
    """B スキャンを面(表面など)に沿って**平らに並べ直し、横に平均した深さの断面**を返す(``table`` → ``table``)。

    各列を ``reference_rows``(``oct_bscan_boundaries`` の行)が同じ行に来るようにずらし、パワー(|A|²)を横に
    平均して振幅に戻す(√平均)。粒状のスペックルに埋もれた界面のピークが立つ(Dong ら 2016 の層の平均の
    深さ断面と同じ考え方)。面の傾きに従わないもの —— 層の光学厚の深さに水平に出る**自己相関の幽霊** ——
    は平らにした座標で傾いてぼける(消えはしない)。

    返り値: ``oct_ascan`` と同じ形の表(kind="oct_ascan"、z_um = 窓の上端から、面は z = ``above_um``)なので
    ``oct_layer_thickness`` にそのまま渡せる。雑音の rms は元の画像の下から ``noise_rows`` の割合の行の
    平均パワー(平均しても床の高さは下がらない)。flat_image_db (Z', W) も返す。
    """
    op = "oct_bscan_flatten"
    b = _table(bscan, "oct_bscan", op)
    img = np.asarray(b["image_db"], float)
    H, W = img.shape
    ref = _per_column(reference_rows, W, "reference_rows", op)
    dz = float(b["dz_um"])
    a_px = int(round(_nonneg(above_um, "above_um", op) / dz))
    b_px = int(round(_pos(below_um, "below_um", op) / dz))
    fr = _finite(noise_rows, "noise_rows", op)
    if not 0.0 < fr < 0.5:
        raise ValueError("%s: noise_rows must be in (0, 0.5)" % op)
    P = 10.0 ** (img / 10.0)
    off = np.arange(-a_px, b_px + 1)
    base = np.round(ref).astype(int)
    rows = base[None, :] + off[:, None]
    valid = (rows >= 0) & (rows < H)
    flat = np.where(valid, P[np.clip(rows, 0, H - 1), np.arange(W)[None, :]], np.nan)
    cnt = np.sum(valid, axis=1)
    if np.any(cnt == 0):
        raise ValueError("%s: the window (above_um, below_um) leaves the image for every column at some depth" % op)
    prof = np.sqrt(np.nanmean(flat, axis=1))
    nfl = math.sqrt(float(np.mean(P[int(H * (1 - fr)):, :])))
    z = (off - off[0]) * dz
    pk = float(np.max(prof))
    return {"kind": "oct_ascan", "z_um": z, "amplitude": prof, "db": 20 * np.log10(np.maximum(prof, 1e-300)),
            "noise_sigma": nfl, "snr_db": float(20 * np.log10(max(pk, 1e-300) / max(nfl, 1e-300))),
            "z_max_um": float(b.get("z_max_um", z[-1])), "dz_um": dz, "zero_pad": 1, "two_sided": False,
            "window": None, "center_nm": b.get("center_nm"), "bandwidth_nm": b.get("bandwidth_nm"),
            "reference_um": a_px * dz, "flat_image_db": 10 * np.log10(np.where(np.isfinite(flat), flat, np.nan)),
            "n_columns": W}

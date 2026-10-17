# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gratingspec — 回折格子と分光器(Czerny–Turner)を、格子の式と幾何から組み立てる。

分光器は「光を色ごとに場所へ並べる」装置で、並べ方は**格子の式**ひとつで決まる。分解能・帯域の幅・
スリットの像の曲がり(smile)・空間方向の倍率の色ずれ(keystone)・高次の光の重なり(迷光の次数)は、
どれもその式と、スリット・鏡・検出器の大きさから閉形式で出る。この module は、

  * クロマティック共焦点(:mod:`chromconf`)の ``spectrometer_fwhm_nm`` と
  * ハイパースペクトル(:func:`spectralrad.hyperspectral_band_weights`)の ``band_fwhm_nm``

に**与えられていた数字**(分光器の線幅)が、スリットの幅・格子の本数・焦点距離・画素からどう決まるかを
実体化する。op は 5 本(``opsoptics`` の ``spectrometer`` カテゴリ):

  * :func:`grating_dispersion` —— 格子の式 mλ = d(sin α + sin β) を解き、角分散・逆線分散・
    アナモルフィック倍率・分解能 mN と上限 2W/λ・自由スペクトル範囲・同じ方向へ出る他の次数の波長を返す。
  * :func:`czerny_turner_design` —— 帯域と検出器の長さからカメラ鏡の焦点距離、Shafer の条件から
    コマを消すカメラ鏡の軸外し角、波長 → 検出器の位置の写像(非線形ぶんも)、2 次光の重なる帯域。
  * :func:`spectrometer_bandpass` —— 波長ごとのスリットの像の幅・逆線分散・帯域の幅(FWHM)。
    装置関数 = スリットの像(矩形)⊗ 画素(矩形)⊗ 回折(瞳の自己相関の逆変換)を数値で畳み込み、
    分解能 λ/FWHM と格子の分解能 mN、エタンデュ(スループット)を並べる。
  * :func:`spectrometer_slit_image` —— 長いスリットの像を 3 次元のベクトルの格子の式(溝に沿った方向余弦は
    保存、溝に垂直な成分に mλ/d が足される)で追い、smile(スペクトル線の曲がり)と keystone
    (空間方向の倍率の波長依存)を出す。閉形式の曲率半径 ρ = f_cam cos β / (sin α + sin β) と並べる。
  * :func:`spectrometer_spectrum` —— 入力スペクトル(pairs)→ 検出器の画素の読み(pairs)。
    1 次の像に高次(2 次・3 次)の像が重なる迷光の次数と、それを止めるロングパスのフィルタを入れる。

座標と符号(Palmer の約束): 角は格子の法線から測り、入射角 α と回折角 β が法線の同じ側なら同符号。
格子の式は mλ = d (sin α + sin β)。m = 0 は鏡面反射 β = −α。波長は nm、溝の密度は本/mm、検出器の
長さ・焦点距離は mm、スリットと画素は µm。

閉形式(PoC と tests の門):

  * 角分散 dβ/dλ = m / (d cos β) = (sin α + sin β) / (λ cos β)。Littrow(α = β)で 2 tan β / λ。
  * 逆線分散 P = d cos β / (m f_cam) [nm/mm]。
  * スリットの像の幅 w' = w (f_cam / f_col)(cos α / cos β)。スリットで決まる帯域の幅は
    w' P = w d cos α / (m f_col) で、**β に依らない**(帯域の全域で一定)。
  * 分解能 R = mN(N = 照らされた溝の数)、上限 2W/λ。一様に照らした矩形の瞳の回折の線幅(FWHM)は
    0.8859 λ / (mN)(sinc² の半値)、Rayleigh の分離は λ / (mN)。
  * Shafer の条件(1 次のコマを中心波長で消す): sin θ₂ / sin θ₁ = (R₂/R₁)² (cos θ₂ / cos θ₁)³ (cos α / cos β)³。
  * smile: スリットの高さ方向の角 γ の光は、溝に垂直な成分が cos γ 倍になる(円錐回折)ので、
    cos γ (sin α + sin β') = mλ/d。理想のカメラの像では Δx ≈ y'² (sin α + sin β) / (2 f_cam cos β) の放物線、
    曲率半径 ρ = f_cam cos β / (sin α + sin β)(Littrow で f / (2 tan β))。線は**長い波長の側へ**曲がる。
  * keystone(理想の直線写像のカメラ): y'(λ) ≈ f_cam tan γ / cos(β − β_c)。帯域の端で 1/cos(Δβ) − 1 だけ伸びる。

出典(教科書・公開論文のみ):

  * C. Palmer, *Diffraction Grating Handbook*, 8th ed., 2020(無償配布の版。式 (2-1)、(2-13)〜(2-17)、
    (2-19)〜(2-23)、(2-24)、(2-27)、(8-11a)、(8-12)、6.2.1 節の Czerny–Turner、7.2 節の line curvature)。
  * A. B. Shafer, L. R. Megill, L. Droppleman, "Optimization of the Czerny–Turner spectrometer",
    *J. Opt. Soc. Am.* 54(7):879-887, 1964 —— コマを消す条件(式の形は下の Feng ほか 2021 の式 (18) で確認)。
  * M. C. Hutley, *Diffraction Gratings*, Academic Press, 1982 —— 円錐回折と line curvature。
  * W. G. Fastie, "Image forming properties of the Ebert monochromator", *J. Opt. Soc. Am.* 42:647-651, 1952
    —— Littrow の線の曲率半径 f / (2 tan β)。
  * 公表の分光器の照合(CC BY 4.0、PoC の門):
    - Z. Feng ほか, "High-Performance Ultra-Thin Spectrometer Optical Design Based on Coddington's Equations",
      *Sensors* 21(2):323, 2021 —— 900 本/mm、i = 45°、f_col 40 mm、カメラ鏡 r = 136 mm、軸外し 14.5° → 14.968°、
      670〜1130 nm、検出器 28.67 mm・画素 14 µm、スリット 25 µm、分解能 0.4 nm(中心)〜0.75 nm(端)。
    - (同誌)"Three Criteria of M-Type Spectrometers for Engineering", *Sensors* 25(8):2439, 2025 ——
      1200 本/mm、i = 9°、r₁ = 104.1667 mm、r₂ = 148.3872 mm、500〜750 nm、スリット 25 µm、画素 14 µm、
      像の FWHM 0.040 / 0.043 / 0.050 mm と分解能 0.391 / 0.386 / 0.385 nm(表 7)。

パラメータと出典の対応(★確かめた範囲。「模型」はこの module の仮定):

    項目                       この module                         出典と照合の状態
    -------------------------  ----------------------------------  ------------------------------------------
    格子の式・分散・分解能     閉形式                              Palmer 2 章(確認)
    帯域の幅                   スリットの像 ⊗ 画素 ⊗ 回折の数値     Palmer (8-12) は sup(w', w'') × P の目安。
                               畳み込みの FWHM                     数値の FWHM は矩形 2 つで大きい方に一致(確認)
    回折の線の形               瞳の自己相関(円・矩形)            教科書の OTF(確認)。格子の溝の誤差は入れない
    Shafer の条件              二分法で θ₂                          Feng 2021 の 14.5° → 14.968° を再現(PoC の門)
    smile / keystone           理想の鏡(収差なし)+ 直線写像       閉形式と O(γ²) で一致(確認)。実機の歪曲・
                               のカメラのベクトル追跡              非点収差は入れていない(模型)
    高次の効率                 1 次との比を定数で与える            模型(実際は溝の形と偏光で波長ごとに違う、
                                                                   Palmer 9 章)

正直な開示:

  * 鏡は**無収差**として扱う(球面鏡の非点収差・球面収差・波長ごとのデフォーカスは入れていない)。
    公表の分光器の「端の分解能が中心より悪い」(Feng 2021 の 0.4 → 0.75 nm)は収差の効果で、この module の
    帯域の幅(スリットで決まる一定値)は**下限**として読む。
  * Feng 2021 は中心の分解能を 0.4 nm とするが、本文の f_col 40 mm・スリット 25 µm・900 本/mm・i = 45° から
    スリットだけで決まる像の幅を出すと 0.49 nm になる(像の FWHM は矩形の大きい方より細くならない)。
    同じ手順で M 型の 2025 年の論文は 0.395 nm 対 0.385〜0.391 nm と 3 % で合う。前者の差は解かずに残す。
  * 偏光と格子の効率(blaze)は入れない。高次の光の強さは呼び手が比で与える。

fail-closed: 文字列・bool・NaN・伝わらない次数(|sin β| > 1)・0 次・帯域の端が検出器に乗らない設計・
Shafer の条件の解が無い・粗すぎて装置関数を標本化できない入力スペクトル、はすべて名指しの ``ValueError``。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "grating_dispersion", "czerny_turner_design", "spectrometer_bandpass",
    "spectrometer_slit_image", "spectrometer_spectrum",
    "GRATINGSPEC", "SINC2_FWHM", "MAX_KERNEL_POINTS",
]

#: 公開 op の名前(レジストリの配線用)。
GRATINGSPEC = [
    "grating_dispersion", "czerny_turner_design", "spectrometer_bandpass",
    "spectrometer_slit_image", "spectrometer_spectrum",
]

#: sinc²(x) の半値全幅を、最初の零点までの距離で割った値(x = 0.442946 の 2 倍)。
#: 一様に照らした矩形の瞳の回折の線幅 = SINC2_FWHM × λ / (mN)。
SINC2_FWHM = 0.8858929413789047

#: 装置関数の数値格子の上限(大きな引数からの巨大な確保を止める)。
MAX_KERNEL_POINTS = 1 << 18
_MAX_WAVELENGTHS = 4096
_MAX_SPECTRUM = 1 << 20
_MAX_SLIT_POINTS = 4001


# --------------------------------------------------------------------------- #
# fail-closed helpers                                                          #
# --------------------------------------------------------------------------- #
def _num(v, name, op, positive=False, nonneg=False, lo=None, hi=None):
    if isinstance(v, (bool, np.bool_)) or isinstance(v, (str, bytes)) or v is None:
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v))
    if isinstance(v, (complex, np.complexfloating)):
        raise ValueError("%s: %s is complex — a real quantity was expected" % (op, name))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, type(v).__name__)) from None
    if not math.isfinite(f):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if positive and f <= 0.0:
        raise ValueError("%s: %s must be > 0, got %r" % (op, name, v))
    if nonneg and f < 0.0:
        raise ValueError("%s: %s must be >= 0, got %r" % (op, name, v))
    if lo is not None and f < lo:
        raise ValueError("%s: %s must be >= %g, got %r" % (op, name, lo, v))
    if hi is not None and f > hi:
        raise ValueError("%s: %s must be <= %g, got %r" % (op, name, hi, v))
    return f


def _count(v, name, op, lo, hi):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    v = int(v)
    if not lo <= v <= hi:
        raise ValueError("%s: %s must lie in [%d, %d], got %d" % (op, name, lo, hi, v))
    return v


def _order(v, op):
    m = _count(v, "order", op, -50, 50)
    if m == 0:
        raise ValueError("%s: order 0 is specular reflection (beta = -alpha) and has no dispersion; "
                         "use a non-zero order" % op)
    return m


def _sin_beta(m, lam_nm, d_nm, sin_a, op, what="wavelength"):
    s = m * lam_nm / d_nm - sin_a
    if np.any(np.abs(s) > 1.0):
        bad = np.atleast_1d(lam_nm)[np.abs(np.atleast_1d(s)) > 1.0]
        raise ValueError("%s: order %d does not propagate at %s %.6g nm (|sin beta| = %.6g > 1)"
                         % (op, m, what, float(bad[0]) if bad.size else float(np.atleast_1d(lam_nm)[0]),
                            float(np.max(np.abs(s)))))
    return s


def _wavelengths(v, name, op):
    a = np.atleast_1d(np.asarray(v, dtype=np.float64)) if not isinstance(v, (str, bytes)) else None
    if a is None or a.ndim != 1 or a.size < 1:
        raise ValueError("%s: %s must be a non-empty 1-D list of wavelengths [nm]" % (op, name))
    if a.size > _MAX_WAVELENGTHS:
        raise ValueError("%s: %d wavelengths exceed the limit %d" % (op, a.size, _MAX_WAVELENGTHS))
    if not np.all(np.isfinite(a)) or np.any(a <= 0.0):
        raise ValueError("%s: %s must be finite and > 0 nm" % (op, name))
    return a


# --------------------------------------------------------------------------- #
# 1. 格子の式                                                                   #
# --------------------------------------------------------------------------- #
def grating_dispersion(groove_density_per_mm=1200.0, wavelength_nm=550.0, incidence_deg=10.0, order=1,
                       focal_length_mm=100.0, illuminated_width_mm=25.0):
    """格子の式 mλ = d(sin α + sin β) を解き、角分散・逆線分散・分解能・重なる次数を表にする。

    groove_density_per_mm: 溝の密度 G [本/mm]。溝の間隔は d = 1/G。
    wavelength_nm: 波長 λ。incidence_deg: 入射角 α(法線から、Palmer の符号)。order: 次数 m(0 は拒否)。
    focal_length_mm: カメラ(結像側)の焦点距離 f(線分散に使う)。
    illuminated_width_mm: 照らされた格子の幅 W(分散方向)。溝の数 N = W/d。

    返り値(table):

    * ``beta_deg`` —— 回折角 β。``deviation_deg`` = α − β(入射光と回折光のなす角)。
    * ``angular_dispersion_deg_per_nm`` / ``angular_dispersion_rad_per_nm`` —— dβ/dλ = m / (d cos β)。
    * ``reciprocal_linear_dispersion_nm_per_mm`` —— P = d cos β / (|m| f)。
    * ``anamorphic_magnification`` —— cos α / cos β(回折光と入射光のビーム幅の比)。
    * ``grooves_illuminated`` / ``resolving_power`` (= |m| N) / ``resolving_power_max`` (= 2W/λ) /
      ``rayleigh_limit_nm`` (= λ / (|m| N)) / ``diffraction_fwhm_nm`` (= 0.8859 λ / (|m| N))。
    * ``free_spectral_range_nm`` —— λ / |m|。``littrow_deg`` —— この次数で α = β になる角(無ければ None)。
    * ``orders`` —— 伝わる全次数の (m, β [deg]) の表。
    * ``overlaps`` —— 同じ β へ出る他の次数の波長 (m', λ' = mλ/m')(迷光の次数。λ' は 50 nm 以上のみ)。

    **Raises** ``ValueError``: 0 次、伝わらない次数、非正の密度・波長・焦点距離・幅、|α| ≥ 90°。
    """
    op = "grating_dispersion"
    G = _num(groove_density_per_mm, "groove_density_per_mm", op, positive=True, hi=1.0e5)
    lam = _num(wavelength_nm, "wavelength_nm", op, positive=True, hi=1.0e6)
    a_deg = _num(incidence_deg, "incidence_deg", op, lo=-89.9, hi=89.9)
    m = _order(order, op)
    f = _num(focal_length_mm, "focal_length_mm", op, positive=True)
    W = _num(illuminated_width_mm, "illuminated_width_mm", op, positive=True)
    d = 1.0e6 / G                                                     # nm
    a = math.radians(a_deg)
    sa = math.sin(a)
    sb = float(_sin_beta(m, lam, d, sa, op))
    b = math.asin(sb)
    cb = math.cos(b)
    if cb < 1e-9:
        raise ValueError("%s: grazing diffraction (cos beta = %.3g): the dispersion diverges" % (op, cb))
    D = m / (d * cb)                                                  # rad/nm
    N = W * 1.0e6 / d
    R = abs(m) * N
    orders = []
    mmax = int(math.floor(2.0 * d / lam)) + 1
    for k in range(-mmax, mmax + 1):
        s = k * lam / d - sa
        if abs(s) <= 1.0:
            orders.append((k, math.degrees(math.asin(s))))
    overlaps = []
    for k in range(1, 4 * abs(m) + 4):
        kk = k if m > 0 else -k
        if kk == m:
            continue
        lp = m * lam / kk
        if lp >= 50.0:
            overlaps.append((kk, lp))
    sl = m * lam / (2.0 * d)
    return {
        "groove_density_per_mm": G, "groove_spacing_nm": d, "wavelength_nm": lam, "order": m,
        "incidence_deg": a_deg, "beta_deg": math.degrees(b), "deviation_deg": a_deg - math.degrees(b),
        "angular_dispersion_rad_per_nm": D, "angular_dispersion_deg_per_nm": math.degrees(D),
        "reciprocal_linear_dispersion_nm_per_mm": d * cb / (abs(m) * f),
        "anamorphic_magnification": math.cos(a) / cb,
        "grooves_illuminated": N, "resolving_power": R, "resolving_power_max": 2.0 * W * 1.0e6 / lam,
        "rayleigh_limit_nm": lam / R, "diffraction_fwhm_nm": SINC2_FWHM * lam / R,
        "free_spectral_range_nm": lam / abs(m),
        "littrow_deg": math.degrees(math.asin(sl)) if abs(sl) <= 1.0 else None,
        "orders": orders, "overlaps": overlaps,
        "focal_length_mm": f, "illuminated_width_mm": W,
    }


# --------------------------------------------------------------------------- #
# 2. Czerny–Turner の設計                                                       #
# --------------------------------------------------------------------------- #
def _shafer_theta2(theta1_rad, ratio, ca, cb, op):
    """sin θ₂ / sin θ₁ = ratio² (cos θ₂ / cos θ₁)³ (cos α / cos β)³ を θ₂ ∈ (0, 80°) で解く(単調なので二分法)。"""
    k = ratio ** 2 * (ca / cb) ** 3 / math.cos(theta1_rad) ** 3
    s1 = math.sin(theta1_rad)

    def g(t):
        return math.sin(t) / s1 - k * math.cos(t) ** 3

    lo, hi = 0.0, math.radians(80.0)
    if g(hi) <= 0.0:
        raise ValueError("%s: the Shafer coma condition has no solution below 80 degrees "
                         "(focal-length ratio %.4g, cos(alpha)/cos(beta) %.4g)" % (op, ratio, ca / cb))
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if g(mid) > 0.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def czerny_turner_design(groove_density_per_mm=1200.0, wavelength_min_nm=500.0, wavelength_max_nm=750.0,
                         incidence_deg=9.0, collimator_f_mm=52.083, detector_length_mm=28.672,
                         collimator_offaxis_deg=6.5, order=1, camera_f_mm=None, n_curve=41):
    """Czerny–Turner(平面格子 + 2 枚の凹面鏡)の 1 次設計: カメラの焦点距離・コマを消す角・波長の写像。

    groove_density_per_mm / order / incidence_deg: 格子と入射角 α(中心波長でも端でも同じ α)。
    wavelength_min_nm / wavelength_max_nm: 検出器に並べる帯域。中心 λ_c はその中点で、検出器の中央に来る。
    collimator_f_mm: コリメータ鏡の焦点距離(曲率半径の半分)。
    detector_length_mm: 検出器の長さ L(分散方向)。帯域の両端が検出器の両端に乗るようにカメラの f を決める。
    collimator_offaxis_deg: コリメータ鏡の軸外し角 θ₁(入射と反射のなす角の半分)。
    camera_f_mm: カメラ鏡の焦点距離を与える(None なら帯域が L にちょうど乗る値を厳密に解く)。
    n_curve: 波長 → 位置の写像の標本数。

    返り値(table、``kind = "czerny_turner"``。下流の op がそのまま受ける):

    * ``center_wavelength_nm`` / ``beta_center_deg`` / ``deviation_deg``(α − β_c)。
    * ``camera_f_mm``(使った値)/ ``camera_f_linear_mm``(線形近似 f = L d cos β_c / (m Δλ)、
      Feng 2021 の式 (16))/ ``camera_f_exact_mm``(像の写像 x = f tan(β − β_c) で両端が L に乗る値)。
    * ``mirror_radii_mm`` —— (2 f_col, 2 f_cam)。
    * ``shafer_offaxis_deg`` —— Shafer の条件でコマを消すカメラ鏡の軸外し角 θ₂。
    * ``dispersion_curve`` —— pairs(λ [nm], 検出器の位置 x [mm])。``nonlinearity_mm`` は直線からの最大のずれ。
    * ``reciprocal_dispersion_nm_per_mm`` —— (端, 中心, 端) の P。
    * ``detector_coverage_mm`` —— 帯域の両端の位置。``second_order_band_nm`` —— 帯域へ 2 次で重なる波長の範囲
      (λ_min/2 〜 λ_max/2)。``order_overlap_from_nm`` —— 帯域の中の光自身が 2 次で重なり始める波長
      (2 λ_min が帯域内なら。無ければ None)。

    **Raises** ``ValueError``: 帯域が逆・帯域の一部が伝わらない、検出器に乗らない、Shafer の解が無い、
    非正の長さ、|α| ≥ 90°。
    """
    op = "czerny_turner_design"
    G = _num(groove_density_per_mm, "groove_density_per_mm", op, positive=True, hi=1.0e5)
    l1 = _num(wavelength_min_nm, "wavelength_min_nm", op, positive=True, hi=1.0e6)
    l2 = _num(wavelength_max_nm, "wavelength_max_nm", op, positive=True, hi=1.0e6)
    if not l2 > l1:
        raise ValueError("%s: wavelength_max_nm (%g) must exceed wavelength_min_nm (%g)" % (op, l2, l1))
    a_deg = _num(incidence_deg, "incidence_deg", op, lo=-89.9, hi=89.9)
    fcol = _num(collimator_f_mm, "collimator_f_mm", op, positive=True)
    L = _num(detector_length_mm, "detector_length_mm", op, positive=True)
    th1_deg = _num(collimator_offaxis_deg, "collimator_offaxis_deg", op, lo=0.01, hi=60.0)
    m = _order(order, op)
    nc = _count(n_curve, "n_curve", op, 3, 4096)
    d = 1.0e6 / G
    a = math.radians(a_deg)
    sa, ca = math.sin(a), math.cos(a)
    lc = 0.5 * (l1 + l2)
    lam = np.linspace(l1, l2, nc)
    sb = _sin_beta(m, lam, d, sa, op)
    b = np.arcsin(sb)
    bc = math.asin(float(_sin_beta(m, lc, d, sa, op)))
    cbc = math.cos(bc)
    t1, t2 = math.tan(b[0] - bc), math.tan(b[-1] - bc)
    span = abs(t2 - t1)
    if span <= 0.0:
        raise ValueError("%s: the band does not disperse (zero span)" % op)
    f_exact = L / span
    f_lin = L * d * cbc / (abs(m) * (l2 - l1))
    if camera_f_mm is None:
        fcam = f_exact
    else:
        fcam = _num(camera_f_mm, "camera_f_mm", op, positive=True)
    x = fcam * np.tan(b - bc) * (1.0 if m > 0 else -1.0)
    if np.any(np.abs(np.cos(b - bc)) < 1e-6):
        raise ValueError("%s: a wavelength leaves the camera at 90 degrees" % op)
    lin = np.polyval(np.polyfit(lam, x, 1), lam)
    P = d * np.cos(b) / (abs(m) * fcam)
    th2 = _shafer_theta2(math.radians(th1_deg), fcam / fcol, ca, cbc, op)
    return {
        "kind": "czerny_turner",
        "groove_density_per_mm": G, "groove_spacing_nm": d, "order": m, "incidence_deg": a_deg,
        "wavelength_min_nm": l1, "wavelength_max_nm": l2, "center_wavelength_nm": lc,
        "beta_center_deg": math.degrees(bc), "beta_range_deg": (math.degrees(float(b[0])), math.degrees(float(b[-1]))),
        "deviation_deg": a_deg - math.degrees(bc),
        "collimator_f_mm": fcol, "camera_f_mm": fcam, "camera_f_linear_mm": f_lin, "camera_f_exact_mm": f_exact,
        "mirror_radii_mm": (2.0 * fcol, 2.0 * fcam),
        "collimator_offaxis_deg": th1_deg, "shafer_offaxis_deg": math.degrees(th2),
        "detector_length_mm": L, "detector_coverage_mm": (float(x[0]), float(x[-1])),
        "dispersion_curve": np.column_stack([lam, x]),
        "nonlinearity_mm": float(np.max(np.abs(x - lin))),
        "reciprocal_dispersion_nm_per_mm": (float(P[0]), float(d * cbc / (abs(m) * fcam)), float(P[-1])),
        "second_order_band_nm": (l1 / 2.0, l2 / 2.0),
        "order_overlap_from_nm": (2.0 * l1) if 2.0 * l1 < l2 else None,
    }


_DESIGN_KEYS = ("groove_spacing_nm", "order", "incidence_deg", "collimator_f_mm", "camera_f_mm",
                "wavelength_min_nm", "wavelength_max_nm", "center_wavelength_nm", "detector_length_mm")


def _check_design(design, op):
    if not isinstance(design, dict) or design.get("kind") != "czerny_turner":
        raise ValueError("%s: expected the table returned by czerny_turner_design(), got %r"
                         % (op, type(design).__name__))
    out = {}
    for k in _DESIGN_KEYS:
        if k not in design:
            raise ValueError("%s: the design table lacks %r" % (op, k))
        if k == "order":
            out[k] = _order(design[k], op)
        elif k == "incidence_deg":
            out[k] = _num(design[k], "design." + k, op, lo=-89.9, hi=89.9)
        else:
            out[k] = _num(design[k], "design." + k, op, positive=True)
    d, m = out["groove_spacing_nm"], out["order"]
    sa = math.sin(math.radians(out["incidence_deg"]))
    out["sa"], out["ca"] = sa, math.cos(math.radians(out["incidence_deg"]))
    out["bc"] = math.asin(float(_sin_beta(m, out["center_wavelength_nm"], d, sa, op, "the centre wavelength")))
    return out


def _beta(D, lam_nm, op, order=None):
    m = D["order"] if order is None else order
    return np.arcsin(_sin_beta(m, np.asarray(lam_nm, dtype=np.float64), D["groove_spacing_nm"], D["sa"], op))


# --------------------------------------------------------------------------- #
# 3. 帯域の幅(装置関数)                                                       #
# --------------------------------------------------------------------------- #
def _box(x, f, w):
    """格子 x 上の関数 f を幅 w の矩形で平均する(区分線形の累積積分の差、w ≤ 0 なら f のまま)。"""
    if w <= 0.0:
        return f
    h = x[1] - x[0]
    C = np.concatenate([[0.0], np.cumsum(0.5 * (f[1:] + f[:-1]) * h)])
    return (np.interp(x + 0.5 * w, x, C) - np.interp(x - 0.5 * w, x, C)) / w


def _diffraction_lsf(x_um, xz_um, pupil):
    """回折の線広がり関数(格子 x 上、面積 1)。xz_um = λ f / D'(矩形の瞳なら最初の零点)。"""
    if pupil == "rectangular":
        lsf = np.sinc(x_um / xz_um) ** 2
    else:
        # 円い瞳: OTF の断面 = 円の自己相関 (2/π)(acos s − s√(1 − s²))、s = ν / ν_c、ν_c = 1 / xz_um。
        n = x_um.size
        h = x_um[1] - x_um[0]
        nu = np.fft.fftfreq(n, h)
        s = np.clip(np.abs(nu) * xz_um, 0.0, 1.0)
        otf = (2.0 / math.pi) * (np.arccos(s) - s * np.sqrt(1.0 - s * s))
        lsf = np.real(np.fft.ifft(otf * np.exp(-2j * math.pi * nu * x_um[0])))
        lsf = np.maximum(lsf, 0.0)
    area = np.sum(lsf) * (x_um[1] - x_um[0])
    return lsf / area


def _fwhm(x, y):
    i = int(np.argmax(y))
    half = 0.5 * y[i]
    lo = i
    while lo > 0 and y[lo] > half:
        lo -= 1
    hi = i
    while hi < y.size - 1 and y[hi] > half:
        hi += 1
    if y[lo] > half or y[hi] > half:
        raise ValueError("spectrometer_bandpass: the line shape does not fall to half maximum inside the grid")
    xl = x[lo] + (half - y[lo]) * (x[lo + 1] - x[lo]) / (y[lo + 1] - y[lo])
    xr = x[hi - 1] + (half - y[hi - 1]) * (x[hi] - x[hi - 1]) / (y[hi] - y[hi - 1])
    return xr - xl


def _line_shape(w_img_um, pixel_um, xz_um, pupil, op):
    """装置関数(検出器の上、µm): 回折 ⊗ スリットの像 ⊗ 画素。返り値 (x, y, fwhm_um)。"""
    widths = [v for v in (w_img_um, pixel_um, xz_um) if v > 0.0]
    h = min(widths) / 24.0
    half = 0.5 * (w_img_um + pixel_um) + 30.0 * xz_um
    n = int(2.0 * half / h) | 1                                       # 奇数: 中心の標本が線の中心に乗る
    if n > MAX_KERNEL_POINTS:
        n = MAX_KERNEL_POINTS - 1
        h = 2.0 * half / (n - 1)
        if min(widths) / h < 6.0:
            raise ValueError("%s: the line shape needs more than %d samples (slit image %.4g um, pixel %.4g um, "
                             "diffraction %.4g um differ too much in scale)"
                             % (op, MAX_KERNEL_POINTS, w_img_um, pixel_um, xz_um))
    x = (np.arange(n) - (n - 1) / 2.0) * h
    y = _diffraction_lsf(x, xz_um, pupil)
    y = _box(x, y, w_img_um)
    y = _box(x, y, pixel_um)
    return x, y, _fwhm(x, y)


def _pupil(p, op):
    if p not in ("circular", "rectangular"):
        raise ValueError("%s: pupil must be 'circular' or 'rectangular', got %r" % (op, p))
    return p


def spectrometer_bandpass(design, slit_width_um=25.0, pixel_um=14.0, input_na=0.1, wavelengths_nm=None,
                          slit_height_mm=1.0, pupil="circular"):
    """分光器の帯域の幅(装置関数の FWHM)を、スリット・画素・回折から波長ごとに出す。

    design: :func:`czerny_turner_design` の表。
    slit_width_um: 入口スリットの幅 w。0 は理想の点(回折と画素だけが残る)。
    pixel_um: 検出器の画素の幅(分散方向)。0 は理想の連続の検出器。
    input_na: スリットに入る光の NA(コリメータで平行になったビームの直径 D = 2 f_col tan(asin NA) を決め、
      照らされた溝の数 N = D / (d cos α) と回折の線幅を決める)。
    wavelengths_nm: 評価する波長(None なら帯域の 5 点)。
    slit_height_mm: スリットの高さ(エタンデュだけに効く)。
    pupil: ``"circular"``(円いビーム、既定)/ ``"rectangular"``(一様に照らした矩形 = 教科書の mN)。

    返り値(table、波長ごとの配列):

    * ``slit_image_um`` —— w' = w (f_cam / f_col)(cos α / cos β)(Palmer (8-11a)、焦点面の上、収差なし)。
    * ``reciprocal_dispersion_nm_per_mm`` —— P = d cos β / (|m| f_cam)(焦点面の上)。
    * ``slit_image_flat_um`` / ``reciprocal_dispersion_flat_nm_per_mm`` / ``obliquity_factor`` —— カメラの軸に
      垂直な平らな検出器の上(局所の倍率 1 / cos²(β − β_c)、:func:`czerny_turner_design` の写像 x = f tan(β − β_c)
      と同じ)。装置関数と FWHM はこちらで作る。積 w' P(スリットで決まる帯域)はどちらでも同じ。
    * ``slit_limited_nm`` (= w d cos α / (|m| f_col)、β に依らない) / ``pixel_limited_nm`` (= p P) /
      ``palmer_bandpass_nm`` (= P sup(w', p)、Palmer (8-12)) / ``diffraction_fwhm_nm``(回折だけの FWHM)/
      ``rayleigh_limit_nm`` (= λ / (|m| N))。
    * ``fwhm_um`` / ``fwhm_nm`` —— 装置関数(回折 ⊗ スリットの像 ⊗ 画素)の FWHM。
    * ``resolving_power`` (= λ / FWHM) / ``grating_resolving_power`` (= |m| N) / ``pixels_per_fwhm``。
    * ``regime`` —— 最も幅の大きい寄与(``"slit"`` / ``"pixel"`` / ``"diffraction"``)。
    * ``line_shapes`` —— 波長ごとの装置関数 pairs(Δλ [nm], 最大 1 に正規化)。
    * ``etendue_mm2sr`` —— スリットの面積 × π NA²(スループットはこれに比例する。w と分解能の取引)。

    **Raises** ``ValueError``: 設計の表でない、帯域の外の波長、NA が (0, 0.95] の外、幅が負、瞳の名前の誤り。
    """
    op = "spectrometer_bandpass"
    D = _check_design(design, op)
    w = _num(slit_width_um, "slit_width_um", op, nonneg=True)
    p = _num(pixel_um, "pixel_um", op, nonneg=True)
    na = _num(input_na, "input_na", op, positive=True, hi=0.95)
    h_mm = _num(slit_height_mm, "slit_height_mm", op, positive=True)
    pupil = _pupil(pupil, op)
    l1, l2 = D["wavelength_min_nm"], D["wavelength_max_nm"]
    lam = np.linspace(l1, l2, 5) if wavelengths_nm is None else _wavelengths(wavelengths_nm, "wavelengths_nm", op)
    if np.any(lam < l1 - 1e-9) or np.any(lam > l2 + 1e-9):
        raise ValueError("%s: wavelengths must lie inside the design band %g-%g nm" % (op, l1, l2))
    d, m, fcol, fcam, ca = D["groove_spacing_nm"], D["order"], D["collimator_f_mm"], D["camera_f_mm"], D["ca"]
    b = _beta(D, lam, op)
    cb = np.cos(b)
    beam_mm = 2.0 * fcol * math.tan(math.asin(na))
    N = beam_mm * 1.0e6 / (d * ca)
    w_img = w * (fcam / fcol) * (ca / cb)                             # 焦点面の上(Palmer (8-11a))
    P = d * cb / (abs(m) * fcam)                                      # nm/mm(焦点面の上)
    xz = (lam * 1e-3) * (fcam * 1e3) / (beam_mm * 1e3 * cb / ca)      # µm: λ f / D'
    # 平らな検出器(カメラの軸に垂直): x = f tan(β − β_c) なので、局所の倍率は 1 / cos²(β − β_c)
    #(Palmer 2.3.2 の obliquity factor と、斜めの焦点距離 f / cos(β − β_c) の積)。
    obl = 1.0 / np.cos(b - D["bc"]) ** 2
    w_flat, P_flat, xz_flat = w_img * obl, P / obl, xz * obl
    out = {k: [] for k in ("fwhm_um", "fwhm_nm", "diffraction_fwhm_nm", "line_shapes", "regime")}
    for i in range(lam.size):
        x, y, fw = _line_shape(float(w_flat[i]), p, float(xz_flat[i]), pupil, op)
        xd, yd, fd = _line_shape(0.0, 0.0, float(xz_flat[i]), pupil, op)
        out["fwhm_um"].append(fw)
        out["fwhm_nm"].append(fw * 1e-3 * P_flat[i])
        out["diffraction_fwhm_nm"].append(fd * 1e-3 * P_flat[i])
        step = max(1, x.size // 801)
        out["line_shapes"].append(np.column_stack([x[::step] * 1e-3 * P_flat[i], y[::step] / y.max()]))
        contrib = (("slit", round(float(w_flat[i]), 9)), ("pixel", round(p, 9)), ("diffraction", round(fd, 9)))
        best = contrib[0]
        for c in contrib[1:]:                                         # 同点は宣言順(丸めた値で比べる)
            if c[1] > best[1]:
                best = c
        out["regime"].append(best[0])
    fwhm_nm = np.asarray(out["fwhm_nm"])
    return {
        "wavelengths_nm": lam, "beta_deg": np.degrees(b),
        "slit_image_um": w_img, "reciprocal_dispersion_nm_per_mm": P,
        "slit_image_flat_um": w_flat, "reciprocal_dispersion_flat_nm_per_mm": P_flat, "obliquity_factor": obl,
        "slit_limited_nm": np.full(lam.size, w * 1e-3 * d * ca / (abs(m) * fcol)),
        "pixel_limited_nm": p * 1e-3 * P_flat,
        "palmer_bandpass_nm": P_flat * np.maximum(w_flat, p) * 1e-3,
        "diffraction_fwhm_nm": np.asarray(out["diffraction_fwhm_nm"]),
        "rayleigh_limit_nm": lam / (abs(m) * N),
        "fwhm_um": np.asarray(out["fwhm_um"]), "fwhm_nm": fwhm_nm,
        "resolving_power": lam / fwhm_nm, "grating_resolving_power": abs(m) * N,
        "grooves_illuminated": N, "beam_diameter_mm": beam_mm,
        "pixels_per_fwhm": (np.asarray(out["fwhm_um"]) / p) if p > 0 else np.full(lam.size, np.inf),
        "regime": out["regime"], "line_shapes": out["line_shapes"],
        "etendue_mm2sr": (w * 1e-3) * h_mm * math.pi * na * na,
        "slit_width_um": w, "pixel_um": p, "input_na": na, "pupil": pupil,
    }


# --------------------------------------------------------------------------- #
# 4. smile と keystone                                                          #
# --------------------------------------------------------------------------- #
def _trace(D, lam_nm, xs_mm, ys_mm, rule="vector"):
    """スリットの点 (xs, ys) の光を、理想のコリメータ → 格子 → 理想のカメラへ追う。返り値 (x', y') [mm]。

    格子の座標: z = 法線、x = 溝に垂直、y = 溝の向き(= スリットの長さの向き)。入射の中心光線の進む向きは
    (−sin α, 0, −cos α)、回折光は (sin β, 0, cos β)(Palmer の符号で mλ = d(sin α + sin β))。
    ``rule="vector"`` は溝に垂直な方向余弦に mλ/d を足し、溝に沿った成分を保つ(正しい 3 次元の式)。
    ``rule="scalar"`` は面内の式 sin β = mλ/d − sin α を高さに関係なく使う**壊した模型**(探針用)。
    """
    d, m, fcol, fcam = D["groove_spacing_nm"], D["order"], D["collimator_f_mm"], D["camera_f_mm"]
    sa, ca, bc = D["sa"], D["ca"], D["bc"]
    lam = np.asarray(lam_nm, dtype=np.float64)
    xs = np.asarray(xs_mm, dtype=np.float64)
    ys = np.asarray(ys_mm, dtype=np.float64)
    # コリメータ: 軸 = 入射の中心の向き、スリットの点 (xs, ys) は向き −(xs e1 + ys ŷ)/f だけ傾く(像は倒立)
    e1x, e1z = ca, -sa                                                # 面内で軸に垂直(x 成分, z 成分)
    vx = fcol * (-sa) - xs * e1x
    vy = -ys + 0.0 * xs
    vz = fcol * (-ca) - xs * e1z
    nrm = np.sqrt(vx * vx + vy * vy + vz * vz)
    kx, ky = vx / nrm, vy / nrm
    if rule == "vector":
        ox = kx + m * lam / d
        oy = ky
    else:
        # 壊した模型: 面内に射影した入射角 α' で面内の式を解き、その β' の向きに高さの成分を足すだけ
        sin_ap = np.sin(np.arctan2(-kx, -vz / nrm))
        sinb = m * lam / d - sin_ap
        if np.any(np.abs(sinb) > 1.0):
            raise ValueError("spectrometer_slit_image: a slit point diffracts into an evanescent order")
        cg = np.sqrt(1.0 - ky * ky)
        ox = cg * sinb
        oy = ky
    rad = 1.0 - ox * ox - oy * oy
    if np.any(rad <= 0.0):
        raise ValueError("spectrometer_slit_image: a slit point diffracts into an evanescent order")
    oz = np.sqrt(rad)
    # カメラ: 軸 w = (sin β_c, 0, cos β_c)、u = (cos β_c, 0, −sin β_c)、v = ŷ。直線写像 x' = f (o·u)/(o·w)
    ow = ox * math.sin(bc) + oz * math.cos(bc)
    ou = ox * math.cos(bc) - oz * math.sin(bc)
    sgn = 1.0 if m > 0 else -1.0
    return sgn * fcam * ou / ow, fcam * oy / ow


def spectrometer_slit_image(design, slit_height_mm=2.0, wavelengths_nm=None, n_points=21, rule="vector"):
    """長いスリットの像を 3 次元で追い、smile(線の曲がり)と keystone(空間倍率の色ずれ)を出す。

    design: :func:`czerny_turner_design` の表。slit_height_mm: スリットの長さ(溝の向き)。
    wavelengths_nm: 評価する波長(None なら帯域の 5 点)。n_points: スリットに沿った標本数(奇数にすると中心を含む)。
    rule: ``"vector"``(3 次元の格子の式、既定)/ ``"scalar"``(面内の式を流用する**壊した模型**。
      門の探針で、smile の閉形式から外れることを確かめるために残してある)。

    返り値(table):

    * ``x_mm`` / ``y_mm`` —— (波長, スリットの点) の像の位置(検出器の中心 = λ_c の中心光線)。
    * ``smile_um`` —— スリットの端の像の x − 中心の像の x(波長ごと、正 = 長い波長の側)。
    * ``smile_closed_um`` —— y'² (sin α + sin β) / (2 f_cam cos β)(放物線の近似)。
    * ``curvature_radius_mm`` —— ρ = f_cam cos β / (sin α + sin β)。
    * ``keystone_um`` —— スリットの端の像の y − 中心波長での y(波長ごと)。
      ``keystone_closed_um`` = y'(λ_c) (1 / cos(β − β_c) − 1)。
    * ``anamorphic_trace`` / ``anamorphic_closed`` —— スリットの幅方向の倍率 dx'/dx_s を追跡と閉形式
      (f_cam / f_col)(cos α / cos β) / cos²(β − β_c)(平らな検出器)で。

    **Raises** ``ValueError``: 設計の表でない、帯域の外、高さ ≤ 0、rule の名前の誤り、伝わらない光。
    """
    op = "spectrometer_slit_image"
    D = _check_design(design, op)
    h = _num(slit_height_mm, "slit_height_mm", op, positive=True)
    n = _count(n_points, "n_points", op, 3, _MAX_SLIT_POINTS)
    if rule not in ("vector", "scalar"):
        raise ValueError("%s: rule must be 'vector' or 'scalar', got %r" % (op, rule))
    l1, l2 = D["wavelength_min_nm"], D["wavelength_max_nm"]
    lam = np.linspace(l1, l2, 5) if wavelengths_nm is None else _wavelengths(wavelengths_nm, "wavelengths_nm", op)
    if np.any(lam < l1 - 1e-9) or np.any(lam > l2 + 1e-9):
        raise ValueError("%s: wavelengths must lie inside the design band %g-%g nm" % (op, l1, l2))
    ys = np.linspace(-0.5 * h, 0.5 * h, n)
    L, Y = np.meshgrid(lam, ys, indexing="ij")
    X, Yp = _trace(D, L, np.zeros_like(L), Y, rule)
    x0, _ = _trace(D, lam, np.zeros_like(lam), np.zeros_like(lam), rule)
    xe, ye = _trace(D, lam, np.zeros_like(lam), np.full(lam.size, 0.5 * h), rule)
    _, yc = _trace(D, np.array([D["center_wavelength_nm"]]), np.zeros(1), np.array([0.5 * h]), rule)
    b = _beta(D, lam, op)
    s_ab = D["sa"] + np.sin(b)
    fcam, fcol = D["camera_f_mm"], D["collimator_f_mm"]
    rho = fcam * np.cos(b) / s_ab
    yimg = np.abs(ye)
    eps = 1e-6
    xp, _ = _trace(D, lam, np.full(lam.size, eps), np.zeros(lam.size), rule)
    xm, _ = _trace(D, lam, np.full(lam.size, -eps), np.zeros(lam.size), rule)
    sgn = 1.0 if D["order"] > 0 else -1.0
    return {
        "wavelengths_nm": lam, "slit_points_mm": ys, "x_mm": X, "y_mm": Yp,
        "smile_um": (xe - x0) * 1e3 * sgn,
        "smile_closed_um": yimg ** 2 / (2.0 * rho) * 1e3,
        "curvature_radius_mm": rho,
        "keystone_um": (np.abs(ye) - abs(float(yc[0]))) * 1e3,
        "keystone_closed_um": abs(float(yc[0])) * (1.0 / np.cos(b - D["bc"]) - 1.0) * 1e3,
        "anamorphic_trace": np.abs(xp - xm) / (2.0 * eps),
        "anamorphic_closed": (fcam / fcol) * D["ca"] / np.cos(b) / np.cos(b - D["bc"]) ** 2,
        "slit_height_mm": h, "rule": rule,
    }


# --------------------------------------------------------------------------- #
# 5. 検出器の読み(高次の重なりつき)                                           #
# --------------------------------------------------------------------------- #
def spectrometer_spectrum(design, spectrum, slit_width_um=25.0, pixel_um=14.0, input_na=0.1,
                          max_order_multiple=3, higher_order_efficiency=0.3, longpass_nm=None,
                          oversample=8, pupil="circular"):
    """入力スペクトル → 検出器の画素の読み(1 次の像に高次の像が重なる)。

    design: :func:`czerny_turner_design` の表。spectrum: pairs(λ [nm] 昇順, 分光放射輝度 ≥ 0、nm あたり)。
    slit_width_um / pixel_um / input_na / pupil: :func:`spectrometer_bandpass` と同じ(装置関数を決める)。
    max_order_multiple: 設計の次数 m の何倍までの次数を足すか(1 = 高次なし、3 なら m, 2m, 3m)。
    higher_order_efficiency: 高次の回折効率の 1 次に対する比(次数によらず一定の模型)。
    longpass_nm: 入口のロングパスのフィルタの端(これより短い光を 0 にする。None = フィルタなし)。
    oversample: 画素を何分割して像を置くか(畳み込みの精度)。

    返り値: pairs(画素の中心の波長 [nm]、1 次の校正で、読み(nm あたりの放射輝度 × 帯域の幅の単位))。
    装置関数は中心波長のもの(スリットの像と回折の幅の波長による変化は入れない —— 帯域ごとの幅は
    :func:`spectrometer_bandpass` が出す)。

    **Raises** ``ValueError``: 入力が粗すぎて装置関数の FWHM の 1/3 より細かく標本化されていない、
    昇順でない・負・非有限のスペクトル、設計の表でない、引数の範囲外。
    """
    op = "spectrometer_spectrum"
    D = _check_design(design, op)
    w = _num(slit_width_um, "slit_width_um", op, nonneg=True)
    p = _num(pixel_um, "pixel_um", op, positive=True)
    na = _num(input_na, "input_na", op, positive=True, hi=0.95)
    kmax = _count(max_order_multiple, "max_order_multiple", op, 1, 10)
    eff = _num(higher_order_efficiency, "higher_order_efficiency", op, nonneg=True, hi=10.0)
    lp = 0.0 if longpass_nm is None else _num(longpass_nm, "longpass_nm", op, positive=True)
    ov = _count(oversample, "oversample", op, 1, 64)
    pupil = _pupil(pupil, op)
    S = np.asarray(spectrum, dtype=np.float64) if not isinstance(spectrum, (str, bytes)) else None
    if S is None or S.ndim != 2 or S.shape[1] != 2 or S.shape[0] < 3:
        raise ValueError("%s: spectrum must be pairs (wavelength nm, radiance) of shape (n, 2), n >= 3" % op)
    if S.shape[0] > _MAX_SPECTRUM:
        raise ValueError("%s: %d spectrum samples exceed the limit %d" % (op, S.shape[0], _MAX_SPECTRUM))
    if not np.all(np.isfinite(S)) or np.any(np.diff(S[:, 0]) <= 0.0) or S[0, 0] <= 0.0:
        raise ValueError("%s: spectrum wavelengths must be finite, positive and strictly increasing" % op)
    if np.any(S[:, 1] < 0.0):
        raise ValueError("%s: spectrum has negative radiance" % op)
    d, m, fcam, fcol, ca, bc = (D["groove_spacing_nm"], D["order"], D["camera_f_mm"], D["collimator_f_mm"],
                                D["ca"], D["bc"])
    L = D["detector_length_mm"]
    npx = int(math.floor(L * 1e3 / p + 1e-9))
    if npx < 3:
        raise ValueError("%s: the detector holds fewer than 3 pixels (%g mm / %g um)" % (op, L, p))
    # 装置関数(中心波長): スリットの像 ⊗ 回折。画素の積分は細かい格子の和で入る。
    beam_mm = 2.0 * fcol * math.tan(math.asin(na))
    lc = D["center_wavelength_nm"]
    w_img = w * (fcam / fcol) * ca / math.cos(bc)
    xz = lc * 1e-3 * fcam * 1e3 / (beam_mm * 1e3 * math.cos(bc) / ca)
    _, _, fw_um = _line_shape(w_img, p, xz, pupil, op)
    Pc = d * math.cos(bc) / (abs(m) * fcam)
    fw_nm = fw_um * 1e-3 * Pc
    # 入力の標本化: 1 次の帯域の内側で、FWHM の 1/3 より細かいこと(粗い入力は線を太らせ、黙って間違う)
    inband = (S[:, 0] >= D["wavelength_min_nm"]) & (S[:, 0] <= D["wavelength_max_nm"])
    if np.count_nonzero(inband) >= 2:
        step = float(np.max(np.diff(S[inband, 0])))
        if step > fw_nm / 3.0:
            raise ValueError("%s: the input spectrum is sampled every %.4g nm, coarser than 1/3 of the instrument "
                             "FWHM %.4g nm — resample it finer (a coarse input would broaden the lines silently)"
                             % (op, step, fw_nm))
    h = p / ov
    nfine = npx * ov
    xf = (np.arange(nfine) + 0.5) * h * 1e-3 - 0.5 * npx * p * 1e-3    # mm、検出器の中心 = 0
    fine = np.zeros(nfine)
    lam = S[:, 0]
    wts = S[:, 1] * np.gradient(lam)
    if lp > 0.0:
        wts = np.where(lam >= lp, wts, 0.0)
    sgn = 1.0 if m > 0 else -1.0
    for k in range(1, kmax + 1):
        mk = m * k
        s = mk * lam / d - D["sa"]
        ok = np.abs(s) < 1.0
        if not np.any(ok):
            continue
        bk = np.arcsin(s[ok])
        if np.any(np.cos(bk - bc) <= 1e-6):
            ok_idx = np.cos(bk - bc) > 1e-6
            bk = bk[ok_idx]
            wk = wts[ok][ok_idx]
        else:
            wk = wts[ok]
        xk = sgn * fcam * np.tan(bk - bc)
        e = 1.0 if k == 1 else eff
        pos = (xk - xf[0]) / (h * 1e-3)
        i0 = np.floor(pos).astype(np.int64)
        fr = pos - i0
        for ii, ww in ((i0, 1.0 - fr), (i0 + 1, fr)):
            sel = (ii >= 0) & (ii < nfine)
            np.add.at(fine, ii[sel], e * wk[sel] * ww[sel])
    # 畳み込み(スリットの像 ⊗ 回折)
    half = 0.5 * w_img + 30.0 * xz
    nk = int(2.0 * half / h) + 1
    nk = min(nk | 1, 2 * nfine + 1)
    xk_um = (np.arange(nk) - (nk - 1) / 2.0) * h
    ker = _box(xk_um, _diffraction_lsf(xk_um, xz, pupil), w_img)
    ker = ker / np.sum(ker)
    nfft = 1 << int(math.ceil(math.log2(nfine + nk)))
    conv = np.fft.irfft(np.fft.rfft(fine, nfft) * np.fft.rfft(ker, nfft), nfft)
    c0 = (nk - 1) // 2
    blurred = conv[c0:c0 + nfine]
    counts = blurred.reshape(npx, ov).sum(axis=1)
    xc = ((np.arange(npx) + 0.5) * p * 1e-3 - 0.5 * npx * p * 1e-3)
    lam_px = d * (D["sa"] + np.sin(bc + np.arctan(sgn * xc / fcam))) / m
    # 読みを「nm あたり」へ: 画素の波長幅で割らず、帯域の幅の単位のまま返す(連続光は ~ S × 画素の Δλ)
    return np.column_stack([lam_px, np.maximum(counts, 0.0)])

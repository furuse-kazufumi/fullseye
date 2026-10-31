# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""chromconf — クロマティック共焦点(白色共焦点)変位センサを、レンズの処方と材料表から組み立てる。

白色光を**軸上色収差の大きい対物レンズ**で集光すると、波長ごとに焦点の高さが変わる。面で反射して
ピンホールを通って分光器へ戻るのは、**面にピントの合った波長だけ**なので、戻りスペクトルのピーク波長が
そのまま高さになる(Molesini 1984 の「焦点を波長で符号化した形状計」)。透明体の表裏・フィルム厚・
鏡面・段差を、走査せず 1 本のスペクトルで非接触に測れるのはこのため。

既存の :func:`interferometry.chromatic_confocal_simulate` / :func:`interferometry.chromatic_confocal_height`
は「高さ = (λ − λ_ref) × 分散係数」の**線形の較正定数**を与えられた側の op で、その定数がどこから来るかは
扱わない。この module はその手前、**レンズの処方(raytrace)と硝材の分散(materials)から**
波長 → 焦点位置の較正表を作り、戻りスペクトルを物理の式から合成し、ピークを拾って高さと厚さに戻す。
光学系(対物レンズの硝材)と観察対象(透明板・金・アルミ)が **同じ材料表** を引く。

op は 6 本(``opsoptics`` の ``confocal`` カテゴリ):

  * :func:`chromatic_confocal_probe` —— 処方 → 波長ごとの焦点位置(近軸と、鏡で較正したピーク位置)、
    像側 NA、縦球面収差、軸方向の応答幅。いわば **虹のものさし** の目盛。
  * :func:`confocal_axial_response` —— 共焦点の軸方向応答 I(z)。鏡面は sinc²(u/2)、点物体は
    sinc⁴(u/4)(u = 8π n z sin²(α/2)/λ、Corle–Chou–Kino 1986、Wilson & Sheppard 1984)。
    縦球面収差を入れると瞳の数値積分に切り替わる(収差 0 では閉形式と一致、門で固定)。
  * :func:`chromatic_confocal_spectrum` —— 面の位置と層構成(透明板・膜・金属)→ 戻りスペクトル
    = 光源 × 面の反射率(材料表の n, k から Fresnel)× 共焦点の軸応答 × 分光器の応答 × 雑音。
    傾き(戻る光の円の重なり)と粗さ(TIS = exp(−(4πσ/λ)²))も入る。
  * :func:`chromatic_confocal_peaks` —— スペクトル → ピーク波長(重心・放物線・ガウス・最大ビン)。
    光源のむらは白色参照で割って補正する。
  * :func:`chromatic_confocal_readout` —— ピーク波長 → 高さ(較正表の逆引き)、2 ピークなら
    透明板の厚さ(見かけの厚さ × n(λ)、NA の補正つき)。
  * :func:`chromatic_confocal_limits` —— 測定範囲・軸方向分解能・戻る傾きの上限・2 ピークが分かれる
    最小の厚さ(Sparrow の基準)を閉形式で。

座標の約束: 光軸 +z はプローブから遠ざかる向き。較正表の z [µm] は **最短波長の較正ピーク位置を 0** と
する(遠い面ほど z が大きい。高さに直すなら符号を反転する)。波長は nm、長さは µm(処方だけ raytrace の
約束どおり mm)。

閉形式(PoC と tests の門):

  * 測定範囲 —— 薄肉単レンズなら f(λ) = f_d (n_d − 1)/(n(λ) − 1)、範囲 ≈ f(λ_max) − f(λ_min)。
    厚肉は raytrace の近軸追跡(厚肉レンズの式と 1e-14 mm で一致することは raytrace の門)。
  * 軸方向の応答幅 —— 鏡面の FWHM = 0.4430 λ / (n (1 − cos α))(sinc² が 1/2 になる x = 1.39156 から)。
    近軸では ≈ 0.886 λ/NA²: **分解能は λ/NA² に比例**。
  * 薄い膜の限界 —— 等しい 2 つの sinc² が Sparrow の基準で分かれる最小の間隔(FWHM の
    :data:`SPARROW_FRACTION` 倍)× n。それより薄い膜は 1 ピークに潰れ、readout は拒否する。
  * 傾き —— 鏡面で反射した光の円錐は 2θ 傾き、瞳との重なり(半径 NA の円 2 つ、中心距離 sin 2θ)
    だけが戻る。sin 2θ ≥ 2 NA(θ ≈ NA)で 0。

出典(教科書と公開論文のみ。市販のセンサの資料は使っていない):

  * G. Molesini, G. Pedrini, P. Poggi, F. Quercioli, "Focus-wavelength encoded optical profilometer",
    *Optics Communications* 49(4):229-233, 1984 —— 原理(焦点の波長符号化)。
  * H. J. Tiziani & H.-M. Uhde, "Three-dimensional image sensing by chromatic confocal microscopy",
    *Applied Optics* 33(10):1838-1843, 1994 —— 波長 → 高さの写像と色収差の対物レンズの設計。
  * T. R. Corle, C.-H. Chou, G. S. Kino, "Depth response of confocal optical microscopes",
    *Optics Letters* 11(12):770-772, 1986 —— 鏡面の軸方向応答と FWHM ∝ λ/(1 − cos α)。
  * T. Wilson & C. J. R. Sheppard, *Theory and Practice of Scanning Optical Microscopy*,
    Academic Press, 1984 —— 点物体と平面物体の軸応答(sinc⁴(u/4) と sinc²(u/2))。
  * Z. Li et al., "A diffractive element-based chromatic confocal thickness measurement device and
    thickness correction method", *iScience* 2025, 113322 —— 透明体の厚さと傾きの補正(応用)。
  * M. Hillenbrand et al., "Hybrid hyperchromats for chromatic confocal sensor systems",
    *Advanced Optical Technologies* 1:187-194, 2012 (DOI 10.1515/aot-2012-0017) —— 範囲 = 薄肉の色収差の和、
    傾きの上限、球面収差がピークを広げ弱めること、硝材の Abbe 数の幅。
  * J.-C. Chen et al., "Influence of sample surface height for evaluation of peak extraction algorithms in
    confocal microscopy", *Applied Optics* 57(22):6516-6526, 2018 と "Corrected parabolic fitting for height
    extraction in confocal microscopy", *Optics Express* 27(3):3682-3697, 2019 —— 推定法の系統誤差。
  * Y.-M. Choi, H. Yoo, D. Kang, "Large-area thickness measurement of transparent multi-layer films based on
    laser confocal reflection sensor", *Measurement* 153:107390, 2020 —— 厚さには n と NA の両方が要る。

パラメータと出典の対応(★確かめた範囲を分けて書く。「模型」は一次文献で値を確かめていない、この module の
仮定か導出):

    項目                     この module / PoC の値            出典と照合の状態
    -----------------------  --------------------------------  ---------------------------------------------
    原理(波長で焦点を符号化) スペクトルのピーク = 面の位置     Molesini 1984、Tiziani & Uhde 1994(確認)
    範囲の式                 近軸の追跡(厚肉)、f/V の近似    Hillenbrand 2012 式 (2) の薄肉の和(確認)。
                                                               PoC で厚肉の閉形式と 4e-12 µm、f/V と 2 %
    範囲の典型               1.19 mm(単レンズ)/1.84 mm    「数 µm〜数 mm」Hillenbrand 2012 §1、18 mm の例
                             (ハイパークロマート)            Sharma & Singh, arXiv:2201.12373(確認、範囲内)
    硝材の Abbe 数           重フリント 20.9 / フッ素クラウン   推奨硝材は約 21〜85(Hillenbrand 2012)。
                             90.9                              フッ素クラウンはその外(材料表の値)
    NA                       0.15〜0.16                        0.15〜0.35 の記載(US 8,212,997、光学ペンの
                                                               特許)。下端に当たる(確認)
    軸応答の幅               0.443 λ/(n(1 − cos α))            半値で kz(1 − cos α) = 1.39(Corle–Chou–Kino
                                                               1986)。閉形式と 1e-12(確認)
    球面収差の効果           ピークが低く広くなる              Hillenbrand 2012 §3 と定性で一致(確認)。
                             3 次 1 項・ピークが LSA/2 ずれる  模型(瞳の数値積分による。実測の照合なし)
    推定法の偏り             ガウス 0.06・放物線 0.11・        非線形当てはめは系統誤差を持ち、面の高さ
                             重心 0.29 µm(雑音なし)          (標本化の位置)で変わる: Chen 2018 / 2019
                                                               (確認、定性)。数値は模型の値
    雑音での順位             重心(半値より上)が最も安定      文献はガウスを最も安定とする例が多い(重心の
                                                               定義が違う)。★一致しない点として残す
    傾きの上限               sin 2θ = 2NA(瞳の重なり)        半頂角 = 傾きで 0(Hillenbrand 2012 §3)。
                                                               NA 0.155 で 9.03° 対 asin 8.92°(1 % の差)
    透明板の厚さ             n(λ₂)·見かけ /(1 − g/2)         n と NA の両方が要る(Choi 2020、確認)。
                                                               g/2 の補正式は模型(平板の閉形式から導出)
    試料の分光反射率         金で 0.15 µm 遠く読む            較正の鏡と反射率が違うと誤差(US 8,587,789、
                                                               定性で確認)。数値は材料表の J&C による模型
    光源のむら               0.93 → 0.014 µm(白色参照)      ±0.4 µm → 0.2 µm 未満(Csőke, Kautny, Kollár、
                                                               SLD と参照光の分光器、プレプリント)。
                                                               オーダーは同じ、LED の分光分布は模型
    粗さ                     TIS = exp(−(4πσ/λ)²)              散乱の定番の式(Bennett & Porteus 1961)。
                                                               ピークの偏りの大きさは模型
    薄膜の限界               Sparrow × FWHM × n                模型(干渉を入れていない)

正直な開示(測った、または式から言えること):

  * 層のあいだの**干渉は入れていない**(反射を強度で足す)。厚い板では分光器の分解能で縞が平均されるが、
    数 µm の薄膜では戻りスペクトルに干渉縞(チャネルドスペクトル)が乗る —— 実物ではそれ自体が分光干渉の
    厚さ計測になる。ここでの「薄すぎる膜は 2 ピークに分かれない」は強度の重なりだけの限界。
  * 縦球面収差は**3 次(ρ⁴)の 1 項**で入れる。処方の実光線から測った値(縁の光線の焦点 − 近軸焦点)を
    3 次に当てはめるので、高次の球面収差は落ちる。透明板が足す球面収差は平行平板の閉形式
    (:func:`materials.plate_focus_shift` と同じ式)を空気換算して足す。
  * 傾いた面は「戻る光の量」だけを下げ、応答の形(傾いた面では非対称になる)は変えない。
  * 粗さは鏡面成分を TIS で減らし、散乱成分を Lambert で NA² だけ拾う(散乱光の応答は点物体の式)。
    スペックルは入れていない。
  * 較正は「鏡を既知の位置に置いてピークを読む」手順を、処方から数値で再現したもの。実機ではこれが
    唯一の較正で、レンズの設計値は使わない。

fail-closed: 文字列・bool・NaN・範囲外の波長・NA ≥ n・単調でない較正表・縁で欠けたピーク・
飽和(平らな頂上)・2 層を指定したのに 1 ピークしか無いスペクトル、はすべて名指しの ``ValueError``。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "chromatic_confocal_probe", "confocal_axial_response", "chromatic_confocal_spectrum",
    "chromatic_confocal_peaks", "chromatic_confocal_readout", "chromatic_confocal_limits",
    "CHROMCONF", "FWHM_X_MIRROR", "SPARROW_FRACTION", "DEFAULT_PROBE_SURFACES",
    "GLASS_DENSE_FLINT", "GLASS_FLUOR_CROWN", "GLASS_CROWN",
]

#: 公開 op の名前(レジストリの配線用)。
CHROMCONF = [
    "chromatic_confocal_probe", "confocal_axial_response", "chromatic_confocal_spectrum",
    "chromatic_confocal_peaks", "chromatic_confocal_readout", "chromatic_confocal_limits",
]

#: sinc²(x) = 1/2 の根 x(鏡面の軸応答の半値)。FWHM_z = x λ / (π n (1 − cos α))。
FWHM_X_MIRROR = 1.3915573782515103

#: 等しい高さの 2 つの鏡面応答 sinc²(u/2) が「谷を持ち始める」間隔(Sparrow の基準)を FWHM で割った値。
#: 中点の 2 階微分が 0 になる間隔を 1 回だけ数値で解いた定数(:func:`_sparrow_fraction` が再計算できる)。
SPARROW_FRACTION = None  # 下の _sparrow_fraction() で import 時に埋める

#: 既定の対物レンズ: 高分散の重フリント(n_d ≈ 1.923、V_d ≈ 20.9、材料表で最も分散の大きい硝子の 1 つ)の平凸単レンズ。
#: 平面を光源側、出射面を双曲面(k = −n²、Descartes の無収差レンズ)にして 575 nm で球面収差を消す。
#: f ≈ 16 mm、ビーム半径 2.5 mm(NA ≈ 0.16)。半径は 575 nm の n から決めた値を丸めずに書いてある。
DEFAULT_PROBE_SURFACES = None  # 下の _default_surfaces() で埋める(materials の n を引くため)

_MAX_POINTS = 1 << 16


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


def _curve(c, name, op, lo_nm=None, hi_nm=None):
    """pairs(λ nm 昇順, 値 ≥ 0)の検査。範囲を覆わなければ ValueError(外挿しない)。"""
    a = np.asarray(c, dtype=np.float64) if not isinstance(c, (str, bytes)) else None
    if a is None or a.ndim != 2 or a.shape[1] != 2 or a.shape[0] < 2:
        raise ValueError("%s: %s must be pairs (wavelength nm, value) of shape (n, 2), n >= 2" % (op, name))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: %s has non-finite values" % (op, name))
    if np.any(np.diff(a[:, 0]) <= 0.0):
        raise ValueError("%s: %s wavelengths must be strictly increasing" % (op, name))
    if np.any(a[:, 1] < 0.0):
        raise ValueError("%s: %s has negative values (a spectrum / response cannot be negative)" % (op, name))
    if lo_nm is not None and (a[0, 0] > lo_nm + 1e-9 or a[-1, 0] < hi_nm - 1e-9):
        raise ValueError("%s: %s covers %.6g-%.6g nm but %.6g-%.6g nm is needed (not extrapolated)"
                         % (op, name, a[0, 0], a[-1, 0], lo_nm, hi_nm))
    return a


def _check_probe(probe, op):
    keys = ("wavelength_nm", "paraxial_um", "calibration_um", "lsa_um", "na")
    if not isinstance(probe, dict) or any(k not in probe for k in keys):
        raise ValueError("%s: probe must be the dict returned by chromatic_confocal_probe() (keys %s)"
                         % (op, ", ".join(keys)))
    wl = np.asarray(probe["wavelength_nm"], dtype=np.float64)
    if wl.ndim != 1 or wl.size < 4 or not np.all(np.isfinite(wl)) or np.any(np.diff(wl) <= 0.0):
        raise ValueError("%s: probe wavelength_nm must hold >= 4 increasing finite values" % op)
    for k in keys[1:]:
        v = np.asarray(probe[k], dtype=np.float64)
        if v.shape != wl.shape or not np.all(np.isfinite(v)):
            raise ValueError("%s: probe[%r] must be finite and the same length as wavelength_nm" % (op, k))
    return wl


def _spline(x, y):
    from scipy.interpolate import CubicSpline
    return CubicSpline(np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64), bc_type="not-a-knot")


# --------------------------------------------------------------------------- #
# media (材料表 or 屈折率の数)                                                    #
# --------------------------------------------------------------------------- #
def _medium_nk(medium, wl_nm, op):
    """媒質の複素屈折率 n + ik を波長の配列で。数は分散なしの実屈折率、名前は materials の表。"""
    wl = np.atleast_1d(np.asarray(wl_nm, dtype=np.float64))
    if isinstance(medium, str):
        import materials as _mt
        rec = _mt._record(medium, op)
        n, k, _, _ = _mt._nk(rec, wl * 1e-3, op)
        return np.asarray(n, dtype=np.float64) + 1j * np.asarray(k, dtype=np.float64)
    n = _num(medium, "medium index", op, positive=True)
    if n < 1.0:
        raise ValueError("%s: a refractive index must be >= 1, got %r" % (op, medium))
    return np.full(wl.shape, n, dtype=np.complex128)


# --------------------------------------------------------------------------- #
# axial response                                                               #
# --------------------------------------------------------------------------- #
def _single_pass_amp(z_um, wl_um, na, n, lsa_um, nodes):
    """片道の軸上の振幅(焦点で 1)。瞳は cos θ で一様(Corle–Kino の重み)、縦球面収差は ρ⁴ の 1 項。

    位相 = k n z (1 − cos θ) + k W ρ⁴、W = −n s² LSA / 4(s = sin α = NA/n、縁の光線の焦点が近軸焦点から
    LSA だけずれる 3 次の球面収差)。LSA = 0 なら解析的に exp(i a(1−c0)/2) sinc(a(1−c0)/2)(a = k n z)。
    """
    z = np.atleast_1d(np.asarray(z_um, dtype=np.float64))
    k = 2.0 * math.pi / wl_um
    s = na / n
    c0 = math.sqrt(1.0 - s * s)
    span = 1.0 - c0
    if lsa_um == 0.0:
        x = 0.5 * k * n * z * span
        return np.exp(1j * x) * np.sinc(x / math.pi)
    W = -n * s * s * lsa_um / 4.0
    g, w = nodes
    c = c0 + 0.5 * span * (g + 1.0)                     # Gauss–Legendre の節を [cos α, 1] へ
    rho2 = (1.0 - c * c) / (s * s)
    ph = k * n * np.outer(z, 1.0 - c) + k * W * rho2 * rho2
    return (np.exp(1j * ph) @ (0.5 * w))


def _nodes_for(na, n, wl_um, lsa_um, z_um):
    """位相の変化量から Gauss–Legendre の節の数を決める(1 周期あたり 16 節以上)。"""
    k = 2.0 * math.pi / wl_um
    s = na / n
    span = 1.0 - math.sqrt(1.0 - s * s)
    zmax = float(np.max(np.abs(z_um))) if np.size(z_um) else 0.0
    cyc = (2.0 * k * n * zmax * span + 2.0 * k * abs(n * s * s * lsa_um / 4.0)) / (2.0 * math.pi)
    m = int(min(8192, max(256, 16 * math.ceil(cyc + 1))))
    return _leggauss(1 << (m - 1).bit_length())        # 2 の冪に丸めてキャッシュを効かせる


_LG_CACHE: dict = {}


def _leggauss(m):
    """Gauss–Legendre の節と重み(m ごとに 1 回だけ計算する。固有値計算は m² 〜 m³ で重い)。"""
    if m not in _LG_CACHE:
        _LG_CACHE[m] = np.polynomial.legendre.leggauss(m)
    return _LG_CACHE[m]


def _response(z_um, wl_um, na, n, lsa_um, target):
    z = np.atleast_1d(np.asarray(z_um, dtype=np.float64))
    if target == "mirror":                               # 往復: 位相が 2 倍(z も W も)→ |A(2z, 2W)|²
        nodes = None if lsa_um == 0.0 else _nodes_for(na, n, wl_um, 2.0 * lsa_um, 2.0 * z)
        a = _single_pass_amp(2.0 * z, wl_um, na, n, 2.0 * lsa_um, nodes)
        return np.abs(a) ** 2
    nodes = None if lsa_um == 0.0 else _nodes_for(na, n, wl_um, lsa_um, z)
    a = _single_pass_amp(z, wl_um, na, n, lsa_um, nodes)  # 点物体: 照明 × 検出 = |A|⁴
    return np.abs(a) ** 4


def _response_bins(dz_um, wl_um, na, lsa_um, target):
    """ビンごとに違う (z, λ, NA, LSA) の応答を 1 回の行列演算で(空気側、n = 1)。

    スペクトルの合成は 1 ビン 1 点なので、ビンごとに積分を呼ぶと 500 ビンで 0.5 秒かかった。節の数は
    全ビンで最も位相の回るビンに合わせる(余る節は精度を上げるだけ)。LSA = 0 のビンも同じ数値積分で
    評価する(閉形式との差は門 tests/test_chromconf.py で 1e-9 未満)。
    """
    dz = np.asarray(dz_um, dtype=np.float64)
    lam = np.asarray(wl_um, dtype=np.float64)
    a = np.asarray(na, dtype=np.float64)
    lsa = np.asarray(lsa_um, dtype=np.float64)
    passes = 2.0 if target == "mirror" else 1.0
    k = 2.0 * np.pi / lam
    s = a
    c0 = np.sqrt(1.0 - s * s)
    span = 1.0 - c0
    cyc = (passes * k * np.abs(dz) * span + passes * k * np.abs(s * s * lsa / 4.0)) / (2.0 * np.pi)
    m = int(min(8192, max(256, 16 * math.ceil(float(cyc.max()) + 1))))
    g, w = _leggauss(1 << (m - 1).bit_length())
    c = c0[:, None] + 0.5 * span[:, None] * (g[None, :] + 1.0)
    rho2 = (1.0 - c * c) / (s * s)[:, None]
    W = -(s * s) * lsa / 4.0
    ph = passes * (k * dz)[:, None] * (1.0 - c) + passes * (k * W)[:, None] * rho2 * rho2
    amp = np.exp(1j * ph) @ (0.5 * w)
    return np.abs(amp) ** 2 if target == "mirror" else np.abs(amp) ** 4


def confocal_axial_response(z_min_um: float = -40.0, z_max_um: float = 40.0, n_points: int = 401,
                            wavelength_nm: float = 550.0, numerical_aperture: float = 0.2,
                            n_medium: float = 1.0, longitudinal_sa_um: float = 0.0,
                            target: str = "mirror") -> np.ndarray:
    """共焦点顕微鏡の軸方向の応答 I(z)(焦点からのずれ z [µm] に対する検出強度)を pairs で返す。

    ``target="mirror"``(平らな鏡面)は I = [sin(u/2)/(u/2)]²、``"point"``(点の散乱体・粗面の散乱成分)は
    I = [sin(u/4)/(u/4)]⁴、u = 8π n z sin²(α/2)/λ(Corle–Chou–Kino 1986、Wilson & Sheppard 1984)。
    瞳は cos θ で一様な重み(この重みで上の式は高 NA でも厳密)。鏡面の FWHM は
    ``FWHM_X_MIRROR`` λ / (π n (1 − cos α)) ≈ 0.886 n λ / NA²(近軸)—— **λ/NA² に比例**。

    ``longitudinal_sa_um``(縁の光線の焦点 − 近軸焦点、+ は遠い側)を与えると、3 次の球面収差
    W ρ⁴(W = −n s² LSA/4)を瞳の位相に入れて Gauss–Legendre で積分する。応答のピークは
    おおよそ LSA/2 へずれ、高さは下がり幅は広がる。値は無収差のピークを 1 とした比(Strehl に相当)。

    z_min_um / z_max_um / n_points: 評価する z の格子(z_min < z_max、n_points は 3〜65536)。
    wavelength_nm: 波長。numerical_aperture: 媒質中の NA = n sin α(0 < NA < n_medium)。
    n_medium: 焦点の側の媒質の屈折率(空気 1)。target: ``"mirror"`` か ``"point"``。

    返り値: pairs(z [µm], I)。
    **Raises** ``ValueError``: 非有限・文字列・bool の数、NA ≤ 0 または NA ≥ n_medium、
    z_min ≥ z_max、未知の target。
    """
    op = "confocal_axial_response"
    z0 = _num(z_min_um, "z_min_um", op)
    z1 = _num(z_max_um, "z_max_um", op)
    if z1 <= z0:
        raise ValueError("%s: z_max_um must exceed z_min_um (got %g, %g)" % (op, z0, z1))
    m = _count(n_points, "n_points", op, 3, _MAX_POINTS)
    wl = _num(wavelength_nm, "wavelength_nm", op, positive=True)
    n = _num(n_medium, "n_medium", op, positive=True, lo=1.0)
    na = _num(numerical_aperture, "numerical_aperture", op, positive=True)
    if na >= n:
        raise ValueError("%s: numerical_aperture %g must be below n_medium %g (sin α < 1)" % (op, na, n))
    lsa = _num(longitudinal_sa_um, "longitudinal_sa_um", op)
    if target not in ("mirror", "point"):
        raise ValueError("%s: target must be 'mirror' or 'point', got %r" % (op, target))
    z = np.linspace(z0, z1, m)
    return np.ascontiguousarray(np.column_stack([z, _response(z, wl * 1e-3, na, n, lsa, target)]))


def _fwhm_closed(wl_um, na, n=1.0):
    s = na / n
    return FWHM_X_MIRROR * wl_um / (math.pi * n * (1.0 - math.sqrt(1.0 - s * s)))


def _sparrow_fraction():
    """等しい 2 つの sinc²(u/2) の和が中点で平らになる間隔 / FWHM(無次元、u の単位で解く)。"""
    from scipy.optimize import brentq

    def f(x):
        return np.sinc(x / math.pi) ** 2

    def d2(d):                                           # 中点 x = 0 の 2 階微分(差分)
        h = 1e-4
        g = lambda x: f(x - d / 2.0) + f(x + d / 2.0)    # noqa: E731
        return (g(h) - 2.0 * g(0.0) + g(-h)) / (h * h)

    d = brentq(d2, 1.0, 3.5, xtol=1e-13)                 # x = u/2 の単位での間隔
    return d / (2.0 * FWHM_X_MIRROR)                     # FWHM は x の単位で 2·1.39156


SPARROW_FRACTION = _sparrow_fraction()


# --------------------------------------------------------------------------- #
# probe: prescription -> calibration table                                     #
# --------------------------------------------------------------------------- #
def _glass_near(nd, vd, op="chromconf"):
    """材料表の硝子から、カタログの n_d・V_d が最も近いものの名前を返す(名前をソースに書かないため)。

    公開側にはメーカーの硝材名を書かない約束なので、硝材は性質(n_d・V_d)で指して材料表から引く。
    最も近い硝子が n_d で 0.002・V_d で 0.5 より離れていれば ValueError(黙って別の硝子にしない)。
    """
    import materials as _mt
    best, cost = None, None
    for r in _mt.glass_map("glass"):
        c = abs(r["nd"] - nd) / 0.002 + abs(r["vd"] - vd) / 0.5
        if cost is None or c < cost:
            best, cost = r, c
    if best is None or abs(best["nd"] - nd) > 0.002 or abs(best["vd"] - vd) > 0.5:
        raise ValueError("%s: no glass in the material table near n_d %.4f / V_d %.2f" % (op, nd, vd))
    return best["name"]


#: 高分散の重フリント(n_d 1.923・V_d 20.9)。既定の対物レンズとハイパークロマートの正のレンズ。
GLASS_DENSE_FLINT = _glass_near(1.9229, 20.88)
#: 低分散のフッ素クラウン(n_d 1.456・V_d 90.9)。ハイパークロマートの負のレンズ。
GLASS_FLUOR_CROWN = _glass_near(1.4560, 90.90)
#: ホウケイ酸クラウン(n_d 1.517・V_d 64.2)。透明板の既定の材料。
GLASS_CROWN = _glass_near(1.5168, 64.17)


def _default_surfaces():
    import raytrace as _rt
    n = _rt.refractive_index(GLASS_DENSE_FLINT, 0.575)
    return [{"R": float("inf"), "t": 4.0, "n": GLASS_DENSE_FLINT, "ap": 2.5},
            {"R": -(n - 1.0) * 16.0, "t": None, "n": 1.0, "k": -n * n}]


DEFAULT_PROBE_SURFACES = _default_surfaces()


def _marginal_focus(rt, sysw, h):
    """高さ h の平行光線(縁の光線)が光軸と交わる位置 [mm、最終面の頂点から]。"""
    r = rt.trace_rays(sysw, [[0.0, h, -1.0]], [[0.0, 0.0, 1.0]], image_mm=50.0)
    if not bool(r["valid"][0]):
        raise ValueError("the marginal ray at h = %g mm is vignetted or totally internally reflected" % h)
    P = r["points"][0, -2]
    D = r["dirs"][0, -1]
    if abs(D[1]) < 1e-15:
        raise ValueError("the marginal ray leaves parallel to the axis (no focus)")
    zl = sum(s["t"] for s in sysw["surfaces"][:-1])
    return float(P[2] + (-P[1] / D[1]) * D[2] - zl)


def _peak_offset(wl_um, na, lsa_um, fwhm_um):
    """鏡を z に置いたときの応答のピーク位置(近軸焦点から)と、その FWHM と高さ。較正の数値版。"""
    half = 3.0 * fwhm_um + 1.5 * abs(lsa_um)
    z = np.linspace(-half, half, 1201)
    r = _response(z, wl_um, na, 1.0, lsa_um, "mirror")
    i = int(np.argmax(r))
    if i == 0 or i == z.size - 1:
        raise ValueError("the mirror response peak left the search window (aberration too large)")
    a, b, c = r[i - 1], r[i], r[i + 1]
    den = a - 2.0 * b + c
    off = 0.5 * (a - c) / den if den != 0.0 else 0.0
    dz = z[1] - z[0]
    zp = z[i] + off * dz
    above = r >= 0.5 * b
    j0 = i
    while j0 > 0 and above[j0 - 1]:
        j0 -= 1
    j1 = i
    while j1 < z.size - 1 and above[j1 + 1]:
        j1 += 1
    hb = 0.5 * b

    def cross(j, k):
        return z[j] + (hb - r[j]) * (z[k] - z[j]) / (r[k] - r[j])

    left = cross(j0 - 1, j0) if j0 > 0 else z[0]
    right = cross(j1, j1 + 1) if j1 < z.size - 1 else z[-1]
    return float(zp), float(right - left), float(b)


def chromatic_confocal_probe(surfaces=None, stop: int = 0, wl_min_nm: float = 450.0,
                             wl_max_nm: float = 700.0, n_points: int = 26) -> dict:
    """対物レンズの処方から、波長 → 焦点位置の較正表(虹のものさしの目盛)を作る。

    処方 *surfaces* は :func:`raytrace.lens_system` と同じ形(dict か (R, t, n[, k[, ap]]) の列、
    硝材は名前で材料表を引く)。**平行光で入射**し、絞り(*stop* 番目の面)の ``ap`` がビーム半径。
    既定は :data:`DEFAULT_PROBE_SURFACES`(重フリントの非球面単レンズ、f ≈ 16 mm、ビーム半径 2.5 mm)。

    各波長で: 近軸の後側焦点距離(raytrace.paraxial_trace)、像側 NA、縁の光線の焦点との差
    (縦球面収差 LSA、実光線)、そして **鏡を置いて応答のピークを読む較正**(縦球面収差を入れた軸応答の
    ピーク位置。無収差なら近軸焦点と一致、収差があればおよそ LSA/2 ずれる)。

    返り値の dict(JSON にできる): ``wavelength_nm`` / ``paraxial_um``(近軸焦点、較正の原点から)/
    ``calibration_um``(鏡で較正したピーク位置、最短波長で 0)/ ``lsa_um`` / ``na`` /
    ``efl_mm`` / ``fwhm_um``(収差込みの鏡面応答の FWHM)/ ``fwhm_closed_um``(無収差の閉形式)/
    ``peak_response``(無収差に対するピークの高さ)/ ``dz_dlambda_um_per_nm``(較正表の傾き)/
    ``range_um``(較正の範囲)/ ``range_paraxial_um`` / ``working_distance_mm``(最短波長の近軸焦点、
    最終面から)/ ``origin_mm``(z = 0 の位置、最終面から)/ ``beam_radius_mm`` / ``surfaces``。

    wl_min_nm / wl_max_nm / n_points: 較正する帯域と点数(4〜1024、等間隔)。

    **Raises** ``ValueError``: 処方の誤り(raytrace がそのまま名指しする)、帯域が硝材の表の外、
    縁の光線のけられ・全反射、焦点が無い(発散系)、**較正表が波長に対して単調でない**(同じ位置に
    2 つの波長が合う = 高さが一意に決まらない)。
    """
    op = "chromatic_confocal_probe"
    import raytrace as _rt
    lo = _num(wl_min_nm, "wl_min_nm", op, positive=True)
    hi = _num(wl_max_nm, "wl_max_nm", op, positive=True)
    if hi <= lo:
        raise ValueError("%s: wl_max_nm must exceed wl_min_nm (got %g, %g)" % (op, lo, hi))
    m = _count(n_points, "n_points", op, 4, 1024)
    if surfaces is None:
        surfaces = DEFAULT_PROBE_SURFACES
    if isinstance(surfaces, (str, bytes)) or not isinstance(surfaces, (list, tuple)) or not surfaces:
        raise ValueError("%s: surfaces must be a non-empty list of surfaces (raytrace.lens_system form)" % op)
    try:
        base = _rt.lens_system([dict(s) if isinstance(s, dict) else s for s in surfaces], stop=stop,
                               wavelength_um=0.5 * (lo + hi) * 1e-3)
    except ValueError as e:
        raise ValueError("%s: %s" % (op, e)) from None
    h = float(base["surfaces"][base["stop"]]["ap"])
    wl = np.linspace(lo, hi, m)
    par, lsa, na, efl = [], [], [], []
    for w in wl:
        try:
            sw = _rt.with_wavelength(base, w * 1e-3)
            p = _rt.paraxial_trace(sw)
            mf = _marginal_focus(_rt, sw, h)
        except ValueError as e:
            raise ValueError("%s: at %.1f nm: %s" % (op, w, e)) from None
        if not (math.isfinite(p["bfl"]) and math.isfinite(p["efl"]) and p["efl"] > 0.0):
            raise ValueError("%s: the system has no real focus at %.1f nm (efl %r)" % (op, w, p["efl"]))
        par.append(p["bfl"])
        efl.append(p["efl"])
        lsa.append((mf - p["bfl"]) * 1e3)
        na.append(h / math.hypot(h, p["efl"]))          # 像側の sin(縁の光線の角度)、無限物体・アプラナティックの近似
    par = np.array(par)
    lsa = np.array(lsa)
    na = np.array(na)
    fwc = np.array([_fwhm_closed(w * 1e-3, a) for w, a in zip(wl, na)])
    offs, fw, pk = [], [], []
    for w, a, s, f in zip(wl, na, lsa, fwc):
        o, fwhm, top = _peak_offset(w * 1e-3, a, s, f)
        offs.append(o)
        fw.append(fwhm)
        pk.append(top)
    cal_abs = par * 1e3 + np.array(offs)               # µm、最終面から
    d = np.diff(cal_abs)
    if not (np.all(d > 0.0) or np.all(d < 0.0)):
        raise ValueError("%s: the calibration is not monotonic in wavelength (focus positions %s µm) — "
                         "two wavelengths would focus at the same height and the reading is ambiguous"
                         % (op, np.array2string(cal_abs, precision=1)))
    origin = cal_abs[0]
    cal = cal_abs - origin
    return {"wavelength_nm": wl.tolist(), "paraxial_um": (par * 1e3 - origin).tolist(),
            "calibration_um": cal.tolist(), "lsa_um": lsa.tolist(), "na": na.tolist(),
            "efl_mm": efl, "fwhm_um": fw, "fwhm_closed_um": fwc.tolist(), "peak_response": pk,
            "dz_dlambda_um_per_nm": np.gradient(cal, wl).tolist(),
            "range_um": float(cal[-1] - cal[0]), "range_paraxial_um": float((par[-1] - par[0]) * 1e3),
            "working_distance_mm": float(par[0]), "origin_mm": float(origin * 1e-3),
            "beam_radius_mm": h, "surfaces": [_json_surface(s) for s in surfaces],
            "stop": int(base["stop"])}


def _json_surface(s):
    """処方の面を JSON にできる形で写す(平面の R = inf は raytrace が受ける文字列 "inf" に)。"""
    d = dict(s) if isinstance(s, dict) else dict(zip(("R", "t", "n", "k", "ap"), s))
    for key in ("R", "t"):
        v = d.get(key)
        if isinstance(v, float) and math.isinf(v):
            d[key] = "inf"
    return d


def _probe_at(probe, wl_nm, op):
    """較正表を 3 次スプラインで任意の波長へ(帯域の外は ValueError)。"""
    w = _check_probe(probe, op)
    x = np.atleast_1d(np.asarray(wl_nm, dtype=np.float64))
    if x.min() < w[0] - 1e-9 or x.max() > w[-1] + 1e-9:
        raise ValueError("%s: wavelengths %.6g-%.6g nm are outside the probe calibration %.6g-%.6g nm"
                         % (op, x.min(), x.max(), w[0], w[-1]))
    return {k: _spline(w, probe[k])(x) for k in ("paraxial_um", "calibration_um", "lsa_um", "na")}


# --------------------------------------------------------------------------- #
# forward: surface + layers -> return spectrum                                 #
# --------------------------------------------------------------------------- #
def _tilt_return(tilt_deg, na):
    """傾き θ の鏡面から瞳へ戻る割合: 半径 NA の円 2 つ(中心距離 sin 2θ)の重なり / 円の面積。"""
    d = math.sin(2.0 * math.radians(abs(tilt_deg)))
    r = np.asarray(na, dtype=np.float64)
    out = np.zeros_like(r)
    ok = d < 2.0 * r
    rr = r[ok]
    if d == 0.0:
        out[ok] = 1.0
        return out
    area = 2.0 * rr * rr * np.arccos(d / (2.0 * rr)) - 0.5 * d * np.sqrt(4.0 * rr * rr - d * d)
    out[ok] = area / (math.pi * rr * rr)
    return out


def _plate_g(n, na):
    """平行平板の縦球面収差 / 厚さ(縁の焦点ずれ − 近軸の焦点ずれ、materials.plate_focus_shift と同じ式)。"""
    return 1.0 / n - np.sqrt(1.0 - na * na) / np.sqrt(n * n - na * na)


def _plate_marginal_focus_um(n: float, na: float, thickness_um: float) -> float:
    """平行平板の裏面へ集光する縁光線の焦点座標(空気側の実空間、µm)。

    Snell 則 ``sin(beta)=NA/n`` を直接使った独立な幾何光線式
    ``t*tan(beta)/tan(alpha)``。近軸座標は ``t/n`` で、両者の差は
    ``-t*_plate_g(n, NA)`` となる。ここで較正座標・LSA はともに空気中で鏡を
    動かした実空間座標であり、見かけ深さ ``t/n`` へもう一度換算しない。
    """
    alpha = math.asin(float(na))
    beta = math.asin(float(na) / float(n))
    return float(thickness_um) * math.tan(beta) / math.tan(alpha)


def chromatic_confocal_spectrum(probe, surface_um: float = 500.0, stack=(), substrate="AL",
                                source=None, detector=None, wl_step_nm: float = 0.5,
                                tilt_deg: float = 0.0, roughness_nm: float = 0.0,
                                spectrometer_fwhm_nm: float = 0.0, photons_per_peak: float = 0.0,
                                read_noise: float = 0.0, seed: int = 0) -> np.ndarray:
    """面の位置と層構成から、クロマティック共焦点の戻りスペクトルを合成する(順モデル)。

    戻りスペクトル S(λ) = 光源(λ) × 検出器(λ) × Σ_界面 [反射率 × 往復の透過 × 傾き・粗さ ×
    共焦点の軸応答(界面の見かけの位置 − 近軸焦点(λ); λ, NA(λ), LSA(λ))]、それを分光器の
    応答(ガウス、FWHM)でぼかし、光子のショット雑音と読出し雑音を足す。

    probe: :func:`chromatic_confocal_probe` の dict。波長の格子は較正の帯域を *wl_step_nm* で刻む。
    surface_um: 最上面の位置(較正表の z、µm)。
    stack: 最上面の下の透明な層の列 ``((材料, 厚さ µm), ...)``。材料は材料表の名前(:data:`GLASS_CROWN` /
        ``"PMMA"`` / ``"WATER"`` …)か屈折率の数。k があれば往復の吸収 exp(−4πk·2t/λ) が入る。
    substrate: 最下層の下の媒質(材料表の名前 —— ``"AL"`` / ``"AU"`` / ``"CU"`` / ``"SI"`` … —— か数、
        空気なら 1.0)。界面の反射率は両側の複素屈折率から垂直入射の Fresnel |(m₁ − m₂)/(m₁ + m₂)|²。
    source / detector: 光源の分光分布と検出器の分光感度(pairs、帯域を覆うこと)。None は平坦。
    tilt_deg: 面の傾き(全界面に共通)。鏡面成分は瞳との重なりの割合だけ戻る(sin 2θ ≥ 2NA で 0)。
    roughness_nm: 面の粗さ σ(RMS)。最上面の鏡面成分は exp(−(4πσ/λ)²)、残りは Lambert で NA² だけ
        戻り、点物体の応答で広がる。
    spectrometer_fwhm_nm: 分光器の線幅(0 は理想)。
    photons_per_peak: 0 なら雑音なしの期待値(最大を 1 に規格化)。正なら最大が平均この光子数になる
        ように拡大し、Poisson のショット雑音を足す。read_noise: 読出し雑音(光子数の単位の σ)。
    seed: 雑音の乱数の種(整数)。

    返り値: pairs(λ [nm], 強度)。負は 0 に切る(分光器は負の光を読まない)。
    **Raises** ``ValueError``: probe の形の誤り、帯域を覆わない source / detector、層の厚さ ≤ 0、
    材料表の区間外の波長、どの界面にも焦点が合わない(全部の界面が較正の範囲外)。
    """
    op = "chromatic_confocal_spectrum"
    w = _check_probe(probe, op)
    zs = _num(surface_um, "surface_um", op)
    step = _num(wl_step_nm, "wl_step_nm", op, positive=True)
    tilt = _num(tilt_deg, "tilt_deg", op, lo=-89.0, hi=89.0)
    sig = _num(roughness_nm, "roughness_nm", op, nonneg=True)
    sfw = _num(spectrometer_fwhm_nm, "spectrometer_fwhm_nm", op, nonneg=True)
    ph = _num(photons_per_peak, "photons_per_peak", op, nonneg=True)
    rn = _num(read_noise, "read_noise", op, nonneg=True)
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)):
        raise ValueError("%s: seed must be an integer, got %r" % (op, seed))
    nb = int(math.floor((w[-1] - w[0]) / step + 1e-9)) + 1
    if not 8 <= nb <= _MAX_POINTS:
        raise ValueError("%s: wl_step_nm %g gives %d bins over the probe band (8..%d allowed)" % (op, step, nb, _MAX_POINTS))
    lam = w[0] + step * np.arange(nb)
    P = _probe_at(probe, lam, op)
    na = P["na"]
    if isinstance(stack, (str, bytes)) or not isinstance(stack, (list, tuple)):
        raise ValueError("%s: stack must be a sequence of (material, thickness_um) pairs" % op)
    layers = []
    for i, L in enumerate(stack):
        if not isinstance(L, (list, tuple)) or len(L) != 2:
            raise ValueError("%s: stack[%d] must be (material, thickness_um), got %r" % (op, i, L))
        t = _num(L[1], "stack[%d] thickness_um" % i, op, positive=True)
        layers.append((_medium_nk(L[0], lam, op), t))
    m_sub = _medium_nk(substrate, lam, op)
    media = [np.ones(nb, dtype=np.complex128)] + [m for m, _ in layers] + [m_sub]
    ftilt = _tilt_return(tilt, na)
    spec = np.zeros(nb)
    trans = np.ones(nb)
    z_app = np.full(nb, zs)
    lsa_extra = np.zeros(nb)
    any_in_range = False
    cal = np.asarray(probe["calibration_um"], dtype=np.float64)
    for i in range(len(media) - 1):
        m1, m2 = media[i], media[i + 1]
        R = np.abs((m1 - m2) / (m1 + m2)) ** 2
        lsa = P["lsa_um"] + lsa_extra
        dz = z_app - P["paraxial_um"]
        resp = _response_bins(dz, lam * 1e-3, na, lsa, "mirror")
        spec_part = R * trans * ftilt * resp
        if i == 0 and sig > 0.0:
            tis = np.exp(-(4.0 * math.pi * sig / lam) ** 2)
            pt = _response_bins(dz, lam * 1e-3, na, lsa, "point")
            spec_part = R * trans * (ftilt * tis * resp + (1.0 - tis) * na * na * pt)
        spec += spec_part
        if np.any((z_app >= cal[0]) & (z_app <= cal[-1])):
            any_in_range = True
        if i < len(layers):                              # 次の界面へ: 往復の透過・見かけの深さ・板の球面収差
            m, t = layers[i]
            n = m.real
            kk = m.imag
            trans = trans * (1.0 - R) ** 2 * np.exp(-4.0 * math.pi * kk * 2.0 * t / (lam * 1e-3))
            z_app = z_app + t / n
            lsa_extra = lsa_extra + t * _plate_g(n, na)       # 較正と同じ空気側の実空間座標
    if not any_in_range:
        raise ValueError("%s: no interface lies inside the calibrated range %.6g..%.6g µm (top surface at "
                         "%.6g µm) — no wavelength focuses on it; the sensor reports 'no surface'"
                         % (op, cal[0], cal[-1], zs))
    if source is not None:
        s = _curve(source, "source", op, lam[0], lam[-1])
        spec = spec * np.interp(lam, s[:, 0], s[:, 1])
    if detector is not None:
        d = _curve(detector, "detector", op, lam[0], lam[-1])
        spec = spec * np.interp(lam, d[:, 0], d[:, 1])
    if sfw > 0.0:
        sg = sfw / (2.0 * math.sqrt(2.0 * math.log(2.0))) / step
        half = int(math.ceil(4.0 * sg))
        ker = np.exp(-0.5 * (np.arange(-half, half + 1) / max(sg, 1e-12)) ** 2)
        ker /= ker.sum()
        spec = np.convolve(np.pad(spec, half, mode="edge"), ker, mode="valid")
    top = float(spec.max())
    if top <= 0.0:
        raise ValueError("%s: nothing returns to the pinhole (tilt %g° with NA %.3g, or zero reflectance)"
                         % (op, tilt, float(na.min())))
    spec = spec / top
    if ph > 0.0 or rn > 0.0:
        rng = np.random.default_rng(int(seed))
        if ph > 0.0:
            spec = rng.poisson(spec * ph).astype(np.float64)
        if rn > 0.0:
            spec = spec + rng.normal(0.0, rn, nb)
    return np.ascontiguousarray(np.column_stack([lam, np.maximum(spec, 0.0)]))


# --------------------------------------------------------------------------- #
# inverse: spectrum -> peaks -> heights                                        #
# --------------------------------------------------------------------------- #
_MODES = ("gaussian", "parabolic", "centroid", "peak")


def chromatic_confocal_peaks(spectrum, reference=None, max_peaks: int = 2, mode: str = "gaussian",
                             min_prominence: float = 0.15, subtract_background: bool = True) -> list:
    """戻りスペクトルのピーク波長を(1 本または透明体の表裏の 2 本)サブビンで拾う。

    reference: 白色参照(鏡を測定範囲いっぱいに動かして取った光源 × 分光器の応答、pairs)。与えると
        スペクトルをこれで割ってから探す —— 光源のむらがピークを引っ張る偏りの補正。
    max_peaks: 返すピークの最大数(大きい順に取り、波長順に並べ直す)。
    mode: ``"gaussian"``(3 点の対数の放物線)/ ``"parabolic"``(3 点の放物線)/
        ``"centroid"``(半値より上の連続区間の重心)/ ``"peak"``(最大のビン)。sinc² の応答に対して
        どれが偏るかは PoC が測る(ガウスの式は sinc² には厳密でない)。
    min_prominence: ピークと認める突出(scipy.signal.find_peaks の prominence)の、最大値に対する割合。
    subtract_background: 中央値を引いて 0 で切ってから探す。

    返り値: ピークごとの dict の列(波長順): ``wavelength_nm`` / ``amplitude`` / ``fwhm_nm`` /
    ``bin``。
    **Raises** ``ValueError``: pairs でない・波長が等間隔でない・負の値、参照が帯域を覆わないか 0 を含む、
    ピークが 1 本も無い(平らなスペクトル)、ピークが最初か最後のビン(較正の範囲外)、頂上が 3 ビン以上
    平ら(飽和)、未知の mode。
    """
    op = "chromatic_confocal_peaks"
    from scipy.signal import find_peaks
    from interferometry import _refine
    a = _curve(spectrum, "spectrum", op)
    if a.shape[0] < 5:
        raise ValueError("%s: spectrum has %d bins; at least 5 are needed" % (op, a.shape[0]))
    lam, y = a[:, 0], a[:, 1].copy()
    st = np.diff(lam)
    if np.max(np.abs(st - st.mean())) > 1e-6 * st.mean():
        raise ValueError("%s: the wavelength axis must be uniformly spaced (resample first)" % op)
    step = float(st.mean())
    mp = _count(max_peaks, "max_peaks", op, 1, 64)
    if mode not in _MODES:
        raise ValueError("%s: mode must be one of %s, got %r" % (op, _MODES, mode))
    prom = _num(min_prominence, "min_prominence", op, positive=True, hi=1.0)
    if not isinstance(subtract_background, (bool, np.bool_)):
        raise ValueError("%s: subtract_background must be True/False" % op)
    if float(y.max()) <= 0.0:
        raise ValueError("%s: the spectrum is all zero — nothing returned to the pinhole" % op)
    tied = int((y == y.max()).sum())
    if tied >= 3:
        raise ValueError("%s: %d bins share the maximum %g — a flat top: the spectrometer is saturated, the "
                         "peak itself is missing" % (op, tied, float(y.max())))
    if reference is not None:
        r = _curve(reference, "reference", op, lam[0], lam[-1])
        rv = np.interp(lam, r[:, 0], r[:, 1])
        if np.any(rv <= 0.0):
            raise ValueError("%s: the reference is zero somewhere in the band (cannot divide)" % op)
        y = y / (rv / rv.max())
    if subtract_background:
        y = np.maximum(y - np.median(y), 0.0)
    top = float(y.max())
    if top <= 0.0:
        raise ValueError("%s: no peak above the background" % op)
    idx, props = find_peaks(np.concatenate([[0.0], y, [0.0]]), prominence=prom * top)
    idx = idx - 1
    if idx.size == 0:
        raise ValueError("%s: no peak with prominence >= %g of the maximum" % (op, prom))
    order = np.argsort(-y[idx])[:mp]
    idx = np.sort(idx[order])
    out = []
    for k in idx:
        k = int(k)
        if k == 0 or k == y.size - 1:
            raise ValueError("%s: a peak sits on bin %d of %d (the band edge) — the surface is outside the "
                             "calibrated range and its height is unknown" % (op, k, y.size))
        hb = 0.5 * y[k]
        j0, j1 = k, k
        while j0 > 0 and y[j0 - 1] >= hb:
            j0 -= 1
        while j1 < y.size - 1 and y[j1 + 1] >= hb:
            j1 += 1
        if mode == "centroid":
            seg = y[j0:j1 + 1] - hb
            off = float((seg * np.arange(j0, j1 + 1)).sum() / seg.sum()) - k if seg.sum() > 0 else 0.0
        else:
            off = float(_refine(y, np.asarray(k), mode))
        left = lam[j0] - step * (y[j0] - hb) / max(y[j0] - (y[j0 - 1] if j0 > 0 else 0.0), 1e-300) if j0 > 0 else lam[0]
        right = lam[j1] + step * (y[j1] - hb) / max(y[j1] - (y[j1 + 1] if j1 < y.size - 1 else 0.0), 1e-300) \
            if j1 < y.size - 1 else lam[-1]
        out.append({"wavelength_nm": float(lam[0] + step * (k + off)), "amplitude": float(y[k]),
                    "fwhm_nm": float(right - left), "bin": k})
    return out


def chromatic_confocal_readout(peaks, probe, layer_material=None) -> dict:
    """ピーク波長を較正表で高さ(z)へ戻し、2 ピークなら透明な層の厚さを出す。

    peaks: :func:`chromatic_confocal_peaks` の返り値(dict の列)か、波長 [nm] の列。
    probe: :func:`chromatic_confocal_probe` の dict。z は較正表を 3 次スプラインで逆引き(単調なので一意)。
    layer_material: 上の 2 ピークのあいだの層の材料(材料表の名前か屈折率の数)。与えると厚さを返す:

      * ``thickness_paraxial_um`` = n(λ₂) × (z₂ − z₁) —— 見かけの厚さ × 屈折率(近軸)。λ₂ は下の面の
        ピーク波長(下の面に焦点を結んでいるのはこの色なので、群屈折率でなく位相屈折率)。
      * ``thickness_um`` = n(λ₂)(z₂ − z₁) / (1 − n·g/2)、g = 1/n − cos α/√(n² − sin²α)。
        ``z`` と LSA は空気中で鏡を動かした実空間座標であり、平板の LSA ``t·g`` の半分だけ
        応答ピークが動く。NA は λ₂ の較正の NA。

    返り値: ``heights_um``(各ピークの z、遠いほど大)/ ``wavelengths_nm`` / 層を指定したとき
    ``apparent_thickness_um`` / ``n_layer`` / ``na`` / ``thickness_paraxial_um`` / ``thickness_um``。
    **Raises** ``ValueError``: 空のピーク列、較正の帯域の外の波長、層を指定したのにピークが 2 本でない
    (薄すぎる膜は 1 本に潰れる —— 厚さを当て推量しない)。
    """
    op = "chromatic_confocal_readout"
    w = _check_probe(probe, op)
    if isinstance(peaks, (str, bytes)) or not isinstance(peaks, (list, tuple, np.ndarray)):
        raise ValueError("%s: peaks must be the list from chromatic_confocal_peaks or wavelengths in nm" % op)
    wls = []
    for p in peaks:
        v = p.get("wavelength_nm") if isinstance(p, dict) else p
        wls.append(_num(v, "peak wavelength_nm", op, positive=True))
    if not wls:
        raise ValueError("%s: no peaks were given (empty input) — there is no height to read" % op)
    wls = sorted(wls)
    if wls[0] < w[0] - 1e-9 or wls[-1] > w[-1] + 1e-9:
        raise ValueError("%s: peak wavelengths %s nm fall outside the calibration %.6g-%.6g nm"
                         % (op, wls, w[0], w[-1]))
    cal = _spline(w, probe["calibration_um"])
    z = [float(cal(x)) for x in wls]
    out = {"heights_um": z, "wavelengths_nm": wls}
    if layer_material is not None:
        if len(wls) != 2:
            raise ValueError("%s: a layer thickness needs exactly 2 peaks (top and bottom face), got %d — a "
                             "layer thinner than the axial resolution merges into one peak "
                             "(see chromatic_confocal_limits)" % (op, len(wls)))
        n = float(_medium_nk(layer_material, wls[1], op).real[0])
        na = float(_spline(w, probe["na"])(wls[1]))
        app = z[1] - z[0]
        g = float(_plate_g(n, na))
        out.update({"apparent_thickness_um": app, "n_layer": n, "na": na,
                    "thickness_paraxial_um": n * app, "thickness_um": n * app / (1.0 - 0.5 * n * g)})
    return out


def chromatic_confocal_limits(probe, layer_material=None, tilt_max_deg: float = 30.0,
                              n_tilt: int = 61) -> dict:
    """較正表から、測定範囲・軸方向分解能・戻る傾きの上限・最小の膜厚を閉形式で出す。

    * ``range_um`` —— 較正表の端から端(焦点ずれの総量)。
    * ``fwhm_closed_um`` / ``fwhm_um`` —— 鏡面応答の FWHM(無収差の閉形式 0.4430 λ/(1 − cos α) と、
      縦球面収差込みの数値)を帯域の両端と中央で。``range_over_fwhm`` は目盛の数(範囲 / 中央の FWHM)。
    * ``max_tilt_deg`` —— 鏡面の傾きの上限(各波長の NA で sin 2θ = 2NA)。最小(最も厳しい)値。
    * ``tilt_return`` —— 中央の波長の NA で、傾き 0〜*tilt_max_deg* に対する戻る光の割合(pairs)。
    * ``min_thickness_um`` —— 等しい 2 つの鏡面応答が Sparrow の基準で分かれる見かけの間隔
      (:data:`SPARROW_FRACTION` × FWHM)に、層の n(λ) と平板の球面収差の補正を掛けた最小の厚さ
      (中央の波長)。干渉を入れない強度の重なりだけの限界(モジュールの開示を参照)。

    **Raises** ``ValueError``: probe の形の誤り、材料表の外、tilt_max_deg が (0, 89] の外。
    """
    op = "chromatic_confocal_limits"
    w = _check_probe(probe, op)
    if layer_material is None:
        layer_material = GLASS_CROWN
    tm = _num(tilt_max_deg, "tilt_max_deg", op, positive=True, hi=89.0)
    nt = _count(n_tilt, "n_tilt", op, 2, 4096)
    na = np.asarray(probe["na"], dtype=np.float64)
    i_mid = w.size // 2
    fwc = np.array([_fwhm_closed(x * 1e-3, a) for x, a in zip(w, na)])
    fw = np.asarray(probe.get("fwhm_um", fwc), dtype=np.float64)
    tmax = np.degrees(0.5 * np.arcsin(np.minimum(1.0, 2.0 * na)))
    th = np.linspace(0.0, tm, nt)
    curve = np.array([_tilt_return(t, np.array([na[i_mid]]))[0] for t in th])
    n = float(_medium_nk(layer_material, w[i_mid], op).real[0])
    g = float(_plate_g(n, na[i_mid]))
    sep = SPARROW_FRACTION * fw[i_mid]
    return {"range_um": float(probe["calibration_um"][-1] - probe["calibration_um"][0]),
            "wavelength_nm": [float(w[0]), float(w[i_mid]), float(w[-1])],
            "fwhm_closed_um": [float(fwc[0]), float(fwc[i_mid]), float(fwc[-1])],
            "fwhm_um": [float(fw[0]), float(fw[i_mid]), float(fw[-1])],
            "range_over_fwhm": float((probe["calibration_um"][-1] - probe["calibration_um"][0]) / fw[i_mid]),
            "max_tilt_deg": float(tmax.min()), "tilt_return": np.column_stack([th, curve]),
            "sparrow_fraction": float(SPARROW_FRACTION), "min_apparent_separation_um": float(sep),
            "n_layer": n, "min_thickness_um": float(n * sep / (1.0 - 0.5 * n * g))}

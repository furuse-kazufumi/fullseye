# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fourierptycho — フーリエ・タイコグラフィ(FP): 低 NA のレンズで斜めに照らした像の組 → 高 NA の複素像。

動機(2026-10-15、ViEW2026 向けの展示会調査の 3 位): 低倍率の対物は視野が広いが分解能が低く、高倍率は逆になる。
FP は LED アレイで照明の角度を変えながら低倍率で何枚も撮り、周波数空間で各像の受け持つ円(瞳)をつなぎ合わせて、
**視野は低倍率のまま、分解能は合成 NA = NA_obj + NA_ill まで**上げる。強度しか撮らないのに位相も戻る
(反復の位相回復 = 収束型の演算)。

内容(6 op):
  設計      `fp_design`(合成 NA・コヒーレントの遮断周期 λ/NA_syn・隣り合う瞳の重なり率・必要な LED の数・
            カメラ画素の標本化条件 Δx ≤ λ/(2 NA_obj)・必要な上げ倍率を、撮る前に閉形式で)
  真値      `fp_usaf_target`(USAF 1951 チャートの群・要素を、面積で正しく塗った振幅 / 位相の物体として)
  撮像      `fp_capture`(複素物体 × 傾いた平面波 → 瞳 → 低解像の強度。LED の明るさの落ち・暗視野の露光倍率・
            ショット雑音と読み出し雑音・瞳の収差・LED アレイのずれ・反射型の高さ → 位相)
  入口      `fp_stack_from_images`(装置・公開データの像の組と照明の NA を、この族の表にする)
  復元      `fp_reconstruct`(逐次の位相回復。物体のスペクトルの更新と瞳の同時推定(EPRY 型)、LED の位置の
            補正(±1 画素の探索 + アレイの幾何 4 自由度の当てはめ)、収束の履歴・止めた理由・合成 NA を返し、
            収束しなければ拒否する)
  計測      `fp_element_contrast`(USAF の要素ごとに 3 本の棒の変調を測り、どの要素まで分解したかを読む)

規約: 長さは µm(LED の幾何だけ mm)、波長は µm。照明の空間周波数 k = sinθ/λ(1/µm)、sinθ は LED の方向余弦。
k の符号: 試料を原点にした LED の位置 (x, y, z) の x/r・y/r を +k とする(r = |(x, y, z)|)。LED が試料の下にあり光が
LED から試料へ進む実機では、物理の横の波数は −x/(rλ) になりうる(座標の取り方による)。符号の取り違えは残差では
見抜けない(両軸の反転は位相の符号が反転した共役像に同じ残差で着く)ので、実機では既知の位相の試料で確かめる。
画像の行が y、列が x。スペクトルは中心が DC(fftshift の並び)。強度は「透明な背景 = 1」の単位
(fp_capture の ``photons`` は背景 1 あたりの電子数)。

順方向の模型(Zheng, Horstmeyer & Yang 2013、eq. は Yeh ら 2015 の書き方):
    I_ℓ(r) = |F⁻¹{ P(u) · O(u − u_ℓ) }|²,   u_ℓ = (sinθx, sinθy)/λ
合成 NA = NA_obj + max NA_ill。隣り合う瞳(半径 r = NA_obj/λ、中心間隔 d)の重なり率は 2 円の交わりの面積 / 円の面積:
    R = (2/π)[acos(a) − a√(1 − a²)],  a = d/(2r)
(Sun ら 2016 の定義。同論文の抄録は「重なりは少なくとも 35 % 要る」、Zheng ら 2013 は約 65 %、Zuo のグループの
平面アレイは 60.35 %)。

復元の更新(Ou, Zheng & Yang 2014 の EPRY、ePIE と同じ形):
    O ← O + α P*/|P|²max (ψ' − ψ),   P ← P + β O*/|O|²max (ψ' − ψ)
ψ' は推定の低解像の場の振幅を測った振幅に置き換えたもの。照明の NA の小さい順に 1 枚ずつ更新する(逐次型)。

★収束の判定(この族で決めたこと。文献はどれも反復の回数を固定している —— EPRY 5〜100 回、Yeh ら 200 回、
  pcFPM 12 回 —— ので、自動の停止の規則は借りてこられなかった):
  1. **停留**: 振幅の相対残差 Σ(√I − |Ψ|)² / Σ I の変化が、``stall_window`` 回(既定 10)で ``stall_tol``(既定 1 %)
     未満になった。回数の上限に届いた・残差が非有限になったら「収束しない」。
     ★逐次型は雑音のある像では厳密な不動点を持たない: 像ごとの射影が互いに食い違うので、1 周ごとの物体の変化
     (``step_history``)は 0.1〜0.4 % で止まらない(合成で実測)。瞳も推定すると、瞳が雑音を吸って残差がゆっくり
     下がり続ける(実データで 200 回後も 10 回あたり 3 %)。だから停止は「残差の改善が 10 回で 1 % 未満」に置き、
     止めた理由と履歴を返す。
  2. **一意性**: 初期値の違う 2 本(明視野像を拡大したもの / 一様)が同じ不動点に着いた(整数画素の平行移動を
     ``filters_freq.phase_correlation_fft`` で合わせ、大域の位相と振幅をそろえた相対差 ≤ ``agree_tol``)。
  ★残差だけでは**重なりの不足を見抜けない**(実測: 重なり 22 % の方が 64 % より残差が小さい —— 拘束が少ない
  分、雑音とモデルの誤差まで合わせ込める)。重なりを減らしていくと、2 本の初期値の差が 39 % で 0.057、32 % で 0.113
  に跳ぶ(Sun ら 2016 の「35 % 以上」の境とそろう)。``agree_tol = 0.08`` はこの境から決めた。
  雑音の床(χ²/N ≈ 1)は判定に使わない: 有限の視野を周期境界の FFT で表す誤差・瞳の縁の離散化・照明の
  空間周波数の丸めで、真の物体でも χ²/N が 4〜6 になる(合成で実測)。

★正直に書いておくこと:
  * 照明の k は格子に丸めて扱う(多くの公開コードと同じ)。半画素までのずれは瞳の縁のずれとして残差に出る。
  * 視野の外から入る光(実際の試料は周期的でない)は周期境界の模型で表せない。残差と比較は端の
    2 λ/(NA_obj Δx) 画素を除いて取る。
  * 瞳の同時推定(既定は 2〜4 次の多項式へ射影)は中程度の収差(rms 0.12 波)を 0.005 波まで戻す。大きな収差
    (rms 0.25 波)は瞳が戻っても 2 本の初期値が一致せず拒否される(合成で実測)。瞳を推定しない復元も、2 本が
    同じ誤った像に着けば「収束」する —— 一意性の門は収差の取り違えを見抜かない。
  * 一意性の門(2 本の初期値の差)は物体に依存する: 散乱の弱い反射型の物体(高さだけの線)や LED の位置を補正した
    復元では、重なりが十分でも位相が 0.09〜0.19 違って拒否されることがある(差は照明 NA 0.2〜0.3 の帯、つまり
    暗視野の像が受け持つ所に集まる。k を格子に丸めた模型の誤差が、弱い信号の帯で効く)。
  * LED の位置の補正は ±1 画素の局所探索とアレイの幾何(ずれ x・y、回転、高さ)の当てはめ。大きなずれ
    (1.4 mm・2°)は戻し切れない。明視野の円を探す初期化(Eckert ら 2018)は入れていない。
  * 反射型(``fp_capture(height_um=…)``)は垂直入射の往復の位相 4πh/λ を使う。照明が対物の外から入る
    反射型の構成(Pacheco ら 2016)でも復元の式は同じだが、斜め入射による位相の cosθ の変化は入れていない。
  * 照明装置と瞳の同時推定には特許がある(2033 年まで有効なものを含む)。この族は式を汎用に書いたもので、
    装置の構成は模倣しない。使う側で確かめること。

出典: G. Zheng, R. Horstmeyer, C. Yang, "Wide-field, high-resolution Fourier ptychographic microscopy",
Nat. Photonics 7, 739 (2013), doi:10.1038/nphoton.2013.187 / X. Ou, G. Zheng, C. Yang, "Embedded pupil function
recovery for Fourier ptychographic microscopy", Opt. Express 22, 4960 (2014), doi:10.1364/OE.22.004960 /
A. M. Maiden, J. M. Rodenburg, "An improved ptychographical phase retrieval algorithm for diffractive imaging",
Ultramicroscopy 109, 1256 (2009), doi:10.1016/j.ultramic.2009.05.012 / L.-H. Yeh et al., "Experimental robustness
of Fourier ptychography phase retrieval algorithms", Opt. Express 23, 33214 (2015), doi:10.1364/OE.23.033214 /
J. Sun, Q. Chen, Y. Zhang, C. Zuo, "Efficient positional misalignment correction method for Fourier ptychographic
microscopy", Biomed. Opt. Express 7, 1336 (2016), doi:10.1364/BOE.7.001336 / J. Sun et al., "Sampling criteria for
Fourier ptychographic microscopy in object space and frequency space", Opt. Express 24, 15765 (2016),
doi:10.1364/OE.24.015765 / S. Pacheco, G. Zheng, R. Liang, "Reflective Fourier ptychography", J. Biomed. Opt. 21,
026010 (2016), doi:10.1117/1.JBO.21.2.026010 / R. Eckert, Z. F. Phillips, L. Waller, "Efficient illumination
angle self-calibration in Fourier ptychography", Appl. Opt. 57, 5434 (2018), doi:10.1364/AO.57.005434。
"""
from __future__ import annotations

import math

import numpy as np

from metriccontract import MetricContractError

__all__ = [
    "fp_design",
    "fp_usaf_target",
    "fp_capture",
    "fp_stack_from_images",
    "fp_reconstruct",
    "fp_element_contrast",
]

#: 画像の一辺の上限(FFT の作業領域を確保する前に拒む)。
MAX_SIDE = 2048
#: LED(= 撮る枚数)の上限。
MAX_LEDS = 1024
#: 反復の回数の上限。
MAX_ITER_CAP = 2000
#: 2 本の初期値の差の既定の上限(重なり 39 % で 0.057、32 % で 0.113 の間。モジュールの説明を参照)。
AGREE_TOL = 0.08
#: 残差がこれまでの最小のこの倍を超えたら「発散」として止める(``converge`` の DIVERGENCE_FACTOR と同じ考え)。
DIVERGENCE_FACTOR = 100.0
#: 公表の重なり率の下限(Sun ら 2016 の抄録)と、原論文の値(Zheng ら 2013)。
OVERLAP_MIN_PUBLISHED = 0.35
OVERLAP_ZHENG_2013 = 0.65
_ABERRATIONS = ("defocus", "astigmatism", "coma", "spherical")


class FPNotConvergedError(MetricContractError):
    """位相回復が収束しなかった(``record`` に履歴と理由)。``converge.NotConvergedError`` と同じ形。"""

    def __init__(self, message, record=None):
        super().__init__(message)
        self.record = record


# --------------------------------------------------------------------------- #
# 入力の検証(fail-closed)
# --------------------------------------------------------------------------- #
def _num(v, name, op, lo=None, hi=None, lo_open=True, hi_open=False):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v))
    v = float(v)
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if lo is not None and (v < lo or (lo_open and v == lo)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and (v > hi or (hi_open and v == hi)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, "<" if hi_open else "<=", hi, v))
    return v


def _int(v, name, op, lo, hi):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    v = int(v)
    if v < lo or v > hi:
        raise ValueError("%s: %s must be in %d..%d, got %d" % (op, name, lo, hi, v))
    return v


def _real2d(a, name, op, nonneg=False, min_side=2):
    A = np.asarray(a)
    if A.dtype.kind not in "iuf" or A.ndim != 2:
        raise ValueError("%s: %s must be a real 2-D array, got %s %s" % (op, name, A.dtype, A.shape))
    if min(A.shape) < min_side or max(A.shape) > MAX_SIDE:
        raise ValueError("%s: %s sides must be in %d..%d, got %s" % (op, name, min_side, MAX_SIDE, A.shape))
    A = A.astype(np.float64)
    if not np.isfinite(A).all():
        raise ValueError("%s: %s has non-finite values" % (op, name))
    if nonneg and (A < 0).any():
        raise ValueError("%s: %s must be >= 0" % (op, name))
    return A


def _pair(v, name, op):
    try:
        a, b = v
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a pair of numbers, got %r" % (op, name, v)) from None
    return _num(a, name + "[0]", op), _num(b, name + "[1]", op)


# --------------------------------------------------------------------------- #
# 幾何: LED の格子 → 照明の空間周波数
# --------------------------------------------------------------------------- #
def _circle_overlap_fraction(d, r):
    """中心間隔 d・半径 r の 2 円の交わりの面積 / 1 円の面積(Sun ら 2016 の重なり率)。"""
    if d >= 2 * r:
        return 0.0
    if d <= 0:
        return 1.0
    a = d / (2 * r)
    return (2.0 / math.pi) * (math.acos(a) - a * math.sqrt(1.0 - a * a))


def _led_grid(n_side, pitch_mm, distance_mm, offset_mm=(0.0, 0.0), rotation_deg=0.0, height_error_mm=0.0):
    """試料の真下を中心にした n_side × n_side の正方格子の LED の (x, y, z) mm と (行, 列) の番号。"""
    c = (n_side - 1) / 2.0
    ii, jj = np.meshgrid(np.arange(n_side), np.arange(n_side), indexing="ij")
    x = (jj - c) * pitch_mm
    y = (ii - c) * pitch_mm
    t = math.radians(rotation_deg)
    xr = math.cos(t) * x - math.sin(t) * y + offset_mm[0]
    yr = math.sin(t) * x + math.cos(t) * y + offset_mm[1]
    z = np.full_like(xr, distance_mm + height_error_mm)
    return np.stack([ii.ravel(), jj.ravel()], 1), np.stack([xr.ravel(), yr.ravel(), z.ravel()], 1)


def _sin_angles(xyz):
    r = np.linalg.norm(xyz, axis=1)
    return xyz[:, 0] / r, xyz[:, 1] / r


# --------------------------------------------------------------------------- #
# fp_design
# --------------------------------------------------------------------------- #
def fp_design(na_obj=0.1, wavelength_um=0.532, led_pitch_mm=4.0, led_distance_mm=70.0, n_side=13,
              magnification=4.0, camera_pixel_um=5.2, target_na=None, field_of_view_um=None,
              boundary_tolerance_na=0.005):
    """FP の性能を**撮る前に**閉形式で(``table``): 合成 NA・遮断周期・重なり率・LED の数・画素の標本化。

    正方格子(``n_side`` × ``n_side``、ピッチ ``led_pitch_mm``)の LED を試料から ``led_distance_mm`` 下に置き、
    中心の LED を光軸に合わせた構成。

    * 照明の NA: 軸上の端の LED で NA_ill = e/√(e² + h²)(e = (n_side − 1)/2 · ピッチ)、対角の角でも返す。
    * 合成 NA = NA_obj + NA_ill(軸)。棒が軸に沿った USAF チャートの分解能を決めるのは軸の値(対角の LED は
      x だけの周波数を瞳に入れない)。コヒーレントの遮断周期 λ/NA_syn(対物だけなら λ/NA_obj)、半周期 λ/(2 NA_syn)。
    * 重なり率: 中心の LED とその隣の瞳の円(半径 NA_obj/λ、中心間隔 = sinθ の差/λ)の交わりの面積 / 円の面積
      = (2/π)[acos a − a√(1 − a²)]、a = d/(2r)。中心が最も小さく(sinθ の刻みは外ほど狭い)、端の値も返す。
      ``overlap_ok`` = 中心の値 ≥ 0.35(Sun ら 2016 の下限)。
    * 標本化: 物体側の画素 Δx = camera_pixel_um / magnification が λ/(2 NA_obj) 以下(R_cam = λ·M/(2 NA_obj Δx_cam)
      ≥ 1)。強度の帯域で見たナイキスト λ/(4 NA_obj) も返す(FP は場を戻すので λ/(2 NA_obj) で足りる)。
    * 上げ倍率: 高解像の画素が λ/(2 NA_syn) 以下になる最小の整数。
    * 境の LED: 照明の NA が NA_obj と ``boundary_tolerance_na`` 以内の LED の数(``boundary_leds``)。その像は
      明視野と暗視野の境で、瞳の縁が照明の 0 次を切るかどうかが k の丸め 1 画素で入れ替わる —— 実測では重なり 39 % の
      構成がこれ 1 つで収束しなくなった(256 画素の視野で。LED の距離を 70 → 76 mm にずらすと収束。384 画素の視野では
      境のままでも収束した —— 起きうるが必ずではない)。``boundary_ok`` = 0 枚。
    * ``target_na``: その合成 NA に要る格子の一辺・LED の総数・照明の NA が足りる LED の数。
    * ``field_of_view_um``: 空間帯域幅積(視野 / 半周期)²。

    返り値: dict(kind="fp_design", na_synthetic, na_illumination_max_axis, coherent_cutoff_period_um,
    overlap_ratio_centre, overlap_ratio_edge, overlap_ok, n_leds, n_brightfield, boundary_leds, boundary_ok,
    object_pixel_um, r_cam,
    pixel_sampling_ok, upsample_needed, …)。
    """
    op = "fp_design"
    na = _num(na_obj, "na_obj", op, lo=0.0, hi=1.0, hi_open=True)
    lam = _num(wavelength_um, "wavelength_um", op, lo=0.0, hi=20.0)
    p = _num(led_pitch_mm, "led_pitch_mm", op, lo=0.0)
    h = _num(led_distance_mm, "led_distance_mm", op, lo=0.0)
    n = _int(n_side, "n_side", op, 1, 31)
    mag = _num(magnification, "magnification", op, lo=0.0)
    cam = _num(camera_pixel_um, "camera_pixel_um", op, lo=0.0)
    edge = (n - 1) / 2.0 * p
    na_ill_axis = edge / math.hypot(edge, h)
    na_ill_diag = math.hypot(edge, edge) / math.sqrt(2 * edge * edge + h * h)
    s1 = p / math.hypot(p, h)                              # 中心の LED と隣の sinθ の差
    overlap = _circle_overlap_fraction(s1 / lam, na / lam)
    if n >= 3:
        e2 = edge - p
        s_out = edge / math.hypot(edge, h) - e2 / math.hypot(e2, h)
        overlap_edge = _circle_overlap_fraction(s_out / lam, na / lam)
    else:
        overlap_edge = None
    na_syn = na + na_ill_axis
    px_obj = cam / mag
    _, xyz = _led_grid(n, p, h)
    sx, sy = _sin_angles(xyz)
    btol = _num(boundary_tolerance_na, "boundary_tolerance_na", op, lo=0.0, lo_open=False, hi=0.5)
    n_bound = int(np.sum(np.abs(np.hypot(sx, sy) - na) <= btol))
    out = {
        "kind": "fp_design",
        "na_obj": na, "wavelength_um": lam,
        "na_illumination_max_axis": na_ill_axis,
        "na_illumination_max_diagonal": na_ill_diag,
        "na_synthetic": na_syn,
        "na_synthetic_diagonal": na + na_ill_diag,
        "resolution_gain": na_syn / na,
        "coherent_cutoff_period_um": lam / na_syn,
        "coherent_cutoff_period_objective_um": lam / na,
        "half_period_um": lam / (2 * na_syn),
        "overlap_ratio_centre": overlap,
        "overlap_ratio_edge": overlap_edge,
        "overlap_ok": bool(overlap >= OVERLAP_MIN_PUBLISHED),
        "overlap_min_published": OVERLAP_MIN_PUBLISHED,
        "led_step_na_centre": s1,
        "n_leds": n * n,
        "n_brightfield": int(np.sum(np.hypot(sx, sy) < na)),
        "boundary_leds": n_bound,
        "boundary_ok": bool(n_bound == 0),
        "object_pixel_um": px_obj,
        "r_cam": lam / (2 * na * px_obj),
        "nyquist_pixel_field_um": lam / (2 * na),
        "nyquist_pixel_intensity_um": lam / (4 * na),
        "pixel_sampling_ok": bool(px_obj <= lam / (2 * na)),
        "upsample_needed": int(math.ceil(px_obj / (lam / (2 * na_syn)) - 1e-9)),
    }
    if target_na is not None:
        tn = _num(target_na, "target_na", op, lo=na, hi=na + 1.0, hi_open=True)
        need = tn - na
        x_need = h * need / math.sqrt(1 - need * need)
        half = int(math.ceil(x_need / p - 1e-9))
        if 2 * half + 1 > 63:
            raise ValueError("%s: target_na %.3f needs a %d-wide grid (more than 63)" % (op, tn, 2 * half + 1))
        _, xyz2 = _led_grid(2 * half + 1, p, h)
        a, b = _sin_angles(xyz2)
        out.update({"target_na": tn, "n_side_needed": 2 * half + 1, "n_leds_needed": (2 * half + 1) ** 2,
                    "n_leds_needed_within_na": int(np.sum(np.hypot(a, b) <= need + 1e-12))})
    if field_of_view_um is not None:
        fov = _num(field_of_view_um, "field_of_view_um", op, lo=0.0)
        out["space_bandwidth_product"] = (fov / (lam / (2 * na_syn))) ** 2
        out["space_bandwidth_product_objective"] = (fov / (lam / (2 * na))) ** 2
    return out


# --------------------------------------------------------------------------- #
# USAF 1951 チャート
# --------------------------------------------------------------------------- #
def _usaf_lp_mm(group, element):
    return 2.0 ** (group + (element - 1) / 6.0)


def fp_usaf_target(groups=(7, 8, 9), elements=(1, 2, 3, 4, 5, 6), pixel_um=0.325, shape=(384, 384),
                   kind="amplitude", bar_value=0.2, background=1.0, phase_rad=1.0, supersample=8, margin_px=6):
    """USAF 1951 チャートの要素を並べた物体(``table``): 振幅(棒が暗い)か位相(棒の位相が ``phase_rad``)か両方。

    要素 (G, E) の線の対の数は 2^(G + (E − 1)/6) lp/mm、周期 = 1000 / それ µm、棒の幅は周期の半分、長さは幅の 5 倍。
    各要素は縦の棒 3 本(x に変わる)と横の棒 3 本(y に変わる)を横に並べ、読み順(群の小さい順、要素の順)に
    左上から詰める。入り切らない要素は落とす(返り値の ``elements`` に載るものだけが描かれている)。
    棒は ``supersample`` 倍の細格子で塗って画素ごとに平均する(面積で正しい被覆率)。棒の幅は細格子の整数に
    丸めるので、``elements[i]["period_um"]`` は丸めた後の実際の周期(公称は ``period_nominal_um``)。
    ``kind="both"`` は棒が暗く、かつ位相も ``phase_rad`` だけ進む物体(染めた厚い棒。振幅と位相が同じ所で変わる)。

    返り値: dict(kind="fp_target", amplitude, phase, coverage, pixel_um, elements=[{group, element, lp_per_mm,
    period_um, period_nominal_um, vertical_bars_box, horizontal_bars_box}], target_kind)。箱は (行0, 行1, 列0, 列1)
    の画素座標(端の値は小数のことがある)。
    """
    op = "fp_usaf_target"
    dx = _num(pixel_um, "pixel_um", op, lo=0.0)
    try:
        ny, nx = shape
    except (TypeError, ValueError):
        raise ValueError("%s: shape must be (rows, cols), got %r" % (op, shape)) from None
    ny = _int(ny, "shape[0]", op, 16, MAX_SIDE)
    nx = _int(nx, "shape[1]", op, 16, MAX_SIDE)
    ss = _int(supersample, "supersample", op, 1, 32)
    mg = _int(margin_px, "margin_px", op, 0, min(ny, nx) // 4)
    if kind not in ("amplitude", "phase", "both"):
        raise ValueError("%s: kind must be 'amplitude', 'phase' or 'both', got %r" % (op, kind))
    bv = _num(bar_value, "bar_value", op, lo=0.0, lo_open=False)
    bg = _num(background, "background", op, lo=0.0)
    pr = _num(phase_rad, "phase_rad", op)
    gl = [_int(g, "groups[]", op, -2, 11) for g in groups]
    el = [_int(e, "elements[]", op, 1, 6) for e in elements]
    if not gl or not el:
        raise ValueError("%s: groups and elements must not be empty" % op)
    hi = np.zeros((ny * ss, nx * ss), np.float64)
    fine = dx / ss
    els = []
    cy, cx = mg * ss, mg * ss
    row_h = 0
    for g in gl:
        for e in el:
            lp = _usaf_lp_mm(g, e)
            w = 1000.0 / lp / 2.0
            wpx = int(round(w / fine))
            if wpx < 1:
                continue                                           # 細格子より細い棒は描けない
            Lpx = 5 * wpx
            gap = max(2 * wpx, 2 * ss)
            blk_w = 5 * wpx + gap + Lpx
            if cx + blk_w > (nx - mg) * ss:
                cx = mg * ss
                cy += row_h + max(gap, 3 * ss)
                row_h = 0
            if cy + Lpx > (ny - mg) * ss or cx + blk_w > (nx - mg) * ss:
                continue
            for b in range(3):
                hi[cy:cy + Lpx, cx + 2 * b * wpx:cx + (2 * b + 1) * wpx] = 1.0
            vbox = (cy / ss, (cy + Lpx) / ss, cx / ss, (cx + 5 * wpx) / ss)
            x2 = cx + 5 * wpx + gap
            for b in range(3):
                hi[cy + 2 * b * wpx:cy + (2 * b + 1) * wpx, x2:x2 + Lpx] = 1.0
            hbox = (cy / ss, (cy + 5 * wpx) / ss, x2 / ss, (x2 + Lpx) / ss)
            els.append({"group": g, "element": e, "lp_per_mm": lp, "period_um": 2 * wpx * fine,
                        "period_nominal_um": 1000.0 / lp, "vertical_bars_box": vbox, "horizontal_bars_box": hbox})
            cx += blk_w + gap
            row_h = max(row_h, Lpx)
    if not els:
        raise ValueError("%s: no element fits into %s pixels of %g um" % (op, (ny, nx), dx))
    cover = hi.reshape(ny, ss, nx, ss).mean(axis=(1, 3))
    if kind == "amplitude":
        amp = bg + (bv - bg) * cover
        ph = np.zeros_like(amp)
    elif kind == "phase":
        amp = np.full_like(cover, bg)
        ph = pr * cover
    else:
        amp = bg + (bv - bg) * cover
        ph = pr * cover
    return {"kind": "fp_target", "amplitude": amp, "phase": ph, "coverage": cover, "pixel_um": dx,
            "elements": els, "target_kind": kind}


# --------------------------------------------------------------------------- #
# 順方向の模型
# --------------------------------------------------------------------------- #
def _pupil(n, cutoff_px, aberr):
    """n × n の瞳(中心が DC)。収差は Zernike 型の多項式の係数(波長の単位、瞳の縁で正規化)。"""
    fy = (np.arange(n) - n // 2)[:, None]
    fx = (np.arange(n) - n // 2)[None, :]
    rx = fx / cutoff_px
    ry = fy / cutoff_px
    rho2 = rx * rx + ry * ry
    S = rho2 <= 1.0
    W = (aberr.get("defocus", 0.0) * (2 * rho2 - 1)
         + aberr.get("astigmatism", 0.0) * (rx * rx - ry * ry)
         + aberr.get("coma", 0.0) * (3 * rho2 - 2) * rx
         + aberr.get("spherical", 0.0) * (6 * rho2 * rho2 - 6 * rho2 + 1))
    return S.astype(np.complex128) * np.exp(2j * np.pi * W), S


def _aberr(v, op):
    if v is None:
        return {}
    if not isinstance(v, dict):
        raise ValueError("%s: pupil_aberration must be a dict of %s (waves), got %r" % (op, _ABERRATIONS, v))
    out = {}
    for k, c in v.items():
        if k not in _ABERRATIONS:
            raise ValueError("%s: unknown aberration %r (known: %s)" % (op, k, ", ".join(_ABERRATIONS)))
        out[k] = _num(c, "pupil_aberration[%s]" % k, op, lo=-5.0, hi=5.0)
    return out


def fp_capture(amplitude, phase=None, pixel_um=0.325, wavelength_um=0.532, na_obj=0.1, downsample=4,
               led_pitch_mm=4.0, led_distance_mm=70.0, n_side=13, pupil_aberration=None,
               photons=4000.0, read_noise_e=2.0, darkfield_gain=8.0, cos_exponent=1.0, seed=0,
               led_offset_mm=(0.0, 0.0), led_rotation_deg=0.0, led_height_error_mm=0.0, height_um=None,
               pad_px=None):
    """LED アレイで斜めに照らした低解像の像の組を合成する(``table``、kind="fp_stack")。

    物体 o = amplitude · e^{i phase}(``pixel_um`` の細かい格子、正方で一辺が ``downsample`` で割り切れる)。
    LED ごとに o に傾いた平面波 e^{i2π(kx x + ky y)} を掛け(**画素の半端な k もそのまま**)、FFT → 中心を
    低解像の大きさで切り出す → 瞳(円 NA_obj/λ × 収差)→ 逆 FFT → |·|²。視野の外の光が入るよう、物体を ``pad_px``
    (既定 = 一辺の 1/4)だけ端の値で広げて描き、カメラの視野だけを切り出す(実際の試料は周期的でない)。

    * ``height_um`` を渡すと**反射型**: 面の高さ h → 往復の位相 4πh/λ(垂直入射の近似)を ``phase`` に足す。
    * LED の明るさ: 方位の Lambert 次数 m(``cos_exponent``)と距離の 2 乗の落ち → cos^(m+3)θ(中心で 1)。
    * 露光: 明視野(NA_ill < NA_obj)は 1、暗視野は ``darkfield_gain`` 倍(暗視野を長く撮る実装の慣習)。
    * 雑音: 背景 1 あたり ``photons`` 電子 × 露光 × 明るさの Poisson + 読み出し ``read_noise_e`` のガウス。
      乱数は ``seed`` の ``np.random.default_rng``。
    * LED アレイのずれ(``led_offset_mm`` / ``led_rotation_deg`` / ``led_height_error_mm``)は**撮像にだけ**入れ、
      表の名目の ``kx`` / ``ky`` には入れない(真の値は ``kx_true`` / ``ky_true``)。
    * 照明の k の規約: kx = x/(rλ)、ky = y/(rλ)(LED の位置 (x, y, z) は試料が原点、r = |(x, y, z)|)—— LED の
      x/r を +k とする。LED が試料の下にあり光が LED から試料へ進む実機では、物理の横の波数は −x/(rλ) になりうる。
    * 低解像の画素 = pixel_um · downsample が λ/(2 NA_obj) を超えると拒否(FP の標本化条件)。

    返り値: dict(kind="fp_stack", images (K, n, n) 電子数、照明の NA の小さい順, exposure, led_brightness, photons,
    read_noise_e, kx, ky, kx_true, ky_true, na_illumination, led_index, led_xyz_mm(名目), pixel_um(低解像),
    wavelength_um, na_obj, pupil_true, na_synthetic_design, …)。
    """
    op = "fp_capture"
    A = _real2d(amplitude, "amplitude", op, nonneg=True, min_side=16)
    ph = np.zeros_like(A) if phase is None else _real2d(phase, "phase", op, min_side=16)
    if ph.shape != A.shape:
        raise ValueError("%s: phase shape %s differs from amplitude %s" % (op, ph.shape, A.shape))
    dx = _num(pixel_um, "pixel_um", op, lo=0.0)
    lam = _num(wavelength_um, "wavelength_um", op, lo=0.0, hi=20.0)
    na = _num(na_obj, "na_obj", op, lo=0.0, hi=1.0, hi_open=True)
    ds = _int(downsample, "downsample", op, 1, 16)
    ns = _int(n_side, "n_side", op, 1, 31)
    pitch = _num(led_pitch_mm, "led_pitch_mm", op, lo=0.0)
    dist = _num(led_distance_mm, "led_distance_mm", op, lo=0.0)
    ab = _aberr(pupil_aberration, op)
    ph_e = _num(photons, "photons", op, lo=0.0)
    rn = _num(read_noise_e, "read_noise_e", op, lo=0.0, lo_open=False)
    dg = _num(darkfield_gain, "darkfield_gain", op, lo=0.0)
    m_led = _num(cos_exponent, "cos_exponent", op, lo=0.0, lo_open=False, hi=50.0)
    sd = _int(seed, "seed", op, 0, (1 << 63) - 1)
    off_mm = _pair(led_offset_mm, "led_offset_mm", op)
    rot = _num(led_rotation_deg, "led_rotation_deg", op, lo=-45.0, hi=45.0)
    dh = _num(led_height_error_mm, "led_height_error_mm", op, lo=-dist, hi=dist)
    N = A.shape[0]
    if A.shape[0] != A.shape[1] or N % ds:
        raise ValueError("%s: the object must be square with a side divisible by downsample=%d, got %s"
                         % (op, ds, A.shape))
    n = N // ds
    if dx * ds > lam / (2 * na):
        raise ValueError("%s: the camera pixel on the object, %.4g um, exceeds lambda/(2 NA_obj) = %.4g um (the FP "
                         "sampling condition)" % (op, dx * ds, lam / (2 * na)))
    if height_um is not None:
        hh = _real2d(height_um, "height_um", op, min_side=16)
        if hh.shape != A.shape:
            raise ValueError("%s: height_um shape %s differs from amplitude %s" % (op, hh.shape, A.shape))
        ph = ph + 4.0 * math.pi * hh / lam
    pad = (N // 4 if pad_px is None else _int(pad_px, "pad_px", op, 0, 4 * N))
    pad = int(math.ceil(pad / ds) * ds)
    obj = A * np.exp(1j * ph)
    big = np.pad(obj, pad, mode="edge")
    Nb = big.shape[0]
    nb = Nb // ds
    df_big = 1.0 / (Nb * dx)
    P_big, _ = _pupil(nb, (na / lam) / df_big, ab)
    idx, xyz_nom = _led_grid(ns, pitch, dist)
    _, xyz = _led_grid(ns, pitch, dist, off_mm, rot, dh)
    if (xyz[:, 2] <= 0).any():
        raise ValueError("%s: the LED array must stay below the sample (distance + height error > 0)" % op)
    sxn, syn = _sin_angles(xyz_nom)
    sx, sy = _sin_angles(xyz)
    order = np.lexsort((idx[:, 1], idx[:, 0], np.round(np.hypot(sxn, syn), 12)))
    coords = np.arange(Nb) * dx
    rng = np.random.default_rng(sd)
    cos_t = xyz[:, 2] / np.linalg.norm(xyz, axis=1)
    bright = cos_t ** (m_led + 3.0)
    bright = bright / bright.max()
    imgs = np.empty((len(order), n, n))
    exposure = np.empty(len(order))
    r0 = Nb // 2 - nb // 2
    sl = slice(pad // ds, pad // ds + n)
    for o, j in enumerate(order):
        ex = np.exp(2j * np.pi * (sx[j] / lam) * coords)[None, :] * np.exp(2j * np.pi * (sy[j] / lam) * coords)[:, None]
        S = np.fft.fftshift(np.fft.fft2(big * ex))
        low = np.fft.ifft2(np.fft.ifftshift(S[r0:r0 + nb, r0:r0 + nb] * P_big)) * (nb * nb) / (Nb * Nb)
        I = (low.real ** 2 + low.imag ** 2)[sl, sl]
        g = 1.0 if math.hypot(sxn[j], syn[j]) < na else dg
        exposure[o] = g
        mean_e = I * ph_e * g * bright[j]
        imgs[o] = rng.poisson(mean_e) + rng.normal(0.0, rn, mean_e.shape)
    df_rec = 1.0 / (n * ds * dx)
    P_true, _ = _pupil(n, (na / lam) / df_rec, ab)
    na_ill = np.hypot(sxn[order], syn[order])
    return {
        "kind": "fp_stack", "images": imgs, "exposure": exposure, "led_brightness": bright[order],
        "photons": ph_e, "read_noise_e": rn,
        "kx": sxn[order] / lam, "ky": syn[order] / lam,
        "kx_true": sx[order] / lam, "ky_true": sy[order] / lam,
        "na_illumination": na_ill, "led_index": idx[order], "led_xyz_mm": xyz_nom[order],
        "led_pitch_mm": pitch, "led_distance_mm": dist, "n_side": ns,
        "pixel_um": dx * ds, "object_pixel_um": dx, "wavelength_um": lam, "na_obj": na, "pupil_true": P_true,
        "na_synthetic_design": na + float(na_ill.max()),
    }


def fp_stack_from_images(images, na_x, na_y, wavelength_um, na_obj, pixel_um, values="intensity",
                         exposure=None, led_xyz_mm=None):
    """装置・公開データの像の組を、この族の表にする(``table``、kind="fp_stack")。

    ``images`` は (K, n, n) の正方の像(``values="amplitude"`` なら振幅、2 乗して強度にする)。``na_x`` / ``na_y`` は
    LED ごとの照明の方向余弦 sinθx・sinθy(**この族の符号**: :func:`fp_capture` と同じく LED の位置の x/r・y/r を
    + とし、u_ℓ = (na_x, na_y)/λ のとき瞳は物体のスペクトルの −u_ℓ を中心に切り出す(I = |F⁻¹{P(u)·O(u − u_ℓ)}|²)。
    LED が試料の下にあり光が LED から試料へ進む装置では、物理の横の波数は −x/r になりうる)。
    ★符号の取り違えは残差では検出できない: 両軸の反転は位相の符号が反転した像(共役)に同じ残差で着き、片軸の反転も
    合成では残差が 1.8 倍になるだけで「収束」した。位相の符号が分かっている試料で、復元の位相の符号を確かめて決める。
    ``exposure`` は像ごとの露光の比(像をこれで割る)。``led_xyz_mm`` を渡すと LED の位置の補正が使える。
    照明の NA の小さい順に並べ替え、元の番号を ``source_order`` に残す。
    カメラの画素(物体側)が λ/(2 NA_obj) を超えると拒否(FP の標本化条件)。
    """
    op = "fp_stack_from_images"
    I = np.asarray(images)
    if I.dtype.kind not in "iuf" or I.ndim != 3 or I.shape[1] != I.shape[2]:
        raise ValueError("%s: images must be a real (K, n, n) array, got %s %s" % (op, I.dtype, I.shape))
    K, n, _ = I.shape
    if K < 2 or K > MAX_LEDS or n < 16 or n > MAX_SIDE:
        raise ValueError("%s: need 2..%d images of side 16..%d, got %s" % (op, MAX_LEDS, MAX_SIDE, I.shape))
    I = I.astype(np.float64)
    if not np.isfinite(I).all():
        raise ValueError("%s: images have non-finite values" % op)
    if values not in ("intensity", "amplitude"):
        raise ValueError("%s: values must be 'intensity' or 'amplitude', got %r" % (op, values))
    if values == "amplitude":
        if (I < 0).any():
            raise ValueError("%s: amplitudes must be >= 0" % op)
        I = I * I
    ax = np.asarray(na_x, np.float64).ravel()
    ay = np.asarray(na_y, np.float64).ravel()
    if ax.shape != (K,) or ay.shape != (K,) or not (np.isfinite(ax).all() and np.isfinite(ay).all()):
        raise ValueError("%s: na_x and na_y must be %d finite numbers each" % (op, K))
    if (np.hypot(ax, ay) >= 1.0).any():
        raise ValueError("%s: an illumination NA must be < 1" % op)
    lam = _num(wavelength_um, "wavelength_um", op, lo=0.0, hi=20.0)
    na = _num(na_obj, "na_obj", op, lo=0.0, hi=1.0, hi_open=True)
    px = _num(pixel_um, "pixel_um", op, lo=0.0)
    if px > lam / (2 * na):
        raise ValueError("%s: pixel_um %.4g exceeds lambda/(2 NA_obj) = %.4g — the bright-field pupil is aliased on the "
                         "camera grid (the FP sampling condition)" % (op, px, lam / (2 * na)))
    ex = np.ones(K) if exposure is None else np.asarray(exposure, np.float64).ravel()
    if ex.shape != (K,) or not (np.isfinite(ex).all() and (ex > 0).all()):
        raise ValueError("%s: exposure must be %d positive numbers" % (op, K))
    order = np.lexsort((np.arange(K), np.round(np.hypot(ax, ay), 12)))
    out = {"kind": "fp_stack", "images": I[order], "exposure": ex[order], "led_brightness": np.ones(K),
           "photons": 1.0, "read_noise_e": None,
           "kx": ax[order] / lam, "ky": ay[order] / lam, "na_illumination": np.hypot(ax, ay)[order],
           "pixel_um": px, "wavelength_um": lam, "na_obj": na, "source_order": order,
           "na_synthetic_design": na + float(np.hypot(ax, ay).max())}
    if led_xyz_mm is not None:
        xyz = np.asarray(led_xyz_mm, np.float64)
        if xyz.shape != (K, 3) or not np.isfinite(xyz).all() or (xyz[:, 2] <= 0).any():
            raise ValueError("%s: led_xyz_mm must be (%d, 3) finite with z > 0" % (op, K))
        out["led_xyz_mm"] = xyz[order]
    return out


# --------------------------------------------------------------------------- #
# 復元(逐次の EPRY / ePIE 型の更新)
# --------------------------------------------------------------------------- #
def _fft(a):
    return np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(a)))


def _ifft(a):
    return np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(a)))


def _low_field(O, r0, c0, n, P):
    return _ifft(O[r0:r0 + n, c0:c0 + n] * P)


def _amp_resid(amp, Psi, inner):
    d = amp[inner, inner] - np.abs(Psi[inner, inner])
    return float(np.sum(d * d))


def _predict_centres(params, xyz, lam, df, sign):
    x0, y0, th, dh = params
    c, s = math.cos(th), math.sin(th)
    x = c * xyz[:, 0] - s * xyz[:, 1] + x0
    y = s * xyz[:, 0] + c * xyz[:, 1] + y0
    z = xyz[:, 2] + dh
    r = np.sqrt(x * x + y * y + z * z)
    return sign * (y / r) / lam / df, sign * (x / r) / lam / df


def _fit_led_geometry(cy, cx, xyz, lam, df, sign, w):
    """LED アレイの幾何(ずれ x・y mm、回転 rad、高さ mm)を、各 LED の瞳の中心に最小二乗で当てる(Sun ら 2016 の後段)。"""
    from scipy.optimize import least_squares  # noqa: PLC0415 — numpy だけの環境で import を落とさない

    def res(p):
        py_, px_ = _predict_centres(p, xyz, lam, df, sign)
        return np.concatenate([(py_ - cy) * w, (px_ - cx) * w])

    sol = least_squares(res, np.zeros(4), x_scale=np.array([1.0, 1.0, 0.01, 1.0]))
    return sol.x


#: LED の位置の探索の候補(この順で比べ、同点は先のものを取る)。
_CANDIDATES = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))


def _pupil_basis(S, degree):
    """瞳の位相の基底: 瞳の円の上で直交化した単項式 x^a y^b(2 ≤ a + b ≤ degree)。ピストンと傾き(物体の平行移動と
    区別できない)は入れない。返り値 (B, Bᵀ)。B は (円の画素数, 基底の数) の正規直交の列。"""
    yy, xx = np.nonzero(S)
    n = S.shape[0]
    r = max(float(np.max(np.hypot(yy - n // 2, xx - n // 2))), 1.0)
    x = (xx - n // 2) / r
    y = (yy - n // 2) / r
    cols = [np.ones_like(x), x, y]
    for deg in range(2, degree + 1):
        for a in range(deg, -1, -1):
            cols.append(x ** a * y ** (deg - a))
    Q, _ = np.linalg.qr(np.stack(cols, 1))
    B = Q[:, 3:]                                                  # ピストンと傾きを除いた直交基底
    return B, B.T


def _run(amp, centres, P0, S, O0, n_iter, pupil_update, pupil_start, alpha, beta, led, xyz, lam, df, sign,
         stall_tol, stall_window, inner, intensity_correction, basis=None):
    K, n, _ = amp.shape
    Sidx = np.nonzero(S)
    N = O0.shape[0]
    off = N // 2 - n // 2
    O = O0.copy()
    P = P0.copy()
    cy, cx = centres[0].copy(), centres[1].copy()
    scale = np.ones(K)
    energy = np.array([float(np.sum(a[inner, inner] ** 2)) for a in amp])
    hist = []
    status, reason = "max_iterations", None
    geo = None
    steps = []
    for it in range(n_iter):
        acc = 0.0
        total = float(np.sum(energy * scale ** 2))      # 明るさの補正の後の測った像のエネルギー
        O_prev = O.copy()
        for j in range(K):
            a = amp[j] * scale[j]
            if led is not None and it >= led and j > 0:
                best = None
                for (dy, dx) in _CANDIDATES:
                    r0, c0 = off + cy[j] + dy, off + cx[j] + dx
                    if r0 < 0 or c0 < 0 or r0 + n > N or c0 + n > N:
                        continue
                    e = round(_amp_resid(a, _low_field(O, r0, c0, n, P), inner), 9)
                    if best is None or e < best[0]:
                        best = (e, dy, dx)
                cy[j] += best[1]
                cx[j] += best[2]
            r0, c0 = off + cy[j], off + cx[j]
            Or = O[r0:r0 + n, c0:c0 + n].copy()
            psi = Or * P
            Psi = _ifft(psi)
            if intensity_correction and it >= 2 and j > 0:      # 最初の像(照明の NA が最小)が明るさの基準
                m_meas = float(np.mean(amp[j]))
                if m_meas > 0:
                    scale[j] = float(np.mean(np.abs(Psi))) / m_meas
                    a = amp[j] * scale[j]
            acc += _amp_resid(a, Psi, inner)
            d = _fft(a * np.exp(1j * np.angle(Psi))) - psi
            O[r0:r0 + n, c0:c0 + n] = Or + alpha * np.conj(P) / max(float(np.max(np.abs(P) ** 2)), 1e-300) * d
            if pupil_update and it >= pupil_start:
                Pn = (P + beta * np.conj(Or) / max(float(np.max(np.abs(Or) ** 2)), 1e-300) * d) * S
                if basis is not None:
                    # 位相の増分を低次の基底へ射影し、振幅は 1(純位相の瞳)に保つ —— 瞳が雑音を吸わない
                    dphi = np.angle(Pn[Sidx] * np.conj(P[Sidx]))
                    ph = np.angle(P[Sidx]) + basis[0] @ (basis[1] @ dphi)
                    Pn = np.zeros_like(P)
                    Pn[Sidx] = np.exp(1j * ph)
                P = Pn
        if led is not None and it >= led and xyz is not None:
            w = np.ones(K)
            w[0] = 0.0
            geo = _fit_led_geometry(cy.astype(float), cx.astype(float), xyz, lam, df, sign, w)
            py_, px_ = _predict_centres(geo, xyz, lam, df, sign)
            cy, cx = np.round(py_).astype(int), np.round(px_).astype(int)
        e = acc / max(total, 1e-300)
        hist.append(e)
        steps.append(float(np.linalg.norm(O - O_prev) / max(np.linalg.norm(O), 1e-300)))
        if not math.isfinite(e):
            status, reason = "diverged", "diverged: non-finite residual at iteration %d" % it
            break
        if e > DIVERGENCE_FACTOR * min(hist):
            status, reason = "diverged", ("diverged: the residual grew to %.3g, %.0f times its minimum %.3g, at iteration %d"
                                          % (e, e / min(hist), min(hist), it))
            break
        if len(hist) > stall_window and (led is None or it >= led + 2):
            prev = hist[-1 - stall_window]
            change = abs(prev - e) / max(prev, 1e-300)
            if change < stall_tol:
                status = "stalled"
                reason = ("stalled: the relative amplitude residual %.4g changed by %.2g (< %.2g) over the last %d "
                          "iterations" % (e, change, stall_tol, stall_window))
                break
    if reason is None:
        reason = ("max_iterations: the residual %.4g still changed by more than %.2g per %d iterations after %d "
                  "iterations" % (hist[-1], stall_tol, stall_window, n_iter))
    return {"O": O, "P": P, "hist": hist, "steps": steps, "status": status, "reason": reason, "cy": cy, "cx": cx,
            "geometry": geo, "scale": scale}


def _disagreement(fa, fb, inner):
    """2 本の復元の相対差(整数画素の平行移動・位相の傾き・大域の位相・振幅の倍率をそろえてから)。"""
    from filters_freq import phase_correlation_fft  # noqa: PLC0415 — 位相相関は既存の op を使う
    a = fa[inner, inner]
    r = phase_correlation_fft(np.abs(a), np.abs(fb[inner, inner]))
    dr, dc = int(r["row_shift"]), int(r["col_shift"])
    b = np.roll(fb, (dr, dc), axis=(0, 1))[inner, inner]        # b = roll(a, d) のとき (dr, dc) = −d
    # 位相の 1 次の傾き(照明の k の全体のずれ = 物体のスペクトルの平行移動と区別できない)も除く:
    # a·b* の 4 倍に詰めた FFT の山の位置が傾きの周波数
    prod = a * np.conj(b)
    h, w = prod.shape
    F = np.abs(np.fft.fft2(prod, s=(4 * h, 4 * w)))
    ky, kx = np.unravel_index(int(np.argmax(F)), F.shape)
    fy = (ky if ky < 2 * h else ky - 4 * h) / (4.0 * h)
    fx = (kx if kx < 2 * w else kx - 4 * w) / (4.0 * w)
    yy, xx = np.mgrid[0:h, 0:w]
    b = b * np.exp(2j * np.pi * (fy * yy + fx * xx))
    c = np.vdot(b, a)
    if abs(c) == 0:
        return float("inf"), (dr, dc)
    b = b * (c / abs(c)) * (np.linalg.norm(a) / max(np.linalg.norm(b), 1e-300))
    return float(np.linalg.norm(a - b) / max(np.linalg.norm(a), 1e-300)), (dr, dc)


def fp_reconstruct(stack, upsample=None, n_iter=200, pupil_update=True, pupil_start=2, alpha=1.0, beta=1.0,
                   led_correction=False, led_start=3, stall_tol=1e-2, stall_window=10, agree_tol=AGREE_TOL,
                   starts=2, margin_px=None, intensity_correction=False, pupil_degree=4, on_fail="raise"):
    """低解像の像の組から高解像の振幅と位相を戻す(``table``、kind="fp_result")。収束しなければ拒否する。

    逐次の位相回復(Ou ら 2014 の EPRY、ePIE と同じ形): 照明の NA の小さい順に 1 枚ずつ、推定の低解像の場の
    振幅を測った振幅に置き換え、その差で物体のスペクトルを ``alpha`` 、瞳を ``beta`` の歩幅で直す
    (瞳は ``pupil_start`` 回目から、円の外は 0 に保つ)。

    * ``pupil_degree``(既定 4): 瞳の位相の更新を、円の上で直交化した 2〜4 次の多項式(12 個。デフォーカス・非点・
      コマ・球面などの低次の収差)へ射影し、振幅は 1 に保つ。``None`` は画素ごとに自由な EPRY(原論文の形)——
      ★自由な瞳は雑音を吸って残差が下がり続け、停留しない(32 画素・25 枚の合成で 200 回後も 10 回あたり 1 % 超)。

    * ``upsample``: 高解像の格子の倍率。None なら照明の NA が入り、画素が λ/(2 NA_syn) 以下になる最小の整数。
    * ``led_correction``: ``led_start`` 回目から、像ごとに瞳の中心を ±1 画素の 9 通りで試して残差の最小を取り
      (同点は丸めた値で比べ、候補の宣言順で先のもの)、続けて表の ``led_xyz_mm`` に LED アレイの幾何
      (ずれ x・y、回転、高さ)を最小二乗で当て、中心をその予測に置き直す(Sun ら 2016 の焼きなましを決定的な
      局所探索に替えたもの)。
    * ``intensity_correction``: 3 回目から像ごとの明るさの比を推定の平均に合わせる(LED の明るさが分からない
      実データ向け)。照明の NA が最小の像は基準として動かさない —— ★全部を動かすと、推定が明るくなれば測った像も
      明るくし直す正の帰還になり、実データで残差が 200 回で 2 万倍に発散した(瞳を多項式に射影したとき)。
    * 収束: 振幅の相対残差の不動点 **かつ** 初期値の違う 2 本(``starts=2``)が ``agree_tol`` 以内で一致。
      残差が下がらない・回数が尽きた・2 本が別の答えに着いた、のどれでも「収束しない」。
      ``on_fail="raise"``(既定)は :class:`FPNotConvergedError`(``MetricContractError``、``record`` に記録)、
      ``"record"`` は記録を返す(``converged=False``)。

    返り値: dict(kind="fp_result", converged, reason, n_iter, residual, residual_history,
    residual_history_starts, step_history(1 周ごとの物体のスペクトルの相対変化), start_disagreement,
    field_second_start, amplitude, phase, field, pupil, pupil_support, na_synthetic
    (= NA_obj + 使った照明の NA の最大、対角の LED を含む), na_synthetic_axis(x・y の方向余弦の最大で取った値 = 軸に
    沿った棒の分解を決める値), pixel_um, upsample, margin_px, led_centres, led_geometry, intensity_scale)。
    """
    op = "fp_reconstruct"
    if not isinstance(stack, dict) or stack.get("kind") != "fp_stack":
        raise ValueError("%s: expected an fp_stack table (from fp_capture or fp_stack_from_images)" % op)
    if on_fail not in ("raise", "record"):
        raise ValueError("%s: on_fail must be 'raise' or 'record', got %r" % (op, on_fail))
    try:
        imgs = np.asarray(stack["images"], np.float64)
        kx = np.asarray(stack["kx"], np.float64).ravel()
        ky = np.asarray(stack["ky"], np.float64).ravel()
        gain = (np.asarray(stack["exposure"], np.float64).ravel() * np.asarray(stack["led_brightness"], np.float64).ravel()
                * float(stack["photons"]))
        lam = float(stack["wavelength_um"])
        na = float(stack["na_obj"])
        dxl = float(stack["pixel_um"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("%s: the fp_stack table is incomplete (%s)" % (op, exc)) from None
    if imgs.ndim != 3 or imgs.shape[1] != imgs.shape[2] or imgs.shape[0] < 2:
        raise ValueError("%s: images must be (K >= 2, n, n), got %s" % (op, imgs.shape))
    K, n, _ = imgs.shape
    if kx.shape != (K,) or ky.shape != (K,) or gain.shape != (K,):
        raise ValueError("%s: kx, ky, exposure and led_brightness must have %d entries" % (op, K))
    if not (np.isfinite(imgs).all() and np.isfinite(kx).all() and np.isfinite(ky).all() and np.isfinite(gain).all()
            and (gain > 0).all() and lam > 0 and 0 < na < 1 and dxl > 0):
        raise ValueError("%s: the fp_stack table has non-finite or out-of-range values" % op)
    n_it = _int(n_iter, "n_iter", op, 1, MAX_ITER_CAP)
    p_start = _int(pupil_start, "pupil_start", op, 0, MAX_ITER_CAP)
    al = _num(alpha, "alpha", op, lo=0.0, hi=2.0)
    be = _num(beta, "beta", op, lo=0.0, hi=2.0)
    l_start = _int(led_start, "led_start", op, 0, MAX_ITER_CAP)
    s_tol = _num(stall_tol, "stall_tol", op, lo=0.0, hi=1.0)
    s_win = _int(stall_window, "stall_window", op, 1, 100)
    a_tol = _num(agree_tol, "agree_tol", op, lo=0.0, hi=2.0)
    n_starts = _int(starts, "starts", op, 1, 2)
    p_deg = None if pupil_degree is None else _int(pupil_degree, "pupil_degree", op, 2, 10)
    df = 1.0 / (n * dxl)
    na_ill = np.hypot(kx, ky) * lam
    na_syn = na + float(na_ill.max())
    if upsample is None:
        need_span = int(np.max(np.abs(np.concatenate([ky, kx])) / df)) + n // 2 + 2
        up = max(int(math.ceil(2.0 * need_span / n)), int(math.ceil(dxl / (lam / (2 * na_syn)) - 1e-9)), 1)
        if up > 16:
            raise ValueError("%s: the illumination NA %.3f needs upsample %d (> 16)" % (op, na_ill.max(), up))
    else:
        up = _int(upsample, "upsample", op, 1, 16)
    N = n * up
    sign = -1.0
    cy = np.round(sign * ky / df).astype(int)
    cx = np.round(sign * kx / df).astype(int)
    if (np.abs(cy) + n // 2 + 1 > N // 2).any() or (np.abs(cx) + n // 2 + 1 > N // 2).any():
        raise ValueError("%s: upsample %d is too small for the illumination NA %.3f" % (op, up, na_ill.max()))
    amp = np.sqrt(np.clip(imgs / gain[:, None, None], 0, None))
    mg = (int(math.ceil(2 * lam / (na * dxl))) if margin_px is None
          else _int(margin_px, "margin_px", op, 0, n // 2 - 2))
    if n - 2 * mg < 8:
        raise ValueError("%s: the images (%d px) are too small for the edge margin %d px" % (op, n, mg))
    inner = slice(mg, n - mg)
    P0, S = _pupil(n, (na / lam) / df, {})
    basis = _pupil_basis(S, p_deg) if (pupil_update and p_deg is not None) else None
    j0 = int(np.argmin(na_ill))
    a0 = np.kron(amp[j0], np.ones((up, up)))
    inits = [a0, np.full((N, N), float(np.mean(amp[j0])))][:n_starts]
    led = l_start if led_correction else None
    xyz = None
    if led_correction:
        if "led_xyz_mm" not in stack:
            raise ValueError("%s: led_correction needs led_xyz_mm in the stack (the nominal LED positions)" % op)
        xyz = np.asarray(stack["led_xyz_mm"], np.float64)
        if xyz.shape != (K, 3) or not np.isfinite(xyz).all():
            raise ValueError("%s: led_xyz_mm must be (%d, 3) finite" % (op, K))
    runs = []
    for k, o0 in enumerate(inits):
        O0 = _fft(o0.astype(np.complex128)) * (n * n) / (N * N)
        if k == 0:
            runs.append(_run(amp, (cy, cx), P0, S, O0, n_it, bool(pupil_update), p_start, al, be, led,
                             xyz, lam, df, sign, s_tol, s_win, inner, bool(intensity_correction), basis))
        else:
            # 2 本目は 1 本目が決めた LED の中心で走らせる(一意性の門は物体について問う。幾何の当てはめを 2 回やると、
            # 幾何の局所解の違いが物体の違いに見える)
            runs.append(_run(amp, (runs[0]["cy"], runs[0]["cx"]), P0, S, O0, n_it, bool(pupil_update), p_start, al,
                             be, None, None, lam, df, sign, s_tol, s_win, inner, bool(intensity_correction), basis))
    main = runs[0]
    field = _ifft(main["O"]) * (N * N) / (n * n)
    big_inner = slice(mg * up, N - mg * up)
    disagree, shift, field_b = None, None, None
    if len(runs) > 1:
        field_b = _ifft(runs[1]["O"]) * (N * N) / (n * n)
        disagree, shift = _disagreement(field, field_b, big_inner)
    stalled = all(r["status"] == "stalled" for r in runs)
    unique = disagree is None or disagree <= a_tol
    converged = stalled and unique
    if not stalled:
        reason = [r for r in runs if r["status"] != "stalled"][0]["reason"]
    elif not unique:
        reason = ("non-unique: two starts (upsampled bright-field / flat) reached different fixed points, relative "
                  "difference %.3f > agree_tol %.3f — the data do not pin the solution (too little spectral overlap?)"
                  % (disagree, a_tol))
    else:
        reason = main["reason"] + ("; two starts agree to %.3f" % disagree if disagree is not None else "")
    geo = main["geometry"]
    rec = {
        "kind": "fp_result", "op": op, "converged": bool(converged), "reason": reason,
        "n_iter": len(main["hist"]), "residual_history": [float(v) for v in main["hist"]],
        "residual": float(main["hist"][-1]) if main["hist"] else None,
        "residual_history_starts": [[float(v) for v in r["hist"]] for r in runs],
        "step_history": main["steps"],
        "start_disagreement": disagree, "start_shift_px": shift, "field_second_start": field_b,
        "amplitude": np.abs(field), "phase": np.angle(field), "field": field,
        "pupil": main["P"], "pupil_support": S,
        "na_synthetic": na_syn, "na_illumination_max": float(na_ill.max()), "na_obj": na,
        "na_synthetic_axis": na + float(max(np.abs(kx).max(), np.abs(ky).max()) * lam),
        "pixel_um": dxl / up, "upsample": up, "margin_px": mg * up,
        "led_centres": np.stack([main["cy"], main["cx"]], 1),
        "led_geometry": None if geo is None else
        {"offset_x_mm": float(geo[0]), "offset_y_mm": float(geo[1]),
         "rotation_deg": math.degrees(float(geo[2])), "height_error_mm": float(geo[3])},
        "intensity_scale": main["scale"],
    }
    if not converged and on_fail == "raise":
        raise FPNotConvergedError("%s: %s — no image is returned as converged" % (op, reason), rec)
    return rec


# --------------------------------------------------------------------------- #
# USAF の要素の読み取り
# --------------------------------------------------------------------------- #
def _profile_points(img, box, along_x, frac=0.6):
    r0, r1, c0, c1 = [float(v) for v in box]
    if along_x:
        L = r1 - r0
        a = int(round(r0 + (1 - frac) / 2 * L))
        prof = img[a:max(int(round(r1 - (1 - frac) / 2 * L)), a + 1), :].mean(axis=0)
        w, start = (c1 - c0) / 5.0, c0
    else:
        L = c1 - c0
        a = int(round(c0 + (1 - frac) / 2 * L))
        prof = img[:, a:max(int(round(c1 - (1 - frac) / 2 * L)), a + 1)].mean(axis=1)
        w, start = (r1 - r0) / 5.0, r0
    pos = np.arange(prof.size, dtype=np.float64) + 0.5          # 画素 i は [i, i+1) を覆い、中心は i + 0.5
    bars = np.interp([start + (2 * b + 0.5) * w for b in range(3)], pos, prof)
    gaps = np.interp([start + (2 * b + 1.5) * w for b in range(2)], pos, prof)
    return bars, gaps


def fp_element_contrast(image, elements, min_modulation=0.1, polarity="auto"):
    """USAF の要素ごとに 3 本の棒の変調を測り、どこまで分解したかを読む(``table``)。

    ``elements`` は ``fp_usaf_target`` の返り値(またはその ``elements``)か、同じ形の箱
    (``vertical_bars_box`` / ``horizontal_bars_box`` = (行0, 行1, 列0, 列1))のリスト。実画像なら箱を手で置く。
    向きごとに、棒の長さの中央 60 % を平均した断面を、3 本の棒の中心と 2 つの隙間の中心で読む。
    変調 = min(隙間 − 両隣の棒)/(5 点の平均 × 2)(暗い棒なら隙間が明るい側。``polarity="auto"`` は隙間の平均と
    棒の平均の大小で決める)。**2 つの隙間がどちらも両隣の棒から立っていないと負になる**(1 つにぼけた塊は
    分解と数えない)。両方の向きで ``min_modulation`` 以上なら分解。``last_resolved`` は並びの先頭から続けて
    分解した最後の要素。
    """
    op = "fp_element_contrast"
    img = _real2d(image, "image", op, min_side=4)
    m_min = _num(min_modulation, "min_modulation", op, lo=0.0, hi=1.0)
    if polarity not in ("auto", "dark_bars", "bright_bars"):
        raise ValueError("%s: polarity must be 'auto', 'dark_bars' or 'bright_bars', got %r" % (op, polarity))
    if isinstance(elements, dict):
        elements = elements.get("elements")
    if not isinstance(elements, (list, tuple)) or not elements:
        raise ValueError("%s: elements must be a non-empty list of element records (or an fp_target)" % op)
    rows = []
    for k, e in enumerate(elements):
        if not isinstance(e, dict) or "vertical_bars_box" not in e or "horizontal_bars_box" not in e:
            raise ValueError("%s: element %d needs vertical_bars_box and horizontal_bars_box" % (op, k))
        rec = {"group": e.get("group"), "element": e.get("element"), "period_um": e.get("period_um")}
        ok_all = True
        for key, along_x in (("vertical_bars_box", True), ("horizontal_bars_box", False)):
            try:
                r0, r1, c0, c1 = [float(v) for v in e[key]]
            except (TypeError, ValueError):
                raise ValueError("%s: element %d %s must be 4 numbers" % (op, k, key)) from None
            if not (0 <= r0 < r1 <= img.shape[0] and 0 <= c0 < c1 <= img.shape[1]):
                raise ValueError("%s: element %d %s %s is outside the image %s" % (op, k, key, e[key], img.shape))
            if (c1 - c0 if along_x else r1 - r0) < 5:
                raise ValueError("%s: element %d %s is narrower than 5 pixels (one pixel per bar or gap)" % (op, k, key))
            bars, gaps = _profile_points(img, (r0, r1, c0, c1), along_x)
            dark = (float(np.mean(gaps)) > float(np.mean(bars))) if polarity == "auto" else polarity == "dark_bars"
            if dark:
                depth = min(float(gaps[i] - max(bars[i], bars[i + 1])) for i in range(2))
            else:
                depth = min(float(min(bars[i], bars[i + 1]) - gaps[i]) for i in range(2))
            denom = 2.0 * float(np.mean(np.abs(np.concatenate([bars, gaps]))))
            mod = depth / denom if denom > 0 else 0.0
            name = "vertical" if along_x else "horizontal"
            rec[name + "_modulation"] = mod
            rec[name + "_resolved"] = bool(mod >= m_min)
            ok_all = ok_all and mod >= m_min
        rec["resolved"] = bool(ok_all)
        rows.append(rec)
    last = None
    for r in rows:
        if not r["resolved"]:
            break
        last = r
    return {"kind": "fp_element_contrast", "elements": rows, "min_modulation": m_min,
            "last_resolved": None if last is None else {"group": last["group"], "element": last["element"],
                                                         "period_um": last["period_um"]},
            "n_resolved": int(sum(r["resolved"] for r in rows))}

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""moirealign — ピッチの僅かに違う 2 枚の格子のモアレで、マスクとウェハのずれを nm 級に読む(位置合わせ)。

動機(2026-10-15): Fullseye のモアレは印刷の網点(``printpath.halftone_moire_period``)だけで、リソグラフィ /
ナノインプリントの**位置合わせ**に使うモアレ —— マスク側のピッチ p_m とウェハ側のピッチ p_w を僅かに変えて重ね、
ずれを M 倍に拡大した縞の**位相**から読む方法 —— が無かった。ここはその層。

内容(8 op):
  設計    `moire_magnification`(縞の周期・拡大率 M・捕捉範囲。周期の閉形式は ``printpath.halftone_moire_period``
          を呼ぶ = 網点と同じ差の周波数ベクトル)/ `moire_talbot_gap`(近接ギャップの Talbot 効果: マスクの格子の像が
          ギャップの先でどれだけ・どちらの符号で残るか。伝搬は ``optics.angular_spectrum_propagate``)
  合成    `moire_overlay_image`(重ねた格子をカメラで撮った像: 単一の対 / 差動の 2 対 / 2 次元の 4 象限、
          ぼけ(ガウスの MTF)と画素の積分(sinc)は閉形式、ギャップ・照明むら・雑音・マーク全体の流れ)
  読み取り `moire_phase`(縞の位相をロックイン = 既知の周波数での複素復調、または Takeda の FFT 法 = ``complexops.cx_fft``
          の側帯域 → ``complexops.phase_unwrap``)/ `moire_phase_to_shift`(位相 → ずれ、粗い推定で次数を決めるのは
          ``fringe.absolute_phase``)/ `moire_differential_shift`(逆向きのピッチ差の 2 対で、像の流れ・照明などの
          共通の誤差を消す)/ `moire_mark_read`(マーク 1 枚を測定像と基準像から読む: 単一・差動・4 象限)
  限界    `moire_phase_crlb`(白色雑音 σ・縞の振幅・画素数からの位相とずれの下限、Rife & Boorstyn 1974 の形)

拡大率の規約(★大事): 縞の周期は P = p_m p_w / |p_w − p_m|。どちらの格子が動くかで拡大率が違う:
  ウェハ(p_w)が δ 動く → 縞は M_w·δ 動く、M_w = p_m / |p_w − p_m|
  マスク(p_m)が δ 動く → 縞は M_m·δ 動く、M_m = p_w / |p_w − p_m|
2 つは p の比(1 + Δp/p)しか違わないが、門で区別できる大きさ(p 2.00 / 2.04 µm で 2 %)。
**どちらの式も「ずれ 1 周期 = 縞 1 周期」**: δ が動いた格子のピッチ 1 つ分を超えると縞は元に戻り、読みは折り返す
(印刷の版ずれと同じ不定性)。差動の 2 対では捕捉範囲が p_m p_w / (p_m + p_w)(約半分)に縮む。

真値(外部): 縞の周期と拡大率の閉形式、白色雑音の下の位相推定の下限(Rife & Boorstyn 1974)、Talbot 長 2p²/λ
(Lord Rayleigh 1881、半分の長さで像が半周期ずれる)。
来歴: Takeda, Ina & Kobayashi, JOSA 72, 156 (1982)(FFT による縞解析)/ Li, Wu & Chou, Nano Lett. 6, 2626 (2006)
(ナノインプリントのモアレ位置合わせ、20 nm 未満)/ Zhu, Hu, Yu et al., Opt. Express 21, 3463 (2013)(4 象限の格子と
位相復調、近接露光)/ Moon & Smith, J. Vac. Sci. Technol. B 23, 2607 (2005)(ISPI、空間位相で 1 nm 未満の検出能)/
Patorski, *Handbook of the Moiré Fringe Technique* (1993) / Amidror, *The Theory of the Moiré Phenomenon* (2009)。
規約: 長さは µm、ずれは nm、位相は rad、像の座標は画素(x = 列、y = 行)、画素は物体側の大きさ pixel_um。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "moire_magnification", "moire_talbot_gap", "moire_overlay_image", "moire_phase",
    "moire_phase_to_shift", "moire_differential_shift", "moire_mark_read", "moire_phase_crlb",
]

#: マークの並び(`moire_overlay_image` / `moire_mark_read`)。
MOIRE_LAYOUTS = ("single", "differential", "quad")


# --------------------------------------------------------------------------- #
# 入力の検査                                                                    #
# --------------------------------------------------------------------------- #
def _num(v, name, op):
    """optics 族の契約: 文字列と bool は数として通さない(float('50') が通ると未パースの設定値が長さになる)。"""
    if isinstance(v, (str, bytes, bool, np.bool_)):
        raise ValueError("%s: %s must be a number, not %s %r" % (op, name, type(v).__name__, v))


def _pos(v, name, op):
    _num(v, name, op)
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a finite number > 0, got %r" % (op, name, v)) from None
    if not (math.isfinite(x) and x > 0.0):
        raise ValueError("%s: %s must be finite and > 0, got %r" % (op, name, v))
    return x


def _nonneg(v, name, op):
    _num(v, name, op)
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a finite number >= 0, got %r" % (op, name, v)) from None
    if not (math.isfinite(x) and x >= 0.0):
        raise ValueError("%s: %s must be finite and >= 0, got %r" % (op, name, v))
    return x


def _finite(v, name, op):
    _num(v, name, op)
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a finite number, got %r" % (op, name, v)) from None
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    return x


def _moving(moving, op):
    if moving not in ("wafer", "mask"):
        raise ValueError("%s: moving must be 'wafer' or 'mask', got %r" % (op, moving))
    return moving


def _pitches(p_mask_um, p_wafer_um, op):
    pm, pw = _pos(p_mask_um, "p_mask_um", op), _pos(p_wafer_um, "p_wafer_um", op)
    if abs(pw - pm) <= 1e-12 * max(pm, pw):
        raise ValueError("%s: p_mask_um and p_wafer_um are equal (%.6g µm) — two gratings of the same pitch "
                         "make no beat, so there is no moiré to read" % (op, pm))
    return pm, pw


def _beat(pm, pw):
    """符号つきの縞の周波数 f = 1/p_m − 1/p_w(1/µm)。"""
    return 1.0 / pm - 1.0 / pw


def _phase_gain(pm, pw, moving):
    """ずれ δ(µm)に対する、正の周波数 |f| で復調した位相の傾き dφ/dδ(rad/µm)。

    重ねた像の差の周波数の項は exp(i2π(f x − x_m/p_m + x_w/p_w))(x_m, x_w は各格子の位置)。|f| で復調すると、
    f < 0 の対は複素共役で読む。だから dφ/dx_w = sgn(f)·2π/p_w、dφ/dx_m = −sgn(f)·2π/p_m。
    """
    s = 1.0 if _beat(pm, pw) > 0 else -1.0
    return s * 2.0 * math.pi / pw if moving == "wafer" else -s * 2.0 * math.pi / pm


def _wrap(a):
    return (np.asarray(a, dtype=np.float64) + np.pi) % (2.0 * np.pi) - np.pi


# --------------------------------------------------------------------------- #
# 1. 設計                                                                       #
# --------------------------------------------------------------------------- #
def moire_magnification(p_mask_um=2.0, p_wafer_um=2.04, moving="wafer", twist_mrad=0.0):
    """モアレの縞の周期・向きと、ずれの拡大率 M・捕捉範囲(閉形式)。

    縞の周期 P = p_m p_w / |p_w − p_m|(格子を回すと周波数ベクトルの差の大きさの逆数 —— ``printpath`` の網点の
    モアレと同じ式なので、そちらを呼んで照合している)。拡大率はどちらの格子が動くかで違い、ウェハが動くなら
    M = p_m / |Δp|、マスクが動くなら M = p_w / |Δp|。捕捉範囲(読みが折り返すずれ)は動く格子のピッチ 1 つ分、
    逆向きのピッチ差の 2 対を使う差動では p_m p_w / (p_m + p_w)。

    twist_mrad は 2 枚の格子の相対回転で、縞は大きく傾く(回転も拡大される)。0 以外では P は縮む。

    返り値: dict(moire_period_um, fringe_angle_deg, magnification, magnification_wafer, magnification_mask,
    beat_frequency_per_um(符号つき)、fringe_direction(+1 / −1: ずれが正のとき縞が +x へ動くか)、
    capture_range_um, capture_range_differential_um)。
    **Raises** ValueError: ピッチが正でない・2 枚が同じピッチ(縞が無い)・moving の綴り違い。
    """
    op = "moire_magnification"
    pm, pw = _pitches(p_mask_um, p_wafer_um, op)
    mv = _moving(moving, op)
    tw = _finite(twist_mrad, "twist_mrad", op)
    import printpath                                       # noqa: PLC0415
    # 網点の式は lpi(25.4 mm あたりの線数)と画素で受ける: 画素 1 µm と置けば周期は µm で返る。
    beat = printpath.halftone_moire_period(lpi_a=25400.0 / pm, angle_a_deg=0.0,
                                           lpi_b=25400.0 / pw, angle_b_deg=math.degrees(tw * 1e-3), pixel_um=1.0)
    period = float(beat["period_px"][0])
    f = _beat(pm, pw)
    dp = abs(pw - pm)
    mw, mm = pm / dp, pw / dp
    g = _phase_gain(pm, pw, mv)
    # 縞の位置 x_f は位相 φ = 2π|f| x_f の逆向き(復調の位相が増えると縞は −x へ動く)。
    direction = -1 if g > 0 else 1
    return {"moire_period_um": period,
            "fringe_angle_deg": float(beat["angle_deg"][0]),
            "magnification": mw if mv == "wafer" else mm,
            "magnification_wafer": mw, "magnification_mask": mm,
            "beat_frequency_per_um": f,
            "fringe_direction": direction,
            "capture_range_um": pw if mv == "wafer" else pm,
            "capture_range_differential_um": pm * pw / (pm + pw)}


def _binary_coeffs(n_harm, duty):
    """0/1 の格子(デューティ duty)のフーリエ係数 c_n、n = −H..H(中心が 0 の対称な線)。"""
    n = np.arange(-n_harm, n_harm + 1)
    c = np.empty(n.shape, dtype=np.complex128)
    nz = n != 0
    c[nz] = np.sin(np.pi * n[nz] * duty) / (np.pi * n[nz])
    c[~nz] = duty
    return n, c


def _sine_coeffs(n_harm):
    n = np.arange(-n_harm, n_harm + 1)
    c = np.zeros(n.shape, dtype=np.complex128)
    c[n == 0] = 0.5
    c[np.abs(n) == 1] = 0.25
    return n, c


def _talbot_coeffs(p_um, wavelength_um, gap_um, duty, n_harm, samples, op):
    """0/1 のマスクを通った光の強度を、ギャップ gap_um の先で 1 周期ぶん計算し、フーリエ係数を返す。

    伝搬は ``optics.angular_spectrum_propagate``(厳密なスカラー回折)。1 周期を周期境界で解くので、格子が
    無限に続く場合の厳密解になる(端の回折は入らない)。
    """
    import optics                                          # noqa: PLC0415
    if samples < 4 * n_harm + 4:
        raise ValueError("%s: samples (%d) must be at least 4·n_harmonics + 4" % (op, samples))
    x = (np.arange(samples) + 0.5) / samples              # 1 周期の中の位置(0..1)
    d = np.minimum(x, 1.0 - x)                             # 線の中心(x = 0)からの距離
    t = (d < duty / 2.0).astype(np.float64)
    field = np.vstack([t, t]).astype(np.complex128)        # 2 行(op の最小の形)、行の方向には一様
    u = optics.angular_spectrum_propagate(field, wavelength_um=wavelength_um, distance_um=gap_um,
                                          pixel_pitch_um=p_um / samples)
    inten = np.abs(u[0]) ** 2
    spec = np.fft.fft(inten) / samples
    # 標本点は x_k = (k + 0.5)/N なので、x = 0 を原点にする位相を戻す。
    n = np.arange(-n_harm, n_harm + 1)
    c = spec[n % samples] * np.exp(-1j * np.pi * n / samples)
    return n, c


def moire_talbot_gap(p_mask_um=2.0, wavelength_um=0.55, gap_um=10.0, duty=0.5, samples=512):
    """近接ギャップの Talbot 効果: マスクの格子の像が、ギャップの先でどれだけ・どちらの符号で残るか。

    近接露光ではマスクとウェハの間にギャップ g があり、マスクの格子を通った光はウェハに届くまでに回折する。
    縞の振幅はマスクの像の基本波(1/p の成分)に比例するので、その振幅の gap = 0 に対する比を返す。
    対称な格子ではこの比は**実数**で、ギャップによって符号が反転する(反転 = 縞が半周期ずれる = 読みが p/2 跳ぶ)。
    Talbot 長 z_T = 2p²/λ(近軸)で像は元に戻り、z_T/2 で半周期ずれた像になる。
    伝搬は ``optics.angular_spectrum_propagate``(近軸近似を使わない)なので、z_T は近軸の値からわずかにずれる。

    返り値: dict(contrast_ratio(符号つき)、phase_rad(0 か π)、talbot_length_um(近軸 2p²/λ)、
    fundamental(複素の基本波係数)、fundamental_at_contact)。
    **Raises** ValueError: 正でないピッチ・波長、負のギャップ、duty が (0, 1) の外、p < λ(伝搬する回折次数が無い)。
    """
    op = "moire_talbot_gap"
    p = _pos(p_mask_um, "p_mask_um", op)
    lam = _pos(wavelength_um, "wavelength_um", op)
    g = _nonneg(gap_um, "gap_um", op)
    du = _finite(duty, "duty", op)
    if not 0.0 < du < 1.0:
        raise ValueError("%s: duty must be in (0, 1), got %r" % (op, duty))
    if p <= lam:
        raise ValueError("%s: p_mask_um (%.4g) must exceed wavelength_um (%.4g) — otherwise no diffraction order "
                         "propagates and the grating image is lost within a wavelength" % (op, p, lam))
    ns = int(samples)
    _, c0 = _talbot_coeffs(p, lam, 0.0, du, 1, ns, op)
    _, cg = _talbot_coeffs(p, lam, g, du, 1, ns, op)
    f0, fg = c0[2], cg[2]                                  # n = +1
    ratio = complex(fg / f0)
    return {"contrast_ratio": float(ratio.real),
            "phase_rad": float(abs(math.atan2(ratio.imag, ratio.real))),
            "imag_residual": float(ratio.imag),
            "talbot_length_um": 2.0 * p * p / lam,
            "fundamental": complex(fg), "fundamental_at_contact": complex(f0)}


# --------------------------------------------------------------------------- #
# 2. 合成                                                                       #
# --------------------------------------------------------------------------- #
def _regions(shape, layout):
    """マークの区画: [(名前, (r0, r1, c0, c1), 軸, 対)]。軸 1 = 縞が x に並ぶ(線は縦)、対 'A' = (p_m, p_w)、'B' = 入れ替え。"""
    h, w = shape
    if layout == "single":
        return [("A_x", (0, h, 0, w), 1, "A")]
    if layout == "differential":
        return [("A_x", (0, h // 2, 0, w), 1, "A"), ("B_x", (h // 2, h, 0, w), 1, "B")]
    return [("A_x", (0, h // 2, 0, w // 2), 1, "A"), ("B_x", (0, h // 2, w // 2, w), 1, "B"),
            ("A_y", (h // 2, h, 0, w // 2), 0, "A"), ("B_y", (h // 2, h, w // 2, w), 0, "B")]


def _profile(coords_px, pixel_um, pm, cm, nm_, pw, cw, nw, xm_um, xw_um, drift_um, sigma_um, min_term):
    """1 次元の像(画素の中心で積分した値)を閉形式で: Σ_n Σ_m a_n b_m H(f) exp(i2π(f(x − s) − n x_m/p_m − m x_w/p_w))。"""
    fn = nm_[:, None] / pm + nw[None, :] / pw              # (Nn, Nm) の周波数 1/µm
    coef = cm[:, None] * cw[None, :]
    mtf = np.exp(-2.0 * np.pi ** 2 * sigma_um ** 2 * fn ** 2) * np.sinc(fn * pixel_um)
    ph = np.exp(-2j * np.pi * (nm_[:, None] * xm_um / pm + nw[None, :] * xw_um / pw))
    amp = coef * mtf * ph
    keep = np.abs(amp) > min_term
    f = fn[keep]
    a = amp[keep]
    x = coords_px * pixel_um - drift_um
    prof = np.real(np.exp(2j * np.pi * np.outer(x, f)) @ a)
    return prof, f, np.abs(coef[keep] * np.sinc(fn[keep] * pixel_um) * np.exp(-2.0 * np.pi ** 2 * sigma_um ** 2 * fn[keep] ** 2))


def _pair(xy, idx):
    if np.ndim(xy) == 0:
        v = float(xy)
        return v if idx == 0 else 0.0
    a = np.asarray(xy, dtype=np.float64).ravel()
    if a.size != 2:
        raise ValueError("expected a scalar or a pair (x, y), got %r" % (xy,))
    return float(a[idx])


def moire_overlay_image(shape=(256, 1024), pixel_um=0.5, p_mask_um=2.0, p_wafer_um=2.04, shift_nm=0.0,
                        layout="single", profile="square", duty=0.5, blur_sigma_um=1.5, gap_um=0.0,
                        wavelength_um=None, drift_nm=0.0, illum_gradient=0.0, noise_sigma=0.0, seed=0,
                        moving="wafer", n_harmonics=15, allow_aliasing=False, with_mask=True):
    """重ねた 2 枚の格子をカメラで撮った像(位置合わせのマーク)を合成する。

    像 = [マークの強度(マスクの格子の像 × ウェハの格子の反射率)] をガウスのぼけ(MTF exp(−2π²σ²f²))と
    画素の積分(sinc)で撮ったもの。格子はフーリエ級数で持つので、ぼけと画素は**閉形式**(打ち切りの誤差は
    n_harmonics と項の大きさの床 1e-12 だけ)。ギャップ gap_um > 0 ではマスクの像を ``moire_talbot_gap`` と同じく
    ``optics.angular_spectrum_propagate`` で伝搬する(0/1 の格子だけ、波長 wavelength_um が要る —— ギャップが 0 なら使わない)。ぼけが格子のピッチを潰すので、
    像に残るのは差の周波数の縞(モアレ)だけになる —— これが位置合わせのマークの要点。

    layout:
      ``"single"``       全面が 1 対(マスク p_m、ウェハ p_w)、線は縦、x のずれを読む。
      ``"differential"`` 上半分 = 対 A(p_m, p_w)、下半分 = 対 B(ピッチを入れ替え)。ずれで 2 つの縞は逆に動き、
                         マーク全体の流れ(drift_nm)では同じ向きに動く。
      ``"quad"``         4 象限: 左上 A_x、右上 B_x、左下 A_y、右下 B_y(下は線が横で y のずれ)。
                         shift_nm と drift_nm は (x, y) の組でもよい。
    ``with_mask=False`` はマスクを外してウェハの格子だけを撮った**直接の像**(比べ手の相互相関に使う。ピッチ 2 µm の
    格子はぼけで消えて一様な灰色になる —— 直接の像ではずれが見えない、を示す)。縞の周期の検査はしない。
    shift_nm は moving(既定 ``"wafer"``)の格子のずれ。drift_nm はマーク全体(2 枚とも)がカメラに対して動いた量。
    illum_gradient は視野の端から端までの照明の傾き(相対、x と y に同じ量)、noise_sigma は加える白色ガウス雑音の
    標準偏差(強度の単位。0/1 の格子 2 枚で平均は 0.25)。

    **Raises** ValueError: 同じピッチ、縞の周期が 2 画素未満(ナイキスト超え)、区画に縞が 1 周期も入らない、
    ぼけで消えきらない格子の周波数がナイキストを超える(``allow_aliasing=True`` で許す —— 実際のカメラでは
    折り返して縞に混ざる)、ギャップがあるのに profile が ``"sine"``、綴り違い、形が小さすぎる。
    """
    op = "moire_overlay_image"
    try:
        h, w = (int(shape[0]), int(shape[1]))
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s: shape must be (rows, cols), got %r" % (op, shape)) from None
    if h < 8 or w < 8 or h * w > 16_777_216:
        raise ValueError("%s: shape must be at least 8x8 and at most 16.7 M pixels, got %r" % (op, shape))
    if layout not in MOIRE_LAYOUTS:
        raise ValueError("%s: layout must be one of %s, got %r" % (op, MOIRE_LAYOUTS, layout))
    if profile not in ("square", "sine"):
        raise ValueError("%s: profile must be 'square' or 'sine', got %r" % (op, profile))
    px = _pos(pixel_um, "pixel_um", op)
    if with_mask:
        pm, pw = _pitches(p_mask_um, p_wafer_um, op)
    else:
        pm, pw = _pos(p_mask_um, "p_mask_um", op), _pos(p_wafer_um, "p_wafer_um", op)
    mv = _moving(moving, op)
    sig = _nonneg(blur_sigma_um, "blur_sigma_um", op)
    gap = _nonneg(gap_um, "gap_um", op)
    if gap > 0.0 and wavelength_um is None:
        raise ValueError("%s: gap_um > 0 needs wavelength_um (the diffraction across the gap depends on it)" % op)
    lam = None if wavelength_um is None else _pos(wavelength_um, "wavelength_um", op)
    du = _finite(duty, "duty", op)
    if not 0.0 < du < 1.0:
        raise ValueError("%s: duty must be in (0, 1), got %r" % (op, duty))
    nsig = _nonneg(noise_sigma, "noise_sigma", op)
    grad = _finite(illum_gradient, "illum_gradient", op)
    if abs(grad) >= 2.0:
        raise ValueError("%s: |illum_gradient| must be < 2 (the illumination would go negative)" % op)
    H = int(n_harmonics)
    if not 1 <= H <= 64:
        raise ValueError("%s: n_harmonics must be in 1..64, got %r" % (op, n_harmonics))
    if gap > 0.0 and profile == "sine":
        raise ValueError("%s: gap_um > 0 needs profile='square' (the gap is modelled as diffraction of a 0/1 mask)" % op)
    for nm_name, v in (("shift_nm", shift_nm), ("drift_nm", drift_nm)):
        for i in (0, 1):
            try:
                _finite(_pair(v, i), nm_name, op)
            except ValueError as exc:
                raise ValueError("%s: %s" % (op, exc)) from None
    period_px = 1.0 / abs(_beat(pm, pw)) / px if with_mask else 0.0
    if with_mask and period_px < 2.0:
        raise ValueError("%s: the moiré period is %.3g px (< 2 px, beyond Nyquist) — use a smaller pitch difference "
                         "or a smaller pixel" % (op, period_px))
    regs = _regions((h, w), layout)
    for name, (r0, r1, c0, c1), ax, _ in regs:
        span = (c1 - c0) if ax == 1 else (r1 - r0)
        if with_mask and span < period_px:
            raise ValueError("%s: region %s spans %d px, less than one moiré period (%.1f px)" % (op, name, span, period_px))
    if profile == "square":
        nb, cb = _binary_coeffs(H, du)
    else:
        nb, cb = _sine_coeffs(H)
    coeffs = {}
    for pair in ("A", "B"):
        p_m, p_w = (pm, pw) if pair == "A" else (pw, pm)
        if not with_mask:
            nmk, cmk = np.array([0]), np.array([1.0 + 0j])
        elif gap > 0.0:
            if p_m <= lam:
                raise ValueError("%s: the mask pitch (%.4g µm) must exceed the wavelength for a gap model" % (op, p_m))
            nmk, cmk = _talbot_coeffs(p_m, lam, gap, du, H, max(512, 8 * H + 8), op)
        else:
            nmk, cmk = nb, cb
        coeffs[pair] = (p_m, cmk, nmk, p_w, cb, nb)
    img = np.zeros((h, w), dtype=np.float64)
    nyq = 0.5 / px
    for _name, (r0, r1, c0, c1), ax, pair in regs:
        p_m, cmk, nmk, p_w, cwk, nwk = coeffs[pair]
        k = 0 if ax == 1 else 1
        sh = _pair(shift_nm, k) * 1e-3
        dr = _pair(drift_nm, k) * 1e-3
        xm, xw = (0.0, sh) if mv == "wafer" else (sh, 0.0)
        coords = np.arange(c0, c1) if ax == 1 else np.arange(r0, r1)
        prof, f, mag = _profile(coords.astype(np.float64), px, p_m, cmk, nmk, p_w, cwk, nwk, xm, xw, dr, sig, 1e-12)
        if not allow_aliasing:
            over = np.abs(f) > nyq
            if over.any() and float(mag[over].max()) > 1e-4:
                raise ValueError("%s: a grating frequency of %.3g /µm survives the blur with amplitude %.2e above the "
                                 "Nyquist frequency %.3g /µm — the camera would alias it into the fringes. Increase "
                                 "blur_sigma_um or reduce pixel_um (or pass allow_aliasing=True)"
                                 % (op, float(np.abs(f[over][np.argmax(mag[over])])), float(mag[over].max()), nyq))
        if ax == 1:
            img[r0:r1, c0:c1] = prof[None, :]
        else:
            img[r0:r1, c0:c1] = prof[:, None]
    if grad != 0.0:
        yy, xx = np.mgrid[0:h, 0:w]
        img *= 1.0 + grad * ((xx + 0.5) / w - 0.5) + grad * ((yy + 0.5) / h - 0.5)
    if nsig > 0.0:
        img = img + np.random.default_rng(int(seed)).normal(0.0, nsig, img.shape)
    return img


# --------------------------------------------------------------------------- #
# 3. 読み取り                                                                   #
# --------------------------------------------------------------------------- #
def _image(a, op, name="image"):
    v = np.asarray(a, dtype=np.float64)
    if v.ndim != 2 or v.shape[0] < 2 or v.shape[1] < 2:
        raise ValueError("%s: %s must be a 2-D array, got shape %r" % (op, name, np.shape(a)))
    if not np.isfinite(v).all():
        raise ValueError("%s: %s contains NaN or Inf" % (op, name))
    return v


def moire_phase(image, period_px=None, axis=1, region=None, window="hann", method="lockin"):
    """縞の位相(像の原点 x = 0 を基準)、振幅、縞の本数を読む。

    ``method="lockin"``: 区画を縞に沿って平均した 1 次元の輪郭に、既知の周期 period_px の (1, cos, sin) を窓の重みで
    最小二乗に当てる(複素復調 Σ w(x) p(x) e^{−i2πx/P} と同じ量を、縞の本数が整数でないときの負の周波数の漏れまで
    含めて解いたもの。正弦 1 本 + 直流なら厳密)。窓 ``"hann"`` は照明むら・高調波の漏れを抑えるが、雑音の分散は
    一様窓の約 1.5 倍(``moire_phase_crlb`` に同じ係数)。``window="none"`` は白色雑音だけなら最良。
    ``method="fft"``: Takeda ら(1982)の FFT 法 —— ``complexops.cx_fft`` の側帯域だけを残して逆変換し、位相の地図を
    ``complexops.phase_unwrap`` で繋ぐ。地図の傾きから周期を測り直す(``period_fit_px``、倍率や回転の誤差が見える)。
    period_px を省くと輪郭の FFT の山を放物線で補間して推定する(``period_estimated`` = True)。

    region = (r0, r1, c0, c1)(省略で全面)、axis = 1 は縞が x に並ぶ(線は縦)、0 は y に並ぶ。
    返り値: dict(phase_rad(−π..π)、amplitude(縞の余弦の振幅)、mean、n_fringes、period_px、period_estimated、
    fft のときは period_fit_px と phase_map も)。
    **Raises** ValueError: 2 次元でない・NaN/Inf、period_px < 2(ナイキスト超え)、区画に縞が 1 周期未満、
    区画が空、綴り違い。
    """
    op = "moire_phase"
    img = _image(image, op)
    if axis not in (0, 1):
        raise ValueError("%s: axis must be 0 or 1, got %r" % (op, axis))
    if window not in ("hann", "none"):
        raise ValueError("%s: window must be 'hann' or 'none', got %r" % (op, window))
    if method not in ("lockin", "fft"):
        raise ValueError("%s: method must be 'lockin' or 'fft', got %r" % (op, method))
    if region is None:
        r0, r1, c0, c1 = 0, img.shape[0], 0, img.shape[1]
    else:
        try:
            r0, r1, c0, c1 = (int(v) for v in region)
        except (TypeError, ValueError):
            raise ValueError("%s: region must be (r0, r1, c0, c1), got %r" % (op, region)) from None
        if not (0 <= r0 < r1 <= img.shape[0] and 0 <= c0 < c1 <= img.shape[1]):
            raise ValueError("%s: region %r is empty or outside the image %r" % (op, region, img.shape))
    sub = img[r0:r1, c0:c1]
    prof = sub.mean(axis=0) if axis == 1 else sub.mean(axis=1)
    origin = c0 if axis == 1 else r0
    n = prof.size
    if n < 4:
        raise ValueError("%s: the region is %d px long along the fringes — too short to read a phase" % (op, n))
    estimated = period_px is None
    if estimated:
        q = prof - prof.mean()
        q = q * np.hanning(n)
        pad = 8 * n
        spec = np.abs(np.fft.rfft(q, pad))
        spec[0] = 0.0
        k = int(np.argmax(spec[1:-1])) + 1
        a, b, c = np.log(spec[k - 1] + 1e-300), np.log(spec[k] + 1e-300), np.log(spec[k + 1] + 1e-300)
        den = a - 2 * b + c
        dk = 0.5 * (a - c) / den if den != 0 else 0.0
        P = pad / (k + dk)
    else:
        P = _finite(period_px, "period_px", op)
    if P < 2.0:
        raise ValueError("%s: period_px = %.4g is below 2 px (beyond Nyquist) — the fringe cannot be sampled" % (op, P))
    nf = n / P
    if nf < 1.0:
        raise ValueError("%s: the region holds %.3g fringe periods (< 1) — the phase of less than one period is not "
                         "separable from the background" % (op, nf))
    x = origin + np.arange(n, dtype=np.float64)
    wv = np.hanning(n + 2)[1:-1] if window == "hann" else np.ones(n)
    mean = float(np.sum(wv * prof) / np.sum(wv))
    out = {"mean": mean, "n_fringes": float(nf), "period_px": float(P), "period_estimated": bool(estimated),
           "method": method}
    if method == "lockin":
        # 既知の周波数の (1, cos, sin) を窓の重みで最小二乗に当てる = 複素復調の、負の周波数の像
        # (縞の本数が整数でないときに漏れて位相を引っぱる)まで含めて解いたもの。正弦 1 本 + 直流なら厳密。
        th = 2.0 * np.pi * x / P
        A = np.stack([np.ones(n), np.cos(th), np.sin(th)], axis=1)
        sw = np.sqrt(wv)
        coef, *_ = np.linalg.lstsq(A * sw[:, None], prof * sw, rcond=None)
        a, b = float(coef[1]), float(coef[2])
        out["phase_rad"] = float(math.atan2(-b, a))       # A cos(θ + φ) = A cosφ cosθ − A sinφ sinθ
        out["amplitude"] = float(math.hypot(a, b))
        out["mean"] = float(coef[0])
        return out
    import complexops                                      # noqa: PLC0415
    rows = sub if axis == 1 else sub.T                     # 縞は列方向に並ぶ形にそろえる
    spec = complexops.cx_fft(rows - rows.mean())
    hh, ww = spec.shape
    fx = (np.arange(ww) - ww // 2) / ww                    # cycles/px(cx_fft は中心が DC)
    fy = (np.arange(hh) - hh // 2) / hh
    f0 = 1.0 / P
    keep = (np.abs(fx[None, :] - f0) < 0.5 * f0) & (np.abs(fy[:, None]) < 0.5 * f0)
    if not keep.any():
        raise ValueError("%s: the side band around %.4g cycles/px holds no frequency bin" % (op, f0))
    analytic = np.fft.ifft2(np.fft.ifftshift(spec * keep))
    wrapped = np.angle(analytic)
    unwrapped = complexops.phase_unwrap(wrapped)
    xs = origin + np.arange(rows.shape[1], dtype=np.float64)
    wx = wv if window == "hann" else np.ones(rows.shape[1])
    line = unwrapped.mean(axis=0)
    A = np.stack([xs, np.ones_like(xs)], axis=1)
    coef, *_ = np.linalg.lstsq(A * wx[:, None], line * wx, rcond=None)
    slope = float(coef[0])
    out["period_fit_px"] = 2.0 * np.pi / slope if slope != 0 else float("inf")
    resid = np.exp(1j * (line - 2.0 * np.pi * xs / P))
    out["phase_rad"] = float(np.angle(np.sum(wx * resid)))
    out["amplitude"] = float(2.0 * np.mean(np.abs(analytic)))
    out["phase_map"] = wrapped if axis == 1 else wrapped.T
    return out


def moire_phase_to_shift(phase_rad=0.5, phase_ref_rad=0.0, p_mask_um=2.0, p_wafer_um=2.04, moving="wafer",
                         coarse_shift_nm=None):
    """縞の位相の変化 → ずれ δ(nm)。δ = Δφ / (dφ/dδ)、dφ/dδ = ±2π / p_動いた格子。

    ずれは動いた格子のピッチ 1 つ分で折り返す(``ambiguity_nm``)。粗いが絶対的なずれ(例: 直接の像の相互相関)
    coarse_shift_nm を渡すと ``fringe.absolute_phase`` で次数を決め、折り返さない値を返す
    (粗い値の誤差が ambiguity の半分未満であること)。返り値の ``fringe_shift_um`` は縞が実際に動いた量
    (= M × δ、符号つき)。
    返り値: dict(shift_nm, ambiguity_nm, order(粗い値で決めた次数、無ければ 0)、fringe_shift_um, magnification)。
    **Raises** ValueError: 位相が有限でない、同じピッチ、綴り違い。
    """
    op = "moire_phase_to_shift"
    pm, pw = _pitches(p_mask_um, p_wafer_um, op)
    mv = _moving(moving, op)
    ph = _finite(phase_rad, "phase_rad", op)
    ref = _finite(phase_ref_rad, "phase_ref_rad", op)
    g = _phase_gain(pm, pw, mv)
    dphi = float(_wrap(ph - ref))
    order = 0
    if coarse_shift_nm is not None:
        import fringe                                      # noqa: PLC0415
        coarse = _finite(coarse_shift_nm, "coarse_shift_nm", op) * 1e-3 * g
        absol = float(fringe.absolute_phase(np.array([[dphi]]), np.array([[coarse]]))[0, 0])
        order = int(round((absol - dphi) / (2.0 * np.pi)))
        dphi = absol
    delta_um = dphi / g
    mag = (pm if mv == "wafer" else pw) / abs(pw - pm)
    fringe_shift = -dphi / (2.0 * math.pi * abs(_beat(pm, pw)))
    return {"shift_nm": delta_um * 1e3, "ambiguity_nm": 2.0 * math.pi / abs(g) * 1e3, "order": order,
            "fringe_shift_um": fringe_shift, "magnification": mag}


def moire_differential_shift(phase_a=0.3, phase_b=-0.3, phase_ref_a=0.0, phase_ref_b=0.0, p_mask_um=2.0, p_wafer_um=2.04,
                             moving="wafer"):
    """逆向きのピッチ差の 2 対(A = (p_m, p_w)、B = (p_w, p_m))から、共通の誤差を消したずれを読む。

    ずれ δ では 2 つの縞が**逆向き**に動き(dφ_A/dδ と dφ_B/dδ の符号が逆)、マーク全体がカメラに対して s 動くと
    **同じ向き**に同じ量(−2π|f|s)動く。だから
        δ = wrap(Δφ_A − Δφ_B) / (g_A − g_B)、 共通 = Δφ_A − g_A δ
    で、像の流れ・ステージの振動・カメラの倍率(どちらの縞にも同じに効く分)は δ から消える。
    捕捉範囲は 2π/|g_A − g_B| = p_m p_w / (p_m + p_w)(単一の対のおよそ半分)。

    返り値: dict(shift_nm, common_phase_rad, drift_nm(共通の位相を像の流れに換算)、ambiguity_nm,
    single_a_nm / single_b_nm(各対だけで読んだ場合 —— 共通の誤差がそのまま乗る))。
    **Raises** ValueError: 位相が有限でない、同じピッチ、綴り違い。
    """
    op = "moire_differential_shift"
    pm, pw = _pitches(p_mask_um, p_wafer_um, op)
    mv = _moving(moving, op)
    da = float(_wrap(_finite(phase_a, "phase_a", op) - _finite(phase_ref_a, "phase_ref_a", op)))
    db = float(_wrap(_finite(phase_b, "phase_b", op) - _finite(phase_ref_b, "phase_ref_b", op)))
    ga = _phase_gain(pm, pw, mv)
    gb = _phase_gain(pw, pm, mv)
    delta = float(_wrap(da - db)) / (ga - gb)
    common = float(_wrap(da - ga * delta))
    f = abs(_beat(pm, pw))
    return {"shift_nm": delta * 1e3, "common_phase_rad": common,
            "drift_nm": -common / (2.0 * math.pi * f) * 1e3,
            "ambiguity_nm": 2.0 * math.pi / abs(ga - gb) * 1e3,
            "single_a_nm": da / ga * 1e3, "single_b_nm": db / gb * 1e3}


def moire_mark_read(image, ref_image, pixel_um=0.5, p_mask_um=2.0, p_wafer_um=2.04, layout="differential",
                    margin_px=4, moving="wafer", window="hann", method="lockin"):
    """位置合わせのマーク 1 枚を、測定像と基準像(ずれ 0 のとき撮ったもの)から読む。

    区画は ``moire_overlay_image`` と同じ並び(layout)。各区画の縞の位相を ``moire_phase``(周期は設計値
    P / pixel_um)で読み、``"single"`` は ``moire_phase_to_shift``、``"differential"`` と ``"quad"`` は
    ``moire_differential_shift`` で共通の誤差を消す。margin_px は区画の境目から捨てる幅(ぼけが隣の区画を混ぜる)。
    ★ずれへの換算は**ピッチだけ**で決まり、カメラの倍率(pixel_um)は復調の周期にしか入らない。基準像と測定像に
    同じに効くので、pixel_um が数 % 違っても読みはほとんど動かない。

    返り値: dict(shift_x_nm、[shift_y_nm]、single_x_nm(対 A だけで読んだ値)、drift_x_nm、[drift_y_nm]、
    amplitudes(区画ごと)、ambiguity_nm、period_px)。
    **Raises** ValueError: 像の形が違う・2 次元でない、layout の綴り違い、margin が区画を食い尽くす、下請けの例外。
    """
    op = "moire_mark_read"
    img = _image(image, op)
    ref = _image(ref_image, op, "ref_image")
    if img.shape != ref.shape:
        raise ValueError("%s: image and ref_image must have the same shape, got %r and %r" % (op, img.shape, ref.shape))
    if layout not in MOIRE_LAYOUTS:
        raise ValueError("%s: layout must be one of %s, got %r" % (op, MOIRE_LAYOUTS, layout))
    px = _pos(pixel_um, "pixel_um", op)
    pm, pw = _pitches(p_mask_um, p_wafer_um, op)
    mv = _moving(moving, op)
    mg = int(margin_px)
    if mg < 0:
        raise ValueError("%s: margin_px must be >= 0, got %r" % (op, margin_px))
    P = 1.0 / abs(_beat(pm, pw)) / px
    ph, amps = {}, {}
    for name, (r0, r1, c0, c1), ax, _pair_name in _regions(img.shape, layout):
        reg = (r0 + mg, r1 - mg, c0 + mg, c1 - mg)
        if reg[0] >= reg[1] or reg[2] >= reg[3]:
            raise ValueError("%s: margin_px = %d leaves region %s empty" % (op, mg, name))
        m = moire_phase(img, P, ax, reg, window, method)
        r = moire_phase(ref, P, ax, reg, window, method)
        ph[name] = (m["phase_rad"], r["phase_rad"])
        amps[name] = m["amplitude"]
    out = {"amplitudes": amps, "period_px": P}
    if layout == "single":
        s = moire_phase_to_shift(ph["A_x"][0], ph["A_x"][1], pm, pw, mv)
        out.update({"shift_x_nm": s["shift_nm"], "single_x_nm": s["shift_nm"], "drift_x_nm": float("nan"),
                    "ambiguity_nm": s["ambiguity_nm"]})
        return out
    d = moire_differential_shift(ph["A_x"][0], ph["B_x"][0], ph["A_x"][1], ph["B_x"][1], pm, pw, mv)
    out.update({"shift_x_nm": d["shift_nm"], "single_x_nm": d["single_a_nm"], "drift_x_nm": d["drift_nm"],
                "ambiguity_nm": d["ambiguity_nm"]})
    if layout == "quad":
        dy = moire_differential_shift(ph["A_y"][0], ph["B_y"][0], ph["A_y"][1], ph["B_y"][1], pm, pw, mv)
        out.update({"shift_y_nm": dy["shift_nm"], "single_y_nm": dy["single_a_nm"], "drift_y_nm": dy["drift_nm"]})
    return out


# --------------------------------------------------------------------------- #
# 4. 限界                                                                       #
# --------------------------------------------------------------------------- #
def moire_phase_crlb(noise_sigma=0.01, amplitude=0.2, n_rows=256, n_cols=1024, p_mask_um=2.0, p_wafer_um=2.04,
                     moving="wafer", window="hann", noisy_reference=True):
    """白色ガウス雑音の下で、縞の位相とずれをどこまで細かく読めるか(下限の閉形式)。

    周波数が既知の正弦 A cos(2πx/P + φ) を N = n_rows × n_cols 画素の独立な雑音 σ の中で読むとき、
    var(φ) ≥ 2σ² / (N A²)(Rife & Boorstyn 1974 の位相の下限)。窓 w で重みを付けたロックインは
    係数 k_w = n Σw² / (Σw)² だけ悪い(Hann で約 1.5)。基準像にも同じ雑音があれば位相差の分散は 2 倍。
    ずれの標準偏差 = σ_φ / |dφ/dδ| = σ_φ p / (2π)。差動の 2 対(各対が同じ画素数)は
    σ_δ,diff = √(σ_A² + σ_B²) / |g_A − g_B|。
    ★これは**雑音だけ**の下限。実際の位置合わせはマークの非対称・ギャップ・傾き・レジストなどの系統誤差で決まり、
    公表値は 10〜30 nm(Li ら 2006、Zhu ら 2013)、空間位相の干渉法で 1 nm 未満の検出能(Moon & Smith 2005)。

    返り値: dict(phase_std_rad, shift_std_nm(対 A だけ)、shift_std_nm_differential、window_factor, n_pixels)。
    **Raises** ValueError: σ < 0、振幅・画素数が正でない、綴り違い、同じピッチ。
    """
    op = "moire_phase_crlb"
    s = _nonneg(noise_sigma, "noise_sigma", op)
    A = _pos(amplitude, "amplitude", op)
    nr, nc = int(n_rows), int(n_cols)
    if nr < 1 or nc < 2:
        raise ValueError("%s: n_rows must be >= 1 and n_cols >= 2, got %r, %r" % (op, n_rows, n_cols))
    if window not in ("hann", "none"):
        raise ValueError("%s: window must be 'hann' or 'none', got %r" % (op, window))
    pm, pw = _pitches(p_mask_um, p_wafer_um, op)
    mv = _moving(moving, op)
    wv = np.hanning(nc + 2)[1:-1] if window == "hann" else np.ones(nc)
    kw = float(nc * np.sum(wv ** 2) / np.sum(wv) ** 2)
    N = nr * nc
    var = 2.0 * s * s / (N * A * A) * kw * (2.0 if noisy_reference else 1.0)
    sp = math.sqrt(var)
    ga, gb = _phase_gain(pm, pw, mv), _phase_gain(pw, pm, mv)
    return {"phase_std_rad": sp, "shift_std_nm": sp / abs(ga) * 1e3,
            "shift_std_nm_differential": math.sqrt(2.0) * sp / abs(ga - gb) * 1e3,
            "window_factor": kw, "n_pixels": N}

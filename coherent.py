# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Coherent imaging and laser speckle — and the speckle floor of laser triangulation (numpy + scipy).

光学系の台帳(``lensimage.psf_from_opd`` / ``render_through_lens``)は**インコヒーレント**
結像だけを扱う(強度の PSF を畳み込む)。レーザーで照らした粗面はそうならない: 面の
凹凸が波長より大きいと、反射光の位相は画素ごとにでたらめになり、レンズの瞳で帯域を
切られた**複素振幅**が干渉して粒々の模様(スペックル)になる。スペックルは**静的**
(部品が止まっていれば毎フレーム同じ)なので、フレームを平均しても減らない ——
光切断・レーザー変位計の高さ誤差の床はここで決まる。

6 つの op(並びは物理の順):

  * :func:`coherent_image` — 振幅 + 位相の物体を、円形瞳(コヒーレント伝達関数
    ``CTF = circ(ρ / ρc)``、``ρc = NA / λ``)に通した像の強度 ``|F⁻¹{P · F{A e^{iφ}}}|²``。
    インコヒーレント結像との違いは**振幅で線形**なこと: 瞳が全次数を通す位相格子は
    像に何も残さず(強度 ≡ 1)、0 次だけを通すと強度は ``J0(a)²`` の一様になる。
  * :func:`speckle_field` — 粗面のランダム位相(完全発達 = 一様位相、または有限の
    粗さ σφ のガウス位相)→ :func:`coherent_image` → ``|E|²``。偏光 2 本・N 枚の独立な
    パターンの強度和、画素の面積積分(細格子で描いて画素ごとに平均)まで。
  * :func:`speckle_statistics` — コントラスト ``C = σ_I / ⟨I⟩``、指数分布(と 1/C² 次の
    ガンマ分布)への KS、強度の自己相関の半値全幅(= 粒径)と自己相関の断面。
  * :func:`laser_line_coherent` — 光切断の光条を、粗面のスペックル込みで描く
    (波長・観察開口 sin u・三角測量角 θ・画素の積分・偏光/独立パターンの和・加法雑音)。
  * :func:`triangulation_speckle_limit` — 三角測量の高さの不確かさの床
    ``δz = C · λ / (2π · sin u_obs · sin θ)``(Dorsch, Häusler & Herrmann 1994)。
  * :func:`speckle_reduction` — 独立なパターン N 枚(角度・波長・時間の多重化)と
    偏光 2 本で ``C = 1/√(N · pol)``、画素の積分による低下は Goodman の積分スペックルの
    **厳密な積分**(円形瞳の ``|2 J1(x)/x|²`` を正方形画素の重なり関数で重みづけ)。

単位の約束: 画像の op は**画素**で考える。``cutoff`` はコヒーレントの遮断周波数
``ρc = NA · (画素の物体側の大きさ) / λ`` を **1 画素あたりの周期数**で言ったもの
(``NA`` は像側でも物体側でも、画素の大きさを同じ側で測れば同じ数)。
光条の op だけは物体側の µm で受け取る(波長・画素の大きさ・光条の幅)。

真値(``tests/test_coherent.py`` の門):
  * Goodman の定理: 完全発達・単一偏光の強度は指数分布(C = 1)、M 本の独立な強度の
    和は M 次のガンマ分布(C = 1/√M)。有限の粗さでは定数の位相子 + 非円形のガウス
    雑音の閉形式(Rice 型)。
  * 粒径: 強度の自己相関は ``1 + |μ|²``、``μ`` は瞳の強度のフーリエ変換 =
    ``2 J1(2π ρc r) / (2π ρc r)``(Airy の振幅)。半値全幅 = ``0.5145 / ρc`` 画素。
  * 画素の積分: ``C² = ∬ K(Δ) |μ(Δ)|² dΔ / A²``(Goodman, *Speckle Phenomena in Optics*,
    2007, §4.6 の積分スペックルの定義式を数値積分したもの。近似式ではない)。
  * 三角測量: 光条中心の標準偏差が λ に +1、sin u に −1、sin θ に −1 で比例する
    (指数を門にする。比例定数はモデル依存なので開示するだけ)。

★正直に書いておくこと:
  * Dorsch らの式は**原論文の本文を読めていない**(読めたのは抄録: 「不確かさは観察開口と
    三角測量角で決まり、投光スポットが観察したスペックルより大きければスポットの大きさに
    よらない」)。式の形 ``C·λ/(2π sin u sin θ)`` は二次文献での引用の形で、2π の係数は
    確かめていない。門は指数だけで立て、測った比例定数は PoC が開示する。
  * 光条の op はスカラ回折・近軸・倍率 1(物体側の座標で描く)・**焦点の合った**平面の
    粗面。高さの変化は光条を画像上で ``h · sin θ`` だけずらすだけで、前縮み(斜めから
    見ると光条の見かけの幅が cos θ 倍になる)・Scheimpflug・デフォーカス・多重散乱・
    体積散乱は入っていない。位相スクリーンは物体側の座標に固定(部品が止まっている)。
  * 位相は物体側の細格子の 1 点ごとに独立(相関長 0 の粗面)。実際の粗面は相関長を
    持つが、観察開口がそれより粗く切っていれば(相関長 < 粒径)統計は同じになる。

出典: J. W. Goodman, *Speckle Phenomena in Optics*, Roberts & Co., 2007(§3.2 一次統計、
§4.4 自己相関、§4.6 積分スペックル)/ R. G. Dorsch, G. Häusler, J. M. Herrmann,
"Laser triangulation: fundamental uncertainty in distance measurement",
*Appl. Opt.* 33(7):1306–1314, 1994 / J. W. Goodman, *Introduction to Fourier Optics*,
3rd ed., 2005(コヒーレント伝達関数)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "coherent_image",
    "speckle_field",
    "speckle_statistics",
    "laser_line_coherent",
    "triangulation_speckle_limit",
    "speckle_reduction",
]

#: 1 枚の細格子の画素数の上限(FFT の作業領域を確保する前に拒む)。
MAX_FINE_PIXELS = 1 << 24
#: 独立なパターン(偏光 × 枚数)の和の上限。
MAX_PATTERNS = 1024
#: 円形瞳の |2 J1(x)/x|² が 1/2 になる x(半値全幅 = 2 · X_HALF / (2π ρc))。
X_HALF = 1.6163399
#: 半値全幅 [画素] = FWHM_PER_INV_CUTOFF / ρc。
FWHM_PER_INV_CUTOFF = 2.0 * X_HALF / (2.0 * math.pi)


def _special():
    from scipy import special as _sp          # noqa: PLC0415 — numpy だけの環境で import を落とさない
    return _sp


def _stats():
    from scipy import stats as _st             # noqa: PLC0415
    return _st


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
    if not lo <= v <= hi:
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, v))
    return v


def _shape(shape, op, lo=4):
    try:
        ny, nx = shape
    except (TypeError, ValueError):
        raise ValueError("%s: shape must be (rows, cols), got %r" % (op, shape)) from None
    ny = _int(ny, "shape[0]", op, lo, 1 << 14)
    nx = _int(nx, "shape[1]", op, lo, 1 << 14)
    return ny, nx


def _real2d(a, name, op, nonneg=False, min_side=1):
    if a is None:
        raise ValueError("%s: %s is None" % (op, name))
    if np.ma.is_masked(a):
        raise ValueError("%s: %s is a masked array with masked entries" % (op, name))
    arr = np.asarray(a)
    if arr.dtype.kind not in "iuf":
        raise ValueError("%s: %s has dtype %r — expected real numbers" % (op, name, str(arr.dtype)))
    if arr.ndim != 2:
        raise ValueError("%s: %s must be 2-D, got shape %s" % (op, name, arr.shape))
    if min(arr.shape) < min_side:
        raise ValueError("%s: %s must be at least %dx%d, got %s" % (op, name, min_side, min_side, arr.shape))
    if arr.size > MAX_FINE_PIXELS:
        raise ValueError("%s: %s has %d pixels, over the %d cap" % (op, name, arr.size, MAX_FINE_PIXELS))
    arr = arr.astype(np.float64)
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s has non-finite values (nan/inf)" % (op, name))
    if nonneg and (arr < 0).any():
        raise ValueError("%s: %s must be >= 0 (an intensity), min %g" % (op, name, float(arr.min())))
    return arr


def _seed(seed, op):
    if seed is None:
        raise ValueError("%s: seed must be an integer (a speckle realisation is reproducible "
                         "only with a fixed seed)" % op)
    return _int(seed, "seed", op, 0, (1 << 63) - 1)


# --------------------------------------------------------------------------- #
# コヒーレント伝達関数
# --------------------------------------------------------------------------- #
def _circ_pupil(ny, nx, cutoff):
    """円形瞳(DC は [0, 0]、numpy の FFT の並び)。cutoff は 1 標本あたりの周期数。"""
    fy = np.fft.fftfreq(ny)[:, None]
    fx = np.fft.fftfreq(nx)[None, :]
    return (fy * fy + fx * fx) <= cutoff * cutoff


def _filter(field, pupil):
    return np.fft.ifft2(np.fft.fft2(field) * pupil)


def _block_mean(img, s):
    if s == 1:
        return img
    ny, nx = img.shape
    return img.reshape(ny // s, s, nx // s, s).mean(axis=(1, 3))


def coherent_image(amplitude, phase=None, cutoff=0.25, pupil=None, defocus_waves=0.0):
    """Coherent image intensity of an amplitude/phase object through a pupil (``image2d``).

    ``|F⁻¹{P · F{A · e^{iφ}}}|²`` with the circular pupil ``P = circ(ρ / cutoff)``
    (``cutoff`` = coherent cut-off NA·pitch/λ in cycles per pixel, in (0, 0.5]) or a
    user ``pupil`` (2-D, same shape, DC at the centre, i.e. ``np.fft.fftshift`` order;
    complex allowed). ``defocus_waves`` multiplies the circular pupil by
    ``exp(i 2π W20 (ρ/ρc)²)``. The object is periodic (the FFT wraps at the edges).

    Ground truth (``tests/test_coherent.py``): a pure phase grating whose orders all pass
    leaves a flat image (intensity 1 to 1e-12); with only the 0th order passed the image is
    the constant ``J0(a)²``; with 0 and ±1 it is ``J0² + 4 J1² sin²`` — the linear-in-amplitude
    signature that incoherent imaging does not have.
    """
    op = "coherent_image"
    A = _real2d(amplitude, "amplitude", op, nonneg=True, min_side=2)
    ny, nx = A.shape
    if phase is None:
        ph = np.zeros_like(A)
    else:
        ph = _real2d(phase, "phase", op)
        if ph.shape != A.shape:
            raise ValueError("%s: phase has shape %s but amplitude has %s" % (op, ph.shape, A.shape))
    dz = _num(defocus_waves, "defocus_waves", op)
    if pupil is None:
        c = _num(cutoff, "cutoff", op, lo=0.0, hi=0.5)
        P = _circ_pupil(ny, nx, c).astype(np.complex128)
        if dz != 0.0:
            fy = np.fft.fftfreq(ny)[:, None]
            fx = np.fft.fftfreq(nx)[None, :]
            P = P * np.exp(2j * math.pi * dz * (fy * fy + fx * fx) / (c * c))
    else:
        Pin = np.asarray(pupil)
        if Pin.dtype.kind not in "iufcb" or Pin.shape != A.shape:
            raise ValueError("%s: pupil must be a numeric 2-D array of shape %s, got %s %s"
                             % (op, A.shape, Pin.dtype, Pin.shape))
        Pin = Pin.astype(np.complex128)
        if not np.isfinite(Pin).all():
            raise ValueError("%s: pupil has non-finite values" % op)
        if not np.any(np.abs(Pin) > 0):
            raise ValueError("%s: pupil is zero everywhere (no light passes)" % op)
        if dz != 0.0:
            raise ValueError("%s: defocus_waves applies to the circular pupil only — "
                             "put the defocus phase into your pupil" % op)
        P = np.fft.ifftshift(Pin)
    E = _filter(A * np.exp(1j * ph), P)
    return (E.real ** 2 + E.imag ** 2)


# --------------------------------------------------------------------------- #
# スペックル
# --------------------------------------------------------------------------- #
def _one_pattern(rng, ny, nx, pupil, rough):
    """1 枚のスペックル強度(期待値 1 に正規化)。"""
    if rough is None:
        phi = rng.uniform(0.0, 2.0 * math.pi, (ny, nx))
    else:
        phi = rng.normal(0.0, rough, (ny, nx))
    E = _filter(np.exp(1j * phi), pupil)
    return E.real ** 2 + E.imag ** 2


def _expected_mean(pupil, rough):
    """1 枚の強度の期待値: 定数の位相子 m² + 拡散成分 (1 − m²)·f(f = 瞳の面積比)。"""
    f = float(pupil.sum()) / pupil.size
    if rough is None:
        return f
    m2 = math.exp(-rough * rough)
    return m2 + (1.0 - m2) * f


def speckle_field(shape=(256, 256), cutoff=0.125, roughness_rad=None, polarizations=1,
                  n_patterns=1, pixel_oversample=1, seed=0):
    """Laser speckle intensity from a rough surface seen through a circular pupil (``image2d``).

    Each pattern is a random phase screen (``roughness_rad=None``: uniform phase on
    [0, 2π) = fully developed; a number σφ: Gaussian phase of that standard deviation =
    partially developed) filtered by the coherent transfer function ``circ(ρ/ρc)`` and
    squared. ``polarizations`` (1 or 2) × ``n_patterns`` independent intensities are
    averaged (C = 1/√M for fully developed speckle). With ``pixel_oversample = s`` the field
    is drawn on an s-times finer grid and averaged over each s×s block — the pixel's area
    integration (``cutoff`` stays in cycles per *output* pixel and must be ≤ 0.5·s).
    The mean intensity is normalised to 1 in expectation (not per image).

    Ground truth (``tests/test_coherent.py``): exponential intensity (KS) with C = 1,
    gamma of order M with C = 1/√M, intensity autocorrelation = Airy amplitude squared,
    the Rice-type closed form for finite roughness, and pixel integration against
    :func:`speckle_reduction`'s exact integral.
    """
    op = "speckle_field"
    ny, nx = _shape(shape, op)
    s = _int(pixel_oversample, "pixel_oversample", op, 1, 64)
    c = _num(cutoff, "cutoff", op, lo=0.0, hi=0.5 * s)
    rough = None if roughness_rad is None else _num(roughness_rad, "roughness_rad", op, lo=0.0, hi=1e3)
    pol = _int(polarizations, "polarizations", op, 1, 2)
    n = _int(n_patterns, "n_patterns", op, 1, MAX_PATTERNS)
    if pol * n > MAX_PATTERNS:
        raise ValueError("%s: polarizations x n_patterns = %d is over the %d cap" % (op, pol * n, MAX_PATTERNS))
    fy, fx = ny * s, nx * s
    if fy * fx > MAX_FINE_PIXELS:
        raise ValueError("%s: the fine grid %dx%d is over the %d-pixel cap" % (op, fy, fx, MAX_FINE_PIXELS))
    rng = np.random.default_rng(_seed(seed, op))
    pupil = _circ_pupil(fy, fx, c / s)
    if not pupil.any():                                    # pragma: no cover — DC is always inside
        raise ValueError("%s: the pupil passes nothing" % op)
    acc = np.zeros((fy, fx))
    for _ in range(pol * n):
        acc += _one_pattern(rng, fy, fx, pupil, rough)
    acc /= (pol * n) * _expected_mean(pupil, rough)
    return _block_mean(acc, s)


def _acf_cuts(img, up):
    """正規化した強度の自己共分散(周期境界)の x・y 断面を、フーリエ補間で up 倍に細かく。"""
    d = img - img.mean()
    ny, nx = d.shape
    S = np.abs(np.fft.fft2(d)) ** 2
    out = []
    for axis in (0, 1):
        # 断面 = パワースペクトルを他方の軸で足して 1-D の逆変換(Wiener–Khinchin の 1-D 版)
        s1 = S.sum(axis=1 - axis)
        n = s1.size
        if up == 1:
            r = np.fft.ifft(s1).real
            out.append(r / r[0])
            continue
        m = n * up
        pad = np.zeros(m, dtype=np.complex128)
        h = n // 2
        pad[:h] = s1[:h]
        pad[m - (n - h):] = s1[h:]
        if n % 2 == 0:                                      # ナイキスト成分は両端に半分ずつ
            pad[h] = 0.5 * s1[h]
            pad[m - h] = 0.5 * s1[h]
        r = np.fft.ifft(pad).real
        out.append(r / r[0])
    return out


def _half_crossing(r, up):
    """自己相関の断面が初めて 1/2 を切る遅れ [画素](線形補間)。"""
    below = np.nonzero(r[: r.size // 2] < 0.5)[0]
    if below.size == 0:
        return float("nan")
    k = int(below[0])
    t = (r[k - 1] - 0.5) / (r[k - 1] - r[k])
    return (k - 1 + t) / up


def speckle_statistics(image, roi=None, upsample=4):
    """First- and second-order statistics of a speckle intensity image (``table``).

    Returns the mean, standard deviation and contrast ``C = σ/⟨I⟩``, the gamma order
    ``M = 1/C²``, the speckle size as the full width at half maximum of the normalised
    intensity autocovariance (``speckle_fwhm_px``, mean of the x and y cuts; Fourier-
    interpolated ``upsample`` times, periodic boundary), the cut itself (``acf_lag_px``,
    ``acf``), and Kolmogorov–Smirnov tests against the exponential law (``ks_p_exponential``)
    and the gamma law of order M (``ks_p_gamma``) on a sub-sample thinned to one pixel per
    ``ks_stride`` (≥ 2 × FWHM) so the samples are close to independent.
    ★The KS p-values are approximate: the mean (and M) are estimated from the same data
    (Lilliefors), and thinning does not make the samples exactly independent.
    """
    op = "speckle_statistics"
    img = _real2d(image, "image", op, nonneg=True, min_side=8)
    if roi is not None:
        try:
            r0, r1, c0, c1 = (int(v) for v in roi)
        except (TypeError, ValueError):
            raise ValueError("%s: roi must be (row0, row1, col0, col1), got %r" % (op, roi)) from None
        if not (0 <= r0 < r1 <= img.shape[0] and 0 <= c0 < c1 <= img.shape[1]):
            raise ValueError("%s: roi %r is outside the %s image" % (op, roi, img.shape))
        img = img[r0:r1, c0:c1]
        if min(img.shape) < 8:
            raise ValueError("%s: the roi must be at least 8x8, got %s" % (op, img.shape))
    up = _int(upsample, "upsample", op, 1, 16)
    mean = float(img.mean())
    if mean <= 0:
        raise ValueError("%s: the image is dark (mean %g) — no speckle to measure" % (op, mean))
    std = float(img.std())
    if std == 0.0:
        raise ValueError("%s: the image is constant — no speckle to measure" % op)
    C = std / mean
    cy, cx = _acf_cuts(img, up)
    hy, hx = _half_crossing(cy, up), _half_crossing(cx, up)
    fwhm = 2.0 * float(np.nanmean([hx, hy])) if np.isfinite([hx, hy]).any() else float("nan")
    nlag = int(min(cx.size, cy.size) // 2)
    lag = np.arange(nlag) / up
    acf = 0.5 * (cx[:nlag] + cy[:nlag])
    stride = max(1, int(math.ceil(2.0 * fwhm))) if math.isfinite(fwhm) else 1
    sub = img[::stride, ::stride].ravel()
    st = _stats()
    ks_e = st.kstest(sub, "expon", args=(0.0, mean))
    M = 1.0 / (C * C)
    ks_g = st.kstest(sub, "gamma", args=(M, 0.0, mean / M))
    return {
        "mean": mean, "std": std, "contrast": C, "gamma_order": M,
        "n_pixels": int(img.size),
        "speckle_fwhm_px": fwhm, "speckle_fwhm_x_px": 2.0 * hx, "speckle_fwhm_y_px": 2.0 * hy,
        "acf_lag_px": lag, "acf": acf,
        "ks_stride": stride, "ks_n": int(sub.size),
        "ks_stat_exponential": float(ks_e.statistic), "ks_p_exponential": float(ks_e.pvalue),
        "ks_stat_gamma": float(ks_g.statistic), "ks_p_gamma": float(ks_g.pvalue),
    }


# --------------------------------------------------------------------------- #
# 光切断の光条
# --------------------------------------------------------------------------- #
def laser_line_coherent(shape=(96, 512), wavelength_um=0.65, sin_u_obs=0.05, pixel_um=2.0,
                        line_width_um=20.0, height_um=20.0, sin_theta=0.5, row0=None,
                        polarizations=1, n_patterns=1, pixel_oversample=2, roughness_rad=None,
                        noise=0.0, seed=0, noise_seed=None):
    """A sheet-of-light laser line on a rough surface, imaged with its speckle (``image2d``).

    Object-side coordinates, magnification 1: one output pixel covers ``pixel_um`` on the
    part. The line is a Gaussian band along the columns, intensity 1/e² half-width
    ``line_width_um`` (as seen by the camera), centred on the row
    ``row0 + height_um · sin_theta / pixel_um`` (``height_um`` a number or one value per
    column, default 20 µm so that ``sin_theta`` acts on the default call; ``row0`` defaults
    to the middle row) — the triangulation shift. Its amplitude
    multiplies a random phase screen fixed to the part (``seed``), the field passes the
    observation pupil ``sin_u_obs`` (cut-off ``sin_u/λ``), and the intensity is integrated
    over each pixel (``pixel_oversample``). ``polarizations`` × ``n_patterns`` independent
    patterns are averaged (a moving diffuser / several wavelengths). ``noise`` adds
    Gaussian read noise of that standard deviation relative to the line's peak mean
    intensity (seeded by ``noise_seed``, so a static part with several noisy frames is
    ``same seed, different noise_seed``). The mean peak intensity is 1.

    The true centre row is returned implicitly by the formula above; see
    :func:`triangulation_speckle_limit` for the floor this sets. Limits: scalar, paraxial,
    in focus, no foreshortening of the line width with θ, no Scheimpflug, phase screen
    uncorrelated between fine samples.
    """
    op = "laser_line_coherent"
    ny, nx = _shape(shape, op, lo=8)
    lam = _num(wavelength_um, "wavelength_um", op, lo=0.0, hi=100.0)
    su = _num(sin_u_obs, "sin_u_obs", op, lo=0.0, hi=1.0)
    st = _num(sin_theta, "sin_theta", op, lo=0.0, hi=1.0)
    pix = _num(pixel_um, "pixel_um", op, lo=0.0, hi=1e5)
    w = _num(line_width_um, "line_width_um", op, lo=0.0, hi=1e6)
    s = _int(pixel_oversample, "pixel_oversample", op, 1, 32)
    pol = _int(polarizations, "polarizations", op, 1, 2)
    n = _int(n_patterns, "n_patterns", op, 1, MAX_PATTERNS)
    nz = _num(noise, "noise", op, lo=0.0, hi=1e3, lo_open=False)
    rough = None if roughness_rad is None else _num(roughness_rad, "roughness_rad", op, lo=0.0, hi=1e3)
    r0 = (ny - 1) / 2.0 if row0 is None else _num(row0, "row0", op)
    h = np.asarray(height_um, dtype=np.float64) if not isinstance(height_um, (str, bytes)) else None
    if h is None or h.dtype.kind != "f" or h.ndim > 1 or (h.ndim == 1 and h.size != nx):
        raise ValueError("%s: height_um must be a number or one value per column (%d), got %r"
                         % (op, nx, height_um))
    if not np.isfinite(h).all():
        raise ValueError("%s: height_um has non-finite values" % op)
    dx = pix / s
    c_fine = su / lam * dx                                  # 細格子 1 標本あたりの周期数
    if c_fine > 0.5:
        raise ValueError("%s: the pupil cut-off sin_u/λ = %.4g /µm is above the fine grid's "
                         "Nyquist (%.4g /µm) — raise pixel_oversample or use smaller pixels"
                         % (op, su / lam, 0.5 / dx))
    fy, fx = ny * s, nx * s
    if fy * fx > MAX_FINE_PIXELS:
        raise ValueError("%s: the fine grid %dx%d is over the %d-pixel cap" % (op, fy, fx, MAX_FINE_PIXELS))
    pupil = _circ_pupil(fy, fx, c_fine)
    centre = r0 + h * st / pix                              # 画素の行(列ごと or 一定)
    yy = (np.arange(fy) + 0.5) / s - 0.5                    # 細格子の標本の位置(出力画素の行の座標)
    cen = np.repeat(centre, s) if np.ndim(centre) else np.full(fx, float(centre))
    amp = np.exp(-((yy[:, None] - cen[None, :]) * pix) ** 2 / (w * w))   # 強度 exp(-2 y²/w²)
    rng = np.random.default_rng(_seed(seed, op))
    acc = np.zeros((fy, fx))
    for _ in range(pol * n):
        if rough is None:
            phi = rng.uniform(0.0, 2.0 * math.pi, (fy, fx))
        else:
            phi = rng.normal(0.0, rough, (fy, fx))
        E = _filter(amp * np.exp(1j * phi), pupil)
        acc += E.real ** 2 + E.imag ** 2
    acc /= (pol * n) * _expected_mean(pupil, rough)
    img = _block_mean(acc, s)
    if nz > 0:
        nrng = np.random.default_rng(_seed(0 if noise_seed is None else noise_seed, op) + 0x5EC)
        img = img + nrng.normal(0.0, nz, img.shape)
    return img


# --------------------------------------------------------------------------- #
# 閉形式
# --------------------------------------------------------------------------- #
def triangulation_speckle_limit(wavelength_um=0.65, sin_u_obs=0.05, sin_theta=0.5, contrast=1.0):
    """Speckle floor of laser triangulation (``table``): ``δz = C λ / (2π sin u_obs sin θ)``.

    Dorsch, Häusler & Herrmann, Appl. Opt. 33(7):1306, 1994: the centroid of a speckled
    spot cannot be located better than ``δx = C λ / (2π sin u_obs)`` in the observation
    plane, and triangulation turns a lateral shift into height through ``1/sin θ``.
    ``C`` is the speckle contrast reaching the detector (1 for fully developed speckle;
    lower with pixel integration or :func:`speckle_reduction`). Also returns the speckle
    size (FWHM of the intensity autocorrelation, ``0.5145 λ / sin u``) in µm.

    ★For a **centroid** estimator ``C`` is *not* the pixel-integrated contrast: the centroid
    of a box-filtered intensity is the centroid of the intensity, so bigger pixels lower the
    contrast a viewer sees but not the centroid's error (gated exactly in the tests).
    Averaging the centroid along ``L`` µm of a line of 1/e² half-width ``w`` scales the error
    as ``√(w/L)`` (measured; Dorsch's spot-size independence is the ``L ≈ w`` case).

    ★The 2π factor is as quoted in secondary sources; the primary text was not read (only
    its abstract). ``tests/test_coherent.py`` gates the exponents (λ: +1, sin u: −1,
    sin θ: −1) against rendered speckled lines, not the constant.
    """
    op = "triangulation_speckle_limit"
    lam = _num(wavelength_um, "wavelength_um", op, lo=0.0, hi=100.0)
    su = _num(sin_u_obs, "sin_u_obs", op, lo=0.0, hi=1.0)
    st = _num(sin_theta, "sin_theta", op, lo=0.0, hi=1.0)
    C = _num(contrast, "contrast", op, lo=0.0, hi=1.0, lo_open=False)
    dx = C * lam / (2.0 * math.pi * su)
    return {
        "delta_z_um": dx / st, "delta_x_um": dx,
        "speckle_fwhm_um": FWHM_PER_INV_CUTOFF * lam / su,
        "wavelength_um": lam, "sin_u_obs": su, "sin_theta": st, "contrast": C,
        "formula": "delta_z = C * lambda / (2 * pi * sin_u_obs * sin_theta)",
        "source": "Dorsch, Hausler & Herrmann, Appl. Opt. 33(7):1306-1314 (1994); "
                  "2*pi factor from secondary citations, exponents gated by simulation",
    }


def _pixel_contrast(cutoff, n=96):
    """正方形画素(1 x 1)で積分したスペックルのコントラスト(Goodman §4.6 の定義式の数値積分)。

    C² = ∬_{[-1,1]²} (1 − |Δx|)(1 − |Δy|) |2 J1(2π ρc r) / (2π ρc r)|² dΔx dΔy。
    対称なので第 1 象限の 4 倍、Gauss–Legendre の n×n 点。
    """
    xg, wg = np.polynomial.legendre.leggauss(n)
    t = 0.5 * (xg + 1.0)                                    # [0, 1]
    wt = 0.5 * wg
    X, Y = np.meshgrid(t, t, indexing="ij")
    r = np.hypot(X, Y)
    x = 2.0 * math.pi * cutoff * r
    j1 = _special().j1
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = np.where(x > 1e-12, 2.0 * j1(x) / np.where(x > 1e-12, x, 1.0), 1.0)
    K = (1.0 - X) * (1.0 - Y)
    c2 = 4.0 * float(np.sum(wt[:, None] * wt[None, :] * K * mu * mu))
    return math.sqrt(min(1.0, c2))


def speckle_reduction(n_patterns=1, polarizations=1, cutoff=None):
    """Predicted speckle contrast after reduction (``table``).

    * ``n_patterns`` independent patterns (angle / wavelength / time diversity, a moving
      part) and ``polarizations`` (1 or 2): ``C = 1/√(N·pol)`` (Goodman §5).
    * ``cutoff`` (coherent cut-off in cycles per pixel): the pixel's area integration,
      ``C_pixel² = ∬ K(Δ)|μ(Δ)|² dΔ`` with the square pixel's overlap ``K`` and the
      circular pupil's ``μ = 2 J1(x)/x`` — the exact defining integral (Goodman §4.6),
      evaluated by Gauss–Legendre quadrature, not the Gaussian-pupil approximation.
      ``None`` = point sampling (C_pixel = 1).

    Returns each factor and the combined ``contrast = C_pixel / √(N·pol)``. Also returns
    ``speckle_cells_per_pixel = 1/C_pixel²`` (Goodman's M for one pixel).
    """
    op = "speckle_reduction"
    n = _int(n_patterns, "n_patterns", op, 1, 1 << 30)
    pol = _int(polarizations, "polarizations", op, 1, 2)
    cpix = 1.0
    if cutoff is not None:
        c = _num(cutoff, "cutoff", op, lo=0.0, hi=64.0)
        cpix = _pixel_contrast(c, n=min(800, 96 + int(8 * c)))
    div = 1.0 / math.sqrt(n * pol)
    return {
        "contrast": cpix * div, "contrast_pixel": cpix, "contrast_diversity": div,
        "speckle_cells_per_pixel": 1.0 / (cpix * cpix),
        "n_patterns": n, "polarizations": pol,
        "cutoff": None if cutoff is None else float(cutoff),
    }

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""semsim —— 走査電子顕微鏡(SEM)像の物理モデルで、縁の明るさを真値つきで作る。

CD-SEM(半導体の寸法計測)でも外観検査でも、**二次電子は斜面でよけいに出る**ので
段差の縁が明るく縁取られる。この縁取りが寸法計測を太らせる —— 明るい帯ごと
しきい値を超えて拾ってしまうからである。その縁取りを「見た目」ではなく
**閉形式の真値**として作るのがこの module の役目で、作った像は他の PoC の
合成入力(真値つき)にもなる(``opsgenerative`` 族の方針そのまま)。

物理(Reimer, *Scanning Electron Microscopy*; Goldstein ほか *SEM and X-ray
Microanalysis* の教科書的モデルを、採点できる最小形に落としたもの):

  * **二次電子の縁効果**: 局所の表面傾き θ に対し放出は δ(θ) = δ0·sec θ で増える
    (脱出深さが 1/cos θ で伸びるため)。平らな面(θ=0)では一様、斜面では
    sec θ 倍。θ は高さ場の勾配から ``arctan|∇h|`` で測る。
  * **ビームの PSF**: 有限のビーム径をガウシアン(σ = ``psf_px``)で畳む。段差の
    縁の明るい線は、この PSF 幅ぶんだけ広がる(= 明るい縁の幅 ≈ PSF 幅)。
  * **ショット雑音**: 画素あたりの電子数をポアソンで散らす(``dose`` 電子/画素)。
  * **帯電**(任意): 緩い横方向の輝度勾配(``charging``)。

真値の 3 本(``tests/test_semsim.py`` が閉形式で確かめる):
  1. 平らな高さ場 → 出力は一様(雑音を切れば ptp = 0)。
  2. 傾き θ の一様斜面 → 平面に対する輝度比はちょうど sec θ。
  3. 段差 → 明るい縁の輝度プロファイルの幅(2 次モーメント)は PSF 幅 σ に一致する。

この族が新しい型語彙を 1 つも作らないのは ``opsgenerative`` と同じ:
入力も出力も既存の ``image2d``(H×W, [0,1] の float)で、作った SEM 像に
既存の 2-D op(しきい値・連結成分・採点)がそのまま掛かることに値打ちがある。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as _ndi

__all__ = ["sem_render"]


def _as_height(height, op: str) -> np.ndarray:
    """高さ場を 2-D の有限な float64 にして返す(fail-closed)。"""
    h = np.asarray(height, dtype=np.float64)
    if h.ndim != 2:
        raise ValueError("%s: height must be 2-D (H, W), got shape %r" % (op, h.shape))
    if h.size == 0:
        raise ValueError("%s: height is empty" % op)
    if not np.isfinite(h).all():
        raise ValueError("%s: height has non-finite values (NaN/Inf)" % op)
    return h


def _positive(v, name: str, op: str) -> float:
    f = float(v)
    if not np.isfinite(f) or f <= 0.0:
        raise ValueError("%s: %s must be a positive finite number, got %r" % (op, name, v))
    return f


def sem_render(height, *, pixel_nm: float = 1.0, psf_px: float = 1.5,
               edge_gain: float = 1.0, base: float = 0.25, dose: float = 0.0,
               charging: float = 0.0, seed: int = 0,
               tilt_max_deg: float = 80.0) -> np.ndarray:
    """高さ場から SEM 像(二次電子の縁効果 + ビーム PSF + ショット雑音)を描く。

    Parameters
    ----------
    height : array_like
        2-D の高さ場[同じ単位は ``pixel_nm``]。欠陥の形そのもの。
    pixel_nm : float
        画素 1 個の一辺[nm]。傾きは ``arctan(|∇h| / pixel_nm)`` で測る。
    psf_px : float
        ビーム PSF のガウシアン σ[px]。段差の明るい縁はこの幅に広がる。
    edge_gain : float
        縁効果の強さの指数。``sec(θ) ** edge_gain``。既定 1.0 が sec θ の素のモデル。
    base : float
        平らな面(θ=0)の明るさ[0,1]。斜面は ``base·sec θ`` に乗る(飽和で 1 に頭打ち)。
    dose : float
        画素あたりの電子数。``> 0`` でポアソン雑音を載せる。``0`` は雑音なし(決定論)。
    charging : float
        帯電による緩い横方向の輝度勾配(0 で無効)。収差でなく系統的な明暗。
    seed : int
        ポアソン雑音の種(``dose > 0`` のときだけ効く)。
    tilt_max_deg : float
        sec θ が発散しないよう θ を頭打ちにする角度[度]。既定 80 度(sec ≈ 5.76)。

    Returns
    -------
    numpy.ndarray
        ``(H, W)`` の float64、[0,1]。平らな面は ``base``、斜面は ``base·sec θ``。

    Notes
    -----
    正規化は**画素ごとでなく固定の線形写像**(``·base`` と [0,1] クリップ)。
    1 枚ごとに min/max で正規化すると平面に対する比が壊れ、sec θ の真値を
    測れなくなる(``poc_real_defect_floor`` が ``colorize_depth`` の per-image
    正規化で踏んだ罠と同じ)。

    Examples
    --------
    >>> import numpy as np
    >>> flat = np.zeros((16, 16))
    >>> img = sem_render(flat)
    >>> float(np.ptp(img))            # 平らな面は一様
    0.0
    >>> ramp = np.tile(np.linspace(0, 15, 16), (16, 1))   # 一様斜面
    >>> r = sem_render(ramp, pixel_nm=1.0)
    >>> theta = np.arctan(1.0)                            # 勾配 1 → 45 度
    >>> abs(float(r[8, 8]) / 0.25 - 1.0 / np.cos(theta)) < 1e-6
    True
    """
    op = "sem_render"
    h = _as_height(height, op)
    pixel_nm = _positive(pixel_nm, "pixel_nm", op)
    psf_px = _positive(psf_px, "psf_px", op)
    base = float(base)
    if not (0.0 < base <= 1.0):
        raise ValueError("%s: base must be in (0, 1], got %r" % (op, base))
    edge_gain = _positive(edge_gain, "edge_gain", op)
    tilt_max = np.radians(_positive(tilt_max_deg, "tilt_max_deg", op))
    if tilt_max >= np.pi / 2:
        raise ValueError("%s: tilt_max_deg must be < 90, got %r" % (op, tilt_max_deg))

    # 傾き θ を高さ場の勾配から。np.gradient は端で片側差分に落ちるが、同じ
    # 傾きなので一様斜面では全面一定のまま(縁の 2 次モーメント検査は内側で測る)。
    gy, gx = np.gradient(h, pixel_nm)
    theta = np.arctan(np.hypot(gx, gy))
    theta = np.minimum(theta, tilt_max)

    # 二次電子の縁効果。δ(θ) = δ0·sec θ(脱出深さが 1/cos θ で伸びる)。
    yield_ = (1.0 / np.cos(theta)) ** edge_gain

    if charging:
        w = h.shape[1]
        ramp = (np.arange(w, dtype=np.float64) / max(w - 1, 1)) - 0.5   # [-0.5, 0.5]
        yield_ = yield_ * (1.0 + float(charging) * ramp[None, :])

    # ビーム PSF。段差の縁の明るい線は、この σ ぶんだけ広がる。
    inten = _ndi.gaussian_filter(yield_, psf_px, mode="nearest")

    if dose > 0.0:
        lam = np.clip(inten * float(dose), 0.0, None)
        rng = np.random.default_rng(int(seed))
        inten = rng.poisson(lam).astype(np.float64) / float(dose)

    return np.clip(inten * base, 0.0, 1.0)

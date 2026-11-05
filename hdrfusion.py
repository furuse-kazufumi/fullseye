# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""HDR imaging — camera response from an exposure series, radiance merge, exposure fusion,
and the measured dynamic range against EMVA 1288 (numpy + scipy).

露出を変えた画像の列から、カメラの応答関数を推定し(Debevec–Malik / Robertson)、
放射輝度の地図を合成し(HDR)、または放射輝度を経ずに 1 枚へ融合する(Mertens)。
トーンマップは既存の :func:`render_tonemap.tonemap_reinhard` / ``tonemap_aces`` を使う(再実装しない)。

土台 / The base layer:
  * :func:`camera_response_debevec` — Debevec & Malik (1997) の最小二乗:
    ``w(Z_ij) [g(Z_ij) − ln E_i − ln Δt_j] = 0`` と滑らかさ ``λ w(z) g''(z) = 0``、``g(中央) = 0``。
  * :func:`camera_response_robertson` — Robertson, Borman & Stevenson (2003) の交互推定
    (放射輝度 ⇄ 逆応答)。全画素を使い、ガウスの重み。
  * :func:`camera_response_linear` — 線形のセンサ(EMVA 1288 で ``K``・暗い時のオフセットを
    測ったもの)の逆応答。
  * :func:`hdr_merge` — 逆応答で各露出を放射輝度に戻して重みつきで合成(対数の重み平均 =
    Debevec、線形の光子数の和 = 散弾雑音の最尤)。
  * :func:`exposure_fusion_mertens` — Mertens, Kautz & Van Reeth (2007): コントラスト・彩度・
    露出の良さの重みを、ラプラシアン・ピラミッドで混ぜる。

Fullseye だけの層 / The layer only Fullseye has:
  * :func:`hdr_exposure_series_simulate` — 既知の放射輝度の場面を、EMVA 1288 の線形モデル
    (量子効率 η・系の利得 K・暗雑音 σ_d・暗いときのオフセット・満杯の電子数・ビット数 =
    散弾雑音・読み出し雑音・飽和・量子化)と任意の非線形の応答で露出の列に撮る。
  * :func:`hdr_radiance_error` — 推定した放射輝度を真値と比べる(倍率 1 つだけを当てて外す)。
  * :func:`hdr_dynamic_range` — HDR の系のダイナミックレンジを**シミュで実測**する
    (EMVA 1288 の定義 DR = μ_p.sat / μ_p.min、SNR = 1 の露光と分散が最大になる露光)、
    並べて閉形式(:func:`sensorchar.emva_sensitivity_threshold` を露出の和に一般化したもの)。

真値(``tests/test_hdrfusion.py`` の門)/ Ground truth:
  * 応答の推定: 既知の γ の応答で撮った列から、推定した ``g`` と真の ``ln`` 逆応答の差
    (定数を外した残差)。放射輝度は倍率を外した相対誤差。
  * 露出融合: 1 枚(または同じ画像 N 枚)はそのまま戻る(ラプラシアン・ピラミッドの再構成は
    厳密)。重みを全部 0 乗にすると N 枚の平均(線形)。
  * ダイナミックレンジ: 露出 1 枚のとき実測が :func:`sensorchar.emva_dynamic_range` の閉形式と
    一致。N 枚では閉形式 ``DR · (Σt / t_min)``(低い側は N 枚の和の SNR = 1)。

GPU: 画素ごとの演算(参照表の引き・重みつきの和・ピラミッド)は numpy と
``scipy.ndimage`` だけで書いてあり、既存の機械的な GPU 化(numpy/scipy を CuPy に差し替える
影のモジュール)にそのまま乗る形。ここでは GPU の測定はしていない。

★正直に書いておくこと / Honest limits:
  * 応答は**グレイ 1 チャンネル**(色ごとに別に推定すること)。融合は RGB も受ける。
  * 推定した放射輝度は**倍率 1 つ**が決まらない(Debevec / Robertson とも)。絶対値が要るなら
    既知の放射輝度の面で 1 点を合わせる。
  * 位置合わせ・動く物体(ゴースト)・レンズのフレアは扱わない(静止した場面を仮定)。
  * 既存の :func:`final_genuine2.radiometric_self_calibration` は HALCON 名の簡易版
    (平均への反復と単調性の強制)で、こちらとは別の算法。並存させる。
  * 既存の :func:`optscene.sensor_capture` は暗いときのオフセットを持たず 0 で切る(暗部の
    雑音が片側に潰れて平均が上へずれる)ので、ダイナミックレンジの実測にはこちらのシミュを使う。

出典 / References: P. E. Debevec, J. Malik, "Recovering high dynamic range radiance maps from
photographs", SIGGRAPH 1997 / M. A. Robertson, S. Borman, R. L. Stevenson, "Estimation-theoretic
approach to dynamic range enhancement using multiple exposures", J. Electron. Imaging 12(2):219–228,
2003 / T. Mertens, J. Kautz, F. Van Reeth, "Exposure fusion", Pacific Graphics 2007 /
P. J. Burt, E. H. Adelson, "The Laplacian pyramid as a compact image code", IEEE Trans. Commun.
31(4):532–540, 1983 / EMVA Standard 1288, Release 4.0 Linear, 2021(式 21・26–28)。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

import sensorchar as _sensorchar

__all__ = [
    "camera_response_debevec",
    "camera_response_robertson",
    "camera_response_linear",
    "hdr_merge",
    "exposure_fusion_mertens",
    "hdr_exposure_series_simulate",
    "hdr_radiance_error",
    "hdr_dynamic_range",
]

#: 量子化の段数の上限(Debevec の正規方程式は段数 + 標本数の大きさ)。
MAX_LEVELS = 1 << 16
MAX_LEVELS_DEBEVEC = 4096
MAX_EXPOSURES = 64
MAX_PIXELS = 1 << 25
_RESP = "camera_response"


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


def _exposures(exposures, n, op):
    t = np.asarray(exposures, dtype=np.float64).reshape(-1)
    if t.size != n:
        raise ValueError("%s: %d exposures for %d images" % (op, t.size, n))
    if not np.isfinite(t).all() or np.any(t <= 0):
        raise ValueError("%s: exposures must be finite and > 0" % op)
    return t


def _stack(images, op, levels=None, allow_rgb=False):
    """画像の列 → (P, H, W[, 3]) の整数の段(Z)と段数。

    float の画像は [0, 1] で、``Z = rint(I · (levels − 1))``。整数の画像はそのまま段
    (``levels`` は 2 以上で、全画素が ``[0, levels − 1]`` に入ること)。
    """
    if isinstance(images, np.ndarray) and images.ndim in (3, 4):
        images = list(images)
    if not isinstance(images, (list, tuple)) or len(images) == 0:
        raise ValueError("%s: images must be a non-empty list of images" % op)
    if len(images) > MAX_EXPOSURES:
        raise ValueError("%s: %d images is over the %d cap" % (op, len(images), MAX_EXPOSURES))
    arrs = []
    for k, im in enumerate(images):
        if np.ma.is_masked(im):
            raise ValueError("%s: image %d is a masked array" % (op, k))
        a = np.asarray(im)
        if a.dtype.kind not in "iuf":
            raise ValueError("%s: image %d has dtype %r — expected real numbers" % (op, k, str(a.dtype)))
        if not (a.ndim == 2 or (allow_rgb and a.ndim == 3 and a.shape[2] == 3)):
            raise ValueError("%s: image %d must be 2-D%s, got shape %s"
                             % (op, k, " or (H, W, 3)" if allow_rgb else "", a.shape))
        if a.size > MAX_PIXELS:
            raise ValueError("%s: image %d has %d values, over the %d cap" % (op, k, a.size, MAX_PIXELS))
        arrs.append(a)
    shp = arrs[0].shape
    if any(a.shape != shp for a in arrs):
        raise ValueError("%s: the images do not all have the same shape" % op)
    if min(shp[:2]) < 2:
        raise ValueError("%s: images must be at least 2x2, got %s" % (op, shp))
    kinds = {a.dtype.kind for a in arrs}
    if levels is None:
        return arrs, None
    if kinds <= {"i", "u"}:
        Z = np.stack(arrs).astype(np.int64)
        if Z.min() < 0 or Z.max() > levels - 1:
            raise ValueError("%s: integer images must lie in [0, levels-1] = [0, %d], got [%d, %d]"
                             % (op, levels - 1, int(Z.min()), int(Z.max())))
        return Z, levels
    F = np.stack([a.astype(np.float64) for a in arrs])
    if not np.isfinite(F).all():
        raise ValueError("%s: images have non-finite values" % op)
    if F.min() < 0.0 or F.max() > 1.0:
        raise ValueError("%s: float images must lie in [0, 1] (got [%g, %g]); pass integer levels "
                         "for raw DN" % (op, float(F.min()), float(F.max())))
    return np.rint(F * (levels - 1)).astype(np.int64), levels


def _hat(levels):
    z = np.arange(levels, dtype=np.float64)
    zmid = 0.5 * (levels - 1)
    return np.where(z <= zmid, z, (levels - 1) - z)


def _gauss_w(levels):
    z = np.arange(levels, dtype=np.float64)
    c = 0.5 * (levels - 1)
    return np.exp(-4.0 * (z - c) ** 2 / (c * c))


def _response(resp, op):
    if not isinstance(resp, dict) or resp.get("kind") != _RESP:
        raise ValueError("%s: expected a camera-response table (kind=%r) from camera_response_*" % (op, _RESP))
    inv = np.asarray(resp.get("inverse"), dtype=np.float64).reshape(-1)
    L = _int(resp.get("levels"), "levels", op, 2, MAX_LEVELS)
    if inv.size != L or not np.isfinite(inv).all():
        raise ValueError("%s: the response's inverse must be %d finite values" % (op, L))
    return inv, L


def _pack_response(inv, method, levels, extra=None):
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.where(inv > 0, np.log(np.where(inv > 0, inv, 1.0)), np.nan)
    out = {"kind": _RESP, "method": method, "levels": int(levels), "inverse": inv, "g": g}
    if extra:
        out.update(extra)
    return out


# --------------------------------------------------------------------------- #
# 1. 応答関数
# --------------------------------------------------------------------------- #
def _sample_pixels(Z, n, rng_seed):
    """標本の画素: 中央の露出の段を n 個に層別して、各層から 1 画素(決定的)。"""
    P = Z.shape[0]
    mid = Z[P // 2].reshape(-1)
    order = np.argsort(mid, kind="stable")
    rng = np.random.default_rng(rng_seed)
    edges = np.linspace(0, order.size, n + 1).astype(int)
    pick = [order[edges[i] + int(rng.integers(0, max(1, edges[i + 1] - edges[i])))] for i in range(n)
            if edges[i + 1] > edges[i]]
    return np.unique(np.asarray(pick, dtype=np.int64))


def camera_response_debevec(images, exposures, levels=256, smoothness=10.0, n_samples=None, seed=0):
    """Inverse camera response from an exposure series by Debevec & Malik's least squares (``table``).

    未知数 = 段ごとの ``g(z) = ln(逆応答)``(``levels`` 個)と標本の画素ごとの ``ln E_i``。
    式 = ``w(Z_ij)[g(Z_ij) − ln E_i − ln t_j] = 0``(全標本 × 全露出)、
    ``smoothness · w(z)(g(z−1) − 2 g(z) + g(z+1)) = 0``(z = 1 .. L−2)、``g((L−1)/2) = 0``。
    重み ``w`` は三角(hat)。標本の画素は中央の露出の段を ``n_samples`` 層に分けて 1 つずつ
    (既定 ``max(50, ⌈2 (L−1)/(P−1)⌉)``、Debevec の条件 ``N (P−1) > L``)。

    ``images``: float in [0, 1] (``Z = rint(I (levels−1))``) or integer levels. ``exposures``: the
    exposure times (any unit; ``g`` is ``ln`` of exposure = irradiance × time in that unit, up to
    one additive constant fixed by ``g(mid) = 0``). Returns ``{"kind": "camera_response",
    "method": "debevec", "levels", "g" (L,), "inverse" (L,) = exp(g), "observed" (L,) bool}``.
    Levels never observed are set by the smoothness term only (``observed`` says which).
    """
    op = "camera_response_debevec"
    L = _int(levels, "levels", op, 2, MAX_LEVELS_DEBEVEC)
    Z, _ = _stack(images, op, levels=L)
    P = Z.shape[0]
    if P < 2:
        raise ValueError("%s: need at least 2 exposures" % op)
    t = _exposures(exposures, P, op)
    lam = _num(smoothness, "smoothness", op, lo=0.0, lo_open=False, hi=1e8)
    n = max(50, int(math.ceil(2.0 * (L - 1) / (P - 1)))) if n_samples is None else _int(
        n_samples, "n_samples", op, 2, 1 << 16)
    idx = _sample_pixels(Z.reshape(P, -1), n, _int(seed, "seed", op, 0, (1 << 63) - 1))
    Zs = Z.reshape(P, -1)[:, idx].T                               # (N, P)
    N = Zs.shape[0]
    w = _hat(L)
    rows_data = N * P
    nrow = rows_data + 1 + (L - 2)
    A = np.zeros((nrow, L + N))
    b = np.zeros(nrow)
    r = np.arange(rows_data)
    zi = Zs.reshape(-1)
    ii = np.repeat(np.arange(N), P)
    jj = np.tile(np.arange(P), N)
    wij = w[zi]
    A[r, zi] = wij
    A[r, L + ii] = -wij
    b[r] = wij * np.log(t[jj])
    A[rows_data, (L - 1) // 2] = 1.0                              # g(中央) = 0
    k = np.arange(1, L - 1)
    rs = rows_data + 1 + np.arange(L - 2)
    A[rs, k - 1] = lam * w[k]
    A[rs, k] = -2.0 * lam * w[k]
    A[rs, k + 1] = lam * w[k]
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    g = sol[:L]
    observed = np.bincount(zi, minlength=L) > 0
    return {"kind": _RESP, "method": "debevec", "levels": L, "g": g, "inverse": np.exp(g),
            "observed": observed, "n_samples": int(N), "smoothness": lam}


def camera_response_robertson(images, exposures, levels=256, max_iter=30, tol=1e-6, max_pixels=200_000):
    """Inverse camera response by Robertson, Borman & Stevenson's alternating estimate (``table``).

    ``E_i = Σ_j w(Z_ij) t_j I(Z_ij) / Σ_j w(Z_ij) t_j²``(放射輝度)と
    ``I(m) = mean{ t_j E_i : Z_ij = m }``(逆応答)を交互に、``I((L−1)/2) = 1`` で正規化して
    相対変化が ``tol`` を切るまで。重みはガウス ``exp(−4 (z − c)²/c²)`` で、両端の段(0 と L−1 =
    真っ黒と飽和)は 0(放射輝度の式が ``w t²`` で重むので、端に残る小さな重みでも飽和した長い露出が
    支配する —— 実測)。画素は ``max_pixels`` 個
    まで等間隔に間引く(決定的)。観測の無い段は隣の段から線形補間。

    Returns the same table as :func:`camera_response_debevec` (``method="robertson"``, with
    ``iterations`` and ``converged``). ★``max_iter=30`` follows OpenCV's ``CalibrateRobertson``
    default. With noisy data the fixed point is biased near both ends (censored pixels just below
    saturation / just above the dark offset): measured on a 5-exposure EMVA series, the ln error at
    level 240 grows from −0.03 (20 iterations) to −0.25 (500) while mid levels stay within 0.02 —
    more iterations is not better. Debevec's smoothness prior does not drift this way. The scale is fixed by ``I(mid) = 1`` (``g(mid) = 0``).
    """
    op = "camera_response_robertson"
    L = _int(levels, "levels", op, 2, MAX_LEVELS)
    Z, _ = _stack(images, op, levels=L)
    P = Z.shape[0]
    if P < 2:
        raise ValueError("%s: need at least 2 exposures" % op)
    t = _exposures(exposures, P, op)
    it = _int(max_iter, "max_iter", op, 1, 10_000)
    tl = _num(tol, "tol", op, lo=0.0)
    mp = _int(max_pixels, "max_pixels", op, 16, MAX_PIXELS)
    Zf = Z.reshape(P, -1)
    stride = max(1, int(math.ceil(Zf.shape[1] / mp)))
    Zf = Zf[:, ::stride]
    w = _gauss_w(L)
    # ★両端(真っ黒・飽和)の重みは 0。ガウスの重みは端で 0.018 残るが、放射輝度の式は w·t² で
    #   重みづけるので、飽和した長い露出(t が 256 倍なら t² は 65536 倍)が支配して応答が波打つ
    #   (雑音なしの列でも ln 誤差 ±0.7、実測)。端を 0 にすると消える。
    w[0] = 0.0
    w[L - 1] = 0.0
    mid = (L - 1) // 2
    Iinv = np.arange(L, dtype=np.float64) / max(mid, 1)
    cnt = np.zeros(L)
    for j in range(P):
        cnt += np.bincount(Zf[j], minlength=L)
    obs = cnt > 0
    if not obs[mid]:
        raise ValueError("%s: the middle level %d is never observed — cannot fix the scale" % (op, mid))
    W = w[Zf]
    T = t[:, None]
    converged = False
    k = 0
    for k in range(1, it + 1):
        num = np.sum(W * T * Iinv[Zf], axis=0)
        den = np.sum(W * T * T, axis=0)
        E = np.where(den > 0, num / np.where(den > 0, den, 1.0), 0.0)
        acc = np.zeros(L)
        for j in range(P):
            acc += np.bincount(Zf[j], weights=t[j] * E, minlength=L)
        new = np.where(obs, acc / np.where(obs, cnt, 1.0), 0.0)
        new = np.interp(np.arange(L), np.nonzero(obs)[0], new[obs])
        if new[mid] <= 0:
            raise ValueError("%s: the middle level's estimate is not positive — degenerate series" % op)
        new = new / new[mid]
        ch = float(np.max(np.abs(new - Iinv)) / max(np.max(np.abs(new)), 1e-300))
        Iinv = new
        if ch < tl:
            converged = True
            break
    return _pack_response(Iinv, "robertson", L, {"observed": obs, "iterations": int(k),
                                                  "converged": converged})


def camera_response_linear(levels=256, dark_offset_dn=0.0, gain_dn_per_unit=1.0):
    """Inverse response of a linear sensor: ``X = (Z − offset) / gain`` (``table``).

    EMVA 1288 で測った系の利得(``K · η`` = DN / 光子、または DN / 任意の単位)と暗いときの
    オフセット [DN] から。逆応答はオフセットより下で負になる(散弾雑音で暗部が負に振れるのを
    そのまま運ぶ —— 線形の合成 ``hdr_merge(weight="linear")`` が偏りなく平均できる)。
    For a sensor characterised by EMVA 1288 (system gain ``K η`` and dark offset). The inverse
    goes negative below the offset on purpose (unbiased averaging in ``hdr_merge(weight="linear")``).
    """
    op = "camera_response_linear"
    L = _int(levels, "levels", op, 2, MAX_LEVELS)
    off = _num(dark_offset_dn, "dark_offset_dn", op, lo=0.0, lo_open=False, hi=L - 1)
    gn = _num(gain_dn_per_unit, "gain_dn_per_unit", op, lo=0.0)
    inv = (np.arange(L, dtype=np.float64) - off) / gn
    return _pack_response(inv, "linear", L, {"dark_offset_dn": off, "gain_dn_per_unit": gn,
                                              "observed": np.ones(L, dtype=bool)})


# --------------------------------------------------------------------------- #
# 2. 合成と融合
# --------------------------------------------------------------------------- #
def hdr_merge(images, exposures, response=None, weight="hat", saturation_margin=1, dark_level=None):
    """Merge an exposure series into a relative radiance map (``image2d``).

    各露出の段 ``Z`` を逆応答 ``X(Z)`` で露光量に戻し、``X / t`` を重みつきで合成する:
      * ``weight="hat"`` / ``"gaussian"``: Debevec の対数の重み平均
        ``ln E = Σ w(Z)(ln X(Z) − ln t) / Σ w(Z)``(``X ≤ 0`` の段は重み 0)。
      * ``weight="hat_time"``: 三角の重みに露出時間 ``t`` を掛ける。散弾雑音が支配するとき
        ``Var(ln X_j) ≈ 1/(η L t_j)`` なので、``t`` に比例する重みが対数の推定の逆分散の重み
        (短い露出の暗い段の雑音を持ち込まない。暗部の傷の CNR が 4 倍、PoC で実測)。
      * ``weight="linear"``: 光子数の和 ``E = Σ X / Σ t``(飽和と ``Z ≥ L−1−margin`` を除く全露出、
        暗部の負の値も含む)。線形のセンサでは散弾雑音の最尤で、暗部も偏らない。
    どの露出でも有効でない画素(全部で飽和 / 全部で真っ暗)は、最短(飽和)/ 最長(真っ暗)の露出
    1 枚の値で埋める(下限 / 上限の推定 —— NaN を返さない約束。``hdr_dynamic_range`` は
    ここで測れる上限を数える)。``response=None`` は「段 = 露光量」の線形(オフセット 0)。
    そのときの段数 ``L`` は float と ``uint8`` で 256、それ以外の整数 dtype(``uint16`` に
    入った 12 bit のセンサ値など、満の値が dtype から決まらないもの)は**系列の最大値 + 1**
    ―― つまり系列で最も明るい段を飽和とみなす。満の値が分かっているなら
    ``camera_response_*`` の応答表(``levels``)を渡すこと。
    三角の重みは ``[dark_level, L−1]`` に張る(既定 = 逆応答が初めて正になる段。暗いときの
    オフセットを持つセンサで、オフセットのすぐ上の雑音だらけの段に重みを与えないため)。

    Returns radiance in ``inverse``-units per exposure-time unit (relative: Debevec/Robertson fix
    only the scale ``g(mid) = 0``). ★Assumes a static scene and registered frames.
    """
    op = "hdr_merge"
    if response is None:
        arrs, _ = _stack(images, op)
        # ★2026-11-05(敵対的検証 第 2 巡): uint8 でも段数を「データの最大値 + 1」にしていたので、
        # どの露出も飽和していない系列で**最も明るい画素が飽和扱い**になり(Z >= L-1-margin)、
        # 三角の重みも実際の段の幅でなくデータの幅に張られていた(未飽和の uint8 系列で
        # 相対誤差の中央値が 256 段の 0.50 % に対し 0.69 %)。uint8 は満の値が 255 に決まるので 256 段。
        # uint16 などは 10/12/14 bit のセンサ値を入れるのが普通で満の値が dtype から
        # 決まらないため、従来どおりデータの最大値 + 1(= 最も明るい段を飽和とみなす)。
        if all(a.dtype.kind == "f" for a in arrs) or all(a.dtype == np.uint8 for a in arrs):
            L = 256
        else:
            L = int(max(int(np.max(a)) for a in arrs) + 1)
        inv = np.arange(L, dtype=np.float64)
    else:
        inv, L = _response(response, op)
    Z, _ = _stack(images, op, levels=L)
    P = Z.shape[0]
    t = _exposures(exposures, P, op)
    if weight not in ("hat", "hat_time", "gaussian", "linear"):
        raise ValueError("%s: weight must be 'hat', 'hat_time', 'gaussian' or 'linear'" % op)
    m = _int(saturation_margin, "saturation_margin", op, 0, L - 2)
    X = inv[Z]                                                    # (P, H, W)
    T = t.reshape((P,) + (1,) * (Z.ndim - 1))
    sat = Z >= (L - 1 - m)
    order = np.argsort(t)
    shortest, longest = order[0], order[-1]
    if weight == "linear":
        ok = ~sat
        num = np.sum(np.where(ok, X, 0.0), axis=0)
        den = np.sum(np.where(ok, T, 0.0), axis=0)
        E = np.where(den > 0, num / np.where(den > 0, den, 1.0), X[shortest] / t[shortest])
        return E
    if dark_level is None:
        posl = np.nonzero(inv > 0)[0]
        z0 = int(posl[0]) if posl.size else 0
    else:
        z0 = _int(dark_level, "dark_level", op, 0, L - 2)
    zz = np.arange(L, dtype=np.float64)
    if weight in ("hat", "hat_time"):
        wl = np.clip(np.minimum(zz - z0, (L - 1) - zz), 0.0, None)
    else:
        c = 0.5 * (z0 + L - 1)
        hw = 0.5 * (L - 1 - z0)
        wl = np.where(zz >= z0, np.exp(-4.0 * (zz - c) ** 2 / (hw * hw)), 0.0)
    w = wl[Z]
    if weight == "hat_time":
        w = w * T                                                 # 散弾雑音では Var(ln X_j) ≈ 1/(η L t_j)
    pos = X > 0
    w = np.where(pos & ~sat, w, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        lnE = np.where(pos, np.log(np.where(pos, X, 1.0)), 0.0) - np.log(T)
    sw = w.sum(axis=0)
    lnm = np.sum(w * lnE, axis=0) / np.where(sw > 0, sw, 1.0)
    # 重みが 0 の画素: 段が高ければ最短の露出、低ければ最長の露出 1 枚(正でなければ最小の正の値)
    pmin = float(inv[inv > 0].min()) if np.any(inv > 0) else 1.0
    hi_fb = np.log(np.maximum(X[shortest], pmin)) - math.log(t[shortest])
    lo_fb = np.log(np.maximum(X[longest], pmin)) - math.log(t[longest])
    high = Z[shortest] > 0.5 * (L - 1)
    lnm = np.where(sw > 0, lnm, np.where(high, hi_fb, lo_fb))
    return np.exp(lnm)


def _pyr_kernel():
    return np.array([1.0, 4.0, 6.0, 4.0, 1.0]) / 16.0         # Burt & Adelson の 5 タップ


def _reduce(a):
    k = _pyr_kernel()
    b = ndimage.convolve1d(a, k, axis=0, mode="mirror")
    b = ndimage.convolve1d(b, k, axis=1, mode="mirror")
    return b[::2, ::2]


def _expand(a, shape):
    k = _pyr_kernel() * 2.0
    up = np.zeros((shape[0], shape[1]) + a.shape[2:], dtype=a.dtype)
    up[::2, ::2] = a[: (shape[0] + 1) // 2, : (shape[1] + 1) // 2]
    # ★mode="mirror"(d c b | a b c d)。"reflect"(d c b a | a b c d)だと 0 を挟んだ格子の偶奇が端で
    #   ずれ、端の画素の重みの和が 11/8 になって融合の端が 37 % 明るく飛ぶ(図で発見、2026-11-03)。
    up = ndimage.convolve1d(up, k, axis=0, mode="mirror")
    return ndimage.convolve1d(up, k, axis=1, mode="mirror")


def exposure_fusion_mertens(images, contrast_weight=1.0, saturation_weight=1.0, exposedness_weight=1.0,
                            sigma=0.2, n_levels=None):
    """Fuse an exposure series directly into one well-exposed image (``image2d``; RGB lists also work).

    重み ``W = C^wc · S^ws · E^we``: C = 灰色のラプラシアンの絶対値、S = 色の 3 チャンネルの
    標準偏差(灰色の画像では 1)、E = ``exp(−(I − 0.5)² / (2 σ²))``(色はチャンネルの積)。
    画素ごとに N 枚の和を 1 に正規化し、重みのガウス・ピラミッドで画像のラプラシアン・
    ピラミッドを混ぜて畳む(Mertens ら 2007、Burt & Adelson 1983)。結果は [0, 1] に切る。

    Images: float in [0, 1], 2-D or (H, W, 3), same shape. ``n_levels`` defaults to
    ``⌊log2 min(H, W)⌋``. Ground truth: one image (or N copies) comes back unchanged (the
    pyramid reconstruction is exact); with all three exponents 0 the result is the plain mean.
    ★The output is clipped to [0, 1] (the blend can overshoot slightly at strong edges).
    """
    op = "exposure_fusion_mertens"
    arrs, _ = _stack(images, op, allow_rgb=True)
    F = np.stack([a.astype(np.float64) for a in arrs])
    if not np.isfinite(F).all() or F.min() < 0.0 or F.max() > 1.0:
        raise ValueError("%s: images must be finite floats in [0, 1]" % op)
    wc = _num(contrast_weight, "contrast_weight", op, lo=0.0, lo_open=False, hi=100.0)
    ws = _num(saturation_weight, "saturation_weight", op, lo=0.0, lo_open=False, hi=100.0)
    we = _num(exposedness_weight, "exposedness_weight", op, lo=0.0, lo_open=False, hi=100.0)
    sg = _num(sigma, "sigma", op, lo=0.0, hi=10.0)
    color = F.ndim == 4
    H, W = F.shape[1:3]
    nl = int(math.floor(math.log2(min(H, W)))) if n_levels is None else _int(n_levels, "n_levels", op, 1, 32)
    nl = max(1, min(nl, int(math.floor(math.log2(min(H, W)))) + 1))
    gray = F.mean(axis=-1) if color else F
    Wt = np.ones(gray.shape)
    if wc > 0:
        C = np.abs(np.stack([ndimage.laplace(g, mode="reflect") for g in gray]))
        Wt = Wt * C ** wc
    if ws > 0 and color:
        Wt = Wt * F.std(axis=-1) ** ws
    if we > 0:
        Ex = np.exp(-((F - 0.5) ** 2) / (2.0 * sg * sg))
        Ex = Ex.prod(axis=-1) if color else Ex
        Wt = Wt * Ex ** we
    Wt = Wt + 1e-12
    Wt = Wt / Wt.sum(axis=0, keepdims=True)
    fused = None
    for k in range(F.shape[0]):
        # 画像のラプラシアン・ピラミッド
        gp = [F[k]]
        wp = [Wt[k]]
        for _ in range(nl - 1):
            gp.append(_reduce(gp[-1]))
            wp.append(_reduce(wp[-1]))
        lp = [gp[i] - _expand(gp[i + 1], gp[i].shape) for i in range(nl - 1)] + [gp[-1]]
        part = [lp[i] * (wp[i][..., None] if color else wp[i]) for i in range(nl)]
        fused = part if fused is None else [a + b for a, b in zip(fused, part)]
    out = fused[-1]
    for i in range(nl - 2, -1, -1):
        out = fused[i] + _expand(out, fused[i].shape)
    return np.clip(out, 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 3. Fullseye だけの層: 真値つきの露出列・誤差・ダイナミックレンジ
# --------------------------------------------------------------------------- #
def _sensor_params(op, eta, K, sigma_d_e, dark_offset_dn, bits, full_well_e):
    e = _num(eta, "eta", op, lo=0.0, hi=1.0)
    k = _num(K, "K", op, lo=0.0, hi=1e6)
    sd = _num(sigma_d_e, "sigma_d_e", op, lo=0.0, lo_open=False, hi=1e9)
    b = _int(bits, "bits", op, 1, 16)
    off = _num(dark_offset_dn, "dark_offset_dn", op, lo=0.0, lo_open=False, hi=(1 << b) - 1)
    fw = None if full_well_e is None else _num(full_well_e, "full_well_e", op, lo=0.0, hi=1e12)
    return e, k, sd, off, b, fw


def _capture(mu_p, t, e, k, sd, off, b, fw, gamma, rng):
    """EMVA 1288 の線形モデルで 1 枚: 光子 → Poisson の電子 → 暗雑音 → 飽和 → DN → 応答 → 量子化。"""
    el = rng.poisson(np.minimum(e * mu_p * t, 1e15)).astype(np.float64)
    if fw is not None:
        el = np.minimum(el, fw)
    y = off + k * (el + (rng.normal(0.0, sd, el.shape) if sd > 0 else 0.0))
    top = float((1 << b) - 1)
    x = np.clip(y, 0.0, top) / top
    if gamma != 1.0:
        x = x ** (1.0 / gamma)
    return np.rint(x * top).astype(np.int64)


def hdr_exposure_series_simulate(radiance, exposures, eta=0.6, K=0.1, sigma_d_e=8.0, dark_offset_dn=4.0,
                                 bits=8, full_well_e=None, gamma=1.0, seed=0, as_float=True):
    """Shoot a known-radiance scene as an exposure series with an EMVA 1288 sensor model (``images``).

    ``radiance`` = 画素あたり・時間の単位あたりの光子数 ``μ_p / t``(既知の真値)。各露出 ``t`` で
    電子 ``~ Poisson(η μ_p t)``(満杯 ``full_well_e`` で頭打ち)、暗雑音 ``N(0, σ_d²)`` [e⁻]、
    ``y = offset + K (電子 + 暗雑音)`` [DN]、``[0, 2^bits − 1]`` で切り(飽和)、応答
    ``x^(1/γ)``(``γ = 1`` は線形 = EMVA の線形モデルそのもの)、量子化。
    ``as_float=True`` は ``Z / (2^bits − 1)``(``hdr_merge`` 等が ``levels = 2^bits`` で正確に段に戻す)、
    ``False`` は整数の段。``seed`` を固定すれば決定的(露出ごとに別の乱数列)。

    The true inverse response for ``γ`` is ``X(Z) = ((2^b−1)(Z/(2^b−1))^γ − offset) / (K η)``
    photons (the mean, ignoring quantisation). Ground truth: with ``γ = 1`` the photon transfer
    (``var_y`` vs ``μ_y``) of the output has slope ``K`` (:func:`sensorchar.emva_photon_transfer`).
    """
    op = "hdr_exposure_series_simulate"
    r = np.asarray(radiance, dtype=np.float64)
    if r.ndim != 2 or r.size == 0 or not np.isfinite(r).all() or np.any(r < 0):
        raise ValueError("%s: radiance must be a finite, non-negative 2-D array" % op)
    if r.size > MAX_PIXELS:
        raise ValueError("%s: radiance has %d pixels, over the %d cap" % (op, r.size, MAX_PIXELS))
    t = np.asarray(exposures, dtype=np.float64).reshape(-1)
    if t.size == 0 or t.size > MAX_EXPOSURES or not np.isfinite(t).all() or np.any(t <= 0):
        raise ValueError("%s: exposures must be 1..%d finite times > 0" % (op, MAX_EXPOSURES))
    e, k, sd, off, b, fw = _sensor_params(op, eta, K, sigma_d_e, dark_offset_dn, bits, full_well_e)
    gm = _num(gamma, "gamma", op, lo=0.05, hi=20.0)
    rng = np.random.default_rng(_int(seed, "seed", op, 0, (1 << 63) - 1))
    top = float((1 << b) - 1)
    out = []
    for tj in t:
        Z = _capture(r, float(tj), e, k, sd, off, b, fw, gm, rng)
        out.append(Z / top if as_float else Z)
    return out


def hdr_radiance_error(estimate, truth, mask=None, fit_scale=True):
    """Error of an estimated radiance map against the true one, after one fitted scale (``table``).

    Debevec / Robertson の放射輝度は倍率が決まらないので、``ln`` の差の中央値で倍率 1 つを当てて
    外す(``fit_scale=False`` で外さない)。返り: ``scale``、相対誤差 ``|est·s/truth − 1|`` の
    ``rms`` / ``median`` / ``p95`` / ``max``、``log10`` の差の ``rms``、使った画素数。
    真値が 0 以下・推定が 0 以下の画素は使わない(``n_excluded`` に数える)。
    """
    op = "hdr_radiance_error"
    E = np.asarray(estimate, dtype=np.float64)
    T = np.asarray(truth, dtype=np.float64)
    if E.shape != T.shape or E.ndim != 2:
        raise ValueError("%s: estimate and truth must be 2-D arrays of the same shape" % op)
    if not (np.isfinite(E).all() and np.isfinite(T).all()):
        raise ValueError("%s: estimate / truth have non-finite values" % op)
    m = (E > 0) & (T > 0)
    if mask is not None:
        mk = np.asarray(mask)
        if mk.shape != E.shape:
            raise ValueError("%s: mask must have the image's shape" % op)
        m &= mk.astype(bool)
    n = int(np.count_nonzero(m))
    if n == 0:
        raise ValueError("%s: no pixel with positive estimate and truth" % op)
    d = np.log(E[m]) - np.log(T[m])
    s = float(np.exp(-np.median(d))) if fit_scale else 1.0
    rel = np.abs(E[m] * s / T[m] - 1.0)
    l10 = (d + math.log(s)) / math.log(10.0)
    return {"scale": s, "rms_rel": float(np.sqrt(np.mean(rel * rel))), "median_rel": float(np.median(rel)),
            "p95_rel": float(np.percentile(rel, 95)), "max_rel": float(rel.max()),
            "rms_log10": float(np.sqrt(np.mean(l10 * l10))), "n_pixels": n,
            "n_excluded": int(E.size - n)}


def _variance_max_exposure(k, sd, off, clip_dn, x_clip):
    """打ち切り正規 ``min(N(m, s²), c)`` の分散が最大になる電子数(閉形式の打ち切りの積率を格子で最大化)。

    m = off + K x、s² = K²(σ_d² + x) + 1/12。E[X] = mΦ(α) − sφ(α) + c(1 − Φ(α))、
    E[X²] = (m² + s²)Φ(α) − s(m + c)φ(α) + c²(1 − Φ(α))、α = (c − m)/s。
    """
    from scipy.special import ndtr  # noqa: PLC0415
    x = np.linspace(0.7 * x_clip, 1.1 * x_clip, 8001)
    m = off + k * x
    s = np.sqrt(k * k * (sd * sd + x) + _sensorchar.SIGMA_Q2)
    a = (clip_dn - m) / s
    Phi = ndtr(a)
    phi = np.exp(-0.5 * a * a) / math.sqrt(2.0 * math.pi)
    ex = m * Phi - s * phi + clip_dn * (1.0 - Phi)
    ex2 = (m * m + s * s) * Phi - s * (m + clip_dn) * phi + clip_dn * clip_dn * (1.0 - Phi)
    return float(x[int(np.argmax(ex2 - ex * ex))])


def _snr_one_crossing(L, snr):
    """SNR が初めて 1 を上に切る L(log–log の線形補間)。無ければ NaN。"""
    above = np.nonzero(snr >= 1.0)[0]
    if above.size == 0 or above[0] == 0:
        return float("nan")
    i = int(above[0])
    x0, x1 = math.log(L[i - 1]), math.log(L[i])
    y0, y1 = math.log(max(snr[i - 1], 1e-300)), math.log(snr[i])
    return float(math.exp(x0 + (0.0 - y0) * (x1 - x0) / (y1 - y0)))


def hdr_dynamic_range(exposures, eta=0.6, K=0.1, sigma_d_e=8.0, dark_offset_dn=4.0, bits=8,
                      full_well_e=None, n_frames=400, n_levels=97, decades=None, seed=0):
    """Measured dynamic range of an HDR capture (EMVA 1288 definition) with its closed form (``table``).

    シミュで実測: 放射輝度の等比の階段(``n_levels`` 段、各段 ``n_frames`` 画素 = 繰り返し)を
    :func:`hdr_exposure_series_simulate`(線形、γ = 1)で露出の列に撮り、
    :func:`hdr_merge`(``weight="linear"``、真の線形の逆応答)で合成し、段ごとに SNR = 平均 / 標準偏差。
      * ``L_min``: SNR が 1 を切る放射輝度(EMVA 1288 の絶対感度しきい値の HDR 版)。
      * ``L_sat``: 最短の露出の出力の**分散が最大**になる放射輝度(EMVA の飽和の定義)を、粗い
        階段で見つけた最大の段のまわりを細かい階段で測り直して決める。
      * ``dr = L_sat / L_min``、``dr_db = 20 log10``、``dr_bits = log2``。
    閉形式(並べて返す): 低い側は全露出の和の SNR = 1 ——
    :func:`sensorchar.emva_sensitivity_threshold` に ``σ_d → √P σ_d``、``K → K/√P`` を入れた
    ``μ_p.min`` を ``Σ t`` で割る。高い側は最短の露出が ``2^bits − 1``(または満杯)に届く放射輝度。
    露出 1 枚ならそのまま :func:`sensorchar.emva_dynamic_range`。

    Measured in simulation (EMVA 1288 definitions: SNR = 1 and the maximum of the variance), with
    the closed form side by side. The closed-form saturation is the maximum of the variance of a
    clipped Gaussian ``min(N(μ, σ²(μ)), c)`` with ``σ² = K²(σ_d² + μ_e) + 1/12`` (exact censored-
    normal moments); ``L_clip_closed_form`` is the plain clip point of the mean, about 5 % higher
    (measured). ★Full-well clipping is approximated as a DN clip at ``offset + K·full_well``.
    """
    op = "hdr_dynamic_range"
    t = np.asarray(exposures, dtype=np.float64).reshape(-1)
    if t.size == 0 or t.size > MAX_EXPOSURES or not np.isfinite(t).all() or np.any(t <= 0):
        raise ValueError("%s: exposures must be 1..%d finite times > 0" % (op, MAX_EXPOSURES))
    e, k, sd, off, b, fw = _sensor_params(op, eta, K, sigma_d_e, dark_offset_dn, bits, full_well_e)
    nf = _int(n_frames, "n_frames", op, 16, 1 << 20)
    nl = _int(n_levels, "n_levels", op, 8, 4096)
    sdd = _int(seed, "seed", op, 0, (1 << 62))
    P = t.size
    T = float(t.sum())
    tmin = float(t.min())
    q2 = _sensorchar.SIGMA_Q2
    thr = _sensorchar.emva_sensitivity_threshold(e, math.sqrt(P) * sd, k / math.sqrt(P), sigma_q2=q2)
    Lmin_cf = thr["mu_p_min"] / T
    top = float((1 << b) - 1)
    xsat = (top - off) / k                                       # 飽和の電子数(DN の頭)
    if fw is not None:
        xsat = min(xsat, fw)
    Lsat_cf = xsat / e / tmin
    Lsat_var_cf = _variance_max_exposure(k, sd, off, top if fw is None else min(top, off + k * fw), xsat) / e / tmin
    if not Lsat_cf > Lmin_cf:
        raise ValueError("%s: the saturation (%g) is below the threshold (%g) — no dynamic range" % (op, Lsat_cf, Lmin_cf))
    dec = math.log10(Lsat_cf / Lmin_cf) + 1.6 if decades is None else _num(decades, "decades", op, lo=0.5, hi=20.0)
    Ls = Lmin_cf * 10.0 ** np.linspace(-0.8, dec - 0.8, nl)
    resp = camera_response_linear(1 << b, off, k * e)
    rad = np.repeat(Ls[:, None], nf, axis=1)
    imgs = hdr_exposure_series_simulate(rad, t, e, k, sd, off, b, fw, gamma=1.0, seed=sdd, as_float=False)
    Em = hdr_merge(imgs, t, response=resp, weight="linear", saturation_margin=0)
    mu = Em.mean(axis=1)
    sg = Em.std(axis=1, ddof=1)
    snr = np.where(sg > 0, mu / np.where(sg > 0, sg, 1.0), np.inf)
    Lmin = _snr_one_crossing(Ls, snr)
    # 飽和: 最短の露出の出力の分散が最大の段(粗)→ そのまわり ±1 段を細かく(31 段)
    js = int(np.argmin(t))
    var_s = np.asarray(imgs[js], dtype=np.float64).var(axis=1, ddof=1)
    i = int(np.argmax(var_s))
    lo_, hi_ = Ls[max(i - 1, 0)], Ls[min(i + 1, nl - 1)]
    Lf = np.exp(np.linspace(math.log(lo_), math.log(hi_), 31))
    rad_f = np.repeat(Lf[:, None], nf, axis=1)
    nff = max(nf, 8000)                                          # 分散の最大は平らなので、細かい側は標本を多く
    rad_f = np.repeat(Lf[:, None], nff, axis=1)
    Zf = hdr_exposure_series_simulate(rad_f, [tmin], e, k, sd, off, b, fw, gamma=1.0, seed=sdd + 1,
                                      as_float=False)[0].astype(np.float64)
    vf = Zf.var(axis=1, ddof=1)
    Lsat = float(Lf[int(np.argmax(vf))])
    dr = Lsat / Lmin if Lmin == Lmin and Lmin > 0 else float("nan")
    dr_cf = Lsat_var_cf / Lmin_cf
    return {"dr": dr, "dr_db": 20.0 * math.log10(dr) if dr == dr else float("nan"),
            "dr_bits": math.log2(dr) if dr == dr else float("nan"),
            "L_min": Lmin, "L_sat": Lsat,
            "dr_closed_form": dr_cf, "dr_db_closed_form": 20.0 * math.log10(dr_cf),
            "L_min_closed_form": Lmin_cf, "L_sat_closed_form": Lsat_var_cf, "L_clip_closed_form": Lsat_cf,
            "ratio_measured_to_closed_form": dr / dr_cf if dr == dr else float("nan"),
            "levels": Ls, "snr": snr, "exposures": t, "n_frames": nf,
            "definition": "EMVA 1288: DR = mu_p.sat / mu_p.min (SNR = 1; maximum of the variance)",
            "source": "EMVA Standard 1288 Release 4.0 Linear (eqs. 21, 26-28), generalised to the "
                      "sum of P exposures"}

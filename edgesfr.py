# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""edgesfr — 刃のエッジの写真から解像(SFR/MTF)を、黒点の写真から迷光(ベーリンググレア指数)を測る。

`optics.psf_to_mtf` は「PSF を持っている人」向けで、検査の現場が持っているのは**刃のエッジの写真**と
**黒い点を白地に置いた写真**である。この 4 op はその写真から直接測る(`poc_veiling_glare` の 8 節 (a) の穴):

* :func:`edge_spread` — ISO 12233 の傾いたエッジ法。行ごとにエッジの位置を出して直線を当て、画素を
  エッジからの**垂直距離**で 1/oversample px の升に振り分けて ESF(エッジ拡がり関数)を作る。
  エッジを少し(2〜20°)傾けると、画素の中心がエッジに対していろいろな位相に来るので、画素より細かい ESF が取れる。
* :func:`sfr_from_edge` — ESF を窓 ±window px で切り、両端の平均で黒/白に正規化し、前進差分で LSF にし、
  フーリエ変換の絶対値で SFR(= エッジから測る MTF)を出す。
* :func:`mtf50` — SFR が 0.5 を最初に切る周波数。
* :func:`veiling_glare_index` — ISO 9358 の考え方: 一様な白地に置いた黒い点の中心の明るさ / 白地の明るさ。

★**窓の幅・補正・黒点の範囲は必須の引数にしてある**(既定値を静かに選ばない)。`poc_veiling_glare` の実測:
同じレンズで窓 ±16 px の SFR は MTF50 が 4 % しか動かないのに、黒レベルは 0 → 16 % に悪化する ——
SFR は窓の両端を黒/白の基準に使うので、迷光(裾に逃げた光)が約分されて消える。黒点の一辺を 16 → 256 px に
変えると同じレンズの黒レベルは 19.6 % → 4.5 %。どちらも「測る範囲」を宣言しない限り数字に意味が無い。

真値(tests/test_edgesfr.py):
* ガウスでぼかしたエッジ(点標本)の SFR は閉形式 exp(−2π²σ²f²)、MTF50 = √(ln 2 / (2π²σ²))。
* 角度の推定は描いた角度と一致し、エッジの向き(暗→明 / 明→暗)と 90° の回転で SFR は変わらない。
* 一様な光幕 g を足した像 (1−g)·scene + g で VGI = g(厳密)、SFR は不変(迷光が約分される所見そのもの)。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = ["edge_spread", "sfr_from_edge", "mtf50", "veiling_glare_index"]

_MAX_PIXELS = 64_000_000
_CORRECTIONS = ("none", "derivative", "derivative+bin")


def _image(img, name, fn):
    a = np.asarray(img)
    if a.dtype == object or np.iscomplexobj(a) or isinstance(img, np.ma.MaskedArray):
        raise ValueError("%s: %s must be a real 2-D array (got dtype %s)" % (fn, name, a.dtype))
    if a.ndim != 2:
        raise ValueError("%s: %s must be 2-D (got shape %r)" % (fn, name, a.shape))
    if a.size > _MAX_PIXELS:
        raise ValueError("%s: %s has %d pixels, over the cap %d" % (fn, name, a.size, _MAX_PIXELS))
    a = a.astype(np.float64)
    if not np.isfinite(a).all():
        raise ValueError("%s: %s contains NaN or inf" % (fn, name))
    return a


def _roi(roi, shape, fn):
    try:
        y0, y1, x0, x1 = (int(v) for v in roi)
    except (TypeError, ValueError):
        raise ValueError("%s: roi must be (y0, y1, x0, x1) integers (got %r)" % (fn, roi)) from None
    h, w = shape
    if not (0 <= y0 < y1 <= h and 0 <= x0 < x1 <= w):
        raise ValueError("%s: roi %r is outside the image %dx%d or empty" % (fn, (y0, y1, x0, x1), h, w))
    return y0, y1, x0, x1


def edge_spread(img, roi, *, oversample=4, orientation="auto"):
    """傾いたエッジ(ISO 12233)の ROI から、画素より細かい ESF を作る。

    手順: ROI を「エッジが行を横切る」向きにそろえる(``orientation="auto"`` は列方向と行方向の勾配の大きさで決める、
    ``"vertical"`` = エッジが縦に走る / ``"horizontal"`` = 横に走る)→ 行ごとに 1 階差分の重心でエッジの位置を出す →
    位置を行番号に直線で当てる(最小二乗)→ 各画素の中心のエッジからの**垂直距離** d を出し、幅 1/oversample px の升に
    振り分けて平均する。

    返り値 ``{"x": 升の中心の距離 [px](エッジに垂直), "esf": 升の平均, "count": 升の画素数, "angle_deg": エッジの傾き
    (行に対する、符号つき), "oversample", "orientation": 使った向き, "edge_x0": ROI の 0 行目でのエッジの位置 [px]}``。

    ★傾きが小さすぎる(画素の位相が升を埋めない)と空の升が出る —— **黙って補間しない**で ``ValueError``。
    ISO 12233 が 2〜10° 程度の傾きを求めるのはこのため。傾きが 45° を越えるなら ``orientation`` が逆。

    **Raises** ``ValueError``: 画像が 2-D の実数でない / NaN・inf / roi が画像の外・空・4 行 × 8 列未満 /
    oversample が 1〜16 の整数でない / 行の中にエッジ(差分の変化)が無い / 傾きが 45° 以上 / 空の升が出た。
    """
    fn = "edge_spread"
    a = _image(img, "img", fn)
    y0, y1, x0, x1 = _roi(roi, a.shape, fn)
    if isinstance(oversample, bool) or not isinstance(oversample, (int, np.integer)) or not (1 <= int(oversample) <= 16):
        raise ValueError("%s: oversample must be an integer in [1, 16] (got %r)" % (fn, oversample))
    q = int(oversample)
    r = a[y0:y1, x0:x1]
    if orientation not in ("auto", "vertical", "horizontal"):
        raise ValueError("%s: orientation must be 'auto', 'vertical' or 'horizontal' (got %r)" % (fn, orientation))
    if orientation == "auto":
        gx = float(np.abs(np.diff(r, axis=1)).sum())
        gy = float(np.abs(np.diff(r, axis=0)).sum())
        orientation = "vertical" if gx >= gy else "horizontal"
    if orientation == "horizontal":
        r = r.T
    n_rows, n_cols = r.shape
    if n_rows < 4 or n_cols < 8:
        raise ValueError("%s: the ROI across the edge must be at least 4 rows x 8 columns (got %dx%d)" % (fn, n_rows, n_cols))
    d = np.abs(np.diff(r, axis=1))                   # 列の間(位置 j + 0.5)の差分
    s = d.sum(axis=1)
    if not (s > 0).all():
        raise ValueError("%s: %d of %d rows have no edge (constant along the row)" % (fn, int((s <= 0).sum()), n_rows))
    xc = (d * (np.arange(n_cols - 1) + 0.5)[None, :]).sum(axis=1) / s   # 行ごとのエッジの位置(重心)
    yy = np.arange(n_rows, dtype=np.float64)
    slope, icpt = np.polyfit(yy, xc, 1)             # x_edge(y) = icpt + slope · y
    if abs(slope) >= 1.0:
        raise ValueError("%s: the edge is tilted %.1f deg from the rows — use the other orientation" % (fn, math.degrees(math.atan(slope))))
    cos_t = 1.0 / math.hypot(1.0, slope)
    jj, ii = np.meshgrid(np.arange(n_cols, dtype=np.float64), yy)
    dist = (jj - (icpt + slope * ii)) * cos_t       # エッジからの垂直距離 [px]
    k = np.floor(dist * q).astype(np.int64)
    kmin = int(k.min())
    idx = (k - kmin).ravel()
    nb = int(idx.max()) + 1
    cnt = np.bincount(idx, minlength=nb)
    tot = np.bincount(idx, weights=r.ravel(), minlength=nb)
    # 端の升は画素が薄い(ROI の角)。両端から連続する空/薄い升は切り落とし、内側の空の升だけを欠陥として止める。
    ok = np.nonzero(cnt > 0)[0]
    lo_b, hi_b = int(ok[0]), int(ok[-1])
    inner = cnt[lo_b:hi_b + 1]
    if (inner == 0).any():
        raise ValueError("%s: %d empty bins inside the ESF at oversample %d — the edge is tilted only %.2f deg; "
                         "tilt it more (2-10 deg) or lower oversample" % (fn, int((inner == 0).sum()), q, math.degrees(math.atan(slope))))
    xs = (np.arange(lo_b, hi_b + 1) + kmin + 0.5) / q
    esf = tot[lo_b:hi_b + 1] / inner
    return {"x": xs, "esf": esf, "count": inner.astype(np.int64), "angle_deg": math.degrees(math.atan(slope)),
            "oversample": q, "orientation": orientation, "edge_x0": float(icpt)}


def sfr_from_edge(esf, window, *, correction, ends=1.0, apodize="none"):
    """ESF から SFR(エッジから測る MTF)を出す。

    *esf* は :func:`edge_spread` の返り値(辞書)か、1 px 刻みの 1-D 配列(``oversample`` = 1 とみなす)。
    エッジの中心(差分の絶対値の最大)から ±*window* px を切り、両端 *ends* px の平均を黒/白の基準に正規化し、
    前進差分で LSF にしてフーリエ変換の絶対値を DC で割る。

    *window*(必須、px): 切り出す半幅。★迷光(裾)は窓の外に居るので、窓を狭くするほど SFR から見えなくなる。
    *correction*(必須): 標本化が作る sinc の割り戻し。
      ``"none"`` — 割り戻さない(離散の段差を離散の PSF で畳んだ像なら前進差分が離散 LSF そのもので、これが正しい)。
      ``"derivative"`` — 連続のエッジを点で標本した ESF の前進差分は幅 Δ の箱で LSF を均すので sinc(fΔ) で割る。
      ``"derivative+bin"`` — :func:`edge_spread` の升(幅 Δ)の平均がもう 1 つの箱なので sinc(fΔ)² で割る。
    *apodize*: ``"none"`` か ``"hamming"``(ISO 12233:2017 の LSF の窓)。

    返り値 ``(n, 2)`` の pairs: 列 0 = 周波数 [cyc/px](エッジに垂直)、列 1 = SFR。0 〜 min(1.0, 0.5/Δ) cyc/px
    (升の刻み Δ の Nyquist まで、ただし画素の Nyquist の 2 倍 = 1 cyc/px で打ち切る。その先は sinc の割り戻しが暴れる)。

    **Raises** ``ValueError``: esf が空・NaN / window が正の有限でない・ESF の長さを越える / ends が window 以上 /
    correction・apodize が一覧に無い / 黒と白の基準が等しい(エッジが無い)。
    """
    fn = "sfr_from_edge"
    if correction not in _CORRECTIONS:
        raise ValueError("%s: correction must be one of %r (got %r) — choose it from how the ESF was made" % (fn, _CORRECTIONS, correction))
    if apodize not in ("none", "hamming"):
        raise ValueError("%s: apodize must be 'none' or 'hamming' (got %r)" % (fn, apodize))
    if isinstance(esf, dict):
        x = np.asarray(esf["x"], np.float64)
        e = np.asarray(esf["esf"], np.float64)
        q = int(esf.get("oversample", 1))
    else:
        e = np.asarray(esf, np.float64)
        if e.ndim != 1:
            raise ValueError("%s: a bare esf must be 1-D (got shape %r)" % (fn, e.shape))
        x = np.arange(e.size, dtype=np.float64)
        q = 1
    if e.size < 4 or not np.isfinite(e).all() or not np.isfinite(x).all():
        raise ValueError("%s: the ESF must have at least 4 finite samples" % fn)
    dx = 1.0 / q
    try:
        w = float(window)
        en = float(ends)
    except (TypeError, ValueError):
        raise ValueError("%s: window and ends must be numbers (got %r, %r)" % (fn, window, ends)) from None
    if not (math.isfinite(w) and w > 0):
        raise ValueError("%s: window must be a positive number of pixels (got %r)" % (fn, window))
    if not (math.isfinite(en) and 0 < en < w):
        raise ValueError("%s: ends must be in (0, window) pixels (got %r with window %r)" % (fn, ends, window))
    c = int(np.argmax(np.abs(np.diff(e))))           # 差分 c は x[c] と x[c+1] の間
    xc = 0.5 * (x[c] + x[c + 1])
    m = np.abs(x - xc) <= w
    if m.sum() < 4 or x[m][0] > xc - w + dx or x[m][-1] < xc + w - dx:
        raise ValueError("%s: window ±%g px runs past the ESF (%.2f..%.2f px around the edge at %.2f)" % (fn, w, x[0], x[-1], xc))
    seg, xs = e[m], x[m]
    n_end = max(1, int(round(en * q)))
    lo, hi = float(seg[:n_end].mean()), float(seg[-n_end:].mean())
    if hi == lo:
        raise ValueError("%s: the black and white levels are equal (%g) — no edge inside the window" % (fn, lo))
    lsf = np.diff((seg - lo) / (hi - lo))
    if apodize == "hamming":
        t = (0.5 * (xs[:-1] + xs[1:]) - xc) / w      # [-1, 1]
        lsf = lsf * (0.54 + 0.46 * np.cos(np.pi * np.clip(t, -1.0, 1.0)))
    spec = np.fft.rfft(lsf)
    f = np.fft.rfftfreq(lsf.size, dx)
    dc = abs(spec[0])
    if dc == 0.0:
        raise ValueError("%s: the LSF sums to zero inside the window" % fn)
    mtf = np.abs(spec) / dc
    if correction != "none":
        k = 2 if correction == "derivative+bin" else 1
        mtf = mtf / np.sinc(f * dx) ** k
    fmax = min(1.0, 0.5 / dx)                       # 升の Nyquist(1 px 刻みなら 0.5)、ただし 1 cyc/px まで
    keep = f <= fmax + 1e-12
    return np.ascontiguousarray(np.column_stack([f[keep], mtf[keep]]), dtype=np.float64)


def mtf50(sfr):
    """SFR(pairs: 周波数, 値)が 0.5 を**最初に**切る周波数(直線補間)。0.5 を切らなければ ``ValueError``
    (「測れる範囲の上まで 0.5 以上」を最大値として黙って返さない)。"""
    p = np.asarray(sfr, np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or p.shape[0] < 2 or not np.isfinite(p).all():
        raise ValueError("mtf50: expected an (n, 2) finite pairs array (got shape %r)" % (p.shape,))
    f, v = p[:, 0], p[:, 1]
    below = np.nonzero(v < 0.5)[0]
    if below.size == 0:
        raise ValueError("mtf50: the SFR stays at or above 0.5 up to %.4g cyc/px — MTF50 is beyond the measured range" % f[-1])
    i = int(below[0])
    if i == 0:
        raise ValueError("mtf50: the SFR starts below 0.5 (%.3g at %.4g) — not a normalised SFR" % (v[0], f[0]))
    return float(f[i - 1] + (0.5 - v[i - 1]) * (f[i] - f[i - 1]) / (v[i] - v[i - 1]))


def veiling_glare_index(img, dark_mask, bright_mask):
    """迷光(ベーリンググレア)指数: 黒い点の中心の明るさの平均 / 白地の明るさの平均(ISO 9358 の考え方)。

    *dark_mask*(必須): 黒い点の**中心部**の画素(点の縁の ぼけ を含めない —— 縁を含めるとコアの ぼけ まで迷光に数える)。
    *bright_mask*(必須): 白地の画素。★黒い点の大きさ(と光源の広さ)で答えが変わる: 裾が 1/(1+(r/r0)²) のレンズでは
    黒い点の一辺を 16 → 256 px にすると同じレンズの指数が 19.6 % → 4.5 %(`poc_veiling_glare` 3 節)。点の大きさは結果と一緒に報告すること。

    返り値 ``{"vgi": 比, "dark": 黒点の平均, "bright": 白地の平均, "n_dark", "n_bright"}``。暗電流・黒レベルは引かない
    (引いた像を渡す)。

    **Raises** ``ValueError``: 画像・マスクの形が違う / マスクが bool でない・空・重なる / 白地の平均が 0 以下。
    """
    fn = "veiling_glare_index"
    a = _image(img, "img", fn)
    masks = []
    for nm, mk in (("dark_mask", dark_mask), ("bright_mask", bright_mask)):
        m = np.asarray(mk)
        if m.dtype != bool:
            raise ValueError("%s: %s must be a boolean array (got dtype %s)" % (fn, nm, m.dtype))
        if m.shape != a.shape:
            raise ValueError("%s: %s has shape %r, the image %r" % (fn, nm, m.shape, a.shape))
        if not m.any():
            raise ValueError("%s: %s selects no pixels" % (fn, nm))
        masks.append(m)
    dm, bm = masks
    if (dm & bm).any():
        raise ValueError("%s: dark_mask and bright_mask overlap in %d pixels" % (fn, int((dm & bm).sum())))
    dark, bright = float(a[dm].mean()), float(a[bm].mean())
    if not bright > 0:
        raise ValueError("%s: the bright field averages %g — subtract the black level only if the field stays positive" % (fn, bright))
    return {"vgi": dark / bright, "dark": dark, "bright": bright, "n_dark": int(dm.sum()), "n_bright": int(bm.sum())}

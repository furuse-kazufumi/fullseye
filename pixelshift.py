# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ピクセルシフト撮像 —— センサを 1 画素 / 半画素ずつ動かして、色と解像度を稼ぐ(撮る側と合わせる側)。

センサシフト(圧電アクチュエータで撮像素子そのものを動かす)で複数枚を撮り、合わせる。2 つの使い方がある:

* **1 画素シフト 4 枚**(Bayer): (0,0)・(0,1)・(1,1)・(1,0) と 1 画素ずつ動かすと、シーンの同じ点を R・G・G・B の
  4 つの色の画素が順に見る。各画素で 3 色が**実測**で揃うので、デモザイク(補間)が要らず、偽色とジッパーが出ない。
  ★解像度は上がらない(標本の間隔は 1 画素のまま)。上がるのは色の標本化。
* **半画素シフト**(4 枚 = 白黒、16 枚 = Bayer で 1 画素 4 枚 × 半画素 4 位相): 標本の間隔が 1/2 画素になり、
  ナイキストが 0.5 → 1.0 cyc/px に上がる。★画素の開口の MTF(箱の幅 = 画素の開口、``|sinc(f · fill)|``)は
  シフトしても変わらない —— 上がるのは**折り返しを起こさずに通せる帯域**であって、0.5 cyc/px での MTF の値ではない。
  レンズの MTF が先に落ちていれば(λN/p = Q ≥ 2、Fiete 1999)、そもそも 0.5 cyc/px より上に信号が無く、
  シフトしても何も増えない。

op(どれも fail-closed、黙って補間・推定しない):

* :func:`pixel_shift_pattern` —— 公称のシフト列(``single`` / ``4shot`` / ``half4`` / ``16shot``)+ 誤差(圧電の ±0.1 px・振動)
* :func:`pixel_shift_capture` —— 細かく描いたシーンを、シフトした画素の開口(箱)で**厳密に**積分して撮る(Bayer か白黒)
* :func:`pixel_shift_merge` —— 公称のシフトで格子へ振り分けて合わせる(1 画素 = 全色、半画素 = 2 倍の格子)+ 動き検出の差し戻し
* :func:`pixel_shift_motion_mask` —— 同じ格子点に入った G(白黒なら同じ画素)の食い違いから、動いた画素を見つける
* :func:`false_color_metric` —— 無彩色の被写体に乗った色(BT.601 の Cb・Cr の大きさ)= 偽色の量
* :func:`pixel_shift_resolution_budget` —— 画素の開口の sinc × 回折の MTF・ナイキスト・折り返し・Q = λN/p の閉形式

既存の op との棲み分け(再実装しない):

* 1 枚のデモザイクは ``gfx2d.raw_demosaic_bilinear``(比較の基準と、動いた画素の差し戻し先に使う)。
* 任意の(格子に乗らない)ずれの合成は ``astrostack.drizzle_resample``(面積保存の drizzle)。この
  :func:`pixel_shift_merge` は**公称のずれが格子に乗る**場合(実機のピクセルシフト)専用で、乗らなければ拒否する。
* 回折の MTF の曲線は ``optics.mtf_diffraction``、Airy の PSF は ``optics.airy_pattern``、傾いたエッジの MTF は
  ``edgesfr.edge_spread`` → ``sfr_from_edge`` → ``mtf50``。

出典:

* M. Ben-Ezra, A. Zomet, S. K. Nayar, "Video super-resolution using controlled subpixel detector shifts",
  IEEE Trans. PAMI 27(6), 977–987 (2005) —— 撮像素子を副画素だけ動かして撮る(jitter camera)。
* B. Wronski et al., "Handheld multi-frame super-resolution", ACM Trans. Graphics 38(4), Art. 28 (2019) ——
  ずれた Bayer の raw を合わせると各画素に R・G・B が実測で揃い、デモザイクが要らなくなる。動きへの頑健さ(差し戻し)。
* J. R. Fiete, "Image quality and λFN/p for remote sensing systems", Optical Engineering 38(7), 1229–1240 (1999) ——
  Q = λN/p: Q < 2 なら画素が律速(折り返しが出る)、Q ≥ 2 ならレンズが律速。
* B. K. Gunturk, J. Glotzbach, Y. Altunbasak, R. W. Schafer, R. M. Mersereau, "Demosaicking: color filter array
  interpolation", IEEE Signal Processing Magazine 22(1), 44–54 (2005) —— 偽色・ジッパーは色の標本化の折り返し。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "pixel_shift_pattern",
    "pixel_shift_capture",
    "pixel_shift_merge",
    "pixel_shift_motion_mask",
    "false_color_metric",
    "pixel_shift_resolution_budget",
]

#: 公称のシフト列(dr, dc)[センサ画素]。1 画素シフトは CFA の 2×2 を一巡する順(Sony / Pentax の 4 枚と同じ巡り方)。
_ONE_PX = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))
_HALF_PX = ((0.0, 0.0), (0.0, 0.5), (0.5, 0.5), (0.5, 0.0))
PATTERN_MODES = ("single", "4shot", "half4", "16shot")
BAYER_PATTERNS = ("RGGB", "BGGR", "GRBG", "GBRG")
#: シフトの大きさの上限 [画素] (これより大きい「シフト」は位置合わせの問題で、ピクセルシフトではない)。
MAX_SHIFT_PX = 4.0
#: BT.601 の RGB → (Cb, Cr) の行(gfx2d の ``_YCBCR`` と同じ係数)。
_CBCR = np.array([[-0.168736, -0.331264, 0.5],
                  [0.5, -0.418688, -0.081312]])


# ───────────────────────────── 検査 ─────────────────────────────
def _finite_number(v, name, fn, lo=None, hi=None, lo_open=False):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a number (got %r)" % (fn, name, v))
    x = float(v)
    if not math.isfinite(x):
        raise ValueError("%s: %s must be finite (got %r)" % (fn, name, v))
    if lo is not None and (x <= lo if lo_open else x < lo):
        raise ValueError("%s: %s must be %s %g (got %r)" % (fn, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and x > hi:
        raise ValueError("%s: %s must be <= %g (got %r)" % (fn, name, hi, v))
    return x


def _int(v, name, fn, lo, hi):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or not (lo <= int(v) <= hi):
        raise ValueError("%s: %s must be an integer in [%d, %d] (got %r)" % (fn, name, lo, hi, v))
    return int(v)


def _pattern(pattern, fn):
    if pattern is None:
        return None
    if not isinstance(pattern, str) or pattern.upper() not in BAYER_PATTERNS:
        raise ValueError("%s: pattern must be None (monochrome) or one of %s (got %r)" % (fn, BAYER_PATTERNS, pattern))
    return pattern.upper()


def _cfa_index(pattern, shape):
    """センサの画素ごとの色の番号(0 = R、1 = G、2 = B)。CFA は**センサと一緒に動く**ので、センサの添字で決まる。"""
    lut = {"R": 0, "G": 1, "B": 2}
    blk = np.array([[lut[pattern[0]], lut[pattern[1]]], [lut[pattern[2]], lut[pattern[3]]]], dtype=np.int64)
    h, w = shape
    return np.tile(blk, ((h + 1) // 2, (w + 1) // 2))[:h, :w]


def _shifts(shifts, fn, n=None):
    s = np.asarray(shifts, dtype=np.float64) if not isinstance(shifts, (str, bytes)) else None
    if s is None or s.ndim != 2 or s.shape[1] != 2 or s.shape[0] < 1:
        raise ValueError("%s: shifts must be an (N, 2) array of (dr, dc) in sensor pixels (got %r)"
                         % (fn, getattr(s, "shape", shifts)))
    if not np.isfinite(s).all():
        raise ValueError("%s: shifts contain NaN or inf" % fn)
    if np.abs(s).max() > MAX_SHIFT_PX:
        raise ValueError("%s: |shift| must be <= %g px (got %.3g) — a larger offset is registration, not pixel shift"
                         % (fn, MAX_SHIFT_PX, np.abs(s).max()))
    if n is not None and s.shape[0] != n:
        raise ValueError("%s: %d shifts for %d frames" % (fn, s.shape[0], n))
    return s


# ───────────────────────────── シフト列 ─────────────────────────────
def pixel_shift_pattern(mode="4shot", error_px=0.0, cycles=1, seed=0):
    """ピクセルシフトの公称のシフト列 ``(N, 2)``(dr, dc)[センサ画素]に、アクチュエータの誤差を足して返す。

    *mode*:

    * ``"single"`` —— (0, 0) の 1 枚(比較の基準)。
    * ``"4shot"`` —— (0,0)・(0,1)・(1,1)・(1,0)。Bayer の 2×2 を一巡し、各画素で R・G・G・B が揃う(解像度はそのまま)。
    * ``"half4"`` —— (0,0)・(0,½)・(½,½)・(½,0)。白黒センサで標本の間隔を 1/2 画素に(ナイキスト 2 倍)。
    * ``"16shot"`` —— 半画素 4 位相 × 1 画素 4 枚。Bayer で 2 倍の格子の各点に R・G・G・B が揃う。

    *error_px*: 各枚・各軸に独立に足す正規乱数の標準偏差 [画素] (圧電の位置決め誤差・振動)。0 なら公称のまま。
    ★合わせる側(:func:`pixel_shift_merge`)には**公称**を渡すこと —— 実機は誤差を知らない。
    *cycles*: 同じ巡りを何周するか(N 倍の枚数で雑音を √N で下げる。動く被写体では誤差の元)。
    *seed*: 誤差の乱数の種。

    **Raises** ``ValueError``: mode が一覧に無い / error_px が負・0.5 以上・非有限 / cycles が 1〜64 の整数でない。
    """
    fn = "pixel_shift_pattern"
    if mode not in PATTERN_MODES:
        raise ValueError("%s: mode must be one of %s (got %r)" % (fn, PATTERN_MODES, mode))
    err = _finite_number(error_px, "error_px", fn, lo=0.0)
    if err >= 0.5:
        raise ValueError("%s: error_px must be < 0.5 px (got %r) — beyond that the nominal grid is meaningless" % (fn, error_px))
    cyc = _int(cycles, "cycles", fn, 1, 64)
    if mode == "single":
        base = [(0.0, 0.0)]
    elif mode == "4shot":
        base = list(_ONE_PX)
    elif mode == "half4":
        base = list(_HALF_PX)
    else:
        base = [(h[0] + o[0], h[1] + o[1]) for h in _HALF_PX for o in _ONE_PX]
    s = np.tile(np.array(base, dtype=np.float64), (cyc, 1))
    if err > 0:
        s = s + np.random.default_rng(seed).normal(0.0, err, size=s.shape)
    return np.ascontiguousarray(s)


# ───────────────────────────── 撮る ─────────────────────────────
def _sat(img):
    """面積の総和表(角の座標で引く)。``S[i, j]`` = ``img[:i, :j]`` の総和、形 (H+1, W+1)。"""
    s = np.zeros((img.shape[0] + 1, img.shape[1] + 1), dtype=np.float64)
    s[1:, 1:] = np.cumsum(np.cumsum(img, axis=0), axis=1)
    return s


def _box_sample(sat, y0, y1, x0, x1):
    """面積の総和表を角で双線形に引き、長方形 [y0,y1]×[x0,x1] の積分を返す。

    シーンの 1 標本を「その升の中で一定」とみなすと、総和表は各升の中で双線形なので、双線形補間は**厳密**である
    (近似ではない)。だから開口の積分は、シフトが升の何分の 1 でも誤差なく取れる。
    """
    from scipy import ndimage as ndi

    def at(y, x):
        return ndi.map_coordinates(sat, [y.ravel(), x.ravel()], order=1, mode="nearest").reshape(y.shape)

    return at(y1, x1) - at(y0, x1) - at(y1, x0) + at(y0, x0)


def pixel_shift_capture(scene, factor, shifts, pattern="RGGB", fill_factor=1.0, per_frame=False, margin=None):
    """シフトした撮像素子で撮る: シーンを画素の開口(正方形の箱)で**厳密に**積分し、Bayer か白黒の生の画像を返す。

    *scene*: 細かく描いたシーン。``(Hs, Ws)``(白黒)か ``(Hs, Ws, 3)``(RGB)、有限の実数。1 センサ画素 = *factor* ×
    *factor* 標本。``per_frame=True`` なら先頭に枚数の軸 ``(N, Hs, Ws[, 3])`` を持ち、枚ごとに違うシーン(搬送中の
    ワーク・動く被写体)を撮る。
    *factor*: 1 センサ画素あたりのシーンの標本数(2〜64 の整数)。Hs・Ws はその倍数。
    *shifts*: ``(N, 2)`` の**実際の**シフト (dr, dc)[センサ画素] (:func:`pixel_shift_pattern` の誤差込み)。
    センサが +dc 動くと、画素 (r, c) はシーンの c + dc を見る。
    *pattern*: ``"RGGB"`` などの Bayer(色フィルタはセンサと一緒に動く)か ``None``(白黒。RGB のシーンなら
    各画素で 3 色を取る理想センサ = 真値づくり用で、返り値は ``(N, H, W, 3)``)。
    *fill_factor*: 画素の開口の一辺 / 画素の間隔(0 < f ≤ 1)。開口の MTF は ``|sinc(f · fill)|``(f は cyc/px)。

    *margin*: センサの (0, 0) 画素を置くシーンの升の番号 m(整数)。``None`` なら m = ⌈max |shift|⌉(全シフトで開口が
    シーンの内側に残る最小の余白)。★真値(シフト 0 の理想センサ)と比べるときは、比べる相手と同じ m を明示すること
    —— シフト列が違うと既定の m が違い、同じ添字の画素がシーンの別の場所を指す。

    画素 (r, c) の中心はシーンの座標(升の辺を整数にとる)で ((r + m + ½ + dr)·factor, (c + m + ½ + dc)·factor)。
    返す画像は H = Hs/factor − 2m、W = Ws/factor − 2m。
    積分は面積の総和表の双線形補間で行い、シーンを「升ごとに一定」とみなす限り誤差は丸めだけ(テストで 1e-12)。

    返り値 ``(N, H, W)`` float64(Bayer か白黒)/ ``(N, H, W, 3)``(pattern=None で RGB のシーン)。雑音は足さない
    (EMVA 1288 の雑音を足すなら呼び手で。この op は幾何と開口だけ)。

    **Raises** ``ValueError``: シーンの形・次元・非有限 / factor・fill_factor の範囲 / Hs・Ws が factor の倍数でない /
    シフトの形・大きさ / margin が負・シフトに足りない / per_frame で枚数がシフトと合わない / Bayer なのにシーンが RGB でない(Bayer は色を撮る)/
    残る画素が 8 × 8 未満。
    """
    fn = "pixel_shift_capture"
    F = _int(factor, "factor", fn, 2, 64)
    fill = _finite_number(fill_factor, "fill_factor", fn, lo=0.0, hi=1.0, lo_open=True)
    pat = _pattern(pattern, fn)
    sc = np.asarray(scene, dtype=np.float64)
    if not per_frame:
        sc = sc[None]
    if sc.ndim not in (3, 4) or (sc.ndim == 4 and sc.shape[-1] != 3):
        raise ValueError("%s: scene must be (Hs, Ws) or (Hs, Ws, 3)%s (got shape %r)"
                         % (fn, " with a leading frame axis" if per_frame else "", np.shape(scene)))
    if not np.isfinite(sc).all():
        raise ValueError("%s: scene contains NaN or inf" % fn)
    rgb = sc.ndim == 4
    if pat is not None and not rgb:
        raise ValueError("%s: a Bayer sensor needs an RGB scene (Hs, Ws, 3); use pattern=None for a monochrome sensor" % fn)
    s = _shifts(shifts, fn, n=sc.shape[0] if per_frame else None)
    n = s.shape[0]
    hs, ws = sc.shape[1], sc.shape[2]
    if hs % F or ws % F:
        raise ValueError("%s: scene size %dx%d is not a multiple of factor %d" % (fn, hs, ws, F))
    need = int(math.ceil(np.abs(s).max() - 1e-12)) if np.abs(s).max() > 0 else 0
    if margin is None:
        m = need
    else:
        m = _int(margin, "margin", fn, 0, 10 ** 6)
        if m < need:
            raise ValueError("%s: margin %d is smaller than the largest shift needs (%d)" % (fn, m, need))
    H, W = hs // F - 2 * m, ws // F - 2 * m
    if H < 8 or W < 8:
        raise ValueError("%s: only %dx%d sensor pixels remain after the %d-pixel margin for the shifts" % (fn, H, W, m))
    rr, cc = np.meshgrid(np.arange(H, dtype=np.float64), np.arange(W, dtype=np.float64), indexing="ij")
    half = 0.5 * fill * F
    area = (fill * F) ** 2
    nch = 3 if rgb else 1
    sats_static = None
    if not per_frame:
        sats_static = [_sat(sc[0][..., k] if rgb else sc[0]) for k in range(nch)]
    out = np.empty((n, H, W, nch), dtype=np.float64)
    for i in range(n):
        sats = sats_static if sats_static is not None else [_sat(sc[i][..., k] if rgb else sc[i]) for k in range(nch)]
        cy = (rr + m + 0.5 + s[i, 0]) * F
        cx = (cc + m + 0.5 + s[i, 1]) * F
        for k in range(nch):
            out[i, ..., k] = _box_sample(sats[k], cy - half, cy + half, cx - half, cx + half) / area
    if pat is None:
        return np.ascontiguousarray(out if rgb else out[..., 0])
    idx = _cfa_index(pat, (H, W))
    raw = np.take_along_axis(out, np.broadcast_to(idx[None, :, :, None], (n, H, W, 1)), axis=3)[..., 0]
    return np.ascontiguousarray(raw)


# ───────────────────────────── 合わせる ─────────────────────────────
def _frames(frames, fn):
    f = np.asarray(frames, dtype=np.float64)
    if f.ndim != 3 or f.shape[1] < 4 or f.shape[2] < 4:
        raise ValueError("%s: frames must be (N, H, W) raw frames with H, W >= 4 (got shape %r)" % (fn, np.shape(frames)))
    if not np.isfinite(f).all():
        raise ValueError("%s: frames contain NaN or inf" % fn)
    return f


def _bins(frames, shifts, pattern, scale, fn):
    """各枚の各画素を、公称のシフトで出力の格子(間隔 1/scale 画素)へ振り分ける。

    返り値: (チャネル数, 出力の形, [(枚 i, 出力の行, 出力の列, チャネル, 値) の配列])。
    """
    n, H, W = frames.shape
    s = _shifts(shifts, fn, n=n)
    q = s * scale
    off = np.abs(q - np.round(q))
    if off.max() > 0.25:
        raise ValueError("%s: nominal shifts %s are not on the 1/%d-pixel grid (worst %.3g grid steps off) — pass the "
                         "nominal shifts (the merge cannot know the actuator error), or use astrostack.drizzle_resample "
                         "for arbitrary offsets" % (fn, np.round(s, 3).tolist(), scale, off.max()))
    qi = np.round(q).astype(np.int64)
    nch = 3 if pattern is not None else 1
    cfa = _cfa_index(pattern, (H, W)) if pattern is not None else np.zeros((H, W), np.int64)
    rr, cc = np.meshgrid(np.arange(H), np.arange(W), indexing="ij")
    Ho, Wo = H * scale, W * scale
    recs = []
    for i in range(n):
        orr = rr * scale + qi[i, 0]
        occ = cc * scale + qi[i, 1]
        ok = (orr >= 0) & (orr < Ho) & (occ >= 0) & (occ < Wo)
        idx = np.stack([np.full(ok.sum(), i), orr[ok], occ[ok], cfa[ok]], axis=1)
        recs.append((idx, frames[i][ok]))
    return nch, (Ho, Wo), recs, qi


def _accumulate(nch, shape, recs):
    tot = np.zeros((nch,) + shape)
    cnt = np.zeros((nch,) + shape, dtype=np.int64)
    for idx, val in recs:
        np.add.at(tot, (idx[:, 3], idx[:, 1], idx[:, 2]), val)
        np.add.at(cnt, (idx[:, 3], idx[:, 1], idx[:, 2]), 1)
    return tot, cnt


def _check_channel(pattern):
    return 1 if pattern is not None else 0      # G(Bayer)/ 唯一のチャネル(白黒)


def _motion_mask_core(frames, shifts, pattern, scale, threshold, noise_sigma, fn):
    nch, shape, recs, qi = _bins(frames, shifts, pattern, scale, fn)
    ch = _check_channel(pattern)
    lo = np.full(shape, np.inf)
    hi = np.full(shape, -np.inf)
    cnt = np.zeros(shape, dtype=np.int64)
    for idx, val in recs:
        sel = idx[:, 3] == ch
        r, c, v = idx[sel, 1], idx[sel, 2], val[sel]
        np.minimum.at(lo, (r, c), v)
        np.maximum.at(hi, (r, c), v)
        np.add.at(cnt, (r, c), 1)
    pair = cnt >= 2
    if not pair.any():
        raise ValueError("%s: no output pixel received two samples of the check channel (%s) — motion cannot be "
                         "detected with these shifts" % (fn, "G" if pattern else "mono"))
    spread = np.where(pair, hi - lo, 0.0)
    if noise_sigma is None or noise_sigma == 0:
        d = spread[pair]
        # 2 標本の差 |a − b| の中央値 = 0.6745·√2·σ(半正規)。動いた画素は少数派という前提(MAD と同じ破綻点 50 %)。
        sigma = float(np.median(d)) / (0.6745 * math.sqrt(2.0))
    else:
        sigma = _finite_number(noise_sigma, "noise_sigma", fn, lo=0.0)
    thr = threshold * sigma * math.sqrt(2.0)
    mask = pair & (spread > thr)
    return mask, sigma, pair


def pixel_shift_motion_mask(frames, shifts, pattern="RGGB", scale=1, threshold=4.0, noise_sigma=0.0):
    """動いた画素の地図 ``(H·scale, W·scale)``(1.0 = 動いた、0.0 = 静止 / 判定できない)。

    同じ出力の格子点に、**別の枚**から同じ色(Bayer なら G、白黒ならそのまま)の標本が 2 つ以上入る。被写体が
    止まっていれば、その差は時間の雑音だけ(差の標準偏差 √2·σ)。差の幅(最大 − 最小)が ``threshold · √2 · σ`` を
    超えた格子点を「動いた」とする。σ は *noise_sigma* で与えるか、0 なら全格子点の差の中央値から推定する
    (半正規の中央値 0.6745·√2·σ。動いた画素が半数を超えると推定が壊れる —— MAD と同じ破綻点)。

    ★雑音の少ない静止画でも、**シフトの誤差**があると細かい模様の上で差が出る(誤差 δ・空間周波数 f・振幅 a で
    差 ≈ 2π f a δ)。閾値はその偽陽性と、遅い動き(1 枚あたり小さなずれ)の見逃しの綱引き。
    1 画素シフト 4 枚の Bayer では、各格子点の G はちょうど 2 つ(別の 2 枚から)。

    **Raises** ``ValueError``: frames・shifts の形 / 公称のシフトが格子に乗らない / threshold が正でない /
    どの格子点にも同じ色の標本が 2 つ入らない(このシフト列では動きを検出できない)。
    """
    fn = "pixel_shift_motion_mask"
    f = _frames(frames, fn)
    pat = _pattern(pattern, fn)
    sc = _int(scale, "scale", fn, 1, 4)
    thr = _finite_number(threshold, "threshold", fn, lo=0.0, lo_open=True)
    mask, _sigma, _pair = _motion_mask_core(f, shifts, pat, sc, thr, noise_sigma, fn)
    return mask.astype(np.float64)


def _single_frame_fallback(frames, qi, pattern, scale):
    """シフト (0, 0) の枚を 1 枚だけで色にし(Bayer は gfx2d の双線形デモザイク)、出力の格子へ線形補間する。"""
    from scipy import ndimage as ndi

    k0 = np.nonzero((qi == 0).all(axis=1))[0]
    if k0.size == 0:
        return None
    raw = frames[int(k0[0])]
    if pattern is not None:
        import gfx2d
        lo, hi = float(raw.min()), float(raw.max())
        span = hi - lo if hi > lo else 1.0
        rgb = gfx2d.raw_demosaic_bilinear((raw - lo) / span, pattern=pattern) * span + lo
    else:
        rgb = raw[..., None]
    if scale == 1:
        return rgb
    Ho, Wo = raw.shape[0] * scale, raw.shape[1] * scale
    yy, xx = np.meshgrid(np.arange(Ho) / scale, np.arange(Wo) / scale, indexing="ij")
    return np.stack([ndi.map_coordinates(rgb[..., k], [yy, xx], order=1, mode="nearest")
                     for k in range(rgb.shape[2])], axis=-1)


def pixel_shift_merge(frames, shifts, pattern="RGGB", scale=1, motion_threshold=0.0, noise_sigma=0.0):
    """ピクセルシフトの枚を、**公称の**シフトで格子へ振り分けて合わせる。補間はしない(同じ格子点の標本の平均だけ)。

    *frames*: ``(N, H, W)`` の生の画像(:func:`pixel_shift_capture` の返り値、Bayer か白黒)。
    *shifts*: ``(N, 2)`` の**公称の**シフト(:func:`pixel_shift_pattern` を ``error_px=0`` で)。1/scale 画素の格子に
    乗っていなければ拒否する(任意のずれは ``astrostack.drizzle_resample``)。
    *pattern*: Bayer の並び(``None`` = 白黒)。
    *scale*: 1 = 同じ格子(1 画素シフト 4 枚 → 各画素に R・G・B)、2 = 半画素の格子(half4 / 16shot)。
    *motion_threshold*: > 0 なら :func:`pixel_shift_motion_mask` で動いた格子点を見つけ、そこ(と 8 近傍)だけを
    シフト (0, 0) の 1 枚から作った像(Bayer は ``gfx2d.raw_demosaic_bilinear``)に差し戻す —— 動いた所は
    「ピクセルシフトしなかった」画質に戻るが、櫛状の破綻は消える。0 なら差し戻さない。
    *noise_sigma*: 動き検出の雑音 σ(0 = 推定)。

    返り値: ``(H·scale, W·scale, 3)``(Bayer)/ ``(H·scale, W·scale)``(白黒)の float64。

    端の扱い: シフトのぶん、格子の端(最大シフトの幅)にはどの枚の標本も来ない色がある。そこは (0, 0) の 1 枚から
    作った像で埋める(黙って 0 にしない)。**内側**に標本の来ない格子点・色があれば(例: 1 画素シフト 4 枚を
    scale=2 で合わせる、2 枚だけの Bayer)、このシフト列では格子を埋められないので ``ValueError``。

    **Raises** ``ValueError``: frames・shifts の形・非有限 / 格子に乗らないシフト / scale が 1〜4 でない /
    内側の格子点に標本の来ない色がある / motion_threshold > 0 なのにシフト (0, 0) の枚が無い・動きを検出できない。
    """
    fn = "pixel_shift_merge"
    f = _frames(frames, fn)
    pat = _pattern(pattern, fn)
    sc = _int(scale, "scale", fn, 1, 4)
    mthr = _finite_number(motion_threshold, "motion_threshold", fn, lo=0.0)
    nch, shape, recs, qi = _bins(f, shifts, pat, sc, fn)
    tot, cnt = _accumulate(nch, shape, recs)
    # 内側(どのシフトでも届く範囲)に穴があれば、このシフト列はこの格子を埋められない
    r0, r1 = int(max(0, qi[:, 0].max())), shape[0] - int(max(0, -qi[:, 0].min())) - (sc - 1)
    c0, c1 = int(max(0, qi[:, 1].max())), shape[1] - int(max(0, -qi[:, 1].min())) - (sc - 1)
    inner = cnt[:, r0:max(r0, r1), c0:max(c0, c1)]
    if inner.size == 0 or (inner == 0).any():
        frac = float((inner > 0).mean()) if inner.size else 0.0
        raise ValueError("%s: these %d shifts cover only %.0f %% of the (channel, pixel) cells of the %dx grid — "
                         "e.g. 1-pixel 4-shot fills colour at scale 1 only; use 'half4'/'16shot' for scale 2"
                         % (fn, f.shape[0], 100.0 * frac, sc))
    with np.errstate(invalid="ignore", divide="ignore"):
        img = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
    img = np.moveaxis(img, 0, -1)                     # (Ho, Wo, nch)
    holes = ~np.isfinite(img)
    need_fallback = holes.any() or mthr > 0
    fb = _single_frame_fallback(f, qi, pat, sc) if need_fallback else None
    if holes.any():
        if fb is None:
            raise ValueError("%s: the border has cells no frame reaches and there is no (0, 0) frame to fill them" % fn)
        img[holes] = fb[holes]
    if mthr > 0:
        if fb is None:
            raise ValueError("%s: motion fallback needs a frame at shift (0, 0)" % fn)
        mask, _s, _p = _motion_mask_core(f, shifts, pat, sc, mthr, noise_sigma, fn)
        from scipy import ndimage as ndi
        mask = ndi.binary_dilation(mask, structure=np.ones((3, 3), bool))
        img[mask] = fb[mask]
    out = img if pat is not None else img[..., 0]
    return np.ascontiguousarray(out, dtype=np.float64)


# ───────────────────────────── 測る ─────────────────────────────
def false_color_metric(rgb, reference=None, border=0):
    """偽色の量: 色差(BT.601 の Cb, Cr)の大きさの統計。

    *reference* が無ければ被写体を**無彩色**とみなし、各画素の √(Cb² + Cr²) そのものを偽色とする(白黒の配線・
    織物・網点・解像チャートを撮った場合)。*reference* ``(H, W, 3)`` があれば、その色差との差の大きさを取る
    (色のある被写体)。*border* 画素ぶん四辺を除いてから数える(端の差し戻しを数えないため)。

    返り値 ``{"mean", "rms", "p99", "max", "fraction_over_0.02", "n_pixels"}``。値は入力の階調(0〜1 なら 0〜1)
    の色差。0.02 は 8 bit で約 5 階調。

    **Raises** ``ValueError``: rgb が ``(H, W, 3)`` の有限の実数でない / reference の形が違う / border が負・画像を
    食い尽くす。
    """
    fn = "false_color_metric"
    a = np.asarray(rgb, dtype=np.float64)
    if a.ndim != 3 or a.shape[2] != 3 or not np.isfinite(a).all():
        raise ValueError("%s: rgb must be a finite (H, W, 3) array (got shape %r)" % (fn, np.shape(rgb)))
    b = _int(border, "border", fn, 0, 10 ** 6)
    if 2 * b >= min(a.shape[0], a.shape[1]):
        raise ValueError("%s: border %d leaves nothing of a %dx%d image" % (fn, b, a.shape[0], a.shape[1]))
    cbcr = a @ _CBCR.T
    if reference is not None:
        r = np.asarray(reference, dtype=np.float64)
        if r.shape != a.shape or not np.isfinite(r).all():
            raise ValueError("%s: reference must be a finite array of shape %r (got %r)" % (fn, a.shape, r.shape))
        cbcr = cbcr - r @ _CBCR.T
    if b:
        cbcr = cbcr[b:-b, b:-b]
    mag = np.sqrt((cbcr ** 2).sum(axis=-1)).ravel()
    return {"mean": float(mag.mean()), "rms": float(np.sqrt((mag ** 2).mean())),
            "p99": float(np.percentile(mag, 99.0)), "max": float(mag.max()),
            "fraction_over_0.02": float((mag > 0.02).mean()), "n_pixels": int(mag.size)}


def _diffraction_mtf(x):
    x = np.clip(np.asarray(x, dtype=np.float64), 0.0, 1.0)
    return (2.0 / np.pi) * (np.arccos(x) - x * np.sqrt(1.0 - x * x))


def pixel_shift_resolution_budget(pitch_um, f_number, wavelength_um=0.55, fill_factor=1.0, step_px=0.5):
    """ピクセルシフトで解像が上がるかの閉形式の予算(レンズ律速か画素律速か)。

    周波数 f は cyc/px(センサ画素あたり)。

    * 画素の開口の MTF: ``|sinc(f · fill)|``(箱の幅 fill 画素)。fill = 1 なら f = 1 で 0。
    * 回折の MTF(円形の瞳、収差なし): ``(2/π)(acos x − x√(1 − x²))``、x = f · Q、**Q = λN/p**(Fiete 1999)。
      レンズの遮断は f = 1/Q。
    * ナイキスト: 1 枚 = 0.5、標本の間隔 *step_px* のシフト = 0.5 / step_px。1 枚で f > 0.5 の成分は
      f_alias = |f − round(f)| に折り返る(モアレ)。
    * **律速の境目は Q = 2**: レンズの遮断 1/Q が 1 枚のナイキスト 0.5 より上(Q < 2)なら、1 枚では折り返しが出て
      シフトで帯域が伸びる(画素律速)。Q ≥ 2 なら 0.5 より上に信号が無く、シフトしても増えない(レンズ律速)。
      ★ただし Q = 2 は「折り返しが出るか」の境目で、``gain``(系の MTF ≥ 0.1 の帯域の比)はもっと手前で 1.0 に
      なる: sinc(0.5)·MTF_diff(0.5 Q) = 0.1 の Q ≈ 1.47(fill = 1)。その間(例 Q = 1.75)は ``regime`` が
      ``"pixel_limited"`` でも ``gain`` は 1.0 —— 折り返しは消えるが、見える細かさは増えない。

    返り値の辞書: ``Q``、``lens_cutoff_cyc_px``、``nyquist_single``、``nyquist_shifted``、``aperture_zero_cyc_px``、
    ``mtf_at_nyquist_single``(開口・レンズ・系の 3 つ)、``mtf_at_nyquist_shifted``(同)、``mtf50_cyc_px`` /
    ``mtf10_cyc_px``(系の MTF が 0.5 / 0.1 を切る周波数、数値の二分法)、``usable_band_single`` /
    ``usable_band_shifted``(折り返しを起こさず、系の MTF が 0.1 以上の上限)、``gain``(後者 / 前者)、
    ``regime``(``"pixel_limited"`` / ``"lens_limited"``)、``lp_per_mm_per_cyc_px``(1 cyc/px = 1000/p lp/mm)。

    **Raises** ``ValueError``: pitch_um・f_number・wavelength_um が正の有限でない / fill_factor が (0, 1] でない /
    step_px が {1/4, 1/3, 1/2, 1} でない。
    """
    fn = "pixel_shift_resolution_budget"
    p = _finite_number(pitch_um, "pitch_um", fn, lo=0.0, lo_open=True)
    N = _finite_number(f_number, "f_number", fn, lo=0.0, lo_open=True)
    lam = _finite_number(wavelength_um, "wavelength_um", fn, lo=0.0, lo_open=True)
    fill = _finite_number(fill_factor, "fill_factor", fn, lo=0.0, hi=1.0, lo_open=True)
    st = _finite_number(step_px, "step_px", fn, lo=0.0, lo_open=True)
    if not any(abs(st - v) < 1e-12 for v in (0.25, 1.0 / 3.0, 0.5, 1.0)):
        raise ValueError("%s: step_px must be 1/4, 1/3, 1/2 or 1 (got %r)" % (fn, step_px))
    Q = lam * N / p

    def sysm(f):
        return np.abs(np.sinc(np.asarray(f) * fill)) * _diffraction_mtf(np.asarray(f) * Q)

    def first_below(level, fmax):
        g = np.linspace(0.0, fmax, 20001)
        v = sysm(g)
        i = np.nonzero(v < level)[0]
        if i.size == 0:
            return None
        lo_, hi_ = g[i[0] - 1], g[i[0]]
        for _ in range(60):
            mid = 0.5 * (lo_ + hi_)
            if sysm(mid) < level:
                hi_ = mid
            else:
                lo_ = mid
        return float(0.5 * (lo_ + hi_))

    fmax = min(1.0 / Q, 1.0 / fill) if Q > 0 else 1.0 / fill
    f50 = first_below(0.5, fmax)
    f10 = first_below(0.1, fmax)
    ny1, nys = 0.5, 0.5 / st
    lim = f10 if f10 is not None else fmax
    band1 = min(ny1, lim)
    bands = min(nys, lim)

    def triple(f):
        a = float(abs(np.sinc(f * fill)))
        ln = float(_diffraction_mtf(f * Q))
        return {"aperture": a, "lens": ln, "system": a * ln}

    return {"Q": Q, "lens_cutoff_cyc_px": 1.0 / Q, "nyquist_single": ny1, "nyquist_shifted": nys,
            "aperture_zero_cyc_px": 1.0 / fill,
            "mtf_at_nyquist_single": triple(ny1), "mtf_at_nyquist_shifted": triple(nys),
            "mtf50_cyc_px": f50, "mtf10_cyc_px": f10,
            "usable_band_single": band1, "usable_band_shifted": bands, "gain": bands / band1,
            "regime": "pixel_limited" if Q < 2.0 else "lens_limited",
            "lp_per_mm_per_cyc_px": 1000.0 / p}

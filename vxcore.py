# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""vxcore — OpenVX 1.3.1 が「渡せ」「返せ」と言う素の口を開ける op(第 1 陣 6 本 + 第 2 陣 4 本)。

2026-09-25 に OpenVX 1.3.1 の視覚関数 61 本を本文まで読んで照合したところ、17 件は「対応はあるが入口か出口の形が違う」だった
—— 便利な合成 op(``sobel_mag`` / ``sobel_dir`` / ``nonmax_suppression_amp`` / ``f2_lut_trans`` は引数 ``(v, a, b)`` で
出力を [0, 1] に正規化する進化用の op)は在るが、**規格の順序で使おうとすると入口が無い**: gx と gy を別々に受けて大きさと位相を
返す口、任意の表を引く口、規格どおりに隣を比べる非極大の抑制が無い。この族はその素の口を、**規範文 [REQ-NNNN] をそのまま門に**して足す。

第 1 陣(この版):
* :func:`vx_sobel3x3` — 3.46 節の核 G_x, G_y(REQ-0415)で gx・gy を**別々に**返す。境界は必須の引数。
* :func:`vx_magnitude` — 3.31 節: ``z = uint16(sqrt(double(x² + y²)) + 0.5)``、32767 で飽和(REQ-0270 の概念定義そのもの)。
* :func:`vx_phase` — 3.41 節: ϕ = atan2(gy, gx) を 0 ≤ ϕ < 2π に移し、0〜255 に写す(REQ-0364)。★規格は写し方の丸めを決めていない
  —— ``mapping`` を必須にして、``"floor"``(⌊ϕ·256/2π⌋)か ``"round"``(四捨五入して 256 を 0 に巻く)を呼び手が選ぶ。
* :func:`vx_table_lookup` — 3.47 節: 画素値で表を引く(REQ-0421)。S16 は ``offset`` を足して引く(VX_LUT_OFFSET)。表の外は止める。
* :func:`vx_histogram` — 3.26 節: ``i = (I − offset) × numBins / range``(offset ≤ I < offset + range、REQ-0230)。範囲外は数えない。
* :func:`vx_nonmax_suppression` — 3.39 節: 左上の隣には ≥、右下の隣には > で勝てば残す(REQ-0337)。マスクの非ゼロ画素は比べず残す
  (REQ-0336)。抑制した画素は U8 なら 0、S16 なら INT16_MIN(REQ-0335)。

第 2 陣(2026-10-01): :func:`vx_warp_affine`(3.56、REQ-0498 の**逆写像**)/ :func:`vx_warp_perspective`(3.57、REQ-0508)/
:func:`vx_remap`(3.44、REQ-0392)/ :func:`vx_nonlinear_filter`(3.38、中央値・最小・最大を任意マスクで、REQ-0325〜0330)。
標本は画素の中心(整数座標 = 中心、4.4.6 節)。ワープと remap の境界は UNDEFINED と CONSTANT だけ(REQ-0506)。
★規格の C の宣言は行列を転置した並び(``mat[3][2]``)で持つ —— この op は数学の並び(2×3 / 3×3)だけを受け、(3, 2) は止める。

整数の型(U8 / S16)は規格の型をそのまま守る: 入力の dtype を見て、合わなければ止める(黙って丸めない)。
"""
from __future__ import annotations

import numpy as np

__all__ = ["vx_sobel3x3", "vx_magnitude", "vx_phase", "vx_table_lookup", "vx_histogram", "vx_nonmax_suppression",
           "vx_warp_affine", "vx_warp_perspective", "vx_remap", "vx_nonlinear_filter"]

INT16_MIN = -32768
_BORDERS = ("replicate", "constant", "undefined")
GX = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], np.int32)      # REQ-0415
GY = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], np.int32)


def _img(a, name, fn, dtypes):
    x = np.asarray(a)
    if x.ndim != 2 or min(x.shape) < 1:
        raise ValueError("%s: %s must be a non-empty 2-D image (got shape %r)" % (fn, name, x.shape))
    if x.dtype not in dtypes:
        raise ValueError("%s: %s must have dtype %s, as the standard specifies (got %s) — convert explicitly"
                         % (fn, name, " or ".join(str(np.dtype(d)) for d in dtypes), x.dtype))
    return x


def _pad(x, border, value, fn):
    if border not in _BORDERS:
        raise ValueError("%s: border must be one of %r (got %r)" % (fn, _BORDERS, border))
    if border == "replicate":
        return np.pad(x, 1, mode="edge")
    if border == "constant":
        return np.pad(x, 1, mode="constant", constant_values=value)
    return np.pad(x, 1, mode="constant", constant_values=0)     # undefined: 端は計算するが「有効領域の外」として返す


def vx_sobel3x3(image, *, border, constant_value=0):
    """Sobel 3×3(3.46 節): G_x = [[−1,0,1],[−2,0,2],[−1,0,1]]、G_y = [[−1,−2,−1],[0,0,0],[1,2,1]](REQ-0415)を相関として当てる。

    *image*: U8。*border*(必須): ``"replicate"`` / ``"constant"``(*constant_value* で埋める)/ ``"undefined"``(端 1 画素は
    規格上未定義 —— 0 を入れ、``valid`` の外として返す)。

    返り値 ``{"gx": S16, "gy": S16, "valid": (y0, y1, x0, x1)}``(U8 の 3×3 Sobel は |値| ≤ 1020 なので S16 で飽和しない)。

    **Raises** ``ValueError``: 2-D の U8 でない / border が一覧に無い / constant_value が 0〜255 の外。
    """
    fn = "vx_sobel3x3"
    x = _img(image, "image", fn, (np.uint8,))
    cv = int(constant_value)
    if not 0 <= cv <= 255:
        raise ValueError("%s: constant_value must be in 0..255 (got %r)" % (fn, constant_value))
    p = _pad(x.astype(np.int32), border, cv, fn)
    h, w = x.shape
    gx = np.zeros((h, w), np.int32)
    gy = np.zeros((h, w), np.int32)
    for dy in range(3):
        for dx in range(3):
            win = p[dy:dy + h, dx:dx + w]
            gx += GX[dy, dx] * win
            gy += GY[dy, dx] * win
    if border == "undefined":
        valid = (1, max(1, h - 1), 1, max(1, w - 1))
        m = np.zeros((h, w), bool)
        m[valid[0]:valid[1], valid[2]:valid[3]] = True
        gx[~m] = 0
        gy[~m] = 0
    else:
        valid = (0, h, 0, w)
    return {"gx": gx.astype(np.int16), "gy": gy.astype(np.int16), "valid": valid}


def vx_magnitude(gx, gy):
    """勾配の大きさ(3.31 節)。REQ-0270 の概念定義をそのまま: ``z = uint16(sqrt(double(uint32(x·x) + uint32(y·y))) + 0.5)``、
    ``mag = z > 32767 ? 32767 : z``。入力・出力とも S16。

    **Raises** ``ValueError``: S16 の 2-D でない / 形が違う。
    """
    fn = "vx_magnitude"
    x = _img(gx, "gx", fn, (np.int16,)).astype(np.int64)
    y = _img(gy, "gy", fn, (np.int16,)).astype(np.int64)
    if x.shape != y.shape:
        raise ValueError("%s: gx %r and gy %r differ in shape" % (fn, x.shape, y.shape))
    s = (x * x).astype(np.uint32).astype(np.float64) + (y * y).astype(np.uint32).astype(np.float64)
    z = np.floor(np.sqrt(s) + 0.5)                   # uint16(... + 0.5) は 0 方向の切り捨て(値は非負)
    z = np.minimum(z, 65535.0)                       # uint16 への変換(sqrt(2·32768²) = 46341 なので実際には届かない)
    return np.minimum(z, 32767).astype(np.int16)


def vx_phase(gx, gy, *, mapping):
    """勾配の位相(3.41 節): ϕ = atan2(gy, gx) を 0 ≤ ϕ < 2π に移し、0〜255 に写す(REQ-0364)。出力 U8。

    *mapping*(必須): 規格は写し方の丸めを書いていない。``"floor"`` = ⌊ϕ·256/(2π)⌋(0 ≤ 値 ≤ 255 が自動で成り立つ)、
    ``"round"`` = ⌊ϕ·256/(2π) + 0.5⌋ mod 256(2π の手前は 0 に巻く)。gx = gy = 0 の画素は atan2 の約束で ϕ = 0。

    **Raises** ``ValueError``: S16 の 2-D でない / 形が違う / mapping が一覧に無い。
    """
    fn = "vx_phase"
    if mapping not in ("floor", "round"):
        raise ValueError("%s: mapping must be 'floor' or 'round' — the standard leaves the rounding open (got %r)" % (fn, mapping))
    x = _img(gx, "gx", fn, (np.int16,)).astype(np.float64)
    y = _img(gy, "gy", fn, (np.int16,)).astype(np.float64)
    if x.shape != y.shape:
        raise ValueError("%s: gx %r and gy %r differ in shape" % (fn, x.shape, y.shape))
    phi = np.arctan2(y, x)
    phi = np.where(phi < 0, phi + 2.0 * np.pi, phi)
    phi = np.where(phi >= 2.0 * np.pi, 0.0, phi)     # 0 ≤ ϕ < 2π(−0.0 + 2π の丸めで 2π に届く 1 点を戻す)
    u = phi * (256.0 / (2.0 * np.pi))
    q = np.floor(u) if mapping == "floor" else np.floor(u + 0.5)
    return (q.astype(np.int64) % 256).astype(np.uint8)


def vx_table_lookup(image, table, *, offset=0):
    """表引き(3.47 節): 出力 = table[画素値 + offset](REQ-0421)。U8 と S16 を受ける(REQ-0422)。出力の dtype は表の dtype。

    *offset*: S16 の表は負の画素値を引くために中央を 0 に置く(VX_LUT_OFFSET、典型は 32768)。U8 は 0。
    ★表の外を引く画素があれば止める(黙って端に寄せない)。

    **Raises** ``ValueError``: 画像が U8/S16 の 2-D でない / 表が 1-D でない・空 / 表の外を引く画素がある。
    """
    fn = "vx_table_lookup"
    x = _img(image, "image", fn, (np.uint8, np.int16))
    t = np.asarray(table)
    if t.ndim != 1 or t.size == 0 or t.dtype.kind not in "iu":
        raise ValueError("%s: table must be a non-empty 1-D integer array (got shape %r, dtype %s)" % (fn, t.shape, t.dtype))
    idx = x.astype(np.int64) + int(offset)
    bad = (idx < 0) | (idx >= t.size)
    if bad.any():
        raise ValueError("%s: %d pixels index outside the table [0, %d) with offset %d (min %d, max %d)"
                         % (fn, int(bad.sum()), t.size, int(offset), int(idx.min()), int(idx.max())))
    return t[idx]


def vx_histogram(image, *, num_bins, offset, range_):
    """ヒストグラム(3.26 節): 画素値 I は ``i = (I − offset) × numBins / range`` の升に入る(offset ≤ I < offset + range、REQ-0230)。
    範囲外の画素は数えない。整数の割り算(切り捨て)で升を決める。

    返り値 ``(num_bins, 2)`` の pairs: 列 0 = 升の下端の画素値(offset + i·range/numBins)、列 1 = 数。

    **Raises** ``ValueError``: U8 の 2-D でない / num_bins・range_ が正でない / num_bins > range_ / offset が負。
    """
    fn = "vx_histogram"
    x = _img(image, "image", fn, (np.uint8,)).astype(np.int64)
    nb, rg, off = int(num_bins), int(range_), int(offset)
    if nb <= 0 or rg <= 0 or off < 0:
        raise ValueError("%s: num_bins and range_ must be > 0 and offset >= 0 (got %r, %r, %r)" % (fn, num_bins, range_, offset))
    if nb > rg:
        raise ValueError("%s: num_bins (%d) must not exceed range_ (%d)" % (fn, nb, rg))
    inside = (x >= off) & (x < off + rg)
    i = ((x[inside] - off) * nb) // rg
    counts = np.bincount(i, minlength=nb)
    lo = off + np.arange(nb) * rg / nb
    return np.ascontiguousarray(np.column_stack([lo, counts.astype(np.float64)]))


def vx_nonmax_suppression(image, *, window, mask=None):
    """非極大の抑制(3.39 節)。画素 (x, y) は、窓の中で**自分より前(上の行と、同じ行の左)の隣には ≥、後ろの隣には >** の
    ときだけ残る(REQ-0337)。平らな頂上が 1 画素だけ残るのはこの非対称のため。*mask* の非ゼロ画素は比べず、そのまま残す
    (他の画素の比較にも使わない、REQ-0336)。抑制した画素は U8 なら 0、S16 なら INT16_MIN(REQ-0335)。窓の外にはみ出す隣は比べない。

    *window*(必須): 奇数の窓の一辺(3, 5, …)。

    **Raises** ``ValueError``: U8/S16 の 2-D でない / window が 3 以上の奇数でない / mask の形が違う。
    """
    fn = "vx_nonmax_suppression"
    x = _img(image, "image", fn, (np.uint8, np.int16))
    w = int(window)
    if w < 3 or w % 2 == 0:
        raise ValueError("%s: window must be an odd integer >= 3 (got %r)" % (fn, window))
    ign = np.zeros(x.shape, bool) if mask is None else (np.asarray(mask) != 0)
    if ign.shape != x.shape:
        raise ValueError("%s: mask %r and image %r differ in shape" % (fn, ign.shape, x.shape))
    r = w // 2
    h, wd = x.shape
    v = x.astype(np.int64)
    keep = ~ign
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy == 0 and dx == 0:
                continue
            if abs(dy) >= h or abs(dx) >= wd:
                continue                                                  # ★2026-10-07: 画像の外だけの隣(窓 > 画像で負の添字が回り込み numpy が落ちた)
            before = dy < 0 or (dy == 0 and dx < 0)
            ys0, ys1 = max(0, -dy), min(h, h - dy)
            xs0, xs1 = max(0, -dx), min(wd, wd - dx)
            c = v[ys0:ys1, xs0:xs1]
            nb = v[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
            nb_ign = ign[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
            ok = (c >= nb) if before else (c > nb)
            ok = ok | nb_ign
            keep[ys0:ys1, xs0:xs1] &= ok
    out = x.copy()
    out[~(keep | ign)] = 0 if x.dtype == np.uint8 else INT16_MIN
    return out


# ─────────────────────────────── 第 2 陣: 幾何(3.56 / 3.57 / 3.44)と非線形フィルタ(3.38) ─────────────────────────────
_INTERP = ("nearest", "bilinear")
_GEOM_BORDERS = ("constant", "undefined")          # REQ-0506: ワープと remap の境界は UNDEFINED と CONSTANT だけ


def _sample(img, x0, y0, interpolation, border, constant_value, fn):
    """画素の中心で標本を取る(整数座標 = 画素の中心、4.4.6 節)。外は constant で埋める(undefined は 0 —— 値は規格上未定義)。

    最近傍 = 中心がいちばん近い画素。★ちょうど真ん中(.5)は規格に無いので ⌊x + 0.5⌋(+∞ 側)に寄せる。
    双線形 = 中心からの距離で重みづけ、U8 への戻しは ⌊v + 0.5⌋(規格に無い丸め —— 明記)。
    """
    if interpolation not in _INTERP:
        raise ValueError("%s: interpolation must be one of %r (VX_INTERPOLATION_AREA is not supported, REQ-0503) (got %r)"
                         % (fn, _INTERP, interpolation))
    if border not in _GEOM_BORDERS:
        raise ValueError("%s: border must be one of %r — the standard supports only UNDEFINED and CONSTANT here (got %r)"
                         % (fn, _GEOM_BORDERS, border))
    cv = int(constant_value) if border == "constant" else 0
    if not 0 <= cv <= 255:
        raise ValueError("%s: constant_value must be in 0..255 (got %r)" % (fn, constant_value))
    h, w = img.shape
    src = img.astype(np.float64)
    finite = np.isfinite(x0) & np.isfinite(y0)
    x0 = np.where(finite, x0, -1e9)
    y0 = np.where(finite, y0, -1e9)

    def at(yi, xi):
        inside = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
        v = np.full(xi.shape, float(cv))
        v[inside] = src[yi[inside], xi[inside]]
        return v

    if interpolation == "nearest":
        out = at(np.floor(y0 + 0.5).astype(np.int64), np.floor(x0 + 0.5).astype(np.int64))
    else:
        xf, yf = np.floor(x0), np.floor(y0)
        ax, ay = x0 - xf, y0 - yf
        xi, yi = xf.astype(np.int64), yf.astype(np.int64)
        out = ((1 - ax) * (1 - ay) * at(yi, xi) + ax * (1 - ay) * at(yi, xi + 1)
               + (1 - ax) * ay * at(yi + 1, xi) + ax * ay * at(yi + 1, xi + 1))
        out = np.floor(out + 0.5)
    out[~finite] = cv
    return np.clip(out, 0, 255).astype(np.uint8)


def vx_warp_affine(image, matrix, *, interpolation, border, constant_value=0):
    """アフィン変換(3.56 節)。**逆写像**: 出力の画素 (x, y) は入力の (x0, y0) から取る(REQ-0498):
    ``x0 = M[0,0]·x + M[0,1]·y + M[0,2]``、``y0 = M[1,0]·x + M[1,1]·y + M[1,2]``。

    *matrix*: 数学の並びの 2×3(1 行目が x0 の係数 a, b, c)。★規格の C の宣言は ``mat[3][2] = { {a,d}, {b,e}, {c,f} }``
    (転置した並び)—— C の配列をそのまま渡すと形が (3, 2) になるので止める。*interpolation*(必須): ``"nearest"`` / ``"bilinear"``。
    *border*(必須): ``"constant"``(*constant_value* で埋める)/ ``"undefined"``(0 で埋める、値は規格上未定義)。

    **Raises** ``ValueError``: U8 の 2-D でない / matrix が 2×3 の有限でない / interpolation・border が一覧に無い。
    """
    fn = "vx_warp_affine"
    x = _img(image, "image", fn, (np.uint8,))
    M = np.asarray(matrix, np.float64)
    if M.shape != (2, 3) or not np.isfinite(M).all():
        raise ValueError("%s: matrix must be a finite 2x3 array in mathematical layout (got shape %r) — the C declaration "
                         "mat[3][2] is the transpose" % (fn, M.shape))
    h, w = x.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    x0 = M[0, 0] * xx + M[0, 1] * yy + M[0, 2]
    y0 = M[1, 0] * xx + M[1, 1] * yy + M[1, 2]
    return _sample(x, x0, y0, interpolation, border, constant_value, fn)


def vx_warp_perspective(image, matrix, *, interpolation, border, constant_value=0):
    """射影変換(3.57 節)。逆写像: ``x0 = M[0]·(x, y, 1)``、``y0 = M[1]·(x, y, 1)``、``z0 = M[2]·(x, y, 1)``、
    出力 (x, y) = 入力 (x0/z0, y0/z0)(REQ-0508)。z0 = 0 の画素は外として埋める。

    *matrix*: 数学の並びの 3×3(規格の C の宣言 ``mat[3][3]`` は転置した並び)。他の引数は :func:`vx_warp_affine` と同じ。

    **Raises** ``ValueError``: U8 の 2-D でない / matrix が 3×3 の有限でない / interpolation・border が一覧に無い。
    """
    fn = "vx_warp_perspective"
    x = _img(image, "image", fn, (np.uint8,))
    M = np.asarray(matrix, np.float64)
    if M.shape != (3, 3) or not np.isfinite(M).all():
        raise ValueError("%s: matrix must be a finite 3x3 array in mathematical layout (got shape %r)" % (fn, M.shape))
    h, w = x.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    x0 = M[0, 0] * xx + M[0, 1] * yy + M[0, 2]
    y0 = M[1, 0] * xx + M[1, 1] * yy + M[1, 2]
    z0 = M[2, 0] * xx + M[2, 1] * yy + M[2, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        u = np.where(z0 != 0, x0 / z0, np.nan)
        v = np.where(z0 != 0, y0 / z0, np.nan)
    return _sample(x, u, v, interpolation, border, constant_value, fn)


def vx_remap(image, map_x, map_y, *, interpolation, border, constant_value=0):
    """remap(3.44 節): 出力 (x, y) = 入力 (map_x[y, x], map_y[y, x])(REQ-0392)。表は出力の形、座標は入力の画素の中心が整数。

    **Raises** ``ValueError``: U8 の 2-D でない / map_x と map_y が同じ形の 2-D の実数でない / interpolation・border が一覧に無い。
    """
    fn = "vx_remap"
    x = _img(image, "image", fn, (np.uint8,))
    mx = np.asarray(map_x, np.float64)
    my = np.asarray(map_y, np.float64)
    if mx.ndim != 2 or mx.shape != my.shape:
        raise ValueError("%s: map_x %r and map_y %r must be 2-D arrays of the output shape" % (fn, mx.shape, my.shape))
    return _sample(x, mx, my, interpolation, border, constant_value, fn)


def vx_nonlinear_filter(image, mask, *, function, border, constant_value=0, origin=None):
    """非線形フィルタ(3.38 節): マスクの真の画素の値の中央値 / 最小(収縮)/ 最大(膨張)(REQ-0325・0330)。

    *function*: ``"median"`` / ``"min"`` / ``"max"``(vx_non_linear_filter_e)。*mask*: 2-D の bool(BOX / CROSS / DISK / OTHER の
    どれでも)。*origin*: マスクの原点 (行, 列)(VX_MATRIX_ORIGIN、既定は中央 ``(rows // 2, cols // 2)``)。
    *border*(必須): ``"replicate"`` / ``"constant"`` / ``"undefined"``(端は 0 で埋めて計算する —— 値は規格上未定義)。
    ★マスクの画素数が偶数のときの中央値は規格に無い —— 昇順に並べた ``n // 2`` 番目(上側の中央値、scipy の median_filter と同じ)を取る。
    REQ-0327: 9×9 までのマスクは必ず扱う(この実装に上限は無い)。

    **Raises** ``ValueError``: U8 の 2-D でない / function が一覧に無い / mask が 2-D の bool でない・空 / origin がマスクの外。
    """
    fn = "vx_nonlinear_filter"
    x = _img(image, "image", fn, (np.uint8,))
    if function not in ("median", "min", "max"):
        raise ValueError("%s: function must be 'median', 'min' or 'max' (got %r)" % (fn, function))
    m = np.asarray(mask)
    if m.ndim != 2 or m.dtype != bool or not m.any():
        raise ValueError("%s: mask must be a non-empty 2-D boolean array (got shape %r, dtype %s)" % (fn, m.shape, m.dtype))
    mr, mc = m.shape
    oy, ox = (mr // 2, mc // 2) if origin is None else (int(origin[0]), int(origin[1]))
    if not (0 <= oy < mr and 0 <= ox < mc):
        raise ValueError("%s: origin %r lies outside the %dx%d mask" % (fn, origin, mr, mc))
    if border not in _BORDERS:
        raise ValueError("%s: border must be one of %r (got %r)" % (fn, _BORDERS, border))
    cv = int(constant_value)
    if not 0 <= cv <= 255:
        raise ValueError("%s: constant_value must be in 0..255 (got %r)" % (fn, constant_value))
    h, w = x.shape
    pt, pb, pl, pr = oy, mr - 1 - oy, ox, mc - 1 - ox
    mode = {"replicate": "edge", "constant": "constant", "undefined": "constant"}[border]
    kw = {"constant_values": cv if border == "constant" else 0} if mode == "constant" else {}
    p = np.pad(x, ((pt, pb), (pl, pr)), mode=mode, **kw)
    stack = np.stack([p[i:i + h, j:j + w] for i, j in zip(*np.nonzero(m))], axis=0)
    if function == "min":
        return stack.min(axis=0).astype(np.uint8)
    if function == "max":
        return stack.max(axis=0).astype(np.uint8)
    return np.sort(stack, axis=0)[stack.shape[0] // 2].astype(np.uint8)

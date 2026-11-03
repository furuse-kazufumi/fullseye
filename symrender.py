# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""記号の撮像シミュレーション —— 印字(にじみ・刻印の点)→ 幾何(回転・あおり)→ 照明 →
光学(デフォーカス・動きぶれ)→ センサ(ショット雑音・読み出し雑音・量子化)。

Physical capture model for the symbol-reading family: a symbol (1-D bar widths or a
2-D module grid) is printed (ink spread / dot-peen dots), placed on a plane seen by a
pinhole camera (in-plane rotation, tilt = perspective), lit non-uniformly, blurred by
the lens (defocus pillbox, motion line, Gaussian) and recorded by a sensor (Poisson
shot noise from the full-well electron count, Gaussian read noise, quantisation).
Every knob is a physical quantity with a unit, so a read-rate sweep over one of them
(``symbolpod.py``) answers "how much of *this* can the reader take".

順番は物理の順(反射率 × 照明 → 投影 → ぼけ → 光電変換)。ぼけを投影の後に掛けるのは、
デフォーカスと動きぶれが**像面で**一定の大きさだから(画素単位で指定する)。
The order follows the physics: blur is applied on the image plane, so its sizes are in
pixels.

座標 / coordinates: シンボルの平面は**モジュール単位**の ``(u, v)``(u = 列方向、
v = 行方向、左上が 0)。``homography`` は ``[u, v, 1] → [col, row, w]``。
The symbol plane is in module units ``(u, v)``; ``homography`` maps ``[u, v, 1]`` to
``[col, row, w]`` pixels.

出典 / sources: 薄肉レンズのぼけ円(幾何光学)= E. Hecht, *Optics*, 5th ed., 2017 /
撮像素子の雑音モデル(ショット + 読み出し + 量子化)= EMVA Standard 1288, Release 4.0,
2021(公開)/ にじみを Chebyshev 距離の膨張・収縮で表すのはここでの単純化(角は四角く太る)。
"""
from __future__ import annotations

import numpy as np

__all__ = ["render_symbol", "capture_degrade", "symbol_scene"]


def _num(x, name, op, lo=None, hi=None, allow_none=False):
    if x is None and allow_none:
        return None
    if isinstance(x, bool):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, x))
    try:
        v = float(x)
    except (TypeError, ValueError) as exc:
        raise ValueError("%s: %s must be a number, got %r" % (op, name, x)) from exc
    if not np.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, x))
    if lo is not None and v < lo:
        raise ValueError("%s: %s must be >= %g, got %g" % (op, name, lo, v))
    if hi is not None and v > hi:
        raise ValueError("%s: %s must be <= %g, got %g" % (op, name, hi, v))
    return v


def _symbol_kind(symbol, op):
    """table / 配列から (種類, 形) を読む。1-D は edges、2-D は modules。"""
    if isinstance(symbol, dict):
        if "modules" in symbol and np.asarray(symbol["modules"]).ndim == 2:
            m = np.asarray(symbol["modules"])
            return "2d", m
        if "edges" in symbol and "quiet" in symbol:
            return "1d", symbol
        raise ValueError("%s: symbol table needs 'modules' (2-D grid) or 'edges' + 'quiet' "
                         "(1-D widths from encode_barcode1d)" % op)
    m = np.asarray(symbol)
    if m.ndim == 2:
        return "2d", m
    raise ValueError("%s: symbol must be a symbol table or a 2-D module grid, got shape %s"
                     % (op, m.shape))


def _default_quiet(symbol, kind):
    if isinstance(symbol, dict):
        if "quiet_modules" in symbol:
            return float(symbol["quiet_modules"])
        if "version" in symbol:                    # QR
            return 4.0
    return 4.0 if kind == "2d" and not isinstance(symbol, dict) else 2.0


def symbol_scene(symbol, *, quiet=None, bar_height=None, ink_gain=0.0, dot=None):
    """シンボルの平面(モジュール単位)の大きさと、点 → 暗さ(0/1)の判定関数を返す。

    Build the symbol plane: returns ``(width_modules, height_modules, dark(u, v))`` where
    ``dark`` evaluates arrays of plane points to booleans. ``ink_gain`` (modules) grows
    (> 0) or shrinks (< 0) every dark area by ``ink_gain / 2`` on each side (Chebyshev).
    ``dot`` (2-D only) draws each dark module as a disc of diameter ``dot`` modules
    (dot-peen / ink-jet marks) instead of a square.
    """
    op = "symbol_scene"
    kind, m = _symbol_kind(symbol, op)
    g = _num(ink_gain, "ink_gain", op, -0.9, 0.9)
    r = 0.5 * abs(g)
    if kind == "1d":
        ql, qr = (float(x) for x in symbol["quiet"])
        edges = np.asarray(symbol["edges"], dtype=np.float64)
        W = float(edges[-1] + qr)
        Hb = _num(bar_height, "bar_height", op, 1.0, allow_none=True)
        if Hb is None:
            Hb = max(15.0, 0.35 * float(edges[-1] - edges[0]))
        q = 2.0 if quiet is None else _num(quiet, "quiet", op, 0.0)   # 縦の余白 / vertical margin
        Ht = Hb + 2.0 * q
        starts, ends = edges[0:-1:2], edges[1::2]

        def dark(u, v):
            inside_v = (v >= q) & (v <= q + Hb)
            if g >= 0:
                lo_u, hi_u = u + r, u - r       # 区間 [u-r, u+r] がバーに触れる
                k = np.searchsorted(starts, lo_u, side="right") - 1
                kk = np.clip(k, 0, starts.size - 1)
                hit = (k >= 0) & (ends[kk] >= hi_u)
            else:
                k = np.searchsorted(starts, u - r, side="right") - 1
                kk = np.clip(k, 0, starts.size - 1)
                hit = (k >= 0) & (starts[kk] <= u - r) & (ends[kk] >= u + r)
            return hit & inside_v
        return W, Ht, dark

    mods = (np.asarray(m) != 0)
    R, C = mods.shape
    if R < 1 or C < 1:
        raise ValueError("%s: empty module grid" % op)
    q = _default_quiet(symbol, kind) if quiet is None else _num(quiet, "quiet", op, 0.0)
    pad = np.zeros((R + 4, C + 4), bool)
    pad[2:-2, 2:-2] = mods
    dd = _num(dot, "dot", op, 0.05, 2.0, allow_none=True)

    def lookup(ii, jj):
        return pad[np.clip(ii + 2, 0, R + 3), np.clip(jj + 2, 0, C + 3)]

    def dark(u, v):
        x, y = u - q, v - q
        if dd is not None:
            rad = 0.5 * dd + 0.5 * g
            i0, j0 = np.floor(y).astype(int), np.floor(x).astype(int)
            out = np.zeros(np.shape(u), bool)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    ii, jj = i0 + di, j0 + dj
                    cy, cx = ii + 0.5, jj + 0.5
                    out |= lookup(ii, jj) & ((x - cx) ** 2 + (y - cy) ** 2 <= rad * rad)
            return out
        if r == 0:
            return lookup(np.floor(y).astype(int), np.floor(x).astype(int))
        ia, ib = np.floor(y - r).astype(int), np.floor(y + r - 1e-12).astype(int)
        ja, jb = np.floor(x - r).astype(int), np.floor(x + r - 1e-12).astype(int)
        if g > 0:
            out = np.zeros(np.shape(u), bool)
            for ii in (ia, ib):
                for jj in (ja, jb):
                    out |= lookup(ii, jj)
        else:
            out = np.ones(np.shape(u), bool)
            for ii in (ia, ib):
                for jj in (ja, jb):
                    out &= lookup(ii, jj)
        return out
    return C + 2 * q, R + 2 * q, dark


def _homography(Wm, Hm, module_px, rotate_deg, tilt_deg, tilt_axis_deg, distance_ratio, offset):
    """平面(u, v)→ 画素の射影。中心に置き、回転し、軸のまわりに傾け、ピンホールで写す。"""
    cu, cv = Wm / 2.0, Hm / 2.0
    T0 = np.array([[1, 0, -cu], [0, 1, -cv], [0, 0, 1]], float)
    th = np.deg2rad(rotate_deg)
    Rz = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
    # あおり: 平面の点 (x, y, 0) を、平面内の軸 a のまわりに tilt だけ回す
    a = np.deg2rad(tilt_axis_deg)
    ax = np.array([np.cos(a), np.sin(a), 0.0])
    t = np.deg2rad(tilt_deg)
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    Rt = np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * (K @ K)
    size = max(Wm, Hm)
    D = distance_ratio * size                    # カメラまでの距離(モジュール単位)
    f = module_px * D                            # 中心での倍率 = module_px [px/module]
    # [x, y, 0, 1] → カメラ座標 Rt @ [x, y, 0] + [0, 0, D]; 画素 = f X / Z
    P = np.array([[f, 0, 0], [0, f, 0], [0, 0, 1.0]]) @ np.column_stack([Rt[:, 0], Rt[:, 1], [0, 0, D]])
    Hm_ = P @ Rz @ T0
    # 画素の原点へ寄せる(後でキャンバスの大きさから決める)
    return Hm_ / Hm_[2, 2]


def _apply_h(H, x, y):
    w = H[2, 0] * x + H[2, 1] * y + H[2, 2]
    return (H[0, 0] * x + H[0, 1] * y + H[0, 2]) / w, (H[1, 0] * x + H[1, 1] * y + H[1, 2]) / w


def render_symbol(symbol, module_px=4.0, *, quiet=None, bar_height=None, rotate_deg=0.0,
                  tilt_deg=0.0, tilt_axis_deg=0.0, distance_ratio=10.0, offset_px=(0.0, 0.0),
                  ink_gain=0.0, dot=None, dark=0.05, light=0.85, margin_modules=2.0,
                  supersample=4, return_geometry=False):
    """シンボル(1-D の幅か 2-D のモジュール格子)を、平面の反射率画像として描く(``image2d``)。

    Render a symbol as the reflectance image a pinhole camera sees. ``module_px`` is
    the module (X dimension) size in pixels at the symbol centre; ``rotate_deg`` turns
    the symbol in its plane (counter-clockwise on screen), ``tilt_deg`` tilts the plane
    about an in-plane axis at ``tilt_axis_deg`` (perspective; the camera sits
    ``distance_ratio`` symbol sizes away, so 10 means mild keystone). ``ink_gain``
    (modules) widens dark areas (bar width gain, > 0) or narrows them (< 0); ``dot``
    draws 2-D dark modules as discs of that diameter (modules). Reflectances are
    ``dark`` (ink) and ``light`` (substrate); each pixel is the mean of
    ``supersample``² point samples (area coverage). The canvas holds the symbol, its
    quiet zone (``quiet`` modules; default 4 for QR and raw grids, 2 for the table
    from ``dm_encode`` unless the table says otherwise; for 1-D the table's own quiet
    zones and ``quiet`` is the margin above and below the bars) and a further
    ``margin_modules`` of substrate.

    ``return_geometry=True`` returns a table instead: ``image``, ``homography``
    (plane ``[u, v, 1]`` in modules → ``[col, row, w]``), ``plane_size`` (modules),
    ``module_px``.

    空の入力(モジュール格子が 0 行)は ``ValueError``。
    拒否(``ValueError``): 表に ``modules`` も ``edges`` も無い、``module_px`` <= 0.5、
    ``dark >= light``、反射率が [0, 1] の外、``|tilt_deg| >= 80``、``|ink_gain| > 0.9``、
    ``supersample`` が 1..16 の外、キャンバスが 4000 画素を超える。
    """
    op = "render_symbol"
    mpx = _num(module_px, "module_px", op, 0.5)
    rot = _num(rotate_deg, "rotate_deg", op)
    tilt = _num(tilt_deg, "tilt_deg", op, -79.9, 79.9)
    tax = _num(tilt_axis_deg, "tilt_axis_deg", op)
    dr = _num(distance_ratio, "distance_ratio", op, 1.5)
    dk = _num(dark, "dark", op, 0.0, 1.0)
    lt = _num(light, "light", op, 0.0, 1.0)
    if dk >= lt:
        raise ValueError("%s: dark (%g) must be below light (%g)" % (op, dk, lt))
    mm = _num(margin_modules, "margin_modules", op, 0.0)
    if isinstance(supersample, bool) or not isinstance(supersample, (int, np.integer)) \
            or not 1 <= supersample <= 16:
        raise ValueError("%s: supersample must be an integer in 1..16, got %r" % (op, supersample))
    try:
        ox, oy = (float(offset_px[0]), float(offset_px[1]))
    except (TypeError, IndexError, ValueError) as exc:
        raise ValueError("%s: offset_px must be (dx, dy)" % op) from exc
    Wm, Hm, darkfn = symbol_scene(symbol, quiet=quiet, bar_height=bar_height, ink_gain=ink_gain, dot=dot)
    H = _homography(Wm, Hm, mpx, rot, tilt, tax, dr, (ox, oy))
    # キャンバス: 余白込みの四隅を写した外接箱 / canvas = bbox of the margin-expanded corners
    cu = np.array([-mm, Wm + mm, Wm + mm, -mm])
    cv = np.array([-mm, -mm, Hm + mm, Hm + mm])
    px, py = _apply_h(H, cu, cv)
    if not (np.all(np.isfinite(px)) and np.all(np.isfinite(py))):
        raise ValueError("%s: the tilted plane passes behind the camera — reduce tilt_deg" % op)
    x0, y0 = np.floor(px.min()), np.floor(py.min())
    Wc, Hc = int(np.ceil(px.max() - x0)) + 1, int(np.ceil(py.max() - y0)) + 1
    if Wc > 4000 or Hc > 4000:
        raise ValueError("%s: canvas %dx%d exceeds 4000 px — lower module_px" % (op, Hc, Wc))
    S = np.array([[1, 0, -x0 + ox], [0, 1, -y0 + oy], [0, 0, 1.0]])
    H = S @ H
    Hinv = np.linalg.inv(H)
    ss = int(supersample)
    sub = (np.arange(ss) + 0.5) / ss - 0.5
    cols = (np.arange(Wc)[None, :, None, None] + sub[None, None, None, :])
    rows = (np.arange(Hc)[:, None, None, None] + sub[None, None, :, None])
    X = np.broadcast_to(cols, (Hc, Wc, ss, ss))
    Y = np.broadcast_to(rows, (Hc, Wc, ss, ss))
    u, v = _apply_h(Hinv, X, Y)
    cov = darkfn(u, v).mean(axis=(2, 3))
    img = lt - (lt - dk) * cov
    if return_geometry:
        return {"image": img, "homography": H, "plane_size": (float(Wm), float(Hm)),
                "module_px": mpx}
    return img


def _disk_kernel(d, ss=8):
    """直径 d 画素の一様な円(面積で積分)。d < 1 は恒等に近い。"""
    rad = 0.5 * d
    n = int(np.ceil(rad)) * 2 + 1
    c = n // 2
    sub = (np.arange(ss) + 0.5) / ss - 0.5
    yy = (np.arange(n)[:, None, None, None] - c + sub[None, None, :, None])
    xx = (np.arange(n)[None, :, None, None] - c + sub[None, None, None, :])
    k = ((xx ** 2 + yy ** 2) <= rad * rad).mean(axis=(2, 3))
    if k.sum() <= 0:
        k = np.zeros((1, 1)); k[0, 0] = 1.0
    return k / k.sum()


def _line_kernel(length, angle_deg, ss=8):
    """長さ length 画素の一様な線分(露光中の等速移動)。"""
    L = float(length)
    n = int(np.ceil(0.5 * L)) * 2 + 3
    c = n // 2
    th = np.deg2rad(angle_deg)
    t = (np.arange(ss * 64) + 0.5) / (ss * 64) - 0.5
    xs = c + t * L * np.cos(th)
    ys = c - t * L * np.sin(th)
    k = np.zeros((n, n))
    # 双一次で配る / bilinear splat
    x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
    fx, fy = xs - x0, ys - y0
    for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                      (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(k, (np.clip(y0 + dy, 0, n - 1), np.clip(x0 + dx, 0, n - 1)), w)
    return k / k.sum()


def capture_degrade(image, *, defocus_px=0.0, motion_px=0.0, motion_deg=0.0, gauss_px=0.0,
                    illum_slope=0.0, illum_deg=0.0, vignette=0.0, exposure=1.0, full_well_e=None,
                    read_noise_e=0.0, bits=None, seed=0):
    """反射率の画像に撮像の劣化(照明・ぼけ・センサ雑音)を掛ける(``image2d``)。

    Apply the capture chain to a reflectance image, in physical order:

    1. illumination: ``E = exposure · (1 + illum_slope · s) · (1 − vignette · ρ²)`` with
       ``s`` in [−0.5, 0.5] across the image along ``illum_deg`` and ``ρ`` = radius / half
       diagonal (so ``illum_slope = 0.4`` means 40 % more light on one side than the other);
    2. lens: defocus as a uniform disc of diameter ``defocus_px`` (the geometric blur
       circle ``c = A·|Δz|/z'`` in pixels), uniform motion over ``motion_px`` along
       ``motion_deg``, and a Gaussian of standard deviation ``gauss_px`` (residual
       aberrations / diffraction), each area-integrated, borders replicated;
    3. sensor (only if ``full_well_e`` is given): the irradiance 1.0 fills
       ``full_well_e`` electrons; Poisson shot noise, Gaussian read noise
       ``read_noise_e`` (electrons), saturation at full well, and ``bits``-bit
       quantisation if given. Output = electrons / full_well_e, in [0, 1].

    Deterministic for a given ``seed``. Without ``full_well_e`` the result is noise-free
    (``read_noise_e`` must then be 0).

    空の入力(辺が 0)は ``ValueError``。
    拒否(``ValueError``): 2-D でない、非有限、負のぼけ量、``|illum_slope| >= 2``、
    ``vignette`` が [0, 1) の外、``full_well_e`` < 10、``read_noise_e`` < 0 または
    ``full_well_e`` 無しで > 0、``bits`` が 1..16 の外。
    """
    op = "capture_degrade"
    from scipy import ndimage
    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError("%s: image must be 2-D, got shape %s" % (op, a.shape))
    if a.size == 0:
        raise ValueError("%s: image is empty" % op)
    if not np.isfinite(a).all():
        raise ValueError("%s: image has non-finite values" % op)
    dpx = _num(defocus_px, "defocus_px", op, 0.0, 200.0)
    mpx = _num(motion_px, "motion_px", op, 0.0, 200.0)
    mdeg = _num(motion_deg, "motion_deg", op)
    gpx = _num(gauss_px, "gauss_px", op, 0.0, 100.0)
    sl = _num(illum_slope, "illum_slope", op, -1.999, 1.999)
    ideg = _num(illum_deg, "illum_deg", op)
    vg = _num(vignette, "vignette", op, 0.0, 0.999)
    ex = _num(exposure, "exposure", op, 0.0)
    fw = _num(full_well_e, "full_well_e", op, 10.0, allow_none=True)
    rn = _num(read_noise_e, "read_noise_e", op, 0.0)
    if fw is None and rn > 0:
        raise ValueError("%s: read_noise_e needs full_well_e (noise is in electrons)" % op)
    if bits is not None and (isinstance(bits, bool) or not isinstance(bits, (int, np.integer))
                             or not 1 <= bits <= 16):
        raise ValueError("%s: bits must be an integer in 1..16 or None, got %r" % (op, bits))
    H, W = a.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
    th = np.deg2rad(ideg)
    span = abs(np.cos(th)) * max(W - 1, 1) + abs(np.sin(th)) * max(H - 1, 1)
    s = ((xx - cx) * np.cos(th) - (yy - cy) * np.sin(th)) / max(span, 1.0)
    rho2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / max(cx * cx + cy * cy, 1.0)
    E = ex * (1.0 + sl * s) * (1.0 - vg * rho2)
    out = a * np.clip(E, 0.0, None)
    if dpx > 0:
        # 1 画素より小さい円も面積で配る(3x3 の核)/ sub-pixel discs are area-integrated too
        out = ndimage.convolve(out, _disk_kernel(dpx), mode="nearest")
    if mpx > 0:
        out = ndimage.convolve(out, _line_kernel(mpx, mdeg), mode="nearest")
    if gpx > 0:
        out = ndimage.gaussian_filter(out, gpx, mode="nearest")
    if fw is not None:
        rng = np.random.default_rng(seed)
        e = rng.poisson(np.clip(out, 0.0, None) * fw).astype(np.float64)
        if rn > 0:
            e = e + rng.normal(0.0, rn, size=e.shape)
        e = np.clip(e, 0.0, fw)
        out = e / fw
        if bits is not None:
            lv = (1 << int(bits)) - 1
            out = np.round(out * lv) / lv
    else:
        out = np.clip(out, 0.0, 1.0)
        if bits is not None:
            lv = (1 << int(bits)) - 1
            out = np.round(out * lv) / lv
    return out

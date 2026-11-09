# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""calib_lm —— 真値つきのカメラ校正: チェッカー角の検出、Zhang 法 + 歪みの同時最適化(LM)、ステレオの同時校正、
校正の誤差・不確かさの地図、次の 1 枚の推薦。

Camera calibration with ground truth: checkerboard corner detection with sub-pixel refinement, Zhang's
method followed by a joint Levenberg-Marquardt refinement of intrinsics, Brown-Conrady distortion
(radial k1, k2, k3 and tangential p1, p2) and all board poses, joint stereo calibration, and the layer only
a simulator can add — calibration error maps against the known truth, the covariance of the estimate
mapped over the image, and which next pose would shrink it most.

## 既存の校正 op との関係 / relation to the existing calibration ops (並存、置き換えない)

* ``calib.camera_calibration`` (Zhang の閉形式で K だけ)は**初期値**として呼ぶ。閉形式は歪みを無視するので
  歪みのあるレンズでは K を大きく誤る(``k1 = −0.18`` で傾き 5 度なら fx が 41 %、そのノートの実測)。
  :func:`camera_calibration_lm` はその上で K・歪み・全姿勢を同時に詰める。
* ``camera.estimate_distortion``(直線から歪み、対応点なし)・``camera.undistort_points`` /
  ``undistort_image``(同じ Brown-Conrady、OpenCV の係数順 ``[k1, k2, p1, p2, k3]``)はそのまま使える:
  この族が返す ``K``(3x3、fx は列の軸)と ``dist`` を渡せばよい。
* ``caltab.find_caltab``(円マーク)と並んで、チェッカー板の角を :func:`find_checkerboard_corners` で拾う。
* ``caltab.binocular_calibration``(左右を別々に Zhang、相対姿勢を返さない)には触らない。相対姿勢の同時
  最適化は :func:`stereo_calibration_lm`。

## 座標規約 / conventions (opscalib と同じ)

画素は **(row, col)**、校正板の点は **(x, y)**(z = 0 の平面、mm)。内部では (u = col, v = row) で解く。
``K`` は ``[[fx, 0, cx], [0, fy, cy], [0, 0, 1]]``(fx・cx が列の軸)、歪みは OpenCV と同じ式と係数順。
板の姿勢 ``pose`` は板の座標 → カメラの座標の 4x4。

## 数値の門(tests/test_calib_lm.py)

* 合成の角(真の K・歪み・姿勢で投影)→ LM が真値を 1e-6 の相対誤差で取り戻す。雑音のある角では
  OpenCV の ``calibrateCamera`` / ``stereoCalibrate``(別実装、optional)と同じ極小に落ちる。
* 共分散が予測する fx などの標準偏差 = モンテカルロ(雑音の種 200 本)の実測の標準偏差(15 % 以内)。
* 角の検出: 描画の真値(画素を板へ逆に引いて 3x3 標本で塗った絵、投影の式とは別の経路)とのずれ。
* 誤差の地図: 推定 = 真値 → 0、cx だけ δ ずれ → どこでも δ px、奥行き Z での横ずれ δ·Z/fx(閉形式)。
* 次の 1 枚: 推薦した姿勢を足した校正は、最下位の姿勢を足した校正より実際の誤差が小さい(モンテカルロ)。

依存は numpy と scipy(角の検出の平滑化だけ ``scipy.ndimage``)。OpenCV は試験の照合相手としてだけ使う。
"""
from __future__ import annotations

import math

import numpy as np

import calib as _calib
import camera as _camera

_DIST_MODELS = {"none": (), "k1": (0,), "k1k2": (0, 1), "k1k2p1p2": (0, 1, 2, 3),
                "k1k2p1p2k3": (0, 1, 2, 3, 4)}
_DIST_NAMES = ("k1", "k2", "p1", "p2", "k3")
_INTR_NAMES = ("fx", "fy", "cx", "cy")
#: LM の反復の上限(安全のための線。合成でも実データでも 15〜40 回で収束するので利用者のつまみにしない)。
_MAX_ITER = 200
#: 鞍点の候補の下限(最大の強さに対する比)。
_MIN_RESPONSE = 0.1


# =========================================================================== #
# 入力の検査 / validation
# =========================================================================== #
def _arr(a, name, op, cols=None, min_rows=1):
    if isinstance(a, (str, bytes, dict)) or a is None:
        raise ValueError("%s: %s must be a numeric array (got %s)" % (op, name, type(a).__name__))
    x = np.asarray(a)
    if x.dtype == object or x.dtype.kind not in "biuf":
        raise ValueError("%s: %s must be real numbers" % (op, name))
    x = x.astype(np.float64)
    if cols is not None and (x.ndim != 2 or x.shape[1] != cols):
        raise ValueError("%s: %s must have shape (N, %d) (got %s)" % (op, name, cols, x.shape))
    if x.shape[0] < min_rows:
        raise ValueError("%s: %s needs >= %d rows (got %d)" % (op, name, min_rows, x.shape[0]))
    if not np.isfinite(x).all():
        raise ValueError("%s: %s contains NaN or inf" % (op, name))
    return x


def _num(v, name, op, lo=None, hi=None, lo_open=False):
    if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a real number (got %r)" % (op, name, v))
    x = float(v)
    if not math.isfinite(x) or (lo is not None and (x < lo or (lo_open and x == lo))) or (hi is not None and x > hi):
        raise ValueError("%s: %s out of range (got %r)" % (op, name, v))
    return x


def _kmat(K, op):
    if isinstance(K, dict):
        try:
            K = [[K["fx"], K.get("skew", 0.0), K["cx"]], [0.0, K["fy"], K["cy"]], [0.0, 0.0, 1.0]]
        except KeyError as e:
            raise ValueError("%s: camera dict needs fx, fy, cx, cy (missing %s)" % (op, e)) from None
    K = np.asarray(K, float)
    if K.shape != (3, 3) or not np.isfinite(K).all() or K[0, 0] <= 0 or K[1, 1] <= 0:
        raise ValueError("%s: K must be a finite 3x3 matrix with fx, fy > 0" % op)
    return K


def _dist(d, op):
    if d is None:
        return np.zeros(5)
    a = np.asarray(d, float).reshape(-1)
    if a.size == 4:
        a = np.r_[a, 0.0]
    if a.size != 5 or not np.isfinite(a).all():
        raise ValueError("%s: dist must be [k1, k2, p1, p2(, k3)] finite (got %r)" % (op, d))
    return a


def _pose(P, op, name="pose"):
    P = np.asarray(P, float)
    if P.shape not in ((4, 4), (3, 4)) or not np.isfinite(P).all():
        raise ValueError("%s: %s must be a finite 4x4 (or 3x4) rigid transform" % (op, name))
    R = P[:3, :3]
    if np.abs(R @ R.T - np.eye(3)).max() > 1e-6 or np.linalg.det(R) < 0:
        raise ValueError("%s: %s rotation is not orthonormal" % (op, name))
    return R.copy(), P[:3, 3].copy()


def _shape(shape, op):
    try:
        h, w = (int(shape[0]), int(shape[1]))
    except Exception:                                     # noqa: BLE001
        raise ValueError("%s: image_shape must be (H, W) (got %r)" % (op, shape)) from None
    if h < 8 or w < 8 or h * w > 25_000_000:
        raise ValueError("%s: image_shape out of range (got %r)" % (op, shape))
    return h, w


# =========================================================================== #
# 投影と解析的なヤコビアン / projection and analytic Jacobian
# =========================================================================== #
def _skew(v):
    """(N,3) -> (N,3,3) の歪対称行列 [v]x。"""
    z = np.zeros(len(v))
    return np.stack([np.stack([z, -v[:, 2], v[:, 1]], -1), np.stack([v[:, 2], z, -v[:, 0]], -1),
                     np.stack([-v[:, 1], v[:, 0], z], -1)], 1)


def _proj(Xc, intr, dist, jac=True):
    """カメラ座標の点 → 画素 (u, v) と、内部・歪み・点への微分。

    Project camera-frame points with the Brown-Conrady model. Returns ``uv (N,2)`` and, if ``jac``,
    ``J_intr (N,2,4)`` (fx, fy, cx, cy), ``J_dist (N,2,5)`` (k1, k2, p1, p2, k3), ``J_X (N,2,3)``."""
    fx, fy, cx, cy = intr
    k1, k2, p1, p2, k3 = dist
    X, Y, Z = Xc[:, 0], Xc[:, 1], Xc[:, 2]
    x, y = X / Z, Y / Z
    r2 = x * x + y * y
    rad = 1.0 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
    xd = x * rad + 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
    yd = y * rad + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
    uv = np.stack([fx * xd + cx, fy * yd + cy], 1)
    if not jac:
        return uv
    n = len(Xc)
    Ji = np.zeros((n, 2, 4))
    Ji[:, 0, 0], Ji[:, 0, 2] = xd, 1.0
    Ji[:, 1, 1], Ji[:, 1, 3] = yd, 1.0
    Jd = np.zeros((n, 2, 5))
    Jd[:, 0, 0], Jd[:, 1, 0] = fx * x * r2, fy * y * r2
    Jd[:, 0, 1], Jd[:, 1, 1] = fx * x * r2 ** 2, fy * y * r2 ** 2
    Jd[:, 0, 4], Jd[:, 1, 4] = fx * x * r2 ** 3, fy * y * r2 ** 3
    Jd[:, 0, 2], Jd[:, 1, 2] = fx * 2 * x * y, fy * (r2 + 2 * y * y)
    Jd[:, 0, 3], Jd[:, 1, 3] = fx * (r2 + 2 * x * x), fy * 2 * x * y
    rp = k1 + 2 * k2 * r2 + 3 * k3 * r2 ** 2
    dxx = rad + 2 * x * x * rp + 2 * p1 * y + 6 * p2 * x
    dxy = 2 * x * y * rp + 2 * p1 * x + 2 * p2 * y
    dyy = rad + 2 * y * y * rp + 6 * p1 * y + 2 * p2 * x
    dn = np.zeros((n, 2, 3))                              # d(x, y)/dXc
    dn[:, 0, 0], dn[:, 0, 2] = 1 / Z, -X / Z ** 2
    dn[:, 1, 1], dn[:, 1, 2] = 1 / Z, -Y / Z ** 2
    Dd = np.zeros((n, 2, 2))
    Dd[:, 0, 0], Dd[:, 0, 1] = fx * dxx, fx * dxy
    Dd[:, 1, 0], Dd[:, 1, 1] = fy * dxy, fy * dyy
    return uv, Ji, Jd, Dd @ dn


def _exp(w):
    return _camera.rodrigues(w)


# =========================================================================== #
# 校正板 / checkerboard
# =========================================================================== #
def checkerboard_points(pattern_size, square_size):
    """チェッカー板の内側の角の板座標 (x, y) を行優先で返す(``keypoints``)。

    Board coordinates (x, y) of the inner corners of a checkerboard with ``pattern_size = (cols, rows)``
    inner corners and squares of ``square_size`` (mm), row-major: index ``r·cols + c`` is
    ``(c·square, r·square)``. The first corner is the origin (OpenCV's convention for
    ``findChessboardCorners``). The board has ``(cols + 1) x (rows + 1)`` squares.

    **Raises** ``ValueError``: cols・rows が 2 未満・整数でない、``square_size`` が正でない。
    """
    op = "checkerboard_points"
    cols, rows = _pattern(pattern_size, op)
    s = _num(square_size, "square_size", op, lo=0.0, lo_open=True)
    r, c = np.mgrid[0:rows, 0:cols]
    return np.column_stack([c.ravel() * s, r.ravel() * s]).astype(float)


def _pattern(p, op):
    try:
        cols, rows = int(p[0]), int(p[1])
    except Exception:                                     # noqa: BLE001
        raise ValueError("%s: pattern_size must be (cols, rows) (got %r)" % (op, p)) from None
    if cols != p[0] or rows != p[1] or cols < 2 or rows < 2 or cols * rows > 10000:
        raise ValueError("%s: pattern_size must be integers >= 2 (got %r)" % (op, p))
    return cols, rows


def _undistort_norm(xd, yd, dist, iters=30):
    """歪んだ正規化座標 → 理想の正規化座標(固定点反復)。Fixed-point inverse of the distortion."""
    k1, k2, p1, p2, k3 = dist
    x, y = xd.copy(), yd.copy()
    for _ in range(iters):
        r2 = x * x + y * y
        rad = 1.0 + k1 * r2 + k2 * r2 ** 2 + k3 * r2 ** 3
        dx = 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
        dy = p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
        x = (xd - dx) / rad
        y = (yd - dy) / rad
    return x, y


def sim_checkerboard(pattern_size, square_size, K, dist, pose, image_shape, supersample=3, margin=1.0,
                     blur_sigma=0.0, noise_sigma=0.0, seed=0, black=0.1, white=0.9, background=0.5):
    """既知の K・歪み・姿勢でチェッカー板の画像を合成し、角の真の画素とともに返す(``table``)。

    Render a checkerboard seen through a camera with known intrinsics ``K`` (3x3 or {fx, fy, cx, cy}),
    distortion ``dist`` ([k1, k2, p1, p2(, k3)], OpenCV order) and board pose ``pose`` (board -> camera
    4x4), with the true pixel of every inner corner.

    描画は**投影の式とは逆向きの経路**: 画素(``supersample`` x ``supersample`` の標本)ごとに歪みを固定点反復で
    外し、視線を板の平面に当てて板の座標を求め、その色(黒・白・板の外の余白 ``margin`` マス分は白、その外は
    ``background``)を塗って平均する。真の角は板の点を前向きに投影した値。だから検出の誤差は「描画の標本化 +
    検出器」の誤差で、式の写しにはならない。``blur_sigma``(画素)でガウスぼけ、``noise_sigma`` で正規雑音。

    返す ``dict``: ``image`` (H, W) [0, 1]、``corners`` (N, 2) **(row, col)**、``object_points`` (N, 2) (x, y)、
    ``visible``(全部の角が画像の内側 2 画素以上にある)、``pattern_size``、``square_size``、``K``、``dist``、``pose``。

    **Raises** ``ValueError``: 引数の形・範囲(K が正でない、姿勢が剛体でない、板が背後にある、
    supersample が 1〜8 の外、色が [0, 1] の外)。
    """
    op = "sim_checkerboard"
    cols, rows = _pattern(pattern_size, op)
    s = _num(square_size, "square_size", op, lo=0.0, lo_open=True)
    Km = _kmat(K, op)
    d = _dist(dist, op)
    R, t = _pose(pose, op)
    H, W = _shape(image_shape, op)
    ss = supersample
    if isinstance(ss, bool) or not isinstance(ss, (int, np.integer)) or not 1 <= ss <= 8:
        raise ValueError("%s: supersample must be an integer in [1, 8]" % op)
    m = _num(margin, "margin", op, lo=0.0, hi=5.0)
    bs = _num(blur_sigma, "blur_sigma", op, lo=0.0, hi=20.0)
    ns = _num(noise_sigma, "noise_sigma", op, lo=0.0, hi=1.0)
    blk, wht, bg = (_num(v, n, op, lo=0.0, hi=1.0) for v, n in ((black, "black"), (white, "white"),
                                                                (background, "background")))
    obj = checkerboard_points((cols, rows), s)
    Xc = np.column_stack([obj, np.zeros(len(obj))]) @ R.T + t
    if np.any(Xc[:, 2] <= 0):
        raise ValueError("%s: part of the board is behind the camera" % op)
    uv = _proj(Xc, (Km[0, 0], Km[1, 1], Km[0, 2], Km[1, 2]), d, jac=False)
    out = np.zeros((H, W))
    n3 = R[:, 2]
    off = (np.arange(ss) + 0.5) / ss - 0.5
    cc = np.arange(W, dtype=float)
    for rr0 in range(0, H, 64):                           # 帯ごと(記憶を抑える)/ in bands
        rr = np.arange(rr0, min(H, rr0 + 64), dtype=float)
        acc = np.zeros((len(rr), W))
        for oy in off:
            for ox in off:
                Cg, Rg = np.meshgrid(cc + ox, rr + oy)
                xd = (Cg - Km[0, 2] - Km[0, 1] * 0) / Km[0, 0]
                yd = (Rg - Km[1, 2]) / Km[1, 1]
                x, y = _undistort_norm(xd, yd, d)
                ray = np.stack([x, y, np.ones_like(x)], -1)
                den = ray @ n3
                with np.errstate(divide="ignore", invalid="ignore"):
                    lam = np.where(den > 1e-12, (n3 @ t) / den, np.nan)
                Pb = (ray * lam[..., None] - t) @ R               # 板の座標 / board coordinates
                bx, by = Pb[..., 0], Pb[..., 1]
                ix, iy = np.floor(bx / s), np.floor(by / s)
                inside = (ix >= 0 - 1) & (ix <= cols - 1) & (iy >= -1) & (iy <= rows - 1)
                on_board = (bx >= -s * (1 + m)) & (bx <= s * (cols + m)) & (by >= -s * (1 + m)) & \
                    (by <= s * (rows + m))
                col = np.where(((ix + iy) % 2) == 0, blk, wht)
                col = np.where(inside, col, wht)
                col = np.where(on_board & np.isfinite(lam) & (lam > 0), col, bg)
                acc += col
        out[rr0:rr0 + len(rr)] = acc / (ss * ss)
    if bs > 0:
        from scipy import ndimage as _ndi
        out = _ndi.gaussian_filter(out, bs, mode="nearest")
    if ns > 0:
        out = out + np.random.default_rng(seed).normal(0.0, ns, out.shape)
    out = np.clip(out, 0.0, 1.0)
    vis = bool(np.all((uv[:, 0] >= 2) & (uv[:, 0] <= W - 3) & (uv[:, 1] >= 2) & (uv[:, 1] <= H - 3)))
    P = np.eye(4)
    P[:3, :3], P[:3, 3] = R, t
    return {"image": out, "corners": uv[:, ::-1].copy(), "object_points": obj, "visible": vis,
            "pattern_size": (cols, rows), "square_size": s, "K": Km, "dist": d, "pose": P}


def find_checkerboard_corners(image, pattern_size, sigma=1.5, refine_window=None):
    """チェッカー板の画像から内側の角をサブピクセルで検出し、板の行優先の順で返す(``keypoints``)。

    Detect the inner corners of a checkerboard with ``pattern_size = (cols, rows)`` inner corners, refine
    them to sub-pixel accuracy and return them as (row, col) in the board's row-major order
    (pairs with :func:`checkerboard_points`).

    手順: (1) ガウスの 2 階微分(尺度 ``sigma``)で鞍点の強さ ``−det(Hessian)`` を出し、局所最大を候補に
    (2) 各候補を Förstner の勾配直交の式(OpenCV の ``cornerSubPix`` と同じ原理: 窓の中の勾配 g が角へ向かう
    ベクトルと直交 → ``Σ g gᵀ (p − q) = 0``)で反復して詰める(Förstner & Gülch 1987)
    (3) 最寄りの近傍から格子の 2 方向を決め、局所の平行四辺形で予測しながら格子を伸ばす
    (4) 埋まった格子が ``cols x rows``(または転置)でなければ拒否。
    順の約束: 列の方向 = 長さ cols の軸。2 つの軸の向きは「画像で右手系(板を表から見る)」と
    「最初の角が画像の左上に最も近い」で決める。★対称な板の 180 度の回転は区別しない —— 校正には効かない
    (板の点の集合がその回転で自分に写るので、姿勢が 180 度回るだけ)。cols = rows の板では 90 度も区別しない。

    返す ``(N, 2)``: (row, col)、N = cols·rows。

    **Raises** ``ValueError``: 画像が 2 次元でない・非有限、角の数が合わない・格子が組めない(板が見えない・
    ぼけすぎ・一部が画像の外)、引数の範囲外。
    """
    op = "find_checkerboard_corners"
    cols, rows = _pattern(pattern_size, op)
    img = np.asarray(image, float)
    if img.ndim != 2 or min(img.shape) < 16 or not np.isfinite(img).all():
        raise ValueError("%s: image must be a finite 2-D array of at least 16x16" % op)
    sg = _num(sigma, "sigma", op, lo=0.5, hi=10.0)
    mr = _MIN_RESPONSE   # 鞍点の強さの下限(最大の 10 %)。X 字の判定が後で偽の候補を落とすので外に出さない
    from scipy import ndimage as _ndi
    Ixx = _ndi.gaussian_filter(img, sg, order=(0, 2))
    Iyy = _ndi.gaussian_filter(img, sg, order=(2, 0))
    Ixy = _ndi.gaussian_filter(img, sg, order=(1, 1))
    resp = -(Ixx * Iyy - Ixy * Ixy) * sg ** 4
    resp = np.where(resp > 0, resp, 0.0)
    if resp.max() <= 0:
        raise ValueError("%s: no saddle point found (is there a checkerboard?)" % op)
    nms = int(max(3, round(2 * sg))) * 2 + 1
    peak = (resp == _ndi.maximum_filter(resp, size=nms)) & (resp >= mr * resp.max())
    b = int(math.ceil(3 * sg))
    peak[:b], peak[-b:], peak[:, :b], peak[:, -b:] = False, False, False, False
    cand = np.argwhere(peak).astype(float)              # (row, col)
    if len(cand) < cols * rows:
        raise ValueError("%s: found %d saddle candidates, need %d" % (op, len(cand), cols * rows))
    if len(cand) > 20 * cols * rows:
        order = np.argsort(-resp[peak])
        cand = cand[order[:20 * cols * rows]]
    # 格子の目の大きさ / grid spacing from nearest-neighbour distances
    D = np.linalg.norm(cand[:, None] - cand[None], axis=-1)
    np.fill_diagonal(D, np.inf)
    nn = np.median(np.min(D, axis=1))
    win = int(refine_window) if refine_window is not None else int(max(2, min(8, round(0.35 * nn))))
    if not 1 <= win <= 20:
        raise ValueError("%s: refine_window must be in [1, 20]" % op)
    gy, gx = np.gradient(_ndi.gaussian_filter(img, 0.7))
    ref = np.array([_refine(gx, gy, p, win) for p in cand])
    ok = np.isfinite(ref).all(1)
    ref = ref[ok]
    # X 字の角だけを残す: 円周上で明暗が 4 回入れ替わる(L 字の角は 2 回)/ keep X-junctions only
    ref = ref[[_is_x_corner(img, p, max(2.5, 0.3 * nn)) for p in ref]] if len(ref) else ref
    grid = _grow_grid(ref, cols, rows)
    if grid is None:
        raise ValueError("%s: could not assemble a %dx%d corner grid (board partly hidden, too blurred or "
                         "too oblique)" % (op, cols, rows))
    return grid


def _is_x_corner(img, p, radius, n=48):
    """円周上の明暗の入れ替わりが 4 回なら X 字の角。Four sign changes on a circle = an X-junction."""
    from scipy import ndimage as _ndi
    a = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    rr, cc = p[0] + radius * np.sin(a), p[1] + radius * np.cos(a)
    if rr.min() < 0 or cc.min() < 0 or rr.max() > img.shape[0] - 1 or cc.max() > img.shape[1] - 1:
        return False
    v = _ndi.map_coordinates(img, [rr, cc], order=1)
    lo, hi = v.min(), v.max()
    if hi - lo < 1e-6:
        return False
    b = v > 0.5 * (lo + hi)
    return int(np.sum(b != np.roll(b, 1))) == 4


def _refine(gx, gy, p, win, iters=20):
    """Förstner の勾配直交でサブピクセルへ。Gradient-orthogonality refinement (cornerSubPix principle)."""
    H, W = gx.shape
    q = p.copy()
    yy, xx = np.mgrid[-win:win + 1, -win:win + 1]
    w = np.exp(-(xx ** 2 + yy ** 2) / (2.0 * (0.6 * win) ** 2))
    for _ in range(iters):
        r0, c0 = int(round(q[0])), int(round(q[1]))
        if r0 - win - 1 < 0 or c0 - win - 1 < 0 or r0 + win + 1 >= H or c0 + win + 1 >= W:
            return np.array([np.nan, np.nan])
        sx = gx[r0 - win:r0 + win + 1, c0 - win:c0 + win + 1]
        sy = gy[r0 - win:r0 + win + 1, c0 - win:c0 + win + 1]
        pr, pc = yy + r0, xx + c0
        a, bxy, c = (w * sx * sx).sum(), (w * sx * sy).sum(), (w * sy * sy).sum()
        M = np.array([[c, bxy], [bxy, a]])                # (row, col) 順 / in (row, col) order
        rhs = np.array([(w * (sy * sy * pr + sx * sy * pc)).sum(), (w * (sx * sy * pr + sx * sx * pc)).sum()])
        if abs(np.linalg.det(M)) < 1e-12 * max(1.0, np.trace(M) ** 2):
            return np.array([np.nan, np.nan])
        qn = np.linalg.solve(M, rhs)
        if np.linalg.norm(qn - p) > 1.5 * win:
            return np.array([np.nan, np.nan])
        done = np.linalg.norm(qn - q) < 1e-4
        q = qn
        if done:
            break
    return q


def _grow_grid(pts, cols, rows):
    """候補の点から格子を伸ばし、(cols x rows) を行優先の (row, col) で返す。失敗は None。"""
    n = len(pts)
    D = np.linalg.norm(pts[:, None] - pts[None], axis=-1)
    np.fill_diagonal(D, np.inf)
    cen = np.median(pts, axis=0)
    best = None
    for seed in np.argsort(np.linalg.norm(pts - cen, axis=1))[:6]:
        nb = np.argsort(D[seed])[:6]
        e1 = pts[nb[0]] - pts[seed]
        e2 = None
        for j in nb[1:]:
            v = pts[j] - pts[seed]
            if abs(v @ e1) / (np.linalg.norm(v) * np.linalg.norm(e1)) < 0.5:
                e2 = v
                break
        if e2 is None:
            continue
        idx = {(0, 0): seed}
        used = {seed}
        queue = [(0, 0)]
        while queue:
            i, j = queue.pop(0)
            p = pts[idx[(i, j)]]
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                key = (i + di, j + dj)
                if key in idx:
                    continue
                back = (i - di, j - dj)
                if back in idx:
                    pred = 2 * p - pts[idx[back]]
                else:
                    # 局所の基底: 近くの割り当て済みの点から / local basis from assigned neighbours
                    u1 = e1
                    u2 = e2
                    if (i + 1, j) in idx:
                        u1 = pts[idx[(i + 1, j)]] - p
                    elif (i - 1, j) in idx:
                        u1 = p - pts[idx[(i - 1, j)]]
                    if (i, j + 1) in idx:
                        u2 = pts[idx[(i, j + 1)]] - p
                    elif (i, j - 1) in idx:
                        u2 = p - pts[idx[(i, j - 1)]]
                    pred = p + di * u1 + dj * u2
                step = np.linalg.norm(pred - p)
                dd = np.linalg.norm(pts - pred, axis=1)
                k = int(np.argmin(dd))
                if dd[k] < 0.3 * step and k not in used:
                    idx[key] = k
                    used.add(k)
                    queue.append(key)
        I = np.array([k[0] for k in idx])
        J = np.array([k[1] for k in idx])
        ni, nj = I.max() - I.min() + 1, J.max() - J.min() + 1
        full = len(idx) == ni * nj
        if full and {ni, nj} == {cols, rows} and len(idx) == cols * rows:
            best = (idx, I.min(), J.min(), ni, nj)
            break
    if best is None:
        return None
    idx, i0, j0, ni, nj = best
    G = np.zeros((ni, nj, 2))
    for (i, j), k in idx.items():
        G[i - i0, j - j0] = pts[k]
    # 列の軸 = 長さ cols の軸 / the column axis is the one of length cols
    if ni == cols and nj == rows and cols != rows:
        G = G.transpose(1, 0, 2)                          # -> (rows, cols)
    elif cols == rows:
        # 列の方向 = 画像の横(col)に近い軸 / column axis closest to the image x direction
        a0 = G[0, -1] - G[0, 0]                           # 軸 1 方向
        a1 = G[-1, 0] - G[0, 0]
        if abs(a1[1]) > abs(a0[1]):
            G = G.transpose(1, 0, 2)
    # 右手系(x = col 右、y = row 下)にする / make (col axis, row axis) right-handed in the image
    ex = G[0, -1] - G[0, 0]
    ey = G[-1, 0] - G[0, 0]
    cross = ex[1] * ey[0] - ex[0] * ey[1]                 # (x=col, y=row) での z 成分
    if cross < 0:
        G = G[:, ::-1]
    # 180 度の候補から左上に近いほう / of the two 180-degree choices take the corner nearest the top-left
    if G[-1, -1].sum() < G[0, 0].sum():
        G = G[::-1, ::-1]
    return G.reshape(-1, 2)


# =========================================================================== #
# 単眼の校正(Zhang + LM)/ monocular calibration
# =========================================================================== #
def _init_pose(H, K):
    """平面のホモグラフィ(板 (x,y) → 画素 (u,v))と K から板の姿勢の初期値。"""
    Ki = np.linalg.inv(K)
    h1, h2, h3 = Ki @ H[:, 0], Ki @ H[:, 1], Ki @ H[:, 2]
    lam = 1.0 / np.linalg.norm(h1)
    if (lam * h3)[2] < 0:
        lam = -lam
    r1, r2, t = lam * h1, lam * h2, lam * h3
    R = np.column_stack([r1, r2, np.cross(r1, r2)])
    U, _, Vt = np.linalg.svd(R)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        R = U @ np.diag([1, 1, -1]) @ Vt
    return R, t


def _homography(obj, uv):
    A = []
    for (X, Y), (u, v) in zip(obj, uv):
        A.append([-X, -Y, -1, 0, 0, 0, u * X, u * Y, u])
        A.append([0, 0, 0, -X, -Y, -1, v * X, v * Y, v])
    _, _, Vt = np.linalg.svd(np.asarray(A))
    H = Vt[-1].reshape(3, 3)
    return H / H[2, 2]


class _Problem:
    """LM の問題: カメラ 1〜2 台・板の姿勢 n・(ステレオなら)相対姿勢。"""

    def __init__(self, obj, views, cams, poses, rel, free_dist, fix_intr):
        self.obj3 = np.column_stack([obj, np.zeros(len(obj))])
        self.views = views                                # [cam][view] -> (N,2) (u,v)
        self.cams = cams                                  # list of [intr(4), dist(5)]
        self.poses = poses                                # list of (R, t) for the board in camera 0
        self.rel = rel                                    # (R, t) of camera 1 w.r.t. camera 0 or None
        self.free_dist = free_dist
        self.fix_intr = fix_intr
        self.ncam = len(cams)

    # 自由な変数の並び: [cam0 intr(4) dist(free)] [cam1 ...] [pose_i (6) ...] [rel (6)]
    def n_cam_params(self):
        return 0 if self.fix_intr else 4 + len(self.free_dist)

    def n_params(self):
        return self.ncam * self.n_cam_params() + 6 * len(self.poses) + (6 if self.rel is not None else 0)

    def residual_jac(self, want_jac=True):
        nc = self.n_cam_params()
        P = self.n_params()
        res, rows = [], []
        for c in range(self.ncam):
            intr, dist = self.cams[c]
            for i, (R, t) in enumerate(self.poses):
                Y = self.obj3 @ R.T + t
                if c == 1:
                    Rr, tr = self.rel
                    Xc = Y @ Rr.T + tr
                else:
                    Xc = Y
                if np.any(Xc[:, 2] <= 0):
                    raise ValueError("a board point went behind the camera during refinement")
                if not want_jac:
                    uv = _proj(Xc, intr, dist, jac=False)
                    res.append((uv - self.views[c][i]).reshape(-1))
                    continue
                uv, Ji, Jd, JX = _proj(Xc, intr, dist)
                res.append((uv - self.views[c][i]).reshape(-1))
                J = np.zeros((len(Xc), 2, P))
                if nc:
                    o = c * nc
                    J[:, :, o:o + 4] = Ji
                    J[:, :, o + 4:o + nc] = Jd[:, :, list(self.free_dist)]
                base = self.ncam * nc + 6 * i
                RX = self.obj3 @ R.T
                if c == 0:
                    J[:, :, base:base + 3] = JX @ (-_skew(RX))
                    J[:, :, base + 3:base + 6] = JX
                else:
                    Rr, tr = self.rel
                    JXr = JX @ Rr
                    J[:, :, base:base + 3] = JXr @ (-_skew(RX))
                    J[:, :, base + 3:base + 6] = JXr
                    rb = self.ncam * nc + 6 * len(self.poses)
                    J[:, :, rb:rb + 3] = JX @ (-_skew(Y @ Rr.T))
                    J[:, :, rb + 3:rb + 6] = JX
                rows.append(J.reshape(-1, P))
        r = np.concatenate(res)
        return (r, np.vstack(rows)) if want_jac else r

    def apply(self, dx):
        nc = self.n_cam_params()
        new = _Problem.__new__(_Problem)
        new.__dict__ = dict(self.__dict__)
        cams = []
        for c in range(self.ncam):
            intr, dist = self.cams[c]
            intr, dist = np.array(intr, float), np.array(dist, float)
            if nc:
                o = c * nc
                intr = intr + dx[o:o + 4]
                dist[list(self.free_dist)] += dx[o + 4:o + nc]
            cams.append([intr, dist])
        new.cams = cams
        poses = []
        for i, (R, t) in enumerate(self.poses):
            b = self.ncam * nc + 6 * i
            poses.append((_exp(dx[b:b + 3]) @ R, t + dx[b + 3:b + 6]))
        new.poses = poses
        if self.rel is not None:
            rb = self.ncam * nc + 6 * len(self.poses)
            Rr, tr = self.rel
            new.rel = (_exp(dx[rb:rb + 3]) @ Rr, tr + dx[rb + 3:rb + 6])
        return new


def _lm(prob, max_iter=200):
    """Levenberg-Marquardt(Marquardt の対角の減衰)。返り: (解いた問題, 残差, J, 反復回数, 収束)。"""
    r, J = prob.residual_jac()
    cost = 0.5 * r @ r
    lam = 1e-3
    it = 0
    converged = False
    for it in range(1, max_iter + 1):
        A = J.T @ J
        g = J.T @ r
        dA = np.diag(A).copy()
        dA[dA <= 0] = 1e-12
        improved = False
        for _ in range(30):
            try:
                dx = np.linalg.solve(A + lam * np.diag(dA), -g)
            except np.linalg.LinAlgError:
                lam *= 10
                continue
            try:
                cand = prob.apply(dx)
                rn = cand.residual_jac(want_jac=False)
            except ValueError:
                lam *= 10
                continue
            cn = 0.5 * rn @ rn
            if cn < cost:
                rel = (cost - cn) / max(cost, 1e-300)
                prob, cost = cand, cn
                lam = max(lam / 3.0, 1e-12)
                improved = True
                break
            lam *= 5.0
        if not improved:
            converged = True
            break
        r, J = prob.residual_jac()
        if rel < 1e-15 or np.max(np.abs(dx)) < 1e-14:
            converged = True
            break
    r, J = prob.residual_jac()
    return prob, r, J, it, converged


def _views_uv(image_points_list, n_obj, op, name="image_points_list"):
    if isinstance(image_points_list, np.ndarray) and image_points_list.ndim == 2:
        raise ValueError("%s: %s must be a list of (N, 2) arrays, one per view" % (op, name))
    try:
        views = [_arr(v, "%s[%d]" % (name, k), op, cols=2) for k, v in enumerate(image_points_list)]
    except TypeError:
        raise ValueError("%s: %s must be a list of (N, 2) arrays" % (op, name)) from None
    for k, v in enumerate(views):
        if len(v) != n_obj:
            raise ValueError("%s: %s[%d] has %d points vs %d object points" % (op, name, k, len(v), n_obj))
    return [v[:, ::-1].copy() for v in views]             # (row, col) -> (u, v)


def _init_mono(obj, uv_views, image_shape, op):
    """Zhang の閉形式(calib.camera_calibration)で K の初期値、ホモグラフィで姿勢の初期値。

    初期値なので、公開 op の雑音込みの門(K の相対標準偏差 5 %、2026-11-09)は通さず閉形式の
    本体を直接呼ぶ(不確かさは LM の共分散が報告する)。比の門と非正 K の門は残る。"""
    init = {"method": "zhang"}
    try:
        z = _calib._zhang_closed_form(*_calib._zhang_views(obj, [u[:, ::-1] for u in uv_views]))
        K = np.array([[z["fx"], 0.0, z["cx"]], [0.0, z["fy"], z["cy"]], [0, 0, 1.0]])
        init.update(fx=z["fx"], fy=z["fy"], cx=z["cx"], cy=z["cy"],
                    orientation_rank_ratio=z["orientation_rank_ratio"])
    except ValueError as e:
        if image_shape is None:
            raise ValueError("%s: Zhang's closed form failed (%s); pass image_shape for a fallback start" % (op, e)) \
                from None
        h, w = _shape(image_shape, op)
        f0 = float(max(h, w))
        K = np.array([[f0, 0, (w - 1) / 2.0], [0, f0, (h - 1) / 2.0], [0, 0, 1.0]])
        init = {"method": "fallback (Zhang failed: %s)" % e, "fx": f0, "fy": f0}
    if not (np.isfinite(K).all() and K[0, 0] > 0 and K[1, 1] > 0):
        raise ValueError("%s: invalid initial intrinsics" % op)
    poses = [_init_pose(_homography(obj, uv), K) for uv in uv_views]
    return K, poses, init


def _pack_result(prob, r, J):
    """残差の分散 σ² = |r|²/(m − P) と共分散 σ²(JᵀJ)⁻¹。"""
    P = prob.n_params()
    m = len(r)
    dof = m - P
    sigma2 = float(r @ r / dof) if dof > 0 else float("nan")
    A = J.T @ J
    try:
        cov = sigma2 * np.linalg.inv(A)
    except np.linalg.LinAlgError:
        cov = np.full((P, P), np.inf)
    return sigma2, cov, dof


def camera_calibration_lm(object_points, image_points_list, dist_model="k1k2p1p2k3", image_shape=None):
    """Zhang 法の初期値から内部パラメータ・歪み・全姿勢を LM で同時に最適化し、共分散とともに返す(``table``)。

    Monocular calibration: Zhang's closed form (``calib.camera_calibration``) gives the start, then a
    Levenberg-Marquardt refinement minimises the reprojection error over fx, fy, cx, cy, the distortion
    coefficients of ``dist_model`` and every board pose jointly (Zhang 2000, §3.3; the Brown-Conrady model
    with OpenCV's coefficient order). The Jacobian is analytic; poses are updated on the left by a small
    rotation vector. Skew is fixed at 0.

    ``object_points``: 板の点 (N, 2) の (x, y)(:func:`checkerboard_points` など)。
    ``image_points_list``: 視点ごとの (N, 2) の **(row, col)**。``dist_model``: ``"none"``・``"k1"``・``"k1k2"``・
    ``"k1k2p1p2"``・``"k1k2p1p2k3"``(既定 = OpenCV の既定と同じ 5 係数)。
    ``image_shape``: Zhang の閉形式が退化したとき(全部が正面平行など)の初期値に使う。

    返す ``dict``: ``K`` (3x3)、``fx``・``fy``・``cx``・``cy``、``dist`` [k1, k2, p1, p2, k3]、``poses``(板 → カメラ
    の 4x4 の list)、``rvecs``・``tvecs``、``reproj_rms``(全体)、``per_view_rms``、``residuals``(視点ごとの (N,2)
    (row, col))、``sigma_px``(残差から推定した角の雑音)、``covariance``(fx, fy, cx, cy, k1, k2, p1, p2, k3 の
    9x9 の周辺共分散、固定の係数は 0)、``param_std``(名前 → 標準偏差)、``param_names``、``init``(Zhang の値)、
    ``iterations``・``converged``、``dist_model``、``object_points``、``image_shape``。
    ★再投影誤差が小さいことは配置が良いことを意味しない(``camera_calibration`` のノートの実測)。配置の良し悪しは
    ``param_std`` と :func:`calibration_uncertainty_map` で見る。

    **Raises** ``ValueError``: 視点が 3 未満、点の数が合わない・4 未満・非有限、未知の ``dist_model``、
    初期値が作れない、LM の途中で板が背後へ回る。
    """
    op = "camera_calibration_lm"
    obj = _arr(object_points, "object_points", op, cols=2, min_rows=4)
    if dist_model not in _DIST_MODELS:
        raise ValueError("%s: dist_model must be one of %s (got %r)" % (op, sorted(_DIST_MODELS), dist_model))
    uv = _views_uv(image_points_list, len(obj), op)
    if len(uv) < 3:
        raise ValueError("%s: needs >= 3 views (got %d)" % (op, len(uv)))
    mi = _MAX_ITER
    K, poses, init = _init_mono(obj, uv, image_shape, op)
    free = _DIST_MODELS[dist_model]
    prob = _Problem(obj, [uv], [[np.array([K[0, 0], K[1, 1], K[0, 2], K[1, 2]]), np.zeros(5)]], poses, None,
                    (), False)
    prob, _, _, it0, _ = _lm(prob, mi)                    # 歪みなしで粗く / first without distortion
    prob.free_dist = free
    prob, r, J, it, conv = _lm(prob, mi)
    sigma2, cov, dof = _pack_result(prob, r, J)
    intr, dist = prob.cams[0]
    names = list(_INTR_NAMES) + list(_DIST_NAMES)
    C9 = np.zeros((9, 9))
    idx = [0, 1, 2, 3] + [4 + k for k in free]
    nc = prob.n_cam_params()
    C9[np.ix_(idx, idx)] = cov[:nc, :nc]
    res = r.reshape(len(uv), len(obj), 2)
    per = [float(np.sqrt(np.mean(np.sum(e ** 2, 1)))) for e in res]
    Kout = np.array([[intr[0], 0.0, intr[2]], [0.0, intr[1], intr[3]], [0, 0, 1.0]])
    Ps = []
    for R, t in prob.poses:
        P = np.eye(4)
        P[:3, :3], P[:3, 3] = R, t
        Ps.append(P)
    return {"K": Kout, "fx": float(intr[0]), "fy": float(intr[1]), "cx": float(intr[2]), "cy": float(intr[3]),
            "dist": dist.copy(), "poses": Ps, "rvecs": np.array([_camera.rotation_log(R) for R, _ in prob.poses]),
            "tvecs": np.array([t for _, t in prob.poses]),
            "reproj_rms": float(np.sqrt(np.mean(np.sum(res ** 2, -1)))), "per_view_rms": per,
            "residuals": [e[:, ::-1].copy() for e in res], "sigma_px": float(math.sqrt(sigma2)),
            "covariance": C9, "param_names": names,
            "param_std": {n: float(math.sqrt(max(C9[i, i], 0.0))) for i, n in enumerate(names)},
            "init": init, "iterations": int(it0 + it), "converged": bool(conv), "dist_model": dist_model,
            "object_points": obj, "image_shape": None if image_shape is None else tuple(image_shape),
            "dof": int(dof)}


# =========================================================================== #
# ステレオ / stereo
# =========================================================================== #
def stereo_calibration_lm(object_points, image_points_left, image_points_right, dist_model="k1k2p1p2k3",
                          fix_intrinsics=False, calib_left=None, calib_right=None, image_shape=None):
    """左右の内部・歪み・板の姿勢と右カメラの相対姿勢 (R, T) を LM で同時に最適化する(``table``)。

    Joint stereo calibration: both cameras' intrinsics and distortion, the board poses in the left camera
    and the right camera's pose relative to the left (X_right = R·X_left + T) are refined together by
    Levenberg-Marquardt on the reprojection error in both images. Each camera starts from
    :func:`camera_calibration_lm` (or ``calib_left`` / ``calib_right`` if given) and (R, T) from the
    per-view relative poses (rotation by the chordal mean, translation by the mean).
    ``fix_intrinsics`` keeps both cameras' intrinsics and distortion fixed (OpenCV's CALIB_FIX_INTRINSIC).

    返す ``dict``: ``K1``・``dist1``・``K2``・``dist2``・``R``・``T``・``E`` = [T]x R・``F`` = K2⁻ᵀ E K1⁻¹
    (画素 (u = col, v = row) の同次座標どうし)、``baseline`` = |T|、``reproj_rms``(左右合わせて)、
    ``rms_left``・``rms_right``、``poses_left``、``sigma_px``、``rel_std``(R の回転ベクトルと T の標準偏差 6 個)、
    ``iterations``・``converged``。

    **Raises** ``ValueError``: 左右の視点の数が違う・3 未満、点の数が合わない、単眼の校正の失敗。
    """
    op = "stereo_calibration_lm"
    obj = _arr(object_points, "object_points", op, cols=2, min_rows=4)
    uvL = _views_uv(image_points_left, len(obj), op, "image_points_left")
    uvR = _views_uv(image_points_right, len(obj), op, "image_points_right")
    if len(uvL) != len(uvR) or len(uvL) < 3:
        raise ValueError("%s: needs the same number (>= 3) of left and right views (got %d / %d)"
                         % (op, len(uvL), len(uvR)))
    mi = _MAX_ITER
    if not isinstance(fix_intrinsics, (bool, np.bool_)):
        raise ValueError("%s: fix_intrinsics must be a bool" % op)
    cl = calib_left if calib_left is not None else camera_calibration_lm(
        obj, image_points_left, dist_model, image_shape)
    cr = calib_right if calib_right is not None else camera_calibration_lm(
        obj, image_points_right, dist_model, image_shape)
    for c, nm in ((cl, "calib_left"), (cr, "calib_right")):
        if not isinstance(c, dict) or "K" not in c or "dist" not in c:
            raise ValueError("%s: %s must be a camera_calibration_lm table" % (op, nm))
    if calib_left is not None and "poses" in cl and len(cl["poses"]) == len(uvL):
        posesL = [_pose(P, op, "calib_left pose") for P in cl["poses"]]
    elif calib_left is None:
        posesL = [_pose(P, op) for P in cl["poses"]]
    else:
        posesL = [_init_pose(_homography(obj, u), _kmat(cl["K"], op)) for u in uvL]
    if calib_right is None or ("poses" in cr and len(cr["poses"]) == len(uvR)):
        posesR = [_pose(P, op) for P in cr["poses"]]
    else:
        posesR = [_init_pose(_homography(obj, u), _kmat(cr["K"], op)) for u in uvR]
    Rs = [Rr @ Rl.T for (Rl, _), (Rr, _) in zip(posesL, posesR)]
    U, _, Vt = np.linalg.svd(np.sum(Rs, axis=0))
    R0 = U @ Vt
    if np.linalg.det(R0) < 0:
        R0 = U @ np.diag([1, 1, -1]) @ Vt
    T0 = np.mean([tr - R0 @ tl for (_, tl), (_, tr) in zip(posesL, posesR)], axis=0)
    KL, KR = _kmat(cl["K"], op), _kmat(cr["K"], op)
    cams = [[np.array([KL[0, 0], KL[1, 1], KL[0, 2], KL[1, 2]]), _dist(cl["dist"], op)],
            [np.array([KR[0, 0], KR[1, 1], KR[0, 2], KR[1, 2]]), _dist(cr["dist"], op)]]
    if dist_model not in _DIST_MODELS:
        raise ValueError("%s: unknown dist_model %r" % (op, dist_model))
    prob = _Problem(obj, [uvL, uvR], cams, posesL, (R0, T0), _DIST_MODELS[dist_model], bool(fix_intrinsics))
    prob, r, J, it, conv = _lm(prob, mi)
    sigma2, cov, _dof = _pack_result(prob, r, J)
    n = len(uvL) * len(obj) * 2
    rL, rR = r[:n].reshape(-1, 2), r[n:].reshape(-1, 2)
    (iL, dL), (iR, dR) = prob.cams
    K1 = np.array([[iL[0], 0, iL[2]], [0, iL[1], iL[3]], [0, 0, 1.0]])
    K2 = np.array([[iR[0], 0, iR[2]], [0, iR[1], iR[3]], [0, 0, 1.0]])
    R, T = prob.rel
    Tx = np.array([[0, -T[2], T[1]], [T[2], 0, -T[0]], [-T[1], T[0], 0]])
    E = Tx @ R
    F = np.linalg.inv(K2).T @ E @ np.linalg.inv(K1)
    Pl = []
    for Rl, tl in prob.poses:
        P = np.eye(4)
        P[:3, :3], P[:3, 3] = Rl, tl
        Pl.append(P)
    rel_std = np.sqrt(np.maximum(np.diag(cov)[-6:], 0.0))
    return {"K1": K1, "dist1": dL.copy(), "K2": K2, "dist2": dR.copy(), "R": R, "T": T, "E": E,
            "F": F / F[2, 2] if abs(F[2, 2]) > 1e-15 else F, "baseline": float(np.linalg.norm(T)),
            "reproj_rms": float(np.sqrt(np.mean(np.sum(r.reshape(-1, 2) ** 2, 1)))),
            "rms_left": float(np.sqrt(np.mean(np.sum(rL ** 2, 1)))),
            "rms_right": float(np.sqrt(np.mean(np.sum(rR ** 2, 1)))), "poses_left": Pl,
            "sigma_px": float(math.sqrt(sigma2)), "rel_std": rel_std, "iterations": int(it),
            "converged": bool(conv), "fix_intrinsics": bool(fix_intrinsics)}


# =========================================================================== #
# Fullseye だけの層: 真値つきの誤差の地図・不確かさの地図・次の 1 枚
# =========================================================================== #
def _cal_params(cal, op, name="calibration"):
    if not isinstance(cal, dict) or "K" not in cal or "dist" not in cal:
        raise ValueError("%s: %s must be a camera_calibration_lm table (needs K and dist)" % (op, name))
    K = _kmat(cal["K"], op)
    return np.array([K[0, 0], K[1, 1], K[0, 2], K[1, 2]]), _dist(cal["dist"], op)


def _grid(shape, step, op):
    h, w = _shape(shape, op)
    st = int(_num(step, "step", op, lo=1, hi=max(h, w)))
    rr = np.arange(st / 2.0 - 0.5, h, st)
    cc = np.arange(st / 2.0 - 0.5, w, st)
    C, R = np.meshgrid(cc, rr)
    return R, C


def _pixel_to_norm(u, v, intr, dist):
    xd = (u - intr[2]) / intr[0]
    yd = (v - intr[3]) / intr[1]
    return _undistort_norm(xd, yd, dist, iters=50)


def _best_rotation(X, target, intr, dist, iters=20):
    """推定のカメラで R·X を投影したときに target に最も合う小さな回転 R(Gauss-Newton)。"""
    R = np.eye(3)
    for _ in range(iters):
        Y = X @ R.T
        uv, _, _, JX = _proj(Y, intr, dist)
        J = (JX @ (-_skew(Y))).reshape(-1, 3)
        r = (uv - target).reshape(-1)
        dw, *_ = np.linalg.lstsq(J, -r, rcond=None)
        R = _exp(dw) @ R
        if np.max(np.abs(dw)) < 1e-15:
            break
    return R


def calibration_error_map(calibration, K_true, dist_true, image_shape, step=16, depth=None, remove_rotation=True):
    """真の K・歪みと推定値を比べ、画像のどこで再投影の誤差(px)と 3D の誤差(mm)が大きいかの地図を返す(``table``)。

    Map, over the image, how far the estimated camera misplaces a point compared with the true camera —
    possible only when the truth is known (a simulated calibration). For each grid pixel p the ray of the
    TRUE camera through p is reprojected with the ESTIMATED camera; the map is |p̂ − p| in pixels (the
    error any reprojection-based measurement inherits there). With ``depth`` Z (mm), the 3-D map is the
    lateral distance between the points the two cameras back-project from p at depth Z.

    ``remove_rotation``(既定 True): 推定のカメラを最もよく合う小さな回転で回してから比べる。主点のずれの大部分は
    カメラの向きのずれと見分けがつかず、どんな使い方でも外部の姿勢に吸収されるので、残るのが「内部パラメータと歪み
    でしか直せない」誤差になる。回した角度は ``rotation_removed_deg``、回す前の地図は ``raw_*`` に残す。
    閉形式の門(``remove_rotation=False``): 推定 = 真値 → 0、cx だけ δ ずれ(歪みなし)→ どこでも δ px、
    3D は δ·Z/fx。``image_shape`` (H, W)、``step`` は格子の間隔(画素)。

    返す ``dict``: ``rows``・``cols``(格子の中心)、``reproj_error_px``(地図)、``dx_px``・``dy_px``(成分、列・行)、
    ``max_px``・``rms_px``・``max_at``(row, col)、``raw_rms_px``・``raw_max_px``(回す前)、``rotation_removed_deg``、
    ``error_3d_mm``・``max_3d_mm``(``depth`` があれば)、``depth``。

    **Raises** ``ValueError``: 校正の表が不正、K が正でない、``image_shape``・``step``・``depth`` の範囲外。
    """
    op = "calibration_error_map"
    ie, de = _cal_params(calibration, op)
    Kt = _kmat(K_true, op)
    it_ = np.array([Kt[0, 0], Kt[1, 1], Kt[0, 2], Kt[1, 2]])
    dt = _dist(dist_true, op)
    if not isinstance(remove_rotation, (bool, np.bool_)):
        raise ValueError("%s: remove_rotation must be a bool" % op)
    Rg, Cg = _grid(image_shape, step, op)
    target = np.column_stack([Cg.ravel(), Rg.ravel()])
    x, y = _pixel_to_norm(Cg.ravel(), Rg.ravel(), it_, dt)
    X = np.column_stack([x, y, np.ones_like(x)])
    raw = _proj(X, ie, de, jac=False) - target
    raw_e = np.hypot(raw[:, 0], raw[:, 1])
    Rb = _best_rotation(X, target, ie, de) if remove_rotation else np.eye(3)
    Xr = X @ Rb.T
    d = _proj(Xr, ie, de, jac=False) - target
    dx, dy = d[:, 0].reshape(Cg.shape), d[:, 1].reshape(Cg.shape)
    e = np.hypot(dx, dy)
    k = int(np.argmax(e))
    ang = float(np.degrees(np.linalg.norm(_camera.rotation_log(Rb))))
    out = {"rows": Rg[:, 0].copy(), "cols": Cg[0].copy(), "reproj_error_px": e, "dx_px": dx, "dy_px": dy,
           "max_px": float(e.max()), "rms_px": float(np.sqrt(np.mean(e ** 2))),
           "max_at": (float(Rg.ravel()[k]), float(Cg.ravel()[k])), "raw_rms_px": float(np.sqrt(np.mean(raw_e ** 2))),
           "raw_max_px": float(raw_e.max()), "rotation_removed_deg": ang, "depth": depth}
    if depth is not None:
        Z = _num(depth, "depth", op, lo=0.0, lo_open=True)
        # 推定のカメラが画素 p から逆に引く視線(回した座標で)と真の視線の、奥行き Z での横の距離
        xe, ye = _pixel_to_norm(Cg.ravel(), Rg.ravel(), ie, de)
        ve = np.column_stack([xe, ye, np.ones_like(xe)]) @ Rb       # 推定の視線を真のカメラの座標へ
        ve = ve / ve[:, 2:3]
        e3 = Z * np.hypot(ve[:, 0] - x, ve[:, 1] - y)
        out["error_3d_mm"] = e3.reshape(Cg.shape)
        out["max_3d_mm"] = float(e3.max())
    return out


def _intrinsic_cov(cal, op):
    C = np.asarray(cal.get("covariance"), float) if "covariance" in cal else None
    if C is None or C.shape != (9, 9) or not np.isfinite(C).all():
        raise ValueError("%s: calibration has no finite 9x9 covariance (use camera_calibration_lm)" % op)
    return C


def _uncert_from_cov(C, intr, dist, R, Cg, remove_rotation=True):
    """9x9 の共分散 → 格子の画素ごとの予測の標準偏差。``remove_rotation`` ならカメラの回転と同じ形の成分を除く
    (誤差の地図の ``remove_rotation`` と同じ意味の線形版: 格子全体の変位から最小二乗の回転を引く)。"""
    x, y = _pixel_to_norm(Cg.ravel(), R.ravel(), intr, dist)
    X = np.column_stack([x, y, np.ones_like(x)])
    _, Ji, Jd, JX = _proj(X, intr, dist)
    n = len(X)
    G = np.concatenate([Ji, Jd], axis=2).reshape(2 * n, 9)
    if remove_rotation:
        W = (JX @ (-_skew(X))).reshape(2 * n, 3)
        G = G - W @ np.linalg.lstsq(W, G, rcond=None)[0]
    Jp = G.reshape(n, 2, 9)
    S = np.einsum("nij,jk,nlk->nil", Jp, C, Jp)          # (N, 2, 2)
    return np.sqrt(np.maximum(S[:, 0, 0] + S[:, 1, 1], 0.0)).reshape(Cg.shape)


def calibration_uncertainty_map(calibration, image_shape, step=16, depth=None, remove_rotation=True):
    """校正の推定の共分散を画像の上へ写し、各画素の予測の不確かさ(px、奥行き Z なら mm)の地図を返す(``table``)。

    Propagate the marginal covariance of the intrinsics and distortion (from :func:`camera_calibration_lm`)
    to every grid pixel: a point fixed in the camera frame that the estimate places at p would be
    reprojected with a standard deviation ``sqrt(trace(J C Jᵀ))`` (px, radial), J the 2x9 Jacobian of the
    projection with respect to (fx, fy, cx, cy, k1, k2, p1, p2, k3). Needs no ground truth — this is the
    map a real calibration can show too; the simulation checks that it is honest (Monte Carlo gate).
    With ``depth`` Z (mm) the map is also given in mm (std · Z / f, small-angle).

    ``remove_rotation``(既定 True)は :func:`calibration_error_map` と同じ意味: カメラの向きのずれと見分けの
    つかない成分(主点のずれの大部分)を除く。両方を同じ設定で使うと、モンテカルロの誤差の地図と比べられる。
    ★姿勢の不確かさは周辺化で含まれる(9x9 は全変数の共分散からの周辺)。画像の端ほど大きくなるのは、
    板が写っていない所を歪みの多項式が外挿するから。★線形の予測なので、外挿が大きい所では当たらない:
    6 視点・σ = 0.2 px で k3 まで自由にすると、隅の予測 160 px に対しモンテカルロの実測は 55 px
    (k1k2p1p2 なら全体の平均で 6.42 / 6.39 px と合う。tests の実測)。

    返す ``dict``: ``rows``・``cols``、``std_px``(地図)、``mean_px``・``max_px``・``max_at``、``std_mm``(``depth``)。

    **Raises** ``ValueError``: 共分散が無い・非有限、引数の範囲外。
    """
    op = "calibration_uncertainty_map"
    intr, dist = _cal_params(calibration, op)
    C = _intrinsic_cov(calibration, op)
    if not isinstance(remove_rotation, (bool, np.bool_)):
        raise ValueError("%s: remove_rotation must be a bool" % op)
    Rg, Cg = _grid(image_shape, step, op)
    s = _uncert_from_cov(C, intr, dist, Rg, Cg, bool(remove_rotation))
    k = int(np.argmax(s))
    out = {"rows": Rg[:, 0].copy(), "cols": Cg[0].copy(), "std_px": s, "mean_px": float(s.mean()),
           "max_px": float(s.max()), "max_at": (float(Rg.ravel()[k]), float(Cg.ravel()[k])), "depth": depth}
    if depth is not None:
        Z = _num(depth, "depth", op, lo=0.0, lo_open=True)
        out["std_mm"] = s * Z / (0.5 * (intr[0] + intr[1]))
    return out


def calibration_next_pose(calibration, candidate_poses, image_shape, step=32, sigma_px=None):
    """候補の板の姿勢のうち、足すと校正の不確かさ(画像全体の平均)を最も減らす 1 枚を推薦する(``table``)。

    Recommend the next calibration view. The information already gathered is rebuilt from the
    calibration's own geometry (board, poses, current estimate — the Jacobian does not depend on the
    measured points) as JᵀJ/σ²; each candidate pose (board -> camera 4x4) adds its own block (with its 6
    pose unknowns). The score is the mean of :func:`calibration_uncertainty_map` after adding the
    candidate; lower is better. Candidates whose board leaves the image or goes behind the camera get
    ``inf``. ``sigma_px`` overrides the corner noise (default: the calibration's ``sigma_px``).

    ★これは**予測**(線形化した共分散)。モンテカルロで「推薦を足した校正の実際の誤差 < 最下位を足した校正」を
    門で確かめる(tests)。最適な実験計画の D 最適ではなく、画像の上の予測の不確かさの平均を直接減らす基準。
    画像の上の予測の再投影誤差で次の姿勢を選ぶ考え方は AprilCal(Richardson, Strom & Olson, IROS 2013)と同じ系統
    (あちらは最大値、こちらは平均)。★実測(tests の 6 候補): 候補どうしの差が小さいとき予測の順位と実際の順位は
    入れ替わりうる。確かなのは「最下位を避ける」ほうで、門もそこを見る。

    返す ``dict``: ``scores``(候補ごと、px)、``best_index``、``current_mean_px``、``improvement``(現在 − 最良)、
    ``visible``(候補ごと)、``param_std``(候補ごとの 9 変数の標準偏差)。

    **Raises** ``ValueError``: 校正の表に姿勢・板・雑音が無い、候補が空・剛体でない、引数の範囲外。
    """
    op = "calibration_next_pose"
    intr, dist = _cal_params(calibration, op)
    if "poses" not in calibration or "object_points" not in calibration:
        raise ValueError("%s: calibration must come from camera_calibration_lm (poses and object_points)" % op)
    if isinstance(candidate_poses, np.ndarray) and candidate_poses.ndim == 2:
        candidate_poses = [candidate_poses]
    try:
        cands = [_pose(P, op, "candidate_poses[%d]" % k) for k, P in enumerate(candidate_poses)]
    except TypeError:
        raise ValueError("%s: candidate_poses must be a list of 4x4 poses" % op) from None
    if not cands:
        raise ValueError("%s: candidate_poses is empty" % op)
    h, w = _shape(image_shape, op)
    sg = calibration.get("sigma_px") if sigma_px is None else sigma_px
    sg = _num(sg, "sigma_px", op, lo=0.0, lo_open=True)
    obj = _arr(calibration["object_points"], "object_points", op, cols=2, min_rows=4)
    dm = calibration.get("dist_model", "k1k2p1p2k3")
    if dm not in _DIST_MODELS:
        raise ValueError("%s: unknown dist_model %r" % (op, dm))
    free = _DIST_MODELS[dm]
    poses = [_pose(P, op) for P in calibration["poses"]]
    obj3 = np.column_stack([obj, np.zeros(len(obj))])
    nc = 4 + len(free)

    def view_jac(R, t):
        Xc = obj3 @ R.T + t
        if np.any(Xc[:, 2] <= 0):
            return None, None, None
        uv, Ji, Jd, JX = _proj(Xc, intr, dist)
        Jc = np.concatenate([Ji, Jd[:, :, list(free)]], axis=2).reshape(-1, nc)
        Jp = np.concatenate([JX @ (-_skew(obj3 @ R.T)), JX], axis=2).reshape(-1, 6)
        return Jc, Jp, uv

    nv = len(poses)
    P = nc + 6 * (nv + 1)
    A = np.zeros((P, P))
    for i, (R, t) in enumerate(poses):
        Jc, Jp, _ = view_jac(R, t)
        if Jc is None:
            raise ValueError("%s: a calibration pose puts the board behind the camera" % op)
        b = nc + 6 * i
        A[:nc, :nc] += Jc.T @ Jc
        A[:nc, b:b + 6] += Jc.T @ Jp
        A[b:b + 6, :nc] += Jp.T @ Jc
        A[b:b + 6, b:b + 6] += Jp.T @ Jp
    Rg, Cg = _grid((h, w), step, op)
    idx = [0, 1, 2, 3] + [4 + k for k in free]

    def score(Ainfo):
        Cfull = np.linalg.inv(Ainfo / sg ** 2)
        C9 = np.zeros((9, 9))
        C9[np.ix_(idx, idx)] = Cfull[:nc, :nc]
        return float(_uncert_from_cov(C9, intr, dist, Rg, Cg).mean()), np.sqrt(np.maximum(np.diag(C9), 0))

    A0 = A[:-6, :-6]
    cur, _ = score(A0)
    scores, vis, stds = [], [], []
    b = nc + 6 * nv
    for R, t in cands:
        Jc, Jp, uv = view_jac(R, t)
        ok = Jc is not None and bool(np.all((uv[:, 0] >= 0) & (uv[:, 0] <= w - 1) &
                                            (uv[:, 1] >= 0) & (uv[:, 1] <= h - 1)))
        vis.append(ok)
        if not ok:
            scores.append(float("inf"))
            stds.append(None)
            continue
        An = A.copy()
        An[:nc, :nc] += Jc.T @ Jc
        An[:nc, b:b + 6] += Jc.T @ Jp
        An[b:b + 6, :nc] += Jp.T @ Jc
        An[b:b + 6, b:b + 6] += Jp.T @ Jp
        s, sd = score(An)
        scores.append(s)
        stds.append(dict(zip(list(_INTR_NAMES) + list(_DIST_NAMES), sd.tolist())))
    if not any(vis):
        raise ValueError("%s: no candidate keeps the whole board inside the image" % op)
    best = int(np.argmin(scores))
    return {"scores": scores, "best_index": best, "current_mean_px": cur, "improvement": cur - scores[best],
            "visible": vis, "param_std": stds}

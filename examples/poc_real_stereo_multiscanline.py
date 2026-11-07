# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写のステレオ対で視差・距離・面・円の姿勢まで出し、真値の視差で採点する(複数走査線の視差)。

主役は 0.9.0 の後に入った op —— ``binocular_disparity_ms``(半大域マッチング + 左右一致 + 小数の補間)、
``binocular_distance_ms``、``reconstruct_surface_stereo``、``get_circle_pose``、``points_lepetit``、
``crop_rectangle2``、``create_ncc_model`` / ``find_ncc_models``。題材は Middlebury 2014 の motorcycle
(scikit-image 同梱の 1/4 縮小版、真値視差つき)で、CI でも全章が走る。Middlebury MiddEval3 の訓練
15 場面(1/4 解像度、遮蔽の印つき)が手元にあれば、場面ごとの表も作る。

★名前の ``ms`` は multi-scanline(複数の走査線の向きで集約する)で、多重スケール(ピラミッド)では
ない。だから「多重スケールの効き方」は 2 つに分けて測る: (a) op の中の集約の向き ``paths`` 2 / 4、
(b) op の外で画像を 1/2 に縮めて回し、視差を 2 倍して戻す粗い段(op にピラミッドは無い)。

真値は外から持ってくる:

* 視差・距離・面 —— 配布元の真値視差(構造化光で測ったもの)。距離は ``Z = f B / (d + doffs)``。
* 照合 —— OpenCV の ``StereoSGBM``(同じ探索範囲・窓・左右一致)を参照実装として同じ画素で採点。
  ``find_ncc_models`` のスコアと位置は OpenCV の ``matchTemplate``(TM_CCOEFF_NORMED)と突き合わせる。
  点群は OpenCV の ``reprojectImageTo3D``(Q 行列)と突き合わせる。
* 円の姿勢 —— 後輪のリムの縁を画像だけで拾い、``get_circle_pose`` で中心と法線を出す。真値は同じ縁の
  画素の**真値視差**から作った 3-D 点に、平面と円を当てはめたもの。

章(数値はすべて実行時に印字する実測値):

1. 視差の採点: 有効画素の bad-2・平均誤差・密度。無効を誤りに数えた bad-2 も並べる(密度と正しさは
   別の数字)。OpenCV の SGBM と同じ画素で比べる。
2. 失敗する場所の地図: 真値から遮蔽(右のカメラから見えない画素)を幾何で数え、無地(7x7 の
   局所標準偏差が小さい)と見え方が変わる面(真値の対応で左右の明るさが食い違う = 反射・光沢の代理)
   に分け、区分ごとの bad-2 と無効の割合を出す。遮蔽の数え方は、MiddEval3 があれば配布元の遮蔽の印
   (mask0nocc)と照合する。
3. 集約の向きと粗い段: ``paths`` 2 / 4 と、1/2 に縮めた段。
4. 距離と面: ``binocular_distance_ms`` に ``doffs`` を渡した距離を真値の距離と比べ、
   ``reconstruct_surface_stereo`` の点群を OpenCV の再投影と比べる。
5. 円の姿勢: 後輪のリム。2 つの解は 1 枚の像からは区別できない(再投影の誤差がほぼ同じ)ことも示す。
6. 疎な対応: ``points_lepetit`` の点で ``crop_rectangle2`` → ``create_ncc_model`` → 右の走査線の帯で
   ``find_ncc_models``。同じ数のでたらめな画素で同じことをした対照群と比べる。
7. 訓練 15 場面の表(MiddEval3 が手元にあれば測り直し、無ければ記録値)。

所見(2026-11-08 の実測):

* motorcycle で有効画素の bad-2 **4.67 %**・平均誤差 0.960 px・密度 90.0 %(OpenCV SGBM 7.27 % /
  1.315 px / 88.4 %)。無効を誤りに数えると 14.23 %(SGBM 18.00 %)。両方が有効な画素だけで比べると
  4.45 % 対 4.95 % で差は縮む —— 差の半分は「どこを無効にするか」から来ている。
* ★**失敗する場所**: 遮蔽(真値から幾何で数えた 6.9 %)は 57 % が左右一致で無効に落ちる。誤りが
  残るのは奥行きの段差の近く(bad-2 14.1 %)と見え方が変わる面(11.5 %)で、それ以外は 0.85 %。
  ★「無地で壊れる」は、この場面では**最も平らな 1.2 %(7x7 の標準偏差 < 0.003)だけ**に当たる。
  0.01〜0.02 の段(床のコンクリート)は bad-2 0.68 % で全段で最もよく合う。
* **集約の向き**: paths 4 は 2 より bad-2 が 0.88 点下がる(5.55 → 4.67 %)。1/2 に縮めた段は
  8.31 % で、無地の区分では密度が 85.5 → 95.7 % に上がる代わりに bad-2 が 4.14 → 6.47 % に悪化する。
* **距離と面**: ``doffs`` を渡した距離の相対誤差は中央 0.37 %(1 % 以内 82.2 %)。
  ``reconstruct_surface_stereo`` の 331,087 点は OpenCV の ``reprojectImageTo3D`` と最大 0.0006 mm
  (float32 の丸め)で一致、真値の点との 3-D 距離は中央 11.0 mm。
* ★★**円の姿勢は op が正しく、問題は条件の悪さ**。後輪のリム(半長軸 62 px、弧 223°)で
  ``get_circle_pose`` は中心 23.5 mm・法線 7.74° ずれる。真値の円の上の点を渡すと法線 1.2e-6° で
  一致し、縁の点と真値の円の像の食い違い 0.52 px と同じ雑音を足すと法線の誤差は中央 5.79°・
  95 % 点 9.39° —— 実測はこの中に入る。2 つの解は再投影の差 0.007 px で選べず、法線は 50.7° 違う。
  同じ縁を推定した視差で 3-D にすると中心 2.3 mm・法線 1.59°(ステレオの方が 3〜5 倍よい)。
* **疎な対応**: ``points_lepetit`` の上位 400 点で NCC を引くと bad-2 13.76 %、でたらめな画素
  400 点では 16.27 %。スコア 0.9 以上の 180 点に絞ると 2.22 %。``find_ncc_models`` は OpenCV の
  ``matchTemplate`` と最良位置が全点一致、スコアの差 5e-6。
* ★★**MiddEval3 の 15 場面**(nocc、有効画素の bad-2 の中央): 6.52 % 対 SGBM 10.20 %、14 / 15 場面で
  下回る。条件を 1 つだけ変えた対で性格が分かれる: 露出を変えると ms −0.18 点・SGBM +4.99 点、
  照明を変えると ms +0.94 点(ただし無効が増え、無効も誤りにすると +14.35 点)・SGBM +18.08 点。
  ★逆に**平行化だけが違う対**(Playtable、縦の残差 平均 0.24 px)では ms が +12.12 点悪化し、
  SGBM は +0.59 点しか動かない —— 縦のずれに弱い。理由はまだ確かめていない(census の窓の
  ビットが縦の半画素で反転する、が第一の疑い)。遮蔽の数え方は配布元の mask0nocc と中央 93.3 % 一致。

EXTEND: 自前のステレオに差し替えるなら、平行化済みの左右と ``focal`` / ``baseline`` / ``doffs`` / 主点を
渡す。``doffs`` は 2 台の主点の差 ``cx_right - cx_left`` で、0 と決め打ちできるのは主点を揃えて平行化した
場合だけ。``reconstruct_surface_stereo`` は ``doffs`` を受けないので、視差に ``doffs`` を足して渡す
(``Z = f B / (d + doffs)``、``X = (col - cx) Z / f`` と同じ式になる)。

出典表示: Middlebury 2014 stereo datasets, D. Scharstein et al., "High-resolution stereo datasets with
subpixel-accurate ground truth", GCPR 2014(https://vision.middlebury.edu/stereo/data/ ——
"We grant permission to use and publish all images and disparity maps on this website.")。
MiddEval3 の取得は ``py -3.11 tools/fetch_stereoreal_data.py middeval3``(repo 外、SHA-256 固定)。
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import fetch_stereoreal_data as stereodata  # noqa: E402
import realdata  # noqa: E402

LG = fs.ledger

#: scikit-image 同梱版の校正値(``skimage.data.stereo_motorcycle`` の docstring、1/4 縮小版に有効)。
FOCAL_PX = 994.978
CX, CY = 311.193, 254.877
DOFFS_PX = 31.086
BASELINE_MM = 193.001

#: 探索範囲(真の最大視差 59.91 px を含む)と窓。
MAX_DISP = 64
WINDOW = 5
#: bad-N のしきい [px](この分野の慣習)。
BAD_THR = 2.0
#: 無地とみなす 7x7 の局所標準偏差(灰色 0..1)。0.02 で切ると床のコンクリートまで入り、そこは
#: bad2 1 % 前後でよく合う(章 2 の局所標準偏差の段を参照)。本当に崩れるのは最も平らな側だけ。
FLAT_STD = 0.003
#: 局所標準偏差の段(章 2 の曲線)。
STD_BINS = (0.0, 0.003, 0.006, 0.01, 0.02, 0.05, 1.0)
#: 奥行きの段差とみなす真値視差の隣接差 [px] と、その周りの帯の幅 [px]。
EDGE_JUMP, EDGE_BAND = 1.5, 3
#: 見え方が変わるとみなす、真値の対応での左右の明るさの差(灰色 0..1)。
VIEW_DIFF = 0.08

#: 後輪のリムの縁を探す中心の初期値と半径の帯(画素)。画像だけから決めた値。
WHEEL_GUESS = (325.0, 207.0)
WHEEL_RADII = (45.0, 72.0)

#: CI(MiddEval3 が無い)で印字する、手元で測った場面ごとの値(章 7、2026-11-08)。列は
#: (場面, 探索, bad2 有効 nocc, 密度 nocc, 無効も誤り nocc, 無効も誤り 全画素, SGBM bad2, SGBM 密度,
#: SGBM 無効も誤り nocc, 遮蔽の数え方と配布元の印の一致 [%])。データがあれば測り直して印字する。
RECORDED_MIDDEVAL3 = [
    ('Adirondack', 80, 3.964, 92.362, 11.299, 18.217, 6.212, 90.131, 15.468, 96.624),
    ('ArtL', 64, 6.521, 91.893, 14.099, 33.224, 16.702, 84.38, 29.714, 82.311),
    ('Jadeplant', 160, 7.397, 85.729, 20.613, 38.572, 16.231, 76.371, 36.024, 86.028),
    ('Motorcycle', 80, 4.07, 95.327, 8.553, 17.779, 4.587, 91.561, 12.64, 92.946),
    ('MotorcycleE', 80, 3.889, 95.733, 7.989, 17.191, 9.575, 86.171, 22.08, 92.946),
    ('Piano', 80, 9.173, 88.577, 19.548, 25.535, 18.188, 92.372, 24.428, 94.364),
    ('PianoL', 80, 10.113, 73.542, 33.896, 38.599, 36.27, 79.276, 49.478, 94.364),
    ('Pipes', 80, 6.177, 91.4, 14.246, 29.003, 8.406, 91.598, 16.102, 89.011),
    ('Playroom', 96, 10.602, 83.749, 25.13, 35.239, 11.443, 89.692, 20.572, 87.966),
    ('Playtable', 80, 19.152, 83.395, 32.577, 39.327, 10.202, 90.998, 18.285, 93.273),
    ('PlaytableP', 80, 7.032, 90.187, 16.155, 24.759, 9.61, 91.111, 17.644, 93.413),
    ('Recycle', 80, 4.191, 91.105, 12.713, 18.752, 5.579, 89.086, 15.885, 96.499),
    ('Shelves', 64, 22.246, 78.088, 39.283, 42.599, 23.867, 91.216, 30.555, 94.676),
    ('Teddy', 64, 2.778, 96.019, 6.649, 16.08, 7.097, 91.026, 15.434, 91.379),
    ('Vintage', 192, 6.325, 73.277, 31.358, 36.428, 21.976, 75.235, 41.299, 94.672),
]

#: 同じ場面で条件を 1 つだけ変えた対(章 7)。(基準, 変えた方, 何を変えたか)
PAIRS = (("Motorcycle", "MotorcycleE", "露出"), ("Piano", "PianoL", "照明"),
         ("PlaytableP", "Playtable", "平行化(P = 完全、無印 = 縦の残差 平均 0.24 px)"))

SOURCE = ("Middlebury 2014 stereo (Scharstein et al., GCPR 2014), https://vision.middlebury.edu/stereo/data/ "
          "— permission to use and publish granted by the site; scikit-image quarter-size copy")


class GateError(AssertionError):
    """門を通らなかった。"""


def _require_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise SystemExit("参照実装 OpenCV が無い: `pip install -e .[opencv]` で入れる(%s)" % exc) from exc
    return cv2


# --------------------------------------------------------------------------- #
# 採点の道具
# --------------------------------------------------------------------------- #
def score(pred, gt, mask=None):
    """真値のある画素で、有効だけの bad-N・平均誤差・密度と、無効を誤りに数えた bad-N を返す。"""
    p = np.asarray(pred, np.float64)
    ok = np.isfinite(gt)
    if mask is not None:
        ok = ok & mask
    n = int(ok.sum())
    if n == 0:
        raise GateError("採点する画素が 0 個")
    v = ok & np.isfinite(p)
    e = np.abs(p[v] - gt[v])
    bad_valid = 100.0 * float((e > BAD_THR).mean()) if v.any() else float("nan")
    bad_all = 100.0 * float(((e > BAD_THR).sum() + (n - v.sum())) / n)
    return dict(bad=bad_valid, bad_all=bad_all, avg=float(e.mean()) if v.any() else float("nan"),
                density=100.0 * v.sum() / n, n=n)


def occlusion_from_gt(G):
    """真値視差から、右のカメラから見えない(遮蔽された)左の画素を幾何で数える。

    左の画素 x は右の列 ``x - d(x)`` に写る。同じ行のもっと右の画素 x' が ``x' - d(x') <= x - d(x) - 1``
    へ写るなら、x' の方が手前で x への視線を遮る(1 px の余裕つき)。真値の無い画素は判定しない。
    """
    H, W = G.shape
    xr = np.where(np.isfinite(G), np.arange(W)[None, :] - G, np.inf)
    # 右から左へ見た累積最小(自分より右の画素の写り先の最小)
    rmin = np.minimum.accumulate(xr[:, ::-1], axis=1)[:, ::-1]
    right_min = np.full_like(rmin, np.inf)
    right_min[:, :-1] = rmin[:, 1:]
    return np.isfinite(G) & (right_min <= xr - 1.0)


def _std7(L, size=7):
    m = ndimage.uniform_filter(L, size)
    return np.sqrt(np.maximum(ndimage.uniform_filter(L * L, size) - m * m, 0.0))


def depth_edges(G):
    """真値視差の隣接差が ``EDGE_JUMP`` を超える画素の周り ``EDGE_BAND`` px(奥行きの段差の近く)。"""
    g = np.nan_to_num(G, nan=0.0)
    fin = np.isfinite(G)
    jump = np.zeros(G.shape, bool)
    dx = np.abs(np.diff(g, axis=1)) > EDGE_JUMP
    dx &= fin[:, 1:] & fin[:, :-1]
    dy = np.abs(np.diff(g, axis=0)) > EDGE_JUMP
    dy &= fin[1:, :] & fin[:-1, :]
    jump[:, 1:] |= dx
    jump[:, :-1] |= dx
    jump[1:, :] |= dy
    jump[:-1, :] |= dy
    return ndimage.binary_dilation(jump, iterations=EDGE_BAND) & fin


def failure_classes(L, R, G):
    """遮蔽 / 段差の近く / 無地 / 見え方が変わる面 / それ以外 の 5 区分(排他、この順に優先)。"""
    H, W = G.shape
    occ = occlusion_from_gt(G)
    edge = depth_edges(G) & ~occ
    s = _std7(L)
    flat = (s < FLAT_STD) & np.isfinite(G) & ~occ & ~edge
    rr, cc = np.mgrid[0:H, 0:W]
    xr = cc - np.nan_to_num(G, nan=0.0, posinf=0.0)
    inside = np.isfinite(G) & (xr >= 0)
    Rv = ndimage.map_coordinates(R, [rr, np.clip(xr, 0, W - 1)], order=1)
    view = inside & ~occ & ~edge & ~flat & (np.abs(L - Rv) > VIEW_DIFF)
    rest = np.isfinite(G) & ~occ & ~edge & ~flat & ~view
    return {"遮蔽": occ, "段差の近く": edge, "無地": flat, "見え方が変わる面": view, "それ以外": rest}


def sgbm(cv2, L, R, max_disp=MAX_DISP, window=WINDOW):
    """OpenCV の SGBM(参照実装)。左右一致 1 px、無効は NaN。"""
    m = cv2.StereoSGBM_create(minDisparity=0, numDisparities=max_disp, blockSize=window,
                              P1=8 * window * window, P2=32 * window * window, disp12MaxDiff=1,
                              mode=cv2.STEREO_SGBM_MODE_SGBM)
    d = m.compute((L * 255).astype(np.uint8), (R * 255).astype(np.uint8)).astype(np.float64) / 16.0
    d[d < 0] = np.nan
    return d


# --------------------------------------------------------------------------- #
# 円(後輪のリム)
# --------------------------------------------------------------------------- #
def rim_edge_points(L):
    """中心の初期値から放射状に読み、外へ向かって明 → 暗に落ちる最も強い位置を縁とする(画像だけ)。"""
    Ls = ndimage.gaussian_filter(L, 1.0)
    radii = np.arange(WHEEL_RADII[0], WHEEL_RADII[1], 0.25)
    pts = []
    for a in np.deg2rad(np.arange(0.0, 360.0, 1.0)):
        rr = WHEEL_GUESS[0] + radii * np.sin(a)
        cc = WHEEL_GUESS[1] + radii * np.cos(a)
        dp = np.gradient(ndimage.map_coordinates(Ls, [rr, cc], order=1))
        i = int(np.argmin(dp))
        if dp[i] < -0.03:
            pts.append((rr[i], cc[i]))
    return np.array(pts)


def _conic_residual(P, conic):
    """一般の円錐曲線への代数距離を勾配で割った近似の幾何距離 [px]。"""
    x, y = P[:, 1], P[:, 0]
    a, b, c, d, e, f = conic
    val = a * x * x + b * x * y + c * y * y + d * x + e * y + f
    gx = 2 * a * x + b * y + d
    gy = b * x + 2 * c * y + e
    return np.abs(val) / np.maximum(np.hypot(gx, gy), 1e-12)


def _fit_conic(P):
    x, y = P[:, 1], P[:, 0]
    A = np.column_stack([x * x, x * y, y * y, x, y, np.ones_like(x)])
    s = np.linalg.norm(A, axis=0)
    _, _, Vt = np.linalg.svd(A / s, full_matrices=False)
    return Vt[-1] / s


def ellipse_axes(con):
    """円錐曲線の係数から楕円の中心 (row, col) と半軸 (長, 短) を返す。楕円でなければ None。"""
    a, b, c, d, e, f = con
    M = np.array([[a, b / 2], [b / 2, c]])
    if np.linalg.det(M) <= 0:
        return None
    x0, y0 = np.linalg.solve(2 * M, [-d, -e])
    k = -(a * x0 * x0 + b * x0 * y0 + c * y0 * y0 + d * x0 + e * y0 + f)
    w = np.linalg.eigvalsh(M)
    if k / w[0] <= 0 or k / w[1] <= 0:
        return None
    ax = np.sqrt(k / w)
    return (y0, x0), (float(ax.max()), float(ax.min()))


def ransac_ellipse(P, thr=1.0, iters=3000, seed=0):
    """楕円を RANSAC で当て、内側の点を返す(後輪は排気管と腕で一部が隠れる)。

    半軸が :data:`WHEEL_RADII` の帯に入る楕円だけを候補にする(泥よけの縁などの別の弧を拾わない)。
    """
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(iters):
        idx = rng.choice(len(P), 5, replace=False)
        con = _fit_conic(P[idx])
        geo = ellipse_axes(con)
        if geo is None or not (WHEEL_RADII[0] <= geo[1][1] <= geo[1][0] <= WHEEL_RADII[1]):
            continue
        inl = _conic_residual(P, con) < thr
        if best is None or inl.sum() > best.sum():
            best = inl
    if best is None:
        raise GateError("楕円が 1 つも当たらなかった")
    return best


def circle_from_3d(Q):
    """3-D 点に平面と円を当て、中心・法線(カメラへ向く)・半径・平面の RMS・円の RMS を返す。"""
    m = Q.mean(0)
    _, S, Vt = np.linalg.svd(Q - m)
    n, e1, e2 = Vt[2], Vt[0], Vt[1]
    u, v = (Q - m) @ e1, (Q - m) @ e2
    A = np.c_[2 * u, 2 * v, np.ones_like(u)]
    sol, *_ = np.linalg.lstsq(A, u * u + v * v, rcond=None)
    r = float(np.sqrt(sol[2] + sol[0] ** 2 + sol[1] ** 2))
    c = m + sol[0] * e1 + sol[1] * e2
    if n @ c > 0:
        n = -n
    return dict(center=c, normal=n, radius=r, plane_rms=float(S[2] / np.sqrt(len(Q))),
                circle_rms=float(np.sqrt(np.mean((np.hypot(u - sol[0], v - sol[1]) - r) ** 2))))


def _angle(a, b):
    """2 つの単位ベクトルのなす角 [度]。"""
    return float(np.degrees(np.arccos(np.clip(float(np.dot(a, b)), -1.0, 1.0))))


def arc_span_deg(C):
    """点列が楕円の中心から見て占める角度の幅 [度](最大の空きを除いた残り)。"""
    ang = np.sort(np.degrees(np.arctan2(C[:, 0] - C[:, 0].mean(), C[:, 1] - C[:, 1].mean())))
    gaps = np.diff(np.r_[ang, ang[0] + 360.0])
    return float(360.0 - gaps.max())


def radius_px(C):
    """点列に当てた楕円の半長軸 [px](楕円の大きさの目安)。"""
    geo = ellipse_axes(_fit_conic(C))
    if geo is None:
        raise GateError("縁の点が楕円にならない")
    return geo[1][0]


def pixels_to_3d(rc, disp):
    """画素 (row, col) と視差から、真値と同じ式で 3-D 点 [mm] を作る。"""
    Z = FOCAL_PX * BASELINE_MM / (disp + DOFFS_PX)
    return np.c_[(rc[:, 1] - CX) * Z / FOCAL_PX, (rc[:, 0] - CY) * Z / FOCAL_PX, Z]


# --------------------------------------------------------------------------- #
# 疎な対応(Lepetit 点 + NCC)
# --------------------------------------------------------------------------- #
HALF = 7          # 窓の半幅(15x15)


def sparse_ncc(cv2, L, R, pts):
    """各点の 15x15 を左から切り出し、右の同じ行の帯で NCC の最良位置を探す。"""
    H, W = L.shape
    out = []
    for r, c in pts:
        r0, c0 = int(round(r)), int(round(c))
        if r0 < HALF or r0 > H - HALF - 1 or c0 < MAX_DISP + HALF or c0 > W - HALF - 1:
            continue
        patch = np.asarray(LG.crop_rectangle2(L, float(r0), float(c0), 0.0, HALF, HALF))
        model = LG.create_ncc_model(patch)
        lo = c0 - MAX_DISP - HALF
        strip = R[r0 - HALF:r0 + HALF + 1, lo:c0 + HALF + 1]
        res = LG.find_ncc_models(model, strip, min_score=-1.0, max_matches=1)
        if res["num"] == 0:
            continue
        m = res["matches"][0]
        ref = cv2.matchTemplate(strip.astype(np.float32), patch.astype(np.float32), cv2.TM_CCOEFF_NORMED)[0]
        j = int(np.argmax(ref))
        out.append((r0, c0, c0 - (lo + float(m["col"])), float(m["score"]), c0 - (lo + j + HALF),
                    float(ref[j]), float(m["row"])))
    return np.array(out, np.float64)


# --------------------------------------------------------------------------- #
# 図の道具
# --------------------------------------------------------------------------- #
def oblique_render(points, gray, yaw_deg=-28.0, pitch_deg=12.0, size=(500, 741)):
    """点群を斜めから見た絵(z-buffer、2x2 画素の点、色は左の画像の明るさに陰影)。"""
    P = np.asarray(points, np.float64)
    c = np.median(P, axis=0)
    a, b = np.deg2rad(yaw_deg), np.deg2rad(pitch_deg)
    Ry = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
    Q = (P - c) @ (Rx @ Ry).T + c
    H, W = size
    u = FOCAL_PX * Q[:, 0] / Q[:, 2] + CX
    v = FOCAL_PX * Q[:, 1] / Q[:, 2] + CY
    img = np.zeros((H, W, 3))
    zbuf = np.full((H, W), np.inf)
    order = np.argsort(-Q[:, 2])         # 遠い順に塗り、近い点が上書きする
    for du in (0, 1):
        for dv in (0, 1):
            uu = np.floor(u[order]).astype(int) + du
            vv = np.floor(v[order]).astype(int) + dv
            ok = (uu >= 0) & (uu < W) & (vv >= 0) & (vv < H)
            zz = Q[order, 2]
            idx = np.nonzero(ok)[0]
            # 遠い順の書き込みで、後に書いた(近い)値が残る
            img[vv[idx], uu[idx]] = gray[order][idx, None]
            zbuf[vv[idx], uu[idx]] = np.minimum(zbuf[vv[idx], uu[idx]], zz[idx])
    return np.clip(img, 0, 1)


def draw_points(rgb, pts, colors, r=2):
    im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for (y, x), col in zip(pts, colors):
        dr.ellipse([x - r, y - r, x + r, y + r], outline=col, width=1)
    return np.asarray(im).astype(np.float64) / 255.0


def draw_polyline(rgb, pts, col, width=1):
    im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    ImageDraw.Draw(im).line([(float(x), float(y)) for y, x in pts], fill=col, width=width)
    return np.asarray(im).astype(np.float64) / 255.0


def project_circle(center, normal, radius, count=360):
    """3-D の円を画像へ写した点列 (row, col)。"""
    n = normal / np.linalg.norm(normal)
    a = np.cross(n, [0.0, 0.0, 1.0])
    if np.linalg.norm(a) < 1e-9:
        a = np.array([1.0, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(n, a)
    t = np.linspace(0, 2 * np.pi, count)
    X = center[None, :] + radius * (np.cos(t)[:, None] * a + np.sin(t)[:, None] * b)
    return np.c_[FOCAL_PX * X[:, 1] / X[:, 2] + CY, FOCAL_PX * X[:, 0] / X[:, 2] + CX]


# --------------------------------------------------------------------------- #
# MiddEval3(手元にあるときだけ)
# --------------------------------------------------------------------------- #
def middeval3_scenes(paths):
    """訓練 15 場面を zip から読み、(名前, 左, 右, 真値, 遮蔽の印, 校正) を順に返す。"""
    data = zipfile.ZipFile(paths["MiddEval3-data-Q.zip"])
    gt = zipfile.ZipFile(paths["MiddEval3-GT0-Q.zip"])
    names = sorted({n.split("/")[2] for n in gt.namelist()
                    if n.startswith("MiddEval3/trainingQ/") and n.endswith("disp0GT.pfm")})
    if len(names) != 15:
        raise GateError("MiddEval3 の訓練場面が 15 でない: %d" % len(names))
    with tempfile.TemporaryDirectory(prefix="middeval3_") as tmp:
        for nm in names:
            base = "MiddEval3/trainingQ/%s/" % nm

            def gray(member):
                a = np.asarray(Image.open(io.BytesIO(data.read(base + member))).convert("RGB"), np.float64)
                return (a @ np.array([0.2125, 0.7154, 0.0721])) / 255.0

            pfm = Path(tmp) / (nm + ".pfm")
            pfm.write_bytes(gt.read(base + "disp0GT.pfm"))
            G, _scale = fs.read_pfm(str(pfm))
            G = np.asarray(G, np.float64)
            mask = np.asarray(Image.open(io.BytesIO(gt.read(base + "mask0nocc.png"))))
            calib = {}
            for line in data.read(base + "calib.txt").decode("ascii").splitlines():
                k, _, v = line.partition("=")
                calib[k.strip()] = v.strip()
            yield nm, gray("im0.png"), gray("im1.png"), G, mask, calib


def section_middeval3(cv2, paths):
    rows = []
    agree = []
    for nm, L, R, G, mask, calib in middeval3_scenes(paths):
        G = np.where(np.isfinite(G), G, np.nan)
        ndisp = int(calib["ndisp"])
        md = int(np.ceil(ndisp / 16.0) * 16)
        nocc = mask == 255
        occ_mask = mask == 128
        occ_geo = occlusion_from_gt(np.where(np.isfinite(G), G, np.nan))
        both = np.isfinite(G) & (nocc | occ_mask)
        agree.append(100.0 * float((occ_geo[both] == occ_mask[both]).mean()))
        t = time.perf_counter()
        d = LG.binocular_disparity_ms(L, R, max_disp=md, window=WINDOW, paths=4)["disparity"]
        sec = time.perf_counter() - t
        s_all = score(d, G)
        s_nocc = score(d, G, nocc)
        c = score(sgbm(cv2, L, R, md), G, nocc)
        rows.append((nm, md, s_nocc["bad"], s_nocc["density"], s_nocc["bad_all"], s_all["bad_all"],
                     c["bad"], c["density"], c["bad_all"], agree[-1], sec))
    realdata.mark_read("middlebury:MiddEval3-Q-training")
    return rows


def print_middeval3(rows, recorded=False):
    print("   %-12s %4s %7s %6s %8s %8s | %7s %6s %8s | %6s" % (
        "場面", "探索", "bad2有効", "密度", "bad2全nocc", "bad2全all", "SGBM有効", "密度", "SGBM全", "遮蔽一致"))
    for r in rows:
        print("   %-12s %4d %6.2f%% %5.1f%% %7.2f%% %7.2f%% | %6.2f%% %5.1f%% %7.2f%% | %5.1f%%"
              % tuple(r[:10]))
    tag = "(記録値)" if recorded else ""
    med = np.median(np.array([r[2:10] for r in rows], float), axis=0)
    print("   中央値%s bad2有効 %.2f %% / 密度 %.1f %% / 無効も誤り %.2f %%(nocc) —— SGBM %.2f %% / %.1f %% / %.2f %%"
          "、遮蔽の数え方と配布元の印の一致 %.1f %%"
          % (tag, med[0], med[1], med[2], med[4], med[5], med[6], med[7]))
    return med


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    cv2 = _require_cv2()
    L, R, G = realdata.sample_stereo_pair()
    G = np.where(np.isfinite(G), G, np.nan)          # 穴は +inf のこともある(poc_real_stereo_depth)
    ok = np.isfinite(G)
    H, W = L.shape
    print("実写ステレオ(Middlebury 2014 motorcycle、scikit-image 同梱の 1/4 縮小、%dx%d)" % (H, W))
    print("  真値のある画素 %.1f %%、視差 %.2f〜%.2f px、探索 %d px、窓 %d"
          % (100 * ok.mean(), np.nanmin(G), np.nanmax(G), MAX_DISP, WINDOW))
    if np.nanmax(G) >= MAX_DISP:
        raise GateError("探索範囲が真の最大視差を含まない")

    # --- 1 視差の採点 -------------------------------------------------------- #
    t = time.perf_counter()
    res = LG.binocular_disparity_ms(L, R, max_disp=MAX_DISP, window=WINDOW, paths=4)
    t_ms = time.perf_counter() - t
    D = np.asarray(res["disparity"], np.float64)
    s_ms = score(D, G)
    t = time.perf_counter()
    Dcv = sgbm(cv2, L, R)
    t_cv = time.perf_counter() - t
    s_cv = score(Dcv, G)
    print("\n1. 視差(真値のある %d 画素)" % s_ms["n"])
    print("   binocular_disparity_ms  bad2 %.2f %%(有効だけ)  平均誤差 %.3f px  密度 %.1f %%  "
          "無効も誤り %.2f %%  (%.1f 秒)" % (s_ms["bad"], s_ms["avg"], s_ms["density"], s_ms["bad_all"], t_ms))
    print("   OpenCV SGBM(参照)    bad2 %.2f %%(有効だけ)  平均誤差 %.3f px  密度 %.1f %%  "
          "無効も誤り %.2f %%  (%.2f 秒)" % (s_cv["bad"], s_cv["avg"], s_cv["density"], s_cv["bad_all"], t_cv))
    both = ok & np.isfinite(D) & np.isfinite(Dcv)
    e_ms = np.abs(D - G)[both]
    e_cv = np.abs(Dcv - G)[both]
    print("   両方が有効な %d 画素だけで: bad2 %.2f %% 対 %.2f %%、平均誤差 %.3f 対 %.3f px"
          % (both.sum(), 100 * (e_ms > BAD_THR).mean(), 100 * (e_cv > BAD_THR).mean(), e_ms.mean(), e_cv.mean()))
    frac = D[np.isfinite(D)] - np.floor(D[np.isfinite(D)])
    print("   小数の補間: 小数部が 0 でない有効画素 %.1f %%" % (100 * (frac > 1e-9).mean()))
    g1 = [s_ms["bad"] < 8.0, s_ms["density"] > 85.0, s_ms["avg"] < 1.5,
          100 * (e_ms > BAD_THR).mean() < 100 * (e_cv > BAD_THR).mean(), (frac > 1e-9).mean() > 0.5]
    if not all(g1):
        raise GateError("章 1: %s / %s" % (g1, s_ms))

    # --- 2 失敗する場所 ------------------------------------------------------ #
    cls = failure_classes(L, R, G)
    print("\n2. 失敗する場所(真値から区分、排他)")
    cls_rows = []
    for nm, m in cls.items():
        a, b = score(D, G, m), score(Dcv, G, m)
        cls_rows.append((nm, 100.0 * m.sum() / ok.sum(), a, b))
        print("   %-10s 画素の %5.1f %%  ms: bad2 %6.2f %% 無効 %5.1f %%  |  SGBM: bad2 %6.2f %% 無効 %5.1f %%"
              % (nm, cls_rows[-1][1], a["bad"], 100 - a["density"], b["bad"], 100 - b["density"]))
    by = {r[0]: r for r in cls_rows}
    sd = _std7(L)
    occ_all = cls["遮蔽"]
    curve = []
    for lo_s, hi_s in zip(STD_BINS[:-1], STD_BINS[1:]):
        k = (sd >= lo_s) & (sd < hi_s) & ok & ~occ_all
        r = score(D, G, k)
        curve.append((lo_s, hi_s, 100.0 * k.sum() / ok.sum(), r["bad"], 100 - r["density"], r["bad_all"]))
    print("   局所標準偏差(7x7)の段ごと(遮蔽を除く):")
    for lo_s, hi_s, frac_s, b_s, inv_s, ba_s in curve:
        print("     %.3f〜%.3f  画素の %5.1f %%  bad2 %5.2f %%  無効 %4.1f %%  無効も誤り %5.2f %%"
              % (lo_s, hi_s, frac_s, b_s, inv_s, ba_s))
    # 遮蔽は左右一致で無効に落ちる。段差の近くと見え方が変わる面は誤りが残る。
    # 無地(最も平らな段)は無効が増える —— ただし 0.02 まで広げると逆に最もよく合う段になる。
    rest_r = by["それ以外"][2]
    g2 = [100 - by["遮蔽"][2]["density"] > 5 * (100 - rest_r["density"]),
          by["段差の近く"][2]["bad"] > 3 * rest_r["bad"],
          by["見え方が変わる面"][2]["bad"] > 3 * rest_r["bad"],
          by["無地"][2]["bad_all"] > rest_r["bad_all"],
          min(c[3] for c in curve) == min(c[3] for c in curve[1:5]),
          all(r[1] > 0.5 for r in cls_rows)]
    if not all(g2):
        raise GateError("章 2: %s" % g2)

    # --- 3 集約の向きと粗い段 ------------------------------------------------- #
    print("\n3. 集約の向き(op の中)と 1/2 の粗い段(op の外)")
    t = time.perf_counter()
    D2 = np.asarray(LG.binocular_disparity_ms(L, R, max_disp=MAX_DISP, window=WINDOW, paths=2)["disparity"])
    t2 = time.perf_counter() - t
    s_p2 = score(D2, G)
    print("   paths=2  bad2 %.2f %%  密度 %.1f %%  無効も誤り %.2f %%  (%.1f 秒)"
          % (s_p2["bad"], s_p2["density"], s_p2["bad_all"], t2))
    print("   paths=4  bad2 %.2f %%  密度 %.1f %%  無効も誤り %.2f %%  (%.1f 秒)"
          % (s_ms["bad"], s_ms["density"], s_ms["bad_all"], t_ms))
    h2, w2 = H // 2 * 2, W // 2 * 2
    Lh = L[:h2, :w2].reshape(h2 // 2, 2, w2 // 2, 2).mean((1, 3))
    Rh = R[:h2, :w2].reshape(h2 // 2, 2, w2 // 2, 2).mean((1, 3))
    t = time.perf_counter()
    Dh = np.asarray(LG.binocular_disparity_ms(Lh, Rh, max_disp=MAX_DISP // 2, window=WINDOW, paths=4)["disparity"])
    th = time.perf_counter() - t
    Dup = np.full((H, W), np.nan)
    Dup[:h2, :w2] = 2.0 * np.kron(Dh, np.ones((2, 2)))
    s_half = score(Dup, G)
    print("   1/2 の段(視差 x2、最近傍で戻す)  bad2 %.2f %%  密度 %.1f %%  無効も誤り %.2f %%  (%.1f 秒)"
          % (s_half["bad"], s_half["density"], s_half["bad_all"], th))
    flat = cls["無地"]
    s_half_flat, s_full_flat = score(Dup, G, flat), score(D, G, flat)
    print("   無地の区分だけ: 1/2 の段 bad2 %.2f %% 密度 %.1f %%  /  原寸 bad2 %.2f %% 密度 %.1f %%"
          % (s_half_flat["bad"], s_half_flat["density"], s_full_flat["bad"], s_full_flat["density"]))
    g3 = [s_ms["bad"] < s_p2["bad"], s_half["bad"] > s_ms["bad"], th < t_ms]
    if not all(g3):
        raise GateError("章 3: %s" % g3)

    # --- 4 距離と面 ---------------------------------------------------------- #
    dist = LG.binocular_distance_ms(L, R, focal=FOCAL_PX, baseline=BASELINE_MM, doffs=DOFFS_PX,
                                    max_disp=MAX_DISP, window=WINDOW, paths=4)
    Z = np.asarray(dist["distance"], np.float64)
    Zt = FOCAL_PX * BASELINE_MM / (G + DOFFS_PX)
    vz = ok & np.isfinite(Z)
    rel = np.abs(Z[vz] - Zt[vz]) / Zt[vz]
    same_disp = bool(np.array_equal(np.asarray(dist["disparity"]), D, equal_nan=True))
    print("\n4. 距離と面")
    print("   真の距離 %.0f〜%.0f mm。binocular_distance_ms の相対誤差: 中央 %.2f %%、1 %% 以内 %.1f %%、"
          "5 %% 以内 %.1f %%(%d 画素)" % (np.nanmin(Zt), np.nanmax(Zt), 100 * np.median(rel),
                                          100 * (rel < 0.01).mean(), 100 * (rel < 0.05).mean(), vz.sum()))
    print("   視差は binocular_disparity_ms と同一: %s" % ("はい" if same_disp else "いいえ"))
    pts = np.asarray(LG.reconstruct_surface_stereo(np.where(np.isfinite(D), D + DOFFS_PX, np.nan),
                                                   focal=FOCAL_PX, baseline=BASELINE_MM, cx=CX, cy=CY))
    Qm = np.array([[1, 0, 0, -CX], [0, 1, 0, -CY], [0, 0, 0, FOCAL_PX], [0, 0, 1.0 / BASELINE_MM, 0]])
    cv_xyz = cv2.reprojectImageTo3D(np.where(np.isfinite(D), D + DOFFS_PX, 0).astype(np.float32), Qm)
    cv_pts = cv_xyz[np.isfinite(D)].astype(np.float64)
    diff = np.abs(pts - cv_pts).max()
    print("   reconstruct_surface_stereo: %d 点、OpenCV の reprojectImageTo3D と最大差 %.3g mm"
          "(float32 の丸めの範囲)" % (len(pts), diff))
    gt_pts = pixels_to_3d(np.argwhere(np.isfinite(D)).astype(float), G[np.isfinite(D)])
    e3 = np.linalg.norm(pts - gt_pts, axis=1)
    e3 = e3[np.isfinite(e3)]
    print("   真値の点との 3-D 距離: 中央 %.1f mm、90 %% 点 %.1f mm" % (np.median(e3), np.quantile(e3, 0.9)))
    g4 = [same_disp, np.median(rel) < 0.01, diff < 0.5, np.median(e3) < 30.0, len(pts) == int(np.isfinite(D).sum())]
    if not all(g4):
        raise GateError("章 4: %s" % g4)

    # --- 5 円の姿勢 ---------------------------------------------------------- #
    P = rim_edge_points(L)
    inl = ransac_ellipse(P)
    C = P[inl]
    gt_d = ndimage.map_coordinates(np.where(ok, G, np.nan), [C[:, 0], C[:, 1]], order=0)
    gok = np.isfinite(gt_d)
    truth = circle_from_3d(pixels_to_3d(C[gok], gt_d[gok]))
    cam = {"fx": FOCAL_PX, "fy": FOCAL_PX, "cx": CX, "cy": CY}
    cp = LG.get_circle_pose(C, truth["radius"], cam)
    sols = []
    for k in range(2):
        dc = float(np.linalg.norm(cp["center"][k] - truth["center"]))
        dn = float(np.degrees(np.arccos(np.clip(cp["normal"][k] @ truth["normal"], -1, 1))))
        sols.append((dc, dn, float(cp["rms_px"][k])))
    best = int(np.argmin([s[1] for s in sols]))
    # 推定した視差で同じ縁を 3-D にした円(ステレオだけの答え)
    est_d = ndimage.map_coordinates(np.where(np.isfinite(D), D, np.nan), [C[:, 0], C[:, 1]], order=0)
    eok = np.isfinite(est_d)
    stereo_c = circle_from_3d(pixels_to_3d(C[eok], est_d[eok]))
    print("\n5. 円の姿勢(後輪のリム)")
    print("   縁の候補 %d 点 → 楕円の RANSAC で %d 点(排気管と腕に隠れた所が外れる)" % (len(P), len(C)))
    print("   真値(真値視差の 3-D に平面と円): 半径 %.1f mm、距離 %.0f mm、平面の RMS %.2f mm、円の RMS %.2f mm"
          % (truth["radius"], np.linalg.norm(truth["center"]), truth["plane_rms"], truth["circle_rms"]))
    for k, (dc, dn, rms) in enumerate(sols):
        print("   get_circle_pose 解 %d: 中心のずれ %.1f mm、法線のずれ %.2f°、再投影 %.3f px%s"
              % (k + 1, dc, dn, rms, "  ← 真値に近い方" if k == best else ""))
    print("   2 つの解の再投影の差 %.3f px —— 1 枚の像からは選べない。法線どうしは %.1f° 離れている"
          % (abs(sols[0][2] - sols[1][2]),
             np.degrees(np.arccos(np.clip(cp["normal"][0] @ cp["normal"][1], -1, 1)))))
    sc_dc = float(np.linalg.norm(stereo_c["center"] - truth["center"]))
    sc_dn = float(np.degrees(np.arccos(np.clip(stereo_c["normal"] @ truth["normal"], -1, 1))))
    print("   推定した視差だけで同じことをすると: 中心のずれ %.1f mm、法線のずれ %.2f°、半径 %.1f mm"
          % (sc_dc, sc_dn, stereo_c["radius"]))
    k_scale = 1.05
    cp5 = LG.get_circle_pose(C, truth["radius"] * k_scale, cam)
    ratio = np.linalg.norm(cp5["center"][best]) / np.linalg.norm(cp["center"][best])
    print("   半径を 5 %% 大きく渡すと、中心までの距離は %.4f 倍(単眼の円は半径で距離の目盛りが決まる)" % ratio)
    # 縁の点と真値の円の食い違い(画像の上で)と、op そのものの正しさ(真値の円の上の点を渡す)
    proj = project_circle(truth["center"], truth["normal"], truth["radius"], 7200)
    dd = np.hypot(C[:, None, 0] - proj[None, :, 0], C[:, None, 1] - proj[None, :, 1])
    near = proj[np.argmin(dd, axis=1)]
    gap = float(np.sqrt(np.mean(np.min(dd, axis=1) ** 2)))
    ideal = LG.get_circle_pose(near, truth["radius"], cam)
    ideal_dn = min(_angle(ideal["normal"][k], truth["normal"]) for k in range(2))
    ideal_dc = float(np.min(np.linalg.norm(ideal["center"] - truth["center"], axis=1)))
    # 同じ弧・同じ点数に、食い違いと同じ大きさの雑音を足したときの法線の誤差の分布
    rng = np.random.default_rng(0)
    mc = []
    for _ in range(200):
        r_ = LG.get_circle_pose(near + rng.normal(0.0, gap / np.sqrt(2.0), near.shape), truth["radius"], cam)
        mc.append(min(_angle(r_["normal"][k], truth["normal"]) for k in range(2)))
    mc = np.array(mc)
    print("   縁の点と真値の円の像の食い違い: RMS %.2f px(弧は %.0f° ぶん)" % (gap, arc_span_deg(C)))
    print("   真値の円の上の点(同じ角度)を渡すと: 法線のずれ %.2g°、中心のずれ %.2g mm —— op は正しい"
          % (ideal_dn, ideal_dc))
    print("   その点に %.2f px RMS の雑音を足すと(200 回): 法線のずれ 中央 %.2f°、95 %% 点 %.2f°"
          " —— 実測の %.2f° はこの中に入る(半長軸 %.0f px の楕円では 0.5 px が数度になる)"
          % (gap, np.median(mc), np.quantile(mc, 0.95), sols[best][1], radius_px(C)))
    g5 = [len(C) >= 60, truth["plane_rms"] < 3.0, truth["circle_rms"] < 3.0, gap < 1.0,
          ideal_dn < 1e-4, ideal_dc < 1e-6, sols[best][1] <= np.quantile(mc, 0.95),
          np.median(mc) > 2.0, sc_dn < sols[best][1] and sc_dc < sols[best][0],
          abs(sols[0][2] - sols[1][2]) < 0.05, abs(ratio - k_scale) < 1e-6,
          max(s[1] for s in sols) > 10.0]
    if not all(g5):
        raise GateError("章 5: %s / %s" % (g5, sols))

    # --- 6 疎な対応 ---------------------------------------------------------- #
    t = time.perf_counter()
    lp = np.asarray(LG.points_lepetit(L, radius=3, min_score=0.05))
    t_lp = time.perf_counter() - t
    rng = np.random.default_rng(0)
    N = 400
    lp_use = lp[:N]
    rnd = np.c_[rng.uniform(HALF, H - HALF - 1, N), rng.uniform(MAX_DISP + HALF, W - HALF - 1, N)]
    A = sparse_ncc(cv2, L, R, lp_use)
    B = sparse_ncc(cv2, L, R, rnd)

    def judge(M):
        g = G[M[:, 0].astype(int), M[:, 1].astype(int)]
        k = np.isfinite(g)
        e = np.abs(M[k, 2] - g[k])
        return 100.0 * (e > BAD_THR).mean(), int(k.sum()), M[k], e

    bad_lp, n_lp, A_ok, e_lp = judge(A)
    bad_rn, n_rn, _B_ok, _e_rn = judge(B)
    same_pos = float(np.mean(np.abs(A[:, 2] - A[:, 4]) < 1e-9))
    score_diff = float(np.abs(A[:, 3] - A[:, 5]).max())
    hi = A_ok[:, 3] >= 0.9
    bad_hi = 100.0 * float((e_lp[hi] > BAD_THR).mean())
    print("\n6. 疎な対応(15x15 の NCC、右の同じ行の帯 %d px)" % MAX_DISP)
    print("   points_lepetit: %d 点(%.1f 秒)、上位 %d 点で照合 → 真値のある %d 点の bad2 %.2f %%"
          % (len(lp), t_lp, N, n_lp, bad_lp))
    print("   対照群(でたらめな画素 %d 点): 真値のある %d 点の bad2 %.2f %%" % (N, n_rn, bad_rn))
    print("   スコア 0.9 以上に絞ると %d 点で bad2 %.2f %%" % (hi.sum(), bad_hi))
    print("   OpenCV matchTemplate と: 最良位置の一致 %.1f %%、スコアの最大差 %.2g" % (100 * same_pos, score_diff))
    g6 = [len(lp) > 500, bad_lp < bad_rn, same_pos == 1.0, score_diff < 1e-4, bad_hi < bad_lp, n_lp > 300]
    if not all(g6):
        raise GateError("章 6: %s" % g6)

    # --- 7 MiddEval3 --------------------------------------------------------- #
    print("\n7. Middlebury MiddEval3 訓練 15 場面(1/4 解像度、nocc = 遮蔽されていない画素)")
    paths = stereodata.files("middeval3", required=False)
    if paths is None:
        print("   手元に無い(py -3.11 tools/fetch_stereoreal_data.py middeval3 で取得)。記録値を印字する:")
        if RECORDED_MIDDEVAL3 is None:
            raise GateError("記録値が無い")
        mrows = RECORDED_MIDDEVAL3
        med = print_middeval3(mrows, recorded=True)
    else:
        mrows = section_middeval3(cv2, paths)
        med = print_middeval3(mrows)
        print("   RECORDED = %r" % ([tuple(round(float(x), 3) if not isinstance(x, (str, int)) else x
                                           for x in r[:10]) for r in mrows],))
    by7 = {r[0]: r for r in mrows}
    deltas = {}
    for base, other, what in PAIRS:
        dm = by7[other][2] - by7[base][2]
        dc = by7[other][6] - by7[base][6]
        dma = by7[other][4] - by7[base][4]
        dca = by7[other][8] - by7[base][8]
        deltas[what.split("(")[0]] = (dm, dc, dma, dca)
        print("   %s → %s(%s を変えた): ms bad2 %+.2f 点(無効も誤り %+.2f)/ SGBM %+.2f 点(%+.2f)"
              % (base, other, what, dm, dma, dc, dca))
    wins = sum(r[2] < r[6] for r in mrows)
    print("   有効画素の bad2 で SGBM を下回った場面 %d / 15" % wins)
    g7 = [len(mrows) == 15, med[7] > 90.0, med[0] < med[4],
          abs(deltas["露出"][2]) < 2.0 and deltas["露出"][3] > 5.0,
          abs(deltas["照明"][0]) < 2.0 and deltas["照明"][1] > 10.0 and deltas["照明"][2] < deltas["照明"][3] / 1.5,
          deltas["平行化"][0] > 8.0 and abs(deltas["平行化"][1]) < 2.0 and abs(deltas["平行化"][3]) < 2.0]
    if not all(g7):
        raise GateError("章 7: %s" % g7)

    # --- 図 ---------------------------------------------------------------- #
    lo, hi_d = float(np.nanmin(G)), float(np.nanmax(G))
    render = oblique_render(pts, L[np.isfinite(D)])
    figs.save_grid(
        "scene",
        [np.dstack([L] * 3), np.asarray(fs.colorize_disparity(np.where(np.isfinite(D), D, np.inf), vmin=lo, vmax=hi_d)),
         np.asarray(fs.colorize_disparity(np.where(ok, G, np.inf), vmin=lo, vmax=hi_d)), render],
        ["左(実写)", "binocular_disparity_ms(無効 = 黒)", "真値視差(穴 = 黒)",
         "reconstruct_surface_stereo を斜めから"],
        title="実写のステレオ対から視差と面", ncols=2,
        caption="bad2 %.2f %%(有効だけ)/ 密度 %.1f %%。OpenCV SGBM は %.2f %% / %.1f %%。"
                % (s_ms["bad"], s_ms["density"], s_cv["bad"], s_cv["density"]))

    col = {"遮蔽": (0.85, 0.37, 0.0), "段差の近く": (0.94, 0.89, 0.26), "無地": (0.0, 0.45, 0.70),
           "見え方が変わる面": (0.8, 0.47, 0.65), "それ以外": (0.6, 0.6, 0.6)}
    over = np.dstack([L] * 3) * 0.45
    for nm, m in cls.items():
        over[m] = over[m] + 0.55 * np.array(col[nm])
    err = np.where(ok & np.isfinite(D), np.abs(D - G) > BAD_THR, False)
    inval = ok & ~np.isfinite(D)
    emap = np.dstack([L] * 3) * 0.35
    emap[err] = (0.84, 0.37, 0.0)
    emap[inval] = (0.0, 0.0, 0.0)
    emap[ok & np.isfinite(D) & ~err] = emap[ok & np.isfinite(D) & ~err] + 0.3
    figs.save_grid(
        "failure_map", [over, emap],
        ["区分: 橙 遮蔽 / 黄 段差の近く / 青 無地 / 桃 見え方が変わる面 / 灰 それ以外",
         "橙 = 誤り(|d - 真値| > 2 px)、黒 = 無効(左右一致で落とした)"],
        title="失敗する場所 —— 遮蔽は無効に、段差の近くと光沢は誤りに", ncols=1,
        caption=" / ".join("%s bad2 %.1f %% 無効 %.1f %%" % (r[0], r[2]["bad"], 100 - r[2]["density"]) for r in cls_rows))

    wr0, wr1, wc0, wc1 = 230, 400, 110, 310
    crop = np.dstack([L] * 3)[wr0:wr1, wc0:wc1]
    off = np.array([wr0, wc0], float)
    crop = draw_polyline(crop, project_circle(truth["center"], truth["normal"], truth["radius"]) - off,
                         (240, 228, 66), 1)
    other = 1 - best
    crop = draw_polyline(crop, project_circle(cp["center"][other], cp["normal"][other], truth["radius"]) - off,
                         (213, 94, 0), 1)
    crop = draw_polyline(crop, project_circle(cp["center"][best], cp["normal"][best], truth["radius"]) - off,
                         (0, 114, 178), 1)
    crop = draw_points(crop, C - off, [(0, 158, 115)] * len(C), r=1)
    figs.save_grid(
        "wheel_pose", [crop, np.dstack([L] * 3)[wr0:wr1, wc0:wc1]],
        ["緑 = 縁の点、黄 = 真値の円、青 = 真値に近い解、橙 = もう 1 つの解", "元の画像"],
        title="後輪のリムから円の姿勢(get_circle_pose)", ncols=2,
        caption="真値に近い解: 中心 %.1f mm・法線 %.2f°。もう 1 つの解は法線が %.1f° 違うのに再投影の差は %.3f px。"
                % (sols[best][0], sols[best][1], sols[other][1], abs(sols[0][2] - sols[1][2])))

    kk = A_ok
    good = np.abs(kk[:, 2] - G[kk[:, 0].astype(int), kk[:, 1].astype(int)]) <= BAD_THR
    sp = draw_points(np.dstack([L] * 3), kk[:, :2], [(0, 114, 178) if g else (213, 94, 0) for g in good], r=3)
    figs.save_grid(
        "sparse_ncc", [sp],
        ["青 = 正しい視差(2 px 以内)、橙 = 誤り"],
        title="points_lepetit の点で NCC の対応", ncols=1,
        caption="Lepetit 点 bad2 %.1f %%、でたらめな画素 %.1f %%。NCC は OpenCV と位置が全点一致。"
                % (bad_lp, bad_rn))

    figs.save_table(
        "classes", ["区分", "画素 [%]", "ms bad2 [%]", "ms 無効 [%]", "SGBM bad2 [%]", "SGBM 無効 [%]"],
        [[r[0], "%.1f" % r[1], "%.2f" % r[2]["bad"], "%.1f" % (100 - r[2]["density"]), "%.2f" % r[3]["bad"],
          "%.1f" % (100 - r[3]["density"])] for r in cls_rows],
        title="区分ごとの誤りと無効(motorcycle)", caption="遮蔽は真値から幾何で数えた。")
    figs.save_table(
        "middeval3", ["場面", "bad2 有効", "密度", "無効も誤り(nocc)", "SGBM bad2", "SGBM 密度"],
        [[r[0], "%.2f" % r[2], "%.1f" % r[3], "%.2f" % r[4], "%.2f" % r[6], "%.1f" % r[7]] for r in mrows],
        title="MiddEval3 訓練 15 場面(1/4、nocc)", caption="同じ探索範囲・窓・左右一致の OpenCV SGBM と同じ画素で採点。")

    print("\n所見")
    print("  * 有効画素の bad2 %.2f %%・密度 %.1f %%(SGBM %.2f %% / %.1f %%)。無効を誤りに数えると %.2f %%。"
          % (s_ms["bad"], s_ms["density"], s_cv["bad"], s_cv["density"], s_ms["bad_all"]))
    print("  * 遮蔽は %.0f %% が無効に落ち、段差の近くと見え方が変わる面は誤りとして残る(bad2 %.1f / %.1f %%)。"
          % (100 - by["遮蔽"][2]["density"], by["段差の近く"][2]["bad"], by["見え方が変わる面"][2]["bad"]))
    print("  * 円の姿勢は中心 %.1f mm・法線 %.2f°(0.5 px の縁の食い違いで数度動く)。2 解は再投影で区別できない。"
          % (sols[best][0], sols[best][1]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()

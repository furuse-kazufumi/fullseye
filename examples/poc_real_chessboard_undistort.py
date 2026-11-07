# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写の校正板 13 枚で、歪みの直し・写像の適用・平面への平行化を採点する(直線性と格子の間隔で)。

主役は 0.9.0 の後に入った op —— ``change_radial_distortion_image``(除算モデルの歪みを描き直す)、
``map_image``(逆写像表を適用する)、``rectify_to_world_plane``(平面 z=0 の正面図へ)。脇役に
``points_lepetit``。題材は OpenCV が配布する校正板の写真 13 枚(640x480、内角 9x6、
samples/data/left01〜14.jpg、left10 は配布元に無い)。

真値は外から持ってくる:

* 角の位置 —— OpenCV の ``findChessboardCorners`` + ``cornerSubPix``(外の検出器)。歪みを直した後の
  画像でも、同じ検出器で角を拾い直して採点する(op の出力を op の外で測る)。
* 内部パラメータと歪み —— OpenCV の ``calibrateCamera``(5 係数の Brown–Conrady)。Fullseye の
  ``camera_calibration_lm`` が同じ値を出すかも確かめる。
* 直線性 —— 板の 6 行・9 列の角は、歪みが無ければ直線に並ぶ(物理の拘束、Brown 1971 の plumb line)。
* 平行化 —— 板の角は 1 マス = 40 px の格子に正確に乗るはず(板の形が真値)。

章(数値はすべて実行時に印字する実測値):

1. 校正: ``camera_calibration_lm`` と OpenCV の ``calibrateCamera`` の内部パラメータ・歪み・再投影誤差。
2. 除算モデルの κ: 板の行と列が最もまっすぐになる κ を直線性だけで当てる(1 係数)。OpenCV の 5 係数で
   戻した角と直線性を比べ、板の写らない画像の隅で 2 つのモデルがどれだけ食い違うかも測る。
3. ``change_radial_distortion_image``: κ → 0 で描き直した 13 枚から角を拾い直し、直線性を OpenCV の
   ``undistort`` と比べる。κ を往復させた画像の差(補間の損)も測る。
4. ``map_image``: OpenCV の ``initUndistortRectifyMap`` の表をそのまま渡し、``remap`` と画素で比べる。
   順写像(``x_map`` / ``y_map``)を渡すと拒否することも確かめる。
5. ``rectify_to_world_plane``: 姿勢を Fullseye の ``solve_pnp`` で出し(OpenCV の ``solvePnP`` と照合)、
   1 マス 40 px の正面図へ。拾い直した角が格子からどれだけずれるか。
6. ``points_lepetit`` を板の角(X 字の角)に当てると外れることを数え、理由を式で示す。

CI(写真が無い)では取得せず、手元で測った記録値 ``RECORDED`` を印字して記録どうしの門を通す。

所見(2026-11-08 の実測):

* ``camera_calibration_lm`` は OpenCV の ``calibrateCamera`` と同じ値(内部パラメータの差 2.6e-7 px、
  歪み係数の差 4e-9、再投影 0.4087 px)。
* ★**1 係数の除算モデルで足りる**: 直線性だけで当てた κ = −1.10e-6 /px² で、板の行と列の直線性は
  0.655 → 0.157 px。OpenCV の 5 係数で戻した 0.161 px と同等。ただし 2 つのモデルは板の写った範囲では
  中央 0.49 px しか違わないのに、**板が一度も写っていない画像の隅では 46.9 px 食い違う** —— どちらが
  正しいかはこの 13 枚からは言えない(外挿)。
* ``change_radial_distortion_image`` で描き直した 13 枚から OpenCV で角を拾い直すと、直線性は中央
  0.654 → 0.080 px(OpenCV の ``undistort`` は 0.089 px)。13 枚すべてで直り、13 枚とも OpenCV 以下。
* ``map_image`` は OpenCV の ``initUndistortRectifyMap`` の表で ``remap`` と最大 9.6e-8 の差(線形補間の
  一致)。順写像 ``x_map`` / ``y_map`` を渡すと拒否する。
* ``rectify_to_world_plane``: ``solve_pnp`` の姿勢は OpenCV ``solvePnP`` と回転 中央 0.12°、並進 0.21 %。
  正面図から拾い直した角は 1 マス 40 px の格子から RMS 中央 0.24 px、最悪の写真でも最大 3.0 px
  (0.075 マス)。隣の角との間隔は 39.80〜40.02 px。
* ★``points_lepetit`` は X 字の角に乗らない(1 px 以内 0 / 54)。応答の山は角から 2.6 px 脇に立ち、
  角の真上の応答は山の 11 %。★★さらに点の 90〜93 % は**まっすぐな縁の上**にある。1 本の縁で
  切り分けると、軸に沿った縁・ぼけの無い縁では 0 点なのに、**傾き 10°・ぼけ 0.7 px の縁で 100 px
  あたり 16 点**漏れる —— 直線の上の画素を落とす検査が、傾いてぼけた縁で効かない(記録した穴)。

EXTEND: 自前の板に差し替えるなら、``PATTERN``(内角の数)と写真の置き場(``FULLSEYE_OPENCV_CHESSBOARD_DATA``)
を変える。角の検出器は外のもの(OpenCV)を使っている —— Fullseye の op だけで閉じた採点にすると、
検出と採点の癖が同じ向きにそろって見えなくなる。

出典表示: OpenCV samples/data left01〜14.jpg、Apache License 2.0
(https://github.com/opencv/opencv の LICENSE、コミット 9d4808bef88a7aacbb360732303d42b279ebb6b5)。
取得は ``py -3.11 tools/fetch_stereoreal_data.py chessboard``(repo 外、SHA-256 固定)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import fetch_stereoreal_data as boarddata  # noqa: E402
import mvimage  # noqa: E402
import realdata  # noqa: E402

LG = fs.ledger

#: 板の内角(列 9 x 行 6)。
PATTERN = (9, 6)
#: 平行化の 1 マスの画素数と、出力の外周の余白(マス)。
SQUARE_PX = 40.0
MARGIN_SQ = 1.0
#: cornerSubPix の窓と止め方(OpenCV の校正の例と同じ値)。
SUBPIX_WIN = (11, 11)

#: CI(写真が無い)で印字する、手元で測った値(2026-11-08、``measure`` の返り値を ``to_plain`` で書き写した)。
#: 写真があれば測り直し、同じ形で印字する。
RECORDED = {'n_images': 13,
 'shape': [480, 640],
 'calib': {'fx': 536.073453,
           'fy': 536.016363,
           'cx': 342.370468,
           'cy': 235.536871,
           'dist': [-0.26509, -0.046742, 0.001833, -0.000315, 0.252312],
           'rms_cv': 0.408695,
           'rms_lm': 0.408695,
           'dK': 0.0,
           'dD': 0.0,
           'sec': 0.096533},
 'kappa': {'kappa': -1e-06,
           'line_k': 0.157204,
           'line_0': 0.655425,
           'line_cv': 0.160575,
           'gap_in_med': 0.487417,
           'gap_in_max': 4.200753,
           'gap_out_max': 46.939426,
           'frac_in': 0.559115},
 'change': {'before': [0.459274,
                       0.700001,
                       0.874848,
                       0.694896,
                       0.862581,
                       0.788187,
                       0.451445,
                       0.653632,
                       0.514098,
                       0.507516,
                       0.754829,
                       0.464504,
                       0.575913],
            'fs': [0.087369,
                   0.235031,
                   0.080132,
                   0.080094,
                   0.078244,
                   0.074265,
                   0.054546,
                   0.123497,
                   0.126102,
                   0.060018,
                   0.093597,
                   0.097071,
                   0.068624],
            'cv': [0.088171,
                   0.343096,
                   0.081126,
                   0.089702,
                   0.079531,
                   0.077553,
                   0.068802,
                   0.132095,
                   0.148243,
                   0.083018,
                   0.106259,
                   0.1098,
                   0.089001],
            'sec': 0.057124,
            'roundtrip_mean': 0.007297,
            'roundtrip_p99': 0.060604},
 'map_image': {'max_diff': 0.0, 'refused_forward': True},
 'rectify': [{'rot': 0.088917,
              'dt': 0.032732,
              'tnorm': 16.847185,
              'pnp_rms': 0.19565,
              'err_rms': 0.241053,
              'err_max': 0.454705,
              'sp_mean': 40.006274,
              'sp_cv': 0.005546},
             {'rot': 0.103383,
              'dt': 0.028172,
              'tnorm': 14.72596,
              'pnp_rms': 1.339843,
              'err_rms': 1.372145,
              'err_max': 2.997776,
              'sp_mean': 39.796668,
              'sp_cv': 0.00734},
             {'rot': 0.163791,
              'dt': 0.028146,
              'tnorm': 13.443222,
              'pnp_rms': 0.257506,
              'err_rms': 0.229269,
              'err_max': 0.478658,
              'sp_mean': 40.003825,
              'sp_cv': 0.003311},
             {'rot': 0.165927,
              'dt': 0.031988,
              'tnorm': 14.071177,
              'pnp_rms': 0.241571,
              'err_rms': 0.239251,
              'err_max': 0.408779,
              'sp_mean': 40.00707,
              'sp_cv': 0.004254},
             {'rot': 0.078545,
              'dt': 0.032416,
              'tnorm': 13.703697,
              'pnp_rms': 0.23126,
              'err_rms': 0.229526,
              'err_max': 0.512659,
              'sp_mean': 39.990521,
              'sp_cv': 0.004384},
             {'rot': 0.225397,
              'dt': 0.069315,
              'tnorm': 15.259682,
              'pnp_rms': 0.214317,
              'err_rms': 0.25101,
              'err_max': 0.560918,
              'sp_mean': 40.017586,
              'sp_cv': 0.00466},
             {'rot': 0.323602,
              'dt': 0.030878,
              'tnorm': 15.861874,
              'pnp_rms': 0.237704,
              'err_rms': 0.244774,
              'err_max': 0.540518,
              'sp_mean': 39.986573,
              'sp_cv': 0.004711},
             {'rot': 0.129356,
              'dt': 0.034501,
              'tnorm': 13.523466,
              'pnp_rms': 0.249933,
              'err_rms': 0.253963,
              'err_max': 0.468661,
              'sp_mean': 39.982539,
              'sp_cv': 0.004653},
             {'rot': 0.051737,
              'dt': 0.024514,
              'tnorm': 11.897228,
              'pnp_rms': 0.344325,
              'err_rms': 0.321322,
              'err_max': 0.935936,
              'sp_mean': 39.978432,
              'sp_cv': 0.004657},
             {'rot': 0.107051,
              'dt': 0.026741,
              'tnorm': 14.358635,
              'pnp_rms': 0.186712,
              'err_rms': 0.205542,
              'err_max': 0.374119,
              'sp_mean': 40.01078,
              'sp_cv': 0.004027},
             {'rot': 0.122074,
              'dt': 0.033737,
              'tnorm': 13.679955,
              'pnp_rms': 0.210725,
              'err_rms': 0.223677,
              'err_max': 0.464912,
              'sp_mean': 39.987672,
              'sp_cv': 0.004909},
             {'rot': 0.101267,
              'dt': 0.020184,
              'tnorm': 12.302885,
              'pnp_rms': 0.513332,
              'err_rms': 0.460529,
              'err_max': 1.127071,
              'sp_mean': 39.950885,
              'sp_cv': 0.004939},
             {'rot': 0.148713,
              'dt': 0.020321,
              'tnorm': 13.350593,
              'pnp_rms': 0.193365,
              'err_rms': 0.20502,
              'err_max': 0.397617,
              'sp_mean': 40.013767,
              'sp_cv': 0.003913}],
 'rectify_shape': [281, 401],
 'lepetit': {'per_image': [[1191, 0, 2.475207],
                           [1500, 0, 2.55393],
                           [1521, 0, 2.604934],
                           [1023, 0, 2.488934],
                           [1512, 0, 2.486896],
                           [1463, 0, 2.573983],
                           [1492, 0, 2.48273],
                           [1550, 0, 2.402179],
                           [1462, 0, 2.562038],
                           [1495, 0, 2.498954],
                           [1206, 0, 2.418765],
                           [1470, 0, 2.369584],
                           [1556, 0, 2.586085]],
             'on_edge': [0.903442,
                         0.926,
                         0.923734,
                         0.896383,
                         0.919974,
                         0.913876,
                         0.909517,
                         0.915484,
                         0.916553,
                         0.913043,
                         0.906302,
                         0.920408,
                         0.923522],
             'peak_offset_med': 2.596023,
             'at_corner_over_peak_med': 0.108085}}

SOURCE = ("OpenCV samples/data left01-14.jpg (Apache License 2.0, https://github.com/opencv/opencv, "
          "commit 9d4808bef88a7aacbb360732303d42b279ebb6b5)")


class GateError(AssertionError):
    """門を通らなかった。"""


def _require_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise SystemExit("参照実装 OpenCV が無い: `pip install -e .[opencv]` で入れる(%s)" % exc) from exc
    return cv2


def board_points():
    """板の角の世界座標 (54, 3)。単位は 1 マス、行が先(OpenCV の並びと同じ: x が速く回る)。"""
    obj = np.zeros((PATTERN[0] * PATTERN[1], 3))
    obj[:, :2] = np.mgrid[0:PATTERN[0], 0:PATTERN[1]].T.reshape(-1, 2)
    return obj


def detect(cv2, gray01):
    """OpenCV で角を拾う(外の検出器)。見つからなければ None。返りは (54, 2) の (x, y)。"""
    u8 = np.clip(np.rint(np.asarray(gray01) * 255.0), 0, 255).astype(np.uint8)
    ok, c = cv2.findChessboardCorners(u8, PATTERN)
    if not ok:
        return None
    c = cv2.cornerSubPix(u8, c, SUBPIX_WIN, (-1, -1),
                         (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3))
    return c.reshape(-1, 2).astype(np.float64)


def line_residuals(xy):
    """6 行・9 列それぞれに直線を当てた垂直距離の RMS を、線ごとに返す(px)。"""
    g = np.asarray(xy, np.float64).reshape(PATTERN[1], PATTERN[0], 2)
    out = []
    for lines in (g, g.transpose(1, 0, 2)):
        for ln in lines:
            _, S, _ = np.linalg.svd(ln - ln.mean(0))
            out.append(S[1] / np.sqrt(len(ln)))
    return np.array(out)


def straightness(xy):
    """直線性 = 全 15 本の線の垂直距離の RMS(px)。"""
    r = line_residuals(xy)
    return float(np.sqrt(np.mean(r * r)))


def fit_kappa_plumb(corners, cx, cy):
    """除算モデルの κ を、戻した角の行と列が最もまっすぐになるように当てる(1 変数の黄金分割)。"""
    def cost(k):
        tot = []
        for c in corners:
            ux, uy = mvimage.undistort_division(c[:, 0] - cx, c[:, 1] - cy, k)
            tot.append(line_residuals(np.c_[ux, uy]))
        t = np.concatenate(tot)
        return float(np.sqrt(np.mean(t * t)))

    lo, hi = -5e-6, 5e-6
    g = (np.sqrt(5.0) - 1.0) / 2.0
    a, b = hi - g * (hi - lo), lo + g * (hi - lo)
    fa, fb = cost(a), cost(b)
    for _ in range(80):
        if fa < fb:
            hi, b, fb = b, a, fa
            a = hi - g * (hi - lo)
            fa = cost(a)
        else:
            lo, a, fa = a, b, fb
            b = lo + g * (hi - lo)
            fb = cost(b)
    k = 0.5 * (lo + hi)
    return k, cost(k), cost(0.0)


def lepetit_response(g, radius):
    """``points_lepetit`` と同じ応答(円周の向かい合う 2 点の 2 階差分の和の絶対値 / 2m)を全画素で。

    棄却(直線の上の画素を落とす)は掛けない —— 山の位置だけを見るため。
    """
    drs, dcs = mvimage._circle_offsets(radius)
    H, W = g.shape
    R = radius
    c = g[R:H - R, R:W - R]
    lap = np.zeros_like(c)
    for a, b in zip(drs, dcs):
        lap += g[R + a:H - R + a, R + b:W - R + b] + g[R - a:H - R - a, R - b:W - R - b] - 2.0 * c
    out = np.zeros((H, W))
    out[R:H - R, R:W - R] = np.abs(lap) / (2.0 * len(drs))
    return out


def rot_angle_deg(Ra, Rb):
    c = (np.trace(Ra.T @ Rb) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def draw_marks(gray, xy, col, r=3):
    im = Image.fromarray(np.clip(np.rint(np.asarray(gray) * 255), 0, 255).astype(np.uint8)).convert("RGB")
    dr = ImageDraw.Draw(im)
    for x, y in xy:
        dr.ellipse([x - r, y - r, x + r, y + r], outline=col, width=1)
    return np.asarray(im).astype(np.float64) / 255.0


def draw_lines(rgb, xy, col):
    """角の 1 行目と 1 列目の両端を結ぶ直線(曲がりが目で見える)。"""
    im = Image.fromarray(np.clip(np.rint(rgb * 255), 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    g = np.asarray(xy).reshape(PATTERN[1], PATTERN[0], 2)
    for ln in (g[0], g[-1], g[:, 0], g[:, -1]):
        dr.line([tuple(ln[0]), tuple(ln[-1])], fill=col, width=1)
    return np.asarray(im).astype(np.float64) / 255.0


# --------------------------------------------------------------------------- #
def measure(cv2, paths):
    """写真があるときの全章。印字しながら、記録値と同じ形の dict を返す。"""
    names = sorted(paths)
    ims = []
    for nm in names:
        ims.append(np.asarray(Image.open(paths[nm]).convert("L"), np.float64) / 255.0)
    realdata.mark_read("opencv-samples:chessboard-left")
    H, W = ims[0].shape
    corners = [detect(cv2, g) for g in ims]
    if any(c is None for c in corners):
        raise GateError("OpenCV が角を拾えなかった写真がある")
    obj = board_points()
    rec = {"n_images": len(ims), "shape": [H, W]}

    # --- 1 校正 ---------------------------------------------------------------- #
    rms_cv, K, dist, _rv, _tv = cv2.calibrateCamera([obj.astype(np.float32)] * len(ims),
                                                     [c.astype(np.float32) for c in corners], (W, H), None, None)
    t = time.perf_counter()
    lm = LG.camera_calibration_lm(obj[:, :2], [c[:, ::-1] for c in corners], image_shape=(H, W))
    t_lm = time.perf_counter() - t
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    dK = max(abs(lm["fx"] - fx), abs(lm["fy"] - fy), abs(lm["cx"] - cx), abs(lm["cy"] - cy))
    dD = float(np.abs(np.asarray(lm["dist"]) - dist.ravel()).max())
    rec["calib"] = dict(fx=fx, fy=fy, cx=cx, cy=cy, dist=[float(x) for x in dist.ravel()], rms_cv=float(rms_cv),
                        rms_lm=float(lm["reproj_rms"]), dK=float(dK), dD=dD, sec=t_lm)

    # --- 2 κ ------------------------------------------------------------------- #
    kappa, line_k, line_0 = fit_kappa_plumb(corners, cx, cy)
    cv_lines = []
    for c in corners:
        u = cv2.undistortPoints(c.reshape(-1, 1, 2), K, dist, P=K).reshape(-1, 2)
        cv_lines.append(line_residuals(u))
    cv_line = float(np.sqrt(np.mean(np.concatenate(cv_lines) ** 2)))
    # 2 つのモデルの食い違い: 板の写った範囲(全写真の角の外接矩形)と画像の隅
    yy, xx = np.mgrid[0:H:4, 0:W:4]
    pix = np.c_[xx.ravel(), yy.ravel()].astype(np.float64)
    und_cv = cv2.undistortPoints(pix.reshape(-1, 1, 2), K, dist, P=K).reshape(-1, 2)
    ux, uy = mvimage.undistort_division(pix[:, 0] - cx, pix[:, 1] - cy, kappa)
    gap = np.hypot(ux + cx - und_cv[:, 0], uy + cy - und_cv[:, 1])
    allc = np.concatenate(corners)
    inside = ((pix[:, 0] >= allc[:, 0].min()) & (pix[:, 0] <= allc[:, 0].max())
              & (pix[:, 1] >= allc[:, 1].min()) & (pix[:, 1] <= allc[:, 1].max()))
    rec["kappa"] = dict(kappa=float(kappa), line_k=line_k, line_0=line_0, line_cv=cv_line,
                        gap_in_med=float(np.median(gap[inside])), gap_in_max=float(gap[inside].max()),
                        gap_out_max=float(gap[~inside].max()), frac_in=float(inside.mean()))

    # --- 3 change_radial_distortion_image ---------------------------------------- #
    cam_in = {"fx": fx, "fy": fy, "cx": cx, "cy": cy, "kappa": kappa}
    cam_out = {"fx": fx, "fy": fy, "cx": cx, "cy": cy, "kappa": 0.0}
    per = []
    t = time.perf_counter()
    und_imgs = []
    for g, c in zip(ims, corners):
        u = np.asarray(LG.change_radial_distortion_image(g, cam_in, cam_out))
        und_imgs.append(u)
        c_fs = detect(cv2, u)
        c_cv = detect(cv2, cv2.undistort(g.astype(np.float32), K, dist))
        if c_fs is None or c_cv is None:
            raise GateError("歪みを直した画像で角を拾えなかった")
        per.append((straightness(c), straightness(c_fs), straightness(c_cv)))
    t_ch = (time.perf_counter() - t) / len(ims)
    per = np.array(per)
    back = np.asarray(LG.change_radial_distortion_image(und_imgs[0], cam_out, cam_in))
    m0 = np.zeros((H, W), bool)
    c0 = corners[0]
    m0[int(c0[:, 1].min()):int(c0[:, 1].max()) + 1, int(c0[:, 0].min()):int(c0[:, 0].max()) + 1] = True
    rt = np.abs(back - ims[0])[m0]
    rec["change"] = dict(before=[float(x) for x in per[:, 0]], fs=[float(x) for x in per[:, 1]],
                         cv=[float(x) for x in per[:, 2]], sec=t_ch,
                         roundtrip_mean=float(rt.mean()), roundtrip_p99=float(np.quantile(rt, 0.99)))

    # --- 4 map_image ------------------------------------------------------------- #
    m1, m2 = cv2.initUndistortRectifyMap(K, dist, None, K, (W, H), cv2.CV_32FC1)
    diffs = []
    for g in ims:
        a = np.asarray(LG.map_image(g, {"row_map": m2.astype(np.float64), "col_map": m1.astype(np.float64)}))
        b = cv2.remap(g.astype(np.float32), m1, m2, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        diffs.append(float(np.abs(a - b)[2:-2, 2:-2].max()))
    try:
        LG.map_image(ims[0], {"x_map": m1, "y_map": m2})
        refused = False
    except ValueError:
        refused = True
    rec["map_image"] = dict(max_diff=max(diffs), refused_forward=refused)

    # --- 5 rectify_to_world_plane ----------------------------------------------- #
    Kfs = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1.0]])
    rows5 = []
    nx, ny = PATTERN[0] - 1 + 2 * MARGIN_SQ, PATTERN[1] - 1 + 2 * MARGIN_SQ
    wout, hout = int(round(nx * SQUARE_PX)) + 1, int(round(ny * SQUARE_PX)) + 1
    expect = (board_points()[:, :2] + MARGIN_SQ) * SQUARE_PX
    rect_imgs = []
    for g, c in zip(ims, corners):
        ux, uy = mvimage.undistort_division(c[:, 0] - cx, c[:, 1] - cy, kappa)
        uv = np.c_[ux + cx, uy + cy]
        Rf, tf, rms_pnp = fs.solve_pnp(obj, uv, Kfs)
        ok_cv, rvec, tvec = cv2.solvePnP(obj, c, K, dist)
        Rc, _ = cv2.Rodrigues(rvec)
        T = np.eye(4)
        T[:3, :3], T[:3, 3] = Rf, np.ravel(tf)
        rect = np.asarray(LG.rectify_to_world_plane(g, cam_in, T, wout, hout, 1.0 / SQUARE_PX,
                                                    origin=(-MARGIN_SQ, -MARGIN_SQ)))
        rect_imgs.append(rect)
        cr = detect(cv2, rect)
        if cr is None:
            raise GateError("平行化した画像で角を拾えなかった")
        # 角の並びの向き(OpenCV は板の向きで始点を変えることがある)
        if np.linalg.norm(cr[0] - expect[0]) > np.linalg.norm(cr[0] - expect[-1]):
            cr = cr[::-1]
        err = np.hypot(*(cr - expect).T)
        sp_x = np.diff(cr.reshape(PATTERN[1], PATTERN[0], 2)[:, :, 0], axis=1).ravel()
        sp_y = np.diff(cr.reshape(PATTERN[1], PATTERN[0], 2)[:, :, 1], axis=0).ravel()
        sp = np.r_[sp_x, sp_y]
        rows5.append(dict(rot=rot_angle_deg(Rf, Rc), dt=float(np.linalg.norm(np.ravel(tf) - tvec.ravel())),
                          tnorm=float(np.linalg.norm(tvec)), pnp_rms=float(rms_pnp),
                          err_rms=float(np.sqrt(np.mean(err * err))), err_max=float(err.max()),
                          sp_mean=float(sp.mean()), sp_cv=float(sp.std() / sp.mean())))
    rec["rectify"] = rows5
    rec["rectify_shape"] = [hout, wout]

    # --- 6 points_lepetit ------------------------------------------------------- #
    hits = []
    on_edge = []
    for g, c in zip(ims, corners):
        P = np.asarray(LG.points_lepetit(g, radius=3, min_score=0.02))
        d = np.min(np.hypot(P[:, None, 0] - c[None, :, 1], P[:, None, 1] - c[None, :, 0]), axis=0)
        hits.append((int(len(P)), int((d < 1.0).sum()), float(np.median(d))))
        # 点がまっすぐな縁(OpenCV の Canny、50/150)の 2 px 以内で、どの角からも 4 px より遠い割合
        edges = cv2.Canny(np.clip(np.rint(g * 255), 0, 255).astype(np.uint8), 50, 150) > 0
        dist_e = ndimage.distance_transform_edt(~edges)
        de = dist_e[np.clip(np.rint(P[:, 0]).astype(int), 0, H - 1), np.clip(np.rint(P[:, 1]).astype(int), 0, W - 1)]
        dc = np.min(np.hypot(P[:, None, 0] - c[None, :, 1], P[:, None, 1] - c[None, :, 0]), axis=1)
        on_edge.append(float(np.mean((de <= 2.0) & (dc > 4.0))))
    # 応答(円周の 2 階差分の和の絶対値、op と同じ式)を全画素で作り、各角の周り 6 px で山がどこにあるか
    g = ims[0]
    resp = lepetit_response(g, 3)
    offs, ratio = [], []
    for (x, y) in corners[0]:
        r0, q0 = int(round(y)), int(round(x))
        win = resp[r0 - 6:r0 + 7, q0 - 6:q0 + 7]
        k = np.unravel_index(int(np.argmax(win)), win.shape)
        offs.append(float(np.hypot(k[0] - 6 + r0 - y, k[1] - 6 + q0 - x)))
        ratio.append(float(resp[r0, q0] / max(win.max(), 1e-12)))
    rec["lepetit"] = dict(per_image=hits, on_edge=on_edge, peak_offset_med=float(np.median(offs)),
                          at_corner_over_peak_med=float(np.median(ratio)))
    return rec, dict(ims=ims, corners=corners, und=und_imgs, rect=rect_imgs, K=K, dist=dist,
                     kappa=kappa, expect=expect)


def edge_probe():
    """1 本のまっすぐな縁(100x100、傾き 0° / 10°、ぼけ 0 / 0.7 px)で、points_lepetit が何点出すか。

    実写の板で点が縁に並んだ理由を、真値の分かる最小の絵で切り分ける(合成はこの 1 か所だけ)。
    """
    yy, xx = np.mgrid[0:100, 0:100].astype(np.float64)
    out = {}
    for ang in (0.0, 10.0):
        a = np.deg2rad(ang)
        step = (((xx - 50) * np.cos(a) + (yy - 50) * np.sin(a)) > 0).astype(np.float64)
        for sig in (0.0, 0.7):
            g = ndimage.gaussian_filter(step, sig) if sig else step
            out[(ang, sig)] = int(len(np.asarray(LG.points_lepetit(g, radius=3, min_score=0.02))))
    return out


def report(rec, recorded=False):
    """記録の形の dict を印字し、門を数える。"""
    tag = "(記録値)" if recorded else ""
    c = rec["calib"]
    print("1. 校正%s(写真 %d 枚、%dx%d、内角 %dx%d)" % (tag, rec["n_images"], rec["shape"][1], rec["shape"][0],
                                               PATTERN[0], PATTERN[1]))
    print("   OpenCV calibrateCamera: fx %.3f fy %.3f cx %.3f cy %.3f / k1 %.4f k2 %.4f p1 %.5f p2 %.5f k3 %.4f / "
          "再投影 %.4f px" % (c["fx"], c["fy"], c["cx"], c["cy"], *c["dist"], c["rms_cv"]))
    print("   camera_calibration_lm: 再投影 %.4f px、内部パラメータの最大差 %.2g px、歪み係数の最大差 %.2g"
          "(%.2f 秒)" % (c["rms_lm"], c["dK"], c["dD"], c["sec"]))
    k = rec["kappa"]
    print("\n2. 除算モデルの κ を直線性で当てる%s" % tag)
    print("   κ = %.4g /px²。直線性(15 本 x %d 枚の RMS): 直さない %.3f px → κ %.3f px  "
          "(OpenCV の 5 係数で戻すと %.3f px)" % (k["kappa"], rec["n_images"], k["line_0"], k["line_k"], k["line_cv"]))
    print("   2 つのモデルの食い違い: 板の写った範囲(画像の %.0f %%)で中央 %.2f px・最大 %.2f px、"
          "その外の隅で最大 %.1f px" % (100 * k["frac_in"], k["gap_in_med"], k["gap_in_max"], k["gap_out_max"]))
    ch = rec["change"]
    b, f_, v = (np.array(ch[x]) for x in ("before", "fs", "cv"))
    print("\n3. change_radial_distortion_image%s(κ → 0、%.2f 秒/枚)" % (tag, ch["sec"]))
    print("   拾い直した角の直線性(13 枚の中央): 元 %.3f px → Fullseye %.3f px / OpenCV undistort %.3f px"
          % (np.median(b), np.median(f_), np.median(v)))
    print("   13 枚すべてで元より直った: %s。Fullseye が OpenCV 以下だった写真 %d / %d"
          % ("はい" if bool((f_ < b).all()) else "いいえ", int((f_ <= v).sum()), len(f_)))
    print("   κ を往復させた画像の差(板の範囲、灰色 0..1): 平均 %.4f、99 %% 点 %.4f(線形補間 2 回の損)"
          % (ch["roundtrip_mean"], ch["roundtrip_p99"]))
    m = rec["map_image"]
    print("\n4. map_image%s: OpenCV の initUndistortRectifyMap の表で remap と最大差 %.2g(13 枚)、"
          "順写像 x_map/y_map の拒否 %s" % (tag, m["max_diff"], "した" if m["refused_forward"] else "しない"))
    r5 = rec["rectify"]
    rot = np.array([r["rot"] for r in r5])
    dt = np.array([r["dt"] / r["tnorm"] for r in r5])
    er = np.array([r["err_rms"] for r in r5])
    em = np.array([r["err_max"] for r in r5])
    sp = np.array([r["sp_mean"] for r in r5])
    cvs = np.array([r["sp_cv"] for r in r5])
    print("\n5. rectify_to_world_plane%s(1 マス %.0f px、出力 %dx%d)" % (tag, SQUARE_PX, rec["rectify_shape"][1],
                                                                 rec["rectify_shape"][0]))
    print("   姿勢: solve_pnp と OpenCV solvePnP の回転の差 中央 %.3f° 最大 %.3f°、並進の差 中央 %.2f %%"
          % (np.median(rot), rot.max(), 100 * np.median(dt)))
    print("   拾い直した角と格子のずれ: RMS 中央 %.2f px(最大の写真 %.2f px)、最大 %.2f px = %.3f マス"
          % (np.median(er), er.max(), em.max(), em.max() / SQUARE_PX))
    print("   隣の角との間隔: 平均 %.2f〜%.2f px(13 枚)、ばらつき(変動係数)中央 %.2f %%"
          % (sp.min(), sp.max(), 100 * np.median(cvs)))
    lp = rec["lepetit"]
    hits = np.array([h[1] for h in lp["per_image"]])
    npts = np.array([h[0] for h in lp["per_image"]])
    meds = np.array([h[2] for h in lp["per_image"]])
    print("\n6. points_lepetit を X 字の角に当てる%s" % tag)
    print("   検出 %d〜%d 点/枚のうち、板の角から 1 px 以内に来たのは 54 個中 %d〜%d 個(角からの距離の中央 %.2f px)"
          % (npts.min(), npts.max(), hits.min(), hits.max(), np.median(meds)))
    print("   応答(円周の 2 階差分の和)の山は角から中央 %.2f px 離れ、角の画素の応答は周りの山の %.0f %%"
          " —— 角の真上では明 2 象限と暗 2 象限がほぼ打ち消し、山は角の脇のマスの側に立つ"
          "(Lepetit 点は斑点の検出器で、X 字の角を位置決めする道具ではない)"
          % (lp["peak_offset_med"], 100 * lp["at_corner_over_peak_med"]))
    oe = np.array(lp["on_edge"])
    print("   ★点の %.0f〜%.0f %%(13 枚)は、まっすぐな縁の 2 px 以内でどの角からも 4 px より遠い所にある"
          " —— 直線の上の画素を落とす検査が、実写のぼけた縁では効いていない(記録した穴)"
          % (100 * oe.min(), 100 * oe.max()))
    probe = edge_probe()
    print("   切り分け(1 本の縁、100 px): 傾き 0°・ぼけ無し %d 点 / 傾き 0°・ぼけ 0.7 px %d 点 / "
          "傾き 10°・ぼけ無し %d 点 / 傾き 10°・ぼけ 0.7 px %d 点 —— 傾いてぼけた縁で棄却が漏れる"
          % (probe[(0.0, 0.0)], probe[(0.0, 0.7)], probe[(10.0, 0.0)], probe[(10.0, 0.7)]))

    gates = {
        "1 Fullseye の LM が OpenCV と同じ値": c["dK"] < 1e-3 and c["dD"] < 1e-5 and abs(c["rms_lm"] - c["rms_cv"]) < 1e-6,
        "2 κ で直線性が 3 倍以上よくなる": k["line_k"] < k["line_0"] / 3.0,
        "2 1 係数の κ が OpenCV 5 係数と同等(10 % 以内)": k["line_k"] < 1.1 * k["line_cv"],
        "2 板の外の隅でモデルが食い違う(外挿)": k["gap_out_max"] > 5.0 * k["gap_in_max"],
        "3 13 枚すべてで直る": bool((f_ < b).all()) and np.median(f_) < np.median(b) / 3.0,
        "3 OpenCV undistort と同程度(中央 1.5 倍以内)": np.median(f_) < 1.5 * np.median(v),
        "3 往復の損は小さい": ch["roundtrip_mean"] < 0.02,
        "4 remap と一致": m["max_diff"] < 1e-5 and m["refused_forward"],
        "5 姿勢が OpenCV と一致": np.median(rot) < 0.2 and np.median(dt) < 0.01,
        "5 格子に乗る": np.median(er) < 1.0 and em.max() < 3.0 and abs(np.median(sp) - SQUARE_PX) < 0.5,
        "6 X 字の角には当たらない": hits.max() <= 5 and lp["peak_offset_med"] > 1.5 and lp["at_corner_over_peak_med"] < 0.6,
        "6 記録した穴: 点の大半がまっすぐな縁に乗る": min(lp["on_edge"]) > 0.6,
        "6 切り分け: 傾いてぼけた縁でだけ漏れる": probe[(0.0, 0.0)] == 0 and probe[(0.0, 0.7)] == 0
                                       and probe[(10.0, 0.7)] >= 5,
    }
    print("\n門")
    for name, ok in gates.items():
        print("  [%s] %s" % ("OK" if ok else "NG", name))
    bad = [n for n, ok in gates.items() if not ok]
    if bad:
        raise GateError("門を通らなかった: %s" % bad)
    return gates


def to_plain(x):
    """記録用に numpy の値を素の float / int / list にする。"""
    if isinstance(x, dict):
        return {k: to_plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [to_plain(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return round(float(x), 6)
    if isinstance(x, (np.integer, int)) and not isinstance(x, bool):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def main() -> None:
    t0 = time.perf_counter()
    cv2 = _require_cv2()
    paths = boarddata.files("chessboard", required=False)
    if paths is None:
        print("校正板の写真が手元に無い(py -3.11 tools/fetch_stereoreal_data.py chessboard で取得)。"
              "記録値を印字する。\n")
        if RECORDED is None:
            raise GateError("記録値が無い")
        report(RECORDED, recorded=True)
        print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
        print("\nPASS")
        return
    rec, art = measure(cv2, paths)
    report(rec)
    print("\n  RECORDED = %r" % (to_plain(rec),))

    # --- 図 ---------------------------------------------------------------- #
    i = int(np.argmax(rec["change"]["before"]))       # いちばん曲がって写った写真
    g, c = art["ims"][i], art["corners"][i]
    cu = detect(cv2, art["und"][i])
    before = draw_lines(draw_marks(g, c, (0, 114, 178)), c, (213, 94, 0))
    after = draw_lines(draw_marks(art["und"][i], cu, (0, 114, 178)), cu, (213, 94, 0))
    rect = art["rect"][i]
    cr = detect(cv2, rect)
    rect_rgb = draw_marks(rect, art["expect"], (213, 94, 0), r=5)
    im = Image.fromarray(np.clip(np.rint(rect_rgb * 255), 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for x, y in cr:
        dr.ellipse([x - 2, y - 2, x + 2, y + 2], outline=(0, 114, 178), width=1)
    rect_rgb = np.asarray(im).astype(np.float64) / 255.0
    pad = np.zeros_like(before)
    hh, ww = rect_rgb.shape[:2]
    oy, ox = (pad.shape[0] - hh) // 2, (pad.shape[1] - ww) // 2
    pad[oy:oy + hh, ox:ox + ww] = rect_rgb
    r5 = rec["rectify"][i]
    figs.save_grid(
        "board", [before, after, pad, art["und"][i] - g],
        ["元の写真: 青 = OpenCV の角、橙 = 端の角を結ぶ直線",
         "change_radial_distortion_image(κ → 0)",
         "rectify_to_world_plane: 橙 = 1 マス 40 px の格子、青 = 拾い直した角",
         "直した後 − 元(画像の隅ほど大きく動く)"],
        signed=[False, False, False, True],
        title="実写の校正板を直す —— 曲がった縁がまっすぐに、板が正面図に", ncols=2,
        caption="%s: 直線性 %.3f → %.3f px。正面図の角と格子のずれ RMS %.2f px。"
                % (sorted(paths)[i], straightness(c), straightness(cu), r5["err_rms"]))
    ch = rec["change"]
    figs.save_table(
        "per_image", ["写真", "元 [px]", "Fullseye [px]", "OpenCV [px]", "正面図のずれ RMS [px]", "姿勢の差 [°]"],
        [[nm, "%.3f" % b_, "%.3f" % f_, "%.3f" % v_, "%.2f" % r["err_rms"], "%.3f" % r["rot"]]
         for nm, b_, f_, v_, r in zip(sorted(paths), ch["before"], ch["fs"], ch["cv"], rec["rectify"])],
        title="写真ごとの直線性と正面図のずれ",
        caption="直線性 = 角の 6 行・9 列に当てた直線からの垂直距離の RMS。")
    lp = np.asarray(LG.points_lepetit(g, radius=3, min_score=0.02))
    lp_rgb = draw_marks(g, c, (0, 114, 178), r=4)
    im = Image.fromarray(np.clip(np.rint(lp_rgb * 255), 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for y, x in lp:
        dr.rectangle([x - 1, y - 1, x + 1, y + 1], outline=(213, 94, 0))
    figs.save_grid(
        "lepetit", [np.asarray(im).astype(np.float64) / 255.0],
        ["青丸 = 板の角(OpenCV)、橙 = points_lepetit"],
        title="Lepetit 点は X 字の角に乗らず、まっすぐな縁に並ぶ", ncols=1,
        caption="応答の山は角の真上でなく脇に立つ。点の %.0f %% はまっすぐな縁の上(直線の棄却が効かない)。"
                % (100 * rec["lepetit"]["on_edge"][i]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""手持ちで撮った書類をまっすぐに戻す —— 台形補正と影除去を、真値と突き合わせて測る。

EXTEND: 実写真に差し替えるには ``render_camera`` の戻り値の代わりに
``fs.read_image("photo.jpg")`` を入れ、``main`` の各節が受け取る ``cam`` を
それに置き換える。真値が無くなるので測れるものが変わる ——
(a) 4 隅の画素誤差は測れない(真の隅を知らないので)、
(b) **罫線の残留曲がり**と**行の高さの均一性**は測れる(補正後の画像だけで
決まる量なので)。実写真では紙の反り・レンズ歪みが乗るため、この PoC の
第 6 節(レンズ歪み)の数字が実写真での下限の目安になる。撮るときは
**書類の 4 隅を全部枠に入れる** —— 第 5 節のとおり、隅が枠の外に出ると
誤差は一気に跳ね上がる(実測値は第 5 節の表を見ること)。

この PoC が示すこと:

1. **真値は自分で作れる** —— 平らな書類を作り、既知の姿勢で投影し(既知の
   ホモグラフィ)、既知の照明ムラと影を掛け、雑音を足す。戻して元と比べれば
   「それらしい絵」ではなく画素単位の数字が出る。
2. **ゼロ点を置かないと良し悪しが言えない** —— 上限(真の 4 隅を手で与える
   理想の補正)と下限(何もしない = 相似で位置と大きさだけ合わせる)を並べ、
   推定がその間のどこにいるかを比で出す。
3. **影除去は必ず何かを壊す** —— 照明を平らにするほど、薄い文字と図の階調が
   失われる。良くなる面(平坦度)と壊れる面(薄字の残存・階調の相関)を
   同じ表に並べる。
4. **壊れる条件は連続ではなく崖** —— 傾き・枠外・背景の近さ・影の強さの 4 軸で、
   どこから崩れるかを数字で出す。

★ この PoC が出した道具の穴(op 本体は直していない):

(a) **任意のホモグラフィで画像を歪ませる op が無い**。``fs.op.projective_trans_image``
    は台形歪み 1 パターンを ``a``/``b`` で振るだけで、行列を渡せない
    (``backends_auto`` の実装が固定の 4 隅内寄せ)。台形補正はこの op の
    ど真ん中の用途なのに、**この PoC の中心にある「既知の H で歪ませる /
    H で戻す」が既存 op では書けず**、双一次サンプラを自前で書いた。
(b) **``calib`` と ``tools_geom`` が入口から見えない**。``calib.vector_to_hom_mat2d``
    も ``tools_geom.hough_lines_dir`` も ``fullseye.<名前>`` にも
    ``fullseye.ledger.<名前>`` にも出ない(実測: ``'vector_to_hom_mat2d' in dir(fs)``
    は False、``in dir(fs.ledger)`` も False)。``import calib`` と直接書くしかない。
(c) ★**``vector_to_hom_mat2d`` が 2 つある**。``calib`` 版は射影(DLT、点は (x,y))、
    ``fit_transform`` 版は**アフィン**(最小二乗、docstring は (row,col))。
    名前が同じで**モデルが違う**。取り違えても例外は出ず、台形が残ったまま
    もっともらしい絵が返る —— 第 3 節でその差を数字にした(4 隅 RMS で 40 倍)。
(d) **局所窓の op が小さい窓にしか届かない**。``mean_image``/``gray_tophat``/
    ``median_rect`` は窓 3〜9 px、``var_threshold``/``xsk3_threshold_local_median``
    は 3〜15 px、``gauss_filter`` はシグマ 0.3〜3.0、``illuminate`` はシグマ 3〜15。
    書類の照明ムラを取るには**画像の 1/10 程度(この PoC で 61 px)の窓**が要るが、
    ``a``/``b`` が [0,1] である以上そこへ届かない。第 4 節で「届く範囲で最善」と
    「61 px」を並べ、平坦度で 3 倍の差が出ることを示した。
    (周波数側の ``dc_homomorphic`` だけは正規化カットオフなので大スケールに届く。)
"""
from __future__ import annotations

import math
import time

import numpy as np

import fullseye as fs
import calib
import fit_transform
import tools_geom

RNG_SEED = 20260906

DOC_H, DOC_W = 560, 400          # 平らな書類(真値)の画素寸法
CAM_H, CAM_W = 720, 540          # 撮影画像の画素寸法
PAPER = 0.93                     # 紙の明るさ
INK, FAINT, RULE = 0.12, 0.68, 0.55
BAND_ROWS = tuple(50 + 55 * i for i in range(6))     # 文字行の上端
BAND_H = 12
RULE_OFFSET = 24                                     # 行の下 24 px に罫線
TEXT_C0, TEXT_C1 = 40, 360
RAMP_R0, RAMP_R1, RAMP_C0, RAMP_C1 = 390, 470, 60, 340
FAINT_BANDS = (4, 5)                                 # この 2 行だけ薄い文字


# ─────────────────────────────────────────────────────────────────────────────
# 真値の生成
# ─────────────────────────────────────────────────────────────────────────────
def make_document():
    """平らな書類。文字行を模した矩形の並び + 罫線 + 階調の図。"""
    rng = np.random.default_rng(RNG_SEED)
    doc = np.full((DOC_H, DOC_W), PAPER)
    for i, r0 in enumerate(BAND_ROWS):
        ink = FAINT if i in FAINT_BANDS else INK
        c = TEXT_C0
        while c < TEXT_C1 - 12:
            w = int(rng.integers(14, 46))
            w = min(w, TEXT_C1 - c)
            doc[r0:r0 + BAND_H, c:c + w] = ink
            c += w + int(rng.integers(6, 14))
        doc[r0 + RULE_OFFSET, TEXT_C0:TEXT_C1] = RULE
    ramp = np.linspace(0.10, 0.95, RAMP_C1 - RAMP_C0)[None, :]
    doc[RAMP_R0:RAMP_R1, RAMP_C0:RAMP_C1] = np.repeat(ramp, RAMP_R1 - RAMP_R0, axis=0)
    return doc


def doc_corners_xy():
    """書類の 4 隅を (x=col, y=row) で。左上→右上→右下→左下(画面上で時計回り)。"""
    return np.array([[0.0, 0.0], [DOC_W - 1.0, 0.0],
                     [DOC_W - 1.0, DOC_H - 1.0], [0.0, DOC_H - 1.0]])


def camera_quad(tilt_deg=32.0, roll_deg=7.0, dist=0.36, shift=(0.0, 0.0), focal=900.0):
    """書類を 3D 平面として置き、既知の姿勢でピンホール投影した 4 隅 (u, v)。"""
    s = 0.0004                                        # m / 書類画素
    P = np.column_stack([(doc_corners_xy()[:, 0] - (DOC_W - 1) / 2) * s,
                         (doc_corners_xy()[:, 1] - (DOC_H - 1) / 2) * s,
                         np.zeros(4)])
    a, b = math.radians(tilt_deg), math.radians(roll_deg)
    Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    Rz = np.array([[math.cos(b), -math.sin(b), 0], [math.sin(b), math.cos(b), 0], [0, 0, 1]])
    R = Rx @ Rz
    t = np.array([shift[0], shift[1], dist])
    K = np.array([[focal, 0, (CAM_W - 1) / 2], [0, focal, (CAM_H - 1) / 2], [0, 0, 1.0]])
    uv, depth = fs.project_points(P, K, R, t)
    if np.any(depth <= 0):
        raise ValueError("書類がカメラの背後に回った")
    return np.asarray(uv, float)


def _bilinear(img, rows, cols, fill):
    """双一次補間。★ 任意行列の射影ワープ op が無いので自前(道具の穴 (a))。"""
    h, w = img.shape
    ok = (rows >= 0) & (rows <= h - 1) & (cols >= 0) & (cols <= w - 1)
    r = np.clip(rows, 0, h - 1); c = np.clip(cols, 0, w - 1)
    r0 = np.floor(r).astype(int); c0 = np.floor(c).astype(int)
    r1 = np.minimum(r0 + 1, h - 1); c1 = np.minimum(c0 + 1, w - 1)
    fr = r - r0; fc = c - c0
    out = ((1 - fr) * (1 - fc) * img[r0, c0] + (1 - fr) * fc * img[r0, c1]
           + fr * (1 - fc) * img[r1, c0] + fr * fc * img[r1, c1])
    return np.where(ok, out, fill)


def _undistort_uv(uv, kappa):
    """センサ画素 → 理想画素。r_ideal = r_sensor * (1 + kappa * (r/s)^2)。"""
    if kappa == 0.0:
        return uv
    cx, cy = (CAM_W - 1) / 2, (CAM_H - 1) / 2
    s = max(CAM_H, CAM_W) / 2
    d = uv - np.array([cx, cy])
    f = 1.0 + kappa * ((d[:, 0] ** 2 + d[:, 1] ** 2) / s ** 2)
    return np.column_stack([cx + d[:, 0] * f, cy + d[:, 1] * f])


def illumination_field(strength=0.30, shadow=0.22, edge=0.55, soft=45.0):
    """既知の照明ムラ: 左右の勾配 + 斜めの柔らかい影。"""
    rr, cc = np.mgrid[0:CAM_H, 0:CAM_W].astype(float)
    u = cc / (CAM_W - 1); v = rr / (CAM_H - 1)
    grad = 1.0 - strength * u + 0.18 * v
    line = (cc + 0.6 * rr) / (CAM_W + 0.6 * CAM_H)
    band = 1.0 / (1.0 + np.exp(-(line - edge) * (CAM_W / soft)))
    return grad * (1.0 - shadow * band)


def render_camera(doc, H, bg=0.30, illum=None, noise=0.006, kappa=0.0, seed=RNG_SEED):
    """書類 → 撮影画像。H は書類 (x,y) → 画像 (u,v) のホモグラフィ。"""
    rr, cc = np.mgrid[0:CAM_H, 0:CAM_W].astype(float)
    uv = np.column_stack([cc.ravel(), rr.ravel()])
    uv = _undistort_uv(uv, kappa)
    xy = calib.image_to_world_plane(uv, np.linalg.inv(H))      # 画像 → 書類平面
    x = xy[:, 0].reshape(CAM_H, CAM_W); y = xy[:, 1].reshape(CAM_H, CAM_W)
    rng = np.random.default_rng(seed)
    desk = bg + 0.02 * rng.standard_normal((CAM_H, CAM_W))
    img = _bilinear(doc, y, x, fill=0.0)
    inside = (x >= 0) & (x <= DOC_W - 1) & (y >= 0) & (y <= DOC_H - 1)
    img = np.where(inside, img, desk)
    if illum is None:
        illum = illumination_field()
    img = img * illum
    img = img + noise * rng.standard_normal(img.shape)
    return np.clip(img, 0.0, 1.0), inside


# ─────────────────────────────────────────────────────────────────────────────
# ページ検出(fullseye の op で)
# ─────────────────────────────────────────────────────────────────────────────
def page_mask(img):
    """紙は背景より明るい、を使って 2 値化 → 穴埋め → 最大成分。"""
    g = fs.op.gauss_filter(img, a=0.6)
    reg = fs.op.otsu(g)
    reg = fs.op.fill_holes(reg)
    reg = fs.op.opening_circle(reg, a=1.0)
    reg = fs.op.select_largest(reg)
    return np.asarray(reg > 0.5)


def boundary_points(mask, drop_frame=2):
    """輪郭画素の (x, y)。画像の枠に接する点は落とす(枠は紙の縁ではない)。"""
    bnd = fs.op.get_region_contour(mask.astype(float))
    ys, xs = np.nonzero(np.asarray(bnd) > 0.5)
    keep = ((ys >= drop_frame) & (ys < CAM_H - drop_frame)
            & (xs >= drop_frame) & (xs < CAM_W - drop_frame))
    return np.column_stack([xs[keep], ys[keep]]).astype(float)


def _initial_quad(pts):
    """最遠点の連鎖で 4 隅の粗い当たりを付ける。"""
    m = pts.mean(0)
    p0 = pts[np.argmax(((pts - m) ** 2).sum(1))]
    p1 = pts[np.argmax(((pts - p0) ** 2).sum(1))]
    d = p1 - p0; n = np.array([-d[1], d[0]]) / (np.hypot(*d) + 1e-12)
    side = (pts - p0) @ n
    p2 = pts[np.argmax(side)]; p3 = pts[np.argmin(side)]
    return order_corners(np.array([p0, p1, p2, p3]))


def order_corners(q):
    """左上→右上→右下→左下(画面上で時計回り)に並べ替える。"""
    q = np.asarray(q, float)
    m = q.mean(0)
    ang = np.arctan2(q[:, 1] - m[1], q[:, 0] - m[0])
    q = q[np.argsort(ang)]                                     # 画面上で時計回り
    start = int(np.argmin(q[:, 0] + q[:, 1]))
    return np.roll(q, -start, axis=0)


def _fit_line_tls(pts):
    """全最小二乗で直線を当て、両端の 2 点 (r0,c0,r1,c1) を返す。"""
    m = pts.mean(0)
    _, _, Vt = np.linalg.svd(pts - m)
    d = Vt[0]
    a = m - 400.0 * d; b = m + 400.0 * d
    return (a[1], a[0], b[1], b[0])                            # (row, col) x2


def corners_by_side_fit(pts, corner_gap=18.0):
    """辺ごとに直線を当て、隣り合う辺の交点を隅とする(枠外へも外挿できる)。"""
    quad = _initial_quad(pts)
    sides = [[] for _ in range(4)]
    for k in range(4):
        a, b = quad[k], quad[(k + 1) % 4]
        d = b - a; L = np.hypot(*d)
        if L < 1e-6:
            continue
        t = ((pts - a) @ d) / (L * L)
        proj = a + np.outer(t, d)
        dist = np.hypot(*(pts - proj).T)
        sel = (dist < 0.06 * L) & (t > corner_gap / L) & (t < 1 - corner_gap / L)
        sides[k] = pts[sel]
    lines = []
    for k in range(4):
        if len(sides[k]) < 12:
            return None
        lines.append(_fit_line_tls(sides[k]))
    out = []
    for k in range(4):
        p = tools_geom.intersection_lines(lines[k - 1], lines[k])
        if p is None:
            return None
        out.append([p[1], p[0]])                               # (row,col) → (x,y)
    return order_corners(np.array(out))


def corners_by_hough(mask, n_peaks=4):
    """方向つき Hough で 4 辺を拾い、交点を隅にする。"""
    m = mask.astype(float)
    ang = fs.op.sobel_dir(m) * 2.0 * np.pi - np.pi              # [0,1] → [-pi, pi]
    dir_row, dir_col = np.sin(ang), np.cos(ang)
    bnd = np.asarray(fs.op.get_region_contour(m)) > 0.5
    acc = tools_geom.hough_line_trans_dir(bnd, dir_row, dir_col, n_angle=540)
    rho_max = math.hypot(CAM_H, CAM_W)
    nr, na = acc.shape
    work = acc.copy()
    peaks = []
    for _ in range(n_peaks):
        i = int(np.argmax(work))
        ri, ai = divmod(i, na)
        if work[ri, ai] <= 0:
            break
        peaks.append((ri / (nr - 1) * 2 * rho_max - rho_max, ai / na * np.pi))
        r0, r1 = max(0, ri - 30), min(nr, ri + 31)
        a0, a1 = max(0, ai - 36), min(na, ai + 37)
        work[r0:r1, a0:a1] = 0.0
    if len(peaks) < 4:
        return None
    lines = []
    for rho, th in peaks:
        p = np.array([rho * math.sin(th), rho * math.cos(th)])  # (row, col)
        d = np.array([math.cos(th), -math.sin(th)])
        lines.append((p[0] - 800 * d[0], p[1] - 800 * d[1],
                      p[0] + 800 * d[0], p[1] + 800 * d[1]))
    thetas = np.array([t for _, t in peaks])
    horiz = [i for i in range(4) if math.sin(thetas[i]) ** 2 > 0.5]   # 法線が縦 = 横線
    vert = [i for i in range(4) if i not in horiz]
    if len(horiz) != 2 or len(vert) != 2:
        return None
    out = []
    for i in horiz:
        for j in vert:
            p = tools_geom.intersection_lines(lines[i], lines[j])
            if p is None:
                return None
            out.append([p[1], p[0]])
    return order_corners(np.array(out))


def corners_by_response(img, mask=None, radius=25):
    """corner_response の上位 4 点。mask を渡すと紙の輪郭だけを見る。"""
    src = mask.astype(float) if mask is not None else img
    resp = np.asarray(fs.op.corner_response(src))
    work = resp.copy()
    out = []
    for _ in range(4):
        i = int(np.argmax(work))
        r, c = divmod(i, CAM_W)
        out.append([float(c), float(r)])
        r0, r1 = max(0, r - radius), min(CAM_H, r + radius + 1)
        c0, c1 = max(0, c - radius), min(CAM_W, c + radius + 1)
        work[r0:r1, c0:c1] = -np.inf
    return order_corners(np.array(out))


# ─────────────────────────────────────────────────────────────────────────────
# 補正と計測
# ─────────────────────────────────────────────────────────────────────────────
def bg_divide(x, k):
    """局所平均で割って地を平らにする。

    ★ 窓 ``k`` は自前の積分画像で作っている —— ``fs.op`` の局所窓 op は
    ``mean_image``/``gray_tophat`` が 9 px、``var_threshold`` が 15 px までしか
    届かず、書類の照明ムラ(この PoC で必要なのは 61 px)に手が出ない(穴 (d))。
    """
    pad = k // 2
    xp = np.pad(x, pad, mode="reflect")
    cs = np.cumsum(np.cumsum(xp, axis=0), axis=1)
    cs = np.pad(cs, ((1, 0), (1, 0)))
    s = (cs[k:, k:] - cs[:-k, k:] - cs[k:, :-k] + cs[:-k, :-k]) / (k * k)
    return np.clip(x / np.maximum(s, 1e-6) * 0.9, 0.0, 1.0)


def rectify(cam, H):
    """H(書類 (x,y) → 画像 (u,v))を使って書類の枠へ戻す。"""
    rr, cc = np.mgrid[0:DOC_H, 0:DOC_W].astype(float)
    xy = np.column_stack([cc.ravel(), rr.ravel()])
    uv = calib.image_to_world_plane(xy, H)
    return _bilinear(cam, uv[:, 1].reshape(DOC_H, DOC_W),
                     uv[:, 0].reshape(DOC_H, DOC_W), fill=0.0)


def landmark_error(H_est, H_true, n=9):
    """書類全面の格子点が、補正後にどれだけ元の位置からずれるか(書類画素)。"""
    gy, gx = np.mgrid[0:n, 0:n].astype(float)
    p = np.column_stack([(gx.ravel() / (n - 1)) * (DOC_W - 1),
                         (gy.ravel() / (n - 1)) * (DOC_H - 1)])
    q = calib.image_to_world_plane(p, H_true)                  # 書類 → 画像
    back = calib.image_to_world_plane(q, np.linalg.inv(H_est))  # 画像 → 書類(推定)
    e = np.hypot(*(back - p).T)
    return float(np.sqrt(np.mean(e ** 2))), float(np.max(e))


def rule_bend(rect, half=8, contrast=0.06):
    """補正後の罫線の残留曲がり(直線を当てた残差の最大値、書類画素)。

    ★ この量は**射影の誤りを検出できない** —— ホモグラフィも相似もアフィンも
    直線を直線へ写すため。曲がるのはレンズ歪みのような非射影の成分だけ。
    窓の中に罫線が見つからない(補正が大きくずれている)場合は NaN を返す。
    """
    worst = 0.0
    found = False
    for r0 in (br + RULE_OFFSET for br in BAND_ROWS):
        cols = np.arange(TEXT_C0 + 10, TEXT_C1 - 10, 4)
        if r0 - half < 0 or r0 + half + 1 > rect.shape[0]:
            continue
        band = rect[r0 - half:r0 + half + 1, cols]
        rows = r0 - half + np.argmin(band, axis=0).astype(float)
        good = (np.median(band, axis=0) - band.min(axis=0)) > contrast
        if good.sum() < 0.6 * len(cols):
            continue
        A = np.column_stack([cols[good], np.ones(good.sum())])
        coef, *_ = np.linalg.lstsq(A, rows[good], rcond=None)
        worst = max(worst, float(np.max(np.abs(A @ coef - rows[good]))))
        found = True
    return worst if found else float("nan")


def band_heights(rect, dark=0.85, row_end=RAMP_R0 - 15):
    """補正後の「文字行の高さ」の並び(暗画素の行方向占有率から run を数える)。

    地を 61 px 窓で割ってから閾値を掛けるので、濃い字も薄い字も同じように
    数えられる。図(階調のランプ)は行を数える対象ではないので範囲から外す。
    """
    sub = bg_divide(rect, 61)[:row_end, TEXT_C0 + 10:TEXT_C1 - 10]
    frac = (sub < dark).mean(axis=1)
    on = frac > 0.20
    runs, start = [], None
    for i, v in enumerate(on):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= 4:
                runs.append((start, i - start))
            start = None
    if start is not None and len(on) - start >= 4:
        runs.append((start, len(on) - start))
    return [h for _, h in runs]


def corner_rms(est, truth):
    return float(np.sqrt(np.mean(np.sum((np.asarray(est) - np.asarray(truth)) ** 2, axis=1))))


# ─────────────────────────────────────────────────────────────────────────────
def main():
    t_start = time.perf_counter()
    doc = make_document()
    src = doc_corners_xy()
    quad = camera_quad()
    H_true = calib.vector_to_hom_mat2d(src, quad)
    cam, inside = render_camera(doc, H_true)

    print("=== 1. 真値 —— 平らな書類を既知の姿勢で撮る ===")
    print(f"  書類 {DOC_H}x{DOC_W} / 撮影 {CAM_H}x{CAM_W} / 紙の占有 {100 * inside.mean():.1f} %")
    print(f"  傾き 32 度・ひねり 7 度・距離 0.36 m・焦点 900 px")
    print(f"  真の 4 隅 (x,y): " + " ".join(f"({x:.1f},{y:.1f})" for x, y in quad))
    w_top = np.hypot(*(quad[1] - quad[0])); w_bot = np.hypot(*(quad[2] - quad[3]))
    print(f"  上辺 {w_top:.1f} px / 下辺 {w_bot:.1f} px → 台形の度合い {w_bot / w_top:.3f} 倍")
    il = illumination_field()
    print(f"  照明: 左右勾配 30 % + 斜めの影 22 %(紙にかかる係数 "
          f"{il[inside].min():.2f}〜{il[inside].max():.2f} = {il[inside].max() / il[inside].min():.2f} 倍)")
    print(f"  紙の地のいちばん暗いところ {PAPER * il[inside].min():.3f} / "
          f"机のいちばん明るいところ {0.30 * il[~inside].max():.3f}")
    print("  → 大域 2 値化が効くのはこの大小が保たれている間だけ(第 5 節でその崖を測る)。")

    print("\n=== 2. ページ検出 —— 3 つの推定器を同じ画像に当てる ===")
    mask = page_mask(cam)
    pts = boundary_points(mask)
    est_fit = corners_by_side_fit(pts)
    est_hough = corners_by_hough(mask)
    est_resp_img = corners_by_response(cam)
    est_resp_mask = corners_by_response(cam, mask=mask)
    iou = (mask & inside).sum() / (mask | inside).sum()
    print(f"  紙マスクの IoU {iou:.4f} / 輪郭点 {len(pts)} 個")
    print(f"  {'推定器':<26}{'4 隅 RMS [px]':>14}{'最悪隅 [px]':>12}")
    rows = [("輪郭を辺ごとに直線当て", est_fit), ("方向つき Hough", est_hough),
            ("corner_response(写真そのもの)", est_resp_img),
            ("corner_response(紙マスク)", est_resp_mask)]
    for name, e in rows:
        if e is None:
            print(f"  {name:<26}{'検出できず':>14}")
            continue
        d = np.hypot(*(e - quad).T)
        print(f"  {name:<26}{corner_rms(e, quad):>14.2f}{d.max():>12.2f}")
    print("  → corner_response は写真に当てると文字の角に食われる。同じ op でも")
    print("     紙マスクに当てれば効く —— 検出器の良し悪しではなく入力の問題。")

    print("\n=== 3. ゼロ点 —— 何もしない / 理想 / 推定 ===")
    H_ideal = calib.vector_to_hom_mat2d(src, quad)                  # 真の隅を手で与える
    H_est = calib.vector_to_hom_mat2d(src, est_fit)
    H_hough = calib.vector_to_hom_mat2d(src, est_hough) if est_hough is not None else None
    H_sim = fit_transform.vector_to_similarity(src, quad)           # 位置と大きさだけ
    H_aff = fit_transform.vector_to_hom_mat2d(src, quad)            # ★ 同名だがアフィン
    cases = [("何もしない(相似で合わせるだけ)", H_sim),
             ("アフィンまで(同名 op の取り違え)", H_aff),
             ("推定(輪郭の直線当て)", H_est)]
    if H_hough is not None:
        cases.append(("推定(方向つき Hough)", H_hough))
    cases.append(("理想(真の 4 隅を手で与える)", H_ideal))
    print(f"  {'補正':<28}{'格子 RMS [px]':>14}{'最悪 [px]':>11}{'罫線の曲がり':>13}{'行高 std/平均':>14}")
    ref_lo = ref_hi = None
    results = {}
    for name, H in cases:
        rms, mx = landmark_error(H, H_true)
        rect = rectify(cam, H)
        bend = rule_bend(rect)
        hs = band_heights(rect)
        cv = (np.std(hs) / np.mean(hs)) if len(hs) >= 3 else float("nan")
        results[name] = (rms, bend, cv, len(hs))
        print(f"  {name:<28}{rms:>14.3f}{mx:>11.3f}{bend:>13.2f}{cv:>14.3f}"
              f"   (行 {len(hs)} 本)")
        if name.startswith("何もしない"):
            ref_lo = rms
        if name.startswith("理想"):
            ref_hi = rms
    got = results["推定(輪郭の直線当て)"][0]
    print(f"  → ゼロ点比: 下限 {ref_lo:.3f} px / 上限 {ref_hi:.2e} px / 推定 {got:.3f} px")
    print(f"     下限からの改善 {100 * (1 - (got - ref_hi) / (ref_lo - ref_hi)):.2f} %"
          f"(1.0 = 理想と同じ、0.0 = 何もしないと同じ)")
    print(f"     ★ 同名 op の取り違え(アフィン)は {results['アフィンまで(同名 op の取り違え)'][0] / got:.0f} 倍悪い。")
    print("        例外は出ない —— 台形が残ったまま、それらしい絵が返る。")
    print("     ★ 「罫線の曲がり」列は幾何の誤りをほとんど検出できない —— 射影も")
    print("        アフィンも相似も直線を直線へ写すため。曲がりが意味を持つのは")
    print("        レンズ歪みのような非射影の成分があるときだけ(第 6 節)。")
    print("        誤りが素直に出るのは「行高 std/平均」の方(遠い行ほど縮む)。")

    print("\n=== 4. 影除去は何を壊すか ===")
    # 幾何は理想の補正で片付けてから、光の話だけを見る。照明は第 1 節より強くする
    # (勾配 50 % + 影 50 %)—— 弱い照明では手法の差が出ず、比較にならないため。
    cam_hard, _ = render_camera(doc, H_ideal,
                                illum=illumination_field(strength=0.50, shadow=0.50))
    rect_ideal = rectify(cam_hard, H_ideal)
    truth = doc
    inner = np.zeros_like(truth, bool)
    inner[12:-12, 12:-12] = True
    paper = (truth > 0.85) & inner                         # 紙の地(真値で定義)
    strong_ink = np.zeros_like(truth, bool)
    faint_ink = np.zeros_like(truth, bool)
    for i, r0 in enumerate(BAND_ROWS):
        band = np.zeros_like(truth, bool)
        band[r0:r0 + BAND_H, TEXT_C0:TEXT_C1] = True
        tgt = faint_ink if i in FAINT_BANDS else strong_ink
        tgt |= band & (truth < 0.85)
    ramp = np.zeros_like(truth, bool)
    ramp[RAMP_R0:RAMP_R1, RAMP_C0:RAMP_C1] = True

    def flatness(x):
        """紙の地の明るさのばらつき(小さいほど平ら)。"""
        return float(np.std(x[paper]))

    def ink_mask(x):
        """処理後の画像から「字」と判定される画素(大域 2 値化のあと)。"""
        return np.asarray(fs.op.otsu(x)) < 0.5

    def ramp_corr(x):
        """図の階調の順序が残っているか(真の傾斜との相関、1.0 = 無傷)。"""
        a = x[ramp].ravel(); b = truth[ramp].ravel()
        if np.std(a) < 1e-9:
            return 0.0
        return float(np.corrcoef(a, b)[0, 1])

    def ramp_range(x):
        """図に残っている振幅(真値との比、1.0 = 無傷)。"""
        return float(np.ptp(x[ramp]) / np.ptp(truth[ramp]))

    methods = [
        ("何もしない", lambda x: x),
        ("局所平均で割る(窓 9 = op の上限)", lambda x: bg_divide(x, 9)),
        ("局所平均で割る(窓 25)", lambda x: bg_divide(x, 25)),
        ("局所平均で割る(窓 61 = 自前)", lambda x: bg_divide(x, 61)),
        ("illuminate(シグマ上限 15)", lambda x: np.asarray(fs.op.illuminate(x, a=1.0, b=1.0))),
        ("gray_tophat(窓 9)", lambda x: np.asarray(fs.op.gray_tophat(x, a=1.0))),
        ("dc_homomorphic(周波数)", lambda x: np.asarray(fs.op.dc_homomorphic(x, a=0.1, b=0.5))),
        ("var_threshold(2 値、窓 15)", lambda x: np.asarray(fs.op.var_threshold(x, a=1.0))),
    ]
    print(f"  {'手法':<32}{'地の平坦度':>11}{'濃い字':>8}{'薄い字':>8}{'紙の誤検出':>11}"
          f"{'図の相関':>9}{'図の振幅':>9}")
    shadow_stats = {}
    for name, fn in methods:
        out = fn(rect_ideal)
        m = ink_mask(out)
        fl = flatness(out)
        rs = float(m[strong_ink].mean()); rw = float(m[faint_ink].mean())
        fp = float(m[paper].mean())
        rc, rg = ramp_corr(out), ramp_range(out)
        shadow_stats[name] = (fl, rs, rw, fp, rc, rg)
        print(f"  {name:<32}{fl:>11.4f}{100 * rs:>7.0f}%{100 * rw:>7.0f}%{100 * fp:>10.1f}%"
              f"{rc:>9.3f}{rg:>9.2f}")
    print("  → 「濃い字」「薄い字」は真の字の画素のうち 2 値化後も字と判定された割合、")
    print("     「紙の誤検出」は紙の地が字にされた割合。平坦度は小さいほど良い。")
    print("     何もしないと影の中の紙が丸ごと字にされ(誤検出)、薄い字は影の外で消える。")
    print("     窓を大きくするほど地は平らになるが、図の階調は局所平均と区別が付かず")
    print("     相関が落ちる —— **ランプは照明そのものに見える**。2 値化は振幅を 0 にする。")
    print("     ★ 窓 9(op で届く上限)と窓 61 の差が、a/b が小窓しか出せないことの代償。")

    print("\n=== 5. 壊れる条件 ===")

    def run_case(tilt=32.0, roll=7.0, shift=(0.0, 0.0), bg=0.30, shadow=0.22, kappa=0.0):
        q = camera_quad(tilt_deg=tilt, roll_deg=roll, shift=shift)
        Ht = calib.vector_to_hom_mat2d(src, q)
        il = illumination_field(shadow=shadow)
        c, ins = render_camera(doc, Ht, bg=bg, illum=il, kappa=kappa)
        try:
            m = page_mask(c)
            e = corners_by_side_fit(boundary_points(m))
        except Exception:                                  # noqa: BLE001 — 崩れ方も結果
            e = None
        if e is None:
            return None, None, c, Ht
        return corner_rms(e, q), landmark_error(calib.vector_to_hom_mat2d(src, e), Ht)[0], c, Ht

    print(f"  {'傾き [度]':>10}{'4 隅 RMS [px]':>14}{'格子 RMS [px]':>14}   紙の占有")
    for tilt in (5.0, 20.0, 35.0, 45.0, 55.0, 62.0):
        cr, lr, c, _ = run_case(tilt=tilt)
        occ = 100 * ((c > 0) & (page_mask(c))).mean()
        s = f"{cr:>14.2f}{lr:>14.3f}" if cr is not None else f"{'検出できず':>28}"
        print(f"  {tilt:>10.0f}{s}   {occ:>5.1f} %")

    print(f"\n  {'枠外への食み出し [px]':>22}{'4 隅 RMS [px]':>14}{'格子 RMS [px]':>14}")
    for dy in (0.0, -0.010, -0.020, -0.032, -0.044, -0.056):
        q = camera_quad(shift=(0.0, dy))
        out_px = max(0.0, float(np.max(np.maximum(-q[:, 1], q[:, 1] - (CAM_H - 1)))),
                     float(np.max(np.maximum(-q[:, 0], q[:, 0] - (CAM_W - 1)))))
        cr, lr, _, _ = run_case(shift=(0.0, dy))
        s = f"{cr:>14.2f}{lr:>14.3f}" if cr is not None else f"{'検出できず':>28}"
        print(f"  {out_px:>22.0f}{s}")
    print("  → 辺に直線を当てて交点を取る方式は、隅そのものが見えなくても外挿できる。")
    print("     崩れるのは**辺が 1 本まるごと枠の外に出たとき**。")

    print(f"\n  {'背景の明るさ':>14}{'紙との差':>10}{'4 隅 RMS [px]':>14}{'格子 RMS [px]':>14}")
    for bg in (0.30, 0.38, 0.44, 0.50, 0.65, 0.85):
        cr, lr, _, _ = run_case(bg=bg)
        s = f"{cr:>14.2f}{lr:>14.3f}" if cr is not None else f"{'検出できず':>28}"
        print(f"  {bg:>14.2f}{PAPER - bg:>10.2f}{s}")

    print(f"\n  {'影の強さ':>10}{'4 隅 RMS [px]':>14}{'格子 RMS [px]':>14}")
    for sh in (0.0, 0.20, 0.35, 0.45, 0.55, 0.75):
        cr, lr, _, _ = run_case(shadow=sh)
        s = f"{cr:>14.2f}{lr:>14.3f}" if cr is not None else f"{'検出できず':>28}"
        print(f"  {sh:>10.2f}{s}")

    print("\n=== 6. レンズ歪みを入れると、理想の補正でも罫線は曲がったまま ===")
    print(f"  {'kappa':>8}{'4 隅 RMS [px]':>14}{'罫線の曲がり(推定) [px]':>24}{'(理想 4 隅) [px]':>18}")
    for kappa in (0.0, -0.04, -0.09, -0.16):
        q = camera_quad()
        Ht = calib.vector_to_hom_mat2d(src, q)
        c, _ = render_camera(doc, Ht, kappa=kappa)
        e = corners_by_side_fit(boundary_points(page_mask(c)))
        if e is None:
            print(f"  {kappa:>8.2f}{'検出できず':>14}")
            continue
        bend_est = rule_bend(rectify(c, calib.vector_to_hom_mat2d(src, e)))
        bend_ideal = rule_bend(rectify(c, Ht))
        print(f"  {kappa:>8.2f}{corner_rms(e, q):>14.2f}{bend_est:>24.2f}{bend_ideal:>18.2f}")
    print("  → 4 隅の誤差が小さいままでも罫線は曲がる。ホモグラフィにレンズ歪みの")
    print("     項が無いので、これはモデルの誤りであって推定の誤りではない。")

    print("\n=== 7. 速度(この機械での実測)===")
    for label, fn in (("紙マスク(2 値+穴埋め+最大成分)", lambda: page_mask(cam)),
                      ("輪郭点の抽出", lambda: boundary_points(mask)),
                      ("辺の直線当て + 交点", lambda: corners_by_side_fit(pts)),
                      ("方向つき Hough", lambda: corners_by_hough(mask)),
                      ("ホモグラフィ推定(DLT)", lambda: calib.vector_to_hom_mat2d(src, est_fit)),
                      ("補正(再サンプル)", lambda: rectify(cam, H_est))):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<30}{1e3 * (time.perf_counter() - t0):>9.1f} ms"
              f"  ({CAM_H}x{CAM_W} → {DOC_H}x{DOC_W})")

    # ---- 自己検査(速さは assert しない)-------------------------------------
    assert iou > 0.98, f"紙マスクの IoU が低い: {iou}"
    assert corner_rms(est_fit, quad) < 1.5, "辺の直線当てが 4 隅を 1.5 px 以内に出せない"
    rms_ideal, _ = landmark_error(H_ideal, H_true)
    assert rms_ideal < 1e-6, f"真の隅を与えたのに残差が出る: {rms_ideal}"
    rms_est, _ = landmark_error(H_est, H_true)
    rms_lo, _ = landmark_error(H_sim, H_true)
    assert rms_est < 0.05 * rms_lo, "推定が下限(何もしない)に対して 20 倍良くない"
    rms_aff, _ = landmark_error(H_aff, H_true)
    assert rms_aff > 10 * rms_est, "同名 op(アフィン)の取り違えが数字に出ていない"
    # 影除去は必ず何かを削る: 地を平らにするほど図の階調が失われる
    s_none = shadow_stats["何もしない"]
    s_61 = shadow_stats["局所平均で割る(窓 61 = 自前)"]
    s_9 = shadow_stats["局所平均で割る(窓 9 = op の上限)"]
    s_bin = shadow_stats["var_threshold(2 値、窓 15)"]
    assert s_61[0] < s_none[0], "窓 61 で地が平らにならない"
    assert s_61[4] < s_none[4], "地を平らにしたのに図の階調が一切傷まない(想定外)"
    assert s_9[0] > s_61[0], "窓 9(op の上限)が窓 61 と同じだけ地を平らにできてしまう"
    assert s_bin[5] < 0.05, "2 値化なのに図の振幅が残っている"
    # op の局所窓が小さいことの機械的な確認(道具の穴 (d))
    o = fs.find_op("mean_image")
    assert "9" in (o.doc or ""), "mean_image の窓上限が docstring から読み取れない"
    # 同名 op が 2 つあり、モデルが違う(道具の穴 (c))
    assert calib.vector_to_hom_mat2d is not fit_transform.vector_to_hom_mat2d
    assert abs(fit_transform.vector_to_hom_mat2d(src, quad)[2, 0]) < 1e-12, \
        "fit_transform 版は射影項を持たないはず(アフィン)"
    assert abs(calib.vector_to_hom_mat2d(src, quad)[2, 0]) > 1e-9, \
        "calib 版に射影項が出ない(台形が付いていない)"
    # 入口から見えないこと(道具の穴 (b))
    assert "vector_to_hom_mat2d" not in dir(fs) and "vector_to_hom_mat2d" not in dir(fs.ledger)
    assert "hough_lines_dir" not in dir(fs) and "hough_lines_dir" not in dir(fs.ledger)
    print(f"\n  (全体 {time.perf_counter() - t_start:.1f} s)")
    print("\nPASS")


if __name__ == "__main__":
    main()

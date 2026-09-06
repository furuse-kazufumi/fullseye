# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_panorama_drift — 隣どうしを鎖でつなぐと、一周して元に戻れない。

    py -3.11 examples/poc_panorama_drift.py

【この PoC が答える問題】
パノラマ合成の教科書的な手順は「隣り合う 2 枚の対応から変換を求め、順に掛けて
いく」である。この手順で作った合成画像は **継ぎ目がどこも綺麗に見える**。
にもかかわらず一周して出発点に戻ると数十画素ずれている。理由は単純で、
**鎖は隣の誤差しか見ておらず、遠く離れたフレームどうしの整合を一度も測って
いない**から。誤差が消えたのではなく、見ていない場所に押し出されただけである。

ここでは真値を自分で握る。既知の回転列でパノラマから N 枚を切り出し、
360 度一周させて閉ループを作る。閉ループの真値は厳密に「ずれ 0」なので、
推定した鎖がどれだけ戻れないかを **画素で直接** 測れる。

    EXTEND: 実写に差し替えるなら ``render_frame`` を捨てて自分の画像列を
    ``frames`` に入れるだけでよい。ただし **真値が消える** ので第 3・5・7 章の
    「真の姿勢からのずれ」は測れなくなる。代わりに残るのは (a) 閉ループ誤差
    (一周する撮り方をすれば真値なしで測れる唯一の絶対量)と (b) 継ぎ目の
    食い違い。焦点距離は自分で決めた値ではなくなるので、第 7 章の感度表を見て
    「何 % 間違えるといくら曲がるか」を先に把握してから推定値を入れること。
    実写では ``TRUE_F`` を推定値に置き換えるのではなく、第 7 章のやり方で
    **一周の総回転角が 360 度になる f を探す** ほうが素性が良い。

【章立て】
 0. 舞台 —— 真値の作り方と往復検算
 1. 1 ペアの床 —— 対応点の精度と、そこから決まる 1 段あたりの誤差
 2. ゼロ点 = 隣接ペアの鎖 —— 継ぎ目は綺麗なのに一周して戻れない
 3. 4 つの系の比較(鎖 / 閉ループ拘束 / 全ペア / 大域最適化)
 4. ★ 崖 (a) 重なり率 80 → 10 %
 5. ★ 崖 (b) 枚数 N とドリフトの伸び —— 指数を実測で当てる
 6. ★ 崖 (c) 繰り返し模様の周期が 1 段の移動量に一致するとき
 7. ★ 崖 (d) 焦点距離の誤りが円筒に与える歪み
 8. 位置別の残差 —— 1 つの数字にまとめない
 9. 速度

【★ この PoC が出した道具の穴(op 本体は直していない)】
(a) **``mosaic`` モジュール一式がファサードにも op レジストリにも出ていない**。
    ``proj_match_points_ransac`` / ``gen_projective_mosaic`` /
    ``bundle_adjust_mosaic`` は ``import fullseye as fs`` の公開名 1108 個にも
    ``fs.op`` の 885 op にも無く、``import mosaic`` で裸のモジュールを叩くしか
    ない。ファサードだけを見る利用者には「パノラマ合成が無いライブラリ」に
    見える。
(b) **``bundle_adjust_mosaic`` は束調整ではない**。中身は「画像 0 と直接対応の
    ある相手だけを個別に RANSAC する」ループで、同時最適化も残差の再配分も
    しない。しかも画像 0 と直接の対応が無いフレームは **黙って単位行列のまま
    返る**。名前が約束していることを実装していないので、この PoC の第 3 章の
    「大域最適化」は自分で書いた(``fs.rodrigues`` + ``scipy.least_squares``)。
(c) **``gen_spherical_mosaic`` は球面で何もしない**。実体は
    ``return gen_projective_mosaic(...)`` の 1 行で、docstring の
    「球面パノラマ座標」に対応する処理が無い。
(d) **``proj_match_points_distortion_ransac`` は歪みを推定しない**。
    ``kappa = 0.0`` を足して返すだけ。歪みなしの答えが常に返るので、
    呼んだ側は「歪みは無かった」と読み違える。
(e) **``proj_match_points_ransac_guided`` の ``inliers`` は長さが違う**。
    誘導で間引いた後の部分集合に対するマスクを返すので、元の対応配列を
    そのマスクで添字づけすると黙って別の点を拾う(例外は出ない)。
(f) **ホモグラフィ推定がファサードに無い**。``fs`` には
    ``fundamental_matrix`` / ``essential_matrix`` / ``triangulate`` はあるのに
    ``homography`` が無い。唯一の実装 ``mosaic._homography_dlt`` は非公開の
    上に **点の正規化(等方スケーリング)をしていない**。第 1 章でその差を
    実測した。
(g) **キーポイントに副画素がない**。``fs.match_keypoints`` が返すのは整数座標で、
    副画素補間の入口も無い。第 1 章で測る対応点誤差の床はこれで決まる。
(h) **``optimize_pose_graph``(pose_graph.py)は回転だけの問題に使えない**。
    SE(3) 専用で並進を要求するため、純回転パノラマ(並進ゼロ)では辺の重みが
    定義できない。しかもこれもファサードに出ていない。
(i) **画像を円筒/正距円筒へ張る op が無い**。``tb_project_cylindrical`` /
    ``tb_project_spherical`` は名前に反して **3 次元点群 → 距離画像** であり、
    画像 → 円筒パノラマの写像ではない(``fs.op`` の typed 表記が
    ``points -> image``)。この PoC のキャンバス合成は自前。
"""
from __future__ import annotations

import time

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.optimize import least_squares

import fullseye as fs
import mosaic                     # ★ 穴 (a): fs ファサードにも op レジストリにも無い

T_START = time.perf_counter()

# ── カメラ(真値は私が決める)────────────────────────────────────────────── #
IMG_W, IMG_H = 140, 104
FOV_X_DEG = 45.0
TRUE_F = (IMG_W / 2.0) / np.tan(np.deg2rad(FOV_X_DEG) / 2.0)
CX, CY = (IMG_W - 1) / 2.0, (IMG_H - 1) / 2.0
K_TRUE = fs.intrinsic_matrix(TRUE_F, TRUE_F, CX, CY)
K_INV = np.linalg.inv(K_TRUE)

# ── 円筒パノラマ(場面そのもの)──────────────────────────────────────────── #
F_PAN = TRUE_F * 1.6                       # 元画像より細かく持つ(補間で潰さない)
W_PAN = int(round(2.0 * np.pi * F_PAN))
ELEV_MAX_DEG = 26.0
H_PAN = int(round(2.0 * F_PAN * np.tan(np.deg2rad(ELEV_MAX_DEG))))

# ── 判定に使う量(全章で共通)──────────────────────────────────────────── #
# 誤差はすべて **画素** で出す。角度 1 mrad は画像中心で TRUE_F * 1e-3 px なので
# 換算は一意。「良い/悪い」の線は引かない —— 引くと 1 つの数字に潰れる。
GRID_XY = np.array([[x, y] for y in (8.0, CY, IMG_H - 9.0)
                    for x in (8.0, CX, IMG_W - 9.0)])     # 画面内 3x3 の見張り点
CORNERS_XY = np.array([[0.0, 0.0], [IMG_W - 1.0, 0.0],
                       [IMG_W - 1.0, IMG_H - 1.0], [0.0, IMG_H - 1.0]])

MATCH_KW = dict(patch=11, ratio=0.85, min_distance=3, thresh_rel=0.002, max_n=600)
RANSAC_PX = 1.5


# ===========================================================================
# 0. 舞台 —— 場面・カメラ・真の回転列
# ===========================================================================
def _rx(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _ry(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def true_cam_to_world(theta):
    """方位角 ``theta`` のときのカメラ→世界回転。

    純粋なパンではなく、俯仰 1.5 度・回頭 1.0 度の**周期的な揺れ**を重ねてある。
    手持ちの雲台は必ず揺れるので 1 自由度問題にすると易しすぎる。揺れは
    ``sin`` なので theta = 0 と 2π で厳密に 0 に戻り、**閉ループの真値は
    厳密に単位行列**のまま保たれる。
    """
    return (_ry(theta)
            @ _rx(np.deg2rad(1.5) * np.sin(theta))
            @ _rz(np.deg2rad(1.0) * np.sin(2.0 * theta)))


def make_panorama(rng, period_deg=37.0, motif=1.0, confetti=4200):
    """円筒パノラマを作る。**構造のあるものを必ず混ぜる**。

    4 種類を重ねてある。(1) 低周波の滑らかな地(ここには対応点が立たない)、
    (2) 小さな四角の紙吹雪 —— 角がたくさん立ち、一つ一つは輝度が違うので
    descriptor が一意になる、(3) **直線の格子** —— 方位角は不等間隔にしてある。
    等間隔にすると格子そのものが繰り返し模様になり、第 6 章で調べたい
    「模様の周期」と混ざって原因が切り分けられなくなる、(4) **繰り返しグリフ**
    —— 周期 ``period_deg`` で同じ形を並べる。これが第 6 章の崖の材料。
    """
    base = gaussian_filter(rng.normal(size=(H_PAN, W_PAN)), 11.0)
    img = 0.30 + 0.40 * (base - base.min()) / np.ptp(base)

    ys = rng.integers(2, H_PAN - 6, confetti)
    xs = rng.integers(0, W_PAN, confetti)
    sz = rng.integers(2, 5, confetti)
    val = rng.uniform(0.05, 0.95, confetti)
    for y, x, s, v in zip(ys, xs, sz, val):
        img[y:y + s, x:x + s] = v
        if x + s > W_PAN:                      # 継ぎ目をまたぐぶんを巻き戻す
            img[y:y + s, 0:(x + s) % W_PAN] = v

    line_rng = np.random.default_rng(20260906)
    for d in np.sort(line_rng.uniform(0.0, 360.0, 44)):     # 不等間隔の縦線
        c = int(round(np.deg2rad(d) * F_PAN)) % W_PAN
        img[:, max(0, c - 1):c + 2] *= 0.40
    for e in (-18.0, -9.5, 0.0, 8.0, 17.0):                 # 不等間隔の横線
        r = int(round((H_PAN - 1) / 2.0 + np.tan(np.deg2rad(e)) * F_PAN))
        if 1 <= r < H_PAN - 1:
            img[r - 1:r + 2, :] *= 0.40

    if motif > 0.0:
        glyph = np.zeros((13, 13))
        glyph[2:11, 6] = 1.0
        glyph[6, 2:11] = 1.0
        glyph[2:5, 2:5] = 1.0
        glyph[8:11, 8:11] = 1.0
        step = np.deg2rad(period_deg) * F_PAN
        for k in range(int(W_PAN / step)):
            c = int(round(k * step)) % W_PAN
            for row in (int(H_PAN * 0.28), int(H_PAN * 0.60)):
                tile = img[row:row + 13, c:c + 13]
                if tile.shape == (13, 13):
                    img[row:row + 13, c:c + 13] = np.where(glyph > 0, 0.95, tile)
    return np.clip(img, 0.0, 1.0)


_rr, _cc = np.mgrid[0:IMG_H, 0:IMG_W]
_DIR_CAM = K_INV @ np.stack([_cc.ravel(), _rr.ravel(), np.ones(IMG_H * IMG_W)])


def render_frame(pan, R_c2w, rng=None, noise=0.005):
    """カメラ→世界回転 ``R_c2w`` の画像を円筒パノラマから切り出す(双一次)。"""
    d = R_c2w @ _DIR_CAM
    u = (np.arctan2(d[0], d[2]) * F_PAN) % W_PAN
    v = d[1] / np.hypot(d[0], d[2]) * F_PAN + (H_PAN - 1) / 2.0
    out = map_coordinates(pan, [v, u], order=1, mode="nearest").reshape(IMG_H, IMG_W)
    if rng is not None:
        out = out + rng.normal(0.0, noise, out.shape)
    return out


def pano_uv(R_c2w, pts_xy, focal=None):
    """画素 (x, y) を、そのフレームの姿勢で円筒パノラマ座標 (u, v) に写す。

    単位は「焦点距離 ``focal`` の画素」。既定は真の焦点距離なので、**画像中心の
    1 画素 = パノラマの 1 画素**。誤差を画素で言うための共通の物差し。
    """
    f = TRUE_F if focal is None else focal
    p = np.atleast_2d(np.asarray(pts_xy, float))
    d = R_c2w @ (K_INV @ np.column_stack([p, np.ones(len(p))]).T)
    u = np.arctan2(d[0], d[2]) * f
    v = d[1] / np.hypot(d[0], d[2]) * f
    return np.column_stack([u, v])


def uv_gap(uv_a, uv_b, focal=None):
    """パノラマ座標の差。u は円周なので巻き戻してから距離にする。"""
    f = TRUE_F if focal is None else focal
    du = uv_a[:, 0] - uv_b[:, 0]
    du = (du + np.pi * f) % (2.0 * np.pi * f) - np.pi * f
    return np.hypot(du, uv_a[:, 1] - uv_b[:, 1])


# ===========================================================================
# 推定の道具
# ===========================================================================
def dlt_normalized(p1, p2):
    """正規化つき DLT。``mosaic._homography_dlt`` は正規化しないので自前(穴 f)。"""
    def norm(p):
        c = p.mean(0)
        s = np.sqrt(2.0) / max(np.sqrt(((p - c) ** 2).sum(1)).mean(), 1e-12)
        T = np.array([[s, 0, -s * c[0]], [0, s, -s * c[1]], [0, 0, 1.0]])
        return (np.column_stack([p, np.ones(len(p))]) @ T.T)[:, :2], T

    q1, T1 = norm(np.asarray(p1, float))
    q2, T2 = norm(np.asarray(p2, float))
    A = []
    for (x, y), (u, v) in zip(q1, q2):
        A.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        A.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, Vt = np.linalg.svd(np.asarray(A))
    Hn = Vt[-1].reshape(3, 3)
    Hm = np.linalg.inv(T2) @ Hn @ T1
    return Hm / Hm[2, 2]


def apply_h(Hm, pts_xy):
    p = np.atleast_2d(np.asarray(pts_xy, float))
    q = np.column_stack([p, np.ones(len(p))]) @ np.asarray(Hm, float).T
    return q[:, :2] / q[:, 2:3]


def true_homography(R_i, R_j):
    """真の相対ホモグラフィ(フレーム i の画素 → フレーム j の画素)。"""
    return K_TRUE @ R_j.T @ R_i @ K_INV


def match_pair(img_i, img_j, seed):
    """2 枚から対応点を取り、RANSAC で外れ値を落として正規化 DLT で当てはめる。

    戻り値 ``None`` は「この 2 枚は繋げなかった」。重なりが少ないと本当にそうなる
    ので、失敗を握り潰さずそのまま上へ返す。
    """
    p1, p2 = fs.match_keypoints(img_i, img_j, **MATCH_KW)
    if len(p1) < 8:
        return None
    r = mosaic.proj_match_points_ransac(p1[:, ::-1], p2[:, ::-1],
                                        thresh=RANSAC_PX, iters=400, seed=seed)
    inl = r["inliers"]
    if int(inl.sum()) < 8:
        return None
    a, b = p1[inl], p2[inl]
    return {"H": dlt_normalized(a, b), "H_raw": r["H"], "p1": a, "p2": b,
            "n_match": len(p1), "n_inlier": int(inl.sum())}


def h_to_relrot(Hm, focal=None):
    """ホモグラフィ → 相対回転 ``A = Q_j Q_i^T``(``Q`` は世界→カメラ)。

    純回転なら ``K^-1 H K`` はスケール倍の回転行列。焦点距離を間違えるとそう
    ならないので、SVD で最寄りの回転へ落とし、**どれだけ回転から外れていたか**
    (特異値の広がり)も一緒に返す。第 7 章はこの値を読む。
    """
    Km = K_TRUE if focal is None else fs.intrinsic_matrix(focal, focal, CX, CY)
    A = np.linalg.inv(Km) @ np.asarray(Hm, float) @ Km
    U, S, Vt = np.linalg.svd(A)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        R = U @ np.diag([1.0, 1.0, -1.0]) @ Vt
    return R, float(S[0] / S[2] - 1.0)


def chain_rotations(rels, n):
    """ゼロ点 —— 隣接ペアの推定だけを鎖のように掛ける。"""
    Q = [np.eye(3)]
    for i in range(n - 1):
        Q.append(rels[(i, i + 1)] @ Q[-1])
    return Q


def spread_loop_error(Q, loop_rel, n):
    """閉ループ拘束 —— 一周して残った回転を全フレームへ等分に配り直す。"""
    E = loop_rel @ Q[-1]                       # 本来は単位行列のはず
    w = fs.rotation_log(E)
    return [fs.rodrigues(-(i / n) * w) @ Q[i] for i in range(n)], E


def rotation_average(n, edges):
    """全ペア —— 相対回転の集合から各フレームの姿勢をまとめて解く(スペクトル法)。

    ブロック行列 ``M[j][i] = A_ij`` の上位 3 固有ベクトルが ``Q_i G`` を並べたもの
    になる(``G`` は共通の任意直交行列)。フレーム 0 で ``G`` を潰す。
    鎖と違って **辺の順番が結果に影響しない** ——「どの経路で辿ったか」に依存
    しないことが、ドリフトが消える理由そのもの。
    """
    M = np.zeros((3 * n, 3 * n))
    for i in range(n):
        M[3 * i:3 * i + 3, 3 * i:3 * i + 3] = np.eye(3)
    for (i, j), A in edges.items():
        M[3 * j:3 * j + 3, 3 * i:3 * i + 3] += A
        M[3 * i:3 * i + 3, 3 * j:3 * j + 3] += A.T
    _, V = np.linalg.eigh(M)
    X = V[:, -3:]

    def proj(B):
        U, _, Vt = np.linalg.svd(B)
        R = U @ Vt
        return R if np.linalg.det(R) > 0 else U @ np.diag([1.0, 1.0, -1.0]) @ Vt

    blocks = [proj(X[3 * i:3 * i + 3, :]) for i in range(n)]
    return [b @ blocks[0].T for b in blocks]


def global_refine(Q_init, edge_pts, n):
    """大域最適化 —— 全対応点の再投影残差(画素)を同時に最小化する。

    ★ 穴 (b): ``mosaic.bundle_adjust_mosaic`` はこれをしないので自前。
    フレーム 0 を固定し、残りを ``fs.rodrigues`` の 3 変数で持つ。ヤコビアンの
    疎構造(1 本の残差は 2 フレームにしか触らない)を渡さないと差分計算が
    パラメータ数に比例して遅くなる。
    """
    x0 = np.concatenate([fs.rotation_log(Q_init[i]) for i in range(1, n)])
    keys = list(edge_pts.keys())
    counts = [len(edge_pts[k]["p1"]) for k in keys]
    rows = 2 * sum(counts)
    spars = np.zeros((rows, 3 * (n - 1)))
    r0 = 0
    for (i, j), c in zip(keys, counts):
        for f in (i, j):
            if f > 0:
                spars[r0:r0 + 2 * c, 3 * (f - 1):3 * f] = 1
        r0 += 2 * c

    def residual(x):
        Q = [np.eye(3)] + [fs.rodrigues(x[3 * k:3 * k + 3]) for k in range(n - 1)]
        out = []
        for (i, j) in keys:
            d = edge_pts[(i, j)]
            Hm = K_TRUE @ Q[j] @ Q[i].T @ K_INV
            out.append((apply_h(Hm, d["p1"]) - d["p2"]).ravel())
        return np.concatenate(out)

    sol = least_squares(residual, x0, jac_sparsity=spars, method="trf",
                        xtol=1e-10, ftol=1e-10, max_nfev=60)
    return [np.eye(3)] + [fs.rodrigues(sol.x[3 * k:3 * k + 3]) for k in range(n - 1)]


# ── 誤差の測り方 ─────────────────────────────────────────────────────────── #
def pose_error_px(Q_est, R_true_list):
    """各フレームの真の姿勢からのずれ(画素)。画面内 3x3 の見張り点の平均。"""
    out = []
    for Qe, Rt in zip(Q_est, R_true_list):
        out.append(uv_gap(pano_uv(Qe.T, GRID_XY), pano_uv(Rt, GRID_XY)).mean())
    return np.asarray(out)


def seam_error_px(Q_est, R_true_list, pairs):
    """継ぎ目のずれ —— 推定姿勢で隣を重ねたときに画素が何画素食い違うか。"""
    out = {}
    for (i, j) in pairs:
        He = K_TRUE @ Q_est[j] @ Q_est[i].T @ K_INV
        Ht = true_homography(R_true_list[i], R_true_list[j])
        out[(i, j)] = float(np.linalg.norm(apply_h(He, GRID_XY)
                                           - apply_h(Ht, GRID_XY), axis=1).mean())
    return out


def loop_gap_px(loop_R):
    """閉ループ誤差 —— 一周して戻った姿勢と単位行列の差を、画像四隅の画素で。"""
    uv_e = pano_uv(loop_R.T, CORNERS_XY)
    uv_0 = pano_uv(np.eye(3), CORNERS_XY)
    g = uv_gap(uv_e, uv_0)
    return float(g.mean()), float(g.max()), float(np.rad2deg(
        np.linalg.norm(fs.rotation_log(loop_R))))


def build_edges(n, max_gap, closed):
    """使うペアの一覧。``max_gap=1`` が鎖、2 以上で離れたフレームも使う。"""
    out = []
    for i in range(n):
        for g in range(1, max_gap + 1):
            j = i + g
            if j < n:
                out.append((i, j))
            elif closed:
                out.append((i, (j) % n))
    return out


def rule(title):
    print("\n" + "=" * 74)
    print(title)
    print("=" * 74)


# ===========================================================================
# 0 章
# ===========================================================================
rule("0. 舞台 —— 真値の作り方と往復検算")
rng = np.random.default_rng(20260906)
PAN = make_panorama(rng)
print(f"円筒パノラマ {H_PAN} x {W_PAN} px (焦点 {F_PAN:.1f} px 相当, 仰角 ±{ELEV_MAX_DEG:.0f} 度)")
print(f"カメラ {IMG_W} x {IMG_H} px, 水平画角 {FOV_X_DEG:.0f} 度, 焦点距離 {TRUE_F:.2f} px")

# 検算 1: 真のホモグラフィで写した点が、真の姿勢の円筒座標と一致するか
_Ra, _Rb = true_cam_to_world(np.deg2rad(0.0)), true_cam_to_world(np.deg2rad(15.0))
_hp = apply_h(true_homography(_Ra, _Rb), GRID_XY)
_chk = uv_gap(pano_uv(_Ra, GRID_XY), pano_uv(_Rb, _hp)).max()
print(f"検算 1  ホモグラフィと円筒投影の往復           最大 {_chk:.3e} px")

# 検算 2: 真の姿勢を鎖に流し込めば閉ループ誤差はゼロのはず
_n = 24
_Rtrue = [true_cam_to_world(2 * np.pi * i / _n) for i in range(_n)]
_rel = {(i, (i + 1) % _n): _Rtrue[(i + 1) % _n].T @ _Rtrue[i] for i in range(_n)}
_Q = chain_rotations(_rel, _n)
_lm, _lx, _ld = loop_gap_px(_rel[(_n - 1, 0)] @ _Q[-1])
print(f"検算 2  真値だけで一周したときの閉ループ誤差   {_lm:.3e} px (角度 {_ld:.2e} 度)")
assert _chk < 1e-8 and _lm < 1e-8, "舞台の真値が閉じていない"
print("→ 真値は閉じている。以降の閉ループ誤差はすべて **推定の誤差** である。")


# ===========================================================================
# 1 章
# ===========================================================================
rule("1. 1 ペアの床 —— 対応点の精度と、1 段あたりの誤差")
print("鎖の誤差はすべてここから積み上がる。まず 1 段の大きさを測る。")

N_LOOP = 24
STEP_DEG = 360.0 / N_LOOP
OVERLAP_LOOP = 1.0 - STEP_DEG / FOV_X_DEG
R_LOOP = [true_cam_to_world(2 * np.pi * i / N_LOOP) for i in range(N_LOOP)]
FRAMES = [render_frame(PAN, R, rng) for R in R_LOOP]
print(f"N = {N_LOOP} 枚, 1 段 {STEP_DEG:.1f} 度, 重なり率 {OVERLAP_LOOP * 100:.0f} %")

print(f"\n{'ペア':>6} {'対応':>5} {'内点':>5} {'対応点の真の誤差':>18} "
      f"{'H の誤差(px)':>14} {'正規化なし DLT':>16}")
pair_px, pair_raw_px, corr_err_all, n_in_all = [], [], [], []
for i in range(N_LOOP):
    j = (i + 1) % N_LOOP
    m = match_pair(FRAMES[i], FRAMES[j], seed=100 + i)
    assert m is not None, f"ペア {i}-{j} が繋がらない"
    Ht = true_homography(R_LOOP[i], R_LOOP[j])
    ce = np.linalg.norm(apply_h(Ht, m["p1"]) - m["p2"], axis=1)
    e_norm = float(np.linalg.norm(apply_h(m["H"], GRID_XY)
                                  - apply_h(Ht, GRID_XY), axis=1).mean())
    e_raw = float(np.linalg.norm(apply_h(m["H_raw"], GRID_XY)
                                 - apply_h(Ht, GRID_XY), axis=1).mean())
    pair_px.append(e_norm)
    pair_raw_px.append(e_raw)
    n_in_all.append(m["n_inlier"])
    corr_err_all.append(ce)
    if i < 5:
        print(f"{i:>3}-{j:<2} {m['n_match']:>5} {m['n_inlier']:>5} "
              f"{np.median(ce):>13.3f} px {e_norm:>13.3f} {e_raw:>16.3f}")
corr_all = np.concatenate(corr_err_all)
PAIR_MEAN = float(np.mean(pair_px))
PAIR_MAX = float(np.max(pair_px))
DLT_RAW_MEAN = float(np.mean(pair_raw_px))
print(f"{'...':>6}")
print(f"全 {N_LOOP} ペア: 内点 {np.mean(n_in_all):.1f} 個(中央値), "
      f"対応点の真の誤差 中央値 {np.median(corr_all):.3f} px / 90 % 点 "
      f"{np.percentile(corr_all, 90):.3f} px")
print(f"1 段の誤差 平均 {PAIR_MEAN:.4f} px / 最悪 {PAIR_MAX:.4f} px")
print(f"\n★ 穴 (g): 対応点は整数座標で返る。副画素補間が無いので、対応点の誤差の床は")
print(f"   量子化で決まる ~0.3 px。ここが以下すべての誤差の出発点。")
print(f"★ 穴 (f): 正規化なし DLT(mosaic._homography_dlt)だと 1 段 "
      f"{DLT_RAW_MEAN:.4f} px、")
print(f"   正規化ありだと {PAIR_MEAN:.4f} px。比 {DLT_RAW_MEAN / PAIR_MEAN:.2f} 倍。"
      f" 以降は正規化ありを使う。")


# ===========================================================================
# 2 章
# ===========================================================================
rule("2. ゼロ点 = 隣接ペアの鎖 —— 継ぎ目は綺麗なのに一周して戻れない")

REL_ADJ, EDGE_PTS_ADJ = {}, {}
for (i, j) in build_edges(N_LOOP, 1, closed=True):
    m = match_pair(FRAMES[i], FRAMES[j], seed=200 + i)
    assert m is not None
    A, _ = h_to_relrot(m["H"])
    REL_ADJ[(i, j)] = A
    EDGE_PTS_ADJ[(i, j)] = m

Q_CHAIN = chain_rotations({k: v for k, v in REL_ADJ.items() if k[1] == k[0] + 1}, N_LOOP)
LOOP_R_CHAIN = REL_ADJ[(N_LOOP - 1, 0)] @ Q_CHAIN[-1]
lg_mean, lg_max, lg_deg = loop_gap_px(LOOP_R_CHAIN)
seam_chain = seam_error_px(Q_CHAIN, R_LOOP, build_edges(N_LOOP, 1, closed=True))
seam_open = [v for k, v in seam_chain.items() if k != (N_LOOP - 1, 0)]
pe_chain = pose_error_px(Q_CHAIN, R_LOOP)

print(f"隣り合う継ぎ目 {len(seam_open)} 本のずれ    平均 {np.mean(seam_open):.3f} px "
      f"/ 最悪 {np.max(seam_open):.3f} px")
print(f"最後に閉じる継ぎ目 ({N_LOOP - 1}-0) のずれ  {seam_chain[(N_LOOP - 1, 0)]:.3f} px")
print(f"閉ループ誤差(四隅)               平均 {lg_mean:.3f} px / 最悪 {lg_max:.3f} px "
      f"(残る回転 {lg_deg:.3f} 度)")
print(f"真の姿勢からのずれ                 平均 {pe_chain.mean():.3f} px "
      f"/ 最悪 {pe_chain.max():.3f} px (フレーム {int(pe_chain.argmax())})")
print(f"\n→ 隣どうしは {np.mean(seam_open):.2f} px で合っているのに、"
      f"閉じる 1 本だけ {seam_chain[(N_LOOP - 1, 0)]:.1f} px 開く。")
print("   誤差は消えていない。**まだ測っていない 1 本に全部押し出されている**。")
print("   合成画像を眺めて品質を判断すると、この崖は最後まで見えない。")


# ===========================================================================
# 3 章
# ===========================================================================
rule("3. 4 つの系の比較 —— 何を測る系にすると誤差が戻ってくるか")

MAX_GAP = 3
REL_ALL, EDGE_PTS_ALL = dict(REL_ADJ), dict(EDGE_PTS_ADJ)
for (i, j) in build_edges(N_LOOP, MAX_GAP, closed=True):
    if (i, j) in REL_ALL:
        continue
    m = match_pair(FRAMES[i], FRAMES[j], seed=300 + i * 7 + j)
    if m is None:
        continue
    A, _ = h_to_relrot(m["H"])
    REL_ALL[(i, j)] = A
    EDGE_PTS_ALL[(i, j)] = m

Q_SPREAD, E_LOOP = spread_loop_error(Q_CHAIN, REL_ADJ[(N_LOOP - 1, 0)], N_LOOP)
Q_ALLPAIR = rotation_average(N_LOOP, REL_ALL)
Q_GLOBAL = global_refine(Q_CHAIN, EDGE_PTS_ALL, N_LOOP)

SYSTEMS = [
    ("鎖(隣接のみ・ゼロ点)", Q_CHAIN, len(REL_ADJ)),
    ("鎖 + 閉ループ拘束", Q_SPREAD, len(REL_ADJ)),
    (f"全ペア(距離 <= {MAX_GAP})", Q_ALLPAIR, len(REL_ALL)),
    ("大域最適化(GN)", Q_GLOBAL, len(REL_ALL)),
]
pairs_adj = build_edges(N_LOOP, 1, closed=True)
print(f"{'系':<24}{'辺':>4}{'姿勢平均':>10}{'姿勢最悪':>10}"
      f"{'継ぎ目平均':>12}{'閉じ目':>9}{'閉ループ':>10}")
print("-" * 79)
RESULT = {}
for name, Q, n_edge in SYSTEMS:
    pe = pose_error_px(Q, R_LOOP)
    sm = seam_error_px(Q, R_LOOP, pairs_adj)
    close = sm[(N_LOOP - 1, 0)]
    others = [v for k, v in sm.items() if k != (N_LOOP - 1, 0)]
    lr = REL_ADJ[(N_LOOP - 1, 0)] @ Q[-1] if name.startswith("鎖(") else None
    if lr is None:
        # 系ごとに「一周して戻ったときの姿勢」を推定姿勢そのものから測る
        lg = uv_gap(pano_uv(Q[0].T, CORNERS_XY),
                    pano_uv((REL_ADJ[(N_LOOP - 1, 0)] @ Q[-1]).T, CORNERS_XY)).mean()
    else:
        lg = loop_gap_px(lr)[0]
    RESULT[name] = dict(pose_mean=pe.mean(), pose_max=pe.max(),
                        seam=np.mean(others), close=close, loop=lg)
    print(f"{name:<24}{n_edge:>4}{pe.mean():>10.3f}{pe.max():>10.3f}"
          f"{np.mean(others):>12.3f}{close:>9.3f}{lg:>10.3f}")
print("-" * 79)
print("単位はすべて画素。「閉じ目」= 最後に閉じる 1 本の継ぎ目、")
print("「閉ループ」= 推定した相対回転で一周したときに戻れない量。")
print(f"\n→ 閉ループ拘束だけで姿勢の誤差は "
      f"{RESULT['鎖(隣接のみ・ゼロ点)']['pose_max'] / RESULT['鎖 + 閉ループ拘束']['pose_max']:.1f} "
      f"倍良くなるが、これは **一周する撮り方をした場合にしか使えない**。")
print(f"→ 全ペアと大域最適化は一周しなくても効く。離れたフレームどうしを直接測る")
print(f"   ことが、経路依存を消す本体である(閉ループ拘束は同じことの特殊例)。")


# ===========================================================================
# 4 章
# ===========================================================================
rule("4. ★ 崖 (a) 重なり率 80 → 10 %")
print("重なりを削ると 2 つのことが同時に起きる: 対応点が減る、対応点が画面の端に")
print("片寄る。後者のほうが効く —— 狭い帯だけで決めた変換は帯の外で外挿になる。")
print(f"\n{'重なり':>7}{'1段(度)':>9}{'対応':>6}{'内点':>6}"
      f"{'1段の誤差':>11}{'鎖の姿勢最悪':>14}{'閉ループ':>10}")
print("-" * 65)
N_OV = 8
ov_rows = []
for ov in (0.80, 0.60, 0.40, 0.25, 0.15, 0.10):
    step = np.deg2rad(FOV_X_DEG * (1.0 - ov))
    Rt = [true_cam_to_world(step * i) for i in range(N_OV)]
    fr = [render_frame(PAN, R, rng) for R in Rt]
    rels, e1, nm, ni, ok = {}, [], [], [], True
    for i in range(N_OV - 1):
        m = match_pair(fr[i], fr[i + 1], seed=400 + i)
        if m is None:
            ok = False
            break
        Ht = true_homography(Rt[i], Rt[i + 1])
        e1.append(float(np.linalg.norm(apply_h(m["H"], GRID_XY)
                                       - apply_h(Ht, GRID_XY), axis=1).mean()))
        nm.append(m["n_match"])
        ni.append(m["n_inlier"])
        A, _ = h_to_relrot(m["H"])
        rels[(i, i + 1)] = A
    if not ok:
        print(f"{ov * 100:>6.0f}%{np.rad2deg(step):>9.1f}{'—':>6}{'—':>6}"
              f"{'繋がらない':>13}{'—':>14}{'—':>10}")
        ov_rows.append((ov, None, None))
        continue
    Q = chain_rotations(rels, N_OV)
    pe = pose_error_px(Q, Rt)
    loop = uv_gap(pano_uv(Q[-1].T, CORNERS_XY), pano_uv(Rt[-1], CORNERS_XY)).mean()
    print(f"{ov * 100:>6.0f}%{np.rad2deg(step):>9.1f}{np.mean(nm):>6.0f}"
          f"{np.mean(ni):>6.0f}{np.mean(e1):>11.3f}{pe.max():>14.3f}{loop:>10.3f}")
    ov_rows.append((ov, float(np.mean(e1)), float(pe.max())))
print("-" * 65)
_ok = [r for r in ov_rows if r[1] is not None]
CLIFF_OV = _ok[-1][1] / _ok[0][1]
print(f"→ 重なり 80 % → {_ok[-1][0] * 100:.0f} % で 1 段の誤差が {CLIFF_OV:.1f} 倍。")
print("   「閉ループ」列は 8 枚を開いた鎖で辿った終端のずれ(一周していないので")
print("   真値との差そのもの)。重なりを削ると鎖はまず 1 段で壊れる。")


# ===========================================================================
# 5 章
# ===========================================================================
rule("5. ★ 崖 (b) 枚数 N とドリフトの伸び —— 指数を実測で当てる")
print("理屈の予想: 1 段の誤差が偏りのない独立な雑音なら、鎖はランダムウォークで")
print("誤差 ∝ √N(指数 0.5)。1 段に系統的な偏りがあれば ∝ N(指数 1.0)。")
print("どちらなのかは **測らないと分からない**。8 本の別々の場面で測る。")

N_LIST = [4, 8, 16, 32, 64]
STEP_SWEEP_DEG = 5.0                     # 64 枚で 315 度 —— 一周させない(巻き戻り回避)
N_TRIAL = 8
acc = {n: [] for n in N_LIST}
bias_yaw, noise_yaw = [], []
for t in range(N_TRIAL):
    r_t = np.random.default_rng(9000 + t)
    pan_t = make_panorama(r_t, period_deg=37.0 + 3.0 * t)
    Rt = [true_cam_to_world(np.deg2rad(STEP_SWEEP_DEG) * i) for i in range(max(N_LIST))]
    fr = [render_frame(pan_t, R, r_t) for R in Rt]
    rels = {}
    for i in range(max(N_LIST) - 1):
        m = match_pair(fr[i], fr[i + 1], seed=500 + i)
        if m is None:
            rels[(i, i + 1)] = np.eye(3)
            continue
        A, _ = h_to_relrot(m["H"])
        rels[(i, i + 1)] = A
        A_true = Rt[i + 1].T @ Rt[i]
        d = fs.rotation_log(A @ A_true.T)
        bias_yaw.append(d[1])
        noise_yaw.append(np.linalg.norm(d))
    Q = chain_rotations(rels, max(N_LIST))
    pe = pose_error_px(Q, Rt)
    for n in N_LIST:
        acc[n].append(pe[n - 1])

print(f"\n{'N':>4}{'終端のずれ 平均':>18}{'中央値':>10}{'最悪の試行':>12}")
print("-" * 46)
for n in N_LIST:
    v = np.asarray(acc[n])
    print(f"{n:>4}{v.mean():>18.3f}{np.median(v):>10.3f}{v.max():>12.3f}")
print("-" * 46)
lg_n = np.log(np.asarray(N_LIST, float))
lg_e = np.log(np.asarray([np.mean(acc[n]) for n in N_LIST]))
SLOPE = float(np.polyfit(lg_n, lg_e, 1)[0])
bias_yaw = np.asarray(bias_yaw)
noise_yaw = np.asarray(noise_yaw)
b_px = abs(bias_yaw.mean()) * TRUE_F
s_px = bias_yaw.std() * TRUE_F
print(f"log-log の傾き(実測)              {SLOPE:.3f}")
print(f"1 段の方位角誤差 偏り {bias_yaw.mean() * 1e3:+.3f} mrad "
      f"({b_px:+.4f} px) / ばらつき {bias_yaw.std() * 1e3:.3f} mrad ({s_px:.4f} px)")
print(f"偏りとばらつきの比                  {abs(bias_yaw.mean()) / bias_yaw.std():.3f}")
print(f"N = 64 での内訳予想: 偏りぶん {b_px * 64:.2f} px / "
      f"ランダムウォークぶん {s_px * np.sqrt(64):.2f} px")
print(f"→ 実測 {np.mean(acc[64]):.2f} px。")
if SLOPE < 0.72:
    print("→ 指数は 0.5 側。1 段の誤差はほぼ偏りが無く、ドリフトはランダムウォーク。")
    print("   ここで「偏りが無い」のは **合成したデータだから** である。実写では")
    print("   焦点距離のずれ(第 7 章)や露出変化が偏りを作り、指数は 1 に寄る。")
else:
    print("→ 指数は 1 側。1 段に系統的な偏りがある(上の偏り列を見よ)。")
    print("   ランダムウォークではないので、枚数を減らしても √N でしか減らない")
    print("   という予想は外れる —— 偏りの原因を潰すほうが効く。")


# ===========================================================================
# 6 章
# ===========================================================================
rule("6. ★ 崖 (c) 繰り返し模様の周期が 1 段の移動量に一致するとき")
STEP6 = 15.0
SHIFT_PX = TRUE_F * np.tan(np.deg2rad(STEP6))
print(f"1 段 {STEP6:.0f} 度 = 画像中心で {SHIFT_PX:.1f} px の移動。模様の周期が")
print(f"この移動量の整数倍に近いと、descriptor は **隣の繰り返し** と区別できない。")
print(f"共鳴が起きるのは周期 ≈ {STEP6:.0f} 度 と その半分 {STEP6 / 2:.1f} 度。")
print(f"\n{'周期(度)':>10}{'周期(px)':>10}{'対応':>6}{'誤対応率':>10}"
      f"{'内点':>6}{'1段の誤差':>11}{'6枚の鎖 最悪':>14}")
print("-" * 68)
N6 = 6
rep_rows = []
for per in (6.0, 7.5, 9.0, 12.0, 15.0, 18.0, 22.0, 30.0):
    r6 = np.random.default_rng(4242)
    pan6 = make_panorama(r6, period_deg=per, motif=1.0)
    Rt = [true_cam_to_world(np.deg2rad(STEP6) * i) for i in range(N6)]
    fr = [render_frame(pan6, R, r6) for R in Rt]
    rels, bad, tot, e1, nm, ni = {}, 0, 0, [], [], []
    for i in range(N6 - 1):
        m = match_pair(fr[i], fr[i + 1], seed=600 + i)
        if m is None:
            rels[(i, i + 1)] = np.eye(3)
            continue
        p1, p2 = fs.match_keypoints(fr[i], fr[i + 1], **MATCH_KW)
        Ht = true_homography(Rt[i], Rt[i + 1])
        err = np.linalg.norm(apply_h(Ht, p1) - p2, axis=1)
        bad += int((err > 3.0).sum())
        tot += len(err)
        e1.append(float(np.linalg.norm(apply_h(m["H"], GRID_XY)
                                       - apply_h(Ht, GRID_XY), axis=1).mean()))
        nm.append(m["n_match"])
        ni.append(m["n_inlier"])
        A, _ = h_to_relrot(m["H"])
        rels[(i, i + 1)] = A
    Q = chain_rotations(rels, N6)
    pe = pose_error_px(Q, Rt)
    frac = bad / max(tot, 1)
    per_px = np.deg2rad(per) * TRUE_F
    print(f"{per:>10.1f}{per_px:>10.1f}{np.mean(nm):>6.0f}{frac * 100:>9.1f}%"
          f"{np.mean(ni):>6.0f}{np.mean(e1):>11.3f}{pe.max():>14.3f}")
    rep_rows.append((per, frac, float(np.mean(e1)), float(pe.max())))
print("-" * 68)
_res = [r for r in rep_rows if abs(r[0] - 15.0) < 0.1 or abs(r[0] - 7.5) < 0.1]
_off = [r for r in rep_rows if r not in _res]
REP_BAD_RES = max(r[1] for r in _res)
REP_BAD_OFF = np.median([r[1] for r in _off])
print(f"→ 共鳴する周期(7.5 / 15 度)の誤対応率 最大 {REP_BAD_RES * 100:.1f} %、")
print(f"   外れた周期の中央値 {REP_BAD_OFF * 100:.1f} %。")
print("★ 誤対応率が上がっても RANSAC が吸収してしまうことがある。「内点が多い」は")
print("   正しさの証拠にならない —— 誤対応どうしが同じ嘘のホモグラフィで整合する")
print("   と、内点だけが増えて誤差も増える。上の表は両方を並べてある。")


# ===========================================================================
# 7 章
# ===========================================================================
rule("7. ★ 崖 (d) 焦点距離の誤りが円筒に与える歪み")
print("ホモグラフィから回転を取り出すには焦点距離が要る。f を間違えると")
print("K^-1 H K は回転行列でなくなる。SVD で最寄りの回転に丸めれば計算は通るが、")
print("**丸めた分が毎段の偏りになって積み上がる**。第 5 章で言った「偏りがあれば")
print("指数は 1」の実例。")
print(f"\n{'f 誤差':>8}{'f (px)':>9}{'回転からの外れ':>16}{'一周の総回転(度)':>18}"
      f"{'仰角ドリフト':>14}{'閉ループ':>10}")
print("-" * 76)
foc_rows = []
for e in (-0.10, -0.05, -0.02, 0.0, 0.02, 0.05, 0.10):
    f_use = TRUE_F * (1.0 + e)
    rels, nonrot = {}, []
    for (i, j) in build_edges(N_LOOP, 1, closed=True):
        A, s = h_to_relrot(EDGE_PTS_ADJ[(i, j)]["H"], focal=f_use)
        rels[(i, j)] = A
        nonrot.append(s)
    Q = chain_rotations({k: v for k, v in rels.items() if k[1] == k[0] + 1}, N_LOOP)
    total_yaw = 0.0
    for i in range(N_LOOP):
        total_yaw += abs(fs.rotation_log(rels[(i, (i + 1) % N_LOOP)])[1])
    # 仰角ドリフト: 各フレームの光軸が水平から何 px 上下にずれたか
    elev = []
    for Qi in Q:
        d = Qi.T @ np.array([0.0, 0.0, 1.0])
        elev.append(abs(d[1] / np.hypot(d[0], d[2])) * TRUE_F)
    lg = loop_gap_px(rels[(N_LOOP - 1, 0)] @ Q[-1])[0]
    print(f"{e * 100:>+7.0f}%{f_use:>9.2f}{np.mean(nonrot):>16.2e}"
          f"{np.rad2deg(total_yaw):>18.2f}{max(elev):>13.2f}px{lg:>10.2f}")
    foc_rows.append((e, np.rad2deg(total_yaw), max(elev), lg))
print("-" * 76)
_f0 = [r for r in foc_rows if r[0] == 0.0][0]
_fp = [r for r in foc_rows if abs(r[0] - 0.10) < 1e-9][0]
_fm = [r for r in foc_rows if abs(r[0] + 0.10) < 1e-9][0]
FOC_YAW_SPAN = abs(_fp[1] - _fm[1])
print(f"→ f を ±10 % 間違えると一周の総回転角が {_fm[1]:.1f} 〜 {_fp[1]:.1f} 度に振れる")
print(f"   (真値 360 度、正しい f では {_f0[1]:.2f} 度)。総回転角が 360 度になる f を")
print("   探せば、真値を知らなくても焦点距離を較正できる —— これが実写での使い方。")
print(f"→ 仰角ドリフトは f が {'小さ' if _fm[2] > _fp[2] else '大き'}すぎる側で悪化し、")
print(f"   最大 {max(_fp[2], _fm[2]):.1f} px。円筒に張ったとき水平線が弓なりに曲がる量。")


# ===========================================================================
# 8 章
# ===========================================================================
rule("8. 位置別の残差 —— 1 つの数字にまとめない")
print("同じ「平均 0.4 px」でも、画面の真ん中が合っていて四隅が開いているのと、")
print("全面が一様にずれているのとでは合成画像の見え方がまるで違う。")
cells = np.zeros(9)
for (i, j) in build_edges(N_LOOP, 1, closed=True):
    m = EDGE_PTS_ADJ[(i, j)]
    Ht = true_homography(R_LOOP[i], R_LOOP[j])
    cells += np.linalg.norm(apply_h(m["H"], GRID_XY) - apply_h(Ht, GRID_XY), axis=1)
cells /= N_LOOP
print("\n1 ペアあたりの残差(px)を画面内 3x3 で分けたもの:")
print(f"{'':>8}{'左':>9}{'中':>9}{'右':>9}")
for r, lab in enumerate(("上", "中", "下")):
    print(f"{lab:>8}" + "".join(f"{cells[r * 3 + c]:>9.3f}" for c in range(3)))
EDGE_CENTER_RATIO = float(max(cells[0], cells[2], cells[6], cells[8]) / cells[4])
print(f"\n四隅 / 中央 の比 {EDGE_CENTER_RATIO:.2f}")
print("対応点は画面全体に散っているので、この比は「外挿」ではなく")
print("**ホモグラフィの自由度が周辺で効く** ことを示している。")

print("\nフレームごとの姿勢誤差(鎖・上位 5 件と下位 3 件):")
order = np.argsort(pe_chain)[::-1]
for idx in list(order[:5]) + list(order[-3:]):
    ang = 360.0 * idx / N_LOOP
    print(f"  フレーム {int(idx):>2} (方位 {ang:>5.1f} 度)  {pe_chain[idx]:>7.3f} px")
print(f"平均 {pe_chain.mean():.3f} px、最悪 {pe_chain.max():.3f} px —— "
      f"比 {pe_chain.max() / pe_chain.mean():.1f} 倍。")
print("鎖の誤差は方位角に沿って単調には増えない(揺れの位相と噛み合う)。")
print("「平均」だけ見ると最悪フレームの見た目を過小評価する。")


# ===========================================================================
# 9 章
# ===========================================================================
rule("9. 速度と、この PoC が測らなかったこと")
n_pairs = len(EDGE_PTS_ALL)
print(f"総経過 {time.perf_counter() - T_START:.1f} s")
print(f"1 ペアの対応取り + RANSAC + DLT は数 ms(第 1-3 章で {n_pairs} ペア)。")
print("重いのは大域最適化ではなく **ペア数** である。全ペアを距離無制限にすると")
print(f"N = {N_LOOP} で {N_LOOP * (N_LOOP - 1) // 2} ペアになり、重なりの無い組を")
print("大量に試すことになる。距離 3 に切ったのはそのため(重なり 0 のペアは")
print("そもそも繋がらない)。")
print("\n測っていないこと(この PoC の外):")
print(" - 露出・ビネットの違い。実写では継ぎ目の見た目はここでも壊れる。")
print(" - 並進(視差)。純回転を仮定しているので、近景があるとホモグラフィ自体が")
print("   成り立たない。その場合の崖は本 PoC では測れない。")
print(" - レンズ歪み。歪みを入れると穴 (d) の通り推定する道具が無い。")


# ===========================================================================
# 結論(機械で固定する)
# ===========================================================================
rule("結論")
r_chain = RESULT["鎖(隣接のみ・ゼロ点)"]
r_spread = RESULT["鎖 + 閉ループ拘束"]
r_all = RESULT[f"全ペア(距離 <= {MAX_GAP})"]
r_gn = RESULT["大域最適化(GN)"]
print(f"1. 鎖は隣の継ぎ目を {np.mean(seam_open):.2f} px に保ったまま、"
      f"閉じる 1 本を {r_chain['close']:.1f} px 開く。")
print(f"2. 姿勢の最悪誤差: 鎖 {r_chain['pose_max']:.2f} → 閉ループ拘束 "
      f"{r_spread['pose_max']:.2f} → 全ペア {r_all['pose_max']:.2f} → "
      f"大域最適化 {r_gn['pose_max']:.2f} px。")
print(f"3. ドリフトの伸びの指数は実測 {SLOPE:.2f}(理屈の予想 0.5 = "
      f"ランダムウォーク / 1.0 = 偏り)。")
print(f"4. 重なり 80 → {_ok[-1][0] * 100:.0f} % で 1 段の誤差 {CLIFF_OV:.1f} 倍。")
print(f"5. f を ±10 % 間違えると一周の総回転角が {FOC_YAW_SPAN:.1f} 度も動く。")

# --- 機械で固定する主張 ---------------------------------------------------- #
# (1) ゼロ点は「隣は綺麗・閉じ目は壊れる」という形で必ず壊れる。
assert r_chain["close"] > 8.0 * np.mean(seam_open), (
    f"閉じ目 {r_chain['close']:.3f} が隣接継ぎ目 {np.mean(seam_open):.3f} の "
    "8 倍に届かない —— ゼロ点が壊れていない(実験の設定が甘い)")
# (2) 閉ループ拘束・全ペア・大域最適化はどれも鎖より姿勢が良い。
for _nm, _r in (("閉ループ拘束", r_spread), ("全ペア", r_all), ("大域最適化", r_gn)):
    assert _r["pose_max"] < r_chain["pose_max"], f"{_nm} が鎖に勝てていない"
# (3) 大域最適化は閉ループ誤差をほぼ消す(鎖の 1/5 以下)。
assert r_gn["loop"] < 0.2 * r_chain["loop"], (
    f"大域最適化の閉ループ誤差 {r_gn['loop']:.3f} が鎖 {r_chain['loop']:.3f} の "
    "1/5 を切れていない")
# (4) ドリフトは N とともに伸びる。指数は 0.3 以上(伸びる)、1.3 以下(N より速くない)。
assert 0.30 <= SLOPE <= 1.30, f"ドリフト指数 {SLOPE:.3f} が想定域外"
assert np.mean(acc[64]) > 2.0 * np.mean(acc[4]), "N を 16 倍しても誤差が 2 倍未満"
# (5) 重なりを削ると 1 段が壊れる。
assert CLIFF_OV > 2.0, f"重なりの崖 {CLIFF_OV:.2f} 倍しか出ていない"
# (6) 繰り返し模様の共鳴周期で誤対応が増える。
assert REP_BAD_RES > REP_BAD_OFF, (
    f"共鳴周期の誤対応率 {REP_BAD_RES:.3f} が非共鳴 {REP_BAD_OFF:.3f} を超えない")
# (7) 焦点距離を間違えると一周の総回転角が動く(真値の f では 360 度に十分近い)。
assert abs(_f0[1] - 360.0) < 2.0, f"正しい f でも総回転角が {_f0[1]:.2f} 度"
assert FOC_YAW_SPAN > 10.0, f"f ±10 % で総回転角が {FOC_YAW_SPAN:.2f} 度しか動かない"
# (8) 残差は画面内で一様ではない。
assert EDGE_CENTER_RATIO > 1.05, "四隅と中央の残差が同じ —— 位置別に見る意味が無い"

print("\nPASS")

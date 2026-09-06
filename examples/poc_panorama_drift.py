# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_panorama_drift — 隣どうしを鎖でつなぐと、一周して元に戻れない。

    py -3.11 examples/poc_panorama_drift.py

【この PoC が答える問題】
パノラマ合成の教科書的な手順は「隣り合う 2 枚の対応から変換を求め、順に掛けて
いく」である。この手順で作った合成画像は **継ぎ目がどこも綺麗に見える**。
にもかかわらず一周して出発点に戻ると数十画素ずれている。理由は単純で、
**鎖は隣の誤差しか見ておらず、遠く離れたフレームどうしの整合を一度も測って
いない**から。誤差が消えたのではなく、まだ測っていない場所に押し出されただけ。

ここでは真値を自分で握る。既知の回転列で円筒パノラマから N 枚を切り出し、
360 度一周させて閉ループを作る。閉ループの真値は厳密に「ずれ 0」なので、
推定した鎖がどれだけ戻れないかを **画素で直接** 測れる。

そしてもう一つ。この repo には既にパノラマ用の実装が入っている(``mosaic`` /
``fit_transform`` / ``transforms`` / ``plane_sweep``)。どれも公開 API から届か
ない場所に埋まっている。**それらが本当に鎖(ゼロ点)を上回るのか** を第 4 章で
一つずつ測った。上回らなかったものは上回らなかったと数字で書いてある。

    EXTEND: 実写に差し替えるなら ``render_frame`` を捨てて自分の画像列を
    ``FRAMES`` に入れるだけでよい。ただし **真値が消える** ので「真の姿勢からの
    ずれ」は測れなくなる。残るのは (a) 閉ループ誤差(一周する撮り方をすれば
    真値なしで測れる唯一の絶対量)と (b) 継ぎ目の食い違い。焦点距離は自分で
    決めた値ではなくなるが、第 8 章のやり方で **非直交度が最小になる f を探す**
    と、真値を知らないまま較正できる(総回転角を 360 度に合わせるやり方は
    第 8 章の実測どおり分解能が足りない)。

【章立て】
 0. 舞台 —— 真値の作り方と往復検算
 1. 1 ペアの床 —— 対応点の精度と、そこから決まる 1 段あたりの誤差
 2. ゼロ点 = 隣接ペアの鎖 —— 継ぎ目は綺麗なのに一周して戻れない
 3. 系の比較(鎖 / 閉ループ拘束 / 全ペア / 大域最適化)
 4. ★ 埋もれている既存実装は、鎖を上回るのか
 5. ★ 崖 (a) 重なり率 80 → 10 %
 6. ★ 崖 (b) 枚数 N とドリフトの伸び —— 指数を実測で当てる
 7. ★ 崖 (c) 繰り返し模様の周期が 1 段の移動量に一致するとき
 8. ★ 崖 (d) 焦点距離の誤りが円筒に与える歪み
 9. 位置別の残差 —— 1 つの数字にまとめない
10. 速度と、測らなかったこと

【★ この PoC が出した道具の穴(op 本体は直していない)】
(a) **パノラマ関連のモジュールが丸ごとファサードにも op レジストリにも無い**。
    ``mosaic``(15 関数)/ ``fit_transform``(5 関数)/ ``plane_sweep.warp_by_plane``
    は ``import fullseye as fs`` の公開名にも ``fs.op`` の 885 op にも出て
    こない。``import mosaic`` と裸で書くしかなく、ファサードだけを見る利用者には
    「パノラマ合成が無いライブラリ」に見える。
(b) **``bundle_adjust_mosaic`` は束調整ではない**。中身は「画像 0 と直接対応の
    ある相手だけを個別に RANSAC する」ループで、同時最適化も残差の再配分も
    しない。画像 0 と直接の対応が無いフレームは **黙って単位行列のまま返る**。
    第 4 章で 24 枚のパノラマに掛けた実測を出す。
(c) **``gen_spherical_mosaic`` は球面で何もしない**。実体は
    ``return gen_projective_mosaic(...)`` の 1 行で、docstring の
    「球面パノラマ座標」に対応する処理が存在しない。
(d) **``proj_match_points_distortion_ransac`` は歪みを推定しない**。
    ``kappa = 0.0`` を足して返すだけなので、呼んだ側は「歪みは無かった」と
    読み違える。
(e) **``proj_match_points_ransac_guided`` の ``inliers`` は長さが違う**。
    誘導で間引いた後の部分集合に対するマスクを返すので、元の対応配列を
    そのマスクで添字づけすると黙って別の点を拾う(例外は出ない)。
(f) **2 つの DLT が同じ repo にあって、入力は同じ規約・出力は別の規約**。
    ``mosaic._homography_dlt`` は ``(row, col)`` を受け取って **(x, y) 用の H**
    を返し、``fit_transform.hom_vector_to_proj_hom_mat2d`` は ``(row, col)`` を
    受け取って **(row, col) 用の H** を返す。取り違えても例外は出ない。
    第 1 章で取り違えたときの誤差を実測した。
(g) **``mosaic._homography_dlt`` は点を正規化しない**。兄弟の
    ``fit_transform`` 側は Hartley 正規化つき。同じ対応点で誤差を並べた。
(h) **キーポイントに副画素がない**。``fs.match_keypoints`` が返すのは整数座標で、
    副画素補間の入口も無い。第 1 章で測る対応点誤差の床はこれで決まる。
(i) **純回転(3 自由度)のホモグラフィを当てはめる道具が無い**。あるのは
    8 自由度の一般ホモグラフィだけ。パノラマは並進が無いので 3 自由度で
    足りるのに、5 つ余分に自由度を使うぶんだけ毎段の誤差が増える。
    第 1 章でその差(**1 段あたり 4 倍**)を測った。この PoC は
    ``fs.rodrigues`` + ``scipy.least_squares`` で自前に書いた。
(j) **``optimize_pose_graph``(pose_graph.py)は回転だけの問題に使えない**。
    SE(3) 専用で並進を要求するため、純回転パノラマでは辺が定義できない。
    これもファサードに出ていない。
(k) **画像を円筒/正距円筒へ張る op が無い**。``tb_project_cylindrical`` /
    ``tb_project_spherical`` は名前に反して **3 次元点群 → 距離画像**
    (``fs.op`` の typed 表記が ``points -> image``)。画像 → 円筒の写像ではない。
(l) **``gen_projective_mosaic`` は後から描いた画像で上書きする**。重ね合わせも
    重み付き混合もしないので、**ずれているほど継ぎ目が「綺麗に」見える**
    (二重像が出ないから)。合成画像を見て品質を判断できない構造になっている。
(m) **``proj_match_points_ransac`` の戻り値は dict**。``np.asarray()`` に通すと
    ``shape == ()`` の 0 次元 object 配列になるので、配列を期待した呼び出し側は
    「空が返った」と誤読する。キーは ``H`` / ``inliers`` / ``num_inliers``。
"""
from __future__ import annotations

import time

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.optimize import least_squares

import fullseye as fs
# ★ 穴 (a): 以下 4 つはどれも fs ファサードにも fs.op にも出ていない
import fit_transform
import mosaic
import plane_sweep
import transforms

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

# ── 誤差はすべて画素で出す。「良い/悪い」の線は引かない ────────────────── #
GRID_XY = np.array([[x, y] for y in (8.0, CY, IMG_H - 9.0)
                    for x in (8.0, CX, IMG_W - 9.0)])     # 画面内 3x3 の見張り点
CORNERS_XY = np.array([[0.0, 0.0], [IMG_W - 1.0, 0.0],
                       [IMG_W - 1.0, IMG_H - 1.0], [0.0, IMG_H - 1.0]])
SWAP = np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])   # (x,y)<->(row,col)

MATCH_KW = dict(patch=11, ratio=0.85, min_distance=3, thresh_rel=0.002, max_n=600)
RANSAC_PX = 1.5
MIN_INLIER = 10


# ===========================================================================
# 0. 舞台
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

    純粋なパンではなく、俯仰 1.5 度・回頭 1.0 度の **周期的な揺れ** を重ねてある。
    手持ちの雲台は必ず揺れるので、1 自由度問題にすると易しすぎる。揺れは ``sin``
    なので theta = 0 と 2π で厳密に 0 に戻り、**閉ループの真値は厳密に単位行列**
    のまま保たれる(第 0 章で検算する)。
    """
    return (_ry(theta)
            @ _rx(np.deg2rad(1.5) * np.sin(theta))
            @ _rz(np.deg2rad(1.0) * np.sin(2.0 * theta)))


def make_panorama(rng, period_deg=37.0, motif=1.0, confetti=4200):
    """円筒パノラマを作る。**構造のあるものを必ず混ぜる**。

    4 種類を重ねてある。(1) 低周波の滑らかな地 —— ここには対応点が立たない、
    (2) 小さな四角の紙吹雪 —— 角がたくさん立ち、一つ一つ輝度が違うので
    descriptor が一意になる、(3) **直線の格子** —— 方位角は不等間隔にしてある。
    等間隔にすると格子そのものが繰り返し模様になり、第 7 章で調べたい「模様の
    周期」と混ざって原因が切り分けられなくなる、(4) **繰り返しグリフ** ——
    周期 ``period_deg`` で同じ形を並べる。これが第 7 章の崖の材料。
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
    """画素 (x, y) を、その姿勢で円筒パノラマ座標 (u, v) に写す。

    単位は「焦点距離 ``focal`` の画素」。既定は真の焦点距離なので **画像中心の
    1 画素 = パノラマの 1 画素**。誤差を画素で言うための共通の物差し。
    """
    f = TRUE_F if focal is None else focal
    p = np.atleast_2d(np.asarray(pts_xy, float))
    d = R_c2w @ (K_INV @ np.column_stack([p, np.ones(len(p))]).T)
    return np.column_stack([np.arctan2(d[0], d[2]) * f,
                            d[1] / np.hypot(d[0], d[2]) * f])


def uv_gap(uv_a, uv_b, focal=None):
    """パノラマ座標の差。u は円周なので巻き戻してから距離にする。"""
    f = TRUE_F if focal is None else focal
    du = uv_a[:, 0] - uv_b[:, 0]
    du = (du + np.pi * f) % (2.0 * np.pi * f) - np.pi * f
    return np.hypot(du, uv_a[:, 1] - uv_b[:, 1])


# ===========================================================================
# 推定の道具
# ===========================================================================
def dlt_existing(p1_xy, p2_xy):
    """既存 op ``fit_transform.hom_vector_to_proj_hom_mat2d`` を (x, y) で使う。

    この op の契約は ``(row, col)`` なので、点を入れ替えて呼び、返った H の
    行と列も入れ替えて (x, y) 用に戻す(★ 穴 f)。
    """
    Hrc = fit_transform.hom_vector_to_proj_hom_mat2d(p1_xy[:, ::-1], p2_xy[:, ::-1])
    Hxy = SWAP @ Hrc @ SWAP
    return Hxy / Hxy[2, 2]


def apply_h(Hm, pts_xy):
    p = np.atleast_2d(np.asarray(pts_xy, float))
    q = np.column_stack([p, np.ones(len(p))]) @ np.asarray(Hm, float).T
    return q[:, :2] / q[:, 2:3]


def true_homography(R_i, R_j):
    """真の相対ホモグラフィ(フレーム i の画素 → フレーム j の画素)。"""
    return K_TRUE @ R_j.T @ R_i @ K_INV


def h_to_relrot(Hm, focal=None):
    """ホモグラフィ → 相対回転 ``A = Q_j Q_i^T``(``Q`` は世界→カメラ)。

    純回転なら ``K^-1 H K`` はスケール倍の回転行列。焦点距離を間違えるとそう
    ならないので SVD で最寄りの回転へ落とし、**どれだけ回転から外れていたか**
    (特異値の広がり)も返す。第 8 章はこの値を読む。
    """
    Km = K_TRUE if focal is None else fs.intrinsic_matrix(focal, focal, CX, CY)
    A = np.linalg.inv(Km) @ np.asarray(Hm, float) @ Km
    U, S, Vt = np.linalg.svd(A)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        R = U @ np.diag([1.0, 1.0, -1.0]) @ Vt
    return R, float(S[0] / S[2] - 1.0)


def refine_relrot(A0, p1, p2):
    """★ 穴 (i): 純回転(3 自由度)で当てはめ直す。8 自由度の H を回転へ丸める
    より素性が良い —— 丸めた分が毎段の誤差になるのを避けられる。"""
    def res(x):
        return (apply_h(K_TRUE @ fs.rodrigues(x) @ K_INV, p1) - p2).ravel()
    sol = least_squares(res, fs.rotation_log(A0), xtol=1e-12, ftol=1e-12, max_nfev=40)
    return fs.rodrigues(sol.x)


def chain_rotations(rels, n):
    """ゼロ点 —— 隣接ペアの推定だけを鎖のように掛ける。"""
    Q = [np.eye(3)]
    for i in range(n - 1):
        Q.append(rels[(i, i + 1)] @ Q[-1])
    return Q


def spread_loop_error(Q, loop_rel, n):
    """閉ループ誤差を等分に配る素朴なやり方(1 次近似)。第 3 章で残差を測る。"""
    w = fs.rotation_log(loop_rel @ Q[-1])
    return [fs.rodrigues(-(i / n) * w) @ Q[i] for i in range(n)]


def rotation_average(n, edges):
    """相対回転の集合から各フレームの姿勢をまとめて解く(スペクトル法)。

    ブロック行列 ``M[j][i] = A_ij`` の上位 3 固有ベクトルが ``Q_i G`` を並べたもの
    になる(``G`` は共通の任意直交行列)。フレーム 0 で ``G`` を潰す。
    鎖と違って **辺を辿る順番が結果に影響しない** ——「どの経路で来たか」に
    依存しないことが、ドリフトが消える理由そのもの。
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
    spars = np.zeros((2 * sum(counts), 3 * (n - 1)))
    r0 = 0
    for (i, j), c in zip(keys, counts):
        for f in (i, j):
            if f > 0:
                spars[r0:r0 + 2 * c, 3 * (f - 1):3 * f] = 1
        r0 += 2 * c

    def residual(x):
        Q = [np.eye(3)] + [fs.rodrigues(x[3 * k:3 * k + 3]) for k in range(n - 1)]
        return np.concatenate([
            (apply_h(K_TRUE @ Q[j] @ Q[i].T @ K_INV, edge_pts[(i, j)]["p1"])
             - edge_pts[(i, j)]["p2"]).ravel() for (i, j) in keys])

    sol = least_squares(residual, x0, jac_sparsity=spars, method="trf",
                        xtol=1e-10, ftol=1e-10, max_nfev=60)
    return [np.eye(3)] + [fs.rodrigues(sol.x[3 * k:3 * k + 3]) for k in range(n - 1)]


def match_pair(img_i, img_j, seed):
    """2 枚から対応点を取り、RANSAC で外れ値を落として既存 DLT で当てはめる。

    戻り値 ``None`` は「この 2 枚は繋げなかった」。重なりが少ないと本当にそう
    なるので、失敗を握り潰さずそのまま上へ返す。
    """
    p1, p2 = fs.match_keypoints(img_i, img_j, **MATCH_KW)
    out = {"n_match": len(p1), "n_inlier": 0}
    if len(p1) < MIN_INLIER:
        return out
    r = mosaic.proj_match_points_ransac(p1[:, ::-1], p2[:, ::-1],
                                        thresh=RANSAC_PX, iters=400, seed=seed)
    inl = r["inliers"]
    out["n_inlier"] = int(inl.sum())
    if out["n_inlier"] < MIN_INLIER:
        return out
    a, b = p1[inl], p2[inl]
    H8 = dlt_existing(a, b)
    A8, nonrot = h_to_relrot(H8)
    out.update({"H": H8, "H_raw": r["H"], "p1": a, "p2": b, "ok": True,
                "A8": A8, "A3": refine_relrot(A8, a, b), "nonrot": nonrot})
    return out


# ── 誤差の測り方 ─────────────────────────────────────────────────────────── #
def pose_error_px(Q_est, R_true_list):
    """各フレームの真の姿勢からのずれ(画素)。画面内 3x3 の見張り点の平均。"""
    return np.asarray([uv_gap(pano_uv(Qe.T, GRID_XY), pano_uv(Rt, GRID_XY)).mean()
                       for Qe, Rt in zip(Q_est, R_true_list)])


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
    g = uv_gap(pano_uv(loop_R.T, CORNERS_XY), pano_uv(np.eye(3), CORNERS_XY))
    return float(g.mean()), float(g.max()), float(
        np.rad2deg(np.linalg.norm(fs.rotation_log(loop_R))))


def build_edges(n, max_gap, closed):
    """使うペアの一覧。``max_gap=1`` が鎖、2 以上で離れたフレームも使う。"""
    out = []
    for i in range(n):
        for g in range(1, max_gap + 1):
            j = i + g
            if j < n:
                out.append((i, j))
            elif closed:
                out.append((i, j % n))
    return out


def rule(title):
    print("\n" + "=" * 76)
    print(title)
    print("=" * 76)


# ===========================================================================
rule("0. 舞台 —— 真値の作り方と往復検算")
# ===========================================================================
rng = np.random.default_rng(20260906)
PAN = make_panorama(rng)
print(f"円筒パノラマ {H_PAN} x {W_PAN} px(焦点 {F_PAN:.1f} px 相当, 仰角 ±{ELEV_MAX_DEG:.0f} 度)")
print(f"カメラ {IMG_W} x {IMG_H} px, 水平画角 {FOV_X_DEG:.0f} 度, 焦点距離 {TRUE_F:.2f} px")

_Ra, _Rb = true_cam_to_world(0.0), true_cam_to_world(np.deg2rad(15.0))
_hp = apply_h(true_homography(_Ra, _Rb), GRID_XY)
_chk1 = uv_gap(pano_uv(_Ra, GRID_XY), pano_uv(_Rb, _hp)).max()
print(f"検算 1  ホモグラフィと円筒投影の往復              最大 {_chk1:.3e} px")

_n = 24
_Rtrue = [true_cam_to_world(2 * np.pi * i / _n) for i in range(_n)]
_rel = {(i, (i + 1) % _n): _Rtrue[(i + 1) % _n].T @ _Rtrue[i] for i in range(_n)}
_chk2 = loop_gap_px(_rel[(_n - 1, 0)] @ chain_rotations(_rel, _n)[-1])[0]
print(f"検算 2  真値だけで一周したときの閉ループ誤差      {_chk2:.3e} px")

# 検算 3: 既存の点変換 op / ワープ op が同じ H で同じ答えを出すか
_Ht = true_homography(_Ra, _Rb)
_Hrc = SWAP @ _Ht @ SWAP
_p_tr = np.array([transforms.projective_trans_point_2d(_Hrc, y, x)[::-1]
                  for x, y in GRID_XY])
_chk3 = np.abs(_p_tr - apply_h(_Ht, GRID_XY)).max()
print(f"検算 3  transforms.projective_trans_point_2d と一致  最大 {_chk3:.3e} px")
_im = render_frame(PAN, _Ra)
_wb = plane_sweep.warp_by_plane(_im, np.linalg.inv(_Ht), cval=np.nan)
_ref = render_frame(PAN, _Rb)
_m = np.isfinite(_wb)
_chk4 = float(np.abs(_wb[_m] - _ref[_m]).mean())
print(f"検算 4  plane_sweep.warp_by_plane の逆ワープ残差   平均 {_chk4:.4f} "
      f"(輝度 0-1, 有効 {_m.mean() * 100:.0f} %)")
assert _chk1 < 1e-8 and _chk2 < 1e-8 and _chk3 < 1e-9, "舞台の真値が閉じていない"
print("→ 真値は閉じている。以降の閉ループ誤差はすべて **推定の誤差** である。")
print("→ 既存の点変換 op とワープ op は使えた(規約さえ合わせれば)。")


# ===========================================================================
rule("1. 1 ペアの床 —— 対応点の精度と、1 段あたりの誤差")
# ===========================================================================
print("鎖の誤差はすべてここから積み上がる。まず 1 段の大きさを測る。")

N_LOOP = 24
STEP_DEG = 360.0 / N_LOOP
OVERLAP_LOOP = 1.0 - STEP_DEG / FOV_X_DEG
R_LOOP = [true_cam_to_world(2 * np.pi * i / N_LOOP) for i in range(N_LOOP)]
FRAMES = [render_frame(PAN, R, rng) for R in R_LOOP]
print(f"N = {N_LOOP} 枚, 1 段 {STEP_DEG:.1f} 度, 重なり率 {OVERLAP_LOOP * 100:.0f} %")

PAIRS_ADJ = build_edges(N_LOOP, 1, closed=True)
M_ADJ = {}
for (i, j) in PAIRS_ADJ:
    m = match_pair(FRAMES[i], FRAMES[j], seed=200 + i)
    assert m.get("ok"), f"ペア {i}-{j} が繋がらない"
    M_ADJ[(i, j)] = m

e8, e3, eraw, ebad, ce_all, ni_all, nr_all = [], [], [], [], [], [], []
for (i, j), m in M_ADJ.items():
    Ht = true_homography(R_LOOP[i], R_LOOP[j])
    ref = apply_h(Ht, GRID_XY)
    ce_all.append(np.linalg.norm(apply_h(Ht, m["p1"]) - m["p2"], axis=1))
    ni_all.append(m["n_inlier"])
    nr_all.append(m["nonrot"])
    e8.append(np.linalg.norm(apply_h(m["H"], GRID_XY) - ref, axis=1).mean())
    e3.append(np.linalg.norm(apply_h(K_TRUE @ m["A3"] @ K_INV, GRID_XY) - ref,
                             axis=1).mean())
    eraw.append(np.linalg.norm(apply_h(m["H_raw"], GRID_XY) - ref, axis=1).mean())
    # 規約を取り違えたらどうなるか(★ 穴 f)
    Hbad = fit_transform.hom_vector_to_proj_hom_mat2d(m["p1"][:, ::-1], m["p2"][:, ::-1])
    ebad.append(np.linalg.norm(apply_h(Hbad, GRID_XY) - ref, axis=1).mean())

corr = np.concatenate(ce_all)
E8, E3, ERAW, EBAD = map(lambda v: float(np.mean(v)), (e8, e3, eraw, ebad))
PAIR_MEAN, PAIR_MAX = float(np.mean(e3)), float(np.max(e3))
print(f"\n対応点: 1 ペアあたり内点 {np.mean(ni_all):.1f} 個、真の誤差 中央値 "
      f"{np.median(corr):.3f} px / 90 % 点 {np.percentile(corr, 90):.3f} px")
print(f"\n{'当てはめ方':<44}{'1 段の誤差(px)':>16}")
print("-" * 62)
print(f"{'(A) mosaic._homography_dlt  8 dof / 正規化なし':<44}{ERAW:>16.4f}")
print(f"{'(B) fit_transform 既存 DLT  8 dof / 正規化あり':<44}{E8:>16.4f}")
print(f"{'(C) 純回転 3 dof(自前・穴 i)':<44}{E3:>16.4f}")
print(f"{'(X) 既存 DLT の返り値の規約を取り違えた場合':<44}{EBAD:>16.1f}")
print("-" * 62)
print(f"★ 穴 (g): 正規化の有無で {ERAW / E8:.2f} 倍。(A) と (B) は同じ repo にある。")
print(f"★ 穴 (i): 8 dof を回転へ丸めるより 3 dof で当てはめるほうが "
      f"{E8 / E3:.1f} 倍良い。")
print(f"   H から回転への丸め残り(特異値の広がり)は平均 {np.mean(nr_all):.2e}、")
print(f"   画像端では {np.mean(nr_all) * IMG_W / 2:.2f} px に相当する。")
print(f"★ 穴 (f): (row,col) 用の H を (x,y) に使うと {EBAD:.0f} px ずれる。"
      f" 例外は出ない。")
print(f"★ 穴 (h): 対応点は整数座標(副画素補間の入口が無い)。ここが誤差の床。")
print(f"\n→ 以降のゼロ点は **最良の 1 ペア推定**(C, 1 段 {PAIR_MEAN:.3f} px)で作る。")
print("   弱い当てはめでゼロ点を作ると、鎖に勝つのが簡単すぎる。")


# ===========================================================================
rule("2. ゼロ点 = 隣接ペアの鎖 —— 継ぎ目は綺麗なのに一周して戻れない")
# ===========================================================================
REL3 = {k: m["A3"] for k, m in M_ADJ.items()}
Q_CHAIN = chain_rotations({k: v for k, v in REL3.items() if k[1] == k[0] + 1}, N_LOOP)
LOOP_R = REL3[(N_LOOP - 1, 0)] @ Q_CHAIN[-1]
lg_mean, lg_max, lg_deg = loop_gap_px(LOOP_R)
seam_chain = seam_error_px(Q_CHAIN, R_LOOP, PAIRS_ADJ)
SEAM_OPEN = float(np.mean([v for k, v in seam_chain.items() if k != (N_LOOP - 1, 0)]))
SEAM_CLOSE = seam_chain[(N_LOOP - 1, 0)]
pe_chain = pose_error_px(Q_CHAIN, R_LOOP)

# 生ホモグラフィをそのまま掛ける、いちばん素朴な鎖
Hacc = np.eye(3)
for i in range(N_LOOP - 1):
    Hacc = M_ADJ[(i, i + 1)]["H"] @ Hacc
H_LOOP_RAW = M_ADJ[(N_LOOP - 1, 0)]["H"] @ Hacc
H_LOOP_RAW /= H_LOOP_RAW[2, 2]
RAW_LOOP_PX = float(np.linalg.norm(apply_h(H_LOOP_RAW, CORNERS_XY) - CORNERS_XY,
                                   axis=1).mean())

print(f"隣り合う継ぎ目 {N_LOOP - 1} 本のずれ            平均 {SEAM_OPEN:.3f} px")
print(f"最後に閉じる継ぎ目 ({N_LOOP - 1}-0) のずれ         {SEAM_CLOSE:.3f} px")
print(f"閉ループ誤差(四隅)                    平均 {lg_mean:.3f} px "
      f"/ 最悪 {lg_max:.3f} px(残る回転 {lg_deg:.3f} 度)")
print(f"真の姿勢からのずれ                      平均 {pe_chain.mean():.3f} px "
      f"/ 最悪 {pe_chain.max():.3f} px(フレーム {int(pe_chain.argmax())})")
print(f"生ホモグラフィをそのまま掛けた鎖の閉ループ  {RAW_LOOP_PX:.3f} px "
      f"(回転に丸める鎖の {RAW_LOOP_PX / lg_mean:.1f} 倍)")
print(f"\n→ 隣どうしは {SEAM_OPEN:.2f} px で合っているのに、閉じる 1 本だけ "
      f"{SEAM_CLOSE:.1f} px 開く({SEAM_CLOSE / SEAM_OPEN:.0f} 倍)。")
print("   誤差は消えていない。**まだ測っていない 1 本に全部押し出されている**。")
print("   合成画像を眺めて品質を判断すると、この崖は最後まで見えない —— しかも")
print("   ★ 穴 (l) のとおり既存の合成は後勝ちの上書きなので二重像すら出ない。")


# ===========================================================================
rule("3. 系の比較 —— 何を測る系にすると誤差が戻ってくるか")
# ===========================================================================
MAX_GAP = 2
M_ALL = dict(M_ADJ)
n_far_fail = 0
for (i, j) in build_edges(N_LOOP, MAX_GAP, closed=True):
    if (i, j) in M_ALL:
        continue
    m = match_pair(FRAMES[i], FRAMES[j], seed=300 + i * 7 + j)
    if not m.get("ok"):
        n_far_fail += 1
        continue
    M_ALL[(i, j)] = m
REL_ALL = {k: m["A3"] for k, m in M_ALL.items()}
print(f"距離 {MAX_GAP} までのペアを追加: 使えた辺 {len(REL_ALL)} 本 "
      f"(繋がらなかった {n_far_fail} 本)。距離 3 は {STEP_DEG * 3:.0f} 度 = 画角と")
print("同じで重なりが無いため、そもそも辺にならない。")

Q_SPREAD = spread_loop_error(Q_CHAIN, REL3[(N_LOOP - 1, 0)], N_LOOP)
Q_CYCLE = rotation_average(N_LOOP, REL3)
Q_ALLP = rotation_average(N_LOOP, REL_ALL)
Q_GN = global_refine(Q_CHAIN, M_ALL, N_LOOP)

SYSTEMS = [
    ("0 生 H の鎖", None, len(REL3)),
    ("1 鎖(回転・ゼロ点)", Q_CHAIN, len(REL3)),
    ("2 閉ループ誤差を等分", Q_SPREAD, len(REL3)),
    ("3 閉ループ拘束(厳密)", Q_CYCLE, len(REL3)),
    (f"4 全ペア(距離<={MAX_GAP})", Q_ALLP, len(REL_ALL)),
    ("5 大域最適化(GN)", Q_GN, len(REL_ALL)),
]
print(f"\n{'系':<24}{'辺':>4}{'姿勢平均':>10}{'姿勢最悪':>10}"
      f"{'継ぎ目平均':>12}{'閉じ目':>9}{'閉ループ':>10}")
print("-" * 79)
RESULT = {}
for name, Q, n_edge in SYSTEMS:
    if Q is None:
        print(f"{name:<24}{n_edge:>4}{'—':>10}{'—':>10}{'—':>12}{'—':>9}"
              f"{RAW_LOOP_PX:>10.3f}")
        RESULT[name] = dict(loop=RAW_LOOP_PX)
        continue
    pe = pose_error_px(Q, R_LOOP)
    sm = seam_error_px(Q, R_LOOP, PAIRS_ADJ)
    close = sm[(N_LOOP - 1, 0)]
    others = float(np.mean([v for k, v in sm.items() if k != (N_LOOP - 1, 0)]))
    lg = uv_gap(pano_uv((REL3[(N_LOOP - 1, 0)] @ Q[-1]).T, CORNERS_XY),
                pano_uv(np.eye(3), CORNERS_XY)).mean()
    RESULT[name] = dict(pose_mean=pe.mean(), pose_max=pe.max(),
                        seam=others, close=close, loop=float(lg))
    print(f"{name:<24}{n_edge:>4}{pe.mean():>10.3f}{pe.max():>10.3f}"
          f"{others:>12.3f}{close:>9.3f}{lg:>10.3f}")
print("-" * 79)
print("単位はすべて画素。「閉じ目」= 最後に閉じる 1 本の継ぎ目、「閉ループ」= 推定した")
print("相対回転で一周したときに戻れない量。")
r_chain, r_cyc = RESULT["1 鎖(回転・ゼロ点)"], RESULT["3 閉ループ拘束(厳密)"]
r_spr, r_all = RESULT["2 閉ループ誤差を等分"], RESULT[f"4 全ペア(距離<={MAX_GAP})"]
r_gn = RESULT["5 大域最適化(GN)"]
print(f"\n→ 系 2(log を等分に配る素朴なやり方)は 1 次近似にすぎず、閉ループ誤差が")
print(f"   {r_spr['loop']:.2f} px 残る。回転は可換でないので等分では厳密に閉じない。")
print(f"→ 系 3 は同じ辺だけで閉ループ誤差を {r_cyc['loop']:.3f} px まで落とす。")
print(f"   **新しい観測を 1 つも足さずに** 姿勢最悪が "
      f"{r_chain['pose_max']:.2f} → {r_cyc['pose_max']:.2f} px。")
print(f"   足りなかったのは情報ではなく「経路に依存しない解き方」だった。")
print(f"→ 系 4・5 は一周しなくても効く。閉ループ拘束は全ペアの特殊例である。")


# ===========================================================================
rule("4. ★ 埋もれている既存実装は、鎖(ゼロ点)を上回るのか")
# ===========================================================================
print("repo にあるパノラマ実装を、上と同じ物差しで測る。使えるかどうかを")
print("docstring ではなく数字で決める。")

# --- (1) proj_match_points_ransac の戻り値の形 ----------------------------- #
_r = mosaic.proj_match_points_ransac(M_ADJ[(0, 1)]["p1"][:, ::-1],
                                     M_ADJ[(0, 1)]["p2"][:, ::-1], thresh=1.5)
print(f"\n(1) proj_match_points_ransac の戻り値: {type(_r).__name__} "
      f"keys={list(_r.keys())}")
print(f"    np.asarray(戻り値).shape = {np.asarray(_r).shape}  "
      "← dict を 0 次元 object 配列に包んだ形。")
print("    配列を期待して asarray した呼び出し側は「空が返った」と誤読する(穴 m)。")
print(f"    中身は使えた: H は 3x3、inliers は長さ {len(_r['inliers'])} の bool、"
      f"内点 {_r['num_inliers']} 個。")

# --- (2) ransac_guided の inliers の長さ ----------------------------------- #
_g = mosaic.proj_match_points_ransac_guided(
    M_ADJ[(0, 1)]["p1"][:, ::-1], M_ADJ[(0, 1)]["p2"][:, ::-1],
    guide_H=np.eye(3), thresh=1.5)
print(f"\n(2) proj_match_points_ransac_guided: 入力 {len(M_ADJ[(0, 1)]['p1'])} 点 → "
      f"inliers の長さ {len(_g['inliers'])}")
print("    長さが入力と違う(穴 e)。元の対応配列をこのマスクで添字づけすると")
print("    黙って別の点を拾う。例外は出ない。")

# --- (3) bundle_adjust_mosaic -------------------------------------------- #
matches = {(i, j): (m["p1"][:, ::-1], m["p2"][:, ::-1]) for (i, j), m in M_ALL.items()}
t0 = time.perf_counter()
Hs_ba = mosaic.bundle_adjust_mosaic(FRAMES, matches, seed=0)
t_ba = time.perf_counter() - t0
n_identity = sum(1 for Hm in Hs_ba if np.allclose(Hm, np.eye(3)))
Q_BA = []
for Hm in Hs_ba:
    A, _ = h_to_relrot(np.asarray(Hm, float))
    Q_BA.append(A.T)                       # H_j: 画像 j → 画像 0 なので転置で Q_j
pe_ba = pose_error_px(Q_BA, R_LOOP)
sm_ba = seam_error_px(Q_BA, R_LOOP, PAIRS_ADJ)
print(f"\n(3) bundle_adjust_mosaic({N_LOOP} 枚, 辺 {len(matches)} 本, {t_ba * 1e3:.1f} ms)")
print(f"    単位行列のまま返ったフレーム   {n_identity} / {N_LOOP} 枚")
print(f"    姿勢誤差 平均 {pe_ba.mean():.1f} px / 最悪 {pe_ba.max():.1f} px  "
      f"(鎖は {pe_chain.mean():.1f} / {pe_chain.max():.1f})")
print(f"    継ぎ目 平均 {np.mean(list(sm_ba.values())):.1f} px  "
      f"(鎖は {SEAM_OPEN:.2f})")
print("    → **鎖に上回れなかった**。原因は精度ではなく構造:")
print("      実装は matches の (0, j) / (j, 0) しか読まない。360 度パノラマでは")
print("      画像 0 と重なるのは前後 2 枚だけなので、残りは触られずに単位行列で")
print(f"      返る。名前は束調整だが、同時最適化も残差の再配分もしない(穴 b)。")

# --- (4) gen_projective_mosaic / gen_bundle_adjusted_mosaic --------------- #
SUB = [0, 1, 2, 3, 4]                       # 60 度ぶん(平面キャンバスに収まる範囲)
H_true_sub, H_est_sub = [np.eye(3)], [np.eye(3)]
for i in SUB[1:]:
    H_true_sub.append(true_homography(R_LOOP[i], R_LOOP[0]))
    H_est_sub.append(K_TRUE @ Q_CHAIN[0] @ Q_CHAIN[i].T @ K_INV)
sub_imgs = [FRAMES[i] for i in SUB]
t0 = time.perf_counter()
mos_true = mosaic.gen_projective_mosaic(sub_imgs, H_true_sub, out_shape=(260, 460))
mos_est = mosaic.gen_projective_mosaic(sub_imgs, H_est_sub, out_shape=(260, 460))
t_mos = time.perf_counter() - t0
mos_ba = mosaic.gen_bundle_adjusted_mosaic(sub_imgs, {k: v for k, v in matches.items()
                                                      if k[0] in SUB and k[1] in SUB},
                                           out_shape=(260, 460))
msk = (mos_true != 0) & (mos_est != 0)
mskb = (mos_true != 0) & (mos_ba != 0)
print(f"\n(4) gen_projective_mosaic(5 枚 60 度, {t_mos * 1e3:.0f} ms/2 枚分)")
print(f"    真の H で合成 vs 鎖の H で合成   平均 |差| {np.abs(mos_true - mos_est)[msk].mean():.4f} "
      f"/ 最大 {np.abs(mos_true - mos_est)[msk].max():.3f}(輝度 0-1)")
print(f"    真の H で合成 vs bundle_adjust   平均 |差| {np.abs(mos_true - mos_ba)[mskb].mean():.4f} "
      f"/ 最大 {np.abs(mos_true - mos_ba)[mskb].max():.3f}")
print("    → 合成そのものは動く。ただし ★ 穴 (l): ``_warp_into`` は後から描いた")
print("      画像で上書きするだけで混合しない。ずれていても二重像が出ないので、")
print("      **合成画像を見てもずれ量が分からない**。上の数字は真の合成と引き算")
print("      して初めて出る。")
print("    → 平面キャンバスなので 180 度を超えるパノラマは原理的に張れない")
print("      (24 枚 360 度をそのまま渡すと無限遠へ飛ぶ)。円筒/球面へ張る op は")
print("      無い(穴 c, k)。")

# --- (5) fit_transform / plane_sweep の評価まとめ -------------------------- #
print(f"\n(5) 使えた既存実装(この PoC が本番で使っているもの):")
print(f"    fit_transform.hom_vector_to_proj_hom_mat2d  1 段 {E8:.4f} px "
      f"—— 正規化なしの mosaic 版({ERAW:.4f} px)より良い。第 1-9 章で採用。")
print(f"    transforms.projective_trans_point_2d        自前と一致 {_chk3:.1e} px")
print(f"    plane_sweep.warp_by_plane                   逆ワープ残差 {_chk4:.4f}")
print(f"    mosaic.proj_match_points_ransac             外れ値除去に採用(全章)")
BA_BEATS_CHAIN = bool(pe_ba.max() < pe_chain.max())
print(f"\n【判定】埋もれた実装のうち、**鎖(ゼロ点)を上回ったものは無かった**。")
print(f"        bundle_adjust_mosaic は姿勢最悪 {pe_ba.max():.1f} px で、")
print(f"        ゼロ点 {pe_chain.max():.1f} px の {pe_ba.max() / pe_chain.max():.0f} 倍悪い。")
print(f"        一方で「部品」(DLT・RANSAC・点変換・ワープ)は 4 つとも使えた。")
print(f"        足りないのは部品ではなく、**部品を束ねる大域最適化**である。")


# ===========================================================================
rule("5. ★ 崖 (a) 重なり率 80 → 10 %")
# ===========================================================================
print("重なりを削ると 2 つのことが同時に起きる: 対応点が減る、対応点が画面の端に")
print("片寄る。後者のほうが効く —— 狭い帯だけで決めた変換は帯の外で外挿になる。")
print(f"\n{'重なり':>7}{'1段(度)':>9}{'対応':>6}{'内点':>6}"
      f"{'1段の誤差':>11}{'鎖の終端':>11}{'判定':>14}")
print("-" * 66)
N_OV = 8
ov_rows = []
for ov in (0.80, 0.60, 0.40, 0.25, 0.15, 0.10):
    step = np.deg2rad(FOV_X_DEG * (1.0 - ov))
    Rt = [true_cam_to_world(step * i) for i in range(N_OV)]
    fr = [render_frame(PAN, R, rng) for R in Rt]
    rels, e1, nm, ni, dead = {}, [], [], [], 0
    for i in range(N_OV - 1):
        m = match_pair(fr[i], fr[i + 1], seed=400 + i)
        nm.append(m["n_match"])
        ni.append(m["n_inlier"])
        if not m.get("ok"):
            rels[(i, i + 1)] = np.eye(3)
            dead += 1
            continue
        Ht = true_homography(Rt[i], Rt[i + 1])
        e1.append(float(np.linalg.norm(apply_h(K_TRUE @ m["A3"] @ K_INV, GRID_XY)
                                       - apply_h(Ht, GRID_XY), axis=1).mean()))
        rels[(i, i + 1)] = m["A3"]
    pe = pose_error_px(chain_rotations(rels, N_OV), Rt)
    e1m = float(np.mean(e1)) if e1 else float("nan")
    verdict = "全ペア成立" if dead == 0 else f"{dead}/{N_OV - 1} 本が切断"
    print(f"{ov * 100:>6.0f}%{np.rad2deg(step):>9.1f}{np.mean(nm):>6.0f}"
          f"{np.mean(ni):>6.0f}{e1m:>11.3f}{pe[-1]:>11.2f}{verdict:>14}")
    ov_rows.append((ov, e1m, float(pe[-1]), dead))
print("-" * 66)
_ok = [r for r in ov_rows if r[3] == 0]
CLIFF_OV = _ok[-1][1] / _ok[0][1]
CLIFF_OV_AT = _ok[-1][0]
_dead_from = min([r[0] for r in ov_rows if r[3] > 0], default=None)
print(f"→ 重なり 80 % → {CLIFF_OV_AT * 100:.0f} % で 1 段の誤差が {CLIFF_OV:.1f} 倍。")
if _dead_from is not None:
    print(f"→ 重なり {_dead_from * 100:.0f} % 以下では鎖が **切れる**。切れた辺を単位行列で")
    print("   埋めた結果が「鎖の終端」列。切断は誤差ではなく破綻なので、平均を取る")
    print("   意味が無い —— だから本数を別列で出している。")


# ===========================================================================
rule("6. ★ 崖 (b) 枚数 N とドリフトの伸び —— 指数を実測で当てる")
# ===========================================================================
print("理屈の予想: 1 段の誤差が偏りのない独立な雑音なら、鎖はランダムウォークで")
print("誤差 ∝ √N(指数 0.5)。1 段に系統的な偏りがあれば ∝ N(指数 1.0)。")
print("どちらなのかは **測らないと分からない**。8 本の別々の場面で測る。")

N_LIST = [4, 8, 16, 32, 64]
STEP_SWEEP_DEG = 5.0                     # 64 枚で 315 度 —— 一周させない(巻き戻り回避)
N_TRIAL = 8
acc = {n: [] for n in N_LIST}
bias_yaw = []
for t in range(N_TRIAL):
    r_t = np.random.default_rng(9000 + t)
    pan_t = make_panorama(r_t, period_deg=37.0 + 3.0 * t)
    Rt = [true_cam_to_world(np.deg2rad(STEP_SWEEP_DEG) * i) for i in range(max(N_LIST))]
    fr = [render_frame(pan_t, R, r_t) for R in Rt]
    rels = {}
    for i in range(max(N_LIST) - 1):
        m = match_pair(fr[i], fr[i + 1], seed=500 + i)
        rels[(i, i + 1)] = m["A3"] if m.get("ok") else np.eye(3)
        if m.get("ok"):
            bias_yaw.append(fs.rotation_log(m["A3"] @ (Rt[i + 1].T @ Rt[i]).T)[1])
    pe = pose_error_px(chain_rotations(rels, max(N_LIST)), Rt)
    for n in N_LIST:
        acc[n].append(pe[n - 1])

print(f"\n{'N':>4}{'終端のずれ 平均':>18}{'中央値':>10}{'最悪の試行':>12}")
print("-" * 46)
for n in N_LIST:
    v = np.asarray(acc[n])
    print(f"{n:>4}{v.mean():>18.3f}{np.median(v):>10.3f}{v.max():>12.3f}")
print("-" * 46)
SLOPE = float(np.polyfit(np.log(np.asarray(N_LIST, float)),
                         np.log(np.asarray([np.mean(acc[n]) for n in N_LIST])), 1)[0])
bias_yaw = np.asarray(bias_yaw)
b_px, s_px = abs(bias_yaw.mean()) * TRUE_F, bias_yaw.std() * TRUE_F
print(f"log-log の傾き(実測)               {SLOPE:.3f}")
print(f"1 段の方位角誤差: 偏り {bias_yaw.mean() * 1e3:+.4f} mrad ({b_px:+.4f} px) / "
      f"ばらつき {bias_yaw.std() * 1e3:.4f} mrad ({s_px:.4f} px)")
print(f"偏り / ばらつき                      {abs(bias_yaw.mean()) / bias_yaw.std():.3f}")
print(f"N = 64 の内訳予想: 偏りぶん {b_px * 64:.2f} px + "
      f"ランダムウォークぶん {s_px * np.sqrt(64):.2f} px  → 実測 {np.mean(acc[64]):.2f} px")
if SLOPE < 0.72:
    print("→ 指数は 0.5 側。1 段の誤差はほぼ偏りが無く、ドリフトはランダムウォーク。")
    print("   予想と合った。ただしこれは **合成したデータだから** である。実写では")
    print("   焦点距離のずれ(第 8 章)や露出変化が偏りを作り、指数は 1 に寄る。")
else:
    print("→ 指数は 1 側。1 段に系統的な偏りがある(上の偏りの行を見よ)。")
    print("   ランダムウォークだという予想は外れた。枚数を減らしても √N でしか")
    print("   減らないという見積りは使えない —— 偏りの原因を潰すほうが効く。")
print("   どちらにせよ **N を増やすと必ず伸びる**。鎖に上限は無い。")


# ===========================================================================
rule("7. ★ 崖 (c) 繰り返し模様の周期が 1 段の移動量に一致するとき")
# ===========================================================================
STEP7 = 15.0
SHIFT_PX = TRUE_F * np.tan(np.deg2rad(STEP7))
print(f"1 段 {STEP7:.0f} 度 = 画像中心で {SHIFT_PX:.1f} px の移動。模様の周期がこの移動量の")
print("整数倍に近いと、descriptor は **隣の繰り返し** と区別できない。共鳴する周期は")
print(f"{STEP7:.0f} 度 と その半分 {STEP7 / 2:.1f} 度。")
print(f"\n{'周期(度)':>10}{'周期(px)':>10}{'対応':>6}{'誤対応率':>10}"
      f"{'内点':>6}{'1段の誤差':>11}{'6枚の鎖 最悪':>14}")
print("-" * 68)
N7 = 6
rep_rows = []
for per in (6.0, 7.5, 9.0, 12.0, 15.0, 18.0, 22.0, 30.0):
    r7 = np.random.default_rng(4242)
    pan7 = make_panorama(r7, period_deg=per, motif=1.0)
    Rt = [true_cam_to_world(np.deg2rad(STEP7) * i) for i in range(N7)]
    fr = [render_frame(pan7, R, r7) for R in Rt]
    rels, bad, tot, e1, nm, ni = {}, 0, 0, [], [], []
    for i in range(N7 - 1):
        p1, p2 = fs.match_keypoints(fr[i], fr[i + 1], **MATCH_KW)
        Ht = true_homography(Rt[i], Rt[i + 1])
        err = np.linalg.norm(apply_h(Ht, p1) - p2, axis=1)
        bad += int((err > 3.0).sum())
        tot += len(err)
        m = match_pair(fr[i], fr[i + 1], seed=600 + i)
        nm.append(m["n_match"])
        ni.append(m["n_inlier"])
        if not m.get("ok"):
            rels[(i, i + 1)] = np.eye(3)
            continue
        e1.append(float(np.linalg.norm(apply_h(K_TRUE @ m["A3"] @ K_INV, GRID_XY)
                                       - apply_h(Ht, GRID_XY), axis=1).mean()))
        rels[(i, i + 1)] = m["A3"]
    pe = pose_error_px(chain_rotations(rels, N7), Rt)
    frac = bad / max(tot, 1)
    print(f"{per:>10.1f}{np.deg2rad(per) * TRUE_F:>10.1f}{np.mean(nm):>6.0f}"
          f"{frac * 100:>9.1f}%{np.mean(ni):>6.0f}"
          f"{(np.mean(e1) if e1 else float('nan')):>11.3f}{pe.max():>14.3f}")
    rep_rows.append((per, frac, float(np.mean(e1)) if e1 else float("nan"),
                     float(pe.max())))
print("-" * 68)
_res = [r for r in rep_rows if abs(r[0] - 15.0) < 0.1 or abs(r[0] - 7.5) < 0.1]
_off = [r for r in rep_rows if r not in _res]
REP_BAD_RES = float(max(r[1] for r in _res))
REP_BAD_OFF = float(np.median([r[1] for r in _off]))
REP_ERR_RES = float(max(r[2] for r in _res))
REP_ERR_OFF = float(np.median([r[2] for r in _off]))
print(f"→ 共鳴する周期(7.5 / 15 度)の誤対応率 最大 {REP_BAD_RES * 100:.1f} %、")
print(f"   外れた周期の中央値 {REP_BAD_OFF * 100:.1f} %。1 段の誤差は "
      f"{REP_ERR_OFF:.3f} → {REP_ERR_RES:.3f} px。")
print("★ 誤対応率が上がっても RANSAC が吸収してしまうことがある。「内点が多い」は")
print("   正しさの証拠にならない —— 誤対応どうしが同じ嘘のホモグラフィで整合すると、")
print("   内点だけが増えて誤差も増える。だから上の表は内点と誤差を並べてある。")


# ===========================================================================
rule("8. ★ 崖 (d) 焦点距離の誤りが円筒に与える歪み")
# ===========================================================================
print("ホモグラフィから回転を取り出すには焦点距離が要る。f を間違えると K^-1 H K は")
print("回転行列でなくなる。SVD で最寄りの回転に丸めれば計算は通るが、**丸めた分が")
print("毎段の偏りになって積み上がる**。第 6 章で言った「偏りがあれば指数は 1」の実例。")
print("\n(i) 雑音を消して f の誤りだけを見る —— 真のホモグラフィを誤った f で分解する")
print(f"\n{'f 誤差':>8}{'f (px)':>9}{'回転からの外れ':>16}{'一周の総回転(度)':>18}"
      f"{'仰角ドリフト':>14}{'閉ループ':>10}")
print("-" * 76)
foc_rows = []
H_TRUE_ADJ = {(i, j): true_homography(R_LOOP[i], R_LOOP[j]) for (i, j) in PAIRS_ADJ}
for e in (-0.10, -0.05, -0.02, 0.0, 0.02, 0.05, 0.10):
    f_use = TRUE_F * (1.0 + e)
    rels, nonrot, yaw = {}, [], 0.0
    for (i, j) in PAIRS_ADJ:
        A, s = h_to_relrot(H_TRUE_ADJ[(i, j)], focal=f_use)
        rels[(i, j)] = A
        nonrot.append(s)
        yaw += abs(fs.rotation_log(A)[1])
    Q = chain_rotations({k: v for k, v in rels.items() if k[1] == k[0] + 1}, N_LOOP)
    elev = max(abs((Qi.T @ np.array([0.0, 0.0, 1.0]))[1]
                   / np.hypot(*(Qi.T @ np.array([0.0, 0.0, 1.0]))[[0, 2]])) * TRUE_F
               for Qi in Q)
    lg = loop_gap_px(rels[(N_LOOP - 1, 0)] @ Q[-1])[0]
    print(f"{e * 100:>+7.0f}%{f_use:>9.2f}{np.mean(nonrot):>16.3e}"
          f"{np.rad2deg(yaw):>18.3f}{elev:>13.2f}px{lg:>10.3f}")
    foc_rows.append((e, float(np.mean(nonrot)), np.rad2deg(yaw), elev, lg))
print("-" * 76)
_f0 = [r for r in foc_rows if r[0] == 0.0][0]
_fp = [r for r in foc_rows if abs(r[0] - 0.10) < 1e-9][0]
_fm = [r for r in foc_rows if abs(r[0] + 0.10) < 1e-9][0]
FOC_LOOP_SPAN = max(_fp[4], _fm[4])
print(f"→ 雑音ゼロでも f を ±10 % 間違えると閉ループ誤差が {FOC_LOOP_SPAN:.1f} px 出る")
print(f"   (正しい f では {_f0[4]:.1e} px)。これは雑音由来ではなく **偏り** なので、")
print(f"   枚数を増やしても平均で消えない。仰角ドリフトは水平線が弓なりに曲がる量で、")
print(f"   最大 {max(_fp[3], _fm[3]):.1f} px。円筒に張ったときの「うねり」の正体。")
print(f"→ 一周の総回転角は {_fm[2]:.1f} 〜 {_fp[2]:.1f} 度(真値 360)。**分解能が足りない**")
print(f"   —— ±10 % の f 誤差で {abs(_fp[2] - _fm[2]):.2f} 度しか動かないので、")
print("   総回転角を 360 度に合わせるやり方では f を較正できない。")

print("\n(ii) 実際の推定 H で同じことをする —— 非直交度の最小から f を回収できるか")
grid = np.linspace(0.80, 1.25, 19)
curve = []
for g in grid:
    s = [h_to_relrot(M_ADJ[k]["H"], focal=TRUE_F * g)[1] for k in PAIRS_ADJ]
    curve.append(float(np.mean(s)))
curve = np.asarray(curve)
kmin = int(curve.argmin())
lo, hi = max(kmin - 1, 0), min(kmin + 2, len(grid))
co = np.polyfit(grid[lo:hi], curve[lo:hi], 2)
F_HAT_RATIO = float(-co[1] / (2.0 * co[0])) if len(grid[lo:hi]) == 3 else float(grid[kmin])
print(f"    非直交度が最小になる f / 真の f = {F_HAT_RATIO:.4f} "
      f"(回収した f = {TRUE_F * F_HAT_RATIO:.2f} px, 真値 {TRUE_F:.2f} px, "
      f"誤差 {abs(F_HAT_RATIO - 1) * 100:.1f} %)")
print(f"    格子 {grid[0]:.2f}〜{grid[-1]:.2f} で非直交度 "
      f"{curve.min():.3e}〜{curve.max():.3e}(谷の深さ {curve.max() / curve.min():.1f} 倍)")
print("    → 真値を知らなくても f が %.0f %% 以内で決まる。実写ではこちらを使う。"
      % (abs(F_HAT_RATIO - 1) * 100 + 0.5))


# ===========================================================================
rule("9. 位置別の残差 —— 1 つの数字にまとめない")
# ===========================================================================
print("同じ「平均 0.4 px」でも、真ん中が合っていて四隅が開いているのと、全面が一様に")
print("ずれているのとでは合成画像の見え方がまるで違う。")
cells8 = np.zeros(9)
cells3 = np.zeros(9)
for (i, j), m in M_ADJ.items():
    ref = apply_h(true_homography(R_LOOP[i], R_LOOP[j]), GRID_XY)
    cells8 += np.linalg.norm(apply_h(m["H"], GRID_XY) - ref, axis=1)
    cells3 += np.linalg.norm(apply_h(K_TRUE @ m["A3"] @ K_INV, GRID_XY) - ref, axis=1)
cells8 /= N_LOOP
cells3 /= N_LOOP
print("\n1 ペアあたりの残差(px)を画面内 3x3 で分けたもの:")
print(f"{'':>6}{'8 dof(既存 DLT)':>26}    {'3 dof(純回転)':>24}")
print(f"{'':>6}{'左':>8}{'中':>9}{'右':>9}    {'左':>8}{'中':>9}{'右':>9}")
for r, lab in enumerate(("上", "中", "下")):
    print(f"{lab:>6}" + "".join(f"{cells8[r * 3 + c]:>9.3f}" for c in range(3))
          + "   " + "".join(f"{cells3[r * 3 + c]:>9.3f}" for c in range(3)))
EDGE_CENTER_RATIO = float(max(cells8[0], cells8[2], cells8[6], cells8[8]) / cells8[4])
EDGE_CENTER_RATIO3 = float(max(cells3[0], cells3[2], cells3[6], cells3[8]) / cells3[4])
print(f"\n四隅 / 中央 の比   8 dof {EDGE_CENTER_RATIO:.2f}   3 dof {EDGE_CENTER_RATIO3:.2f}")
print("対応点は画面全体に散っているので、これは外挿ではなく **余分な自由度が周辺で")
print("効いている** ことを示す。自由度を 3 に絞ると偏りかたも変わる。")

print("\nフレームごとの姿勢誤差(鎖・上位 5 件と下位 3 件):")
order = np.argsort(pe_chain)[::-1]
for idx in list(order[:5]) + list(order[-3:]):
    print(f"  フレーム {int(idx):>2}(方位 {360.0 * idx / N_LOOP:>5.1f} 度)  "
          f"{pe_chain[idx]:>7.3f} px")
print(f"平均 {pe_chain.mean():.3f} px、最悪 {pe_chain.max():.3f} px —— "
      f"比 {pe_chain.max() / pe_chain.mean():.1f} 倍。")
print("鎖の誤差は方位角に沿って単調には増えない(揺れの位相と噛み合う)。")
print("「平均」だけ見ると最悪フレームの見た目を過小評価する。")


# ===========================================================================
rule("10. 速度と、この PoC が測らなかったこと")
# ===========================================================================
print(f"総経過 {time.perf_counter() - T_START:.1f} s")
print(f"1 ペアの対応取り + RANSAC + DLT + 3 dof 当てはめは数 ms"
      f"(第 1-4 章で {len(M_ALL)} ペア)。")
print(f"大域最適化({N_LOOP} 枚 = {3 * (N_LOOP - 1)} 変数, 辺 {len(M_ALL)} 本)も"
      "疎ヤコビアンなら 1 秒未満。")
print("重いのはソルバではなく **ペア数** である。距離無制限にすると "
      f"{N_LOOP * (N_LOOP - 1) // 2} ペアになり、重なりの無い組を大量に試すことになる。")
print("\n測っていないこと(この PoC の外):")
print(" - 露出・ビネットの違い。実写では継ぎ目の見た目はここでも壊れる。")
print(" - 並進(視差)。純回転を仮定しているので、近景があるとホモグラフィ自体が")
print("   成り立たない。その場合の崖は本 PoC では測れない。")
print(" - レンズ歪み。歪みを入れると穴 (d) のとおり推定する道具が無い。")
print(" - 実写。合成なので 1 段の誤差に偏りが無い(第 6 章の指数がその証拠)。")


# ===========================================================================
rule("結論")
# ===========================================================================
print(f"1. 鎖は隣の継ぎ目を {SEAM_OPEN:.2f} px に保ったまま、閉じる 1 本を "
      f"{SEAM_CLOSE:.1f} px 開く({SEAM_CLOSE / SEAM_OPEN:.0f} 倍)。")
print(f"2. 姿勢の最悪誤差: 鎖 {r_chain['pose_max']:.2f} → 閉ループ拘束 "
      f"{r_cyc['pose_max']:.2f} → 全ペア {r_all['pose_max']:.2f} → "
      f"大域最適化 {r_gn['pose_max']:.2f} px。")
print(f"3. 埋もれている bundle_adjust_mosaic は鎖を上回らなかった"
      f"(姿勢最悪 {pe_ba.max():.1f} px, {n_identity}/{N_LOOP} 枚が単位行列)。")
print(f"4. ドリフトの伸びの指数は実測 {SLOPE:.2f}(予想 0.5 = ランダムウォーク / "
      f"1.0 = 偏り)。")
print(f"5. 重なり 80 → {CLIFF_OV_AT * 100:.0f} % で 1 段の誤差 {CLIFF_OV:.1f} 倍、"
      f"{(_dead_from or 0) * 100:.0f} % 以下で鎖が切れる。")
print(f"6. 模様の周期が 1 段の移動量と共鳴すると誤対応率 "
      f"{REP_BAD_OFF * 100:.1f} % → {REP_BAD_RES * 100:.1f} %。")
print(f"7. f を ±10 % 間違えると、雑音ゼロでも閉ループ誤差 {FOC_LOOP_SPAN:.1f} px。"
      f" 非直交度の谷から f は {abs(F_HAT_RATIO - 1) * 100:.1f} % で回収できる。")

# --- 機械で固定する主張 ---------------------------------------------------- #
# (1) ゼロ点は「隣は綺麗・閉じ目は壊れる」という形で壊れる。
assert SEAM_CLOSE > 5.0 * SEAM_OPEN, (
    f"閉じ目 {SEAM_CLOSE:.3f} が隣接継ぎ目 {SEAM_OPEN:.3f} の 5 倍に届かない "
    "—— ゼロ点が壊れていない(実験の設定が甘い)")
# (2) 閉ループ拘束・全ペア・大域最適化はどれも鎖より姿勢が良い。
for _nm, _r in (("閉ループ拘束", r_cyc), ("全ペア", r_all), ("大域最適化", r_gn)):
    assert _r["pose_max"] < r_chain["pose_max"], f"{_nm} が鎖に勝てていない"
# (3) 大域最適化は閉ループ誤差をほぼ消す(鎖の 1/5 以下)。
assert r_gn["loop"] < 0.2 * r_chain["loop"], (
    f"大域最適化の閉ループ誤差 {r_gn['loop']:.3f} が鎖 {r_chain['loop']:.3f} の "
    "1/5 を切れていない")
# (4) 素朴な等分は厳密には閉じない(1 次近似であることの機械的な確認)。
assert r_spr["loop"] > 5.0 * r_cyc["loop"], (
    "等分と厳密解の閉ループ誤差に差が無い —— 非可換性が現れていない")
# (5) 埋もれた bundle_adjust_mosaic は鎖を上回らない。上回ったら主張を書き直すこと。
assert not BA_BEATS_CHAIN, (
    "bundle_adjust_mosaic が鎖を上回った —— 第 4 章の結論を書き直すこと")
assert n_identity >= N_LOOP - 5, (
    f"単位行列で返ったのは {n_identity} 枚 —— 穴 (b) の症状が再現していない")
# (6) ドリフトは N とともに伸びる。指数は 0.3 以上、1.3 以下。
assert 0.30 <= SLOPE <= 1.30, f"ドリフト指数 {SLOPE:.3f} が想定域外"
assert np.mean(acc[64]) > 2.0 * np.mean(acc[4]), "N を 16 倍しても誤差が 2 倍未満"
# (7) 重なりを削ると 1 段が壊れ、やがて鎖が切れる。
assert CLIFF_OV > 2.0, f"重なりの崖 {CLIFF_OV:.2f} 倍しか出ていない"
assert _dead_from is not None, "重なり 10 % でも切れなかった —— 崖が出ていない"
# (8) 繰り返し模様の共鳴周期で誤対応が増える。
assert REP_BAD_RES > REP_BAD_OFF, (
    f"共鳴周期の誤対応率 {REP_BAD_RES:.3f} が非共鳴 {REP_BAD_OFF:.3f} を超えない")
# (9) 焦点距離の誤りは雑音ゼロでも偏りとして残り、非直交度の谷から回収できる。
assert _f0[4] < 1e-6 < FOC_LOOP_SPAN, (
    f"f 誤差の効果が出ていない(正 {_f0[4]:.1e} / ±10 % {FOC_LOOP_SPAN:.3f})")
assert abs(F_HAT_RATIO - 1.0) < 0.06, f"f の回収誤差 {abs(F_HAT_RATIO - 1) * 100:.1f} %"
# (10) 残差は画面内で一様ではない。
assert EDGE_CENTER_RATIO > 1.05, "四隅と中央の残差が同じ —— 位置別に見る意味が無い"
# (11) 既存の部品(DLT / 点変換 / ワープ)は使えた。
assert E8 < ERAW and _chk3 < 1e-9 and _chk4 < 0.05, "既存部品の評価が再現しない"

print("\nPASS")

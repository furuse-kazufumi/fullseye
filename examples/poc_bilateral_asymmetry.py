# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""左右非対称性を測る —— 鏡映して重ね、入れた変形量と突き合わせる。

比較形態学(頭蓋・骨・顔)と工業の左右対称部品検査には、設計 CAD が無いという共通点がある。
基準の無い対象で「どこがおかしいか」を言うには、**その個体自身の反対側**を基準にするしかない
(もう一つの道は群集平均だが、それは標本が多数要る)。手順は鏡映して重ねる、それだけ。
問題は「どの面で鏡映するか」で、その面自体を測定データから決めると
**片側の変形が面そのものを引きずる**。

EXTEND: 実際の頭蓋・骨で走らせるなら ``cranium_mesh()`` を実スキャンの読み込みに差し替える
(``fs.read_mesh("skull.ply")`` → ``(V, F)``、点群だけなら ``fs.read_points`` で
そのまま ``P`` に入れて ``sample_surface`` を飛ばす)。公開標本は MorphoSource
(``https://www.morphosource.org/``)に CT 由来の頭蓋・骨の PLY/STL が多数ある。
**データはこのリポジトリに同梱しない**(容量とライセンスの両方の理由)。
**媒体ごとに利用条件が違う** —— MorphoSource は「サイト全体で一つのライセンス」ではなく、
標本ごと・ファイルごとに寄託機関が条件(CC BY / CC BY-NC / 要申請 / 再配布不可 …)を
付けている。使う前に**その 1 ファイルの条件を個別に確認**し、成果物には寄託機関・標本 ID・
ファイルの版を明記すること。実スキャンでは本 PoC が仮定していない条件が 3 つ増える:
(a) 単位が mm とは限らない(CT は voxel spacing 由来。スケールを外すと床も信号も同倍率でずれる)、
(b) 破損・欠損があるので trimmed ICP(``fs.icp(..., trim=0.2)``)に替える、
(c) 標本が閉曲面とは限らないので、本 PoC の「重心から見て外向き」という法線の向き付けは
使えない(``fs.estimate_normals(..., viewpoint=...)`` にスキャナ位置を渡す)。

この PoC が示すこと:

1. **入れた量と測った量を突き合わせられる** —— 厳密に左右対称な合成頭蓋を作り、片側にだけ
   既知の高さの膨らみを法線方向に入れる。測った非対称量が入れた量の何倍になるかを数字で言う。
2. **検査には床がある** —— 完全対称な標本を測っても 0 は出ない。床は距離の取り方で 2 桁動く
   (点対点 1.33 mm → 点対面 0.030 mm → 近傍平滑 0.012 mm、15000 点・全長 218 mm)。
   床より小さい差は検出できない。
3. **対称面は変形に引きずられる** —— 残差を最小にする面は解剖学的な正中面ではない。
   片側 6.33 mm の膨らみに対して面が 2.92 mm / 1.72 度ずれ、**非対称量の 46 % が消える**。
   これがこの問題の一番の罠で、「よく合う面」を探すほど症状が薄まる。
   真の面で鏡映すると利得 1.0 だが残差 rms は**大きい** ——
   つまり **残差が小さい面ほど良い、は成り立たない**。
4. **床と利得はトレードオフ** —— 正中ランドマークから面を決めると利得はほぼ 1.0 だが、
   床が 16 倍高い。**見つけるなら残差最適面、量を言うならランドマーク面**。両方要る。
5. **鏡映だけでは「どちら側が異常か」は原理的に決まらない** —— 非対称場は必ず等量の
   二重ローブ(患側 +d と、その鏡像位置 -d)になる。左右を決めるには群集平均か外部知識が要る。

★ この PoC が出した道具の穴(op 本体は直していない):

- **A. `symmetry3d` の op がファサードに出ていない**。``ops3d`` の台帳(カテゴリ ``symmetry``)
  には ``reflect_points`` / ``reflection_symmetry_score`` / ``detect_reflection_symmetry`` /
  ``detect_rotational_symmetry`` の 4 つが登録済みなのに ``fs.reflect_points`` は
  AttributeError(第 8 章で実行時に確認)。この PoC は鏡映を自前で書いた(``_mirror``)。
- **B. `metrics3d` の距離もファサード未露出** —— ``chamfer_distance`` / ``hausdorff_distance``
  / ``accuracy`` / ``completeness`` / ``fscore``。対称スコアの土台なのに consumer から呼べない。
- **C. 対称スコアが点対点(chamfer)しか無い**。``reflection_symmetry_score`` は chamfer を
  中央値最近傍間隔で割る。点対点距離は**点間隔がそのまま床**になる(実測 rms ≒ 点間隔 x 1.2)。
  同じ標本で点対面に替えるだけで床が 45 倍下がる(第 2 章)。対称スコアに点対面の選択肢が要る。
- **D. `detect_reflection_symmetry` は PCA 3 軸しか試さない**。第 2・第 3 の広がりが 0.2 %
  しか違わない標本で **66 度**、回転体では **88 度**外した(第 6 章 (c))。
  軸を連続に動かす最適化が無く、しかも**外したことを黙っている**。
  候補スコアの差(margin)を返してくれれば呼び出し側で弾けるのに、それも返らない。
- **E. 位置合わせ後の対称面を返す op が無い**。スコアは返るが面が返らない。合成写像
  ``p → R·H·p + t`` から固有値 -1 の固有ベクトルと ``m·t/2`` で厳密に取り出せる
  (中点集合の平面フィットと厚み 1e-13 mm で一致することを assert で検算済み)。
  引きずられ量を測るにはこれが要る。この PoC は ``_plane_from_map`` を自前で書いた。
- **F. 3-D ランドマークが無い**。``handpose.hand_landmarks`` は MediaPipe の手だけ。
  形態学の正中矢状面は正中ランドマーク(nasion / bregma / opisthion …)から決めるのが
  正解で、本 PoC でも利得 1.0 を出した唯一の方法なのに、ランドマーク集合の型も、
  そこから面を出す op も無い。
- **G. Procrustes / 一般化 Procrustes 解析(GPA)が無い**。``fs.kabsch`` は対応つき剛体だけ。
  スケール込み Procrustes も、複数標本を共通座標へ載せる GPA も無い。形態学の基本工具。
- **H. 統計形状モデル(平均形状・形状 PCA モード)が無い**。上の 5 の帰結として
  「どちら側が異常か」には群集平均が要るが、その器が無い。
- **I. 符号つき surface-to-surface 距離の op が無い**。1-D には
  ``profileops.profile_deviation`` / ``_signed_distance_to_polyline`` が居るのに、
  3-D の対応物(点群 → 相手曲面への符号つき距離 + 近傍平滑 + 分位)が無い。
  この PoC は ``_surface_deviation`` を自前で書いた。
- **J. `fs.obb` が (N,3) の SVD を `full_matrices=True` で回す**(``pcseg.py:425``)。
  20000 点で 20000x20000 の U を 3.2 GB 確保して 3.8 秒、しかもその U は捨てている
  (``_, _, Vt = np.linalg.svd(P - c)``)。``full_matrices=False`` なら 0.7 ms
  (**5000 倍超**、第 7 章で実測)。10 万点では U だけで 80 GB になり落ちる。
  **同じ形が兄弟コードにもある**(いずれも U を捨てている。実コードで 1 件ずつ確認):
  ``pcseg.py:92`` (fit_plane) / ``measure.py:73`` (2-D 直線フィット、(N,2) で N x N)/
  ``ops.py:565`` (輪郭の直線化)/ ``camera.py:366`` と ``pnp3d.py:178`` (平面 PnP)。
  1 件直すのではなく、この形をまとめて掃くべき。

★ 疑ったが実測で否定したもの(残しておく): 最初は「``point_to_plane_icp`` の ``tol``
既定 1e-8 が絶対値なので、mm 単位の標本では収束判定が発火せず ``max_iter`` まで回る」
と書いた —— 一式が 20000 点で 3.9 秒かかっていたからだ。時間を関数ごとに割ったら
3.8 秒は ``fs.obb``(上の J)で、ICP は ``max_iter`` 3 でも 60 でも 4 反復で収束し、
tol=1e-8 と 1e-7 で **rmse が 10 桁一致**していた。遅い場所は測って特定する。
なお ``fs.icp``(点対点)の方は 60 反復まで回っても rmse が 1.1658 から 1.1607 にしか
動かない —— こちらは収束が遅いのではなく、目的関数が点間隔ノイズに支配されていて
**下がる先が無い**(第 2 章の床がそれ)。

数字はすべて下の実行結果。この機械(Windows 11 / py 3.11 / CPU)での実測。
"""
from __future__ import annotations

import math
import time

import numpy as np
from scipy.spatial import cKDTree

import fullseye as fs

POSE_EULER_DEG = (17.0, -9.0, 23.0)      # 実スキャンは軸に揃っていない。揃えると問題が易しくなる
POSE_SHIFT = np.array([120.0, -40.0, 55.0])
OBB_SUBSET = 4000                        # ★穴 J: fs.obb は点数の 2 乗で効くので部分点で呼ぶ


# ==== 標本づくり ============================================================

def _uv_sphere_topology(nu, nv, z_cap):
    """UV 格子の三角形分割 + 極キャップ。→ ``(cap_vertices, faces)``。"""
    idx = np.arange(nu * nv).reshape(nu, nv)
    i0, i3 = idx[:, :-1], idx[:, 1:]
    i1, i2 = np.roll(idx, -1, 0)[:, :-1], np.roll(idx, -1, 0)[:, 1:]
    F = np.concatenate([np.stack([i0, i1, i2], -1).reshape(-1, 3),
                        np.stack([i0, i2, i3], -1).reshape(-1, 3)])
    top, bot = nu * nv, nu * nv + 1
    caps = np.array([[0.0, 0.0, z_cap], [0.0, 0.0, -z_cap]])
    ring_t, ring_b = idx[:, 0], idx[:, -1]
    F = np.concatenate([F,
                        np.stack([np.full(nu, top), np.roll(ring_t, -1), ring_t], -1),
                        np.stack([np.full(nu, bot), ring_b, np.roll(ring_b, -1)], -1)])
    return caps, F.astype(np.int64)


def cranium_mesh(nu: int = 128, nv: int = 72):
    """合成の頭蓋もどき(楕円体 + 吻 + 頬骨弓 + 後頭下の凹み)。→ ``(V, F)``。

    半径を経度 ``u`` について ``cos u`` の**偶関数**だけで作る。``x = r sin v cos u`` なので
    ``u → π - u`` で ``x`` だけが反転し、``nu`` が偶数なら格子点が格子点へ写る。
    結果として **頂点集合が浮動小数点の精度で厳密に左右対称**(第 1 章で 9e-14 mm と検算)。
    面の張り方(四角形の対角線)は鏡映で入れ替わるので、三角形分割そのものは対称ではない
    —— その分は床に乗る。実物と同じで、これは隠さず測る。
    """
    if nu % 2:
        raise ValueError("nu must be even, else the vertex grid is not mirror-symmetric")
    U, Vv = np.meshgrid(2.0 * np.pi * np.arange(nu) / nu,
                        np.pi * (np.arange(nv) + 0.5) / nv, indexing="ij")
    su, cu, sv, cv = np.sin(U), np.cos(U), np.sin(Vv), np.cos(Vv)
    r = 1.0
    r = r + 0.30 * np.clip(su, 0.0, None) ** 3 * sv ** 2               # 吻(+y)
    r = r + 0.16 * (cu ** 2) ** 3 * np.exp(-((Vv - 1.7) / 0.35) ** 2)  # 頬骨弓(±x)
    r = r - 0.12 * np.exp(-((Vv - np.pi) / 0.28) ** 2)                 # 後頭下の凹み
    a, b, c = 70.0, 95.0, 62.0                                         # 半軸 [mm]
    P = np.stack([a * r * sv * cu, b * r * sv * su, c * r * cv], -1).reshape(-1, 3)
    caps, F = _uv_sphere_topology(nu, nv, c * 1.02)
    return np.concatenate([P, caps]), F


def revolution_mesh(nu: int = 128, nv: int = 72):
    """y 軸まわりの回転体(x 半軸 = z 半軸)。対称面が**連続無限**にある縮退標本。→ ``(V, F)``。

    こういう標本では「最も対称な面」を探しても解剖学的な正中面は選ばれない
    —— y 軸を含む面はどれも真の対称面なので、選ぶ根拠がデータの中に無い(第 6 章 (c))。
    """
    U, Vv = np.meshgrid(2.0 * np.pi * np.arange(nu) / nu,
                        np.pi * (np.arange(nv) + 0.5) / nv, indexing="ij")
    r = 1.0 - 0.10 * np.exp(-((Vv - np.pi) / 0.30) ** 2)
    a, b, c = 70.0, 95.0, 70.0
    P = np.stack([a * r * np.sin(Vv) * np.cos(U), b * r * np.sin(Vv) * np.sin(U),
                  c * r * np.cos(Vv)], -1).reshape(-1, 3)
    caps, F = _uv_sphere_topology(nu, nv, c)
    return np.concatenate([P, caps]), F


def vertex_normals(V, F):
    """面積重みつき頂点法線(外向きに揃える)。→ (N,3)。閉曲面前提。"""
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V, dtype=np.float64)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    return -N if np.mean(np.einsum("ij,ij->i", N, V - V.mean(0))) < 0 else N


def blob_weight(V, direction, sigma):
    """片側の一点を中心にしたガウス重み(0..1)。→ ``(w, center)``。"""
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    k = int(np.argmax(V @ d))
    return np.exp(-np.sum((V - V[k]) ** 2, axis=1) / (2.0 * sigma ** 2)), V[k]


def half_weight(V, softness=12.0):
    """右半身(x>0)だけを滑らかに立ち上げる重み。広い片側変形用。"""
    return 1.0 / (1.0 + np.exp(-V[:, 0] / softness))


def posed_cloud(V, F, n, seed, R, t):
    """メッシュ表面から n 点をサンプリングし、既知の剛体姿勢へ置く。→ (n,3)。"""
    return fs.sample_surface(V, F, n, seed=seed) @ R.T + t


# ==== 測り方 ================================================================

def _mirror(P, p0, n):
    """平面(点 p0・法線 n)で鏡映。★穴 A: ``symmetry3d.reflect_points`` の再実装。"""
    n = np.asarray(n, float)
    n = n / np.linalg.norm(n)
    return P - 2.0 * ((P - np.asarray(p0, float)) @ n)[:, None] * n[None, :]


def _principal_axes(P):
    """点群の主軸(列が軸、寄与の大きい順)。``full_matrices=False`` は必須 —— ★穴 J 参照。"""
    return np.linalg.svd(P - P.mean(0), full_matrices=False)[2].T


def _surface_deviation(P, A, k_smooth=12, k_normal=16):
    """P の各点から相手点群 A の**局所接平面**までの符号つき距離。→ ``(smoothed, raw)``。

    符号は「A の外向き法線の側が正」= 元の標本が相手より外へ張り出していれば +。
    点対点距離を使うと点間隔がそのまま床になるので、必ず接平面へ落とす(第 2 章)。
    ``k_smooth`` 近傍の中央値を取ると、サンプリング由来の跳ねがさらに落ちる。
    ★穴 I: 3-D の符号つき surface-to-surface 距離 op が無いので自前。
    """
    nA = fs.estimate_normals(A, k=k_normal)
    nA[np.einsum("ij,ij->i", nA, A - A.mean(0)) < 0] *= -1.0   # 閉曲面 → 重心基準で外向き
    _, i = cKDTree(A).query(P)
    s = np.einsum("ij,ij->i", P - A[i], nA[i])
    if k_smooth <= 1:
        return s, s
    _, j = cKDTree(P).query(P, k=int(min(k_smooth, len(P))))
    return np.median(s[j], axis=1), s


def pca_plane_candidates(P):
    """PCA 主軸 3 本を候補法線として点対点残差で採点。→ ``(centroid, axes, scores)``。

    ``symmetry3d.detect_reflection_symmetry`` と同じ戦略(★穴 D: 候補は 3 本だけ)。
    """
    if len(P) < 3:
        raise ValueError("need >= 3 points to propose a symmetry plane")
    c = P.mean(0)
    axes = _principal_axes(P)
    tree = cKDTree(P)
    scores = np.array([float(np.sqrt(np.mean(tree.query(_mirror(P, c, axes[:, i]))[0] ** 2)))
                       for i in range(3)])
    return c, axes, scores


def best_pca_plane(P):
    """候補のうち残差最小の鏡映面。→ ``(point, normal, score, axis_index, margin)``。

    ``margin`` = (2 位のスコア - 1 位) / 1 位。**これが小さいときの面は信用してはいけない**
    (第 6 章 (c) で 0.07 以下のとき 66〜88 度外した)。
    """
    c, axes, s = pca_plane_candidates(P)
    b = int(np.argmin(s))
    ordered = np.sort(s)
    return c, axes[:, b], float(s[b]), b, float((ordered[1] - ordered[0]) / ordered[0])


def _plane_from_map(A, t):
    """非固有等長写像 ``p → A p + t``(det A = -1)の実効的な反射面。→ ``(normal, offset)``。

    A は固有値 -1 を持ち、その固有ベクトルが面の法線 m。面は ``m·x = (m·t)/2``。
    滑り(グライド)成分や面内回転が乗っていても面そのものはこの式で厳密に決まる。
    ★穴 E: 位置合わせ後の対称面を返す op が無いので自前。
    """
    w, V = np.linalg.eig(A)
    m = np.real(V[:, int(np.argmin(np.abs(w + 1.0)))])
    m = m / np.linalg.norm(m)
    return m, float(m @ t) / 2.0


def mirror_pipeline(P, refine="p2plane", plane=None, max_iter=30, tol=1e-7):
    """鏡映 → 位置合わせ。→ ``(aligned, normal, offset)``。

    ``plane`` に ``(p0, n)`` を渡せばその面で、``None`` なら PCA 候補から選ぶ。
    ``refine`` = ``"none"``(位置合わせしない)/ ``"p2point"``(点対点 ICP)/
    ``"p2plane"``(点対面 ICP)。点対面は 4 反復で収束するので ``max_iter`` は 30 で足りる。
    """
    p0, n = plane if plane is not None else best_pca_plane(P)[:2]
    Q = _mirror(P, p0, n)
    if refine == "none":
        R, t, aligned = np.eye(3), np.zeros(3), Q
    elif refine == "p2point":
        R, t, aligned, _ = fs.icp(Q, P, max_iter=max_iter, tol=tol)
    elif refine == "p2plane":
        R, t, aligned, _ = fs.point_to_plane_icp(Q, P, max_iter=max_iter, tol=tol)
    else:
        raise ValueError("refine must be 'none', 'p2point' or 'p2plane'")
    H = np.eye(3) - 2.0 * np.outer(n, n)
    m, c = _plane_from_map(R @ H, R @ (2.0 * (n @ p0) * n) + t)
    return aligned, m, c


def plane_error(m, c, m_true, c_true):
    """推定面と真の正中面の差。→ ``(角度 [deg], 位置 [mm])``。法線の符号を揃えてから比べる。"""
    if m @ m_true < 0:
        m, c = -m, -c
    return math.degrees(math.acos(min(1.0, abs(float(m @ m_true))))), float(c - c_true)


def midline_landmark_plane(V_posed, lm_idx):
    """正中ランドマーク群への最小二乗平面。→ ``(point, normal)``。

    形態学の正解手順(正中矢状面は正中ランドマークで決め、左右差はその面で測る)。
    ★穴 F/G: ランドマークの型も GPA も、この 3 行を担う op も fullseye に無い。
    """
    L = V_posed[lm_idx]
    c = L.mean(0)
    return c, np.linalg.svd(L - c, full_matrices=False)[2][2]


def extents_of(P):
    """外接箱の辺(長い順)。★穴 J を避けるため部分点で ``fs.obb`` を呼ぶ。"""
    sub = P if len(P) <= OBB_SUBSET else P[np.linspace(0, len(P) - 1, OBB_SUBSET).astype(int)]
    return np.sort(2.0 * fs.obb(sub)["extents"])[::-1]


def _fmt(x, w=8, p=3):
    return f"{'-':>{w}}" if not np.isfinite(x) else f"{x:>{w}.{p}f}"


# ==== 本体 ==================================================================

def main():
    from scipy.spatial.transform import Rotation
    R_pose = Rotation.from_euler("xyz", POSE_EULER_DEG, degrees=True).as_matrix()
    t_pose = POSE_SHIFT
    m_true = R_pose[:, 0]                    # 標本座標の x=0 面が真の正中面
    c_true = float(m_true @ t_pose)

    V, F = cranium_mesh()
    Nv = vertex_normals(V, F)
    w_blob, blob_center = blob_weight(V, (0.75, 0.35, 0.45), 28.0)
    w_narrow, _ = blob_weight(V, (0.75, 0.35, 0.45), 12.0)
    w_half = half_weight(V)
    N_MAIN = 15000

    def specimen(weight, amp, n=N_MAIN, seed=1):
        return posed_cloud(V + amp * weight[:, None] * Nv, F, n, seed, R_pose, t_pose)

    print("=== 1. 標本 —— 厳密に左右対称な頭蓋もどきと、片側だけの既知の膨らみ ===")
    flipped = V.copy()
    flipped[:, 0] *= -1.0
    d_mirror, _ = cKDTree(V).query(flipped)
    P_undeformed = posed_cloud(V, F, N_MAIN, 1, R_pose, t_pose)
    ext = extents_of(P_undeformed)
    sp = float(np.median(cKDTree(P_undeformed).query(P_undeformed, k=2)[0][:, 1]))
    print(f"  頂点 {len(V)} / 三角形 {len(F)} / サンプル点 {N_MAIN}")
    print(f"  外接箱の辺 {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm、点間隔の中央値 {sp:.3f} mm")
    print(f"  頂点集合の鏡映一致 {d_mirror.max():.2e} mm(厳密対称。ここが崩れると以降は全部意味を失う)")
    print(f"  膨らみの中心 {np.round(blob_center, 1)}(標本座標。x>0 が右側)、幅 sigma = 28 mm")
    print("  → 変形は頂点法線の向きに入れる。だから注入量がそのまま「相手曲面までの距離」になる。")
    print("     接線方向にずらすと曲面上を滑るだけで距離はほぼ 0 になり、真値が定義できない。")

    print("\n=== 2. 検査の床 —— 完全対称な標本を測っても 0 は出ない ===")
    print(f"  {'点数':>7}{'点間隔':>9}{'点対点 rms':>12}{'点対面 rms':>12}"
          f"{'平滑 rms':>11}{'平滑 p99':>10}{'平滑 |max|':>11}")
    floors = {}
    for n in (2000, 5000, N_MAIN, 30000):
        P = posed_cloud(V, F, n, 1, R_pose, t_pose)
        spacing = float(np.median(cKDTree(P).query(P, k=2)[0][:, 1]))
        aligned, _, _ = mirror_pipeline(P)
        sm, raw = _surface_deviation(P, aligned)
        p2p = float(np.sqrt(np.mean(cKDTree(aligned).query(P)[0] ** 2)))
        floors[n] = (float(np.sqrt(np.mean(sm ** 2))), float(np.abs(sm).max()), spacing)
        print(f"  {n:>7d}{spacing:>9.3f}{p2p:>12.4f}{float(np.sqrt(np.mean(raw ** 2))):>12.4f}"
              f"{floors[n][0]:>11.4f}{float(np.percentile(np.abs(sm), 99)):>10.4f}{floors[n][1]:>11.4f}")
    print("  → 点対点は**点間隔がそのまま床**(rms / 点間隔 が 4 段とも 1.2 前後で一定。下の assert)。")
    print("     接平面へ落とすと接線方向のばらつきが消え、近傍中央値でさらに落ちる。")
    print("     ★穴 C: symmetry3d の対称スコアは点対点(chamfer)しか持たない。")
    floor_rms, floor_max, _ = floors[N_MAIN]

    print("\n=== 3. ゼロ点 —— 鏡映しない / 位置合わせしない ===")
    amp_probe = 1.6
    P = specimen(w_blob, amp_probe)
    injected = float(_surface_deviation(P, P_undeformed)[0].max())
    print(f"  入れた膨らみ {amp_probe:.2f} mm(実測の注入量 = 変形前の曲面までの距離 {injected:.3f} mm)")
    print(f"  {'方法':<34}{'rms':>9}{'max':>9}{'床比':>9}{'面の角度':>10}{'面のずれ':>10}")
    for label, plane, refine in (
            ("(0) 鏡映しない(自分と比べる)", None, None),
            ("(1) 世界座標の x=0 面で鏡映のみ", (np.zeros(3), np.array([1.0, 0.0, 0.0])), "none"),
            ("(2) PCA 面で鏡映のみ", None, "none"),
            ("(3) PCA 面 + 点対点 ICP", None, "p2point"),
            ("(4) PCA 面 + 点対面 ICP", None, "p2plane")):
        if refine is None:
            sm = np.zeros(len(P))
            ang = off = float("nan")
        else:
            aligned, m, c = mirror_pipeline(P, refine=refine, plane=plane)
            sm, _ = _surface_deviation(P, aligned)
            ang, off = plane_error(m, c, m_true, c_true)
        rms = float(np.sqrt(np.mean(sm ** 2)))
        print(f"  {label:<34}{rms:>9.4f}{float(np.abs(sm).max()):>9.4f}"
              f"{rms / floor_rms:>9.1f}{_fmt(ang, 10)}{_fmt(off, 10)}")
    print("  → (0) は変形量に関係なく恒等的に 0。**何を入れても検出できない**(盲目のゼロ点)。")
    print("     (1) は姿勢が違うだけで 4 桁外す —— 「解剖学的に想定した面」を固定で使う危険。")
    print("     (2) から (4) が鏡映 + 位置合わせの取り分。点対点 ICP (3) は点対面 (4) にわずかに")
    print("     及ばない。完全対称な標本(第 2 章)では差がもっと開き、点対点は床の 10 倍で止まる。")

    print("\n=== 4. 入れた量 vs 測った量 —— 面の決め方で利得が変わる ===")
    sel = np.argsort(np.abs(V[:, 0]))[:400]
    order = np.argsort(np.arctan2(V[sel, 2], V[sel, 1]))
    lm_idx = sel[order[:: max(1, len(order) // 16)]][:16]
    print(f"  正中ランドマーク {len(lm_idx)} 点(標本座標で |x| <= {np.abs(V[lm_idx, 0]).max():.2f} mm)")
    print(f"  {'入れた量':>9}{'真の注入':>10}{'残差最適面 max':>16}{'利得':>7}"
          f"{'ランドマーク面 max':>19}{'利得':>7}")
    gains = {}
    for amp in (0.0, 0.4, 0.8, 1.6, 3.2, 6.4):
        Vd = V + amp * w_blob[:, None] * Nv
        Pa = posed_cloud(Vd, F, N_MAIN, 1, R_pose, t_pose)
        truth = float(_surface_deviation(Pa, P_undeformed)[0].max())
        opt = float(_surface_deviation(Pa, mirror_pipeline(Pa)[0])[0].max())
        lc, ln = midline_landmark_plane(Vd @ R_pose.T + t_pose, lm_idx)
        lmk = float(_surface_deviation(Pa, _mirror(Pa, lc, ln))[0].max())
        gains[amp] = (truth, opt, lmk)
        g1 = opt / truth if truth > 1e-9 else float("nan")
        g2 = lmk / truth if truth > 1e-9 else float("nan")
        print(f"  {amp:>9.2f}{truth:>10.3f}{opt:>16.3f}{_fmt(g1, 7)}{lmk:>19.3f}{_fmt(g2, 7)}")
    opt_floor, lm_floor = gains[0.0][1], gains[0.0][2]
    g_opt = gains[6.4][1] / gains[6.4][0]
    g_lmk = gains[6.4][2] / gains[6.4][0]
    print(f"  → 残差最適面の利得は {g_opt:.2f} 前後で一定(= 系統的に {100 * (1 - g_opt):.0f} % 過小評価)。")
    print(f"     ランドマーク面の利得は {g_lmk:.2f} だが、床が {lm_floor:.3f} mm と"
          f" 残差最適面の {lm_floor / opt_floor:.0f} 倍(面自体の推定誤差がそのまま乗る)。")
    print(f"     床の 3 倍を要求したときの検出限界 = 残差最適面 {3 * opt_floor / g_opt:.2f} mm 相当 /"
          f" ランドマーク面 {3 * lm_floor / g_lmk:.2f} mm 相当。")
    print("     小さい振幅でランドマーク面の利得が 1 を超えるのは、床が信号に足し込まれているだけ。")
    print("     **見つけるなら残差最適面、量を言うならランドマーク面**。両方要る。")

    print("\n=== 5. 対称面が引きずられる —— この問題の一番の罠 ===")
    print(f"  {'変形':<18}{'入れた量':>9}{'真の注入':>10}{'測った max':>12}{'利得':>7}"
          f"{'面の角度':>10}{'面のずれ':>10}")
    drag = {}
    for label, w in (("局所 sigma=12", w_narrow), ("局所 sigma=28", w_blob),
                     ("広い片側(半身)", w_half)):
        for amp in (1.6, 6.4):
            Pa = specimen(w, amp)
            truth = float(_surface_deviation(Pa, P_undeformed)[0].max())
            aligned, m, c = mirror_pipeline(Pa)
            sm, _ = _surface_deviation(Pa, aligned)
            ang, off = plane_error(m, c, m_true, c_true)
            drag[(label, amp)] = (truth, float(sm.max()), ang, off)
            print(f"  {label:<18}{amp:>9.2f}{truth:>10.3f}{float(sm.max()):>12.3f}"
                  f"{float(sm.max()) / truth:>7.3f}{ang:>10.3f}{off:>10.3f}")
    narrow_g = drag[("局所 sigma=12", 6.4)][1] / drag[("局所 sigma=12", 6.4)][0]
    wide_g = drag[("広い片側(半身)", 6.4)][1] / drag[("広い片側(半身)", 6.4)][0]
    print(f"  → 変形が広いほど面が引きずられ、利得が落ちる({narrow_g:.2f} → {g_opt:.2f}"
          f" → {wide_g:.2f})。残差最小化にとっては「変形を左右へ薄く塗り広げる」のが")
    print("     一番安上がりなので、最適化はそちらへ行く。")
    P64 = specimen(w_blob, 6.4)
    al64, m64, c64 = mirror_pipeline(P64)
    sm_opt, _ = _surface_deviation(P64, al64)
    sm_ora, _ = _surface_deviation(P64, _mirror(P64, t_pose, m_true))
    print(f"  真の面で鏡映: 利得 {sm_ora.max() / gains[6.4][0]:.2f} / 残差 rms "
          f"{np.sqrt(np.mean(sm_ora ** 2)):.4f}")
    print(f"  残差最適面   : 利得 {sm_opt.max() / gains[6.4][0]:.2f} / 残差 rms "
          f"{np.sqrt(np.mean(sm_opt ** 2)):.4f}  ← 残差は小さいのに信号も小さい")
    print("  → **残差 rms が小さい面ほど良い、は成り立たない**。残差を最小にする面は、")
    print("     症状の半分を「左右に均した」ことで手に入れている。")
    hi, lo = P64[int(np.argmax(sm_opt))], P64[int(np.argmin(sm_opt))]
    print(f"  二重ローブ: 最大 {sm_opt.max():+.3f} mm と最小 {sm_opt.min():+.3f} mm がほぼ等量で、")
    print(f"    2 点は正中面の反対側にある(真の面までの符号つき距離 "
          f"{float(m_true @ hi - c_true):+.1f} / {float(m_true @ lo - c_true):+.1f} mm)。")
    print("    どちらが患側かは鏡映だけでは決まらない。★穴 H: 群集平均(統計形状モデル)が要る。")

    print("\n=== 6. 壊れる条件 ===")
    print("  (a) 変形が大きすぎる —— PCA が別の主軸を選び、面が丸ごと飛ぶ")
    print(f"  {'入れた量':>9}{'真の注入':>10}{'測った max':>12}{'利得':>7}"
          f"{'面の角度':>10}{'選ばれた軸':>11}{'margin':>9}")
    for amp in (6.4, 12.0, 25.0, 40.0):
        Pa = specimen(w_blob, amp)
        truth = float(_surface_deviation(Pa, P_undeformed)[0].max())
        _, _, _, axis, margin = best_pca_plane(Pa)
        aligned, m, c = mirror_pipeline(Pa)
        sm, _ = _surface_deviation(Pa, aligned)
        ang, _off = plane_error(m, c, m_true, c_true)
        print(f"  {amp:>9.1f}{truth:>10.3f}{float(sm.max()):>12.3f}"
              f"{float(sm.max()) / truth:>7.3f}{ang:>10.3f}{axis:>11d}{margin:>9.3f}")
    print(f"     境界は 12 mm と 25 mm の間(全長 {ext[0]:.0f} mm の 5.5 % と 11 %)。")
    print("     変形が主軸そのものを動かしてしまうと、対称面の候補が入れ替わる。")

    print("\n  (b) 点群が粗い —— 床が上がり、信号が沈む(fs.voxel_downsample で間引く)")
    P_dense = posed_cloud(V, F, 40000, 1, R_pose, t_pose)
    P_dense_def = specimen(w_blob, 1.6, n=40000)
    print(f"  {'voxel [mm]':>11}{'点数':>8}{'点間隔':>9}{'床 rms':>10}{'床 |max|':>10}"
          f"{'信号 max':>10}{'信号/床':>9}")
    coarse = {}
    for vx in (0.0, 2.0, 4.0, 8.0, 14.0):
        A = P_dense if vx == 0.0 else fs.voxel_downsample(P_dense, vx)
        B = P_dense_def if vx == 0.0 else fs.voxel_downsample(P_dense_def, vx)
        spacing = float(np.median(cKDTree(A).query(A, k=2)[0][:, 1]))
        fa, _ = _surface_deviation(A, mirror_pipeline(A)[0])
        fb, _ = _surface_deviation(B, mirror_pipeline(B)[0])
        fmax = float(np.abs(fa).max())
        coarse[vx] = (len(A), spacing, fmax, float(fb.max()))
        print(f"  {vx:>11.1f}{len(A):>8d}{spacing:>9.3f}{float(np.sqrt(np.mean(fa ** 2))):>10.4f}"
              f"{fmax:>10.4f}{float(fb.max()):>10.4f}{float(fb.max()) / fmax:>9.2f}")
    print(f"     voxel 8 mm(点間隔 {coarse[8.0][1]:.1f} mm、{coarse[8.0][0]} 点)までは")
    print(f"     1.6 mm の膨らみが床の {coarse[8.0][3] / coarse[8.0][2]:.1f} 倍で残る。"
          f" 14 mm(点間隔 {coarse[14.0][1]:.1f} mm)で床が {coarse[14.0][2]:.2f} mm へ跳ね、")
    print(f"     信号/床が {coarse[14.0][3] / coarse[14.0][2]:.2f} まで落ちて検出不能になる"
          f"(近傍不足で法線推定そのものが壊れる)。")

    print("\n  (c) もともと対称に近くない —— 主軸が縮退すると面ごと外し、しかも黙っている")
    print(f"  {'標本':<22}{'外接箱の辺':>26}{'候補スコア':>26}{'margin':>9}{'軸':>4}{'面の角度':>10}")
    degenerate = {}
    for label, mesh_v, mesh_f, kx in (("頭蓋(元)", V, F, 1.0),
                                      ("頭蓋 x 幅 0.82 倍", V, F, 0.82),
                                      ("回転体(x 半軸 = z 半軸)", *revolution_mesh(), 1.0)):
        Vs = np.asarray(mesh_v, float).copy()
        Vs[:, 0] *= kx
        Ns = vertex_normals(Vs, mesh_f)
        ws, _ = blob_weight(Vs, (0.75, 0.35, 0.45), 28.0)
        Pa = posed_cloud(Vs + 6.4 * ws[:, None] * Ns, mesh_f, 12000, 1, R_pose, t_pose)
        e = extents_of(Pa)
        _, n_s, _, axis, margin = best_pca_plane(Pa)
        sc = pca_plane_candidates(Pa)[2]
        ang = math.degrees(math.acos(min(1.0, abs(float(n_s @ m_true)))))
        degenerate[label] = (margin, ang)
        print(f"  {label:<22}{f'{e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f}':>26}"
              f"{f'{sc[0]:.2f} / {sc[1]:.2f} / {sc[2]:.2f}':>26}{margin:>9.3f}{axis:>4d}{ang:>10.2f}")
    print("     回転体では y 軸を含む面がどれも真の対称面なので、正中面を選ぶ根拠がデータに無い。")
    print("     ★穴 D: それでも op は最良候補を 1 つ返すだけで、外したことを何も知らせない。")
    print("     候補スコアの差(margin)が 0.1 を切ったら結果を採用しない、という門は自前で要る。")

    print("\n=== 7. 速度(この機械での実測)===")
    Pt = specimen(w_blob, 1.6, n=20000)
    p0t, nt = best_pca_plane(Pt)[:2]
    Qt = _mirror(Pt, p0t, nt)
    for label, fn in (("fs.sample_surface", lambda: fs.sample_surface(V, F, 20000, seed=2)),
                      ("fs.estimate_normals(k=16)", lambda: fs.estimate_normals(Pt, k=16)),
                      ("fs.voxel_downsample(2 mm)", lambda: fs.voxel_downsample(Pt, 2.0)),
                      ("PCA 候補 3 面の採点", lambda: pca_plane_candidates(Pt)),
                      ("fs.icp(点対点)", lambda: fs.icp(Qt, Pt, max_iter=30, tol=1e-7)),
                      ("fs.point_to_plane_icp", lambda: fs.point_to_plane_icp(
                          Qt, Pt, max_iter=30, tol=1e-7)),
                      ("符号つき距離 + 平滑", lambda: _surface_deviation(Pt, Qt)),
                      ("鏡映 + 位置合わせ 一式", lambda: mirror_pipeline(Pt))):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<28}{1e3 * (time.perf_counter() - t0):>9.1f} ms  (20000 点)")
    t0 = time.perf_counter()
    fs.obb(Pt[:5000])
    ms_obb5 = 1e3 * (time.perf_counter() - t0)
    t0 = time.perf_counter()
    fs.obb(Pt)
    ms_obb20 = 1e3 * (time.perf_counter() - t0)
    t0 = time.perf_counter()
    np.linalg.svd(Pt - Pt.mean(0), full_matrices=False)
    ms_svd = 1e3 * (time.perf_counter() - t0)
    print(f"  ★穴 J: fs.obb 5000 点 {ms_obb5:.0f} ms / 20000 点 {ms_obb20:.0f} ms(点数の 2 乗)。")
    print(f"     中身は (N,3) の SVD 1 回。full_matrices=False なら {ms_svd:.2f} ms"
          f"(**{ms_obb20 / ms_svd:.0f} 倍**)。捨てている U を 20000x20000 = 3.2 GB 確保している。")
    ms_tol, rmse_tol = {}, {}
    for tol in (1e-8, 1e-7):
        t0 = time.perf_counter()
        _, _, _, r = fs.point_to_plane_icp(Qt, Pt, max_iter=60, tol=tol)
        ms_tol[tol], rmse_tol[tol] = 1e3 * (time.perf_counter() - t0), r
    print(f"  (否定した疑い)point_to_plane_icp の tol: 1e-8 {ms_tol[1e-8]:.0f} ms /"
          f" 1e-7 {ms_tol[1e-7]:.0f} ms、rmse 差 {abs(rmse_tol[1e-8] - rmse_tol[1e-7]):.1e}。")
    t0 = time.perf_counter()
    _, _, _, r_short = fs.icp(Qt, Pt, max_iter=3, tol=1e-8)
    ms_short = 1e3 * (time.perf_counter() - t0)
    t0 = time.perf_counter()
    _, _, _, r_long = fs.icp(Qt, Pt, max_iter=60, tol=1e-8)
    ms_long = 1e3 * (time.perf_counter() - t0)
    print(f"     一方 fs.icp(点対点)は 3 反復 {ms_short:.0f} ms(rmse {r_short:.4f})→"
          f" 60 反復 {ms_long:.0f} ms(rmse {r_long:.4f})。20 倍かけて {r_short - r_long:.4f} mm"
          f" しか下がらない —— 目的関数が点間隔ノイズに支配されていて下がる先が無い。")

    print("\n=== 8. ファサードに出ていない op(実行時に確認)===")
    for name in ("reflect_points", "reflection_symmetry_score", "detect_reflection_symmetry",
                 "detect_rotational_symmetry", "chamfer_distance", "hausdorff_distance",
                 "procrustes", "landmarks_3d", "midsagittal_plane", "surface_deviation"):
        print(f"  fullseye.{name:<30}{'あり' if hasattr(fs, name) else 'なし'}")
    print("  → 上 4 つは ops3d の台帳(カテゴリ symmetry)には登録済み。台帳に在ることと")
    print("     consumer から呼べることは別物(★穴 A/B)。下 4 つはそもそも無い(★穴 F/G/I)。")

    # ---- 自己検査(速さは assert しない)------------------------------------
    # 1. 標本が厳密に左右対称であること(ここが崩れると全部の数字が意味を失う)
    assert d_mirror.max() < 1e-9, f"合成頭蓋の頂点集合が左右対称でない ({d_mirror.max():.2e} mm)"
    # 2. 床は 0 ではないが、標本長の 0.1 % 未満に収まること
    assert 0.0 < floor_rms < 0.05, f"床 rms が想定外 ({floor_rms:.4f} mm)"
    assert floor_max < 1e-3 * ext[0], f"床 max が標本長の 0.1 % を超えた ({floor_max:.4f} mm)"
    # 3. 床は点数を増やすと下がる(= サンプリング由来であって実装の非対称ではない)
    assert floors[N_MAIN][0] < floors[2000][0], "点数を増やしても床が下がらない = 系統誤差の疑い"
    # 4. 点対点距離の床は点間隔に比例する(第 2 章の主張そのもの)
    for n in (2000, 5000, N_MAIN, 30000):
        Pn = posed_cloud(V, F, n, 1, R_pose, t_pose)
        p2p = float(np.sqrt(np.mean(cKDTree(mirror_pipeline(Pn)[0]).query(Pn)[0] ** 2)))
        assert 1.1 < p2p / floors[n][2] < 1.35, f"点対点の床 / 点間隔 = {p2p / floors[n][2]:.2f}"
    # 5. 鏡映しないゼロ点は変形量に関係なく 0(盲目であることの明示)
    for amp in (0.5, 4.0):
        Pz = specimen(w_blob, amp)
        assert np.max(np.abs(_surface_deviation(Pz, Pz)[0])) < 1e-12, "自分と比べて 0 でない"
    # 6. 真の面で鏡映すれば注入量を取り戻せる(利得 ~1)
    truth64 = gains[6.4][0]
    assert 0.95 < sm_ora.max() / truth64 < 1.05, \
        f"真の面でも注入量が戻らない (利得 {sm_ora.max() / truth64:.3f})"
    # 7. 残差最適面は真の面より残差が小さいのに、非対称量は小さく出る(= 引きずられの証拠)
    assert np.sqrt(np.mean(sm_opt ** 2)) < np.sqrt(np.mean(sm_ora ** 2)), \
        "最適面の残差が真の面より大きい = 最適化が効いていない"
    assert sm_opt.max() < 0.75 * sm_ora.max(), "引きずられが再現しない(利得が落ちていない)"
    ang64, off64 = plane_error(m64, c64, m_true, c_true)
    assert ang64 > 1.0 and off64 > 2.0, f"面の引きずられが小さすぎる ({ang64:.2f} deg / {off64:.2f} mm)"
    # 8. _plane_from_map の閉形式が中点集合の平面フィットと一致すること
    p0b, nb = best_pca_plane(P64)[:2]
    Rb, tb, _, _ = fs.point_to_plane_icp(_mirror(P64, p0b, nb), P64, max_iter=30, tol=1e-7)
    Ab = Rb @ (np.eye(3) - 2.0 * np.outer(nb, nb))
    tvb = Rb @ (2.0 * (nb @ p0b) * nb) + tb
    mb, cb = _plane_from_map(Ab, tvb)
    mid = 0.5 * (P64 + P64 @ Ab.T + tvb)
    mid_c = mid.mean(0)
    S, Vt = np.linalg.svd(mid - mid_c, full_matrices=False)[1:]
    thickness = float(S[2] / math.sqrt(len(mid)))
    assert thickness < 1e-8, f"中点集合が平面でない (厚み {thickness:.2e} mm)"
    assert abs(abs(float(Vt[2] @ mb)) - 1.0) < 1e-8, "閉形式の面法線が中点フィットと食い違う"
    assert abs(abs(float(Vt[2] @ mid_c)) - abs(cb)) < 1e-6, "閉形式の面位置が中点フィットと食い違う"
    # 9. 二重ローブ: 最大と最小がほぼ等量で、正中面の反対側に出ること
    assert abs(sm_opt.max() + sm_opt.min()) < 0.1 * sm_opt.max(), "非対称場が二重ローブになっていない"
    assert (float(m_true @ hi - c_true)) * (float(m_true @ lo - c_true)) < 0, \
        "二つのローブが正中面の同じ側にある"
    # 10. 縮退標本では面を外し、margin がそれを予告すること(壊れる条件が本当に壊れる)
    m_ok, a_ok = degenerate["頭蓋(元)"]
    m_rev, a_rev = degenerate["回転体(x 半軸 = z 半軸)"]
    assert a_ok < 5.0 and m_ok > 0.3, f"異方性標本で面を外した ({a_ok:.1f} deg / margin {m_ok:.2f})"
    assert a_rev > 30.0, f"回転体で面を外さない = 壊れる条件の再現に失敗 ({a_rev:.1f} deg)"
    assert m_rev < 0.1, f"回転体の margin が縮退を予告しない ({m_rev:.3f})"
    # 11. 退化入力は黙って嘘の面を返さない
    for bad in (np.zeros((0, 3)), np.zeros((2, 3))):
        try:
            best_pca_plane(bad)
            raise AssertionError("退化入力が素通りした")
        except ValueError:
            pass
    print("\nPASS")


if __name__ == "__main__":
    main()

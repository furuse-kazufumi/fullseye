# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""twoview — 2視点エピポーラ幾何(基礎行列 F・本質行列 E・三角測量・相対姿勢復元)。

pnp3d が単視点(既知 3D → 姿勢)なら、twoview は**2 枚の画像の対応点だけ**から相対姿勢と
シーン構造を復元する(Structure-from-Motion / Visual Odometry の核)。正規化 8 点法で F を解き、
K 既知なら E=K2ᵀF K1 に変換、E を分解して 4 つの (R,t) 候補を得、cheirality(全点 depth>0)で
一意化する。三角測量は DLT。並進 t はスケール不定(単眼の本質的曖昧性)なので単位ベクトルで扱う。

規約: 同次座標 x=(u,v,1)、エピポーラ拘束 x2ᵀ F x1 = 0。P=K[R|t]。cam1 は [I|0] 基準。
GT 検証 = 合成 2 カメラで投影 → F 拘束残差 ~0・R 誤差<1°・t 方向誤差<1°・三角測量再投影<1e-6。

用途: 単眼 SfM/VO、ステレオ較正の確認、多視点再構成の初期化(Physical AI の空間認識)。
"""
import numpy as np


def _to_homog(pts):
    """2D 点 (N,2) → 同次 (N,3)。"""
    p = np.asarray(pts, float)
    return np.hstack([p, np.ones((len(p), 1))])


def _normalize_points(pts):
    """Hartley 正規化: 重心を原点・平均距離 √2 に。→ (正規化点 (N,2), 変換 T (3,3))。"""
    p = np.asarray(pts, float)
    c = p.mean(axis=0)
    mean_dist = np.mean(np.linalg.norm(p - c, axis=1))
    s = np.sqrt(2.0) / (mean_dist + 1e-12)
    T = np.array([[s, 0, -s * c[0]],
                  [0, s, -s * c[1]],
                  [0, 0, 1.0]])
    pn = (T @ _to_homog(p).T).T
    return pn[:, :2], T


def fundamental_8point(pts1, pts2):
    """正規化 8 点法で基礎行列 F を推定(rank-2 強制)。→ F (3,3)。8 点以上必要。"""
    p1 = np.asarray(pts1, float)
    p2 = np.asarray(pts2, float)
    if len(p1) < 8 or len(p2) < 8:
        raise ValueError("8 点法は 8 点以上必要")
    if len(p1) != len(p2):
        raise ValueError("対応点数が不一致")
    n1, T1 = _normalize_points(p1)
    n2, T2 = _normalize_points(p2)
    x1, y1 = n1[:, 0], n1[:, 1]
    x2, y2 = n2[:, 0], n2[:, 1]
    A = np.stack([x2 * x1, x2 * y1, x2,
                  y2 * x1, y2 * y1, y2,
                  x1, y1, np.ones_like(x1)], axis=1)
    _, _, Vt = np.linalg.svd(A)
    F = Vt[-1].reshape(3, 3)
    # rank-2 強制(基礎行列の性質: det F = 0)
    U, S, Vt2 = np.linalg.svd(F)
    S[2] = 0.0
    F = U @ np.diag(S) @ Vt2
    # 逆正規化: x2ᵀ (T2ᵀ F_n T1) x1 = 0
    F = T2.T @ F @ T1
    scale = F[2, 2] if abs(F[2, 2]) > 1e-12 else np.linalg.norm(F)
    return F / scale


def sampson_distance(F, pts1, pts2):
    """エピポーラ拘束の Sampson 距離(1 次幾何誤差、各対応)。→ (N,)。"""
    F = np.asarray(F, float)
    x1 = _to_homog(pts1)
    x2 = _to_homog(pts2)
    Fx1 = (F @ x1.T).T       # (N,3)
    Ftx2 = (F.T @ x2.T).T    # (N,3)
    num = np.sum(x2 * Fx1, axis=1) ** 2
    den = Fx1[:, 0] ** 2 + Fx1[:, 1] ** 2 + Ftx2[:, 0] ** 2 + Ftx2[:, 1] ** 2
    return num / (den + 1e-12)


def essential_from_fundamental(F, K1, K2=None):
    """基礎行列 → 本質行列 E = K2ᵀ F K1(特異値を (1,1,0) に整形)。→ E (3,3)。"""
    K1 = np.asarray(K1, float)
    K2 = K1 if K2 is None else np.asarray(K2, float)
    E = K2.T @ np.asarray(F, float) @ K1
    U, _, Vt = np.linalg.svd(E)
    return U @ np.diag([1.0, 1.0, 0.0]) @ Vt


def essential_8point(pts1, pts2, K1, K2=None):
    """対応点 + K から本質行列 E を直接。→ E (3,3)。"""
    F = fundamental_8point(pts1, pts2)
    return essential_from_fundamental(F, K1, K2)


def decompose_essential(E):
    """本質行列 E を 4 つの (R,t) 候補に分解(t は単位ベクトル)。→ [(R,t),...] 長さ 4。"""
    U, _, Vt = np.linalg.svd(np.asarray(E, float))
    if np.linalg.det(U) < 0:
        U = -U
    if np.linalg.det(Vt) < 0:
        Vt = -Vt
    W = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]])
    R1 = U @ W @ Vt
    R2 = U @ W.T @ Vt
    t = U[:, 2]
    return [(R1, t), (R1, -t), (R2, t), (R2, -t)]


def triangulate(pts1, pts2, P1, P2):
    """DLT 三角測量: 2 視点の対応点 + 射影行列 → 3D 点。→ (N,3)。"""
    p1 = np.asarray(pts1, float)
    p2 = np.asarray(pts2, float)
    P1 = np.asarray(P1, float)
    P2 = np.asarray(P2, float)
    out = np.zeros((len(p1), 3))
    for i in range(len(p1)):
        x1, y1 = p1[i]
        x2, y2 = p2[i]
        A = np.stack([x1 * P1[2] - P1[0],
                      y1 * P1[2] - P1[1],
                      x2 * P2[2] - P2[0],
                      y2 * P2[2] - P2[1]])
        _, _, Vt = np.linalg.svd(A)
        X = Vt[-1]
        out[i] = X[:3] / X[3]
    return out


def _projection_matrices(R, t, K1, K2):
    """cam1=K1[I|0], cam2=K2[R|t] の射影行列。→ (P1, P2)。"""
    P1 = K1 @ np.hstack([np.eye(3), np.zeros((3, 1))])
    P2 = K2 @ np.hstack([R, np.asarray(t, float).reshape(3, 1)])
    return P1, P2


def _cheirality_count(R, t, pts1, pts2, K1, K2):
    """候補 (R,t) で三角測量し、両カメラ前方(depth>0)の点数を数える。→ (count, X)。"""
    P1, P2 = _projection_matrices(R, t, K1, K2)
    X = triangulate(pts1, pts2, P1, P2)
    z1 = X[:, 2]
    z2 = ((R @ X.T).T + np.asarray(t, float))[:, 2]
    return int(np.sum((z1 > 0) & (z2 > 0))), X


def _homography_dlt(pts1, pts2):
    """正規化 DLT でホモグラフィ H (pts1→pts2) を推定。→ H (3,3)。平面退化検出に使う。

    平面シーン/純回転では対応点が単一 H を厳密に満たす。4 点以上必要(通常は 8 点法と同数)。
    """
    p1 = np.asarray(pts1, float)
    p2 = np.asarray(pts2, float)
    n1, T1 = _normalize_points(p1)
    n2, T2 = _normalize_points(p2)
    rows = []
    for (x, y), (u, v) in zip(n1, n2):
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
    _, _, Vt = np.linalg.svd(np.asarray(rows, float))
    H = Vt[-1].reshape(3, 3)
    H = np.linalg.inv(T2) @ H @ T1     # 逆正規化
    denom = H[2, 2] if abs(H[2, 2]) > 1e-12 else (np.linalg.norm(H) + 1e-12)
    return H / denom


def _planar_degeneracy_ratio(pts1, pts2):
    """対応点が単一ホモグラフィでどれだけ説明できるか(スケール不変)。→ float(小=平面的)。

    平面(共平面 3D)/純回転シーンでは 1 つの H が全対応を厳密に満たすため、本質行列分解は
    退化する(F は 2 パラメータ族に縮退)。H の対称転送残差の中央値を点群の広がりで正規化して
    返す。値が小さいほど平面的=退化。三角測量後の構造ではなく **入力対応点** で判定するのは、
    退化時に復元姿勢が誤るため三角測量済み構造が平面性を保たない(スケール不変な共分散比でも
    seed により 0.003〜0.44 と散らばり分離不能)ことを実測で確認したため。
    """
    p1 = np.asarray(pts1, float)
    p2 = np.asarray(pts2, float)
    try:
        H = _homography_dlt(p1, p2)
        Hi = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        return 0.0   # H が特異=極度の退化。fail-closed で平面扱い
    fwd = (H @ _to_homog(p1).T).T
    fwd = fwd[:, :2] / fwd[:, 2:3]
    bwd = (Hi @ _to_homog(p2).T).T
    bwd = bwd[:, :2] / bwd[:, 2:3]
    resid = np.linalg.norm(fwd - p2, axis=1) + np.linalg.norm(bwd - p1, axis=1)
    scale = (np.mean(np.linalg.norm(p1 - p1.mean(axis=0), axis=1))
             + np.mean(np.linalg.norm(p2 - p2.mean(axis=0), axis=1)))
    return float(np.median(resid) / (scale + 1e-12))


def recover_pose(pts1, pts2, K1, K2=None, planar_tol=1e-2):
    """対応点 + K から相対姿勢 (R,t) と 3D 構造を復元(cheirality で一意化)。→ (R, t_unit, points3d)。

    t はスケール不定なので単位ベクトル。points3d は cam1 座標系(|t|=1 に対応するスケール)。

    fail-closed: 平面(共平面 3D)/純回転シーンは本質行列分解の**退化配置**で、Sampson 残差 ~0 の
    まま並進方向を誤って返す(見かけは完璧)。そうした入力は姿勢を復元できないため ValueError で
    明示拒否する(ホモグラフィ分解を使うこと)。`planar_tol` はスケール不変な平面度しきい値
    (`_planar_degeneracy_ratio` の戻り値がこれ未満なら退化と判定)。
    """
    K1 = np.asarray(K1, float)
    K2 = K1 if K2 is None else np.asarray(K2, float)
    p1 = np.asarray(pts1, float)
    p2 = np.asarray(pts2, float)
    if len(p1) < 8 or len(p2) < 8:
        raise ValueError("8 点法は 8 点以上必要")
    if len(p1) != len(p2):
        raise ValueError("対応点数が不一致")
    ratio = _planar_degeneracy_ratio(p1, p2)
    if ratio < planar_tol:
        raise ValueError(
            "平面(共平面 3D)/純回転シーンは本質行列分解が退化するため recover_pose では"
            f"相対姿勢を復元できない(平面度 ratio={ratio:.2e} < tol={planar_tol:g})。"
            "この配置ではホモグラフィ分解(H = K2⁻¹·(画像ホモグラフィ)·K1 の分解)を用いること。"
        )
    E = essential_8point(pts1, pts2, K1, K2)
    best = None
    for R, t in decompose_essential(E):
        cnt, X = _cheirality_count(R, t, pts1, pts2, K1, K2)
        if best is None or cnt > best[0]:
            best = (cnt, R, t, X)
    _, R, t, X = best
    return R, t, X

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""剛体運動セグメンテーション — 2 点群を運動が一致する剛体ごとに分割(numpy + scipy)。

観測 2 時刻の**非構造点群** ``pts0`` -> ``pts1`` を、それぞれが独立の剛体運動を
する複数の物体(dynamic scene)に**分割**する。各点に最近傍フローを与え、反復
RANSAC で「1 つの剛体運動で説明できる点集合(inlier)」を大きい順に切り出しては
除去し、残った点を outlier(label = -1)にする。

固有価値(既存 3D フローとの棲み分け):
  * :func:`match3d.scene_flow_lk` は voxel 化 + Lucas-Kanade の**密フロー**(規則格子
    上・単一運動場)。本モジュールは生の点群を扱い、運動を**物体ごとに離散ラベル化**する。
  * :mod:`scene_flow3d` はシーン**全体を単一剛体 + 残差**へ分解する(物体は 1 つ想定)。
    本モジュールは **N 個の剛体への分割**(左半分は並進・右半分は回転…のような
    multi-body motion)そのものを固有の対象にする。物体数は未知で、データから決める。
  * 剛体推定は閉形式 Kabsch(:func:`registration.kabsch`)を再利用し、ここでは
    「フロー整合による multi-body RANSAC 分割」に固有価値を置く。

限界(honest / self_reported):
  * 最近傍対応は各物体の変位が局所点間隔より十分小さい前提(小運動)で正しい。大変位・
    物体が空間的に重なる場合は対応が破綻し分割が乱れる。
  * RANSAC はランダム性を持つ(``seed`` で再現可能化)。稀に劣物体を先に取ると分割が
    ずれる。inlier 判定に使う target は**全** ``pts1`` への最近傍で固定するため、物体
    除去後も target は動かさない(除去後の再対応はしない = 単純化)。
  * outlier / 未対応点は詐称せず label = -1 に落とす。物体数は ``max_bodies`` で上限。

参考(public):Fischler & Bolles, "Random Sample Consensus", CACM 1981(RANSAC);
Kabsch, Acta Cryst. 1976(閉形式剛体);Torr & Zisserman の multi-model fitting 系譜。
"""
from __future__ import annotations

import numpy as np

from registration import kabsch, apply_transform

__all__ = ["estimate_flow", "fit_rigid", "segment_rigid_motions"]


def _as_points(a, name: str) -> np.ndarray:
    """(N, 3) float64 に検証変換(不正形状・非有限は fail-closed で ValueError)。"""
    P = np.asarray(a, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"{name} must be an (N, 3) array, got shape {P.shape}")
    if not np.all(np.isfinite(P)):
        raise ValueError(f"{name} contains non-finite values")
    return P


def estimate_flow(pts0, pts1) -> np.ndarray:
    """pts0 の各点から pts1 の最近傍への 3-D 変位ベクトル場 (N, 3) を返す(最近傍フロー)。

    ``pts0`` の各点 p について ``pts1`` 中の最近傍 q を cKDTree で求め、変位 ``q - p``
    を返す。要素数は N != M でよい。変位が局所点間隔より十分小さい小運動でのみ「点 i の
    真の対応先」を当てる(honest な最近傍の限界)。segment_rigid_motions が inlier 判定に
    使う **観測フロー** を与える。

    Args:
        pts0: (N, 3) 時刻 0 の点群。
        pts1: (M, 3) 時刻 1 の点群。
    Returns:
        (N, 3) 変位ベクトル場(pts0 と同じ行順)。空 pts0 は (0, 3) を返す。
    Raises:
        ValueError: 形状不正、または pts0 が非空なのに pts1 が空(最近傍が存在しない)。
    """
    from scipy.spatial import cKDTree

    P0 = _as_points(pts0, "pts0")
    P1 = _as_points(pts1, "pts1")
    if P0.shape[0] == 0:
        return np.empty((0, 3), np.float64)
    if P1.shape[0] == 0:                       # 最近傍が存在しない -> fail-closed
        raise ValueError("pts1 is empty; cannot compute nearest-neighbour flow")
    _, idx = cKDTree(P1).query(P0, k=1)
    idx = np.asarray(idx, dtype=np.intp).reshape(-1)
    return P1[idx] - P0


def fit_rigid(pts_from, pts_to):
    """対応点から閉形式 Kabsch で剛体変換 (R, t) を推定する(pts_from[i] -> pts_to[i])。

    行 i どうしが対応する (N, 3) 2 点集合から、``|| (R·p + t) - q ||`` を最小化する
    proper rotation(det = +1, 反射なし)と並進を返す。:func:`registration.kabsch` の
    薄いラッパで、入力検証を付す(N >= 3 で回転が一意)。

    Args:
        pts_from: (N, 3) 変換元(対応順)。
        pts_to: (N, 3) 変換先(対応順)。
    Returns:
        (R, t): (3, 3) 回転行列, (3,) 並進ベクトル。
    Raises:
        ValueError: 形状不一致 / (N, 3) でない / N < 3 / 非有限。
    """
    P = _as_points(pts_from, "pts_from")
    Q = _as_points(pts_to, "pts_to")
    if P.shape != Q.shape:
        raise ValueError(f"pts_from {P.shape} and pts_to {Q.shape} must match")
    if P.shape[0] < 3:
        raise ValueError("fit_rigid needs at least 3 corresponded points to fix a rotation")
    R, t = kabsch(P, Q)
    return np.asarray(R, np.float64), np.asarray(t, np.float64)


def segment_rigid_motions(pts0, pts1, thresh, max_bodies: int = 5,
                          min_inliers=None, n_iter: int = 100,
                          k_sample: int = 6, seed: int = 0) -> dict:
    """2 点群を運動が一致する剛体ごとに分割する(反復 RANSAC による multi-body 分割)。

    まず :func:`estimate_flow` で観測フロー(各 pts0 点 -> pts1 最近傍)を取り、
    ``target = pts0 + flow`` を対応先として固定する。以後、残り点集合に対して:

      1. 空間的に近い ``k_sample`` 点(seed + その最近傍)を種に Kabsch で剛体仮説を立て、
      2. フロー整合 ``|| (R·s + t) - target(s) || < thresh`` を満たす inlier を数え、
      3. ``n_iter`` 試行で最良仮説を選び、その inlier で Kabsch 再フィット(refine)、
      4. inlier 数が ``min_inliers`` 以上ならそれを 1 剛体として確定・除去。

    を ``max_bodies`` 個または残り点が閾値を下回るまで繰り返す。どの剛体にも属さない残り点は
    ``labels = -1``(outlier / 未対応、詐称しない)。近傍種サンプリングは空間的に連続な物体を
    まとめて掴むための locality prior で、閾値ではなく相対順位だけを使うためスケール不変。

    Args:
        pts0: (N, 3) 時刻 0 の点群。
        pts1: (M, 3) 時刻 1 の点群(N と一致不要)。
        thresh: フロー整合の inlier 距離しきい値。**座標スケール相対**で与えること
            (絶対 epsilon をモジュール内に持たないため、呼び手が座標系に合わせる)。
        max_bodies: 抽出する剛体数の上限(>= 1)。
        min_inliers: 1 剛体と認める最小 inlier 数。None なら ``max(3, round(0.1*N))``。
            outlier の塊を偽の剛体にしないための下限。
        n_iter: 剛体 1 個あたりの RANSAC 試行回数。
        k_sample: 1 仮説を作る種サンプルの点数(seed + 最近傍、>= 3)。
        seed: RANSAC 乱数シード(再現性)。
    Returns:
        dict: ``{"labels": (N,) int(各点の剛体 id、0..K-1 / outlier=-1),
        "motions": [(R, t), ...](id 順の剛体変換、K 個)}``。
    Raises:
        ValueError: 形状不正 / 非有限 / pts1 空 / thresh <= 0 / max_bodies < 1 /
            k_sample < 3。
    """
    P0 = _as_points(pts0, "pts0")
    P1 = _as_points(pts1, "pts1")
    thresh = float(thresh)
    if not np.isfinite(thresh) or thresh <= 0.0:
        raise ValueError("thresh must be a positive, finite scale-relative distance")
    if int(max_bodies) < 1:
        raise ValueError("max_bodies must be >= 1")
    if int(k_sample) < 3:
        raise ValueError("k_sample must be >= 3 (Kabsch needs 3 points to fix a rotation)")

    n = P0.shape[0]
    if n == 0:
        return {"labels": np.empty((0,), np.intp), "motions": []}
    if P1.shape[0] == 0:                       # 最近傍が存在しない -> fail-closed
        raise ValueError("pts1 is empty; cannot segment rigid motions")

    if min_inliers is None:
        min_inliers = max(3, int(round(0.1 * n)))
    min_inliers = max(3, int(min_inliers))

    from scipy.spatial import cKDTree

    # 観測フローと固定 target(全 pts1 への最近傍)。以後 target は動かさない。
    _, tgt_idx = cKDTree(P1).query(P0, k=1)
    targets = P1[np.asarray(tgt_idx, np.intp).reshape(-1)]

    labels = np.full(n, -1, dtype=np.intp)
    motions: list = []
    rng = np.random.default_rng(int(seed))
    remaining = np.arange(n, dtype=np.intp)    # 未割当グローバル index

    for _ in range(int(max_bodies)):
        m = remaining.shape[0]
        if m < min_inliers:                    # 残りで 1 剛体を作れない -> 終了
            break

        rem_pts = P0[remaining]
        rem_tgt = targets[remaining]
        ks = int(min(k_sample, m))
        tree = cKDTree(rem_pts)

        best_count = min_inliers - 1           # >= min_inliers を要求
        best_inl = None
        for _ in range(int(n_iter)):
            s = int(rng.integers(m))
            _, nn = tree.query(rem_pts[s], k=ks)
            samp = np.atleast_1d(np.asarray(nn, np.intp)).reshape(-1)
            if samp.shape[0] < 3:
                continue
            try:
                R, t = kabsch(rem_pts[samp], rem_tgt[samp])
            except ValueError:
                continue
            res = np.linalg.norm(apply_transform(rem_pts, R, t) - rem_tgt, axis=1)
            inl = res < thresh
            c = int(inl.sum())
            if c > best_count:
                best_count = c
                best_inl = inl

        if best_inl is None:                   # min_inliers 以上の仮説なし -> 終了
            break

        # 最良 inlier で剛体を再フィット(refine)し、inlier を確定し直す。
        sel = np.nonzero(best_inl)[0]
        R, t = kabsch(rem_pts[sel], rem_tgt[sel])
        res = np.linalg.norm(apply_transform(rem_pts, R, t) - rem_tgt, axis=1)
        inl = res < thresh
        if int(inl.sum()) < min_inliers:       # refine 後に痩せたら偽物 -> 終了
            break

        body_id = len(motions)
        labels[remaining[inl]] = body_id
        motions.append((np.asarray(R, np.float64), np.asarray(t, np.float64)))
        remaining = remaining[~inl]

    return {"labels": labels, "motions": motions}

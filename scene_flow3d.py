# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""点群ベース 3D シーンフロー — 最近傍フロー + 剛体/非剛体分解(numpy + scipy)。

観測 2 時刻の**非構造点群** ``pts0`` -> ``pts1`` の間の 3-D 運動を、
(1) 点ごとの最近傍変位ベクトル、(2) 全体を説明する単一剛体運動(ICP 風 Kabsch)、
(3) 剛体を差し引いた残差(非剛体変形)、(4) 局所平滑化フロー、に分解する。

固有価値(既存との棲み分け):
  * :func:`match3d.scene_flow_lk` は voxel 化 + Lucas-Kanade の**構造化**フロー
    (規則格子上・微分ベース)。本モジュールは voxel 化せず、順序も要素数も
    揃っていない**生の点群**を cKDTree の最近傍対応で直接扱う(点数 N != M 可)。
  * :mod:`sceneflow` は 2-D 画像上の光学フロー / 自己運動(発散・curl・FoE・TTC)。
    本モジュールは 3-D 点群空間そのものを対象とする。
  * 剛体推定は :func:`registration.kabsch`(閉形式 Procrustes)を再利用し、
    ここでは「剛体運動 + 残差変形」というフローの**分解**に固有価値を置く。

限界(honest / self_reported):最近傍対応は変位が局所点間隔より十分小さい前提で
正しい。大変位や大回転では対応が破綻し、ICP は局所解に落ちうる(収束保証なし)。
残差は「剛体で説明できない成分」であって真の非剛体対応そのものではない。

参考(public):Besl & McKay, "A Method for Registration of 3-D Shapes", TPAMI 1992
(ICP);Kabsch, Acta Cryst. 1976(閉形式剛体);Vedula et al., "Three-Dimensional
Scene Flow", ICCV 1999(scene flow の概念)。
"""
from __future__ import annotations

import numpy as np

from registration import kabsch, apply_transform

__all__ = [
    "nearest_neighbor_flow",
    "rigid_flow",
    "residual_flow",
    "smooth_flow",
]


def _as_points(a, name: str) -> np.ndarray:
    """(N, 3) float64 に検証変換(不正形状は fail-closed で ValueError)。"""
    P = np.asarray(a, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"{name} must be an (N, 3) array, got shape {P.shape}")
    if not np.all(np.isfinite(P)):
        raise ValueError(f"{name} contains non-finite values")
    return P


def nearest_neighbor_flow(pts0, pts1) -> np.ndarray:
    """各点 pts0 から pts1 の最近傍への 3-D 変位ベクトル場 (N, 3) を返す。

    ``pts0`` の各点 p について ``pts1`` 中の最近傍 q を cKDTree で求め、変位
    ``q - p`` を返す。要素数は N != M でよい。変位が局所点間隔より十分小さい
    とき(小さな運動)にのみ「点 i の真の対応先」を当てる — 大変位では最近傍が
    別点に張り付く(honest な限界、正則化には :func:`smooth_flow` を併用)。

    Args:
        pts0: (N, 3) 時刻 0 の点群。
        pts1: (M, 3) 時刻 1 の点群。
    Returns:
        (N, 3) 変位ベクトル場(pts0 と同じ行順)。
    Raises:
        ValueError: 形状不正、または pts0 が非空なのに pts1 が空。
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


def rigid_flow(pts0, pts1, max_iter: int = 20) -> dict:
    """pts0 -> pts1 を説明する単一剛体運動を最近傍対応 + Kabsch(ICP 風)で推定。

    恒等変換から出発し、毎反復で現姿勢の点群から ``pts1`` への最近傍対応を取り、
    :func:`registration.kabsch` で閉形式に (R, t) を求めて累積する。対応 index が
    前反復と一致(= 収束)するか ``max_iter`` で停止する。収束判定は index の
    安定性のみに依存するため**スケール不変**(絶対 epsilon を使わない)。

    Args:
        pts0: (N, 3) 時刻 0 の点群(N >= 3、回転を一意に決めるため)。
        pts1: (M, 3) 時刻 1 の点群(M >= 1、N と一致不要)。
        max_iter: ICP 反復上限。
    Returns:
        dict: ``{"R": (3,3) 回転, "t": (3,) 並進, "rmse": 整合後の点-最近傍
        RMS 距離}``。R は真の回転(det=+1)。rmse は実測値(詐称なし)。
    Raises:
        ValueError: 形状不正、pts0 < 3 点、または pts1 が空。
    """
    from scipy.spatial import cKDTree

    P0 = _as_points(pts0, "pts0")
    P1 = _as_points(pts1, "pts1")
    if P0.shape[0] < 3:
        raise ValueError("rigid_flow needs at least 3 points in pts0 to fix a rotation")
    if P1.shape[0] == 0:
        raise ValueError("pts1 is empty; cannot estimate rigid motion")

    tree = cKDTree(P1)
    R_tot = np.eye(3, dtype=np.float64)
    t_tot = np.zeros(3, dtype=np.float64)
    cur = P0.copy()
    prev_idx = None
    for _ in range(int(max_iter)):
        _, idx = tree.query(cur, k=1)
        idx = np.asarray(idx, dtype=np.intp).reshape(-1)
        if prev_idx is not None and np.array_equal(idx, prev_idx):
            break
        prev_idx = idx
        R, t = kabsch(cur, P1[idx])
        cur = cur @ R.T + t                    # cur <- R*cur + t
        R_tot = R @ R_tot
        t_tot = R @ t_tot + t

    d, _ = tree.query(cur, k=1)
    rmse = float(np.sqrt(np.mean(np.asarray(d, np.float64) ** 2)))
    return {"R": R_tot, "t": t_tot, "rmse": rmse}


def residual_flow(pts0, pts1, R, t) -> np.ndarray:
    """剛体 (R, t) を差し引いた残差フロー(非剛体成分) (N, 3) を返す。

    ``pts0`` を剛体変換した位置 ``warped = R*pts0 + t`` を基準に、そこから
    ``pts1`` の最近傍への変位を残差とする(= 剛体で説明できなかった運動)。
    完全剛体なら warped は pts1 集合と一致し残差は 0 に潰れる。基準点を warped に
    取るため大きな剛体運動があっても残差だけを正しく取り出せる(pts0 基準だと
    剛体分が混入する)。

    Args:
        pts0: (N, 3) 時刻 0 の点群。
        pts1: (M, 3) 時刻 1 の点群。
        R: (3, 3) 剛体回転(:func:`rigid_flow` の出力)。
        t: (3,) 剛体並進。
    Returns:
        (N, 3) 残差変位ベクトル場。
    Raises:
        ValueError: 形状不正、または pts1 が空。
    """
    from scipy.spatial import cKDTree

    P0 = _as_points(pts0, "pts0")
    P1 = _as_points(pts1, "pts1")
    Rm = np.asarray(R, np.float64)
    tv = np.asarray(t, np.float64)
    if Rm.shape != (3, 3) or tv.shape != (3,):
        raise ValueError("R must be (3, 3) and t must be (3,)")
    if P0.shape[0] == 0:
        return np.empty((0, 3), np.float64)
    if P1.shape[0] == 0:
        raise ValueError("pts1 is empty; cannot compute residual flow")

    warped = apply_transform(P0, Rm, tv)
    _, idx = cKDTree(P1).query(warped, k=1)
    idx = np.asarray(idx, dtype=np.intp).reshape(-1)
    return P1[idx] - warped


def smooth_flow(pts0, pts1, k: int = 10, n_iter: int = 5) -> np.ndarray:
    """最近傍フローを近傍平均で局所平滑化した正則化フロー (N, 3) を返す。

    :func:`nearest_neighbor_flow` の生フロー(最近傍対応ゆえノイズが乗る)を、
    ``pts0`` 空間の k 近傍トポロジ(自身を含む、1 度だけ構築)で反復平均する。
    ゼロ平均ノイズを抑えつつ滑らかな変位場は概ね保存する(Jacobi 反復 =
    フロー場のラプラシアン平滑化)。線形場は対称近傍で不偏、曲率のある場は
    僅かに縮む(honest な平滑化バイアス)。

    Args:
        pts0: (N, 3) 時刻 0 の点群。
        pts1: (M, 3) 時刻 1 の点群。
        k: 平均に使う近傍数(自身含む)。
        n_iter: 平滑化反復回数。
    Returns:
        (N, 3) 平滑化変位ベクトル場。
    Raises:
        ValueError: 形状不正、または pts0 非空なのに pts1 が空。
    """
    from scipy.spatial import cKDTree

    P0 = _as_points(pts0, "pts0")
    flow = nearest_neighbor_flow(P0, pts1)     # 形状検証・空 pts1 の fail-closed もここで
    n = P0.shape[0]
    if n == 0:
        return flow
    kk = int(min(max(1, k), n))
    _, idx = cKDTree(P0).query(P0, k=kk)
    idx = np.asarray(idx, dtype=np.intp).reshape(n, kk)   # (N, kk) 自身を含む
    for _ in range(int(n_iter)):
        flow = flow[idx].mean(axis=1)
    return flow

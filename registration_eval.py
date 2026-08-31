# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""registration_eval — 点群登録(ICP/GICP/FPFH)の公正評価メトリクス。

:mod:`metrics3d`(chamfer / F-score / pose_error 等の再構成メトリクス)を補完し、
**推定した剛体変換そのものの良さ**を数値化する登録ベンチの土台:

- :func:`inlier_ratio` — 与えた対応集合(source[i]↔target[i])のうち、推定変換下で
  残差 < thresh に収まる割合(Predator/GeoTransformer の Inlier Ratio, IR)。
- :func:`rmse_inliers` — その inlier 上の RMSE(+ inlier 数)。登録残差の実測。
- :func:`registration_recall` — 3DMatch 流の per-pair 成否指標。GT 変換で
  対応(重なり)を張り、**推定変換**でその対応の RMSE を測り thresh を切るかで 1/0。
- :func:`rotation_translation_error` — 2 つの 4×4 変換間の相対回転誤差(測地角[度],
  RRE)と相対並進誤差(RTE)。

これらは register_auto のヒューリスティック選択(近=ICP / 遠=FPFH+ICP)を
「変換品質を最大化する fitness ベース選択」へ引き上げるための、手法非依存な
共通ものさし。:mod:`metrics3d` の ``pose_error``(R,t を個別受け取り)と異なり、
本モジュールは **登録標準の 4×4 同次変換** で統一し、対応集合ベースの IR/RMSE と
重なりベースの Registration Recall を提供する(役割が別物)。

すべて閉形式・GT 検証可能: est=gt なら recall=1・rmse≈0・角度誤差 0 / est に既知
誤差を入れると誤差はその値そのもの / inlier_ratio は thresh に単調非減少。
しきい値 thresh はデータ単位(スケール相対)。形状不正は fail-closed(ValueError)。

依存: numpy + scipy(cKDTree)のみ。cv2/skimage 不使用。
参考(公開): Zeng+ *3DMatch* CVPR 2017(Registration Recall);
Huang+ *Predator* CVPR 2021 / Qin+ *GeoTransformer* CVPR 2022(Inlier Ratio)。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "registration_recall",
    "inlier_ratio",
    "rmse_inliers",
    "rotation_translation_error",
    "make_transform",
    "transform_points",
]


# ─────────────────────────────────────────────────────────────────────────
# 入力検証(fail-closed)
# ─────────────────────────────────────────────────────────────────────────
def _as_transform(T, name: str = "transform") -> np.ndarray:
    """4×4 同次変換として検証。型・形状不正・非有限は ValueError(fail-closed)。"""
    try:
        A = np.asarray(T, np.float64)
    except (TypeError, ValueError) as e:
        # 連鎖ファザー実測(wave-4): dict 等の非数値プール産物が np.asarray で
        # 形状チェックに届く前に生 TypeError 化していた。明示 ValueError で拒否。
        raise ValueError(
            f"{name}: a numeric 4x4 homogeneous transform is required "
            f"(got {type(T).__name__})") from e
    if A.shape != (4, 4):
        raise ValueError(f"{name}: a 4x4 homogeneous transform is required (got shape {A.shape})")
    if not np.all(np.isfinite(A)):
        raise ValueError(f"{name}: contains non-finite values (NaN/Inf)")
    return A


def _as_points(P, name: str = "points") -> np.ndarray:
    """(N,3) 非空点群として検証。型・形状不正・非有限は ValueError(fail-closed)。"""
    try:
        A = np.asarray(P, np.float64)
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"{name}: a numeric (N,3) point cloud is required "
            f"(got {type(P).__name__})") from e
    if A.ndim != 2 or A.shape[1] != 3 or A.shape[0] < 1:
        raise ValueError(f"{name}: a non-empty (N,3) point cloud is required (got shape {A.shape})")
    if not np.all(np.isfinite(A)):
        raise ValueError(f"{name}: contains non-finite values (NaN/Inf)")
    return A


def _check_thresh(thresh, name: str = "thresh") -> float:
    """正の有限しきい値として検証。非数値・非正・非有限は ValueError(fail-closed)。"""
    try:
        t = float(thresh)
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"{name} must be a positive finite scalar "
            f"(got {type(thresh).__name__})") from e
    if not np.isfinite(t) or t <= 0.0:
        raise ValueError(f"{name} must be a positive finite value (got {thresh})")
    return t


# ─────────────────────────────────────────────────────────────────────────
# 変換ユーティリティ
# ─────────────────────────────────────────────────────────────────────────
def make_transform(R, t) -> np.ndarray:
    """回転 (3×3) と並進 (3,) から 4×4 同次変換を組む。→ (4,4)。"""
    Rm = np.asarray(R, np.float64)
    tv = np.asarray(t, np.float64).reshape(-1)
    if Rm.shape != (3, 3):
        raise ValueError(f"make_transform: R must be 3x3 (got {Rm.shape})")
    if tv.shape != (3,):
        raise ValueError(f"make_transform: t must have length 3 (got {tv.shape})")
    T = np.eye(4, dtype=np.float64)
    T[:3, :3] = Rm
    T[:3, 3] = tv
    return T


def transform_points(T, points) -> np.ndarray:
    """4×4 同次変換を点群 (N,3) に適用 = (R·p + t)。→ (N,3)。"""
    A = _as_transform(T)
    P = _as_points(points)
    return P @ A[:3, :3].T + A[:3, 3]


# ─────────────────────────────────────────────────────────────────────────
# 評価メトリクス
# ─────────────────────────────────────────────────────────────────────────
def inlier_ratio(source, target, transform, thresh: float) -> float:
    """対応集合の inlier 率 = ‖T·source[i] − target[i]‖ < thresh の割合。→ [0,1]。

    ``source`` と ``target`` は **index 対応**(source[i] が target[i] に対応)の
    同数点群(FPFH 等の putative correspondence を想定)。thresh に単調非減少。
    形状不一致・非 (N,3) は ValueError(fail-closed)。
    """
    S = _as_points(source, "source")
    Tg = _as_points(target, "target")
    if S.shape != Tg.shape:
        raise ValueError(
            f"inlier_ratio: source and target must have the same number of corresponding points"
            f" ({S.shape} vs {Tg.shape})")
    T = _as_transform(transform)
    tau = _check_thresh(thresh)
    res = np.linalg.norm(S @ T[:3, :3].T + T[:3, 3] - Tg, axis=1)
    return float(np.mean(res < tau))


def rmse_inliers(source, target, transform, thresh: float):
    """inlier 対応(残差 < thresh)上の RMSE と inlier 数。→ (rmse, n_inliers)。

    ``source[i]↔target[i]`` の index 対応が前提(:func:`inlier_ratio` と同じ)。
    inlier が 0 個なら RMSE は未定義 → ``(nan, 0)`` を返す(honest; 捏造しない)。
    形状不一致・非 (N,3) は ValueError(fail-closed)。
    """
    S = _as_points(source, "source")
    Tg = _as_points(target, "target")
    if S.shape != Tg.shape:
        raise ValueError(
            f"rmse_inliers: source and target must have the same number of corresponding points"
            f" ({S.shape} vs {Tg.shape})")
    T = _as_transform(transform)
    tau = _check_thresh(thresh)
    res = np.linalg.norm(S @ T[:3, :3].T + T[:3, 3] - Tg, axis=1)
    mask = res < tau
    n = int(mask.sum())
    if n == 0:
        return float("nan"), 0
    rmse = float(np.sqrt(np.mean(res[mask] ** 2)))
    return rmse, n


def registration_recall(source, target, gt_transform, est_transform,
                        thresh: float, *, corr_thresh: float | None = None) -> float:
    """3DMatch 流の per-pair 登録成否 = 1.0(成功)/ 0.0(失敗)。

    GT 変換 ``gt_transform`` で source を target フレームへ写し、target 側の最近傍
    (距離 < ``corr_thresh``、既定は thresh)を GT 対応(=重なり)として張る。その
    対応を **推定変換** ``est_transform`` で写した RMSE が ``thresh`` を切れば成功。

    ``source``/``target`` は index 対応でなくてよい(対応は GT から張るため target の
    並びに依存しない)。GT 重なりが 1 点も無ければ成否は未定義 → ``nan``(honest)。
    データセット全体の Registration Recall はこの per-pair 指標(重なり有ペア上)の平均。
    形状不正は ValueError(fail-closed)。
    """
    from scipy.spatial import cKDTree

    S = _as_points(source, "source")
    Tg = _as_points(target, "target")
    Tgt = _as_transform(gt_transform, "gt_transform")
    Test = _as_transform(est_transform, "est_transform")
    tau = _check_thresh(thresh)
    cr = tau if corr_thresh is None else _check_thresh(corr_thresh, "corr_thresh")

    # GT 変換下で対応(重なり)を張る — est に依存しない
    S_gt = S @ Tgt[:3, :3].T + Tgt[:3, 3]
    dist, idx = cKDTree(Tg).query(S_gt, k=1)
    keep = dist < cr
    if not np.any(keep):
        return float("nan")  # GT 重なり無し → 未定義

    p = S[keep]
    q = Tg[idx[keep]]
    S_est = p @ Test[:3, :3].T + Test[:3, 3]
    rmse = float(np.sqrt(np.mean(np.sum((S_est - q) ** 2, axis=1))))
    return 1.0 if rmse < tau else 0.0


def rotation_translation_error(gt, est):
    """2 つの 4×4 変換間の相対回転誤差(測地角[度], RRE)と相対並進誤差(RTE)。

    RRE = 角度(gt_R^T · est_R) = arccos((tr−1)/2) を度で。任意軸まわりの角 θ の
    回転差なら RRE=θ。RTE = ‖gt_t − est_t‖。→ (rre_deg, rte)。
    非 4×4 は ValueError(fail-closed)。
    """
    G = _as_transform(gt, "gt")
    E = _as_transform(est, "est")
    dR = G[:3, :3].T @ E[:3, :3]
    cos = np.clip((np.trace(dR) - 1.0) / 2.0, -1.0, 1.0)
    rre = float(np.degrees(np.arccos(cos)))
    rte = float(np.linalg.norm(G[:3, 3] - E[:3, 3]))
    return rre, rte

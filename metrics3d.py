# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""metrics3d — 3D 再構成 / 登録の評価メトリクス(進化探索の fitness 土台)。

点群・voxel・法線・姿勢の一致度を数値化する: chamfer / Hausdorff / F-score /
completeness・accuracy / normal consistency / voxel IoU / pose error / RMSE。

これらは **3D パイプラインの進化探索で fitness としてそのまま使える**。register_auto の
ヒューリスティック選択(近=ICP / 遠=FPFH+ICP)を、これらメトリクスを最小化/最大化する
fitness ベース選択へ引き上げる鍵。すべて閉形式・GT 検証可能(同一入力→完全一致、
既知オフセット→距離=オフセット)。scipy.spatial.cKDTree のみ依存。
"""
import numpy as np


def _kd(pts):
    from scipy.spatial import cKDTree
    return cKDTree(np.asarray(pts, float))


def _require_cloud(pts, name):
    """空でない (N,3) 点群であることを入口で保証(fail-closed)。

    空点群の平均は無言の NaN になり、進化探索の fitness に毒として流れ込む
    (連鎖ファザー wave-7 実測: radius_outlier_removal が雲を空にした直後の
    chamfer_distance が NaN。同クラスを accuracy/completeness/fscore/
    normal_consistency でも実測確認し一掃)。空になるのは上流フィルタの
    パラメータ事故なので、メトリクス側は数を返さず明示的に拒否する。
    """
    p = np.asarray(pts, float)
    if p.ndim != 2 or p.shape[1] != 3:
        raise ValueError("%s must be an (N, 3) point cloud, got shape %r"
                         % (name, p.shape))
    if len(p) == 0:
        raise ValueError("%s is empty — an upstream filter (outlier removal / "
                         "cropping / downsampling) probably removed every "
                         "point; the metric would be a silent NaN" % (name,))
    return p


def _nn_dist(a, b):
    """a の各点 → b への最近傍距離。→ (Na,)。"""
    d, _ = _kd(b).query(np.asarray(a, float), k=1)
    return d


def chamfer_distance(a, b, squared=False):
    """対称 Chamfer 距離 = 0.5*(mean_a min_b + mean_b min_a)。→ scalar。小さいほど一致。

    Raises ValueError: どちらかが空 or (N,3) でない場合(空の平均 = 無言 NaN)。"""
    a = _require_cloud(a, "a")
    b = _require_cloud(b, "b")
    dab = _nn_dist(a, b)
    dba = _nn_dist(b, a)
    if squared:
        dab, dba = dab ** 2, dba ** 2
    return float(0.5 * (dab.mean() + dba.mean()))


def hausdorff_distance(a, b):
    """対称 Hausdorff 距離 = max(max_a min_b, max_b min_a)。→ scalar。最悪ケースの乖離。"""
    return float(max(_nn_dist(a, b).max(), _nn_dist(b, a).max()))


def accuracy(a, b, tau):
    """正確性 = a の点のうち b から tau 以内にある割合(precision)。→ [0,1]。

    Raises ValueError: どちらかが空 or (N,3) でない場合(空の平均 = 無言 NaN)。"""
    return float(np.mean(_nn_dist(_require_cloud(a, "a"),
                                  _require_cloud(b, "b")) < tau))


def completeness(a, b, tau):
    """完全性 = b の点のうち a から tau 以内にある割合(recall)。→ [0,1]。

    Raises ValueError: どちらかが空 or (N,3) でない場合(空の平均 = 無言 NaN)。"""
    return float(np.mean(_nn_dist(_require_cloud(b, "b"),
                                  _require_cloud(a, "a")) < tau))


def fscore(a, b, tau):
    """F-score @ tau = precision と recall の調和平均。→ (f, precision, recall)。再構成の標準指標。

    Raises ValueError: どちらかが空 or (N,3) でない場合(accuracy/completeness 経由)。"""
    p = accuracy(a, b, tau)
    r = completeness(a, b, tau)
    f = 0.0 if (p + r) == 0 else 2 * p * r / (p + r)
    return f, p, r


def rmse_correspondence(a, b):
    """対応既知(同 index)の RMSE = sqrt(mean |a_i - b_i|^2)。→ scalar。登録残差の評価。"""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if a.shape != b.shape:
        raise ValueError("correspondence points must have equal count and shape")
    return float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))


def normal_consistency(points_a, normals_a, points_b, normals_b):
    """最近傍対応での法線一致度 = mean|cos(na, nb)|(向き無視)。→ [0,1]。1=完全一致。

    Raises ValueError: 点群が空 or (N,3) でない/法線が点と 1 対 1 でない場合。"""
    from scipy.spatial import cKDTree
    pa = _require_cloud(points_a, "points_a")
    pb = _require_cloud(points_b, "points_b")
    na = _require_cloud(normals_a, "normals_a")
    nb_all = _require_cloud(normals_b, "normals_b")
    if len(na) != len(pa) or len(nb_all) != len(pb):
        raise ValueError("normals must pair one normal with each point — "
                         "points_a %d/normals_a %d, points_b %d/normals_b %d"
                         % (len(pa), len(na), len(pb), len(nb_all)))
    _, idx = cKDTree(pb).query(pa, k=1)
    nb = nb_all[idx]
    na = na / (np.linalg.norm(na, axis=1, keepdims=True) + 1e-12)
    nb = nb / (np.linalg.norm(nb, axis=1, keepdims=True) + 1e-12)
    return float(np.mean(np.abs(np.sum(na * nb, axis=1))))


def voxel_iou(vol_a, vol_b, iso=0.5):
    """voxel 占有の IoU(intersection over union)。→ [0,1]。体積一致度。

    両 volume は同一 shape が必須。異形状は numpy broadcasting で見かけ上一致し
    誤った IoU(例: (10,1,10) vs (1,10,10) → 1.0)を静かに返すので、fail-closed で
    shape 不一致は ValueError で拒否する。"""
    a = np.asarray(vol_a)
    b = np.asarray(vol_b)
    if a.shape != b.shape:
        raise ValueError(
            f"voxel_iou: both volumes must have the same shape (got {a.shape} and {b.shape})")
    a = a >= iso
    b = b >= iso
    inter = int(np.logical_and(a, b).sum())
    union = int(np.logical_or(a, b).sum())
    return float(inter / union) if union > 0 else 1.0


def voxel_dice(vol_a, vol_b, iso=0.5):
    """voxel 占有の Dice 係数 = 2|A∩B|/(|A|+|B|)。→ [0,1]。医用でよく使う。

    voxel_iou と同じく、異形状は broadcasting で無意味な値(Dice>1 すら起こる)を
    返すため fail-closed で shape 不一致は ValueError。"""
    a = np.asarray(vol_a)
    b = np.asarray(vol_b)
    if a.shape != b.shape:
        raise ValueError(
            f"voxel_dice: both volumes must have the same shape (got {a.shape} and {b.shape})")
    a = a >= iso
    b = b >= iso
    sa, sb = int(a.sum()), int(b.sum())
    inter = int(np.logical_and(a, b).sum())
    return float(2 * inter / (sa + sb)) if (sa + sb) > 0 else 1.0


def pose_error(R_est, t_est, R_gt, t_gt):
    """姿勢誤差 = (回転角[度], 並進ノルム)。登録結果の GT 比較。→ (rot_deg, trans_err)。"""
    Re = np.asarray(R_est, float)
    Rg = np.asarray(R_gt, float)
    dR = Re.T @ Rg
    cos = np.clip((np.trace(dR) - 1.0) / 2.0, -1.0, 1.0)
    rot = float(np.degrees(np.arccos(cos)))
    trans = float(np.linalg.norm(np.asarray(t_est, float) - np.asarray(t_gt, float)))
    return rot, trans

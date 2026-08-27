"""symmetry3d — 点群の対称性検出(反射面・回転軸)。metrics3d.chamfer を対称スコアに使う。

対称性は形状補完・姿勢正準化・検査(左右差=欠陥)に効く。反射対称は「点群を候補平面で鏡映して
元と重なるか」、回転対称は「軸まわり 2π/order 回転で重なるか」を **chamfer 距離** で採点する
(小さいほど対称)。候補平面/軸は PCA 主軸(重心を通る)から取る — 多くの対称形状は対称面が主軸に整列する。

スコアは RMS 半径で正規化してスケール不変。GT: 楕円体は主軸平面で反射対称(スコア小)、非対称形状は
スコア大、円柱は軸まわり回転対称(任意 order)。metrics3d.chamfer_distance を fitness と同じ土台で流用。

用途: 対称性による形状補完(欠損側を鏡映で埋める)、正準姿勢、左右差検査(Physical AI/検査)。
"""
import numpy as np

import metrics3d


def reflect_points(points, plane_point, plane_normal):
    """点群を平面(点 plane_point・法線 plane_normal)で鏡映。→ (N,3)。"""
    p = np.asarray(points, float)
    p0 = np.asarray(plane_point, float)
    n = np.asarray(plane_normal, float)
    n = n / (np.linalg.norm(n) + 1e-12)
    d = (p - p0) @ n                                  # 符号付き距離 (N,)
    return p - 2.0 * d[:, None] * n[None, :]


def rotate_points(points, axis_point, axis_dir, angle):
    """点群を軸(点 axis_point・方向 axis_dir)まわり angle[rad] 回転(Rodrigues)。→ (N,3)。"""
    p = np.asarray(points, float)
    a = np.asarray(axis_point, float)
    d = np.asarray(axis_dir, float)
    d = d / (np.linalg.norm(d) + 1e-12)
    v = p - a
    c, s = np.cos(angle), np.sin(angle)
    rot = v * c + np.cross(d, v) * s + np.outer(v @ d, d) * (1 - c)
    return rot + a


def _rms_radius(points):
    p = np.asarray(points, float)
    return float(np.sqrt(np.mean(np.sum((p - p.mean(axis=0)) ** 2, axis=1)))) + 1e-12


def _pca_axes(points):
    """点群の主軸(共分散固有ベクトル、固有値降順)。→ (3,3) 各列が軸。"""
    p = np.asarray(points, float)
    c = p - p.mean(axis=0)
    w, V = np.linalg.eigh(c.T @ c)
    return V[:, ::-1]                                  # 降順


def reflection_symmetry_score(points, plane_point, plane_normal):
    """反射対称スコア = chamfer(鏡映, 元) / RMS半径(小さいほど対称、スケール不変)。→ float。"""
    p = np.asarray(points, float)
    refl = reflect_points(p, plane_point, plane_normal)
    return float(metrics3d.chamfer_distance(refl, p) / _rms_radius(p))


def detect_reflection_symmetry(points):
    """PCA 主軸を法線とする候補平面(重心通過)から最良の反射対称面を選ぶ。

    → dict{plane_point, plane_normal, score, all_scores}。score が小さいほど対称。
    """
    p = np.asarray(points, float)
    if len(p) < 3:
        raise ValueError("反射対称検出は 3 点以上必要")
    c = p.mean(axis=0)
    axes = _pca_axes(p)
    scores = [reflection_symmetry_score(p, c, axes[:, i]) for i in range(3)]
    best = int(np.argmin(scores))
    return {"plane_point": c, "plane_normal": axes[:, best],
            "score": float(scores[best]), "all_scores": [float(s) for s in scores]}


def rotational_symmetry_score(points, axis_point, axis_dir, order):
    """回転対称スコア = chamfer(2π/order 回転, 元) / RMS半径(小さいほど対称)。→ float。"""
    p = np.asarray(points, float)
    rot = rotate_points(p, axis_point, axis_dir, 2 * np.pi / order)
    return float(metrics3d.chamfer_distance(rot, p) / _rms_radius(p))


def detect_rotational_symmetry(points, orders=(2, 3, 4, 6, 8)):
    """PCA 主軸を候補軸として最良の回転対称(軸 × order)を選ぶ。

    → dict{axis_point, axis_dir, order, score, table}。score が小さいほど対称。
    """
    p = np.asarray(points, float)
    if len(p) < 3:
        raise ValueError("回転対称検出は 3 点以上必要")
    c = p.mean(axis=0)
    axes = _pca_axes(p)
    best = None
    table = []
    for i in range(3):
        for o in orders:
            sc = rotational_symmetry_score(p, c, axes[:, i], o)
            table.append((i, int(o), sc))
            if best is None or sc < best[2]:
                best = (i, int(o), sc)
    ai, order, score = best
    return {"axis_point": c, "axis_dir": axes[:, ai], "order": order,
            "score": float(score), "table": table}

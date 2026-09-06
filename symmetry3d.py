# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""symmetry3d — 点群の対称性検出(反射面・回転軸)。metrics3d.chamfer を対称スコアに使う。

対称性は形状補完・姿勢正準化・検査(左右差=欠陥)に効く。反射対称は「点群を候補平面で鏡映して
元と重なるか」、回転対称は「軸まわり 2π/order 回転で重なるか」を **chamfer 距離** で採点する
(小さいほど対称)。候補平面/軸は PCA 主軸(重心を通る)から取る — 多くの対称形状は対称面が主軸に整列する。

スコアは中央値最近傍間隔で正規化してスケール不変(=反射/回転が点間隔の何倍ずれるか)。GT: 楕円体は主軸平面で反射対称(スコア小)、非対称形状は
スコア大、円柱は軸まわり回転対称(任意 order)。metrics3d.chamfer_distance を fitness と同じ土台で流用。

用途: 対称性による形状補完(欠損側を鏡映で埋める)、正準姿勢、左右差検査(Physical AI/検査)。
"""
import numpy as np

import metrics3d


def reflect_points(points, plane_point, plane_normal):
    """点群を平面(点 plane_point・法線 plane_normal)で鏡映。→ (N,3)。

    各点 p の平面からの符号付き距離 ``d = (p - plane_point) · n``(n は正規化した法線)を取り、
    ``p' = p - 2 d n`` を返す(Householder 鏡映)。平面上の点は動かず、平面の両側の点が入れ替わる。
    点の並び順は保たれるので ``p'[i]`` は ``p[i]`` の鏡像。座標の単位はそのまま。

    - ``points``: (N,3) の配列(float に変換)。形状検証はしない。
    - ``plane_point``: 平面上の 1 点 (3,)。``plane_normal``: 法線 (3,)(長さは任意、内部で正規化。
      符号は結果に影響しない)。

    注意: 法線はノルムに 1e-12 を足して割るため、ゼロベクトルを渡しても例外にならず点群がほぼ
    そのまま返る(fail-closed ではない)。``reflection_symmetry_score`` /
    ``detect_reflection_symmetry`` の内部で使うほか、検出した対称面で欠損側を埋める(鏡像を元の
    点群に連結する)形状補完にも使える。
    """
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


def _median_spacing(points):
    """点群の中央値最近傍間隔(スケール相対な対称残差の基準長)。→ float。"""
    from scipy.spatial import cKDTree
    p = np.asarray(points, float)
    d, _ = cKDTree(p).query(p, k=2)
    spacing = float(np.median(d[:, 1]))
    # ゼロ割ガードを座標スケールに相対化する。絶対 epsilon(+1e-12)だと ~1e-9 スケールの
    # 座標では正規化(chamfer/spacing)を歪めてスケール不変性が崩れる(diff ~1e-3)。
    # 特徴長 = 重心からの RMS 半径。実データ(spacing>0)ではフロアは事実上発火せず、
    # 重複点(spacing≈0)のみを相対フロアで持ち上げる。
    scale = float(np.sqrt(np.mean(np.sum((p - p.mean(axis=0)) ** 2, axis=1))))
    if scale == 0.0:                                  # 全点一致=正規化不能: 詐称せず fail-closed
        raise ValueError("degenerate point cloud (all points coincide): symmetry normalization scale is undefined")
    return max(spacing, 1e-12 * scale)


def _pca_axes(points):
    """点群の主軸(共分散固有ベクトル、固有値降順)。→ (3,3) 各列が軸。"""
    p = np.asarray(points, float)
    c = p - p.mean(axis=0)
    w, V = np.linalg.eigh(c.T @ c)
    return V[:, ::-1]                                  # 降順


def reflection_symmetry_score(points, plane_point, plane_normal):
    """反射対称スコア = chamfer(鏡映, 元) / 中央値最近傍間隔(小さいほど対称、スケール不変)。→ float。

    ``reflect_points`` で点群を平面で鏡映し、元の点群との対称 Chamfer 距離(``chamfer_distance``:
    双方向の最近傍距離の平均の平均)を、元の点群の最近傍間隔の中央値で割る。「鏡像が元の点から
    点間隔の何倍ずれているか」という無次元量なので、座標を定数倍しても値は変わらない。

    - ``points``: (N,3) 点群。``plane_point`` / ``plane_normal``: 候補平面(法線は内部で正規化)。
    - fail-closed: 点群が空・(N,3) でない(``chamfer_distance`` が ``ValueError``)、全点が一致して
      間隔が定義できない(``ValueError``)。重複点で中央値間隔が 0 になる場合だけ、重心からの RMS
      半径 × 1e-12 を床にする。

    読み方の注意: 厳密に対称な形でも、鏡像の点が元のサンプル点にぴったり重なるわけではないので
    スコアは 0 にならず、点間隔程度が床になる(実測値は ``detect_reflection_symmetry`` の表を参照)。
    閾値で採否を決めるより、複数候補を掃引して最小値と 2 位との差(``margin``)を見る。PCA の
    3 軸以外の候補面を試したいときは、この関数を平面パラメータで直接掃引する。
    """
    p = np.asarray(points, float)
    refl = reflect_points(p, plane_point, plane_normal)
    return float(metrics3d.chamfer_distance(refl, p) / _median_spacing(p))


def detect_reflection_symmetry(points):
    """PCA 主軸を法線とする候補平面(重心通過)から最良の反射対称面を選ぶ。

    → dict{plane_point, plane_normal, score, all_scores, margin}。
    score が小さいほど対称。

    ★ **``score`` だけで採否を決めない。``margin`` を見ること**(2026-09-06 追加)。
    ``margin`` は 2 位と 1 位の score の差で、**候補が団子なら答えはくじ引き**
    である、という警告になる。実測(1500 点):

    ==================  ========  ========  =========
    形状                best      2 位      margin
    ==================  ========  ========  =========
    箱(鏡映面が 3 枚)     0.9397    0.9499     0.0102
    角柱つきの箱          0.9876    0.9918     0.0043
    球                    1.0490    1.0551     0.0062
    一様乱数の立方体      1.0608    1.3435     0.2828
    ==================  ========  ========  =========

    対称面が複数ある形ほど margin は小さい —— これは不具合ではなく、そういう形
    だという情報である。点群位置合わせの PoC が同じ構造を測っていて、PCA の
    候補は**素の直方体で 83 % が反転した象限を掴む**が、そのとき先に潰れるのは
    残差ではなく候補どうしの margin だった(0.42 → 0.066 → 0.039)。**残差でなく
    margin で採否を見る**、が両方に共通する結論。

    ★ **``score`` は 0 に近づかない。** 厳密に対称な形でも点の間隔が床を作る
    (上の表で箱が 0.94)。「0 に近いか」ではなく「同じ形を鏡映せずに測った値」や
    「点間隔」と比べること。

    ★ **候補は PCA の 3 軸だけ**。真の対称面が主軸のどれとも一致しない形では
    見つからず、しかも黙って 3 つのうち最良を返す。密に振った候補が要るなら
    ``reflection_symmetry_score`` を直接掃引すること。
    """
    p = np.asarray(points, float)
    if len(p) < 3:
        raise ValueError("reflection symmetry detection requires at least 3 points")
    c = p.mean(axis=0)
    axes = _pca_axes(p)
    scores = [reflection_symmetry_score(p, c, axes[:, i]) for i in range(3)]
    best = int(np.argmin(scores))
    ranked = sorted(float(x) for x in scores)
    return {"plane_point": c, "plane_normal": axes[:, best],
            "score": float(scores[best]), "all_scores": [float(s) for s in scores],
            # 2 位との差。小さいほど「どの候補でも同じ」= 選択に意味が無い。
            "margin": float(ranked[1] - ranked[0])}


def rotational_symmetry_score(points, axis_point, axis_dir, order):
    """回転対称スコア = chamfer(2π/order 回転, 元) / 中央値最近傍間隔(小さいほど対称)。→ float。"""
    p = np.asarray(points, float)
    rot = rotate_points(p, axis_point, axis_dir, 2 * np.pi / order)
    return float(metrics3d.chamfer_distance(rot, p) / _median_spacing(p))


def detect_rotational_symmetry(points, orders=(2, 3, 4, 6, 8)):
    """PCA 主軸を候補軸として最良の回転対称(軸 × order)を選ぶ。

    → dict{axis_point, axis_dir, order, score, table, margin}。
    score が小さいほど対称。

    ★ ``margin``(2 位との差)を必ず併読すること。理由は
    :func:`detect_reflection_symmetry` と同じ —— 候補が団子なら選択はくじ引きで、
    そのとき先に潰れるのは score ではなく margin である。回転対称は候補が
    3 軸 x order なので**同じ軸の別 order が 2 位に来る**ことも多く、その場合の
    margin の小ささは「order が決まらない」を意味する(軸は決まっている)。
    ``table`` に全候補が入っているので、軸だけ固定して order を見直せる。

    ★ 候補は PCA の 3 軸だけ。真の対称軸が主軸のどれとも一致しない形では
    見つからず、しかも黙って最良を返す。
    """
    p = np.asarray(points, float)
    if len(p) < 3:
        raise ValueError("rotational symmetry detection requires at least 3 points")
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
    ranked = sorted(float(t[2]) for t in table)
    return {"axis_point": c, "axis_dir": axes[:, ai], "order": order,
            "score": float(score), "table": table,
            # 2 位との差。小さいほど「どの候補でも同じ」= 選択に意味が無い。
            "margin": float(ranked[1] - ranked[0]) if len(ranked) > 1 else 0.0}

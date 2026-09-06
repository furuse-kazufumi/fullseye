# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""curvature3d — 点群の主曲率・平均/ガウス曲率・shape index(局所二次曲面フィット)。

match3d.curvature_maps は voxel 場の曲率だが、ここは**非構造点群**の各点で局所 Monge パッチ
w=f(u,v) を最小二乗フィットし、第一/第二基本形式から主曲率 k1,k2 を出す(再パラメータ化に頑健)。

**符号規約と向きの限界(honest)**: 曲率の符号は法線の向きに依存する。K=k1k2 は法線反転に不変だが、
平均曲率 H・shape index・k1/k2 の符号は向き付き法線が要る。**開いた面(bowl/dome/patch)の凹/凸は
局所情報だけでは原理的に決まらない**(大域的な内外の向きが必要)。そこで:
  - `normals` 引数(視点/range image 由来の**向き付き**法線)を渡すと局所法線をそれに整合させ、
    **正しい凹/凸符号**を出す(凹球=cup → -1、凸球=cap → +1)。
  - `normals` 未指定時は近傍重心から離れる向き(凸側)へ揃えるヒューリスティクス。開面では常に凸側を
    向くため **凹/凸の符号は不定=凸マグニチュードとして報告**(bowl も dome も同符号)。「凹球→-1」は
    向き付き法線を与えたときのみ到達する。

GT: 半径 R の球 → k1=k2=1/R・K=1/R² / 円柱 → k1=1/R,k2=0・K=0 / 平面 → 0。
shape index(Koenderink)= 球(凸)+1・円柱 +0.5・鞍点 0・平面 不定(0 扱い)。凹球は向き付き法線時 -1。

用途: 把持アフォーダンス(凸/凹/鞍点判定)、表面分類、曲率異常による欠陥検出(Physical AI)。
"""
import numpy as np
from scipy.spatial import cKDTree


def _knn_idx(points, k):
    """各点の (自身含む) k+1 近傍インデックス。→ (N, k+1) int。"""
    p = np.asarray(points, float)
    k = min(k, len(p) - 1)
    tree = cKDTree(p)
    _, idx = tree.query(p, k=k + 1)
    return np.atleast_2d(idx)


def _principal_at(local, orient=None):
    """クエリ点を原点にした近傍 (m,3) → 主曲率 (k1>=k2) と法線。

    PCA で法線(最小固有ベクトル)を推定 → 接線基底で Monge 形 w=du+ev+au²+buv+cv² を
    フィット → 第一/第二基本形式の shape operator 固有値で k1,k2。

    `orient`(向き付き参照法線, 3,)を与えると PCA 法線をそれに整合(dot>0)させ、大域的な
    凹/凸の符号を正しく出す。未指定なら近傍重心から離れる向き(凸側)へ揃えるヒューリスティクス
    (開面では常に凸側=符号は凸マグニチュードで不定)。いずれも凸(法線から遠ざかる曲がり)を正。
    """
    if len(local) < 5:
        return 0.0, 0.0, np.array([0.0, 0.0, 1.0])
    C = local.T @ local
    w_eig, V = np.linalg.eigh(C)
    normal = V[:, 0]                 # 最小固有値方向 = 法線
    if orient is not None:
        # 向き付き参照法線(視点/range image 由来の大域向き)へ整合
        if np.dot(normal, orient) < 0:
            normal = -normal
    else:
        centroid = local.mean(axis=0)
        if np.dot(centroid, normal) > 0:  # 近傍の重心から離れる向き(凸側)へ
            normal = -normal
    t1 = V[:, 2] - np.dot(V[:, 2], normal) * normal
    t1 /= np.linalg.norm(t1) + 1e-12
    t2 = np.cross(normal, t1)
    u = local @ t1
    v = local @ t2
    wc = local @ normal
    A = np.stack([u, v, u * u, u * v, v * v], axis=1)
    coef, *_ = np.linalg.lstsq(A, wc, rcond=None)
    d, e, a, b, c = coef
    fx, fy, fxx, fxy, fyy = d, e, 2 * a, b, 2 * c
    denom = np.sqrt(1 + fx * fx + fy * fy)
    I1 = np.array([[1 + fx * fx, fx * fy], [fx * fy, 1 + fy * fy]])
    II = np.array([[fxx, fxy], [fxy, fyy]]) / denom
    S = np.linalg.solve(I1, II)      # shape operator
    ev = np.sort(np.linalg.eigvals(S).real)
    # 外向き法線だと凸面は負固有値 → 符号反転して凸=正、k1>=k2 を維持
    k1, k2 = -ev[0], -ev[1]
    return k1, k2, normal


def _validate_normals(normals, n):
    """向き付き参照法線を検証 → (n,3) float。fail-closed(不正形状/非有限/ゼロ長は ValueError)。"""
    nrm = np.asarray(normals, float)
    if nrm.shape != (n, 3):
        raise ValueError(f"normals must have shape ({n}, 3), got {nrm.shape}")
    if not np.all(np.isfinite(nrm)):
        raise ValueError("normals must be finite")
    if np.any(np.linalg.norm(nrm, axis=1) < 1e-12):
        raise ValueError("normals must be nonzero (each row needs an orientation)")
    return nrm


def _curvatures(points, k, normals=None):
    """全点の (k1, k2, normals)。→ (N,), (N,), (N,3)。

    normals(向き付き参照法線, (N,3))を渡すと各点の局所法線をそれへ整合させ凹/凸符号を正しく出す。
    """
    p = np.asarray(points, float)
    n = len(p)
    if normals is not None:
        normals = _validate_normals(normals, n)
    idx = _knn_idx(p, k)
    K1 = np.zeros(n)
    K2 = np.zeros(n)
    NRM = np.zeros((n, 3))
    for i in range(n):
        local = p[idx[i]] - p[i]     # クエリ点を原点に
        orient = None if normals is None else normals[i]
        K1[i], K2[i], NRM[i] = _principal_at(local, orient)
    return K1, K2, NRM


def principal_curvatures(points, k=25, normals=None):
    """各点の主曲率 (k1>=k2)。→ (k1 (N,), k2 (N,))。

    normals(向き付き参照法線, (N,3))未指定時は凸側マグニチュード(開面の凹/凸符号は不定)。
    向き付き法線を渡すと大域向きに整合し正しい符号(凹=負, 凸=正)。

    手順(各点、Python ループ):
    - ``cKDTree`` で自身を含む k+1 近傍を取る(k は N-1 に切り詰め)。近傍が 5 点未満なら ``k1 = k2 = 0`` を返す(5 係数の二次曲面が組めないため)。
    - 近傍座標をクエリ点原点に平行移動し、``local.T @ local`` の最小固有ベクトルを法線とする(向きは ``normals`` があればそれに整合、無ければ近傍重心から離れる側)。
    - 接線基底 (t1, t2) に射影し ``w = d·u + e·v + a·u² + b·uv + c·v²`` を最小二乗フィット → 第一/第二基本形式から shape operator の固有値を取り、凸を正にして ``k1 >= k2`` に並べる。

    - 単位は 1/長さ(点群の単位に依存)。半径 R の球なら ``k1 = k2 = 1/R``、円柱は ``(1/R, 0)``、平面は 0。
    - ``k`` は近傍点数(既定 25)。大きいほど平滑で曲率は低め、小さいほどノイズを拾う。
    - ``normals`` は (N,3) で有限かつ非ゼロ行が必須(``ValueError``)。決定論的。
    - 後段: ``mean_curvature`` / ``gaussian_curvature`` / ``shape_index``(いずれも内部で同じ計算を繰り返す)。shape index と曲がりの対が要るなら 2 本を ``(N,2)`` に並べて ``curvature_to_shape_index``。
    """
    K1, K2, _ = _curvatures(points, k, normals)
    return K1, K2


def mean_curvature(points, k=25, normals=None):
    """平均曲率 H=(k1+k2)/2。→ (N,)。向きに依存する量。

    normals(向き付き参照法線, (N,3))未指定時は凸側ヒューリスティクス(開面の凹/凸符号は不定)。
    向き付き法線を渡すと大域向きに整合し正しい符号を出す。

    補足:
    - 計算は ``principal_curvatures`` と同じ(k+1 近傍の PCA 法線 + 局所二次曲面フィット)で、``(k1 + k2) / 2`` を返す。単位は 1/長さ。
    - 符号は凸を正とする規約で、``normals`` を渡したときだけ大域的な凹/凸に対応する。未指定では開いた面の H は常に凸側(絶対値相当)。
    - 近傍が 5 点未満の点は 0。``k`` は N-1 に切り詰められる。
    - 半径 R の球なら ``1/R``、円柱は ``1/(2R)``、平面は 0。鞍点(k1 = -k2)も 0 だが ``gaussian_curvature`` は負になるので区別できる。
    - ``normals`` は (N,3) で有限かつ非ゼロ行(``ValueError``)。決定論的。
    """
    K1, K2, _ = _curvatures(points, k, normals)
    return (K1 + K2) / 2.0


def gaussian_curvature(points, k=25):
    """ガウス曲率 K=k1·k2(法線の反転に不変)。→ (N,)。

    補足:
    - ``principal_curvatures`` と同じ局所二次曲面フィットで ``k1 * k2`` を返す。符号は法線の向きに依らないため ``normals`` 引数を持たない(向き付けは常に近傍重心ヒューリスティクス)。
    - 単位は 1/長さ²。半径 R の球なら ``1/R²``、円柱・平面は 0、鞍点は負(k1 と k2 が異符号)。
    - ``k`` は近傍点数(既定 25、N-1 に切り詰め)。近傍が 5 点未満の点は 0。
    - 楕円点(K>0)/放物点(K=0)/双曲点(K<0)の分類に使う。凸凹の区別は ``mean_curvature`` か ``shape_index`` に ``normals`` を渡して行う。
    - 入力は (N,3) の点群。決定論的。
    """
    K1, K2, _ = _curvatures(points, k)
    return K1 * K2


def shape_index(points, k=25, normals=None):
    """Koenderink の shape index s∈[-1,1] (凸球+1・円柱+0.5・鞍点0・凹球-1)。→ (N,)。

    umbilic/平面判定は**曲率スケール相対**(絶対しきい値なし)。緩やかな凸/凹(曲率が微小でも)は
    符号=凹凸を保ち、平面はデータ全体の曲率スケールに対して相対的に 0 の点のみ s=0 とする。

    normals(向き付き参照法線, (N,3))未指定時は開面の凹/凸符号が不定(凸マグニチュードで報告)。
    向き付き法線を渡すと大域向きに整合し正しい符号(凹球=cup → -1)を出す。

    計算(各点、``principal_curvatures`` と同じフィット):
    - 平面判定: curvedness ``sqrt((k1² + k2²) / 2)`` が、全点の curvedness の中央値 × 1e-3 未満なら s = 0。中央値が 0(曲率信号なし)なら全点 0。
    - 臍点判定: ``|k1 - k2| < 1e-2 × (|k1| + |k2|)`` なら s = ``sign(k1 + k2)``(厳密に ±1)。
    - それ以外: ``s = (2/π) · arctan((k1 + k2) / (k1 - k2))``。

    - しきい値は絶対値でなく **データ全体の曲率スケール相対** なので、同じ形でも他の点との混在具合で平面扱いになる点が変わる。単一の点群を分類する前提で使う。
    - 近傍が 5 点未満の点は k1 = k2 = 0 → 平面(0)。``k`` は N-1 に切り詰め。
    - ``normals`` は (N,3) で有限かつ非ゼロ行(``ValueError``)。未指定では開いた面の符号は不定(凸側)。
    - 曲がりの強さは含まない。強さも要るなら ``principal_curvatures`` の 2 本を ``(N,2)`` に並べて ``curvature_to_shape_index`` に通す。
    """
    K1, K2, _ = _curvatures(points, k, normals)
    ssum = K1 + K2
    diff = K1 - K2                        # k1>=k2 なので diff>=0
    mag = np.abs(K1) + np.abs(K2)         # 局所曲率の大きさ
    curv = np.sqrt((K1 ** 2 + K2 ** 2) / 2.0)  # curvedness(各点)
    scale = float(np.median(curv))        # データ全体の曲率スケール(robust)

    rel_umbilic = 1e-2                    # |k1-k2| がこの割合未満 → 臍点扱い(符号のみ)
    rel_flat = 1e-3                       # curvedness がスケールのこの割合未満 → 平面(s=0)

    s = np.zeros_like(K1)
    # 平面: データ曲率スケールに対して相対的に 0 の点のみ(scale>0 が前提。信号ゼロなら全面平面)
    if scale > 0.0:
        flat_plane = curv < rel_flat * scale
    else:
        flat_plane = np.ones_like(K1, dtype=bool)  # 曲率信号なし → 不定(平面=0)

    # 臍点(k1≈k2): |k1-k2| が曲率の大きさに対して相対的に小 → 符号 sign(k1+k2) で凹凸を保つ
    umbilic = (diff < rel_umbilic * mag) & (mag > 0.0)

    umb = umbilic & ~flat_plane          # 臍点かつ非平面 → 符号(緩くても凹凸を保存)
    s[umb] = np.sign(ssum[umb])
    general = ~umbilic & ~flat_plane     # 一般(異方性)→ Koenderink arctan
    s[general] = (2.0 / np.pi) * np.arctan(ssum[general] / diff[general])
    return s


def curvedness(points, k=25):
    """curvedness C=√((k1²+k2²)/2)(曲がりの強さ、shape index と直交な量)。→ (N,)。"""
    K1, K2, _ = _curvatures(points, k)
    return np.sqrt((K1 ** 2 + K2 ** 2) / 2.0)


def estimate_normals(points, k=25):
    """外向き(近傍重心から離れる)に統一した点群法線。→ (N,3)。

    手順(各点、Python ループ): ``cKDTree`` で自身を含む k+1 近傍(k は N-1 に切り詰め)を取り、クエリ点を原点にした近傍座標の散布行列 ``local.T @ local`` の最小固有ベクトルを法線にする(単位長)。向きは「近傍重心との内積が正なら反転」= 近傍重心から離れる側に揃える。

    - 近傍が 5 点未満の点は固定値 ``(0, 0, 1)`` を返す(推定していない)。
    - 向き付けは局所ヒューリスティクスで、閉じた凸形状なら外向きだが、開いた面・薄板・凹部では隣接点どうしで向きが食い違い得る(大域一貫性は保証しない)。大域的に揃えるには ``orient_normals`` に通すか、最初から ``estimate_oriented_normals`` を使う。organized 深度画像なら ``normals_from_depth`` が視点向きで速い。
    - 返り値は float64 (N,3)。``k`` 既定 25。決定論的。
    - 内部は ``principal_curvatures`` と同じ計算を通る(法線推定にも二次曲面フィットまで走る)ので、点数が多いと遅い。
    """
    _, _, NRM = _curvatures(points, k)
    return NRM

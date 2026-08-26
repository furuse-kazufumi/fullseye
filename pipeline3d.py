"""pipeline3d — Physical AI 視覚の合成パイプライン(高優先 op×op を 1 本の実用 op に)。

docs/OP_COMBINATION_MATRIX.md の高優先(実現性×差別化)組み合わせを、そのまま呼べる合成 op に
実体化する。個々の op(match3d / feat_* / fuse3d)を連結し、Physical AI の実タスク
(点群登録・CAD 整合・平面度/真球度計測・SDF 照合)を 1 コールで提供する。

`register_auto` は **データを見て手法を自動選択**する = 進化アルゴリズムが fitness で自動的に
手法を選ぶのと同じ発想の、決定論的(ルールベース)な前身。ops3d レジストリ + この選択層が、
将来の「3D パイプラインの自動探索/進化」の土台になる。
"""
import numpy as np

import match3d as X
import feat_fpfh
import fuse3d


def _np(x):
    return x.detach().cpu().numpy() if hasattr(x, "detach") else np.asarray(x)


def register_pointclouds(src, dst, refine=True, trim=0.7):
    """点群大域登録(初期推定なし): FPFH+RANSAC → ICP 精緻化。→ (R, t, rmse)。

    OP_COMBINATION #2。大回転+部分重なりを init なしで解き、ICP で機械精度へ締める。
    """
    out = feat_fpfh.register_fpfh(src, dst)
    R, t = _np(out[0]), _np(out[1])
    if refine:
        R2, t2, info = X.icp_point2point_3d(src, dst, iters=40, init_R=R, init_t=t,
                                            trim_ratio=trim)
        return _np(R2), _np(t2), info.get("rmse")
    return R, t, None


def align_cad_to_scan(vertices, faces, scan, samples=8000):
    """CAD mesh を点群スキャンへ整合(Physical AI 典型の CAD-to-scan)。→ (R, t)。OP_COMBINATION #1。"""
    return fuse3d.register_cross((vertices, faces), "mesh", scan, "points",
                                 method="fpfh", samples=samples)


def measure_plane(points):
    """点群 → 支配平面(法線,通過点)+ 平面度(残差 RMS / PV)。検出+計測の合成。OP_COMBINATION #4。"""
    c, n, _ = X.fit_plane_3d(points)
    d = np.array([X.distance_point_plane(p, c, n) for p in np.asarray(points)])
    return {"normal": n, "point": c,
            "flatness_rms": float(np.sqrt(np.mean(d ** 2))),
            "pv": float(d.max() - d.min())}


def inspect_roundness(points):
    """点群 → 球フィット + 真球度(半径残差 PV / RMS)。球状部品計測。OP_COMBINATION #15。"""
    c, r = X.fit_sphere_3d(points)
    dr = np.linalg.norm(np.asarray(points) - c, axis=1) - r
    return {"center": c, "radius": r,
            "roundness_pv": float(dr.max() - dr.min()),
            "rms": float(np.sqrt(np.mean(dr ** 2)))}


def match_sdf(scene, template, device="cpu", mc=0.3):
    """SDF ベース照合: 両者を符号付き距離場へ変換 → 勾配方向照合(滑らか・遮蔽頑健)。

    → [score, d, h, w]。OP_COMBINATION #3(signed_distance_field → match_shape_3d)。
    """
    ssdf = X.signed_distance_field(scene, device)
    tsdf = X.signed_distance_field(template, device)
    return X.match_shape_3d(ssdf, tsdf, device, mc=mc)


def register_auto(src, dst):
    """データを見て登録法を**自動選択**(進化=fitness 自動選択の決定論的前身)。→ (method, R, t)。

    重なり(最近傍距離の中央値 / 物体スケール)が小 = 既に近い → ICP、大 = 遠い/大回転 → FPFH+ICP。
    ops3d の型連結 + このヒューリスティック選択が、将来の自動パイプライン探索の土台。
    """
    from scipy.spatial import cKDTree
    src = np.asarray(src, float); dst = np.asarray(dst, float)
    d = cKDTree(dst).query(src, k=1)[0]
    scale = np.linalg.norm(src.max(0) - src.min(0))
    if np.median(d) < 0.05 * scale:
        R, t, _ = X.icp_point2point_3d(src, dst, iters=40)
        return "icp", _np(R), _np(t)
    R, t, _ = register_pointclouds(src, dst)
    return "fpfh+icp", R, t

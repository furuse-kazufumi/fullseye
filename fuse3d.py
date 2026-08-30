"""異種構造の統合(TRIZ 統合/複合)= 全5構造を組み合わせる。

マトリクスの「行」(データ構造)を掛け合わせる層: どの構造も共通表現(点群 / voxel)へ**変換**して
寄せれば、**異種構造間の相互マッチ**(例: CAD mesh vs LiDAR 点群スキャン = Physical AI 典型課題)や
**多構造フュージョン**(mesh + points + depth → 1 つの密度 voxel)ができる。変換グラフ(match3d)が土台。
"""
import numpy as np

import match3d as X
import feat_fpfh


def to_points(data, kind, samples=20000, **kw):
    """任意の 3D 構造 → 点群(共通表現)。全5構造を 1 本の入口へ統合。

    kind: "points"(N,3)/ "mesh"=(vertices,faces)/ "depth"=depth+{fx,fy,cx,cy[,stride]}/
          "voxel"=密度 grid+{iso}/ "3dgs"=means(N,3)。
    """
    if kind == "points":
        return np.asarray(data, float)
    if kind == "mesh":
        return X.mesh_to_points(data[0], data[1], samples)
    if kind == "depth":
        return X.depth_to_points(data, kw["fx"], kw["fy"], kw["cx"], kw["cy"], kw.get("stride", 1))
    if kind == "voxel":
        return np.argwhere(np.asarray(data) > kw.get("iso", 0.5)).astype(float)
    if kind == "3dgs":
        return np.asarray(data, float)
    raise ValueError(f"unknown structure kind: {kind}")


def _np(x):
    return x.detach().cpu().numpy() if hasattr(x, "detach") else np.asarray(x)


def register_cross(src, src_kind, dst, dst_kind, method="fpfh", samples=15000, **kw):
    """異種構造間の剛体登録。両者を点群へ変換 → 登録器(fpfh=大回転/icp=要 coarse init)。

    例: register_cross((verts,faces),"mesh", scan_pts,"points") で CAD↔スキャン整合。返り値 (R, t)。
    """
    ps = to_points(src, src_kind, samples, **kw)
    pd = to_points(dst, dst_kind, samples, **kw)
    if method == "fpfh":
        out = feat_fpfh.register_fpfh(ps, pd)
        return _np(out[0]), _np(out[1])
    if method == "icp":
        R, t, _ = X.icp_point2point_3d(ps, pd, iters=50)
        return _np(R), _np(t)
    raise ValueError(f"unknown registration method: {method}")


def fuse_to_voxel(items, size=64, bounds=None, device="cpu", smooth=0.8):
    """複数構造を共通密度 voxel へ融合(TRIZ 統合)。items=[(data,kind,params_dict), ...]。

    mesh(topology)+ points(sample)+ depth(観測)等の相補的な構造を 1 表現に。返り値 (voxel, bounds)。
    """
    allpts = [to_points(d, k, **p) for d, k, p in items]
    P = np.vstack(allpts)
    if bounds is None:
        bounds = (P.min(0), P.max(0))
    return X.points_to_voxel(P, size, bounds, device, smooth=smooth), bounds

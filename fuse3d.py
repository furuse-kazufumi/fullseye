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

    ``kind`` ごとの変換(実装どおり):
    - ``"points"`` / ``"3dgs"``: ``np.asarray(data, float)`` を返すだけ(形の検査は
      しない。``(N, 3)`` を渡すのは呼び手の責任)。
    - ``"mesh"``: ``data = (vertices, faces)``。``match3d.mesh_to_points`` で面積重みの
      一様サンプリングを ``samples`` 点(既定 20000、seed 固定 = 決定的)。
    - ``"depth"``: ``data`` は深度マップ ``(H, W)``、``kw`` に ``fx, fy, cx, cy`` が
      **必須**(無ければ ``KeyError``)、``stride`` は任意(既定 1、間引き)。
      ``match3d.depth_to_points`` のピンホール逆投影で、``depth > 0`` の画素だけを
      ``(x, y, z)`` 点にする(カメラ座標、x = 列方向、y = 行方向、z = 深度)。
    - ``"voxel"``: 密度 grid ``(D, H, W)`` を ``kw["iso"]``(既定 0.5)で閾値し、
      ``np.argwhere`` の **整数 index 座標** ``(z, y, x)`` を float にした点群。
      物理座標には直さない(spacing は掛けない)。

    返り値: ``(N, 3)`` float64。``kind`` が上記以外なら ``ValueError``。
    ``samples`` は ``"mesh"`` 以外では無視される。

    注意: ``"voxel"`` の座標は配列 index 順 ``(z, y, x)``、``"depth"`` はカメラ座標
    ``(x, y, z)`` と、種別ごとに軸の意味が違う。異種を ``register_cross`` /
    ``fuse_to_voxel`` で混ぜるときは、この差を呼び手が揃えておくこと。
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

    手順: ``to_points(src, src_kind, samples, **kw)`` と ``to_points(dst, dst_kind,
    samples, **kw)`` で両者を点群にし、``method`` で登録器を選ぶ。
    - ``"fpfh"``(既定): ``feat_fpfh.register_fpfh(ps, pd)`` を既定パラメータで呼ぶ
      (FPFH 記述子 + RANSAC、初期姿勢不要、大回転・部分重なりに対応)。
    - ``"icp"``: ``match3d.icp_point2point_3d(ps, pd, iters=50)``(最近傍対応 +
      Kabsch)。初期姿勢の引数は渡さないので、``src`` が ``dst`` に近い(粗く
      合っている)ことが前提。
    - それ以外は ``ValueError``。

    返り値: ``(R, t)`` — ``R`` は ``(3, 3)``、``t`` は ``(3,)`` の numpy 配列(torch tensor
    は CPU の numpy に変換して返す)。慣習は ``dst ≈ src @ R.T + t``。

    注意:
    - ``**kw`` は **両方の** ``to_points`` に同じものが渡る(``"depth"`` の ``fx, fy, cx,
      cy`` や ``"voxel"`` の ``iso`` を片側だけに与えることはできない)。
    - ``samples`` は ``"mesh"`` のサンプル数(既定 15000)。点群の個数・形は検査しない。
    - 座標系の違い(``to_points`` 参照: voxel は ``(z, y, x)`` index、depth はカメラ
      ``(x, y, z)``)は吸収しない。
    - 精度を締めるには fpfh の結果を初期値に ``icp_point2point_3d`` を直接呼ぶ。
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
    # fail-closed: items は [(data, kind, params), ...]。生データを渡す誤用は
    # 素の TypeError で深部から落ちる(連鎖ファザー実測)ので入口で明示拒否
    if not isinstance(items, (list, tuple)) or not items or not all(
            isinstance(it, (list, tuple)) and len(it) == 3
            and isinstance(it[2], dict) for it in items):
        raise ValueError("items must be a non-empty list of (data, kind, "
                         "params_dict) triples — e.g. [((V, F), 'mesh', {}), "
                         "(pts, 'points', {})], got %r" % (type(items).__name__,))
    allpts = [to_points(d, k, **p) for d, k, p in items]
    P = np.vstack(allpts)
    if bounds is None:
        bounds = (P.min(0), P.max(0))
    return X.points_to_voxel(P, size, bounds, device, smooth=smooth), bounds

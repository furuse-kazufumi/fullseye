"""SuGaR 風メッシュ抽出 ―― 表面整列した 3DGS からメッシュを取り出す。

  1. flatten 正則つきで 3DGS 学習(各ガウシアンを扁平な円盤=面に整列)
  2. 各ガウシアンの薄軸(最小スケール軸)を surface normal とし、法線つき点群を作る
  3. Open3D Poisson でメッシュ再構成 → 低密度をトリム → bbox でクロップ
  4. mesh.ply 書き出し + プレビュー画像 + sim 真値メッシュとの bbox 比較(honest 検証)

sim ネイティブなので真値メッシュ(scene_geometries)と付き合わせて品質を確認できる。
実行は fullseye_3dgs.setup_cuda_env() 後(native gsplat)。
"""
from __future__ import annotations
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_SH_C0 = 0.28209479177387814


def _quats_to_R(q):
    q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-9)
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    R = np.empty((len(q), 3, 3), np.float32)
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - w * z); R[:, 0, 2] = 2 * (x * z + w * y)
    R[:, 1, 0] = 2 * (x * y + w * z); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - w * x)
    R[:, 2, 0] = 2 * (x * z - w * y); R[:, 2, 1] = 2 * (y * z + w * x); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def gaussians_to_mesh(g, *, opacity_thresh=0.25, poisson_depth=8, density_pct=6,
                      knn=30, sor_std=0.0, pca=True, boundary_frac=0.08, log=print):
    """学習済みガウシアン dict -> Open3D TriangleMesh(法線つき点群 + Poisson)。

    法線: 薄軸(最小スケール軸)を「向きの参照」としてだけ使い、実際の法線は局所近傍
    PCA で再推定する。円盤ごとに独立してばらつく薄軸をそのまま Poisson に渡すと表面が
    スパイク状になるため、幾何的に滑らかな PCA 法線へ置換し符号だけ薄軸に合わせる。
    """
    import open3d as o3d
    import torch
    means = g["means"].cpu().numpy().astype(np.float64)
    scales = torch.exp(g["scales"]).cpu().numpy()
    quats = g["quats"].cpu().numpy()
    opac = torch.sigmoid(g["opacities"]).cpu().numpy()
    dc = g["sh0"].reshape(-1, 3).cpu().numpy()
    rgb = np.clip(_SH_C0 * dc + 0.5, 0, 1)
    keep = opac > opacity_thresh
    means, scales, quats, rgb = means[keep], scales[keep], quats[keep], rgb[keep]
    R = _quats_to_R(quats)
    kmin = np.argmin(scales, axis=1)                       # 薄軸 = 向きの参照のみ
    ref = R[np.arange(len(R)), :, kmin].astype(np.float64)
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(means)
    pcd.colors = o3d.utility.Vector3dVector(rgb.astype(np.float64))
    # floater(疎な外れ点)は Poisson で長いスパイクの芯になるため先に統計的に除去
    if sor_std and len(means) > knn:
        pcd, keep_idx = pcd.remove_statistical_outlier(nb_neighbors=knn, std_ratio=sor_std)
        ref = ref[np.asarray(keep_idx)]
    if pca:
        # 局所近傍 PCA で滑らかな幾何法線を再推定
        pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamKNN(knn=knn))
        est = np.asarray(pcd.normals)
        flip = np.sum(est * ref, axis=1) < 0               # 符号を薄軸参照に合わせる
        est[flip] *= -1.0
        pcd.normals = o3d.utility.Vector3dVector(est)
    else:
        pcd.normals = o3d.utility.Vector3dVector(ref)       # 旧法: 薄軸そのまま
    pcd.orient_normals_consistent_tangent_plane(knn)       # 法線の向きを大域整合
    log(f"Poisson 再構成 (点 {len(pcd.points)}, depth {poisson_depth}, "
        f"{'PCA' if pca else '薄軸'}法線 knn={knn}) …")
    mesh, dens = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=poisson_depth, linear_fit=True)
    dens = np.asarray(dens)
    # 低密度トリム(=外挿/スパイクの芯を除去)。ただし XY 境界リングは保護し、
    # トリムで地形の footprint が縮むのを防ぐ(TRIZ 原理3 局所的性質=空間分離)。
    low = dens < np.quantile(dens, density_pct / 100.0)
    if boundary_frac > 0 and mesh.has_vertices():
        xy = np.asarray(mesh.vertices)[:, :2]
        lo, hi = xy.min(0), xy.max(0)
        margin = float((hi - lo).min()) * boundary_frac
        d_edge = np.minimum(xy - lo, hi - xy).min(axis=1)   # 最寄り XY 縁までの距離
        low &= d_edge >= margin                              # 境界リングは削らない
    mesh.remove_vertices_by_mask(low)
    mesh = mesh.crop(pcd.get_axis_aligned_bounding_box())  # 元の範囲へ
    # 後処理: 退化/重複除去 → 小クラスタ(floater)除去 → Taubin スムージング
    mesh.remove_degenerate_triangles(); mesh.remove_duplicated_vertices()
    mesh.remove_duplicated_triangles(); mesh.remove_non_manifold_edges()
    try:
        idx, counts, _ = mesh.cluster_connected_triangles()
        idx = np.asarray(idx); counts = np.asarray(counts)
        if len(counts):
            big = counts.max()
            small = np.where(counts < max(50, big * 0.02))[0]     # 総面の 2% 未満は除去
            mesh.remove_triangles_by_mask(np.isin(idx, small))
            mesh.remove_unreferenced_vertices()
    except Exception:
        pass
    mesh = mesh.filter_smooth_taubin(number_of_iterations=6)       # スパイク低減
    mesh.compute_vertex_normals()
    return mesh, pcd


def _gt_mesh_bbox(scene_xml):
    """sim 真値メッシュ(全 geom)の合成 bbox(honest 検証用)。"""
    import sim_source as S
    s = S.MuJoCo(scene_xml)
    try:
        geoms = s.scene_geometries()
    finally:
        s.close()
    if not geoms:
        return None
    import numpy as _np
    mins, maxs = [], []
    for g in geoms:
        v = _np.asarray(g.vertices)
        if len(v):
            mins.append(v.min(0)); maxs.append(v.max(0))
    if not mins:
        return None
    return _np.min(mins, 0), _np.max(maxs, 0)


def _preview(mesh, path, n=4):
    """メッシュを数アングルから描画して montage 保存(matplotlib, headless 可)。
    頂点色があればそれで着色(地形の実際の見た目)、無ければグレーでシェーディング。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    v = np.asarray(mesh.vertices); f = np.asarray(mesh.triangles)
    if len(v) == 0 or len(f) == 0:
        return None
    vc = np.asarray(mesh.vertex_colors) if mesh.has_vertex_colors() else None
    facecolors = None
    if vc is not None and len(vc) == len(v):
        fc = vc[f].mean(axis=1)                       # 面 = 3 頂点色の平均
        # 簡易ランバート陰影(法線 z 成分)で立体感を付ける
        tv = v[f]
        nrm = np.cross(tv[:, 1] - tv[:, 0], tv[:, 2] - tv[:, 0])
        nl = np.linalg.norm(nrm, axis=1, keepdims=True)
        nz = np.abs(nrm[:, 2:3] / np.clip(nl, 1e-9, None))
        shade = 0.55 + 0.45 * nz                      # 0.55..1.0
        facecolors = np.clip(fc * shade, 0, 1)
    fig = plt.figure(figsize=(4 * n, 4))
    for i in range(n):
        ax = fig.add_subplot(1, n, i + 1, projection="3d")
        if facecolors is not None:
            tri = Poly3DCollection(v[f], facecolors=facecolors, edgecolor="none", linewidths=0)
            ax.add_collection3d(tri)
            ax.set_xlim(v[:, 0].min(), v[:, 0].max()); ax.set_ylim(v[:, 1].min(), v[:, 1].max())
            ax.set_zlim(v[:, 2].min(), v[:, 2].max())
        else:
            ax.plot_trisurf(v[:, 0], v[:, 1], f, v[:, 2], color=(0.7, 0.72, 0.78),
                            edgecolor="none", linewidth=0, antialiased=True, shade=True)
        ax.view_init(elev=18, azim=90 * i)
        ax.set_axis_off()
        try:
            ax.set_box_aspect((1, 1, 1))
        except Exception:
            pass
    fig.tight_layout(); fig.savefig(path, dpi=90, facecolor="#0f1117"); plt.close(fig)
    return path


def extract_mesh(scene, out_dir, *, n_views=36, iters=1500, res=256, radius=1.3,
                 elevation_deg=22.0, lookat=(0, 0, 0.18), n_gauss_init=8000,
                 flatten=0.02, depth_weight=0.15, poisson_depth=8, log=print):
    """シーンを SuGaR 風にメッシュ化。戻り値: {mesh_ply, vertices, faces, gt_bbox, ...}。

    depth_weight>0 で sim 真値深度を幾何監督に使い(sim ネイティブのタダ情報)、
    ガウシアンを表面に固定 → footprint/形状精度を上げる(実測 bbox 差 0.19→0.08m)。"""
    import gsplat_train_native as N
    os.makedirs(out_dir, exist_ok=True)
    r = N.train_densify(scene, out_dir, n_views=n_views, iters=iters, res=res, radius=radius,
                        elevation_deg=elevation_deg, lookat=lookat, n_gauss_init=n_gauss_init,
                        flatten=flatten, depth_weight=depth_weight, return_gaussians=True, log=log)
    mesh, pcd = gaussians_to_mesh(r["gaussians"], poisson_depth=poisson_depth, log=log)
    import open3d as o3d
    ply = os.path.join(out_dir, "mesh.ply")
    o3d.io.write_triangle_mesh(ply, mesh)
    prev = _preview(mesh, os.path.join(out_dir, "mesh_preview.png"))
    nv, nf = len(mesh.vertices), len(mesh.triangles)
    # honest 検証: 真値メッシュ bbox と比較
    gt = _gt_mesh_bbox(scene)
    if gt is not None and nv:
        v = np.asarray(mesh.vertices)
        ext_got = v.max(0) - v.min(0); ext_gt = gt[1] - gt[0]
        err = float(np.abs(ext_got - ext_gt).max())
        log(f"mesh: {nv} 頂点 / {nf} 面 | bbox 抽出 {np.round(ext_got,2)} vs 真値 {np.round(ext_gt,2)} "
            f"(最大差 {err:.3f}m)")
    else:
        log(f"mesh: {nv} 頂点 / {nf} 面")
    return {"mesh_ply": ply, "preview": prev, "vertices": nv, "faces": nf,
            "test_psnr": r.get("test_psnr")}


if __name__ == "__main__":
    import fullseye_3dgs as F
    F.setup_cuda_env()
    sc = sys.argv[1] if len(sys.argv) > 1 else "demo"
    import scene_registry as R
    spec = R.resolve(sc)
    out = sys.argv[2] if len(sys.argv) > 2 else "sugar_out"
    extract_mesh(spec["xml"], out, lookat=spec["lookat"], radius=spec["radius"],
                 elevation_deg=spec["elevation_deg"], log=lambda m: print(m, flush=True))

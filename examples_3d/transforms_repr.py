# -*- coding: utf-8 -*-
"""事例: 3-D データ表現の相互変換ハブ(点群↔ボクセル↔メッシュ↔SDF↔深度↔TSDF)(representation).

平たく言うと: 同じ 1 個の物体でも、扱う工程ごとに姿を変える —— カメラは「深度画像」で、
CAD は「メッシュ」で、スキャナは「点群」で、衝突判定は「符号付き距離場(SDF)」で、GPU 処理は
「ボクセル」で表す。3-D パイプラインの土台は **どの表現からどの表現へも壊れずに移れること**。
ここでは半径・中心が既知の球(と、登録用に非対称な段付きブロック)を素材に、変換 op 群を
1 本の鎖に繋いで「表現を変えても物体の幾何が保たれる」ことを解析真値で確かめる。

  depth ──depth_to_points──▶ points(球面上に載る)
  mesh / 3dgs ──{mesh_to_voxel, gaussians_to_voxel}──▶ voxel(同じ殻に重なる=IoU)
  voxel ──voxel_to_mips──▶ 直交 3 面 MIP(球なので 3 枚が合同)
  occupancy ──signed_distance_field──▶ SDF ──sdf_to_occupancy──▶ occupancy(往復で復元)
  depth ──tsdf_from_depth──▶ 単フレーム TSDF(ゼロ等値面が可視表面に載る)
  {mesh,points,3dgs} ──fuse_to_voxel──▶ 融合ボクセル / to_points で全構造を点群へ統一
  mesh(CAD)──register_cross──▶ points(スキャン)へ剛体整合
  depth 列 ──integrate──▶ 多フレーム TSDF ──表面点(真球に載る)

検証(GT): 球の中心 C・半径 R は生成時に既知。各変換の出力を「C からの距離 ≈ R」等の
解析真値と数値照合する(見た目でなく assert):
    - depth_to_points  : 復元点が球面に厳密に載る(median|d-R| ≈ 0)
    - mesh_to_voxel / gaussians_to_voxel : 密度殻が球面近傍、両者の occupancy が高 IoU で一致
    - voxel_to_mips    : 直交 3 MIP の面積が互いに合同(球対称)かつ ≈ πR²
    - signed_distance_field : 出力 SDF が解析符号距離 (dist-R) と corr>0.99・RMS<0.6 voxel
    - sdf_to_occupancy : occ→SDF→occ の往復が元 occupancy を IoU≈1 で復元
    - tsdf_from_depth  : TSDF のゼロ交差帯が可視球面(C から距離 R)に載る
    - to_points        : depth 経路が depth_to_points と一致、mesh 経路が球面に載る
    - fuse_to_voxel    : 複数構造の融合殻が球面近傍(< 1 voxel)
    - register_cross   : CAD メッシュ→スキャン点群を剛体整合、回転<3°・整列RMSE<スケール3%
    - integrate        : 多フレーム TSDF の抽出表面が真球に載る(median|r-R| < voxel)

beat-the-null: どの GT も「わざと外した」対照を判別的に上回ることを assert する —— 誤った中心へ
測った距離、数 voxel ずらした occupancy との IoU、変換前(恒等姿勢)の整列 RMSE、非球なら崩れる
MIP 面積の対称性。変換が偶然でなく本当に同じ幾何を運んでいることの裏取り。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
import match3d as X          # depth/mesh/gaussians/voxel/sdf 変換 + tsdf_from_depth
import fuse3d                # to_points / register_cross / fuse_to_voxel(構造統合)
import tsdf_fusion           # new_volume / integrate / extract_surface_points(多フレーム TSDF)
import visualhull            # look_at(eye, target, up) -> (R, t)  規約: X_cam = R X + t
from scipy.spatial import cKDTree

# ═══════════════════════════════════════════════════════════════════════════
# 素材: 半径 R・中心 C の球(表現変換の共通の被写体)。ワールド座標。
# ═══════════════════════════════════════════════════════════════════════════
rng = np.random.default_rng(0)
center = np.array([0.2, -0.1, 0.15])          # 原点から少しずらす(判別性)
R = 1.0                                        # 既知半径(全 GT の基準)

# 共通のワールド voxel 格子(全 voxel 変換を同一格子に載せて比較可能に)
m = 1.35 * R
lo = center - m
bounds = (center - m, center + m)              # (min3, max3)
size = 48
span = 2.0 * m
vox = span / (size - 1)                         # voxel 一辺(ワールド長)
r_vox = R / vox                                 # 球半径(voxel 単位)


def sphere_mesh(c, radius, nu=40, nv=20):
    """UV 球メッシュ(頂点+三角面)。mesh 系変換の入力。"""
    us = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    vs = np.linspace(0, np.pi, nv)
    V = [[np.sin(v) * np.cos(u), np.sin(v) * np.sin(u), np.cos(v)] for v in vs for u in us]
    V = np.asarray(c, float) + radius * np.asarray(V)
    F = []
    for j in range(nv - 1):
        for i in range(nu):
            a, b = j * nu + i, j * nu + (i + 1) % nu
            cc, dd = (j + 1) * nu + i, (j + 1) * nu + (i + 1) % nu
            F.append([a, b, cc]); F.append([b, dd, cc])
    return V, np.asarray(F, int)


def sphere_points(c, radius, n, gen):
    """球面上の一様点(法線方向を正規化してスケール)。"""
    u = gen.normal(size=(n, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    return np.asarray(c, float) + radius * u


def voxel_index_to_world(ijk):
    """voxel index (i,j,k) → ワールド座標。points_to_voxel の floor 割当(左端)に一致。"""
    return lo + np.asarray(ijk, float) / (size - 1) * span


V, Fc = sphere_mesh(center, R)
means = sphere_points(center, R, 3000, rng)     # 3DGS の中心(球面上)
scales = np.full((means.shape[0], 3), 0.03)     # 等方・小スケール
opac = np.ones(means.shape[0])                  # 不透明度 1

# ═══════════════════════════════════════════════════════════════════════════
# 1) depth_to_points: 解析深度(球)をピンホール逆投影 → カメラ座標の球面点
# ═══════════════════════════════════════════════════════════════════════════
H = Wd = 120
focal = 150.0
cxp, cyp = (Wd - 1) / 2.0, (H - 1) / 2.0
K = np.array([[focal, 0, cxp], [0, focal, cyp], [0, 0, 1.0]])


def render_sphere_depth(c, radius, Rm, t, K, H, W):
    """カメラ (Rm,t,K) から半径 radius の球を見た解析的な深度画像(球に当たらぬ画素=0)。"""
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    Cc = Rm @ np.asarray(c, float) + np.asarray(t, float)
    uu, vv = np.meshgrid(np.arange(W), np.arange(H))
    d = np.stack([(uu - cx) / fx, (vv - cy) / fy, np.ones_like(uu, float)], -1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    b = (d * Cc).sum(-1)
    cc = float(Cc @ Cc) - radius ** 2
    disc = b * b - cc
    s = b - np.sqrt(np.clip(disc, 0.0, None))
    valid = (disc >= 0.0) & (s > 0.0)
    depth = np.zeros((H, W))
    depth[valid] = (s * d[..., 2])[valid]
    return depth


eye0 = center + np.array([0.0, 0.0, 4.0 * R])
Rm0, t0 = visualhull.look_at(eye0, center, up=(0.0, 1.0, 0.0))
depth0 = render_sphere_depth(center, R, Rm0, t0, K, H, Wd)
Cc = Rm0 @ center + t0                            # 球中心のカメラ座標

pts_cam = X.depth_to_points(depth0, focal, focal, cxp, cyp)     # (N,3) カメラ座標
d_true = np.abs(np.linalg.norm(pts_cam - Cc, axis=1) - R)       # 真中心からの半径残差
d_null = np.abs(np.linalg.norm(pts_cam - (Cc + np.array([0.5, 0.0, 0.0])), axis=1) - R)
med_true, med_null = float(np.median(d_true)), float(np.median(d_null))
print(f"[depth_to_points] 逆投影点 {len(pts_cam)} 個, median|d-R|={med_true:.4g}  (誤中心null={med_null:.4g})")
assert pts_cam.shape[1] == 3 and len(pts_cam) > 1000
assert med_true < 0.02 * R, f"逆投影点が球面に載っていない: {med_true:.4g}"
assert med_true < 0.1 * med_null, "誤中心nullを判別的に上回れていない"

# ═══════════════════════════════════════════════════════════════════════════
# 2) to_points: 任意構造 → 点群の統一入口(全5種を1本に集約)
# ═══════════════════════════════════════════════════════════════════════════
p_depth = fuse3d.to_points(depth0, "depth", fx=focal, fy=focal, cx=cxp, cy=cyp)
p_mesh = fuse3d.to_points((V, Fc), "mesh", samples=8000)
p_gs = fuse3d.to_points(means, "3dgs")
# occupancy voxel(solid 球)→ 点群(voxel index)。§4 で作る occ_solid を使う
zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
wx = lo[0] + xx / (size - 1) * span             # points_to_voxel は idx0→x,1→y,2→z
wy = lo[1] + yy / (size - 1) * span
wz = lo[2] + zz / (size - 1) * span
# 注: mgrid 軸と x/y/z の対応は idx0→x のため、grid を (i=x,j=y,k=z) として組み直す
gi, gj, gk = np.mgrid[0:size, 0:size, 0:size]
wxx = lo[0] + gi / (size - 1) * span
wyy = lo[1] + gj / (size - 1) * span
wzz = lo[2] + gk / (size - 1) * span
dist_grid = np.sqrt((wxx - center[0]) ** 2 + (wyy - center[1]) ** 2 + (wzz - center[2]) ** 2)
occ_solid = (dist_grid <= R).astype(np.float64)  # solid 球 occupancy(§7 でも使用)
p_vox = fuse3d.to_points(occ_solid, "voxel", iso=0.5)

dm = np.abs(np.linalg.norm(p_mesh - center, axis=1) - R)
print(f"[to_points] depth経路==depth_to_points: {np.allclose(p_depth, pts_cam)}, "
      f"mesh経路 median|d-R|={float(np.median(dm)):.4g}, voxel点={len(p_vox)}, 3dgs点={len(p_gs)}")
assert np.allclose(p_depth, pts_cam), "to_points(depth) は depth_to_points と一致すべき"
assert float(np.median(dm)) < 0.02 * R, "to_points(mesh) が球面に載っていない"
assert len(p_vox) > 1000 and p_gs.shape == means.shape

# ═══════════════════════════════════════════════════════════════════════════
# 3) mesh_to_voxel & gaussians_to_voxel: 異種構造 → 同一格子の密度ボクセル
# ═══════════════════════════════════════════════════════════════════════════
vol_mesh = X.mesh_to_voxel(V, Fc, size, bounds=bounds, samples=60000, smooth=0.8)
vol_gs = X.gaussians_to_voxel(means, scales, opac, size, bounds=bounds)
occ_mesh = vol_mesh > 0.05 * vol_mesh.max()
occ_gs = vol_gs > 0.05 * vol_gs.max()


def shell_radius_stats(occ):
    ijk = np.argwhere(occ)
    return np.abs(np.linalg.norm(voxel_index_to_world(ijk) - center, axis=1) - R)


rs_mesh = shell_radius_stats(occ_mesh)
rs_gs = shell_radius_stats(occ_gs)
iou_mg = float((occ_mesh & occ_gs).sum() / (occ_mesh | occ_gs).sum())
shifted = np.zeros_like(occ_gs); s = 6
shifted[s:, s:, s:] = occ_gs[:-s, :-s, :-s]     # null: 数 voxel ずらした殻
iou_null = float((occ_mesh & shifted).sum() / (occ_mesh | shifted).sum())
print(f"[mesh_to_voxel] 殻 median|d-R|={float(np.median(rs_mesh)):.3g} ({int(occ_mesh.sum())} vox)")
print(f"[gaussians_to_voxel] 殻 median|d-R|={float(np.median(rs_gs)):.3g} ({int(occ_gs.sum())} vox)")
print(f"    mesh/gauss occupancy IoU={iou_mg:.3f}  (ずらしnull={iou_null:.3f})")
assert float(np.median(rs_mesh)) < 2.0 * vox and np.percentile(rs_mesh, 90) < 4.0 * vox
assert float(np.median(rs_gs)) < 2.0 * vox and np.percentile(rs_gs, 90) < 4.0 * vox
assert iou_mg > 0.30, f"2 構造の voxel 表現が一致しない: IoU={iou_mg:.3f}"
assert iou_mg > 4.0 * iou_null, "一致IoUがずらしnullを判別的に上回れていない"

# ═══════════════════════════════════════════════════════════════════════════
# 4) voxel_to_mips: ボクセル → 直交 3 方向 MIP。球なら 3 枚が合同・面積≈πR²
# ═══════════════════════════════════════════════════════════════════════════
mips = X.voxel_to_mips(vol_mesh)
areas, cents = [], []
for mp in mips:
    on = mp > 0.05 * mp.max()
    areas.append(int(on.sum()))
    ij = np.argwhere(on)
    cents.append(ij.mean(0))
areas = np.array(areas, float)
disk = np.pi * r_vox ** 2
sym_ratio = areas.max() / areas.min()
cen_err = max(np.linalg.norm(c - (size - 1) / 2.0) for c in cents)
print(f"[voxel_to_mips] 3面 on面積={[int(a) for a in areas]} (πR²={disk:.0f}), "
      f"対称比 max/min={sym_ratio:.3f}, 中心誤差={cen_err:.2f} vox")
assert all(mp.shape == (size, size) for mp in mips) and len(mips) == 3
assert sym_ratio < 1.06, f"球なのに 3 MIP 面積が非対称(非球なら崩れる量): {sym_ratio:.3f}"
assert 0.6 * disk < areas.mean() < 1.6 * disk, "MIP 円板面積が πR² と桁で合わない"
assert areas.mean() < 0.7 * size ** 2, "MIP が枠を埋めていない=コンパクト円板(null)"
assert cen_err < 2.5, "MIP 円板の中心が球中心の投影に載っていない"

# ═══════════════════════════════════════════════════════════════════════════
# 5) signed_distance_field & 6) sdf_to_occupancy: occupancy ↔ SDF の可逆対
# ═══════════════════════════════════════════════════════════════════════════
sdf = X.signed_distance_field(occ_solid, device="cpu", iso=0.5)      # 内<0 / 外>0(voxel 単位)
analytic = (dist_grid - R) / vox                                      # 解析符号距離(voxel 単位)
analytic_wrong = (np.sqrt((wxx - center[0] - 0.4 * R) ** 2 + (wyy - center[1]) ** 2
                          + (wzz - center[2]) ** 2) - R) / vox        # 誤中心 null
corr = float(np.corrcoef(sdf.ravel(), analytic.ravel())[0, 1])
rms_true = float(np.sqrt(np.mean((sdf - analytic) ** 2)))
rms_null = float(np.sqrt(np.mean((sdf - analytic_wrong) ** 2)))
print(f"[signed_distance_field] SDF vs 解析: corr={corr:.4f}, RMS={rms_true:.3f} vox  (誤中心null RMS={rms_null:.3f})")
assert corr > 0.99, f"SDF が解析符号距離と一致しない: corr={corr:.4f}"
assert rms_true < 0.6, f"SDF の RMS 誤差が大きすぎ: {rms_true:.3f} vox"
assert rms_true < 0.25 * rms_null, "誤中心nullを判別的に上回れていない"

occ_rt = X.sdf_to_occupancy(sdf, iso=0.0)                             # SDF ≤ 0 → 内側
a, b = occ_rt > 0.5, occ_solid > 0.5
iou_rt = float((a & b).sum() / (a | b).sum())
occ_shift = np.zeros_like(b); occ_shift[4:] = b[:-4]                  # null: ずらした occ
iou_rt_null = float((a & occ_shift).sum() / (a | occ_shift).sum())
print(f"[sdf_to_occupancy] occ→SDF→occ 往復 IoU={iou_rt:.4f}  (ずらしnull={iou_rt_null:.3f})")
assert iou_rt > 0.98, f"occ↔SDF 往復で occupancy が復元されない: IoU={iou_rt:.4f}"
assert iou_rt > 1.3 * iou_rt_null, "往復IoUがずらしnullを上回れていない"

# ═══════════════════════════════════════════════════════════════════════════
# 7) tsdf_from_depth: 単フレーム深度 → TSDF。ゼロ交差帯が可視球面に載る
# ═══════════════════════════════════════════════════════════════════════════
tb_lo, tb_hi = Cc - 1.4 * R, Cc + 1.4 * R
tsz = 48
tsdf1 = X.tsdf_from_depth(depth0, focal, focal, cxp, cyp, size=tsz, bounds=(tb_lo, tb_hi), trunc=3.0)
# tsdf_from_depth の格子: axis0→z, axis1→y, axis2→x, 中心 = (idx+0.5)/tsz
tspan = tb_hi - tb_lo
az, ay, ax = np.mgrid[0:tsz, 0:tsz, 0:tsz]
cx_w = tb_lo[0] + (ax + 0.5) / tsz * tspan[0]
cy_w = tb_lo[1] + (ay + 0.5) / tsz * tspan[1]
cz_w = tb_lo[2] + (az + 0.5) / tsz * tspan[2]
dist_to_Cc = np.sqrt((cx_w - Cc[0]) ** 2 + (cy_w - Cc[1]) ** 2 + (cz_w - Cc[2]) ** 2)
near = np.abs(tsdf1) < 0.15                       # ゼロ等値面帯
zero_dist = dist_to_Cc[near]
med_zero = float(np.median(zero_dist))
# null: 誤中心から測ると R から外れる
med_zero_null = float(np.median(np.sqrt((cx_w[near] - Cc[0] - 0.5) ** 2
                                        + (cy_w[near] - Cc[1]) ** 2 + (cz_w[near] - Cc[2]) ** 2)))
print(f"[tsdf_from_depth] TSDF範囲=[{tsdf1.min():.2f},{tsdf1.max():.2f}], "
      f"ゼロ帯 {int(near.sum())} vox, median dist→Cc={med_zero:.3f} (R={R}, 誤中心null={med_zero_null:.3f})")
assert tsdf1.min() < -0.3 < 0.3 < tsdf1.max(), "TSDF が表面前後(±)を跨いでいない"
assert near.sum() > 100, "ゼロ交差帯が検出されない"
assert abs(med_zero - R) < 0.1 * R, f"ゼロ帯が可視球面(距離R)に載っていない: {med_zero:.3f}"
assert abs(med_zero - R) < abs(med_zero_null - R), "誤中心nullより真中心の方が R に近い(判別)"

# ═══════════════════════════════════════════════════════════════════════════
# 8) fuse_to_voxel: mesh + points + 3dgs を 1 つの密度ボクセルへ融合
# ═══════════════════════════════════════════════════════════════════════════
world_pts = sphere_points(center, R, 4000, rng)
items = [((V, Fc), "mesh", {}), (world_pts, "points", {}), (means, "3dgs", {})]
vol_fused, _ = fuse3d.fuse_to_voxel(items, size=size, bounds=bounds, smooth=0.8)
occ_fused = vol_fused > 0.05 * vol_fused.max()
rs_fused = shell_radius_stats(occ_fused)
med_fused = float(np.median(rs_fused))
# null: 誤中心へ測った殻残差
ijk_f = np.argwhere(occ_fused)
med_fused_null = float(np.median(np.abs(
    np.linalg.norm(voxel_index_to_world(ijk_f) - (center + np.array([0.4, 0, 0])), axis=1) - R)))
print(f"[fuse_to_voxel] 融合殻 median|d-R|={med_fused:.3g} ({int(occ_fused.sum())} vox, "
      f"誤中心null={med_fused_null:.3g})")
assert med_fused < vox, f"融合殻が球面から 1 voxel 以上ずれている: {med_fused:.3g}"
assert med_fused < 0.5 * med_fused_null, "融合殻が誤中心nullを判別的に上回れていない"

# ═══════════════════════════════════════════════════════════════════════════
# 9) register_cross: CAD メッシュ(段付きブロック)→ スキャン点群を剛体整合
#    球は回転対称で姿勢不能なので、ここは非対称な段付き立体を使う。
# ═══════════════════════════════════════════════════════════════════════════
def box_tris(xr, yr, zr):
    (xa, xb), (ya, yb), (za, zb) = xr, yr, zr
    Vb = np.array([[xa, ya, za], [xb, ya, za], [xb, yb, za], [xa, yb, za],
                   [xa, ya, zb], [xb, ya, zb], [xb, yb, zb], [xa, yb, zb]], float)
    Fb = np.array([[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6], [0, 4, 5], [0, 5, 1],
                   [1, 5, 6], [1, 6, 2], [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0]], int)
    return Vb, Fb


def stepped_mesh():
    """非対称な段付きブロック(大箱 + 端に載る小箱)。回転対称が無く姿勢が一意。"""
    V1, F1 = box_tris((0, 10), (0, 6), (0, 3))
    V2, F2 = box_tris((0, 3), (0, 6), (3, 5))
    return np.vstack([V1, V2]), np.vstack([F1, F2 + len(V1)])


def rotmat(axis, deg):
    ax = np.asarray(axis, float); ax /= np.linalg.norm(ax); th = np.radians(deg)
    Kx = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * Kx @ Kx


def align_rmse(src, dst, Re, te):
    moved = src @ np.asarray(Re).T + np.asarray(te)
    dd, _ = cKDTree(dst).query(moved, k=1)
    return float(np.sqrt(np.mean(dd ** 2)))


Vs, Fs = stepped_mesh()
Rg, tg = rotmat([0.3, 1.0, 0.2], 40.0), np.array([3.0, -2.0, 1.0])   # 既知の剛体変換
src_ref = fuse3d.to_points((Vs, Fs), "mesh", samples=6000)           # CAD 表面点(整列採点用)
dst_scan = fuse3d.to_points((Vs, Fs), "mesh", samples=6000) @ Rg.T + tg   # 別サンプルの「スキャン」
scale = float(np.linalg.norm(src_ref.max(0) - src_ref.min(0)))
# CROSS: mesh(CAD)を points(スキャン)へ直接登録(内部で両者を点群化)
Rf, tf = fuse3d.register_cross((Vs, Fs), "mesh", dst_scan, "points", method="fpfh")
rmse_reg = align_rmse(src_ref, dst_scan, Rf, tf)
rmse_init = align_rmse(src_ref, dst_scan, np.eye(3), np.zeros(3))     # null: 変換前(恒等)
rot_err = float(np.degrees(np.arccos(np.clip((np.trace(np.asarray(Rf) @ Rg.T) - 1) / 2, -1, 1))))
print(f"[register_cross] mesh→points 整列RMSE={rmse_reg:.4f} (スケール{scale:.2f}の{rmse_reg/scale*100:.2f}%), "
      f"回転誤差={rot_err:.2f}°, 恒等null={rmse_init:.3f}")
assert rmse_reg < 0.03 * scale, f"CAD↔スキャンの整合が甘い: RMSE={rmse_reg:.4f}"
assert rot_err < 3.0, f"回転の復元誤差が大きい: {rot_err:.2f}°"
assert rmse_reg < 0.1 * rmse_init, "整列後RMSEが恒等null(変換前)を判別的に下回れていない"

# ═══════════════════════════════════════════════════════════════════════════
# 10) integrate: 多フレーム深度を投影的 TSDF に統合 → ゼロ交差表面が真球に載る
# ═══════════════════════════════════════════════════════════════════════════
def fib_dirs(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    ga = np.pi * (1.0 + 5.0 ** 0.5)
    th = ga * i
    return np.stack([np.sin(phi) * np.cos(th), np.sin(phi) * np.sin(th), np.cos(phi)], 1)


res = 64
mm = 1.25 * R
b3 = ((center[0] - mm, center[0] + mm), (center[1] - mm, center[1] + mm),
      (center[2] - mm, center[2] + mm))
voxel3 = 2.0 * mm / res
trunc = 4.0 * voxel3
eyes = center[None, :] + 4.0 * R * fib_dirs(10)

# 単フレーム(視点0)と多フレームを比較。どちらも integrate を直接呼ぶ(fuse は使わない)。
def surface_from_frames(eye_list):
    tsdf_v, w_v = tsdf_fusion.new_volume(b3, res)
    for eye in eye_list:
        Rm, t = visualhull.look_at(eye, center, up=(0.0, 0.0, 1.0))
        dep = render_sphere_depth(center, R, Rm, t, K, H, Wd)
        tsdf_fusion.integrate(tsdf_v, w_v, dep, K, Rm, t, trunc, bounds=b3)
    return tsdf_fusion.extract_surface_points(tsdf_v, w_v, b3, res)


sp_single = surface_from_frames(eyes[:1])
sp_multi = surface_from_frames(eyes)
r_multi = np.abs(np.linalg.norm(sp_multi - center, axis=1) - R)
med_multi = float(np.median(r_multi))
r_multi_null = float(np.median(np.abs(
    np.linalg.norm(sp_multi - (center + np.array([0.3, 0, 0])), axis=1) - R)))
print(f"[integrate] 単F表面点={len(sp_single)}, 多F(10)表面点={len(sp_multi)}, "
      f"多F median|r-R|={med_multi:.4g} (voxel={voxel3:.3g}, 誤中心null={r_multi_null:.3g})")
assert len(sp_multi) > 0 and sp_multi.shape[1] == 3
assert med_multi < voxel3, f"融合表面が真球から 1 voxel 以上ずれている: {med_multi:.4g}"
assert med_multi < 0.3 * r_multi_null, "融合表面が誤中心nullを判別的に上回れていない"
assert len(sp_multi) > len(sp_single), "多視点融合が単フレームより表面を多く復元していない(全周被覆)"

print("PASS: 球(+段付き立体)を depth/mesh/3dgs/points/voxel/SDF/TSDF へ相互変換し、"
      "全変換 op の出力が解析真値(中心Cからの距離≈R・往復IoU≈1・整列RMSE<3%)に一致、"
      "各々が誤中心/ずらし/恒等/非対称nullを判別的に上回ることを確認")

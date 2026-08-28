# -*- coding: utf-8 -*-
"""事例: 2 視点 SfM から表面再構成まで、1 つの球で通す (reconstruction).

平たく言うと: 同じ物体を 2 枚の画像で撮ると、対応点だけから「カメラがどれだけ動いたか
(本質行列 E)」と「点の 3D 位置(三角測量)」が出せる(Structure-from-Motion の核)。
多視点でためた密な点群からは、alpha shape で**表面の殻**だけ抜き出し、符号付き距離場(SDF)を
オフセットして殻に厚みを付け、その表面を深度画像として**観測合成**できる。ここでは全部を
**中心 [0,0,6]・半径 1.5 の 1 つの球**で一気通貫に示し、6 つの op を鎖のように繋ぐ:

  essential_8point → triangulate → mean_edge_error → alpha_shape_boundary → sdf_offset → render_point_depth

検証(GT): すべて既知真値と照合する(合成なのでノイズ無し)。
  1. essential_8point : 復元 E が真の E=[t]×R と(符号/スケールを除き)一致 |cos|≈1、
                        正規化エピポーラ残差 x̂2ᵀE x̂1 ≈ 0。
  2. triangulate      : 真の射影行列で 3D 点を機械精度復元。E から復元した姿勢での
                        三角測量も(スケール合わせ後)真の点群に一致。
  3. mean_edge_error  : 真姿勢グラフの整合誤差 = 0。SfM で復元した姿勢をノードに差しても
                        残差はほぼ 0(= SfM が幾何に整合)。
  4. alpha_shape_boundary : 立体球の境界点は半径 ≈ R(表面の殻)。
  5. sdf_offset       : sdf_offset(sphere_sdf(R), r) == sphere_sdf(R+r) を機械精度で。
  6. render_point_depth : 殻の深度画像は物理境界 [d−R, d+R] 内、最前面 ≈ d−R。z-buffer は
                        同一画素で最近点を採用。半径スケール s で深度が s 倍(単調)。

beat-the-null: 各段に「わざと外した」零点比較を置く — 誤回転の E(|cos| 小・残差大)、
対応点シャッフルの三角測量(誤差桁違い)、ドリフト姿勢の edge error(> 0・単調)、
立体球点群のランダム部分集合(表面率が低い)、誤オフセット量、平坦(全 0)深度。
すべて「動いた」ではなく「真値を復元し零点を判別的に上回る」ことを assert する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
import twoview          # essential_8point / triangulate / decompose_essential
import pose_graph       # mean_edge_error / relative_pose
import recon3d          # alpha_shape_boundary / estimate_alpha
import sdf_ops          # sdf_offset / sphere_sdf / grid_coords
import match3d          # render_point_depth


# --------------------------------------------------------------------------- #
# 幾何ヘルパ                                                                    #
# --------------------------------------------------------------------------- #
def rot(axis, deg):
    """軸まわり deg 度の回転行列(Rodrigues)。"""
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    th = np.deg2rad(deg)
    Kx = np.array([[0, -axis[2], axis[1]],
                   [axis[2], 0, -axis[0]],
                   [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * (Kx @ Kx)


def rot_angle_deg(Ra, Rb):
    """2 つの回転行列の角度差(度)。"""
    c = np.clip((np.trace(Ra.T @ Rb) - 1) / 2, -1, 1)
    return float(np.rad2deg(np.arccos(c)))


def skew(v):
    """3 ベクトル → 反対称行列 [v]×(v × x = [v]× x)。"""
    v = np.asarray(v, float)
    return np.array([[0, -v[2], v[1]],
                     [v[2], 0, -v[0]],
                     [-v[1], v[0], 0]])


def homog(pts):
    """(N,2) → 同次 (N,3)。"""
    p = np.asarray(pts, float)
    return np.hstack([p, np.ones((len(p), 1))])


def projection(K, R, t):
    """P = K[R|t](3,4)。"""
    return K @ np.hstack([np.asarray(R, float), np.asarray(t, float).reshape(3, 1)])


# 共通シーン: 中心 [0,0,6]・半径 1.5 の球(全 op がこの 1 つの球を扱う)
K = np.array([[800.0, 0, 320.0],
              [0, 800.0, 240.0],
              [0, 0, 1.0]])
C_SPHERE = np.array([0.0, 0.0, 6.0])   # 球中心(カメラから距離 d=6)
R_SPHERE = 1.5                         # 球半径 R
D = float(C_SPHERE[2])                 # 光軸方向のカメラ〜中心距離

R_true = rot([0.2, 1.0, 0.1], 18.0)    # 2 台目カメラの真の回転(18 度)
t_true = np.array([1.0, 0.15, 0.1])    # 真の並進(単眼ではスケール不定)
base = float(np.linalg.norm(t_true))   # 真の基線長(= |t| スケール)


# =========================================================================== #
# Part 1 — 2 視点 SfM: essential_8point + triangulate                          #
# =========================================================================== #
# 球表面に散らした 3D 点を 2 台のカメラへ投影(両カメラ前方の点だけ残す)
rng = np.random.default_rng(0)
X = []
while len(X) < 48:
    d = rng.standard_normal(3)
    p = C_SPHERE + R_SPHERE * d / np.linalg.norm(d)           # 球面上の点
    if p[2] > 0.5 and (R_true @ p + t_true)[2] > 0.5:         # 両カメラ前方
        X.append(p)
X = np.array(X)

P1_true = projection(K, np.eye(3), np.zeros(3))               # cam1 = K[I|0]
P2_true = projection(K, R_true, t_true)                      # cam2 = K[R|t]
Xh = np.hstack([X, np.ones((len(X), 1))])                    # 同次 4 次 [X;1]
u1 = (P1_true @ Xh.T).T
u2 = (P2_true @ Xh.T).T
pts1 = u1[:, :2] / u1[:, 2:3]                                 # 1 枚目の観測画素
pts2 = u2[:, :2] / u2[:, 2:3]                                 # 2 枚目の観測画素

# --- (1) essential_8point: 対応点 + K から本質行列 E ------------------------
E_est = twoview.essential_8point(pts1, pts2, K)

# GT: 真の E = [t_unit]× R(スケール/符号を除き一致)。両者 |·|_F=√2(特異値 1,1,0)。
t_unit = t_true / base
E_true = skew(t_unit) @ R_true
cos_E = float(np.sum(E_est * E_true) / (np.linalg.norm(E_est) * np.linalg.norm(E_true)))

# beat-null: 誤った回転で作った E とは方向が合わない
R_wrong = rot([0.0, 1.0, 0.0], 40.0)
E_wrong = skew(t_unit) @ R_wrong
cos_Ew = float(np.sum(E_est * E_wrong) / (np.linalg.norm(E_est) * np.linalg.norm(E_wrong)))

# 正規化エピポーラ残差 x̂2ᵀ E x̂1(x̂ = K⁻¹ x)。真の E_est ≈0 / 誤 E_wrong は大きい。
Kinv = np.linalg.inv(K)
xh1 = (Kinv @ homog(pts1).T).T
xh2 = (Kinv @ homog(pts2).T).T
r_est = np.einsum("ij,jk,ik->i", xh2, E_est, xh1)
r_wrong = np.einsum("ij,jk,ik->i", xh2, E_wrong, xh1)

print(f"[1] E 方向一致 |cos(E_est,E_true)| = {abs(cos_E):.6f}  (誤回転 null |cos| = {abs(cos_Ew):.3f})")
print(f"[1] エピポーラ残差 max |x̂2ᵀE x̂1| = {np.max(np.abs(r_est)):.2e}  (誤 E null = {np.max(np.abs(r_wrong)):.2e})")
assert abs(cos_E) > 0.999, f"E が真値と方向一致しない: |cos|={abs(cos_E)}"
assert abs(cos_E) > abs(cos_Ew) + 0.2, f"E が誤回転 null を判別的に上回らない: {abs(cos_E)} vs {abs(cos_Ew)}"
assert np.max(np.abs(r_est)) < 1e-6, f"エピポーラ残差が大きい: {np.max(np.abs(r_est))}"
assert np.max(np.abs(r_wrong)) > 1e-2, "null(誤 E)がエピポーラ拘束を破っていない(零点が本物でない)"

# --- (2) triangulate: 真の射影行列で 3D 点を復元(機械精度)-----------------
X_rec = twoview.triangulate(pts1, pts2, P1_true, P2_true)
err_true = np.linalg.norm(X_rec - X, axis=1)

# beat-null: 対応点をシャッフル(誤マッチ)した三角測量は真の点から大きく外れる
perm = rng.permutation(len(pts2))
X_bad = twoview.triangulate(pts1, pts2[perm], P1_true, P2_true)
err_bad = np.linalg.norm(X_bad - X, axis=1)

print(f"[2] 三角測量(真P)3D誤差 max = {err_true.max():.2e}  (対応シャッフル null mean = {err_bad.mean():.3f})")
assert err_true.max() < 1e-6, f"三角測量が真の点群を復元できていない: {err_true.max()}"
assert err_bad.mean() > 1e-2, "null(誤マッチ)が真値に一致してしまう(零点が本物でない)"

# --- (2b) 合成: E_est から姿勢を復元し、triangulate で cheirality 選択 -------
# decompose_essential の 4 候補それぞれで triangulate → 両カメラ前方(depth>0)の点数で一意化。
best = None
for R_c, t_c in twoview.decompose_essential(E_est):
    P2_c = projection(K, R_c, t_c)                           # t は単位ベクトル
    Xc = twoview.triangulate(pts1, pts2, P1_true, P2_c)      # ← ここでも triangulate
    z1 = Xc[:, 2]
    z2 = ((R_c @ Xc.T).T + t_c)[:, 2]
    cnt = int(np.sum((z1 > 0) & (z2 > 0)))
    if best is None or cnt > best[0]:
        best = (cnt, R_c, t_c, Xc)
_, R_est, t_est, X_sfm = best

rot_err = rot_angle_deg(R_est, R_true)
t_dir = float(np.dot(t_est / np.linalg.norm(t_est), t_unit))
X_sfm_metric = X_sfm * base                                  # |t|=1 スケール → 真の基線へ
err_sfm = np.linalg.norm(X_sfm_metric - X, axis=1)
print(f"[2b] E→姿勢復元: 回転誤差 {rot_err:.3e}度 / 並進方向 dot {t_dir:.6f} / "
      f"三角測量(復元姿勢)3D誤差 max {err_sfm.max():.2e}")
assert rot_err < 1e-2, f"復元回転が真値からずれる: {rot_err}度"
assert t_dir > 0.9999, f"復元並進方向がずれる: dot={t_dir}"
assert err_sfm.max() < 1e-6, f"復元姿勢での三角測量が真値からずれる: {err_sfm.max()}"


# =========================================================================== #
# Part 2 — 姿勢グラフ整合誤差(BA 的残差): mean_edge_error                     #
# =========================================================================== #
# SfM で得た相対姿勢をエッジ制約に、姿勢グラフの整合度を測る。pose_graph の姿勢は
# world←body 規約(p_world = R_i p_i + t_i)。カメラ外部 [R|t](world→cam)の逆を取る。
def cam_to_node(R_cam, t_cam):
    """カメラ外部 [R|t](world→cam)→ pose_graph ノード [rvec|t](world←cam)。"""
    Rn = R_cam.T
    tn = -R_cam.T @ np.asarray(t_cam, float)
    return np.concatenate([pose_graph.R_to_rvec(Rn), tn])

# 3 ノード(= 3 カメラ)。node1 の真姿勢は 2 視点 SfM の cam2。
R_cam3 = rot([0.1, 0.3, 1.0], 25.0)
t_cam3 = np.array([1.6, -0.4, 0.3]) * base
pose0 = cam_to_node(np.eye(3), np.zeros(3))                  # cam1(基準)
pose1 = cam_to_node(R_true, t_true)                         # cam2(SfM 対象)
pose2 = cam_to_node(R_cam3, t_cam3)                        # cam3
poses_true = np.stack([pose0, pose1, pose2])

# エッジ = 真の相対姿勢(オドメトリ 0-1,1-2 + ループ閉じ 0-2)
def edge(i, j):
    rvec_ij, t_ij = pose_graph.relative_pose(poses_true[i], poses_true[j])
    return (i, j, rvec_ij, t_ij)

edges = [edge(0, 1), edge(1, 2), edge(0, 2)]

err0 = pose_graph.mean_edge_error(poses_true, edges)
# 合成: SfM で復元した姿勢を node1 に差し替えても整合(残差ほぼ 0 = SfM が幾何に整合)
pose1_sfm = cam_to_node(R_est, t_est * base)               # 復元 R,t(スケール合わせ)
poses_sfm = np.stack([pose0, pose1_sfm, pose2])
err_sfm_graph = pose_graph.mean_edge_error(poses_sfm, edges)

# beat-null: ドリフト姿勢は整合誤差 > 0、ドリフトを倍にすると誤差も増える(単調)
def drift(delta, seed=7):
    g = np.random.default_rng(seed)
    p = poses_true.copy()
    p[1:] += g.normal(0.0, delta, p[1:].shape)              # 先頭以外を摂動
    return pose_graph.mean_edge_error(p, edges)

err_d1 = drift(0.02)
err_d2 = drift(0.04)
# 決定性: 同じ入力は同じ出力
det = pose_graph.mean_edge_error(poses_true, edges)

print(f"[3] 姿勢グラフ整合誤差: 真値 {err0:.2e} / SfM姿勢 {err_sfm_graph:.2e} / "
      f"ドリフト0.02 {err_d1:.4f} / 0.04 {err_d2:.4f}")
assert err0 < 1e-9, f"真姿勢グラフの整合誤差が 0 でない: {err0}"
assert det == err0, "mean_edge_error が非決定的"
assert err_sfm_graph < 1e-4, f"SfM 姿勢がグラフに整合しない(SfM 不正確): {err_sfm_graph}"
assert err_d1 > 1e-3, f"ドリフト null が整合誤差を増やさない(零点が本物でない): {err_d1}"
assert err_d2 > err_d1, f"整合誤差がドリフト量に単調でない: {err_d2} !> {err_d1}"


# =========================================================================== #
# Part 3 — 表面再構成: alpha_shape_boundary                                    #
# =========================================================================== #
# 密な立体球(体積一様、表面+内部)から表面の殻だけ抜く。
def solid_ball(n, c, R, seed):
    g = np.random.default_rng(seed)
    d = g.standard_normal((n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    rad = R * np.cbrt(g.uniform(0.0, 1.0, n))                # 体積一様(半径 CDF ∝ r³)
    return c + rad * d

N_BALL = 4000
ball = solid_ball(N_BALL, C_SPHERE, R_SPHERE, seed=3)
rad_all = np.linalg.norm(ball - C_SPHERE, axis=1)           # 各点の中心距離(真値)

alpha = recon3d.estimate_alpha(ball) * 0.5                  # 中実を素直に埋める(torus 事例と同流儀)
bidx = recon3d.alpha_shape_boundary(ball, alpha)            # 境界点インデックス
rad_bnd = rad_all[bidx]
near_surf_bnd = float(np.mean(rad_bnd > 0.9 * R_SPHERE))    # 境界の表面率

# beat-null: 同数のランダム部分集合(内部を含むので表面率が低い)
g = np.random.default_rng(11)
ridx = g.choice(N_BALL, size=len(bidx), replace=False)
near_surf_rand = float(np.mean(rad_all[ridx] > 0.9 * R_SPHERE))

print(f"[4] alpha 境界点: {len(bidx)}/{N_BALL}  平均半径 {rad_bnd.mean():.3f}(真 R={R_SPHERE}) "
      f"表面率 {near_surf_bnd:.3f}  (ランダム部分集合 null {near_surf_rand:.3f})")
assert 0 < len(bidx) < N_BALL, f"境界点が空か全点: {len(bidx)}"
assert abs(rad_bnd.mean() - R_SPHERE) < 0.1 * R_SPHERE, f"境界点の平均半径が R から外れる: {rad_bnd.mean()}"
assert near_surf_bnd > 0.8, f"境界が表面の殻になっていない(表面率低): {near_surf_bnd}"
assert near_surf_bnd > near_surf_rand + 0.3, \
    f"境界がランダム null を判別的に上回らない: {near_surf_bnd} vs {near_surf_rand}"

# 再構成した表面殻の点(以降の SDF / 深度合成で使う)
shell = ball[bidx]


# =========================================================================== #
# Part 4 — SDF に厚みを付ける: sdf_offset                                      #
# =========================================================================== #
# 復元した半径 R の球を解析 SDF で表し、オフセットで殻に厚みを付ける。
lo = C_SPHERE - (R_SPHERE + 1.0)
hi = C_SPHERE + (R_SPHERE + 1.0)
bounds = np.stack([lo, hi], axis=1)                        # ((xmin,xmax),(ymin,ymax),(zmin,zmax))
grid, _extent = sdf_ops.grid_coords(bounds, 32)           # coords (32,32,32,3)
sdf_R = sdf_ops.sphere_sdf(grid, C_SPHERE, R_SPHERE)        # 半径 R の球 SDF

delta = 0.4                                                 # 付ける厚み(r>0=膨張)
sdf_off = sdf_ops.sdf_offset(sdf_R, delta)                 # = sdf_R - delta
sdf_expect = sdf_ops.sphere_sdf(grid, C_SPHERE, R_SPHERE + delta)   # 半径 R+δ の球 SDF

# GT: オフセットは半径を +δ した球 SDF に機械精度で一致
max_off_err = float(np.max(np.abs(sdf_off - sdf_expect)))
# beat-null: 誤ったオフセット量(δ/2)では一致しない
sdf_wrong = sdf_ops.sdf_offset(sdf_R, delta * 0.5)
max_wrong_err = float(np.max(np.abs(sdf_wrong - sdf_expect)))
# 単調: 正オフセットは内側(sdf<0)ボクセルを増やす(= 膨張)
inside0 = int(np.sum(sdf_R < 0))
inside1 = int(np.sum(sdf_off < 0))
# ゼロ等値面の移動: 半径 R+δ の点は オフセット SDF で ≈0
probe_dir = g.standard_normal((200, 3)); probe_dir /= np.linalg.norm(probe_dir, axis=1, keepdims=True)
probe = C_SPHERE + (R_SPHERE + delta) * probe_dir
sdf_probe = sdf_ops.sphere_sdf(probe, C_SPHERE, R_SPHERE)   # 元 SDF ではこの点は +δ
off_probe = sdf_ops.sdf_offset(sdf_probe, delta)           # オフセット後 ≈ 0

print(f"[5] sdf_offset: max|off − sphere(R+δ)| = {max_off_err:.2e}  (誤δ null = {max_wrong_err:.3f})  "
      f"内側ボクセル {inside0}→{inside1}  R+δ 面の残差 {np.max(np.abs(off_probe)):.2e}")
assert max_off_err < 1e-9, f"sdf_offset が sphere_sdf(R+δ) と一致しない: {max_off_err}"
assert max_wrong_err > 0.1, "null(誤オフセット量)が一致してしまう(零点が本物でない)"
assert inside1 > inside0, f"正オフセットが膨張していない: {inside0}→{inside1}"
assert np.max(np.abs(off_probe)) < 1e-9, f"R+δ 面がオフセット SDF のゼロ集合でない: {np.max(np.abs(off_probe))}"


# =========================================================================== #
# Part 5 — 観測合成: render_point_depth                                        #
# =========================================================================== #
# 再構成した表面殻をカメラ(原点・光軸 +z)から見た深度画像。物理境界 [d−R, d+R]。
size = (480, 640)                                           # (H, W)
depth = match3d.render_point_depth(shell, K, size)          # 外部姿勢=恒等
nz = depth[depth > 0]
front, back = D - R_SPHERE, D + R_SPHERE                    # 4.5, 7.5

# 決定性
depth2 = match3d.render_point_depth(shell, K, size)
# 単調(半径スケール): 点を原点から s 倍 → 同一画素で深度が s 倍(u,v 不変・z が s 倍)
s = 1.5
depth_s = match3d.render_point_depth(shell * s, K, size)
both = (depth > 0) & (depth_s > 0)

print(f"[6] 深度画像: 非背景画素 {int((depth>0).sum())}  深度範囲 [{nz.min():.3f}, {nz.max():.3f}] "
      f"(物理境界 [{front:.1f}, {back:.1f}])  最前面 {nz.min():.3f}≈{front:.1f}")
assert (depth > 0).sum() > 0, "深度画像が空(何も描画されていない)"
assert np.array_equal(depth, depth2), "render_point_depth が非決定的"
assert nz.min() >= front - 1e-9, f"深度が物理下界 d−R を割る: {nz.min()} < {front}"
assert nz.max() <= back + 1e-9, f"深度が物理上界 d+R を超える: {nz.max()} > {back}"
assert nz.min() <= front + 0.2 * R_SPHERE, f"最前面(球の手前極 d−R)を捉えていない: {nz.min()}"
assert np.allclose(depth_s[both], s * depth[both]), "半径スケールで深度が s 倍にならない(z-buffer 破綻)"
# beat-null: 平坦(全 0)深度は物理範囲チェックを満たさない
assert not np.all(depth == 0), "深度が全 0(零点)"

# --- z-buffer 意味論の制御 GT(手置き点で真値照合)--------------------------
# 既知の 3D 点を整数画素へ落として、各画素の深度が最近点 z に一致するか。
ctrl = np.array([
    [0.0, 0.0, 5.0],     # → (320,240) z=5
    [1.0, 0.0, 10.0],    # → (400,240) z=10
    [0.0, -1.0, 4.0],    # → (320, 40) z=4
    [2.0, 2.0, 8.0],     # → (520,440) z=8  (最近)
    [3.0, 3.0, 12.0],    # → (520,440) z=12 (奥, z-buffer で隠れる)
])
dctrl = match3d.render_point_depth(ctrl, K, size)
assert dctrl[240, 320] == 5.0, f"手前点の深度が違う: {dctrl[240,320]}"
assert dctrl[240, 400] == 10.0, f"点の深度が違う: {dctrl[240,400]}"
assert dctrl[40, 320] == 4.0, f"点の深度が違う: {dctrl[40,320]}"
assert dctrl[440, 520] == 8.0, f"同一画素で最近点(z=8)を採用していない: {dctrl[440,520]}"
assert dctrl[0, 0] == 0.0, f"点の無い画素が背景 0 でない: {dctrl[0,0]}"


print(f"PASS: 1 つの球で 6 op を鎖状に検証 — "
      f"E |cos|={abs(cos_E):.4f}(誤回転null {abs(cos_Ew):.2f}) / "
      f"三角測量誤差 {err_true.max():.1e}(シャッフルnull {err_bad.mean():.2f}) / "
      f"姿勢グラフ整合 真{err0:.0e}·SfM{err_sfm_graph:.0e}(ドリフトnull {err_d1:.3f}↗{err_d2:.3f}) / "
      f"alpha境界表面率 {near_surf_bnd:.2f}(randnull {near_surf_rand:.2f}) / "
      f"sdf_offset誤差 {max_off_err:.1e}(誤δnull {max_wrong_err:.2f}) / "
      f"深度 [{nz.min():.2f},{nz.max():.2f}]⊂[{front:.1f},{back:.1f}]・z-buffer最近点採用")

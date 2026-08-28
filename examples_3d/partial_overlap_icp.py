"""事例: 別方向から撮った 2 枚の部分スキャンを重ね合わせる (registration).

Physical AI では 1 台の深度センサで物体を一周できず、視点ごとに「見えている面だけ」の
部分点群(partial scan)が得られる。これらを 1 つの座標系へ融合するのが登録(registration)
の中核だが、部分観測どうしは重なりが小さく、しかも別々の位置からサンプルされる(点は
一致しない)ため、素朴な合わせ方は破綻する。ここでは非対称なでこぼこブロブ(ランダムな
瘤を持つ星状凸曲面)の表面を、別方向の 2 視点で可視な部分だけ切り出して scan A(表面の
~6 割)と scan B を作り、B に既知の剛体変換 (R_gt, t_gt) を掛けてバラした上で、
pipeline3d.register_pointclouds(FPFH+RANSAC → ICP)で A へ戻す。重なりは ~4 割の難条件。

検証(GT): B に掛けた変換の真値がわかるので、復元されるべき逆変換 R_rec=R_gt.T が既知。
  * 実 op の回転誤差(測地度)が数度以内で、インライア RMSE が真値整列で到達できる
    「サンプリング/ノイズ床」の水準まで下がる。
  beat-null: (A) 重心+PCA主軸合わせ(ICP なし)と (B) 単位行列から始める ICP は、
  部分重なりでは主軸/最近傍が食い違い大きな回転誤差で固着する。実 op はこの両 null を
  桁違いに下回る=判別的。
"""
import numpy as np
from scipy.spatial import cKDTree

import pipeline3d as P
import match3d as M   # icp_point2point_3d(単位行列開始の null 用)


def _np(x):
    """torch.Tensor / ndarray を numpy に正規化。"""
    return x.detach().cpu().numpy() if hasattr(x, "detach") else np.asarray(x)


def rotation_matrix(axis, deg):
    """軸まわり deg 度の回転行列 (ロドリゲスの公式)。"""
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


def rotation_error_deg(R_est, R_gt):
    """2 つの回転行列の間の測地距離(度)。相対回転の回転角 = 誤差。"""
    R_est = np.asarray(R_est)
    cos = (np.trace(R_est.T @ R_gt) - 1) / 2
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


# --- でこぼこブロブ(非対称・特徴豊富)の半径場 ----------------------------------
# 固定シードで瘤(こぶ)の位置・強さ・鋭さを決める = A/B 共通の「同一物体」。
# 球状の回転対称も平面の姿勢曖昧性も無いので、FPFH の角特徴が効き ICP が締まる。
R0 = 5.0
_BF = np.random.default_rng(0)
_NB = 9
_bump_c = _BF.normal(size=(_NB, 3))
_bump_c /= np.linalg.norm(_bump_c, axis=1, keepdims=True)   # 瘤の中心方向(単位ベクトル)
_bump_a = _BF.uniform(0.15, 0.55, _NB)                       # 瘤の高さ(半径への寄与)
_bump_w = _BF.uniform(2.0, 6.0, _NB)                         # 瘤の鋭さ


def _radius(dirs):
    """方向(単位ベクトル)→ ブロブ半径。瘤は von-Mises 状の隆起の和。"""
    dots = dirs @ _bump_c.T                                  # (N, NB) 各瘤中心との内積
    return R0 * (1.0 + (_bump_a * np.exp(_bump_w * (dots - 1.0))).sum(1))


def sample_blob(n, seed):
    """ブロブ表面を n 点、独立にサンプル。点と(可視判定用の)放射方向を返す。"""
    rng = np.random.default_rng(seed)
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)            # 球面一様な方向
    pts = _radius(d)[:, None] * d                            # 表面点(星状凸)
    return pts, d                                            # d ≈ 外向き放射方向


def visible(radial, view_dir, cos_thr=0.0):
    """視線 view_dir(レイの進む向き)に対し前向き(可視)な面のマスク。

    放射方向 n が視線と逆(n·v < cos_thr)ならカメラ側を向く=可視。cos_thr を少し
    正にすると擦過面も含め、可視率を上げられる。
    """
    v = np.asarray(view_dir, float)
    v /= np.linalg.norm(v)
    return radial @ v < cos_thr


def pca_frame(pts):
    """点群の重心と主軸(列=軸, 降順, 符号決定的, 右手系)を返す。"""
    c = pts.mean(0)
    X = pts - c
    w, V = np.linalg.eigh(X.T @ X / len(X))
    V = V[:, np.argsort(w)[::-1]]
    for k in range(3):                      # 符号: 最大成分を正に固定(決定的)
        if V[np.argmax(np.abs(V[:, k])), k] < 0:
            V[:, k] = -V[:, k]
    if np.linalg.det(V) < 0:                # 右手系に補正
        V[:, 2] = -V[:, 2]
    return c, V


def trimmed_rmse(src, dst, trim):
    """src 各点 → dst 最近傍距離のうち小さい順 trim 割の RMSE(部分重なり評価)。"""
    d = cKDTree(dst).query(src, k=1)[0]
    k = max(3, int(round(len(d) * trim)))
    return float(np.sqrt(np.mean(np.sort(d)[:k] ** 2)))


# ═══ 1) ブロブ表面を 2 回独立サンプルし、別視点の部分スキャン A / B を作る ═══
surf_A, rad_A = sample_blob(9000, seed=1)     # scan A 用の独立サンプル
surf_B, rad_B = sample_blob(9000, seed=2)     # scan B 用の独立サンプル(別realization)

VIEW_A = [0.0, 0.0, 1.0]                       # 上(-z 側)から見る
VIEW_B = [0.966, 0.0, -0.259]                  # A と ~105 度離れた方向 → 部分重なり
mA = visible(rad_A, VIEW_A, cos_thr=0.18)      # cos_thr>0 で擦過面も拾い可視率 ~6 割
mB = visible(rad_B, VIEW_B, cos_thr=0.18)

allpts = np.vstack([surf_A, surf_B])
full_diag = float(np.linalg.norm(allpts.max(0) - allpts.min(0)))
noise = 0.004 * full_diag                      # センサノイズ = 対角長の 0.4%
rngA = np.random.default_rng(10)
rngB = np.random.default_rng(20)
scan_A = surf_A[mA] + rngA.normal(0.0, noise, surf_A[mA].shape)   # 部分スキャン A(A 座標系)
scan_B = surf_B[mB] + rngB.normal(0.0, noise, surf_B[mB].shape)   # 部分スキャン B(同 A 座標系)

fracA = mA.mean()                              # 表面のうち A が見た割合
res = float(np.median(cKDTree(scan_A).query(scan_A, k=2)[0][:, 1]))  # A の点間隔
# 幾何的な重なり率: 変換前の B の点で、A に res の 2 倍以内の最近傍がある割合
d_BA = cKDTree(scan_A).query(scan_B, k=1)[0]
overlap = float((d_BA < 2.0 * res).mean())

# ═══ 2) B に既知の剛体変換を掛けてバラす(未知姿勢の別スキャンを模す)═══
R_gt = rotation_matrix([0.4, 1.0, 0.3], 55.0)  # 大回転 55 度(単位行列 ICP の収束域外)
t_gt = np.array([3.0, -2.0, 4.0])              # 並進
scan_B_moved = scan_B @ R_gt.T + t_gt          # バラした scan B

# 復元されるべき逆変換(GT): B_moved を A 座標系へ戻す (R_rec, t_rec)
R_rec = R_gt.T
t_rec = -t_gt @ R_gt

TRIM = float(np.clip(overlap, 0.35, 0.7))      # 重なり率に合わせた Trimmed ICP

# ═══ 3) 登録: 初期推定なしで B_moved を A へ戻す(FPFH+RANSAC → ICP)═══
R_est, t_est, rmse = P.register_pointclouds(scan_B_moved, scan_A, trim=TRIM)
real_err = rotation_error_deg(R_est, R_rec)

# GT 整列で到達できる RMSE 床(サンプリング差 + ノイズ)。同じ trim で評価
B_gt_aligned = scan_B_moved @ R_rec.T + t_rec
floor_rmse = trimmed_rmse(B_gt_aligned, scan_A, TRIM)

print(f"ブロブ表面点数 A/B        : {len(surf_A)}/{len(surf_B)}  (放射方向つき)")
print(f"scan A(部分)             : {scan_A.shape}  可視率 {fracA:.2f}(表面の ~6 割)")
print(f"scan B(部分)             : {scan_B.shape}")
print(f"点間隔 res / ノイズ σ     : {res:.4f} / {noise:.4f}")
print(f"A-B 重なり率(幾何)       : {overlap:.2f}  → Trimmed ICP trim={TRIM:.2f}")
print(f"真の変換 R_gt             : 55 度回転, t_gt={t_gt.tolist()}")
print(f"実 op 回転誤差 (度)       : {real_err:.3f}")
print(f"実 op インライア RMSE     : {rmse:.4f}   (GT 整列の床 {floor_rmse:.4f})")

# ═══ 4) beat-null ═══
# null-A: 重心を合わせ、主軸(PCA)どうしを合わせる(ICP なし)
_, VA = pca_frame(scan_A)
_, VBm = pca_frame(scan_B_moved)
R_null = VA @ VBm.T                             # B_moved 主軸 → A 主軸
pca_err = rotation_error_deg(R_null, R_rec)

# null-B: 単位行列から始める ICP(大回転を跨げず局所解に固着)
Rid, tid, info_id = M.icp_point2point_3d(scan_B_moved, scan_A, iters=40, trim_ratio=TRIM)
icp_id_err = rotation_error_deg(_np(Rid), R_rec)

print(f"beat-null 回転誤差 (度)   : 実 op {real_err:.3f} / PCA主軸 {pca_err:.2f} / "
      f"単位行列ICP {icp_id_err:.2f}")

# ═══ GT 検証(判別的)═══
# (a) 実 op は数度以内で姿勢を復元(部分重なり ~4 割でも FPFH+ICP で締まる)
assert real_err < 4.0, f"実 op の回転誤差が大きすぎる: {real_err:.3f} 度"
# (b) インライア RMSE が GT 整列の床の水準(部分重なり故 res 程度が下限)
assert rmse < 1.8 * floor_rmse, \
    f"RMSE が床まで収束していない: {rmse:.4f} vs 床 {floor_rmse:.4f}"
# (c) 重なりが本当に部分的(全体一致ではない)ことを確認
assert 0.25 <= overlap <= 0.65, f"重なりが部分観測の範囲にない: {overlap:.2f}"
# beat-null: 両 null は部分重なりで大きく外し、実 op はそれを桁違いに下回る
assert pca_err > 15.0, f"PCA null が偶然当たってしまった: {pca_err:.2f} 度"
assert icp_id_err > 15.0, f"単位行列 ICP null が偶然当たってしまった: {icp_id_err:.2f} 度"
assert real_err < 0.25 * pca_err, \
    f"実 op が PCA null を十分下回っていない: {real_err:.3f} vs {pca_err:.2f}"
assert real_err < 0.25 * icp_id_err, \
    f"実 op が単位行列 ICP null を十分下回っていない: {real_err:.3f} vs {icp_id_err:.2f}"

print(f"PASS: 重なり {overlap:.0%} の部分スキャンを FPFH+ICP で登録。回転誤差 "
      f"{real_err:.2f}度 < 4度・RMSE {rmse:.4f} が床 {floor_rmse:.4f} 水準。"
      f"null(PCA {pca_err:.1f}度 / 単位行列ICP {icp_id_err:.1f}度)を桁違いに下回る")

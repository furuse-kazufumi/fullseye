# 事例: 2視点からの相対カメラ姿勢(SfM初期化)
#   2枚の画像で撮った同じシーンの対応点だけから、カメラがどれだけ動いたか
#   (回転と並進の向き)と、点群の3D位置を復元する。SfM/VOの出発点。
import numpy as np
import twoview

# --- 合成シーン: 既知の R,t,K で 3D 点を 2 台のカメラへ投影する ----------------
K = np.array([[800.0, 0, 320.0],
              [0, 800.0, 240.0],
              [0, 0, 1.0]])  # 共通の内部パラメータ(焦点距離800px, 主点(320,240))


def rot(axis, deg):
    """軸まわり deg 度の回転行列(Rodrigues)。"""
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    th = np.deg2rad(deg)
    Kx = np.array([[0, -axis[2], axis[1]],
                   [axis[2], 0, -axis[0]],
                   [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * (Kx @ Kx)


def rot_angle_deg(Ra, Rb):
    """2つの回転行列の角度差(度)。"""
    c = np.clip((np.trace(Ra.T @ Rb) - 1) / 2, -1, 1)
    return np.rad2deg(np.arccos(c))


R_true = rot([0.2, 1.0, 0.1], 18.0)        # 真のカメラ回転(18度)
t_true = np.array([1.0, 0.15, 0.1])        # 真の並進(単眼ではスケールは不定)

# 奥行きをばらけさせた非平面の3D点(共平面だと本質行列分解が退化するので避ける)
rng = np.random.default_rng(0)
X = []
while len(X) < 40:
    p = np.array([rng.uniform(-2, 2), rng.uniform(-2, 2), rng.uniform(4, 9)])
    if p[2] > 0.5 and (R_true @ p + t_true)[2] > 0.5:  # 両カメラの前方
        X.append(p)
X = np.array(X)

# P1 = K[I|0](基準カメラ), P2 = K[R|t](2台目)で画素へ投影
P1, P2 = twoview._projection_matrices(R_true, t_true, K, K)
h1 = (P1 @ np.hstack([X, np.ones((len(X), 1))]).T).T
h2 = (P2 @ np.hstack([X, np.ones((len(X), 1))]).T).T
pts1 = h1[:, :2] / h1[:, 2:3]              # 1枚目の観測画素
pts2 = h2[:, :2] / h2[:, 2:3]              # 2枚目の観測画素

# --- ここから復元(入力は pts1,pts2,K だけ。R,t,X は使わない) -----------------

# (1) 基礎行列 F を正規化8点法で推定 → エピポーラ拘束の残差(Sampson距離)を確認
F = twoview.fundamental_8point(pts1, pts2)
samp = twoview.sampson_distance(F, pts1, pts2)
print(f"[1] Sampson距離 max = {samp.max():.3e}  (エピポーラ拘束 x2^T F x1 = 0 の残差)")

# (2) K既知なので本質行列 E = K^T F K
E = twoview.essential_from_fundamental(F, K)
print(f"[2] 本質行列の特異値 = {np.round(np.linalg.svd(E)[1], 3)}  (理想は (1,1,0))")

# (3) recover_pose: E を分解し cheirality(全点が両カメラ前方)で一意な (R,t) を選ぶ
R_est, t_est, X_rec = twoview.recover_pose(pts1, pts2, K)

# --- GT検証: 回転角・並進方向・三角測量点 --------------------------------------
rot_err = rot_angle_deg(R_est, R_true)
u_est = t_est / np.linalg.norm(t_est)
u_true = t_true / np.linalg.norm(t_true)
t_dir_dot = float(np.dot(u_est, u_true))          # 1に近いほど並進方向が一致
t_dir_err_deg = np.rad2deg(np.arccos(np.clip(t_dir_dot, -1, 1)))

# 復元3Dは単位並進スケール(|t|=1)。真のスケール |t_true| を掛けて元の点群と比較。
X_rescaled = X_rec * np.linalg.norm(t_true)
pt_err = np.linalg.norm(X_rescaled - X, axis=1)   # 各点の3D復元誤差

print(f"[3] 回転誤差            = {rot_err:.4f} 度")
print(f"[3] 並進方向の一致 dot  = {t_dir_dot:.6f}  (= {t_dir_err_deg:.4f} 度ずれ)")
print(f"[4] 三角測量点の3D誤差  max = {pt_err.max():.3e}  mean = {pt_err.mean():.3e}")

# ノイズ無しの合成データなので、いずれもごく小さいはず
assert samp.max() < 1e-6,            f"Sampson残差が大きい: {samp.max()}"
assert rot_err < 0.5,               f"回転誤差が大きい: {rot_err} 度"
assert t_dir_dot > 0.999,           f"並進方向がずれている: dot={t_dir_dot}"
assert pt_err.max() < 1e-6,         f"三角測量点が元3Dから離れている: {pt_err.max()}"
print("OK: 相対姿勢(R,t方向)と三角測量点が真値に一致")
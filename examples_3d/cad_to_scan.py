"""事例: CADモデルをノイズ入り3Dスキャンに位置合わせ (registration).

工場でCAD設計データ(理想形状)と、実物をレーザースキャンした点群を突き合わせたい。
スキャンは (1) 未知の姿勢で置かれている (2) センサノイズが乗る。
初期姿勢の当てずっぽうを一切与えず、pipeline3d.register_pointclouds が
FPFH記述子+RANSACで大まかに合わせ、ICPでセンサノイズ床の水準まで締める
(ノイズ入りスキャンなので到達できるのはノイズ床であり、無ノイズの機械精度ではない)。

検証(GT): 既知の回転・並進を掛けて dst を作るので、推定回転と真の回転の角度差が測れる。
"""
import numpy as np
import pipeline3d as P


def rotation_matrix(axis, deg):
    """軸まわり deg 度の回転行列 (ロドリゲスの公式)。"""
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


def rotation_error_deg(R_est, R_gt):
    """2つの回転行列の間の測地距離(度)。相対回転の回転角 = 誤差。"""
    R_est = np.asarray(R_est)
    cos = (np.trace(R_est.T @ R_gt) - 1) / 2
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def cad_like_part(n=1000, seed=0):
    """CAD部品の代わりに「非対称な直方体(10×6×3)の表面」から点をサンプル。

    注意(重要): 完全な球は回転対称なので、どの回転で重ねても形が一致してしまい
    姿勢を一意に復元できない(登録が破綻する)。実際に球で試すと回転誤差が
    掛けた角度そのまま(=全く合わない)になる。CAD部品は普通、面・稜線・角という
    非対称な特徴を持つので、それを模した非対称ブロックを使う。
    """
    rng = np.random.default_rng(seed)
    dims = np.array([10.0, 6.0, 3.0])          # 3辺すべて異なる=非対称
    pts = np.empty((n, 3))
    for i in range(n):
        f = rng.integers(0, 6)                 # 6面のどれか
        u = rng.random(3) * dims               # 面上の一様点
        u[f // 2] = 0.0 if f % 2 == 0 else dims[f // 2]   # 該当軸を面に貼り付け
        pts[i] = u
    return pts


# --- 1) 合成データ生成: clean な CADモデル(src)と、姿勢ずれ+ノイズの scan(dst) ---
src = cad_like_part(n=1000, seed=0)            # CAD設計データ(理想形状の点群)
R_gt = rotation_matrix([0.3, 1.0, 0.2], 35.0)  # 実物の未知姿勢(真値)= 35度回転
t_gt = np.array([4.0, -2.0, 1.0])              # 実物の未知位置(真値)= 並進

scale = float(np.linalg.norm(src.max(0) - src.min(0)))   # 物体の対角長 ~ 12
noise = 0.01 * scale                            # スキャナノイズ = スケールの1%
rng = np.random.default_rng(42)
# dst = src を真の姿勢で置き直し、ガウスノイズを重畳(=ノイズ入り3Dスキャン)
scan = src @ R_gt.T + t_gt + rng.normal(0.0, noise, src.shape)

# --- 2) 登録: 初期推定なしで CAD(src) を scan(dst) に合わせる ---
R_est, t_est, rmse = P.register_pointclouds(src, scan)

# --- 3) GT検証: 回転誤差(度)とインライアRMSE ---
rerr = rotation_error_deg(R_est, R_gt)
print(f"物体スケール(対角長)     : {scale:.3f}")
print(f"注入ノイズ(標準偏差)     : {noise:.3f}  (スケールの1%)")
print(f"回転誤差 (度)             : {rerr:.3f}")
print(f"登録RMSE                  : {rmse:.4f}  (注入ノイズ {noise:.4f} と同水準なら成功)")

# GT: 姿勢が正しく復元できていれば回転誤差は小さく、RMSE は注入ノイズの水準まで
# 下がる(それ以上は下がらない=ノイズ床)。ノイズ床の 2 倍未満を要求することで
# 「大まかに合っただけ」や破綻(単位行列を返す等 ~35度)を判別的に弾く。
assert rerr < 2.0, f"回転誤差が大きすぎる: {rerr:.3f} 度"
assert rmse < 2.0 * noise, \
    f"RMSE がノイズ床まで収束していない: {rmse:.4f} vs ノイズ {noise:.4f}"
print(f"PASS: 回転誤差 {rerr:.2f}度 < 2度、RMSE {rmse:.4f} がノイズ床 {noise:.4f} の水準まで収束")

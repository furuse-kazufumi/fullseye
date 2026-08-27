"""事例: 手法を自動選択する点群登録 (registration).

点群登録には向き不向きがある。既に大体合っている(小さなズレ)なら ICP だけで速く正確に
締められる。逆に大きく回っている/離れているなら、初期推定なしで大まかに合わせる
FPFH+RANSAC を前段に噛ませないと ICP は局所解に落ちる。

pipeline3d.register_auto は **データ(2点群の最近傍距離)を見て** どちらの状況かを判定し、
近ければ "icp"、遠ければ "fpfh+icp" を自動で選ぶ。ユーザは手法を指定しなくてよい。
(進化計算が fitness で手法を勝手に選ぶのと同じ発想の、ルールベースの前身。)

検証(GT): 近接ケース・大回転ケースの2つを投げ、選ばれた手法と整列後RMSEを確認する。
"""
import numpy as np
from scipy.spatial import cKDTree
import pipeline3d as P


def rotation_matrix(axis, deg):
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


def alignment_rmse(src, dst, R, t):
    """推定姿勢で src を動かし、dst 最近傍までの距離のRMSE(=どれだけ重なったか)。"""
    R = np.asarray(R)
    t = np.asarray(t)
    moved = src @ R.T + t
    d, _ = cKDTree(dst).query(moved, k=1)
    return float(np.sqrt(np.mean(d ** 2)))


def cad_like_part(n=1000, seed=0):
    """非対称な直方体(10×6×3)の表面点。球は回転対称で登録不能なので使わない。"""
    rng = np.random.default_rng(seed)
    dims = np.array([10.0, 6.0, 3.0])
    pts = np.empty((n, 3))
    for i in range(n):
        f = rng.integers(0, 6)
        u = rng.random(3) * dims
        u[f // 2] = 0.0 if f % 2 == 0 else dims[f // 2]
        pts[i] = u
    return pts


src = cad_like_part(n=1000, seed=0)
scale = float(np.linalg.norm(src.max(0) - src.min(0)))
noise = 0.01 * scale
rng = np.random.default_rng(7)

# --- ケースA: 近接(小さなズレ)= 2度回転 + わずかな並進。ICP 単独で足りるはず ---
R_near = rotation_matrix([0, 0, 1], 2.0)
t_near = np.array([0.1, 0.1, 0.1])
dst_near = src @ R_near.T + t_near + rng.normal(0.0, noise, src.shape)
m_near, R1, t1 = P.register_auto(src, dst_near)
rmse_near = alignment_rmse(src, dst_near, R1, t1)

# --- ケースB: 大回転(遠い)= 50度回転 + 大きな並進。FPFH+ICP が必要 ---
R_far = rotation_matrix([0.3, 1.0, 0.2], 50.0)
t_far = np.array([3.0, -2.0, 1.0])
dst_far = src @ R_far.T + t_far + rng.normal(0.0, noise, src.shape)
m_far, R2, t2 = P.register_auto(src, dst_far)
rmse_far = alignment_rmse(src, dst_far, R2, t2)

print(f"物体スケール          : {scale:.3f}   ノイズ標準偏差: {noise:.3f}")
print(f"近接ケース  -> 選択手法: {m_near:8s}  整列RMSE: {rmse_near:.4f}")
print(f"大回転ケース-> 選択手法: {m_far:8s}  整列RMSE: {rmse_far:.4f}")

# GT: 近接は "icp"、大回転は "fpfh+icp" が自動選択され、どちらも整列(RMSE≒ノイズ水準)
assert m_near == "icp", f"近接ケースで想定外の手法: {m_near}"
assert m_far == "fpfh+icp", f"大回転ケースで想定外の手法: {m_far}"
assert rmse_near < 0.05 * scale, f"近接ケース整列失敗: RMSE={rmse_near:.4f}"
assert rmse_far < 0.05 * scale, f"大回転ケース整列失敗: RMSE={rmse_far:.4f}"
print("PASS: データに応じ手法を自動選択し、両ケースとも整列(RMSE < スケールの5%)")

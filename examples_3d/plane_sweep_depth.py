# 事例: 2視点プレーンスイープ・ステレオ深度
#   カメラ姿勢が既知の2枚から、画素ごとの奥行き(深度マップ)を作る。
#   奥行き候補を並べ、各候補で片方の画像をもう片方へ射影ワープし、
#   輝度が最も一致する奥行きを画素ごとに選ぶ(winner-take-all)。
import numpy as np
import plane_sweep

# --- 独立GTレンダラ: 各画素のrayを平面と交差させ、平面上のテクスチャをサンプル -----
# (plane_sweep 実装とは別モデルなので、GTは実装の焼き直しではない)


def rot(axis, deg):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    th = np.deg2rad(deg)
    Kx = np.array([[0, -axis[2], axis[1]],
                   [axis[2], 0, -axis[0]],
                   [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * (Kx @ Kx)


def texture(x, y):
    """平面上(x,y)の輝度。全域で勾配が非零・低周波(深度の一意性を担保)。"""
    return (np.sin(1.7 * x + 0.3) * np.cos(2.3 * y - 0.5)
            + 0.6 * np.sin(0.9 * x + 1.1 * y + 0.7)
            + 0.4 * np.cos(2.9 * x - 1.3 * y + 0.2)
            + 0.25 * np.sin(0.5 * x - 0.4 * y))


def render(K, R, t, normal, d0, shape):
    """カメラ P=K[R|t] で平面 n^T X = d0(基準系)を撮像。→ (画像, 真深度Z, 3D点)。"""
    h, w = shape
    Kinv = np.linalg.inv(K)
    C = -R.T @ t                                  # カメラ中心(基準系)
    yy, xx = np.mgrid[0:h, 0:w]
    p = np.stack([xx.ravel(), yy.ravel(), np.ones(xx.size)], axis=0)
    dir_ref = R.T @ (Kinv @ p)                     # 基準系でのray方向
    n = np.asarray(normal, float).reshape(3)
    s = (d0 - n @ C) / (n @ dir_ref)               # ray と平面の交点パラメータ
    Xp = C[:, None] + s[None, :] * dir_ref         # (3,N) 基準系の3D点
    img = texture(Xp[0] / d0, Xp[1] / d0).reshape(h, w)
    depth = Xp[2].reshape(h, w)                     # 基準系での深度Z(=GT)
    return img, depth, Xp.T.reshape(h, w, 3)


def visible_mask(K, R, t, X_ref, shape, margin=2.0):
    """refの3D点をsourceへ投影し画像内に落ちる画素(照合可能領域)のマスク。"""
    h, w = shape
    Xf = X_ref.reshape(-1, 3).T
    proj = K @ (R @ Xf + t.reshape(3, 1))
    z = proj[2]
    with np.errstate(invalid="ignore", divide="ignore"):
        u, v = proj[0] / z, proj[1] / z
    ok = (z > 1e-6) & (u >= margin) & (u <= w - 1 - margin) \
        & (v >= margin) & (v <= h - 1 - margin)
    return ok.reshape(h, w)


# --- 合成シーン: フロント平行平面(既知深度 d0=5.0) --------------------------
shape = (140, 180)
K = np.array([[500.0, 0, 90.0], [0, 500.0, 70.0], [0, 0, 1.0]])
R = rot([0.15, 1.0, 0.1], 5.0)                     # source の相対回転
t = np.array([0.14, 0.03, 0.02])                   # baseline(既知)
normal = np.array([0.0, 0.0, 1.0])                 # フロント平行(法線=光軸方向)
d0 = 5.0                                           # 真の平面距離

img_ref, depth_ref, X_ref = render(K, np.eye(3), np.zeros(3), normal, d0, shape)  # 基準カメラ
img_src, _, _ = render(K, R, t, normal, d0, shape)                                # source カメラ

# --- ここから深度推定(入力は 2枚 + K,R,t + 深度候補だけ) --------------------
# 逆深度等間隔で 0.5*d0 .. 1.8*d0 の候補を100本
inv = np.linspace(1.0 / (1.8 * d0), 1.0 / (0.5 * d0), 100)
cands = (1.0 / inv)[::-1].copy()

est = plane_sweep.plane_sweep_depth(img_ref, img_src, K, R, t, cands, window=1)

# --- GT検証: 照合可能な有効画素で相対誤差を測る -------------------------------
vis = visible_mask(K, R, t, X_ref, shape) & np.isfinite(est)
rel = np.abs(est[vis] - depth_ref[vis]) / depth_ref[vis]
median_rel = float(np.median(rel))
p90_rel = float(np.percentile(rel, 90))
cand_spacing = float(np.median(np.diff(np.sort(cands))))  # 離散化限界(系統誤差の下限)

print(f"真の深度 d0            = {d0}")
print(f"有効画素率(vis)        = {vis.mean():.2%}")
print(f"推定深度の中央値       = {np.median(est[vis]):.4f}")
print(f"相対誤差 median        = {median_rel:.4f}")
print(f"相対誤差 p90           = {p90_rel:.4f}")
print(f"候補間隔(離散化限界)  ≈ {cand_spacing / d0:.4f}")

# ノイズ無し・候補離散化のみが誤差要因。中央値/90%点とも数%以内のはず。
assert vis.mean() > 0.3,      f"照合可能領域が狭すぎる: {vis.mean()}"
assert median_rel < 0.02,     f"深度の相対誤差(中央値)が大きい: {median_rel}"
assert p90_rel < 0.03,        f"深度の相対誤差(p90)が大きい: {p90_rel}"
print("OK: 既知深度のフロント平行平面を相対誤差<2%(中央値)で復元")
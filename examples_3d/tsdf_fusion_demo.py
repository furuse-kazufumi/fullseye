# -*- coding: utf-8 -*-
"""事例: 複数の深度フレームを TSDF で融合し表面(ゼロ交差)を抽出する。

実問題: 1 台の深度カメラでノイズを含む観測を複数の向きから撮ると、各フレームは
物体の手前側しか見えず、しかも計測ノイズを含む。これらを 1 つの符号付き距離場
(TSDF)に重み付き平均で融合すると、(1) 物体全周の表面を復元でき、(2) 各観測の
ノイズが打ち消し合って、単一フレームより真の表面に近い点群が得られる。
ここでは半径既知の球を合成観測し、融合表面の半径誤差が単一フレームより小さいこと、
かつ抽出点が真の球面近傍に載ることを数値で検証する(視覚でなく assert)。

依存は numpy と fullseye の tsdf_fusion / visualhull のみ(cv2/torch/skimage 不使用)。
"""
import numpy as np

import tsdf_fusion            # 主モジュール: fuse() / extract_surface_points()
import visualhull            # look_at(eye, target, up) -> (R, t)  X_cam = R X + t


def render_sphere_depth(center, radius, R, t, K, H, W):
    """カメラ (R,t,K) から半径 radius の球を見た解析的な深度画像を作る。

    各画素の視線(カメラ原点発の単位ベクトル)と球の交点を 2 次方程式で解き、
    交点までの奥行き(perpendicular Z-depth)を返す。球に当たらない画素は 0(無効)。
    これが「真の物体を撮った深度センサ画像」の役割を果たす合成観測。
    """
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    Cc = R @ np.asarray(center, float) + np.asarray(t, float)      # 球中心をカメラ座標へ
    uu, vv = np.meshgrid(np.arange(W), np.arange(H))
    d = np.stack([(uu - cx) / fx, (vv - cy) / fy, np.ones_like(uu, float)], axis=-1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)                 # 単位光線方向
    b = (d * Cc).sum(-1)
    c = float(Cc @ Cc) - radius ** 2
    disc = b * b - c                                               # 判別式
    s_near = b - np.sqrt(np.clip(disc, 0.0, None))                 # 手前側の交点距離
    valid = (disc >= 0.0) & (s_near > 0.0)
    Zc = s_near * d[..., 2]                                        # 垂直方向の奥行き
    depth = np.zeros((H, W), dtype=np.float64)
    depth[valid] = Zc[valid]
    return depth


def fib_dirs(n):
    """フィボナッチ球で n 個のほぼ等方な単位方向(視点をまんべんなく配置)。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    ga = np.pi * (1.0 + 5.0 ** 0.5)
    th = ga * i
    return np.stack([np.sin(phi) * np.cos(th),
                     np.sin(phi) * np.sin(th),
                     np.cos(phi)], axis=1)


def median_radius_error(pts, center, radius):
    """抽出点の「中心からの距離」と真の半径との差の中央値(小さいほど正確)。"""
    r = np.linalg.norm(pts - np.asarray(center, float), axis=1)
    return float(np.median(np.abs(r - radius)))


# ── シーン設定: 半径 1.0 の球を 12 視点で囲む ─────────────────────────────
rng = np.random.default_rng(0)
center = np.array([0.17, -0.11, 0.08], float)   # 原点から少しずらす(判別性)
radius = 1.0
H = W = 100
focal = 130.0
K = np.array([[focal, 0.0, (W - 1) / 2.0],
              [0.0, focal, (H - 1) / 2.0],
              [0.0, 0.0, 1.0]], float)

n_views = 12
D = 4.0 * radius                                 # 撮影距離
eyes = center[None, :] + D * fib_dirs(n_views)

# 融合体積の範囲(球中心 ± 1.25R の立方体)と表面帯幅 trunc
m = 1.25 * radius
bounds = ((center[0] - m, center[0] + m),
          (center[1] - m, center[1] + m),
          (center[2] - m, center[2] + m))
res = 64
voxel = 2.0 * m / res
trunc = 4.0 * voxel                              # 表面帯 = 数 voxel

# 各視点の (深度, K, R, t) を作り、深度に独立なガウスノイズを混入(実センサ模擬)
noise_sigma = 0.5 * voxel                        # 計測ノイズの標準偏差
depths_clean, depths_noisy, Ks, Rs, ts = [], [], [], [], []
for eye in eyes:
    R, t = visualhull.look_at(eye, center, up=(0.0, 0.0, 1.0))
    dep = render_sphere_depth(center, radius, R, t, K, H, W)
    noisy = dep.copy()
    mask = dep > 0                               # 有効画素だけにノイズを乗せる
    noisy[mask] = dep[mask] + rng.normal(0.0, noise_sigma, size=int(mask.sum()))
    depths_clean.append(dep)
    depths_noisy.append(noisy)
    Ks.append(K); Rs.append(R); ts.append(t)

# ── (A) 単一フレーム(視点0 のノイズ深度のみ)で表面抽出 ──────────────────
tsdf_s, w_s = tsdf_fusion.fuse([depths_noisy[0]], [Ks[0]], [Rs[0]], [ts[0]],
                               bounds, res, trunc)
pts_single = tsdf_fusion.extract_surface_points(tsdf_s, w_s, bounds, res)

# ── (B) 全 12 フレームのノイズ深度を融合して表面抽出 ─────────────────────
tsdf_f, w_f = tsdf_fusion.fuse(depths_noisy, Ks, Rs, ts, bounds, res, trunc)
pts_fused = tsdf_fusion.extract_surface_points(tsdf_f, w_f, bounds, res)

err_single = median_radius_error(pts_single, center, radius)
err_fused = median_radius_error(pts_fused, center, radius)

# ── 数値 GT の出力 ──────────────────────────────────────────────────────
print("voxel size             =", round(voxel, 6))
print("depth noise sigma      =", round(noise_sigma, 6), "(= 0.5 voxel)")
print("single-frame  points   =", len(pts_single),
      " median radius err =", round(err_single, 6),
      "(", round(err_single / voxel, 3), "voxel )")
print("fused(12view) points   =", len(pts_fused),
      " median radius err =", round(err_fused, 6),
      "(", round(err_fused / voxel, 3), "voxel )")
print("improvement (single/fused) =", round(err_single / err_fused, 3), "x")

# GT-1: 融合表面の半径誤差は単一フレームより小さい(ノイズ平均化で頑健)
assert err_fused < err_single, \
    f"fused err {err_fused:.4g} should beat single-frame err {err_single:.4g}"
# GT-2: 抽出点は真の球面近傍に載る(中央値誤差 < voxel サイズ)
assert err_fused < voxel, \
    f"fused surface must lie within 1 voxel of the true sphere (err={err_fused:.4g}, voxel={voxel:.4g})"
# GT-3: 融合は全周を覆うので単一フレームより点数が多い(裏面の穴埋め)
assert len(pts_fused) > len(pts_single), \
    f"fusion should recover more surface ({len(pts_fused)} vs {len(pts_single)})"

print("OK: 融合表面は単一観測よりノイズに頑健で、真の球面近傍に載る")
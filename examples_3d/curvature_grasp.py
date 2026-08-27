# -*- coding: utf-8 -*-
"""事例: 主曲率・shape index による把持アフォーダンス (Fullseye curvature3d)。

実問題: ロボットハンドが物体表面のどこを掴めるかは「局所の曲がり方」で決まる。
  - 球のような両方向に凸な面 → 包み込み把持 (両主曲率が正)
  - 円柱の側面 → 一方向だけ曲がる(もう一方は真っ直ぐ)→ 軸に巻き付ける把持 (片方の主曲率が 0)
  - 鞍(サドル)面 → 反対向きに曲がる → 谷にフィンガーを差し込むピンチ (ガウス曲率 K<0)
各点で局所二次曲面をフィットして主曲率 k1>=k2 と Koenderink の shape index を求め、
この 3 タイプを数値で識別できることを検証する。
"""
import numpy as np
import curvature3d


# ---- 合成サーフェス生成 (tests と同じ閉形式サンプラ) ----
def fib_sphere(n, R):
    """Fibonacci 球で半径 R の球面を n 点。GT: k1=k2=1/R, K=1/R^2。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    return R * np.stack([np.sin(phi) * np.cos(th),
                         np.sin(phi) * np.sin(th), np.cos(phi)], axis=1)


def cylinder(n_th, n_z, R, H):
    """半径 R の円柱側面。GT: k1=1/R, k2=0, K=0。"""
    th = np.linspace(0, 2 * np.pi, n_th, endpoint=False)
    zz = np.linspace(-H / 2, H / 2, n_z)
    T, Z = np.meshgrid(th, zz)
    return np.stack([R * np.cos(T).ravel(), R * np.sin(T).ravel(), Z.ravel()], axis=1)


def saddle(n, a, L, seed=0):
    """双曲放物面 z=(x^2-y^2)/(2a)。原点で主曲率 +-1/a → K<0(鞍点)。"""
    rng = np.random.default_rng(seed)
    xy = rng.uniform(-L, L, size=(n, 2))
    x, y = xy[:, 0], xy[:, 1]
    return np.stack([x, y, (x ** 2 - y ** 2) / (2 * a)], axis=1)


# ============================================================
# 1. 球 (R=2): 両方向に凸 → 両主曲率が正、shape index ~ +1
# ============================================================
Rs = 2.0
sph = fib_sphere(700, Rs)
k1_s, k2_s = curvature3d.principal_curvatures(sph, k=25)
K_s = curvature3d.gaussian_curvature(sph, k=25)
si_s = curvature3d.shape_index(sph, k=25)
print("[球 R=2]  期待 k1=k2=1/R=0.5, K=1/R^2=0.25, shape_index=+1")
print(f"  median k1={np.median(k1_s):.3f}  k2={np.median(k2_s):.3f}"
      f"  K={np.median(K_s):.3f}  shape_index={np.median(si_s):.3f}")

# ============================================================
# 2. 円柱 (R=1.5): 一方向のみ凸 → 片方の主曲率が ~0、shape index ~ +0.5
# ============================================================
Rc = 1.5
cyl = cylinder(60, 40, Rc, H=6.0)
k1_c, k2_c = curvature3d.principal_curvatures(cyl, k=25)
K_c = curvature3d.gaussian_curvature(cyl, k=25)
si_c = curvature3d.shape_index(cyl, k=25)
print(f"[円柱 R=1.5] 期待 k1=1/R=0.667, k2=0, K=0, shape_index=+0.5")
print(f"  median k1={np.median(k1_c):.3f}  k2={np.median(k2_c):.3f}"
      f"  K={np.median(K_c):.3f}  shape_index={np.median(si_c):.3f}")

# ============================================================
# 3. 鞍点 (双曲放物面): 反対向きに曲がる → K<0、主曲率が異符号
# ============================================================
a = 2.0
sad = saddle(1200, a, L=1.5)
core = np.linalg.norm(sad[:, :2], axis=1) < 0.7          # 端は曲率が変化 → 中央部で評価
k1_d, k2_d = curvature3d.principal_curvatures(sad, k=30)
K_d = curvature3d.gaussian_curvature(sad, k=30)
si_d = curvature3d.shape_index(sad, k=30)
print(f"[鞍点]     期待 K<0, k1>0>k2 (異符号), shape_index~0")
print(f"  median K(core)={np.median(K_d[core]):.3f}"
      f"  k1={np.median(k1_d[core]):.3f}  k2={np.median(k2_d[core]):.3f}"
      f"  shape_index={np.median(si_d[core]):.3f}")

# ============================================================
# 4. (発展) 凹んだ椀 vs 膨らんだドーム: 向き付き法線で凹/凸を区別
#    掴む側(内側/外側)は局所情報だけでは決まらない → 視点由来の法線を渡す
# ============================================================
def bowl_dome(k, L=1.0, n=1500, seed=0):
    rng = np.random.default_rng(seed)
    xy = rng.uniform(-L, L, size=(n, 2))
    x, y = xy[:, 0], xy[:, 1]
    return np.stack([x, y, 0.5 * k * (x ** 2 + y ** 2)], axis=1)

bowl = bowl_dome(k=+0.8)                                  # 上に凹む椀 (cup)
dome = bowl_dome(k=-0.8)                                  # 上に膨らむ蓋 (cap)
up = np.tile([0.0, 0.0, 1.0], (1500, 1))                 # 視点(+z)由来の向き付き法線
core2 = lambda p: np.linalg.norm(p[:, :2], axis=1) < 0.6
si_bowl = curvature3d.shape_index(bowl, k=30, normals=up)
si_dome = curvature3d.shape_index(dome, k=30, normals=up)
print("[椀/ドーム] 向き付き法線(+z)で 凹=負 / 凸=正 に符号が分かれる")
print(f"  bowl(凹) shape_index={np.median(si_bowl[core2(bowl)]):.3f}"
      f"   dome(凸) shape_index={np.median(si_dome[core2(dome)]):.3f}")

# ================== GT 検証 ==================
# 球: 両主曲率が正 & 1/R 付近 & K>0 & shape_index~+1
assert np.median(k1_s) > 0 and np.median(k2_s) > 0                       # 両正
assert abs(np.median(k1_s) - 1 / Rs) < 0.15 / Rs                        # k1~1/R
assert abs(np.median(k2_s) - 1 / Rs) < 0.15 / Rs                        # k2~1/R
assert np.median(K_s) > 0 and np.median(si_s) > 0.9                     # K>0, s~+1
# 円柱: 片方 ~0, もう片方 1/R, K~0, shape_index~+0.5
assert abs(np.median(k1_c) - 1 / Rc) < 0.15 / Rc                        # k1~1/R
assert abs(np.median(k2_c)) < 0.15 / Rc                                 # k2~0 (真っ直ぐ方向)
assert abs(np.median(K_c)) < 0.10 / Rc ** 2                             # K~0
assert 0.3 < np.median(si_c) < 0.7                                      # s~+0.5
# 鞍点: K<0 かつ主曲率が異符号
assert np.median(K_d[core]) < 0                                        # ガウス曲率が負
assert np.median(k1_d[core]) > 0 > np.median(k2_d[core])               # k1>0>k2 (異符号)
assert abs(np.median(si_d[core])) < 0.35                              # shape_index~0
# 3 タイプが K の符号で判別できる: 球 K>0, 円柱 K~0, 鞍点 K<0
assert np.median(K_s) > 0.05 and abs(np.median(K_c)) < 0.05 and np.median(K_d[core]) < -0.05
# 向き付き法線: 椀(凹)は負, ドーム(凸)は正
assert np.median(si_bowl[core2(bowl)]) < -0.5 and np.median(si_dome[core2(dome)]) > 0.5

print("\nALL GT CHECKS PASSED")
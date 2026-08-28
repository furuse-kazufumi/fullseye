"""事例: 点群の間引き(voxel grid / farthest-point)で密度を均して軽くする (mesh_process).

LiDAR や深度カメラの点群は数十万〜数百万点あり、密度もムラだらけ(近い面は密・
遠い面は疎)。下流の ICP や特徴計算を回すには間引きが要る。Fullseye は 2 種を持つ:

  * ``pcl_filter.voxel_grid_downsample`` — 一辺 v の格子でセルごとに重心 1 点へ集約。
    密度を均一化し、元の表面から最大でも ~v の距離に必ず点が残る(カバレッジ保証)。
  * ``pcseg.farthest_point_sampling`` — 既選択から最も遠い点を貪欲に選ぶ。**点数を固定**
    しつつ最も widely に散らす(端点・角を残す)。認識前処理の定番。

検証(GT): 「元の点それぞれに、間引き後の最近傍がどれだけ近いか」= カバレッジを
ハウスドルフ距離で測る。voxel は理論上 ~v で抑えられ、**同数のランダム間引き**より
必ず良い(ランダムは疎な穴を作る)。これで beat-the-null。
"""
import numpy as np
import pcl_filter
import pcseg
import metrics3d as M


def wavy_surface_cloud(n=60000, seed=0):
    """波打つ矩形面 z=sin(x)cos(y) 上の点群(密度ムラを付けて現実の点群を模す)。"""
    rng = np.random.default_rng(seed)
    # 密度ムラ: 半分は狭い領域に集中させる(近距離の密な面を模す)
    x = np.concatenate([rng.uniform(-3, 3, n // 2), rng.uniform(-3, -1, n - n // 2)])
    y = np.concatenate([rng.uniform(-3, 3, n // 2), rng.uniform(-3, -1, n - n // 2)])
    z = np.sin(x) * np.cos(y)
    return np.stack([x, y, z], axis=1)


# --- 1) ムラのある密な点群 -------------------------------------------------
pts = wavy_surface_cloud(60000, seed=0)
n0 = len(pts)
diag = float(np.linalg.norm(pts.max(0) - pts.min(0)))

# --- 2) voxel grid downsample(セル辺 v)----------------------------------
v = 0.15
vg = pcl_filter.voxel_grid_downsample(pts, v)
nv = len(vg)

# --- 3) farthest-point sampling(点数を nv に合わせて公平に比較)-----------
fps_idx = pcseg.farthest_point_sampling(pts, nv, seed=0)
fp = pts[fps_idx]

# --- 4) ベースライン: 同数をランダムに間引く ------------------------------
rng = np.random.default_rng(1)
rand = pts[rng.choice(n0, size=nv, replace=False)]

# --- 5) GT: 元点群 → 間引き後 のハウスドルフ距離(=最悪カバレッジ)--------
h_vg = M.hausdorff_distance(pts, vg)
h_fp = M.hausdorff_distance(pts, fp)
h_rd = M.hausdorff_distance(pts, rand)
print(f"元の点数            : {n0}")
print(f"voxel(v={v}) 後点数 : {nv}  ({100*nv/n0:.1f}%)")
print(f"voxel カバレッジ距離: {h_vg:.4f}   (理論上限 ~v*sqrt3 = {v*np.sqrt(3):.3f})")
print(f"FPS   カバレッジ距離: {h_fp:.4f}")
print(f"乱択  カバレッジ距離: {h_rd:.4f}   (同数を無作為に残しただけ)")

# GT: (a) 大幅に間引けている (b) voxel は理論上限 v*sqrt3 を超えない (c) voxel も FPS も
# ランダム間引きより明確に良い(穴を作らない)=間引きが均一カバレッジを保っている。
assert nv < n0 * 0.5, f"間引けていない: {nv}/{n0}"
assert h_vg <= v * np.sqrt(3) + 1e-9, f"voxel カバレッジが理論上限超過: {h_vg:.4f}"
assert h_vg < 0.7 * h_rd, f"voxel が乱択より優位でない: {h_vg:.4f} vs {h_rd:.4f}"
assert h_fp < h_rd, f"FPS が乱択より優位でない: {h_fp:.4f} vs {h_rd:.4f}"
print(f"PASS: {n0}->{nv}点。voxel {h_vg:.3f}(<= {v*np.sqrt(3):.3f})・FPS {h_fp:.3f} "
      f"がいずれも乱択 {h_rd:.3f} より均一にカバー")

"""事例: メッシュの間引き(QEM decimation)で形を保ったまま面数を減らす (mesh_process).

DL してきた高精細メッシュ(例: Stanford Dragon は 87 万面)は、そのままでは重くて
レンダも衝突判定も回らない。``meshrepair.decimate_qem``(Garland-Heckbert の
二次誤差計量)は、平らな所ほど積極的に、曲率の高い所は温存して辺を潰し、
少ない面で元の形を近似する。

検証(GT): 元メッシュの頂点群から見た「間引き後メッシュのハウスドルフ距離」を
形状保存の指標にする。QEM は誤差最小の位置へ潰すので、**同じ枚数だけ頂点を
ランダムに間引いた素朴なベースライン**より必ず小さいはず。これで「ただ間引いた
だけ」と「形を残して間引いた」を判別的に弾く(beat-the-null)。
"""
import numpy as np
import sdf_ops
import render3d
import meshrepair
import metrics3d as M


def bumpy_blob(res=64):
    """有機的な非凸ブロブの密メッシュを作る(球 SDF を正弦で波打たせる)。"""
    bounds = ((-1.3, 1.3), (-1.3, 1.3), (-1.3, 1.3))
    coords, _ = sdf_ops.grid_coords(bounds, res)
    r = np.linalg.norm(coords, axis=-1)
    x, y, z = coords[..., 0], coords[..., 1], coords[..., 2]
    bumps = 0.12 * np.sin(3 * x) * np.sin(3 * y) * np.sin(3 * z)   # 表面の凹凸=曲率変化
    sdf = r - (0.9 + bumps)
    return render3d.marching_cubes(sdf, level=0.0)


# --- 1) 密メッシュを用意 ---------------------------------------------------
V, F = bumpy_blob(res=64)
n0 = len(F)
scale = float(np.linalg.norm(V.max(0) - V.min(0)))     # 形の対角長(正規化用)

# --- 2) QEM で目標 30% 面数へ間引く ---------------------------------------
target = int(n0 * 0.30)
Vd, Fd = meshrepair.decimate_qem(V, F, target)
n1 = len(Fd)

# --- 3) ランダム頂点間引きのベースライン(同じ頂点数だけ無作為に残す)------
rng = np.random.default_rng(0)
keep = rng.choice(len(V), size=len(Vd), replace=False)
Vr = V[keep]

# --- 4) GT: 元頂点群に対する形状保存(ハウスドルフ距離, 対角長で正規化)-----
h_qem = M.hausdorff_distance(V, Vd) / scale
h_rnd = M.hausdorff_distance(V, Vr) / scale
print(f"元の面数              : {n0}")
print(f"間引き後 面数         : {n1}  (目標 {target}, {100*n1/n0:.0f}%)")
print(f"QEM  ハウスドルフ/対角: {h_qem:.4f}")
print(f"乱択 ハウスドルフ/対角: {h_rnd:.4f}  (同数の頂点を無作為に残しただけ)")

# GT: 面数は確かに減り(半分未満)、QEM は形を残す(対角の 5% 未満)。かつ乱択
# ベースラインより明確に良い(=単に点を捨てたのではなく形を最適化して間引いた)。
assert n1 < n0 * 0.5, f"面数が十分減っていない: {n1}/{n0}"
assert h_qem < 0.05, f"QEM が形を保てていない: {h_qem:.4f}"
assert h_qem < 0.6 * h_rnd, \
    f"QEM が乱択間引きに対して優位でない: {h_qem:.4f} vs {h_rnd:.4f}"
print(f"PASS: {n0}->{n1}面 ({100*n1/n0:.0f}%) で形状誤差 {h_qem:.4f} "
      f"< 乱択 {h_rnd:.4f}(QEM が形を残して間引けている)")

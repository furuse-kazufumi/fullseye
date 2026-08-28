"""事例: メッシュの間引き(QEM decimation)で形を保ったまま面数を減らす (mesh_process).

DL してきた高精細メッシュ(例: Stanford Dragon は 87 万面)は、そのままでは重くて
レンダも衝突判定も回らない。``meshrepair.decimate_qem``(Garland-Heckbert の
二次誤差計量)は、平らな所ほど積極的に、曲率の高い所は温存して辺を潰し、
少ない面で**穴のない**表面として元の形を近似する。

検証(GT): 元の表面を密にサンプルした点群を、間引き後メッシュの表面がどれだけ
カバーできているか(ハウスドルフ距離)で測る。**同じ枚数だけ面を無作為に残した
素朴なベースライン**は穴だらけになり、穴に落ちた元表面の点が遠くなって距離が跳ねる。
QEM はそれより明確に小さい(=形を残して間引けている)。これで beat-the-null。
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
    return render3d.marching_cubes(r - (0.9 + bumps), level=0.0)


def sample_surface(V, F, n, seed=0):
    """三角形の面積に比例して表面上に n 点を一様サンプル(重心座標)。"""
    rng = np.random.default_rng(seed)
    tri = V[F]                                        # (M,3,3)
    ab, ac = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    area = 0.5 * np.linalg.norm(np.cross(ab, ac), axis=1)
    p = area / area.sum()
    idx = rng.choice(len(F), size=n, p=p)
    u = rng.random((n, 1)); v = rng.random((n, 1))
    over = (u + v) > 1.0                              # 三角形内へ折り返す
    u[over], v[over] = 1 - u[over], 1 - v[over]
    return tri[idx, 0] + u * (tri[idx, 1] - tri[idx, 0]) + v * (tri[idx, 2] - tri[idx, 0])


# --- 1) 密メッシュを用意 ---------------------------------------------------
V, F = bumpy_blob(res=64)
n0 = len(F)
scale = float(np.linalg.norm(V.max(0) - V.min(0)))     # 形の対角長(正規化用)
orig_pts = sample_surface(V, F, 20000, seed=1)         # 元の「真の表面」

# --- 2) QEM で目標 30% 面数へ間引く ---------------------------------------
target = int(n0 * 0.30)
Vd, Fd = meshrepair.decimate_qem(V, F, target)
n1 = len(Fd)

# --- 3) ベースライン: 同じ面数だけ面を無作為に残す(=穴あきメッシュ)-------
rng = np.random.default_rng(0)
Fr = F[rng.choice(n0, size=n1, replace=False)]

# --- 4) GT: 元表面点 → 間引き後表面 のハウスドルフ距離(対角長で正規化)----
h_qem = M.hausdorff_distance(orig_pts, sample_surface(Vd, Fd, 20000, seed=2)) / scale
h_rnd = M.hausdorff_distance(orig_pts, sample_surface(V, Fr, 20000, seed=3)) / scale
print(f"元の面数              : {n0}")
print(f"間引き後 面数         : {n1}  (目標 {target}, {100*n1/n0:.0f}%)")
print(f"QEM  ハウスドルフ/対角: {h_qem:.4f}")
print(f"乱択 ハウスドルフ/対角: {h_rnd:.4f}  (同数の面を無作為に残した穴あき)")

# GT: 面数は半分未満に減り、QEM は形を残す(対角の 5% 未満)。かつ穴あきベースライン
# より明確に良い(穴が無いので最悪点距離が跳ねない)=形を保って間引けている。
assert n1 < n0 * 0.5, f"面数が十分減っていない: {n1}/{n0}"
assert h_qem < 0.05, f"QEM が形を保てていない: {h_qem:.4f}"
assert h_qem < 0.5 * h_rnd, \
    f"QEM が穴あきベースラインに対して優位でない: {h_qem:.4f} vs {h_rnd:.4f}"
print(f"PASS: {n0}->{n1}面 ({100*n1/n0:.0f}%) で形状誤差 {h_qem:.4f} "
      f"<< 穴あき {h_rnd:.4f}(QEM が穴なく形を残して間引けている)")

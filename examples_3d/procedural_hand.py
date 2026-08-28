"""事例: 手続き的に「手全体の骨格」をSDFで組み上げ、構造を検証する (modeling).

CADや計測に頼らず、解剖の知識だけから 3D モデルを作れると、教材・デモ・合成データが
自前で用意できる。ここでは手の 27 骨(手根骨8・中手骨5・指骨14)を **カプセルSDF**
(``sdf_ops`` の球SDF + 線分距離)で配置し、``render3d.marching_cubes`` で 1 枚の
メッシュに抜く。指は +y、手のひら法線 +z、親指は +x 側。

検証(GT): 出来た形が本当に「手」か? 占有ボクセルの構造で判別する。
  * 指先側(y上端 22%)の帯を横切る**連結成分の数 = 到達している指の本数 >= 4**。
  * 指方向(y)が厚み(z)より細長い(elongation)。
同じ体積の**単一球**を null として同じ計測をすると指の本数は 1 にしかならない。
「手 >= 4 本 / 球 = 1 本」で、blob ではなく手の骨格になっていることを判別的に示す。
"""
import numpy as np
from scipy import ndimage
import sdf_ops
import render3d


def capsule_sdf(coords, a, b, r):
    """線分 [a,b] からの距離 - r(=カプセルの符号付き距離)。"""
    a = np.asarray(a, float); b = np.asarray(b, float)
    ab = b - a; ap = coords - a
    t = np.clip((ap @ ab) / (float(ab @ ab) or 1e-9), 0.0, 1.0)[..., None]
    return np.linalg.norm(coords - (a + t * ab), axis=-1) - r


def build_hand_bones():
    """27 骨 + 関節ノブを ('cap'|'sph', ...) のリストで返す(指 +y, 親指 +x)。"""
    fingers = [("index", 0.055, 0.115, 0.235), ("middle", 0.018, 0.040, 0.265),
               ("ring", -0.018, -0.040, 0.240), ("little", -0.055, -0.120, 0.190)]
    WY, KY, GAP = -0.055, 0.300, 0.010
    bones, rng = [], np.random.RandomState(3)
    # 手根骨 8(2列のコンパクトな塊)
    for i in range(8):
        row = i // 4
        cx = -0.060 + (i % 4) * 0.040 + (0.008 if row else -0.008)
        cy = WY - 0.110 + row * 0.040
        bones.append(("sph", (cx, cy, (rng.rand() - 0.5) * 0.015), 0.024 - 0.002 * (i % 3)))
    # 中手骨 + 指骨(関節ノブつき)
    for _, wx, kx, flen in fingers:
        k = np.array([kx, KY, 0.010])
        bones.append(("cap", np.array([wx, WY, 0.0]), k, 0.019))
        bones.append(("sph", tuple(k), 0.023))
        cur, dirx = k.copy(), kx * 0.15
        for j, (fr, rad) in enumerate(zip([0.45, 0.33, 0.22], [0.0150, 0.0130, 0.0110])):
            nxt = cur + np.array([dirx * (j + 1), flen * fr, -0.012 * (j + 1)])
            bones.append(("cap", cur + [0, GAP, 0], nxt, rad))
            if j < 2:
                bones.append(("sph", tuple(nxt), rad + 0.004))
            cur = nxt
    # 親指(中手骨 + 2 指骨、外+下へ)
    tw = np.array([0.085, WY + 0.02, 0.015])
    t1, t2, t3 = (np.array(p) for p in ([0.235, 0.055, 0.045],
                                        [0.335, 0.150, 0.060], [0.405, 0.220, 0.065]))
    bones += [("cap", tw, t1, 0.024), ("sph", tuple(t1), 0.021),
              ("cap", t1 + [0, GAP, 0], t2, 0.017), ("sph", tuple(t2), 0.018),
              ("cap", t2 + [0, GAP, 0], t3, 0.014)]
    return bones


BOUNDS = ((-0.24, 0.48), (-0.20, 0.60), (-0.12, 0.14))
RES = (150, 170, 60)


def eval_sdf(bones):
    """全骨の SDF を格子上で union(min)して符号付き距離場を返す。"""
    coords, _ = sdf_ops.grid_coords(BOUNDS, RES)
    sdf = np.full(coords.shape[:-1], 1e9)
    for kind, *r in bones:
        d = sdf_ops.sphere_sdf(coords, r[0], r[1]) if kind == "sph" \
            else capsule_sdf(coords, r[0], r[1], r[2])
        sdf = np.minimum(sdf, d)
    return coords, sdf


def fingertip_band_count(occ):
    """占有の y 上端 22% の帯を横切る連結成分数(=そこへ到達している指の本数)。"""
    idx = np.argwhere(occ)
    ext_y = idx[:, 1].max() - idx[:, 1].min() + 1
    yband = idx[:, 1].max() - int(0.22 * ext_y)
    slab = np.zeros_like(occ); slab[:, yband:, :] = occ[:, yband:, :]
    _, n = ndimage.label(slab)
    return n


# --- 1) 手の骨を組み、SDF → メッシュ --------------------------------------
bones = build_hand_bones()
n_bone_prims = sum(1 for b in bones if b[0] == "cap") + 8   # 中手/指骨カプセル + 手根骨8
coords, sdf = eval_sdf(bones)
occ = sdf < 0.0
V, F = render3d.marching_cubes(sdf, level=0.0)
ext = np.ptp(np.argwhere(occ), axis=0) + 1                            # (x,y,z) voxel 範囲
elong = ext[1] / ext[2]
fingers = fingertip_band_count(occ)
print(f"配置した骨(カプセル+手根骨): {n_bone_prims}  (解剖学的な 27 骨)")
print(f"メッシュ                    : V{V.shape} F{F.shape}")
print(f"占有 範囲(x,y,z voxel)      : {ext.tolist()}  細長さ y/z = {elong:.2f}")
print(f"指先バンドの本数            : {fingers}")

# --- 2) null: 同体積の単一球で同じ計測(手の構造が無い)--------------------
R = (3 / (4 * np.pi) * occ.sum()) ** (1 / 3)
c = coords.reshape(-1, 3).mean(0)
occ_null = sdf_ops.sphere_sdf(coords, c, R) < 0.0
fingers_null = fingertip_band_count(occ_null)
ext_null = np.ptp(np.argwhere(occ_null), axis=0) + 1
print(f"null 球: 指先バンド本数 {fingers_null} / 細長さ {ext_null[1] / ext_null[2]:.2f}")

# GT: メッシュが十分な規模で生成され、指先に 4 本以上到達し(=四指)、細長い。
# 同体積の球 null は指が 1 本(=構造が無い)。手 >= 4 と 球 = 1 で判別的。
assert len(V) > 3000 and len(F) > 3000, f"メッシュが小さすぎる: V{V.shape} F{F.shape}"
assert fingers >= 4, f"指先に届く本数が四指に満たない: {fingers}"
assert elong > 3.5, f"手にしては細長くない: {elong:.2f}"
assert fingers_null <= 1, f"null 球が構造を持ってしまった: {fingers_null}"
assert fingers > fingers_null, "手が null 球より指の構造を持っていない"
print(f"PASS: 27 骨のSDFから V{len(V)}/F{len(F)} のメッシュ。指先 {fingers} 本(>=四指)"
      f"・細長さ {elong:.2f} = 手の骨格(球 null は {fingers_null} 本で構造なし)")

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""(題は最後に書き直す)

(仮の docstring。実行後に実測値で書き直す)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

L3 = fs.ledger          # 3-D op の公開経路(ファサード fs.<名> には多くが無い)

# --- 群落の諸元(すべて設計値 = 真値)---------------------------------------- #
PLOT = 2.25             # 区画の一辺 [m]。**周期境界**(縁の効果を消すため)
ROW = 0.75              # 条間 [m]
IN_ROW = 0.25           # 株間 [m]
LEAF_L = 0.85           # 葉身長 [m](中肋に沿った弧長)
LEAF_W = 0.085          # 最大葉幅 [m]
BETA_DEG = 70.0         # 着生角(水平から)[度]
KAPPA = 1.1             # 中肋の曲率 [rad/m](先へ行くほど寝る)
STEM_R = 0.011          # 稈半径 [m]
LEAF_Z0, LEAF_Z1 = 0.30, 1.40    # 葉の着生高さの範囲 [m]
NESTED_MAX = 24         # 生育の上限葉数。葉 k の着生高さは n_leaf に依らない
N_LEAF = 7              # 1 株の葉数(基準条件)
CELL = 0.010            # カバー格子のセル [m](= 1 cm)
CELL_FINE = 0.005       # 図と参照用の細かいセル [m]
SEED = 20260907

PLOT_AREA = PLOT * PLOT


# --------------------------------------------------------------------------- #
# 0. 葉の閉形式 —— 面積・傾き・到達距離がすべて式で出る                        #
# --------------------------------------------------------------------------- #
# 中肋を「水平からの角 alpha(u) = beta - kappa*u」で走る単位速度の曲線にすると、
#   水平前進 Ix(u) = (sin beta - sin(beta - kappa u)) / kappa
#   高さ    Iz(u) = (cos(beta - kappa u) - cos beta) / kappa
# となり、幅 w(u) の帯(横方向は水平で中肋に直交)を張った面は
#   dA = (w/2)|C'| du dt = (w/2) du dt  (|C'| = 1)
# なので **面積 = ∫ w(u) du**。w(u) = W sqrt(4q(1-q)), q=u/L と取れば
#   面積 = W L ∫ sqrt(4q(1-q)) dq = pi/4 * L * W   —— 楕円と同じ閉形式。
# 法線は n = (-sin a cos phi, -sin a sin phi, cos a) なので |n.z| = |cos alpha(u)|。

def ix_of(u, beta, kappa):
    """中肋の水平前進 [m](閉形式)。"""
    return (np.sin(beta) - np.sin(beta - kappa * u)) / kappa


def iz_of(u, beta, kappa):
    """中肋の高さ [m](閉形式)。"""
    return (np.cos(beta - kappa * u) - np.cos(beta)) / kappa


def width_of(u, leaf_len, leaf_w):
    """葉幅 [m]。``w(u) = W sqrt(4q(1-q))``(楕円形の葉身)。"""
    q = np.clip(u / leaf_len, 0.0, 1.0)
    return leaf_w * np.sqrt(np.maximum(4.0 * q * (1.0 - q), 0.0))


def leaf_area(leaf_len, leaf_w):
    """片面葉面積 [m^2] の**閉形式** = pi/4 * L * W。"""
    return 0.25 * np.pi * leaf_len * leaf_w


_QN = 512                                     # 1 葉あたりの求積点数


def leaf_projection(beta, kappa, leaf_len, leaf_w, phi, direction):
    """葉 1 枚の ``∫ w |n.b| du`` [m^2](向き ``b`` への投影面積)。**求積は 1 次元**。"""
    u = (np.arange(_QN) + 0.5) * (leaf_len / _QN)
    a = beta - kappa * u
    w = width_of(u, leaf_len, leaf_w)
    bx, by, bz = direction
    nb = -np.sin(a) * (bx * np.cos(phi) + by * np.sin(phi)) + np.cos(a) * bz
    return float(np.sum(w * np.abs(nb)) * (leaf_len / _QN))


# --------------------------------------------------------------------------- #
# 1. 群落を作る —— 真値は「撒いた葉の設計値の一覧」                             #
# --------------------------------------------------------------------------- #
def make_canopy(n_leaf=N_LEAF, row=ROW, in_row=IN_ROW, beta_deg=BETA_DEG,
                kappa=KAPPA, leaf_len=LEAF_L, leaf_w=LEAF_W, seed=SEED,
                distichous=True, bend_deg=0.0):
    """区画いっぱいの群落を作る。返るのは**葉 1 枚ごとの設計値**。

    株は条(row)に沿って並べ、葉は互生(distichous = 180 度おき)で着ける ——
    これが**株内クランピング**の源で、この PoC の主役。``distichous=False`` に
    すると葉の方位を一様乱数にする(対照群: 株はあるが葉は方向を揃えない)。

    ★葉 k の着生高さは :data:`NESTED_MAX` で決めるので、``n_leaf`` を増やした
    群落は前の群落を**そのまま含む**(下から上へ葉が増える = 生育)。これを
    しないと葉数を変えるたびに別の群落になり、植被率の曲線が単調でなくなって
    「崖」を測れない(2026-09-07 に一度そうなった)。

    ``bend_deg`` は風で葉が寝る量 [度]。**葉面積は 1 mm^2 も変わらない**ので、
    「面積が変わっていないのに推定値が動く」を作る道具になる。
    """
    rng = np.random.default_rng(seed)
    n_row = max(1, int(round(PLOT / row)))
    n_in = max(1, int(round(PLOT / in_row)))
    xs = (np.arange(n_row) + 0.5) * (PLOT / n_row)
    ys = (np.arange(n_in) + 0.5) * (PLOT / n_in)
    px, py = np.meshgrid(xs, ys, indexing="ij")
    px = px.ravel() + rng.normal(0.0, 0.02, px.size)
    py = py.ravel() + rng.normal(0.0, 0.02, py.size)
    n_plant = px.size

    base, phi, beta, kap, ll, ww, plant = [], [], [], [], [], [], []
    for p in range(n_plant):
        phi0 = rng.uniform(0.0, 2.0 * np.pi)
        for k in range(n_leaf):
            frac = (k + 0.5) / n_leaf
            z0 = LEAF_Z0 + frac * (LEAF_Z1 - LEAF_Z0)
            if distichous:
                ang = phi0 + k * np.pi + rng.normal(0.0, np.radians(12.0))
            else:
                ang = rng.uniform(0.0, 2.0 * np.pi)
            base.append((px[p], py[p], z0))
            phi.append(ang)
            # 上位葉ほど立つ(実測される垂直勾配)。風はここを一律に寝かせる。
            beta.append(np.radians(beta_deg - bend_deg + 6.0 * (frac - 0.5))
                        + rng.normal(0.0, np.radians(5.0)))
            kap.append(kappa * rng.uniform(0.88, 1.12))
            ll.append(leaf_len * rng.uniform(0.85, 1.15))
            ww.append(leaf_w * rng.uniform(0.85, 1.15))
            plant.append(p)

    can = {"base": np.asarray(base, np.float64), "phi": np.asarray(phi),
           "beta": np.asarray(beta), "kappa": np.asarray(kap),
           "L": np.asarray(ll), "W": np.asarray(ww),
           "plant": np.asarray(plant, np.int32),
           "n_plant": n_plant, "n_leaf": n_leaf,
           "stem_top": np.stack([px, py, np.full(n_plant, STEM_H)], 1),
           "stem_base": np.stack([px, py, np.zeros(n_plant)], 1)}
    can["area"] = leaf_area(can["L"], can["W"])
    can["lai"] = float(can["area"].sum() / PLOT_AREA)
    can["smax"] = ix_of(can["L"], can["beta"], can["kappa"])
    # 稈の側面積 = 2 pi r h(茎は葉ではない = LAI には入らない)
    can["stem_area"] = 2.0 * np.pi * STEM_R * STEM_H * n_plant / PLOT_AREA
    can["height"] = float(np.max(can["base"][:, 2]
                                 + iz_of(np.minimum(can["beta"] / can["kappa"], can["L"]),
                                         can["beta"], can["kappa"])))
    return can


def canopy_G(can, direction=(0.0, 0.0, 1.0)):
    """群落の投影係数 G(b) = 葉面積あたりの投影面積(**閉形式の求積**)。

    天頂方向 ``b=(0,0,1)`` なら Beer-Lambert の消光係数 k = G(0) そのもの。
    """
    tot = 0.0
    for i in range(can["L"].size):
        tot += leaf_projection(can["beta"][i], can["kappa"][i], can["L"][i],
                               can["W"][i], can["phi"][i], direction)
    return float(tot / can["area"].sum())


def canopy_G_zenith(can, theta, n_az=8):
    """天頂角 ``theta`` [rad] の G(theta)(方位について平均)。"""
    out = 0.0
    for j in range(n_az):
        az = 2.0 * np.pi * j / n_az
        b = (np.sin(theta) * np.cos(az), np.sin(theta) * np.sin(az), np.cos(theta))
        out += canopy_G(can, b)
    return out / n_az


# --------------------------------------------------------------------------- #
# 2. 上から見る —— 解析的な高さ場をそのまま z-buffer にする                     #
# --------------------------------------------------------------------------- #
def canopy_buffers(can, cell=CELL, with_stem=True):
    """天頂から見た**厳密な**バッファ群を返す(点サンプリングを介さない)。

    帯の投影は葉の局所座標 ``(s, t)`` で ``s in [0, smax]`` かつ
    ``|t| <= w(u(s))/2`` と書ける。``s -> u`` は
    ``u = (beta - arcsin(sin beta - kappa s)) / kappa`` と**逆にも解ける**ので、
    セル中心が葉の下にあるかは 1 回の代入で決まる。点を撒いて塗るより速く、
    しかも**偏りが無い**(点密度で太らない)。

    返り値の dict:
      ``top`` 最上面の高さ [m] / ``nz`` その面の |n.z| / ``lid`` 最上面の葉 index /
      ``layer`` そのセルを覆う葉の**枚数**(重なりの数)/ ``cell`` セル辺長。
    """
    n = int(round(PLOT / cell))
    top = np.full((n, n), -1.0e9)
    nzb = np.zeros((n, n))
    lid = np.full((n, n), -1, np.int32)
    layer = np.zeros(n * n, np.int64)

    b = can["base"]
    for i in range(can["L"].size):
        bx, by, bz = b[i]
        phi, beta, kap = can["phi"][i], can["beta"][i], can["kappa"][i]
        ll, ww, smax = can["L"][i], can["W"][i], can["smax"][i]
        cp, sp = np.cos(phi), np.sin(phi)
        pad = 0.5 * ww + cell
        x0, x1 = min(bx, bx + smax * cp) - pad, max(bx, bx + smax * cp) + pad
        y0, y1 = min(by, by + smax * sp) - pad, max(by, by + smax * sp) + pad
        i0, i1 = int(np.floor(x0 / cell)), int(np.ceil(x1 / cell)) + 1
        j0, j1 = int(np.floor(y0 / cell)), int(np.ceil(y1 / cell)) + 1
        gx = (np.arange(i0, i1) + 0.5) * cell
        gy = (np.arange(j0, j1) + 0.5) * cell
        dx = gx[None, :] - bx
        dy = gy[:, None] - by
        s = dx * cp + dy * sp
        t = -dx * sp + dy * cp
        arg = np.sin(beta) - kap * s
        ok = (s >= 0.0) & (s <= smax) & (np.abs(arg) <= 1.0)
        u = np.where(ok, (beta - np.arcsin(np.clip(arg, -1.0, 1.0))) / kap, 0.0)
        inside = ok & (np.abs(t) <= 0.5 * width_of(u, ll, ww))
        if not inside.any():
            continue
        alpha = beta - kap * u
        zz = bz + iz_of(u, beta, kap)
        rr = np.mod(np.arange(j0, j1), n)[:, None] + np.zeros((1, i1 - i0), np.int64)
        cc = np.mod(np.arange(i0, i1), n)[None, :] + np.zeros((j1 - j0, 1), np.int64)
        flat = (rr * n + cc)[inside]
        layer += np.bincount(flat, minlength=n * n)
        r, c = flat // n, flat % n
        z = zz[inside]
        better = z > top[r, c]
        rb, cb = r[better], c[better]
        top[rb, cb] = z[better]
        nzb[rb, cb] = np.abs(np.cos(alpha))[inside][better]
        lid[rb, cb] = i

    if with_stem:
        # 稈は鉛直の円柱 = 上から見れば半径 r の円板。**葉ではないので LAI には
        # 入らないが、カバー率には入る**(PAI と LAI の違いの実体)。
        for p in range(can["n_plant"]):
            sx, sy = can["stem_base"][p, 0], can["stem_base"][p, 1]
            i0 = int(np.floor((sx - STEM_R) / cell))
            i1 = int(np.ceil((sx + STEM_R) / cell)) + 1
            j0 = int(np.floor((sy - STEM_R) / cell))
            j1 = int(np.ceil((sy + STEM_R) / cell)) + 1
            gx = (np.arange(i0, i1) + 0.5) * cell
            gy = (np.arange(j0, j1) + 0.5) * cell
            m = ((gx[None, :] - sx) ** 2 + (gy[:, None] - sy) ** 2) <= STEM_R ** 2
            if not m.any():
                continue
            rr = np.mod(np.arange(j0, j1), n)[:, None] + np.zeros((1, i1 - i0), np.int64)
            cc = np.mod(np.arange(i0, i1), n)[None, :] + np.zeros((j1 - j0, 1), np.int64)
            flat = (rr * n + cc)[m]
            layer += np.bincount(flat, minlength=n * n)
            r, c = flat // n, flat % n
            better = STEM_H > top[r, c]
            top[r[better], c[better]] = STEM_H
            nzb[r[better], c[better]] = 1.0        # 円板として扱う(先端の切り口)

    return {"top": top, "nz": nzb, "lid": lid,
            "layer": layer.reshape(n, n).astype(np.float64), "cell": cell, "n": n}


def cover_of(buf):
    """植被率(セル中心が植物に覆われている割合)。"""
    return float(np.mean(buf["layer"] > 0))


def visible_leaf_index(buf):
    """センサが**見えている**葉面積 / 地表面積 [m^2/m^2]。

    セルの投影面積 ``cell^2`` を最上面の ``|n.z|`` で割ると、そのセルが写している
    葉面積になる(葉が寝ているほど 1 セルが表す葉面積は小さい)。
    """
    m = (buf["lid"] >= 0) & (buf["nz"] > 1e-6)
    return float(np.sum(buf["cell"] ** 2 / buf["nz"][m]) / PLOT_AREA)


# --------------------------------------------------------------------------- #
# 3. 三角形メッシュ —— face_areas / face_normals で面積加重の葉角を出す         #
# --------------------------------------------------------------------------- #
def canopy_mesh(can, nu=40, nt=8, max_leaves=None):
    """群落の葉を三角形メッシュにする → ``(V, F)``。

    面の向きは葉の表側(上向き)に揃える。``mesh_area`` と閉形式 pi/4 L W の
    差が、そのまま**離散化の代償**になる。

    ★``u`` の両端(葉先と葉元)は幅がゼロなので、そこに頂点を置くと ``nt`` 個の
    頂点が 1 点に潰れ、``face_normals`` が「退化三角形」で**拒否する**
    (2026-09-07 に踏んだ)。半セル内側から取ることで避ける ——
    そのぶん先端の面積を落とすので、閉形式との差に現れる。
    """
    idx = range(can["L"].size if max_leaves is None else min(max_leaves, can["L"].size))
    V, F = [], []
    off = 0
    for i in idx:
        bx, by, bz = can["base"][i]
        phi, beta, kap = can["phi"][i], can["beta"][i], can["kappa"][i]
        ll, ww = can["L"][i], can["W"][i]
        u = np.linspace(0.0, ll, nu + 2)[1:-1]
        t = np.linspace(-1.0, 1.0, nt)
        w = width_of(u, ll, ww)
        cx = bx + ix_of(u, beta, kap) * np.cos(phi)
        cy = by + ix_of(u, beta, kap) * np.sin(phi)
        cz = bz + iz_of(u, beta, kap)
        ex, ey = -np.sin(phi), np.cos(phi)
        vx = cx[:, None] + t[None, :] * 0.5 * w[:, None] * ex
        vy = cy[:, None] + t[None, :] * 0.5 * w[:, None] * ey
        vz = np.repeat(cz[:, None], nt, 1)
        V.append(np.stack([vx.ravel(), vy.ravel(), vz.ravel()], 1))
        a, bb = np.meshgrid(np.arange(nu - 1), np.arange(nt - 1), indexing="ij")
        p00 = (a * nt + bb).ravel() + off
        p10 = ((a + 1) * nt + bb).ravel() + off
        p01 = (a * nt + bb + 1).ravel() + off
        p11 = ((a + 1) * nt + bb + 1).ravel() + off
        F.append(np.stack([p00, p10, p11], 1))
        F.append(np.stack([p00, p11, p01], 1))
        off += nu * nt
    return np.concatenate(V, 0), np.concatenate(F, 0).astype(np.int64)


def mesh_leaf_angles(mesh):
    """面ごとの傾き [度] と**面積の重み**(:func:`face_areas` / :func:`face_normals`)。"""
    areas = np.asarray(L3.face_areas(mesh))
    nrm = np.asarray(L3.face_normals(mesh))
    inc = np.degrees(np.arccos(np.clip(np.abs(nrm[:, 2]), 0.0, 1.0)))
    return inc, areas, np.abs(nrm[:, 2])


# --------------------------------------------------------------------------- #
# 4. 節 1 —— 場面と真値                                                        #
# --------------------------------------------------------------------------- #
def section_scene():
    print("\n" + "=" * 78)
    print("1) 場面と真値 —— 葉面積・葉角・草高は式で分かる")
    print("=" * 78)

    can = make_canopy()
    k_true = canopy_G(can)
    print("  区画 %.2f x %.2f m(周期境界)  条間 %.2f m / 株間 %.2f m -> %d 株"
          " = %.2f 株/m^2" % (PLOT, PLOT, ROW, IN_ROW, can["n_plant"],
                              can["n_plant"] / PLOT_AREA))
    print("  1 株 %d 枚 / 葉 1 枚 %.4f m^2(閉形式 pi/4 x L x W)-> 葉面積合計"
          " %.3f m^2" % (can["n_leaf"], float(can["area"].mean()),
                         float(can["area"].sum())))
    print("  ★真値  LAI = %.4f m^2/m^2   草高 = %.3f m   消光係数 k = G(0) = %.4f"
          % (can["lai"], can["height"], k_true))
    print("  稈の側面積 / 地表面積 = %.4f m^2/m^2 —— **これは葉ではない**"
          "(PAI = LAI + %.3f)" % (can["stem_area"], can["stem_area"]))

    mesh = canopy_mesh(can)
    area_mesh = float(L3.mesh_area(mesh))
    inc, ar, nz = mesh_leaf_angles(mesh)
    k_mesh = float(np.sum(ar * nz) / np.sum(ar))
    inc_mean = float(np.sum(ar * inc) / np.sum(ar))
    print("\n  メッシュ(%d 面)で検算: 面積 %.4f m^2 (閉形式比 %+.3f %%) / "
          "面積加重 <|n.z|> = %.4f (閉形式比 %+.3f %%)"
          % (mesh[1].shape[0], area_mesh,
             100 * (area_mesh - can["area"].sum()) / can["area"].sum(),
             k_mesh, 100 * (k_mesh - k_true) / k_true))
    print("  面積加重の平均葉傾角 = %.2f 度(面ごとの面積で重みを付けないと"
          " %.2f 度 = %+.2f 度ずれる)"
          % (inc_mean, float(inc.mean()), float(inc.mean()) - inc_mean))

    buf = canopy_buffers(can, CELL_FINE)
    cov = cover_of(buf)
    print("\n  上から見る: 植被率 %.4f / 重なりの平均枚数 %.4f 枚 = k x LAI の実測"
          "(閉形式 %.4f、比 %+.3f %%)"
          % (cov, float(buf["layer"].mean()), k_true * can["lai"],
             100 * (float(buf["layer"].mean()) - k_true * can["lai"])
             / (k_true * can["lai"])))
    return can, buf, k_true, (inc, ar, nz)


# --------------------------------------------------------------------------- #
# 5. 節 2 —— 稈をカプセルで作り、SDF -> voxel -> mesh の代償を測る              #
# --------------------------------------------------------------------------- #
def section_stem_capsule():
    print("\n" + "=" * 78)
    print("2) 稈 = カプセル —— SDF から mesh へ渡すたびに面積は目減りする")
    print("=" * 78)

    a = np.array([0.0, 0.0, 0.0])
    b = np.array([0.0, 0.0, 0.30])                 # 短く切った稈の一節 [m]
    r = 0.011
    area_ex = 2 * np.pi * r * float(np.linalg.norm(b - a)) + 4 * np.pi * r ** 2
    vol_ex = np.pi * r ** 2 * float(np.linalg.norm(b - a)) + 4.0 / 3.0 * np.pi * r ** 3
    print("  閉形式: 表面積 %.6f m^2 / 体積 %.8f m^3(半径 %.3f m, 芯線長 %.3f m)"
          % (area_ex, vol_ex, r, float(np.linalg.norm(b - a))))
    print("   h [mm]   面積 [m^2]   誤差      体積 [m^3]     誤差   水密")
    rows, hs, aerr, verr = [], [], [], []
    for h in (0.0040, 0.0028, 0.0020, 0.0014):
        bounds = ((-0.03, 0.03), (-0.03, 0.03), (-0.03, 0.33))
        res = [max(4, int(round((q[1] - q[0]) / h))) for q in bounds]
        g = np.asarray(L3.grid_coords(bounds, res))
        sdf = np.asarray(L3.capsule_sdf(g, a, b, r))
        occ = np.asarray(L3.sdf_to_occupancy(sdf))
        mesh = L3.voxel_to_mesh.raw(occ.astype(np.float64), 0.5)
        V = np.asarray(mesh[0], np.float64)
        # voxel_to_mesh は voxel 単位の座標を返す。軸ごとの辺長を掛けて m に戻す。
        step = np.array([(q[1] - q[0]) / (n - 1) for q, n in zip(bounds, res)])
        V = V * step[None, :]
        F = np.asarray(mesh[1], np.int64)
        am = float(L3.mesh_area((V, F)))
        vm = abs(float(L3.mesh_volume((V, F))))    # marching cubes は内向き巻き
        nb = int(np.asarray(L3.boundary_vertices((V, F))).size)
        rows.append(["%.1f" % (1000 * h), "%.6f" % am,
                     "%+.2f %%" % (100 * (am - area_ex) / area_ex),
                     "%.8f" % vm, "%+.2f %%" % (100 * (vm - vol_ex) / vol_ex),
                     "水密" if nb == 0 else "縁 %d 点" % nb])
        hs.append(1000 * h)
        aerr.append(100 * (am - area_ex) / area_ex)
        verr.append(100 * (vm - vol_ex) / vol_ex)
        print("   %5.1f   %.6f  %+6.2f %%   %.8f  %+6.2f %%   %s"
              % (1000 * h, am, aerr[-1], vm, verr[-1], rows[-1][5]))

    print("\n  ★**面積と体積は同じ向きに壊れない**: 体積は %+.2f -> %+.2f %% と"
          "詰めれば当たるのに、\n     面積は %+.2f -> %+.2f %% で**一貫して過大**"
          " —— marching cubes の階段面は\n     滑らかな円筒より長い。"
          "カプセルの LAI 換算(稈の側面積)を voxel 経由で出すと\n     この分だけ"
          "PAI が水増しされる。" % (verr[0], verr[-1], aerr[0], aerr[-1]))

    figs.save_table("capsule_calibration",
                    ["voxel h [mm]", "面積 [m^2]", "面積の誤差", "体積 [m^3]",
                     "体積の誤差", "境界"], rows,
                    title="稈(カプセル)の SDF -> voxel -> mesh の代償",
                    caption="閉形式 2 pi r h + 4 pi r^2 / pi r^2 h + 4/3 pi r^3 と比べる。")
    return {"area_err": aerr, "vol_err": verr, "h": hs}


# --------------------------------------------------------------------------- #
# 6. 節 3 —— ゼロ点(植被率 -> Beer-Lambert 反転)                              #
# --------------------------------------------------------------------------- #
def lai_from_cover(cover, k):
    """Beer-Lambert の反転 ``LAI = -ln(1 - C) / k``(**ゼロ点の推定器**)。"""
    c = np.clip(np.asarray(cover, np.float64), 0.0, 1.0 - 1e-12)
    return -np.log(1.0 - c) / k


def section_zero_point(k_true):
    print("\n" + "=" * 78)
    print("3) ゼロ点 —— 上から見た植被率を Beer-Lambert で LAI に直す")
    print("=" * 78)
    print("  教科書の既定は k = 0.5(球形葉角分布)。この群落の真の k は %.4f。"
          % k_true)
    print("   葉数  真の LAI   植被率   LAI(k=0.5)  誤差    LAI(真の k)  誤差")

    rows, lai_t, lai_05, lai_kt, covers = [], [], [], [], []
    for n_leaf in (1, 2, 4, 7, 11, 16):
        can = make_canopy(n_leaf=n_leaf)
        buf = canopy_buffers(can)
        c = cover_of(buf)
        e05 = lai_from_cover(c, 0.5)
        ekt = lai_from_cover(c, k_true)
        lai_t.append(can["lai"])
        covers.append(c)
        lai_05.append(float(e05))
        lai_kt.append(float(ekt))
        rows.append(["%d" % n_leaf, "%.3f" % can["lai"], "%.4f" % c,
                     "%.3f" % e05, "%+.1f %%" % (100 * (e05 - can["lai"]) / can["lai"]),
                     "%.3f" % ekt, "%+.1f %%" % (100 * (ekt - can["lai"]) / can["lai"])])
        print("   %4d   %7.3f  %7.4f   %8.3f  %+6.1f %%   %8.3f  %+6.1f %%"
              % (n_leaf, can["lai"], c, e05, 100 * (e05 - can["lai"]) / can["lai"],
                 ekt, 100 * (ekt - can["lai"]) / can["lai"]))

    print("\n  ★k を真値に直しても救われない。薄い群落(LAI %.2f)で %+.1f %% なのに、"
          % (lai_t[0], 100 * (lai_kt[0] - lai_t[0]) / lai_t[0]))
    print("     厚い群落(LAI %.2f)では %+.1f %% —— **偏りは k ではなく群落の並び方**"
          "から来ている。" % (lai_t[-1], 100 * (lai_kt[-1] - lai_t[-1]) / lai_t[-1]))
    figs.save_table("zero_point",
                    ["1 株の葉数", "真の LAI", "植被率", "LAI (k=0.5)", "誤差",
                     "LAI (真の k)", "誤差"], rows,
                    title="ゼロ点: 植被率から LAI を出す",
                    caption="k を真値にしても、厚くなるほど過小評価が進む。")
    return {"lai_true": lai_t, "cover": covers, "lai_k05": lai_05, "lai_kt": lai_kt}


# --------------------------------------------------------------------------- #
# 7. 節 4 —— 崖を先に予測してから測る                                          #
# --------------------------------------------------------------------------- #
def section_cliff(k_true):
    print("\n" + "=" * 78)
    print("4) 崖 —— 先に予測する。2 つの推定器に 2 つの別々の天井がある")
    print("=" * 78)
    print("  予測 A(遮蔽の天井): 上から見えている葉面積 / 地表面積 は")
    print("     ∫_0^LAI exp(-k s) ds = (1 - exp(-k LAI)) / k なので、LAI -> ∞ で")
    print("     **1/k = %.3f m^2/m^2 で頭打ち**。葉を何枚足しても超えない。" % (1.0 / k_true))
    print("  予測 B(投影が畳む崖): 植被率の感度 dC/dLAI = k exp(-k LAI) は")
    print("     LAI とともに指数で鈍る。密度 rho 点/m^2 の標本雑音")
    print("     sigma_C = sqrt(C(1-C)/n) が LAI 差 0.5 の信号を飲む LAI が崖。")

    n_leaves = list(range(1, 25))
    lai_t, cover, vis, layers = [], [], [], []
    for n_leaf in n_leaves:
        can = make_canopy(n_leaf=n_leaf)
        buf = canopy_buffers(can)
        lai_t.append(can["lai"])
        cover.append(cover_of(buf))
        vis.append(visible_leaf_index(buf))
        layers.append(float(buf["layer"].mean()))
    lai_t = np.asarray(lai_t)
    cover = np.asarray(cover)
    vis = np.asarray(vis)

    pred_vis = (1.0 - np.exp(-k_true * lai_t)) / k_true
    print("\n   真の LAI   見えている葉面積   予測(1-e^-kL)/k   比")
    for i in (0, 3, 6, 11, 17, 23):
        print("   %8.3f   %14.4f   %15.4f   %6.3f"
              % (lai_t[i], vis[i], pred_vis[i], vis[i] / pred_vis[i]))
    print("  ★天井の実測 %.4f m^2/m^2(LAI %.2f)、予測 1/k = %.4f —— 比 %.3f。"
          % (vis[-1], lai_t[-1], 1.0 / k_true, vis[-1] * k_true))
    print("     LAI が %.2f -> %.2f と %.1f 倍になっても見える葉は %.2f 倍にしか"
          "ならない。" % (lai_t[5], lai_t[-1], lai_t[-1] / lai_t[5],
                          vis[-1] / vis[5]))

    # --- クランピング指数 Omega ------------------------------------------- #
    omega = lai_from_cover(cover, k_true) / lai_t
    print("\n  クランピング指数 Omega = LAI(推定) / LAI(真値):"
          " LAI %.2f で %.3f、LAI %.2f で %.3f。"
          % (lai_t[0], omega[0], lai_t[-1], omega[-1]))
    print("     ★予想は「株冠が地面を覆い尽くしているので Omega ≒ 1」だったが、"
          "実測は %.3f。" % (omega[-1]))
    print("     株冠は閉じていても**株の中で葉どうしが同じ地面を何度も覆う** ——"
          " 互生の葉は\n     1 つの鉛直面に並ぶので、そこが二重三重に重なる。")

    # --- 崖 B: 雑音が LAI 差 0.5 を飲む点 --------------------------------- #
    rng = np.random.default_rng(SEED)
    d_lai = 0.5
    print("\n   点密度 rho   予測の崖 LAI*   実測の崖 LAI*(判別率 84 %% を切る点)")
    dens, pred_l, meas_l = [], [], []
    for rho in (50.0, 200.0, 800.0, 3200.0):
        n_pt = int(round(rho * PLOT_AREA))
        # 予測: d' = dC / sqrt(2 C(1-C)/n) = 1 となる LAI(モデルは Omega 込み)
        om = float(np.interp(2.0, lai_t, omega))
        grid = np.linspace(0.3, 12.0, 400)
        cc = 1.0 - np.exp(-k_true * om * grid)
        dc = k_true * om * d_lai * np.exp(-k_true * om * grid)
        dprime = dc / np.sqrt(2.0 * cc * (1.0 - cc) / n_pt)
        below = np.nonzero(dprime < 1.0)[0]
        pl = float(grid[below[0]]) if below.size else float(grid[-1])
        # 実測: 隣り合う 2 条件を rho 点で標本化して順序が正しく出る割合
        ml = np.nan
        for i in range(len(lai_t) - 2):
            j = int(np.argmin(np.abs(lai_t - (lai_t[i] + d_lai))))
            if j <= i:
                continue
            c1 = rng.binomial(n_pt, cover[i], 4000) / n_pt
            c2 = rng.binomial(n_pt, cover[j], 4000) / n_pt
            acc = float(np.mean(c2 > c1))
            if acc < 0.84:
                ml = lai_t[i]
                break
        if not np.isfinite(ml):
            ml = lai_t[-1]
        dens.append(rho)
        pred_l.append(pl)
        meas_l.append(float(ml))
        print("   %8.0f     %10.2f     %10.2f" % (rho, pl, ml))
    print("  ★崖は点密度の**対数**でしか動かない: %.0f -> %.0f 点/m^2 と %.0f 倍に"
          "しても\n     崖は %.2f -> %.2f(+%.2f)しか伸びない。"
          % (dens[0], dens[-1], dens[-1] / dens[0], meas_l[0], meas_l[-1],
             meas_l[-1] - meas_l[0]))

    figs.save_plot("cliff_ceilings",
                   [("見えている葉面積(実測)", lai_t, vis),
                    ("予測 (1-e^-kL)/k", lai_t, pred_vis),
                    ("天井 1/k", lai_t, np.full_like(lai_t, 1.0 / k_true)),
                    ("真値 = LAI", lai_t, lai_t)],
                   xlabel="真の LAI [m^2/m^2]", ylabel="葉面積指数 [m^2/m^2]",
                   title="遮蔽の天井は 1/k —— 葉を足しても見える分は増えない",
                   caption="実測と閉形式 (1-e^-kL)/k が重なる。斜めの直線が真値。")
    figs.save_plot("cliff_estimators",
                   [("LAI(植被率から)", lai_t, lai_from_cover(cover, k_true)),
                    ("真値", lai_t, lai_t),
                    ("重なりの平均枚数 / k", lai_t, np.asarray(layers) / k_true)],
                   xlabel="真の LAI [m^2/m^2]", ylabel="推定 LAI [m^2/m^2]",
                   title="植被率からの LAI は真値から離れ続ける",
                   caption="重なりの枚数(遮蔽を無視して全部数えた場合)は真値に乗る。")
    figs.save_plot("cliff_density",
                   [("予測(d'=1)", dens, pred_l), ("実測(判別率 84 %)", dens, meas_l)],
                   xlabel="点密度 [点/m^2]", ylabel="判別できる上限 LAI",
                   title="崖は点密度の対数でしか動かない")
    return {"lai": lai_t, "cover": cover, "vis": vis, "layers": np.asarray(layers),
            "omega": omega, "pred_vis": pred_vis, "dens": dens,
            "pred_l": pred_l, "meas_l": meas_l, "k": k_true}


# --------------------------------------------------------------------------- #
# 8. 節 5 —— 対照群: 遮蔽が奪う分と、投影が畳む分を分けて数える                 #
# --------------------------------------------------------------------------- #
def section_controls(k_true):
    print("\n" + "=" * 78)
    print("5) 対照群 —— 「遮蔽が奪う分」と「投影が畳む分」を分けて数える")
    print("=" * 78)

    rows = []
    print("   条件                    LAI    重なり枚数  植被率  見える葉  "
          "畳んだ分  奪われた分")
    keep = {}
    for name, n_leaf, dist in (("(a) 疎(葉 1 枚/株)", 1, True),
                               ("(b) 基準(互生)", 7, True),
                               ("(c) 厚い(互生)", 16, True),
                               ("(d) 厚い(方位乱数)", 16, False)):
        can = make_canopy(n_leaf=n_leaf, distichous=dist)
        buf = canopy_buffers(can)
        cov = cover_of(buf)
        lay = float(buf["layer"].mean())
        v = visible_leaf_index(buf)
        fold = lay - cov                      # 投影 [m^2/m^2]、重なりが 1 枚に畳まれた分
        stolen = can["lai"] - v               # 葉 [m^2/m^2]、遮蔽で見えない分
        rows.append([name, "%.3f" % can["lai"], "%.4f" % lay, "%.4f" % cov,
                     "%.4f" % v, "%.4f" % fold, "%.4f" % stolen])
        print("   %-22s %6.3f  %9.4f  %7.4f  %8.4f  %8.4f  %9.4f"
              % (name, can["lai"], lay, cov, v, fold, stolen))
        keep[name] = (can, buf, cov, lay, v)

    can_c, buf_c, cov_c, lay_c, vis_c = keep["(c) 厚い(互生)"]
    print("\n  ★**天頂から見るかぎり、遮蔽は植被率を 1 ビットも変えない**。")
    print("     植被率は最上面だけで決まるので、下に何枚隠れていても同じ %.4f。"
          % cov_c)
    print("     壊しているのは**投影が畳む分 %.4f(投影 m^2/m^2)**のほうで、"
          % (lay_c - cov_c))
    print("     これは「1 セルを覆う葉が平均 %.2f 枚あるのに 1 枚として数える」"
          "こと。" % lay_c)
    print("  ★遮蔽が奪うのは**別の推定器**: 見えた葉を足す式は %.4f m^2/m^2 しか"
          "拾えず、\n     真値 %.3f の %.1f %% を落とす(葉の単位で %.4f m^2/m^2)。"
          % (vis_c, can_c["lai"], 100 * (1 - vis_c / can_c["lai"]),
             can_c["lai"] - vis_c))

    can_d, buf_d, cov_d, lay_d, vis_d = keep["(d) 厚い(方位乱数)"]
    om_c = lai_from_cover(cov_c, k_true) / can_c["lai"]
    om_d = lai_from_cover(cov_d, k_true) / can_d["lai"]
    print("  ★★原因は互生(葉が 1 つの鉛直面に並ぶこと)だと**対照群 (d) が示す**:")
    print("     同じ LAI %.3f でも方位を乱数にすると Omega が %.3f -> %.3f、"
          % (can_c["lai"], om_c, om_d))
    print("     植被率が %.4f -> %.4f、推定 LAI が %.3f -> %.3f と真値へ寄る。"
          % (cov_c, cov_d, lai_from_cover(cov_c, k_true),
             lai_from_cover(cov_d, k_true)))

    figs.save_table("controls",
                    ["条件", "真の LAI", "重なり枚数", "植被率", "見える葉面積",
                     "畳んだ分", "遮蔽が奪った分"], rows,
                    title="対照群: 壊れ方を種類ごとに数える",
                    caption="「畳んだ分」は投影面積の単位、「奪われた分」は葉面積の単位。"
                            "同じ量の言い換えではない。")

    # 場面の図 —— 深度図・重なり枚数の地図・カバー図
    buf_f = canopy_buffers(can_c, CELL_FINE)
    top = np.where(buf_f["lid"] >= 0, buf_f["top"], 0.0)
    figs.save_grid("scene_nadir",
                   [top, np.minimum(buf_f["layer"], 6.0),
                    (buf_f["lid"] >= 0).astype(np.float64)],
                   ["最上面の高さ [m](0 = 裸地)",
                    "重なった葉の枚数(上限 6)",
                    "植被(1 = 植物)"],
                   title="天頂から見た群落(LAI %.2f、セル %.0f mm)"
                         % (can_c["lai"], 1000 * CELL_FINE), ncols=3,
                   caption="真ん中の図が「投影が畳む分」そのもの ——"
                           "白いほど何枚も重なっている。")
    return {"cover_c": cov_c, "layer_c": lay_c, "vis_c": vis_c,
            "lai_c": can_c["lai"], "omega_c": om_c, "omega_d": om_d,
            "cover_d": cov_d, "can_c": can_c, "buf_fine": buf_f}


# --------------------------------------------------------------------------- #
# 9. 節 6 —— 掃引(株間・葉の傾き・点密度とセル)                               #
# --------------------------------------------------------------------------- #
def section_sweeps():
    print("\n" + "=" * 78)
    print("6) 掃引 —— 条間・葉の傾き・センサの粗さ")
    print("=" * 78)

    print("\n  (a) 条間 [m](LAI をほぼ一定に保つため 1 株の葉数で補正)")
    print("      条間   株/m^2  1株の葉数   真の LAI   植被率   Omega")
    rows_a = []
    for row, n_leaf in ((0.375, 4), (0.5625, 5), (0.75, 7), (1.125, 14)):
        can = make_canopy(n_leaf=n_leaf, row=row)
        k = canopy_G(can)
        buf = canopy_buffers(can)
        c = cover_of(buf)
        om = float(lai_from_cover(c, k) / can["lai"])
        rows_a.append(["%.3f" % row, "%.2f" % (can["n_plant"] / PLOT_AREA),
                       "%d" % n_leaf, "%.3f" % can["lai"], "%.4f" % c, "%.3f" % om])
        print("      %.3f  %6.2f   %6d   %8.3f  %7.4f  %6.3f"
              % (row, can["n_plant"] / PLOT_AREA, n_leaf, can["lai"], c, om))
    print("      ★条間を %s -> %s m と広げると Omega は %s -> %s。"
          "**同じ LAI でも並べ方で推定値が動く**。"
          % (rows_a[0][0], rows_a[-1][0], rows_a[0][5], rows_a[-1][5]))

    print("\n  (b) 着生角 [度](葉の傾き。k は閉形式で出す)")
    print("      着生角    k = G(0)   真の LAI   植被率   推定 LAI   誤差")
    rows_b, betas, ks, errs = [], [], [], []
    for beta in (45.0, 58.0, 68.0, 78.0):
        can = make_canopy(beta_deg=beta)
        k = canopy_G(can)
        buf = canopy_buffers(can)
        c = cover_of(buf)
        est = float(lai_from_cover(c, k))
        e = 100 * (est - can["lai"]) / can["lai"]
        rows_b.append(["%.0f" % beta, "%.4f" % k, "%.3f" % can["lai"],
                       "%.4f" % c, "%.3f" % est, "%+.1f %%" % e])
        betas.append(beta)
        ks.append(k)
        errs.append(e)
        print("      %5.0f    %7.4f   %8.3f  %7.4f  %8.3f  %+6.1f %%"
              % (beta, k, can["lai"], c, est, e))
    print("      ★立った葉ほど誤差が小さい(k %.3f -> %.3f で誤差 %+.1f -> %+.1f %%)"
          " ——\n         同じ葉面積でも光が通るので、植被率がまだ飽和していない。"
          % (ks[0], ks[-1], errs[0], errs[-1]))

    print("\n  (c) センサの粗さ(セル辺長)と点密度 —— **欠測の扱いで向きが逆**")
    can = make_canopy(n_leaf=11)
    k = canopy_G(can)
    ref = cover_of(canopy_buffers(can, 0.0025))
    print("      基準の植被率(セル 2.5 mm)= %.4f / 真の LAI = %.3f" % (ref, can["lai"]))
    print("      セル [mm]   植被率    LAI      誤差")
    rows_c = []
    cells, covs = [], []
    for cell in (0.0025, 0.005, 0.010, 0.020, 0.040, 0.080):
        c = cover_of(canopy_buffers(can, cell))
        est = float(lai_from_cover(c, k))
        rows_c.append(["%.1f" % (1000 * cell), "%.4f" % c, "%.3f" % est,
                       "%+.1f %%" % (100 * (est - can["lai"]) / can["lai"])])
        cells.append(1000 * cell)
        covs.append(c)
        print("      %8.1f   %.4f  %7.3f   %+6.1f %%"
              % (1000 * cell, c, est, 100 * (est - can["lai"]) / can["lai"]))
    print("      ★セル中心で判定するかぎり、粗いセルは**偏らずに散らばるだけ**"
          "(%.4f -> %.4f)。\n         「セルに 1 点でも当たれば植被」と数えると"
          "縁のぶん太る —— それを次で測る。" % (covs[0], covs[-2]))

    # 「1 点でも当たれば植被」の規約(実機の既定)を、同じ場面で測る
    buf = canopy_buffers(can, 0.0025)
    n_fine = buf["n"]
    print("\n      規約の違い(基準 %.4f):" % ref)
    rows_d = []
    for cell in (0.010, 0.020, 0.040, 0.080):
        f = int(round(cell / 0.0025))
        m = (buf["lid"] >= 0)[: (n_fine // f) * f, : (n_fine // f) * f]
        blocks = m.reshape(n_fine // f, f, n_fine // f, f)
        any_hit = float(blocks.any(axis=(1, 3)).mean())
        centre = cover_of(canopy_buffers(can, cell))
        rows_d.append(["%.0f" % (1000 * cell), "%.4f" % centre, "%.4f" % any_hit,
                       "%+.3f" % (any_hit - centre)])
        print("        セル %2.0f mm: 中心判定 %.4f / 1 点でも当たれば %.4f "
              "(+%.4f) -> LAI %+.1f %%"
              % (1000 * cell, centre, any_hit, any_hit - centre,
                 100 * (float(lai_from_cover(any_hit, k)) - can["lai"]) / can["lai"]))

    figs.save_table("sweep_row_beta",
                    ["条間 [m]", "株/m^2", "1 株の葉数", "真の LAI", "植被率", "Omega"],
                    rows_a, title="掃引 (a) 条間",
                    caption="LAI をそろえても並べ方で推定値が動く。")
    figs.save_plot("sweep_beta",
                   [("推定 LAI の誤差 [%]", ks, errs),
                    ("ゼロ(真値)", ks, [0.0] * len(ks))],
                   xlabel="消光係数 k = G(0)", ylabel="推定 LAI の誤差 [%]",
                   title="立った葉(k 小)ほど植被率からの LAI は当たる")
    figs.save_table("sweep_cell",
                    ["セル [mm]", "植被率(中心判定)", "推定 LAI", "誤差"], rows_c,
                    title="掃引 (c) センサのセル辺長",
                    caption="セル中心で判定すれば偏らない。太るのは規約のせい。")
    return {"row": rows_a, "beta": rows_b, "cell": rows_c, "rule": rows_d,
            "ref_cover": ref, "ks": ks, "errs": errs, "covs": covs, "cells": cells}


# --------------------------------------------------------------------------- #
# 10. 節 7 —— 点群から葉角を推定して受光に効かせる                              #
# --------------------------------------------------------------------------- #
def sensor_cloud(buf, rho, rng, sigma=0.005, dropout=0.05):
    """天頂の距離センサが返す点群 ``(N,3) = (x,y,z)`` [m]。

    セルの最上面をランダムに ``rho`` 点/m^2 だけ拾い、測距雑音と欠測を入れる。
    裸地のセルは地面(z = 0 + 粗さ)を返す —— 実機も「返りが無い」ではなく
    「地面が返る」ので、**地面と植物を分ける仕事が呼び手に残る**。
    """
    n = buf["n"]
    cell = buf["cell"]
    n_pt = int(round(rho * PLOT_AREA))
    r = rng.integers(0, n, n_pt)
    c = rng.integers(0, n, n_pt)
    x = (c + rng.uniform(0, 1, n_pt)) * cell
    y = (r + rng.uniform(0, 1, n_pt)) * cell
    z = np.where(buf["lid"][r, c] >= 0, buf["top"][r, c], 0.0)
    z = z + rng.normal(0.0, sigma, n_pt)
    z[buf["lid"][r, c] < 0] += rng.normal(0.0, 0.004, int(np.sum(buf["lid"][r, c] < 0)))
    keep = rng.random(n_pt) > dropout
    return np.stack([x, y, z], 1)[keep], (buf["lid"][r, c] >= 0)[keep]


def section_leaf_angle(can, buf_fine, k_true, mesh_stats):
    print("\n" + "=" * 78)
    print("7) 葉角の推定と受光 —— 面積で重みを付けないと角度は嘘になる")
    print("=" * 78)

    inc, ar, nz = mesh_stats
    rng = np.random.default_rng(SEED + 1)
    pts, is_veg = sensor_cloud(buf_fine, 4000.0, rng)
    print("  センサ点群 %d 点(4000 点/m^2、測距雑音 5 mm、欠測 5 %%)" % pts.shape[0])

    # 地面を知らない前提で平面を当てる(plane_segmentation は RANSAC)
    lab = np.asarray(L3.plane_segmentation(pts, 0.02, 200, 1, 200, SEED))
    ground = pts[lab == 0]
    z_g = float(np.median(ground[:, 2])) if ground.size else 0.0
    h99 = float(np.percentile(pts[:, 2] - z_g, 99.9))
    print("  地面: 抽出 %d 点、推定標高 %.4f m(真値 0)-> 草高 %.3f m(真値 %.3f m、"
          "%+.1f %%)" % (ground.shape[0] // 1, z_g, h99, can["height"],
                         100 * (h99 - can["height"]) / can["height"]))

    veg = pts[pts[:, 2] - z_g > 0.05]
    sub = veg[rng.choice(veg.shape[0], min(20000, veg.shape[0]), replace=False)]
    nrm = np.asarray(L3.estimate_normals(sub, 18))
    nz_est = np.abs(nrm[:, 2])
    # 各点が写す葉面積は cell^2/|n.z| なので、重みは 1/|n.z| = 面積加重の逆数
    k_pts = float(sub.shape[0] / np.sum(1.0 / np.maximum(nz_est, 0.05)))
    k_naive = float(np.mean(nz_est))
    print("\n  ★法線の符号は任意なので |n.z| で受ける(そこは既知の作法)。問題は重み:")
    print("     面積加重の k = %.4f / 点数だけの平均 = %.4f / 真値 %.4f"
          % (k_pts, k_naive, k_true))
    print("     メッシュ側(face_areas で重み)= %.4f、面ごとの面積を無視すると %.4f。"
          % (float(np.sum(ar * nz) / np.sum(ar)), float(np.mean(nz))))

    # 受光: fPAR = 1 - exp(-k(theta_s) LAI)。天頂の植被率だけからだと k(0) LAI しか
    # 分からないので、**必要なのは比 k(theta_s)/k(0)**。
    print("\n  受光(fPAR)への効き —— 太陽高度で必要な係数が変わる")
    print("      太陽天頂角   G(theta)/cos   球形仮定   真の fPAR   仮定の fPAR   誤差")
    rows = []
    cov = cover_of(buf_fine)
    for th_deg in (15.0, 30.0, 45.0, 60.0):
        th = np.radians(th_deg)
        g = canopy_G_zenith(can, th)
        k_th = g / np.cos(th)
        k_sph = 0.5 / np.cos(th)
        fpar_true = 1.0 - np.exp(-k_th * can["lai"])
        # 天頂の植被率 C = 1 - exp(-k(0) LAI_eff) から: fPAR = 1 - (1-C)^(k_th/k0)
        fpar_est = 1.0 - (1.0 - cov) ** (k_sph / (0.5 / 1.0))
        rows.append(["%.0f" % th_deg, "%.4f" % k_th, "%.4f" % k_sph,
                     "%.4f" % fpar_true, "%.4f" % fpar_est,
                     "%+.1f %%" % (100 * (fpar_est - fpar_true) / fpar_true)])
        print("      %8.0f    %8.4f   %8.4f   %8.4f   %10.4f   %+6.1f %%"
              % (th_deg, k_th, k_sph, fpar_true, fpar_est,
                 100 * (fpar_est - fpar_true) / fpar_true))
    print("  ★天頂 (theta=0) では **fPAR = 植被率**がそのまま答えで、k を取り違えても"
          "消える\n     (LAI は k で割るが fPAR は k を掛け戻すので相殺する)。"
          "誤差が出るのは\n     斜めの太陽 —— そこで初めて葉角分布が要る。")

    order = np.argsort(inc)
    figs.save_plot("leaf_angle_dist",
                   [("面積加重(face_areas)", inc[order], np.cumsum(ar[order]) / ar.sum()),
                    ("面の数だけで数える", np.sort(inc), np.linspace(0, 1, inc.size))],
                   xlabel="葉の傾き [度](水平 = 0)", ylabel="累積割合",
                   title="面ごとの面積で重みを付けるかどうかで葉角分布が変わる")
    figs.save_table("fpar", ["太陽天頂角 [度]", "真の k(theta)", "球形仮定の k",
                             "真の fPAR", "仮定の fPAR", "誤差"], rows,
                    title="受光(fPAR)は天頂では k に鈍く、斜めで効く")
    return {"k_pts": k_pts, "k_naive": k_naive, "h99": h99, "rows": rows,
            "n_pts": int(pts.shape[0]), "z_g": z_g}


# --------------------------------------------------------------------------- #
# 11. 節 8 —— 風(葉面積は変わらないのに推定値が動く)                          #
# --------------------------------------------------------------------------- #
def section_wind(k_true):
    print("\n" + "=" * 78)
    print("8) 風 —— 葉面積は 1 mm^2 も変わらないのに推定 LAI が動く")
    print("=" * 78)
    print("   風で寝る量   真の LAI    k = G(0)   植被率   LAI(k 固定)  LAI(k 更新)")
    rows = []
    base_k = None
    for bend in (0.0, 5.0, 10.0, 20.0):
        can = make_canopy(bend_deg=bend)
        k = canopy_G(can)
        if base_k is None:
            base_k = k
        buf = canopy_buffers(can)
        c = cover_of(buf)
        e_fix = float(lai_from_cover(c, base_k))
        e_upd = float(lai_from_cover(c, k))
        rows.append(["%.0f" % bend, "%.4f" % can["lai"], "%.4f" % k, "%.4f" % c,
                     "%.3f" % e_fix, "%.3f" % e_upd])
        print("   %8.0f 度   %8.4f  %8.4f  %7.4f  %9.3f   %9.3f"
              % (bend, can["lai"], k, c, e_fix, e_upd))
    d_fix = float(rows[-1][4]) - float(rows[0][4])
    d_upd = float(rows[-1][5]) - float(rows[0][5])
    print("  ★葉が %s 度寝るだけで、k を固定したままの LAI は %+.3f (%+.1f %%) 動く。"
          % (rows[-1][0], d_fix, 100 * d_fix / float(rows[0][1])))
    print("     k を更新すると %+.3f (%+.1f %%) に縮むが**ゼロにはならない** ——"
          " 寝た葉は\n     重なりも増やすので、k の更新は片方しか直していない。"
          % (d_upd, 100 * d_upd / float(rows[0][1])))
    figs.save_table("wind", ["寝る量 [度]", "真の LAI", "k = G(0)", "植被率",
                             "LAI(k 固定)", "LAI(k 更新)"], rows,
                    title="風で葉が寝ると、面積が同じでも推定 LAI が動く")
    return {"rows": rows, "d_fix": d_fix, "d_upd": d_upd}


# --------------------------------------------------------------------------- #
# 12. 節 9 —— 体積として見る(投影図と断面)                                    #
# --------------------------------------------------------------------------- #
def section_volume(can, buf_fine):
    print("\n" + "=" * 78)
    print("9) 体積として見る —— 投影図と断面、葉面積密度の鉛直分布")
    print("=" * 78)

    rng = np.random.default_rng(SEED + 3)
    mesh = canopy_mesh(can, nu=30, nt=6)
    pts = np.asarray(L3.mesh_sample_points(mesh[0], mesh[1], n=180000,
                                           method="uniform", seed=SEED))
    bounds = ((0.0, PLOT), (0.0, PLOT), (0.0, 1.8))
    res = (90, 90, 72)
    occ = np.asarray(L3.occupancy_grid(pts, bounds, res), np.float64)
    print("  点群 %d 点 -> 占有格子 %s(軸ごとの res)。占有率 %.4f"
          % (pts.shape[0], "x".join(map(str, res)), float(occ.mean())))

    side = np.asarray(L3.render_volume_projection(occ, azimuth=0.0, elevation=90.0,
                                                  mode="xray"))
    nadir = np.asarray(L3.render_volume_projection(occ, azimuth=0.0, elevation=0.0,
                                                   mode="xray"))
    # 葉面積密度の鉛直分布(真値は葉の設計値から閉形式で積める)
    zc = np.linspace(0.0, 1.8, 73)
    prof_true = np.zeros(72)
    for i in range(can["L"].size):
        u = (np.arange(_QN) + 0.5) * (can["L"][i] / _QN)
        z = can["base"][i, 2] + iz_of(u, can["beta"][i], can["kappa"][i])
        w = width_of(u, can["L"][i], can["W"][i]) * (can["L"][i] / _QN)
        prof_true += np.histogram(z, bins=zc, weights=w)[0]
    prof_true /= PLOT_AREA * (zc[1] - zc[0])
    prof_occ = occ.sum(axis=(1, 2))
    prof_occ = prof_occ / max(prof_occ.max(), 1e-9) * prof_true.max()
    zmid = 0.5 * (zc[1:] + zc[:-1])
    i_pk = int(np.argmax(prof_true))
    print("  葉面積密度のピーク: 真値 %.3f m 高さで %.3f m^2/m^3、"
          "占有格子の山は %.3f m。"
          % (zmid[i_pk], prof_true[i_pk], float(zmid[int(np.argmax(prof_occ))])))
    print("  ★占有格子は「そこに葉があるか」しか持たないので、**重なった葉を数え"
          "られない**。\n     形は似ていても縦軸は面積密度ではない(規格化しないと"
          "並べられない)。")

    dsm = np.where(buf_fine["lid"] >= 0, buf_fine["top"], 0.0)
    slope = np.asarray(L3.dem_slope(dsm, CELL_FINE))
    print("  草冠面の傾斜(dem_slope): 中央値 %.1f 度 / 90 %% 点 %.1f 度 ——"
          " 草冠は「面」ではない。" % (float(np.median(slope)),
                                      float(np.percentile(slope, 90))))

    figs.save_grid("scene_xray", [side, nadir],
                   ["側面からの積算投影(x 線)", "天頂からの積算投影"],
                   title="群落を体積として見る(占有格子 %s)" % "x".join(map(str, res)),
                   caption="側面図では条(row)の構造が縞に見える。")
    mid = occ[:, :, occ.shape[2] // 2]
    figs.save_grid("section_and_dsm",
                   [occ[:, occ.shape[1] // 2, :].T[::-1], dsm, slope],
                   ["鉛直断面(条に直交)", "草冠面の高さ [m]", "草冠面の傾斜 [度]"],
                   title="断面と草冠面", ncols=3,
                   caption="草冠面は連続面ではなく、葉ごとに切り立っている。")
    figs.save_plot("vertical_profile",
                   [("真値(閉形式)", prof_true, zmid),
                    ("占有格子(最大で規格化)", prof_occ, zmid)],
                   xlabel="葉面積密度 [m^2/m^3]", ylabel="高さ [m]",
                   title="葉面積密度の鉛直分布")
    return {"peak_z": float(zmid[i_pk]), "peak": float(prof_true[i_pk]),
            "slope_med": float(np.median(slope)), "occ_mean": float(occ.mean())}


# --------------------------------------------------------------------------- #
# 13. 道具の穴                                                                 #
# --------------------------------------------------------------------------- #
def section_tool_gaps():
    print("\n" + "=" * 78)
    print("10) 道具の穴(この PoC で使ってみて)")
    print("=" * 78)
    print("  (a) 群落の投影(帯の解析的な z-buffer)を作る op が無い。")
    print("      三角形メッシュを任意方向へラスタライズして被覆率・深度を返す口が")
    print("      あれば、この PoC の中核 60 行は 1 呼び出しになる。")
    assert not hasattr(fs.ledger, "rasterize_mesh_depth")
    print("  (b) `voxel_to_mesh` は **voxel 単位の座標**を返す(spacing 引数が無い)。")
    print("      呼び手が (bounds, res) から辺長を作って掛け戻している。")
    import inspect
    assert "spacing" not in inspect.signature(fs.ledger.voxel_to_mesh.raw).parameters
    print("  (c) `mesh_volume` は marching cubes の巻き順(内向き)をそのまま受けるので")
    print("      符号が負になる。ノートに書いてあるとおりだが、abs() を呼び手が付ける。")
    print("  (d) Beer-Lambert の反転(被覆率 -> LAI)と Miller の多角度積分は")
    print("      公開経路に無い。植生・農業の族はまだ 1 本も無い。")
    assert not hasattr(fs.ledger, "beer_lambert_lai")
    print("  (e) `occupancy_grid` は軸ごとの res を受けるようになった(2026-09-07)ので")
    print("      薄い層でも立方に縛られない —— これは足りていた。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("作物の 3-D 表現型 —— 葉が重なった瞬間、葉面積は測れなくなる")
    print("区画 %.2f m 角(周期境界)/ 葉身 %.2f x %.3f m / 稈長 %.2f m"
          % (PLOT, LEAF_L, LEAF_W, STEM_H))
    print("=" * 78)

    can, buf_fine, k_true, mesh_stats = section_scene()
    cap = section_stem_capsule()
    zero = section_zero_point(k_true)
    cliff = section_cliff(k_true)
    ctrl = section_controls(k_true)
    sw = section_sweeps()
    ang = section_leaf_angle(ctrl["can_c"], ctrl["buf_fine"], k_true, mesh_stats)
    wind = section_wind(k_true)
    vol = section_volume(can, buf_fine)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 見える葉面積の天井は 1/k = %.3f m^2/m^2(予測)、実測 %.3f。"
          % (1.0 / k_true, cliff["vis"][-1]))
    print("  * 植被率からの LAI は LAI %.2f で %+.1f %%、LAI %.2f で %+.1f %%。"
          % (cliff["lai"][0], 100 * (cliff["omega"][0] - 1),
             cliff["lai"][-1], 100 * (cliff["omega"][-1] - 1)))
    print("  * 崖は点密度の対数でしか動かない(%.0f -> %.0f 点/m^2 で %.2f -> %.2f)。"
          % (cliff["dens"][0], cliff["dens"][-1], cliff["meas_l"][0],
             cliff["meas_l"][-1]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    # --- 所見を固定する assert ------------------------------------------- #
    assert 1.0 / k_true * 0.90 < cliff["vis"][-1] < 1.0 / k_true, "遮蔽の天井 1/k"
    assert cliff["omega"][-1] < cliff["omega"][0], "クランピングは厚いほど強い"
    assert ctrl["omega_d"] > ctrl["omega_c"], "方位乱数は互生より真値に近い"
    assert cliff["meas_l"][-1] - cliff["meas_l"][0] < 4.0, "崖は対数でしか動かない"
    assert abs(wind["d_upd"]) < abs(wind["d_fix"]), "k の更新は片方しか直さない"

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""小惑星イトカワの重力を、実際の形のまま 3-D で学ぶ(はやぶさが降りた場所はなぜ平らで低いのか、2026-10-25)。

    py -3.11 tools/build_itokawa_anim3d.py            # docs/anim3d/itokawa_gravity.html を書く(初回は重力の計算に数分)
    py -3.11 tools/build_itokawa_anim3d.py --check    # 書かずに、門の値の印字と HTML の生成だけ

形は公開データ(NASA PDS Small Bodies Node の Gaskell Itokawa Shape Model V1.1、Q = 64 の 49,152 面、CC0 1.0。
repo では data/itokawa_shape/gaskell_q64.npz、出典と改変は同じ場所の README.md)。重力は一様密度の多面体の
厳密な式(Werner & Scheeres 1997)を op にした ``polyhedron_gravity`` で、頂点 25,350 個すべてで計算する。
色・矢印・粒の動きは **すべて op の出力**(手で描いた値ではない)。

タブ(1 タブ = 1 つの問い。学習用の型 ① 問い → ② 予想 → ③ 再生 → ④ 式 → ⑤ 限界):

1. **形と大きさ**: 自転軸(z)のまわりに 1 周(12.13 時間)。体積は ``mesh_volume``、大きさは ``obb``、
   質量 = 体積 × 密度(1.9 g/cm³)を公表値と比べる。
2. **表面の重力**: 表面の実効重力の大きさ(重力 + 自転の遠心力)を色で塗り、長軸を通る断面(``mesh_slice_contours``)
   に沿って歩く人の「重さ」と斜面の角を時系列に出す。矢印 = その場所の実効重力の向き。
3. **ミューゼスの海が平らで低いのはなぜ**: 実効ポテンシャルを高さに見立てた地図(ジオポテンシャル高度)と、
   表面に撒いた粒が実効ポテンシャルの坂を下る様子(頂点の隣接で最急降下)。着陸点の推定位置の高さの順位も出す。
4. **限界: 一様密度という仮定**: 頭と胴で密度が違う説(Lowry et al. 2014: x = 150 m で切って胴 1,750 / 頭 2,850 kg/m³)
   へ密度の差を連続に振り、重心が形の中心からずれていく様子と、表面の重力の変わり方を見せる。
5. **数学: 体積 = 符号付き四面体の和**: 面を 1 枚ずつ(ここでは 24 の塊ずつ)足していき、重心を頂点にした四面体の
   体積の和が全体の体積に近づく。内向きの面(首のくびれ)は負の体積(赤)で打ち消す。

理論の線 = 門の値: 球の分割メッシュの遠方の重力(点質量)、直方体と Gauss–Legendre 求積(別の経路)、発散の
差分(ガウスの法則: 中で −4πGρ、外で 0)、勾配の差分、頭と胴に切った 2 つの和 = 全体。値は :func:`gates`、
バッジの表(checks)はその値と基準の比較で決める。限界の回は最初に置かない。

**regen_all には入れない**(``pocviewer.write_viewer`` で書く手回しの生成物。重力の計算に数分かかる。出力を変えたら
手で回して commit。門は tests/test_itokawa_anim3d.py)。重い計算は out/itokawa_anim3d_cache/ に入力のハッシュで
保存し、2 回目からはそれを使う(op の実装・形・定数のどれかが変わればハッシュが変わって計算し直す)。

出典(数値): A. Fujiwara et al., "The rubble-pile asteroid Itokawa as observed by Hayabusa", Science 312,
1330 (2006)(大きさ 535 × 294 × 209 m、質量 3.51 × 10^10 kg、密度 1.9 ± 0.13 g/cm³、ミューゼスの海と
相模原の平らな所が重力的に低い所と一致)/ S. Abe et al., "Mass and local topography measurements of Itokawa
by Hayabusa", Science 312, 1344 (2006)(質量 (3.58 ± 0.18) × 10^10 kg、密度 1.95 ± 0.14 g/cm³、体積
(1.84 ± 0.09) × 10^7 m³、空隙率 約 40 %)/ H. Demura et al., "Pole and global shape of 25143 Itokawa",
Science 312, 1347 (2006)(体積 0.018378 km³ ± 5 %)/ S. C. Lowry et al., "The internal structure of asteroid
(25143) Itokawa as revealed by detection of YORP spin-up", A&A 562, A48 (2014)/ H. Yano & S. Aida, "Hayabusa's
sampling site coordinates on Itokawa"(JAXA キュレーションのシンポジウム 2013 の予稿)/ 重力の式は R. A. Werner &
D. J. Scheeres, Celest. Mech. Dyn. Astron. 65, 313 (1997)。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fullseye as fs  # noqa: E402
import pocviewer as pv  # noqa: E402
import polygrav as pg  # noqa: E402

T = pv.viewer_text
L = fs.ledger
OUT_HTML = ROOT / "docs" / "anim3d" / "itokawa_gravity.html"
DATA = ROOT / "data" / "itokawa_shape" / "gaskell_q64.npz"
CACHE_DIR = ROOT / "out" / "itokawa_anim3d_cache"
LANGS = ("ja", "en")
#: 原本 ver64q.tab の SHA-256(data/itokawa_shape/README.md と tools/import_itokawa_shape.py と同じ)
SHA256_TAB = "b472418ab40e7b7e8b29f085fa1d334038f69a2b3dd936a4e591a77ed3610c28"

# ---- 一次情報の数値(出典は docstring) ---------------------------------------------------------- #
RHO = 1900.0                                  # 密度 [kg/m³](Fujiwara 2006: 1.9 ± 0.13 g/cm³)
RHO_SIGMA = 130.0
PUB_DIMS = (535.0, 294.0, 209.0)              # 直交する 3 軸の長さ [m](Fujiwara 2006 / Demura 2006)
PUB_VOLUME = 0.018378e9                       # 体積 [m³](Demura 2006、± 5 %)
PUB_VOLUME_REL = 0.05
PUB_MASS_F = 3.51e10                          # 質量 [kg](Fujiwara 2006)
PUB_MASS_A, PUB_MASS_A_SIGMA = 3.58e10, 0.18e10   # 質量 [kg](Abe 2006)
PUB_POROSITY = 0.40                           # 空隙率(Abe 2006、LL コンドライトを仮定して約 40 %)
PM_DEG_PER_DAY = 712.14376110                 # 自転(PDS の bundle の説明: W = 129.73 + 712.14376110 d)
OMEGA = math.radians(PM_DEG_PER_DAY) / 86400.0
PERIOD_H = 360.0 / PM_DEG_PER_DAY * 24.0
LOWRY_X_CUT = 150.0                           # 頭と胴の境 x = 150 m(Lowry 2014)
LOWRY_RHO_BODY, LOWRY_RHO_BODY_SIGMA = 1750.0, 110.0
LOWRY_RHO_HEAD, LOWRY_RHO_HEAD_SIGMA = 2850.0, 500.0
LOWRY_RHO_MEAN = 1950.0                       # 全体の密度は Abe 2006 の 1,950 kg/m³ に保つ(Lowry 2014)
LOWRY_COM_X, LOWRY_COM_X_SIGMA = 21.0, 12.0   # 重心のずれ(x 方向だけとしたとき、頭の側へ)[m]
TD_SITES = {                                  # Yano & Aida 2013 の推定(緯度・経度の範囲、度)
    "TD1": ((-82.0, -71.0), (323.0, 324.0)),
    "TD2": ((-10.0, -1.0), (331.0, 333.0)),
}

OPS_USED = ("polygrav.polyhedron_gravity", "polygrav.polyhedron_clip_halfspace", "mesh_props.mesh_volume",
            "mesh_props.mesh_area", "mesh_props.vertex_normals", "mesh_props.face_areas", "pcseg.obb",
            "meshres.mesh_edge_stats", "printpath.mesh_slice_contours", "render3d.geodesic_dome")

ROCK_RGB = (0.64, 0.60, 0.53)
N_CHUNK = 24                                  # 数学のタブの塊の数


# --------------------------------------------------------------------------- #
# 形                                                                          #
# --------------------------------------------------------------------------- #
def load_mesh():
    """npz → (V [m] (N,3), F (M,3), 落とした重複頂点の数)。原本の注意書きの「面から使われない重複頂点」を落とす。"""
    z = np.load(DATA, allow_pickle=False)
    if str(z["source_sha256"]) != SHA256_TAB:
        raise ValueError("形状データの出どころの SHA-256 が記録と違う")
    Vcm = z["vertices_cm"].astype(np.int64)
    F = z["faces"].astype(np.int64)
    used = np.unique(F)
    remap = -np.ones(len(Vcm), dtype=np.int64)
    remap[used] = np.arange(used.size)
    return Vcm[used] / 100.0, remap[F], int(len(Vcm) - used.size)


def latlon_dir(lat, lon):
    la, lo = math.radians(lat), math.radians(lon)
    return np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])


def site_vertex(V, lat, lon, cone_deg=3.0):
    """緯度・経度(body-fixed の原点から見た向き)の方向にある表面の頂点(円錐の中で原点から最も遠いもの)。"""
    d = latlon_dir(lat, lon)
    u = V / np.linalg.norm(V, axis=1)[:, None]
    near = np.flatnonzero(u @ d > math.cos(math.radians(cone_deg)))
    if near.size == 0:
        raise ValueError("その向きに頂点が無い")
    return int(near[np.argmax(np.linalg.norm(V[near], axis=1))])


def vertex_areas(V, F):
    """頂点の面積(接する面の面積の 1/3 ずつ)。face_areas(op)を頂点へ配る。"""
    fa = L.face_areas((V, F))
    va = np.zeros(len(V))
    for k in range(3):
        np.add.at(va, F[:, k], fa / 3.0)
    return va


def neighbors(F, n):
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    e = np.concatenate([e, e[:, ::-1]])
    e = np.unique(e, axis=0)
    starts = np.searchsorted(e[:, 0], np.arange(n + 1))
    return e[:, 1], starts


# --------------------------------------------------------------------------- #
# 重い計算(入力のハッシュで保存)                                               #
# --------------------------------------------------------------------------- #
def _cache_key(V, F):
    h = hashlib.sha256()
    h.update(V.tobytes())
    h.update(F.tobytes())
    h.update((ROOT / "polygrav.py").read_bytes())
    h.update(repr((RHO, OMEGA, LOWRY_X_CUT, pg.G_NEWTON)).encode())
    return h.hexdigest()[:16]


def heavy_fields(V, F, VN, verbose=True):
    """全頂点での一様密度の重力(実効重力・斜面つき)と、頭の部分(単位密度)の重力。数分かかるので保存する。"""
    key = _cache_key(V, F)
    path = CACHE_DIR / ("fields_%s.npz" % key)
    if path.exists():
        z = np.load(path, allow_pickle=False)
        return {k: z[k] for k in z.files}
    if verbose:
        print("computing polyhedron_gravity at %d vertices (whole, then head part) ..." % len(V), flush=True)
    W = pg.polyhedron_gravity((V, F), V, density=RHO, omega=OMEGA, normals=VN)
    head = pg.polyhedron_clip_halfspace((V, F), [LOWRY_X_CUT, 0.0, 0.0], [1.0, 0.0, 0.0])
    H = pg.polyhedron_gravity(head, V, density=1.0)
    out = {"potential": W["potential"], "acceleration": W["acceleration"], "div_g": W["div_g"],
           "eff_potential": W["effective_potential"], "eff_acceleration": W["effective_acceleration"],
           "slope_deg": W["slope_deg"], "com": W["center_of_mass"], "volume": np.array(W["volume"]),
           "head_acc_unit": H["acceleration"], "head_volume": np.array(H["volume"]), "head_com": H["center_of_mass"],
           "head_V": head[0], "head_F": head[1]}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez(path, **out)
    return out


# --------------------------------------------------------------------------- #
# 計算(タブごと)                                                              #
# --------------------------------------------------------------------------- #
def compute(verbose=True):
    V, F, n_dup = load_mesh()
    stats = L.mesh_edge_stats(V, F)
    vol_op = float(L.mesh_volume((V, F)))
    area = float(L.mesh_area((V, F)))
    VN = L.vertex_normals((V, F))
    box = L.obb(V)
    dims = np.sort(2.0 * np.asarray(box["extents"]))[::-1]
    hf = heavy_fields(V, F, VN, verbose)
    com = hf["com"]
    vol = float(hf["volume"])
    va = vertex_areas(V, F)
    R = {"V": V, "F": F, "n_dup": n_dup, "stats": stats, "vol_op": vol_op, "vol": vol, "area": area, "VN": VN,
         "box": box, "dims": dims, "com": com, "hf": hf, "va": va}
    R["mass"] = RHO * vol
    # 実効重力の大きさ・ジオポテンシャル高度
    ge = np.linalg.norm(hf["eff_acceleration"], axis=1)
    g0 = np.linalg.norm(hf["acceleration"], axis=1)
    R["geff"] = ge
    R["g_nospin"] = g0
    R["g_ref"] = float(np.sum(ge * va) / np.sum(va))
    phi = hf["eff_potential"]
    R["height"] = (phi - phi.min()) / R["g_ref"]
    R["centrifugal_frac"] = float(np.max(OMEGA ** 2 * np.linalg.norm((V - com)[:, :2], axis=1) / g0))
    # 歩く道: y = 0 の断面(長軸と自転軸を含む面)
    R["path"] = walk_path(V, F)
    # 着陸点の推定位置
    sites = {}
    for name, ((la0, la1), (lo0, lo1)) in TD_SITES.items():
        k = site_vertex(V, 0.5 * (la0 + la1), 0.5 * (lo0 + lo1))
        sites[name] = {"k": k, "height": float(R["height"][k]),
                       "pct": float(np.sum(va[R["height"] < R["height"][k]]) / np.sum(va) * 100.0),
                       "slope": float(hf["slope_deg"][k]), "geff": float(ge[k])}
    R["sites"] = sites
    R["grains"] = grains(V, F, phi, VN)
    R["limit"] = two_density(R)
    R["chunks"] = tetra_chunks(V, F, com)
    return R


def walk_path(V, F):
    """長軸と自転軸を含む断面 y = 0 の輪郭(mesh_slice_contours)を、最寄りの頂点の列にする。"""
    Vr = np.stack([V[:, 0], V[:, 2], -V[:, 1]], axis=1)          # 新しい z = −y(右手系の回転)
    tab = L.mesh_slice_contours((Vr, F), 0.0)
    ring = np.asarray(tab["ring"])
    rid = int(np.bincount(ring.astype(int)).argmax())
    pts2 = np.stack([np.asarray(tab["x"])[ring == rid], np.asarray(tab["y"])[ring == rid]], axis=1)
    pts = np.stack([pts2[:, 0], np.zeros(len(pts2)), pts2[:, 1]], axis=1)   # (x, y=0, z)
    d2 = ((pts[:, None, :] - V[None, :, :]) ** 2).sum(axis=2)
    idx = np.argmin(d2, axis=1)
    seq = [int(idx[0])]
    for k in idx[1:]:
        if int(k) != seq[-1]:
            seq.append(int(k))
    if seq[0] == seq[-1]:
        seq.pop()
    seq = np.array(seq)
    start = int(np.argmax(V[seq, 0]))                              # +x の端(頭の先)から歩き出す
    seq = np.roll(seq, -start)
    seq = np.append(seq, seq[0])                                   # 1 周して戻る
    step = np.linalg.norm(np.diff(V[seq], axis=0), axis=1)
    return {"idx": seq, "s": np.concatenate([[0.0], np.cumsum(step)]), "n_contour": int(len(pts2))}


def grains(V, F, phi, VN, n=1500, iters=(0, 2, 5, 10, 20, 40, 80), seed=7):
    """表面に撒いた粒が、実効ポテンシャル(op の値)の低い隣の頂点へ移り続ける(頂点の隣接で最急降下)。"""
    rng = np.random.default_rng(seed)
    nb, st = neighbors(F, len(V))
    best = np.arange(len(V))
    for v in range(len(V)):
        cand = nb[st[v]:st[v + 1]]
        j = cand[np.argmin(phi[cand])]
        if phi[j] < phi[v]:
            best[v] = j
    pos = rng.choice(len(V), size=n, replace=False)
    frames = {}
    cur = pos.copy()
    for it in range(max(iters) + 1):
        if it in iters:
            frames[it] = cur.copy()
        cur = best[cur]
    sinks = np.flatnonzero(best == np.arange(len(V)))
    return {"start": pos, "frames": frames, "iters": iters, "final": frames[max(iters)], "n_sinks": int(sinks.size),
            "sinks": sinks}


def two_density(R):
    """頭(x ≥ 150 m)と胴で密度が違うとき: 重ね合わせ ρ_胴·(全体) + (ρ_頭 − ρ_胴)·(頭) で重心と表面の重力。"""
    hf, V = R["hf"], R["V"]
    vol, vh = R["vol"], float(hf["head_volume"])
    cw, ch = R["com"], hf["head_com"]
    accW_unit = hf["acceleration"] / RHO
    accH_unit = hf["head_acc_unit"]
    s = np.linspace(0.0, 1.0, 81)
    rho_h = LOWRY_RHO_MEAN + s * (LOWRY_RHO_HEAD - LOWRY_RHO_MEAN)
    rho_b = (LOWRY_RHO_MEAN * vol - rho_h * vh) / (vol - vh)
    M = rho_b * vol + (rho_h - rho_b) * vh
    com = (rho_b[:, None] * vol * cw + (rho_h - rho_b)[:, None] * vh * ch) / M[:, None]

    def geff(rb, rh, c):
        acc = rb * accW_unit + (rh - rb) * accH_unit
        d = V - c
        perp = d.copy()
        perp[:, 2] = 0.0
        return np.linalg.norm(acc + OMEGA ** 2 * perp, axis=1)

    g_uni = geff(LOWRY_RHO_MEAN, LOWRY_RHO_MEAN, cw)
    g_two = geff(rho_b[-1], rho_h[-1], com[-1])
    return {"s": s, "rho_h": rho_h, "rho_b": rho_b, "M": M, "com": com, "vh": vh, "head_frac": vh / vol,
            "dcom": com - cw, "g_uni": g_uni, "g_two": g_two, "dg_pct": (g_two / g_uni - 1.0) * 100.0}


def tetra_chunks(V, F, c):
    """面を重心まわりの方位角で N_CHUNK 個の塊に分け、塊ごとに符号付き四面体の体積を足す。"""
    cen = V[F].mean(axis=1) - c
    az = np.arctan2(cen[:, 1], cen[:, 0])
    order = np.argsort(az, kind="stable")
    groups = np.array_split(order, N_CHUNK)
    a, b, d = V[F[:, 0]] - c, V[F[:, 1]] - c, V[F[:, 2]] - c
    vol6 = np.einsum("ij,ij->i", a, np.cross(b, d))
    vols = vol6 / 6.0
    return {"groups": groups, "vols": vols, "chunk_pos": np.array([vols[g][vols[g] > 0].sum() for g in groups]),
            "chunk_neg": np.array([vols[g][vols[g] < 0].sum() for g in groups]), "neg_faces": int(np.sum(vols < 0))}


# --------------------------------------------------------------------------- #
# 門(理論の線 = 門の値)                                                        #
# --------------------------------------------------------------------------- #
def _box_mesh(a, b, c):
    V = np.array([[x, y, z] for x in (0, a) for y in (0, b) for z in (0, c)], float)
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    F = []
    for q in quads:
        F += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    return V, np.array(F)


def _box_quadrature(P, a, b, c, n=40):
    """直方体の重力を Gauss–Legendre の 3 重求積で(多面体の式とは別の経路)。G = ρ = 1。"""
    x, w = np.polynomial.legendre.leggauss(n)
    X, Y, Z = (x + 1) / 2 * a, (x + 1) / 2 * b, (x + 1) / 2 * c
    W = np.einsum("i,j,k->ijk", w, w, w) * a * b * c / 8.0
    XX, YY, ZZ = np.meshgrid(X, Y, Z, indexing="ij")
    d = np.stack([XX - P[0], YY - P[1], ZZ - P[2]], -1)
    r = np.linalg.norm(d, axis=-1)
    return -(W / r).sum(), (W[..., None] * d / r[..., None] ** 3).sum(axis=(0, 1, 2))


def gates(R) -> dict:
    """門の値。テストもこの関数の値を見る(重い全頂点の計算は compute 済みの R を使う)。"""
    g = {}
    V, F, hf = R["V"], R["F"], R["hf"]
    st = R["stats"]
    g["boundary_edges"] = int(st["boundary_edges"])
    g["non_manifold_edges"] = int(st["non_manifold_edges"])
    g["volume_op_vs_polygrav"] = abs(R["vol_op"] - R["vol"]) / R["vol"]
    g["volume_vs_published"] = R["vol"] / PUB_VOLUME - 1.0
    g["dims"] = [float(x) for x in R["dims"]]
    g["dims_vs_published"] = [float(R["dims"][k] / PUB_DIMS[k] - 1.0) for k in range(3)]
    g["mass"] = R["mass"]
    g["mass_vs_fujiwara"] = R["mass"] / PUB_MASS_F - 1.0
    g["bulk_density_from_abe_mass"] = PUB_MASS_A / R["vol"]
    # 球: geodesic_dome(周波数 16、5,120 面)の遠くの重力 = 点質量(体積は多面体のもの)
    Vs, Fs = L.geodesic_dome(16, radius=100.0)
    sph = pg.polyhedron_gravity((Vs, Fs), [[0.0, 0.0, 2000.0], [1000.0, 700.0, -400.0], [10.0, 20.0, 5.0]],
                                density=1.0, G=1.0)
    rr = np.linalg.norm(np.array([[0.0, 0.0, 2000.0], [1000.0, 700.0, -400.0]]), axis=1)
    pm = sph["mass"] / rr ** 2
    g["sphere_far_rel"] = float(np.max(np.abs(np.linalg.norm(sph["acceleration"][:2], axis=1) - pm) / pm))
    g["sphere_far_pot_rel"] = float(np.max(np.abs(-sph["potential"][:2] - sph["mass"] / rr) / (sph["mass"] / rr)))
    r_in = np.linalg.norm([10.0, 20.0, 5.0])                    # 中: 一様な球なら g = (4/3)πGρ r(多面体なので近似)
    g["sphere_inside_rel"] = float(abs(np.linalg.norm(sph["acceleration"][2]) / (4.0 / 3.0 * math.pi * r_in) - 1.0))
    # 直方体と求積(別の経路)
    Vb, Fb = _box_mesh(2.0, 1.0, 0.5)
    P = np.array([5.0, 3.0, 2.0])
    bx = pg.polyhedron_gravity((Vb, Fb), P[None, :], density=1.0, G=1.0)
    Uq, gq = _box_quadrature(P, 2.0, 1.0, 0.5)
    g["box_vs_quadrature_pot"] = float(abs(bx["potential"][0] - Uq) / abs(Uq))
    g["box_vs_quadrature_acc"] = float(np.max(np.abs(bx["acceleration"][0] - gq)) / np.linalg.norm(gq))
    # イトカワ: 中と外の発散(立体角の和)と、差分の発散・勾配(別の経路)
    com = R["com"]
    P_in = com.copy()
    P_out = np.array([0.0, 0.0, 600.0])
    h = 0.05
    pts = [P_in, P_out]
    for base in (P_in, P_out):
        for k in range(3):
            e = np.zeros(3)
            e[k] = h
            pts += [base + e, base - e]
    G1 = pg.polyhedron_gravity((V, F), np.array(pts), density=RHO)
    lim = 4.0 * math.pi * pg.G_NEWTON * RHO
    g["div_inside_rel"] = float(abs(G1["div_g"][0] / -lim - 1.0))
    g["div_outside_abs_over_4piGrho"] = float(abs(G1["div_g"][1]) / lim)
    acc = G1["acceleration"]
    pot = G1["potential"]
    fd_div, fd_grad = [], []
    for j, base_i in enumerate((0, 1)):
        o = 2 + 6 * j
        fd_div.append(sum((acc[o + 2 * k][k] - acc[o + 2 * k + 1][k]) / (2 * h) for k in range(3)))
        fd_grad.append(np.array([-(pot[o + 2 * k] - pot[o + 2 * k + 1]) / (2 * h) for k in range(3)]))
    g["fd_div_inside_rel"] = float(abs(fd_div[0] / -lim - 1.0))
    g["fd_div_outside_over_4piGrho"] = float(abs(fd_div[1]) / lim)
    g["fd_grad_rel"] = float(max(np.linalg.norm(fd_grad[j] - acc[j]) / np.linalg.norm(acc[j]) for j in range(2)))
    # イトカワの遠く(100 km)= 点質量
    far = np.array([[1.0e5, 0.0, 0.0], [0.0, 1.0e5, 0.0], [0.0, 0.0, 1.0e5]])
    Gf = pg.polyhedron_gravity((V, F), far, density=RHO)
    gm = pg.G_NEWTON * R["mass"] / np.linalg.norm(far - com, axis=1) ** 2
    g["itokawa_far_rel"] = float(np.max(np.abs(np.linalg.norm(Gf["acceleration"], axis=1) / gm - 1.0)))
    # 表面の重力
    ge = R["geff"]
    g["geff_min_um"], g["geff_max_um"] = float(ge.min() * 1e6), float(ge.max() * 1e6)
    g["geff_ratio"] = float(ge.max() / ge.min())
    g["g_ref_um"] = R["g_ref"] * 1e6
    g["centrifugal_frac_max"] = R["centrifugal_frac"]
    g["slope_mean_deg"] = float(np.sum(hf["slope_deg"] * R["va"]) / np.sum(R["va"]))
    g["slope_max_deg"] = float(hf["slope_deg"].max())
    g["slope_frac_over_30"] = float(np.sum(R["va"][hf["slope_deg"] > 30.0]) / np.sum(R["va"]))
    # 歩く道: 端と首の重さ
    p = R["path"]
    gp = ge[p["idx"]]
    g["path_geff_min_um"], g["path_geff_max_um"] = float(gp.min() * 1e6), float(gp.max() * 1e6)
    xp = V[p["idx"], 0]
    g["path_geff_at_ends_um"] = float(ge[p["idx"][np.argmax(np.abs(xp - com[0]))]] * 1e6)
    # 頭と胴に切った 2 つの和 = 全体(切る op の検算)
    hV, hF = hf["head_V"], hf["head_F"]
    body = pg.polyhedron_clip_halfspace((V, F), [LOWRY_X_CUT, 0.0, 0.0], [-1.0, 0.0, 0.0])
    probe = np.array([[0.0, 0.0, 400.0], [LOWRY_X_CUT, 10.0, 0.0], com, [600.0, 50.0, -30.0]])
    a_w = pg.polyhedron_gravity((V, F), probe, density=1.0)
    a_h = pg.polyhedron_gravity((hV, hF), probe, density=1.0)
    a_b = pg.polyhedron_gravity(body, probe, density=1.0)
    g["split_volume_rel"] = float(abs(a_h["volume"] + a_b["volume"] - a_w["volume"]) / a_w["volume"])
    g["split_acc_rel"] = float(np.max(np.abs(a_h["acceleration"] + a_b["acceleration"] - a_w["acceleration"]))
                               / np.max(np.abs(a_w["acceleration"])))
    lm = R["limit"]
    g["head_frac"] = float(lm["head_frac"])
    g["lowry_rho_body_ours"] = float(lm["rho_b"][-1])
    g["mass_conserved_rel"] = float(np.max(np.abs(lm["M"] / (LOWRY_RHO_MEAN * R["vol"]) - 1.0)))
    g["com_offset_two_density_m"] = float(np.linalg.norm(lm["dcom"][-1]))
    g["com_offset_x_two_density_m"] = float(lm["dcom"][-1][0])
    g["com_offset_uniform_m"] = 0.0
    g["dg_pct_min"], g["dg_pct_max"] = float(lm["dg_pct"].min()), float(lm["dg_pct"].max())
    g["com_vs_origin_m"] = float(np.linalg.norm(com))
    # ミューゼスの海
    g["sites"] = R["sites"]
    gr = R["grains"]
    hgt = R["height"]
    low20 = np.quantile(hgt, 0.2)
    g["grains_in_low20_start"] = float(np.mean(hgt[gr["start"]] <= low20))
    g["grains_in_low20_end"] = float(np.mean(hgt[gr["final"]] <= low20))
    g["grains_height_start_m"] = float(np.mean(hgt[gr["start"]]))
    g["grains_height_end_m"] = float(np.mean(hgt[gr["final"]]))
    g["height_max_m"] = float(hgt.max())
    # 数学: 符号付き四面体の和
    ch = R["chunks"]
    g["tetra_sum_vs_mesh_volume"] = float(abs(ch["vols"].sum() - R["vol_op"]) / R["vol_op"])
    apex2 = np.array([1000.0, -700.0, 300.0])                   # 天体の外の頂点でも同じ体積
    a, b, d = V[F[:, 0]] - apex2, V[F[:, 1]] - apex2, V[F[:, 2]] - apex2
    g["tetra_apex_outside_rel"] = float(abs(np.einsum("ij,ij->i", a, np.cross(b, d)).sum() / 6.0 - R["vol_op"]) / R["vol_op"])
    g["tetra_neg_faces"] = ch["neg_faces"]
    g["tetra_neg_frac"] = float(-ch["vols"][ch["vols"] < 0].sum() / R["vol_op"])
    return g


# --------------------------------------------------------------------------- #
# 3-D の部品                                                                  #
# --------------------------------------------------------------------------- #
def quat_z(a):
    return np.array([math.cos(a / 2), 0.0, 0.0, math.sin(a / 2)])


def quat_from_z(d):
    """+z を単位ベクトル d に向ける四元数 (w, x, y, z)。"""
    d = np.asarray(d, float) / np.linalg.norm(d)
    z = np.array([0.0, 0.0, 1.0])
    c = float(z @ d)
    if c < -1 + 1e-12:
        return np.array([0.0, 1.0, 0.0, 0.0])
    ax = np.cross(z, d)
    q = np.array([1.0 + c, ax[0], ax[1], ax[2]])
    return q / np.linalg.norm(q)


def arrow_mesh(length=40.0, r=2.2):
    n = 10
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring = np.stack([np.cos(th), np.sin(th)], 1)
    shaft = 0.72 * length
    pts = [np.c_[ring * r, np.zeros(n)], np.c_[ring * r, np.full(n, shaft)], np.c_[ring * r * 2.6, np.full(n, shaft)],
           np.array([[0.0, 0.0, length]]), np.array([[0.0, 0.0, 0.0]])]
    V = np.concatenate(pts)
    F = []
    for i in range(n):
        j = (i + 1) % n
        F += [[i, j, n + j], [i, n + j, n + i]]
        F += [[2 * n + i, 2 * n + j, 3 * n]]
        F += [[3 * n + 1, j, i]]
        F += [[n + i, n + j, 2 * n + j], [n + i, 2 * n + j, 2 * n + i]]
    return V, np.array(F)


def box_mesh_centered(ext):
    V = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float) * np.asarray(ext)
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    F = []
    for q in quads:
        F += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    return V, np.array(F)


def rod_mesh(length, r=1.5, n=8):
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring = np.stack([np.cos(th), np.sin(th)], 1) * r
    V = np.concatenate([np.c_[ring, np.full(n, -length / 2)], np.c_[ring, np.full(n, length / 2)]])
    F = []
    for i in range(n):
        j = (i + 1) % n
        F += [[i, j, n + j], [i, n + j, n + i]]
    return V, np.array(F)


def ball_mesh(r):
    Vs, Fs = L.geodesic_dome(2, radius=r)
    return np.asarray(Vs), np.asarray(Fs)


def static(T, B, xyz_list, quat_list=None):
    xyz = np.zeros((T, B, 3))
    quat = np.zeros((T, B, 4))
    quat[..., 0] = 1.0
    for b, p in enumerate(xyz_list):
        xyz[:, b] = p
    if quat_list is not None:
        for b, q in enumerate(quat_list):
            if q is not None:
                quat[:, b] = q
    return xyz, quat


def _e(x):
    return "0" if x == 0 else "%.1e" % x


def _row(what_ja, what_en, criterion, result, ok):
    return {"what": T(what_ja, what_en), "criterion": criterion, "result": result, "ok": bool(ok)}


# --------------------------------------------------------------------------- #
# タブ                                                                        #
# --------------------------------------------------------------------------- #
def tab_shape(R, g):
    V, F, com = R["V"], R["F"], R["com"]
    pos = V - com
    nT = 97
    hours = np.linspace(0.0, PERIOD_H, nT)
    t = np.linspace(0.0, 12.0, nT)
    ang = OMEGA * hours * 3600.0
    box = R["box"]
    axes = np.asarray(box["axes"])
    if np.linalg.det(axes) < 0:
        axes = axes.copy()
        axes[:, 2] *= -1
    bV, bF = box_mesh_centered(np.asarray(box["extents"]))
    bV = bV @ axes.T + (np.asarray(box["center"]) - com)
    rV, rF = rod_mesh(420.0, r=1.6)
    bodies = [{"name": "itokawa", "pos": pos, "faces": F, "rgb": ROCK_RGB,
               "label": T("イトカワ(Gaskell の形、49,152 面)", "Itokawa (Gaskell shape, 49,152 faces)")},
              {"name": "obb", "pos": bV, "faces": bF, "rgb": (0.55, 0.80, 1.0), "alpha": 0.16,
               "label": T("obb の箱(主軸の向きの外接箱)", "obb box (bounding box on the principal axes)")},
              {"name": "spin_axis", "pos": rV, "faces": rF, "rgb": (1.0, 0.84, 0.31),
               "label": T("自転軸(z、重心を通る)", "spin axis (z, through the centre of mass)")}]
    xyz, quat = static(nT, 3, [com, com, com])
    for k in range(nT):
        q = quat_z(ang[k])
        quat[k, 0] = q
        quat[k, 1] = q
    events = [{"t": float(t[int(round(f * (nT - 1)))]), "label": T(lab_ja, lab_en)}
              for f, lab_ja, lab_en in ((0.25, "1/4 周(%.2f 時間)" % (PERIOD_H / 4), "quarter turn (%.2f h)" % (PERIOD_H / 4)),
                                        (0.5, "半周(%.2f 時間)" % (PERIOD_H / 2), "half turn (%.2f h)" % (PERIOD_H / 2)),
                                        (1.0, "1 周 = %.2f 時間" % PERIOD_H, "one turn = %.2f h" % PERIOD_H))]
    d = {"t": t, "bodies": bodies, "xyz": xyz, "quat": quat, "events": events,
         "axis": {"values": hours, "segments": [{"k": 0, "label": T("自転の時刻", "time in the spin"), "unit": " h", "decimals": 2}]}}
    return d


def tab_gravity(R, g):
    V, F, com, hf = R["V"], R["F"], R["com"], R["hf"]
    p = R["path"]
    idx = p["idx"]
    nT = len(idx)
    t = np.arange(nT) / 12.0
    VN = R["VN"]
    ge = R["geff"]
    gvec = hf["eff_acceleration"]
    walker_V, walker_F = ball_mesh(5.0)
    aV, aF = arrow_mesh(45.0, 2.0)
    bodies = [{"name": "itokawa", "pos": V - com, "faces": F, "val": ge * 1e6,
               "label": T("実効重力の大きさ |g_eff|", "effective gravity |g_eff|")},
              {"name": "walker", "pos": walker_V, "faces": walker_F, "rgb": (1.0, 1.0, 1.0),
               "label": T("歩く人", "walker")},
              {"name": "arrow", "pos": aV, "faces": aF, "rgb": (1.0, 0.84, 0.31),
               "label": T("その場所の実効重力の向き", "direction of effective gravity there")}]
    xyz, quat = static(nT, 3, [com, np.zeros(3), np.zeros(3)])
    for k, v in enumerate(idx):
        base = V[v] + VN[v] * 5.5
        xyz[k, 1] = base
        dirn = gvec[v] / np.linalg.norm(gvec[v])
        xyz[k, 2] = base - dirn * 50.0                       # 矢印の先が人に刺さる(上から押す向き)
        quat[k, 2] = quat_from_z(dirn)
    s = p["s"]
    lo_g = math.floor(g["geff_min_um"] / 5.0) * 5.0
    hi_g = math.ceil(g["geff_max_um"] / 5.0) * 5.0
    series = [{"label": T("実効重力の大きさ |g_eff|(歩く道の上)", "effective gravity |g_eff| (along the path)"),
               "color": "#ffd54f", "values": ge[idx] * 1e6, "lo": lo_g, "hi": hi_g, "unit": " µm/s²", "decimals": 1},
              {"label": T("斜面の角(実効重力と −法線のなす角)", "slope (angle between g_eff and −normal)"),
               "color": "#4fc3f7", "values": hf["slope_deg"][idx], "lo": 0.0, "hi": 60.0, "unit": "°", "decimals": 1,
               "threshold": 35.0}]
    # 段: 端と首(歩く道の上で重心からの x の最大・最小、首 = |g_eff| の最大)
    xs = V[idx, 0] - com[0]
    k_far = int(np.argmax(xs))
    k_far2 = int(np.argmin(xs))
    k_gmax = int(np.argmax(ge[idx]))
    events = sorted([(t[k_far], T("頭の先(+x の端)", "tip of the head (+x end)")),
                     (t[k_gmax], T("|g_eff| が最大", "largest |g_eff|")),
                     (t[k_far2], T("胴の端(−x の端)", "end of the body (−x end)"))], key=lambda e: e[0])
    cbar = {"lo": lo_g, "hi": hi_g, "unit": "µm/s²", "cmap": "seq", "label": T("実効重力 |g_eff|", "effective gravity |g_eff|")}
    trails = [{"body": "walker", "color": "#ffffff", "tail": 0.0, "label": T("歩いた道(y = 0 の断面)", "path walked (section y = 0)")}]
    return {"t": t, "bodies": bodies, "xyz": xyz, "quat": quat, "series": series, "cbar": cbar, "trails": trails,
            "events": [{"t": float(a), "label": b} for a, b in events],
            "axis": {"values": s, "segments": [{"k": 0, "label": T("歩いた距離", "distance walked"), "unit": " m", "decimals": 0}]}}


def tab_muses(R, g):
    V, F, com, hf = R["V"], R["F"], R["com"], R["hf"]
    VN = R["VN"]
    hgt = R["height"]
    gr = R["grains"]
    iters = list(gr["iters"])
    per = 12
    nT = per * len(iters) + per
    t = np.arange(nT) / 12.0
    # ポテンシャルの高さの地形: 重心から放射方向に高さを誇張して並べる(右に置く)
    scale = 60.0 / max(float(hgt.max()), 1e-9)
    radial = (V - com) / np.linalg.norm(V - com, axis=1)[:, None]
    relief = (V - com) + radial * (hgt * scale)[:, None]
    shift = np.array([0.0, 420.0, 0.0])
    bodies = [{"name": "itokawa", "pos": V - com, "faces": F, "val": hgt,
               "label": T("ジオポテンシャル高度(実効ポテンシャル ÷ 平均の重力)", "geopotential height (effective potential ÷ mean gravity)")},
              {"name": "relief", "pos": relief, "faces": F, "val": hgt,
               "label": T("高さを %.0f 倍にした地形(右)" % scale, "the same heights exaggerated %.0f× (right)" % scale)}]
    marks = []
    for name in ("TD1", "TD2"):
        k = R["sites"][name]["k"]
        mV, mF = ball_mesh(7.0)
        bodies.append({"name": name, "pos": mV, "faces": mF, "rgb": (1.0, 0.35, 0.35),
                       "label": T("着陸点の推定(%s、Yano & Aida 2013)" % name, "estimated touchdown site (%s, Yano & Aida 2013)" % name)})
        marks.append(V[k] + VN[k] * 7.0)
    xyz, quat = static(nT, len(bodies), [com, com + shift] + marks)
    clouds = []
    for j, it in enumerate(iters):
        vv = gr["frames"][it]
        pts = V[vv] + VN[vv] * 2.5
        clouds.append({"k": j * per, "pos": pts, "color": "#ffffff", "point_size": 3.2})
    events = [{"t": float(t[j * per]), "label": T("%d 歩" % it, "%d steps" % it)} for j, it in enumerate(iters) if it in (0, 10, 80)]
    hmax = float(np.ceil(hgt.max()))
    cbar = {"lo": 0.0, "hi": hmax, "unit": "m", "cmap": "seq", "label": T("高さ(低い = 粒が集まる)", "height (low = grains gather)")}
    mean_h = np.array([float(np.mean(hgt[gr["frames"][iters[min(k // per, len(iters) - 1)]]])) for k in range(nT)])
    series = [{"label": T("粒の高さの平均", "mean height of the grains"), "color": "#ffffff", "values": mean_h,
               "lo": 0.0, "hi": float(np.ceil(g["grains_height_start_m"] * 1.3)), "unit": " m", "decimals": 1}]
    axis_vals = np.array([float(iters[min(k // per, len(iters) - 1)]) for k in range(nT)])
    return {"t": t, "bodies": bodies, "xyz": xyz, "quat": quat, "clouds": clouds, "events": events, "cbar": cbar,
            "series": series,
            "axis": {"values": axis_vals, "segments": [{"k": 0, "label": T("粒が坂を下った歩数", "downhill steps taken by the grains"), "unit": "", "decimals": 0}]}}


def tab_limit(R, g):
    V, F, com = R["V"], R["F"], R["com"]
    lm = R["limit"]
    nT = len(lm["s"])
    t = np.arange(nT) / 10.0
    cfV, cfF = ball_mesh(6.0)
    cmV, cmF = ball_mesh(7.5)
    pV, pF = box_mesh_centered((0.6, 190.0, 150.0))
    bodies = [{"name": "itokawa", "pos": V - com, "faces": F, "val": lm["dg_pct"], "alpha": 0.45,
               "label": T("|g_eff| の変化(2 密度 ÷ 一様 − 1)", "change in |g_eff| (two densities ÷ uniform − 1)")},
              {"name": "cof", "pos": cfV, "faces": cfF, "rgb": (1.0, 1.0, 1.0),
               "label": T("形の中心(一様密度の重心)", "centre of figure (uniform-density centre of mass)")},
              {"name": "com", "pos": cmV, "faces": cmF, "rgb": (1.0, 0.6, 0.2),
               "label": T("重心(頭を重くしていく)", "centre of mass (head made denser)")},
              {"name": "cut", "pos": pV, "faces": pF, "rgb": (0.55, 0.80, 1.0), "alpha": 0.22,
               "label": T("頭と胴の境 x = 150 m(Lowry 2014)", "head / body boundary x = 150 m (Lowry 2014)")}]
    xyz, quat = static(nT, 4, [com, com, com, np.array([LOWRY_X_CUT, 0.0, 0.0])])
    xyz[:, 2] = lm["com"]
    span = max(abs(g["dg_pct_min"]), abs(g["dg_pct_max"]))
    span = math.ceil(span)
    cbar = {"lo": -span, "hi": span, "unit": "%", "cmap": "div",
            "label": T("|g_eff| の変化(頭 2,850 / 胴 %.0f kg/m³)" % lm["rho_b"][-1], "change in |g_eff| (head 2,850 / body %.0f kg/m³)" % lm["rho_b"][-1])}
    dcx = lm["dcom"][:, 0]
    series = [{"label": T("重心のずれ(x、頭の側が正)", "centre-of-mass shift (x, towards the head)"), "color": "#ff9800",
               "values": dcx, "lo": 0.0, "hi": 40.0, "unit": " m", "decimals": 1, "threshold": LOWRY_COM_X},
              {"label": T("胴の密度(全体の質量を保つ)", "body density (total mass kept)"), "color": "#4fc3f7",
               "values": lm["rho_b"], "lo": 1600.0, "hi": 2000.0, "unit": " kg/m³", "decimals": 0}]
    trails = [{"body": "com", "color": "#ff9800", "tail": 0.0, "label": T("重心の動き", "path of the centre of mass")}]
    return {"t": t, "bodies": bodies, "xyz": xyz, "quat": quat, "cbar": cbar, "series": series, "trails": trails,
            "events": [{"t": float(t[-1]), "label": T("Lowry 2014 の密度", "Lowry 2014 densities")}],
            "axis": {"values": lm["rho_h"], "segments": [{"k": 0, "label": T("頭の密度 ρ_頭", "head density ρ_head"), "unit": " kg/m³", "decimals": 0}]}}


def tab_math(R, g):
    V, F, com = R["V"], R["F"], R["com"]
    ch = R["chunks"]
    vols = ch["vols"]
    per = 6
    nT = per * N_CHUNK + per * 2
    t = np.arange(nT) / 12.0
    bodies = []
    homes, dirs = [], []
    for j, grp in enumerate(ch["groups"]):
        for sign, rgb, nm in ((1, (0.62, 0.80, 0.55), "pos"), (-1, (0.95, 0.35, 0.35), "neg")):
            sel = grp[(vols[grp] > 0) if sign > 0 else (vols[grp] < 0)]
            if sel.size == 0:
                continue
            used = np.unique(F[sel])
            remap = -np.ones(len(V), dtype=np.int64)
            remap[used] = np.arange(used.size)
            pos = V[used] - com
            bodies.append({"name": "c%02d%s" % (j, nm), "pos": pos, "faces": remap[F[sel]], "rgb": rgb})
            cen = (V[F[grp]].mean(axis=(0, 1)) - com)
            cen[2] = 0.0
            dirs.append((j, cen / max(np.linalg.norm(cen), 1e-9)))
    B = len(bodies)
    xyz = np.zeros((nT, B, 3))
    quat = np.zeros((nT, B, 4))
    quat[..., 0] = 1.0
    for b, (j, dvec) in enumerate(dirs):
        k0 = per * (j + 1)
        for k in range(nT):
            f = min(max((k - (k0 - per)) / per, 0.0), 1.0)
            f = 0.5 - 0.5 * math.cos(math.pi * f)
            xyz[k, b] = com + dvec * 380.0 * (1.0 - f)
    cum = np.zeros(nT)
    cneg = np.zeros(nT)
    tot = vols.sum()
    for k in range(nT):
        n_in = min(max(k // per, 0), N_CHUNK)
        cum[k] = (ch["chunk_pos"][:n_in].sum() + ch["chunk_neg"][:n_in].sum()) / tot * 100.0
        cneg[k] = -ch["chunk_neg"][:n_in].sum() / tot * 100.0
    faces_in = np.array([sum(len(gp) for gp in ch["groups"][:min(k // per, N_CHUNK)]) for k in range(nT)], float)
    series = [{"label": T("足した四面体の体積の和 ÷ 全体", "sum of signed tetrahedra so far ÷ total"), "color": "#9ccc65",
               "values": cum, "lo": 0.0, "hi": 110.0, "unit": " %", "decimals": 2, "threshold": 100.0},
              {"label": T("そのうち負の体積(内向きの面)", "of which negative volume (inward-facing faces)"), "color": "#ef5350",
               "values": cneg, "lo": 0.0, "hi": 10.0, "unit": " %", "decimals": 2}]
    return {"t": t, "bodies": bodies, "xyz": xyz, "quat": quat, "series": series,
            "events": [{"t": float(t[per * N_CHUNK]), "label": T("全部の面を足した", "all faces added")}],
            "axis": {"values": faces_in, "segments": [{"k": 0, "label": T("足した面の数", "faces added"), "unit": "", "decimals": 0}]}}


# --------------------------------------------------------------------------- #
# checks / lesson / 文                                                         #
# --------------------------------------------------------------------------- #
def all_checks(R, g):
    s1, s2 = g["sites"]["TD1"], g["sites"]["TD2"]
    dv = g["volume_vs_published"]
    dm = g["mass_vs_fujiwara"]
    dd = g["dims_vs_published"]
    rb = g["lowry_rho_body_ours"]
    cx = g["com_offset_x_two_density_m"]
    return {
        "shape": [
            _row("閉じた曲面(mesh_edge_stats: 境界の辺・3 面以上が接する辺)", "closed surface (mesh_edge_stats: boundary / non-manifold edges)",
                 "0 / 0", "%d / %d" % (g["boundary_edges"], g["non_manifold_edges"]),
                 g["boundary_edges"] == 0 and g["non_manifold_edges"] == 0),
            _row("体積: mesh_volume と polyhedron_gravity(別の実装)", "volume: mesh_volume vs polyhedron_gravity (separate code)",
                 "< 1e-12", _e(g["volume_op_vs_polygrav"]), g["volume_op_vs_polygrav"] < 1e-12),
            _row("体積と公表値 0.018378 km³(Demura 2006、± 5 %)", "volume vs published 0.018378 km³ (Demura 2006, ± 5 %)",
                 "|差| < 5 %", "%+.1f %%" % (dv * 100), abs(dv) < PUB_VOLUME_REL),
            _row("質量 = 体積 × 1.9 g/cm³ と 3.51 × 10^10 kg(Fujiwara 2006。密度の幅 ± 7 %)",
                 "mass = volume × 1.9 g/cm³ vs 3.51 × 10^10 kg (Fujiwara 2006; density ± 7 %)",
                 "|差| < 7 %", "%+.1f %%" % (dm * 100), abs(dm) < RHO_SIGMA / RHO)],
        "gravity": [
            _row("球(geodesic_dome 5,120 面)の遠くの重力と点質量 GM/r²", "sphere (geodesic_dome, 5,120 faces) far field vs point mass GM/r²",
                 "< 1e-6", _e(g["sphere_far_rel"]), g["sphere_far_rel"] < 1e-6),
            _row("直方体: 多面体の式と Gauss–Legendre の 3 重求積(別の経路)", "box: polyhedron formula vs Gauss–Legendre triple quadrature (separate path)",
                 "< 1e-12", "%s / %s" % (_e(g["box_vs_quadrature_pot"]), _e(g["box_vs_quadrature_acc"])),
                 max(g["box_vs_quadrature_pot"], g["box_vs_quadrature_acc"]) < 1e-12),
            _row("ガウスの法則: イトカワの中で ∇·g = −4πGρ(立体角の和)", "Gauss's law: ∇·g = −4πGρ inside Itokawa (sum of solid angles)",
                 "< 1e-12", _e(g["div_inside_rel"]), g["div_inside_rel"] < 1e-12),
            _row("ガウスの法則: 外で ∇·g = 0", "Gauss's law: ∇·g = 0 outside", "< 1e-12", _e(g["div_outside_abs_over_4piGrho"]),
                 g["div_outside_abs_over_4piGrho"] < 1e-12),
            _row("発散の差分(5 cm 刻みの中心差分。立体角を使わない経路): 中 / 外", "finite-difference divergence (5 cm central differences, no solid angles): inside / outside",
                 "< 1e-6", "%s / %s" % (_e(g["fd_div_inside_rel"]), _e(g["fd_div_outside_over_4piGrho"])),
                 max(g["fd_div_inside_rel"], g["fd_div_outside_over_4piGrho"]) < 1e-6),
            _row("加速度 = −(ポテンシャルの差分の勾配)", "acceleration = −(finite-difference gradient of the potential)",
                 "< 1e-7", _e(g["fd_grad_rel"]), g["fd_grad_rel"] < 1e-7),
            _row("イトカワの 100 km 先の重力と点質量", "Itokawa at 100 km vs point mass", "< 1e-4", _e(g["itokawa_far_rel"]),
                 g["itokawa_far_rel"] < 1e-4)],
        "muses": [
            _row("粒が坂を下ると平均の高さが下がる(最初 → 80 歩)", "grains moving downhill lower their mean height (start → 80 steps)",
                 T("下がる", "lower"), "%.1f → %.1f m" % (g["grains_height_start_m"], g["grains_height_end_m"]),
                 g["grains_height_end_m"] < g["grains_height_start_m"]),
            _row("低い方から 20 % の面積に入る粒の割合(最初 → 80 歩)", "share of grains in the lowest 20 % of the area (start → 80 steps)",
                 T("増える", "rises"), "%.0f → %.0f %%" % (g["grains_in_low20_start"] * 100, g["grains_in_low20_end"] * 100),
                 g["grains_in_low20_end"] > g["grains_in_low20_start"]),
            _row("着陸点の推定 TD1(南極寄り)の高さの順位(低い方から、面積の %)", "height rank of the estimated site TD1 (near the south pole; % of area below it)",
                 "< 50 %", "%.0f %%" % s1["pct"], s1["pct"] < 50.0),
            _row("着陸点の推定 TD2(赤道寄り)の高さの順位", "height rank of the estimated site TD2 (near the equator)",
                 "< 50 %", "%.0f %%" % s2["pct"], s2["pct"] < 50.0)],
        "limit": [
            _row("頭と胴に切った 2 つ(polyhedron_clip_halfspace)の和 = 全体: 体積 / 重力", "head + body pieces (polyhedron_clip_halfspace) = whole: volume / gravity",
                 "< 1e-12", "%s / %s" % (_e(g["split_volume_rel"]), _e(g["split_acc_rel"])),
                 max(g["split_volume_rel"], g["split_acc_rel"]) < 1e-12),
            _row("密度を振っても全体の質量は 1,950 kg/m³ × 体積のまま", "total mass stays 1,950 kg/m³ × volume at every step",
                 "< 1e-12", _e(g["mass_conserved_rel"]), g["mass_conserved_rel"] < 1e-12),
            _row("頭 2,850 のとき胴の密度(この形で)と Lowry 2014 の 1,750 ± 110", "body density with the head at 2,850 (on this shape) vs Lowry 2014: 1,750 ± 110",
                 "± 110 kg/m³", "%.0f kg/m³" % rb, abs(rb - LOWRY_RHO_BODY) <= LOWRY_RHO_BODY_SIGMA),
            _row("そのときの重心のずれ(x)と Lowry 2014 の 21 ± 12 m", "centre-of-mass shift (x) then vs Lowry 2014: 21 ± 12 m",
                 "± 12 m", "%.1f m" % cx, abs(cx - LOWRY_COM_X) <= LOWRY_COM_X_SIGMA),
            _row("限界(形): 大きさ(obb の 3 辺)と 535 × 294 × 209 m(Fujiwara 2006)—— 3 軸の定義の違い",
                 "limit (shape): size (3 obb edges) vs 535 × 294 × 209 m (Fujiwara 2006) — the axes are defined differently",
                 "|差| < 10 %", "%+.1f / %+.1f / %+.1f %%" % tuple(x * 100 for x in dd), max(abs(x) for x in dd) < 0.10),
            _row("一様密度の仮定は、YORP の観測が求める重心のずれ(14 m 以上)を出せるか", "can the uniform-density assumption give the centre-of-mass shift the YORP observation needs (≥ 14 m)?",
                 "≥ 14 m", "%.0f m" % g["com_offset_uniform_m"], g["com_offset_uniform_m"] >= 14.0)],
        "math": [
            _row("符号付き四面体の和(頂点 = 重心)と mesh_volume", "sum of signed tetrahedra (apex = centre of mass) vs mesh_volume",
                 "< 1e-12", _e(g["tetra_sum_vs_mesh_volume"]), g["tetra_sum_vs_mesh_volume"] < 1e-12),
            _row("頂点を天体の外に置いても同じ体積(閉じた曲面なら頂点に依らない)", "apex outside the body gives the same volume (independent of the apex for a closed surface)",
                 "< 1e-12", _e(g["tetra_apex_outside_rel"]), g["tetra_apex_outside_rel"] < 1e-12),
            _row("負の体積の四面体(内向きの面)がある", "some tetrahedra are negative (inward-facing faces)",
                 "> 0", "%d 面 / %.2f %%" % (g["tetra_neg_faces"], g["tetra_neg_frac"] * 100), g["tetra_neg_faces"] > 0)],
    }


def all_lessons(R, g):
    m = g["mass"]
    s1, s2 = g["sites"]["TD1"], g["sites"]["TD2"]
    gr_ratio = g["geff_ratio"]
    return {
        "shape": {
            "question": T("イトカワの体積(この形から計算)と密度 1.9 g/cm³ から、質量はどれくらい?",
                          "From Itokawa's volume (computed from this shape) and a density of 1.9 g/cm³, how heavy is it?"),
            "choices": [T("%.1f × 10^7 kg" % (m / 1e10), "%.1f × 10^7 kg" % (m / 1e10)),
                        T("%.1f × 10^10 kg" % (m / 1e10), "%.1f × 10^10 kg" % (m / 1e10)),
                        T("%.1f × 10^13 kg" % (m / 1e10), "%.1f × 10^13 kg" % (m / 1e10))],
            "answer": 1,
            "explain": T("体積は %.3f × 10^7 m³(mesh_volume)。1.9 g/cm³ = 1,900 kg/m³ を掛けて %.2f × 10^10 kg。探査機の軌道から"
                         "測った値 3.51 × 10^10 kg(Fujiwara 2006)と %+.1f %% で合う。差は形の版と密度の幅(± 0.13)の範囲。"
                         % (R["vol"] / 1e7, m / 1e10, g["mass_vs_fujiwara"] * 100),
                         "The volume is %.3f × 10^7 m³ (mesh_volume). Times 1,900 kg/m³ gives %.2f × 10^10 kg, within %+.1f %% "
                         "of the 3.51 × 10^10 kg measured from the spacecraft's trajectory (Fujiwara 2006) — inside the "
                         "spread of the shape versions and the density (± 0.13)." % (R["vol"] / 1e7, m / 1e10, g["mass_vs_fujiwara"] * 100)),
            "formula": T("体積 V = (1/6) Σ_面 v0 · (v1 × v2)(発散定理)\n質量 M = ρ V\n空隙率 = 1 − ρ / ρ_粒(Abe 2006 は LL コンドライトの粒の密度を仮定して約 40 %)",
                         "volume V = (1/6) Σ_faces v0 · (v1 × v2) (divergence theorem)\nmass M = ρ V\n"
                         "porosity = 1 − ρ / ρ_grain (about 40 % with the LL-chondrite grain density, Abe 2006)"),
            "limit": T("形は Q = 64(49,152 面、辺の長さ 数 m)の粗い版で、数 m より細かい岩は入っていない。大きさの 535 × 294 × 209 m は"
                       "論文の 3 軸の定義と obb(頂点の主成分の向きの外接箱)が同じとは限らない。質量は密度の推定に比例し、"
                       "空隙率 40 % は隕石(LL コンドライト)の粒の密度を仮定した値(Abe 2006)。",
                       "The shape is the coarse Q = 64 version (49,152 faces, edges a few metres), so rocks smaller than a few "
                       "metres are absent. The paper's 535 × 294 × 209 m axes need not match obb (a box on the principal axes of "
                       "the vertices). The mass scales with the assumed density; the 40 % porosity assumes the grain density of "
                       "LL-chondrite meteorites (Abe 2006)."),
        },
        "gravity": {
            "question": T("イトカワの上を、頭の先から首を通って胴の端まで歩く。「重さ」(実効重力)はどこで一番軽い?",
                          "Walk over Itokawa from the tip of the head, across the neck, to the end of the body. Where do you weigh the least?"),
            "choices": [T("どこでも同じ(小さいから)", "The same everywhere (it is small)"),
                        T("両端(重心から遠く、遠心力も大きい)", "At the ends (far from the centre of mass, more centrifugal force)"),
                        T("首のくびれ(細いから)", "At the narrow neck (it is thin)")],
            "answer": 1,
            "explain": T("表面の実効重力は %.1f〜%.1f µm/s²(地球の約 10 万分の 1)で、場所によって %.1f 倍違う。重心から遠い両端ほど"
                         "引力が弱く、自転の遠心力(最大で引力の %.1f %%)も外向きに効くので軽い。60 kg の人なら、端で約 %.2f g 重、"
                         "重い所で約 %.2f g 重。"
                         % (g["geff_min_um"], g["geff_max_um"], gr_ratio, g["centrifugal_frac_max"] * 100,
                            60.0 * g["geff_min_um"] * 1e-6 / 9.80665 * 1000, 60.0 * g["geff_max_um"] * 1e-6 / 9.80665 * 1000),
                         "Surface effective gravity is %.1f–%.1f µm/s² (about 1/100,000 of Earth's) and varies %.1f× over the "
                         "surface. The ends are farthest from the centre of mass, so the pull is weakest there, and the "
                         "centrifugal term (up to %.1f %% of the pull) points outwards too. A 60 kg person weighs about %.2f g-force "
                         "at the ends and %.2f g-force at the heaviest spot."
                         % (g["geff_min_um"], g["geff_max_um"], gr_ratio, g["centrifugal_frac_max"] * 100,
                            60.0 * g["geff_min_um"] * 1e-6 / 9.80665 * 1000, 60.0 * g["geff_max_um"] * 1e-6 / 9.80665 * 1000)),
            "formula": T("Φ = −(Gρ/2) Σ_f ( h_f S_f − h_f² ω_f )(Werner & Scheeres 1997)\ng = −∇Φ、 g_eff = g + ω² ρ⊥\n"
                         "∇·g = −Gρ Σ_f ω_f(中で −4πGρ、外で 0)\n斜面の角 = ∠(g_eff, −n)",
                         "Φ = −(Gρ/2) Σ_f ( h_f S_f − h_f² ω_f ) (Werner & Scheeres 1997)\ng = −∇Φ,  g_eff = g + ω² ρ⊥\n"
                         "∇·g = −Gρ Σ_f ω_f (−4πGρ inside, 0 outside)\nslope = ∠(g_eff, −n)"),
            "limit": T("密度は一様と仮定している(限界のタブ)。斜面の角は頂点の法線(面積の重みの平均)で測るので、数 m より細かい"
                       "凹凸の斜面は入らない。歩く道は y = 0 の断面の輪郭に最も近い頂点の列。",
                       "Density is assumed uniform (see the limit tab). The slope uses vertex normals (area-weighted), so slopes "
                       "of bumps smaller than a few metres are absent. The path is the chain of vertices nearest to the y = 0 section."),
        },
        "muses": {
            "question": T("はやぶさが降りたミューゼスの海は、細かい砂利が平らにたまった場所。なぜそこにたまる?",
                          "The Muses Sea, where Hayabusa touched down, is a flat pond of fine gravel. Why does it collect there?"),
            "choices": [T("降りるために平らにならした", "It was levelled for the landing"),
                          T("実効ポテンシャルが低い所へ、揺れた粒が流れ込む", "Shaken grains flow down into places where the effective potential is low"),
                          T("遠心力が一番強い所だから", "It is where the centrifugal force is strongest")],
            "answer": 1,
            "explain": T("重力と遠心力をまとめた実効ポテンシャルを、平均の重力で割ると「高さ」になる(最大 %.1f m)。粒は高い所から低い所へ"
                         "転がるので、撒いた粒を op の値で坂の下へ動かすと、平均の高さは %.1f → %.1f m に下がり、低い方 20 %% の面積に入る粒は"
                         " %.0f → %.0f %% に増える。着陸点の推定位置 TD1(平らな所の真ん中)は低い方から %.0f %%、TD2 は %.0f %%(Yano & Aida 2013 は、TD2 がイトカワで最も急な"
                         "ポテンシャルの斜面の 1 つのすぐ隣だと書いている)。Fujiwara 2006 は、平らな所"
                         "(ミューゼスの海・相模原)が重力的に低い所と一致すると報告している。"
                         % (g["height_max_m"], g["grains_height_start_m"], g["grains_height_end_m"], g["grains_in_low20_start"] * 100,
                            g["grains_in_low20_end"] * 100, s1["pct"], s2["pct"]),
                         "Dividing the effective potential (gravity plus centrifugal) by the mean gravity gives a 'height' (up to "
                         "%.1f m). Grains roll from high to low: moving scattered grains downhill by the op's values lowers their "
                         "mean height from %.1f to %.1f m, and the share in the lowest 20 %% of the area rises from %.0f to %.0f %%. "
                         "The estimated touchdown site TD1 (mid-pond) sits at the %.0f %% height rank and TD2 at %.0f %% (Yano & Aida "
                         "2013 note that TD2 lies right next to one of Itokawa's steepest potential slopes). Fujiwara 2006 "
                         "reports that the smooth areas (Muses Sea, Sagamihara) match the gravitationally low regions."
                         % (g["height_max_m"], g["grains_height_start_m"], g["grains_height_end_m"], g["grains_in_low20_start"] * 100,
                            g["grains_in_low20_end"] * 100, s1["pct"], s2["pct"])),
            "formula": T("実効ポテンシャル Φ_eff = Φ − ½ ω² ρ⊥²\nジオポテンシャル高度 H = (Φ_eff − Φ_eff,min) / ḡ\n粒の 1 歩: 隣の頂点のうち Φ_eff が最も低い所へ",
                         "effective potential Φ_eff = Φ − ½ ω² ρ⊥²\ngeopotential height H = (Φ_eff − Φ_eff,min) / ḡ\none grain step: to the neighbouring vertex with the lowest Φ_eff"),
            "limit": T("粒の動きは「坂の下へ」だけの模型で、摩擦・跳ね返り・揺れ(衝突の振動)の強さは入れていない。着陸点は"
                       "Yano & Aida 2013 の推定範囲の中心を、緯度・経度が形状モデルの座標系(北極 = +z、経度は東向き)と同じと"
                       "仮定して置いた。密度は一様と仮定している。",
                       "Grain motion is a 'downhill only' model: no friction, bouncing or the strength of impact shaking. The "
                       "touchdown sites are the centres of the Yano & Aida 2013 estimates, assuming their latitude/longitude use "
                       "the shape model's frame (north = +z, east longitude). Density is assumed uniform."),
        },
        "limit": {
            "question": T("頭の方が胴より重い(密度が高い)と、重心はどう動く?", "If the head is denser than the body, how does the centre of mass move?"),
            "choices": [T("動かない(形が同じだから)", "It does not move (the shape is the same)"),
                        T("頭の方へずれる", "It shifts towards the head"),
                        T("胴の方へずれる", "It shifts towards the body")],
            "answer": 1,
            "explain": T("頭(x ≥ 150 m、体積の %.1f %%)の密度を 1,950 → 2,850 kg/m³ に上げ、全体の質量を保つように胴を %.0f kg/m³ に"
                         "下げると、重心は頭の方へ %.1f m ずれる。Lowry 2014 は自転の加速(YORP)の観測から 21 ± 12 m のずれと、"
                         "胴 1,750 ± 110・頭 2,850 ± 500 kg/m³ を導いた。表面の重力は %.1f〜%+.1f %% 変わる。一様密度の仮定では"
                         "ずれは 0 m で、観測を説明できない。"
                         % (g["head_frac"] * 100, g["lowry_rho_body_ours"], g["com_offset_x_two_density_m"], g["dg_pct_min"], g["dg_pct_max"]),
                         "Raising the head's density (x ≥ 150 m, %.1f %% of the volume) from 1,950 to 2,850 kg/m³ and lowering the "
                         "body to %.0f kg/m³ to keep the total mass shifts the centre of mass %.1f m towards the head. Lowry 2014 "
                         "derived a 21 ± 12 m shift and body 1,750 ± 110 / head 2,850 ± 500 kg/m³ from the observed spin-up (YORP). "
                         "Surface gravity changes by %.1f to %+.1f %%. A uniform density gives 0 m and cannot explain the observation."
                         % (g["head_frac"] * 100, g["lowry_rho_body_ours"], g["com_offset_x_two_density_m"], g["dg_pct_min"], g["dg_pct_max"])),
            "formula": T("Φ_2 = ρ_胴 Φ_1(全体) + (ρ_頭 − ρ_胴) Φ_1(頭)(式が密度について線形)\n全体の質量: ρ_胴 V + (ρ_頭 − ρ_胴) V_頭 = 1,950 V\n"
                         "重心: (ρ_胴 V c + (ρ_頭 − ρ_胴) V_頭 c_頭) / M",
                         "Φ_2 = ρ_body Φ_1(whole) + (ρ_head − ρ_body) Φ_1(head) (linear in density)\n"
                         "total mass: ρ_body V + (ρ_head − ρ_body) V_head = 1,950 V\ncentre of mass: (ρ_body V c + (ρ_head − ρ_body) V_head c_head) / M"),
            "limit": T("2 密度でも各部分の中は一様と仮定している。境 x = 150 m・密度の値は Lowry 2014 のもので、中身を直接測ったわけでは"
                       "ない(探査機は周回していないので、重力場から密度の分布は決められていない)。重心が動けば自転軸の位置と向きも"
                       "変わるが、ここでは z 軸の向きのまま重心を通す軸にした。",
                       "Each part is still uniform inside. The boundary x = 150 m and the densities are Lowry 2014's; the interior "
                       "was not measured directly (the spacecraft did not orbit, so the gravity field could not fix the density "
                       "distribution). A shifted centre of mass also moves the spin axis; here the axis keeps the z direction "
                       "through the new centre of mass."),
        },
        "math": {
            "question": T("でこぼこの形の体積を、中の点を使わず「面だけ」から正確に出せる?", "Can you get the exact volume of a bumpy shape from its faces alone, without any interior points?"),
            "choices": [T("出せない(中を細かく区切って数えるしかない)", "No (you must chop the inside into tiny cells)"),
                        T("出せる: 面ごとの符号付き四面体の体積を足す", "Yes: add the signed volumes of one tetrahedron per face"),
                        T("凸な形のときだけ出せる", "Only for convex shapes")],
            "answer": 1,
            "explain": T("1 点(ここでは重心)と各面で四面体を作り、体積 (1/6) v0·(v1×v2) を足す。面が外向きなら正、内向き(首のくびれの裏側)"
                         "なら負で、余分に数えた所を打ち消す。%d 面(%.2f %%)が負。合計は mesh_volume と %s の差で一致し、頂点を天体の外に"
                         "置いても同じ(差 %s)。発散定理 ∫∇·(x/3) dV = ∮ (x/3)·n dS そのもの。"
                         % (g["tetra_neg_faces"], g["tetra_neg_frac"] * 100, _e(g["tetra_sum_vs_mesh_volume"]), _e(g["tetra_apex_outside_rel"])),
                         "Build one tetrahedron from a point (here the centre of mass) and each face, and add (1/6) v0·(v1×v2). "
                         "Outward faces count positive, inward ones (behind the neck) negative, cancelling what was over-counted: "
                         "%d faces (%.2f %%) are negative. The total matches mesh_volume to %s, and moving the apex outside the "
                         "body changes nothing (%s). It is the divergence theorem ∫∇·(x/3) dV = ∮ (x/3)·n dS."
                         % (g["tetra_neg_faces"], g["tetra_neg_frac"] * 100, _e(g["tetra_sum_vs_mesh_volume"]), _e(g["tetra_apex_outside_rel"]))),
            "formula": T("V = Σ_f (1/6) (v0 − p) · ((v1 − p) × (v2 − p))\n= (1/3) ∮ x · n dS(発散定理、p に依らない)",
                         "V = Σ_f (1/6) (v0 − p) · ((v1 − p) × (v2 − p))\n= (1/3) ∮ x · n dS (divergence theorem, independent of p)"),
            "limit": T("面が閉じていて向きが揃っているときだけ正しい(穴があると、穴を p へ向かって塞いだ立体の体積になる)。自己交差は"
                       "二重に数える。ここでは 49,152 面を方位角で 24 の塊に分けて見せている。",
                       "Only correct for a closed, consistently oriented surface (with a hole you get the solid closed towards p). "
                       "Self-intersections count twice. Here the 49,152 faces are shown in 24 chunks by azimuth."),
        },
    }


def build_spec(R, g):
    N = pv.viewer_number
    d1, d2, d3, d4, d5 = tab_shape(R, g), tab_gravity(R, g), tab_muses(R, g), tab_limit(R, g), tab_math(R, g)
    checks, lessons = all_checks(R, g), all_lessons(R, g)

    def mk(tid, label, badge, text, d, numbers, view):
        tb = pv.viewer_anim3d_tab(tid, label, badge, text, d["t"], d["bodies"], d["xyz"], d["quat"],
                                  trails=d.get("trails"), clouds=d.get("clouds"), events=d.get("events"),
                                  series=d.get("series"), cbar=d.get("cbar"), numbers=numbers, view=view,
                                  checks=checks[tid], axis=d["axis"], lesson=lessons[tid])
        return tb

    dims = g["dims"]
    s1, s2 = g["sites"]["TD1"], g["sites"]["TD2"]
    tab1 = mk("shape", T("形と大きさ", "Shape and size"), "passed",
              T("はやぶさ(JAXA)のカメラの画像 775 枚から作られた形(Gaskell、49,152 面)を、自転軸 z のまわりに 1 周(%.2f 時間)回す。"
                "体積は面だけから出す mesh_volume、大きさは主軸の向きの外接箱 obb(水色)。黄色の棒が重心を通る自転軸。"
                "体積 × 密度で質量が出る。" % PERIOD_H,
                "The shape built from 775 images of Hayabusa's (JAXA) camera (Gaskell, 49,152 faces) turns once about the "
                "spin axis z (%.2f h). The volume comes from the faces alone (mesh_volume), the size from a box on the "
                "principal axes (obb, light blue). The yellow rod is the spin axis through the centre of mass. Volume × "
                "density gives the mass." % PERIOD_H),
              d1,
              [N(T("体積(mesh_volume)/ 公表値", "volume (mesh_volume) / published"), "%.3f / 1.838 × 10^7 m³" % (R["vol"] / 1e7)),
               N(T("大きさ(obb)/ 公表値", "size (obb) / published"), "%.0f × %.0f × %.0f / 535 × 294 × 209 m" % tuple(dims)),
               N(T("質量(× 1.9 g/cm³)/ 公表値", "mass (× 1.9 g/cm³) / published"), "%.2f / 3.51 × 10^10 kg" % (R["mass"] / 1e10)),
               N(T("自転の周期(PDS の極と自転の値)", "spin period (PDS pole and rotation)"), "%.4f h" % PERIOD_H)],
              {"az": -1.2, "el": 0.35, "dist": 0.9})
    tab2 = mk("gravity", T("表面の重力", "Surface gravity"), "passed",
              T("表面の色 = 実効重力の大きさ(重力 + 自転の遠心力)。一様密度 1.9 g/cm³ の多面体の重力を、Werner & Scheeres の厳密な式"
                "(op polyhedron_gravity)で頂点 25,350 個すべてで計算した。白い人が長軸の断面(mesh_slice_contours)を一周し、"
                "黄色の矢印がその場所の実効重力の向き。矢印が地面に垂直でないところは坂(斜面の角)。",
                "Colour = magnitude of effective gravity (gravity plus spin centrifugal). The gravity of a uniform 1.9 g/cm³ "
                "polyhedron is computed with Werner & Scheeres' exact formula (op polyhedron_gravity) at all 25,350 vertices. "
                "The white walker goes round the long-axis section (mesh_slice_contours); the yellow arrow shows the "
                "direction of effective gravity there. Where it is not perpendicular to the ground, the ground is a slope."),
              d2,
              [N(T("表面の |g_eff|(最小〜最大)", "surface |g_eff| (min–max)"), T("%.1f〜%.1f µm/s²" % (g["geff_min_um"], g["geff_max_um"]), "%.1f to %.1f µm/s²" % (g["geff_min_um"], g["geff_max_um"]))),
               N(T("遠心力 ÷ 引力(最大)", "centrifugal ÷ gravity (max)"), "%.1f %%" % (g["centrifugal_frac_max"] * 100)),
               N(T("斜面の角(面積の平均 / 最大)", "slope (area mean / max)"), "%.1f / %.1f °" % (g["slope_mean_deg"], g["slope_max_deg"])),
               N(T("ガウスの法則: 中の ∇·g と −4πGρ の差", "Gauss's law: ∇·g inside vs −4πGρ"), _e(g["div_inside_rel"]))],
              {"az": -1.5708, "el": 0.15, "dist": 0.9})
    tab3 = mk("muses", T("ミューゼスの海はなぜ平らで低い", "Why the Muses Sea is flat and low"), "passed",
              T("色 = ジオポテンシャル高度(実効ポテンシャルを平均の重力 %.1f µm/s² で割った「高さ」)。右は同じ高さを放射方向に誇張した地形。"
                "白い点は表面に撒いた粒で、1 歩ごとに隣の頂点のうち実効ポテンシャル(op の値)が一番低い所へ移る。粒は低い所へ集まる。"
                "赤い玉が着陸点の推定位置(TD1・TD2)。" % g["g_ref_um"],
                "Colour = geopotential height (the effective potential divided by the mean gravity %.1f µm/s²). On the right, "
                "the same heights exaggerated radially. White dots are grains scattered over the surface; each step moves "
                "a grain to the neighbouring vertex with the lowest effective potential (op values). The grains gather in "
                "the low places. Red balls: estimated touchdown sites (TD1, TD2)." % g["g_ref_um"]),
              d3,
              [N(T("高さの範囲(最大)", "height range (max)"), "%.1f m" % g["height_max_m"]),
               N(T("粒の平均の高さ(最初 → 80 歩)", "grains' mean height (start → 80 steps)"), "%.1f → %.1f m" % (g["grains_height_start_m"], g["grains_height_end_m"])),
               N(T("着陸点 TD1 / TD2 の高さの順位", "height rank of TD1 / TD2"), "%.0f / %.0f %%" % (s1["pct"], s2["pct"])),
               N(T("TD1 / TD2 の斜面の角", "slope at TD1 / TD2"), "%.1f / %.1f °" % (s1["slope"], s2["slope"]))],
              {"az": -2.2, "el": -0.5, "dist": 1.1})
    tab4 = mk("limit", T("限界: 一様密度という仮定", "Limit: the uniform-density assumption"), "limit",
              T("ここまでは中身の密度が一様と仮定した。Lowry 2014 は、自転がわずかに速くなっていく観測(YORP)を説明するには重心が形の"
                "中心から頭の側へ約 21 m ずれている必要があり、頭(x ≥ 150 m)が胴より重いと考えた。時間つまみで頭の密度を上げていく"
                "(全体の質量は保つ)。橙の玉 = 重心、白い玉 = 形の中心、色 = 表面の重力の変わり方。表の最後の 2 行は落ちる項目:"
                "一様密度では重心がずれない(観測を説明できない)こと、形の大きさの 3 辺(obb)が公表の 3 軸と 3 本目で %+.0f %% 違う"
                "(3 軸の定義と形の版が違う)こと。" % (g["dims_vs_published"][2] * 100),
                "So far the interior was assumed uniform. Lowry 2014 found that the slowly increasing spin rate (YORP) "
                "needs the centre of mass about 21 m from the centre of figure towards the head, and concluded that the head "
                "(x ≥ 150 m) is denser than the body. The slider raises the head's density (total mass kept). Orange ball = "
                "centre of mass, white ball = centre of figure, colour = how surface gravity changes. The last two rows "
                "of the table fail: a uniform density cannot shift the centre of mass (so it cannot explain the "
                "observation), and the shape's three obb edges differ from the published three axes by %+.0f %% on the "
                "third (different axis definitions and shape versions)." % (g["dims_vs_published"][2] * 100)),
              d4,
              [N(T("頭の体積の割合", "head share of the volume"), "%.1f %%" % (g["head_frac"] * 100)),
               N(T("胴の密度(頭 2,850 のとき)/ Lowry 2014", "body density (head 2,850) / Lowry 2014"), "%.0f / 1,750 ± 110 kg/m³" % g["lowry_rho_body_ours"]),
               N(T("重心のずれ(x)/ Lowry 2014", "centre-of-mass shift (x) / Lowry 2014"), "%.1f / 21 ± 12 m" % g["com_offset_x_two_density_m"]),
               N(T("表面の |g_eff| の変化", "change in surface |g_eff|"), T("%.1f〜%+.1f %%" % (g["dg_pct_min"], g["dg_pct_max"]), "%.1f to %+.1f %%" % (g["dg_pct_min"], g["dg_pct_max"])))],
              {"az": -1.5708, "el": 1.2, "dist": 0.9})
    tab5 = mk("math", T("数学: 体積 = 符号付き四面体の和", "Maths: volume = sum of signed tetrahedra"), "passed",
              T("面を方位角の順に 24 の塊に分け、塊が 1 つずつ戻ってくるたびに、重心と各面で作った四面体の体積を足していく(緑 = 正、"
                "赤 = 負)。全部の面が戻ると、和はちょうど全体の体積になる。中の点は 1 つも使わない。",
                "The faces are split into 24 chunks by azimuth. Each time a chunk comes back, the volumes of the "
                "tetrahedra built from the centre of mass and each face are added (green = positive, red = negative). When "
                "every face is back, the sum is exactly the volume — without a single interior point."),
              d5,
              [N(T("和と mesh_volume の差", "sum vs mesh_volume"), _e(g["tetra_sum_vs_mesh_volume"])),
               N(T("負の四面体", "negative tetrahedra"), "%d 面 / %.2f %%" % (g["tetra_neg_faces"], g["tetra_neg_frac"] * 100))],
              {"az": -1.2, "el": 0.6, "dist": 1.2})
    tabs = [tab1, tab2, tab3, tab4, tab5]
    if tabs[0]["badge"] == "limit":
        raise AssertionError("限界の回を最初のタブにしない")
    credit = T("形: Gaskell Itokawa Shape Model V1.1(R. Gaskell ほか。はやぶさ〔JAXA〕の AMICA の画像から作成)、NASA PDS Small Bodies Node、"
               "CC0 1.0(パブリックドメインへの献呈)。Q = 64 の版(25,350 頂点・49,152 面、単位 km、z 軸 = 自転の極、x 軸 = 経度 0)を"
               "使い、頂点番号を 0 始まりにし、面から使われない重複頂点を落とした。数値: Fujiwara ほか 2006・Abe ほか 2006・"
               "Demura ほか 2006(いずれも Science 312)、Lowry ほか 2014(A&A 562)、Yano & Aida 2013。重力の式: Werner & Scheeres 1997。",
               "Shape: Gaskell Itokawa Shape Model V1.1 (R. Gaskell et al., from Hayabusa [JAXA] AMICA images), NASA PDS Small "
               "Bodies Node, CC0 1.0 (public-domain dedication). The Q = 64 version (25,350 vertices, 49,152 faces, units km, "
               "z = spin pole, x = longitude 0) with vertex numbers made 0-based and unused duplicate vertices dropped. "
               "Numbers: Fujiwara et al. 2006, Abe et al. 2006, Demura et al. 2006 (all Science 312), Lowry et al. 2014 "
               "(A&A 562), Yano & Aida 2013. Gravity formula: Werner & Scheeres 1997.")
    spec = pv.viewer_spec(
        "itokawa_gravity",
        T("小惑星イトカワの重力", "Gravity on asteroid Itokawa"),
        T("実際の形のまま、立つ場所の重さ・坂・砂のたまり方を計算する —— 計算は fullseye の op", "The real shape: weight, slopes and where gravel gathers — computed by fullseye's ops"),
        T("各タブは ① 問い → ② 予想(選択肢を押すと答えが開く)→ ③ 再生(▶)→ ④ 式 → ⑤ 限界 の順。時間つまみの読みは物理量(時刻・歩いた"
          "距離・密度など)。バッジを押すと、確かめた項目・基準・結果の表が開く。ドラッグで視点を回す。",
          "Each tab runs ① question → ② predict (tap a choice to reveal the answer) → ③ play (▶) → ④ equation → ⑤ limit. "
          "The time slider reads a physical quantity (time, distance walked, density …). Tap a badge to open what was "
          "checked, the criterion and the result. Drag to orbit."),
        tabs, credit=credit)
    return spec


def verify_html(path, R):
    """埋めた色(頂点ごとの op の値)を戻して元と比べる。返りは数字の dict(失敗は AssertionError)。"""
    html = Path(path).read_text(encoding="utf-8")
    data = json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))
    A = data["arrays"]
    tabs = {tb["id"]: tb for tb in data["tabs"]}
    worst = 0.0
    for tid, val in (("gravity", R["geff"] * 1e6), ("muses", R["height"]), ("limit", R["limit"]["dg_pct"])):
        rec = A[tabs[tid]["bodies"][0]["val"]]
        back = pv._decode_array(rec)
        cb = tabs[tid]["cbar"]
        ref = np.clip(val, cb["lo"], cb["hi"])
        step = pv._quant_step(rec)
        worst = max(worst, float(np.max(np.abs(back - ref) / (step / 2 + 1e-15))))
    assert worst <= 1.0 + 1e-9, worst
    assert "http://" not in html and "https://" not in html, "外部 URL がある"
    assert "C:\\" not in html and "C:/" not in html, "ローカルパスがある"
    assert "**" not in html, "強調の ** が残っている"
    return {"bytes": len(html.encode("utf-8")), "val_step_ratio": worst}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="書かずに、門の値の印字と HTML の生成だけ")
    ap.add_argument("--out", default=str(OUT_HTML))
    a = ap.parse_args(argv)
    R = compute()
    g = gates(R)
    for k, v in g.items():
        print("%-32s %s" % (k, v))
    spec = build_spec(R, g)
    if a.check:
        n = len(pv._build_html(spec, list(LANGS)).encode("utf-8"))
        print("ok: %d bytes (not written)" % n)
        return 0
    path = pv.write_viewer(spec, a.out, list(LANGS))
    res = verify_html(path, R)
    print("wrote %s (%.2f MB) %s" % (path, Path(path).stat().st_size / 1e6, res))
    return 0


if __name__ == "__main__":
    sys.exit(main())

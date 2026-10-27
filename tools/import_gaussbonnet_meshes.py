#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""離散 Gauss–Bonnet の動く 3-D(tools/build_gaussbonnet_anim3d.py)が読むメッシュを、repo に置く小さな npz にする(手で回す取り込み)。

    py -3.11 -I tools/import_gaussbonnet_meshes.py --genus                 # data/gaussbonnet/genus2.npz, genus3.npz
    py -3.11 -I tools/import_gaussbonnet_meshes.py --triceratops <取得した GLB>   # data/gaussbonnet/triceratops_scan.npz

* ``genus2.npz`` / ``genus3.npz``: 穴が 2 つ・3 つの閉曲面(合成)。平面の梯子の形のグラフ(2 本の横棒と g + 1 本の縦棒)を
  管で太らせた陰関数(線分までの距離の滑らかな最小 − 管の半径)を等値面 0 で切り(``render3d.marching_cubes``、scikit-image が要る)、
  ``decimate_qem_manifold`` で面を減らす。書く前に閉じていること(境界辺 0・非多様体辺 0)と χ = V − E + F = 2 − 2g を検査し、
  合わなければ何も書かない。
* ``triceratops_scan.npz``: 恐竜(トリケラトプス)の骨格の 3-D 走査(館の公開データ、CC0)。原本の GLB(14.4 MB)は repo の外に手で取得し
  (取得物は untrusted として専用の空ディレクトリに置く)、SHA-256 を照合してから ``read_gltf_merged`` で読み、
  ``decimate_qem_manifold``(境界を保つ)で面を 15 万 → 2.4 万に減らす。走査は 2,000 枚余りの開いた面片(テクスチャの継ぎ目で
  頂点が切れている)で、1 つの閉曲面ではない —— それをそのまま持つ(教材では「境界のある面」の限界の回に使う)。
  間引きで扇が 2 つになった頂点(つままれた頂点)は扇ごとに分け、面片ごとの離散 Gauss–Bonnet(境界の項つきの Σ K = 2πχ)が
  厳密に成り立つことを確かめてから書く。元の頂点数・面数・境界辺の数・面片の数も記録する。

出典と利用条件は ``data/gaussbonnet/README.md``。生成物は tools/regen_all.py の EXCLUDED(原本が repo の外にあり、
scikit-image も任意の依存なので CI では作れない)。
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "data" / "gaussbonnet"
#: 2026-10-26 に取得した Triceratops horridus(150k 面・4096 px テクスチャ版)の GLB の SHA-256(sample_data の台帳と同じ値)。
SHA256_GLB = "cd8525c7371d14876bcdefe3f579d216bf597db892c2de6ed597da86bf1a98b3"
GLB_BYTES = 14395048
TRICERATOPS_FACES = 24000
GENUS_FACES = 7000


def _euler(V, F):
    import mathgeometry
    return mathgeometry.mesh_euler_characteristic(V, F)


def _components(F, n_vertices: int) -> int:
    import scipy.sparse as sp
    import scipy.sparse.csgraph as cg
    I = np.r_[F[:, 0], F[:, 1], F[:, 2]]
    J = np.r_[F[:, 1], F[:, 2], F[:, 0]]
    A = sp.coo_matrix((np.ones(len(I)), (I, J)), shape=(n_vertices, n_vertices))
    n, lab = cg.connected_components(A, directed=False)
    return int(len(np.unique(lab[np.unique(F)])))


# --------------------------------------------------------------------------- 合成: 穴が g 個の閉曲面
def ladder_segments(g: int, span: float = 1.6, rail: float = 0.9):
    """2 本の横棒(y = ±rail)と g + 1 本の縦棒(x = 等間隔)の線分 [(p0, p1)]。独立な輪の数 = g。"""
    xs = (np.arange(g + 1) - g / 2.0) * span
    segs = [((xs[0], -rail, 0.0), (xs[-1], -rail, 0.0)), ((xs[0], rail, 0.0), (xs[-1], rail, 0.0))]
    for x in xs:
        segs.append(((x, -rail, 0.0), (x, rail, 0.0)))
    return [(np.asarray(a, float), np.asarray(b, float)) for a, b in segs]


def _seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / float(ab @ ab), 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def genus_field(g: int, pitch: float = 0.055, radius: float = 0.42, blend: float = 0.35):
    """管で太らせた梯子の陰関数(負 = 中)を格子で評価する。戻り = (vol, origin)。"""
    segs = ladder_segments(g)
    pts = np.array([p for s in segs for p in s])
    lo, hi = pts.min(0) - (radius + 0.5), pts.max(0) + (radius + 0.5)
    nx, ny, nz = [int(np.ceil((hi[k] - lo[k]) / pitch)) + 1 for k in range(3)]
    gx, gy, gz = [lo[k] + pitch * np.arange(n) for k, n in enumerate((nx, ny, nz))]
    X, Y, Z = np.meshgrid(gx, gy, gz, indexing="ij")
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    d = _seg_dist(P, *segs[0])
    for a, b in segs[1:]:                                         # 多項式の滑らかな最小(k = blend)
        d2 = _seg_dist(P, a, b)
        h = np.clip(0.5 + 0.5 * (d2 - d) / blend, 0.0, 1.0)
        d = d2 * (1 - h) + d * h - blend * h * (1 - h)
    return (d - radius).reshape(nx, ny, nz), lo, pitch


def make_genus(g: int, target_faces: int = GENUS_FACES):
    import mesh_decimate
    import render3d
    vol, origin, pitch = genus_field(g)
    V, F = render3d.marching_cubes(vol, 0.0)
    V = V * pitch + origin
    V, F = mesh_decimate.decimate_qem_manifold(V, F, target_faces)
    e = _euler(V, F)
    if not e["closed"] or e["chi"] != 2 - 2 * g or _components(F, V.shape[0]) != 1:
        raise ValueError("genus %d: 閉じた 1 つの曲面にならなかった %r" % (g, e))
    return V.astype(np.float32), F.astype(np.int32), e


# --------------------------------------------------------------------------- 実物: 骨格の走査(開いた面片の集まり)
def split_pinched_vertices(V, F):
    """1 つの頂点に 2 つ以上の扇(面の輪)が集まる頂点(辺は多様体でも頂点が多様体でない「つままれた」頂点)を、扇ごとに別の頂点に分ける。

    境界のある面の離散 Gauss–Bonnet(Σ_内部 (2π − Σθ) + Σ_境界 (π − Σθ) = 2πχ)は、境界の頂点がちょうど 2 本の境界辺を持つ
    (= 扇が 1 つ)ことを前提にする。間引きで扇が 2 つになった頂点があると、境界の項が 1 つ分しか数えられず、和が 2πχ から π ずつ外れる。
    分けると V と χ がその数だけ増え、面片ごとの定理が厳密に戻る。戻り = (V, F, 分けた頂点の数)。
    """
    V = np.asarray(V, float)
    F = np.asarray(F, int)
    nv = V.shape[0]
    inc: list = [[] for _ in range(nv)]
    for fi, f in enumerate(F):
        for v in f:
            inc[v].append(fi)
    newV, F2, n_split = [V], F.copy(), 0
    next_id = nv
    for v in range(nv):
        fs = inc[v]
        if len(fs) < 2:
            continue
        # 頂点 v を含む面を、v を含む辺で結んで連結成分に分ける
        parent = {f: f for f in fs}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        by_edge: dict = {}
        for f in fs:
            tri = F[f]
            for u in tri:
                if u != v:
                    by_edge.setdefault(int(u), []).append(f)
        for lst in by_edge.values():
            for f in lst[1:]:
                a, b = find(lst[0]), find(f)
                if a != b:
                    parent[a] = b
        roots = sorted({find(f) for f in fs})
        if len(roots) == 1:
            continue
        n_split += 1
        for r in roots[1:]:
            newV.append(V[v][None, :])
            for f in fs:
                if find(f) == r:
                    F2[f][F2[f] == v] = next_id
            next_id += 1
    return np.concatenate(newV), F2, n_split


def import_triceratops(glb: Path, target_faces: int = TRICERATOPS_FACES):
    import mathgeometry
    import mesh_decimate
    import meshio_opt
    raw = glb.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != SHA256_GLB or len(raw) != GLB_BYTES:
        raise ValueError("GLB の SHA-256 / 大きさが記録と違う(%s, %d bytes)—— 書かない" % (sha, len(raw)))
    V, F = meshio_opt.read_gltf_merged(str(glb))
    if V.shape[0] == 0 or not np.all(np.isfinite(V)):
        raise ValueError("GLB から三角形が読めなかった")
    e0 = _euler(V, F)
    V2, F2 = mesh_decimate.decimate_qem_manifold(V, F, target_faces)
    V2, F2, n_split = split_pinched_vertices(V2, F2)
    e1 = _euler(V2, F2)
    if e1["nonmanifold_edges"] != 0 or e1["boundary_edges"] == 0:
        raise ValueError("間引いた走査が想定(境界あり・非多様体なし)と違う %r" % e1)
    d = mathgeometry.angle_defect(V2, F2)
    if abs(d["total"] - d["two_pi_chi"]) > 1e-9:
        raise ValueError("間引いた走査で境界の項つきの Σ K が 2πχ と合わない(差 %.3e)—— 書かない" % abs(d["total"] - d["two_pi_chi"]))
    meta = {"source_sha256": sha, "source_vertices": e0["V"], "source_faces": e0["F"], "source_boundary_edges": e0["boundary_edges"],
            "source_components": _components(F, V.shape[0]), "source_chi": e0["chi"], "split_vertices": n_split}
    return V2.astype(np.float32), F2.astype(np.int32), e1, meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--genus", action="store_true", help="genus2.npz / genus3.npz を書く(scikit-image が要る)")
    ap.add_argument("--triceratops", metavar="GLB", help="取得した Triceratops horridus の GLB(150k 面版)")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    a = ap.parse_args(argv)
    if not a.genus and not a.triceratops:
        ap.error("--genus か --triceratops のどちらかを指定する")
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if a.genus:
        for g in (2, 3):
            V, F, e = make_genus(g)
            p = out_dir / ("genus%d.npz" % g)
            np.savez_compressed(p, vertices=V, faces=F, genus=np.array(g))
            print("wrote %s (%d bytes): %d vertices, %d faces, chi %d, closed %s" % (p, p.stat().st_size, e["V"], e["F"], e["chi"], e["closed"]))
    if a.triceratops:
        V, F, e, meta = import_triceratops(Path(a.triceratops))
        p = out_dir / "triceratops_scan.npz"
        np.savez_compressed(p, vertices=V, faces=F, **{k: np.array(v) for k, v in meta.items()})
        print("wrote %s (%d bytes): %d vertices, %d faces, boundary edges %d, chi %d, pinched vertices split %d; "
              "source %d vertices / %d faces / %d boundary edges / %d patches"
              % (p, p.stat().st_size, e["V"], e["F"], e["boundary_edges"], e["chi"], meta["split_vertices"], meta["source_vertices"],
                 meta["source_faces"], meta["source_boundary_edges"], meta["source_components"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

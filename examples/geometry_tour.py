# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""geometry_tour — 離散幾何と位相の古典を、画像・メッシュ・点群で見る(測地距離・Gauss–Bonnet・Delaunay)。

    py -3.11 examples/geometry_tour.py

【この例が示すこと】
1. **障害物のある部屋の最短距離(2-D 画像)** —— 壁とすき間のある間取りで、入口からの「歩いて行ける距離」を求める。
   画素を 8 近傍でたどる Dijkstra は、斜め 22.5° の方向に進めず等距離線が**八角形**に歪む(格子の向きの誤差、
   細かくしても消えない)。熱法は面の中を斜めに進めるので等距離線は**円**になり、細かくするほど真値に近づく。
2. **曲面の最短距離(3-D メッシュ)** —— 球面の大円距離に対して、辺をたどる Dijkstra は 7.8% の誤差で止まり、
   熱法は細かくするほど誤差が減り続ける。
3. **Gauss–Bonnet** —— トーラスの頂点ごとの曲がり(角欠損)を展開図に描く。外側は凸で正、内側は鞍で負。
   総和はどんなに歪めてもちょうど 0(= 2πχ、χ = 0)。球はちょうど 4π。穴の数だけで総和が決まる。
4. **Delaunay 分割** —— どの三角形の外接円の中にも他の点が無い。三角形の数は 2n − h − 2。3-D でも外接球が空。

【グラウンドトゥルース】ユークリッド距離・大円距離 Rθ・2πχ・2n − h − 2。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs      # noqa: E402
import fullseye as fs          # noqa: E402  公開経路(fs.<名前>)から呼ぶ


def _dijkstra8(M, src, sp):
    """比較用: 画素の 8 近傍グラフの Dijkstra(素朴な格子の最短路)。"""
    from scipy.sparse import coo_matrix, csgraph
    n0, n1 = M.shape
    idx = -np.ones(M.shape, int)
    idx[M] = np.arange(M.sum())
    R, C, W = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        x0, x1 = max(0, -dx), n1 - max(0, dx)
        a = idx[0:n0 - dy, x0:x1]
        b = idx[dy:n0, x0 + dx:x1 + dx]
        ok = (a >= 0) & (b >= 0)
        R.append(a[ok])
        C.append(b[ok])
        W.append(np.full(ok.sum(), math.hypot(dy, dx) * sp))
    A = coo_matrix((np.concatenate(W), (np.concatenate(R), np.concatenate(C))), shape=(int(M.sum()),) * 2)
    out = np.full(M.shape, np.inf)
    out[M] = csgraph.dijkstra(A, directed=False, indices=idx[src])
    return out


def _floorplan(n):
    """入口(左上)と、すき間のある壁 2 枚の部屋。"""
    M = np.ones((n, n), bool)
    w = max(1, n // 60)
    M[n // 3:n // 3 + w, : int(0.7 * n)] = False                  # 上の壁(右側にすき間)
    M[2 * n // 3:2 * n // 3 + w, int(0.3 * n):] = False           # 下の壁(左側にすき間)
    return M


def _iso(D, vmax, step=0.05):
    """距離画像に 0.05 ごとの縞を入れる(等距離線を目で追えるように)。通れない所は少し下の値。"""
    fin = np.isfinite(D)
    img = np.where(fin, D, 0.0)
    stripes = (np.floor(img / step) % 2 == 0)
    return np.where(fin, np.where(stripes, img, 0.8 * img), -0.02 * vmax)


def run() -> dict:
    t0 = time.perf_counter()
    out = {}

    # ---- 1. 部屋の最短距離 -------------------------------------------------------------- #
    n = 161
    sp = 1.0 / (n - 1)
    room = _floorplan(n)
    src = (n // 10, n // 10)
    Dh = fs.geodesic_heat_grid(room, src, spacing=sp)["distance"]
    Dd = _dijkstra8(room, src, sp)
    free = np.ones((n, n), bool)
    yy, xx = np.indices(free.shape)
    c = (n // 2, n // 2)
    true = np.hypot(yy - c[0], xx - c[1]) * sp
    Dfree_h = fs.geodesic_heat_grid(free, c, spacing=sp)["distance"]
    Dfree_d = _dijkstra8(free, c, sp)
    eh = float(np.abs(Dfree_h - true).max())
    ed = float(np.abs(Dfree_d - true).max())
    print("1) 何も無い部屋で真のユークリッド距離との最大差: 熱法 %.4f / 8 近傍 Dijkstra %.4f(%.1f 倍)" % (eh, ed, ed / eh))
    assert ed > 5 * eh
    p = (int(0.9 * n), int(0.9 * n))
    print("   壁を回った先 %s までの距離: 熱法 %.3f / Dijkstra %.3f(直線なら %.3f)"
          % (p, Dh[p], Dd[p], math.hypot(p[0] - src[0], p[1] - src[1]) * sp))
    assert np.isfinite(Dh[p]) and Dh[p] > math.hypot(p[0] - src[0], p[1] - src[1]) * sp
    out.update(free_err_heat=eh, free_err_dijkstra8=ed)

    # ---- 2. 球面 ------------------------------------------------------------------------ #
    import geodesic3d
    rows = []
    for freq in (4, 8, 16):
        V, F = fs.ledger.geodesic_dome(freq)
        V = V / np.linalg.norm(V, axis=1, keepdims=True)
        tr = np.arccos(np.clip(V @ V[0], -1, 1))
        e_h = float(np.abs(fs.geodesic_heat(V, F, 0)["distance"] - tr).mean() / tr.mean())
        e_d = float(np.abs(geodesic3d.geodesic_mesh(V, F, 0) - tr).mean() / tr.mean())
        rows.append((len(V), e_h, e_d))
    print("2) 球面の測地距離の相対誤差(頂点数: 熱法 / 辺の Dijkstra): "
          + ", ".join("%d: %.3f / %.3f" % r for r in rows))
    assert rows[-1][1] < rows[0][1] / 3 and rows[-1][2] > 0.7 * rows[0][2]

    # ---- 3. Gauss–Bonnet --------------------------------------------------------------- #
    nu, nv = 48, 24
    V, F = fs.mesh_torus(2.0, 0.7, nu, nv)
    ad = fs.angle_defect(V, F)
    adj = fs.angle_defect(V + 0.04 * np.random.default_rng(0).normal(size=V.shape), F)
    Vs, Fs = fs.ledger.geodesic_dome(6)
    sph = fs.angle_defect(Vs, Fs)
    chi_t = fs.mesh_euler_characteristic(V, F)
    print("3) 角欠損の総和: トーラス %.1e(歪めても %.1e、χ=%d・種数 %d)/ 球 %.6f(4π = %.6f)"
          % (ad["total"], adj["total"], chi_t["chi"], chi_t["genus"], sph["total"], 4 * math.pi))
    assert abs(ad["total"]) < 1e-10 and abs(adj["total"]) < 1e-10 and abs(sph["total"] - 4 * math.pi) < 1e-10

    # ---- 4. Delaunay ------------------------------------------------------------------- #
    P = np.random.default_rng(3).random((40, 2))
    dl = fs.delaunay_triangulate(P)
    viol = sum(int(np.sum(np.linalg.norm(P - cc, axis=1) < r - 1e-9)) for cc, r in zip(dl["circumcenters"], dl["circumradii"]))
    print("4) Delaunay: 三角形 %d 個 = 2n − h − 2 = %d、外接円の中の点 %d 個"
          % (dl["n_triangles"], 2 * 40 - len(dl["hull"]) - 2, viol))
    assert dl["n_triangles"] == 2 * 40 - len(dl["hull"]) - 2 and viol == 0
    P3 = np.random.default_rng(4).random((80, 3))
    d3 = fs.delaunay_triangulate(P3)
    v3 = sum(int(np.sum(np.linalg.norm(P3 - cc, axis=1) < r - 1e-9)) for cc, r in zip(d3["circumcenters"], d3["circumradii"]))
    assert v3 == 0

    # ---- 図 ---------------------------------------------------------------------------- #
    if figs.enabled():
        vmax = float(np.max(Dh[np.isfinite(Dh)]))
        figs.save_grid("room",
                       [_iso(Dd, vmax), _iso(Dh, vmax), np.abs(Dfree_d - true), np.abs(Dfree_h - true)],
                       ["画素の 8 近傍 Dijkstra", "熱法(fs.geodesic_heat_grid)",
                        "何も無い部屋での誤差(Dijkstra)", "同じ(熱法)、同じ色の目盛り"],
                       ncols=2, vrange=[(-0.02 * vmax, vmax), (-0.02 * vmax, vmax), (0.0, ed), (0.0, ed)],
                       title="壁のある部屋で入口からの「歩く距離」—— 縞は 0.05 ごとの等距離線",
                       caption="壁(暗い線)のすき間を回り込む距離。8 近傍の Dijkstra は斜め 22.5° に進めないので等距離線が"
                               "八角形に歪み、何も無い部屋でも最大 %.3f ずれる(下段左、放射状の筋)。熱法は円で、最大 %.4f"
                               "(下段右、同じ目盛りでほぼ黒)。" % (ed, eh))
        figs.save_plot("sphere_convergence",
                       [("熱法(fs.geodesic_heat)", np.log10([r[0] for r in rows]), np.log10([r[1] for r in rows])),
                        ("辺をたどる Dijkstra(geodesic_mesh)", np.log10([r[0] for r in rows]), np.log10([r[2] for r in rows]))],
                       xlabel="log10(頂点の数)", ylabel="log10(大円距離との相対誤差)",
                       title="球面の最短距離 —— 細かくすると熱法だけが真値に近づく",
                       caption="辺をたどる Dijkstra は辺の向きにしか進めず、どれだけ細かくしても誤差 %.1f%% で止まる。"
                               "熱法は面の中を斜めに進めるので、頂点を増やすほど誤差が減る(%.1f%% → %.1f%%)。"
                               % (100 * rows[-1][2], 100 * rows[0][1], 100 * rows[-1][1]))
        figs.save_grid("torus_defect",
                       [np.kron(ad["defect"].reshape(nu, nv).T, np.ones((6, 6))),
                        np.kron(adj["defect"].reshape(nu, nv).T, np.ones((6, 6)))],
                       ["整ったトーラス(総和 %.0e)" % ad["total"], "頂点を乱したトーラス(総和 %.0e)" % adj["total"]],
                       ncols=2, signed=True,
                       title="トーラスの曲がり(角欠損)—— 青は凸、橙は鞍、総和はいつも 0",
                       caption="展開図: 横が大円の向き、縦が管のまわり(上下の端が外側、中段が内側)。外側は凸で正(青)、"
                               "内側は鞍で負(橙)。"
                               "頂点を乱すと色はまだらになるが、総和は丸めの範囲で 0 のまま —— 穴が 1 つなら 2πχ = 0(Gauss–Bonnet)。"
                               "球なら総和はちょうど 4π(= %.6f)。" % sph["total"])
        tri = dl["triangles"]
        series = [("点", P[:, 0], P[:, 1])]
        for k, t in enumerate(tri):
            q = P[np.r_[t, t[0]]]
            series.append(("Delaunay の三角形" if k == 0 else "", q[:, 0], q[:, 1]))
        th = np.linspace(0, 2 * math.pi, 120)
        picks = (3, 11, 25)
        for k, i in enumerate(picks):
            cc, r = dl["circumcenters"][i], dl["circumradii"][i]
            series.append(("外接円(中に点が無い)" if k == 0 else "", cc[0] + r * np.cos(th), cc[1] + r * np.sin(th)))
        allx = np.concatenate([np.asarray(s_[1]) for s_ in series])
        ally = np.concatenate([np.asarray(s_[2]) for s_ in series])
        figs.save_plot("delaunay", series, size=(560, 520),
                       kinds=["scatter"] + ["line"] * (len(series) - 1),
                       styles=[None] + [None] * len(tri) + ["dashed"] * len(picks),
                       colors=["wrong"] + ["reference"] * len(tri) + ["emphasis"] * len(picks),
                       xlim=(float(allx.min()) - 0.02, float(allx.max()) + 0.02),
                       ylim=(float(ally.min()) - 0.02, float(ally.max()) + 0.02), aspect="equal",
                       xlabel="x", ylabel="y",
                       title="Delaunay 分割 —— どの外接円の中にも、ほかの点が無い",
                       caption="40 点を三角形 %d 個に分割(= 2n − h − 2)。破線は外接円の例。3-D の 80 点でも外接球の中に点は 0 個。"
                               % dl["n_triangles"])
    assert not figs.errors(), figs.errors()

    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  geometry_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()

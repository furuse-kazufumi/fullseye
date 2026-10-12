# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery_drive_city_terrain — 街(建物の足跡)・起伏・LiDAR の箱・倉庫の格子を、面積・体積・閉形式の距離で確かめる

    py -3.11 examples/gallery_drive_city_terrain.py

【平たく言うと】
運転の世界の「地面と街」を作る op と、その上で距離を測る op を 7 本まとめて確かめる。
PLATEAU 形式の建物を読み、箱で切り出し、足跡を押し出して角柱にする(driveplateau)。道の周りに起伏を
付けた地面の格子を作る(driveterrain)。光線が箱に当たるまでの距離を出す(lidarsim)。倉庫の床の格子で
最短手数と計画の総コストを数える(agvfleet)。どれも「答えが紙の上で出せる」入力を渡して照合する。

【何を期待し、何と比べるか】
  * triangulate_polygon : 凹の L 字と櫛形 —— 三角形は k − 2 個、面積の和 = 靴紐公式の面積、全部反時計回り。
                          時計回りに並べた入力でも同じ。頂点 2 個は拒む。
  * buildings_in_box    : 30 m 間隔に並んだ 5 棟から、重心が x ∈ [15, 75] の 2 棟(高さ 15・20 m)だけを返す。
  * building_prisms     : 2 棟の角柱 = 頂点 16・面 20(側面 8 + 屋根 2 × 2 棟)、境界辺は底の 8 本だけ、
                          体積(発散定理、底は z = 0 で寄与 0)= Σ 足跡の面積 × 高さ、屋根の色 = 0.92 倍。
  * terrain_mesh        : 40 × 20 m を 2 m の升 → 頂点 21 × 11・面 400、道の面(ラベル 0)は 160 枚(重心が |y| < 3.5)、
                          道から flat = 2 m 以内の高さ = 路面のうねりの閉形式、上から見た面積の和 = 800 m²、全部上向き。
  * ray_box_ranges      : 箱 x ∈ [5, 7] へ: 正面 5 m、方向の長さに依らない、外れは inf、斜め 5·√1.01 m、箱の中からは出口。
                          乱数の 2000 本を「6 枚の面との交点を全部調べる」第 2 実装と照合。
  * grid_distances      : 壁(列 2 の上 3 マス)を回り込む距離 = 6 + c − r(閉形式)、囲まれたマスは inf。
  * plan_cost           : 「最後に着いた時刻」の和 —— 途中で目的地を通り過ぎた車は戻った時刻で数える(3 + 3 + 0 = 6)。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agvfleet as AF  # noqa: E402
import drivecourse  # noqa: E402
import driveplateau as PL  # noqa: E402
import driveterrain as DT  # noqa: E402
import lidarsim as LS  # noqa: E402

_ROWS = []


def check(op, what, expected, got, ok):
    """1 行 = 何を期待し、何が出て、合ったか。"""
    _ROWS.append((op, bool(ok)))
    print("  %-19s %-50s 期待 %-22s 実測 %-22s %s" % (op, what, expected, got, "ok" if ok else "NG"))


def _shoelace(P):
    P = np.asarray(P, np.float64)
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _tri_signed(P, T):
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    return 0.5 * ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))


def _boundary_edges(F):
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    _, cnt = np.unique(E, axis=0, return_counts=True)
    return int((cnt == 1).sum()), int((cnt > 2).sum())


def part_polygons():
    print("== 1. 多角形の三角形分割")
    shapes = {
        "L 字(凹 6 頂点)": np.array([[0, 0], [4, 0], [4, 1], [1, 1], [1, 3], [0, 3]], np.float64),
        "櫛形(凹 10 頂点)": np.array([[0, 0], [5, 0], [5, 3], [4, 3], [4, 1], [3, 1], [3, 3], [1, 3], [1, 1], [0, 1]],
                                    np.float64),
    }
    for name, P in shapes.items():
        for order, Q in (("反時計回り", P), ("時計回り", P[::-1].copy())):
            T = PL.triangulate_polygon(Q)
            s = _tri_signed(Q, T)
            want = abs(_shoelace(Q))
            check("triangulate_polygon", "%s・%s: k − 2 個・面積の和" % (name, order), "%d・%.6g" % (len(Q) - 2, want),
                  "%d・%.6g" % (len(T), s.sum()), len(T) == len(Q) - 2 and abs(s.sum() - want) < 1e-12
                  and bool(np.all(s > 0)))
    bad = False
    try:
        PL.triangulate_polygon([[0, 0], [1, 0]])
    except ValueError:
        bad = True
    check("triangulate_polygon", "頂点 2 個は拒む", "ValueError", "ValueError" if bad else "通った", bad)


def part_buildings():
    print("== 2. 建物(PLATEAU 形式 → 箱で切り出し → 角柱)")
    gml = PL.citygml_synthetic(5, spacing=30.0, size=12.0)        # 高さ 10 + 5i、中心 x = 30i
    parsed = PL.plateau_parse(gml)
    sel = PL.buildings_in_box(parsed, 15.0, 75.0, -10.0, 10.0)
    hs = [b["height"] for b in sel]
    check("buildings_in_box", "重心が x ∈ [15, 75] の建物", "2 棟・高さ [15, 20]", "%d 棟・高さ %s" % (len(sel), hs),
          len(sel) == 2 and hs == [15.0, 20.0])
    check("buildings_in_box", "箱が空の範囲", "0 棟", "%d 棟" % len(PL.buildings_in_box(parsed, 200, 300, -10, 10)),
          len(PL.buildings_in_box(parsed, 200.0, 300.0, -10.0, 10.0)) == 0)
    rev = False
    try:
        PL.buildings_in_box(parsed, 75.0, 15.0, -10.0, 10.0)
    except ValueError:
        rev = True
    check("buildings_in_box", "xmin > xmax は拒む", "ValueError", "ValueError" if rev else "通った", rev)

    V, F, C, ids = PL.building_prisms(sel, color_fn=lambda b: (0.5, 0.6, 0.7), base_z=0.0, roof_shade=0.92)
    check("building_prisms", "頂点・面(側面 8 + 屋根 2)× 2 棟", "16・20", "%d・%d" % (len(V), len(F)),
          len(V) == 16 and len(F) == 20 and ids.tolist() == [0] * 10 + [1] * 10)
    n_open, n_bad = _boundary_edges(F)
    check("building_prisms", "境界辺 = 底の 4 本 × 2 棟、3 面以上が共有する辺 0", "8・0", "%d・%d" % (n_open, n_bad),
          n_open == 8 and n_bad == 0)
    nrm = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])            # 長さ = 2 × 面積
    zc = V[F][:, :, 2].mean(axis=1)
    vol = float((0.5 * nrm[:, 2] * zc).sum())                                   # ∮ z n_z dA(底は z = 0 で 0)
    want = sum(abs(_shoelace(b["footprint"])) * b["height"] for b in sel)
    check("building_prisms", "体積 = Σ 足跡の面積 × 高さ(外向きの面)", "%.4f m³" % want, "%.4f m³" % vol,
          abs(vol - want) < 1e-6 * want)
    roof = nrm[:, 2] > 0
    check("building_prisms", "屋根の色 = 側面の 0.92 倍", "(0.46, 0.552, 0.644)",
          str(np.round(C[roof][0], 4).tolist()), np.allclose(C[roof], np.array([0.5, 0.6, 0.7]) * 0.92)
          and np.allclose(C[~roof], (0.5, 0.6, 0.7)))
    e = PL.building_prisms([])
    check("building_prisms", "建物 0 件は空を返す", "(0,3)(0,3)(0,3)(0,)", "%s%s%s%s" % tuple(a.shape for a in e),
          e[0].shape == (0, 3) and e[1].shape == (0, 3) and e[3].shape == (0,))


def part_terrain():
    print("== 3. 起伏のある地面の格子")
    course = drivecourse.course_road(length=40.0, width=7.0)       # 直線路 y ∈ [−3.5, 3.5]
    p = DT.terrain_params(seed=3, amplitude=2.0, flat=2.0, blend=6.0, road_amp=0.3, road_len=(30.0, 25.0),
                          road_phase=(0.0, 1.0))
    m = DT.terrain_mesh(p, course, (0.0, 40.0, -10.0, 10.0), step=2.0)
    V, F = m["V"], m["F"]
    check("terrain_mesh", "頂点 21 × 11・面 2 × 20 × 10", "231・400", "%d・%d" % (len(V), len(F)),
          len(V) == 231 and len(F) == 400)
    n_road = int((m["face_label"] == 0).sum())
    check("terrain_mesh", "道の面(重心 |y| < 3.5 の行 4 本 × 20 × 2)", "160", str(n_road),
          n_road == 160 and int((m["face_label"] == 10).sum()) == 240)
    near = np.abs(V[:, 1]) <= 5.0                                     # 道の縁 3.5 + flat 2.0 の内側
    wave = 0.15 * (np.sin(2 * np.pi * V[:, 0] / 30.0) + np.sin(2 * np.pi * V[:, 1] / 25.0 + 1.0))
    err = float(np.abs(V[near, 2] - wave[near]).max())
    check("terrain_mesh", "道から 2 m 以内の高さ = うねりの閉形式", "差 < 1e-12", "%.1e" % err, err < 1e-12)
    far = np.abs(V[:, 1]) >= 9.9
    check("terrain_mesh", "道から離れると起伏が乗る(|y| = 10 の行)", "うねりと違う",
          "最大の差 %.2f m" % float(np.abs(V[far, 2] - wave[far]).max()), float(np.abs(V[far, 2] - wave[far]).max()) > 0.05)
    nrm = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    area_xy = float(0.5 * nrm[:, 2].sum())
    check("terrain_mesh", "上から見た面積の和・全部上向き", "800 m²・400 / 400", "%.9g m²・%d / 400" % (area_xy, (nrm[:, 2] > 0).sum()),
          abs(area_xy - 800.0) < 1e-9 and bool(np.all(nrm[:, 2] > 0)))
    n_open, _ = _boundary_edges(F)
    check("terrain_mesh", "境界辺 = 外周の 2 × (20 + 10)", "60", str(n_open), n_open == 60)


def _ray_box_ref(o, D, box):
    """第 2 実装: 6 枚の面との交点を全部調べ、箱の面の上にある最初の前方の交点(t·‖D‖)。"""
    lo, hi = np.array(box[:3], np.float64), np.array(box[3:], np.float64)
    inside = np.all(o > lo) and np.all(o < hi)
    best = math.inf
    for ax in range(3):
        if D[ax] == 0:
            continue
        for plane in (lo[ax], hi[ax]):
            t = (plane - o[ax]) / D[ax]
            if t < 0:
                continue
            q = o + t * D
            others = [k for k in range(3) if k != ax]
            if all(lo[k] - 1e-12 <= q[k] <= hi[k] + 1e-12 for k in others):
                best = min(best, t)
    if inside or best < math.inf:
        return best * float(np.linalg.norm(D))
    return math.inf


def part_lidar():
    print("== 4. 光線と箱(LiDAR)")
    box = (5.0, -1.0, -1.0, 7.0, 1.0, 1.0)
    D = np.array([[1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 0.1, 0.0], [-1.0, 0.0, 0.0]])
    r = LS.ray_box_ranges((0.0, 0.0, 0.0), D, box)
    want = [5.0, 5.0, math.inf, 5.0 * math.sqrt(1.01), math.inf]
    check("ray_box_ranges", "正面・長さ 2 の方向・横・斜め・後ろ", "5, 5, inf, 5.0249, inf",
          ", ".join("%.4f" % v if np.isfinite(v) else "inf" for v in r),
          all((math.isinf(a) and math.isinf(b)) or abs(a - b) < 1e-12 for a, b in zip(r, want)))
    ins = LS.ray_box_ranges((6.0, 0.0, 0.0), np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0]]), box)
    check("ray_box_ranges", "箱の中から: 出口までの距離", "1, 1", "%.12g, %.12g" % tuple(ins), np.allclose(ins, [1.0, 1.0]))
    rng = np.random.default_rng(7)
    O = rng.uniform(-3, 12, (2000, 3))
    aim = rng.uniform((3.5, -2.5, -2.5), (8.5, 2.5, 2.5), (2000, 3))     # 箱の周りを狙う(当たりと外れが混ざる)
    Ds = (aim - O) * rng.uniform(0.2, 3.0, (2000, 1))
    got = np.array([LS.ray_box_ranges(o, d[None, :], box)[0] for o, d in zip(O, Ds)])
    ref = np.array([_ray_box_ref(o, d, box) for o, d in zip(O, Ds)])
    fin = np.isfinite(ref)
    agree = np.array_equal(np.isfinite(got), fin) and float(np.abs(got[fin] - ref[fin]).max()) < 1e-9
    check("ray_box_ranges", "乱数 2000 本 = 6 面を全部調べる第 2 実装", "一致(当たり %d 本)" % fin.sum(),
          "当たり %d 本・差 %.1e" % (np.isfinite(got).sum(), float(np.abs(got[fin] - ref[fin]).max()) if fin.any() else 0.0),
          agree and 50 < fin.sum() < 1950)
    bad = False
    try:
        LS.ray_box_ranges((0, 0, 0), D, (1.0, 0.0, 0.0, 1.0, 1.0, 1.0))
    except ValueError:
        bad = True
    check("ray_box_ranges", "min < max でない箱は拒む", "ValueError", "ValueError" if bad else "通った", bad)


def part_grid():
    print("== 5. 倉庫の格子(最短手数・計画の総コスト)")
    g = np.ones((4, 6), bool)
    g[0:3, 2] = False                                          # 列 2 の上 3 マスが壁(通れるのは行 3 だけ)
    d = AF.grid_distances(g, (0, 0))
    R, C = np.indices(g.shape)
    want = np.where(C <= 1, R + C, 6 + C - R).astype(float)    # 左側はマンハッタン、右側は行 3 を回り込む
    want[~g] = np.inf
    check("grid_distances", "壁を回り込む距離 = 6 + c − r(右側)", "(0,5) = 11・(0,3) = 9",
          "(0,5) = %g・(0,3) = %g" % (d[0, 5], d[0, 3]), np.array_equal(d, want))
    g2 = g.copy()
    g2[3, 2] = False                                           # 通り道も塞ぐ → 右側は届かない
    d2 = AF.grid_distances(g2, (0, 0))
    check("grid_distances", "通り道を塞ぐと右側は inf", "右側 12 マス inf", "inf %d マス" % int(np.isinf(d2[:, 3:]).sum()),
          int(np.isinf(d2[:, 3:]).sum()) == 12 and np.array_equal(d2[:, :2], want[:, :2]))
    paths = [[(1, 0), (1, 1), (1, 2), (1, 3), (1, 3), (1, 3)],     # 3 手で着いて居座る
             [(0, 0), (0, 1), (0, 2), (0, 1), (0, 1), (0, 1)],     # t = 1 に通り過ぎ、t = 3 に戻って着く
             [(2, 2)]]                                             # 最初から目的地
    check("plan_cost", "最後に着いた時刻の和 3 + 3 + 0", "6", str(AF.plan_cost(paths)), AF.plan_cost(paths) == 6)
    empty = False
    try:
        AF.plan_cost([])
    except ValueError:
        empty = True
    check("plan_cost", "空の計画は拒む", "ValueError", "ValueError" if empty else "通った", empty)


def run():
    t0 = time.perf_counter()
    part_polygons()
    part_buildings()
    part_terrain()
    part_lidar()
    part_grid()
    return time.perf_counter() - t0


if __name__ == "__main__":
    sec = run()
    ng = [op for op, ok in _ROWS if not ok]
    print("city & terrain: %d op / %d 検査 / NG %d / %.2f s" % (len({op for op, _ in _ROWS}), len(_ROWS), len(ng), sec))
    if ng:
        print("FAILED:", sorted(set(ng)))
        raise SystemExit(1)
    print("PASS")

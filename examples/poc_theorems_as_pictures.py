# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 定理が門になる図 —— きれいな絵に、絵の外から答え合わせをする

アポロニウスの円、フォードの円、測地ドーム、葉序の螺旋、IFS のフラクタル、
空間充填曲線。どれも**きれいなので、合っているかを誰も確かめない**絵である。
実装が少し間違っていても、円は詰まるし螺旋は回るしフラクタルはフラクタルに見える。

★**この回の規律**: 使った式で答え合わせをしない。真値は次のどれかに限った。

1. **デカルトの円定理** —— 接している 4 円は `(Σk)² = 2Σk²` を満たす。生成は
   反射 `k' = 2(k1+k2+k3) − k4` で行うので、**接触を距離から探し直して**定理に
   入れれば、中心の計算が正しいかまで一度に効く。さらに `(−1, 2, 2, 3)` から
   始めた充填は**どこまで行っても曲率が整数**(Lagarias–Mallows–Wilks)——
   実装が少しずれれば整数から外れる、絵では絶対に見えない種類の誤り。
2. **整数の等式 |ps − qr| = 1** —— フォード円が接するのはこのときに限る。
   こちらは 2 次元の距離を測り、あちらは整数を見る。1 組でも食い違えば落ちる。
3. **オイラーの公式** —— 測地ドームは、どれだけ細分しても**次数 5 の頂点が
   ちょうど 12 個**。次数は**既存の別実装**(`conngraph.graph_degree_table`)に
   数えさせる —— 自分で数え直して自分と一致しても、何も確かめたことにならない。
4. **フィボナッチの斜列** —— 葉序の螺旋は角度をどう選んでも螺旋に見えるので、
   絵を見ずに近傍の**番号差**を数える。黄金角のときだけ 8, 13, 21, 34, 55 に
   山が立つ。
5. **モランの式と既存 op** —— 相似次元 `Σrᵢᵈ = 1` は**描く前に**解ける。
   描いた点のほうは既存 `fractal_dimension`(箱数え)が測る。導出も入力も
   違うので、一致は偶然では起きない。
6. **置換であること** —— 空間充填曲線は 4ⁿ 点をちょうど 1 回ずつ通り、隣は必ず
   距離 1。局所性は主張でなく**表**にする(ヒルベルトは √k、走査線は k)。

図:
1. ``apollonian``: 充填と、段ごとの円の数・整数の曲率。
2. ``ford``: フォードの円と、接触が整数の等式と一致すること。
3. ``dome``: 測地ドームの三角形分割と、次数 5 の 12 個。
4. ``phyllotaxis``: 黄金角と対照群を並べる。
5. ``parastichy``: 番号差の山(フィボナッチかどうか)。
6. ``ifs``: 4 つのアトラクタと、閉形式 vs 箱数え。
7. ``curves``: 空間充填曲線 4 種。
8. ``locality``: 局所性の表。
9. ``numbers``: 数表。

走らせ方: ``py -3.11 examples/poc_theorems_as_pictures.py``
(図は ``out/figures/poc_theorems_as_pictures/``)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

CHECKS = []


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s%s" % ("OK" if ok else "NG", label,
                           ("  —— " + detail) if detail else ""))
    return bool(ok)


def _raster_points(pts, shape=(420, 420), pad=0.06, radius=0.9, extent=None):
    """点群を白地に黒で焼く(図のためだけ。測るのは op のほう)。

    ★*extent* は ``(lo, hi)`` の共通座標系。**複数回に分けて焼くときは必ず渡す** ——
    渡さないと呼び出しごとに自分の外接矩形へ正規化され、三角形 1 枚ずつを焼いた
    図が「各三角形が画面いっぱいに伸びた線の山」になる(実測。数値の検査は
    20 件とも通っていたので、図を開くまで気づけなかった)。
    """
    p = np.asarray(pts, dtype=np.float64)
    lo, hi = (p.min(axis=0), p.max(axis=0)) if extent is None else extent
    span = np.maximum(hi - lo, 1e-12).max()
    h, w = shape
    s = (1.0 - 2.0 * pad) * min(h, w) / span
    c = (p - (lo + hi) / 2.0) * s
    rr = c[:, 1] * -1.0 + h / 2.0
    cc = c[:, 0] + w / 2.0
    img = np.ones(shape, dtype=np.float64)
    k = int(np.ceil(radius + 0.5))
    br, bc = np.floor(rr).astype(int), np.floor(cc).astype(int)
    for dr in range(-k, k + 2):
        for dc in range(-k, k + 2):
            ri, ci = br + dr, bc + dc
            ok = (ri >= 0) & (ri < h) & (ci >= 0) & (ci < w)
            if not ok.any():
                continue
            dist = np.hypot(ri[ok] - rr[ok], ci[ok] - cc[ok])
            np.minimum.at(img, (ri[ok], ci[ok]),
                          1.0 - np.clip(radius - dist + 0.5, 0.0, 1.0))
    return img


def _raster_edges(V2, edges, shape=(460, 460), pad=0.06, width=1.0, per=48):
    """辺の集合を**ひとつの座標系で一度に**焼く(三角形ごとに焼かない)。"""
    V2 = np.asarray(V2, dtype=np.float64)
    lo, hi = V2.min(axis=0), V2.max(axis=0)
    a = V2[edges[:, 0]]
    b = V2[edges[:, 1]]
    t = np.linspace(0.0, 1.0, per)[None, :, None]
    dense = (a[:, None, :] * (1.0 - t) + b[:, None, :] * t).reshape(-1, 2)
    return _raster_points(dense, shape, pad, radius=width * 0.5, extent=(lo, hi))


def _raster_polyline(pts, shape=(420, 420), pad=0.06, width=1.0):
    """折れ線を、線分に沿って密に打ち直してから焼く。"""
    p = np.asarray(pts, dtype=np.float64)
    seg = np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1]))
    t = np.concatenate([[0.0], np.cumsum(seg)])
    if t[-1] <= 0:
        return np.ones(shape, dtype=np.float64)
    span = max((p.max(axis=0) - p.min(axis=0)).max(), 1e-12)
    m = int(np.clip(t[-1] / span * min(shape) * 2.0, p.shape[0], 400_000))
    want = np.linspace(0.0, t[-1], m)
    dense = np.stack([np.interp(want, t, p[:, 0]),
                      np.interp(want, t, p[:, 1])], axis=1)
    return _raster_points(dense, shape, pad, radius=width * 0.5)


def _raster_circles(x, y, r, shape=(520, 520), pad=0.04, width=1.0, keep=None):
    """円の**輪郭**を焼く。円ごとに外接矩形だけを触る(全画面走査は無駄)。"""
    x = np.asarray(x, float); y = np.asarray(y, float); r = np.asarray(r, float)
    sel = np.ones(x.shape, bool) if keep is None else np.asarray(keep, bool)
    lo = np.array([np.min(x[sel] - r[sel]), np.min(y[sel] - r[sel])])
    hi = np.array([np.max(x[sel] + r[sel]), np.max(y[sel] + r[sel])])
    span = max((hi - lo).max(), 1e-12)
    h, w = shape
    s = (1.0 - 2.0 * pad) * min(h, w) / span
    cx = (x - (lo[0] + hi[0]) / 2.0) * s + w / 2.0
    cy = -(y - (lo[1] + hi[1]) / 2.0) * s + h / 2.0
    rr = r * s
    img = np.ones(shape, dtype=np.float64)
    for i in np.flatnonzero(sel):
        rad = rr[i]
        if rad < 0.7:
            continue
        r0 = int(max(0, np.floor(cy[i] - rad - 2)))
        r1 = int(min(h, np.ceil(cy[i] + rad + 2)))
        c0 = int(max(0, np.floor(cx[i] - rad - 2)))
        c1 = int(min(w, np.ceil(cx[i] + rad + 2)))
        if r1 <= r0 or c1 <= c0:
            continue
        yy, xx = np.mgrid[r0:r1, c0:c1]
        d = np.abs(np.hypot(xx - cx[i], yy - cy[i]) - rad)
        img[r0:r1, c0:c1] = np.minimum(img[r0:r1, c0:c1],
                                       np.clip(d - width * 0.5 + 0.5, 0.0, 1.0))
    return img


def _adjacency_from_faces(V, F):
    """面から無向の隣接行列を作る(既存 op に次数を数えさせるための入口)。"""
    n = V.shape[0]
    W = np.zeros((n, n), dtype=np.float64)
    for a, b, c in F:
        for i, j in ((a, b), (b, c), (c, a)):
            W[int(i), int(j)] = W[int(j), int(i)] = 1.0
    return W


# --------------------------------------------------------------------------- #
def chapter_apollonian():
    print("\n1. アポロニウスの窓 —— 円の 1 つ 1 つが定理を背負う")
    t = fs.ledger.circle_packing_apollonian(curvatures=(-1.0, 2.0, 2.0, 3.0), depth=4)
    x, y, r, k, lv = t["x"], t["y"], t["radius"], t["curvature"], t["depth"]
    counts = [int((lv == i).sum()) for i in range(5)]
    print("   段ごとの円の数:", counts, " 合計", len(x))
    check(len(x) == 2 * 3 ** 4 + 2, "円の総数が 2·3^depth + 2",
          "%d 個(depth=4)" % len(x))

    off = float(np.abs(k - np.round(k)).max())
    check(off < 1e-6, "★曲率が最後まで整数のまま(整数充填)",
          "最大ずれ %.2e" % off)

    # 接触を距離から探し直して、デカルトの円定理に入れる
    z = x + 1j * y
    n = len(x)
    tangent = np.zeros((n, n), dtype=bool)
    for i in range(n):
        d = np.abs(z - z[i])
        tangent[i] = (np.isclose(d, r + r[i], rtol=1e-9, atol=1e-12)
                      | np.isclose(d, np.abs(r - r[i]), rtol=1e-9, atol=1e-12))
        tangent[i, i] = False
    worst, quads = 0.0, 0
    for i in range(n):
        for j in range(i + 1, n):
            if not tangent[i, j]:
                continue
            for m in range(j + 1, n):
                if not (tangent[i, m] and tangent[j, m]):
                    continue
                for q in range(m + 1, n):
                    if tangent[i, q] and tangent[j, q] and tangent[m, q]:
                        ks = k[[i, j, m, q]]
                        lhs, rhs = float(ks.sum()) ** 2, 2.0 * float((ks ** 2).sum())
                        worst = max(worst, abs(lhs - rhs) / max(abs(lhs), abs(rhs), 1.0))
                        quads += 1
    print("   接している 4 円の組: %d" % quads)
    check(quads >= 20, "接する 4 円が多数見つかる", "%d 組" % quads)
    check(worst < 1e-9, "★その全部でデカルトの円定理が成り立つ",
          "相対ずれの最大 %.2e" % worst)

    uniq = len({(round(float(a), 9), round(float(b), 9), round(float(c), 9))
                for a, b, c in zip(x, y, r)})
    check(uniq == len(x), "同じ円を二度描いていない", "一意 %d / %d" % (uniq, len(x)))

    try:
        fs.ledger.circle_packing_apollonian(curvatures=(-1.0, 2.0, 2.0, 4.0))
        check(False, "定理を満たさない四つ組を拒否", "拒否しなかった")
    except ValueError as e:
        check("Descartes" in str(e), "定理を満たさない四つ組は fail-closed",
              str(e)[:70])

    if figs.enabled():
        figs.save("apollonian",
                  _raster_circles(x, y, r, keep=(np.abs(k) < 240.0)),
                  caption="アポロニウスの窓(種 (-1, 2, 2, 3)、depth 4 = %d 円)。"
                          "接している 4 円 %d 組すべてでデカルトの円定理が成り立ち"
                          "(相対ずれ最大 %.1e)、曲率は最後まで整数のまま"
                          "(ずれ最大 %.1e)。図は半径が 1 画素を割る円を省いている。"
                          % (len(x), quads, worst, off), gray=True)
        figs.save_plot("apollonian_counts",
                       [("円の数", np.arange(len(counts), dtype=float),
                         np.asarray(counts, dtype=float))],
                       xlabel="段", ylabel="その段で生まれた円",
                       title="段ごとの円の数 —— 種だけ 4 方向、以降は 3 方向",
                       caption="合計は 2·3^depth + 2。種の四つ組だけ 4 方向に反射し、"
                               "以降は 3 方向 —— ここを 4 のままにすると親を作り直して"
                               "depth 3 で 56 個のはずが 88 個になる(一意な円は 56 の"
                               "ままなので、絵は正しく見える)。")
    return {"circles": len(x), "quads": quads, "descartes_worst": worst,
            "integer_off": off}


# --------------------------------------------------------------------------- #
def chapter_ford():
    print("\n2. フォードの円 —— 接触は幾何でなく整数が決める")
    t = fs.ledger.ford_circles(max_denominator=12)
    p, q, x, y, r = t["p"], t["q"], t["x"], t["y"], t["radius"]
    print("   分母 12 までのフォード円: %d 個" % len(p))

    def phi(m):
        c = 0
        for a in range(1, m + 1):
            u, v = a, m
            while v:
                u, v = v, u % v
            c += (u == 1)
        return c

    want = 1 + sum(phi(kk) for kk in range(1, 13))
    check(len(p) == want, "★個数がオイラーの関数の和と一致(|F_n| = 1 + Σφ)",
          "%d = %d" % (len(p), want))

    agree, disagree, touching = 0, 0, 0
    for i in range(len(p)):
        for j in range(i + 1, len(p)):
            d = float(np.hypot(x[i] - x[j], y[i] - y[j]))
            geom = bool(np.isclose(d, r[i] + r[j], rtol=1e-11, atol=1e-14))
            ints = abs(int(p[i]) * int(q[j]) - int(q[i]) * int(p[j])) == 1
            agree += (geom == ints)
            disagree += (geom != ints)
            touching += geom
    check(disagree == 0, "★接触が |ps − qr| = 1 と完全に一致",
          "一致 %d 組・不一致 %d 組(接触 %d 組)" % (agree, disagree, touching))
    check(np.allclose(r, 0.5 / q ** 2.0, rtol=1e-12), "半径が 1/(2q²)")

    if figs.enabled():
        figs.save("ford", _raster_circles(x, y, r, shape=(320, 900), pad=0.02),
                  caption="フォードの円(分母 12 まで、%d 円)。接しているのは %d 組で、"
                          "それは |p·s − q·r| = 1 を満たす組と**完全に一致**した"
                          "(不一致 %d 組)。円は (p/q, 1/(2q²)) に載るので、接触の判定は"
                          "2 次元の距離で見る —— x の差だけで測ると 0/1 と 1/9 のような"
                          "組を取り逃す。" % (len(p), touching, disagree), gray=True)
    return {"circles": len(p), "touching": touching, "disagree": disagree}


# --------------------------------------------------------------------------- #
def chapter_dome():
    print("\n3. 測地ドーム —— オイラーの公式が 5 角形を 12 個に縛る")
    import conngraph
    rows = []
    ok = True
    for freq in (1, 2, 3, 4, 6):
        V, F = fs.ledger.geodesic_dome(frequency=freq)
        W = _adjacency_from_faces(V, F)
        deg = conngraph.graph_degree_table(W)["in_degree"]
        n5, n6 = int((deg == 5).sum()), int((deg == 6).sum())
        edges = int(W.sum() // 2)
        euler = V.shape[0] - edges + F.shape[0]
        rows.append((freq, V.shape[0], edges, F.shape[0], n5, n6, euler))
        ok &= (n5 == 12 and euler == 2)
        print("   f=%d  V=%4d E=%5d F=%4d  次数5=%2d 次数6=%4d  V−E+F=%d"
              % (freq, V.shape[0], edges, F.shape[0], n5, n6, euler))
    check(ok, "★どの分割でも次数 5 の頂点がちょうど 12 個・V−E+F=2",
          "f = 1, 2, 3, 4, 6 で確認")
    V, F = fs.ledger.geodesic_dome(frequency=4)
    rad = np.linalg.norm(V, axis=1)
    check(float(np.abs(rad - 1.0).max()) < 1e-12, "全頂点が半径 1 の球面上",
          "最大ずれ %.2e" % float(np.abs(rad - 1.0).max()))

    if figs.enabled():
        V3, F3 = fs.ledger.geodesic_dome(frequency=3)
        W3 = _adjacency_from_faces(V3, F3)
        d3 = conngraph.graph_degree_table(W3)["in_degree"]
        front = V3[:, 2] > -0.05
        # ★手前側の**辺**を集めて、ひとつの座標系で一度に焼く。三角形を 1 枚ずつ
        #   焼くと、呼び出しごとに自分の外接矩形へ正規化されて図が壊れる。
        ij = np.argwhere(np.triu(W3, 1) > 0)
        ij = ij[front[ij[:, 0]] & front[ij[:, 1]]]
        wire = _raster_edges(V3[:, :2], ij, (460, 460), width=1.1)
        pent = np.minimum(wire, _raster_points(
            V3[(d3 == 5) & front][:, :2], (460, 460), pad=0.06, radius=5.0,
            extent=(V3[:, :2].min(axis=0), V3[:, :2].max(axis=0))))
        figs.save_grid("dome", [wire, pent],
                       captions=["三角形分割(f=3、手前側)",
                                 "同じ図に次数 5 の頂点を重ねた(手前側のぶん)"],
                       title="測地ドーム —— 5 角形の芯はいつも 12 個",
                       caption="分割 f を 1, 2, 3, 4, 6 と上げても、次数 5 の頂点は"
                               "**ちょうど 12 個**から動かない(次数 6 だけが増える)。"
                               "次数は既存の `graph_degree_table` に数えさせている ——"
                               "自分で数え直して自分と一致しても確かめたことにならない。"
                               "V − E + F はどの f でも 2。", gray=True)
        figs.save_plot("dome_degrees",
                       [("次数 5", np.array([float(r[0]) for r in rows]),
                         np.array([float(r[4]) for r in rows])),
                        ("次数 6", np.array([float(r[0]) for r in rows]),
                         np.array([float(r[5]) for r in rows]))],
                       xlabel="分割数 f", ylabel="頂点の数",
                       title="次数 5 は 12 で動かない",
                       caption="オイラーの公式 V − E + F = 2 の帰結。11 個でも 13 個でも"
                               "球にならないので、これは実装の都合ではない。")
    return {"rows": rows}


# --------------------------------------------------------------------------- #
def chapter_phyllotaxis():
    print("\n4. 葉序 —— 螺旋は角度を選ばないが、フィボナッチは黄金角だけ")
    fib = {1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233}

    def peaks(angle, n=800):
        pts = fs.ledger.phyllotaxis_pattern(n_points=n, angle_deg=angle)
        counts = fs.ledger.neighbour_index_gaps(pts, k=6)
        order = np.argsort(counts)[::-1]
        return pts, [int(g) for g in order[:7] if counts[g] > 0]

    golden_pts, golden = peaks(None)
    ctrl_pts, ctrl = peaks(137.0)
    ninety_pts, ninety = peaks(90.0)
    g_hit = sum(1 for g in golden if g in fib)
    c_hit = sum(1 for g in ctrl if g in fib)
    n_hit = sum(1 for g in ninety if g in fib)
    print("   黄金角      番号差の山:", golden, " フィボナッチ %d/7" % g_hit)
    print("   137.0 度    番号差の山:", ctrl, " フィボナッチ %d/7" % c_hit)
    print("    90.0 度    番号差の山:", ninety, " フィボナッチ %d/7" % n_hit)
    check(g_hit >= 6, "★黄金角では山がフィボナッチ数に立つ", "%d/7" % g_hit)
    check(g_hit > c_hit and g_hit > n_hit, "対照群(137.0 度・90 度)と区別できる",
          "%d 対 %d 対 %d" % (g_hit, c_hit, n_hit))

    if figs.enabled():
        figs.save_grid("phyllotaxis",
                       [_raster_points(golden_pts, radius=1.6),
                        _raster_points(ctrl_pts, radius=1.6),
                        _raster_points(ninety_pts, radius=1.6)],
                       captions=["黄金角 137.50776°", "137.0°(対照群)", "90°(対照群)"],
                       ncols=3, title="どの角度でも「それらしい螺旋」は出る",
                       caption="3 枚とも螺旋に見える。だから絵では決まらない ——"
                               "隣の**番号差**を数えると、フィボナッチ数に山が立つのは"
                               "黄金角だけだった(%d/7 対 %d/7)。"
                               % (g_hit, c_hit), gray=True)
        counts_g = fs.ledger.neighbour_index_gaps(golden_pts, k=6)
        counts_c = fs.ledger.neighbour_index_gaps(ctrl_pts, k=6)
        gmax = int(min(len(counts_g), len(counts_c), 100))
        gx = np.arange(gmax, dtype=float)
        figs.save_plot("parastichy",
                       [("黄金角", gx, counts_g[:gmax].astype(float)),
                        ("137.0°(対照群)", gx, counts_c[:gmax].astype(float))],
                       xlabel="番号差", ylabel="近傍の組数",
                       title="斜列(parastichy)を絵に頼らず数える",
                       caption="黄金角の山は %s —— すべてフィボナッチ数。対照群の山は"
                               " %s で、フィボナッチに乗るのは %d/7 だけ。"
                               % (golden, ctrl, c_hit))
    return {"golden": golden, "ctrl": ctrl, "ninety": ninety,
            "g_hit": g_hit, "c_hit": c_hit}


# --------------------------------------------------------------------------- #
def chapter_ifs():
    print("\n5. IFS —— 描く前に解ける次元と、描いてから数える次元")
    import ops as _ops
    table = dict(_ops.OPS)
    box_op = table.get("fractal_dimension")
    rows, clouds = [], {}
    ok_closed = True
    for preset, closed in (("sierpinski", np.log(3) / np.log(2)),
                           ("koch", np.log(4) / np.log(3)),
                           ("cantor_dust", np.log(4) / np.log(3)),
                           ("dragon", 2.0)):
        d = float(fs.ledger.ifs_similarity_dimension(preset))
        pts = fs.ledger.ifs_fractal(preset, n_points=40000, seed=0)
        clouds[preset] = pts
        box = float("nan")
        if box_op is not None:
            g = np.zeros((256, 256), dtype=np.float64)
            qq = pts - pts.min(axis=0)
            qq = qq / max(qq.max(), 1e-12) * 255.0
            g[qq[:, 1].astype(int).clip(0, 255), qq[:, 0].astype(int).clip(0, 255)] = 1.0
            box = float(np.asarray(box_op(g, 0.5, 0.5)).reshape(-1)[0])
        rows.append((preset, d, closed, box))
        ok_closed &= abs(d - closed) < 1e-9
        print("   %-12s モラン %.4f  閉形式 %.4f  箱数え %.4f"
              % (preset, d, closed, box))
    check(ok_closed, "★モランの式が閉形式と 9 桁一致", "4 つの preset")
    if box_op is not None:
        gap = max(abs(r[1] - r[3]) for r in rows if np.isfinite(r[3]))
        check(gap < 0.35, "既存 op(箱数え)とも同じ水準",
              "最大の差 %.3f(有限点数で箱数えは上に出る)" % gap)
    try:
        fs.ledger.ifs_similarity_dimension("barnsley_fern")
        check(False, "相似でない写像を拒否", "拒否しなかった")
    except ValueError as e:
        # ★判定は "is not a similarity" で行う。"similarit" だけで見ると
        #   **op 名 `ifs_similarity_dimension` そのものに当たって必ず通る** ——
        #   最初それで書いており、しかも preset 名を間違えて("fern"、正しくは
        #   "barnsley_fern")未知 preset の拒否を見ていたのに OK が出ていた。
        check("is not a similarity" in str(e),
              "★相似でない写像(バーンズリーのシダ)には使えないと拒否",
              str(e)[:72])

    if figs.enabled():
        figs.save_grid("ifs",
                       [_raster_points(clouds[k0], radius=0.7) for k0 in clouds],
                       captions=["%s  モラン %.4f / 箱数え %.4f"
                                 % (r0[0], r0[1], r0[3]) for r0 in rows],
                       ncols=4, title="描く前に解ける次元と、描いてから数える次元",
                       caption="モランの式 Σrᵢᵈ = 1 は**写像の縮小率だけ**から d を出す。"
                               "箱数えは**描いた点**を数える。導出も入力も違うので、"
                               "一致は偶然では起きない(有限の点数では箱数えが上に出る)。"
                               "シダ(barnsley_fern)は相似でない写像を含むので、"
                               "モランの式は使えないと op が拒否する。", gray=True)
    return {"rows": rows}


# --------------------------------------------------------------------------- #
def chapter_curves():
    print("\n6. 空間充填曲線 —— 抜けも重複もない、という主張を数える")
    kinds = ("hilbert", "moore", "boustrophedon", "row_major")
    summary, curves = [], {}
    ok_perm = True
    for kind in kinds:
        pts = fs.ledger.space_filling_curve(kind, 5)
        curves[kind] = pts
        n = 32
        uniq = len({(int(a), int(b)) for a, b in pts})
        step = np.abs(np.diff(pts, axis=0)).sum(axis=1)
        adjacent = bool(np.all(step == 1))
        closed = int(np.abs(pts[0] - pts[-1]).sum()) == 1
        summary.append((kind, uniq == n * n, adjacent, closed))
        ok_perm &= (uniq == n * n)
        print("   %-14s 置換 %-5s 隣接 %-5s 閉 %-5s"
              % (kind, uniq == n * n, adjacent, closed))
    check(ok_perm, "★どれも 4^n 点をちょうど 1 回ずつ通る", "order 5 = 1,024 点")
    check(dict((s[0], s[2]) for s in summary)["row_major"] is False,
          "走査線(row_major)は隣接でない = 対照群", "行の端で跳ぶ")
    check(dict((s[0], s[3]) for s in summary)["moore"] is True,
          "★ムーア曲線だけ閉じている", "ヒルベルトは閉じない")

    h = fs.ledger.curve_locality(curves["hilbert"])
    b = fs.ledger.curve_locality(curves["boustrophedon"])
    print("   番号差 :", list(h["gap"]))
    print("   ヒルベルト:", [round(float(v), 2) for v in h["ratio"]])
    print("   走査線   :", [round(float(v), 2) for v in b["ratio"]])
    far = h["gap"] >= 2
    check(bool(np.all(b["ratio"][far] > h["ratio"][far])),
          "★局所性はヒルベルトが常に上(主張でなく表)",
          "番号差 2 以上の全部で")

    if figs.enabled():
        figs.save_grid("curves",
                       [_raster_polyline(fs.ledger.space_filling_curve(k1, 4)
                                         .astype(float), width=1.2) for k1 in kinds],
                       captions=list(kinds), ncols=4,
                       title="空間充填曲線 —— 抜けも重複もない、を数で言う",
                       caption="order 5 で 4^5 = 1,024 点をちょうど 1 回ずつ通り、隣り"
                               "合う点は必ず距離 1。row_major(走査線)は行の端で跳ぶので"
                               "隣接が成り立たない = 対照群。閉じているのは moore だけ。",
                       gray=True)
        figs.save_plot("locality",
                       [("hilbert", h["gap"].astype(float), h["ratio"]),
                        ("boustrophedon", b["gap"].astype(float), b["ratio"]),
                        ("√k(参考)", h["gap"].astype(float),
                         np.sqrt(h["gap"].astype(float)))],
                       xlabel="番号差 k", ylabel="平均距離(k=1 を 1 とする)",
                       title="局所性は主張でなく表",
                       caption="ヒルベルトは √k の近くを通り(k=32 で %.2f)、走査線は"
                               "ほぼ k に比例する(%.2f)。「ヒルベルトは局所性が良い」は"
                               "こう measurable にして初めて主張になる。"
                               % (h["ratio"][-1], b["ratio"][-1]))
    return {"summary": summary, "hilbert": [float(v) for v in h["ratio"]],
            "raster": [float(v) for v in b["ratio"]]}


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    print(__doc__.strip().split("\n")[0])
    a = chapter_apollonian()
    f = chapter_ford()
    d = chapter_dome()
    p = chapter_phyllotaxis()
    i = chapter_ifs()
    c = chapter_curves()

    if figs.enabled():
        rows_t = [
            ["アポロニウス(depth 4)", "円の数 / 接する 4 円",
             "%d 円 / %d 組" % (a["circles"], a["quads"]), "2·3^4 + 2 = 164"],
            ["デカルトの円定理", "(Σk)² − 2Σk² の相対ずれ",
             "%.1e" % a["descartes_worst"], "0(定理)"],
            ["整数充填", "曲率の整数からのずれ", "%.1e" % a["integer_off"],
             "0(Lagarias–Mallows–Wilks)"],
            ["フォードの円(分母 12)", "接触と |ps − qr| = 1 の不一致",
             "%d 組" % f["disagree"], "0(整数の等式)"],
            ["フォードの円の個数", "|F_n|", "%d" % f["circles"],
             "1 + Σφ(k) = %d" % f["circles"]],
            ["測地ドーム", "次数 5 の頂点(f = 1, 2, 3, 4, 6)", "すべて 12",
             "12(オイラーの公式)"],
            ["葉序(黄金角)", "番号差の山がフィボナッチ",
             "%d / 7" % p["g_hit"], "対照群 137.0° は %d / 7" % p["c_hit"]],
            ["IFS シェルピンスキー", "相似次元",
             "%.4f" % i["rows"][0][1], "log3/log2 = %.4f(箱数え %.3f)"
             % (i["rows"][0][2], i["rows"][0][3])],
            ["空間充填曲線", "4^5 点の置換・隣は距離 1", "4 種すべて成立",
             "置換(定義)"],
            ["局所性 k=32", "ヒルベルト / 走査線",
             "%.2f / %.2f" % (c["hilbert"][-1], c["raster"][-1]), "√32 = 5.66 / 32"],
        ]
        figs.save_table("numbers", ["主張", "測った量", "実測", "真値 / 期待"],
                        rows_t,
                        title="定理が門になる図 —— 絵の外から当てた答え",
                        caption="どの行も「使った式」ではない真値で採点している: "
                                "デカルトの円定理、整数充填、|ps − qr| = 1、"
                                "オイラーの関数の和、オイラーの公式(既存 "
                                "graph_degree_table が数えた)、フィボナッチ、"
                                "モランの式と既存 fractal_dimension、置換であること。")
    # ★図の書き出しが失敗したら、ここで拾う。見ないと「検査は全部 OK・でも図は
    #   1 枚も出ていない」が黙って通る(examplefig は fail-soft で貯める)。
    assert not figs.errors(), figs.errors()
    bad = [c for c in CHECKS if not c[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)"
          % (len(CHECKS), len(CHECKS) - len(bad), time.time() - t0))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()

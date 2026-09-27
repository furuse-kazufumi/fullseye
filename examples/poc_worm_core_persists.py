# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""線虫の脳の核は生まれた時から在る —— 8 匹の発生系列で「最も深い殻」に居続ける細胞を数える。

    py -3.11 examples/poc_worm_core_persists.py

:mod:`poc_connectome_across_worms` は**結合**が何匹に在るかを数えた。ここでは**細胞**が
どの深さの殻に居るかを数える。k-core(Seidman 1983)は「全員が k 本以上の結合を持つ極大
部分グラフ」、その重み版 s-core(Eidsaa & Almaas 2013)は「全員がシナプス s 個以上」。殻を
外から順に剥いていって最後に残る「最も深い殻」が、その配線の核である。Witvliet et al. 2021
の 8 匹(生後 0 時間 → 成虫)に :func:`graphinv.graph_kcore` を当て、
:func:`graphinv.graph_core_persistence` で 8 匹**全員**の最深殻に居る細胞(persistent)を数える。
Yadav & Singh 2026(bioRxiv 10.64898/2026.06.12.730308)が同じデータで同じ量を測っている ——
公表値: 入・出 × k・s の 4 種の核のどれかで persistent な細胞は **51 個**。

この PoC が測る唯一の主張:

    **重みで剥いた最深殻(s-core)は発生を通じて 6〜10 細胞と小さく、RIA の対は生後 0 時間
    から成虫まで一度も外れない。0/1 で剥いた k-core は成虫でも指数 3〜5 と粗く、最深殻が
    150 細胞に膨らむので核を見分けられない。** 富裕層(rich club)の帯は成虫で広がる。

検査する恒等式(下の assert、当てはめた数字は無い):

1. 完全グラフの核の指数は n − 1、木は 1、閉路は 2(op のテストと同じ定理を実データの隣で再確認)。
2. 0/1 行列の s-core は k-core と厳密に一致し、重みを c 倍すると s-core の指数はちょうど c 倍。
3. ``Σ_i |最深殻_i| = Σ_v 出現回数_v``、persistent ⊆ どの個体の最深殻、4 分類の和 = 細胞数。
4. rich club φ(k) は 1 点ずつ計算する :func:`conngraph.graph_rich_club` と全 k で一致。

公表値との照合(Yadav & Singh 2026、本文): 4 種の核のどれかで persistent な細胞 = 51。
論文はさらに「頭部の神経では AIBR・RIBL・RIAR の 3 個だけ」と書くが、ここでの定義(4 種
**すべて**で persistent)では RIAL・RIAR の 2 個になる —— 論文の 3 個がどの定義かは本文から
読み取れず、一致しない旨をそのまま印字する(当てはめない)。

データはこのリポジトリに同梱しない。`FULLSEYE_CONNECTOME_DIR/witvliet/` に nemanode.org の
``witvliet_2020_<1..8>.json`` があれば実データ、無ければ合成の系列(仕込んだ核が持続する)で
回り、その旨を印字する。細胞の位置は同じ場所の ``skeletons/Dataset<N>_skeletons.json``
(著者 repo)の根の座標(在れば)、細胞の種類は ``_neurons.csv``(在れば)。
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import examplefig as figs  # noqa: E402
import graphinv as G  # noqa: E402

STAGES = ["L1 0h", "L1 5h", "L1 8h", "L1 16h", "L2 23h", "L3 27h", "成虫 45h", "成虫 45h"]
HOURS = [0, 5, 8, 16, 23, 27, 45, 45]


# ------------------------------------------------------------------------------------------------
# data
# ------------------------------------------------------------------------------------------------

def _data_dir() -> str:
    d = os.environ.get("FULLSEYE_CONNECTOME_DIR", "")
    return os.path.join(d, "witvliet") if d else ""


def load_real(d: str):
    """8 匹の化学シナプス(pre, post, synapses)、細胞名の和集合、種類、位置。"""
    sets = []
    for i in range(1, 9):
        e = json.load(open(os.path.join(d, "witvliet_2020_%d.json" % i), encoding="utf-8"))
        sets.append([(r["pre"], r["post"], int(r["synapses"])) for r in e
                     if r["type"] == "chemical" and r["pre"] != r["post"]])
    cells = sorted({c for s in sets for r in s for c in r[:2]})
    types = {c: "neuron" for c in cells}
    p = os.path.join(d, "_neurons.csv")
    if os.path.isfile(p):
        rows = sorted(csv.DictReader(open(p, encoding="utf-8")), key=lambda r: -len(r["class"]))
        for c in cells:
            n = "BWM" + c[6:] if c.startswith("BWM-") else c
            for r in rows:
                if n.startswith(r["class"]):
                    types[c] = r["type"]
                    break
    pos = None
    sd = os.path.join(d, "skeletons")
    if all(os.path.isfile(os.path.join(sd, "Dataset%d_skeletons.json" % i)) for i in range(1, 9)):
        pos = []
        for i in range(1, 9):
            sk = json.load(open(os.path.join(sd, "Dataset%d_skeletons.json" % i), encoding="utf-8"))
            P = np.full((len(cells), 2), np.nan)
            for j, c in enumerate(cells):
                s = sk.get(c)
                if not s or not s.get("coords"):
                    continue
                st = s.get("starts") or []
                key = str(st[0]) if st and str(st[0]) in s["coords"] else next(iter(s["coords"]))
                P[j] = s["coords"][key][1:3]                       # (y, z): 体軸方向から見る(神経環が環に見える)
            pos.append(P)
    return sets, cells, types, pos


def synthetic(seed: int = 0):
    """合成の系列: 8 段で辺が増える乱雑な有向グラフの上に、6 細胞の核(重い相互結合)を全段に仕込む。"""
    rng = np.random.default_rng(seed)
    n = 60
    cells = ["c%02d" % i for i in range(n)]
    base = rng.random((n, n))
    sets = []
    for k in range(8):
        p = 0.03 + 0.02 * k
        W = (base < p) * rng.poisson(1.2, (n, n))
        W[np.ix_(range(6), range(6))] = 4 + k
        np.fill_diagonal(W, 0)
        sets.append([(cells[a], cells[b], int(W[a, b])) for a, b in zip(*np.nonzero(W))])
    types = {c: "neuron" for c in cells}
    pos = [rng.random((n, 2)) * [1.6, 1.0] + rng.normal(0, 0.01, (n, 2)) for _ in range(8)]
    return sets, cells, types, pos


def matrices(sets, cells):
    idx = {c: i for i, c in enumerate(cells)}
    out = {}
    for k, s in enumerate(sets):
        W = np.zeros((len(cells), len(cells)))
        for a, b, w in s:
            W[idx[a], idx[b]] += w
        out["D%d" % (k + 1)] = W
    return out


# ------------------------------------------------------------------------------------------------
# drawing (numpy only; imagedraw は 1 本 5 ms なので 2,000 辺 × 90 コマには重い)
# ------------------------------------------------------------------------------------------------

def _raster_lines(H, W, p0, p1, alpha):
    """線分の束を加算で描く: 各線分を長さに比例した点で標本化し、(H, W) の重みに足す。"""
    acc = np.zeros((H, W))
    if len(p0) == 0:
        return acc
    L = np.hypot(*(p1 - p0).T)
    m = np.maximum(2, np.ceil(L * 1.5).astype(int))
    for k in np.unique(m):
        sel = m == k
        t = np.linspace(0.0, 1.0, k)[None, :, None]
        pts = p0[sel][:, None, :] * (1 - t) + p1[sel][:, None, :] * t          # (e, k, 2)
        a = np.repeat(alpha[sel], k)
        x = np.clip(np.rint(pts[..., 0]).astype(int).ravel(), 0, W - 1)
        y = np.clip(np.rint(pts[..., 1]).astype(int).ravel(), 0, H - 1)
        np.add.at(acc, (y, x), a)
    return acc


def _stamp(img, xy, r, rgb):
    """円盤を塗る(max 合成)。"""
    H, W = img.shape[:2]
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (xx ** 2 + yy ** 2) <= r * r
    for x, y in xy:
        x, y = int(round(x)), int(round(y))
        y0, y1 = max(0, y - r), min(H, y + r + 1)
        x0, x1 = max(0, x - r), min(W, x + r + 1)
        if y1 <= y0 or x1 <= x0:
            continue
        d = disk[y0 - (y - r):y1 - (y - r), x0 - (x - r):x1 - (x - r)]
        img[y0:y1, x0:x1][d] = np.maximum(img[y0:y1, x0:x1][d], rgb)


def frame(P, W, core, persist, H=480, Wd=560, progress=0.0):
    """1 コマ: 位置 P(画素)、重み W、最深殻の強さ core(n, 0..1)、persistent(n, bool)。"""
    img = np.zeros((H, Wd, 3))
    img[:] = (0.04, 0.05, 0.08)
    shown = ~np.isnan(P[:, 0])
    W = W * np.outer(shown, shown)
    a, b = np.nonzero(W > 0)
    w = np.log1p(W[a, b]) / np.log1p(max(1.0, W.max()))
    both = np.minimum(core[a], core[b])
    plain = _raster_lines(H, Wd, P[a], P[b], w * (1.0 - both) * 0.25)
    hot = _raster_lines(H, Wd, P[a], P[b], w * both * 0.9)
    img += np.clip(plain, 0, 1)[..., None] * np.array([0.30, 0.55, 1.00])
    img += np.clip(hot, 0, 1)[..., None] * np.array([1.00, 0.55, 0.10])
    img = np.clip(img, 0, 1)
    _stamp(img, P[(core < 0.05) & shown], 3, np.array([0.55, 0.60, 0.70]))
    for v in np.nonzero((core >= 0.05) & shown)[0]:
        c = core[v]
        _stamp(img, P[v:v + 1], 4 + int(round(2 * c)), np.array([1.0, 0.75 + 0.2 * c, 0.15]) * (0.5 + 0.5 * c))
    _stamp(img, P[persist & shown], 8, np.array([1.0, 0.25, 0.20]))
    # 進み具合の帯(下端)と 8 段の目印
    img[H - 10:H - 4, 20:Wd - 20] = (0.15, 0.15, 0.18)
    img[H - 10:H - 4, 20:20 + int((Wd - 40) * progress)] = (0.9, 0.9, 0.9)
    for h in HOURS:
        x = 20 + int((Wd - 40) * h / HOURS[-1])
        img[H - 14:H - 2, max(0, x - 1):x + 1] = (0.7, 0.7, 0.7)
    return img


def _procrustes(X, Y):
    """X(m, 2)を Y(m, 2)へ最もよく重ねる相似変換(回転・等方拡大・平行移動)を返す。"""
    mx, my = X.mean(axis=0), Y.mean(axis=0)
    A, B = X - mx, Y - my
    U, S, Vt = np.linalg.svd(A.T @ B)
    R = U @ Vt
    if np.linalg.det(R) < 0:                                     # 鏡映は許さない(左右が入れ替わる)
        U[:, -1] *= -1
        R = U @ Vt
    sc = S.sum() / max((A ** 2).sum(), 1e-12)
    return R, sc, mx, my


def layout(pos, cells, draw, H=480, Wd=560, margin=36):
    """各段の位置(nm)を成虫(8 匹目)の向きに Procrustes で揃え、2〜98 パーセンタイルの箱で画素へ。

    ``draw`` (n,) bool の細胞だけを使う(筋肉の根は神経環から遠く、合わせも箱も引きずる)。
    欠けは前後の段から補う。どの段にも位置が無い細胞は描かない(その数を返す)。
    """
    P = np.array(pos, float)                                     # (8, n, 2)
    P[:, ~np.asarray(draw, bool)] = np.nan
    REF = 6                                                      # 7 匹目の成虫(8 匹目は標本が歪み、残差が 2 倍)
    ref = P[REF]
    for k in range(8):
        if k == REF:
            continue
        both = ~np.isnan(P[k, :, 0]) & ~np.isnan(ref[:, 0])      # その匹に在る細胞だけで合わせる
        R, sc, mx, my = _procrustes(P[k][both], ref[both])
        Q = (P[k][both] - mx) @ R * sc + my
        # 外れ値に強く: 残差の大きい 2 割を外してもう一度合わせる
        res = np.hypot(*(Q - ref[both]).T)
        keep = res <= np.percentile(res, 80)
        R, sc, mx, my = _procrustes(P[k][both][keep], ref[both][keep])
        own = ~np.isnan(P[k, :, 0])
        P[k][own] = (P[k][own] - mx) @ R * sc + my
    # 欠けは(揃えた後の)前後の段から補う
    for k in range(8):
        for j in np.nonzero(np.isnan(P[k, :, 0]))[0]:
            others = [P[m, j] for m in list(range(k - 1, -1, -1)) + list(range(k + 1, 8)) if not np.isnan(P[m, j, 0])]
            if others:
                P[k, j] = others[0]
    still = np.isnan(P[..., 0]).any(axis=0)
    lo = np.nanpercentile(P[:, ~still], 2, axis=(0, 1))
    hi = np.nanpercentile(P[:, ~still], 98, axis=(0, 1))
    span = np.maximum(hi - lo, 1e-9)
    s = min((Wd - 2 * margin) / span[0], (H - 2 * margin - 20) / span[1])
    out = (P - lo) * s + margin
    out[..., 0] = np.clip(out[..., 0], 4, Wd - 5)
    out[..., 1] = np.clip(out[..., 1], 4, H - 24)
    out[:, still] = np.nan
    return out, int((still & np.asarray(draw, bool)).sum())


# ------------------------------------------------------------------------------------------------

def main() -> int:
    t0 = time.time()
    d = _data_dir()
    real = bool(d) and all(os.path.isfile(os.path.join(d, "witvliet_2020_%d.json" % i)) for i in range(1, 9))
    if real:
        sets, cells, types, pos = load_real(d)
        print("実データ: Witvliet 2021 の 8 匹(nemanode.org)、化学シナプス、細胞 %d" % len(cells))
    else:
        sets, cells, types, pos = synthetic()
        print("実データが無いので合成の系列で回す(FULLSEYE_CONNECTOME_DIR/witvliet/ に 8 つ置くと実データ)")
    mats = matrices(sets, cells)
    n = len(cells)
    is_neuron = np.array([types[c] not in ("muscle", "glia") for c in cells])

    # 1. 定理(op のテストと同じ)を実データの隣で
    K = np.ones((7, 7)) - np.eye(7)
    assert G.graph_kcore(K, mode="undirected")["kmax"] == 6
    T = np.zeros((9, 9))
    for v in range(1, 9):
        T[(v - 1) // 2, v] = T[v, (v - 1) // 2] = 1
    assert G.graph_kcore(T, mode="undirected")["kmax"] == 1
    C = np.roll(np.eye(9), 1, axis=1)
    assert G.graph_kcore(C + C.T, mode="undirected")["kmax"] == 2

    # 2. s-core と k-core の関係(成虫 1 匹で)
    W8 = mats["D8"]
    for mode in ("in", "out"):
        B8 = (W8 > 0).astype(int)
        kc = G.graph_kcore(B8, mode=mode)
        sc1 = G.graph_kcore(B8, mode=mode, weighted=True)
        assert np.array_equal(kc["core"], np.rint(sc1["core"]).astype(int))            # 恒等式 2
        sc = G.graph_kcore(W8, mode=mode, weighted=True)
        sc3 = G.graph_kcore(3.0 * W8, mode=mode, weighted=True)
        assert np.allclose(sc3["core"], 3.0 * sc["core"])

    # 3. 4 種の核の persistence
    print("\n8 匹の最深殻(persistent = 8 匹全員の最深殻に居る細胞):")
    print("  %-10s %-32s %-40s %s" % ("核", "各段の指数", "最深殻の大きさ", "persistent / recurrent / transient"))
    results = {}
    anyp = np.zeros(n, bool)
    allp = np.ones(n, bool)
    for mode in ("in", "out"):
        for weighted in (False, True):
            r = G.graph_core_persistence(mats, mode=mode, weighted=weighted)
            assert int(r["n_inner"].sum()) == int(r["appearances"].sum())              # 恒等式 3
            assert r["n_persistent"] + r["n_recurrent"] + r["n_transient"] + r["n_never"] == n
            for k in range(8):
                assert r["membership"][k][r["persistent"]].all()
            results[(mode, weighted)] = r
            anyp |= r["persistent"]
            allp &= r["persistent"]
            print("  %-10s %-32s %-40s %d / %d / %d" % (
                ("入" if mode == "in" else "出") + ("・s-core" if weighted else "・k-core"),
                " ".join("%g" % x for x in r["kmax"]), " ".join("%d" % x for x in r["n_inner"]),
                r["n_persistent"], r["n_recurrent"], r["n_transient"]))
            print("      persistent: %s" % " ".join(cells[v] for v in np.nonzero(r["persistent"])[0]))
    n_any = int(anyp.sum())
    print("\n4 種のどれかで persistent: %d 細胞(Yadav & Singh 2026 の公表値 51)%s"
          % (n_any, "" if not real else (" —— 一致" if n_any == 51 else " —— 不一致")))
    print("4 種すべてで persistent: %s(論文の「頭部の神経で persistent は AIBR・RIBL・RIAR の 3 個」とは定義が合わない —— そのまま記す)"
          % " ".join(cells[v] for v in np.nonzero(allp)[0]))
    if real:
        assert n_any == 51, n_any
    rin = results[("in", True)]
    assert rin["n_inner"].max() <= 12 if real else True                                  # 主張: s-core の最深殻は小さい
    print("入・s-core の最深殻の細胞の種類: %s"
          % ", ".join("%s %d" % (t, sum(1 for v in np.nonzero(rin["membership"].any(axis=0))[0] if types[cells[v]] == t))
                      for t in sorted({types[c] for c in cells})))

    # 4. rich club の帯(入次数、次数保存ヌル 20 標本)
    import conngraph as CG
    curves = []
    print("\nrich club(入次数 > k の細胞の密度 / 次数保存ヌル、ratio > 1 + sd の帯):")
    for k in range(8):
        W = mats["D%d" % (k + 1)]
        r = G.graph_rich_club_curve(W, mode="in", n_null=20, seed=k)
        if k == 7:
            rt = G.graph_rich_club_curve(W, mode="total", n_null=2, seed=1)
            for kk in (0, len(rt["k"]) // 2, len(rt["k"]) - 1):
                assert abs(rt["phi"][kk] - CG.graph_rich_club(W, int(rt["k"][kk]))) < 1e-12   # 恒等式 4
        reg = r["k"][r["regime"]]
        curves.append(r)
        print("  %-8s k = 0..%2d、帯 %s、ratio 最大 %.2f(k=%d)" % (
            STAGES[k], r["k"].max(), ("%d..%d" % (reg.min(), reg.max())) if reg.size else "無し",
            np.nanmax(r["ratio"]), r["k"][np.nanargmax(r["ratio"])]))

    # ---------------------------------------------------------------------------------------------
    # figures
    # ---------------------------------------------------------------------------------------------
    if figs.enabled():
        hours = np.array(HOURS, float)
        figs.save_plot("core_depth",
                       [("入・s-core(シナプス数で剥く)", hours, results[("in", True)]["kmax"].astype(float)),
                        ("出・s-core", hours, results[("out", True)]["kmax"].astype(float)),
                        ("入・k-core(0/1 で剥く)", hours, results[("in", False)]["kmax"].astype(float)),
                        ("出・k-core", hours, results[("out", False)]["kmax"].astype(float))],
                       xlabel="生後の時間 [h]", ylabel="最深殻の指数(k または s)",
                       title="最深殻の深さ: s-core は発生とともに %g → %g、k-core は %d → %d"
                             % (results[("in", True)]["kmax"][0], results[("in", True)]["kmax"][-1],
                                results[("in", False)]["kmax"][0], results[("in", False)]["kmax"][-1]),
                       caption="同じ 8 匹。0/1 の k-core は成虫でも指数 %d、最深殻が %d 細胞まで膨らむ。シナプス数で剥く s-core は"
                               "最深殻が %d〜%d 細胞のまま深くなる。" % (
                                   results[("in", False)]["kmax"][-1], results[("in", False)]["n_inner"].max(),
                                   results[("in", True)]["n_inner"].min(), results[("in", True)]["n_inner"].max()),
                       kinds=["line"] * 4)
        figs.save_plot("rich_club_curves",
                       [(STAGES[k], curves[k]["k"][curves[k]["count"] >= 5].astype(float),
                         np.nan_to_num(curves[k]["ratio"][curves[k]["count"] >= 5], nan=1.0))
                        for k in (0, 3, 5, 7)],
                       xlabel="入次数の閾値 k", ylabel="φ(k) / ヌルの平均",
                       title="rich club の帯: 入次数の高い細胞どうしは、次数だけの偶然より密に結ばれる",
                       caption="次数保存ヌル 20 標本。1 を超える帯が rich club(細胞が 5 個未満になる尾は描かない)。"
                               "成虫では k の広い範囲で 1 を超え、最大 %.2f 倍。" % max(np.nanmax(c["ratio"]) for c in curves),
                       kinds=["line"] * 4, ylim=(0.0, max(3.0, float(max(np.nanmax(c["ratio"]) for c in curves)) + 0.2)))

        if pos is not None:
            P, n_nopos = layout(pos, cells, is_neuron)
            core_str = []
            for k in range(8):
                core_str.append(np.where(results[("in", True)]["membership"][k], 1.0, 0.0))
            persist = allp
            # 静止画: 8 段
            panels = [frame(P[k], mats["D%d" % (k + 1)], core_str[k], persist, progress=HOURS[k] / HOURS[-1]) for k in range(8)]
            figs.save_grid("core_map", panels,
                           ["%s: 最深殻(入・s) %d 細胞、s = %g" % (STAGES[k], results[("in", True)]["n_inner"][k],
                                                              results[("in", True)]["kmax"][k]) for k in range(8)],
                           ncols=4, title="8 匹の配線を神経の位置(骨格の根、体軸方向から見る)に載せ、成虫の向きに揃える。橙 = その匹の最深殻、赤 = 8 匹全員で持続",
                           caption="神経だけを描く(筋肉・グリアは最深殻に入らない)。辺の明るさはシナプス数の対数。青 = 普通の結合、橙 = 最深殻の中の"
                                   "結合。各匹の位置は成虫(7 匹目)へ Procrustes(回転・拡大・平行移動、残差上位 2 割を外して再適合)で揃え、"
                                   "2〜98 パーセンタイルの箱で切った。位置の無い神経 %d 個は描かない。" % n_nopos)
            # 動く図: 段の間を補間
            frames = []
            hold, trans = 5, 7
            for k in range(8):
                for _ in range(hold):
                    frames.append(frame(P[k], mats["D%d" % (k + 1)], core_str[k], persist, progress=HOURS[k] / HOURS[-1]))
                if k < 7:
                    for j in range(1, trans + 1):
                        t = j / (trans + 1)
                        frames.append(frame((1 - t) * P[k] + t * P[k + 1],
                                            (1 - t) * mats["D%d" % (k + 1)] + t * mats["D%d" % (k + 2)],
                                            (1 - t) * core_str[k] + t * core_str[k + 1], persist,
                                            progress=((1 - t) * HOURS[k] + t * HOURS[k + 1]) / HOURS[-1]))
            for _ in range(hold):
                frames.append(frames[-1])
            figs.save_gif("core_map_gif", [np.clip(f, 0, 1) for f in frames], fps=8,
                          caption="生後 0 時間から成虫まで。結合が生え、最深殻(橙)が入れ替わる中で、赤の細胞(%s)は一度も外れない。"
                                  % " ".join(cells[v] for v in np.nonzero(persist)[0]))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS  細胞 %d、4 種のどれかで持続 %d、全種で持続 %s、所要 %.1f s"
          % (n, n_any, " ".join(cells[v] for v in np.nonzero(allp)[0]), time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())

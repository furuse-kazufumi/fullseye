# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""シナプスは神経突起に比例して増えるか —— 8 匹の線虫で、形の成長と配線の成長を細胞ごとに並べる。

    py -3.11 examples/poc_worm_synapses_vs_neurites.py

Witvliet 2021 は、生まれてから成虫までに神経突起の総長が約 5 倍、化学シナプスが約 6 倍になり、
「L1 を除けば、シナプスの数は神経突起の長さに比例して増え、密度は保たれる」と書いている。
また「ハブ(生まれた時点で相手の多い細胞)は入力を不釣り合いに増やすが、出力はそうでない」とも。
この PoC は、同じ 8 匹の骨格(:mod:`treemorph` の tree op)と配線(:mod:`graphinv` の
``graph_strength_growth``)から、その 3 つを数字で確かめ、論文が書いていない **細胞ごと** の対応
(形が伸びた細胞ほどシナプスも増えたか)を測る。

この PoC が測る唯一の主張:

    **系全体では、シナプスの密度は L1 の間に上がり、その後は一定(論文どおり)。ところが細胞ごと
    に見ると、神経突起の伸びとシナプスの増えの対応は弱く(順位相関 0.2 台)、シナプスは形とは
    別の理由で足されている。**

検査する恒等式(下の assert、当てはめた数字は無い):

1. ``graph_strength_growth``: 入力の増分の総和 = 出力の増分の総和 = シナプス総数の差、
   strengthened − weakened + added − lost = その差(整数で厳密)。
2. 細胞ごとのシナプス数(前 + 後)の総和 = 総シナプス数の 2 倍。
3. 細胞ごとのケーブル長の総和 = 総ケーブル長(骨格 1 本ずつ tree_morphometry で測った和)。
4. 密度の門: L1 の間の密度の上がり(4 匹目 / 1 匹目)は、L1 以後の密度の揺れ(最大 / 最小)より
   大きい —— 論文の「L1 を除けば密度は保たれる」を、数字を当てはめずに検査する。
5. 対応の弱さの門: 細胞ごとの順位相関は、細胞をシャッフルした零分布の 97.5 パーセンタイルを
   超える(対応は 0 ではない)が、0.5 には届かない(形だけでは決まらない)。

データ: ``FULLSEYE_CONNECTOME_DIR``(Witvliet の JSON 8 本と skeletons/Dataset*_skeletons.json)。
無ければ合成の 8 段(密度一定の枝と、ハブに偏って足されるシナプス)で回る。生データは commit しない。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "examples"))
import examplefig as figs  # noqa: E402
import graphinv as GI  # noqa: E402
import treemorph as TM  # noqa: E402
from poc_worm_neurites_grow import skeleton_to_swcs  # noqa: E402

STAGES = ["L1 0h", "L1 5h", "L1 8h", "L1 16h", "L2 23h", "L3 27h", "成虫 45h", "成虫 45h #2"]
L1_LAST = 3        # 4 匹目までが L1


def load(d: str):
    """8 段それぞれの {細胞: ケーブル長 [µm]} と、化学シナプスの辺の列。"""
    lengths, edges = [], []
    for i in range(1, 9):
        sks = json.load(open(os.path.join(d, "skeletons", "Dataset%d_skeletons.json" % i), encoding="utf-8"))
        L = {}
        for name, sk in sks.items():
            tot = 0.0
            for swc in skeleton_to_swcs(sk):
                tot += float(TM.tree_morphometry(TM.tree_from_swc(swc))["cable_length"])
            if tot > 0:
                L[name] = tot / 1000.0
        lengths.append(L)
        con = json.load(open(os.path.join(d, "witvliet_2020_%d.json" % i), encoding="utf-8"))
        edges.append([(e["pre"], e["post"], int(e["synapses"])) for e in con if e["type"] == "chemical"])
    return lengths, edges


def synthetic():
    """8 段: 細胞ごとに伸びが違う枝(毎段 ×1.1〜×1.4)。シナプスは 3/4 を長さに比例して、1/4 をでたらめに
    足す(形との対応は弱い)。密度は L1 で上がり、後は一定。"""
    rng = np.random.default_rng(0)
    n = 60
    names = ["N%02d" % k for k in range(n)]
    L = rng.uniform(20, 120, n)
    rate = rng.uniform(1.1, 1.4, n)
    W = np.zeros((n, n))
    lengths, edges = [], []
    for t in range(8):
        if t:
            L = L * rate
        dens = 1.0 + 0.4 * min(t, L1_LAST) / L1_LAST
        target = dens * L.sum() * 0.06
        p = L / L.sum()
        while W.sum() < target:
            if rng.random() < 0.75:
                i, j = rng.choice(n, 2, replace=False, p=p)
            else:
                i, j = rng.choice(n, 2, replace=False)
            W[i, j] += 1
        lengths.append({names[k]: float(L[k]) for k in range(n)})
        edges.append([(names[i], names[j], int(W[i, j])) for i in range(n) for j in range(n) if W[i, j] > 0])
    return lengths, edges


def per_cell_synapses(E):
    s = {}
    for a, b, w in E:
        s[a] = s.get(a, 0) + w
        s[b] = s.get(b, 0) + w
    return s


def matrix(E, names):
    idx = {c: k for k, c in enumerate(names)}
    M = np.zeros((len(names), len(names)))
    for a, b, w in E:
        M[idx[a], idx[b]] += w
    return M


def rank(x):
    return np.argsort(np.argsort(x, kind="stable"), kind="stable").astype(float)


def spearman(x, y):
    return float(np.corrcoef(rank(x), rank(y))[0, 1])


def main() -> None:
    d = os.environ.get("FULLSEYE_CONNECTOME_DIR", "")
    real = bool(d) and os.path.isfile(os.path.join(d, "witvliet_2020_1.json")) and \
        os.path.isdir(os.path.join(d, "skeletons"))
    lengths, edges = load(d) if real else synthetic()
    if not real:
        print("Witvliet のデータが無いので合成の 8 段で回す(FULLSEYE_CONNECTOME_DIR を指すと実データ)")
    src = "Witvliet 2021 の 8 匹" if real else "合成 8 段"

    # ---- 1. 系全体: 総長・総数・密度 ------------------------------------------------------
    cable = np.array([sum(L.values()) for L in lengths])
    syn = np.array([sum(w for _, _, w in E) for E in edges], float)
    dens = syn / cable
    print("%s —— 段ごとの神経突起の総長、化学シナプス、密度:" % src)
    for k in range(8):
        print("   %-12s 骨格 %3d 本  総長 %8.0f µm  シナプス %5d  密度 %.3f /µm"
              % (STAGES[k], len(lengths[k]), cable[k], syn[k], dens[k]))
    l1_rise = dens[L1_LAST] / dens[0]
    later = dens[L1_LAST:]
    later_spread = later.max() / later.min()
    print("   総長 ×%.2f、シナプス ×%.2f(論文: 約 5 倍・約 6 倍)" % (cable[-1] / cable[0], syn[-1] / syn[0]))
    print("   密度: L1 の間に ×%.2f、L1 以後の揺れは最大/最小 = %.2f → 「L1 を除けば密度は保たれる」%s"
          % (l1_rise, later_spread, "と矛盾しない" if l1_rise > later_spread else "と合わない"))
    assert l1_rise > later_spread, (l1_rise, later_spread)          # 恒等式 4

    # ---- 2. 細胞ごと: 形の伸び vs シナプスの増え(1 匹目 → 8 匹目) ------------------------------
    s1, s8 = per_cell_synapses(edges[0]), per_cell_synapses(edges[-1])
    assert sum(s1.values()) == 2 * syn[0] and sum(s8.values()) == 2 * syn[-1]     # 恒等式 2
    assert abs(sum(lengths[0].values()) - cable[0]) < 1e-9 * cable[0]              # 恒等式 3
    names = sorted(n for n in lengths[0] if n in lengths[-1] and s1.get(n, 0) > 0 and s8.get(n, 0) > 0)
    gl = np.array([np.log(lengths[-1][n] / lengths[0][n]) for n in names])
    gs = np.array([np.log(s8[n] / s1[n]) for n in names])
    rho = spearman(gl, gs)
    rng = np.random.default_rng(0)
    null = np.array([spearman(gl, rng.permutation(gs)) for _ in range(2000)])
    p975 = float(np.percentile(np.abs(null), 97.5))
    dens_cell = np.array([(s8[n] / lengths[-1][n]) / (s1[n] / lengths[0][n]) for n in names])
    print("細胞ごと(%d 細胞、1 匹目 → 8 匹目): 神経突起 ×%.2f(中央値)、シナプス ×%.2f(中央値)、"
          "密度が上がった細胞 %.0f %%" % (len(names), np.exp(np.median(gl)), np.exp(np.median(gs)),
                                      100 * np.mean(dens_cell > 1)))
    print("   伸びと増えの順位相関 %.2f(細胞をシャッフルした零分布の 97.5 %% 点 %.2f)" % (rho, p975))
    assert rho > p975, (rho, p975)                                                # 恒等式 5(前半)
    assert rho < 0.5, rho                                                         # 恒等式 5(後半)
    order = np.argsort(gs - gl)
    print("   形より配線が伸びた細胞:", ", ".join("%s(突起 ×%.1f・シナプス ×%.0f)" % (names[k], np.exp(gl[k]), np.exp(gs[k]))
                                          for k in order[-4:][::-1]))
    print("   配線より形が伸びた細胞:", ", ".join("%s(突起 ×%.1f・シナプス ×%.1f)" % (names[k], np.exp(gl[k]), np.exp(gs[k]))
                                          for k in order[:4]))

    # ---- 3. どこにシナプスが足されたか(graph_strength_growth) ----------------------------------
    cells = sorted(set(a for E in (edges[0], edges[-1]) for a, b, _ in E) | set(b for E in (edges[0], edges[-1]) for a, b, _ in E))
    g = GI.graph_strength_growth(matrix(edges[0], cells), matrix(edges[-1], cells))
    assert g["gain_in"].sum() == g["gain_out"].sum() == g["ds"] == syn[-1] - syn[0]          # 恒等式 1
    assert g["strengthened"] - g["weakened"] + g["added"] - g["lost"] == g["ds"]
    print("新しいシナプス %d 個の行き先: 生まれた時に在った接続を太らせた %d、新しい接続 %d、消えた接続 −%d、細った −%d"
          % (g["ds"], g["strengthened"], g["added"], g["lost"], g["weakened"]))
    print("   生まれた時の相手の数と、増えたシナプスの順位相関: 入力 %.2f / 出力 %.2f(%d 細胞)"
          % (g["rho_in"], g["rho_out"], g["n_ranked"]))
    print("   上位 1 割のハブ(%d 細胞): 生まれた時の入力の取り分 %.0f %% → 増分の取り分 %.0f %%、"
          "出力 %.0f %% → %.0f %%" % (len(g["hubs"]), 100 * g["hub_share_in_a"], 100 * g["hub_share_gain_in"],
                                   100 * g["hub_share_out_a"], 100 * g["hub_share_gain_out"]))

    if figs.enabled():
        x = np.arange(8, dtype=float)
        figs.save_plot("density_by_stage", [("シナプス / µm", x, dens)],
                       xlabel="発生段階(1 匹目 → 8 匹目)", ylabel="シナプス密度 [/µm]",
                       title="密度は L1 の間に上がり、その後の揺れは小さい",
                       caption="%s。化学シナプスの総数を神経突起の総長で割った。L1 の間に ×%.2f、L1 以後の揺れは %.2f。"
                               % (src, l1_rise, later_spread))
        figs.save_plot("cell_growth_scatter", [("細胞", np.exp(gl), np.exp(gs))],
                       xlabel="神経突起の伸び(倍)", ylabel="シナプスの増え(倍)",
                       title="形が伸びた細胞ほどシナプスも増えたか —— 弱い",
                       caption="1 点 = 細胞 %d 個。順位相関 %.2f(零分布 97.5 %% 点 %.2f)。" % (len(names), rho, p975),
                       kinds=["scatter"])
        k = g["degree_a"] > 0
        figs.save_plot("gain_vs_degree", [("入力の増分", g["degree_a"][k].astype(float), g["gain_in"][k]),
                                          ("出力の増分", g["degree_a"][k].astype(float), g["gain_out"][k])],
                       xlabel="生まれた時の相手の数", ylabel="増えたシナプス", title="相手の多い細胞ほど増える —— 入力も出力も",
                       caption="順位相関 入力 %.2f / 出力 %.2f。上位 1 割のハブの取り分は入力 %.0f %% → %.0f %%。"
                               % (g["rho_in"], g["rho_out"], 100 * g["hub_share_in_a"], 100 * g["hub_share_gain_in"]),
                       kinds=["scatter", "scatter"])
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS%s: 総長 ×%.2f・シナプス ×%.2f、密度は L1 で ×%.2f のち揺れ %.2f、細胞ごとの伸びと増えの順位相関 %.2f"
          "(零分布 %.2f)、新しいシナプスの %.0f %% は既存の接続を太らせた。"
          % ("" if real else "(合成)", cable[-1] / cable[0], syn[-1] / syn[0], l1_rise, later_spread, rho, p975,
             100 * g["strengthened"] / g["ds"]))


if __name__ == "__main__":
    main()

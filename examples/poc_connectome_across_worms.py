# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""同じ線虫の配線は、個体が違うとどこまで同じか —— 8 匹の発生系列で「全員に在る結合」を数える。

    py -3.11 examples/poc_connectome_across_worms.py

:mod:`poc_connectome_lr_symmetry` は**1 匹の中**の左右を比べた。ここでは**匹と匹**を比べる。
Witvliet et al. 2021(Nature 596:257)は遺伝的に同一な C. elegans 8 匹の脳(神経環)を
生まれた直後から成虫まで電子顕微鏡で再構成した。同じ細胞名の上に 8 枚の配線を重ね、
各結合が何匹に出るか(出現回数 0..8)を :func:`graphinv.graph_edge_consensus` で数える。

この PoC が測る唯一の主張:

    **8 匹すべてに在る結合は、各個体の次数だけから期待される数(次数保存ヌル)を
    桁違いに超える。ただしその核は結合の一部で、成虫 2 匹どうしの重なり(Jaccard)は
    隣り合う発生段階どうしと同じ程度しかない。** 核は少数の結合でシナプスの過半を担う。

検査する恒等式(下の assert、当てはめた数字は無い):

1. 合成の系列 —— 全個体に共通の核 C 本 + 個体ごとに重ならない固有の結合 u 本 —— では、
   出現回数の分布は ``h[K] = C``・``h[1] = K·u``・他は 0、どの 2 匹の Jaccard も
   ``C / (C + 2u)``、発生順の分類は stable = C・added = u・lost = u・flicker = (K−2)·u。
   すべて整数(Jaccard は整数の比)で厳密に一致する。
2. どの入力でも ``Σ c·h[c] = Σ|E_i|``、分類 4 つの和 = 和集合、シナプスの取り分の和 = 1。
3. ヌルの各標本は各個体の入次数列・出次数列を厳密に保存する(op の中で検査、壊れていれば拒む)。

データはこのリポジトリに同梱しない(nemanode.org のデータには明示のライセンスが無く、
引用の依頼だけがある)。`FULLSEYE_CONNECTOME_DIR/witvliet/` に nemanode.org の
``/api/download-connectivity?datasetId=witvliet_2020_<1..8>`` の JSON があれば実データで、
無ければ合成の系列で回り、その旨を印字する。

公表値との照合(論文 Methods、PMC8756380): 論文は「7 匹以上に在る結合」を stable とし、
成虫の結合の約 43 % が stable とする。細胞単位で素朴に数えると 34 % にしかならない。
著者が公開した結合ごとの分類表(``connection_classifications.csv``、同梱しない)が
`FULLSEYE_CONNECTOME_DIR/witvliet/` に在れば、差を 3 段に分けて印字する: 論文は**左右の対で
まとめた結合**が 7 匹以上に在れば、その対に属する細胞単位の結合 1 本 1 本に stable の札を付ける。
この札の付け方だけで論文の stable を 95 % 以上再現できることを門にする。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import examplefig as figs  # noqa: E402
import graphinv as G  # noqa: E402

N_NULL = 20
IDS = ["witvliet_2020_%d" % i for i in range(1, 9)]
#: 論文 Methods の推定齢(25 °C 換算、時間)。7 と 8 は同齢として扱うと論文に明記。
AGE_H = [0, 5, 8, 16, 23, 27, 45, 45]
STAGE = ["L1 0h", "L1 5h", "L1 8h", "L1 16h", "L2 23h", "L3 27h", "adult 45h", "adult 45h"]
#: 論文の公表値(成虫の結合に占める stable の割合、variable が担うシナプスの割合)
PAPER_STABLE_FRAC, PAPER_VARIABLE_SYN = 0.43, 0.16


def synthetic_series(n: int, K: int, core: int, uniq: int, seed: int):
    """核 core 本を全個体に、固有 uniq 本を個体ごとに重ならず置いた K 枚の配線(重みつき)。"""
    rng = np.random.default_rng(seed)
    cand = np.array([(i, j) for i in range(n) for j in range(n) if i != j])
    pick = rng.choice(len(cand), size=core + K * uniq, replace=False)
    mats = []
    for k in range(K):
        M = np.zeros((n, n))
        for (i, j) in cand[pick[:core]]:
            M[i, j] = rng.integers(3, 9)          # 核は太い
        for (i, j) in cand[pick[core + k * uniq: core + (k + 1) * uniq]]:
            M[i, j] = rng.integers(1, 3)          # 固有は細い
        mats.append(M)
    return mats


def load_witvliet(d: str):
    """8 匹の化学シナプスを、全員に在る細胞名の上の行列にそろえる。"""
    rows = {}
    for i in IDS:
        L = json.load(open(os.path.join(d, i + ".json"), encoding="utf-8"))
        rows[i] = [(x["pre"], x["post"], int(x["synapses"])) for x in L if x["type"] == "chemical"]
    cells = [set(a for a, _, _ in r) | set(b for _, b, _ in r) for r in rows.values()]
    common = sorted(set.intersection(*cells))
    idx = {c: k for k, c in enumerate(common)}
    mats, outside = {}, []
    for i, r in rows.items():
        M = np.zeros((len(common), len(common)))
        out = 0
        for a, b, s in r:
            if a in idx and b in idx:
                M[idx[a], idx[b]] += s
            else:
                out += s
        mats[i] = M
        outside.append((out, sum(s for _, _, s in r)))
    return mats, common, len(set.union(*cells)), outside


def pair_name(c: str, pool) -> str:
    """左右の対の名前(``AVAL`` → ``AVA*``)。相方が ``pool`` に居なければそのまま。"""
    if c[-1:] in ("L", "R") and (c[:-1] + ("R" if c[-1] == "L" else "L")) in pool:
        return c[:-1] + "*"
    return c


def paper_gap(mats, cells, wd, adult):
    """細胞単位の ≥7 / 対単位の札 / 論文の表 の 3 段。表が無ければ None。"""
    path = os.path.join(wd, "connection_classifications.csv")
    if not os.path.isfile(path):
        return None
    import csv
    with open(path, encoding="utf-8") as f:
        cls = {(r["pre"], r["post"]): r["classification"] for r in csv.DictReader(f)}
    pool = set(cells)
    P = [(m > 0) for m in mats.values()]
    edges = [{(cells[i], cells[j]) for i, j in zip(*np.nonzero(p)) if i != j} for p in P]
    occ, pocc = {}, {}
    for e in edges:
        for a, b in e:
            occ[(a, b)] = occ.get((a, b), 0) + 1
        for q in {(pair_name(a, pool), pair_name(b, pool)) for a, b in e}:
            pocc[q] = pocc.get(q, 0) + 1
    ad = edges[adult]
    cell7 = {e for e in ad if occ[e] >= 7}
    pair7 = {e for e in ad if pocc[(pair_name(e[0], pool), pair_name(e[1], pool))] >= 7}
    paper = {e for e in ad if cls.get(e) == "stable"}
    return {"n": len(ad), "cell7": len(cell7), "pair7": len(pair7), "paper": len(paper),
            "paper_in_pair7": len(paper & pair7), "cell7_in_paper": len(cell7 & paper)}


def occupancy_colours(K: int) -> np.ndarray:
    """出現回数 1..K の色。★colorize_depth は入力を自分の値域に正規化し直すので、
    0.25 から始めても最も暗い紫に戻る —— 長い色列を作ってから上 3/4 を選ぶ。"""
    import fullseye as fs
    ramp = np.asarray(fs.colorize_depth(np.linspace(0.0, 1.0, 256)), np.float64)[..., :3].reshape(256, 3)
    return ramp[np.linspace(64, 255, K).round().astype(int)]


def occupancy_frames(P, occ, order, K, scale=3):
    """発生段階ごとのコマ: 在る結合を「全体で何匹に出るか」の色で塗る(尺度は全コマ共通)。"""
    import fullseye as fs
    col = occupancy_colours(K)
    frames = []
    for t in range(P.shape[0]):
        img = np.full(P.shape[1:] + (3,), 0.12)
        on = P[t][np.ix_(order, order)] > 0
        o = occ[np.ix_(order, order)]
        img[on] = col[o[on] - 1]
        img = np.kron(img, np.ones((scale, scale, 1)))
        img = np.asarray(fs.text_box(img, "%s  (worm %d/8, %d edges)" % (STAGE[t], t + 1, int(P[t].sum())),
                                     (6, 6), anchor="lt", font_size=13))
        frames.append(img)
    return frames


def main() -> None:
    # ---- 恒等式 1: 合成の系列で閉形式 ------------------------------------------------
    K, core, uniq = 8, 60, 25
    syn = synthetic_series(40, K, core, uniq, seed=0)
    r = G.graph_edge_consensus(syn, ordered=True, n_null=4)
    h = r["occupancy_hist"]
    assert h == [0, K * uniq] + [0] * (K - 2) + [core], h
    off = r["jaccard"][~np.eye(K, dtype=bool)]
    assert np.all(off == core / (core + 2 * uniq)), off
    assert (r["stable"], r["added"], r["lost"], r["flicker"]) == (core, uniq, uniq, (K - 2) * uniq), r
    assert sum(c * x for c, x in enumerate(h)) == sum(r["edges_per_individual"])
    assert abs(sum(r["synapse_share"]) - 1.0) < 1e-12
    print("恒等式: 核 %d 本 + 固有 %d 本 x %d 匹の合成系列で h[K]=%d・h[1]=%d・Jaccard=%d/%d・"
          "stable/added/lost/flicker=%d/%d/%d/%d がすべて整数で一致"
          % (core, uniq, K, h[K], h[1], core, core + 2 * uniq, core, uniq, uniq, (K - 2) * uniq))

    # ---- 実データ(無ければ合成) --------------------------------------------------------
    d = os.environ.get("FULLSEYE_CONNECTOME_DIR", "")
    wd = os.path.join(d, "witvliet") if d else ""
    real = bool(wd) and all(os.path.isfile(os.path.join(wd, i + ".json")) for i in IDS)
    if real:
        mats, cells, n_union_cells, outside = load_witvliet(wd)
        label = "C. elegans 8 匹・化学シナプス(Witvliet 2021、nemanode.org)"
        print("%s: 8 匹すべてに在る細胞 %d(どれかに在る細胞 %d)。その外に落ちたシナプス: 生直後 %d/%d、成虫 %d/%d"
              % (label, len(cells), n_union_cells, outside[0][0], outside[0][1], outside[-1][0], outside[-1][1]))
    else:
        mats = {i: m for i, m in zip(IDS, synthetic_series(120, 8, 300, 90, seed=3))}
        label = "合成の系列(核 300 本 + 固有 90 本 x 8 匹)"
        print("実データが無いので %s で回す(FULLSEYE_CONNECTOME_DIR/witvliet/ に JSON を置くと実データ)" % label)

    res = G.graph_edge_consensus(mats, ordered=True, n_null=N_NULL)
    K = res["k"]
    h = res["occupancy_hist"]
    nm, ns = res["occupancy_null_mean"], res["occupancy_null_sd"]
    assert sum(c * x for c, x in enumerate(h)) == sum(res["edges_per_individual"])
    assert res["stable"] + res["added"] + res["lost"] + res["flicker"] == res["union"]
    print("結合数(1 匹ずつ): %s、和集合 %d" % (res["edges_per_individual"], res["union"]))
    print("出現回数 c=1..8 の結合数  実測: %s" % h[1:])
    print("                          ヌル: %s(各個体を次数保存で独立に組み替え、%d 標本の平均)"
          % ([round(x, 1) for x in nm[1:]], N_NULL))
    print("8 匹すべてに在る結合: 実測 %d 本 / ヌル 平均 %.1f・最大 %d 本"
          % (h[K], nm[K], res["shared_all_null_max"]))
    share_all_edges = h[K] / res["union"]
    print("その核は和集合の %.0f %% の結合で、シナプス(8 匹の合計)の %.0f %% を担う"
          % (100 * share_all_edges, 100 * res["synapse_share"][K]))
    print("発生順の分類: stable %d / added(途中から在り続ける) %d / lost(途中で消える) %d / flicker %d"
          % (res["stable"], res["added"], res["lost"], res["flicker"]))
    J = res["jaccard"]
    gaps, jv = [], []
    for i in range(K):
        for j in range(i + 1, K):
            gaps.append(abs(AGE_H[j] - AGE_H[i]))
            jv.append(J[i, j])
    gaps, jv = np.array(gaps, float), np.array(jv)
    adj = np.mean([J[i, i + 1] for i in range(K - 2)])
    print("Jaccard: 隣り合う段階の平均 %.2f、生直後 vs 成虫 %.2f / %.2f、同齢の成虫 2 匹 %.2f"
          % (adj, J[0, K - 2], J[0, K - 1], J[K - 2, K - 1]))

    rows = []
    gap = None
    if real:
        P = np.stack([(m > 0) for m in mats.values()])
        for t in range(K):
            np.fill_diagonal(P[t], False)
        occ = P.sum(axis=0)
        for a in (K - 2, K - 1):
            Wa = list(mats.values())[a].copy()
            np.fill_diagonal(Wa, 0)
            st = int((P[a] & (occ >= 7)).sum())
            syn_var = float(Wa[P[a] & (occ < 7)].sum() / Wa.sum())
            rows.append((STAGE[a] + " #%d" % (a + 1), int(P[a].sum()), st, st / P[a].sum(), syn_var))
            print("成虫 #%d: 結合 %d 本のうち 7 匹以上に在る %d 本(%.0f %%、論文の stable ≈ %.0f %%)、"
                  "7 匹未満の結合が担うシナプス %.0f %%(論文の variable は %.0f %%、dynamic を含まない)"
                  % (a + 1, P[a].sum(), st, 100 * st / P[a].sum(), 100 * PAPER_STABLE_FRAC,
                     100 * syn_var, 100 * PAPER_VARIABLE_SYN))
        gap = paper_gap(mats, cells, wd, K - 2)
        if gap is not None:
            n_ = gap["n"]
            print("論文との差の内訳(成虫 #%d、共通 %d 細胞): 細胞単位で 7 匹以上 %.1f %% → 左右の対で 7 匹以上なら"
                  "対の全結合に札 %.1f %% → 論文の表(variable・dynamic を先に除く)%.1f %%。論文の stable %d 本のうち"
                  " %d 本(%.1f %%)を対の札だけで再現"
                  % (K - 1, len(cells), 100 * gap["cell7"] / n_, 100 * gap["pair7"] / n_, 100 * gap["paper"] / n_,
                     gap["paper"], gap["paper_in_pair7"], 100 * gap["paper_in_pair7"] / gap["paper"]))
            assert gap["paper_in_pair7"] >= 0.95 * gap["paper"], gap
            rows.append(("差の内訳 ① 細胞単位で 7 匹以上", n_, gap["cell7"], gap["cell7"] / n_, float("nan")))
            rows.append(("差の内訳 ② 左右の対で 7 匹以上(対の全結合に札)", n_, gap["pair7"], gap["pair7"] / n_, float("nan")))
            rows.append(("差の内訳 ③ 論文の表の stable", n_, gap["paper"], gap["paper"] / n_, float("nan")))
        else:
            print("(著者の分類表 connection_classifications.csv が無いので、論文との差の内訳は出さない)")
        # 実配線の主張(合成では検証しない)
        assert h[K] >= 10 * max(res["shared_all_null_max"], 1), (h[K], res["shared_all_null_max"])
        assert res["synapse_share"][K] > 0.5 and share_all_edges < 0.25, (res["synapse_share"][K], share_all_edges)
        assert J[K - 2, K - 1] < 0.6 and abs(J[K - 2, K - 1] - adj) < 0.1, (J[K - 2, K - 1], adj)
        assert J[0, K - 1] < adj, (J[0, K - 1], adj)
    else:
        print("(合成の系列: 実配線の主張 —— 核がヌルを桁違いに超える・成虫どうしの重なり —— はここでは検証しない)")

    if figs.enabled():
        P = np.stack([(m > 0) for m in mats.values()]).astype(np.int8)
        for t in range(K):
            np.fill_diagonal(P[t], 0)
        occ = P.sum(axis=0)
        order = np.argsort(-(occ.sum(axis=0) + occ.sum(axis=1)), kind="stable")
        import fullseye as fs
        col = occupancy_colours(K)
        img = np.full(occ.shape + (3,), 0.12)
        o = occ[np.ix_(order, order)]
        img[o > 0] = col[o[o > 0] - 1]
        figs.save("occupancy_matrix", np.kron(img, np.ones((3, 3, 1))),
                  caption="%s。行 = 送り手、列 = 受け手(次数の降順)。色 = その結合が 8 匹中何匹に在るか"
                          "(青紫 = 1 匹だけ → 緑 → 黄 = 8 匹全員、背景の暗い灰 = どの個体にも無い。最も暗い紫は背景と紛れるので使わない)。全員に在る核は %d 本。" % (label, h[K]))
        figs.save_gif("wiring_across_development", occupancy_frames(P, occ, order, K), fps=1.5,
                      caption="生まれた直後から成虫まで 8 匹の配線を順に。色は全体での出現回数なので、"
                              "早い段階から在る結合ほど明るい。")
        c = np.arange(1, K + 1, dtype=float)
        lg = lambda v: np.log10(np.maximum(np.asarray(v, float), 0.1))  # noqa: E731
        figs.save_plot("occupancy_vs_null",
                       [("実測", c, lg(h[1:])), ("次数保存ヌル(%d 標本平均)" % N_NULL, c, lg(nm[1:]))],
                       xlabel="何匹に在るか(1..8)", ylabel="log10 結合数(0 は 0.1 に置く)",
                       title="全員に在る結合は偶然の何倍か",
                       caption="ヌルは各個体の入次数・出次数を保ったまま独立に組み替えた配線。8 匹全員に在る結合は"
                               "実測 %d 本、ヌルでは %d 標本の最大でも %d 本。" % (h[K], N_NULL, res["shared_all_null_max"]))
        figs.save_plot("jaccard_vs_age_gap", [("2 匹の組(28 組)", gaps, jv)], kinds=["scatter"],
                       xlabel="2 匹の推定齢の差(時間)", ylabel="Jaccard(有向の結合)",
                       title="齢が離れるほど配線は違う —— が、同齢の成虫どうしも 0.5 程度",
                       caption="横軸 0 の点が同齢の成虫 2 匹(Jaccard %.2f)。隣り合う段階の平均は %.2f。"
                               % (J[K - 2, K - 1], adj))
        figs.save_plot("synapse_share_by_occupancy",
                       [("シナプスの取り分", c, np.array(res["synapse_share"][1:])),
                        ("結合数の取り分", c, np.array(h[1:], float) / res["union"])],
                       kinds=["line", "line"],
                       xlabel="何匹に在るか(1..8)", ylabel="取り分(和 = 1)",
                       title="核は少数の結合で、シナプスの過半を担う",
                       caption="8 匹全員に在る結合は結合数の %.0f %%、シナプスの %.0f %%。"
                               % (100 * share_all_edges, 100 * res["synapse_share"][K]))
        if rows:
            figs.save_table("paper_comparison",
                            ["個体", "結合", "7 匹以上", "割合", "7 匹未満のシナプス"],
                            [[a, str(b), str(c_), "%.0f %%" % (100 * d_), "-" if e != e else "%.0f %%" % (100 * e)]
                             for a, b, c_, d_, e in rows]
                            + [["論文(stable / variable)", "-", "-", "≈ 43 %", "16 %(variable のみ)"]],
                            title="公表値との照合(差は内訳まで分けた)",
                            caption="論文は左右の対でまとめた結合が 7 匹以上に在れば、その対の細胞単位の結合すべてに "
                                    "stable の札を付ける(②)。①→② で %.1f 点上がり、variable と dynamic を先に除く分だけ ③ で %.1f 点下がる。"
                                    % ((100.0 * (gap["pair7"] - gap["cell7"]) / gap["n"], 100.0 * (gap["pair7"] - gap["paper"]) / gap["n"])
                                       if gap else (float("nan"), float("nan"))))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS%s: 8 匹全員に在る結合 %d 本(ヌル最大 %d)、それが担うシナプス %.0f %%、同齢の成虫 2 匹の Jaccard %.2f。"
          "合成系列の閉形式は整数で一致。"
          % ("" if real else "(合成)", h[K], res["shared_all_null_max"], 100 * res["synapse_share"][K], J[K - 2, K - 1]))


if __name__ == "__main__":
    main()

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""40 年前の手作業の配線図と、今の成虫の配線はどれだけ重なるか —— 時代の差を個体の差と並べる。

    py -3.11 examples/poc_connectome_across_decades.py

:mod:`poc_connectome_across_worms` は同じ研究室・同じ手法の 8 匹を比べた。ここでは
**再構成した時代と手法が違う**成虫を並べる。White et al. 1986 は C. elegans の神経系を
電子顕微鏡写真から手作業でたどった最初の完全な配線図で、その成虫 N2U を、
Witvliet et al. 2021 の成虫 2 匹(dataset 7・8)と同じ細胞名の上で重ねる。

この PoC が測る唯一の主張:

    **時代と手法が違う成虫どうしの重なりは、同じ手法の成虫 2 匹どうしより少し低いだけで、
    差の大部分は個体差と同じ大きさに収まる。3 匹すべてに在る結合は、各個体の次数だけ
    から期待される数を桁違いに超える。**

検査する恒等式(下の assert):

1. 同じ配線を 2 回渡すと Jaccard はちょうど 1、出現回数はすべて K。
2. ``Σ c·h[c] = Σ|E_i|`` と、Jaccard 行列の対称性・対角 1。
3. 個体の並びを入れ替えると Jaccard 行列は同じ置換で並び替わるだけ(値は変わらない)。

データはこのリポジトリに同梱しない(nemanode.org。明示のライセンスは無く引用の依頼のみ)。
`FULLSEYE_CONNECTOME_DIR/witvliet/` に ``witvliet_2020_7`` / ``witvliet_2020_8`` /
``white_1986_n2u`` の JSON があれば実データで、無ければ合成(核 + 個体差 + 「古い手法が
細い結合を取りこぼす」を仕込んだもの)で回り、その旨を印字する。

注意(正直な内訳): nemanode 上の N2U は Zhen lab が 2020 年に筋肉の情報を補った版で、
「時代の差」には再注釈の差も含まれる。JSH(White 1986 のもう 1 匹)は L4 幼虫なので成虫の
比較には入れない。
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
IDS = ["witvliet_2020_7", "witvliet_2020_8", "white_1986_n2u"]
LABEL = ["2021 成虫 #7", "2021 成虫 #8", "1986 成虫 N2U"]


def load(d: str):
    rows = {}
    for i in IDS:
        L = json.load(open(os.path.join(d, i + ".json"), encoding="utf-8"))
        rows[i] = [(x["pre"], x["post"], int(x["synapses"])) for x in L if x["type"] == "chemical"]
    cells = [set(a for a, _, _ in r) | set(b for _, b, _ in r) for r in rows.values()]
    common = sorted(set.intersection(*cells))
    ix = {c: k for k, c in enumerate(common)}
    mats = {}
    for i, r in rows.items():
        M = np.zeros((len(common), len(common)))
        for a, b, s in r:
            if a in ix and b in ix:
                M[ix[a], ix[b]] += s
        mats[i] = M
    return mats, common


def synthetic(n=150, seed=4):
    """核(太い)+ 個体ごとの細い結合。3 匹目(「古い手法」)は細い結合の半分を取りこぼす。"""
    rng = np.random.default_rng(seed)
    core = (rng.random((n, n)) < 0.03) * rng.integers(3, 12, (n, n))
    mats = {}
    for k, i in enumerate(IDS):
        thin = (rng.random((n, n)) < 0.03) * rng.integers(1, 3, (n, n))
        if k == 2:
            thin = thin * (rng.random((n, n)) < 0.5)
        M = (core + thin).astype(float)
        np.fill_diagonal(M, 0)
        mats[i] = M
    return mats, ["n%d" % i for i in range(n)]


def main() -> None:
    d = os.environ.get("FULLSEYE_CONNECTOME_DIR", "")
    wd = os.path.join(d, "witvliet") if d else ""
    real = bool(wd) and all(os.path.isfile(os.path.join(wd, i + ".json")) for i in IDS)
    mats, cells = load(wd) if real else synthetic()
    src = "C. elegans 成虫 3 匹(Witvliet 2021 ×2 + White 1986 N2U、nemanode.org)" if real else "合成(核 + 個体差 + 古い手法の取りこぼし)"
    if not real:
        print("実データが無いので合成で回す(FULLSEYE_CONNECTOME_DIR/witvliet/ に JSON を置くと実データ)")

    # ---- 恒等式 -----------------------------------------------------------------------
    A = mats[IDS[0]]
    same = G.graph_edge_consensus([A, A])
    assert np.all(same["jaccard"] == 1.0) and same["occupancy_hist"][2] == same["union"]
    res = G.graph_edge_consensus(mats, n_null=N_NULL)
    h, J = res["occupancy_hist"], res["jaccard"]
    assert sum(c * x for c, x in enumerate(h)) == sum(res["edges_per_individual"])
    assert np.allclose(J, J.T) and np.all(np.diag(J) == 1.0)
    perm = [2, 0, 1]
    rp = G.graph_edge_consensus([mats[IDS[k]] for k in perm])
    assert np.array_equal(rp["jaccard"], J[np.ix_(perm, perm)])
    print("恒等式: 同じ配線 2 回で Jaccard 1・Σ c·h = Σ|E|・対称・並べ替えは置換だけ —— すべて一致")

    same_era = J[0, 1]
    cross = (J[0, 2], J[1, 2])
    print("%s: 共通の細胞 %d、結合 %s" % (src, len(cells), res["edges_per_individual"]))
    print("Jaccard: 同じ手法の成虫 2 匹 %.3f / 1986 N2U と 2021 の 2 匹 %.3f・%.3f(差 %.3f)"
          % (same_era, cross[0], cross[1], same_era - np.mean(cross)))
    print("3 匹すべてに在る結合: %d 本(次数保存ヌル 平均 %.1f・最大 %d、%d 標本)"
          % (h[3], res["occupancy_null_mean"][3], res["shared_all_null_max"], N_NULL))
    # N2U だけに在る結合 / N2U だけに無い結合(2021 の 2 匹には在る)
    P = np.stack([(m > 0) for m in mats.values()])
    for t in range(3):
        np.fill_diagonal(P[t], False)
    only_old = P[2] & ~P[0] & ~P[1]
    missed = ~P[2] & P[0] & P[1]
    W = (mats[IDS[0]] + mats[IDS[1]]) / 2.0
    both_new = P[0] & P[1]
    miss_syn = float(W[missed].mean()) if missed.any() else float("nan")
    kept_syn = float(W[both_new & P[2]].mean())
    print("2021 の 2 匹ともに在るのに 1986 に無い結合 %d 本(平均シナプス %.2f)/ 3 匹とも在る結合の平均 %.2f"
          % (int(missed.sum()), miss_syn, kept_syn))
    print("1986 だけに在る結合 %d 本" % int(only_old.sum()))
    if real:
        assert same_era > max(cross), (same_era, cross)                       # 時代の差はある
        assert same_era - np.mean(cross) < 0.5 * (1.0 - same_era), (same_era, cross)  # が、個体差より小さい
        assert h[3] >= 20 * max(res["occupancy_null_mean"][3], 1.0), (h[3], res["occupancy_null_mean"][3])
        assert miss_syn < kept_syn, (miss_syn, kept_syn)                       # 取りこぼしは細い結合
    else:
        print("(合成: 実配線の主張はここでは検証しない)")

    if figs.enabled():
        figs.save_table("jaccard_across_decades", [""] + LABEL,
                        [[LABEL[i]] + ["%.3f" % J[i, j] for j in range(3)] for i in range(3)],
                        title="時代と手法が違う成虫どうしの重なり(Jaccard)",
                        caption="%s。共通の %d 細胞の上の化学シナプスの有向結合。" % (src, len(cells)))
        c = np.arange(1, 4, dtype=float)
        lg = lambda v: np.log10(np.maximum(np.asarray(v, float), 0.1))  # noqa: E731
        figs.save_plot("occupancy_vs_null_decades",
                       [("実測", c, lg(h[1:])), ("次数保存ヌル(%d 標本平均)" % N_NULL, c, lg(res["occupancy_null_mean"][1:]))],
                       xlabel="何匹に在るか(1..3)", ylabel="log10 結合数(0 は 0.1 に置く)",
                       title="3 匹すべてに在る結合は偶然の何倍か",
                       caption="3 匹すべてに在る結合 %d 本、ヌルの平均 %.1f 本。"
                               % (h[3], res["occupancy_null_mean"][3]))
        # ★2 匹の平均(半整数)を丸めると偶数丸めで奇数/偶数のギザギザが出る —— 合計(整数)で数える
        S2 = mats[IDS[0]] + mats[IDS[1]]
        bins = np.arange(2, 25)

        def hist(mask):
            v = np.clip(S2[mask].astype(int), 2, 24)
            return np.array([np.mean(v == b) for b in bins]) if mask.any() else np.zeros(len(bins))
        figs.save_plot("what_1986_missed",
                       [("2021 の 2 匹に在り 1986 に無い", bins.astype(float), hist(missed)),
                        ("3 匹とも在る", bins.astype(float), hist(both_new & P[2]))],
                       xlabel="2021 の 2 匹の合計シナプス数(24 以上は 24)", ylabel="割合",
                       title="1986 に無い結合は細い",
                       caption="2021 の 2 匹ともに在るのに 1986 に無い結合は平均 %.2f シナプス、3 匹とも在る結合は %.2f。"
                               % (miss_syn, kept_syn))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS%s: 同じ手法の成虫 2 匹 %.3f に対し 1986 N2U との重なり %.3f・%.3f、3 匹共通 %d 本(ヌル %.1f)。"
          % ("" if real else "(合成)", same_era, cross[0], cross[1], h[3], res["occupancy_null_mean"][3]))


if __name__ == "__main__":
    main()

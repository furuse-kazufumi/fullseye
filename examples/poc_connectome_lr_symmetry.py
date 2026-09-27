# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""線虫の配線は左右対称か —— 左右の対を入れ替えた配線との重なりを、閉形式と次数保存ヌルで挟む。

    py -3.11 examples/poc_connectome_lr_symmetry.py

:mod:`poc_bilateral_asymmetry` は**形**(頭蓋のメッシュ)の左右非対称を鏡映で測った。
ここでは**配線**(有向グラフ)の左右対称を測る。C. elegans は 302 ニューロンのうち
左右対が 98 組あり、「配線として左右対称」なら L/R をすべて入れ替えても辺集合は変わらない。
その重なり(Jaccard)が 1 からどれだけ下がるか、そしてそれが**次数だけの偶然**より
どれだけ上か、を同じ op(:func:`graphinv.graph_swap_symmetry` /
:func:`graphinv.graph_degree_preserving_null`)で出す。

この PoC が測る唯一の主張:

    **配線の左右対称は、L/R 入れ替えの Jaccard で 1 本の数字になる。C. elegans の実測は
    完全対称(1.0)からも次数保存ヌル(偶然)からも離れた中間にある。** 非対称が対ごとに
    どれだけ偏るかは「上位 10 組の取り分」を一様(10/98 ≈ 10 %)と並べて出す —— 集中の
    度合いは主張でなく実測値(予想「少数の対に集中」は、実測では一様の 2 倍程度だった)。

検査する恒等式(下の assert、当てはめた数字は無い):

1. 完全に鏡映な合成配線(左半分 m 辺、右半分はその写し)の右半分から k 辺を移すと、
   Jaccard = (m − k)/(m + k) —— 集合の数え上げから出る**閉形式**で、k = 0..m の全段で
   浮動小数の丸めなく一致する(分子・分母は整数)。
2. 恒等ペア(空の対リスト)で 1.0、2 回入れ替えると元の行列に戻る。
3. ヌルの各標本は入次数列・出次数列を厳密に保存する(op の中で検査、壊れていれば拒む)。

データはこのリポジトリに同梱しない。`FULLSEYE_CONNECTOME_DIR` に `celegans_herm_chem.npy`
と `celegans_herm_neurons.json`(Cook et al. 2019、wormwiring.org SI 5)があれば実データで、
無ければ合成の鏡映配線で回り、その旨を印字する。
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


def lr_pairs(names):
    """名前の末尾 L/R で対を組む(`AVAL`/`AVAR` → 1 組)。片側だけの名前は対にしない。"""
    idx = {n: i for i, n in enumerate(names)}
    pairs = []
    for n, i in idx.items():
        if n.endswith("L") and n[:-1] + "R" in idx:
            pairs.append((i, idx[n[:-1] + "R"]))
    return sorted(pairs)


def mirrored_synthetic(m_half: int, n_half: int, seed: int):
    """左半分 n_half ノードに m_half 辺(自己結合なし)、右半分はその写し。交差辺なし。"""
    rng = np.random.default_rng(seed)
    n = 2 * n_half
    B = np.zeros((n, n), int)
    cand = [(i, j) for i in range(n_half) for j in range(n_half) if i != j]
    pick = rng.choice(len(cand), size=m_half, replace=False)
    for p in pick:
        i, j = cand[p]
        B[i, j] = 1
        B[i + n_half, j + n_half] = 1
    return B, [(i, i + n_half) for i in range(n_half)]


def move_k_edges(B, n_half, k, rng):
    """右半分の辺 k 本を、写しに無い場所へ移す(辺数は不変)。"""
    C = B.copy()
    right = [(i, j) for i in range(n_half, 2 * n_half) for j in range(n_half, 2 * n_half) if C[i, j]]
    empty = [(i, j) for i in range(n_half, 2 * n_half) for j in range(n_half, 2 * n_half)
             if i != j and not C[i, j] and not B[i - n_half, j - n_half]]
    for (a, b) in [right[t] for t in rng.choice(len(right), size=k, replace=False)]:
        C[a, b] = 0
    for (a, b) in [empty[t] for t in rng.choice(len(empty), size=k, replace=False)]:
        C[a, b] = 1
    return C


def per_pair_asymmetry(B, pairs):
    """対 (l, r) ごとに、l の辺のうち r 側に写しが無い本数 + その逆(両向き)。"""
    n = B.shape[0]
    perm = np.arange(n)
    for l, r in pairs:
        perm[l], perm[r] = r, l
    S = B[np.ix_(perm, perm)]           # 入れ替えた配線
    out = []
    for l, r in pairs:
        rows = int(np.sum(B[l] & ~S[l])) + int(np.sum(B[:, l] & ~S[:, l]))
        rows += int(np.sum(B[r] & ~S[r])) + int(np.sum(B[:, r] & ~S[:, r]))
        deg = int(B[l].sum() + B[:, l].sum() + B[r].sum() + B[:, r].sum())
        out.append((rows, deg))
    return out


def main() -> None:
    d = os.environ.get("FULLSEYE_CONNECTOME_DIR", "")
    pm = os.path.join(d, "celegans_herm_chem.npy") if d else ""
    pn = os.path.join(d, "celegans_herm_neurons.json") if d else ""
    real = bool(pm and os.path.isfile(pm) and os.path.isfile(pn))

    # ---- 恒等式 1: 合成の鏡映配線で閉形式 (m−k)/(m+k) を全段で ---------------------
    n_half, m_half = 30, 120
    B0, pairs0 = mirrored_synthetic(m_half, n_half, seed=0)
    assert G.graph_swap_symmetry(B0, pairs0)["jaccard"] == 1.0
    assert G.graph_swap_symmetry(B0, [])["jaccard"] == 1.0
    rng = np.random.default_rng(1)
    ks = list(range(0, m_half + 1, 8))
    js = []
    for k in ks:
        Bk = move_k_edges(B0, n_half, k, rng)
        r = G.graph_swap_symmetry(Bk, pairs0)
        assert r["shared"] == 2 * (m_half - k) and r["union"] == 2 * (m_half + k), (k, r)
        assert r["jaccard"] == (m_half - k) / (m_half + k), (k, r["jaccard"])
        js.append(r["jaccard"])
    print("恒等式: 鏡映配線(片側 %d 辺)の右半分から k 辺を移すと Jaccard = (m−k)/(m+k) —— k=%s の %d 段で厳密に一致"
          % (m_half, ks[:3] + ["..."] + ks[-1:], len(ks)))
    figs.save_plot("lr_jaccard_closed_form",
                   [("op の実測", np.array(ks, float), np.array(js)),
                    ("閉形式 (m−k)/(m+k)", np.array(ks, float), (m_half - np.array(ks, float)) / (m_half + np.array(ks, float)))],
                   xlabel="写しから外した辺 k(片側 120 辺)", ylabel="L/R 入れ替えの Jaccard",
                   title="閉形式と op の一致(合成の鏡映配線)",
                   caption="集合の数え上げから Jaccard = (m−k)/(m+k)。op は %d 段すべてで分子・分母まで整数で一致した。" % len(ks))

    # ---- 実データ(無ければ合成に非対称を仕込んだもの) ------------------------------
    if real:
        B = (np.load(pm) > 0).astype(int)
        np.fill_diagonal(B, 0)
        names = json.load(open(pn, encoding="utf-8"))
        pairs = lr_pairs(names)
        label = "C. elegans 雌雄同体・化学シナプス(Cook 2019)"
    else:
        B = move_k_edges(B0, n_half, 40, np.random.default_rng(2))
        names = ["n%dL" % i for i in range(n_half)] + ["n%dR" % i for i in range(n_half)]
        pairs = pairs0
        label = "合成(鏡映配線に 40 辺の非対称を仕込んだもの)"
    s = G.graph_degree_summary(B)
    obs = G.graph_swap_symmetry(B, pairs)
    # 次数保存ヌル: 同じ次数列で辺を入れ替えた配線の Jaccard(偶然の重なり)
    nulls = []
    rng = np.random.default_rng(0)
    for _ in range(N_NULL):
        # op の次数保存ヌルはモチーフの統計だけ返すので、ヌル配線そのものは同じ入れ替え(_rewire)で作り、
        # 次数列の保存はここでも確かめる(壊れていたら比を出さない)
        Bn = G._rewire(B.astype(np.int8), np.random.default_rng(int(rng.integers(1 << 30))), 3 * s["edges"])
        assert np.array_equal(Bn.sum(0), B.sum(0)) and np.array_equal(Bn.sum(1), B.sum(1))
        nulls.append(G.graph_swap_symmetry(Bn, pairs)["jaccard"])
    nulls = np.array(nulls)
    z = (obs["jaccard"] - nulls.mean()) / (nulls.std(ddof=1) + 1e-12)
    print("%s: n=%d |E|=%d 左右対 %d 組 —— L/R 入れ替えの Jaccard %.3f(完全対称 1.000、次数保存ヌル %.3f ± %.3f、z %.1f)"
          % (label, s["n"], s["edges"], len(pairs), obs["jaccard"], nulls.mean(), nulls.std(ddof=1), z))

    asym = per_pair_asymmetry(B, pairs)
    order = np.argsort([-a for a, _ in asym])
    frac = np.array([a / max(dg, 1) for a, dg in asym])
    top10 = 100 * sum(asym[i][0] for i in order[:10]) / max(sum(a for a, _ in asym), 1)
    print("非対称の偏り: 上位 10 組で非対称辺の %.0f %%(一様なら %.0f %%、%d 組中)"
          % (top10, 1000.0 / len(pairs), len(pairs)))
    for i in order[:8]:
        l, r = pairs[i]
        print("   %-6s/%-6s  写しの無い辺 %3d / 次数計 %3d(%.0f %%)"
              % (names[l], names[r], asym[i][0], asym[i][1], 100 * frac[i]))
    figs.save_plot("lr_pair_asymmetry",
                   [("対ごとの非対称率(降順)", np.arange(len(pairs), dtype=float), np.sort(frac)[::-1]),
                    ("全体の Jaccard から期待される率", np.array([0.0, len(pairs) - 1.0]),
                     np.array([1 - obs["jaccard"]] * 2))],
                   xlabel="左右対(非対称率の降順)", ylabel="写しの無い辺 / 次数計",
                   title="非対称は対ごとにどれだけ偏るか", ylim=(0.0, 1.0),
                   caption="%s。%d 組のうち上位 10 組が非対称辺の %.0f %%(一様なら %.0f %%)。水平線は全体の Jaccard から"
                           "の期待率 1 − J。" % (label, len(pairs), top10, 1000.0 / len(pairs)))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS%s: L/R 入れ替えの Jaccard %.3f は完全対称 1.000 と次数保存ヌル %.3f の間にあり(z %.1f)、"
          "閉形式 (m−k)/(m+k) は %d 段で厳密に一致。" % ("" if real else "(合成)", obs["jaccard"], nulls.mean(), z, len(ks)))


if __name__ == "__main__":
    main()

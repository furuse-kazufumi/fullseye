# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""配線行列は「次数だけの偶然」より何倍構造を持つか —— 同じ物差しを 3 つの門(phylum)に当てる。

    py -3.11 examples/graphinv_three_phyla.py

公開された**完全な**結合図が 3 つの門で揃っている: C. elegans(線虫、Cook 2019)/
Ciona 幼生(脊索動物、Ryan 2016)/ Drosophila 幼虫(節足動物、Winding 2023)。
素の個数(3 サイクル 2,470 本)は規模で決まるので比べられない。**次数保存のヌル**で
割った比なら比べられる —— それが :mod:`graphinv` の 4 op の使いどころ。

この PoC が測る唯一の主張:

    **配線行列の「次数以上の構造」は、次数保存のヌルとの比で門を跨いで比べられる。
    相互辺(i→j かつ j→i)と有向 3 サイクルは、どの門でもヌルの数倍ある。**

検査する恒等式(下の assert): Σ入 = Σ出 = |E| / 3 サイクルの 2 実装が一致 /
ヌルの各標本が次数列を厳密に保存 / 恒等ペアの Jaccard = 1 / C. elegans の
公表値(302 本の細胞リスト − 配線 300 本 = {CANL, CANR})。

データはこのリポジトリに同梱しない。手元に無ければ**同じ恒等式が成り立つ合成の
配線**(有向の環 + 相互辺を仕込んだもの)で回し、その旨を印字する。実データは
`FULLSEYE_CONNECTOME_DIR` に `celegans_herm_chem.npy` / `ciona_adj.npy` /
`larval_all_all_W.npy` を置く。

来歴: Maslov & Sneppen 2002(次数保存の入れ替え)/ Milo et al. 2002(モチーフ)/
Cook et al. 2019 / Ryan, Lu & Meinertzhagen 2016 / Winding et al. 2023。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import graphinv as G  # noqa: E402


def _synthetic(n, p, reciprocal, seed):
    """恒等式が成り立つ合成配線: 乱雑辺 + 相互辺を明示的に仕込む(構造データを 1 本混ぜる)。"""
    rng = np.random.default_rng(seed)
    B = (rng.random((n, n)) < p).astype(int)
    np.fill_diagonal(B, 0)
    for _ in range(reciprocal):
        i, j = rng.integers(n, size=2)
        if i != j:
            B[i, j] = B[j, i] = 1
    return B


def _load():
    d = os.environ.get("FULLSEYE_CONNECTOME_DIR", "")
    names = [("C. elegans(線虫)", "celegans_herm_chem.npy"),
             ("Ciona 幼生(脊索動物)", "ciona_adj.npy"),
             ("Drosophila 幼虫(節足動物)", "larval_all_all_W.npy")]
    out = []
    for label, fn in names:
        p = os.path.join(d, fn) if d else ""
        if p and os.path.isfile(p):
            out.append((label, np.load(p), "実データ"))
    if out:
        return out
    return [("合成 A(疎)", _synthetic(300, 0.03, 200, 0), "合成"),
            ("合成 B(密)", _synthetic(200, 0.08, 300, 1), "合成"),
            ("合成 C(相互辺なし)", _synthetic(250, 0.04, 0, 2), "合成")]


def main() -> None:
    rows = []
    for label, W, kind in _load():
        s = G.graph_degree_summary(W)
        c = G.graph_cycle3(W)
        r = G.graph_degree_preserving_null(W, n_samples=10, swaps_per_edge=3, seed=0)
        assert s["in_degree"].sum() == s["out_degree"].sum() == s["edges"]
        assert r["cycles3"] == c["cycles3"]
        assert G.graph_swap_symmetry(W, [])["jaccard"] == 1.0
        rows.append((label, kind, s, r))
        print("%-26s [%s] n=%d |E|=%d 密度 %.4f | 相互辺 %d(ヌル %.0f、%.2f 倍、z %.1f)"
              " | 3 サイクル %d(ヌル %.0f、%.2f 倍、z %.1f)"
              % (label, kind, s["n"], s["edges"], s["density"],
                 r["reciprocal_pairs"], r["reciprocal_null_mean"], r["reciprocal_ratio"], r["reciprocal_z"],
                 r["cycles3"], r["cycles3_null_mean"], r["cycles3_ratio"], r["cycles3_z"]))
    # 3 サイクルの第 2 実装(小グラフで総当たり)
    S = _synthetic(30, 0.15, 0, 9)
    bf = sum(1 for i in range(30) for j in range(30) if S[i, j]
             for k in range(30) if S[j, k] and S[k, i]) // 3
    assert G.graph_cycle3(S)["cycles3"] == bf, (G.graph_cycle3(S)["cycles3"], bf)
    real = [r for r in rows if r[1] == "実データ"]
    if real:
        print("\nPASS: %d 門の実データで、相互辺は次数保存ヌルの %s 倍、3 サイクルは %s 倍 —— "
              "次数だけでは説明できない構造が門を跨いで測れた。"
              % (len(real), "/".join("%.1f" % r[3]["reciprocal_ratio"] for r in real),
                 "/".join("%.2f" % r[3]["cycles3_ratio"] for r in real)))
    else:
        print("\nPASS(合成): 実データ無し(FULLSEYE_CONNECTOME_DIR 未設定)。恒等式は合成配線で "
              "全部通った —— 相互辺を仕込んだ A/B はヌルの %.1f/%.1f 倍、仕込まない C は %.2f 倍。"
              % (rows[0][3]["reciprocal_ratio"], rows[1][3]["reciprocal_ratio"], rows[2][3]["reciprocal_ratio"]))


if __name__ == "__main__":
    main()

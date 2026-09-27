# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""線虫の神経突起は、生まれてから成虫までに何倍に伸びるか —— 8 匹の骨格を op で測り、論文の値と並べる。

    py -3.11 examples/poc_worm_neurites_grow.py

:mod:`poc_connectome_across_worms` は 8 匹の**配線**(誰が誰にシナプスを作るか)を比べた。ここでは
同じ 8 匹の**形**(神経突起の骨格)を測る。Witvliet et al. 2021 は「神経突起の総長は生まれてから
成虫までに 5 倍になった」と書いている。その骨格を SWC の木に直し、fullseye の
:func:`treemorph.tree_from_swc` / :func:`treemorph.tree_morphometry` / :func:`treemorph.tree_sholl`
で測り直す。

この PoC が測る唯一の主張:

    **op で測った神経突起の総長の比(成虫 / 生直後)は、論文の「5 倍」と同じ桁に収まる(4.3 倍)。
    ただし著者自身の骨格ファイルの length を足しても 3.95 倍で、5 倍そのものはこのファイルからは出ない。
    根からの枝沿いの最長距離は、著者が骨格ファイルに書いた節点ごとの距離と一致する。**

検査する恒等式・真値(下の assert):

1. 骨格 → SWC → op の往復で、節点数 = 辺数 + 1、先端 = 1 + Σ(子 − 1)(op の中でも検査)。
2. 断片が 1 つの骨格では、op の ``max_path_length`` が著者の ``dist_to_root`` の最大と相対 1e-8 以内で
   一致する(第 2 実装)。著者の ``dist_to_root`` には座標の無い節点も混ざっているので、座標のある節点だけで比べる。★著者の ``length`` は線分の長さの合計ではない(中央値 0.89 倍、書き出し元の定義で、
   この repo からは確かめられない)ので門にしない —— 最初はこれを門にしかけて、1,586 本中 1,360 本が合わなかった。
4. 骨格の中には途中で途切れて断片が 2 つ以上あるものがある(1 匹あたり 7〜10 本)。断片ごとに木として測り、
   長さは合計する。
3. 3-D の Sholl の曲線の下の面積 = Σ|d_子 − d_親|(閉形式)。

データはこのリポジトリに同梱しない(dwitvliet/nature2021 の ``data/skeletons/DatasetN_skeletons.json``、
リポジトリにライセンスの記載が無い)。`FULLSEYE_CONNECTOME_DIR/witvliet/skeletons/` に 8 つあれば実データ、
無ければ合成の成長する木で回り、その旨を印字する。座標の単位は nm。

正直な内訳: 論文の集計は筋肉などを除いた細胞に絞り(``valid_cells``)、L3 の個体(dataset 6)は標本の縮みを
補正して長さを 1.1 倍している(著者のコード ``upscale_l3``)。ここは骨格ファイルの全ニューロン様の骨格を
そのまま足すので、論文の 5 倍とは母数が違う(同じ桁かだけを見る)。
"""
from __future__ import annotations

import json
import os
import sys
from collections import deque
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import examplefig as figs  # noqa: E402
import treemorph as TM  # noqa: E402

STAGE = ["L1 0h", "L1 5h", "L1 8h", "L1 16h", "L2 23h", "L3 27h", "adult #7", "adult #8"]
PAPER_FOLD = 5.0          # 論文本文「neurite length increased 5-fold」
SHOW = "AVAL"             # Sholl を発生順に並べて見せるニューロン


def skeleton_to_swcs(sk: dict) -> list:
    """著者の骨格(子 -> 親の辞書 + 座標)を、断片ごとの SWC の列に。根から幅優先で番号を振り直す
    (親 id < 子 id)。節点が 2 未満の断片は捨てる。"""
    coords, arbor = sk["coords"], sk["arbor"]
    kids: dict = {}
    for c, p in arbor.items():
        kids.setdefault(str(p), []).append(str(c))
    out, seen = [], 0
    for root in sorted(n for n in coords if n not in arbor):
        order, q = [], deque([root])
        while q:
            n = q.popleft()
            order.append(n)
            q.extend(sorted(kids.get(n, [])))
        seen += len(order)
        if len(order) < 2:
            continue
        new = {n: k + 1 for k, n in enumerate(order)}
        lines = []
        for n in order:
            x, y, z = coords[n]
            # 座標は 6 桁で書く(3 桁だと丸めで最長経路が相対 1.9e-6 ずれ、第 2 実装との一致を濁す)
            lines.append("%d 3 %.6f %.6f %.6f 1 %d" % (new[n], x, y, z, new[str(arbor[n])] if n in arbor else -1))
        out.append("\n".join(lines))
    if seen != len(coords):
        raise ValueError("%s: %d of %d nodes reachable from a root (a cycle?)" % (sk.get("name"), seen, len(coords)))
    return out


def synthetic_series():
    """8 段で枝が伸びて増える合成の木(長さは段ごとに 1.25 倍ずつ)。"""
    out = []
    for t in range(8):
        rng = np.random.default_rng(0)
        pts, lines = [np.zeros(3)], ["1 1 0 0 0 1 -1"]
        n = 60 + 25 * t
        for i in range(2, n + 1):
            p = int(rng.integers(max(1, i - 6), i))
            x = pts[p - 1] + rng.normal(0, 1, 3) * 100 * 1.25 ** t
            pts.append(x)
            lines.append("%d 3 %.3f %.3f %.3f 1 %d" % (i, x[0], x[1], x[2], p))
        out.append({"SYN": {"name": "SYN", "swcs": ["\n".join(lines)], "dist_max": None}})
    return out


def load(d: str):
    series = []
    for i in range(1, 9):
        sks = json.load(open(os.path.join(d, "Dataset%d_skeletons.json" % i), encoding="utf-8"))
        cells = {}
        for name, sk in sks.items():
            swcs = skeleton_to_swcs(sk)
            if swcs:
                one = len([n for n in sk["coords"] if n not in sk["arbor"]]) == 1
                cells[name] = {"name": name, "swcs": swcs, "author_len": float(sk["length"]),
                               # ★dist_to_root には coords に無い節点も入っている(1 匹目で 196 本中 54 本)。
                               #   座標のある節点だけに絞らないと最大値が食い違う(最大 12 倍)。
                               "dist_max": max(sk["dist_to_root"][n] for n in sk["coords"]) if one else None}
        series.append(cells)
    return series


def main() -> None:
    d = os.environ.get("FULLSEYE_CONNECTOME_DIR", "")
    sd = os.path.join(d, "witvliet", "skeletons") if d else ""
    real = bool(sd) and all(os.path.isfile(os.path.join(sd, "Dataset%d_skeletons.json" % i)) for i in range(1, 9))
    series = load(sd) if real else synthetic_series()
    if not real:
        print("実データが無いので合成の成長する木で回す(FULLSEYE_CONNECTOME_DIR/witvliet/skeletons/ に 8 つ置くと実データ)")

    totals, common_tot, worst_rel, n_trees, n_frag, n_checked = [], [], 0.0, 0, 0, 0
    common = set.intersection(*[set(c) for c in series])
    per = []
    for cells in series:
        tot = ctot = 0.0
        m_all = {}
        for name, c in cells.items():
            length = 0.0
            for j, swc in enumerate(c["swcs"]):
                t = TM.tree_from_swc(swc)
                m = TM.tree_morphometry(t)
                s = TM.tree_sholl(t, n_radii=30)
                xyz, pidx = t["xyz"], t["parent_index"]
                dd = np.linalg.norm(xyz - xyz[t["root"]], axis=1)
                k = np.flatnonzero(pidx >= 0)
                assert abs(s["integral"] - float(np.abs(dd[k] - dd[pidx[k]]).sum())) <= 1e-9 * max(1.0, s["integral"])
                length += m["cable_length"]
                if j == 0:
                    m_all[name] = (m, t)
                n_trees += 1
            n_frag += len(c["swcs"]) > 1
            if c["dist_max"]:
                n_checked += 1
                worst_rel = max(worst_rel, abs(m_all[name][0]["max_path_length"] - c["dist_max"]) / c["dist_max"])
            tot += length
            if name in common:
                ctot += length
        totals.append(tot)
        common_tot.append(ctot)
        per.append(m_all)
    fold = totals[-1] / totals[0]
    author = [sum(c.get("author_len") or 0.0 for c in cells.values()) for cells in series]
    fold_a = author[-1] / author[0] if author[0] > 0 else float("nan")
    fold_c = common_tot[-1] / common_tot[0]
    unit = 1e-3 if real else 1.0     # nm -> µm
    print("骨格の木 %d 本(断片に分かれた骨格 %d 個を含む)を SWC -> tree_from_swc -> tree_morphometry に通した"
          "(構造の約束と Sholl の閉形式は全部通過)" % (n_trees, n_frag))
    if real:
        print("断片が 1 つの骨格 %d 本で、op の最長経路と著者の dist_to_root の最大の相対差: 最大 %.2e"
              % (n_checked, worst_rel))
        # 許容 1e-8: SWC に 6 桁で書いた座標の丸め(1 線分あたり最大 √3 × 0.5e-6 nm)が経路に沿って積もる分
        assert n_checked > 1000 and worst_rel < 1e-8, (n_checked, worst_rel)
    for i in range(8):
        print("  %-10s 骨格 %3d 本  総長 %9.0f µm(8 匹に共通の %d 本だけなら %9.0f µm)"
              % (STAGE[i], len(series[i]), totals[i] * unit, len(common), common_tot[i] * unit))
    print("成虫 #8 / 生直後: 総長 %.2f 倍(共通の細胞だけなら %.2f 倍)、論文は約 %.0f 倍" % (fold, fold_c, PAPER_FOLD))
    if real:
        print("  参考: 著者が骨格ファイルに書いた length を足しても %.2f 倍 —— 論文の 5 倍はこのファイルの単純な合計"
              "からは再現できない(集計する細胞・範囲が違う)。同じ桁までは合う。" % fold_a)
    if real:
        assert 3.0 < fold_c < 8.0, fold_c                      # 同じ桁(論文の 5 倍の前後)
    else:
        print("(合成: 論文の値との照合はしない)")

    if figs.enabled():
        x = np.array([0, 5, 8, 16, 23, 27, 45, 45], float) if real else np.arange(8, dtype=float)
        figs.save_plot("neurite_length_growth",
                       [("全骨格の総長 [µm]", x, np.array(totals) * unit),
                        ("8 匹に共通の細胞だけ [µm]", x, np.array(common_tot) * unit)],
                       kinds=["line", "line"], xlabel="推定齢 [時間]" if real else "段",
                       ylabel="神経突起の総長 [µm]", title="神経突起は生まれてから %.1f 倍に伸びる" % fold_c,
                       caption="tree_morphometry のケーブル長の合計(断片は合算)。共通の細胞だけで %.2f 倍、全骨格で %.2f 倍"
                               "(論文は約 %.0f 倍。論文は筋肉などを除き、L3 の個体を縮みの補正で 1.1 倍している)。"
                               % (fold_c, fold, PAPER_FOLD))
        name = SHOW if (real and all(SHOW in p for p in per)) else sorted(common)[0]
        rmax = max(np.linalg.norm(p[name][1]["xyz"] - p[name][1]["xyz"][p[name][1]["root"]], axis=1).max() for p in per)
        radii = (np.arange(40) + 0.5) * rmax / 40
        series_plot = []
        for i in (0, 3, 5, 7):
            t = per[i][name][1]
            series_plot.append((STAGE[i], radii * unit, TM.tree_sholl(t, radii=radii)["crossings"].astype(float)))
        figs.save_plot("sholl_through_development", series_plot, xlabel="骨格の始点からの距離 [µm](始点が細胞体とは限らない)" if real else "距離",
                       ylabel="交点数(3-D Sholl)", title="%s の Sholl 曲線が発生とともに育つ" % name,
                       caption="同じ名前のニューロン %s を 4 つの発生段階で。3-D の Sholl なので回転に依らない。" % name)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS%s: 骨格 %d 本が構造の約束と Sholl の閉形式を通過、神経突起の総長は %.2f 倍(共通の細胞)、論文は約 %.0f 倍。"
          % ("" if real else "(合成)", n_trees, fold_c, PAPER_FOLD))


if __name__ == "__main__":
    main()

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""走行長は小さな融合を許さない —— 同じ誤りを、ERL と VOI は違う重さで数える。

    py -3.11 examples/poc_skeleton_run_length_vs_voi.py

コネクトームの自動切り出しの採点には 2 つの流儀がある。画素(または骨格の節点)の分割表から出す
**VOI**(split / merge)と、正解の骨格の上を「同じ物体のまま何 µm 走れるか」で測る **ERL**
(expected run length、Januszewski 2018)。ERL は融合した走行を 0 とみなす —— 相手がどれほど小さくても。
この PoC は、実物の神経の骨格(Witvliet 2021 の 8 匹、1,727 本)を正解にして、候補のラベル付けを
**仕込んで**(分断と融合を 1 つずつ)、2 つの採点がどこで食い違うかを、閉形式で確かめながら見る。
候補は合成(実物の骨格に誤りを 1 つ入れたもの)で、実際の切り出し器の出力ではない。

この PoC が測る唯一の主張:

    **骨格 a の一部(節点の割合 q)を骨格 b の物体に貼ると、VOI の merge は q → 0 で 0 に向かうが、
    ERL では貼られた側の骨格 b が走行を丸ごと失う(q に依らず損失 1)。a 自身の損失は分断と同じ
    (1 − (1 − q_cable)²)。分断では両者とも「真ん中で切るのがいちばん痛い」で一致する。**

★最初の版は「a の損失が q に依らず一定」と主張していた —— 誤り。ERL が 0 にするのは融合した**物体**
の走行で、a の残り(1 − q)は無傷の走行のまま残る。一定の損失を受けるのは、その物体に丸ごと覆われる b。

検査する恒等式(下の assert、当てはめた数字は無い):

1. 分断 1 つ(辺 e で切る): ERL = (A² + (L − A − |e|)²) / L。A は切った側の部分木のケーブル(第 2 の
   走査で数える)。骨格 1,727 本 × 切る辺 1 本ずつで、全件 1e-9 以内。
2. 同じ分断の VOI(節点をそのまま画素とみて): split = (m/N)·H2(m1/m)(m1 = 切った側の節点数)。全件 1e-12。
3. 融合(骨格 a の遠い側 q を骨格 b の物体に貼る): a の ERL はちょうど (L − A − |e|)²/L(貼った部分 A の
   走行は zero_labels で 0)、b の ERL はちょうど 0、VOI の merge は ((m1 + m2)/N)·H2(m1/(m1 + m2))。
   q を 5 % → 50 % と振ると VOI は単調に増え、b の損失は 1 のまま。
4. 無傷なら ERL = ケーブル長、VOI = 0。走行の和 + 切れ目のケーブル + 背景のケーブル = 全ケーブル(全件)。
5. 分岐の無い骨格をケーブルの上で一様に m 点で切ると、走行の長さの割合は Dirichlet(1, …, 1) に従い
   E[Σ l_i² / L'²] = 2/(m+2)(L' = 切れ目の辺を除いた残り)。分岐の無い骨格の集団で、平均の比が 1 ± 0.05
   に入る(統計の門)。

データ: ``FULLSEYE_CONNECTOME_DIR/skeletons/Dataset*_skeletons.json``。無ければ合成の木で回る。
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
import segcompare as SC  # noqa: E402
import treemorph as TM  # noqa: E402
from poc_worm_neurites_grow import skeleton_to_swcs, synthetic_series  # noqa: E402


def h2(p: float) -> float:
    return 0.0 if p <= 0 or p >= 1 else float(-(p * np.log2(p) + (1 - p) * np.log2(1 - p)))


def load(d: str):
    trees = []
    for i in range(1, 9):
        sks = json.load(open(os.path.join(d, "skeletons", "Dataset%d_skeletons.json" % i), encoding="utf-8"))
        for name, sk in sks.items():
            for swc in skeleton_to_swcs(sk):
                t = TM.tree_from_swc(swc)
                if len(t["id"]) >= 12:
                    trees.append((("%d:%s" % (i, name)), t))
    return trees


def subtree_cable(t, k):
    """節点 k から下の部分木のケーブル(k と親を結ぶ辺は含まない)。第 2 の走査。"""
    pidx = np.asarray(t["parent_index"])
    xyz = np.asarray(t["xyz"], float)
    n = len(pidx)
    below = np.zeros(n, bool)
    below[k] = True
    for _ in range(n):
        new = below[pidx[pidx >= 0]] & ~below[np.flatnonzero(pidx >= 0)]
        if not new.any():
            break
        below[np.flatnonzero(pidx >= 0)[new]] = True
    child = np.flatnonzero(pidx >= 0)
    inside = below[child] & below[pidx[child]]
    return float(np.linalg.norm(xyz[child[inside]] - xyz[pidx[child[inside]]], axis=1).sum()), below


def voi_split(m1, m, N):
    return m / N * h2(m1 / m)


def main() -> None:
    d = os.environ.get("FULLSEYE_CONNECTOME_DIR", "")
    real = bool(d) and os.path.isdir(os.path.join(d, "skeletons"))
    if real:
        trees = load(d)
    else:
        trees = [("SYN%d" % k, TM.tree_from_swc(s["SYN"]["swcs"][0])) for k, s in enumerate(synthetic_series())]
        print("骨格が無いので合成の木 8 本で回す(FULLSEYE_CONNECTOME_DIR を指すと Witvliet の骨格)")
    src = "Witvliet 2021 の骨格 %d 本" % len(trees) if real else "合成の木 %d 本" % len(trees)
    rng = np.random.default_rng(0)

    # ---- 恒等式 4 と 1・2: 無傷、そして分断 1 つ ------------------------------------------------
    worst_erl, worst_voi, n_checked = 0.0, 0.0, 0
    ratio_mid, ratio_end = [], []
    for _name, t in trees:
        n = len(t["id"])
        pidx = np.asarray(t["parent_index"])
        intact = TM.tree_run_length(t, np.ones(n, int))
        L = intact["cable_length"]
        assert abs(intact["erl"] - L) < 1e-9 * max(L, 1) and intact["runs"] == 1
        child = np.flatnonzero(pidx >= 0)
        k = int(rng.choice(child))                          # 切る辺 = 節点 k と親の間
        A, below = subtree_cable(t, k)
        e = float(np.linalg.norm(np.asarray(t["xyz"])[k] - np.asarray(t["xyz"])[pidx[k]]))
        lab = np.where(below, 2, 1)
        r = TM.tree_run_length(t, lab)
        want = (A ** 2 + (L - A - e) ** 2) / L
        worst_erl = max(worst_erl, abs(r["erl"] - want) / max(L, 1e-12))
        assert abs(sum(r["run_lengths"]) + r["cut_cable"] + r["background_cable"] - L) < 1e-9 * max(L, 1)
        v = SC.seg_variation_of_information(np.ones((1, n), int), lab.reshape(1, -1))
        worst_voi = max(worst_voi, abs(v["split"] - voi_split(int(below.sum()), n, n)), v["merge"])
        n_checked += 1
        # 分断の位置: ケーブルの真ん中で切る vs 端で切る(分岐の無い骨格だけ、順序は根から)
        nchild = np.bincount(pidx[child], minlength=n)
        if (nchild <= 1).all():
            order = [int(np.flatnonzero(pidx == -1)[0])]
            while nchild[order[-1]] == 1:
                order.append(int(np.flatnonzero(pidx == order[-1])[0]))
            for frac, bucket in ((0.5, ratio_mid), (0.1, ratio_end)):
                cut = order[max(1, int(round(frac * (n - 1))))]
                lab2 = np.ones(n, int)
                for j in order[order.index(cut):]:
                    lab2[j] = 2
                bucket.append(TM.tree_run_length(t, lab2)["erl"] / L)
    assert worst_erl < 1e-9 and worst_voi < 1e-12, (worst_erl, worst_voi)
    print("%s: 無傷で ERL = ケーブル長、分断 1 つで ERL の閉形式 (A² + (L−A−|e|)²)/L と VOI の (m/N)·H2 が全 %d 本で一致"
          "(最大相対誤差 %.1e / %.1e)" % (src, n_checked, worst_erl, worst_voi))
    if ratio_mid:
        print("   分岐の無い骨格 %d 本: 真ん中で切ると ERL は %.2f L、端(1 割)で切ると %.2f L —— 真ん中がいちばん痛い"
              % (len(ratio_mid), float(np.mean(ratio_mid)), float(np.mean(ratio_end))))
        assert np.mean(ratio_mid) < np.mean(ratio_end)

    # ---- 恒等式 3: 融合の大きさを振る ------------------------------------------------------------
    qs = np.array([0.05, 0.1, 0.2, 0.3, 0.4, 0.5])
    voi_merge = np.zeros(len(qs))
    loss_a = np.zeros(len(qs))
    loss_b = np.zeros(len(qs))
    n_pairs = 0
    worst_merge = 0.0
    for (_na, ta), (_nb, tb) in zip(trees[0::2], trees[1::2]):
        na, nb = len(ta["id"]), len(tb["id"])
        La = TM.tree_run_length(ta, np.ones(na, int))["cable_length"]
        Lb = TM.tree_run_length(tb, np.ones(nb, int))["cable_length"]
        pa = np.asarray(ta["parent_index"])
        xyz = np.asarray(ta["xyz"], float)
        order = [int(np.flatnonzero(pa == -1)[0])]
        seen = set(order)
        while len(order) < na:                              # 幅優先の順(根から遠い側を貼る)
            nxt = [int(c) for c in np.flatnonzero(np.isin(pa, order)) if int(c) not in seen]
            if not nxt:
                break
            order.extend(nxt)
            seen.update(nxt)
        n_pairs += 1
        for qi, q in enumerate(qs):
            m2 = max(1, int(round(q * na)))
            glued = np.zeros(na, bool)
            glued[order[na - m2:]] = True
            lab_a = np.where(glued, 2, 1)                     # 骨格 a の遠い側 q を、骨格 b の物体(2)に貼る
            truth = np.concatenate([np.ones(na, int), np.full(nb, 2)]).reshape(1, -1)
            cand = np.concatenate([lab_a, np.full(nb, 2)]).reshape(1, -1)
            v = SC.seg_variation_of_information(truth, cand)
            N = na + nb
            assert abs(v["merge"] - (m2 + nb) / N * h2(m2 / (m2 + nb))) < 1e-12
            assert abs(v["split"] - voi_split(m2, na, N)) < 1e-12
            voi_merge[qi] += v["merge"]
            ra = TM.tree_run_length(ta, lab_a, zero_labels=[2])      # 物体 2 は骨格 b も覆う = 融合
            rb = TM.tree_run_length(tb, np.full(nb, 2), zero_labels=[2])
            child = np.flatnonzero(pa >= 0)
            inside = glued[child] & glued[pa[child]]
            cut = glued[child] != glued[pa[child]]
            A = float(np.linalg.norm(xyz[child[inside]] - xyz[pa[child[inside]]], axis=1).sum())
            e = float(np.linalg.norm(xyz[child[cut]] - xyz[pa[child[cut]]], axis=1).sum())
            worst_merge = max(worst_merge, abs(ra["erl"] - (La - A - e) ** 2 / La) / La, rb["erl"])
            loss_a[qi] += 1.0 - ra["erl"] / La
            loss_b[qi] += 1.0 - rb["erl"] / Lb
    voi_merge /= n_pairs
    loss_a /= n_pairs
    loss_b /= n_pairs
    assert worst_merge < 1e-9, worst_merge
    print("融合の大きさ q(骨格 a の節点の割合)を振る(%d 組、a の ERL は (L−A−|e|)²/L、b の ERL は 0 と全件一致):" % n_pairs)
    for q, vm, la, lb in zip(qs, voi_merge, loss_a, loss_b):
        print("   q = %.2f: VOI merge %.4f ビット、ERL の損失 a %.3f / b %.3f" % (q, vm, la, lb))
    assert (np.diff(voi_merge) > 0).all(), voi_merge                       # VOI は q で単調に増える
    assert (loss_b == 1.0).all(), loss_b                                   # 貼られた側は q に依らず全部失う
    assert voi_merge[0] < 0.25 * voi_merge[-1], (voi_merge[0], voi_merge[-1])

    # ---- 恒等式 5: 一様な m 点切りの期待値(分岐の無い骨格) ---------------------------------------
    paths = []
    for _name, t in trees:
        pidx = np.asarray(t["parent_index"])
        n = len(pidx)
        if (np.bincount(pidx[pidx >= 0], minlength=n) <= 1).all() and n >= 40:
            order = [int(np.flatnonzero(pidx == -1)[0])]
            while len(order) < n:
                order.append(int(np.flatnonzero(pidx == order[-1])[0]))
            paths.append((t, order))
    ratios = []
    m = 3
    for t, order in paths:
        n = len(order)
        xyz = np.asarray(t["xyz"], float)
        cum = np.concatenate([[0.0], np.cumsum(np.linalg.norm(xyz[order[1:]] - xyz[order[:-1]], axis=1))])
        acc = 0.0
        reps = 40
        for _ in range(reps):
            # 切る位置はケーブル長の上で一様(節点番号の上で一様ではない —— 辺の長さが揃っていないので)
            cuts = np.unique(np.searchsorted(cum, rng.uniform(0, cum[-1], m)).clip(1, n - 1))
            lab = np.ones(n, int)
            for c, pos in enumerate(cuts):
                for j in order[pos:]:
                    lab[j] = c + 2
            r = TM.tree_run_length(t, lab)
            kept = float(sum(r["run_lengths"]))            # 切れ目の辺のケーブルは走行から落ちるので、残りで正規化
            acc += float((r["run_lengths"] ** 2).sum()) / kept ** 2 * (len(cuts) + 2) / 2.0
        ratios.append(acc / reps)
    if paths:
        mean_ratio = float(np.mean(ratios))
        print("分岐の無い骨格 %d 本をケーブルの上で一様に %d 点で切る: 平均 Σl²/L'² ÷ 2/(m+2) = %.3f(Dirichlet の期待値との比)"
              % (len(paths), m, mean_ratio))
        assert abs(mean_ratio - 1.0) < 0.05, mean_ratio

    if figs.enabled():
        figs.save_plot("merge_size_erl_vs_voi",
                       [("VOI の merge [ビット]", qs, voi_merge), ("ERL の損失: 貼った側 a", qs, loss_a),
                        ("ERL の損失: 貼られた側 b", qs, loss_b)],
                       xlabel="融合した部分の割合 q", ylabel="",
                       title="小さな融合を、VOI は小さく、ERL は(貼られた側で)丸ごと数える",
                       caption="%s。骨格 a の遠い側 q を骨格 b の物体に貼った(%d 組の平均)。VOI の merge は q → 0 で 0 に向かい、"
                               "a の損失は分断と同じ 1 − (1 − q)² に従うが、b は q に依らず走行を全部失う。" % (src, n_pairs))
        if ratio_mid:
            figs.save_plot("cut_position_erl",
                           [("真ん中で切る", np.arange(len(ratio_mid), dtype=float), np.array(ratio_mid)),
                            ("端(1 割)で切る", np.arange(len(ratio_end), dtype=float), np.array(ratio_end))],
                           xlabel="分岐の無い骨格(番号)", ylabel="ERL / L",
                           title="分断はどこで切るかで痛さが違う —— 真ん中が最悪",
                           caption="1 点 = 骨格 1 本。真ん中で切ると ERL は L の約 1/2、端で切ると約 0.8 L。",
                           kinds=["scatter", "scatter"])
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS%s: 分断の閉形式が %d 本で一致(ERL 相対 %.0e・VOI %.0e)、融合 q = %.2f で VOI merge %.4f / ERL 損失 a %.2f・"
          "b %.2f、q = %.2f で %.4f / %.2f・%.2f。%s" % ("" if real else "(合成)", n_checked, worst_erl, worst_voi, qs[0], voi_merge[0],
                                                loss_a[0], loss_b[0], qs[-1], voi_merge[-1], loss_a[-1], loss_b[-1],
                                        ("一様 %d 点切りの期待値との比 %.3f。" % (m, mean_ratio)) if paths else ""))


if __name__ == "__main__":
    main()

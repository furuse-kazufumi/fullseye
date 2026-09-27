# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""切り出しの誤りは、配線図のどこを壊すか —— 画素の採点は分断を重く、融合を軽く数える。

    py -3.11 examples/poc_em_wiring_errors.py

コネクトームは、電子顕微鏡(EM)の体積から切り出した神経の上に、シナプスの注釈(前の点・後の点)を
落として読む。切り出しの誤り(分断・融合)は、その配線図の誤りに化ける。ただし全部ではない:
シナプスの無い所で神経を切っても、配線図は 1 本も変わらない。

:mod:`segcompare` の配線 op 2 本で測る:

* ``seg_synapse_partners`` —— シナプスの両端がどの物体に落ちるか(= 分割が言っている配線図)。
* ``seg_wiring_variation`` —— 画素の VOI を **シナプスの端 2n 点だけ**で取り直したもの(split / merge)と、
  シナプスを接続ごとに束ねた VOI(connection_split / connection_merge)。

この PoC が測る唯一の主張:

    **画素の VOI は、配線の損傷の代理としては分断を重く・融合を軽く数える。** CREMI sample A の正解に、
    シナプスのある神経 1 本ずつ「半分に切る」「いちばん広く接する隣と貼る」誤りを仕込み(54 + 54 件)、
    画素の VOI と端の VOI を比べると: 分断の 4 割(23 / 54)は配線を 1 ビットも変えず、画素 1 ビット
    あたりの配線の損傷(中央値)は融合 1.30 に対し分断 0.58。画素の VOI の大きい順に直すのは、でたらめ
    よりはずっと効く(上位 20 件で 41 % 対 19 %)が、配線の順(49 %)には届かない。

検査する恒等式(下の assert、当てはめた数字は無い):

1. 端の水準の閉形式: 神経の端 s 個が s1 / s2 に分かれると split はちょうど (s/2n)·H2(s1/s) ビット、
   端 e1 個と e2 個の神経を貼ると merge はちょうど (e/2n)·H2(e1/e) ビット(e = e1 + e2)。仕込んだ
   **全件**でこの式と一致すること(誤差 < 1e-12)。
2. 第 2 経路: 端の VOI は、端の位置のラベルだけで取った ``seg_variation_of_information`` と同じ。
3. 画素の VOI も閉形式どおり(m/N)·H2(m1/m) —— 前の PoC(分けすぎとまとめすぎ)と同じ門。
4. 正解どうし・付け替えで 0。

誤りは 1 件ずつ独立に仕込むので、「直した割合」は 1 件ごとの損傷の和で数える(誤りどうしの干渉は
測っていない)。

先行研究: シナプスの注釈のある画素だけで VI を取る「synapse VI」は Plaza・Scheffer・Chklovskii 2014
(Focused proofreading, arXiv:1409.1199、NeuroProof の C++)が定義し、split と merge の 2 項に分けている。
端の VOI はその構成と同じ。この PoC のものは、numpy だけの実装、接続ごとの水準、誤りを 1 件ずつ仕込んで
画素と配線の損傷を同じ単位で比べる実験、校正の順番の比較。NRI(Reilly 2018)は端の対の F 値、ERL
(Januszewski 2018)は骨格の走行長で、どちらも情報量ではない。データは CREMI sample A(``FULLSEYE_CREMI`` か ``<FULLSEYE_DATA_DIR か
~/.cache/fullseye>/cremi/sample_A_20160501.hdf``、h5py が要る)の xy の 1/4 の区画(z 全 125 枚)。
生データは commit しない。無ければ合成の 3 次元の細胞で回る。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import examplefig as figs  # noqa: E402
import segcompare as SC  # noqa: E402

CREMI = os.environ.get("FULLSEYE_CREMI") or os.path.join(
    os.environ.get("FULLSEYE_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "fullseye"),
    "cremi", "sample_A_20160501.hdf")
RES = np.array([40.0, 4.0, 4.0])          # CREMI の体素 [nm](z, y, x)


def h2(p: float) -> float:
    return 0.0 if p <= 0 or p >= 1 else float(-(p * np.log2(p) + (1 - p) * np.log2(1 - p)))


def load_cremi(path: str, y0: int = 0, x0: int = 625, size: int = 625):
    """正解の神経ラベル(z 全部 × xy の区画)と、区画に両端が入るシナプス。"""
    if not os.path.isfile(path):
        return None
    try:
        import h5py
    except ImportError:
        return None
    with h5py.File(path, "r") as f:
        lab = f["volumes/labels/neuron_ids"][:, y0:y0 + size, x0:x0 + size]
        ids = f["annotations/ids"][:]
        loc = f["annotations/locations"][:]
        partners = f["annotations/presynaptic_site/partners"][:]
    _u, inv = np.unique(lab, return_inverse=True)
    truth = (inv.reshape(lab.shape) + 1).astype(np.int64)
    pos = {int(i): np.asarray(p, float) for i, p in zip(ids, loc)}
    shift = np.array([0.0, y0 * RES[1], x0 * RES[2]])
    pre = np.array([pos[int(a)] for a, _b in partners]) - shift
    post = np.array([pos[int(b)] for _a, b in partners]) - shift
    ext = RES * truth.shape
    keep = np.all((pre >= 0) & (pre < ext) & (post >= 0) & (post < ext), axis=1)
    return truth, {"pre": pre[keep], "post": post[keep]}, RES, \
        "CREMI sample A(z 125 枚 × xy %d² @ %d,%d)" % (size, y0, x0)


def synthetic(shape=(24, 80, 80), n_cells=40, n_syn=60, seed=0):
    """3 次元ボロノイの細胞と、隣り合う細胞の境界をまたぐシナプス(前後の点は 2 体素離す)。"""
    rng = np.random.default_rng(seed)
    pts = rng.uniform(0, 1, (n_cells, 3)) * shape
    grid = np.stack(np.meshgrid(*[np.arange(s) + 0.5 for s in shape], indexing="ij"), -1)
    lab = np.argmin(((grid[..., None, :] - pts) ** 2).sum(-1), axis=-1) + 1
    pre, post = [], []
    while len(pre) < n_syn:
        p = rng.uniform([1, 1, 1], np.array(shape) - 2)
        d = rng.normal(size=3)
        q = p + 2 * d / np.linalg.norm(d)
        if np.all((q >= 0) & (q < shape)):
            a, b = lab[tuple(p.astype(int))], lab[tuple(q.astype(int))]
            if a != b:
                pre.append(p)
                post.append(q)
    return lab.astype(np.int64), {"pre": np.array(pre), "post": np.array(post)}, np.ones(3), \
        "合成(3 次元ボロノイ %d 細胞、シナプス %d)" % (n_cells, n_syn)


def ranks(x):
    return np.argsort(np.argsort(x, kind="stable"), kind="stable").astype(float)


def spearman(x, y) -> float:
    return float(np.corrcoef(ranks(x), ranks(y))[0, 1])


def end_labels(labels, syn, spacing):
    ends = np.vstack([syn["pre"], syn["post"]])
    idx = np.floor(ends / spacing).astype(int)
    return labels[tuple(idx.T)]


def main() -> None:
    data = load_cremi(CREMI)
    real = data is not None
    truth, syn, spacing, src = data if real else synthetic()
    if not real:
        print("CREMI が無いので合成の 3 次元の細胞で回す(FULLSEYE_CREMI に sample_A_20160501.hdf を置くと実データ)")
    N = truth.size
    w = SC.seg_synapse_partners(truth, syn, spacing=spacing)
    n = w["n"]
    print("%s: 神経 %d 本、シナプス %d 個 → 配線図の接続 %d 本(端が背景 %d、自己結合 %d)"
          % (src, int(truth.max()), n, len(w["edges"]), w["n_background"], w["n_autapse"]))

    # ---- 恒等式 4 ---------------------------------------------------------------------
    assert SC.seg_wiring_variation(truth, truth, syn, spacing=spacing)["voi"] == 0.0
    perm = np.random.default_rng(1).permutation(int(truth.max()) + 1) + 5
    assert SC.seg_wiring_variation(truth, perm[truth], syn, spacing=spacing)["voi"] == 0.0

    ends = end_labels(truth, syn, spacing)
    sizes = np.bincount(truth.ravel())
    on_syn = np.unique(ends)
    new_id = int(truth.max()) + 1
    splits, merges = [], []
    worst_gap = 0.0
    for i in on_syn:
        m = truth == i
        # ---- 半分に切る(x の中央の面で)-------------------------------------------------
        xx = np.nonzero(m)[2]
        part = m.copy()
        part[m] = xx > np.median(xx)
        m1 = int(part.sum())
        cut = np.where(part, new_id, truth)
        v = SC.seg_wiring_variation(truth, cut, syn, spacing=spacing)
        e_cut = end_labels(cut, syn, spacing)
        s = int((ends == i).sum())
        s1 = int(((ends == i) & (e_cut == new_id)).sum())
        want = s / (2 * n) * h2(s1 / s)
        px = sizes[i] / N * h2(m1 / sizes[i])                       # 恒等式 3(前の PoC で門)
        worst_gap = max(worst_gap, abs(v["split"] - want), v["merge"])
        splits.append({"id": int(i), "pixel": px, "wiring": v["split"], "conn": v["connection_split"],
                       "ends": s, "part": part})
        # ---- いちばん広く接する隣と貼る ---------------------------------------------------
        sh = np.zeros_like(m)
        sh[1:] |= m[:-1]
        sh[:-1] |= m[1:]
        sh[:, 1:] |= m[:, :-1]
        sh[:, :-1] |= m[:, 1:]
        sh[:, :, 1:] |= m[:, :, :-1]
        sh[:, :, :-1] |= m[:, :, 1:]
        nb = truth[sh & ~m]
        if nb.size == 0:
            continue
        j = int(np.bincount(nb).argmax())
        glued = np.where(m, j, truth)
        v = SC.seg_wiring_variation(truth, glued, syn, spacing=spacing)
        e1, e2 = int((ends == i).sum()), int((ends == j).sum())
        want = (e1 + e2) / (2 * n) * h2(e1 / (e1 + e2))
        worst_gap = max(worst_gap, abs(v["merge"] - want), v["split"])
        mm = sizes[i] + sizes[j]
        merges.append({"id": int(i), "other": j, "pixel": mm / N * h2(sizes[i] / mm), "wiring": v["merge"],
                       "conn": v["connection_merge"], "ends": e1 + e2})
    # 恒等式 1: 全件で閉形式
    assert worst_gap < 1e-12, worst_gap
    # 恒等式 2: 端の VOI = 端のラベルだけの VOI(最後の融合で)
    x = SC.seg_variation_of_information(ends.reshape(1, -1), end_labels(glued, syn, spacing).reshape(1, -1))
    assert abs(x["merge"] - v["merge"]) < 1e-12 and abs(x["split"] - v["split"]) < 1e-12
    print("仕込んだ誤り: 分断 %d 件・融合 %d 件 —— 端の水準の閉形式と全件で一致(最大誤差 %.1e)"
          % (len(splits), len(merges), worst_gap))

    ps = np.array([r["pixel"] for r in splits])
    ws = np.array([r["wiring"] for r in splits])
    pm = np.array([r["pixel"] for r in merges])
    wm = np.array([r["wiring"] for r in merges])
    zs, zm = int((ws <= 1e-12).sum()), int((wm <= 1e-12).sum())
    print("   分断: 配線を 1 ビットも変えないもの %d / %d 件(切った面の片側にシナプスの端が無い)" % (zs, len(ws)))
    print("   融合: 配線を 1 ビットも変えないもの %d / %d 件" % (zm, len(wm)))
    rs = float(np.median(ws / ps))
    rm = float(np.median(wm / pm))
    print("   画素 1 ビットあたりの配線の損傷(中央値): 分断 %.2f / 融合 %.2f" % (rs, rm))
    pix = np.concatenate([ps, pm])
    wir = np.concatenate([ws, wm])
    rho = spearman(pix, wir)
    print("   画素の VOI と端の VOI の順位相関(全 %d 件): %.2f" % (len(pix), rho))

    # ---- 校正の順番: 画素の VOI の大きい順に直す vs 配線の損傷の大きい順 vs でたらめ ----------------
    total = wir.sum()
    k = np.arange(len(wir) + 1)
    by_pixel = np.concatenate([[0], np.cumsum(wir[np.argsort(-pix, kind="stable")])]) / total
    ideal = np.concatenate([[0], np.cumsum(np.sort(wir)[::-1])]) / total
    rng = np.random.default_rng(0)
    rand = np.mean([np.concatenate([[0], np.cumsum(wir[rng.permutation(len(wir))])]) for _ in range(200)], 0) / total
    k20 = min(20, len(wir))
    print("   上位 %d 件を直すと消える配線の損傷: 画素の VOI の順 %.0f%% / 配線の順(理想) %.0f%% / でたらめ %.0f%%"
          % (k20, 100 * by_pixel[k20], 100 * ideal[k20], 100 * rand[k20]))
    assert ideal[k20] >= by_pixel[k20] - 1e-12 and ideal[k20] >= rand[k20] - 1e-12
    gap = ideal[k20] - by_pixel[k20]

    if figs.enabled():
        figs.save_plot("proofreading_order",
                       [("配線の損傷の大きい順(理想)", k, ideal), ("画素の VOI の大きい順", k, by_pixel),
                        ("でたらめ(200 回の平均)", k, rand)],
                       xlabel="直した誤りの件数", ylabel="消えた配線の損傷の割合",
                       title="画素の VOI の順は、でたらめよりずっと効くが理想には届かない",
                       caption="%s。分断 %d 件・融合 %d 件を 1 件ずつ仕込み、それぞれの配線の損傷(シナプスの端で取った VOI)を"
                               "足し上げた。上位 %d 件で、画素の VOI の順は %.0f%%、配線の順は %.0f%%。"
                               % (src, len(ws), len(wm), k20, 100 * by_pixel[k20], 100 * ideal[k20]))
        figs.save_plot("pixel_vs_wiring_cost",
                       [("分断", ps, ws), ("融合", pm, wm)],
                       xlabel="画素の VOI [ビット]", ylabel="シナプスの端の VOI [ビット]",
                       title="画素で大きい誤りが、配線で大きいとは限らない",
                       caption="1 点 = 仕込んだ誤り 1 件。順位相関 %.2f。分断の %d / %d 件は配線を 1 ビットも変えない(横軸の上に並ぶ)。"
                               % (rho, zs, len(ws)), kinds=["scatter", "scatter"])
        # 対比: 画素では最大級なのに配線は無傷の分断 と、画素 1 ビットあたりで配線を最も壊す分断
        free = [r for r in splits if r["wiring"] <= 1e-12]
        hurt = max(splits, key=lambda r: r["wiring"] / max(r["pixel"], 1e-12))
        if free:
            big = max(free, key=lambda r: r["pixel"])
            panels, caps = [], []
            for r, what in ((big, "画素 %.4f ビット → 配線 0"), (hurt, "画素 %.4f ビット → 配線 %.4f")):
                m = truth == r["id"]
                img = m.max(axis=0).astype(float) * 0.45 + r["part"].max(axis=0) * 0.35
                e = np.floor(np.vstack([syn["pre"], syn["post"]]) / spacing).astype(int)
                on = truth[tuple(e.T)] == r["id"]
                for zz, yy, xx in e[on]:
                    img[max(yy - 3, 0):yy + 4, max(xx - 3, 0):xx + 4] = 1.0
                panels.append(img)
                caps.append((what % ((r["pixel"],) if r is big else (r["pixel"], r["wiring"]))) + "(端 %d 個)" % r["ends"])
            figs.save_grid("two_cuts", panels, caps, ncols=2,
                           title="神経を z 方向に重ねた影。明るい側が切り離した半分、白い四角がシナプスの端")
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS%s: 分断 %d・融合 %d 件の端の VOI が閉形式と全件一致。分断の %d 件は配線を変えず、画素 1 ビットあたりの"
          "配線の損傷は分断 %.2f / 融合 %.2f、画素と配線の順位相関は %.2f、上位 %d 件を直したとき画素の順は理想より %.0f ポイント少ない。"
          % ("" if real else "(合成)", len(ws), len(wm), zs, rs, rm, rho, k20, 100 * gap))


if __name__ == "__main__":
    main()

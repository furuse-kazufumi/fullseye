# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""電子顕微鏡の神経の切り出しを採点する —— 分けすぎと、まとめすぎを別々の数字にする。

    py -3.11 examples/poc_em_split_merge_score.py

コネクトームは電子顕微鏡(EM)の断面から神経を 1 本ずつ切り出して作る。自動の切り出しは
**分断**(1 本の神経を 2 つに切る)と**融合**(別々の 2 本を 1 つにする)を残し、CREMI などの
競技会は切り出しを VOI(variation of information)と adapted Rand error で採点する。
:mod:`segcompare` の 3 op(``seg_contingency`` / ``seg_variation_of_information`` / ``seg_rand``)で、
VOI を「分けすぎ(split)」と「まとめすぎ(merge)」に分けて測る。

この PoC が測る唯一の主張:

    **正解に分断を 1 つ仕込むと split だけが、融合を 1 つ仕込むと merge だけが、閉形式どおりの
    量だけ上がる。古典的な切り出し(膜応答 → しきい値 → 連結成分 → 膜の画素を最寄りの細胞へ)は、
    しきい値 1 本で「分けすぎ」から「まとめすぎ」へ入れ替わり、その交点の近くで VOI が最小になる。**

★採点の前処理ひとつで結論が逆になる: 膜の画素を背景(ラベル 0)のまま残すと、背景全体が 1 つの巨大な
「領域」として数えられ、merge が 2 倍以上に水増しされて、どのしきい値でも「まとめすぎ」に見える
(CREMI、しきい値 70 % で merge 2.07 → 割り振ると 0.85)。

検査する恒等式(下の assert、当てはめた数字は無い):

1. 正解のラベル m 画素を m1 と m2 に割ると、split はちょうど (m/N)·H2(m1/m) ビット増え、merge は 0
   (H2 = 2 値のエントロピー)。融合は split と merge の役を入れ替えた同じ式。**実データのどの割り方でも厳密**。
2. 付け替え不変: ラベル番号を並べ替えても VOI も Rand も変わらない。
3. 正解どうしで VOI = 0・adjusted Rand = 1・adapted Rand error = 0。

分断と融合を仕込むのは既存の :func:`emproof.seg_inject_split` / :func:`emproof.seg_inject_merge`。
データは CREMI sample A(``FULLSEYE_CREMI`` か ``<FULLSEYE_DATA_DIR か ~/.cache/fullseye>/cremi/
sample_A_20160501.hdf``、h5py が要る)。生データは commit しない。無ければ合成の細胞画像で回る。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
import emproof as EP  # noqa: E402
import examplefig as figs  # noqa: E402
import segcompare as SC  # noqa: E402

CREMI = os.environ.get("FULLSEYE_CREMI") or os.path.join(
    os.environ.get("FULLSEYE_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "fullseye"),
    "cremi", "sample_A_20160501.hdf")


def h2(p: float) -> float:
    return 0.0 if p <= 0 or p >= 1 else float(-(p * np.log2(p) + (1 - p) * np.log2(1 - p)))


def load_slice(path: str, z: int = 40, y0: int = 300, x0: int = 300, size: int = 512):
    if not os.path.isfile(path):
        return None
    try:
        import h5py
    except ImportError:
        return None
    with h5py.File(path, "r") as f:
        raw = f["volumes/raw"][z, y0:y0 + size, x0:x0 + size].astype(np.float64) / 255.0
        lab = f["volumes/labels/neuron_ids"][z, y0:y0 + size, x0:x0 + size].astype(np.int64)
    _u, inv = np.unique(lab, return_inverse=True)
    return raw, (inv.reshape(lab.shape) + 1).astype(np.int64), "CREMI sample A z=%d (%d^2 @ %d,%d)" % (z, size, y0, x0)


def synthetic(size=256, seed=0):
    """ボロノイの細胞(正解)と、その境界を暗い線にした画像。"""
    rng = np.random.default_rng(seed)
    pts = rng.uniform(0, size, (40, 2))
    yy, xx = np.mgrid[0:size, 0:size]
    d = (yy[..., None] - pts[:, 0]) ** 2 + (xx[..., None] - pts[:, 1]) ** 2
    lab = np.argmin(d, axis=2) + 1
    edge = np.zeros_like(lab, bool)
    edge[:-1] |= lab[:-1] != lab[1:]
    edge[:, :-1] |= lab[:, :-1] != lab[:, 1:]
    raw = 0.7 - 0.5 * edge + 0.05 * rng.standard_normal(lab.shape)
    return raw, lab.astype(np.int64), "合成(ボロノイ 40 細胞)"


def sizes_of(labels, ids):
    return [int((labels == i).sum()) for i in ids]


def main() -> None:
    data = load_slice(CREMI)
    real = data is not None
    raw, truth, src = data if real else synthetic()
    if not real:
        print("CREMI が無いので合成の細胞で回す(FULLSEYE_CREMI に sample_A_20160501.hdf を置くと実データ)")
    N = truth.size

    # ---- 恒等式 3 と 2 ------------------------------------------------------------------
    v0, r0 = SC.seg_variation_of_information(truth, truth), SC.seg_rand(truth, truth)
    assert v0["voi"] == 0.0 and r0["adjusted_rand_index"] == 1.0 and r0["adapted_rand_error"] == 0.0
    perm = np.random.default_rng(1).permutation(int(truth.max()) + 1) + 7
    assert SC.seg_variation_of_information(truth, perm[truth])["voi"] == 0.0

    # ---- 恒等式 1: 分断を仕込む -> split だけが閉形式どおり ------------------------------------
    rows = []
    for k in range(4):
        cut = EP.seg_inject_split(truth, n=1, seed=k, min_area=4000 if real else 800, ignore_zero=False)
        ch = EP.seg_label_changes(truth, cut, ignore_zero=False)
        b = int(ch["split_before"][0])
        parts = sorted(set(int(x) for x in ch["split_after"]))
        m1, m2 = sizes_of(cut, parts)
        m = m1 + m2
        want = m / N * h2(m1 / m)
        v = SC.seg_variation_of_information(truth, cut)
        assert abs(v["split"] - want) < 1e-12 and v["merge"] < 1e-12, (v, want)
        rows.append(("分断 %d(ラベル %d を %d + %d に)" % (k + 1, b, m1, m2), v["split"], v["merge"], want))
    # ---- 融合を仕込む -> merge だけが閉形式どおり ------------------------------------------
    for k in range(4):
        glued = EP.seg_inject_merge(truth, n=1, seed=k, min_area=3000 if real else 600, ignore_zero=False)
        ch = EP.seg_label_changes(truth, glued, ignore_zero=False)
        ids = sorted(set(int(x) for x in ch["merge_before"]))
        m1, m2 = sizes_of(truth, ids)
        m = m1 + m2
        want = m / N * h2(m1 / m)
        v = SC.seg_variation_of_information(truth, glued)
        assert abs(v["merge"] - want) < 1e-12 and v["split"] < 1e-12, (v, want)
        rows.append(("融合 %d(ラベル %d と %d を 1 つに)" % (k + 1, ids[0], ids[1]), v["split"], v["merge"], want))
    print("%s: 仕込んだ分断 4 件は split だけ、融合 4 件は merge だけが (m/N)·H2(m1/m) ビットどおり上がった(誤差 < 1e-12)" % src)
    for name, s, mg, want in rows:
        print("   %-34s split %.6f  merge %.6f  (閉形式 %.6f)" % (name, s, mg, want))

    # ---- 古典の切り出しを採点 -----------------------------------------------------------
    import fullseye as fs
    from scipy import ndimage as ndi
    memb = np.asarray(EP.seg_membrane_response(raw))

    def classic(q, fill=True):
        """膜応答の q パーセンタイル未満を細胞とみて連結成分。fill=True で膜の画素を最寄りの細胞へ。"""
        cand = np.asarray(fs.ledger.blob_label(memb < np.percentile(memb, q))).astype(np.int64)
        if fill and cand.max() > 0:
            idx = ndi.distance_transform_edt(cand == 0, return_distances=False, return_indices=True)
            cand = cand[tuple(idx)]
        return cand

    results = []
    for q in (60, 65, 70, 75, 80, 85):
        cand = classic(q)
        if cand.max() == 0:
            continue
        v = SC.seg_variation_of_information(truth, cand)
        r = SC.seg_rand(truth, cand)
        results.append((q, v["split"], v["merge"], r["adapted_rand_error"], r["adjusted_rand_index"], int(cand.max())))
    print("古典の切り出し(膜応答の %s パーセンタイル未満を細胞とみて連結成分、膜の画素は最寄りの細胞へ):"
          % "/".join(str(x[0]) for x in results))
    for q, s, mg, are, ari, nl in results:
        side = "分けすぎ" if s > mg else "まとめすぎ"
        print("   しきい値 %2d%%: split %.3f  merge %.3f  adapted Rand error %.3f  ARI %.3f  ラベル %4d 個 → %s"
              % (q, s, mg, are, ari, nl, side))
    # しきい値を上げる(細胞とみなす面積が増える)ほど merge が増え split が減り、どこかで入れ替わる —— 交差の門
    ss = [x[1] for x in results]
    mm = [x[2] for x in results]
    assert mm[-1] > mm[0] and ss[-1] < ss[0], (ss, mm)
    assert ss[0] > mm[0] and mm[-1] > ss[-1], ("no crossover", ss, mm)
    best = int(np.argmin([x[1] + x[2] for x in results]))
    cross = next(i for i in range(len(results)) if mm[i] > ss[i])
    print("   → しきい値 %d%% と %d%% の間で分けすぎからまとめすぎへ入れ替わり、VOI は %d%% で最小(%.3f)"
          % (results[cross - 1][0], results[cross][0], results[best][0], ss[best] + mm[best]))
    q_bg = results[min(cross, len(results) - 1)][0]
    bg = SC.seg_variation_of_information(truth, classic(q_bg, fill=False))
    fl = SC.seg_variation_of_information(truth, classic(q_bg, fill=True))
    print("   ★背景の扱い(しきい値 %d%%): 膜の画素をラベル 0 のまま → merge %.3f / 最寄りの細胞へ → merge %.3f(%.1f 倍の水増し)"
          % (q_bg, bg["merge"], fl["merge"], bg["merge"] / max(fl["merge"], 1e-12)))
    assert bg["merge"] > fl["merge"], (bg, fl)

    if figs.enabled():
        qs = np.array([x[0] for x in results], float)
        figs.save_plot("split_vs_merge_by_threshold",
                       [("split(分けすぎ)", qs, np.array(ss)), ("merge(まとめすぎ)", qs, np.array(mm))],
                       xlabel="細胞とみなす膜応答のパーセンタイル", ylabel="ビット",
                       title="しきい値 1 本で、分けすぎとまとめすぎが入れ替わる",
                       caption="%s。膜応答の低い画素を細胞とみて連結成分を取り、膜の画素を最寄りの細胞へ割り振った切り出しを、"
                               "正解と VOI で比べた。しきい値を上げると split が %.2f → %.2f に下がり、merge が %.2f → %.2f に上がる。"
                               "VOI 最小は %d%%。" % (src, ss[0], ss[-1], mm[0], mm[-1], results[best][0]))
        cand = classic(results[best][0])
        figs.save_grid("truth_vs_classic", [raw, truth.astype(float) % 17, cand.astype(float) % 17],
                       ["EM 断面", "正解のラベル", "古典の切り出し(しきい値 %d%%)" % results[best][0]],
                       title="%s —— VOI 最小のしきい値で split %.2f / merge %.2f"
                             % (src, results[best][1], results[best][2]), ncols=3)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS%s: 分断 4 件・融合 4 件の閉形式が 1e-12 で一致、付け替え不変・正解どうし 0 を確認、古典の切り出しは"
          "しきい値で split %.2f → %.2f / merge %.2f → %.2f と入れ替わり、VOI 最小は %d%%。"
          % ("" if real else "(合成)", ss[0], ss[-1], mm[0], mm[-1], results[best][0]))


if __name__ == "__main__":
    main()

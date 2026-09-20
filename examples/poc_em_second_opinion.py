# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: EM 連結体校正の「古典 CV セカンドオピニオン」―― 膜はラベルの境界にしか無いはず

電子顕微鏡(EM)の連続断面からニューロンを切り出した自動分割には、**融合**(2 細胞が 1 つの id)と
**分断**(1 細胞が途中で 2 つの id)が残り、人がそれを探して直す(校正)。先行研究(MergeNet 2017、
Zung 2017、Dmitriev 2018、ConnectomeBench 2025)はすべて深層学習で候補を出す。この PoC は学習なしで
同じ 2 種類を数える —— 「細胞膜(暗い稜線)は本来ラベルの境界にしか無い」という 1 つの前提を 2 通りに:

* 融合の疑い = ラベルの**内部**を横切る膜の弦(``seg_membrane_chord_score``)。閉じた輪(ミトコンドリア)は除く。
* 分断の疑い = 膜の無い境界(``seg_boundary_membrane_gap``)。

**主張は 1 つだけ**: 正解ラベルに人工の融合・分断を仕込み、閾値を訓練断面で選んで**別の断面**で測ると
(``holdout_threshold``)、膜の無い境界は分断を、内部の弦は融合を、乱数や大きさの基準より確実に指す。
数字は評価断面の AUC / TPR / FPR。

図:
1. ``second_opinion_slice``: 評価断面 1 枚 —— 生 EM | 膜応答 | 重ね描き(白 = ラベル境界、マゼンタ = 融合の
   疑いの膜、シアン = 分断の疑いの境界、黄 = 仕込んだ誤りの答え)。
2. ``suspects_on_the_cube``: 断面を z に積んだ立方体の上で、疑わしい箇所(マゼンタ / シアン、明るさ = スコア)を
   全境界(灰)の上に載せて回す GIF。
3. ``holdout_roc``: 評価断面の ROC(融合・分断の検出器と乱数)。
4. ``holdout_numbers``: 閾値・訓練/評価の AUC・TPR・FPR を検出器と基準(乱数・大きさ)で並べた表。

データ: 手元の CREMI sample A(adult *Drosophila* FAFB、``C:/dev/data/cremi/sample_A_20160501.hdf`` か
``FULLSEYE_CREMI``、h5py が要る)。**生データは commit しない**(集計と図だけ)。無ければ合成の代替
(z でゆっくり動くボロノイ細胞 + 境界の膜 + 閉じた輪のミトコンドリア + 雑音)で同じ経路を走らせ
``DATA: synthetic surrogate`` と印字する。

走らせ方: ``py -3.11 examples/poc_em_second_opinion.py``(図は ``out/figures/poc_em_second_opinion/``)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402
import emproof as E  # noqa: E402

CREMI = os.environ.get("FULLSEYE_CREMI", r"C:/dev/data/cremi/sample_A_20160501.hdf")
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
MAGENTA, CYAN, YELLOW = (1.0, 0.25, 0.9), (0.2, 0.9, 1.0), (1.0, 0.9, 0.2)


# --------------------------------------------------------------------------- #
# データ                                                                        #
# --------------------------------------------------------------------------- #
def load_cremi(path: str, z0: int = 40, nz: int = 12, y0: int = 300, x0: int = 300, size: int = 512):
    """CREMI sample A の (nz, size, size) 切片。無ければ None。"""
    if not os.path.isfile(path):
        return None
    try:
        import h5py
    except ImportError:
        return None
    with h5py.File(path, "r") as f:
        raw = f["volumes/raw"][z0:z0 + nz, y0:y0 + size, x0:x0 + size].astype(np.float64) / 255.0
        lab = f["volumes/labels/neuron_ids"][z0:z0 + nz, y0:y0 + size, x0:x0 + size].astype(np.int64)
    # id を 1.. に詰める(seg_* は任意の非負 id を受けるが、表と図で読みやすい)
    _u, inv = np.unique(lab, return_inverse=True)
    return raw, (inv.reshape(lab.shape) + 1).astype(np.int64), "CREMI sample A z=%d..%d (%d^2 @ %d,%d)" % (z0, z0 + nz - 1, size, y0, x0)


def synthetic_stack(nz: int = 8, size: int = 256, n_cells: int = 40, seed: int = 0):
    """合成の代替: z でゆっくり動くボロノイ細胞、境界の膜、閉じた輪(ミトコンドリア)、雑音。"""
    rng = np.random.default_rng(seed)
    seeds = rng.random((n_cells, 2)) * size
    drift = rng.normal(size=(n_cells, 2)) * 1.5
    yy, xx = np.mgrid[0:size, 0:size]
    raws, labs = [], []
    for z in range(nz):
        s = seeds + drift * z
        d = (yy[..., None] - s[:, 0]) ** 2 + (xx[..., None] - s[:, 1]) ** 2
        lab = (np.argmin(d, -1) + 1).astype(np.int64)
        edge = np.zeros((size, size), bool)
        edge[:, :-1] |= lab[:, :-1] != lab[:, 1:]
        edge[:-1, :] |= lab[:-1, :] != lab[1:, :]
        mem = ndi.gaussian_filter(edge.astype(float), 1.0)
        mem = mem / max(mem.max(), 1e-9)
        for _ in range(6):                                   # ミトコンドリア: 閉じた輪
            cy, cx = rng.integers(12, size - 12, size=2)
            r = rng.integers(4, 8)
            ring = np.abs(np.hypot(yy - cy, xx - cx) - r) < 1.1
            mem = np.maximum(mem, ndi.gaussian_filter(ring.astype(float), 0.7) / 0.45)
        raw = 1.0 - 0.8 * np.clip(mem, 0.0, 1.0) + 0.06 * rng.standard_normal((size, size))
        raws.append(raw)
        labs.append(lab)
    return np.stack(raws), np.stack(labs), "synthetic surrogate (%d slices, %d^2, %d cells)" % (nz, size, n_cells)


# --------------------------------------------------------------------------- #
# 1 断面の処理                                                                  #
# --------------------------------------------------------------------------- #
def process_slice(raw, lab, z, knobs):
    """人工誤りを仕込み、2 つの疑いを数え、正例 / 負例のスコアと図の材料を返す。"""
    M = E.seg_membrane_response(raw, sigma=knobs["sigma"])
    merged = E.seg_inject_merge(lab, n=1, seed=z, min_area=knobs["merge_area"])
    cut = E.seg_inject_split(merged, n=1, seed=z, min_area=knobs["split_area"], axis=("row", "col")[z % 2])
    ch = E.seg_label_changes(lab, cut)
    merged_ids = set(ch["merge_after"].tolist())
    split_pairs = {(min(int(b), int(a)), max(int(b), int(a))) for b, a in zip(ch["split_before"], ch["split_after"]) if a != b}
    chord = E.seg_membrane_chord_score(cut, M, tau=knobs["tau"], band=knobs["band"], min_area=knobs["chord_min_area"],
                                       min_segment=knobs["min_segment"])
    gap = E.seg_boundary_membrane_gap(cut, M, tau=knobs["tau"], min_len=knobs["min_len"])
    is_merge = np.isin(chord["label"], list(merged_ids))
    pair_keys = list(zip(gap["label_a"].tolist(), gap["label_b"].tolist()))
    is_split = np.array([k in split_pairs for k in pair_keys], bool)
    # ★面積で揃える: 仕込んだ融合は「min_area 以上の 2 ラベルの和」なので必ず大きい。負例をそのまま
    #   使うと「大きいラベル = 怪しい」だけで AUC が出てしまう(最初の実測: 弦 0.86 に対し面積だけで 0.87)。
    #   負例は正例と同じ下限(2 × merge_area)以上の成分に限り、基準の「面積だけ」も同じ集合で測る。
    matched = (chord["area"] >= 2 * knobs["merge_area"]) | is_merge
    return {"M": M, "cut": cut, "chord": chord, "gap": gap, "is_merge": is_merge, "is_split": is_split,
            "merged_ids": merged_ids, "split_pairs": split_pairs, "lab": lab, "matched": matched,
            "merge_area": chord["area"].astype(float), "split_len": gap["length"].astype(float)}


def auc(pos, neg):
    from scipy.stats import rankdata
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    r = rankdata(np.concatenate([pos, neg]), method="average")
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg)))


def roc(pos, neg):
    s = np.unique(np.concatenate([pos, neg]))[::-1]
    tpr = np.array([np.mean(pos >= t) for t in s])
    fpr = np.array([np.mean(neg >= t) for t in s])
    return np.concatenate([[0.0], fpr, [1.0]]), np.concatenate([[0.0], tpr, [1.0]])


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def boundary_mask(lab):
    e = np.zeros(lab.shape, bool)
    e[:, :-1] |= lab[:, :-1] != lab[:, 1:]
    e[:-1, :] |= lab[:-1, :] != lab[1:, :]
    return e


def overlay(raw, res, knobs, top=3):
    """生 EM に、境界(白)・融合の疑いの膜(マゼンタ)・分断の疑いの境界(シアン)・答え(黄)を重ねる。"""
    g = np.clip((raw - raw.min()) / max(float(np.ptp(raw)), 1e-9), 0, 1)
    rgb = np.stack([g, g, g], -1) * 0.85
    cut, M = res["cut"], res["M"]
    rgb[boundary_mask(cut)] = 0.75
    for lid in res["chord"]["label"][:top]:
        m = cut == lid
        dist = ndi.distance_transform_edt(m)
        mem = (dist > knobs["band"]) & (M > knobs["tau"])
        rgb[ndi.binary_dilation(mem, iterations=1)] = MAGENTA
    for a, b in zip(res["gap"]["label_a"][:top], res["gap"]["label_b"][:top]):
        pa, pb = cut == a, cut == b
        edge = (ndi.binary_dilation(pa, iterations=2) & pb) | (ndi.binary_dilation(pb, iterations=2) & pa)
        rgb[edge] = CYAN
    truth = boundary_mask(res["lab"]) & ~boundary_mask(cut)                             # 仕込んだ融合の消えた境界
    for a, b in res["split_pairs"]:
        pa, pb = cut == a, cut == b
        truth |= (ndi.binary_dilation(pa, iterations=1) & pb)
    rgb[ndi.binary_dilation(truth, iterations=1)] = YELLOW
    return rgb


def cube_gif(results, size_px, knobs):
    """疑わしい箇所を立方体の上で回す(``points_activity_video``)。"""
    nz = len(results)
    zscale = size_px / max(nz, 1)
    bg, P, X, C = [], [], [], []
    for z, res in enumerate(results):
        cut, M = res["cut"], res["M"]
        ys, xs = np.nonzero(boundary_mask(cut))
        k = max(1, len(ys) // 1500)
        bg.append(np.column_stack([xs[::k], ys[::k], np.full(len(ys[::k]), z * zscale)]))
        for lid, sc in zip(res["chord"]["label"][:2], res["chord"]["score"][:2]):
            m = cut == lid
            mem = (ndi.distance_transform_edt(m) > knobs["band"]) & (M > knobs["tau"])
            yy, xx = np.nonzero(mem)
            if len(yy):
                P.append(np.column_stack([xx, yy, np.full(len(yy), z * zscale)]))
                X.append(np.full(len(yy), sc))
                C.append(np.tile(MAGENTA, (len(yy), 1)))
        for a, b, frac in zip(res["gap"]["label_a"][:2], res["gap"]["label_b"][:2], res["gap"]["gap_fraction"][:2]):
            pa, pb = cut == a, cut == b
            edge = ndi.binary_dilation(pa, iterations=1) & pb
            yy, xx = np.nonzero(edge)
            if len(yy):
                P.append(np.column_stack([xx, yy, np.full(len(yy), z * zscale)]))
                X.append(np.full(len(yy), frac))
                C.append(np.tile(CYAN, (len(yy), 1)))
    P = np.concatenate(P).astype(float)
    X = np.concatenate(X)[None, :]
    C = np.concatenate(C)
    frames = fs.ledger.points_activity_video(P, X, colors=C, size=360, aspect=1.0, pitch=25.0, substeps=36,
                                             point_px=2, gain=3.0, background=np.concatenate(bg).astype(float))
    return frames


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.time()
    data = None if REDUCED else load_cremi(CREMI)
    if data is None:
        raw, lab, name = synthetic_stack(nz=6 if REDUCED else 8)
        knobs = dict(sigma=1.2, tau=0.3, band=3, chord_min_area=400, min_segment=8, min_len=20,
                     merge_area=800, split_area=1200)
        real = False
    else:
        raw, lab, name = data
        knobs = dict(sigma=2.0, tau=0.2, band=4, chord_min_area=1500, min_segment=20, min_len=60,
                     merge_area=3000, split_area=4000)
        real = True
    print("DATA:", name)
    print("KNOBS:", knobs)
    nz = raw.shape[0]
    results = [process_slice(raw[z], lab[z], z, knobs) for z in range(nz)]
    half = nz // 2
    train, test = results[:half], results[half:]

    def sel(r, key, positive):
        """正例 / 負例の行(融合は面積で揃えた集合の中だけ)。"""
        flag = r["is_merge"] if key == "chord" else r["is_split"]
        m = (flag if positive else ~flag) & (r["matched"] if key == "chord" else True)
        return m

    def scores(part, key, flag):
        col = "score" if key == "chord" else "gap_fraction"
        pos = np.concatenate([r[key][col][sel(r, key, True)] for r in part])
        neg = np.concatenate([r[key][col][sel(r, key, False)] for r in part])
        return pos, neg

    rng = np.random.default_rng(0)
    rows, curves = [], []
    summary = {}
    for label, key, flag, base_key in (("merge: membrane chord", "chord", "is_merge", "merge_area"),
                                       ("split: boundary gap", "gap", "is_split", "split_len")):
        trp, trn = scores(train, key, flag)
        tep, ten = scores(test, key, flag)
        h = E.holdout_threshold(trp, trn, tep, ten, target_fpr=0.05)
        summary[key] = h
        rows.append([label, "%.3f" % h["tau"], "%.2f" % h["train_auc"], "%.2f" % h["test_auc"], "%.2f" % h["test_tpr"], "%.2f" % h["test_fpr"],
                     "%d / %d" % (h["n_test_pos"], h["n_test_neg"])])
        curves.append((label, *roc(tep, ten)))
        # 基準 1: 乱数(同じ件数)
        hr = E.holdout_threshold(rng.random(len(trp)), rng.random(len(trn)), rng.random(len(tep)), rng.random(len(ten)), 0.05)
        rows.append([label.split(":")[0] + ": random scores", "%.3f" % hr["tau"], "%.2f" % hr["train_auc"], "%.2f" % hr["test_auc"], "%.2f" % hr["test_tpr"], "%.2f" % hr["test_fpr"], ""])
        summary[key + "_random"] = hr
        # 基準 2: 大きさだけ(融合 = 面積が大きいほど怪しい / 分断 = 境界が短いほど怪しい)
        sgn = 1.0 if key == "chord" else -1.0
        bp = np.concatenate([sgn * r[base_key][sel(r, key, True)] for r in train]); bn = np.concatenate([sgn * r[base_key][sel(r, key, False)] for r in train])
        tp = np.concatenate([sgn * r[base_key][sel(r, key, True)] for r in test]); tn = np.concatenate([sgn * r[base_key][sel(r, key, False)] for r in test])
        hb = E.holdout_threshold(bp, bn, tp, tn, 0.05)
        rows.append([label.split(":")[0] + ": size only (%s)" % ("area" if key == "chord" else "short boundary"), "%.3f" % hb["tau"], "%.2f" % hb["train_auc"], "%.2f" % hb["test_auc"], "%.2f" % hb["test_tpr"], "%.2f" % hb["test_fpr"], ""])
        summary[key + "_size"] = hb
        if key == "gap":
            curves.append(("random", *roc(rng.random(len(tep)), rng.random(len(ten)))))
    for key, name_ in (("chord", "merge (membrane chord)"), ("gap", "split (boundary gap)")):
        h = summary[key]
        print("%-24s tau %.3f  train AUC %.2f  test AUC %.2f  test TPR %.2f  test FPR %.2f  (pos %d / neg %d)" % (
            name_, h["tau"], h["train_auc"], h["test_auc"], h["test_tpr"], h["test_fpr"], h["n_test_pos"], h["n_test_neg"]))
        print("%-24s random AUC %.2f   size-only AUC %.2f" % ("", summary[key + "_random"]["test_auc"], summary[key + "_size"]["test_auc"]))

    # 真値: 分断は膜の無い境界でほぼ確実、融合は弦で乱数・大きさより上(数字は評価断面)
    assert summary["gap"]["test_auc"] >= (0.9 if real else 0.95), summary["gap"]
    assert summary["chord"]["test_auc"] >= (0.65 if real else 0.8), summary["chord"]
    assert summary["chord"]["test_auc"] > summary["chord_random"]["test_auc"] + 0.1
    assert summary["gap"]["test_auc"] > summary["gap_size"]["test_auc"]
    assert 0.25 <= summary["gap_random"]["test_auc"] <= 0.75
    assert summary["gap"]["train_fpr"] <= 0.05 + 1e-9                          # 閾値は訓練側の FPR で選ぶ
    print("HOLDOUT: thresholds chosen on slices 0..%d, numbers reported on slices %d..%d" % (half - 1, half, nz - 1))

    # 図
    if figs.enabled():
        r0 = test[0]
        figs.save_grid("second_opinion_slice",
                       [raw[half], r0["M"], overlay(raw[half], r0, knobs)],
                       captions=["raw EM (%s)" % ("CREMI" if real else "synthetic"), "membrane response (seg_membrane_response)",
                                 "white = label boundary, magenta = merge suspect (chord), cyan = split suspect (gap), yellow = injected truth"],
                       gray=[True, False, False], ncols=3,
                       caption="one evaluation slice: the injected merge is the membrane crossing a label (magenta), the injected split is the boundary without membrane (cyan)")
        frames = cube_gif(results, raw.shape[1], knobs)
        figs.save_gif("suspects_on_the_cube", frames, fps=12.0,
                      caption="suspects on the stacked cube: magenta = merge suspects (membrane chords), cyan = split suspects (membrane-free boundaries), brightness = score, grey = all label boundaries")
        figs.save_plot("holdout_roc", [(lab_, fpr, tpr) for lab_, fpr, tpr in curves], xlabel="false positive rate", ylabel="true positive rate",
                       title="evaluation slices: merge AUC %.2f, split AUC %.2f" % (summary["chord"]["test_auc"], summary["gap"]["test_auc"]),
                       caption="ROC on the held-out slices; thresholds were chosen on the other half", xlim=(0, 1), ylim=(0, 1))
        figs.save_table("holdout_numbers", ["detector", "tau (train)", "train AUC", "test AUC", "test TPR", "test FPR", "test pos / neg"], rows,
                        title="second opinion vs baselines (held-out slices)",
                        caption="tau = smallest threshold with train FPR <= 5 %; every number in the test columns comes from slices the threshold never saw")
        assert not figs.errors(), figs.errors()
    print("elapsed %.0fs" % (time.time() - t0))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

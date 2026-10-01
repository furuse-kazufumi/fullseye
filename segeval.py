# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""分割の採点の物差し: ラベル対応の分割表(最大重なり)、Dice・Jaccard、境界 F 値(許容距離)、Hausdorff・平均表面距離、
過分割・未分割の数、物体の個数の一致(分裂・融合・欠落・偽)、そして全部を 1 枚に並べる採点表。

## 何を作るか

セグメンテーション拡充 第 1 陣「評価の物差し」。学習器は載せない。どの物差しも **定理か第 2 実装の門** が立つものだけ:

1. 分割表(``seg_confusion_table``)—— 行 = 真、列 = 予測の画素数の表(密)。対応は Hungarian でなく **最大重なり**
   (行ごとの argmax・列ごとの argmax)で、相互に選び合えば ``mutual``、全体が 1 対 1 なら ``unique_matching``。
2. Dice・Jaccard(``seg_dice_jaccard``)—— マスク(背景以外の和)か、ラベル別(最大重なりの相手と)。恒等式 D = 2J/(1+J)。
3. 境界 F 値(``seg_boundary_f``)—— 許容距離 τ の中に相手の境界があれば一致(Martin 2004 の「許容距離つき境界の適合率・
   再現率」の流儀。Martin は 2 部マッチングで 1 対 1 に対応させるが、ここでは距離変換で「τ 以内に相手がいるか」だけを数える
   = Csurka 2013 / DAVIS(Perazzi 2016)の BF 値)。距離変換 = 総当たりが門、τ = 0 で画素一致。
4. Hausdorff・平均表面距離(``seg_hausdorff`` / ``seg_mean_surface_distance``)—— 境界画素の集合の間の距離。
   既存 ``metrics3d.hausdorff_distance``(点群、cKDTree)が第 2 実装。
5. 過分割・未分割(``seg_under_over_segmentation``)—— 分割表の列の多数決(各予測がどの真に属すか)の多重度 = 過分割の数、
   行の多数決の多重度 = 未分割の数(Levine & Nazif 1985 の「領域の数で数える」流儀)。
6. 個数の一致(``seg_object_counts_match``)—— 「主に重なる」辺(重なり ≥ min_overlap × 小さい方の面積)の 2 部グラフの次数で
   分裂(真の次数 ≥ 2)・融合(予測の次数 ≥ 2)・欠落(真の次数 0)・偽(予測の次数 0)・一致(両方 1)を数える。
7. 採点表(``seg_score_card``)—— 上の全部 + 既存 ``segcompare`` の VI(Meilă 2007)・Rand・ARI を 1 つの dict に。

## 既存の op を再利用する(再実装しない)

* 分割表の疎な形 = ``segcompare.seg_contingency``(ここはそれを密にして対応を足す)。
* VI = ``segcompare.seg_variation_of_information``、Rand・ARI・adapted Rand = ``segcompare.seg_rand``(a = 真、b = 予測)。
* マスクの Dice・IoU の第 2 実装 = ``metrics3d.voxel_dice`` / ``voxel_iou``(テストで照合)。
* 点群の Hausdorff = ``metrics3d.hausdorff_distance``(テストで照合)。

## 境界の規約

境界画素 = 右か下の隣とラベルが違う画素(画素の間の「割れ目」を左上の画素で代表する、1 画素幅)。真も予測も同じ規約なので、
同じ分割なら境界が完全に一致して距離 0。画像の縁は境界にしない(縁で切れた物体を罰しない)。

## 単位

画素。距離はユークリッド(画素の中心の間)。ラベルは非負の整数、``background``(既定 0)は物体でない。
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import numpy as np
from scipy import ndimage as ndi

import segcompare

__all__ = [
    "MAX_TABLE_CELLS",
    "seg_confusion_table", "seg_dice_jaccard", "seg_boundary_f", "seg_hausdorff", "seg_mean_surface_distance",
    "seg_under_over_segmentation", "seg_object_counts_match", "seg_score_card",
]

#: 密な分割表の上限(真のラベル数 × 予測のラベル数)。超えたら ValueError(過分割の嵐を黙って抱えない)。
MAX_TABLE_CELLS = 4_000_000


# ───────────────────────────── 入力の検査 ─────────────────────────────
def _labels(x, name: str, op: str) -> np.ndarray:
    """2-D の整数ラベル画像に揃える(bool → 0/1、整数値の float → int)。負・非整数・2-D 以外は ValueError。"""
    if isinstance(x, (str, bytes)) or np.ma.is_masked(x):
        raise ValueError("%s: %s must be a 2-D integer label image" % (op, name))
    a = np.asarray(x)
    if a.dtype.kind == "b":
        a = a.astype(np.int64)
    elif a.dtype.kind == "f":
        if not np.isfinite(a).all() or not np.array_equal(a, np.round(a)):
            raise ValueError("%s: %s has non-integer values — labels must be integers" % (op, name))
        a = a.astype(np.int64)
    elif a.dtype.kind not in "iu":
        raise ValueError("%s: %s has dtype %s — labels must be integers" % (op, name, a.dtype))
    if a.ndim != 2 or a.size == 0:
        raise ValueError("%s: %s must be a non-empty 2-D label image, got shape %r" % (op, name, a.shape))
    a = a.astype(np.int64, copy=False)
    if int(a.min()) < 0:
        raise ValueError("%s: %s has negative labels (min %d)" % (op, name, int(a.min())))
    return a


def _pair(pred, true, op: str) -> Tuple[np.ndarray, np.ndarray]:
    p = _labels(pred, "labels_pred", op)
    t = _labels(true, "labels_true", op)
    if p.shape != t.shape:
        raise ValueError("%s: labels_pred %r and labels_true %r differ in shape" % (op, p.shape, t.shape))
    return p, t


def _background(v, op: str) -> int:
    try:
        b = int(v)
    except (TypeError, ValueError):
        raise ValueError("%s: background must be an integer (got %r)" % (op, v)) from None
    if b < 0:
        raise ValueError("%s: background must be >= 0 (got %d)" % (op, b))
    return b


def _dense_table(p: np.ndarray, t: np.ndarray, op: str):
    """密な分割表 T[i, j] = #{真 = labels_true[i] かつ 予測 = labels_pred[j]}(``segcompare.seg_contingency`` を密に)。"""
    c = segcompare.seg_contingency(t, p)
    ua, ub = c["labels_a"], c["labels_b"]
    if len(ua) * len(ub) > MAX_TABLE_CELLS:
        raise ValueError("%s: %d true x %d predicted labels exceed MAX_TABLE_CELLS=%d" % (op, len(ua), len(ub), MAX_TABLE_CELLS))
    T = np.zeros((len(ua), len(ub)), np.int64)
    T[c["rows"], c["cols"]] = c["counts"]
    return T, ua.astype(np.int64), ub.astype(np.int64)


def _fg_index(labels: np.ndarray, bg: int) -> np.ndarray:
    return np.flatnonzero(labels != bg)


# ───────────────────────────── 1. 分割表と対応 ─────────────────────────────
def seg_confusion_table(labels_pred, labels_true, *, background: int = 0) -> Dict[str, object]:
    """ラベル対応の分割表(行 = 真、列 = 予測)と、最大重なりによる対応・対応の一意性の印。

    ``table[i, j]`` = 真のラベル ``labels_true[i]`` と予測のラベル ``labels_pred[j]`` を同時に持つ画素数。
    対応は **最大重なり**: 真 i の相手 = 背景でない列のうち ``table[i, :]`` が最大の列(``pred_of_true``、ラベル値、無ければ −1)、
    予測 j の相手 = 背景でない行のうち最大の行(``true_of_pred``)。``mutual_true[i]`` = 真 i の相手が真 i を選び返す、
    ``mutual_pred[j]`` も同様。``claims[j]`` = 予測 j を相手に選んだ真の数。``unique_matching`` = 背景でない行・列がすべて相互に
    選び合う(= 1 対 1 の全単射)。背景の行・列は表には残り、対応からは外す。
    Hungarian(総和最大の割当)でなく argmax なので、1 つの大きな予測を複数の真が選ぶことがある —— それが ``claims`` ≥ 2 の印。

    返り値: ``table``、``labels_true`` / ``labels_pred``(行・列のラベル値)、``row_sums`` / ``col_sums``、``pred_of_true`` /
    ``true_of_pred``、``mutual_true`` / ``mutual_pred``、``claims``、``unique_matching``、``n_true`` / ``n_pred``(背景を除く個数)、``n``。"""
    op = "seg_confusion_table"
    p, t = _pair(labels_pred, labels_true, op)
    bg = _background(background, op)
    T, ua, ub = _dense_table(p, t, op)
    fr, fc = _fg_index(ua, bg), _fg_index(ub, bg)
    pred_of_true = np.full(len(ua), -1, np.int64)
    true_of_pred = np.full(len(ub), -1, np.int64)
    best_c = np.full(len(ua), -1, np.int64)                 # 行 → 列の添字
    best_r = np.full(len(ub), -1, np.int64)
    if fr.size and fc.size:
        sub = T[np.ix_(fr, fc)]
        jj = np.argmax(sub, axis=1)
        ok = sub[np.arange(len(fr)), jj] > 0
        best_c[fr[ok]] = fc[jj[ok]]
        ii = np.argmax(sub, axis=0)
        ok2 = sub[ii, np.arange(len(fc))] > 0
        best_r[fc[ok2]] = fr[ii[ok2]]
    has_c = best_c >= 0
    pred_of_true[has_c] = ub[best_c[has_c]]
    has_r = best_r >= 0
    true_of_pred[has_r] = ua[best_r[has_r]]
    mutual_true = np.zeros(len(ua), bool)
    mutual_true[has_c] = best_r[best_c[has_c]] == np.flatnonzero(has_c)
    mutual_pred = np.zeros(len(ub), bool)
    mutual_pred[has_r] = best_c[best_r[has_r]] == np.flatnonzero(has_r)
    claims = np.bincount(best_c[has_c], minlength=len(ub)).astype(np.int64)
    unique = bool(np.all(mutual_true[fr])) and bool(np.all(mutual_pred[fc])) if (fr.size or fc.size) else True
    if fr.size != fc.size:
        unique = False
    return {"table": T, "labels_true": ua, "labels_pred": ub,
            "row_sums": T.sum(axis=1), "col_sums": T.sum(axis=0),
            "pred_of_true": pred_of_true, "true_of_pred": true_of_pred,
            "mutual_true": mutual_true, "mutual_pred": mutual_pred, "claims": claims,
            "unique_matching": unique, "n_true": int(fr.size), "n_pred": int(fc.size), "n": int(T.sum())}


# ───────────────────────────── 2. Dice・Jaccard ─────────────────────────────
def seg_dice_jaccard(labels_pred, labels_true, *, background: int = 0, per_label: bool = False) -> Dict[str, object]:
    """Dice と Jaccard —— マスク(背景でない画素の和)で 1 組、``per_label`` なら真のラベルごとに最大重なりの相手と。

    マスク: ``intersection`` = 両方とも背景でない画素数、``size_pred`` / ``size_true``、``union``。
    Jaccard J = ∩/∪、Dice D = 2∩/(|P|+|T|)。両方空なら 1(何も無いと正しく言った)。恒等式 D = 2J/(1+J)(門)。
    ``per_label=True`` で ``labels``(背景でない真のラベル)、``per_dice`` / ``per_jaccard``(相手が無ければ 0)、
    ``mean_dice`` / ``mean_jaccard`` を足す。"""
    op = "seg_dice_jaccard"
    p, t = _pair(labels_pred, labels_true, op)
    bg = _background(background, op)
    P, Tm = p != bg, t != bg
    inter = int(np.count_nonzero(P & Tm))
    sp, st = int(np.count_nonzero(P)), int(np.count_nonzero(Tm))
    union = sp + st - inter
    jac = inter / union if union > 0 else 1.0
    dice = 2.0 * inter / (sp + st) if sp + st > 0 else 1.0
    out = {"dice": float(dice), "jaccard": float(jac), "intersection": inter, "union": union,
           "size_pred": sp, "size_true": st}
    if per_label:
        c = seg_confusion_table(p, t, background=bg)
        T, ua, ub = c["table"], c["labels_true"], c["labels_pred"]
        fr = _fg_index(ua, bg)
        pd, pj = np.zeros(fr.size), np.zeros(fr.size)
        for k, i in enumerate(fr):
            lab = c["pred_of_true"][i]
            if lab < 0:
                continue
            j = int(np.flatnonzero(ub == lab)[0])
            n_ij, a_i, b_j = float(T[i, j]), float(c["row_sums"][i]), float(c["col_sums"][j])
            pj[k] = n_ij / (a_i + b_j - n_ij)
            pd[k] = 2.0 * n_ij / (a_i + b_j)
        out.update({"labels": ua[fr], "per_dice": pd, "per_jaccard": pj,
                    "mean_dice": float(pd.mean()) if fr.size else 1.0,
                    "mean_jaccard": float(pj.mean()) if fr.size else 1.0})
    return out


# ───────────────────────────── 3〜4. 境界の距離 ─────────────────────────────
def _boundary(lab: np.ndarray) -> np.ndarray:
    """境界画素 = 右か下の隣とラベルが違う画素(割れ目を左上の画素で代表、1 画素幅、画像の縁は含めない)。"""
    b = np.zeros(lab.shape, bool)
    b[:, :-1] |= lab[:, 1:] != lab[:, :-1]
    b[:-1, :] |= lab[1:, :] != lab[:-1, :]
    return b


def _directed(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """src の各境界画素から dst の最も近い境界画素までのユークリッド距離(距離変換)。dst が空なら inf。"""
    if not dst.any():
        return np.full(int(src.sum()), np.inf)
    dt = ndi.distance_transform_edt(~dst)
    return dt[src]


def _surfaces(labels_pred, labels_true, op: str):
    p, t = _pair(labels_pred, labels_true, op)
    bp, bt = _boundary(p), _boundary(t)
    return _directed(bp, bt), _directed(bt, bp), int(bp.sum()), int(bt.sum())


def seg_boundary_f(labels_pred, labels_true, *, tau: float = 2.0) -> Dict[str, object]:
    """境界 F 値(許容距離 τ): 予測の境界画素のうち真の境界から τ 以内にあるものの割合 = ``precision``、逆が ``recall``。

    F = 2PR/(P+R)。境界は :func:`_boundary` の規約(ラベルの割れ目、1 画素幅)なので、ラベルの番号や背景の区別によらない
    (分割の形だけを見る)。距離は距離変換(ユークリッド、画素の中心)。τ = 0 で画素の一致。
    両方の境界が空(どちらも 1 色)なら P = R = F = 1、片方だけ空なら 0。
    返り値: ``f``、``precision``、``recall``、``tau``、``n_pred_boundary`` / ``n_true_boundary``、
    ``dist_pred_to_true`` / ``dist_true_to_pred``(境界画素ごとの距離)。"""
    op = "seg_boundary_f"
    try:
        tau_f = float(tau)
    except (TypeError, ValueError):
        raise ValueError("%s: tau must be a number (got %r)" % (op, tau)) from None
    if not math.isfinite(tau_f) or tau_f < 0:
        raise ValueError("%s: tau must be finite and >= 0 (got %r)" % (op, tau))
    d_pt, d_tp, n_p, n_t = _surfaces(labels_pred, labels_true, op)
    eps = 1e-9
    if n_p == 0 and n_t == 0:
        prec = rec = 1.0
    else:
        prec = float(np.mean(d_pt <= tau_f + eps)) if n_p else 0.0
        rec = float(np.mean(d_tp <= tau_f + eps)) if n_t else 0.0
    f = 2.0 * prec * rec / (prec + rec) if prec + rec > 0 else 0.0
    return {"f": float(f), "precision": prec, "recall": rec, "tau": tau_f,
            "n_pred_boundary": n_p, "n_true_boundary": n_t, "dist_pred_to_true": d_pt, "dist_true_to_pred": d_tp}


def seg_hausdorff(labels_pred, labels_true, *, percentile: float = 95.0) -> Dict[str, float]:
    """境界画素の集合の間の Hausdorff 距離 = max(max 予測→真, max 真→予測)と、その ``percentile`` 版(HD95 など)。

    境界は :func:`_boundary` の規約。どちらかの境界が空(1 色の画像)なら測るものが無いので ValueError。
    返り値: ``hausdorff``、``hausdorff_percentile``、``percentile``、``directed_pred_to_true`` / ``directed_true_to_pred``(各最大)。"""
    op = "seg_hausdorff"
    q = float(percentile)
    if not (0.0 <= q <= 100.0):
        raise ValueError("%s: percentile must be in [0, 100] (got %r)" % (op, percentile))
    d_pt, d_tp, n_p, n_t = _surfaces(labels_pred, labels_true, op)
    if n_p == 0 or n_t == 0:
        raise ValueError("%s: a label image with no boundary (single label) has no surface to measure" % op)
    h_pt, h_tp = float(d_pt.max()), float(d_tp.max())
    return {"hausdorff": max(h_pt, h_tp),
            "hausdorff_percentile": max(float(np.percentile(d_pt, q)), float(np.percentile(d_tp, q))),
            "percentile": q, "directed_pred_to_true": h_pt, "directed_true_to_pred": h_tp}


def seg_mean_surface_distance(labels_pred, labels_true) -> Dict[str, float]:
    """平均表面距離(ASSD): 両方向の境界画素の距離をまとめて平均 = (Σ 予測→真 + Σ 真→予測)/(n_p + n_t)。RMS も。

    境界は :func:`_boundary` の規約。どちらかの境界が空なら ValueError。
    返り値: ``assd``、``rms``、``mean_pred_to_true`` / ``mean_true_to_pred``、``n_pred_boundary`` / ``n_true_boundary``。"""
    op = "seg_mean_surface_distance"
    d_pt, d_tp, n_p, n_t = _surfaces(labels_pred, labels_true, op)
    if n_p == 0 or n_t == 0:
        raise ValueError("%s: a label image with no boundary (single label) has no surface to measure" % op)
    allv = np.concatenate([d_pt, d_tp])
    return {"assd": float(allv.mean()), "rms": float(np.sqrt(np.mean(allv * allv))),
            "mean_pred_to_true": float(d_pt.mean()), "mean_true_to_pred": float(d_tp.mean()),
            "n_pred_boundary": n_p, "n_true_boundary": n_t}


# ───────────────────────────── 5. 過分割・未分割 ─────────────────────────────
def seg_under_over_segmentation(labels_pred, labels_true, *, background: int = 0) -> Dict[str, object]:
    """過分割・未分割の数を、分割表の多数決の多重度で数える(Levine & Nazif 流: 領域の数で)。

    各予測(背景以外)を、最も重なる真(背景も候補)に帰属させる。真 i に帰属した予測の数 k_i が ``pieces_per_true``、
    ``over`` = Σ max(k_i − 1, 0)(1 つの真が何個に割れたか)。各真を最も重なる予測に帰属させ、予測 j に帰属した真の数 m_j が
    ``objects_per_pred``、``under`` = Σ max(m_j − 1, 0)(1 つの予測が何個の真を抱えたか)。
    背景に帰属した予測は ``spurious``(偽)、背景に帰属した真は ``missed``(欠落)に数える。
    返り値: ``over``、``under``、``spurious``、``missed``、``labels_true`` / ``pieces_per_true``、``labels_pred`` / ``objects_per_pred``、
    ``over_segmented_true``(k ≥ 2 の真のラベル)、``under_segmented_pred``(m ≥ 2 の予測のラベル)。"""
    op = "seg_under_over_segmentation"
    p, t = _pair(labels_pred, labels_true, op)
    bg = _background(background, op)
    T, ua, ub = _dense_table(p, t, op)
    fr, fc = _fg_index(ua, bg), _fg_index(ub, bg)
    pieces = np.zeros(fr.size, np.int64)
    spurious = 0
    if fc.size:
        owner = np.argmax(T[:, fc], axis=0)                 # 各予測の多数決の真(行の添字、背景も候補)
        for j, i in zip(fc, owner):
            if ua[i] == bg:
                spurious += 1
            else:
                pieces[np.searchsorted(fr, i)] += 1
    objs = np.zeros(fc.size, np.int64)
    missed = 0
    if fr.size:
        owner = np.argmax(T[fr, :], axis=1)
        for i, j in zip(fr, owner):
            if ub[j] == bg:
                missed += 1
            else:
                objs[np.searchsorted(fc, j)] += 1
    return {"over": int(np.maximum(pieces - 1, 0).sum()), "under": int(np.maximum(objs - 1, 0).sum()),
            "spurious": spurious, "missed": missed,
            "labels_true": ua[fr], "pieces_per_true": pieces, "labels_pred": ub[fc], "objects_per_pred": objs,
            "over_segmented_true": ua[fr][pieces >= 2], "under_segmented_pred": ub[fc][objs >= 2]}


# ───────────────────────────── 6. 個数の一致 ─────────────────────────────
def seg_object_counts_match(labels_pred, labels_true, *, background: int = 0, min_overlap: float = 0.5) -> Dict[str, object]:
    """物体の個数の一致: 分裂・融合・欠落・偽・一致を、「主に重なる」辺の 2 部グラフの次数で数える。

    真 i と予測 j(どちらも背景でない)の間に辺を置く条件 = 重なり n_ij ≥ ``min_overlap`` × min(|i|, |j|)
    (小さい方がもう一方に主に入っている)。真の次数 d_i、予測の次数 e_j:
    ``missed`` = #{d_i = 0}、``false`` = #{e_j = 0}、``split`` = #{d_i ≥ 2}(1 つの真が複数の予測に割れた)、
    ``merged`` = #{e_j ≥ 2}(1 つの予測が複数の真を抱えた)、``matched`` = #{d_i = 1 かつ その相手の e_j = 1}。
    ``counts_match`` = 真と予測の個数が同じで全部が一致。min_overlap > 0.5 なら各予測は高々 1 つの真に「主に入る」が、
    真が小さく予測が大きい辺もあるので融合は検出できる。
    返り値: 上の数 + ``n_true`` / ``n_pred``、``edges``(真ラベル, 予測ラベル)の (m, 2)、``split_true`` / ``merged_pred`` /
    ``missed_true`` / ``false_pred``(ラベルの配列)、``min_overlap``。"""
    op = "seg_object_counts_match"
    p, t = _pair(labels_pred, labels_true, op)
    bg = _background(background, op)
    try:
        mo = float(min_overlap)
    except (TypeError, ValueError):
        raise ValueError("%s: min_overlap must be a number (got %r)" % (op, min_overlap)) from None
    if not (0.0 < mo <= 1.0):
        raise ValueError("%s: min_overlap must be in (0, 1] (got %r)" % (op, min_overlap))
    T, ua, ub = _dense_table(p, t, op)
    fr, fc = _fg_index(ua, bg), _fg_index(ub, bg)
    sub = T[np.ix_(fr, fc)].astype(np.float64)
    a = T.sum(axis=1)[fr].astype(np.float64)[:, None]
    b = T.sum(axis=0)[fc].astype(np.float64)[None, :]
    edge = (sub > 0) & (sub >= mo * np.minimum(a, b) - 1e-9)
    d = edge.sum(axis=1)
    e = edge.sum(axis=0)
    matched = 0
    for k in range(fr.size):
        if d[k] == 1:
            j = int(np.flatnonzero(edge[k])[0])
            if e[j] == 1:
                matched += 1
    ei, ej = np.nonzero(edge)
    edges = np.stack([ua[fr][ei], ub[fc][ej]], axis=1) if ei.size else np.zeros((0, 2), np.int64)
    out = {"n_true": int(fr.size), "n_pred": int(fc.size), "matched": matched,
           "split": int((d >= 2).sum()), "merged": int((e >= 2).sum()),
           "missed": int((d == 0).sum()), "false": int((e == 0).sum()),
           "split_true": ua[fr][d >= 2], "merged_pred": ub[fc][e >= 2],
           "missed_true": ua[fr][d == 0], "false_pred": ub[fc][e == 0],
           "edges": edges, "min_overlap": mo}
    out["counts_match"] = bool(fr.size == fc.size and matched == fr.size)
    return out


# ───────────────────────────── 7. 採点表 ─────────────────────────────
def seg_score_card(labels_pred, labels_true, *, background: int = 0, tau: float = 2.0, min_overlap: float = 0.5) -> Dict[str, float]:
    """全部の物差しを 1 枚に: Dice・Jaccard(マスク)、VI・split・merge、Rand・ARI(``segcompare``)、境界 F(τ)、
    Hausdorff・HD95・ASSD(境界が無ければ NaN)、過分割・未分割、分裂・融合・欠落・偽・一致、個数。

    ``segcompare`` には a = 真、b = 予測で渡す(split = 予測が真を切った量、merge = 予測が真を貼った量)。
    値は float か int の平らな dict(表にそのまま並ぶ)。"""
    op = "seg_score_card"
    p, t = _pair(labels_pred, labels_true, op)
    bg = _background(background, op)
    dj = seg_dice_jaccard(p, t, background=bg)
    vi = segcompare.seg_variation_of_information(t, p)
    rd = segcompare.seg_rand(t, p)
    bf = seg_boundary_f(p, t, tau=tau)
    try:
        hd = seg_hausdorff(p, t)
        sd = seg_mean_surface_distance(p, t)
        h, h95, assd = hd["hausdorff"], hd["hausdorff_percentile"], sd["assd"]
    except ValueError:
        h = h95 = assd = math.nan
    uo = seg_under_over_segmentation(p, t, background=bg)
    cm = seg_object_counts_match(p, t, background=bg, min_overlap=min_overlap)
    return {"dice": dj["dice"], "jaccard": dj["jaccard"],
            "voi": vi["voi"], "split_bits": vi["split"], "merge_bits": vi["merge"],
            "rand_index": rd["rand_index"], "adjusted_rand_index": rd["adjusted_rand_index"],
            "boundary_f": bf["f"], "boundary_precision": bf["precision"], "boundary_recall": bf["recall"], "tau": bf["tau"],
            "hausdorff": h, "hausdorff95": h95, "assd": assd,
            "over": uo["over"], "under": uo["under"],
            "n_true": cm["n_true"], "n_pred": cm["n_pred"], "matched": cm["matched"], "split": cm["split"],
            "merged": cm["merged"], "missed": cm["missed"], "false": cm["false"], "counts_match": cm["counts_match"]}

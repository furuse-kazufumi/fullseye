# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""anomeval — 異常検知の汎用の評価指標(画像 AUROC・画素 AUROC・PRO / AUPRO・領域ごとの重なり)。

欠陥図を出す方法(良品統計の変動モデル ``varmodel``・RPCA ``dc_rpca_sparse``・ゴールデン差分
``compare_to_golden``・パッチ特徴の方法 …)を**同じ物差し**で比べるための op 族。どの方法の
中身にも依存せず、「スコアの図」と「欠陥マスク」(画像単位なら「スコア」と「ラベル」)だけを受ける。

  * :func:`anomaly_image_auroc` — 画像ごとのスコアと良/不良のラベルから AUROC(Mann–Whitney)。
  * :func:`anomaly_pixel_auroc` — 画素ごとのスコアと欠陥マスクから AUROC。
  * :func:`anomaly_pro` — PRO 曲線(欠陥の連結領域ごとの重なりの平均)と、FPR 0.3 までの
    正規化面積 AUPRO(Bergmann ら CVPR 2020 の定義と、その後の慣習の積分上限)。
  * :func:`anomaly_region_overlap` — 1 つの閾値での領域ごとの重なりと、検出した領域の割合。

約束: AUROC は**厳密**(同点は 1/2、順位の中央値で数える)、PRO の曲線は閾値の格子を使わず
**すべての異なるスコアで**評価する(並べ替えた累積和)。定義できないとき(欠陥も良品も無い等)は
値を返さず ``ValueError``。

出典(公開文献のみ): J. A. Hanley & B. J. McNeil, *Radiology* 143:29, 1982(AUROC = Mann–Whitney)/
P. Bergmann, M. Fauser, D. Sattlegger, C. Steger, *CVPR* 2020(PRO、FPR 0.3 までの積分)。
"""
from __future__ import annotations

import numpy as np

__all__ = ["anomaly_image_auroc", "anomaly_pixel_auroc", "anomaly_pro", "anomaly_region_overlap"]

_MAX_VALUES = 1 << 27                     # 1 回で受け付ける値の数の上限(メモリの防壁)


def _rankdata(x):
    from scipy.stats import rankdata       # noqa: PLC0415 — 遅延 import
    return rankdata(x)


def _scores(x, name, op):
    """(n, H, W) の有限な float64 へ。2-D 1 枚は (1, H, W)。"""
    if isinstance(x, (list, tuple)):
        if len(x) == 0:
            raise ValueError("%s: %s is empty (0 maps)" % (op, name))
        arrs = [np.asarray(a, dtype=np.float64) for a in x]
        if any(a.ndim != 2 for a in arrs) or len({a.shape for a in arrs}) != 1:
            raise ValueError("%s: %s must be equal-shaped 2-D maps" % (op, name))
        a = np.stack(arrs)
    else:
        a = np.asarray(x, dtype=np.float64)
    if a.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if a.ndim == 2:
        a = a[None]
    if a.ndim != 3:
        raise ValueError("%s: %s must be (n, H, W) or 2-D, got shape %s" % (op, name, a.shape))
    if a.size > _MAX_VALUES:
        raise ValueError("%s: %s has %d values (> %d)" % (op, name, a.size, _MAX_VALUES))
    if not np.isfinite(a).all():
        raise ValueError("%s: %s contains non-finite values" % (op, name))
    return a


def _binary(m, shape, name, op):
    mk = np.stack([np.asarray(x) for x in m]) if isinstance(m, (list, tuple)) else np.asarray(m)
    if mk.size == 0:
        raise ValueError("%s: %s is empty" % (op, name))
    if mk.ndim == len(shape) - 1 and len(shape) == 3:
        mk = mk[None]
    if mk.shape != tuple(shape):
        raise ValueError("%s: %s %s must match the scores %s" % (op, name, mk.shape, tuple(shape)))
    if mk.dtype != bool:
        u = np.unique(mk)
        if not np.isin(u, (0, 1)).all():
            raise ValueError("%s: %s must be binary (0/1 or bool), found %s" % (op, name, u[:5]))
        mk = mk.astype(bool)
    return mk


def _auroc(s, y, op):
    pos = int(y.sum())
    neg = int(y.size - pos)
    if pos == 0 or neg == 0:
        raise ValueError("%s: need both positives and negatives (got %d / %d)" % (op, pos, neg))
    r = _rankdata(s)
    auc = (float(r[y].sum()) - pos * (pos + 1) / 2.0) / (pos * float(neg))
    return float(auc), pos, neg


def anomaly_image_auroc(scores, labels):
    """Image-level AUROC from one anomaly score per image and a good/defective label per image (``table``).

    ``scores`` is a 1-D array (higher = more anomalous), ``labels`` the same length with 1 /
    True = defective. Exact Mann–Whitney statistic with mid-ranks for ties (Hanley & McNeil
    1982): the probability that a random defective image outscores a random good one, ties
    counting 1/2. Returns ``auroc``, ``n_pos``, ``n_neg``.

    Raises ``ValueError`` on empty / mismatched / non-finite input, non-binary labels, or when
    all images carry the same label (AUROC undefined).
    """
    op = "anomaly_image_auroc"
    s = np.asarray(scores, dtype=np.float64).ravel()
    if s.size == 0:
        raise ValueError("%s: scores is empty" % op)
    if not np.isfinite(s).all():
        raise ValueError("%s: scores contains non-finite values" % op)
    y = _binary(labels, s.shape, "labels", op) if np.asarray(labels).ndim == 1 else None
    if y is None:
        raise ValueError("%s: labels must be 1-D with one label per score" % op)
    auc, pos, neg = _auroc(s, y, op)
    return {"auroc": auc, "n_pos": pos, "n_neg": neg}


def anomaly_pixel_auroc(scores, masks):
    """Pixel-level AUROC of anomaly score maps against ground-truth defect masks (``table``).

    ``scores`` and ``masks`` are (n, H, W) (or lists / single 2-D maps); higher score = more
    anomalous. Exact Mann–Whitney statistic with mid-ranks for ties: the probability that a
    random defect pixel outscores a random good pixel, ties counting 1/2. Returns ``auroc``,
    ``n_pos``, ``n_neg``.

    Raises ``ValueError`` on empty / mismatched / non-finite input, non-binary masks, or when
    the masks contain no defect pixel or no good pixel (AUROC undefined).
    """
    op = "anomaly_pixel_auroc"
    s = _scores(scores, "scores", op)
    mk = _binary(masks, s.shape, "masks", op)
    auc, pos, neg = _auroc(s.ravel(), mk.ravel(), op)
    return {"auroc": auc, "n_pos": pos, "n_neg": neg}


def _regions(mk):
    """マスクごとの 8 連結領域。返り: ラベル図 (n,H,W)(全体で通し番号)、領域の面積。"""
    from scipy import ndimage as ndi       # noqa: PLC0415
    labs = np.zeros(mk.shape, dtype=np.int64)
    areas = [np.zeros(0, dtype=np.int64)]
    nreg = 0
    for i in range(mk.shape[0]):
        lab, nr = ndi.label(mk[i], structure=np.ones((3, 3), dtype=int))
        if nr:
            labs[i] = np.where(lab > 0, lab + nreg, 0)
            areas.append(np.bincount(lab.ravel())[1:])
            nreg += nr
    return labs, np.concatenate(areas), nreg


def anomaly_pro(scores, masks, fpr_max=0.3):
    """Per-region overlap (PRO) curve and its normalised area AUPRO up to ``fpr_max`` (``table``).

    Definition (Bergmann et al., CVPR 2020): at a threshold t, every 8-connected defect region
    C of every mask scores ``|{score >= t} ∩ C| / |C|``; PRO(t) is the mean over all regions,
    so a small defect weighs as much as a large one. FPR(t) is the fraction of all good pixels
    with score >= t. The curve is evaluated exactly at every distinct score (sorted cumulative
    sums, no threshold grid), starts at (0, 0), is integrated by the trapezoid rule up to
    ``fpr_max`` (the customary 0.3; linear interpolation at the cut) and divided by ``fpr_max``
    → ``aupro`` in [0, 1]. Returns ``aupro``, ``fpr`` / ``pro`` (the curve up to the cut),
    ``n_regions``, ``fpr_max``.

    Raises ``ValueError`` on empty / mismatched / non-finite input, non-binary masks, no defect
    region, no good pixel, or ``fpr_max`` outside (0, 1].
    """
    op = "anomaly_pro"
    s = _scores(scores, "scores", op)
    mk = _binary(masks, s.shape, "masks", op)
    fm = float(fpr_max)
    if not (0.0 < fm <= 1.0):
        raise ValueError("%s: fpr_max must be in (0, 1], got %r" % (op, fpr_max))
    labs, areas, nreg = _regions(mk)
    nneg = int((~mk).sum())
    if nreg == 0 or nneg == 0:
        raise ValueError("%s: need at least one defect region and one good pixel (got %d / %d)"
                         % (op, nreg, nneg))
    w = np.zeros(nreg + 1)
    w[1:] = 1.0 / (areas * float(nreg))
    flat = s.ravel()
    order = np.argsort(-flat, kind="mergesort")
    sv = flat[order]
    cp = np.cumsum(w[labs.ravel()[order]])
    cn = np.cumsum((~mk.ravel()[order]).astype(np.float64)) / nneg
    last = np.r_[np.nonzero(np.diff(sv) != 0)[0], sv.size - 1]       # 同じスコアの群の末尾
    fpr = np.r_[0.0, cn[last]]
    pro = np.r_[0.0, cp[last]]
    cut = int(np.searchsorted(fpr, fm, side="right"))
    fx, py = fpr[:cut], pro[:cut]
    if cut < fpr.size and fx[-1] < fm:
        x0, x1, y0, y1 = fpr[cut - 1], fpr[cut], pro[cut - 1], pro[cut]
        yi = y0 + (y1 - y0) * (fm - x0) / (x1 - x0) if x1 > x0 else y1
        fx = np.r_[fx, fm]
        py = np.r_[py, yi]
    area = float(np.sum((fx[1:] - fx[:-1]) * (py[1:] + py[:-1]) * 0.5))
    return {"aupro": area / fm, "fpr": fx, "pro": py, "n_regions": int(nreg), "fpr_max": fm}


def anomaly_region_overlap(predicted, masks, min_overlap=0.5):
    """Per-region overlap of a binary defect prediction with the ground-truth regions at one operating point (``table``).

    ``predicted`` and ``masks`` are binary (n, H, W) (or 2-D). For every 8-connected
    ground-truth region C: ``overlap = |predicted ∩ C| / |C|``; a region counts as detected
    when ``overlap >= min_overlap``. Returns ``overlap`` (per region, in mask order),
    ``pro`` (their mean = one point of the PRO curve), ``detected_fraction``, ``hit_any``
    (fraction of regions touched by at least one predicted pixel), ``fpr`` (predicted good
    pixels / good pixels), ``n_regions``, ``min_overlap``.

    Raises ``ValueError`` on empty / mismatched / non-binary input, no ground-truth region, or
    ``min_overlap`` outside (0, 1].
    """
    op = "anomaly_region_overlap"
    pr = np.stack([np.asarray(x) for x in predicted]) if isinstance(predicted, (list, tuple)) \
        else np.asarray(predicted)
    if pr.size == 0:
        raise ValueError("%s: predicted is empty" % op)
    if pr.ndim == 2:
        pr = pr[None]
    if pr.ndim != 3:
        raise ValueError("%s: predicted must be (n, H, W) or 2-D, got %s" % (op, pr.shape))
    pr = _binary(pr, pr.shape, "predicted", op)
    mk = _binary(masks, pr.shape, "masks", op)
    mo = float(min_overlap)
    if not (0.0 < mo <= 1.0):
        raise ValueError("%s: min_overlap must be in (0, 1], got %r" % (op, min_overlap))
    labs, areas, nreg = _regions(mk)
    if nreg == 0:
        raise ValueError("%s: the masks contain no defect region" % op)
    hit = np.bincount(labs[pr], minlength=nreg + 1)[1:]
    ov = hit / areas
    nneg = int((~mk).sum())
    return {"overlap": ov, "pro": float(ov.mean()), "detected_fraction": float((ov >= mo).mean()),
            "hit_any": float((hit > 0).mean()),
            "fpr": float((pr & ~mk).sum() / nneg) if nneg else 0.0,
            "n_regions": int(nreg), "min_overlap": mo}

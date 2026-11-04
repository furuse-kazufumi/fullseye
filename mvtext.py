# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mvtext —— 文字行の傾きと字の斜体角、字の切り出し、NURBS の補間。

傾きは Postl の射影の差分の 2 乗和を、画素を回さずインクの座標だけで計算する。
出典: W. Postl, Proc. ICPR 1986, 687-689; D. S. Bloomberg et al., Proc. SPIE 2422, 302-320 (1995);
L. Piegl and W. Tiller, The NURBS Book, 2nd ed., Springer (1997), sec. 9.2.1。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _ink(image_or_region, op):
    a = np.asarray(image_or_region)
    if a.size == 0:
        raise ValueError("%s: image is empty — pass at least one pixel" % op)
    if a.ndim != 2:
        raise ValueError("%s: image must be 2-D, got shape %r" % (op, a.shape))
    if a.dtype == bool:
        return a
    v = a.astype(np.float64)
    if not np.isfinite(v).all():
        raise ValueError("%s: image has NaN/inf pixels" % op)
    if v.max() == v.min():
        return np.zeros(v.shape, bool)
    hist, edges = np.histogram(v, bins=64)
    p = hist.astype(np.float64) / hist.sum()
    mids = 0.5 * (edges[:-1] + edges[1:])
    w0 = np.cumsum(p)
    m0 = np.cumsum(p * mids)
    between = np.where((w0 > 0) & (w0 < 1), (m0[-1] * w0 - m0) ** 2 / np.maximum(w0 * (1 - w0), 1e-12), 0)
    t = mids[int(np.argmax(between))]
    dark = v < t
    # インクは少数派の側と見なす(明るい地に暗い字でも、その逆でも同じ答えにする)。
    return dark if dark.sum() <= (~dark).sum() else ~dark


def _peak(angles, scores):
    """走査の最大を 3 点放物線で小数へ寄せる。"""
    i = int(np.argmax(scores))
    if 0 < i < len(angles) - 1:
        d = scores[i - 1] - 2.0 * scores[i] + scores[i + 1]
        if d < 0:
            return float(angles[i] + 0.5 * (scores[i - 1] - scores[i + 1]) / d * (angles[1] - angles[0]))
    return float(angles[i])


def _project_score(values):
    lo = np.floor(values.min())
    bins = np.bincount((np.floor(values - lo)).astype(int))
    diff = np.diff(bins.astype(np.float64))
    return float(np.sum(diff * diff))


def text_line_orientation(image, max_angle=30.0, step=0.25):
    """文字行の傾きを射影の鋭さの最大で求める(度)。

    行の射影は傾きが合うと階段が最も鋭くなる。その鋭さ(隣り合う射影の差の 2 乗和)を
    ``-max_angle .. max_angle`` で走査する。角度の向きはこの repo の矩形と同じで、右へ進むと行
    が増える向きが正。インクが無い画像は 0.0 を返す(理由: 傾きを決める手がかりが無い)。
    空の入力(``image`` が 0 要素)は ValueError。

    Args:
        image: 灰色画像か bool の領域 (H, W)。灰色は Otsu のしきい値で二値にする。
        max_angle: 走査の範囲(度、> 0)。
        step: 走査の刻み(度、> 0)。

    Returns:
        傾き(度)。
    """
    op = "text_line_orientation"
    ink = _ink(image, op)
    ma, st = float(max_angle), float(step)
    if not (ma > 0 and st > 0):
        raise ValueError("%s: max_angle and step must be positive" % op)
    r, c = np.nonzero(ink)
    if r.size == 0:
        return 0.0
    r = r - r.mean()
    c = c - c.mean()
    angles = np.arange(-ma, ma + st / 2.0, st)
    scores = [_project_score(r * np.cos(np.deg2rad(a)) - c * np.sin(np.deg2rad(a))) for a in angles]
    return _peak(angles, scores)


def text_line_slant(image, max_angle=45.0, step=0.5):
    """水平な文字行の字の斜体角を、列の射影の鋭さの最大で求める(度)。

    せん断 ``col' = col + (row - row0) tan(a)`` で縦の字画が立つと列の射影が最も鋭くなる。
    正の角度は下へ行くほど左へ寄った字(上が右へ倒れた字)。
    インクが無い画像は 0.0 を返す(理由: 斜体角を決める手がかりが無い)。
    空の入力(``image`` が 0 要素)は ValueError。

    Args:
        image: 灰色画像か bool の領域 (H, W)。文字行は水平に直しておく。
        max_angle: 走査の範囲(度、0 より大きく 90 未満)。
        step: 走査の刻み(度、> 0)。

    Returns:
        斜体角(度)。
    """
    op = "text_line_slant"
    ink = _ink(image, op)
    ma, st = float(max_angle), float(step)
    if not (0 < ma < 90 and st > 0):
        raise ValueError("%s: max_angle must be in (0, 90) and step positive" % op)
    r, c = np.nonzero(ink)
    if r.size == 0:
        return 0.0
    r = r - r.mean()
    angles = np.arange(-ma, ma + st / 2.0, st)
    scores = [_project_score(c + r * np.tan(np.deg2rad(a))) for a in angles]
    return _peak(angles, scores)


def segment_characters(image, min_area=4, max_gap=1):
    """文字行の画像を、字ごとの列の塊へ切り分けたラベル画像にする。

    連結成分を列の範囲で束ね、列の隙間が ``max_gap`` 以下の成分は同じ字にする(``i`` の点や
    ``=`` のように上下へ分かれた字を 1 字に数えるため)。``min_area`` 未満の成分は雑音として
    捨てる。ラベルは左から順。インクが無い画像は全 0 を返す(理由: 字が無い)。
    空の入力(``image`` が 0 要素)は ValueError。

    Args:
        image: 灰色画像か bool の領域 (H, W)。
        min_area: 残す連結成分の最小の画素数(>= 1)。
        max_gap: 同じ字と見なす列の隙間(>= 0)。隙間が負(重なり)の成分は必ず束ねる。

    Returns:
        ``image`` と同じ形の整数ラベル画像(背景 0、字 1..n)。
    """
    op = "segment_characters"
    ink = _ink(image, op)
    if int(min_area) < 1 or int(max_gap) < 0:
        raise ValueError("%s: min_area must be >= 1 and max_gap >= 0" % op)
    labels, n = ndimage.label(ink, structure=np.ones((3, 3), bool))
    out = np.zeros(ink.shape, dtype=np.int32)
    if n == 0:
        return out
    spans = []
    for i, sl in enumerate(ndimage.find_objects(labels), 1):
        if int((labels[sl] == i).sum()) >= int(min_area):
            spans.append((sl[1].start, sl[1].stop, i))
    spans.sort()
    glyph, right = 0, None
    for start, stop, i in spans:
        if right is None or start - right > int(max_gap):
            glyph += 1
            right = stop
        else:
            right = max(right, stop)
        out[labels == i] = glyph
    return out


def select_characters(labels, min_height_ratio=0.5, max_height_ratio=1.5, max_width_ratio=2.0):
    """字のラベル画像から、高さと幅が中央値から外れた塊を落として左から振り直す。

    高さと幅の中央値に対する比で判定する。塊が 1 つも無いと全 0 を返す(理由: 字が無い)。
    空の入力(``labels`` が 0 要素)は ValueError。

    Args:
        labels: :func:`segment_characters` のラベル画像。
        min_height_ratio: 高さの下限(中央値に対する比)。
        max_height_ratio: 高さの上限(中央値に対する比)。
        max_width_ratio: 幅の上限(中央値に対する比)。

    Returns:
        ``labels`` と同じ形の整数ラベル画像。
    """
    op = "select_characters"
    a = np.asarray(labels)
    if a.size == 0:
        raise ValueError("%s: labels are empty — pass at least one pixel" % op)
    if a.ndim != 2 or not np.issubdtype(a.dtype, np.integer) or a.min() < 0:
        raise ValueError("%s: labels must be a 2-D non-negative integer array" % op)
    if not (0 <= float(min_height_ratio) <= float(max_height_ratio)) or float(max_width_ratio) <= 0:
        raise ValueError("%s: the ratios must be ordered and positive" % op)
    objs = [(i + 1, sl) for i, sl in enumerate(ndimage.find_objects(a)) if sl is not None]
    out = np.zeros(a.shape, dtype=np.int32)
    if not objs:
        return out
    heights = np.array([sl[0].stop - sl[0].start for _, sl in objs], dtype=np.float64)
    widths = np.array([sl[1].stop - sl[1].start for _, sl in objs], dtype=np.float64)
    hm, wm = float(np.median(heights)), float(np.median(widths))
    keep = [(sl[1].start, i) for (i, sl), h, w in zip(objs, heights, widths)
            if float(min_height_ratio) * hm <= h <= float(max_height_ratio) * hm
            and w <= float(max_width_ratio) * wm]
    for new, (_, i) in enumerate(sorted(keep), 1):
        out[a == i] = new
    return out


def _basis(u, knots, degree):
    """B スプラインの基底の行列 (len(u), n)。Cox-de Boor の漸化式。"""
    u = np.asarray(u, dtype=np.float64)
    t = np.asarray(knots, dtype=np.float64)
    n = len(t) - degree - 1
    N = np.zeros((len(u), len(t) - 1))
    for i in range(len(t) - 1):
        N[:, i] = (u >= t[i]) & (u < t[i + 1])
    last = np.nonzero(t[:-1] < t[1:])[0][-1]
    N[u >= t[-1], :] = 0.0
    N[u >= t[-1], last] = 1.0
    for p in range(1, degree + 1):
        M = np.zeros((len(u), len(t) - 1 - p))
        for i in range(len(t) - 1 - p):
            d1, d2 = t[i + p] - t[i], t[i + p + 1] - t[i + 1]
            if d1 > 0:
                M[:, i] += (u - t[i]) / d1 * N[:, i]
            if d2 > 0:
                M[:, i] += (t[i + p + 1] - u) / d2 * N[:, i + 1]
        N = M
    return N[:, :n]


def gen_nurbs_interp(points, degree=3):
    """点列を全部通る非有理 B スプラインの制御点を求める(大域補間)。

    媒介変数は弦長、節点は媒介変数の平均(The NURBS Book の 9.2.1)で決め、基底の線形方程式を
    解く。重みは全部 1 なので、返りをそのまま ``nurbs_curve`` に渡せる(``knots`` と ``degree``
    も一緒に渡す)。連続する同じ点は ValueError(弦長が 0 になり媒介変数が決まらない)。
    空の入力(``points`` が 0 要素)は ValueError。

    Args:
        points: (N, d) の点列(N > degree)。
        degree: 次数(>= 1)。

    Returns:
        ``control_points`` (N, d)、``knots`` (N+degree+1,)、``weights``、``degree``、``u`` を持つ dict。
    """
    op = "gen_nurbs_interp"
    Q = np.asarray(points, dtype=np.float64)
    if Q.size == 0:
        raise ValueError("%s: points are empty — pass at least degree + 1 points" % op)
    if Q.ndim != 2 or not np.isfinite(Q).all():
        raise ValueError("%s: points must be a finite (N, d) array" % op)
    p = int(degree)
    n = Q.shape[0]
    if p < 1 or n <= p:
        raise ValueError("%s: need degree >= 1 and more than degree points" % op)
    chords = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    if (chords <= 0).any():
        raise ValueError("%s: consecutive points must differ" % op)
    u = np.concatenate([[0.0], np.cumsum(chords)]) / chords.sum()
    u[-1] = 1.0
    knots = np.zeros(n + p + 1)
    knots[-(p + 1):] = 1.0
    for j in range(1, n - p):
        knots[j + p] = u[j:j + p].mean()
    A = _basis(u, knots, p)
    P = np.linalg.solve(A, Q)
    return {"control_points": P, "knots": knots, "weights": np.ones(n), "degree": p, "u": u}

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mvmorph —— 二値形態学の古典: Golay の構造要素組・ヒットオアミス・肥厚・SKIZ・分離の開放。

領域は 2-D の bool 配列で受け取り bool で返す(``opening_seg`` だけラベル画像)。
Golay の文字は 5 つだけ実装した。``l`` / ``m`` / ``e`` / ``i`` は細線化と端点の教科書の形、
``c`` はこの repo の定義で、凹の角を埋める形(中心がミス、隣の 2 辺と間の角がヒット)。残りの
文字は ValueError で拒む。他の製品の同名の文字との形の一致は確かめていない。

出典: J. Serra, Image Analysis and Mathematical Morphology, Academic Press (1982);
P. Soille, Morphological Image Analysis, 2nd ed., Springer (2003);
R. C. Gonzalez and R. E. Woods, Digital Image Processing, 4th ed., ch. 9 (2018)。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

#: 3x3 の周りの 8 画素を時計回りに並べた順(N から)。45 度の回転はこの輪を 1 つ送る。
_RING = ((0, 1), (0, 2), (1, 2), (2, 2), (2, 1), (2, 0), (1, 0), (0, 0))
_N, _NE, _E, _SE, _S, _SW, _W, _NW = range(8)

#: 文字 → (ヒットの輪の添字, ミスの輪の添字, 中心の扱い)。
#: 中心の扱い: 1 = ヒット、0 = ミス、None = 問わない。
_GOLAY = {
    "l": ((_SW, _S, _SE), (_NW, _N, _NE), 1),
    "m": ((_W, _S), (_N, _NE, _E), 1),
    "e": ((_S,), (_NW, _N, _NE, _E, _W), 1),
    "i": ((), (_N, _NE, _E, _SE, _S, _SW, _W, _NW), 1),
    "c": ((_W, _SW, _S), (), 0),
}


def _region(region, op):
    a = np.asarray(region)
    if a.size == 0:
        raise ValueError("%s: region is empty — pass at least one pixel" % op)
    if a.ndim != 2:
        raise ValueError("%s: region must be 2-D, got shape %r" % (op, a.shape))
    if a.dtype != bool and not np.isfinite(a.astype(np.float64)).all():
        raise ValueError("%s: region has NaN/inf pixels" % op)
    return a > 0 if a.dtype != bool else a


def _se_pair(hit, miss, op):
    h = np.asarray(hit, dtype=bool)
    m = np.asarray(miss, dtype=bool)
    if h.ndim != 2 or h.shape != m.shape or h.size == 0:
        raise ValueError("%s: hit/miss must be equal-shape 2-D arrays" % op)
    if h.shape[0] % 2 == 0 or h.shape[1] % 2 == 0:
        raise ValueError("%s: hit/miss must have odd sides" % op)
    if (h & m).any():
        raise ValueError("%s: a pixel cannot be in both hit and miss" % op)
    if not (h.any() or m.any()):
        raise ValueError("%s: hit and miss are both empty" % op)
    return h, m


def golay_elements(letter, rotation=0):
    """Golay の文字の 3x3 構造要素組(ヒット、ミス)を 45 度刻みの回転つきで作る。

    ``letter`` は ``l`` / ``m`` / ``e`` / ``i`` / ``c``。``rotation`` は 45 度の時計回りの回数。
    実装していない文字は ValueError。

    Args:
        letter: Golay の文字。
        rotation: 回転の回数(整数、8 で一周)。

    Returns:
        ``hit`` と ``miss``(どちらも (3, 3) の bool)を持つ dict。
    """
    op = "golay_elements"
    key = str(letter).lower()
    if key not in _GOLAY:
        raise ValueError("%s: letter must be one of %s, got %r" % (op, ", ".join(sorted(_GOLAY)), letter))
    hits, misses, centre = _GOLAY[key]
    rot = int(rotation) % 8
    hit = np.zeros((3, 3), bool)
    miss = np.zeros((3, 3), bool)
    for i in hits:
        hit[_RING[(i + rot) % 8]] = True
    for i in misses:
        miss[_RING[(i + rot) % 8]] = True
    if centre == 1:
        hit[1, 1] = True
    elif centre == 0:
        miss[1, 1] = True
    return {"hit": hit, "miss": miss}


def _hmt(a, hit, miss):
    """画像の外は背景と見なすヒットオアミス変換。"""
    out = ndimage.binary_erosion(a, structure=hit, border_value=1 if not hit.any() else 0) if hit.any() \
        else np.ones(a.shape, bool)
    if miss.any():
        out = out & ndimage.binary_erosion(~a, structure=miss, border_value=1)
    return out


def hit_or_miss_golay(region, letter, rotation=0):
    """Golay の文字 1 つでヒットオアミス変換を掛ける(一致した中心の画素を返す)。

    画像の外は背景と見なす。空の入力(``region`` が 0 要素)は ValueError。

    Args:
        region: 2-D の領域。
        letter: Golay の文字。
        rotation: 45 度の回転の回数。

    Returns:
        ``region`` と同じ形の bool 配列。
    """
    a = _region(region, "hit_or_miss_golay")
    pair = golay_elements(letter, rotation)
    return _hmt(a, pair["hit"], pair["miss"])


def hit_or_miss_seq(region, letter):
    """Golay の文字の 8 回転すべてのヒットオアミスの和を返す。

    空の入力(``region`` が 0 要素)は ValueError。

    Args:
        region: 2-D の領域。
        letter: Golay の文字。

    Returns:
        ``region`` と同じ形の bool 配列。
    """
    a = _region(region, "hit_or_miss_seq")
    out = np.zeros(a.shape, bool)
    for rot in range(8):
        pair = golay_elements(letter, rot)
        out |= _hmt(a, pair["hit"], pair["miss"])
    return out


def thickening_hit_miss(region, hit, miss, iterations=1):
    """任意の構造要素組で肥厚を掛ける(``A ∪ HMT(A)`` を ``iterations`` 回)。

    ヒットオアミスで一致した中心の画素を領域へ足す。中心はミス側に置く(ヒット側に置くと
    何も増えない)。変化が止まったら早く抜ける。
    空の入力(``region`` が 0 要素)は ValueError。

    Args:
        region: 2-D の領域。
        hit: ヒットの構造要素(奇数辺の bool 配列)。
        miss: ミスの構造要素(同じ形)。
        iterations: 繰り返しの上限(>= 1)。

    Returns:
        ``region`` と同じ形の bool 配列。
    """
    op = "thickening_hit_miss"
    a = _region(region, op)
    h, m = _se_pair(hit, miss, op)
    n = int(iterations)
    if n < 1:
        raise ValueError("%s: iterations must be >= 1" % op)
    for _ in range(n):
        grown = a | _hmt(a, h, m)
        if (grown == a).all():
            break
        a = grown
    return a


def thickening_golay(region, letter, rotation=0, iterations=1):
    """Golay の文字 1 つで肥厚を掛ける。

    空の入力(``region`` が 0 要素)は ValueError。

    Args:
        region: 2-D の領域。
        letter: Golay の文字(中心がミスの文字だけが領域を増やす)。
        rotation: 45 度の回転の回数。
        iterations: 繰り返しの上限(>= 1)。

    Returns:
        ``region`` と同じ形の bool 配列。
    """
    a = _region(region, "thickening_golay")
    pair = golay_elements(letter, rotation)
    return thickening_hit_miss(a, pair["hit"], pair["miss"], iterations)


def thickening_seq(region, letter, iterations=0):
    """Golay の文字の回転を順に掛ける肥厚を、変化が止まるまで続ける。

    ``letter="c"`` は 90 度ずつ 4 回転で凹の角を埋め、4 連結の領域は外接矩形へ収束する(斜めの
    階段も凹の角の並びなので全部埋まる。凸包ではない)。``iterations`` が 0 なら収束まで。
    空の入力(``region`` が 0 要素)は ValueError。

    Args:
        region: 2-D の領域。
        letter: Golay の文字。
        iterations: 全回転を掛ける回数の上限(0 は収束まで)。

    Returns:
        ``region`` と同じ形の bool 配列。
    """
    op = "thickening_seq"
    a = _region(region, op)
    limit = int(iterations)
    if limit < 0:
        raise ValueError("%s: iterations must be >= 0" % op)
    step = 2 if str(letter).lower() == "c" else 1
    budget = limit if limit else a.size
    for _ in range(budget):
        before = a.copy()
        for rot in range(0, 8, step):
            pair = golay_elements(letter, rot)
            a = a | _hmt(a, pair["hit"], pair["miss"])
        if (a == before).all():
            break
    return a


def morph_hat(region, se):
    """開放で消えた画素と閉鎖で増えた画素の和を返す(白黒のトップハットの和)。

    画像の外は背景と見なす。空の入力(``region`` が 0 要素)は ValueError。

    Args:
        region: 2-D の領域。
        se: 構造要素(奇数辺の bool 配列)。

    Returns:
        ``region`` と同じ形の bool 配列。
    """
    op = "morph_hat"
    a = _region(region, op)
    s = np.asarray(se, dtype=bool)
    if s.ndim != 2 or s.size == 0 or not s.any():
        raise ValueError("%s: se must be a non-empty 2-D array with a true pixel" % op)
    opened = ndimage.binary_opening(a, structure=s)
    pad = max(s.shape)
    closed = ndimage.binary_closing(np.pad(a, pad), structure=s)[pad:-pad, pad:-pad]
    return (a & ~opened) | (closed & ~a)


def morph_skiz(region):
    """領域の連結成分の影響圏の境界(SKIZ)をユークリッド距離で求める。

    背景の各画素を最も近い連結成分へ割り当て、右か下の隣と割り当てが違う背景の画素を境界に
    する。連結成分が 1 つなら境界は無く、全部 False を返す(理由: 影響圏が 1 つで境界が無い)。
    空の入力(``region`` が 0 要素)は ValueError。

    Args:
        region: 2-D の領域。

    Returns:
        ``region`` と同じ形の bool 配列。
    """
    op = "morph_skiz"
    a = _region(region, op)
    labels, n = ndimage.label(a, structure=np.ones((3, 3), bool))
    if n < 2:
        return np.zeros(a.shape, bool)
    idx = ndimage.distance_transform_edt(labels == 0, return_distances=False, return_indices=True)
    zone = labels[idx[0], idx[1]]
    edge = np.zeros(a.shape, bool)
    edge[:-1, :] |= zone[:-1, :] != zone[1:, :]
    edge[:, :-1] |= zone[:, :-1] != zone[:, 1:]
    return edge & ~a


def opening_seg(region, se):
    """くびれで繋がった物体を収縮で切り離し、元の領域の中で広げ直してラベルにする。

    構造要素で収縮 → 連結成分 → 各成分を最寄りの画素へ広げる(``region`` の中だけ)。収縮で
    全部消えると全 0 のラベルを返す(理由: 切り離す種が残らない)。
    空の入力(``region`` が 0 要素)は ValueError。

    Args:
        region: 2-D の領域。
        se: 構造要素(奇数辺の bool 配列)。

    Returns:
        ``region`` と同じ形の整数ラベル画像(背景 0、物体 1..n)。
    """
    op = "opening_seg"
    a = _region(region, op)
    s = np.asarray(se, dtype=bool)
    if s.ndim != 2 or s.size == 0 or not s.any():
        raise ValueError("%s: se must be a non-empty 2-D array with a true pixel" % op)
    seeds, n = ndimage.label(ndimage.binary_erosion(a, structure=s))
    if n == 0:
        return np.zeros(a.shape, dtype=np.int32)
    idx = ndimage.distance_transform_edt(seeds == 0, return_distances=False, return_indices=True)
    return np.where(a, seeds[idx[0], idx[1]], 0).astype(np.int32)

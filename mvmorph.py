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


def _nearest_zone_sets(labels):
    """背景の各画素の「最も近い連結成分」の集合を、格子の 8 通りの対称(反転・転置)から集める。

    ``distance_transform_edt`` の最近傍は同距離のとき走査の向きで 1 つを選ぶ。8 通りの向きで
    選ばせた番号を全部持てば、集合は像の反転・転置に対して共変になる(同距離の成分が複数なら
    集合の要素も複数)。返り: 距離 ``d``(H, W)と番号 ``Z``(8, H, W)。
    """
    zs = []
    d = None
    for tr in (False, True):
        base = labels.T if tr else labels
        for fr in (False, True):
            for fc in (False, True):
                sl = (slice(None, None, -1 if fr else 1), slice(None, None, -1 if fc else 1))
                lab = base[sl]
                dd, idx = ndimage.distance_transform_edt(lab == 0, return_indices=True)
                z = lab[idx[0], idx[1]][sl]
                if tr:
                    z = z.T
                zs.append(z)
                if d is None:
                    d = dd[sl].T if tr else dd[sl]
    return d, np.stack(zs)


def _sets_disjoint(Zp, Zq):
    """画素ごとに 2 つの番号の集合((8, ...) の 2 枚)が共通の要素を持たないか。"""
    common = np.zeros(Zp.shape[1:], bool)
    for i in range(Zp.shape[0]):
        common |= (Zp[i][None] == Zq).any(axis=0)
    return ~common


def morph_skiz(region):
    """領域の連結成分の影響圏の境界(SKIZ)をユークリッド距離で求める。

    背景の各画素について最も近い連結成分(8 連結)の集合を求め、(1) 同距離の成分が 2 つ以上ある
    画素と、(2) 4 近傍の隣と集合が重ならない対のうち、自分の成分から遠い側(等しければ両方)の
    画素を境界にする。規則は対の両側を同じに扱うので、境界は像の上下・左右の反転と転置に対して
    対称(偶数幅の隙間では中央の 2 列、奇数幅では中央の 1 列)。その代わり線は 1 画素幅とは限らず、同距離の
    画素から 1 画素のひげ(端点)が出やすい(実写の金属組織 168 枚で、片側の規則の 265 本に対し 1,116 本)。
    1 画素幅の線や端点の数が要るなら、後段で細線化すること。連結成分が 1 つなら境界は無く、
    全部 False を返す(理由: 影響圏が 1 つで境界が無い)。空の入力(``region`` が 0 要素)は ValueError。

    Args:
        region: 2-D の領域。

    Returns:
        ``region`` と同じ形の bool 配列。
    """
    # ★2026-11-09 点検: 以前は「右か下の隣と割り当てが違う画素」だけに印を付けたので境界が上・左へ
    #   1 画素寄り、像を 180° 回して戻すと 147 画素(境界 105 画素)が一致しなかった。偶数幅の隙間で
    #   境界の列が 19(元)対 20(反転して戻す)。成分ごとに距離変換を取る厳密な参照と一致する。
    op = "morph_skiz"
    a = _region(region, op)
    labels, n = ndimage.label(a, structure=np.ones((3, 3), bool))
    if n < 2:
        return np.zeros(a.shape, bool)
    d, Z = _nearest_zone_sets(labels)
    edge = Z.min(axis=0) != Z.max(axis=0)                 # 同距離の成分が 2 つ以上(二等分線の上)
    dj = _sets_disjoint(Z[:, :-1, :], Z[:, 1:, :])
    edge[:-1, :] |= dj & (d[:-1, :] >= d[1:, :])
    edge[1:, :] |= dj & (d[1:, :] >= d[:-1, :])
    dj = _sets_disjoint(Z[:, :, :-1], Z[:, :, 1:])
    edge[:, :-1] |= dj & (d[:, :-1] >= d[:, 1:])
    edge[:, 1:] |= dj & (d[:, 1:] >= d[:, :-1])
    return edge & ~a


def _same_value_components(lab, mask):
    """``mask`` の中で ``lab`` の値が等しい画素どうしの 8 連結成分の番号(scipy.sparse.csgraph)。"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    h, w = lab.shape
    ids = np.arange(h * w).reshape(h, w)
    rows, cols = [], []
    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        r0, r1 = slice(0, h - dr), slice(dr, h)
        c0, c1 = (slice(0, w - dc), slice(dc, w)) if dc >= 0 else (slice(-dc, w), slice(0, w + dc))
        ok = mask[r0, c0] & mask[r1, c1] & (lab[r0, c0] == lab[r1, c1])
        rows.append(ids[r0, c0][ok])
        cols.append(ids[r1, c1][ok])
    r = np.concatenate(rows)
    c = np.concatenate(cols)
    g = coo_matrix((np.ones(r.size, np.int8), (r, c)), shape=(h * w, h * w))
    return connected_components(g, directed=False)[1].reshape(h, w)


def opening_seg(region, se):
    """くびれで繋がった物体を収縮で切り離し、元の領域の中で広げ直してラベルにする。

    構造要素で収縮 → 連結成分 → 各種を ``region`` の中だけを通って(測地的に)広げる。各画素は
    最寄りの種の番号を受けるが、その番号の区画が ``region`` の中で種とつながらない画素(背景を
    跨いだ割り当て)は、つながった区画から 8 近傍で 1 画素ずつ広げ直す。**種を 1 つも持たない
    連結成分(収縮で消えた小さな塊)は 0**(隣の物体の番号をもらわない)。収縮で全部消えると全 0 の
    ラベルを返す(理由: 切り離す種が残らない)。
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
    # ★2026-11-09 点検: 以前は最近傍の種の番号をそのまま配ったので、背景を跨いで割り当てた。
    #   大物体 30x25 から 3 px 離れた 3x3 の塊(5x5 の収縮で種が消える)が大物体の番号 1 をもらった。
    #   最近傍の区画が種と領域の中でつながる画素はそのまま(単一の凸な物体では以前と 0 px 差)。
    idx = ndimage.distance_transform_edt(seeds == 0, return_distances=False, return_indices=True)
    lab = np.where(a, seeds[idx[0], idx[1]], 0)
    comp = _same_value_components(lab, a)
    seeded = np.zeros(int(comp.max()) + 1, bool)
    seeded[comp[seeds > 0]] = True
    ok = a & seeded[comp]
    out = np.where(ok, lab, 0)
    todo = a & ~ok
    if todo.any():
        _grow_geodesic(out, ok, todo)                     # 種へ領域の中を通って行けない画素は 0 のまま
    return out.astype(np.int32)


_EIGHT_OFFSETS = np.array([(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)])


def _grow_geodesic(out, ok, todo):
    """``todo`` の画素へ、``ok`` の区画から 8 近傍で 1 画素ずつ番号を広げる(``out``・``ok``・``todo`` をその場で書き換える)。

    各層の画素は、最も近い ``ok`` の画素(距離 1 か √2 の隣)の番号を受ける。最近傍は、層の画素を
    ``todo`` の連結成分(8 連結)ごとに分け、その成分の前線を囲む小さな窓の中だけで ``distance_transform_edt``
    を取って決める —— 隣は窓の中に必ず在り、別の成分の画素は隣にならないので、全画面で取るのと同じ答え
    (同距離の選び方も含めて一致することを全画面版の参照で確かめている)。
    ★2026-11-09 独立レビュー: 以前は層ごとに全画面の距離変換を回したので、背景を跨いで別の種に近い長さ L の
    細長い部分があると O(L × H × W) になり、1024² で 21.4 s(修正前の opening_seg は 0.03 s)かかった。
    前線全体を 1 つの窓で囲んだ版では、細長い部分が左上と右下に 1 本ずつあると窓が画面全体に広がり 1024² で
    5.24 s に戻った(2 回目の確認)ので、窓を連結成分ごとに分けた。
    """
    h, w = out.shape
    comp, _ = ndimage.label(todo, structure=np.ones((3, 3), bool))
    fr = np.nonzero(ndimage.binary_dilation(ok, structure=np.ones((3, 3), bool)) & todo)
    while fr[0].size:
        cid = comp[fr]
        order = np.argsort(cid, kind="stable")
        rs, cs, cid = fr[0][order], fr[1][order], cid[order]
        cuts = np.flatnonzero(np.diff(cid)) + 1
        labs = np.empty(rs.size, dtype=out.dtype)
        for a, b in zip(np.r_[0, cuts], np.r_[cuts, rs.size]):
            pr, pc = rs[a:b], cs[a:b]
            r0, r1 = max(int(pr.min()) - 2, 0), min(int(pr.max()) + 3, h)
            c0, c1 = max(int(pc.min()) - 2, 0), min(int(pc.max()) + 3, w)
            jr, jc = ndimage.distance_transform_edt(~ok[r0:r1, c0:c1], return_distances=False,
                                                    return_indices=True)
            labs[a:b] = out[jr[pr - r0, pc - c0] + r0, jc[pr - r0, pc - c0] + c0]
        fr = (rs, cs)
        out[fr] = labs
        ok[fr] = True
        todo[fr] = False
        nr = (fr[0][:, None] + _EIGHT_OFFSETS[None, :, 0]).ravel()
        nc = (fr[1][:, None] + _EIGHT_OFFSETS[None, :, 1]).ravel()
        inside = (nr >= 0) & (nr < h) & (nc >= 0) & (nc < w)
        nr, nc = nr[inside], nc[inside]
        keep = todo[nr, nc]
        flat = np.unique(nr[keep] * w + nc[keep])
        fr = (flat // w, flat % w)

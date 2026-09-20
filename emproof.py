# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""emproof —— EM 連結体(コネクトミクス)の校正に古典 CV で「セカンドオピニオン」を出す。

電子顕微鏡(EM)の連続断面からニューロンを切り出す自動分割は、**融合**(別々の 2 細胞を 1 つの
ID にしてしまう)と**分断**(1 細胞を途中で 2 つの ID に切ってしまう)を残す。校正(proofreading)は
人がそれを探して直す作業で、先行研究(MergeNet 2017、Zung 2017、Dmitriev 2018、ConnectomeBench 2025)は
すべて深層学習で候補を出す。この族は **学習なし・閉形式・ノブつき** で同じ 2 種類の疑いを数え、
評価をホールドアウトで内蔵する ―― 深層学習の第 1 意見に対する、原理の違う第 2 意見。

* 融合の疑い = ラベルの**内部**を横切る膜。細胞膜(暗い稜線)は本来ラベルの境界にしか無い。内部の膜成分が
  境界帯の 2 か所を結ぶ「弦」になっていれば、そこで 2 細胞が貼り付いている(``seg_membrane_chord_score``)。
  ミトコンドリアの膜は閉じた輪で境界に触れないので弦にならない ―― 設計の肝。
* 分断の疑い = 膜の無い境界。隣接する 2 ラベルの境界画素のうち膜応答が閾値未満の割合
  (``seg_boundary_membrane_gap``)。人工の直線分断はこれで AUC 0.99(CREMI sample A、試作)。
* 膜応答は ``seg_membrane_response``(ガウス平滑した Hessian の固有値から暗い線を取る、Steger 流の閉形式)か、
  レジストリの ``sk_frangi``(scikit-image)。どちらも断面ごとに 99.5 percentile で正規化するのが前提。
* 評価は ``seg_inject_merge`` / ``seg_inject_split`` で正解ラベルに人工の誤りを仕込み、
  ``seg_label_changes`` で仕込んだ対を取り出し、``holdout_threshold`` で**閾値を訓練断面で選び別断面で測る**。

入力は 2-D の 1 断面(``labels2d`` = 整数ラベル、``image2d`` = 生 EM か膜応答)。立体は断面ごとに回して
z で積む(PoC ``examples/poc_em_second_opinion.py``)。numpy + scipy.ndimage だけで動く。
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy import ndimage as ndi

__all__ = [
    "seg_membrane_response", "seg_membrane_chord_score", "seg_boundary_membrane_gap",
    "seg_inject_merge", "seg_inject_split", "seg_label_changes", "holdout_threshold",
    "MAX_LABEL_PIXELS", "SPLIT_AXES",
]

#: 1 断面の画素数の上限(8192²)。EM の断面は 1250² 〜 4096² が普通で、それ以上は分けて回す。
MAX_LABEL_PIXELS = 2 ** 26
#: ``seg_inject_split`` の切り方。
SPLIT_AXES = ("row", "col")


# --------------------------------------------------------------------------- #
# 入口の検査                                                                    #
# --------------------------------------------------------------------------- #
def _labels(x: Any, op: str, name: str = "labels") -> np.ndarray:
    a = np.asarray(x)
    if a.ndim != 2 or a.size == 0:
        raise ValueError(f"{op}: {name} must be a non-empty 2-D label image, got shape {a.shape}")
    if a.dtype == bool or not np.issubdtype(a.dtype, np.integer):
        raise ValueError(f"{op}: {name} must have an integer dtype (one id per neuron), got {a.dtype}; "
                         "label a mask with blob_label first")
    if a.size > MAX_LABEL_PIXELS:
        raise ValueError(f"{op}: {name} has {a.size} pixels > MAX_LABEL_PIXELS={MAX_LABEL_PIXELS}")
    if int(a.min()) < 0:
        raise ValueError(f"{op}: {name} has negative ids (min={int(a.min())})")
    return a.astype(np.int64, copy=False)


def _image(x: Any, op: str, name: str, shape=None) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    if a.ndim != 2 or a.size == 0:
        raise ValueError(f"{op}: {name} must be a non-empty 2-D image, got shape {a.shape}")
    if shape is not None and a.shape != tuple(shape):
        raise ValueError(f"{op}: {name} shape {a.shape} must match labels shape {tuple(shape)}")
    if not np.isfinite(a).all():
        raise ValueError(f"{op}: {name} must be finite (NaN/Inf would be read as membrane)")
    return a


def _finite(x: Any, op: str, name: str, lo=None, hi=None) -> float:
    if isinstance(x, (bool, np.bool_, str)) or x is None:
        raise ValueError(f"{op}: {name} must be a number, got {x!r}")
    v = float(x)
    if not np.isfinite(v):
        raise ValueError(f"{op}: {name} must be finite, got {v}")
    if lo is not None and v < lo:
        raise ValueError(f"{op}: {name} must be >= {lo}, got {v}")
    if hi is not None and v > hi:
        raise ValueError(f"{op}: {name} must be <= {hi}, got {v}")
    return v


def _count(x: Any, op: str, name: str, lo: int = 0) -> int:
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer)):
        raise ValueError(f"{op}: {name} must be an integer, got {x!r}")
    v = int(x)
    if v < lo:
        raise ValueError(f"{op}: {name} must be >= {lo}, got {v}")
    return v


def _normalise(M: np.ndarray, normalize: bool) -> np.ndarray:
    """断面ごとの 99.5 percentile で割る(コントラスト差を吸収しないと、暗い断面では全部の境界が
    「膜が薄い」に見える)。負は 0 に切る。"""
    if not isinstance(normalize, (bool, np.bool_)):
        raise ValueError(f"normalize must be a bool, got {normalize!r}")
    M = np.maximum(M, 0.0)
    if not normalize:
        return M
    top = float(np.percentile(M, 99.5))
    return M / top if top > 0.0 else M


def _adjacent_pairs(L: np.ndarray, M: np.ndarray | None, ignore_zero: bool):
    """4 近傍で隣り合う異ラベル画素の (lo, hi) 対と、その境界の膜応答(両側の強い方)。"""
    pairs, vals = [], []
    for A, B, Ma, Mb in (
        (L[:, :-1], L[:, 1:], None if M is None else M[:, :-1], None if M is None else M[:, 1:]),
        (L[:-1, :], L[1:, :], None if M is None else M[:-1, :], None if M is None else M[1:, :]),
    ):
        d = A != B
        if ignore_zero:
            d &= (A != 0) & (B != 0)
        a, b = A[d], B[d]
        pairs.append(np.stack([np.minimum(a, b), np.maximum(a, b)], axis=1))
        if M is not None:
            vals.append(np.maximum(Ma[d], Mb[d]))
    P = np.concatenate(pairs, axis=0) if pairs else np.zeros((0, 2), np.int64)
    V = np.concatenate(vals, axis=0) if vals else None
    return P, V


# --------------------------------------------------------------------------- #
# 膜応答                                                                        #
# --------------------------------------------------------------------------- #
def seg_membrane_response(image, sigma: float = 1.5, normalize: bool = True) -> np.ndarray:
    """EM 断面の**暗い線**(細胞膜)の応答 [0, ∞)。ガウス平滑した Hessian の固有値 λ1 ≥ λ2 から
    ``max(λ1 − |λ2|, 0)`` (Steger の線検出の閉形式、σ² で尺度正規化)。

    暗い線の上では横断方向の 2 階微分が大きく正(λ1)、線に沿う方向は 0(λ2)なので λ1 − |λ2| が立つ。
    暗い**塊**(ミトコンドリア内部・シナプス小胞)は λ1 ≈ λ2 > 0 で打ち消し合って 0 に近い ―― 膜だけを
    拾う。``normalize=True`` で断面の 99.5 percentile を 1 にする(``seg_*`` の閾値はその尺度で書く)。
    scikit-image があるならレジストリの ``sk_frangi``(``fs.apply(img, "sk_frangi", a=0.5, b=0.5)``)も
    同じ席に使える(試作はそちらで AUC を測った)。

    Parameters
    ----------
    image : (H, W) float
        生 EM(明るい = 細胞質、暗い = 膜)。範囲は問わない(勾配の比だけを見る)。
    sigma : float
        平滑の σ [px]。膜の太さの半分程度(CREMI 4 nm/px なら 1.5〜2.5)。
    """
    op = "seg_membrane_response"
    img = _image(image, op, "image")
    s = _finite(sigma, op, "sigma", lo=0.3, hi=64.0)
    hyy = ndi.gaussian_filter(img, s, order=(2, 0))
    hxx = ndi.gaussian_filter(img, s, order=(0, 2))
    hxy = ndi.gaussian_filter(img, s, order=(1, 1))
    tr = 0.5 * (hxx + hyy)
    disc = np.sqrt(np.maximum(0.25 * (hxx - hyy) ** 2 + hxy ** 2, 0.0))
    lam1, lam2 = tr + disc, tr - disc
    resp = np.maximum(lam1 - np.abs(lam2), 0.0) * (s * s)
    return _normalise(resp, normalize)


# --------------------------------------------------------------------------- #
# 疑い                                                                          #
# --------------------------------------------------------------------------- #
def seg_membrane_chord_score(labels, membrane, tau: float = 0.2, band: int = 4, min_area: int = 1500,
                             min_segment: int = 20, normalize: bool = True, ignore_zero: bool = True,
                             max_points: int = 400, min_hole: int = 4) -> dict:
    """**融合の疑い**: ラベルの内部を横切る膜の「弦」の長さ / ラベルの径。ラベル(連結成分)ごとに 1 行。

    手順: 成分の内側(境界から ``band`` px より内)で膜応答 > ``tau`` の画素を 8 連結の成分にし、
    ``min_segment`` px 以上の膜成分ごとに、3 px 太らせて境界帯(``band`` < 距離 ≤ ``band`` + 3)に
    触れる画素の**最遠 2 点間距離**を弦長とする。score = max 弦長 / sqrt(面積)。境界の 2 か所を結ぶ膜
    (= 貼り付いた 2 細胞の境目)は score ≈ 1、境界に触れない断片は 0 か小さい。**穴を持つ膜成分**
    (``min_hole`` px 以上の穴 = 閉じた輪 = ミトコンドリア・小胞)は弦の候補から外す ―― 境界の 2 点に
    接する輪は弦と同じ「遠い 2 点」を持つので、穴の有無で先に分ける。輪が切れて弧になった膜は
    外せない(実データで AUC が 1 にならない主因)。

    CREMI sample A(512² 断面 12 枚、試作)で人工融合の成分 vs 他: AUC 0.83(tau 0.2)。
    列: ``label`` / ``component`` / ``area`` / ``score`` / ``chord_px`` / ``n_segments`` / ``cy`` / ``cx``
    (score 降順)。``min_area`` 未満の成分は数えない(小さな断片の弦は径と同程度で常に高く出る)。

    >>> table = seg_membrane_chord_score(labels, seg_membrane_response(raw))
    >>> table["label"][:5], table["score"][:5]          # 疑いの強い順
    """
    op = "seg_membrane_chord_score"
    L = _labels(labels, op)
    M = _normalise(_image(membrane, op, "membrane", L.shape), normalize)
    t = _finite(tau, op, "tau", lo=0.0)
    bd = _count(band, op, "band", lo=1)
    ma = _count(min_area, op, "min_area", lo=1)
    ms = _count(min_segment, op, "min_segment", lo=1)
    mp = _count(max_points, op, "max_points", lo=2)
    mh = _count(min_hole, op, "min_hole", lo=1)
    if not isinstance(ignore_zero, (bool, np.bool_)):
        raise ValueError(f"{op}: ignore_zero must be a bool, got {ignore_zero!r}")
    rows = []
    eight = np.ones((3, 3), bool)
    for lid, sl in enumerate(ndi.find_objects(L), start=1):
        if sl is None or (ignore_zero and lid == 0):
            continue
        sub = L[sl] == lid
        if int(sub.sum()) < ma:
            continue
        comps, n = ndi.label(sub)
        Msub = M[sl]
        for c in range(1, n + 1):
            m = comps == c
            area = int(m.sum())
            if area < ma:
                continue
            dist = ndi.distance_transform_edt(m)
            mem = (dist > bd) & (Msub > t)
            best, nseg = 0.0, 0
            if mem.any():
                mc, k = ndi.label(mem, structure=eight)
                sizes = np.bincount(mc.ravel(), minlength=k + 1)
                shell = m & (dist <= bd + 3)
                for j in np.nonzero(sizes[1:] >= ms)[0] + 1:
                    seg = mc == j
                    # 閉じた輪(穴を持つ膜成分 = ミトコンドリア・小胞)は弦ではない: 境界の 2 点に
                    # 接する輪は弦と同じ「遠い 2 点」を持つので、穴の有無で先に除く。境界帯にかかって
                    # 弧になった輪は除けない(境界の膜と繋がる弦を輪と区別できなくなるので、帯の外で
                    # 見る案は取らなかった)—— 実データで AUC が 1 にならない主因
                    if int(ndi.binary_fill_holes(seg).sum()) - int(seg.sum()) >= mh:
                        continue
                    touch = ndi.binary_dilation(seg, iterations=3) & shell
                    ys, xs = np.nonzero(touch)
                    if len(ys) < 2:
                        continue
                    nseg += 1
                    pts = np.column_stack([ys, xs]).astype(np.float64)
                    if len(pts) > mp:
                        pts = pts[np.linspace(0, len(pts) - 1, mp).astype(int)]
                    d = np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1)).max()
                    best = max(best, float(d))
            ys, xs = np.nonzero(m)
            rows.append((lid, c, area, best / np.sqrt(area), best, nseg,
                         float(ys.mean()) + sl[0].start, float(xs.mean()) + sl[1].start))
    if not rows:
        return {k: np.zeros(0, dt) for k, dt in (("label", np.int64), ("component", np.int64), ("area", np.int64),
                                                 ("score", np.float64), ("chord_px", np.float64),
                                                 ("n_segments", np.int64), ("cy", np.float64), ("cx", np.float64))}
    arr = np.array(rows, dtype=np.float64)
    order = np.argsort(-arr[:, 3], kind="stable")
    arr = arr[order]
    return {"label": arr[:, 0].astype(np.int64), "component": arr[:, 1].astype(np.int64),
            "area": arr[:, 2].astype(np.int64), "score": arr[:, 3], "chord_px": arr[:, 4],
            "n_segments": arr[:, 5].astype(np.int64), "cy": arr[:, 6], "cx": arr[:, 7]}


def seg_boundary_membrane_gap(labels, membrane, tau: float = 0.2, min_len: int = 60,
                              normalize: bool = True, ignore_zero: bool = True) -> dict:
    """**分断の疑い**: 隣接する 2 ラベルの境界画素のうち、膜応答が ``tau`` 未満の割合。隣接対ごとに 1 行。

    細胞の境目には必ず膜(暗い線)がある。膜が無いのにラベルが変わる境界は、1 細胞を 2 つに切った
    分断の跡(``seg_inject_split`` の直線はまさにこれ)。4 近傍で異ラベルが接する画素を数え、境界の膜応答は
    両側の強い方をとる。CREMI sample A の試作で人工分断 vs 他: **AUC 0.99**(tau 0.2、境界長 ≥ 60)。
    列: ``label_a`` / ``label_b``(a < b)/ ``length`` / ``gap_fraction`` / ``membrane_mean``(gap_fraction 降順)。
    ``min_len`` px 未満の短い境界は数えない(数画素の接触は膜の有無を言えない)。

    >>> table = seg_boundary_membrane_gap(labels, seg_membrane_response(raw))
    >>> table["label_a"][0], table["label_b"][0], table["gap_fraction"][0]   # いちばん怪しい対
    """
    op = "seg_boundary_membrane_gap"
    L = _labels(labels, op)
    M = _normalise(_image(membrane, op, "membrane", L.shape), normalize)
    t = _finite(tau, op, "tau", lo=0.0)
    ml = _count(min_len, op, "min_len", lo=1)
    if not isinstance(ignore_zero, (bool, np.bool_)):
        raise ValueError(f"{op}: ignore_zero must be a bool, got {ignore_zero!r}")
    P, V = _adjacent_pairs(L, M, ignore_zero)
    empty = {"label_a": np.zeros(0, np.int64), "label_b": np.zeros(0, np.int64), "length": np.zeros(0, np.int64),
             "gap_fraction": np.zeros(0), "membrane_mean": np.zeros(0)}
    if len(P) == 0:
        return empty
    K = int(L.max()) + 1
    key = P[:, 0] * K + P[:, 1]
    uniq, inv = np.unique(key, return_inverse=True)
    length = np.bincount(inv)
    gap = np.bincount(inv, weights=(V < t).astype(np.float64))
    msum = np.bincount(inv, weights=V)
    keep = length >= ml
    if not keep.any():
        return empty
    la, lb = uniq[keep] // K, uniq[keep] % K
    frac, mean = gap[keep] / length[keep], msum[keep] / length[keep]
    order = np.argsort(-frac, kind="stable")
    return {"label_a": la[order].astype(np.int64), "label_b": lb[order].astype(np.int64),
            "length": length[keep][order].astype(np.int64), "gap_fraction": frac[order],
            "membrane_mean": mean[order]}


# --------------------------------------------------------------------------- #
# 評価用の人工誤り                                                              #
# --------------------------------------------------------------------------- #
def seg_inject_merge(labels, n: int = 1, seed: int = 0, min_area: int = 3000, ignore_zero: bool = True) -> np.ndarray:
    """評価用に**融合**を仕込む: 隣接する大きなラベル対を ``n`` 組選び、片方の id をもう片方に書き換える。

    ``min_area`` px 以上のラベルだけを候補にし(小さな断片の融合は弦が短くて検出できず、評価が
    「仕込めない誤り」に引っ張られる)、乱数(``seed``)で対を選ぶ。同じラベルは 1 回しか使わない。
    ``n`` 組取れなければ ValueError(黙って少ない数で返すと AUC の分母が変わる)。仕込んだ対は
    ``seg_label_changes(labels, out)["merge_before"]`` で取り出せる。

    >>> merged = seg_inject_merge(labels, n=1, seed=3)
    >>> seg_label_changes(labels, merged)["merge_before"]     # 吸われた id
    """
    op = "seg_inject_merge"
    L = _labels(labels, op).copy()
    k = _count(n, op, "n", lo=1)
    sd = _count(seed, op, "seed", lo=0)
    ma = _count(min_area, op, "min_area", lo=1)
    if not isinstance(ignore_zero, (bool, np.bool_)):
        raise ValueError(f"{op}: ignore_zero must be a bool, got {ignore_zero!r}")
    sizes = np.bincount(L.ravel())
    P, _ = _adjacent_pairs(L, None, ignore_zero)
    P = np.unique(P, axis=0) if len(P) else P
    big = set(np.nonzero(sizes >= ma)[0].tolist())
    if ignore_zero:
        big.discard(0)
    adj: dict[int, list[int]] = {}
    for a, b in P.tolist():
        if a in big and b in big:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
    rng = np.random.default_rng(sd)
    order = rng.permutation(sorted(adj))
    used: set[int] = set()
    done = 0
    for a in order.tolist():
        if a in used:
            continue
        nb = [b for b in adj[a] if b not in used]
        if not nb:
            continue
        b = int(rng.choice(nb))
        L[L == b] = a
        used.update((int(a), b))
        done += 1
        if done == k:
            break
    if done < k:
        raise ValueError(f"{op}: only {done} of {n} merges possible (need adjacent label pairs with "
                         f">= min_area={ma} px each; lower min_area or n)")
    return L


def seg_inject_split(labels, n: int = 1, seed: int = 0, min_area: int = 4000, axis: str = "row",
                     ignore_zero: bool = True) -> np.ndarray:
    """評価用に**分断**を仕込む: 大きなラベルを ``n`` 個選び、画素の中央値の行(``axis="row"``)か
    列(``"col"``)で 2 つに切って、片側に新しい id(既存最大 + 1, +2, …)を付ける。

    切り口は直線 = 膜の無い境界で、``seg_boundary_membrane_gap`` が拾うべき形。両側が
    ``min_area / 4`` px 以上残るラベルだけ候補にする。``n`` 個取れなければ ValueError。
    仕込んだ対は ``seg_label_changes(labels, out)["split_before"]`` で取り出せる。

    >>> cut = seg_inject_split(labels, n=1, seed=0, axis="row")
    """
    op = "seg_inject_split"
    L = _labels(labels, op).copy()
    k = _count(n, op, "n", lo=1)
    sd = _count(seed, op, "seed", lo=0)
    ma = _count(min_area, op, "min_area", lo=4)
    if axis not in SPLIT_AXES:
        raise ValueError(f"{op}: axis must be one of {SPLIT_AXES}, got {axis!r}")
    if not isinstance(ignore_zero, (bool, np.bool_)):
        raise ValueError(f"{op}: ignore_zero must be a bool, got {ignore_zero!r}")
    sizes = np.bincount(L.ravel())
    cand = np.nonzero(sizes >= ma)[0]
    if ignore_zero:
        cand = cand[cand != 0]
    rng = np.random.default_rng(sd)
    coord = np.arange(L.shape[0])[:, None] if axis == "row" else np.arange(L.shape[1])[None, :]
    next_id = int(L.max()) + 1
    done = 0
    for a in rng.permutation(cand).tolist():
        mask = L == a
        vals = np.nonzero(mask)[0] if axis == "row" else np.nonzero(mask)[1]
        med = float(np.median(vals))
        half = mask & (np.broadcast_to(coord, L.shape) > med)
        if int(half.sum()) < ma // 4 or int(mask.sum() - half.sum()) < ma // 4:
            continue
        L[half] = next_id
        next_id += 1
        done += 1
        if done == k:
            break
    if done < k:
        raise ValueError(f"{op}: only {done} of {n} splits possible (need labels with >= min_area={ma} px "
                         f"that leave >= min_area/4 px on both sides)")
    return L


def seg_label_changes(before, after, min_pixels: int = 1, ignore_zero: bool = True) -> dict:
    """2 枚のラベル画像の差を**融合と分断の対**として返す(校正の前後、または仕込んだ誤りの答え合わせ)。

    ``before`` のラベル b と ``after`` のラベル a が同じ画素を ``min_pixels`` 以上共有する対を数え、
    * 融合 = after の 1 ラベルが before の 2 ラベル以上を覆う → ``merge_after`` / ``merge_before``(対ごとに 1 行。
      吸った側の id 自身も before の 1 つとして並ぶ)
    * 分断 = before の 1 ラベルが after の 2 ラベル以上に割れる → ``split_before`` / ``split_after``(同様に
      残った側の id も並ぶ)
    ``n_merged`` / ``n_split`` は誤りの数(after 側・before 側の id で数える)。id の一致は見ない
    (ラベルを振り直した 2 枚でも使える)。

    >>> ch = seg_label_changes(truth, seg_inject_merge(truth))
    >>> int(ch["n_merged"])
    1
    """
    op = "seg_label_changes"
    B = _labels(before, op, "before")
    A = _labels(after, op, "after")
    if A.shape != B.shape:
        raise ValueError(f"{op}: before {B.shape} and after {A.shape} must have the same shape")
    mp = _count(min_pixels, op, "min_pixels", lo=1)
    if not isinstance(ignore_zero, (bool, np.bool_)):
        raise ValueError(f"{op}: ignore_zero must be a bool, got {ignore_zero!r}")
    b, a = B.ravel(), A.ravel()
    if ignore_zero:
        keep = (b != 0) & (a != 0)
        b, a = b[keep], a[keep]
    K = int(A.max()) + 1
    key = b * K + a
    uniq, cnt = np.unique(key, return_counts=True)
    uniq = uniq[cnt >= mp]
    bb, aa = uniq // K, uniq % K
    # 融合: a ごとの b の数
    ua, ia = np.unique(aa, return_inverse=True)
    n_b_per_a = np.bincount(ia)
    merge_a = ua[n_b_per_a >= 2]
    m_rows = np.isin(aa, merge_a)
    # 分断: b ごとの a の数
    ub, ib = np.unique(bb, return_inverse=True)
    n_a_per_b = np.bincount(ib)
    split_b = ub[n_a_per_b >= 2]
    s_rows = np.isin(bb, split_b)
    return {"merge_after": aa[m_rows].astype(np.int64), "merge_before": bb[m_rows].astype(np.int64),
            "split_before": bb[s_rows].astype(np.int64), "split_after": aa[s_rows].astype(np.int64),
            "n_merged": int(len(merge_a)), "n_split": int(len(split_b))}


# --------------------------------------------------------------------------- #
# ホールドアウト評価                                                            #
# --------------------------------------------------------------------------- #
def _auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann–Whitney の AUC(同点は 0.5)。"""
    from scipy.stats import rankdata
    r = rankdata(np.concatenate([pos, neg]), method="average")
    n_p, n_n = len(pos), len(neg)
    return float((r[:n_p].sum() - n_p * (n_p + 1) / 2.0) / (n_p * n_n))


def holdout_threshold(train_pos, train_neg, test_pos, test_neg, target_fpr: float = 0.05) -> dict:
    """閾値を**訓練側で選び、評価は別の側で**測る(score が高いほど「疑わしい」)。

    ``tau`` = 訓練の負例(仕込んでいない成分・対)の偽陽性率が ``target_fpr`` 以下になる最小の閾値
    (負例スコアの上位 ``target_fpr`` 分位)。返すのは ``tau`` と、訓練・評価それぞれの AUC・TPR・FPR、件数。
    評価側の数字だけを主張に使う ―― 閾値を選んだ側で測った TPR は必ず楽観する(evolve の holdout 規律を
    op に切り出したもの)。AUC は Mann–Whitney(同点 0.5)。

    >>> r = holdout_threshold(tr_pos, tr_neg, te_pos, te_neg, target_fpr=0.05)
    >>> r["tau"], r["test_auc"], r["test_tpr"], r["test_fpr"]
    """
    op = "holdout_threshold"
    arrs = []
    for name, x in (("train_pos", train_pos), ("train_neg", train_neg), ("test_pos", test_pos), ("test_neg", test_neg)):
        a = np.asarray(x, dtype=np.float64).ravel()
        if a.size == 0:
            raise ValueError(f"{op}: {name} is empty (no AUC without both classes on both sides)")
        if not np.isfinite(a).all():
            raise ValueError(f"{op}: {name} must be finite")
        arrs.append(a)
    trp, trn, tep, ten = arrs
    f = _finite(target_fpr, op, "target_fpr", lo=0.0, hi=1.0)
    # 負例の上位 f 分位より上を陽性にする: tau = そのぶんだけ許した最小値
    neg_sorted = np.sort(trn)[::-1]
    allowed = int(np.floor(f * len(trn)))           # 訓練の負例のうち陽性と呼んでよい個数
    if allowed >= len(trn):                         # target_fpr = 1: 全部を陽性に
        tau = float(neg_sorted[-1])
    else:                                           # allowed 個より上、次の負例は陽性にしない
        tau = float(np.nextafter(neg_sorted[allowed], np.inf))
    return {"tau": tau,
            "train_auc": _auc(trp, trn), "test_auc": _auc(tep, ten),
            "train_tpr": float(np.mean(trp >= tau)), "train_fpr": float(np.mean(trn >= tau)),
            "test_tpr": float(np.mean(tep >= tau)), "test_fpr": float(np.mean(ten >= tau)),
            "n_train_pos": int(len(trp)), "n_train_neg": int(len(trn)),
            "n_test_pos": int(len(tep)), "n_test_neg": int(len(ten))}

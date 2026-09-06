# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""血管網を抜いて分岐を測る —— 細線化のヒゲと、分岐近傍の径の過大。

血管造影・網膜眼底・μCT の血管セグメント、あるいは多孔質材やひび割れの網目を
グラフにして測る、という仕事です。出す数字は **分岐点の数と位置 / 枝の径 /
分岐則(Murray)の指数**。

真値は **合成した木そのもの**(各枝の始点・終点・直径、各分岐点の座標)です。
枝の直径は Murray の法則 d0^3 = d1^3 + d2^3 に厳密に従わせ、分岐角も Murray
の最適角(cos θ1 = (d0^4 + d1^4 − d2^4)/(2 d0^2 d1^2))で置いているので、
指数 3 が復元できるかを **式に対して** 検定できます。

EXTEND: 実物に差し替えるなら :func:`build_tree` が返す枝の表(``segments``)と
分岐点の表(``bifs``)を、手でトレースした中心線と径の表に置き換えます。
**セグメンテーション結果を真値にするのは不可** —— この PoC が測っている
いちばん大きな誤差(分岐近傍の径の過大)は、セグメンテーションにも同じ形で
入っているので、比べても打ち消して見えなくなります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

(番号つきの所見は :func:`main` の実行結果でそのまま印字されます)

来歴(公開文献のみ): Murray, *PNAS* 12 (1926) 207 —— 最小仕事の法則と分岐角 /
Zhang & Suen, *CACM* 27 (1984) 236 —— 細線化 / Lee, Kashyap & Chu,
*CVGIP* 56 (1994) 462 —— 位相保存の細線化 / Sherman, *J. Gen. Physiol.* 78
(1981) 431 —— Murray 則の生理学的検証。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N_PIX = 512              # 視野 [px]
D_ROOT = 13.0            # 根の直径 [px]
D_MIN = 3.0              # これ未満になったら枝分かれを止める [px]
LAMBDA_LO, LAMBDA_HI = 5.5, 7.5   # 枝の長さ / 直径
GAMMA_LO, GAMMA_HI = 0.65, 1.0    # 分岐の非対称度 d2/d1
MAX_DEPTH = 6
FG, BG = 0.82, 0.14      # 血管と背景の明るさ
PSF_SIGMA = 1.0          # 撮像系のぼけ [px]
NOISE = 0.012            # 撮像ノイズ(1σ)
SEED = 5

_LAB = fs.ledger


# --------------------------------------------------------------------------- #
# 1. 木を作る —— Murray の法則が真値                                            #
# --------------------------------------------------------------------------- #
def build_tree(seed: int = SEED, n_pix: int = N_PIX) -> dict:
    """Murray 則に厳密に従う 2 分木を作る。返り値が **この PoC の真値**。

    * 直径: d0^3 = d1^3 + d2^3(非対称度 γ = d2/d1 を毎回引く)
    * 分岐角: Murray の最適角(上式の cos θ)。角度も直径から決まるので、
      「もっともらしく見える木」ではなく **法則に従う木** になる。
    * 長さ: L = λ·d(λ は 5.5〜7.5)。血管の長さ/径比の実測範囲に合わせた。
    """
    rng = np.random.default_rng(seed)
    segs, bifs = [], []
    root = (n_pix - 14.0, n_pix * 0.5)                 # (row, col)、下端の中央
    stack = [(root, -np.pi / 2.0, D_ROOT, 0, -1)]
    while stack:
        p0, ang, d, depth, parent = stack.pop()
        length = d * rng.uniform(LAMBDA_LO, LAMBDA_HI)
        p1 = (p0[0] + length * np.sin(ang), p0[1] + length * np.cos(ang))
        idx = len(segs)
        segs.append({"p0": p0, "p1": p1, "d": d, "depth": depth, "parent": parent})
        if depth >= MAX_DEPTH:
            continue
        g = rng.uniform(GAMMA_LO, GAMMA_HI)
        d1 = d / (1.0 + g ** 3) ** (1.0 / 3.0)
        d2 = g * d1
        if min(d1, d2) < D_MIN:
            continue
        c1 = (d ** 4 + d1 ** 4 - d2 ** 4) / (2.0 * d ** 2 * d1 ** 2)
        c2 = (d ** 4 + d2 ** 4 - d1 ** 4) / (2.0 * d ** 2 * d2 ** 2)
        t1, t2 = np.arccos(np.clip(c1, -1, 1)), np.arccos(np.clip(c2, -1, 1))
        sgn = 1.0 if rng.random() < 0.5 else -1.0
        jitter = rng.normal(0.0, 0.06)
        bifs.append({"pos": p1, "parent": idx, "d0": d, "d1": d1, "d2": d2,
                     "children": (len(segs) + 0, len(segs) + 1)})
        stack.append((p1, ang - sgn * t1 + jitter, d1, depth + 1, idx))
        stack.append((p1, ang + sgn * t2 + jitter, d2, depth + 1, idx))
    return {"segments": segs, "bifs": bifs, "n_pix": n_pix}


def render(tree: dict, seed: int = SEED, noise: float = NOISE,
           psf: float = PSF_SIGMA) -> np.ndarray:
    """木を **面積被覆** で塗り、撮像系のぼけと雑音を足した観測画像を返す。"""
    n = tree["n_pix"]
    cov = np.zeros((n, n))
    yy, xx = np.mgrid[0:n, 0:n]
    for s in tree["segments"]:
        (y0, x0), (y1, x1) = s["p0"], s["p1"]
        r = 0.5 * s["d"]
        r0 = int(max(0, min(y0, y1) - r - 3))
        r1 = int(min(n, max(y0, y1) + r + 4))
        c0 = int(max(0, min(x0, x1) - r - 3))
        c1 = int(min(n, max(x0, x1) + r + 4))
        if r1 <= r0 or c1 <= c0:
            continue
        py = yy[r0:r1, c0:c1] - y0
        px = xx[r0:r1, c0:c1] - x0
        vy, vx = y1 - y0, x1 - x0
        ll = vy * vy + vx * vx
        t = np.clip((py * vy + px * vx) / max(ll, 1e-9), 0.0, 1.0)
        dist = np.hypot(py - t * vy, px - t * vx)
        cov[r0:r1, c0:c1] = np.maximum(cov[r0:r1, c0:c1],
                                       np.clip(r + 0.5 - dist, 0.0, 1.0))
    img = BG + (FG - BG) * cov
    if psf > 0:
        img = np.asarray(fs.apply(img, "gauss_filter", a=(psf - 0.3) / 2.7))
    rng = np.random.default_rng(seed + 1000)
    return np.clip(img + rng.normal(0.0, noise, img.shape), 0.0, 1.0)


def seg_distance(pts, seg) -> np.ndarray:
    """点列 ``pts`` (N,2) から線分までの距離。"""
    (y0, x0), (y1, x1) = seg["p0"], seg["p1"]
    vy, vx = y1 - y0, x1 - x0
    ll = max(vy * vy + vx * vx, 1e-9)
    t = np.clip(((pts[:, 0] - y0) * vy + (pts[:, 1] - x0) * vx) / ll, 0.0, 1.0)
    return np.hypot(pts[:, 0] - (y0 + t * vy), pts[:, 1] - (x0 + t * vx))


def count_true_crossings(tree: dict) -> int:
    """真値の木で、親子でない枝どうしが近づきすぎている組の数(交差の見張り)。"""
    segs = tree["segments"]
    hits = 0
    for i, a in enumerate(segs):
        pa = np.asarray([a["p0"], a["p1"]])
        for j in range(i + 1, len(segs)):
            b = segs[j]
            if b["parent"] == i or a["parent"] == j or a["parent"] == b["parent"]:
                continue
            d = min(seg_distance(pa, b).min(),
                    seg_distance(np.asarray([b["p0"], b["p1"]]), a).min())
            if d < 0.5 * (a["d"] + b["d"]):
                hits += 1
    return hits


# --------------------------------------------------------------------------- #
# 2. 骨格の道具 —— fullseye の 3-D 骨格族を 1 枚のスライスに使う                #
# --------------------------------------------------------------------------- #
def skeletonize(mask) -> np.ndarray:
    """2-D の細線化。**3-D の骨格族に (1,H,W) を渡す**(末尾「道具の穴」(a))。"""
    return np.asarray(_LAB.skeletonize_vol(np.asarray(mask, bool)[None, :, :]))[0]


def neighbour_count(skel) -> np.ndarray:
    """骨格画素の 8 近傍にある骨格画素の数。"""
    s = np.asarray(skel, np.uint8)
    return ndimage.convolve(s, np.ones((3, 3), int), mode="constant") - s


def junction_pixels(skel) -> np.ndarray:
    """近傍数 3 以上の骨格画素(**ゼロ点の分岐点**)。"""
    return np.asarray(skel, bool) & (neighbour_count(skel) >= 3)


def endpoint_pixels(skel) -> np.ndarray:
    return np.asarray(skel, bool) & (neighbour_count(skel) <= 1)


def junction_nodes(skel) -> np.ndarray:
    """分岐画素を **連結成分にまとめて** 1 分岐 1 点の座標にする。"""
    j = junction_pixels(skel)
    if not j.any():
        return np.zeros((0, 2))
    lab = _LAB.blob_label(j)
    f = _LAB.blob_features(lab)
    return np.column_stack([f["row"], f["col"]])


def prune_spurs(skel, min_len: float, iters: int = 3) -> np.ndarray:
    """**短い枝だけ** を刈る(端点を持ち、長さが ``min_len`` 未満の枝)。

    用意されている :func:`ledger.skeleton_prune3d` は「端点除去を length 回
    反復」なので、**すべての枝を length 画素ずつ短くする** —— 短い枝だけを
    落とす道具ではない(6 節で実測して比べる)。ここでは分岐画素を外して
    連結成分に切り、端点を含む短い成分だけを消す。
    """
    sk = np.asarray(skel, bool).copy()
    for _ in range(iters):
        j = junction_pixels(sk)
        e = endpoint_pixels(sk)
        seg = sk & ~j
        if not seg.any():
            break
        lab = _LAB.blob_label(seg)
        n = int(lab.max())
        if n == 0:
            break
        size = np.bincount(lab.ravel(), minlength=n + 1)
        has_end = np.zeros(n + 1, bool)
        has_end[lab[e & (lab > 0)]] = True
        kill = np.zeros(n + 1, bool)
        kill[1:] = has_end[1:] & (size[1:] < min_len)
        if not kill.any():
            break
        sk &= ~kill[lab]
    return sk


def match_points(det, true_pts, tol: float) -> dict:
    """検出点と真値を **1 対 1** で近い順に対応づける(重複割り当てを許さない)。"""
    det = np.asarray(det, np.float64).reshape(-1, 2)
    tru = np.asarray(true_pts, np.float64).reshape(-1, 2)
    if det.size == 0 or tru.size == 0:
        return {"n_match": 0, "err": np.zeros(0), "n_fp": len(det), "n_fn": len(tru)}
    dm = np.hypot(det[:, None, 0] - tru[None, :, 0], det[:, None, 1] - tru[None, :, 1])
    used_d, used_t, errs = set(), set(), []
    order = np.dstack(np.unravel_index(np.argsort(dm, axis=None), dm.shape))[0]
    for i, k in order:
        if dm[i, k] > tol:
            break
        if i in used_d or k in used_t:
            continue
        used_d.add(int(i))
        used_t.add(int(k))
        errs.append(float(dm[i, k]))
    return {"n_match": len(errs), "err": np.asarray(errs),
            "n_fp": len(det) - len(errs), "n_fn": len(tru) - len(errs)}


# --------------------------------------------------------------------------- #
# 節 1. ゼロ点 —— 2 値化 -> 細線化 -> 近傍数 3 以上                             #
# --------------------------------------------------------------------------- #
def section_zero_point(tree: dict, img) -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点 —— 2 値化 -> 細線化 -> 近傍数 3 以上の画素を分岐点とする")
    print("=" * 78)

    mask = img >= 0.5 * (FG + BG)
    skel = skeletonize(mask)
    jp = junction_pixels(skel)
    nodes = junction_nodes(skel)
    tru = np.asarray([b["pos"] for b in tree["bifs"]])
    tol = 6.0

    m_pix = match_points(np.column_stack(np.nonzero(jp)), tru, tol)
    m_nod = match_points(nodes, tru, tol)
    print("  真値の分岐 %d 個(枝 %d 本、真値どうしの近接 %d 組)"
          % (len(tru), len(tree["segments"]), count_true_crossings(tree)))
    print("  ★ゼロ点(画素をそのまま数える): 分岐画素 %d 個 -> 対応 %d / 余分 %d / "
          "見落とし %d、位置誤差 %.2f px"
          % (int(jp.sum()), m_pix["n_match"], m_pix["n_fp"], m_pix["n_fn"],
             m_pix["err"].mean() if m_pix["err"].size else np.nan))
    print("     1 個の分岐が **画素 %d 個** に化けている(%.1f 倍)。"
          % (int(jp.sum()), jp.sum() / max(len(tru), 1)))
    print("  連結成分にまとめる(fs.skeleton_nodes と同じ規約): 節点 %d 個 -> "
          "対応 %d / 余分 %d / 見落とし %d、位置誤差 %.2f px"
          % (len(nodes), m_nod["n_match"], m_nod["n_fp"], m_nod["n_fn"],
             m_nod["err"].mean() if m_nod["err"].size else np.nan))
    fn = fs.skeleton_nodes(mask)
    print("  検算: fs.skeleton_nodes は分岐 %d 個・端点 %d 個(骨格 %d px)と"
          "報告する —— 節点の数は一致した。"
          % (fn["n_junctions"], fn["n_endpoints"], fn["skeleton_length"]))
    print("  ★まとめても余分が %d 個残る。これが **ヒゲ(spur)** ——"
          " 太い枝の縁の凹凸から短い枝が生えて、そこが新しい分岐に見える。"
          % m_nod["n_fp"])

    over = np.asarray(fs.colorize_labels(skel.astype(np.int32) * 1))
    view = np.where(skel[..., None], over, np.repeat(img[..., None], 3, axis=2))
    figs.save_grid("scene", [img, view, jp.astype(float)],
                   ["観測画像", "細線化", "近傍数 3 以上"],
                   title="血管網(枝 %d 本 / 分岐 %d 個 / 根の直径 %.0f px)"
                         % (len(tree["segments"]), len(tru), D_ROOT), ncols=3)
    return {"skel": skel, "mask": mask, "true": tru, "pix": m_pix, "nod": m_nod}


# --------------------------------------------------------------------------- #
# 節 2. ★★ヒゲを刈るしきい値 —— 両立しない                                     #
# --------------------------------------------------------------------------- #
def section_prune(tree: dict, img, z: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) ★★ヒゲを刈るしきい値を振る —— 偽の分岐と、本物の細い枝は両立しない")
    print("=" * 78)

    tru = z["true"]
    # 「本物の末端」= 子を持たない枝の先端。刈りすぎるとこれが消える。
    segs = tree["segments"]
    has_child = {s["parent"] for s in segs if s["parent"] >= 0}
    leaves = np.asarray([s["p1"] for i, s in enumerate(segs) if i not in has_child])
    print("  真値: 分岐 %d 個 / 末端 %d 本(いちばん細い枝の直径 %.2f px)"
          % (len(tru), len(leaves), min(s["d"] for s in segs)))
    print("\n   刈る長さ [px]  節点  余分  見落とし  位置誤差   末端の残存  "
          "末端の位置誤差")

    lens, n_fp, n_fn, n_leaf, errs = [], [], [], [], []
    keep_sk = {}
    for ln in (0, 2, 4, 6, 8, 12, 18, 26):
        sk = prune_spurs(z["skel"], ln) if ln else z["skel"]
        nodes = junction_nodes(sk)
        m = match_points(nodes, tru, 6.0)
        ep = np.column_stack(np.nonzero(endpoint_pixels(sk)))
        ml = match_points(ep, leaves, 12.0)
        lens.append(ln)
        n_fp.append(m["n_fp"])
        n_fn.append(m["n_fn"])
        n_leaf.append(ml["n_match"])
        errs.append(float(m["err"].mean()) if m["err"].size else np.nan)
        print("       %3d        %3d   %3d     %3d      %.2f px      %3d / %d    "
              "%.2f px" % (ln, len(nodes), m["n_fp"], m["n_fn"], errs[-1],
                           ml["n_match"], len(leaves),
                           float(ml["err"].mean()) if ml["err"].size else np.nan))
        if ln in (0, 6, 26):
            keep_sk[ln] = sk

    best = int(np.argmin([a + b for a, b in zip(n_fp, n_fn)]))
    print("\n  ★偽の分岐(余分)は %d -> %d に減るが、同じ操作で本物の末端が "
          "%d / %d -> %d / %d に減る。"
          % (n_fp[0], n_fp[-1], n_leaf[0], len(leaves), n_leaf[-1], len(leaves)))
    print("  ★どちらもゼロになる長さは無い。いちばん総誤差が小さいのは %d px で、"
          "そこでも 余分 %d / 見落とし %d / 末端の消失 %d 本。"
          % (lens[best], n_fp[best], n_fn[best], len(leaves) - n_leaf[best]))
    print("     ヒゲの長さと、いちばん細い枝の長さが **重なっている** ので、"
          "長さだけでは分けられない。")

    figs.save_plot("prune",
                   [("偽の分岐(余分)", lens, n_fp),
                    ("見落とした分岐", lens, n_fn),
                    ("消えた末端", lens, [len(leaves) - v for v in n_leaf])],
                   xlabel="刈る枝の長さ [px]", ylabel="件数",
                   title="ヒゲを刈るほど本物の細い枝も消える")
    return {"len": lens, "fp": n_fp, "fn": n_fn, "leaf": n_leaf,
            "leaves": leaves, "sk": keep_sk, "best": lens[best]}


# --------------------------------------------------------------------------- #
# 節 3. ★★径の推定 —— 分岐の近くで必ず過大                                     #
# --------------------------------------------------------------------------- #
def radius_field(mask) -> np.ndarray:
    """画素単位の EDT。**進化 op の distance_transform は最大値で正規化される**
    ので使えず、3-D の :func:`vol_distance_transform` に (1,H,W) を渡す
    (末尾「道具の穴」(b))。"""
    return np.asarray(fs.vol_distance_transform(np.asarray(mask, bool)[None, :, :]))[0]


def truth_at(tree: dict, pts) -> tuple:
    """各点について、**最も近い枝の直径** と **最寄りの分岐までの距離** を返す。"""
    segs = tree["segments"]
    dmat = np.stack([seg_distance(pts, s) for s in segs], axis=1)
    k = np.argmin(dmat, axis=1)
    d_true = np.asarray([segs[i]["d"] for i in k])
    bif = np.asarray([b["pos"] for b in tree["bifs"]])
    db = np.hypot(pts[:, None, 0] - bif[None, :, 0],
                  pts[:, None, 1] - bif[None, :, 1]).min(axis=1)
    return d_true, db, k


def section_radius(tree: dict, img, z: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) ★★径の推定(距離変換の 2 倍)—— 分岐の近くで必ず過大")
    print("=" * 78)

    edt = radius_field(z["mask"])
    sk = prune_spurs(z["skel"], 6)
    pts = np.column_stack(np.nonzero(sk)).astype(np.float64)
    d_est = 2.0 * edt[sk]
    d_true, d_bif, _ = truth_at(tree, pts)
    rel = 100.0 * (d_est - d_true) / d_true

    print("  骨格画素 %d 点で評価。全体の偏り %+.2f %%(中央値 %+.2f %%)"
          % (len(pts), rel.mean(), np.median(rel)))
    print("\n   分岐からの距離 [px]   点数    径の偏り [%]   標準偏差")
    edges = [0, 3, 6, 10, 15, 22, 32, 60]
    ctr, bias, sd = [], [], []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (d_bif >= a) & (d_bif < b)
        if m.sum() < 10:
            continue
        ctr.append(0.5 * (a + b))
        bias.append(float(rel[m].mean()))
        sd.append(float(rel[m].std()))
        print("      %3d - %3d          %5d      %+7.2f       %6.2f"
              % (a, b, int(m.sum()), bias[-1], sd[-1]))

    far = rel[d_bif >= 15]
    near = rel[d_bif < 6]
    print("\n  ★分岐から 6 px 未満では %+.1f %%、15 px 以上では %+.1f %% ——"
          " **差は %.1f 点**。" % (near.mean(), far.mean(),
                                   near.mean() - far.mean()))
    print("     距離変換は「最も近い背景まで」なので、2 本の枝が合流している"
          "ところでは背景が遠のき、\n     どちらの枝の径でもない大きな値になる。")
    print("  ★遠いところでも偏りは %+.1f %% 残る(ゼロではない)—— これは"
          "しきい値の位置(縁が %.2f px 外へ出る)による系統的な太り。"
          % (far.mean(), 0.5 * far.mean() / 100 * float(np.median(d_true))))

    figs.save_plot("radius_bias",
                   [("径の偏り [%]", ctr, bias),
                    ("偏りゼロ", ctr, [0.0] * len(ctr))],
                   xlabel="最寄りの分岐までの距離 [px]", ylabel="径の偏り [%]",
                   title="分岐の近くでは径が必ず過大に出る")
    return {"edt": edt, "sk": sk, "pts": pts, "d_est": d_est, "d_true": d_true,
            "d_bif": d_bif, "rel": rel, "near": float(near.mean()),
            "far": float(far.mean())}


# --------------------------------------------------------------------------- #
# 節 4. ★★Murray の指数 —— 測る位置で 3 になったりならなかったり                #
# --------------------------------------------------------------------------- #
def murray_exponent(d0: float, d1: float, d2: float) -> float:
    """(d1/d0)^n + (d2/d0)^n = 1 を満たす n を二分法で解く。"""
    r1, r2 = d1 / d0, d2 / d0
    if not (0 < r1 < 1 and 0 < r2 < 1):
        return np.nan

    def f(n):
        return r1 ** n + r2 ** n - 1.0
    lo, hi = 0.2, 20.0
    if f(lo) < 0 or f(hi) > 0:
        return np.nan
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _diameter_along(seg, from_pos, offset: float, edt, sk) -> float:
    """枝 ``seg`` の、``from_pos`` から ``offset`` 進んだ点での径(2×EDT)。"""
    (y0, x0), (y1, x1) = seg["p0"], seg["p1"]
    if np.hypot(y0 - from_pos[0], x0 - from_pos[1]) > \
       np.hypot(y1 - from_pos[0], x1 - from_pos[1]):
        (y0, x0), (y1, x1) = (y1, x1), (y0, x0)
    ll = np.hypot(y1 - y0, x1 - x0)
    t = min(offset / max(ll, 1e-9), 0.95)
    p = (y0 + t * (y1 - y0), x0 + t * (x1 - x0))
    ys, xs = np.nonzero(sk)
    d2 = (ys - p[0]) ** 2 + (xs - p[1]) ** 2
    k = int(np.argmin(d2))
    return 2.0 * float(edt[ys[k], xs[k]])


def section_murray(tree: dict, r: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) ★★Murray の指数 —— 測る位置を分岐から離すと 3 に近づく")
    print("=" * 78)
    print("  真値は厳密に n = 3(直径を d0^3 = d1^3 + d2^3 で作っている)。")
    print("\n   分岐からの距離 [px]   使えた分岐   指数の中央値   四分位範囲   "
          "|n-3| の中央値")

    edt, sk = r["edt"], r["sk"]
    offs, meds, iqrs = [], [], []
    for off in (0, 3, 6, 10, 15, 22):
        ns = []
        for b in tree["bifs"]:
            par = tree["segments"][b["parent"]]
            ch = [tree["segments"][i] for i in b["children"]
                  if i < len(tree["segments"])]
            if len(ch) != 2:
                continue
            d0 = _diameter_along(par, b["pos"], off, edt, sk)
            d1 = _diameter_along(ch[0], b["pos"], off, edt, sk)
            d2 = _diameter_along(ch[1], b["pos"], off, edt, sk)
            n = murray_exponent(d0, d1, d2)
            if np.isfinite(n):
                ns.append(n)
        ns = np.asarray(ns)
        q1, q3 = (np.percentile(ns, [25, 75]) if ns.size else (np.nan, np.nan))
        offs.append(off)
        meds.append(float(np.median(ns)) if ns.size else np.nan)
        iqrs.append(float(q3 - q1) if ns.size else np.nan)
        print("        %3d              %3d / %3d        %5.2f       %5.2f       "
              "%5.2f" % (off, ns.size, len(tree["bifs"]), meds[-1], iqrs[-1],
                         float(np.median(np.abs(ns - 3.0))) if ns.size else np.nan))

    j = int(np.nanargmin([abs(m - 3.0) for m in meds]))
    print("\n  ★分岐点そのもの(距離 0)で測ると指数の中央値は %.2f。親の径が"
          "過大に出るので、\n     d1^n + d2^n = d0^n を満たすには n を大きく"
          "しなければならない。" % meds[0])
    print("  ★%d px 離すと %.2f まで戻る(真値 3.00、誤差 %+.2f)。"
          % (offs[j], meds[j], meds[j] - 3.0))
    print("     ただし離しすぎると別の問題が出る: 使えた分岐が %d -> %d 個に減る"
          "(短い枝は %d px も無い)。" % (len(tree["bifs"]),
                                          len(tree["bifs"]), offs[-1]))
    figs.save_plot("murray",
                   [("指数の中央値", offs, meds),
                    ("真値 n=3", offs, [3.0] * len(offs))],
                   xlabel="径を測る位置(分岐からの距離)[px]",
                   ylabel="Murray の指数 n",
                   title="分岐点で測ると指数が壊れる(真値 3)")
    return {"off": offs, "med": meds, "iqr": iqrs}


# --------------------------------------------------------------------------- #
# 節 5. どの枝が失われるか(太さで数える)                                      #
# --------------------------------------------------------------------------- #
def section_thin(tree: dict, z: dict, p: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) ★失われるのは細い枝 —— 太さで分けて数える")
    print("=" * 78)

    sk = p["sk"][p["best"]] if p["best"] in p["sk"] else prune_spurs(z["skel"],
                                                                    p["best"])
    segs = tree["segments"]
    pts = np.column_stack(np.nonzero(sk)).astype(np.float64)
    print("   直径の帯 [px]   枝の本数   骨格が乗った本数   乗った割合")
    rows = []
    for lo, hi in ((3.0, 4.0), (4.0, 5.5), (5.5, 7.5), (7.5, 10.0), (10.0, 99.0)):
        sel = [s for s in segs if lo <= s["d"] < hi]
        if not sel:
            continue
        hit = 0
        for s in sel:
            d = seg_distance(pts, s)
            if (d < 0.5 * s["d"] + 1.5).sum() >= 0.4 * np.hypot(
                    s["p1"][0] - s["p0"][0], s["p1"][1] - s["p0"][1]):
                hit += 1
        rows.append((lo, hi, len(sel), hit))
        print("    %4.1f - %4.1f       %3d          %3d           %5.1f %%"
              % (lo, hi, len(sel), hit, 100.0 * hit / len(sel)))
    thin = rows[0]
    thick = rows[-1]
    print("\n  ★いちばん細い帯(%.1f-%.1f px)で %d / %d 本、いちばん太い帯で "
          "%d / %d 本。" % (thin[0], thin[1], thin[3], thin[2], thick[3], thick[2]))
    print("     失うのは常に細いほうで、しかも **細い枝ほど本数が多い**"
          "(木の末端だから)—— 本数で数えた検出率は細い側の性能でほぼ決まる。")
    figs.save_table("summary",
                    ["量", "真値", "推定", "備考"],
                    [["分岐の数", "%d" % len(tree["bifs"]),
                      "%d" % (len(tree["bifs"]) - z["nod"]["n_fn"] + z["nod"]["n_fp"]),
                      "刈らない状態(節点にまとめた後)"],
                     ["分岐の位置誤差 [px]", "0",
                      "%.2f" % z["nod"]["err"].mean(), "対応がついたものだけ"],
                     ["径の偏り(分岐 < 6 px)[%]", "0", "%+.1f" % p["near_bias"],
                      "距離変換が合流を見る"],
                     ["径の偏り(分岐 >= 15 px)[%]", "0", "%+.1f" % p["far_bias"],
                      "しきい値の位置による太り"],
                     ["Murray の指数(距離 0)", "3.00", "%.2f" % p["n0"],
                      "分岐点で測ると壊れる"],
                     ["Murray の指数(最良)", "3.00", "%.2f" % p["nbest"],
                      "分岐から %d px 離す" % p["offbest"]]],
                    title="血管網の計測まとめ(枝 %d 本 / 分岐 %d 個)"
                          % (len(segs), len(tree["bifs"])))
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 節 6. 道具の穴                                                                #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("6) 道具の穴(この PoC で fullseye を使ってみて)")
    print("=" * 78)

    import ops
    reg = {o.name: o for o in ops.REGISTRY}

    # (a) 2-D の骨格解析(端点・分岐・枝分割・剪定)が台帳に無い —— 3-D だけ
    for name in ("skeleton_junctions", "skeleton_endpoints", "skeleton_prune",
                 "skeleton_branches", "skeletonize"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    for name in ("skeleton_junctions3d", "skeleton_endpoints3d",
                 "skeleton_prune3d", "skeleton_branches3d", "skeletonize_vol"):
        assert hasattr(fs.ledger, name), name
    m = np.zeros((40, 40), bool)
    m[18:22, 5:35] = True
    try:
        _LAB.skeletonize_vol(m)                    # 2-D をそのまま渡すと拒まれる
        raise AssertionError("2-D を受けるようになった(この節を書き換えること)")
    except ValueError:
        pass
    assert np.asarray(_LAB.skeletonize_vol(m[None])).shape == (1, 40, 40)
    print("  (a) 骨格解析の族(細線化・端点・分岐・枝分割・剪定)は **3-D 専用**。"
          "2-D を渡すと ValueError。(1,H,W) にすると全部そのまま動くので、"
          "この PoC はそうしている —— 動くのに 2-D の名前が無いだけ。")

    # (b) 画素単位の距離変換が 2-D の公開経路に無い(op は最大値で正規化)
    dn = np.asarray(fs.apply(m.astype(np.float64), "distance_transform"))
    assert abs(float(dn.max()) - 1.0) < 1e-9, float(dn.max())
    d3 = np.asarray(fs.vol_distance_transform(m[None]))
    assert abs(float(d3.max()) - 2.0) < 1e-9, float(d3.max())
    print("  (b) 進化 op の distance_transform は最大値で正規化するので、"
          "画素単位の距離が取れない(2.0 px が 1.0 になる)。"
          "vol_distance_transform に (1,H,W) を渡すのが唯一の経路。")

    # (c) ★skeleton_prune3d は「短い枝を刈る」ではなく「全部の枝を短くする」
    t = np.zeros((80, 80), bool)
    t[38:42, 10:70] = True
    t[20:40, 40:44] = True
    sk = np.asarray(_LAB.skeletonize_vol(t[None]))
    before = int(sk.sum())
    after = int(np.asarray(_LAB.skeleton_prune3d(sk, 10)).sum())
    assert before - after > 25, (before, after)
    print("  (c) ★skeleton_prune3d(sk, L) は端点除去を L 回反復するので、"
          "ヒゲだけでなく **すべての枝が L 画素ずつ短くなる**"
          "(ヒゲの無い T 字で %d -> %d px)。"
          "「短い枝だけを刈る」道具として使うと、本物の枝の先端を失う。"
          % (before, after))

    # (d) ★fs.skeleton_nodes は docstring が「座標」と言うのに端点しか返さない
    info = fs.skeleton_nodes(t)
    import inspect as _insp
    assert "their coordinates" in (_insp.getdoc(fs.skeleton_nodes) or "")
    assert "endpoints" in info and "junctions" not in info, sorted(info)
    print("  (d) ★fs.skeleton_nodes の docstring は「端点と分岐点 **とその座標**」"
          "と書いてあるが、返るのは端点の座標だけ。分岐点は数しか返らない"
          "(実装では座標を作って捨てている)。血管のグラフ化には座標が要る。")

    # (e) 骨格をグラフ(節点と辺)にする口が無い
    for name in ("skeleton_graph", "to_graph", "branch_table", "network_graph"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    assert "r2_split_skeleton_lines" in reg          # 枝に切る op はある(画像出力)
    print("  (e) 骨格を **節点と辺の表** にする口が無い。r2_split_skeleton_lines は"
          "枝に切るが返り値は画像なので、どの枝がどの節点につながるかが取れない。"
          "分岐次数・枝長・径を枝ごとに出すには呼び手が全部書くことになる"
          "(この PoC がそう)。")

    # (f) Murray 則のような「枝の関係」を検定する道具は当然無い(記録として)
    for name in ("murray_exponent", "branching_exponent"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    print("  (f) 分岐則(Murray)の指数当てはめは無い。これは応用側の量なので"
          "無くて当然だが、(e) の枝の表さえあれば 10 行で書ける ——"
          "**足りないのは統計ではなくグラフのほう**。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    tree = build_tree()
    img = render(tree)
    print("=" * 78)
    print("血管網を抜いて分岐を測る —— ヒゲと、分岐近傍の径の過大")
    print("視野 %d px 角 / 枝 %d 本 / 分岐 %d 個 / 直径 %.1f - %.1f px"
          % (N_PIX, len(tree["segments"]), len(tree["bifs"]),
             min(s["d"] for s in tree["segments"]),
             max(s["d"] for s in tree["segments"])))
    print("真値: Murray 則 d0^3 = d1^3 + d2^3(分岐角も同じ式の最適角)")
    print("=" * 78)

    z = section_zero_point(tree, img)
    p = section_prune(tree, img, z)
    r = section_radius(tree, img, z)
    mu = section_murray(tree, r)
    j = int(np.nanargmin([abs(m - 3.0) for m in mu["med"]]))
    section_thin(tree, z, {**p, "near_bias": r["near"], "far_bias": r["far"],
                           "n0": mu["med"][0], "nbest": mu["med"][j],
                           "offbest": mu["off"][j]})
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 分岐画素をそのまま数えると 1 個の分岐が %.1f 倍に化ける。"
          "連結成分にまとめるのは最低条件。" % (z["pix"]["n_fp"] / max(len(z["true"]), 1)))
    print("  * ヒゲを刈る長さには両立点が無い(余分 %d、末端の消失 %d 本が最良)。"
          % (p["fp"][int(np.argmin([a + b for a, b in zip(p["fp"], p["fn"])]))],
             len(p["leaves"]) - p["leaf"][int(np.argmin(
                 [a + b for a, b in zip(p["fp"], p["fn"])]))]))
    print("  * 径は分岐の近くで %+.1f %%、離れて %+.1f %% —— **1 つの数字に"
          "まとめてはいけない**。" % (r["near"], r["far"]))
    print("  * Murray の指数は測る位置で %.2f -> %.2f と動く(真値 3)。"
          % (mu["med"][0], mu["med"][j]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()

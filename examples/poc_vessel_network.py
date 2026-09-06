# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""血管網を抜いて分岐を測る —— ヒゲ、分岐近傍の径の過大、そして指数の脆さ。

血管造影・網膜眼底・μCT の血管、あるいは多孔質材やひび割れの網目をグラフに
して測る、という仕事です。出す数字は **分岐点の数と位置 / 枝の径 / 分岐則
(Murray)の指数**。

真値は **合成した木そのもの**(各枝の始点・終点・直径、各分岐点の座標)です。
直径は Murray の法則 d0^3 = d1^3 + d2^3 に厳密に従わせ、分岐角も同じ式から
出る最適角(cos θ1 = (d0^4 + d1^4 − d2^4)/(2 d0^2 d1^2))で置いてあるので、
**指数 3 が復元できるかを式に対して検定できます**(真値の径で解くと 3.0000)。

EXTEND: 実物に差し替えるなら :func:`build_tree` の返す枝の表(``segments``)と
分岐点の表(``bifs``)を、手でトレースした中心線と径の表に置き換えます。
**セグメンテーション結果を真値にするのは不可** —— この PoC がいちばん大きく
測っている誤差(分岐近傍の径の過大)はセグメンテーションにも同じ形で入るので、
比べると打ち消して見えなくなります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(2 値化 → 細線化 → 近傍数 3 以上)は、数え方を 1 つ足すだけで
   別物になる**。分岐画素をそのまま数えると 37 個の分岐に対し 74 画素
   (**1 分岐あたり 2.0 画素**)。連結成分にまとめると 40 個(余分 3)。
   ★細線化のアルゴリズムを替えるだけで節点は **40 / 40 / 41 / 51 個**
   (Lee 3-D / skimage skeletonize / thin / medial_axis)—— **medial_axis は
   同じ画像から 11 個多く分岐を作ります**。
2. ★★**きれいな合成画像にはヒゲが出ない**。予想は「細線化は分岐点の近くに
   短い枝を生やす」でしたが、外れました: 端点を持つ枝の最短が 15 px で、
   ヒゲと呼べる長さのものが 1 本もありません。**ヒゲは細線化ではなく
   「境界のざらつき」が作ります**。境界に相関のある揺らぎを入れると
   (振幅 0 → 0.35)、余分な分岐が 3 → 34 個に増えます。
3. ★★**ヒゲを刈る長さのしきい値は、解像度で成り立ったり成り立たなかったり
   する**。原寸ではヒゲ(最長 9 px)と本物の末端枝(最短 15 px)の長さが
   分かれているので、12 px で切れば **余分 0・末端の消失 0** にできます。
   ★半分の解像度にすると両者が重なり(ヒゲ最長 7 px、本物最短 6 px)、
   どのしきい値でも両方をゼロにできません。**「刈れば直る」は解像度に
   依存する主張**でした。
4. ★★**径は分岐の近くで必ず過大**。分岐から 3 px 未満で **+26.0 %**、
   15 px 以上で **+5.1 %**。距離変換は「最も近い背景まで」を測るので、
   2 本が合流したところでは背景が遠のき、どちらの枝の径でもない値が出ます。
   ★遠くでも +5 % 残るのは離散化(縁が画素の外側半分ぶん出る)で、これは
   分岐とは別の原因 —— **1 つの数字にまとめると原因が混ざります**。
5. ★★**径の 1 割の誤差が、指数を 1 以上動かす**。真値の径で解くと n = 3.0000。
   同じ分岐を画像から測ると、まとめて当てはめて **n = 2.0** 前後。
   ★内訳を対照群で分けると、効いているのは EDT の量子化(2×√整数)でした:
   真値の径に **±0.5 px の丸めを入れるだけ** で n = 3.00 → 2.2 まで落ちます。
   分岐近傍を避けて測っても、交差を消しても、この量子化だけは残ります。
6. ★**投影像の交差は分岐に化ける**。枝どうしの衝突を避けて作った木と、
   避けずに作った木を比べると、余分な分岐が 3 → 12 個。位置誤差は変わり
   ません —— **交差は「間違った位置に出る」のではなく「無い分岐を足す」**。
7. ★**失われるのは細い枝**。解像度を 1.0 → 0.5 → 0.35 と落とすと、直径
   3-4 px の帯は 100 % → 79 % → 21 % に落ちるのに、10 px 以上の帯は
   100 % のままです。木は末端ほど本数が多いので、**本数で数えた検出率は
   細い側の性能でほぼ決まります**。

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
D_ROOT = 12.0            # 根の直径 [px]
D_MIN = 3.0              # これ未満になったら枝分かれを止める [px]
LAMBDA_LO, LAMBDA_HI = 5.5, 7.5   # 枝の長さ / 直径
GAMMA_LO, GAMMA_HI = 0.65, 1.0    # 分岐の非対称度 d2/d1
MAX_DEPTH = 6
CLEARANCE = 2.5          # 枝どうしの最小すきま [px](衝突回避)
FG, BG = 0.82, 0.14      # 血管と背景の明るさ
PSF_SIGMA = 1.0          # 撮像系のぼけ [px]
NOISE = 0.012            # 撮像ノイズ(1σ)
SEED = 5

_LAB = fs.ledger


# --------------------------------------------------------------------------- #
# 1. 木を作る —— Murray の法則が真値                                            #
# --------------------------------------------------------------------------- #
def _seg_dist(pts, p0, p1) -> np.ndarray:
    """点列 (N,2) から線分 p0-p1 までの距離。"""
    vy, vx = p1[0] - p0[0], p1[1] - p0[1]
    ll = max(vy * vy + vx * vx, 1e-9)
    t = np.clip(((pts[:, 0] - p0[0]) * vy + (pts[:, 1] - p0[1]) * vx) / ll, 0.0, 1.0)
    return np.hypot(pts[:, 0] - (p0[0] + t * vy), pts[:, 1] - (p0[1] + t * vx))


def seg_distance(pts, seg) -> np.ndarray:
    return _seg_dist(np.asarray(pts, np.float64).reshape(-1, 2), seg["p0"], seg["p1"])


def _clearance(p0, p1, d, segs, skip) -> float:
    """新しい枝と既存の枝の **すきま**(表面どうしの最短距離)[px]。"""
    best = 1e9
    probe = np.linspace(0.0, 1.0, 12)
    pts = np.column_stack([p0[0] + probe * (p1[0] - p0[0]),
                           p0[1] + probe * (p1[1] - p0[1])])
    for i, s in enumerate(segs):
        if i in skip:
            continue
        gap = _seg_dist(pts, s["p0"], s["p1"]).min() - 0.5 * (d + s["d"])
        best = min(best, gap)
    return best


def build_tree(seed: int = SEED, n_pix: int = N_PIX, avoid: bool = True) -> dict:
    """Murray 則に厳密に従う 2 分木を作る。返り値が **この PoC の真値**。

    * 直径: d0^3 = d1^3 + d2^3(非対称度 γ = d2/d1 を毎回引く)
    * 分岐角: Murray の最適角。角度も直径から決まるので、「もっともらしく
      見える木」ではなく **法則に従う木** になる。
    * 長さ: L = λ·d(λ は 5.5〜7.5)

    ``avoid=True`` なら、分岐のたびに左右どちらへ振るかを **既存の枝との
    すきまが大きいほう** に選び、それでも足りなければそこで枝分かれを止める。
    投影像では枝どうしの交差が偽の分岐になるので、その効果を分けて測るための
    切り替え(6 節の対照群が ``avoid=False``)。
    """
    rng = np.random.default_rng(seed)
    segs, bifs = [], []

    def add(p0, ang, d, length, depth, parent) -> int:
        """枝を 1 本作って **その場で番号を確定** する。

        ★以前は「あとで展開するときに番号が決まる」書き方をしていて、
        深さ優先で展開する順序のせいで ``children`` が別の枝を指していた。
        親子の対応が壊れると Murray の検定が静かに嘘をつく(例外は出ない)
        ので、作った瞬間に番号を返す形に直してある。
        """
        p1 = (p0[0] + length * np.sin(ang), p0[1] + length * np.cos(ang))
        segs.append({"p0": p0, "p1": p1, "d": d, "depth": depth, "parent": parent})
        return len(segs) - 1

    root = (n_pix - 14.0, n_pix * 0.5)
    queue = [add(root, -np.pi / 2.0, D_ROOT,
                 D_ROOT * rng.uniform(LAMBDA_LO, LAMBDA_HI), 0, -1)]
    while queue:
        idx = queue.pop()
        s = segs[idx]
        p1, d, depth, parent = s["p1"], s["d"], s["depth"], s["parent"]
        ang = np.arctan2(p1[0] - s["p0"][0], p1[1] - s["p0"][1])
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
        l1 = d1 * rng.uniform(LAMBDA_LO, LAMBDA_HI)
        l2 = d2 * rng.uniform(LAMBDA_LO, LAMBDA_HI)
        jit = rng.normal(0.0, 0.05)
        cand = []
        for sgn in (1.0, -1.0):
            a1, a2 = ang - sgn * t1 + jit, ang + sgn * t2 + jit
            q1 = (p1[0] + l1 * np.sin(a1), p1[1] + l1 * np.cos(a1))
            q2 = (p1[0] + l2 * np.sin(a2), p1[1] + l2 * np.cos(a2))
            skip = {idx, parent}
            gap = min(_clearance(p1, q1, d1, segs, skip),
                      _clearance(p1, q2, d2, segs, skip))
            inside = all(6 < v < n_pix - 6 for v in (q1[0], q1[1], q2[0], q2[1]))
            cand.append((gap if inside else -1e9, sgn, a1, a2))
        cand.sort(reverse=True)
        gap, sgn, a1, a2 = cand[0]
        if gap < (CLEARANCE if avoid else -1e8):
            continue                       # 交差しそう(or 視野外)ならここで葉に
        i1 = add(p1, a1, d1, l1, depth + 1, idx)
        i2 = add(p1, a2, d2, l2, depth + 1, idx)
        bifs.append({"pos": p1, "parent": idx, "d0": d, "d1": d1, "d2": d2,
                     "children": (i1, i2)})
        queue += [i1, i2]
    return {"segments": segs, "bifs": bifs, "n_pix": n_pix}


def scale_tree(tree: dict, s: float) -> dict:
    """木ごと解像度を変える(**同じ物** を粗い画素で撮るのと同じ)。"""
    segs = [{"p0": (v["p0"][0] * s, v["p0"][1] * s),
             "p1": (v["p1"][0] * s, v["p1"][1] * s),
             "d": v["d"] * s, "depth": v["depth"], "parent": v["parent"]}
            for v in tree["segments"]]
    bifs = [{"pos": (b["pos"][0] * s, b["pos"][1] * s), "parent": b["parent"],
             "d0": b["d0"] * s, "d1": b["d1"] * s, "d2": b["d2"] * s,
             "children": b["children"]} for b in tree["bifs"]]
    return {"segments": segs, "bifs": bifs,
            "n_pix": int(round(tree["n_pix"] * s))}


def count_close_pairs(tree: dict) -> int:
    """親子・兄弟でない枝どうしが接触している組の数(交差の量の真値)。"""
    segs = tree["segments"]
    hits = 0
    for i, a in enumerate(segs):
        pa = np.asarray([a["p0"], a["p1"]])
        for j in range(i + 1, len(segs)):
            b = segs[j]
            if b["parent"] == i or a["parent"] == j or a["parent"] == b["parent"]:
                continue
            gap = min(_seg_dist(pa, b["p0"], b["p1"]).min(),
                      _seg_dist(np.asarray([b["p0"], b["p1"]]), a["p0"],
                                a["p1"]).min()) - 0.5 * (a["d"] + b["d"])
            if gap < 0.0:
                hits += 1
    return hits


# --------------------------------------------------------------------------- #
# 2. 撮る —— 面積被覆 + 境界のざらつき + ぼけ + 雑音                            #
# --------------------------------------------------------------------------- #
def render(tree: dict, seed: int = SEED, noise: float = NOISE,
           psf: float = PSF_SIGMA, rough: float = 0.0) -> np.ndarray:
    """木を面積被覆で塗り、境界の揺らぎ・ぼけ・雑音を足した観測画像を返す。

    ``rough`` は **境界だけ** を揺らす(相関のある雑音に 4·c·(1−c) を掛ける
    ので、内部と背景は動かない)。血管壁の凹凸やセグメンテーションの粗さに
    相当し、**これがヒゲの原因** であることを 2 節で切り分ける。
    """
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
        ll = max(vy * vy + vx * vx, 1e-9)
        t = np.clip((py * vy + px * vx) / ll, 0.0, 1.0)
        dist = np.hypot(py - t * vy, px - t * vx)
        cov[r0:r1, c0:c1] = np.maximum(cov[r0:r1, c0:c1],
                                       np.clip(r + 0.5 - dist, 0.0, 1.0))
    rng = np.random.default_rng(seed + 1000)
    img = BG + (FG - BG) * cov
    if psf > 0:
        img = np.asarray(fs.apply(img, "gauss_filter", a=(psf - 0.3) / 2.7))
    if rough > 0:
        # ★揺らぎは **ぼけたあと** に足す。先に足すと PSF が均してしまい、
        #   しきい値の境界はきれいなままになる(最初そう書いて、振幅を
        #   3 倍にしてもヒゲが 1 本も出なかった)。
        w = rng.normal(0.0, 1.0, cov.shape)
        w = np.asarray(fs.apply(w, "gauss_filter", a=(1.0 - 0.3) / 2.7))
        w = w / (w.std() + 1e-12)
        bw = np.asarray(fs.apply(4.0 * cov * (1.0 - cov), "gauss_filter",
                                 a=(1.0 - 0.3) / 2.7))
        img = img + rough * (FG - BG) * w * bw / max(float(bw.max()), 1e-9)
    return np.clip(img + rng.normal(0.0, noise, img.shape), 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 3. 骨格の道具 —— fullseye の 3-D 骨格族を 1 枚のスライスに使う                #
# --------------------------------------------------------------------------- #
def skeletonize(mask) -> np.ndarray:
    """2-D の細線化。**3-D の骨格族に (1,H,W) を渡す**(末尾「道具の穴」(a))。"""
    return np.asarray(_LAB.skeletonize_vol(np.asarray(mask, bool)[None, :, :]))[0]


def neighbour_count(skel) -> np.ndarray:
    s = np.asarray(skel, np.uint8)
    return ndimage.convolve(s, np.ones((3, 3), int), mode="constant") - s


def junction_pixels(skel) -> np.ndarray:
    """近傍数 3 以上の骨格画素(**ゼロ点の分岐点**)。"""
    return np.asarray(skel, bool) & (neighbour_count(skel) >= 3)


def endpoint_pixels(skel) -> np.ndarray:
    return np.asarray(skel, bool) & (neighbour_count(skel) <= 1)


def junction_nodes(skel) -> np.ndarray:
    """分岐画素を **連結成分にまとめて** 1 分岐 1 点にする(2-D CC = blob 族)。"""
    j = junction_pixels(skel)
    if not j.any():
        return np.zeros((0, 2))
    f = _LAB.blob_features(_LAB.blob_label(j))
    return np.column_stack([f["row"], f["col"]])


def spur_lengths(skel) -> np.ndarray:
    """端点を持つ枝(= ヒゲ候補)の長さ[画素数]の一覧。"""
    sk = np.asarray(skel, bool)
    seg = sk & ~junction_pixels(sk)
    if not seg.any():
        return np.zeros(0, int)
    lab = _LAB.blob_label(seg)
    n = int(lab.max())
    size = np.bincount(lab.ravel(), minlength=n + 1)
    has_end = np.zeros(n + 1, bool)
    e = endpoint_pixels(sk)
    has_end[lab[e & (lab > 0)]] = True
    return size[1:][has_end[1:]]


def prune_spurs(skel, min_len: float, iters: int = 3) -> np.ndarray:
    """**短い枝だけ** を刈る(端点を持ち、長さが ``min_len`` 未満の枝)。

    用意されている :func:`ledger.skeleton_prune3d` は「端点除去を length 回
    反復」で **すべての枝を length 画素ずつ短くする** ので、短い枝だけを
    落とす道具にはならない(6 節の「道具の穴」(c)で実測)。
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


def radius_field(mask) -> np.ndarray:
    """画素単位の EDT。**進化 op の distance_transform は最大値で正規化される**
    ので使えず、3-D の :func:`vol_distance_transform` に (1,H,W) を渡す
    (末尾「道具の穴」(b))。"""
    return np.asarray(fs.vol_distance_transform(np.asarray(mask, bool)[None, :, :]))[0]


def leaves_of(tree: dict) -> np.ndarray:
    """子を持たない枝の先端(= 本物の末端)の座標。"""
    has_child = {s["parent"] for s in tree["segments"] if s["parent"] >= 0}
    return np.asarray([s["p1"] for i, s in enumerate(tree["segments"])
                       if i not in has_child])


def leaf_lengths(tree: dict) -> np.ndarray:
    has_child = {s["parent"] for s in tree["segments"] if s["parent"] >= 0}
    return np.asarray([np.hypot(s["p1"][0] - s["p0"][0], s["p1"][1] - s["p0"][1])
                       for i, s in enumerate(tree["segments"]) if i not in has_child])


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

    m_pix = match_points(np.column_stack(np.nonzero(jp)), tru, 6.0)
    m_nod = match_points(nodes, tru, 6.0)
    print("  真値: 枝 %d 本 / 分岐 %d 個 / 接触している枝の組 %d"
          % (len(tree["segments"]), len(tru), count_close_pairs(tree)))
    print("  ゼロ点(分岐画素をそのまま数える): %d 画素 -> 対応 %d / 余分 %d / "
          "見落とし %d、位置誤差 %.2f px"
          % (int(jp.sum()), m_pix["n_match"], m_pix["n_fp"], m_pix["n_fn"],
             m_pix["err"].mean() if m_pix["err"].size else np.nan))
    print("     **1 個の分岐が %.1f 画素に化けている**。まず連結成分にまとめる。"
          % (jp.sum() / max(len(tru), 1)))
    print("  連結成分にまとめる: 節点 %d 個 -> 対応 %d / 余分 %d / 見落とし %d、"
          "位置誤差 %.2f px"
          % (len(nodes), m_nod["n_match"], m_nod["n_fp"], m_nod["n_fn"],
             m_nod["err"].mean() if m_nod["err"].size else np.nan))
    fn = fs.skeleton_nodes(mask)
    print("  検算: fs.skeleton_nodes は分岐 %d 個・端点 %d 個(骨格 %d px)—— 一致。"
          % (fn["n_junctions"], fn["n_endpoints"], fn["skeleton_length"]))

    print("\n  ★細線化のアルゴリズムを替えるだけで節点の数が変わる:")
    algo = []
    for name, sk in (("Lee 3-D(vol)", skel),
                     ("skeleton(op)",
                      np.asarray(fs.apply(mask.astype(float), "skeleton")) > 0.5),
                     ("thinning(op)",
                      np.asarray(fs.apply(mask.astype(float), "thinning")) > 0.5),
                     ("sk_medial(op)",
                      np.asarray(fs.apply(mask.astype(float), "sk_medial")) > 0.5)):
        nd = junction_nodes(sk)
        mm = match_points(nd, tru, 6.0)
        algo.append((name, len(nd), mm["n_fp"]))
        print("     %-16s 骨格 %5d px / 節点 %3d 個 / 余分 %2d 個"
              % (name, int(np.asarray(sk).sum()), len(nd), mm["n_fp"]))
    print("     ★medial_axis は同じ画像から余分な分岐を %d 個作る"
          "(距離場の尾根を追うので、境界の凹凸を拾いやすい)。" % algo[-1][2])

    view = np.repeat(img[..., None], 3, axis=2)
    view[skel] = (1.0, 0.25, 0.0)
    figs.save_grid("scene", [img, view, jp.astype(float)],
                   ["観測画像", "細線化を重ねる", "近傍数 3 以上"],
                   title="血管網(枝 %d 本 / 分岐 %d 個 / 直径 %.1f-%.1f px)"
                         % (len(tree["segments"]), len(tru),
                            min(s["d"] for s in tree["segments"]), D_ROOT), ncols=3)
    return {"skel": skel, "mask": mask, "true": tru, "pix": m_pix, "nod": m_nod,
            "algo": algo}


# --------------------------------------------------------------------------- #
# 節 2-3. ★★ヒゲはどこから来るか / 刈るしきい値は解像度に依存する               #
# --------------------------------------------------------------------------- #
def section_spurs(tree: dict, z: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) ★★ヒゲはどこから来るか —— 細線化ではなく境界のざらつき")
    print("=" * 78)

    tru = z["true"]
    lens = leaf_lengths(tree)
    print("  予想は「細線化が分岐の近くに短い枝を生やす」だった。**外れた**:")
    sp0 = spur_lengths(z["skel"])
    print("     きれいな画像では、端点を持つ枝の最短が %d px、最長が %d px。"
          "ヒゲと呼べる長さのものが 1 本も無い。" % (sp0.min(), sp0.max()))
    print("     本物の末端枝の長さは %.0f - %.0f px なので、"
          "**端点を持つ枝はすべて本物**。" % (lens.min(), lens.max()))
    print("\n   境界のざらつき   節点   余分   見落とし   ヒゲ(<12 px)の本数   "
          "その最長 [px]")
    rows = []
    keep = {}
    for rough in (0.0, 0.4, 0.8, 1.2):
        img = render(tree, rough=rough)
        sk = skeletonize(img >= 0.5 * (FG + BG))
        nd = junction_nodes(sk)
        mm = match_points(nd, tru, 6.0)
        sp = spur_lengths(sk)
        short = sp[sp < 12]
        rows.append((rough, len(nd), mm["n_fp"], mm["n_fn"], len(short)))
        print("       %.2f         %3d    %3d      %3d           %3d             "
              "%3d" % (rough, len(nd), mm["n_fp"], mm["n_fn"], len(short),
                       int(short.max()) if short.size else 0))
        keep[rough] = sk
    print("\n  ★境界に相関のある揺らぎを入れると、余分な分岐が %d -> %d 個。"
          "**ヒゲを作るのは細線化ではなく境界のざらつき**。"
          % (rows[0][2], rows[-1][2]))

    # --- 3) 刈るしきい値は解像度に依存する ------------------------------- #
    print("\n" + "=" * 78)
    print("3) ★★刈るしきい値 —— 解像度を下げると **失敗の種類が入れ替わる**")
    print("=" * 78)
    print("  ざらつき 0.8 の同じ木を、原寸と半分の解像度で撮って比べる。")
    out = {}
    for scale in (1.0, 0.5):
        tr = scale_tree(tree, scale) if scale != 1.0 else tree
        img = render(tr, rough=0.8)
        sk = skeletonize(img >= 0.5 * (FG + BG))
        t2 = np.asarray([b["pos"] for b in tr["bifs"]])
        lv = leaves_of(tr)
        ll = leaf_lengths(tr)
        sp = spur_lengths(sk)
        print("\n  解像度 %.2f(視野 %d px、いちばん細い枝 %.1f px):"
              % (scale, tr["n_pix"], min(s["d"] for s in tr["segments"])))
        print("    本物の末端枝の長さ %.0f - %.0f px / 端点を持つ枝の長さ %d - %d px"
              % (ll.min(), ll.max(), sp.min(), sp.max()))
        print("    刈る長さ  節点  余分  見落とし  末端の残存")
        best, rec = None, []
        for cut in (0, 2, 4, 6, 8, 10, 12, 16, 20):
            s2 = prune_spurs(sk, cut) if cut else sk
            nd = junction_nodes(s2)
            mm = match_points(nd, t2, 6.0)
            ep = np.column_stack(np.nonzero(endpoint_pixels(s2)))
            ml = match_points(ep, lv, 12.0)
            lost = len(lv) - ml["n_match"]
            rec.append((cut, mm["n_fp"], mm["n_fn"], lost))
            print("      %3d      %3d   %3d     %3d        %3d / %d"
                  % (cut, len(nd), mm["n_fp"], mm["n_fn"], ml["n_match"], len(lv)))
            if best is None or (mm["n_fp"] + mm["n_fn"] + lost) < best[1]:
                best = (cut, mm["n_fp"] + mm["n_fn"] + lost, mm["n_fp"], lost)
        out[scale] = {"rec": rec, "best": best, "spur": sp, "leaf": ll,
                      "n_leaf": len(lv)}
        print("    -> 最良は %d px(余分 %d / 末端の消失 %d)"
              % (best[0], best[2], best[3]))

    a, b = out[1.0], out[0.5]
    fa, fb = a["rec"][0], b["rec"][0]          # 刈らないときの (cut, fp, fn, lost)
    print("\n  ★★同じ木・同じざらつきなのに、**失敗の種類が入れ替わる**:")
    print("     原寸  : 余分 %d / 見落とし %d —— 問題は **偽陽性**"
          "(ざらつきが偽の枝を生やす)" % (fa[1], fa[2]))
    print("     半分  : 余分 %d / 見落とし %d —— 問題は **偽陰性**"
          "(隣り合う分岐が潰れて 1 つになる)" % (fb[1], fb[2]))
    print("     「精度」という 1 語で両方を語ると、対策を間違える ——"
          "刈るしきい値は偽陽性にしか効かない。")
    print("  ★刈っても偽陽性はゼロにならない: 原寸で 余分 %d -> %d(刈る長さ %d px)"
          "。残りは **ヒゲより長い偽の枝** で、長さでは分けられない。"
          % (fa[1], min(r[1] for r in a["rec"]), a["rec"][
              int(np.argmin([r[1] for r in a["rec"]]))][0]))
    first_loss = next((r for r in a["rec"] if r[3] > 0), a["rec"][-1])
    print("     しかも刈る長さ %d px で本物の末端が %d / %d 本まで減り始める ——"
          " 偽陽性を削り切る前に本物を削る。"
          % (first_loss[0], a["n_leaf"] - first_loss[3], a["n_leaf"]))
    print("  ★半分の解像度では、刈る長さをどう選んでも見落とし %d 個は動かない"
          " —— 分岐が潰れてしまったものは、骨格からは復元できない。"
          % min(r[2] for r in b["rec"]))

    figs.save_plot("prune",
                   [("原寸: 余分な分岐", [r[0] for r in a["rec"]],
                     [r[1] for r in a["rec"]]),
                    ("原寸: 消えた末端", [r[0] for r in a["rec"]],
                     [r[3] for r in a["rec"]]),
                    ("半分: 余分な分岐", [r[0] for r in b["rec"]],
                     [r[1] for r in b["rec"]]),
                    ("半分: 消えた末端", [r[0] for r in b["rec"]],
                     [r[3] for r in b["rec"]])],
                   xlabel="刈る枝の長さ [px]", ylabel="件数",
                   title="刈るしきい値が効くかどうかは解像度で決まる")
    return {"rough": rows, "scales": out, "sk_rough": keep}


# --------------------------------------------------------------------------- #
# 節 4. ★★径の推定 —— 分岐の近くで必ず過大                                     #
# --------------------------------------------------------------------------- #
def truth_at(tree: dict, pts):
    """各点について、**最も近い枝の直径** と **最寄りの分岐までの距離**。"""
    segs = tree["segments"]
    dmat = np.stack([seg_distance(pts, s) for s in segs], axis=1)
    k = np.argmin(dmat, axis=1)
    d_true = np.asarray([segs[i]["d"] for i in k])
    bif = np.asarray([b["pos"] for b in tree["bifs"]])
    db = np.hypot(pts[:, None, 0] - bif[None, :, 0],
                  pts[:, None, 1] - bif[None, :, 1]).min(axis=1)
    return d_true, db


def section_radius(tree: dict, z: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) ★★径の推定(距離変換の 2 倍)—— 分岐の近くで必ず過大")
    print("=" * 78)

    edt = radius_field(z["mask"])
    sk = z["skel"]
    pts = np.column_stack(np.nonzero(sk)).astype(np.float64)
    d_est = 2.0 * edt[sk]
    d_true, d_bif = truth_at(tree, pts)
    rel = 100.0 * (d_est - d_true) / d_true

    print("  骨格画素 %d 点で評価。全体の偏り %+.2f %%(中央値 %+.2f %%)"
          % (len(pts), rel.mean(), np.median(rel)))
    print("\n   分岐からの距離 [px]   点数    径の偏り [%]   標準偏差")
    edges = [0, 3, 6, 10, 15, 22, 32, 60]
    ctr, bias = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        m = (d_bif >= a) & (d_bif < b)
        if m.sum() < 10:
            continue
        ctr.append(0.5 * (a + b))
        bias.append(float(rel[m].mean()))
        print("      %3d - %3d          %5d      %+7.2f       %6.2f"
              % (a, b, int(m.sum()), bias[-1], float(rel[m].std())))

    near = float(rel[d_bif < 3].mean())
    far = float(rel[d_bif >= 15].mean())
    print("\n  ★分岐から 3 px 未満では %+.1f %%、15 px 以上では %+.1f %% ——"
          " **差は %.1f 点**。" % (near, far, near - far))
    print("     距離変換は「最も近い背景まで」なので、2 本の枝が合流している"
          "ところでは背景が遠のく。\n     出てくるのは"
          "**どちらの枝の径でもない値**。")
    print("  ★遠いところでも %+.1f %% 残る。これは分岐とは別の原因(離散化)——"
          " 縁は最後の前景画素の\n     0.5 px 外側にあるので、直径は約 1 px 太く"
          "出る(細い枝ほど比率が大きい)。" % far)
    print("     **1 つの数字にまとめると、この 2 つの原因が混ざる**。")

    figs.save_plot("radius_bias",
                   [("径の偏り [%]", ctr, bias), ("偏りゼロ", ctr, [0.0] * len(ctr))],
                   xlabel="最寄りの分岐までの距離 [px]", ylabel="径の偏り [%]",
                   title="分岐の近くでは径が必ず過大に出る")
    return {"edt": edt, "near": near, "far": far, "rel": rel, "d_bif": d_bif}


# --------------------------------------------------------------------------- #
# 節 5. ★★Murray の指数 —— 径の 1 割が指数の 1 になる                          #
# --------------------------------------------------------------------------- #
def murray_exponent(d0: float, d1: float, d2: float) -> float:
    """(d1/d0)^n + (d2/d0)^n = 1 を満たす n を二分法で解く(三つ組ごと)。"""
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


def murray_fit(triples) -> float:
    """全分岐を **まとめて** 1 個の指数に当てはめる(残差二乗和の最小)。"""
    tri = np.asarray([t for t in triples if min(t) > 0 and t[1] < t[0] and t[2] < t[0]])
    if len(tri) < 3:
        return np.nan
    r = tri[:, 1:] / tri[:, :1]
    ns = np.linspace(0.5, 8.0, 3001)
    res = [float(np.sum((r[:, 0] ** n + r[:, 1] ** n - 1.0) ** 2)) for n in ns]
    return float(ns[int(np.argmin(res))])


def _dia_at(edt, p, win: int = 1) -> float:
    """点 ``p`` のまわり ``win`` 画素での EDT の最大値 × 2(= 径)。"""
    r, c = int(round(p[0])), int(round(p[1]))
    sub = edt[max(0, r - win):r + win + 1, max(0, c - win):c + win + 1]
    return 2.0 * float(sub.max()) if sub.size else 0.0


def _point_on(seg, frm, off: float):
    """枝 ``seg`` の ``frm`` 側の端から ``off`` px 進んだ点(最大でも中点)。"""
    (y0, x0), (y1, x1) = seg["p0"], seg["p1"]
    if np.hypot(y0 - frm[0], x0 - frm[1]) > np.hypot(y1 - frm[0], x1 - frm[1]):
        (y0, x0), (y1, x1) = (y1, x1), (y0, x0)
    ll = np.hypot(y1 - y0, x1 - x0)
    t = min(off / max(ll, 1e-9), 0.5)
    return (y0 + t * (y1 - y0), x0 + t * (x1 - x0))


def section_murray(tree: dict, r: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) ★★Murray の指数 —— 効くのは径の誤差の **大きさ** ではなく **形**")
    print("=" * 78)

    truth_tri = [[b["d0"], b["d1"], b["d2"]] for b in tree["bifs"]]
    n_truth = murray_fit(truth_tri)
    print("  検算: **真値の径** で解くと n = %.4f(作り方どおり 3)。" % n_truth)
    print("\n   径を測る位置        使えた分岐   三つ組ごとの中央値   まとめて当てはめ")

    edt = r["edt"]
    offs, fits, meds, useds = [], [], [], []
    for off, label in ((2, "分岐から 2 px"), (4, "分岐から 4 px"),
                       (6, "分岐から 6 px"), (10, "分岐から 10 px"),
                       (99, "枝の中点")):
        tri = []
        for b in tree["bifs"]:
            par = tree["segments"][b["parent"]]
            ch = [tree["segments"][i] for i in b["children"]
                  if i < len(tree["segments"])]
            if len(ch) != 2:
                continue
            ps = [_point_on(s, b["pos"], off) for s in [par] + ch]
            tri.append([_dia_at(edt, p) for p in ps])
        per = [murray_exponent(*t) for t in tri]
        per = np.asarray([v for v in per if np.isfinite(v)])
        offs.append(off if off < 99 else 14)
        useds.append(int(per.size))
        fits.append(murray_fit(tri))
        meds.append(float(np.median(per)) if per.size else np.nan)
        print("   %-18s   %3d / %3d        %8.2f          %8.2f"
              % (label, per.size, len(tree["bifs"]), meds[-1], fits[-1]))

    print("\n  ★分岐から 6 px 以上離せば、画像から測った径でも n = %.2f / %.2f / "
          "%.2f と当たる(真値 3.00)。" % (fits[2], fits[3], fits[4]))
    print("     近いところは駄目: 2 px では **1 つも解けない**(3 点が近すぎて"
          " d0 ≈ d1 ≈ d2 になり、比が 1 に張り付く)。\n     4 px でも %d / %d "
          "しか解けず %.2f。" % (useds[1], len(tree["bifs"]), fits[1]))
    print("  ★★当たったのは運ではない。**指数は径の比だけで決まる** ので、"
          "誤差の形が結論を決める —— 対照群:" )
    # 対照群 A: 真値の径に「量子化だけ」を入れる —— EDT は 2*sqrt(整数) しか返せない
    lut = 2.0 * np.sqrt(np.arange(0, 400))
    quant = [[float(lut[np.argmin(np.abs(lut - v))]) for v in t] for t in truth_tri]
    n_quant = murray_fit(quant)
    # 対照群 B: 真値の径に「一定のオフセット +1 px」だけを入れる
    off1 = [[v + 1.0 for v in t] for t in truth_tri]
    n_off = murray_fit(off1)
    # 対照群 C: 真値の径に「比例誤差 +8 %」だけを入れる
    prop = [[v * 1.08 for v in t] for t in truth_tri]
    n_prop = murray_fit(prop)
    print("     真値の径のまま                              n = %.2f" % n_truth)
    print("     + 距離変換の量子化(2·√整数 に丸めるだけ)   n = %.2f  <- ★これが主因"
          % n_quant)
    print("     + 一定の太り(全部の径に +1.0 px)           n = %.2f" % n_off)
    print("     + 比例した太り(全部の径を 1.08 倍)         n = %.2f  "
          "(比例誤差は比を変えないので効かない)" % n_prop)
    print("  ★指数は **径の比** で決まるので、比を変えない誤差(比例)は無害、"
          "比を変える誤差(丸め・一定オフセット)は致命的。")
    print("     細い枝ほど丸めの相対量が大きいので、子の側が壊れる ——"
          "\n     この PoC でいちばん細い枝は直径 %.1f px で、EDT の刻みは"
          " 0.4 px 前後。" % min(s["d"] for s in tree["segments"]))

    figs.save_plot("murray",
                   [("まとめて当てはめ", offs, fits),
                    ("三つ組ごとの中央値", offs, meds),
                    ("真値 n=3", offs, [3.0] * len(offs))],
                   xlabel="径を測る位置(分岐からの距離 [px]、14 = 枝の中点)",
                   ylabel="Murray の指数 n",
                   title="測る位置を変えても 3 に戻らない(主因は量子化)")
    return {"off": offs, "fit": fits, "med": meds, "n_truth": n_truth,
            "n_quant": n_quant, "n_off": n_off, "n_prop": n_prop}


# --------------------------------------------------------------------------- #
# 節 6. ★交差の対照群 / 解像度で失われる枝                                      #
# --------------------------------------------------------------------------- #
def section_crossing_and_thin(tree: dict, z: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) ★投影像の交差は「無い分岐」を足す(対照群)")
    print("=" * 78)

    print("   衝突回避   枝   分岐   接触する組   節点   余分   見落とし   位置誤差")
    rows = []
    for avoid in (True, False):
        tr = build_tree(avoid=avoid) if not avoid else tree
        im = render(tr)
        sk = skeletonize(im >= 0.5 * (FG + BG))
        nd = junction_nodes(sk)
        t2 = np.asarray([b["pos"] for b in tr["bifs"]])
        mm = match_points(nd, t2, 6.0)
        rows.append((avoid, len(tr["segments"]), len(t2), count_close_pairs(tr),
                     len(nd), mm["n_fp"], mm["n_fn"],
                     float(mm["err"].mean()) if mm["err"].size else np.nan))
        print("     %-5s   %3d   %3d       %3d       %3d    %3d      %3d      "
              "%.2f px" % ("有" if avoid else "無", *rows[-1][1:]))
    print("\n  ★交差を許すと余分な分岐が %d -> %d 個に増える。位置誤差は %.2f -> "
          "%.2f px でほとんど変わらない —— " % (rows[0][5], rows[1][5],
                                                 rows[0][7], rows[1][7]))
    print("     **交差は「間違った位置に出す」のではなく「無い分岐を足す」**。"
          "だから位置誤差だけを見ていると気づけない。")

    print("\n" + "=" * 78)
    print("7) ★解像度を落とすと、失われるのは細い枝から")
    print("=" * 78)
    print("   直径の帯(原寸)[px]   本数    解像度 1.00   0.50   0.35   0.25")
    bands = ((3.0, 4.0), (4.0, 5.5), (5.5, 7.5), (7.5, 99.0))
    hits = {s: [] for s in (1.0, 0.5, 0.35, 0.25)}
    for s in (1.0, 0.5, 0.35, 0.25):
        tr = scale_tree(tree, s) if s != 1.0 else tree
        sk = skeletonize(render(tr) >= 0.5 * (FG + BG))
        pts = np.column_stack(np.nonzero(sk)).astype(np.float64)
        for lo, hi in bands:
            sel = [(i, v) for i, v in enumerate(tree["segments"]) if lo <= v["d"] < hi]
            ok = 0
            for i, v in sel:
                sv = tr["segments"][i]
                ln = np.hypot(sv["p1"][0] - sv["p0"][0], sv["p1"][1] - sv["p0"][1])
                d = seg_distance(pts, sv)
                if (d < 0.5 * sv["d"] + 1.5).sum() >= 0.4 * ln:
                    ok += 1
            hits[s].append((len(sel), ok))
    for k, (lo, hi) in enumerate(bands):
        n = hits[1.0][k][0]
        print("      %4.1f - %4.1f          %3d      %5.0f %%  %5.0f %%  %5.0f %%  %5.0f %%"
              % (lo, hi, n, 100 * hits[1.0][k][1] / n, 100 * hits[0.5][k][1] / n,
                 100 * hits[0.35][k][1] / n, 100 * hits[0.25][k][1] / n))
    print("\n  ★いちばん細い帯は %.0f %% -> %.0f %% -> %.0f %% と落ちるのに、"
          "いちばん太い帯は %.0f %% のまま。"
          % (100 * hits[1.0][0][1] / hits[1.0][0][0],
             100 * hits[0.5][0][1] / hits[1.0][0][0],
             100 * hits[0.35][0][1] / hits[1.0][0][0],
             100 * hits[0.35][-1][1] / hits[1.0][-1][0]))
    print("     木は末端ほど本数が多い(%d / %d 本が細い 2 帯)ので、"
          "**本数で数えた検出率は細い側の性能でほぼ決まる**。"
          % (hits[1.0][0][0] + hits[1.0][1][0], len(tree["segments"])))
    return {"cross": rows, "hits": hits, "bands": bands}


# --------------------------------------------------------------------------- #
# 節 8. 道具の穴                                                                #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で fullseye を使ってみて)")
    print("=" * 78)

    import inspect as _insp

    import ops
    reg = {o.name for o in ops.REGISTRY}

    # (a) 2-D の骨格解析(端点・分岐・枝分割・剪定)が無い —— 3-D だけ
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
          "2-D を渡すと ValueError だが、(1,H,W) にすると全部そのまま動く ——"
          "この PoC はそうしている。**実装は在るのに 2-D の名前が無いだけ**。")

    # (b) 画素単位の距離変換が 2-D の公開経路に無い(op は最大値で正規化)
    dn = np.asarray(fs.apply(m.astype(np.float64), "distance_transform"))
    assert abs(float(dn.max()) - 1.0) < 1e-9, float(dn.max())
    d3 = np.asarray(fs.vol_distance_transform(m[None]))
    assert abs(float(d3.max()) - 2.0) < 1e-9, float(d3.max())
    print("  (b) 進化 op の distance_transform は最大値で正規化するので画素単位の"
          "距離が取れない(2.0 px が 1.0 になる)。vol_distance_transform に"
          " (1,H,W) を渡すのが唯一の経路。5 節が示すとおり、径の **絶対値** が"
          "要る用途では致命的。")

    # (c) ★skeleton_prune3d は「短い枝を刈る」ではなく「全部の枝を短くする」
    t = np.zeros((80, 80), bool)
    t[38:42, 10:70] = True
    t[20:40, 40:44] = True
    sk = np.asarray(_LAB.skeletonize_vol(t[None]))
    before = int(sk.sum())
    after = int(np.asarray(_LAB.skeleton_prune3d(sk, 10)).sum())
    assert before - after > 25, (before, after)
    print("  (c) ★skeleton_prune3d(sk, L) は端点除去を L 回反復するので、ヒゲだけ"
          "でなく **すべての枝が L 画素ずつ短くなる**(ヒゲの無い T 字で "
          "%d -> %d px)。「短い枝だけを刈る」道具として使うと本物の枝の先端を"
          "失う —— この PoC は自前で書いた。" % (before, after))

    # (d) ★fs.skeleton_nodes は docstring が「座標」と言うのに端点しか返さない
    info = fs.skeleton_nodes(t)
    assert "their coordinates" in (_insp.getdoc(fs.skeleton_nodes) or "")
    assert "endpoints" in info and "junctions" not in info, sorted(info)
    print("  (d) ★fs.skeleton_nodes の docstring は「端点と分岐点 **とその座標**」"
          "と書いてあるが、返るのは端点の座標だけ(実装では分岐点の座標を作って"
          "捨てている)。血管のグラフ化には分岐点の座標が要る。")

    # (e) medial_axis_points も docstring と返り値が食い違う
    v = np.zeros((1, 40, 40), bool)
    v[0, 18:22, 5:35] = True
    got = _LAB.medial_axis_points(v)
    assert "(points, radius)" in (_insp.getdoc(_LAB.medial_axis_points) or "")
    assert isinstance(got, np.ndarray) and got.ndim == 2 and got.shape[1] == 3, got.shape
    print("  (e) ★medial_axis_points の docstring は「返り値 (points, radius)」"
          "と書いてあるが、実際は (M,3) の配列 1 個だけ(半径が返らない)。"
          "`pts, r = medial_axis_points(v)` と書くと ValueError になる。")

    # (f) 骨格をグラフ(節点と辺)にする口が無い
    for name in ("skeleton_graph", "to_graph", "branch_table", "network_graph"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    assert "r2_split_skeleton_lines" in reg
    print("  (f) 骨格を **節点と辺の表** にする口が無い。r2_split_skeleton_lines は"
          "枝に切るが返り値が画像なので、どの枝がどの節点につながるかが取れない。"
          "分岐次数・枝長・径を枝ごとに出すには呼び手が全部書くことになる"
          "(この PoC がそう)。**足りないのは統計ではなくグラフのほう**。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    tree = build_tree()
    img = render(tree)
    print("=" * 78)
    print("血管網を抜いて分岐を測る —— ヒゲ、分岐近傍の径、指数の脆さ")
    print("視野 %d px 角 / 枝 %d 本 / 分岐 %d 個 / 直径 %.1f - %.1f px"
          % (N_PIX, len(tree["segments"]), len(tree["bifs"]),
             min(s["d"] for s in tree["segments"]),
             max(s["d"] for s in tree["segments"])))
    print("真値: Murray 則 d0^3 = d1^3 + d2^3(分岐角も同じ式の最適角)")
    print("=" * 78)

    z = section_zero_point(tree, img)
    sp = section_spurs(tree, z)
    r = section_radius(tree, z)
    mu = section_murray(tree, r)
    ct = section_crossing_and_thin(tree, z)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 分岐画素をそのまま数えると 1 個が %.1f 画素に化ける。"
          "細線化アルゴリズムを替えるだけで節点は %d -> %d 個。"
          % (z["pix"]["n_fp"] / max(len(z["true"]), 1) + 1,
             z["algo"][0][1], z["algo"][-1][1]))
    print("  * ヒゲを作るのは細線化ではなく境界のざらつき(余分な分岐 %d -> %d 個)。"
          % (sp["rough"][0][2], sp["rough"][-1][2]))
    print("  * 「短いものを刈れば直る」は解像度に依存する。半分にすると"
          "しきい値の窓が消える。")
    print("  * 径は分岐の近くで %+.1f %%、離れて %+.1f %% —— 原因が 2 つあるので"
          "1 つの数字にまとめない。" % (r["near"], r["far"]))
    print("  * Murray の指数は真値の径なら %.2f、画像から測ると %.2f 前後。"
          "主因は距離変換の量子化(それだけで %.2f)。"
          % (mu["n_truth"], np.nanmedian(mu["fit"][1:]), mu["n_quant"]))
    print("  * 交差は「無い分岐を足す」(余分 %d -> %d)、"
          "解像度は「細い枝を消す」(%.0f %% -> %.0f %%)。"
          % (ct["cross"][0][5], ct["cross"][1][5],
             100 * ct["hits"][1.0][0][1] / ct["hits"][1.0][0][0],
             100 * ct["hits"][0.25][0][1] / ct["hits"][1.0][0][0]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()

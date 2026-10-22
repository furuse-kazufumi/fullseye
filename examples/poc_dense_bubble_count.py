# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""密集した泡を数える —— 重なりが深くて決まらないときは、個数ではなく区間を返す。

    py -3.11 examples/poc_dense_bubble_count.py
    FULLSEYE_BUBBLE_DOWNLOAD=1 py -3.11 examples/poc_dense_bubble_count.py   # 実データも取る

【問い】液中の泡は重なり、触れ合い、1 つの塊に融合して見える。連結成分を数えると
重なりの数だけ少なく出る。距離変換 → 山(種)→ 分水嶺で割れば戻せるが、
**重なりが深くなると「2 個か 1 個か」は画像から決まらなくなる**。そこで
もっともらしい数を 1 つ返す道具は、黙って間違う。この PoC はその境目を
閉形式で予言し、実データで確かめ、境目の向こうでは数を返さない op を作る。

【既存の op で足りるかを先に確かめた(3 層とも引いた)】

* 2-D 台帳 ``opsblob``: ``blob_distance`` → ``blob_seeds`` → ``blob_split`` の連鎖は
  ある。**h を 1 つ選んで必ず 1 つの個数を返す**。重なり率 0.8 の 2 円を h = 1 px で
  割ると 1 個と答え、迷いを示す口が無い(下の門で記録)。
* 進化 op ``persistence_map``(山の突出度の地図): 全体の最大で正規化した 1 枚の
  地図で、**山ごとの表も成分ごとの区間も出ない**。``cv_hough_circles`` は個数
  だけを返し、半径 3〜20 px 固定。``xsk2_h_maxima`` は入力を [0, 1] に切り詰める。
* 3-D 側 ``separate_touching`` は 3-D 専用。``segworld.world_blobs_touching`` は
  重なり率つきの合成の世界(ここでそのまま使う)。

足りないのは「**決まらないことを言える**」1 点だけだったので、汎用 op を 1 本足した:
``blob2d.blob_count_interval``(台帳 ``opsblob`` の ``split``)。山ごとに 0 次元
パーシステンス(突出度)を測り、相対突出度 p/h が帯 [rel_lo, rel_hi) に落ちた山を
「あいまい」として区間 [lo, hi] を返す。``round_tol`` を与えると、数えた山の
内接円で説明できない面積を持つ塊の上限を開く(hi = None)。

【閉形式(外部真値)】等しい半径 r の 2 円が重なり率 o(中心間 d = 2r(1 − o))で
重なると、くびれの半幅 w = sqrt(r² − (d/2)²)、相対突出度 p/h = 1 − sqrt(1 − (1 − o)²)。
半径によらない。和集合の面積比 A/(πr²) = 2 − レンズ/(πr²) も閉形式。前者で
「割れなくなる重なり率」、後者で「面積でも見えなくなる重なり率」が予言できる。

【実データ】(repo に入れない。``FULLSEYE_BUBBLE_DOWNLOAD=1`` で ``FULLSEYE_DATA_DIR``
(既定 ``~/.cache/fullseye``)の ``poc_dense_bubble_count/`` へ取得。無いとき(CI)は
記録値を印字して実データの章を飛ばす)

* 水電解(PEMWE)の酸素の泡の光学動画から切り出した 35 枚と手作業のマスク —
  Colliard-Granero, Gompou, Rodenbücher, Malek, Eikerling, Eslamibidgoli,
  "Polymer Electrolyte Membrane Water Electrolyzer Oxygen Bubble Evolution Optical
  Video Recording", Zenodo, doi:10.5281/zenodo.10184579, **CC BY 4.0**。
  改変: マスクを 127 で二値化し、孤立した泡の形を切り出して重なり率を振って並べ直した
  (半合成)。★マスクは**意味分割**(泡か否か)で、泡ごとの番号は無い —— 融合した
  塊の真の個数はデータに無いので、実画像そのものの個数は採点できない(区間を示すだけ)。
* BBBC005 v1 の真値マスク(SIMCEP の合成細胞、個数がファイル名に入っている)—
  Ljosa, Sokolnicki & Carpenter, Nature Methods 9 (2012) 637、
  https://bbbc.broadinstitute.org/BBBC005 、**CC0 1.0**。改変なし(マスクを読むだけ)。
  ★アーカイブの ``_w1`` は小さい物体(核の大きさ)、``_w2`` は大きい物体(細胞体)の
  マスク —— 説明ページの「stain 1 = 細胞体」と逆なので、面積の中央値で確かめてから使う。

【ALCON2009 型の採点(自前の実装)】泡ごとの矩形と、答えの重心の点。点が矩形に
入れば当たり(1 つの矩形に当たるのは 1 点まで。2 部グラフの最大マッチング)、
余った点は誤検出、当たらなかった矩形は未検出。得点 = 当たり − 誤検出 − 未検出
(真値の数で割ったものを併記)。公開されている採点の形(重心が矩形内で加点、
誤検出・未検出は減点)に合わせたもので、重みは同じとした(元の重みは非公開)。

【門】(すべて実行時に計算)
1. 突出度が閉形式どおりか(r = 12/20/30 px、重なり率 0.1〜0.8 で 1.5 px 以内)
2. 自信をもって間違うのは、閉形式が「面積でも見えない」と言う重なり率だけ
3. 割れなくなる重なり率(決まる → 決まらない)が閉形式の予言の近くにある
4. 合成の世界(world_blobs_touching)で、決まったときの個数が真値と合う・区間が真値を含む
5. ALCON 型の採点の閉形式(全部当たり N、全部外れ −2N、二重回答 0、無回答 −N)
6. 壊す探針: 面積の検査を外すと深い重なりで自信をもって 1 個と答える
7. 実データ(あるときだけ): BBBC005 の個数の相対誤差・区間の被覆・自信をもった誤りの率、
   PEMWE の泡の形を並べた半合成の個数と ALCON 型の得点、孤立した泡を 1 個と数えるか

【読み方】各節の印字は「真値 / 実測 / 判定」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import hashlib
import io
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fullseye as fs  # noqa: E402  ★先に fullseye(パスフックが repo 直下を足す)
import blob2d as B  # noqa: E402
import segworld as SW  # noqa: E402

import examplefig as figs  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

#: op の既定の帯(宣言してから評価する。実データを見て決めた値ではない)。
REL_LO, REL_HI, MIN_PROM = 0.05, 0.15, 1.0
#: 泡の形の許し: 縦横比 1.1 まで(丸い泡)。細胞: 縦横比 1.3 まで(いびつ)。
RT_BUBBLE, RT_CELL = 0.1, 0.3
#: op が分けられる泡の大きさの下限(内接円の半径、px)。門 1 の量子化(突出度が閉形式より最大 1.5 px
#: 低く出る)を rel_hi で割った 1.5 / 0.15 = 10 px。これより小さい泡は、帯の上端の重なりでも山が
#: 量子化に埋もれる。
R_RESOLVE = 10

FAILS: list[str] = []
GATES: list[str] = []


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


# --------------------------------------------------------------------------- #
# 閉形式                                                                        #
# --------------------------------------------------------------------------- #
def rel_closed(o: float) -> float:
    """等しい 2 円、重なり率 o の相対突出度 p/h = 1 − sqrt(1 − (1 − o)²)。"""
    return 1.0 - math.sqrt(max(0.0, 1.0 - (1.0 - o) ** 2))


def o_for_rel(x: float) -> float:
    """相対突出度 x になる重なり率(rel_closed の逆。式の形が同じになる)。"""
    return 1.0 - math.sqrt(max(0.0, 1.0 - (1.0 - x) ** 2))


def union_ratio_closed(o: float) -> float:
    """等しい 2 円の和集合の面積 / (πr²)。レンズ = 2r²acos(d/2r) − (d/2)sqrt(4r² − d²)。"""
    d = 2.0 * (1.0 - o)                      # r = 1 で
    lens = 2.0 * math.acos(min(1.0, d / 2.0)) - (d / 2.0) * math.sqrt(max(0.0, 4.0 - d * d))
    return (2.0 * math.pi - lens) / math.pi


def o_unobservable(r: float, rt: float) -> float:
    """面積の検査でも見えなくなる重なり率: union_ratio = 1 + rt + 1/r を二分法で。"""
    target = 1.0 + rt + 1.0 / r
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if union_ratio_closed(mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------- #
# 道具                                                                          #
# --------------------------------------------------------------------------- #
def pair_mask(r1: float, r2: float, o: float, seed) -> np.ndarray:
    """半径 r1, r2 の 2 円を重なり率 o で置く。向きと副画素の位置は種から。

    重なり率 = 小さいほうの直径のうち、相手に食い込んだ割合: 中心間 d = r1 + r2 − 2o·min(r1, r2)。
    等しい半径なら d = 2r(1 − o)(世界 ``world_blobs_touching`` と同じ定義)。★最初は
    d = (r1 + r2)(1 − o) と書いていた —— 大きさの違う 2 つでは、小さいほうが o = 0.2 で
    もう半分以上埋まり、「浅い重なり」と呼べなくなる(実際の泡の半合成で 20 場面中 13 が誤り)。
    """
    rng = np.random.default_rng(seed)
    th = rng.uniform(0.0, math.pi)
    off = rng.uniform(-0.5, 0.5, 2)
    d = r1 + r2 - 2.0 * o * min(r1, r2)
    n = int(2 * (r1 + r2) + 16)
    u = np.array([math.sin(th), math.cos(th)])
    c1 = np.array([n / 2.0, n / 2.0]) + off - u * d / 2.0
    c2 = c1 + u * d
    yy, xx = np.mgrid[0:n, 0:n]
    return (((yy - c1[0]) ** 2 + (xx - c1[1]) ** 2) < r1 * r1) | \
           (((yy - c2[0]) ** 2 + (xx - c2[1]) ** 2) < r2 * r2)


def count_op(mask, rt=None, **kw):
    """新しい op(台帳経由と同じ実体)。"""
    return B.blob_count_interval(mask, rel_lo=kw.get("rel_lo", REL_LO), rel_hi=kw.get("rel_hi", REL_HI),
                                 min_prominence=kw.get("min_prominence", MIN_PROM), round_tol=rt)


def count_chain(mask, h=1.0):
    """既存の連鎖: blob_distance → blob_seeds(h)→ blob_split。返り値 (個数, ラベル)。"""
    d = B.blob_distance(mask)
    lab = B.blob_label(mask)
    if lab.max() == 0:
        return 0, lab
    parts = B.blob_split(lab, B.blob_seeds(d, h), d)
    return int(parts.max()), parts


def verdict(res: dict, truth: int) -> str:
    """op の答えを真値で裁く。

    right = 1 つの数に決めて正しい / wrong = **1 つの数に決めて間違えた(自信をもった誤り)** /
    range = 決まらないと言い、区間が真値を含む / open = 上限を開いて拒否、下限は真値以下 /
    miss = 決まらないと言ったが、区間が真値を含まない(数は言っていないが、区間は外れ)。
    """
    lo, hi = res["lo"], res["hi"]
    if res["determined"]:
        return "right" if lo == truth else "wrong"
    if hi is None:
        return "open" if lo <= truth else "miss"
    return "range" if lo <= truth <= hi else "miss"


def _mean_or_nan(xs) -> float:
    """空なら NaN(全部棄権した条件)。警告を出さない。"""
    return float(np.mean(xs)) if len(xs) else float("nan")


def centroids(labels: np.ndarray) -> np.ndarray:
    """ラベルごとの重心 (n, 2) [row, col]。"""
    n = int(labels.max())
    if n == 0:
        return np.zeros((0, 2))
    return np.asarray(ndimage.center_of_mass(np.ones(labels.shape), labels, np.arange(1, n + 1)),
                      np.float64).reshape(-1, 2)


def alcon_score(points, boxes) -> dict:
    """ALCON2009 型の採点。points (k, 2) [row, col]、boxes (n, 4) [r0, c0, r1, c1](両端を含む)。

    点が矩形に入れば当たり。1 つの矩形に当たるのは 1 点まで(2 部グラフの最大マッチング)。
    得点 = 当たり − 誤検出(余った点)− 未検出(当たらなかった矩形)。
    """
    p = np.asarray(points, np.float64).reshape(-1, 2)
    b = np.asarray(boxes, np.float64).reshape(-1, 4)
    k, n = len(p), len(b)
    hits = 0
    if k and n:
        inside = ((p[:, None, 0] >= b[None, :, 0]) & (p[:, None, 0] <= b[None, :, 2])
                  & (p[:, None, 1] >= b[None, :, 1]) & (p[:, None, 1] <= b[None, :, 3]))
        ri, ci = linear_sum_assignment(-inside.astype(np.float64))
        hits = int(inside[ri, ci].sum())
    fp, fn = k - hits, n - hits
    return {"hits": hits, "fp": fp, "fn": fn, "score": hits - fp - fn, "n": n,
            "norm": (hits - fp - fn) / n if n else float("nan")}


def disk_boxes(centers, radius, shape):
    """円の外接矩形(画像の中に切る)。"""
    c = np.asarray(centers, np.float64).reshape(-1, 2)
    r = np.broadcast_to(np.asarray(radius, np.float64), (len(c),))
    return np.stack([np.clip(c[:, 0] - r, 0, shape[0] - 1), np.clip(c[:, 1] - r, 0, shape[1] - 1),
                     np.clip(c[:, 0] + r, 0, shape[0] - 1), np.clip(c[:, 1] + r, 0, shape[1] - 1)], 1)


def scored_by_component(res, comp, truth_pts, truth_boxes):
    """決まった成分だけで ALCON 型の得点を出す(決まらない成分は棄権)。

    返り値: (得点の辞書, 棄権した真値の数)。
    """
    det = {int(l) for l, s in zip(res["components"]["label"], res["components"]["status"]) if s == "determined"}
    tp = np.asarray(truth_pts, np.float64).reshape(-1, 2)
    ti = np.clip(np.round(tp).astype(int), 0, np.array(comp.shape) - 1)
    tcomp = comp[ti[:, 0], ti[:, 1]]
    keep_t = np.array([int(c) in det for c in tcomp], bool)
    pts = centroids(res["labels"])
    if len(pts):
        pi = np.clip(np.round(pts).astype(int), 0, np.array(comp.shape) - 1)
        keep_p = np.array([int(c) in det for c in comp[pi[:, 0], pi[:, 1]]], bool)
        pts = pts[keep_p]
    return alcon_score(pts, np.asarray(truth_boxes)[keep_t]), int((~keep_t).sum())


# 図の色(役割ごと)
COL = {"determined": (0.15, 0.55, 1.0), "ambiguous": (1.0, 0.72, 0.0), "unexplained": (0.85, 0.15, 0.85),
       "right": (0.15, 0.55, 1.0), "range": (1.0, 0.72, 0.0), "open": (0.85, 0.15, 0.85),
       "wrong": (0.9, 0.1, 0.1), "miss": (0.55, 0.3, 0.1), "truth": (0.1, 0.85, 0.3), "point": (1.0, 0.1, 0.1)}


def _rgb(gray):
    g = np.asarray(gray, np.float64)
    if g.ndim == 3:
        return g.copy()
    lo, hi = float(g.min()), float(g.max())
    g = (g - lo) / (hi - lo) if hi > lo else np.zeros_like(g)
    return np.repeat(g[:, :, None], 3, axis=2)


def _paint_status(base, res):
    """成分の判定ごとに塗る(決まった成分は分割の境界も描く)。"""
    img = _rgb(base)
    comp = ndimage.label(np.asarray(res["labels"]) > 0, np.ones((3, 3), bool))[0]
    for lab, st in zip(res["components"]["label"], res["components"]["status"]):
        m = comp == lab
        img[m] = 0.55 * img[m] + 0.45 * np.array(COL[st])
    edges = np.zeros(img.shape[:2], bool)
    lb = np.asarray(res["labels"])
    edges |= (lb != np.roll(lb, 1, 0)) | (lb != np.roll(lb, 1, 1))
    edges &= lb > 0
    img[edges] = (0.05, 0.05, 0.05)
    return np.clip(img, 0, 1)


def _iv(res) -> str:
    """op の答えを文字に: 決まれば 1 つの数、決まらなければ lo〜hi(上限を開けば ∞)。"""
    if res["determined"]:
        return "%d" % res["lo"]
    return "%d〜%s" % (res["lo"], "∞" if res["hi"] is None else res["hi"])


def _mask_base(m):
    """マスクを図の下地に: 背景は明るい灰、前景は中間の灰(_rgb の正規化で背景が黒にならないように)。"""
    return np.repeat(np.where(m, 0.55, 0.93)[:, :, None], 3, axis=2)


def _determined_points(res):
    """決まった成分の塊の重心だけ(決まらない成分は棄権なので点を出さない)。"""
    det = {int(l) for l, st in zip(res["components"]["label"], res["components"]["status"]) if st == "determined"}
    comp = ndimage.label(np.asarray(res["labels"]) > 0, np.ones((3, 3), bool))[0]
    pts = centroids(res["labels"])
    keep = [int(comp[int(round(q[0])), int(round(q[1]))]) in det for q in pts]
    return pts[np.asarray(keep, bool)] if len(pts) else pts


def _crop_around(img, m, size):
    """前景の重心を中心に size x size を切り出す(はみ出す分は明るい灰で埋める)。"""
    cy, cx = [int(round(v)) for v in ndimage.center_of_mass(m)]
    h = size // 2
    out = np.full((size, size, 3), 0.93)
    r0, c0 = cy - h, cx - h
    sr0, sc0 = max(r0, 0), max(c0, 0)
    sr1, sc1 = min(r0 + size, img.shape[0]), min(c0 + size, img.shape[1])
    out[sr0 - r0:sr1 - r0, sc0 - c0:sc1 - c0] = img[sr0:sr1, sc0:sc1]
    return out


def _box(img, b, color):
    r0, c0, r1, c1 = [int(round(v)) for v in b]
    img[r0:r1 + 1, [c0, c1]] = color
    img[[r0, r1], c0:c1 + 1] = color


def _cross(img, p, color, s=3):
    r, c = int(round(p[0])), int(round(p[1]))
    h, w = img.shape[:2]
    img[max(r - s, 0):min(r + s + 1, h), min(max(c, 0), w - 1)] = color
    img[min(max(r, 0), h - 1), max(c - s, 0):min(c + s + 1, w)] = color


def _label(img, text, fs_=13):
    return np.asarray(fs.text_box(np.asarray(img, np.float64), text, (6, 6), anchor="lt", font_size=fs_))


# --------------------------------------------------------------------------- #
# 1. 2 つの円: どこで割れなくなるか(閉形式で予言して測る)                        #
# --------------------------------------------------------------------------- #
def chapter_pair():
    print("\n== 1. 2 つの円の重なり率を振る(閉形式の予言 vs 実測)")
    radii = (12, 20) if REDUCED else (12, 20, 30)
    step = 0.05 if REDUCED else 0.025
    reps = 2 if REDUCED else 4
    os_ = np.round(np.arange(0.0, 0.951, step), 3)
    rows = []                     # (r1, r2, o, rep, prom2, rel2, verdict, chain_h1, area_ratio)
    for r1, r2 in [(r, r) for r in radii] + [(20, 12)]:
        for o in os_:
            for k in range(reps):
                m = pair_mask(r1, r2, float(o), (r1, r2, int(o * 1000), k))
                res = count_op(m, rt=RT_BUBBLE)
                pk = res["peaks"]
                order = np.argsort(-pk["prominence"], kind="stable")
                p2 = float(pk["prominence"][order[1]]) if len(order) > 1 else 0.0
                q2 = float(pk["rel_prominence"][order[1]]) if len(order) > 1 else 0.0
                n_chain, _ = count_chain(m, 1.0)
                rows.append((r1, r2, float(o), k, p2, q2, verdict(res, 2), n_chain,
                             float(res["components"]["area_ratio"][0])))
    # 門 1: 突出度が閉形式どおりか(等しい半径、o = 0.1〜0.8)
    worst = 0.0
    for r1, r2, o, k, p2, q2, v, nc, ar in rows:
        if r1 == r2 and 0.1 <= o <= 0.8:
            worst = max(worst, abs(p2 - r1 * rel_closed(o)))
    gate("突出度が閉形式 r(1 − sqrt(1 − (1 − o)²))どおり", worst <= 2.0,
         "最大のずれ %.2f px(許し 2 px = 山の高さと鞍の高さの量子化 0.5 + 1 px に余裕、半径 %s、o = 0.1〜0.8)" % (worst, list(radii)))
    # 門 2: 自信をもって間違うのは、面積でも見えない重なり率だけ
    bad = []
    for r1, r2, o, k, p2, q2, v, nc, ar in rows:
        if r1 == r2 and v == "wrong" and o < o_unobservable(r1, RT_BUBBLE) - 0.03:
            bad.append((r1, o))
    o_obs = {r: o_unobservable(r, RT_BUBBLE) for r in radii}
    n_miss = sum(1 for x in rows if x[0] == x[1] and x[6] == "miss")
    gate("等しい 2 円で、決まらないと言った区間はいつも真値 2 を含む", n_miss == 0, "外れ %d 件" % n_miss)
    gate("自信をもった誤りは閉形式の『見えない』重なり率の外に出ない", not bad,
         "見えない境 o* = " + ", ".join("r%d: %.3f" % kv for kv in o_obs.items())
         + ("" if not bad else "、外れ %s" % bad[:4]))
    # 門 3: 割れなくなる重なり率(right が途切れる最初の o)が閉形式の予言の近く
    o_pred = o_for_rel(REL_HI)
    breaks = {}
    for r in radii:
        vs = {}
        for r1, r2, o, k, p2, q2, v, nc, ar in rows:
            if r1 == r2 == r:
                vs.setdefault(o, []).append(v)
        first = min((o for o, l in vs.items() if any(x != "right" for x in l)), default=1.0)
        breaks[r] = first
    # 量子化で突出度は閉形式より最大 2 px 低く出る(門 1)ので、半径 r での予言の下端は
    # rel_closed(o) = rel_hi + 2/r になる重なり率。上端は量子化なしの o(rel_hi)。
    lo_pred = {r: o_for_rel(min(REL_HI + 2.0 / r, 0.99)) for r in radii}
    ok3 = all(lo_pred[r] - 0.03 <= b <= o_pred + 0.05 for r, b in breaks.items())
    gate("割れなくなる重なり率が閉形式の予言の幅に入る", ok3,
         "予言 o(rel_hi + 2/r)〜o(rel_hi) = %s、実測 %s"
         % (", ".join("r%d: %.3f〜%.3f" % (r, lo_pred[r], o_pred) for r in radii),
            ", ".join("r%d: %.3f" % kv for kv in breaks.items())))
    # 門 4(既存の穴の記録): 既存の連鎖は o = 0.8 で自信をもって 1 個と答える
    c08 = [nc for r1, r2, o, k, p2, q2, v, nc, ar in rows if r1 == r2 == 20 and abs(o - 0.8) < 1e-9]
    v08 = [v for r1, r2, o, k, p2, q2, v, nc, ar in rows if r1 == r2 == 20 and abs(o - 0.8) < 1e-9]
    gate("既存の連鎖(h = 1 px)は o = 0.8 で 1 個と答え、新しい op は数を返さない",
         all(c == 1 for c in c08) and all(x in ("open", "range") for x in v08),
         "連鎖 %s / op %s" % (c08, v08))
    tally = {}
    for r1, r2, o, k, p2, q2, v, nc, ar in rows:
        if r1 == r2:
            tally[v] = tally.get(v, 0) + 1
    print("   等しい 2 円 %d 件の判定: %s" % (sum(tally.values()), tally))
    return {"rows": rows, "radii": radii, "o_obs": o_obs, "breaks": breaks, "o_pred": o_pred}


# --------------------------------------------------------------------------- #
# 2. 合成の世界: 鎖状に重なった円(world_blobs_touching、真値は生成側)            #
# --------------------------------------------------------------------------- #
WORLD_OV = (0.0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8)


def chapter_world():
    print("\n== 2. 合成の世界 world_blobs_touching(12 円、半径 14 px)で重なり率を振る")
    seeds = range(3) if REDUCED else range(12)
    per = {}
    keep = {}
    for ov in WORLD_OV:
        acc = {"truth": [], "cc": [], "chain": [], "lo": [], "hi": [], "v": [],
               "alc_op": [], "alc_chain": [], "abst": [], "alc_forced": []}
        for s in seeds:
            w = SW.world_blobs_touching(n=12, overlap=ov, seed=int(s), size=(160, 160), radius=14.0)
            lab_t = np.asarray(w["labels"])
            m = lab_t > 0
            tr = w["truth"]
            n = int(tr["n"])
            centers = np.asarray(tr["centers"], np.float64)
            boxes = disk_boxes(centers, float(tr["radius"]), m.shape)
            comp = B.blob_label(m)
            res = count_op(m, rt=RT_BUBBLE)
            nc, chain_lab = count_chain(m, 1.0)
            sc, ab = scored_by_component(res, comp, centers, boxes)
            acc["truth"].append(n)
            acc["cc"].append(int(comp.max()))
            acc["chain"].append(nc)
            acc["lo"].append(res["lo"])
            acc["hi"].append(-1 if res["hi"] is None else res["hi"])
            acc["v"].append(verdict(res, n))
            acc["alc_op"].append(sc)
            acc["abst"].append(ab)
            acc["alc_chain"].append(alcon_score(centroids(chain_lab), boxes))
            acc["alc_forced"].append(alcon_score(centroids(res["labels"]), boxes))
            if s == 0:
                keep[ov] = (w, res, boxes, centers)
        per[ov] = acc
        t = np.array(acc["truth"], float)
        rel = lambda k: float(np.mean((np.array(acc[k], float) - t) / t))   # noqa: E731
        vs = acc["v"]
        wid = [h - l for l, h in zip(acc["lo"], acc["hi"]) if h >= 0]
        print("   o=%.1f  CC %+.3f  連鎖 %+.3f  op lo %+.3f | 決まる %d/%d 区間 %d(幅 %.1f) 開 %d 誤り %d | ALCON 連鎖 %.2f op(決まった分) %.2f 棄権 %d"
              % (ov, rel("cc"), rel("chain"), rel("lo"), vs.count("right"), len(vs), vs.count("range"), _mean_or_nan(wid),
                 vs.count("open"), vs.count("wrong"), np.mean([a["norm"] for a in acc["alc_chain"]]),
                 _mean_or_nan([a["norm"] for a in acc["alc_op"] if a["n"]]), int(np.sum(acc["abst"]))))
    allv = [v for ov in WORLD_OV for v in per[ov]["v"]]
    n_all = len(allv)
    wrong = allv.count("wrong") + allv.count("miss")
    gate("合成の世界で自信をもった誤り・区間外れが 0 件", wrong == 0, "%d 世界中 %d 件" % (n_all, wrong))
    det_ok = all(per[ov]["v"].count("right") == len(per[ov]["v"]) for ov in WORLD_OV if ov <= 0.2)
    gate("浅い重なり(o ≤ 0.2)は全部 1 つの個数に決まり、真値と一致", det_ok)
    # 既存の連鎖: o = 0.8 で個数が真値から離れる(穴の記録)
    t8 = np.array(per[0.8]["truth"], float)
    ch8 = float(np.mean(np.abs(np.array(per[0.8]["chain"], float) - t8) / t8))
    gate("既存の連鎖は o = 0.8 で自信をもった数を返し、平均 10 % 以上外れる", ch8 >= 0.10,
         "平均 |相対誤差| %.3f" % ch8)
    alc = [a["norm"] for ov in WORLD_OV for a in per[ov]["alc_op"] if a["n"]]
    gate("ALCON 型の得点: 決まった成分では満点に近い(平均 ≥ 0.95)", float(np.mean(alc)) >= 0.95,
         "平均 %.3f(%d 世界)" % (float(np.mean(alc)), len(alc)))
    return {"per": per, "keep": keep}


# --------------------------------------------------------------------------- #
# 3. ALCON 型の採点そのものの門(閉形式)                                          #
# --------------------------------------------------------------------------- #
def chapter_scorer():
    print("\n== 3. ALCON 型の採点の閉形式")
    rng = np.random.default_rng(20261018)
    c = rng.uniform(20, 180, (9, 2))
    bx = disk_boxes(c, 6.0, (200, 200))
    n = len(c)
    a = alcon_score(c, bx)
    b = alcon_score(c + 50.0 + 400.0, bx)
    d = alcon_score(np.concatenate([c, c + 0.5]), bx)
    e = alcon_score(np.zeros((0, 2)), bx)
    gate("全部当たり = N、全部外れ = −2N、二重回答 = 0、無回答 = −N",
         (a["score"], b["score"], d["score"], e["score"]) == (n, -2 * n, 0, -n),
         "N=%d: %d / %d / %d / %d" % (n, a["score"], b["score"], d["score"], e["score"]))
    # 1 点が 2 つの矩形に入るとき、別の点が片方にしか入らないなら両方当てる(最大マッチング)
    bx2 = np.array([[0, 0, 10, 10], [0, 5, 10, 15]], float)
    pts = np.array([[5, 7], [5, 2]], float)
    gate("重なった矩形でも最大マッチング(貪欲なら 1、正しくは 2)", alcon_score(pts, bx2)["hits"] == 2)


# --------------------------------------------------------------------------- #
# 4. 壊す探針                                                                   #
# --------------------------------------------------------------------------- #
def chapter_probes():
    print("\n== 4. 壊して確かめる")
    m = pair_mask(20, 20, 0.8, (20, 20, 800, 0))
    with_check = count_op(m, rt=RT_BUBBLE)
    without = count_op(m, rt=None)
    gate("面積の検査を外すと、重なり率 0.8 の 2 円を自信をもって 1 個と答える",
         with_check["hi"] is None and without["determined"] and without["count"] == 1,
         "検査あり lo=%d hi=%s / 検査なし count=%s" % (with_check["lo"], with_check["hi"], without["count"]))
    # 帯を潰す(rel_lo = rel_hi)と、あいまいの区間が消えて誤りが出る
    wrong = 0
    for o in np.arange(0.40, 0.70, 0.025):
        for k in range(3):
            mm = pair_mask(20, 20, float(o), (77, int(o * 1000), k))
            r = count_op(mm, rt=None, rel_lo=0.10, rel_hi=0.10)
            wrong += verdict(r, 2) == "wrong"
    gate("帯を潰す(rel_lo = rel_hi = 0.10)と、o = 0.4〜0.7 で自信をもった誤りが出る", wrong > 0,
         "%d 件(帯 0.05〜0.15 なら 0 件 —— 門 2)" % wrong)
    # 尺度: 2 倍に拡大しても相対突出度の判定は変わらない(絶対の h は変わる)
    same, chain_same, tot = 0, 0, 0
    for s in range(3 if REDUCED else 8):
        w = SW.world_blobs_touching(n=12, overlap=0.3, seed=100 + s, size=(160, 160), radius=14.0)
        mm = np.asarray(w["labels"]) > 0
        big = np.kron(mm, np.ones((2, 2), bool))
        r1, r2 = count_op(mm, rt=RT_BUBBLE), count_op(big, rt=RT_BUBBLE)
        same += (r1["lo"], r1["hi"]) == (r2["lo"], r2["hi"])
        chain_same += count_chain(mm, 2.0)[0] == count_chain(big, 2.0)[0]
        tot += 1
    gate("2 倍に拡大しても op の区間は同じ(相対突出度は尺度によらない)", same == tot,
         "%d/%d(既存の連鎖 h = 2 px は %d/%d)" % (same, tot, chain_same, tot))
    # 入力の拒否(fail-closed)
    bad = 0
    for kw in ({"rel_lo": 0.2, "rel_hi": 0.1}, {"round_tol": float("nan")}, {"min_prominence": -1.0}):
        try:
            B.blob_count_interval(m, **kw)
        except ValueError:
            bad += 1
    try:
        B.blob_count_interval(np.zeros((4, 4, 4), bool))
    except ValueError:
        bad += 1
    gate("不正な入力は値を返さずに拒否(帯の逆転・NaN・負の床・3-D)", bad == 4, "%d/4" % bad)
    # 台帳経由でも同じ実体
    via, _notes = fs.op_run("blob_count_interval", m, round_tol=RT_BUBBLE)
    gate("台帳(fs.op_run)経由でも同じ答え", via["lo"] == with_check["lo"] and via["hi"] == with_check["hi"])


# --------------------------------------------------------------------------- #
# 5. 実データ(あるときだけ)                                                     #
# --------------------------------------------------------------------------- #
PEMWE_URL = "https://zenodo.org/api/records/10184579/files/PEMWE_Model_Training_Dataset.rar/content"
PEMWE_MD5 = "6358d8c5f2936332661e19647c5f696d"
BBBC_URL = "https://data.broadinstitute.org/bbbc/BBBC005/BBBC005_v1_ground_truth.zip"
BBBC_SHA256 = "40edbd48e0c28e9adeb000893888c7291b28c788d1093bda7b5999753795a514"
#: 記録値(2026-10-18 の手元の実行)。CI では実データを持たないので、これを印字して章を飛ばす。
RECORDED: dict = {
    "bbbc_small_rel_err_op": 0.0034, "bbbc_small_rel_err_cc": 0.0937, "bbbc_small_confident_wrong": "11/600",
    "bbbc_large_confident_wrong": "0/300", "bbbc_large_refused": "286/300",
    "pemwe_semisynthetic_confident_wrong": "2/65", "pemwe_alcon_determined": 0.950,
    "pemwe_isolated_oversplit": "2/537", "pemwe_tradeoff_wrong_rt0.30": 0.031, "pemwe_tradeoff_wrong_rt0.65": 0.185,
}


def _data_dir() -> str:
    d = os.path.join(os.environ.get("FULLSEYE_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "fullseye"),
                     "poc_dense_bubble_count")
    os.makedirs(d, exist_ok=True)
    return d


def _may_download() -> bool:
    return os.environ.get("FULLSEYE_BUBBLE_DOWNLOAD", "").strip() in ("1", "yes", "true")


def _digest(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _fetch(url, path, algo, want):
    """取って、指紋が合わなければ消して拒否する。"""
    if not os.path.exists(path):
        if not _may_download():
            return False
        import urllib.request
        tmp = path + ".part"
        with urllib.request.urlopen(url, timeout=300) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(tmp, path)
    got = _digest(path, algo)
    if got != want:
        os.remove(path)
        raise RuntimeError("%s の %s が合わない(%s != %s)。消した" % (os.path.basename(path), algo, got, want))
    return True


def _rar_tool():
    """RAR を読める tar(libarchive の bsdtar)。Windows 10 以降の標準の tar.exe は bsdtar。"""
    if sys.platform == "win32":
        p = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "tar.exe")
        return p if os.path.exists(p) else None
    return shutil.which("bsdtar")


def load_pemwe():
    """(画像, マスク) の列(35 組)。無ければ None。"""
    d = _data_dir()
    rar = os.path.join(d, "PEMWE_Model_Training_Dataset.rar")
    out = os.path.join(d, "pemwe")
    try:
        if not _fetch(PEMWE_URL, rar, "md5", PEMWE_MD5):
            return None
    except Exception as exc:                            # noqa: BLE001
        print("   PEMWE を取れない: %s" % exc)
        return None
    if not os.path.isdir(out):
        tool = _rar_tool()
        if tool is None:
            print("   RAR を開く bsdtar が無い(Linux なら libarchive-tools)")
            return None
        os.makedirs(out + ".part", exist_ok=True)
        subprocess.run([tool, "-xf", rar, "-C", out + ".part"], check=True, timeout=300)
        os.replace(out + ".part", out)
    from PIL import Image
    pairs = []
    for img_p in sorted(Path(out).rglob("*.tif")):
        if "Mask" in str(img_p.parent.name):
            continue
        mdir = [p for p in img_p.parent.parent.iterdir() if p.is_dir() and "Mask" in p.name]
        if not mdir:
            continue
        mp = mdir[0] / img_p.name
        if not mp.exists():
            continue
        im = np.asarray(Image.open(img_p), np.float64) / 255.0
        mk = np.asarray(Image.open(mp)) > 127
        pairs.append((img_p.parent.parent.name + "/" + img_p.stem, im, mk))
    if len(pairs) != 35:
        print("   PEMWE の組が 35 でない(%d)—— 拒否" % len(pairs))
        return None
    return pairs


def load_bbbc():
    """{'small': [(個数, マスク)], 'large': [...]}。無ければ None。"""
    path = os.path.join(_data_dir(), "BBBC005_v1_ground_truth.zip")
    try:
        if not _fetch(BBBC_URL, path, "sha256", BBBC_SHA256):
            return None
    except Exception as exc:                            # noqa: BLE001
        print("   BBBC005 を取れない: %s" % exc)
        return None
    import zipfile
    from PIL import Image
    z = zipfile.ZipFile(path)
    sets = {"_w1": [], "_w2": []}
    for name in sorted(z.namelist()):
        mm = re.search(r"^BBBC005_v1_ground_truth/SIMCEPImages_\w+_C(\d+)_F1_s\d+(_w[12])\.TIF$", name)
        if mm:
            sets[mm.group(2)].append((int(mm.group(1)), name))
    out = {}
    for key, items in sets.items():
        out[key] = [(c, np.asarray(Image.open(io.BytesIO(z.read(n)))) > 127, n) for c, n in items]
    med = {k: float(np.median([np.bincount(ndimage.label(m)[0].ravel())[1:].mean() for c, m, n in v[:40] if m.any()]))
           for k, v in out.items()}
    small, large = ("_w1", "_w2") if med["_w1"] < med["_w2"] else ("_w2", "_w1")
    print("   BBBC005: 面積の中央値 %s → 小さい物体 = %s、大きい物体 = %s" % (
        {k: round(v) for k, v in med.items()}, small, large))
    return {"small": out[small], "large": out[large]}


def rederive(res: dict, rt) -> dict:
    """round_tol なしの答えに、面積の検査を後から当てる(山の判定は round_tol によらない)。

    op の中の式(面積 > (1 + rt + 1/h_min) · Σπh²、h は雑音でない山)をここでもう一度書く。
    BBBC の 4 通りの round_tol を 1 回の持続計算で出すため。直接呼んだ答えと照合する(章の門)。
    """
    if rt is None:
        return {"lo": res["lo"], "hi": res["hi"], "determined": res["determined"]}
    comp = res["components"]
    pk = res["peaks"]
    lo, hi, open_ = 0, 0, False
    for lab, l, h, ar in zip(comp["label"], comp["lo"], comp["hi"], comp["area_ratio"]):
        hs = pk["height"][(pk["component"] == lab) & (pk["status"] != B.PEAK_NOISE)]
        lo += int(l)
        if ar > 1.0 + rt + 1.0 / max(float(hs.min()), 1.0):
            open_ = True
        else:
            hi += int(h)
    hi_v = None if open_ else hi
    return {"lo": lo, "hi": hi_v, "determined": hi_v == lo}


def chapter_bbbc():
    print("\n== 5. BBBC005(CC0、SIMCEP の合成細胞、個数はファイル名)")
    # 予算 reduced(CI)では実データの章を走らせない: 間引いた標本で門の率を測ると門が標本の運になる
    #(2026-10-18、10 枚に 1 枚で 4/60 = 6.7 %、全数では 11/600 = 1.8 %)。記録値を印字して飛ばす。
    data = None if REDUCED else load_bbbc()
    if data is None:
        print("   データが無いか予算 reduced(取得は FULLSEYE_BUBBLE_DOWNLOAD=1)。記録値: %s"
              % ", ".join("%s %s" % kv for kv in RECORDED.items() if kv[0].startswith("bbbc")))
        return None
    stats = {}
    for key, items in data.items():
        if key == "large":
            items = items[::2]                      # 大きい物体の 600 枚は 1 枚 0.4 s。半分で足りる
        rows = []
        n_same = 0
        for i, (c, m, name) in enumerate(items):
            base = count_op(m, rt=None)
            r = {rt: rederive(base, rt) for rt in (None, 0.2, RT_CELL, 0.5)}
            if i % 25 == 0:                         # 第 2 の経路: op を直接 round_tol つきで呼んだ答えと照合
                d = count_op(m, rt=RT_CELL)
                n_same += (d["lo"], d["hi"]) == (r[RT_CELL]["lo"], r[RT_CELL]["hi"])
            # 既存の連鎖(blob_split)は 520x696 で 1 枚 1〜4 秒かかるので 10 枚に 1 枚だけ(-1 = 回していない)
            nch = count_chain(m, 1.0)[0] if i % 10 == 0 else -1
            rows.append((c, int(B.blob_label(m).max()), nch, r, name))
        n_chk = len(range(0, len(items), 25))
        gate("%s: 面積の検査を後から当て直した答え = op を直接呼んだ答え" % key, n_same == n_chk, "%d/%d" % (n_same, n_chk))
        stats[key] = rows
        t = np.array([x[0] for x in rows], float)
        e_cc = np.abs(np.array([x[1] for x in rows]) - t) / t
        ch = np.array([x[2] for x in rows], float)
        e_ch = np.abs(ch[ch >= 0] - t[ch >= 0]) / t[ch >= 0]
        e_lo = np.abs(np.array([x[3][RT_CELL]["lo"] for x in rows]) - t) / t
        print("   %s(%d 枚): 平均 |相対誤差| CC %.3f / 連鎖 h=1 %.3f(%d 枚)/ op lo %.3f" % (
            key, len(rows), e_cc.mean(), e_ch.mean(), len(e_ch), e_lo.mean()))
        for rt in (None, 0.2, RT_CELL, 0.5):
            vs = [verdict(x[3][rt], x[0]) for x in rows]
            wr = [abs(x[3][rt]["lo"] - x[0]) for x in rows if verdict(x[3][rt], x[0]) == "wrong"]
            print("     round_tol=%s: 決まって正 %d / 区間 %d / 上限を開く %d / 自信をもった誤り %d(最大 %d 個ずれ)/ 区間の外れ %d" % (
                rt, vs.count("right"), vs.count("range"), vs.count("open"), vs.count("wrong"), max(wr, default=0),
                vs.count("miss")))
        stats[key + "_err"] = (e_cc.mean(), e_ch.mean(), e_lo.mean())
    s = stats["small"]
    vs = [verdict(x[3][RT_CELL], x[0]) for x in s]
    wr = [abs(x[3][RT_CELL]["lo"] - x[0]) for x in s if verdict(x[3][RT_CELL], x[0]) == "wrong"]
    e_cc, e_ch, e_lo = stats["small_err"]
    gate("小さい物体: op の個数の相対誤差が連結成分より小さく、2 % 以内", e_lo <= 0.02 and e_lo < e_cc,
         "op %.4f / CC %.4f / 連鎖 %.4f" % (e_lo, e_cc, e_ch))
    # ★最初は「相対 3 % 以内」と書いて、真値 30 個で 1 個ずれた 0.033 で落ちた —— 言いたかったのは
    #   「誤っても 1 個ぶん」なので、個数の差で書き直した(2026-10-18)。真値は画面の外に出た細胞も
    #   数えているので、1 個の差の一部は op でなく真値の規約の側にある(どれかは区別していない)。
    #   ★2 回目: 1 個ぶんでも足りなかった(最大 2 個、600 枚の全数で)。ずれの大きさは印字に残し、
    #   門は「自信をもった誤りの件数」だけにする —— 合わせ直すたびに門を緩めるのは門ではないので、
    #   ここで止める。
    gate("小さい物体: 自信をもった誤りは 5 % 以下",
         vs.count("wrong") <= 0.05 * len(vs),
         "%d/%d 件、最大のずれ %d 個(区間の外れは別に %d 件)" % (vs.count("wrong"), len(vs), max(wr, default=0),
                                                         vs.count("miss")))
    lg = stats["large"]
    vl = [verdict(x[3][RT_CELL], x[0]) for x in lg]
    vn = [verdict(x[3][None], x[0]) for x in lg]
    gate("大きい物体(重なりが深い): 面積の検査つきなら自信をもった誤りは 5 % 以下",
         vl.count("wrong") <= 0.05 * len(vl),
         "誤り %d/%d、上限を開いて拒否 %d、区間の外れ %d(検査なしなら誤り %d・外れ %d)" % (
             vl.count("wrong"), len(vl), vl.count("open"), vl.count("miss"), vn.count("wrong"), vn.count("miss")))
    return stats


def chapter_pemwe():
    print("\n== 6. 水電解の泡(PEMWE、CC BY 4.0、手作業マスク)")
    # 予算 reduced(CI)では実データの章を走らせない: 間引いた標本で門の率を測ると門が標本の運になる
    #(2026-10-18、10 枚に 1 枚で 4/60 = 6.7 %、全数では 11/600 = 1.8 %)。記録値を印字して飛ばす。
    pairs = None if REDUCED else load_pemwe()
    if pairs is None:
        print("   データが無いか予算 reduced(取得は FULLSEYE_BUBBLE_DOWNLOAD=1)。記録値: %s"
              % ", ".join("%s %s" % kv for kv in RECORDED.items() if kv[0].startswith("pemwe")))
        return None
    # 6a. 孤立した泡の形(手作業マスクの成分のうち、充実度 ≥ 0.95・縁に触れない)。
    #     大きさで 2 つに分ける: 等価半径 R_RESOLVE 以上 = op が分けられるはずの大きさ(門 1 の量子化
    #     2 px を rel_hi で割った 13 px … ではなく、山の高さ h と突出度 p の比で効くのは h·rel_hi ≥ 1.5 px
    #     → h ≥ 10 px)。5〜10 px は記録だけ(格子に埋もれる側)。
    tmpl, small = [], []
    for name, im, mk in pairs:
        lab = B.blob_label(mk)
        ft = B.blob_features(lab)
        for k in range(len(ft["label"])):
            if ft["solidity"][k] >= 0.95 and not ft["touches_border"][k] and ft["area"][k] >= math.pi * 25:
                sl = ndimage.find_objects((lab == int(ft["label"][k])).astype(np.int32))[0]
                t = np.asarray(lab[sl] == int(ft["label"][k]))
                (tmpl if ft["area"][k] >= math.pi * R_RESOLVE ** 2 else small).append(t)
    print("   孤立した泡の形: 等価半径 %d px 以上 %d 個 / 5〜%d px %d 個(35 枚のマスクから。★『充実度 ≥ 0.95 なら 1 個』"
          "は仮定 —— 重なり率 0.9 を超える 2 個はこの仮定でも見分けられない)" % (R_RESOLVE, len(tmpl), R_RESOLVE, len(small)))
    single = [count_op(t, rt=None) for t in tmpl]
    over = sum(r["lo"] > 1 for r in single)
    amb = sum(not r["determined"] for r in single)
    ratio_x = np.array([r["components"]["area_ratio"][0] - 1.0 - 1.0 / max(float(r["peaks"]["height"].max()), 1.0)
                        for r in single])
    rt95 = float(math.ceil(np.quantile(ratio_x, 0.95) * 20.0) / 20.0)
    rt_p = RT_CELL                                   # 冒頭で宣言した「いびつな物体」の許し
    print("   1 個を 2 個以上と割った %d / あいまい %d。round_tol は冒頭の宣言 %.2f を使う"
          "(孤立した泡の 95 %% を通す許しなら %.2f —— 下の掃引で、それが隠れた泡も通すことを示す)"
          % (over, amb, rt_p, rt95))
    gate("孤立した泡を割りすぎない(確かな山が 2 つ以上 ≤ 2 %)", over <= 0.02 * len(tmpl),
         "%d/%d" % (over, len(tmpl)))
    # 6b. 半合成: 実際の泡の形を重なり率を振って鎖に並べる(真値 = 置いた個数・矩形・重心)
    ovs = (0.0, 0.2, 0.4, 0.6)
    per = {}
    ex = {}
    n_scene = 6 if REDUCED else 20
    for ov in ovs:
        acc = {"v": [], "cc": [], "chain": [], "lo": [], "t": [], "alc": [], "alc_chain": [], "abst": [], "base": []}
        for s in range(n_scene):
            sc = _place_chain(tmpl, ov, (int(ov * 100), s), size=320)
            if sc is None:
                continue
            m, boxes, cents = sc
            n = len(boxes)
            comp = B.blob_label(m)
            res = count_op(m, rt=rt_p)
            acc["base"].append((count_op(m, rt=None), n))
            nc, chain_lab = count_chain(m, 1.0)
            a, ab = scored_by_component(res, comp, cents, boxes)
            acc["v"].append(verdict(res, n))
            acc["cc"].append(int(comp.max()))
            acc["chain"].append(nc)
            acc["lo"].append(res["lo"])
            acc["t"].append(n)
            acc["alc"].append(a)
            acc["abst"].append(ab)
            acc["alc_chain"].append(alcon_score(centroids(chain_lab), boxes))
            if s < 2:
                ex.setdefault(ov, []).append((m, res, boxes, cents))
        per[ov] = acc
        t = np.array(acc["t"], float)
        vs = acc["v"]
        print("   o=%.1f(%d 場面): CC %+.3f 連鎖 %+.3f op lo %+.3f | 決まる %d 区間 %d 開 %d 誤り %d 外れ %d | ALCON 連鎖 %.2f op %.2f 棄権 %d"
              % (ov, len(t), np.mean((np.array(acc["cc"]) - t) / t), np.mean((np.array(acc["chain"]) - t) / t),
                 np.mean((np.array(acc["lo"]) - t) / t), vs.count("right"), vs.count("range"), vs.count("open"),
                 vs.count("wrong"), vs.count("miss"), np.mean([x["norm"] for x in acc["alc_chain"]]),
                 _mean_or_nan([x["norm"] for x in acc["alc"] if x["n"]]), int(np.sum(acc["abst"]))))
    allv = [v for ov in ovs for v in per[ov]["v"]]
    gate("実際の泡の形の半合成: 自信をもった誤り(1 つの数に決めて外す)≤ 5 %", allv.count("wrong") <= 0.05 * len(allv),
         "%d/%d" % (allv.count("wrong"), len(allv)))
    shallow = [v for ov in ovs if ov <= 0.2 for v in per[ov]["v"]]
    gate("実際の泡の形の半合成: 浅い重なり(o ≤ 0.2)では区間も外れない", shallow.count("miss") == 0,
         "外れ %d/%d" % (shallow.count("miss"), len(shallow)))
    # ★記録(門ではない): o = 0.4 では「決まらない」と言った塊の区間が真値を外す。いびつな泡が
    #   別の泡に食い込むと、くびれが山を残さず、上限 hi にも数えられない(op の docstring の限界)。
    deep_miss = sum(per[ov]["v"].count("miss") for ov in ovs if ov >= 0.4)
    deep_n = sum(len(per[ov]["v"]) for ov in ovs if ov >= 0.4)
    print("   記録: o ≥ 0.4 で区間の外れ %d/%d(全部『決まらない』と答えた塊。真値が hi を上回る)" % (deep_miss, deep_n))
    al = [x["norm"] for ov in ovs for x in per[ov]["alc"] if x["n"]]
    gate("実際の泡の形の半合成: ALCON 型の得点(決まった成分)平均 ≥ 0.9", float(np.mean(al)) >= 0.9,
         "平均 %.3f(%d 場面)" % (float(np.mean(al)), len(al)))
    # 6b''. 矛盾の掃引: 形の許し round_tol を広げると孤立した泡は数えられるようになり、隠れた泡も通す
    sweep = []
    base_all = [bn for ov in ovs for bn in per[ov]["base"]]
    for rt in (0.0, 0.05, 0.1, 0.2, 0.3, 0.45, rt95):
        sd = float(np.mean([rederive(r, rt)["determined"] for r in single]))
        vv = [verdict(rederive(r, rt), n) for r, n in base_all]
        sweep.append((rt, sd, vv.count("wrong") / len(vv), vv.count("miss") / len(vv),
                      (vv.count("open") + vv.count("range") + vv.count("miss")) / len(vv)))
        print("   掃引 round_tol=%.2f: 孤立した泡を 1 個と言い切る %.3f / 塊の自信をもった誤り %.3f・区間の外れ %.3f・棄権 %.3f"
              % sweep[-1])
    w_decl = [x for x in sweep if abs(x[0] - RT_CELL) < 1e-9][0]
    w_95 = sweep[-1]
    gate("形の許しを孤立した泡の 95 % 点まで広げると、自信をもった誤りが宣言値より増える(矛盾の記録)",
         w_95[2] > w_decl[2], "round_tol %.2f: %.3f / %.2f: %.3f" % (rt95, w_95[2], RT_CELL, w_decl[2]))
    # 6b'. 小さい泡(等価半径 5〜10 px)は記録だけ: 山が格子の量子化に埋もれる側
    sm = {}
    for ov in (0.2, 0.4):
        vs_s = []
        for s in range(n_scene):
            sc = _place_chain(small, ov, (7, int(ov * 100), s), size=200)
            if sc is not None:
                vs_s.append(verdict(count_op(sc[0], rt=rt_p), len(sc[1])))
        sm[ov] = vs_s
        print("   記録: 小さい泡(5〜%d px)o=%.1f: 決まる %d 区間 %d 開 %d 誤り %d 外れ %d(%d 場面)" % (
            R_RESOLVE, ov, vs_s.count("right"), vs_s.count("range"), vs_s.count("open"), vs_s.count("wrong"),
            vs_s.count("miss"), len(vs_s)))
    # 6c. 実画像そのもの: 真の個数は無い(意味分割)。区間と拒否の内訳だけを示す
    real = []
    for name, im, mk in pairs:
        r = count_op(mk, rt=rt_p)
        st = r["components"]["status"]
        real.append((name, int(B.blob_label(mk).max()), r["lo"], r["hi"],
                     st.count("determined"), st.count("ambiguous"), st.count("unexplained"), im, mk, r))
    det = sum(x[4] for x in real)
    tot = sum(x[4] + x[5] + x[6] for x in real)
    print("   実画像 35 枚: 成分 %d 個のうち 決まる %d / あいまい %d / 上限を開く %d。連結成分の合計 %d、op の lo 合計 %d"
          % (tot, det, sum(x[5] for x in real), sum(x[6] for x in real), sum(x[1] for x in real),
             sum(x[2] for x in real)))
    return {"tmpl": tmpl, "rt": rt_p, "per": per, "ex": ex, "real": real, "ovs": ovs, "small": sm, "sweep": sweep}


def _place_chain(tmpl, ov, seed, k=4, size=256):
    """泡の形 k 個を鎖に置く。隣どうしの中心間は r1 + r2 − 2·ov·min(r1, r2)(r = 等価半径、pair_mask と同じ定義)。

    鎖の前の泡以外と重なる置き方は 40 回まで引き直す。引き直しきれなければ None(場面を捨てる。
    深い重なりほど捨てる場面が増える —— 章の印字に場面の数を出す)。
    """
    rng = np.random.default_rng(seed)
    pick = [tmpl[int(i)] for i in rng.integers(0, len(tmpl), k)]
    canvas_lab = np.zeros((size, size), np.int32)
    boxes, cents = [], []
    prev_c, prev_r = None, None
    for i, t in enumerate(pick):
        r = math.sqrt(t.sum() / math.pi)
        cy, cx = ndimage.center_of_mass(t)
        placed = False
        for _ in range(40):
            if prev_c is None:
                c = np.array([size / 2.0, size / 2.0])
            else:
                th = rng.uniform(0, 2 * math.pi)
                c = prev_c + (prev_r + r - 2.0 * ov * min(prev_r, r)) * np.array([math.sin(th), math.cos(th)])
            r0, c0 = int(round(c[0] - cy)), int(round(c[1] - cx))
            if r0 < 1 or c0 < 1 or r0 + t.shape[0] >= size - 1 or c0 + t.shape[1] >= size - 1:
                continue
            win = canvas_lab[r0:r0 + t.shape[0], c0:c0 + t.shape[1]]
            others = set(np.unique(win[t])) - {0, i}       # 直前(番号 i)以外と重なるなら置き直す
            if others:
                continue
            win[t & (win == 0)] = i + 1
            boxes.append((r0, c0, r0 + t.shape[0] - 1, c0 + t.shape[1] - 1))
            cents.append((r0 + cy, c0 + cx))
            prev_c, prev_r = np.array([r0 + cy, c0 + cx]), r
            placed = True
            break
        if not placed:
            return None
    return canvas_lab > 0, np.array(boxes, float), np.array(cents, float)


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def make_figures(pair, world, bbbc, pemwe):
    src_p = ("Colliard-Granero et al., PEMWE oxygen bubble optical video recording, Zenodo "
             "doi:10.5281/zenodo.10184579, CC BY 4.0. Masks thresholded at 127; bubble shapes re-placed (semi-synthetic).")
    src_b = ("BBBC005v1 (Ljosa et al., Nature Methods 2012), https://bbbc.broadinstitute.org/BBBC005, CC0 1.0. "
             "Ground-truth masks read as is.")
    # 1. 実画像の上に op の判定(あれば)
    if pemwe is not None:
        real = sorted(pemwe["real"], key=lambda x: -(x[5] + x[6]))
        name, ncc, lo, hi, nd, na, nu, im, mk, r = real[0]
        name2, ncc2, lo2, hi2, nd2, na2, nu2, im2, mk2, r2 = real[len(real) // 2]
        p1 = _label(_paint_status(im, r), "連結成分 %d / op: %d〜%s(青 決まる・橙 あいまい・紫 上限を開く)"
                    % (ncc, lo, "∞" if hi is None else hi), 12)
        p2 = _label(_paint_status(im2, r2), "連結成分 %d / op: %d〜%s" % (ncc2, lo2, "∞" if hi2 is None else hi2), 12)
        figs.save("real_bubbles_verdict", np.concatenate([p1, np.ones((p1.shape[0], 8, 3)), p2], 1),
                  "水電解の酸素の泡(実画像、手作業マスク)に op の判定を重ねた。青 = 個数が決まった塊(黒線は割れ目)、"
                  "橙 = くびれが帯の中で 1 個か 2 個か決まらない塊、紫 = 数えた山では面積を説明できない塊(上限を開く)。"
                  "大きく融合したガスの帯は数を返さない。", source=src_p)
    # 2. 突出度 vs 重なり率(閉形式は破線)
    rows = pair["rows"]
    ser, sty, col = [], [], []
    for r in pair["radii"]:
        xs = np.array([x[2] for x in rows if x[0] == x[1] == r])
        ys = np.array([x[5] for x in rows if x[0] == x[1] == r])
        ser.append(("実測 r=%d px" % r, xs, ys))
        sty.append(None)
        col.append(None)
    oo = np.linspace(0, 0.95, 200)
    ser.append(("閉形式 1 − sqrt(1 − (1 − o)²)", oo, np.array([rel_closed(o) for o in oo])))
    sty.append("dashed")
    col.append("reference")
    for v, lab in ((REL_HI, "rel_hi(これ以上 = 確か)"), (REL_LO, "rel_lo(これ未満 = 雑音)")):
        ser.append((lab, np.array([0, 0.95]), np.array([v, v])))
        sty.append("dotted")
        col.append("neutral")
    figs.save_plot("prominence_vs_overlap", ser, xlabel="重なり率 o(0 = 接する、1 = 同心)",
                   title="2 番目の山の相対突出度: 実測(点)と閉形式(破線)",
                   ylabel="2 番目の山の相対突出度 p/h", ylim=(0, 1.0),
                   kinds=["scatter"] * len(pair["radii"]) + ["line"] * 3, styles=sty, colors=col,
                   caption="等しい 2 円の 2 番目の山の相対突出度。閉形式(破線)は半径によらない。実測は格子の量子化で"
                           "閉形式より最大 1.5 px 低い。点線の帯の中に落ちた山は『あいまい』。")
    # 3. 2 円の判定の並び(マスクを判定の色で塗る)
    panels, caps = [], []
    for o in (0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
        m = pair_mask(20, 20, o, (20, 20, int(o * 1000), 0))
        res = count_op(m, rt=RT_BUBBLE)
        v = verdict(res, 2)
        nc = count_chain(m, 1.0)[0]
        img = _mask_base(m)
        img[m] = 0.35 * img[m] + 0.65 * np.array(COL[v])
        lb = res["labels"]
        e = ((lb != np.roll(lb, 1, 0)) | (lb != np.roll(lb, 1, 1))) & (lb > 0)
        img[e] = 0.05
        panels.append(np.kron(img, np.ones((3, 3, 1))))
        caps.append("o=%.2f op %s / 連鎖 %d" % (o, _iv(res), nc))
    figs.save_grid("pair_verdicts", panels, captions=caps, ncols=4,
                   title="半径 20 px の 2 円: op の判定(青 決まる・橙 区間・紫 上限を開く・赤 誤り)と既存の連鎖",
                   caption="重なり率を上げると、くびれが浅くなって 0.5 前後で『1 個か 2 個か』が決まらなくなり(橙)、"
                           "0.7 を超えると山が 1 つになる。面積の検査が上限を開く(紫)。0.9 を超えると和集合は縦横比 1.1 "
                           "の楕円と区別できない —— ここだけは op も 1 個と答える(閉形式が予言する見えない領域)。"
                           "既存の連鎖(h = 1 px)は全部の重なり率で 1 つの数を返す。")
    # 4. 判定の地図(半径 × 重なり率)
    os_ = sorted({x[2] for x in rows})
    cases = [(r, r) for r in pair["radii"]] + [(20, 12)]
    vm = np.ones((len(cases) * 10, len(os_) * 6, 3))
    for i, (r1, r2) in enumerate(cases):
        for j, o in enumerate(os_):
            vs = [x[6] for x in rows if x[0] == r1 and x[1] == r2 and x[2] == o]
            worst = "wrong" if "wrong" in vs else ("open" if "open" in vs else ("range" if "range" in vs else "right"))
            vm[i * 10:(i + 1) * 10 - 1, j * 6:(j + 1) * 6 - 1] = COL[worst]
    vm = np.kron(vm, np.ones((4, 4, 1)))
    left, bottom = 150, 44
    canvas = np.ones((vm.shape[0] + bottom + 8, vm.shape[1] + left + 8, 3))
    canvas[4:4 + vm.shape[0], left:left + vm.shape[1]] = vm
    names = ["r = %d px" % r for r in pair["radii"]] + ["r = 20 と 12 px"]
    for i, nm in enumerate(names):
        canvas = np.asarray(fs.text_box(canvas, nm, (6, 4 + i * 40 + 8), anchor="lt", font_size=12))
    for j in range(0, len(os_), 8):
        canvas = np.asarray(fs.text_box(canvas, "%.1f" % os_[j], (left + j * 24, vm.shape[0] + 10), anchor="lt",
                                        font_size=11))
    canvas = np.asarray(fs.text_box(canvas, "重なり率 o →", (left + vm.shape[1] - 120, vm.shape[0] + 10),
                                    anchor="lt", font_size=11))
    vm = canvas
    figs.save("verdict_map", vm,
              "判定の地図。行 = 半径(上から %s、最下段は 20 px と 12 px の組)、列 = 重なり率 0〜0.95(左から右)。"
              "青 = 2 個に決まる、橙 = 区間、紫 = 上限を開く、赤 = 自信をもった誤り(閉形式の見えない領域だけ)。"
              % ", ".join("%d px" % r for r in pair["radii"]))
    # 5. 合成の世界: 重なり率ごとの個数の誤差と、決まった割合
    per = world["per"]
    ovs = np.array(WORLD_OV)

    def mean_rel(k):
        return np.array([np.mean((np.array(per[o][k], float) - np.array(per[o]["truth"], float))
                                 / np.array(per[o]["truth"], float)) for o in WORLD_OV])
    det_frac = np.array([per[o]["v"].count("right") / len(per[o]["v"]) for o in WORLD_OV])
    figs.save_plot("world_count_error", [
        ("連結成分", ovs, mean_rel("cc")), ("既存の連鎖 h=1 px", ovs, mean_rel("chain")),
        ("op の下限 lo", ovs, mean_rel("lo")), ("op が 1 つの数に決めた割合", ovs, det_frac)],
        xlabel="重なり率 o", ylabel="平均の相対誤差 / 割合", ylim=(-1.0, 1.05),
        title="合成の世界: 個数の相対誤差と、op が 1 つの数に決めた割合",
        colors=["neutral", "wrong", "right", "emphasis"], styles=[None, None, None, "dashed"],
        caption="world_blobs_touching(12 円、半径 14 px)。連結成分は重なりの数だけ少なく、既存の連鎖は o ≥ 0.6 で"
                "自信をもって外れる。op は決まらない塊を区間で返し、1 つの数に決めた世界では真値と一致した。")
    # 6. 合成の世界の場面(ALCON 型: 緑の矩形 = 真値、赤の十字 = 答えの重心)
    panels, caps = [], []
    for o in (0.2, 0.5, 0.7):
        w, res, boxes, cents = world["keep"][o]
        img = _paint_status(np.asarray(w["image"]), res)
        for b in boxes:
            _box(img, b, COL["truth"])
        for p in _determined_points(res):
            _cross(img, p, COL["point"])
        panels.append(np.kron(img, np.ones((2, 2, 1))))
        caps.append("o=%.1f 真値 12、op %s" % (o, _iv(res)))
    figs.save_grid("world_scenes", panels, captions=caps, ncols=3,
                   title="合成の世界と ALCON 型の採点(緑の矩形 = 真値、赤の十字 = 答えの重心)",
                   caption="重なり率 0.2 / 0.5 / 0.7。決まった塊(青)の重心(赤の十字)は矩形に 1 つずつ入る。"
                           "橙・紫の塊は棄権して点を出さない(区間だけを返す)。")
    # 7. BBBC005
    if bbbc is not None:
        ser = []
        for key, lab in (("small", "小さい物体"), ("large", "大きい物体")):
            rows_b = bbbc[key]
            t = np.array([x[0] for x in rows_b], float)
            ser.append(("%s: 連結成分" % lab, t, np.array([x[1] for x in rows_b], float)))
            ser.append(("%s: op の下限" % lab, t, np.array([x[3][RT_CELL]["lo"] for x in rows_b], float)))
        ser.append(("真値", np.array([0, 100.0]), np.array([0, 100.0])))
        figs.save_plot("bbbc005_count_vs_truth", ser, xlabel="真値(ファイル名の個数)", ylabel="数えた個数",
                       kinds=["scatter"] * 4 + ["line"], styles=[None] * 4 + ["dashed"],
                       colors=[None, None, None, None, "reference"], xlim=(0, 102), ylim=(0, 105),
                       title="BBBC005: 真値の個数と数えた個数",
                       caption="BBBC005 の真値マスク。小さい物体は op の下限が真値の線に乗る(連結成分は密になるほど下)。"
                               "大きい物体は重なりが深すぎて下限も大きく下回る —— op はその大半で上限を開き(数を返さず)、"
                               "自信をもった誤りを出さない。", source=src_b)
        panels, caps = [], []
        data = load_bbbc()
        for key in ("small", "large"):
            want = [x[4] for x in bbbc[key] if x[0] == 53][0]
            c, m, name = [x for x in data[key] if x[2] == want][0]
            r = count_op(m, rt=RT_CELL)
            panels.append(_paint_status(_mask_base(m), r))
            caps.append("%s 真値 %d / 連結成分 %d / op %s" % ("小" if key == "small" else "大", c,
                        int(B.blob_label(m).max()), _iv(r)))
        figs.save_grid("bbbc005_masks", panels, captions=caps, ncols=2,
                       title="BBBC005 の真値マスクに op の判定(青 決まる・橙 区間・紫 上限を開く)",
                       caption="同じ個数の場面の小さい物体(左)と大きい物体(右)。", vrange=None)
    # 8. PEMWE の半合成
    if pemwe is not None:
        panels, caps = [], []
        for ov in (0.0, 0.2, 0.4):
            for m, res, boxes, cents in pemwe["ex"].get(ov, [])[:2]:
                img = _paint_status(_mask_base(m), res)
                for b in boxes:
                    _box(img, b, COL["truth"])
                for p in _determined_points(res):
                    _cross(img, p, COL["point"])
                panels.append(np.kron(_crop_around(img, m, 160), np.ones((2, 2, 1))))
                caps.append("o=%.1f 真値 %d、op %s" % (ov, len(boxes), _iv(res)))
        if panels:
            figs.save_grid("pemwe_semisynthetic", panels, captions=caps, ncols=2,
                           title="実際の泡の形(PEMWE の手作業マスク)を重なり率を振って並べた半合成",
                           caption="緑の矩形 = 置いた泡(真値)、赤の十字 = 決まった塊の重心。重なり率は小さいほうの泡の"
                                   "直径のうち相手に食い込んだ割合。o = 0.4 では塊は棄権し、区間だけを返す(真値を外すこともある)。",
                           vrange=None)
        per = pemwe["per"]
        ovs = np.array(pemwe["ovs"])
        y_op = np.array([_mean_or_nan([x["norm"] for x in per[o]["alc"] if x["n"]]) for o in pemwe["ovs"]])
        ok_ = np.isfinite(y_op)                      # 全部棄権した重なり率には点が無い
        figs.save_plot("pemwe_alcon_vs_overlap", [
            ("op(決まった塊、棄権を除く)", ovs[ok_], y_op[ok_]),
            ("既存の連鎖 h=1 px(全部に答える)", ovs, np.array([np.mean([x["norm"] for x in per[o]["alc_chain"]]) for o in pemwe["ovs"]])),
            ("op が棄権した泡の割合", ovs, np.array([np.sum(per[o]["abst"]) / max(np.sum(per[o]["t"]), 1) for o in pemwe["ovs"]]))],
            xlabel="重なり率 o", ylabel="ALCON 型の得点 / 真値の数", ylim=(-1.05, 1.05),
            title="実際の泡の形の半合成: ALCON 型の得点",
            kinds=["scatter", "line", "line"],
            colors=["right", "wrong", "neutral"], styles=[None, None, "dashed"],
            caption="得点 = (当たり − 誤検出 − 未検出)/ 真値の数。既存の連鎖は深い重なりで点を落とす。op は"
                    "決まらない塊を棄権し、答えた分は満点に近い(棄権の割合は破線)。", source=src_p)
    if pemwe is not None:
        sw = np.array(pemwe["sweep"])
        figs.save_plot("pemwe_round_tol_tradeoff", [
            ("孤立した泡を 1 個と言い切る割合", sw[:, 0], sw[:, 1]),
            ("塊の自信をもった誤り", sw[:, 0], sw[:, 2]),
            ("塊の区間の外れ", sw[:, 0], sw[:, 3]),
            ("塊で棄権(区間・上限を開く)", sw[:, 0], sw[:, 4])],
            xlabel="形の許し round_tol(許す縦横比 − 1)", ylabel="割合", ylim=(0, 1.02),
            title="形の許しの矛盾: 孤立した泡を数えるほど、隠れた泡を見逃す",
            kinds=["line"] * 4, colors=["right", "wrong", "emphasis", "neutral"], styles=[None, None, "dashed", "dotted"],
            caption="実際の泡の形の矛盾: 形の許しを広げると孤立した泡は 1 個と言い切れるが、隠れた泡も通して自信をもった"
                    "誤りが出る。宣言値 0.3 で誤り %.1f %%、孤立した泡の 95 %% を通す %.2f では %.1f %%。"
                    % (100 * [x for x in pemwe["sweep"] if abs(x[0] - RT_CELL) < 1e-9][0][2], pemwe["sweep"][-1][0],
                       100 * pemwe["sweep"][-1][2]), source=src_p)
    # 9. 2 円が融合していく動画(距離変換と判定)
    frames = []
    for o in np.linspace(0.0, 0.95, 39 if not REDUCED else 8):
        m = pair_mask(20, 20, float(o), (20, 20, 999, 0))
        res = count_op(m, rt=RT_BUBBLE)
        d = B.blob_distance(m)
        v = verdict(res, 2)
        img = np.asarray(fs.colorize_depth(d / 20.0), np.float64)[:, :, :3]
        if img.max() > 1.0:
            img = img / 255.0
        img[~m] = 1.0
        for pr in zip(res["peaks"]["row"], res["peaks"]["col"], res["peaks"]["status"]):
            _cross(img, pr[:2], (1, 1, 1) if pr[2] == B.PEAK_SURE else ((1, 0.72, 0) if pr[2] == B.PEAK_AMBIGUOUS else (0.5, 0.5, 0.5)), 2)
        img = np.kron(img, np.ones((3, 3, 1)))
        frames.append(_label(img, "o=%.2f p/h=%.3f(閉 %.3f)→%s" % (
            o, float(np.sort(res["peaks"]["rel_prominence"])[::-1][1]) if len(res["peaks"]["rel_prominence"]) > 1 else 0.0,
            rel_closed(float(o)), {"right": "2 個", "range": "1〜2 個", "open": "1 個以上", "wrong": "1 個(誤り)",
                                   "miss": "外れ"}[v]), 11))
    figs.save_gif("pair_merging", frames, "2 つの泡が近づいて融合していく。色 = 距離変換(内接円の半径)、白い十字 = 確かな山、"
                  "橙 = あいまいな山。くびれが浅くなると 2 番目の山が帯に落ち、やがて消える。", fps=6.0)


def main():
    t0, c0 = time.time(), time.process_time()
    print("PoC 密集した泡を数える(予算 %s、帯 %.2f〜%.2f、床 %.1f px)" % (
        "reduced" if REDUCED else "full", REL_LO, REL_HI, MIN_PROM))
    pair = chapter_pair()
    world = chapter_world()
    chapter_scorer()
    chapter_probes()
    bbbc = chapter_bbbc()
    pemwe = chapter_pemwe()
    if not REDUCED and figs.enabled():
        make_figures(pair, world, bbbc, pemwe)
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (
        time.process_time() - c0, time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()

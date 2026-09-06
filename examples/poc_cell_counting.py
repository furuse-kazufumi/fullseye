# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""重なった細胞をどう数えるか —— 個数・過分割・過統合を別々に測る。

EXTEND: 実際の顕微鏡画像に差し替えるなら ``make_scene()`` が返す辞書の
``img``(観測画像)と ``owner``(画素ごとの「どの細胞のものか」ラベル)の対を、
撮影画像と手作業ラベルに置き換える。**真値はラベル画像だけでは足りない** ——
この PoC のいちばん重要な軸(どれとどれが重なっているか、隠れた面積はどれだけか)は
ラベル画像には残らないので、``cells`` 表(中心・長短径・傾き)も一緒に持つこと。
手作業で作れないなら、重なりの軸は測れないと正直に書くほうがよい。

この PoC が示すこと:

1. **ゼロ点(大津の二値化 + 連結成分)を先に測る** —— これに勝てない手法は採らない。
   実測ではゼロ点は重なりが増えるほど単調に下振れし、いちばん密な条件で
   個数を 3 割以上取りこぼす。取りこぼしの正体は全部「過統合」である。
2. ★**計数が合っていて分割が全部外れている点が実在する** —— 分水嶺の種の
   間引き量 h を振ると、過分割と過統合が逆向きに動くので **どこかで打ち消し合う**。
   その h では個数の偏りがほぼゼロになるのに、過分割と過統合はどちらも
   最悪付近のまま残る。**個数だけを報告していたら最良の設定として通る**。
3. **過分割と過統合は別々に数えないと見えない** —— 「分割誤り 20 件」と 1 つに
   まとめると、種を増やすべきか減らすべきかが決まらない。向きが逆の 2 つの
   欠陥なので、片方を減らすともう片方が増える。
4. **最適な h は密度で動く** —— 疎な場面で最適な h を固定したまま密な場面へ
   持っていくと壊れる。ここを実測して数字で出す。
5. **大きさが 3 倍違う集団が混ざると単一スケールの前提が壊れる** —— 距離変換の
   極大を種にする手法は、大きい細胞を割り、小さい細胞をまとめる。**同じ h で
   両方が同時に起きる**ので、h をどう選んでも直らない。
6. **縁で切れた細胞をどう数えるか**で計数が動く。数える / 数えない / 半分の
   3 通りを実測して差を出す。半分に数える規約(Gundersen 流の折衷)がいちばん
   偏りが小さいが、それは **真値の側も同じ規約で数えた場合だけ**である。
7. **面積は「見えている面積」までしか取れない** —— 重なった細胞の真の面積との
   差は、分割をどれだけ上手くやっても残る原理的な床である。

主な実測は実行時に印字される。★この PoC が出した fullseye の道具の穴は
末尾の「道具の穴」節と、親への報告に列挙してある。要点だけ:
(a) **2 次元の連結成分ラベリングと per-object の region props が facade に無い**
(3 次元の ``vol_label`` / ``vol_region_props`` はある)。(b) 進化 op の
``distance_transform`` は最大値で正規化するので **画素単位の距離が取れない**。
(c) ``xsk2_h_maxima`` は入力を ``[0,1]`` に切り詰めるうえ h を
``0.05 + 0.3a``(= 正規化画像に対する比)でしか振れず、**画素単位の h を
指定できない**。(d) ``circularity`` / ``eccentricity`` / ``area_center`` は
画像全体の 1 スカラーで、**物体ごとには取れない**。
"""
from __future__ import annotations

import time
import unicodedata

import numpy as np

import fullseye as fs          # ★先に fullseye を import すること(パスフックが
import volops                  #   リポジトリ直下を sys.path に足すので順序が要る)
import segmentation as fsseg   # noqa: F401  (2D watershed の所在を示すために保持)


# --------------------------------------------------------------------------- #
# 表示                                                                          #
# --------------------------------------------------------------------------- #
def _dw(s):
    """全角を 2 桁と数えた表示幅(str.format は文字数で数えるので桁が揃わない)。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def pad(s, n, right=True):
    """表示幅 ``n`` に詰める。``right`` なら右寄せ。"""
    s = str(s)
    sp = " " * max(0, n - _dw(s))
    return sp + s if right else s + sp


# --------------------------------------------------------------------------- #
# 標本の合成 —— 真値は全部こちらが握っている                                     #
# --------------------------------------------------------------------------- #
#: 画素数(正方)。
IMG = 288
#: 副画素の細分数。細胞は副画素格子に描いてから面積平均で画素へ落とす。
SS = 3
#: 細胞の平均の長半径 [画素]。短半径はこの ``AXIS_RATIO`` 倍。
R_BASE = 6.4
AXIS_RATIO = 0.78

#: 細胞の種別。**乱数で散らしただけの配置に頼らない**ための構造。
KIND_COLONY, KIND_CHAIN, KIND_LARGE, KIND_SINGLE, KIND_EDGE = 0, 1, 2, 3, 4
KIND_NAME = ("コロニー", "分裂鎖", "大型", "孤立", "縁")

#: 点像分布関数(PSF)のシグマ [画素]。``gauss_filter`` は ``sigma = 0.3 + 2.7a``。
PSF_SIGMA = 1.2
PSF_A = (PSF_SIGMA - 0.3) / 2.7

#: 既定の背景ムラの振幅と、既定の光子数スケール(ショット雑音の強さを決める)。
BG_AMP = 0.10
PHOTONS = 260.0
READ_NOISE = 0.010


def _hex_points(k, step, rng):
    """六方最密に近い格子上の ``k`` 点(中心付近から順に)。コロニーの骨格。

    乱数で散らすと隣接距離が指数分布になり、「重なり」が密度と一緒に動いてしまう。
    格子に置いて ``step`` だけを振れば、**個数を変えずに重なりだけ**を変えられる。
    """
    pts = []
    ring = 0
    while len(pts) < k:
        if ring == 0:
            pts.append((0.0, 0.0))
        else:
            for i in range(6 * ring):
                th = 2.0 * np.pi * i / (6 * ring)
                pts.append((ring * step * np.sin(th), ring * step * np.cos(th)))
        ring += 1
    pts = np.asarray(pts[:k], float)
    return pts + rng.normal(0.0, 0.09 * step, pts.shape)


def layout(seed, *, pack=1.05, size_ratio=2.0, n_colony=3, k_colony=10,
           n_chain=4, k_chain=3, n_large=8, n_single=20, n_edge=8):
    """細胞の一覧 ``(cy, cx, ra, rb, theta, bright, kind)`` を作る。

    ``pack`` が **重なりの強さ**(コロニー内の中心間距離 / 2ra)。1.5 で明らかに
    離れ、1.0 で接し、0.65 で深く重なる。**個数は ``pack`` に依らない**ので、
    この 1 つのノブで「重なりだけ」を振れる。``size_ratio`` は大型集団の線寸法。

    集団(コロニー / 鎖 / 大型 / 孤立)はそれぞれ **縄張りの円**を予約してから
    置く。乱数で撒くと、疎に設定したつもりでも集団どうしが偶然重なり、
    「pack を大きくしても重なりが減らない」という測れない場面になってしまう。
    """
    rng = np.random.default_rng(20260906 + 977 * seed)
    cells = []
    discs = []                      # 予約済みの縄張り (cy, cx, 半径)

    def reserve(rad, lo=0.05, hi=0.95, gap=3.0, tries=400, near_edge=False):
        """半径 ``rad`` の縄張りが空いている場所を探す。見つからなければ None。"""
        for _ in range(tries):
            if near_edge:
                side = int(rng.integers(4))
                t = rng.uniform(0.08 * IMG, 0.92 * IMG)
                off = rng.uniform(-0.55 * rad, 0.75 * rad)
                p = np.array(((off, t), (IMG - 1.0 - off, t),
                              (t, off), (t, IMG - 1.0 - off))[side])
            else:
                p = rng.uniform(lo * IMG, hi * IMG, 2)
            if all(np.hypot(p[0] - d[0], p[1] - d[1]) > rad + d[2] + gap for d in discs):
                discs.append((p[0], p[1], rad))
                return p
        return None

    def add(cy, cx, ra, rb, th, kind):
        cells.append((cy, cx, ra, rb, th, float(rng.uniform(0.55, 0.70)), kind))

    # (1) コロニー —— 六方格子に密集。pack で重なりが決まる。
    step = 2.0 * R_BASE * pack
    for _ in range(n_colony):
        offs = _hex_points(k_colony, step, rng)
        radii = R_BASE * rng.uniform(0.88, 1.12, len(offs))
        rad = float(np.max(np.hypot(offs[:, 0], offs[:, 1]) + radii))
        p = reserve(rad)
        if p is None:
            continue
        for (dy, dx), r in zip(offs, radii):
            add(p[0] + dy, p[1] + dx, r, r * AXIS_RATIO,
                rng.uniform(0, np.pi), KIND_COLONY)

    # (2) 分裂中の鎖 —— 中心間 1.05ra の亜鈴形。pack に依らず **常に重なっている**
    #     構造を 1 つ残しておく(疎な条件でも「重なりのある場面」が消えないように)。
    for _ in range(n_chain):
        th = rng.uniform(0, 2 * np.pi)
        r = R_BASE * rng.uniform(0.85, 1.05)
        offs, bends = [], []
        for j in range(k_chain):
            bend = 0.18 * rng.normal() * j
            d = 1.05 * r * j
            offs.append((d * np.sin(th + bend), d * np.cos(th + bend)))
            bends.append(bend)
        offs = np.asarray(offs) - np.mean(offs, 0)
        rad = float(np.max(np.hypot(offs[:, 0], offs[:, 1])) + r)
        p = reserve(rad)
        if p is None:
            continue
        for (dy, dx), bend in zip(offs, bends):
            add(p[0] + dy, p[1] + dx, r, r * AXIS_RATIO,
                th + bend + np.pi / 2, KIND_CHAIN)

    # (3) 大型集団 —— 線寸法 size_ratio 倍(面積は 2 乗倍)。単一スケールの前提を壊す。
    for _ in range(n_large):
        r = R_BASE * size_ratio * rng.uniform(0.9, 1.1)
        p = reserve(r)
        if p is None:
            continue
        add(p[0], p[1], r, r * AXIS_RATIO, rng.uniform(0, np.pi), KIND_LARGE)

    # (4) 孤立細胞 —— 縄張りを取るので「易しい」対照が必ず残る。
    for _ in range(n_single):
        r = R_BASE * rng.uniform(0.85, 1.15)
        p = reserve(r)
        if p is None:
            continue
        add(p[0], p[1], r, r * AXIS_RATIO, rng.uniform(0, np.pi), KIND_SINGLE)

    # (5) 縁で切れる細胞 —— 中心を画像の外側寄りに置き、**わざと半分だけ写す**。
    for _ in range(n_edge):
        r = R_BASE * rng.uniform(0.85, 1.15)
        p = reserve(r, near_edge=True)
        if p is None:
            continue
        add(p[0], p[1], r, r * AXIS_RATIO, rng.uniform(0, np.pi), KIND_EDGE)

    return cells, rng


def _paint(acc, owner, best, cy, cx, ra, rb, th, bright, ident):
    """副画素格子に楕円を 1 つ描く。``ident<0`` はデブリ(``owner`` に入れない)。

    重なった画素の帰属は **中心までの正規化距離が小さいほう** に決める(楕円計量の
    ボロノイ分割)。この規約を先に決めておかないと「2 つを 1 つにまとめた」を
    数える基準が定義できない —— 真値の側があいまいだと過統合は測れない。
    強度は加算(半透明)。実際の蛍光像でも重なりは明るくなる。
    """
    n = acc.shape[0]
    r = int(np.ceil(max(ra, rb) * SS)) + 2
    y0, y1 = max(0, int(cy * SS) - r), min(n, int(cy * SS) + r + 1)
    x0, x1 = max(0, int(cx * SS) - r), min(n, int(cx * SS) + r + 1)
    if y1 <= y0 or x1 <= x0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dy = yy / SS - cy
    dx = xx / SS - cx
    ct, st = np.cos(th), np.sin(th)
    u = dx * ct + dy * st
    v = -dx * st + dy * ct
    f = (u / ra) ** 2 + (v / rb) ** 2
    inside = f <= 1.0
    if not inside.any():
        return 0
    acc[y0:y1, x0:x1] += np.where(inside, bright * (1.0 - 0.22 * f), 0.0)
    if ident >= 0:
        sub_o = owner[y0:y1, x0:x1]
        sub_b = best[y0:y1, x0:x1]
        take = inside & (f < sub_b)
        sub_o[take] = ident
        sub_b[take] = f[take]
    return int(inside.sum())          # 他の細胞が無ければ見えたはずの副画素数


def make_scene(seed, *, pack=0.88, size_ratio=2.0, bg_amp=BG_AMP, photons=PHOTONS,
               read_noise=READ_NOISE, n_debris=22, n_frag=6, **kw):
    """1 枚の場面を合成して真値つきで返す。

    返す辞書:
      ``img``    観測画像 (IMG, IMG) —— PSF・背景ムラ・ショット雑音・読出雑音つき。
      ``owner``  画素ごとの帰属ラベル (IMG, IMG) int32。0 = 背景 / デブリ。
      ``cells``  細胞の一覧(中心・長短径・傾き・種別)。
      ``area_true``    真の面積 πab [画素²](重なりで隠れていても変わらない)。
      ``area_alone``   **他の細胞が無ければ**見えたはずの面積(= 画像内に入る楕円)。
      ``area_vis``     実際に見えている面積 [画素²](``owner`` の画素数)。
      ``occ``          他の細胞に隠された割合 = 1 - area_vis / area_alone。
                       ★画像の縁で切れたぶんは ``area_alone`` 側に織り込み済みで、
                       **重なりと縁を混ぜない**(混ぜると縁の細胞が全部「重なって
                       いる」ことになり、重なりのノブが測れなくなる)。
      ``on_edge``      画像の縁に掛かっているか。
    """
    cells, rng = layout(seed, pack=pack, size_ratio=size_ratio, **kw)
    n = IMG * SS
    acc = np.zeros((n, n), np.float32)
    owner = np.zeros((n, n), np.int32)
    best = np.full((n, n), np.inf, np.float32)
    alone = np.zeros(len(cells))
    for i, (cy, cx, ra, rb, th, br, _k) in enumerate(cells):
        alone[i] = _paint(acc, owner, best, cy, cx, ra, rb, th, br, i + 1) / (SS * SS)

    # デブリ —— 細胞ではないので owner には入れない。明るい微粒子と、暗く細長い破片。
    for _ in range(n_debris):
        r = rng.uniform(0.7, 1.8)
        _paint(acc, owner, best, *rng.uniform(2, IMG - 2, 2), r, r,
               0.0, 0.95, -1)
    for _ in range(n_frag):
        _paint(acc, owner, best, *rng.uniform(4, IMG - 4, 2),
               rng.uniform(2.0, 3.5), rng.uniform(0.6, 1.2),
               rng.uniform(0, np.pi), 0.45, -1)

    sig = acc.reshape(IMG, SS, IMG, SS).mean(axis=(1, 3)).astype(np.float64)
    own_px = owner[SS // 2::SS, SS // 2::SS].copy()

    # 背景ムラ(照明の傾き + 緩い縞)。**PSF の前に足す** —— 照明も光学系を通る。
    gy, gx = np.mgrid[0:IMG, 0:IMG] / float(IMG)
    bg = 0.05 + bg_amp * (0.35 + 0.65 * gy) * (0.5 + 0.5 * np.cos(2 * np.pi * (0.8 * gx - 0.15)))
    clean = fs.apply(sig + bg, "gauss_filter", a=PSF_A)

    # ショット雑音(光子計数)+ 読出雑音。photons が 1 画素あたりの換算光子数。
    nrng = np.random.default_rng(70000 + seed)
    img = nrng.poisson(np.clip(clean, 0.0, None) * photons) / photons
    img = img + nrng.normal(0.0, read_noise, img.shape)

    ncell = len(cells)
    area_true = np.asarray([np.pi * c[2] * c[3] for c in cells])
    area_vis = np.bincount(own_px.ravel(), minlength=ncell + 1)[1:].astype(float)
    on_edge = np.asarray([
        (c[0] - c[2] < 0) or (c[0] + c[2] > IMG - 1) or
        (c[1] - c[2] < 0) or (c[1] + c[2] > IMG - 1) for c in cells])
    occ = 1.0 - area_vis / np.maximum(alone, 1e-9)
    return {
        "img": img, "owner": own_px, "cells": cells, "n": ncell,
        "area_true": area_true, "area_alone": alone, "area_vis": area_vis,
        "occ": occ, "on_edge": on_edge,
        "kind": np.asarray([c[6] for c in cells]), "seed": seed,
    }


# --------------------------------------------------------------------------- #
# 道具の薄い包み —— fullseye 側に無い形のものはここで明示的に補う                 #
# --------------------------------------------------------------------------- #
def cc_label(mask):
    """2 次元の 8 連結ラベリング。

    ★道具の穴: fullseye の facade に **2 次元のラベリングが無い**。``fs.op`` 側の
    ``connect_and_holes`` / ``cv_cc_count`` / ``blob_count`` は **個数(1 スカラー)**
    しか返さず、``hx_region_to_label`` はラベル画像を返すが進化 op の規約で
    ``[0,1]`` に正規化されるので、ラベル番号が浮動小数の刻みになってしまう。
    ここでは 3 次元用の ``volops.vol_label`` に厚さ 1 のボリュームを渡している。
    26 近傍が面内では 8 連結に落ちるので結果は正しいが、**2 次元の道具ではない**。
    """
    lab, k = volops.vol_label(np.asarray(mask, bool)[None, :, :], connectivity=26)
    return lab[0], int(k)


def edt(mask):
    """画素単位のユークリッド距離変換。

    ★道具の穴: 進化 op の ``distance_transform`` / ``dist_transform`` / ``cv_dist``
    は **最大値で正規化して返す**ので、「中心まで何画素あるか」が取り出せない。
    h-maxima の h を画素で指定したい、面積から半径を推したい、といった用途では
    正規化された距離は使えない。ここも 3 次元用 ``vol_distance_transform`` を
    厚さ 1 で使っている。
    """
    return volops.vol_distance_transform(np.asarray(mask, bool)[None, :, :])[0]


def watershed(landscape, markers, mask):
    """マーカー制御分水嶺(2 次元)。

    ★道具の穴: 2 次元版 ``segmentation.watersheds_marker`` はモジュールには
    在るが ``fs.`` にも ``fs.ledger.`` にも **公開されていない**(``import
    segmentation`` で直に掴むしかない)。しかも mask 引数が無いので背景まで
    塗ってしまう。ここは mask を取れる ``volops.vol_watershed`` を厚さ 1 で使う。
    """
    return volops.vol_watershed(np.asarray(landscape, float)[None, :, :],
                                np.asarray(markers, np.int32)[None, :, :],
                                mask=np.asarray(mask, bool)[None, :, :])[0]


def h_maxima_seeds(d, h_px):
    """距離変換 ``d`` の h-maxima 種。``h_px`` は **画素単位**の間引き量。

    ★道具の穴: ``xsk2_h_maxima`` は (1) 入力を ``np.clip(v, 0, 1)`` で切り詰め、
    (2) h を ``0.05 + 0.3a`` = **正規化画像に対する比** でしか振れない。距離変換は
    画素単位なので、ここでは ``d / D0`` に割ってから渡し、``a`` を逆算している。
    ``D0`` は ``d.max()`` 以上かつ ``h_px / 0.35`` 以上でなければならず、
    **h_px が ``0.05 * d.max()`` より小さいと表現できない**(下限に張り付く)。
    """
    dmax = float(d.max())
    if dmax <= 0:
        return np.zeros_like(d, np.int32), 0, 0.0
    d0 = max(dmax * 1.001, h_px / 0.35)
    a = (h_px / d0 - 0.05) / 0.3
    a_clip = float(np.clip(a, 0.0, 1.0))
    m = fs.apply(np.clip(d / d0, 0.0, 1.0), "xsk2_h_maxima", a=a_clip)
    lab, k = cc_label(m > 0.5)
    return lab, k, (0.05 + 0.3 * a_clip) * d0        # 実際に効いた h [画素]


def moment_ellipse(ys, xs):
    """画素集合の 2 次中心モーメントから長短半径 ``(ra, rb)`` と傾きを出す。

    塗り潰した楕円なら ``ra = 2 sqrt(λ1)`` がちょうど長半径になる。
    ★道具の穴: fullseye の ``circularity`` / ``eccentricity`` / ``area_center`` /
    ``moments_region_2nd`` は **画像全体を 1 つの領域として 1 スカラー**を返す
    進化 op なので、**物体ごとの形状量が取れない**(3 次元の
    ``vol_region_props`` は per-object で返すのに、2 次元にはそれが無い)。
    """
    if ys.size < 3:
        return 0.5, 0.5, 0.0
    y = ys - ys.mean()
    x = xs - xs.mean()
    cov = np.array([[float((y * y).mean()), float((y * x).mean())],
                    [float((y * x).mean()), float((x * x).mean())]])
    w, v = np.linalg.eigh(cov)
    w = np.clip(w, 1e-9, None)
    ra, rb = 2.0 * np.sqrt(w[1]), 2.0 * np.sqrt(w[0])
    ang = float(np.arctan2(v[1, 1], v[0, 1]))
    return float(ra), float(rb), ang


def per_object(labels, k):
    """ラベル画像から物体ごとの (面積, 充填率, ra, rb, 縁接触) を返す。

    充填率 = 面積 / (π ra rb)。塗り潰した 1 個の楕円なら 1.0、亜鈴形(2 個が
    くっついたもの)なら 0.6〜0.8 に落ちる —— これが「形の事前知識」の中身。
    """
    if k == 0:
        return {}
    flat = labels.ravel()
    order = np.argsort(flat, kind="stable")
    sf = flat[order]
    starts = np.searchsorted(sf, np.arange(k + 2))
    H, W = labels.shape
    out = {}
    for i in range(1, k + 1):
        idx = order[starts[i]:starts[i + 1]]
        if idx.size == 0:
            continue
        ys, xs = np.divmod(idx, W)
        ra, rb, ang = moment_ellipse(ys.astype(float), xs.astype(float))
        a = float(idx.size)
        out[i] = {"area": a, "fill": a / max(np.pi * ra * rb, 1e-9),
                  "ra": ra, "rb": rb, "ang": ang,
                  "edge": bool(ys.min() == 0 or xs.min() == 0
                               or ys.max() == H - 1 or xs.max() == W - 1),
                  "cy": float(ys.mean()), "cx": float(xs.mean())}
    return out


# --------------------------------------------------------------------------- #
# 手法 —— どれも「ラベル画像」を返す                                             #
# --------------------------------------------------------------------------- #
def foreground(img, op="sk_otsu"):
    """全手法で共有する前景マスク(大津 + 穴埋め)。

    **わざと共有する** —— こうすると手法間の差が「分け方」だけになり、閾値の
    良し悪しと混ざらない。閾値そのものの崖は雑音・背景ムラの節で別に測る。
    """
    b = fs.apply(np.asarray(img, np.float64), op) > 0.5
    return fs.apply(b.astype(np.float64), "fill_holes") > 0.5


def m_cc(img, fg=None):
    """ゼロ点 —— 大津 + 連結成分。触れ合った細胞は 1 個になる。"""
    fg = foreground(img) if fg is None else fg
    return cc_label(fg)[0]


def m_ws_all(img, fg=None):
    """距離変換 + 分水嶺(局所極大を全部種にする)。間引きをしないので過分割側。"""
    fg = foreground(img) if fg is None else fg
    d = edt(fg)
    pk = volops.vol_local_maxima(d[None, :, :], 1)
    seed = np.zeros_like(fg, bool)
    if len(pk):
        seed[np.asarray(pk)[:, 1], np.asarray(pk)[:, 2]] = True
    mk, k = cc_label(seed)          # 平坦な尾根は 1 つの種にまとめる
    if k == 0:
        return cc_label(fg)[0]
    return watershed(-d, mk, fg)


def m_ws_h(img, fg=None, h_px=2.4):
    """h-maxima で種を間引いてから分水嶺。``h_px`` が過分割/過統合のノブ。"""
    fg = foreground(img) if fg is None else fg
    d = edt(fg)
    mk, k, _h = h_maxima_seeds(d, h_px)
    if k == 0:
        return cc_label(fg)[0]
    return watershed(-d, mk, fg)


#: 形の事前知識のしきい値。充填率がこれ以上なら「1 個の楕円」とみなして割らない。
FILL_KEEP = 0.86
#: デブリ棄却の面積下限 [画素²]。細胞の面積の 1/4 を目安にする。
AREA_MIN_FRAC = 0.25


def _ref_area(props):
    """場面から「細胞 1 個ぶんの面積」を自己校正する。

    充填率が高い(= 1 個に見える)連結成分の面積の中央値を使う。外から与えると
    「答えを教えている」ことになるので、**画像だけから推す**。
    """
    good = [p["area"] for p in props.values() if p["fill"] >= 0.92 and p["area"] > 12]
    return float(np.median(good)) if good else 100.0


def m_shape(img, fg=None, h_px=2.4):
    """形の事前知識を使う —— 充填率と面積で「割るべき連結成分」だけを割る。

    1. 連結成分を取り、モーメント楕円の充填率と面積を出す。
    2. 面積が細胞 1 個ぶんの 1/4 未満なら **デブリとして棄てる**。
    3. 充填率が高く、面積も 1 個ぶんなら **そのまま**(分水嶺に掛けない)。
    4. そうでないものは、面積から推した個数 ``k = round(面積 / 1 個ぶん)`` に
       届くまで h を下げながら分水嶺を掛ける。★この「期待した個数まで割る」が
       単一スケールの前提そのもので、大きさが 3 倍違う集団が混ざると **大型細胞を
       ``k`` 個に割ってしまう**(崖 (b))。
    """
    fg = foreground(img) if fg is None else fg
    lab, k = cc_label(fg)
    props = per_object(lab, k)
    aref = _ref_area(props)
    out = np.zeros_like(lab)
    nxt = 0
    for i, p in props.items():
        if p["area"] < AREA_MIN_FRAC * aref:
            continue                                    # デブリ
        sel = lab == i
        kest = max(1, int(round(p["area"] / aref)))
        if p["fill"] >= FILL_KEEP and kest == 1:
            nxt += 1
            out[sel] = nxt
            continue
        ys, xs = np.nonzero(sel)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        sub = sel[y0:y1, x0:x1]
        d = edt(sub)
        w = None
        for hh in (h_px, 0.6 * h_px, 0.35 * h_px):
            mk, kk, _h = h_maxima_seeds(d, hh)
            if kk == 0:
                continue
            w = watershed(-d, mk, sub)
            if kk >= kest:
                break
        if w is None:
            w = cc_label(sub)[0]
        for j in range(1, int(w.max()) + 1):
            m = w == j
            if m.any():
                nxt += 1
                out[y0:y1, x0:x1][m] = nxt
    return out


def count_by_area(img, fg=None):
    """分割せず面積割りで **個数だけ** を出す(ラベルは返さない)。

    分割の質を一切問わない対照。個数だけ見るなら分割は要らない、という主張を
    数字で置いておくためのもの。
    """
    fg = foreground(img) if fg is None else fg
    lab, k = cc_label(fg)
    props = per_object(lab, k)
    aref = _ref_area(props)
    tot = sum(p["area"] for p in props.values() if p["area"] >= AREA_MIN_FRAC * aref)
    return int(round(tot / max(aref, 1e-9)))


# --------------------------------------------------------------------------- #
# 指標 —— 個数 / 過分割 / 過統合を **別々に**                                    #
# --------------------------------------------------------------------------- #
#: 「有意に重なっている」の下限。真値細胞の見えている面積のこの割合以上を
#: 覆っていれば、その予測ラベルはその細胞に触れているとみなす。
TAU = 0.25


def evaluate(scene, pred, tau=TAU):
    """真値と予測のラベル画像を突き合わせて、欠陥を **向きごとに** 数える。

    重なり行列 ``O[g, p]`` を作り、``O[g,p] >= tau * (g の見えている面積)`` を
    「有意」とする。同じ有意行列から:
      過分割 = Σ_g max(0, (g に触れた予測ラベル数) - 1)
      過統合 = Σ_p max(0, (p が触れた真値細胞数) - 1)
    が出る。**1 つの数にまとめない** —— 向きが逆の 2 つの欠陥で、片方を減らすと
    もう片方が増えるため、合計を見ても種の間引き量をどちらへ動かせばよいか
    決まらない。
    """
    gt = scene["owner"]
    ng = scene["n"]
    pred = np.asarray(pred, np.int64)
    npred = int(pred.max())
    if npred == 0:
        z = np.zeros(ng, int)
        return {"n_pred": 0, "split": 0, "merge": 0, "missed": ng, "spurious": 0,
                "one2one": [], "n_gt": ng, "per_gt": z, "per_pred": np.zeros(0, int)}
    O = np.bincount((gt.ravel().astype(np.int64) * (npred + 1) + pred.ravel()),
                    minlength=(ng + 1) * (npred + 1)).reshape(ng + 1, npred + 1)
    core = O[1:, 1:].astype(float)                      # 真値細胞 x 予測ラベル
    avis = np.maximum(core.sum(1) + O[1:, 0], 1.0)      # 見えている面積
    sig = core >= tau * avis[:, None]
    per_gt = sig.sum(1)
    per_pred = sig.sum(0)
    one2one = [(g, int(np.argmax(sig[g])) + 1)
               for g in range(ng)
               if per_gt[g] == 1 and per_pred[int(np.argmax(sig[g]))] == 1]
    # 「この予測ラベルは主にどの真値細胞のものか」= 過統合を細胞の種別へ配りたいとき用
    owner_of_pred = np.where(sig.any(0), np.argmax(core, 0), -1)
    return {
        "n_pred": npred, "n_gt": ng,
        "split": int(np.maximum(per_gt - 1, 0).sum()),
        "merge": int(np.maximum(per_pred - 1, 0).sum()),
        "missed": int((per_gt == 0).sum()),
        "spurious": int((per_pred == 0).sum()),
        "one2one": one2one, "per_gt": per_gt, "per_pred": per_pred,
        "sig": sig, "owner_of_pred": owner_of_pred,
    }


def summarize(rows):
    """複数枚の結果を「偏り」と「散らばり」に分けてまとめる。**混ぜない**。"""
    err = np.asarray([r["n_pred"] - r["n_gt"] for r in rows], float)
    return {
        "bias": float(err.mean()), "scatter": float(err.std()),
        "split": float(np.mean([r["split"] for r in rows])),
        "merge": float(np.mean([r["merge"] for r in rows])),
        "missed": float(np.mean([r["missed"] for r in rows])),
        "spurious": float(np.mean([r["spurious"] for r in rows])),
        "n_gt": float(np.mean([r["n_gt"] for r in rows])),
        "one2one": float(np.mean([len(r["one2one"]) for r in rows])),
    }


# --------------------------------------------------------------------------- #
def main():
    t0 = time.perf_counter()
    SEEDS = (0, 1, 2)
    #: 重なりの強さ(コロニー内の中心間距離 / 2ra)。個数は変えずにこれだけ振る。
    PACKS = (1.50, 1.25, 1.05, 0.85, 0.65)
    BASE_PACK = 1.05
    SPARSE, MID, DENSE = PACKS[0], PACKS[2], PACKS[-1]

    print("=== 1. 何を作ったか(真値は全部こちらが握っている)===")
    base = {p: [make_scene(s, pack=p) for s in SEEDS] for p in PACKS}
    sc0 = base[BASE_PACK][0]
    print(f"  {IMG}x{IMG} 画素、副画素 {SS}x{SS} で描いてから面積平均。"
          f"PSF シグマ {PSF_SIGMA} 画素、")
    print(f"  背景ムラ振幅 {BG_AMP}、光子数 {PHOTONS:.0f}/画素(ショット雑音)、"
          f"読出雑音 {READ_NOISE}。")
    print("  " + pad("種別", 12, right=False) + pad("個数", 8) + pad("長半径 [px]", 14)
          + pad("真の面積", 12) + pad("見えている", 12) + pad("隠れた割合", 12))
    kd = sc0["kind"]
    for k in range(5):
        m = kd == k
        if not m.any():
            continue
        print("  " + pad(KIND_NAME[k], 12, right=False) + pad(f"{int(m.sum())}", 8)
              + pad(f"{np.mean([c[2] for c, t in zip(sc0['cells'], m) if t]):.1f}", 14)
              + pad(f"{sc0['area_true'][m].mean():.0f}", 12)
              + pad(f"{sc0['area_vis'][m].mean():.0f}", 12)
              + pad(f"{100 * sc0['occ'][m].mean():.1f} %", 12))
    print(f"  合計 {sc0['n']} 個 + デブリ(明るい微粒子 22 + 暗い破片 6、"
          f"**細胞ではない**)。")
    print("  " + pad("重なり pack", 14, right=False) + pad("細胞数", 9)
          + pad("重なった細胞の割合", 22) + pad("平均で隠れた割合", 20)
          + pad("前景の連結成分数", 20))
    occ_tab = {}
    for p in PACKS:
        occ = np.concatenate([s["occ"] for s in base[p]])
        ncc = np.mean([cc_label(foreground(s["img"]))[1] for s in base[p]])
        occ_tab[p] = (float(np.mean(occ > 0.02)), float(occ.mean()), float(ncc))
        print("  " + pad(f"{p:.2f}", 14, right=False)
              + pad(f"{base[p][0]['n']}", 9)
              + pad(f"{100 * occ_tab[p][0]:.1f} %", 22)
              + pad(f"{100 * occ_tab[p][1]:.1f} %", 20)
              + pad(f"{ncc:.0f}", 20))
    print("  → **細胞数は pack に依らず一定**なので、この 1 列で『重なりだけ』を")
    print("     振れている。前景の連結成分数(右端)は重なりとともに減る = 触れ合った")
    print("     細胞が 1 塊になっていく。ここがゼロ点の失点そのもの。")

    print("\n=== 2. ゼロ点を先に測る —— 大津 + 連結成分 ===")
    print("  " + pad("重なり pack", 14, right=False) + pad("真の個数", 10)
          + pad("推定", 8) + pad("偏り", 9) + pad("散らばり", 11)
          + pad("過分割", 9) + pad("過統合", 9) + pad("取りこぼし", 12)
          + pad("偽物", 8))
    zero = {}
    for p in PACKS:
        rows = [evaluate(s, m_cc(s["img"])) for s in base[p]]
        zero[p] = summarize(rows)
        z = zero[p]
        print("  " + pad(f"{p:.2f}", 14, right=False) + pad(f"{z['n_gt']:.0f}", 10)
              + pad(f"{z['n_gt'] + z['bias']:.0f}", 8) + pad(f"{z['bias']:+.1f}", 9)
              + pad(f"{z['scatter']:.1f}", 11) + pad(f"{z['split']:.1f}", 9)
              + pad(f"{z['merge']:.1f}", 9) + pad(f"{z['missed']:.1f}", 12)
              + pad(f"{z['spurious']:.1f}", 8))
    print("  → ゼロ点の偏りは **重なりとともに単調に下振れ**する。散らばりは小さいので")
    print("     枚数を増やしても消えない。失点はほぼ全部が **過統合** で、過分割は")
    print("     ゼロに近い(切る仕掛けが無いので当然)。「偽物」はデブリを数えたぶん。")
    print("  → ★注意: **過統合 ≠ 取りこぼし** である。2 個を 1 個にまとめると個数は")
    print("     1 しか減らないが、過統合の件数は 1、取りこぼし(有意に触れた予測ラベルが")
    print("     1 つも無い細胞)は 0 のまま。この 2 つを分けないと、密なコロニーの")
    print("     中心で細胞が『消えている』のか『隣とくっついている』のか分からない。")

    print("\n=== 3. 手法の比較 —— 個数・過分割・過統合を分けて ===")
    H_DEF = 2.4
    METHODS = (
        ("大津+連結成分(ゼロ点)", lambda im, fg: m_cc(im, fg)),
        ("距離変換+分水嶺(全極大)", lambda im, fg: m_ws_all(im, fg)),
        (f"h-maxima 分水嶺(h={H_DEF})", lambda im, fg: m_ws_h(im, fg, h_px=H_DEF)),
        ("形の事前知識(充填率+面積)", lambda im, fg: m_shape(im, fg, h_px=H_DEF)),
    )
    W = 26
    res3 = {}
    for p in (SPARSE, MID, DENSE):
        print(f"  — 重なり pack {p:.2f}(重なった細胞 "
              f"{100 * occ_tab[p][0]:.0f} %、真の個数 {base[p][0]['n']})—")
        print("  " + pad("手法", W, right=False) + pad("偏り", 9) + pad("散らばり", 11)
              + pad("過分割", 9) + pad("過統合", 9) + pad("取りこぼし", 12)
              + pad("偽物", 8) + pad("1対1", 8))
        fgs = [foreground(s["img"]) for s in base[p]]
        for name, fn in METHODS:
            rows = [evaluate(s, fn(s["img"], fg)) for s, fg in zip(base[p], fgs)]
            r = summarize(rows)
            res3[(p, name)] = r
            print("  " + pad(name, W, right=False) + pad(f"{r['bias']:+.1f}", 9)
                  + pad(f"{r['scatter']:.1f}", 11) + pad(f"{r['split']:.1f}", 9)
                  + pad(f"{r['merge']:.1f}", 9) + pad(f"{r['missed']:.1f}", 12)
                  + pad(f"{r['spurious']:.1f}", 8) + pad(f"{r['one2one']:.0f}", 8))
        cnt = [count_by_area(s["img"], fg) for s, fg in zip(base[p], fgs)]
        cb = float(np.mean([c - s["n"] for c, s in zip(cnt, base[p])]))
        cs = float(np.std([c - s["n"] for c, s in zip(cnt, base[p])]))
        res3[(p, "面積割り(個数のみ)")] = {"bias": cb, "scatter": cs}
        print("  " + pad("面積割り(個数のみ・分割しない)", W, right=False)
              + pad(f"{cb:+.1f}", 9) + pad(f"{cs:.1f}", 11) + pad("—", 9)
              + pad("—", 9) + pad("—", 12) + pad("—", 8) + pad("—", 8))
    print("  → 全極大を種にすると **過分割が跳ね上がる**(距離変換の尾根が雑音で")
    print("     割れる)。h で間引くと過分割は落ちるが過統合が増える。形の事前知識は")
    print("     『割らない』判断を先に入れるので、疎な条件での過分割を抑えられる。")
    print("  → 面積割りは **分割を一切しないのに個数の偏りが小さい**。個数だけが")
    print("     欲しいなら分割は要らない、という当たり前の事実がここに出る。逆に")
    print("     言えば **個数が合っていることは分割が合っている証拠にならない**。")

    print("\n=== 4. 崖 (a) 重なり —— 過分割と過統合のどちらが先に来るか ===")
    print("  " + pad("重なり pack", 12, right=False)
          + "".join(pad(n.split("(")[0][:10], 16) for n, _ in METHODS))
    print("  " + pad("", 12, right=False)
          + "".join(pad("偏り/過分割/過統合", 16) for _ in METHODS))
    dens = {}
    for p in PACKS:
        fgs = [foreground(s["img"]) for s in base[p]]
        cells = []
        for name, fn in METHODS:
            r = summarize([evaluate(s, fn(s["img"], fg)) for s, fg in zip(base[p], fgs)])
            dens[(p, name)] = r
            cells.append(pad(f"{r['bias']:+.0f}/{r['split']:.0f}/{r['merge']:.0f}", 16))
        print("  " + pad(f"{p:.2f}", 12, right=False) + "".join(cells))
    ws_name = f"h-maxima 分水嶺(h={H_DEF})"
    first = {}
    for name, _ in METHODS:
        sp = [dens[(p, name)]["split"] for p in PACKS]
        mg = [dens[(p, name)]["merge"] for p in PACKS]
        # 「先に来る」= pack を詰めていったとき、最初に基準線(疎な条件の値 + 3 件)を
        #  超えるのはどちらか。両方超えないなら None。
        def cross(v):
            for i, p in enumerate(PACKS):
                if v[i] > v[0] + 3.0:
                    return p
            return None
        first[name] = (cross(sp), cross(mg))
    print(f"  疎(pack {SPARSE:.2f})から +3 件を超えるのはどちらが先か:")
    for name, _ in METHODS:
        a, b = first[name]
        print("    " + pad(name, W, right=False)
              + f"過分割 {a if a else '越えず'} / 過統合 {b if b else '越えず'}")
    print("  → **どちらが先に来るかは手法で違う**。切る仕掛けの無いゼロ点は過統合しか")
    print("     起こさない。全極大の分水嶺は最初から過分割が高止まりで、重なりが")
    print("     増えても過分割は減らない(尾根の雑音は重なりと無関係だから)。")

    print("\n=== 5. 崖 (b) 大きさのばらつき —— 単一スケールの前提はいつ壊れるか ===")
    RATIOS = (1.0, 1.5, 2.0, 2.5, 3.0)
    HS_SIZE = (1.0, 1.6, 2.4, 3.4)
    print(f"  大型集団 8 個の線寸法だけを振る(他は同じ)。pack {BASE_PACK:.2f} 固定。")
    print("  ★**集団ごとに分けて数える** —— 全体に混ぜると、大型の過分割と小型の")
    print("     過統合が打ち消し合って『どちらも問題なし』に見えてしまう。")
    print("  " + pad("大きさ比", 10, right=False) + pad("面積比", 10)
          + "".join(pad(f"h={h}", 15) for h in HS_SIZE) + pad("形の事前知識", 18))
    print("  " + pad("", 10, right=False) + pad("", 10)
          + "".join(pad("大型割れ/小型統合", 15) for _ in HS_SIZE)
          + pad("大型割れ/小型統合", 18))
    size_tab = {}
    for r in RATIOS:
        scs = [make_scene(s, pack=BASE_PACK, size_ratio=r) for s in SEEDS]
        fgs = [foreground(s["img"]) for s in scs]

        def by_class(preds, scs=scs):
            """(大型細胞の過分割件数, 小型細胞に掛かった過統合件数) の平均。"""
            bs, sm = [], []
            for s, pred in zip(scs, preds):
                ev = evaluate(s, pred)
                big = s["kind"] == KIND_LARGE
                bs.append(float(np.maximum(ev["per_gt"][big] - 1, 0).sum()))
                own = ev["owner_of_pred"]
                small_pred = (own >= 0) & ~big[np.clip(own, 0, None)]
                sm.append(float(np.maximum(ev["per_pred"][small_pred] - 1, 0).sum()))
            return float(np.mean(bs)), float(np.mean(sm))

        cells = []
        for h in HS_SIZE:
            b, m = by_class([m_ws_h(s["img"], fg, h_px=h) for s, fg in zip(scs, fgs)])
            size_tab[(r, h)] = (b, m)
            cells.append(pad(f"{b:.1f} / {m:.1f}", 15))
        b, m = by_class([m_shape(s["img"], fg, h_px=H_DEF) for s, fg in zip(scs, fgs)])
        size_tab[(r, "shape")] = (b, m)
        size_tab[(r, "n_big")] = int((scs[0]["kind"] == KIND_LARGE).sum())
        print("  " + pad(f"{r:.1f}x", 10, right=False) + pad(f"{r * r:.1f}x", 10)
              + "".join(cells) + pad(f"{b:.1f} / {m:.1f}", 18))
    print(f"  (大型は {size_tab[(1.0, 'n_big')]} 個。「大型割れ」はそのうち何件が"
          "2 つ以上に割られたか)")
    print("  " + pad("大きさ比", 12, right=False) + pad("大型に最適な h", 18)
          + pad("小型に最適な h", 18) + pad("差", 8))
    for r in RATIOS:
        hb = max(HS_SIZE, key=lambda h: -size_tab[(r, h)][0])
        hs = max(HS_SIZE, key=lambda h: -size_tab[(r, h)][1])
        size_tab[(r, "argh")] = (hb, hs)
        print("  " + pad(f"{r:.1f}x", 12, right=False) + pad(f"{hb:.1f}", 18)
              + pad(f"{hs:.1f}", 18) + pad(f"{hb - hs:+.1f}", 8))
    print("  → 大型細胞は **h を大きくするほど** 割れなくなり、小型細胞は"
          " **h を小さくするほど**")
    print("     くっつかなくなる。**要求が真逆**なので、単一の h では両方は救えない。")
    print("     大きさ比を上げるほど大型の過分割が増え、要求の差が広がる —— これが")
    print("     ノブの調整では直らないことの根拠で、スケール空間(細胞の大きさごとに")
    print("     h を変える)が要る。")
    print("  → 形の事前知識(面積から個数を推して、その数まで割る)は **もっと悪い**。")
    print("     大型細胞 1 個の面積が『1 個ぶん』の何倍もあるので、面積から推した")
    print("     個数が最初から間違っており、**わざわざその数まで割りにいく**。")
    print("     自己校正した『1 個ぶんの面積』が単峰であることを暗黙に前提している。")

    print("\n=== 6. 崖 (c) 種の間引き量 h —— 過分割と過統合のトレードオフ ===")
    HS = (0.0, 1.0, 1.5, 2.0, 2.4, 3.0, 3.6, 4.4, 5.5)
    print("  h=0 は間引きなし(全極大)。h は **画素単位**。")
    hcurve = {}
    for p in (SPARSE, MID, DENSE):
        print(f"  — 重なり pack {p:.2f} —")
        print("  " + pad("h [px]", 10, right=False) + pad("実効 h", 10)
              + pad("偏り", 9) + pad("散らばり", 11) + pad("過分割", 9)
              + pad("過統合", 9) + pad("過分割+過統合", 16) + pad("1対1", 8))
        fgs = [foreground(s["img"]) for s in base[p]]
        for h in HS:
            if h == 0.0:
                preds = [m_ws_all(s["img"], fg) for s, fg in zip(base[p], fgs)]
                heff = 0.0
            else:
                preds = [m_ws_h(s["img"], fg, h_px=h) for s, fg in zip(base[p], fgs)]
                heff = h_maxima_seeds(edt(fgs[0]), h)[2]
            r = summarize([evaluate(s, pr) for s, pr in zip(base[p], preds)])
            hcurve[(p, h)] = r
            print("  " + pad(f"{h:.1f}", 10, right=False) + pad(f"{heff:.2f}", 10)
                  + pad(f"{r['bias']:+.1f}", 9) + pad(f"{r['scatter']:.1f}", 11)
                  + pad(f"{r['split']:.1f}", 9) + pad(f"{r['merge']:.1f}", 9)
                  + pad(f"{r['split'] + r['merge']:.1f}", 16)
                  + pad(f"{r['one2one']:.0f}", 8))
    print("  " + pad("重なり pack", 14, right=False) + pad("|偏り| 最小の h", 18)
          + pad("そのときの過分割/過統合", 26) + pad("1対1 最大の h", 18)
          + pad("その 1対1", 12))
    best_h = {}
    for p in (SPARSE, MID, DENSE):
        hb = min(HS, key=lambda h: abs(hcurve[(p, h)]["bias"]))
        ho = max(HS, key=lambda h: hcurve[(p, h)]["one2one"])
        best_h[p] = (hb, ho)
        print("  " + pad(f"{p:.2f}", 14, right=False) + pad(f"{hb:.1f}", 18)
              + pad(f"{hcurve[(p, hb)]['split']:.1f} / "
                    f"{hcurve[(p, hb)]['merge']:.1f}", 26)
              + pad(f"{ho:.1f}", 18) + pad(f"{hcurve[(p, ho)]['one2one']:.0f}", 12))
    print("  → 過分割は h とともに単調に減り、過統合は単調に増える —— **トレードオフ**。")
    print("     合計(右から 3 列目)には谷ができるが、その谷の位置と『偏りがゼロに")
    print("     なる h』は **一致しない**。どちらを最適と呼ぶかで答えが変わる。")
    hb_list = [best_h[p][0] for p in (SPARSE, MID, DENSE)]
    ho_list = [best_h[p][1] for p in (SPARSE, MID, DENSE)]
    print(f"  → **最適な h は密度で動く**: 偏り基準で {hb_list}、"
          f"1対1 基準で {ho_list}。")
    print("     疎な場面で決めた h をそのまま密な場面へ持っていくと壊れる。")

    print("\n=== 7. ★計数が合っていて分割が全部外れている点を探す ===")
    print("  過分割と過統合は逆向きに動くので、**どこかで打ち消し合う**。その点では")
    print("  個数の偏りがほぼゼロになるのに、分割の誤りは最悪付近のまま残る。")
    print("  " + pad("重なり pack", 12, right=False) + pad("h", 8) + pad("偏り", 9)
          + pad("過分割", 9) + pad("過統合", 9) + pad("誤り合計", 12)
          + pad("誤り合計の最小", 16) + pad("1対1 / 細胞数", 16))
    cancel = {}
    for p in (SPARSE, MID, DENSE):
        hb = best_h[p][0]
        r = hcurve[(p, hb)]
        tot_min = min(hcurve[(p, h)]["split"] + hcurve[(p, h)]["merge"] for h in HS)
        cancel[p] = (hb, r, tot_min)
        print("  " + pad(f"{p:.2f}", 12, right=False) + pad(f"{hb:.1f}", 8)
              + pad(f"{r['bias']:+.1f}", 9) + pad(f"{r['split']:.1f}", 9)
              + pad(f"{r['merge']:.1f}", 9)
              + pad(f"{r['split'] + r['merge']:.1f}", 12)
              + pad(f"{tot_min:.1f}", 16)
              + pad(f"{r['one2one']:.0f} / {r['n_gt']:.0f}", 16))
    worst = max((DENSE, MID, SPARSE), key=lambda p: cancel[p][1]["split"]
                + cancel[p][1]["merge"])
    cw = cancel[worst][1]
    print(f"  → いちばん危ないのは pack {worst:.2f} / h {cancel[worst][0]:.1f} の行:")
    print(f"     **個数の偏りは {cw['bias']:+.1f} 個**(真値 {cw['n_gt']:.0f} 個に対して"
          f" {100 * abs(cw['bias']) / cw['n_gt']:.1f} %)なのに、")
    print(f"     過分割 {cw['split']:.1f} 件 + 過統合 {cw['merge']:.1f} 件 ="
          f" {cw['split'] + cw['merge']:.1f} 件の分割誤りがあり、")
    print(f"     1 対 1 に正しく対応した細胞は {cw['one2one']:.0f} / {cw['n_gt']:.0f} 個")
    print(f"     しかない。**個数だけを報告していたら最良の設定として通る**。")
    print("     打ち消し合いが起きる理由もはっきりしている: 過分割は個数を +1 に、")
    print("     過統合は -1 に動かすので、両者が同数なら **個数は元に戻る**。")

    print("\n=== 8. 崖 (d) 雑音と背景ムラ ===")
    print("  " + pad("条件", 26, right=False) + pad("前景率", 10)
          + "".join(pad(n.split("(")[0][:10], 16) for n, _ in METHODS))
    print("  " + pad("", 26, right=False) + pad("", 10)
          + "".join(pad("偏り/過分割/過統合", 16) for _ in METHODS))
    noise_tab = {}
    truth_fg = None
    for label, kw in (("基準", {}),
                      ("光子 1/4(雑音 2 倍)", {"photons": PHOTONS / 4}),
                      ("光子 1/16(雑音 4 倍)", {"photons": PHOTONS / 16}),
                      ("背景ムラ 2.5 倍", {"bg_amp": 2.5 * BG_AMP}),
                      ("背景ムラ 5 倍", {"bg_amp": 5.0 * BG_AMP}),
                      ("両方(1/16 + 5 倍)", {"photons": PHOTONS / 16,
                                              "bg_amp": 5.0 * BG_AMP})):
        scs = [make_scene(s, pack=BASE_PACK, **kw) for s in SEEDS]
        fgs = [foreground(s["img"]) for s in scs]
        fgr = float(np.mean([f.mean() for f in fgs]))
        if truth_fg is None:
            truth_fg = float(np.mean([(s["owner"] > 0).mean() for s in scs]))
        cells = []
        for name, fn in METHODS:
            r = summarize([evaluate(s, fn(s["img"], fg)) for s, fg in zip(scs, fgs)])
            noise_tab[(label, name)] = r
            cells.append(pad(f"{r['bias']:+.0f}/{r['split']:.0f}/{r['merge']:.0f}", 16))
        noise_tab[(label, "fg")] = fgr
        print("  " + pad(label, 26, right=False) + pad(f"{100 * fgr:.1f} %", 10)
              + "".join(cells))
    print(f"  (真値の前景率 = 細胞が占める画素の割合 {100 * truth_fg:.1f} %)")
    print("  → **雑音と背景ムラは効き方が違う**。雑音は距離変換の尾根を割るので")
    print("     過分割を増やす。背景ムラは大津の閾値を動かして前景率そのものを")
    print("     ずらすので、暗い側の細胞が消え(取りこぼし)、明るい側が膨らんで")
    print("     くっつく(過統合)。**同じ『画質が悪い』でも直し方が逆**で、")
    print("     前者は種の間引き、後者は背景補正(shading correction)が要る。")

    print("\n=== 9. 崖 (e) 縁で切れた細胞をどう数えるか ===")
    print("  3 通りの規約: 全部数える / 縁に触れたものを捨てる / 半分に数える。")
    print("  " + pad("規約", 22, right=False) + pad("真値", 10) + pad("推定", 10)
          + pad("偏り", 9) + pad("散らばり", 11) + pad("真値との差の由来", 24))
    edge_tab = {}
    fgs = [foreground(s["img"]) for s in base[BASE_PACK]]
    preds = [m_ws_h(s["img"], fg, h_px=H_DEF) for s, fg in zip(base[BASE_PACK], fgs)]
    for rule in ("全部数える", "縁を捨てる", "半分に数える"):
        gts, ests = [], []
        for s, pred in zip(base[BASE_PACK], preds):
            k = int(pred.max())
            pp = per_object(pred, k)
            pe = sum(1 for v in pp.values() if v["edge"])
            gt_e = int(s["on_edge"].sum())
            if rule == "全部数える":
                gts.append(s["n"]); ests.append(k)
            elif rule == "縁を捨てる":
                gts.append(s["n"] - gt_e); ests.append(k - pe)
            else:
                gts.append(s["n"] - 0.5 * gt_e); ests.append(k - 0.5 * pe)
        e = np.asarray(ests, float) - np.asarray(gts, float)
        edge_tab[rule] = (float(np.mean(gts)), float(np.mean(ests)),
                          float(e.mean()), float(e.std()))
        note = {"全部数える": "縁の半端な塊も 1 個と数える",
                "縁を捨てる": "真値側も同じ規約で捨てている",
                "半分に数える": "折衷(Gundersen 流)"}[rule]
        print("  " + pad(rule, 22, right=False) + pad(f"{edge_tab[rule][0]:.1f}", 10)
              + pad(f"{edge_tab[rule][1]:.1f}", 10)
              + pad(f"{edge_tab[rule][2]:+.1f}", 9)
              + pad(f"{edge_tab[rule][3]:.1f}", 11) + pad(note, 24, right=False))
    spread = max(v[1] for v in edge_tab.values()) - min(v[1] for v in edge_tab.values())
    print(f"  → **規約を変えるだけで推定個数が {spread:.1f} 個動く**"
          f"(真値 {edge_tab['全部数える'][0]:.0f} 個の"
          f" {100 * spread / edge_tab['全部数える'][0]:.0f} %)。規約を書かずに")
    print("     『細胞数 N 個』と報告してはいけない。")
    print("  → ★ただし、真値の側も同じ規約で数えれば **偏りはどの規約でも小さい**。")
    print("     危ないのは規約の選択そのものではなく、**推定と真値で違う規約を使う**")
    print("     ことのほう(例: 装置が縁を捨てて数え、参照は全部数えている)。")

    print("\n=== 10. 面積と長短径の推定誤差 —— 見えている面積までしか取れない ===")
    print("  1 対 1 に対応した細胞だけを見る。面積は画素数、長短径はモーメント楕円と")
    print("  ``fs.fit_ellipse``(境界点への直接最小二乗当てはめ)の両方で出す。")
    print("  ★**隠れた割合の帯で分ける** —— 混ぜると、隠れていない細胞が数で薄めて")
    print("     『面積はよく当たる』に見えてしまう。")
    print("  " + pad("隠れた割合", 14, right=False) + pad("細胞数", 9)
          + pad("面積 vs 見えている面積", 26) + pad("面積 vs 真の面積", 22)
          + pad("ra(モーメント)", 20) + pad("ra(当てはめ)", 20)
          + pad("rb(モーメント)", 20))
    OCC_EDGES = ((0.0, 0.02), (0.02, 0.15), (0.15, 0.40), (0.40, 1.01))
    OCC_LBL = ("~2 %", "2-15 %", "15-40 %", "40 % 超")
    bins = {i: {"dv": [], "dt": [], "ra": [], "rf": [], "rb": []}
            for i in range(len(OCC_EDGES))}
    area_tab = {}
    for p in (SPARSE, MID, DENSE):
        fgs2 = [foreground(s["img"]) for s in base[p]]
        dv, dt = [], []
        for s, fg in zip(base[p], fgs2):
            pred = m_ws_h(s["img"], fg, h_px=H_DEF)
            ev = evaluate(s, pred)
            pp = per_object(pred, ev["n_pred"])
            # 境界点(4 近傍でラベルが違う画素)—— 楕円当てはめの入力
            bnd = np.zeros_like(pred, bool)
            bnd[:-1, :] |= pred[:-1, :] != pred[1:, :]
            bnd[1:, :] |= pred[:-1, :] != pred[1:, :]
            bnd[:, :-1] |= pred[:, :-1] != pred[:, 1:]
            bnd[:, 1:] |= pred[:, :-1] != pred[:, 1:]
            bnd &= pred > 0
            for g, q in ev["one2one"]:
                if s["on_edge"][g] or q not in pp:
                    continue
                a_pred = pp[q]["area"]
                e_vis = 100.0 * (a_pred / max(s["area_vis"][g], 1.0) - 1.0)
                e_true = 100.0 * (a_pred / max(s["area_true"][g], 1.0) - 1.0)
                dv.append(e_vis)
                dt.append(e_true)
                o = float(s["occ"][g])
                bi = next(i for i, (a, b) in enumerate(OCC_EDGES) if a <= o < b)
                ra_t, rb_t = s["cells"][g][2], s["cells"][g][3]
                bins[bi]["dv"].append(e_vis)
                bins[bi]["dt"].append(e_true)
                bins[bi]["ra"].append(100.0 * (pp[q]["ra"] / ra_t - 1.0))
                bins[bi]["rb"].append(100.0 * (pp[q]["rb"] / rb_t - 1.0))
                ys, xs = np.nonzero(bnd & (pred == q))
                if ys.size >= 6:
                    try:
                        e = fs.fit_ellipse(np.stack([ys, xs], 1).astype(float))
                        bins[bi]["rf"].append(100.0 * (e["ra"] / ra_t - 1.0))
                    except Exception:
                        pass
        area_tab[p] = (len(dv), float(np.mean(dv)), float(np.mean(dt)))
    f = lambda v: f"{np.mean(v):+.1f}±{np.std(v):.1f}" if len(v) else "—"
    for i, lbl in enumerate(OCC_LBL):
        b = bins[i]
        print("  " + pad(lbl, 14, right=False) + pad(f"{len(b['dv'])}", 9)
              + pad(f(b["dv"]), 26) + pad(f(b["dt"]), 22) + pad(f(b["ra"]), 20)
              + pad(f(b["rf"]), 20) + pad(f(b["rb"]), 20))
    print("  " + pad("(全部混ぜる)", 14, right=False)
          + pad(f"{sum(len(bins[i]['dv']) for i in bins)}", 9)
          + pad(f(sum((bins[i]["dv"] for i in bins), [])), 26)
          + pad(f(sum((bins[i]["dt"] for i in bins), [])), 22))
    print("  → 単位は %。**隠れていない細胞では 2 つの列がほぼ一致する**のに、")
    print("     隠れた細胞では『見えている面積』には当たったまま『真の面積』だけが")
    print("     大きく下振れする。この差は分割の巧拙ではなく、**隠れた部分は原理的に")
    print("     観測できない**ことの現れ = 誤差の床である。最下行のように混ぜると")
    print("     床が薄まって見えなくなる。")
    print("  → 長半径はモーメント楕円のほうが安定する。境界点への当てはめは、")
    print("     分水嶺が引いた **直線的な切断面** をそのまま楕円弧と読むので、")
    print("     切られた細胞で大きく外れる。切断面を除いて当てはめる仕掛けが要る。")

    print("\n=== 11. 速度(この機械での実測、224x224 の 1 枚あたり)===")
    probe = base[BASE_PACK][0]["img"]
    fgp = foreground(probe)
    speed = {}
    for name, fn in (("大津 + 穴埋め(前処理)", lambda: foreground(probe)),
                     ("連結成分(ゼロ点)", lambda: m_cc(probe, fgp)),
                     ("距離変換+分水嶺(全極大)", lambda: m_ws_all(probe, fgp)),
                     (f"h-maxima 分水嶺", lambda: m_ws_h(probe, fgp, h_px=H_DEF)),
                     ("形の事前知識", lambda: m_shape(probe, fgp, h_px=H_DEF))):
        fn()
        t = time.perf_counter()
        for _ in range(3):
            fn()
        speed[name] = 1e3 * (time.perf_counter() - t) / 3
        print("  " + pad(name, 26, right=False) + pad(f"{speed[name]:.1f}", 9) + " ms")
    print("  → 形の事前知識だけ 1 桁遅い。連結成分ごとに Python の for を回して")
    print("     部分画像に分水嶺を掛けているため。**塊の数に比例**するので、密な")
    print("     場面では逆に速くなる(塊が減るので)。")

    print("\n=== 12. 道具の穴(この PoC で当たったもの)===")
    holes = (
        ("2 次元の連結成分ラベリングが facade に無い",
         "vol_label に厚さ 1 のボリュームを渡して代用。fs.op 側は個数スカラーのみ"),
        ("2 次元の per-object region props が無い",
         "3 次元の vol_region_props はあるのに 2 次元は image 全体の 1 スカラー"),
        ("distance_transform が最大値で正規化される",
         "画素単位の距離が取れない。vol_distance_transform で代用"),
        ("xsk2_h_maxima が [0,1] 切り詰め + h は比でしか振れない",
         "画素単位の h を指定できない。h < 0.05*max(EDT) は表現不能"),
        ("2 次元 watershed が公開されていない",
         "segmentation.watersheds_marker はモジュール直下のみ、mask 引数も無い"),
        ("circularity / eccentricity / area_center が物体ごとに取れない",
         "画像全体の 1 スカラー。分割判定に使えないので自前でモーメントを回した"),
    )
    for a, b in holes:
        print("  ・" + a)
        print("      → " + b)

    print("\n=== 13. まとめ ===")
    lines = (
        ("ゼロ点(大津+連結成分)で足りるか",
         f"疎なら足りる(偏り {zero[SPARSE]['bias']:+.1f})が、"
         f"密で {zero[DENSE]['bias']:+.1f} 個。失点は全部過統合"),
        ("分水嶺は何を直すか",
         f"過統合を {zero[DENSE]['merge']:.0f} → "
         f"{dens[(DENSE, ws_name)]['merge']:.0f} 件へ。代わりに過分割が出る"),
        ("h をどう選ぶか",
         f"選べない。偏り基準の最適 h が密度で {hb_list} と動く"),
        ("大きさが 3 倍違うと",
         f"h 固定のまま大型だけが割れる(過分割 "
         f"{size_tab[(1.0, 'big')]:.1f} → {size_tab[(3.0, 'big')]:.1f} 件)"),
        ("★いちばん危ない読み違え",
         f"個数の偏り {cw['bias']:+.1f} 個で分割誤り {cw['split'] + cw['merge']:.0f} 件。"
         "過分割と過統合が打ち消し合う"),
        ("縁の規約",
         f"規約を変えるだけで推定が {spread:.1f} 個動く。推定と真値で規約を揃える"),
        ("面積の誤差の床",
         f"見えている面積には {area_tab[DENSE][1]:+.1f} % で当たるが、"
         f"真の面積には {area_tab[DENSE][2]:+.1f} %"),
    )
    for q, a in lines:
        print("  " + pad(q, 34, right=False) + a)
    print(f"\n  全体の所要 {time.perf_counter() - t0:.1f} 秒")

    # ---- 自己検査(速さは assert しない)------------------------------------- #
    # (1) 合成が要求どおり: 個数は pack に依らず一定で、重なりだけが単調に増える
    ns = [base[p][0]["n"] for p in PACKS]
    assert len(set(ns)) == 1, ns
    ovs = [occ_tab[p][0] for p in PACKS]
    assert all(ovs[i] < ovs[i + 1] for i in range(len(ovs) - 1)), ovs
    assert ovs[0] > 0.15 and ovs[-1] > 0.70, ovs      # 疎でも鎖のぶん重なりが残る
    # 構造が実在する: 大型集団は面積で 3 倍以上、デブリは owner に入っていない
    big = sc0["area_true"][sc0["kind"] == KIND_LARGE].mean()
    sml = sc0["area_true"][sc0["kind"] == KIND_SINGLE].mean()
    assert big > 3.0 * sml, (big, sml)
    assert int(sc0["owner"].max()) <= sc0["n"], sc0["owner"].max()

    # (2) ゼロ点は重なりとともに単調に下振れし、失点は過統合に偏る
    zb = [zero[p]["bias"] for p in PACKS]
    assert all(zb[i] > zb[i + 1] for i in range(len(zb) - 1)), zb
    assert zb[-1] < -0.25 * zero[PACKS[-1]]["n_gt"], zb          # 3 割超の取りこぼし
    assert zero[PACKS[-1]]["merge"] > 10.0 * max(zero[PACKS[-1]]["split"], 1.0), zero
    assert zero[PACKS[-1]]["scatter"] < 0.5 * abs(zb[-1]), zero  # 枚数では消えない
    # ★過統合と取りこぼしは別物 —— くっついても「消えて」はいない
    assert zero[PACKS[-1]]["merge"] > 5.0 * (zero[PACKS[-1]]["missed"] + 1.0), zero

    # (3) 分水嶺はゼロ点の過統合を大きく減らす(が過分割を出す)
    for p in (MID, DENSE):
        assert dens[(p, ws_name)]["merge"] < 0.6 * zero[p]["merge"], (p, dens[(p, ws_name)])
        assert dens[(p, ws_name)]["split"] > zero[p]["split"], (p, dens[(p, ws_name)])
    # 全極大は最初から過分割が高い(疎な条件でも)
    assert dens[(SPARSE, "距離変換+分水嶺(全極大)")]["split"] \
        > dens[(SPARSE, ws_name)]["split"] + 3.0, dens[(SPARSE, "距離変換+分水嶺(全極大)")]
    # 形の事前知識は疎な条件で過分割を抑える
    assert res3[(SPARSE, "形の事前知識(充填率+面積)")]["split"] \
        <= res3[(SPARSE, "距離変換+分水嶺(全極大)")]["split"], res3
    # 面積割りは分割を一切しないのに個数の偏りは小さい = 個数は分割の証拠にならない
    assert abs(res3[(DENSE, "面積割り(個数のみ)")]["bias"]) < abs(zero[DENSE]["bias"]), res3

    # (4) 崖 (c) h のトレードオフ: 過分割は単調に減り、過統合は単調に増える
    for p in (SPARSE, MID, DENSE):
        sp = [hcurve[(p, h)]["split"] for h in HS]
        mg = [hcurve[(p, h)]["merge"] for h in HS]
        assert sp[0] > sp[-1] + 5.0, (p, sp)
        assert mg[-1] > mg[0] + 5.0, (p, mg)
        # 単調性は雑音で少し崩れてよいが、大枠で逆向きであることは要求する
        assert np.corrcoef(np.arange(len(HS)), sp)[0, 1] < -0.8, (p, sp)
        assert np.corrcoef(np.arange(len(HS)), mg)[0, 1] > 0.8, (p, mg)
    # ★最適な h は密度で動く(偏り基準か 1対1 基準のどちらかで必ず動く)
    assert len(set(hb_list)) > 1 or len(set(ho_list)) > 1, (hb_list, ho_list)

    # (5) ★計数が合っていて分割が全部外れている点が実在する
    #     偏りが 2 % 未満なのに、分割誤りが「誤り合計の最小値」より十分多い。
    found = False
    for p in (SPARSE, MID, DENSE):
        hb, r, tot_min = cancel[p]
        if abs(r["bias"]) < 0.02 * r["n_gt"] and (r["split"] + r["merge"]) > tot_min + 5.0:
            found = True
            # そのとき 1対1 対応は全細胞の 9 割に届かない = 分割は当たっていない
            assert r["one2one"] < 0.90 * r["n_gt"], (p, r)
    assert found, {p: cancel[p][1]["bias"] for p in (SPARSE, MID, DENSE)}

    # (6) 崖 (b) 大きさ: 大型集団だけの過分割が単調に増える
    bs = [size_tab[(r, "big")] for r in RATIOS]
    assert bs[-1] > bs[0] + 3.0, bs
    assert bs[-1] > 0.5 * 10, bs           # 大型 10 個の半数以上が割れる

    # (7) 崖 (d) 雑音は過分割を、背景ムラは前景率を壊す —— 効き方が違う
    n_base = noise_tab[("基準", "距離変換+分水嶺(全極大)")]
    n_noisy = noise_tab[("光子 1/16(雑音 4 倍)", "距離変換+分水嶺(全極大)")]
    assert n_noisy["split"] > n_base["split"] + 3.0, (n_base, n_noisy)
    fg_base = noise_tab[("基準", "fg")]
    fg_shade = noise_tab[("背景ムラ 5 倍", "fg")]
    assert abs(fg_shade - truth_fg) > abs(fg_base - truth_fg) + 0.01, (fg_base, fg_shade)

    # (8) 崖 (e) 縁: 規約を変えると推定が動くが、真値も同じ規約なら偏りは小さい
    assert spread > 2.0, spread
    for rule, v in edge_tab.items():
        assert abs(v[2]) < 0.12 * edge_tab["全部数える"][0], (rule, v)

    # (9) 面積: 見えている面積には当たるが、真の面積には重なりぶん届かない(床)
    for p in (MID, DENSE):
        assert abs(area_tab[p][1]) < 15.0, (p, area_tab[p])
        assert area_tab[p][2] < area_tab[p][1] - 3.0, (p, area_tab[p])
    assert area_tab[DENSE][2] < area_tab[SPARSE][2], area_tab

    # (10) ★道具の穴が「まだ在る」ことを機械で確かめる(直ったら落ちる = 良い落ち方)
    #      (a) 進化 op の距離変換は最大値で正規化される
    m = np.zeros((32, 32), bool)
    m[8:24, 8:24] = True
    dn_op = fs.apply(m.astype(np.float64), "distance_transform")
    d_px = edt(m)
    assert abs(float(dn_op.max()) - 1.0) < 1e-9, float(dn_op.max())
    assert d_px.max() > 7.0, float(d_px.max())
    #      (b) xsk2_h_maxima は入力を [0,1] に切り詰める(生の距離を渡すと壊れる)
    raw = fs.apply(d_px, "xsk2_h_maxima", a=0.5)
    nrm = fs.apply(d_px / d_px.max(), "xsk2_h_maxima", a=0.5)
    assert float(raw.sum()) != float(nrm.sum()), (raw.sum(), nrm.sum())
    #      (c) 2 次元の per-object region props が無い(image 全体の 1 スカラー)
    two = np.zeros((40, 40), np.float64)
    two[5:15, 5:15] = 1.0
    two[25:35, 25:35] = 1.0
    c = np.asarray(fs.apply(two, "circularity"))
    assert c.size == 1 or float(c.min()) == float(c.max()), c.shape
    #      (d) 2 次元ラベリングが fs / fs.ledger に無い
    assert not hasattr(fs, "label_components_2d")
    assert not hasattr(fs.ledger, "watersheds_marker")

    print("\nPASS")


if __name__ == "__main__":
    main()

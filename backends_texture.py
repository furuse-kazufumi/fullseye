# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""backends_texture — 独自(非 HALCON)のテクスチャ複雑さ特徴。

imgevolve は HALCON 中心に始まったが、この cluster は HALCON に無い「テクスチャの
複雑さを 1 スカラーで測る」特徴を numpy だけで足す(``Op.halcon`` は空 —— カバレッジ
主張はしない)。第一号は Minkowski-Bouligand(ボックスカウント)フラクタル次元。
既存の entropy_gray / gray_histo(分布のばらつき)とは別軸で、「構造が空間を
どれだけ埋めるか」の自己相似スケーリングを測る。将来 lacunarity 等をここに足す。
"""
from __future__ import annotations

import numpy as np


def _safe(fn, out_sort=None):
    """失敗を sort 妥当な fallback に落とす共有ガード(backend_safe.guard)。"""
    from backend_safe import guard
    return guard(fn, out_sort=out_sort)


def fractal_dimension(v, a, b):
    """テクスチャの複雑さを測る Minkowski-Bouligand(ボックスカウント)フラクタル次元。

    閾値 ``a``(既定 0.5)で二値化し、箱サイズ ``s = 1, 2, 4, …`` について「構造を
    含む s×s 箱」の数 ``N(s)`` を数え、``log N(s)`` を ``log(1/s)`` に最小二乗回帰した
    傾きを返す(Mandelbrot 1982)。直線状の構造は ~1、平面を埋める領域は ~2、自己
    相似な縁は中間の非整数(Sierpinski 三角形なら ``log 3 / log 2 ≈ 1.585``)。表面
    粗さ・組織テクスチャ・地形・破面などの安価な複雑さ特徴に使える。

    有限解像度のため塗り潰し領域は 2 をやや下回る(粗いスケールで箱が飽和する既知の
    過小評価)。``a`` が二値化の閾値、``b`` は未使用。構造が無い/1 スケールしか取れない
    ときは 0 を返す。"""
    x = np.clip(np.asarray(v, np.float64), 0.0, 1.0)
    g = x if x.ndim == 2 else x.reshape(x.shape[0], -1)
    mask = g > float(a)
    h, w = mask.shape
    n = min(h, w)
    sizes: list[int] = []
    counts: list[int] = []
    s = 1
    while s <= n // 2:
        ph, pw = (-h) % s, (-w) % s
        padded = np.pad(mask, ((0, ph), (0, pw)))
        hs, ws = padded.shape
        boxes = padded.reshape(hs // s, s, ws // s, s).any(axis=(1, 3))
        sizes.append(s)
        counts.append(int(boxes.sum()))
        s *= 2
    sz = np.asarray(sizes, np.float64)
    ct = np.asarray(counts, np.float64)
    ok = ct > 0
    if ok.sum() < 2:                                       # 構造が無い / スケールが 1 つ
        return np.float64(0.0)
    slope = np.polyfit(np.log(1.0 / sz[ok]), np.log(ct[ok]), 1)[0]
    return np.float64(max(0.0, slope))


DOCS = {"fractal_dimension": fractal_dimension.__doc__}


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    # halcon="" —— HALCON にボックスカウント次元の operator は無い(新規能力、
    # カバレッジ主張なし)。entropy_gray などの分布特徴とは軸が違う。
    defs = [
        ("fractal_dimension", "features", fractal_dimension),
    ]
    return [Op(n, c, "", IMAGE, FEATURE, _safe(f, FEATURE)) for (n, c, f) in defs]

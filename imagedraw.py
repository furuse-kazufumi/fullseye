# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""imagedraw — 画像配列に直接マーカー/線/円/輪郭を焼き込むラスタ描画op(numpy)。

Fullseye の既定の描画モデルは HALCON 流(``gen_*_xld`` で図形ジオメトリを作り、
Studio の ``dev_display`` でビューに重ね描き)。本モジュールはそれと相補的に、
**ピクセルバッファへ直接アノテーションを焼く** cv2.line/circle/drawMarker 相当を
純 numpy で提供する。対応点(ランドマーク)の可視化、デバッグオーバーレイ、教材
図の生成に使う(:mod:`imagemorph` の対応点を描くのに便利)。

規約(imagemorph と同じ): 画像は (H,W) か (H,W,C)、値域 [0,1] の float。点は
(x,y) ピクセル座標。全 draw_* は **入力を破壊せず新しい配列を返す**。color は
グレースケールならスカラ、カラーなら長さ C のシーケンス(スカラなら全チャンネル同値)。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

__all__ = [
    "draw_line",
    "draw_polyline",
    "draw_circle",
    "draw_markers",
    "draw_contour",
]


def _prep(img):
    a = np.array(img, dtype=np.float64)          # copy(入力を破壊しない)
    if a.ndim not in (2, 3):
        raise ValueError(f"img must be (H,W) or (H,W,C) (got: {a.shape})")
    if a.size == 0 or a.shape[0] == 0 or a.shape[1] == 0:
        raise ValueError("img is empty")
    return np.clip(a, 0.0, 1.0)


def _color_for(a, color):
    if a.ndim == 2:
        return float(color if np.isscalar(color) else np.mean(color))
    c = np.asarray(color, dtype=np.float64)
    if c.ndim == 0:
        c = np.full(a.shape[2], float(c))
    if c.shape[0] < a.shape[2]:
        c = np.concatenate([c, np.zeros(a.shape[2] - c.shape[0])])
    return c[: a.shape[2]]


def _dilate(mask, width):
    w = int(round(width))
    if w <= 1:
        return mask
    return ndimage.binary_dilation(mask, iterations=max(1, (w - 1) // 2 + (w - 1) % 2))


def _apply(a, mask, color, width):
    mask = _dilate(mask, width)
    a[mask] = _color_for(a, color)
    return a


def _line_mask(shape, p0, p1):
    """(x0,y0)-(x1,y1) を結ぶ直線の1px マスク(端はクランプ)。"""
    H, W = shape
    x0, y0 = float(p0[0]), float(p0[1])
    x1, y1 = float(p1[0]), float(p1[1])
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    xs = np.linspace(x0, x1, n)
    ys = np.linspace(y0, y1, n)
    xi = np.clip(np.round(xs).astype(int), 0, W - 1)
    yi = np.clip(np.round(ys).astype(int), 0, H - 1)
    m = np.zeros((H, W), dtype=bool)
    m[yi, xi] = True
    return m


def _polyline_mask(shape, points, closed):
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    if pts.shape[0] < 2:
        raise ValueError("polyline requires at least 2 points")
    seq = list(pts) + ([pts[0]] if closed else [])
    m = np.zeros(shape, dtype=bool)
    for i in range(len(seq) - 1):
        m |= _line_mask(shape, seq[i], seq[i + 1])
    return m


def draw_line(img, p0, p1, color=1.0, width=1):
    """(x,y)=p0 から p1 へ太さ width の直線を描く。"""
    a = _prep(img)
    return _apply(a, _line_mask(a.shape[:2], p0, p1), color, width)


def draw_polyline(img, points, color=1.0, width=1, closed=False):
    """点列 (N,2) を結ぶ折れ線を描く(closed=True で始点に戻る=多角形)。"""
    a = _prep(img)
    return _apply(a, _polyline_mask(a.shape[:2], points, closed), color, width)


def draw_contour(img, contour, color=1.0, width=1):
    """XLD 輪郭 ``{cs:[Nx2 (row,col),...]}`` または (N,2) 配列を閉じて描く。

    XLD 輪郭は (row,col) 順なので (x,y)=(col,row) に変換して描画する。
    """
    a = _prep(img)
    if isinstance(contour, dict):
        arrs = contour.get("cs", [])
    else:
        arrs = [contour]
    m = np.zeros(a.shape[:2], dtype=bool)
    for arr in arrs:
        p = np.asarray(arr, dtype=np.float64).reshape(-1, 2)
        if p.shape[0] < 2:
            continue
        if isinstance(contour, dict):                 # (row,col) -> (x,y)
            p = p[:, ::-1]
        m |= _polyline_mask(a.shape[:2], p, closed=True)
    return _apply(a, m, color, width)


def draw_circle(img, center, radius, color=1.0, width=1, fill=False):
    """中心 (x,y)・半径 radius の円(fill=True で塗り潰し)。"""
    a = _prep(img)
    H, W = a.shape[:2]
    cx, cy = float(center[0]), float(center[1])
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot(xx - cx, yy - cy)
    if fill:
        m = d <= radius
        a[m] = _color_for(a, color)
        return a
    m = np.abs(d - radius) <= max(0.6, width / 2.0)
    a[m] = _color_for(a, color)
    return a


def draw_markers(img, points, color=1.0, size=4, shape="cross", width=1):
    """点列 (N,2) の各点にマーカーを描く。shape='cross'|'square'|'dot'。"""
    a = _prep(img)
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    if shape == "dot":
        for x, y in pts:
            a = draw_circle(a, (x, y), size, color, width=width, fill=True)
        return a
    H, W = a.shape[:2]
    m = np.zeros((H, W), dtype=bool)
    for x, y in pts:
        if shape == "cross":
            m |= _line_mask((H, W), (x - size, y), (x + size, y))
            m |= _line_mask((H, W), (x, y - size), (x, y + size))
        elif shape == "square":
            m |= _polyline_mask((H, W), [(x - size, y - size), (x + size, y - size),
                                         (x + size, y + size), (x - size, y + size)], closed=True)
        else:
            raise ValueError(f"shape must be 'cross'|'square'|'dot' (got: {shape!r})")
    return _apply(a, m, color, width)

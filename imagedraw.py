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

## 描画状態と線種(:mod:`drawstyle`)

``style=`` に :class:`drawstyle.DrawStyle` を渡すと、色・線幅・線種・塗りをまとめて
指定できる。``style`` を渡さなければ **従来と 1 ビットも変わらない**(白・幅 1・実線)::

    from drawstyle import DrawStyle
    img = draw_polyline(img, pts, style=DrawStyle(color="wrong", line_style="dashed"))

``with drawstyle.draw_style(...)`` ブロックの中でも既定が差し替わる。装置グローバルな
可変状態を持たない理由は :mod:`drawstyle` の docstring を参照(図の再現性のため)。

``color=`` は float(グレー)/ RGB 三つ組 / :mod:`palette` の役割名(``"wrong"`` 等)
のいずれでもよい。個別引数(``color`` / ``width``)は ``style`` より優先する。

## 破線の位相をどう決めたか

破線・点線の位相は **折れ線の弧長にそって連続**する ―― 頂点でリセットしない。
閉じた折れ線では終点→始点の閉じ辺も同じ弧長の続きとして描き、**継ぎ目でパターンが
きれいに合うことは保証しない**(合わせるには周長をパターン周期の整数倍に丸める必要が
あり、それは指定した画素長を勝手に変えることになる)。

頂点でリセットしない理由は美観ではなく **正しさ**: XLD 輪郭のように 1–2 画素ごとに
頂点がある点列で位相をリセットすると、各辺が必ずパターンの先頭(= 点灯)から始まる
ので、破線を指定したのに実線が出る。実測でも、60 頂点の円輪郭を ``dashed`` で描くと
リセット方式は点灯率 100 % になり、弧長連続方式は 10/15 = 67 % 付近に落ちる。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import drawstyle
from drawstyle import DrawStyle

__all__ = [
    "draw_line",
    "draw_polyline",
    "draw_circle",
    "draw_markers",
    "draw_contour",
    "new_canvas",
]


class _Keep:
    """「引数が渡されなかった」ことを表す番兵(``None`` は正当な値になりうるため)。"""

    def __repr__(self):
        return "<from style>"


_KEEP = _Keep()


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


def _settle(color, width, style):
    """(color, width, style) を解決して ``(色, 線幅, パターン, style)`` を返す。

    優先順は **個別引数 > 渡された style > ``with draw_style`` の周囲スタイル >
    従来の既定(白・幅 1・実線)**。周囲スタイルが無く style も渡されなければ、
    従来と同じ値がそのまま流れる(= ビット不変)。
    """
    st = style if style is not None else drawstyle.current_style()
    if st is not None and not isinstance(st, DrawStyle):
        raise ValueError(f"style must be a DrawStyle, got {type(st).__name__}")
    scheme = "okabe_ito" if st is None else st.scheme
    col = (1.0 if st is None else st.color) if color is _KEEP else color
    wid = (1 if st is None else st.width) if width is _KEEP else width
    pattern = None if st is None else st.pattern()
    return drawstyle.resolve_color(col, scheme), drawstyle.check_width(wid), pattern, st


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


def _phase_on(s, pattern):
    """弧長 ``s``(画素)の各要素がパターンの「点灯」区間に入るか。

    パターンは ``(on, off, on, off, ...)`` の画素長。周期 ``sum(pattern)`` で巻き、
    偶数番目の run(0, 2, ...)を点灯とする。
    """
    pat = np.asarray(pattern, dtype=np.float64)
    period = float(pat.sum())
    edges = np.concatenate([[0.0], np.cumsum(pat)])
    phase = np.mod(np.asarray(s, dtype=np.float64), period)
    idx = np.clip(np.searchsorted(edges, phase, side="right") - 1, 0, pat.size - 1)
    return (idx % 2) == 0


def _polyline_mask(shape, points, closed, pattern=None):
    """折れ線のマスク。``pattern`` を渡すと破線(位相は弧長で連続)。"""
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    if pts.shape[0] < 2:
        raise ValueError("polyline requires at least 2 points")
    seq = list(pts) + ([pts[0]] if closed else [])
    m = np.zeros(shape, dtype=bool)
    if pattern is None:
        for i in range(len(seq) - 1):
            m |= _line_mask(shape, seq[i], seq[i + 1])
        return m
    H, W = shape
    s0 = 0.0
    for i in range(len(seq) - 1):
        (x0, y0), (x1, y1) = seq[i], seq[i + 1]
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        xs = np.linspace(x0, x1, n)
        ys = np.linspace(y0, y1, n)
        seg = float(np.hypot(x1 - x0, y1 - y0))
        t = np.linspace(0.0, 1.0, n) if n > 1 else np.zeros(1)
        on = _phase_on(s0 + t * seg, pattern)
        if on.any():
            xi = np.clip(np.round(xs[on]).astype(int), 0, W - 1)
            yi = np.clip(np.round(ys[on]).astype(int), 0, H - 1)
            m[yi, xi] = True
        s0 += seg                                  # 頂点をまたいで位相を継ぐ
    return m


def new_canvas(shape, color=_KEEP, style=None):
    """背景色つきの空キャンバスを作る(HALCON の ``set_draw`` + 塗り潰しに当たる下地)。

    Args:
        shape: ``(H, W)`` か ``(H, W, C)``。``(H, W)`` に RGB 色を渡すと ``(H, W, 3)``
            を返す(色の長さがチャンネル数を決める)。
        color: 背景色。float / RGB 三つ組 / :mod:`palette` の役割名。既定は 0.0(黒)。
        style: :class:`drawstyle.DrawStyle`。``color`` 未指定ならこのスタイルの
            **塗り色**(``fill_color`` が無ければ ``color``)を背景に使う。

    Returns:
        ``[0,1]`` にクリップした float64 配列。

    Raises ValueError: shape の次元が 2/3 でない、寸法が 1 未満か整数でない、
        チャンネル数が 1 未満、色が不正。
    """
    st = style if style is not None else drawstyle.current_style()
    if st is not None and not isinstance(st, DrawStyle):
        raise ValueError(f"style must be a DrawStyle, got {type(st).__name__}")
    if color is _KEEP:
        col = 0.0 if st is None else st.interior_color()
    else:
        col = drawstyle.resolve_color(color, "okabe_ito" if st is None else st.scheme)
    dims = tuple(shape)
    if len(dims) not in (2, 3):
        raise ValueError(f"shape must be (H,W) or (H,W,C) (got: {dims})")
    for v in dims:
        if isinstance(v, bool) or not float(v).is_integer() or int(v) < 1:
            raise ValueError(f"shape entries must be integers >= 1 (got: {dims})")
    H, W = int(dims[0]), int(dims[1])
    if len(dims) == 3:
        a = np.zeros((H, W, int(dims[2])), dtype=np.float64)
    elif np.isscalar(col):
        a = np.zeros((H, W), dtype=np.float64)
    else:
        a = np.zeros((H, W, len(col)), dtype=np.float64)
    a[...] = _color_for(a, col)
    return np.clip(a, 0.0, 1.0)


def draw_line(img, p0, p1, color=_KEEP, width=_KEEP, style=None):
    """(x,y)=p0 から p1 へ太さ width の直線を描く。

    ``style`` の ``line_style`` が実線以外なら破線で描く(位相は始点から弧長で進む)。
    """
    a = _prep(img)
    col, wid, pattern, _ = _settle(color, width, style)
    if pattern is None:
        return _apply(a, _line_mask(a.shape[:2], p0, p1), col, wid)
    return _apply(a, _polyline_mask(a.shape[:2], [p0, p1], False, pattern), col, wid)


def draw_polyline(img, points, color=_KEEP, width=_KEEP, closed=False, style=None):
    """点列 (N,2) を結ぶ折れ線を描く(closed=True で始点に戻る=多角形)。

    破線の位相は頂点をまたいで連続する(モジュール docstring「破線の位相」参照)。
    """
    a = _prep(img)
    col, wid, pattern, _ = _settle(color, width, style)
    return _apply(a, _polyline_mask(a.shape[:2], points, closed, pattern), col, wid)


def draw_contour(img, contour, color=_KEEP, width=_KEEP, style=None):
    """XLD 輪郭 ``{cs:[Nx2 (row,col),...]}`` または (N,2) 配列を閉じて描く。

    XLD 輪郭は (row,col) 順なので (x,y)=(col,row) に変換して描画する。
    破線の位相は輪郭ごとに 0 から始まり、その輪郭の中では弧長で連続する
    (輪郭は独立した図形なので、前の輪郭の位相を引きずらせない)。
    """
    a = _prep(img)
    col, wid, pattern, _ = _settle(color, width, style)
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
        m |= _polyline_mask(a.shape[:2], p, True, pattern)
    return _apply(a, m, col, wid)


def draw_circle(img, center, radius, color=_KEEP, width=_KEEP, fill=_KEEP, style=None):
    """中心 (x,y)・半径 radius の円(fill=True で塗り潰し)。

    ``fill`` を省略すると ``style.draw``(``"margin"`` / ``"fill"``、HALCON の
    ``set_draw`` 相当)に従う。``style.fill_color`` を指定した塗り潰しでは
    **内部を塗り色・縁を線色**で描く(塗りと輪郭の色を分けられる)。
    ``line_style`` は輪郭に効き、位相は θ=atan2(y-cy, x-cx) 増加方向の弧長
    ``r·θ`` で進む(継ぎ目 θ=0 でパターンが合うことは保証しない)。
    """
    a = _prep(img)
    col, wid, pattern, st = _settle(color, width, style)
    do_fill = ((st is not None and st.draw == "fill") if fill is _KEEP else bool(fill))
    H, W = a.shape[:2]
    cx, cy = float(center[0]), float(center[1])
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot(xx - cx, yy - cy)
    if do_fill:
        a[d <= radius] = _color_for(a, col if st is None else st.interior_color())
        if st is None or st.fill_color is None:
            return a                                  # 従来どおり(塗り色のみ)
    m = np.abs(d - radius) <= max(0.6, wid / 2.0)
    if pattern is not None:
        s = np.mod(np.arctan2(yy - cy, xx - cx), 2.0 * np.pi) * max(float(radius), 1e-9)
        m &= _phase_on(s, pattern)
    a[m] = _color_for(a, col)
    return a


def draw_markers(img, points, color=_KEEP, size=4, shape="cross", width=_KEEP, style=None):
    """点列 (N,2) の各点にマーカーを描く。shape='cross'|'square'|'dot'。

    マーカーは ``style`` の色と線幅に従うが、**``line_style`` は無視して常に実線**で
    描く。マーカーは記号であって線ではなく、パターン周期がマーカー寸法より長いと
    「置いた場所によってマーカーが丸ごと消える」からで、消えたことは図を見るまで
    分からない(:mod:`palette` の ``ROLE_MARKERS`` と同じ発想 ―― 記号は必ず出す)。
    """
    a = _prep(img)
    col, wid, _pattern, st = _settle(color, width, style)
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    solid = None if st is None else st.with_(line_style="solid")
    if shape == "dot":
        for x, y in pts:
            a = draw_circle(a, (x, y), size, col, width=wid, fill=True, style=solid)
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
    return _apply(a, m, col, wid)

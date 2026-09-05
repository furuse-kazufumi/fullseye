# -*- coding: utf-8 -*-
"""Qiita 記事の図を **fullseye 自身の描画 op** で作る。

数値は 2026-09-06 に取った実測値をそのまま埋め込む(再測定はしない —— 記事の図が
走らせるたびに変わると、本文の数字と図がずれる)。出典はこのファイル内のコメント。

出力: docs/articles/assets/blas_*.png
"""
from __future__ import annotations

import os
import sys

import numpy as np

ROOT = r"C:\dev\projects\imgevolve"
sys.path.insert(0, ROOT)

import annotate as A                                            # noqa: E402

OUT = os.path.join(ROOT, "docs", "articles", "assets")
os.makedirs(OUT, exist_ok=True)

W, H = 1000, 620
MARGIN = (110, 70, 40, 70)          # left, top, right, bottom

THREADS = (1, 2, 4, 8, 24)

# --- 実測値 (24 論理 CPU / OpenBLAS 0.3.31 / numpy 2.4.6 / Windows、中央値) --- #
SVD = {                              # n -> ms per thread count
    48:   (0.165, 0.195, 0.266, 0.344, 0.651),
    96:   (0.650, 0.918, 1.081, 1.305, 2.217),
    192:  (3.721, 5.079, 5.576, 5.884, 7.727),
    384:  (19.331, 23.572, 21.686, 28.090, 36.243),
    768:  (126.939, 109.702, 105.845, 115.009, 358.628),
}
GEMM = {
    96:   (0.028, 0.062, 0.031, 0.030, 0.029),
    192:  (0.203, 0.157, 0.158, 0.118, 0.612),
    384:  (1.793, 1.193, 0.804, 0.615, 1.908),
    768:  (13.994, 7.400, 3.904, 2.404, 3.433),
}
#: 2 の冪の前後(単スレッドの実効 GFLOPS)
PAD = [(255, 27.9), (256, 26.1), (257, 30.4), (264, 30.9),
       (511, 41.4), (512, 34.6), (513, 41.2), (520, 44.1),
       (1023, 43.9), (1024, 35.9), (1025, 44.4), (1032, 44.5)]
#: 92 升の格子での採点 (規則, 失う ms, 1.2 倍超えの升目, 最悪倍率)
RULES = [
    ("何もしない\n(24t)", 3975, 79, 19.91),
    ("要素数", 235, 14, 2.50),
    ("長辺", 241, 29, 3.89),
    ("短辺\n(採用)", 303, 5, 1.41),
]

#: スレッド数 5 本の系列色。Okabe & Ito(2008)の定性パレットから直に取る
#: —— 役割名(right/wrong など)は意味を持つので、単なる系列には使わない
#: (この repo は「赤緑インジケータ禁止」= 立場で意味が反転する配色を避ける)。
_PALETTE = (
    (0.000, 0.447, 0.698),      # blue      1t
    (0.337, 0.706, 0.914),      # sky       2t
    (0.000, 0.620, 0.451),      # green     4t
    (0.902, 0.624, 0.000),      # orange    8t
    (0.835, 0.369, 0.000),      # vermillion 24t
)


def _canvas(w=W, h=H, v=0.10):
    return np.full((h, w, 3), v, np.float64)


def _axes(w=W, h=H, xlim=(0, 1), ylim=(0, 1), margin=None, **kw):
    m = margin or MARGIN
    rect = (m[0], m[1], w - m[0] - m[2], h - m[1] - m[3])
    return A.axes_transform(rect, xlim, ylim, **kw)


def _frame(img, ax, xticks, yticks, xfmt="{:g}", yfmt="{:g}"):
    img = A.grid_lines(img, ax, xticks=xticks, yticks=yticks, alpha=0.22)
    img = A.axes_frame(img, ax)
    img = A.ticks(img, ax, xticks=xticks, yticks=None, label_fmt=xfmt, font_size=13)
    img = A.ticks(img, ax, xticks=None, yticks=yticks, label_fmt=yfmt, font_size=13)
    return img


def fig_threads():
    """図 1: 分解はスレッドで速くならない / 行列積は速くなる。"""
    ns = sorted(SVD)
    lx = [np.log10(n) for n in ns]
    ax = _axes(xlim=(min(lx) - 0.08, max(lx) + 0.08), ylim=(-1.0, 2.75))
    img = _canvas()
    xt = [np.log10(n) for n in ns]
    yt = [-1, 0, 1, 2]
    # ★1 スレッドが最速だった範囲を半透明で敷く。線を隠さないよう先に置き、
    #   alpha を低く保つ(帯そのものが主張しすぎると、線の比較が読みにくくなる)。
    bx0, by0 = A.data_to_pixel(ax, min(lx) - 0.08, 2.75)
    bx1, by1 = A.data_to_pixel(ax, np.log10(384) + 0.04, -1.0)
    img = A.filled_polygon(img, [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)],
                           color=(0.00, 0.447, 0.698), alpha=0.13)
    img = A.grid_lines(img, ax, xticks=xt, yticks=yt, alpha=0.22)
    img = A.axes_frame(img, ax)
    # 目盛りのラベルは自前で置く(対数軸を人が読める形に)
    for n, x in zip(ns, xt):
        px, py = A.data_to_pixel(ax, x, -1.0)
        img = A.text_box(img, f"{n}", (int(px), int(py) + 16), anchor="ct",
                         font_size=13, box_alpha=0.0)
    for e, y in zip(("0.1", "1", "10", "100"), yt):
        px, py = A.data_to_pixel(ax, min(lx) - 0.08, y)
        img = A.text_box(img, e, (int(px) - 10, int(py)), anchor="rm",
                         font_size=13, box_alpha=0.0)

    for i, t in enumerate(THREADS):
        ys = [np.log10(SVD[n][i]) for n in ns]
        img = A.plot_series(img, ax, lx, ys, kind="line",
                            color=_PALETTE[i % len(_PALETTE)], width=3)
        img = A.plot_series(img, ax, lx, ys, kind="scatter",
                            color=_PALETTE[i % len(_PALETTE)], marker_size=5)
    img = A.legend_box(img, [(_PALETTE[i % len(_PALETTE)], f"{t} スレッド")
                             for i, t in enumerate(THREADS)],
                       (MARGIN[0] + 18, MARGIN[1] + 14), font_size=14)
    img = A.text_box(img, "SVD (n×n) — スレッドを増やすほど遅い",
                     (W // 2, 26), anchor="ct", font_size=19, box_alpha=0.0)
    img = A.text_box(img, "この帯の中では 1 スレッドが最速",
                     (MARGIN[0] + 18, MARGIN[1] + 178), anchor="lt",
                     font_size=13, box_alpha=0.45)
    img = A.text_box(img, "行列の辺 n", (W // 2, H - 8), anchor="cb",
                     font_size=14, box_alpha=0.0)
    img = A.text_box(img, "時間 [ms]", (50, MARGIN[1] - 12), anchor="lb",
                     font_size=14, box_alpha=0.0)
    img = A.text_box(img,
                     "24 論理 CPU / OpenBLAS 0.3.31 / numpy 2.4.6 / 中央値",
                     (W - 22, H - 8), anchor="rb", font_size=12, box_alpha=0.0)
    return img


def fig_gemm():
    """図 2: 行列積は逆の傾き —— だから全体を絞ってはいけない。"""
    ns = sorted(GEMM)
    lx = [np.log10(n) for n in ns]
    ax = _axes(xlim=(min(lx) - 0.08, max(lx) + 0.08), ylim=(-1.8, 1.3))
    img = _canvas()
    xt = list(lx)
    yt = [-1.5, -1, 0, 1]
    img = A.grid_lines(img, ax, xticks=xt, yticks=yt, alpha=0.22)
    img = A.axes_frame(img, ax)
    for n, x in zip(ns, xt):
        px, py = A.data_to_pixel(ax, x, -1.8)
        img = A.text_box(img, f"{n}", (int(px), int(py) + 16), anchor="ct",
                         font_size=13, box_alpha=0.0)
    for e, y in zip(("0.03", "0.1", "1", "10"), yt):
        px, py = A.data_to_pixel(ax, min(lx) - 0.08, y)
        img = A.text_box(img, e, (int(px) - 10, int(py)), anchor="rm",
                         font_size=13, box_alpha=0.0)
    for i, t in enumerate(THREADS):
        ys = [np.log10(GEMM[n][i]) for n in ns]
        img = A.plot_series(img, ax, lx, ys, kind="line",
                            color=_PALETTE[i % len(_PALETTE)], width=3)
        img = A.plot_series(img, ax, lx, ys, kind="scatter",
                            color=_PALETTE[i % len(_PALETTE)], marker_size=5)
    img = A.legend_box(img, [(_PALETTE[i % len(_PALETTE)], f"{t} スレッド")
                             for i, t in enumerate(THREADS)],
                       (MARGIN[0] + 18, MARGIN[1] + 14), font_size=14)
    img = A.text_box(img, "行列積 a @ a — こちらはスレッドで速くなる（傾きが逆）",
                     (W // 2, 26), anchor="ct", font_size=19, box_alpha=0.0)
    img = A.text_box(img, "行列の辺 n", (W // 2, H - 8), anchor="cb",
                     font_size=14, box_alpha=0.0)
    img = A.text_box(img, "時間 [ms]", (50, MARGIN[1] - 12), anchor="lb",
                     font_size=14, box_alpha=0.0)
    img = A.text_box(img, "768 で 1t 14.0ms / 8t 2.4ms = 5.8 倍",
                     (W - 40, H - MARGIN[3] - 24), anchor="rb", font_size=13,
                     box_alpha=0.55)
    return img


def fig_padding():
    """図 3: 2 の冪だけ遅い(キャッシュのセット競合)。"""
    ys = [g for _, g in PAD]
    ax = _axes(xlim=(-0.7, len(PAD) - 0.3), ylim=(20, 50))
    img = _canvas()
    yt = [20, 25, 30, 35, 40, 45, 50]
    img = A.grid_lines(img, ax, xticks=None, yticks=yt, alpha=0.22)
    img = A.axes_frame(img, ax)
    img = A.ticks(img, ax, xticks=[], yticks=yt, label_fmt="{:g}", font_size=13)
    c_pow2 = (0.835, 0.369, 0.000)
    c_other = (0.000, 0.447, 0.698)
    for i, (n, g) in enumerate(PAD):
        col = c_pow2 if (n & (n - 1)) == 0 else c_other
        img = _bar(img, ax, i, g, 0.33, col, y0=20.0)
        px, py = A.data_to_pixel(ax, i, 20)
        img = A.text_box(img, str(n), (int(px), int(py) + 14), anchor="ct",
                         font_size=12, box_alpha=0.0)
    img = A.legend_box(img, [(c_pow2, "2 の冪"), (c_other, "その前後")],
                       (W - 40, MARGIN[1] + 14), anchor="rt", font_size=14)
    img = A.text_box(img, "2 の冪の辺だけ遅い — SVD の単スレッド実効性能",
                     (W // 2, 26), anchor="ct", font_size=19, box_alpha=0.0)
    img = A.text_box(img, "行列の辺 n", (W // 2, H - 8), anchor="cb",
                     font_size=14, box_alpha=0.0)
    img = A.text_box(img, "GFLOPS", (50, MARGIN[1] - 12), anchor="lb",
                     font_size=13, box_alpha=0.0)
    img = A.text_box(img, "13〜19% 遅い。ただし最速スレッド数は変わらない",
                     (W - 22, H - 8), anchor="rb", font_size=12, box_alpha=0.0)
    return img


def _bar(img, ax, xc, y, half, color, y0=0.0):
    """棒 1 本を矩形で描く。

    ``plot_series(kind="bar")`` は**点が 1 個だと棒の幅を軸幅から決める**
    (``step = rw``)ので、色を変えるために 1 本ずつ呼ぶと軸いっぱいの帯になる。
    色分けしたいときは自分で矩形を置くほうが素直。
    """
    x0, ytop = A.data_to_pixel(ax, xc - half, y)
    x1, ybot = A.data_to_pixel(ax, xc + half, y0)
    poly = [(x0, ytop), (x1, ytop), (x1, ybot), (x0, ybot)]
    return A.filled_polygon(img, poly, color=color)


def fig_rules():
    """図 4: 合計ではなく最悪値で選んだ。"""
    img = _canvas()
    ax = _axes(xlim=(-0.6, len(RULES) - 0.4), ylim=(0, 21),
               margin=(110, 70, 40, 170))
    yt = [0, 5, 10, 15, 20]
    img = A.grid_lines(img, ax, xticks=None, yticks=yt, alpha=0.22)
    img = A.axes_frame(img, ax)
    img = A.ticks(img, ax, xticks=[], yticks=yt, label_fmt="{:g}", font_size=13)
    colors = [(0.835, 0.369, 0.000), (0.62, 0.62, 0.66),
              (0.62, 0.62, 0.66), (0.000, 0.447, 0.698)]
    for i, (lab, lost, cells, w) in enumerate(RULES):
        img = _bar(img, ax, i, w, 0.26, colors[i])
        px, py = A.data_to_pixel(ax, i, w)
        img = A.text_box(img, "%.2f 倍" % w, (int(px), int(py) - 8), anchor="cb",
                         font_size=15, box_alpha=0.0)
        px0, py0 = A.data_to_pixel(ax, i, 0)
        img = A.text_box(img, lab, (int(px0), int(py0) + 16), anchor="ct",
                         font_size=15, box_alpha=0.0)
        note = "失う %dms" % lost + chr(10) + "1.2 倍超え %d/92" % cells
        img = A.text_box(img, note, (int(px0), int(py0) + 78), anchor="ct",
                         font_size=12, box_alpha=0.0)
    img = A.text_box(img, "同じ格子 92 升での最悪倍率 — 合計ではなくここで選んだ",
                     (W // 2, 26), anchor="ct", font_size=19, box_alpha=0.0)
    img = A.text_box(img, "最悪の升目で何倍遅いか", (50, MARGIN[1] - 12),
                     anchor="lb", font_size=13, box_alpha=0.0)
    img = A.text_box(img,
                     "合計だけ見ると要素数(235ms)が最良。最悪値で見ると短辺(1.41 倍)。",
                     (W // 2, H - 8), anchor="cb", font_size=13, box_alpha=0.0)
    return img


def main():
    import imgio
    figs = {
        "blas_threads_svd": fig_threads(),
        "blas_threads_gemm": fig_gemm(),
        "blas_padding": fig_padding(),
        "blas_rules": fig_rules(),
    }
    for name, img in figs.items():
        p = os.path.join(OUT, name + ".png")
        imgio.save(p, np.clip(img, 0, 1))
        print(f"wrote {p}  {img.shape}")


if __name__ == "__main__":
    main()

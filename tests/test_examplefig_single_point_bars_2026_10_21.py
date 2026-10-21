"""render_plot: 1 点だけの棒の系列(棒ごとに色を変える描き方)が隣の棒と重ならないこと。

2026-10-21、製造公差 PoC(2026.271)の歩留まりの対比図で、x=0 と x=1 の 2 本の棒がそれぞれ
描画域の 70 % の幅で描かれて重なっていた(plot_series は系列内の点の間隔から幅を決めるが、
1 点の系列には間隔が無い)。render_plot が全系列の棒の x から間隔を求めて渡す。
"""
from __future__ import annotations

import numpy as np

import examplefig as figs


def _columns(mask: np.ndarray) -> set[int]:
    return set(np.nonzero(mask.any(axis=0))[0].tolist())


def _hue_masks(img: np.ndarray):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    orange = (r > 0.6) & (b < 0.35) & (g < 0.75)
    blue = (b > 0.5) & (r < 0.45)
    return orange, blue


def test_two_single_point_bar_series_do_not_overlap():
    img = figs.render_plot([("", [0], [0.8]), ("", [1], [0.5])], size=(640, 430),
                           kinds=["bar", "bar"], colors=["wrong", "right"],
                           xlim=(-0.5, 1.5), ylim=(0, 1))
    orange, blue = _hue_masks(np.asarray(img))
    co, cb = _columns(orange), _columns(blue)
    plot_w = 640 - 96
    assert co and cb, (len(co), len(cb))
    assert not (co & cb), "2 本の棒の列が重なっている"
    # 間隔 1 の 70 %(= 描画域 2 単位の 35 %)に収まる。旧挙動は各 70 % で、ここで落ちる。
    assert len(co) <= 0.36 * plot_w, len(co)
    assert len(cb) <= 0.36 * plot_w, len(cb)
    assert len(co) >= 0.30 * plot_w, len(co)
    # 左の棒(x=0)は右の棒(x=1)より左にある。
    assert max(co) < min(cb)


def test_single_bar_uses_the_tick_spacing():
    img = figs.render_plot([("", [0], [0.8])], size=(640, 430), kinds=["bar"],
                           colors=["wrong"], xlim=(-0.5, 1.5), ylim=(0, 1))
    orange, _ = _hue_masks(np.asarray(img))
    co = _columns(orange)
    plot_w = 640 - 96
    assert co
    assert len(co) < 0.5 * plot_w, len(co)


def test_multi_point_bar_series_are_unchanged():
    x = np.arange(5, dtype=float)
    before = figs.render_plot([("", x, x + 1.0)], size=(640, 430), kinds=["bar"],
                              xlim=(-0.5, 4.5), ylim=(0, 6))
    orange, blue = _hue_masks(np.asarray(before))
    # 既定色 reference(青)。5 本が別々の列に立つ。
    cols = sorted(_columns(blue))
    runs = 1 + int(np.sum(np.diff(cols) > 1))
    assert runs == 5, runs

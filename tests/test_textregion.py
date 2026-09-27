# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""textregion — Stroke Width Transform 系 op の厳密な真値と fail-closed を検査する。

真値は 3 種類: (1) 幅 w の矩形ストロークで SWT = w(整数、厳密)、(2) **第 2 実装** =
軸に沿うストロークの幅は、勾配の軸に沿った文字画素の連の長さ(run length)に等しい、
(3) 拡大 k 倍で SWT も k 倍。乱数は使わない(構造データで対称性の破れを見る)。
"""
from __future__ import annotations

import numpy as np
import pytest

import textregion as T


def _hbar(w: int, h: int = 80, wd: int = 120, dark: bool = True):
    img = np.ones((h, wd)) if dark else np.zeros((h, wd))
    img[30:30 + w, 10:110] = 0.0 if dark else 1.0
    return img


def _vbar(w: int):
    img = np.ones((120, 80))
    img[10:110, 30:30 + w] = 0.0
    return img


def _run_length_width(ink: np.ndarray, axis: int) -> np.ndarray:
    """第 2 実装: 各文字画素について、軸 axis に沿った文字画素の連の長さ。"""
    out = np.zeros(ink.shape, int)
    a = np.moveaxis(ink, axis, 0)
    o = np.moveaxis(out, axis, 0)
    for j in range(a.shape[1]):
        col = a[:, j]
        i = 0
        while i < col.size:
            if col[i]:
                k = i
                while k < col.size and col[k]:
                    k += 1
                o[i:k, j] = k - i
                i = k
            else:
                i += 1
    return out


# ---- 恒等式 1: 矩形ストロークの幅 -----------------------------------------------
@pytest.mark.parametrize("w", [2, 3, 5, 9, 16])
def test_horizontal_bar_width_is_exact(w):
    r = T.swt_map(_hbar(w))
    inside = r["swt"][30:30 + w, 20:100]
    assert np.all(inside == w), np.unique(inside)


@pytest.mark.parametrize("w", [2, 4, 7])
def test_vertical_bar_width_is_exact(w):
    r = T.swt_map(_vbar(w))
    inside = r["swt"][20:100, 30:30 + w]
    assert np.all(inside == w)


def test_light_on_dark_is_the_same_width():
    r = T.swt_map(_hbar(5, dark=False), dark_on_light=False)
    assert np.all(r["swt"][30:35, 20:100] == 5)


# ---- 恒等式 2: 第 2 実装(連の長さ) ------------------------------------------------
@pytest.mark.parametrize("w", [1, 2, 5, 11])
def test_swt_agrees_with_run_length_second_implementation(w):
    img = _hbar(w)
    ink = img < 0.5
    r = T.swt_map(img)
    rl = _run_length_width(ink, axis=0)
    inside = (slice(30, 30 + w), slice(20, 100))
    assert np.array_equal(r["swt"][inside], rl[inside])


# ---- 恒等式 3: 拡大 -----------------------------------------------------------------
@pytest.mark.parametrize("k", [2, 3])
def test_scaling_the_image_scales_the_width(k):
    small = _hbar(5)
    big = np.kron(small, np.ones((k, k)))
    a = T.swt_map(small)["swt"]
    b = T.swt_map(big)["swt"]
    assert np.median(a[a > 0]) == 5 and np.median(b[b > 0]) == 5 * k


# ---- 幅 1(境界画素が両側とも地に接する)も拾う ---------------------------------------
def test_one_pixel_stroke_is_width_one():
    """★2026-09-27: size 16 のフォントは縦の連が 1 px で、幅 1 を捨てると行が全部消えた。"""
    r = T.swt_map(_hbar(1))
    assert np.all(r["swt"][30, 20:100] == 1) and r["n_hits"] > 0


# ---- 候補と行 -------------------------------------------------------------------------
def test_two_bars_of_equal_width_become_two_candidates_and_one_line():
    """★試験側の前提を実測で直した(2026-09-27): 棒は縦横比 10 以内、隙間は高さの 3 倍以内。"""
    img = np.ones((80, 200))
    img[30:35, 10:50] = 0.0        # 5 × 40(縦横比 8)
    img[30:35, 60:100] = 0.0       # 隙間 10 ≤ 3 × 5
    c = T.text_candidates(T.swt_map(img)["swt"])
    assert len(c["boxes"]) == 2 and np.all(c["stroke_width"] == 5)
    ln = T.text_lines(c["boxes"], c["stroke_width"])
    assert len(ln["lines"]) == 1 and tuple(ln["lines"][0]) == (30, 10, 35, 100)


def test_bars_of_very_different_height_are_not_one_line():
    img = np.ones((80, 200))
    img[30:33, 10:34] = 0.0        # 3 × 24(縦横比 8)
    img[20:45, 40:90] = 0.0        # 25 × 50、高さ比 8 > 2
    c = T.text_candidates(T.swt_map(img)["swt"])
    assert len(c["boxes"]) == 2
    ln = T.text_lines(c["boxes"], c["stroke_width"])
    assert len(ln["lines"]) == 2


def test_a_bar_too_elongated_for_a_letter_is_rejected_by_the_aspect_rule():
    """罫線のような 3 × 50(縦横比 16.7)は文字候補にならない —— 規則が効いていることを固定。"""
    img = np.ones((80, 200))
    img[30:33, 10:60] = 0.0
    c = T.text_candidates(T.swt_map(img)["swt"])
    assert len(c["boxes"]) == 0 and c["n_components"] == 1


def test_a_filled_square_has_uniform_width_equal_to_its_side():
    """★円盤は 2 回目の走査(中央値)で幅が直径に揃うので分散では落ちない(実測 std/mean 0.00)。
    分散規則の試験は矩形で: 一辺 s の正方形は SWT = s が全画素で厳密。"""
    img = np.ones((100, 100))
    img[30:51, 40:61] = 0.0
    r = T.swt_map(img)
    inside = r["swt"][32:49, 42:59]
    assert np.all(inside == 21)
    c = T.text_candidates(r["swt"])
    assert len(c["boxes"]) == 1 and c["stroke_width"][0] == 21


# ---- fail-closed ---------------------------------------------------------------------
@pytest.mark.parametrize("bad", [np.zeros((0, 0)), np.ones((3, 3, 2)), np.array([[0.0, np.nan], [1.0, 0.0]])])
def test_bad_images_are_refused(bad):
    with pytest.raises(ValueError):
        T.swt_map(bad)


def test_flat_image_gives_no_edges_and_no_error():
    r = T.swt_map(np.full((20, 20), 0.5))
    assert r["n_rays"] == 0 and not np.any(r["swt"] > 0)


def test_text_lines_refuses_mismatched_widths():
    with pytest.raises(ValueError):
        T.text_lines(np.array([[0, 0, 5, 5]]), stroke_width=[1.0, 2.0])

# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""annotate(図注の層)を**構成的な真値**で検証する。

図を描く op は「例外が出ない」だけでは何も保証できない ―― 一番怖いのは
**黙って間違った絵を返す**ことで、それは機械検査を素通りする。だからここでは
次の 4 つを数字で確かめる:

  1. **閉形式との一致** — スケールバーの画素長 = ``round(length/units_per_pixel)``、
     目盛りの位置 = ``x0 + (v-lo)/(hi-lo)*(w-1)``、α 合成 = ``a*f+(1-a)*b``、
     凡例の高さ = ``2*pad + n*row_h + (n-1)*gap``。
  2. **座標系の取り違え** — row は下向き / 点は (x,y) / マスクは [row,col]。
     ここを間違えた実装は「それらしい絵」を返すので、**非正方**の画像と
     非対称な図形で狙い撃ちする。
  3. **fail-closed** — 画像外・負の寸法・非有限・空の系列・未知の役割名・
     収まらない文字は、文書化された ValueError。
  4. **決定的** — 同じ入力から同じバイト列。
"""
from __future__ import annotations

import numpy as np
import pytest

import annotate as A
import imagedraw
import opsannotate
import palette

# 非正方(H != W)を既定にする。(row,col) と (x,y) の取り違えは正方形だと
# 形が合ってしまって気づけない。
H, W = 120, 200


def _canvas(value=0.10, channels=3):
    if channels is None:
        return np.full((H, W), value, dtype=np.float64)
    return np.full((H, W, channels), value, dtype=np.float64)


# ------------------------------------------------------------------ #
# 1. 閉形式との一致
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("length,upp", [(100.0, 2.0), (75.0, 0.5), (37.0, 1.0), (12.0, 0.25)])
def test_scale_bar_pixel_length_matches_the_physical_length(length, upp):
    """バーの画素長 == round(物理長 / 分解能)。**これが唯一の真値**。"""
    img = _canvas(0.0)
    out = A.scale_bar(img, length, upp, unit="um", xy=(10, 100), anchor="lb",
                      color=(1.0, 1.0, 1.0), thickness=4, label=False)
    lit = np.isclose(out[..., 0], 1.0)
    cols = np.flatnonzero(lit.any(axis=0))
    assert cols.size == int(round(length / upp)), (
        f"{length} at {upp}/px should be {int(round(length / upp))}px, drew {cols.size}px")
    rows = np.flatnonzero(lit.any(axis=1))
    assert rows.size == 4                                    # thickness をそのまま


def test_scale_bar_shorter_than_a_pixel_is_refused():
    with pytest.raises(ValueError, match="shorter than one pixel"):
        A.scale_bar(_canvas(), 0.4, 1.0, unit="um")


def test_axes_transform_is_the_closed_form():
    ax = A.axes_transform((20, 10, 101, 51), (0.0, 10.0), (-1.0, 1.0))
    px, py = A.data_to_pixel(ax, np.array([0.0, 5.0, 10.0]), np.array([-1.0, 0.0, 1.0]))
    assert np.allclose(px, [20.0, 70.0, 120.0], atol=1e-12)  # 20 + t*(101-1)
    # invert_y: ylim[0] は **下端**(row は下向き)
    assert np.allclose(py, [60.0, 35.0, 10.0], atol=1e-12)   # 10 + 50 - t*50


def test_axes_y_axis_points_up_not_down():
    """row は下向き / グラフの y は上向き ―― 反転を忘れた実装をここで殺す。"""
    ax = A.axes_transform((0, 0, 100, 100), (0, 1), (0, 1))
    _, py_lo = A.data_to_pixel(ax, 0.0, 0.0)
    _, py_hi = A.data_to_pixel(ax, 0.0, 1.0)
    assert py_lo > py_hi, "ylim の下端が画像の下(row が大)に来ていない"
    ax2 = A.axes_transform((0, 0, 100, 100), (0, 1), (0, 1), invert_y=False)
    _, q_lo = A.data_to_pixel(ax2, 0.0, 0.0)
    _, q_hi = A.data_to_pixel(ax2, 0.0, 1.0)
    assert q_lo < q_hi


def test_axes_log_scale_is_decade_linear():
    ax = A.axes_transform((40, 0, 200, 50), (1.0, 1000.0), (0, 1), xscale="log")
    px, _ = A.data_to_pixel(ax, np.array([1.0, 10.0, 100.0, 1000.0]), np.zeros(4))
    span = 199.0
    assert np.allclose(px, 40.0 + np.array([0, 1, 2, 3]) / 3.0 * span, atol=1e-9)


def test_axes_reversed_limits_do_not_collapse_to_one_end():
    """反転軸(lo > hi)。``np.clip(v, lo, hi)`` を使う実装は全点が端に貼り付く。"""
    ax = A.axes_transform((0, 0, 101, 51), (10.0, 0.0), (0.0, 1.0))
    px, _ = A.data_to_pixel(ax, np.array([10.0, 5.0, 0.0]), np.zeros(3))
    assert np.allclose(px, [0.0, 50.0, 100.0], atol=1e-12)
    assert len(set(np.round(px, 6))) == 3, "全点が同じ画素に潰れている"


@pytest.mark.parametrize("lo,hi,want", [
    (0.0, 10.0, [0, 2, 4, 6, 8, 10]),      # 端をどちらも含む(off-by-one なし)
    (0.0, 1.0, [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]),
    (-3.0, 3.0, [-2, 0, 2]),               # raw=1.2 -> step=2、端は目盛りに乗らない
    (0.0, 5.0, [0, 1, 2, 3, 4, 5]),
])
def test_nice_ticks_includes_both_ends(lo, hi, want):
    got = A.nice_ticks(lo, hi)
    assert np.allclose(got, want), f"{lo}..{hi}: {got} != {want}"


def test_nice_ticks_log_walks_decades():
    assert np.allclose(A.nice_ticks(1.0, 1000.0, scale="log"),
                       [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000])


def test_tick_marks_land_on_the_closed_form_positions():
    """描かれた目盛りの列 == data_to_pixel の丸め。**1 画素のずれも見逃さない**。"""
    ax = A.axes_transform((20, 10, 161, 61), (0.0, 8.0), (0.0, 1.0))
    img = _canvas(0.0)
    out = A.ticks(img, ax, xticks=[0.0, 2.0, 4.0, 6.0, 8.0], yticks=[],
                  color=(1.0, 1.0, 1.0), tick_len=6, label=False, width=1)
    band = out[10 + 60 + 1:10 + 60 + 6, :, 0]                # 枠の外に出た部分だけ
    cols = np.flatnonzero(np.isclose(band, 1.0).any(axis=0))
    want, _ = A.data_to_pixel(ax, np.array([0.0, 2.0, 4.0, 6.0, 8.0]), np.zeros(5))
    assert np.array_equal(cols, np.round(want).astype(int))


def test_alpha_blend_is_exactly_the_documented_formula():
    """α 合成は ``a*f + (1-a)*b``。順序も係数も**厳密一致**で確かめる。"""
    base = np.random.default_rng(0).uniform(0.0, 1.0, (H, W, 3))
    mask = np.zeros((H, W), bool)
    mask[30:70, 20:90] = True
    alpha = 0.37
    col = np.asarray(palette.role_color("wrong"), np.float64)
    out = A.overlay_mask(base, mask, "wrong", alpha)
    want = base.copy()
    want[mask] = alpha * col + (1.0 - alpha) * base[mask]
    assert np.array_equal(out, want), f"max |diff| = {np.abs(out - want).max()}"
    assert np.array_equal(out[~mask], base[~mask])           # マスク外は無傷


def test_alpha_zero_and_one_are_the_endpoints():
    base = _canvas(0.3)
    m = np.zeros((H, W), bool)
    m[10:20, 10:20] = True
    assert np.array_equal(A.overlay_mask(base, m, "right", 0.0), base)
    one = A.overlay_mask(base, m, "right", 1.0)
    assert np.allclose(one[m], palette.role_color("right"))


def test_legend_box_height_is_the_closed_form():
    """箱の高さ = 2*pad + n*row_h + (n-1)*row_gap。"""
    pad, gap, swatch, fs = 8, 4, 14, 13
    for n in (1, 2, 3, 5):
        rows = [("right", f"row {i}") for i in range(n)]
        m = A.measure_text("row 0", font_size=fs)
        row_h = max(swatch, m["height"])
        want = 2 * pad + n * row_h + (n - 1) * gap
        img = np.zeros((want + 40, W, 3))                    # 箱が入る高さを用意する
        out = A.legend_box(img, rows, (4, 4), swatch=swatch, row_gap=gap, pad=pad,
                           font_size=fs, box_color=(1.0, 1.0, 1.0), box_alpha=1.0,
                           border=0)
        rows_lit = np.flatnonzero((out[..., 0] > 0.5).any(axis=1))
        assert rows_lit.size == want, f"n={n}: drew {rows_lit.size}px, closed form {want}px"


def test_legend_can_carry_the_role_markers():
    """色だけに意味を載せない ―― ``markers=True`` で記号を併記できる。"""
    img = _canvas(0.0)
    plain = A.legend_box(img, [("wrong", "spacing なし")], (4, 4), markers=False)
    marked = A.legend_box(img, [("wrong", "spacing なし")], (4, 4), markers=True)
    assert not np.array_equal(plain, marked)
    assert palette.ROLE_MARKERS["wrong"] == "×"


def test_color_bar_reproduces_the_lut_end_to_end():
    lut = palette.diverging_lut(64)
    img = _canvas(0.0)
    out = A.color_bar(img, lut, (20, 10, 12, 64), vmin=-1.0, vmax=1.0, border=0,
                      label_fmt="{:g}", font_size=10)
    top = out[10, 20:32, :3].mean(axis=0)
    bot = out[10 + 63, 20:32, :3].mean(axis=0)
    assert np.allclose(top, lut[-1], atol=1e-9), "縦バーの **上** が vmax でない"
    assert np.allclose(bot, lut[0], atol=1e-9), "縦バーの **下** が vmin でない"


def test_panel_grid_geometry_is_the_closed_form():
    panels = [np.full((40, 60, 3), 0.5) for _ in range(5)]
    pad, label_h, ncols = 10, 30, 3
    out = A.panel_grid(panels, [f"p{i}" for i in range(5)], ncols=ncols, pad=pad,
                       label_h=label_h, font_size=12)
    nrows = 2
    want_w = 2 * pad + ncols * 60 + (ncols - 1) * pad
    want_h = 2 * pad + nrows * (40 + label_h) + (nrows - 1) * pad
    assert out.shape[:2] == (want_h, want_w)


def test_compare_frame_keeps_both_pictures_byte_exact():
    left = np.random.default_rng(1).uniform(0, 1, (40, 50, 3))
    right = np.random.default_rng(2).uniform(0, 1, (40, 30, 3))
    out = A.compare_frame(left, right, layout="h", divider=3, gap=2, labels=None)
    assert out.shape == (40, 50 + 3 + 4 + 30, 3)
    assert np.array_equal(out[:, :50], left)
    assert np.array_equal(out[:, 50 + 7:], right)


def test_zoom_inset_is_nearest_neighbour_so_no_structure_is_invented():
    img = np.random.default_rng(3).uniform(0, 1, (H, W, 3))
    src = (10, 10, 12, 8)
    out = A.zoom_inset(img, src, (100, 40), factor=4, width=1, connect=False)
    crop = img[10:18, 10:22]
    big = np.repeat(np.repeat(crop, 4, axis=0), 4, axis=1)
    got = out[41:40 + 32 - 1, 101:100 + 48 - 1]              # 1px の枠を除く内側
    assert np.array_equal(got, big[1:-1, 1:-1])


def test_filled_polygon_area_matches_the_analytic_area():
    img = _canvas(0.0)
    tri = [(20.0, 20.0), (120.0, 20.0), (20.0, 100.0)]       # 直角三角形 100x80
    out = A.filled_polygon(img, tri, color=(1.0, 1.0, 1.0))
    got = int(np.count_nonzero(out[..., 0] > 0.5))
    want = 0.5 * 100.0 * 80.0
    assert abs(got - want) / want < 0.03, f"area {got} vs analytic {want}"


def test_ellipse_fill_area_matches_pi_a_b():
    img = _canvas(0.0)
    out = A.ellipse(img, (100.0, 60.0), (40.0, 25.0), 0.0, color=(1.0, 1.0, 1.0), fill=True)
    got = int(np.count_nonzero(out[..., 0] > 0.5))
    want = np.pi * 40.0 * 25.0
    assert abs(got - want) / want < 0.01, f"area {got} vs pi*a*b {want:.1f}"


def test_arc_span_matches_the_requested_angle():
    img = _canvas(0.0)
    full = A.arc(img, (100.0, 60.0), 40.0, 0.0, 359.999, color=(1.0, 1.0, 1.0), width=1)
    quarter = A.arc(img, (100.0, 60.0), 40.0, 0.0, 90.0, color=(1.0, 1.0, 1.0), width=1)
    nf = np.count_nonzero(full[..., 0] > 0.5)
    nq = np.count_nonzero(quarter[..., 0] > 0.5)
    assert abs(nq / nf - 0.25) < 0.03, f"quarter/full = {nq / nf:.4f}"


# ------------------------------------------------------------------ #
# 2. 座標系の取り違え(黙って間違った絵を返す型)
# ------------------------------------------------------------------ #

def test_points_are_xy_not_rowcol():
    """(x,y) で受ける ―― 取り違えた実装は転置した位置に描く。"""
    img = _canvas(0.0)
    out = A.crosshair(img, (150, 20), color=(1.0, 1.0, 1.0), gap=0, extent=5, width=1)
    lit = np.argwhere(out[..., 0] > 0.5)
    assert lit[:, 0].mean() == pytest.approx(20, abs=1)      # row = y
    assert lit[:, 1].mean() == pytest.approx(150, abs=1)     # col = x


def test_mask_shaped_like_the_transpose_is_refused():
    """(row,col) と (x,y) を取り違えたマスクは**通さない**。"""
    with pytest.raises(ValueError, match="transpose"):
        A.overlay_mask(_canvas(), np.zeros((W, H), bool))


def test_text_box_anchor_places_the_plate_where_it_says():
    img = _canvas(0.0)
    out = A.text_box(img, "AB", (150, 100), anchor="rb", pad=4, box_alpha=1.0,
                     box_color=(1.0, 1.0, 1.0), text_color=(0.0, 0.0, 0.0), font_size=12)
    lit = np.argwhere(out[..., 0] > 0.9)
    assert lit[:, 1].max() == 150 - 1 or lit[:, 1].max() == 150   # 右端がアンカー
    assert lit[:, 0].max() <= 100


def test_rect_is_x_y_w_h_with_the_top_left_first():
    img = _canvas(0.0)
    out = A.rounded_rect(img, (30, 10, 100, 40), radius=0, color=(1.0, 1.0, 1.0), fill=True)
    lit = np.argwhere(out[..., 0] > 0.5)
    assert (lit[:, 1].min(), lit[:, 1].max()) == (30, 129)   # x .. x+w-1
    assert (lit[:, 0].min(), lit[:, 0].max()) == (10, 49)    # y .. y+h-1


def test_overlay_labels_gives_the_same_id_the_same_colour():
    lab = np.zeros((H, W), np.int32)
    lab[10:30, 10:30] = 3
    lab[60:80, 100:140] = 3
    out = A.overlay_labels(_canvas(0.0), lab, alpha=1.0)
    assert np.array_equal(out[15, 15], out[70, 120]), "同じラベル番号に別の色が付いた"
    assert np.array_equal(out[0, 0], np.zeros(3))            # 背景(0)は透明


# ------------------------------------------------------------------ #
# 3. 文字 —— 測ってから描く / 黙って切らない
# ------------------------------------------------------------------ #

def test_measure_text_shrinks_to_fit_when_wrapping_is_off():
    """格子のラベルは 2 行にすると版が崩れる ―― 折り返さずに縮める。"""
    wide = A.measure_text("これは長めのラベルです", font_size=20)
    narrow = A.measure_text("これは長めのラベルです", font_size=20, max_width=wide["width"] // 2,
                            min_font_size=6, wrap=False)
    assert narrow["font_size"] < 20
    assert len(narrow["lines"]) == 1
    assert narrow["width"] <= wide["width"] // 2


def test_measure_text_wraps_instead_of_shrinking_by_default():
    wide = A.measure_text("これは長めのラベルです", font_size=20)
    wrapped = A.measure_text("これは長めのラベルです", font_size=20,
                             max_width=wide["width"] // 2, min_font_size=6)
    assert wrapped["font_size"] == 20 and len(wrapped["lines"]) > 1
    assert wrapped["width"] <= wide["width"] // 2


def test_text_that_cannot_fit_raises_instead_of_being_clipped():
    with pytest.raises(ValueError, match="does not fit"):
        A.measure_text("とても長い説明文をとても狭い箱に入れようとしている", font_size=14,
                       max_width=8, min_font_size=9)


def test_text_box_that_overflows_the_image_raises():
    with pytest.raises(ValueError, match="does not fit in the"):
        A.text_box(_canvas(), "はみ出すラベル", (W - 4, 4), font_size=16)


def test_text_invisible_against_its_background_raises():
    """背景と同化した文字は「そこにあるのに読めない」―― 機械では気づけない。"""
    with pytest.raises(ValueError, match="contrast"):
        A.text_box(_canvas(0.05), "見えない", (10, 10), text_color=(0.06, 0.06, 0.08),
                   box_alpha=0.0)


def test_text_box_wraps_when_a_width_is_given():
    img = _canvas(0.0)
    one = A.text_box(img, "abcdefghij", (5, 5), font_size=12, box_alpha=1.0,
                     box_color=(1.0, 1.0, 1.0), text_color=(0.0, 0.0, 0.0))
    two = A.text_box(img, "abcdefghij", (5, 5), font_size=12, box_alpha=1.0,
                     box_color=(1.0, 1.0, 1.0), text_color=(0.0, 0.0, 0.0),
                     max_width=48, min_font_size=12)
    h_one = np.flatnonzero((one[..., 0] > 0.9).any(axis=1)).size
    h_two = np.flatnonzero((two[..., 0] > 0.9).any(axis=1)).size
    assert h_two > h_one, "折り返したのに箱が高くなっていない"


def test_label_points_avoids_collisions_or_says_so():
    img = _canvas(0.0)
    out = A.label_points(img, [(30, 30), (90, 30), (150, 90)], ["1", "2", "3"], font_size=11)
    assert out.shape == img.shape
    with pytest.raises(ValueError, match="no free spot"):
        A.label_points(img, [(40, 40)] * 6, font_size=11)


# ------------------------------------------------------------------ #
# 4. fail-closed(文書化された ValueError)
# ------------------------------------------------------------------ #

def test_unknown_palette_role_is_refused():
    with pytest.raises(ValueError, match="unknown role"):
        A.arrow(_canvas(), (10, 10), (50, 50), color="danger")


def test_non_finite_image_is_refused():
    bad = _canvas()
    bad[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        A.crosshair(bad, (10, 10))


@pytest.mark.parametrize("call,match", [
    (lambda: A.rounded_rect(_canvas(), (10, 10, -5, 20)), "positive"),
    (lambda: A.rounded_rect(_canvas(), (10, 10, 30, 20), radius=-1), "radius"),
    (lambda: A.ellipse(_canvas(), (10, 10), (0, 5)), "radii must be positive"),
    (lambda: A.arc(_canvas(), (10, 10), 5, 30.0, 30.0), "zero-length arc"),
    (lambda: A.zoom_inset(_canvas(), (10, 10, 20, 20), (0, 0), factor=0), "integer >= 1"),
    (lambda: A.zoom_inset(_canvas(), (10, 10, 20, 20), (W - 5, 0), factor=3), "does not fit"),
    (lambda: A.overlay_mask(_canvas(), np.zeros((H, W), bool), alpha=1.5), "within \\[0,1\\]"),
    (lambda: A.overlay_labels(_canvas(), -np.ones((H, W), np.int32)), "must be >= 0"),
    (lambda: A.axes_transform((0, 0, 100, 50), (1.0, 1.0), (0, 1)), "non-zero range"),
    (lambda: A.axes_transform((0, 0, 100, 50), (0.0, 10.0), (0, 1), xscale="log"),
     "strictly positive"),
    (lambda: A.axes_transform((0, 0, 1, 50), (0, 1), (0, 1)), "at least 2x2"),
    (lambda: A.nice_ticks(5.0, 5.0), "zero range"),
    (lambda: A.legend_box(_canvas(), [], (5, 5)), "entries is empty"),
    (lambda: A.legend_box(_canvas(), ["right"], (5, 5)), "must be a \\(color, text\\) pair"),
    (lambda: A.color_bar(_canvas(), palette.diverging_lut(8), (5, 5, 10, 20), 1.0, 1.0),
     "zero range"),
    (lambda: A.scale_bar(_canvas(), -1.0, 1.0), "must be positive"),
    (lambda: A.panel_grid([]), "panels is empty"),
    (lambda: A.filled_polygon(_canvas(), [(1, 1), (2, 2)]), "at least 3 points"),
    (lambda: A.arrow(_canvas(), (10, 10), (10, 10)), "endpoints coincide"),
    (lambda: A.arrow(_canvas(), (-40, -40), (-10, -10)), "entirely outside"),
    (lambda: A.leader_line(_canvas(), (5, 5), (10, 10), cap="star"), "cap must be"),
    (lambda: A.measure_text("x", font_size=0), "font sizes must be >= 1"),
    (lambda: A.text_box(_canvas(), "x", (5, 5), anchor="middle"), "anchor must be"),
])
def test_fail_closed(call, match):
    with pytest.raises(ValueError, match=match):
        call()


def test_plot_series_refuses_an_empty_series():
    ax = A.axes_transform((10, 10, 100, 50), (0, 1), (0, 1))
    with pytest.raises(ValueError, match="empty"):
        A.plot_series(_canvas(), ax, [], [])


def test_plot_series_refuses_mismatched_lengths():
    ax = A.axes_transform((10, 10, 100, 50), (0, 1), (0, 1))
    with pytest.raises(ValueError, match="same length"):
        A.plot_series(_canvas(), ax, [0, 1, 2], [0, 1])


def test_plot_series_refuses_points_that_would_be_clamped_onto_the_frame():
    """範囲外の点を端に貼り付けて描くのは**嘘のグラフ**。既定で例外にする。"""
    ax = A.axes_transform((10, 10, 100, 50), (0.0, 1.0), (0.0, 1.0))
    with pytest.raises(ValueError, match="fall outside"):
        A.plot_series(_canvas(), ax, [0.0, 0.5, 5.0], [0.1, 0.2, 0.3])
    A.plot_series(_canvas(), ax, [0.0, 0.5, 5.0], [0.1, 0.2, 0.3], clip=False)  # 明示なら可


# ------------------------------------------------------------------ #
# 5. imagedraw への素通し / 非破壊 / 決定的
# ------------------------------------------------------------------ #

def test_style_is_passed_through_to_imagedraw_untouched(monkeypatch):
    """線種の引数が imagedraw に増えたとき、この層を直さずに渡せること。"""
    seen = {}
    real = imagedraw.draw_line

    def spy(img, p0, p1, **kw):
        seen.update(kw)
        return real(img, p0, p1, **{k: v for k, v in kw.items() if k in ("color", "width")})

    monkeypatch.setattr(imagedraw, "draw_line", spy)
    A.arrow(_canvas(), (10, 10), (80, 60), width=3, style={"dash": (6, 3), "cap": "round"})
    assert seen["dash"] == (6, 3) and seen["cap"] == "round", seen
    assert seen["width"] == 3


def test_grid_lines_leaves_untouched_pixels_bit_identical():
    """線の無い画素まで α を通すと、格子を重ねるたび絵が 1 ulp ずつ動く。"""
    rng = np.random.default_rng(11)
    img = rng.uniform(0.1, 0.9, (H, W, 3))
    ax = A.axes_transform((20, 10, 120, 60), (0.0, 4.0), (0.0, 1.0))
    once = A.grid_lines(img, ax, alpha=0.35)
    twice = A.grid_lines(once, ax, alpha=0.35)
    outside = np.s_[80:, 160:]                               # 軸の外(格子は来ない)
    assert np.array_equal(once[outside], img[outside])
    assert np.array_equal(twice[outside], img[outside])


def test_short_arrow_does_not_draw_its_shaft_backwards():
    """矢じりが軸より長いと、根元が起点の手前に来て軸が**逆向き**に伸びる。"""
    img = _canvas(0.0)
    out = A.arrow(img, (100, 60), (108, 60), color=(1.0, 1.0, 1.0), width=1,
                  head_len=12.0, head_width=9.0)
    cols = np.flatnonzero((out[..., 0] > 0.5).any(axis=0))
    assert cols.min() >= 99, f"軸が起点 (x=100) より手前 x={cols.min()} まで伸びている"
    assert cols.max() <= 109


def test_style_cannot_smuggle_a_colour_past_the_palette():
    with pytest.raises(ValueError, match="must not carry 'color'"):
        A.arrow(_canvas(), (10, 10), (50, 50), style={"color": (1, 0, 0)})


def test_style_must_be_a_mapping():
    with pytest.raises(ValueError, match="must be a dict"):
        A.crosshair(_canvas(), (10, 10), style=[("width", 2)])


def test_low_level_lines_go_through_imagedraw(monkeypatch):
    """線引きを二重に持たない ―― 実際に imagedraw が呼ばれることを確かめる。"""
    calls = []
    for name in ("draw_line", "draw_polyline", "draw_circle", "draw_markers"):
        real = getattr(imagedraw, name)
        monkeypatch.setattr(imagedraw, name,
                            (lambda n, f: (lambda *a, **k: (calls.append(n), f(*a, **k))[1]))(name, real))
    ax = A.axes_transform((10, 10, 100, 50), (0, 1), (0, 1))
    A.axes_frame(_canvas(), ax)
    A.plot_series(_canvas(), ax, [0.0, 1.0], [0.0, 1.0])
    A.leader_line(_canvas(), (20, 20), (60, 60), cap="dot")
    assert {"draw_polyline", "draw_circle"} <= set(calls), calls


@pytest.mark.parametrize("fn", [
    lambda im: A.text_box(im, "x", (10, 10)),
    lambda im: A.arrow(im, (10, 10), (80, 60)),
    lambda im: A.crosshair(im, (50, 50)),
    lambda im: A.overlay_mask(im, np.ones((H, W), bool), alpha=0.5),
    lambda im: A.rounded_rect(im, (10, 10, 40, 30)),
    lambda im: A.ellipse(im, (50, 50), (20, 10)),
    lambda im: A.filled_polygon(im, [(10, 10), (60, 12), (30, 50)]),
    lambda im: A.zoom_inset(im, (5, 5, 10, 10), (100, 60), 3),
])
def test_ops_do_not_mutate_their_input(fn):
    img = _canvas(0.3)
    before = img.copy()
    fn(img)
    assert np.array_equal(img, before)


@pytest.mark.parametrize("fn", [
    lambda im: A.text_box(im, "決定的", (10, 10)),
    lambda im: A.legend_box(im, [("right", "ok"), ("wrong", "ng")], (10, 10), markers=True),
    lambda im: A.overlay_labels(im, np.tile(np.arange(4, dtype=np.int32), (H, W // 4))),
    lambda im: A.label_points(im, [(30, 30), (100, 70)], ["a", "b"]),
])
def test_output_is_byte_identical_across_calls(fn):
    img = _canvas(0.2)
    assert np.array_equal(fn(img), fn(img))


def test_grayscale_and_rgba_images_are_both_accepted():
    for ch in (None, 1, 3, 4):
        img = _canvas(0.2, channels=ch)
        out = A.overlay_mask(img, np.ones((H, W), bool), "right", 0.5)
        assert out.shape == img.shape
        assert A.crosshair(img, (50, 50)).shape == img.shape


# ------------------------------------------------------------------ #
# 6. 台帳(opsannotate)
# ------------------------------------------------------------------ #

def test_ledger_covers_every_public_op():
    assert set(opsannotate.OPSANNOTATE) == set(A.__all__)
    assert opsannotate.missing() == []


def test_ledger_entries_carry_a_docstring_line():
    for name, meta in opsannotate.OPSANNOTATE.items():
        assert meta["doc"], f"{name} has no docstring first line"
        assert meta["category"] in opsannotate.categories()


def test_ledger_call_returns_the_declared_pairs_type():
    """宣言 out=pairs なら (N,2) が返る(素の返りは 2 本の 1-D)。"""
    ax = A.axes_transform((0, 0, 101, 51), (0, 10), (0, 1))
    raw = opsannotate.get("data_to_pixel")(ax, [0.0, 10.0], [0.0, 1.0])
    assert isinstance(raw, tuple) and len(raw) == 2
    pairs = opsannotate.call("data_to_pixel", ax, [0.0, 10.0], [0.0, 1.0])
    assert pairs.shape == (2, 2)
    assert np.allclose(pairs[:, 0], [0.0, 100.0])


def test_public_facade_exposes_every_op_except_the_one_that_would_shadow():
    """``fs.<op>`` で引ける。ただし ``overlay_mask`` だけは**わざと出さない**。"""
    import fullseye as fs
    missing = [n for n in A.__all__ if n != "overlay_mask" and not hasattr(fs, n)]
    assert not missing, f"not reachable from the facade: {missing}"
    assert fs.overlay_mask.__module__ == "imgio", (
        "fs.overlay_mask must stay the existing imgio one — shadowing it with the "
        "annotate version (different colour convention, different mask rule) would "
        "silently change every existing caller's picture")
    assert fs.annotate.overlay_mask.__module__ == "annotate"


def test_example_gallery_runs():
    import importlib.util
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "examples", "annotate_gallery.py")
    spec = importlib.util.spec_from_file_location("annotate_gallery", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    report = mod.run()
    assert report["scale_bar_px_error"] == 0
    assert report["tick_px_error"] == 0
    assert report["alpha_max_abs_error"] == 0.0
    assert report["legend_height_error"] == 0


def test_data_to_pixel_refuses_mismatched_lengths():
    """長さの違う 2 本を返すと、zip した呼び手が**黙って嘘の図**を描く。

    2026-09-02、連鎖ファザーがこの op を実行できるようになった直後に発覚。
    それまでは x=7 点・y=3 点でも例外を出さず ``(7,)`` と ``(3,)`` を返していた。
    zip すると **3 点だけが x の先頭 3 つの位置に**描かれ、点が消えたことも
    x がずれたことも図からは分からない。

    兄弟の :func:`annotate.plot_series` は同じ状況を拒否していた ―― **同じ族の
    中で規律が割れていた**ので、文言も揃えてある(片方だけ直すと再発する型)。
    """
    import numpy as np
    import pytest

    import annotate

    ax = annotate.axes_transform((4, 4, 60, 40), (0.0, 10.0), (0.0, 5.0))
    with pytest.raises(ValueError, match="x and y must have the same length"):
        annotate.data_to_pixel(ax, np.linspace(0, 10, 7), np.linspace(0, 5, 3))
    with pytest.raises(ValueError, match="x and y must have the same length"):
        annotate.plot_series(np.zeros((60, 80)), ax,
                             np.linspace(0, 10, 7), np.linspace(0, 5, 3))

    # 揃っていれば通る(締めすぎていないこと)
    px, py = annotate.data_to_pixel(ax, np.linspace(0, 10, 7), np.linspace(0, 5, 7))
    assert px.shape == py.shape == (7,)


# ------------------------------------------------------------------ #
# 5. 板なしラベルの可読性 / 改行の契約(2026-09-02 の回帰)
# ------------------------------------------------------------------ #

def _ink_contrast(before, after, region, bg):
    """``region``(y0,y1,x0,x1)内で描画により変わった画素(= 文字)の平均色と
    地 ``bg`` との WCAG コントラスト比。変わった画素が無ければ ``(0, 1.0)``。

    平均には縁のアンチエイリアス画素も混ざるので、字の芯より低めに出る
    (= 検査は保守的)。
    """
    y0, y1, x0, x1 = region
    b = before[y0:y1, x0:x1]
    a = after[y0:y1, x0:x1]
    changed = np.abs(a - b).reshape(a.shape[0], a.shape[1], -1).max(axis=2) > 1e-9
    n = int(changed.sum())
    if n == 0:
        return 0, 1.0
    m = float(a[changed].mean())
    return n, A._contrast_ratio((m,) * 3, (bg,) * 3)


@pytest.mark.parametrize("bg", [1.0, 0.0])
def test_color_bar_labels_are_legible_on_white_and_on_black(bg):
    """板なし(``box_alpha=0``)のラベルは**白地でも黒地でも**読めること。

    2026-09-02 まで内部の text_box 呼び出しが ``min_contrast=1.0`` で検査を切り、
    既定の明るい文字を白地に置いていた ―― 白い紙の上のカラーバーの数値が
    コントラスト比 1.07 で「そこにあるのに見えない」。例外も出ないので機械には
    気づけなかった。文字色が既定のときは下地に合わせて暗い字へ切り替える。
    """
    img = _canvas(bg)
    out = A.color_bar(img, palette.diverging_lut(64), (20, 20, 16, 80),
                      vmin=0.0, vmax=1.0, border=0)
    n, ratio = _ink_contrast(img, out, (0, H, 40, W), bg)          # バーの右 = ラベル
    assert n > 0, "ラベルが描かれていない"
    assert ratio >= A.DEFAULT_MIN_CONTRAST, f"bg={bg}: label contrast {ratio:.2f}"


@pytest.mark.parametrize("bg", [1.0, 0.0])
def test_tick_labels_are_legible_on_white_and_on_black(bg):
    """目盛りの数値も同じ(x ラベル = 枠の下、y ラベル = 枠の左)。"""
    img = _canvas(bg)
    ax = A.axes_transform((50, 20, 120, 60), (0.0, 1.0), (0.0, 1.0))
    out = A.ticks(img, ax, xticks=[0.0, 0.5, 1.0], yticks=[0.0, 1.0],
                  color=(0.5, 0.5, 0.5), tick_len=5)
    # 目盛り線は y<=84 / x>=45 に収まるので、下の 2 領域には文字しか無い
    for region in ((88, H, 40, W), (0, H, 0, 44)):
        n, ratio = _ink_contrast(img, out, region, bg)
        assert n > 0, f"region {region}: ラベルが描かれていない"
        assert ratio >= A.DEFAULT_MIN_CONTRAST, f"bg={bg} region={region}: {ratio:.2f}"


def test_legend_and_panel_labels_are_legible_on_white():
    """同じ型の兄弟: 板なし凡例と、白地の panel_grid のラベル・題。"""
    img = _canvas(1.0)
    out = A.legend_box(img, [("right", "ok"), ("wrong", "ng")], (4, 4),
                       box_alpha=0.0, border=0, markers=False)
    n, ratio = _ink_contrast(img, out, (0, 60, 34, W), 1.0)         # x>=34 は文字だけ
    assert n > 0 and ratio >= A.DEFAULT_MIN_CONTRAST, f"legend: {ratio:.2f}"

    panels = [np.full((30, 40, 3), 0.5) for _ in range(2)]
    grid = A.panel_grid(panels, ["a", "b"], ncols=2, pad=6, label_h=32,
                        background=1.0, border=0, title="T")
    ink = grid[(np.abs(grid - 1.0).max(axis=2) > 1e-9) & (np.abs(grid - 0.5).max(axis=2) > 1e-9)]
    assert ink.size > 0, "ラベルが描かれていない"
    ratio = A._contrast_ratio((float(ink.mean()),) * 3, (1.0,) * 3)
    assert ratio >= A.DEFAULT_MIN_CONTRAST, f"panel_grid: {ratio:.2f}"


def test_explicit_text_colour_is_not_silently_replaced():
    """自動切り替えは**既定色のときだけ**。明示した色が読めなければ例外のまま。"""
    with pytest.raises(ValueError, match="contrast"):
        A.text_box(_canvas(1.0), "白い字", (10, 10), text_color=(0.97, 0.97, 0.97),
                   box_alpha=0.0)


def test_measure_text_newlines_work_without_a_width():
    """``\\n`` は ``max_width`` の有無・``wrap`` によらず効く。

    2026-09-02 まで ``max_width=None``(と ``wrap=False``)では改行を分けずに
    1 行として PIL に渡していた。PIL は複数行の幅を測れないので
    ``measure_text("a\\nb")`` は文書の契約と違って **ValueError** になっていた。
    """
    one = A.measure_text("ab", max_width=None)
    two = A.measure_text("ab\ncd", max_width=None)
    assert two["lines"] == ["ab", "cd"]
    assert two["line_height"] == one["line_height"]
    assert two["height"] == 2 * one["height"]
    assert two["width"] == max(one["width"], A.measure_text("cd")["width"])
    nowrap = A.measure_text("ab\ncd", max_width=500, wrap=False)
    assert nowrap["lines"] == ["ab", "cd"] and nowrap["height"] == two["height"]
    wrapped = A.measure_text("ab\ncd", max_width=500)
    assert wrapped["lines"] == ["ab", "cd"] and wrapped["height"] == two["height"]

    # text_box も同じ契約: 板は改行 1 つぶん(= line_height)だけ高くなる
    img = _canvas(0.0)
    kw = dict(box_alpha=1.0, box_color=(1.0, 1.0, 1.0), text_color=(0.0, 0.0, 0.0))
    single = A.text_box(img, "ab", (5, 5), **kw)
    double = A.text_box(img, "ab\ncd", (5, 5), **kw)
    h1 = np.flatnonzero((single[..., 0] > 0.9).any(axis=1)).size
    h2 = np.flatnonzero((double[..., 0] > 0.9).any(axis=1)).size
    assert h2 - h1 == one["line_height"]


# ------------------------------------------------------------------ #
# 7. 学術図の作法(paper 族、2026-09-03)—— 配置は layout の閉形式で検算する
# ------------------------------------------------------------------ #

def test_ledger_paper_category_counts():
    """台帳: 7 カテゴリ / 46 op、paper 族は 21 op(描く 13 + layout 8)。"""
    assert len(opsannotate.categories()) == 7
    assert len(opsannotate.OPSANNOTATE) == 46
    paper = opsannotate.list_ops("paper")
    assert len(paper) == 21
    layouts = [n for n in paper if n.endswith("_layout")]
    assert len(layouts) == 8
    for n in layouts:
        assert opsannotate.info(n)["out"] == "table", n
    for n in paper:
        if not n.endswith("_layout"):
            assert opsannotate.info(n)["out"] == "image2d", n
    # docstring の 1 行目が返り型を名乗る
    for n in paper:
        doc = opsannotate.info(n)["doc"]
        assert doc.startswith("table(dict)") or doc.startswith("画像(image2d)"), (n, doc)


def test_leader_layout_is_closed_form_and_collision_free():
    """肘 = point + side*gap、文字 = 肘 + side_x*0.6*gap。板同士は重ならない。"""
    pts = [(60, 80), (66, 84), (72, 88), (150, 40)]
    lay = A.annotate_leader_layout((H, W), pts, ["alpha", "beta", "gamma", "delta"], gap=20)
    assert lay["n"] == 4
    boxes = [it["box"] for it in lay["items"]]
    for i in range(4):
        for j in range(i + 1, 4):
            assert not A._overlaps(boxes[i], boxes[j]), (i, j)
    for it, (x, y) in zip(lay["items"], pts):
        sx, sy = it["side"]
        g = lay["gap"] * (1.0 if it["elbow"] == (x + sx * lay["gap"], y + sy * lay["gap"]) else
                          abs(it["elbow"][1] - y) / lay["gap"])
        assert it["elbow"] == pytest.approx((x + sx * g, y + sy * g))
        if sx != 0:
            assert it["text_xy"] == pytest.approx((it["elbow"][0] + sx * 0.6 * g, it["elbow"][1]))
            assert it["anchor"] == ("lm" if sx > 0 else "rm")
        bx, by, bw, bh = it["box"]
        assert 0 <= bx and 0 <= by and bx + bw <= W and by + bh <= H
        # 板は他の点を覆わない
        for (px, py) in pts:
            if (px, py) != (x, y):
                assert not (bx <= px <= bx + bw - 1 and by <= py <= by + bh - 1)


def test_leader_auto_side_points_away_from_the_image_centre():
    left = A.annotate_leader_layout((H, W), [(20, 60)], ["L"])["items"][0]["side"][0]
    right = A.annotate_leader_layout((H, W), [(180, 60)], ["R"])["items"][0]["side"][0]
    assert left == -1 and right == 1


def test_leader_refuses_when_no_free_spot():
    pts = [(100, 60)] * 30
    with pytest.raises(ValueError, match="cannot be placed"):
        A.annotate_leader_layout((H, W), pts, [f"label {i}" for i in range(30)])


def test_leader_draw_uses_the_layout_and_is_deterministic():
    img = _canvas(0.2)
    lay = A.annotate_leader_layout((H, W), [(60, 80)], ["a"])
    out1 = A.annotate_leader(img, [(60, 80)], ["a"])
    out2 = A.annotate_leader(img, [(60, 80)], ["a"], layout=lay)
    assert np.array_equal(out1, out2)
    assert not np.array_equal(out1, img)
    # 肘の位置の画素に線が乗っている(AA なので > 背景)
    ex, ey = lay["items"][0]["elbow"]
    assert out1[int(round(ey)), int(round(ex)), 0] != pytest.approx(0.2)


def test_aa_line_coverage_is_partial_at_the_edge_and_full_on_the_axis():
    """距離ベースの AA: 線の中心画素は被覆 1、半画素外は中間、遠くは 0。"""
    cov = A._segment_coverage((20, 40), (5.0, 10.0), (35.0, 10.0), width=1.0)
    assert cov[10, 20] == pytest.approx(1.0)
    assert 0.0 < cov[11, 20] < 1.0
    assert cov[13, 20] == 0.0
    assert cov[10, 2] == 0.0                                  # 端点の外


def test_dash_pieces_cover_exactly_the_on_fraction():
    pieces = A._dash_pieces([(0.0, 0.0), (100.0, 0.0)], False, (6.0, 4.0))
    on = sum(q[0] - p[0] for p, q in pieces)
    assert on == pytest.approx(60.0)                            # 10 周期 x 6
    assert all(q[0] > p[0] for p, q in pieces)


def test_dimension_layout_closed_form():
    lay = A.annotate_dimension_layout((40, 100), (140, 100), offset=20, extension=6)
    (q0, q1) = lay["line"]
    assert q0 == pytest.approx((40, 120)) and q1 == pytest.approx((140, 120))
    assert lay["length_px"] == pytest.approx(100.0)
    assert lay["normal"] == pytest.approx((0.0, 1.0))
    assert lay["ext0"][1] == pytest.approx((40, 126))
    assert lay["text_xy"] == pytest.approx((90, 128))
    neg = A.annotate_dimension_layout((40, 100), (140, 100), offset=-20)
    assert neg["line"][0] == pytest.approx((40, 80)) and neg["normal"] == pytest.approx((0.0, -1.0))
    with pytest.raises(ValueError, match="coincide"):
        A.annotate_dimension_layout((1, 1), (1, 1))
    with pytest.raises(ValueError, match="non-zero"):
        A.annotate_dimension_layout((1, 1), (5, 1), offset=0)


def test_dimension_value_is_length_times_resolution():
    """値 = |p1-p0| * units_per_pixel。文字が書かれた位置は layout の text_xy。"""
    img = _canvas(0.2)
    lay = A.annotate_dimension_layout((40, 60), (140, 60), offset=-20)
    out = A.annotate_dimension(img, (40, 60), (140, 60), 0.25, "mm", offset=-20, layout=lay)
    # 寸法線の位置に色が乗り、そこから遠い行は無傷
    assert not np.allclose(out[40, 60:120], 0.2)
    assert np.allclose(out[110, :], 0.2)
    assert lay["length_px"] * 0.25 == pytest.approx(25.0)
    with pytest.raises(ValueError, match="units_per_pixel"):
        A.annotate_dimension(img, (40, 60), (140, 60), "0.25")


def test_angle_layout_takes_the_smaller_angle_and_its_bisector():
    lay = A.annotate_angle_layout((100, 50), (50, 50), (50, 0), radius=30)
    assert lay["angle_deg"] == pytest.approx(90.0)
    # 画面座標: a は右(0°)、b は上(270°)。小さい方は 270→360(=0)
    assert lay["start_deg"] == pytest.approx(270.0)
    assert lay["bisector_deg"] == pytest.approx(315.0)
    r = 30 + 12
    assert lay["text_xy"] == pytest.approx((50 + r * np.cos(np.radians(315)),
                                            50 + r * np.sin(np.radians(315))))
    straight = A.annotate_angle_layout((0, 50), (50, 50), (100, 50))
    assert straight["angle_deg"] == pytest.approx(180.0)
    with pytest.raises(ValueError, match="differ from vertex"):
        A.annotate_angle_layout((50, 50), (50, 50), (1, 1))


def test_angle_draws_arc_on_the_circle_only():
    img = _canvas(0.0)
    out = A.annotate_angle(img, (150, 60), (100, 60), (100, 20), radius=30, draw_rays=False,
                           color=(1.0, 1.0, 1.0), font_size=10)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot(xx - 100, yy - 60)
    lit = out[..., 0] > 0.5
    # 弧の画素は半径 30 の近く(文字の板は別の場所)
    on_arc = lit & (d < 40) & (yy <= 61) & (xx >= 99)
    assert on_arc.sum() > 20
    assert np.all(np.abs(d[on_arc] - 30) <= 1.5)


def test_scale_bar_layout_picks_a_nice_number_under_the_target():
    lay = A.annotate_scale_bar_layout((H, W), 0.5, "µm", corner="rb", target_fraction=0.2,
                                      margin=14)
    target = 0.2 * (W - 28) * 0.5                       # 17.2 µm → 10 µm
    assert lay["length"] == 10.0
    assert lay["px"] == int(round(10.0 / 0.5))
    assert lay["length"] <= target
    x0, y0, w, h = lay["rect"]
    assert w == lay["px"] and x0 + w == W - 14 and y0 + h == H - 14
    for v, want in ((17.2, 10.0), (23.0, 20.0), (0.7, 0.5), (500.0, 500.0), (4.99, 2.0)):
        assert A._nice_floor(v) == want, v
    with pytest.raises(ValueError, match="corner"):
        A.annotate_scale_bar_layout((H, W), 0.5, corner="centre")


def test_scale_bar_draws_exactly_the_layout_pixels():
    img = _canvas(0.0)
    lay = A.annotate_scale_bar_layout((H, W), 0.5, "um", corner="lb")
    out = A.annotate_scale_bar(img, 0.5, "um", corner="lb", color=(1.0, 1.0, 1.0),
                               box_alpha=0.0)
    x0, y0, w, h = lay["rect"]
    assert np.all(out[y0:y0 + h, x0:x0 + w, 0] == 1.0)
    assert np.all(out[y0:y0 + h, x0 + w:x0 + w + 5, 0] == 0.0)


def test_orientation_arrow_points_the_stated_way():
    img = _canvas(0.0)
    out = A.annotate_orientation(img, 0.0, xy=(100, 60), size=40, label=None,
                                 color=(1.0, 1.0, 1.0))
    lit = out[..., 0] > 0.5
    rows = np.flatnonzero(lit.any(axis=1))
    # 上向き: 矢じりは上端(row 小)側にあり、幅広い行は上にある
    widths = lit.sum(axis=1)
    assert rows.min() < 60 < rows.max()
    assert widths[rows.min() + 6] > widths[rows.max() - 3]
    with pytest.raises(ValueError, match="outside"):
        A.annotate_orientation(img, 0.0, xy=(5, 5), size=40)


def test_inset_layout_chooses_largest_integer_factor_that_fits():
    lay = A.annotate_inset_layout((H, W), (20, 20, 30, 20), corner="rt", margin=10,
                                  max_fraction=0.4)
    assert lay["factor"] == min(int(0.4 * W) // 30, int(0.4 * H) // 20)
    dx, dy, dw, dh = lay["dst_rect"]
    assert (dw, dh) == (30 * lay["factor"], 20 * lay["factor"])
    assert dx + dw == W - 10 and dy == 10
    with pytest.raises(ValueError, match="cover its own source"):
        A.annotate_inset_layout((H, W), (20, 20, 30, 20), corner="lt", margin=10)
    with pytest.raises(ValueError, match="integer"):
        A.annotate_inset_layout((H, W), (20, 20, 30, 20), factor=1.5)


def test_inset_copies_source_pixels_nearest_neighbour():
    img = _canvas(0.0)
    img[25, 30] = (0.9, 0.1, 0.4)
    lay = A.annotate_inset_layout((H, W), (20, 20, 20, 10), corner="rb")
    out = A.annotate_inset(img, (20, 20, 20, 10), corner="rb", width=1, connect=False)
    f = lay["factor"]
    dx, dy, _, _ = lay["dst_rect"]
    block = out[dy + 5 * f:dy + 6 * f, dx + 10 * f:dx + 11 * f]
    assert np.allclose(block, (0.9, 0.1, 0.4))


def test_outline_layout_area_equals_mask_pixels_and_centroid_is_exact():
    m = np.zeros((H, W), bool)
    m[30:70, 50:110] = True
    m[40:50, 60:70] = False                                   # 穴
    lay = A.annotate_outline_layout(m)
    assert lay["n_loops"] == 2
    assert lay["area"] == int(m.sum())
    rr, cc = np.nonzero(m)
    assert lay["centroid"] == pytest.approx((cc.mean(), rr.mean()))
    assert lay["bbox"] == (50, 30, 60, 40)
    outer = lay["contours"][0]
    # 外周多角形(靴紐公式)の面積 = 外側の画素数(穴を含む)
    x, y = outer[:, 0], outer[:, 1]
    area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))
    assert area == pytest.approx(40 * 60)
    with pytest.raises(ValueError, match="no true pixel"):
        A.annotate_outline_layout(np.zeros((H, W), bool))


def test_outline_draws_on_the_boundary_and_not_inside():
    img = _canvas(0.0)
    m = np.zeros((H, W), bool)
    m[30:70, 50:110] = True
    out = A.annotate_outline(img, m, color=(1.0, 1.0, 1.0), width=1.0)
    assert out[30, 80, 0] > 0.3 and out[69, 80, 0] > 0.3
    assert out[50, 80, 0] == 0.0                              # 内部は無傷
    with pytest.raises(ValueError, match="does not match"):
        A.annotate_outline(img, m[:, :100])


def test_text_path_layout_positions_follow_arc_length():
    path = [(10.0, 50.0), (110.0, 50.0), (110.0, 100.0)]
    lay = A.annotate_text_path_layout("abc", path, font_size=12)
    assert lay["length"] == pytest.approx(150.0)
    s = 0.0
    for it in lay["chars"]:
        assert it["s"] == pytest.approx(s + it["width"] / 2.0)
        assert it["angle_deg"] == pytest.approx(0.0)          # 最初の水平区間
        assert it["xy"][1] == pytest.approx(50.0) and it["xy"][0] == pytest.approx(10.0 + it["s"])
        s += it["width"]
    far = A.annotate_text_path_layout("x", path, font_size=12, start=120.0)["chars"][0]
    assert far["angle_deg"] == pytest.approx(90.0)            # 縦の区間は下向き
    assert far["xy"][0] == pytest.approx(110.0)
    with pytest.raises(ValueError, match="path is"):
        A.annotate_text_path_layout("x" * 80, path, font_size=12)


def test_text_path_draws_only_near_the_path():
    img = _canvas(0.0)
    path = [(20.0, 60.0), (180.0, 60.0)]
    out = A.annotate_text_path(img, "hello", path, font_size=14, color=(1.0, 1.0, 1.0))
    lit = out[..., 0] > 0.2
    rows = np.flatnonzero(lit.any(axis=1))
    assert 40 < rows.min() and rows.max() < 80
    assert lit.sum() > 20


def test_colorbar_overlay_matches_alpha_formula():
    img = _canvas(0.2)
    field = np.linspace(0.0, 1.0, W)[None, :].repeat(H, axis=0)
    lut = palette.diverging_lut(256)
    out = A.annotate_colorbar(img, field, (180, 10, 8, 80), lut=lut, vmin=0.0, vmax=1.0,
                              alpha=0.5, font_size=10)
    # 場が 0 の列は lut[0]、1 の列は lut[-1] を α=0.5 で重ねたもの(バーの外の行で)
    assert np.allclose(out[100, 0], 0.5 * lut[0] + 0.5 * 0.2)
    assert np.allclose(out[100, W - 1], 0.5 * lut[-1] + 0.5 * 0.2)
    with pytest.raises(ValueError, match="non-finite"):
        A.annotate_colorbar(img, np.full((H, W), np.nan), (180, 10, 8, 80))
    with pytest.raises(ValueError, match="zero range"):
        A.annotate_colorbar(img, np.zeros((H, W)), (180, 10, 8, 80))


def test_panel_label_text_and_corners():
    img = _canvas(0.2)
    for corner in ("lt", "rt", "lb", "rb"):
        out = A.annotate_panel_label(img, "b", corner=corner)
        assert not np.array_equal(out, img)
    assert A._panel_letter(0, "paren") == "(a)"
    assert A._panel_letter(2, "upper") == "C"
    with pytest.raises(ValueError, match="letter"):
        A.annotate_panel_label(img, "ab")
    with pytest.raises(ValueError, match="style"):
        A.annotate_panel_label(img, "a", style="bold")


def test_figure_grid_layout_matches_panel_grid_formula_and_output_size():
    shapes = [(60, 80), (50, 70), (60, 80)]
    lay = A.annotate_figure_grid_layout(shapes, ncols=2, pad=10, caption_h=32)
    cw, ch = 80, 60
    assert lay["size"] == (2 * 10 + 2 * (ch + 32) + 10, 2 * 10 + 2 * cw + 10)
    assert lay["cells"][1] == (10 + cw + 10, 10, cw, ch)
    assert lay["panels"][1] == (10 + cw + 10 + (cw - 70) // 2, 10 + (ch - 50) // 2, 70, 50)
    assert lay["captions"][2] == (10, 10 + ch + 32 + 10 + ch, cw, 32)
    assert lay["letters"] == ["(a)", "(b)", "(c)"]
    panels = [np.full(s + (3,), v) for s, v in zip(shapes, (0.3, 0.6, 0.9))]
    fig = A.annotate_figure_grid(panels, ["one", "two", "three"], ncols=2, pad=10,
                                 caption_h=32, font_size=12)
    assert fig.shape[:2] == lay["size"]
    # パネルの画素はそのまま(拡大しない)
    for (x, y, w, h), v in zip(lay["panels"], (0.3, 0.6, 0.9)):
        assert np.allclose(fig[y + 2:y + h - 2, x + 2:x + w - 2], v)
    with pytest.raises(ValueError, match="letters"):
        A.annotate_figure_grid(panels, letters="yes")


def test_numbered_markers_and_legend_share_numbering():
    img = _canvas(0.2)
    out = A.annotate_markers(img, [(30, 30), (100, 60)], start=3, radius=9)
    assert not np.array_equal(out, img)
    assert np.allclose(out[30, 60], 0.2)                      # 円の外は無傷
    leg = A.annotate_legend(out, ["first", "second"], (190, 10), anchor="rt", start=3)
    assert not np.array_equal(leg, out)
    with pytest.raises(ValueError, match="does not fit"):
        A.annotate_markers(img, [(30, 30)], labels=["a long label"], radius=6)
    with pytest.raises(ValueError, match="radius"):
        A.annotate_markers(img, [(30, 30)], radius=True)
    with pytest.raises(ValueError, match="empty"):
        A.annotate_legend(img, [], (10, 10))


def test_paper_ops_accept_grayscale_and_rgba():
    m = np.zeros((H, W), bool)
    m[30:70, 50:110] = True
    for ch in (None, 1, 3, 4):
        img = _canvas(0.2, channels=ch)
        assert A.annotate_leader(img, [(60, 80)], ["a"]).shape == img.shape
        assert A.annotate_outline(img, m).shape == img.shape
        assert A.annotate_dimension(img, (40, 60), (140, 60), offset=-20).shape == img.shape
        assert A.annotate_scale_bar(img, 0.5).shape == img.shape


def test_paper_ops_are_deterministic():
    img = _canvas(0.2)
    m = np.zeros((H, W), bool)
    m[30:70, 50:110] = True
    for fn in (lambda i: A.annotate_leader(i, [(60, 80), (150, 40)], ["a", "b"]),
               lambda i: A.annotate_outline(i, m, label="ROI"),
               lambda i: A.annotate_angle(i, (150, 60), (100, 60), (100, 20)),
               lambda i: A.annotate_text_path(i, "abc", [(20, 60), (180, 60)])):
        assert np.array_equal(fn(img), fn(img))

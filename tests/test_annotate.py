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
    (-3.0, 3.0, [-3, -2, -1, 0, 1, 2, 3]),
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
        img = _canvas(0.0)
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
                     box_color=(1.0, 1.0, 1.0), font_size=12)
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

def test_measure_text_shrinks_to_fit():
    wide = A.measure_text("これは長めのラベルです", font_size=20)
    narrow = A.measure_text("これは長めのラベルです", font_size=20, max_width=wide["width"] // 2,
                            min_font_size=6)
    assert narrow["font_size"] < 20
    assert narrow["width"] <= wide["width"] // 2


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
                     box_color=(1.0, 1.0, 1.0))
    two = A.text_box(img, "abcdefghij", (5, 5), font_size=12, box_alpha=1.0,
                     box_color=(1.0, 1.0, 1.0), max_width=48, min_font_size=12)
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
    (lambda: A.arrow(_canvas(), (10, 10), (10, 10), head_len=0, head_width=0), "outside"),
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

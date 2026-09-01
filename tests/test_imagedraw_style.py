# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drawstyle × imagedraw: 描画状態・線種・背景のGTテスト。

要点は 3 つ:

1. **既存呼び出しがビット不変** ―― 展示 141 点はこの op で描かれており、再生成で
   SHA-256 が変われば全部作り直しになる。``style`` を渡さない呼び出しの出力を
   変更前の実装で採った SHA-256 と突き合わせる(下の ``LEGACY_SHA256``)。
2. **破線は閉形式と一致** ―― 目視でなく画素数で測る。長さ L の水平線に
   ``[on, off]`` を引いたときの点灯画素数は、s = 0..L の整数位置のうち
   ``s mod (on+off) < on`` の個数、すなわち ``q*on + min(r, on)``
   (``q, r = divmod(L+1, on+off)``)に **厳密に** 一致する。
3. **fail-closed** ―― 不正な線種・役割名・線幅は黙って実線/既定に落ちず ValueError。
"""
import hashlib
import threading

import numpy as np
import pytest
from scipy import ndimage

import contours_xld as X
import drawstyle as S
import imagedraw as D
import palette
from drawstyle import DrawStyle


# --------------------------------------------------------------------------
# 1. 既存呼び出しのビット不変性
# --------------------------------------------------------------------------
def _base_gray():
    rng = np.random.default_rng(7)
    return rng.random((70, 90)) * 0.4


def _base_rgb():
    rng = np.random.default_rng(11)
    return rng.random((60, 80, 3)) * 0.3


def _xld():
    return X.gen_circle_contour_xld(40, 40, 15, n=60, shape=(80, 80))


#: 変更前の imagedraw.py(描画状態を入れる前)で採った出力の SHA-256。
#: ``style`` を渡さない呼び出しは 1 ビットも変わってはならない。
LEGACY_SHA256 = {
    "line_default": "f2310d0adbe482f9008152508365a3f7f2fdf01e61ce4bb2e2cfcbd17f7bfcb6",
    "line_pos": "4172e6cc548780bdaab9525493835de5c8412676d44ae8ec0cc8541d6ae6ce6e",
    "line_kw": "aa06f3571f241489d3df3ef02f27e07341194c135ee81b6988db7a71467d5ff3",
    "line_rgb": "8493bb8a765a19f0f7b2bc203a5a3cc17c21496a697c00173348406a6951c3d7",
    "poly_open": "001dd54175bea9a6ebf7ff5294f1b9ea87481d5224f118816d94b447362aa3ad",
    "poly_closed": "cd68351ef37c10eae9a1ede10c09ad0b5396100fd1c18329ddd002da56061940",
    "poly_rgb": "ea3e176164875ced0ffb87f43272ad10194382b7debf34c7894fe3a5f4a412ad",
    "circle_outline": "2b6553c491522334a43e9875d5f1206f33ab65d939469bc58fbae6ab7060f37e",
    "circle_outline_w4": "26f0e989904a0932a055b39408bd9805eb25f98ee3c90765e14374dedcebd6b2",
    "circle_outline_wf": "00200cd73eea15cb26075253bf3e38a4936ebd80001260161210a2d9aecc177c",
    "circle_fill": "bd20f087dab84e0c0c866e03347288e82699e385613202cd12c5ed7b1b3a6c1c",
    "circle_fill_rgb": "6e351762e0a35234bd8dd2dcd382ff0e8d5a0b7bc7f5864dfcc3867814cbbebd",
    "markers_cross": "2a190ebe31b87c2df5df91021b283395ded468e35f52e987778579a6629a04f2",
    "markers_square": "7f71cb9cb78a79d4959d3d1625e6c6fccff73773ce56824e6785c5011e772445",
    "markers_dot": "41dc148688f2b1792c8e91ac0d741240655f75cd8cf84ee8dc9e34b89b36f1ff",
    "markers_rgb": "d3037a9d0f06b0a52dd4ef85080d9e559438792b2cc55921b809ec52634957cc",
    "contour_xld": "bb9a667385eff12aa72f6d0e286b3b0fb2fb48ba15133d29a5fa40f10bbfcfc6",
    "contour_arr": "2a1dc426d7518714a4c0141236373f4345a3875971a1e2052760fdd23471ef85",
}

LEGACY_CALLS = {
    "line_default": lambda: D.draw_line(_base_gray(), (3, 5), (80, 60)),
    "line_pos": lambda: D.draw_line(_base_gray(), (3, 5), (80, 60), 0.75, 3),
    "line_kw": lambda: D.draw_line(_base_gray(), (0, 0), (89, 69), color=1.0, width=1),
    "line_rgb": lambda: D.draw_line(_base_rgb(), (2, 2), (77, 55), (1.0, 0.2, 0.0), 2),
    "poly_open": lambda: D.draw_polyline(_base_gray(), [(5, 5), (60, 12), (30, 55)], 0.9, 2),
    "poly_closed": lambda: D.draw_polyline(_base_gray(), [(5, 5), (60, 12), (30, 55)],
                                           0.9, 2, closed=True),
    "poly_rgb": lambda: D.draw_polyline(_base_rgb(), [(4, 4), (70, 8), (40, 50)],
                                        (0.1, 0.9, 0.4), 1, closed=True),
    "circle_outline": lambda: D.draw_circle(_base_gray(), (45, 35), 20.0, 0.8, 1),
    "circle_outline_w4": lambda: D.draw_circle(_base_gray(), (45, 35), 20.0, 0.8, 4),
    "circle_outline_wf": lambda: D.draw_circle(_base_gray(), (45, 35), 20.0, 0.8, 1.5),
    "circle_fill": lambda: D.draw_circle(_base_gray(), (45, 35), 12.0, 0.6, fill=True),
    "circle_fill_rgb": lambda: D.draw_circle(_base_rgb(), (40, 30), 14.0, (0.2, 0.4, 1.0),
                                             fill=True),
    "markers_cross": lambda: D.draw_markers(_base_gray(), [(20, 20), (60, 45)], 1.0, 5,
                                            "cross", 1),
    "markers_square": lambda: D.draw_markers(_base_gray(), [(20, 20), (60, 45)], 0.5, 6,
                                             "square", 3),
    "markers_dot": lambda: D.draw_markers(_base_gray(), [(20, 20), (60, 45)], 0.7, 4, "dot", 1),
    "markers_rgb": lambda: D.draw_markers(_base_rgb(), [(30, 30)], (1, 0, 0), 5, "square", 2),
    "contour_xld": lambda: D.draw_contour(np.zeros((80, 80)), _xld(), 1.0, 1),
    "contour_arr": lambda: D.draw_contour(_base_gray(),
                                          np.array([[5.0, 5.0], [50.0, 8.0], [30.0, 40.0]]),
                                          0.9, 2),
}


def _sha(a):
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest()


@pytest.mark.parametrize("name", sorted(LEGACY_CALLS))
def test_legacy_calls_are_bit_identical(name):
    """style を渡さない呼び出しは変更前と 1 ビットも変わらない(展示の再生成が壊れない)。"""
    assert _sha(LEGACY_CALLS[name]()) == LEGACY_SHA256[name]


def test_repeated_calls_are_deterministic():
    for fn in LEGACY_CALLS.values():
        assert _sha(fn()) == _sha(fn())


# --------------------------------------------------------------------------
# 2. 線種 ―― 閉形式との一致
# --------------------------------------------------------------------------
def _lit_on_row(pattern, L, row=10):
    st = DrawStyle(line_style=list(pattern))
    img = D.draw_line(np.zeros((20, L + 20)), (0, row), (L, row), style=st)
    return int((img[row] > 0.5).sum())


def _closed_form(on, off, L):
    """s = 0..L の整数位置のうち ``s mod (on+off) < on`` の個数。"""
    q, r = divmod(L + 1, on + off)
    return q * on + min(r, on)


@pytest.mark.parametrize("on,off,L", [(10, 5, 100), (10, 5, 199), (3, 2, 60), (7, 7, 140),
                                      (1, 4, 120), (20, 3, 77)])
def test_dashed_lit_pixels_match_closed_form(on, off, L):
    """点灯画素数は閉形式に **厳密に** 一致し、理想比 L*on/(on+off) から 1 周期以内。"""
    lit = _lit_on_row((on, off), L)
    assert lit == _closed_form(on, off, L)
    ideal = (L + 1) * on / (on + off)
    assert abs(lit - ideal) <= (on + off)


def test_dashed_is_a_strict_subset_of_solid_and_shorter():
    solid = D.draw_line(np.zeros((20, 120)), (0, 10), (100, 10))
    dashed = D.draw_line(np.zeros((20, 120)), (0, 10), (100, 10),
                         style=DrawStyle(line_style="dashed"))
    assert int((solid > 0.5).sum()) == 101                       # L+1 画素
    assert int((dashed > 0.5).sum()) == _closed_form(10, 5, 100) == 70
    assert not ((dashed > 0.5) & ~(solid > 0.5)).any()           # 実線の部分集合


def test_dotted_and_dashed_are_different_pixel_sets():
    """点線と破線が「実際に違う画素列」であることを数値で示す(目視にしない)。"""
    dashed = D.draw_line(np.zeros((20, 120)), (0, 10), (100, 10),
                         style=DrawStyle(line_style="dashed")) > 0.5
    dotted = D.draw_line(np.zeros((20, 120)), (0, 10), (100, 10),
                         style=DrawStyle(line_style="dotted")) > 0.5
    assert int(dashed.sum()) == 70 and int(dotted.sum()) == 21
    assert int((dashed ^ dotted).sum()) == 63                    # 63 画素が食い違う
    assert ndimage.label(dashed)[1] == 7                         # 破線は 7 本の線分
    assert ndimage.label(dotted)[1] == 21                        # 点線は 21 個の点


def test_explicit_pattern_equals_named_style():
    a = D.draw_line(np.zeros((20, 120)), (0, 10), (100, 10),
                    style=DrawStyle(line_style=[10, 5]))
    b = D.draw_line(np.zeros((20, 120)), (0, 10), (100, 10),
                    style=DrawStyle(line_style="dashed"))
    assert _sha(a) == _sha(b)


def test_dashdot_has_two_run_lengths():
    m = D.draw_line(np.zeros((20, 200)), (0, 10), (170, 10),
                    style=DrawStyle(line_style="dashdot")) > 0.5
    lab, n = ndimage.label(m)
    sizes = sorted(set(int(s) for s in ndimage.sum(m, lab, range(1, n + 1))))
    assert sizes == [1, 10]                                      # 点(1px)と破線(10px)


def test_thick_dashes_keep_their_gaps():
    """太い破線でも破綻しない: 線分の本数が幅を変えても保たれる。"""
    comps = []
    for w in (1, 2, 3):
        t = D.draw_line(np.zeros((30, 130)), (5, 15), (115, 15),
                        style=DrawStyle(line_style="dashed", width=w)) > 0.5
        comps.append(ndimage.label(t)[1])
    assert comps == [8, 8, 8]


def test_dash_phase_is_continuous_across_corners():
    """角で位相をリセットしない ―― リセットすると各辺が必ず点灯から始まる。"""
    # 第 1 辺の長さ 87 は周期 15 の倍数でない(87 mod 15 = 12)ので、継いだ位相は
    # 第 2 辺を「消灯の途中」から始める ―― リセット方式なら必ず点灯から始まる。
    pts = [(10, 10), (97, 10), (97, 100)]
    got = D.draw_polyline(np.zeros((120, 120)), pts, style=DrawStyle(line_style=[10, 5])) > 0.5
    # リセット方式(各辺が phase 0 から)を組んで比べる
    reset = np.zeros((120, 120), bool)
    for a, b in zip(pts[:-1], pts[1:]):
        seg = D.draw_line(np.zeros((120, 120)), a, b, style=DrawStyle(line_style=[10, 5])) > 0.5
        reset |= seg
    assert int(got.sum()) != int(reset.sum())                    # 実際に違う図になる
    # 角のある辺の切れ目の位置が両者でずれている = 位相が継がれている証拠
    assert not np.array_equal(got, reset)


def test_dense_polyline_would_degenerate_if_phase_reset():
    """1–2 画素ごとに頂点がある輪郭では、位相リセットは実線と区別がつかなくなる。"""
    xld = _xld()
    solid = D.draw_contour(np.zeros((80, 80)), xld) > 0.5
    dashed = D.draw_contour(np.zeros((80, 80)), xld,
                            style=DrawStyle(line_style="dashed")) > 0.5
    n_solid, n_dash = int(solid.sum()), int(dashed.sum())
    assert n_solid == 59 and n_dash == 41                        # 実測(69.5 %)
    # 頂点リセット方式の再現: 各辺を独立に phase 0 から描くと実線に戻る
    p = np.asarray(xld["cs"][0], float)[:, ::-1]
    reset = np.zeros((80, 80), bool)
    for i in range(len(p)):
        reset |= D._polyline_mask((80, 80), [p[i], p[(i + 1) % len(p)]], False, (10.0, 5.0))
    assert int(reset.sum()) == n_solid                           # = 100 %、破線が消える
    assert n_dash < n_solid


def test_closed_polyline_dash_wraps_through_the_seam():
    """閉じた折れ線では閉じ辺も弧長の続き ―― 継ぎ目でパターンが合う保証はしない。"""
    pts = [(10, 10), (90, 10), (90, 90), (10, 90)]
    m = D.draw_polyline(np.zeros((110, 110)), pts, closed=True,
                        style=DrawStyle(line_style=[10, 5])) > 0.5
    solid = D.draw_polyline(np.zeros((110, 110)), pts, closed=True) > 0.5
    assert 0 < int(m.sum()) < int(solid.sum())
    assert not m[10, 10 + 12]                                    # 始点直後にも消灯区間がある


def test_circle_outline_dash_reduces_pixels_by_the_pattern_ratio():
    solid = D.draw_circle(np.zeros((100, 100)), (50, 50), 30.0) > 0.5
    dashed = D.draw_circle(np.zeros((100, 100)), (50, 50), 30.0,
                           style=DrawStyle(line_style="dashed")) > 0.5
    ratio = dashed.sum() / solid.sum()
    assert 0.55 < ratio < 0.80                                   # 10/15 = 0.667 付近
    assert not (dashed & ~solid).any()
    assert ndimage.label(dashed)[1] > 5                          # 弧が分かれている


# --------------------------------------------------------------------------
# 3. 色 ―― 役割名で描く
# --------------------------------------------------------------------------
def test_role_name_equals_palette_lookup():
    rgb = palette.role_color("wrong")
    a = D.draw_line(np.zeros((40, 60, 3)), (2, 20), (55, 20), "wrong")
    b = D.draw_line(np.zeros((40, 60, 3)), (2, 20), (55, 20), rgb)
    assert _sha(a) == _sha(b)
    assert np.allclose(a[20, 30], rgb)


def test_role_respects_scheme():
    st = DrawStyle(color="wrong", scheme="blue_orange")
    a = D.draw_line(np.zeros((40, 60, 3)), (2, 20), (55, 20), style=st)
    assert np.allclose(a[20, 30], palette.role_color("wrong", "blue_orange"))
    assert not np.allclose(a[20, 30], palette.role_color("wrong", "okabe_ito"))


def test_role_on_gray_image_uses_the_channel_mean():
    a = D.draw_line(np.zeros((40, 60)), (2, 20), (55, 20), "wrong")
    assert a[20, 30] == pytest.approx(float(np.mean(palette.role_color("wrong"))))


def test_explicit_color_argument_beats_the_style():
    st = DrawStyle(color="wrong")
    a = D.draw_line(np.zeros((40, 60, 3)), (2, 20), (55, 20), (1.0, 1.0, 1.0), style=st)
    assert np.allclose(a[20, 30], (1.0, 1.0, 1.0))


# --------------------------------------------------------------------------
# 4. 背景 / 塗り
# --------------------------------------------------------------------------
def test_new_canvas_gray_and_role_colour():
    g = D.new_canvas((30, 40), 0.25)
    assert g.shape == (30, 40) and np.all(g == 0.25)
    c = D.new_canvas((30, 40), "neutral")
    assert c.shape == (30, 40, 3) and np.allclose(c[0, 0], palette.role_color("neutral"))
    rgba = D.new_canvas((8, 9, 4), (1.0, 0.0, 0.0))
    assert rgba.shape == (8, 9, 4) and np.allclose(rgba[0, 0], (1.0, 0.0, 0.0, 0.0))


def test_new_canvas_defaults_to_black_and_clips():
    assert np.all(D.new_canvas((5, 5)) == 0.0)
    assert D.new_canvas((5, 5), 3.0).max() == 1.0                # [0,1] にクリップ


def test_new_canvas_takes_the_style_fill_colour():
    st = DrawStyle(color="wrong", fill_color="neutral")
    a = D.new_canvas((6, 7), style=st)
    assert np.allclose(a[0, 0], palette.role_color("neutral"))


def test_set_draw_fill_makes_circle_solid():
    st = DrawStyle(color=0.9, draw="fill")
    a = D.draw_circle(np.zeros((60, 60)), (30, 30), 15.0, style=st)
    assert a[30, 30] == pytest.approx(0.9)
    margin = D.draw_circle(np.zeros((60, 60)), (30, 30), 15.0, style=st.with_(draw="margin"))
    assert margin[30, 30] == 0.0 and margin[30, 45] > 0.5


def test_fill_colour_and_outline_colour_can_differ():
    st = DrawStyle(color="wrong", fill_color="neutral", draw="fill", width=3)
    a = D.draw_circle(np.zeros((80, 80, 3)), (40, 40), 20.0, style=st)
    assert np.allclose(a[40, 40], palette.role_color("neutral"))     # 内部 = 塗り色
    assert np.allclose(a[40, 60], palette.role_color("wrong"))       # 縁 = 線色


def test_fill_without_fill_colour_is_the_legacy_single_colour():
    st = DrawStyle(color=0.7, draw="fill")
    a = D.draw_circle(np.zeros((60, 60)), (30, 30), 15.0, style=st)
    b = D.draw_circle(np.zeros((60, 60)), (30, 30), 15.0, 0.7, fill=True)
    assert _sha(a) == _sha(b)


def test_markers_ignore_line_style_and_stay_solid():
    st = DrawStyle(color=1.0, line_style="dotted")
    a = D.draw_markers(np.zeros((60, 60)), [(30, 30)], size=6, shape="cross", style=st)
    b = D.draw_markers(np.zeros((60, 60)), [(30, 30)], 1.0, 6, "cross", 1)
    assert _sha(a) == _sha(b)
    for sh in ("square", "dot"):
        a = D.draw_markers(np.zeros((60, 60)), [(30, 30)], size=6, shape=sh, style=st)
        b = D.draw_markers(np.zeros((60, 60)), [(30, 30)], 1.0, 6, sh, 1)
        assert _sha(a) == _sha(b)


# --------------------------------------------------------------------------
# 5. 状態を持たせない設計の担保
# --------------------------------------------------------------------------
def test_context_manager_scopes_the_style_and_restores_it():
    pts = [(0, 10), (100, 10)]
    assert S.current_style() is None
    with S.draw_style(line_style="dashed"):
        inside = D.draw_line(np.zeros((20, 120)), *pts) > 0.5
        assert isinstance(S.current_style(), DrawStyle)
    outside = D.draw_line(np.zeros((20, 120)), *pts) > 0.5
    assert S.current_style() is None
    assert int(inside.sum()) == 70 and int(outside.sum()) == 101


def test_context_manager_nests_and_unwinds_on_exception():
    with S.draw_style(color=0.5):
        with S.draw_style(color=0.25):
            assert S.current_style().color == 0.25
        assert S.current_style().color == 0.5
        with pytest.raises(RuntimeError):
            with S.draw_style(color=0.1):
                raise RuntimeError("boom")
        assert S.current_style().color == 0.5                    # 例外でも戻る
    assert S.current_style() is None


def test_style_does_not_leak_across_threads():
    """並行生成でスタイルが混ざらない(モジュールグローバルを書き換えていない証拠)。"""
    seen = {}

    def worker():
        seen["ambient"] = S.current_style()
        seen["lit"] = int((D.draw_line(np.zeros((20, 120)), (0, 10), (100, 10)) > 0.5).sum())

    with S.draw_style(line_style="dotted"):
        t = threading.Thread(target=worker)
        t.start()
        t.join()
        assert int((D.draw_line(np.zeros((20, 120)), (0, 10), (100, 10)) > 0.5).sum()) == 21
    assert seen["ambient"] is None and seen["lit"] == 101         # 別スレッドは実線のまま


def test_drawing_order_does_not_change_a_figure():
    """図をまたいで状態が漏れない: with ブロックの前後で同じ呼び出しが同じ結果。"""
    call = LEGACY_CALLS["poly_closed"]
    before = _sha(call())
    with S.draw_style(color="wrong", line_style="dashed", width=4):
        D.draw_line(np.zeros((40, 40)), (0, 0), (39, 39))
    assert _sha(call()) == before


def test_drawstyle_is_immutable_and_set_aliases_return_new_values():
    st = DrawStyle()
    with pytest.raises(Exception):                               # frozen dataclass
        st.color = 0.5
    st2 = S.set_line_style(S.set_color(S.set_line_width(None, 3), "wrong"), [10, 5])
    assert st2.width == 3 and st2.color == "wrong" and st2.line_style == [10, 5]
    assert st == DrawStyle()                                     # 元は不変
    assert S.set_draw(st2, "fill").draw == "fill" and st2.draw == "margin"


def test_style_helpers_resolve_pattern_and_colour():
    assert S.resolve_pattern("solid") is None
    assert S.resolve_pattern("dashed") == (10.0, 5.0)
    assert S.resolve_pattern([4, 2]) == (4.0, 2.0)
    assert S.resolve_color(0.5) == 0.5
    assert S.resolve_color("right") == palette.role_color("right")
    assert S.resolve_color([1, 0, 0]) == (1.0, 0.0, 0.0)


# --------------------------------------------------------------------------
# 6. fail-closed(黙って実線/既定に落とさない)
# --------------------------------------------------------------------------
@pytest.mark.parametrize("bad", [
    "dashes",              # 未知の名前
    [],                    # 空パターン
    [10],                  # 奇数長(on/off の対でない)
    [10, 0],               # 0 の run
    [10, -5],              # 負の run
    [10, float("nan")],    # 非有限
    [float("inf"), 5],
])
def test_invalid_line_style_raises(bad):
    with pytest.raises(ValueError):
        S.resolve_pattern(bad)
    with pytest.raises(ValueError):
        DrawStyle(line_style=bad)


@pytest.mark.parametrize("bad", ["magenta", "Wrong", "ok"])
def test_unknown_colour_role_raises(bad):
    with pytest.raises(ValueError):
        S.resolve_color(bad)
    with pytest.raises(ValueError):
        D.draw_line(np.zeros((20, 20)), (0, 0), (10, 10), bad)


def test_unknown_scheme_and_bad_draw_mode_raise():
    with pytest.raises(ValueError):
        DrawStyle(color="wrong", scheme="neon")
    with pytest.raises(ValueError):
        DrawStyle(draw="outline")


@pytest.mark.parametrize("bad", [0, -1, 0.5, float("nan"), float("inf"), "3", None])
def test_invalid_width_raises(bad):
    with pytest.raises(ValueError):
        DrawStyle(width=bad)
    with pytest.raises(ValueError):
        D.draw_line(np.zeros((20, 20)), (0, 0), (10, 10), 1.0, bad)


def test_non_finite_colour_raises():
    with pytest.raises(ValueError):
        D.draw_line(np.zeros((20, 20)), (0, 0), (10, 10), float("nan"))
    with pytest.raises(ValueError):
        D.draw_line(np.zeros((20, 20, 3)), (0, 0), (10, 10), (1.0, float("inf"), 0.0))
    with pytest.raises(ValueError):
        S.resolve_color([])


def test_bad_style_object_raises():
    with pytest.raises(ValueError):
        D.draw_line(np.zeros((20, 20)), (0, 0), (10, 10), style="dashed")
    with pytest.raises(ValueError):
        with S.draw_style(DrawStyle(), color=0.5):
            pass
    with pytest.raises(ValueError):
        with S.draw_style("dashed"):
            pass


@pytest.mark.parametrize("bad", [(0, 10), (10, 0), (-3, 4), (10,), (2, 3, 4, 5), (10.5, 4)])
def test_new_canvas_rejects_bad_shapes(bad):
    with pytest.raises(ValueError):
        D.new_canvas(bad)


def test_new_canvas_rejects_bad_colour():
    with pytest.raises(ValueError):
        D.new_canvas((5, 5), "chartreuse")
    with pytest.raises(ValueError):
        D.new_canvas((5, 5), float("nan"))

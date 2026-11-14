# -*- coding: utf-8 -*-
"""studio_editops(Qt なし): 矩形選択の桁の変換・複数カーソルの編集の計画・行の操作・括弧・キーの表・対訳。

一番壊れやすいのは「見た目の桁 ↔ 文字の位置」なので、ここで厚く確かめる(全角・タブ・絵文字・結合文字)。
窓を使う試験は tests/test_studio_editops_qt_2026_11_13.py。
"""
import ast
import io
import os

import pytest

import studio_editops as eo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAMILY = "\U0001F468‍\U0001F469‍\U0001F467"          # 家族(ZWJ で 3 人を繋いだ絵文字 1 つ)
FLAG_JP = "\U0001F1EF\U0001F1F5"                                # 国旗(地域指示記号 2 つ)
THUMB = "\U0001F44D\U0001F3FD"                                  # 親指 + 肌の色
E_ACUTE = "é"                                             # e + 結合アクセント
GA = "が"                                             # か + 結合濁点


def _spans(text, tab=4):
    return [(c.start, c.end, c.col, c.width) for c in eo.cells(text, tab)]


# --------------------------------------------------------------------------- #
# まとまりと幅
# --------------------------------------------------------------------------- #
def test_ascii_is_one_column_per_character():
    assert _spans("abc") == [(0, 1, 0, 1), (1, 2, 1, 1), (2, 3, 2, 1)]
    assert eo.text_width("hello world") == 11
    assert eo.text_width("") == 0


@pytest.mark.parametrize("tab,expected", [
    (4, [(0, 1, 0, 1), (1, 2, 1, 3), (2, 3, 4, 1), (3, 4, 5, 3), (4, 5, 8, 1)]),
    (8, [(0, 1, 0, 1), (1, 2, 1, 7), (2, 3, 8, 1), (3, 4, 9, 7), (4, 5, 16, 1)]),
])
def test_tab_runs_to_the_next_tab_stop(tab, expected):
    assert _spans("a\tb\tc", tab) == expected


def test_tab_at_a_tab_stop_is_a_full_tab():
    assert _spans("\t\tx", 4) == [(0, 1, 0, 4), (1, 2, 4, 4), (2, 3, 8, 1)]
    assert _spans("abcd\tx", 4) == [(0, 1, 0, 1), (1, 2, 1, 1), (2, 3, 2, 1), (3, 4, 3, 1), (4, 5, 4, 4), (5, 6, 8, 1)]


def test_full_width_is_two_columns_and_half_width_kana_is_one():
    assert _spans("日本語") == [(0, 1, 0, 2), (1, 2, 2, 2), (2, 3, 4, 2)]
    assert eo.text_width("ｱｲｳ") == 3                    # 半角カナ
    assert eo.text_width("ＡＢ") == 4                    # 全角の英字
    assert eo.text_width("x = 1  # 日本語のコメント") == 9 + 2 * 8
    assert eo.char_width("あ") == 2 and eo.char_width("ｱ") == 1 and eo.char_width("a") == 1


def test_half_width_voiced_mark_has_its_own_column():
    assert eo.text_width("ｶﾞ") == 2                     # 半角の濁点は 1 桁を使う(結合文字ではない)
    assert len(eo.cells("ｶﾞ")) == 2


def test_emoji_is_one_cluster_of_two_columns():
    assert _spans("a\U0001F600b") == [(0, 1, 0, 1), (1, 2, 1, 2), (2, 3, 3, 1)]
    assert _spans(FAMILY) == [(0, 5, 0, 2)]
    assert _spans(FLAG_JP) == [(0, 2, 0, 2)]
    assert _spans(FLAG_JP + FLAG_JP) == [(0, 2, 0, 2), (2, 4, 2, 2)]      # 国旗 2 つは 2 つのまとまり
    assert _spans(THUMB) == [(0, 2, 0, 2)]


def test_combining_marks_join_the_previous_character():
    assert _spans(E_ACUTE + "x") == [(0, 2, 0, 1), (2, 3, 1, 1)]
    assert _spans(GA) == [(0, 2, 0, 2)]
    assert eo.char_width("́") == 0
    assert _spans("❤️") == [(0, 2, 0, 1)]                        # 異体字セレクタは前に付く
    assert _spans("한") == [(0, 3, 0, 2)]                  # ハングルの字母 3 つ = 1 文字


def test_a_leading_combining_mark_and_one_after_a_tab_stand_alone():
    assert _spans("́a") == [(0, 1, 0, 1), (1, 2, 1, 1)]
    assert _spans("\t́") == [(0, 1, 0, 4), (1, 2, 4, 1)]


def test_ambiguous_width_characters_are_one_column_unless_the_font_says_wide():
    t = "※a○b"
    assert _spans(t) == [(0, 1, 0, 1), (1, 2, 1, 1), (2, 3, 2, 1), (3, 4, 3, 1)]
    asked = []
    wide = eo.Columns(4, lambda ch: asked.append(ch) or ch == "※")
    assert _spans(t, wide) == [(0, 1, 0, 2), (1, 2, 2, 1), (2, 3, 3, 1), (3, 4, 4, 1)]
    assert asked == ["※", "○"]                                    # 曖昧幅の文字だけを書体に聞く
    assert eo.text_width(t, wide) == 5 and eo.index_at_col(t, 2, wide) == 1 and eo.col_of(t, 2, wide) == 3
    assert _spans("a\tb", eo.Columns(8)) == _spans("a\tb", 8)
    assert eo.box_carets(["※abc", "abcde"], 0, 2, 1, 4, wide) == [eo.Caret(0, 1, 3), eo.Caret(1, 2, 4)]


def test_char_width_rejects_tabs_and_strings():
    with pytest.raises(ValueError):
        eo.char_width("\t")
    with pytest.raises(ValueError):
        eo.char_width("ab")
    with pytest.raises(ValueError):
        eo.cells("a", tab=0)


# --------------------------------------------------------------------------- #
# 桁 ↔ 位置
# --------------------------------------------------------------------------- #
MIXED = "a\tb日本😀" + E_ACUTE + "x"      # 桁: a0 tab1-3 b4 日5-6 本7-8 😀9-10 é11 x12


def test_col_of_every_index_in_a_mixed_line():
    assert [eo.col_of(MIXED, i) for i in range(len(MIXED) + 1)] == [0, 1, 4, 5, 7, 9, 11, 11, 12, 13]
    assert eo.col_of(MIXED, -3) == 0 and eo.col_of(MIXED, 99) == 13


def test_index_at_col_goes_to_the_nearest_boundary_and_ties_go_left():
    got = [eo.index_at_col(MIXED, c) for c in range(15)]
    #        桁 0  1  2  3  4  5  6  7  8  9 10 11 12 13 14
    assert got == [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 8, 9, 9]
    assert eo.index_at_col("日本語", 1) == 0          # 全角の真ん中: 同じ距離なら左
    assert eo.index_at_col("\tx", 1) == 0 and eo.index_at_col("\tx", 2) == 0 and eo.index_at_col("\tx", 3) == 1


def test_columns_past_the_end_of_the_line_stop_at_the_end():
    assert eo.index_at_col("ab", 10) == 2
    assert eo.index_at_col("", 0) == 0 and eo.index_at_col("", 7) == 0
    assert eo.index_at_col("日本", 99) == 2
    assert eo.col_of("", 0) == 0


def test_boundaries_never_split_a_cluster():
    t = "a" + FAMILY + "b" + E_ACUTE
    assert eo.snap_index(t, 3) == 1 and eo.snap_index(t, 1) == 1 and eo.snap_index(t, 99) == len(t)
    assert eo.next_boundary(t, 1) == 6 and eo.next_boundary(t, 3) == 6 and eo.next_boundary(t, len(t)) == len(t)
    assert eo.prev_boundary(t, 6) == 1 and eo.prev_boundary(t, len(t)) == 7 and eo.prev_boundary(t, 0) == 0
    assert eo.next_boundary("abc", 1) == 2 and eo.prev_boundary("abc", 1) == 0


def test_step_col_moves_by_one_cluster_on_text_and_by_one_column_past_the_end():
    assert [eo.step_col("a日b", c, +1) for c in (0, 1, 3, 4, 5)] == [1, 3, 4, 5, 6]
    assert [eo.step_col("a日b", c, -1) for c in (6, 5, 4, 3, 1, 0)] == [5, 4, 3, 1, 0, 0]
    assert eo.step_col("a\tb", 1, +1) == 4 and eo.step_col("a\tb", 4, -1) == 1


def test_utf16_positions_count_two_units_for_characters_outside_the_bmp():
    t = "a😀b日😀"
    assert [eo.cp_to_u16(t, i) for i in range(6)] == [0, 1, 3, 4, 5, 7]
    assert [eo.u16_to_cp(t, u) for u in range(8)] == [0, 1, 1, 2, 3, 4, 4, 5]     # サロゲートの途中は文字の先頭
    assert eo.u16_len(t) == 7 and eo.u16_len("abc") == 3 and eo.u16_len("") == 0
    assert eo.cp_to_u16("abc", 99) == 3 and eo.u16_to_cp("abc", 99) == 3 and eo.u16_to_cp(t, -1) == 0


ALPHABET = ["a", "Z", " ", "\t", "日", "語", "ｱ", "ﾞ", "Ａ", "́", "゙", "\U0001F600", "‍",
            "\U0001F468", "\U0001F1EF", "\U0001F1F5", "\U0001F3FD", "️", "é", " ", "(", "#"]


def _hyp():
    hypothesis = pytest.importorskip("hypothesis")
    return hypothesis, hypothesis.strategies


def test_property_cells_tile_the_line_and_columns_are_contiguous():
    hypothesis, st = _hyp()
    seen = []

    @hypothesis.settings(max_examples=300, deadline=None)
    @hypothesis.given(st.lists(st.sampled_from(ALPHABET), max_size=24).map("".join), st.sampled_from([1, 2, 4, 8]))
    def run(text, tab):
        cs = eo.cells(text, tab)
        seen.append(len(cs))
        assert len(cs) <= len(text)
        assert bool(cs) == bool(text)                  # 空の行だけがまとまり 0 個
        pos, col = 0, 0
        for c in cs:
            assert c.start == pos and c.end > c.start and c.col == col and c.width >= 1
            pos, col = c.end, c.col + c.width
        assert pos == len(text) and col == eo.text_width(text, tab)

    run()
    assert len(seen) >= 100 and max(seen) >= 3, "試した行が少ない・短い: %d" % len(seen)


def test_property_round_trip_between_columns_and_boundaries():
    hypothesis, st = _hyp()
    checked = [0]

    @hypothesis.settings(max_examples=300, deadline=None)
    @hypothesis.given(st.lists(st.sampled_from(ALPHABET), max_size=24).map("".join), st.sampled_from([2, 4, 8]),
                      st.integers(min_value=0, max_value=60))
    def run(text, tab, col):
        cs = eo.cells(text, tab)
        bounds = [c.start for c in cs] + [len(text)]
        cols = [c.col for c in cs] + [eo.text_width(text, tab)]
        for i, c in zip(bounds, cols):                 # 境目 → 桁 → 境目 は元へ戻る
            assert eo.col_of(text, i, tab) == c
            assert eo.index_at_col(text, c, tab) == i
            checked[0] += 1
        i = eo.index_at_col(text, col, tab)            # どの桁も、一番近い境目へ行く
        assert i in bounds
        got = eo.col_of(text, i, tab)
        best = min(abs(c - col) for c in cols)
        assert abs(got - col) == best or (col > cols[-1] and i == len(text))
        assert eo.snap_index(text, i) == i

    run()
    assert checked[0] >= 300, "境目を確かめた数が少ない: %d" % checked[0]


def test_property_utf16_round_trip():
    hypothesis, st = _hyp()
    checked = [0]

    @hypothesis.settings(max_examples=200, deadline=None)
    @hypothesis.given(st.lists(st.sampled_from(ALPHABET), max_size=24).map("".join))
    def run(text):
        assert eo.u16_len(text) == len(text.encode("utf-16-le")) // 2
        for i in range(len(text) + 1):
            u = eo.cp_to_u16(text, i)
            assert u == len(text[:i].encode("utf-16-le")) // 2
            assert eo.u16_to_cp(text, u) == i
            checked[0] += 1

    run()
    assert checked[0] >= 200


# --------------------------------------------------------------------------- #
# 行の分け方(CRLF)
# --------------------------------------------------------------------------- #
def test_crlf_lf_and_cr_documents_give_the_same_lines():
    lf = "ab\n\n日本\nx"
    for nl in ("\r\n", "\n", "\r"):
        rows, kind = eo.split_lines(lf.replace("\n", nl))
        assert rows == ["ab", "", "日本", "x"] and kind == nl
    assert eo.split_lines("") == ([""], "\n")
    rows, _ = eo.split_lines("abcdef\r\nab\r\nabcdef")
    assert eo.box_carets(rows, 0, 2, 2, 4) == [eo.Caret(0, 2, 4), eo.Caret(1, 2, 2), eo.Caret(2, 2, 4)]


# --------------------------------------------------------------------------- #
# 箱 → 行ごとの選択
# --------------------------------------------------------------------------- #
LINES = ["abc def", "ab", "", "abcdefgh", "日本語のコメント", "a\tb\tc"]


def test_box_selects_the_same_columns_on_every_line_that_reaches_the_left_edge():
    got = eo.box_carets(LINES, 0, 2, 5, 5)
    assert got == [eo.Caret(0, 2, 5), eo.Caret(1, 2, 2), eo.Caret(3, 2, 5), eo.Caret(4, 1, 2), eo.Caret(5, 1, 3)]
    # 空行(幅 0 < 2)は入らない。"ab" は幅がちょうど 2 なので行末に幅 0 で入る。


def test_box_dragged_right_to_left_keeps_the_direction():
    got = eo.box_carets(LINES, 3, 5, 0, 2)
    assert got[0] == eo.Caret(0, 5, 2) and got[-1] == eo.Caret(3, 5, 2)
    assert [c.start for c in got] == [2, 2, 2] and [c.end for c in got] == [5, 2, 5]


def test_zero_width_box_is_one_cursor_per_line():
    got = eo.box_carets(LINES, 0, 3, 4, 3)
    assert [(c.line, c.anchor, c.pos) for c in got] == [(0, 3, 3), (3, 3, 3), (4, 1, 1)]
    assert len(got) == 3 and all(c.empty for c in got)


def test_when_no_line_reaches_the_box_every_line_gets_a_cursor_at_its_end():
    got = eo.box_carets(LINES, 0, 40, 2, 44)
    assert got == [eo.Caret(0, 7, 7), eo.Caret(1, 2, 2), eo.Caret(2, 0, 0)]


def test_box_on_full_width_text_takes_whole_characters_only():
    rows = ["# 日本語", "# 漢字かな", "# abcdef"]
    got = eo.box_carets(rows, 0, 2, 2, 6)
    assert [rows[c.line][c.start:c.end] for c in got] == ["日本", "漢字", "abcd"]
    got = eo.box_carets(rows, 0, 3, 2, 5)              # 両端が全角の真ん中: 左へ寄る
    assert [rows[c.line][c.start:c.end] for c in got] == ["日", "漢", "bc"]


def test_box_with_emoji_and_combining_marks_never_cuts_a_cluster():
    rows = ["x" + FAMILY + "yz", "x" + E_ACUTE + "abc", "x😀yz"]
    got = eo.box_carets(rows, 0, 1, 2, 3)
    assert [rows[c.line][c.start:c.end] for c in got] == [FAMILY, E_ACUTE + "a", "😀"]
    assert len(got) == 3


def test_box_lines_are_clamped_to_the_document():
    assert eo.box_carets(["ab", "cd"], -5, 0, 99, 1) == [eo.Caret(0, 0, 1), eo.Caret(1, 0, 1)]


# --------------------------------------------------------------------------- #
# 編集の計画
# --------------------------------------------------------------------------- #
def test_typing_goes_to_the_same_column_on_every_line():
    carets = eo.box_carets(LINES, 0, 2, 3, 2)
    edits, new = eo.plan_replace(carets, ["X"] * len(carets))
    assert eo.apply_edits(LINES, edits)[:4] == ["abXc def", "abX", "", "abXcdefgh"]
    assert new == [eo.Caret(0, 3, 3), eo.Caret(1, 3, 3), eo.Caret(3, 3, 3)]


def test_replace_with_several_carets_on_one_line_shifts_the_later_ones():
    rows = ["foo bar foo"]
    carets = [eo.Caret(0, 0, 3), eo.Caret(0, 8, 11)]
    edits, new = eo.plan_replace(carets, ["quux", "z"])
    assert eo.apply_edits(rows, edits) == ["quux bar z"]
    assert new == [eo.Caret(0, 4, 4), eo.Caret(0, 10, 10)]
    with pytest.raises(ValueError):
        eo.plan_replace(carets, ["x"])


def test_tabs_keep_carets_right_after_what_was_typed():
    rows = ["a\tb", "a\tb"]
    carets = eo.box_carets(rows, 0, 2, 1, 2)           # タブの途中 → 左(位置 1)
    assert carets == [eo.Caret(0, 1, 1), eo.Caret(1, 1, 1)]
    for ch in "xy":
        edits, carets = eo.plan_replace(carets, [ch] * 2)
        rows = eo.apply_edits(rows, edits)
    assert rows == ["axy\tb", "axy\tb"] and carets == [eo.Caret(0, 3, 3), eo.Caret(1, 3, 3)]


def test_delete_and_backspace_remove_a_selection_or_one_whole_cluster():
    rows = ["a" + FAMILY + "b", "a日b", "ab"]
    carets = [eo.Caret(0, 1, 1), eo.Caret(1, 1, 1), eo.Caret(2, 2, 2)]
    edits, new = eo.plan_delete(rows, carets, backward=False)
    assert eo.apply_edits(rows, edits) == ["ab", "ab", "ab"]            # 行末の Delete は何もしない
    assert new == [eo.Caret(0, 1, 1), eo.Caret(1, 1, 1), eo.Caret(2, 2, 2)]
    carets = [eo.Caret(0, 6, 6), eo.Caret(1, 2, 2), eo.Caret(2, 0, 0)]
    edits, new = eo.plan_delete(rows, carets, backward=True)
    assert eo.apply_edits(rows, edits) == ["ab", "ab", "ab"]            # 行頭の Backspace は何もしない
    assert new == [eo.Caret(0, 1, 1), eo.Caret(1, 1, 1), eo.Caret(2, 0, 0)]
    edits, new = eo.plan_delete(["abcdef"], [eo.Caret(0, 1, 4)], backward=True)
    assert eo.apply_edits(["abcdef"], edits) == ["aef"] and new == [eo.Caret(0, 1, 1)]


@pytest.mark.parametrize("clip,count,mode,texts", [
    ("1\n2\n3", 3, "spread", ["1", "2", "3"]),
    ("1\r\n2\r\n3\r\n", 3, "spread", ["1", "2", "3"]),
    ("x", 3, "same", ["x", "x", "x"]),
    ("x\n", 2, "same", ["x", "x"]),
    ("", 2, "same", ["", ""]),
    ("1\n2", 3, "full", ["1\n2"] * 3),
    ("1\n2", 1, "full", ["1\n2"]),
])
def test_paste_is_spread_by_rows_or_repeated(clip, count, mode, texts):
    assert eo.paste_rows(clip, count) == (mode, texts)


def test_apply_edits_with_newlines_adds_lines_and_does_not_change_its_input():
    rows = ["ab", "cd"]
    out = eo.apply_edits(rows, [eo.Edit(0, 1, 1, "1\n2"), eo.Edit(1, 0, 0, "1\n2")])
    assert out == ["a1", "2b", "1", "2cd"] and rows == ["ab", "cd"]


def test_shift_carets_follows_edits_on_the_same_line():
    carets = [eo.Caret(0, 2, 5), eo.Caret(1, 0, 0), eo.Caret(2, 3, 1)]
    edits = [eo.Edit(0, 0, 0, "    "), eo.Edit(2, 0, 2, "")]
    assert eo.shift_carets(carets, edits) == [eo.Caret(0, 6, 9), eo.Caret(1, 0, 0), eo.Caret(2, 1, 0)]


def test_move_carets_by_cluster_and_merge_when_they_meet():
    rows = ["a" + FAMILY + "b", "  xy"]
    carets = [eo.Caret(0, 6, 6), eo.Caret(1, 4, 4)]
    left = eo.move_carets(rows, carets, "left")
    assert left == [eo.Caret(0, 1, 1), eo.Caret(1, 3, 3)]
    assert eo.move_carets(rows, left, "right", select=True) == [eo.Caret(0, 1, 6), eo.Caret(1, 3, 4)]
    assert eo.move_carets(rows, carets, "home") == [eo.Caret(0, 0, 0), eo.Caret(1, 2, 2)]
    assert eo.move_carets(rows, [eo.Caret(1, 2, 2)], "home") == [eo.Caret(1, 0, 0)]
    assert eo.move_carets(rows, carets, "end") == [eo.Caret(0, 7, 7), eo.Caret(1, 4, 4)]
    assert eo.move_carets(["abc"], [eo.Caret(0, 0, 0), eo.Caret(0, 1, 1)], "left") == [eo.Caret(0, 0, 0)]
    assert eo.move_carets(["abc"], [eo.Caret(0, 0, 2)], "left") == [eo.Caret(0, 0, 0)]
    with pytest.raises(ValueError):
        eo.move_carets(rows, carets, "up")


def test_normalize_carets_sorts_and_merges_overlaps():
    got = eo.normalize_carets([eo.Caret(1, 0, 0), eo.Caret(0, 4, 2), eo.Caret(0, 3, 6), eo.Caret(0, 6, 8)])
    assert got == [eo.Caret(0, 6, 2), eo.Caret(0, 6, 8), eo.Caret(1, 0, 0)]
    assert eo.Caret(0, 4, 2).start == 2 and eo.Caret(0, 4, 2).end == 4 and not eo.Caret(0, 4, 2).empty


# --------------------------------------------------------------------------- #
# 行の操作
# --------------------------------------------------------------------------- #
def test_indent_skips_blank_lines_and_outdent_removes_one_level():
    rows = ["a", "", "    b", "  c", "\td", "   "]
    assert eo.apply_edits(rows, eo.plan_indent(rows, range(6))) == ["    a", "", "        b", "      c", "    \td", "   "]
    assert eo.apply_edits(rows, eo.plan_outdent(rows, range(6))) == ["a", "", "b", "c", "d", ""]
    assert eo.plan_outdent(["x"], [0]) == []


def test_toggle_comment_at_the_shallowest_indent_and_back():
    rows = ["def f():", "    a = 1", "", "    return a"]
    edits = eo.plan_toggle_comment(rows, [1, 2, 3], "#")
    out = eo.apply_edits(rows, edits)
    assert out == ["def f():", "    # a = 1", "", "    # return a"] and len(edits) == 2
    assert eo.apply_edits(out, eo.plan_toggle_comment(out, [1, 2, 3], "#")) == rows
    mixed = ["# a", "b"]
    assert eo.apply_edits(mixed, eo.plan_toggle_comment(mixed, [0, 1], "#")) == ["# # a", "# b"]
    assert eo.apply_edits(["*x", "* y"], eo.plan_toggle_comment(["*x", "* y"], [0, 1], "*")) == ["x", "y"]
    assert eo.plan_toggle_comment(["", "  "], [0, 1], "#") == []
    with pytest.raises(ValueError):
        eo.plan_toggle_comment(rows, [0], "")


def test_reorder_lines_up_down_and_at_the_edges():
    rows = ["a", "b", "c", "d"]
    assert eo.reorder_lines(rows, 1, 2, -1) == (0, 2, ["b", "c", "a"])
    assert eo.reorder_lines(rows, 1, 2, +1) == (1, 3, ["d", "b", "c"])
    assert eo.reorder_lines(rows, 0, 1, -1) is None and eo.reorder_lines(rows, 2, 3, +1) is None


def test_trailing_whitespace_is_removed_but_full_width_spaces_stay():
    rows = ["a  ", "b\t", "c", "  ", "d　", ""]
    edits = eo.strip_trailing_edits(rows)
    assert len(edits) == 3
    assert eo.apply_edits(rows, edits) == ["a", "b", "c", "", "d　", ""]
    assert eo.strip_trailing_text("a  \r\nb\t\r\n") == "a\r\nb\r\n"
    assert eo.strip_trailing_text("a \nb") == "a\nb"


# --------------------------------------------------------------------------- #
# 語・次の一致・括弧
# --------------------------------------------------------------------------- #
def test_word_at_the_cursor_or_just_before_it():
    t = "foo_bar = baz(1)  # 変数"
    assert eo.word_at(t, 0) == (0, 7) and eo.word_at(t, 7) == (0, 7) and eo.word_at(t, 3) == (0, 7)
    assert eo.word_at(t, 8) is None and eo.word_at(t, 13) == (10, 13)
    assert eo.word_at(t, len(t)) == (20, 22) and eo.word_at("", 0) is None


def test_next_occurrence_wraps_skips_taken_and_can_match_whole_words():
    rows = ["x = xx + x", "y = x", "x"]
    assert eo.next_occurrence(rows, "x", 0, 1) == (0, 4)
    assert eo.next_occurrence(rows, "x", 0, 1, whole_word=True) == (0, 9)
    assert eo.next_occurrence(rows, "x", 2, 1, whole_word=True) == (0, 0)             # 末尾から先頭へ
    taken = {(0, 0), (0, 9), (1, 4), (2, 0)}
    assert eo.next_occurrence(rows, "x", 0, 1, taken, whole_word=True) is None        # 全部選んだら無し
    assert eo.next_occurrence(rows, "x", 0, 10, {(1, 4)}, whole_word=True) == (2, 0)
    assert eo.next_occurrence(rows, "", 0, 0) is None and eo.next_occurrence(rows, "zz", 0, 0) is None
    assert eo.next_occurrence(["ab ab"], "ab", 0, 2) == (0, 3) and eo.next_occurrence(["ab ab"], "ab", 0, 5) == (0, 0)


def test_brackets_in_strings_and_comments_are_not_counted():
    rows = ["f(a, [1, 2], '(')  # )", 'g = """ ( ', ' ) """ + h({', "    'k': 1})"]
    table = eo.bracket_table(rows, "#")
    assert [ch for _i, ch in table[0]] == ["(", "[", "]", ")"]
    assert table[1] == [] and [ch for _i, ch in table[2]] == ["(", "{"] and [ch for _i, ch in table[3]] == ["}", ")"]
    assert eo.match_bracket(table, 0, 1) == (0, 1, 0, 16)
    assert eo.match_bracket(table, 0, 17) == (0, 16, 0, 1)              # カーソルが括弧の後ろ
    assert eo.match_bracket(table, 0, 5) == (0, 5, 0, 10)
    assert eo.match_bracket(table, 2, 10) == (2, 10, 3, 11)             # 行をまたぐ
    assert eo.match_bracket(table, 3, 10) == (3, 10, 2, 11)
    assert eo.match_bracket(table, 0, 3) is None and eo.match_bracket(table, 9, 0) is None


def test_unbalanced_brackets_have_no_partner_and_pipeline_comment_lines_are_skipped():
    assert eo.match_bracket(eo.bracket_table(["(()"], "#"), 0, 0) is None
    assert eo.match_bracket(eo.bracket_table(["())"], "#"), 0, 3) is None
    table = eo.bracket_table(["* note (", "blur (3, 3)"], "*")
    assert table[0] == [] and eo.match_bracket(table, 1, 5) == (1, 5, 1, 10)


# --------------------------------------------------------------------------- #
# キーの表
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("raw,want", [
    ("shift+ctrl+k", "Ctrl+Shift+K"), ("Alt+Shift+.", "Shift+Alt+."), ("Ctrl++", "Ctrl++"), ("Ctrl+=", "Ctrl+="),
    ("Escape", "Esc"), ("Shift+Backtab", "Shift+Tab"), ("Ctrl+K, Ctrl+C", "Ctrl+K"), ("ctrl+]", "Ctrl+]"),
    ("Ctrl+Enter", "Ctrl+Return"), ("Alt+Up", "Alt+Up"), ("F5", "F5"), ("", ""),
])
def test_normalize_key(raw, want):
    assert eo.normalize_key(raw) == want


def test_the_keymap_has_no_key_assigned_twice_and_every_command_is_named_once():
    keys = [eo.normalize_key(k) for b in eo.KEYMAP for k in b.keys]
    assert len(keys) >= 15 and len(keys) == len(set(keys)), sorted(k for k in keys if keys.count(k) > 1)
    commands = [b.command for b in eo.KEYMAP]
    assert len(commands) == len(set(commands)) == 15
    assert {b.group for b in eo.KEYMAP} == {"box", "line"}
    assert {b.when for b in eo.KEYMAP} == {"always", "box", "no_own_comment"}


def test_the_keymap_does_not_take_keys_the_editor_parts_handle_themselves():
    internal = [(k, "editor", True) for k in eo.EDITOR_INTERNAL_KEYS]
    assert len(internal) == 11
    assert eo.find_conflicts(eo.active_bindings(editor_has_comment=True), internal) == []
    # Ctrl+/ を自分で持たないエディタ(CodeEditor / PyEditor)に付けた時だけ、こちらの Ctrl+/ が効く
    got = eo.find_conflicts(eo.active_bindings(editor_has_comment=False), internal)
    assert got == [("line.comment", "Ctrl+/", "editor")]


def test_find_conflicts_sees_only_shortcuts_that_reach_the_editor():
    mine = eo.active_bindings(editor_has_comment=True)
    assert ("line.duplicate", "Ctrl+D") in mine and ("box.cancel", "Esc") not in mine
    existing = [("Ctrl+D", "Duplicate stage", False), ("ctrl+shift+k", "Something", True), ("F5", "Run", True)]
    assert eo.find_conflicts(mine, existing) == [("line.delete", "Ctrl+Shift+K", "Something")]
    assert ("box.cancel", "Esc") in eo.active_bindings(include_box_only=True)


def test_the_document_lists_every_key_of_the_keymap():
    path = os.path.join(ROOT, "docs", "STUDIO_EDITOR_KEYS.md")
    doc = io.open(path, encoding="utf-8").read()
    keys = [k for b in eo.KEYMAP for k in b.keys]
    assert len(keys) >= 15
    absent = [k for k in keys if ("`%s`" % k) not in doc]
    assert absent == [], "文書に無いキー: %s" % absent


# --------------------------------------------------------------------------- #
# 対訳
# --------------------------------------------------------------------------- #
def test_every_ui_string_has_five_translations_and_the_table_has_nothing_else():
    table = eo.load_table()
    strings = eo.ui_strings()
    # 26 -> 27(2026-11-13: キーの設定で変えたキーを「使い方」の窓に並べる前の 1 行 MSG_KEYS_CHANGED)
    # 27 -> 28(2026-11-15: 「使い方」の窓のボタン BTN_CLOSE。Qt の標準の Close は訳されない)
    assert len(strings) == 28 and len(set(strings)) == 28
    assert eo.missing() == []
    assert sorted(table) == sorted(strings)
    assert eo.LANGS == ("en", "ja", "zh", "tw", "ko", "de")
    assert eo.missing({"Indent": {"ja": "字下げ"}})[:1] == [("Extend box selection up", "ja")]


def test_translations_keep_the_placeholders_and_japanese_is_not_left_in_english():
    table = eo.load_table()
    assert len(table) == 28
    bad = []
    for key, row in table.items():
        for lang in eo.LANGS[1:]:
            if row[lang].count("%d") != key.count("%d") or row[lang].count("\n") != key.count("\n"):
                bad.append((key[:20], lang))
            if lang != "de" and row[lang].isascii():
                bad.append((key[:20], lang, "ascii"))
    assert bad == []


def test_make_tr_follows_the_language_and_falls_back_to_english():
    assert eo.make_tr("ja")("Duplicate line") == "行を複製"
    assert eo.make_tr("en")("Duplicate line") == "Duplicate line"
    assert eo.make_tr("ja")("not in the table") == "not in the table" and eo.make_tr("ja")("") == ""
    lang = {"code": "de"}
    tr = eo.make_tr(lambda: lang["code"])
    assert tr("Delete line") == "Zeile löschen"
    lang["code"] = "ko"
    assert tr("Delete line") == "줄 삭제"
    lang["code"] = "fr"                                # 知らない言語は英語のまま
    assert tr("Delete line") == "Delete line"
    first = eo.make_tr("ja", first=lambda s: "先" if s == "Indent" else s)
    assert first("Indent") == "先" and first("Outdent") == "字下げを戻す"
    with pytest.raises(ValueError):
        eo.make_tr("fr")
    with pytest.raises(ValueError):
        eo.load_table(os.path.join(ROOT, "studio_assets", "no_such_table.json"))


def test_the_logic_module_does_not_import_qt():
    src = io.open(os.path.join(ROOT, "studio_editops.py"), encoding="utf-8").read()
    names = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    assert len(names) >= 4, names
    assert [n for n in names if n.startswith(("PySide", "PyQt", "studio"))] == []

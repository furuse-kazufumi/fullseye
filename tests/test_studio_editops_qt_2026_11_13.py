# -*- coding: utf-8 -*-
"""studio_editops_qt: 矩形選択・複数カーソル・行の操作を、本物のキーとマウスのイベントで確かめる(offscreen)。

* 素の ``QPlainTextEdit`` と、Studio の本物のエディタの部品(``ProgramEditor`` / ``CodeEditor`` / ``PyEditor``)に
  取り付けて、結果の文面を期待の文面と 1 文字ずつ比べる。Undo 1 回で元へ、Redo で戻る。
* クリップボードは差し替える(利用者の本物のクリップボードには触らない)。設定は一時ファイル。
* 取り付けていないエディタ・外したエディタは、元の振る舞いのまま。
"""
import os
import time

import pytest

import studio_editops as eo

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

import studio_editops_qt as eq  # noqa: E402

K = QtCore.Qt
SA = K.ShiftModifier | K.AltModifier
FAMILY = "\U0001F468\u200d\U0001F469\u200d\U0001F467"


class FakeClipboard:
    """``text()`` / ``setText()`` だけを持つ差し替えのクリップボード。"""

    def __init__(self, text=""):
        self._text = text
        self.sets = 0

    def text(self):
        return self._text

    def setText(self, text):                       # noqa: N802 (Qt の名前に合わせる)
        self._text = text
        self.sets += 1


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _pump(sec=0.05):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.005)


def _show(ed, text):
    f = QtGui.QFont("Consolas")
    f.setStyleHint(QtGui.QFont.Monospace)
    f.setPointSize(10)
    if type(ed) is QtWidgets.QPlainTextEdit:
        ed.setFont(f)
        ed.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
    ed.resize(760, 420)
    ed.show()
    ed.setPlainText(text)
    ed.document().clearUndoRedoStacks()
    ed.setFocus()
    _pump(0.05)
    return ed


_KEEP = []


def _plain(app, text, **opts):
    ed = _show(QtWidgets.QPlainTextEdit(), text)
    clip = FakeClipboard()
    ops = eq.install(ed, clipboard=clip, **opts)
    _KEEP.append(ed)
    return ed, ops, clip


def _goto(ed, line, col, anchor_col=None):
    """カーソルを ``line`` 行の文字の位置 ``col`` へ(``anchor_col`` があればそこから選ぶ)。"""
    blk = ed.document().findBlockByNumber(line)
    t = blk.text()
    cur = ed.textCursor()
    if anchor_col is not None:
        cur.setPosition(blk.position() + eo.cp_to_u16(t, anchor_col))
        cur.setPosition(blk.position() + eo.cp_to_u16(t, col), QtGui.QTextCursor.KeepAnchor)
    else:
        cur.setPosition(blk.position() + eo.cp_to_u16(t, col))
    ed.setTextCursor(cur)


def _key(ed, key, mods=K.NoModifier, n=1):
    for _ in range(n):
        QTest.keyClick(ed, key, mods)


def _same(got, want):
    """1 文字ずつ比べ、最初に違う所を言う。"""
    assert len(want) > 0
    for i, (a, b) in enumerate(zip(got, want)):
        assert a == b, "位置 %d で違う: %r != %r\n got=%r\nwant=%r" % (i, a, b, got, want)
    assert len(got) == len(want), "長さが違う\n got=%r\nwant=%r" % (got, want)


def _vp_point(ed, line, col):
    """``line`` 行の文字の位置 ``col`` の左端(ビューポートの座標)。"""
    blk = ed.document().findBlockByNumber(line)
    cur = QtGui.QTextCursor(ed.document())
    cur.setPosition(blk.position() + eo.cp_to_u16(blk.text(), col))
    r = ed.cursorRect(cur)
    return QtCore.QPoint(r.x(), r.center().y())


def _mouse(ed, etype, pos, button, buttons, mods):
    vp = ed.viewport()
    ev = QtGui.QMouseEvent(etype, QtCore.QPointF(pos), QtCore.QPointF(vp.mapToGlobal(pos)), button, buttons, mods)
    QtWidgets.QApplication.sendEvent(vp, ev)


def _drag(ed, p0, p1, mods=K.AltModifier):
    _mouse(ed, QtCore.QEvent.MouseButtonPress, p0, K.LeftButton, K.LeftButton, mods)
    mid = QtCore.QPoint((p0.x() + p1.x()) // 2, (p0.y() + p1.y()) // 2)
    for p in (mid, p1):
        _mouse(ed, QtCore.QEvent.MouseMove, p, K.NoButton, K.LeftButton, mods)
    _mouse(ed, QtCore.QEvent.MouseButtonRelease, p1, K.LeftButton, K.NoButton, mods)


def _box_selection_count(ed, ops):
    """今出ている ``ExtraSelection`` のうち、箱の印(選びの色の物)の数。"""
    bg = ops.colors()["sel_bg"]
    return sum(1 for s in ed.extraSelections()
               if s.cursor.hasSelection() and s.format.background().color() == bg)


TEXT = "abc def\nab\n\nabcdefgh\nxyz 12345"


# --------------------------------------------------------------------------- #
# 取り付けていないエディタは何も変わらない
# --------------------------------------------------------------------------- #
def _drive_defaults(ed):
    _goto(ed, 0, 2)
    _key(ed, K.Key_Tab)
    _key(ed, K.Key_Down, SA)
    _key(ed, K.Key_D, K.ControlModifier)
    _key(ed, K.Key_Up, K.AltModifier)
    _key(ed, K.Key_K, K.ControlModifier | K.ShiftModifier)
    QTest.keyClicks(ed, "Q")
    return ed.toPlainText()


def test_an_editor_without_install_keeps_the_stock_behaviour(app):
    ed = _show(QtWidgets.QPlainTextEdit(), TEXT)
    _KEEP.append(ed)
    got = _drive_defaults(ed)
    assert got.startswith("ab\tQc def\n"), got             # Tab は素のタブ文字、他のキーは何も編集しない
    assert got.count("\n") == TEXT.count("\n")
    assert eq.get(ed) is None and "setExtraSelections" not in vars(ed)
    assert [c for c in ed.children() if c.objectName() == "editopsOverlay"] == []


def test_install_then_uninstall_gives_back_exactly_the_stock_behaviour(app):
    ref = _drive_defaults(_show(QtWidgets.QPlainTextEdit(), TEXT))
    ed, ops, _clip = _plain(app, TEXT)
    width = ed.cursorWidth()
    _goto(ed, 0, 2)
    _key(ed, K.Key_Down, SA, 3)
    assert ops.active() and ed.cursorWidth() == 0
    assert eq.uninstall(ed) is True and eq.uninstall(ed) is False
    _pump(0.05)
    assert ed.cursorWidth() == width and ed.extraSelections() == []
    assert "setExtraSelections" not in vars(ed) and "createStandardContextMenu" not in vars(ed)
    assert [c for c in ed.children() if c.objectName() == "editopsOverlay" and c.isVisible()] == []
    ed.setPlainText(TEXT)
    _same(_drive_defaults(ed), ref)


def test_install_twice_returns_the_same_object(app):
    ed, ops, _clip = _plain(app, TEXT)
    assert eq.install(ed) is ops and eq.get(ed) is ops
    assert len([c for c in ed.children() if isinstance(c, eq.EditOps)]) == 1


# --------------------------------------------------------------------------- #
# キーで箱を作って編集する
# --------------------------------------------------------------------------- #
def test_shift_alt_arrows_make_a_box_and_typing_goes_to_every_line(app):
    ed, ops, _clip = _plain(app, TEXT)
    said = []
    ops.on_message = said.append
    _goto(ed, 0, 2)
    _key(ed, K.Key_Down, SA, 4)
    _key(ed, K.Key_Right, SA, 3)
    assert ops.box() == (0, 2, 4, 5)
    assert said == ["box: 2 lines", "box: 3 lines", "box: 4 lines"]    # 状態行: 空行は届かないので 4 行
    assert ops.carets() == [eo.Caret(0, 2, 5), eo.Caret(1, 2, 2), eo.Caret(3, 2, 5), eo.Caret(4, 2, 5)]
    assert ops.selected_texts() == ["c d", "", "cde", "z 1"]
    assert _box_selection_count(ed, ops) == 3                      # 幅のある 3 行が ExtraSelection で見える
    QTest.keyClicks(ed, "X")
    want = "abXef\nabX\n\nabXfgh\nxyX2345"
    _same(ed.toPlainText(), want)
    assert ops.carets() == [eo.Caret(0, 3, 3), eo.Caret(1, 3, 3), eo.Caret(3, 3, 3), eo.Caret(4, 3, 3)]
    ed.undo()
    _same(ed.toPlainText(), TEXT)                                  # 1 回の Undo で全部の行が戻る
    assert not ed.document().isUndoAvailable()
    ed.redo()
    _same(ed.toPlainText(), want)


def test_a_zero_width_box_is_a_cursor_on_every_line_and_each_key_is_one_undo(app):
    ed, ops, _clip = _plain(app, "aaa\nbbb\nccc")
    _goto(ed, 0, 1)
    _key(ed, K.Key_Down, SA, 2)
    assert [c.empty for c in ops.carets()] == [True, True, True] and _box_selection_count(ed, ops) == 0
    assert len(ops.caret_rects()) == 3
    QTest.keyClicks(ed, "12")
    _same(ed.toPlainText(), "a12aa\nb12bb\nc12cc")
    ed.undo()
    _same(ed.toPlainText(), "a1aa\nb1bb\nc1cc")
    ed.undo()
    _same(ed.toPlainText(), "aaa\nbbb\nccc")
    ed.redo()
    ed.redo()
    _same(ed.toPlainText(), "a12aa\nb12bb\nc12cc")


def test_delete_and_backspace_on_a_box(app):
    ed, ops, _clip = _plain(app, TEXT)
    ops.set_box(0, 1, 4, 3)
    _key(ed, K.Key_Delete)
    _same(ed.toPlainText(), "a def\na\n\nadefgh\nx 12345")
    ed.undo()
    _same(ed.toPlainText(), TEXT)
    ops.set_box(3, 2, 4, 2)                                        # 幅 0: Backspace は左の 1 文字、Delete は右の 1 文字
    _key(ed, K.Key_Backspace)
    _same(ed.toPlainText(), "abc def\nab\n\nacdefgh\nxz 12345")
    _key(ed, K.Key_Delete)
    _same(ed.toPlainText(), "abc def\nab\n\nadefgh\nx 12345")
    ed.undo()
    ed.undo()
    _same(ed.toPlainText(), TEXT)


def test_copy_joins_the_rows_and_cut_removes_them(app):
    ed, ops, clip = _plain(app, TEXT)
    ops.set_box(0, 0, 4, 2)
    _key(ed, K.Key_C, K.ControlModifier)
    assert clip.text() == "ab\nab\n\nab\nxy" and clip.sets == 1
    _same(ed.toPlainText(), TEXT)
    assert ops.active()                                             # コピーしても箱は残る
    _key(ed, K.Key_X, K.ControlModifier)
    assert clip.sets == 2
    _same(ed.toPlainText(), "c def\n\n\ncdefgh\nz 12345")
    ed.undo()
    _same(ed.toPlainText(), TEXT)


def test_paste_goes_row_by_row_when_the_row_counts_match(app):
    ed, ops, clip = _plain(app, "a=\nb=\nc=")
    clip.setText("1\n22\n333")
    ops.set_box(0, 2, 2, 2)
    _key(ed, K.Key_V, K.ControlModifier)
    _same(ed.toPlainText(), "a=1\nb=22\nc=333")
    assert ops.carets() == [eo.Caret(0, 3, 3), eo.Caret(1, 4, 4), eo.Caret(2, 5, 5)]
    ed.undo()
    _same(ed.toPlainText(), "a=\nb=\nc=")
    ed.redo()
    _same(ed.toPlainText(), "a=1\nb=22\nc=333")


def test_paste_of_one_line_goes_to_every_row_and_other_shapes_are_pasted_whole(app):
    ed, ops, clip = _plain(app, "a\nb\nc")
    clip.setText("#")
    ops.set_box(0, 0, 2, 0)
    assert ops.paste() == "same"
    _same(ed.toPlainText(), "#a\n#b\n#c")
    ed.undo()
    clip.setText("1\n2")                                            # 2 行を 3 つのカーソルへ: 各々に丸ごと
    ops.set_box(0, 1, 2, 1)
    assert ops.paste() == "full"
    _same(ed.toPlainText(), "a1\n2\nb1\n2\nc1\n2")
    assert not ops.active()
    ed.undo()
    _same(ed.toPlainText(), "a\nb\nc")


def test_tab_indents_the_box_lines_and_shift_tab_takes_it_back(app):
    ed, ops, _clip = _plain(app, "if x:\na = 1\n\nb = 2")
    ops.set_box(1, 0, 3, 1)
    _key(ed, K.Key_Tab)
    _same(ed.toPlainText(), "if x:\n    a = 1\n\n    b = 2")
    assert ops.selected_texts() == ["a", "", "b"]                   # 箱は字と一緒に右へ動く(空行は字下げしない)
    _key(ed, K.Key_Backtab, K.ShiftModifier)
    _same(ed.toPlainText(), "if x:\na = 1\n\nb = 2")
    ed.undo()
    _same(ed.toPlainText(), "if x:\n    a = 1\n\n    b = 2")
    ed.undo()
    _same(ed.toPlainText(), "if x:\na = 1\n\nb = 2")


def test_tab_on_a_zero_width_box_fills_to_the_next_stop_on_every_line(app):
    ed, ops, _clip = _plain(app, "ab=1\nabc=2\na=3")
    ops.set_box(0, 2, 2, 2)                                         # "a=3" は桁 2 が = の後ろ
    _key(ed, K.Key_Tab)
    _same(ed.toPlainText(), "ab  =1\nab  c=2\na=  3")


def test_escape_and_a_plain_click_end_the_box_but_a_right_click_does_not(app):
    ed, ops, _clip = _plain(app, TEXT)
    ops.set_box(0, 1, 3, 4)
    assert ops.active() and ed.cursorWidth() == 0
    _key(ed, K.Key_Escape)
    assert not ops.active() and ed.cursorWidth() >= 1 and _box_selection_count(ed, ops) == 0
    assert ed.textCursor().selectedText() == "bcd"                  # 主のカーソル(動く角の行)の選びが残る
    ops.set_box(0, 1, 3, 4)
    p = _vp_point(ed, 4, 3)
    QTest.mouseClick(ed.viewport(), K.RightButton, K.NoModifier, p)
    assert ops.active()
    QTest.mouseClick(ed.viewport(), K.LeftButton, K.NoModifier, p)
    assert not ops.active()
    assert ed.textCursor().blockNumber() == 4 and not ed.textCursor().hasSelection()


def test_left_right_home_end_move_every_cursor_and_other_keys_fall_back_to_one_cursor(app):
    ed, ops, _clip = _plain(app, "  abc\n  de\n  f")
    ops.set_box(0, 3, 2, 3)
    _key(ed, K.Key_End)
    assert ops.carets() == [eo.Caret(0, 5, 5), eo.Caret(1, 4, 4), eo.Caret(2, 3, 3)]
    QTest.keyClicks(ed, ";")
    _same(ed.toPlainText(), "  abc;\n  de;\n  f;")
    _key(ed, K.Key_Home)
    assert [c.pos for c in ops.carets()] == [2, 2, 2]
    _key(ed, K.Key_Right, K.ShiftModifier)
    assert ops.selected_texts() == ["a", "d", "f"]
    _key(ed, K.Key_Left)
    assert [c.pos for c in ops.carets()] == [2, 2, 2] and ops.active()
    _key(ed, K.Key_Z, K.ControlModifier)                            # Undo は元の動作(箱はやめる)
    assert not ops.active()
    _same(ed.toPlainText(), "  abc\n  de\n  f")


def test_ctrl_alt_down_adds_a_cursor_below(app):
    ed, ops, _clip = _plain(app, "aaa\nbbb\nccc")
    _goto(ed, 0, 3)
    _key(ed, K.Key_Down, K.ControlModifier | K.AltModifier, 2)
    assert ops.carets() == [eo.Caret(0, 3, 3), eo.Caret(1, 3, 3), eo.Caret(2, 3, 3)]
    QTest.keyClicks(ed, ",")
    _same(ed.toPlainText(), "aaa,\nbbb,\nccc,")


def test_shrinking_the_box_back_past_its_start(app):
    ed, ops, _clip = _plain(app, TEXT)
    _goto(ed, 3, 4)
    _key(ed, K.Key_Up, SA, 3)
    _key(ed, K.Key_Left, SA, 2)
    assert ops.box() == (3, 4, 0, 2)
    assert ops.selected_texts() == ["c ", "", "cd"]                 # 空行は左端に届かないので入らない
    _key(ed, K.Key_Down, SA, 3)
    assert ops.box() == (3, 4, 3, 2) and ops.selected_texts() == ["cd"]


def test_a_change_from_outside_drops_the_box(app):
    ed, ops, _clip = _plain(app, TEXT)
    ops.set_box(0, 1, 4, 3)
    ed.setPlainText("new text")
    assert not ops.active() and ed.cursorWidth() >= 1
    QTest.keyClicks(ed, "z")
    _same(ed.toPlainText(), "znew text")


def test_a_read_only_editor_is_not_edited(app):
    ed, ops, _clip = _plain(app, TEXT)
    ed.setReadOnly(True)
    ops.set_box(0, 0, 4, 2)
    QTest.keyClicks(ed, "X")
    _key(ed, K.Key_Delete)
    _key(ed, K.Key_Escape)
    for cmd in ("line.duplicate", "line.delete", "line.move_down", "line.comment", "line.indent", "edit.trim"):
        ops.run(cmd)
    _same(ed.toPlainText(), TEXT)
    with pytest.raises(ValueError):
        ops.run("no.such.command")


# --------------------------------------------------------------------------- #
# 全角・タブ・絵文字・結合文字
# --------------------------------------------------------------------------- #
JA = "x = 1      # 日本語のコメント\nyy = 22    # 二行目の説明\nzzz = 333  # ｶﾀｶﾅ と ABC"


def test_box_over_japanese_comments_uses_display_columns(app):
    ed, ops, _clip = _plain(app, JA)
    ops.set_box(0, 13, 2, 17)                                       # コメントの先頭から 4 桁 = 全角 2 文字
    assert ops.selected_texts() == ["日本", "二行", "ｶﾀｶﾅ"]
    QTest.keyClicks(ed, "@")
    want = "x = 1      # @語のコメント\nyy = 22    # @目の説明\nzzz = 333  # @ と ABC"
    _same(ed.toPlainText(), want)
    ed.undo()
    _same(ed.toPlainText(), JA)
    ed.redo()
    _same(ed.toPlainText(), want)


def test_typing_japanese_into_a_box_keeps_the_columns(app):
    ed, ops, _clip = _plain(app, JA)
    ops.set_box(0, 11, 2, 11)
    ops.insert_text("注")
    _same(ed.toPlainText(), JA.replace("# ", "注# "))
    QTest.keyClicks(ed, "!")
    _same(ed.toPlainText(), JA.replace("# ", "注!# "))
    assert ops.box() == (0, 14, 2, 14)                              # 注 は 2 桁、! は 1 桁


@pytest.mark.parametrize("wide,texts", [(True, ["a", "e"]), (False, ["c", "e"])])
def test_ambiguous_width_characters_follow_the_font(app, wide, texts):
    """※ ○ → などは書体で幅が変わる。全角に出る書体なら 2 桁、半角に出る書体なら 1 桁として箱を取る。"""
    ed, ops, _clip = _plain(app, "※→abc\nabcdef", ambiguous_wide=wide)
    ops.set_box(0, 4, 1, 5)
    assert ops.selected_texts() == texts
    measured = eq.install(_show(QtWidgets.QPlainTextEdit(), "x"))   # 指定しなければ、今の書体で測る
    _KEEP.append(measured.editor)
    fm = QtGui.QFontMetricsF(measured.editor.font())
    assert measured._is_wide("※") == (fm.horizontalAdvance("※") > 1.5 * fm.horizontalAdvance("0"))


def test_box_edges_inside_a_full_width_character_snap_instead_of_splitting(app):
    ed, ops, _clip = _plain(app, "日本語\nabcdef\n漢字かな")
    ops.set_box(0, 1, 2, 3)                                         # 両端が全角の真ん中
    assert ops.selected_texts() == ["日", "bc", "漢"]
    _key(ed, K.Key_Delete)
    _same(ed.toPlainText(), "本語\nadef\n字かな")


def test_emoji_outside_the_bmp_do_not_shift_the_positions(app):
    text = "a😀bcd\n😀😀xyz\nabcdef\n" + FAMILY + "pqr"
    ed, ops, _clip = _plain(app, text)
    ops.set_box(0, 3, 3, 4)
    assert ops.selected_texts() == ["b", "😀", "d", "q"]            # 2 行目: 桁 3 は絵文字の真ん中 → 左の境目(桁 2)へ
    QTest.keyClicks(ed, "#")
    want = "a😀#cd\n😀#xyz\nabc#ef\n" + FAMILY + "p#r"
    _same(ed.toPlainText(), want)
    ed.undo()
    _same(ed.toPlainText(), text)
    ops.set_box(0, 1, 3, 1)                                         # 絵文字・結合の列の手前に幅 0 のカーソル
    _key(ed, K.Key_Delete)
    _same(ed.toPlainText(), "abcd\n😀xyz\nacdef\npqr")           # 家族の絵文字(5 文字ぶん)も 1 つとして消える


def test_combining_marks_stay_with_their_base_character(app):
    text = "ae\u0301z\nabcd\nか\u3099きく"
    ed, ops, _clip = _plain(app, text)
    ops.set_box(0, 1, 2, 2)
    assert ops.selected_texts() == ["e\u0301", "b", "か\u3099"]     # 3 行目: 桁 1 は「が」の真ん中 → 左、桁 2 は境目
    ops.set_box(0, 2, 2, 2)
    _key(ed, K.Key_Backspace)
    _same(ed.toPlainText(), "az\nacd\nきく")


def test_tabs_in_the_text_count_to_the_next_tab_stop(app):
    text = "a\tb\tc\n1234\t5678\nxxxxxxxxxxxx"
    ed, ops, _clip = _plain(app, text)
    ops.set_box(0, 4, 2, 5)
    assert ops.selected_texts() == ["b", "", "x"]                   # 2 行目: 桁 5 はタブ(桁 4〜8)の途中 → 左の境目
    QTest.keyClicks(ed, "Q")
    _same(ed.toPlainText(), "a\tQ\tc\n1234Q\t5678\nxxxxQxxxxxxx")
    QTest.keyClicks(ed, "R")                                        # 続けて打っても、打った物の直後に入る
    _same(ed.toPlainText(), "a\tQR\tc\n1234QR\t5678\nxxxxQRxxxxxxx")


def test_lines_shorter_than_the_box_are_left_out_and_not_padded(app):
    ed, ops, _clip = _plain(app, "abcdefgh\nab\n\nabcdefgh")
    ops.set_box(0, 5, 3, 7)
    assert [c.line for c in ops.carets()] == [0, 3]
    QTest.keyClicks(ed, "_")
    _same(ed.toPlainText(), "abcde_h\nab\n\nabcde_h")              # 短い行は空白で埋めない
    ops.clear()
    ed.setPlainText("ab\nc\n")
    ops.set_box(0, 9, 2, 9)                                         # どの行も届かない: 全部の行末にカーソル
    QTest.keyClicks(ed, ";")
    _same(ed.toPlainText(), "ab;\nc;\n;")


def test_crlf_text_loads_as_plain_lines(app):
    ed, ops, _clip = _plain(app, "abcd\r\nefgh\r\nijkl")
    assert ed.document().blockCount() == 3
    ops.set_box(0, 1, 2, 3)
    assert ops.selected_texts() == ["bc", "fg", "jk"]
    QTest.keyClicks(ed, "-")
    _same(ed.toPlainText(), "a-d\ne-h\ni-l")


# --------------------------------------------------------------------------- #
# マウス
# --------------------------------------------------------------------------- #
def test_alt_drag_selects_a_box(app):
    ed, ops, _clip = _plain(app, TEXT)
    _drag(ed, _vp_point(ed, 0, 1), _vp_point(ed, 4, 4))
    assert ops.box() == (0, 1, 4, 4)
    assert ops.selected_texts() == ["bc ", "b", "bcd", "yz "]
    assert _box_selection_count(ed, ops) == 4
    QTest.keyClicks(ed, "|")
    _same(ed.toPlainText(), "a|def\na|\n\na|efgh\nx|12345")


def test_alt_drag_past_the_end_of_a_line_counts_columns_by_the_character_width(app):
    ed, ops, _clip = _plain(app, "ab\nabcdefghij\nabcdefghij")
    w = ops.char_advance()
    p0 = _vp_point(ed, 0, 2)
    p0 = QtCore.QPoint(int(round(p0.x() + 4 * w)), p0.y())          # 1 行目の行末より 4 桁右
    _drag(ed, p0, _vp_point(ed, 2, 8))
    assert ops.box() == (0, 6, 2, 8)
    assert ops.selected_texts() == ["gh", "gh"]                     # 1 行目は届かないので入らない


def test_alt_drag_over_japanese_text(app):
    ed, ops, _clip = _plain(app, JA)
    _drag(ed, _vp_point(ed, 0, 13), _vp_point(ed, 2, 15))           # 3 行目の位置 15 = ｶﾀ の後ろ = 桁 15
    assert ops.box() == (0, 13, 2, 15)
    assert ops.selected_texts() == ["日", "二", "ｶﾀ"]


def test_shift_alt_click_makes_a_box_from_the_cursor(app):
    ed, ops, _clip = _plain(app, TEXT)
    _goto(ed, 0, 1)
    p = _vp_point(ed, 3, 5)
    _mouse(ed, QtCore.QEvent.MouseButtonPress, p, K.LeftButton, K.LeftButton, SA)
    _mouse(ed, QtCore.QEvent.MouseButtonRelease, p, K.LeftButton, K.NoButton, SA)
    assert ops.box() == (0, 1, 3, 5)
    p = _vp_point(ed, 4, 3)                                         # もう一度: 固定の角はそのまま
    _mouse(ed, QtCore.QEvent.MouseButtonPress, p, K.LeftButton, K.LeftButton, SA)
    _mouse(ed, QtCore.QEvent.MouseButtonRelease, p, K.LeftButton, K.NoButton, SA)
    assert ops.box() == (0, 1, 4, 3)
    assert ops.selected_texts() == ["bc", "b", "bc", "yz"]


def test_a_mouse_move_without_the_button_does_not_keep_dragging(app):
    ed, ops, _clip = _plain(app, TEXT)
    p0, p1 = _vp_point(ed, 0, 1), _vp_point(ed, 3, 3)
    _mouse(ed, QtCore.QEvent.MouseButtonPress, p0, K.LeftButton, K.LeftButton, K.AltModifier)
    _mouse(ed, QtCore.QEvent.MouseMove, p1, K.NoButton, K.NoButton, K.AltModifier)     # 離した合図を取りこぼした後
    assert ops.box() == (0, 1, 0, 1)


# --------------------------------------------------------------------------- #
# IME(確定の時だけ全部の行へ)
# --------------------------------------------------------------------------- #
def test_ime_preedit_touches_nothing_and_the_commit_goes_to_every_line(app):
    ed, ops, _clip = _plain(app, "a = \nbb = \nccc = ")
    ops.set_box(0, 2, 2, 2)
    assert len(ops.carets()) == 3
    QtWidgets.QApplication.sendEvent(ed, QtGui.QInputMethodEvent("にほん", []))
    _same(ed.toPlainText(), "a = \nbb = \nccc = ")                 # 未確定の間は文面を変えない
    preedit = [ed.document().findBlockByNumber(i).layout().preeditAreaText() for i in range(3)]
    assert preedit.count("にほん") == 1
    commit = QtGui.QInputMethodEvent()
    commit.setCommitString("日本")
    QtWidgets.QApplication.sendEvent(ed, commit)
    _same(ed.toPlainText(), "a 日本= \nbb日本 = \ncc日本c = ")
    preedit = [ed.document().findBlockByNumber(i).layout().preeditAreaText() for i in range(3)]
    assert preedit == ["", "", ""]
    assert ops.box() == (0, 6, 2, 6)
    ed.undo()
    _same(ed.toPlainText(), "a = \nbb = \nccc = ")                 # 確定 1 回 = Undo 1 回
    assert not ed.document().isUndoAvailable()


def test_ime_without_a_box_is_left_to_the_editor(app):
    ed, ops, _clip = _plain(app, "ab")
    _goto(ed, 0, 1)
    commit = QtGui.QInputMethodEvent()
    commit.setCommitString("漢")
    QtWidgets.QApplication.sendEvent(ed, commit)
    _same(ed.toPlainText(), "a漢b")
    assert not ops.active()


# --------------------------------------------------------------------------- #
# 行の操作(カーソル 1 つ)
# --------------------------------------------------------------------------- #
CODE = "def f(a):\n    x = [1, (2)]\n    return x\nprint(f(0))"


def test_ctrl_d_duplicates_the_line_and_the_cursor_goes_to_the_copy(app):
    ed, ops, _clip = _plain(app, CODE)
    _goto(ed, 1, 6)
    _key(ed, K.Key_D, K.ControlModifier)
    _same(ed.toPlainText(), "def f(a):\n    x = [1, (2)]\n    x = [1, (2)]\n    return x\nprint(f(0))")
    cur = ed.textCursor()
    assert (cur.blockNumber(), cur.positionInBlock()) == (2, 6)
    ed.undo()
    _same(ed.toPlainText(), CODE)
    assert not ed.document().isUndoAvailable()
    ed.redo()
    assert ed.toPlainText().count("x = [1, (2)]") == 2


def test_ctrl_d_duplicates_every_selected_line_including_the_last_line_of_the_document(app):
    ed, ops, _clip = _plain(app, "a\nb\nc")
    cur = ed.textCursor()
    cur.setPosition(2)
    cur.setPosition(5, QtGui.QTextCursor.KeepAnchor)               # b の先頭から c の後ろまで
    ed.setTextCursor(cur)
    _key(ed, K.Key_D, K.ControlModifier)
    _same(ed.toPlainText(), "a\nb\nc\nb\nc")
    assert ed.textCursor().selectedText().replace("\u2029", "\n") == "b\nc"
    assert ed.textCursor().selectionStart() == 6


def test_alt_up_and_down_move_the_line_with_the_cursor(app):
    ed, ops, _clip = _plain(app, "one\ntwo\nthree\nfour")
    _goto(ed, 1, 2)
    _key(ed, K.Key_Down, K.AltModifier)
    _same(ed.toPlainText(), "one\nthree\ntwo\nfour")
    assert (ed.textCursor().blockNumber(), ed.textCursor().positionInBlock()) == (2, 2)
    _key(ed, K.Key_Down, K.AltModifier, 3)                          # 末尾で止まる
    _same(ed.toPlainText(), "one\nthree\nfour\ntwo")
    _key(ed, K.Key_Up, K.AltModifier, 5)                            # 先頭で止まる
    _same(ed.toPlainText(), "two\none\nthree\nfour")
    assert (ed.textCursor().blockNumber(), ed.textCursor().positionInBlock()) == (0, 2)
    ed.undo()
    _same(ed.toPlainText(), "one\ntwo\nthree\nfour")                # 上へ 1 回ぶんだけ戻る


def test_alt_down_moves_a_block_of_selected_lines(app):
    ed, ops, _clip = _plain(app, "a\nb\nc\nd")
    cur = ed.textCursor()
    cur.setPosition(0)
    cur.setPosition(3, QtGui.QTextCursor.KeepAnchor)               # a と b
    ed.setTextCursor(cur)
    _key(ed, K.Key_Down, K.AltModifier)
    _same(ed.toPlainText(), "c\na\nb\nd")
    assert ed.textCursor().selectedText().replace("\u2029", "\n") == "a\nb"


def test_ctrl_shift_k_deletes_lines_in_the_middle_at_the_end_and_the_only_line(app):
    ed, ops, _clip = _plain(app, "a\nb\nc")
    _goto(ed, 1, 1)
    _key(ed, K.Key_K, K.ControlModifier | K.ShiftModifier)
    _same(ed.toPlainText(), "a\nc")
    assert ed.textCursor().blockNumber() == 1
    _key(ed, K.Key_K, K.ControlModifier | K.ShiftModifier)          # 最後の行
    _same(ed.toPlainText(), "a")
    ed.undo()
    ed.undo()
    _same(ed.toPlainText(), "a\nb\nc")
    ed.setPlainText("only")
    _key(ed, K.Key_K, K.ControlModifier | K.ShiftModifier)
    assert ed.toPlainText() == ""


def test_tab_and_shift_tab_indent_the_selected_lines_and_plain_tab_goes_to_the_next_stop(app):
    ed, ops, _clip = _plain(app, "a\nb\n\nc")
    ed.selectAll()
    _key(ed, K.Key_Tab)
    _same(ed.toPlainText(), "    a\n    b\n\n    c")
    assert ed.textCursor().hasSelection()
    _key(ed, K.Key_Backtab, K.ShiftModifier)
    _same(ed.toPlainText(), "a\nb\n\nc")
    ed.undo()
    ed.undo()
    _same(ed.toPlainText(), "a\nb\n\nc")
    _goto(ed, 0, 1)
    _key(ed, K.Key_Tab)                                             # 選びなし: 次の 4 桁の位置まで空白
    _same(ed.toPlainText(), "a   \nb\n\nc")
    assert "\t" not in ed.toPlainText()
    _key(ed, K.Key_Backtab, K.ShiftModifier)                        # 選びなしの Shift+Tab: その行の字下げを戻す(無ければ何もしない)
    _same(ed.toPlainText(), "a   \nb\n\nc")


def test_ctrl_slash_comments_on_an_editor_that_has_no_comment_key_of_its_own(app):
    ed, ops, _clip = _plain(app, CODE)
    cur = ed.textCursor()
    cur.setPosition(ed.document().findBlockByNumber(1).position())
    cur.setPosition(ed.document().findBlockByNumber(2).position() + 3, QtGui.QTextCursor.KeepAnchor)
    ed.setTextCursor(cur)
    _key(ed, K.Key_Slash, K.ControlModifier)
    _same(ed.toPlainText(), "def f(a):\n    # x = [1, (2)]\n    # return x\nprint(f(0))")
    _key(ed, K.Key_Slash, K.ControlModifier)
    _same(ed.toPlainText(), CODE)
    ed.undo()
    assert ed.toPlainText().count("# ") == 2


def test_ctrl_bracket_jumps_to_the_partner_and_back_and_the_pair_is_highlighted(app):
    ed, ops, _clip = _plain(app, CODE)
    _goto(ed, 1, 8)                                                 # [ の手前
    _pump(0.02)
    marked = sorted(s.cursor.selectedText() for s in ed.extraSelections() if s.cursor.hasSelection())
    assert marked == ["[", "]"]
    _key(ed, K.Key_BracketRight, K.ControlModifier)
    assert (ed.textCursor().blockNumber(), ed.textCursor().positionInBlock()) == (1, 15)
    _key(ed, K.Key_BracketRight, K.ControlModifier)
    assert (ed.textCursor().blockNumber(), ed.textCursor().positionInBlock()) == (1, 8)
    said = []
    ops.on_message = said.append
    _goto(ed, 2, 6)
    _key(ed, K.Key_BracketRight, K.ControlModifier)
    assert said == ["no matching bracket"]
    assert (ed.textCursor().blockNumber(), ed.textCursor().positionInBlock()) == (2, 6)


def test_shift_alt_period_selects_the_word_then_adds_the_next_occurrences(app):
    ed, ops, _clip = _plain(app, "x = xx + x\ny = x\nx")
    _goto(ed, 0, 0)
    _key(ed, K.Key_Greater, SA)                                     # Shift を押した . は > として届く
    assert ed.textCursor().selectedText() == "x" and not ops.active()
    _key(ed, K.Key_Greater, SA)
    assert ops.carets() == [eo.Caret(0, 0, 1), eo.Caret(0, 9, 10)]  # 語として一致する物だけ(xx は飛ばす)
    _key(ed, K.Key_Period, SA)
    _key(ed, K.Key_Period, SA)
    assert len(ops.carets()) == 4
    said = []
    ops.on_message = said.append
    _key(ed, K.Key_Period, SA)                                      # もう無い
    assert len(ops.carets()) == 4 and said == ["no other occurrence"]
    QTest.keyClicks(ed, "val")
    _same(ed.toPlainText(), "val = xx + val\ny = val\nval")
    ed.undo()
    ed.undo()
    ed.undo()
    _same(ed.toPlainText(), "x = xx + x\ny = x\nx")


def test_trim_trailing_whitespace_is_one_undo_and_trim_on_save_is_off_by_default(app):
    text = "a  \nb\t\nc\n   "
    ed, ops, _clip = _plain(app, text)
    assert ops.trim_on_save is False and ops.before_save() == 0
    _same(ed.toPlainText(), text)
    assert ops.trim_trailing() == 3
    _same(ed.toPlainText(), "a\nb\nc\n")
    ed.undo()
    _same(ed.toPlainText(), text)
    ops.set_trim_on_save(True)
    assert ops.before_save() == 3
    _same(ed.toPlainText(), "a\nb\nc\n")


# --------------------------------------------------------------------------- #
# 見た目: 桁の目安の線・カーソル・設定
# --------------------------------------------------------------------------- #
def test_the_overlay_covers_the_viewport_and_lets_the_mouse_through(app):
    ed, ops, _clip = _plain(app, TEXT)
    _pump(0.05)
    ov = [c for c in ed.children() if c.objectName() == "editopsOverlay"]
    assert len(ov) == 1
    assert ov[0].geometry() == ed.viewport().geometry() and ov[0].isVisible()
    assert ov[0].testAttribute(K.WA_TransparentForMouseEvents)
    center = ed.viewport().geometry().center()
    assert ed.childAt(center) is ed.viewport()                      # マウスは下のビューポートへ届く
    ed.resize(500, 300)
    _pump(0.05)
    assert ov[0].geometry() == ed.viewport().geometry()


def test_rulers_are_drawn_at_79_and_99_columns_and_can_be_switched_off(app):
    ed, ops, _clip = _plain(app, "x" * 120)
    ed.resize(1100, 200)
    _pump(0.05)
    assert ops.rulers == (79, 99)
    w = ops.char_advance()
    assert abs((ops.ruler_x(99) - ops.ruler_x(79)) - 20 * w) < 1e-6
    blk = ed.document().findBlockByNumber(0)
    cur = QtGui.QTextCursor(blk)
    cur.setPosition(79)
    assert abs(ed.cursorRect(cur).x() - ops.ruler_x(79)) <= 1.5     # 線は 79 文字目の右の境目に重なる
    x = int(round(ops.ruler_x(79)))
    y = ed.viewport().height() - 6                                  # 文字の無い下の方
    off = ed.viewport().geometry().topLeft()
    with_line = ed.grab().toImage().pixelColor(off.x() + x, off.y() + y)
    ops.set_rulers(())
    _pump(0.05)
    without = ed.grab().toImage().pixelColor(off.x() + x, off.y() + y)
    assert with_line != without, "線が描かれていない"
    assert ops.rulers == ()


def test_every_cursor_of_a_zero_width_box_is_painted(app):
    ed, ops, _clip = _plain(app, "aaaa\nbbbb\ncccc")
    ops.set_rulers(())
    ops.set_box(0, 2, 2, 2)
    _pump(0.05)
    rects = ops.caret_rects()
    assert len(rects) == 3
    img = ed.grab().toImage()
    off = ed.viewport().geometry().topLeft()
    fg = ops.colors()["fg"]
    hits = [img.pixelColor(off.x() + r.x(), off.y() + r.center().y()) == fg for r in rects]
    assert hits == [True, True, True], hits


def test_settings_are_remembered_in_the_settings_object_that_was_passed(app, tmp_path):
    ini = QtCore.QSettings(str(tmp_path / "editops.ini"), QtCore.QSettings.IniFormat)
    ed, ops, _clip = _plain(app, TEXT, settings=lambda: ini)
    assert ops.rulers == (79, 99) and ops.trim_on_save is False     # 既定
    ops.set_rulers(())
    ops.set_trim_on_save(True)
    ini.sync()
    again = QtCore.QSettings(str(tmp_path / "editops.ini"), QtCore.QSettings.IniFormat)
    ed2, ops2, _clip2 = _plain(app, TEXT, settings=lambda: again)
    assert ops2.rulers == () and ops2.trim_on_save is True
    ops2.set_rulers((79, 99))
    assert again.value("editops/rulers") == "79,99"


# --------------------------------------------------------------------------- #
# メニュー(入口はキーだけにしない)と 6 言語
# --------------------------------------------------------------------------- #
def _menu_rows(menu):
    """``{サブメニューの名前: [(項目の名前, 文)]}``。"""
    out = {}
    for a in menu.actions():
        sub = a.menu()
        if sub is not None and sub.objectName().startswith("editops:"):
            out[sub.objectName()] = [(x.objectName(), x.text()) for x in sub.actions() if not x.isSeparator()]
    return out


def test_the_context_menu_has_the_three_groups_with_the_keys_shown(app):
    ed, ops, _clip = _plain(app, TEXT)
    menu = ops.build_context_menu()
    rows = _menu_rows(menu)
    assert sorted(rows) == ["editops:menu.box", "editops:menu.display", "editops:menu.line"]
    assert len(rows["editops:menu.box"]) == 6 and len(rows["editops:menu.line"]) == 9
    assert len(rows["editops:menu.display"]) == 2
    texts = dict(rows["editops:menu.box"] + rows["editops:menu.line"])
    assert texts["editops:line.duplicate"] == "Duplicate line\tCtrl+D"
    assert texts["editops:box.down"] == "Extend box selection down\tAlt+Shift+Down"
    assert texts["editops:howto"] == "How to use box selection…"
    standard = [a.text() for a in menu.actions() if a.menu() is None and not a.isSeparator()]
    assert len(standard) >= 5, standard                             # 元の項目(元に戻す・コピー・貼り付け …)は残る
    ops.set_box(0, 0, 2, 1)
    rows = _menu_rows(ops.build_context_menu())
    assert "editops:box.cancel" in dict(rows["editops:menu.box"])   # 箱がある間だけ「やめる」が出る


def test_menu_items_run_the_same_operations_as_the_keys(app):
    ed, ops, _clip = _plain(app, "a\nb")
    menu = ops.build_context_menu()
    acts = {x.objectName(): x for a in menu.actions() if a.menu() is not None for x in a.menu().actions()}
    acts["editops:line.duplicate"].trigger()
    _same(ed.toPlainText(), "a\na\nb")
    acts["editops:box.down"].trigger()
    assert ops.active() and len(ops.carets()) == 2
    acts["editops:rulers"].trigger()
    assert ops.rulers == ()
    acts["editops:trim_on_save"].trigger()
    assert ops.trim_on_save is True


def test_the_right_click_event_shows_our_menu_on_a_stock_editor(app):
    ed, ops, _clip = _plain(app, TEXT)
    seen = []
    orig = ops._show_context_menu
    ops._show_context_menu = lambda g, p: seen.append(_menu_rows(ops.build_context_menu(p)))
    try:
        p = _vp_point(ed, 1, 1)
        ev = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, p, ed.viewport().mapToGlobal(p))
        QtWidgets.QApplication.sendEvent(ed.viewport(), ev)
    finally:
        ops._show_context_menu = orig
    assert len(seen) == 1 and len(seen[0]) == 3


@pytest.mark.parametrize("lang", ["ja", "zh", "tw", "ko", "de"])
def test_menus_and_the_how_to_follow_the_language(app, lang):
    ed, ops, _clip = _plain(app, TEXT, tr=eo.make_tr(lang))
    ops.set_box(0, 0, 1, 1)
    rows = _menu_rows(ops.build_context_menu())
    table = eo.load_table()
    items = [t for group in rows.values() for _n, t in group]
    assert len(items) == 18
    english = {b.title for b in eo.KEYMAP} | {eo.ACT_HOWTO, eo.ACT_RULERS, eo.ACT_TRIM_ON_SAVE}
    left_in_english = [t for t in items if t.split("\t")[0] in english]
    assert left_in_english == []
    assert table[eo.KEYMAP[0].title][lang] + "\tAlt+Shift+Up" in items
    assert ops.howto_text() == table[eo.HOWTO_TEXT][lang] and "Alt" in ops.howto_text()
    acts = ops.command_actions()
    assert len(acts) == 16 and sorted(acts) == sorted(eo.PALETTE_WORDS)
    assert acts["editops_line_delete"].text() == table["Delete line"][lang]


def test_the_how_to_window_does_not_block_and_is_reused(app):
    ed, ops, _clip = _plain(app, TEXT, tr=eo.make_tr("ja"))
    box = ops.show_howto()
    _pump(0.05)
    assert box.isVisible() and not box.isModal() and box.windowTitle() == "矩形選択"
    assert "Alt + ドラッグ" in box.text()
    assert ops.show_howto() is box
    box.close()


# --------------------------------------------------------------------------- #
# Studio の本物のエディタの部品に取り付ける
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def studio_mod(app, tmp_path_factory):
    old = os.environ.get("FULLSEYE_STUDIO_SETTINGS")
    os.environ["FULLSEYE_STUDIO_SETTINGS"] = str(tmp_path_factory.mktemp("editops") / "studio.ini")
    import studio
    yield studio
    if old is None:
        os.environ.pop("FULLSEYE_STUDIO_SETTINGS", None)
    else:
        os.environ["FULLSEYE_STUDIO_SETTINGS"] = old


PIPE = "* note\nblur (0.5, 0.5)\notsu (0.5, 0.5)\nmedian (0.2, 0.2)"


def test_program_editor_keeps_its_gutter_marks_and_its_own_highlights(app, studio_mod):
    cls = studio_mod._program_editor_class(QtWidgets, QtGui, QtCore)
    ed = _show(cls(["blur", "otsu", "median", "gauss_filter", "gaussian"]), PIPE)
    _KEEP.append(ed)
    ed.breakpoints.add(2)
    ed.set_errors({3: "bad"})
    ed.set_exec_line(2)
    before = len(ed.extraSelections())
    assert before >= 3                                              # 今の行・実行中の行・エラーの波線
    width = ed.gutter_width()
    ops = eq.install(ed, clipboard=FakeClipboard())
    assert ops.comment_prefix == "*"
    ops.set_box(1, 6, 3, 9)
    assert ops.selected_texts() == ["0.5", "0.5", " (0"]
    ed._highlight()                                                 # 持ち主が印を付け直しても、箱の印は消えない
    assert _box_selection_count(ed, ops) == 3
    waves = [s for s in ed.extraSelections()
             if s.format.underlineStyle() == QtGui.QTextCharFormat.WaveUnderline]
    assert len(waves) == 1
    QTest.keyClicks(ed, "9")
    _same(ed.toPlainText(), "* note\nblur (9, 0.5)\notsu (9, 0.5)\nmedian9.2, 0.2)")
    ed.undo()
    _same(ed.toPlainText(), PIPE)
    assert ed.breakpoints == {2} and ed.errors() == {3: "bad"} and ed._exec_line == 2
    assert ed.gutter_width() == width and ed.viewportMargins().left() == width
    ops.clear()
    assert len(ed.extraSelections()) == before


def test_program_editor_keeps_its_own_keys_and_its_completion_popup(app, studio_mod):
    cls = studio_mod._program_editor_class(QtWidgets, QtGui, QtCore)
    ed = _show(cls(["blur", "otsu", "median", "gauss_filter", "gaussian"]), PIPE)
    _KEEP.append(ed)
    eq.install(ed, clipboard=FakeClipboard())
    _goto(ed, 1, 2)
    _key(ed, K.Key_Slash, K.ControlModifier)                        # Ctrl+/ はエディタ自身の物("* ")
    assert ed.toPlainText().split("\n")[1] == "* blur (0.5, 0.5)"
    ed.undo()
    _key(ed, K.Key_F, K.ControlModifier)
    assert ed.find_bar.isVisible()
    ed.find_bar.close_bar()
    ed.setPlainText("")
    ed.setFocus()
    QTest.keyClicks(ed, "gau")
    _pump(0.1)
    assert ed._completer.popup().isVisible()
    _key(ed, K.Key_Tab)                                             # 候補の窓が出ている間の Tab は窓の物
    _pump(0.05)
    assert "    " not in ed.toPlainText() and "\t" not in ed.toPlainText()
    ed._completer.popup().hide()
    ed.setPlainText("x")
    _goto(ed, 0, 1)
    _key(ed, K.Key_Tab)
    assert ed.toPlainText() == "x   "


def test_a_bare_modifier_key_does_not_open_the_op_completion_before_our_keys(app, studio_mod):
    """ProgramEditor はどのキーでもカーソル下の語の補完の窓を出す。Alt を押した時点で窓が開くと、続く矢印キーは
    窓の物になり、Alt+↑ や Shift+Alt+↓ がエディタへ届かない。取り付けた後は、修飾キーだけの押下では開かない。"""
    cls = studio_mod._program_editor_class(QtWidgets, QtGui, QtCore)
    ed = _show(cls(["blur", "otsu", "median"]), PIPE)
    _KEEP.append(ed)
    ops = eq.install(ed, clipboard=FakeClipboard())
    _goto(ed, 3, 3)                                                 # "median" の途中
    for key, mod in ((K.Key_Alt, K.AltModifier), (K.Key_Shift, K.ShiftModifier), (K.Key_Control, K.ControlModifier)):
        QTest.keyPress(ed, key, mod)
        _pump(0.03)
        assert not ed._completer.popup().isVisible(), key
        QTest.keyRelease(ed, key, K.NoModifier)
    _key(ed, K.Key_Up, K.AltModifier)
    _same(ed.toPlainText(), PIPE.replace("otsu (0.5, 0.5)", "@").replace("median (0.2, 0.2)", "otsu (0.5, 0.5)")
          .replace("@", "median (0.2, 0.2)"))
    _key(ed, K.Key_Down, SA)
    assert ops.active() and len(ops.carets()) == 2
    _key(ed, K.Key_Escape)
    ed.setPlainText("")
    QTest.keyClicks(ed, "ot")                                       # 普通に打てば、補完の窓は今までどおり出る
    _pump(0.05)
    assert ed._completer.popup().isVisible()
    ed._completer.popup().hide()


def test_code_editor_gets_the_groups_in_its_own_context_menu(app, studio_mod):
    cls = studio_mod._code_editor_class(QtWidgets, QtGui, QtCore)
    ed = _show(cls(), CODE)
    _KEEP.append(ed)
    ops = eq.install(ed, clipboard=FakeClipboard())
    assert not ops._own_context_menu()                              # このエディタは自前のメニューを出す
    rows = _menu_rows(ed.createStandardContextMenu())
    assert sorted(rows) == ["editops:menu.box", "editops:menu.display", "editops:menu.line"]
    ops.set_box(1, 4, 2, 4)
    QTest.keyClicks(ed, "# ")
    _same(ed.toPlainText(), "def f(a):\n    # x = [1, (2)]\n    # return x\nprint(f(0))")
    ed.undo()
    ed.undo()
    _same(ed.toPlainText(), CODE)
    full = [s for s in ed.extraSelections() if s.format.property(QtGui.QTextFormat.FullWidthSelection)]
    assert len(full) == 1                                           # 今の行の強調(このエディタには無かった物)
    _goto(ed, 0, 9)
    _key(ed, K.Key_Return)                                          # エディタ自身の自動字下げはそのまま
    assert ed.toPlainText().startswith("def f(a):\n    \n")


def test_py_editor_with_highlighter_and_assist(app):
    import studio_pyedit_complete as comp
    import studio_pyedit_qt as pq
    text = "import numpy as np\nimg = np.zeros((8, 8))  # 画像\nout = img + 1\n"
    ed = _show(pq.PyEditor(comp.default_provider(namespace={}, use_jedi=False), "dark", lambda s: s), text)
    _KEEP.append(ed)
    ops = eq.install(ed, clipboard=FakeClipboard())
    assert ops._assist() is ed.assist and ops._assist_active()
    ed.assist.set_breakpoints({2})
    ops.set_box(1, 0, 2, 3)
    ed.assist.refresh_decorations()                                 # 色分けの側が印を付け直しても箱は残る
    assert _box_selection_count(ed, ops) == 2
    assert ops.colors()["sel_bg"] == QtGui.QColor(ed.assist.theme.selection_bg)
    QTest.keyClicks(ed, "v")
    _same(ed.toPlainText(), "import numpy as np\nv = np.zeros((8, 8))  # 画像\nv = img + 1\n")
    _pump(0.1)
    assert ed.assist.highlighter.document() is ed.document()
    assert ed.assist.marks.breakpoints == {2}
    ed.undo()
    _same(ed.toPlainText(), text)
    ops.clear()
    # 候補の窓が出ている間の Tab / Esc は窓の物
    ed.setPlainText("np.ze")
    _goto(ed, 0, 5)
    ed.assist.provider = comp.default_provider(namespace={"np": __import__("numpy")}, use_jedi=False)
    assert ed.assist.show_completions(force=True)
    assert ed.assist.popup.isVisible()
    _key(ed, K.Key_Tab)
    _pump(0.05)
    assert "    " not in ed.toPlainText() and ed.toPlainText().startswith("np.zeros")
    ed.assist.popup.hide()


# --------------------------------------------------------------------------- #
# 本物の窓: 配線の覚え書きどおりに繋ぎ、キーの当たりを機械で確かめる
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def win(app, studio_mod):
    w, _model = studio_mod.build_window()
    w.resize(1400, 860)
    w.show()
    w.activateWindow()
    _pump(0.4)
    edit = w._program["edit"]
    # ---- ここからが「配線の覚え書き」の差分(studio.py の build_window の最後に入る 3 行) ----
    ops = eq.install(edit, tr=eo.make_tr(lambda: studio_mod._UI_LANG.get("code", "en"), first=studio_mod.tr),
                     settings=studio_mod._settings)
    ops.populate_menu(w._menus["edit"])
    w._actions.update(ops.command_actions(w))
    studio_mod.PALETTE_WORDS.update(eo.PALETTE_WORDS)
    # ---- ここまで ----
    ops._clipboard = FakeClipboard()
    w._editops = ops
    yield w
    for k in eo.PALETTE_WORDS:
        studio_mod.PALETTE_WORDS.pop(k, None)
    studio_mod._UI_LANG["code"] = "en"
    w.close_guard = lambda: True
    w.quiesce()
    w.close()
    _pump(0.1)


def _program(win, text):
    ed = win._program["edit"]
    win._docks["program"].show()
    win.activateWindow()
    ed.setPlainText(text)
    ed.setFocus()
    _pump(0.3)
    return ed


def test_no_key_of_ours_collides_with_any_shortcut_of_the_studio_window(win):
    ed = win._program["edit"]
    existing = eq.collect_shortcuts(win, ed)
    keys = {eo.normalize_key(k) for k, _owner, _covers in existing}
    assert len(existing) >= 60, len(existing)
    assert {"F5", "Ctrl+F", "Ctrl+S", "F1", "F9", "Ctrl+Shift+D", "Ctrl+D", "Ctrl+/"} <= keys     # 集め損ねていない
    reach = {eo.normalize_key(k): covers for k, owner, covers in existing if "Duplicate stage" in owner}
    assert reach == {"Ctrl+D": False}                               # 段の複製の Ctrl+D は段の一覧の中だけ
    report = eq.check_conflicts(win, ed)
    assert report["existing"] == len(existing)
    assert report["studio"] == [], report["studio"]
    assert report["internal"] == [], report["internal"]
    assert {key for _c, key, _o in report["builtin"]} <= {"Ctrl+D"}  # X11 系の既定(Ctrl+D = Delete)だけは上書きする
    mine = eo.active_bindings(editor_has_comment=True)
    assert len(mine) == 14


def test_the_checker_would_catch_a_collision(win):
    ed = win._program["edit"]
    a = QtGui.QAction("Clash for the test", win)
    a.setShortcut(QtGui.QKeySequence("Ctrl+Shift+K"))
    win.addAction(a)
    try:
        report = eq.check_conflicts(win, ed)
        assert report["studio"] == [("line.delete", "Ctrl+Shift+K", "Clash for the test")]
    finally:
        win.removeAction(a)
        a.setShortcut(QtGui.QKeySequence())
        a.setParent(None)
        a.deleteLater()
    _pump(0.05)
    assert eq.check_conflicts(win, ed)["studio"] == []


def test_box_selection_in_the_program_of_the_real_window(win):
    ed = _program(win, PIPE)
    ops = win._editops
    _goto(ed, 1, 6)
    _key(ed, K.Key_Down, SA, 1)
    _key(ed, K.Key_Right, SA, 3)
    assert ops.selected_texts() == ["0.5", "0.5"]
    QTest.keyClicks(ed, "0.25")
    _same(ed.toPlainText(), "* note\nblur (0.25, 0.5)\notsu (0.25, 0.5)\nmedian (0.2, 0.2)")
    for _ in range(4):
        ed.undo()
    _same(ed.toPlainText(), PIPE)
    _pump(0.3)
    _key(ed, K.Key_F, K.ControlModifier)                            # 既存のキーはそのまま
    assert win._program["find"]["bar"].isVisible()
    win._program["find"]["bar"].close_bar()
    _goto(ed, 1, 0)
    _key(ed, K.Key_Slash, K.ControlModifier)
    assert ed.toPlainText().split("\n")[1] == "* blur (0.5, 0.5)"
    ed.undo()
    _goto(ed, 3, 2)
    _key(ed, K.Key_Up, K.AltModifier)                               # 行の移動
    _same(ed.toPlainText(), "* note\nblur (0.5, 0.5)\nmedian (0.2, 0.2)\notsu (0.5, 0.5)")
    ed.undo()


def test_box_selection_in_python_mode_with_the_assist_active(win):
    code = "import numpy as np\na = np.zeros((4, 4))   # 画像 A\nbb = np.ones((4, 4))   # 画像 B\n"
    ed = _program(win, "")
    ops = win._editops
    win._pymode.set_mode("python", announce=False)
    try:
        ed.setPlainText(code)
        ed.setFocus()
        _pump(0.4)
        assert ops._assist_active() and ops.comment_prefix == "#"
        ops.set_box(1, 25, 2, 29)
        assert ops.selected_texts() == ["画像", "画像"]
        _pump(0.1)                                                  # PyEditAssist の印の付け直し(30 ms)の後も箱は残る
        assert _box_selection_count(ed, ops) == 2
        QTest.keyClicks(ed, "img")
        _same(ed.toPlainText(), code.replace("画像", "img"))
        for _ in range(3):
            ed.undo()
        _same(ed.toPlainText(), code)
        _goto(ed, 1, 0)
        _key(ed, K.Key_D, K.ControlModifier)                        # 行の複製(段の複製の Ctrl+D は段の一覧の中だけ)
        assert ed.toPlainText().count("a = np.zeros((4, 4))") == 2
        ed.undo()
        _same(ed.toPlainText(), code)
    finally:
        ed.setPlainText("")
        win._pymode.state["code_dirty"] = False
        win._pymode.set_mode("pipeline", announce=False)
        _pump(0.2)


def test_the_edit_menu_and_the_palette_have_the_same_entries(win, studio_mod):
    rows = _menu_rows(win._menus["edit"])
    assert sorted(rows) == ["editops:menu.box", "editops:menu.display", "editops:menu.line"]
    assert len(rows["editops:menu.box"]) + len(rows["editops:menu.line"]) >= 15
    labels = ["▸ " + win._actions[k].text() + " " + studio_mod.PALETTE_WORDS.get(k, "") for k in win._actions]
    keys = list(win._actions)

    def hits(q):
        return [keys[i] for i in studio_mod.palette_filter(labels, q)]

    found = {q: k in hits(q) for q, k in (("矩形", "editops_box_down"), ("box", "editops_box_up"),
                                          ("複製", "editops_line_duplicate"), ("duplicate line", "editops_line_duplicate"),
                                          ("括弧", "editops_bracket_jump"), ("行末", "editops_edit_trim"),
                                          ("使い方", "editops_howto"))}
    assert found == dict.fromkeys(found, True) and len(found) == 7
    ed = _program(win, "a\nb")
    win._actions["editops_line_duplicate"].trigger()
    _same(ed.toPlainText(), "a\na\nb")
    ed.undo()


def test_settings_of_the_real_window_go_to_the_temporary_settings_file(win, studio_mod):
    ops = win._editops
    path = os.environ["FULLSEYE_STUDIO_SETTINGS"]
    assert studio_mod._settings().fileName().replace("\\", "/") == path.replace("\\", "/")
    ops.set_rulers(())
    studio_mod._settings().sync()
    assert "rulers=" in open(path, encoding="utf-8").read()
    ops.set_rulers(eq.DEFAULT_RULERS)
    assert studio_mod._settings().value("editops/rulers") == "79,99"


def test_japanese_ui_shows_the_menu_in_japanese_in_the_real_window(win, studio_mod):
    ops = win._editops
    studio_mod._UI_LANG["code"] = "ja"
    try:
        rows = _menu_rows(ops.build_context_menu())
        items = [t for group in rows.values() for _n, t in group]
        assert len(items) >= 16
        assert [t for t in items if t.split("\t")[0].isascii()] == []
    finally:
        studio_mod._UI_LANG["code"] = "en"


# --------------------------------------------------------------------------- #
# 2026-11-15(設計書 D95): 残るメニュー(Edit メニュー)に足した入口は、言語の切り替えとキーの変更に追従する
# --------------------------------------------------------------------------- #
def test_retranslate_follows_the_language_and_the_keys_in_a_kept_menu(app):
    import shiboken6  # noqa: PLC0415
    lang = {"code": "en"}
    ed, ops, _clip = _plain(app, TEXT, tr=eo.make_tr(lambda: lang["code"]))
    menu = QtWidgets.QMenu()
    subs = ops.populate_menu(menu)                                   # Edit メニューのように、作ったまま残るメニュー
    acts = ops.command_actions()
    assert len(subs) == 3 and len(ops._menu_items) == 20            # サブメニュー 3 + 項目 17
    assert _menu_rows(menu)["editops:menu.line"][0] == ("editops:line.duplicate", "Duplicate line\tCtrl+D")
    ops.build_context_menu()                                         # 右クリックのメニューは毎回作る: 覚えない
    assert len(ops._menu_items) == 20
    table = eo.load_table()
    lang["code"] = "ja"
    assert ops.retranslate() == 20 and eq.retranslate_all() >= 1
    titles = [a.text() for a in menu.actions() if a.menu() is not None]
    assert titles == [table[t]["ja"] for t in (eo.MENU_BOX, eo.MENU_LINE, eo.MENU_DISPLAY)]
    assert _menu_rows(menu)["editops:menu.line"][0][1] == table["Duplicate line"]["ja"] + "\tCtrl+D"
    assert dict(_menu_rows(menu)["editops:menu.display"])["editops:rulers"] == table[eo.ACT_RULERS]["ja"]
    assert acts["editops_line_delete"].text() == table["Delete line"]["ja"]          # コマンドパレットの入口
    assert acts["editops_howto"].text() == table[eo.ACT_HOWTO]["ja"]
    ops.set_bindings({"line.duplicate": ("F8",)})                    # キーを変えたら、残るメニューの右のキーも
    assert _menu_rows(menu)["editops:menu.line"][0][1] == table["Duplicate line"]["ja"] + "\tF8"
    assert acts["editops_line_duplicate"].toolTip() == table["Duplicate line"]["ja"] + " (F8)"
    ops.set_bindings(None)
    assert _menu_rows(menu)["editops:menu.line"][0][1] == table["Duplicate line"]["ja"] + "\tCtrl+D"
    box = ops.show_howto()
    _pump(0.05)
    assert [b.text() for b in box.buttons()] == [table[eo.BTN_CLOSE]["ja"]]          # 「Close」のままにしない
    assert not any(b.isDefault() or b.autoDefault() for b in box.buttons())          # Enter でボタンを押さない
    lang["code"] = "de"
    ops.retranslate()                                                # 出ている「使い方」の窓も付け直す
    assert box.windowTitle() == table[eo.HOWTO_TITLE]["de"] and box.text() == table[eo.HOWTO_TEXT]["de"]
    assert [b.text() for b in box.buttons()] == [table[eo.BTN_CLOSE]["de"]]
    QTest.keyClick(box, K.Key_Escape)                                # Esc で閉じる
    _pump(0.05)
    assert not box.isVisible()
    shiboken6.delete(menu)                                           # 消えたメニューの入口は忘れる
    assert ops.retranslate() == 0 and ops._menu_items == []


def test_menu_keys_are_written_the_way_qt_writes_them(app):
    """設計書 D96: どう書いて渡しても、メニュー・ツールヒント・「使い方」に出す字は Qt の書き方(NativeText)。"""
    native = QtGui.QKeySequence.NativeText
    raw = [k for b in eo.KEYMAP for k in b.keys]
    assert len(raw) >= 15 and [k for k in raw if QtGui.QKeySequence(k).toString(native) != k] == []   # 表の字も同じ
    ed, ops, _clip = _plain(app, TEXT)
    ops.set_bindings({"line.duplicate": ("shift+alt+d", "Ctrl+D")})
    texts = dict(_menu_rows(ops.build_context_menu())["editops:menu.line"])
    assert texts["editops:line.duplicate"] == "Duplicate line\tAlt+Shift+D"
    assert ops.command_actions()["editops_line_duplicate"].toolTip() == "Duplicate line (Alt+Shift+D / Ctrl+D)"
    assert "Duplicate line: Alt+Shift+D / Ctrl+D" in ops.howto_text()
    ops.set_bindings(None)
    assert "Alt + Shift + arrow keys" in ops.howto_text() and "Shift + Alt" not in ops.howto_text()

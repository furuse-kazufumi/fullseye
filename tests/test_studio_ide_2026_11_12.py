# -*- coding: utf-8 -*-
"""Studio の IDE としての使いやすさ(第 1 便, 2026-11-12)。

監査(IDE_AUDIT.md)の受け入れ条件をそのまま試験にしたもの。起動は既存の Studio テストと同じ
(offscreen・空の設定ファイル)。キー操作は QTest で実際のキーイベントを送る(関数を直接呼ぶだけにしない)。

1. Program 欄のホバーヘルプ / 補完の順位(B-9)
2. 構文エラーの波線・ガター印・Problems(B-1)/「もしかして」/ 段の型違いの重複(B-2)
3. Program 欄の検索と置換(B-4)
4. Ctrl+/ の行コメント
5. Shift+F1 の op ヘルプ(B-10)/ 文字サイズ
6. Variables が非表示の間の実行(B-3)
7. 言語の切り替えに追従する文言(B-5, B-7)
8. 選んだ行だけの実行
"""
import json
import os
import re
import time

import pytest

import studio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CJK = re.compile("[぀-ヿ一-鿿]")


def _pump(sec=0.3):
    from PySide6 import QtWidgets
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def _app():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _launch(tmp_path, monkeypatch, size=(1400, 800), name="s.ini"):
    """空の設定ファイルで Studio を起動する(普段の設定には触らない)。"""
    _app()
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / name))
    win, model = studio.build_window()
    win.resize(*size)
    win.show()
    _pump(0.5)
    return win, model


def _close(win):
    studio._UI_LANG["code"] = "en"
    win.close_guard = lambda: True
    win.quiesce()
    win.close()
    _pump(0.1)


@pytest.fixture
def win(tmp_path, monkeypatch):
    w, m = _launch(tmp_path, monkeypatch)
    w._test_model = m
    yield w
    _close(w)


def _editor(win, text=""):
    """Program 欄を表示して中身を入れ、フォーカスを置く。"""
    ed = win._program["edit"]
    win._docks["program"].show()
    win.activateWindow()
    ed.setPlainText(text)
    ed.setFocus()
    _pump(0.3)
    return ed


def _key(w, key, mods=None):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    QTest.keyClick(w, key, mods if mods is not None else QtCore.Qt.NoModifier)
    _pump(0.05)


def _pos_of(ed, needle, nth=0):
    """欄の中で needle(の中ほど)がある位置(ビューポート座標)。"""
    from PySide6 import QtGui
    text = ed.toPlainText()
    i = -1
    for _ in range(nth + 1):
        i = text.index(needle, i + 1)
    c = QtGui.QTextCursor(ed.document())
    c.setPosition(i + max(1, len(needle) // 2))
    r = ed.cursorRect(c)
    from PySide6 import QtCore
    return QtCore.QPoint(r.x() + 1, r.center().y())


def _hover(ed, needle, nth=0):
    """needle の上へ ToolTip イベントを送り、出た文を返す(何も出なければ "")。"""
    from PySide6 import QtCore, QtGui, QtWidgets
    QtWidgets.QToolTip.hideText()
    p = _pos_of(ed, needle, nth)
    ev = QtGui.QHelpEvent(QtCore.QEvent.ToolTip, p, ed.viewport().mapToGlobal(p))
    QtWidgets.QApplication.sendEvent(ed.viewport(), ev)
    _pump(0.05)
    return QtWidgets.QToolTip.text() if QtWidgets.QToolTip.isVisible() else ""


# --------------------------------------------------------------------------- 1. ホバーヘルプ
def test_hover_on_an_op_name_shows_the_signature_and_the_real_unit(win):
    ed = _editor(win, "gaussian (0.4, 0.5)\n")
    text = _hover(ed, "gaussian")
    assert "blur σ" in text, text                       # つまみの実単位(受け入れ条件)
    assert "gaussian" in text                           # 補完 popup と同じシグネチャ文
    assert ed._tip("gaussian").splitlines()[0] in text


def test_hover_on_a_non_op_word_shows_nothing(win):
    ed = _editor(win, "gaussian (0.4, 0.5)\n* a comment about nothing\n")
    assert _hover(ed, "comment") == ""
    assert _hover(ed, "nothing") == ""


def test_hover_knob_text_follows_the_values_on_that_line(win):
    ed = _editor(win, "gaussian (0.1, 0.5)\ngaussian (0.9, 0.5)\n")
    first, second = _hover(ed, "gaussian", 0), _hover(ed, "gaussian", 1)
    line = lambda t: [x for x in t.splitlines() if "σ" in x and "=" in x][-1]
    assert line(first) != line(second)


# --------------------------------------------------------------------------- 補完の順位(B-9)
def test_completion_puts_the_nearest_name_first(win):
    ed = win._program["edit"]
    got = ed.completion_candidates("gaus")
    assert got[0] == "gaussian", got[:5]
    assert set(got) == set(ed._index.search("gaus", limit=None))      # 並べ替えるだけで、候補は増減しない
    assert ed.completion_candidates("gaussian")[0] == "gaussian"        # 完全一致
    exact = ed.completion_candidates("otsu")
    assert exact[0] == "otsu"


def test_completion_popup_order_and_tab_still_confirm(win):
    from PySide6 import QtCore
    ed = _editor(win, "")
    from PySide6.QtTest import QTest
    QTest.keyClicks(ed, "gaus")
    _pump(0.3)
    pop = ed._completer.popup()
    assert pop.isVisible()
    assert pop.model().index(0, 0).data() == "gaussian"
    _key(pop, QtCore.Qt.Key_Tab)                          # Tab で確定する挙動は変えない
    assert ed.toPlainText().strip() == "gaussian"

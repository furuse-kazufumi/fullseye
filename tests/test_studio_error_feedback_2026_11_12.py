# -*- coding: utf-8 -*-
"""P-03・P-04・P-06・P-10(2026-11-12 の使い勝手点検): エラーと無反応。"""
import os

import numpy as np
import pytest

import studio
import studio_errors


@pytest.fixture()
def win_model(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    seen = []
    monkeypatch.setattr(studio, "ERROR_HOOK", lambda parent, title, text: seen.append((title, text)))
    win, model = studio.build_window()
    win._seen_errors = seen
    yield win, model
    win.close_guard = lambda: True
    win.quiesce()
    win.close()


def _pump():
    from PySide6 import QtWidgets
    for _ in range(5):
        QtWidgets.QApplication.processEvents()


# ---- P-03: 長いメッセージは折り返して全文が読める -----------------------------------
def test_long_message_is_wrapped_not_cut_off(win_model):
    from PySide6 import QtGui
    win, _ = win_model
    view = win._main_view
    long = "wrapped words " * 40
    view.set_message("Pipeline error\n\n" + long)
    pm = view._item.pixmap()
    # 描いた文字が左右の端に触れない(以前は 1 行のまま左右が切れた)。余白 32px を空けて折り返している
    img = pm.toImage()
    w, h = img.width(), img.height()
    bg = QtGui.QColor("#12141b").rgb()
    for x in list(range(0, 24)) + list(range(w - 24, w)):
        for y in range(0, h, 3):
            assert img.pixel(x, y) == bg, "文字が端まで届いている(折り返されていない): x=%d y=%d" % (x, y)


# ---- P-04: 適用に失敗したら「前の結果を表示中(未適用)」---------------------------------
def test_failed_apply_marks_the_picture_as_previous_result(win_model):
    win, model = win_model
    win._load_sample_image("coins")
    ed = win._program["edit"]
    ed.setPlainText("gaussian (0.5, 0.5)\n")
    win._program["apply"](); _pump()
    assert win._main_view.notice_text() == ""
    ed.setPlainText("gaussian (0.5, 0.5)\nnot_an_op (0.5, 0.5)\n")
    win._program["apply"](); _pump()
    note = win._main_view.notice_text()
    assert "previous result (not applied)" in note
    assert "unknown op 'not_an_op'" in note, "新しいエラーの中身が画像側にも出る"
    assert [s[0] for s in model.stages] == ["gaussian"], "失敗した適用はモデルを変えない"
    # 次に成功したら消える
    ed.setPlainText("gaussian (0.5, 0.5)\notsu (0.5, 0.5)\n")
    win._program["apply"](); _pump()
    assert win._main_view.notice_text() == ""


def test_notice_in_japanese_mode(win_model):
    win, _ = win_model
    studio._UI_LANG["code"] = "ja"
    try:
        win._program["edit"].setPlainText("nope_op (0.5, 0.5)\n")
        win._program["apply"](); _pump()
        assert "前の結果を表示中(未適用)" in win._main_view.notice_text() or "未適用" in win._main_view.notice_text()
    finally:
        studio._UI_LANG["code"] = "en"


# ---- P-06: 開けない画像は最初の行に平易な原因 -------------------------------------------
@pytest.mark.parametrize("kind,ja,en", [
    ("missing", "ファイルが見つかりません", "does not exist"),
    ("empty", "空のファイル", "empty"),
    ("garbage", "読めない形式", "cannot be read"),
    ("folder", "フォルダが選ばれています", "folder"),
])
def test_unreadable_image_says_the_plain_cause_first(win_model, tmp_path, monkeypatch, kind, ja, en):
    win, _ = win_model
    if kind == "missing":
        p = tmp_path / "nope.png"
    elif kind == "empty":
        p = tmp_path / "empty.png"; p.write_bytes(b"")
    elif kind == "garbage":
        p = tmp_path / "bad.png"; p.write_bytes(b"this is not a png")
    else:
        p = tmp_path
    from PySide6 import QtWidgets
    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(p), "")))
    for lang, want in (("ja", ja), ("en", en)):
        studio._UI_LANG["code"] = lang
        try:
            win._seen_errors.clear()
            win._actions["open_image"].trigger()
        finally:
            studio._UI_LANG["code"] = "en"
        title, text = win._seen_errors[-1]
        first = text.splitlines()[0]
        assert want in first, (lang, first)
        assert "The step could not run" not in text and "処理を実行できませんでした" not in text


def test_open_failure_class_is_known():
    info = studio_errors.explain_failure(ValueError("cannot decode image: x"), open_path="x.png")
    assert info["class"] in studio_errors.FAILURE_CLASSES
    assert info["title"]["key"] == "err." + info["class"]


# ---- P-10: 何も選ばずに + を押したら理由を言う --------------------------------------------
def test_plus_without_a_selection_explains(win_model):
    win, model = win_model
    win._op_list.setCurrentItem(None)
    n = len(model.stages)
    win._op_buttons["insert"].click(); _pump()
    assert len(model.stages) == n
    assert "Select an operator from the list first." in win.statusBar().currentMessage()
    studio._UI_LANG["code"] = "ja"
    try:
        win._op_buttons["insert"].click(); _pump()
        assert "先に一覧から 1 つ選んでください" in win.statusBar().currentMessage()
    finally:
        studio._UI_LANG["code"] = "en"

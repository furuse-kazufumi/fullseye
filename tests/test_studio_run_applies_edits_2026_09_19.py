# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Studio: 実行キーは未適用の Program 編集を先に Apply する(GenSpark 第 8 報 N13、2026-09-19)。

Xvfb + xdotool の実測: Program に `gaussian (0.4, 0.5)` を打つと「● unapplied edits」になり、実行キーを
押しても画面が 1 bit も変わらなかった。`_do_run_all` が `model.stages`(古いパイプライン)をそのまま走らせて
いたから。直し = dirty なら先に apply、通らなければ走らせない。Ctrl+R を F5 の別名に。
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import studio  # noqa: E402


def _window():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    return studio.build_window(studio.PipelineModel(studio.demo_image(32)))


def test_run_all_applies_unapplied_program_edits_first():
    win, model = _window()
    edit = win._program["edit"]
    edit.setPlainText("gaussian (0.4, 0.5)\notsu (0.5, 0.5)")     # textChanged → code_dirty
    win._do_run_all()
    assert [list(s) for s in model.stages] == [["gaussian", 0.4, 0.5], ["otsu", 0.5, 0.5]]


def test_run_all_does_not_run_the_old_pipeline_when_the_edit_does_not_parse():
    win, model = _window()
    model.add_stage("gaussian")
    before = [list(s) for s in model.stages]
    win._program["edit"].setPlainText("no_such_op_xyz (0.5, 0.5)")
    win._do_run_all()                                                # Apply が通らない → 何も変えない
    assert [list(s) for s in model.stages] == before


def test_browser_search_ranks_name_matches_before_doc_matches():
    win, _model = _window()
    win._search.setText("canny")
    names = [win._op_list.item(i).data(0x0100) for i in range(win._op_list.count())]   # Qt.UserRole
    assert names, "no hit for 'canny'"
    assert "canny" in names[0], names[:5]                 # 名前に含む op が説明文だけの op(edges_color)より先
    if "edges_color" in names:
        assert names.index("edges_color") > names.index(names[0])


def test_run_once_says_so_when_the_op_fell_back():
    win, model = _window()
    import fullseye as fs
    # edges_color は color(3-D)入力。グレー画像に Run once すると sort の既定値へ落ちる
    lst = win._op_list
    win._search.setText("edges_color")
    idx = next((i for i in range(lst.count()) if lst.item(i).data(0x0100) == "edges_color"), None)
    if idx is None:
        pytest.skip("edges_color not registered here (needs cv2)")
    lst.setCurrentRow(idx)
    fs.clear_fallbacks()
    n_before = len(win._graphics_windows)
    win._run_op_once()
    assert len(win._graphics_windows) == n_before + 1
    gw = win._graphics_windows[-1]
    title = gw.windowTitle() if hasattr(gw, "windowTitle") else str(getattr(gw, "title", ""))
    assert "FALLBACK" in title, title


def test_ctrl_r_is_an_alias_of_the_run_key():
    win, _model = _window()
    from PySide6 import QtGui
    shortcuts = {s.toString() for a in win.findChildren(QtGui.QAction) for s in a.shortcuts()}
    assert "F5" in shortcuts and "Ctrl+R" in shortcuts

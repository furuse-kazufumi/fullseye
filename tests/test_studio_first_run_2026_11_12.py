# -*- coding: utf-8 -*-
"""Studio の最初の 1 分(2026-11-12 の使い勝手点検 P-01・P-15)の回帰テスト。

P-01: 設定を空にして起動 → 何も触らず終了 → 同じ設定で再起動、で Operators・Pipeline・
Program が消えて画像だけになっていた。窓を閉じると Qt が dock を全部 hide して
visibilityChanged(False) を撃ち、それを「利用者が閉じた」として保存していたため。
"""
import os
import time

import pytest


def _pump(app, sec=0.5):
    end = time.monotonic() + sec
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def _launch(monkeypatch, ini, then=None):
    """設定 ini を指して Studio を起動し、可視状態を返して閉じる。"""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(ini))
    from PySide6 import QtWidgets
    import studio

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, _model = studio.build_window()
    win.show()
    _pump(app)
    if then is not None:
        then(win, app)
    seen = {k: d.isVisible() for k, d in win._docks.items()}
    win.quiesce()
    win.close_guard = lambda: True
    win.close()
    _pump(app, 0.2)
    return seen


def test_two_launches_with_same_empty_settings_keep_the_panels(tmp_path, monkeypatch):
    ini = tmp_path / "fresh.ini"
    first = _launch(monkeypatch, ini)
    second = _launch(monkeypatch, ini)
    for panel in ("operators", "pipeline", "program"):
        assert first[panel], "1 回目の起動で %s が見えない" % panel
        assert second[panel], "2 回目の起動で %s が消えた(P-01)" % panel
    assert first == second


def test_first_launch_shows_the_pipeline_parameters_tab(tmp_path, monkeypatch):
    """P-15: 初回レイアウトで Pipeline · Parameters のタブが Operators の隣に見える。"""
    seen = {}

    def probe(win, app):
        dock = win._docks["pipeline"]
        seen["hidden"] = dock.isHidden()
        seen["tabbed"] = win._docks["pipeline"] in win.tabifiedDockWidgets(win._docks["operators"])

    _launch(monkeypatch, tmp_path / "fresh.ini", then=probe)
    assert seen == {"hidden": False, "tabbed": True}


def test_a_panel_the_user_closed_stays_closed_next_time(tmp_path, monkeypatch):
    """直し過ぎの検査: 利用者が自分で閉じたパネルは、次回も閉じたまま。"""
    ini = tmp_path / "fresh.ini"
    _launch(monkeypatch, ini, then=lambda win, app: (win._docks["program"].close(), _pump(app, 0.2)))
    second = _launch(monkeypatch, ini)
    assert not second["program"]
    assert second["operators"] and second["pipeline"]


def test_switching_tabs_does_not_hide_the_tab_behind(tmp_path, monkeypatch):
    """タブの裏に回った dock は「閉じた」ではない(visibilityChanged(False) の誤記録)。"""
    ini = tmp_path / "fresh.ini"

    def flip(win, app):
        win._docks["pipeline"].raise_()
        _pump(app, 0.2)
        win._docks["operators"].raise_()
        _pump(app, 0.2)

    _launch(monkeypatch, ini, then=flip)
    second = _launch(monkeypatch, ini)
    assert second["operators"] and second["pipeline"] and second["program"]

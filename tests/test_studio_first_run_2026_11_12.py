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
    # 2026-11-13(第 2 段): 初回は画像 + コード。ほかのパネルはパネルの帯から出す。
    assert first["program"], "1 回目の起動で program が見えない"
    assert second["program"], "2 回目の起動で program が消えた(P-01)"
    assert [k for k, v in first.items() if v] == ["program"] and len(first) == 7
    assert first == second


def test_first_launch_has_the_pipeline_parameters_one_click_away(tmp_path, monkeypatch):
    """P-15(2026-11-13 に形を変えた): 初回、Pipeline · Parameters はパネルの帯のボタン 1 回で出る。

    以前は「タブを初回から見せる」で守っていた(隠れた dock の裏のつまみを初めての人が見つけられない)。
    第 2 段で初回は画像 + コードだけにしたので、常に見えているボタンから 1 回で出ることを確かめる。"""
    seen = {}

    def probe(win, app):
        dock = win._docks["pipeline"]
        button = win._panels["buttons"]["pipeline"]
        seen["button_visible"] = button.isVisible()
        seen["tip_names_it"] = button.toolTip().startswith(dock.windowTitle())
        seen["hidden_before"] = dock.isHidden()
        button.click()
        _pump(app, 0.2)
        seen["visible_after"] = dock.isVisible()

    _launch(monkeypatch, tmp_path / "fresh.ini", then=probe)
    assert seen == {"button_visible": True, "tip_names_it": True, "hidden_before": True, "visible_after": True}


def test_a_panel_the_user_closed_stays_closed_next_time(tmp_path, monkeypatch):
    """直し過ぎの検査: 利用者が自分で閉じたパネルは、次回も閉じたまま。"""
    ini = tmp_path / "fresh.ini"

    def use(win, app):
        win._panels["buttons"]["operators"].click()      # 出したパネルは次回も出ている
        win._panels["buttons"]["pipeline"].click()
        _pump(app, 0.2)
        win._docks["program"].close()
        _pump(app, 0.2)

    _launch(monkeypatch, ini, then=use)
    second = _launch(monkeypatch, ini)
    assert not second["program"]
    assert second["operators"] and second["pipeline"]
    assert not second["variables"] and not second["display"]      # 出していない物は出てこない


def test_switching_tabs_does_not_hide_the_tab_behind(tmp_path, monkeypatch):
    """タブの裏に回った dock は「閉じた」ではない(visibilityChanged(False) の誤記録)。"""
    ini = tmp_path / "fresh.ini"

    def flip(win, app):
        win._panels["buttons"]["operators"].click()
        win._panels["buttons"]["pipeline"].click()
        _pump(app, 0.2)
        win._docks["pipeline"].raise_()
        _pump(app, 0.2)
        win._docks["operators"].raise_()
        _pump(app, 0.2)

    _launch(monkeypatch, ini, then=flip)
    second = _launch(monkeypatch, ini)
    assert second["operators"] and second["pipeline"] and second["program"]

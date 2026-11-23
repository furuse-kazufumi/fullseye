# -*- coding: utf-8 -*-
"""Studio の Program 欄の Python のモード(UI の繋ぎ, 2026-11-13)。

受け入れの筋書き 13 項目(repo の外に置いた作業用の e2e.py が本物の窓で通す物)の offscreen 版。
起動は既存の Studio の試験と同じ(offscreen・空の設定ファイル)。キーは QTest で本物のキーイベントを送る。
確認の窓(信頼・保存・名前を付けて保存・条件)は studio_pymode の差し込み口を差し替える。
"""
import builtins
import json
import os
import threading
import time

import numpy as np
import pytest

import studio
import studio_program as sp
import studio_pymode as pm_mod
import studio_timingkit as timing


#: GUI heartbeat を送るまでの遅延(ms) / delay before the GUI heartbeat is sent.
GUI_HEARTBEAT_DELAY_MS = 100
#: 作業側が heartbeat を待つ上限(秒) / worker-side heartbeat deadline.
GUI_HEARTBEAT_DEADLINE_S = 2.0
#: user program から heartbeat を見る builtins 名 / builtin name carrying the heartbeat.
GUI_HEARTBEAT_BUILTIN = "_studio_test_gui_heartbeat"


# --------------------------------------------------------------------------- #
# 道具                                                                          #
# --------------------------------------------------------------------------- #
def _app():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _pump(sec=0.3):
    from PySide6 import QtWidgets
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)


def _launch(tmp_path, monkeypatch, name="s.ini", start_mode="auto", time_limit=None):
    _app()
    ini = tmp_path / name
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(ini))
    if time_limit is not None:
        from PySide6 import QtCore
        s = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
        s.setValue("pymode/time_limit_s", time_limit)
        s.sync()
    win, model = studio.build_window(start_mode=start_mode)
    win.resize(1400, 860)
    win.show()
    win.activateWindow()
    _pump(0.4)
    return win, model


def _close(win):
    studio._UI_LANG["code"] = "en"
    win.close_guard = lambda: True
    win.quiesce()
    win.close()
    _pump(0.1)


def _set_text(win, text):
    from PySide6 import QtGui
    ed = win._program["edit"]
    c = QtGui.QTextCursor(ed.document())
    c.select(QtGui.QTextCursor.Document)
    c.insertText(text)
    ed.setTextCursor(c)
    _pump(0.35)                                   # 打っている最中の検査(250 ms の待ち)


def _key(win, key, mod=None):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    QTest.keyClick(win._program["edit"], key, mod or QtCore.Qt.NoModifier)
    _pump(0.05)


def _run_f5(win, timeout=30):
    from PySide6 import QtCore
    _key(win, QtCore.Qt.Key_F5)
    assert win._pymode.wait_idle(timeout)
    _pump(0.1)
    return win._pymode.last


def _problems(win):
    pl = win._problems_list
    return [pl.item(i) for i in range(pl.count())]


# --------------------------------------------------------------------------- #
# Qt なしの部品                                                                 #
# --------------------------------------------------------------------------- #
def test_line_base_is_converted_in_one_place():
    """画面の行(1 始まり)⇔ Qt のブロック・補完の供給元(0 始まり)の変換は 1 か所。studio_program.complete は
    1 始まりで、PyEditAssist の供給元は 0 始まり: LineBase(base=1) で包むと同じ候補になる。"""
    assert pm_mod.to_block(1) == 0 and pm_mod.to_line(0) == 1
    assert [pm_mod.to_line(pm_mod.to_block(n)) for n in range(1, 6)] == [1, 2, 3, 4, 5]
    assert pm_mod.to_block(0) == 0                       # 0 以下は先頭のブロックへ
    import studio_pyedit_complete as comp

    class _Src:
        def complete(self, text, line, col):
            return [c["name"] for c in sp.complete(text, line, col)]

        def hover(self, text, line, col):
            return sp.hover(text, line, col)
    text = "x = 1\ny = gaus"
    wrapped = comp.LineBase(_Src(), base=1)
    assert "gaussian" in wrapped.complete(text, 1, 8)    # 0 始まりの行 1 = 2 行目
    assert "gaussian" in [c["name"] for c in sp.complete(text, 2, 8)]
    assert wrapped.hover("y = gaussian(img)", 0, 6)["name"] == "gaussian"


def test_run_plan_continue_and_step():
    s = pm_mod.DebugSession("t", lines_run=6, line=4, reason="breakpoint")
    assert pm_mod.run_plan("run", None, "t", {4}, {}) == {"breakpoints": [4], "conditions": {}, "resume_after_lines": 0,
                                                          "max_lines": None, "restart": False, "resume": None}
    # 待っている実行が無い止まり方(pause_hook を使えない形): 今までどおり走り直しで続ける
    assert not s.live
    assert pm_mod.run_plan("continue", s, "t", {4}, {4: "i > 1"})["resume_after_lines"] == 7
    assert pm_mod.run_plan("continue", s, "changed", {4}, {})["restart"] is True
    assert pm_mod.run_plan("step", s, "t", {4}, {})["max_lines"] == 7
    assert pm_mod.run_plan("step", None, "t", {4}, {})["max_lines"] == 0
    # 待っている実行がある: 起こすだけ(新しい実行を作らない)。文面が変わっていれば上から
    ev = threading.Event()
    job = pm_mod.RunJob("program", ev.wait, ev, {}).start()
    try:
        live = pm_mod.DebugSession("t", lines_run=6, line=4, reason="breakpoint", job=job)
        assert live.live
        assert pm_mod.run_plan("continue", live, "t", {4, 9}, {9: "i > 1"}) == {
            "breakpoints": [4, 9], "conditions": {9: "i > 1"}, "resume_after_lines": 0, "max_lines": None,
            "restart": False, "resume": "continue"}
        assert pm_mod.run_plan("step", live, "t", {4}, {})["resume"] == "step"
        assert pm_mod.run_plan("run", live, "t", {4}, {})["resume"] is None
        changed = pm_mod.run_plan("continue", live, "changed", {4}, {})
        assert changed["resume"] is None and changed["restart"] is True
    finally:
        ev.set()
        job.thread.join(2.0)
    assert not live.live
    with pytest.raises(ValueError):
        pm_mod.run_plan("jump", None, "t", (), {})
    assert pm_mod.first_changed_line("a\nb\nc", "a\nB\nc") == 2
    assert pm_mod.first_changed_line("a\nb", "a\nb") is None
    assert pm_mod.error_line_of("line 12: ZeroDivisionError: division by zero") == 12


def test_conditional_breakpoint_and_resume_in_the_runner():
    img = np.zeros((16, 16))
    t = "x = 0\nfor i in range(4):\n    x = x + i\nprint(x)\n"
    r = sp.run_program(t, img, breakpoints=[3], conditions={3: "i == 2"})
    assert r.stopped == "breakpoint" and r.stopped_line == 3 and r.values["i"] == 2
    r2 = sp.run_program(t, img, breakpoints=[3], resume_after_lines=r.lines_run + 1)
    assert r2.stopped == "breakpoint" and r2.lines_run > r.lines_run
    bad = sp.run_program(t, img, breakpoints=[3], conditions={3: "nope > 1"})
    assert bad.stopped == "breakpoint" and any("could not be evaluated" in n for n in bad.notes)   # 止めて理由を言う


def test_evaluate_stops_a_selected_infinite_loop():
    ns = sp.run_program("x = 1\n", np.zeros((8, 8))).namespace
    t0 = time.perf_counter()
    r = sp.evaluate("while True:\n    pass", ns, time_limit_s=0.3)
    assert time.perf_counter() - t0 < 3.0
    assert r["error"] and "stopped" in r["error"]


# --------------------------------------------------------------------------- #
# 1. 起動 → Python のモード、例が入って色分けされている                           #
# --------------------------------------------------------------------------- #
def test_1_new_settings_start_in_python_with_the_example(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        assert pm.mode == "python" and pm.btn_py.isChecked() and not pm.btn_pipe.isChecked()
        text = win._program["edit"].toPlainText()
        assert text == sp.STARTER_PROGRAM and 10 <= len(text.strip().splitlines()) <= 15
        assert pm.assist is not None and pm.assist.active
        assert pm.assist.highlighter.document() is win._program["edit"].document()
        blk = win._program["edit"].document().findBlockByNumber(8)          # "if n > 10:" の行
        assert blk.layout().formats(), "the Python text is not coloured"
        assert "Python" in pm.mode_note.text()
        assert win._actions["pymode_python"].isChecked()
    finally:
        _close(win)


def test_build_window_default_stays_in_the_pipeline_mode(tmp_path, monkeypatch):
    """ライブラリ・既存の試験の build_window() は今までどおりパイプラインのモード(既存の試験の前提を壊さない)。"""
    _app()
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "p.ini"))
    win, _m = studio.build_window()
    try:
        assert win._pymode.mode == "pipeline"
        assert not win._program["edit"].toPlainText().startswith("# python")
        assert not win._state.get("code_dirty"), "attaching the Python highlighter must not mark unapplied edits"
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 2. 実行 → 絵・記録・出力・変数。実行の間も画面は固まらない                       #
# --------------------------------------------------------------------------- #
def test_2_run_shows_picture_record_output_and_variables(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        res = _run_f5(win)
        assert res.ok, res.errors
        assert [c.op for c in res.calls] == ["gaussian", "otsu", "blob_count", "opening_circle"]
        assert pm.record.count() == 4 and pm.record.item(0).text().startswith("L5  gaussian")
        assert not pm.record.item(0).icon().isNull()                      # サムネイル
        assert "blobs:" in pm.output.toPlainText()
        assert {"img", "mask", "n"} <= set(pm.var_source.ns)
        assert np.array_equal(win._state["raw"], res.output)              # 画像の欄 = 最後に見せた値
        assert pm.stage_stack.currentIndex() == 1
    finally:
        _close(win)


def test_2_gui_keeps_running_during_a_slow_program(tmp_path, monkeypatch):
    from PySide6 import QtCore
    heartbeat = threading.Event()
    monkeypatch.setattr(builtins, GUI_HEARTBEAT_BUILTIN, heartbeat, raising=False)
    win, model = _launch(tmp_path, monkeypatch)
    try:
        _set_text(win, "# python\nimport builtins, time\n"
                       "deadline = time.perf_counter() + %r\n"
                       "while not getattr(builtins, %r).is_set() "
                       "and time.perf_counter() < deadline:\n"
                       "    pass\n"
                       "gui_heartbeat_seen = getattr(builtins, %r).is_set()\n"
                       "show(img)\n" % (GUI_HEARTBEAT_DEADLINE_S, GUI_HEARTBEAT_BUILTIN,
                                         GUI_HEARTBEAT_BUILTIN))
        _key(win, QtCore.Qt.Key_F5)
        assert win._pymode.running
        QtCore.QTimer.singleShot(GUI_HEARTBEAT_DELAY_MS, heartbeat.set)
        assert win._pymode.wait_idle(10)
        assert win._pymode.last.values["gui_heartbeat_seen"] is True
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 3. 打っている最中の波線と Problems(押すとその行へ、直すと消える)               #
# --------------------------------------------------------------------------- #
def test_3_errors_while_typing(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        ed = win._program["edit"]
        _set_text(win, "# python\nx = 0\nif x = 1:\n    pass\n")
        rows = _problems(win)
        assert rows and "assign_in_condition" in rows[0].text()
        assert 3 in ed.errors()
        win._problems_list.itemClicked.emit(rows[0])
        assert ed.textCursor().blockNumber() + 1 == 3
        _set_text(win, "# python\nx = 0\nif x == 1:\n    pass\n")
        assert not _problems(win) and not ed.errors()
        _set_text(win, "# python\ny = gausian(img, 0.3)\n")
        txt = " ".join(r.text() for r in _problems(win))
        assert "gausian" in txt and "gaussian" in txt                     # もしかして
        _set_text(win, "# python\ny = gaussian（img, 0.3）\n")
        assert "fullwidth_char" in " ".join(r.text() for r in _problems(win))
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 4. 補完・引数の案内・ホバー                                                    #
# --------------------------------------------------------------------------- #
def test_4_completion_signature_and_hover(tmp_path, monkeypatch):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        pm.catalog.warm_up()
        _set_text(win, "# python\n")
        ed = win._program["edit"]
        ed.setFocus()
        from PySide6 import QtGui
        c = ed.textCursor()
        c.movePosition(QtGui.QTextCursor.End)
        ed.setTextCursor(c)
        QTest.keyClicks(ed, "x = gaus")
        _pump(0.3)
        a = pm.assist
        assert a.popup.isVisible()
        names = [it.name for it in a._items]
        assert "gaussian" in names[:5]
        g = [it for it in a._items if it.name == "gaussian"][0]
        assert g.detail                                                  # op の説明
        QTest.keyClick(ed, QtCore.Qt.Key_Escape)
        QTest.keyClicks(ed, "sian(")
        _pump(0.3)
        assert a.tip.isVisible()
        h = pm.provider.hover("y = gaussian(img, 0.3)", 0, 6)
        assert h is not None and "gaussian" in h.title
        assert not ed._completer.popup().isVisible()                     # 古い補完は出ない(二重にしない)
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 5. ブレークポイント(条件つき)・1 行・続行・止める・ウォッチ                      #
# --------------------------------------------------------------------------- #
def test_5_breakpoint_step_continue_and_watch(tmp_path, monkeypatch):
    from PySide6 import QtCore
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        pm.vars.watch.add_expression("n * 2")
        ed.goto_line(8)                                                  # print("blobs:", n)
        _key(win, QtCore.Qt.Key_F9)
        assert 8 in ed.breakpoints
        res = _run_f5(win)
        assert res.stopped == "breakpoint" and res.stopped_line == 8
        assert ed._exec_line == 8 and pm.session is not None
        assert len(res.calls) == 3 and "n" in pm.var_source.ns
        assert pm.vars.watch.wait_idle(5)
        assert str(int(res.values["n"] * 2)) in pm.vars.watch.table.item(0, 1).text()
        assert pm.btn_run.text() == "Continue"
        _key(win, QtCore.Qt.Key_F6)
        assert pm.wait_idle(10)
        assert pm.last.stopped == "step" and pm.last.stopped_line == 9
        _key(win, QtCore.Qt.Key_F5)                                      # 続行 → 最後まで
        assert pm.wait_idle(10)
        assert pm.last.ok and pm.session is None and ed._exec_line == -1
        # 条件つき: ループの中で i == 3 のときだけ止まる
        _set_text(win, "# python\nt = 0\nfor i in range(6):\n    t = t + i\nshow(img)\n")
        pm.set_condition(4, "i == 3")
        res = _run_f5(win)
        assert res.stopped == "breakpoint" and res.values["i"] == 3
        _key(win, QtCore.Qt.Key_F2, QtCore.Qt.ControlModifier)          # 止める(Debug の区切りを終える)
        assert pm.session is None
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 6. 実行時の例外                                                              #
# --------------------------------------------------------------------------- #
def test_6_runtime_exception_marks_the_line(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        _set_text(win, "# python\nx = 0\ny = 1 / x\nshow(img)\n")
        res = _run_f5(win)
        assert res.errors and "ZeroDivisionError" in res.errors[0] and res.error_line == 3
        assert "line 3: ZeroDivisionError" in pm.output.toPlainText()
        _pump(0.35)
        assert 3 in ed.errors()
        rows = _problems(win)
        assert rows, "the Problems list is empty"
        assert any("ZeroDivisionError" in r.text() for r in rows), [r.text() for r in rows]
        ed.goto_line(1)
        pm.goto_line(pm_mod.error_line_of(res.errors[0]))
        assert ed.textCursor().blockNumber() + 1 == 3
        assert win.isVisible()                                           # Studio は落ちない
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 7. 無限ループ: 止めるボタン・時間の上限・Release・止められない C の呼び出し          #
# --------------------------------------------------------------------------- #
def test_7_infinite_loop_is_stopped(tmp_path, monkeypatch):
    from PySide6 import QtCore
    win, model = _launch(tmp_path, monkeypatch, time_limit=30)
    try:
        pm = win._pymode
        _set_text(win, "# python\nwhile True:\n    pass\n")
        # 止めるボタン: 時間の上限は遠くに置く(上限 0.8 s のまま押すと、遅い機械では上限が先に来て time_limit に
        # なる = 2 つの原因を競わせる試験だった。e2e の 7 段目が 10 回中 5 回落ちた原因)
        _key(win, QtCore.Qt.Key_F5)
        _pump(0.2)
        assert pm.running
        t0 = time.perf_counter()
        pm.btn_stop.click()
        assert pm.wait_idle(5)
        assert pm.last.stopped == "stop_requested" and time.perf_counter() - t0 < 3.0
        pm._set("time_limit_s", 0.8)
        res = _run_f5(win)                                               # 時間の上限
        assert res.stopped == "time_limit"
        pm.set_config("release")
        res = _run_f5(win)
        assert res.stopped in ("time_limit", "stop_requested") and res.config == "release"
        # Lock.acquire() は全 OS で Python bytecode に戻らない C 待機。有限の sleep は単に遅く、先に戻り得る。
        gate = timing.UnstoppableGate()
        _set_text(win, "# python\n" + gate.source())
        t0 = time.perf_counter()
        res = _run_f5(win, timeout=10)
        assert res.stopped == "unstoppable" and time.perf_counter() - t0 < 6
        assert "could not stop" in pm.output.toPlainText()
        # 画面は使い続けられる。残った実行が終わるまでは次の実行を断ってそう言い、終われば走る
        _set_text(win, "# python\nshow(gaussian(img, 0.2))\n")
        runs0 = pm.state.get("pymode_runs", 0)
        _key(win, QtCore.Qt.Key_F5)
        _pump(0.2)
        assert pm.state.get("pymode_runs", 0) == runs0 and "still running in the background" in pm.output.toPlainText()
        gate.release()
        end = time.monotonic() + 15
        while sp.abandoned_runs() and time.monotonic() < end:
            time.sleep(0.05)
        assert not sp.abandoned_runs()                                    # 残したまま次の試験へ行かない
        assert _run_f5(win).ok
    finally:
        if "gate" in locals():
            gate.close()
        _close(win)


# --------------------------------------------------------------------------- #
# 8. Debug ⇔ Release                                                          #
# --------------------------------------------------------------------------- #
def test_8_debug_and_release_give_the_same_result(tmp_path, monkeypatch):
    from PySide6 import QtCore
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        d = _run_f5(win).output
        flashes = []
        monkeypatch.setattr(pm, "flash", lambda m: flashes.append(m))
        win._program["edit"].breakpoints.add(6)
        win._actions["pymode_config_toggle"].trigger()
        assert pm.config == "release" and pm.config_box.currentText() == "Release"
        assert any("Release does not stop" in f for f in flashes)
        res = _run_f5(win)
        assert res.stopped is None and np.array_equal(res.output, d)
        assert len(res.notes) >= 1, "no notes at all"
        assert any("Release does not stop" in n for n in res.notes), res.notes
        assert not pm.btn_step.isEnabled()
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 9. 値を 1 つ変えて再実行 → 変えていない op はメモ化                              #
# --------------------------------------------------------------------------- #
def test_9_memo_reuses_unchanged_calls(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        _run_f5(win)
        text = win._program["edit"].toPlainText().replace("opening_circle(mask, 0.3)", "opening_circle(mask, 0.2)")
        _set_text(win, text)
        assert "out of date" in pm.record_title.text()
        res = _run_f5(win)
        assert [c.cached for c in res.calls] == [True, True, True, False]
        assert "cache" in pm.record.item(0).text() and "calc" in pm.record.item(3).text()
        assert "3 from cache" in pm.record_title.text()
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 10. ファイル・信頼の確認・プロジェクト                                            #
# --------------------------------------------------------------------------- #
def test_10_files_unsaved_mark_and_trust(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        p = tmp_path / "a.py"
        monkeypatch.setattr(pm_mod, "SAVE_AS_HOOK", lambda *_a: str(p))
        assert win._actions["pymode_new"].isEnabled()
        win._actions["pymode_new"].trigger()
        _set_text(win, "# python\nprint('hello')\nshow(img)\n")
        assert pm.unsaved() and "\u25cf" in pm.file_label.text() and "*" in win.windowTitle()
        win._actions["pymode_save"].trigger()
        assert p.read_text(encoding="utf-8").startswith("# python") and not pm.unsaved()
        assert "*" not in win.windowTitle().split(" — ")[0]
        # 外から来たファイル: 初回の実行の前に確認(断れば走らない)
        q = tmp_path / "other.py"
        q.write_text("# python\nprint('from file')\nshow(img)\n", encoding="utf-8")
        asked = []
        monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *_a: asked.append(1) or False)
        assert pm.open_program(str(q))
        runs0 = pm.state.get("pymode_runs", 0)
        _run_f5(win)
        assert asked and pm.state.get("pymode_runs", 0) == runs0           # 確認を断った: 走っていない
        monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *_a: asked.append(2) or True)
        res = _run_f5(win)
        assert res.ok and "from file" in res.stdout
        n = len(asked)
        assert pm.open_program(str(q))                                   # 同じ中身: 覚えている
        _run_f5(win)
        assert len(asked) == n
        q.write_text("# python\nprint('changed')\nshow(img)\n", encoding="utf-8")
        assert pm.open_program(str(q))                                   # 中身が変わった: 確認し直す
        _run_f5(win)
        assert len(asked) == n + 1
        # 閉じる前の確認(未保存のファイル)
        _set_text(win, "# python\nprint('edited')\n")
        monkeypatch.setattr(pm_mod, "SAVE_HOOK", lambda *_a: "cancel")
        assert pm.confirm_close() is False
    finally:
        _close(win)


def test_10_project_panel_opens_python_and_finds_pipelines_and_params(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        root = tmp_path / "proj"
        for sub in ("images", "pipelines", "programs", "params", "results"):
            (root / sub).mkdir(parents=True)
        (root / "pipelines" / "x.json").write_text(json.dumps(
            {"fullseye_pipeline": 1, "stages": [["gaussian", 0.3, 0.5], ["otsu", 0.5, 0.5]]}), encoding="utf-8")
        (root / "params" / "rig.toml").write_text("[camera]\nfx = 1200.0\n", encoding="utf-8")
        prog = root / "programs" / "p.py"
        prog.write_text("# python\np = load_pipeline('x.json')\nm = p(img)\nrig = load_params('rig.toml')\n"
                        "print(rig['camera.fx'])\nshow(m)\n", encoding="utf-8")
        win._project["open_dir"](str(root))
        _pump(0.2)
        monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *_a: True)
        assert win._open_python_file(str(prog)) is not False              # Project のパネルの行き先
        assert pm.active and pm.file == str(prog) and pm.origin == "project"
        res = _run_f5(win)
        assert res.ok, res.errors
        assert "1200" in res.stdout and [c.pipeline for c in res.calls[:2]] == ["x", "x"]
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 11. パイプラインとの往復                                                       #
# --------------------------------------------------------------------------- #
def test_11_pipeline_mode_round_trip(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda *_a: True)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        _set_text(win, "# python\nshow(gaussian(img, 0.25))\n")
        model.stages = [["gaussian", 0.4, 0.5], ["otsu", 0.5, 0.5]]
        win._refresh_stage_list()
        win._actions["pymode_toggle"].trigger()
        assert pm.mode == "pipeline" and ed.toPlainText().startswith("gaussian (0.4, 0.5)")
        assert pm.stage_stack.currentIndex() == 0 and pm.btn_pipe.isChecked()
        assert not win._state.get("code_dirty")
        win._actions["pymode_toggle"].trigger()
        assert ed.toPlainText() == "# python\nshow(gaussian(img, 0.25))\n"    # 切り替えで失わない
        win._actions["pymode_toggle"].trigger()
        win._actions["pymode_convert"].trigger()
        assert pm.active and ed.toPlainText().splitlines()[0] == "img = gaussian(img, 0.4, 0.5)"
        res = _run_f5(win)
        ref = studio.api.run_pipeline(model.image, [("gaussian", 0.4, 0.5)], coerce=True)
        ref = studio.api.run_pipeline(ref, [("otsu", 0.5, 0.5)], coerce=False)
        assert np.array_equal(res.output, ref)
        ed.undo()
        assert ed.toPlainText() == "# python\nshow(gaussian(img, 0.25))\n"    # Undo で前の Python
        pj = tmp_path / "pipe.json"
        pj.write_text(json.dumps({"fullseye_pipeline": 1, "stages": [["median", 0.3, 0.5]]}), encoding="utf-8")
        win._open_pipe_path(str(pj))
        assert pm.mode == "pipeline" and ed.toPlainText().startswith("median")
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 12. 選んだ行だけ実行(直前の実行の名前空間で)                                   #
# --------------------------------------------------------------------------- #
def test_12_run_selected_lines_in_the_last_namespace(tmp_path, monkeypatch):
    from PySide6 import QtCore, QtGui
    win, model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        _set_text(win, "# python\nk = 3\nshow(img)\nk2 = k * 10\n")
        _run_f5(win)
        pm.namespace["k"] = 5                                            # 直前の名前空間の値を使う
        blk = ed.document().findBlockByNumber(3)
        c = QtGui.QTextCursor(blk)
        c.movePosition(QtGui.QTextCursor.EndOfBlock, QtGui.QTextCursor.KeepAnchor)
        ed.setTextCursor(c)
        win._actions["run_selection"].trigger()
        assert pm.wait_idle(5)
        assert pm.namespace["k2"] == 50 and pm.var_source.ns["k2"] == 50
        assert "ran lines 4" in win._program["status"]().text()
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# 13. 終了して起動し直す → モード・ファイル・カーソル・ブレークポイント・ウォッチ       #
# --------------------------------------------------------------------------- #
def test_13_restart_restores_the_session(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch, name="keep.ini")
    p = tmp_path / "keep.py"
    p.write_text("# python\na = 1\nb = a + 1\nshow(img)\n", encoding="utf-8")
    try:
        pm = win._pymode
        monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *_a: True)
        pm.open_program(str(p))
        _run_f5(win)                                                     # 確認して実行(覚える)
        pm.toggle_breakpoint(3)
        pm.set_condition(3, "a == 1")
        pm.vars.watch.add_expression("a + b")
        win._program["edit"].goto_line(3)
        pm.set_config("release")
    finally:
        _close(win)
    win2, _m = _launch(tmp_path, monkeypatch, name="keep.ini")
    try:
        pm2 = win2._pymode
        ed2 = win2._program["edit"]
        assert pm2.mode == "python" and pm2.file == str(p) and pm2.config == "release"
        assert ed2.toPlainText() == p.read_text(encoding="utf-8")
        assert ed2.textCursor().blockNumber() + 1 == 3
        assert ed2.breakpoints == {3} and pm2.conditions == {3: "a == 1"}
        assert pm2.vars.watch.watch.exprs == ["a + b"]
        asked = []
        monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *_a: asked.append(1) or True)
        assert _run_f5(win2).ok and not asked                            # 確認済みの同じ中身: 聞かない
        win2._actions["pymode_toggle"].trigger()
    finally:
        _close(win2)
    win3, _m = _launch(tmp_path, monkeypatch, name="keep.ini")
    try:
        assert win3._pymode.mode == "pipeline"                           # 前回のまま(パイプラインで終えた)
    finally:
        _close(win3)


# --------------------------------------------------------------------------- #
# 入口(UX 規則 §1)・言語                                                       #
# --------------------------------------------------------------------------- #
_NEW_ACTIONS = ("pymode_python", "pymode_pipeline", "pymode_toggle", "pymode_convert", "pymode_debug",
                "pymode_release", "pymode_config_toggle", "pymode_example", "pymode_clear_output", "pymode_new",
                "pymode_open", "pymode_save", "pymode_save_as", "pymode_run", "pymode_step", "pymode_stop",
                "pymode_breakpoint", "pymode_condition")


def test_entries_menus_palette_and_keys(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        acts = win._actions
        for k in _NEW_ACTIONS:
            assert k in acts, k
            assert studio.PALETTE_WORDS.get(k), "no palette aliases for %s" % k
        menu_texts = {a.text() for m in win._menus.values() for a in m.actions()}
        for k in _NEW_ACTIONS:
            assert acts[k].text() in menu_texts, k
        assert acts["pymode_stop"].shortcut().toString() == "Ctrl+F2"
        assert acts["pymode_breakpoint"].shortcut().toString() == "F9"
        keys = [a.shortcut().toString() for a in win.findChildren(studio_qt_action()) if a.shortcut().toString()]
        dup = sorted({k for k in keys if keys.count(k) > 1} & {"Ctrl+F2", "F9", "Ctrl+N", "Ctrl+Alt+O", "Ctrl+Alt+S",
                                                              "Ctrl+Alt+M", "Ctrl+Alt+D", "Ctrl+Alt+Shift+S"})
        assert not dup, dup
    finally:
        _close(win)


def studio_qt_action():
    from PySide6 import QtGui
    return QtGui.QAction


def _pymode_strings():
    """studio_pymode.py の画面の文(tr(...)・入口の名前と説明)を構文木から集める。"""
    import ast
    src = open(os.path.join(os.path.dirname(studio.__file__), "studio_pymode.py"), encoding="utf-8").read()
    out = set()
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
        args = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if name in ("tr", "_ptr") and args:
            out.add(args[0])
        elif name == "mk" and len(node.args) >= 4:
            for a in (node.args[1], node.args[3]):
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    out.add(a.value)
    out |= {"The last mode", "Python mode", "Pipeline mode", "Program mode", "Start Studio in"}
    return out


def test_new_strings_have_six_languages():
    keys = _pymode_strings()
    data = json.load(open(os.path.join(os.path.dirname(studio.__file__), "studio_assets", "i18n.json"),
                          encoding="utf-8"))
    strings = data["strings"]
    missing = [k for k in sorted(keys)
               if not strings.get(k) or any(not str(strings[k].get(l, "")).strip()
                                            for l in ("ja", "zh", "tw", "ko", "de", "hi"))]
    assert not missing, missing
    assert len(keys) >= 60


def test_japanese_ui_has_no_english_left_in_the_mode_bar(tmp_path, monkeypatch):
    win, model = _launch(tmp_path, monkeypatch)
    try:
        studio._UI_LANG["code"] = "ja"
        pm = win._pymode
        pm.retranslate()
        for w in (pm.btn_pipe, pm.btn_run, pm.btn_stop, pm.btn_step, pm.mode_note, pm.output_title):
            assert not w.text().isascii(), w.text()
    finally:
        _close(win)

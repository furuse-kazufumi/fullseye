# -*- coding: utf-8 -*-
"""Studio の Python のモード: 第 3 回の独立レビュー(2026-11-13)の指摘 S1〜S9 の回帰試験。

* S1: 「選んだ行を実行」(``studio_program.evaluate``)も、F5 と同じ 1 つの入口(``_guarded_user_call``)を通る。
  作業スレッドからの Qt の import を断り、import の見張り・プロセスの状態の取り戻し・残した実行の後始末が付く。
  窓を出す backend で作られた matplotlib の図が残っていても、次の実行は Agg で描く。
* S2: 信頼は文面の SHA-256 に結び付く(変換・移す → Ctrl+Z で、確認していないファイルの文面が確認なしに走らない)。
* S3: 保存・自動保存は、ディスクの生のバイトの SHA-256 と大きさで「外で変わったか」を決める(読めない・解けない・
  大きすぎる時は「変わった」)。
* S4: 補完・ホバー・シグネチャが利用者のコードを呼ばない型は、許す型の一覧で決める(包みの型は中身まで見る)。
* S5: パイプラインのファイルを開いたら、未適用の編集の状態を全部消す。
* S6: 信頼の確認と従来のエディタのタブを閉じる窓は、既定のボタンがキャンセル側。
* S7: import の見張りは、相対 import と ``importlib.__import__`` も見る。
* S8: object の配列を ``show()`` しても、モーダルの窓は出ない。

**固まりうる試験は子プロセス + 時間の上限で回す**(作業スレッドに Qt の窓ができると、閉じた所で GIL を持ったまま
止まり、pytest ごと固まる。固まり = 失敗として数え、時間切れで CI を止めない)。
"""
import ast
import json
import os
import subprocess
import sys
import threading
import time

import numpy as np
import pytest

import studio
import studio_program as sp
import studio_pymode as pm_mod

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = np.zeros((16, 16))


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


def _launch(tmp_path, monkeypatch, start_mode="python", time_limit=None):
    _app()
    ini = tmp_path / "s.ini"
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(ini))
    if time_limit is not None:
        from PySide6 import QtCore
        s = QtCore.QSettings(str(ini), QtCore.QSettings.IniFormat)
        s.setValue("pymode/time_limit_s", time_limit)
        s.sync()
    win, model = studio.build_window(start_mode=start_mode)
    win.resize(1400, 860)
    win.show()
    _pump(0.3)
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
    _pump(0.35)


def _select_lines(win, first, last):
    """1 始まりの行 *first*〜*last* を選ぶ。"""
    from PySide6 import QtGui
    ed = win._program["edit"]
    doc = ed.document()
    c = QtGui.QTextCursor(doc.findBlockByNumber(first - 1))
    end = doc.findBlockByNumber(last - 1)
    c.setPosition(end.position() + max(0, end.length() - 1), QtGui.QTextCursor.KeepAnchor)
    ed.setTextCursor(c)


def _run(win, timeout=20):
    pm = win._pymode
    assert pm.run() is True
    assert pm.wait_idle(timeout)
    _pump(0.1)
    return pm.last


def _run_selection(win, first, last, timeout=20):
    pm = win._pymode
    _select_lines(win, first, last)
    assert pm.run_selection() is True
    assert pm.wait_idle(timeout)
    _pump(0.1)


def _output(win) -> str:
    return win._pymode.output.toPlainText()


#: 子プロセスの先頭: Studio の窓を作る道具(親と同じ物)。結果は ``RESULT <JSON>`` の 1 行で返す。
_CHILD_HEAD = r'''
import json, os, sys, threading, time, faulthandler
faulthandler.dump_traceback_later(int(os.environ["S3_CHILD_DUMP_S"]), exit=True)
sys.path.insert(0, os.environ["S3_ROOT"])
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import numpy as np
OUT = {}
def step(name):
    print("STEP " + name, flush=True)
def done():
    print("RESULT " + json.dumps(OUT, default=str), flush=True)
def pump(sec=0.3):
    from PySide6 import QtWidgets
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)
def launch(time_limit=5):
    from PySide6 import QtCore, QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    s = QtCore.QSettings(os.environ["FULLSEYE_STUDIO_SETTINGS"], QtCore.QSettings.IniFormat)
    s.setValue("pymode/time_limit_s", time_limit)
    s.sync()
    import studio
    win, model = studio.build_window(start_mode="python")
    win.resize(1400, 860)
    win.show()
    pump(0.3)
    return win
def close(win):
    win.close_guard = lambda: True
    win.quiesce()
    win.close()
    pump(0.1)
def set_text(win, text):
    from PySide6 import QtGui
    ed = win._program["edit"]
    c = QtGui.QTextCursor(ed.document())
    c.select(QtGui.QTextCursor.Document)
    c.insertText(text)
    ed.setTextCursor(c)
    pump(0.35)
def select_lines(win, first, last):
    from PySide6 import QtGui
    ed = win._program["edit"]
    doc = ed.document()
    c = QtGui.QTextCursor(doc.findBlockByNumber(first - 1))
    end = doc.findBlockByNumber(last - 1)
    c.setPosition(end.position() + max(0, end.length() - 1), QtGui.QTextCursor.KeepAnchor)
    ed.setTextCursor(c)
def wait(pm, sec=15):
    t0 = time.monotonic()
    while pm.running and time.monotonic() - t0 < sec:
        pump(0.05)
    pump(0.2)
    return not pm.running
def widgets_off_gui():
    from PySide6 import QtWidgets
    gui = QtWidgets.QApplication.instance().thread()
    return sorted(set(type(w).__name__ for w in QtWidgets.QApplication.allWidgets() if w.thread() is not gui))
'''


def _child(tmp_path, body: str, timeout: int = 150) -> dict:
    """*body* を子プロセスで回し、``RESULT`` の行の JSON を返す。*timeout* 秒で終わらなければ殺して**失敗**にする
    (固まった時は、最後に通った ``STEP`` と、子が自分で書いたスレッドの写しを失敗の文に出す)。"""
    script = tmp_path / "child.py"
    script.write_text(_CHILD_HEAD + body, encoding="utf-8")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONUTF8="1", PYTHONUNBUFFERED="1", S3_ROOT=ROOT,
               S3_CHILD_DUMP_S=str(max(10, timeout - 30)), FULLSEYE_STUDIO_SETTINGS=str(tmp_path / "child.ini"))
    env.pop("MPLBACKEND", None)
    p = subprocess.Popen([sys.executable, str(script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                         cwd=str(tmp_path))
    try:
        out, err = p.communicate(timeout=timeout)
        hung = False
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate()
        hung = True
    out, err = out.decode("utf-8", "replace"), err.decode("utf-8", "replace")
    steps = [ln[5:] for ln in out.splitlines() if ln.startswith("STEP ")]
    results = [ln[7:] for ln in out.splitlines() if ln.startswith("RESULT ")]
    where = err.find("Thread 0x")
    tail = err[where:where + 1500] if where >= 0 else err[-1500:]
    assert not hung, "the child did not finish in %d s (hang) after step %r\n%s" % (timeout, steps[-1:], tail)
    assert results, "the child ended (exit %s) without a result after step %r\n%s" % (p.returncode, steps[-1:], tail)
    return json.loads(results[-1])


# --------------------------------------------------------------------------- #
# S1: 「選んだ行を実行」も F5 と同じ 1 つの入口を通る                              #
# --------------------------------------------------------------------------- #
def test_s1_every_run_of_user_code_goes_through_the_one_guarded_door():
    """源の側から数える: 見張りつきで利用者のコードを回す所(``_run_with_watchdog``)は ``_guarded_user_call`` の中の
    1 か所だけで、``run_program``(F5・続行・1 行実行)と ``evaluate``(選んだ行)はどちらもそこを通る。"""
    with open(os.path.join(ROOT, "studio_program.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}

    def calls(fn, name):
        return [c for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                and c.func.id == name]
    watchdog_callers = sorted(n for n, f in funcs.items() if calls(f, "_run_with_watchdog"))
    assert watchdog_callers == ["_guarded_user_call"], watchdog_callers
    door = funcs["_guarded_user_call"]
    for part in ("_refusal", "_ImportGuard", "_restore_when_done", "_push_sys_path", "_pop_sys_path"):
        assert len(calls(door, part)) == 1, part
    takes = [c for c in ast.walk(door) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
             and c.func.attr in ("take", "restore", "install", "uninstall")]
    assert sorted(c.func.attr for c in takes) == ["install", "restore", "take", "uninstall"]
    for entrance in ("run_program", "evaluate"):
        assert len(calls(funcs[entrance], "_guarded_user_call")) == 1, entrance
    refusal = funcs["_refusal"]
    for part in ("abandoned_runs", "_stray_value_threads", "needs_gui_thread"):
        assert len(calls(refusal, part)) == 1, part


def test_s1_the_selection_puts_the_process_state_back_like_f5(tmp_path):
    """探針 r04 c: 選んだ行が変えた sys.stdout / excepthook / 再帰の上限 / 環境変数 / 作業フォルダが Studio に残った。"""
    r = sp.run_program("# python\nx = 1\n", IMG)
    assert r.ok
    out0, hook0, rl0, cwd0 = sys.stdout, sys.excepthook, sys.getrecursionlimit(), os.getcwd()
    os.environ.pop("S1_SEL", None)
    src = ("import sys, os, io\nsys.stdout = io.StringIO()\nsys.excepthook = lambda *a: None\n"
           "sys.setrecursionlimit(sys.getrecursionlimit() + 123)\nos.environ['S1_SEL'] = 'left by the selection'\nos.chdir(r'%s')\ny = 2\n"
           % str(tmp_path))
    try:
        for kw in ({"time_limit_s": 10.0}, {}):                        # 見張りつき(選んだ行)と、上限なしの呼び出し
            e = sp.evaluate(src, r, **kw)
            assert e["error"] is None and r.namespace["y"] == 2
            left = {"sys.stdout": sys.stdout is not out0, "sys.excepthook": sys.excepthook is not hook0,
                    "recursion limit": sys.getrecursionlimit() != rl0, "env": os.environ.get("S1_SEL"),
                    "cwd": os.getcwd() != cwd0}
            assert left == {"sys.stdout": False, "sys.excepthook": False, "recursion limit": False, "env": None,
                            "cwd": False}, left
            notes = [n for n in e["notes"] if n.startswith("restored after the run: ")]
            assert len(notes) == 1
            for name in ("os.environ", "cwd", "sys.stdout", "sys.excepthook", "recursion limit"):
                assert name in notes[0], (name, notes)
    finally:
        sys.stdout, sys.excepthook = out0, hook0
        sys.setrecursionlimit(rl0)
        os.chdir(cwd0)
        os.environ.pop("S1_SEL", None)


def test_s1_the_selection_is_refused_while_a_value_helper_thread_is_left(monkeypatch):
    """F5 と同じ断り(R5): 変数の欄の ``__repr__`` 用のスレッドが残っている間は、選んだ行も始めない。"""
    r = sp.run_program("# python\nx = 1\n", IMG)
    monkeypatch.setattr(sp, "_stray_value_threads", lambda: 2)
    e = sp.evaluate("x = 5", r, time_limit_s=5.0)
    assert e["error"] == sp.STRAY_BLOCKS_RUN % 2 and r.namespace["x"] == 1
    e = sp.evaluate("x = 5", r)
    assert e["error"] == sp.STRAY_BLOCKS_RUN % 2 and r.namespace["x"] == 1
    assert sp.run_program("# python\nx = 1\n", IMG).errors == [sp.STRAY_BLOCKS_RUN % 2]


def test_s1_a_selection_that_cannot_be_stopped_is_put_back_when_it_ends():
    """F5 と同じ後始末(H3): 止められずに残した「選んだ行」が後から変えた環境も、終わった所で戻す。その間は次を断る。"""
    import builtins
    r = sp.run_program("# python\nx = 1\n", IMG)
    imp0 = builtins.__import__
    for k in ("S1_EARLY", "S1_LATE"):
        os.environ.pop(k, None)
    try:
        e = sp.evaluate("import os, time\nos.environ['S1_EARLY'] = '1'\ntry:\n    time.sleep(3.0)\n"
                        "except BaseException:\n    pass\nos.environ['S1_LATE'] = '1'\n", r, time_limit_s=0.2)
        assert e["error"].startswith("could not stop the selected lines")
        assert len(sp.abandoned_runs()) == 1
        assert os.environ.get("S1_EARLY") is None                       # 諦めた所で 1 回戻す
        assert sp.evaluate("x = 2", r, time_limit_s=5.0)["error"] == sp.ABANDONED_BLOCKS_RUN % 1
        assert builtins.__import__ is not imp0                          # 残した実行が生きている間、見張りは付けたまま
        end = time.monotonic() + 15
        while sp.abandoned_runs() and time.monotonic() < end:
            time.sleep(0.05)
        assert sp.abandoned_runs() == []
        assert os.environ.get("S1_LATE") is None and os.environ.get("S1_EARLY") is None
        assert builtins.__import__ is imp0
        assert sp.evaluate("x = 2", r, time_limit_s=5.0)["error"] is None and r.namespace["x"] == 2
    finally:
        end = time.monotonic() + 15                                     # 残した実行を次の試験へ持ち越さない
        while sp.abandoned_runs() and time.monotonic() < end:
            time.sleep(0.05)
        for k in ("S1_EARLY", "S1_LATE"):
            os.environ.pop(k, None)


def test_s1_the_selection_uses_its_own_time_limit_not_the_one_of_the_last_release_run():
    """Release の実行が記録に残した時間の上限が、後の「選んだ行」の op の呼び出しを「時間切れ」で止めていた。"""
    r = sp.run_program("# python\ng = gaussian(img, 0.3)\n", IMG, config="release", time_limit_s=0.3)
    assert r.ok
    time.sleep(0.5)                                                     # 前の実行の上限は過ぎた
    e = sp.evaluate("h = gaussian(img, 0.4)", r, time_limit_s=10.0)
    assert e["error"] is None and [c.op for c in e["calls"]] == ["gaussian"]
    e = sp.evaluate("h = gaussian(img, 0.5)", r)
    assert e["error"] is None and [c.op for c in e["calls"]] == ["gaussian"]
    stop = threading.Event()
    stop.set()                                                          # 自分の停止の要求は op の境目でも効く
    assert sp.evaluate("h = gaussian(img, 0.6)", r, stop_event=stop)["error"].startswith("stopped")


def test_s1_the_selection_in_the_window_is_restored_and_says_so(tmp_path, monkeypatch):
    """窓で: 選んだ行が変えた作業フォルダは戻り、出力の欄に「戻した」と出る。止まっている間の選んだ行も同じ。"""
    win, _model = _launch(tmp_path, monkeypatch, time_limit=10)
    cwd0 = os.getcwd()
    os.environ.pop("S1_WIN", None)
    try:
        pm = win._pymode
        _set_text(win, "# python\nx = 1\nimport os\nos.chdir(r'%s')\nos.environ['S1_WIN'] = 'sel'\ny = x + 1\n"
                  % str(tmp_path))
        pm.edit.breakpoints = {6}
        assert pm.run() is True
        end = time.monotonic() + 15
        while pm.session is None and time.monotonic() < end:
            _pump(0.05)
        assert pm.session is not None and pm.session.live              # 6 行目で止まって待っている
        paused_cwd = os.getcwd()
        _set_text(win, pm.edit.toPlainText() + "os.environ['S1_WIN'] = 'paused sel'\n")
        _run_selection(win, 7, 7)
        assert os.environ.get("S1_WIN") == "sel" and os.getcwd() == paused_cwd      # 止まっている実行の状態に戻る
        assert "restored after the run: os.environ" in _output(win)
        pm.stop()
        _pump(0.3)
        assert os.getcwd() == cwd0 and os.environ.get("S1_WIN") is None
        _set_text(win, "# python\nx = 1\nimport os\nos.chdir(r'%s')\n" % str(tmp_path))
        _run(win)
        pm.output.clear()
        _run_selection(win, 3, 4)
        assert os.getcwd() == cwd0
        assert "restored after the run: cwd" in _output(win)
    finally:
        os.chdir(cwd0)
        os.environ.pop("S1_WIN", None)
        _close(win)


def test_s1_qt_and_matplotlib_from_the_selection_do_not_reach_the_worker_thread(tmp_path):
    """探針 r04 a / b・r04b・r04c・r04d(子プロセス + 時間の上限): 選んだ行が作業スレッドで QLabel や QtAgg の図を
    作り、``plt.close('all')`` で Studio 全体が固まった。選んだ行で plot を試してから F5 しても固まった。"""
    pytest.importorskip("matplotlib")
    got = _child(tmp_path, r'''
win = launch()
pm = win._pymode
def base():
    set_text(win, "x = 1\n")
    pm.run(); assert wait(pm)
def selection(text, first, last):
    base()
    set_text(win, text)
    select_lines(win, first, last)
    pm.output.clear()
    ok = pm.run_selection()
    finished = wait(pm)
    return {"started": ok, "finished": finished, "output": pm.output.toPlainText()[-900:], "ns": sorted(
        k for k in (pm.namespace or {}) if k in ("w", "fig", "f", "after", "b", "c"))}

step("a: a Qt widget from the selection")
OUT["a"] = selection("x = 1\nfrom PySide6 import QtWidgets\nw = QtWidgets.QLabel('made by a selection')\n", 2, 3)
OUT["a_widgets"] = widgets_off_gui()

step("b: matplotlib.use('QtAgg') + plt.figure() from the selection")
OUT["b"] = selection("x = 1\nimport matplotlib\nmatplotlib.use('QtAgg', force=True)\n"
                     "import matplotlib.pyplot as plt\nfig = plt.figure()\n", 2, 5)
OUT["b_widgets"] = widgets_off_gui()

step("r04b: QtAgg + a figure window + plt.close('all') from the selection")
OUT["r04b"] = selection("x = 1\nimport matplotlib\nmatplotlib.use('QtAgg')\nimport matplotlib.pyplot as plt\n"
                        "f = plt.figure()\nw = f.canvas.manager.window\nw.show()\nplt.close('all')\nafter = 1\n", 2, 9)
OUT["r04b_widgets"] = widgets_off_gui()

step("r04c: plain plt.plot + plt.show from the selection")
OUT["r04c"] = selection("x = 1\nimport matplotlib.pyplot as plt\nb = plt.get_backend()\nplt.plot([1, 2, 3])\n"
                        "c = type(plt.gcf().canvas).__name__\nplt.show()\nafter = 1\n", 2, 7)
OUT["r04c_values"] = {k: str((pm.namespace or {}).get(k)) for k in ("b", "c", "after")}
shown = win._state.get("raw")
OUT["r04c_shown"] = [type(shown).__name__, list(getattr(shown, "shape", ()))]
OUT["r04c_widgets"] = widgets_off_gui()

step("r04d: F5 of plt.figure() + plt.close('all') after the selection")
set_text(win, "import matplotlib, matplotlib.pyplot as plt\nb = matplotlib.get_backend()\nf = plt.figure()\n"
              "c = type(f.canvas).__name__\nplt.close('all')\nafter = 2\n")
pm.output.clear()
OUT["r04d_started"] = pm.run()
OUT["r04d_finished"] = wait(pm)
OUT["r04d_errors"] = list(pm.last.errors) if pm.last is not None else None
OUT["r04d_values"] = {k: str((pm.namespace or {}).get(k)) for k in ("b", "c", "after")}
OUT["r04d_widgets"] = widgets_off_gui()

step("the next F5 still runs")
set_text(win, "print('next F5')\n")
pm.run(); OUT["next_finished"] = wait(pm)
OUT["next_output"] = pm.output.toPlainText()[-200:]
close(win)
done()
''')
    a = got["a"]
    assert a["started"] and a["finished"]
    assert "not run: this program imports Qt directly" in a["output"] and "line 2" in a["output"], a["output"]
    assert a["ns"] == [] and got["a_widgets"] == []
    b = got["b"]
    assert b["finished"] and "Studio does not let a running program import" in b["output"], b["output"]
    assert "fig" not in b["ns"] and got["b_widgets"] == []
    c = got["r04b"]
    assert c["finished"] and "Studio does not let a running program import" in c["output"], c["output"]
    assert c["ns"] == [] and got["r04b_widgets"] == []
    d = got["r04c"]
    assert d["finished"] and "set_wakeup_fd" not in d["output"] and "✕" not in d["output"], d["output"]
    assert got["r04c_values"]["b"].lower() == "agg" and got["r04c_values"]["c"] == "FigureCanvasAgg"
    assert got["r04c_values"]["after"] == "1"
    assert "the figure was put in the image pane" in d["output"]
    assert got["r04c_shown"][0] == "ndarray" and len(got["r04c_shown"][1]) == 3 and got["r04c_shown"][1][2] == 3
    assert got["r04c_widgets"] == []
    assert got["r04d_started"] and got["r04d_finished"] and got["r04d_errors"] == []
    assert got["r04d_values"] == {"b": "agg", "c": "FigureCanvasAgg", "after": "2"} or \
        got["r04d_values"] == {"b": "Agg", "c": "FigureCanvasAgg", "after": "2"}, got["r04d_values"]
    assert got["r04d_widgets"] == []
    assert got["next_finished"] and "next F5" in got["next_output"]


def test_s1_a_figure_left_on_a_window_backend_does_not_put_the_next_run_on_that_backend(tmp_path):
    """探針 r04d の中身(子プロセス + 時間の上限): 窓を出す backend の図が 1 つ残っていると、import の見張りは
    matplotlib を Agg にせず、次の F5 の ``plt.figure()`` が作業スレッドで Qt の窓を作った(閉じた所で固まる)。"""
    pytest.importorskip("matplotlib")
    got = _child(tmp_path, r'''
from PySide6 import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import studio_program as sp
left = plt.figure()                                   # GUI(main)スレッドで作った、窓つきの図
OUT["left_canvas"] = type(left.canvas).__name__
OUT["fignums_before"] = list(plt.get_fignums())
step("run a program that draws and closes all figures")
r = sp.run_program("# python\nimport matplotlib, matplotlib.pyplot as plt\nb = matplotlib.get_backend()\n"
                   "n = len(plt.get_fignums())\nf = plt.figure()\nc = type(f.canvas).__name__\nplt.plot([1, 2])\n"
                   "plt.show()\nplt.close('all')\nafter = 1\n", np.zeros((8, 8)), time_limit_s=20)
OUT["errors"] = r.errors
OUT["values"] = {k: str(r.values.get(k)) for k in ("b", "n", "c", "after")}
OUT["notes"] = r.notes
OUT["output"] = [type(r.output).__name__, list(getattr(r.output, "shape", ()))]
gui = app.thread()
OUT["widgets_off_gui"] = sorted(set(type(w).__name__ for w in QtWidgets.QApplication.allWidgets()
                                    if w.thread() is not gui))
import shiboken6
OUT["left_window_alive"] = bool(shiboken6.isValid(left.canvas.manager.window))   # 消されていない
OUT["fignums_after"] = list(plt.get_fignums())
step("a second run has nothing left to detach")
r2 = sp.run_program("# python\nimport matplotlib.pyplot as plt\nf = plt.figure()\nplt.close('all')\n",
                    np.zeros((8, 8)), time_limit_s=20)
OUT["errors2"], OUT["notes2"] = r2.errors, r2.notes
done()
''')
    assert got["left_canvas"] == "FigureCanvasQTAgg" and got["fignums_before"] == [1]
    assert got["errors"] == [], got["errors"]
    assert got["values"]["b"].lower() == "agg" and got["values"]["c"] == "FigureCanvasAgg", got["values"]
    assert got["values"]["n"] == "0" and got["values"]["after"] == "1"          # 残っていた図は pyplot の一覧から外れた
    assert got["widgets_off_gui"] == [] and got["left_window_alive"] is True
    assert got["fignums_after"] == []
    assert got["output"][0] == "ndarray" and len(got["output"][1]) == 3
    detached = [n for n in got["notes"] if n == sp.MPL_DETACHED_NOTE % 1]
    assert len(detached) == 1 and sp.MPL_SHOWN_NOTE in got["notes"], got["notes"]
    assert got["errors2"] == [] and [n for n in got["notes2"] if "pyplot" in n] == []


# --------------------------------------------------------------------------- #
# S7: import の見張りは、相対 import と importlib.__import__ も見る               #
# --------------------------------------------------------------------------- #
_S7_DOORS = {
    "relative import of the package": "__package__ = 'PySide6'\nfrom . import QtWidgets\n",
    "relative import of a submodule": "__package__ = 'PySide6'\nfrom .QtWidgets import QLabel\n",
    "relative import two levels up": "__package__ = 'PySide6.QtCore'\nfrom .. import QtWidgets\n",
    "relative import by __name__": "__name__ = 'PySide6.mine'\nfrom . import QtWidgets\n",
    "relative import of a matplotlib window backend": "__package__ = 'matplotlib.backends'\nfrom . import backend_qtagg\n",
    "importlib.__import__": "import importlib\nm = importlib.__import__('PySide6.QtWidgets', fromlist=['QLabel'])\n",
    "importlib.__import__ of a name in fromlist": "import importlib\nm = importlib.__import__('PySide6', "
                                                  "fromlist=['QtWidgets'])\n",
    "importlib.__import__ relative": "import importlib\nm = importlib.__import__('QtWidgets', {'__package__': "
                                     "'PySide6'}, None, ['QLabel'], 1)\n",
}


@pytest.mark.parametrize("door", sorted(_S7_DOORS))
def test_s7_relative_imports_and_importlib_import_are_refused_on_the_worker_thread(door, monkeypatch):
    """探針 r06 7a / 7b: 見張りは ``level != 0`` の import と ``importlib.__import__`` を見ていなかった
    (作業スレッドで QLabel が作られた)。ここでは import だけを試す(窓は作らない)。"""
    import builtins
    import importlib
    monkeypatch.setattr(sp, "GUI_BRIDGE", None)
    before = (builtins.__import__, importlib.import_module, importlib.__import__)
    r = sp.run_program("# python\nx = 1\n" + _S7_DOORS[door] + "after = 1\n", IMG)
    assert not r.ok and len(r.errors) == 1
    assert "ImportError: Studio does not let a running program import" in r.errors[0], r.errors
    assert r.values["x"] == 1 and "after" not in r.values and "m" not in r.values and "QtWidgets" not in r.values
    assert (builtins.__import__, importlib.import_module, importlib.__import__) == before   # 見張りは実行の間だけ
    e = sp.evaluate(_S7_DOORS[door] + "after = 1\n", sp.run_program("# python\nx = 1\n", IMG), time_limit_s=10.0)
    assert e["error"] and "Studio does not let a running program import" in e["error"], e   # 選んだ行でも同じ
    assert (builtins.__import__, importlib.import_module, importlib.__import__) == before


def test_s7_ordinary_relative_imports_and_importlib_import_still_work(tmp_path, monkeypatch):
    """断るのは GUI の部品だけ: 利用者のパッケージの中の相対 import と、``importlib.__import__`` の普通の使い方は通る。"""
    monkeypatch.setattr(sp, "GUI_BRIDGE", None)
    pkg = tmp_path / "s7pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("from . import helper\nfrom .helper import twice\nfrom .sub import deep\n",
                                     encoding="utf-8")
    (pkg / "helper.py").write_text("def twice(v):\n    return 2 * v\n", encoding="utf-8")
    sub = pkg / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("from .. import helper as up\ndeep = up.twice(4)\n", encoding="utf-8")
    prog = tmp_path / "main.py"
    text = ("# python\nimport importlib\nimport s7pkg\na = s7pkg.twice(3)\nb = s7pkg.deep\n"
            "j = importlib.__import__('json').dumps([1])\nk = importlib.__import__('os.path', fromlist=['join']).sep\n")
    prog.write_text(text, encoding="utf-8")
    r = sp.run_program(text, IMG, filename=str(prog))
    assert r.ok, r.errors
    assert r.values["a"] == 6 and r.values["b"] == 8 and r.values["j"] == "[1]" and r.values["k"] == os.sep
    assert "s7pkg" not in sys.modules                                     # 利用者のモジュールは実行の後に外す


# --------------------------------------------------------------------------- #
# S2: 信頼は文面に結び付く(変換・移す → Ctrl+Z)                                  #
# --------------------------------------------------------------------------- #
def _marker_program(tmp_path, name):
    """走ったら印のファイルを書く .py(確認していないコードが走ったかを、印の有無で見る)。"""
    mark = tmp_path / ("MARK_" + name)
    p = tmp_path / (name + ".py")
    p.write_text("open(r'%s', 'w').write('ran')\nprint('X ran')\n" % str(mark), encoding="utf-8")
    return p, mark


def _trust_hooks(monkeypatch, answer):
    asked = []
    monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *a: asked.append(a[2]) or answer)
    monkeypatch.setattr(pm_mod, "SAVE_HOOK", lambda *a: "discard")
    return asked


@pytest.mark.parametrize("how", ["convert", "move"])
@pytest.mark.parametrize("then", ["undo", "undo and edit", "undo, redo, undo"])
def test_s2_undo_after_convert_or_move_does_not_run_an_unconfirmed_file_without_asking(how, then, tmp_path, monkeypatch):
    """探針 r02 a / b: X.py を開く(未確認)→ パイプラインのモードで打つ →「Python に変換」か札の「Python の
    モードへ移す」→ Ctrl+Z で X の文面が戻る → F5。確認の窓が出ずに X が走った。Ctrl+Z の後に 1 字直しても同じ。"""
    asked = _trust_hooks(monkeypatch, False)
    win, _model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        path, mark = _marker_program(tmp_path, "x_" + how)
        assert pm.open_program(str(path)) is True
        x_text = ed.toPlainText()
        assert pm.origin == "file" and pm.session_trusted is False
        pm.set_mode("pipeline")
        if how == "convert":
            _set_text(win, "gaussian (0.5, 0.5)\n")
            assert pm.convert_to_python() is True
        else:
            _set_text(win, "k = 1\nprint(k)\n")
            pm.update_badge()
            assert pm.move_text_to_python() is True
        assert pm.active and ed.toPlainText() != x_text
        ed.undo()
        _pump(0.1)
        assert ed.toPlainText() == x_text                                # Ctrl+Z で X の文面が戻った
        if then == "undo and edit":
            _set_text(win, x_text + "# one more line\n")
        elif then == "undo, redo, undo":
            ed.redo()
            _pump(0.1)
            assert ed.toPlainText() != x_text
            ed.undo()
            _pump(0.1)
            assert ed.toPlainText() == x_text
        assert pm.origin == "file" and pm.session_trusted is False       # 由来と信頼も、X の物に戻る
        assert pm.run() is False
        _pump(0.2)
        assert len(asked) == 1 and str(path) in asked[0]                  # 確認の窓が出て、どのファイルから来たかを言う
        assert not mark.exists() and "X ran" not in _output(win)
        assert "was not confirmed" in _output(win)
        _select_lines(win, 1, 1)
        assert pm.run_selection() is False                                # 選んだ行でも同じ
        assert len(asked) == 2 and not mark.exists()
    finally:
        _close(win)


def test_s2_confirming_once_is_remembered_and_typed_text_is_never_asked_about(tmp_path, monkeypatch):
    """確認すれば走る。確認した後は、Undo / Redo で同じ文面に戻っても聞き直さない。自分で打った文面の変換は聞かない。"""
    asked = _trust_hooks(monkeypatch, True)
    win, _model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        # 自分で打った文面 → パイプラインのモードで打つ → 変換 → Ctrl+Z → F5: 聞かない
        _set_text(win, "# python\nmine = 1\n")
        pm.set_mode("pipeline")
        _set_text(win, "gaussian (0.5, 0.5)\n")
        assert pm.convert_to_python() is True
        ed.undo()
        _pump(0.1)
        assert ed.toPlainText() == "# python\nmine = 1\n"
        res = _run(win)
        assert res.ok and asked == [] and pm.origin == "typed"
        # ファイル → 変換 → Ctrl+Z → F5: 1 回聞き、「実行する」で走る。その後は聞かない
        path, mark = _marker_program(tmp_path, "y")
        assert pm.open_program(str(path)) is True
        x_text = ed.toPlainText()
        pm.set_mode("pipeline")
        _set_text(win, "gaussian (0.5, 0.5)\n")
        assert pm.convert_to_python() is True
        converted = ed.toPlainText()
        res = _run(win)
        assert res.ok and asked == []                                    # 変換した文面は利用者が打った物: 聞かない
        ed.undo()
        _pump(0.1)
        assert ed.toPlainText() == x_text
        res = _run(win)
        assert len(asked) == 1 and res.ok and mark.exists()
        ed.redo()
        _pump(0.1)
        assert ed.toPlainText() == converted
        ed.undo()
        _pump(0.1)
        assert ed.toPlainText() == x_text
        mark.unlink()
        res = _run(win)
        assert len(asked) == 1 and res.ok and mark.exists()              # 確認済みの文面: 聞き直さない
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# S3: 「外で変わったか」は生のバイトで決める(読めない・解けない・大きすぎる = 変わった)  #
# --------------------------------------------------------------------------- #
class _Asker:
    """やり直しの効かない操作の確認の窓の差し替え: 聞かれた文を覚え、``answer`` を返す。"""

    def __init__(self, monkeypatch, answer=False):
        self.calls = []
        self.answer = answer
        monkeypatch.setattr(studio, "CONFIRM_ACTION_HOOK", self)

    def __call__(self, parent, title, text, action):
        self.calls.append((title, text, action))
        return self.answer


def _type_at_end(win, text):
    from PySide6 import QtGui
    ed = win._program["edit"]
    c = ed.textCursor()
    c.movePosition(QtGui.QTextCursor.End)
    c.insertText(text)
    ed.setTextCursor(c)
    _pump(0.05)


_S3_OUTSIDE = {
    "utf-8": "print('changed outside, utf-8 日本語')\n".encode("utf-8"),
    "cp932": "print('外で書き換えた (cp932)')\n".encode("cp932"),
    "latin-1": "print('geändert')\n".encode("latin-1"),
    "larger than 4 MB": ("#" + "あ" * 1_500_000 + "\nprint(1)\n").encode("utf-8"),
    "utf-16": "print('utf-16')\n".encode("utf-16"),
}


@pytest.mark.parametrize("kind", sorted(_S3_OUTSIDE))
def test_s3_a_file_changed_outside_is_never_overwritten_without_asking(kind, tmp_path, monkeypatch):
    """探針 r05 b / c / d: 外で cp932 で書き換えられた・4 MB を越えたファイルは「読めない = 変わっていない」になり、
    自動保存が聞かずに上書きし、保存(Ctrl+S)も聞かなかった。書き換えた中身は戻せない。"""
    ask = _Asker(monkeypatch, answer=False)
    monkeypatch.setattr(pm_mod, "SAVE_HOOK", lambda *_a: "discard")
    win, _model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        p = tmp_path / "a.py"
        p.write_bytes(b"print('original')\n")
        assert pm.open_program(str(p)) is True
        pm.set_autosave_file("idle", 0.5)
        _type_at_end(win, "# typed in Studio\n")
        outside = _S3_OUTSIDE[kind]
        p.write_bytes(outside)                                            # Studio の外の書き換え
        assert pm.disk_changed() is True
        assert pm.autosave_file("idle") is False and p.read_bytes() == outside
        assert "not autosaved" in pm.autosave_note.text()
        _pump(1.0)                                                        # 待っていた自動保存の時計が鳴っても同じ
        assert p.read_bytes() == outside
        assert pm.save() is False                                         # 保存は聞く。キャンセルなら書かない
        assert len(ask.calls) == 1 and "changed on disk" in ask.calls[0][1] and p.read_bytes() == outside
        ask.answer = True
        assert pm.save() is True and len(ask.calls) == 2                  # 「上書きする」と答えた時だけ書く
        assert p.read_bytes() == b"print('original')\n# typed in Studio\n"
        assert pm.disk_changed() is False and pm.save() is True and len(ask.calls) == 2
    finally:
        _close(win)


def test_s3_the_same_bytes_are_not_a_change_and_an_unreadable_file_is(tmp_path, monkeypatch):
    """同じ中身を書き直しただけなら「変わっていない」(自動保存は続く)。読めない時は「変わった」(上書きしない側)。
    外で消されたファイルは、保存で作り直す(上書きする相手が無い)。CRLF のファイルも、開いた時のバイトで比べる。"""
    ask = _Asker(monkeypatch, answer=False)
    monkeypatch.setattr(pm_mod, "SAVE_HOOK", lambda *_a: "discard")
    win, _model = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        p = tmp_path / "b.py"
        original = b"print('original')\r\nx = 1\r\n"
        p.write_bytes(original)
        assert pm.open_program(str(p)) is True
        pm.set_autosave_file("idle", 0.5)
        assert pm.disk_changed() is False
        p.write_bytes(original)                                           # 同じ中身の書き直し
        assert pm.disk_changed() is False
        _type_at_end(win, "# mine\n")
        assert pm.autosave_file("idle") is True and b"# mine" in p.read_bytes()
        assert pm.disk_changed() is False                                 # 自分で書いた中身
        _type_at_end(win, "# more\n")
        real = getattr(pm_mod, "_file_stamp", None)
        monkeypatch.setattr(pm_mod, "_file_stamp", lambda path: None, raising=False)   # 読めない(権限・壊れた媒体)
        assert pm.disk_changed() is True
        assert pm.autosave_file("idle") is False and b"# more" not in p.read_bytes()
        assert pm.save() is False and len(ask.calls) == 1 and b"# more" not in p.read_bytes()
        monkeypatch.setattr(pm_mod, "_file_stamp", real, raising=False)
        assert pm.disk_changed() is False
        os.remove(str(p))                                                 # 外で消された
        assert pm.disk_changed() is False and pm.save() is True and len(ask.calls) == 1
        assert b"# more" in p.read_bytes()
    finally:
        _close(win)


def test_s3_the_python_editor_window_asks_before_saving_over_bytes_it_cannot_read(tmp_path, monkeypatch):
    """従来の Python エディタの保存も同じ形だった: 外で cp932 に書き換えられると、聞かずに上書きした。"""
    from PySide6 import QtWidgets
    script = tmp_path / "legacy.py"
    script.write_bytes(b"print(1)\n")
    win, _model = _launch(tmp_path, monkeypatch, start_mode="auto")
    try:
        ask = _Asker(monkeypatch, answer=False)
        win.drop_handler([str(script)])
        _pump(0.3)
        pe = win._pyedit
        ed = pe["editor"]()
        saves = [b for b in pe["dlg"].findChildren(QtWidgets.QAbstractButton) if b.text().replace("&", "") == "Save"]
        assert len(saves) == 1
        ed.setPlainText("print(2)\n")
        saves[0].click()
        assert ask.calls == [] and script.read_text(encoding="utf-8") == "print(2)\n"     # 変わっていなければ聞かない
        ed.setPlainText("print(3)\n")
        for outside in (_S3_OUTSIDE["cp932"], _S3_OUTSIDE["utf-8"]):
            n0 = len(ask.calls)
            script.write_bytes(outside)
            ask.answer = False
            saves[0].click()
            assert len(ask.calls) == n0 + 1 and script.read_bytes() == outside
            ask.answer = True
            saves[0].click()
            assert len(ask.calls) == n0 + 2 and script.read_text(encoding="utf-8") == "print(3)\n"
            saves[0].click()
            assert len(ask.calls) == n0 + 2                               # 自分で保存した後は聞かない
    finally:
        try:
            win._pyedit["dlg"].close()
        except Exception:                                                 # noqa: BLE001
            pass
        _close(win)


# --------------------------------------------------------------------------- #
# S5: パイプラインのファイルを開いたら、未適用の編集の状態を全部消す                 #
# --------------------------------------------------------------------------- #
def _pipeline_file(tmp_path):
    p = tmp_path / "opened.json"
    p.write_text(json.dumps({"fullseye_pipeline": 1, "stages": [["gaussian", 0.3, 0.5]], "directives": []}),
                 encoding="utf-8")
    return p


def _stages(model):
    return [list(s)[:3] for s in model.stages]


def _discard_hook(monkeypatch, answer):
    asked = []
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda parent, title, text: asked.append((title, text)) or answer)
    return asked


@pytest.mark.parametrize("start", ["python mode", "pipeline mode with the focus in the Program"])
def test_s5_opening_a_pipeline_file_drops_every_trace_of_the_discarded_edits(start, tmp_path, monkeypatch):
    """探針 r03: パイプラインのモードで未適用の編集 → Python のモード → パイプラインのファイルを開く(「捨てる」と
    答える)。捨てたはずの文面が Program に残り、Apply すると開いたパイプラインがその文面で置き換わった。
    パイプラインのモードのままでも、Program にフォーカスがあると同じ文面が残った。"""
    asked = _discard_hook(monkeypatch, True)
    win, model = _launch(tmp_path, monkeypatch, start_mode="pipeline")
    try:
        pm = win._pymode
        ed = win._program["edit"]
        _set_text(win, "median (5)\nthreshold (0.5)\n")                  # 打っただけ(未適用)
        ed.breakpoints.add(2)
        assert pm.state.get("code_dirty") is True and _stages(model) == []
        if start == "python mode":
            pm.set_mode("python")
            _pump(0.2)
            assert pm.pipe_dirty is True
            pm.toggle_breakpoint(2)                                      # Python の文面のブレークポイント
        else:
            monkeypatch.setattr(ed, "hasFocus", lambda: True)            # 打っている最中(Program にフォーカス)
        win._open_pipe_path(str(_pipeline_file(tmp_path)))
        _pump(0.4)
        assert len(asked) == 1 and "unapplied Program edits" in asked[0][1]
        assert pm.mode == "pipeline" and _stages(model) == [["gaussian", 0.3, 0.5]]
        text = ed.toPlainText()
        assert "median" not in text and "threshold" not in text and "gaussian" in text    # 開いた段の列から作り直す
        assert text.strip() == pm.ctx["generated_text"]().strip()
        assert pm.state.get("code_dirty") is False and pm.pipe_dirty is False
        assert "unapplied" not in win._program["status"]().text()
        assert ed.breakpoints == set()                                   # 捨てた文面のブレークポイントも残さない
        assert not ed.document().isUndoAvailable()                       # Ctrl+Z で捨てた文面は戻らない
        assert pm.mode_mismatch() is None
        if start == "python mode":
            assert pm.breakpoints_py == {2}                              # Python の文面の物は消さない
        win._program["apply"]()
        _pump(0.3)
        assert _stages(model) == [["gaussian", 0.3, 0.5]]                # Apply しても、開いたパイプラインのまま
    finally:
        _close(win)


def test_s5_cancel_keeps_the_unapplied_edits(tmp_path, monkeypatch):
    """「捨てますか」でキャンセルなら何も変わらない: 開かない。未適用の文面と印は、モードを戻せばそのまま在る。"""
    asked = _discard_hook(monkeypatch, False)
    win, model = _launch(tmp_path, monkeypatch, start_mode="pipeline")
    try:
        pm = win._pymode
        ed = win._program["edit"]
        _set_text(win, "median (5)\nthreshold (0.5)\n")
        pm.set_mode("python")
        _pump(0.2)
        win._open_pipe_path(str(_pipeline_file(tmp_path)))
        _pump(0.3)
        assert len(asked) == 1 and pm.mode == "python" and _stages(model) == [] and pm.pipe_dirty is True
        pm.set_mode("pipeline")
        _pump(0.2)
        assert ed.toPlainText() == "median (5)\nthreshold (0.5)\n" and pm.state.get("code_dirty") is True
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# S6: 確認の窓の既定のボタンはキャンセル側(Enter で取り返しのつかない事を起こさない)  #
# --------------------------------------------------------------------------- #
def _press_a_key_instead_of_exec(monkeypatch, key):
    """``QMessageBox.exec`` の代わりに、窓を出して *key* を押す。押す前の ``(既定のボタン, Esc のボタン, フォーカスの
    あるボタン)`` の役割を覚える。既定の窓そのもの(試験用の差し替えでなく、利用者が見る窓)を試すための道具。"""
    from PySide6 import QtWidgets
    from PySide6.QtTest import QTest
    seen = []

    def fake_exec(box):
        box.show()
        _pump(0.2)
        focus = QtWidgets.QApplication.focusWidget()
        seen.append(tuple(box.buttonRole(b) if isinstance(b, QtWidgets.QAbstractButton) else None
                          for b in (box.defaultButton(), box.escapeButton(), focus)))
        QTest.keyClick(box, key)
        _pump(0.05)
        box.hide()
        return 0

    def no_static_question(*_a, **_k):
        raise AssertionError("QMessageBox.question() builds and runs the window in one call: its default button "
                             "cannot be checked — build the box, set the default button, then exec()")
    monkeypatch.setattr(QtWidgets.QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", staticmethod(no_static_question))
    # 既定の窓は、画面の無い実行(offscreen)では出さずに「実行しない」を返す。その先(窓そのもの)を試す
    monkeypatch.setenv("QT_QPA_PLATFORM", "s6-not-offscreen")
    return seen


@pytest.mark.parametrize("key", ["Key_Return", "Key_Enter", "Key_Escape"])
def test_s6_enter_and_escape_on_every_default_confirmation_window_choose_the_safe_side(key, monkeypatch):
    """探針 r08: 信頼の確認(「ファイルから来たプログラムを実行しますか」)は、既定のボタンを決めていなかったので
    Enter で「Run it」が押された。F5 の直後に出る窓で反射的に Enter を押すと、確認していないコードが走る。"""
    from PySide6 import QtCore, QtWidgets
    _app()
    seen = _press_a_key_instead_of_exec(monkeypatch, getattr(QtCore.Qt, key))
    reject = QtWidgets.QMessageBox.RejectRole
    assert pm_mod._default_trust(None, "Run this Python program?", "text") is False          # 実行しない
    assert seen[-1] == (reject, reject, reject), seen[-1]
    assert studio._default_confirm_action(None, "Overwrite", "what is lost", "Overwrite the file") is False
    assert seen[-1] == (reject, reject, reject), seen[-1]
    assert studio._default_confirm(None, "Open pipeline", "Discard them?") is False          # 捨てない
    assert seen[-1] == (reject, reject, reject), seen[-1]
    assert len(seen) == 3
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")                    # 画面が無ければ、窓を出さずに安全な側
    assert pm_mod._default_trust(None, "t", "x") is False
    assert studio._default_confirm_action(None, "t", "x", "go") is False
    assert len(seen) == 3


def test_s6_closing_a_changed_tab_of_the_python_editor_asks_with_the_safe_default(tmp_path, monkeypatch):
    """従来の Python エディタのタブを閉じる窓は ``QMessageBox.question(Yes | No)`` で既定を渡しておらず、Enter で
    「Yes(捨てる)」だった。終了の時と同じ確認(CONFIRM_HOOK = Discard / Cancel、既定は Cancel)を通す。"""
    from PySide6 import QtWidgets
    asked = []
    answer = {"go": False}
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda parent, title, text: asked.append((title, text)) or answer["go"])
    static_calls = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "question",
                        staticmethod(lambda *a, **k: static_calls.append(a[1:3]) or QtWidgets.QMessageBox.Yes))
    script = tmp_path / "s6.py"
    script.write_bytes(b"print(1)\n")
    win, _model = _launch(tmp_path, monkeypatch, start_mode="auto")
    try:
        win.drop_handler([str(script)])                                  # 従来の Python エディタのタブで開く
        _pump(0.3)
        pe = win._pyedit
        tabs = pe["tabs"]
        n = tabs.count()
        assert n >= 1
        pe["editor"]().setPlainText("print(2)  # not saved\n")
        tabs.tabCloseRequested.emit(tabs.currentIndex())
        _pump(0.1)
        assert static_calls == []                                        # 既定のボタンを見られない窓は使わない
        assert len(asked) == 1 and "unsaved changes" in asked[0][1] and tabs.count() == n     # キャンセル: 閉じない
        answer["go"] = True
        tabs.tabCloseRequested.emit(tabs.currentIndex())
        _pump(0.1)
        assert len(asked) == 2 and tabs.count() == n - 1                 # 「捨てる」と答えた時だけ閉じる
    finally:
        try:
            win._pyedit["dlg"].close()
        except Exception:                                                 # noqa: BLE001
            pass
        _close(win)


# --------------------------------------------------------------------------- #
# S8: 数でない配列を show() しても、モーダルの窓は出ない                            #
# --------------------------------------------------------------------------- #
_S8_NOT_PICTURES = {
    "object": "a = np.empty((8, 8), dtype=object)\na[:] = Probe()\n",
    "str": "a = np.full((8, 8), 'ab')\n",
    "datetime": "a = np.zeros((8, 8), dtype='M8[s]')\n",
    "struct": "a = np.zeros((8, 8), dtype=[('x', 'f4'), ('y', 'i4')])\n",
}
_S8_PROBE = ("CALLED = []\nclass Probe:\n    def __float__(self):\n        CALLED.append('float')\n        return 0.5\n"
             "    def __lt__(self, o):\n        CALLED.append('lt')\n        return False\n"
             "    def __add__(self, o):\n        CALLED.append('add')\n        return self\n    __radd__ = __add__\n")


@pytest.mark.parametrize("kind", sorted(_S8_NOT_PICTURES))
def test_s8_showing_an_array_that_is_not_numbers_says_so_without_a_modal_window(kind, tmp_path, monkeypatch):
    """探針 r01: object の配列を ``show()`` する・選んだ行の値にすると、表示の処理が ``np.isfinite`` で落ち、
    毎回「Display error / The step could not run」のモーダルの窓が出た(画面の無い実行では GUI がそこで止まった)。"""
    modals = []
    monkeypatch.setattr(studio, "ERROR_HOOK", lambda parent, title, text: modals.append((title, str(text)[:200])))
    win, _model = _launch(tmp_path, monkeypatch, time_limit=10)
    try:
        pm = win._pymode
        errors0 = len(pm.state.get("errors", []))
        _set_text(win, "# python\n" + _S8_PROBE + _S8_NOT_PICTURES[kind] + "show(a)\n")
        res = _run(win)
        assert res.ok and modals == []                                   # 実行は成功。窓は出ない
        assert len(pm.state.get("errors", [])) == errors0                # 「表示の誤り」としても数えない
        out = _output(win)
        assert out.count("The shown value is not an image (") == 1 and "8×8" in out, out
        assert "not an image" in win.statusBar().currentMessage()        # 断りは状態の帯にも出す
        last = pm.edit.document().blockCount()
        _set_text(win, pm.edit.toPlainText() + "a\n")
        pm.output.clear()
        _run_selection(win, last, last)                                  # 選んだ行の値が、その配列
        assert modals == [] and "8×8" in _output(win) and "not an image" not in _output(win)   # 値の要約だけ。絵にしない
        assert pm.namespace["CALLED"] == []                              # 利用者の __float__ / 比べる演算は呼ばない
        assert pm_mod._is_image(pm.namespace["a"]) is False
    finally:
        _close(win)


def test_s8_numeric_arrays_are_still_displayed(tmp_path, monkeypatch):
    """数の配列(bool・整数・実数・複素数)は今までどおり画像の欄へ出る。"""
    modals = []
    monkeypatch.setattr(studio, "ERROR_HOOK", lambda parent, title, text: modals.append((title, str(text)[:200])))
    win, _model = _launch(tmp_path, monkeypatch, time_limit=10)
    try:
        pm = win._pymode
        for src, dtype in (("bool", np.bool_), ("np.uint8", np.uint8), ("np.float32", np.float32),
                           ("complex", np.complex128)):
            _set_text(win, "# python\na = np.ones((8, 8), dtype=%s)\nshow(a)\n" % src)
            res = _run(win)
            assert res.ok and modals == [] and "not an image" not in _output(win), src
            assert res.output.dtype == np.dtype(dtype) and pm_mod._is_image(res.output), src
            if src != "complex":                                         # 複素数は見せ方を選ぶ(絵そのものではない)
                assert win._state.get("raw") is res.output, src
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# S4: 補完・ホバー・シグネチャが調べてよい物は、許す型の一覧で決める               #
# --------------------------------------------------------------------------- #
S4_CALLED = []


def _s4_hit(what):
    """利用者のコードが呼ばれた事を、呼んだスレッドの名前つきで記録する。"""
    S4_CALLED.append("%s@%s" % (what, threading.current_thread().name))


class _S4Watched:
    """属性を読まれるたびに記録する、利用者の物(``__getattribute__``)。"""

    def __getattribute__(self, name):
        _s4_hit("__getattribute__ " + name)
        return object.__getattribute__(self, name)


class _S4Callable:
    """呼べる利用者の物。無い属性を読まれるたびに記録する(``__getattr__``)。"""

    def __call__(self, a, b=1):
        return a

    def __getattr__(self, name):
        _s4_hit("__getattr__ " + name)
        raise AttributeError(name)


class _S4Repr:
    def __repr__(self):
        _s4_hit("__repr__")
        return "<S4Repr>"


class _S4Meta(type):
    @property
    def __name__(cls):
        _s4_hit("Meta.__name__")
        return "Fake"


class _S4WithMeta(metaclass=_S4Meta):
    def method(self, a, b=_S4Repr(), *rest, key=_S4Repr(), **more):
        return a


class _S4Module(type(sys)):
    def __getattribute__(self, name):
        _s4_hit("Module.__getattribute__ " + name)
        return type(sys).__getattribute__(self, name)


class _S4Planted:
    """ライブラリのモジュールへ差し込む、利用者のクラス(``json._S4Planted`` として辿れるようにする)。"""

    def __dir__(self):
        _s4_hit("__dir__")
        return ["a"]

    def __getattr__(self, name):
        _s4_hit("__getattr__ " + name)
        return 1


def _s4_user_function(a, b=_S4Repr()):
    return a


def _s4_namespace(monkeypatch):
    import contextlib
    import functools
    import json
    import weakref
    _S4Planted.__module__ = "json"
    _S4Planted.__qualname__ = "_S4Planted"
    monkeypatch.setattr(json, "_S4Planted", _S4Planted, raising=False)
    keep = [_S4Watched(), _S4Callable()]                                  # 弱参照の先を生かしておく

    @contextlib.contextmanager
    def managed(a, b=_S4Repr()):
        yield a

    @functools.lru_cache(maxsize=None)
    def cached(a, b=_S4Repr()):
        return a
    return {
        "proxy": weakref.proxy(keep[0]),
        "cproxy": weakref.proxy(keep[1]),
        "part": functools.partial(_S4Callable(), 1),
        "part_arg": functools.partial(sorted, _S4Repr()),
        "part_kw": functools.partial(sorted, key=_S4Callable()),
        "pmeth": functools.partialmethod(_S4Callable(), 1),
        "planted": _S4Planted(),
        "ufunc": _s4_user_function,
        "managed": managed,
        "cached": cached,
        "bound": _S4Callable().__call__,
        "_keep": keep,
    }


@pytest.mark.parametrize("use_jedi", [False, True])
def test_s4_library_wrappers_do_not_carry_user_code_onto_the_gui_thread(use_jedi, monkeypatch):
    """探針 r07: ``weakref.proxy``・``functools.partial``・ライブラリのモジュールへ差し込んだクラスを通して、補完・
    ホバー・シグネチャが GUI のスレッドで利用者の ``__getattribute__`` / ``__getattr__`` / ``__dir__`` を呼んだ
    (ホバーはマウスを置くだけで起きる)。既定値の ``__repr__`` も、シグネチャを文字にする所で呼ばれた。"""
    import studio_pyedit_complete as comp
    import studio_pyedit_safe as safe
    import studio_pyedit_values as V
    assert threading.current_thread().name == "MainThread"
    if use_jedi and not comp.jedi_available():
        pytest.skip("jedi is not installed")
    pm_mod._configure_jedi()
    ns = _s4_namespace(monkeypatch)
    prov = comp.default_provider(namespace=lambda: ns, catalog=None, use_jedi=use_jedi)
    names = sorted(k for k in ns if not k.startswith("_"))
    assert len(names) == 11
    S4_CALLED.clear()
    for name in names:
        assert safe.is_inert(ns[name]) is False, name                     # どれも「調べてよい物」ではない
        assert safe.is_plain_value(ns[name]) is False, name               # jedi にも生きた値として渡さない
        prov.complete(name + ".", 0, len(name) + 1)
        prov.complete(name, 0, len(name))
        prov.hover(name, 0, 1)
        prov.signature(name + "(", 0, len(name) + 1)
        for c in prov.complete(name[:3], 0, 3):                           # 候補の説明(選んだ時に作られる)
            c.full_doc()
        safe.static_names(ns[name])
        V.children(ns[name])
        assert S4_CALLED == [], (name, S4_CALLED[:6])
    assert comp.signature_of_object("part", ns["part"]) is None
    # 利用者の関数は __code__ から(既定値は =…、__repr__ は呼ばない。2026-11-15 第 4 回の確かめで戻した)
    assert [p.text for p in comp.signature_of_object("ufunc", ns["ufunc"]).params] == ["a", "b=…"]
    assert comp._sig_text(ns["managed"]) == "(a, b=…)" and comp._doc_of(ns["proxy"]) == ""
    assert "a" not in safe.static_names(ns["planted"])                    # __dir__ の嘘の名前は出ない
    assert S4_CALLED == []


def test_s4_the_allow_list_still_covers_what_a_program_uses_every_day():
    """断りすぎない事: ライブラリの関数・クラス・モジュール・numpy の物は今までどおり調べる(シグネチャと説明が出る)。
    一覧に無いライブラリのクラスのインスタンスは、静的な名前で補完する(``dir`` とほぼ同じ名前が出る)。"""
    import functools
    import json
    import pathlib
    import studio_pyedit_complete as comp
    import studio_pyedit_safe as safe
    inert = {"module": np, "list": [], "dict": {}, "int": 3, "str": "s", "None": None, "array": np.zeros(2),
             "scalar": np.float64(1.5), "dtype": np.dtype("f8"), "ufunc": np.sin, "numpy function": np.linspace,
             "python function": json.dumps, "frozen stdlib function": os.path.join, "builtin": len,
             "method descriptor": str.join, "class": json.JSONEncoder, "bound method of a class": pathlib.Path.cwd,
             "partial of library parts": functools.partial(np.linspace, 0, 1, num=5),
             "partial with a list": functools.partial(sorted, [3, 1, 2]),
             "staticmethod": staticmethod(json.dumps), "property": property(json.dumps)}
    refused = [k for k, v in sorted(inert.items()) if not safe.is_inert(v)]
    assert refused == [] and len(inert) == 21
    p = pathlib.Path(".")
    assert safe.is_inert(p) is False                                      # 一覧に無いライブラリのクラスのインスタンス
    static = set(safe.static_names(p))
    assert {"exists", "name", "parent", "read_text", "with_suffix"} <= static
    assert len([n for n in dir(p) if n not in static]) <= 3               # dir() とほぼ同じ名前
    sig = comp.signature_of_object("linspace", np.linspace)
    assert sig is not None and [q.name for q in sig.params][:3] == ["start", "stop", "num"]
    sig = comp.signature_of_object("part", inert["partial of library parts"])
    assert sig is not None and "endpoint" in [q.name for q in sig.params]
    assert comp._sig_text(json.dumps).startswith("(obj") and "Serialize" in comp._doc_of(json.dumps)
    ns = {"p": p, "np": np, "arr": np.zeros((2, 2))}
    prov = comp.default_provider(namespace=lambda: ns, catalog=None, use_jedi=False)
    assert "exists" in [c.name for c in prov.complete("p.ex", 0, 4)]
    assert "zeros" in [c.name for c in prov.complete("np.ze", 0, 5)]
    assert "shape" in [c.name for c in prov.complete("arr.sha", 0, 7)]
    assert prov.signature("np.linspace(", 0, 12) is not None
    assert safe.is_plain_value(json.dumps) and safe.is_plain_value(np) and not safe.is_plain_value(p)


def test_s4_the_variables_summary_of_functions_classes_and_modules_calls_no_user_code(monkeypatch):
    """S4 を直す途中で見つけた同じ型の穴: 変数の欄の要約(GUI のスレッド)が、利用者の関数の既定値の ``__repr__``
    (``inspect.signature`` を文字にする所)、メタクラスの ``__name__``、モジュールの ``__getattribute__`` を呼んだ。
    ``def f(x, cfg=Config()):`` のような普通の書き方で、``__repr__`` が重ければ実行のたびに画面が止まる。"""
    import json
    import studio_pyedit_values as V
    assert threading.current_thread().name == "MainThread"
    ns = _s4_namespace(monkeypatch)
    values = {"function": _s4_user_function, "bound method": _S4WithMeta().method, "class": _S4WithMeta,
              "module": _S4Module("s4mod"), "wrapped": ns["managed"], "proxy": ns["proxy"], "planted": ns["planted"],
              "partial": ns["part_arg"]}
    S4_CALLED.clear()
    text = {k: V.summarize(v).text for k, v in values.items()}
    on_gui = [c for c in S4_CALLED if c.endswith("@MainThread")]
    assert on_gui == [], on_gui                                           # GUI のスレッドでは 1 つも呼ばない
    assert text["function"] == "_s4_user_function(a, b=…)"           # 既定値は文字にしない(…)
    assert text["bound method"] == "method(a, b=…, *rest, key=…, **more)"
    assert text["class"] == "class _S4WithMeta" and text["module"] == "module s4mod"
    assert text["wrapped"].startswith("managed(")
    # ライブラリの関数は今までどおり、既定値つきのシグネチャが出る
    assert V.summarize(json.dumps).text.startswith("dumps(obj, *, skipkeys=False")
    assert V.summarize(len).text.startswith("len(")

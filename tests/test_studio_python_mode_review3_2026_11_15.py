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

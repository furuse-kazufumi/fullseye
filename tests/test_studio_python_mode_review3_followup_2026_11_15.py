# -*- coding: utf-8 -*-
"""Studio の Python のモード: 第 3 回レビューの直し(S1〜S9)を、確かめの担当 2 人が確かめて見つけた残りの回帰試験
(2026-11-15)。

* S1b(重大): 入口を入れ子にしない。Debug で止まっている間の「選んだ行」は、止まっている実行の見張りの下で回し、
  自分では見張りを付けず、遅れた戻しもしない。止められずに残しても、Debug の実行が終わった後に Studio の import が
  壊れず、プログラムが変えた環境と作業フォルダは戻る。走っている(止まっていない)実行と重ねては始めない。
  外した見張りが鉤の列に残っても、None を呼ばずに元の物へ素通しする。
* S1c: 止まっている間の選んだ行の後でも、続行したプログラムの print は出力に出る(名前空間の print を戻す)。
* S1d: 選んだ行は、名前空間の ``__studio_recorder__`` に置かれた物が :class:`Recorder` そのものでなければ使わない
  (見張りの外で利用者のコードを呼ばない)。
* S7b: import の見張りは、``importlib.import_module`` の相対の名前・dict の派生を globals にした ``__import__``・
  str の派生の名前も見る。
* S4b〜S4f: 補完・ホバー・シグネチャ・変数の欄が GUI のスレッドで利用者のコードを呼ばない残りの道(呼べない物の
  ``inspect.signature``・利用者の物に束縛された C のメソッド・メタクラスの ``__getattribute__``・Studio のフォルダに
  置いたプログラム)と、S4 の直しで出なくなった利用者の関数のシグネチャ。
* S3b / S3c: 起動し直した時、外で変わった・読めないファイルを、退避した未保存の文面で聞かずに上書きしない。
  読めない時も退避した文面を捨てない。
* S2b: Undo / Redo で戻った文面の由来と信頼は、その文面が置き換えられた時の物(手で打った文面を「ファイルから
  来た」と言わない)。確認していないファイルの文面は、今までどおり確認するまで走らない。

**固まりうる試験・import の鉤を壊しうる試験は子プロセス + 時間の上限で回す**(壊れた鉤が pytest ごと巻き込まない)。
"""
import builtins
import importlib
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
import studio_pyedit_complete as comp
import studio_pyedit_safe as safe
import studio_pyedit_values as V

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


def _launch(tmp_path, monkeypatch, start_mode="python", time_limit=None, ini_name="s.ini"):
    _app()
    ini = tmp_path / ini_name
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


def _type_at_end(pm, text):
    from PySide6 import QtGui
    c = pm.edit.textCursor()
    c.movePosition(QtGui.QTextCursor.End)
    c.insertText(text)
    pm.edit.setTextCursor(c)
    _pump(0.2)


def _wait_abandoned(sec=20.0) -> bool:
    end = time.monotonic() + sec
    while sp.abandoned_runs() and time.monotonic() < end:
        time.sleep(0.05)
    return not sp.abandoned_runs()


def _run_child(tmp_path, head: str, body: str, timeout: int) -> dict:
    """*head* + *body* を子プロセスで回し、``RESULT`` の行の JSON を返す。*timeout* 秒で終わらなければ殺して**失敗**に
    する(固まった時は、最後に通った ``STEP`` と、子が自分で書いたスレッドの写しを失敗の文に出す)。"""
    script = tmp_path / "child.py"
    script.write_text(head + body, encoding="utf-8")
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


#: 子プロセスの先頭(API だけ): 始めた時の import の入口と作業フォルダを覚え、結果は ``RESULT <JSON>`` の 1 行で返す。
_API_HEAD = r'''
import builtins, importlib, json, os, sys, threading, time, faulthandler
faulthandler.dump_traceback_later(int(os.environ["S3_CHILD_DUMP_S"]), exit=True)
sys.path.insert(0, os.environ["S3_ROOT"])
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import numpy as np
import studio_program as sp
OUT = {}
ORIG = (builtins.__import__, importlib.import_module, importlib.__import__)
CWD0 = os.getcwd()
def step(name):
    print("STEP " + name, flush=True)
def done():
    print("RESULT " + json.dumps(OUT, default=str), flush=True)
def real_hooks():
    return [builtins.__import__ is ORIG[0], importlib.import_module is ORIG[1], importlib.__import__ is ORIG[2]]
def wait_abandoned(sec=30):
    end = time.monotonic() + sec
    while sp.abandoned_runs() and time.monotonic() < end:
        time.sleep(0.05)
    return not sp.abandoned_runs()
'''

#: 子プロセスの先頭(Studio の窓): 上の物に、窓を作る道具を足す。
_GUI_HEAD = _API_HEAD + r'''
def pump(sec=0.3):
    from PySide6 import QtWidgets
    end = time.monotonic() + sec
    while time.monotonic() < end:
        QtWidgets.QApplication.processEvents()
        time.sleep(0.01)
def launch(time_limit=30):
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
def wait_until(cond, sec=15):
    end = time.monotonic() + sec
    while time.monotonic() < end and not cond():
        pump(0.05)
    return bool(cond())
'''


# --------------------------------------------------------------------------- #
# S1b(重大): 入口を入れ子にしない                                                #
# --------------------------------------------------------------------------- #
def test_s1b_an_abandoned_selection_while_paused_leaves_the_imports_env_and_cwd_clean(tmp_path):
    """確かめ v02: Debug で止まっている間の「選んだ行」が止められずに残り、その後で Debug の実行が終わると、
    選んだ行の遅れた戻しが「止まっていた時の写し」と外した見張りを戻した。後の import が全部 TypeError になり、
    プログラムが変えた環境変数と作業フォルダも戻ってきた(子プロセス + 時間の上限)。"""
    body = r'''
PROG = "import os\nos.environ['S1B_LEAK'] = 'paused program'\nos.chdir(@CWD@)\nx = 1\ny = 2\n"
paused, release, box, res = threading.Event(), threading.Event(), {}, {}
def hook(snap):
    box["snap"] = snap
    box["hook_in_pause"] = builtins.__import__
    paused.set()
    release.wait(60)
    return "continue"
step("f5")
f5 = threading.Thread(target=lambda: res.setdefault("r", sp.run_program(PROG, np.zeros((4, 4)), breakpoints=[5],
                      pause_hook=hook, config="debug", time_limit_s=60, stop_event=threading.Event())))
f5.start()
OUT["paused"] = paused.wait(30)
step("selection")
ns = box["snap"].namespace
sel = sp.evaluate("import time\ntime.sleep(4)\nimport os\nos.environ['S1B_SEL'] = 'late'", ns, time_limit_s=0.3,
                  stop_event=threading.Event())
OUT["sel_error"] = (sel["error"] or "")[:30]
OUT["hook_kept_while_left"] = builtins.__import__ is box["hook_in_pause"]
OUT["refused_while_left"] = sp.evaluate("z = 1", ns, time_limit_s=5)["error"] == sp.ABANDONED_BLOCKS_RUN % 1
step("release")
release.set()
f5.join(30)
OUT["f5_errors"] = res["r"].errors
OUT["left_after_f5"] = bool(sp.abandoned_runs())
OUT["next_refused_while_left"] = sp.run_program("a = 1\n", np.zeros((4, 4))).errors == [sp.ABANDONED_BLOCKS_RUN % 1]
step("wait")
OUT["cleared"] = wait_abandoned(30)
time.sleep(0.3)
OUT["hooks"] = real_hooks()
OUT["env"] = [os.environ.get("S1B_LEAK"), os.environ.get("S1B_SEL")]
OUT["cwd_back"] = os.getcwd() == CWD0
step("next")
r2 = sp.run_program("import os\nz = os.environ.get('S1B_LEAK')\n", np.zeros((4, 4)), time_limit_s=10)
OUT["next"] = [r2.errors, r2.values.get("z", "missing")]
from PySide6 import QtCore  # noqa: F401  (Studio の GUI のスレッドの import)
OUT["main_import"] = "ok"
done()
'''.replace("@CWD@", repr(str(tmp_path).replace("\\", "/")))
    got = _run_child(tmp_path, _API_HEAD, body, timeout=150)
    assert got["paused"] is True
    assert got["sel_error"].startswith("could not stop"), got
    assert got["hook_kept_while_left"] is True                # 選んだ行は自分の見張りを重ねない(止まっている実行の物のまま)
    assert got["refused_while_left"] is True
    assert got["f5_errors"] == [] and got["left_after_f5"] is True and got["next_refused_while_left"] is True
    assert got["cleared"] is True
    assert got["hooks"] == [True, True, True], got            # 3 つの import の入口が本物に戻る
    assert got["env"] == [None, None] and got["cwd_back"] is True, got
    assert got["next"] == [[], None] and got["main_import"] == "ok", got


def test_s1b_the_debug_run_ends_while_its_selection_is_still_running(tmp_path):
    """外側(止まっていた Debug の実行)が、内側(選んだ行)が終わる前に終わった: 外側の後始末は内側が終わるのを
    待ち、その間は次の実行を断り、終わった所で外側の前の状態へ戻して見張りを外す(子プロセス + 時間の上限)。"""
    body = r'''
PROG = "import os\nos.environ['S1B_PROG'] = 'paused program'\nos.chdir(@CWD@)\nx = 1\ny = 2\n"
paused, release, box, res, sel = threading.Event(), threading.Event(), {}, {}, {}
def hook(snap):
    box["snap"] = snap
    paused.set()
    release.wait(60)
    return "continue"
f5 = threading.Thread(target=lambda: res.setdefault("r", sp.run_program(PROG, np.zeros((4, 4)), breakpoints=[5],
                      pause_hook=hook, config="debug", time_limit_s=60, stop_event=threading.Event())))
f5.start()
OUT["paused"] = paused.wait(30)
step("selection")
src = "import os, time\nos.environ['S1B_SEL'] = '1'\ntime.sleep(1.5)\nos.environ['S1B_SEL2'] = '2'\n"
t = threading.Thread(target=lambda: sel.setdefault("r", sp.evaluate(src, box["snap"].namespace)))
t.start()
time.sleep(0.4)
step("release")
release.set()
f5.join(30)
OUT["f5_errors"] = res["r"].errors
OUT["waiting_counts_as_left"] = bool(sp.abandoned_runs())
OUT["next_refused"] = sp.run_program("a = 1\n", np.zeros((4, 4))).errors[:1] == [sp.ABANDONED_BLOCKS_RUN % 1]
step("join")
t.join(30)
OUT["sel_error"] = sel["r"]["error"]
OUT["cleared"] = wait_abandoned(30)
time.sleep(0.2)
OUT["hooks"] = real_hooks()
OUT["env"] = [os.environ.get(k) for k in ("S1B_PROG", "S1B_SEL", "S1B_SEL2")]
OUT["cwd_back"] = os.getcwd() == CWD0
r2 = sp.run_program("import json\nz = json.dumps(1)\n", np.zeros((4, 4)), time_limit_s=10)
OUT["next"] = [r2.errors, r2.values.get("z")]
done()
'''.replace("@CWD@", repr(str(tmp_path).replace("\\", "/")))
    got = _run_child(tmp_path, _API_HEAD, body, timeout=150)
    assert got["paused"] is True and got["f5_errors"] == []
    assert got["waiting_counts_as_left"] is True and got["next_refused"] is True, got
    assert got["sel_error"] is None and got["cleared"] is True
    assert got["hooks"] == [True, True, True], got
    assert got["env"] == [None, None, None] and got["cwd_back"] is True, got
    assert got["next"] == [[], "1"], got


def test_s1b_the_selection_while_paused_runs_under_the_paused_runs_guard_and_not_beside_a_running_one():
    """止まっている間の選んだ行は、止まっている実行の見張り(同じ鉤)の下で回り、Qt の import は断られる。止まって
    いない(走っている)実行とは重ねて始めない(:data:`ANOTHER_RUN_BLOCKS_RUN`)。"""
    paused, release, box, res = threading.Event(), threading.Event(), {}, {}

    def hook(snap):
        box["snap"] = snap
        box["hook"] = builtins.__import__
        paused.set()
        release.wait(30)
        return "continue"
    t = threading.Thread(target=lambda: res.setdefault("r", sp.run_program(
        "x = 1\ny = 2\nz = 3\n", IMG, breakpoints=[2], pause_hook=hook, config="debug", time_limit_s=30,
        stop_event=threading.Event())))
    t.start()
    try:
        assert paused.wait(20)
        ns = box["snap"].namespace
        e = sp.evaluate("import builtins\nseen = builtins.__import__\n", ns, time_limit_s=10)
        assert e["error"] is None and ns["seen"] is box["hook"]      # 2 つ目の見張りを付けていない
        e = sp.evaluate("import importlib\nq = importlib.import_module('PySide6.QtWidgets')\n", ns, time_limit_s=10)
        assert e["error"] and "Studio does not let a running program import" in e["error"], e
        assert "q" not in ns
        assert builtins.__import__ is box["hook"]                       # 選んだ行の後も、止まっている実行の見張りのまま
    finally:
        release.set()
        t.join(30)
    assert res["r"].errors == [] and res["r"].values["z"] == 3
    imp0 = builtins.__import__
    started, res2 = threading.Event(), {}
    t2 = threading.Thread(target=lambda: res2.setdefault("r", sp.run_program(
        "import time\nfor i in range(150):\n    time.sleep(0.01)\nw = 1\n", IMG, time_limit_s=30)))
    t2.start()
    try:
        end = time.monotonic() + 10
        while builtins.__import__ is imp0 and time.monotonic() < end:
            time.sleep(0.005)
        assert builtins.__import__ is not imp0                          # 走っている
        e = sp.evaluate("q = 1", res["r"], time_limit_s=5)
        assert e["error"] == sp.ANOTHER_RUN_BLOCKS_RUN and "q" not in res["r"].namespace
    finally:
        t2.join(30)
    assert res2["r"].errors == [] and builtins.__import__ is imp0
    assert sp.evaluate("q = 1", res["r"], time_limit_s=5)["error"] is None   # 終わった後は普通に走る


def test_s1b_a_guard_left_under_another_hook_passes_imports_through_after_it_is_taken_off():
    """外した見張りが鉤の列に残っても(上に別の鉤が重なっていて元へ戻せなかった)、None を呼ばず、何も断らずに
    元の物へ素通しする(前は外す時に元の物を None にした: 残った鉤から呼ぶ import が全部 TypeError になった)。"""
    imp0 = builtins.__import__
    try:
        g = sp._ImportGuard() if sp._ImportGuard.__init__.__code__.co_argcount == 1 else sp._ImportGuard(None)
        g.install()
        mine = builtins.__import__
        assert mine is not imp0

        def over(*a, **k):
            return mine(*a, **k)
        builtins.__import__ = over                                      # 別の物が上に重なった(外せない)
        g.uninstall()
        assert builtins.__import__ is over
        import json as j1                                               # 残った鉤を通る(None を呼ばない)
        assert j1.dumps(1) == "1"
        g2 = importlib.import_module("json")
        assert g2 is j1
    finally:
        builtins.__import__ = imp0


def test_s1b_in_the_window_debug_selection_stop_stop_leaves_studio_working(tmp_path):
    """確かめ v03(窓で、利用者が押せる順に): Debug の F5 で止める → C の中で待つ行を選んで実行 → 止める(選んだ行を
    残す)→ もう一度止める(Debug を終える)→ 残した行が自分で終わる。前は Studio の GUI のスレッドの
    ``from PySide6 import QtWidgets`` が TypeError になった(子プロセス + 時間の上限)。"""
    body = r'''
win = launch(time_limit=30)
ORIG = (builtins.__import__, importlib.import_module, importlib.__import__)   # PySide6 は builtins.__import__ を包む
pm = win._pymode
pm.set_config("debug")
cwd_prog = @CWD@
set_text(win, "import os, time\nos.environ['S1B_WIN'] = 'paused program'\nos.chdir(%r)\ny = 2\ntime.sleep(4)\n" % cwd_prog)
pm.edit.breakpoints = {4}
step("run")
pm.run()
OUT["paused"] = wait_until(lambda: pm.session is not None and pm.session.live, 20)
select_lines(win, 5, 5)
step("selection")
OUT["selection_started"] = pm.run_selection()
pump(0.4)
OUT["stop1"] = pm.stop()
OUT["selection_done"] = wait_until(lambda: pm.job is None, 20)
OUT["left"] = len(sp.abandoned_runs())
step("stop2")
OUT["stop2"] = pm.stop()
pump(0.5)
step("wait")
OUT["cleared"] = wait_until(lambda: not sp.abandoned_runs(), 30)
pump(0.5)
OUT["hooks"] = real_hooks()
OUT["env"] = os.environ.get("S1B_WIN")
OUT["cwd_back"] = os.getcwd() == CWD0
from PySide6 import QtWidgets  # noqa: F401  (Studio の GUI のスレッドの import)
OUT["gui_import"] = "ok"
step("next")
set_text(win, "z = 1\nprint('next run ok', z)\n")
pm.edit.breakpoints = set()
pm.run()
wait_until(lambda: pm.job is None, 20)
pump(0.3)
OUT["next_output"] = pm.output.toPlainText()[-400:]
close(win)
done()
'''.replace("@CWD@", repr(str(tmp_path)))
    got = _run_child(tmp_path, _GUI_HEAD, body, timeout=180)
    assert got["paused"] is True and got["selection_started"] is True and got["stop1"] is True
    assert got["selection_done"] is True and got["left"] == 1 and got["stop2"] is True
    assert got["cleared"] is True
    assert got["hooks"] == [True, True, True], got
    assert got["env"] is None and got["cwd_back"] is True, got
    assert got["gui_import"] == "ok" and "next run ok 1" in got["next_output"], got


# --------------------------------------------------------------------------- #
# S1c: 選んだ行は名前空間の print を戻す / S1d: 名前空間の記録役を信じない         #
# --------------------------------------------------------------------------- #
def test_s1c_the_programs_print_after_a_selection_while_paused_reaches_its_output():
    """確かめ v04b P1: 止まっている間に選んだ行を走らせると、続行したプログラムの print が出力に出なかった
    (選んだ行が名前空間の print を自分の入れ物に差し替えて、戻さなかった)。"""
    paused, release, box, res = threading.Event(), threading.Event(), {}, {}

    def hook(snap):
        box["snap"] = snap
        paused.set()
        release.wait(30)
        return "continue"
    t = threading.Thread(target=lambda: res.setdefault("r", sp.run_program(
        "a = 3\nb = 4\nprint('END-PRINT', a)\n", IMG, breakpoints=[2], pause_hook=hook, config="debug",
        time_limit_s=30, stop_event=threading.Event())))
    t.start()
    try:
        assert paused.wait(20)
        ns = box["snap"].namespace
        prog_print = ns["print"]
        e = sp.evaluate("print('SEL', a + 10)", ns, time_limit_s=10)
        assert e["error"] is None and e["stdout"] == "SEL 13\n"
        assert ns["print"] is prog_print                                # 名前空間の print はプログラムの物に戻る
    finally:
        release.set()
        t.join(30)
    r = res["r"]
    assert r.errors == [] and "END-PRINT 3" in r.stdout and "SEL" not in r.stdout, r.stdout
    e = sp.evaluate("print('after')\nprint = 5\n", r, time_limit_s=10)       # 選んだ行が print を書き換えたら、それは残す
    assert e["error"] is None and e["stdout"] == "after\n" and r.namespace["print"] == 5


def test_s1d_the_selection_does_not_use_a_recorder_object_put_in_the_namespace_by_the_program():
    """確かめ v06: 選んだ行は記録役を名前空間の ``__studio_recorder__`` から取り、その属性を見張りの外(呼び出し側の
    スレッド)で読み書きした。プログラムがそこに自分の物を置くと、利用者のコードが上限なしに走った。"""
    r = sp.run_program("x = 1\n", IMG)
    touched = []

    class FakeRecorder:
        def __getattribute__(self, name):
            touched.append((name, threading.current_thread().name))
            raise AttributeError(name)

        def __bool__(self):
            touched.append(("__bool__", threading.current_thread().name))
            return True
    real = r.namespace["__studio_recorder__"]
    r.namespace["__studio_recorder__"] = FakeRecorder()
    t0 = time.perf_counter()
    e = sp.evaluate("y = x + 1\ng = gaussian(img, 0.5)\n", r, time_limit_s=10)
    assert e["error"] is None and r.namespace["y"] == 2 and [c.op for c in e["calls"]] == ["gaussian"]
    assert touched == [] and time.perf_counter() - t0 < 5.0
    r.namespace["__studio_recorder__"] = real                             # 本物の記録役は今までどおり使う
    n0 = len(real.calls)
    e = sp.evaluate("h = gaussian(img, 0.4)\n", r, time_limit_s=10)
    assert e["error"] is None and [c.op for c in e["calls"]] == ["gaussian"] and len(real.calls) == n0 + 1

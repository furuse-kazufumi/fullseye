# -*- coding: utf-8 -*-
"""Studio の Python のモード: 独立レビュー(2026-11-13)の指摘の回帰試験。

レビューアの探針(p01〜p09。repo の外の作業用の資料)と同じ内容を、直した後に成り立つ形で固定する。

* H1: パイプラインのファイルの表示の指示に式を書いても、「Python に変換」は断る。変換した文面はファイルの信頼を
  引き継ぐ(初回の実行の前に確認)。パイプラインのモードの文面を Python として走らせない。
* H2: 実行の後の変数の表は、利用者の ``__repr__`` / ``__len__`` / ``__class__`` を呼ばない。
* H3: 止められずに残した実行が生きている間は、次の実行を断ってそう言う。終わったら状態をもう一度戻す。
* H4: 実行の後に戻すプロセスの状態(``RESTORED_STATE`` の全部)。
* M1: Qt を直接使うプログラムは、橋が無ければ作業スレッドでは走らせない。
* M3: 補完・ホバー・変数の要約は、利用者の ``__dir__`` / ``__getattr__`` / ``__class__`` を呼ばない。
* M4: 変数の欄の編集は実行の名前空間に届く。
* M5: 従来の Python エディタにファイルから開いた .py も、初回の実行の前に確認する。
* L1: 出力の上限。E2: 未保存の文面の自動の書き出し。
"""
import ast
import builtins
import json
import os
import sys
import threading
import time

import numpy as np
import pytest

import studio
import studio_program as sp
import studio_pyedit_complete as comp
import studio_pyedit_safe as safe
import studio_pyedit_values as V
import studio_pymode as pm_mod

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


def _launch(tmp_path, monkeypatch, start_mode="auto", name="s.ini", time_limit=None):
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


def _f5(win, timeout=20):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    QTest.keyClick(win._program["edit"], QtCore.Qt.Key_F5)
    assert win._pymode.wait_idle(timeout)
    _pump(0.1)
    return win._pymode.last


def _wait_no_abandoned(timeout=15.0):
    """止められずに残した実行が終わるまで待つ(残したまま次の試験へ行くと、その試験の実行が断られる)。"""
    end = time.monotonic() + timeout
    while sp.abandoned_runs() and time.monotonic() < end:
        time.sleep(0.05)
    time.sleep(0.15)                                       # 終わった後の「もう一度戻す」を待つ
    return not sp.abandoned_runs()


# --------------------------------------------------------------------------- #
# H1: 表示の指示の引数 / 変換した文面の信頼                                       #
# --------------------------------------------------------------------------- #
_EVIL_ARGS = ["__import__('os').getcwd()", "open('x', 'w')", "a.b", "a[0]", "1 + 1", "x=1", "lambda: 1",
              "f'{x}'", "[1, 2]", "(1, 2)", "-'a'", "not a", "a if b else c", "{1: 2}", "b'x'", "1j", "..."]


@pytest.mark.parametrize("arg", _EVIL_ARGS)
def test_h1_directive_arguments_other_than_constants_and_words_are_refused(arg):
    py, errs = sp.hdev_to_python("gaussian (0.3, 0.5)\ndev_set_lut (%s)\n" % arg)
    assert py == "" and errs, (arg, py)
    assert errs[0].startswith("line 2: cannot convert the directive"), errs
    assert sp._directive_to_python("dev_set_lut (%s)" % arg) is None


def test_h1_plain_directives_still_convert_and_are_rebuilt_from_the_tree():
    src = ("dev_set_lut (gray)\ndev_disp_text ('#1 coin', 10, -20.5)\ndev_update_off\ngaussian (0.3, 0.5)\n"
           'dev_set_color ("red")\n')
    py, errs = sp.hdev_to_python(src)
    assert not errs, errs
    lines = py.splitlines()
    assert lines[0] == "dev_set_lut('gray')" and lines[1] == "dev_disp_text('#1 coin', 10, -20.5)"
    assert lines[2] == "dev_update_off()" and lines[4] == "dev_set_color('red')"
    seen = 0
    for ln in (lines[0], lines[1], lines[2], lines[4]):
        call = ast.parse(ln, mode="eval").body
        assert isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and not call.keywords
        for a in call.args:                                              # 定数(と符号つきの数)だけ
            node = a.operand if isinstance(a, ast.UnaryOp) else a
            assert isinstance(node, ast.Constant), ast.dump(a)
            seen += 1
    assert seen == 5
    r = sp.run_program(py, IMG)
    assert r.ok, r.errors


def _pipeline_file(tmp_path, directives, name="p.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"fullseye_pipeline": 1, "stages": [["gaussian", 0.3, 0.5]],
                             "directives": directives}), encoding="utf-8")
    return str(p)


def test_h1_a_pipeline_file_with_an_expression_cannot_reach_python(tmp_path, monkeypatch):
    """探針 p01: 指示の引数に式を書いたパイプラインのファイル → 変換は断られ、どの入口からも走らない。"""
    marker = tmp_path / "MARKER.txt"
    pipe = _pipeline_file(tmp_path, ["dev_set_lut (__import__('pathlib').Path(r'%s').write_text('pwned'))" % marker])
    asked = []
    monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *a: asked.append(a) or True)
    win, _m = _launch(tmp_path, monkeypatch, start_mode="pipeline")
    try:
        pm = win._pymode
        win._open_pipe_path(pipe)
        _pump(0.3)
        assert pm.mode == "pipeline" and "__import__" in win._program["edit"].toPlainText()
        runs0 = pm.state.get("pymode_runs", 0)
        assert pm.convert_to_python() is False and pm.mode == "pipeline"
        assert pm.run() is False and pm.step() is False and pm.run_selection() is False   # パイプラインの文面は Python として走らない
        assert pm.wait_idle(5) and pm.state.get("pymode_runs", 0) == runs0
        win._program["run"](True)                                        # パイプラインとしての実行(指示の引数は評価しない)
        _pump(0.5)
    finally:
        _close(win)
    assert not marker.exists()


def test_h1_a_converted_pipeline_file_asks_before_the_first_run(tmp_path, monkeypatch):
    pipe = _pipeline_file(tmp_path, ["dev_set_lut (gray)"])
    asked = []
    answer = {"v": False}
    monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *a: asked.append(a) or answer["v"])
    win, _m = _launch(tmp_path, monkeypatch, start_mode="pipeline")
    try:
        pm = win._pymode
        win._open_pipe_path(pipe)
        _pump(0.3)
        assert pm.pipe_source == os.path.abspath(pipe)
        assert pm.convert_to_python() is True and pm.active
        assert win._program["edit"].toPlainText().splitlines()[0] == "dev_set_lut('gray')"
        assert pm.origin == "file" and pm.session_trusted is False        # 「手で打った」扱いにしない
        runs0 = pm.state.get("pymode_runs", 0)
        _f5(win)
        assert len(asked) == 1 and pm.state.get("pymode_runs", 0) == runs0     # 断った: 走っていない
        assert os.path.basename(pipe) in asked[0][2]                           # どのファイルから来たかを言う
        answer["v"] = True
        res = _f5(win)
        assert len(asked) == 2 and res.ok, res.errors
        _f5(win)
        assert len(asked) == 2                                            # 確認済みの同じ文面は聞かない
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# H2: 変数の表は利用者のコードを呼ばない                                          #
# --------------------------------------------------------------------------- #
_HOSTILE = ("CALLED = []\n"
            "class Evil:\n"
            "    def __repr__(self):\n"
            "        CALLED.append('repr')\n"
            "        while True:\n"
            "            pass\n"
            "    __str__ = __repr__\n"
            "class Liar:\n"
            "    @property\n"
            "    def __class__(self):\n"
            "        CALLED.append('class')\n"
            "        while True:\n"
            "            pass\n"
            "class S(str):\n"
            "    def __len__(self):\n"
            "        CALLED.append('len')\n"
            "        while True:\n"
            "            pass\n"
            "class L(list):\n"
            "    def __len__(self):\n"
            "        CALLED.append('len')\n"
            "        return 10 ** 9\n"
            "    def __iter__(self):\n"
            "        CALLED.append('iter')\n"
            "        return iter(())\n"
            "e = Evil()\nxs = [Evil(), 1]\nd = {'k': (Evil(),)}\nli = Liar()\ns = S('abc')\nl = L([1, 2, 3])\n"
            "big = list(range(10 ** 6))\nglobals()[7] = 'not a string key'\n")


def test_h2_the_variable_table_never_calls_user_code():
    """探針 p02: ``__repr__`` が戻らない物が名前空間にあっても、実行は時間の上限の内に戻る。"""
    box = {}
    th = threading.Thread(target=lambda: box.setdefault("r", sp.run_program(_HOSTILE, IMG, time_limit_s=5.0)),
                          daemon=True)
    t0 = time.perf_counter()
    th.start()
    th.join(20)
    assert not th.is_alive(), "run_program did not return: the variable table called user code that never returns"
    r = box["r"]
    assert r.ok, r.errors
    assert time.perf_counter() - t0 < 10
    assert r.values["CALLED"] == []                                       # 何も呼ばれていない
    rows = {v.name: v.summary for v in r.variables}
    assert len(rows) >= 8
    assert rows["e"] == "Evil" and rows["li"] == "Liar" and rows["s"] == "S"
    assert rows["xs"] == "list[2] [<Evil>, 1]" and rows["d"] == "dict[1] {'k': (<Evil>,)}"
    assert rows["l"] == "L[3]"                                            # 基底の長さ(派生の __len__ は呼ばない)
    assert rows["big"] == "list[1000000]"                                 # 全文の repr を作らない
    assert 7 not in r.values


def test_h2_summaries_of_plain_values_are_unchanged():
    d = sp.describe_value
    assert d([1, 2, 3])[2] == "list[3] [1, 2, 3]" and d((1,))[2] == "tuple[1] (1,)"
    assert d({"a": 1.5})[2] == "dict[1] {'a': 1.5}" and d(set())[2] == "set[0] set()"
    assert d("abc")[2] == "'abc'" and d(3)[2] == "3" and d(None)[2] == "None" and d(True)[2] == "True"
    assert d(np.float64(1.5))[2] == "1.5" and d(np.int32(7))[:2] == ("int", None)
    assert d("x" * 100)[2] == "'" + "x" * 56 + "…'"
    assert d(np.zeros((2, 2)))[2].startswith("ndarray 2×2 [[0. 0.]")
    assert d(np.zeros((64, 64)))[2] == "ndarray 64×64 float64"
    assert d(np.array([object()], dtype=object))[2] == "ndarray 1 object"   # 要素の repr を呼ばない
    assert d(len)[2] == "len" and d(int)[2] == "int"


def test_h2_the_window_recovers_when_a_value_has_a_repr_that_never_returns(tmp_path, monkeypatch):
    win, _m = _launch(tmp_path, monkeypatch, time_limit=5)
    try:
        pm = win._pymode
        _set_text(win, "# python\nclass Evil:\n    def __repr__(self):\n        while True:\n            pass\n"
                       "xs = [Evil()]\nshow(img)\n")
        res = _f5(win, timeout=15)
        assert res.ok and not pm.running
        pm.set_mode("pipeline")
        assert pm.mode == "pipeline"                                      # 「走っている」として断られない
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# H3: 止められずに残した実行                                                     #
# --------------------------------------------------------------------------- #
def _late_writer(tmp_path, seconds=1.6):
    return ("import os, time\n"
            "try:\n"
            "    time.sleep(%r)\n"
            "except BaseException:\n"
            "    pass\n"
            "os.environ['ZZ_STUDIO_LATE'] = 'leaked'\n"
            "os.chdir(%r)\n") % (seconds, str(tmp_path))


def test_h3_an_abandoned_run_blocks_the_next_run_and_is_restored_again_when_it_ends(tmp_path):
    """探針 p03: 諦めた実行は、戻した後にも環境変数と作業フォルダを書き換える。生きている間は次を始めず、
    終わった所でもう一度戻す。"""
    assert _wait_no_abandoned()
    cwd = os.getcwd()
    assert "ZZ_STUDIO_LATE" not in os.environ
    try:
        r = sp.run_program(_late_writer(tmp_path), IMG, time_limit_s=0.2, config="release")
        assert r.stopped == "unstoppable", (r.stopped, r.errors)
        assert len(sp.abandoned_runs()) == 1
        assert len(r.notes) >= 2, r.notes
        assert any("new runs are refused" in n for n in r.notes), r.notes
        nxt = sp.run_program("x = 1\n", IMG)                              # 残っている間は走らせない
        assert not nxt.ran and nxt.errors and "still running in the background (1)" in nxt.errors[0]
        assert nxt.not_run_reason == nxt.errors[0] and "x" not in nxt.values
        ev = sp.evaluate("1 + 1", {"__builtins__": builtins}, time_limit_s=1.0)
        assert ev["value"] is None and "still running in the background" in ev["error"]
        assert _wait_no_abandoned(), "the abandoned run did not end"
        assert "ZZ_STUDIO_LATE" not in os.environ, "the late write of the abandoned run was not undone"
        assert os.getcwd() == cwd
        ok = sp.run_program("x = 1\n", IMG)
        assert ok.ok and ok.values["x"] == 1
    finally:
        _wait_no_abandoned()
        os.environ.pop("ZZ_STUDIO_LATE", None)
        os.chdir(cwd)


def test_h3_the_window_says_that_the_earlier_run_is_still_running(tmp_path, monkeypatch):
    assert _wait_no_abandoned()
    cwd = os.getcwd()
    win, _m = _launch(tmp_path, monkeypatch, time_limit=0.3)
    try:
        pm = win._pymode
        pm.set_config("release")
        _set_text(win, "# python\n" + _late_writer(tmp_path, 6.0))     # 並行の負荷でも、次の F5 より先に終わらない長さ
        res = _f5(win, timeout=10)
        assert res.stopped == "unstoppable"
        runs0 = pm.state.get("pymode_runs", 0)
        _set_text(win, "# python\nshow(gaussian(img, 0.2))\n")
        from PySide6 import QtCore
        from PySide6.QtTest import QTest
        QTest.keyClick(win._program["edit"], QtCore.Qt.Key_F5)
        _pump(0.2)
        assert not pm.running and pm.state.get("pymode_runs", 0) == runs0   # 始めていない
        assert "still running in the background" in pm.output.toPlainText().splitlines()[-1]
        assert "still running in the background" in win._program["status"]().toolTip()
        assert _wait_no_abandoned()
        assert _f5(win).ok                                                # 終われば使い続けられる
    finally:
        _wait_no_abandoned()
        os.environ.pop("ZZ_STUDIO_LATE", None)
        os.chdir(cwd)
        _close(win)


# --------------------------------------------------------------------------- #
# H4: 実行の後に戻す物(全部を見る)                                              #
# --------------------------------------------------------------------------- #
def test_h4_every_restored_item_is_restored_and_named(tmp_path):
    """探針 p03b + 今までの 5 つ。``RESTORED_STATE`` の全部を 1 つずつ壊して、戻る事と notes に出る事を見る。"""
    import warnings
    before = {
        "sys.path": list(sys.path), "os.environ": dict(os.environ), "cwd": os.getcwd(),
        "builtins": dict(vars(builtins)), "warnings": list(warnings.filters),
        "sys.stdout": sys.stdout, "sys.stderr": sys.stderr, "sys.stdin": sys.stdin,
        "sys.excepthook": sys.excepthook, "sys.displayhook": sys.displayhook,
        "sys.unraisablehook": sys.unraisablehook, "threading.excepthook": threading.excepthook,
        "recursion limit": sys.getrecursionlimit(),
    }
    assert set(before) == set(sp.RESTORED_STATE), set(before) ^ set(sp.RESTORED_STATE)
    prog = ("import sys, os, io, builtins, threading, warnings\n"
            "sys.path.insert(0, 'ZZZ_PATH')\n"
            "os.environ['ZZ_STUDIO_LEAK'] = '1'\n"
            "os.chdir(%r)\n"
            "builtins.ZZ_STUDIO_LEAK = 1\n"
            "warnings.simplefilter('ignore')\n"
            "sys.stdout = io.StringIO()\nsys.stderr = io.StringIO()\nsys.stdin = io.StringIO()\n"
            "sys.excepthook = lambda *a: None\nsys.displayhook = lambda v: None\n"
            "sys.unraisablehook = lambda u: None\nthreading.excepthook = lambda a: None\n"
            "sys.setrecursionlimit(sys.getrecursionlimit() + 123)\n") % str(tmp_path)
    try:
        r = sp.run_program(prog, IMG)
        after = {
            "sys.path": list(sys.path), "os.environ": dict(os.environ), "cwd": os.getcwd(),
            "builtins": dict(vars(builtins)), "warnings": list(warnings.filters),
            "sys.stdout": sys.stdout, "sys.stderr": sys.stderr, "sys.stdin": sys.stdin,
            "sys.excepthook": sys.excepthook, "sys.displayhook": sys.displayhook,
            "sys.unraisablehook": sys.unraisablehook, "threading.excepthook": threading.excepthook,
            "recursion limit": sys.getrecursionlimit(),
        }
    finally:                                                             # 落ちても試験のプロセスを壊したままにしない
        sys.stdout, sys.stderr, sys.stdin = before["sys.stdout"], before["sys.stderr"], before["sys.stdin"]
        sys.excepthook, sys.displayhook = before["sys.excepthook"], before["sys.displayhook"]
        sys.unraisablehook, threading.excepthook = before["sys.unraisablehook"], before["threading.excepthook"]
        sys.setrecursionlimit(before["recursion limit"])
        os.chdir(before["cwd"])
        os.environ.pop("ZZ_STUDIO_LEAK", None)
        sys.path[:] = before["sys.path"]
        vars(builtins).pop("ZZ_STUDIO_LEAK", None)
    assert r.ok, r.errors
    for name in sp.RESTORED_STATE:
        if name in ("sys.path", "os.environ", "cwd", "warnings", "recursion limit"):
            assert after[name] == before[name], name
        elif name == "builtins":
            assert after[name].keys() == before[name].keys(), name
        else:
            assert after[name] is before[name], name
    notes = [n for n in r.notes if n.startswith("restored after the run: ")]
    assert len(notes) == 1, r.notes
    named = notes[0][len("restored after the run: "):].split(", ")
    assert sorted(named) == sorted(sp.RESTORED_STATE), named               # 戻した物は全部名前で言う


# --------------------------------------------------------------------------- #
# M1: Qt を直接使うプログラム                                                    #
# --------------------------------------------------------------------------- #
def _in_thread(fn):
    box = {}
    th = threading.Thread(target=lambda: box.setdefault("r", fn()), daemon=True)
    th.start()
    th.join(30)
    assert not th.is_alive()
    return box["r"]


def test_m1_qt_programs_are_refused_off_the_gui_thread_without_a_bridge(monkeypatch):
    """探針 p04: 橋が無いまま作業スレッドで QWidget を作ると未定義の動作。走らせずに、分かる文で断る。"""
    monkeypatch.setattr(sp, "GUI_BRIDGE", None)
    prog = "x = 1\nfrom PySide6 import QtWidgets\nw = QtWidgets.QLabel('hi')\nw.show()\n"
    r = _in_thread(lambda: sp.run_program(prog, IMG))
    assert not r.ran and not r.ok and r.error_line == 2
    assert r.errors[0].startswith("line 2: not run: this program imports Qt directly") and "x" not in r.values
    r = sp.run_program("from PySide6 import QtCore\nv = QtCore.qVersion()\n", IMG)   # main スレッド(Studio の外)は今までどおり
    assert r.ok and r.values["v"]
    monkeypatch.setattr(sp, "GUI_BRIDGE", type("B", (), {"call": staticmethod(lambda fn, *a: fn(*a)),
                                                         "close": staticmethod(lambda w: None)})())
    r = _in_thread(lambda: sp.run_program("from PySide6 import QtCore\nv = QtCore.qVersion()\n", IMG))
    assert r.ok                                                           # 橋があれば作業スレッドでも走る


def test_m1_the_window_reports_not_run(tmp_path, monkeypatch):
    monkeypatch.setattr(sp, "GUI_BRIDGE", None)
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        _set_text(win, "# python\nfrom PySide6 import QtWidgets\nw = QtWidgets.QLabel('hi')\nw.show()\n")
        res = _f5(win)
        assert not res.ran and res.error_line == 2
        out = pm.output.toPlainText()
        assert "imports Qt directly" in out and "ran in" not in out.split("──")[-1]
        assert 2 in win._program["edit"].errors()
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# M3: 補完・ホバー・要約は利用者のコードを呼ばない                                 #
# --------------------------------------------------------------------------- #
CALLED = []


class Tricky:
    visible = 1

    def __init__(self):
        self.inst = 2

    def __dir__(self):
        CALLED.append("__dir__")
        return ["a", "b"]

    def __getattr__(self, name):
        CALLED.append("__getattr__(%s)" % name)
        return 1

    @property
    def prop(self):
        CALLED.append("property prop")
        return 1

    def method(self):
        return 1


class FakeStr:
    @property
    def __class__(self):
        CALLED.append("__class__ property")
        return str

    def __getitem__(self, k):
        CALLED.append("__getitem__")
        return "x"

    def __len__(self):
        CALLED.append("__len__")
        return 1


class SlowClass:
    @property
    def __class__(self):
        CALLED.append("__class__ slow")
        time.sleep(3)
        return SlowClass


class EvilStr(str):
    def __len__(self):
        CALLED.append("EvilStr.__len__")
        return 3

    def __getitem__(self, k):
        CALLED.append("EvilStr.__getitem__")
        return "x"


def _hostile_ns():
    return {"t": Tricky(), "fs_": FakeStr(), "slow": SlowClass(), "es": EvilStr("abc"), "box": [Tricky()],
            "n": 3, "arr": np.zeros((4, 4)), "np": np}


@pytest.mark.parametrize("use_jedi", [False, True])
def test_m3_completion_hover_and_signature_do_not_call_user_code(use_jedi):
    """探針 p05: ``__class__`` のプロパティ 1 つで補完が 45 秒止まっていた。"""
    if use_jedi and not comp.jedi_available():
        pytest.skip("jedi is not installed")
    pm_mod._configure_jedi()
    ns = _hostile_ns()
    prov = comp.default_provider(namespace=lambda: ns, catalog=None, use_jedi=use_jedi)
    CALLED.clear()
    t0 = time.perf_counter()
    got = {}
    for text in ("t.", "t.prop.", "fs_.", "slow.", "es.", "box[0].", "arr.sha", "np.ze"):
        got[text] = [c.name for c in prov.complete(text, 0, len(text))]
    prov.hover("t.prop", 0, 4)
    prov.hover("slow", 0, 2)
    prov.signature("t.zz(", 0, 5)
    prov.signature("t.method(", 0, 9)
    dt = time.perf_counter() - t0
    assert CALLED == [], CALLED
    assert dt < 8.0, dt                                                   # 止まらない(以前は 45 s)
    # 利用者のクラスの物: 静的な名前(型の MRO とインスタンスの __dict__)が候補に出る。__dir__ の嘘の名前は出ない
    assert {"prop", "method", "visible", "inst"} <= set(got["t."]), got["t."]
    assert "a" not in got["t."] and "b" not in got["t."]
    assert "shape" in got["arr.sha"] and "zeros" in got["np.ze"]             # ライブラリの物は今までどおり


def test_m3_only_plain_values_are_handed_to_jedi():
    ns = _hostile_ns()
    plain = sorted(k for k, v in ns.items() if safe.is_plain_value(v))
    assert plain == ["arr", "n", "np"]                                    # 利用者の物と入れ物は渡さない
    assert not safe.is_inert(ns["t"]) and not safe.is_inert(Tricky) and safe.is_inert(np) and safe.is_inert([])
    assert safe.is_library_type(str) and safe.is_library_type(np.ndarray) and not safe.is_library_type(EvilStr)
    assert safe.isinst(ns["es"], str) and not safe.isinst(ns["fs_"], str)
    CALLED.clear()
    assert safe.static_names(ns["t"]).count("inst") == 1 and "prop" in safe.static_names(ns["t"])
    assert "zeros" in safe.static_names(np)
    assert CALLED == []


def test_m3_the_variables_summary_does_not_read_class_or_user_methods():
    ns = _hostile_ns()
    CALLED.clear()
    t0 = time.perf_counter()
    s_fake, s_slow, s_es = V.summarize(ns["fs_"]), V.summarize(ns["slow"]), V.summarize(ns["es"])
    V.summarize(ns["box"])
    V.children(ns["t"])
    V.children(ns["es"])
    V.candidate_attributes(ns["t"])
    V.fingerprint(ns["fs_"])
    V.fingerprint(ns["es"])
    dt = time.perf_counter() - t0
    assert CALLED == [], CALLED
    assert dt < 2.0, dt
    assert s_fake.kind == "object" and s_slow.kind == "object"            # str に化けた物を str として扱わない
    assert s_es.kind == "object" and s_es.type_name.endswith("EvilStr")   # 派生した str は型の名前だけ
    assert V.summarize("abc").kind == "str" and V.summarize(np.zeros(3)).kind == "ndarray"
    assert "prop" in V.candidate_attributes(ns["t"]) and "a" not in V.candidate_attributes(ns["t"])


# --------------------------------------------------------------------------- #
# M4: 変数の欄の編集                                                            #
# --------------------------------------------------------------------------- #
def test_m4_an_edit_in_the_variables_panel_reaches_the_run_namespace(tmp_path, monkeypatch):
    """探針 p08: 欄では x=5 と見えるのに、名前空間は 1 のままだった。"""
    from PySide6 import QtGui
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        _set_text(win, "# python\nx = 1\nshow(img)\nprint('x is', x)\n")
        _f5(win)
        assert pm.namespace["x"] == 1 and pm.var_source.ns["x"] == 1
        pm.var_source.set_value((("name", "x"),), 5)                      # 欄の編集が呼ぶ物
        assert pm.var_source.ns["x"] == 5 and pm.namespace["x"] == 5
        c = QtGui.QTextCursor(ed.document().findBlockByNumber(3))
        ed.setTextCursor(c)
        assert pm.run_selection() and pm.wait_idle(10)
        _pump(0.1)
        assert "x is 5" in pm.output.toPlainText().strip().splitlines()[-2:]
        # 関数の中で止まっている時の局所変数は、外から書き換えられない: 見かけだけ変えずに断る
        _set_text(win, "# python\ng = 1\ndef f(k):\n    return k + g\nout = f(4)\nshow(img)\n")
        pm.toggle_breakpoint(4)
        _f5(win)
        assert pm.var_source.ns["k"] == 4
        import studio_pyedit_values as pv
        with pytest.raises(pv.EditError):
            pm.var_source.set_value((("name", "k"),), 9)
        assert pm.var_source.ns["k"] == 4
        pm.var_source.set_value((("name", "g"),), 100)                    # モジュールの変数は、続きの実行に効く
        res = _f5(win)
        assert res.ok and res.values["out"] == 104
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# M5: 従来の Python エディタにファイルから開いた .py                              #
# --------------------------------------------------------------------------- #
def test_m5_a_dropped_py_file_is_confirmed_before_it_runs_in_the_python_editor(tmp_path, monkeypatch):
    marker = tmp_path / "ran.txt"
    script = tmp_path / "dropped.py"
    script.write_text("open(%r, 'a').write('x')\n" % str(marker), encoding="utf-8")
    asked = []
    answer = {"v": False}
    monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *a: asked.append(a) or answer["v"])
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        win.drop_handler([str(script)])
        _pump(0.3)
        pe = win._pyedit
        ed = pe["editor"]()
        assert ed is not None and ed._path == str(script) and ed._from_file is True
        dlg = pe["dlg"]

        def run_and_wait():
            pe["run"]()
            end = time.monotonic() + 30
            while dlg._proc is not None and time.monotonic() < end:
                _pump(0.05)
            assert dlg._proc is None, "the script did not finish"
        run_and_wait()
        assert len(asked) == 1 and not marker.exists()                    # 断った: 走っていない
        assert str(script) in asked[0][2]
        answer["v"] = True
        run_and_wait()
        assert len(asked) == 2 and marker.read_text() == "x"
        run_and_wait()
        assert len(asked) == 2 and marker.read_text() == "xx"             # 確認した後は聞かない
        pe["open_path"](str(script))                                      # 同じ中身を開き直す: 台帳が覚えている
        run_and_wait()
        assert len(asked) == 2
        script.write_text("open(%r, 'a').write('y')\n" % str(marker), encoding="utf-8")
        pe["open_path"](str(script))                                      # 中身が変わった: 聞き直す
        answer["v"] = False
        run_and_wait()
        assert len(asked) == 3 and marker.read_text() == "xxx"
        pe["new"]()                                                       # 自分で打った物は聞かない
        n = len(asked)
        pe["editor"]().setPlainText("print(1)\n")
        run_and_wait()
        assert len(asked) == n
    finally:
        try:
            win._pyedit["dlg"].close()
        except Exception:                                                 # noqa: BLE001
            pass
        _close(win)


# --------------------------------------------------------------------------- #
# L1: 出力の上限 / E2: 自動の書き出し                                            #
# --------------------------------------------------------------------------- #
def test_l1_captured_output_is_bounded_and_says_what_was_dropped(monkeypatch):
    monkeypatch.setattr(sp, "MAX_STDOUT_CHARS", 10_000)
    r = sp.run_program("for i in range(5000):\n    print('line %06d' % i)\n", IMG)
    assert r.ok and r.stdout_total == 5000 * 12
    assert r.stdout.startswith("… (%d earlier characters of output dropped)\n" % (5000 * 12 - 10_000))
    assert r.stdout.endswith("line 004999\n") and len(r.stdout) < 10_200   # 古い方から捨てる
    small = sp.run_program("# python\nprint('a')\nprint('b')\n", IMG)
    assert small.ok and small.stdout == "a\nb\n" and small.stdout_total == 4
    buf = sp._BoundedOutput(limit=8)
    for ch in "0123456789abcdefghij":
        buf.write(ch)
    assert buf.getvalue().endswith("cdefghij") and buf.total == 20


def test_l1_the_output_pane_keeps_a_bounded_number_of_lines(tmp_path, monkeypatch):
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        _set_text(win, "# python\nfor i in range(20000):\n    print('row', i)\nshow(img)\n")
        res = _f5(win, timeout=30)
        assert res.ok
        assert pm.output.document().blockCount() <= pm_mod.MAX_OUTPUT_LINES + 1
        assert "row 19999" in pm.output.toPlainText()                     # 新しい方が残る
        pm._out("y" * (pm_mod.MAX_OUTPUT_CHARS + 50))
        assert "50" in pm.output.toPlainText().splitlines()[-2] and len(pm.output.toPlainText()) < 2 * pm_mod.MAX_OUTPUT_CHARS + 400_000
    finally:
        _close(win)


def test_e2_unsaved_text_is_written_out_while_typing_and_comes_back_after_a_crash(tmp_path, monkeypatch):
    win, _m = _launch(tmp_path, monkeypatch, name="crash.ini")
    try:
        pm = win._pymode
        assert pm._autosave.isActive() and pm._autosave.interval() == pm_mod.AUTOSAVE_MS
        assert pm.autosave_now() is False                                 # 変わっていなければ書かない
        _set_text(win, "# python\nprecious = 42\nshow(img)\n")
        assert pm.autosave_now() is True and pm.autosave_now() is False
        # 落ちた事にする: 閉じる処理(save_state)を通さずに、同じ設定で起動し直す
        win2, _m2 = _launch(tmp_path, monkeypatch, name="crash.ini")
        try:
            assert win2._program["edit"].toPlainText() == "# python\nprecious = 42\nshow(img)\n"
            assert win2._pymode.mode == "python"
        finally:
            _close(win2)
    finally:
        _close(win)

# -*- coding: utf-8 -*-
"""Studio の Python のモード: 第 2 回の独立レビュー(2026-11-13)の指摘の回帰試験。

目標は 2 つ: (a) 確認していないコードが走らない (b) 普通に書いたコードのうっかり(重い ``__str__``、``plt.show()``、
スレッド)で Studio が固まったり戻らなくなったりしない。

* R1: 実行の結果を文字にする処理は、全部が作業スレッドの中・見張りの内側(上限つき)。呼び出し側は str だけを受け取る。
* R2: 「ライブラリの型」は名前でなく実体で決める。メタクラスの ``__eq__`` / ``__mro__`` / ``__name__`` を通さない。
* R3: 作業スレッドからの GUI の部品の import を断る。matplotlib は Agg、``plt.show()`` は図を画像の欄へ。
* R4 / R10: 従来の Python エディタは、確認した文面 = 走らせる文面。ファイルから来た文面は入口に依らず確認する。
* R5: 変数の欄の ``__repr__`` 用のスレッドは溜めない。変えた環境は戻す。残っている間は実行を始めずに知らせる。
* R6: プログラムが起こして残したスレッドを知らせる。R9: 例外の文とツールチップの上限。
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
import studio_program_i18n as spi
import studio_pyedit_complete as comp
import studio_pyedit_i18n as pi
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


def _launch(tmp_path, monkeypatch, start_mode="auto", time_limit=None):
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


def _f5(win, timeout=20):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    QTest.keyClick(win._program["edit"], QtCore.Qt.Key_F5)
    assert win._pymode.wait_idle(timeout)
    _pump(0.1)
    return win._pymode.last


def _bounded(fn, seconds=15.0):
    """*fn* を別スレッドで呼び、*seconds* 以内に戻ることを確かめて結果を返す(戻らない = 見張りの外で固まった)。"""
    box = {}
    th = threading.Thread(target=lambda: box.setdefault("r", fn()), daemon=True)
    t0 = time.perf_counter()
    th.start()
    th.join(seconds)
    assert not th.is_alive(), "did not return in %.0f s: user code ran outside the watchdog" % seconds
    return box["r"], time.perf_counter() - t0


def _wait(cond, timeout=15.0):
    end = time.monotonic() + timeout
    while not cond() and time.monotonic() < end:
        time.sleep(0.05)
    return cond()


# --------------------------------------------------------------------------- #
# R1: 結果を文字にする処理は見張りの内側                                          #
# --------------------------------------------------------------------------- #
_LOOPING = {
    "metaclass __eq__": "class M(type):\n    def __eq__(cls, o):\n        while True:\n            pass\n"
                        "    __hash__ = type.__hash__\nclass E(metaclass=M):\n    pass\nx = E()\n",
    "metaclass __name__": "class M(type):\n    @property\n    def __name__(cls):\n        while True:\n            pass\n"
                          "class E(metaclass=M):\n    pass\nx = E()\n",
    "exception __str__": "class Boom(Exception):\n    def __str__(self):\n        while True:\n            pass\n"
                         "raise Boom('x')\n",
    "exception __class__": "class Boom(Exception):\n    @property\n    def __class__(self):\n        while True:\n"
                           "            pass\nraise Boom('x')\n",
    "exception __getattribute__": "class Boom(Exception):\n    def __getattribute__(self, n):\n        while True:\n"
                                  "            pass\nraise Boom('x')\n",
    "sys.exit(obj) __repr__": "import sys\nclass C:\n    def __repr__(self):\n        while True:\n            pass\n"
                              "    __str__ = __repr__\nsys.exit(C())\n",
    "show(obj) __class__": "class C:\n    @property\n    def __class__(self):\n        while True:\n            pass\n"
                           "show(C())\n",
    "exception arg __repr__": "class A:\n    def __repr__(self):\n        while True:\n            pass\n"
                              "raise KeyError(A())\n",
}


@pytest.mark.parametrize("config", ["debug", "release"])
@pytest.mark.parametrize("name", sorted(_LOOPING))
def test_r1_user_code_that_never_returns_cannot_keep_the_run_from_ending(name, config):
    """探針 q02: 6 つの入口(+2)。どれも実行は終わる(時間の上限 2 s、結果を文字にする段の上限 2 s)。"""
    r, dt = _bounded(lambda: sp.run_program("# python\n" + _LOOPING[name], IMG, time_limit_s=2.0, config=config))
    assert dt < 9.0, dt
    assert r.ran and r.stopped is None, (r.stopped, r.errors)             # プログラムの本体は時間切れではない
    if "exception" in name:
        assert len(r.errors) == 1 and r.error_line and r.errors[0].startswith("line %d: " % r.error_line)
        assert ("Boom" in r.errors[0]) or ("KeyError" in r.errors[0])
    if name in ("exception __str__", "exception arg __repr__"):
        assert "did not return in time" in r.errors[0]                    # 文は作れなかった、と正直に言う
    if name == "sys.exit(obj) __repr__":
        assert r.errors == ["line 8: the program called exit(<C>)"]
    assert "x" in r.values or name.startswith(("exception", "sys.exit", "show"))


def test_r1_identity_paths_never_call_the_hooks():
    """止まらないフックでなく数えるフックで、「1 回も呼ばれない」ことを見る(速く戻っただけでは証明にならない)。"""
    prog = ("# python\nCALLED = []\n"
            "class M(type):\n"
            "    def __eq__(cls, o):\n        CALLED.append('eq')\n        return False\n"
            "    __hash__ = type.__hash__\n"
            "    @property\n    def __name__(cls):\n        CALLED.append('name')\n        return 'Fake'\n"
            "    @property\n    def __mro__(cls):\n        CALLED.append('mro')\n        return (object,)\n"
            "class E(metaclass=M):\n"
            "    @property\n    def __class__(self):\n        CALLED.append('class')\n        return int\n"
            "    def __repr__(self):\n        CALLED.append('repr')\n        return 'E()'\n"
            "    def __len__(self):\n        CALLED.append('len')\n        return 3\n"
            "x = E()\nxs = [E(), 1]\nd = {'k': E()}\nshow(x)\n")
    r = sp.run_program(prog, IMG)
    assert r.ok, r.errors
    assert r.values["CALLED"] == []
    rows = {v.name: v.summary for v in r.variables}
    assert rows["x"] == "E" and rows["xs"] == "list[2] [<E>, 1]" and rows["d"] == "dict[1] {'k': <E>}"
    assert r.output is r.values["x"] and r.output_sort == "E"
    ex = sp.run_program("# python\nCALLED = []\nclass B(Exception):\n"
                        "    @property\n    def __class__(self):\n        CALLED.append('class')\n        return B\n"
                        "    def __getattribute__(self, n):\n        CALLED.append('getattr ' + n)\n"
                        "        return object.__getattribute__(self, n)\n"
                        "    def __str__(self):\n        CALLED.append('str')\n        return 'text of B'\n"
                        "raise B()\n", IMG)
    assert ex.errors == ["line 14: B: text of B"]
    assert ex.values["CALLED"] == ["str"]                                 # __str__ を 1 回だけ(見張りの内側で)


def test_r1_an_ordinary_error_text_is_unchanged_and_long_text_is_clipped():
    r = sp.run_program("# python\nx = 1\ny = x / 0\n", IMG)
    assert r.errors == ["line 3: ZeroDivisionError: division by zero"] and r.values["x"] == 1
    r = sp.run_program("# python\nimport no_such_module_zz\n", IMG)
    assert r.errors[0].startswith("line 2: ModuleNotFoundError: No module named 'no_such_module_zz' — install it")
    r = sp.run_program("# python\nraise ValueError('x' * 20_000_000)\n", IMG)       # 探針 q02b: 20 MB の文
    assert len(r.errors[0]) < sp.MAX_ERROR_CHARS + 100 and r.errors[0].endswith("more characters)")
    r = sp.run_program("# python\nclass B(Exception):\n    def __str__(self):\n        return 1 / 0\nraise B()\n", IMG)
    assert r.errors == ["line 5: B: <the text of this B is not available: its __str__ raised ZeroDivisionError>"]
    r = sp.run_program("# python\nimport sys\nsys.exit('bye')\n", IMG)
    assert r.errors == ["line 3: the program called exit('bye')"]
    tr = pi.make_tr("ja")
    shown = spi.localize("line 5: B: <the text of this B is not available: its __str__ did not return in time>", tr)
    assert shown.startswith("5 行目: B: <この B の文は出せません")


def test_r1_a_time_limit_stop_still_lists_the_variables():
    """プログラムを時間切れで止めた後の「文字にする段」を、止めの例外が壊さない(段の切り替えで撃つのをやめる)。"""
    for _ in range(3):
        r = sp.run_program("# python\nk = 7\nwhile True:\n    pass\n", IMG, time_limit_s=0.3)
        assert r.stopped == "time_limit" and r.values.get("k") == 7, (r.stopped, r.notes, list(r.values))
        r = sp.run_program("# python\nk = 7\nwhile True:\n    pass\n", IMG, time_limit_s=0.3, config="release")
        assert r.stopped == "time_limit" and r.values.get("k") == 7, (r.stopped, r.notes, list(r.values))


def test_r1_the_window_recovers_and_only_shows_plain_images(tmp_path, monkeypatch):
    win, _m = _launch(tmp_path, monkeypatch, time_limit=2)
    try:
        pm = win._pymode
        _set_text(win, "# python\n" + _LOOPING["exception __str__"])
        res = _f5(win, timeout=15)
        assert not pm.running and "did not return in time" in res.errors[0]
        _set_text(win, "# python\n" + _LOOPING["show(obj) __class__"])
        res = _f5(win, timeout=15)
        assert res.ok and not pm.running
        assert "not an image (C)" in pm.output.toPlainText()               # GUI は素の配列だけを表示へ渡す
        _set_text(win, "# python\nraise ValueError('x' * 5_000_000)\n")
        res = _f5(win, timeout=15)
        status = win._program["status"]()
        assert len(status.toolTip()) <= pm_mod.MAX_TOOLTIP_CHARS + 10 and len(status.text()) < 200
        assert len(pm.output.toPlainText()) < 400_000
        pm.set_mode("pipeline")
        assert pm.mode == "pipeline"
    finally:
        _close(win)


# --------------------------------------------------------------------------- #
# R2: ライブラリの型は実体で決める                                               #
# --------------------------------------------------------------------------- #
CALLED = []


class FakesJson:
    __module__ = "json"                              # クラス本体で名前を偽る

    def __dir__(self):
        CALLED.append("__dir__")
        return ["a"]

    def __getattr__(self, n):
        CALLED.append("__getattr__ " + n)
        return 1


class Meta(type):
    def __eq__(cls, other):
        CALLED.append("Meta.__eq__")
        return False
    __hash__ = type.__hash__

    @property
    def __mro__(cls):
        CALLED.append("Meta.__mro__")
        return (object,)

    @property
    def __name__(cls):
        CALLED.append("Meta.__name__")
        return "int"

    @property
    def __dict__(cls):
        CALLED.append("Meta.__dict__")
        return {}


class WithMeta(metaclass=Meta):
    def __init__(self):
        self.field = 1


def test_r2_library_types_are_decided_by_identity_not_by_name():
    """探針 q03: ``__module__ = 'json'`` や ``__name__ = 'numpy'`` で「ライブラリの型」に化けられた。"""
    import collections
    import fractions
    import pathlib
    for t in (int, str, list, np.ndarray, np.float64, collections.OrderedDict, fractions.Fraction, pathlib.PurePath,
              type(len), type(sys), type(None)):
        assert safe.is_library_type(t), t
    assert not safe.is_library_type(FakesJson) and not safe.is_inert(FakesJson())
    ns = {"__name__": "numpy"}
    exec("class X:\n    def __dir__(self):\n        return ['a']\n", ns)               # プログラムが __name__ を偽る
    assert safe.module_of(ns["X"]) == "numpy" and not safe.is_library_type(ns["X"])
    assert not safe.is_plain_value(ns["X"]()) and not safe.is_inert(ns["X"]())

    def local_class():
        class Inner:
            pass
        return Inner
    assert not safe.is_library_type(local_class())                        # 辿れない型は利用者の物として扱う側
    CALLED.clear()
    assert safe.static_names(FakesJson()) and "a" not in safe.static_names(FakesJson())
    assert CALLED == []


@pytest.mark.parametrize("use_jedi", [False, True])
def test_r2_completion_and_summaries_do_not_go_through_the_metaclass(use_jedi):
    if use_jedi and not comp.jedi_available():
        pytest.skip("jedi is not installed")
    pm_mod._configure_jedi()
    ns = {"m": WithMeta(), "f": FakesJson(), "n": 3}
    prov = comp.default_provider(namespace=lambda: ns, catalog=None, use_jedi=use_jedi)
    CALLED.clear()
    t0 = time.perf_counter()
    for text in ("m.", "f.", "m.fie"):
        prov.complete(text, 0, len(text))
    prov.hover("m", 0, 1)
    assert safe.is_plain_value(ns["m"]) is False and safe.is_plain_value(ns["n"]) is True
    s = V.summarize(ns["m"])
    V.children(ns["m"])
    V.fingerprint(ns["m"])
    V.candidate_attributes(ns["m"])
    assert sp.describe_value(ns["m"])[2] == "WithMeta"
    assert CALLED == [], CALLED
    assert time.perf_counter() - t0 < 5.0
    assert s.kind == "object" and s.type_name.endswith("WithMeta")        # 名前は type 自身の記述子から


# --------------------------------------------------------------------------- #
# R3: GUI の部品の import と matplotlib                                          #
# --------------------------------------------------------------------------- #
_QT_DOORS = {
    "import statement inside exec": "exec('from PySide6 import QtWidgets')\n",
    "importlib.import_module": "import importlib\nm = importlib.import_module('PySide6.QtWidgets')\n",
    "__import__": "m = __import__('PySide6.QtWidgets')\n",
    "from-import of a submodule": "m = __import__('PySide6', fromlist=['QtWidgets'])\n",
    "tkinter": "m = __import__('tkinter')\n",
}


@pytest.mark.parametrize("door", sorted(_QT_DOORS))
def test_r3_gui_toolkits_cannot_be_imported_from_the_worker_thread(door, monkeypatch):
    """探針 q06: 構文木の検査をすり抜けて、作業スレッドで QWidget が作られていた。"""
    monkeypatch.setattr(sp, "GUI_BRIDGE", None)
    imp0, impmod0, env0 = builtins.__import__, importlib.import_module, os.environ.get("MPLBACKEND")
    r = sp.run_program("# python\nx = 1\n" + _QT_DOORS[door], IMG)
    assert not r.ok and len(r.errors) == 1
    assert "ImportError: Studio does not let a running program import" in r.errors[0], r.errors
    assert "m" not in r.values and r.values["x"] == 1
    # 見張りは実行の間だけ: 終わったら元の import と環境に戻っている
    assert builtins.__import__ is imp0 and importlib.import_module is impmod0
    assert os.environ.get("MPLBACKEND") == env0
    assert r.notes == [], r.notes                    # 自分で付けた物(import の見張り・MPLBACKEND)を「戻した」と言わない
    shown = spi.localize(r.errors[0], pi.make_tr("ja"))
    assert "import をさせません" in shown and "Studio does not let" not in shown


def test_r3_other_threads_and_ordinary_imports_are_not_refused(monkeypatch):
    monkeypatch.setattr(sp, "GUI_BRIDGE", None)
    seen = {}
    stop = threading.Event()

    def gui_side():                                   # Studio 自身のスレッドの import は通る
        while not stop.is_set():
            try:
                seen["mod"] = importlib.import_module("PySide6.QtCore").__name__
            except ImportError as e:                  # noqa: PERF203
                seen["err"] = str(e)
            time.sleep(0.005)
    th = threading.Thread(target=gui_side, daemon=True)
    th.start()
    try:
        r = sp.run_program("# python\nimport json, math, time\nimport numpy as np\ntime.sleep(0.2)\nv = json.dumps([1])\n",
                           IMG)
    finally:
        stop.set()
        th.join(2)
    assert r.ok, r.errors
    assert seen.get("mod") == "PySide6.QtCore" and "err" not in seen
    assert not sp._ImportGuard.refused("matplotlib.backends.backend_agg")
    assert sp._ImportGuard.refused("matplotlib.backends.backend_qtagg") and sp._ImportGuard.refused("PyQt5.QtCore")


#: R3 の matplotlib の試験の中身(子プロセスで回す)。PySide6 を読み込んだ Studio と同じ状態にしてから、プログラムを
#: 作業スレッドで走らせる。結果は ``RESULT <JSON>`` の 1 行。
_R3_MPL_CHILD = r'''
import json, os, sys, faulthandler
faulthandler.dump_traceback_later(int(os.environ["R3_CHILD_DUMP_S"]), exit=True)
sys.path.insert(0, os.environ["R3_ROOT"])
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import numpy as np
from PySide6 import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
import studio_program as sp
sp.GUI_BRIDGE = None
IMG = np.zeros((16, 16))
OUT = {}
def step(name):
    print("STEP " + name, flush=True)
def picture(r):
    o = r.output
    if type(o) is not np.ndarray:
        return [type(o).__name__]
    return ["ndarray", list(o.shape), float(o.min()), float(o.max()), float(o.std())]

step("plt.show() on the default backend")
r = sp.run_program("# python\nimport matplotlib.pyplot as plt\nb = plt.get_backend()\nplt.plot([1, 2, 3])\nplt.show()\n"
                   "after = 1\nplt.close('all')\n", IMG, time_limit_s=20)
OUT["show"] = {"errors": r.errors, "b": str(r.values.get("b")), "after": r.values.get("after"), "picture": picture(r),
               "note": sp.MPL_SHOWN_NOTE in r.notes, "source": r.output_source}
import matplotlib.pyplot as plt
OUT["show_put_back"] = plt.show.__module__ != sp.__name__

step("show(fig)")
r = sp.run_program("# python\nimport matplotlib.pyplot as plt\nf = plt.figure()\nplt.plot([3, 1, 2])\nshow(f)\n"
                   "plt.close('all')\n", IMG, time_limit_s=20)
OUT["show_fig"] = {"errors": r.errors, "picture": picture(r)}

step("QtAgg + a figure window + plt.close('all')")
r = sp.run_program("# python\nimport matplotlib\nmatplotlib.use('QtAgg')\nimport matplotlib.pyplot as plt\n"
                   "f = plt.figure()\nw = f.canvas.manager.window\nw.show()\nplt.close('all')\n", IMG, time_limit_s=20)
OUT["qtagg"] = {"errors": r.errors, "has_f": "f" in r.values}

step("matplotlib still works after the refusal")
r = sp.run_program("# python\nimport matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\n"
                   "plt.plot([1, 2])\nplt.show()\nplt.close('all')\n", IMG, time_limit_s=20)
OUT["after"] = {"errors": r.errors}
gui = app.thread()
OUT["widgets_off_gui"] = sorted(set(type(w).__name__ for w in QtWidgets.QApplication.allWidgets()
                                    if w.thread() is not gui))
print("RESULT " + json.dumps(OUT), flush=True)
'''


def test_r3_matplotlib_runs_on_agg_and_show_puts_the_figure_in_the_image_pane(tmp_path):
    """探針 q06b / q06c: 既定のまま ``plt.show()`` すると作業スレッドで Qt の窓が出来、閉じると Studio が固まった。

    **子プロセス + 時間の上限で回す**(2026-11-13 第 3 回レビュー S9)。見張りが無いと、この試験は落ちずに固まった
    (作業スレッドの Qt の窓は GIL を持ったまま止まるので、試験の中の時間の上限も pytest-timeout も働かない。
    レビューでは pytest を 600 秒で殺した)。子プロセスなら、固まり = 150 秒で失敗。"""
    pytest.importorskip("matplotlib")
    timeout = 150
    script = tmp_path / "r3_child.py"
    script.write_text(_R3_MPL_CHILD, encoding="utf-8")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONUTF8="1", PYTHONUNBUFFERED="1", R3_ROOT=root,
               R3_CHILD_DUMP_S=str(timeout - 30), FULLSEYE_STUDIO_SETTINGS=str(tmp_path / "child.ini"))
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
    got = json.loads(results[-1])
    show = got["show"]
    assert show["errors"] == [], show["errors"]
    assert show["b"].lower() == "agg" and show["after"] == 1
    kind, shape, lo, hi, std = show["picture"]
    assert kind == "ndarray" and len(shape) == 3 and shape[2] == 3 and shape[0] > 50
    assert 0.0 <= lo and hi <= 1.0 and std > 0.0
    assert show["note"] is True and show["source"].startswith("show line 5")
    assert got["show_put_back"] is True                                    # 差し替えた show は実行の後に外す
    assert got["show_fig"]["errors"] == [] and got["show_fig"]["picture"][0] == "ndarray" \
        and len(got["show_fig"]["picture"][1]) == 3                        # show(fig) でも同じ
    assert len(got["qtagg"]["errors"]) == 1 and got["qtagg"]["has_f"] is False
    assert "Studio does not let a running program import" in got["qtagg"]["errors"][0], got["qtagg"]["errors"]
    assert got["after"]["errors"] == [], got["after"]["errors"]           # 断った後も matplotlib は使い続けられる
    assert got["widgets_off_gui"] == []                                    # 作業スレッドに Qt の窓は 1 つも無い


# --------------------------------------------------------------------------- #
# R4 / R10: 従来の Python エディタ                                               #
# --------------------------------------------------------------------------- #
def _run_in_editor(win):
    pe = win._pyedit
    dlg = pe["dlg"]
    pe["run"]()
    end = time.monotonic() + 30
    while dlg._proc is not None and time.monotonic() < end:
        _pump(0.05)
    assert dlg._proc is None, "the script did not finish"
    return pe["output"].toPlainText()


def test_r4_the_python_editor_runs_the_text_that_was_confirmed_not_the_file_on_disk(tmp_path, monkeypatch):
    """探針 q01 f / f2: 開いた後でディスクを書き換えると、確認の窓に出した文面と違う物が走った。"""
    marker = tmp_path / "MARKER.txt"
    helper = tmp_path / "sibling_zz.py"
    helper.write_text("VALUE = 41\n", encoding="utf-8")
    script = tmp_path / "a.py"
    script.write_text("import sibling_zz\nprint('A: harmless', sibling_zz.VALUE + 1)\n", encoding="utf-8")
    asked = []
    monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *a: asked.append(a) or True)
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        win.drop_handler([str(script)])
        _pump(0.3)
        ed = win._pyedit["editor"]()
        assert ed.toPlainText().startswith("import sibling_zz")
        script.write_text("open(%r, 'w').write('pwned')\n" % str(marker), encoding="utf-8")   # 開いた後で書き換える
        out = _run_in_editor(win)
        assert len(asked) == 1 and "A: harmless 42" in out                # 画面の文面が走った(隣の .py も import できる)
        assert not marker.exists(), "the file on disk ran instead of the confirmed text"
        assert "changed on disk" in out                                    # ディスクが変わった事は言う
        script.write_text("open(%r, 'w').write('pwned again')\n" % str(marker), encoding="utf-8")
        out = _run_in_editor(win)                                          # 確認した後の書き換えも走らない
        assert len(asked) == 1 and not marker.exists() and "A: harmless 42" in out
        assert not [p for p in os.listdir(tmp_path) if p.startswith("scratch_")]
    finally:
        try:
            win._pyedit["dlg"].close()
        except Exception:                                                 # noqa: BLE001
            pass
        _close(win)


def test_r10_a_parameter_file_sent_to_the_editor_is_confirmed_before_it_runs(tmp_path, monkeypatch):
    """探針 q01 g: プロジェクトのパラメータのファイル → Open in editor → F5 が確認なしに走った。"""
    from PySide6 import QtWidgets
    marker = tmp_path / "MARKER.txt"
    params = tmp_path / "params_g.yaml"
    params.write_text("open(%r, 'w').write('pwned')\n" % str(marker), encoding="utf-8")
    asked = []
    answer = {"v": False}
    monkeypatch.setattr(pm_mod, "TRUST_HOOK", lambda *a: asked.append(a) or answer["v"])
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        sub = win._open_params_file(str(params))
        _pump(0.2)
        buttons = [b for b in sub.findChildren(QtWidgets.QPushButton) if b.text() == "Open in editor"]
        assert len(buttons) == 1
        buttons[0].click()
        _pump(0.3)
        ed = win._pyedit["editor"]()
        assert ed is not None and ed._from_file is True and ed._origin == os.path.abspath(str(params))
        _run_in_editor(win)
        assert len(asked) == 1 and not marker.exists()                    # 確認を断った: 走っていない
        assert os.path.basename(str(params)) in asked[0][2]
        answer["v"] = True
        _run_in_editor(win)
        assert len(asked) == 2 and marker.exists()
    finally:
        try:
            win._pyedit["dlg"].close()
        except Exception:                                                 # noqa: BLE001
            pass
        _close(win)


# --------------------------------------------------------------------------- #
# R5: 変数の欄の __repr__ 用のスレッド                                           #
# --------------------------------------------------------------------------- #
class SleepsInRepr:
    def __init__(self, seconds, mark):
        self.seconds, self.mark = seconds, mark

    def __repr__(self):
        os.environ["ZZ_STUDIO_REPR"] = self.mark
        try:
            time.sleep(self.seconds)
        except BaseException:                         # noqa: BLE001 -- 止めの例外を握りつぶす(探針 q07 と同じ)
            pass
        return "SleepsInRepr(%s)" % self.mark


class QuickRepr:
    def __repr__(self):
        CALLED.append("QuickRepr.__repr__")
        os.environ["ZZ_STUDIO_QUICK"] = "1"
        return "QuickRepr()"


def test_r5_helper_threads_do_not_pile_up_and_their_changes_are_put_back(tmp_path):
    """探針 q07: 止まらない ``__repr__`` のスレッドが溜まり、環境変数の書き換えが Studio に残った。"""
    assert _wait(lambda: not V.stray_threads())
    os.environ.pop("ZZ_STUDIO_REPR", None)
    os.environ.pop("ZZ_STUDIO_QUICK", None)
    try:
        CALLED.clear()
        s = V.summarize(QuickRepr())
        assert s.text == "QuickRepr()" and CALLED == ["QuickRepr.__repr__"]
        assert "ZZ_STUDIO_QUICK" not in os.environ                         # __repr__ が変えた環境は戻す
        n0 = threading.active_count()
        s1 = V.summarize(SleepsInRepr(1.5, "a"))
        assert s1.problem == "repr_timeout" and len(V.stray_threads()) == 1
        CALLED.clear()
        s2 = V.summarize(QuickRepr())                                      # 残っている間は新しく起こさない
        s3 = V.summarize(SleepsInRepr(1.5, "b"))
        assert CALLED == [] and "not shown" in s2.text and "not shown" in s3.text
        assert len(V.stray_threads()) == 1 and threading.active_count() <= n0 + 2      # 残り 1 本 + 後始末 1 本
        ev = V.WatchEvaluator({"x": 3}, timeout_s=0.1)
        j = ev.start("x * 2")
        assert j.result is not None and not j.result.ok and "not shown" in j.result.error
        # 実行系も、残っている間は始めない(保留の止めの例外で Debug の実行が時間切れに見える = 探針 q07b)
        for cfg in ("debug", "release"):
            r = sp.run_program("# python\nk = 1\n", IMG, time_limit_s=3.0, config=cfg)
            assert not r.ran and r.errors == [sp.STRAY_BLOCKS_RUN % 1] and "k" not in r.values, (cfg, r.errors)
        assert spi.localize(sp.STRAY_BLOCKS_RUN % 1, pi.make_tr("ja")) != sp.STRAY_BLOCKS_RUN % 1
        assert _wait(lambda: not V.stray_threads(), 10)
        assert _wait(lambda: "ZZ_STUDIO_REPR" not in os.environ, 5)        # 残ったスレッドが終わった所で戻す
        assert V.summarize(QuickRepr()).text == "QuickRepr()"              # 終われば元どおり
    finally:
        _wait(lambda: not V.stray_threads(), 10)
        os.environ.pop("ZZ_STUDIO_REPR", None)
        os.environ.pop("ZZ_STUDIO_QUICK", None)


def test_r5_a_run_is_not_started_while_a_value_helper_thread_is_left(tmp_path, monkeypatch):
    """探針 q07b / q07e: 残ったスレッドの保留の例外で、次の Debug の実行が何もしなくても時間切れになった。"""
    assert _wait(lambda: not V.stray_threads())
    win, _m = _launch(tmp_path, monkeypatch, time_limit=5)
    try:
        pm = win._pymode
        _set_text(win, "# python\nimport time\nclass Stuck:\n    def __repr__(self):\n        try:\n"
                       "            time.sleep(2.5)\n        except BaseException:\n            pass\n"
                       "        return 'Stuck()'\nx = Stuck()\nshow(img)\n")
        res = _f5(win)
        assert res.ok, res.errors
        assert _wait(lambda: len(V.stray_threads()) == 1, 5), "the Variables panel did not leave the helper thread"
        runs0 = pm.state.get("pymode_runs", 0)
        _set_text(win, "# python\ny = 1\nshow(img)\n")
        from PySide6 import QtCore
        from PySide6.QtTest import QTest
        QTest.keyClick(win._program["edit"], QtCore.Qt.Key_F5)
        _pump(0.2)
        assert not pm.running and pm.state.get("pymode_runs", 0) == runs0  # 始めずに、そう言う
        assert "still running its own code" in pm.output.toPlainText().splitlines()[-1]
        assert _wait(lambda: not V.stray_threads(), 10)
        res = _f5(win)
        assert res.ok and res.stopped is None and res.values["y"] == 1     # 時間切れの誤判定をしない
    finally:
        _wait(lambda: not V.stray_threads(), 10)
        _close(win)


# --------------------------------------------------------------------------- #
# R7 の付記: 残した実行は、戻し終えるまで「残っている」                            #
# --------------------------------------------------------------------------- #
def test_r7_the_next_run_waits_until_the_late_restore_of_an_abandoned_run_is_done(tmp_path, monkeypatch):
    """残した実行のスレッドが終わった瞬間に次の実行を通すと、その実行の途中で状態と import の見張りが戻される
    (e2e の 7 段目が 10 回中 1 回落ちた)。遅れて戻す処理が終わるまで、次の実行を断る。"""
    assert _wait(lambda: not sp.abandoned_runs())
    real = sp._GlobalState.restore
    slow = {"calls": 0}

    def slow_restore(self):
        slow["calls"] += 1
        if threading.current_thread().name == "studio-program-late-restore":
            time.sleep(1.0)                           # 遅れて戻す処理を、わざと遅くする
        return real(self)
    monkeypatch.setattr(sp._GlobalState, "restore", slow_restore)
    imp0 = builtins.__import__
    prog = "# python\nimport time\ntry:\n    time.sleep(2.5)\nexcept BaseException:\n    pass\n"
    try:
        r = sp.run_program(prog, IMG, time_limit_s=0.2, config="release")
        assert r.stopped == "unstoppable"
        worker = [t for t in threading.enumerate() if t.name == "studio-program"]
        assert len(worker) == 1
        worker[0].join(10)
        assert not worker[0].is_alive()               # 残した実行そのものは終わった
        assert len(sp.abandoned_runs()) == 1          # …が、戻し終えるまでは「残っている」
        nxt = sp.run_program("# python\nx = 1\n", IMG)
        assert not nxt.ran and "still running in the background" in nxt.errors[0]
        assert _wait(lambda: not sp.abandoned_runs(), 10)
        ok = sp.run_program("# python\nx = 1\n", IMG)
        assert ok.ok and ok.notes == [], ok.notes
        assert builtins.__import__ is imp0            # import の見張りが残っていない
    finally:
        _wait(lambda: not sp.abandoned_runs(), 10)


# --------------------------------------------------------------------------- #
# R6: プログラムが起こして残したスレッド                                          #
# --------------------------------------------------------------------------- #
def test_r6_threads_left_by_the_program_are_reported(tmp_path, monkeypatch):
    """探針 q04 B: プログラムの ``threading.Thread(...).start()`` が残っていても、何も言わずに次が走っていた。"""
    assert _wait(lambda: not sp.program_threads())
    prog = ("# python\nimport threading, time\n"
            "t = threading.Thread(target=lambda: time.sleep(1.5), name='zz-user-thread', daemon=True)\nt.start()\n")
    r = sp.run_program(prog, IMG)
    assert r.ok
    notes = [n for n in r.notes if "thread(s) that are still running" in n]
    assert len(notes) == 1 and "started 1 thread" in notes[0] and "zz-user-thread" in notes[0], r.notes
    assert sp.program_threads() == ["zz-user-thread"]
    assert spi.localize(notes[0], pi.make_tr("ja")) != notes[0]
    assert _wait(lambda: not sp.program_threads(), 10)
    clean = sp.run_program("# python\nimport threading\nt = threading.Thread(target=lambda: None)\nt.start()\nt.join()\n",
                           IMG)
    assert clean.ok and not [n for n in clean.notes if "thread(s)" in n]   # 終わったスレッドは数えない
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        _set_text(win, prog + "show(img)\n")
        res = _f5(win)
        assert res.ok and "zz-user-thread" in pm.output.toPlainText()
        _set_text(win, "# python\nshow(img)\n")
        res = _f5(win)                                                     # 次の実行の前に知らせてから走る
        assert res.ok
        assert "Threads started by an earlier run are still running (zz-user-thread)" in pm.output.toPlainText()
    finally:
        _wait(lambda: not sp.program_threads(), 10)
        _close(win)

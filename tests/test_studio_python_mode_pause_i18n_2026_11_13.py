# -*- coding: utf-8 -*-
"""Studio の Python のモード: 止まった所から続ける・局所変数・実行時と検査の文の言語・例と案内(2026-11-13)。

* 続行と 1 行実行は、止まって待っている実行を起こす(上から走り直さない = print が 2 度出ない)。
* 止まった所が関数の中なら、その枠の局所変数が結果と変数の欄に出る。
* 実行系・検査の英語の文は、画面では UI の言語(型の表は源のファイルから数える)。
* 例の文面のコメントと「最初の 3 手」は UI の言語とモードに従う。
* 止めるボタンと時間の上限: 先に来た方が理由になる(e2e の 7 段目が 10 回中 5 回落ちた原因の固定)。
"""
import ast
import os
import re
import threading
import time

import numpy as np
import pytest

import studio
import studio_program as sp
import studio_program_i18n as spi
import studio_pyedit_i18n as pi
import studio_pymode as pm_mod

IMG = np.zeros((16, 16))
ROOT = os.path.dirname(os.path.abspath(studio.__file__))


# --------------------------------------------------------------------------- #
# 実行系: 止まった所から続ける(Qt なし)                                          #
# --------------------------------------------------------------------------- #
def _hook(commands, seen):
    """pause_hook: 止まるたびに結果を *seen* に足し、*commands* の次の指示を返す(尽きたら stop)。"""
    it = iter(commands)

    def hook(snap):
        seen.append(snap)
        return next(it, "stop")
    return hook


def test_continue_goes_on_from_where_it_stopped_and_does_not_run_twice():
    text = "print('a')\nx = 1\nprint('b')\ny = x + 1\nprint('c')\n"
    seen = []
    r = sp.run_program(text, IMG, breakpoints=[4], pause_hook=_hook(["continue"], seen))
    assert len(seen) == 1
    snap = seen[0]
    assert snap.stopped == "breakpoint" and snap.stopped_line == 4
    assert snap.stdout == "a\nb\n" and snap.values["x"] == 1 and "y" not in snap.values
    assert r.ok and r.stopped is None
    assert r.stdout == "a\nb\nc\n"                       # 上から走り直していない(a と b は 1 回ずつ)
    assert r.values["y"] == 2


def test_step_after_a_breakpoint_runs_exactly_one_line_each_time():
    text = "a = 1\nb = 2\nc = 3\nd = 4\n"
    seen = []
    r = sp.run_program(text, IMG, breakpoints=[2], pause_hook=_hook(["step", "step", "continue"], seen))
    assert [(s.stopped, s.stopped_line) for s in seen] == [("breakpoint", 2), ("step", 3), ("step", 4)]
    assert [sorted(k for k in s.values if k in "abcd") for s in seen] == [["a"], ["a", "b"], ["a", "b", "c"]]
    assert r.ok and r.values["d"] == 4


def test_a_loop_breakpoint_stops_on_every_pass_and_new_breakpoints_can_be_passed():
    text = "t = 0\nfor i in range(3):\n    t = t + i\nz = 9\n"
    seen = []
    r = sp.run_program(text, IMG, breakpoints=[3], pause_hook=_hook(
        ["continue", {"command": "continue", "breakpoints": [4], "conditions": {}}, "continue"], seen))
    assert [(s.stopped_line, s.values.get("i")) for s in seen] == [(3, 0), (3, 1), (4, 2)]
    assert r.ok and r.values["t"] == 3


def test_stop_while_waiting_ends_the_run_as_stop_requested():
    seen = []
    r = sp.run_program("a = 1\nb = 2\n", IMG, breakpoints=[2], pause_hook=_hook(["stop"], seen))
    assert len(seen) == 1 and r.stopped == "stop_requested" and r.stopped_line == 2
    assert "b" not in r.values


def test_a_hook_that_ignores_the_stop_request_is_still_stopped():
    """待っている間に stop_event が立てば、フックが見ていなくても見張りが止める(呼び出し側は必ず戻る)。"""
    stop = threading.Event()

    def deaf(_snap):
        stop.set()
        end = time.perf_counter() + 20
        while time.perf_counter() < end:                  # 止める要求を見ない待ち(Python のループ)
            time.sleep(0.01)
        return "continue"
    t0 = time.perf_counter()
    r = sp.run_program("a = 1\nb = 2\n", IMG, breakpoints=[2], pause_hook=deaf, stop_event=stop)
    assert time.perf_counter() - t0 < 5.0
    assert r.stopped == "stop_requested"


def test_the_time_spent_waiting_does_not_count_toward_the_time_limit():
    def slow(_snap):
        time.sleep(1.0)                                   # 上限(0.5 s)より長く止まっている
        return "continue"
    r = sp.run_program("a = 1\nb = 2\nc = 3\n", IMG, breakpoints=[2], pause_hook=slow, time_limit_s=0.5)
    assert r.ok, r.errors
    assert r.elapsed_s < 0.5


def test_locals_of_the_stopped_frame_and_the_stack():
    text = ("g = 10\n"
            "def f(k):\n"
            "    inner = k * 2\n"
            "    return inner + g\n"
            "out = f(4)\n")
    seen = []
    r = sp.run_program(text, IMG, breakpoints=[4], pause_hook=_hook(["continue"], seen))
    assert len(seen) == 1
    assert seen[0].locals == {"k": 4, "inner": 8}
    assert seen[0].stack == [("f", 4), ("<module>", 5)]
    assert seen[0].values["g"] == 10 and "inner" not in seen[0].values
    assert r.ok and r.values["out"] == 18 and r.locals == {}
    # 待たない形(pause_hook なし = 今までどおり止まった所で終える)でも、局所変数は結果に入る
    r2 = sp.run_program(text, IMG, breakpoints=[4])
    assert r2.stopped == "breakpoint" and r2.locals == {"k": 4, "inner": 8} and r2.stack[0] == ("f", 4)
    # モジュールの階層で止まったら空(名前空間そのものなので重ねない)
    r3 = sp.run_program(text, IMG, breakpoints=[5])
    assert r3.stopped == "breakpoint" and r3.locals == {} and r3.stack == [("<module>", 5)]


def test_release_never_waits():
    seen = []
    r = sp.run_program("a = 1\nb = 2\n", IMG, breakpoints=[2], config="release", pause_hook=_hook(["stop"], seen))
    assert r.ok and not seen


# --------------------------------------------------------------------------- #
# 止める要求と時間の上限: 先に来た方が理由(e2e 7 段目の原因)                       #
# --------------------------------------------------------------------------- #
def test_whichever_comes_first_is_the_reason_stop_request_or_time_limit():
    """e2e の 7 段目(止めるボタン)は、時間の上限 1.0 s のまま無限ループを起こし、スクリーンショットを撮ってから
    止めるボタンを押していた。押すまでに 1.01〜1.07 s かかった回(10 回中 5 回)は、**上限が先に来て**
    ``time_limit`` で止まっていた(製品は正しい。試験が 2 つの原因を競わせていた)。ここで順序を固定する。"""
    loop = "while True:\n    pass\n"
    stop = threading.Event()
    threading.Timer(0.2, stop.set).start()
    r = sp.run_program(loop, IMG, stop_event=stop, time_limit_s=30.0)       # 要求が先
    assert r.stopped == "stop_requested" and r.elapsed_s < 5.0
    stop2 = threading.Event()
    threading.Timer(1.2, stop2.set).start()
    r2 = sp.run_program(loop, IMG, stop_event=stop2, time_limit_s=0.3)      # 上限が先(要求は後から来る)
    assert r2.stopped == "time_limit" and r2.elapsed_s < 1.0
    stop2.set()


# --------------------------------------------------------------------------- #
# 言語: 型の表は源のファイルから数える                                           #
# --------------------------------------------------------------------------- #
def _program_source_strings():
    """studio_program.py の文字列の定数(``%`` で埋める前の書式文字列を含む)。"""
    src = open(os.path.join(ROOT, "studio_program.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    return tree, [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def test_every_template_is_a_format_string_of_studio_program():
    """型は源の書式文字列と同じ文字列(源の文を変えたら、ここが落ちて表を直す事になる)。"""
    _tree, strings = _program_source_strings()
    assert len(strings) > 500
    blob = "\x00".join(strings)
    pyflakes = {"Imported but never used: %s", "Assigned but never used (inside a function): %s",
                "Defined again before the first one was used: %s", "A loop variable hides an import: %s"}
    missing = []
    for t in spi.TEMPLATES:
        if t == spi.LINE_LABEL:
            ok = "line %d: " in blob
        elif t in spi.LINE_BODY_TEMPLATES:
            ok = ("line %d: " + t) in blob or ("line 1: " + t) in blob
        elif t in pyflakes:
            ok = t[:-len(": %s")] in strings                # 源では "%s: %s" % (文, pyflakes の文) で繋ぐ
        elif t in ("There is no op named '%s'", "There is no op named '%s' — did you mean '%s'?"):
            ok = "There is no op named '%s'%s" in strings and " — did you mean '%s'?" in strings
        elif t == "%s — install it into Studio's Python: \"%s\" -m pip install %s":
            ok = " — install it into Studio's Python: \"%s\" -m pip install %s" in strings
        elif t == "restored after the run: %s":
            ok = "restored after the run: " in strings
        elif t in ("stopped: time limit", "stopped: on request"):
            ok = "stopped: %s" in strings and t.split(": ")[1] in strings
        else:
            ok = t in blob
        if not ok:
            missing.append(t)
    assert not missing, missing
    assert len(spi.TEMPLATES) >= 80


def _check_messages_in_source():
    """``_P(行, 桁, 行, 桁, 重さ, 符号, 文, 直し方)`` と ``Advice(行, 種類, 文)`` の文と直し方(書式文字列)。"""
    tree, _s = _program_source_strings()
    out = []

    def fmt(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            return fmt(node.left)
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else ""
        if name == "_P":
            out += [fmt(a) for a in node.args[6:8]]
        elif name == "Advice":
            out += [fmt(a) for a in node.args[2:3]]
    return [m for m in out if m]


def test_every_check_and_advice_message_in_the_source_has_a_template():
    """源の側から数える: 検査と助言の文(_P と Advice の書式文字列)は、全部が型の表に在る。"""
    msgs = _check_messages_in_source()
    assert len(msgs) >= 45, len(msgs)
    special = {"There is no op named '%s'%s"}             # 2 つの型(もしかして の有無)に分けてある
    ja = pi.make_tr("ja")

    def covered(m):
        if m in spi.TEMPLATES or m in special:
            return True
        # 値を埋めずに書いた文(「'!' is written 'not' in Python」)は、値つきの型に当たって訳されればよい
        return not spi.placeholders(m) and spi.localize(m, ja) != m
    missing = sorted(set(m for m in msgs if not covered(m)))
    assert not missing, missing


def test_every_template_is_translated_in_five_languages_with_the_same_placeholders():
    tab = pi.load_table()
    assert len(spi.TEMPLATES) == len(set(spi.TEMPLATES))
    bad = []
    for t in spi.TEMPLATES:
        row = tab.get(t) or {}
        for lang in pi.LANGS[1:]:
            v = row.get(lang, "")
            if not v.strip() or spi.placeholders(v) != spi.placeholders(t):
                bad.append((t, lang))
    assert not bad, bad


@pytest.mark.parametrize("lang", ["ja", "zh", "tw", "ko", "de"])
def test_real_messages_are_localized_and_values_survive(lang):
    tr = pi.make_tr(lang)
    r = sp.run_program("x = 1\nwhile True:\n    pass\n", IMG, time_limit_s=0.2)
    assert r.stopped == "time_limit"
    shown = spi.localize(r.errors[0], tr)
    assert shown != r.errors[0] and "0.2" in shown and spi.line_number_of(shown) == r.error_line
    assert "stopped" not in shown and "line " not in shown
    r = sp.run_program("a = 1\nb = a / 0\n", IMG)
    shown = spi.localize(r.errors[0], tr)                  # Python 自身の例外の文はそのまま、行の言い方だけ変わる
    assert shown.endswith("ZeroDivisionError: division by zero") and not shown.startswith("line ")
    assert spi.line_number_of(shown) == 2
    r = sp.run_program("a = 1\n", IMG, breakpoints=[1], config="release")
    assert len(r.notes) >= 1
    notes = [spi.localize(n, tr) for n in r.notes]
    assert all(n != e for n, e in zip(notes, r.notes) if e.startswith("Release")), notes
    probs = sp.check_program("# python\nx = 0\nif x = 1:\n    pass\ny = gausian(img, 0.3)\nz = gaussian（img, 0.3）\n",
                             syntax=sp.SYNTAX_PYTHON)
    probs += sp.check_program("# python\ny = gausian(img, 0.3)\nimport os\nw = undefined_thing + 1\n",
                              syntax=sp.SYNTAX_PYTHON)
    assert len(probs) >= 4, probs
    for p in probs:
        assert spi.localize(p.message, tr) != p.message, (lang, p.code, p.message)
        if p.hint:
            assert spi.localize(p.hint, tr) != p.hint, (lang, p.code, p.hint)
    rows, per_line = pm_mod.problem_rows(probs, tr)
    assert rows and all(pm_mod.error_line_of(msg) == ln for ln, msg in rows), rows
    assert all("[%s]" % p.code in msg for p, (_ln, msg) in zip(probs, rows))    # 符号は訳さない


def test_unknown_language_and_unknown_text_stay_english():
    ident = lambda s: s                                                       # noqa: E731
    assert spi.localize("line 3: stopped on request", ident) == "line 3: stopped on request"
    assert spi.localize("something nobody wrote a template for", pi.make_tr("ja")) == \
        "something nobody wrote a template for"
    assert spi.localize("", pi.make_tr("ja")) == "" and spi.localize(None, pi.make_tr("ja")) is None
    rows, _p = pm_mod.problem_rows(sp.check_program("# python\nif x = 1:\n    pass\n", syntax=sp.SYNTAX_PYTHON))
    assert rows and rows[0][1].startswith("✕ line 2: '=' assigns")           # tr なし = 今までどおり英語


def test_line_number_is_read_in_every_language():
    forms = [spi.line_label(12, pi.make_tr(lang)) for lang in pi.LANGS]
    assert len(set(forms)) >= 4, forms
    for f in forms:
        assert spi.line_number_of("✕ %s: x" % f) == 12, f
    assert spi.line_number_of("no number here") is None and spi.line_number_of("outline 3") is None


# --------------------------------------------------------------------------- #
# 例の文面: 言語ごとのコメント、コードは同じ                                      #
# --------------------------------------------------------------------------- #
def _code_only(text):
    return [re.sub(r'"[^"]*"', '""', ln.split("#", 1)[0]).rstrip() for ln in text.split("\n")]


def test_starter_program_per_language_has_the_same_code_and_no_problems():
    assert sorted(sp.STARTER_PROGRAMS) == ["de", "en", "ja", "ko", "tw", "zh"]
    assert sp.starter_program("hi") == sp.STARTER_PROGRAM == sp.STARTER_PROGRAMS["en"]   # 表に無い言語は英語
    base = _code_only(sp.STARTER_PROGRAM)
    for lang, text in sp.STARTER_PROGRAMS.items():
        assert _code_only(text) == base, lang
        assert text.startswith("# python\n") and text.endswith("show(mask)\n")
        probs = [p for p in sp.check_program(text, syntax=sp.SYNTAX_PYTHON) if p.severity == "error"]
        assert not probs, (lang, probs)
        if lang != "en":
            assert text != sp.STARTER_PROGRAM
    assert len(set(sp.STARTER_PROGRAMS.values())) == 6
    assert re.search(r"[぀-ヿ]", sp.STARTER_PROGRAMS["ja"])              # 日本語の見本は日本語のコメント
    r = sp.run_program(sp.STARTER_PROGRAMS["ja"], IMG)
    assert r.ok and [c.op for c in r.calls][:3] == ["gaussian", "otsu", "blob_count"]


# --------------------------------------------------------------------------- #
# 画面(offscreen)                                                             #
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


def _launch(tmp_path, monkeypatch, start_mode="auto"):
    _app()
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "s.ini"))
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


def test_continue_in_the_window_resumes_the_waiting_run(tmp_path, monkeypatch):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        _set_text(win, "# python\nprint('tick')\nk = 1\nk = k + 1\nprint('tock')\nshow(img)\n")
        pm.toggle_breakpoint(4)
        runs0 = pm.state.get("pymode_runs", 0)
        res = _f5(win)
        assert res.stopped == "breakpoint" and res.stopped_line == 4
        sess = pm.session
        assert sess is not None and sess.live and not pm.running
        assert pm.btn_run.text() == "Continue" and pm.btn_stop.isEnabled()
        thread = sess.job.thread
        assert thread.is_alive()                                         # 実行は終わっていない: その場で待っている
        QTest.keyClick(ed, QtCore.Qt.Key_F6)                             # 1 行
        assert pm.wait_idle(10)
        assert pm.last.stopped == "step" and pm.last.stopped_line == 5 and pm.last.values["k"] == 2
        assert pm.session.job.thread is thread                           # 同じ実行が続いている
        res = _f5(win)                                                   # 続行 → 最後まで
        assert res.ok and pm.session is None and not thread.is_alive()
        assert pm.state.get("pymode_runs", 0) == runs0 + 1               # 起こした実行は 1 回だけ
        out = pm.output.toPlainText()
        assert out.count("tick") == 1 and out.count("tock") == 1, out    # 上から走り直していない
        assert res.stdout == "tick\ntock\n"
    finally:
        _close(win)


def test_stop_while_waiting_ends_the_thread_and_editing_restarts_from_the_top(tmp_path, monkeypatch):
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        _set_text(win, "# python\nprint('one')\nk = 1\nshow(img)\n")
        pm.toggle_breakpoint(3)
        _f5(win)
        thread = pm.session.job.thread
        QTest.keyClick(ed, QtCore.Qt.Key_F2, QtCore.Qt.ControlModifier)  # 止める = Debug の区切りを終える
        assert pm.session is None and not thread.is_alive() and not pm.btn_stop.isEnabled()
        assert pm.btn_run.text() == "Run"
        _f5(win)                                                         # もう一度止まる
        thread = pm.session.job.thread
        _set_text(win, "# python\nprint('one')\nk = 2\nshow(img)\n")      # 止まっている間に文面を直す
        pm.edit.breakpoints.clear()
        res = _f5(win)
        assert res.ok and res.values["k"] == 2 and not thread.is_alive()
        assert "running again from the top" in pm.output.toPlainText()
        # 閉じる時に、待っている実行を残さない
        _set_text(win, "# python\nk = 5\nshow(img)\n")
        pm.toggle_breakpoint(2)
        _f5(win)
        thread = pm.session.job.thread
        assert thread.is_alive()
    finally:
        _close(win)
    assert not thread.is_alive()


def test_locals_of_a_function_are_listed_when_stopped_inside_it(tmp_path, monkeypatch):
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        _set_text(win, "# python\ng = 10\ndef f(k):\n    inner = k * 2\n    return inner + g\nout = f(4)\nshow(img)\n")
        pm.toggle_breakpoint(5)
        res = _f5(win)
        assert res.stopped == "breakpoint" and res.stopped_line == 5
        ns = pm.var_source.ns
        assert ns["inner"] == 8 and ns["k"] == 4 and ns["g"] == 10       # 局所変数とモジュールの変数の両方
        assert "f()" in win._program["status"]().text()
        res = _f5(win)
        assert res.ok and "inner" not in pm.var_source.ns and pm.var_source.ns["out"] == 18
    finally:
        _close(win)


def test_japanese_ui_shows_run_time_and_check_texts_in_japanese(tmp_path, monkeypatch):
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        win._apply_language("ja")
        _pump(0.2)
        _set_text(win, "# python\nx = 0\ny = 1 / x\nshow(img)\n")
        res = _f5(win)
        assert res.errors == ["line 3: ZeroDivisionError: division by zero"]       # 結果は英語のまま(API)
        out = pm.output.toPlainText()
        assert "3 行目: ZeroDivisionError" in out and "line 3" not in out
        assert pm_mod.error_line_of("✕ 3 行目: ZeroDivisionError") == 3
        _pump(0.35)
        rows = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
        assert rows and any("3 行目" in r for r in rows), rows
        assert not any("line 3" in r for r in rows), rows
        _set_text(win, "# python\ny = gausian(img, 0.3)\nif y = 1:\n    pass\n")
        rows = [win._problems_list.item(i).text() for i in range(win._problems_list.count())]
        assert rows and not any(re.search(r"\bline \d", r) for r in rows), rows
        assert any("代入" in r for r in rows), rows
        pm._set("time_limit_s", 0.3)
        _set_text(win, "# python\nwhile True:\n    pass\n")
        res = _f5(win)
        assert res.stopped == "time_limit"
        tail = pm.output.toPlainText().splitlines()[-1]
        assert "時間の上限" in tail and "time limit" not in tail, tail
        assert "時間の上限" in win._program["status"]().text()
    finally:
        _close(win)


def test_example_and_new_program_follow_the_ui_language(tmp_path, monkeypatch):
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        ed = win._program["edit"]
        assert ed.toPlainText() == sp.STARTER_PROGRAM
        pm.toggle_breakpoint(8)
        win._apply_language("ja")
        _pump(0.2)
        assert ed.toPlainText() == sp.STARTER_PROGRAMS["ja"] and not pm.unsaved()
        assert ed.breakpoints == {8}                                     # 行は同じなので印は残る
        win._actions["pymode_new"].trigger()
        assert "新しいプログラム" in ed.toPlainText() and not pm.unsaved()
        win._apply_language("de")
        _pump(0.2)
        assert "Neues Programm" in ed.toPlainText() and not pm.unsaved()
        win._actions["pymode_example"].trigger()
        assert ed.toPlainText() == sp.STARTER_PROGRAMS["de"]
        _set_text(win, ed.toPlainText() + "k = 1\n")                      # 手を付けた文面は入れ替えない
        mine = ed.toPlainText()
        win._apply_language("ja")
        _pump(0.2)
        assert ed.toPlainText() == mine and pm.unsaved()
    finally:
        _close(win)


def test_first_steps_guide_follows_the_program_mode(tmp_path, monkeypatch):
    win, _m = _launch(tmp_path, monkeypatch)
    try:
        pm = win._pymode
        labels = win._first_steps_labels
        assert len(labels) == 3
        assert pm.mode == "python" and [l.text() for l in labels] == list(studio.FIRST_STEPS_PYTHON)
        assert "F5" in labels[0].text() and "Operators" not in " ".join(l.text() for l in labels)
        win._apply_language("ja")
        _pump(0.1)
        assert all(re.search(r"[぀-ヿ一-鿿]", l.text()) for l in labels), [l.text() for l in labels]
        assert labels[0].toolTip() == labels[0].text()
        win._apply_language("en")
        pm.set_mode("pipeline")
        assert [l.text() for l in labels] == list(studio.FIRST_STEPS_PIPELINE)
        pm.set_mode("python")
        assert [l.text() for l in labels] == list(studio.FIRST_STEPS_PYTHON)
    finally:
        _close(win)
    win2, _m2 = _launch(tmp_path, monkeypatch, start_mode="pipeline")    # 今までの build_window() の既定
    try:
        assert [l.text() for l in win2._first_steps_labels] == list(studio.FIRST_STEPS_PIPELINE)
    finally:
        _close(win2)

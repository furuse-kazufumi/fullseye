# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Program 欄の書いている最中の指摘(check_program)・補完とホバー・Debug / Release の構成。

指摘は「間違った例 → 期待する code と行・列」と、それ以上の数の「正しい例 → 指摘ゼロ」(誤検出の試験)。
fix を当てたら compile が通ることも確かめる。任意の依存(parso / pyflakes / jedi)は、ある時と、
import を塞いで土台に落ちる時の両方を試す。"""
from __future__ import annotations

import os
import sys
import threading
import time

import numpy as np
import pytest

import api
import studio_program as sp

NAMES = sorted(sp.op_table())


def _gray(seed=0, size=48):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size]
    return np.clip(0.5 + 0.3 * np.sin(x / 5.0) * np.cos(y / 7.0) + 0.05 * rng.standard_normal((size, size)), 0, 1)


def _codes(text, **kw):
    return [(p.line, p.col, p.code) for p in sp.check_program(text, syntax="python", **kw)]


# --------------------------------------------------------------------------- #
# 間違った例 → code・行・列                                                     #
# --------------------------------------------------------------------------- #
WRONG = [
    ("if x = 1:\n    pass\n", (1, 5, "assign_in_condition")),
    ("x = (1,\ny = 2\n", (1, 4, "unclosed_bracket")),
    ("if x > 0\n    pass\n", (1, 8, "missing_colon")),
    ("for i in range(3)\n    pass\n", (1, 17, "missing_colon")),
    ("x = [1 2]\n", (1, 5, "missing_comma")),
    ("def f():\nreturn 1\n", (2, 0, "indentation")),
    ("if x:\n\tpass\n        pass\n", (3, 0, "tabs_spaces")),
    ("if a && b:\n    pass\n", (1, 5, "c_operator")),
    ("if a || b:\n    pass\n", (1, 5, "c_operator")),
    ("if y:\n    pass\nelse if x:\n    pass\n", (3, 0, "else_if")),
    ("s = 'abc\n", (1, 4, "unclosed_string")),
    ("x = 1 {\n", (1, 6, "brace_block")),
    ("img = gaussian（img, 0.4）\n", (1, 14, "fullwidth_char")),
    ("x = 1，2\n", (1, 5, "fullwidth_char")),
    ("x　= 1\n", (1, 1, "fullwidth_char")),
    ("img = gausian(img, 0.4)\n", (1, 6, "undefined_name")),
    ("x = true\n", (1, 4, "js_literal")),
    ("y = null\n", (1, 4, "js_literal")),
    ("img = gaussian(img, 9)\n", (1, 20, "knob_out_of_range")),
    ("img = gaussian(img, a=-2)\n", (1, 22, "knob_out_of_range")),
    ("img = gaussian(img, c=0.3)\n", (1, 22, "unknown_keyword")),
    ("d = sub_image(0.3)\n", (1, 4, "missing_inputs")),
    ("img = gaussian(img, 0.1, 0.2, 0.3)\n", (1, 6, "too_many_args")),
    ("blob_count(otsu(img))\n", (1, 0, "result_discarded")),
    ("img = gaussian(img, 0.4)\nendfor\n", (2, 0, "mixed_syntax")),
    ("* a comment\nimg = gaussian(img)\n", (1, 0, "mixed_syntax")),
    ("img = op('gausian', img)\n", (1, 9, "unknown_op")),
    ("if 1 > 0:\n    y = 1\nprint(y)\n", (3, 6, "maybe_undefined")),
    ("x = 1;\n", (1, 5, "semicolon")),
]


@pytest.mark.parametrize("text,want", WRONG)
def test_wrong_examples_are_pointed_at(text, want):
    got = _codes(text)
    assert got and got[0] == want, (text, got)


def test_fixes_compile():
    n = 0
    for text, _want in WRONG:
        probs = sp.check_program(text, syntax="python")
        fixes = [p.fix for p in probs if p.fix]
        if not fixes:
            continue
        fixed = text
        for f in sorted(fixes, key=lambda f: (f["line"], f["col"]), reverse=True):   # 後ろから当てる
            fixed = sp.apply_fix(fixed, f)
        compile(fixed, "<fixed>", "exec")
        assert not [p for p in sp.check_program(fixed, syntax="python")
                    if p.severity == "error" and p.code == probs[0].code], (text, fixed)
        n += 1
    assert n >= 10, n


def test_syntax_errors_do_not_cascade():
    probs = sp.check_program("if x = 1:\n    pass\n    y = 2\n", syntax="python")
    assert [p.code for p in probs] == ["assign_in_condition"]
    probs = sp.check_program("img = gaussian（img, 0.4）\n", syntax="python")
    assert {p.code for p in probs} == {"fullwidth_char"} and len(probs) == 2      # 括弧 2 つ。構文の誤りは重ねない


def test_problem_shape_is_fixed():
    p = sp.check_program("x = true\n", syntax="python")[0]
    assert (p.line, p.col, p.end_line, p.end_col, p.severity, p.code) == (1, 4, 1, 8, "error", "js_literal")
    assert p.message and p.hint and p.fix == {"line": 1, "col": 4, "end_line": 1, "end_col": 8, "text": "True"}
    assert p.params == {"name": "true", "good": "True"}


def test_pipeline_programs_are_checked_with_the_pipeline_parser():
    probs = sp.check_program("gaussian (0.4)\nnot_an_op (0.5)\n")
    assert [(p.line, p.code) for p in probs] == [(2, "pipeline_syntax")]
    assert sp.check_program("gaussian (0.4, 0.5)\nfor 2\nmedian (0.3)\nendfor\n") == []


# --------------------------------------------------------------------------- #
# 正しい例 → 指摘ゼロ(誤検出の試験。間違った例より多く)                         #
# --------------------------------------------------------------------------- #
RIGHT = [
    "img = gaussian(img, 0.4)\nshow(img)\n",
    "squares = [i * i for i in range(5)]\nodd = {i for i in squares if i % 2}\nd = {k: v for k, v in zip('ab', 'cd')}\n"
    "g = sum(x for x in squares)\nprint(squares, odd, d, g)\n",
    "f = lambda v, w=2: v * w\nprint(f(3))\n",
    "import os\nwith open(os.devnull) as fh:\n    print(fh.name)\n",
    "try:\n    v = 1 / 0\nexcept ZeroDivisionError as err:\n    print(err)\nelse:\n    print(v)\nfinally:\n    print('done')\n",
    "counter = 0\ndef bump():\n    global counter\n    counter += 1\nbump()\nprint(counter)\n",
    "x = [1, 2]\ndel x[0]\nprint(x)\n",
    "if (n := blob_count(otsu(img))) > 3:\n    print(n)\n",
    "def area(w: float, h: float = 1.0) -> float:\n    return w * h\nsize: int = 3\nprint(area(2), size)\n",
    "n = 3\nname = 'img'\nprint(f'{name}: {n:>4d} {n!r}')\n",
    "import functools\n@functools.lru_cache(maxsize=None)\ndef fib(k):\n    return k if k < 2 else fib(k - 1) + fib(k - 2)\nprint(fib(10))\n",
    "class Box:\n    def __init__(self, v):\n        self.v = v\n    def double(self):\n        return Box(self.v * 2)\nprint(Box(2).double().v)\n",
    "for s in [0.2, 0.4]:\n    img = gaussian(img, s)\nwhile False:\n    break\nelse:\n    pass\n",
    "mask = otsu(img)\nn = blob_count(mask)\nif n > 20:\n    img = median(img, 0.8)\nelif n > 5:\n    img = gaussian(img, 0.3)\nelse:\n    img = gaussian(img, 0.1)\nshow(img)\n",
    "d = sub_image(img, gaussian(img, 0.9))\nshow(d)\n",
    "p = pipeline([('gaussian', 0.4), ('otsu',)])\nout = p(img)\nshow(out)\n",
    "x = op('gaussian', img, a=0.4)\nshow(x)\n",
    "gaussian(0.4)\nmedian(0.3)\n",                               # 入力を省いた = 今の流れ(捨てていない)
    "text = 'gaussian（img）は全角でも文字列の中'  # コメントの中の，も対象外\nprint(text)\n",
    "a = np.zeros((3, 3))\nb = a.T @ a\nprint(b.shape)\n",
    "from fullseye.studio_prelude import *\nimg = image = studio_input()\nimg = gaussian(img, 0.4)\nstudio_output()\n",
    "x = 1\nif x:\n    y = 2\nelse:\n    y = 3\nprint(y)\n",
    "for i in range(3):\n    last = i\nprint(last)\n",
    "match 3:\n    case 1:\n        print('one')\n    case other:\n        print(other)\n",
    "async def go():\n    return 1\nprint(go)\n",
    "values = [*range(3), 4]\nfirst, *rest = values\nprint(first, rest)\n",
    "s = '''multi\nline（全角） string'''\nprint(s)\n",
    "assert img is not None, 'no image'\nshow(img)\n",
    "def outer():\n    total = 0\n    def inner():\n        nonlocal total\n        total += 1\n    inner()\n    return total\nprint(outer())\n",
    "ops = [%s]\nprint(len(ops))\n" % ", ".join(NAMES),           # 前置きの全 op 名
]


@pytest.mark.parametrize("text", RIGHT)
def test_right_examples_give_no_problems(text):
    probs = sp.check_program(text, syntax="python")
    assert probs == [], [(p.line, p.col, p.code, p.message) for p in probs]


def test_more_right_examples_than_wrong_ones():
    assert len(RIGHT) >= len(WRONG)


def test_500_lines_are_checked_quickly():
    big = "\n".join("x%d = gaussian(img, 0.%d)\nif x%d is not None:\n    img = median(x%d, 0.3)"
                    % (i, i % 9 + 1, i, i) for i in range(167))
    assert len(big.splitlines()) >= 500
    sp.check_program(big)                                             # 初回は op の表を作る
    best = min(_timed(lambda: sp.check_program(big)) for _ in range(3))
    print("check_program 500 lines: %.1f ms" % best)
    assert best < 200, best                                           # 目安 50 ms(実測は設計書)。重い機械でも落ちない幅


def _timed(fn):
    t0 = time.perf_counter()
    fn()
    return (time.perf_counter() - t0) * 1000


# --------------------------------------------------------------------------- #
# 任意の依存: ある時 / 塞いだ時                                                 #
# --------------------------------------------------------------------------- #
def _block(monkeypatch, *names):
    for n in names:
        for k in list(sys.modules):
            if k == n or k.startswith(n + "."):
                monkeypatch.delitem(sys.modules, k, raising=False)
        monkeypatch.setitem(sys.modules, n, None)                     # import が ImportError になる


def test_backends_listed_and_degrade_when_blocked(monkeypatch):
    rows = {r["name"]: r for r in sp.checker_backends()}
    assert rows["compile/ast/tokenize/difflib"]["available"]
    _block(monkeypatch, "parso", "pyflakes", "jedi")
    rows = {r["name"]: r for r in sp.checker_backends()}
    for n in ("parso", "pyflakes", "jedi"):
        assert not rows[n]["available"] and "pip install " + n in rows[n]["missing"]
    # 土台だけでも指摘する
    assert _codes("img = gausian(img, 0.4)\n")[0][2] == "undefined_name"
    assert _codes("x = (1,\ny = 2\nz = [1 2]\n")[0][2] == "unclosed_bracket"
    for text in RIGHT[:8]:
        assert sp.check_program(text, syntax="python") == [], text
    # 補完とホバーも前置きと組み込みの名前だけで答える
    names = [c["name"] for c in sp.complete("img = gaus", 1, 10)]
    assert "gaussian" in names and all(n.startswith("gaus") for n in names)
    h = sp.hover("img = gaussian(img)", 1, 8)
    assert h["name"] == "gaussian" and "image -> image" in h["signature"]
    assert sp.hover("x = len([1])", 1, 5)["name"] == "len"


def test_parso_adds_later_syntax_errors_without_cascading():
    pytest.importorskip("parso")
    probs = sp.check_program("x = (1,\ny = 2\nz = [1 2]\nw = 3\nv = [4 5]\n", syntax="python")
    assert probs[0].code == "unclosed_bracket" and len(probs) >= 2
    assert all(p.severity == "error" for p in probs) and len(probs) <= sp.MAX_SYNTAX_ERRORS


def test_pyflakes_reports_unused_imports_and_order():
    pytest.importorskip("pyflakes")
    assert ("unused_import" in [c for _l, _c, c in _codes("import os\nx = 1\nprint(x)\n")])
    assert _codes("print(later)\nlater = 1\n")[0][2] == "undefined_name"       # 順序まで見る
    for text in RIGHT:
        probs = [p for p in sp.check_program(text, syntax="python") if p.severity == "error"]
        assert probs == [], (text, [(p.line, p.code, p.message) for p in probs])


def test_jedi_completion_knows_the_prelude_and_numpy():
    pytest.importorskip("jedi")
    names = [c["name"] for c in sp.complete("img = gaus", 1, 10)]
    assert "gaussian" in names
    names = [c["name"] for c in sp.complete("x = np.zer", 1, 10)]
    assert "zeros" in names


# --------------------------------------------------------------------------- #
# Debug / Release                                                                #
# --------------------------------------------------------------------------- #
PROGS = [
    "mask = threshold(img, 0.5)\nn = blob_count(mask)\nif n > 2:\n    img = gaussian(img, 0.9)\nelse:\n    img = median(img, 0.3)\n",
    "for s in [0.2, 0.4]:\n    img = gaussian(img, s)\nk = 0\nwhile k < 3:\n    k += 1\n    img = median(img, 0.2)\n",
    "def f(x):\n    return gaussian(x, 0.3)\nimg = f(f(img))\np = pipeline([('sobel_amp',), ('otsu',)])\nshow(p(img))\n",
]


@pytest.mark.parametrize("text", PROGS)
def test_debug_and_release_give_the_same_record_and_output(text):
    img = _gray()
    md, mr = sp.OpMemo(), sp.OpMemo()
    d = sp.run_program(text, img, config="debug", memo=md)
    r = sp.run_program(text, img, config="release", memo=mr)
    assert d.ok and r.ok, (d.errors, r.errors)
    assert d.stages() == r.stages() and d.stage_lines() == r.stage_lines()
    assert [c.pipeline_step for c in d.calls] == [c.pipeline_step for c in r.calls]
    assert np.array_equal(np.asarray(d.output), np.asarray(r.output))
    assert d.config == "debug" and r.config == "release"
    r2 = sp.run_program(text, img, config="release", memo=mr)
    eligible = [c for c in r2.calls if sp.memo_eligible(c.op)]
    assert eligible, [c.op for c in r2.calls]                          # 対象が 0 件なら何も確かめていない
    assert all(c.cached for c in eligible)                             # メモ化も同じ


def test_release_stops_at_op_boundaries_and_time_limit():
    r = sp.run_program("while True:\n    img = gaussian(img, 0.1)\n", _gray(), config="release", time_limit_s=0.3)
    assert r.stopped == "time_limit" and r.stopped_line == 2 and r.errors[0].startswith("line 2:")
    ev = threading.Event()
    threading.Timer(0.2, ev.set).start()
    r = sp.run_program("while True:\n    img = median(img, 0.2)\n", _gray(), config="release", time_limit_s=None,
                       stop_event=ev)
    assert r.stopped == "stop_requested" and r.stopped_line == 2


def test_release_says_breakpoints_do_not_stop():
    r = sp.run_program("img = gaussian(img, 0.2)\nimg = median(img, 0.3)\n", _gray(), config="release",
                       breakpoints=[2], max_lines=1)
    assert r.ok and len(r.calls) == 2 and r.stopped is None
    assert len(r.notes) >= 2, r.notes
    assert any("Release does not stop at breakpoints (lines 2)" in n for n in r.notes)
    assert any("line by line" in n for n in r.notes)
    with pytest.raises(ValueError, match="config"):
        sp.run_program("x = 1\n", _gray(), config="fast")


# --------------------------------------------------------------------------- #
# 実行の対象 = ファイル、名前空間を残す、sys.path を戻す、(ファイル, 行)          #
# --------------------------------------------------------------------------- #
def _project(tmp_path):
    proj = tmp_path / "proj"
    (proj / "programs").mkdir(parents=True)
    (proj / "programs" / "helper.py").write_text(
        "from fullseye.studio_prelude import *\n"
        "def smooth(x, n):\n"
        "    for _ in range(n):\n"
        "        x = gaussian(x, 0.3)\n"
        "    return x\n"
        "def broken(x):\n"
        "    return x / 0\n", encoding="utf-8")
    main = proj / "programs" / "main.py"
    main.write_text("import helper\nimg = helper.smooth(img, 2)\nn = blob_count(otsu(img))\n", encoding="utf-8")
    return proj, main


def test_run_file_imports_project_modules_and_restores_sys_path(tmp_path):
    proj, main = _project(tmp_path)
    before_path, had_helper = list(sys.path), "helper" in sys.modules
    r = sp.run_file(str(main), _gray(), project_dir=str(proj))
    assert r.ok, r.errors
    assert r.filename == str(main.resolve()) or r.filename == os.path.abspath(str(main))
    assert [c.op for c in r.calls] == ["gaussian", "gaussian", "otsu", "blob_count"]
    assert [c.line for c in r.calls][-2:] == [3, 3]                    # 実行したファイルの行
    assert sys.path == before_path                                     # 足した道は戻る
    assert ("helper" in sys.modules) == had_helper                    # 利用者のモジュールは外す(直すと読み直す)


def test_errors_are_reported_as_file_and_line(tmp_path):
    proj, main = _project(tmp_path)
    main.write_text("import helper\nx = 1\ny = helper.broken(x)\n", encoding="utf-8")
    r = sp.run_file(str(main), _gray(), project_dir=str(proj))
    assert r.errors[0].startswith("line 3: ZeroDivisionError") and r.error_line == 3
    assert r.error_file.endswith("helper.py")
    assert len(r.notes) >= 1, r.notes
    assert any("helper.py line 7" in n for n in r.notes)
    r = sp.run_program("x = 1\ny = x / 0\n", _gray())
    assert r.error_file == sp.PROGRAM_FILENAME and r.error_line == 2


def test_breakpoints_work_in_a_file(tmp_path):
    proj, main = _project(tmp_path)
    r = sp.run_file(str(main), _gray(), project_dir=str(proj), breakpoints=[3])
    assert r.stopped == "breakpoint" and r.stopped_line == 3 and [c.op for c in r.calls] == ["gaussian", "gaussian"]


def test_evaluate_in_the_namespace_after_a_run():
    r = sp.run_program("mask = otsu(img)\nn = blob_count(mask)\n", _gray())
    assert r.ok and r.namespace is not None
    e = sp.evaluate("n + 1", r)
    assert e["error"] is None and e["value"] == r.values["n"] + 1
    e = sp.evaluate("g = gaussian(img, 0.2)\nprint(g.shape)", r)
    assert e["error"] is None and e["value"] is None and e["stdout"] == "(48, 48)\n" and [c.op for c in e["calls"]] == ["gaussian"]
    assert "g" in r.namespace and len(r.calls) == 3                    # 記録はその実行に足される
    e = sp.evaluate("undefined_thing", r)
    assert e["error"].startswith("line 1: NameError")
    assert sp.evaluate("1", None)["error"].startswith("no namespace")
    assert sp.run_program("x = 1\n", _gray(), keep_namespace=False).namespace is None


def test_starter_program_runs_and_shows_a_picture_and_stages():
    text = sp.STARTER_PROGRAM
    assert 10 <= len([l for l in text.splitlines() if l.strip()]) <= 15
    assert sp.detect_syntax(text) == ("python", [])
    assert [p for p in sp.check_program(text, syntax="python") if p.severity != "hint"] == []
    r = sp.run_program(text, _gray())
    assert r.ok, r.errors
    ops = [c.op for c in r.calls]
    assert ops[:3] == ["gaussian", "otsu", "blob_count"] and len(ops) == 4
    assert r.output_source.startswith("show line") and isinstance(r.output, np.ndarray) and r.output.ndim == 2
    assert r.stdout.startswith("blobs: ")
    assert r.output.shape != (48, 48)                                  # 同梱の coins を読んだ

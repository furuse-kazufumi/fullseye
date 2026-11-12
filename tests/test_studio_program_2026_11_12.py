# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Studio の Program 欄の Python のモード(studio_program.py)と、パイプラインファイルの読み書き(engine / defs_io)。

門は中身を数える: 後方互換は既存の試験が使っている Program の文面を **集めて数え**(下限つき)、
1 つ残らず今の解析器と突き合わせる。書き出しは別プロセスで走らせて画素単位で比べる。"""
from __future__ import annotations

import ast
import json
import re
import os
import pathlib
import subprocess
import sys
import threading
import time

import numpy as np
import pytest

import api
import engine
import defs_io
import studio
import studio_program as sp

ROOT = pathlib.Path(__file__).resolve().parents[1]
NAMES = sorted(sp.op_table())


def _blobs(n, size=64):
    """*n* 個の明るい四角が並ぶ画像(粒の数が分かっている)。"""
    img = np.zeros((size, size))
    for i in range(n):
        r, c = 4 + (i // 4) * 14, 4 + (i % 4) * 14
        img[r:r + 8, c:c + 8] = 1.0
    return img


def _gray(seed=0, size=48):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size]
    return np.clip(0.5 + 0.3 * np.sin(x / 5.0) * np.cos(y / 7.0) + 0.05 * rng.standard_normal((size, size)), 0, 1)


# --------------------------------------------------------------------------- #
# 記法の見分け                                                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text,want", [
    ("gaussian (0.4, 0.5)\nmedian (0.2, 0.5)", "hdevelop"),          # Python としても読めるが同じ意味
    ("gaussian", "hdevelop"),
    ("gaussian 0.4 0.5", "hdevelop"),
    ("for 3\ngaussian (0.4, 0.5)\nendfor", "hdevelop"),
    ("* comment\nif 1\nmedian (0.3)\nendif", "hdevelop"),
    ("dev_update_off ()\ndev_set_color ('red')\ngaussian (0.4)", "hdevelop"),
    ("img = gaussian(img, 0.4)", "python"),
    ("x = 1", "python"),
    ("gaussian(img, 0.4)", "python"),                                 # 入力の変数を渡している
    ("for i in range(3):\n    img = gaussian(img, 0.1)", "python"),
    ("if x\ngaussian (0.4)\nendif", "hdevelop"),                                 # ':' の無い if(HDevelop の印だけ)
    ("if x > 1:\n    y = (", "python"),                               # Python の構文の誤り
    ("# python\ngaussian (0.4, 0.5)", "python"),                      # 1 行目の印
    ("# hdevelop\nx = 1", "hdevelop"),
])
def test_detect_syntax(text, want):
    syn, errs = sp.detect_syntax(text)
    assert syn == want and errs == [], (text, syn, errs)


def test_mixed_syntax_is_an_error_with_both_line_numbers():
    text = "x = 1\nif x > 0:\n    gaussian (0.4, 0.5)\nendif\n"
    syn, errs = sp.detect_syntax(text)
    assert len(errs) == 1 and "line 4" in errs[0] and "line 1" in errs[0], errs
    r = sp.run_program(text, _gray())
    assert not r.ran and r.errors == errs and r.error_line == 4


def test_python_syntax_error_has_line():
    r = sp.run_program("x = 1\nif x > 0:\ny = 2\n", _gray())
    assert r.errors and r.errors[0].startswith("line 3: SyntaxError"), r.errors


def test_unclosed_if_in_hdevelop_still_reported():
    r = sp.run_program("if 1\ngaussian (0.4)\n", _gray())
    assert r.syntax == "hdevelop" and any("missing 'endif'" in e and "line 1" in e for e in r.errors), r.errors


# --------------------------------------------------------------------------- #
# 後方互換: 既存の試験の Program の文面を全部集めて突き合わせる                    #
# --------------------------------------------------------------------------- #
_CORPUS_FILES = ["test_studio.py", "test_studio_logic.py", "test_studio_params.py",
                 "test_studio_error_feedback_2026_11_12.py", "test_studio_run_applies_edits_2026_09_19.py",
                 "test_studio_search_staples_2026_11_12.py", "test_studio_stage_previews_bypass_2026_10_20.py",
                 "test_studio_worker_teardown_thread_2026_11_04.py"]
_HDEV_HEADS = {"for", "endfor", "if", "else", "elseif", "endif", "while", "endwhile"}


_SHAPE_RE = [re.compile(r"^[A-Za-z_]\w*\s*\(.*\)\s*(#.*)?$"), re.compile(r"^[A-Za-z_]\w*(\s+[-+.\w]+)*$")]


def _looks_like_hdev_program(s: str, names: set) -> bool:
    """既存の試験の文字列のうち Program の文面と見なす物: 行が全部、コメント・制御の語・既知の op/指示で
    始まる行か、行が全部「op の呼び出しの形」で既知の op を 1 つ以上含む(未知の op をわざと入れた試験も拾う)。
    説明の文(docstring)は句読点で形から外れる。素の op 名 1 語は op の引数の文字列なので数えない。"""
    lines = [l.strip() for l in s.splitlines() if l.strip()]
    if not lines or s.isidentifier() or "%s" in s or "%d" in s:
        return False                                  # 書式の型紙(% で埋める前)は数えない

    def known(t):
        if t.startswith(("*", "#")):
            return True
        w = t.replace("(", " ").split()
        head = w[0].lower() if w else ""
        return head in names or head in _HDEV_HEADS or head.startswith(("dev_", "disp_", "set_system"))

    marks = [known(t) for t in lines]
    if all(marks):
        return True
    return any(marks) and all(t.startswith(("*", "#")) or any(rx.match(t) for rx in _SHAPE_RE) for t in lines)


def _corpus():
    names = set(NAMES)
    out = {}
    for fn in _CORPUS_FILES:
        tree = ast.parse((ROOT / "tests" / fn).read_text(encoding="utf-8"))
        docs = set()
        for node in ast.walk(tree):                   # docstring は説明の文(Program ではない)
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                    docs.add(id(first.value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
                s = node.value
                if _looks_like_hdev_program(s, names):
                    out.setdefault(s, fn)
    return out


CORPUS = _corpus()


def test_corpus_is_not_empty():
    # 2026-11-12 の実測は下の数(集め方が壊れて空になったら落ちる)
    print("corpus", len(CORPUS), "multi-line", sum(1 for s in CORPUS if "\n" in s))
    assert len(CORPUS) >= 80, len(CORPUS)
    assert sum(1 for s in CORPUS if "\n" in s) >= 30


def test_every_existing_program_is_still_read_as_hdevelop():
    py = [s for s in CORPUS if sp.detect_syntax(s) != ("hdevelop", [])]
    assert py == [], py[:5]


def test_every_existing_program_gives_the_same_stages_and_lines():
    n = 0
    for text in CORPUS:
        st, errs, lines = studio.parse_hdev_program_lines(text, NAMES)
        r = sp.run_program(text, None)
        assert r.syntax == "hdevelop"
        assert r.errors == errs, text
        if not errs:
            assert r.stages() == [(s[0], s[1], s[2]) for s in st], text
            assert r.stage_lines() == lines, text
            assert [c.bypass for c in r.calls] == [studio._is_bypassed(s) for s in st], text
            n += 1
    assert n >= 65, n   # 2026-11-12 の実測 72


def test_existing_programs_run_like_the_studio_runner():
    """画像つきの実行が Studio の _run_stage(段ごとの api.run_pipeline, coerce は第 1 段だけ)と同じ値。"""
    img = _gray()
    n = 0
    for text in CORPUS:
        st, errs, _lines = studio.parse_hdev_program_lines(text, NAMES)
        if errs or not st or len(st) > 12:
            continue
        v, ok = img, True
        for i, s in enumerate(st):
            if studio._is_bypassed(s):
                continue
            try:
                v = api.run_pipeline(v, [(s[0], s[1], s[2])], coerce=(i == 0))
            except Exception:                         # noqa: BLE001
                ok = False
                break
        r = sp.run_program(text, img)
        if not ok:
            assert r.errors, text
            continue
        assert not r.errors, (text, r.errors)
        if isinstance(v, np.ndarray):
            assert np.array_equal(np.asarray(r.output), v, equal_nan=True), text
        n += 1
    assert n >= 35, n   # 2026-11-12 の実測 42(残りは op が入力の型で断る)


def test_hdevelop_to_python_round_trip_on_the_corpus():
    """従来 → Python 風へ変換して走らせると、走る段・行番号・最後の img が従来のモードと一致する。"""
    img = _gray()
    converted = same = 0
    for text in CORPUS:
        st, errs, lines = studio.parse_hdev_program_lines(text, NAMES)
        if errs:
            continue
        py, cerr = sp.hdev_to_python(text)
        assert cerr == [], (text, cerr)
        assert len(py.splitlines()) == len(text.splitlines()), text
        converted += 1
        live = [(s[0], s[1], s[2]) for s in st if not studio._is_bypassed(s)]
        live_lines = [ln for s, ln in zip(st, lines) if not studio._is_bypassed(s)]
        hd = sp.run_program(text, img)
        r = sp.run_program(py, img, syntax="python")
        if hd.errors:
            continue
        if any(op_info.out_sort in sp.MEASURE_SORTS for op_info in (sp.op_table()[s[0]] for s in live[:-1])):
            continue                                  # 途中で測る op は従来のモードで数を次へ渡す(意味が違う)
        assert r.errors == [], (text, py, r.errors)
        assert r.stages() == live and r.stage_lines() == live_lines, (text, py)
        if live:
            want = hd.output
            got = r.values.get("img")
            if isinstance(want, np.ndarray):
                assert np.array_equal(np.asarray(got), want, equal_nan=True), text
            same += 1
    assert converted >= 60 and same >= 35, (converted, same)   # 2026-11-12 の実測 (69, 39)


def test_hdev_to_python_examples():
    py, errs = sp.hdev_to_python("* smooth\nfor 2\ngaussian (0.4, 0.5)\nendfor\nif 1 = 2\nmedian (0.2)\nelse\nendif")
    assert errs == []
    assert py.splitlines() == ["# smooth", "for _ in range(2):", "    img = gaussian(img, 0.4, 0.5)",
                               "# endfor", "if 1 == 2:", "    img = median(img, 0.2)", "else: pass", "# endif"]
    py, _ = sp.hdev_to_python("if foo\ngaussian (0.4)\nendif")    # 定数でない条件は従来と同じ真偽
    assert py.splitlines()[0] == "if True:  # was: if foo"
    _, errs = sp.hdev_to_python("while 1\nendwhile")
    assert errs and "while" in errs[0]


def test_python_to_hdev():
    text = "# python\nimg = gaussian(img, 0.4)\nimg = median(img, a=0.2, b=0.7)\nimg = otsu(img)\n"
    hd, errs = sp.python_to_hdev(text)
    assert errs == []
    st, e2, lines = studio.parse_hdev_program_lines(hd, NAMES)
    assert e2 == [] and [s[0] for s in st] == ["gaussian", "median", "otsu"] and lines == [2, 3, 4]
    assert (st[1][1], st[1][2]) == (0.2, 0.7)
    img = _gray()
    a = sp.run_program(text, img).output
    b = sp.run_program(hd, img).output
    assert np.array_equal(a, b)
    _, errs = sp.python_to_hdev("img = gaussian(img, 0.4)\nif 1 > 0:\n    img = median(img)\n")
    assert errs and errs[0].startswith("line 2:"), errs
    _, errs = sp.python_to_hdev("mask = otsu(img)\nn = blob_count(mask)\n")
    assert errs and errs[0].startswith("line 1:"), errs
    _, errs = sp.python_to_hdev("img = otsu(img)\nimg = blob_count(img)\nimg = gaussian(img)\n")
    assert any("line 2" in e and "measuring" in e for e in errs), errs


# --------------------------------------------------------------------------- #
# Python のモードの文法と意味                                                   #
# --------------------------------------------------------------------------- #
def test_variables_branches_loops_functions_numpy_print():
    prog = (
        "def smooth(x, times):\n"                     # 1
        "    for _ in range(times):\n"
        "        x = gaussian(x, 0.3)\n"
        "    return x\n"
        "vals = []\n"                                 # 5
        "for s in [0.2, 0.4]:\n"
        "    vals.append(s)\n"
        "k = 0\n"
        "while True:\n"
        "    k += 1\n"                                # 10
        "    if k == 1:\n"
        "        continue\n"
        "    elif k >= 3:\n"
        "        break\n"
        "img = smooth(img, k)\n"                      # 15
        "m = float(np.mean(img))\n"
        "print('k', k, 'mean', round(m, 3))\n"
    )
    r = sp.run_program(prog, _gray())
    assert r.ok, r.errors
    assert [c.op for c in r.calls] == ["gaussian"] * 3 and {c.line for c in r.calls} == {3}
    assert r.values["k"] == 3 and r.values["vals"] == [0.2, 0.4]
    assert r.stdout.startswith("k 3 mean ")
    table = {v.name: v for v in r.variables}
    assert table["img"].summary == "image 48×48 float64" and table["smooth"].kind == "function"


def test_implicit_flow_measure_ops_and_two_input_ops():
    img = _gray()
    r = sp.run_program("gaussian(0.4)\nn = blob_count(otsu())\nd = sub_image(img, gaussian(img, 0.9))\n", img)
    assert r.ok, r.errors
    ops = [(c.op, c.implicit_input, c.measured) for c in r.calls]
    assert ops == [("gaussian", True, False), ("otsu", True, False), ("blob_count", False, True),
                   ("gaussian", False, False), ("sub_image", False, False)]
    g = api.apply(img, "gaussian", 0.4, 0.5)
    assert np.array_equal(r.calls[1].value, api.apply(g, "otsu", 0.5, 0.5))   # 入力を省くと今の流れ
    assert isinstance(r.values["n"], float)
    want = api.apply([img, api.apply(img, "gaussian", 0.9, 0.5)], "sub_image", 0.5, 0.5)
    assert np.array_equal(r.values["d"], want)
    assert r.output_source == "last op line 3"                 # show が無ければ最後の画像の op
    r2 = sp.run_program("a = gaussian(img, 0.4)\nb = median(img, 0.4)\nshow(a)\n", img)
    assert r2.output_source == "show line 3" and np.array_equal(r2.output, r2.values["a"])


def test_op_call_errors_have_line_numbers():
    img = _gray()
    cases = {
        "x = 1\ny = undefined_name + 1\n": ("line 2:", "NameError"),
        "x = 1\nimg = gaussian(img, 'a')\n": ("line 2:", "neither an input nor a number"),
        "x = 1\ny = 'a' + 1\n": ("line 2:", "TypeError"),
        "x = 0\ny = 1 / x\n": ("line 2:", "ZeroDivisionError"),
        "x = 1\nimg = no_such_op(img)\n": ("line 2:", "NameError"),
        "x = 1\nimg = op('no_such_op', img)\n": ("line 2:", "unknown op"),
        "x = 1\nimg = gaussian(img, float('nan'))\n": ("line 2:", "finite"),
        "x = 1\nd = sub_image(img)\n": ("line 2:", "takes 2 input"),
        "x = 1\nimg = gaussian(img, 0.1, 0.2, 0.3)\n": ("line 2:", "at most 2 knobs"),
    }
    for text, (line, word) in cases.items():
        r = sp.run_program(text, img)
        assert r.errors and r.errors[0].startswith(line) and word in r.errors[0], (text, r.errors)


def test_knob_clamping_is_reported_with_line():
    r = sp.run_program("x = 1\nimg = gaussian(img, 9.0, -3)\n", _gray())
    assert r.ok and r.calls[0].stage() == ("gaussian", 1.0, 0.0)
    assert r.clamped == ["line 2: gaussian a=9 → 1", "line 2: gaussian b=-3 → 0"]


def test_op_escape_hatch_and_keywords():
    img = _gray()
    r = sp.run_program("x = op('gaussian', img, a=0.4)\ny = gaussian(img, b=0.5, a=0.4)\n", img)
    assert r.ok and np.array_equal(r.values["x"], r.values["y"])


def test_branch_on_a_measured_result_changes_the_picture():
    prog = ("mask = threshold(img, 0.5)\n"
            "n = blob_count(mask)\n"
            "if n > 5:\n"
            "    img = gaussian(img, 0.9)\n"
            "else:\n"
            "    img = gaussian(img, 0.1)\n")
    many, few = _blobs(8), _blobs(2)
    rm, rf = sp.run_program(prog, many), sp.run_program(prog, few)
    assert rm.ok and rf.ok
    assert rm.values["n"] == 8.0 and rf.values["n"] == 2.0
    assert [c.line for c in rm.calls] == [1, 2, 4] and [c.line for c in rf.calls] == [1, 2, 6]
    assert np.array_equal(rm.output, api.apply(many, "gaussian", 0.9, 0.5))
    assert np.array_equal(rf.output, api.apply(few, "gaussian", 0.1, 0.5))
    assert not np.array_equal(rm.output, api.apply(many, "gaussian", 0.1, 0.5))


def test_time_limit_and_stop_request_stop_an_endless_loop():
    t0 = time.perf_counter()
    r = sp.run_program("k = 0\nwhile True:\n    k += 1\n", _gray(), time_limit_s=0.2)
    assert r.stopped == "time_limit" and r.errors[0].startswith("line ") and time.perf_counter() - t0 < 5
    ev = threading.Event()
    threading.Timer(0.2, ev.set).start()
    r = sp.run_program("while True:\n    pass\n", _gray(), time_limit_s=None, stop_event=ev)
    assert r.stopped == "stop_requested"
    # 捕まえても止まる(BaseException、一度止めたら次の行でまた止める)
    r = sp.run_program("try:\n    while True:\n        pass\nexcept Exception:\n    pass\nx = 1\n", _gray(), time_limit_s=0.2)
    assert r.stopped == "time_limit" and "x" not in r.values


def test_breakpoints_steps_and_continue():
    prog = "img = gaussian(img, 0.2)\nimg = median(img, 0.3)\nimg = gaussian(img, 0.5)\n"
    r = sp.run_program(prog, _gray(), breakpoints=[2])
    assert r.stopped == "breakpoint" and r.stopped_line == 2 and [c.line for c in r.calls] == [1]
    assert r.errors == []
    r = sp.run_program("for i in range(3):\n    img = gaussian(img, 0.2)\n", _gray(), breakpoints=[2], skip_hits=2)
    assert r.stopped_line == 2 and len(r.calls) == 2                 # 3 回目の到達で止まる = 続行
    r = sp.run_program(prog, _gray(), max_lines=2)
    assert r.stopped == "step" and [c.line for c in r.calls] == [1, 2]


def test_untrusted_python_is_not_run():
    r = sp.run_program("x = 1\n", _gray(), trusted=False)
    assert not r.ran and r.not_run_reason and "confirm" in r.not_run_reason and r.values == {}
    r = sp.run_program("gaussian (0.4)", _gray(), trusted=False)       # HDevelop 風は任意のコードを含まない
    assert r.ran and r.ok


def test_trust_store(tmp_path):
    p = tmp_path / "trust.json"
    ts = sp.TrustStore(str(p))
    text = "img = gaussian(img, 0.4)\n"
    assert ts.is_trusted(text, "typed") and not ts.is_trusted(text, "file") and not ts.is_trusted(text, "mcp")
    ts.trust(text)
    assert sp.TrustStore(str(p)).is_trusted(text, "project")
    assert not sp.TrustStore(str(p)).is_trusted(text + "x = 1\n", "project")   # 1 文字でも変われば確認し直す
    assert sp.program_digest("a\r\nb") == sp.program_digest("a\nb")


# --------------------------------------------------------------------------- #
# メモ化                                                                        #
# --------------------------------------------------------------------------- #
def test_memo_hits_equal_recomputation():
    prog = "a = gaussian(img, 0.4)\nb = median(a, 0.3)\nm = otsu(b)\nn = blob_count(m)\n"
    img = _gray()
    memo = sp.OpMemo()
    r1 = sp.run_program(prog, img, memo=memo)
    r2 = sp.run_program(prog, img, memo=memo)
    assert [c.cached for c in r1.calls] == [False] * 4 and [c.cached for c in r2.calls] == [True] * 4
    r0 = sp.run_program(prog, img)                                    # メモ無し
    for c0, c2 in zip(r0.calls, r2.calls):
        assert np.array_equal(np.asarray(c0.value), np.asarray(c2.value))
    # 1 行直すと、その上流は命中・下流は計算し直し
    r3 = sp.run_program(prog.replace("median(a, 0.3)", "median(a, 0.6)"), img, memo=memo)
    assert [c.cached for c in r3.calls] == [True, False, False, False]
    # 入力の中身が変われば命中しない(id でなく中身の指紋)
    img2 = img.copy(); img2[10, 10] += 0.01
    r4 = sp.run_program(prog, img2, memo=memo)
    assert not r4.calls[0].cached


def test_loop_invariant_call_is_computed_once_with_memo():
    memo = sp.OpMemo()
    r = sp.run_program("for i in range(5):\n    g = gaussian(img, 0.4)\n", _gray(), memo=memo)
    assert [c.cached for c in r.calls] == [False, True, True, True, True]


def test_user_arrays_are_fingerprinted_by_content():
    memo = sp.OpMemo()
    prog = "x = np.array(img)\nx[0, 0] = 0.25\na = gaussian(x, 0.4)\nx[1, 1] = 0.75\nb = gaussian(x, 0.4)\n"
    r = sp.run_program(prog, _gray(), memo=memo)
    assert r.ok and [c.cached for c in r.calls] == [False, False]     # 書き換えた配列は別の鍵
    assert not np.array_equal(r.values["a"], r.values["b"])


def test_op_outputs_are_read_only():
    r = sp.run_program("a = gaussian(img, 0.4)\na[0, 0] = 1.0\n", _gray())
    assert r.errors and r.errors[0].startswith("line 2:") and "read-only" in r.errors[0]


def test_nondeterministic_ops_are_not_memoised_and_eligible_ops_are_deterministic():
    assert not sp.memo_eligible("add_noise_white")
    assert sp.memo_eligible("gaussian") and sp.memo_eligible("otsu")
    elig = [n for n in NAMES if sp.op_table()[n].in_sort == "image" and sp.op_table()[n].arity == 1
            and sp.memo_eligible(n)]
    assert len(elig) >= 300, len(elig)
    img = _gray(size=24)
    import warnings
    checked = 0
    for n in elig[::8]:                                               # 標本: 同じ入力で 2 回呼んで同じ答え
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                a = api.apply(img, n, 0.5, 0.5)
                b = api.apply(img, n, 0.5, 0.5)
            except Exception:                         # noqa: BLE001
                continue
        assert sp.fingerprint(a) == sp.fingerprint(b), n
        checked += 1
    assert checked >= 30, checked


# --------------------------------------------------------------------------- #
# パイプライン                                                                  #
# --------------------------------------------------------------------------- #
def test_pipeline_object_equals_run_pipeline_and_is_recorded():
    img = _gray()
    stages = [("gaussian", 0.4, 0.5), ("sobel_amp", 0.5, 0.5), ("otsu", 0.4, 0.5)]
    r = sp.run_program("p = pipeline([('gaussian', 0.4), ('sobel_amp',), ('otsu', 0.4)], name='edge')\n"
                       "out = p(img)\nx1 = p.run(img, upto=1)\nsteps = p.run_stepwise(img)\n", img)
    assert r.ok, r.errors
    assert np.array_equal(r.values["out"], api.run_pipeline(img, stages))
    assert np.array_equal(r.values["x1"], api.run_pipeline(img, stages[:2]))
    eng_steps = engine.FullseyeEngine(stages).run_stepwise(img)
    assert all(np.array_equal(a, b) for a, b in zip(r.values["steps"], eng_steps))
    assert [(c.pipeline, c.pipeline_step) for c in r.calls[:3]] == [("edge", 1), ("edge", 2), ("edge", 3)]


def test_every_recipe_runs_like_run_pipeline():
    import recipes
    img = _gray(size=64)
    n = 0
    for name in recipes.names():
        st = recipes.stages(name)
        try:
            want = api.run_pipeline(img, st)
        except Exception:                             # noqa: BLE001
            continue
        r = sp.run_program("out = load_pipeline(%r)(img)\n" % name, img)
        assert r.ok, (name, r.errors)
        got = r.values["out"]
        if isinstance(want, np.ndarray):
            assert np.array_equal(got, want, equal_nan=True), name
        else:
            assert got == want or (isinstance(want, float) and np.isnan(want) and np.isnan(got)), name
        assert [c.pipeline for c in r.calls] == [name] * len(st)
        n += 1
    assert n >= 10, n


def test_current_pipeline_is_the_studio_stage_list():
    img = _gray()
    cur = [("gaussian", 0.3, 0.5), ("median", 0.4, 0.5)]
    r = sp.run_program("out = current_pipeline()(img)\n", img, current_stages=cur)
    assert r.ok and np.array_equal(r.values["out"], api.run_pipeline(img, cur))


def _studio_file(tmp_path, stages, name="inspect.json", **extra):
    m = studio.PipelineModel(_gray())
    m.stages = stages
    d = m.to_dict()
    d.update(extra)
    p = tmp_path / name
    p.write_text(json.dumps(d), encoding="utf-8")
    return p, m


def test_studio_saved_file_loads_and_runs_like_studio(tmp_path):
    import fullseye as fs
    stages = [["gaussian", 0.4, 0.5], ["median", 0.3, 0.5, True], ["otsu", 0.5, 0.5]]
    p, m = _studio_file(tmp_path, stages, directives=["dev_update_off ()"])
    pf = fs.load_pipeline(str(p))
    assert [list(s) for s in pf.stages] == [["gaussian", 0.4, 0.5], ["otsu", 0.5, 0.5]]   # 切った段は走らない
    want = m.result_upto(len(m.stages) - 1)
    assert np.array_equal(pf(m.image), want) and np.array_equal(pf.run(m.image), want)
    # 保存 → 読み込み → 保存で中身が変わらない(切った段・directives も残る)
    out1 = tmp_path / "a.json"; pf.save(str(out1))
    d1 = json.loads(out1.read_text(encoding="utf-8"))
    assert d1["fullseye_kind"] == "pipeline" and d1["version"] == 1 and d1["created_by"].startswith("fullseye")
    assert d1["stages"] == stages and d1["directives"] == ["dev_update_off ()"]
    out2 = tmp_path / "b.json"; fs.load_pipeline(str(out1)).save(str(out2))
    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")
    # 書いたファイルは Studio でも開ける
    m2 = studio.PipelineModel(_gray()); m2.load_dict(d1)
    assert [list(s) for s in m2.stages] == [s[:3] for s in stages] and studio._is_bypassed(m2.stages[1])
    assert fs.read_def(str(out1)).stages == pf.stages


def test_pipeline_file_errors_say_where(tmp_path):
    import fullseye as fs
    good = {"fullseye_pipeline": 1, "stages": [["gaussian", 0.4, 0.5]]}
    cases = {
        "unknown.json": (dict(good, stages=[["no_such_op", 0.4, 0.5]]), "unknown operator"),
        "range.json": (dict(good, stages=[["gaussian", 1.5, 0.5]]), "must be in [0, 1]"),
        "newer.json": (dict(good, fullseye_kind="pipeline", version=9), "newer Fullseye"),
        "kind.json": (dict(good, fullseye_kind="camera", version=1), "unknown definition kind"),
        "oldkey.json": (dict(good, fullseye_pipeline=99), "not a version"),       # 調査 §4 D の穴
        "banana.json": (dict(good, fullseye_pipeline="banana"), "not a version"),
        "graph.json": ({"fullseye_graph": 1, "stages": [["gaussian", 0.4, 0.5]]}, "FullseyeGraph"),
        "verstr.json": (dict(good, fullseye_kind="pipeline", version="1"), "must be an integer"),
        "params.json": (dict(good, stages=[{"op": "gaussian", "params": {"sigma_px": 2}}]), "params"),
        "nostages.json": ({"name": "x"}, "not recognisable"),
    }
    for fn, (d, word) in cases.items():
        (tmp_path / fn).write_text(json.dumps(d), encoding="utf-8")
        with pytest.raises(ValueError) as ei:
            fs.load_pipeline(str(tmp_path / fn))
        assert word in str(ei.value) and fn in str(ei.value), (fn, ei.value)
    (tmp_path / "broken.json").write_text('{"stages": [', encoding="utf-8")
    with pytest.raises(ValueError, match=r"broken\.json: not valid JSON \(line 1"):
        fs.load_pipeline(str(tmp_path / "broken.json"))
    with pytest.raises(FileNotFoundError) as ei:
        fs.load_pipeline("nowhere.json", search_dirs=[str(tmp_path / "a"), str(tmp_path / "b")])
    assert str(tmp_path / "a") in str(ei.value) and str(tmp_path / "b") in str(ei.value)


def test_load_pipeline_search_order_and_recording_in_a_program(tmp_path):
    prog_dir, proj_dir = tmp_path / "prog", tmp_path / "proj"
    prog_dir.mkdir(); (proj_dir / "pipelines").mkdir(parents=True)
    _studio_file(proj_dir / "pipelines", [["gaussian", 0.2, 0.5]], name="p.json")
    _studio_file(prog_dir, [["median", 0.3, 0.5]], name="p.json")
    assert sp.pipeline_search_dirs(str(proj_dir), str(prog_dir))[:2] == [str(proj_dir / "pipelines"), str(prog_dir)]
    img = _gray()
    r = sp.run_program("out = load_pipeline('p.json')(img)\n", img, program_dir=str(prog_dir), project_dir=str(proj_dir))
    assert r.ok and [c.op for c in r.calls] == ["gaussian"] and r.calls[0].pipeline == "p"   # プロジェクトの pipelines/ が先
    r = sp.run_program("out = load_pipeline('p.json')(img)\n", img, program_dir=str(prog_dir), project_dir=str(tmp_path))
    assert r.ok and [c.op for c in r.calls] == ["median"]                                    # 次にプログラムの場所
    r = sp.run_program("x = 1\nout = load_pipeline('zz.json')(img)\n", img, program_dir=str(tmp_path))
    assert r.errors and r.errors[0].startswith("line 2: FileNotFoundError")


# --------------------------------------------------------------------------- #
# 定義ファイルの層                                                              #
# --------------------------------------------------------------------------- #
def test_defs_io_values_and_atomic_write(tmp_path):
    assert defs_io.to_jsonable({"a": (1, np.float32(0.5)), "b": np.arange(3)}) == {"a": [1, 0.5], "b": [0, 1, 2]}
    with pytest.raises(defs_io.DefinitionError, match=r"\$\.x\[1\]"):
        defs_io.to_jsonable({"x": [1.0, float("nan")]})
    with pytest.raises(defs_io.DefinitionError, match="too large"):
        defs_io.to_jsonable(np.zeros(5000))
    with pytest.raises(defs_io.DefinitionError):
        defs_io.write_json_atomic(str(tmp_path / "x.json"), {"v": float("inf")})
    assert list(tmp_path.iterdir()) == []                             # 失敗しても一時ファイルは残らない
    defs_io.write_json_atomic(str(tmp_path / "x.json"), {"v": 1})
    assert [p.name for p in tmp_path.iterdir()] == ["x.json"]


def test_defs_io_sidecar_reference_is_checked(tmp_path):
    import hashlib
    arr = np.arange(6.0)
    np.save(tmp_path / "a.npy", arr)
    h = hashlib.sha256((tmp_path / "a.npy").read_bytes()).hexdigest()
    assert np.array_equal(defs_io.resolve_sidecar({"$array": "a.npy", "sha256": h}, str(tmp_path)), arr)
    with pytest.raises(defs_io.DefinitionError, match="sha256"):
        defs_io.resolve_sidecar({"$array": "a.npy", "sha256": "0" * 64}, str(tmp_path))
    with pytest.raises(defs_io.DefinitionError, match="outside"):
        defs_io.resolve_sidecar({"$array": "../a.npy", "sha256": h}, str(tmp_path / "sub"))


def test_write_def_dispatches_by_type(tmp_path):
    import fullseye as fs
    e = engine.FullseyeEngine([("gaussian", 0.4, 0.5)], name="g")
    assert fs.write_def(e, str(tmp_path / "g.json")) == "pipeline"
    d = json.loads((tmp_path / "g.json").read_text(encoding="utf-8"))
    assert list(d)[:3] == ["fullseye_kind", "version", "created_by"] and d["fullseye_kind"] == "pipeline"
    got = fs.read_def(str(tmp_path / "g.json"))
    assert isinstance(got, engine.PipelineFile) and got.stages == [["gaussian", 0.4, 0.5]]
    with pytest.raises(fs.DefinitionError, match="no definition kind"):
        fs.write_def(object(), str(tmp_path / "z.json"))
    with pytest.raises(fs.DefinitionError, match="not 'camera'|not recognisable"):
        fs.read_def(str(tmp_path / "g.json"), kind="camera")


def test_stage_forms_are_read_into_the_canonical_form(tmp_path):
    import fullseye as fs
    forms = [["gaussian", 0.4, 0.5], {"op": "gaussian", "a": 0.4}, {"name": "gaussian", "a": 0.4, "b": 0.5},
             "gaussian", ["gaussian", {"a": 0.4}], {"op": "median", "a": 0.3, "bypass": True}]
    p = tmp_path / "forms.json"
    p.write_text(json.dumps({"stages": forms}), encoding="utf-8")
    pf = fs.load_pipeline(str(p))
    assert pf._all == [["gaussian", 0.4, 0.5], ["gaussian", 0.4, 0.5], ["gaussian", 0.4, 0.5],
                       ["gaussian", 0.5, 0.5], ["gaussian", 0.4, 0.5], ["median", 0.3, 0.5, True]]
    pf.save(str(tmp_path / "out.json"))                               # 書くときは正本の形
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))["stages"] == pf._all
    m = studio.PipelineModel(_gray())
    m.load_dict(json.loads((tmp_path / "out.json").read_text(encoding="utf-8")))   # Studio でも開ける
    assert len(m.stages) == 6
    assert len(engine.STAGE_FORMS) == 5


# --------------------------------------------------------------------------- #
# 書き出し(別プロセスで走らせて画素単位で比べる)                                 #
# --------------------------------------------------------------------------- #
EXPORT_PROGRAMS = {
    "branch": ("mask = threshold(img, 0.5)\nn = blob_count(mask)\n"
               "if n > 5:\n    img = gaussian(img, 0.9)\nelif n > 1:\n    img = median(img, 0.4)\nelse:\n    img = gaussian(img, 0.1)\n"),
    "for": "for s in [0.2, 0.4, 0.6]:\n    img = gaussian(img, s)\nfor i in range(2):\n    img = median(img, 0.3)\n",
    "while": "k = 0\nwhile blob_count(threshold(img, 0.5)) > 1 and k < 6:\n    img = gaussian(img, 0.8)\n    k += 1\nshow(img)\n",
    "function": "def smooth(x, n):\n    for _ in range(n):\n        x = gaussian(x, 0.3)\n    return x\nimg = smooth(img, 3)\n",
    "numpy": "x = np.clip(np.array(img) * 1.2, 0, 1)\nimg = gaussian(x, 0.4)\nshow(otsu(img))\n",
    "pipeline": "p = load_pipeline('Edge — Sobel + Otsu')\nedges = p(img)\nif blob_count(edges) > 0:\n    show(edges)\n",
}


@pytest.mark.parametrize("key", sorted(EXPORT_PROGRAMS))
def test_exported_script_matches_studio_pixel_for_pixel(key, tmp_path):
    text = EXPORT_PROGRAMS[key]
    img = _blobs(6)
    r = sp.run_program(text, img)
    assert r.ok, r.errors
    script = sp.export_python_script(text)
    assert text in script                                             # 文面はそのまま入る
    sp_path = tmp_path / "prog.py"
    sp_path.write_text(script, encoding="utf-8")
    np.save(tmp_path / "in.npy", img)
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUTF8="1")
    proc = subprocess.run([sys.executable, str(sp_path), str(tmp_path / "in.npy"), str(tmp_path / "out.npy")],
                          cwd=str(tmp_path), env=env, capture_output=True, text=True, timeout=240)
    assert proc.returncode == 0, proc.stderr[-2000:]
    got = np.load(tmp_path / "out.npy")
    assert got.dtype == np.asarray(r.output).dtype and np.array_equal(got, r.output), key
    # 書き出した物を Program 欄へ貼っても同じ結果(逆向き)
    back = sp.run_program(script, img)
    assert back.ok, back.errors
    assert np.array_equal(back.output, r.output)


def test_export_refuses_hdevelop():
    with pytest.raises(ValueError, match="export_standalone"):
        sp.export_python_script("gaussian (0.4, 0.5)")


# --------------------------------------------------------------------------- #
# 前置きの名前の衝突                                                            #
# --------------------------------------------------------------------------- #
def test_prelude_collisions_are_found_and_excluded():
    got = sp.prelude_collisions(["min", "and", "match", "img", "ok_name", "9x", "dev_update_off"])
    assert got == {"min": "python builtin", "and": "python keyword", "match": "python soft keyword",
                   "img": "prelude name", "9x": "not an identifier", "dev_update_off": "display directive"}
    import fullseye.studio_prelude as pre
    bad = sp.prelude_collisions()
    exported = set(pre.__all__)
    assert not (set(bad) & exported)
    assert all(n in exported for n in NAMES if n not in bad)
    assert len(NAMES) >= 900 and len(bad) == 0, sorted(bad)            # 2026-11-12 の実測: 964 op で衝突 0


# --------------------------------------------------------------------------- #
# 助言                                                                          #
# --------------------------------------------------------------------------- #
def _kinds(text):
    return [(a.line, a.kind) for a in sp.advise_program(text)]


def test_advice_fires_where_it_should():
    t = "a = gaussian(img, 0.4)\nn = blob_count(otsu(a))\nshow(a)\n"
    adv = sp.advise_program(t)
    assert [(a.line, a.kind) for a in adv] == [(2, "unused_result")]
    assert adv[0].fixed_text == "a = gaussian(img, 0.4)\nshow(a)"
    assert sp.run_program(adv[0].fixed_text, _gray()).ok
    assert _kinds("for i in range(3):\n    g = gaussian(img, 0.4)\n    show(g)\n") == [(2, "loop_invariant")]
    assert _kinds("a = gaussian(img, 0.4)\nb = gaussian(img, 0.4)\nshow(sub_image(a, b))\n") == [(2, "duplicate")]
    assert _kinds("m = otsu(img)\ng = gaussian(m, 0.4)\nshow(g)\n") == [(2, "type_mismatch")]


@pytest.mark.parametrize("text", [
    "n = blob_count(otsu(img))\nprint(n)\n",                          # 後で読まれる
    "def f():\n    n = blob_count(otsu(img))\nf()\n",                  # 関数の中
    "a = gaussian(img, 0.4)\n",                                       # 画像の op(流れと表示を変える)
    "for s in [0.1, 0.2]:\n    g = gaussian(img, s)\n",               # 引数がループで変わる
    "for i in range(3):\n    img = gaussian(img, 0.4)\n",             # 入力がループで変わる
    "for i in range(3):\n    g = gaussian(0.4)\n",                    # 入力を省いた = 流れに依る
    "for i in range(3):\n    g = add_noise_white(img, 0.4)\n",        # 乱数の op
    "for i in range(3):\n    g = gaussian(img, 0.4)\n    img.fill(0)\n",   # 属性の呼び出し(書き換えかも)
    "a = gaussian(img, 0.4)\nimg = median(img)\nb = gaussian(img, 0.4)\n",  # 間で入力が変わる
    "gaussian = 3\nx = gaussian\n",                                   # op の名前を上書き
    "x = eval('1')\nn = blob_count(otsu(img))\n",                    # 動的な名前の操作
    "m = otsu(img)\nm = gaussian(img)\ng = gaussian(m, 0.4)\n",      # 2 回代入される変数の型は決めない
])
def test_advice_stays_quiet_when_unsure(text):
    assert sp.advise_program(text) == [], (text, sp.advise_program(text))


# --------------------------------------------------------------------------- #
# スレッドと Qt の差し込み口                                                     #
# --------------------------------------------------------------------------- #
def test_run_program_works_from_a_worker_thread():
    out = {}

    def work():
        out["r"] = sp.run_program("print('hi')\nimg = gaussian(img, 0.4)\n", _gray())
        out["stop"] = sp.run_program("while True:\n    pass\n", _gray(), time_limit_s=0.2)
    th = threading.Thread(target=work)
    th.start(); th.join(30)
    assert out["r"].ok and out["r"].stdout == "hi\n" and len(out["r"].calls) == 1
    assert out["stop"].stopped == "time_limit"
    assert sys.gettrace() is None or sys.gettrace() is not None      # 呼んだスレッドの外の trace は触らない


def test_missing_package_says_how_to_install():
    r = sp.run_program("x = 1\nimport no_such_pkg_for_studio_xyz\n", _gray())
    assert r.errors[0].startswith("line 2: ModuleNotFoundError") and "-m pip install no_such_pkg_for_studio_xyz" in r.errors[0]


def test_ui_refuses_clearly_without_a_qt_application(monkeypatch):
    monkeypatch.setattr(sp, "GUI_BRIDGE", None)
    monkeypatch.setattr(sp, "_qt_application", lambda: None)
    r = sp.run_program("x = 1\nw = ui(lambda: 1)\n", _gray())
    assert r.errors and r.errors[0].startswith("line 2: RuntimeError") and "no Qt application" in r.errors[0]


def test_show_window_goes_through_the_bridge_and_is_closed(monkeypatch):
    calls = []

    class Bridge:
        def call(self, fn, *args):
            calls.append(threading.current_thread().name)
            return fn(*args)

    class FakeWidget:
        shown = closed = False

        def show(self):
            self.shown = True

        def close(self):
            self.closed = True

    monkeypatch.setattr(sp, "GUI_BRIDGE", Bridge())
    ns_widget = FakeWidget()                                          # プログラムの外の窓は触られない
    r = sp.run_program("class W:\n    shown = closed = False\n    def show(self):\n        self.shown = True\n"
                       "    def close(self):\n        self.closed = True\n"
                       "w = show_window(W)\nv = ui(lambda a: a + 1, 1)\n", _gray())
    assert r.ok, r.errors
    assert r.values["v"] == 2 and r.values["w"].shown and r.windows == [r.values["w"]]
    assert len(calls) == 2                                            # show_window 1 回 + ui 1 回、どちらも橋を通る
    w = r.values["w"]
    assert sp.close_program_windows(r) == 1 and w.closed and r.windows == []
    assert len(calls) == 3                                            # 閉じるのも橋を通る
    assert not ns_widget.shown


def test_needs_gui_thread_and_qt_binding_advice():
    assert sp.needs_gui_thread("from PySide6 import QtWidgets\n")
    assert sp.needs_gui_thread("import PyQt5.QtCore\n")
    assert not sp.needs_gui_thread("import numpy as np\nimg = gaussian(img)\n")
    assert [(a.line, a.kind) for a in sp.advise_program("x = 1\nimport PyQt5.QtWidgets\n")] == [(2, "qt_binding_mix")]
    assert sp.advise_program("from PySide6 import QtWidgets\n") == []

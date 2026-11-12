# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Program の実行を必ず止められること(Debug / Release × 4 種の止まりにくいプログラム)と、実行の後に
プロセス全体の状態(sys.path・os.environ・cwd・builtins)が戻ること。

試験そのものが固まらないよう、止める試験は子プロセスで回し、外側に時間切れを付ける。呼び出し側(子プロセスの
run_program)は「時間の上限 + 2 秒」以内に必ず戻ること。止められない物(C の中の長い呼び出し)は
``stopped == "unstoppable"`` と、そう言う文が結果に入ること。"""
from __future__ import annotations

import builtins
import json
import os
import pathlib
import subprocess
import sys
import textwrap

import numpy as np
import pytest

import studio_program as sp

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIMIT = 0.5

PROGRAMS = {
    "busy_loop": "while True:\n    pass\n",
    "swallowing_loop": "while True:\n    try:\n        pass\n    except BaseException:\n        pass\n",
    "sleep": "import time\ntime.sleep(60)\n",
    "heavy_numpy": "import numpy as np\na = np.random.default_rng(0).random((2500, 2500))\nu = np.linalg.svd(a)\n",
}

CHILD = textwrap.dedent('''
    import json, os, sys, time
    sys.path.insert(0, {root!r})
    import numpy as np
    import studio_program as sp
    text, config, limit = {text!r}, {config!r}, {limit!r}
    sp.run_program("x = gaussian(img, 0.1)", np.zeros((16, 16)))   # 初回の準備(op の表・前置き)を時間に入れない
    t0 = time.perf_counter()
    r = sp.run_program(text, np.zeros((16, 16)), time_limit_s=limit, config=config)
    dt = time.perf_counter() - t0
    print(json.dumps({{"dt": dt, "stopped": r.stopped, "errors": r.errors, "abandoned": len(sp.abandoned_runs())}}))
    sys.stdout.flush()
    os._exit(0)                                   # 残したスレッドを待たない
''')


@pytest.mark.parametrize("config", ["debug", "release"])
@pytest.mark.parametrize("key", sorted(PROGRAMS))
def test_the_caller_always_gets_control_back(key, config, tmp_path):
    script = tmp_path / "child.py"
    script.write_text(CHILD.format(root=str(ROOT), text=PROGRAMS[key], config=config, limit=LIMIT), encoding="utf-8")
    proc = subprocess.run([sys.executable, "-u", str(script)], capture_output=True, text=True, timeout=120,
                          env=dict(os.environ, PYTHONUTF8="1"))
    assert proc.returncode == 0, proc.stderr[-1500:]
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["dt"] < LIMIT + 2.0, out                               # 呼び出し側は必ず戻る
    if key in ("busy_loop", "swallowing_loop"):
        assert out["stopped"] == "time_limit", out                    # 素の Python のループは止まる
        assert out["errors"][0].startswith("line ") and "time limit" in out["errors"][0]
    else:                                                             # C の中の長い呼び出しは止められない
        assert out["stopped"] in ("unstoppable", "time_limit"), out
        if out["stopped"] == "unstoppable":
            assert "could not stop the program" in out["errors"][0] and out["abandoned"] == 1


def test_stop_request_in_release_stops_a_busy_loop():
    import threading
    ev = threading.Event()
    threading.Timer(0.2, ev.set).start()
    r = sp.run_program("k = 0\nwhile True:\n    k += 1\n", np.zeros((8, 8)), config="release", time_limit_s=None,
                       stop_event=ev)
    assert r.stopped == "stop_requested" and r.errors[0].endswith("stopped on request") and r.stopped_line in (2, 3)


def test_untrusted_says_why_it_did_not_run():
    r = sp.run_program("x = 1\n", np.zeros((8, 8)), trusted=False)
    assert not r.ran and r.errors and r.errors[0].startswith("not run:") and r.errors == [r.not_run_reason]


def test_process_state_is_restored_after_the_run(tmp_path):
    before = (list(sys.path), dict(os.environ), os.getcwd(), dict(vars(builtins)))
    prog = ("import sys, os, builtins\n"
            "sys.path.insert(0, 'ZZZ_PATH')\n"
            "os.environ['ZZ_STUDIO_LEAK'] = '1'\n"
            "os.chdir(%r)\n"
            "builtins.ZZ_STUDIO_LEAK = 1\n"
            "import warnings\nwarnings.simplefilter('ignore')\n") % str(tmp_path)
    r = sp.run_program(prog, np.zeros((8, 8)))
    assert r.ok, r.errors
    assert sys.path == before[0] and dict(os.environ) == before[1] and os.getcwd() == before[2]
    assert not hasattr(builtins, "ZZ_STUDIO_LEAK") and dict(vars(builtins)).keys() == before[3].keys()
    assert any(n.startswith("restored after the run: sys.path, os.environ, cwd, builtins") for n in r.notes), r.notes


def test_exit_recursion_and_writes_are_reported():
    z = np.zeros((8, 8))
    r = sp.run_program("import sys\nsys.exit(3)\n", z)
    assert r.errors == ["line 2: the program called exit(3)"]
    r = sp.run_program("def f(n):\n    return f(n + 1)\nf(0)\n", z)
    assert r.errors and "RecursionError" in r.errors[0] and r.errors[0].startswith("line ")
    r = sp.run_program("img[0, 0] = 5\n", z)
    assert r.errors and "read-only" in r.errors[0] and z[0, 0] == 0
    r = sp.run_program("g = gaussian(img, 0.3)\ng[0, 0] = 9\n", z)
    assert r.errors and r.errors[0].startswith("line 2:") and "read-only" in r.errors[0]

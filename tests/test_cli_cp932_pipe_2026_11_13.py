# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""日本語 Windows で出力をパイプやファイルへ回すと ``fullseye`` が落ちた(2026-11-13、配布物の検証 M3)。

標準出力が cp932(strict)になり、help の「—」などで ``UnicodeEncodeError``(rc=1)。``fullseye --help > h.txt``・
``fullseye has <無い名前>``・``fullseye samples list``。本物の端末では落ちない(Windows のコンソールは UTF-8)。
ここでは ``PYTHONIOENCODING=cp932`` と subprocess のパイプで同じ状態を作る(Linux の CI でも再現する)。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run_cp932(*args):
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING", "PYTHONPATH")}
    env.update(PYTHONIOENCODING="cp932", PYTHONUTF8="0", PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, "-m", "fullseye", *args], cwd=str(ROOT), stdin=subprocess.DEVNULL,
                          capture_output=True, timeout=600, env=env)


@pytest.mark.parametrize("args, rc, expect", [
    (("--help",), 0, "usage:"),
    (("has", "no_such_op_2026_11_13"), 1, "no_such_op_2026_11_13"),
    (("samples", "list"), 0, "http"),
])
def test_output_into_a_cp932_pipe_does_not_crash(args, rc, expect):
    p = _run_cp932(*args)
    out = p.stdout.decode("cp932")               # 書けた物は cp932 として読める(壊れた列になっていない)
    err = p.stderr.decode("cp932", "replace")
    assert "UnicodeEncodeError" not in err and "Traceback" not in err, err[-800:]
    assert p.returncode == rc, (p.returncode, err[-800:])
    assert expect in out, out[:800]


def test_help_in_a_cp932_pipe_replaces_only_the_characters_cp932_cannot_hold():
    p = _run_cp932("--help")
    out = p.stdout.decode("cp932")
    assert p.returncode == 0, p.stderr[-800:]
    # 「fullseye — single CLI」の — は cp932 に無い -> ? に置き換わる(他の字はそのまま)
    assert "fullseye ? single CLI" in out, out[:400]

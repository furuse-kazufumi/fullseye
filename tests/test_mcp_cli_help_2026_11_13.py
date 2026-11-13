# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``python -m fullseye.mcp --help`` が help を出さずに入力待ちで止まった(2026-11-13、配布物の検証 M7)。

サーバの main は ``--coverage`` / ``--demo`` しか見ず、ほかの引数は全部無視して stdio サーバとして起動していた。
端末で打つと黙って止まる。``-h`` / ``--help`` は使い方を出して 0、知らない引数は使い方と理由を出して非 0。
stdin は閉じて渡す(直す前の版は EOF で黙って 0 で終わる = 使い方が無いので落ちる)。時間の上限つき。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run(*args):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=str(ROOT))
    return subprocess.run([sys.executable, "-m", "fullseye.mcp", *args], cwd=str(ROOT), stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, env=env)


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_the_usage_and_exits_0_without_starting_the_server(flag):
    p = _run(flag)
    assert p.returncode == 0, p.stderr[-800:]
    assert "usage: python -m fullseye.mcp" in p.stdout, p.stdout[:800]
    assert "--demo" in p.stdout and "--coverage" in p.stdout and "claude mcp add fullseye" in p.stdout
    assert "ready:" not in p.stderr, p.stderr[-800:]          # サーバの起動の行(stderr)が無い = 起動していない
    assert "jsonrpc" not in p.stdout


def test_an_unknown_argument_prints_the_usage_and_exits_non_zero():
    p = _run("--no-such-flag")
    assert p.returncode == 2, (p.returncode, p.stderr[-800:])
    assert "usage: python -m fullseye.mcp" in p.stderr and "--no-such-flag" in p.stderr, p.stderr[-800:]
    assert p.stdout == "", p.stdout[:400]
    assert "ready:" not in p.stderr

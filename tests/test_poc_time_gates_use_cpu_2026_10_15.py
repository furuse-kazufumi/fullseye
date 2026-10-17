# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC の所要時間の門は壁時計でなくプロセスの CPU 時間で測る —— 2026-10-15 の回帰テスト。

poc_phase_measuring_deflectometry の門「所要時間 < 120 秒」が、CI の並列のシャード(py3.12 3/4)で壁時計 120.6 秒
(手元 23 秒)になり赤になった。壁時計は同じ機械で走る他のテストの負荷まで数える。同じ形の門が examples/ に
15 本(17 門)あった。門が抑えたいのは PoC 自身の計算量なので ``time.process_time`` で測り、壁時計は併記する。

この検査は examples/*.py を AST で読み、門の関数(``gate`` / ``check`` など)の条件が ``<`` / ``<=`` で、
左辺が壁時計(``time.time`` / ``perf_counter`` / ``monotonic``)の差から作った名前か、その呼び出しそのもので
あるものを数える。0 本であること。範囲が黙って縮まないよう、読んだファイルの数に下限を置く。
"""
from __future__ import annotations

import ast
import glob
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WALL = {"time", "perf_counter", "monotonic"}
_GATES = {"check", "gate", "_gate", "ok", "expect"}


def _is_wall_call(n) -> bool:
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _WALL
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "time")


def _wallish(expr, names) -> bool:
    return any(_is_wall_call(n) or (isinstance(n, ast.Name) and n.id in names) for n in ast.walk(expr))


def wall_clock_gates(path: str) -> list:
    """``path`` の中で、壁時計の差を ``<`` / ``<=`` で判定している門の (行, 条件) の一覧。"""
    tree = ast.parse(open(path, encoding="utf-8").read())
    names: set = set()
    for _ in range(3):                                  # t = time.time() - t0; el = t (2 段まで追う)
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.BinOp) and _wallish(n.value, names):
                names.update(t.id for t in n.targets if isinstance(t, ast.Name))
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _GATES:
            for a in n.args:
                if (isinstance(a, ast.Compare) and any(isinstance(o, (ast.Lt, ast.LtE)) for o in a.ops)
                        and _wallish(a.left, names)):
                    out.append((n.lineno, ast.unparse(a)))
    return out


def test_the_probe_catches_the_wall_clock_form(tmp_path):
    # 探針そのものを確かめる(探針が壊れて 0 を返すと門は素通りになる)
    src = ("import time\nt0 = time.time()\nelapsed = time.time() - t0\n"
           "check(elapsed < 60.0, 'x', '')\nc0 = time.process_time()\ncpu = time.process_time() - c0\n"
           "check(cpu < 60.0, 'y', '')\n")
    p = tmp_path / "probe.py"
    p.write_text(src, encoding="utf-8")
    hits = wall_clock_gates(str(p))
    assert [h[1] for h in hits] == ["elapsed < 60.0"]


def test_no_poc_gates_its_own_run_time_on_the_wall_clock():
    files = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.py")))
    assert len(files) >= 300, "examples/ が %d 本しか読めない —— 範囲が縮んでいる" % len(files)
    bad = ["%s:%d  %s" % (os.path.basename(f), ln, cond) for f in files for ln, cond in wall_clock_gates(f)]
    assert not bad, "壁時計で自分の所要時間を判定している門(time.process_time に替え、壁時計は併記する):\n" + "\n".join(bad)

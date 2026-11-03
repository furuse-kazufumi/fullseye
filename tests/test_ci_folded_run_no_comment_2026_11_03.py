"""CI の `run: >`(折り畳みスカラー)の中にコメント行を書かないこと、と nightly の件数の門。

2026-11-02〜03: nightly の order-shuffle の ``Install`` 段で、``run: >`` の中に書いた ``# xlsx も入れる…``
の 2 行が折り畳みで ``pip install ...`` と 1 行に連結され、行全体がシェルのコメントになった。
何も入らず、次の段が ``pytest: command not found``(exit 127)。job の ``continue-on-error: true`` で
run は緑のままだった(run 41431579929 のログで確認)。2026-10-22 にも同じ型で ``--store-durations`` が
消えている。ここで 3 度目を止める。

門:
1. 全 workflow の ``run: >`` / ``>-`` / ``>+`` ブロックに ``#`` で始まる行が無い(折り畳むと後ろが消える)。
2. YAML として読んだ ``run`` の本文で、1 行目が ``#`` で始まり、かつ同じ行に ``pip`` / ``pytest`` / ``python``
   が続くもの(= 連結されて消えたコマンド)が無い。1 と別の読み方で同じ事故を見る。
3. order-shuffle の件数の門(``order-shuffle-ran``)が在り、continue-on-error が付いていない。
4. ``tools/ci_junit_floor.py`` が 0 件・床未満・ファイル無しを赤にする。
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")
FLOOR = os.path.join(ROOT, "tools", "ci_junit_floor.py")


def _workflows():
    names = sorted(n for n in os.listdir(WF) if n.endswith((".yml", ".yaml")))
    assert len(names) >= 2, names  # 読み方が壊れて 0 本で通るのを防ぐ
    return names


def _folded_blocks(text):
    """``run: >`` ブロックごとに (開始行番号, [本文の行]) を返す。"""
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        m = re.match(r"^(\s*)(?:-\s+)?run:\s*>[-+]?\s*(#.*)?$", ln)
        if not m:
            continue
        ind = len(ln) - len(ln.lstrip())
        body = []
        j = i + 1
        while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > ind):
            body.append(lines[j])
            j += 1
        yield i + 1, body


def test_no_comment_line_inside_folded_run_blocks():
    n_blocks = 0
    bad = []
    for name in _workflows():
        with open(os.path.join(WF, name), encoding="utf-8") as f:
            text = f.read().replace("\r\n", "\n")
        for lineno, body in _folded_blocks(text):
            n_blocks += 1
            for k, b in enumerate(body):
                if b.lstrip().startswith("#"):
                    bad.append("%s:%d: %s" % (name, lineno + 1 + k, b.strip()[:60]))
    # ci.yml には少なくとも Install 段と full suite の pytest 段の 2 本以上がある。
    assert n_blocks >= 3, "run: > が %d 本しか見つからない(読み方が壊れていないか)" % n_blocks
    assert not bad, "run: > の中のコメント行(折り畳むと後ろのコマンドが消える):\n" + "\n".join(bad)


def test_no_parsed_run_starts_with_a_comment_that_swallows_a_command():
    yaml = pytest.importorskip("yaml")
    n_runs = 0
    bad = []
    for name in _workflows():
        with open(os.path.join(WF, name), encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        for job, jd in (doc.get("jobs") or {}).items():
            for st in jd.get("steps") or []:
                run = st.get("run")
                if not run:
                    continue
                n_runs += 1
                for line in run.split("\n"):
                    s = line.strip()
                    if s.startswith("#") and re.search(r"\b(pip|pytest|python3?)\s", s):
                        bad.append("%s / %s / %s: %s" % (name, job, st.get("name"), s[:80]))
    assert n_runs >= 20, n_runs
    assert not bad, "コメント行の中にコマンドが入っている(連結で消えた疑い):\n" + "\n".join(bad)


def test_order_shuffle_has_a_red_gate_for_zero_tests():
    yaml = pytest.importorskip("yaml")
    with open(os.path.join(WF, "ci.yml"), encoding="utf-8") as f:
        jobs = yaml.safe_load(f)["jobs"]
    shuffle = jobs["order-shuffle"]
    gate = jobs["order-shuffle-ran"]
    assert gate["needs"] == "order-shuffle"
    assert "always()" in gate["if"]
    assert not gate.get("continue-on-error"), "件数の門に continue-on-error を付けると門にならない"
    runs = [s.get("run", "") for s in shuffle["steps"]]
    assert sum("--junitxml=shuffle-" in r for r in runs) == 2, runs
    gate_runs = " ".join(s.get("run", "") for s in gate["steps"])
    m = re.search(r"ci_junit_floor\.py\s+(.*?)--min-executed\s+(\d+)", gate_runs)
    assert m, gate_runs
    assert "shuffle-serial.xml" in m.group(1) and "shuffle-parallel.xml" in m.group(1)
    assert int(m.group(2)) >= 1000, "床が低すぎる(数件走っただけで通ってしまう)"


def _junit(tmp_path, name, tests, skipped, failures=0, errors=0):
    p = tmp_path / name
    p.write_text(
        '<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" '
        'tests="%d" skipped="%d" failures="%d" errors="%d"></testsuite></testsuites>'
        % (tests, skipped, failures, errors), encoding="utf-8")
    return str(p)


def _run_floor(*args):
    return subprocess.run([sys.executable, FLOOR, *args], capture_output=True, text=True,
                          encoding="utf-8", timeout=60)


def test_floor_tool_passes_enough_executed_and_counts_failures_as_executed(tmp_path):
    a = _junit(tmp_path, "a.xml", tests=120, skipped=20, failures=7)
    r = _run_floor(a, "--min-executed", "100")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "executed=100" in r.stdout


@pytest.mark.parametrize("tests,skipped", [(0, 0), (50, 50), (99, 0)])
def test_floor_tool_is_red_on_zero_all_skipped_or_below_floor(tmp_path, tests, skipped):
    a = _junit(tmp_path, "a.xml", tests=tests, skipped=skipped)
    r = _run_floor(a, "--min-executed", "100")
    assert r.returncode == 1, r.stdout
    assert "RED" in r.stdout


def test_floor_tool_is_red_on_missing_or_broken_file(tmp_path):
    good = _junit(tmp_path, "good.xml", tests=500, skipped=0)
    broken = tmp_path / "broken.xml"
    broken.write_text("<testsuites><testsuite", encoding="utf-8")
    r = _run_floor(good, str(tmp_path / "missing.xml"), str(broken), "--min-executed", "10")
    assert r.returncode == 1
    assert r.stdout.count("RED") == 2, r.stdout


def test_floor_tool_refuses_a_zero_floor(tmp_path):
    a = _junit(tmp_path, "a.xml", tests=0, skipped=0)
    r = _run_floor(a, "--min-executed", "0")
    assert r.returncode == 2  # argparse の error

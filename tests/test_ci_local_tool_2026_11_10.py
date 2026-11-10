# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tools/ci_local.py(手元の Linux で CI 相当を回す道具)そのものの門。WSL は起動しない。

2026-11-10 の敵対的レビューが実行で確かめた入力を、そのままテストにしてある:

* ``--only ruff --skip ruff``・全段 ``--skip`` が**何も走らせずに終了コード 0** だった
* 部分実行の要約の題が「手元の全数」のままだった
* 壊れた JUnit で要約が書けず、0 件の JUnit が成功に見えた
* 状態ディレクトリに排他が無く、目印の無い既存のディレクトリで ``clean -fdx`` を走らせた
* 門の一覧の内蔵の写し・ci.yml から手で写した依存の定義が、黙ってずれうる
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("ci_local_tool_t", ROOT / "tools" / "ci_local.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cl = _load()

SHA = "a" * 40
BASE = "b" * 40
MERGED = "c" * 40


def _job(**over) -> dict:
    job = {"sha": SHA, "ref": "HEAD", "subject": "subject line", "branch": "feat/x", "target": "HEAD(feat/x)",
           "dirty_count": 0, "dirty_applies": True, "notes": [], "selected": list(cl.PHASE_KEYS), "only": None,
           "skip": [], "pytest_args": [], "pip_audit": True, "cov": False, "workers": 2, "dist": "worksteal",
           "tree": {"sha": SHA, "base_ref": "origin/master", "base_sha": BASE, "fetched": "yes", "behind": 3,
                    "ahead": 2, "mode": "merge", "tested": MERGED}}
    job.update(over)
    return job


def _state(job: dict, results: dict, **over) -> dict:
    st = {"job": job, "tree": job["tree"], "results": cl.fill_not_run(results, job, over.get("stopped_at"), None),
          "total": 12.0, "tools_probed": True, "tools_missing": [], "apt_missing": []}
    st.update(over)
    return st


def _ok(detail: str = "ok") -> dict:
    return {"state": "ok", "detail": detail, "sec": 1.0}


# ---- 門の一覧 --------------------------------------------------------------------------------

def test_builtin_gates_are_ten_distinct_existing_files():
    gates = cl.BUILTIN_GATES
    assert len(gates) == 10
    assert len(set(gates)) == 10
    missing = [g for g in gates if not (ROOT / g).is_file()]
    assert missing == []


def test_builtin_gates_match_the_list_file_where_it_exists():
    listed = ROOT / cl.GATES_FILE
    if not listed.exists():
        pytest.skip(f"{cl.GATES_FILE} はまだこの木に無い(CI を速くする便が入ったら、内蔵の写しと一致を見る)")
    names = cl.parse_gate_list(listed.read_text(encoding="utf-8"))
    assert len(names) >= 10
    assert sorted(names) == sorted(cl.BUILTIN_GATES)


def test_parse_gate_list_drops_comments_and_blank_lines():
    text = "# 門\n\ntests/test_a.py\n  tests/test_b.py  # 理由\n#tests/test_c.py\n\n"
    assert cl.parse_gate_list(text) == ["tests/test_a.py", "tests/test_b.py"]


# ---- 1 段も走らない組み合わせ ----------------------------------------------------------------

NOTHING_RUNS = [
    ["--only", "ruff", "--skip", "ruff"],
    ["--only", "lint", "--skip", "ruff"],
    ["--only", "tests", "--skip", "tests"],
    ["--skip", "ruff", "--skip", "regen", "--skip", "gates", "--skip", "core", "--skip", "tests"],
]


@pytest.mark.parametrize("argv", NOTHING_RUNS, ids=["only-skip-ruff", "only-lint-skip-alias", "only-skip-tests",
                                                    "skip-all-five"])
def test_no_phase_selected_exits_nonzero_without_launching_anything(argv, tmp_path, monkeypatch):
    calls = []

    def _refuse(*a, **k):
        calls.append(a)
        raise AssertionError("1 段も走らない組み合わせで外部プロセスを起動した")

    monkeypatch.setattr(cl.subprocess, "run", _refuse)
    monkeypatch.setattr(cl.subprocess, "call", _refuse)
    args = cl.build_parser().parse_args(argv)
    assert cl.select_phases(args.only, args.skip) == []
    rc = cl.main([*argv, "--out", str(tmp_path / "out")])
    assert rc == cl.EXIT_USAGE == 2
    assert calls == []
    assert not (tmp_path / "out").exists()


def test_select_phases_keeps_the_order_and_resolves_the_alias():
    assert cl.select_phases(None, []) == ["lint", "regen", "gates", "core", "tests"]
    assert cl.select_phases("ruff", []) == ["lint"]
    assert cl.select_phases(None, ["tests", "ruff"]) == ["regen", "gates", "core"]


def test_abbreviated_options_are_rejected():
    with pytest.raises(SystemExit) as exc:
        cl.build_parser().parse_args(["--on", "lint"])
    assert exc.value.code == 2


def test_exit_code_is_nonzero_unless_something_ran_and_all_of_it_passed():
    job = _job()
    nothing = _state(job, {})
    assert [nothing["results"][k]["state"] for k in cl.PHASE_KEYS] == ["not_run"] * 5
    assert cl.exit_code(nothing) == cl.EXIT_FAILED == 1
    one_ok = _state(_job(only="lint", selected=["lint"]), {"lint": _ok()})
    assert cl.exit_code(one_ok) == cl.EXIT_OK == 0
    one_bad = _state(job, {"lint": _ok(), "regen": {"state": "failed", "detail": "失敗", "sec": 2.0}})
    assert cl.exit_code(one_bad) == 1
    crashed = _state(job, {"lint": _ok()}, crash="RuntimeError: x")
    assert cl.exit_code(crashed) == 1
    busy = _state(job, {}, busy=True, crash="別の ci_local が使っている")
    assert cl.exit_code(busy) == cl.EXIT_BUSY == 3


# ---- 要約 ------------------------------------------------------------------------------------

PARTIAL_JOBS = [
    ("only", {"only": "lint", "selected": ["lint"]}, "--only lint"),
    ("skip", {"skip": ["tests"], "selected": ["lint", "regen", "gates", "core"]}, "--skip tests"),
    ("pytest-args", {"pytest_args": ["-k", "smoke"]}, "pytest への追加引数 `-k smoke`"),
    ("no-pip-audit", {"pip_audit": False}, "--no-pip-audit"),
]


@pytest.mark.parametrize("over,reason", [(o, r) for _, o, r in PARTIAL_JOBS], ids=[n for n, _, _ in PARTIAL_JOBS])
def test_partial_run_summary_says_it_is_not_the_full_suite(over, reason):
    job = _job(**over)
    results = {k: _ok() for k in job["selected"]}
    text = cl.render_summary(_state(job, results))
    title, conclusion = text.splitlines()[0], text.splitlines()[2]
    assert title.endswith("部分実行(全数ではない)")
    assert conclusion.startswith("- 結論: **部分実行(全数ではない)**")
    assert reason in conclusion
    assert "この結果を全数の証拠にしない" in conclusion
    rows = [ln for ln in text.splitlines() if ln.startswith("| ")]
    labels = [cl.PHASE_LABEL[k] for k in cl.PHASE_KEYS]
    assert [r.split(" | ")[0][2:] for r in rows[1:6]] == labels
    not_run = len(cl.PHASE_KEYS) - len(job["selected"])
    assert sum("未実行" in r for r in rows[1:6]) == not_run


def test_full_run_summary_is_not_marked_partial_and_names_both_shas():
    job = _job()
    text = cl.render_summary(_state(job, {k: _ok() for k in cl.PHASE_KEYS}))
    assert "全数ではない" not in text
    assert "- 結論: **全段 ok**(5 段)" in text
    assert SHA[:12] in text and BASE[:12] in text and MERGED[:12] in text
    assert "未実行" not in text


def test_stopped_run_keeps_the_later_phases_in_the_table_as_not_run():
    job = _job()
    results = {"lint": _ok(), "regen": {"state": "failed", "detail": "失敗(exit 1、regen.log)", "sec": 3.0}}
    st = _state(job, results, stopped_at=cl.PHASE_LABEL["regen"])
    text = cl.render_summary(st)
    assert cl.exit_code(st) == 1
    assert "- 結論: **失敗**: regen_all --check" in text
    assert text.count("未実行(regen_all --check が落ちて止めた") == 3


def test_tree_line_states_what_was_tested_in_every_mode():
    seen = []
    for mode in ("merge", "ahead", "is_base", "behind", "tip"):
        line = cl.tree_line({"sha": SHA, "base_ref": "origin/master", "base_sha": BASE, "fetched": "yes",
                             "behind": 3, "ahead": 2, "mode": mode, "tested": MERGED})
        assert SHA[:12] in line and BASE[:12] in line, mode
        seen.append(line)
    assert len(set(seen)) == 5
    assert MERGED[:12] in seen[0] and "merge" in seen[0]
    assert "--no-merge" in seen[4] and "同じ木ではない" in seen[4]
    unfetched = cl.tree_line({"sha": SHA, "base_ref": "origin/master", "base_sha": BASE, "fetched": "no_fetch",
                              "behind": 0, "ahead": 1, "mode": "ahead", "tested": SHA})
    assert "**fetch していない**(--no-fetch" in unfetched
    by_sha = cl.tree_line({"sha": SHA, "base_ref": BASE, "base_sha": BASE, "fetched": "not_remote",
                           "behind": 0, "ahead": 1, "mode": "ahead", "tested": SHA})
    assert "形でないので fetch していない" in by_sha and "--no-fetch" not in by_sha


def test_tree_line_does_not_claim_a_merge_that_could_not_be_made():
    line = cl.tree_line({"sha": SHA, "base_ref": "origin/master", "base_sha": BASE, "fetched": "yes",
                         "behind": 4, "ahead": 1, "mode": "merge", "tested": None})
    assert line.startswith("- 検査した木: **無い**")
    assert "作れなかった" in line and "作った" not in line
    assert SHA[:12] in line and BASE[:12] in line


def test_busy_and_crashed_runs_say_why_nothing_ran():
    job = _job(only="lint", selected=["lint"])
    busy = cl.fill_not_run({}, job, None, "使用中", busy=True)
    assert busy["lint"]["detail"] == "未実行(状態ディレクトリが使用中)"
    assert busy["tests"]["detail"] == "未実行(--only lint)"
    crashed = cl.fill_not_run({}, job, None, "RuntimeError: merge が衝突した")
    assert crashed["lint"]["detail"] == "未実行(準備で止まった)"
    st = {"job": job, "tree": dict(job["tree"], tested=None), "results": crashed, "total": 1.0,
          "crash": "RuntimeError: merge が衝突した。**master を取り込んでから**やり直す"}
    text = cl.render_summary(st)
    assert cl.exit_code(st) == 1
    assert "- 結論: **失敗 —— 1 段も走っていない**" in text
    assert "master を取り込んでから" in text


def _git(repo: Path, *args: str) -> str:
    import subprocess

    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@invalid", "-c",
                           "commit.gpgsign=false", *args], check=True, capture_output=True, text=True).stdout.strip()


def test_head_that_moved_during_a_phase_fails_the_check(tmp_path):
    state = tmp_path / "state"
    inner = _inner(tmp_path, state, "a")
    inner.repo.mkdir(parents=True)
    _git(inner.repo, "init", "-q")
    (inner.repo / "f.txt").write_text("1", encoding="utf-8")
    _git(inner.repo, "add", "f.txt")
    _git(inner.repo, "commit", "-q", "-m", "one")
    first = _git(inner.repo, "rev-parse", "HEAD")
    (inner.repo / "f.txt").write_text("2", encoding="utf-8")
    _git(inner.repo, "commit", "-q", "-am", "two")
    second = _git(inner.repo, "rev-parse", "HEAD")
    assert first != second and len(first) == 40
    inner.tested = second
    inner.verify_tree("段の終わり")  # 一致していれば何も起きない
    inner.tested = first
    with pytest.raises(RuntimeError, match="検査中に木が差し替わった"):
        inner.verify_tree("段の終わり")


def test_summary_lists_missing_tools_first_and_counts_their_skips():
    reasons = {"embed ビルドを建てられない: cargoが無い": 2, "Rust 実装を建てられない": 1, "nodeが無い": 4,
               "Chrome / Chromium not found": 2, "needs a BLAS with >= 4 threads": 5,
               "optional data not present": 7, "robust frustum nodes are monochrome": 6}
    total, per = cl.github_only_skips(reasons, ["cargo", "node", "Chrome"])
    assert (total, per) == (9, {"cargo": 3, "node": 4, "Chrome": 2})
    assert cl.github_only_skips(reasons, []) == (0, {})
    job = _job()
    jc = {"tests": 100, "failures": 0, "errors": 0, "skipped": 27, "xfailed": 0, "executed": 73, "failed": [],
          "skip_reasons": reasons, "broken": None}
    st = _state(job, {k: _ok() for k in cl.PHASE_KEYS}, tools_missing=["cargo", "node", "Chrome"], junit_full=jc,
                blas={"first": 5, "recovered": 5, "detail": "2 ファイル"})
    lines = cl.render_summary(st).splitlines()
    assert lines[3].startswith("- **手元に無い道具(GitHub の runner にはある)**: cargo、node、Chrome")
    assert sum("手元の道具が無いための skip = 9 件" in ln for ln in lines) == 1
    assert "| 7 | optional data not present |" in lines
    assert sum("5 件が走った" in ln for ln in lines) == 1


def test_summary_scrubs_local_paths_and_reports_dirty_files_as_a_count():
    job = _job(dirty_count=4)
    st = _state(job, {"lint": _ok()}, crash="RuntimeError: /home/someone/state/repo が無い",
                scrub=[("/home/someone/state", "<state-dir>"), ("/home/someone", "~")])
    text = cl.render_summary(st)
    assert "someone" not in text
    assert "<state-dir>/repo" in text
    assert "未 commit の変更 4 件" in text


# ---- JUnit と件数の床 ------------------------------------------------------------------------

GOOD_JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="5">
<testcase classname="tests.test_a" name="test_pass" time="0.1"/>
<testcase classname="tests.test_a" name="test_skip" time="0.0"><skipped type="pytest.skip" message="cargo not found">x</skipped></testcase>
<testcase classname="tests.test_a" name="test_xfail" time="0.0"><skipped type="pytest.xfail" message="known"/></testcase>
<testcase classname="tests.test_b" name="test_fail" time="0.2"><failure message="boom">x</failure></testcase>
<testcase classname="tests.test_b" name="test_err" time="0.2"><error message="setup">x</error></testcase>
</testsuite></testsuites>
"""


def test_junit_counts_reads_every_outcome():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "junit.xml"
        p.write_text(GOOD_JUNIT, encoding="utf-8")
        jc = cl.junit_counts(p)
    assert (jc["tests"], jc["failures"], jc["errors"], jc["skipped"], jc["xfailed"], jc["executed"]) == \
        (5, 1, 1, 1, 1, 3)
    assert jc["failed"] == ["tests.test_b::test_fail", "tests.test_b::test_err(error)"]
    assert jc["skip_reasons"] == {"cargo not found": 1}
    assert jc["skipped_cases"] == [["tests.test_a", "test_skip", "cargo not found"]]
    assert jc["broken"] is None
    assert cl.junit_verdict(jc) is None
    assert cl.junit_verdict(jc, floor=3) is None
    assert cl.junit_verdict(jc, floor=4) == "実行件数 3 が床 4 を下回る"


BAD_JUNITS = [
    ("missing", None, "JUnit が無い"),
    ("truncated", '<?xml version="1.0"?><testsuites><testsuite name="pytest"><testcase classname="a" name="b"',
     "JUnit が壊れている(ParseError)"),
    ("empty-file", "", "JUnit が壊れている(ParseError)"),
    ("zero-cases", '<?xml version="1.0"?><testsuites><testsuite name="pytest" tests="0"/></testsuites>',
     "1 件も走っていない(JUnit が 0 件)"),
]


@pytest.mark.parametrize("content,verdict", [(c, v) for _, c, v in BAD_JUNITS], ids=[n for n, _, _ in BAD_JUNITS])
def test_broken_missing_or_empty_junit_is_a_failure_not_an_exception(content, verdict, tmp_path):
    p = tmp_path / "junit.xml"
    if content is not None:
        p.write_text(content, encoding="utf-8")
    jc = cl.junit_counts(p)
    assert jc["tests"] == 0
    assert cl.junit_verdict(jc) == verdict
    assert cl.junit_verdict(jc, floor=10) == verdict


def test_suite_floor_is_ninety_percent_of_the_duration_baseline():
    assert cl.SUITE_FLOOR_RATIO == 0.90
    assert cl.SUITE_FLOOR_ABSOLUTE == 10_000
    assert cl.suite_floor(27_664)[0] == 24_898
    assert cl.suite_floor(None)[0] == 10_000
    assert cl.suite_floor(0)[0] == 10_000
    n = cl.count_durations(ROOT / ".test_durations")
    assert n is not None and n > 20_000
    floor, basis = cl.suite_floor(n)
    assert floor == math.ceil(n * 0.9)
    assert 20_000 <= floor < n
    assert ".test_durations" in basis


def test_count_durations_of_an_unreadable_file_is_none(tmp_path):
    assert cl.count_durations(tmp_path / "nope") is None
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    assert cl.count_durations(bad) is None
    lst = tmp_path / "list.json"
    lst.write_text("[1, 2]", encoding="utf-8")
    assert cl.count_durations(lst) is None


# ---- 外側の引数と置き場 ----------------------------------------------------------------------

def test_state_dir_must_be_a_linux_path():
    assert cl.check_state_dir_arg("~/fullseye-ci-local", True) == "~/fullseye-ci-local"
    assert cl.check_state_dir_arg("/home/u/ci", False) == "/home/u/ci"
    for bad in ("C:/Program Files/Git/tmp/zzz", "E:\\work\\zzz", "rel/dir"):
        with pytest.raises(cl.UsageError):
            cl.check_state_dir_arg(bad, True)
    with pytest.raises(cl.UsageError):
        cl.check_state_dir_arg("rel/dir", False)


def test_inner_refuses_to_run_without_explicit_state_dir_and_workers(tmp_path, capsys):
    job = tmp_path / "job.json"
    job.write_text(json.dumps(_job(state_dir=str(tmp_path / "state"), out=str(tmp_path / "out"))), encoding="utf-8")
    assert cl.main(["--inside", str(job)]) == cl.EXIT_USAGE
    assert cl.main(["--inside", str(job), "--state-dir", str(tmp_path / "state")]) == cl.EXIT_USAGE
    assert "--state-dir と -n" in capsys.readouterr().err
    assert not (tmp_path / "state").exists()


def test_prepare_out_removes_the_previous_run_products_only(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    stale = ["summary.md", "result.json", "junit-full.xml", "junit-gates.xml", "full-suite.log"]
    for name in stale:
        (out / name).write_text("previous run", encoding="utf-8")
    (out / "notes.txt").write_text("mine", encoding="utf-8")
    cl.prepare_out(out)
    assert sorted(p.name for p in out.iterdir()) == ["notes.txt"]
    assert set(stale) <= set(cl.OUT_PRODUCTS)


def test_only_the_fullseye_pyproject_is_accepted():
    assert cl.is_fullseye_pyproject((ROOT / "pyproject.toml").read_text(encoding="utf-8")) is True
    assert cl.is_fullseye_pyproject('[project]\nname = "raptor"\n') is False
    assert cl.is_fullseye_pyproject('[project]\ndescription = "name = fullseye"\n') is False


# ---- 状態ディレクトリ: 目印と排他 ------------------------------------------------------------

def _inner(tmp_path: Path, state: Path, tag: str):
    return cl.Inner(_job(state_dir=str(state), out=str(tmp_path / f"out-{tag}")))


def test_unmarked_existing_directory_is_refused_and_left_untouched(tmp_path):
    state = tmp_path / "somebody-elses"
    (state / "repo").mkdir(parents=True)
    (state / "repo" / "precious.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(RuntimeError, match="目印"):
        _inner(tmp_path, state, "a").claim_state_dir()
    assert sorted(p.name for p in state.iterdir()) == ["repo"]
    assert (state / "repo" / "precious.txt").read_text(encoding="utf-8") == "keep"


def test_state_dir_lock_makes_the_second_run_fail_at_once(tmp_path):
    pytest.importorskip("fcntl", reason="flock は Linux 側(内側)だけ")
    state = tmp_path / "state"
    first = _inner(tmp_path, state, "a")
    first.claim_state_dir()
    assert (state / cl.MARKER).is_file()
    owner = json.loads((state / cl.OWNER_FILE).read_text(encoding="utf-8"))
    assert owner["sha"] == SHA
    second = _inner(tmp_path, state, "b")
    with pytest.raises(cl.Busy, match=SHA[:12]):
        second.claim_state_dir()
    first._lock_fh.close()
    second.claim_state_dir()  # 持ち主が終われば取れる
    second._lock_fh.close()


def test_state_dir_of_the_first_version_is_adopted_by_its_venv_stamp(tmp_path):
    pytest.importorskip("fcntl", reason="flock は Linux 側(内側)だけ")
    state = tmp_path / "old"
    (state / "venv-full").mkdir(parents=True)
    (state / "venv-full" / ".ci_local_stamp.json").write_text("{}", encoding="utf-8")
    inner = _inner(tmp_path, state, "a")
    inner.claim_state_dir()
    inner._lock_fh.close()
    assert (state / cl.MARKER).is_file()
    assert len(inner.setup_notes) == 1 and "引き継いだ" in inner.setup_notes[0]


# ---- ci.yml から手で写した定義 ---------------------------------------------------------------

def test_hand_copied_dependency_definitions_still_appear_in_ci_yml():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    needles = [
        f'pip install -e ".[{cl.FULL_EXTRAS}]"',
        " ".join(cl.FULL_EXTRA_PKGS),
        "pip install --index-url {} {}".format(cl.TORCH_INDEX, " ".join(f'"{p}"' for p in cl.TORCH_PKGS)),
        "pip install " + " ".join(f'"{p}"' for p in cl.OPTIONAL_PKGS),
        f'pip install "{cl.OPENCV_CONTRIB}"',
        f'python -c "{cl.VERIFY_FULL}"',
        "python -m pip install --upgrade " + " ".join(f'"{p}"' for p in cl.PIP_BOOTSTRAP),
        f'pip install -q "{cl.BUILD_PIN}"',
        f'pip install "{cl.RUFF_PIN}"',
        f'pip install "{cl.PIP_AUDIT_PIN}"',
        "python tools/pip_audit_gate.py " + " ".join(cl.PIP_AUDIT_ARGS),
        "sudo apt-get install -y -q " + " ".join(cl.APT_PKGS[:4]),
        "sudo apt-get install -y -q " + " ".join(cl.APT_PKGS[4:]),
        f"--min-executed {cl.SUITE_FLOOR_ABSOLUTE}",
        "python tools/regen_all.py --check",
        "pytest tests/test_unified_packaging.py tests/test_packaging_foundation.py -q",
        "pytest tests/test_mcp_wheel.py tests/test_abi_wheel.py -q -ra",
    ]
    assert len(needles) == 17
    assert len(cl.APT_PKGS) == 6
    missing = [n for n in needles if n not in ci]
    assert missing == []
    assert "pytest-xdist" not in cl.FULL_EXTRA_PKGS and cl.LOCAL_ONLY_PKGS == ["pytest-xdist"]

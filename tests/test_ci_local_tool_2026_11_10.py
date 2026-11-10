# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tools/ci_local.py(手元の Linux で CI 相当を回す道具)そのものの門。WSL は起動しない。

2026-11-10 の敵対的レビューが実行で確かめた入力を、そのままテストにしてある:

* ``--only ruff --skip ruff``・全段 ``--skip`` が**何も走らせずに終了コード 0** だった
* 部分実行の要約の題が「手元の全数」のままだった
* 壊れた JUnit で要約が書けず、0 件の JUnit が成功に見えた
* 状態ディレクトリに排他が無く、目印の無い既存のディレクトリで ``clean -fdx`` を走らせた
* 門の一覧の内蔵の写し・ci.yml から手で写した依存の定義が、黙ってずれうる

同じ日の 2 回目のレビューは、道具を 1 か所ずつ壊す変異 22 通りのうち 8 通りを、このファイルが見逃すことを示した
(床を計算するだけで渡さない・祖先の判定が逆・fetch の失敗を握りつぶす・BLAS の回し直しの失敗を無視・
pip-audit と pytest の終了コードを無視・merge しない・環境変数の状態ディレクトリを読まない)。
純関数だけを見ていたからで、後半のテストは ``build_job``・``sync_repo``・``phase_*``・``rerun_blas``・``Inner.main`` を通す。
git は ``tmp_path`` の中の本物の repo で動かす(git が無ければ skip でなく失敗)。pytest・pip・ruff は差し替える。
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


def test_suite_floor_is_ninety_five_percent_of_the_duration_baseline():
    assert cl.SUITE_FLOOR_RATIO == 0.95
    assert cl.SUITE_FLOOR_ABSOLUTE == 10_000
    assert cl.suite_floor(27_664)[0] == 26_281
    assert cl.suite_floor(None)[0] == 10_000
    assert cl.suite_floor(0)[0] == 10_000
    n = cl.count_durations(ROOT / ".test_durations")
    assert n is not None and n > 20_000
    floor, basis = cl.suite_floor(n)
    assert floor == math.ceil(n * 0.95)
    assert 20_000 <= floor < n
    assert ".test_durations" in basis and "0.95" in basis
    # 比率の根拠にした実測(手元の全数: .test_durations 27,699 行 / JUnit 28,148 件 / 実行 27,710 件)は通り、
    # 以前の床(0.90 = 24,930 件)まで減った実行は通らない
    measured_floor = cl.suite_floor(27_699)[0]
    assert measured_floor == 26_315
    assert cl.junit_verdict({"tests": 28_148, "executed": 27_710, "broken": None}, measured_floor) is None
    assert cl.junit_verdict({"tests": 28_148, "executed": 24_930, "broken": None}, measured_floor) is not None


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
    assert json.loads((state / cl.OWNER_FILE).read_text(encoding="utf-8"))["sha"] == SHA  # 目印のあとにロックも取る


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


# =============================================================================================
# 2 回目のレビュー(2026-11-10)の追跡。純関数だけでなく、道具の中身を通す。
# git は tmp_path の中の本物の repo で動かし(無ければ skip でなく失敗)、pytest・pip・ruff は差し替える。
# =============================================================================================

def _tree(**over) -> dict:
    return dict(_job()["tree"], **over)


def _all_ok() -> dict:
    return {k: _ok() for k in cl.PHASE_KEYS}


# ---- GitHub と違う条件(--no-merge・--no-fetch・--allow-other-python)-------------------------

DEVIATING_JOBS = [
    ("no-merge", {"tree": _tree(mode="tip", tested=SHA)}, "--no-merge"),
    ("no-fetch", {"tree": _tree(fetched="no_fetch")}, "--no-fetch"),
    ("base-by-sha", {"tree": _tree(fetched="not_remote", base_ref=BASE)}, "形でないので fetch していない"),
    ("other-python", {"allow_other_python": True, "python": "python3.12"}, "--allow-other-python(Python 3.12.3"),
]


@pytest.mark.parametrize("over,reason", [(o, r) for _, o, r in DEVIATING_JOBS], ids=[n for n, _, _ in DEVIATING_JOBS])
def test_run_under_other_conditions_than_github_is_never_called_all_green(over, reason):
    job = _job(**over)
    versions = {"full": "3.12.3", "lint": "3.12.3"} if over.get("allow_other_python") else {"full": "3.11.9"}
    st = _state(job, _all_ok(), python_versions=versions)
    text = cl.render_summary(st)
    title, conclusion = text.splitlines()[0], text.splitlines()[2]
    assert title.endswith("— GitHub の CI とは違う条件")
    assert "部分実行" not in title
    assert conclusion.startswith("- 結論: **GitHub の CI とは違う条件での検査**")
    assert reason in conclusion
    assert "この結果を GitHub の CI が通る証拠にしない" in conclusion
    assert "**全段 ok**" not in text
    assert len(cl.deviation_reasons(job, versions)) == 1
    # 終了コードは「走った段が ok」のまま 0。緑との区別は題・結論・verdict でする
    assert cl.exit_code(st) == cl.EXIT_OK
    assert cl.verdict(st) == "deviating_ok"


def test_deviation_reasons_is_empty_for_the_default_run_and_lists_every_flag():
    assert cl.deviation_reasons(_job()) == []
    assert cl.deviation_reasons(_job(allow_other_python=False), {"full": "3.11.9"}) == []
    every = cl.deviation_reasons(_job(tree=_tree(mode="tip", fetched="no_fetch"), allow_other_python=True),
                                 {"full": "3.12.3", "lint": "3.11.9"})
    assert len(every) == 3
    assert every[0].startswith("--no-merge") and every[1].startswith("--no-fetch")
    assert "3.12.3" in every[2] and "3.11.9" not in every[2]


def test_partial_run_under_other_conditions_carries_both_warnings():
    job = _job(only="lint", selected=["lint"], tree=_tree(fetched="no_fetch"))
    st = _state(job, {"lint": _ok()})
    text = cl.render_summary(st)
    title, conclusion = text.splitlines()[0], text.splitlines()[2]
    assert title.endswith("— 部分実行(全数ではない) — GitHub の CI とは違う条件")
    assert conclusion.startswith("- 結論: **部分実行(全数ではない)**")
    assert "この結果を全数の証拠にしない" in conclusion
    assert "この結果を GitHub の CI が通る証拠にしない" in conclusion
    assert cl.verdict(st) == "partial_ok"


def test_verdict_separates_the_meanings_of_exit_code_zero():
    failed = {"state": "failed", "detail": "失敗", "sec": 2.0}
    cases = [
        (_state(_job(), _all_ok()), "full_ok", 0),
        (_state(_job(only="lint", selected=["lint"]), {"lint": _ok()}), "partial_ok", 0),
        (_state(_job(pytest_args=["-k", "smoke"]), _all_ok()), "partial_ok", 0),
        (_state(_job(pip_audit=False), _all_ok()), "partial_ok", 0),
        (_state(_job(tree=_tree(mode="tip", tested=SHA)), _all_ok()), "deviating_ok", 0),
        (_state(_job(tree=_tree(fetched="no_fetch")), _all_ok()), "deviating_ok", 0),
        (_state(_job(), dict(_all_ok(), regen=failed)), "failed", 1),
        (_state(_job(tree=_tree(mode="tip", tested=SHA)), dict(_all_ok(), tests=failed)), "failed", 1),
        (_state(_job(), {}), "failed", 1),
        (_state(_job(), {}, busy=True, crash="別の ci_local が使っている"), "busy", 3),
    ]
    assert len(cases) == 10
    got = [(cl.verdict(st), cl.exit_code(st)) for st, _, _ in cases]
    assert got == [(want, code) for _, want, code in cases]
    # 「全段 ok」と書くのは full_ok のときだけ
    green = ["- 結論: **全段 ok**(5 段)" in cl.render_summary(st) for st, _, _ in cases]
    assert green == [want == "full_ok" for _, want, _ in cases]
    assert sum(green) == 1


# ---- skip の前回比と BLAS の回し直しの集計 ---------------------------------------------------

def test_skip_jump_flags_a_large_increase_and_names_what_grew():
    assert (cl.SKIP_JUMP_RATIO, cl.SKIP_JUMP_MIN) == (0.10, 20)
    prev = {"skipped": 427, "sha": SHA, "when": "2026-11-10 18:40",
            "skip_reasons": {"cargo が無い": 114, "optional data not present": 300}}
    # 知らせる線 = 427 + max(20, ceil(42.7)) = 470。ちょうどは知らせない
    assert cl.skip_jump(prev, {"skipped": 470, "skip_reasons": {}}) is None
    msg = cl.skip_jump(prev, {"skipped": 471, "skip_reasons": {"cargo が無い": 114, "optional data not present": 300,
                                                               "could not import 'torch'": 44, "new | reason": 13}})
    assert msg is not None
    assert msg.startswith("**skip が前回の記録から大きく増えた**: 427 → 471 件(+44。知らせる線は +43)")
    assert "+44 件「could not import 'torch'」;+13 件「new / reason」" in msg
    assert SHA[:12] in msg and "2026-11-10 18:40" in msg and cl.SKIP_BASELINE_FILE in msg
    assert "cargo が無い" not in msg  # 増えていない理由は挙げない
    assert cl.skip_jump(prev, {"skipped": 300, "skip_reasons": {}}) is None  # 減ったのは知らせない
    # 記録が小さいときは件数の下限(20)が線
    assert cl.skip_jump({"skipped": 5}, {"skipped": 25}) is None
    assert cl.skip_jump({"skipped": 5}, {"skipped": 26}) is not None
    # 記録が無い・読めない形なら比べない
    unusable = [None, {}, {"skipped": "many"}, [427]]
    assert [cl.skip_jump(p, {"skipped": 10_000}) for p in unusable] == [None] * 4


def test_summary_puts_the_skip_jump_right_under_the_tools_line():
    msg = cl.skip_jump({"skipped": 10, "sha": SHA, "when": "2026-11-10 18:40"}, {"skipped": 31})
    assert msg is not None
    st = _state(_job(), _all_ok(), skip_jump=msg)
    lines = cl.render_summary(st).splitlines()
    assert lines[3].startswith("- 手元に無い道具: なし")
    assert lines[4] == f"- {msg}"
    assert lines[5].startswith("- 検査した木: ")
    assert sum("skip が前回の記録から大きく増えた" in ln for ln in lines) == 1
    assert cl.exit_code(st) == 0  # 知らせるだけ(失敗にはしない)
    quiet = cl.render_summary(_state(_job(), _all_ok())).splitlines()
    assert quiet[4].startswith("- 検査した木: ")


def test_blas_rerun_outcome_counts_what_ran_stayed_skipped_or_vanished(tmp_path):
    cases = [("tests.test_t", "test_a"), ("tests.test_t", "test_b"), ("tests.test_u", "test_c")]
    ids = {("tests.test_t", "test_a"), ("tests.test_t", "test_b"), ("tests.test_t", "test_other")}
    res = cl.blas_rerun_outcome(cases, ids, {("tests.test_t", "test_b")})
    assert res == {"first": 3, "recovered": 1, "still_skipped": 1, "absent": 1}
    assert cl.blas_rerun_outcome(cases, None, set()) == {"first": 3, "recovered": 0, "still_skipped": 0, "absent": 3}
    assert cl.blas_rerun_outcome(cases, set(cases), set()) == {"first": 3, "recovered": 3, "still_skipped": 0,
                                                               "absent": 0}
    junit = tmp_path / "junit.xml"
    junit.write_text(GOOD_JUNIT, encoding="utf-8")
    got = cl.junit_case_ids(junit)
    assert got is not None and len(got) == 5 and ("tests.test_b", "test_fail") in got
    assert cl.junit_case_ids(tmp_path / "nope.xml") is None


def test_summary_says_how_many_blas_tests_still_did_not_run():
    reasons = {"needs a BLAS with >= 4 threads": 3}
    jc = {"tests": 100, "failures": 0, "errors": 0, "skipped": 3, "xfailed": 0, "executed": 97, "failed": [],
          "skip_reasons": reasons, "broken": None}
    stuck = _state(_job(), _all_ok(), junit_full=jc,
                   blas={"first": 3, "recovered": 1, "still_skipped": 1, "absent": 1, "detail": "1 ファイル"})
    lines = cl.render_summary(stuck).splitlines()
    assert sum("1 件が走った、**2 件は走らないまま = 失敗**(skip のまま 1 件・回し直しに現れない 1 件)" in ln
               for ln in lines) == 1
    fine = _state(_job(), _all_ok(), junit_full=jc,
                  blas={"first": 3, "recovered": 3, "still_skipped": 0, "absent": 0, "detail": "1 ファイル"})
    text = cl.render_summary(fine)
    assert text.count("3 件が走った(1 ファイル)") == 1 and "走らないまま" not in text


# ---- 外側: build_job(本物の git)-------------------------------------------------------------

def _commit(repo: Path, name: str, text: str, msg: str) -> str:
    (repo / name).write_text(text, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD")


def _origin(tmp_path: Path, name: str = "origin", project: str = "fullseye") -> Path:
    origin = tmp_path / name
    origin.mkdir(parents=True)
    _git(origin, "init", "-q", "-b", "master")
    (origin / "f.txt").write_text("1\n", encoding="utf-8")
    _git(origin, "add", "f.txt")
    _commit(origin, "pyproject.toml", f'[project]\nname = "{project}"\n', "first")
    return origin


def _work_repo(tmp_path: Path) -> tuple[Path, Path]:
    """origin(master に 1 commit)と、その clone。"""
    origin = _origin(tmp_path)
    work = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    return origin, work


def _args(tmp_path: Path, *argv: str):
    return cl.build_parser().parse_args([*argv, "--out", str(tmp_path / "out")])


def _shape(job: dict) -> tuple:
    tree = job["tree"]
    return tree["mode"], tree["behind"], tree["ahead"], tree["fetched"]


def test_build_job_classifies_the_tree_against_the_freshly_fetched_base(tmp_path):
    origin, work = _work_repo(tmp_path)
    base0 = _git(origin, "rev-parse", "HEAD")
    job, out, common = cl.build_job(_args(tmp_path), work, {})
    assert _shape(job) == ("is_base", 0, 0, "yes")
    assert (job["sha"], job["tree"]["base_sha"]) == (base0, base0)
    assert out == (tmp_path / "out").resolve()
    assert common.resolve() == (work / ".git").resolve()
    assert job["selected"] == list(cl.PHASE_KEYS)
    # 対象が 2 commit 先 = merge は対象そのもの
    _commit(work, "a.txt", "a\n", "a")
    tip = _commit(work, "b.txt", "b\n", "b")
    job = cl.build_job(_args(tmp_path), work, {})[0]
    assert _shape(job) == ("ahead", 0, 2, "yes")
    assert (job["sha"], job["tree"]["base_sha"]) == (tip, base0)
    # master が 3 commit 進む。手元の追跡 ref は古いままで、道具が fetch して初めて見える
    for i in range(3):
        new_base = _commit(origin, f"m{i}.txt", "m\n", f"master {i}")
    assert _git(work, "rev-parse", "origin/master") == base0
    job = cl.build_job(_args(tmp_path), work, {})[0]
    assert _shape(job) == ("merge", 3, 2, "yes")
    assert job["tree"]["base_sha"] == new_base != base0
    assert cl.deviation_reasons(job) == []
    # 対象が master の祖先(遅れているだけ)
    job = cl.build_job(_args(tmp_path, "--ref", base0), work, {})[0]
    assert _shape(job) == ("behind", 3, 0, "yes")
    assert job["dirty_applies"] is False
    # --no-merge は分岐していても先端だけ
    job = cl.build_job(_args(tmp_path, "--no-merge"), work, {})[0]
    assert _shape(job) == ("tip", 3, 2, "yes")
    assert len(cl.deviation_reasons(job)) == 1


def test_no_fetch_keeps_the_stale_tracking_ref_and_is_reported_as_a_deviation(tmp_path):
    origin, work = _work_repo(tmp_path)
    base0 = _git(origin, "rev-parse", "HEAD")
    _commit(work, "a.txt", "a\n", "a")
    new_base = _commit(origin, "m.txt", "m\n", "master moved")
    job = cl.build_job(_args(tmp_path, "--no-fetch"), work, {})[0]
    assert _shape(job) == ("ahead", 0, 1, "no_fetch")  # 古い master に対しては「先にいるだけ」に見える
    assert job["tree"]["base_sha"] == base0
    assert _git(work, "rev-parse", "origin/master") == base0  # fetch していない
    reasons = cl.deviation_reasons(job)
    assert len(reasons) == 1 and reasons[0].startswith("--no-fetch")
    job = cl.build_job(_args(tmp_path), work, {})[0]
    assert _shape(job) == ("merge", 1, 1, "yes")
    assert job["tree"]["base_sha"] == new_base
    by_sha = cl.build_job(_args(tmp_path, "--base", new_base), work, {})[0]
    assert _shape(by_sha) == ("merge", 1, 1, "not_remote")
    assert len(cl.deviation_reasons(by_sha)) == 1


def test_fetch_failure_stops_instead_of_testing_against_a_stale_base(tmp_path):
    _, work = _work_repo(tmp_path)
    _git(work, "remote", "set-url", "origin", str(tmp_path / "gone"))
    with pytest.raises(cl.UsageError, match="`git fetch origin master` が失敗した"):
        cl.build_job(_args(tmp_path), work, {})
    job = cl.build_job(_args(tmp_path, "--no-fetch"), work, {})[0]  # 明示すれば、古い ref のまま進める
    assert _shape(job) == ("is_base", 0, 0, "no_fetch")


def test_state_dir_and_workers_come_from_the_environment_unless_given_as_arguments(tmp_path):
    _, work = _work_repo(tmp_path)
    env = {"FULLSEYE_CI_LOCAL_DIR": "~/ci-elsewhere", "FULLSEYE_CI_LOCAL_WORKERS": "3"}
    job = cl.build_job(_args(tmp_path, "--no-fetch"), work, env)[0]
    assert (job["state_dir"], job["workers"]) == ("~/ci-elsewhere", 3)
    job = cl.build_job(_args(tmp_path, "--no-fetch", "--state-dir", "~/by-arg", "-n", "5"), work, env)[0]
    assert (job["state_dir"], job["workers"]) == ("~/by-arg", 5)
    job = cl.build_job(_args(tmp_path, "--no-fetch"), work, {})[0]
    assert (job["state_dir"], job["workers"]) == (cl.DEFAULT_STATE_DIR, 12)
    with pytest.raises(cl.UsageError, match="1 以上"):
        cl.build_job(_args(tmp_path, "--no-fetch", "-n", "0"), work, {})
    with pytest.raises(cl.UsageError, match="--state-dir"):
        cl.build_job(_args(tmp_path, "--no-fetch"), work, {"FULLSEYE_CI_LOCAL_DIR": "relative/dir"})


def test_build_job_counts_uncommitted_changes_and_refuses_what_it_cannot_test(tmp_path):
    _, work = _work_repo(tmp_path)
    (work / "untracked.txt").write_text("x", encoding="utf-8")
    (work / "f.txt").write_text("changed\n", encoding="utf-8")
    job = cl.build_job(_args(tmp_path, "--no-fetch"), work, {})[0]
    assert (job["dirty_count"], job["dirty_applies"]) == (2, True)
    with pytest.raises(cl.UsageError, match="commit に解決できない"):
        cl.build_job(_args(tmp_path, "--no-fetch", "--ref", "no-such-branch"), work, {})
    with pytest.raises(cl.UsageError, match="merge の相手が無い"):
        cl.build_job(_args(tmp_path, "--no-fetch", "--base", "no-such-base"), work, {})
    other = _origin(tmp_path, "other", project="raptor")
    with pytest.raises(cl.UsageError, match="Fullseye ではない"):
        cl.build_job(_args(tmp_path, "--no-fetch", "--no-merge"), other, {})


# ---- 内側: 検査する木(本物の git)-----------------------------------------------------------

def _inner_from(tmp_path: Path, work: Path, *argv: str):
    job, _, common = cl.build_job(_args(tmp_path, *argv), work, {})
    job.update(source=str(common), out=str(tmp_path / "out-inner"), state_dir=str(tmp_path / "state"))
    return cl.Inner(job)


def _tracked(repo: Path) -> list[str]:
    return sorted(p.name for p in repo.iterdir() if p.name != ".git")


def test_sync_repo_tests_the_merge_commit_with_base_as_the_first_parent(tmp_path):
    origin, work = _work_repo(tmp_path)
    tip = _commit(work, "feature.txt", "feature\n", "feature")
    base = _commit(origin, "master_side.txt", "master\n", "master moved")
    inner = _inner_from(tmp_path, work)
    assert inner.tree["mode"] == "merge"
    inner.sync_repo()
    assert len(inner.tested) == 40 and inner.tested not in (tip, base)
    assert inner.tree["tested"] == inner.tested
    assert _git(inner.repo, "rev-parse", "HEAD") == inner.tested
    assert _git(inner.repo, "rev-parse", "HEAD^1") == base  # GitHub の PR と同じ向き
    assert _git(inner.repo, "rev-parse", "HEAD^2") == tip
    assert _tracked(inner.repo) == ["f.txt", "feature.txt", "master_side.txt", "pyproject.toml"]
    assert _git(inner.repo, "rev-parse", "refs/ci-local/tested") == inner.tested
    assert _git(work, "rev-parse", "HEAD") == tip  # merge を作るのは clone の中だけ
    # 2 回目: 既にある clone を使い、前の run の置き土産を消して同じ形の木にする
    (inner.repo / "left-over.txt").write_text("x", encoding="utf-8")
    again = _inner_from(tmp_path, work)
    again.sync_repo()
    assert _tracked(again.repo) == ["f.txt", "feature.txt", "master_side.txt", "pyproject.toml"]
    assert (_git(again.repo, "rev-parse", "HEAD^1"), _git(again.repo, "rev-parse", "HEAD^2")) == (base, tip)


def test_sync_repo_reports_a_conflict_and_leaves_no_half_merged_tree(tmp_path):
    import subprocess

    origin, work = _work_repo(tmp_path)
    _commit(work, "same.txt", "feature side\n", "feature")
    base = _commit(origin, "same.txt", "master side\n", "master moved")
    inner = _inner_from(tmp_path, work)
    assert inner.tree["mode"] == "merge"
    with pytest.raises(RuntimeError) as exc:
        inner.sync_repo()
    assert "との merge が衝突した(1 ファイル: `same.txt`)" in str(exc.value)
    assert inner.tested is None and "tested" not in inner.tree
    assert not (inner.repo / ".git" / "MERGE_HEAD").exists()
    assert _git(inner.repo, "status", "--porcelain") == ""
    assert _git(inner.repo, "rev-parse", "HEAD") == base
    ref = subprocess.run(["git", "-C", str(inner.repo), "rev-parse", "--verify", "--quiet", "refs/ci-local/tested"],
                         capture_output=True, text=True)
    assert (ref.returncode, ref.stdout.strip()) == (1, "")
    assert cl.tree_line(inner.tree).startswith("- 検査した木: **無い**")


def test_sync_repo_tests_the_tip_itself_when_no_merge_is_made(tmp_path):
    origin, work = _work_repo(tmp_path)
    tip = _commit(work, "feature.txt", "feature\n", "feature")
    ahead = _inner_from(tmp_path / "ahead", work)
    assert ahead.tree["mode"] == "ahead"
    ahead.sync_repo()
    assert ahead.tested == tip == _git(ahead.repo, "rev-parse", "HEAD")
    assert _tracked(ahead.repo) == ["f.txt", "feature.txt", "pyproject.toml"]
    _commit(origin, "master_side.txt", "master\n", "master moved")
    only_tip = _inner_from(tmp_path / "tip", work, "--no-merge")
    assert only_tip.tree["mode"] == "tip" and only_tip.tree["behind"] == 1
    only_tip.sync_repo()
    assert only_tip.tested == tip
    assert _tracked(only_tip.repo) == ["f.txt", "feature.txt", "pyproject.toml"]  # master 側は入らない


# ---- 内側: 目印の無い旧版の置き場を引き継ぐ前に repo/ を確かめる ------------------------------

def _stamped(tmp_path: Path) -> Path:
    state = tmp_path / "old"
    (state / "venv-core").mkdir(parents=True)
    (state / "venv-core" / ".ci_local_stamp.json").write_text("{}", encoding="utf-8")
    return state


def _listing(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if ".git" not in p.parts)


def test_old_state_dir_is_adopted_when_its_repo_is_a_clone_of_the_tested_repo(tmp_path):
    origin = _origin(tmp_path)
    state = _stamped(tmp_path)
    _git(tmp_path, "clone", "-q", str(origin), str(state / "repo"))
    (state / "repo" / "left-over.txt").write_text("x", encoding="utf-8")
    inner = cl.Inner(_job(state_dir=str(state), out=str(tmp_path / "out-a"), source=str(origin)))
    inner.check_marker()
    assert (state / cl.MARKER).is_file()
    assert len(inner.setup_notes) == 1 and "引き継いだ" in inner.setup_notes[0]
    inner.check_marker()  # 目印があれば、2 回目は何も言わない
    assert len(inner.setup_notes) == 1


def test_old_state_dir_without_a_repo_is_adopted_by_its_venv_stamp(tmp_path):
    state = _stamped(tmp_path)
    inner = cl.Inner(_job(state_dir=str(state), out=str(tmp_path / "out-a"), source=str(tmp_path / "origin")))
    inner.check_marker()
    assert (state / cl.MARKER).is_file()
    assert len(inner.setup_notes) == 1 and "引き継いだ" in inner.setup_notes[0]


FOREIGN_REPOS = ["other-origin", "not-fullseye", "no-origin", "not-git"]


@pytest.mark.parametrize("kind", FOREIGN_REPOS)
def test_old_state_dir_with_a_foreign_repo_is_refused_before_anything_is_cleaned(kind, tmp_path):
    origin = _origin(tmp_path)
    state = _stamped(tmp_path)
    repo = state / "repo"
    source = origin
    if kind == "other-origin":  # 別の Fullseye の clone(origin が、検査する repo と違う)
        _git(tmp_path, "clone", "-q", str(_origin(tmp_path, "elsewhere")), str(repo))
        want = "origin が、検査する repo と違う"
    elif kind == "not-fullseye":  # origin は合うが、中身が Fullseye でない
        source = _origin(tmp_path, "raptor", project="raptor")
        _git(tmp_path, "clone", "-q", str(source), str(repo))
        want = "name が fullseye でない"
    elif kind == "no-origin":  # レビューの実行と同じ形: たまたま repo/ という名前の、別の git repo
        _origin(state, "repo")
        want = "origin が、検査する repo と違う"
    else:
        repo.mkdir()
        want = "git の clone でない"
    (repo / "precious.txt").write_text("keep", encoding="utf-8")
    before = _listing(state)
    assert "repo/precious.txt" in before and "venv-core/.ci_local_stamp.json" in before
    inner = cl.Inner(_job(state_dir=str(state), out=str(tmp_path / "out-a"), source=str(source)))
    with pytest.raises(RuntimeError, match=want) as exc:
        inner.check_marker()
    assert "止めた" in str(exc.value)
    assert not (state / cl.MARKER).exists()
    assert _listing(state) == before
    assert (repo / "precious.txt").read_text(encoding="utf-8") == "keep"
    assert inner.setup_notes == []


def test_unmarked_directory_without_a_venv_stamp_is_never_adopted(tmp_path):
    state = tmp_path / "somebody-elses"
    state.mkdir()
    (state / "notes.txt").write_text("keep", encoding="utf-8")
    inner = _inner(tmp_path, state, "a")
    with pytest.raises(RuntimeError, match="目印 .fullseye-ci-local が無い。"):
        inner.check_marker()
    assert _listing(state) == ["notes.txt"]
    empty = tmp_path / "empty"
    empty.mkdir()
    _inner(tmp_path, empty, "b").check_marker()  # 空の既存のディレクトリは、目印を置いて使う
    assert _listing(empty) == [cl.MARKER]


# ---- 内側: 段(pytest・pip・ruff は差し替え)--------------------------------------------------

class _FakeRun:
    """``Inner.run`` の差し替え。呼び出しを記録し、handler の返した終了コードを返す。"""

    def __init__(self, handler):
        self.calls: list[dict] = []
        self.handler = handler

    def __call__(self, cmd, *, env=None, cwd=None, log=None, check=True):
        self.calls.append({"cmd": list(cmd), "env": dict(env or {}), "cwd": cwd, "log": log})
        rc = self.handler(list(cmd), log)
        if check and rc != 0:
            raise RuntimeError(f"exit {rc}")
        return rc


def _junit_text(passed: int, skipped=(), failed: int = 0, ran=()) -> str:
    from xml.sax.saxutils import quoteattr

    rows = [f'<testcase classname="tests.test_many" name="test_{i}" time="0.01"/>' for i in range(passed)]
    rows += [f"<testcase classname={quoteattr(c)} name={quoteattr(n)} time=\"0.01\"/>" for c, n in ran]
    rows += [f"<testcase classname={quoteattr(c)} name={quoteattr(n)} time=\"0.0\"><skipped type=\"pytest.skip\" "
             f"message={quoteattr(r)}>x</skipped></testcase>" for c, n, r in skipped]
    rows += [f'<testcase classname="tests.test_many" name="test_bad_{i}" time="0.01"><failure message="boom">x'
             "</failure></testcase>" for i in range(failed)]
    return ('<?xml version="1.0" encoding="utf-8"?>\n<testsuites><testsuite name="pytest" tests="%d">\n%s\n'
            "</testsuite></testsuites>\n" % (len(rows), "\n".join(rows)))


def _pytest_script(script):
    """pytest の呼び出しを、順に (終了コード, 書く JUnit の中身。None なら書かない) で演じる。"""
    left = list(script)

    def handler(cmd, log):
        rc, text = left.pop(0)
        target = [a.split("=", 1)[1] for a in cmd if a.startswith("--junitxml=")]
        assert len(target) == 1, cmd
        if text is not None:
            Path(target[0]).write_text(text, encoding="utf-8")
        return rc

    return handler


def _suite_inner(tmp_path: Path, n_rows: int, **job_over):
    inner = cl.Inner(_job(state_dir=str(tmp_path / "state"), out=str(tmp_path / "out"), **job_over))
    inner.repo.mkdir(parents=True, exist_ok=True)
    rows = {f"tests/test_many.py::test_{i}": 0.01 for i in range(n_rows)}
    (inner.repo / ".test_durations").write_text(json.dumps(rows), encoding="utf-8")
    inner.full_env = lambda name: {"PATH": "/venv/bin"}
    return inner


def _run_suite(inner, script) -> _FakeRun:
    inner.run = fake = _FakeRun(_pytest_script(script))
    inner.phase_tests()
    return fake


def test_full_suite_phase_fails_on_a_nonzero_pytest_exit_even_when_the_junit_is_clean(tmp_path):
    bad = _suite_inner(tmp_path / "bad", 100)
    fake = _run_suite(bad, [(1, _junit_text(100))])
    res = bad.results["tests"]
    assert res["state"] == "failed"
    assert res["detail"].startswith("失敗(exit 1)") and "100 passed / 0 failed" in res["detail"]
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["cmd"][1:3] == ["-q", "-ra"] and call["cmd"][-4:] == ["-n", "2", "--dist", "worksteal"]
    assert (call["log"], call["cwd"]) == ("full-suite.log", bad.repo)
    assert call["env"]["FULLSEYE_REQUIRE_OPTIONAL"] == "1"
    good = _suite_inner(tmp_path / "good", 100)  # 同じ JUnit で終了コードだけ 0
    _run_suite(good, [(0, _junit_text(100))])
    assert good.results["tests"]["state"] == "ok"
    red = _suite_inner(tmp_path / "red", 100)  # 落ちたテストは JUnit からも名前を拾う
    _run_suite(red, [(1, _junit_text(98, failed=2))])
    assert red.results["tests"]["state"] == "failed" and "98 passed / 2 failed" in red.results["tests"]["detail"]
    assert len(red.st["junit_full"]["failed"]) == 2


def test_full_suite_phase_applies_the_count_floor_of_the_tested_tree(tmp_path):
    floor = math.ceil(100 * cl.SUITE_FLOOR_RATIO)
    assert floor == 95
    below = _suite_inner(tmp_path / "below", 100)
    _run_suite(below, [(0, _junit_text(floor - 1))])
    assert below.results["tests"]["state"] == "failed"
    assert "実行件数 94 が床 95 を下回る" in below.results["tests"]["detail"]
    at = _suite_inner(tmp_path / "at", 100)
    _run_suite(at, [(0, _junit_text(floor))])
    assert at.results["tests"]["state"] == "ok"
    assert sum("全数の件数の床: 実行 95 件 / 床 95 件" in r for r in at.remarks) == 1
    # skip は実行に数えない: 100 件あっても 6 件が skip なら床を割る
    skipped = [("tests.test_opt", f"test_{i}", "optional data not present") for i in range(6)]
    mostly = _suite_inner(tmp_path / "skips", 100)
    _run_suite(mostly, [(0, _junit_text(94, skipped=skipped))])
    assert mostly.results["tests"]["state"] == "failed"
    # 追加引数つきは床を見ない(その代わり、結果に「全数ではない」と書く)
    extra = _suite_inner(tmp_path / "extra", 100, pytest_args=["-k", "smoke"])
    fake = _run_suite(extra, [(0, _junit_text(3))])
    assert extra.results["tests"]["state"] == "ok"
    assert "**追加引数つき(全数ではない)**: `-k smoke`" in extra.results["tests"]["detail"]
    assert fake.calls[0]["cmd"][-2:] == ["-k", "smoke"]
    assert [r for r in extra.remarks if "床" in r] == []
    assert not (extra.state / cl.SKIP_BASELINE_FILE).exists()
    # 壊れた JUnit は、終了コードが 0 でも失敗
    broken = _suite_inner(tmp_path / "broken", 100)
    _run_suite(broken, [(0, None)])
    assert broken.results["tests"]["state"] == "failed" and "JUnit が無い" in broken.results["tests"]["detail"]


BLAS_CASES = [("tests.test_blas_a", "test_one", "needs a BLAS with >= 4 threads"),
              ("tests.test_blas_a", "test_two", "needs a BLAS with >= 4 threads"),
              ("tests.test_blas_b.TestX", "test_three", "needs a BLAS with >= 3 threads")]
BLAS_IDS = [(c, n) for c, n, _ in BLAS_CASES]


def _blas_inner(tmp_path: Path, with_files: bool = True):
    inner = _suite_inner(tmp_path, 100)
    if with_files:
        (inner.repo / "tests").mkdir()
        for name in ("test_blas_a.py", "test_blas_b.py"):
            (inner.repo / "tests" / name).write_text("", encoding="utf-8")
    return inner


def test_blas_rerun_runs_the_skipped_files_serially_without_the_thread_limits(tmp_path):
    inner = _blas_inner(tmp_path)
    fake = _run_suite(inner, [(0, _junit_text(97, skipped=BLAS_CASES)),
                              (0, _junit_text(0, ran=[*BLAS_IDS, ("tests.test_blas_a", "test_other")]))])
    assert inner.results["tests"]["state"] == "ok"
    assert len(fake.calls) == 2
    full, again = fake.calls
    assert sorted(k for k in full["env"] if k.endswith("_NUM_THREADS")) == [
        "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS"]
    assert [k for k in again["env"] if k.endswith("_NUM_THREADS")] == []
    assert len(again["env"]) == len(full["env"]) - 4
    assert again["cmd"][-2:] == ["tests/test_blas_a.py", "tests/test_blas_b.py"]
    assert "-n" not in again["cmd"] and again["log"] == "blas.log"
    blas = inner.st["blas"]
    assert (blas["first"], blas["recovered"], blas["still_skipped"], blas["absent"]) == (3, 3, 0, 0)
    # BLAS と関係の無い skip では回し直さない
    plain = _suite_inner(tmp_path / "plain", 100)
    fake = _run_suite(plain, [(0, _junit_text(97, skipped=[("tests.test_opt", "test_x", "optional data")]))])
    assert len(fake.calls) == 1 and "blas" not in plain.st


def test_blas_rerun_that_fails_makes_the_full_suite_phase_fail(tmp_path):
    # 回し直した 3 件は走ったが、同じファイルの別のテストが落ちて exit 1
    inner = _blas_inner(tmp_path / "red")
    fake = _run_suite(inner, [(0, _junit_text(97, skipped=BLAS_CASES)), (1, _junit_text(0, ran=BLAS_IDS, failed=1))])
    assert len(fake.calls) == 2
    res = inner.results["tests"]
    assert res["state"] == "failed" and "BLAS を絞らない回し直しが失敗(exit 1、blas.log)" in res["detail"]
    assert inner.st["blas"]["recovered"] == 3
    # 回し直しが JUnit を書かなかった
    lost = _blas_inner(tmp_path / "lost")
    _run_suite(lost, [(0, _junit_text(97, skipped=BLAS_CASES)), (0, None)])
    assert lost.results["tests"]["state"] == "failed"
    assert "BLAS を絞らない回し直しが失敗(exit 0、blas.log)" in lost.results["tests"]["detail"]
    assert (lost.st["blas"]["recovered"], lost.st["blas"]["absent"]) == (0, 3)


def test_blas_rerun_that_still_does_not_run_the_tests_makes_the_phase_fail(tmp_path):
    # 回し直しは exit 0。ただし 1 件は skip のまま、1 件は回し直しに現れない
    inner = _blas_inner(tmp_path / "stuck")
    rerun = _junit_text(0, ran=BLAS_IDS[:1], skipped=BLAS_CASES[1:2])
    _run_suite(inner, [(0, _junit_text(97, skipped=BLAS_CASES)), (0, rerun)])
    res = inner.results["tests"]
    assert res["state"] == "failed"
    assert "BLAS を絞らずに回し直しても 2 件が走らない(skip のまま 1 件・回し直しに現れない 1 件" in res["detail"]
    blas = inner.st["blas"]
    assert (blas["first"], blas["recovered"], blas["still_skipped"], blas["absent"]) == (3, 1, 1, 1)
    # テストのファイルを特定できなければ、回し直せないこと自体が失敗
    nofile = _blas_inner(tmp_path / "nofile", with_files=False)
    fake = _run_suite(nofile, [(0, _junit_text(97, skipped=BLAS_CASES))])
    assert len(fake.calls) == 1
    assert nofile.results["tests"]["state"] == "failed"
    assert "skip 3 件を回し直せなかった" in nofile.results["tests"]["detail"]
    assert (nofile.st["blas"]["recovered"], nofile.st["blas"]["absent"]) == (0, 3)


def test_full_suite_phase_records_skips_and_flags_a_jump_on_the_next_run(tmp_path):
    def skips(n: int, reason: str) -> list:
        return [("tests.test_opt", f"test_{reason[:3]}_{i}", reason) for i in range(n)]

    base = skips(10, "optional data not present")
    first = _suite_inner(tmp_path, 1000)
    _run_suite(first, [(0, _junit_text(990, skipped=base))])
    record = first.state / cl.SKIP_BASELINE_FILE
    assert first.results["tests"]["state"] == "ok"
    assert json.loads(record.read_text(encoding="utf-8"))["skipped"] == 10
    assert sum("最初の記録にした" in r for r in first.remarks) == 1
    # +21 件(線は +20): 床は割らないので ok のまま、要約の先頭で知らせる。記録は増える前のまま
    jumped = _suite_inner(tmp_path, 1000)
    _run_suite(jumped, [(0, _junit_text(969, skipped=base + skips(21, "could not import 'torch'")))])
    assert jumped.results["tests"]["state"] == "ok"
    assert "10 → 31 件(+21。知らせる線は +20)" in jumped.st["skip_jump"]
    assert "+21 件「could not import 'torch'」" in jumped.st["skip_jump"]
    assert json.loads(record.read_text(encoding="utf-8"))["skipped"] == 10
    # +20 件ちょうどは知らせず、記録を更新する
    edge = _suite_inner(tmp_path, 1000)
    _run_suite(edge, [(0, _junit_text(970, skipped=base + skips(20, "could not import 'torch'")))])
    assert "skip_jump" not in edge.st
    assert sum("skip の前回比: 10 → 30 件" in r for r in edge.remarks) == 1
    assert json.loads(record.read_text(encoding="utf-8"))["skipped"] == 30
    # 床を割った run の件数は、次回の比べる相手にしない
    low = _suite_inner(tmp_path / "low", 1000)
    _run_suite(low, [(0, _junit_text(10))])
    assert low.results["tests"]["state"] == "failed"
    assert not (low.state / cl.SKIP_BASELINE_FILE).exists()


def _lint_inner(tmp_path: Path, with_ruff: bool = True, **job_over):
    inner = cl.Inner(_job(state_dir=str(tmp_path / "state"), out=str(tmp_path / "out"), **job_over))
    (inner.repo / "tools").mkdir(parents=True)
    (inner.repo / "tools" / "pip_audit_gate.py").write_text("", encoding="utf-8")
    (inner.venv_lint / "bin").mkdir(parents=True)
    for name in ("python", "ruff") if with_ruff else ("python",):
        (inner.venv_lint / "bin" / name).write_text("", encoding="utf-8")
    inner.check_python = lambda venv, which: "3.11.9"
    inner.capture = lambda cmd, env=None: "ruff 9.9.9"
    return inner


def _run_lint(inner, ruff_rc: int, audit_rc: int, pip_rc: int = 0) -> _FakeRun:
    def handler(cmd, log):
        if "tools/pip_audit_gate.py" in cmd:
            return audit_rc
        if cmd[-2:] == ["check", "."]:
            return ruff_rc
        return pip_rc

    inner.run = fake = _FakeRun(handler)
    inner.phase_lint()
    return fake


LINT_OUTCOMES = [
    ("both-ok", 0, 0, "ok", ["ruff 9.9.9 ok", "pip-audit ok"]),
    ("pip-audit-found-something", 0, 1, "failed", ["ruff 9.9.9 ok", "pip-audit 失敗(exit 1、pip-audit.log"]),
    ("pip-audit-could-not-run", 0, 2, "failed", ["pip-audit 失敗(exit 2、pip-audit.log"]),
    ("ruff-failed", 1, 0, "failed", ["ruff 9.9.9 失敗(exit 1、ruff.log)", "pip-audit ok"]),
]


@pytest.mark.parametrize("ruff_rc,audit_rc,state,texts", [c[1:] for c in LINT_OUTCOMES],
                         ids=[c[0] for c in LINT_OUTCOMES])
def test_lint_phase_follows_the_exit_codes_of_ruff_and_pip_audit(ruff_rc, audit_rc, state, texts, tmp_path):
    inner = _lint_inner(tmp_path)
    fake = _run_lint(inner, ruff_rc, audit_rc)
    res = inner.results["lint"]
    assert res["state"] == state
    assert [t for t in texts if t not in res["detail"]] == []
    audits = [c for c in fake.calls if "tools/pip_audit_gate.py" in c["cmd"]]
    assert len(audits) == 1
    assert audits[0]["cmd"][1:] == ["tools/pip_audit_gate.py", *cl.PIP_AUDIT_ARGS]
    assert (audits[0]["log"], audits[0]["cwd"]) == ("pip-audit.log", inner.repo)
    ruffs = [c for c in fake.calls if c["cmd"][-2:] == ["check", "."]]
    assert len(ruffs) == 1 and (ruffs[0]["log"], ruffs[0]["cwd"]) == ("ruff.log", inner.repo)
    assert len(fake.calls) == 4  # pip の更新・ruff と pip-audit を入れる・ruff・pip-audit


def test_lint_phase_says_when_pip_audit_was_left_out_or_ruff_is_not_the_latest(tmp_path):
    skipped = _lint_inner(tmp_path / "no-audit", pip_audit=False)
    fake = _run_lint(skipped, 0, 1)
    assert skipped.results["lint"]["state"] == "ok"
    assert "pip-audit **未実行**(--no-pip-audit)" in skipped.results["lint"]["detail"]
    assert [c for c in fake.calls if "tools/pip_audit_gate.py" in c["cmd"]] == []
    installs = [c["cmd"] for c in fake.calls if "-U" in c["cmd"]]
    assert len(installs) == 1 and installs[0][-1] == cl.RUFF_PIN and cl.PIP_AUDIT_PIN not in installs[0]
    assert len(fake.calls) == 3
    stale = _lint_inner(tmp_path / "stale")
    _run_lint(stale, 0, 0, pip_rc=1)
    assert stale.results["lint"]["state"] == "ok"
    assert "**最新に上げられなかった**" in stale.results["lint"]["detail"]
    missing = _lint_inner(tmp_path / "no-ruff", with_ruff=False)
    fake = _run_lint(missing, 0, 0)
    assert missing.results["lint"]["state"] == "failed"
    assert "ruff を入れられなかった" in missing.results["lint"]["detail"] and len(fake.calls) == 2


def test_capture_returns_the_output_of_a_command():
    import sys

    assert cl.Inner.capture(None, [sys.executable, "-c", "print('ruff 1.2.3')"]) == "ruff 1.2.3"
    assert cl.Inner.capture(None, [sys.executable, "-c", "import sys; sys.exit(3)"]) == ""


def _gate_inner(tmp_path: Path, present: int):
    inner = cl.Inner(_job(state_dir=str(tmp_path / "state"), out=str(tmp_path / "out")))
    inner.full_env = lambda name: {"PATH": "/venv/bin"}
    gates = [g.split("::", 1)[0] for g in cl.BUILTIN_GATES]
    for rel in gates[:present]:
        (inner.repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (inner.repo / rel).write_text("", encoding="utf-8")
    return inner


def _run_phase(inner, name: str, script) -> _FakeRun:
    inner.run = fake = _FakeRun(_pytest_script(script))
    getattr(inner, name)()
    return fake


def test_gate_phase_fails_on_exit_code_unusable_junit_or_a_missing_gate(tmp_path):
    n = len(cl.BUILTIN_GATES)
    ok = _gate_inner(tmp_path / "ok", n)
    fake = _run_phase(ok, "phase_gates", [(0, _junit_text(40))])
    assert ok.results["gates"] == dict(ok.results["gates"], state="ok", detail="ok — 40 件")
    cmd = fake.calls[0]["cmd"]
    assert cmd[-n:] == list(cl.BUILTIN_GATES) and cmd[-n - 4:-n] == ["-n", "2", "--dist", "load"]
    assert "内蔵の写し" in ok.st["gates_source"]
    red = _gate_inner(tmp_path / "red", n)
    _run_phase(red, "phase_gates", [(1, _junit_text(39, failed=1))])
    assert red.results["gates"]["state"] == "failed" and "exit 1、gates.log" in red.results["gates"]["detail"]
    lost = _gate_inner(tmp_path / "lost", n)
    _run_phase(lost, "phase_gates", [(0, None)])
    assert lost.results["gates"]["state"] == "failed" and "JUnit が無い" in lost.results["gates"]["detail"]
    short = _gate_inner(tmp_path / "short", n - 1)
    _run_phase(short, "phase_gates", [(0, _junit_text(40))])
    assert short.results["gates"]["state"] == "failed"
    assert "一覧にあって実在しない門 1 本" in short.results["gates"]["detail"]
    none = _gate_inner(tmp_path / "none", 0)
    fake = _run_phase(none, "phase_gates", [])
    assert none.results["gates"]["state"] == "failed" and fake.calls == []
    # 検査した木に一覧のファイルがあれば、内蔵の写しでなくそれを使う
    listed = _gate_inner(tmp_path / "listed", 2)
    (listed.repo / cl.GATES_FILE).parent.mkdir(parents=True, exist_ok=True)
    (listed.repo / cl.GATES_FILE).write_text("# 門\n" + "\n".join(cl.BUILTIN_GATES[:2]) + "\n", encoding="utf-8")
    fake = _run_phase(listed, "phase_gates", [(0, _junit_text(7))])
    assert listed.results["gates"]["state"] == "ok" and fake.calls[0]["cmd"][-2:] == list(cl.BUILTIN_GATES[:2])
    assert "内蔵の写し" not in listed.st["gates_source"] and "2 本" in listed.st["gates_source"]


def test_regen_phase_follows_the_exit_code(tmp_path):
    ok = _gate_inner(tmp_path / "ok", 0)
    ok.run = fake = _FakeRun(lambda cmd, log: 0)
    ok.phase_regen()
    assert ok.results["regen"]["state"] == "ok"
    assert len(fake.calls) == 1
    assert fake.calls[0]["cmd"][-2:] == ["tools/regen_all.py", "--check"] and fake.calls[0]["log"] == "regen.log"
    red = _gate_inner(tmp_path / "red", 0)
    red.run = _FakeRun(lambda cmd, log: 1)
    red.phase_regen()
    assert red.results["regen"]["state"] == "failed" and "exit 1、regen.log" in red.results["regen"]["detail"]


def _core_inner(tmp_path: Path):
    inner = cl.Inner(_job(state_dir=str(tmp_path / "state"), out=str(tmp_path / "out")))
    inner.make_venv = lambda venv: None
    inner.check_python = lambda venv, which: "3.11.9"
    return inner


def test_core_phase_stops_at_the_first_failing_step_and_needs_both_junits(tmp_path):
    def handler_failing_at(step: int | None, write_junit: bool):
        seen = []

        def handler(cmd, log):
            seen.append(cmd)
            target = [a.split("=", 1)[1] for a in cmd if a.startswith("--junitxml=")]
            if target and write_junit:
                Path(target[0]).write_text(_junit_text(4), encoding="utf-8")
            return 1 if len(seen) == step else 0

        return handler

    ok = _core_inner(tmp_path / "ok")
    ok.run = fake = _FakeRun(handler_failing_at(None, True))
    ok.phase_core()
    assert ok.results["core"]["state"] == "ok"
    assert len(fake.calls) == 17
    assert sorted({c["log"] for c in fake.calls}) == ["core.log"]
    red = _core_inner(tmp_path / "red")
    red.run = fake = _FakeRun(handler_failing_at(9, True))
    red.phase_core()
    assert red.results["core"]["state"] == "failed" and len(fake.calls) == 9
    assert "wheel: sdist→wheel(core.log)" in red.results["core"]["detail"]
    lost = _core_inner(tmp_path / "lost")
    lost.run = fake = _FakeRun(handler_failing_at(None, False))
    lost.phase_core()
    assert lost.results["core"]["state"] == "failed" and len(fake.calls) == 17
    assert lost.results["core"]["detail"].count("JUnit が無い") == 2


# ---- 内側: main(段の並びと result.json)------------------------------------------------------

def _main_inner(tmp_path: Path, outcomes: dict, **job_over):
    import time

    inner = cl.Inner(_job(state_dir=str(tmp_path / "state"), out=str(tmp_path / "out"), **job_over))
    ran: list[str] = []

    def synced() -> None:
        inner.tested = MERGED
        inner.tree["tested"] = MERGED

    def phase(key: str):
        def go() -> None:
            ran.append(key)
            outcome = outcomes.get(key, True)
            if isinstance(outcome, Exception):
                raise outcome
            inner.set_result(key, outcome, "", time.time())

        return go

    inner.claim_state_dir = outcomes.get("claim", lambda: None)
    inner.probe_tools = lambda: inner.st.update(tools_missing=[], apt_missing=[], tools_probed=True)
    inner.sync_repo = synced
    inner.clean_tree = lambda: None
    inner.verify_tree = lambda when: None
    inner.phase_lint, inner.phase_regen, inner.phase_gates = phase("lint"), phase("regen"), phase("gates")
    inner.phase_core, inner.phase_tests = phase("core"), phase("tests")
    return inner, ran


def _finished(inner) -> tuple[dict, str]:
    return (json.loads((inner.out / "result.json").read_text(encoding="utf-8")),
            (inner.out / "summary.md").read_text(encoding="utf-8"))


def test_inner_main_writes_a_verdict_that_tells_green_from_the_other_zero_exits(tmp_path, monkeypatch):
    monkeypatch.setattr(cl.platform, "freedesktop_os_release", lambda: {"PRETTY_NAME": "TestOS"}, raising=False)
    inner, ran = _main_inner(tmp_path / "ok", {})
    assert inner.main() == 0 and ran == list(cl.PHASE_KEYS)
    result, summary = _finished(inner)
    assert (result["verdict"], result["exit_code"], result["partial"], result["deviations"]) == ("full_ok", 0, [], [])
    assert "- 結論: **全段 ok**(5 段)" in summary and "TestOS" in summary

    inner, ran = _main_inner(tmp_path / "no-fetch", {}, tree=_tree(fetched="no_fetch"))
    assert inner.main() == 0 and ran == list(cl.PHASE_KEYS)
    result, summary = _finished(inner)
    assert (result["verdict"], result["exit_code"], len(result["deviations"])) == ("deviating_ok", 0, 1)
    assert "**全段 ok**" not in summary and "GitHub の CI とは違う条件での検査" in summary

    inner, ran = _main_inner(tmp_path / "only", {}, only="lint", selected=["lint"])
    assert inner.main() == 0 and ran == ["lint"]
    result, summary = _finished(inner)
    assert (result["verdict"], result["partial"]) == ("partial_ok", ["--only lint"])
    assert summary.count("未実行(--only lint)") == 4


def test_inner_main_stops_at_the_first_failed_phase_unless_told_to_keep_going(tmp_path, monkeypatch):
    monkeypatch.setattr(cl.platform, "freedesktop_os_release", lambda: {"PRETTY_NAME": "TestOS"}, raising=False)
    inner, ran = _main_inner(tmp_path / "stop", {"regen": False})
    assert inner.main() == 1 and ran == ["lint", "regen"]
    result, summary = _finished(inner)
    assert (result["verdict"], result["exit_code"]) == ("failed", 1)
    assert summary.count("未実行(regen_all --check が落ちて止めた") == 3

    inner, ran = _main_inner(tmp_path / "keep", {"regen": RuntimeError("boom")}, keep_going=True)
    assert inner.main() == 1 and ran == list(cl.PHASE_KEYS)
    result, summary = _finished(inner)
    assert result["verdict"] == "failed"
    states = [result["results"][k]["state"] for k in cl.PHASE_KEYS]
    assert states == ["ok", "failed", "ok", "ok", "ok"]
    assert "段が途中で止まった: RuntimeError: boom" in result["results"]["regen"]["detail"]

    def busy() -> None:
        raise cl.Busy("状態ディレクトリを別の ci_local が使っている")

    inner, ran = _main_inner(tmp_path / "busy", {"claim": busy})
    assert inner.main() == cl.EXIT_BUSY and ran == []
    result, summary = _finished(inner)
    assert (result["verdict"], result["exit_code"]) == ("busy", 3)
    assert "- 結論: **実行していない**" in summary

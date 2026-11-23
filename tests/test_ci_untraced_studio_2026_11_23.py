# -*- coding: utf-8 -*-
"""Studio の tracer 非依存の停止・時間試験が、専用 CI から抜けないための門。"""
from __future__ import annotations

import ast
import os

import yaml


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNTRACED_LIST = "tools/ci_untraced_tests.txt"
UNTRACED_JOB = "untraced"
HELPER_NAME = "requires_no_external_tracer"
EXPECTED_CALLERS = {
    "tests/test_studio_pyedit_2026_11_12.py::test_watch_shows_evaluating_then_stuck_and_stops_auto_reevaluation",
    "tests/test_studio_pyedit_2026_11_12.py::test_watch_job_logic_without_qt",
    "tests/test_studio_program_check_2026_11_12.py::test_500_lines_are_checked_quickly",
    "tests/test_studio_python_mode_2026_11_13.py::test_7_infinite_loop_is_stopped",
    "tests/test_studio_python_mode_review_2026_11_13.py::test_h3_an_abandoned_run_blocks_the_next_run_and_is_restored_again_when_it_ends",
    "tests/test_studio_python_mode_review_2026_11_13.py::test_h3_the_window_says_that_the_earlier_run_is_still_running",
    "tests/test_studio_python_mode_review2_2026_11_13.py::test_r5_helper_threads_do_not_pile_up_and_their_changes_are_put_back",
    "tests/test_studio_python_mode_review2_2026_11_13.py::test_r5_a_run_is_not_started_while_a_value_helper_thread_is_left",
    "tests/test_studio_python_mode_review2_2026_11_13.py::test_r7_the_next_run_waits_until_the_late_restore_of_an_abandoned_run_is_done",
    "tests/test_studio_python_mode_review3_2026_11_15.py::test_s1_a_selection_that_cannot_be_stopped_is_put_back_when_it_ends",
    "tests/test_bench_ops.py::test_smoke_run_is_fast_enough_for_ci",
}


def _listed_files() -> list[str]:
    path = os.path.join(ROOT, UNTRACED_LIST)
    rows = []
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            row = raw.split("#", 1)[0].strip()
            if row:
                rows.append(row.replace("\\", "/"))
    return rows


def _helper_callers() -> set[str]:
    callers = set()
    test_dir = os.path.join(ROOT, "tests")
    for name in sorted(os.listdir(test_dir)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        rel = "tests/" + name
        tree = ast.parse(open(os.path.join(test_dir, name), encoding="utf-8").read(), filename=rel)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
                continue
            if any(isinstance(call, ast.Call)
                   and isinstance(call.func, ast.Attribute)
                   and call.func.attr == HELPER_NAME for call in ast.walk(node)):
                callers.add(rel + "::" + node.name)
    return callers


def test_every_untraced_test_is_listed_and_every_listed_file_exists():
    listed = _listed_files()
    assert listed, "tools/ci_untraced_tests.txt lists no test file"
    assert len(listed) == len(set(listed)), listed
    assert all(path.startswith("tests/test_") and path.endswith(".py") for path in listed), listed
    missing = [path for path in listed if not os.path.isfile(os.path.join(ROOT, path))]
    assert not missing, missing
    callers = _helper_callers()
    assert callers == EXPECTED_CALLERS, sorted(callers ^ EXPECTED_CALLERS)
    assert {nodeid.split("::", 1)[0] for nodeid in callers} <= set(listed)


def test_untraced_ci_job_reads_the_list_and_cannot_enable_pytest_cov():
    path = os.path.join(ROOT, ".github", "workflows", "ci.yml")
    with open(path, encoding="utf-8") as fh:
        jobs = yaml.safe_load(fh)["jobs"]
    job = jobs[UNTRACED_JOB]
    assert job["needs"] == "changes"
    assert job["if"] == "needs.changes.outputs.docs-only != 'true'"
    assert job["env"]["FULLSEYE_REQUIRE_UNTRACED"] == "1"
    runs = "\n".join(step.get("run", "") for step in job["steps"])
    assert UNTRACED_LIST in runs
    pytest_runs = [step["run"] for step in job["steps"] if "pytest" in step.get("run", "")]
    assert len(pytest_runs) == 2                              # install と実行
    command = pytest_runs[-1]
    assert "pytest -p no:cov -ra" in command
    assert "--cov" not in command

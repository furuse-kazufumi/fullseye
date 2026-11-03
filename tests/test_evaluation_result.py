"""GateResult/CaseResult aggregate failures without changing legacy stdout."""

import pytest

from fullseye.evaluation.result import CaseResult, GateAdapter, GateResult, GateStyle


def test_gate_result_requires_bool_and_case_collects_every_failure():
    gates = [
        GateResult("accuracy", True, 0.2, 0.0, 0.5, "<=", "inside limit"),
        GateResult("repeatability", False, 0.8, 0.0, 0.5, "<=", "outside limit"),
        GateResult("coverage", False, 0.7, 0.95, 0.01, ">=", "too few"),
    ]
    result = CaseResult("case", gates=gates)
    assert not result.passed
    assert [gate.name for gate in result.failures] == ["repeatability", "coverage"]
    with pytest.raises(TypeError, match="must be bool"):
        GateResult("bad", 1)  # type: ignore[arg-type]


def test_gate_adapter_is_the_selected_accumulator_with_exact_style():
    printed = []
    names, failures = [], []
    adapter = GateAdapter(
        style=GateStyle(indent="   ", pass_word="ok", fail_word="NG", detail_prefix=" — "),
        printer=printed.append,
        all_names=names,
        failed_names=failures,
    )
    adapter("first", True, "1.0 mm")
    adapter("second", False)
    assert printed == ["   [ok] first — 1.0 mm", "   [NG] second"]
    assert names == ["first", "second"]
    assert failures == ["second"]
    assert [gate.passed for gate in adapter.results] == [True, False]

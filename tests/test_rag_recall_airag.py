"""Grounded, category-balanced retrieval gates for small-model op selection."""
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from fullseye.opsearch import plan as plan_api, plan_chain, search_ops

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "docs" / "ops" / "rag_benchmark.json"
REPORT = ROOT / "docs" / "rag_synonym_gaps.json"


def _data():
    data = json.loads(BENCH.read_text(encoding="utf-8"))
    assert data["queries"], "an empty benchmark must never pass"
    return data


def _recall(found, relevant):
    return len(set(found) & set(relevant)) / len(set(relevant))


# Per-query executable plans, kept so a failing gate shows which queries moved (a bare
# "0.525 >= 0.576" cost a full CI run to investigate on 2026-10-30).
_EXEC_DETAIL: dict = {}


def _measure(rows):
    queries = []
    by_category = defaultdict(lambda: {"search": [], "plan": [], "executable": []})
    for row in rows:
        direct = [x["name"] for x in search_ops(row["query"], 10)["ops"]]
        plan = plan_chain(row["query"], row["start_sort"], row["goal_sort"], k=10, max_depth=4)
        planned = [x["name"] for stage in plan.get("stages", []) for x in stage["candidates"]]
        executable=plan_api(row["start_sort"],row["goal_sort"],goal=row["query"])
        executable_names=[name for p in executable.get("plans",[]) for name in p["ops"]]
        sr, pr = _recall(direct, row["relevant"]), _recall(planned, row["relevant"])
        er=_recall(executable_names,row["relevant"])
        queries.append((row, sr, pr, er))
        _EXEC_DETAIL[row["id"]] = (round(er, 3), [p["ops"] for p in executable.get("plans", [])][:7])
        by_category[row["category"]]["search"].append(sr)
        by_category[row["category"]]["plan"].append(pr)
        by_category[row["category"]]["executable"].append(er)
    avg = lambda xs: sum(xs) / len(xs)
    return queries, {k: {m: avg(v[m]) for m in ("search", "plan", "executable")} for k, v in by_category.items()}


def test_corpus_is_large_balanced_and_multilingual():
    rows = _data()["queries"]
    assert len(rows) >= 40
    counts = Counter(r["category"] for r in rows)
    assert len(counts) >= 5 and min(counts.values()) >= 5, counts
    langs = {r["lang"] for r in rows}
    assert {"ja", "en", "zh", "ko", "de"} <= langs
    assert sum(r["lang"] == "ja" for r in rows) > len(rows) / 2
    assert len({r["id"] for r in rows}) == len(rows)


def test_every_answer_has_true_poc_evidence_at_the_claimed_line():
    for row in _data()["queries"]:
        assert 1 <= len(row["relevant"]) <= 5
        assert set(row["evidence"]) == set(row["relevant"])
        for op, ref in row["evidence"].items():
            rel, sep, line_text = ref.rpartition(":")
            assert sep and line_text.isdigit(), (row["id"], ref)
            path, line_no = ROOT / rel, int(line_text)
            assert path.is_file() and (rel.startswith("examples/") or rel.startswith("examples_3d/"))
            lines = path.read_text(encoding="utf-8").splitlines()
            assert 1 <= line_no <= len(lines)
            assert op in lines[line_no - 1], "%s: claimed evidence line does not contain %s" % (ref, op)


def test_per_query_category_and_overall_recall_gates():
    data = _data()
    queries, cats = _measure(data["queries"])
    overall_search = sum(q[1] for q in queries) / len(queries)
    overall_plan = sum(q[2] for q in queries) / len(queries)
    overall_executable = sum(q[3] for q in queries) / len(queries)
    gate = data["thresholds"]
    assert overall_plan >= gate["overall_plan"]["minimum"]
    assert overall_executable >= gate["overall_executable_plan"]["minimum"], (
        overall_executable, {k: v for k, v in _EXEC_DETAIL.items() if v[0] < 1.0})
    for name, limits in gate["categories"].items():
        assert cats[name]["plan"] >= limits["minimum"], (name, cats[name])
        if name != "general":
            assert cats[name]["plan"] >= cats[name]["search"], (name, cats[name])
    # Every query value is retained in the generated report, not hidden by averages.
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["categories"]["general"]["plan_recall_at_10"] == pytest.approx(cats["general"]["plan"])
    got = {r["id"]: r for r in report["queries"]}
    for row, sr, pr, er in queries:
        assert got[row["id"]]["search_recall_at_10"] == pytest.approx(sr)
        assert got[row["id"]]["plan_recall_at_10"] == pytest.approx(pr)
        assert got[row["id"]]["executable_plan_recall_at_10"] == pytest.approx(er)


def test_synonym_gap_generated_artifact_is_current():
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["n_queries"] == len(_data()["queries"])
    expected = {q["id"] for q in report["queries"] if q["missed_by_search"]}
    assert {g["id"] for g in report["synonym_gaps"]} == expected
    assert expected, "the gap report must not become vacuously empty"


def _validate_rows(rows):
    assert rows, "an empty benchmark must never pass"

def test_gate_rejects_empty_and_one_query_regression():
    with pytest.raises(AssertionError):
        _validate_rows([])
    data = _data()
    rows = [dict(r) for r in data["queries"]]
    # One full miss changes macro recall by 1/40=0.025; the overall margin is
    # exactly smaller than that, so a single currently-correct query must fail.
    measured, _ = _measure(rows)
    victim = next(i for i, (_, _, pr, _er) in enumerate(measured) if pr == 1.0)
    rows[victim] = dict(rows[victim], relevant=["no_such_operator_for_mutation_gate"])
    changed, _ = _measure(rows)
    score = sum(q[2] for q in changed) / len(changed)
    assert score < data["thresholds"]["overall_plan"]["minimum"]

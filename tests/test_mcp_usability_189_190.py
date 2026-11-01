"""LLM-free acceptance gates for MCP usability issues #189 and #190."""
from __future__ import annotations

import numpy as np

from fullseye.mcp.catalog import Catalog
from fullseye.mcp.handles import HandleStore
from fullseye.mcp.server import (
    MINIMAL_TOOLS,
    OP_EXECUTION_TOOLS,
    call_tool,
    physical_parameter_catalog,
    validate_pipeline,
)
from fullseye.opsearch import plan, search_ops


def _inside(spec: dict) -> float:
    choices = spec.get("choices")
    if choices:
        return float(choices[len(choices) // 2])
    lo, hi = float(spec["min"]), float(spec["max"])
    value = (lo + hi) / 2.0
    return float(round(value)) if spec.get("kind") == "int" else value


def _outside(spec: dict) -> float:
    choices = spec.get("choices")
    if choices:
        return max(float(x) for x in choices) + 2.0
    return float(spec["max"]) + max(1.0, abs(float(spec["max"])) * 0.1)


def test_named_physical_parameters_are_ledger_enumerated_and_fail_closed_for_every_op():
    cat = Catalog.load()
    ledger = physical_parameter_catalog()
    assert len(ledger) == 14
    for op, named in ledger.items():
        for name, spec in named.items():
            good = validate_pipeline([{"op": op, "params": {name: _inside(spec)}}], "image", cat)
            assert good["valid"], (op, name, good["errors"])
            normalized = good["stages"][0]
            assert name in normalized["named_params"]
            assert 0.0 <= normalized[spec["knob"]] <= 1.0

            bad = validate_pipeline([{"op": op, "params": {name: _outside(spec)}}], "image", cat)
            assert not bad["valid"], (op, name)
            errors = [row for row in bad["errors"]
                      if row["reason"] == "physical_parameter_out_of_range"]
            assert errors and ("not clipped" in errors[0]["detail"] or
                               "not rounded" in errors[0]["detail"])


def test_named_physical_parameter_executes_and_conflicting_ab_is_rejected(tmp_path):
    cat = Catalog.load()
    store = HandleStore(roots=[str(tmp_path)])
    handle = store.put(np.eye(16), sort="image", provenance=[])["handle"]
    result = call_tool("fullseye_apply", {
        "handle": handle, "op": "gaussian", "params": {"sigma_px": 1.2}, "vision": "none",
    }, cat, store)
    assert result["structuredContent"]["named_params"]["sigma_px"]["value"] == 1.2
    try:
        call_tool("fullseye_apply", {
            "handle": handle, "op": "gaussian", "a": 0.2,
            "params": {"sigma_px": 1.2}, "vision": "none",
        }, cat, store)
    except Exception as exc:  # ArgError is intentionally a boundary error
        assert "not both" in str(exc)
    else:  # pragma: no cover - a silent precedence rule would violate fail-closed
        raise AssertionError("a and sigma_px were silently combined")


def test_goal_semantics_change_plan_rank_and_explain_the_exact_boost():
    goals = ("暗い欠陥を抽出", "照明むらを除去", "細い傷を強調")
    tops = []
    for goal in goals:
        result = plan("image", "image", goal=goal, constraints={"k": 7, "max_depth": 2})
        assert result["ok"], goal
        top = result["plans"][0]
        tops.append(top["ops"][0])
        assert top["evidence"]
        assert any(ev["term"] in goal and ev["op"] in top["ops"] and ev["points"] > 0
                   and ev["matched_description"] for ev in top["evidence"])
    assert len(set(tops)) == 3, tops


def test_zero_hit_retry_and_each_search_candidate_has_next_call():
    rescued = search_ops("員数", 3)
    assert rescued["ops"] == []
    assert rescued["retry_queries"] and rescued["retry_ops"]
    assert all(row["retry_query"] in rescued["retry_queries"] for row in rescued["retry_ops"])
    found = search_ops("remove gaussian noise", 3)
    assert found["ops"]
    assert all("fullseye_" in row["next_call"] and "pipeline" in row["next_call"]
               for row in found["ops"])


def test_sort_mismatch_is_structured_with_loader_or_conversion_fix():
    result = validate_pipeline([{"op": "otsu"}], "color", Catalog.load())
    mismatch = next(row for row in result["errors"] if row["reason"] == "sort_mismatch")
    assert mismatch["actual"] == ["color"]
    assert mismatch["expected"] == ["image"]
    assert mismatch["fixes"]
    assert any(fix.get("tool") == "fullseye_load_image" or fix.get("kind") == "conversion"
               for fix in mismatch["fixes"])


def test_unique_high_level_proposal_is_validated_and_ambiguous_query_is_not_chosen():
    cat = Catalog.load()
    exact = call_tool("fullseye_suggest_pipeline", {
        "query": "gaussian", "start_sort": "image", "goal_sort": "image",
    }, cat)["structuredContent"]
    assert exact["unique"] and exact["validation"]["valid"]
    assert exact["pipeline"]["stages"] == [{"op": "gaussian"}]
    ambiguous = call_tool("fullseye_suggest_pipeline", {
        "query": "filter image", "start_sort": "image", "goal_sort": "image",
    }, cat)["structuredContent"]
    assert not ambiguous["unique"] and "pipeline" not in ambiguous


def test_template_handle_is_required_and_drives_positioning_pipeline(tmp_path):
    scene = np.zeros((48, 48), dtype=np.float64)
    template = np.array([[0, 1, 0], [1, 1, 0], [0, 0, 1]], dtype=np.float64)
    scene[20:23, 31:34] = template
    scene_path, template_path = tmp_path / "scene.npy", tmp_path / "template.npy"
    np.save(scene_path, scene)
    np.save(template_path, template)
    cat, store = Catalog.load(), HandleStore(roots=[str(tmp_path)])
    sh = call_tool("fullseye_load_image", {"path": str(scene_path), "vision": "none"},
                   cat, store)["structuredContent"]["handle"]
    th = call_tool("fullseye_load_template", {"path": str(template_path), "vision": "none"},
                   cat, store)["structuredContent"]
    assert th["role"] == "template"
    refused = call_tool("fullseye_pipeline", {
        "handle": sh, "stages": [{"op": "ncc_locate"}], "vision": "none",
    }, cat, store)
    assert refused["isError"] and refused["structuredContent"]["reason"] == "missing_template_handle"
    matched = call_tool("fullseye_pipeline", {
        "handle": sh, "template_handle": th["handle"],
        "stages": [{"op": "ncc_locate"}], "vision": "none",
    }, cat, store)["structuredContent"]
    record = matched["stages"][0]
    assert record["status"] == "ok" and record["op"] == "ncc_locate"
    assert record["value"][0] > 0.9


def test_new_tools_stay_in_minimal_profile_without_broadening_op_execution_allowlist():
    assert {"fullseye_load_template", "fullseye_suggest_pipeline"} <= MINIMAL_TOOLS
    assert OP_EXECUTION_TOOLS == {"fullseye_apply", "fullseye_pipeline"}

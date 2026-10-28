"""Contracts for chain planning, compact cards, probe evidence, and validation."""
from fullseye.mcp.catalog import Catalog
from fullseye.mcp.server import call_tool, validate_pipeline
from fullseye.opsearch import op_cards, plan_chain, search_ops


def test_search_and_plan_expose_probe_without_filtering_failures():
    found = search_ops("gaussian blur", 5)["ops"]
    assert found
    flags = ["probe" in row and "status" in row["probe"] for row in found]
    assert flags == [True] * len(found)
    plan = plan_chain("extract image features", "image", "feature", k=5)
    assert plan["found"] and plan["stages"]
    candidates = plan["stages"][0]["candidates"]
    assert candidates
    flags = ["probe" in row for row in candidates]
    assert flags == [True] * len(candidates)


def test_cards_stop_at_whole_operator_boundary():
    one = op_cards(["gaussian"], 1000)
    cost = one["cards"][0]["tokens"]
    none = op_cards(["gaussian"], cost - 1)
    assert none["cards"] == [] and none["used_tokens"] == 0 and none["truncated"]
    exact = op_cards(["gaussian", "otsu"], cost)
    assert [c["name"] for c in exact["cards"]] == ["gaussian"]


def test_validator_is_fail_closed_and_suggests_typo_repair():
    cat = Catalog.load()
    bad = validate_pipeline([{"op": "gausian", "a": 2.0}], "image", cat)
    assert not bad["valid"]
    reasons = {e["reason"] for e in bad["errors"]}
    assert {"unknown_op"} <= reasons
    assert bad["errors"][0]["candidates"]
    mismatch = validate_pipeline([{"op": "otsu"}, {"op": "gaussian"}], "image", cat)
    errors = mismatch["errors"]
    assert errors
    hits = [e for e in errors if e["reason"] == "sort_mismatch" and e["stage"] == 2]
    assert hits


def test_validation_mcp_returns_machine_readable_error():
    cat = Catalog.load()
    result = call_tool("fullseye_validate_pipeline",
                       {"start_sort": "image", "stages": [{"op": "no_such_op"}]}, cat)
    assert result["isError"] is True
    assert result["structuredContent"]["errors"][0]["reason"] == "unknown_op"

"""Deterministic CI gates for the LLM-free side of mcp_agent_eval."""
from __future__ import annotations

from collections import Counter

from tools import mcp_agent_eval as evaluation


def _event(op, *, value=None, mean=None, std=None, shape=None):
    stats = {}
    if mean is not None:
        stats["mean"] = mean
    if std is not None:
        stats["std"] = std
    if shape is not None:
        stats["shape"] = shape
    record = {"op": op, "status": "ok", "stats": stats}
    if value is not None:
        record["value"] = value
    return {"tool": "fullseye_pipeline", "is_error": False,
            "result": {"structuredContent": {"stages": [record]}}}


def _passing_events(task, prepared):
    judge = task["judge"]
    if judge == "judge_component_count":
        return [_event("count_obj", value=prepared.truth["count"])]
    if judge == "judge_region_fraction":
        return [_event("otsu", mean=prepared.truth["fraction"])]
    if judge == "judge_smoothed_std":
        return [_event("gaussian", std=prepared.truth["max_std"] * 0.8)]
    if judge == "judge_feature_count":
        return [_event("cv_good_features", shape=[prepared.truth["min_features"] + 1, 2])]
    if judge == "judge_match_position":
        return [_event("ncc_locate", value=[0.99, prepared.truth["y"], prepared.truth["x"]])]
    if judge == "judge_dolp_mean":
        return [_event("polarization_dolp_map", mean=prepared.truth["mean"])]
    if judge == "judge_phase_mean":
        return [_event("wrapped_phase", mean=prepared.truth["mean"])]
    if judge == "judge_depth_mean":
        return [_event("decode_fringe", mean=prepared.truth["mean"])]
    raise AssertionError(judge)


def test_task_source_has_five_balanced_categories_and_no_op_names_in_requests():
    data = evaluation.load_tasks()
    assert len(data["tasks"]) >= 20
    counts = Counter(task["category"] for task in data["tasks"])
    assert set(counts) == set(evaluation.CATEGORIES)
    assert min(counts.values()) >= 4
    for task in data["tasks"]:
        request = task["request"]
        assert not any(op in request for op in evaluation.EXPECTED_OPS[task["judge"]])


def test_every_generator_is_byte_deterministic_and_truth_is_stable(tmp_path):
    data = evaluation.load_tasks()
    for task in data["tasks"]:
        first = evaluation.generate_task_input(task, tmp_path / "first")
        second = evaluation.generate_task_input(task, tmp_path / "second")
        assert first.sha256 == second.sha256, task["id"]
        assert first.truth == second.truth, task["id"]
        assert first.files == second.files


def test_every_named_judge_is_deterministic_and_accepts_its_synthetic_truth(tmp_path):
    data = evaluation.load_tasks()
    for task in data["tasks"]:
        prepared = evaluation.generate_task_input(task, tmp_path)
        events = _passing_events(task, prepared)
        first = evaluation.judge_task(task, prepared, events)
        second = evaluation.judge_task(task, prepared, events)
        assert first == second
        assert first["passed"], (task["id"], first)


def test_real_mcp_server_lists_required_tools_and_reads_every_task_input():
    result = evaluation.validate_inputs(evaluation.load_tasks())
    assert result == {"tasks": 20, "mcp": "ok"}

"""経路の検査(fullseye.explain_pipeline と MCP の dry_run)の門 / Gates for the pipeline route inspector.

経路表だけで決まる部分(``assume_cuda=True``)は GPU の無い CI でも常に走る。既知のレシピで切り替わりの数と
往復の見込みが期待どおりか、型の切れ目を run_pipeline と同じ規則で言うか、生成物(レシピ全部の表)が
作り直したものと同じかを見る。
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

import api
import fullseye

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHAPE = (2048, 2048)


def plan(stages, **kw):
    kw.setdefault("assume_cuda", True)
    return fullseye.explain_pipeline(stages, SHAPE, **kw)


@pytest.mark.parametrize("stages, n_switches, n_transfers, cpu_ops", [
    (["gaussian", "otsu", "fill_up", "count_obj"], 0, 1, []),                    # Count — blobs: 全段 GPU
    (["otsu", "sk_clear_border", "count_obj"], 0, 1, []),                        # FA — count holes
    (["gaussian", "otsu", "fill_up", "remove_small"], 0, 1, []),                 # Segment — blob / coin
    (["gaussian", "sk_rolling_ball", "threshold", "select_shape"], 0, 1, []),   # FA — scratch: 全段 GPU
    (["gaussian", "sk_dog", "threshold", "select_shape"], 2, 2, ["sk_dog"]),      # 途中に GPU 経路の無い段
    (["gaussian", "hx_plane_deviation", "threshold", "select_shape"], 2, 3, []),  # torch -> CuPy -> torch
])
def test_known_recipes_switch_where_expected(stages, n_switches, n_transfers, cpu_ops):
    p = plan(stages)
    assert p["n_switches"] == n_switches and p["n_transfers"] == n_transfers, p["switches"]
    assert [s["op"] for s in p["stages"] if s["on"] == "cpu"] == cpu_ops
    assert p["type_breaks"] == []
    assert p["n_gpu_stages"] + p["n_cpu_stages"] == len(stages)


def test_switch_reasons_name_the_stage_and_the_cause():
    p = plan(["gaussian", "sk_dog", "threshold", "select_shape"])
    assert p["switches"] == [
        {"at": 1, "op": "sk_dog", "from": "accel", "to": "cpu", "reason": "not_listed"},
        {"at": 2, "op": "threshold", "from": "cpu", "to": "accel", "reason": None}]
    assert "not_listed" in p["reasons"]
    p = plan(["gaussian", "hx_plane_deviation", "threshold"])
    assert [s["reason"] for s in p["switches"]] == ["engine_change", "engine_change"]
    p = plan(["count_obj"])                                     # 鎖の枠だけの経路を単独で
    assert p["stages"][0]["reason"] == "chain_only" and p["n_transfers"] == 0


def test_crossover_is_reported_at_small_sizes():
    p = fullseye.explain_pipeline(["gaussian"], (32, 32), assume_cuda=True)
    assert p["stages"][0]["on"] == "cpu" and p["stages"][0]["reason"] == "crossover"


def test_type_breaks_follow_run_pipeline():
    p = plan(["gaussian", "count_obj"])
    assert p["type_breaks"] == [{"index": 1, "op": "count_obj", "reason": "sort_mismatch",
                                 "expected": "region", "got": "image"}]
    with pytest.raises(ValueError, match="type mismatch"):
        api.run_pipeline(np.zeros((16, 16)), ["gaussian", "count_obj"], device="cpu")
    p = plan(["gaussian", "no_such_op"])
    assert p["type_breaks"][0]["reason"] == "unknown_op"
    assert plan(["gaussian", "otsu", "count_obj"])["type_breaks"] == []


def test_stage_forms_are_the_run_pipeline_forms():
    a = plan("gaussian,otsu,count_obj")
    b = plan([("gaussian", .3, .5), {"op": "otsu"}, ("count_obj",)])
    assert [s["op"] for s in a["stages"]] == [s["op"] for s in b["stages"]] == ["gaussian", "otsu", "count_obj"]
    assert a["switches"] == b["switches"]


def test_without_a_gpu_nothing_is_on_the_gpu(monkeypatch):
    monkeypatch.delenv("FULLSEYE_DEVICE", raising=False)
    monkeypatch.setattr(api, "cuda_available", lambda: False)
    p = fullseye.explain_pipeline(["gaussian", "otsu", "count_obj"], SHAPE)
    assert p["decision"]["reason"] == "no_cuda" and p["n_gpu_stages"] == 0 and p["n_transfers"] == 0
    assert p["n_switches"] == 0


def test_rejected_family_ops_say_why():
    p = plan(["otsu", "convexity"])
    assert p["stages"][1]["on"] == "cpu" and p["stages"][1]["reason"] == "not_listed"
    assert p["stages"][1]["detail"] == "accel:slower_than_cpu_even_resident"


def test_explain_pipeline_never_runs_an_op(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("explain_pipeline must not run anything")
    monkeypatch.setattr(api, "apply", boom)
    monkeypatch.setattr(api, "run_pipeline", boom)
    plan(["gaussian", "otsu", "count_obj"])


def test_generated_route_table_is_current():
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "gen_gpu_routes.py"), "--check"], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    table = json.loads((ROOT / "docs" / "perf" / "pipeline_routes.json").read_text(encoding="utf-8"))
    after, before = table["summary"]["after"], table["summary"]["before"]
    assert after["recipes"] >= 12 and after["stages"] >= 37                     # 空を通さない
    assert after["gpu_stages"] >= before["gpu_stages"] and after["switches"] <= before["switches"]


# ---- MCP: fullseye_pipeline の dry_run -------------------------------------------------------------
def _store_with(image):
    from fullseye.mcp.handles import HandleStore
    store = HandleStore(roots=[], max_bytes=100_000_000)
    return store, store.put(image, sort="image", provenance=[])["handle"]


def test_mcp_pipeline_dry_run_returns_the_plan_without_running(monkeypatch):
    from fullseye.mcp import Catalog, call_tool
    calls = []
    monkeypatch.setattr(api, "apply", lambda *a, **k: calls.append(1))
    store, h = _store_with(np.random.default_rng(0).random((64, 64)))
    res = call_tool("fullseye_pipeline", {"handle": h, "dry_run": True, "assume_cuda": True,
                                          "stages": [{"op": "gaussian"}, {"op": "otsu"}, {"op": "count_obj"}]},
                    Catalog.load(), store)
    assert not res["isError"] and calls == []
    plan_ = res["structuredContent"]["plan"]
    assert res["structuredContent"]["dry_run"] is True
    assert plan_["shape"] == [64, 64] and [s["op"] for s in plan_["stages"]] == ["gaussian", "otsu", "count_obj"]
    assert {"switches", "type_breaks", "n_transfers", "segments"} <= set(plan_)


def test_mcp_pipeline_schema_only_adds_arguments():
    from fullseye.mcp.server import TOOLS
    props = TOOLS["fullseye_pipeline"]["inputSchema"]["properties"]
    assert props["dry_run"]["type"] == "boolean" and props["assume_cuda"]["type"] == "boolean"
    assert TOOLS["fullseye_pipeline"]["inputSchema"]["required"] == ["handle", "stages"]

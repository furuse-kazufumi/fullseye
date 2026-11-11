# -*- coding: utf-8 -*-
"""MCP の入口で、AI が課題のファイルを見つけ・正しい形で段を書けるようにした修正の門(2026-11-08)。

Gates for the MCP fixes found while scoring AI-built inspections (examples/poc_ai_built_inspection_scored.py):
the AI could not see the task's files in ``list_samples``, a missing file gave no readable names, the validator
accepted knob values the pipeline refuses, ``a``/``b`` inside ``params`` gave no fix, and the operators a person
reaches for (``bothat`` / ``hx_plane_deviation``) never surfaced for crack and stain queries.
"""
from __future__ import annotations

import os

import numpy as np
import pytest
from PIL import Image

from fullseye.mcp.catalog import Catalog
from fullseye.mcp.handles import SAMPLE_DIR, HandleError, HandleStore
from fullseye.mcp.server import call_tool, validate_pipeline


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


@pytest.fixture()
def store(tmp_path):
    for name in ("crack_dev_defect_1.png", "crack_dev_good_1.png"):
        Image.fromarray(np.full((8, 8), 120, np.uint8)).save(tmp_path / name)
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")
    return HandleStore(roots=[SAMPLE_DIR, str(tmp_path)]), tmp_path


def test_list_samples_returns_the_task_files_without_host_paths(cat, store):
    st, root = store
    res = call_tool("fullseye_list_samples", {}, cat, st)["structuredContent"]
    assert res["files"] == ["crack_dev_defect_1.png", "crack_dev_good_1.png"]   # 画像だけ、相対名
    assert res["samples"], "同梱サンプルも従来どおり返す"
    text = repr(res)
    assert str(root) not in text and os.path.basename(str(root)) not in text


def test_root_files_lists_the_root_and_one_level_below_and_hides_dot_names(tmp_path):
    def img(p):
        p.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(np.zeros((4, 4), np.uint8)).save(p)
    img(tmp_path / "x.png")
    img(tmp_path / "a" / "y.png")
    img(tmp_path / "a" / "b" / "z.png")            # 2 段下は出さない
    img(tmp_path / ".hidden.png")
    img(tmp_path / ".d" / "w.png")
    st = HandleStore(roots=[SAMPLE_DIR, str(tmp_path)])
    assert sorted(st.root_files()) == ["a/y.png", "x.png"]


def test_a_missing_file_is_refused_with_the_nearest_readable_names(cat, store):
    st, root = store
    with pytest.raises(HandleError) as exc:
        st.load("crack_defect_1.png")
    msg = str(exc.value)
    assert "ファイルが無い" in msg
    near = msg.split("読める名前(近い順): ", 1)[1].split(", ")
    assert near[0] == "crack_dev_defect_1.png"
    assert 1 <= len(near) <= 8
    assert str(root) not in msg
    # 名前が分かれば読める(従来どおり)
    assert st.load("crack_dev_defect_1.png")["sort"] == "image"


def test_the_validator_refuses_knobs_the_pipeline_refuses(cat):
    for bad in ({"a": 128}, {"b": -0.1}, {"a": "0.5"}, {"a": True}):
        r = validate_pipeline([{"op": "threshold", **bad}], "image", cat)
        assert r["valid"] is False, bad
        assert [e["reason"] for e in r["errors"]] == ["knob_out_of_range"], (bad, r["errors"])
    for ok in ({"a": 0}, {"a": 1.0, "b": 0.0}, {}):
        r = validate_pipeline([{"op": "threshold", **ok}], "image", cat)
        assert r["valid"] is True, (ok, r["errors"])
    # 範囲外の段があっても、続く段の型の検査は続ける(余計な連鎖の誤りを作らない)
    r = validate_pipeline([{"op": "threshold", "a": 9}, {"op": "select_shape", "a": 0.5}], "image", cat)
    assert [e["reason"] for e in r["errors"]] == ["knob_out_of_range"]
    assert r["out_sort"] == "region"


def test_knobs_inside_params_get_a_fix_not_just_a_refusal(cat):
    r = validate_pipeline([{"op": "gaussian", "params": {"a": 0.5, "b": 0.5}}], "image", cat)
    err = r["errors"][0]
    assert err["reason"] == "unknown_parameter"
    assert "段の直下" in err["detail"]
    r = validate_pipeline([{"op": "gaussian", "params": {"sigmaa": 1.0}}], "image", cat)
    assert "detail" not in r["errors"][0]                     # a/b でない誤りには添えない


@pytest.mark.parametrize("query, want", [
    ("コンクリートのひび割れを検出", {"bothat", "hx_plane_deviation"}),
    ("crack detection", {"hx_plane_deviation"}),
    ("ろうそくの表面の汚れ・欠けを見つける", {"bothat"}),
])
def test_crack_and_stain_queries_reach_the_operators_a_person_uses(cat, query, want):
    st = HandleStore(roots=[])
    ops = [o["name"] for o in call_tool("fullseye_find_ops", {"query": query, "limit": 8}, cat, st)
           ["structuredContent"]["ops"]]
    assert ops, query
    assert want <= set(ops), (query, ops)

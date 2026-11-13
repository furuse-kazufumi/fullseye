# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""AI の役で MCP を使った検証(2026-11-13)の報告 2〜13 番と C の回帰試験。

報告の現象を 1 件ずつ再現してから直した。各試験の docstring に、直す前に何が起きていたかを書く。
"""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fullseye.mcp import server as S                              # noqa: E402
from fullseye.mcp.catalog import Catalog                          # noqa: E402
from fullseye.mcp.handles import HandleStore                      # noqa: E402
from fullseye.mcp.opworker import close_worker                    # noqa: E402


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


@pytest.fixture()
def store(tmp_path):
    return HandleStore(thumb_dir=str(tmp_path / "thumb"))


@pytest.fixture(scope="module", autouse=True)
def _close_shared_worker():
    yield
    close_worker()


def _text(result):
    return result["content"][0]["text"]


# --------------------------------------------------------------------------- 2: 失敗の本文に段番号と理由
def test_validation_failure_text_names_every_stage_and_reason(cat, store):
    """直す前: fullseye_validate_pipeline の不合格の本文は「error」と「stages=0」だけで、理由は structuredContent にしか無かった。"""
    r = S.call_tool("fullseye_validate_pipeline", {"stages": [
        {"op": "lockin_thermal_wave"}, {"op": "no_such_op_xyz"}]}, cat, store)
    text = _text(r)
    lines = text.splitlines()
    assert lines[0].startswith("検証: 不合格(誤り 2 件")
    assert lines[1].startswith("段 1 lockin_thermal_wave: not_executable_in_mcp") and "代わりに" in lines[1]
    assert lines[2].startswith("段 2 no_such_op_xyz: unknown_op")
    ok = S.call_tool("fullseye_validate_pipeline", {"start_sort": "image", "stages": [{"op": "otsu"}]}, cat, store)
    assert _text(ok).startswith("検証: 合格(1 段") and "段 1 otsu: image -> region" in _text(ok)


def test_pipeline_type_error_message_lists_stage_and_fix(cat, store):
    """直す前: -32602 の本文は最初の誤りの JSON を 1 行に繋いだ物だった。"""
    h = S.call_tool("fullseye_load_image", {"path": "coins"}, cat, store)["structuredContent"]["handle"]
    with pytest.raises(S.ArgError) as err:
        S.call_tool("fullseye_pipeline", {"handle": h, "stages": [{"op": "otsu"}, {"op": "gaussian"}]}, cat, store)
    msg = str(err.value)
    assert "段 2 gaussian: sort_mismatch" in msg and "来たのは region、要るのは image" in msg
    assert "直し方の候補" in msg and "1 段も走らせていない" in msg and not msg.lstrip().startswith("{")


def test_strict_failure_text_has_one_line_per_stage(cat, store):
    """直す前: 段が失敗した時の本文は、結果の JSON を丸ごと 1 行に繋いでいた。"""
    r = S.call_tool("fullseye_pipeline", {"stages": [
        {"op": "illumination_design", "params": {"surface": "no such surface"}}]}, cat, store)
    assert r["isError"]
    lines = _text(r).splitlines()
    assert lines[0] == "段 1 illumination_design failed in strict mode: execution_failed"
    assert lines[1].startswith("段 1 illumination_design: 失敗 execution_failed — ValueError:")
    assert "動く見本" in _text(r) and "{\"completed\"" not in _text(r)


# --------------------------------------------------------------------------- 3: 入力を読まない op を提案と plan から外す
def test_fixes_and_plans_never_route_through_ops_that_ignore_their_input(cat, store):
    """直す前: image → region の直し方の候補が hx_gen_empty_region(入力の中身を見ない生成の op)で、
    従った gaussian → sobel_amp → hx_gen_empty_region → count_obj が 0.0 を判定 ok で返した。"""
    from fullseye.opsearch import _input_independent_names, plan
    blind = _input_independent_names()
    assert "hx_gen_empty_region" in blind and len(blind) >= 20
    checked = S.validate_pipeline([{"op": "gaussian"}, {"op": "otsu"}, {"op": "sobel_amp"}, {"op": "count_obj"}],
                                  "image", cat, store=store)
    fixes = [f for e in checked["errors"] for m in e.get("value", []) if isinstance(m, dict)
             for f in m.get("fixes", []) if f.get("kind") == "conversion"]
    assert fixes, checked["errors"]
    used = {op for f in fixes for op in f["ops"]}
    assert used and not (used & blind), used & blind
    routes = plan("image", "region", constraints={"k": 10, "max_depth": 3})
    assert routes.get("ok") and routes["plans"]
    ops_in_plans = {op for pl in routes["plans"] for op in pl["ops"]}
    assert ops_in_plans and not (ops_in_plans & blind), ops_in_plans & blind


# --------------------------------------------------------------------------- 4: 実行できない op の誤り文と「近い名前」
def test_alternatives_share_a_name_word_and_the_name_is_not_its_own_neighbour(cat, store):
    """直す前: fullseye_apply は台帳の op にも「registry 層に無い」とだけ返し、「近い名前」に同じ名前を出した。
    代わりの op は、同じ分類で名前の語を共有する物だけ(共有しなければ並べない)。"""
    from fullseye.opsearch import mcp_unavailable
    lens = mcp_unavailable("lens_file_read")["executable_alternatives"]
    assert len(lens) >= 3
    assert all(set(name.split("_")) & {"lens", "file", "read"} for name in lens)
    thermal = mcp_unavailable("lockin_thermal_wave")
    assert thermal["reason"] == "sample_run_failed"
    alternatives = thermal["executable_alternatives"]
    assert len(alternatives) <= 5
    assert not [n for n in alternatives if not set(n.split("_")) & {"lockin", "thermal", "wave"}]
    h = S.call_tool("fullseye_load_image", {"path": "coins"}, cat, store)["structuredContent"]["handle"]
    with pytest.raises(S.ArgError) as err:
        S.call_tool("fullseye_apply", {"handle": h, "op": "lockin_phase"}, cat, store)
    assert "'lockin_phase'(registry 層に無い)" in str(err.value)
    assert "近い名前: ['lockin_phase'" not in str(err.value) and "op_run('lockin_phase'" in str(err.value)

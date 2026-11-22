# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MCP find_ops で、走らない op が走る検索結果を上位から押し出した回帰の試験(2026-11-22)。

PR #322 の後、日本語のステレオ距離の問いで MCP で走らない op が上位 5 件中 4 件を占め、走る
``binocular_disparity_ms`` が 6 位になった。検索本体の順位は変えず、MCP の返事だけを有界に並べ直す。
"""
import itertools
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (ROOT, os.path.dirname(os.path.abspath(__file__)), os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fullseye.mcp import server as S                       # noqa: E402
from fullseye.mcp.catalog import Catalog                   # noqa: E402
from fullseye.mcp.handles import HandleStore               # noqa: E402

_OP_LIMIT = 5
_TOTAL_LIMIT = 7
_NON_RUNNABLE_AHEAD = 4
_EXHAUSTIVE_LIMIT = 3
_POOL_EXTRA_ROWS = 3


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


@pytest.fixture()
def store(tmp_path):
    return HandleStore(thumb_dir=str(tmp_path / "thumb"))


def test_prefer_mcp_executable_boundedly_demotes_non_runnable_rows_without_mutating_input():
    from fullseye.opsearch import MCP_NONEXECUTABLE_DEMOTION_SLOTS, prefer_mcp_executable

    non_runnable_names = ["N%d" % i for i in range(_NON_RUNNABLE_AHEAD)]
    executable_name = "E4"
    rows = [{"name": name, "score": float(_OP_LIMIT - i)}
            for i, name in enumerate(non_runnable_names + [executable_name])]
    original_rows = [dict(row) for row in rows]
    result = prefer_mcp_executable(rows, {executable_name}, _OP_LIMIT)

    insertion = _NON_RUNNABLE_AHEAD - MCP_NONEXECUTABLE_DEMOTION_SLOTS
    expected_names = non_runnable_names[:insertion] + [executable_name] + non_runnable_names[insertion:]
    assert [row["name"] for row in result] == expected_names
    assert result[insertion]["executable"] is True
    assert all(row["executable"] is False for row in result if row["name"] in non_runnable_names)
    assert set(non_runnable_names) <= {row["name"] for row in result}
    assert rows == original_rows and all("executable" not in row for row in rows)
    input_by_name = {row["name"]: row for row in rows}
    assert all(row is not input_by_name[row["name"]] for row in result)


def test_prefer_mcp_executable_preserves_class_order_and_never_moves_a_row_too_far():
    from fullseye.opsearch import MCP_NONEXECUTABLE_DEMOTION_SLOTS, prefer_mcp_executable

    names = ["E0", "N1", "N2", "N3", "E4", "N5"]
    runnable = {"E0", "E4"}
    rows = [{"name": name} for name in names]
    unchanged = prefer_mcp_executable(rows, runnable, len(rows), slots=0)
    result = prefer_mcp_executable(rows, runnable, len(rows))

    assert [row["name"] for row in unchanged] == names
    assert [row["name"] for row in result if row["executable"]] == ["E0", "E4"]
    assert [row["name"] for row in result if not row["executable"]] == ["N1", "N2", "N3", "N5"]
    new_positions = {row["name"]: i for i, row in enumerate(result)}
    assert all(i - new_positions[name] <= MCP_NONEXECUTABLE_DEMOTION_SLOTS
               for i, name in enumerate(names) if name in runnable)
    assert new_positions["E4"] == names.index("E4") - MCP_NONEXECUTABLE_DEMOTION_SLOTS


def test_prefer_mcp_executable_rejects_invalid_limits_and_slots():
    from fullseye.opsearch import prefer_mcp_executable

    rows = [{"name": "E0"}]
    for invalid_limit in (0, -1, True, 1.5):
        with pytest.raises(ValueError, match="limit"):
            prefer_mcp_executable(rows, {"E0"}, invalid_limit)
    for invalid_slots in (-1, True):
        with pytest.raises(ValueError, match="slots"):
            prefer_mcp_executable(rows, {"E0"}, _OP_LIMIT, slots=invalid_slots)


def test_mcp_search_pool_is_sufficient_for_every_executable_class_pattern():
    from fullseye.opsearch import (MCP_NONEXECUTABLE_DEMOTION_SLOTS, mcp_search_pool,
                                  prefer_mcp_executable)

    pool = mcp_search_pool(_EXHAUSTIVE_LIMIT)
    assert pool == _EXHAUSTIVE_LIMIT + MCP_NONEXECUTABLE_DEMOTION_SLOTS
    pattern_length = pool + _POOL_EXTRA_ROWS
    rows = [{"name": "op%d" % i} for i in range(pattern_length)]
    for pattern in itertools.product((False, True), repeat=pattern_length):
        runnable = {row["name"] for row, executable in zip(rows, pattern) if executable}
        complete = prefer_mcp_executable(rows, runnable, _EXHAUSTIVE_LIMIT)
        pooled = prefer_mcp_executable(rows[:pool], runnable, _EXHAUSTIVE_LIMIT)
        assert complete == pooled, pattern


def test_find_ops_keeps_a_runnable_op_in_the_mcp_result(monkeypatch, cat, store):
    """直す前: 検索の順のまま先頭の op 行数だけを返し、切り捨て位置のすぐ外(PR #322 の例では 6 位)の走る op が
    消えた。走らない op を op 行数ぶん前に置き、走る op をその次に置く。"""
    import fullseye.opsearch as O
    from fssystem import get_system

    recipe_limit = max(0, min(get_system("find_ops_recipe_max"), _TOTAL_LIMIT - 1))
    expected_op_rows = _TOTAL_LIMIT - recipe_limit
    edges = O._graph()["edges"]
    non_runnable = [edge["op"] for edge in edges if not edge.get("verified_executable")][:expected_op_rows]
    runnable = next(edge["op"] for edge in edges if edge.get("verified_executable"))
    assert len(non_runnable) == expected_op_rows
    ordered_names = non_runnable + [runnable]
    ordered_names += [edge["op"] for edge in edges
                      if not edge.get("verified_executable") and edge["op"] not in ordered_names]

    def fake_search_ops(query, k=None, *, lang=None, in_sort=None, out_sort=None, **_kwargs):
        rows = [{"name": op, "in_sort": "image", "out_sort": "image", "summary": "summary",
                 "score": float(len(ordered_names) - i), "next_call": "next"}
                for i, op in enumerate(ordered_names)]
        return {"ok": True, "reason": "ok", "query": query, "lang": lang, "total": len(rows),
                "ops": rows[:k], "hint": ""}

    monkeypatch.setattr(O, "search_ops", fake_search_ops)
    result = S.call_tool("fullseye_find_ops", {"query": "stereo distance", "limit": _TOTAL_LIMIT}, cat, store)
    structured = result["structuredContent"]
    assert len(structured["ops"]) == expected_op_rows
    by_name = {row["name"]: row for row in structured["ops"]}
    assert runnable in by_name, [row["name"] for row in structured["ops"]]
    assert by_name[runnable]["executable"] is True
    assert any(row["executable"] is False for row in structured["ops"])
    proposal_marks = {row["name"]: row["executable"] for row in structured["proposals"]
                      if row["kind"] == "op"}
    assert proposal_marks == {row["name"]: row["executable"] for row in structured["ops"]}


def test_find_ops_executable_only_marks_every_kept_row_executable(cat, store):
    structured = S.call_tool("fullseye_find_ops", {"query": "lens", "executable_only": True},
                             cat, store)["structuredContent"]
    rows = structured["ops"] + structured.get("retry_ops", [])
    assert rows and all(row["executable"] is True for row in rows)


def test_find_ops_executable_only_caps_retry_ops_at_the_op_rows(monkeypatch, cat, store):
    """直す前(独立レビュー 2026-11-22): executable_only の retry_ops は op 行数で切られず、search_ops が多めに
    作った retry 行(既定で最大 op 行数の 8 倍)がそのまま返った。"""
    import fullseye.opsearch as O
    from fssystem import get_system

    recipe_limit = max(0, min(get_system("find_ops_recipe_max"), _TOTAL_LIMIT - 1))
    expected_op_rows = _TOTAL_LIMIT - recipe_limit
    runnable = [edge["op"] for edge in O._graph()["edges"] if edge.get("verified_executable")]
    assert len(runnable) > expected_op_rows

    def fake_search_ops(query, k=None, *, lang=None, **_kwargs):
        rows = [{"name": op, "in_sort": "image", "out_sort": "image", "summary": "summary",
                 "score": 1.0, "next_call": "next", "retry_query": "retry"} for op in runnable[:k]]
        return {"ok": True, "reason": "operators found by deterministic retry", "query": query, "lang": lang,
                "total": 0, "ops": [], "hint": "", "retry_ops": rows}

    monkeypatch.setattr(O, "search_ops", fake_search_ops)
    structured = S.call_tool("fullseye_find_ops", {"query": "stereo distance", "limit": _TOTAL_LIMIT,
                                                   "executable_only": True}, cat, store)["structuredContent"]
    assert 0 < len(structured["retry_ops"]) <= expected_op_rows

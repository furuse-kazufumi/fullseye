# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MCP の JSON 入出口 —— fullseye_import_json(引数で封筒を受けハンドル化)と
fullseye_export_json(ハンドルの中身を封筒 + Markdown で持ち出す)。fail-closed を門で固定する。"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye  # noqa: E402
from fullseye.mcp import Catalog, call_tool  # noqa: E402
from fullseye.mcp.handles import HandleStore  # noqa: E402
from fullseye.mcp.server import ArgError, MAX_STRUCTURED_BYTES  # noqa: E402


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


def test_import_then_export_round_trips_an_array_bit_for_bit(cat):
    store = HandleStore()
    pts = np.array([[1.5, 2.0], [1.0 / 3.0, np.pi]])
    # 引数はオブジェクトの封筒でも文字列の JSON でもよい
    r = call_tool("fullseye_import_json", {"envelope": fullseye.to_jsonable(pts, "points")}, cat, store)
    assert r["isError"] is False
    h = r["structuredContent"]["handle"]
    assert h and r["structuredContent"]["sort"] == "points"
    r2 = call_tool("fullseye_export_json", {"handle": h}, cat, store)
    assert r2["isError"] is False
    back, sort = fullseye.from_jsonable(r2["structuredContent"])
    assert sort == "points" and np.array_equal(back.view(np.uint8), pts.view(np.uint8))
    assert "structuredContent が JSON 封筒" in r2["content"][0]["text"]


def test_import_accepts_a_json_string_argument(cat):
    store = HandleStore()
    r = call_tool("fullseye_import_json", {"json": fullseye.to_json((np.eye(3) > 0), "region")}, cat, store)
    assert r["isError"] is False and r["structuredContent"]["handle"]
    _meta, arr = store.get(r["structuredContent"]["handle"])
    assert np.array_equal(arr, np.eye(3))


def test_import_of_a_non_array_sort_returns_a_value_not_a_handle(cat):
    store = HandleStore()
    r = call_tool("fullseye_import_json", {"envelope": fullseye.to_jsonable(2.5, "feature")}, cat, store)
    assert r["isError"] is False
    assert r["structuredContent"]["handle"] is None and r["structuredContent"]["sort"] == "feature"
    val, sort = fullseye.from_jsonable(r["structuredContent"]["value"])
    assert sort == "feature" and val == 2.5


def test_import_is_fail_closed(cat):
    store = HandleStore()
    with pytest.raises(ArgError, match="どちらか一方"):
        call_tool("fullseye_import_json", {"json": "x", "envelope": {}}, cat, store)
    with pytest.raises(ArgError, match="どちらか一方"):
        call_tool("fullseye_import_json", {}, cat, store)
    with pytest.raises(ArgError, match="読めない"):
        call_tool("fullseye_import_json",
                  {"envelope": {"fullseye_sort": "image", "version": 99, "payload": {}}}, cat, store)
    with pytest.raises(ArgError, match="読めない"):
        call_tool("fullseye_import_json", {"json": "{not json"}, cat, store)
    with pytest.raises(ArgError):                                  # 知らない引数
        call_tool("fullseye_import_json", {"envelope": fullseye.to_jsonable(1.0, "feature"), "x": 1}, cat, store)


def test_export_refuses_a_value_too_big_for_json(cat):
    store = HandleStore()
    big = store.put(np.zeros((400, 400)), sort="image", provenance=[])["handle"]
    r = call_tool("fullseye_export_json", {"handle": big}, cat, store)
    assert r["isError"] is True and "上限" in r["content"][0]["text"]
    # 上限内なら通る(小さい画像)
    small = store.put(np.zeros((4, 5)), sort="image", provenance=[])["handle"]
    ok = call_tool("fullseye_export_json", {"handle": small}, cat, store)
    assert ok["isError"] is False and fullseye.from_jsonable(ok["structuredContent"])[1] == "image"


def test_export_refuses_an_unknown_handle_and_a_non_json_sort(cat):
    store = HandleStore()
    with pytest.raises(ArgError):
        call_tool("fullseye_export_json", {"handle": "fullseye://img/deadbeefdeadbeef"}, cat, store)
    weird = store.put(np.zeros((2, 2, 2, 2)), sort="any", provenance=[])["handle"]
    r = call_tool("fullseye_export_json", {"handle": weird}, cat, store)
    assert r["isError"] is True and "JSON 橋が無い" in r["content"][0]["text"]


def test_export_readable_is_exact_and_human_listed(cat):
    store = HandleStore()
    h = store.put(np.array([[0.5, 1.5], [2.5, 3.5]]), sort="matrix", provenance=[])["handle"]
    r = call_tool("fullseye_export_json", {"handle": h, "readable": True}, cat, store)
    assert r["structuredContent"]["payload"]["encoding"] == "list"
    back, _ = fullseye.from_jsonable(r["structuredContent"])
    assert np.array_equal(back, np.array([[0.5, 1.5], [2.5, 3.5]]))

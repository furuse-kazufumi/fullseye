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


# --- fullseye_estimate_distortion(直線群 + K の JSON → 歪み係数)------------------ #
def _distorted_grid_lines(K, dist):
    span = np.linspace(12, 188, 30)
    lines = [fullseye.distort_points(np.column_stack([span, np.full(30, y)]), K, dist).tolist()
             for y in (40, 100, 160)]
    lines += [fullseye.distort_points(np.column_stack([np.full(30, x), span]), K, dist).tolist()
              for x in (40, 100, 160)]
    return lines


def test_estimate_distortion_recovers_coefficients(cat):
    K = fullseye.intrinsic_matrix(0.95 * 200, 0.95 * 200, 99.5, 99.5)
    true = [-0.24, 0.06, 0.0, 0.0, 0.0]
    r = call_tool("fullseye_estimate_distortion",
                  {"lines": _distorted_grid_lines(K, true), "K": K.tolist(),
                   "radial": 2, "tangential": False}, cat)
    assert not r.get("isError")
    d = r["structuredContent"]["dist"]
    assert len(d) == 5 and abs(d[0] - true[0]) < 1e-4 and abs(d[1] - true[1]) < 1e-4
    assert r["structuredContent"]["n_lines"] == 6


def test_estimate_distortion_revalidates_untrusted_lines_and_K(cat):
    K = fullseye.intrinsic_matrix(180.0, 180.0, 99.5, 99.5)
    good = _distorted_grid_lines(K, [-0.2, 0.05, 0.0, 0.0, 0.0])
    # K が 3x3 でない → -32602(ArgError、信頼境界の再検証)
    with pytest.raises(ArgError):
        call_tool("fullseye_estimate_distortion", {"lines": good, "K": [[1, 0], [0, 1]]}, cat)
    # 線が (N,2) でない → -32602
    with pytest.raises(ArgError):
        call_tool("fullseye_estimate_distortion",
                  {"lines": [[[1, 2, 3]] * 4, good[0]], "K": K.tolist()}, cat)
    # 非有限 → -32602
    with pytest.raises(ArgError):
        call_tool("fullseye_estimate_distortion",
                  {"lines": [[[1.0, float("inf")]] * 4] + good[:1], "K": K.tolist()}, cat)
    # 線が 1 本(スキーマ minItems=2)→ -32602
    with pytest.raises(ArgError):
        call_tool("fullseye_estimate_distortion", {"lines": good[:1], "K": K.tolist()}, cat)


def test_estimate_distortion_fail_closed_on_short_line(cat):
    K = fullseye.intrinsic_matrix(180.0, 180.0, 99.5, 99.5)
    good = _distorted_grid_lines(K, [-0.2, 0.05, 0.0, 0.0, 0.0])
    # 各線 3 点未満は estimate_distortion が拒否 → isError(ArgError でなく道具の拒否)
    r = call_tool("fullseye_estimate_distortion",
                  {"lines": [[[1.0, 2.0], [3.0, 4.0]], good[0]], "K": K.tolist()}, cat)
    assert r.get("isError")


# --- apply/pipeline/inspect が小さい型付き結果に jsonio 封筒 + mdio を添える -------- #
def _img_handle(cat, store):
    img = np.zeros((64, 64))
    img[16:48, 16:48] = 1.0
    env = fullseye.to_jsonable(img, "image")
    return call_tool("fullseye_import_json", {"envelope": env}, cat, store)["structuredContent"]["handle"]


def test_pipeline_attaches_json_for_a_small_typed_result(cat):
    store = HandleStore()
    h = _img_handle(cat, store)
    r = call_tool("fullseye_pipeline",
                  {"handle": h, "stages": [{"op": "gaussian"}, {"op": "otsu"}, {"op": "count_obj"}],
                   "vision": "none"}, cat, store)
    sc = r["structuredContent"]
    assert "json" in sc, "小さい型付き最終結果に封筒が添付されていない"
    val, sort = fullseye.from_jsonable(sc["json"])               # bit そのまま戻せる
    assert float(val) == float(sc["value"])                      # 封筒 == 返り値


def test_inspect_attaches_json_for_points_but_not_for_an_image(cat):
    store = HandleStore()
    pts = np.array([[1.5, 2.0], [1.0 / 3.0, np.pi]])
    ph = call_tool("fullseye_import_json",
                   {"envelope": fullseye.to_jsonable(pts, "points")}, cat, store)["structuredContent"]["handle"]
    ins = call_tool("fullseye_inspect", {"handle": ph, "vision": "none"}, cat, store)
    assert "json" in ins["structuredContent"]
    back, _ = fullseye.from_jsonable(ins["structuredContent"]["json"])
    assert np.array_equal(back, pts)                             # 厳密往復
    # 画像は大きいので添付しない(ハンドル/小図で扱う)
    ih = _img_handle(cat, store)
    ins_img = call_tool("fullseye_inspect", {"handle": ih, "vision": "none"}, cat, store)
    assert "json" not in ins_img["structuredContent"]


def test_apply_attaches_markdown_in_the_text_for_a_typed_result(cat):
    store = HandleStore()
    pts = np.array([[1.0, 2.0], [3.0, 4.0]])
    ph = call_tool("fullseye_import_json",
                   {"envelope": fullseye.to_jsonable(pts, "points")}, cat, store)["structuredContent"]["handle"]
    # points に恒等的な op は無いので inspect の text で Markdown 添付を見る
    ins = call_tool("fullseye_inspect", {"handle": ph, "vision": "none"}, cat, store)
    assert "json" in ins["structuredContent"]
    # to_markdown の描画(表 or 要約)が本文に入っている
    assert fullseye.to_markdown(pts, "points").splitlines()[0] in ins["content"][0]["text"]

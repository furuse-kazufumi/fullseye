# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MCP カタログの facade 層は関数だけ(2026-09-20、GenSpark 第 41 報 N141)。

`import fullseye` で呼べる名前を「callable なら op」と数えていたので、クラス 41 個(`Image` / `Pipeline` /
`MissingBackendError` / `TcpChannel` …)が op として検索面に出ていた。クラスとモジュールを除き、
facade 層の全項目が関数であることを問う。同じ報の「facade 表に無い 474 件」は HALCON 対応表との
比較で、実関数 460 本は正当(設計のまま)。
"""
from __future__ import annotations

import inspect
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import fullseye as fs  # noqa: E402
from fullseye.mcp import catalog as C  # noqa: E402
from fullseye.mcp.server import call_tool  # noqa: E402


@pytest.fixture(scope="module")
def cat():
    return C.Catalog.load()


def test_facade_layer_lists_functions_only(cat):
    facade = [n for n, e in cat.entries.items() if "facade" in e.sources]
    assert len(facade) > 900
    classes = [n for n in facade if inspect.isclass(getattr(fs, n, None))]
    assert classes == [], "facade 層にクラスが op として混ざっている: %s" % classes[:10]
    assert all(inspect.isroutine(getattr(fs, n)) or callable(getattr(fs, n)) for n in facade)
    for name in ("Image", "Pipeline", "FullseyeEngine", "MissingBackendError", "VideoPipeline"):
        assert name not in cat.entries, name


def test_search_surface_carries_no_class_names(cat):
    for q in ("Pipeline", "Image", "Channel", "Error"):
        r = call_tool("fullseye_search_ops", {"query": q, "limit": 50}, cat)["structuredContent"]
        hit = [o["name"] for o in r["ops"] if inspect.isclass(getattr(fs, o["name"], None))]
        assert hit == [], (q, hit)


def test_real_facade_functions_stay_searchable(cat):
    """関数を減らしていないこと(クラスだけを除いた): 索引に無い実関数 census_transform / orient2d は残る。"""
    for name in ("census_transform", "orient2d", "point_in_polygon"):
        assert name in cat.entries and "facade" in cat.entries[name].sources, name

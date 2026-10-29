"""Regressions reproduced from the 2026-10-29 on-prem agent conversations."""
import numpy as np
import pytest

from fullseye.mcp.catalog import Catalog
from fullseye.mcp.handles import HandleStore
from fullseye.mcp.server import call_tool, validate_pipeline
from fullseye.opsearch import normalize_sort, plan, search_ops, sort_aliases


# Keep this explicit: adding a new MCP sort boundary must add an assertion here.
SORT_BOUNDARIES = (
    "find_ops.in_sort", "find_ops.out_sort", "plan.have", "plan.want",
    "validate.start_sort", "pipeline.start_sort", "binding.declaration", "load_stack.sort",
)


def test_all_sort_aliases_use_one_normalizer_at_every_boundary(tmp_path):
    assert len(SORT_BOUNDARIES) == 8
    cat = Catalog.load()
    store = HandleStore(roots=[str(tmp_path)])
    handle = store.put(np.zeros((2, 2)), sort="image", provenance=[])["handle"]
    for alias, canonical in sort_aliases().items():
        assert normalize_sort(alias) == normalize_sort(canonical) == canonical
        assert search_ops("image", 1, in_sort=alias) == search_ops("image", 1, in_sort=canonical)
        assert search_ops("image", 1, out_sort=alias) == search_ops("image", 1, out_sort=canonical)
        assert plan([alias], canonical)["have"] == plan([canonical], canonical)["have"]
        assert plan([canonical], alias)["want"] == plan([canonical], canonical)["want"]
        va = validate_pipeline([], alias, cat)
        vc = validate_pipeline([], canonical, cat)
        assert va["start_sort"] == vc["start_sort"] == canonical
        ba = validate_pipeline([], None, cat, bindings={"have:" + alias: handle}, store=store)
        bc = validate_pipeline([], None, cat, bindings={"have:" + canonical: handle}, store=store)
        # The declared name is canonicalized before binding type comparison.
        assert [e["reason"] for e in ba["errors"]] == [e["reason"] for e in bc["errors"]]


def test_conversation_seq_image_aliases_work_at_mcp_entries(tmp_path):
    cat = Catalog.load()
    a = call_tool("fullseye_find_ops", {"query": "frame", "in_sort": "images"}, cat)
    b = call_tool("fullseye_find_ops", {"query": "frame", "in_sort": "seq<image>"}, cat)
    assert a["structuredContent"] == b["structuredContent"]
    p = tmp_path / "x.npy"
    np.save(p, np.zeros((2, 2)))
    store = HandleStore(roots=[str(tmp_path)])
    x = call_tool("fullseye_load_stack", {"paths": [str(p)], "sort": "images"}, cat, store)
    assert x["structuredContent"]["sort"] == "seq<image>"


def test_zero_hit_type_filter_returns_routes_and_typed_unfiltered_top():
    result = search_ops("threshold", 3, in_sort="color", out_sort="region")
    assert result["ops"] == []
    assert 1 <= len(result["conversion_paths"]) <= 2
    assert any(path["from"] == "color" and path["to"] == "image" and
               "rgb1_to_gray" in path["ops"] for path in result["conversion_paths"])
    assert 1 <= len(result["unfiltered_top"]) <= 3
    assert all(set(row) == {"name", "in_sort", "out_sort"} for row in result["unfiltered_top"])
    assert len(str(result).encode("utf-8")) < 3000

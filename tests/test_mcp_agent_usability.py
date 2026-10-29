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


def test_color_request_reports_gray_file_honestly_for_image_and_stack(tmp_path):
    import imgio
    path = tmp_path / "gray.png"
    imgio.save(str(path), np.arange(16, dtype=np.uint8).reshape(4, 4))
    cat, store = Catalog.load(), HandleStore(roots=[str(tmp_path)])
    loaded = call_tool("fullseye_load_image", {"path": str(path), "color": True,
                                                "vision": "none"}, cat, store)["structuredContent"]
    assert loaded["sort"] == "image" and loaded["shape"] == [4, 4]
    assert loaded["note"] == "ファイルは灰色なので image で読んだ"
    forced = call_tool("fullseye_load_image", {"path": str(path), "force_color": True,
                                                "vision": "none"}, cat, store)["structuredContent"]
    assert forced["sort"] == "color" and forced["shape"] == [4, 4, 3]
    stack = call_tool("fullseye_load_stack", {"paths": [str(path)], "sort": "images",
                                               "color": True}, cat, store)["structuredContent"]
    assert stack["sort"] == "seq<image>" and stack["shape"] == [1, 4, 4]
    assert "灰色" in stack["note"]


def test_mcp_load_paths_never_expose_root_or_home(tmp_path):
    import imgio
    root = tmp_path / "private-root"
    root.mkdir()
    path = root / "gray.png"
    imgio.save(str(path), np.zeros((2, 2), dtype=np.uint8))
    cat, store = Catalog.load(), HandleStore(roots=[str(root)])
    success = call_tool("fullseye_load_image", {"path": str(path), "vision": "none"}, cat, store)
    success_text = str(success)
    assert "<root>/gray.png" in success_text
    assert str(root) not in success_text and str(tmp_path.parent) not in success_text
    outside = tmp_path / "secret.png"
    with pytest.raises(Exception) as caught:
        call_tool("fullseye_load_image", {"path": str(outside), "vision": "none"}, cat, store)
    refusal = str(caught.value)
    assert "<outside>/secret.png" in refusal
    assert str(tmp_path) not in refusal and str(root) not in refusal

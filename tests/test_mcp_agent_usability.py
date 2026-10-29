"""Regressions reproduced from the 2026-10-29 on-prem agent conversations."""
import numpy as np
import pytest

from fullseye.mcp.catalog import Catalog
from fullseye.mcp.handles import HandleStore
from fullseye.mcp.server import _tool_error, call_tool, tool_result, validate_pipeline
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


def test_fringe_search_normalizes_the_legacy_index_sort_on_both_sides():
    """OP_SEARCH still says images while OP_GRAPH and the API say seq<image>."""
    legacy = search_ops("fringe depth", 3, in_sort="images", out_sort="depth")
    canonical = search_ops("fringe depth", 3, in_sort="seq<image>", out_sort="depth")
    assert len(legacy["ops"]) == len(canonical["ops"]) > 0
    assert "decode_fringe" in {row["name"] for row in legacy["ops"]}


def test_aliases_keep_result_counts_at_search_plan_validate_and_pipeline_boundaries(tmp_path):
    cat = Catalog.load()
    store = HandleStore(roots=[str(tmp_path)])
    for alias, canonical in sort_aliases().items():
        assert len(search_ops("image", 20, in_sort=alias)["ops"]) == len(
            search_ops("image", 20, in_sort=canonical)["ops"])
        assert len(search_ops("image", 20, out_sort=alias)["ops"]) == len(
            search_ops("image", 20, out_sort=canonical)["ops"])
        assert len(plan(alias, canonical).get("plans", [])) == len(
            plan(canonical, canonical).get("plans", []))
        alias_validation = validate_pipeline([], alias, cat)
        canonical_validation = validate_pipeline([], canonical, cat)
        assert len(alias_validation["errors"]) == len(canonical_validation["errors"])
        alias_handle = store.put(np.zeros((2, 2)), sort=alias, provenance=[])["handle"]
        canonical_handle = store.put(np.ones((2, 2)), sort=canonical, provenance=[])["handle"]
        stages = [{"op": "definitely_unknown", "inputs": []}]
        alias_pipeline = call_tool("fullseye_pipeline", {"handle": alias_handle, "stages": stages}, cat, store)
        canonical_pipeline = call_tool("fullseye_pipeline", {"handle": canonical_handle, "stages": stages}, cat, store)
        assert len(alias_pipeline["structuredContent"]["errors"]) == len(
            canonical_pipeline["structuredContent"]["errors"])


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


def test_structured_results_have_short_useful_text_for_text_only_clients():
    structured = {"ok": True, "reason": "operators found", "total": 9,
                  "ops": [{"name": "otsu"}, {"name": "threshold"}],
                  "handle": "fullseye://img/0123456789abcdef", "out_sort": "region"}
    result = tool_result(str(structured).replace("'", '"'), structured)
    text = result["content"][0]["text"]
    assert "structured result" not in text
    assert text.splitlines() == ["ok: operators found", "total=9 ops=2 top=otsu,threshold",
                                 "handle=fullseye://img/0123456789abcdef sort=region"]
    assert len(text.encode("utf-8")) < 180
    failed = _tool_error('{"valid":false}', {"valid": False, "reason": "sort_mismatch", "stages": []})
    assert failed["content"][0]["text"].startswith("error: sort_mismatch")

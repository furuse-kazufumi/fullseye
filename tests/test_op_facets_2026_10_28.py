import json
from pathlib import Path

from fullseye import opsearch
from fullseye.mcp.server import TOOLS

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    return json.loads((ROOT / "fullseye/data" / name).read_text(encoding="utf-8"))

def test_graph_is_non_vacuous_and_edges_have_sources():
    g=load("OP_GRAPH.json")
    assert len(g["nodes"]) >= 90 and len(g["edges"]) >= 2500
    missing=[e["op"] for e in g["edges"] if not e.get("source") or not e.get("compute",{}).get("source")]
    assert not missing

def test_family_ops_exist_and_properties_have_sources():
    names={e["op"] for e in load("OP_GRAPH.json")["edges"]}
    fs=load("OP_FAMILIES.json")["families"]
    assert len(fs) >= 7 and sum(len(f["ops"]) for f in fs) > 20
    bad=[r["op"] for f in fs for r in f["ops"] if r["op"] not in names or not r["property_sources"]]
    assert not bad

def test_backward_solutions_are_forward_edges():
    r=opsearch.required_inputs("depth", max_depth=3, k=5)
    edges={e["op"] for e in load("OP_GRAPH.json")["edges"]}
    assert r["solutions"]
    bad=[s["path"] for s in r["solutions"] if not set(s["path"]) <= edges]
    assert not bad

def test_unused_knobs_are_not_searchable():
    g=load("OP_GRAPH.json")
    edge=next(e for e in g["edges"] if any(not x.get("used") for x in e["parameters"].values()))
    r=opsearch.param_space(edge["op"], {})
    assert all(not p["search"] for p in r["parameters"].values() if not p["used"])

def test_new_mcp_surfaces_are_declared():
    expected={"fullseye_choose_op","fullseye_required_inputs","fullseye_param_space",
              "fullseye_pipeline_shape","fullseye_patterns","fullseye_sort_guide"}
    assert expected <= set(TOOLS)

def test_shape_pattern_and_sort_queries():
    assert opsearch.pipeline_shape("single","dense_field")["found"]
    assert opsearch.pattern_skeleton("Pipe-and-Filter","image","region")["found"]
    guide=opsearch.sort_guide()
    assert guide["sorts"] and guide["documented_choose_when"] + guide["undocumented_choose_when"] == len(guide["sorts"])

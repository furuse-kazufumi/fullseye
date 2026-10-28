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
    missing=[e["op"] for e in g["edges"] if not e.get("source_ref") or not e.get("compute",{}).get("source_ref")]
    assert not missing

def test_family_ops_exist_and_properties_have_sources():
    names={e["op"] for e in load("OP_GRAPH.json")["edges"]}
    fs=load("OP_FAMILIES.json")["families"]
    assert len(fs) == 7 and sum(len(f["ops"]) for f in fs) >= 17
    bad=[r["op"] for f in fs for r in f["ops"] if r["op"] not in names or not r["membership_source"]]
    assert not bad

def test_backward_solutions_are_forward_edges():
    r=opsearch.required_inputs("depth", max_depth=3, k=5)
    edges={e["op"] for e in load("OP_GRAPH.json")["edges"]}
    assert r["solutions"]
    bad=[s["path"] for s in r["solutions"] if not {x for x in s["path"] if not x.startswith("acquire:")} <= edges]
    assert not bad
    edge_map={e["op"]:e for e in load("OP_GRAPH.json")["edges"]}
    invalid=[]
    for solution in r["solutions"]:
        have=set()
        for name in solution["path"]:
            if name.startswith("acquire:"): have.add(name.split(":",1)[1]); continue
            edge=edge_map[name]
            missing_inputs=[x for x in edge["inputs"] if x!="any" and x not in have]
            if missing_inputs: invalid.append((name,sorted(have)))
            have.add(edge["output"] if edge["output"]!="any" else "depth")
        if "depth" not in have: invalid.append((solution["path"],sorted(have)))
    assert not invalid

def test_unused_knobs_are_not_searchable():
    g=load("OP_GRAPH.json")
    edge=next(e for e in g["edges"] if any(not x.get("used") for x in e["parameters"].values()))
    r=opsearch.param_space(edge["op"], {})
    bad=[p for p in r["parameters"].values() if not p["used"] and p["search"]]
    assert not bad

def test_new_mcp_surfaces_are_declared():
    expected={"fullseye_choose_op","fullseye_required_inputs","fullseye_param_space",
              "fullseye_pipeline_shape","fullseye_sort_guide","fullseye_plan","fullseye_describe","fullseye_choose"}
    assert expected <= set(TOOLS)

def test_shape_pattern_and_sort_queries():
    assert opsearch.pipeline_shape("single","dense_field")["found"]
    assert opsearch.pattern_skeleton("Pipe-and-Filter","image","region")["found"]
    guide=opsearch.sort_guide()
    assert guide["sorts"] and guide["truncated"]
    assert guide["documented_choose_when"] + guide["undocumented_choose_when"] == guide["total"]

def test_graph_population_vocabulary_and_execution_boundary():
    g=load("OP_GRAPH.json")
    idx=json.loads((ROOT/"docs/OP_INDEX.json").read_text(encoding="utf-8"))
    graph_names={e["op"] for e in g["edges"] if not e.get("population_extension_reason")}
    assert graph_names == {e["name"] for e in idx["ops"]}
    assert g["sort_aliases"]["image2d"] == "image" and g["sort_aliases"]["mask"] == "region"
    assert len({e["op"] for e in g["edges"]}) == len(g["edges"])
    assert any(x["op"]=="gaussians_to_voxel" for x in g["diagnostics"]["duplicate_declarations"])
    core=("threshold","canny","gaussian","median","otsu")
    nonexec=[name for name in core if not next(e for e in g["edges"] if e["op"]==name)["executable"]]
    assert not nonexec

def test_six_business_plans_put_grounded_main_op_in_results():
    tasks=[
      ("deflectometry phase slope dent",["image","image"],"normalmap","deflectometry_phase_to_slope"),
      ("polarization scratch","polsweep","image","polarization_dolp_map"),
      ("fringe projection height","images","depth","decode_fringe"),
      ("part positioning","image","match","ncc_locate"),
      ("fast 3d structured light","images","depth","decode_fringe"),
      ("multi product corner","image","feature","cv_good_features")]
    results=[(main,opsearch.plan(have,want,constraints={"query":query,"max_depth":3,"k":5,"executable_only":False}))
             for query,have,want,main in tasks]
    failed=[main for main,r in results if not r["ok"] or not any(main in p["ops"] for p in r["plans"])]
    assert not failed

def test_business_plan_mutation_is_caught(monkeypatch):
    g=load("OP_GRAPH.json"); g["edges"]=[e for e in g["edges"] if e["op"]!="decode_fringe"]
    monkeypatch.setitem(opsearch._CACHE,"json:OP_GRAPH.json",g)
    r=opsearch.plan("images","depth",constraints={"query":"fringe projection height","k":5,"executable_only":False})
    assert not any("decode_fringe" in p["ops"] for p in r.get("plans",[]))

def test_family_negative_examples_and_cpu_measurements():
    f=load("OP_FAMILIES.json"); members={x["name"]:{r["op"] for r in x["ops"]} for x in f["families"]}
    assert "thin_lens" not in members["morphology"]
    assert "holdout_threshold" not in members["thresholding"]
    timing=json.loads((ROOT/"docs/ops/families_timing.json").read_text(encoding="utf-8"))
    measured=[r for r in timing["measurements"].values() if r["status"]=="measured"]
    assert measured and all(r.get("complexity_exponent") is not None for r in measured)

def test_knob_schema_context_edges_and_system_params():
    assert opsearch.param_space("lowpass",{"width":512})["parameters"]["a"]["search"]
    assert opsearch.param_space("local_std",{"width":512})["parameters"]["a"]["enum"] == [0.0,0.25,0.49,0.75,1.0]
    one=opsearch.param_space("median",{"width":1,"height":1})
    assert one["parameters"]["a"]["max"] == 0.0
    params=opsearch.system_params()["params"]
    assert params and all(r["hide_from_ai"] and r["source"] for r in params.values())

def test_mcp_minimal_profile_is_eight_tools_and_patterns_are_hidden():
    from fullseye.mcp.server import handle_tools_list
    r=handle_tools_list({"profile":"minimal"}); assert len(r["tools"])==8 and r["estimated_tokens"] < 2000
    full=handle_tools_list({"profile":"full"}); assert "fullseye_patterns" not in {x["name"] for x in full["tools"]}

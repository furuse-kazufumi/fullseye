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
    retired={"fullseye_plan_chain","fullseye_required_inputs","fullseye_pipeline_shape",
             "fullseye_sort_guide","fullseye_param_space","fullseye_choose_op"}
    assert retired.isdisjoint(TOOLS)
    assert {"fullseye_plan","fullseye_describe","fullseye_choose"} <= set(TOOLS)

def test_shape_pattern_and_sort_queries():
    assert opsearch.pipeline_shape("single","dense_field")["found"]
    assert not opsearch.pattern_skeleton("Pipe-and-Filter","image","region")["found"]
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

def test_any_is_split_and_unknown_edges_are_not_planned():
    g=load("OP_GRAPH.json")
    assert "any" not in {n["sort"] for n in g["nodes"]}
    invalid_semantics=[e["op"] for e in g["edges"] if e["type_semantics"] not in {"typed","poly","unknown","source"}]
    assert invalid_semantics == []
    unknown={e["op"] for e in g["edges"] if e["type_semantics"]=="unknown"}
    r=opsearch.plan("image","pose",goal="register",constraints={"executable_only":False,"k":20})
    planned={op for p in r.get("plans",[]) for op in p["ops"]}
    assert planned.isdisjoint(unknown)
    invalid_consumption=[e["op"] for e in g["edges"] if e["consumes_input"] != bool(e["inputs"])]
    assert invalid_consumption == []

def test_nary_registry_declarations_are_exact_and_duplicate_is_explained():
    g=load("OP_GRAPH.json"); idx=load("OP_INDEX.json")
    edges={e["op"]:e for e in g["edges"]}
    nary=[r for r in idx["ops"] if r.get("tier")=="nary"]
    assert nary
    mismatches=[r["name"] for r in nary if edges[r["name"]]["inputs"] != r["in_sorts"]]
    assert mismatches == []
    duplicate=next(x for x in g["diagnostics"]["duplicate_declarations"] if x["op"]=="gaussians_to_voxel")
    assert duplicate["exemption"]

def test_bundle_types_are_nodes_and_only_grounded_elementwise_ops_are_lifted():
    g=load("OP_GRAPH.json")
    assert "seq<image>" in {n["sort"] for n in g["nodes"]}
    equivalence={e["op"] for e in g["edges"] if e["category"]=="type_equivalence"}
    assert equivalence == {"type::images_to_seq_image","type::seq_image_to_images"}
    edges={e["op"]:e for e in g["edges"]}
    unsafe=[r["base_op"] for r in g["lifted_map_edges"]
            if edges[r["base_op"]]["bundle_semantics"] != "elementwise"]
    assert unsafe == []
    forbidden=[r["base_op"] for r in g["lifted_map_edges"]
               if r["base_op"].startswith(("aug_","tb_random_")) or r["base_op"] in {"equalize","autocontrast","autolevel"}]
    assert forbidden == []

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
    assert all(all("dag" in p and p["dag"]["outputs"] for p in r["plans"]) for _,r in results)

def test_hypergraph_plan_is_bounded_and_shared_by_both_directions():
    forward=opsearch.plan("images","depth",goal="fringe projection height",
                          constraints={"max_depth":4,"k":3,"executable_only":False})
    backward=opsearch.plan(None,"depth",direction="backward",goal="fringe projection height",
                           constraints={"max_depth":4,"k":3,"executable_only":False})
    assert forward["ok"] and backward["ok"]
    assert "decode_fringe" in forward["plans"][0]["ops"]
    assert "decode_fringe" in backward["plans"][0]["ops"]
    assert forward["search"]["elapsed_ms"] < 1000
    capped=opsearch.plan("image","feature",goal="features",constraints={"max_expansions":1})
    assert capped["partial"]["limit_reached"] == "max_expansions"

def test_business_plan_mutation_is_caught(monkeypatch):
    g=load("OP_GRAPH.json"); g["edges"]=[e for e in g["edges"] if e["op"]!="decode_fringe"]
    monkeypatch.setitem(opsearch._CACHE,"json:OP_GRAPH.json",g)
    r=opsearch.plan("images","depth",constraints={"query":"fringe projection height","k":5,"executable_only":False})
    matching_plans=[p for p in r.get("plans",[]) if "decode_fringe" in p["ops"]]
    assert matching_plans == []

def test_three_multi_input_business_dags_execute_through_mcp():
    import numpy as np
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import call_tool
    store=HandleStore(roots=[]); cat=Catalog.load()
    def put(value,sort="image"):
        return store.put(np.asarray(value,float),sort=sort,provenance=[{"synthetic":True}])["handle"]
    diffuse=put(np.full((32,32),.3)); specular=put(np.full((32,32),.1))
    polar=call_tool("fullseye_pipeline",{"handle":diffuse,"stages":[
        {"op":"polarization_render","inputs":[diffuse,specular],"params":{}},
        {"op":"polarization_dolp_map","inputs":["stage:1"],"params":{}},
        {"op":"threshold","inputs":["stage:2"],"params":{},"a":.5}]},cat,store)
    frames=np.stack([.5+.4*np.cos(2*(2*np.pi*i/4))*np.ones((32,32)) for i in range(4)])
    stack=put(frames,"images")
    fringe=call_tool("fullseye_pipeline",{"handle":stack,"stages":[
        {"op":"decode_fringe","inputs":[stack],"params":{"k":1.0}}]},cat,store)
    phase=put(np.zeros((32,32)))
    mirror=call_tool("fullseye_pipeline",{"handle":phase,"stages":[
        {"op":"deflectometry_phase_to_slope","inputs":[phase,phase],"params":{}}]},cat,store)
    assert [polar.get("isError"),fringe.get("isError"),mirror.get("isError")] == [False,False,False]
    assert polar["structuredContent"]["out_sort"] == "region"
    assert fringe["structuredContent"]["out_sort"] == "depth"
    assert mirror["structuredContent"]["out_sort"] == "normalmap"

def test_validate_distinguishes_unknown_from_known_non_executable():
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.server import validate_pipeline
    cat=Catalog.load()
    known=validate_pipeline([{"op":"register_cross","inputs":["input","input"],"params":{}}],"image",cat)
    missing=validate_pipeline([{"op":"definitely_missing_op","inputs":["input"],"params":{}}],"image",cat)
    assert known["errors"][0]["reason"] == "not_executable_in_mcp"
    assert missing["errors"][0]["reason"] == "unknown_op"
    assert "definitely_missing_op" not in missing["errors"][0]["candidates"]

def test_family_negative_examples_and_cpu_measurements():
    f=load("OP_FAMILIES.json"); members={x["name"]:{r["op"] for r in x["ops"]} for x in f["families"]}
    assert "thin_lens" not in members["morphology"]
    assert "holdout_threshold" not in members["thresholding"]
    timing=json.loads((ROOT/"docs/ops/families_timing.json").read_text(encoding="utf-8"))
    measured=[r for r in timing["measurements"].values() if r["status"]=="measured"]
    assert measured
    missing_exponents=[r for r in measured if r.get("complexity_exponent") is None]
    assert missing_exponents == []
    quick=timing["measurements"]["quicksort"]
    assert set(quick["complexity_exponents"]) == {"random","nearly_sorted","reverse","duplicates"}
    assert 1.4 <= quick["complexity_exponents"]["nearly_sorted"] < 1.6
    stability={n:next(p["value"] for p in timing["measurements"][n]["properties"] if p["name"]=="stable")
               for n in ("quicksort","heapsort","mergesort")}
    assert stability == {"quicksort":False,"heapsort":False,"mergesort":True}
    g=load("OP_GRAPH.json")
    heuristic=[e for e in g["edges"] if e.get("family_candidate") and not e.get("family")]
    assert heuristic
    assert {e["family_candidate_source"] for e in heuristic} == {"heuristic_regex"}

def test_knob_schema_context_edges_and_system_params():
    assert opsearch.param_space("lowpass",{"width":512})["parameters"]["a"]["search"]
    assert opsearch.param_space("local_std",{"width":512})["parameters"]["a"]["enum"] == [0.0,0.25,0.49,0.75,1.0]
    one=opsearch.param_space("median",{"width":1,"height":1})
    assert one["parameters"]["a"]["max"] == 0.0
    system=opsearch.system_params(); params=system["params"]
    assert system["generated_from"] == "fssystem.SYSTEM_PARAMS"
    missing=[name for name,r in params.items() if not r["hide_from_ai"] or "applied_by" not in r]
    assert missing == []

def test_mcp_minimal_profile_is_ten_tools_and_patterns_are_hidden():
    from fullseye.mcp.server import handle_tools_list
    r=handle_tools_list({"profile":"minimal"}); assert len(r["tools"])==10 and r["estimated_tokens"] < 1500
    full=handle_tools_list({"profile":"full"}); assert "fullseye_patterns" not in {x["name"] for x in full["tools"]}
